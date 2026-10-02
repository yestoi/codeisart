# it20 E0: Blob ids and velocities, the implementer's report

BASE e8335bd (checked first). Work commit 99609bd on main; this report in the commit after it.

## Files changed
- `arcade/sensed.py`: `Blob` gains, after `in_zone`, `_: dataclasses.KW_ONLY`, then `id: int = -1` (-1 untracked),
  `vx: float = 0.0`, `vy: float = 0.0` (fw/s, the source's). `__post_init__` unchanged. 4 lines.
- `tests/arcade/test_sensed.py`: three new tests after `test_blob_coordinates_are_clamped`. No existing line changed.

## New tests, each watched failing first (before the `sensed.py` edit)
- `test_blob_ids_and_velocities_default_untracked_and_still`: defaults `(-1, 0.0, 0.0)`; set by keyword; a tracked
  blob differs from an untracked one and equals it once its three fields are reset.
  RED: `AttributeError: 'Blob' object has no attribute 'id'`.
- `test_blob_new_fields_are_keyword_only`: `Blob(0.4, 0.6, 0.03, (255, 0, 0), True, 3)` raises `TypeError`; the
  positional fields are exactly `x, y, size, color, in_zone` and the keyword ones exactly `id, vx, vy`.
  RED: `AssertionError: assert [] == ['id', 'vx', 'vy']` (the sixth positional already raised before, with five
  fields; the field-list assert is what pins the keyword-only marker).
- `test_place_blob_keeps_id_and_velocity`: `place_blob` keeps `id`, `vx`, `vy` both in and out of the zone.
  RED: `TypeError: Blob.__init__() got an unexpected keyword argument 'id'`.

## Test counts and times
- `tests/arcade/test_sensed.py`: 27 passed in 0.03 s (24 before + 3). `--durations=15`: all 15 under 0.005 s, so
  E0 adds well under its +0.5 s share (about 0.01 s).
- Guards plus `test_game.py` (`test_sensed.py`, `test_actors.py`, `test_runner.py`, `test_lobby.py`,
  `test_festival.py`, `test_game.py`, whole files): 233 passed, 0 skipped, 16.72 s.
- Named guards by id: `test_actors.py::test_blob_and_audio_scripts`,
  `test_runner.py::test_games_get_only_in_zone_blobs`, `test_sensed.py::test_place_blob`,
  `test_sensed.py::test_blob_coordinates_are_clamped` (its :273 equality holds with the defaults): 4 passed.
- The whole suite was not run (the orchestrator's rule).

## Deviations from the plan
None. No existing assert changed or removed.

## Notes
- `tools/arcade_evidence.py:135` serialises dataclasses with `dataclasses.asdict`; a Blob in an evidence record now
  carries three more keys (`id`, `vx`, `vy`). Nothing reads them back by position; no change made (not my file).
- No caller rebuilds a Blob from a tuple (`Blob(*...)`) in `arcade/`, `tools/` or `tests/`.

## Owner questions
None.
