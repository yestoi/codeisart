import pytest

from arcade.attract.lobby import Lobby
from arcade.calibration import Calibration
from arcade.games import all_games
from arcade.headless import NullLobby
from arcade.runner import Runner
from arcade.sources import SCRIPTS, NoSource, make_sources
from arcade.sources.actors import Person, scene
from arcade.sources.scripted import ScriptedCamera
from show.display.fake import FakeDisplay
from tests.arcade.helpers import FakeClock, make_cfg


def test_make_sources_none_and_scripted():
    clock = FakeClock()
    cam, aud = make_sources(make_cfg((128, 32)), (128, 32), clock)
    assert isinstance(cam, NoSource) and isinstance(aud, NoSource)
    assert cam.latest() is None and aud.latest() is None and not cam.available and not aud.available

    # a script overrides the configured camera; audio stays the none source until M5
    cam, aud = make_sources(make_cfg((128, 32), camera="mediapipe", audio="sounddevice"), (128, 32), clock,
                            script="walkup")
    assert isinstance(cam, ScriptedCamera) and isinstance(aud, NoSource) and aud.latest() is None
    capture_t, bodies, blobs, motion = cam.latest()
    assert capture_t == clock.now and blobs == ()
    with pytest.raises(ValueError, match="walkup"):
        make_sources(make_cfg((128, 32)), (128, 32), clock, script="nosuch")


def test_make_sources_mediapipe_gets_the_config_clock_and_calibration(monkeypatch):
    import arcade.sources.pose_mediapipe as pm

    seen = {}

    class Spy:
        def __init__(self, cfg, size, clock, *, calibration=None):
            seen.update(cfg=cfg, size=size, clock=clock, calibration=calibration)

    monkeypatch.setattr(pm, "MediaPipeCamera", Spy)
    cfg, clock, cal = make_cfg((64, 64), camera="mediapipe"), FakeClock(), Calibration(zone=(0.1, 0.1, 0.9, 0.9))
    cam, aud = make_sources(cfg, (64, 64), clock, calibration=cal)
    assert isinstance(cam, Spy) and isinstance(aud, NoSource)
    assert seen == dict(cfg=cfg, size=(64, 64), clock=clock, calibration=cal)


def test_scripted_camera_stamps_the_runner_clock(font5x7):
    clock = FakeClock(500.0)
    frames = scene(persons=[Person(0.5, id=7)], ticks=2)
    cam = ScriptedCamera(frames, clock)
    runner = Runner(make_cfg((128, 32)), FakeDisplay(), font5x7, NullLobby(), [], clock=clock, sleep=clock.sleep)
    first = runner.sense(cam, NoSource())
    assert first.camera_fresh and first.camera_seq == 1 and [b.id for b in first.bodies] == [7]
    assert first.camera_t == runner.t                     # stamped now on the runner's clock: no age
    clock.sleep(1 / 30)
    second = runner.sense(cam, NoSource())
    assert second.camera_fresh and second.camera_seq == 2
    clock.sleep(1 / 30)
    assert cam.latest() is None and not cam.available     # the script has run out: no camera


def test_walkup_script_shows_the_mirror_then_the_invite_within_5s(font5x7):
    clock = FakeClock()
    cfg = make_cfg((128, 32))
    games = all_games()
    cam, aud = make_sources(cfg, cfg.size, clock, script="walkup")
    runner = Runner(cfg, FakeDisplay(), font5x7, Lobby(games, cfg), games, clock=clock, sleep=clock.sleep,
                    strict=True)
    runner.trace = []
    runner.loop(cam, aud, max_ticks=5 * cfg.fps)
    modes = [s.get("mode") for s in runner.trace]
    assert "mirror" in modes and "invite" in modes, modes
    assert modes.index("mirror") < modes.index("invite")
    assert set(SCRIPTS) == {"walkup"}
