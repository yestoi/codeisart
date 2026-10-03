import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

import arcade.main
from arcade.attract.lobby import Lobby
from arcade.calibration import Calibration
from arcade.main import build_display, main
from arcade.preview import PreviewDisplay
from arcade.scores import Scores, SessionLog
from arcade.sources.scripted import ScriptedCamera
from show.display.fake import FakeDisplay
from show.display.sdl import SDLDisplay
from tests.arcade.helpers import make_cfg

ROOT = Path(__file__).resolve().parents[2]


def test_build_display_wraps_sdl_in_preview_and_passes_fake_through():
    assert isinstance(build_display(make_cfg((64, 64))), FakeDisplay)
    d = build_display(make_cfg((64, 64), backend="sdl", sdl_scale=2, look="plain", gamma=1.8))
    try:
        assert isinstance(d, PreviewDisplay) and isinstance(d.inner, SDLDisplay)
        assert d.inner.size == (128, 128)                 # the window is w*scale by h*scale at scale 1
        assert (d.mode, d.scale, d.gamma) == ("plain", 2, 1.8)
    finally:
        d.close()


def _toml(tmp_path: Path, **over) -> Path:
    fields = {"backend": "fake", "data_dir": str(tmp_path / "data"), "font_path": str(ROOT / "fonts" / "5x7.bin"),
              **over}
    path = tmp_path / "arcade.toml"
    path.write_text("".join(f"{k} = {v!r}\n".replace("'", '"') for k, v in fields.items()))
    (tmp_path / "data").mkdir(exist_ok=True)
    return path


def test_main_builds_runner_with_the_small_lobby_and_games_once(tmp_path, monkeypatch):
    built, calls = [], []
    real_all_games = arcade.main.all_games

    def counting_all_games():
        calls.append(1)
        return real_all_games()

    class SpyRunner:
        def __init__(self, cfg, display, font, lobby, games, **kw):
            self.args = dict(cfg=cfg, display=display, font=font, lobby=lobby, games=games, **kw)
            built.append(self)

        def loop(self, camera, audio, max_ticks=None, until=None):
            self.looped = (camera, audio, max_ticks, until)

    monkeypatch.setattr(arcade.main, "all_games", counting_all_games)
    monkeypatch.setattr(arcade.main, "Runner", SpyRunner)
    config = _toml(tmp_path)
    assert main(["--config", str(config), "--script", "walkup", "--seconds", "2"]) == 0   # run is the default
    assert len(calls) == 1 and len(built) == 1
    a = built[0].args
    assert isinstance(a["lobby"], Lobby) and a["lobby"].games == {g.info.name: g for g in a["games"]}
    assert isinstance(a["display"], FakeDisplay) and a["display"].closed
    assert isinstance(a["scores"], Scores) and a["scores"].path == tmp_path / "data" / "scores.json"
    assert isinstance(a["sessions"], SessionLog) and a["sessions"].path == tmp_path / "data" / "sessions.jsonl"
    assert isinstance(a["calibration"], Calibration)
    assert a["local_clock"] == datetime.now and a["lux"] is None
    assert "director" not in a
    camera, audio, max_ticks, until = built[0].looped
    assert isinstance(camera, ScriptedCamera) and audio.latest() is None and max_ticks == 2 * a["cfg"].fps

    built.clear()
    assert main(["run", "--config", str(config), "--script", "walkup"]) == 0
    assert built[0].looped[2] is None and until is None    # no --seconds: run until stopped; no --leave-after


def test_main_passes_the_saved_calibration(tmp_path, monkeypatch):
    from arcade.calibration import save_calibration

    built = []

    class SpyRunner:
        def __init__(self, *args, **kw):
            built.append(kw)

        def loop(self, camera, audio, max_ticks=None, until=None):
            pass

    monkeypatch.setattr(arcade.main, "Runner", SpyRunner)
    config = _toml(tmp_path)
    save_calibration(tmp_path / "data", Calibration(zone=(0.1, 0.2, 0.9, 0.8), calibrated=True))
    assert main(["run", "--config", str(config), "--script", "walkup", "--seconds", "0"]) == 0
    assert built[0]["calibration"].zone == (0.1, 0.2, 0.9, 0.8) and built[0]["calibration"].calibrated


def test_run_opens_a_128x64_wall_by_default(monkeypatch, caplog):
    # Q32, Q33: four 64x32 panels, 2 x 2. No --config: the repo's arcade.toml, read from the repo root.
    sizes = []

    def spy_build_display(cfg):
        sizes.append(cfg.size)
        return FakeDisplay()

    monkeypatch.chdir(ROOT)
    monkeypatch.setattr(arcade.main, "build_display", spy_build_display)
    caplog.set_level(logging.INFO, logger="arcade.main")
    assert main(["run", "--seconds", "0.2", "--script", "walkup"]) == 0
    assert sizes == [(128, 64)]
    started = [r.getMessage() for r in caplog.records if r.name == "arcade.main" and r.levelno == logging.INFO]
    assert started == ["wall 128x64, backend sdl"], started


def test_main_dispatches_the_new_commands(tmp_path, monkeypatch):
    # calibrate, record and stats live in their own modules, imported only when their command runs.
    import arcade.calibrate
    import arcade.sources.record
    import arcade.stats

    seen = []
    for module in (arcade.calibrate, arcade.sources.record, arcade.stats):
        monkeypatch.setattr(module, "main", lambda args, name=module.__name__: seen.append((name, args)) or 0)
    config, out, sessions = str(_toml(tmp_path)), str(tmp_path / "door.jsonl.gz"), str(tmp_path / "s.jsonl")
    assert main(["calibrate", "--config", config]) == 0
    assert main(["record", "--config", config, "--script", "door-point", "--i-have-consent", "--raw",
                 "--with-motion", "--out", out]) == 0
    assert main(["stats", "--config", config, "--sessions", sessions]) == 0
    assert [name for name, _ in seen] == ["arcade.calibrate", "arcade.sources.record", "arcade.stats"]
    cal, rec, stats = (args for _, args in seen)
    assert (cal.command, cal.config) == ("calibrate", config)
    assert (rec.command, rec.config, rec.script, rec.i_have_consent, rec.raw, rec.with_motion, rec.out) == (
        "record", config, "door-point", True, True, True, out)
    assert (stats.command, stats.config, stats.sessions) == ("stats", config, sessions)

    seen.clear()
    assert main(["record", "--script", "empty-room"]) == 0 and main(["stats"]) == 0
    rec, stats = (args for _, args in seen)
    assert (rec.config, rec.i_have_consent, rec.raw, rec.with_motion, rec.out) == ("arcade.toml", False, False,
                                                                                   False, None)
    assert (stats.config, stats.sessions) == ("arcade.toml", None)
    with pytest.raises(SystemExit):
        main(["record", "--script", "no-such-script", "--i-have-consent"])


def _actors_file(path: Path, inputs=None) -> Path:
    from arcade.sources.actors import Person, scene
    from arcade.sources.scenario import ScenarioWriter, make_header

    with ScenarioWriter(path, make_header("sensed", fps=30, inputs=inputs)) as writer:
        for sensed in scene(persons=[Person(0.5, id=4)], ticks=30):
            writer.write(sensed)
    return path


def test_run_replay_plays_a_scenario_file(tmp_path, monkeypatch):
    from arcade.runner import Runner
    from arcade.sources.replay import ReplayCamera

    path = _actors_file(tmp_path / "stand.jsonl.gz", inputs={"pose"})
    looped, real_loop = [], Runner.loop

    def spy_loop(self, camera, audio, max_ticks=None, until=None):
        looped.append((camera, max_ticks))
        return real_loop(self, camera, audio, max_ticks=max_ticks, until=until)

    monkeypatch.setattr(Runner, "loop", spy_loop)
    config = str(_toml(tmp_path))
    assert main(["run", "--config", config, "--replay", str(path), "--seconds", "0.2"]) == 0
    (camera, max_ticks), = looped
    assert isinstance(camera, ReplayCamera) and camera.provides == frozenset({"pose"}) and max_ticks == 6
    with pytest.raises(SystemExit):                        # a script and a replay are exclusive
        main(["run", "--config", config, "--replay", str(path), "--script", "walkup"])


def test_run_require_exits_nonzero_without_camera(tmp_path, monkeypatch, capsys):
    built, opened = [], []

    class SpyRunner:
        def __init__(self, *args, **kw):
            built.append(kw)

        def loop(self, camera, audio, max_ticks=None, until=None):
            pass

    real_make_sources = arcade.main.make_sources
    monkeypatch.setattr(arcade.main, "make_sources", lambda *a, **kw: opened.append(a) or real_make_sources(*a, **kw))
    monkeypatch.setattr(arcade.main, "Runner", SpyRunner)
    monkeypatch.setattr(arcade.main, "probe_camera", lambda timeout, index=0: (False, f"device {index}: no frames"))
    config = str(_toml(tmp_path))
    assert main(["run", "--config", config, "--script", "walkup", "--require", "camera"]) == 1
    assert built == [] and opened == []                   # the doctor runs first: no source opened, no runner
    assert "camera  UNAVAILABLE  device 0: no frames" in capsys.readouterr().out

    monkeypatch.setattr(arcade.main, "probe_camera", lambda timeout, index=0: (True, f"device {index}: 640x480"))
    assert main(["run", "--config", config, "--script", "walkup", "--require", "camera", "--seconds", "0"]) == 0
    assert len(built) == 1 and len(opened) == 1
    assert main(["run", "--config", config, "--script", "walkup", "--seconds", "0"]) == 0   # no --require: no doctor
    assert len(built) == 2


def test_run_seconds_exits_zero_under_dummy_sdl(tmp_path):
    config = _toml(tmp_path, backend="sdl", sdl_scale=4)
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    got = subprocess.run([sys.executable, "-m", "arcade", "run", "--config", str(config), "--seconds", "1",
                          "--script", "walkup"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert got.returncode == 0, got.stdout + got.stderr
    assert "Traceback" not in got.stderr, got.stderr


def test_run_game_offers_only_that_game_and_refuses_an_unknown_one(tmp_path, monkeypatch, capsys):
    built, opened = [], []

    class SpyRunner:
        def __init__(self, cfg, display, font, lobby, games, **kw):
            built.append((lobby, games))

        def loop(self, camera, audio, max_ticks=None, until=None):
            pass

    real_make_sources = arcade.main.make_sources
    monkeypatch.setattr(arcade.main, "make_sources", lambda *a, **kw: opened.append(a) or real_make_sources(*a, **kw))
    monkeypatch.setattr(arcade.main, "Runner", SpyRunner)
    config = str(_toml(tmp_path))
    assert main(["run", "--config", config, "--script", "walkup", "--seconds", "0", "--game", "pong"]) == 0
    lobby, games = built[0]
    assert [g.info.name for g in games] == ["pong"] and list(lobby.games) == ["pong"]

    assert main(["run", "--config", config, "--script", "walkup", "--seconds", "0", "--game", "tetris"]) == 2
    assert len(built) == 1 and len(opened) == 1               # refused before a source or a runner
    out = capsys.readouterr().out
    assert "unknown game 'tetris'" in out and "copyme, pong" in out


def test_leave_after_is_parsed_and_off_by_default():
    from arcade.main import build_parser
    assert build_parser().parse_args(["run"]).leave_after is None
    assert build_parser().parse_args(["run", "--game", "freeze", "--leave-after", "5"]).leave_after == 5.0


def test_run_leave_after_hands_the_runner_its_leave(tmp_path, monkeypatch):
    """--game NAME --leave-after S: the loop's until is Runner.left(S); without the flag there is none."""
    from arcade.runner import Runner
    seen = []

    def spy_loop(self, camera, audio, max_ticks=None, until=None):
        seen.append((self, until))

    monkeypatch.setattr(Runner, "loop", spy_loop)
    config = str(_toml(tmp_path))
    assert main(["run", "--config", config, "--script", "walkup", "--game", "jump", "--leave-after", "5"]) == 0
    runner, until = seen[-1]
    assert callable(until) and until() is False, "nothing played yet: the run stays"
    runner.ended, runner.t = 1, 100.0                      # a round over, the zone empty since the start
    assert until() is True
    assert main(["run", "--config", config, "--script", "walkup", "--game", "jump"]) == 0
    assert seen[-1][1] is None
