"""Rotas de batch processing — processamento em lote."""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.project import Project, ProjectStatus

logger = structlog.get_logger()
router = APIRouter(prefix="/batch", tags=["batch"])


class BatchRequest(BaseModel):
    """Requisição de processamento em lote."""

    project_ids: list[str]


class BatchResponse(BaseModel):
    """Resposta do batch processing."""

    started: list[str]
    skipped: list[str]
    errors: list[dict]


@router.post("/start", response_model=BatchResponse)
async def batch_start_pipeline(
    data: BatchRequest,
    db: AsyncSession = Depends(get_db),
) -> BatchResponse:
    """Inicia pipeline para múltiplos projetos."""
    from workers.tasks import run_full_pipeline

    started = []
    skipped = []
    errors = []

    for project_id in data.project_ids:
        project = await db.get(Project, project_id)
        if not project:
            errors.append({"project_id": project_id, "error": "Projeto não encontrado"})
            continue

        if not project.instrumental_filename:
            skipped.append(project_id)
            continue

        if project.status in (
            ProjectStatus.SYNTHESIZING,
            ProjectStatus.REFINING,
            ProjectStatus.MIXING,
        ):
            skipped.append(project_id)
            continue

        try:
            run_full_pipeline.delay(project_id)
            project.status = ProjectStatus.ANALYZING
            project.progress = 0
            await db.commit()
            started.append(project_id)
        except Exception as e:
            errors.append({"project_id": project_id, "error": str(e)})

    logger.info(
        "batch_iniciado",
        started=len(started),
        skipped=len(skipped),
        errors=len(errors),
    )
    return BatchResponse(started=started, skipped=skipped, errors=errors)


@router.get("/status")
async def batch_status(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retorna status resumido de todos os projetos."""
    result = await db.execute(select(Project))
    projects = result.scalars().all()

    summary = {
        "total": len(projects),
        "by_status": {},
        "processing": [],
    }

    for project in projects:
        status_key = project.status.value if project.status else "unknown"
        summary["by_status"][status_key] = summary["by_status"].get(status_key, 0) + 1

        if project.status in (
            ProjectStatus.ANALYZING,
            ProjectStatus.SYNTHESIZING,
            ProjectStatus.REFINING,
            ProjectStatus.MIXING,
        ):
            summary["processing"].append({
                "id": project.id,
                "name": project.name,
                "status": status_key,
                "step": project.current_step.value if project.current_step else None,
                "progress": project.progress,
            })

    return summary
