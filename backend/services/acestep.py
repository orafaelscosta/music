"""Wrapper para ACE-Step — geração vocal/musical com IA."""

import asyncio
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import structlog

logger = structlog.get_logger()

# Pipeline carregado uma vez (singleton) para evitar reload do modelo
_pipeline_instance = None
_pipeline_loading = False


class ACEStepConfig:
    """Configurações para geração ACE-Step."""

    def __init__(
        self,
        lyrics: str = "",
        language: str = "it",
        duration_seconds: float = 30.0,
        seed: int = -1,
        guidance_scale: float = 15.0,
        num_inference_steps: int = 60,
        sample_rate: int = 48000,
        prompt: str = "",
        scheduler_type: str = "euler",
        cfg_type: str = "apg",
        omega_scale: float = 10.0,
    ):
        self.lyrics = lyrics
        self.language = language
        self.duration_seconds = duration_seconds
        self.seed = seed
        self.guidance_scale = guidance_scale
        self.num_inference_steps = num_inference_steps
        self.sample_rate = sample_rate
        self.prompt = prompt
        self.scheduler_type = scheduler_type
        self.cfg_type = cfg_type
        self.omega_scale = omega_scale

    def to_dict(self) -> dict:
        return {
            "lyrics": self.lyrics,
            "language": self.language,
            "duration_seconds": self.duration_seconds,
            "seed": self.seed,
            "guidance_scale": self.guidance_scale,
            "num_inference_steps": self.num_inference_steps,
            "sample_rate": self.sample_rate,
            "prompt": self.prompt,
            "scheduler_type": self.scheduler_type,
            "cfg_type": self.cfg_type,
            "omega_scale": self.omega_scale,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ACEStepConfig":
        valid_keys = {
            "lyrics", "language", "duration_seconds", "seed",
            "guidance_scale", "num_inference_steps", "sample_rate",
            "prompt", "scheduler_type", "cfg_type", "omega_scale",
        }
        return cls(**{k: v for k, v in data.items() if k in valid_keys})


def format_lyrics_for_acestep(lyrics: str) -> str:
    """Formata letra com tags de estrutura para ACE-Step.

    ACE-Step usa tags como [verse], [chorus], [bridge] para segmentar.
    Detecta estrutura automaticamente por padrões de repetição.
    """
    if not lyrics or not lyrics.strip():
        return ""

    # Se já tem tags [verse]/[chorus], retornar como está
    if "[verse]" in lyrics.lower() or "[chorus]" in lyrics.lower():
        return lyrics

    # Separar em estrofes por linhas em branco
    raw_sections = [s.strip() for s in lyrics.split("\n\n") if s.strip()]

    if not raw_sections:
        return lyrics

    # Heurística: estrofes curtas (<=2 linhas) tendem a ser refrão
    formatted_parts = []
    chorus_seen = False
    for i, section in enumerate(raw_sections):
        lines = [l for l in section.split("\n") if l.strip()]
        n_lines = len(lines)

        if n_lines <= 2 and i > 0:
            tag = "[chorus]"
            chorus_seen = True
        elif chorus_seen and i == len(raw_sections) - 1 and n_lines <= 3:
            tag = "[outro]"
        elif i == 0:
            tag = "[verse]"
        else:
            tag = "[verse]"

        formatted_parts.append(f"{tag}\n{section}")

    return "\n\n".join(formatted_parts)


def build_acestep_prompt(
    language: str = "it",
    bpm: float | None = None,
    musical_key: str | None = None,
    vocal_style: str = "pop",
    gender: str = "neutral",
    voice_tags: list[str] | None = None,
) -> str:
    """Constrói prompt descritivo para ACE-Step baseado na análise do projeto.

    Args:
        gender: 'male', 'female' ou 'neutral' — inclui descritor de gênero no prompt.
        voice_tags: tags extras do voice preset (ex: ['operatic', 'dramatic']).
    """
    lang_names = {
        "it": "Italian", "pt": "Portuguese", "en": "English",
        "es": "Spanish", "fr": "French", "ja": "Japanese",
    }
    lang_name = lang_names.get(language, language)

    # Descritor de gênero vocal
    gender_desc = {
        "male": "male vocals",
        "female": "female vocals",
    }

    style_descriptors = {
        "pop": "pop, catchy, melodic, emotional",
        "operatic": "operatic, dramatic, classical, powerful vocals",
        "breathy": "breathy, intimate, soft, airy vocals",
        "powerful": "powerful, belting, energetic, strong vocals",
        "ethereal": "ethereal, ambient, dreamy, reverb vocals",
    }
    style_desc = style_descriptors.get(vocal_style, "pop, melodic, singing")

    parts = [f"{lang_name} vocal"]

    # Incluir gênero no prompt
    if gender in gender_desc:
        parts.append(gender_desc[gender])

    # Se temos voice_tags do preset, usar em vez do style_desc genérico
    if voice_tags:
        parts.extend(voice_tags)
    else:
        parts.append(style_desc)

    if musical_key:
        parts.append(musical_key)
    if bpm:
        parts.append(f"{bpm:.0f} BPM")

    return ", ".join(parts)


class ACEStepService:
    """Serviço de geração vocal/musical usando ACE-Step."""

    def __init__(self, engine_path: Path | None = None):
        from config import settings
        self.engine_path = engine_path or settings.acestep_path
        self.model_path = settings.acestep_model_path

    def is_available(self) -> bool:
        """Verifica se o ACE-Step está instalado."""
        if not self.engine_path.exists():
            return False
        has_code = (self.engine_path / "acestep" / "pipeline_ace_step.py").exists()
        # Safetensors ficam em subdiretórios (ace_step_transformer/, music_dcae_f8c8/, etc.)
        has_model = self.model_path.exists() and any(self.model_path.rglob("*.safetensors"))
        return has_code and has_model

    def _get_pipeline(self):
        """Retorna pipeline singleton (carrega modelo uma vez só)."""
        global _pipeline_instance, _pipeline_loading

        if _pipeline_instance is not None:
            return _pipeline_instance

        if _pipeline_loading:
            raise RuntimeError("Pipeline já está sendo carregado")

        _pipeline_loading = True
        try:
            # Adicionar repo ao sys.path para imports
            repo_str = str(self.engine_path)
            if repo_str not in sys.path:
                sys.path.insert(0, repo_str)

            from acestep.pipeline_ace_step import ACEStepPipeline

            logger.info(
                "acestep_carregando_modelo",
                checkpoint=str(self.model_path),
            )

            _pipeline_instance = ACEStepPipeline(
                checkpoint_dir=str(self.model_path),
                dtype="float32",  # CPU-friendly (bfloat16 para GPU)
                cpu_offload=True,
            )

            logger.info("acestep_modelo_carregado")
            return _pipeline_instance
        except Exception as e:
            logger.error("acestep_erro_carregamento", error=str(e))
            raise
        finally:
            _pipeline_loading = False

    async def generate(
        self,
        output_path: Path,
        config: ACEStepConfig,
        ref_audio_path: Path | None = None,
        ref_strength: float = 0.5,
    ) -> Path:
        """Gera música com vocal via ACE-Step.

        Args:
            ref_audio_path: Áudio de referência para audio2audio (ex: vocal original).
                Se None, usa text2music (gera do zero).
            ref_strength: Força da referência (0.0-1.0). Maior = mais similar ao ref.
                0.5 é bom para manter timing/melodia mas mudar a voz.
        """
        return await asyncio.to_thread(
            self._generate_sync, output_path, config, ref_audio_path, ref_strength
        )

    def _generate_sync(
        self,
        output_path: Path,
        config: ACEStepConfig,
        ref_audio_path: Path | None = None,
        ref_strength: float = 0.5,
    ) -> Path:
        """Geração síncrona via ACE-Step."""
        logger.info(
            "acestep_geracao_iniciada",
            language=config.language,
            duration=config.duration_seconds,
            mode="audio2audio" if ref_audio_path else "text2music",
        )

        if self.is_available():
            return self._run_engine(output_path, config, ref_audio_path, ref_strength)
        else:
            logger.warning("acestep_nao_disponivel_usando_fallback")
            return self._generate_placeholder(output_path, config)

    def _run_engine(
        self,
        output_path: Path,
        config: ACEStepConfig,
        ref_audio_path: Path | None,
        ref_strength: float,
    ) -> Path:
        """Executa o ACE-Step via API Python direta.

        Dois modos:
        - text2music (ref_audio_path=None): gera música completa do zero com vocal.
        - audio2audio (ref_audio_path=vocal.wav): cria variação mantendo timing/melodia.
          Ideal para voice replacement quando o ref é o vocal original.
        """
        try:
            pipeline = self._get_pipeline()

            output_path.parent.mkdir(parents=True, exist_ok=True)

            prompt = config.prompt
            if not prompt:
                prompt = f"A beautiful {config.language} vocal performance, singing, melodic"

            seeds = [config.seed] if config.seed >= 0 else None
            use_audio2audio = ref_audio_path is not None and ref_audio_path.exists()

            logger.info(
                "acestep_pipeline_call",
                mode="audio2audio" if use_audio2audio else "text2music",
                ref_audio=str(ref_audio_path) if use_audio2audio else None,
                ref_strength=ref_strength if use_audio2audio else None,
                prompt=prompt,
                duration=config.duration_seconds,
            )

            result = pipeline(
                audio_duration=config.duration_seconds,
                prompt=prompt,
                lyrics=config.lyrics,
                infer_step=config.num_inference_steps,
                guidance_scale=config.guidance_scale,
                scheduler_type=config.scheduler_type,
                cfg_type=config.cfg_type,
                omega_scale=config.omega_scale,
                manual_seeds=seeds,
                guidance_interval=0.5,
                guidance_interval_decay=0.0,
                min_guidance_scale=3.0,
                use_erg_tag=True,
                use_erg_lyric=True,
                use_erg_diffusion=True,
                oss_steps="",
                guidance_scale_text=0.0,
                guidance_scale_lyric=0.0,
                audio2audio_enable=use_audio2audio,
                ref_audio_input=str(ref_audio_path) if use_audio2audio else None,
                ref_audio_strength=ref_strength if use_audio2audio else 0.5,
                save_path=str(output_path),
                batch_size=1,
            )

            logger.info("acestep_geracao_concluida", output=str(output_path))
            return output_path

        except Exception as e:
            logger.error("acestep_erro_engine", error=str(e))
            logger.warning("acestep_fallback_apos_erro")
            return self._generate_placeholder(output_path, config)

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
