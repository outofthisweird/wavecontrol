"""Rendering loop driven by shared analysis and time data."""
from __future__ import annotations

import queue
import random
import threading
from typing import List, Tuple

import numpy as np
import pygame

from .analysis import AudioAnalyzer
from .event_system import Event, EventBus, EventType
from .image_sequence import ImageSequence
from .time_state import TimeStateManager


class Particle:
    def __init__(self, position: Tuple[int, int], velocity: Tuple[float, float], ttl: int) -> None:
        self.x, self.y = position
        self.vx, self.vy = velocity
        self.ttl = ttl

    def update(self) -> None:
        self.x += self.vx
        self.y += self.vy
        self.ttl -= 1


class Renderer(threading.Thread):
    def __init__(
        self,
        event_bus: EventBus,
        time_manager: TimeStateManager,
        analysis_queue: "queue.Queue[np.ndarray]",
        analyzer: AudioAnalyzer,
        image_sequence: ImageSequence | None = None,
        size: tuple[int, int] = (960, 540),
        fps: int = 60,
    ) -> None:
        super().__init__(daemon=True)
        self.event_bus = event_bus
        self.time_manager = time_manager
        self.analysis_queue = analysis_queue
        self.analyzer = analyzer
        self.image_sequence = image_sequence
        self.size = size
        self.fps = fps
        self._running = threading.Event()
        self._running.set()
        self._latest_buffer: np.ndarray | None = None
        self._amplitude = 0.0
        self._rms = 0.0
        self._peak = 0.0
        self._beat_flash = 0
        self._direction = 1
        self.particles: List[Particle] = []
        self.event_bus.subscribe(self._on_event)

    def _on_event(self, event: Event) -> None:
        if event.type == EventType.ON_BEAT:
            self._beat_flash = 10
            self._spawn_particles(32)
            if self.image_sequence:
                self.image_sequence.rewind_on_beat()
        elif event.type == EventType.ON_REVERSE_TOGGLE:
            self._direction = -self._direction

    def _spawn_particles(self, count: int) -> None:
        for _ in range(count):
            x = random.randint(0, self.size[0])
            y = random.randint(0, self.size[1])
            speed = random.uniform(1, 4) * self._direction
            self.particles.append(
                Particle(
                    (x, y),
                    (random.uniform(-1, 1) * speed, random.uniform(-1, 1) * speed),
                    ttl=random.randint(15, 45),
                )
            )

    def stop(self) -> None:
        self._running.clear()

    def run(self) -> None:
        pygame.init()
        screen = pygame.display.set_mode(self.size)
        clock = pygame.time.Clock()
        trail = pygame.Surface(self.size, pygame.SRCALPHA)

        while self._running.is_set():
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.stop()

            try:
                latest = self.analysis_queue.get_nowait()
                self._latest_buffer = latest
                self._amplitude = self.analyzer.amplitude(latest)
                self._rms = self.analyzer.rms(latest)
                self._peak = self.analyzer.peak(latest)
            except queue.Empty:
                pass

            screen.fill((5, 5, 8))
            trail.fill((0, 0, 0, 10))

            self._draw_waveform(trail)
            self._draw_particles(trail)
            self._draw_image(screen)
            screen.blit(trail, (0, 0))

            if self._beat_flash > 0:
                flash_intensity = min(255, self._beat_flash * 16)
                overlay = pygame.Surface(self.size)
                overlay.set_alpha(flash_intensity)
                overlay.fill((255, 255, 255))
                screen.blit(overlay, (0, 0))
                self._beat_flash -= 1

            pygame.display.flip()
            clock.tick(self.fps)

        pygame.quit()

    def _draw_waveform(self, surface: pygame.Surface) -> None:
        if self._latest_buffer is None:
            return
        h = surface.get_height()
        w = surface.get_width()
        samples = self._latest_buffer[:, 0]
        step = max(1, len(samples) // w)
        center = h // 2
        deformation = int(self._peak * h * 0.5)
        points = []
        for x, sample in enumerate(samples[::step]):
            y = center + int(sample * center * 0.8) + random.randint(-2, 2)
            y += int(self._amplitude * deformation)
            points.append((x, y))
        if len(points) > 1:
            pygame.draw.lines(surface, (120, 220, 255), False, points, 2)
            for x, y in points[:: max(1, len(points) // 200)]:
                pygame.draw.circle(surface, (120, 220, 255), (x, y), 2)

    def _draw_particles(self, surface: pygame.Surface) -> None:
        alive = []
        for particle in self.particles:
            particle.update()
            if particle.ttl > 0:
                alive.append(particle)
                pygame.draw.circle(surface, (255, 180, 80), (int(particle.x), int(particle.y)), 3)
        self.particles = alive

    def _draw_image(self, surface: pygame.Surface) -> None:
        if not self.image_sequence:
            return
        frame = self.image_sequence.frame_for_time(self.time_manager.state.accumulated_time)
        if frame is None:
            return
        pygame_frame = pygame.surfarray.make_surface(np.transpose(frame, (1, 0, 2)))
        pygame_frame = pygame.transform.scale(pygame_frame, self.size)
        surface.blit(pygame_frame, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
