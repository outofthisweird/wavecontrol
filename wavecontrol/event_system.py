"""
Event system responsible for decoupling subsystems.

Events are data-only messages and do not directly trigger rendering or audio
logic; consumers should inspect the queue and react by adjusting their own
state.
"""
from __future__ import annotations

import enum
import queue
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Optional


class EventType(str, enum.Enum):
    ON_BEAT = "on_beat"
    ON_LOOP = "on_loop"
    ON_PLAY = "on_play"
    ON_PAUSE = "on_pause"
    ON_REVERSE_TOGGLE = "on_reverse_toggle"
    ON_RATE_CHANGE = "on_rate_change"


@dataclass(frozen=True)
class Event:
    """Simple data container for system events."""

    type: EventType
    payload: Dict[str, Any] = field(default_factory=dict)


class EventBus:
    """Thread-safe event bus built on top of a queue."""

    def __init__(self, maxsize: int = 256) -> None:
        self._queue: "queue.Queue[Event]" = queue.Queue(maxsize=maxsize)
        self._listeners: "list[Callable[[Event], None]]" = []
        self._lock = threading.Lock()

    def emit(self, event: Event) -> None:
        """Publish an event to the queue and notify listeners."""
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            # Drop silently to avoid blocking real-time audio threads.
            return
        with self._lock:
            for listener in self._listeners:
                listener(event)

    def poll(self, max_events: int = 32) -> Iterable[Event]:
        """Yield up to ``max_events`` events currently buffered."""
        drained = 0
        while drained < max_events:
            try:
                event = self._queue.get_nowait()
            except queue.Empty:
                break
            yield event
            drained += 1

    def subscribe(self, callback: Callable[[Event], None]) -> None:
        """Register an immediate listener for each emitted event."""
        with self._lock:
            self._listeners.append(callback)

    def clear(self) -> None:
        """Empty queued events and remove listeners."""
        with self._lock:
            self._listeners.clear()
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
