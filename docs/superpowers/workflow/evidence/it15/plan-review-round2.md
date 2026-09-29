## Verdict: CONFIRMED

Both blocking findings are fixed. I ran every check; I did not only read the plan.

## B1 and B2 (lifted or not, the runs)

**Both lifted.**

- The plan's two tests are byte for byte the ones I gave. They sit right after the budget test (`diff` shows no difference).
- I took the plan's exact block as it stands now into scratch as `test_exact2.py` (178 lines) and ran it on my scratch wall.

| close | the 12 exact tests |
|---|---|
| the planned close | 12 passed |
| no re-init (`holding = False` only) | fails B1's test, 1 failed |
| reads the clock again (`while clock() < due`) | fails B2's test (the 3rd sleep asserts), 1 failed |

## The changed budget test

**At least as strong as the old one.**

1. **It measures more.** It now measures the whole run from dark, so the flash tracker is warm and every window is counted. The old test counted only windows from a second before the close.

2. **It leaves out no close that sends differently.**
   - I closed at every tick of round 1's range in the test's two drives, both models, and hashed each close's sends (ticks and bytes).
   - That gives 16 different send lists. Every one has a tick in `phases()` (`phases_check.txt`).
   - One tick has no `phases` tick of its own: tick 47 of the "counted send tears" case. Its sends are the same as the "one tear" case's closes at ticks 28 to 67, and those are covered.
   - Within a phase of the hold, every close sends the same.
   - My earlier count of 49,249 different send lists was over the whole sweep; for this test's drives the count is 16.

3. **Every wrong close from round 1 still fails at least one test** (`r2_exact_<mode>.txt`):

| close | round 1 | round 2 (12 tests) |
|---|---|---|
| today's close | 6 failed | 8 failed, both "one tear" budget cases among them |
| a wait from the close's call | 3 | 4, the budget "one tear"-probe case among them |
| no first wait | 5 | 6, the budget "one tear"-probe case among them |
| a real `time.sleep` | 6 | 7 |
| no quiet second before black | 1 | 2 |
| black with no counted frame | 1 | 2 |
| black not governed | 1 | 1 |
| display closed only when nothing raised | 2 | 2 |
| no re-init | passed all | 1 (B1) |
| reads the clock again | passed all | 1 (B2) |
| re-init with no priming | passed all | passes all: same wall, not a finding (round 1) |
| no quiet second after a failed counted send | passed all | passes all: only the prose test catches it (round 1 note) |

**The one line in `tests/test_wall_close.py`:**
- The copy with `loop.sleep = lambda s: None` added before `loop._close()` differs from the file by that one line only.
- On the scratch wall and main, all 7 tests pass. The loop's close no longer sleeps a real second (it is not among the 3 slowest; the slowest took 0.33 s).
- Every assert stays, and so does its meaning. The close that sends black with no counted frame still fails `test_the_loop_s_close_after_a_failed_push_sends_the_counted_frame_first`.

## New findings (or "none")

None.

Notes (not blocking):
- The one line keeps the test fast only if `_open_wall` passes the loop's sleep late bound (`lambda s: self.sleep(s)`), as the plan says. An implementer who writes `sleep=self.sleep` gets a real 1 s sleep there, not a failing test.
- Plan form: 297 lines, none over 120 characters. The frozen files are still listed as not edited.

## The exact tests' time

- 2.40 s for all 12 when run alone on the planned close.
- The budget test takes 1.3 to 1.8 s per case when 13 runs share the CPU. B1 and B2 take 0.01 s each.
- That is inside the 5 s allowed. The writer measured 2.81 s.

## Minutes

- Start 09:30:34 CDT, end 09:33 CDT: about 3 minutes.
- Probes, all in `scratchpad/it15-plan-review/`:
  - `test_exact2.py`
  - `r2_exact_<mode>.txt` (the 12 tests against the planned close and 12 wrong closes)
  - `phases_check.py` / `phases_check.txt`
  - `test_wall_close_line.py` / `r2_wall_close_line.txt`
  - `r2_exact_time.txt`
- Nothing in the repository was changed. No `cd` was used, and no sweep was run.
