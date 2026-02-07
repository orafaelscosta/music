"""Orquestrador principal do pipeline de processamento."""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

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
                await self.run_step(project, step, db)
            except Exception as e:
                project.status = ProjectStatus.ERROR
                project.error_message = f"Erro no step {step.value}: {str(e)}"
                await db.commit()
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
        """Sintetiza vocal — placeholder para Fase 3."""
        logger.info("synthesis_placeholder", project_id=project.id)
        project.status = ProjectStatus.SYNTHESIZING
        # Será implementado na Fase 3 com DiffSinger/ACE-Step

    async def _run_refinement(self, project: Project, db: AsyncSession) -> None:
        """Refina timbre vocal — placeholder para Fase 4."""
        logger.info("refinement_placeholder", project_id=project.id)
        project.status = ProjectStatus.REFINING
        # Será implementado na Fase 4 com Applio/RVC

    async def _run_mix(self, project: Project, db: AsyncSession) -> None:
        """Mixagem final — placeholder para Fase 5."""
        logger.info("mix_placeholder", project_id=project.id)
        project.status = ProjectStatus.MIXING
        # Será implementado na Fase 5 com Pedalboard
