from __future__ import annotations

import numpy as np


class FakeDisplay:
    """Keeps only the last frame and a count (daemon plan amendment for Task 5)."""

    def __init__(self):
        self.last: np.ndarray | None = None
        self.count = 0
        self.brightness = 1.0
        self.closed = False

    def push(self, frame: np.ndarray) -> None:
        self.last = frame.copy()
        self.count += 1

    def set_brightness(self, level: float) -> None:
        self.brightness = level

    def close(self, keep_picture: bool = False) -> None:   # keep_picture: the Colorlight hand-off, nothing here
        self.closed = True
