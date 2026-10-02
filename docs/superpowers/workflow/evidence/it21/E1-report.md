# it21 E1 report: per-input availability (C35), a loop that can stop, the vy unit

Implementer: opus, main checkout, serial. Started at fd7de35 (checked). Code commit: a0dabbc (BASE for batch 1).

## Files changed
- `arcade/sensed.py`: `CAMERA_INPUTS = frozenset({"pose", "blobs", "motion"})` and `AUDIO_INPUTS =
  frozenset({"audio"})` defined beside `MOTION_GRID` (:36-37); `Blob.vy`'s comment now says frame heights per second,
  the source's (Q131) (:284; `vx` keeps widths).
- `arcade/runner.py`:
  - imports `AUDIO_INPUTS, CAMERA_INPUTS` from `arcade.sensed` (its own definitions removed), so
    `arcade.runner.CAMERA_INPUTS is arcade.sensed.CAMERA_INPUTS`.
  - new module function `_provides(camera) -> frozenset[str]`: `getattr(camera, "provides", CAMERA_INPUTS)`; not a
    `set`/`frozenset` of `str` raises `TypeError`; returns `frozenset(provides) & CAMERA_INPUTS`.
  - `Runner._source(name, source, check, provides=False)` now returns `(got, ok, inputs)`; with `provides=True` it
    calls `_provides(source)` in the same `try` as `latest()`, so a raising or malformed provides fails the source
    exactly as a raising `latest()` does (logged once per run of failures, `(None, False, frozenset())`).
  - `sense()`: the camera is read with `provides=True`; while the result is fresh, bodies are kept only with
    `"pose"`, blobs only with `"blobs"`, the grid only with `"motion"` (else `None`); status inputs are
    `provides if camera_ok` plus `AUDIO_INPUTS if mic_ok`.
  - `loop(camera, audio, max_ticks=None, until=None)`: after each tick, `if until is not None and until(): break`.
- `tests/arcade/test_runner.py`: additions only (no existing line changed; :694, :697, :711 and the fake `Camera`
  at :657 untouched). New: `WALL = (128, 64)`, fakes `Seeing(Camera)` (declares `provides`) and
  `RaisingProvides(Camera)` (a `provides` property that raises `OSError`), and the four acceptance tests:
  `test_sense_claims_only_what_the_camera_provides`, `test_a_camera_without_provides_claims_every_camera_input`,
  `test_a_raising_provides_fails_the_camera`, `test_loop_stops_when_until_is_true`.

## TDD
RED (tests written first, run before any code): 4 failed for the expected reasons: status `{"pose","blobs","motion"}
!= {"pose"}`; `module 'arcade.sensed' has no attribute 'CAMERA_INPUTS'`; the body still passed with a raising
provides; `Runner.loop() got an unexpected keyword argument 'until'`. GREEN after the code above.

## Tests (command run from /Users/trey/dev/codeisart)
- `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs
  --durations=15 tests/arcade/test_runner.py tests/arcade/test_sensed.py` (absolute paths): 114 passed in 4.41 s.
- Guard: same command on `tests/arcade/test_game.py tests/arcade/test_lobby.py tests/arcade/test_headless.py
  tests/arcade/test_doctor.py`: 116 passed in 12.43 s (no flaky rerun needed).
- Extra guard (the other callers of `Runner.loop`): `tests/arcade/test_sources.py tests/arcade/test_main.py`: 9
  passed in 1.68 s.
- The whole suite was not run (the task's rule; the orchestrator runs it once after the last merge).

## Time the new tests add
`--durations=0` on the four new tests: every setup, call and teardown under 0.005 s (all 12 hidden); the four ran in
0.04 s together. Well inside E1's +0.5 s share.

## Readings and deviations from the plan
1. "`s.motion` all False" vs "no grid (`None`)": the runner passes `motion=None` to `Sensed`; `Sensed.__post_init__`
   turns `None` into the empty `(0, 0)` grid, and `sense()`'s `.with_motion(cfg.size)` makes it an all-False
   `(height, width)` grid, `(64, 128)` at the wall. The existing representation is kept; the test asserts
   `s.motion.shape == (64, 128) and not s.motion.any()`.
2. Names in `provides` outside `CAMERA_INPUTS` (for example `"audio"`) are cut, not a failure (the plan's
   `provides & CAMERA_INPUTS`); the test pins that a camera can never claim the microphone. Only the type is checked
   (a `set`/`frozenset` whose items are all `str`; a list, tuple, str, dict, `None` or `{1}` fails the camera).
3. `provides` is read only for the camera (`_source(..., provides=True)`); the audio source's `provides`, if any, is
   ignored (the plan names the camera only). `_source` now returns a 3-tuple; its only callers are in `sense()`.
4. The filter applies whenever the camera result is fresh, also while `available` is False (today such a result's
   bodies still pass with `camera_ok` False; unchanged). `provides` itself is read even when `latest()` gives None,
   so a raising provides with no capture is still a logged failure.
5. `loop` breaks right after the tick on which `until()` is True, before the period's sleep (no reason to wait a
   period before returning). `until()` is not guarded: if it raises, the exception leaves `loop` (record and
   calibrate run strict, and R's `test_a_raising_scene_ends_record_and_closes_the_writer` relies on raises coming
   out).
6. The new tests run at 128x64 (`WALL`, Q82), not the file's `SIZE = (64, 64)` the older tests use; `WALL` is
   defined beside the new fakes (after :712), not at the top, so the plan's line numbers :694, :697, :711 hold.
7. `arcade/sensed.py`'s two new lines shift `Blob.vy` from :282 to :284 (the plan's :282 is the line before E1).

## Questions for the owner (none blocks; the plan's reading was taken)
- Q-E1a: `getattr(camera, "provides", CAMERA_INPUTS)` (the plan review's instruction) treats a `provides` property
  that raises `AttributeError` as absent, so that camera claims every input instead of failing. Any other exception
  fails the camera (tested with `OSError`). Acceptable, or should an `AttributeError` raised inside a property also
  fail the camera (it would need `inspect.getattr_static` to tell "absent" from "raised")?
