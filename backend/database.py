"""Configuração do banco de dados SQLAlchemy async."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings

engine = create_async_engine(settings.database_url, echo=False)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Classe base para todos os modelos SQLAlchemy."""

    pass


async def get_db() -> AsyncSession:
    """Dependency que fornece uma sessão de banco de dados."""
    async with async_session() as session:
        yield session


async def init_db() -> None:
    """Cria todas as tabelas no banco de dados."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
