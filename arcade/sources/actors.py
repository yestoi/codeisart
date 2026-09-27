"""Scripted synthetic input for tests and tools (spec 6.4). Deterministic: no randomness, no wall clock."""
from __future__ import annotations

import math
from typing import Callable, Iterable, Iterator

import numpy as np

from arcade.calibration import Calibration
from arcade.poses import POSES
from arcade.sensed import (LEFT_ELBOW, LEFT_HIP, LEFT_SHOULDER, LEFT_WRIST, MOTION_GRID, REACH_TOP_TORSOS,
                           RIGHT_ELBOW, RIGHT_HIP, RIGHT_SHOULDER, RIGHT_WRIST, Audio, Blob, Body, Keypoint,
                           Sensed, place, place_blob)

TICK = 1 / 30
MAX_BLOBS = 8
_ARMS = {"left": (LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST), "right": (RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST)}

Offsets = tuple[tuple[float, float], ...]


def _points(cx: float, cy: float, h: float, offsets: Offsets, conf: float = 1.0) -> list[Keypoint]:
    return [Keypoint(cx + dx * h, cy + dy * h, conf) for dx, dy in offsets]


def make_keypoints(cx: float, cy: float, h: float, left_up: bool = False, right_up: bool = False,
                   conf: float = 1.0) -> tuple[Keypoint, ...]:
    """A standing figure with its hip centre at (cx, cy) and total height h, coordinates normalized."""
    offsets = list(POSES["stand"])
    for hand, up in (("left", left_up), ("right", right_up)):
        if up:
            for i in _ARMS[hand][1:]:
                offsets[i] = POSES["arms_up"][i]
    return tuple(_points(cx, cy, h, tuple(offsets), conf))


def body_box(keypoints: Iterable[Keypoint]) -> tuple[float, float, float, float]:
    xs = [k.x for k in keypoints]
    ys = [k.y for k in keypoints]
    clamp = lambda v: min(1.0, max(0.0, v))
    return (clamp(min(xs) - 0.02), clamp(min(ys) - 0.02), clamp(max(xs) + 0.02), clamp(max(ys) + 0.02))


def _check_hand(hand: str) -> None:
    if hand not in _ARMS:
        raise ValueError(f"hand must be 'left' or 'right', got {hand!r}")


class Person:
    """A scripted body. Every method returns self so scripts chain. y is the hip height."""

    def __init__(self, x: float = 0.5, y: float = 0.55, height: float = 0.6, id: int | None = None):
        self.x0, self.y0, self.h, self.id = x, y, height, id
        self._moves: list[tuple[float, float, float, float]] = []
        self._hands: list[tuple[float, float, str]] = []
        self._wrists: list[tuple[float, float, str, float, float]] = []
        self._poses: list[tuple[float, float, str]] = []
        self._jumps: list[tuple[float, float, float]] = []
        self._arrive = 0.0
        self._leave: float | None = None

    def _x_at(self, t: float) -> float:
        x = self.x0
        for t0, t1, xa, xb in self._moves:
            if t >= t1:
                x = xb
            elif t0 <= t < t1:
                x = xa + (xb - xa) * (t - t0) / (t1 - t0)
        return x

    def _lift_at(self, t: float) -> float:
        lift = 0.0
        for at, seconds, height in self._jumps:
            if at <= t < at + seconds:
                u = (t - at) / seconds
                lift = max(lift, height * 4 * u * (1 - u))
        return lift

    def walk(self, x_to: float, seconds: float, at: float | None = None) -> "Person":
        t0 = (self._moves[-1][1] if self._moves else 0.0) if at is None else at
        self._moves.append((t0, t0 + seconds, self._x_at(t0), x_to))
        return self

    def raise_hand(self, at: float, seconds: float = 0.5, hand: str = "right") -> "Person":
        _check_hand(hand)
        self._hands.append((at, at + seconds, hand))
        return self

    def both_hands_up(self, at: float, seconds: float) -> "Person":
        self._hands.append((at, at + seconds, "both"))
        return self

    def wrist(self, hand: str, y_from: float, y_to: float, seconds: float, at: float | None = None) -> "Person":
        """Move one wrist from y_from to y_to in reach-box v units (0 top, 1 hip height) over seconds.

        The wrist follows the script during [at, at + seconds) and hangs at the side outside it. With at
        None it starts where this hand's last wrist script ended, or at 0.
        """
        _check_hand(hand)
        if at is None:
            ends = [t1 for _, t1, h, _, _ in self._wrists if h == hand]
            at = ends[-1] if ends else 0.0
        self._wrists.append((at, at + seconds, hand, y_from, y_to))
        return self

    def pose(self, name: str, at: float, seconds: float) -> "Person":
        """Hold POSES[name] during [at, at + seconds)."""
        if name not in POSES:
            raise ValueError(f"unknown pose {name!r}; known: {', '.join(sorted(POSES))}")
        self._poses.append((at, at + seconds, name))
        return self

    def jump(self, at: float, height: float = 0.15, seconds: float = 0.6) -> "Person":
        self._jumps.append((at, seconds, height))
        return self

    def leave(self, at: float) -> "Person":
        self._leave = at
        return self

    def arrive(self, at: float) -> "Person":
        self._arrive = at
        return self

    def present(self, t: float) -> bool:
        return t >= self._arrive and (self._leave is None or t < self._leave)

    def _offsets_at(self, t: float) -> list[tuple[float, float]]:
        offsets = list(POSES["stand"])
        for t0, t1, name in self._poses:
            if t0 <= t < t1:
                offsets = list(POSES[name])
        for t0, t1, hand in self._hands:
            if t0 <= t < t1:
                for side in ("left", "right") if hand == "both" else (hand,):
                    for i in _ARMS[side][1:]:
                        offsets[i] = POSES["arms_up"][i]
        return offsets

    def _keypoints_at(self, t: float) -> list[Keypoint]:
        cx, cy = self._x_at(t), self.y0 - self._lift_at(t)
        offsets = self._offsets_at(t)
        pts = _points(cx, cy, self.h, tuple(offsets))
        for t0, t1, hand, y_from, y_to in self._wrists:
            if t0 <= t < t1:
                v = y_from + (y_to - y_from) * (t - t0) / (t1 - t0)
                shoulder, elbow, wrist = _ARMS[hand]
                # The reach box of sensed.Body.reach, from the pose offsets rather than the keypoints, so a
                # body partly out of frame (keypoints clamped with confidence 0) still has one.
                sx, sy = [(a + b) / 2 for a, b in zip(offsets[LEFT_SHOULDER], offsets[RIGHT_SHOULDER])]
                hx, hy = [(a + b) / 2 for a, b in zip(offsets[LEFT_HIP], offsets[RIGHT_HIP])]
                top = cy + (sy - REACH_TOP_TORSOS * math.hypot(sx - hx, sy - hy)) * self.h
                y = top + v * (cy + hy * self.h - top)
                pts[wrist] = Keypoint(pts[wrist].x, y)
                pts[elbow] = Keypoint((pts[shoulder].x + pts[wrist].x) / 2, (pts[shoulder].y + y) / 2)
        return pts

    def _anchor_at(self, t: float) -> tuple[float, float]:
        return self._x_at(t), self.y0 - self._lift_at(t)

    def body_at(self, t: float, id: int) -> Body:
        kps = tuple(self._keypoints_at(t))
        (x1, y1), (x0, y0) = self._anchor_at(t), self._anchor_at(t - TICK)
        return Body(self.id if self.id is not None else id, body_box(kps), kps,
                    vx=(x1 - x0) / TICK, vy=(y1 - y0) / TICK)


BlobScript = Callable[[float], Blob | None]
MotionScript = Callable[[float], np.ndarray | None]
AudioScript = Callable[[float], Audio]


def moving_blob(x0: float, y0: float, x1: float, y1: float, seconds: float,
                color: tuple[int, int, int] = (255, 255, 255), size: float = 0.03,
                start: float = 0.0) -> BlobScript:
    def script(t: float) -> Blob | None:
        if t < start or t > start + seconds:
            return None
        u = (t - start) / seconds if seconds > 0 else 1.0
        return Blob(x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, size, color)
    return script


def motion_rect(x0: float, y0: float, x1: float, y1: float, start: float, seconds: float) -> MotionScript:
    """Motion cells lit over a rectangle during [start, start + seconds), on the 128x64 grid.

    The rectangle is in fractions of the motion grid, which covers the calibrated zone at the wall's
    aspect (spec 5), not in the camera coordinates Person(x) uses: x 0.5 is the middle of the zone.
    """
    w, h = MOTION_GRID
    c0, r0 = int(x0 * w), int(y0 * h)
    c1, r1 = max(c0 + 1, math.ceil(x1 * w)), max(r0 + 1, math.ceil(y1 * h))
    grid = np.zeros((h, w), bool)
    grid[max(r0, 0):min(r1, h), max(c0, 0):min(c1, w)] = True

    def script(t: float) -> np.ndarray | None:
        return grid.copy() if start <= t < start + seconds else None
    return script


def silence() -> AudioScript:
    return lambda t: Audio()


def loud(level: float) -> AudioScript:
    return lambda t: Audio(level=level, level_smooth=level, peak=level)


def level_ramp(points: list[tuple[float, float]]) -> AudioScript:
    """level (and level_smooth and peak) interpolated linearly between (t, level) points, ends held."""
    if not points or any(b[0] < a[0] for a, b in zip(points, points[1:])):
        raise ValueError(f"level_ramp needs (t, level) points in time order, got {points!r}")

    def script(t: float) -> Audio:
        level = points[0][1] if t <= points[0][0] else points[-1][1]
        for (ta, la), (tb, lb) in zip(points, points[1:]):
            if ta <= t < tb:
                level = la + (lb - la) * (t - ta) / (tb - ta)
                break
        return Audio(level=level, level_smooth=level, peak=level)
    return script


def _fires(t: float, when: float) -> bool:
    """Exactly one tick per event: the first tick at or after it."""
    return when - 1e-9 <= t < when + TICK - 1e-9


def claps(times: list[float]) -> AudioScript:
    def script(t: float) -> Audio:
        hit = any(_fires(t, c) for c in times)
        return Audio(level=0.8 if hit else 0.05, level_smooth=0.8 if hit else 0.05,
                     peak=1.0 if hit else 0.05, clap=hit, onset=hit)
    return script


def tempo(bpm: float, start: float = 0.0) -> AudioScript:
    period = 60.0 / bpm

    def script(t: float) -> Audio:
        n = math.floor((t - start) / period + 1e-9)
        hit = t >= start - 1e-9 and _fires(t, start + n * period)
        return Audio(level=0.6 if hit else 0.3, level_smooth=0.6 if hit else 0.3, peak=0.9 if hit else 0.3,
                     onset=hit, beat=hit, bpm=bpm)
    return script


def scene(persons: Iterable[Person] = (), blobs: Iterable[BlobScript] = (), motion: Iterable[MotionScript] = (),
          audio: AudioScript | None = None, ticks: int = 90,
          calibration: Calibration | None = None) -> Iterator[Sensed]:
    """Sensed records at 30 Hz with a fresh camera frame every tick, as a perfect 30 fps camera gives.

    Bodies are placed against the calibration (the default one when None) and sorted largest scale
    first; blobs are placed, kept in script order (a Blob has no brightness to sort by) and capped at 8;
    motion scripts are ORed on the 128x64 grid.
    """
    persons, blobs, motion = list(persons), list(blobs), list(motion)
    audio = audio or silence()
    cal = calibration or Calibration()
    w, h = MOTION_GRID
    for i in range(ticks):
        t = i * TICK
        bodies = [place(p.body_at(t, idx), cal) for idx, p in enumerate(persons) if p.present(t)]
        bodies.sort(key=lambda b: -b.scale)
        lights = tuple(place_blob(b, cal) for b in (s(t) for s in blobs) if b is not None)[:MAX_BLOBS]
        grid = np.zeros((h, w), bool)
        for script in motion:
            cells = script(t)
            if cells is not None:
                if cells.shape != (h, w):
                    raise ValueError(f"a motion script returned shape {cells.shape}, not {(h, w)}")
                grid |= cells
        yield Sensed(t=t, camera_t=t, camera_fresh=True, camera_seq=i + 1, bodies=tuple(bodies),
                     blobs=lights, motion=grid, audio=audio(t))
