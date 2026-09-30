"""The wall's hold after a failed push and its dark start (it14 T-wall, C51, C52): the plan's, as given."""
import ast
import math
from pathlib import Path

import numpy as np
import pytest

from arcade.flash import BUDGET, flash_area, square_flashes
from show.wall import HOLD_S, GovernedDisplay

ROOT = Path(__file__).resolve().parents[1]
H, W = 64, 128
LIT = np.array((51, 255, 51), np.uint8)
DARK = np.zeros((H, W, 3), np.uint8)


class TornDisplay:
    """A send numbered in `tears` (every call counted from 1) raises after the rows above `split` arrived.
    card=False: rows show as they arrive (it13's probe). card=True: colorlight's order, the frame packet first
    shows the rows the last call left. shown: (tick, the wall after the call)."""
    def __init__(self, tears, split=H // 2, card=False):
        self.tears, self.split, self.card = tears, split, card
        self.calls, self.tick, self.closed = 0, 0, False
        self.rows, self.screen, self.shown = DARK.copy(), DARK.copy(), []

    def push(self, frame):
        self.calls += 1
        if self.card:
            self.screen = self.rows.copy()
        torn = self.tears(self.calls)
        if torn:
            self.rows[:self.split] = frame[:self.split]
        else:
            self.rows = frame.copy()
        if not self.card:
            self.screen = self.rows.copy()
        self.shown.append((self.tick, self.screen.copy()))
        if torn:
            raise OSError("torn")

    def set_brightness(self, level):
        pass

    def close(self):
        self.closed = True


class SteadyDisplay:
    """The steady sender's model (route A): push raises the error its last torn burst carried back and stores
    nothing, or stores the frame and clears the pause; then the tick's bursts run, ceil(59 / fps) of them. A burst
    numbered in `tears` (bursts counted from 1) writes the rows above `split`, sends no sync and pauses the sender;
    the burst after a push that ends a pause is a prime (rows, no sync). The sync of a burst shows the rows the
    burst before it sent. shown: (tick, the wall after each burst)."""
    def __init__(self, tears, split=H // 2, fps=20):
        self.tears, self.split, self.per_tick = tears, split, math.ceil(59 / fps)
        self.bursts, self.tick, self.closed = 0, 0, False
        self.rows, self.screen, self.shown = DARK.copy(), DARK.copy(), []
        self.pending, self.paused, self.primed, self.error = DARK.copy(), False, False, None

    def push(self, frame):
        if self.error is not None:
            error, self.error = self.error, None
            raise error
        self.pending = frame.copy()
        self.paused = False
        self._run()

    def _run(self):
        for _ in range(self.per_tick):
            if self.paused:
                self.shown.append((self.tick, self.screen.copy()))
                continue
            self.bursts += 1
            if self.primed:
                self.screen = self.rows.copy()                # the sync: the last burst's rows show
            self.primed = True
            if self.tears(self.bursts):
                self.rows[:self.split] = self.pending[:self.split]
                self.paused, self.primed, self.error = True, False, OSError("torn")
            else:
                self.rows = self.pending.copy()
            self.shown.append((self.tick, self.screen.copy()))

    def set_brightness(self, level):
        pass

    def close(self):
        self.pending, self.paused = DARK.copy(), False      # the driver's own black, held a second
        self._run()
        self._run()
        self.closed = True


MODELS = ("probe", "card", "steady")


def torn_display(tears, split=H // 2, model="probe", fps=20):
    if model == "steady":
        return SteadyDisplay(tears, split=split, fps=fps)
    return TornDisplay(tears, split=split, card=model == "card")


def in_time(shown, fps):
    """The wall from dark in real time: each tick cut in k slots (k the most calls in a tick), a slot the wall after
    a call, a tick padded with its last state (or the last tick's): fps * k slots are a second."""
    by_tick = {}
    for tick, frame in shown:
        by_tick.setdefault(tick, []).append(frame)
    k = max(len(v) for v in by_tick.values())
    seq, last = [DARK] * k, DARK
    for tick in range(max(by_tick) + 1):
        frames = by_tick.get(tick) or [last]
        seq += frames + [frames[-1]] * (k - len(frames))
        last = frames[-1]
    return seq, fps * k


def reversal(hz, fps, n, top_first=False):
    out = []
    for k in range(n):
        f = DARK.copy()
        if (round(k / fps * 2 * hz) % 2 == 0) != top_first:
            f[H // 2:] = LIT
        else:
            f[:H // 2] = LIT
        out.append(f)
    return out


def strobe(hz, fps, n):
    return [np.broadcast_to(LIT if round(k / fps * 2 * hz) % 2 == 0 else DARK[0, 0], (H, W, 3)).copy()
            for k in range(n)]


def drive(frames, inner, fps):
    """The loop's push, one a tick, the tick's time the wall's clock; a failed push is the loop's to log."""
    wall = GovernedDisplay(inner, H, W, fps=fps, from_dark=True, clock=lambda: inner.tick / fps)
    for k, f in enumerate(frames):
        inner.tick = k
        try:
            wall.push(f)
        except OSError:
            pass
    return wall


TEARS = {"every 2nd": lambda n: n % 2 == 0, "every 3rd": lambda n: n % 3 == 0, "calls 9-12": lambda n: 9 <= n <= 12,
         "call 5": lambda n: n == 5}


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("tears", TEARS, ids=list(TEARS))
@pytest.mark.parametrize("hz,fps", [(10, 20), (10, 30), (5, 30)])
@pytest.mark.parametrize("pattern", [reversal, strobe], ids=["reversal", "strobe"])
def test_torn_pushes_keep_the_wall_in_the_budget_in_real_time(pattern, hz, fps, tears, model):
    inner = torn_display(TEARS[tears], model=model, fps=fps)
    drive(pattern(hz, fps, 4 * fps), inner, fps)
    seq, n = in_time(inner.shown, fps)
    assert flash_area(seq, fps=n) == 0.0 and square_flashes(seq, fps=n) <= BUDGET


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("split", [24, 33])
@pytest.mark.parametrize("lead", [0, 1])
def test_one_torn_push_at_any_call_keeps_the_wall_in_the_budget(lead, split, model):
    frames = reversal(10, 20, 120, top_first=True)
    frames = frames[:1] * lead + frames
    for call in range(1, 11):
        inner = torn_display(lambda n, call=call: n == call, split=split, model=model)
        drive(frames, inner, 20)
        seq, n = in_time(inner.shown, 20)
        assert square_flashes(seq, fps=n) <= BUDGET and flash_area(seq, fps=n) == 0.0, call


class Clocked:
    """A display whose sends numbered in `fail` raise; sent: (the clock's time, the frame) of every good send."""
    def __init__(self, fail, clock):
        self.fail, self.clock, self.calls, self.sent, self.closed = set(fail), clock, 0, [], False

    def push(self, frame):
        self.calls += 1
        if self.calls in self.fail:
            raise OSError("no carrier")
        self.sent.append((self.clock(), frame.copy()))

    def set_brightness(self, level):
        pass

    def close(self):
        self.closed = True


def test_after_a_failed_push_the_wall_is_still_then_sends_the_counted_frame_twice_a_second_apart():
    now = [0.0]
    inner = Clocked({17, 21}, lambda: now[0])
    wall = GovernedDisplay(inner, H, W, fps=16, from_dark=True, clock=lambda: now[0])
    applied, apply = [], wall.governor.apply
    wall.governor.apply = lambda f: applied.append(now[0]) or apply(f)
    got, counted = [], {}
    for k, f in enumerate(strobe(1, 16, 160)):
        now[0] = k / 16
        try:
            got.append(wall.push(f))
        except OSError:
            got.append("raised")
            counted[k] = wall.last.copy()
    # call 17 fails at 1.0: still to 2.0; the counted frame at 2.0 and 3.0; new frames from 4.0. Call 21 (4.0625)
    # fails: still to 5.0625; the counted frame at 5.0625 and 6.0625; new frames from 7.0625.
    assert HOLD_S == 1.0 and wall.failed == 2 and sorted(counted) == [16, 65] and not wall.holding
    assert [t for t, _ in inner.sent] == [k / 16 for k in [*range(16), 32, 48, 64, 81, 97, *range(113, 160)]]
    assert [k for k, g in enumerate(got) if g is None] == [*range(17, 32), *range(33, 48), *range(49, 64),
                                                           *range(66, 81), *range(82, 97), *range(98, 113)]
    for sent, pushed, failed in ((16, 32, 16), (17, 48, 16), (19, 81, 65), (20, 97, 65)):
        assert np.array_equal(inner.sent[sent][1], counted[failed]) and np.array_equal(got[pushed], counted[failed])
    # B1: at 4.0 and 7.0625 the re-initialised governor applies the counted frame, then the new frame.
    assert applied == [k / 16 for k in [*range(17), 64, 64, 65, 113, *range(113, 160)]]
    assert wall.governed == len(applied) - 4


@pytest.mark.parametrize("hz,fps", [(10, 20), (10, 30), (5, 20), (5, 30)])
@pytest.mark.parametrize("pattern", [reversal, strobe], ids=["reversal", "strobe"])
def test_from_a_dark_wall_the_first_second_is_in_the_budget(pattern, hz, fps):
    inner = Clocked(set(), lambda: 0.0)
    wall = GovernedDisplay(inner, H, W, fps=fps, from_dark=True)
    assert inner.calls == 0                                       # nothing is sent at birth
    for f in pattern(hz, fps, 2 * fps):
        wall.push(f)
    shown = [DARK] + [f for _, f in inner.sent]                   # the dark wall, then what was sent
    assert len(shown) == 2 * fps + 1
    assert flash_area(shown, fps=fps) == 0.0 and square_flashes(shown, fps=fps) <= BUDGET


def test_every_governed_wall_starts_from_dark_and_the_show_s_holds():
    made = {p.name for p in [*(ROOT / "show").rglob("*.py"), *(ROOT / "tools").glob("*.py")]
            if "GovernedDisplay(" in p.read_text()}
    assert made == {"main.py", "wall_pattern.py", "wall_video.py"}
    for path in (ROOT / "show" / "main.py", ROOT / "tools" / "wall_pattern.py", ROOT / "tools" / "wall_video.py"):
        wraps = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == "GovernedDisplay"]
        assert wraps, path
        for w in wraps:
            kw = {k.arg: ast.unparse(k.value) for k in w.keywords}
            assert kw.get("from_dark") == "True", ast.unparse(w)
            assert path.name != "main.py" or kw.get("clock") not in (None, "None"), ast.unparse(w)


# -- the plan's tests in prose ----------------------------------------------------------------------------------------

from tests.test_main import FailingPushes, no_devices, playing_loop  # noqa: E402, F401 (no_devices: autouse)


def test_without_a_clock_a_failed_push_does_not_hold():
    inner = Clocked({3}, lambda: 0.0)
    wall = GovernedDisplay(inner, H, W, fps=16, from_dark=True)
    frames = strobe(1, 16, 4)
    for f in frames[:2]:
        wall.push(f)
    with pytest.raises(OSError):
        wall.push(frames[2])                                      # call 3
    assert not wall.holding and wall.failed == 1 and wall.governed == 2
    out = wall.push(frames[3])                                    # call 4: governed and sent at once
    assert out is not None and not wall.holding and wall.governed == 3 and len(inner.sent) == 3
    assert np.array_equal(inner.sent[-1][1], out) and np.array_equal(wall.last, out)


# it15 T-close (C53): the close in the hold waits it out; its test is test_wall_close_hold.py's
# test_close_in_the_hold_waits_then_the_counted_frame_waits_then_black, which replaces the one here.


def test_a_held_loop_step_counts_toward_the_dark_lights(tmp_path):
    from show.main import PUSH_DARK_S

    inner = FailingPushes(range(2, 400))
    loop = playing_loop(tmp_path, inner)                          # call 1 at 0.05
    assert loop.lights.modes[1] == "bright"
    loop.step(1.0)                                                # call 2 fails: the hold
    loop.step(1.5)                                                # held
    for k in range(9):
        loop.step(2.25 + k)                                       # each counted send fails: the hold again
    assert inner.count == 1 and inner.calls == 11 and loop.wall.holding
    loop.step(1.0 + PUSH_DARK_S - 0.05)                           # held
    assert loop.lights.offs == 0 and loop.lights.modes[1] == "bright"
    loop.step(1.0 + PUSH_DARK_S)                                  # held, nothing sent: 10 s without a frame
    assert inner.calls == 11 and loop.wall.holding
    assert loop.lights.offs == 1 and loop.lights.modes[1] == "off"
    inner.fail.clear()
    loop.step(11.25)                                              # the counted send arrives: relit
    assert inner.count == 2 and np.array_equal(inner.pushed[-1], loop.wall.last)
    assert loop.lights.modes[1] == "bright" and loop.show.playing
