# G2 report: Flap (`flap`), iteration 19

Base a5dbf29. Files: `arcade/games/flap.py`, `arcade/games/flap_bots.py`, `arcade/games/flap_feel.toml`,
`tests/arcade/test_flap.py`, this report. No other file touched.

## Tests
- `tests/arcade/test_flap.py`: 36 passed (about 15.8 s alone).
- Oracle `-k flap` (with my file): 39 passed (the 3 oracle tests: feel budgets, bots rank, pooled plays), 80 s wall
  on the loaded machine, 58 s of it the pool/report setup for flap's 60 report plays.
- Full suite in three parts:
  1. `tests --ignore=tests/arcade`: 1109 passed, 3 skipped, 131 s.
  2. `tests/arcade` minus oracle and all_games: 767 passed, 1 skipped, 1 failed, 245 s. The failure was
     `tests/arcade/test_headless.py::test_tick_budget_with_the_governors_share` (median 0.509 against 0.5, load);
     rerun alone: 19 passed. The one skip is `test_pose_mediapipe.py:303` (no model file in the worktree; the 3 skips of
     part 1 are the base's three), so skips read 4 here only by this worktree artifact.
  3. oracle + all_games: 49 passed, 159 s.
  Total 1925 passed after the rerun (base 1880 passed): +36 mine, +3 oracle flap tests, +8 test_all_games parameters.

## Final win rates (20 report seeds, the oracle's own report)
good 1.0, lazy 0.6 (0.75 with lazy at reaction 9, which failed the band), none 0.0, phases_reached 1.0,
round_seconds 49.0.

## Lever values and bots as committed
All plan constants as given (RUN_SECONDS 45, READY_SECONDS 1, READY_Y 30, FLAP_WINDOW 0.4, V_ABOVE 0.40, V_BELOW 0.62,
BIRD 28/5x4, GRAVITY 24, FLAP_VY -22, MAX_FALL 30, PIPE_W 6, GAP_H (34, 30), PIPE_EVERY 3, SCROLL 20, GAP_Y (14, 44),
GAP_STEP 6, FLOOR_Y 59, CRASH_SECONDS 1.2, MAX_RUNS 3, gauge 8 wide, V_TOP/V_BOTTOM 0.15/0.85, rows 4 to 56). No game
lever moved. Only a bot number: good `reaction_ticks = 5`, `noise = 0.02`; lazy `reaction_ticks = 10` (plan: 9),
`noise = 0.05`. Sweep: 4 ticks at 0.1, then 4 ticks at 0.95. Lazy's rate by reaction ticks (20 seeds): 9 gives 0.75,
10 gives 0.60, 11 gives 0.55, 12 gives 0.05.

## Feel metrics against budgets (all met, no override)
response_ticks 1.5 (max 2), response_px 16 (min 12), fidelity 0.990 (min 0.8), range 0.825 (min 0.6), lit_fraction
0.056, dim_fraction 0.0, liveliness 0.00139, flash_area_raw 0.0, square_flashes 0, score_visible 1.0, score_legible 1.0,
win_good 1.0, win_lazy 0.6, win_none 0.0, phases_reached 1.0, round_seconds 49.

## What the files add to the suite's time
My file 15.8 s alone (`test_good_beats_lazy_beats_nobody` 11 s of it, plays the oracle's pool does not share).
Oracle flap: the 60 report plays go to the pool, `test_feel_meets_its_budgets[flap]` 2.8 s call. test_all_games for
flap: soak 5.0 s (128x64) and 3.9 s (96x48), plus smaller flash and tick tests. Estimated total about 25 to 30 s of
suite time, within the plan's G2 share.

## Deviations and notes
- `test_both_wrists_down_within_the_window_flap`: read as the wrists' drops staggered by 0.3 s (flaps) or 0.5 s (does
  not), since under the rule as written one slow sweep within 0.4 s also flaps. A stagger 0 case is added.
- `bird_vy` is FLAP_VY on the flap's tick: the flap is applied after that tick's gravity.
- A flap in `over` restarts only after the CRASH_SECONDS fade.
- `score` in debug_state is the best run while in `over` (so the end card shows it); `scores.record` is called once,
  for the best run, when the last run ends (a survived run, or run MAX_RUNS) or in `done()`. A session left before
  `done()` after a non-final crash banks nothing.
- `active`: a flap on the tick, or the gauge's row range over the last 1 s at 3 px or more.
- Extras the plan left open: a floor line at row 59, "FLAP TO FLY" at 1x, hint text "ARMS UP THEN DOWN", "FLAP AGAIN"
  after a fade with runs left. The first gap's centre is READY_Y plus or minus GAP_STEP.
- canonical is 60 s (not about 100 s): six slow strokes fill 5 s to 20 s, then a flap every 1.8 s.

## Questions for the owner
None blocking. Lazy's rate is cliff-like in reaction ticks (0.75 at 9, 0.05 at 12): a later change to the physics may
need lazy retuned.
