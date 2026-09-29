# Iteration 14: the flash governor's three gaps (a torn push, the first frame, the arcade's gamma)
BASE: HEAD at the spawn. Carried fixes C50, C51, C52. Thin plan. SAFETY SLICE.
Implementers' BASE: I0's commit (code head at the plan: 418ef74). Q65, Q66, Q67 (below). NOT edited: `arcade/
flash.py`, `arcade/brightness.py`, `show/display/colorlight.py`, `arcade/runner.py` (C52's arcade half: Q67).

## Global Constraints
- Test command, from the root: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/
  python -m pytest -q -rs`. About 225 s, 1140 collected, 1 skip on the Mac (`tests/test_sandbox.py:153`). In a
  worktree a second skip, `tests/arcade/test_pose_mediapipe.py:223` (the pose model is not in git), is expected.
  Suite limit 250 s. New tests 8 s at most (`--durations=0`): I0 0.1 s, T-wall 4 s (measured 2.9 s in scratch).
- Test-first; only your files; never `cd` (absolute paths, `git -C`); `git add` by name; no stash, push or command
  over 10 min; `tmp_path`; fakes only (no window, sound, GPIO, packet). Nothing under `deploy/` installed, enabled
  or run. No rulings: a gap is reported. Trailer `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- No existing assert is removed or weakened, save ONE: `tests/test_main.py:289-300` asserts what Q65 replaces (a
  new frame governed 0.05 s after a failure; any hold changes it); the EXACT test below replaces it. Not edited:
  `tests/test_wall.py`, `tests/test_wall_close.py`, `tests/test_wall_pattern_governed.py`, `tests/arcade/` but I0's.
- EXACT safety tests (Loop rule 4): reformat only, no assert changed. They pass on the writer's scratch copy of the
  planned wall (77 passed, 3.1 s); today's code and each of seven wrong walls fail some (the report).

## Lanes
- I0 (orchestrator, main checkout, first): C50 below; `tests/arcade/test_config.py`, then the suite; one commit: BASE.
- GROUP 1, one task, `isolation: "worktree"` from BASE: T-wall (opus). No other task: C52's arcade half is Q67
  (not changed), the `--config`/`load_config`/soak notes are cut (see the report). `arcade/runner.py`: no task.
- Merge order: I0, T-wall. After T-wall's merge: its files, then `tests/test_wall.py tests/test_wall_close.py
  tests/test_main.py tests/test_wall_pattern_governed.py tests/test_show_soak.py`, then the full suite.
- Owners: I0 `arcade/config.py`, `tests/arcade/test_config.py` (`arcade.toml` read, not edited: gamma 2.2).
  T-wall `show/wall.py`, `show/main.py`, `tools/wall_pattern.py`, `tests/test_wall_hold.py` (new),
  `tests/test_main.py` (only 289-300). Nobody: `show/config.py`, `show.toml`, `show.poc.toml`, `tools/show_*.py`.

## I0 (orchestrator): C50, the arcade's gamma bound, test first
1. `tests/arcade/test_config.py`, at the end: `test_gamma_outside_1_to_2_2_is_refused` (0.22, 22.0, 0.5, 2.3 by
   `load_config(write(tmp_path, f"gamma = {value}"))`: ValueError matching "gamma"); `test_gamma_1_and_2_2_are_taken`
   (1.0 and 2.2 load as given); `test_the_shipped_arcade_configs_are_in_the_gamma_bound` (`arcade.toml`, `arcade.mac.
   toml` by `load_config`: 1.0 <= gamma <= 2.2; the root is `Path(__file__).resolve().parents[2]`). Four fail today.
2. `arcade/config.py` after line 105: `if not 1.0 <= cfg.gamma <= 2.2:` raise `ValueError(f"gamma must be 1.0 (the
   card applies gamma) to 2.2 (bytes as they are), got {cfg.gamma}")`; 101-105 stay (`test_config.py:77-78`). Tests
   build no other gamma through `load_config` (`test_brightness.py:109,113,259` build `ArcadeConfig` in code).
   Commit `fix(arcade): gamma is 1.0 to 2.2, as the show's (C50; it14 I0)`.

## T-wall (opus): the hold after a failed push (C51) and the dark start (C52), in `GovernedDisplay`
```
HOLD_S = 1.0         # show/wall.py: after a failed send, the wall is still this long before each counted send
SETTLE_SENDS = 2     # the counted frame is sent this many times, HOLD_S apart, then new frames HOLD_S later
class GovernedDisplay:
    def __init__(self, display, height, width, fps=30, gamma=2.2, *, from_dark: bool = False,
                 clock: Callable[[], float] | None = None)
        # from_dark (C52): governor.apply(black) once at birth, NOT sent: the dark wall is the governor's first
        #   frame, so the first frame shown is counted against black. False: today's (the first frame passes).
        # clock (C51): seconds for the hold; None: no hold (a caller that stops at its first failure).
    holding: bool    # True from a failed send (clock given) until push governs a new frame after the hold
    def push(self, frame) -> np.ndarray | None
        # Not holding: today's (apply, send, governed += 1, returns what was sent).
        # Holding: governor.apply is NOT called and the frame is dropped. Until HOLD_S after the failed send (or
        #   after the last counted send) nothing is sent and push returns None. Then repush() sends the counted
        #   frame (self.last) and push returns a copy of it; SETTLE_SENDS such sends, each HOLD_S after the one
        #   before; HOLD_S after the last one, holding ends and this push governs and sends its own frame.
        # A send that raises (a counted send too): failed += 1, the hold starts again from that time, the
        #   exception goes on to the caller as today (the loop logs and counts it).
    def repush(self) -> None     # today's; the hold's counted sends go through it
    def close(self) -> None      # today's behaviour, not held: the counted frame if unsent, two governed black
```
- One governed path: a private `_govern(frame)` (apply, `_send`, governed += 1) is what `push` and `close` use;
  `_send(` keeps exactly two call sites (`_govern`, `repush`) and `display.push` one (`tests/test_main.py:87`).
- The governor during the hold: not called. Its window counts frames: frames it never sees keep the last fps in the
  window longer, so after the hold it is stricter in seconds, never laxer (Q59's rule).
- `show/main.py`: `self._now` (0.0 at first) set by `start(now)` and first thing in `step(now)`; both
  `GovernedDisplay(` calls in `_open_wall` add `from_dark=True, clock=lambda: self._now`. `_push`: no repush of
  its own (`_push_failed` goes); `sent = self.wall.push(frame)`; an Exception: today's path (count, log, `_failing`);
  `sent is None` (held, nothing sent): `self._failing(now)`, no log; else today's success path (a counted send
  that arrives is a good push: failures reset, lights relit). `_close` unchanged.
- `tools/wall_pattern.py`: its one `GovernedDisplay(` adds `from_dark=True`, no clock: the tool stops at its first
  OSError and closes (`tests/test_wall_pattern_governed.py:41-47`), so it never holds.
- A normal show: nothing held at the start; the first frame is counted against black (one transition of six), so a
  fast entry in the first second may be held a tick sooner. No hold without a failed push (the soak and shots never
  hold); after one the wall is frozen 3 s at least (still, the counted frame twice a second apart, a second more).

Safety tests, EXACT, `tests/test_wall_hold.py` (docstring: "The wall's hold after a failed push and its dark start
(it14 T-wall, C51, C52): the plan's, as given."):
```python
import ast
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

@pytest.mark.parametrize("card", [False, True], ids=["probe", "card"])
@pytest.mark.parametrize("tears", TEARS, ids=list(TEARS))
@pytest.mark.parametrize("hz,fps", [(10, 20), (10, 30), (5, 20), (5, 30)])
@pytest.mark.parametrize("pattern", [reversal, strobe], ids=["reversal", "strobe"])
def test_torn_pushes_keep_the_wall_in_the_budget_in_real_time(pattern, hz, fps, tears, card):
    inner = TornDisplay(TEARS[tears], card=card)
    drive(pattern(hz, fps, 3 * fps), inner, fps)
    seq, n = in_time(inner.shown, fps)
    assert flash_area(seq, fps=n) == 0.0 and square_flashes(seq, fps=n) <= BUDGET

@pytest.mark.parametrize("card", [False, True], ids=["probe", "card"])
@pytest.mark.parametrize("lead", [0, 1])
def test_one_torn_push_at_any_call_keeps_the_wall_in_the_budget(lead, card):
    frames = reversal(10, 20, 50, top_first=True)
    frames = frames[:1] * lead + frames
    for call in range(1, 11):
        inner = TornDisplay(lambda n, call=call: n == call, split=24, card=card)
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
    assert applied == [k / 16 for k in [*range(17), 64, 65, *range(113, 160)]] and wall.governed == len(applied) - 2

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
    assert made == {"main.py", "wall_pattern.py"}
    for path in (ROOT / "show" / "main.py", ROOT / "tools" / "wall_pattern.py"):
        wraps = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == "GovernedDisplay"]
        assert wraps, path
        for w in wraps:
            kw = {k.arg: ast.unparse(k.value) for k in w.keywords}
            assert kw.get("from_dark") == "True" and (path.name != "main.py" or "clock" in kw), ast.unparse(w)
```
Safety test, EXACT, `tests/test_main.py:289-300` replaced by (the one named change; `FailingPushes`,
`playing_loop` as in the file):
```python
def test_after_a_failed_push_the_wall_holds_then_sends_the_counted_frame(tmp_path):
    """C51 (Q65, Q66): replaces it13's test of this place, which governed a new frame 0.05 s after the failure."""
    inner = FailingPushes({3})
    loop = playing_loop(tmp_path, inner)                          # call 1 at 0.05
    loop.step(0.25)                                               # call 2
    loop.step(0.5)                                                # call 3 fails: its frame was governed
    counted = loop.wall.last.copy()
    assert inner.count == 2 and loop.wall.governed == 2 and loop.wall.holding
    for t, count in ((1.0, 2), (1.5, 3), (2.0, 3), (2.5, 4), (3.0, 4)):
        loop.step(t)                                              # still; the counted frame at 1.5 and 2.5
        assert inner.count == count and loop.wall.governed == 2, t
    assert np.array_equal(inner.pushed[2], counted) and np.array_equal(inner.pushed[3], counted)
    loop.step(3.5)                                                # new frames again
    assert inner.count == 5 and loop.wall.governed == 3 and not loop.wall.holding
    loop.step(3.75)
    assert inner.count == 6                                       # one push a step again
```
Prose tests, `tests/test_wall_hold.py`: `test_without_a_clock_a_failed_push_does_not_hold` (the next push governs
and sends); `test_close_during_the_hold_sends_the_counted_frame_then_black` (no wait; closed); `test_a_held_loop_
step_counts_toward_the_dark_lights` (as `tests/test_main.py:303`: lights off after 10 s of held and failed steps,
relit at the first counted send that arrives). `tests/test_main.py:303-318` stays green unedited.

## I2 (the operator, in verify, after the review): from a clean detached checkout of the head
```
.venv/bin/python -m tools.show_shot --session strobe --seconds 6 --every-ms 150 --look plain --scale 1 --cols 4 \
    --out <s>/it14-strobe
.venv/bin/python -m tools.show_shot --session presses --every-ms 1000 --look both --out <s>/it14-presses
.venv/bin/python -m tools.show_shot --config show.poc.toml --session presses --every-ms 1000 --look both \
    --out <s>/it14-presses-poc
.venv/bin/python -m tools.show_soak --minutes 2 --press-every 5 --out <s>/it14-soak
.venv/bin/python -c "from arcade.config import load_config as l; print(l(__import__('pathlib').Path('arcade.toml')))"
```
Must show: strobe: every label `area 0.0000`, `sq <= 6`, held. Presses, full wall: held 0, at most 4 square flashes
(it13's; not worse); 128x64: Q60's holds as it13's. Soak: exit 0, governed = steps, failures 0, `squares_max <= 6`.
The arcade config: gamma 2.2. The hold never shows with fakes. The real panels (GATE C, the owner): Q66's check.

## Decisions
- Q65's text (resend every tick) is not enough: one tear at the budget's last change reads 7 (p4); the hold is quiet
  (Q66). `from_dark` is opt-in and passed by every caller (the AST test): priming by default changes `tests/test_
  wall.py:59-72`, `tests/test_wall_close.py:19-32`, `tests/test_main.py:406-416` (an unprimed reference governor).

## Questions for the owner (the loop takes each default at once)
- Q66 (it14): The hold after a failed push is quiet: nothing sent for 1 s, the counted frame, 1 s, the counted
  frame, 1 s, then new frames (3 s frozen per failure; a dead link is sent to once a second), not Q65's resend
  every tick. Default: yes, quiet. It needs the Colorlight card to keep its last frame through 1 s without packets;
  check on the real panels (stop the sender 3 s; the picture must stay, not blank). If it blanks, Q65's resend.
- Q67 (it14): May `arcade/runner.py` prime its governor with black at birth (C52 for the arcade)? It changes
  `tests/arcade/test_headless.py:227` (`len(governor) == 300` becomes 301: the priming is one more timed apply) in
  six cases; nothing else moved. Default: not changed (the arcade starts on the dark lobby).
