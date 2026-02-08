# ClovisAI — Claude Code Instructions

## Projeto
Sistema web de criação musical com IA — geração de vocais sobre instrumentais existentes.
Stack: Next.js 14 + FastAPI + Python AI engines.

## Regras de Código

### Backend (Python)
- Python 3.11+
- FastAPI com tipagem completa (Pydantic v2)
- Async/await em todos os endpoints
- Celery para jobs pesados (>5s de processamento)
- Logging estruturado com structlog
- Docstrings em português
- Type hints obrigatórios
- Tests com pytest + pytest-asyncio

### Frontend (TypeScript)
- Next.js 14 App Router
- TypeScript strict mode
- Tailwind CSS (sem CSS modules)
- Server Components por padrão, Client Components apenas quando necessário
- Zustand para state management
- React Query para data fetching
- Componentes no padrão: PascalCase, um componente por arquivo

### Geral
- Commits em português, formato conventional commits
- Variáveis de ambiente em .env (nunca hardcoded)
- Docker para todos os serviços
- Todos os paths de áudio são relativos ao storage/
- Erros retornam JSON padronizado: { "error": str, "detail": str }

## Comandos Úteis
- `docker compose up -d` — subir todos os serviços
- `cd frontend && npm run dev` — dev frontend
- `cd backend && uvicorn main:app --reload` — dev backend
- `celery -A workers.tasks worker --loglevel=info` — worker de jobs
- `python scripts/test_engines.py` — verificar engines AI

## Ordem de Implementação
Sempre seguir a ordem das fases no plano do projeto.
Cada fase deve ter seus testes antes de avançar para a próxima.

## Engines AI — Configuração
- DiffSinger: engines/diffsinger/ — requer voicebanks em engines/voicebanks/
- ACE-Step: engines/ace-step/ — modelo baixado via download_models.sh
- Applio: engines/applio/ — fork em engines/applio/
- Basic Pitch: pip install basic-pitch
- Demucs: pip install demucs
- Pedalboard: pip install pedalboard

## Prioridades
1. Funcionalidade > Estética (mas manter UI limpa)
2. DiffSinger é o engine principal, ACE-Step é backup/rápido
3. Italiano é o idioma prioritário, depois português
4. Sempre oferecer preview antes de render completo
5. WebSocket para todo feedback de progresso
