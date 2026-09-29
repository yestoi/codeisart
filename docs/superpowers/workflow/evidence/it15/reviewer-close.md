## Verdict: APPROVED

Lane B (16dbb91..01bfd95) does what the plan says. Every probe ran against the real `show.wall.GovernedDisplay` and the real `ShowLoop`. Across 178,236 closes the worst reading is 6 square transitions, with area 0.000 (only the `#` band reads more, and it reads the same with no tear). Every close in a hold ends black with the display closed. The longest wait is 2.0 s. The exact tests are the plan's, node for node.

## Blocking findings (file:line, the input, what happens, why it blocks)

None.

## Lane B, the close: the eight points (one short answer each, with numbers)

1. **The budget: kept, including the cases the plan review did not cover.**
   - The sweep (`sweep.py`) runs the real wall. One tick is one loop push, and the close's sleeps move the tick on. The measure is the whole run from dark (the tracker warm), in real time, at 2 slots a tick, with the close's wait and its own frames counted.
   - Held closes in the same phase send the same, so each is measured once. Unheld closes are measured at every tick up to the last hold's end plus 1 s plus 2 ticks.
   - Cross-check: 3,802 sampled closes were measured again with the full `in_time` + `square_flashes` / `flash_area`, and all agree.
   - Sanity check: the same sweep on the 16dbb91 wall (today's close) reads 8 at call 28, and at call 24 on the card (C53 reproduced, `sanity_oldwall.txt`).

   | sweep | pictures | fps | models | tears | splits | calls | closes | worst sq | area | held closes lit | open | longest sleep |
   |---|---|---|---|---|---|---|---|---|---|---|---|---|
   | s1 | all 21 (19 + 2 full strobes) | 20 | both | one | 33 | 1-22 | 24,024 | 6 | 0.000 (hash 0.063/0.078) | 0 | 0 | 1.95 s |
   | s1 | all 21 | 30 | both | one | 33 | 1-22 | 33,264 | 6 | 0.000 (hash 0.094) | 0 | 0 | 1.967 s |
   | s2 (not covered before) | 5 (rev b32 10 Hz, rev 5 Hz, checks off16 5 Hz, full 10 Hz, full 5 Hz) | 20 | both | one, c1, c2, new | 8, 20, 56 | 1-14 | 46,200 | 6 | 0.000 | 0 | 0 | 1.95 s |
   | s3 (not covered before) | the same 5 | 20 | both | second tear at n+4, 5, 6, 8, 12, 20, 30 | 8, 33 | 18-22 | 26,700 | 6 | 0.000 | 0 | 0 | 1.95 s |
   | s4 (not covered before): the close's counted send tears | all 21 | 20 | both | one | 8, 33 | 1-22 | 48,048 | 6 | 0.000 (hash 0.063/0.078) | 0 | 0 | 1.95 s |

2. **The wait: correct, and it ends.**
   - `show/wall.py:134` reads the clock once, before the first wait. There is no loop, and the only other sleep is `HOLD_S` at :142.
   - `show/main.py:190` and `:200-201` pass `sleep=lambda s: self.sleep(s)` (late bound). `show/main.py:427` sets `self._now = self.clock()` right before `self.wall.close()`.
   - Real `time.sleep` and `time.monotonic` (`realclose.txt`):

   | case | stop time |
   |---|---|
   | close in the hold at the tear | 2.003 s |
   | 0.6 s after the tear | 1.398 s |
   | after the first counted send | 0.784 s |
   | the real `run()` stopped by SIGTERM 0.35 s in (tear at call 3) | 1.770 s from the signal to the end, exit 0 |

   - Each case sends the counted frame, then black, black. It ends black and the display is closed.
   - The wait is `_since + 1 - now`. `_since` is an earlier step's `_now`, taken from the monotonic clock, so the wait is at most 1 s, and there is one more `HOLD_S`. At most 2 s plus the sends. No path waits forever.

3. **The governor before the black: correct.**
   - `_end_hold()` (`show/wall.py:143`) runs before the two `_govern(black)`. It makes the governor again and primes it with `_last`, unsent.
   - The plan's B1 test passes: a 5 Hz full strobe, the card model, a tear at call 22, a close at tick 22 ends black.
   - In the sweeps, both full strobes (5 and 10 Hz) and every picture give 0 held closes that end lit, at fps 20 and 30, on both models.

4. **Failures in the close: the display is closed in every case, and nothing is sent early.**

   | failure | what happens |
   |---|---|
   | the counted send fails | Logged. The close sleeps 1 s after it, then two blacks. 2.010 s, ends black, closed. |
   | the first black fails | Raises inside the close, `_close` logs it, the display is closed (calls 5). The wall is left at the counted frame, not black: the display failed. |
   | Ctrl-C (SIGINT) at 0.3 s into the wait | KeyboardInterrupt at 0.305 s. Nothing sent after the tear (calls 3), closed. As the plan says. |
   | a second SIGTERM at 0.3 s | Counted (`seen` 2). The sleep goes on (1.996 s), then black, closed. |

   - The exact tests cover KeyboardInterrupt and OSError raised from the wait (calls 3, closed).

5. **Not holding, and no clock: unchanged.**
   - Not holding: the close took 0.001 s, with no sleep called, then black, black, closed.
   - No clock: `tools/wall_pattern.py:204` passes no clock and no sleep (checked by the AST test). The exact test `test_a_close_without_a_clock_never_waits` passes. `tools/` is untouched.

6. **Every path to a display: only `_send` (`show/wall.py:157`).**
   - `_send(` is called at :110 (`_govern`) and :117 (`repush`, the counted frame, already governed).
   - Nowhere else in `show/*.py` pushes to a display.
   - There is no alias, `getattr`, stored bound method or lambda that sends. The new `_sleep` sends nothing.

7. **The exact tests: unchanged.**
   - The AST compare (`exact_compare.txt`) finds all 20 nodes of the plan's block (8 test functions, 12 collected) identical in `tests/test_wall_close_hold.py`. Only layout differs.
   - The file adds the 4 prose tests and 3 imports.
   - In `tests/test_wall_hold.py`, only `test_close_during_the_hold_sends_the_counted_frame_then_black` is removed, with a comment in its place.
   - `tests/test_wall_close.py` gets exactly one line, `loop.sleep = lambda s: None`, and no assert changes.
   - Test runs: `test_wall_close_hold.py` 16 passed (2.45 s), `test_wall_hold.py` 68 passed, `test_wall_close.py` 7 passed. 0 skipped.
   - Collected on main now: 1311. The Quick Draw fix c99d463 adds 3 tests (not parametrized), so 01bfd95 has 1308 = 1293 + 12 + 4 - 1. There is no drop.

8. **The frozen files: untouched.**
   - `git diff 0dae849..01bfd95 -- arcade/flash.py arcade/brightness.py show/display/colorlight.py` is empty.
   - `git diff 16dbb91..01bfd95 --stat -- deploy/ tools/` is empty.
   - Main moved to 44a9dd2, but nothing in `show/` or `tests/test_wall*` changed after 01bfd95.

## Removed or changed asserts

All five are from the one test the plan names, `tests/test_wall_hold.py::test_close_during_the_hold_sends_the_counted_frame_then_black`, which was removed. Its replacement is `test_close_in_the_hold_waits_then_the_counted_frame_waits_then_black` in `tests/test_wall_close_hold.py`.

| removed assert | in the replacement |
|---|---|
| `wall.push(frames[3]) is None and wall.holding` | kept |
| `inner.closed and inner.calls == 6 and not wall.unsent` | kept, plus `not wall.holding` |
| `[t for t, _ in inner.sent[2:]] == [3 / 16] * 3` | changed as the plan says, to `[18/16, 34/16, 34/16]` with sleeps `[15/16, 1.0]` |
| `np.array_equal(inner.sent[2][1], counted)` | kept |
| `not inner.sent[3][1].any() and not inner.sent[4][1].any() and wall.governed == 4` | kept |

No other assert in `tests/` was removed or changed in 16dbb91..01bfd95.

## Noted, not carried (one line each)

- Unheld closes after the hold's end (today's close, the it13 behaviour) often end lit on strobes, because the governor holds the black back. They read at most 6, so this is not lane B's.
- The first black failing leaves the wall at the counted frame. This is the display's failure, and it is logged and closed as the plan says.
- `show/main.py:427`: if `self.clock()` raised, the wall would not be closed. `time.monotonic` does not raise, so this is not a finding.
- One of my Bash commands had a no-op `cd /tmp` in it (`; cd /tmp >/dev/null 2>&1; true`), against the rule. It changed nothing.

## Not covered

- fps 30 for sweeps s2, s3 and s4 (the new cases were run at fps 20 only; s1 ran at both).
- Pictures other than the 5 named in s2 and s3.
- s3 was run only at calls 18-22.
- Splits 20 and 56 for the close's own tear (s4 ran splits 8 and 33).
- Under systemd, and r6 / Q66's card: not run.
- The full suite was not run (operator's), so the suite-wide skip count was not measured. The three lane B files skip 0.

## Probes (file names) and minutes

- Folder: `scratchpad/it15-review-close/`.
- `sweep.py` (the real wall, whole-run warm measure, cross-check), with `pics.py` copied from the plan review.
- Outputs: `s1_one_33_fps20.txt`, `s1_one_33_fps30.txt`, `s2_splits_twotears_fps20.txt`, `s3_gaps_fps20.txt`, `s4_closetear_fps20.txt`.
- Sanity check: `sanity_oldwall.txt`, with `old_wall.py` = `git show 16dbb91:show/wall.py`.
- `realclose.py` / `realclose.txt`: the real `ShowLoop._close()` and `run()`, real sleep, SIGTERM and SIGINT.
- `exact_compare.py` / `exact_compare.txt`.
- `tests.txt`, `collect.txt`.
- Time: 10:34 to 10:58 CDT, about 24 minutes. One process at a time, with no file in the repository created or changed.
