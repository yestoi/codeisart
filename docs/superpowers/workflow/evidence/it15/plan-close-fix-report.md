## What changed in the plan (line count after)
The plan is /Users/trey/dev/codeisart/docs/superpowers/plans/2026-09-29-it15-close-in-a-hold.md. It is now 297 lines, no line over 120 characters, not committed. The exact block is byte for byte the scratch file I ran (checked by a string compare).

- **Exact block:** two tests added, B1 and B2, as the review gives them. The budget test now closes only at the `phases` ticks and measures the whole run from dark.
- **"The close planned", step 1:** says in plain words that the clock is read ONCE, before the first wait, and never inside a loop. The reason: the loop's wall clock is `self._now`, which no sleep moves. A close that reads it again never ends, and the stop hangs until systemd kills it.
- **Owners:** `tests/test_wall_close.py` is now T-close's, for one added line only.
- **"The changed test":** corrected. The old test would still pass after the planned close (it sleeps a real 1.95 s, because its fake clock never moves). It is replaced because it asserts a close that does not wait.
- **Global constraints and Steps:** now 12 exact tests, 2.8 s; today's close fails 8.
- **Decisions:** two lines added. One on the budget test's `phases` and its warm measure. One on `deploy/README.md`'s "Stop" text: this task does not change it, and the owner is told that a stop after a failed push takes up to 2 s.

## B1 and B2 (the test, what passes it, what fails it, the seconds)
The runs are in scratch `it15-plan-close/fix_runs.txt`.

| test | planned close (B) | fails it | time |
|---|---|---|---|
| `test_a_close_in_the_hold_ends_black_when_the_governor_is_at_the_budget` (B1) | passes | the close without the re-init (`noreset`: `holding = False` only); today's; never closing the display | under 0.1 s |
| `test_a_close_in_the_hold_reads_the_clock_once` (B2) | passes | the close that reads the clock again (`whileclock`: `while clock() < due`, capped at 50 sleeps in the scratch wall); also today's, A, B', half wait, no wait, ungoverned, never closing | under 0.1 s |

Every wrong close against the 12 exact tests:

| close | exact tests failed |
|---|---|
| today's (with `sleep` accepted) | 8 |
| A (wait, black, no counted frame) | 2 |
| B' (no quiet second before black) | 2 |
| waits HOLD_S/2, no counted frame | 3 |
| waits HOLD_S/2, then counted frame, 1 s, black | 4 (the budget "one tear"-probe case among them) |
| no wait, no counted frame | 5 |
| no first wait, then counted frame, 1 s, black | 6 (the budget "one tear"-probe case among them) |
| black not governed | 2 |
| no re-init | 1 (B1) |
| clock read again | 1 (B2) |
| never closes the display | 12 |

## The notes taken and not taken
- **(a) Taken.** `tests/test_wall_close.py:62-69` gets one line, `loop.sleep = lambda s: None`, before `loop._close()`. No assert changes. I did not run it on a scratch `main.py`. It works only because the plan passes the wall `sleep=lambda s: self.sleep(s)`, late bound.
- **(b) Taken.** The sentence on the old test is corrected, as above.
- **(c) Taken.** The budget test closes at `phases(tear, fps)` = {tear+1, tear+2, the tick after each counted send (tear+fps+1, tear+2·fps+1), the hold's end −1 to +2}. For the counted-send tear these ticks are taken from the second hold. Today's close still fails both "one tear" cases, and the planned close passes all 4.
- **4. Taken.** The measure is now the whole run from dark, so the flash tracker is warm: no cold slice, and every window of the run is counted. It is not the review's `after()`: it counts the windows before the close too, which the hold's own tests already hold at 6 or under. I ran every wrong close of my table again against the changed test (above).
- **Not taken:** the review's other notes, beyond the Decisions line on `deploy/README.md` and the note that Ctrl-C during the wait leaves the wall as the tear left it (that one was already in the plan).

## The exact tests' time
The whole new file takes 2.81 s on the planned close (12 passed). The slowest cases are the budget test at 0.61 to 0.76 s each (4 cases); B1 and B2 are under 0.1 s each. Before this fix the file took 7.65 s.

## Minutes
Start 09:27:51 CDT, end 09:30 CDT, about 3 minutes.

No `cd` was used. Nothing in the repository changed but the plan. Nothing under `deploy/` was run. No probe is left running.
