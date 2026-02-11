"""Rotas para operações de melodia — extração, importação, edição MIDI."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.project import PipelineStep, Project, ProjectStatus

logger = structlog.get_logger()
router = APIRouter(prefix="/melody", tags=["melody"])


def _get_melody_service():
    """Lazy-load MelodyService para evitar importar librosa no startup."""
    from services.melody import MelodyService
    return MelodyService()


def _get_syllable_service():
    """Lazy-load SyllableService para evitar importar no startup."""
    from services.syllable import SyllableService
    return SyllableService()


@router.post("/{project_id}/extract")
async def extract_melody(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Extrai melodia do instrumental usando análise de pitch."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    if not project.instrumental_filename or not project.audio_format:
        raise HTTPException(status_code=400, detail="Upload do instrumental necessário")

    audio_path = settings.projects_path / project_id / f"instrumental.{project.audio_format}"
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de áudio não encontrado")

    bpm = project.bpm or 120.0

    svc = _get_melody_service()
    try:
        melody = await svc.extract_melody_from_audio(audio_path, bpm)
    except Exception as e:
        logger.error("melody_extraction_erro", project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Erro na extração de melodia: {str(e)}")

    # Salvar melodia JSON
    project_dir = settings.projects_path / project_id
    svc.save_melody_json(melody, project_dir / "melody.json")

    # Exportar MIDI
    await svc.export_midi(melody, project_dir / "melody.mid")

    # Atualizar status do projeto
    project.current_step = PipelineStep.MELODY
    await db.commit()

    logger.info("melody_extraida", project_id=project_id, notes=len(melody.notes))

    return melody.to_dict()


@router.post("/{project_id}/import")
async def import_midi(
    project_id: str,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Importa melodia de um arquivo MIDI externo."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    if not file.filename or not file.filename.lower().endswith((".mid", ".midi")):
        raise HTTPException(status_code=400, detail="Apenas arquivos .mid/.midi são aceitos")

    # Salvar arquivo temporário
    project_dir = settings.projects_path / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    temp_midi = project_dir / "imported.mid"

    content = await file.read()
    with open(temp_midi, "wb") as f:
        f.write(content)

    bpm = project.bpm or 120.0

    svc = _get_melody_service()
    try:
        melody = await svc.import_midi(temp_midi, bpm)
    except Exception as e:
        logger.error("midi_import_erro", project_id=project_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Erro na importação MIDI: {str(e)}")

    # Salvar melodia JSON e MIDI
    svc.save_melody_json(melody, project_dir / "melody.json")
    await svc.export_midi(melody, project_dir / "melody.mid")

    # Limpar arquivo temporário
    if temp_midi.exists():
        temp_midi.unlink()

    project.current_step = PipelineStep.MELODY
    await db.commit()

    logger.info("midi_importado", project_id=project_id, notes=len(melody.notes))
    return melody.to_dict()


@router.get("/{project_id}")
async def get_melody(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retorna os dados de melodia do projeto."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    melody_json = settings.projects_path / project_id / "melody.json"
    if not melody_json.exists():
        raise HTTPException(status_code=404, detail="Melodia não encontrada. Execute extração ou importe MIDI.")

    melody = _get_melody_service().load_melody_json(melody_json)
    return melody.to_dict()


@router.put("/{project_id}")
async def update_melody(
    project_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Atualiza a melodia do projeto (edição do piano roll)."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    from services.melody import MelodyData

    try:
        melody = MelodyData.from_dict(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Dados de melodia inválidos: {str(e)}")

    # Salvar
    svc = _get_melody_service()
    project_dir = settings.projects_path / project_id
    svc.save_melody_json(melody, project_dir / "melody.json")
    await svc.export_midi(melody, project_dir / "melody.mid")

    await db.commit()

    logger.info("melody_atualizada", project_id=project_id, notes=len(melody.notes))
    return melody.to_dict()


@router.post("/{project_id}/snap-to-grid")
async def snap_melody_to_grid(
    project_id: str,
    grid_resolution: float = 0.125,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Quantiza notas da melodia para o grid baseado no BPM."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    melody_json = settings.projects_path / project_id / "melody.json"
    if not melody_json.exists():
        raise HTTPException(status_code=404, detail="Melodia não encontrada")

    svc = _get_melody_service()
    melody = svc.load_melody_json(melody_json)
    melody.snap_to_grid(grid_resolution)

    project_dir = settings.projects_path / project_id
    svc.save_melody_json(melody, project_dir / "melody.json")
    await svc.export_midi(melody, project_dir / "melody.mid")

    logger.info("melody_quantizada", project_id=project_id, grid=grid_resolution)
    return melody.to_dict()


@router.post("/{project_id}/syllabify")
async def syllabify_lyrics(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Segmenta a letra do projeto em sílabas e alinha com notas."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    if not project.lyrics:
        raise HTTPException(status_code=400, detail="Nenhuma letra definida no projeto")

    language = project.language or "it"

    # Segmentar em sílabas
    syl_svc = _get_syllable_service()
    syllables = await syl_svc.syllabify_text(project.lyrics, language)
    lines = syl_svc.syllables_to_lines(project.lyrics, syllables)

    # Se houver melodia, associar sílabas às notas
    melody_json = settings.projects_path / project_id / "melody.json"
    melody_assigned = False
    if melody_json.exists():
        mel_svc = _get_melody_service()
        melody = mel_svc.load_melody_json(melody_json)
        melody = mel_svc.assign_lyrics_to_notes(melody, syllables)
        mel_svc.save_melody_json(melody, melody_json)

        project_dir = settings.projects_path / project_id
        await mel_svc.export_midi(melody, project_dir / "melody.mid")
        melody_assigned = True

    logger.info(
        "syllabify_concluido",
        project_id=project_id,
        total_syllables=len(syllables),
        assigned=melody_assigned,
    )

    return {
        "syllables": syllables,
        "lines": lines,
        "total": len(syllables),
        "assigned_to_melody": melody_assigned,
    }


@router.get("/{project_id}/export/midi")
async def export_midi_file(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retorna URL para download do MIDI exportado."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    midi_path = settings.projects_path / project_id / "melody.mid"
    if not midi_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo MIDI não encontrado")

    return {
        "download_url": f"/api/audio/{project_id}/melody.mid",
        "filename": "melody.mid",
    }
