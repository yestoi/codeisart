"""The close while the wall holds (it15 T-close, C53): the plan's, as given."""
import ast
import copy
import logging
import math
from pathlib import Path

import numpy as np
import pytest

from arcade.flash import BUDGET, flash_area, square_flashes
from show.wall import HOLD_S, GovernedDisplay
from tests.test_wall_hold import H, W, Clocked, TornDisplay, in_time, reversal, strobe

TEAR = 28   # call 28 (tick 27), split 33, the reversal top first 10 Hz: today's close reads 7 to 8 (C53)


class Ticks:
    """The wall's clock (the display's tick) and its sleep: a sleep is noted and moves the tick on, rounded up."""
    def __init__(self, inner, fps):
        self.inner, self.fps, self.slept = inner, fps, []

    def __call__(self):
        return self.inner.tick / self.fps

    def sleep(self, s):
        self.slept.append(s)
        self.inner.tick += math.ceil(s * self.fps - 1e-9)


def closes(frames, inner, fps, at):
    """drive's loop; at each tick in `at` a copy of the wall closes (its own sends never tear): yields (the tick,
    the copy's display, the copy's sleeps)."""
    ticks = Ticks(inner, fps)
    wall = GovernedDisplay(inner, H, W, fps=fps, from_dark=True, clock=ticks, sleep=ticks.sleep)
    for k, f in enumerate(frames):
        inner.tick = k
        if k in at:
            w, t = copy.deepcopy((wall, ticks))
            w.display.tears = lambda n: False
            w.close()
            yield k, w.display, t.slept
        try:
            wall.push(f)
        except OSError:
            pass


def phases(tear, fps):
    """The ticks after a tear at tick `tear` whose closes send differently: 1 and 2 after it, the tick after each
    counted send, the hold's end from -1 to +2 (a close within one phase of the hold sends the same)."""
    return {tear + 1, tear + 2, tear + fps + 1, tear + 2 * fps + 1, *range(tear + 3 * fps - 1, tear + 3 * fps + 3)}


@pytest.mark.parametrize("card", [False, True], ids=["probe", "card"])
@pytest.mark.parametrize("torn", [(TEAR,), (TEAR, TEAR + 1)], ids=["one tear", "the counted send tears"])
def test_a_close_j_ticks_after_a_tear_stays_in_the_budget_and_ends_black(torn, card):
    fps = 20
    end = (TEAR - 1) + (len(torn) + 2) * fps + 2               # the hold's end and two ticks beyond
    inner = TornDisplay(lambda n: n in torn, split=33, card=card)
    frames = reversal(10, fps, end + 1, top_first=True)
    at = phases(TEAR - 1, fps) if len(torn) == 1 else phases(TEAR - 1 + fps, fps)   # the last tear's hold
    for k, shown, slept in closes(frames, inner, fps, at):     # j = k - (TEAR - 1)
        seq, n = in_time(shown.shown, fps)                     # the whole run from dark: the measure warm
        assert square_flashes(seq, fps=n) <= BUDGET and flash_area(seq, fps=n) == 0.0, k
        assert shown.closed and not shown.screen.any() and not shown.rows.any(), k        # black, closed
        assert sum(slept) <= 2 * HOLD_S + 1e-9, k


def test_a_close_in_the_hold_ends_black_when_the_governor_is_at_the_budget():
    fps = 20
    inner = TornDisplay(lambda n: n == 22, split=33, card=True)   # 5 Hz strobe, the tear at call 22 (tick 21)
    ticks = Ticks(inner, fps)
    wall = GovernedDisplay(inner, H, W, fps=fps, from_dark=True, clock=ticks, sleep=ticks.sleep)
    for k, f in enumerate(strobe(5, fps, 22)):
        inner.tick = k
        try:
            wall.push(f)
        except OSError:
            pass
    inner.tick = 22
    wall.close()
    assert inner.closed and not inner.screen.any() and not inner.rows.any()


def test_a_close_in_the_hold_reads_the_clock_once():
    now, slept = [0.0], []
    inner = Clocked({3}, lambda: now[0])

    def sleep(s):                                   # the loop's: it never moves the wall's clock (self._now)
        slept.append(s)
        assert len(slept) <= 2, "the close waits on a clock that never moves"
    wall = GovernedDisplay(inner, H, W, fps=16, from_dark=True, clock=lambda: now[0], sleep=sleep)
    frames = strobe(1, 16, 3)
    wall.push(frames[0]), wall.push(frames[1])
    now[0] = 2 / 16
    with pytest.raises(OSError):
        wall.push(frames[2])
    now[0] = 3 / 16
    wall.close()
    assert slept == pytest.approx([15 / 16, HOLD_S]) and inner.calls == 6 and inner.closed


def test_close_in_the_hold_waits_then_the_counted_frame_waits_then_black():
    """Replaces test_wall_hold.py's close in the hold: the quiet second, the counted frame, the quiet second, black."""
    now = [0.0]
    inner = Clocked({3}, lambda: now[0])
    slept = []

    def sleep(s):
        slept.append(s)
        now[0] += s
    wall = GovernedDisplay(inner, H, W, fps=16, from_dark=True, clock=lambda: now[0], sleep=sleep)
    frames = strobe(1, 16, 4)
    for f in frames[:2]:
        wall.push(f)
    now[0] = 2 / 16
    with pytest.raises(OSError):
        wall.push(frames[2])                                      # call 3: governed and counted, never shown
    counted = wall.last.copy()
    now[0] = 3 / 16
    assert wall.push(frames[3]) is None and wall.holding          # held, nothing sent
    wall.close()                                                  # 15/16 s still; call 4 at 18/16; 1 s; 5 and 6
    assert inner.closed and inner.calls == 6 and not wall.unsent and not wall.holding
    assert slept == pytest.approx([15 / 16, HOLD_S])
    assert [t for t, _ in inner.sent[2:]] == pytest.approx([18 / 16, 34 / 16, 34 / 16])
    assert np.array_equal(inner.sent[2][1], counted)
    assert not inner.sent[3][1].any() and not inner.sent[4][1].any() and wall.governed == 4   # governed black


def test_close_after_the_counted_frame_went_waits_once_then_black():
    now = [0.0]
    inner = Clocked({3}, lambda: now[0])
    slept = []
    wall = GovernedDisplay(inner, H, W, fps=16, from_dark=True, clock=lambda: now[0],
                           sleep=lambda s: slept.append(s) or now.__setitem__(0, now[0] + s))
    for k, f in enumerate(strobe(1, 16, 20)):
        now[0] = k / 16
        try:
            wall.push(f)                                          # call 3 (2/16) fails; call 4 at 18/16 counted
        except OSError:
            pass
    now[0] = 20 / 16
    wall.close()                                                  # still to 34/16, then black: calls 5 and 6
    assert slept == pytest.approx([14 / 16]) and inner.calls == 6 and inner.closed
    assert [t for t, _ in inner.sent[3:]] == pytest.approx([34 / 16, 34 / 16])
    assert not inner.sent[3][1].any() and not inner.sent[4][1].any()


@pytest.mark.parametrize("error", [KeyboardInterrupt, OSError])
def test_a_wait_that_raises_sends_nothing_and_still_closes_the_display(error):
    now = [2 / 16]
    inner = Clocked({3}, lambda: now[0])

    def sleep(s):
        raise error()
    wall = GovernedDisplay(inner, H, W, fps=16, from_dark=True, clock=lambda: now[0], sleep=sleep)
    frames = strobe(1, 16, 3)
    wall.push(frames[0]), wall.push(frames[1])
    with pytest.raises(OSError):
        wall.push(frames[2])
    with pytest.raises(error):
        wall.close()
    assert inner.closed and inner.calls == 3                      # nothing sent after the tear: no early black


def test_a_close_without_a_clock_never_waits():
    inner = Clocked({3}, lambda: 0.0)
    wall = GovernedDisplay(inner, H, W, fps=16, from_dark=True, sleep=lambda s: pytest.fail("slept"))
    frames = strobe(1, 16, 3)
    wall.push(frames[0]), wall.push(frames[1])
    with pytest.raises(OSError):
        wall.push(frames[2])
    wall.close()                                                  # today's: the counted frame, black, black
    assert inner.calls == 6 and inner.closed and not inner.sent[-1][1].any()


def test_a_close_that_is_not_holding_never_waits():
    inner = Clocked(set(), lambda: 0.0)
    wall = GovernedDisplay(inner, H, W, fps=16, from_dark=True, clock=lambda: 0.0,
                           sleep=lambda s: pytest.fail("slept"))
    wall.push(strobe(1, 16, 1)[0])
    wall.close()
    assert inner.calls == 3 and inner.closed and not inner.sent[-1][1].any()


# -- the plan's tests in prose ----------------------------------------------------------------------------------------

from tests.test_main import FailingPushes, no_devices, playing_loop  # noqa: E402, F401 (no_devices: autouse)

ROOT = Path(__file__).resolve().parents[1]


def test_the_loop_s_close_in_a_hold_waits_on_the_loop_s_sleep(tmp_path):
    t, slept = [0.0], []
    inner = FailingPushes({3})
    loop = playing_loop(tmp_path, inner)                          # call 1 at 0.05
    loop.clock = lambda: t[0]

    def sleep(s):                                                 # set after the loop is made: the wall's is late bound
        slept.append(s)
        t[0] += s
    loop.sleep = sleep
    loop.step(0.10)
    loop.step(0.15)                                               # call 2; call 3 fails: its frame was governed
    counted = loop.wall.last.copy()
    t[0] = 0.2
    loop._close()                                                 # 0.95 s still; call 4 (counted); 1 s; 5 and 6 black
    assert slept == pytest.approx([0.95, 1.0])
    assert inner.count == 5 and np.array_equal(inner.pushed[2], counted)
    assert not inner.pushed[-1].any() and not inner.pushed[-2].any() and inner.closed


def _close_in_the_hold(fail):
    """Clocked(fail), the hold from call 3 at 2/16, the close at 3/16; each sleep moves the clock. Returns (inner,
    the wall, the sleeps)."""
    now, slept = [0.0], []
    inner = Clocked(fail, lambda: now[0])

    def sleep(s):
        slept.append(s)
        now[0] += s
    wall = GovernedDisplay(inner, H, W, fps=16, from_dark=True, clock=lambda: now[0], sleep=sleep)
    frames = strobe(1, 16, 3)
    wall.push(frames[0]), wall.push(frames[1])
    now[0] = 2 / 16
    with pytest.raises(OSError):
        wall.push(frames[2])                                      # call 3: the hold
    now[0] = 3 / 16
    return inner, wall, slept


def test_a_failed_counted_send_in_the_close_still_waits_then_goes_black(caplog):
    inner, wall, slept = _close_in_the_hold({3, 4})
    with caplog.at_level(logging.ERROR, logger="show.wall"):
        wall.close()                                              # call 4, the counted frame, fails: logged
    assert any(r.name == "show.wall" and r.exc_info for r in caplog.records)
    assert slept == pytest.approx([15 / 16, HOLD_S])
    assert inner.calls == 6 and len(inner.sent) == 4 and inner.closed
    assert [t for t, _ in inner.sent[2:]] == pytest.approx([34 / 16, 34 / 16])
    assert not inner.sent[2][1].any() and not inner.sent[3][1].any()   # 5 and 6: black


def test_a_failed_black_in_the_close_raises_and_still_closes_the_display():
    inner, wall, slept = _close_in_the_hold({3, 5})
    with pytest.raises(OSError):
        wall.close()                                              # call 4 the counted frame; call 5, black, fails
    assert slept == pytest.approx([15 / 16, HOLD_S])
    assert inner.calls == 5 and inner.closed


def test_every_governed_wall_of_the_show_gets_the_loop_s_sleep():
    for path, want in ((ROOT / "show" / "main.py", "lambda s: self.sleep(s)"),
                       (ROOT / "tools" / "wall_pattern.py", None)):
        wraps = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == "GovernedDisplay"]
        assert wraps, path
        for w in wraps:
            kw = {k.arg: ast.unparse(k.value) for k in w.keywords}
            assert kw.get("sleep") == want, ast.unparse(w)
    assert len([n for n in ast.walk(ast.parse((ROOT / "show" / "main.py").read_text())) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name) and n.func.id == "GovernedDisplay"]) == 2
