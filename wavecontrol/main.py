"""Application bootstrap for the WaveControl standalone app."""
from __future__ import annotations

import argparse
import queue
import sys
import time
from pathlib import Path

import pygame

from .analysis import AudioAnalyzer
from .audio_engine import AudioEngine
from .bpm import BPMSystem
from .event_system import EventBus, Event, EventType
from .image_sequence import ImageSequence
from .input_handler import InputHandler
from .renderer import Renderer
from .time_state import TimeState, TimeStateManager


def build_app(audio_path: str, image_dir: str | None = None) -> tuple[
    AudioEngine, Renderer, InputHandler, BPMSystem, EventBus, TimeStateManager
]:
    analysis_queue: "queue.Queue" = queue.Queue(maxsize=8)
    event_bus = EventBus()
    time_state = TimeState(sample_rate=44100.0)
    time_manager = TimeStateManager(time_state)
    analyzer = AudioAnalyzer()
    bpm_system = BPMSystem(event_bus, sample_rate=time_state.sample_rate)
    image_sequence = None
    if image_dir:
        image_path = Path(image_dir)
        if image_path.exists():
            image_sequence = ImageSequence(str(image_path), (640, 360))

    audio_engine = AudioEngine(event_bus, time_manager, analysis_queue)
    audio_engine.load_file(audio_path)

    renderer = Renderer(event_bus, time_manager, analysis_queue, analyzer, image_sequence)
    input_handler = InputHandler(audio_engine, bpm_system, time_manager, event_bus)
    return audio_engine, renderer, input_handler, bpm_system, event_bus, time_manager


def run(audio_path: str, image_dir: str | None = None) -> None:
    audio_engine, renderer, input_handler, bpm_system, event_bus, time_manager = build_app(
        audio_path, image_dir
    )

    renderer.start()
    input_handler.start()
    audio_engine.play()

    last_beat_index = -1
    running = True
    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            snapshot = time_manager.snapshot()
            beat_interval = bpm_system._beat_interval
            current_index = int(snapshot.accumulated_time / beat_interval)
            if current_index != last_beat_index and bpm_system.beat_due(snapshot.accumulated_time):
                event_bus.emit(Event(EventType.ON_BEAT))
                last_beat_index = current_index
            for _ in event_bus.poll():
                # Rendering and audio react through event subscription,
                # so polling is only necessary to keep the queue healthy.
                pass
            time.sleep(0.005)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        renderer.stop()
        input_handler.stop()
        audio_engine.stop()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WaveControl standalone app")
    parser.add_argument("audio", help="Path to an audio file (WAV, MP3, FLAC)")
    parser.add_argument(
        "--images", help="Optional directory of images for the image sequence system"
    )
    args = parser.parse_args(argv)

    audio_path = Path(args.audio)
    if not audio_path.exists():
        print(f"Audio file not found: {audio_path}")
        return 1
    run(str(audio_path), args.images)
    return 0


if __name__ == "__main__":
    sys.exit(main())
