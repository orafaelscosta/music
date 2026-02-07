"""Serviço de análise de áudio — BPM, tonalidade, waveform."""

import asyncio
from pathlib import Path

import librosa
import numpy as np
import structlog

from api.schemas import AudioAnalysis

logger = structlog.get_logger()

# Mapeamento de pitch classes para nomes de notas
PITCH_CLASS_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


class AudioAnalyzer:
    """Analisa áudio instrumental para extrair metadados musicais."""

    async def analyze(self, file_path: Path) -> AudioAnalysis:
        """Executa análise completa do áudio em thread separada."""
        return await asyncio.to_thread(self._analyze_sync, file_path)

    def _analyze_sync(self, file_path: Path) -> AudioAnalysis:
        """Análise síncrona do áudio (roda em thread)."""
        logger.info("analise_iniciada", file=str(file_path))

        # Carregar áudio
        y, sr = librosa.load(str(file_path), sr=None)
        duration = librosa.get_duration(y=y, sr=sr)

        # Detectar BPM
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(np.round(tempo, 1)) if np.isscalar(tempo) else float(np.round(tempo[0], 1))

        # Detectar tonalidade usando chroma features
        musical_key = self._detect_key(y, sr)

        # Gerar waveform peaks para visualização
        waveform_peaks = self._generate_peaks(y, num_peaks=500)

        # Formato do arquivo
        audio_format = file_path.suffix.lstrip(".")

        logger.info(
            "analise_concluida",
            duration=round(duration, 2),
            bpm=bpm,
            key=musical_key,
            sr=sr,
        )

        return AudioAnalysis(
            duration_seconds=round(duration, 2),
            sample_rate=sr,
            bpm=bpm,
            musical_key=musical_key,
            audio_format=audio_format,
            waveform_peaks=waveform_peaks,
        )

    def _detect_key(self, y: np.ndarray, sr: int) -> str:
        """Detecta a tonalidade musical usando perfil de Krumhansl-Schmuckler."""
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_mean = np.mean(chroma, axis=1)

        # Perfis de Krumhansl-Schmuckler para major e minor
        major_profile = np.array(
            [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
        )
        minor_profile = np.array(
            [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
        )

        best_corr = -1
        best_key = "C"

        for i in range(12):
            rotated_chroma = np.roll(chroma_mean, -i)

            corr_major = np.corrcoef(rotated_chroma, major_profile)[0, 1]
            if corr_major > best_corr:
                best_corr = corr_major
                best_key = f"{PITCH_CLASS_NAMES[i]} major"

            corr_minor = np.corrcoef(rotated_chroma, minor_profile)[0, 1]
            if corr_minor > best_corr:
                best_corr = corr_minor
                best_key = f"{PITCH_CLASS_NAMES[i]} minor"

        return best_key

    def _generate_peaks(self, y: np.ndarray, num_peaks: int = 500) -> list[float]:
        """Gera lista de picos para renderização de waveform."""
        chunk_size = max(1, len(y) // num_peaks)
        peaks = []
        for i in range(0, len(y), chunk_size):
            chunk = y[i : i + chunk_size]
            peak = float(np.max(np.abs(chunk)))
            peaks.append(round(peak, 4))
        return peaks[:num_peaks]

    async def generate_waveform_peaks(
        self, file_path: Path, num_peaks: int = 500
    ) -> list[float]:
        """Gera peaks de waveform para um arquivo de áudio."""
        return await asyncio.to_thread(self._generate_peaks_from_file, file_path, num_peaks)

    def _generate_peaks_from_file(self, file_path: Path, num_peaks: int) -> list[float]:
        """Carrega áudio e gera peaks (síncrono)."""
        y, _ = librosa.load(str(file_path), sr=22050)
        return self._generate_peaks(y, num_peaks)
