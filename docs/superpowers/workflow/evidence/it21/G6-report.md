# G6 report: C56, Jump's words out of the player's way

Files: `arcade/games/jump.py`, `tests/arcade/test_jump.py`, this report.

Changes: `FIGURE_H` 56 -> 50; new `PROMPT_Y = 51`, `PROMPT_X0 = 18`, `PROMPT_BAND = (50, 10)`, `HINT_TEXT`, `OVER_RANG`, `OVER_MISS`.
`_centred` replaced by `_prompt` (black box rows 50-59, cols 18-127, text 1x centred). ready "GET SET"; play "JUMP!" or
(hint) "RING THE BELL!", never both, no 2x "JUMP!"; over "BELL RUNG!"/"NICE TRY!"; result unchanged. Draw order: figure,
rows 60-63 black, striker, band, result number, score. Pop position unchanged.

Tests: the changed assert :130 (56 -> 50) and four new tests (prompt vs figure rect, 3 zone x x 2 phases = 6 cases; hint;
pop clear, 2 cases; over). Nothing else changed.
- `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .../python -m pytest -q -rs tests/arcade/test_jump.py`: 64 passed.
- `... tests/arcade/test_all_games.py tests/arcade/test_oracle.py -k jump`: 11 passed.
- New tests add about 0.2 s (--durations: over 0.10 s, hint 0.02 s, rest 0.01 s each), under the plan's +2 s.

Oracle metrics for jump at 128x64, 20 seeds, no failures: response_ticks 1.0, response_px 216, fidelity 0.999, range 0.685,
lit_fraction 0.0994, dim_fraction 0.0, liveliness 0.019, flash_area_raw 0.0037, square_flashes 4, score_visible 0.978,
score_legible 1.0, presence_answer_seconds 0.0, win_good 1.0, win_lazy 0.45, win_none 0.0, round_seconds 30.0,
phases_reached 1.0.

Deviations: none. TDD note: the red step was the ImportError for the new constants (tests written first); the
behavioural tests were not separately watched failing before the code. Questions for the owner: none.
