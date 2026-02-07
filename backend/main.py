"""AI Vocal Studio — Entry point da aplicação FastAPI."""

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import audio, pipeline, projects, voices
from api.websocket import websocket_endpoint
from config import settings
from database import init_db

# Configurar structlog
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

logger = structlog.get_logger()

app = FastAPI(
    title="AI Vocal Studio",
    description="Sistema orquestrador para geração de vocais por IA",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — permitir frontend Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar rotas
app.include_router(projects.router, prefix="/api")
app.include_router(audio.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")
app.include_router(voices.router, prefix="/api")

# WebSocket
app.websocket("/ws/{project_id}")(websocket_endpoint)


@app.on_event("startup")
async def startup() -> None:
    """Inicialização da aplicação."""
    logger.info("app_iniciando", version="0.1.0")

    # Criar diretórios necessários
    settings.projects_path.mkdir(parents=True, exist_ok=True)

    # Inicializar banco de dados
    await init_db()

    logger.info("app_pronta", storage=str(settings.storage_path))


@app.get("/api/health")
async def health_check() -> dict:
    """Endpoint de health check."""
    return {"status": "ok", "version": "0.1.0"}
