"""Rotas de templates de projeto."""

import structlog
from fastapi import APIRouter

logger = structlog.get_logger()
router = APIRouter(prefix="/templates", tags=["templates"])

# Templates pré-definidos
PROJECT_TEMPLATES = [
    {
        "id": "italian_opera",
        "name": "Opera Italiana",
        "description": "Vocal lírico italiano com DiffSinger",
        "language": "it",
        "synthesis_engine": "diffsinger",
        "mix_preset": "balanced",
        "icon": "music",
    },
    {
        "id": "pop_portuguese",
        "name": "Pop Brasileiro",
        "description": "Vocal pop em português com ACE-Step",
        "language": "pt",
        "synthesis_engine": "acestep",
        "mix_preset": "vocal_forward",
        "icon": "mic",
    },
    {
        "id": "ambient_vocal",
        "name": "Ambient Vocal",
        "description": "Vocal etéreo com reverb pesado",
        "language": "en",
        "synthesis_engine": "diffsinger",
        "mix_preset": "ambient",
        "icon": "cloud",
    },
    {
        "id": "radio_hit",
        "name": "Radio Hit",
        "description": "Mix comprimido e brilhante para rádio/streaming",
        "language": "en",
        "synthesis_engine": "acestep",
        "mix_preset": "radio",
        "icon": "radio",
    },
    {
        "id": "dry_studio",
        "name": "Estúdio Seco",
        "description": "Vocal limpo e seco para produção manual",
        "language": "it",
        "synthesis_engine": "diffsinger",
        "mix_preset": "dry",
        "icon": "headphones",
    },
]


@router.get("")
async def list_templates() -> dict:
    """Lista templates de projeto disponíveis."""
    return {"templates": PROJECT_TEMPLATES, "total": len(PROJECT_TEMPLATES)}


@router.get("/{template_id}")
async def get_template(template_id: str) -> dict:
    """Retorna um template específico."""
    for template in PROJECT_TEMPLATES:
        if template["id"] == template_id:
            return template
    return {"error": "Template não encontrado"}
