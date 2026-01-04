"""Real-time audio analysis utilities."""
from __future__ import annotations

import numpy as np


class AudioAnalyzer:
    """Computes waveform statistics and FFT on audio buffers."""

    def __init__(self, fft_size: int = 1024) -> None:
        self.fft_size = fft_size

    def amplitude(self, buffer: np.ndarray) -> float:
        return float(np.mean(np.abs(buffer)))

    def rms(self, buffer: np.ndarray) -> float:
        return float(np.sqrt(np.mean(np.square(buffer))))

    def peak(self, buffer: np.ndarray) -> float:
        return float(np.max(np.abs(buffer)))

    def fft(self, buffer: np.ndarray) -> np.ndarray:
        windowed = buffer[: self.fft_size, 0] * np.hanning(self.fft_size)
        spectrum = np.fft.rfft(windowed)
        return np.abs(spectrum)
