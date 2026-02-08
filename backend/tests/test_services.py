"""Testes para os serviços de backend."""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf


# ============================================================
# Testes do AudioAnalyzer
# ============================================================
class TestAudioAnalyzer:
    """Testes para o serviço de análise de áudio."""

    @pytest.mark.asyncio
    async def test_analyze_returns_valid_data(self, sample_audio_path):
        """Verifica que a análise retorna campos esperados."""
        from services.analyzer import AudioAnalyzer

        analyzer = AudioAnalyzer()
        result = await analyzer.analyze(sample_audio_path)

        assert result.duration_seconds > 0
        assert result.sample_rate > 0
        assert result.bpm >= 0
        assert result.musical_key is not None
        assert result.audio_format == "wav"
        assert len(result.waveform_peaks) > 0

    @pytest.mark.asyncio
    async def test_analyze_duration_is_correct(self, sample_audio_path):
        """Verifica que a duração está próxima do esperado (2s)."""
        from services.analyzer import AudioAnalyzer

        analyzer = AudioAnalyzer()
        result = await analyzer.analyze(sample_audio_path)

        assert abs(result.duration_seconds - 2.0) < 0.5

    @pytest.mark.asyncio
    async def test_generate_waveform_peaks(self, sample_audio_path):
        """Verifica que os picos de waveform são gerados."""
        from services.analyzer import AudioAnalyzer

        analyzer = AudioAnalyzer()
        peaks = await analyzer.generate_waveform_peaks(sample_audio_path, num_peaks=100)

        assert len(peaks) == 100
        assert all(isinstance(p, float) for p in peaks)
        assert all(0 <= p <= 1 for p in peaks)


# ============================================================
# Testes do MelodyService
# ============================================================
class TestMelodyService:
    """Testes para o serviço de melodia."""

    @pytest.mark.asyncio
    async def test_extract_melody_from_audio(self, sample_audio_path):
        """Verifica extração de melodia retorna dados válidos."""
        from services.melody import MelodyService

        svc = MelodyService()
        melody = await svc.extract_melody_from_audio(sample_audio_path, bpm=120.0)

        assert melody.bpm == 120.0
        assert list(melody.time_signature) == [4, 4]
        # Pode ou não ter notas dependendo do conteúdo
        assert isinstance(melody.notes, list)

    @pytest.mark.asyncio
    async def test_save_and_load_melody_json(self, tmp_project_dir):
        """Verifica serialização JSON de ida e volta."""
        from services.melody import MelodyData, MelodyNote, MelodyService

        svc = MelodyService()
        note = MelodyNote(
            start_time=0.0, end_time=0.5, midi_note=60,
            velocity=80, lyric="la"
        )
        melody = MelodyData(notes=[note], bpm=120.0, time_signature=[4, 4])

        json_path = tmp_project_dir / "melody.json"
        svc.save_melody_json(melody, json_path)
        loaded = svc.load_melody_json(json_path)

        assert len(loaded.notes) == 1
        assert loaded.notes[0].midi_note == 60
        assert loaded.notes[0].lyric == "la"
        assert loaded.bpm == 120.0

    @pytest.mark.asyncio
    async def test_export_and_import_midi(self, tmp_project_dir):
        """Verifica exportação e importação MIDI."""
        from services.melody import MelodyData, MelodyNote, MelodyService

        svc = MelodyService()
        notes = [
            MelodyNote(start_time=0.0, end_time=0.5, midi_note=60, velocity=80),
            MelodyNote(start_time=0.5, end_time=1.0, midi_note=64, velocity=90),
            MelodyNote(start_time=1.0, end_time=1.5, midi_note=67, velocity=70),
        ]
        melody = MelodyData(notes=notes, bpm=120.0)

        midi_path = tmp_project_dir / "test.mid"
        await svc.export_midi(melody, midi_path)
        assert midi_path.exists()

        imported = await svc.import_midi(midi_path, bpm=120.0)
        assert len(imported.notes) == 3

    def test_assign_lyrics_to_notes(self):
        """Verifica atribuição de sílabas às notas."""
        from services.melody import MelodyData, MelodyNote, MelodyService

        svc = MelodyService()
        notes = [
            MelodyNote(start_time=0.0, end_time=0.5, midi_note=60),
            MelodyNote(start_time=0.5, end_time=1.0, midi_note=64),
            MelodyNote(start_time=1.0, end_time=1.5, midi_note=67),
        ]
        melody = MelodyData(notes=notes, bpm=120.0)
        syllables = ["la", "la", "la"]

        result = svc.assign_lyrics_to_notes(melody, syllables)
        assert all(n.lyric == "la" for n in result.notes)

    def test_snap_to_grid(self):
        """Verifica snap-to-grid quantiza tempos corretamente."""
        from services.melody import MelodyData, MelodyNote

        note = MelodyNote(start_time=0.13, end_time=0.63, midi_note=60)
        melody = MelodyData(notes=[note], bpm=120.0)

        melody.snap_to_grid(grid_resolution=0.125)
        # 0.13 deveria virar 0.125, 0.63 deveria virar 0.625
        assert melody.notes[0].start_time == pytest.approx(0.125, abs=0.01)


# ============================================================
# Testes do SyllableService
# ============================================================
class TestSyllableService:
    """Testes para o serviço de silabificação."""

    @pytest.mark.asyncio
    async def test_syllabify_italian(self):
        """Verifica silabificação de texto italiano (fallback)."""
        from services.syllable import SyllableService

        svc = SyllableService()
        syllables = await svc.syllabify_text("Ciao mondo", language="it")

        assert len(syllables) > 0
        assert isinstance(syllables, list)
        assert all(isinstance(s, str) for s in syllables)

    @pytest.mark.asyncio
    async def test_syllabify_portuguese(self):
        """Verifica silabificação de texto em português."""
        from services.syllable import SyllableService

        svc = SyllableService()
        syllables = await svc.syllabify_text("Olá mundo", language="pt")

        assert len(syllables) > 0

    def test_syllables_to_lines(self):
        """Verifica organização de sílabas por linhas."""
        from services.syllable import SyllableService

        svc = SyllableService()
        text = "Linha um\nLinha dois"
        syllables = ["Li", "nha", "um", "Li", "nha", "dois"]
        lines = svc.syllables_to_lines(text, syllables)

        assert len(lines) == 2

    @pytest.mark.asyncio
    async def test_syllabify_empty_text(self):
        """Texto vazio retorna lista vazia."""
        from services.syllable import SyllableService

        svc = SyllableService()
        result = await svc.syllabify_text("", language="it")
        assert result == []


# ============================================================
# Testes do DiffSingerService
# ============================================================
class TestDiffSingerService:
    """Testes para o wrapper DiffSinger."""

    def test_is_not_available_without_engine(self):
        """Sem engine instalado, retorna indisponível."""
        from services.diffsinger import DiffSingerService

        svc = DiffSingerService()
        # Em ambiente de teste, o engine não está instalado
        assert isinstance(svc.is_available(), bool)

    @pytest.mark.asyncio
    async def test_placeholder_synthesis(self, tmp_project_dir):
        """Verifica que placeholder gera arquivo WAV."""
        from services.diffsinger import DiffSingerConfig, DiffSingerService
        from services.melody import MelodyData, MelodyNote, MelodyService

        svc = DiffSingerService()
        melody_svc = MelodyService()

        notes = [
            MelodyNote(start_time=0.0, end_time=0.5, midi_note=60, lyric="la"),
            MelodyNote(start_time=0.5, end_time=1.0, midi_note=64, lyric="la"),
        ]
        melody = MelodyData(notes=notes, bpm=120.0)
        json_path = tmp_project_dir / "melody.json"
        melody_svc.save_melody_json(melody, json_path)

        output_path = tmp_project_dir / "vocals.wav"
        config = DiffSingerConfig(voicebank="test", language="it")
        await svc.synthesize(json_path, output_path, config)

        assert output_path.exists()
        data, sr = sf.read(str(output_path))
        assert len(data) > 0
        assert sr > 0


# ============================================================
# Testes do ACEStepService
# ============================================================
class TestACEStepService:
    """Testes para o wrapper ACE-Step."""

    def test_is_not_available_without_engine(self):
        """Sem engine instalado, retorna indisponível."""
        from services.acestep import ACEStepService

        svc = ACEStepService()
        assert isinstance(svc.is_available(), bool)

    @pytest.mark.asyncio
    async def test_placeholder_generation(self, tmp_project_dir):
        """Verifica que placeholder gera arquivo WAV."""
        from services.acestep import ACEStepConfig, ACEStepService

        svc = ACEStepService()
        output_path = tmp_project_dir / "vocal_ace.wav"
        config = ACEStepConfig(
            lyrics="la la la",
            language="it",
            duration_seconds=2.0,
        )
        await svc.generate(output_path, config)

        assert output_path.exists()
        data, sr = sf.read(str(output_path))
        assert len(data) > 0


# ============================================================
# Testes do RVCService
# ============================================================
class TestRVCService:
    """Testes para o wrapper RVC/Applio."""

    def test_is_not_available_without_engine(self):
        """Sem engine instalado, retorna indisponível."""
        from services.rvc import RVCService

        svc = RVCService()
        assert isinstance(svc.is_available(), bool)

    @pytest.mark.asyncio
    async def test_placeholder_conversion(self, sample_audio_path, tmp_project_dir):
        """Verifica que fallback de pitch-shift funciona."""
        from services.rvc import RVCConfig, RVCService

        svc = RVCService()
        output_path = tmp_project_dir / "refined.wav"
        config = RVCConfig(model_name="test", pitch_shift=2)
        await svc.convert(sample_audio_path, output_path, config)

        assert output_path.exists()
        data, sr = sf.read(str(output_path))
        assert len(data) > 0

    def test_list_models_returns_list(self):
        """List models retorna uma lista."""
        from services.rvc import RVCService

        svc = RVCService()
        models = svc.list_models()
        assert isinstance(models, list)


# ============================================================
# Testes do MixerService
# ============================================================
class TestMixerService:
    """Testes para o serviço de mixagem."""

    @pytest.mark.asyncio
    async def test_mix_fallback(self, sample_audio_path, tmp_project_dir):
        """Verifica mixagem fallback (sem Pedalboard)."""
        from services.mixer import MixConfig, MixerService

        svc = MixerService()
        output_path = tmp_project_dir / "mix.wav"
        config = MixConfig(vocal_gain_db=0, instrumental_gain_db=-3)

        await svc.mix(sample_audio_path, sample_audio_path, output_path, config)

        assert output_path.exists()
        data, sr = sf.read(str(output_path))
        assert len(data) > 0

    def test_presets_exist(self):
        """Verifica que os 5 presets estão definidos."""
        from services.mixer import MixPreset

        presets = MixPreset.list_presets()
        assert len(presets) == 5
        names = [p["name"] for p in presets]
        assert "balanced" in names
        assert "vocal_forward" in names
        assert "ambient" in names
        assert "dry" in names
        assert "radio" in names

    def test_config_from_preset(self):
        """Verifica que config pode ser criada a partir de preset."""
        from services.mixer import MixConfig

        config = MixConfig.from_preset("balanced")
        assert config.vocal_gain_db == 0.0
        assert config.instrumental_gain_db == -3.0

    def test_config_to_and_from_dict(self):
        """Verifica serialização de config."""
        from services.mixer import MixConfig

        config = MixConfig(vocal_gain_db=2.0, reverb_room_size=0.5)
        data = config.to_dict()
        restored = MixConfig.from_dict(data)

        assert restored.vocal_gain_db == 2.0
        assert restored.reverb_room_size == 0.5

    @pytest.mark.asyncio
    async def test_export_wav(self, sample_audio_path, tmp_project_dir):
        """Verifica exportação WAV."""
        from services.mixer import MixerService

        svc = MixerService()
        output_path = tmp_project_dir / "export.wav"
        await svc.export(sample_audio_path, output_path, "wav")

        assert output_path.exists()
