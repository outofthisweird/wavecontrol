"""Keyboard and mouse interaction layer."""
from __future__ import annotations

import threading
import time
from typing import Callable, Optional

try:
    import keyboard  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    keyboard = None

from .audio_engine import AudioEngine
from .bpm import BPMSystem
from .event_system import EventBus
from .time_state import TimeStateManager


class InputHandler(threading.Thread):
    """
    Non-blocking keyboard handler.

    Uses the `keyboard` package when available; otherwise becomes a no-op to
    avoid crashing in restricted environments.
    """

    def __init__(
        self,
        audio_engine: AudioEngine,
        bpm_system: BPMSystem,
        time_manager: TimeStateManager,
        event_bus: EventBus,
        rate_step: float = 0.1,
    ) -> None:
        super().__init__(daemon=True)
        self.audio_engine = audio_engine
        self.bpm_system = bpm_system
        self.time_manager = time_manager
        self.event_bus = event_bus
        self.rate_step = rate_step
        self._running = threading.Event()
        self._running.set()
        self._manual_buffer: list[str] = []

    def run(self) -> None:
        if keyboard is None:
            return
        keyboard.on_press(self._handle_key)
        while self._running.is_set():
            time.sleep(0.05)

    def stop(self) -> None:
        self._running.clear()

    def _handle_key(self, event) -> None:  # pragma: no cover - requires keyboard events
        name = event.name
        if name == "space":
            self._toggle_play_pause()
        elif name == "r":
            self.audio_engine.toggle_reverse()
        elif name == "l":
            self.audio_engine.toggle_loop()
        elif name == "up":
            self.audio_engine.set_playback_rate(self.time_manager.state.playback_rate + self.rate_step)
        elif name == "down":
            self.audio_engine.set_playback_rate(self.time_manager.state.playback_rate - self.rate_step)
        elif name == "b":
            if self.audio_engine.audio_data is not None:
                self.bpm_system.detect(self.audio_engine.audio_data[:, 0])
        elif name.isdigit():
            self._manual_buffer.append(name)
        elif name == "enter" and self._manual_buffer:
            bpm_value = float("".join(self._manual_buffer))
            self._manual_buffer.clear()
            self.bpm_system.manual_override(bpm_value)

    def _toggle_play_pause(self) -> None:
        if self.audio_engine._playing:
            self.audio_engine.pause()
        else:
            self.audio_engine.play()
