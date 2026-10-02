# G3 report: Swat (`swat`), iteration 19

Base a5dbf29 (checked first). Branch: the worktree's own branch (agent worktree agent-a43fac7edc5096b91).

## Files
- `arcade/games/swat.py`, `arcade/games/swat_bots.py`, `arcade/games/swat_feel.toml`, `tests/arcade/test_swat.py`, this report.
- No engine, safety or shared file touched (`arcade/bots.py` read only; I0's `Move.pose` and `hand="both"` unused).

## Test counts
- `tests/arcade/test_swat.py`: 46 passed (about 12 s on the loaded machine without the 5-seed bot tests, which are 13 s cold and memoised after the oracle in a full run).
- `test_oracle.py -k swat`: 3 passed (feel budgets, bots rank, pooled plays equal in-process plays), 102 s alone with the 60 plays.
- Full suite, three parts: part 1 (`tests --ignore=tests/arcade`) 1109 passed, 3 skipped, 132.8 s; part 2 (arcade without oracle and all_games) 778 passed, 1 skipped, 176.2 s; part 3 (oracle + all_games) 49 passed, 148.0 s. Total 1936 passed, 4 skipped.
- Skip note: the 4th skip is `tests/arcade/test_pose_mediapipe.py:303` ("no model at .../models/pose_landmarker_lite.task"): the model file is not in this worktree (untracked in the main checkout). It is an environment fact of the worktree, not the game; it should not skip in the main checkout. Nothing failed, no timing test failed.

## Final win rates (20 report seeds, 128x64) and feel
- win_good 0.95, win_lazy 0.35, win_none 0.0; phases_reached 1.0; round_seconds (median, good) 66.2 (3 s ready + 60 s + 3 s hold).
- Budgets (all met, none overridden): response_ticks 1.0 (max 2), response_px 17 (min 12), fidelity 0.954 (min 0.8), range 0.873 (min 0.6), lit_fraction 0.029 (0.01 to 0.5), dim_fraction 0.003 (max 0.1), liveliness 0.004 (min 0.001), flash_area_raw 0.003 (max 0.1), square_flashes 2 (max 6), score_visible 1.0, score_legible 1.0.
- Score lists over the 20 seeds (goal 30): good 48 35 38 44 36 39 41 43 37 44 39 40 35 25 48 46 35 42 43 47; lazy 37 28 17 26 18 35 29 33 26 28 37 25 19 18 35 39 23 29 28 41.

## Lever values and the bots' numbers as committed
- Levers moved from the plan's starting values: `GOAL` 30 (plan 25), `SPAWN_EVERY` (1.4, 0.8) (plan 1.1, 0.6), `BOMB_SHARE` 0.2 (plan 0.15). All other constants as the plan.
- Good: `reaction_ticks` 5, `noise` 0.02, swipe every 3 ticks, `HALF` 0.15, bomb avoid 8 px (hand down), `LEAD_TICKS` 6 (leads the fruit's drift by its last-tick move).
- Lazy: `reaction_ticks` 12, `noise` 0.05, swipe every 8 ticks, ignores bombs, `HALF` 0.07 (short strokes), `LEAD_TICKS` 0.
- Why: with the plan's numbers both bots won every seed (a bot cuts about 55 of 56 fruit, so even the lazy bot passed 25). The lazy bot has to be a worse cutter (no lead, short strokes) and the round tighter; the goal then splits them.

## What the files add to the suite's time
- Under load (4 worktrees at once): the 60 report plays plus the feel report in the oracle: about 100 s alone (`-k swat`), mostly the plays on the pool in a full run; `test_feel_meets_its_budgets[swat]` 3.6 s, `test_pooled_plays_are_the_in_process_plays[swat]` 1.6 s; the soak adds `swat-128x64` 7.0 s and `swat-96x48` 4.9 s in `test_all_games.py`.
- My file: slowest calls 2.1 s (lobby window), 2.1 s and 2.0 s (flash rule, canonical and duo, first 25 s each), 1.3 s (seeded repeat), 0.9 s (scenarios); about 10 to 12 s for the 44 non-bot tests under load, over the 6 s asked. The cost is the real-runner tests (lobby, flash, soak-like); I cut each to a 20 to 25 s window and no more. The 5-seed bot tests (13 s cold) are free after the oracle's pool in a full run.

## Deviations from the plan
1. `GOAL`, `SPAWN_EVERY`, `BOMB_SHARE` and the lazy bot's numbers as above (named levers; the plan says tune them).
2. Canonical: the plan says "one slow wrist sweep". `response_px` (min 12) read 5.5 with a 4 s sweep and 13 with 2 s, so the sweep is 1.5 s (top to hip, 17 px); the rest as the plan (walk across with the hand up, then swipes 0.2 to 0.8 every 0.4 s). `CANONICAL_SECONDS` 70.
3. A bomb is drawn as a fat plus (dark corners), a fruit as a full 5x5 square, so a bomb reads without a second colour channel trick; the `bomb_xy` pixel is lit.
4. Test windows: the flash-rule, lobby and idle tests run the first 20 to 25 s of their scenario, not the whole one (time). `test_a_still_body_under_real_noise_scores_nothing` is 5 ids x 2 heights, 25 s each, through the game directly.
5. The blade can sit under the score's black box (top right, rows 0 to 17); `test_debug_state_is_clean` skips the lit-pixel check for a blade there (the plan's "score drawn last over a black box").
6. `swipe(seat, a, b, v)` and `spawn(...)` are public methods of the game (the tests drive them); `update` calls `swipe` each tick per seat.
7. `fx.flash` on a combo: if it returns True no burst is made on that tick (all cuts of the tick); if False the bursts go on.

## Questions for the owner
- Is GOAL 30 with a 56-fruit ceiling right for humans? A real player cuts far fewer than a bot; the oracle only fixes the bots' order. A real-wall run may want GOAL back toward 25.
- The worktree lacks `models/pose_landmarker_lite.task`, so one skip more than at BASE here; not an issue in the main checkout.
