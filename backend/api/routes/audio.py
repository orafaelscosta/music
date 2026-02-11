"""Rotas de upload e download de áudio."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import AudioAnalysis
from config import settings
from database import get_db
from models.project import PipelineStep, Project, ProjectStatus

logger = structlog.get_logger()
router = APIRouter(prefix="/audio", tags=["audio"])


def _get_analyzer():
    """Lazy-load AudioAnalyzer para evitar importar librosa no startup."""
    from services.analyzer import AudioAnalyzer
    return AudioAnalyzer()


@router.post("/{project_id}/upload", response_model=AudioAnalysis)
async def upload_instrumental(
    project_id: str,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
) -> AudioAnalysis:
    """Faz upload do instrumental e executa análise automática."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    # Validar formato
    if not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo sem nome")

    extension = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if extension not in settings.allowed_audio_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Formato não suportado. Use: {', '.join(settings.allowed_audio_formats)}",
        )

    # Validar tamanho
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.max_upload_size_mb:
        raise HTTPException(
            status_code=400,
            detail=f"Arquivo muito grande ({size_mb:.1f}MB). Máximo: {settings.max_upload_size_mb}MB",
        )

    # Salvar arquivo
    project_dir = settings.projects_path / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    file_path = project_dir / f"instrumental.{extension}"

    with open(file_path, "wb") as f:
        f.write(content)

    logger.info(
        "instrumental_uploaded",
        project_id=project_id,
        filename=file.filename,
        size_mb=round(size_mb, 2),
    )

    # Atualizar status do projeto
    project.status = ProjectStatus.ANALYZING
    project.current_step = PipelineStep.ANALYSIS
    project.instrumental_filename = file.filename
    project.audio_format = extension
    await db.commit()

    # Executar análise
    try:
        analysis = await _get_analyzer().analyze(file_path)
    except Exception as e:
        project.status = ProjectStatus.ERROR
        project.error_message = f"Erro na análise: {str(e)}"
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Erro na análise de áudio: {str(e)}")

    # Salvar resultados da análise no projeto
    project.duration_seconds = analysis.duration_seconds
    project.sample_rate = analysis.sample_rate
    project.bpm = analysis.bpm
    project.musical_key = analysis.musical_key
    project.status = ProjectStatus.MELODY_READY
    project.current_step = PipelineStep.MELODY
    project.progress = 100
    await db.commit()

    logger.info(
        "analise_concluida",
        project_id=project_id,
        bpm=analysis.bpm,
        key=analysis.musical_key,
        duration=analysis.duration_seconds,
    )

    return analysis


@router.get("/{project_id}/{filename}")
async def download_audio(
    project_id: str,
    filename: str,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Download de um arquivo de áudio do projeto."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    project_dir = settings.projects_path / project_id
    file_path = project_dir / filename

    # Segurança: verificar que o path está dentro do diretório do projeto
    try:
        file_path.resolve().relative_to(project_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Acesso negado")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="audio/wav" if filename.endswith(".wav") else "application/octet-stream",
    )


@router.get("/{project_id}/waveform")
async def get_waveform(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retorna dados de waveform para visualização."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    if not project.instrumental_filename or not project.audio_format:
        raise HTTPException(status_code=400, detail="Nenhum instrumental uploaded")

    file_path = settings.projects_path / project_id / f"instrumental.{project.audio_format}"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de áudio não encontrado")

    peaks = await _get_analyzer().generate_waveform_peaks(file_path)
    return {"peaks": peaks, "duration": project.duration_seconds}
