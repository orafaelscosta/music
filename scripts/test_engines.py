#!/usr/bin/env python3
"""Testa a disponibilidade dos engines de IA."""

import sys
from pathlib import Path

# Adicionar backend ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def check_engine(name: str, check_fn) -> bool:
    """Verifica se um engine está disponível."""
    try:
        result = check_fn()
        print(f"  [OK] {name}: {result}")
        return True
    except Exception as e:
        print(f"  [FALHOU] {name}: {e}")
        return False


def main():
    print("=" * 50)
    print("  AI Vocal Studio — Teste de Engines")
    print("=" * 50)
    print()

    results = {}

    # 1. librosa (análise de áudio)
    print("Bibliotecas Python:")
    results["librosa"] = check_engine(
        "librosa",
        lambda: __import__("librosa").__version__,
    )

    results["soundfile"] = check_engine(
        "soundfile",
        lambda: __import__("soundfile").__version__,
    )

    results["numpy"] = check_engine(
        "numpy",
        lambda: __import__("numpy").__version__,
    )

    # 2. Basic Pitch
    print()
    print("Engines AI:")
    results["basic_pitch"] = check_engine(
        "Basic Pitch",
        lambda: __import__("basic_pitch").__version__
        if __import__("importlib").util.find_spec("basic_pitch")
        else (_ for _ in ()).throw(ImportError("não instalado")),
    )

    # 3. Demucs
    results["demucs"] = check_engine(
        "Demucs",
        lambda: "disponível"
        if __import__("importlib").util.find_spec("demucs")
        else (_ for _ in ()).throw(ImportError("não instalado")),
    )

    # 4. Pedalboard
    results["pedalboard"] = check_engine(
        "Pedalboard",
        lambda: __import__("pedalboard").__version__
        if __import__("importlib").util.find_spec("pedalboard")
        else (_ for _ in ()).throw(ImportError("não instalado")),
    )

    # 5. Verificar diretórios de engines
    print()
    print("Diretórios de engines:")
    engines_dir = Path(__file__).parent.parent / "engines"

    for engine_name in ["diffsinger", "ace-step", "applio", "demucs"]:
        engine_path = engines_dir / engine_name
        has_content = engine_path.exists() and any(engine_path.iterdir()) if engine_path.exists() else False
        status = "configurado" if has_content else "vazio"
        print(f"  {'[OK]' if has_content else '[--]'} {engine_name}: {status}")

    # 6. Verificar voicebanks
    print()
    print("Voicebanks:")
    voicebanks_dir = engines_dir / "voicebanks"
    for lang in ["italian", "portuguese"]:
        lang_dir = voicebanks_dir / lang
        count = len(list(lang_dir.iterdir())) if lang_dir.exists() else 0
        print(f"  {'[OK]' if count > 0 else '[--]'} {lang}: {count} voz(es)")

    # 7. GPU
    print()
    print("GPU:")
    try:
        import torch

        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_mem / (1024**3)
            print(f"  [OK] CUDA: {gpu_name} ({vram:.1f} GB VRAM)")
        else:
            print("  [--] CUDA não disponível (modo CPU)")
    except ImportError:
        print("  [--] PyTorch não instalado")

    # Resumo
    print()
    print("=" * 50)
    ok_count = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"  Resultado: {ok_count}/{total} bibliotecas disponíveis")
    print("=" * 50)


if __name__ == "__main__":
    main()
