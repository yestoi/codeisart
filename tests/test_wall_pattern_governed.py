"""The test pattern through the flash governor (it13 T-pattern): every frame to the wall governed, the fps and
gamma refusals before the display, grid and panels, and --config."""
import ast
from pathlib import Path

import numpy as np
import pytest

from arcade.flash import BUDGET, flash_area, square_flashes
from show.font import Font
from show.renderer import draw_text
from show.wall import GovernedDisplay
from tests.test_main import FailingPushes
from tests.test_wall import Recorder
from tools import wall_pattern as wp

ROOT = Path(__file__).resolve().parents[1]
WHITE = (wp.LEVEL,) * 3


# -- the plan's safety tests, EXACT ------------------------------------------------------------------------------------

def strobe(width, height, t):                        # the whole wall lit and black by turns: 10 Hz at 20 fps
    lit = round(t * 20) % 2 == 0
    return np.full((height, width, 3), (0, wp.LEVEL, 0) if lit else (0, 0, 0), np.uint8)


def test_every_frame_the_pattern_tool_sends_is_governed(monkeypatch):
    """the plan's, as given"""
    monkeypatch.setitem(wp.PATTERNS, "strobe", strobe)
    monkeypatch.setitem(wp.LOOK_FOR, "strobe", "a strobe the governor holds")
    inner, clock = Recorder(), iter(np.arange(0.0, 100.0, 0.05))
    assert wp.run("strobe", inner, 128, 64, brightness=0.1, seconds=5.0, fps=20, clock=lambda: next(clock),
                  sleep=lambda s: None, out=[].append) == 0
    raw = [strobe(128, 64, k * 0.05) for k in range(1, len(inner.pushed) - 1)]
    assert len(inner.pushed) == 99 + 2 and flash_area(raw, fps=20) > 0.5
    assert flash_area(inner.pushed, fps=20) == 0.0 and square_flashes(inner.pushed, fps=20) <= BUDGET
    assert inner.closed


def test_a_failed_push_ends_with_the_counted_frame_then_governed_black():
    """the plan's, as given"""
    inner, clock = FailingPushes({3}), iter(np.arange(0.0, 100.0, 0.05))
    assert wp.run("rgb", inner, 128, 64, brightness=0.1, seconds=5.0, fps=20, clock=lambda: next(clock),
                  sleep=lambda s: None, out=[].append) == 1
    assert inner.closed and inner.count == 5 and np.array_equal(inner.pushed[2], wp.rgb(128, 64, 0.0))
    assert not inner.pushed[-1].any() and not inner.pushed[-2].any()


def test_the_pattern_tool_reaches_the_display_only_through_the_governor():
    """the plan's, as given"""
    tree = ast.parse((ROOT / "tools" / "wall_pattern.py").read_text())
    attrs = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute)]  # every use, not only calls (no aliases)
    for name in ("push", "set_brightness", "close"):
        used = [n for n in attrs if n.attr == name]
        assert used and all(ast.unparse(n.value) == "wall" for n in used), name
    assert not [n for n in attrs if n.attr in ("_send", "display")]
    wraps = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == "GovernedDisplay"]
    assert len(wraps) == 1 and ast.unparse(wraps[0].args[0]) == "display"


# -- the rest ---------------------------------------------------------------------------------------------------------

class Levels(Recorder):
    """A Recorder that keeps every brightness level with the clock's time when it was set."""

    def __init__(self, now):
        super().__init__()
        self.now, self.levels = now, []

    def set_brightness(self, level):
        super().set_brightness(level)
        self.levels.append((self.now[0], level))


def ticking(step):
    """A clock that steps by `step` a call, and the list holding its last reading."""
    now, it = [0.0], iter(np.arange(0.0, 1000.0, step))

    def clock():
        now[0] = float(next(it))
        return now[0]
    return clock, now


def run(pattern, display, **kw):
    kw.setdefault("sleep", lambda s: None)
    kw.setdefault("out", [].append)
    return wp.run(pattern, display, 128, 64, **kw)


def test_the_governor_fps_is_never_under_the_push_rate():
    for fps, want in zip((1, 2.0, 7.5, 20.0), (2, 2, 8, 20)):
        got = wp.governor_fps(fps)
        assert got == want and isinstance(got, int), fps
    assert wp.MAX_FPS == 60.0


class Governed(GovernedDisplay):
    made: list = []

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        Governed.made.append(self)


def test_run_governs_at_the_governor_fps_with_the_gamma_asked(monkeypatch):
    monkeypatch.setattr(wp, "GovernedDisplay", Governed)
    monkeypatch.setattr(Governed, "made", [])
    clock = iter(np.arange(0.0, 100.0, 0.5))
    assert run("grid", Recorder(), brightness=0.1, seconds=1.0, fps=7.5, gamma=1.0,
               clock=lambda: next(clock)) == 0
    (wall,) = Governed.made
    assert wall.governor.fps == 8 and wall.governor.gamma == 1.0 and wall.governor.shape == (64, 128, 3)


@pytest.mark.parametrize("fps,gamma", [(0, 2.2), (-1, 2.2), (float("nan"), 2.2), (float("inf"), 2.2), (61, 2.2),
                                       (20, 0.22), (20, 22.0)])
def test_run_refuses_a_bad_fps_or_gamma_without_touching_the_display(fps, gamma):
    inner, said = Recorder(), []
    assert run("rgb", inner, brightness=0.1, seconds=1.0, fps=fps, gamma=gamma, out=said.append) == 2
    assert inner.count == 0 and inner.pushed == [] and inner.brightness == 1.0 and not inner.closed
    assert said and ("fps" in said[-1] or "gamma" in said[-1])


@pytest.mark.parametrize("brightness,cap", [(0.31, 0.3), (0.41, 1.0), (0.1, 0.05)])
def test_run_refuses_a_brightness_over_the_cap_asked_or_the_tool_s(brightness, cap):
    inner, said = Recorder(), []
    assert run("rgb", inner, brightness=brightness, cap=cap, seconds=1.0, out=said.append) == 2
    assert inner.count == 0 and inner.brightness == 1.0 and not inner.closed
    assert f"{min(cap, wp.CAP):g}" in said[-1]


def test_steps_changes_the_device_brightness_at_most_every_2_s():
    assert wp.STEP_SECONDS == 2.0
    clock, now = ticking(0.05)
    inner = Levels(now)
    assert run("steps", inner, brightness=0.3, cap=0.3, seconds=20.0, fps=20, clock=clock) == 0
    times = [t for t, _ in inner.levels]
    assert len(inner.levels) == 10                              # the first level, then a change every 2 s
    assert all(b - a >= wp.STEP_SECONDS - 1e-9 for a, b in zip(times, times[1:]))
    assert max(level for _, level in inner.levels) <= 0.3 <= wp.CAP
    assert {level for _, level in inner.levels} == {0.3 * s for s in wp.STEPS}


def test_an_os_error_from_a_push_is_said_then_the_wall_closes():
    inner, said = FailingPushes({2}), []
    clock = iter(np.arange(0.0, 100.0, 0.05))
    assert run("panels", inner, brightness=0.1, seconds=5.0, fps=20, clock=lambda: next(clock),
               out=said.append) == 1
    assert "no carrier" in said[-1] and inner.closed and not inner.pushed[-1].any()


@pytest.mark.parametrize("width,height", [(128, 64), (512, 192)])
def test_grid_lines_every_8_pixels(width, height):
    g = wp.grid(width, height, 0.0)
    assert g.shape == (height, width, 3) and g.dtype == np.uint8
    lit = (g == WHITE).all(axis=2)
    assert lit[::8].all() and lit[:, ::8].all()
    rest = np.ones((height, width), bool)
    rest[::8], rest[:, ::8] = False, False
    assert not g[rest].any()                                    # nothing else lit: g[4, 4] among them
    assert wp.LOOK_FOR["grid"] and "grid" in wp.PATTERNS


@pytest.mark.parametrize("width,height", [(128, 64), (128, 32), (512, 192)])
def test_border_is_one_pixel_along_all_four_edges(width, height):
    b = wp.border(width, height, 0.0)
    assert b.shape == (height, width, 3) and b.dtype == np.uint8
    lit = (b == WHITE).all(axis=2)
    assert lit[0].all() and lit[-1].all() and lit[:, 0].all() and lit[:, -1].all()   # the last row and column too
    assert not b[1:-1, 1:-1].any()                              # nothing inside the frame
    assert wp.LOOK_FOR["border"] and "border" in wp.PATTERNS


@pytest.mark.parametrize("width,height,n", [(512, 192, 48), (128, 64, 4)])
def test_panels_labels_every_panel(width, height, n):
    f, font, labelled = wp.panels(width, height, 0.0), Font.load(wp.FONT_PATH), 0
    for r in range(height // wp.PANEL_H):
        for c in range(width // wp.PANEL_W):
            y, x = r * wp.PANEL_H, c * wp.PANEL_W
            want = np.zeros((wp.PANEL_H, wp.PANEL_W, 3), np.uint8)
            draw_text(want, 2, 2, f"{r},{c}", font, WHITE)
            assert want.any() and np.array_equal(f[y:y + wp.PANEL_H, x:x + wp.PANEL_W], want), (r, c)
            labelled += 1
    assert labelled == n and wp.LOOK_FOR["panels"] and "panels" in wp.PATTERNS


def test_there_is_no_white_pattern():
    assert "white" not in wp.PATTERNS and "white" not in wp.LOOK_FOR     # Q64


# -- main --------------------------------------------------------------------------------------------------------------

def spies(monkeypatch):
    """make_display and run replaced: what each was given."""
    made, ran = [], []

    def fake_make_display(cfg, on_key=None):
        made.append(cfg)
        return Recorder()

    def fake_run(pattern, display, width, height, **kw):
        ran.append(dict(pattern=pattern, width=width, height=height, **kw))
        return 0

    monkeypatch.setattr(wp, "make_display", fake_make_display)
    monkeypatch.setattr(wp, "run", fake_run)
    return made, ran


def write_config(tmp_path, text):
    path = tmp_path / "show.toml"
    path.write_text(text)
    return str(path)


CONFIG = ('backend = "ddp"\nwidth = 512\nheight = 192\ngamma = 1.0\nbrightness_cap = 0.3\n'
          'ddp_host = "10.0.0.9"\nddp_port = 4049\ncolorlight_iface = "enp3s0"\n')


def test_config_sets_the_wall_and_a_flag_wins(monkeypatch, tmp_path):
    made, ran = spies(monkeypatch)
    path = write_config(tmp_path, CONFIG)
    assert wp.main(["rgb", "--config", path]) == 0
    cfg = made[-1]
    assert (cfg.backend, cfg.width, cfg.height, cfg.iface, cfg.ddp_host, cfg.ddp_port) == \
        ("ddp", 512, 192, "enp3s0", "10.0.0.9", 4049)
    assert ran[-1]["gamma"] == 1.0 and ran[-1]["cap"] == 0.3 and (ran[-1]["width"], ran[-1]["height"]) == (512, 192)
    assert wp.main(["rgb", "--config", path, "--width", "128", "--backend", "sdl", "--gamma", "2.2"]) == 0
    assert (made[-1].backend, made[-1].width, made[-1].height) == ("sdl", 128, 192) and ran[-1]["width"] == 128
    assert ran[-1]["gamma"] == 2.2
    count = len(made)
    assert wp.main(["rgb", "--config", path, "--brightness", "0.35"]) == 2
    assert len(made) == count


def test_the_cap_is_never_over_the_tool_s(monkeypatch, tmp_path):
    made, ran = spies(monkeypatch)
    path = write_config(tmp_path, "brightness_cap = 1.0\nbackend = \"colorlight\"\n")
    assert wp.main(["rgb", "--config", path]) == 0 and ran[-1]["cap"] == wp.CAP
    assert wp.main(["rgb", "--config", path, "--brightness", "0.5"]) == 2 and len(made) == 1


def test_a_backend_the_tool_has_no_choice_for_is_refused(monkeypatch, tmp_path, capsys):
    made, ran = spies(monkeypatch)
    path = write_config(tmp_path, 'backend = "fake"\n')
    assert wp.main(["rgb", "--config", path]) == 2 and made == [] and ran == []
    assert "fake" in capsys.readouterr().out
    assert wp.main(["rgb", "--config", path, "--backend", "ddp"]) == 0 and made[-1].backend == "ddp"


def test_without_a_config_the_defaults_are_today_s(monkeypatch):
    made, ran = spies(monkeypatch)
    assert wp.main(["rgb"]) == 0
    cfg = made[-1]
    assert (cfg.backend, cfg.width, cfg.height, cfg.iface, cfg.sdl_scale, cfg.ddp_host, cfg.ddp_port,
            cfg.brightness) == ("colorlight", 128, 64, "eth0", 8, "127.0.0.1", 4048, 0.1)
    assert ran[-1]["gamma"] == 2.2 and ran[-1]["cap"] == wp.CAP and ran[-1]["fps"] == 20.0


def test_png_takes_the_config_size(tmp_path):
    from PIL import Image

    path = write_config(tmp_path, CONFIG)
    out = tmp_path / "grid.png"
    assert wp.main(["grid", "--config", path, "--png", str(out)]) == 0
    with Image.open(out) as im:
        assert im.size == (512 * 8, 192 * 8)
    assert wp.main(["grid", "--config", path, "--height", "64", "--png", str(out)]) == 0
    with Image.open(out) as im:
        assert im.size == (512 * 8, 64 * 8)


@pytest.mark.parametrize("flags", [["--fps", "0"], ["--gamma", "22.0"], ["--fps", "nan"], ["--brightness", "0.5"]])
def test_main_refuses_before_making_the_display(monkeypatch, capsys, flags):
    made, ran = spies(monkeypatch)
    assert wp.main(["rgb", *flags]) == 2
    assert made == [] and ran == [] and "wall_pattern:" in capsys.readouterr().out


def test_a_config_that_does_not_load_is_refused(monkeypatch, tmp_path, capsys):
    made, ran = spies(monkeypatch)
    path = write_config(tmp_path, "gamma = 22.0\n")
    assert wp.main(["rgb", "--config", path]) == 2 and made == []
    assert "gamma" in capsys.readouterr().out
