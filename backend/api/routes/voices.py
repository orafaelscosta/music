"""Rotas para gerenciamento de vozes e modelos."""

import structlog
from fastapi import APIRouter

from config import settings

logger = structlog.get_logger()
router = APIRouter(prefix="/voices", tags=["voices"])

# Biblioteca de vozes predefinidas
VOICE_PRESETS = [
    {
        "id": "tenor_lirico",
        "name": "Tenor Lírico",
        "description": "Voz masculina clara e projetada, ideal para ópera e baladas",
        "gender": "male",
        "icon": "🎭",
        "tags": ["operatic", "dramatic", "classical", "clear tenor vocals", "lyrical"],
        "voicebank": "umidaji",
        "params": {
            "breathiness": 15, "tension": 70, "energy": 80,
            "vibrato": 75, "pitch_range": 85, "gender": 20,
        },
    },
    {
        "id": "baritono_pop",
        "name": "Barítono Pop",
        "description": "Voz masculina quente e moderna, perfeita para pop e R&B",
        "gender": "male",
        "icon": "🎤",
        "tags": ["pop", "warm", "smooth", "baritone vocals", "modern"],
        "voicebank": "umidaji",
        "params": {
            "breathiness": 30, "tension": 40, "energy": 65,
            "vibrato": 35, "pitch_range": 55, "gender": 25,
        },
    },
    {
        "id": "tenor_rock",
        "name": "Tenor Rock",
        "description": "Voz masculina potente e rasgada, para rock e alternativo",
        "gender": "male",
        "icon": "🔥",
        "tags": ["rock", "powerful", "raspy", "gritty male vocals", "energetic"],
        "voicebank": "umidaji",
        "params": {
            "breathiness": 10, "tension": 85, "energy": 95,
            "vibrato": 30, "pitch_range": 75, "gender": 20,
        },
    },
    {
        "id": "crooner_jazz",
        "name": "Crooner Jazz",
        "description": "Voz masculina suave e aveludada, estilo jazz e bossa nova",
        "gender": "male",
        "icon": "🎷",
        "tags": ["jazz", "smooth", "velvet", "crooner male vocals", "intimate"],
        "voicebank": "umidaji",
        "params": {
            "breathiness": 45, "tension": 25, "energy": 45,
            "vibrato": 40, "pitch_range": 50, "gender": 30,
        },
    },
    {
        "id": "soprano_lirica",
        "name": "Soprano Lírica",
        "description": "Voz feminina poderosa e cristalina, para ópera e clássico",
        "gender": "female",
        "icon": "✨",
        "tags": ["operatic", "dramatic", "classical", "soprano female vocals", "powerful"],
        "voicebank": "umidaji",
        "params": {
            "breathiness": 15, "tension": 65, "energy": 85,
            "vibrato": 80, "pitch_range": 95, "gender": 80,
        },
    },
    {
        "id": "mezzo_pop",
        "name": "Mezzo Pop",
        "description": "Voz feminina versátil e expressiva, ideal para pop e dance",
        "gender": "female",
        "icon": "💫",
        "tags": ["pop", "catchy", "melodic", "female vocals", "expressive"],
        "voicebank": "umidaji",
        "params": {
            "breathiness": 25, "tension": 45, "energy": 70,
            "vibrato": 40, "pitch_range": 65, "gender": 75,
        },
    },
    {
        "id": "alto_indie",
        "name": "Alto Indie",
        "description": "Voz feminina intimista e aérea, estilo indie e folk",
        "gender": "female",
        "icon": "🌙",
        "tags": ["indie", "breathy", "intimate", "airy female vocals", "folk"],
        "voicebank": "umidaji",
        "params": {
            "breathiness": 70, "tension": 20, "energy": 40,
            "vibrato": 25, "pitch_range": 50, "gender": 65,
        },
    },
    {
        "id": "soprano_ethereal",
        "name": "Soprano Etérea",
        "description": "Voz feminina delicada e sonhadora, para ambient e new age",
        "gender": "female",
        "icon": "🦋",
        "tags": ["ethereal", "ambient", "dreamy", "angelic female vocals", "reverb"],
        "voicebank": "umidaji",
        "params": {
            "breathiness": 60, "tension": 20, "energy": 35,
            "vibrato": 55, "pitch_range": 80, "gender": 80,
        },
    },
    # --- Novas vozes masculinas ---
    {
        "id": "contratenor",
        "name": "Contratenor",
        "description": "Voz masculina aguda em falsete, registro celestial e raro",
        "gender": "male",
        "icon": "👼",
        "tags": ["classical", "falsetto", "ethereal", "countertenor male vocals", "angelic"],
        "voicebank": "umidaji",
        "params": {
            "breathiness": 35, "tension": 50, "energy": 60,
            "vibrato": 65, "pitch_range": 95, "gender": 35,
        },
    },
    {
        "id": "soul_gospel",
        "name": "Soul Gospel",
        "description": "Voz masculina quente e emotiva, belting espiritual",
        "gender": "male",
        "icon": "🙏",
        "tags": ["soul", "gospel", "powerful", "warm male vocals", "belting", "emotional"],
        "voicebank": "umidaji",
        "params": {
            "breathiness": 20, "tension": 75, "energy": 90,
            "vibrato": 60, "pitch_range": 80, "gender": 25,
        },
    },
    {
        "id": "rapper_mc",
        "name": "Rapper/MC",
        "description": "Voz masculina rítmica e percussiva, flow e atitude",
        "gender": "male",
        "icon": "🎙️",
        "tags": ["hip-hop", "rap", "rhythmic", "spoken word male vocals", "urban"],
        "voicebank": "umidaji",
        "params": {
            "breathiness": 15, "tension": 60, "energy": 85,
            "vibrato": 10, "pitch_range": 30, "gender": 15,
        },
    },
    {
        "id": "country_masculino",
        "name": "Country Tenor",
        "description": "Voz masculina narrativa e acolhedora, estilo Nashville",
        "gender": "male",
        "icon": "🤠",
        "tags": ["country", "warm", "storytelling", "twangy male vocals", "acoustic"],
        "voicebank": "umidaji",
        "params": {
            "breathiness": 35, "tension": 45, "energy": 60,
            "vibrato": 45, "pitch_range": 60, "gender": 25,
        },
    },
    {
        "id": "indie_soft_male",
        "name": "Indie Sussurrado",
        "description": "Voz masculina suave e sussurrada, lo-fi e intimista",
        "gender": "male",
        "icon": "🌿",
        "tags": ["indie", "soft", "whisper", "lo-fi male vocals", "intimate", "gentle"],
        "voicebank": "umidaji",
        "params": {
            "breathiness": 80, "tension": 15, "energy": 30,
            "vibrato": 15, "pitch_range": 40, "gender": 30,
        },
    },
    {
        "id": "metal_gutural",
        "name": "Metal Gutural",
        "description": "Voz masculina agressiva e intensa, grito e peso",
        "gender": "male",
        "icon": "⚡",
        "tags": ["metal", "aggressive", "screaming", "heavy male vocals", "intense", "distorted"],
        "voicebank": "umidaji",
        "params": {
            "breathiness": 5, "tension": 95, "energy": 100,
            "vibrato": 10, "pitch_range": 65, "gender": 15,
        },
    },
    # --- Novas vozes femininas ---
    {
        "id": "diva_rnb",
        "name": "Diva R&B",
        "description": "Voz feminina poderosa e melismática, runs e expressão",
        "gender": "female",
        "icon": "👑",
        "tags": ["r&b", "soulful", "melismatic", "powerful female vocals", "diva", "runs"],
        "voicebank": "umidaji",
        "params": {
            "breathiness": 20, "tension": 55, "energy": 80,
            "vibrato": 65, "pitch_range": 85, "gender": 75,
        },
    },
    {
        "id": "country_feminino",
        "name": "Country Folk",
        "description": "Voz feminina calorosa e narrativa, violão e história",
        "gender": "female",
        "icon": "🌾",
        "tags": ["country", "folk", "warm", "storytelling female vocals", "acoustic"],
        "voicebank": "umidaji",
        "params": {
            "breathiness": 40, "tension": 35, "energy": 55,
            "vibrato": 35, "pitch_range": 55, "gender": 70,
        },
    },
    {
        "id": "punk_feminino",
        "name": "Punk Rock",
        "description": "Voz feminina crua e explosiva, atitude e energia",
        "gender": "female",
        "icon": "💥",
        "tags": ["punk", "rock", "raw", "aggressive female vocals", "energetic", "rebellious"],
        "voicebank": "umidaji",
        "params": {
            "breathiness": 10, "tension": 80, "energy": 95,
            "vibrato": 15, "pitch_range": 70, "gender": 70,
        },
    },
    {
        "id": "jazz_lounge",
        "name": "Jazz Lounge",
        "description": "Voz feminina esfumada e sedutora, noites de jazz",
        "gender": "female",
        "icon": "🍷",
        "tags": ["jazz", "smoky", "smooth", "sultry female vocals", "lounge", "intimate"],
        "voicebank": "umidaji",
        "params": {
            "breathiness": 55, "tension": 30, "energy": 45,
            "vibrato": 45, "pitch_range": 55, "gender": 65,
        },
    },
    {
        "id": "mpb_bossa",
        "name": "MPB / Bossa",
        "description": "Voz feminina suave e brasileira, bossa nova e MPB",
        "gender": "female",
        "icon": "🌴",
        "tags": ["bossa nova", "mpb", "soft", "brazilian female vocals", "gentle", "warm"],
        "voicebank": "umidaji",
        "params": {
            "breathiness": 50, "tension": 20, "energy": 40,
            "vibrato": 30, "pitch_range": 50, "gender": 70,
        },
    },
    {
        "id": "gospel_feminino",
        "name": "Gospel Power",
        "description": "Voz feminina explosiva e espiritual, belting e fé",
        "gender": "female",
        "icon": "🔔",
        "tags": ["gospel", "powerful", "belting", "spiritual female vocals", "emotional", "choir"],
        "voicebank": "umidaji",
        "params": {
            "breathiness": 10, "tension": 70, "energy": 95,
            "vibrato": 70, "pitch_range": 90, "gender": 80,
        },
    },
]


@router.get("/presets")
async def list_voice_presets() -> dict:
    """Retorna a biblioteca de vozes predefinidas."""
    return {"presets": VOICE_PRESETS, "total": len(VOICE_PRESETS)}


@router.get("")
async def list_voices() -> dict:
    """Lista voicebanks e modelos de voz disponíveis."""
    voices = {"diffsinger": [], "rvc": []}

    # Escanear voicebanks DiffSinger
    voicebanks_path = settings.voicebanks_path
    if voicebanks_path.exists():
        for lang_dir in voicebanks_path.iterdir():
            if lang_dir.is_dir() and not lang_dir.name.startswith("."):
                for voice_dir in lang_dir.iterdir():
                    if voice_dir.is_dir() and not voice_dir.name.startswith("."):
                        # Verificar se tem modelo ONNX
                        has_model = bool(list(voice_dir.rglob("acoustic.onnx")))
                        voices["diffsinger"].append(
                            {
                                "name": voice_dir.name,
                                "language": lang_dir.name,
                                "has_model": has_model,
                                "path": f"engines/voicebanks/{lang_dir.name}/{voice_dir.name}",
                            }
                        )

    # Escanear modelos RVC
    applio_models = settings.applio_path / "models"
    if applio_models.exists():
        for model_file in applio_models.glob("*.pth"):
            voices["rvc"].append(
                {
                    "name": model_file.stem,
                    "path": f"engines/applio/repo/models/{model_file.name}",
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
