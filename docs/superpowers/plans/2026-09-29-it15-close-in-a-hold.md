# Iteration 15: the close while the wall holds (C53)
BASE: HEAD at the spawn. Carried fix C53. Thin plan. SAFETY TASK.
Code head da20a3a. Q68, Q69 below. NOT edited: `arcade/` (all), `show/display/colorlight.py`, `deploy/`, `tools/`.

## Global Constraints
- Test command, from the root: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/
  python -m pytest -q -rs`. About 235 s, 1231 collected, 1 skip on the Mac. In a worktree a second skip,
  `tests/arcade/test_pose_mediapipe.py:223` (the pose model is not in git), is expected: tell the orchestrator.
- Test-first; only your files; never `cd` (absolute paths, `git -C`); `git add` by name; no stash, push or command
  over 10 min; fakes only (no window, sound, GPIO, packet). Nothing under `deploy/` installed, enabled or run.
  No rulings: a gap is reported. Trailer `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- No existing assert is removed or weakened, save the ONE in "The changed test". EXACT tests (Loop rule 4):
  reformat only. On the writer's scratch wall all 12 pass (2.8 s); today fails 8; eleven wrong closes fail some.

## Lanes
- One task, `isolation: "worktree"` from BASE: T-close (opus); it touches nothing of the arcade lane's.
- Owners: T-close `show/wall.py`, `show/main.py` (only `_open_wall` and `_close`), `tests/test_wall_close_hold.py`
  (new), `tests/test_wall_hold.py` (only `test_close_during_the_hold_sends_the_counted_frame_then_black`, 211-228),
  `tests/test_wall_close.py` (one added line only, below; no assert of it changes). Nobody: `tests/test_wall.py`,
  `tests/test_main.py`, `tools/wall_pattern.py`.
- After the merge: its files; under `tests/`: `test_wall.py test_wall_close.py test_main.py
  test_wall_pattern_governed.py test_show_soak.py`; then the full suite.

## T-close (opus): the close waits out the hold, in `GovernedDisplay`
### The gap (the writer's measure, scratch `find_today.txt`)
Reversal top first 10 Hz, fps 20, one tear at call 28 (tick 27), split 33, today's `close()` j ticks later: 8
square transitions in a second (rows as they arrive, j = 1) and 7 (both models, j = 2 to 16); area 0.000. Also one
case each at call 24 and, 5 Hz, call 27 (card, j = 1). What makes it: the close sends the counted frame (the return
from the tear) and black right behind the tear. Black alone after a tear stays at 6 (the "no wait" close, below).

### The close planned
While the wall holds (`self.holding`, which needs a clock), `close()`:
1. waits, sending nothing, until the hold's next send is due: `wait = self._since + HOLD_S - self._clock()`;
   `self._sleep(wait)` when `wait > 0`. The clock is read ONCE, before the first wait, and never inside a loop:
   the loop's wall clock is `self._now`, which no sleep moves, so a close that reads it again (`while clock() <
   due`) never ends and the stop hangs until systemd kills it (the plan review's B2; its exact test below);
2. if no counted send has gone since the failure (`self._settled == 0`): the counted frame once (`repush`; a
   failure is logged and the close goes on), then `self._sleep(HOLD_S)`: a quiet second after it, whatever it did;
3. `self._end_hold()` (the governor made again in place and primed with the counted frame, not sent: the wall's
   picture and the governor's state brought together as at a hold's end, Q50: black passes `apply`);
4. two governed black frames (`_govern`), as today; `display.close()` in `finally`, whatever raised.
Not holding: today's close (the counted frame if `unsent`, two governed black, closed), no sleep. No clock
(`tools/wall_pattern.py`): never holding, no sleep. At most `2 * HOLD_S` (2 s) of sleep plus four sends, inside
systemd's default `TimeoutStopSec` (90 s; `deploy/show.service` sets none). A wait that raises (Ctrl-C) ends the
close: nothing more sent (no early black), the display closed by `finally`, the exception goes on. A second
SIGTERM does not raise (`Sigterm` counts it) and the sleep goes on (PEP 475).

### Interfaces
- `GovernedDisplay.__init__(self, display, height, width, fps=30, gamma=2.2, *, from_dark=False, clock=None,
  sleep: Callable[[float], None] = time.sleep)`: `self._sleep = sleep`. `import time` in `show/wall.py`.
- `close(self) -> None`: as above; its docstring and the module docstring say the close waits out the hold (C53).
  No new constant: the waits are `HOLD_S` (1.0). `_end_hold` is reused as it is.
- `show/main.py`, `_open_wall`: both `GovernedDisplay(...)` calls get `sleep=lambda s: self.sleep(s)` (late bound:
  tests set `loop.sleep` after the loop is made). `_close`: `self._now = self.clock()` right before
  `self.wall.close()`, so the wall's clock reads the time of the close (the real wait is not one step too long).

### The changed test (the ONE assert change)
`tests/test_wall_hold.py:211-228`, `test_close_during_the_hold_sends_the_counted_frame_then_black`: its lines
224-226 (`wall.close()  # no wait ...`, `inner.calls == 6 ...`, the sent times `[3 / 16] * 3`) assert the close
that is not held. With the planned close it would still pass (its fake clock never moves: the close's sleeps are
real, 1.95 s), but it asserts no wait, so it is deleted and replaced by the exact test below (same set-up; the
counted frame at 18/16, black at 34/16, sleeps 15/16 and 1.0):
`test_close_in_the_hold_waits_then_the_counted_frame_waits_then_black`.
`tests/test_wall_close.py:62-69`: ONE line added, `loop.sleep = lambda s: None`, right before its `loop._close()`,
so that it does not sleep a real second (the wall's `sleep` is the loop's, late bound). No assert of it changes.

### EXACT tests: `tests/test_wall_close_hold.py` (new; reformat only)
```python
"""The close while the wall holds (it15 T-close, C53): the plan's, as given."""
import copy
import math

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
    wall = GovernedDisplay(inner, H, W, fps=16, from_dark=True, clock=lambda: 0.0, sleep=lambda s: pytest.fail("slept"))
    wall.push(strobe(1, 16, 1)[0])
    wall.close()
    assert inner.calls == 3 and inner.closed and not inner.sent[-1][1].any()
```
### Tests in prose (the implementer writes them, in the same file, after the exact ones)
- `test_the_loop_s_close_in_a_hold_waits_on_the_loop_s_sleep`: `playing_loop(tmp_path, FailingPushes({3}))`,
  `loop.clock = lambda: t[0]`, `loop.sleep` adds to `t[0]` and notes; steps 0.10, 0.15 (call 3 fails); `t[0] = 0.2`;
  `loop._close()`: sleeps `[0.95, 1.0]` (approx), `inner.count == 5`, `pushed[2]` the counted frame, the last two
  black, `inner.closed` (import `FailingPushes, no_devices, playing_loop` from `tests.test_main`).
- `test_a_failed_counted_send_in_the_close_still_waits_then_goes_black`: `Clocked({3, 4})`, close in the hold:
  call 4 fails, logged; sleeps `[15/16, 1.0]`; 5, 6 black; closed. `..._failed_black_...`: `{3, 5}`: raises, closed.
- `test_every_governed_wall_of_the_show_gets_the_loop_s_sleep` (AST, as `test_wall_hold.py:178`): both calls in
  `show/main.py` pass `sleep=`; `tools/wall_pattern.py` passes none (no clock, no hold).
### Steps
1. The tests first; they fail on BASE (no `sleep` keyword; with it, today fails the "one tear" cases and 6 more).
2. The one test in `tests/test_wall_hold.py`; `show/wall.py`; `show/main.py`. 3. The four files, then the suite;
   `--durations=0` for the new file (the writer's: 2.8 s). 4. Commit `fix(show): the close waits out the hold
   after a failed push, then goes black (C53; it15 T-close)`.

## I2 (the operator, in verify, after the review): from a clean detached checkout of the head
```
.venv/bin/python -m show --backend fake & sleep 5; kill -TERM $!; wait $!; echo "exit $?"
.venv/bin/python -m tools.show_shot --session strobe --seconds 6 --every-ms 150 --look plain --scale 1 --cols 4 \
    --out <s>/it15-strobe
.venv/bin/python -m tools.show_shot --session presses --every-ms 1000 --look both --out <s>/it15-presses
.venv/bin/python -m tools.show_shot --config show.poc.toml --session presses --every-ms 1000 --look both \
    --out <s>/it15-presses-poc
.venv/bin/python -m tools.show_soak --minutes 2 --press-every 5 --out <s>/it15-soak
.venv/bin/python -m tools.show_soak --config show.poc.toml --minutes 2 --press-every 5 --out <s>/it15-soak-poc
```
Must show: the stop: exit 0, "closing: the wall goes black" logged, about 0.06 s from the signal to the exit as in
it13 (the fake display never fails: no hold, no wait). Strobe: every label `area 0.0000`, `sq <= 6`. Presses, full
wall: held 0, at most 4 square flashes (not worse); 128x64 as it14's. Soaks: exit 0, governed = steps, failures 0,
`squares_max <= 6`.

## Decisions
- The close waits out the hold (the roadmap's (a)), not (b): the wall still ends black. Every change of the close
  is a second from the one before, as the hold's own sends are. It replaces Q66's "The close is never held" (Q68).
- The counted frame stays (when the hold has not sent it yet): `tests/test_wall_close.py:69` keeps its assert.
  Black straight after the first wait (1 s at most) also reads 6 but moves that assert (Q69).
- Q66's gate (a card that blanks) stays the owner's. There the close does what the hold does: the card goes dark
  in the first quiet second, the counted frame lights it again, then black; not measured with r6 (the report).
- The budget test closes only at the ticks whose closes send differently (`phases`: j = 1, 2, the tick after each
  counted send, the hold's end -1 to +2; the plan review's note) and measures the whole run from dark, so the
  flash tracker is warm (no cold slice). Today's close still fails it; the planned close passes (the fix report).
- `deploy/README.md`'s "Stop" text is not changed by this task (nothing under `deploy/` is touched); the owner is
  told that a stop after a failed push takes up to 2 s.

## Questions for the owner (the loop takes each default at once)
- Q68 (it15): May a stop within 3 s of a failed push take up to 2 s to darken the wall (nothing for up to 1 s, the
  counted frame, 1 s, black; C53)? Without a failed push the stop is as fast as today. Default: yes. It replaces
  Q66's line "The close is never held".
- Q69 (it15): May the close go black after the first quiet second without the counted frame (1 s at most)? Also 6
  and area 0.000, but it changes `tests/test_wall_close.py:69`. Default: no, the counted frame stays (2 s).
