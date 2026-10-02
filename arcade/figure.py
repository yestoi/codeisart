"""The mirror figure (spec 7.3 step 2): a body drawn on the wall as a stick figure in its player's colour.

Shared by the lobby, the attract director (M8) and Copy Me. to_wall maps the camera frame into a rect of the wall
with one scale on both axes, so the figure is not stretched sideways: the camera frame is FRAME_ASPECT wide per
unit of height, and its normalised x is multiplied by that before the scale.
"""
from __future__ import annotations

import dataclasses
import math
from typing import Callable

from arcade.canvas import Canvas, Color
from arcade.input import EPSILON, GLIDE_PERIOD
from arcade.sensed import MIN_CONF, NOSE, SKELETON, Body, Keypoint

FRAME_ASPECT = 4 / 3     # the camera frame's width over its height: both camera streams are 4:3
STROKE = 2               # px (spec 7.3 step 2)
HEAD = 0.06              # the head disc's radius as a share of the rect's height
MIN_BOX = 1e-3           # a box shorter than this (a degenerate detection) is measured as this tall

Rect = tuple[int, int, int, int]


def _round(v: float) -> int:
    """Rounded half up, as the canvas rounds."""
    return math.floor(v + 0.5)


def to_wall(body: Body, rect: Rect, aspect: float = FRAME_ASPECT) -> Callable[[float, float], tuple[int, int]]:
    """A function from frame-normalised (x, y) to a wall pixel in rect (x, y, w, h): the body's box height fills
    the rect's h, one scale on both axes (x times aspect), and the box centre lands on the rect centre."""
    rx, ry, rw, rh = rect
    x0, y0, x1, y1 = body.box
    scale = max(rh - 1, 0) / max(y1 - y0, MIN_BOX)
    bx, by = (x0 + x1) / 2, (y0 + y1) / 2
    cx, cy = rx + (rw - 1) / 2, ry + (rh - 1) / 2

    def f(x: float, y: float) -> tuple[int, int]:
        return _round(cx + (x - bx) * aspect * scale), _round(cy + (y - by) * scale)
    return f


def figure_rect(body: Body, size: tuple[int, int]) -> Rect:
    """The rect a body's figure fills: a square of the wall's height centred on column round(zone_x * (width - 1)).
    It may reach past the wall's sides; drawing clips."""
    width, height = size
    column = _round(body.zone_x * (width - 1))
    return (column - height // 2, 0, height, height)


def _thick_line(canvas: Canvas, a: tuple[int, int], b: tuple[int, int], color: Color, stroke: int) -> None:
    """A line stroke px thick across its run: copies offset along the minor axis, so every column of a mostly
    horizontal line (every row of a mostly vertical one) has exactly stroke pixels."""
    (ax, ay), (bx, by) = a, b
    steep = abs(by - ay) > abs(bx - ax)
    first = -((stroke - 1) // 2)
    for k in range(first, first + stroke):
        dx, dy = (k, 0) if steep else (0, k)
        canvas.line(ax + dx, ay + dy, bx + dx, by + dy, color)


class KeypointHold:
    """One figure's keypoints held through single dropouts (C37). One per figure: the lobby's mirror, Copy Me
    and M8 each keep their own.

    update(body, t) gives body with every keypoint under MIN_CONF in its last confident place and conf, while
    that was seen within grace seconds; a keypoint gone longer stays low, so its limb is not drawn. A new body
    id or None clears what is held. Call it every tick with the body drawn, None when there is none.
    """

    def __init__(self, grace: float):
        if not 0.0 <= grace < math.inf:
            raise ValueError(f"grace must be finite seconds, 0 or more, got {grace!r}")
        self.grace = float(grace)
        self._id: int | None = None
        self._seen: dict[int, tuple[Keypoint, float]] = {}      # keypoint index: (last confident, when)

    def update(self, body: Body | None, t: float) -> Body | None:
        if body is None or body.id != self._id:
            self._id, self._seen = (None if body is None else body.id), {}
        if body is None:
            return None
        kps = list(body.keypoints)
        for i, k in enumerate(kps):
            if k.conf >= MIN_CONF:
                self._seen[i] = (k, t)
            elif i in self._seen and t - self._seen[i][1] <= self.grace + EPSILON:
                kps[i] = self._seen[i][0]
        held = tuple(kps)
        return body if held == body.keypoints else dataclasses.replace(body, keypoints=held)


def _lerp(a: float, b: float, s: float) -> float:
    return a + (b - a) * s


class FigureGlide:
    """One figure's body given on every tick, moved linearly from where it was last drawn to the newest capture
    over one measured capture period, as input.Glide moves a control. A figure drawn straight from the captures
    steps at the pose rate (15 a second on the Pi, 2026-10-02: "choppy"); this one moves on every tick, one
    capture period late at most.

    update(body, t, camera_t): a capture newer than the last (camera_t later) starts a move from the last output
    to body; every tick gives the move's share at t, arriving as the next capture is due (the period is the
    measured gap between captures, clamped to input.GLIDE_PERIOD). x, y, the box and zone_x move; conf and
    every other field are the newest body's. A keypoint under MIN_CONF in the newest body is given as it is.
    A new id or None resets: the next body is output as it is, and so is a body that changes while camera_t
    stands still (a record without capture times has no period to move over). One per figure, as KeypointHold."""

    def __init__(self):
        self._id: int | None = None
        self._from: Body | None = None        # the output when the newest capture arrived
        self._to: Body | None = None          # the newest capture
        self._start = self._capture = 0.0
        self._period = GLIDE_PERIOD[1]
        self._out: Body | None = None

    def update(self, body: Body | None, t: float, camera_t: float) -> Body | None:
        if body is None or body.id != self._id:
            self._id = None if body is None else body.id
            self._from = self._to = self._out = body
            self._start = self._capture = camera_t
            self._period = GLIDE_PERIOD[1]
            return body
        if camera_t > self._capture:
            lo, hi = GLIDE_PERIOD
            self._period = min(hi, max(lo, camera_t - self._capture))
            self._from, self._to, self._start, self._capture = self._out, body, t, camera_t
        elif body is not self._to and body != self._to:     # changed with no capture time: nothing to move over
            self._from = self._to = self._out = body
            return body
        share = min(1.0, max(0.0, (t - self._start) / self._period))
        self._out = self._to if share >= 1.0 or self._from is self._to else self._blend(share)
        return self._out

    def _blend(self, s: float) -> Body:
        a, b = self._from, self._to
        kps = tuple(k if k.conf < MIN_CONF or p.conf < MIN_CONF else Keypoint(_lerp(p.x, k.x, s), _lerp(p.y, k.y, s), k.conf)
                    for p, k in zip(a.keypoints, b.keypoints))
        box = tuple(_lerp(p, q, s) for p, q in zip(a.box, b.box))
        return dataclasses.replace(b, keypoints=kps, box=box, zone_x=_lerp(a.zone_x, b.zone_x, s))


def draw_figure(canvas: Canvas, body: Body, rect: Rect, color: Color, stroke: int = STROKE) -> None:
    """The body as a stick figure in rect: every SKELETON limb whose two keypoints both have conf >= MIN_CONF,
    stroke px thick, and a head disc when the nose is seen."""
    f = to_wall(body, rect)
    kps = body.keypoints
    pts = [f(k.x, k.y) for k in kps]
    for a, b in SKELETON:
        if kps[a].conf >= MIN_CONF and kps[b].conf >= MIN_CONF:
            _thick_line(canvas, pts[a], pts[b], color, stroke)
    if kps[NOSE].conf >= MIN_CONF:
        canvas.fill_circle(*pts[NOSE], max(1, _round(HEAD * rect[3])), color)
