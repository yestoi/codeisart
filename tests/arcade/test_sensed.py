import dataclasses
import math

import numpy as np
import pytest

from arcade.calibration import Calibration
from arcade.sensed import (LEFT_ANKLE, LEFT_EAR, LEFT_ELBOW, LEFT_EYE, LEFT_HIP, LEFT_KNEE,
                           LEFT_SHOULDER, LEFT_WRIST, NOSE, RIGHT_ANKLE, RIGHT_EAR, RIGHT_ELBOW,
                           RIGHT_EYE, RIGHT_HIP, RIGHT_KNEE, RIGHT_SHOULDER, RIGHT_WRIST, SKELETON,
                           Audio, Blob, Body, Keypoint, Sensed, place, place_blob)


def kps(**over):
    pts = [Keypoint(0.5, 0.2 + i * 0.04) for i in range(17)]
    for idx, kp in over.items():
        pts[int(idx)] = kp
    return tuple(pts)


# A standing figure: shoulders at y 0.4, 0.2 apart; hips at y 0.7, so the torso is 0.3 and the raise
# line is at 0.4 - 0.3 * 0.3 = 0.31. The nose (0.22) is above it, the wrists hang at hip height.
FIGURE = {
    NOSE: Keypoint(0.5, 0.22), LEFT_EYE: Keypoint(0.48, 0.2), RIGHT_EYE: Keypoint(0.52, 0.2),
    LEFT_EAR: Keypoint(0.46, 0.21), RIGHT_EAR: Keypoint(0.54, 0.21),
    LEFT_SHOULDER: Keypoint(0.4, 0.4), RIGHT_SHOULDER: Keypoint(0.6, 0.4),
    LEFT_ELBOW: Keypoint(0.37, 0.55), RIGHT_ELBOW: Keypoint(0.63, 0.55),
    LEFT_WRIST: Keypoint(0.35, 0.7), RIGHT_WRIST: Keypoint(0.65, 0.7),
    LEFT_HIP: Keypoint(0.45, 0.7), RIGHT_HIP: Keypoint(0.55, 0.7),
    LEFT_KNEE: Keypoint(0.45, 0.85), RIGHT_KNEE: Keypoint(0.55, 0.85),
    LEFT_ANKLE: Keypoint(0.45, 0.95), RIGHT_ANKLE: Keypoint(0.55, 0.95),
}
BOX = (0.3, 0.2, 0.7, 1.0)


def figure(over=None, box=BOX, **fields):
    pts = dict(FIGURE)
    pts.update(over or {})
    return Body(1, box, tuple(pts[i] for i in range(17)), **fields)


def test_body_requires_17_keypoints():
    with pytest.raises(ValueError):
        Body(1, (0, 0, 1, 1), tuple(Keypoint(0, 0) for _ in range(5)))


def test_body_cleans_bad_keypoints():
    pts = kps(**{str(LEFT_WRIST): Keypoint(1.7, -0.2, 0.9), str(RIGHT_WRIST): Keypoint(math.nan, 0.5, 0.9)})
    b = Body(1, (0, 0, 1, 1), pts)
    assert b.left_wrist == Keypoint(1.0, 0.0, 0.0)
    assert b.right_wrist.conf == 0.0 and b.right_wrist.x == 0.0


def test_clean_clamps_confidence_and_rejects_non_finite():
    pts = kps(**{str(NOSE): Keypoint(0.5, 0.2, 5.0), str(LEFT_EYE): Keypoint(0.5, 0.2, -1.0),
                 str(RIGHT_EYE): Keypoint(0.5, 0.2, math.nan), str(LEFT_EAR): Keypoint(math.inf, 0.2, 0.9),
                 str(RIGHT_EAR): Keypoint(0.5, -math.inf, 0.9)})
    b = Body(1, (0, 0, 1, 1), pts)
    assert b.keypoints[NOSE] == Keypoint(0.5, 0.2, 1.0)
    assert b.keypoints[LEFT_EYE] == Keypoint(0.5, 0.2, 0.0)
    assert b.keypoints[RIGHT_EYE] == Keypoint(0.0, 0.0, 0.0)
    assert b.keypoints[LEFT_EAR] == Keypoint(1.0, 0.2, 0.0)
    assert b.keypoints[RIGHT_EAR] == Keypoint(0.5, 0.0, 0.0)


def test_body_defaults_and_measured_scale():
    b = figure()
    assert (b.vx, b.vy, b.in_zone, b.zone_x, b.zone_y, b.seen_ago) == (0.0, 0.0, True, 0.5, 0.5, 0.0)
    assert b.scale == pytest.approx(0.48)            # nose to mid-hip
    assert figure(scale=0.7).scale == 0.7            # a given scale is kept
    assert b.shoulder_mid == Keypoint(0.5, 0.4) and b.hip_mid == Keypoint(0.5, 0.7)
    assert b.shoulder_width == pytest.approx(0.2) and b.torso == pytest.approx(0.3)
    assert b.center == (0.5, 0.6) and b.height == pytest.approx(0.8)
    assert b.nose == b.keypoints[NOSE] and b.confidence == 1.0
    assert Body(1, (0, 0, 1, 1), kps()).scale == pytest.approx(0.46)


def test_raise_line_is_above_shoulders():
    b = figure()
    assert b.raise_line == pytest.approx(0.31)
    assert b.raised_wrist is None and not b.both_hands_up
    low = 0.4 - 0.1 * 0.3                             # 0.1 torso above the shoulders: not raised
    assert figure({RIGHT_WRIST: Keypoint(0.65, low)}).raised_wrist is None
    high = 0.4 - 0.4 * 0.3                            # 0.4 torso above: raised
    up = figure({RIGHT_WRIST: Keypoint(0.65, high)})
    assert up.raised_wrist == Keypoint(0.65, high) and not up.both_hands_up
    assert figure({RIGHT_WRIST: Keypoint(0.65, 0.3)}).raised_wrist is not None   # below the nose, still raised
    both = figure({LEFT_WRIST: Keypoint(0.35, 0.1), RIGHT_WRIST: Keypoint(0.65, high)})
    assert both.both_hands_up and both.raised_wrist == Keypoint(0.35, 0.1)      # the higher one
    faint = figure({RIGHT_WRIST: Keypoint(0.65, 0.1, 0.1)})
    assert faint.raised_wrist is None


def test_nose_fallback_only_without_shoulders():
    hidden = {LEFT_SHOULDER: Keypoint(0.4, 0.4, 0.0), RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0)}
    b = figure(hidden)
    assert b.shoulder_mid is None and b.raise_line == pytest.approx(0.22)
    assert figure({**hidden, RIGHT_WRIST: Keypoint(0.65, 0.25)}).raised_wrist is None
    assert figure({**hidden, RIGHT_WRIST: Keypoint(0.65, 0.18)}).raised_wrist is not None
    one = figure({RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0)})    # one shoulder still sets the line
    assert one.shoulder_mid == Keypoint(0.5, 0.4)                 # its y; x from the hips
    assert one.raise_line == pytest.approx(0.31)
    no_hips = {RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0), LEFT_HIP: Keypoint(0.45, 0.7, 0.0),
               RIGHT_HIP: Keypoint(0.55, 0.7, 0.0)}
    assert figure(no_hips).shoulder_mid == Keypoint(0.5, 0.4)    # x from the nose
    alone = {**no_hips, NOSE: Keypoint(0.5, 0.22, 0.0)}
    assert figure(alone).shoulder_mid == Keypoint(0.4, 0.4)      # nothing else: the shoulder itself
    one_hip = {RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0), RIGHT_HIP: Keypoint(0.55, 0.7, 0.0)}
    assert figure(one_hip).shoulder_mid == Keypoint(0.5, 0.4)    # one hip is off centre too: the nose


def test_one_shoulder_does_not_move_the_centre():
    # Shoulders 0.24 apart for the 0.3 torso: the 1.25 ratio TORSO_PER_SHOULDER_WIDTH assumes, as actors use.
    up = {LEFT_SHOULDER: Keypoint(0.38, 0.4), RIGHT_WRIST: Keypoint(0.7, 0.1)}
    seen = figure({**up, RIGHT_SHOULDER: Keypoint(0.62, 0.4, 0.31)})
    lost = figure({**up, RIGHT_SHOULDER: Keypoint(0.62, 0.4, 0.29)})    # crosses MIN_CONF
    assert abs(seen.anchor.x - lost.anchor.x) < 0.03
    assert abs(seen.cursor[0] - lost.cursor[0]) < 0.03
    assert abs(seen.cursor[1] - lost.cursor[1]) < 0.03
    cal = Calibration()
    assert abs(place(seen, cal).zone_x - place(lost, cal).zone_x) < 0.03


def test_hooded_body_still_raises():
    hood = {NOSE: Keypoint(0.5, 0.22, 0.0), LEFT_EYE: Keypoint(0.48, 0.2, 0.0),
            RIGHT_EYE: Keypoint(0.52, 0.2, 0.0)}
    b = figure({**hood, RIGHT_WRIST: Keypoint(0.65, 0.2)})
    assert b.raise_line == pytest.approx(0.31)
    assert b.raised_wrist == Keypoint(0.65, 0.2)
    assert b.scale == pytest.approx(0.3 * 1.5)        # no nose: 1.5 torso lengths


def test_body_with_nothing_confident_never_raises_or_fails():
    blank = Body(1, BOX, tuple(Keypoint(0.5, 0.5, 0.0) for _ in range(17)))
    assert blank.raise_line is None and blank.raised_wrist is None and not blank.both_hands_up
    assert blank.cursor is None and blank.anchor is None and blank.scale == 0.0
    assert blank.reach(Keypoint(0.5, 0.6)) == pytest.approx((0.5, 0.5))
    placed = place(blank, Calibration())
    assert placed.in_zone and (placed.zone_x, placed.zone_y) == pytest.approx((0.5, 2 / 3))


def test_sensed_defaults():
    s = Sensed(t=1.0)
    assert s.bodies == () and s.blobs == () and s.audio == Audio()
    assert s.motion.shape == (0, 0) and s.motion.dtype == bool
    grid = np.zeros((4, 8), bool)
    held = Sensed(0.0, motion=grid)
    with pytest.raises(ValueError, match="read-only"):
        held.motion[0, 0] = True                     # one grid is shared by the ticks that hold it
    assert not held.with_motion((4, 2)).motion.flags.writeable
    assert grid.flags.writeable                      # the record holds a read-only view, not the caller's array
    assert Sensed(0.0, motion=None).motion.shape == (0, 0)
    assert (s.camera_t, s.camera_fresh, s.camera_seq) == (0.0, False, 0)
    assert s.player is None and s.player2 is None and not s.present
    assert not hasattr(s, "primary")
    a = Audio()
    assert (a.level, a.level_smooth, a.peak, a.voice, a.voice_db, a.floor_db) == (0, 0, 0, 0, -90.0, -90.0)
    assert not (a.clap or a.onset or a.beat) and a.bpm is None


def test_with_motion_resamples_never_rasterizes():
    b = figure()
    s = Sensed(0.0, bodies=(b,)).with_motion((8, 4))
    assert s.motion.shape == (4, 8) and s.motion.dtype == bool and not s.motion.any()
    given = np.ones((4, 8), bool)
    held = Sensed(0.0, motion=given)
    assert held.with_motion((8, 4)) is held and np.shares_memory(held.motion, given)
    small = np.array([[True, False], [False, True]])
    up = Sensed(0.0, motion=small).with_motion((8, 4)).motion
    assert up.shape == (4, 8)
    assert up[:2, :4].all() and up[2:, 4:].all() and not up[:2, 4:].any() and not up[2:, :4].any()
    grid = np.zeros((64, 128), bool)
    grid[33, 101] = True
    down = Sensed(0.0, motion=grid).with_motion((64, 32)).motion
    assert down.shape == (32, 64) and down.sum() == 1 and down[16, 50]    # one lit cell survives shrinking


def test_reach_box_corners():
    b = figure()     # shoulder mid (0.5, 0.4), shoulders 0.2 apart, torso 0.3, hips at 0.7
    top = 0.4 - 1.05 * 0.3
    assert b.reach(Keypoint(0.2, top)) == pytest.approx((0.0, 0.0))
    assert b.reach(Keypoint(0.8, 0.7)) == pytest.approx((1.0, 1.0))
    assert b.reach(Keypoint(0.5, (top + 0.7) / 2)) == pytest.approx((0.5, 0.5))
    assert b.reach(Keypoint(0.0, 1.0)) == (0.0, 1.0)                        # clamped
    half = {i: Keypoint(0.5 + (k.x - 0.5) / 2, 0.5 + (k.y - 0.5) / 2) for i, k in FIGURE.items()}
    small = figure(half, box=(0.4, 0.35, 0.6, 0.75))
    wrist = Keypoint(0.7, 0.3)
    assert small.reach(Keypoint(0.5 + (wrist.x - 0.5) / 2, 0.5 + (wrist.y - 0.5) / 2)) == pytest.approx(b.reach(wrist))
    no_shoulders = figure({LEFT_SHOULDER: Keypoint(0.4, 0.4, 0.0), RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0)})
    assert no_shoulders.reach(Keypoint(0.5, 0.6)) == pytest.approx((0.5, 0.5))   # the body box


def test_cursor_is_wrist_further_from_hip():
    right = figure({RIGHT_WRIST: Keypoint(0.8, 0.3), LEFT_WRIST: Keypoint(0.4, 0.65)})
    assert right.cursor == right.reach(right.right_wrist)
    assert right.cursor == pytest.approx((1.0, (0.3 - 0.085) / 0.615))
    left = figure({LEFT_WRIST: Keypoint(0.25, 0.2), RIGHT_WRIST: Keypoint(0.6, 0.72)})
    assert left.cursor == left.reach(left.left_wrist)
    only = figure({RIGHT_WRIST: Keypoint(0.8, 0.3, 0.0), LEFT_WRIST: Keypoint(0.4, 0.65)})
    assert only.cursor == only.reach(only.left_wrist)
    none = figure({RIGHT_WRIST: Keypoint(0.8, 0.3, 0.0), LEFT_WRIST: Keypoint(0.4, 0.65, 0.1)})
    assert none.cursor is None


def test_anchor_order():
    assert figure().anchor == Keypoint(0.5, 0.4)
    hidden = {LEFT_SHOULDER: Keypoint(0.4, 0.4, 0.0), RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0)}
    assert figure(hidden).anchor == Keypoint(0.5, 0.22)
    assert figure({**hidden, NOSE: Keypoint(0.5, 0.22, 0.0)}).anchor == Keypoint(0.5, 0.7)


def test_place_uses_calibration_zone():
    b = figure()
    placed = place(b, Calibration())                  # zone (0.2, 0.2, 0.8, 0.8), min_height 0.45
    assert placed.in_zone
    assert (placed.zone_x, placed.zone_y) == pytest.approx((0.5, (0.4 - 0.2) / 0.6))
    assert placed.keypoints == b.keypoints and placed.scale == b.scale and b.zone_y == 0.5
    right = place(b, Calibration(zone=(0.6, 0.0, 1.0, 1.0)))
    assert not right.in_zone and right.zone_x == 0.0                       # clamped to the zone edge
    short = place(figure(box=(0.3, 0.2, 0.7, 0.6)), Calibration())         # 0.4 tall, under min_height
    assert not short.in_zone
    tall_enough = place(figure(box=(0.3, 0.2, 0.7, 0.65)), Calibration())
    assert tall_enough.in_zone


def test_place_blob():
    assert place_blob(Blob(0.5, 0.5, 0.03, (255, 255, 255)), Calibration()).in_zone
    assert not place_blob(Blob(0.05, 0.1, 0.03, (255, 255, 255)), Calibration()).in_zone
    assert Blob(0.1, 0.2, 0.05, (255, 0, 0)).in_zone


def test_skeleton_indices_valid():
    assert all(0 <= a < 17 and 0 <= b < 17 for a, b in SKELETON)
    assert Blob(0.1, 0.2, 0.05, (255, 0, 0)).color == (255, 0, 0)


def test_sensed_and_audio_take_keywords_after_t():
    # C12: revision 2 called Sensed(t, bodies, blobs, motion, audio); in spec 5's field order that binds
    # the bodies to camera_t without an error. Audio(0.8, 1.0) would put 1.0 in level_smooth.
    with pytest.raises(TypeError):
        Sensed(1.0, (figure(),))
    with pytest.raises(TypeError):
        Audio(0.8, 1.0)
    assert [f.name for f in dataclasses.fields(Sensed) if not f.kw_only] == ["t"]
    assert all(f.kw_only for f in dataclasses.fields(Audio))
    s = Sensed(1.0, bodies=(figure(),), audio=Audio(level=0.8, level_smooth=1.0))
    assert s.bodies[0].id == 1 and s.camera_t == 0.0 and s.audio.level_smooth == 1.0


def test_one_shoulder_without_hips_uses_the_nose_line():
    # C14: one shoulder and no hip give no torso, so a line from the shoulders would sit on the shoulder.
    no_hips = {RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0), LEFT_HIP: Keypoint(0.45, 0.7, 0.0),
               RIGHT_HIP: Keypoint(0.55, 0.7, 0.0)}
    b = figure(no_hips)
    assert b.shoulder_mid is not None and b.torso == 0.0
    assert b.raise_line == pytest.approx(0.22)                                           # the nose
    assert figure({**no_hips, RIGHT_WRIST: Keypoint(0.65, 0.395)}).raised_wrist is None   # a hair over the shoulder
    assert figure({**no_hips, RIGHT_WRIST: Keypoint(0.65, 0.25)}).raised_wrist is None    # under the nose
    assert figure({**no_hips, RIGHT_WRIST: Keypoint(0.65, 0.18)}).raised_wrist == Keypoint(0.65, 0.18)
    assert figure({**no_hips, LEFT_WRIST: Keypoint(0.35, 0.1), RIGHT_WRIST: Keypoint(0.65, 0.18)}).both_hands_up
    blind = figure({**no_hips, NOSE: Keypoint(0.5, 0.22, 0.0), RIGHT_WRIST: Keypoint(0.65, 0.1),
                    LEFT_WRIST: Keypoint(0.35, 0.1)})
    assert blind.raise_line is None and blind.raised_wrist is None and not blind.both_hands_up


def test_blob_coordinates_are_clamped():
    # C16: headlamps() crosses from x -0.05 to 1.05; a consumer mapping x to a pixel would index at -1.
    b = Blob(-0.05, 1.2, 0.02, (255, 250, 235))
    assert (b.x, b.y) == (0.0, 1.0)
    assert Blob(math.nan, 0.5, 0.02, (255, 0, 0)).x == 0.0 and Blob(0.3, math.inf, 0.02, (255, 0, 0)).y == 1.0
    assert Blob(None, 0.5, 0.02, (255, 0, 0)).x == 0.0                                  # as a keypoint's None
    assert place_blob(b, Calibration()).x == 0.0
    assert Blob(0.25, 0.75, 0.02, (255, 0, 0)) == Blob(0.25, 0.75, 0.02, (255, 0, 0), True)   # in range: kept


def test_raise_line_needs_a_torso_over_the_floor():
    # C22: side-on at the bar the shoulders overlap (0.03 apart) and the counter hides the hips. The torso from
    # the shoulder width is 0.0375, under 0.1 of the 0.8 box, and a line from it would sit a hair (0.011) above
    # the shoulders, so a wrist at the collarbone would count as raised.
    from arcade.sensed import TORSO_FLOOR
    side = {LEFT_SHOULDER: Keypoint(0.485, 0.4), RIGHT_SHOULDER: Keypoint(0.515, 0.4),
            LEFT_HIP: Keypoint(0.45, 0.7, 0.0), RIGHT_HIP: Keypoint(0.55, 0.7, 0.0)}
    b = figure(side)
    assert TORSO_FLOOR == 0.1
    assert b.torso == pytest.approx(0.0375) and b.torso < TORSO_FLOOR * b.height
    assert b.raise_line == pytest.approx(0.22)                                           # the nose
    assert figure({**side, RIGHT_WRIST: Keypoint(0.65, 0.38)}).raised_wrist is None      # at the collarbone
    assert figure({**side, RIGHT_WRIST: Keypoint(0.65, 0.18)}).raised_wrist == Keypoint(0.65, 0.18)
    assert figure({**side, NOSE: Keypoint(0.5, 0.22, 0.0)}).raise_line is None           # no nose either: None
    near = figure(side, box=(0.3, 0.6, 0.7, 0.95))              # a 0.35 box: the floor is 0.035, the torso passes
    assert near.raise_line == pytest.approx(0.4 - 0.3 * 0.0375)
    assert figure().raise_line == pytest.approx(0.31)                                     # a full torso is unchanged


# C46: the spike (the owner at 2 m) has shoulders 0.128 apart and a torso of 0.26, 2.03 shoulder widths, where
# TORSO_PER_SHOULDER_WIDTH assumes 1.25; without hips the reach box then sat 0.1 torso too low and a raised wrist
# read v 0.
NO_HIPS = {LEFT_HIP: Keypoint(0.45, 0.7, 0.0), RIGHT_HIP: Keypoint(0.55, 0.7, 0.0),
           LEFT_KNEE: Keypoint(0.45, 0.85, 0.0), RIGHT_KNEE: Keypoint(0.55, 0.85, 0.0),
           LEFT_ANKLE: Keypoint(0.45, 0.95, 0.0), RIGHT_ANKLE: Keypoint(0.55, 0.95, 0.0)}
SPIKE_SHOULDERS = {LEFT_SHOULDER: Keypoint(0.436, 0.4), RIGHT_SHOULDER: Keypoint(0.564, 0.4)}


def test_body_defaults_are_measured_with_the_default_torso():
    b = figure()
    assert b.measured is True and b.torso_per_width == 0.0
    assert b.torso == pytest.approx(0.3) and b.raise_line == pytest.approx(0.31)          # hips: the measure
    assert b.reach(Keypoint(0.8, 0.7)) == pytest.approx((1.0, 1.0))
    bare = figure(NO_HIPS)                                     # shoulders 0.2 apart: 1.25 x 0.2 as today
    assert bare.measured is True and bare.torso_per_width == 0.0
    assert bare.torso == pytest.approx(0.25) and bare.raise_line == pytest.approx(0.4 - 0.3 * 0.25)
    assert bare.reach(Keypoint(0.2, 0.4 - 1.05 * 0.25)) == pytest.approx((0.0, 0.0))
    assert bare.reach(Keypoint(0.8, 0.4 + 0.25)) == pytest.approx((1.0, 1.0))
    assert figure(NO_HIPS, measured=False).torso == pytest.approx(0.25)                   # measured alone: no change


def test_torso_without_hips_uses_the_learned_ratio():
    over = {**NO_HIPS, **SPIKE_SHOULDERS, LEFT_WRIST: Keypoint(0.35, 0.7, 0.0), RIGHT_WRIST: Keypoint(0.6, 0.2)}
    learned = figure(over, torso_per_width=2.03)
    assert learned.shoulder_width == pytest.approx(0.128)
    assert learned.torso == pytest.approx(0.26, abs=0.001)                                # the spike's measure
    assert learned.raise_line == pytest.approx(0.4 - 0.3 * 2.03 * 0.128)                 # Q74: one torso for all
    width = 2 * 1.5 * 0.128
    assert learned.reach(Keypoint(0.5 - 1.5 * 0.128, 0.5))[0] == pytest.approx(0.0)       # the width is the shoulders'
    assert learned.reach(Keypoint(0.5 + width / 2, 0.5))[0] == pytest.approx(1.0)
    assert learned.cursor[1] > 0.05, learned.cursor                                       # 0.2 above the shoulders
    assert figure(over).cursor[1] == 0.0                                                  # the default ratio: clamped
    # one shoulder with the hips seen: the width comes from the torso by the same ratio (0.3 / 2.03, not / 1.25)
    one = figure({RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0)}, torso_per_width=2.03)
    assert one.shoulder_width == 0.0 and one.torso == pytest.approx(0.3)
    assert one.reach(Keypoint(0.5 + 1.5 * 0.3 / 2.03, 0.5))[0] == pytest.approx(1.0)
    assert figure({RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0)}).reach(Keypoint(0.5 + 1.5 * 0.24, 0.5))[0] == \
        pytest.approx(1.0)                                                                # the default: 0.3 / 1.25


def test_a_bad_torso_ratio_reads_the_default():
    for bad in (math.nan, -1.0, math.inf):
        b = figure(NO_HIPS, torso_per_width=bad)
        assert b.torso_per_width == 0.0, bad
        assert b.torso == pytest.approx(0.25), bad
