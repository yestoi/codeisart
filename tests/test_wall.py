"""The governed wall (it12 T-main, Q50): every frame the show pushes passes arcade.flash.FlashGovernor first.

The safety tests are the plan's, as given (docs/superpowers/plans/2026-09-29-it12-show-runs.md, T-main). The
legibility tests hold the show's own frames to the bounds the plan writer's probe measured
(it12-plan/probe_fixed_text.py): a share is the largest share of one frame's pixels that differ from the input.
"""
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from arcade.flash import BUDGET, FlashGovernor, flash_area, square_flashes
from show.attract import Attract
from show.config import Config
from show.display.fake import FakeDisplay
from show.entries import load_entry
from show.font import Font
from show.main import BLINK_HZ, error_frame
from show.renderer import renderer_for
from show.state import ATTRACT_STRIP
from show.terminal import Terminal
from show.wall import GovernedDisplay
from tests.show_helpers import write_entry

# -- the plan's safety test, as given -------------------------------------------------------------------------------

H, W, FPS = 192, 512, 20


class Recorder(FakeDisplay):                          # every pushed frame kept
    def __init__(self):
        super().__init__()
        self.pushed = []

    def push(self, frame):
        super().push(frame)
        self.pushed.append(frame.copy())


def strobe(n, period=1):
    on, off = np.full((H, W, 3), (51, 255, 51), np.uint8), np.zeros((H, W, 3), np.uint8)
    return [on if (k // period) % 2 == 0 else off for k in range(n)]


def test_a_10_hz_full_screen_strobe_is_held_to_the_budget():
    inner = Recorder()
    wall, frames = GovernedDisplay(inner, H, W, fps=FPS, gamma=2.2), strobe(100)
    for f in frames:
        wall.push(f)
    assert flash_area(frames, fps=FPS) > 0.5 and flash_area(inner.pushed, fps=FPS) == 0.0
    assert square_flashes(inner.pushed, fps=FPS) <= BUDGET
    assert wall.governor.held_ticks > 0 and wall.governed == inner.count == 100


# -- the plan's safety test in prose ----------------------------------------------------------------------------------

def test_the_display_gets_exactly_the_governed_frame():
    inner, reference = Recorder(), FlashGovernor(H, W, 2.2, fps=FPS)
    wall = GovernedDisplay(inner, H, W, fps=FPS, gamma=2.2)
    for k, f in enumerate(strobe(40)):
        out = wall.push(f)
        want = reference.apply(f)
        assert np.array_equal(inner.pushed[-1], want) and np.array_equal(out, want), k
    assert wall.governed == inner.count == 40 and wall.governor.held_ticks == reference.held_ticks > 0
    with pytest.raises(ValueError):
        wall.push(np.zeros((64, 128, 3), np.uint8))
    assert inner.count == wall.governed == 40                     # the odd frame reached no display
    for gamma in (0.22, 22.0):
        with pytest.raises(ValueError, match="gamma"):
            GovernedDisplay(Recorder(), H, W, fps=FPS, gamma=gamma)


# -- the wall's own rules ---------------------------------------------------------------------------------------------

def test_repush_sends_the_last_governed_frame_without_governing():
    inner = Recorder()
    wall = GovernedDisplay(inner, H, W, fps=FPS)
    wall.repush()                                                 # nothing governed yet: nothing sent
    assert inner.count == 0
    for f in strobe(30):
        last = wall.push(f)
    held = wall.governor.held_ticks
    wall.repush()
    assert inner.count == 31 and wall.governed == 30 and wall.governor.held_ticks == held > 0
    assert np.array_equal(inner.pushed[-1], last)


def test_the_wall_never_closes_the_display_it_is_given_when_it_refuses():
    inner = Recorder()
    with pytest.raises(ValueError):
        GovernedDisplay(inner, H, W, fps=1)                       # the governor's own check
    with pytest.raises(ValueError):
        GovernedDisplay(inner, H, W, gamma=True)
    assert not inner.closed and inner.count == 0


def test_brightness_goes_to_the_device():
    inner = Recorder()
    GovernedDisplay(inner, H, W).set_brightness(0.15)
    assert inner.brightness == 0.15 and inner.count == 0


# -- legibility: the show's frames through the wall -------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
FONT = Font.load(ROOT / "fonts" / "5x7.bin")
TEXT, INK = Config(fps=FPS), Config(width=128, height=64, view="ink", fps=FPS)
PLAYING = "NOW: hello by Trey, 2026, Not A.I. | NEXT: -"      # the probe's strip
OFF = b"\x1b[?25l\x1b[H\x1b[2J"                                # StrobePlayer's black screen, the cursor hidden


def govern(cfgs, term, n, feed=None, strip=PLAYING, cursor=True):
    """n frames at FPS of term, fed by feed(k) before each, rendered for each config as the loop renders them (the
    cursor blinks at BLINK_HZ) and pushed through a wall of its own. Per config: the wall, the largest share of a
    frame's pixels the governor changed, and the frames the display got."""
    runs = [(renderer_for(c, FONT), GovernedDisplay(Recorder(), c.height, c.width, fps=FPS)) for c in cfgs]
    shares = [0.0] * len(runs)
    for k in range(n):
        if feed is not None:
            feed(k)
        cursor_on = cursor and int(k / FPS * 2 * BLINK_HZ) % 2 == 0
        text = strip(k) if callable(strip) else strip
        for i, (renderer, wall) in enumerate(runs):
            frame = renderer.render(term.screen, cursor_on, text)
            out = wall.push(frame)
            if out is not frame:                      # the governor returns the frame itself when nothing is held
                shares[i] = max(shares[i], float((out != frame).any(axis=2).mean()))
    return [(wall, share, wall.display.pushed) for (_, wall), share in zip(runs, shares)]


def feeds(chunks):
    """govern's term, n and feed for a chunk of bytes a frame."""
    term = Terminal(80, 23)

    def feed(k):
        if chunks[k]:
            term.feed(chunks[k])
    return term, len(chunks), feed


def typing(cps, seconds):
    """arcade/flash.py typed at cps, a frame's share each frame (the probe's fixed text)."""
    src, per = (ROOT / "arcade" / "flash.py").read_bytes(), cps // FPS
    return [src[k * per:(k + 1) * per] for k in range(int(seconds * FPS))]


def test_attract_scroll_is_not_held(tmp_path):
    entry = load_entry(write_entry(tmp_path, "flash", 1, (ROOT / "arcade" / "flash.py").read_text()))
    term = Terminal(80, 23)
    attract = Attract([entry], term, 3.0)
    attract.start(0.0)
    runs = govern((TEXT, INK), term, 10 * FPS, lambda k: attract.tick(k / FPS), ATTRACT_STRIP)
    for name, (wall, share, _) in zip(("text", "ink"), runs):
        print(f"{name}: attract 3 lines/s, 10 s: held_ticks {wall.governor.held_ticks}, share {share:.4f}")
        assert wall.governor.held_ticks == 0, name


def test_typing_is_barely_held():
    for cps, bound in ((400, 0.03), (1600, 0.08)):
        [(wall, share, _)] = govern((TEXT,), *feeds(typing(cps, 5)))
        print(f"text: typing {cps} cps, 5 s: share {share:.4f} (bound {bound})")
        assert share <= bound, (cps, share)


def test_a_flood_is_held_on_few_pixels():
    chunks, i = [], 0
    for _ in range(3 * FPS):
        chunk = b""
        while len(chunk) < 4096:
            chunk += f"{i}\n".encode()
            i += 1
        chunks.append(chunk)
    [(wall, share, _)] = govern((TEXT,), *feeds(chunks))
    print(f"text: a flood of numbered lines, 4 KB a frame, 3 s: share {share:.4f}")
    assert share <= 0.02, share


@pytest.mark.skipif(shutil.which("cc") is None, reason="needs a C compiler")
def test_the_hello_band_is_not_held(tmp_path):
    # hello's own bytes, built without its pacing (usleep a no-op): the same output, 3 s sooner
    stub = tmp_path / "no_usleep.c"
    stub.write_text("int no_usleep(unsigned int us) { (void)us; return 0; }\n")
    subprocess.run(["cc", "-Dusleep=no_usleep", "-o", str(tmp_path / "hello"),
                    str(ROOT / "entries" / "hello" / "hello.c"), str(stub)], check=True, capture_output=True,
                   timeout=60)
    raw = subprocess.run([str(tmp_path / "hello")], env={"LINES": "23", "COLUMNS": "80"}, capture_output=True,
                         timeout=30).stdout
    parts = raw.split(b"\x1b[H")
    chunks = [parts[0]] + [b"\x1b[H" + p for p in parts[1:]] + [b""] * 40
    assert len(chunks) > 100
    for name, (wall, share, _) in zip(("text", "ink"), govern((TEXT, INK), *feeds(chunks))):
        print(f"{name}: the hello band: share {share:.4f}")
        assert share == 0.0, name


def test_cursor_blink_and_strip_alternation_are_not_held():
    def alternate(k):                                 # Q58's halves, 3 s each: two changes by 6 s
        return "Trey, 2026" if (k // (3 * FPS)) % 2 == 0 else "Not A.I."
    runs = govern((TEXT, INK), *feeds([b"$ "] + [b""] * (6 * FPS)), strip=alternate)
    for name, (wall, share, _) in zip(("text", "ink"), runs):
        assert wall.governor.held_ticks == 0 and share == 0.0, name


def test_the_static_error_frame_passes_unchanged():
    lines = ["entries: entries: not a directory", "font: [Errno 2] No such file or directory: 'fonts/5x7.bin'"]
    for w, h, font in ((512, 192, FONT), (128, 64, FONT), (512, 192, None)):
        frame, inner = error_frame(w, h, (51, 255, 51), font, lines), Recorder()
        assert frame.shape == (h, w, 3) and frame.dtype == np.uint8 and frame.any()
        wall = GovernedDisplay(inner, h, w, fps=FPS)
        for _ in range(2 * FPS):
            wall.push(frame)
        assert wall.governor.held_ticks == 0 and all(np.array_equal(f, frame) for f in inner.pushed)
    assert error_frame(512, 192, (51, 255, 51), FONT, []).any()                  # never black


def test_the_ink_view_holds_a_fast_scroll_on_few_pixels():
    [(wall, share, _)] = govern((INK,), *feeds(typing(400, 5)))
    print(f"ink: typing 400 cps, 5 s: share {share:.4f} (bound 0.15), held_ticks {wall.governor.held_ticks}")
    assert share <= 0.15, share


def test_strobes_over_3_hz_are_held_and_under_are_not():
    from tests.test_main import FILL                          # the loop tests' lit screen, the cursor hidden
    for period in (1, 2, 3, 4):                               # 10, 5, 3.3 and 2.5 Hz at 20 fps
        chunks = [FILL if (k // period) % 2 == 0 else OFF for k in range(60)]
        for name, (wall, share, pushed) in zip(("text", "ink"), govern((TEXT, INK), *feeds(chunks))):
            if period < 4:
                area, squares = flash_area(pushed, fps=FPS), square_flashes(pushed, fps=FPS)
                print(f"{name}: strobe {FPS / (2 * period):.1f} Hz: pushed area {area}, squares {squares}, "
                      f"held_ticks {wall.governor.held_ticks}")
                assert area == 0.0 and squares <= BUDGET, (name, period, area, squares)
            else:
                assert wall.governor.held_ticks == 0, name
