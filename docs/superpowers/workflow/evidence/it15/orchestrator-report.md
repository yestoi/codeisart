## Completed
Lane A (arcade), from BASE f24cd3d (checked at 08:36):
- I0 (bef4c17): `PLAYS`, `play_key` and the new `played(game_cls, bot_name, seed)` are in `tests/arcade/helpers.py`. `test_oracle.py` imports them and gains `test_feel_meets_its_budgets[<name>]` (marked feel) and `test_bots_rank[<name>]` for every game but Pong, with one 20-seed report per game in the module-level `REPORTS`. I checked this by temporarily including Pong: both passed and reused the memoised plays. `test_pong.py` passes alone (46) and after `test_oracle.py` (49).
- E1 (380f11d, opus): C47 and C46. `Body.measured` and `Body.torso_per_width` are defaulted fields. The tracker learns the torso per shoulder width and takes the first measure at once. `Depth` takes a new centre on the first measured capture, once per `reset()`. All 11 plan tests were seen failing first. The Pong check is EQUAL to the plan: response_ticks 1.0, response_px 12.0, fidelity 0.9947, range 0.6287, win_good 1.0, win_lazy 0.25, win_none 0.0, round_seconds 66.0667, phases_reached 1.0, failures []. `test_oracle.py` plus `test_pong.py`: 50 passed.
- E2 (21813e7, opus): C45's merge only. It adds `DUP_DISTANCE = 0.04` and `merge_duplicates`, called in `step()`, with the plan's five tests and two extras. The hand point was cut (see Deviations).
- G1 Quick Draw (worktree-agent-a2dd0ee6c6d1c03f6, 23f0156, sonnet): merged as 5fdb93d. The oracle, the generic tests and its 34 tests pass. Its feel report: failures []; win_good 1.0, win_lazy 0.45, win_none 0.0, round_seconds 20.98, fidelity 0.989, range 0.635. There is no budget override.
- G2 Dodge (worktree-agent-a1975312e3ec27257, c49d902, sonnet): it was whole. The oracle, the generic tests and its 43 tests passed. Feel failures []; win_good 0.95, win_lazy 0.35, win_none 0.0, round_seconds 49.5. It merged as 83fe13a and was then REVERTED (16dbb91) under the cut order, step 1, because I1's suite took 334.84 s. The branch and worktree are kept (/Users/trey/dev/codeisart/.claude/worktrees/agent-a1975312e3ec27257). Reverting 16dbb91 restores Dodge. Per the operator (10:16), the Dodge decision is the operator's after this report.
- I1 (8ddba28): one line in the game guide's Controls on `Body.measured` and on `Depth`'s first measure. The full suite ran with `--durations=25`.

Lane B (the show's wall, T-close, C53, SAFETY):
- Plan committed alone (14d2f07, `docs(plan): it15 lane B, the close waits out the hold (C53)`), after the operator's confirmation. The plan was not edited.
- T-close (worktree-agent-aef9b4669b1f6ed09, 378191d, opus, a worktree from 14d2f07): merged as 01bfd95.
  - `GovernedDisplay` has `sleep=` (default `time.sleep`). `close()` in a hold reads the clock once, before the first wait, never in a loop. It then sends the counted frame once if `_settled == 0` (a failure is logged), sleeps `HOLD_S`, calls `_end_hold()` and sends two governed black frames.
  - `_open_wall` passes `sleep=lambda s: self.sleep(s)` to both calls. `_close` sets `self._now = self.clock()` before `wall.close()`.
- The checks after the merge:
  - The plan's EXACT block against `tests/test_wall_close_hold.py`, compared by AST test by test: all 12 tests (8 functions, 2 of them parametrised to 4 and 2) and the helpers `Ticks`, `closes`, `phases`, `TEAR` and every import are the SAME. No assert, input or number changed, only layout. The file adds the four prose tests after them: `test_the_loop_s_close_in_a_hold_waits_on_the_loop_s_sleep`, `test_a_failed_counted_send_in_the_close_still_waits_then_goes_black`, `test_a_failed_black_in_the_close_raises_and_still_closes_the_display` and `test_every_governed_wall_of_the_show_gets_the_loop_s_sleep`, with a helper `_close_in_the_hold`.
  - `git diff 0dae849 -- arcade/flash.py arcade/brightness.py show/display/colorlight.py` is EMPTY. `git diff f24cd3d -- arcade/runner.py tools/ deploy/` is empty.
  - Removed `assert` lines in `git diff f24cd3d -- tests/`: five in total, all in `tests/test_wall_hold.py::test_close_during_the_hold_sends_the_counted_frame_then_black`. That is the one test the plan names; it is deleted and replaced by the exact `test_close_in_the_hold_waits_then_the_counted_frame_waits_then_black`, and a two-line comment points to it. The lines:
    - `assert wall.push(frames[3]) is None and wall.holding`
    - `assert inner.closed and inner.calls == 6 and not wall.unsent`
    - `assert [t for t, _ in inner.sent[2:]] == [3 / 16] * 3`
    - `assert np.array_equal(inner.sent[2][1], counted)`
    - `assert not inner.sent[3][1].any() and not inner.sent[4][1].any() and wall.governed == 4`

    Lane A removed no assert line.
  - `tests/test_wall_close.py` gains only `loop.sleep = lambda s: None` before `loop._close()`. No assert of it changed.
- On BASE, before the fix:
  - All 16 new tests failed: 14 with TypeError (no `sleep` keyword), and the loop and AST tests on no wait and no `sleep=`.
  - With the keyword only and the old close, 8 of the 12 exact tests failed, as the plan says. The "one tear" closes at j = 1 read 8 square flashes against a budget of 6.
- Seconds (`--durations=0` on the new file): 16 passed in 2.53 s. The four `j_ticks` cases take 0.56 to 0.64 s each; everything else is 0.01 s or less.

The review's fix B1 (Quick Draw), under the operator's rulings of 10:31, after T-close's merge and suite:
- c99d463 (opus, serial in the main checkout, from 01bfd95): seat a is never the CPU's.
  - A new `_is_cpu(seat)` is true only for seat b with no human. Seat a with no human is empty: its bar is at the bottom as in a dropout, drawn in player 1's colour; it never draws or wins; `a.rounds` never rises.
  - TOO SOON by seat b's human against an empty seat a is a void round.
  - `debug_state()["cpu"]` is now "right" or None.
  - The hint is not drawn in `result`.
  - Files: `arcade/games/quickdraw.py` and `tests/arcade/test_quickdraw.py` only. The removed test lines are imports; no assert was changed or removed.
- The new tests, each seen failing first:
  - (a) `test_a_solo_player_who_leaves_in_result_banks_no_round_they_did_not_play`, the probe's five seeds through the real runner. It failed first on 1057892440 with score 3.0 and best 3.0.
  - (b) `test_a_player_back_after_the_grace_gets_seat_a_with_their_rounds_only`. It failed first when seat a's CPU won, so `left` became 2.
  - (c) `test_the_hint_is_not_drawn_over_the_reaction_time`. It failed first on hint pixels beside the time.
- The probe after the fix: all five seeds end by the leave rule at 2-1, with score 2.0 and best None.
- Quick Draw's feel report after the fix: failures []; win_good 1.0, win_lazy 0.45, win_none 0.0, fidelity 0.9891, range 0.6349, square_flashes 2.0, flash_area_raw 0.0, round_seconds 20.98, phases_reached 1.0. No band was touched and Pong was not touched. `test_oracle.py` plus `test_all_games.py -k quickdraw`: 10 passed.
- The implementer's smallest readings:
  - The empty seat's anchor is reset each tick, so it is never input and never raises the hint.
  - A returning body regains seat a through the existing `_assign` at the next `ready`.
  - The hint vanishes at the start of `result` rather than fading.
  - A launch with nobody in view leaves seat a empty from the start.
- The review's non-blocking notes (`_flashed`, `_winner`, `_to_ready_void`, the dropout that arms the bar) are not fixed, per ruling 5.

## Deviations
- E2's hand point was CUT (plan cut order, step 3). The implementer stopped before coding because `HAND_LANDMARKS` changes two things the plan does not name:
  - `tests/arcade/test_pose_mediapipe.py::test_landmark_mapping` line 90 asserts `kps[LEFT_WRIST].x == 0.15`; the mean of the three landmarks makes it 0.17.
  - `test_raised_right_hand_gives_right_wrist_x_over_half` would need its `person_landmarks` fixture to gain pinky and index landmarks, or `raised_wrist` is None.

  I sent E2 back as the C45 merge only. Restoring the hand point needs the owner's ruling on those two asserts.
- Dodge cut on suite time (cut order, step 1): I1's run took 334.84 s (1345 passed, 1 skip, load average about 2.4 to 4.3). The run right after the G2 merge took 321.11 s. Without Dodge the suite took 293.57 s at 10:10 (the operator's evidence run was beside it, and it was still under 330, so Quick Draw stays), then 277.48 s after T-close with lane B's +16 tests. The overrun is inside the load noise; the operator re-times it.
- E1's commit trailer: the implementer wrote `Claude Opus 5.5`. I amended the message only (558e1fb became 380f11d, the same tree) to the Fable 5.1 line.
- The Dodge revert's message was amended to give the reason and the Fable 5.1 trailer (71d326e became 16dbb91).
- After E1 I did not re-run the full suite myself. The implementer's clean run (1241 passed, 1 skip, 541 s under a load of about 48) was on the same tree. Under load, E1 and E2 each had first runs with timing failures that passed alone and on rerun: `test_headless.py:236` and `test_headless.py::test_tick_budget_with_the_governors_share`. T-close's first worktree run failed `tests/test_show_shot.py::test_strobe_session_is_held` (held 0, a real-time child process); it passed alone and on rerun, and T-close cannot reach it. Every one of my runs was clean.
- I0: the parametrised tests are defined under `if OTHER_GAMES:`, because an empty parameter set collects one skipped item each, which would break "count plus 0" and "1 skip".
- Lane B started at 10:16, not at 09:32: the operator's messages of 09:32 and 09:56 reached me only after lane A's first report (written at about 10:15). I started lane B on receipt, and nothing was lost to the ordering, since lane B shares no file with lane A.
- E1 smallest readings:
  - "measured at 1.6 s" is read as 1.6 times the scale.
  - The first measure is taken at once only for a capture later in time.
  - The hanging wrist is below confidence without hips in the raised-hand test.
  - The Pong test measures travel as the paddle's y range.
  - Two read-only commands used `cd`.
- G1 tuning inside the bands, as the plan allows:
  - `CPU_DRAW` is (0.25, 0.80), not (0.40, 0.70).
  - lazy `reaction_ticks` is 15, not 14, and it draws early at `wait_left` < 1.0, not 0.5.
  - Smallest readings: a void round goes straight back to `ready`; a same-tick tie goes to the human; a seat in dropout shows its bar at the bottom; geometry scales with the wall's height.
- G2's deviations, all on the cut branch:
  - An extra `debug_state` key `rocks`.
  - Both bots walk to the nearest free x rather than stepping 0.25 of the zone. Lazy's noise is 0.05, not 0.06, and it reacts above row 40, not 38.
  - `HIT_SLACK` is read as 1 px a side.
  - The run bar is `w - 26` px wide, for the score's gutter.
  - `canonical` runs 55 s.
- T-close's smallest readings:
  - The replacement test lives in the new file, with a two-line pointer comment in `test_wall_hold.py`.
  - "Logged" is checked with caplog.
  - The AST test is stricter: `sleep=` must be exactly `lambda s: self.sleep(s)`, with exactly 2 calls.
  - `self._now = self.clock()` sits inside `_close`'s existing try.
  - The not-holding and no-clock paths keep the old `elif self.unsent:` path.
  - The new file's module docstring is its own, not the plan's line. It is not an assert, input or number.
- Findings outside the tasks:
  - E1: without hips, `Cursor` and `Body.cursor` can switch to a hanging hand. It does not bite Quick Draw, per G1.
  - G1: the bar lags the wrist by about 0.1 s through the Glide, plus camera latency. A human check of `CPU_DRAW` is worth making.
  - G2: a `canonical` run through a `Lobby` with raw=True counts the lobby's end card in `flash_area` (0.005). A scratch script run from a worktree imports the main checkout's `arcade` unless `sys.path` is set.
- Working-tree changes by others while I ran: `docs/superpowers/workflow/decisions.md`, `journal.md` and `state.md` are modified, and `docs/superpowers/workflow/evidence/it15/` is untracked. I left them alone and uncommitted. No one else committed to main.

## Test status (command + counts)
Command, from /Users/trey/dev/codeisart: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs -p no:cacheprovider /Users/trey/dev/codeisart`
- After I0 (bef4c17): 1230 passed, 1 skipped, 284.63 s.
- After E1 (implementer's run, same tree as 380f11d): 1241 passed, 1 skipped, 541.38 s (load about 48).
- After E2 (implementer's run, 21813e7): 1248 passed, 1 skipped, 235.49 s.
- After the G1 merge (5fdb93d): 1292 passed, 1 skipped, 274.29 s.
- After the G2 merge (83fe13a): 1345 passed, 1 skipped, 321.11 s.
- I1 with `--durations=25` (8ddba28, Dodge in): 1345 passed, 1 skipped, 334.84 s, OVER 330. Slowest: the Pong report setup 62.92 s, `test_feel_meets_its_budgets[dodge]` 26.70 s, `[quickdraw]` 25.99 s.
- After the Dodge revert (16dbb91): 1292 passed, 1 skipped, 293.57 s.
- After the T-close merge (01bfd95):
  - The plan's "After the merge" files (`test_wall_close_hold.py`, `test_wall_hold.py`, `test_wall_close.py`, `test_wall.py`, `test_main.py`, `test_wall_pattern_governed.py`, `test_show_soak.py`): 170 passed in 27.14 s.
  - The full suite: 1307 passed, 1 skipped, 277.48 s.
- After the B1 fix (c99d463), the implementer's run on main, the FINAL run: 1310 passed, 1 skipped, 307.20 s. That is under 330. The new tests add about 1.7 s, and the rest of the rise from 277 s is load. The skip is `tests/test_sandbox.py:153` (no unshare on macOS). I did not re-run it myself; nothing changed after it.

## Commits (sha + subject)
- bef4c17 test(arcade): the oracle judges every game; plays shared through helpers (it15 I0)
- 380f11d feat(arcade): the tracker says "measured" and holds the torso (it15 E1: C47, C46)
- 21813e7 feat(arcade): one person, one pose: duplicate poses merged (it15 E2: C45)
- 23f0156 feat(arcade): Quick Draw, the first hand up on DRAW wins (it15 G1)
- 5fdb93d Merge G1: Quick Draw (it15)
- c49d902 feat(arcade): Dodge, rocks and side steps under the whole body's x (it15 G2)
- 83fe13a Merge G2: Dodge (it15)
- 8ddba28 docs(arcade): the game guide says Body.measured and Depth's first measure (it15 I1)
- 16dbb91 Revert "Merge G2: Dodge (it15)" (cut order step 1, suite 334.84 s)
- 14d2f07 docs(plan): it15 lane B, the close waits out the hold (C53)
- 378191d fix(show): the close waits out the hold after a failed push, then goes black (C53; it15 T-close)
- 01bfd95 Merge T-close: the close waits out the hold (C53; it15)
- c99d463 fix(arcade): Quick Draw keeps player 1's seat; no round for an empty seat (it15 review B1)

HEAD is c99d463. `git diff 0dae849 -- arcade/flash.py arcade/brightness.py show/display/colorlight.py arcade/runner.py` is empty. Nothing is pushed or deployed. The branch worktree-agent-a1975312e3ec27257 (Dodge) and its worktree are kept.

## Minutes (serial lane, parallel tasks, integration)
- Lane A:
  - Serial lane, 43 min: I0 10 (08:36 to 08:46), E1 29 (08:47 to 09:16), E2 13 including the send-back (09:16 to 09:29).
  - Parallel tasks, 24 min: G1 21 and G2 23, from 09:30 to 09:53.
  - Integration, 21 min: the merges and suites, I1, the Dodge revert and the suite (09:53 to 10:14).
- Lane B:
  - The plan commit at 10:16.
  - The T-close task, 15 min (10:16 to 10:31).
  - The merge and checks, 6 min: the named files, the full suite, the AST and diff checks (10:31 to 10:37).
- The review's fix B1: 12 min (10:38 to 10:50), serial in the main checkout, including its full suite.
- Total: 08:36 to 10:51, 135 min.
