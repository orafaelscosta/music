"""Modelo de dados do Projeto."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class ProjectStatus(str, enum.Enum):
    """Status geral do projeto."""

    CREATED = "created"
    UPLOADING = "uploading"
    ANALYZING = "analyzing"
    MELODY_READY = "melody_ready"
    SYNTHESIZING = "synthesizing"
    REFINING = "refining"
    MIXING = "mixing"
    COMPLETED = "completed"
    ERROR = "error"


class PipelineStep(str, enum.Enum):
    """Etapas do pipeline de processamento."""

    UPLOAD = "upload"
    SEPARATION = "separation"
    ANALYSIS = "analysis"
    MELODY = "melody"
    SYNTHESIS = "synthesis"
    REFINEMENT = "refinement"
    MIX = "mix"


class Project(Base):
    """Modelo do projeto de vocal."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus), default=ProjectStatus.CREATED
    )
    current_step: Mapped[PipelineStep | None] = mapped_column(
        Enum(PipelineStep), nullable=True
    )

    # Metadados do áudio instrumental
    instrumental_filename: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    audio_format: Mapped[str | None] = mapped_column(String(10), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    musical_key: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Letra e idioma
    lyrics: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), default="it")

    # Indica se o áudio enviado contém vocal (precisa separação Demucs)
    has_vocals: Mapped[bool] = mapped_column(Boolean, default=False)

    # Configurações do engine
    synthesis_engine: Mapped[str | None] = mapped_column(
        String(50), default="diffsinger"
    )
    voice_model: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Progresso do pipeline (0-100 por step)
    progress: Mapped[int] = mapped_column(Integer, default=0)

    # Mensagem de erro (se houver)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Project {self.id}: {self.name} [{self.status}]>"
