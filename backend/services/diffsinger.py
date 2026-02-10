"""Wrapper para o engine DiffSinger — síntese vocal a partir de MIDI + letra."""

import asyncio
import json
import re
from pathlib import Path

import numpy as np
import soundfile as sf
import structlog

logger = structlog.get_logger()

# ─── Italian Grapheme-to-Phoneme (regras simplificadas) ───

# Mapa de grafemas italianos → fonemas intermediários (dsdict-it style)
_IT_DIGRAPHS = [
    ("gli", "LL i"),
    ("gn", "JJ"),
    ("sci", "SS i"),
    ("sce", "SS e"),
    ("sch", "s k"),
    ("chi", "k i"),
    ("che", "k e"),
    ("ghi", "g i"),
    ("ghe", "g e"),
    ("ci", "tSS i"),
    ("ce", "tSS e"),
    ("gi", "dZZ i"),
    ("ge", "dZZ e"),
    ("qu", "k w"),
    ("cc", "k k"),
    ("ss", "s s"),
    ("zz", "ts ts"),
    ("ll", "l l"),
    ("rr", "r r"),
    ("mm", "m m"),
    ("nn", "n n"),
    ("pp", "p p"),
    ("tt", "t t"),
    ("bb", "b b"),
    ("dd", "d d"),
    ("ff", "f f"),
    ("gg", "g g"),
]

_IT_SINGLE = {
    "a": "a", "e": "e", "i": "i", "o": "o", "u": "u",
    "à": "a", "è": "EE", "é": "e", "ì": "i", "ò": "OO", "ó": "o", "ù": "u",
    "b": "b", "c": "k", "d": "d", "f": "f", "g": "g",
    "h": "", "j": "j", "k": "k", "l": "l", "m": "m",
    "n": "n", "p": "p", "r": "r", "s": "s", "t": "t",
    "v": "v", "w": "w", "x": "k s", "z": "ts",
}

# Tabela de replacements do dsdict-it.yaml: fonema intermediário → fonema do modelo
_IT_REPLACEMENTS = {
    "a": "es/a", "b": "es/b", "d": "pt/d", "dz": "ja/z", "dZZ": "pt/dj",
    "e": "es/e", "EE": "pt/eh", "f": "pt/f", "g": "es/g", "i": "es/i",
    "j": "es/y", "JJ": "es/nJ", "k": "pt/k", "l": "es/l", "LL": "pt/lh",
    "m": "pt/m", "n": "pt/n", "nf": "pt/n", "ng": "pt/ng",
    "o": "es/o", "OO": "pt/oh", "p": "pt/p", "r": "es/r", "s": "pt/s",
    "SS": "pt/sh", "t": "es/t", "ts": "ja/ts", "tSS": "pt/ch",
    "u": "pt/u", "v": "pt/v", "w": "es/w", "z": "pt/z",
}

# Prefixo → language ID
_LANG_PREFIX_MAP = {"en": 1, "es": 2, "ja": 3, "ko": 4, "pt": 5, "zh": 6}


def _italian_g2p(text: str) -> list[str]:
    """Converte texto italiano para sequência de fonemas do modelo."""
    text = text.lower().strip()
    if not text:
        return ["SP"]

    model_phonemes = []
    i = 0
    while i < len(text):
        if not text[i].isalpha():
            if model_phonemes and model_phonemes[-1] != "SP":
                model_phonemes.append("SP")
            i += 1
            continue

        matched = False
        for grapheme, intermediate in _IT_DIGRAPHS:
            if text[i:i + len(grapheme)] == grapheme:
                for ph in intermediate.split():
                    if ph in _IT_REPLACEMENTS:
                        model_phonemes.append(_IT_REPLACEMENTS[ph])
                    elif ph:
                        model_phonemes.append(ph)
                i += len(grapheme)
                matched = True
                break

        if not matched:
            ch = text[i]
            intermediate = _IT_SINGLE.get(ch, "")
            for ph in intermediate.split():
                if ph in _IT_REPLACEMENTS:
                    model_phonemes.append(_IT_REPLACEMENTS[ph])
            i += 1

    return model_phonemes if model_phonemes else ["SP"]


# ─── Portuguese Grapheme-to-Phoneme ───

_PT_DIGRAPHS = [
    ("lh", ["pt/lh"]),
    ("nh", ["pt/nh"]),
    ("ch", ["pt/sh"]),
    ("rr", ["pt/rr"]),
    ("ss", ["pt/s"]),
    ("qu", ["pt/k"]),
    ("gu", ["pt/g"]),
    ("ão", ["pt/an", "pt/u0"]),
    ("õe", ["pt/on", "pt/i0"]),
    ("ou", ["pt/o", "pt/u0"]),
    ("ei", ["pt/e", "pt/i0"]),
    ("ai", ["pt/a", "pt/i0"]),
    ("oi", ["pt/o", "pt/i0"]),
    ("au", ["pt/a", "pt/u0"]),
    ("am", ["pt/an"]),
    ("an", ["pt/an"]),
    ("em", ["pt/en"]),
    ("en", ["pt/en"]),
    ("im", ["pt/in"]),
    ("in", ["pt/in"]),
    ("om", ["pt/on"]),
    ("on", ["pt/on"]),
    ("um", ["pt/un"]),
    ("un", ["pt/un"]),
]

_PT_SINGLE: dict[str, list[str]] = {
    "a": ["pt/a"], "á": ["pt/a"], "â": ["pt/ax"], "ã": ["pt/an"],
    "e": ["pt/e"], "é": ["pt/eh"], "ê": ["pt/e"],
    "i": ["pt/i"], "í": ["pt/i"],
    "o": ["pt/o"], "ó": ["pt/oh"], "ô": ["pt/o"],
    "u": ["pt/u"], "ú": ["pt/u"],
    "b": ["pt/b"], "c": ["pt/k"], "ç": ["pt/s"],
    "d": ["pt/d"], "f": ["pt/f"], "g": ["pt/g"],
    "h": [],  # mudo
    "j": ["pt/j"], "k": ["pt/k"], "l": ["pt/l"],
    "m": ["pt/m"], "n": ["pt/n"], "p": ["pt/p"],
    "r": ["pt/r"], "s": ["pt/s"], "t": ["pt/t"],
    "v": ["pt/v"], "w": ["pt/v"], "x": ["pt/sh"],
    "y": ["pt/i"], "z": ["pt/z"],
}


def _portuguese_g2p(text: str) -> list[str]:
    """Converte texto português para sequência de fonemas pt/ do modelo."""
    text = text.lower().strip()
    if not text:
        return ["SP"]

    # Normalizar acentos comuns de input sem acento
    text = text.replace("cao", "ção").replace("nao", "não")

    phonemes: list[str] = []
    i = 0
    while i < len(text):
        if not text[i].isalpha() and text[i] not in "áàâãéêíóôõúç":
            if phonemes and phonemes[-1] != "SP":
                phonemes.append("SP")
            i += 1
            continue

        # Tentar digrafos
        matched = False
        for grapheme, phs in _PT_DIGRAPHS:
            if text[i:i + len(grapheme)] == grapheme:
                phonemes.extend(phs)
                i += len(grapheme)
                matched = True
                break

        if not matched:
            ch = text[i]
            phs = _PT_SINGLE.get(ch, [])
            phonemes.extend(phs)
            i += 1

    return phonemes if phonemes else ["SP"]


def _g2p(text: str, language: str) -> list[str]:
    """Seleciona G2P correto baseado no idioma."""
    if language == "pt":
        return _portuguese_g2p(text)
    elif language == "it":
        return _italian_g2p(text)
    else:
        # Fallback: usar português
        return _portuguese_g2p(text)


def _get_lang_id_for_config(language: str) -> int:
    """Retorna language ID consistente baseado no idioma do projeto."""
    _CONFIG_LANG_MAP = {
        "it": 5,   # Italiano → Português (mais similar foneticamente)
        "pt": 5,   # Português
        "es": 2,   # Espanhol
        "en": 1,   # Inglês
        "ja": 3,   # Japonês
        "ko": 4,   # Coreano
        "zh": 6,   # Chinês
    }
    return _CONFIG_LANG_MAP.get(language, 5)


class DiffSingerConfig:
    """Configurações para renderização DiffSinger."""

    def __init__(
        self,
        voicebank: str = "umidaji",
        language: str = "it",
        breathiness: float = 0.0,
        tension: float = 0.0,
        energy: float = 1.0,
        voicing: float = 1.0,
        pitch_deviation: float = 0.0,
        gender: float = 0.0,
        sample_rate: int = 44100,
        speaker: str = "",
        diffusion_steps: int = 50,
    ):
        self.voicebank = voicebank
        self.language = language
        self.breathiness = breathiness
        self.tension = tension
        self.energy = energy
        self.voicing = voicing
        self.pitch_deviation = pitch_deviation
        self.gender = gender
        self.sample_rate = sample_rate
        self.speaker = speaker
        self.diffusion_steps = diffusion_steps

    def to_dict(self) -> dict:
        return {
            "voicebank": self.voicebank,
            "language": self.language,
            "breathiness": self.breathiness,
            "tension": self.tension,
            "energy": self.energy,
            "voicing": self.voicing,
            "pitch_deviation": self.pitch_deviation,
            "gender": self.gender,
            "sample_rate": self.sample_rate,
            "speaker": self.speaker,
            "diffusion_steps": self.diffusion_steps,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DiffSingerConfig":
        valid_keys = {
            "voicebank", "language", "breathiness", "tension", "energy",
            "voicing", "pitch_deviation", "gender", "sample_rate", "speaker",
            "diffusion_steps",
        }
        return cls(**{k: v for k, v in data.items() if k in valid_keys})


class DiffSingerService:
    """Serviço de síntese vocal usando DiffSinger (ONNX/OpenUTAU voicebanks)."""

    def __init__(self, engine_path: Path | None = None):
        from config import settings
        self.engine_path = engine_path or settings.diffsinger_path
        self.voicebanks_path = settings.voicebanks_path

    def is_available(self) -> bool:
        """Verifica se há voicebanks DiffSinger instalados."""
        if not self.voicebanks_path.exists():
            return False
        for lang_dir in self.voicebanks_path.iterdir():
            if not lang_dir.is_dir():
                continue
            for vb_dir in lang_dir.iterdir():
                if not vb_dir.is_dir():
                    continue
                if list(vb_dir.rglob("acoustic.onnx")):
                    return True
        return False

    def list_voicebanks(self) -> list[dict]:
        """Lista voicebanks disponíveis."""
        voicebanks = []
        if not self.voicebanks_path.exists():
            return voicebanks

        for lang_dir in self.voicebanks_path.iterdir():
            if not lang_dir.is_dir() or lang_dir.name.startswith("."):
                continue
            for vb_dir in lang_dir.iterdir():
                if not vb_dir.is_dir() or vb_dir.name.startswith("."):
                    continue

                configs = list(vb_dir.rglob("dsconfig.yaml"))
                if not configs:
                    continue

                config_path = configs[0]
                model_dir = config_path.parent

                speakers = []
                try:
                    import yaml
                    with open(config_path) as f:
                        ds_cfg = yaml.safe_load(f)
                    speakers = ds_cfg.get("speakers", [])
                except Exception:
                    pass

                has_onnx = bool(list(model_dir.rglob("acoustic.onnx")))

                voicebanks.append({
                    "name": vb_dir.name,
                    "language": lang_dir.name,
                    "path": str(model_dir),
                    "has_model": has_onnx,
                    "speakers": speakers,
                    "config_path": str(config_path),
                })
        return voicebanks

    def _find_voicebank(self, name: str) -> Path | None:
        """Encontra o diretório de um voicebank pelo nome."""
        for vb in self.list_voicebanks():
            if vb["name"].lower() == name.lower() or name.lower() in vb["name"].lower():
                return Path(vb["path"])
        return None

    def _find_voicebank_root(self, name: str) -> Path | None:
        """Encontra a raiz do voicebank (diretório que contém dsmain/)."""
        for vb in self.list_voicebanks():
            if vb["name"].lower() == name.lower() or name.lower() in vb["name"].lower():
                vb_path = Path(vb["path"])
                # Subir até encontrar o diretório que contém dsmain/
                for candidate in [vb_path, vb_path.parent, vb_path.parent.parent]:
                    if (candidate / "dsmain").exists():
                        return candidate
                # Buscar dsmain/ dentro do path
                dsmain_dirs = list(vb_path.rglob("dsmain"))
                if dsmain_dirs:
                    return dsmain_dirs[0].parent
                return vb_path
        return None

    async def synthesize(
        self,
        melody_json_path: Path,
        output_path: Path,
        config: DiffSingerConfig,
        preview_seconds: float | None = None,
    ) -> Path:
        """Sintetiza vocal a partir de melodia JSON + configuração."""
        return await asyncio.to_thread(
            self._synthesize_sync, melody_json_path, output_path, config, preview_seconds
        )

    def _synthesize_sync(
        self,
        melody_json_path: Path,
        output_path: Path,
        config: DiffSingerConfig,
        preview_seconds: float | None = None,
    ) -> Path:
        """Síntese síncrona via DiffSinger."""
        logger.info(
            "diffsinger_sintese_iniciada",
            voicebank=config.voicebank,
            language=config.language,
        )

        with open(melody_json_path) as f:
            melody_data = json.load(f)

        notes = melody_data.get("notes", [])
        if not notes:
            raise ValueError("Melodia sem notas para sintetizar")

        if preview_seconds:
            notes = [n for n in notes if n["start_time"] < preview_seconds]

        # Pré-processar notas: filtrar artefatos e resolver overlaps
        bpm = melody_data.get("bpm", 120.0)
        notes = self._preprocess_notes(notes, bpm=bpm)

        vb_root = self._find_voicebank_root(config.voicebank)
        if vb_root:
            try:
                return self._run_full_pipeline(
                    notes, output_path, config, vb_root, preview_seconds
                )
            except Exception as e:
                logger.error("diffsinger_pipeline_erro", error=str(e), exc_info=True)
                logger.warning("diffsinger_fallback_apos_erro")

        logger.warning("diffsinger_nao_disponivel_usando_fallback")
        return self._generate_placeholder(notes, output_path, config, preview_seconds)

    def _preprocess_notes(self, notes: list[dict], bpm: float = 120.0) -> list[dict]:
        """Pré-processa notas: filtra artefatos e resolve overlaps."""
        if not notes:
            return notes

        base_notes = list(notes)
        n_with_lyrics = sum(1 for n in base_notes if n.get("lyric", "").strip())

        logger.info(
            "notas_pre_filtragem",
            total=len(base_notes),
            com_letra=n_with_lyrics,
        )

        # 1. Filtrar notas muito curtas (< 100ms)
        base_notes = [
            n for n in base_notes
            if (n["end_time"] - n["start_time"]) >= 0.1
        ]

        if not base_notes:
            return notes[:50]

        # 2. Ordenar e resolver overlaps
        base_notes.sort(key=lambda n: n["start_time"])
        merged = []
        for note in base_notes:
            if merged and note["start_time"] < merged[-1]["end_time"]:
                # Overlap — manter a mais longa
                if (note["end_time"] - note["start_time"]) > (
                    merged[-1]["end_time"] - merged[-1]["start_time"]
                ):
                    merged[-1] = note
            else:
                merged.append(note)

        # 3. Atribuir sílaba "a" para notas sem letra (melisma)
        for idx, note in enumerate(merged):
            if not note.get("lyric", "").strip():
                merged[idx] = dict(note)
                merged[idx]["lyric"] = "a"

        midi_notes = [n["midi_note"] for n in merged]
        logger.info(
            "notas_preprocessadas",
            original=len(notes),
            filtradas=len(merged),
            midi_range=f"{min(midi_notes)}-{max(midi_notes)}",
        )
        return merged

    def _load_phoneme_map(self, vb_root: Path) -> dict[str, int]:
        """Carrega mapeamento fonema→token_id do voicebank."""
        for path in [
            vb_root / "dsmain" / "phonemes.json",
            vb_root / "dsdur" / "files" / "phonemes.json",
        ]:
            if path.exists():
                with open(path) as f:
                    return json.load(f)
        raise FileNotFoundError(f"phonemes.json não encontrado em {vb_root}")

    def _load_speaker_embed(self, vb_root: Path, speaker: str = "") -> np.ndarray:
        """Carrega speaker embedding do voicebank."""
        # Buscar em vários diretórios possíveis
        search_dirs = [
            vb_root / "dsdur" / "embeds",
            vb_root / "dspitch" / "embeds",
            vb_root / "embeds",
        ]

        emb_files: list[Path] = []
        for d in search_dirs:
            if d.exists():
                emb_files = sorted(d.glob("*.emb"))
                if emb_files:
                    break

        if not emb_files:
            return np.zeros(384, dtype=np.float32)

        target_file = emb_files[0]
        if speaker:
            for ef in emb_files:
                if speaker.lower() in ef.stem.lower():
                    target_file = ef
                    break

        data = np.fromfile(str(target_file), dtype=np.float32)
        logger.info("speaker_embed_carregado", file=target_file.name, shape=data.shape)
        return data

    # ─── Preparação de dados de sequência ───

    def _prepare_sequence_data(
        self,
        notes: list[dict],
        phoneme_map: dict[str, int],
        sr: int,
        hop_size: int,
        language: str,
    ) -> dict[str, np.ndarray]:
        """Prepara dados de sequência para os modelos DiffSinger.

        Retorna dict com arrays para os níveis token, word e note:
            tokens: (n_tokens,) int64 — IDs de fonemas
            languages: (n_tokens,) int64 — IDs de idioma
            ph_midi: (n_tokens,) int64 — nota MIDI por fonema
            word_div: (n_words,) int64 — qtd fonemas por palavra/nota
            word_dur: (n_words,) int64 — duração estimada em frames
            note_midi: (n_notes,) float32 — MIDI por nota (mesmo len que word_div)
            note_rest: (n_notes,) bool — flag de pausa
        """
        lang_id = _get_lang_id_for_config(language)
        sp_id = phoneme_map.get("SP", 2)
        ap_id = phoneme_map.get("AP", 1)

        fps = sr / hop_size

        tokens_list: list[int] = []
        langs_list: list[int] = []
        ph_midi_list: list[int] = []
        word_div_list: list[int] = []
        word_dur_list: list[int] = []
        note_midi_list: list[float] = []
        note_rest_list: list[bool] = []

        # SP inicial antes da primeira nota
        first_start = notes[0]["start_time"] if notes else 0.0
        initial_frames = max(int(first_start * fps), 1)
        tokens_list.append(sp_id)
        langs_list.append(lang_id)
        ph_midi_list.append(0)
        word_div_list.append(1)
        word_dur_list.append(initial_frames)
        note_midi_list.append(0.0)
        note_rest_list.append(True)

        prev_end = first_start

        for note in notes:
            start_time = note["start_time"]
            end_time = note["end_time"]
            midi = note["midi_note"]

            # Gap entre notas → SP ou AP
            gap = start_time - prev_end
            if gap > 0.02:  # > 20ms gap → silence
                gap_frames = max(int(gap * fps), 1)
                tokens_list.append(sp_id)
                langs_list.append(lang_id)
                ph_midi_list.append(0)
                word_div_list.append(1)
                word_dur_list.append(gap_frames)
                note_midi_list.append(0.0)
                note_rest_list.append(True)
            elif gap > 0.005:  # 5-20ms → breath
                gap_frames = max(int(gap * fps), 1)
                tokens_list.append(ap_id)
                langs_list.append(lang_id)
                ph_midi_list.append(0)
                word_div_list.append(1)
                word_dur_list.append(gap_frames)
                note_midi_list.append(0.0)
                note_rest_list.append(True)

            # Fonemas da nota
            lyric = (note.get("lyric", "") or "a").strip()
            if not lyric:
                lyric = "a"
            phonemes = _g2p(lyric, language)
            if not phonemes or phonemes == ["SP"]:
                phonemes = ["pt/a"] if language == "pt" else ["es/a"]

            note_frames = max(int((end_time - start_time) * fps), 1)

            for ph in phonemes:
                token_id = phoneme_map.get(ph, sp_id)
                tokens_list.append(token_id)
                langs_list.append(lang_id)
                ph_midi_list.append(midi)

            word_div_list.append(len(phonemes))
            word_dur_list.append(note_frames)
            note_midi_list.append(float(midi))
            note_rest_list.append(False)

            prev_end = end_time

        # SP final
        tokens_list.append(sp_id)
        langs_list.append(lang_id)
        ph_midi_list.append(0)
        word_div_list.append(1)
        word_dur_list.append(1)
        note_midi_list.append(0.0)
        note_rest_list.append(True)

        return {
            "tokens": np.array(tokens_list, dtype=np.int64),
            "languages": np.array(langs_list, dtype=np.int64),
            "ph_midi": np.array(ph_midi_list, dtype=np.int64),
            "word_div": np.array(word_div_list, dtype=np.int64),
            "word_dur": np.array(word_dur_list, dtype=np.int64),
            "note_midi": np.array(note_midi_list, dtype=np.float32),
            "note_rest": np.array(note_rest_list, dtype=bool),
        }

    def _estimate_durations_fallback(
        self,
        tokens: np.ndarray,
        word_div: np.ndarray,
        word_dur: np.ndarray,
        phoneme_map: dict[str, int],
    ) -> np.ndarray:
        """Estima durações de fonemas a partir de durações de palavras (fallback).

        Usado quando os modelos de duração (dur.onnx) não estão disponíveis.
        """
        id_to_ph = {v: k for k, v in phoneme_map.items()}
        vowel_set = {
            "pt/a", "pt/e", "pt/eh", "pt/i", "pt/o", "pt/oh", "pt/u",
            "pt/ax", "pt/ae", "pt/an", "pt/en", "pt/in", "pt/on", "pt/un",
            "pt/i0", "pt/u0",
            "es/a", "es/e", "es/i", "es/o", "es/u",
            "SP", "AP",
        }

        durations = np.ones(len(tokens), dtype=np.int64)
        ph_idx = 0

        for w in range(len(word_div)):
            n_ph = int(word_div[w])
            w_frames = int(word_dur[w])

            if n_ph == 1:
                durations[ph_idx] = max(w_frames, 1)
            else:
                is_vowel = []
                for p in range(n_ph):
                    ph_name = id_to_ph.get(int(tokens[ph_idx + p]), "")
                    is_vowel.append(ph_name in vowel_set)

                n_vow = sum(is_vowel)
                n_cons = n_ph - n_vow

                cons_frames = max(int(w_frames * 0.08), 2) if n_cons > 0 else 0
                remaining = max(w_frames - cons_frames * n_cons, 1)
                vow_frames = max(remaining // max(n_vow, 1), 1) if n_vow > 0 else 1

                for p in range(n_ph):
                    durations[ph_idx + p] = vow_frames if is_vowel[p] else cons_frames

                # Ajustar resto
                total = int(durations[ph_idx:ph_idx + n_ph].sum())
                diff = w_frames - total
                if diff != 0:
                    durations[ph_idx + n_ph - 1] = max(
                        int(durations[ph_idx + n_ph - 1]) + diff, 1
                    )

            ph_idx += n_ph

        return durations

    def _estimate_f0_fallback(
        self,
        ph_midi: np.ndarray,
        durations: np.ndarray,
        sr: int,
        hop_size: int,
    ) -> np.ndarray:
        """Estima f0 a partir de notas MIDI (fallback sem pitch predictor)."""
        n_frames = int(durations.sum())
        f0 = np.zeros(n_frames, dtype=np.float32)
        fps = sr / hop_size

        frame_idx = 0
        for i in range(len(ph_midi)):
            dur = int(durations[i])
            midi = int(ph_midi[i])
            if midi > 0 and dur > 0:
                freq = 440.0 * (2.0 ** ((midi - 69) / 12.0))
                segment = np.full(dur, freq, dtype=np.float32)

                # Vibrato simples após 40% da nota
                vib_start = int(dur * 0.4)
                if vib_start < dur and dur > int(0.2 * fps):
                    t = np.arange(dur - vib_start, dtype=np.float32) / fps
                    depth = freq * (2 ** (15 / 1200) - 1)
                    ramp = np.minimum(t / 0.4, 1.0)
                    segment[vib_start:] += depth * ramp * np.sin(2 * np.pi * 5.0 * t)

                end_idx = min(frame_idx + dur, n_frames)
                f0[frame_idx:end_idx] = segment[:end_idx - frame_idx]

            frame_idx += dur

        return f0

    # ─── Pipeline principal ───

    def _run_full_pipeline(
        self,
        notes: list[dict],
        output_path: Path,
        config: DiffSingerConfig,
        vb_root: Path,
        preview_seconds: float | None,
    ) -> Path:
        """Pipeline completo: linguistic → dur → pitch → acoustic → vocoder.

        Usa os modelos de duração e pitch do voicebank quando disponíveis,
        produzindo durações e f0 que o modelo acústico espera (treinados juntos).
        """
        import onnxruntime as ort

        sr = config.sample_rate
        hop_size = 512

        # ── 1. Carregar dados do voicebank ──
        phoneme_map = self._load_phoneme_map(vb_root)
        spk_embed_vec = self._load_speaker_embed(vb_root, config.speaker)

        logger.info(
            "voicebank_carregado",
            phonemes=len(phoneme_map),
            spk_dim=spk_embed_vec.shape[0],
        )

        # ── 2. Preparar sequências ──
        seq = self._prepare_sequence_data(
            notes, phoneme_map, sr, hop_size, config.language
        )

        tokens = seq["tokens"]
        languages = seq["languages"]
        ph_midi = seq["ph_midi"]
        word_div = seq["word_div"]
        word_dur = seq["word_dur"]
        note_midi = seq["note_midi"]
        note_rest = seq["note_rest"]

        n_tokens = len(tokens)
        n_words = len(word_div)

        logger.info(
            "sequence_data_preparada",
            n_tokens=n_tokens,
            n_words=n_words,
        )

        # ── 3. Predição de duração ──
        ling_dur_path = vb_root / "dsdur" / "files" / "linguistic.onnx"
        dur_model_path = vb_root / "dsdur" / "files" / "dur.onnx"

        if ling_dur_path.exists() and dur_model_path.exists():
            logger.info("usando_modelos_duracao")

            ling_dur = ort.InferenceSession(
                str(ling_dur_path), providers=["CPUExecutionProvider"]
            )
            dur_model = ort.InferenceSession(
                str(dur_model_path), providers=["CPUExecutionProvider"]
            )

            # Linguistic encoder (dur): tokens + languages + word_div + word_dur
            ling_dur_out = ling_dur.run(None, {
                "tokens": tokens.reshape(1, -1),
                "languages": languages.reshape(1, -1),
                "word_div": word_div.reshape(1, -1),
                "word_dur": word_dur.reshape(1, -1),
            })
            encoder_out, x_masks = ling_dur_out

            # Duration predictor: encoder_out + x_masks + ph_midi + spk_embed
            spk_tok = np.tile(
                spk_embed_vec.reshape(1, 1, -1), (1, n_tokens, 1)
            ).astype(np.float32)

            dur_out = dur_model.run(None, {
                "encoder_out": encoder_out,
                "x_masks": x_masks,
                "ph_midi": ph_midi.reshape(1, -1),
                "spk_embed": spk_tok,
            })

            # Converter para frames inteiros (mínimo 1)
            durations = np.maximum(
                np.round(dur_out[0][0]).astype(np.int64), 1
            )

            logger.info(
                "duracao_predita",
                total_frames=int(durations.sum()),
                dur_range=f"{durations.min()}-{durations.max()}",
            )
        else:
            logger.warning("modelos_duracao_ausentes_usando_estimativa")
            durations = self._estimate_durations_fallback(
                tokens, word_div, word_dur, phoneme_map
            )

        n_frames = int(durations.sum())

        # Computar note_dur a partir das durações preditas por fonema
        note_dur = np.zeros(n_words, dtype=np.int64)
        ph_idx = 0
        for w in range(n_words):
            n_ph = int(word_div[w])
            note_dur[w] = int(durations[ph_idx:ph_idx + n_ph].sum())
            ph_idx += n_ph

        # ── 4. Predição de pitch (f0) ──
        ling_pitch_path = vb_root / "dspitch" / "files" / "linguistic.onnx"
        pitch_model_path = vb_root / "dspitch" / "files" / "pitch.onnx"

        if ling_pitch_path.exists() and pitch_model_path.exists():
            logger.info("usando_modelos_pitch", n_frames=n_frames)

            ling_pitch = ort.InferenceSession(
                str(ling_pitch_path), providers=["CPUExecutionProvider"]
            )
            pitch_model = ort.InferenceSession(
                str(pitch_model_path), providers=["CPUExecutionProvider"]
            )

            # Linguistic encoder (pitch): tokens + languages + ph_dur
            ling_pitch_out = ling_pitch.run(None, {
                "tokens": tokens.reshape(1, -1),
                "languages": languages.reshape(1, -1),
                "ph_dur": durations.reshape(1, -1),
            })
            encoder_out_p, x_masks_p = ling_pitch_out

            # Pitch predictor (diffusion): nota → contorno f0 natural
            spk_frames = np.tile(
                spk_embed_vec.reshape(1, 1, -1), (1, n_frames, 1)
            ).astype(np.float32)

            pitch_out = pitch_model.run(None, {
                "encoder_out": encoder_out_p,
                "ph_dur": durations.reshape(1, -1),
                "note_midi": note_midi.reshape(1, -1),
                "note_rest": note_rest.reshape(1, -1),
                "note_dur": note_dur.reshape(1, -1),
                "pitch": np.zeros((1, n_frames), dtype=np.float32),
                "expr": np.ones((1, n_frames), dtype=np.float32),
                "retake": np.ones((1, n_frames), dtype=bool),
                "spk_embed": spk_frames,
                "steps": np.array(config.diffusion_steps, dtype=np.int64),
            })

            f0_raw = pitch_out[0][0].astype(np.float32)  # (n_frames,)

            # Pitch predictor produz valores em MIDI (semitones contínuos).
            # Converter para Hz e aplicar threshold de voicing (MIDI >= 30).
            # Valores abaixo de MIDI 30 (~46 Hz) são ruído/silêncio.
            VOICING_MIDI_THRESHOLD = 30.0

            logger.info(
                "pitch_raw_stats",
                raw_min=f"{f0_raw.min():.2f}",
                raw_max=f"{f0_raw.max():.2f}",
                raw_mean=f"{np.mean(f0_raw[f0_raw > 1.0]):.2f}" if np.any(f0_raw > 1.0) else "0",
                pct_above_threshold=f"{100*np.sum(f0_raw >= VOICING_MIDI_THRESHOLD)/len(f0_raw):.0f}%",
            )

            # Converter MIDI → Hz, silenciando valores sub-vocais
            f0 = np.where(
                f0_raw >= VOICING_MIDI_THRESHOLD,
                440.0 * (2.0 ** ((f0_raw - 69) / 12.0)),
                0.0,
            ).astype(np.float32)

            voiced_f0 = f0[f0 > 1.0]
            logger.info(
                "pitch_predito",
                f0_range=f"{f0.min():.1f}-{f0.max():.1f}",
                mean_f0=f"{np.mean(voiced_f0):.1f}" if len(voiced_f0) > 0 else "0",
                voiced_pct=f"{100*len(voiced_f0)/len(f0):.0f}%",
            )
        else:
            logger.warning("modelos_pitch_ausentes_usando_estimativa")
            f0 = self._estimate_f0_fallback(ph_midi, durations, sr, hop_size)

        # ── 5. Modelo acústico → mel spectrogram ──
        acoustic_path = vb_root / "dsmain" / "acoustic.onnx"
        if not acoustic_path.exists():
            onnx_files = list(vb_root.rglob("acoustic.onnx"))
            if not onnx_files:
                raise FileNotFoundError(
                    f"acoustic.onnx não encontrado em {vb_root}"
                )
            acoustic_path = onnx_files[0]

        logger.info("acoustic_model_carregando", path=str(acoustic_path))
        acoustic = ort.InferenceSession(
            str(acoustic_path), providers=["CPUExecutionProvider"]
        )

        spk_frames = np.tile(
            spk_embed_vec.reshape(1, 1, -1), (1, n_frames, 1)
        ).astype(np.float32)

        gender = np.full((1, n_frames), config.gender, dtype=np.float32)
        velocity = np.full((1, n_frames), config.energy, dtype=np.float32)

        acoustic_feeds = {
            "tokens": tokens.reshape(1, -1),
            "languages": languages.reshape(1, -1),
            "durations": durations.reshape(1, -1),
            "f0": f0.reshape(1, -1),
            "gender": gender,
            "velocity": velocity,
            "spk_embed": spk_frames,
            "steps": np.array(config.diffusion_steps, dtype=np.int64),
        }

        logger.info(
            "acoustic_inference_iniciando",
            n_tokens=n_tokens,
            n_frames=n_frames,
            steps=config.diffusion_steps,
            shapes={k: v.shape for k, v in acoustic_feeds.items()},
        )

        mel_output = acoustic.run(None, acoustic_feeds)[0]  # (1, n_frames, 128)
        logger.info("acoustic_inference_concluida", mel_shape=mel_output.shape)

        # ── 6. Vocoder → waveform ──
        vocoder_path = vb_root / "dsvocoder" / "tgm_hifigan_v110.onnx"
        if not vocoder_path.exists():
            voc_files = list(vb_root.rglob("*.onnx"))
            voc_files = [
                f for f in voc_files
                if "vocoder" in f.name or "hifigan" in f.name
            ]
            if voc_files:
                vocoder_path = voc_files[0]

        if vocoder_path.exists():
            logger.info("vocoder_carregando", path=str(vocoder_path))
            vocoder = ort.InferenceSession(
                str(vocoder_path), providers=["CPUExecutionProvider"]
            )

            waveform = vocoder.run(None, {
                "mel": mel_output,
                "f0": f0.reshape(1, -1),
            })[0]  # (1, n_samples)
            audio = waveform.squeeze().astype(np.float32)
            logger.info("vocoder_concluido", samples=len(audio))
        else:
            logger.warning("vocoder_nao_encontrado_usando_griffin_lim")
            audio = self._mel_to_audio(mel_output.squeeze(), sr, hop_size)

        # ── 7. Normalizar e salvar ──
        peak = np.max(np.abs(audio))
        if peak > 0:
            audio = (audio / peak * 0.85).astype(np.float32)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output_path), audio, sr)

        logger.info(
            "diffsinger_pipeline_concluido",
            output=str(output_path),
            duration=len(audio) / sr,
        )
        return output_path

    def _mel_to_audio(self, mel: np.ndarray, sr: int, hop_size: int) -> np.ndarray:
        """Converte mel spectrogram para áudio via Griffin-Lim (fallback)."""
        try:
            import librosa
            audio = librosa.feature.inverse.mel_to_audio(
                mel.T if mel.shape[0] < mel.shape[1] else mel,
                sr=sr, hop_length=hop_size, n_fft=2048,
            )
            return audio.astype(np.float32)
        except Exception:
            n_frames = mel.shape[0]
            return np.zeros(n_frames * hop_size, dtype=np.float32)

    def _generate_placeholder(
        self,
        notes: list[dict],
        output_path: Path,
        config: DiffSingerConfig,
        preview_seconds: float | None,
    ) -> Path:
        """Gera áudio placeholder com sintetizador simples baseado nas notas."""
        sr = config.sample_rate

        if not notes:
            audio = np.zeros(sr, dtype=np.float32)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(output_path), audio, sr)
            return output_path

        max_time = max(n["end_time"] for n in notes)
        if preview_seconds:
            max_time = min(max_time, preview_seconds)

        total_samples = int(max_time * sr) + sr
        audio = np.zeros(total_samples, dtype=np.float32)

        for note in notes:
            start = int(note["start_time"] * sr)
            end = int(note["end_time"] * sr)
            if preview_seconds:
                end = min(end, int(preview_seconds * sr))
            if start >= total_samples or end <= start:
                continue

            midi = note["midi_note"]
            freq = 440.0 * (2.0 ** ((midi - 69) / 12.0))
            duration_samples = end - start

            t = np.linspace(0, (end - start) / sr, duration_samples, endpoint=False)

            signal = (
                0.5 * np.sin(2 * np.pi * freq * t)
                + 0.25 * np.sin(2 * np.pi * freq * 2 * t)
                + 0.12 * np.sin(2 * np.pi * freq * 3 * t)
                + 0.06 * np.sin(2 * np.pi * freq * 4 * t)
            )

            attack = min(int(0.02 * sr), duration_samples // 4)
            release = min(int(0.05 * sr), duration_samples // 4)
            envelope = np.ones(duration_samples, dtype=np.float32)
            if attack > 0:
                envelope[:attack] = np.linspace(0, 1, attack)
            if release > 0:
                envelope[-release:] = np.linspace(1, 0, release)

            signal *= envelope * 0.3

            end_idx = min(start + duration_samples, total_samples)
            audio[start:end_idx] += signal[: end_idx - start].astype(np.float32)

        peak = np.max(np.abs(audio))
        if peak > 0:
            audio = audio / peak * 0.8

        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output_path), audio, sr)

        logger.info(
            "placeholder_vocal_gerado",
            output=str(output_path),
            duration=max_time,
            notes=len(notes),
        )
        return output_path
