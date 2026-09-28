import inspect
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from arcade.calibration import Calibration
from arcade.sensed import MIN_CONF, Sensed, place
from arcade.sources.actors import (REAL_NOISE, TICK, Person, camp_kick, claps, crowd, degrade, headlamps,
                                   motion_rect, scene, shake, wind)

ROOT = Path(__file__).resolve().parents[2]

DIGEST = """
import hashlib
from arcade.sources.actors import Person, crowd, degrade, scene
frames = degrade(scene(persons=[Person(0.3).walk(0.7, 2.0).raise_hand(at=1.0), *crowd(3)], ticks=90))
h = hashlib.sha256()
for f in frames:
    h.update(repr((f.camera_seq, f.camera_fresh, [(b.id, b.keypoints, b.in_zone) for b in f.bodies])).encode())
digest = h.hexdigest()
"""


def walker():
    return Person(0.2).walk(0.8, 3.0)


def test_degrade_samples_holds_and_delays():
    source = list(scene(persons=[walker()], audio=claps([0.2]), ticks=90))
    frames = list(degrade(iter(source)))
    assert len(frames) == 90
    fresh = [i for i, f in enumerate(frames) if f.camera_fresh]
    assert fresh == list(range(5, 90, 3)) and len(fresh) == 29        # 10 fps, first visible at 0.15 s
    for f in frames[:5]:
        assert f.bodies == () and f.camera_seq == 0 and f.motion.size == 0
    for i, f in enumerate(frames[5:], start=5):
        assert f.t == source[i].t
        assert 0.15 - 1e-9 <= f.t - f.camera_t < 0.25, f"tick {i}: camera_t {f.camera_t}"
        assert f.camera_seq == (i - 5) // 3 + 1
    assert frames[6].bodies == frames[5].bodies and frames[7].bodies == frames[5].bodies
    assert frames[8].bodies != frames[5].bodies
    assert frames[6].audio.clap and not frames[6].camera_fresh     # audio is not delayed
    clean = list(degrade(iter(source), keypoint_dropout=0.0, jitter=0.0))
    assert clean[8].bodies == source[3].bodies                       # capture 1 is the scene at 0.1 s


def test_degrade_without_noise_is_the_scene():
    source = list(scene(persons=[walker()], motion=[motion_rect(0.0, 0.0, 0.5, 0.5, 0.0, 1.0)], ticks=40))
    frames = list(degrade(iter(source), fps=30, latency=0.0, keypoint_dropout=0.0, jitter=0.0))
    for i, (f, s) in enumerate(zip(frames, source)):
        assert f.bodies == s.bodies and f.camera_fresh and f.camera_seq == i + 1
        assert f.camera_t == s.t and np.array_equal(f.motion, s.motion)


def test_degrade_drops_and_jitters_at_the_given_rates():
    source = list(scene(persons=[walker(), Person(0.7, id=7)], ticks=300))
    frames = [f for f in degrade(iter(source), latency=0.0) if f.camera_fresh]
    dropped = total = 0
    for f in frames:
        truth = source[round(f.camera_t / TICK)]
        for b, t in zip(f.bodies, truth.bodies):
            for k, kt in zip(b.keypoints, t.keypoints):
                total += 1
                dropped += k.conf == 0.0
                assert abs(k.x - kt.x) <= 0.01 + 1e-9 and abs(k.y - kt.y) <= 0.01 + 1e-9
    assert total == 100 * 2 * 17
    assert 0.10 <= dropped / total <= 0.20, f"dropped {dropped} of {total}"


def test_degrade_rejects_bad_parameters():
    for bad in ({"fps": 0}, {"latency": -0.1}, {"keypoint_dropout": 1.5}, {"jitter": -0.01},
                {"fps": float("nan")}):
        with pytest.raises(ValueError, match="degrade needs"):
            list(degrade(scene(ticks=1), **bad))


def test_degrade_refuses_a_stream_that_does_not_start_at_zero():
    source = list(scene(persons=[walker()], ticks=60))
    with pytest.raises(ValueError, match="starts at t=0; frame 0 has t=1.0"):
        list(degrade(iter(source[30:])))
    with pytest.raises(ValueError, match="frame 2"):
        list(degrade(iter(source[:2] + source[3:])))


def test_still_player_keeps_cursor_and_zone_steady_under_spec_noise():
    source = scene(persons=[Person().raise_hand(at=0.0, seconds=99.0)], ticks=900)
    noise = degrade(source, fps=10, latency=0.15, keypoint_dropout=0.15, jitter=0.01)   # spec 6.4 literals
    captures = [f.bodies[0] for f in noise if f.camera_fresh]
    assert len(captures) == 299
    u = np.array([b.cursor[0] for b in captures if b.right_wrist.conf >= MIN_CONF])
    zone_x = np.array([b.zone_x for b in captures])
    assert np.median(u) == pytest.approx(0.71, abs=0.02) and np.median(zone_x) == pytest.approx(0.5, abs=0.01)
    # A dropped shoulder, or a dropped shoulder and hip, once moved the centre half a width (u by 0.15).
    assert np.mean(np.abs(u - np.median(u)) > 0.1) <= 0.02
    assert np.mean(np.abs(zone_x - np.median(zone_x)) > 0.05) <= 0.02


def test_degrade_is_deterministic():
    runs = []
    for _ in range(2):
        ns: dict = {}
        exec(DIGEST, ns)
        runs.append(ns["digest"])
    for seed in ("0", "12345"):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        out = subprocess.run([sys.executable, "-c", DIGEST + "print(digest)"], cwd=ROOT, env=env,
                             capture_output=True, text=True, check=True)
        runs.append(out.stdout.strip())
    assert len(set(runs)) == 1, runs


def test_real_noise_is_a_degrade_setting():
    assert set(REAL_NOISE) == {"fps", "latency", "keypoint_dropout", "jitter"}     # values are refit (spec 9.5)
    assert len(list(degrade(scene(persons=[walker()], ticks=30), **REAL_NOISE))) == 30
    names = ("fps", "latency", "keypoint_dropout", "jitter")
    defaults = {n: inspect.signature(degrade).parameters[n].default for n in names}
    assert defaults == {"fps": 10, "latency": 0.15, "keypoint_dropout": 0.15, "jitter": 0.01}   # spec 6.4


def test_crowd_is_out_of_zone():
    people = crowd(6)
    assert len(people) == 6 and len({p.id for p in people}) == 6
    raised = 0
    for f in scene(persons=[Person(0.5), *people], ticks=300):
        assert len(f.bodies) == 7
        assert [b.in_zone for b in f.bodies] == [True] + [False] * 6
        assert f.bodies[0].id == 0                                    # the player is the largest
        raised += sum(b.raised_wrist is not None for b in f.bodies[1:])
    assert raised > 0                                                 # the crowd waves


def test_camp_kick_has_onsets_but_no_claps():
    kick = camp_kick(125)
    frames = [kick(i * TICK) for i in range(1800)]
    assert sum(a.onset for a in frames) == 125 and sum(a.beat for a in frames) == 125
    assert not any(a.clap for a in frames)
    assert all(a.voice == 0.0 and a.voice_db == a.floor_db and a.bpm == 125 for a in frames)


def test_wind_never_claps():
    frames = [wind()(i * TICK) for i in range(1800)]
    assert not any(a.clap or a.beat for a in frames)
    assert 20 <= sum(a.onset for a in frames) <= 25
    assert all(a.voice < 0.1 for a in frames) and max(a.level for a in frames) > 0.45


def test_headlamps_are_out_of_zone():
    frames = list(scene(blobs=headlamps(), ticks=1800))
    assert all(f.blobs and not any(b.in_zone for b in f.blobs) for f in frames)
    crossing = [i for i, f in enumerate(frames) if len(f.blobs) == 2]
    assert crossing and crossing[0] == 0 and 600 in crossing and 300 not in crossing


def test_shake_empties_motion_and_jitters():
    source = list(scene(persons=[walker()], motion=[motion_rect(0.0, 0.0, 1.0, 1.0, 0.0, 9.0)], ticks=90))
    shaken = list(shake(1.0, 1.0)(iter(source)))
    assert len(shaken) == 90
    for i, (f, s) in enumerate(zip(shaken, source)):
        if 30 <= i < 60:
            assert f.motion.size == 0
            for k, ks in zip(f.bodies[0].keypoints, s.bodies[0].keypoints):
                assert abs(k.x - ks.x) <= 0.03 + 1e-9 and abs(k.y - ks.y) <= 0.03 + 1e-9 and k.conf == ks.conf
            assert f.bodies[0].keypoints != s.bodies[0].keypoints
        else:
            assert f is s
    first = list(shake(1.0, 1.0)(iter(source)))
    assert all(a.bodies == b.bodies for a, b in zip(first, shaken))


def test_shake_places_against_the_scene_calibration():
    right = Calibration(zone=(0.5, 0.2, 1.0, 0.8))
    source = list(scene(persons=[Person(0.85)], ticks=60, calibration=right))
    assert all(f.bodies[0].in_zone for f in source)
    shaken = list(shake(0.5, 1.0, calibration=right)(iter(source)))
    assert all(f.bodies[0].in_zone for f in shaken)
    with pytest.raises(ValueError, match="calibration"):                    # owner decision Q9: no silent default zone
        list(shake(0.5, 1.0)(iter(source)))


def test_degrade_needs_the_scene_calibration():
    # C13: degrade (and shake, owner decision Q9) placed noisy bodies against the default zone whatever
    # the scene used.
    right = Calibration(zone=(0.5, 0.2, 1.0, 0.8))
    source = list(scene(persons=[Person(0.85)], ticks=60, calibration=right))
    with pytest.raises(ValueError, match="calibration"):
        list(degrade(iter(source)))
    kept = list(degrade(iter(source), keypoint_dropout=0.0, jitter=0.0, calibration=right))
    assert all(f.bodies[0].in_zone for f in kept[5:]) and kept[8].bodies == source[3].bodies
    noisy = list(degrade(iter(source), calibration=right))
    assert sum(f.bodies[0].in_zone for f in noisy[5:]) >= 0.9 * 55
    unplaced = [Sensed(t=i * TICK, bodies=(Person().body_at(i * TICK, 0),)) for i in range(6)]
    with pytest.raises(ValueError, match="place"):
        list(degrade(iter(unplaced)))
    # Calibrations that differ from the default in one placement field each: min_height moves in_zone
    # alone, a wider zone zone_x alone, a taller one zone_y alone. degrade and shake catch every one.
    for cal, x in ((Calibration(min_height=0.3), 0.5), (Calibration(zone=(0.1, 0.2, 0.9, 0.8)), 0.4),
                   (Calibration(zone=(0.2, 0.1, 0.8, 0.9)), 0.5)):
        source = list(scene(persons=[Person(x, height=0.4)], ticks=12, calibration=cal))
        b, default = source[0].bodies[0], place(source[0].bodies[0], Calibration())
        differs = (b.in_zone != default.in_zone, b.zone_x != default.zone_x, b.zone_y != default.zone_y)
        assert sum(differs) == 1, (cal, differs)
        with pytest.raises(ValueError, match="calibration"):
            list(degrade(iter(source)))
        with pytest.raises(ValueError, match="calibration"):
            list(shake(0.0, 1.0)(iter(source)))
        assert len(list(degrade(iter(source), calibration=cal))) == 12
        assert len(list(shake(0.0, 1.0, calibration=cal)(iter(source)))) == 12
    # Every body is checked, not just the first: body 1 stands outside both zones, body 2 only in the scene's.
    source = list(scene(persons=[Person(0.1, id=1), Person(0.85, id=2)], ticks=12, calibration=right))
    with pytest.raises(ValueError, match="body 2"):
        list(degrade(iter(source)))
    with pytest.raises(ValueError, match="body 2"):
        list(shake(0.0, 1.0)(iter(source)))


def test_scene_refuses_duplicate_ids_and_crowd_takes_an_id_base():
    # C15: crowd always started at 100 and scene used the list index, so ids could collide.
    with pytest.raises(ValueError, match="duplicate body id 100"):
        scene(persons=[Person(), *crowd(2), *crowd(2)])
    with pytest.raises(ValueError, match="duplicate body id 0"):
        scene(persons=[Person(0.2), Person(0.5, id=0)])
    assert [p.id for p in crowd(3, id_base=200)] == [200, 201, 202]
    frames = list(scene(persons=[Person(), *crowd(2), *crowd(2, id_base=200)], ticks=1))
    assert sorted(b.id for b in frames[0].bodies) == [0, 100, 101, 200, 201]


def test_festival_guard_rails():
    # C16: headlamp blobs stay on the wall; camp_kick(0) is a ValueError; degrade keeps the detector box.
    assert all(0.0 <= b.x <= 1.0 for f in scene(blobs=headlamps(), ticks=600) for b in f.blobs)
    with pytest.raises(ValueError, match="bpm"):
        camp_kick(0)
    source = list(scene(persons=[walker()], ticks=30))
    for f in degrade(iter(source)):
        for b in f.bodies:
            truth = source[round(f.camera_t / TICK)].bodies[0]
            assert (b.box, b.scale, b.vx, b.vy) == (truth.box, truth.scale, truth.vx, truth.vy)
