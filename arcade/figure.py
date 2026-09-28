"""The mirror figure (spec 7.3 step 2): a body drawn on the wall as a stick figure in its player's colour.

Shared by the lobby, the attract director (M8) and Copy Me. to_wall maps the camera frame into a rect of the wall
with one scale on both axes, so the figure is not stretched sideways: the camera frame is FRAME_ASPECT wide per
unit of height, and its normalised x is multiplied by that before the scale.
"""
from __future__ import annotations

import math
from typing import Callable

from arcade.canvas import Canvas, Color
from arcade.sensed import MIN_CONF, NOSE, SKELETON, Body

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
