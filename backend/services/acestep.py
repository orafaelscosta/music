"""Wrapper para ACE-Step — geração vocal rápida com Lyric2Vocal."""

import asyncio
import json
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
import structlog

logger = structlog.get_logger()


class ACEStepConfig:
    """Configurações para geração ACE-Step."""

    def __init__(
        self,
        lyrics: str = "",
        language: str = "it",
        duration_seconds: float = 30.0,
        seed: int = -1,
        guidance_scale: float = 3.5,
        num_inference_steps: int = 50,
        sample_rate: int = 44100,
    ):
        self.lyrics = lyrics
        self.language = language
        self.duration_seconds = duration_seconds
        self.seed = seed
        self.guidance_scale = guidance_scale
        self.num_inference_steps = num_inference_steps
        self.sample_rate = sample_rate

    def to_dict(self) -> dict:
        return {
            "lyrics": self.lyrics,
            "language": self.language,
            "duration_seconds": self.duration_seconds,
            "seed": self.seed,
            "guidance_scale": self.guidance_scale,
            "num_inference_steps": self.num_inference_steps,
            "sample_rate": self.sample_rate,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ACEStepConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__init__.__code__.co_varnames})


class ACEStepService:
    """Serviço de geração vocal rápida usando ACE-Step v1.5."""

    def __init__(self, engine_path: Path | None = None):
        from config import settings
        self.engine_path = engine_path or settings.acestep_path

    def is_available(self) -> bool:
        """Verifica se o ACE-Step está instalado."""
        if not self.engine_path.exists():
            return False
        return any(self.engine_path.glob("*.py")) or (self.engine_path / "models").exists()

    async def generate(
        self,
        output_path: Path,
        config: ACEStepConfig,
        instrumental_path: Path | None = None,
    ) -> Path:
        """Gera vocal com ACE-Step no modo Lyric2Vocal."""
        return await asyncio.to_thread(
            self._generate_sync, output_path, config, instrumental_path
        )

    def _generate_sync(
        self,
        output_path: Path,
        config: ACEStepConfig,
        instrumental_path: Path | None = None,
    ) -> Path:
        """Geração síncrona via ACE-Step."""
        logger.info(
            "acestep_geracao_iniciada",
            language=config.language,
            duration=config.duration_seconds,
        )

        if self.is_available():
            return self._run_engine(output_path, config, instrumental_path)
        else:
            logger.warning("acestep_nao_disponivel_usando_fallback")
            return self._generate_placeholder(output_path, config)

    def _run_engine(
        self,
        output_path: Path,
        config: ACEStepConfig,
        instrumental_path: Path | None,
    ) -> Path:
        """Executa o ACE-Step real."""
        cmd = [
            "python", str(self.engine_path / "infer.py"),
            "--lyrics", config.lyrics,
            "--language", config.language,
            "--duration", str(config.duration_seconds),
            "--output", str(output_path),
            "--guidance_scale", str(config.guidance_scale),
            "--num_steps", str(config.num_inference_steps),
        ]

        if config.seed >= 0:
            cmd.extend(["--seed", str(config.seed)])

        if instrumental_path and instrumental_path.exists():
            cmd.extend(["--audio_prompt", str(instrumental_path)])

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600
            )
            if result.returncode != 0:
                logger.error("acestep_erro", stderr=result.stderr)
                raise RuntimeError(f"ACE-Step falhou: {result.stderr[:500]}")
        except FileNotFoundError:
            logger.warning("acestep_cli_nao_encontrado_usando_fallback")
            return self._generate_placeholder(output_path, config)

        logger.info("acestep_geracao_concluida", output=str(output_path))
        return output_path

    def _generate_placeholder(
        self, output_path: Path, config: ACEStepConfig
    ) -> Path:
        """Gera áudio placeholder para quando ACE-Step não está disponível."""
        sr = config.sample_rate
        duration = min(config.duration_seconds, 60.0)
        total_samples = int(duration * sr)

        # Gerar um drone vocal simples como placeholder
        t = np.linspace(0, duration, total_samples, endpoint=False)

        # Frequência base que varia lentamente (simula melodia)
        base_freq = 220.0  # A3
        vibrato = 5.0 * np.sin(2 * np.pi * 5.5 * t)  # Vibrato 5.5Hz
        freq_contour = base_freq + vibrato

        # Fase instantânea
        phase = 2 * np.pi * np.cumsum(freq_contour) / sr

        # Fundamental + harmônicos
        audio = (
            0.5 * np.sin(phase)
            + 0.2 * np.sin(2 * phase)
            + 0.1 * np.sin(3 * phase)
            + 0.05 * np.sin(4 * phase)
        ).astype(np.float32)

        # Fade in/out
        fade_samples = int(0.5 * sr)
        if fade_samples > 0 and total_samples > 2 * fade_samples:
            audio[:fade_samples] *= np.linspace(0, 1, fade_samples).astype(np.float32)
            audio[-fade_samples:] *= np.linspace(1, 0, fade_samples).astype(np.float32)

        audio *= 0.4

        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output_path), audio, sr)

        logger.info(
            "acestep_placeholder_gerado",
            output=str(output_path),
            duration=duration,
        )
        return output_path
