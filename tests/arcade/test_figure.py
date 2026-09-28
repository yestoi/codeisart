import dataclasses

import numpy as np

from arcade.canvas import Canvas
from arcade.figure import FRAME_ASPECT, STROKE, draw_figure, figure_rect, to_wall
from arcade.juice import PLAYER_COLORS
from arcade.sensed import (LEFT_ANKLE, LEFT_ELBOW, LEFT_KNEE, LEFT_WRIST, RIGHT_ANKLE, RIGHT_ELBOW, RIGHT_KNEE,
                           RIGHT_WRIST, Body, Keypoint)
from arcade.sources.actors import body_box, make_keypoints

AMBER = PLAYER_COLORS[0]


def standing(cx=0.5, cy=0.55, h=0.6, zone_x=0.5) -> Body:
    kps = make_keypoints(cx, cy, h)
    return Body(1, body_box(kps), kps, zone_x=zone_x)


def lit(frame) -> int:
    return int(frame.any(axis=2).sum())


def test_to_wall_is_uniform():
    body = standing()
    x0, y0, x1, y1 = body.box
    rect = (7, 3, 301, 301)
    f = to_wall(body, rect)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    base = f(cx, cy)
    assert base == (7 + 150, 3 + 150)                                  # the box centre on the rect centre
    down, right = f(cx, cy + 0.1), f(cx + 0.1 / FRAME_ASPECT, cy)
    assert down[0] == base[0] and right[1] == base[1]
    assert down[1] - base[1] == right[0] - base[0] > 0                 # one scale on both axes
    assert f(cx, y0)[1] == 3 and f(cx, y1)[1] == 3 + 300               # the box height fills the rect's
    wide = to_wall(body, rect, aspect=2.0)
    assert wide(cx + 0.05, cy)[0] - base[0] == down[1] - base[1]       # x times aspect
    assert all(isinstance(v, int) for v in base)


def test_figure_rect_follows_zone_x_and_fills_the_height():
    for size in ((128, 32), (64, 64)):
        w, h = size
        for zone_x in (0.0, 0.25, 0.5, 0.8, 1.0):
            x, y, rw, rh = figure_rect(standing(zone_x=zone_x), size)
            assert (y, rw, rh) == (0, h, h), (size, zone_x)
            column = zone_x * (w - 1)
            assert abs(x + (rw - 1) / 2 - column) <= 1.0, (size, zone_x, x)
    left, right = figure_rect(standing(zone_x=0.2), (128, 32)), figure_rect(standing(zone_x=0.8), (128, 32))
    assert right[0] - left[0] == round(0.8 * 127) - round(0.2 * 127)


def test_mirror_draws_2px_figure_in_player_colour(font5x7):
    assert STROKE == 2
    for size in ((128, 32), (64, 64)):
        canvas = Canvas(*size, font5x7)
        body = standing()
        rect = figure_rect(body, size)
        draw_figure(canvas, body, rect, AMBER)
        frame = canvas.frame
        on = frame.any(axis=2)
        assert on.sum() > 20, size
        assert {tuple(int(v) for v in px) for px in frame[on]} == {AMBER}, size
        f = to_wall(body, rect)
        top = max(f(body.keypoints[k].x, body.keypoints[k].y)[1] for k in (LEFT_KNEE, RIGHT_KNEE)) + 1
        bottom = min(f(body.keypoints[k].x, body.keypoints[k].y)[1] for k in (LEFT_ANKLE, RIGHT_ANKLE)) - 1
        assert bottom - top >= 3, size
        for row in range(top, bottom + 1):                             # the shins: two runs of exactly 2 px
            cols = np.flatnonzero(on[row])
            runs = np.split(cols, np.flatnonzero(np.diff(cols) > 1) + 1)
            assert [len(r) for r in runs] == [2, 2], (size, row, cols)


def test_low_confidence_limbs_skipped(font5x7):
    size = (128, 32)
    body = standing()
    arms = (LEFT_ELBOW, RIGHT_ELBOW, LEFT_WRIST, RIGHT_WRIST)
    weak = dataclasses.replace(body, keypoints=tuple(Keypoint(k.x, k.y, 0.1) if i in arms else k
                                                     for i, k in enumerate(body.keypoints)))
    full, partial = Canvas(*size, font5x7), Canvas(*size, font5x7)
    rect = figure_rect(body, size)
    draw_figure(full, body, rect, AMBER)
    draw_figure(partial, weak, rect, AMBER)
    assert 0 < lit(partial.frame) < lit(full.frame)
    headless = dataclasses.replace(body, keypoints=(Keypoint(0.0, 0.0, 0.0),) + body.keypoints[1:])
    none = Canvas(*size, font5x7)
    draw_figure(none, headless, rect, AMBER)
    assert 0 < lit(none.frame) < lit(full.frame)                       # no head disc, no neck lines
