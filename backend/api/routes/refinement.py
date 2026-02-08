"""Rotas de refinamento vocal — conversão de timbre com RVC/Applio."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.project import PipelineStep, Project, ProjectStatus

logger = structlog.get_logger()
router = APIRouter(prefix="/refinement", tags=["refinement"])


class RefinementRequest(BaseModel):
    """Parâmetros de conversão de timbre vocal."""

    model_name: str = ""
    pitch_shift: int = Field(default=0, ge=-24, le=24)
    index_rate: float = Field(default=0.75, ge=0.0, le=1.0)
    filter_radius: int = Field(default=3, ge=0, le=7)
    rms_mix_rate: float = Field(default=0.25, ge=0.0, le=1.0)
    protect: float = Field(default=0.33, ge=0.0, le=0.5)
    f0_method: str = Field(default="rmvpe", pattern="^(rmvpe|crepe|harvest|pm)$")


class RefinementResponse(BaseModel):
    """Resposta do refinamento vocal."""

    status: str
    model_name: str
    output_file: str
    download_url: str


@router.post("/{project_id}/convert", response_model=RefinementResponse)
async def convert_vocal(
    project_id: str,
    params: RefinementRequest,
    db: AsyncSession = Depends(get_db),
) -> RefinementResponse:
    """Converte o timbre do vocal usando RVC/Applio."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    project_dir = settings.projects_path / project_id
    input_path = project_dir / "vocals_raw.wav"
    if not input_path.exists():
        raise HTTPException(status_code=400, detail="Vocal não sintetizado ainda")

    output_file = "vocals_refined.wav"
    output_path = project_dir / output_file

    project.status = ProjectStatus.REFINING
    project.current_step = PipelineStep.REFINEMENT
    project.progress = 0
    await db.commit()

    try:
        from services.rvc import RVCConfig, RVCService

        svc = RVCService()
        config = RVCConfig(
            model_name=params.model_name,
            pitch_shift=params.pitch_shift,
            index_rate=params.index_rate,
            filter_radius=params.filter_radius,
            rms_mix_rate=params.rms_mix_rate,
            protect=params.protect,
            f0_method=params.f0_method,
        )
        await svc.convert(input_path, output_path, config)

    except Exception as e:
        project.status = ProjectStatus.ERROR
        project.error_message = f"Erro no refinamento: {str(e)}"
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Erro no refinamento: {str(e)}")

    project.status = ProjectStatus.MIXING
    project.current_step = PipelineStep.MIX
    project.progress = 100
    await db.commit()

    logger.info("refinamento_concluido", project_id=project_id, model=params.model_name)

    return RefinementResponse(
        status="completed",
        model_name=params.model_name,
        output_file=output_file,
        download_url=f"/api/audio/{project_id}/{output_file}",
    )


@router.post("/{project_id}/bypass")
async def bypass_refinement(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Pula o refinamento — copia vocal raw como refined."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    project_dir = settings.projects_path / project_id
    raw_path = project_dir / "vocals_raw.wav"
    refined_path = project_dir / "vocals_refined.wav"

    if not raw_path.exists():
        raise HTTPException(status_code=400, detail="Vocal não sintetizado ainda")

    import shutil
    shutil.copy2(raw_path, refined_path)

    project.current_step = PipelineStep.MIX
    project.status = ProjectStatus.MIXING
    await db.commit()

    logger.info("refinamento_bypass", project_id=project_id)
    return {"status": "bypassed", "output_file": "vocals_refined.wav"}


@router.get("/{project_id}/models")
async def list_rvc_models(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Lista modelos RVC disponíveis para conversão."""
    from services.rvc import RVCService

    svc = RVCService()
    models = svc.list_models()
    return {"models": models, "total": len(models)}


@router.post("/{project_id}/models/upload")
async def upload_rvc_model(
    project_id: str,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload de modelo RVC customizado (.pth)."""
    if not file.filename or not file.filename.endswith(".pth"):
        raise HTTPException(status_code=400, detail="Apenas arquivos .pth são aceitos")

    models_dir = settings.applio_path / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    model_path = models_dir / file.filename

    with open(model_path, "wb") as f:
        f.write(content)

    logger.info("modelo_rvc_uploaded", filename=file.filename)
    return {"status": "uploaded", "model_name": model_path.stem, "path": str(model_path)}


@router.get("/{project_id}/compare")
async def get_comparison_files(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retorna URLs para comparação A/B (antes/depois do refinamento)."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    project_dir = settings.projects_path / project_id

    result = {
        "before": None,
        "after": None,
    }

    raw_path = project_dir / "vocals_raw.wav"
    refined_path = project_dir / "vocals_refined.wav"

    if raw_path.exists():
        result["before"] = {
            "file": "vocals_raw.wav",
            "download_url": f"/api/audio/{project_id}/vocals_raw.wav",
        }

    if refined_path.exists():
        result["after"] = {
            "file": "vocals_refined.wav",
            "download_url": f"/api/audio/{project_id}/vocals_refined.wav",
        }

    return result
