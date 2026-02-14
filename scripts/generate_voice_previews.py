#!/usr/bin/env python3
"""Gera previews de áudio (~10s) para cada voice preset usando ACE-Step.

Uso: cd backend && python ../scripts/generate_voice_previews.py
"""

import asyncio
import subprocess
import sys
from pathlib import Path

# Adicionar backend ao path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from services.acestep import ACEStepService, ACEStepConfig, build_acestep_prompt
from api.routes.voices import VOICE_PRESETS
from config import settings

OUTPUT_DIR = settings.storage_path / "voice-previews"
DURATION = 10.0
SEED = 42
INFERENCE_STEPS = 40  # Menos steps para gerar rápido, qualidade OK para preview
GUIDANCE = 5.0

# Letras curtas para cada idioma/estilo — demonstram timbre
PREVIEW_LYRICS = {
    "default": (
        "[verse]\n"
        "La la la, singing for you\n"
        "Feel the music in the air\n"
        "Every note, every word\n"
        "Dancing through the night"
    ),
    "operatic": (
        "[verse]\n"
        "Nel blu dipinto di blu\n"
        "Felice di stare lassù\n"
        "E volavo volavo\n"
        "Felice più in alto del sole"
    ),
    "jazz": (
        "[verse]\n"
        "The night is young and so are we\n"
        "Moonlight falling soft and free\n"
        "A melody of dreams\n"
        "Floating on the breeze"
    ),
    "rock": (
        "[verse]\n"
        "Fire in my veins tonight\n"
        "Breaking through the walls of light\n"
        "Screaming at the sky above\n"
        "Nothing's ever gonna be enough"
    ),
    "hiphop": (
        "[verse]\n"
        "Yeah, stepping to the beat\n"
        "Flow is cold, the rhyme is heat\n"
        "Moving through the city streets\n"
        "Every bar I spit's elite"
    ),
    "bossa": (
        "[verse]\n"
        "Olha que coisa mais linda\n"
        "Mais cheia de graça\n"
        "É ela menina\n"
        "Que vem e que passa"
    ),
    "gospel": (
        "[verse]\n"
        "Amazing grace how sweet the sound\n"
        "That saved a wretch like me\n"
        "I once was lost but now I'm found\n"
        "Was blind but now I see"
    ),
    "country": (
        "[verse]\n"
        "Dusty road beneath my feet\n"
        "Stars above the old main street\n"
        "Guitar playing soft and slow\n"
        "Wind tells stories as I go"
    ),
    "ethereal": (
        "[verse]\n"
        "Floating through the silver clouds\n"
        "Whispers in the starlit shroud\n"
        "Dreaming of a world unseen\n"
        "Lost in waves of blue and green"
    ),
    "indie": (
        "[verse]\n"
        "Quiet morning light comes in\n"
        "Coffee steam and violin\n"
        "Pages turning, time stands still\n"
        "Softly breathing on the windowsill"
    ),
    "metal": (
        "[verse]\n"
        "Darkness falls upon the throne\n"
        "Crushing steel and breaking bone\n"
        "Thunder roars beneath the ground\n"
        "Chaos reigns without a sound"
    ),
    "soul": (
        "[verse]\n"
        "Deep inside my heart I know\n"
        "Love is more than just a show\n"
        "Feel it burning like a flame\n"
        "Nothing's ever quite the same"
    ),
    "rnb": (
        "[verse]\n"
        "Baby when you look at me\n"
        "Everything I want to be\n"
        "Running through my melody\n"
        "You're the harmony I need"
    ),
    "punk": (
        "[verse]\n"
        "Tear it down and start again\n"
        "No more rules no more pretend\n"
        "Burning bright against the grain\n"
        "Dancing wild in the rain"
    ),
}

# Mapear cada preset para um tipo de letra
PRESET_LYRICS_MAP = {
    "tenor_lirico": "operatic",
    "baritono_pop": "default",
    "tenor_rock": "rock",
    "crooner_jazz": "jazz",
    "soprano_lirica": "operatic",
    "mezzo_pop": "default",
    "alto_indie": "indie",
    "soprano_ethereal": "ethereal",
    "contratenor": "operatic",
    "soul_gospel": "soul",
    "rapper_mc": "hiphop",
    "country_masculino": "country",
    "indie_soft_male": "indie",
    "metal_gutural": "metal",
    "diva_rnb": "rnb",
    "country_feminino": "country",
    "punk_feminino": "punk",
    "jazz_lounge": "jazz",
    "mpb_bossa": "bossa",
    "gospel_feminino": "gospel",
}


def get_lyrics_for_preset(preset_id: str) -> str:
    """Retorna letras adequadas ao estilo do preset."""
    style_key = PRESET_LYRICS_MAP.get(preset_id, "default")
    return PREVIEW_LYRICS.get(style_key, PREVIEW_LYRICS["default"])


def get_prompt_for_preset(preset: dict) -> str:
    """Constrói prompt ACE-Step a partir dos dados do preset."""
    return build_acestep_prompt(
        language="en",  # Previews em inglês (mais universal para ACE-Step)
        vocal_style="pop",
        gender=preset["gender"],
        voice_tags=preset["tags"],
    )


async def generate_preview(svc: ACEStepService, preset: dict, output_dir: Path) -> bool:
    """Gera preview WAV para um preset."""
    preset_id = preset["id"]
    wav_path = output_dir / f"{preset_id}.wav"
    mp3_path = output_dir / f"{preset_id}.mp3"

    # Pular se já existe MP3
    if mp3_path.exists():
        print(f"  ⏭  {preset_id} — já existe, pulando")
        return True

    lyrics = get_lyrics_for_preset(preset_id)
    prompt = get_prompt_for_preset(preset)

    print(f"  🎵 {preset_id} ({preset['name']})")
    print(f"     Prompt: {prompt}")

    config = ACEStepConfig(
        lyrics=lyrics,
        language="en",
        duration_seconds=DURATION,
        seed=SEED,
        guidance_scale=GUIDANCE,
        num_inference_steps=INFERENCE_STEPS,
        prompt=prompt,
    )

    try:
        await svc.generate(wav_path, config)

        # Converter WAV → MP3 com ffmpeg
        if wav_path.exists():
            result = subprocess.run(
                [
                    "ffmpeg", "-y", "-i", str(wav_path),
                    "-codec:a", "libmp3lame", "-b:a", "192k",
                    "-ar", "44100",
                    str(mp3_path),
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and mp3_path.exists():
                wav_path.unlink()  # Remover WAV original
                size_kb = mp3_path.stat().st_size / 1024
                print(f"     ✅ OK — {size_kb:.0f} KB")
                return True
            else:
                print(f"     ⚠️  ffmpeg falhou: {result.stderr[:200]}")
                # Manter WAV como fallback
                if wav_path.exists():
                    print(f"     📦 Mantendo WAV como fallback")
                    return True
                return False
        else:
            print(f"     ❌ WAV não foi gerado")
            return False

    except Exception as e:
        print(f"     ❌ Erro: {e}")
        return False


async def main():
    print("=" * 60)
    print("🎤 Gerando previews de voz para a biblioteca")
    print(f"   Presets: {len(VOICE_PRESETS)}")
    print(f"   Duração: {DURATION}s | Steps: {INFERENCE_STEPS} | Seed: {SEED}")
    print(f"   Output: {OUTPUT_DIR}")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    svc = ACEStepService()

    if not svc.is_available():
        print("❌ ACE-Step não está disponível!")
        print(f"   Engine path: {svc.engine_path}")
        print(f"   Model path: {svc.model_path}")
        sys.exit(1)

    print(f"✅ ACE-Step disponível\n")

    success = 0
    failed = 0

    for i, preset in enumerate(VOICE_PRESETS, 1):
        print(f"\n[{i}/{len(VOICE_PRESETS)}] ", end="")
        ok = await generate_preview(svc, preset, OUTPUT_DIR)
        if ok:
            success += 1
        else:
            failed += 1

    print("\n" + "=" * 60)
    print(f"✅ Sucesso: {success} | ❌ Falha: {failed}")
    print(f"📁 Arquivos em: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
