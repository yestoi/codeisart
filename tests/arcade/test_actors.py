import math

import numpy as np
import pytest

from arcade.poses import POSES
from arcade.sensed import LEFT_WRIST, NOSE, RIGHT_WRIST, Keypoint
from arcade.sources.actors import (TICK, Person, claps, level_ramp, loud, make_keypoints, motion_rect,
                                   moving_blob, scene, silence, tempo)


def test_make_keypoints_is_a_standing_figure():
    kps = make_keypoints(0.5, 0.5, 0.6)
    assert len(kps) == 17
    assert kps[NOSE].y < kps[LEFT_WRIST].y
    up = make_keypoints(0.5, 0.5, 0.6, right_up=True)
    assert up[RIGHT_WRIST].y < up[NOSE].y and up[LEFT_WRIST].y > up[NOSE].y


def test_person_walks_and_holds_position():
    p = Person(0.1).walk(0.9, seconds=2.0)
    assert p.body_at(0.0, 0).center[0] == pytest.approx(0.1, abs=0.02)
    assert p.body_at(1.0, 0).center[0] == pytest.approx(0.5, abs=0.02)
    assert p.body_at(5.0, 0).center[0] == pytest.approx(0.9, abs=0.02)


def test_person_chained_walks_start_where_the_last_ended():
    p = Person(0.2).walk(0.6, 1.0).walk(0.2, 1.0)
    assert p.body_at(1.0, 0).center[0] == pytest.approx(0.6, abs=0.02)
    assert p.body_at(2.0, 0).center[0] == pytest.approx(0.2, abs=0.02)


def test_hands_and_jump_and_presence():
    p = Person().raise_hand(at=1.0, seconds=0.5).both_hands_up(at=3.0, seconds=1.0).jump(at=5.0, height=0.2)
    assert p.body_at(0.5, 0).raised_wrist is None
    assert p.body_at(1.2, 0).raised_wrist is not None and not p.body_at(1.2, 0).both_hands_up
    assert p.body_at(3.5, 0).both_hands_up
    standing = p.body_at(4.0, 0).nose.y
    assert p.body_at(5.3, 0).nose.y < standing - 0.1
    q = Person().leave(at=2.0)
    assert q.present(1.9) and not q.present(2.1)
    r = Person().arrive(at=2.0)
    assert not r.present(1.9) and r.present(2.1)


def test_scene_assigns_ids_and_ticks():
    frames = list(scene(persons=[Person(0.2), Person(0.8)], ticks=3))
    assert len(frames) == 3
    assert [b.id for b in frames[0].bodies] == [0, 1]
    assert frames[1].t == pytest.approx(TICK)
    assert frames[0].motion.shape == (64, 128) and not frames[0].motion.any()


def test_blob_and_audio_scripts():
    b = moving_blob(0.0, 0.5, 1.0, 0.5, seconds=2.0, color=(255, 0, 0))
    assert b(-0.1) is None and b(2.1) is None
    assert b(1.0).x == pytest.approx(0.5) and b(1.0).color == (255, 0, 0)
    assert silence()(3.0).level == 0.0
    c = claps([1.0, 2.0])
    hits = [i for i in range(90) if c(i * TICK).onset]
    assert len(hits) == 2
    t = tempo(120)
    beats = [i for i in range(90) if t(i * TICK).beat]
    assert beats == [0, 15, 30, 45, 60, 75]
    assert t(0.1).bpm == 120
    assert loud(0.9)(0.0).level == 0.9
    frames = list(scene(blobs=[b], audio=c, ticks=60))
    assert frames[30].blobs[0].x == pytest.approx(0.5, abs=0.01)
    assert frames[30].audio.onset


def test_tempo_128_exactly_one_beat_per_period():
    for bpm in (60, 90, 100, 120, 128, 140, 174, 200):
        script = tempo(bpm)
        beats = [i for i in range(1800) if script(i * TICK).beat]
        assert len(beats) == bpm, f"{bpm} bpm gave {len(beats)} beats in 60 s"
        gaps = np.diff(beats)
        assert gaps.min() >= math.floor(1800 / bpm), f"{bpm} bpm has a gap of {gaps.min()} ticks"
    late = tempo(128, start=2.0)
    first = next(i for i in range(1800) if late(i * TICK).beat)
    assert first == 60


def test_claps_fire_exactly_once():
    for k in range(300):
        when = k * 0.0123
        script = claps([when])
        hits = [i for i in range(120) if script(i * TICK).clap]
        assert hits == [math.ceil(when / TICK - 1e-6)], f"clap at {when} fired on ticks {hits}"
        assert all(script(i * TICK).onset == (i in hits) for i in range(120))


def test_wrist_ramp_in_reach_units():
    p = Person().wrist("right", 0.9, 0.1, seconds=2.0, at=1.0).wrist("right", 0.1, 0.5, seconds=1.0)
    assert p.body_at(0.5, 0).right_wrist == make_keypoints(0.5, 0.55, 0.6)[RIGHT_WRIST]   # hanging before
    for t, v in ((1.0, 0.9), (2.0, 0.5), (2.9, 0.14), (3.5, 0.3)):
        body = p.body_at(t, 0)
        assert body.reach(body.right_wrist)[1] == pytest.approx(v, abs=1e-9), f"t={t}"
        assert body.left_wrist == make_keypoints(0.5, 0.55, 0.6)[LEFT_WRIST]
    assert p.body_at(2.9, 0).raised_wrist is not None and p.body_at(1.0, 0).raised_wrist is None
    assert p.body_at(4.0, 0).right_wrist == make_keypoints(0.5, 0.55, 0.6)[RIGHT_WRIST]   # hanging after
    with pytest.raises(ValueError, match="hand"):
        Person().wrist("middle", 0.0, 1.0, 1.0)


def test_wrist_works_for_a_body_partly_out_of_frame():
    low = Person(y=1.05).wrist("right", 0.5, 0.5, seconds=1.0).body_at(0.5, 0)       # hips below the frame
    assert low.hip_mid is None and low.right_wrist.conf == 1.0
    high = Person(y=0.3, height=0.6).jump(at=0.0, height=0.2).wrist("left", 0.0, 0.0, seconds=1.0)
    assert high.body_at(0.3, 0).left_wrist.conf == 0.0                               # above the frame: clamped
    inside = Person().wrist("right", 0.3, 0.3, seconds=1.0).body_at(0.5, 0)
    assert inside.reach(inside.right_wrist)[1] == pytest.approx(0.3, abs=1e-9)


def test_pose_from_table():
    assert set(POSES) >= {"stand", "t_pose", "arms_up"}
    assert all(len(offsets) == 17 for offsets in POSES.values())
    stand = tuple(Keypoint(0.5 + dx * 0.6, 0.55 + dy * 0.6) for dx, dy in POSES["stand"])
    assert make_keypoints(0.5, 0.55, 0.6) == stand
    p = Person(x=0.5, y=0.55, height=0.6).pose("t_pose", at=1.0, seconds=2.0)
    held = p.body_at(1.5, 0)
    for i, (dx, dy) in enumerate(POSES["t_pose"]):
        assert (held.keypoints[i].x, held.keypoints[i].y) == pytest.approx((0.5 + dx * 0.6, 0.55 + dy * 0.6))
    assert p.body_at(0.5, 0).keypoints == make_keypoints(0.5, 0.55, 0.6)
    assert p.body_at(3.0, 0).keypoints == make_keypoints(0.5, 0.55, 0.6)
    assert Person().pose("arms_up", at=0.0, seconds=1.0).body_at(0.5, 0).both_hands_up


def test_unknown_pose_raises():
    with pytest.raises(ValueError, match="unknown pose 'dab'"):
        Person().pose("dab", at=0.0, seconds=1.0)


def test_motion_rect_grid():
    m = motion_rect(0.25, 0.5, 0.5, 1.0, start=1.0, seconds=1.0)
    assert m(0.9) is None and m(2.0) is None
    grid = m(1.5)
    assert grid.shape == (64, 128) and grid.dtype == bool
    assert grid[32:, 32:64].all() and grid.sum() == 32 * 32
    tiny = motion_rect(0.5, 0.5, 0.5, 0.5, start=0.0, seconds=1.0)(0.0)
    assert tiny.sum() == 1 and tiny[32, 64]
    frames = list(scene(motion=[m, motion_rect(0.0, 0.0, 0.1, 0.1, start=0.0, seconds=0.5)], ticks=60))
    assert frames[0].motion[:7, :13].all() and not frames[0].motion[32:, 32:64].any()
    assert frames[45].motion[32:, 32:64].all() and not frames[45].motion[:7, :13].any()
    assert not frames[20].motion.any()
    with pytest.raises(ValueError, match="shape"):
        list(scene(motion=[lambda t: np.zeros((4, 4), bool)], ticks=1))


def test_level_ramp_interpolates():
    ramp = level_ramp([(1.0, 0.0), (3.0, 1.0), (4.0, 0.5)])
    assert ramp(0.0).level == 0.0 and ramp(2.0).level == pytest.approx(0.5)
    assert ramp(3.5).level == pytest.approx(0.75) and ramp(9.0).level == 0.5
    assert ramp(2.0).level_smooth == ramp(2.0).peak == ramp(2.0).level
    with pytest.raises(ValueError):
        level_ramp([(2.0, 0.0), (1.0, 1.0)])
    with pytest.raises(ValueError):
        level_ramp([])


def test_scene_stamps_camera_and_places_bodies():
    big, small = Person(0.5, height=0.6), Person(0.1, height=0.3)
    frames = list(scene(persons=[small, big], blobs=[moving_blob(0.5, 0.5, 0.5, 0.5, 9.0)] * 10, ticks=3))
    f = frames[2]
    assert (f.camera_t, f.camera_fresh, f.camera_seq) == (f.t, True, 3)
    assert [b.id for b in f.bodies] == [1, 0]                   # largest scale first
    assert f.bodies[0].in_zone and not f.bodies[1].in_zone     # the small one is short and off to the side
    assert len(f.blobs) == 8 and all(b.in_zone for b in f.blobs)


def test_person_velocity():
    p = Person(0.1).walk(0.9, seconds=2.0).jump(at=3.0, height=0.2)
    assert p.body_at(1.0, 0).vx == pytest.approx(0.4)
    assert p.body_at(0.0, 0).vx == 0.0                          # causal: not yet moving at the start
    assert p.body_at(2.0, 0).vx == pytest.approx(0.4)           # the last tick of the walk still moved
    assert p.body_at(2.5, 0).vx == 0.0 and p.body_at(2.5, 0).vy == 0.0
    assert p.body_at(3.1, 0).vy < 0                             # rising


def test_tempo_needs_a_positive_bpm():
    # C16: tempo(0) divided by zero; a negative bpm gave a negative period.
    for bad in (0, -120, math.nan, math.inf):
        with pytest.raises(ValueError, match="bpm"):
            tempo(bad)
