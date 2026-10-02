# it21 S report

Files: `arcade/stats.py`, `tests/arcade/test_stats.py` (both new), this report.

Tests: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs --durations=15 tests/arcade/test_stats.py tests/arcade/test_scores.py tests/arcade/test_privacy.py tests/arcade/test_doctor.py`
-> 51 passed in 0.79 s (4 new tests, all under 5 ms each). Red seen first (ImportError: no `arcade.stats`).
`arcade.__file__` resolves under the worktree.

Deviations: none. Details: a line is "bad" if it is not JSON, not an object, or has a non-string game or reason
(blank lines are ignored, not counted). `main` prints "N bad line(s) skipped" after the table when bad > 0.
`args.config` None falls back to "arcade.toml" (as `run`'s default). A missing or empty log prints "no sessions".
Table line: `game  N sessions  median Xs  reason=count ...`. `stats` imports only `arcade.config` and
`arcade.games` (no hardware module) and uses no forbidden privacy call.

Questions for the owner: none.
