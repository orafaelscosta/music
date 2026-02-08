"""Orquestrador principal do pipeline de processamento."""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from api.websocket import manager
from models.project import PipelineStep, Project, ProjectStatus

logger = structlog.get_logger()

# Ordem das etapas do pipeline
PIPELINE_ORDER: list[PipelineStep] = [
    PipelineStep.UPLOAD,
    PipelineStep.ANALYSIS,
    PipelineStep.MELODY,
    PipelineStep.SYNTHESIS,
    PipelineStep.REFINEMENT,
    PipelineStep.MIX,
]


class PipelineOrchestrator:
    """Gerencia a execução do pipeline de processamento vocal."""

    async def run_full_pipeline(
        self, project_id: str, db: AsyncSession
    ) -> None:
        """Executa o pipeline completo para um projeto."""
        project = await db.get(Project, project_id)
        if not project:
            logger.error("projeto_nao_encontrado", project_id=project_id)
            return

        logger.info("pipeline_completo_iniciado", project_id=project_id)

        for step in PIPELINE_ORDER:
            if step == PipelineStep.UPLOAD:
                continue  # Upload já foi feito

            try:
                await manager.send_progress(
                    project_id, step.value, 0,
                    message=f"Iniciando {step.value}...", status="processing",
                )
                await self.run_step(project, step, db)
                await manager.send_progress(
                    project_id, step.value, 100,
                    message=f"{step.value} concluído", status="completed",
                )
            except Exception as e:
                project.status = ProjectStatus.ERROR
                project.error_message = f"Erro no step {step.value}: {str(e)}"
                await db.commit()
                await manager.broadcast_error(
                    project_id, f"Erro no step {step.value}: {str(e)}"
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
        await manager.send_progress(
            project_id, "completed", 100,
            message="Pipeline concluído!", status="completed",
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

        step_handlers = {
            PipelineStep.ANALYSIS: self._run_analysis,
            PipelineStep.MELODY: self._run_melody,
            PipelineStep.SYNTHESIS: self._run_synthesis,
            PipelineStep.REFINEMENT: self._run_refinement,
            PipelineStep.MIX: self._run_mix,
        }

        handler = step_handlers.get(step)
        if handler:
            await handler(project, db)

        project.progress = 100
        await db.commit()

        logger.info(
            "step_concluido", project_id=project.id, step=step.value
        )

    async def _run_analysis(self, project: Project, db: AsyncSession) -> None:
        """Executa análise de áudio."""
        from config import settings
        from services.analyzer import AudioAnalyzer

        analyzer = AudioAnalyzer()
        file_path = (
            settings.projects_path
            / project.id
            / f"instrumental.{project.audio_format}"
        )
        analysis = await analyzer.analyze(file_path)

        project.duration_seconds = analysis.duration_seconds
        project.sample_rate = analysis.sample_rate
        project.bpm = analysis.bpm
        project.musical_key = analysis.musical_key
        project.status = ProjectStatus.MELODY_READY

    async def _run_melody(self, project: Project, db: AsyncSession) -> None:
        """Extrai melodia MIDI do instrumental."""
        from config import settings
        from services.melody import MelodyService

        melody_svc = MelodyService()
        audio_path = (
            settings.projects_path
            / project.id
            / f"instrumental.{project.audio_format}"
        )
        bpm = project.bpm or 120.0
        melody = await melody_svc.extract_melody_from_audio(audio_path, bpm)

        project_dir = settings.projects_path / project.id
        melody_svc.save_melody_json(melody, project_dir / "melody.json")
        await melody_svc.export_midi(melody, project_dir / "melody.mid")

        # Associar sílabas se houver letra
        if project.lyrics:
            from services.syllable import SyllableService
            syllable_svc = SyllableService()
            syllables = await syllable_svc.syllabify_text(
                project.lyrics, project.language or "it"
            )
            melody_svc.assign_lyrics_to_notes(melody, syllables)
            melody_svc.save_melody_json(melody, project_dir / "melody.json")
            await melody_svc.export_midi(melody, project_dir / "melody.mid")

        logger.info("melody_gerada", project_id=project.id, notes=len(melody.notes))

    async def _run_synthesis(self, project: Project, db: AsyncSession) -> None:
        """Sintetiza vocal usando DiffSinger ou ACE-Step."""
        from config import settings

        project.status = ProjectStatus.SYNTHESIZING

        project_dir = settings.projects_path / project.id
        melody_json = project_dir / "melody.json"
        output_path = project_dir / "vocals_raw.wav"

        engine = project.synthesis_engine or "diffsinger"
        language = project.language or "it"

        if engine == "diffsinger":
            from services.diffsinger import DiffSingerConfig, DiffSingerService

            svc = DiffSingerService()
            config = DiffSingerConfig(
                voicebank=project.voice_model or "leif",
                language=language,
            )
            await svc.synthesize(melody_json, output_path, config)

        elif engine == "acestep":
            from services.acestep import ACEStepConfig, ACEStepService

            svc = ACEStepService()
            config = ACEStepConfig(
                lyrics=project.lyrics or "",
                language=language,
                duration_seconds=project.duration_seconds or 30.0,
            )
            instrumental_path = None
            if project.audio_format:
                instrumental_path = project_dir / f"instrumental.{project.audio_format}"
            await svc.generate(output_path, config, instrumental_path)

        logger.info("sintese_concluida", project_id=project.id, engine=engine)

    async def _run_refinement(self, project: Project, db: AsyncSession) -> None:
        """Refina timbre vocal usando RVC/Applio."""
        from config import settings
        from services.rvc import RVCConfig, RVCService

        project.status = ProjectStatus.REFINING
        project_dir = settings.projects_path / project.id
        input_path = project_dir / "vocals_raw.wav"
        output_path = project_dir / "vocals_refined.wav"

        if not input_path.exists():
            # Bypass se não houver vocal sintetizado
            logger.warning("refinement_bypass_sem_vocal", project_id=project.id)
            return

        svc = RVCService()
        config = RVCConfig(model_name=project.voice_model or "")
        await svc.convert(input_path, output_path, config)

        logger.info("refinement_concluido", project_id=project.id)

    async def _run_mix(self, project: Project, db: AsyncSession) -> None:
        """Mixagem final com Pedalboard."""
        from config import settings
        from services.mixer import MixConfig, MixerService

        project.status = ProjectStatus.MIXING
        project_dir = settings.projects_path / project.id

        # Determinar vocal (refinado ou raw)
        vocal_path = project_dir / "vocals_refined.wav"
        if not vocal_path.exists():
            vocal_path = project_dir / "vocals_raw.wav"
        if not vocal_path.exists():
            logger.warning("mix_bypass_sem_vocal", project_id=project.id)
            return

        # Determinar instrumental
        instrumental_path = None
        if project.audio_format:
            instrumental_path = project_dir / f"instrumental.{project.audio_format}"
        if not instrumental_path or not instrumental_path.exists():
            logger.warning("mix_bypass_sem_instrumental", project_id=project.id)
            return

        output_path = project_dir / "mix_final.wav"

        svc = MixerService()
        config = MixConfig()  # Preset balanced (padrão)
        await svc.mix(vocal_path, instrumental_path, output_path, config)

        logger.info("mix_concluido", project_id=project.id)
