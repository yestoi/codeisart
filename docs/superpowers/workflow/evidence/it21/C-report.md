# it21 C: `calibrate`, the implementer's report

Branch `worktree-agent-ad3dc68e4cc19d5c8`, from BASE 90c3397 (checked with `git rev-parse --short HEAD`).
`import arcade` from the worktree root resolves to the worktree's `arcade/__init__.py`.

## Files

- `arcade/calibrate.py` (new): the constants as the plan gives them (`HOLD_SECONDS` ... `VIEW`), `Calibrator(data_dir)`
  (the `LobbyLike` methods, `request = None`, `result`, `failed`, `phase`, `debug_state`: `phase`, `seconds`,
  `stands`, `zone`), `view_xy(x, y)` (a camera place to its wall pixel in `VIEW`), `zone_of(anchors)`, `main(args)`.
- `tests/arcade/test_calibrate.py` (new): 9 tests, plus `sheet_scene(games, cfg)` and `sheet_frames()` for I2.
- This report.

No other file touched. `arcade/calibration.py`, `main.py`, `headless.py`, `actors.py` unchanged.

## Tests

Command (from the worktree root):
`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs --durations=15 tests/arcade/test_calibrate.py`
-> `9 passed in 2.70s`.

Guards with mine: `... -m pytest -q -rs tests/arcade/test_calibrate.py tests/arcade/test_calibration.py
tests/arcade/test_doctor.py tests/arcade/test_runner.py` -> `129 passed in 7.67s` (no skip in these files).
The whole suite was not run (the task's rule: never the whole suite; the orchestrator runs it after the merges).

Time my tests add (`--durations=15`): 0.86 s (the nobody run's 62.5 s of ticks, a module fixture), 0.47 s (the
actors' run, a module fixture shared by four tests), 0.45 s (`test_main_turns_hide_still_off`, which ticks the
actors' scene once more through `main`), 0.41 s (`test_a_zone_that_would_not_load_fails`), 0.24 s (the flash rule:
`concurrent_area` over 855 frames), 0.18 s (walking), 0.01 s (jump): about 2.6 s, under the planned +3 s.

TDD: the tests were written first and failed at import; then against a stub (constants, a do-nothing Calibrator)
8 of 9 failed on their own asserts. The ninth, `test_a_jump_stays_in_the_calibrated_zone`, passed on the stub (no
file: the default zone also holds those jumps), so it now first requires the calibrated file's zone. A mutation
(the review's thin zone: y from the anchors alone) fails both that test and `test_calibrate_with_actors_writes_zone`.

The tests (all actors through `run_headless(..., lobby=calibrator)`, no real clock, no camera):
- `test_calibrate_with_actors_writes_zone`: a person (id 1) raises both hands, stands still at x 0.3 and 0.7 (height
  0.5) and 0.5 (height 0.6, `scale_to`), stays for the baseline, leaves; a still lamp at (0.1, 0.1), outside the
  default zone; a torch carried across the clear for 3 s. The file loads equal to `result`: zone x 0.25 to 0.75
  (the anchors +- MARGIN), y 0.2 to 0.8, `min_height` 0.8 x the far body's height (0.40), `baseline_scale` within
  0.01 of the near body's scale (0.27), one static light (the lamp, never the torch), radius `STATIC_RADIUS`,
  `audio_floor_db` the default (headless has no microphone), `calibrated` true.
- `test_a_jump_stays_in_the_calibrated_zone`: that zone; a 0.15 jump at (0.3, 0.5), (0.7, 0.5), (0.5, 0.6) peaks at
  0.15 and is `in_zone` on every tick; a 0.15 jump at height 0.7 leaves even the default zone.
- `test_main_turns_hide_still_off`: `make_sources` patched at `arcade.calibrate.make_sources` (a stand-in camera with
  `features.hide_still = True`); `Runner.loop` patched with one that ticks the actors' scene until `until()`. Checks:
  `make_sources(cfg, (128, 64), calibration=Calibration())`, `hide_still` False at loop time, a strict runner with no
  games, the default calibration, `until == calibrator.done`, the camera and the display closed, the file in
  `cfg.data_dir`, 0. Then a camera without `features` (`NoSource`) and a loop that does nothing: 1, no file.
- `test_nobody_comes_writes_no_file`: an empty aim; `failed` at 60 s (within 2 ticks), "NO ONE CAME" on the wall,
  `done()` 2 s later, no file.
- `test_a_body_restarts_the_clear`: in the actors' run the operator leaves and a visitor walks in during the clear;
  the clear lasts over `CLEAR_SECONDS` + 1 s and ends `CLEAR_SECONDS` after the last body (within 2 ticks).
- `test_a_walking_body_does_not_stand`: after aim, a body walking 0.05 fw a second for 6 s makes no stand
  (`far_left`, 0 stands throughout); still at the end for 2 s, it makes one.
- `test_every_step_keeps_rows_60_to_63_dark_and_the_flash_rule`: both runs (every step, and aim then failed): the
  phases in order, governor held 0 ticks, rows 60 to 63 dark in every raw frame, no channel lit under
  `feel.DIM_LEVEL`, each step's words found at 1x at row 1 by `feel.find_text` on its first tick, raw
  `concurrent_area` under `SMALL_AREA` (the whole actors' run; the nobody run around its change of words).
- `test_dots_and_the_zone_are_drawn_in_the_view` (not in the plan's list): every keypoint of a body is a `DOT` at
  `view_xy`, the lamp a `LIGHT`; in the saved frame the zone's four corners are `ZONE` and its inside is not.
- `test_a_zone_that_would_not_load_fails`: `MARGIN` patched to -0.3 (x0 0.6 past x1 0.4): `failed` names the zone,
  "NOT SAVED" on the wall, no file.

I2's sheet works: `python -m tools.arcade_shot jump --lobby tests.arcade.test_calibrate:sheet_scene --scenario
tests.arcade.test_calibrate:sheet_frames --out <scratchpad>/calibrate --every 60 --cols 5 --look both` gave 855
frames, all non-black, final state `saved`, 3 stands, zone (0.25, 0.2, 0.75, 0.8), held 0. I read the plain sheet:
every step's words, the dots, the lamp and the zone outline as it grows. The images went to the scratchpad only.

## How it reads the plan (choices where the plan is silent)

- Time is `sensed.t` (the runner's). Each step's timeout runs from the step's start; the clear's restarts do not
  reset it (the plan: "a step that has not ended in `STEP_TIMEOUT`").
- aim: any body with `both_hands_up`, through `input.Hold(HOLD_SECONDS)` (its default 0.25 s grace for a dropped
  wrist). Stands and the baseline: the largest body by `scale`; a tick without it, or with another id as the largest,
  starts the window again; the window starts again at each step's start. Still: every anchor of the last
  `STILL_SECONDS` within `STILL_FW` (hypot of x and y) of the window's median, after that body has been seen that
  long. A stand keeps the median anchor x, y and the median `Body.height` (box height).
- clear: any body in `sensed.bodies` (in the zone or not) restarts it. Lights are counted on `camera_fresh` ticks
  (captures): each blob joins the nearest light already seen within `STATIC_RADIUS` (once per capture), and a light
  seen in at least `STATIC_SHARE` of the captures is kept at its mean place. The floor: the last `floor_db` of a
  clear tick on which `set_status` said the microphone was available.
- Saving: the `Calibration` is checked with `arcade.calibration._from_json(json.loads(json.dumps(asdict(cal))))`,
  the very check `load_calibration` makes, before `save_calibration`; a `ValueError` or an `OSError` (the write)
  fails the run with "NOT SAVED" and writes nothing. The file is written on the tick saved begins.
- `debug_state["seconds"]` is the seconds in the current phase; `zone` is `zone_of` the stands so far, rounded to
  3 places, None before the first stand.
- Drawing (128x64 only): the zone outline (`ZONE` = (255, 200, 0)), then each blob as a dot (`LIGHT` = (255, 0,
  255)), then each confident keypoint (`DOT` = (0, 255, 0)), then the words (white) over a black box on rows 0 to 9.
  `VIEW` spans rows 10 to 59, so nothing reaches rows 60 to 63. The clear's `<n>` is the whole seconds left, 10 to 1.
- `main(args)`: `load_config(args.config)`; `make_sources(cfg, cfg.size, calibration=Calibration())`; `hide_still`
  set False through `getattr(camera, "features", None)`; `Font.load(Path(cfg.font_path))` as `run` does;
  `build_display` imported inside `main` (arcade.main imports this module lazily, I1); `Runner(cfg, display, font,
  cal, [], calibration=Calibration(), strict=True)`, `loop(camera, audio, until=cal.done)`; ^C ends it as `run`
  does; display closed, then the sources, in `finally`s; prints "calibrate: saved PATH" (0) or "calibrate: nothing
  saved (REASON)" (1).

## Deviations from the plan

1. Blobs drawn as dots (`LIGHT`). The plan names keypoint dots and the zone; without the lights the clear step
   shows nothing of what it records (the lamp). Static dots only, so the flash rule holds (checked).
2. A failure that is not "nobody came" (a calibration that would not load, or a write that fails) shows "NOT SAVED"
   rather than "NO ONE CAME"; `failed` holds the reason (for the zone it is `_from_json`'s message, which names the
   zone).
3. `test_nobody_comes_writes_no_file` runs 62.5 s, not 61 s, so it also sees `done()` (END_SECONDS after the
   failure at 60 s); with 61 s `done()` is still False and the loop would not have ended.
4. `arcade.calibration._from_json` (a private name) is imported to check the file before writing it, so a saved
   file always loads back; `calibration.py` itself is unchanged.
5. One test beyond the plan's list: `test_dots_and_the_zone_are_drawn_in_the_view`.

## Questions for the owner (none blocks; the plan's reading is built)

1. A stand is not required to be away from the stands before it. If the operator is still standing at the far left
   2 s after "STAND FAR RIGHT" shows, far_right records the same place and the zone is too narrow, silently (the
   outline on the wall shows it). A guard (a stand at least, say, 0.1 fw from every earlier stand) is about four
   lines; not built, as the plan does not name it.
2. A body that drops out for one capture (no body in a tick) restarts a stand's window. With a real tracker this is
   rare while a person stands still, so no grace was added.
3. The camera frame's edge is not drawn (only the zone so far): while aiming, the wall shows dots on black with no
   frame line round `VIEW`. A 1 px outline of `VIEW` would show where the camera's frame ends; not built.
