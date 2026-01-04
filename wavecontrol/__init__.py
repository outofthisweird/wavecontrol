"""
WaveControl – a standalone Python application for real-time audio playback,
analysis, and visualization.

This package is organized to keep audio, rendering, input, and timing concerns
separate while communicating via shared state objects and event queues.
"""

__all__ = [
    "audio_engine",
    "analysis",
    "bpm",
    "event_system",
    "image_sequence",
    "input_handler",
    "renderer",
    "time_state",
]
