"""Configurações centrais do ClovisAI."""

from pathlib import Path

from pydantic_settings import BaseSettings

# Raiz do projeto (pai do diretório backend/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Configurações da aplicação carregadas de variáveis de ambiente."""

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Database
    database_url: str = "sqlite+aiosqlite:///./storage/clovisai.db"

    # Storage
    storage_path: Path = Path("./storage")

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "change-me-in-production"

    # AI Engines paths (absolutos, baseados na raiz do projeto)
    diffsinger_path: Path = _PROJECT_ROOT / "engines" / "diffsinger" / "repo"
    acestep_path: Path = _PROJECT_ROOT / "engines" / "ace-step" / "repo"
    acestep_model_path: Path = _PROJECT_ROOT / "engines" / "ace-step" / "model"
    applio_path: Path = _PROJECT_ROOT / "engines" / "applio" / "repo"
    voicebanks_path: Path = _PROJECT_ROOT / "engines" / "voicebanks"

    # Processing limits
    max_upload_size_mb: int = 500
    max_concurrent_jobs: int = 2
    preview_duration_seconds: int = 15

    # Allowed audio formats
    allowed_audio_formats: list[str] = ["wav", "mp3", "flac", "ogg", "m4a"]

    @property
    def projects_path(self) -> Path:
        """Caminho para armazenamento de projetos."""
        return self.storage_path / "projects"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
