## Verdict: CONFIRMED

## B1 and B2 (lifted or not, with the numbers)
- **B1 is lifted.** Plan lines 58-60 say everything an implementer needs:
  - the re-init is IN PLACE, with shape, gamma and fps;
  - `held_ticks` is carried;
  - `apply(self.last)` runs once and is not sent;
  - all of this happens at the hold's end, before that push governs its frame.
  - Line 61 adds that `SETTLE_SENDS` restarts from 0 after a failed counted send.
- **I tried three wrong walls that a careless reading could build. The plan's tests catch all three:**

| wrong wall | tests it fails (of 66) |
|---|---|
| re-init without the apply (`wrong_reinit.py`) | 10 |
| re-init primed with the NEW frame instead of `self.last` (`round2/wrong_primenew.py`) | 9: the one-tear test 8 of 8, and the AST test |
| no re-init (the planned wall before the fix) | 10 |

  - Priming with the new frame passes the timing test, because the spy records times, not frames. The one-tear test still catches it.
  - A re-init at the hold's start rather than its end would be just as safe, because nothing is applied during the hold. The timing test's `applied` list catches it anyway.
- **B2 is lifted.** I took the test block from the PLAN's text (`round2/plan_block.py`, 158 lines) and ran it against each wall (`round2/r1_plan_block.txt`):

| wall | result |
|---|---|
| my fixed wall (`reset_inplace.py`) | 65 passed, 1 failed (the AST test, because the repository is unchanged) |
| the planned wall without the fix | 10 failed: one-tear 8 of 8, timing 1, AST 1 |
| `wrong_reinit.py` | 10 failed: one-tear 8 of 8, timing 1, AST 1 |

- **Dropping the (5, 20) case is safe.** I restored (5, 20) and ran 10 walls (`round2/r2_five_twenty.txt`). No wall fails on (5, 20) at all, so no wall fails only there. The walls were: the fix, the planned wall, `wrong_reinit`, and the writer's modes repush, still, apply, none, undark, primefirst and sendblack.

## Points 3 to 5
- **3. The new numbers are right on the fixed wall.**
  - The timing test asserts `applied == [k / 16 for k in [*range(17), 64, 64, 65, 113, *range(113, 160)]]` and `wall.governed == len(applied) - 4`. It passes (part of the 65 above).
  - The replacement loop test, taken from the plan, runs with its new `inner.pushed[4] == loop.wall.last`. It passes with the fixed wall and the plan's loop in memory (`round2/r4_loop_block.txt`, 1 passed).
- **4. The time fits, with a thin margin.** One run of the plan's file on the fixed wall took 9.13 s in pytest (9.34 s wall clock). That is under T-wall's 9.5 s and the 10 s for new tests. The suite goes to about 234-240 s, under 250 s.
- **5. Yes, the plan now says what my report found.**
  - Q66 now says a blanking card breaks the budget (7 to 8, area 0.5), calls the panel check a SAFETY GATE, and says Q65's resend reads 7 too.
  - The Decisions line carries a close within a second of a tear (8 on a reversal at budget) as C53, not planned in this slice.

## New blocking findings (plan line, the evidence, the smallest fix)
None.

## Notes
- The time margin is 0.2-0.4 s on the Mac. A slower worktree run could pass 9.5 s. If it does, drop one `hz,fps` pair from `test_torn_pushes...`, because none of those cases catches a wall the one-tear test does not.
- In this set, only the one-tear test catches the post-hold faults. The 4 x fps torn test catches only today's wall and the unprimed walls.
- After the re-init, the soak's `timed_apply` wrapper also times the priming apply, one extra apply per hold. This is harmless.

## Minutes
Start 07:20, end 07:24 CDT: 4 minutes. The repository is unchanged. The probes are in `scratchpad/it14-plan-review/round2/`.
