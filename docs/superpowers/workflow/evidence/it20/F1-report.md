# F1 report (C55, Copy Me's outline colour)

Base b4f1e9b. Files: `arcade/games/copyme.py` (`OUTLINE_COLOR = (255, 0, 255)`, docstring says magenta; every use is the one constant, so outline, head circle and the small target all follow), `tests/arcade/test_copyme.py`, `tests/arcade/test_swat.py`.

## Tests
- `test_copyme.py::test_the_outline_differs_from_every_figure_colour` (new): distance to PLAYER_COLORS[0], [1] and MATCH_COLOR >= 150, and a `duo` play frame has outline pixels and seat b pixels. Failed first: `40.0 >= 150.0` (cyan vs seat b (0,160,255)). Now passes. Note the plan quoted 282/301/413; the real seat-b distance from the old cyan was 40.
- `test_copyme.py::test_own_drawing_keeps_rows_60_to_63_dark[canonical|duo]` and `test_swat.py::test_own_drawing_keeps_rows_60_to_63_dark[canonical|duo]` (new): guards, passed at once (P2: those drawings never light rows 60 to 63); they follow `test_flap.py:307`.
- Changed assert: `test_copyme.py:178` `(0, 200, 255)` to `(255, 0, 255)`; docstring line 1 says magenta. No other assert touched.

## Runs
- `tests/arcade/test_copyme.py tests/arcade/test_swat.py`: 90 passed, 35.6 s (2 skip-free). `test_all_games.py + test_oracle.py -k "copyme or swat"`: 22 passed (the -k applied to all files in that call), 39 s. `test_game.py`: 42 passed.
- Slowest own: swat good_beats_lazy 13.5 s, copyme 7.4 s (existing); new tests 0.5 s each (4 new in copyme/swat about 2.2 s total plus the colour test).

## Copy Me feel (128x64, 20 seeds), all budgets met, failures []
flash_area_raw 0.0110, square_flashes 4.0, win_good 1.0, win_lazy 0.4, win_none 0.0, fidelity 0.9996, range 0.70, lit_fraction 0.108, dim_fraction 0, score_visible 0.978, phases_reached 1.0.

## Deviations / questions
None. The operator reads the `duo` sheet again (I2).
