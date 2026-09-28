"""The flash governor (spec 7.6 as amended by Q13 and Q15): no area of the wall flashes more than 3 times a second.

Runner-level and last before push (Q11: limiter, then governor, then push), so the bound holds on what the wall
shows; no game or mode can bypass it. After the review prototype FlashLimiter
(docs/superpowers/reviews/2026-09-26-arcade-review-lenses/flashguard2.py), with spec 7.6's saturated-red rule,
the light model of the previews, Q13's small-area exemption, Q15's field cap and a square backstop (plan review B7).
"""
from __future__ import annotations

import logging
import math
from functools import lru_cache

import numpy as np

from arcade.look import is_real, light_lut

log = logging.getLogger("arcade")

FPS = 30                 # the runner's default tick rate: one second of frames
THRESHOLD = 0.1          # a swing of this much light (0..1) from the last extreme is a transition
BUDGET = 6               # transitions per pixel in any second: two per flash, so 3 flashes a second
RED_SHARE = 0.8          # a pixel whose red is this share of its light or more is saturated red
REC709 = np.array([0.2126, 0.7152, 0.0722], np.float32)
WINDOW = 32              # the area rule's square: 16 cm of P5 wall, a 10 degree field seen from 92 cm
SMALL_AREA = 0.1         # a flash on under this share of every WINDOW square is not held (Q13, decision 16)
FIELD_AREA = 0.125       # over-budget flips on this share of the wall, either way, are held however small (Q15)
BACKSTOP_PASSES = 8      # the square backstop's passes before it holds the whole frame (the review saw 4 at most)


def signals(frame: np.ndarray, gamma: float) -> np.ndarray:
    """(3, h, w) float32, each pixel's light measured three ways, a swing in any of which is a transition:
    Rec. 709 luminance; the same doubled for saturated red (red at least RED_SHARE of the light, spec 7.6);
    and red excess, red's light less green's and blue's (0 at least), which moves when red trades against
    another colour of the same luminance."""
    light = light_lut(gamma)[frame]
    y = light @ REC709
    red = light[..., 0]
    doubled = np.where(red >= RED_SHARE * light.sum(axis=2), 2.0 * y, y)      # black: 0 either way
    excess = np.maximum(red - light[..., 1] - light[..., 2], 0.0)
    return np.stack((y, doubled, excess))


class _Transitions:
    """Per value: the lowest and highest since the last transition, and that transition's direction. A rise of
    threshold or more over the lowest (unless already rising) or a fall of threshold or more from the highest
    (unless already falling) is a transition, and both restart there. Before the first, either way counts."""

    def __init__(self, v: np.ndarray, threshold: float):
        self.threshold = threshold
        self.lo, self.hi = v.copy(), v.copy()
        self.direction = np.zeros(v.shape, np.int8)

    def flips(self, v: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        up = (v - self.lo >= self.threshold) & (self.direction <= 0)
        down = (self.hi - v >= self.threshold) & (self.direction >= 0)
        return up | down, up

    def advance(self, v: np.ndarray, flip: np.ndarray, up: np.ndarray) -> None:
        self.direction[flip] = np.where(up[flip], 1, -1)
        self.lo = np.where(flip, v, np.minimum(self.lo, v))
        self.hi = np.where(flip, v, np.maximum(self.hi, v))


@lru_cache(maxsize=16)
def _band(n: int, k: int) -> np.ndarray:
    """(n - k + 1, n) float32: row i is 1 over columns i to i + k - 1, so band @ v sums every run of k."""
    i, j = np.arange(n - k + 1)[:, None], np.arange(n)[None, :]
    band = ((j >= i) & (j < i + k)).astype(np.float32)
    band.flags.writeable = False
    return band


def _square_sums(a: np.ndarray, window: int) -> tuple[np.ndarray, int]:
    """a (..., h, w) summed over every window x window square (cut to the wall), and the square's area."""
    h, w = a.shape[-2:]
    wh, ww = min(window, h), min(window, w)
    return _band(h, wh) @ a @ _band(w, ww).T, wh * ww


def largest_share(mask: np.ndarray, window: int = WINDOW) -> float:
    """The largest share of any window x window square of mask (h, w) that is True, 0..1; on a wall smaller
    than the window the square is cut to the wall."""
    sums, area = _square_sums(mask.astype(np.float32), window)
    return float(sums.max()) / area


def square_means(s: np.ndarray, window: int = WINDOW) -> np.ndarray:
    """(3, h, w) signals to (3, h', w'): their mean over every window x window square (cut to the wall)."""
    sums, area = _square_sums(s, window)
    return sums / area


def _concurrent(flip: np.ndarray, up: np.ndarray, over: np.ndarray, window: int) -> float:
    """The largest share of any square whose over-budget pixels transition the same way in this frame (any of
    the three signals rising, or any falling): the area of a flash, as the guidance counts "flashes occurring
    concurrently". Text scrolling past turns some pixels on and others off, never most of a square one way."""
    ups, downs = (flip & up).any(axis=0) & over, (flip & ~up).any(axis=0) & over
    return max(largest_share(ups, window), largest_share(downs, window))


class _Window:
    """Per position: how many transitions the last n frames hold."""

    def __init__(self, n: int, shape: tuple[int, ...]):
        self.ring = np.zeros((n,) + shape, bool)
        self.count = np.zeros(shape, np.int16)
        self.i = 0

    def push(self, shown: np.ndarray) -> None:
        self.count -= self.ring[self.i]
        self.ring[self.i] = shown
        self.count += shown
        self.i = (self.i + 1) % len(self.ring)


class FlashGovernor:
    """apply(frame) returns the frame with every over-budget transition held at the pixel's previous output,
    unless the flash is a small area, and with every square whose mean light would flash past budget held whole.

    A transition is over budget when the pixel's previous fps frames already hold budget of them (spec 7.6's
    "already transitioned six times in the last second"), so any fps + 1 frames show at most budget. A flash
    is a small area (Q13), and nothing is held, while all three: the over-budget transitions of this frame
    going the same way fill under SMALL_AREA of every WINDOW square; those going either way fill under
    FIELD_AREA of the wall (Q15); and no square's mean light has made budget transitions in the last fps
    frames (one such square anywhere lets over-budget pixels be held anywhere). Then the square backstop: a
    square whose mean light would make a transition while its last fps frames already hold budget is held
    whole, whatever its pixels' own budgets, until no such square flips. After BACKSTOP_PASSES passes it holds
    the whole frame instead, logged once, so apply never hangs. So every square's mean shows at most budget
    transitions in any fps + 1 frames, however its pixels take turns. Fine text scrolling past passes: it
    turns a few pixels of a square on and others off, and the square's mean hardly moves. A strobe, a pattern
    reversal, a reversing grating, many small flashes together, and a flash spread over a few frames or taken
    in turns are all held. Held pixels are measured as shown: what the wall showed is what is counted.

    The first frame passes, and a frame with nothing held is returned as it is (the same array). held_ticks
    counts the frames in which anything was held (the runner's flash_held_ticks). fps is the runner's tick rate
    (cfg.fps). A frame of another shape or dtype raises ValueError.
    """

    def __init__(self, height: int, width: int, gamma: float = 2.2, fps: int = FPS, threshold: float = THRESHOLD,
                 budget: int = BUDGET):
        light_lut(gamma)                                             # checks gamma
        if isinstance(fps, bool) or not isinstance(fps, int) or fps < 2:
            raise ValueError(f"fps must be an int of at least 2, got {fps!r}")
        if isinstance(budget, bool) or not isinstance(budget, int) or budget < 1:
            raise ValueError(f"budget must be an int of at least 1, got {budget!r}")
        if not is_real(threshold) or not 0.0 < threshold < math.inf:
            raise ValueError(f"threshold must be over 0 and finite, got {threshold!r}")
        self.shape, self.gamma, self.budget, self.fps = (height, width, 3), gamma, budget, fps
        self.threshold = threshold
        self.held_ticks = 0
        self._prev: np.ndarray | None = None                        # a copy of the last output
        self._shown: np.ndarray | None = None                       # and its signals
        self._pixels: _Transitions | None = None
        self._squares: _Transitions | None = None
        self._pixel_window = self._square_window = None
        self._gave_up = False                                       # the backstop's fallback is logged once

    def apply(self, frame: np.ndarray) -> np.ndarray:
        if frame.shape != self.shape or frame.dtype != np.uint8:
            raise ValueError(f"frame must be {self.shape} uint8, got {frame.shape} {frame.dtype}")
        s = signals(frame, self.gamma)
        if self._pixels is None:                             # nothing is held before a transition: no _prev yet
            means = square_means(s)
            self._pixels, self._squares = _Transitions(s, self.threshold), _Transitions(means, self.threshold)
            self._pixel_window = _Window(self.fps, s.shape[1:])
            self._square_window = _Window(self.fps, means.shape[1:])
            self._shown = s
            return frame
        flip, up = self._pixels.flips(s)
        over = self._pixel_window.count >= self.budget
        hold = flip.any(axis=0) & over
        square_over = self._square_window.count >= self.budget
        if not (hold.any() and (square_over.any() or hold.mean() >= FIELD_AREA
                                or _concurrent(flip, up, over, WINDOW) >= SMALL_AREA)):
            hold[:] = False                                  # a small flash (Q13): nothing is held
        # Square backstop: a square whose mean would make an over-budget transition is held whole, whatever
        # its pixels' own budgets; repeat until no over-budget square flips (all held flips nothing).
        h, w = hold.shape
        bh, bw = _band(h, min(WINDOW, h)), _band(w, min(WINDOW, w))
        for _ in range(BACKSTOP_PASSES):
            shown = np.where(hold, self._shown, s)           # measure what is shown: a held pixel does not flip
            means = square_means(shown)
            square_flip, square_up = self._squares.flips(means)
            bad = square_flip.any(axis=0) & square_over
            if not bad.any():
                break
            hold |= (bh.T @ bad.astype(np.float32) @ bw) > 0
        else:                                                # never measured: hold the whole frame, which flips nothing
            if not self._gave_up:
                log.warning("flash governor: the square backstop took %d passes; holding the whole frame",
                            BACKSTOP_PASSES)
                self._gave_up = True
            hold[:] = True
            shown, means = self._shown, square_means(self._shown)
            square_flip = square_up = np.zeros(means.shape, bool)
        out = frame
        if hold.any():
            self.held_ticks += 1
            out = np.where(hold[..., None], self._prev, frame)
        s = shown
        flip, up = self._pixels.flips(s)
        self._pixels.advance(s, flip, up)
        self._pixel_window.push(flip.any(axis=0))
        self._squares.advance(means, square_flip, square_up)
        self._square_window.push(square_flip.any(axis=0))
        self._prev, self._shown = out.copy(), s
        return out


def _counted(frames, gamma: float, fps: int, threshold: float, squares: int | None = None):
    """For each frame after the first: its flips and rises (3, h, w) and the window of the fps frames before
    it, counted as the governor counts; of the square means of the given size instead, when given."""
    track, window = None, None
    for frame in frames:
        s = signals(np.asarray(frame), gamma)
        if squares is not None:
            s = square_means(s, squares)
        if track is None:
            track, window = _Transitions(s, threshold), _Window(fps, s.shape[1:])
            continue
        flip, up = track.flips(s)
        yield flip, up, window
        track.advance(s, flip, up)
        window.push(flip.any(axis=0))


def flash_area(frames, gamma: float = 2.2, fps: int = FPS, threshold: float = THRESHOLD,
               budget: int = BUDGET) -> float:
    """The largest share of the wall that flashed more than budget / 2 times in a second (more than budget
    transitions in fps consecutive frames), counted as the governor counts. For tests and tools: spec 7.6's
    "a game's raw output may flash at most 10 percent of the wall", and 0.0 for governed output of any flash
    that is not a small area."""
    worst = 0.0
    for flip, up, window in _counted(frames, gamma, fps, threshold):
        last_second = window.count - window.ring[window.i] + flip.any(axis=0)
        worst = max(worst, float((last_second > budget).mean()))
    return worst


def concurrent_area(frames, gamma: float = 2.2, fps: int = FPS, threshold: float = THRESHOLD,
                    budget: int = BUDGET, window: int = WINDOW) -> float:
    """The largest share of any window x window square whose over-budget transitions went the same way in one
    frame, as the governor measures a flash's area (Q13): governed output is always under SMALL_AREA."""
    worst = 0.0
    for flip, up, counts in _counted(frames, gamma, fps, threshold):
        worst = max(worst, _concurrent(flip, up, counts.count >= budget, window))
    return worst


def square_flashes(frames, gamma: float = 2.2, fps: int = FPS, threshold: float = THRESHOLD,
                   window: int = WINDOW) -> int:
    """The most transitions the mean light of any window x window square made in fps consecutive frames: a
    flash of an area, however its pixels take turns."""
    worst = 0
    for flip, up, counts in _counted(frames, gamma, fps, threshold, squares=window):
        worst = max(worst, int((counts.count - counts.ring[counts.i] + flip.any(axis=0)).max()))
    return worst
