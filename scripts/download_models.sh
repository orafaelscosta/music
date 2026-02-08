#!/bin/bash
# ClovisAI — Download de modelos AI
set -e

echo "=========================================="
echo "  ClovisAI — Download de Modelos"
echo "=========================================="

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo "NOTA: Este script lista os modelos necessários."
echo "Devido ao tamanho dos modelos, o download é manual."
echo ""

echo "=== 1. DiffSinger Voicebanks ==="
echo "  Leif (multilingual): ~500 MB"
echo "    -> https://github.com/lottev1991/Leif-DiffSinger"
echo "    -> Destino: engines/voicebanks/italian/"
echo ""
echo "  BRAPA PT-BR voices: ~300 MB"
echo "    -> https://github.com/Team-BRAPA"
echo "    -> Destino: engines/voicebanks/portuguese/"
echo ""

echo "=== 2. ACE-Step v1.5 ==="
echo "  Modelo base: ~3.5 GB"
echo "  Lyric2Vocal LoRA: ~200 MB"
echo "    -> https://huggingface.co/ACE-Step/ACE-Step-v1-5"
echo "    -> Destino: engines/ace-step/"
echo ""

echo "=== 3. Applio/RVC ==="
echo "  Pretrained models: ~1 GB"
echo "  Hubert base: ~200 MB"
echo "    -> https://github.com/IAHispano/Applio"
echo "    -> Destino: engines/applio/"
echo ""

echo "=== 4. Demucs (htdemucs_ft) ==="
echo "  Modelo: ~800 MB"
echo "    -> Baixado automaticamente via: python -m demucs --model htdemucs_ft"
echo ""

echo "=== 5. Basic Pitch ==="
echo "  Modelo Spotify: ~50 MB"
echo "    -> Baixado automaticamente via: pip install basic-pitch"
echo ""

echo "Total estimado: ~6-7 GB"
echo ""
echo "Para instalar o Applio (engine RVC):"
echo "  cd engines/applio"
echo "  git clone https://github.com/IAHispano/Applio.git ."
echo "  pip install -r requirements.txt"
echo ""
