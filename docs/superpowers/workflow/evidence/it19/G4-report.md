# G4 Freeze: implementer report

Base a5dbf29. Branch: the worktree's own branch (see the final message for the name and sha).

## Files changed (all new)
- arcade/games/freeze.py
- arcade/games/freeze_bots.py
- arcade/games/freeze_feel.toml
- tests/arcade/test_freeze.py (38 tests)
- docs/superpowers/workflow/evidence/it19/G4-report.md

## Test counts
- tests/arcade/test_freeze.py: 38 passed (about 23 s alone; the slowest, test_good_beats_lazy_beats_nobody, 11 to 12.5 s, is the shared bot play).
- test_oracle.py -k freeze: 3 passed, 67.5 s (63 s of it is the module's pool setup, shared with Pong).
- test_all_games.py -k freeze: 8 passed, 10.9 s.
- Full suite, three parts: 1109 passed, 3 skipped (130 s); 770 passed, 1 skipped (197 s); 49 passed (123 s).
  Total 1928 passed, 4 skipped, 1932 collected (base 1883, +49 = 38 + 3 + 8). No failures.
- Skips: 4 against the brief's 3. The extra one is tests/arcade/test_pose_mediapipe.py:303, "no model at <worktree>/models/pose_landmarker_lite.task": the model file is not in the worktree. Not caused by Freeze.

## Win rates, levers, bot numbers (20 report seeds)
- win_good 1.0, win_lazy 0.4, win_none 0.0. Bands met with no tuning.
- Levers untouched: GREEN_SECONDS (3,6), RED_SECONDS (2.5,4), LAZY_GREEN 4.5. GRACE 0.5 and REDS 6 fixed. MOVE_TRAVEL 0.25 (not raised).
- Bots: good reaction_ticks 6, noise 0.005; lazy reaction_ticks 10, noise 0.01, slips 1.0 s into the first red when the first green lasted over 4.5 s; SWAY 0.1, SWAY_SECONDS 1.2, SWING (0.2, 0.8) every 0.3 s.

## Feel metrics (all budgets met, failures [])
response_ticks 1.0; response_px 396; fidelity 0.99987; range 0.921; lit_fraction 0.098; dim_fraction 0.0157; liveliness 0.0184; flash_area_raw 0.0186; square_flashes 5 (budget 6); score_visible 1.0; score_legible 1.0; presence_answer_seconds 0.0; round_seconds 52.9; phases_reached 1.0.

## Suite time added
Freeze adds about 23 s (own file) + 2.7 s call (oracle) + 5.7 s and 3.4 s (soaks) + 1.5 s (pooled-play check); the pool setup it adds to is shared.

## Deviations
1. COUNT_LAG 0.3 s: a red counts 0.3 s after it ends, so a seat's travel through the last moment of the red is judged.
2. The canonical has no side steps: waves of 0.45 s and a slow sweep only. Faster sweeps, side steps and 0.3 s waves drove the flash governor to held ticks and square_flashes to the budget.
3. A survivor in a duo counts the red it stood through.
4. idle_body ends "inactive" at about 35 s by the runner's own rule, so its test asserts score 0, out False and best None, not phase over.
5. Hint text is "MOVE!" (y=13); the ready text sits at top=24, both over black boxes, so the head stays clear.
6. Over words: OUT, SAFE!, P1 WIN, P2 WIN, DRAW.
7. `plan` and `seats` are public attributes (the tests read them).

## Questions for the owner
None.
