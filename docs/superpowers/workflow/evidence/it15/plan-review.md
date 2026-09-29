## Verdict: BLOCKED

The planned close keeps the budget in every case I measured: 162,640 closes, worst 6, area 0.000. Two wrong closes still pass all 10 exact tests, and each one has a real effect: the wall ends lit, or the stop hangs. Each needs one small exact test, given below; I ran both. Nothing else blocks.

## Blocking findings

**B1. The exact tests do not guard step 3 (`_end_hold()` before the black).**
- The wrong close: the same as the plan, but step 3 only sets `self.holding = False`. The governor is not made again.
- It passes all 10 exact tests (`exact_noreset.txt`).
- The input: fps 20, a 5 Hz full-wall strobe (`strobe(5, 20, n)` from `tests/test_wall_hold.py`, lit first), card model, split 33, one tear at call 22 (tick 21). Then a close in the hold at j = 1, 21 or 41.
- What happens: the wall ends lit. It shows 1 square transition and area 0 (a still picture, not a flash). The governor counts its window in applies, not seconds. So it still holds the pre-tear second and holds the black back.
- The numbers: `sw_noreset_strobe.txt`: 3 held closes end lit. With the plan's close, the same closes end black (0 lit).
- The plan's reversal case cannot see this: there, even the wrong close ends black (`sw_noreset.txt`, 2,200 closes).
- What the plan must say: add this exact test. It takes 0.07 s. The plan passes it; the no-re-init close fails it (`extra_runs.txt`).
```python
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
```

**B2. A wait that reads the wall's clock again passes every exact test, but hangs the real stop.**
- The wrong close: `due = self._since + HOLD_S; while self._clock() < due: self._sleep(due - self._clock())`.
- It passes all 10 exact tests (`exact_whileclock.txt`). In every exact test the fake sleep moves the fake clock.
- In the real show, the wall's clock is `lambda: self._now`, and `_close` sets it only once. `time.sleep` never moves it, so the close never ends.
- The numbers: `hang.py` runs `loop._close()` with the loop's clock at 0.2 and a hold from 0.15. The plan's close sleeps 0.95 s and 1.0 s, then makes 5 sends and closes. The wrong close made 50 sleeps of 0.95 s and sent nothing; the probe stopped it there.
- In the real show, the stop hangs until systemd kills the service at 90 s. The wall stays as the tear left it (lit).
- The plan's text says "the clock is read once", but only a prose test (the loop's close) would catch this, and only if it is written that way.
- What the plan must say: add this exact test. It takes under 0.1 s. The plan passes it; the wrong close fails it (`extra_runs.txt`).
```python
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
```

## The six points

1. **The budget: kept.**
   - How I built it: a scratch copy of `show/wall.py` with the close taken literally from the plan. The clock is read once. The counted frame goes only when `_settled == 0`, then `sleep(HOLD_S)` whatever the send did. Then `_end_hold()`, then two `_govern(black)`, with `display.close()` in `finally`.
   - What I swept: 162,640 closes (49,249 different send sequences).
     - The 19 pictures of r1pics; fps 20 and 30; probe and card models.
     - One tear at calls 1 to 22, split 33.
     - Splits 8, 20 and 56 at calls 15 to 22.
     - A tear on the first counted send, a tear on the second, and a second tear on the first new frame after the hold (calls 15 to 22, split 33).
     - Every j from 1 to the last hold's end plus 1 s plus 2 ticks. This includes closes at the hold's end and 1 and 2 ticks after it.
   - How I measured: every window that ends at or after the close's first send, the close's own frames included.

   | what | result |
   |---|---|
   | worst square transitions | 6 (fps 20 and 30, both models) |
   | flash area | 0.000; the `#` band reads 0.063 / 0.078 / 0.094, the same with no tear (`hash_notear.txt`) |
   | held closes that end lit | 0 |
   | closes that leave the display open | 0 |
   | longest sleep | 1.95 s at fps 20, 1.967 s at fps 30 (the test clock rounds up to ticks) |

   - Also measured:
     - A full-wall strobe at 10 Hz and 5 Hz: 6.
     - The close's own counted send tearing: no held close over 6.
     - Today's close in the same sweep: 8 (C53 reproduced).

2. **The exact tests: not enough yet.**
   - 12 wrong closes tried. 8 fail at least one exact test.
   - 4 pass all 10:
     - no re-init: B1.
     - a wait that reads the clock again: B2.
     - a re-init with no priming: it gives the same sends and the same wall. Black is a fresh governor's first frame, so it passes. No display test can see it.
     - no quiet second after a failed counted send: only the prose test catches it. It read the same as the plan in my sweep.

3. **The real show.**
   - The longest stop is about 2 s plus 3 sends. Measured with the real `time.sleep` and a second SIGTERM during the wait: 1.96 s. The handler counted the signal (`seen` 2), the sleep went on, and the close sent black and closed the display.
   - `deploy/show.service` sets no `TimeoutStopSec`, so systemd's default of 90 s applies. `WatchdogSec=15` is not reached.
   - Ctrl-C during the wait: KeyboardInterrupt after 0.30 s. Nothing is sent after the tear and the display is closed. The wall stays as the tear left it, not black.
   - A failed counted send in the close is logged and the close goes on. A failed black send raises after the display is closed, and `_close` logs it.
   - The close cannot wait forever as the plan words it, but only B2's test makes that sure.
   - With no clock (`tools/wall_pattern.py`), the wall never holds and the close never sleeps (exact test).

4. **The close when the wall is not holding is unchanged.**
   - 155 existing tests pass on the scratch wall and main: `test_wall_close`, `test_wall_hold`, `test_wall`, `test_main`, `test_wall_pattern_governed`, `test_show_soak`.
   - `tests/test_wall_close.py:62-69` now sleeps a real 1.04 s (0.03 s today), as the plan says.
   - The replaced test in `test_wall_hold.py` is stronger than the old one. It keeps every old assert except the send times, and adds the sleeps, the counted frame at 18/16, black at 34/16, and `not holding`.

5. **Q66 (a card that blanks with no packets).** The close does what the hold does. The card goes dark in the first quiet second, the counted frame lights it again, and black follows 1 s later. That is no worse than the hold itself. Today's close sends the counted frame and black right after the tear, which reads 7 to 8. I did not measure it with r6.

6. **The form.**
   - 248 lines, none over 120 characters. Every file of the task is listed.
   - No frozen file is touched: `arcade/`, `deploy/`, `show/display/colorlight.py`.
   - The exact tests are slow: 13.7 s here and 7.7 s for the writer, over the 5 s allowed. See the notes.

**Not covered, point by point (notes, not guesses):**
- Point 1:
  - Splits 8, 20 and 56 at calls 1 to 14.
  - The two-tear sets (c1, c2, new) at calls 1 to 14 and at splits other than 33.
  - Tears 4 or more calls apart after the hold.
  - The close's own counted send tearing: only at fps 20/30, splits 8/33, calls 18 to 26, 7 pictures.
- Point 3: SIGINT and SIGTERM were measured in one process, not under systemd.
- Point 4: only the six test files named, not the full suite.
- Point 5: r6 was not run.
- Point 6: the exact tests' time was taken once, while another lane was building.

## Wrong closes tried against the exact tests

| wrong close | exact tests that fail |
|---|---|
| today's close (with `sleep` accepted) | 6: both "one tear" budget cases, both timing tests, the raise test x2 |
| a wait from the close's call (HOLD_S/2), then the counted frame, 1 s, black | 3: budget "one tear"-probe, both timing tests |
| no first wait (the counted frame, 1 s, black) | 5: budget "one tear"-probe, both timing tests, the raise test x2 |
| wait, the counted frame, black at once (no quiet second) | `..._waits_then_the_counted_frame_waits_then_black` |
| wait, black with no counted frame | the same test |
| black sent straight to the display (not governed) | the same test (`governed == 4`) |
| the display closed only when nothing raised | the raise test x2 |
| a real `time.sleep` in place of the given `sleep` | 6: both budget "one tear" cases, both timing tests, the raise test x2 |
| no re-init before the black (`holding = False` only) | passes all: **B1** |
| a wait that reads the clock again (`while clock() < due`) | passes all: **B2** |
| a re-init with no priming | passes all. Same sends and same wall in every case; not a finding |
| no quiet second after a failed counted send in the close | passes all. Only the prose `Clocked({3, 4})` test catches it; it read the same as the plan |

## Notes (not blocking, one line each)

- The exact budget test measures a slice, `seq[(k - fps) * (n // fps):]`, so its flash tracker starts cold. In my sweep a cold tracker counted 7 where the whole run read 6 (`tail7.txt`, `slice_check.txt`), and in principle it could also miss a swing. Better: warm the tracker on the second before and count only the windows that end after the close starts (`after()` in `sweep.py`).
- Test time (a note): while the wall holds, closes in the same phase send the same frames at the same ticks. So the budget test can close only at j = 1, the tick after each counted send, and the hold's end from -1 to +2. That is about 8 closes per case instead of about 65, with the same strength. In my sweep, 162,640 closes gave only 49,249 different send sequences.
- `tests/test_wall_close.py:62-69` sleeps 1 s for real. One line, `loop.sleep = lambda s: None` before `loop._close()`, removes it with no assert changed. The plan would then list that file as owned for that one line.
- The old `test_close_during_the_hold_sends_the_counted_frame_then_black` still passes with the planned close, after a real 1.95 s sleep, because its fake clock never moves. The plan says those asserts fail; replacing the test is still right.
- `deploy/README.md` ("Stop") says the daemon sends two black frames, then exits. After a failed push the stop now takes up to 2 s. `deploy/` is not to be touched, so this is for the owner.
- Ctrl-C during the wait leaves the wall as the tear left it (lit), as a second Ctrl-C during today's close would.
- The sweep first showed 7s at its last swept tick and in a close whose black send tears. Both came from the cold tracker on a slice; the whole run reads 6 (`tail7.txt`, `closetear_today_whole.txt`). Nothing new there.

## Probes (file names) and minutes

- Folder: `scratchpad/it15-plan-review/`
- Scratch wall and main, loaded in place of the real ones by `plug.py`: `wall_p.py` (the planned close, plus the wrong closes), `main_p.py`.
- Test files: `test_exact.py` (the plan's exact block, the same bytes as in the plan), `test_extra.py` (the B1 and B2 tests).
- Test runs: `exact_<mode>.txt` for each close (12 wrong closes and the plan), `extra_runs.txt`, `existing_plan.txt`, `sleepy_plan.txt`, `sleepy_today.txt`.
- Sweeps: `sweep.py`, `pics.py` (r1pics plus 2 full strobes), `run_sweeps2.sh`, results in `sw2_plan_all.txt`. The first sweep, with the cold tracker, is in `sw_plan_all.txt`. Also `sw_noreset*.txt`, `sw_whileclock.txt`, `sw_closetear_*.txt`, `sw_check_*.txt`.
- Other probes: `hang.py` / `hang.txt`, `tail7.py`, `slice_check.py`, `tailtear.py`, `closetear_today.py`, `hash_notear.py`, each with its `.txt`.
- Time: start 08:46:17 CDT, end 09:28 CDT, about 42 minutes. That is over the 20 asked for: I had to re-run the sweep after finding the cold-tracker artifact.
- Rules: no file in the repository changed; no `cd`; nothing under `deploy/` was run; `research_notes/` and `reports/` were not opened.
