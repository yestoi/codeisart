# it21 R report: `record` (spec 6.3, 6.5, 9.5) and the privacy rule

Implementer: opus, worktree `/Users/trey/dev/codeisart/.claude/worktrees/agent-a47649598ce80c7b1`, branch
`worktree-agent-a47649598ce80c7b1`. Started at 90c3397 (checked: BASE, main after E1). `import arcade` resolves
under the worktree (checked). Code commit: 79ae0e0. This report is committed after it.

## Files (all new; nothing else touched)
- `arcade/sources/record.py`:
  - `COUNTDOWN = 3`, `REC_COLOR = (255, 0, 0)`, `TEXT_COLOR = (255, 255, 255)`, plus `REC_XY = (1, 1)`,
    `CUE_Y = 28`, `MARKER_ROWS = 4`, `MAX_CUE = 21`.
  - `RecordScript(name, seconds, cues)` (frozen) and `RECORD_SCRIPTS`: spec 9.5's twelve with the plan's seconds;
    cues written from each description (door-point: "STAND IN THE MIDDLE", then for doors 1 to 3 "POINT AT DOOR n",
    "HOLD" 2 s, "HAND DOWN", then "SWEEP, DON'T STOP" 21 s to 27 s, "HAND DOWN"). Every cue at most 21 characters,
    upper case, the first at t 0, all before the script's end.
  - `refusal(cfg, *, consent, raw) -> str | None`: no consent; colorlight without `allow_record`; `--raw` on colorlight
    (even with `allow_record`); `--raw` unless `cfg.camera == "mediapipe"`. Reads cfg only.
  - `RecordScene(script, writer, *, with_motion, raw_camera=None)`: the LobbyLike methods, `info = None`,
    `request = None`; `debug_state()` is exactly `{"phase", "seconds", "cue", "written"}`. "countdown" 3 s (nothing
    written), "rec" `script.seconds` (writes `dataclasses.replace(sensed, t=t - start, camera_t=camera_t - start,
    motion=<(0, 0) unless with_motion>)` once a tick), then "end" (`done()`). With `raw_camera` it writes nothing and
    sets `raw_camera.tap = writer.write` on the tick rec starts, `None` on the tick it ends. Draw: every body as a
    figure (`figure_rect`, `draw_figure`, `PLAYER_COLORS[i % 2]` by order), rows 60 to 63 black, then each text over a
    black box one pixel wider than its cells all round (`_label`): countdown "3"/"2"/"1" at 2x centred; in rec "REC"
    in red at (1, 1), "<n>S" in white one space right of it, the current cue centred at rows 28 to 35.
  - `record(cfg, script, camera, audio, display, font, out, *, raw=False, with_motion=False, clock, sleep) -> int`:
    the header as the plan says (`make_header(...)` plus `header["inputs"]`; raw: `["motion", "pose"]` and
    `header["mirror"] = cfg.mirror`), `Runner(cfg, display, font, scene, [], clock=clock, sleep=sleep, strict=True)`,
    `loop(camera, audio, until=scene.done)`; `finally`: the tap `None` (raw only), `camera.close()`, then
    `writer.close()` (nested, so the writer closes even if `close()` raises). Raw counts through `_Counted`, a
    wrapper around `writer.write` handed to the scene (so to the tap). `git_sha()`: `git rev-parse --short HEAD` at
    the repository root, None when that fails.
  - `default_out(cfg, script)` and `main(args) -> int` (below).
- `tests/arcade/test_record.py`: 18 tests (the 6 amendment tests, the plan's 6 new tests, plus 6 more: the scripts,
  every cue legible, main's success and raise paths, the sheet helpers), and the module helpers
  `sheet_scene(games, cfg)` and `sheet_frames()`.
- `tests/arcade/test_privacy.py`: `test_no_forbidden_calls` plus 22 snippet cases checking that the rule catches
  each form and lets each allowed form through.

## TDD
- RED: both files written first. `test_record.py` failed at collection, `ModuleNotFoundError: No module named
  'arcade.sources.record'`. `test_privacy.py` passed at once, as the plan requires ("must pass on today's
  `arcade/`"). It is a guard over existing code. Its own failing cases are the 14 snippet cases in
  `test_the_rule_catches`.
- GREEN: 41 passed after `record.py`.
- The implementation passed on its first run, so I checked the tests with 8 temporary mutations of `record.py`
  (each reverted; `git diff --stat` empty afterwards). Each was caught:
  - `strict=False`: the raising test fails on `GuardClock`'s "record ran past 1000 ticks" instead of hanging.
  - No rows 60 to 63 band: the rows test fails.
  - No black box under the texts: the countdown and REC tests fail.
  - The tap set before the loop: the raw test fails.
  - The tap not cleared in the `finally`: the raw raising test fails.
  - The writer closed before the camera: 3 tests fail.
  - Motion kept by default: the motion test fails.
  - `t` not rebased on rec's start: the cues and countdown tests fail.
- One fix after green: `record` now returns its count after the `finally`. Before, in raw mode the count was read
  before `close()` joined the camera thread, so a capture still inside the tap call would be written but not counted.

## Tests (from the worktree root)
- `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs
  --durations=15 tests/arcade/test_record.py tests/arcade/test_privacy.py`: **41 passed in 1.20 s**.
- With the guards: the same command on `tests/arcade/test_record.py tests/arcade/test_privacy.py
  tests/arcade/test_doctor.py tests/arcade/test_scenario.py tests/arcade/test_runner.py`: **187 passed in 6.43 s**,
  no skip and no rerun.
- `/Users/trey/dev/codeisart/.venv/bin/python -c "import sys, arcade.sources.record, arcade.main; ..."` loads no
  `cv2`, `mediapipe` or `sounddevice` (`[]`). `record.py` imports `make_sources` from `arcade.sources` at module
  level and never `blobs`.
- The whole suite was not run (the task's rule).

## Time the new tests add (`--durations=15`)
About 1.2 s for both files together, inside R's +3 s share. The largest: `test_rec_frames_keep_the_flash_rule_and_
rows_60_to_63_dark` 0.25 s, the `recorded` fixture (one 151-tick run shared by four tests) 0.15 s, the motion run
0.14 s, the raw run 0.14 s, `test_no_forbidden_calls` 0.13 s, the two raising runs 0.09 s each, the rest under 0.05 s.

## The sheet helpers, checked with I2's command
`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m tools.arcade_shot jump
--lobby tests.arcade.test_record:sheet_scene --scenario tests.arcade.test_record:sheet_frames --out
<scratchpad>/it21-record/record --look both --flash-report`: 360 frames, 360 non-black, `flash_held_ticks` 0,
`flash_area` raw and pushed 0.021. The sheet shows 3, 2, 1, then REC with 0S to 8S, the cues "STAND IN THE MIDDLE",
"POINT AT DOOR 1", "HOLD", "HAND DOWN", and the figure walking in and pointing. Rows 60 to 63 are dark. The images
are in the session scratchpad, not in the evidence folder, and nothing is committed (Q98).

## Readings and deviations from the plan
1. The countdown starts at the scene's first tick. `Runner.loop`'s first tick is at t 0, and `run_headless`'s at
   1/30.
2. Rec runs for elapsed time in [0, seconds), so a sensed file holds `seconds x fps` records (60 for the 2 s test
   script). On the tick where elapsed reaches `seconds`, the scene goes to "end": it writes nothing and draws the
   figures only (no REC, no cue). That is the last pushed frame.
3. Raw timing: the tap is set in `update`, after that tick's `latest()`. So the first tapped capture is the next
   one, and the end tick's capture is still tapped. A raw file covers (start, start + seconds]: 60 captures in the
   test, within one capture of the cues' base. This matches the review's R2 reading.
4. `debug_state()["seconds"]` is the whole seconds recorded (0 in the countdown, capped at `script.seconds` in
   "end"). `written` counts the scene's own Sensed writes, so it is 0 in raw mode; raw's count is `record`'s return.
5. Every body is drawn, in zone or not (the recording shows what the camera sees). Colours cycle through the two
   `PLAYER_COLORS` by order.
6. `inputs` for a sensed file holds camera names only, as the plan says, even when a microphone is open (Q-Ra).
7. `git_sha()` gives the short sha only, with no dirty flag (the plan: "short sha or None").
8. `main` details not in the plan:
   - It loads the font before opening any source.
   - An unknown `args.script` is treated like a refusal: it prints the known names and returns 2 before anything
     opens. I1's parser `choices` makes this unreachable from the CLI.
   - The refusal line is `record refused: <why>`; the success line is `recorded N records of <script> to <path>`.
   - `make_sources(cfg, cfg.size)` is called with its default calibration (`load_calibration(data_dir)` for
     mediapipe).
   - There is no KeyboardInterrupt handling: ^C propagates after the finally blocks close the writer (so the partial
     file is a whole gzip stream), the display and the sources (Q-Rc).
9. Privacy rule, beyond the plan's list:
   - It also catches `savez_compressed`, and an `ImportFrom` alias with a forbidden name (`from cv2 import
     imwrite`).
   - `from . import wave` (a relative sibling, not the standard library) is allowed.
   - Comments and strings never count (ast).
   - `record.py` gets no exemption and needs none.
10. Test helpers in `test_record.py`:
    - `GuardClock` is a FakeClock that fails past 1000 ticks, so a non-strict runner fails the test instead of
      hanging the suite.
    - `TapCamera` is the stand-in for W's `tap`. It captures on every `latest()` from the start, plus once in
      `close()`, which stands for a capture after `done()`.
    - `logged_writer` is monkeypatched into `record_mod.ScenarioWriter` to log the order of the closes.
11. `RecordScene.__init__` calls `reset((128, 64), None)` so that `debug_state()` works before the runner resets it.

## For the integrators
- I1: `from arcade.sources.record import main as record_main; return record_main(args)` reads `args.config`,
  `args.script`, `args.i_have_consent`, `args.raw`, `args.with_motion` and `args.out` (None or empty means the
  default path). `RECORD_SCRIPTS` holds the twelve names for the parser's `choices`.
- RP: R writes `header["inputs"]` (a sorted list of `CAMERA_INPUTS` names) and, raw only, `header["mirror"]` (a
  bool). Both pass today's `check_header`, and they match RP's planned checks.

## Questions for the owner (none blocks; the plan's reading was taken)
- Q-Ra: once the M5 audio source exists, should a sensed file's `inputs` also list `"audio"` while the microphone is
  available? Today it is the camera's names only, as the plan says, and no game reads audio (Q99).
- Q-Rb: the cue texts (Q142 leaves them to you) are in `RECORD_SCRIPTS`. Change any wording you want; each must
  stay 21 characters or fewer, and the tests check that.
- Q-Rc: ^C during a recording keeps the partial file (closed properly) and exits with the traceback. Should `main`
  catch it, print the path and return 1 instead?
- Q-Rd: the end tick (the last frame) shows the figures only. Would you like a short "SAVED" card instead?
