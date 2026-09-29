"""The show's loop (it12 T-main): setup that never exits, the step, run, the CLI; every frame through the governor.

The safety tests are the plan's, as given (docs/superpowers/plans/2026-09-29-it12-show-runs.md, T-main). No test
drives GPIO or a sound device: `make_lights`, `make_buttons` and `AudioCues` are stood in for below.
"""
import ast
import dataclasses
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

import show.main as show_main
from arcade.flash import BUDGET, FlashGovernor, flash_area, square_flashes
from show.audio import FakeAudio
from show.config import Config, load_config
from show.lights import FakeLights
from show.main import PUSH_DARK_S, RESCAN_S, RETRY_S, WATCHDOG_EVERY_S, ShowLoop, config_from, main, parse_args
from show.wall import GovernedDisplay
from tests.show_helpers import HELLO_C, write_entry
from tests.test_wall import FPS, H, W, Recorder, strobe


class Lights(FakeLights):
    """The show's fake lights, counting all_off and close."""

    def __init__(self):
        super().__init__()
        self.offs = 0

    def all_off(self):
        self.offs += 1
        super().all_off()


@pytest.fixture(autouse=True)
def no_devices(monkeypatch):
    monkeypatch.setattr(show_main, "make_lights", lambda *a, **k: Lights())
    monkeypatch.setattr(show_main, "make_buttons", lambda *a, **k: None)
    monkeypatch.setattr(show_main, "AudioCues", lambda *a, **k: FakeAudio())


# -- the plan's safety tests, as given ------------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
FILL = b"\x1b[?25l\x1b[H\x1b[7m" + b" " * (80 * 23 - 1) + b"\x1b[0m"      # the cursor hidden first


class StrobePlayer:                                   # the whole terminal lit and black by turns: 10 Hz at 20 fps
    def __init__(self, entry, term, cfg):
        self.term, self.done, self.crowd, self.k = term, False, False, 0

    def start(self, now, crowd=False):
        self.term.reset(23)

    def stop(self):
        self.done = True

    def tick(self, now):
        self.term.feed(FILL if self.k % 2 == 0 else b"\x1b[?25l\x1b[H\x1b[2J")
        self.k += 1
        return []


def loop_cfg(tmp_path, **kw):
    write_entry(tmp_path / "entries", "a", 1, HELLO_C)
    return Config(backend="fake", entries_dir=tmp_path / "entries", font_path=ROOT / "fonts" / "5x7.bin",
                  audio_dir=tmp_path, fps=20, **kw)


def test_the_loop_holds_a_strobing_entry(tmp_path):
    inner, rendered = Recorder(), []
    loop = ShowLoop(loop_cfg(tmp_path), display=inner, player_factory=StrobePlayer, notify=lambda s: None)
    loop.start(0.0)
    loop.presses.put(1)
    for k in range(1, 101):
        loop.step(k / 20)
        rendered.append(loop.rendered.copy())
    assert flash_area(rendered, fps=20) > 0.3 and flash_area(inner.pushed, fps=20) == 0.0
    assert square_flashes(inner.pushed, fps=20) <= BUDGET and inner.count == loop.wall.governed == 100


def test_every_display_is_wrapped_by_the_governor_at_birth():
    tree = ast.parse((ROOT / "show" / "main.py").read_text())
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    made = [n for n in calls if isinstance(n.func, ast.Name) and n.func.id == "make_display"]
    wraps = [n for n in calls if isinstance(n.func, ast.Name) and n.func.id == "GovernedDisplay"]
    assert len(made) == 1 and any(made[0] in list(ast.walk(w)) for w in wraps)
    pushes = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr == "push"]
    assert pushes and all(ast.unparse(n.value) == "self.wall" for n in pushes)
    assert not [a for a in ast.walk(tree) if isinstance(a, ast.alias) and a.name == "make_display" and a.asname]
    wall = ast.parse((ROOT / "show" / "wall.py").read_text())
    assert len([n for n in ast.walk(wall) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "push"]) == 1                  # _send's display.push, after apply
    assert "_send" not in (ROOT / "show" / "main.py").read_text()
    assert len([n for n in ast.walk(wall) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "_send"]) == 2               # push's (apply's output), repush's (the last governed)
    for path in [*(ROOT / "show").glob("*.py"), ROOT / "tools" / "show_shot.py"]:
        assert path.name in ("main.py", "wall.py") or "make_display" not in path.read_text(), path


def test_startup_failures_keep_the_loop_and_every_frame_goes_through_the_governor(tmp_path):
    cfg = Config(backend="fake", entries_dir=tmp_path / "missing", font_path=tmp_path / "missing.bin",
                 audio_dir=tmp_path, fps=20)
    inner, told = Recorder(), []
    loop = ShowLoop(cfg, display=inner, notify=told.append)
    loop.start(0.0)
    for k in range(1, 41):
        loop.step(k / 20)
    assert loop.show is None and loop.errors and inner.count == loop.wall.governed == 40
    assert inner.pushed[-1].any() and all(np.array_equal(f, inner.pushed[0]) for f in inner.pushed)
    assert "READY=1" in told and "WATCHDOG=1" in told


def test_a_gamma_the_governor_refuses_shows_its_error_governed(tmp_path):
    inner = Recorder()
    loop = ShowLoop(loop_cfg(tmp_path, gamma=-1.0), display=inner, notify=lambda s: None)
    loop.start(0.0)
    for k in range(1, 21):
        loop.step(k / 20)
    assert loop.show is None and any("gamma" in e for e in loop.errors) and loop.wall.governor.gamma == 2.2
    assert inner.count == loop.wall.governed == 20 and loop.wall.governor.fps == 30 and inner.pushed[-1].any()
    assert all(np.array_equal(f, inner.pushed[0]) for f in inner.pushed) and not inner.closed


# -- the plan's safety tests in prose -------------------------------------------------------------------------------

def test_the_loop_s_own_display_is_governed(tmp_path, monkeypatch):
    made = []

    class Made(Recorder):
        def __init__(self):
            super().__init__()
            made.append(self)

    monkeypatch.setattr("show.display.fake.FakeDisplay", Made)
    loop = ShowLoop(loop_cfg(tmp_path), player_factory=StrobePlayer, notify=lambda s: None)
    loop.start(0.0)
    loop.presses.put(1)
    for k in range(1, 101):
        loop.step(k / 20)
    assert len(made) == 1 and made[0].count == loop.wall.governed == 100
    assert flash_area(made[0].pushed, fps=20) == 0.0 and square_flashes(made[0].pushed, fps=20) <= BUDGET


def test_when_no_governor_can_be_built_the_wall_stays_dark(tmp_path, monkeypatch):
    def refuse(*a, **k):
        raise RuntimeError("no governor")

    monkeypatch.setattr("show.wall.FlashGovernor", refuse)
    inner, told = Recorder(), []
    loop = ShowLoop(loop_cfg(tmp_path), display=inner, notify=told.append)
    loop.start(0.0)
    for k in range(1, 200):                                       # to 9.95 s
        loop.step(k / 20)
    assert loop.wall is None and inner.count == 0 and inner.closed and loop.lights.offs == 0
    loop.step(PUSH_DARK_S)
    assert loop.lights.offs >= 1 and all(m == "off" for m in loop.lights.modes.values())
    assert inner.count == 0 and loop.errors and "WATCHDOG=1" in told


# -- the loop --------------------------------------------------------------------------------------------------------

def small_cfg(tmp_path, **kw):
    """The 128x64 PoC's view: a cheap governor for tests that are not about the flash bound."""
    return loop_cfg(tmp_path, width=128, height=64, view="ink", **kw)


def playing_loop(tmp_path, inner=None, **kw):
    loop = ShowLoop(small_cfg(tmp_path), display=inner if inner is not None else Recorder(),
                    player_factory=StrobePlayer, notify=lambda s: None, **kw)
    loop.start(0.0)
    loop.presses.put(1)
    loop.step(0.05)
    assert loop.show.playing
    return loop


def test_parse_args_defaults():
    args = parse_args([])
    assert args.config == Path("show.toml") and args.backend is None
    assert args.play is None and args.capture is False


def test_a_bad_config_falls_back_with_its_error(tmp_path):
    bad = tmp_path / "show.toml"
    bad.write_text('backend = "ddp"\nbrightnes = 0.9\n')
    cfg, error = config_from(parse_args(["--config", str(bad), "--backend", "fake", "--capture"]))
    assert "brightnes" in error and cfg == dataclasses.replace(Config(), backend="fake", capture=True)
    assert config_from(parse_args(["--config", str(tmp_path / "none.toml")]))[1] is None
    inner = Recorder()
    loop = ShowLoop(cfg, display=inner, notify=lambda s: None, config_error=error)
    loop.start(0.0)
    for k in range(1, 11):
        loop.step(k / 20)
    assert loop.show is None and loop.errors[0] == error and inner.count == loop.wall.governed == 10
    assert inner.pushed[-1].any() and inner.brightness == Config().effective_brightness
    loop.step(RETRY_S + 1)
    assert loop.show is None                                      # a bad config is never retried


def show_toml(tmp_path, **extra):
    write_entry(tmp_path / "entries", "quick", 1, HELLO_C)
    text = (f'backend = "fake"\nentries_dir = "{tmp_path / "entries"}"\n'
            f'font_path = "{ROOT / "fonts" / "5x7.bin"}"\naudio_dir = "{tmp_path}"\n')
    text += "".join(f"{k} = {v}\n" for k, v in extra.items())
    (tmp_path / "show.toml").write_text(text)
    return tmp_path / "show.toml"


def run_show(args, timeout):
    """python -m show in a child, killed in any case: (return code, its log)."""
    env = {**os.environ, "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}
    proc = subprocess.Popen([sys.executable, "-m", "show", *args], cwd=ROOT, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    try:
        out, _ = proc.communicate(timeout=timeout)
        return proc.returncode, out.decode(errors="replace")
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()


@pytest.mark.skipif(shutil.which("cc") is None, reason="needs a C compiler")
def test_play_one_entry_headless_and_exit(tmp_path):
    cfg = show_toml(tmp_path, typewriter_cps=100000, dwell=0.1, error_hold=0.1, min_build_seconds=0.1, fps=60)
    rc, out = run_show(["--config", str(cfg), "--play", "quick"], timeout=60)
    assert rc == 0, out
    assert "playing quick" in out


def test_unknown_play_slug_is_an_error(tmp_path):
    assert main(["--config", str(show_toml(tmp_path)), "--play", "nope"]) == 2


def test_python_dash_m_show_runs_main(tmp_path):
    rc, out = run_show(["--config", str(show_toml(tmp_path)), "--play", "nope"], timeout=60)
    assert rc == 2 and "nope" in out, out


def test_a_press_that_raises_returns_to_attract(tmp_path):
    loop = playing_loop(tmp_path)
    player = loop.show.player

    def press(station, now):
        raise RuntimeError("press")

    loop.show.press = press
    loop.presses.put(1)
    loop.step(0.10)
    assert not loop.show.playing and player.done and loop.show.strip(0.10).startswith("PRESS")
    assert loop.wall.governed == 2


def test_a_render_that_raises_repushes_the_last_frame_and_returns_to_attract(tmp_path):
    inner = Recorder()
    loop = playing_loop(tmp_path, inner)
    loop.step(0.10)
    last, player = loop.rendered, loop.show.player

    def render(*a, **k):
        raise RuntimeError("render")

    loop.renderer.render = render
    loop.step(0.15)
    assert loop.rendered is last and np.array_equal(inner.pushed[-1], inner.pushed[-2])
    assert not loop.show.playing and player.done and inner.count == loop.wall.governed == 3


class FailingPushes(Recorder):
    """Pushes numbered in `fail` (counting every call from 1) raise, as a torn push would."""

    def __init__(self, fail):
        super().__init__()
        self.fail, self.calls = set(fail), 0

    def push(self, frame):
        self.calls += 1
        if self.calls in self.fail:
            raise OSError("no carrier")
        super().push(frame)


def test_after_a_failed_push_the_last_governed_frame_goes_again(tmp_path):
    inner = FailingPushes({3})
    loop = playing_loop(tmp_path, inner)                          # call 1
    loop.step(0.10)                                               # call 2
    loop.step(0.15)                                               # call 3 fails: its frame was governed
    governed = loop.wall.governed
    third = loop.rendered.copy()
    loop.step(0.20)                                               # calls 4 (the repush) and 5
    assert inner.count == 4 and governed == 2 and loop.wall.governed == 3
    assert np.array_equal(inner.pushed[2], third) and np.array_equal(inner.pushed[3], loop.rendered)
    loop.step(0.25)
    assert inner.count == 5                                       # one push a step again


def test_a_failing_push_darkens_the_lights_after_10_s_and_relights(tmp_path):
    inner = FailingPushes(range(2, 400))
    loop = playing_loop(tmp_path, inner)
    assert loop.lights.modes[1] == "bright"
    loop.step(1.0)                                                # the first failure
    loop.step(1.0 + PUSH_DARK_S - 0.05)
    assert loop.lights.offs == 0 and loop.lights.modes[1] == "bright"
    loop.step(1.0 + PUSH_DARK_S)
    assert loop.lights.offs == 1 and loop.lights.modes[1] == "off"
    loop.presses.put(1)                                           # the show goes on in the dark
    loop.step(12.0)
    assert loop.lights.modes[1] == "off"
    inner.fail.clear()
    loop.step(13.0)                                               # a good push: relit
    assert loop.lights.modes[1] == "bright" and loop.show.playing


def test_the_watchdog_is_petted_once_a_second(tmp_path, monkeypatch):
    told = []
    loop = ShowLoop(small_cfg(tmp_path), display=Recorder(), notify=lambda s: told.append((s, now)))
    now = 0.0
    loop.start(now)
    for k in range(1, 61):
        now = k / 20
        loop.step(now)
    assert told[0] == ("READY=1", 0.0)
    pets = [t for s, t in told if s == "WATCHDOG=1"]
    gaps = np.diff(pets)
    assert pets[0] == 0.05 and len(pets) == 3                    # the first step, then once a second
    assert gaps.min() >= WATCHDOG_EVERY_S and gaps.max() < WATCHDOG_EVERY_S + 0.05 + 1e-9
    monkeypatch.setattr("show.wall.FlashGovernor", lambda *a, **k: 1 / 0)
    dark = []                                                     # no show and no display: petted all the same
    loop = ShowLoop(small_cfg(tmp_path / "dark"), display=Recorder(), notify=dark.append)
    loop.start(0.0)
    for k in range(1, 41):
        loop.step(k / 20)
    assert loop.wall is None and loop.show is None and dark.count("WATCHDOG=1") == 2


def test_a_fixed_entries_dir_is_picked_up_at_the_next_retry(tmp_path):
    cfg = dataclasses.replace(small_cfg(tmp_path), entries_dir=tmp_path / "later")
    inner = Recorder()
    loop = ShowLoop(cfg, display=inner, notify=lambda s: None)
    loop.start(0.0)
    loop.step(0.05)
    assert loop.show is None and any("later" in e for e in loop.errors)
    shutil.copytree(tmp_path / "entries", tmp_path / "later")
    loop.step(RETRY_S - 0.05)
    assert loop.show is None
    loop.step(RETRY_S)
    assert loop.show is not None and not loop.errors and loop.show.strip(RETRY_S).startswith("PRESS")
    assert inner.count == loop.wall.governed == 3 and not np.array_equal(inner.pushed[1], inner.pushed[2])


def test_rescan_every_30_s_reaches_the_show(tmp_path):
    loop = ShowLoop(small_cfg(tmp_path), display=Recorder(), notify=lambda s: None)
    loop.start(0.0)
    loop.step(0.05)
    write_entry(tmp_path / "entries", "b", 2, HELLO_C)
    loop.step(RESCAN_S - 0.05)
    assert sorted(loop.show.entries) == [1]
    loop.step(RESCAN_S)
    assert sorted(loop.show.entries) == [1, 2]


def test_the_poc_config_pushes_ink_frames(tmp_path):
    poc = load_config(ROOT / "show.poc.toml")
    cfg = dataclasses.replace(poc, backend="fake", entries_dir=loop_cfg(tmp_path).entries_dir,
                              font_path=ROOT / "fonts" / "5x7.bin", audio_dir=tmp_path)
    inner = Recorder()
    loop = ShowLoop(cfg, display=inner, notify=lambda s: None)
    loop.start(0.0)
    for k in range(1, 21):
        loop.step(k / 20)
    assert loop.show is not None and loop.wall.governor.shape == (64, 128, 3)
    assert inner.last.shape == (64, 128, 3) and inner.last[-8:].any() and inner.last[:-8].any()
    assert inner.count == loop.wall.governed == 20


def test_brightness_is_set_once_on_the_device(tmp_path, caplog):
    class Counting(Recorder):
        def __init__(self):
            super().__init__()
            self.levels = []

        def set_brightness(self, level):
            super().set_brightness(level)
            self.levels.append(level)

    inner = Counting()
    loop = ShowLoop(small_cfg(tmp_path, brightness=0.9, brightness_cap=0.4), display=inner, notify=lambda s: None)
    loop.start(0.0)
    for k in range(1, 21):
        loop.step(k / 20)
    assert inner.levels == [0.4] and inner.pushed[-1].max() > 0.4 * 255    # the device dims; the pixels do not
    inner = Counting()
    cfg = dataclasses.replace(small_cfg(tmp_path / "ddp", brightness=0.2), backend="ddp")
    ShowLoop(cfg, display=inner, notify=lambda s: None).start(0.0)
    assert inner.levels == [0.2]
    assert any(r.levelname == "WARNING" and "Falcon Player" in r.getMessage() and "0.20" in r.getMessage()
               for r in caplog.records)


def test_a_clean_close_pushes_two_governed_black_frames():
    inner, reference = Recorder(), FlashGovernor(H, W, 2.2, fps=FPS)
    wall = GovernedDisplay(inner, H, W, fps=FPS)
    for f in strobe(40):
        wall.push(f)
        reference.apply(f)
    black = np.zeros((H, W, 3), np.uint8)
    want = [reference.apply(black).copy(), reference.apply(black).copy()]
    wall.close()
    assert inner.count == 42 and inner.closed
    assert all(np.array_equal(got, w) for got, w in zip(inner.pushed[-2:], want))


def test_run_never_steps_faster_than_fps(tmp_path):
    loop = ShowLoop(small_cfg(tmp_path), display=Recorder(), notify=lambda s: None)
    t, steps = [0.0], []
    loop.clock = lambda: t[0]

    def sleep(s):
        assert s > 0
        t[0] += s

    def step(now):
        steps.append(now)
        if len(steps) == 3:
            t[0] += 0.5                                           # a stalled step
        if len(steps) == 8:
            raise KeyboardInterrupt

    loop.sleep, loop.step = sleep, step
    assert loop.run() == 0
    gaps = np.diff(steps)
    assert len(steps) == 8 and gaps.min() >= 1 / 20 - 1e-9
    assert gaps[2] == pytest.approx(0.5) and gaps[3:] == pytest.approx([0.05] * 4)   # no catch-up after it
    assert loop.wall.display.closed


def test_run_s_finally_survives_a_raising_close(tmp_path):
    class Raising(Recorder):
        def close(self):
            self.closed = True
            raise OSError("close")

    closed = []

    class ClosingLights(Lights):
        def close(self):
            closed.append("lights")
            raise OSError("lights")

    inner = Raising()
    loop = ShowLoop(small_cfg(tmp_path), display=inner, notify=lambda s: None)
    t = [0.0]
    loop.clock, loop.sleep = (lambda: t[0]), (lambda s: t.__setitem__(0, t[0] + s))
    real_start = loop.start

    def start(now):
        real_start(now)
        loop.lights = ClosingLights()
        loop.show.abort = lambda now: 1 / 0

    steps = []

    def step(now):
        steps.append(now)
        if len(steps) == 3:
            raise KeyboardInterrupt

    loop.start, loop.step = start, step
    assert loop.run() == 0
    assert inner.closed and closed == ["lights"] and inner.count == 2      # the two black frames, then close
