"""Rotas de mixagem e exportação — cadeia de efeitos com Pedalboard."""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.project import PipelineStep, Project, ProjectStatus

logger = structlog.get_logger()
router = APIRouter(prefix="/mix", tags=["mix"])


class MixRequest(BaseModel):
    """Parâmetros de mixagem."""

    vocal_gain_db: float = Field(default=0.0, ge=-24.0, le=12.0)
    instrumental_gain_db: float = Field(default=-3.0, ge=-24.0, le=12.0)
    eq_low_gain_db: float = Field(default=0.0, ge=-12.0, le=12.0)
    eq_mid_gain_db: float = Field(default=2.0, ge=-12.0, le=12.0)
    eq_high_gain_db: float = Field(default=1.0, ge=-12.0, le=12.0)
    compressor_threshold_db: float = Field(default=-18.0, ge=-40.0, le=0.0)
    compressor_ratio: float = Field(default=3.0, ge=1.0, le=20.0)
    reverb_room_size: float = Field(default=0.3, ge=0.0, le=1.0)
    reverb_wet_level: float = Field(default=0.15, ge=0.0, le=1.0)
    limiter_threshold_db: float = Field(default=-1.0, ge=-12.0, le=0.0)
    preset: str | None = None


class MixResponse(BaseModel):
    """Resposta da mixagem."""

    status: str
    output_file: str
    download_url: str
    preset: str | None


class ExportRequest(BaseModel):
    """Parâmetros de exportação."""

    format: str = Field(default="wav", pattern="^(wav|mp3|flac|ogg)$")
    sample_rate: int = Field(default=44100, ge=8000, le=96000)


class ExportResponse(BaseModel):
    """Resposta da exportação."""

    status: str
    format: str
    output_file: str
    download_url: str


@router.post("/{project_id}/render", response_model=MixResponse)
async def render_mix(
    project_id: str,
    params: MixRequest,
    db: AsyncSession = Depends(get_db),
) -> MixResponse:
    """Renderiza mixagem com cadeia de efeitos."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    project_dir = settings.projects_path / project_id

    # Determinar vocal (refinado ou raw)
    vocal_path = project_dir / "vocals_refined.wav"
    if not vocal_path.exists():
        vocal_path = project_dir / "vocals_raw.wav"
    if not vocal_path.exists():
        raise HTTPException(status_code=400, detail="Vocal não disponível para mixagem")

    # Determinar instrumental
    instrumental_path = None
    if project.audio_format:
        instrumental_path = project_dir / f"instrumental.{project.audio_format}"
    if not instrumental_path or not instrumental_path.exists():
        raise HTTPException(status_code=400, detail="Instrumental não disponível")

    output_file = "mix_final.wav"
    output_path = project_dir / output_file

    project.status = ProjectStatus.MIXING
    project.current_step = PipelineStep.MIX
    project.progress = 0
    await db.commit()

    try:
        from services.mixer import MixConfig, MixerService

        svc = MixerService()

        # Usar preset se especificado
        if params.preset:
            config = MixConfig.from_preset(params.preset)
        else:
            config = MixConfig(
                vocal_gain_db=params.vocal_gain_db,
                instrumental_gain_db=params.instrumental_gain_db,
                eq_low_gain_db=params.eq_low_gain_db,
                eq_mid_gain_db=params.eq_mid_gain_db,
                eq_high_gain_db=params.eq_high_gain_db,
                compressor_threshold_db=params.compressor_threshold_db,
                compressor_ratio=params.compressor_ratio,
                reverb_room_size=params.reverb_room_size,
                reverb_wet_level=params.reverb_wet_level,
                limiter_threshold_db=params.limiter_threshold_db,
            )

        await svc.mix(vocal_path, instrumental_path, output_path, config)

    except Exception as e:
        project.status = ProjectStatus.ERROR
        project.error_message = f"Erro na mixagem: {str(e)}"
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Erro na mixagem: {str(e)}")

    project.status = ProjectStatus.COMPLETED
    project.progress = 100
    await db.commit()

    logger.info("mix_concluido", project_id=project_id, preset=params.preset)

    return MixResponse(
        status="completed",
        output_file=output_file,
        download_url=f"/api/audio/{project_id}/{output_file}",
        preset=params.preset,
    )


@router.post("/{project_id}/export", response_model=ExportResponse)
async def export_mix(
    project_id: str,
    params: ExportRequest,
    db: AsyncSession = Depends(get_db),
) -> ExportResponse:
    """Exporta mixagem em formato específico."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    project_dir = settings.projects_path / project_id
    mix_path = project_dir / "mix_final.wav"

    if not mix_path.exists():
        raise HTTPException(status_code=400, detail="Mixagem não renderizada ainda")

    output_file = f"export_{project.name or project_id}.{params.format}"
    # Sanitizar nome do arquivo
    output_file = "".join(c if c.isalnum() or c in "._-" else "_" for c in output_file)
    output_path = project_dir / output_file

    try:
        from services.mixer import MixerService

        svc = MixerService()
        await svc.export(mix_path, output_path, params.format, params.sample_rate)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na exportação: {str(e)}")

    logger.info(
        "export_concluido",
        project_id=project_id,
        format=params.format,
    )

    return ExportResponse(
        status="completed",
        format=params.format,
        output_file=output_file,
        download_url=f"/api/audio/{project_id}/{output_file}",
    )


@router.get("/{project_id}/download/{filename}")
async def download_export(
    project_id: str,
    filename: str,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Download direto do arquivo exportado."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    file_path = settings.projects_path / project_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream",
    )


@router.get("/{project_id}/presets")
async def list_presets(project_id: str) -> dict:
    """Lista presets de mixagem disponíveis."""
    from services.mixer import MixPreset

    return {"presets": MixPreset.list_presets()}


@router.get("/{project_id}/status")
async def mix_status(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Status atual da mixagem."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    project_dir = settings.projects_path / project_id

    has_vocal = (project_dir / "vocals_refined.wav").exists() or (
        project_dir / "vocals_raw.wav"
    ).exists()
    has_instrumental = bool(
        project.audio_format
        and (project_dir / f"instrumental.{project.audio_format}").exists()
    )
    has_mix = (project_dir / "mix_final.wav").exists()

    # Listar exports existentes
    exports = []
    for ext in ["wav", "mp3", "flac", "ogg"]:
        for f in project_dir.glob(f"export_*.{ext}"):
            exports.append({
                "file": f.name,
                "format": ext,
                "download_url": f"/api/audio/{project_id}/{f.name}",
            })

    return {
        "project_id": project_id,
        "status": project.status.value if project.status else "unknown",
        "has_vocal": has_vocal,
        "has_instrumental": has_instrumental,
        "has_mix": has_mix,
        "exports": exports,
    }
