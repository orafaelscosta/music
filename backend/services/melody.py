"""Serviço de melodia — extração MIDI, manipulação e exportação."""

import asyncio
import json
from pathlib import Path

import librosa
import numpy as np
import structlog

logger = structlog.get_logger()

# Constantes MIDI
MIDI_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def midi_note_to_name(midi_note: int) -> str:
    """Converte número MIDI para nome da nota (ex: 60 -> C4)."""
    octave = (midi_note // 12) - 1
    note = MIDI_NOTE_NAMES[midi_note % 12]
    return f"{note}{octave}"


def note_name_to_midi(name: str) -> int:
    """Converte nome da nota para número MIDI (ex: C4 -> 60)."""
    note = name[:-1]
    octave = int(name[-1])
    return MIDI_NOTE_NAMES.index(note) + (octave + 1) * 12


class MelodyNote:
    """Representa uma nota no piano roll."""

    def __init__(
        self,
        start_time: float,
        end_time: float,
        midi_note: int,
        velocity: int = 100,
        lyric: str = "",
    ):
        self.start_time = start_time
        self.end_time = end_time
        self.midi_note = midi_note
        self.velocity = velocity
        self.lyric = lyric

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    @property
    def note_name(self) -> str:
        return midi_note_to_name(self.midi_note)

    def to_dict(self) -> dict:
        return {
            "start_time": round(self.start_time, 4),
            "end_time": round(self.end_time, 4),
            "duration": round(self.duration, 4),
            "midi_note": self.midi_note,
            "note_name": self.note_name,
            "velocity": self.velocity,
            "lyric": self.lyric,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MelodyNote":
        return cls(
            start_time=data["start_time"],
            end_time=data["end_time"],
            midi_note=data["midi_note"],
            velocity=data.get("velocity", 100),
            lyric=data.get("lyric", ""),
        )


class MelodyData:
    """Contém os dados completos de melodia de um projeto."""

    def __init__(
        self,
        notes: list[MelodyNote] | None = None,
        bpm: float = 120.0,
        time_signature: tuple[int, int] = (4, 4),
    ):
        self.notes = notes or []
        self.bpm = bpm
        self.time_signature = time_signature

    def to_dict(self) -> dict:
        return {
            "notes": [n.to_dict() for n in self.notes],
            "bpm": self.bpm,
            "time_signature": list(self.time_signature),
            "total_notes": len(self.notes),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MelodyData":
        melody = cls(
            bpm=data.get("bpm", 120.0),
            time_signature=tuple(data.get("time_signature", [4, 4])),
        )
        melody.notes = [MelodyNote.from_dict(n) for n in data.get("notes", [])]
        return melody

    def snap_to_grid(self, grid_resolution: float = 0.125) -> None:
        """Quantiza notas para o grid mais próximo (em beats)."""
        beat_duration = 60.0 / self.bpm
        grid_time = grid_resolution * beat_duration
        for note in self.notes:
            note.start_time = round(note.start_time / grid_time) * grid_time
            note.end_time = round(note.end_time / grid_time) * grid_time
            if note.end_time <= note.start_time:
                note.end_time = note.start_time + grid_time


class MelodyService:
    """Serviço para extração, manipulação e exportação de melodias MIDI."""

    async def extract_melody_from_audio(
        self, audio_path: Path, bpm: float = 120.0
    ) -> MelodyData:
        """Extrai melodia de um arquivo de áudio usando análise de pitch."""
        return await asyncio.to_thread(
            self._extract_melody_sync, audio_path, bpm
        )

    def _extract_melody_sync(self, audio_path: Path, bpm: float) -> MelodyData:
        """Extração síncrona de melodia usando librosa pyin."""
        logger.info("melody_extraction_iniciada", file=str(audio_path))

        y, sr = librosa.load(str(audio_path), sr=22050)

        # Usar pyin para detecção de pitch (mais robusto que piptrack)
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y,
            fmin=librosa.note_to_hz("C2"),
            fmax=librosa.note_to_hz("C7"),
            sr=sr,
        )

        # Converter frequências para notas MIDI
        times = librosa.times_like(f0, sr=sr)
        hop_time = times[1] - times[0] if len(times) > 1 else 0.01

        notes: list[MelodyNote] = []
        current_note: int | None = None
        note_start: float = 0.0

        for i, (freq, is_voiced) in enumerate(zip(f0, voiced_flag)):
            time = times[i]

            if is_voiced and not np.isnan(freq) and freq > 0:
                midi_note = int(round(librosa.hz_to_midi(freq)))
                midi_note = max(24, min(96, midi_note))  # Limitar range vocal

                if current_note is None:
                    current_note = midi_note
                    note_start = time
                elif midi_note != current_note:
                    # Nova nota — salvar a anterior
                    notes.append(MelodyNote(
                        start_time=note_start,
                        end_time=time,
                        midi_note=current_note,
                    ))
                    current_note = midi_note
                    note_start = time
            else:
                if current_note is not None:
                    notes.append(MelodyNote(
                        start_time=note_start,
                        end_time=time,
                        midi_note=current_note,
                    ))
                    current_note = None

        # Última nota
        if current_note is not None:
            notes.append(MelodyNote(
                start_time=note_start,
                end_time=times[-1] + hop_time,
                midi_note=current_note,
            ))

        # Filtrar notas muito curtas (< 50ms)
        notes = [n for n in notes if n.duration >= 0.05]

        # Agrupar notas próximas com mesmo pitch
        notes = self._merge_close_notes(notes, gap_threshold=0.05)

        melody = MelodyData(notes=notes, bpm=bpm)

        logger.info(
            "melody_extraction_concluida",
            total_notes=len(notes),
            bpm=bpm,
        )
        return melody

    def _merge_close_notes(
        self, notes: list[MelodyNote], gap_threshold: float = 0.05
    ) -> list[MelodyNote]:
        """Agrupa notas adjacentes com mesmo pitch separadas por gap pequeno."""
        if not notes:
            return notes

        merged: list[MelodyNote] = [notes[0]]
        for note in notes[1:]:
            prev = merged[-1]
            gap = note.start_time - prev.end_time
            if note.midi_note == prev.midi_note and gap < gap_threshold:
                prev.end_time = note.end_time
            else:
                merged.append(note)
        return merged

    async def import_midi(self, midi_path: Path, bpm: float = 120.0) -> MelodyData:
        """Importa melodia de um arquivo MIDI externo."""
        return await asyncio.to_thread(self._import_midi_sync, midi_path, bpm)

    def _import_midi_sync(self, midi_path: Path, bpm: float) -> MelodyData:
        """Importação síncrona de MIDI."""
        logger.info("midi_import_iniciado", file=str(midi_path))

        import mido

        mid = mido.MidiFile(str(midi_path))

        # Extrair BPM do MIDI se disponível
        for track in mid.tracks:
            for msg in track:
                if msg.type == "set_tempo":
                    bpm = round(mido.tempo2bpm(msg.tempo), 1)
                    break

        # Extrair notas
        notes: list[MelodyNote] = []
        active_notes: dict[int, float] = {}
        current_time = 0.0

        # Usar primeira track com notas (ou mesclar todas)
        for track in mid.tracks:
            current_time = 0.0
            for msg in track:
                current_time += mido.tick2second(msg.time, mid.ticks_per_beat, mido.bpm2tempo(bpm))

                if msg.type == "note_on" and msg.velocity > 0:
                    active_notes[msg.note] = current_time
                elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                    if msg.note in active_notes:
                        start = active_notes.pop(msg.note)
                        if current_time - start >= 0.05:
                            notes.append(MelodyNote(
                                start_time=start,
                                end_time=current_time,
                                midi_note=msg.note,
                                velocity=100,
                            ))

        # Ordenar por tempo
        notes.sort(key=lambda n: n.start_time)

        logger.info(
            "midi_import_concluido",
            total_notes=len(notes),
            bpm=bpm,
        )
        return MelodyData(notes=notes, bpm=bpm)

    async def export_midi(
        self, melody: MelodyData, output_path: Path
    ) -> Path:
        """Exporta melodia para arquivo MIDI compatível com OpenUtau/DiffSinger."""
        return await asyncio.to_thread(
            self._export_midi_sync, melody, output_path
        )

    def _export_midi_sync(self, melody: MelodyData, output_path: Path) -> Path:
        """Exportação síncrona para MIDI."""
        import mido

        mid = mido.MidiFile(ticks_per_beat=480)
        track = mido.MidiTrack()
        mid.tracks.append(track)

        # Metadata
        track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(melody.bpm)))
        track.append(mido.MetaMessage(
            "time_signature",
            numerator=melody.time_signature[0],
            denominator=melody.time_signature[1],
        ))
        track.append(mido.MetaMessage("track_name", name="Vocal Melody"))

        # Converter notas
        tempo = mido.bpm2tempo(melody.bpm)
        events: list[tuple[float, str, int, int]] = []

        for note in melody.notes:
            events.append((note.start_time, "note_on", note.midi_note, note.velocity))
            events.append((note.end_time, "note_off", note.midi_note, 0))

            # Adicionar lyric como evento se presente
            if note.lyric:
                events.append((note.start_time, "lyric", 0, 0))

        events.sort(key=lambda e: e[0])

        prev_time = 0.0
        lyric_idx = 0
        lyrics_list = [n.lyric for n in melody.notes if n.lyric]

        for time, event_type, note_val, vel in events:
            delta_seconds = time - prev_time
            delta_ticks = int(mido.second2tick(delta_seconds, mid.ticks_per_beat, tempo))
            delta_ticks = max(0, delta_ticks)

            if event_type == "lyric":
                if lyric_idx < len(lyrics_list):
                    track.append(mido.MetaMessage(
                        "lyrics", text=lyrics_list[lyric_idx], time=delta_ticks
                    ))
                    lyric_idx += 1
            else:
                track.append(mido.Message(
                    event_type, note=note_val, velocity=vel, time=delta_ticks
                ))

            prev_time = time

        output_path.parent.mkdir(parents=True, exist_ok=True)
        mid.save(str(output_path))

        logger.info("midi_export_concluido", path=str(output_path))
        return output_path

    def save_melody_json(self, melody: MelodyData, output_path: Path) -> None:
        """Salva melodia em formato JSON interno."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(melody.to_dict(), f, indent=2)

    def load_melody_json(self, json_path: Path) -> MelodyData:
        """Carrega melodia de formato JSON interno."""
        with open(json_path) as f:
            data = json.load(f)
        return MelodyData.from_dict(data)

    def assign_lyrics_to_notes(
        self, melody: MelodyData, syllables: list[str]
    ) -> MelodyData:
        """Atribui sílabas às notas da melodia sequencialmente."""
        for i, note in enumerate(melody.notes):
            if i < len(syllables):
                note.lyric = syllables[i]
            else:
                note.lyric = ""
        return melody
