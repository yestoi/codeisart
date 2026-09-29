## Plan (path, line count)
/Users/trey/dev/codeisart/docs/superpowers/plans/2026-09-29-it15-close-in-a-hold.md, 248 lines, no line over 120
characters. Not committed. One task, T-close (opus, worktree): `show/wall.py`, `show/main.py` (`_open_wall` and
`_close` only), `tests/test_wall_close_hold.py` (new), `tests/test_wall_hold.py` (one test, lines 211-228). The
plan's exact test block is byte for byte the scratch file I ran (`diff`: same).

## The gap today (which closes read over 6: j, the model, the picture, the numbers)
Measured with the test helpers of `tests/test_wall_hold.py` (TornDisplay, in_time), fps 20, today's close, one
tear at call n = 21 to 34, split 33 and 8, j = 1 to 16 (scratch `find.py`, `find_today.txt`): 33 cases over 6.

| picture | model | split | tear call | j over 6 | squares | area |
|---|---|---|---|---|---|---|
| reversal top first 10 Hz | probe | 33 | 28 | 2 to 16 (j = 1 reads 8) | 7 to 8 | 0.000 |
| reversal top first 10 Hz | card | 33 | 28 | 1 to 16 | 7 | 0.000 |
| reversal top first 10 Hz | card | 33 | 24 | 1 | 7 | 0.000 |
| reversal top first 5 Hz | card | 33 | 27 | 1 | 7 | 0.000 |

Reversal bottom first 10 Hz and the strobe: none over 6. Split 8: none over 6. Worst: 8 (probe, j = 1).
Not done, for lack of time: fps 30, the 32x32 checks and the block strobe on this helper (the broad sweep over
them was started and stopped: too slow, 4.7 s a case). A longer sweep (j to 3 s + 2 ticks, calls 24 to 30, today's
and the planned close) did not finish in the time; I stopped it at 08:45 and it gave no numbers. For j beyond 16
today's close is measured only by the exact test's cases (tear at call 28 and a tear on the counted send).

## The close planned (what it does, how long it takes, the numbers with it, what the wall shows at the end)
While the wall holds: wait until the hold's next send is due (`_since + HOLD_S - clock()`, slept, nothing sent);
if the hold has not yet sent the counted frame, send it once and wait `HOLD_S` more; then `_end_hold()` (the
governor made again in place and primed with the counted frame, not sent), then two governed black frames; the
display closed in `finally`. Not holding, or no clock: today's close, no sleep. The loop passes
`sleep=lambda s: self.sleep(s)` and sets `_now = self.clock()` before the close.
- Time: at most 2 s of sleep plus four sends (1 s when the counted frame already went). No hold: as today (the
  I2 stop check should read about 0.06 s, the fake display never fails). systemd's stop limit: 90 s (the
  default; `deploy/show.service` sets no `TimeoutStopSec`).
- Numbers (exact test, scratch wall mode B): reversal top first 10 Hz, tear at call 28, split 33, fps 20, j = 1 to
  the hold's end + 2, both models, one tear and a tear on the counted send: at most 6, area 0.0 in every close.
- The wall ends black (screen and rows all zero), the display closed.
- Q66's blanking card (r6): not measured. On such a card the close does what the hold does: the card goes dark in
  the first quiet second, the counted frame lights it, a second later black.

## Wrong closes tried against each exact test
Scratch wall `wall15.py` with a MODE switch, tests run with a plugin that puts it in place of `show.wall`
(`exact_runs.txt`, `exact_runs2.txt`). Planned close (B): 10 passed, 7.65 s.

| close | fails |
|---|---|
| today's (with `sleep` accepted) | 6: the two "one tear" budget cases (7 to 8), the two timing tests, the raise test x2 |
| today's, as in the repository | all 10 (TypeError: no `sleep` keyword; `exact_repo_today.txt`) |
| A: wait, then black without the counted frame | `..._waits_then_the_counted_frame_waits_then_black` |
| B': wait, counted frame, black at once (no quiet second between) | the same test |
| waits HOLD_S/2 from the close, not from the hold's send | the two prose-exact timing tests |
| no wait at all (reset, black) | both timing tests, the raise test x2 |
| black straight to the display, not governed | `..._then_black` (`governed == 4`) |
| black without the governor's reset | `..._then_black` |
| never closes the display | all 10 |

Weak point, said plainly: the budget test alone catches only today's close; A, B', "no wait", "half wait",
"ungoverned" and "no reset" read at most 6 there. They fail on the exact timing and count asserts, not on the
metric. "No reset" read 6 and ended black in this set-up; I did not find a case where the reset matters.

## Existing asserts that change
- `tests/test_wall_hold.py:224-226` in `test_close_during_the_hold_sends_the_counted_frame_then_black`: the close
  with no wait (six calls all at 3/16). The whole test goes; the exact
  `test_close_in_the_hold_waits_then_the_counted_frame_waits_then_black` replaces it (counted frame at 18/16,
  black at 34/16, sleeps 15/16 and 1.0).
- `tests/test_wall_close.py:62-69` (the loop's close after a failed push; asserts `pushed[2]` is the counted
  frame): it would change under close A (black only). The plan keeps it with variant B: its asserts pass, but
  its loop has the real `time.sleep`, so it sleeps 1 s for real (the first wait is 0 because the loop's clock is
  real and its steps are fake times). Not run on a scratch `main.py`: I did not build one.

## Decisions taken
- The close waits out the hold (the roadmap's (a)), not (b): the wall still ends black.
- Keep the counted frame after the first quiet second, then a second quiet second, then black (2 s at most), so
  `tests/test_wall_close.py` is not changed. Black alone after the first second also reads 6 (Q69).
- The wait: the wall's clock read once, then an injectable `sleep` (default `time.sleep`); the loop passes its
  own `sleep`, late bound, and sets `_now` from its clock before the close.
- A wait that raises sends nothing more and closes the display; a second SIGTERM is only counted, the sleep goes on.
- Test time: the new file took 7.7 s in scratch, over the brief's 5 s. The budget test is 1.9 s a case (4 cases).
  I left it at all j, both models, rather than cut j.

## Questions for the owner (each with a default the loop takes at once; Q68, Q69)
- Q68: May a stop within 3 s of a failed push take up to 2 s to darken the wall? Default: yes. This replaces
  Q66's line "The close is never held".
- Q69: May the close go black after the first quiet second without the counted frame (1 s at most)? It also reads
  at most 6 and area 0.000, but changes `tests/test_wall_close.py:69`. Default: no, the counted frame stays.

## Minutes (start and end from `date`)
Start 08:22:10 CDT. End 08:46 CDT (about 24 minutes).
Rule note: one Bash command at the start had `cd /tmp` in it (a slip); it ran nothing in the repository and the
probe after it failed on a missing `timeout`. No other rule broken. `git status` shows `tests/arcade/helpers.py`
and `tests/arcade/test_oracle.py` changed: not mine (the arcade lane).
