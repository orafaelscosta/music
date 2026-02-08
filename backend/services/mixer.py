"""Serviço de mixagem e masterização com Pedalboard."""

import asyncio
from pathlib import Path

import numpy as np
import soundfile as sf
import structlog

logger = structlog.get_logger()


class MixPreset:
    """Preset de mixagem com parâmetros pré-definidos."""

    PRESETS = {
        "balanced": {
            "vocal_gain_db": 0.0,
            "instrumental_gain_db": -3.0,
            "eq_low_gain_db": 0.0,
            "eq_mid_gain_db": 2.0,
            "eq_high_gain_db": 1.0,
            "compressor_threshold_db": -18.0,
            "compressor_ratio": 3.0,
            "reverb_room_size": 0.3,
            "reverb_wet_level": 0.15,
            "limiter_threshold_db": -1.0,
        },
        "vocal_forward": {
            "vocal_gain_db": 3.0,
            "instrumental_gain_db": -6.0,
            "eq_low_gain_db": -2.0,
            "eq_mid_gain_db": 4.0,
            "eq_high_gain_db": 2.0,
            "compressor_threshold_db": -15.0,
            "compressor_ratio": 4.0,
            "reverb_room_size": 0.2,
            "reverb_wet_level": 0.1,
            "limiter_threshold_db": -1.0,
        },
        "ambient": {
            "vocal_gain_db": -2.0,
            "instrumental_gain_db": 0.0,
            "eq_low_gain_db": 2.0,
            "eq_mid_gain_db": 0.0,
            "eq_high_gain_db": 3.0,
            "compressor_threshold_db": -20.0,
            "compressor_ratio": 2.0,
            "reverb_room_size": 0.7,
            "reverb_wet_level": 0.35,
            "limiter_threshold_db": -1.0,
        },
        "dry": {
            "vocal_gain_db": 0.0,
            "instrumental_gain_db": -3.0,
            "eq_low_gain_db": 0.0,
            "eq_mid_gain_db": 0.0,
            "eq_high_gain_db": 0.0,
            "compressor_threshold_db": -12.0,
            "compressor_ratio": 2.0,
            "reverb_room_size": 0.0,
            "reverb_wet_level": 0.0,
            "limiter_threshold_db": -1.0,
        },
        "radio": {
            "vocal_gain_db": 2.0,
            "instrumental_gain_db": -4.0,
            "eq_low_gain_db": -4.0,
            "eq_mid_gain_db": 5.0,
            "eq_high_gain_db": 3.0,
            "compressor_threshold_db": -12.0,
            "compressor_ratio": 6.0,
            "reverb_room_size": 0.15,
            "reverb_wet_level": 0.08,
            "limiter_threshold_db": -0.5,
        },
    }

    @classmethod
    def get(cls, name: str) -> dict:
        """Retorna parâmetros de um preset."""
        return cls.PRESETS.get(name, cls.PRESETS["balanced"]).copy()

    @classmethod
    def list_presets(cls) -> list[dict]:
        """Lista presets disponíveis."""
        return [
            {"name": name, "params": params}
            for name, params in cls.PRESETS.items()
        ]


class MixConfig:
    """Configurações da mixagem."""

    def __init__(
        self,
        vocal_gain_db: float = 0.0,
        instrumental_gain_db: float = -3.0,
        eq_low_gain_db: float = 0.0,
        eq_mid_gain_db: float = 2.0,
        eq_high_gain_db: float = 1.0,
        compressor_threshold_db: float = -18.0,
        compressor_ratio: float = 3.0,
        reverb_room_size: float = 0.3,
        reverb_wet_level: float = 0.15,
        limiter_threshold_db: float = -1.0,
        output_format: str = "wav",
        sample_rate: int = 44100,
    ):
        self.vocal_gain_db = vocal_gain_db
        self.instrumental_gain_db = instrumental_gain_db
        self.eq_low_gain_db = eq_low_gain_db
        self.eq_mid_gain_db = eq_mid_gain_db
        self.eq_high_gain_db = eq_high_gain_db
        self.compressor_threshold_db = compressor_threshold_db
        self.compressor_ratio = compressor_ratio
        self.reverb_room_size = reverb_room_size
        self.reverb_wet_level = reverb_wet_level
        self.limiter_threshold_db = limiter_threshold_db
        self.output_format = output_format
        self.sample_rate = sample_rate

    def to_dict(self) -> dict:
        return {
            "vocal_gain_db": self.vocal_gain_db,
            "instrumental_gain_db": self.instrumental_gain_db,
            "eq_low_gain_db": self.eq_low_gain_db,
            "eq_mid_gain_db": self.eq_mid_gain_db,
            "eq_high_gain_db": self.eq_high_gain_db,
            "compressor_threshold_db": self.compressor_threshold_db,
            "compressor_ratio": self.compressor_ratio,
            "reverb_room_size": self.reverb_room_size,
            "reverb_wet_level": self.reverb_wet_level,
            "limiter_threshold_db": self.limiter_threshold_db,
            "output_format": self.output_format,
            "sample_rate": self.sample_rate,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MixConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__init__.__code__.co_varnames})

    @classmethod
    def from_preset(cls, preset_name: str) -> "MixConfig":
        """Cria config a partir de um preset."""
        params = MixPreset.get(preset_name)
        return cls(**params)


class MixerService:
    """Serviço de mixagem vocal + instrumental com cadeia de efeitos."""

    def _use_pedalboard(self) -> bool:
        """Verifica se Pedalboard está disponível."""
        try:
            import pedalboard  # noqa: F401
            return True
        except ImportError:
            return False

    async def mix(
        self,
        vocal_path: Path,
        instrumental_path: Path,
        output_path: Path,
        config: MixConfig,
    ) -> Path:
        """Mixa vocal com instrumental aplicando cadeia de efeitos."""
        return await asyncio.to_thread(
            self._mix_sync, vocal_path, instrumental_path, output_path, config
        )

    def _mix_sync(
        self,
        vocal_path: Path,
        instrumental_path: Path,
        output_path: Path,
        config: MixConfig,
    ) -> Path:
        """Mixagem síncrona."""
        logger.info(
            "mix_iniciado",
            vocal=str(vocal_path),
            instrumental=str(instrumental_path),
        )

        if self._use_pedalboard():
            return self._mix_with_pedalboard(
                vocal_path, instrumental_path, output_path, config
            )
        else:
            logger.warning("pedalboard_nao_disponivel_usando_fallback")
            return self._mix_fallback(
                vocal_path, instrumental_path, output_path, config
            )

    def _mix_with_pedalboard(
        self,
        vocal_path: Path,
        instrumental_path: Path,
        output_path: Path,
        config: MixConfig,
    ) -> Path:
        """Mixagem usando Pedalboard com cadeia de efeitos profissional."""
        import pedalboard
        from pedalboard.io import AudioFile

        # Ler vocal
        with AudioFile(str(vocal_path)) as f:
            vocal_audio = f.read(f.frames)
            vocal_sr = f.samplerate

        # Ler instrumental
        with AudioFile(str(instrumental_path)) as f:
            inst_audio = f.read(f.frames)
            inst_sr = f.samplerate

        # Resample se necessário
        if vocal_sr != config.sample_rate:
            import librosa
            vocal_audio = librosa.resample(
                vocal_audio, orig_sr=vocal_sr, target_sr=config.sample_rate
            )
        if inst_sr != config.sample_rate:
            import librosa
            inst_audio = librosa.resample(
                inst_audio, orig_sr=inst_sr, target_sr=config.sample_rate
            )

        sr = config.sample_rate

        # Cadeia de efeitos no vocal
        vocal_board = pedalboard.Pedalboard([
            pedalboard.Gain(gain_db=config.vocal_gain_db),
            pedalboard.HighpassFilter(cutoff_frequency_hz=80.0),
            pedalboard.LowShelfFilter(
                cutoff_frequency_hz=250.0,
                gain_db=config.eq_low_gain_db,
            ),
            pedalboard.PeakFilter(
                cutoff_frequency_hz=2500.0,
                gain_db=config.eq_mid_gain_db,
                q=1.0,
            ),
            pedalboard.HighShelfFilter(
                cutoff_frequency_hz=8000.0,
                gain_db=config.eq_high_gain_db,
            ),
            pedalboard.Compressor(
                threshold_db=config.compressor_threshold_db,
                ratio=config.compressor_ratio,
                attack_ms=10.0,
                release_ms=100.0,
            ),
            pedalboard.Reverb(
                room_size=config.reverb_room_size,
                wet_level=config.reverb_wet_level,
                dry_level=1.0 - config.reverb_wet_level,
            ),
        ])

        # Efeitos no instrumental
        inst_board = pedalboard.Pedalboard([
            pedalboard.Gain(gain_db=config.instrumental_gain_db),
        ])

        # Processar
        vocal_processed = vocal_board(vocal_audio, sr)
        inst_processed = inst_board(inst_audio, sr)

        # Alinhar durações (pad com silêncio)
        vocal_channels = vocal_processed.shape[0] if vocal_processed.ndim > 1 else 1
        inst_channels = inst_processed.shape[0] if inst_processed.ndim > 1 else 1

        # Garantir mono ou stereo consistente
        if vocal_processed.ndim == 1:
            vocal_processed = vocal_processed.reshape(1, -1)
        if inst_processed.ndim == 1:
            inst_processed = inst_processed.reshape(1, -1)

        # Converter ambos para stereo
        if vocal_processed.shape[0] == 1:
            vocal_processed = np.vstack([vocal_processed, vocal_processed])
        if inst_processed.shape[0] == 1:
            inst_processed = np.vstack([inst_processed, inst_processed])

        # Alinhar comprimentos
        max_len = max(vocal_processed.shape[1], inst_processed.shape[1])
        if vocal_processed.shape[1] < max_len:
            pad = np.zeros((2, max_len - vocal_processed.shape[1]))
            vocal_processed = np.hstack([vocal_processed, pad])
        if inst_processed.shape[1] < max_len:
            pad = np.zeros((2, max_len - inst_processed.shape[1]))
            inst_processed = np.hstack([inst_processed, pad])

        # Somar
        mixed = vocal_processed + inst_processed

        # Limiter final
        master_board = pedalboard.Pedalboard([
            pedalboard.Limiter(threshold_db=config.limiter_threshold_db),
        ])
        mixed = master_board(mixed.astype(np.float32), sr)

        # Salvar
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with AudioFile(str(output_path), "w", sr, num_channels=2) as f:
            f.write(mixed)

        logger.info("mix_pedalboard_concluido", output=str(output_path))
        return output_path

    def _mix_fallback(
        self,
        vocal_path: Path,
        instrumental_path: Path,
        output_path: Path,
        config: MixConfig,
    ) -> Path:
        """Mixagem com NumPy/SciPy quando Pedalboard não está disponível."""
        import librosa

        # Carregar áudios
        vocal, v_sr = librosa.load(str(vocal_path), sr=config.sample_rate, mono=True)
        instrumental, i_sr = librosa.load(str(instrumental_path), sr=config.sample_rate, mono=True)

        # Aplicar ganho (dB → linear)
        vocal_gain = 10 ** (config.vocal_gain_db / 20.0)
        inst_gain = 10 ** (config.instrumental_gain_db / 20.0)
        vocal = vocal * vocal_gain
        instrumental = instrumental * inst_gain

        # EQ simplificado via filtros
        vocal = self._apply_simple_eq(vocal, config.sample_rate, config)

        # Compressão simples
        vocal = self._apply_simple_compression(
            vocal, config.compressor_threshold_db, config.compressor_ratio
        )

        # Reverb simples (convolução com impulso)
        if config.reverb_wet_level > 0:
            vocal = self._apply_simple_reverb(
                vocal, config.sample_rate,
                config.reverb_room_size, config.reverb_wet_level
            )

        # Alinhar comprimentos
        max_len = max(len(vocal), len(instrumental))
        if len(vocal) < max_len:
            vocal = np.pad(vocal, (0, max_len - len(vocal)))
        if len(instrumental) < max_len:
            instrumental = np.pad(instrumental, (0, max_len - len(instrumental)))

        # Somar
        mixed = vocal + instrumental

        # Limiter simples
        limit = 10 ** (config.limiter_threshold_db / 20.0)
        peak = np.max(np.abs(mixed))
        if peak > limit:
            mixed = mixed * (limit / peak)

        # Converter para stereo
        mixed_stereo = np.vstack([mixed, mixed])

        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output_path), mixed_stereo.T, config.sample_rate)

        logger.info("mix_fallback_concluido", output=str(output_path))
        return output_path

    def _apply_simple_eq(
        self, audio: np.ndarray, sr: int, config: MixConfig
    ) -> np.ndarray:
        """EQ simplificado com filtros de shelving."""
        from scipy import signal

        # High-pass em 80Hz para limpar graves
        sos = signal.butter(2, 80, btype="high", fs=sr, output="sos")
        audio = signal.sosfilt(sos, audio).astype(np.float32)

        # Low shelf em 250Hz
        if abs(config.eq_low_gain_db) > 0.5:
            gain = 10 ** (config.eq_low_gain_db / 20.0)
            sos = signal.butter(1, 250, btype="low", fs=sr, output="sos")
            low = signal.sosfilt(sos, audio).astype(np.float32)
            audio = audio + low * (gain - 1)

        # Mid peak em 2.5kHz
        if abs(config.eq_mid_gain_db) > 0.5:
            gain = 10 ** (config.eq_mid_gain_db / 20.0)
            sos = signal.butter(2, [1500, 4000], btype="band", fs=sr, output="sos")
            mid = signal.sosfilt(sos, audio).astype(np.float32)
            audio = audio + mid * (gain - 1)

        # High shelf em 8kHz
        if abs(config.eq_high_gain_db) > 0.5:
            gain = 10 ** (config.eq_high_gain_db / 20.0)
            sos = signal.butter(1, 8000, btype="high", fs=sr, output="sos")
            high = signal.sosfilt(sos, audio).astype(np.float32)
            audio = audio + high * (gain - 1)

        return audio

    def _apply_simple_compression(
        self, audio: np.ndarray, threshold_db: float, ratio: float
    ) -> np.ndarray:
        """Compressão simplificada."""
        threshold = 10 ** (threshold_db / 20.0)
        output = np.copy(audio)

        above_mask = np.abs(output) > threshold
        if np.any(above_mask):
            signs = np.sign(output[above_mask])
            magnitudes = np.abs(output[above_mask])
            excess = magnitudes - threshold
            compressed = threshold + excess / ratio
            output[above_mask] = signs * compressed

        return output

    def _apply_simple_reverb(
        self,
        audio: np.ndarray,
        sr: int,
        room_size: float,
        wet_level: float,
    ) -> np.ndarray:
        """Reverb simplificado com delay feedback."""
        delay_samples = int(room_size * 0.05 * sr)
        if delay_samples < 1:
            return audio

        reverb = np.zeros_like(audio)
        feedback = 0.5 * room_size
        num_taps = 6

        for i in range(num_taps):
            tap_delay = delay_samples * (i + 1)
            tap_gain = feedback ** (i + 1)
            if tap_delay < len(audio):
                padded = np.pad(audio, (tap_delay, 0))[:len(audio)]
                reverb += padded * tap_gain

        return audio * (1.0 - wet_level) + reverb * wet_level

    async def export(
        self,
        input_path: Path,
        output_path: Path,
        output_format: str = "wav",
        sample_rate: int = 44100,
    ) -> Path:
        """Exporta áudio mixado em formato específico."""
        return await asyncio.to_thread(
            self._export_sync, input_path, output_path, output_format, sample_rate
        )

    def _export_sync(
        self,
        input_path: Path,
        output_path: Path,
        output_format: str,
        sample_rate: int,
    ) -> Path:
        """Exportação síncrona para formato específico."""
        import librosa

        y, sr = librosa.load(str(input_path), sr=sample_rate, mono=False)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_format == "wav":
            sf.write(str(output_path), y.T if y.ndim > 1 else y, sample_rate, format="WAV")
        elif output_format == "flac":
            sf.write(str(output_path), y.T if y.ndim > 1 else y, sample_rate, format="FLAC")
        elif output_format == "mp3":
            # Usar ffmpeg para MP3
            import subprocess
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                sf.write(tmp.name, y.T if y.ndim > 1 else y, sample_rate)
                subprocess.run(
                    ["ffmpeg", "-y", "-i", tmp.name, "-b:a", "320k", str(output_path)],
                    capture_output=True, timeout=120,
                )
                Path(tmp.name).unlink(missing_ok=True)
        elif output_format == "ogg":
            sf.write(str(output_path), y.T if y.ndim > 1 else y, sample_rate, format="OGG")
        else:
            sf.write(str(output_path), y.T if y.ndim > 1 else y, sample_rate)

        logger.info(
            "export_concluido",
            output=str(output_path),
            format=output_format,
        )
        return output_path
