"""Configuração de testes — fixtures compartilhadas."""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Configurar ambiente de teste ANTES de importar módulos do app
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["STORAGE_PATH"] = tempfile.mkdtemp()

from database import Base, get_db  # noqa: E402
from main import app  # noqa: E402
from config import settings  # noqa: E402


# Event loop para testes async
@pytest.fixture(scope="session")
def event_loop():
    """Cria event loop único para toda a sessão de testes."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Engine e session de teste
@pytest_asyncio.fixture
async def db_engine():
    """Engine de banco de dados in-memory para testes."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Sessão de banco de dados para testes."""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine):
    """Cliente HTTP de teste com banco in-memory."""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def tmp_project_dir():
    """Diretório temporário para simular storage de projeto."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test-project-id"
        project_dir.mkdir()
        yield project_dir


@pytest.fixture
def sample_audio_path(tmp_project_dir):
    """Cria um arquivo WAV simples de teste."""
    import numpy as np
    import soundfile as sf

    audio_path = tmp_project_dir / "test_audio.wav"
    sr = 22050
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # Tom simples de 440Hz
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)
    sf.write(str(audio_path), audio, sr)
    return audio_path
