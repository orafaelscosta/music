"""Serviço de separação de fontes usando Demucs (htdemucs)."""

import asyncio
from pathlib import Path

import numpy as np
import soundfile as sf
import structlog
import torch

logger = structlog.get_logger()

# Cache do modelo para evitar reload
_model_cache = None


def _get_model():
    """Carrega o modelo htdemucs (cached)."""
    global _model_cache
    if _model_cache is None:
        from demucs.pretrained import get_model
        logger.info("demucs_carregando_modelo", model="htdemucs")
        _model_cache = get_model("htdemucs")
        logger.info("demucs_modelo_carregado")
    return _model_cache


class DemucsService:
    """Separação de fontes com Demucs htdemucs."""

    async def separate(
        self,
        input_path: Path,
        output_dir: Path,
        progress_fn=None,
    ) -> dict[str, Path]:
        """Separa áudio em vocals + instrumental (drums+bass+other).

        Retorna dict com paths: {"vocals": Path, "instrumental": Path}
        """
        return await asyncio.to_thread(
            self._separate_sync, input_path, output_dir, progress_fn,
        )

    def _separate_sync(
        self,
        input_path: Path,
        output_dir: Path,
        progress_fn=None,
    ) -> dict[str, Path]:
        """Separação síncrona."""
        from demucs.apply import apply_model
        from demucs.audio import AudioFile

        model = _get_model()
        if progress_fn:
            progress_fn(10, "Modelo Demucs carregado")

        logger.info("demucs_separacao_iniciada", input=str(input_path))

        # Carregar áudio
        wav = AudioFile(input_path).read(
            streams=0, samplerate=model.samplerate, channels=model.audio_channels,
        )
        ref = wav.mean(0)
        wav = (wav - ref.mean()) / ref.std()

        if progress_fn:
            progress_fn(20, "Audio carregado, separando fontes...")

        # Aplicar modelo
        device = torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")
        sources = apply_model(
            model, wav[None], device=device, progress=False, split=True,
        )
        sources = sources * ref.std() + ref.mean()

        if progress_fn:
            progress_fn(70, "Fontes separadas, salvando arquivos...")

        # sources shape: (1, n_sources, channels, samples)
        # sources order: drums, bass, other, vocals
        source_names = model.sources  # ['drums', 'bass', 'other', 'vocals']

        output_dir.mkdir(parents=True, exist_ok=True)
        output_paths = {}

        for i, name in enumerate(source_names):
            source_wav = sources[0, i].cpu().numpy()  # (channels, samples)
            out_path = output_dir / f"{name}.wav"
            # soundfile espera (samples, channels)
            sf.write(str(out_path), source_wav.T, model.samplerate)
            output_paths[name] = out_path
            logger.info("demucs_fonte_salva", name=name, path=str(out_path))

        if progress_fn:
            progress_fn(85, "Criando faixa instrumental...")

        # Criar instrumental = drums + bass + other
        instrumental = (
            sources[0, source_names.index("drums")]
            + sources[0, source_names.index("bass")]
            + sources[0, source_names.index("other")]
        ).cpu().numpy()

        instrumental_path = output_dir / "instrumental_separated.wav"
        sf.write(str(instrumental_path), instrumental.T, model.samplerate)
        output_paths["instrumental"] = instrumental_path

        if progress_fn:
            progress_fn(95, "Separacao concluida")

        # Log qualidade da separação
        vocals_rms = np.sqrt(np.mean(sources[0, source_names.index("vocals")].cpu().numpy() ** 2))
        instr_rms = np.sqrt(np.mean(instrumental ** 2))
        logger.info(
            "demucs_separacao_concluida",
            vocals_rms=round(float(vocals_rms), 4),
            instrumental_rms=round(float(instr_rms), 4),
            samplerate=model.samplerate,
        )

        return output_paths
