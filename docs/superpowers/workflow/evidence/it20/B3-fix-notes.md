# it20 B3 fix: hostile lines in a scenario file

Base c8324fa. Test-first (superpowers TDD skill). Files: `arcade/sources/scenario.py`, `tests/arcade/test_scenario.py`.
`replay.py` is not touched.

## What changed (`arcade/sources/scenario.py`)
- (1) `ScenarioReader.__iter__` catches any `Exception` from parsing or decoding one line (RecursionError included):
  the line is skipped with one warning, `skipped += 1`, and the lines after it are read. `BAD_LINE` is gone (it
  had no other user). At open, a header that fails to parse for any reason (RecursionError included) raises the
  documented `ValueError` ("no header: RecursionError: ...").
- (2) Every float field is read through `_finite` (ValueError on NaN, Infinity, -Infinity, 1e999): the box, each
  keypoint's x, y and conf, vx, vy, scale, seen_ago, torso_per_width, a blob's x, y, size, vx, vy, and every
  float audio field (bpm still may be null). `t` and `camera_t` already were. `_box` and `_keypoints` are shared
  with `decode_raw`, so a raw record's detections now refuse a non-finite number too.
- Docstrings (module, `decode`) say so.

## New tests and how each failed on c8324fa
The probes' inputs: `"[" * 200000 + "]" * 200000` between good lines (the probe's three ticks of a standing body
at 0.5), and the probe's `"box": [0, 0, Infinity, Infinity]` with that body's keypoints.
- `test_a_deeply_nested_line_is_skipped`: `RecursionError: maximum recursion depth exceeded while decoding a JSON
  array` out of `list(ScenarioReader(...))`.
- `test_replay_reads_past_a_deeply_nested_line` (`open_replay`, `latest()` once a tick): RecursionError on the
  second `latest()`.
- `test_a_header_that_cannot_be_parsed_is_refused` (nested header, through `ScenarioReader` and `open_replay`):
  RecursionError, not ValueError.
- `test_a_non_finite_box_is_skipped`: the record came through with `box=(0.0, 0.0, inf, inf)`, `skipped` 0.
- `test_a_non_finite_box_never_reaches_a_game` (the runner probe cut to 4 s: 3 s of the Infinity box, then 1 s
  of good lines, into Jump with `strict=False`): `crashes == {'jump': 1}` (Jump's draw: "cannot convert float NaN
  to integer").
- `test_a_non_finite_blob_value_is_skipped` (`size` Infinity): two records read, not one.
- `test_a_non_finite_audio_value_is_skipped` (`level` NaN): the record came through with `level=nan`.
- `test_every_float_field_refuses_a_non_finite_number[<field>]`, 26 field paths, each line written once with each
  of NaN, Infinity, -Infinity, 1e999: 24 failed (five records read, not one); `t` and `camera_t` passed already
  (today's code checks those two), kept to pin them.

## Counts and times
`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_scenario.py
tests/arcade/test_sensed.py`:
- on c8324fa's `scenario.py` with the new tests: 31 failed, 45 passed;
- with the fix: 76 passed (scenario 16 + 33 new, sensed 27), 0 skipped, 0.24 to 0.31 s. The slowest new test,
  `test_a_non_finite_box_never_reaches_a_game`, 0.04 to 0.05 s; the rest under 0.005 s each (the nested line too).
The whole suite was not run (the brief).
