"""Rotas de controle do pipeline de processamento."""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import ProjectResponse
from database import get_db
from models.project import PipelineStep, Project, ProjectStatus

logger = structlog.get_logger()
router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/{project_id}/start", response_model=ProjectResponse)
async def start_pipeline(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> Project:
    """Inicia o pipeline automático completo (one-click)."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    if not project.instrumental_filename:
        raise HTTPException(
            status_code=400, detail="Upload do instrumental necessário antes de iniciar"
        )

    if project.status in (ProjectStatus.SYNTHESIZING, ProjectStatus.REFINING, ProjectStatus.MIXING):
        raise HTTPException(status_code=409, detail="Pipeline já em execução")

    # Dispara task Celery para processamento completo
    from workers.tasks import run_full_pipeline

    run_full_pipeline.delay(project_id)

    project.status = ProjectStatus.ANALYZING
    project.current_step = PipelineStep.ANALYSIS
    project.progress = 0
    await db.commit()
    await db.refresh(project)

    logger.info("pipeline_iniciado", project_id=project_id)
    return project


@router.post("/{project_id}/step/{step}", response_model=ProjectResponse)
async def run_pipeline_step(
    project_id: str,
    step: PipelineStep,
    db: AsyncSession = Depends(get_db),
) -> Project:
    """Executa um passo específico do pipeline."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    # Validar pré-requisitos por step
    step_prerequisites: dict[PipelineStep, list[str]] = {
        PipelineStep.ANALYSIS: ["instrumental_filename"],
        PipelineStep.MELODY: ["bpm"],
        PipelineStep.SYNTHESIS: ["lyrics"],
        PipelineStep.REFINEMENT: [],
        PipelineStep.MIX: [],
    }

    missing = [
        field
        for field in step_prerequisites.get(step, [])
        if not getattr(project, field, None)
    ]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Pré-requisitos faltando: {', '.join(missing)}",
        )

    # Dispara task Celery para o step específico
    from workers.tasks import run_pipeline_step as run_step_task

    run_step_task.delay(project_id, step.value)

    project.current_step = step
    project.progress = 0
    await db.commit()
    await db.refresh(project)

    logger.info("pipeline_step_iniciado", project_id=project_id, step=step.value)
    return project


@router.get("/{project_id}/status")
async def get_pipeline_status(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retorna o status atual do pipeline."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    # Verificar quais arquivos existem para determinar steps completos
    from config import settings

    project_dir = settings.projects_path / project_id
    files_exist = {}
    for filename in [
        "instrumental", "melody.mid", "melody.json", "vocals_raw.wav",
        "vocals_refined.wav", "mix_final.wav",
    ]:
        if filename == "instrumental":
            files_exist[filename] = bool(
                project.audio_format
                and (project_dir / f"instrumental.{project.audio_format}").exists()
            )
        else:
            files_exist[filename] = (project_dir / filename).exists()

    return {
        "project_id": project_id,
        "status": project.status,
        "current_step": project.current_step,
        "progress": project.progress,
        "error_message": project.error_message,
        "files": files_exist,
        "steps": {
            "upload": {
                "completed": files_exist.get("instrumental", False),
                "available": True,
            },
            "analysis": {
                "completed": project.bpm is not None,
                "available": files_exist.get("instrumental", False),
            },
            "melody": {
                "completed": files_exist.get("melody.mid", False),
                "available": project.bpm is not None,
            },
            "synthesis": {
                "completed": files_exist.get("vocals_raw.wav", False),
                "available": files_exist.get("melody.mid", False),
            },
            "refinement": {
                "completed": files_exist.get("vocals_refined.wav", False),
                "available": files_exist.get("vocals_raw.wav", False),
            },
            "mix": {
                "completed": files_exist.get("mix_final.wav", False),
                "available": files_exist.get("vocals_raw.wav", False)
                or files_exist.get("vocals_refined.wav", False),
            },
        },
    }
