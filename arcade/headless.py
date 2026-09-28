"""Headless pieces shared by the tests and the agent tools: a recording display and the fixed local time of
headless runs."""
from __future__ import annotations

from datetime import datetime

import numpy as np


OPENING_NIGHT = datetime(2026, 11, 11, 21, 0)    # headless local time: evidence never depends on the time of day


class RecordingDisplay:
    """A display that keeps copies of what it was pushed: every frame (keep_all) or only the last."""

    def __init__(self, keep_all: bool = True):
        self.keep_all = keep_all
        self.frames: list[np.ndarray] = []
        self.last: np.ndarray | None = None
        self.count = 0
        self.brightness = 1.0
        self.closed = False

    def push(self, frame: np.ndarray) -> None:
        copy = frame.copy()
        if self.keep_all:
            self.frames.append(copy)
        self.last = copy
        self.count += 1

    def set_brightness(self, level: float) -> None:
        self.brightness = level

    def close(self) -> None:
        self.closed = True

