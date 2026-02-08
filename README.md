# ClovisAI - Music Creation

Sistema web de criação musical com IA. Faça upload de um instrumental, insira a letra e o pipeline gera automaticamente a voz cantada, refina o timbre e entrega a mixagem final.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, React Query, Zustand |
| Backend | FastAPI, SQLAlchemy (async), Pydantic v2, structlog |
| AI Engines | DiffSinger, ACE-Step, RVC/Applio, Pedalboard |
| Infra | Docker, Celery + Redis, SQLite, WebSocket |

## Funcionalidades

- **Quick Start** — upload do instrumental + letra em um único passo, pipeline automático
- **Pipeline completo** — Análise → Melodia → Síntese → Refinamento → Mixagem
- **Piano Roll** — editor visual de melodia com extração automática via librosa
- **Síntese vocal** — DiffSinger (qualidade) ou ACE-Step (velocidade) com fallback
- **Refinamento de timbre** — RVC/Applio para clonagem de voz
- **Mixer** — Pedalboard com EQ, compressor, reverb, limiter e 5 presets
- **Exportação** — WAV, FLAC, MP3, OGG
- **Comparação A/B** — compare áudios de cada estágio do pipeline lado a lado
- **Templates** — 5 presets prontos (Italian Opera, Pop Português, Ambient, Radio Hit, Dry Studio)
- **Batch processing** — processar múltiplos projetos em paralelo
- **Progresso em tempo real** — WebSocket para acompanhar cada step do pipeline
- **65 testes automatizados** — cobertura de serviços e rotas API

## Estrutura do Projeto

```
clovisai/
├── backend/
│   ├── api/
│   │   ├── routes/          # Endpoints (projects, audio, pipeline, melody, synthesis, refinement, mix, voices, templates, batch)
│   │   ├── schemas.py       # Pydantic models
│   │   └── websocket.py     # WebSocket manager
│   ├── models/
│   │   └── project.py       # SQLAlchemy model
│   ├── services/
│   │   ├── analyzer.py      # Análise de áudio (BPM, key, waveform)
│   │   ├── melody.py        # Extração de melodia, MIDI, piano roll
│   │   ├── syllable.py      # Segmentação silábica (IT, PT, EN, ES, FR, DE, JA)
│   │   ├── diffsinger.py    # Wrapper DiffSinger
│   │   ├── acestep.py       # Wrapper ACE-Step
│   │   ├── rvc.py           # Wrapper RVC/Applio
│   │   ├── mixer.py         # Mixagem com Pedalboard
│   │   └── orchestrator.py  # Pipeline orchestrator
│   ├── workers/
│   │   └── tasks.py         # Celery tasks
│   ├── tests/               # pytest + pytest-asyncio (65 testes)
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings (Pydantic)
│   ├── database.py          # SQLAlchemy async engine
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx                    # Dashboard
│   │   │   ├── quick-start/page.tsx        # Quick Start (one-shot)
│   │   │   ├── settings/page.tsx           # Status dos engines
│   │   │   └── project/[id]/
│   │   │       ├── page.tsx                # Detalhe do projeto
│   │   │       ├── melody/page.tsx         # Piano Roll
│   │   │       ├── synthesis/page.tsx      # Síntese vocal
│   │   │       ├── refinement/page.tsx     # Refinamento RVC
│   │   │       ├── mix/page.tsx            # Mixer e exportação
│   │   │       └── compare/page.tsx        # Comparação A/B
│   │   ├── components/
│   │   │   ├── AudioPlayer.tsx             # Player com wavesurfer.js
│   │   │   ├── PianoRoll.tsx               # Editor de melodia canvas
│   │   │   ├── PipelineProgress.tsx        # Barra de progresso
│   │   │   ├── UploadZone.tsx              # Drag-and-drop upload
│   │   │   ├── LyricsEditor.tsx            # Editor de letra
│   │   │   ├── VoiceSelector.tsx           # Seletor de voicebanks
│   │   │   ├── Toast.tsx                   # Notificações
│   │   │   └── Providers.tsx               # React Query + Zustand
│   │   └── lib/
│   │       ├── api.ts                      # Cliente API
│   │       ├── audio.ts                    # Utils de áudio
│   │       └── websocket.ts                # WebSocket client
│   ├── Dockerfile
│   └── package.json
├── scripts/
│   └── test_engines.py      # Verificação de ambiente
├── docker-compose.yml
└── CLAUDE.md                # Instruções para Claude Code
```

## Início Rápido

### Pré-requisitos

- Python 3.11+
- Node.js 22+
- ffmpeg
- Redis (opcional — pipeline funciona sem, mas sem fila async)

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
# API em http://localhost:8000
# Swagger em http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Interface em http://localhost:3000
```

### Docker

```bash
docker compose up -d
```

### Testes

```bash
cd backend
python -m pytest tests/ -v
```

## API — Endpoints Principais

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/api/pipeline/quick-start` | Upload + letra + pipeline automático |
| `POST` | `/api/projects` | Criar projeto |
| `POST` | `/api/audio/{id}/upload` | Upload instrumental |
| `POST` | `/api/pipeline/{id}/start` | Iniciar pipeline completo |
| `GET` | `/api/pipeline/{id}/status` | Status do pipeline |
| `POST` | `/api/melody/{id}/extract` | Extrair melodia |
| `POST` | `/api/synthesis/{id}/render` | Sintetizar vocal |
| `POST` | `/api/refinement/{id}/convert` | Refinar timbre |
| `POST` | `/api/mix/{id}/render` | Renderizar mix |
| `POST` | `/api/mix/{id}/export` | Exportar (WAV/FLAC/MP3/OGG) |
| `GET` | `/api/templates` | Listar templates |
| `POST` | `/api/batch/start` | Batch processing |
| `WS` | `/ws/{project_id}` | Progresso em tempo real |

## Pipeline

```
Upload → Análise (BPM, key) → Melodia (PYIN) → Síntese (DiffSinger/ACE-Step)
    → Refinamento (RVC) → Mixagem (Pedalboard) → Export
```

Cada engine AI tem um **fallback funcional** quando não está instalado:
- **DiffSinger/ACE-Step** → síntese sinusoidal placeholder
- **RVC/Applio** → pitch-shift simples
- **Pedalboard** → cadeia NumPy/SciPy equivalente

## Licença

Projeto privado.
