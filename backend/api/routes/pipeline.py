"""Rotas de controle do pipeline de processamento."""

import structlog
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import ProjectResponse
from config import settings
from database import get_db
from models.project import PipelineStep, Project, ProjectStatus

logger = structlog.get_logger()
router = APIRouter(prefix="/pipeline", tags=["pipeline"])


def _get_analyzer():
    """Lazy-load AudioAnalyzer para evitar importar librosa no startup."""
    from services.analyzer import AudioAnalyzer
    return AudioAnalyzer()


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
    pipeline_queued = False
    try:
        from workers.tasks import run_full_pipeline
        run_full_pipeline.delay(project_id)
        pipeline_queued = True
    except Exception as e:
        logger.warning("celery_indisponivel", error=str(e))

    project.status = ProjectStatus.ANALYZING
    project.current_step = PipelineStep.ANALYSIS
    project.progress = 0
    await db.commit()
    await db.refresh(project)

    if not pipeline_queued:
        logger.info("pipeline_iniciado_sem_celery", project_id=project_id)
    else:
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


@router.post("/quick-start", response_model=ProjectResponse, status_code=201)
async def quick_start(
    file: UploadFile,
    lyrics: str = Form(...),
    name: str = Form(default=""),
    language: str = Form(default="it"),
    synthesis_engine: str = Form(default="diffsinger"),
    has_vocals: bool = Form(default=False),
    # Vocal params
    voice_preset: str = Form(default=""),
    vocal_style: str = Form(default="pop"),
    breathiness: float = Form(default=30),
    tension: float = Form(default=45),
    energy: float = Form(default=65),
    vibrato: float = Form(default=40),
    pitch_range: float = Form(default=60),
    gender: float = Form(default=50),
    # Mix params
    mix_preset: str = Form(default="balanced"),
    vocal_gain_db: float = Form(default=0),
    instrumental_gain_db: float = Form(default=-3),
    reverb_amount: float = Form(default=25),
    compression_amount: float = Form(default=40),
    db: AsyncSession = Depends(get_db),
) -> Project:
    """Cria projeto, faz upload, salva letra e inicia pipeline — tudo em um request."""
    # Validar formato do áudio
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

    # Validar engine
    if synthesis_engine not in ("diffsinger", "acestep"):
        synthesis_engine = "diffsinger"

    # Criar projeto com parâmetros vocais e de mix
    import json

    project_name = name.strip() or file.filename.rsplit(".", 1)[0]
    # Se voice_preset foi selecionado, buscar parâmetros do preset
    if voice_preset:
        from api.routes.voices import VOICE_PRESETS
        preset = next((p for p in VOICE_PRESETS if p["id"] == voice_preset), None)
        if preset:
            preset_params = preset["params"]
            breathiness = preset_params.get("breathiness", breathiness)
            tension = preset_params.get("tension", tension)
            energy = preset_params.get("energy", energy)
            vibrato = preset_params.get("vibrato", vibrato)
            pitch_range = preset_params.get("pitch_range", pitch_range)
            gender = preset_params.get("gender", gender)

    vocal_config = json.dumps({
        "voice_preset": voice_preset,
        "vocal_style": vocal_style,
        "breathiness": breathiness,
        "tension": tension,
        "energy": energy,
        "vibrato": vibrato,
        "pitch_range": pitch_range,
        "gender": gender,
        "mix_preset": mix_preset,
        "vocal_gain_db": vocal_gain_db,
        "instrumental_gain_db": instrumental_gain_db,
        "reverb_amount": reverb_amount,
        "compression_amount": compression_amount,
    })

    # Descrição legível para exibição na UI
    style_labels = {
        "operatic": "Operístico", "pop": "Pop", "breathy": "Aéreo",
        "powerful": "Potente", "ethereal": "Etéreo", "custom": "Personalizado",
    }
    mix_labels = {
        "balanced": "Equilibrado", "vocal_forward": "Vocal em Destaque",
        "ambient": "Ambiente", "radio": "Radio Ready", "dry": "Seco",
    }
    engine_labels = {"diffsinger": "DiffSinger", "acestep": "ACE-Step"}
    description = (
        f"Vocal {style_labels.get(vocal_style, vocal_style)} · "
        f"Mix {mix_labels.get(mix_preset, mix_preset)} · "
        f"{engine_labels.get(synthesis_engine, synthesis_engine)}"
    )

    project = Project(
        name=project_name,
        description=description,
        language=language,
        lyrics=lyrics,
        synthesis_engine=synthesis_engine,
        has_vocals=has_vocals,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    # Salvar config vocal como arquivo JSON para o pipeline
    project_dir = settings.projects_path / project.id
    project_dir.mkdir(parents=True, exist_ok=True)

    with open(project_dir / "vocal_config.json", "w") as vc:
        vc.write(vocal_config)
    file_path = project_dir / f"instrumental.{extension}"

    with open(file_path, "wb") as f:
        f.write(content)

    project.instrumental_filename = file.filename
    project.audio_format = extension

    logger.info(
        "quick_start_upload",
        project_id=project.id,
        filename=file.filename,
        size_mb=round(size_mb, 2),
    )

    # Executar análise síncrona
    try:
        analysis = await _get_analyzer().analyze(file_path)
    except Exception as e:
        project.status = ProjectStatus.ERROR
        project.error_message = f"Erro na análise: {str(e)}"
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Erro na análise de áudio: {str(e)}")

    project.duration_seconds = analysis.duration_seconds
    project.sample_rate = analysis.sample_rate
    project.bpm = analysis.bpm
    project.musical_key = analysis.musical_key

    # Disparar pipeline completo via Celery
    pipeline_queued = False
    try:
        from workers.tasks import run_full_pipeline
        run_full_pipeline.delay(project.id)
        pipeline_queued = True
    except Exception as e:
        logger.warning("celery_indisponivel_quick_start", error=str(e))

    project.status = ProjectStatus.ANALYZING
    project.current_step = PipelineStep.ANALYSIS
    project.progress = 0
    await db.commit()
    await db.refresh(project)

    logger.info(
        "quick_start_concluido",
        project_id=project.id,
        name=project.name,
        lyrics_len=len(lyrics),
        engine=synthesis_engine,
    )
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
        "instrumental", "vocals.wav", "melody.mid", "melody.json",
        "vocals_raw.wav", "vocals_refined.wav", "mix_final.wav",
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
            "separation": {
                "completed": files_exist.get("vocals.wav", False),
                "available": files_exist.get("instrumental", False) and project.has_vocals,
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
