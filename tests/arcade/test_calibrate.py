"""calibrate (spec 6.6): the Calibrator is the runner's lobby with no games, driven by actors through run_headless.

sheet_scene and sheet_frames are for I2's contact sheet:
    python -m tools.arcade_shot jump --lobby tests.arcade.test_calibrate:sheet_scene \
        --scenario tests.arcade.test_calibrate:sheet_frames --out docs/superpowers/workflow/evidence/it21/calibrate
"""
from __future__ import annotations

import dataclasses
import random
import tempfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from arcade import calibrate
from arcade.calibrate import (CLEAR_SECONDS, DOT, LIGHT, MARGIN, MIN_HEIGHT_SHARE, STATIC_RADIUS, STEP_TIMEOUT,
                              ZONE, Calibrator, view_xy)
from arcade.calibration import FILENAME, Calibration, load_calibration
from arcade.canvas import Canvas
from arcade.feel import DIM_LEVEL, find_text
from arcade.flash import SMALL_AREA, concurrent_area
from arcade.headless import run_headless
from arcade.runner import Runner
from arcade.sensed import Blob, Sensed, place, place_blob
from arcade.sources import NoSource
from arcade.sources.actors import TICK, Person, moving_blob, scene
from tests.arcade.helpers import make_cfg

ROOT = Path(__file__).resolve().parents[2]
WALL = (128, 64)
FAR_H, NEAR_H = 0.5, 0.6            # a 0.15 jump leaves even the default zone above about 0.66 (jump.py:15-16)
STANDS = ((0.3, FAR_H), (0.7, FAR_H), (0.5, NEAR_H))     # (x, height): far left, far right, near
LAMP = (0.1, 0.1)                   # a still light, outside the default zone: the lobby sees every blob
LEAVES = 14.2                       # the operator leaves just after the clear begins (about 13.9 s): it restarts
VISITOR = (15.2, 15.7)              # someone walks into the clear: it restarts again
SCENE_SECONDS = 28.5                # the clear ends about 25.7 s, saved about 27.7 s
STEPS = ("aim", "far_left", "far_right", "near", "baseline", "clear", "saved")
WORDS = {"aim": "AIM: HANDS UP", "far_left": "STAND FAR LEFT", "far_right": "STAND FAR RIGHT",
         "near": "STAND AT THE FRONT", "baseline": "STAND STILL", "clear": "CLEAR THE FRAME 10", "saved": "SAVED",
         "failed": "NO ONE CAME"}


def operator() -> Person:
    """Both hands up, then still at each stand in turn (x 0.3 and 0.7 far, 0.5 near), still there for the baseline,
    then gone. Each walk starts about 0.3 s after the step before has ended (the steps' times follow the constants:
    aim about 2.0 s, far left 4.6, far right 7.9, near 10.9, baseline 13.9)."""
    p = Person(0.5, height=FAR_H, id=1).both_hands_up(at=0.0, seconds=2.4)
    p.walk(0.3, 0.6, at=2.1).walk(0.7, 1.0, at=5.0).walk(0.5, 0.6, at=8.3)
    p.scale_to(NEAR_H / FAR_H, 0.6, at=8.3)
    return p.leave(LEAVES)


def lamp(t: float) -> Blob:
    return Blob(*LAMP, 0.02, (255, 240, 200))


def sheet_frames(seconds: float = SCENE_SECONDS, visitor: bool = True):
    """The operator's calibration with a still lamp, a torch carried across the clear (seen in under STATIC_SHARE
    of its captures: never a static light) and a visitor who walks into the clear."""
    persons = [operator()]
    if visitor:
        persons.append(Person(0.6, height=FAR_H, id=2).arrive(VISITOR[0]).leave(VISITOR[1]))
    torch = moving_blob(0.2, 0.9, 0.9, 0.9, 3.0, color=(255, 255, 255), start=18.0)
    return scene(persons=persons, blobs=[lamp, torch], ticks=round(seconds / TICK))


def sheet_scene(games, cfg) -> Calibrator:
    """The lobby for tools.arcade_shot (called as f(games, cfg)): a Calibrator writing to a fresh temporary dir."""
    return Calibrator(Path(tempfile.mkdtemp(prefix="calibrate-sheet-")))


def _run(data_dir: Path, font, frames, **kw):
    cal = Calibrator(data_dir)
    _, runner = run_headless(make_cfg(WALL), font, [], frames, lobby=cal, trace=True, raw=True, **kw)
    return SimpleNamespace(cal=cal, runner=runner, data_dir=data_dir)


@pytest.fixture(scope="module")
def calibrated(tmp_path_factory, font5x7):
    return _run(tmp_path_factory.mktemp("calibrated"), font5x7, sheet_frames())


@pytest.fixture(scope="module")
def nobody(tmp_path_factory, font5x7):
    # an empty aim: failed at STEP_TIMEOUT, then "NO ONE CAME" END_SECONDS and done (62.5 s: done has come)
    return _run(tmp_path_factory.mktemp("nobody"), font5x7, scene(ticks=round(62.5 / TICK)))


def test_calibrate_with_actors_writes_zone(calibrated):
    cal = calibrated.cal
    assert cal.failed is None and cal.done() and cal.result is not None
    saved = load_calibration(calibrated.data_dir)
    assert saved == cal.result and saved.calibrated
    x0, y0, x1, y1 = saved.zone
    xs = [x for x, _ in STANDS]
    assert x0 == pytest.approx(min(xs) - MARGIN, abs=0.005) and x1 == pytest.approx(max(xs) + MARGIN, abs=0.005)
    assert y0 <= 0.2 and y1 >= 0.8                              # never thinner than the default's
    for x, h in STANDS:                                         # every stand's anchor inside, MARGIN from the side
        a = Person(x, height=h).body_at(0.0, 1).anchor
        assert x0 + MARGIN - 0.005 <= a.x <= x1 - MARGIN + 0.005 and y0 < a.y < y1
    far = Person(0.3, height=FAR_H).body_at(0.0, 1)
    assert saved.min_height == pytest.approx(MIN_HEIGHT_SHARE * far.height, abs=0.005)
    near = Person(0.5, height=NEAR_H).body_at(0.0, 1)
    assert saved.baseline_scale == pytest.approx(near.scale, abs=0.01)
    assert len(saved.static_mask) == 1                          # the lamp; never the torch
    x, y, r = saved.static_mask[0]
    assert (x, y) == pytest.approx(LAMP, abs=0.005) and r == STATIC_RADIUS
    assert saved.audio_floor_db == Calibration().audio_floor_db   # headless has no microphone: the default


def test_a_jump_stays_in_the_calibrated_zone(calibrated):
    zone = load_calibration(calibrated.data_dir)
    assert zone.calibrated and zone.zone != Calibration().zone            # the actors' zone, not the default
    for x, h in STANDS:
        p = Person(x, height=h, id=1).jump(at=0.3, height=0.15)
        bodies = [s.bodies[0] for s in scene([p], ticks=round(1.2 / TICK), calibration=zone)]
        standing = Person(x, height=h).body_at(0.0, 1).anchor.y
        assert max(standing - b.anchor.y for b in bodies) == pytest.approx(0.15, abs=0.01)    # the jump peaks
        assert all(b.in_zone for b in bodies), (x, h)
    tall = Person(0.5, height=0.7, id=1).jump(at=0.3, height=0.15)   # above about 0.66: out of even the default zone
    assert not all(s.bodies[0].in_zone for s in scene([tall], ticks=round(1.2 / TICK), calibration=Calibration()))


def _toml(tmp_path: Path, **over) -> Path:
    fields = {"backend": "fake", "camera": "none", "audio": "none", "data_dir": str(tmp_path / "data"),
              "font_path": str(ROOT / "fonts" / "5x7.bin"), **over}
    path = tmp_path / "arcade.toml"
    path.write_text("".join(f"{k} = {v!r}\n".replace("'", '"') for k, v in fields.items()))
    return path


def test_main_turns_hide_still_off(tmp_path, monkeypatch):
    """main opens the sources against the default calibration (raw camera space) and turns the camera's still-light
    hiding off: StaticMask would hide the lamp long before clear records it. The runner is strict, with no games,
    and loops until the Calibrator is done. The real loop runs on the real clock: here it ticks the actors' scene."""
    class Features:
        hide_still = True

    class Camera(NoSource):
        available = True

        def __init__(self):
            self.features, self.closed = Features(), False

        def close(self) -> None:
            self.closed = True

    camera, opened, looped = Camera(), [], []

    def fake_make_sources(cfg, size, *args, calibration=None, **kw):
        opened.append((size, args, kw, calibration))
        return camera, NoSource()

    def scene_loop(self, cam, audio, max_ticks=None, until=None):
        looped.append((self, cam.features.hide_still, max_ticks, until))
        for sensed in sheet_frames():
            self.tick(sensed, TICK)
            if until():
                break

    monkeypatch.setattr(calibrate, "make_sources", fake_make_sources)
    monkeypatch.setattr(Runner, "loop", scene_loop)
    config = _toml(tmp_path)
    assert calibrate.main(SimpleNamespace(config=str(config))) == 0
    assert opened == [((128, 64), (), {}, Calibration())]
    runner, hide_still, max_ticks, until = looped[0]
    assert hide_still is False and max_ticks is None
    assert isinstance(runner.lobby, Calibrator) and until == runner.lobby.done and runner.lobby.done()
    assert runner.strict and runner.games == {} and runner.calibration == Calibration()
    assert camera.closed and runner.display.closed
    assert load_calibration(tmp_path / "data").calibrated

    # A camera without features (the none camera) is fine; a calibration that never finished writes nothing: 1.
    (tmp_path / "data" / FILENAME).unlink()
    monkeypatch.setattr(calibrate, "make_sources", lambda cfg, size, **kw: (NoSource(), NoSource()))
    monkeypatch.setattr(Runner, "loop", lambda self, cam, audio, max_ticks=None, until=None: None)
    assert calibrate.main(SimpleNamespace(config=str(config))) == 1
    assert not (tmp_path / "data" / FILENAME).exists()


def test_nobody_comes_writes_no_file(nobody, font5x7):
    cal, trace = nobody.cal, nobody.runner.trace
    assert cal.phase == "failed" and cal.failed and cal.result is None and cal.done()
    assert not (nobody.data_dir / FILENAME).exists()
    first = next(s for s in trace if s["phase"] == "failed")
    assert first["t"] == pytest.approx(STEP_TIMEOUT, abs=2 * TICK)
    assert all(s["phase"] == "aim" for s in trace if s["t"] < first["t"])
    assert find_text(nobody.runner.raw_frames[-1], font5x7, WORDS["failed"], scales=(1,)) is not None


def test_a_body_restarts_the_clear(calibrated):
    trace = calibrated.runner.trace
    clear = [s["t"] for s in trace if s["phase"] == "clear"]
    saved = next(s["t"] for s in trace if s["phase"] == "saved")
    assert clear[0] < LEAVES < VISITOR[0] < saved
    assert saved - clear[0] > CLEAR_SECONDS + 1.0                         # the visitor held it up
    assert saved - VISITOR[1] == pytest.approx(CLEAR_SECONDS, abs=2 * TICK)   # CLEAR_SECONDS from the last body


def test_a_walking_body_does_not_stand(tmp_path, font5x7):
    p = Person(0.5, height=FAR_H, id=1).both_hands_up(at=0.0, seconds=2.4)
    p.walk(0.2, 6.0, at=2.1)                                    # 0.05 frame widths a second, then still at 0.2
    run = _run(tmp_path, font5x7, scene([p], ticks=round(10.5 / TICK)))
    trace = run.runner.trace
    aimed = next(s["t"] for s in trace if s["phase"] != "aim")
    walking = [s for s in trace if aimed <= s["t"] <= 8.1 + TICK]
    assert walking and all(s["phase"] == "far_left" and s["stands"] == 0 for s in walking)
    assert trace[-1]["phase"] == "far_right" and trace[-1]["stands"] == 1    # still at 0.2 for 2 s: a stand


def test_every_step_keeps_rows_60_to_63_dark_and_the_flash_rule(calibrated, nobody, font5x7):
    for run, steps in ((calibrated, STEPS), (nobody, ("aim", "failed"))):
        trace, raw = run.runner.trace, run.runner.raw_frames
        phases = [s["phase"] for s in trace]
        assert list(dict.fromkeys(phases)) == list(steps)
        assert run.runner.governor.held_ticks == 0
        assert not [i for i, f in enumerate(raw) if f[60:].any()]                  # the runner's marker rows
        assert not [i for i, f in enumerate(raw) if ((f > 0) & (f < DIM_LEVEL)).any()]   # no dim channel
        for step in steps:                                      # the step's words at 1x, at row 1, on its first tick
            found = find_text(raw[phases.index(step)], font5x7, WORDS[step], scales=(1,))
            assert found is not None and found[1] == 1, (step, found)
    assert concurrent_area(calibrated.runner.raw_frames) < SMALL_AREA
    fail = [s["phase"] for s in nobody.runner.trace].index("failed")
    assert concurrent_area(nobody.runner.raw_frames[fail - 30:fail + 30]) < SMALL_AREA


def test_dots_and_the_zone_are_drawn_in_the_view(calibrated, font5x7, tmp_path):
    cal = Calibrator(tmp_path)
    cal.reset(WALL, random.Random(0))
    body = place(Person(0.3, height=FAR_H, id=1).body_at(0.0, 1), Calibration())
    light = place_blob(lamp(0.0), Calibration())
    cal.update(Sensed(TICK, camera_fresh=True, bodies=(body,), blobs=(light,)), TICK)
    canvas = Canvas(*WALL, font5x7)
    cal.draw(canvas)
    for k in body.keypoints:
        x, y = view_xy(k.x, k.y)
        assert tuple(canvas.frame[y, x]) == DOT
    x, y = view_xy(*LAMP)
    assert tuple(canvas.frame[y, x]) == LIGHT
    last = calibrated.runner.raw_frames[-1]                      # saved: the zone's 1 px outline in the view
    x0, y0, x1, y1 = calibrated.cal.result.zone
    for px, py in (view_xy(x0, y0), view_xy(x1, y0), view_xy(x0, y1), view_xy(x1, y1)):
        assert tuple(last[py, px]) == ZONE
    inside = view_xy((x0 + x1) / 2, (y0 + y1) / 2)
    assert tuple(last[inside[1], inside[0]]) != ZONE


def test_a_zone_that_would_not_load_fails(tmp_path, font5x7, monkeypatch):
    monkeypatch.setattr(calibrate, "MARGIN", -0.3)    # x0 0.6 past x1 0.4: calibration.json would not load
    run = _run(tmp_path, font5x7, sheet_frames(seconds=25.0, visitor=False))
    cal = run.cal
    assert cal.phase == "failed" and cal.result is None and "zone" in cal.failed
    assert not (tmp_path / FILENAME).exists()
    assert find_text(run.runner.raw_frames[-1], font5x7, "NOT SAVED", scales=(1,)) is not None


def test_a_far_body_does_not_hold_the_clear(tmp_path, font5x7):
    # The event wall (2026-10-02) looks at a crowd: people walk behind the play spot through the whole clear, at
    # heights no player has. A body shorter than the min_height the calibration will save (MIN_HEIGHT_SHARE of the
    # shortest stand) is not a player and does not restart the clear.
    far_h = MIN_HEIGHT_SHARE * FAR_H - 0.05
    crowd = Person(0.6, height=far_h, id=2)                                 # there from start to end
    run = _run(tmp_path, font5x7, scene(persons=[operator(), crowd], blobs=[lamp], ticks=round(26.0 / TICK)))
    trace = run.runner.trace
    assert run.cal.failed is None, run.cal.failed
    saved = next(s["t"] for s in trace if s["phase"] == "saved")
    assert saved - LEAVES == pytest.approx(CLEAR_SECONDS, abs=0.5)         # CLEAR_SECONDS from the operator leaving
    assert load_calibration(run.data_dir).calibrated


def test_a_player_sized_body_still_holds_the_clear(tmp_path, font5x7):
    tall = Person(0.6, height=FAR_H, id=2).arrive(VISITOR[0]).leave(VISITOR[1])
    run = _run(tmp_path, font5x7, scene(persons=[operator(), tall], blobs=[lamp], ticks=round(28.5 / TICK)))
    saved = next(s["t"] for s in run.runner.trace if s["phase"] == "saved")
    assert saved - VISITOR[1] == pytest.approx(CLEAR_SECONDS, abs=2 * TICK)


def test_the_clear_lets_a_body_of_player_height_but_a_third_of_the_scale_be(tmp_path):
    # Behind a near player (legs out of frame) a far person can be as tall as the stands measured; its torso is not.
    cal = Calibrator(tmp_path)
    cal.stands = [(0.3, 0.5, FAR_H), (0.7, 0.5, FAR_H), (0.5, 0.5, NEAR_H)]
    crowd = Person(0.5, height=FAR_H).body_at(0.0, 2)                       # as tall as a far stand
    cal.baseline_scale = crowd.scale * 3
    cal.t = 0.0
    cal._next("clear")
    cal._clear(Sensed(1.0, bodies=(crowd,)), 1.0)
    assert cal._clear_since == 0.0                                           # not restarted
    player = dataclasses.replace(crowd, scale=cal.baseline_scale)
    cal._clear(Sensed(2.0, bodies=(player,)), 2.0)
    assert cal._clear_since == 2.0                                           # a player-sized body restarts it
