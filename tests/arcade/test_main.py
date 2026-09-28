import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

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

        def loop(self, camera, audio, max_ticks=None):
            self.looped = (camera, audio, max_ticks)

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
    camera, audio, max_ticks = built[0].looped
    assert isinstance(camera, ScriptedCamera) and audio.latest() is None and max_ticks == 2 * a["cfg"].fps

    built.clear()
    assert main(["run", "--config", str(config), "--script", "walkup"]) == 0
    assert built[0].looped[2] is None                    # no --seconds: run until stopped


def test_main_passes_the_saved_calibration(tmp_path, monkeypatch):
    from arcade.calibration import save_calibration

    built = []

    class SpyRunner:
        def __init__(self, *args, **kw):
            built.append(kw)

        def loop(self, camera, audio, max_ticks=None):
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


def test_run_seconds_exits_zero_under_dummy_sdl(tmp_path):
    config = _toml(tmp_path, backend="sdl", sdl_scale=4)
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    got = subprocess.run([sys.executable, "-m", "arcade", "run", "--config", str(config), "--seconds", "1",
                          "--script", "walkup"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert got.returncode == 0, got.stdout + got.stderr
    assert "Traceback" not in got.stderr, got.stderr
