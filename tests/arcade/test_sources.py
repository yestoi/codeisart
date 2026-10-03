import pytest

from arcade.attract.lobby import Lobby
from arcade.calibration import Calibration
from arcade.games import all_games
from arcade.headless import NullLobby
from arcade.runner import Runner
from arcade.sensed import CAMERA_INPUTS
from arcade.sources import SCRIPTS, NoSource, ScenarioWriter, make_header, make_sources
from arcade.sources.actors import Person, scene
from arcade.sources.scripted import SCRIPT_INPUTS, ScriptedCamera
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


def _stand_file(path, ticks=3):
    with ScenarioWriter(path, make_header("sensed", fps=30)) as writer:
        for sensed in scene(persons=[Person(0.5, id=3)], ticks=ticks):
            writer.write(sensed)
    return path


def test_make_sources_replay_from_the_flag_and_the_config(tmp_path, monkeypatch):
    import arcade.sources
    from arcade.calibration import save_calibration
    from arcade.sources.replay import ReplayAudio, ReplayCamera

    path, clock, cal = _stand_file(tmp_path / "stand.jsonl.gz"), FakeClock(), Calibration(zone=(0.1, 0.1, 0.9, 0.9))
    cam, aud = make_sources(make_cfg((128, 64)), (128, 64), clock, replay=path, calibration=cal)
    assert isinstance(cam, ReplayCamera) and isinstance(aud, ReplayAudio)
    capture_t, bodies, blobs, motion = cam.latest()
    assert capture_t == clock.now and [b.id for b in bodies] == [3]

    seen = []
    monkeypatch.setattr(arcade.sources, "open_replay", lambda *a: seen.append(a) or ("camera", "audio"))
    assert make_sources(make_cfg((128, 64)), (128, 64), clock, replay=path, calibration=cal) == ("camera", "audio")
    assert seen[-1] == (path, cal, clock)
    # the config: camera "replay" plays cfg.scenario, placed against the saved calibration; a script still wins
    saved = Calibration(zone=(0.2, 0.2, 0.8, 0.8), calibrated=True)
    save_calibration(tmp_path, saved)
    cfg = make_cfg((128, 64), camera="replay", scenario=str(path), data_dir=tmp_path)
    assert make_sources(cfg, (128, 64), clock) == ("camera", "audio")
    assert seen[-1] == (str(path), saved, clock)
    assert isinstance(make_sources(cfg, (128, 64), clock, script="walkup")[0], ScriptedCamera) and len(seen) == 2
    with pytest.raises(ValueError, match="scenario"):
        make_sources(make_cfg((128, 64), camera="replay"), (128, 64), clock)
    with pytest.raises(ValueError, match="script"):
        make_sources(make_cfg((128, 64)), (128, 64), clock, script="walkup", replay=path)
    assert len(seen) == 2


class StatusLobby(NullLobby):
    def set_status(self, camera_ok, mic_ok, inputs, calibrated):
        self.status = (camera_ok, mic_ok, inputs, calibrated)


def test_walkup_provides_pose_only(font5x7):
    # walkup holds no light: its camera claims pose alone, so the lobby offers no blob game on it (C35)
    clock = FakeClock()
    cam, aud = make_sources(make_cfg((128, 64)), (128, 64), clock, script="walkup")
    assert SCRIPT_INPUTS == {"walkup": frozenset({"pose"})} and cam.provides == frozenset({"pose"})
    assert ScriptedCamera(iter(()), clock).provides == CAMERA_INPUTS     # a scripted camera claims every input
    lobby = StatusLobby()
    runner = Runner(make_cfg((128, 64)), FakeDisplay(), font5x7, lobby, [], clock=clock, sleep=clock.sleep)
    runner.sense(cam, aud)
    assert lobby.status[:3] == (True, False, {"pose"})


def test_make_sources_mediapipe_gets_the_config_clock_and_calibration(monkeypatch):
    import arcade.sources.pose_mediapipe as pm

    seen = {}

    class Spy:
        def __init__(self, cfg, size, clock, *, calibration=None):
            seen.update(cfg=cfg, size=size, clock=clock, calibration=calibration)

    monkeypatch.setattr(pm, "PoseCamera", Spy)
    cfg, clock, cal = make_cfg((64, 64), camera="mediapipe"), FakeClock(), Calibration(zone=(0.1, 0.1, 0.9, 0.9))
    cam, aud = make_sources(cfg, (64, 64), clock, calibration=cal)
    assert isinstance(cam, Spy) and isinstance(aud, NoSource)
    assert seen == dict(cfg=cfg, size=(64, 64), clock=clock, calibration=cal)


def test_make_sources_imx500_opens_the_pair_and_hands_it_to_the_pose_camera(monkeypatch):
    import arcade.sources.pose_imx500 as pi
    import arcade.sources.pose_mediapipe as pm

    seen = {}

    class Spy:
        def __init__(self, cfg, size, clock, *, calibration=None, capture=None, detector=None):
            seen.update(cfg=cfg, size=size, clock=clock, calibration=calibration, capture=capture, detector=detector)

    monkeypatch.setattr(pm, "PoseCamera", Spy)
    monkeypatch.setattr(pi, "open_imx500", lambda cfg, size: ("the capture", "the detector"))
    cfg, clock, cal = make_cfg((64, 64), camera="imx500"), FakeClock(), Calibration(zone=(0.1, 0.1, 0.9, 0.9))
    cam, aud = make_sources(cfg, (64, 64), clock, calibration=cal)
    assert isinstance(cam, Spy) and isinstance(aud, NoSource)
    assert seen == dict(cfg=cfg, size=(64, 64), clock=clock, calibration=cal, capture="the capture", detector="the detector")


def test_make_sources_imx500_without_picamera2_is_unavailable_and_says_so(monkeypatch, caplog):
    import sys

    monkeypatch.setitem(sys.modules, "picamera2", None)        # import picamera2 raises ImportError
    cfg = make_cfg((64, 64), camera="imx500")
    cam, aud = make_sources(cfg, (64, 64), FakeClock())
    assert cam.available is False and cam.latest() is None
    assert "imx500 camera unavailable" in caplog.text and "picamera2" in caplog.text
    cam.close()


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
