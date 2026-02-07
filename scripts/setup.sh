#!/bin/bash
# AI Vocal Studio — Script de instalação completa
set -e

echo "=========================================="
echo "  AI Vocal Studio — Setup"
echo "=========================================="

# Diretório raiz do projeto
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 1. Criar diretórios
echo ""
echo "[1/6] Criando diretórios..."
mkdir -p storage/projects
mkdir -p engines/{diffsinger,ace-step,applio,demucs}
mkdir -p engines/voicebanks/{italian,portuguese}

# 2. Copiar .env se não existir
if [ ! -f .env ]; then
    echo "[2/6] Criando .env a partir do template..."
    cp .env.example .env
    echo "  -> .env criado. Edite conforme necessário."
else
    echo "[2/6] .env já existe, pulando..."
fi

# 3. Backend — Python
echo ""
echo "[3/6] Configurando backend Python..."
cd "$PROJECT_ROOT/backend"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt
deactivate
echo "  -> Backend configurado."

# 4. Frontend — Node.js
echo ""
echo "[4/6] Configurando frontend Next.js..."
cd "$PROJECT_ROOT/frontend"
npm install
echo "  -> Frontend configurado."

# 5. Verificar Redis
echo ""
echo "[5/6] Verificando Redis..."
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo "  -> Redis está rodando."
    else
        echo "  -> Redis instalado mas não está rodando. Inicie com: redis-server"
    fi
else
    echo "  -> Redis não encontrado. Instale com: sudo apt install redis-server"
    echo "     Ou use Docker: docker compose up redis -d"
fi

# 6. Verificar dependências de sistema
echo ""
echo "[6/6] Verificando dependências de sistema..."
MISSING=""
for cmd in ffmpeg python3; do
    if ! command -v $cmd &> /dev/null; then
        MISSING="$MISSING $cmd"
    fi
done

if [ -n "$MISSING" ]; then
    echo "  -> Dependências faltando:$MISSING"
    echo "     Instale com: sudo apt install$MISSING"
else
    echo "  -> Todas as dependências de sistema encontradas."
fi

echo ""
echo "=========================================="
echo "  Setup concluído!"
echo "=========================================="
echo ""
echo "Para iniciar em modo desenvolvimento:"
echo "  Backend:  cd backend && source .venv/bin/activate && uvicorn main:app --reload"
echo "  Frontend: cd frontend && npm run dev"
echo "  Worker:   cd backend && celery -A workers.tasks worker --loglevel=info"
echo ""
echo "Ou use Docker Compose:"
echo "  docker compose up -d"
echo ""
