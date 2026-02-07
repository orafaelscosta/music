"""Rotas de síntese vocal — DiffSinger e ACE-Step."""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.project import PipelineStep, Project, ProjectStatus

logger = structlog.get_logger()
router = APIRouter(prefix="/synthesis", tags=["synthesis"])


class SynthesisRequest(BaseModel):
    """Parâmetros de síntese vocal."""

    engine: str = Field(default="diffsinger", pattern="^(diffsinger|acestep)$")
    voicebank: str = "leif"
    language: str | None = None  # Usa idioma do projeto se None

    # Parâmetros DiffSinger
    breathiness: float = Field(default=0.0, ge=-1.0, le=1.0)
    tension: float = Field(default=0.0, ge=-1.0, le=1.0)
    energy: float = Field(default=1.0, ge=0.0, le=2.0)
    voicing: float = Field(default=1.0, ge=0.0, le=2.0)
    pitch_deviation: float = Field(default=0.0, ge=-1.0, le=1.0)
    gender: float = Field(default=0.0, ge=-1.0, le=1.0)

    # Parâmetros ACE-Step
    guidance_scale: float = Field(default=3.5, ge=1.0, le=10.0)
    num_inference_steps: int = Field(default=50, ge=10, le=200)
    seed: int = -1

    # Preview
    preview_seconds: float | None = Field(default=None, ge=5, le=30)


class SynthesisResponse(BaseModel):
    """Resposta da síntese vocal."""

    status: str
    engine: str
    output_file: str
    duration_seconds: float | None = None
    download_url: str


@router.post("/{project_id}/render", response_model=SynthesisResponse)
async def render_vocal(
    project_id: str,
    params: SynthesisRequest,
    db: AsyncSession = Depends(get_db),
) -> SynthesisResponse:
    """Renderiza vocal completo com o engine selecionado."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    melody_json = settings.projects_path / project_id / "melody.json"
    if not melody_json.exists():
        raise HTTPException(status_code=400, detail="Melodia necessária antes da síntese")

    language = params.language or project.language or "it"

    # Atualizar status
    project.status = ProjectStatus.SYNTHESIZING
    project.current_step = PipelineStep.SYNTHESIS
    project.progress = 0
    project.synthesis_engine = params.engine
    project.voice_model = params.voicebank
    await db.commit()

    project_dir = settings.projects_path / project_id
    output_file = "vocals_raw.wav"
    output_path = project_dir / output_file

    try:
        if params.engine == "diffsinger":
            from services.diffsinger import DiffSingerConfig, DiffSingerService

            svc = DiffSingerService()
            config = DiffSingerConfig(
                voicebank=params.voicebank,
                language=language,
                breathiness=params.breathiness,
                tension=params.tension,
                energy=params.energy,
                voicing=params.voicing,
                pitch_deviation=params.pitch_deviation,
                gender=params.gender,
            )
            await svc.synthesize(melody_json, output_path, config, params.preview_seconds)

        elif params.engine == "acestep":
            from services.acestep import ACEStepConfig, ACEStepService

            svc = ACEStepService()
            lyrics = project.lyrics or ""
            duration = project.duration_seconds or 30.0
            if params.preview_seconds:
                duration = params.preview_seconds

            config = ACEStepConfig(
                lyrics=lyrics,
                language=language,
                duration_seconds=duration,
                seed=params.seed,
                guidance_scale=params.guidance_scale,
                num_inference_steps=params.num_inference_steps,
            )

            instrumental_path = None
            if project.audio_format:
                instrumental_path = project_dir / f"instrumental.{project.audio_format}"

            await svc.generate(output_path, config, instrumental_path)

    except Exception as e:
        project.status = ProjectStatus.ERROR
        project.error_message = f"Erro na síntese: {str(e)}"
        project.progress = 0
        await db.commit()
        logger.error("sintese_erro", project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Erro na síntese: {str(e)}")

    # Obter duração do áudio gerado
    duration = None
    try:
        import librosa
        y, sr = librosa.load(str(output_path), sr=None, duration=1)
        info = sf_info(str(output_path))
        duration = info.duration if info else None
    except Exception:
        pass

    project.status = ProjectStatus.REFINING if not params.preview_seconds else ProjectStatus.SYNTHESIZING
    project.progress = 100
    project.current_step = PipelineStep.REFINEMENT if not params.preview_seconds else PipelineStep.SYNTHESIS
    await db.commit()

    logger.info(
        "sintese_concluida",
        project_id=project_id,
        engine=params.engine,
        preview=params.preview_seconds is not None,
    )

    return SynthesisResponse(
        status="completed",
        engine=params.engine,
        output_file=output_file,
        duration_seconds=duration,
        download_url=f"/api/audio/{project_id}/{output_file}",
    )


@router.post("/{project_id}/preview", response_model=SynthesisResponse)
async def preview_vocal(
    project_id: str,
    params: SynthesisRequest,
    db: AsyncSession = Depends(get_db),
) -> SynthesisResponse:
    """Gera preview rápido (10-15s) do vocal."""
    params.preview_seconds = params.preview_seconds or settings.preview_duration_seconds

    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    melody_json = settings.projects_path / project_id / "melody.json"
    if not melody_json.exists():
        raise HTTPException(status_code=400, detail="Melodia necessária antes da síntese")

    language = params.language or project.language or "it"
    project_dir = settings.projects_path / project_id
    output_file = "vocals_preview.wav"
    output_path = project_dir / output_file

    try:
        if params.engine == "diffsinger":
            from services.diffsinger import DiffSingerConfig, DiffSingerService

            svc = DiffSingerService()
            config = DiffSingerConfig(
                voicebank=params.voicebank,
                language=language,
                breathiness=params.breathiness,
                tension=params.tension,
                energy=params.energy,
                voicing=params.voicing,
                pitch_deviation=params.pitch_deviation,
                gender=params.gender,
            )
            await svc.synthesize(melody_json, output_path, config, params.preview_seconds)

        elif params.engine == "acestep":
            from services.acestep import ACEStepConfig, ACEStepService

            svc = ACEStepService()
            config = ACEStepConfig(
                lyrics=project.lyrics or "",
                language=language,
                duration_seconds=params.preview_seconds,
                seed=params.seed,
                guidance_scale=params.guidance_scale,
                num_inference_steps=max(20, params.num_inference_steps // 2),
            )
            await svc.generate(output_path, config)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no preview: {str(e)}")

    logger.info("preview_gerado", project_id=project_id, engine=params.engine)

    return SynthesisResponse(
        status="completed",
        engine=params.engine,
        output_file=output_file,
        duration_seconds=params.preview_seconds,
        download_url=f"/api/audio/{project_id}/{output_file}",
    )


@router.post("/{project_id}/variations")
async def generate_variations(
    project_id: str,
    params: SynthesisRequest,
    count: int = 3,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Gera múltiplas variações do vocal para comparação."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    melody_json = settings.projects_path / project_id / "melody.json"
    if not melody_json.exists():
        raise HTTPException(status_code=400, detail="Melodia necessária")

    count = min(count, 5)  # Máximo 5 variações
    language = params.language or project.language or "it"
    project_dir = settings.projects_path / project_id
    variations = []

    for i in range(count):
        output_file = f"vocals_var_{i+1}.wav"
        output_path = project_dir / output_file

        try:
            if params.engine == "diffsinger":
                from services.diffsinger import DiffSingerConfig, DiffSingerService

                svc = DiffSingerService()
                config = DiffSingerConfig(
                    voicebank=params.voicebank,
                    language=language,
                    breathiness=params.breathiness + (i * 0.1 - 0.1),
                    tension=params.tension + (i * 0.05 - 0.05),
                    energy=params.energy,
                    voicing=params.voicing,
                    pitch_deviation=params.pitch_deviation,
                    gender=params.gender,
                )
                await svc.synthesize(
                    melody_json, output_path, config, params.preview_seconds or 15
                )

            elif params.engine == "acestep":
                from services.acestep import ACEStepConfig, ACEStepService

                svc = ACEStepService()
                config = ACEStepConfig(
                    lyrics=project.lyrics or "",
                    language=language,
                    duration_seconds=params.preview_seconds or 15,
                    seed=i * 42 if params.seed < 0 else params.seed + i,
                    guidance_scale=params.guidance_scale,
                    num_inference_steps=max(20, params.num_inference_steps // 2),
                )
                await svc.generate(output_path, config)

            variations.append({
                "index": i + 1,
                "file": output_file,
                "download_url": f"/api/audio/{project_id}/{output_file}",
            })

        except Exception as e:
            logger.warning(
                "variacao_falhou", project_id=project_id, index=i + 1, error=str(e)
            )

    logger.info(
        "variacoes_geradas",
        project_id=project_id,
        count=len(variations),
    )

    return {
        "project_id": project_id,
        "engine": params.engine,
        "variations": variations,
        "total": len(variations),
    }


@router.get("/{project_id}/status")
async def get_synthesis_status(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retorna status da síntese e arquivos disponíveis."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    project_dir = settings.projects_path / project_id

    files = {}
    for name in ["vocals_raw.wav", "vocals_preview.wav"]:
        path = project_dir / name
        files[name] = {
            "exists": path.exists(),
            "download_url": f"/api/audio/{project_id}/{name}" if path.exists() else None,
        }

    # Verificar variações
    variation_files = sorted(project_dir.glob("vocals_var_*.wav"))
    files["variations"] = [
        {
            "file": f.name,
            "download_url": f"/api/audio/{project_id}/{f.name}",
        }
        for f in variation_files
    ]

    return {
        "project_id": project_id,
        "engine": project.synthesis_engine,
        "voice_model": project.voice_model,
        "status": project.status,
        "files": files,
    }


def sf_info(path: str):
    """Obtém informações de um arquivo de áudio."""
    try:
        import soundfile as sf
        return sf.info(path)
    except Exception:
        return None
