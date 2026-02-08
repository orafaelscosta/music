"""Rotas para gerenciamento de vozes e modelos."""

import structlog
from fastapi import APIRouter

from config import settings

logger = structlog.get_logger()
router = APIRouter(prefix="/voices", tags=["voices"])


@router.get("")
async def list_voices() -> dict:
    """Lista voicebanks e modelos de voz disponíveis."""
    voices = {"diffsinger": [], "rvc": []}

    # Escanear voicebanks DiffSinger
    voicebanks_path = settings.voicebanks_path
    if voicebanks_path.exists():
        for lang_dir in voicebanks_path.iterdir():
            if lang_dir.is_dir():
                for voice_dir in lang_dir.iterdir():
                    if voice_dir.is_dir():
                        voices["diffsinger"].append(
                            {
                                "name": voice_dir.name,
                                "language": lang_dir.name,
                                "path": str(voice_dir.relative_to(settings.storage_path.parent)),
                            }
                        )

    # Escanear modelos RVC
    applio_models = settings.applio_path / "models"
    if applio_models.exists():
        for model_file in applio_models.glob("*.pth"):
            voices["rvc"].append(
                {
                    "name": model_file.stem,
                    "path": str(model_file.relative_to(settings.storage_path.parent)),
                }
            )

    return voices


@router.get("/engines")
async def list_engines() -> dict:
    """Lista engines de síntese disponíveis e seu status."""
    engines = {}

    # Verificar DiffSinger
    engines["diffsinger"] = {
        "name": "DiffSinger",
        "description": "Síntese vocal de alta qualidade a partir de MIDI + letra",
        "installed": settings.diffsinger_path.exists(),
        "gpu_required": False,
        "languages": ["it", "pt", "en", "ja"],
    }

    # Verificar ACE-Step
    engines["acestep"] = {
        "name": "ACE-Step",
        "description": "Geração vocal rápida com suporte a Lyric2Vocal",
        "installed": settings.acestep_path.exists(),
        "gpu_required": True,
        "gpu_vram_gb": 4,
        "languages": ["multi"],
    }

    # Verificar Applio/RVC
    engines["applio"] = {
        "name": "Applio (RVC)",
        "description": "Conversão de timbre vocal",
        "installed": settings.applio_path.exists(),
        "gpu_required": True,
        "gpu_vram_gb": 6,
    }

    return engines


@router.post("/engines/{engine_name}/test")
async def test_engine(engine_name: str) -> dict:
    """Testa se um engine de IA está disponível."""
    available = False

    if engine_name == "diffsinger":
        available = settings.diffsinger_path.exists() and any(
            settings.diffsinger_path.glob("*.py")
        )
    elif engine_name == "acestep":
        available = settings.acestep_path.exists() and any(
            settings.acestep_path.glob("*.py")
        )
    elif engine_name == "applio":
        from services.rvc import RVCService
        svc = RVCService()
        available = svc.is_available()
    elif engine_name == "pedalboard":
        try:
            import pedalboard  # noqa: F401
            available = True
        except ImportError:
            available = False

    logger.info("engine_testado", engine=engine_name, available=available)
    return {"engine": engine_name, "available": available}
