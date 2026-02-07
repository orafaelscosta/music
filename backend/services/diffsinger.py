"""Wrapper para o engine DiffSinger — síntese vocal a partir de MIDI + letra."""

import asyncio
import json
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
import structlog

logger = structlog.get_logger()


class DiffSingerConfig:
    """Configurações para renderização DiffSinger."""

    def __init__(
        self,
        voicebank: str = "leif",
        language: str = "it",
        breathiness: float = 0.0,
        tension: float = 0.0,
        energy: float = 1.0,
        voicing: float = 1.0,
        pitch_deviation: float = 0.0,
        gender: float = 0.0,
        sample_rate: int = 44100,
    ):
        self.voicebank = voicebank
        self.language = language
        self.breathiness = breathiness
        self.tension = tension
        self.energy = energy
        self.voicing = voicing
        self.pitch_deviation = pitch_deviation
        self.gender = gender
        self.sample_rate = sample_rate

    def to_dict(self) -> dict:
        return {
            "voicebank": self.voicebank,
            "language": self.language,
            "breathiness": self.breathiness,
            "tension": self.tension,
            "energy": self.energy,
            "voicing": self.voicing,
            "pitch_deviation": self.pitch_deviation,
            "gender": self.gender,
            "sample_rate": self.sample_rate,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DiffSingerConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__init__.__code__.co_varnames})


class DiffSingerService:
    """Serviço de síntese vocal usando DiffSinger/OpenUtau."""

    def __init__(self, engine_path: Path | None = None):
        from config import settings
        self.engine_path = engine_path or settings.diffsinger_path
        self.voicebanks_path = settings.voicebanks_path

    def is_available(self) -> bool:
        """Verifica se o DiffSinger está instalado e configurado."""
        return self.engine_path.exists() and any(self.engine_path.iterdir()) if self.engine_path.exists() else False

    def list_voicebanks(self) -> list[dict]:
        """Lista voicebanks disponíveis."""
        voicebanks = []
        if not self.voicebanks_path.exists():
            return voicebanks

        for lang_dir in self.voicebanks_path.iterdir():
            if not lang_dir.is_dir():
                continue
            for vb_dir in lang_dir.iterdir():
                if not vb_dir.is_dir():
                    continue
                voicebanks.append({
                    "name": vb_dir.name,
                    "language": lang_dir.name,
                    "path": str(vb_dir),
                    "has_model": any(vb_dir.glob("*.onnx")) or any(vb_dir.glob("*.pth")),
                })
        return voicebanks

    async def synthesize(
        self,
        melody_json_path: Path,
        output_path: Path,
        config: DiffSingerConfig,
        preview_seconds: float | None = None,
    ) -> Path:
        """Sintetiza vocal a partir de melodia JSON + configuração."""
        return await asyncio.to_thread(
            self._synthesize_sync, melody_json_path, output_path, config, preview_seconds
        )

    def _synthesize_sync(
        self,
        melody_json_path: Path,
        output_path: Path,
        config: DiffSingerConfig,
        preview_seconds: float | None = None,
    ) -> Path:
        """Síntese síncrona via DiffSinger."""
        logger.info(
            "diffsinger_sintese_iniciada",
            voicebank=config.voicebank,
            language=config.language,
        )

        # Carregar dados de melodia
        with open(melody_json_path) as f:
            melody_data = json.load(f)

        notes = melody_data.get("notes", [])
        if not notes:
            raise ValueError("Melodia sem notas para sintetizar")

        # Filtrar notas para preview
        if preview_seconds:
            notes = [n for n in notes if n["start_time"] < preview_seconds]

        # Preparar dados para DiffSinger
        ds_input = self._prepare_ds_input(notes, config)

        # Verificar se temos o engine real disponível
        if self.is_available():
            return self._run_engine(ds_input, output_path, config)
        else:
            # Fallback: gerar sinal de placeholder com frequências das notas
            logger.warning("diffsinger_nao_disponivel_usando_fallback")
            return self._generate_placeholder(notes, output_path, config, preview_seconds)

    def _prepare_ds_input(self, notes: list[dict], config: DiffSingerConfig) -> dict:
        """Prepara input no formato esperado pelo DiffSinger."""
        phonemes = []
        durations = []
        pitches = []

        for note in notes:
            lyric = note.get("lyric", "a")
            if not lyric:
                lyric = "a"

            # Fonemas simplificados — em produção usaria phonemizer real
            phonemes.append(lyric)
            durations.append(note["end_time"] - note["start_time"])
            pitches.append(note["midi_note"])

        return {
            "phonemes": phonemes,
            "durations": durations,
            "pitches": pitches,
            "config": config.to_dict(),
        }

    def _run_engine(
        self, ds_input: dict, output_path: Path, config: DiffSingerConfig
    ) -> Path:
        """Executa o engine DiffSinger real."""
        # Salvar input temporário
        input_path = output_path.parent / "ds_input.json"
        with open(input_path, "w") as f:
            json.dump(ds_input, f)

        # Executar DiffSinger CLI
        cmd = [
            "python", str(self.engine_path / "inference.py"),
            "--input", str(input_path),
            "--output", str(output_path),
            "--voicebank", config.voicebank,
            "--sample_rate", str(config.sample_rate),
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600
            )
            if result.returncode != 0:
                logger.error("diffsinger_erro", stderr=result.stderr)
                raise RuntimeError(f"DiffSinger falhou: {result.stderr[:500]}")
        except FileNotFoundError:
            logger.warning("diffsinger_cli_nao_encontrado_usando_fallback")
            return self._generate_placeholder(
                [{"start_time": d, "end_time": d + dur, "midi_note": p}
                 for d, dur, p in zip(
                    np.cumsum([0] + ds_input["durations"][:-1]),
                    ds_input["durations"],
                    ds_input["pitches"],
                )],
                output_path, config, None,
            )
        finally:
            if input_path.exists():
                input_path.unlink()

        logger.info("diffsinger_sintese_concluida", output=str(output_path))
        return output_path

    def _generate_placeholder(
        self,
        notes: list[dict],
        output_path: Path,
        config: DiffSingerConfig,
        preview_seconds: float | None,
    ) -> Path:
        """Gera áudio placeholder com sintetizador simples baseado nas notas."""
        sr = config.sample_rate

        if not notes:
            # Silêncio de 1 segundo
            audio = np.zeros(sr, dtype=np.float32)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(output_path), audio, sr)
            return output_path

        # Calcular duração total
        max_time = max(n["end_time"] for n in notes)
        if preview_seconds:
            max_time = min(max_time, preview_seconds)

        total_samples = int(max_time * sr) + sr  # +1s de padding
        audio = np.zeros(total_samples, dtype=np.float32)

        for note in notes:
            start = int(note["start_time"] * sr)
            end = int(note["end_time"] * sr)
            if preview_seconds:
                end = min(end, int(preview_seconds * sr))
            if start >= total_samples or end <= start:
                continue

            midi = note["midi_note"]
            freq = 440.0 * (2.0 ** ((midi - 69) / 12.0))
            duration_samples = end - start

            # Gerar vocal-like tone (fundamental + formantes)
            t = np.linspace(0, (end - start) / sr, duration_samples, endpoint=False)

            # Fundamental + harmônicos para simular voz
            signal = (
                0.5 * np.sin(2 * np.pi * freq * t)
                + 0.25 * np.sin(2 * np.pi * freq * 2 * t)
                + 0.12 * np.sin(2 * np.pi * freq * 3 * t)
                + 0.06 * np.sin(2 * np.pi * freq * 4 * t)
            )

            # Envelope ADSR simples
            attack = min(int(0.02 * sr), duration_samples // 4)
            release = min(int(0.05 * sr), duration_samples // 4)
            envelope = np.ones(duration_samples, dtype=np.float32)
            if attack > 0:
                envelope[:attack] = np.linspace(0, 1, attack)
            if release > 0:
                envelope[-release:] = np.linspace(1, 0, release)

            signal *= envelope * 0.3

            # Adicionar ao buffer principal
            end_idx = min(start + duration_samples, total_samples)
            audio[start:end_idx] += signal[: end_idx - start].astype(np.float32)

        # Normalizar
        peak = np.max(np.abs(audio))
        if peak > 0:
            audio = audio / peak * 0.8

        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output_path), audio, sr)

        logger.info(
            "placeholder_vocal_gerado",
            output=str(output_path),
            duration=max_time,
            notes=len(notes),
        )
        return output_path
