"""
Time state manager centralizing playback position and derived timing data.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass
class TimeState:
    """Data object shared between systems."""

    sample_rate: float
    playhead_time: float = 0.0
    accumulated_time: float = 0.0
    direction: int = 1
    playback_rate: float = 1.0
    loop_enabled: bool = True
    loop_start: float = 0.0
    loop_end: float = 0.0

    def set_loop_points(self, start: float, end: float) -> None:
        self.loop_start = max(0.0, min(start, end))
        self.loop_end = max(self.loop_start, end)

    def reset(self) -> None:
        self.playhead_time = self.loop_start
        self.accumulated_time = 0.0
        self.direction = 1
        self.playback_rate = 1.0


class TimeStateManager:
    """Thread-safe mutator for the shared TimeState."""

    def __init__(self, time_state: TimeState) -> None:
        self.state = time_state
        self._lock = threading.Lock()

    def toggle_direction(self) -> int:
        with self._lock:
            self.state.direction *= -1
            return self.state.direction

    def set_rate(self, playback_rate: float) -> float:
        with self._lock:
            self.state.playback_rate = max(0.1, playback_rate)
            return self.state.playback_rate

    def toggle_loop(self) -> bool:
        with self._lock:
            self.state.loop_enabled = not self.state.loop_enabled
            return self.state.loop_enabled

    def update_time(self, frames: int) -> None:
        """Advance timing based on frames rendered by audio callback."""
        delta_time = frames / self.state.sample_rate * self.state.playback_rate
        with self._lock:
            self.state.accumulated_time += abs(delta_time)
            if self.state.direction > 0:
                self.state.playhead_time += delta_time
                if (
                    self.state.loop_enabled
                    and self.state.loop_end
                    and self.state.playhead_time >= self.state.loop_end
                ):
                    self.state.playhead_time = self.state.loop_start
            else:
                self.state.playhead_time -= delta_time
                if (
                    self.state.loop_enabled
                    and self.state.loop_end
                    and self.state.playhead_time <= self.state.loop_start
                ):
                    self.state.playhead_time = self.state.loop_end

    def snapshot(self) -> TimeState:
        """Return a shallow copy safe for reading outside the lock."""
        with self._lock:
            return TimeState(**vars(self.state))
