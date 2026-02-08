#!/usr/bin/env python3
"""Testa a disponibilidade dos engines de IA e bibliotecas."""

import sys
from pathlib import Path

# Adicionar backend ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def check(name: str, check_fn) -> bool:
    """Verifica se um componente está disponível."""
    try:
        result = check_fn()
        status = "\033[32m[OK]\033[0m"
        print(f"  {status} {name}: {result}")
        return True
    except Exception as e:
        status = "\033[31m[--]\033[0m"
        print(f"  {status} {name}: {e}")
        return False


def main():
    print()
    print("\033[1m" + "=" * 55)
    print("  AI Vocal Studio — Verificação de Ambiente")
    print("=" * 55 + "\033[0m")
    print()

    results = {}

    # === Bibliotecas Python ===
    print("\033[1mBibliotecas Python:\033[0m")
    for lib in ["librosa", "soundfile", "numpy", "scipy"]:
        results[lib] = check(lib, lambda l=lib: __import__(l).__version__)
    results["mido"] = check("mido", lambda: (
        __import__("mido"), "disponível"
    )[-1])

    results["sqlalchemy"] = check(
        "sqlalchemy", lambda: __import__("sqlalchemy").__version__
    )
    results["fastapi"] = check(
        "fastapi", lambda: __import__("fastapi").__version__
    )

    # === Engines AI ===
    print()
    print("\033[1mEngines de IA:\033[0m")

    base = Path(__file__).parent.parent

    # DiffSinger
    ds_path = base / "engines" / "diffsinger"
    results["diffsinger"] = check("DiffSinger", lambda: (
        "disponível" if ds_path.exists()
        and any(ds_path.glob("*.py"))
        else "não instalado (placeholder ativo)"
    ))

    # ACE-Step
    as_path = base / "engines" / "ace-step"
    results["acestep"] = check("ACE-Step", lambda: (
        "disponível" if as_path.exists()
        and any(as_path.glob("*.py"))
        else "não instalado (placeholder ativo)"
    ))

    # Pedalboard
    try:
        import pedalboard
        results["pedalboard"] = check("Pedalboard", lambda: pedalboard.__version__)
    except ImportError:
        results["pedalboard"] = check(
            "Pedalboard", lambda: "não instalado (fallback NumPy/SciPy ativo)"
        )

    # === Serviços Backend ===
    print()
    print("\033[1mServiços Backend (fallback):\033[0m")

    results["analyzer"] = check("AudioAnalyzer", lambda: (
        __import__("services.analyzer", fromlist=["AudioAnalyzer"]).AudioAnalyzer,
        "importado com sucesso"
    )[-1])

    results["melody"] = check("MelodyService", lambda: (
        __import__("services.melody", fromlist=["MelodyService"]).MelodyService,
        "importado com sucesso"
    )[-1])

    results["diffsinger_svc"] = check("DiffSingerService", lambda: (
        __import__("services.diffsinger", fromlist=["DiffSingerService"])
        .DiffSingerService(),
        "importado (placeholder ativo)"
    )[-1])

    results["acestep_svc"] = check("ACEStepService", lambda: (
        __import__("services.acestep", fromlist=["ACEStepService"])
        .ACEStepService(),
        "importado (placeholder ativo)"
    )[-1])

    results["rvc_svc"] = check("RVCService", lambda: (
        __import__("services.rvc", fromlist=["RVCService"]).RVCService(),
        "importado (fallback pitch-shift)"
    )[-1])

    results["mixer_svc"] = check("MixerService", lambda: (
        __import__("services.mixer", fromlist=["MixerService"]).MixerService(),
        "importado"
    )[-1])

    # === Diretórios ===
    print()
    print("\033[1mDiretórios:\033[0m")
    for name, path in [
        ("Storage", base / "storage"),
        ("Projects", base / "storage" / "projects"),
        ("DiffSinger", base / "engines" / "diffsinger"),
        ("Voicebanks", base / "engines" / "voicebanks"),
        ("ACE-Step", base / "engines" / "ace-step"),
        ("Applio/RVC", base / "engines" / "applio"),
    ]:
        exists = path.exists()
        has_content = exists and any(path.iterdir()) if exists else False
        if has_content:
            print(f"  \033[32m[OK]\033[0m {name}: {path}")
        elif exists:
            print(f"  \033[33m[--]\033[0m {name}: vazio ({path})")
        else:
            print(f"  \033[31m[--]\033[0m {name}: não existe ({path})")

    # === GPU ===
    print()
    print("\033[1mGPU:\033[0m")
    try:
        import torch
        if torch.cuda.is_available():
            gpu = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_mem / (1024**3)
            print(f"  \033[32m[OK]\033[0m CUDA: {gpu} ({vram:.1f} GB VRAM)")
        else:
            print("  \033[33m[--]\033[0m CUDA não disponível (modo CPU)")
    except ImportError:
        print(
            "  \033[33m[--]\033[0m PyTorch não instalado "
            "(não necessário para placeholders)"
        )

    # === Resumo ===
    print()
    print("\033[1m" + "=" * 55)
    ok = sum(1 for v in results.values() if v)
    total = len(results)
    color = (
        "\033[32m" if ok == total
        else "\033[33m" if ok > total // 2
        else "\033[31m"
    )
    print(f"  {color}Resultado: {ok}/{total} componentes funcionando\033[0m")
    print(
        "  O sistema funciona com placeholders mesmo sem engines AI."
    )
    print("=" * 55 + "\033[0m")
    print()


if __name__ == "__main__":
    main()
