"""Wrapper para Applio/RVC — conversão de timbre vocal."""

import asyncio
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
import structlog

logger = structlog.get_logger()


class RVCConfig:
    """Configurações para conversão de timbre RVC."""

    def __init__(
        self,
        model_name: str = "",
        pitch_shift: int = 0,
        index_rate: float = 0.75,
        filter_radius: int = 3,
        rms_mix_rate: float = 0.25,
        protect: float = 0.33,
        f0_method: str = "rmvpe",
        sample_rate: int = 44100,
    ):
        self.model_name = model_name
        self.pitch_shift = pitch_shift
        self.index_rate = index_rate
        self.filter_radius = filter_radius
        self.rms_mix_rate = rms_mix_rate
        self.protect = protect
        self.f0_method = f0_method
        self.sample_rate = sample_rate

    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name,
            "pitch_shift": self.pitch_shift,
            "index_rate": self.index_rate,
            "filter_radius": self.filter_radius,
            "rms_mix_rate": self.rms_mix_rate,
            "protect": self.protect,
            "f0_method": self.f0_method,
            "sample_rate": self.sample_rate,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RVCConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__init__.__code__.co_varnames})


class RVCService:
    """Serviço de conversão de timbre vocal usando Applio/RVC."""

    def __init__(self, engine_path: Path | None = None):
        from config import settings
        self.engine_path = engine_path or settings.applio_path

    def is_available(self) -> bool:
        """Verifica se o Applio/RVC está instalado."""
        if not self.engine_path.exists():
            return False
        return (self.engine_path / "infer-web.py").exists() or any(self.engine_path.glob("*.py"))

    def list_models(self) -> list[dict]:
        """Lista modelos RVC disponíveis."""
        models = []
        models_dir = self.engine_path / "models"
        if not models_dir.exists():
            return models

        for pth_file in models_dir.glob("**/*.pth"):
            index_file = pth_file.with_suffix(".index")
            if not index_file.exists():
                # Procurar index no mesmo diretório
                index_files = list(pth_file.parent.glob("*.index"))
                index_file = index_files[0] if index_files else None

            models.append({
                "name": pth_file.stem,
                "path": str(pth_file),
                "has_index": index_file is not None and index_file.exists(),
                "index_path": str(index_file) if index_file and index_file.exists() else None,
            })
        return models

    async def convert(
        self,
        input_path: Path,
        output_path: Path,
        config: RVCConfig,
    ) -> Path:
        """Converte o timbre do vocal usando RVC."""
        return await asyncio.to_thread(
            self._convert_sync, input_path, output_path, config
        )

    def _convert_sync(
        self,
        input_path: Path,
        output_path: Path,
        config: RVCConfig,
    ) -> Path:
        """Conversão síncrona via RVC/Applio."""
        logger.info(
            "rvc_conversao_iniciada",
            model=config.model_name,
            pitch_shift=config.pitch_shift,
        )

        if not input_path.exists():
            raise FileNotFoundError(f"Arquivo de entrada não encontrado: {input_path}")

        if self.is_available() and config.model_name:
            return self._run_engine(input_path, output_path, config)
        else:
            logger.warning("rvc_nao_disponivel_usando_fallback")
            return self._apply_placeholder_effect(input_path, output_path, config)

    def _run_engine(
        self,
        input_path: Path,
        output_path: Path,
        config: RVCConfig,
    ) -> Path:
        """Executa o Applio/RVC real."""
        model_path = self.engine_path / "models" / f"{config.model_name}.pth"

        cmd = [
            "python", str(self.engine_path / "infer-web.py"),
            "--input", str(input_path),
            "--output", str(output_path),
            "--model", str(model_path),
            "--pitch", str(config.pitch_shift),
            "--index_rate", str(config.index_rate),
            "--filter_radius", str(config.filter_radius),
            "--rms_mix_rate", str(config.rms_mix_rate),
            "--protect", str(config.protect),
            "--f0_method", config.f0_method,
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600
            )
            if result.returncode != 0:
                logger.error("rvc_erro", stderr=result.stderr)
                raise RuntimeError(f"RVC falhou: {result.stderr[:500]}")
        except FileNotFoundError:
            logger.warning("rvc_cli_nao_encontrado_usando_fallback")
            return self._apply_placeholder_effect(input_path, output_path, config)

        logger.info("rvc_conversao_concluida", output=str(output_path))
        return output_path

    def _apply_placeholder_effect(
        self,
        input_path: Path,
        output_path: Path,
        config: RVCConfig,
    ) -> Path:
        """Aplica efeito de pitch-shift simples como placeholder."""
        import librosa

        y, sr = librosa.load(str(input_path), sr=config.sample_rate)

        # Aplicar pitch shift
        if config.pitch_shift != 0:
            y = librosa.effects.pitch_shift(
                y, sr=sr, n_steps=config.pitch_shift
            )

        # Leve suavização para simular mudança de timbre
        if len(y) > 1024:
            kernel_size = 3
            kernel = np.ones(kernel_size) / kernel_size
            y = np.convolve(y, kernel, mode="same").astype(np.float32)

        # Normalizar
        peak = np.max(np.abs(y))
        if peak > 0:
            y = y / peak * 0.8

        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output_path), y, sr)

        logger.info(
            "rvc_placeholder_aplicado",
            output=str(output_path),
            pitch_shift=config.pitch_shift,
        )
        return output_path
