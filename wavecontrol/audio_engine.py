"""
Audio engine implementing callback-based playback with loop and reverse support.
"""
from __future__ import annotations

import threading
from pathlib import Path
import queue
from typing import Optional

import numpy as np
import sounddevice as sd
import soundfile as sf

from .event_system import Event, EventBus, EventType
from .time_state import TimeStateManager


class AudioEngine:
    """Handles audio file loading and real-time playback."""

    def __init__(
        self,
        event_bus: EventBus,
        time_manager: TimeStateManager,
        analysis_queue: "queue.Queue[np.ndarray]",
        block_size: int = 1024,
    ) -> None:
        self.event_bus = event_bus
        self.time_manager = time_manager
        self.analysis_queue = analysis_queue
        self.block_size = block_size

        self.audio_data: Optional[np.ndarray] = None
        self.sample_rate: int = 44100
        self.channels: int = 2
        self._stream: Optional[sd.OutputStream] = None
        self._position: float = 0.0
        self._playing = False
        self._lock = threading.Lock()

    def load_file(self, path: str) -> None:
        """Load a local audio file into memory."""
        filepath = Path(path).expanduser().resolve()
        data, samplerate = sf.read(filepath, dtype="float32", always_2d=True)
        self.audio_data = data
        self.sample_rate = samplerate
        self.channels = data.shape[1]
        with self._lock:
            self._position = 0.0
        self.time_manager.state.sample_rate = float(samplerate)
        self.time_manager.state.loop_start = 0.0
        self.time_manager.state.loop_end = data.shape[0] / samplerate

    def _ensure_stream(self) -> None:
        if self._stream is None:
            self._stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self.block_size,
                dtype="float32",
                callback=self._callback,
            )

    def play(self) -> None:
        if self.audio_data is None:
            raise RuntimeError("No audio loaded")
        self._ensure_stream()
        with self._lock:
            self._playing = True
        if self._stream and not self._stream.active:
            self._stream.start()
        self.event_bus.emit(Event(EventType.ON_PLAY))

    def pause(self) -> None:
        with self._lock:
            self._playing = False
        self.event_bus.emit(Event(EventType.ON_PAUSE))

    def stop(self) -> None:
        with self._lock:
            self._playing = False
            self._position = 0.0
        if self._stream:
            self._stream.stop(ignore_errors=True)

    def toggle_reverse(self) -> int:
        direction = self.time_manager.toggle_direction()
        self.event_bus.emit(Event(EventType.ON_REVERSE_TOGGLE, {"direction": direction}))
        return direction

    def set_playback_rate(self, rate: float) -> float:
        rate = self.time_manager.set_rate(rate)
        self.event_bus.emit(Event(EventType.ON_RATE_CHANGE, {"rate": rate}))
        return rate

    def toggle_loop(self) -> bool:
        return self.time_manager.toggle_loop()

    def _callback(self, outdata: np.ndarray, frames: int, time, status) -> None:  # type: ignore[override]
        if self.audio_data is None:
            outdata.fill(0)
            return

        with self._lock:
            playing = self._playing
            position = self._position

        if not playing:
            outdata.fill(0)
            return

        playback_rate = self.time_manager.state.playback_rate
        direction = self.time_manager.state.direction
        loop_start = self.time_manager.state.loop_start
        loop_end = self.time_manager.state.loop_end or (len(self.audio_data) / self.sample_rate)

        block = np.zeros((frames, self.channels), dtype=np.float32)
        loop_event_triggered = False

        for i in range(frames):
            frame_index = int(round(position))
            if frame_index < 0 or frame_index >= len(self.audio_data):
                if self.time_manager.state.loop_enabled:
                    position = loop_start * self.sample_rate if direction > 0 else loop_end * self.sample_rate
                    loop_event_triggered = True
                    continue
                else:
                    block[i:] = 0
                    with self._lock:
                        self._playing = False
                    break
            block[i] = self.audio_data[frame_index]
            position += playback_rate * direction
            if self.time_manager.state.loop_enabled:
                if direction > 0 and position >= loop_end * self.sample_rate:
                    position = loop_start * self.sample_rate
                    loop_event_triggered = True
                elif direction < 0 and position <= loop_start * self.sample_rate:
                    position = loop_end * self.sample_rate
                    loop_event_triggered = True

        outdata[: len(block)] = block
        with self._lock:
            self._position = position
        self.time_manager.update_time(frames)

        try:
            self.analysis_queue.put_nowait(block.copy())
        except Exception:
            pass

        if loop_event_triggered:
            self.event_bus.emit(Event(EventType.ON_LOOP))

    def close(self) -> None:
        if self._stream is not None:
            self._stream.close()
            self._stream = None
