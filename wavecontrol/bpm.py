"""Automatic and manual BPM detection."""
from __future__ import annotations

import numpy as np

from .event_system import Event, EventBus, EventType


class BPMSystem:
    """Detects BPM from audio samples and exposes a beat clock."""

    def __init__(self, event_bus: EventBus, sample_rate: float) -> None:
        self.event_bus = event_bus
        self.sample_rate = sample_rate
        self.manual_bpm: float | None = None
        self._beat_interval = 60.0 / 120.0  # default 120 BPM

    def manual_override(self, bpm: float) -> float:
        self.manual_bpm = max(1.0, bpm)
        self._beat_interval = 60.0 / self.manual_bpm
        return self.manual_bpm

    def detect(self, samples: np.ndarray) -> float:
        """Very lightweight peak-based BPM estimation."""
        if samples.ndim > 1:
            samples = np.mean(samples, axis=1)
        # Use the first ~30 seconds or entire buffer.
        max_frames = int(self.sample_rate * 30)
        samples = samples[:max_frames]
        envelope = np.abs(samples)
        threshold = envelope.mean() + envelope.std()
        peaks = np.where(envelope > threshold)[0]
        if len(peaks) < 2:
            bpm = 120.0
        else:
            intervals = np.diff(peaks) / self.sample_rate
            seconds_per_beat = np.median(intervals)
            bpm = 60.0 / max(seconds_per_beat, 1e-3)
        self._beat_interval = 60.0 / bpm
        return bpm

    def beat_due(self, accumulated_time: float) -> bool:
        """Check whether a beat event should fire at the provided time."""
        return accumulated_time % self._beat_interval < 1e-3

    def emit_beat(self) -> None:
        self.event_bus.emit(Event(EventType.ON_BEAT))
