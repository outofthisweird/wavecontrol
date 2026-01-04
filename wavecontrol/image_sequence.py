"""
Image sequence loader with caching and beat-driven rewinds.
"""
from __future__ import annotations

import functools
from pathlib import Path
from typing import List, Tuple

import numpy as np
from PIL import Image


def natural_sort_key(path: Path) -> Tuple:
    """Return a tuple used to naturally sort filenames."""
    parts = []
    for chunk in path.stem.split():
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(chunk)
    return tuple(parts)


class ImageSequence:
    """Caches resized images and exposes frame lookup by accumulated time."""

    def __init__(self, directory: str, target_size: tuple[int, int]) -> None:
        self.directory = Path(directory).expanduser().resolve()
        self.target_size = target_size
        self.images: List[np.ndarray] = []
        self.frames_per_second = 24
        self.rewind_frames_on_beat = 3
        self._current_index = 0
        self._load_images()

    def _load_images(self) -> None:
        supported = {".png", ".jpg", ".jpeg", ".webp"}
        files = sorted(
            [p for p in self.directory.iterdir() if p.suffix.lower() in supported],
            key=natural_sort_key,
        )
        for path in files:
            image = Image.open(path).convert("RGB")
            image = image.resize(self.target_size)
            self.images.append(np.asarray(image))

    def frame_for_time(self, accumulated_time: float) -> np.ndarray | None:
        if not self.images:
            return None
        desired_index = int(accumulated_time * self.frames_per_second) % len(self.images)
        self._current_index = desired_index
        return self.images[self._current_index]

    def rewind_on_beat(self) -> None:
        if not self.images:
            return
        self._current_index = (self._current_index - self.rewind_frames_on_beat) % len(
            self.images
        )

    def current_frame(self) -> np.ndarray | None:
        if not self.images:
            return None
        return self.images[self._current_index]
