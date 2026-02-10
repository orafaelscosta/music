"""Schemas Pydantic para validação de dados da API."""

from datetime import datetime

from pydantic import BaseModel, Field

from models.project import PipelineStep, ProjectStatus


class ProjectCreate(BaseModel):
    """Schema para criação de projeto."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    language: str = Field(default="it", pattern="^(it|pt|en|es|fr|de|ja)$")
    synthesis_engine: str | None = Field(None, pattern="^(diffsinger|acestep)$")
    has_vocals: bool = False
    template_id: str | None = None


class ProjectUpdate(BaseModel):
    """Schema para atualização de projeto."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    lyrics: str | None = None
    language: str | None = Field(None, pattern="^(it|pt|en|es|fr|de|ja)$")
    synthesis_engine: str | None = Field(None, pattern="^(diffsinger|acestep)$")
    voice_model: str | None = None


class ProjectResponse(BaseModel):
    """Schema de resposta com dados do projeto."""

    id: str
    name: str
    description: str | None
    status: ProjectStatus
    current_step: PipelineStep | None

    instrumental_filename: str | None
    audio_format: str | None
    duration_seconds: float | None
    sample_rate: int | None
    bpm: float | None
    musical_key: str | None

    lyrics: str | None
    language: str | None
    has_vocals: bool
    synthesis_engine: str | None
    voice_model: str | None
    progress: int
    error_message: str | None

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    """Schema de resposta para listagem de projetos."""

    projects: list[ProjectResponse]
    total: int


class AudioAnalysis(BaseModel):
    """Resultado da análise de áudio."""

    duration_seconds: float
    sample_rate: int
    bpm: float
    musical_key: str
    audio_format: str
    waveform_peaks: list[float]


class PipelineProgress(BaseModel):
    """Mensagem de progresso do pipeline via WebSocket."""

    project_id: str
    step: PipelineStep
    progress: int = Field(ge=0, le=100)
    message: str = ""
    status: str = "processing"


class MelodyNoteSchema(BaseModel):
    """Schema de uma nota MIDI na melodia."""

    start_time: float
    end_time: float
    duration: float = 0
    midi_note: int = Field(ge=0, le=127)
    note_name: str = ""
    velocity: int = Field(default=100, ge=0, le=127)
    lyric: str = ""


class MelodyResponse(BaseModel):
    """Resposta com dados de melodia."""

    notes: list[MelodyNoteSchema]
    bpm: float
    time_signature: list[int]
    total_notes: int


class SyllabifyResponse(BaseModel):
    """Resposta da segmentação silábica."""

    syllables: list[str]
    lines: list[list[str]]
    total: int
    assigned_to_melody: bool


class ErrorResponse(BaseModel):
    """Schema padronizado de erro."""

    error: str
    detail: str
