"""A flash meter: arcade.flash's counting a frame at a time, for a run too long to keep its frames (it13 T-wall).

`FlashMeter.add(frame)` gives the frame's flash area, as `arcade.flash.flash_area` counts it (the share of the
wall past budget transitions in the last fps frames), and its square flashes, as `square_flashes` counts them
(the most transitions any window x window square's mean light made in the last fps frames). The maxima of a
run are `flash_area` and `square_flashes` of its frames. `take()` gives the maxima since the last take, for a
report every so often. It reads arcade.flash's pieces and changes nothing there; it holds nothing back, the
governor does.
"""
from __future__ import annotations

import numpy as np

from arcade.flash import BUDGET, THRESHOLD, WINDOW, _Transitions, _Window, signals, square_means


class FlashMeter:
    def __init__(self, fps: int, gamma: float = 2.2, threshold: float = THRESHOLD, budget: int = BUDGET,
                 window: int = WINDOW):
        if isinstance(fps, bool) or not isinstance(fps, int) or fps < 2:
            raise ValueError(f"fps must be an int of at least 2, got {fps!r}")
        self.fps, self.gamma, self.threshold, self.budget, self.window = fps, gamma, threshold, budget, window
        self.frames = 0                                     # over every frame added
        self.area_max = 0.0
        self.squares_max = 0
        self._since = (0.0, 0)                              # the maxima since the last take
        self._pixels = self._squares = None                 # (_Transitions, _Window) each, from the first frame

    def add(self, frame: np.ndarray) -> tuple[float, int]:
        """This frame's flash area and square flashes; the first frame's are 0.0 and 0."""
        s = signals(np.asarray(frame), self.gamma)
        means = square_means(s, self.window)
        self.frames += 1
        if self._pixels is None:
            self._pixels = _Transitions(s, self.threshold), _Window(self.fps, s.shape[1:])
            self._squares = _Transitions(means, self.threshold), _Window(self.fps, means.shape[1:])
            return 0.0, 0
        area = float((self._count(self._pixels, s) > self.budget).mean())
        squares = int(self._count(self._squares, means).max())
        self.area_max, self.squares_max = max(self.area_max, area), max(self.squares_max, squares)
        self._since = max(self._since[0], area), max(self._since[1], squares)
        return area, squares

    def take(self) -> tuple[float, int]:
        """The largest flash area and square flashes that add gave since the last take; then both start again."""
        since, self._since = self._since, (0.0, 0)
        return since

    @staticmethod
    def _count(counted: tuple[_Transitions, _Window], v: np.ndarray) -> np.ndarray:
        """Per position: its transitions in the fps frames ending with this one (flash_area's last_second)."""
        track, window = counted
        flip, up = track.flips(v)
        shown = flip.any(axis=0)
        last_second = window.count - window.ring[window.i] + shown
        track.advance(v, flip, up)
        window.push(shown)
        return last_second
