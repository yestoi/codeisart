# it07 orchestrator report

BASE 6ddaf78 (checked at start). Final HEAD a2e6681. The suite is green: 674 collected, 674 passed, 0 failed, 0 skipped, 0 xfailed, 132.5 s.

## Completed
- **S1** (opus, main checkout): 17ca145. Adds the callable feed for `run_headless`, `REQUIRED_SCENARIOS`, `fx: Juice` under TYPE_CHECKING and the docstring rules in `game.py`, the new `arcade/bots.py`, and the new `arcade/feel_budgets.toml`. Its tests are in test_headless (+2), test_game (+3) and test_bots (8).
- **P1** (opus): feel metrics, `arcade/feel.py` and `tests/arcade/test_feel.py`. Branch commit 0551d31, merged 7f71237.
- **P2** (opus): `arcade/pattern.py`, `tests/arcade/test_pattern.py` and `tests/arcade/test_all_games.py`. Branch commit 772dfc8, merged af86881.
- **P3** (sonnet): Pong's `canonical`, `idle_body` and `nobody` scenarios, `pong_bots.py`, `pong_feel.toml`, the Q23 score seat, and tuning (CPU_SPEED 24, BALL_START 60). Branch commit 9a69392, merged 1a493e1.
- **P4** (sonnet): `tools/arcade_evidence.py` and its tests. Branch commits 73974f5 and 94e0245 (the fix). The first merge a4a3c6d was reverted (a6aef84), sent back once, then reapplied (60f3989) and merged with its fix (8c750a4).
- **P5** (sonnet): `tools/arcade_shot.py` provenance header, captions with CAPTION_KEYS, `--allow-black`, `--look`, the 1,536 px cap and `--flash-report`. Branch commit 4091222, merged cf846e5.
- **P6** (opus): C37, `KeypointHold` in `arcade/figure.py`, with the lobby mirror drawing through it. Branch commit 1abfbf8, merged 387936a.
- **P7** (sonnet): `.claude/skills/arcade-game-authoring/SKILL.md`, 289 lines. Branch commit 3395ca7, merged 1014118.
- **I1**:
  - 4ede4a6 removes P2's two `xfail(strict=True, reason="until P3")` marks, which were its only edit to that file.
  - 8f68d07 adds `tests/arcade/test_oracle.py`: `test_feel_pong_meets_its_budgets` (`feel`), `test_bots_rank_on_pong` and `test_evidence_package_for_pong`. They share one module-scoped 20-seed `feel.report(Pong, "128x32")`.
- **Pong feel fix, round 1** (fresh sonnet agent, main checkout, Pong's files only): 35ae954. A body in view takes a CPU seat at once, mid-rally; before this it waited for the next serve. It adds `test_a_walk_up_takes_a_cpu_seat_at_once`. After it, Pong meets every budget. Round 2 was not needed.
  - Pong at 128x32 over 20 seeds: response_ticks 2.0 (max 2), fidelity 0.995, range 0.774, lit_fraction 0.022, dim_fraction 0.189 (override max 0.3, with a reason: the dim net), liveliness 0.0035, flash_area_raw 0, square_flashes 0, win_good 1.0, win_lazy 0.2, win_none 0.0, round_seconds 92.0, phases_reached 1.0. `failures == []`.
- **Stretch X1** (opus, main checkout): a2e6681. Adds `score_visible` (score kind, min 0.8; Pong 0.959), `score_legible` (the `distance` look at 5 m, score kind, min 0.9; Pong 1.0) and `idle_hint_seconds` (every kind, max 3; Pong 0.0). New tables only; no existing band changed.

## Deviations
- **P4's first merge broke the suite.** `_seeds` read `list(feel.FEEL_SEEDS)`, but P1 defines `FEEL_SEEDS = 20`, an int, so it raised TypeError. The merge was reverted with `git revert -m 1` and sent back once. The fix: `main` passes the `--seeds` int through to `report`, which draws `bots.seeds(game, layout, n)`, the plan's seed rule. A test was added. The fix was re-merged by reverting the revert and then merging the branch. As a result the merge order on main is P3, P1, P2, P4 (reverted), P5, P6, P7, then P4 again.
- **The xfail marks were removed before I1's test file was written.** P3 was merged before P2, so P2's strict xfails XPASSed at P2's merge (2 failed). I removed the marks at once (4ede4a6, I1's planned edit) instead of reverting P2.
- **Pong round 1 went to a fresh agent.** It first went to the P3 agent, which is bound to its worktree and could not commit on main; it made no change. On the operator's instruction a fresh main-checkout agent did it.
  - That agent's plan was for a second arrival to also take the remaining CPU seat at once. It did not do this, because the existing `test_second_player_joins_at_the_next_serve` asserts that player 2 waits for a serve. Only the first human is seated mid-rally.
- **P3 changed one existing assert.** `test_registered_and_declared`'s `set(Pong.SCENARIOS) == {"solo","duel"}` now lists the five scenarios, a necessary extension.
- **P3's `test_idle_body_scores_nothing` does not assert `score == 0`.** With CPU_SPEED 24 the CPU sometimes misses a still paddle, so an idle body banks 1 or 2 points on some seeds. It asserts that the round ends `over`, is not won, the CPU leads, and `score == left`.
- **X1 extended two existing asserts** (additions, to pin the new defaults):
  - the expected dicts in `test_bots.py::test_budget_file_parses_and_has_every_kind` (I allowed it);
  - the metric-key set in `test_feel.py::test_measure_repeats_under_seeds`.
- **X1 did not do the fail-versus-win transient.** It needs `fail`/`win` scenarios, or frames kept from bot plays.
- **X2 and X3: not started.** More than 60 minutes had passed when X1 finished.
- **Interface additions beyond the plan:**
  - S1's `play` also stops when the session ends otherwise (Nobody "left" after about 8 s).
  - `Move.x` is in zone coordinates.
  - P1's `measure` and `report` take a keyword-only `own=None`, and there is a public `own_file(game_cls)`.
  - P2 defines `BUDGET_MS` from env `ARCADE_TICK_BUDGET_MS` (default 2.0) in its test file; the constant existed only locally in test_headless.
  - P2 does not pass `hostile_mix` through `degrade`.
  - P5 adds keyword-only `caption_keys` and `cols`, and its black check ignores the bottom row (the runner's player marker).
  - P6 also resets the holds in `end_session`.
- **Process slips.** S1, P2, the Pong-fix agent, X1 and I each ran `cd` into the directory the shell was already in (read-only or test commands). Nothing outside the agent's own checkout changed.

## Findings for the review
1. **Suite time is 132.5 s, against 36.9 s at it06.** The biggest costs:
   - test_oracle about 55 s (the report fixture 48 s, the evidence package 7 s), within I1's 60 s;
   - test_pong about 22 s (`test_good_beats_lazy_beats_nobody` 11.7 s), over P3's 20 s;
   - test_feel about 11 s, test_all_games about 6 s per game, the lobby noise tests about 5 s.
   - P2: each game adds a third size (96x48), so about 9 s per future game, not 5.
2. **`response_ticks` for Pong is exactly at its max of 2.0, with no margin.** P1 warns that the metric depends on the input moving fast enough: the paddle is 2 px wide and RESPONSE_PX is 12.
3. **Pong's `round_seconds` median of 92 s is the 90 s time cap.** The good bot leads at the cap rather than reaching WIN_POINTS. win_good 1.0 and win_lazy 0.2 are inside the bands.
4. **X1's `idle_hint_seconds` is weak.** It only shows that the wall answers a still body. Pong's 0.0 comes from the CPU seat changing colour, not from a hint. `score_visible` can count the other side's digit when both sides show the same number. Pong draws its score at 1x, while spec 7.4 says scores use 2x. Its new budget numbers (0.8, 0.9, 3 s) are an owner question.
5. **Raw frames include the runner's overlays** (the `fx.render` player marker on the bottom row). `dim_fraction`, `liveliness` and `flash_area_raw` count them (P1), and P5 ignores the bottom row for its black check.
6. **C37 margin is small.** After P6, the reviewer-notes input gives raw `concurrent_area` 0.067 to 0.092 against SMALL_AREA 0.1 (worst 0.0918 at 128x32, person 3 at x 0.6). The remainder is keypoint jitter, not dropouts.
7. **An idle body can bank points in Pong** (P3), and `Scores.record` stores them at the end of a round.
8. **P4 has not been run end to end from the CLI on the merged tree.** The oracle's `test_evidence_package_for_pong` covers `package([Pong], ...)`; the operator's I2 command is the first CLI run. In worktrees `test_pose_mediapipe` skipped (no models/); in the main checkout it passes.
9. **Tick-budget and the other timing tests passed on every run here.** No reruns were needed.

## Test status (command + counts after each step, and the suite's seconds at the end)
Command, from /Users/trey/dev/codeisart: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs`

| Step | Result |
|---|---|
| Base 6ddaf78 (plan's figure at 5ed04f2) | 596 passed, 36.9 s |
| After S1 (17ca145) | 609 passed, 38.4 s |
| After P3 merge | 617 passed, 52.4 s |
| After P1 merge | 626 passed, 61.0 s |
| After P2 merge | 639 passed, 2 failed (strict XPASS "until P3"), 67.3 s |
| After the xfail marks were removed (4ede4a6) | 641 passed, 67.5 s |
| After P4 merge (a4a3c6d) | 650 passed, 1 failed (TypeError in arcade_evidence `_seeds`), 70.4 s; reverted a6aef84 |
| After P5 merge | 648 passed, 69.8 s |
| After P6 merge | 653 passed, 72.9 s |
| After P7 merge | 653 passed, 72.7 s |
| After P4 was reapplied with its fix | 664 passed, 75.3 s |
| After I1's test_oracle (8f68d07) | test_feel_pong_meets_its_budgets failed: `response_ticks 10 > max 2; fidelity -0.2823 < min 0.8` (other two passed) |
| After the Pong fix (35ae954) | 669 passed, 0 failed, 130.8 s |
| After X1 (a2e6681), final | 674 collected, 674 passed, 0 failed, 0 skipped, 0 xfailed, 132.5 s |

## Commits (sha + subject)
Main, first parent, 6ddaf78..a2e6681:
- 17ca145 feat(arcade): closed-loop feed, REQUIRED_SCENARIOS, bots.py and the default feel budgets (S1, it07)
- 1a493e1 Merge P3: Pong's scripts, bots and budgets (it07), of 9a69392
- 7f71237 Merge P1: feel metrics (it07), of 0551d31
- af86881 Merge P2: pattern check and the tests for every game (it07), of 772dfc8
- 4ede4a6 test(arcade): drop the two 'until P3' xfail marks now Pong has its scripts and bots (I1, it07)
- a4a3c6d Merge P4: tools/arcade_evidence.py (it07), of 73974f5
- a6aef84 Revert "Merge P4: tools/arcade_evidence.py (it07)"
- cf846e5 Merge P5: arcade_shot provenance and the black refusal (it07), of 4091222
- 387936a Merge P6: C37, the mirror holds a dropped keypoint (it07), of 1abfbf8
- 1014118 Merge P7: the arcade-game-authoring skill (it07), of 3395ca7
- 60f3989 Reapply "Merge P4: tools/arcade_evidence.py (it07)"
- 8c750a4 Merge P4 again: arcade_evidence passes --seeds as an int (it07), of 94e0245
- 8f68d07 test(arcade): the oracle end to end on Pong: feel budgets, bot ranking, evidence package (I1, it07)
- 35ae954 fix(pong): a body in view takes a CPU seat at once, mid-rally (feel response and fidelity)
- a2e6681 feat(feel): score visibility, 5 m legibility and the idle hint, with default budgets (X1, it07)

The worktree branches are left in place: worktree-agent-{ae1200bd0647335f6, ac56b6ccc3f680ee1, acb86be052a5994df, af0c763b3eeea756c, a90655fb15e4dcf7f, a7ead0ff041394812, ae0f8661c3141e1d8}. None is a failed branch. Nothing was pushed, no tag was set, and I2 was not run. state.md was not touched.

## Minutes (serial lane, parallel tasks, integration, stretch)
- Serial lane (S1): 9 min.
- Parallel tasks: 25 min. P1 to P4 ran together, P3 the longest at 18.5 min; then P5 to P7 took 4 min.
- Integration: 22 min. That covers the merges, P4's revert and send-back, I1, and the Pong round 1 fix; I1 ended green at 56 min.
- Stretch: 16 min (X1 only).
- Total: about 74 min.

## Review fix (B1)
One fresh opus implementer worked in the main checkout, with no worktree. It made one commit.
- **Commit:** 6ebbb6d, "fix(feel): presence_answer_seconds, measured with no budget (B1, it07)". It sits on a2e6681.
- **Files:** arcade/feel.py, arcade/feel_budgets.toml, tests/arcade/test_feel.py and tests/arcade/test_bots.py. SKILL.md and tools/arcade_evidence.py never named the metric, so they are unchanged.
- **What changed:**
  - `idle_hint_seconds` is renamed `presence_answer_seconds` (`_presence_answer`, `PRESENCE_WINDOW` = 6.0). Its docstring says it measures that the wall answers a present body and that it is NOT spec 9.3's idle hint.
  - The metric is removed from the control, score and toy defaults. The budget file's "3 s" comment line is gone, and one line was added saying the metric is measured with no budget.
  - `judge` already skipped metrics that have no budget, and a test now pins that.
  - `score_visible` and `score_legible` and their budgets are unchanged.
- **Tests:**
  - New: `test_presence_answer_has_no_default_budget`. It checks the raw TOML and `feel.budgets` for a stub of each kind, and that `judge` gives no failure for None, 0.0, `PRESENCE_WINDOW` or 1e9.
  - The measure test is renamed `test_presence_answer_times_the_first_answer_to_a_present_body`. It gives a number for a game that draws a present body and `PRESENCE_WINDOW` for one that draws nothing, and it now asserts the budget is absent.
  - test_bots' expected dicts lose X1's `idle_hint_seconds` entry, and nothing else changes there. The key set in `test_measure_repeats_under_seeds` carries the new name.
  - The two expected idle-hint failures are gone from test_feel. The score failures are still asserted exactly.
- **Grep:** `git grep -n idle_hint -- ':!docs/superpowers/'` prints nothing.
- **Suite, my run:** 675 collected, 675 passed, 0 failed, 0 skipped, 0 xfailed, 142.1 s. The implementer's run took 134.1 s.
- **Pong's feel report after the fix** (128x32, `bots.seeds(Pong, "128x32", 20)`):
  - response_ticks 2.0, fidelity 0.9946, range 0.7742
  - lit_fraction 0.0219, dim_fraction 0.1892, liveliness 0.0035
  - flash_area_raw 0.0, square_flashes 0.0
  - score_visible 0.9588, score_legible 1.0, presence_answer_seconds 0.0 (no budget)
  - win_good 1.0, win_lazy 0.2, win_none 0.0
  - round_seconds 92.03, phases_reached 1.0
  - The budgets judged are the 15 others, and `presence_answer_seconds` is not among them. `failures == []`.
- **Deviations:**
  - The implementer's full-suite command began with `cd /Users/trey/dev/codeisart`, the directory it was already in, so it changed nothing.
  - The new no-budget test guards only the new name. The old name's removal is pinned by test_bots' exact dict.
  - docs/superpowers/workflow/decisions.md shows as modified in the tree, as state.md does. Neither was touched or staged by the fix.
