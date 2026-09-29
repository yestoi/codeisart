## Plan (path, line count)
- `/Users/trey/dev/codeisart/docs/superpowers/plans/2026-09-29-it14-governor-gaps.md`
- 296 lines. No line is over 120 characters. Not committed. I edited no other file.
- `git status` also shows `decisions.md`, `roadmap.md` and `state.md` as modified. I did not touch them.

## B1 (what changed in the plan, the probe's numbers with the fix)
I took the reviewer's fix.
- `push` interface: when the hold ends, before that push governs its frame, `self.governor.__init__(h, w, gamma, fps=fps)` runs in place. `held_ticks` is carried over. Then `governor.apply(self.last)` runs once, and that frame is not sent. The plan says why: after a tear, a square's direction on the wall differs from the governor's. Once the direction is unknown again, the next move counts whichever way it goes. Doing it in place keeps the soak's wrapper and the test spies.
- The old line "the governor during the hold ... stricter in seconds, never laxer" is gone. That argument was wrong for a torn square.
- My scratch wall with the fix is `it14-plan/fix/wall14b.py` (mode `fix`).
- I ran the reviewer's r1 sweep on it at fps 20 (`fix/p5_sweep_fix.py`, output `fix/p5_sweep_fix_20.txt`): 19 pictures x 120 tear cases x 2 models (card and probe).

Worst square count (flash area) over the 120 tear cases. Both models give the same numbers.

| picture | planned wall, no fix (review r1) | with the fix |
|---|---|---|
| reversal, rows 32 / 48, top first, 10 Hz | 7 (0.000) | 6 (0.000) |
| reversal, rows 24 / 32, top first, 5 Hz | 7 (0.000) | 6 (0.000) |
| 32x32 checks, offset 0 / 16, 10 Hz and 5 Hz | 7 (0.000) | 6 (0.000) |
| the other row reversals, columns, block strobe | 6 or less | 6 (0.000) |
| scroll 1 row / 3 rows | 2 / 3 | 2 / 3 (0.000) |
| scrolling `#` band | 0 (0.063) | 0 (0.063): Q13's small-area rule, not the hold |

With the fix no case reads over 6. The sweep took 252 s.

I did not run fps 30 (time). The reviewer's r3 already showed the 8 fps-30 cases that read 7 going to 6 with the same fix.

## B2 (what changed in the tests, which walls fail and pass them, the measured seconds)
Changes to the exact test text:
- `test_one_torn_push...`: `split` is parametrized over 24 and 33. It uses `reversal(10, 20, 120, top_first=True)` and `split=split`. That is 8 cases.
- `test_torn_pushes...`: `pattern(hz, fps, 4 * fps)`. To stay near the time limit I dropped `(5, 20)`. No wrong wall fails only on `(5, 20)`.
- The timing test: `applied == [k / 16 for k in [*range(17), 64, 64, 65, 113, *range(113, 160)]]` and `wall.governed == len(applied) - 4`. My scratch wall with the fix gives exactly these values, the same as the reviewer's.
- The AST test: `kw.get("clock") not in (None, "None")` for `main.py`. It is split into two asserts, with the same meaning.
- Blank lines between definitions in the test block were removed. Only the layout changed.

The plan's test block (`fix/test_from_plan.py`, taken from the plan) and the same tests in `fix/test_amended.py` against each wall. The AST test fails on every wall here because it reads the unchanged repository, so it is left out of the counts:

| wall | result |
|---|---|
| fix (the plan) | all pass (65 of 66; only the AST test fails) |
| quiet (the plan before this fix) | 8 one-torn cases fail, plus the timing test |
| noprime (the reviewer's `wrong_reinit`: re-init, no apply) | 8 one-torn cases fail, plus the timing test |
| repush (Q65's text) | 8 one-torn cases, the timing test |
| still (one counted send) | 6 one-torn cases, the timing test |
| apply (the governor is fed the held frame) | the timing test |
| none (today's wall) | 2 torn-push cases (reversal 5 Hz fps 30), the timing test |
| undark (no priming at birth) | 8 from-dark, 8 one-torn, 4 torn-push |
| sendblack (black is sent at birth) | 8 from-dark, 8 one-torn, the timing test |
| primefirst (the first frame is applied twice) | 8 from-dark, 8 one-torn, 4 torn-push, the timing test |

- Replacement test in `tests/test_main.py`: it adds `assert np.array_equal(inner.pushed[4], loop.wall.last)` after `step(3.5)`. The test taken from the plan passes with my in-memory loop plugin (`plug/test_loop_from_plan.py`: 1 passed).
- Measured time for the whole new file on the fixed wall: 8.04 s and 8.84 s in two runs on an idle machine (`fix/fix_timing.txt`). A third run took 16.3 s, but it ran while the sweep was using the CPU. The plan now says: new tests 10 s at most, T-wall 9.5 s.

## Notes folded in
- The AST test now uses `kw.get("clock") not in (None, "None")`.
- `push`'s interface says a counted send that fails starts the hold again, with `SETTLE_SENDS` counted from 0.
- The replacement test asserts that the frame sent at 3.5 is the step's governed frame (`inner.pushed[4]` against `loop.wall.last`).
- Q66 now says a card that blanks without packets breaks the budget during a hold (review r6: 7 to 8 transitions, flash area 0.5). So the owner's check on the panels is a SAFETY GATE. If the card blanks, the wall is not shown to the public until a hold that stays in the budget is found. Q65's resend is no fallback: it reads 7 as well.
- Decisions has one new line: B1 is taken, and a close within a second of a tear is carried as C53 and not planned here.

## Anything you could not do
- I did not run the fix sweep at fps 30 (time). The reviewer's r3 covers the 8 fps-30 cases that read 7.
- The new test file takes 8.0 to 8.8 s. That is over the old 8 s. The plan's allowance is now 9.5 s for T-wall and 10 s in all.
- Nothing was refused by the harness.

## Minutes (start and end from `date`)
- Start 07:10:32 CDT. End 07:19:40 CDT (about 10 minutes).
