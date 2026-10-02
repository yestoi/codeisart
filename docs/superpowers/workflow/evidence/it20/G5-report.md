# it20 G5, Jump: report

Base b4f1e9b. Files (all new): `arcade/games/jump.py`, `arcade/games/jump_bots.py`, `arcade/games/jump_feel.toml`,
`tests/arcade/test_jump.py`, this report. Built test-first (the test file was written and seen failing at import, then
the game; one red after green was my own test timing, fixed in the test: window 2 ends at 15.5 s, the run was 14 s).

## Tests and times (worktree, shared Mac)
- `tests/arcade/test_jump.py`: 39 passed, 16.2 s (slowest: `test_good_beats_lazy_beats_nobody` 7.9 s, its 15 bot plays;
  `test_seeded_runs_repeat` 2.0 s; the rest 1.1 s or less).
- `tests/arcade/test_all_games.py -k jump`: 8 passed, 9.3 s (soaks 4.2 s at 128x64, 3.8 s at 96x48).
- `tests/arcade/test_oracle.py -k jump`: 3 passed, 13.6 s (pool: 60 plays, 4 workers, 9.6 s; feel call 3.2 s).
- `tests/arcade/test_game.py`: passed (53 passed together with the two above).
- Whole suite not run (orchestrator's). Own CPU beside the soaks: about 16 s tests + 7 s soaks + pool plays (9.6 s on 4
  workers), within the plan's +30 s share.

## Feel report (20 seeds, 128x64, `arcade.feel.report`; failures: none)
win_good 1.0, win_lazy 0.45, win_none 0.0, fidelity 0.999, range 0.685, response_ticks 1.0, response_px 197.5,
flash_area_raw 0.0024, square_flashes 4.0 (at most 6), score_visible 0.978, score_legible 1.0, round_seconds 30.0,
phases_reached 1.0, lit_fraction 0.111, dim_fraction 0.0, liveliness 0.018.

## Constants and bots
All the plan's constants as written; no number moved. Added: `COLUMN_SLACK = 1`, `MIN_SAMPLES = 5`, `LINE_COLOR` (255,
255, 255: the peak line), `TEXT_COLOR` (255, 160, 0), `BELL_W, BELL_H = 5, 4`. Person's torso is 0.18 of the frame
(measured in `jump_bots.TORSO`): good's peak is 44 cm = lift 0.158, lazy's 34 cm = lift 0.122. Bot arc: 18 ticks, starts 5
ticks after the bot sees play open. No tuning needed.

## Deviations and choices the plan left open
- `measure_rise` returns None under `MIN_RISE` too (so None means "not counted"); the bar and `rise` then read 0.
- The bell rings live, on the first counted capture at or over `bell_cm` (cm integer), not at the window's end; flash is
  `fx.flash((255, 255, 255), 0.15)` (return not needed for anything else, noted in a comment) and the pop sits at x 32.
- The ready check: samples kept SETTLE_SECONDS, at least `MIN_SAMPLES`, span at least SETTLE - 0.05 s; opens at 1.43 to
  1.5 s after a still start. A player seen again after the grace, or a new id, starts the samples afresh.
- `active` is False outside play (a stander in ready or result is not active); the hint shows only in play (idle 2 s),
  so `idle_body` hints at about 3.5 s after the game starts, not under 3 s (the guide's "within three seconds"): ready's
  "GET SET" is on the wall from the first tick. Say if the hint should also come in ready.
- The result number is drawn at x 20, row 24 over a black box; "over" shows the best as the white line on an empty bar
  plus the score; no extra text.
- Canonical (40 s): walk 0.5 -> 0.15 -> 0.85 -> 0.5 at 0.1 zone/s from 5.5 s (far end at 16 s), jumps 0.15 high at 6.5,
  15.5 and 24.5 s (launch + 1.5 + 9k + 0.5). They fall in the windows during the sweep (read from a headless run:
  `test_canonical_drives_the_lobby_to_jump` asserts three counted heights). The first two bells ring inside the
  measured 20 s: `square_flashes` 4.0, under 6.
- `test_the_bell_rings_once_and_checks_the_flash` wraps `fx.pop` and `fx.flash` through a `Spy` subclass of Jump.

## Owner questions
- Hint in ready as well as play (see above)?
- The figure can pass under the striker, the score box and the centred texts (drawn over it); `player_xy` can then be a
  covered pixel (my debug-state test checks a centred player only).
