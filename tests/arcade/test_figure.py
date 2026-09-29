import dataclasses

import numpy as np
import pytest

from arcade.canvas import Canvas
from arcade.figure import FRAME_ASPECT, STROKE, KeypointHold, draw_figure, figure_rect, to_wall
from arcade.juice import PLAYER_COLORS
from arcade.sensed import (LEFT_ANKLE, LEFT_ELBOW, LEFT_KNEE, LEFT_WRIST, MIN_CONF, RIGHT_ANKLE, RIGHT_ELBOW,
                           RIGHT_KNEE, RIGHT_WRIST, Body, Keypoint)
from arcade.sources.actors import body_box, make_keypoints

AMBER = PLAYER_COLORS[0]


@pytest.fixture(params=[(128, 64), (128, 32), (64, 64)], ids=["128x64", "128x32", "64x64"])
def size(request) -> tuple[int, int]:
    """conftest's sizes plus the wall's own: every sized figure test also runs at 128x64."""
    return request.param


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


def test_figure_rect_follows_zone_x_and_fills_the_height(size):
    w, h = size
    for zone_x in (0.0, 0.25, 0.5, 0.8, 1.0):
        x, y, rw, rh = figure_rect(standing(zone_x=zone_x), size)
        assert (y, rw, rh) == (0, h, h), (size, zone_x)
        column = zone_x * (w - 1)
        assert abs(x + (rw - 1) / 2 - column) <= 1.0, (size, zone_x, x)
    left, right = figure_rect(standing(zone_x=0.2), (128, 32)), figure_rect(standing(zone_x=0.8), (128, 32))
    assert right[0] - left[0] == round(0.8 * 127) - round(0.2 * 127)


def test_mirror_draws_2px_figure_in_player_colour(font5x7, size):
    assert STROKE == 2
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
    for row in range(top, bottom + 1):                                 # the shins: two runs of exactly 2 px
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


GRACE = 0.55                                                           # capture_grace(10)


def dropped(body: Body, joints, dx: float = 0.0) -> Body:
    """body moved dx to the right, with joints dropped out (conf 0 at (0, 0), as degrade drops them)."""
    return dataclasses.replace(body, keypoints=tuple(Keypoint(0.0, 0.0, 0.0) if i in joints
                                                     else Keypoint(k.x + dx, k.y, k.conf)
                                                     for i, k in enumerate(body.keypoints)))


def drawn(font, body: Body, size=(64, 64)):
    canvas = Canvas(*size, font)
    draw_figure(canvas, body, figure_rect(body, size), AMBER)
    return canvas.frame


def test_a_single_keypoint_dropout_is_held(font5x7):
    hold = KeypointHold(GRACE)
    seen = standing()
    assert hold.update(seen, 0.0) == seen                              # a whole body passes as it is
    out = hold.update(dropped(seen, {LEFT_ELBOW}, dx=0.01), 0.1)
    assert out.keypoints[LEFT_ELBOW] == seen.keypoints[LEFT_ELBOW]     # its last confident place and conf
    moved = dropped(seen, set(), dx=0.01)
    assert out.keypoints[:LEFT_ELBOW] + out.keypoints[LEFT_ELBOW + 1:] == \
        moved.keypoints[:LEFT_ELBOW] + moved.keypoints[LEFT_ELBOW + 1:]  # the confident ones are this capture's
    assert out.id == seen.id and out.box == seen.box
    held = hold.update(dropped(seen, {LEFT_ELBOW}), GRACE)             # still held at exactly grace
    assert np.array_equal(drawn(font5x7, held), drawn(font5x7, seen))
    back = dataclasses.replace(seen, keypoints=seen.keypoints[:LEFT_ELBOW] + (Keypoint(0.3, 0.5, 0.9),)
                               + seen.keypoints[LEFT_ELBOW + 1:])
    assert hold.update(back, GRACE + 0.1).keypoints[LEFT_ELBOW] == Keypoint(0.3, 0.5, 0.9)
    assert hold.update(dropped(seen, {LEFT_ELBOW}), GRACE + 0.2).keypoints[LEFT_ELBOW] == Keypoint(0.3, 0.5, 0.9)


def test_a_limb_gone_longer_than_grace_disappears(font5x7):
    hold = KeypointHold(GRACE)
    seen = standing()
    hold.update(seen, 0.0)
    gone = dropped(seen, {LEFT_ELBOW, LEFT_WRIST})
    for t in (0.1, 0.3, 0.5):
        assert hold.update(gone, t).keypoints[LEFT_WRIST] == seen.keypoints[LEFT_WRIST], t
    late = hold.update(gone, GRACE + 0.1)
    assert late.keypoints[LEFT_ELBOW].conf < MIN_CONF and late.keypoints[LEFT_WRIST].conf < MIN_CONF
    assert late == gone                                                # stays low: the arm is not drawn
    assert lit(drawn(font5x7, late)) < lit(drawn(font5x7, seen))
    assert hold.update(gone, 5.0) == gone                              # and does not come back later


def test_hold_clears_on_a_new_body_id():
    seen = standing()
    other = dataclasses.replace(dropped(seen, {LEFT_ELBOW}), id=2)
    hold = KeypointHold(GRACE)
    hold.update(seen, 0.0)
    assert hold.update(other, 0.1) == other                            # another person: nothing of body 1 held
    hold = KeypointHold(GRACE)
    hold.update(seen, 0.0)
    assert hold.update(None, 0.1) is None
    assert hold.update(dropped(seen, {LEFT_ELBOW}), 0.2) == dropped(seen, {LEFT_ELBOW})   # None cleared it
    with pytest.raises(ValueError):
        KeypointHold(-1.0)
