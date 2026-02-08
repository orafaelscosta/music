"""Rotas CRUD de projetos."""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from database import get_db
from models.project import Project

logger = structlog.get_logger()
router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
) -> Project:
    """Cria um novo projeto de vocal."""
    # Aplicar configurações do template, se fornecido
    synthesis_engine = data.synthesis_engine or "diffsinger"
    description = data.description

    if data.template_id:
        from api.routes.templates import PROJECT_TEMPLATES

        template = next(
            (t for t in PROJECT_TEMPLATES if t["id"] == data.template_id), None
        )
        if template:
            synthesis_engine = template["synthesis_engine"]
            if not description:
                description = template["description"]

    project = Project(
        name=data.name,
        description=description,
        language=data.language,
        synthesis_engine=synthesis_engine,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    logger.info("projeto_criado", project_id=project.id, name=project.name)
    return project


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Lista todos os projetos."""
    result = await db.execute(
        select(Project).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()
    return {"projects": projects, "total": len(projects)}


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> Project:
    """Busca um projeto pelo ID."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
) -> Project:
    """Atualiza dados de um projeto."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)
    logger.info("projeto_atualizado", project_id=project.id, fields=list(update_data.keys()))
    return project


@router.post("/{project_id}/duplicate", response_model=ProjectResponse, status_code=201)
async def duplicate_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> Project:
    """Duplica um projeto existente (sem arquivos de áudio)."""
    original = await db.get(Project, project_id)
    if not original:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    new_project = Project(
        name=f"{original.name} (cópia)",
        description=original.description,
        language=original.language,
        synthesis_engine=original.synthesis_engine,
        voice_model=original.voice_model,
        lyrics=original.lyrics,
    )
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)
    logger.info(
        "projeto_duplicado",
        original_id=project_id,
        new_id=new_project.id,
    )
    return new_project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove um projeto e seus arquivos."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    # Remove arquivos do storage
    from config import settings
    project_dir = settings.projects_path / project_id
    if project_dir.exists():
        import shutil
        shutil.rmtree(project_dir)

    await db.delete(project)
    await db.commit()
    logger.info("projeto_removido", project_id=project_id)
