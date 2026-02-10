"""Orquestrador principal do pipeline de processamento."""

import time
from pathlib import Path
from typing import Callable

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from api.websocket import publish_progress
from models.project import PipelineStep, Project, ProjectStatus

logger = structlog.get_logger()

# Ordem das etapas do pipeline
PIPELINE_ORDER: list[PipelineStep] = [
    PipelineStep.UPLOAD,
    PipelineStep.SEPARATION,
    PipelineStep.ANALYSIS,
    PipelineStep.MELODY,
    PipelineStep.SYNTHESIS,
    PipelineStep.REFINEMENT,
    PipelineStep.MIX,
]

# Tipo para callback de progresso
ProgressCallback = Callable[[int, str], None]


class PipelineOrchestrator:
    """Gerencia a execução do pipeline de processamento vocal."""

    def _make_progress_fn(
        self, project_id: str, step: str, project: Project, db: AsyncSession
    ) -> ProgressCallback:
        """Cria função de callback para reportar progresso via Redis + DB."""
        start_time = time.time()

        def report_progress(percent: int, message: str = "") -> None:
            elapsed = time.time() - start_time
            eta = None
            if 0 < percent < 100 and elapsed > 0:
                eta = round((elapsed / percent) * (100 - percent))

            # Publicar via Redis (chega ao browser via WebSocket)
            publish_progress(
                project_id, step, percent,
                message=message, status="processing",
                eta_seconds=eta, elapsed_seconds=round(elapsed),
            )

            # Atualizar DB para polling funcionar também
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # Se já estamos num event loop, atualizar sync
                project.progress = percent
            else:
                project.progress = percent

        return report_progress

    async def run_full_pipeline(
        self, project_id: str, db: AsyncSession
    ) -> None:
        """Executa o pipeline completo para um projeto."""
        project = await db.get(Project, project_id)
        if not project:
            logger.error("projeto_nao_encontrado", project_id=project_id)
            return

        logger.info("pipeline_completo_iniciado", project_id=project_id)

        engine = project.synthesis_engine or "diffsinger"

        has_vocals = project.has_vocals or False

        for step in PIPELINE_ORDER:
            if step == PipelineStep.UPLOAD:
                continue

            # Separação só é necessária quando o áudio contém vocal
            if step == PipelineStep.SEPARATION and not has_vocals:
                logger.info(
                    "step_pulado_sem_vocal",
                    project_id=project_id,
                    step=step.value,
                )
                continue

            # ACE-Step usa text2music — não precisa de melodia (gera do prompt)
            if engine == "acestep" and step == PipelineStep.MELODY:
                logger.info(
                    "step_pulado_acestep",
                    project_id=project_id,
                    step=step.value,
                )
                continue

            try:
                publish_progress(
                    project_id, step.value, 0,
                    message=f"Iniciando {step.value}...", status="processing",
                )
                await self.run_step(project, step, db)
                publish_progress(
                    project_id, step.value, 100,
                    message=f"{step.value} concluido", status="completed",
                )
            except Exception as e:
                project.status = ProjectStatus.ERROR
                project.error_message = f"Erro no step {step.value}: {str(e)}"
                await db.commit()
                publish_progress(
                    project_id, "error", 0,
                    message=f"Erro no step {step.value}: {str(e)}", status="error",
                )
                logger.error(
                    "pipeline_erro",
                    project_id=project_id,
                    step=step.value,
                    error=str(e),
                )
                return

        project.status = ProjectStatus.COMPLETED
        project.progress = 100
        await db.commit()
        publish_progress(
            project_id, "completed", 100,
            message="Pipeline concluido!", status="completed",
        )
        logger.info("pipeline_completo_concluido", project_id=project_id)

    async def run_step(
        self, project: Project, step: PipelineStep, db: AsyncSession
    ) -> None:
        """Executa uma etapa específica do pipeline."""
        logger.info(
            "step_iniciado", project_id=project.id, step=step.value
        )

        project.current_step = step
        project.progress = 0
        await db.commit()

        progress_fn = self._make_progress_fn(project.id, step.value, project, db)

        step_handlers = {
            PipelineStep.SEPARATION: self._run_separation,
            PipelineStep.ANALYSIS: self._run_analysis,
            PipelineStep.MELODY: self._run_melody,
            PipelineStep.SYNTHESIS: self._run_synthesis,
            PipelineStep.REFINEMENT: self._run_refinement,
            PipelineStep.MIX: self._run_mix,
        }

        handler = step_handlers.get(step)
        if handler:
            await handler(project, db, progress_fn)

        project.progress = 100
        await db.commit()

        logger.info(
            "step_concluido", project_id=project.id, step=step.value
        )

    async def _run_separation(
        self, project: Project, db: AsyncSession, progress: ProgressCallback
    ) -> None:
        """Separa vocal e instrumental usando Demucs."""
        from config import settings
        from services.demucs import DemucsService

        project_dir = settings.projects_path / project.id
        input_path = project_dir / f"instrumental.{project.audio_format}"

        progress(5, "Inicializando Demucs...")

        svc = DemucsService()

        def demucs_progress(pct: int, msg: str) -> None:
            progress(pct, msg)

        result = await svc.separate(input_path, project_dir, demucs_progress)

        # Renomear: o "instrumental" original vira "original" e o separado vira o novo instrumental
        original_path = project_dir / f"original.{project.audio_format}"
        input_path.rename(original_path)

        # O instrumental separado (sem vocal) se torna o novo "instrumental.wav"
        import shutil
        separated_instrumental = result["instrumental"]
        new_instrumental = project_dir / "instrumental.wav"
        shutil.copy2(separated_instrumental, new_instrumental)

        # Atualizar formato do instrumental no projeto (agora é wav)
        project.audio_format = "wav"

        progress(95, "Separacao concluida — vocal e instrumental extraidos")
        logger.info(
            "separacao_concluida",
            project_id=project.id,
            vocals=str(result.get("vocals")),
            instrumental=str(result.get("instrumental")),
        )

    async def _run_analysis(
        self, project: Project, db: AsyncSession, progress: ProgressCallback
    ) -> None:
        """Executa análise de áudio."""
        from config import settings
        from services.analyzer import AudioAnalyzer

        progress(10, "Carregando arquivo de audio...")

        analyzer = AudioAnalyzer()
        # Usar o instrumental (original ou separado)
        file_path = (
            settings.projects_path
            / project.id
            / f"instrumental.{project.audio_format}"
        )

        progress(20, "Detectando BPM e tonalidade...")
        analysis = await analyzer.analyze(file_path)

        progress(85, "Salvando resultados...")

        project.duration_seconds = analysis.duration_seconds
        project.sample_rate = analysis.sample_rate
        project.bpm = analysis.bpm
        project.musical_key = analysis.musical_key
        project.status = ProjectStatus.MELODY_READY

        progress(95, "Analise completa")

    async def _run_melody(
        self, project: Project, db: AsyncSession, progress: ProgressCallback
    ) -> None:
        """Extrai melodia MIDI — da vocal separada (se disponível) ou do instrumental."""
        from config import settings
        from services.melody import MelodyService

        progress(5, "Inicializando extracao de melodia...")

        melody_svc = MelodyService()
        project_dir = settings.projects_path / project.id

        # Preferir vocal separada (muito melhor para extrair melodia)
        vocals_path = project_dir / "vocals.wav"
        if vocals_path.exists() and project.has_vocals:
            audio_path = vocals_path
            source = "vocal separada"
        else:
            audio_path = project_dir / f"instrumental.{project.audio_format}"
            source = "instrumental"

        bpm = project.bpm or 120.0

        progress(15, f"Extraindo melodia da {source}...")
        logger.info("melody_source", source=source, path=str(audio_path))
        melody = await melody_svc.extract_melody_from_audio(audio_path, bpm)

        progress(60, "Salvando MIDI e JSON...")
        project_dir = settings.projects_path / project.id
        melody_svc.save_melody_json(melody, project_dir / "melody.json")
        await melody_svc.export_midi(melody, project_dir / "melody.mid")

        if project.lyrics:
            progress(75, "Associando silabas a melodia...")
            from services.syllable import SyllableService
            syllable_svc = SyllableService()
            syllables = await syllable_svc.syllabify_text(
                project.lyrics, project.language or "it"
            )
            melody_svc.assign_lyrics_to_notes(melody, syllables)
            melody_svc.save_melody_json(melody, project_dir / "melody.json")
            await melody_svc.export_midi(melody, project_dir / "melody.mid")

        progress(95, f"Melodia extraida — {len(melody.notes)} notas")
        logger.info("melody_gerada", project_id=project.id, notes=len(melody.notes))

    async def _run_synthesis(
        self, project: Project, db: AsyncSession, progress: ProgressCallback
    ) -> None:
        """Sintetiza vocal usando DiffSinger ou ACE-Step."""
        from config import settings

        project.status = ProjectStatus.SYNTHESIZING

        project_dir = settings.projects_path / project.id
        melody_json = project_dir / "melody.json"
        output_path = project_dir / "vocals_raw.wav"

        engine = project.synthesis_engine or "diffsinger"
        language = project.language or "it"

        progress(5, f"Inicializando engine {engine}...")

        if engine == "diffsinger":
            from services.diffsinger import DiffSingerConfig, DiffSingerService

            # Carregar vocal_config.json se existir
            vocal_config_path = project_dir / "vocal_config.json"
            vocal_params = {}
            if vocal_config_path.exists():
                import json
                with open(vocal_config_path) as f:
                    vocal_params = json.load(f)

            # Se voice_preset tem voicebank mapeado, usar
            voicebank = project.voice_model or "umidaji"
            voice_preset_id = vocal_params.get("voice_preset", "")
            if voice_preset_id:
                from api.routes.voices import VOICE_PRESETS
                preset = next((p for p in VOICE_PRESETS if p["id"] == voice_preset_id), None)
                if preset and preset.get("voicebank"):
                    voicebank = preset["voicebank"]

            svc = DiffSingerService()
            config = DiffSingerConfig(
                voicebank=voicebank,
                language=language,
                gender=vocal_params.get("gender", 0.0) / 100.0,
                energy=vocal_params.get("energy", 60.0) / 100.0,
                breathiness=vocal_params.get("breathiness", 0.0) / 100.0,
                tension=vocal_params.get("tension", 50.0) / 100.0,
            )

            progress(15, "Carregando voicebank...")
            progress(30, "Gerando espectrograma mel...")
            await svc.synthesize(melody_json, output_path, config)
            progress(90, "Convertendo para audio...")

        elif engine == "acestep":
            from services.acestep import (
                ACEStepConfig, ACEStepService,
                build_acestep_prompt, format_lyrics_for_acestep,
            )

            # Carregar vocal_config.json para estilo e gênero
            vocal_config_path = project_dir / "vocal_config.json"
            vocal_style = "pop"
            gender_value = 50.0
            voice_preset_id = ""
            if vocal_config_path.exists():
                import json
                with open(vocal_config_path) as f:
                    vc = json.load(f)
                    vocal_style = vc.get("vocal_style", "pop")
                    gender_value = vc.get("gender", 50.0)
                    voice_preset_id = vc.get("voice_preset", "")

            # Determinar gênero textual a partir do valor numérico
            if gender_value <= 35:
                gender_str = "male"
            elif gender_value >= 65:
                gender_str = "female"
            else:
                gender_str = "neutral"

            # Buscar tags do voice preset se disponível
            voice_tags = None
            if voice_preset_id:
                from api.routes.voices import VOICE_PRESETS
                preset = next((p for p in VOICE_PRESETS if p["id"] == voice_preset_id), None)
                if preset:
                    voice_tags = preset.get("tags")
                    gender_str = preset.get("gender", gender_str)

            # Construir prompt e formatar lyrics
            prompt = build_acestep_prompt(
                language=language,
                bpm=project.bpm,
                musical_key=project.musical_key,
                vocal_style=vocal_style,
                gender=gender_str,
                voice_tags=voice_tags,
            )
            formatted_lyrics = format_lyrics_for_acestep(project.lyrics or "")

            svc = ACEStepService()
            config = ACEStepConfig(
                lyrics=formatted_lyrics,
                language=language,
                duration_seconds=project.duration_seconds or 30.0,
                prompt=prompt,
            )

            has_vocals = project.has_vocals or False
            original_vocals_path = project_dir / "vocals.wav"

            if has_vocals and original_vocals_path.exists():
                # ---- MODO VOICE REPLACEMENT ----
                # Audio com vocal original → audio2audio usa VOCAL como referência
                # Mantém timing/melodia do vocal original, muda a voz
                logger.info(
                    "acestep_voice_replacement",
                    prompt=prompt,
                    ref_vocal=str(original_vocals_path),
                    duration=config.duration_seconds,
                )
                progress(15, "Carregando modelo ACE-Step (3.5B)...")
                full_music_path = project_dir / "acestep_full.wav"
                progress(30, "Substituindo voz (audio2audio com vocal ref)...")
                await svc.generate(
                    full_music_path, config,
                    ref_audio_path=original_vocals_path,
                    ref_strength=0.5,
                )
            else:
                # ---- MODO TEXT2MUSIC ----
                # Instrumental sem vocal → gera música do zero com vocal
                # Nota: vocal não sincroniza com instrumental original
                logger.info(
                    "acestep_text2music",
                    prompt=prompt,
                    lyrics_len=len(formatted_lyrics),
                    duration=config.duration_seconds,
                )
                progress(15, "Carregando modelo ACE-Step (3.5B)...")
                full_music_path = project_dir / "acestep_full.wav"
                progress(30, "Gerando musica com vocal (text2music)...")
                await svc.generate(full_music_path, config)

            # Extrair vocal isolado usando Demucs (em subdir para não sobrescrever)
            progress(70, "Extraindo vocal com Demucs...")
            from services.demucs import DemucsService
            import shutil
            demucs_svc = DemucsService()
            acestep_demucs_dir = project_dir / "acestep_demucs"
            acestep_demucs_dir.mkdir(exist_ok=True)
            demucs_result = await demucs_svc.separate(
                full_music_path, acestep_demucs_dir,
                lambda pct, msg: progress(70 + pct // 5, f"Demucs: {msg}"),
            )
            separated_vocals = demucs_result.get("vocals")
            if separated_vocals and Path(separated_vocals).exists():
                shutil.copy2(separated_vocals, output_path)
                logger.info(
                    "acestep_vocal_extraido",
                    project_id=project.id,
                    source=str(separated_vocals),
                )
            else:
                logger.warning("acestep_vocal_nao_extraido", project_id=project.id)

            progress(90, "Vocal extraido com sucesso")

        progress(95, "Sintese concluida")
        logger.info("sintese_concluida", project_id=project.id, engine=engine)

    async def _run_refinement(
        self, project: Project, db: AsyncSession, progress: ProgressCallback
    ) -> None:
        """Refina timbre vocal usando RVC/Applio."""
        from config import settings
        from services.rvc import RVCConfig, RVCService

        project.status = ProjectStatus.REFINING
        project_dir = settings.projects_path / project.id
        input_path = project_dir / "vocals_raw.wav"
        output_path = project_dir / "vocals_refined.wav"

        if not input_path.exists():
            progress(50, "Sem vocal para refinar, pulando...")
            logger.warning("refinement_bypass_sem_vocal", project_id=project.id)
            return

        progress(10, "Carregando vocal bruto...")
        svc = RVCService()
        config = RVCConfig(model_name=project.voice_model or "")

        progress(30, "Aplicando conversao de timbre...")
        await svc.convert(input_path, output_path, config)

        progress(90, "Refinamento aplicado")
        logger.info("refinement_concluido", project_id=project.id)

    async def _run_mix(
        self, project: Project, db: AsyncSession, progress: ProgressCallback
    ) -> None:
        """Mixagem final com Pedalboard."""
        from config import settings

        project.status = ProjectStatus.MIXING
        project_dir = settings.projects_path / project.id
        output_path = project_dir / "mix_final.wav"
        engine = project.synthesis_engine or "diffsinger"

        from services.mixer import MixConfig, MixerService

        vocal_path = project_dir / "vocals_refined.wav"
        if not vocal_path.exists():
            vocal_path = project_dir / "vocals_raw.wav"
        if not vocal_path.exists():
            progress(50, "Sem vocal para mixar, pulando...")
            logger.warning("mix_bypass_sem_vocal", project_id=project.id)
            return

        instrumental_path = None
        if project.audio_format:
            instrumental_path = project_dir / f"instrumental.{project.audio_format}"
        if not instrumental_path or not instrumental_path.exists():
            progress(50, "Sem instrumental para mixar, pulando...")
            logger.warning("mix_bypass_sem_instrumental", project_id=project.id)
            return

        progress(10, "Carregando faixas de audio...")
        svc = MixerService()
        config = MixConfig()

        progress(30, "Aplicando EQ e compressao no vocal...")
        progress(50, "Ajustando niveis e panorama...")
        await svc.mix(vocal_path, instrumental_path, output_path, config)

        progress(90, "Exportando mix final...")
        logger.info("mix_concluido", project_id=project.id)
