"""Configurações centrais do AI Vocal Studio."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configurações da aplicação carregadas de variáveis de ambiente."""

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Database
    database_url: str = "sqlite+aiosqlite:///./storage/vocal_studio.db"

    # Storage
    storage_path: Path = Path("./storage")

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "change-me-in-production"

    # AI Engines paths
    diffsinger_path: Path = Path("./engines/diffsinger")
    acestep_path: Path = Path("./engines/ace-step")
    applio_path: Path = Path("./engines/applio")
    voicebanks_path: Path = Path("./engines/voicebanks")

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
