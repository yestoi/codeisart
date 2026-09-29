"""systemctl stop, the fallback's display, lights.tick, fps (it13 T-main).

SIGTERM raises KeyboardInterrupt once, only inside main(), so run's finally darkens the wall and the lights; a
broken show.toml keeps the wall it names (never brighter than Config()); the lights tick every step; an fps the
governor refuses paces run at FALLBACK_FPS. No test drives GPIO or a sound device, but the systemctl stop test's
child, which keeps the real AudioCues under SDL's dummy drivers.
"""
import dataclasses
import logging
import os
import signal
import subprocess
import sys
import threading
import time

import numpy as np
import pytest

import show.main as show_main
from arcade.flash import FlashGovernor
from show.config import Config
from show.main import FALLBACK_FPS, ShowLoop, Sigterm, config_from, main, parse_args, sigterm_raises
from tests.test_main import FailingPushes, Lights, ROOT, StrobePlayer, no_devices, show_toml, small_cfg  # noqa: F401
from tests.test_wall import Recorder


def stop_self():
    """SIGTERM to this process, once the handler is known to be Sigterm; its KeyboardInterrupt within a second."""
    assert isinstance(signal.getsignal(signal.SIGTERM), Sigterm)
    os.kill(os.getpid(), signal.SIGTERM)
    for _ in range(1000):
        time.sleep(0.001)
    raise AssertionError("SIGTERM raised nothing")


def fake_time(loop):
    t = [0.0]
    loop.clock, loop.sleep = (lambda: t[0]), (lambda s: t.__setitem__(0, t[0] + s))


# -- systemctl stop -------------------------------------------------------------------------------------------------

def test_sigterm_raises_once_then_is_ignored():
    handler = Sigterm()
    with pytest.raises(KeyboardInterrupt):
        handler(signal.SIGTERM, None)
    handler(signal.SIGTERM, None)                                  # the close is under way: only counted
    handler(signal.SIGTERM, None)
    assert handler.seen == 3


def test_sigterm_raises_outside_the_main_thread_installs_nothing(caplog):
    before, inside = signal.getsignal(signal.SIGTERM), []

    def body():
        with sigterm_raises():
            inside.append(signal.getsignal(signal.SIGTERM))

    thread = threading.Thread(target=body)
    thread.start()
    thread.join(5)
    assert inside == [before] and signal.getsignal(signal.SIGTERM) is before
    assert any(r.levelname == "WARNING" and "SIGTERM" in r.getMessage() for r in caplog.records)


class Events(Lights):
    """The show's fake lights, logging all_off, tick and close into a list the wall shares."""

    def __init__(self, events):
        super().__init__()
        self.events = events

    def all_off(self):
        self.events.append("lights off")
        super().all_off()

    def tick(self, now):
        self.events.append("lights tick")
        super().tick(now)

    def close(self):
        self.events.append("lights close")


def test_sigterm_in_a_running_loop_darkens_the_wall_and_the_lights(tmp_path, monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    events = []

    class Wall(Recorder):
        def close(self):
            events.append("wall close")
            super().close()

    monkeypatch.setattr(show_main, "make_lights", lambda *a, **k: Events(events))
    inner = Wall()
    loop = ShowLoop(small_cfg(tmp_path), display=inner, player_factory=StrobePlayer, notify=lambda s: None)
    fake_time(loop)
    real_step, rendered = loop.step, []

    def step(now):
        real_step(now)
        rendered.append(loop.rendered.copy())
        if len(rendered) == 3:
            events.clear()
            stop_self()

    loop.step = step
    loop.presses.put(1)
    before = signal.getsignal(signal.SIGTERM)
    with sigterm_raises():
        assert loop.run() == 0
    assert signal.getsignal(signal.SIGTERM) is before and len(rendered) == 3
    reference, black = FlashGovernor(64, 128, 2.2, fps=20), np.zeros((64, 128, 3), np.uint8)
    for f in rendered:
        reference.apply(f)
    want = [reference.apply(black).copy(), reference.apply(black).copy()]
    assert inner.count == 5 and inner.closed
    assert all(np.array_equal(got, w) for got, w in zip(inner.pushed[-2:], want))
    assert loop.lights.modes and all(m == "off" for m in loop.lights.modes.values())
    assert all(v == (0.0, 0.0) for v in loop.lights.levels.values())
    assert events[-4:] == ["lights off", "lights tick", "lights close", "wall close"]
    assert any(r.levelname == "INFO" and r.getMessage().startswith("closing") for r in caplog.records)


def test_main_logs_the_later_sigterms_after_the_close(tmp_path, monkeypatch, caplog):
    def run(self, play=None):
        try:
            stop_self()
        except KeyboardInterrupt:
            for _ in range(2):                                    # the close is under way: two more, counted
                os.kill(os.getpid(), signal.SIGTERM)
                time.sleep(0.01)
        assert signal.getsignal(signal.SIGTERM).seen == 3
        return 0

    caplog.set_level(logging.INFO)
    monkeypatch.setattr(ShowLoop, "run", run)
    before = signal.getsignal(signal.SIGTERM)
    assert main(["--config", str(show_toml(tmp_path))]) == 0
    assert signal.getsignal(signal.SIGTERM) is before
    assert any("SIGTERM" in r.getMessage() and "3" in r.getMessage() for r in caplog.records)


def test_importing_show_main_installs_no_handler():
    out = subprocess.run([sys.executable, "-c", "import signal, show.main; print(signal.getsignal(signal.SIGTERM) "
                          "is signal.SIG_DFL)"], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert out.stdout.strip() == "True", out.stderr


def test_systemctl_stop_is_a_clean_exit(tmp_path):
    env = {**os.environ, "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy", "PYTHONUNBUFFERED": "1"}
    proc = subprocess.Popen([sys.executable, "-m", "show", "--config", str(show_toml(tmp_path)), "--backend", "fake"],
                            cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    lines, running = [], threading.Event()

    def read():
        for line in proc.stdout:
            lines.append(line)
            if "the show runs at" in line:
                running.set()

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    try:
        assert running.wait(10), "".join(lines)
        proc.send_signal(signal.SIGTERM)
        assert proc.wait(timeout=10) == 0, "".join(lines)
        reader.join(5)
        out = "".join(lines)
        assert "closing" in out and "audio unavailable" not in out, out   # the real AudioCues (SDL's mixer) ran
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        reader.join(5)
        proc.stdout.close()


# -- the fallback's display -----------------------------------------------------------------------------------------

def fallback(tmp_path, text, *argv):
    path = tmp_path / "show.toml"
    path.write_text(text)
    cfg, error = config_from(parse_args(["--config", str(path), *argv]))
    assert error is not None and error.startswith("config: ")
    return cfg


def test_a_broken_show_toml_keeps_its_display_keys(tmp_path):
    cfg = fallback(tmp_path, 'backend = "colorlight"\ncolorlight_iface = "enp3s0"\nwidth = 128\nheight = 64\n'
                             'ddp_host = "10.0.0.2"\nddp_port = 4049\nfps = 0\ngamma = 1.0\n')
    assert (cfg.backend, cfg.colorlight_iface, cfg.width, cfg.height) == ("colorlight", "enp3s0", 128, 64)
    assert (cfg.ddp_host, cfg.ddp_port) == ("10.0.0.2", 4049)
    assert cfg.fps == 20 and cfg.gamma == 2.2                     # never gamma, fps
    assert dataclasses.replace(cfg, backend="sdl", colorlight_iface="eth0", width=512, height=192,
                               ddp_host="127.0.0.1", ddp_port=4048) == Config()
    assert fallback(tmp_path, "brightness = 0.9\nfps = 0\n").brightness == 0.15
    cfg = fallback(tmp_path, "brightness = 0.05\nbrightness_cap = 0.1\nfps = 0\n")
    assert (cfg.brightness, cfg.brightness_cap) == (0.05, 0.1) and cfg.effective_brightness == 0.05
    for bad in ("true", '"dim"', "-0.5", "1.5", "nan", "inf", "-inf", "2"):
        cfg = fallback(tmp_path, f"brightness = {bad}\nbrightness_cap = {bad}\nfps = 0\n")
        assert (cfg.brightness, cfg.brightness_cap) == (0.15, 0.40), bad
    assert fallback(tmp_path, "brightness = 0\nbrightness_cap = 1\nfps = 0\n").effective_brightness == 0.0
    assert fallback(tmp_path, 'backend = "colorlight\nwidth = 128\n') == Config()          # not TOML
    assert fallback(tmp_path, "backend = 3\nwidth = 128.0\nheight = true\nddp_port = \"x\"\nfps = 0\n") == Config()
    cfg = fallback(tmp_path, 'backend = "colorlight"\nfps = 0\n', "--backend", "fake", "--capture")
    assert cfg.backend == "fake" and cfg.capture


# -- lights.tick ----------------------------------------------------------------------------------------------------

class Ticks(Lights):
    def __init__(self):
        super().__init__()
        self.ticks = []

    def tick(self, now):
        self.ticks.append(now)
        super().tick(now)


def test_lights_tick_on_every_step(tmp_path, monkeypatch):
    monkeypatch.setattr(show_main, "make_lights", lambda *a, **k: Ticks())
    times = [k / 20 for k in range(1, 41)]
    no_show = ShowLoop(dataclasses.replace(small_cfg(tmp_path / "a"), entries_dir=tmp_path / "none"),
                       display=Recorder(), notify=lambda s: None)
    failing = ShowLoop(small_cfg(tmp_path / "b"), display=FailingPushes(range(1, 100)), notify=lambda s: None)
    raising = ShowLoop(small_cfg(tmp_path / "c"), display=Recorder(), notify=lambda s: None)
    for loop in (no_show, failing, raising):
        loop.start(0.0)
    raising.show.tick = lambda now: 1 / 0
    for loop in (no_show, failing, raising):
        for now in times:
            loop.step(now)
    assert no_show.show is None and failing.wall.display.count == 0 and raising.wall.governed == 40
    assert no_show.lights.ticks == failing.lights.ticks == raising.lights.ticks == times


# -- fps ------------------------------------------------------------------------------------------------------------

def test_an_fps_the_governor_refuses_never_divides_by_zero(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    for k, fps in enumerate((0, -1, 1, 2.5, True)):
        inner = Recorder()
        loop = ShowLoop(dataclasses.replace(small_cfg(tmp_path / str(k)), fps=fps), display=inner,
                        notify=lambda s: None)
        fake_time(loop)
        real_step, steps = loop.step, []

        def step(now):
            real_step(now)
            steps.append(now)
            if len(steps) == 5:
                raise KeyboardInterrupt

        loop.step = step
        assert loop.run() == 0, fps
        assert len(steps) == 5 and np.diff(steps).min() >= 1 / FALLBACK_FPS - 1e-9, fps
        assert any("fps" in e and repr(fps) in e for e in loop.errors) and loop.show is None, (fps, loop.errors)
        assert inner.count == 7 and inner.closed and inner.pushed[4].any(), fps     # 5 static frames, 2 black
    assert any(r.levelname == "ERROR" and str(FALLBACK_FPS) in r.getMessage() and "fps" in r.getMessage()
               for r in caplog.records)
    assert any(r.levelname == "INFO" and r.getMessage() == f"the show runs at {FALLBACK_FPS} fps"
               for r in caplog.records)
