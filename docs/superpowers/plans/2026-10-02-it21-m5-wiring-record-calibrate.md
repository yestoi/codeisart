# Iteration 21 (arcade): C56 (Jump's layout), M5's second lane: the wiring with C35, raw replay, record, calibrate
BASE: HEAD after E1 is committed (the orchestrator gives the sha). Thin plan. Not a safety slice: no change to
`arcade/flash.py`, `brightness.py`, `show/display/colorlight.py`, or the runner's order of limiter, governor, push.
"Spec" = `docs/superpowers/specs/2026-09-26-wall-arcade-design.md`, not edited. "Core plan" =
`docs/superpowers/plans/2026-09-26-wall-arcade-core.md`: a draft to test, not text to paste; its amendments (Tasks
12, 15, 16, 18: lines 588 to 700) and today's code win over its bodies. In `docs/superpowers/workflow/evidence/it21/`:
`plan-writer-report.md` (Q136 to Q147, defaulted) and `plan-review.md` (B1 to B7, notes 1 to 4: fixed in this text).
## Global Constraints
- Test command, from the checkout's (or worktree's) root: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
  /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs`. Baseline at 3a3fe02's tree: 2236 collected, 2233
  passed, 3 skipped, 457.24 s on the shared Mac. Worktrees show a 4th skip (no `models/` there). One command per Bash
  call; tools as modules (`python -m tools.arcade_shot`); no `cd`.
- The orchestrator runs the FULL suite once, after the last merge. After each other merge: a subset that names
  `tests/arcade/test_all_games.py` FIRST (else the join waits for the whole pool), then the merged task's test files,
  `tests/arcade/test_oracle.py` and `tests/arcade/test_game.py`. Implementers run their own files and the generic
  ones they touch (`test_all_games.py -k jump`, `test_oracle.py -k jump`), never the whole suite.
- Touch only your task's files. Test-first. No removed or weakened assert; no band in `arcade/feel_budgets.toml` or a
  `*_feel.toml` loosened. The only changed asserts are the three named below: `tests/arcade/test_jump.py:130`
  (G6), `tests/arcade/test_pose_mediapipe.py:149` (W) and `tests/arcade/test_scenario.py:217-218` (RP); one changed
  setup, `tests/arcade/test_blobs.py:89` (W). An assert this plan does not name that would have to change: stop.
- 128x64 only (Q32, Q33, Q82): no code, test or tuning for another size (the generic soak at 96x48 is the engine's and
  stays). Rows 60 to 63 stay dark in everything this slice draws (the runner's marker): Jump, REC, calibrate.
- The frozen protocol is unchanged; `test_protocol_members_are_the_frozen_set` is not edited. No game reads the
  microphone or the motion grid (Q99). Nothing is fetched, nothing goes to the Pi or the card, nothing is pushed.
- Flash (C24, guide 6): Jump's frames keep governor held ticks 0 and raw `concurrent_area` under 0.1. REC and
  calibrate draw static text and dots only: no blink, no stripe; saturated red counts double.
- Colours saturated, low channels 0, no channel set under 140 alone (`feel.DIM_LEVEL`); Jump's score at 2x, drawn
  last over its black box. `Sensed`/`Audio`/`Blob`/`Body` built with keywords after their positional fields (C21);
  `time.thread_time` for perf tests (marked `perf`); seeds `zlib.crc32`.
- `import arcade.main` loads no `cv2`, `mediapipe` or `sounddevice` (`tests/arcade/test_doctor.py:46`,
  `test_importing_main_loads_no_hardware_module`): `arcade/sources/blobs.py` imports `cv2` at its top, so nothing
  `arcade.main` or `arcade/sources/__init__.py` imports at module level may import `blobs`; the raw replay path and
  `pose_mediapipe` import it inside functions or are themselves imported lazily (they are today).
- Privacy (spec 6.5): nothing under `arcade/` writes but Sensed and raw scenario records (`ScenarioWriter`), scores,
  the sessions log and `calibration.json`; raw frames only through `record --raw`, from the source thread, via
  `scenario.encode_raw` (base64 and `struct`: no forbidden call, so no exemption is used). `run` logs no new INFO line
  (`test_main.py::test_run_opens_a_128x64_wall_by_default` pins the list).
- Under load `tests/arcade/test_headless.py::test_tick_budget_with_the_governors_share` (:236-237) and
  `tests/test_show_shot.py::test_strobe_session_is_held` fail and pass on a rerun: rerun them alone before a revert.
- Suite: at most 540 s (Q102). Shares: E1 +0.5 s, G6 +2 s, W +1.5 s, RP +1.5 s, R +3 s, C +3 s, S +0.2 s, I1 +1.5 s:
  about +13 s, about 470 s. No game is added: the pool stays 480 plays. Report yours (`--durations=15`).
## Lanes and merge order
1. SERIAL, main checkout: E1 (one implementer, `model: opus`), committed, its files' tests run. BASE is E1's commit.
2. PARALLEL batch 1, `isolation: "worktree"`, ONE message: G6 Jump's layout (`model: sonnet`), W the wiring (`opus`),
   R record (`opus`), C calibrate (`opus`). Each first checks `git rev-parse --short HEAD` equals BASE.
3. Merge G6, W, R, C in that order with `git -C /Users/trey/dev/codeisart merge --no-ff`, the subset after each; a
   merge that breaks it is undone with `git revert -m 1` and sent back once.
4. PARALLEL batch 2, from the merged HEAD (BASE2), ONE message: RP raw replay and the range check (`opus`), S stats
   (`sonnet`). Merge RP, then S, the subset after each. Then I1 (orchestrator), the full suite once, then I2.
No cross-imports between parallel tasks beyond BASE: R and C import E1's names; R writes the header key `inputs`
itself (RP's reader reads it; `check_header` ignores unknown keys today).
Files by task (no file under two tasks):
- E1: `arcade/runner.py`, `arcade/sensed.py`, `tests/arcade/test_runner.py`. G6: `arcade/games/jump.py`,
  `tests/arcade/test_jump.py`. W: `arcade/sources/blobs.py`, `arcade/sources/pose_mediapipe.py`,
  `tests/arcade/test_blobs.py`, `tests/arcade/test_pose_mediapipe.py`.
- R: `arcade/sources/record.py`, `tests/arcade/test_record.py`, `tests/arcade/test_privacy.py` (all new).
- C: `arcade/calibrate.py`, `tests/arcade/test_calibrate.py`. S: `arcade/stats.py`, `tests/arcade/test_stats.py`.
- RP: `arcade/sources/replay.py`, `arcade/sources/scenario.py`, `tests/arcade/test_scenario.py`.
- I1: `arcade/main.py`, `arcade/sources/__init__.py`, `arcade/sources/scripted.py`, `arcade/sources/README.md`,
  `tests/arcade/test_main.py`, `tests/arcade/test_sources.py`.
Not edited: `sources/camera.py`, `actors.py`, `calibration.py`, `figure.py`, `attract/lobby.py`, `headless.py`,
`jump_bots.py`, `jump_feel.toml`, and every shared file that I1 does not list (`feel_budgets.toml`, `config.py`, ...).
## E1: per-input availability (C35), a loop that can stop, the vy unit (opus, main checkout, serial)
- `CAMERA_INPUTS` and `AUDIO_INPUTS` move from `arcade/runner.py:54-55` to `arcade/sensed.py` (beside `MOTION_GRID`,
  :35); `runner.py` imports them, so `arcade.runner.CAMERA_INPUTS` still resolves.
- A camera source may declare `provides`: a `set`/`frozenset` of names in `CAMERA_INPUTS`. Absent: `CAMERA_INPUTS`
  (today's behaviour). `Runner._source` (`runner.py:566`) reads it in the same `try` as `latest()`: one that raises
  or is not a set of strings fails the source as a raising `latest()` does (logged once, unavailable).
- `sense()` (`runner.py:577-608`): `inputs` is the camera's `provides & CAMERA_INPUTS` when `camera_ok` (was all of
  `CAMERA_INPUTS`, :605) plus `AUDIO_INPUTS` when `mic_ok`; a camera that does not provide `"pose"` gives no bodies,
  `"blobs"` no blobs, `"motion"` no grid (`None`). The lobby already offers a game only when `needs <= inputs`
  (`arcade/attract/lobby.py:145`); `Runner.available()` (:334, the games not hidden) does not change.
- `loop(camera, audio, max_ticks=None, until: Callable[[], bool] | None = None)` (:610): also stops after the first
  tick on which `until()` is True (record and calibrate stop on their scene's `done`). `max_ticks` still bounds.
- `arcade/sensed.py:282`: `vy`'s comment says frame heights per second, the source's (Q131); :281 keeps widths.
- Unchanged: `test_runner.py:694`, `:697` and `:711` (the fake `Camera`, :657, has no `provides`: the default).
- Acceptance (`tests/arcade/test_runner.py`): `test_sense_claims_only_what_the_camera_provides` (`provides={"pose"}`
  with blobs and a grid in `latest()`: status inputs `{"pose"}`, `s.blobs == ()`, `s.motion` all False; with
  `{"pose", "blobs"}` the blobs pass); `test_a_camera_without_provides_claims_every_camera_input`;
  `test_a_raising_provides_fails_the_camera` (logged once, status `(False, ..., set(), ...)`);
  `test_loop_stops_when_until_is_true` (until True after 3 ticks: 3 ticks; with `max_ticks=2`: 2).
## G6: C56, Jump's words out of the player's way (sonnet, worktree)
The roadmap's C56 is the requirement. Layout at 128x64, as numbers the tests check:
- The figure: `FIGURE_H` 56 becomes 50, so its rect is rows 0 to 49 at every `zone_x` (columns as today:
  `figure_rect`, centred on `round(zone_x * 127)`; the column backlash unchanged).
- The prompt band: rows 50 to 59 (text at `PROMPT_Y = 51`, 1x, over a black box rows 50 to 59), columns
  `PROMPT_X0 = BAR_X + BAR_W + 2 = 18` to 127, the text centred in them. The striker (columns 6 to 15), the score
  (top right, rows 0 to 17) and rows 60 to 63 are outside it. So no prompt pixel meets the figure's rect anywhere.
- `ready`: "GET SET" in the band. `play`: "JUMP!" in the band; after `HINT_IDLE_SECONDS` not active, the band shows
  `HINT_TEXT = "RING THE BELL!"` instead (never both; `hint` True while it shows; no 2x "JUMP!" any more).
  `result`: as today (the attempt's number at 2x right of the bar; Q127 stands). `over`: the band shows
  `OVER_RANG = "BELL RUNG!"` when `rang`, else `OVER_MISS = "NICE TRY!"`.
- The "DING!" pop stays at `(BAR_X + BAR_W + 16, _row(bell_cm))`: rows 24 to 34 for `BELL_CM`, so its text stays
  above row 46, clear of the band. Draw order: figure, rows 60 to 63 black, striker, the band, the result's number,
  last the score. No rule constant, bot, window or band moves; `jump_feel.toml` unchanged.
- Changed assert (named): `tests/arcade/test_jump.py:130`, the tuple's `FIGURE_H` 56 becomes 50 (the figure leaves
  rows 50 to 59 to the prompt; C56). The rest of :130 and every other assert unchanged.
- Acceptance (`tests/arcade/test_jump.py`, about 2 s): `test_the_prompt_never_meets_the_figure_rect` (`ready` and
  `play`, a player at zone x 0.15, 0.5 and 0.85: `feel.find_text` finds the phase's word at 1x with its rows in
  50 to 59 and its x at 18 or more, and the figure's rect rows are 0 to `FIGURE_H - 1`; the head disc at
  `player_xy` is lit); `test_the_hint_replaces_the_prompt` (`idle_body` in `play` past the idle time: the band holds
  `HINT_TEXT`, "JUMP!" is found at neither 1x nor 2x; after a jump, "JUMP!" again); `test_the_pop_is_clear_of_the_
  prompt` (at the bell's lowest and highest rows the pop's text rows end above row 50); `test_over_shows_a_word`
  (rang: `OVER_RANG` found; a no-jump game: `OVER_MISS`). The two rows-60-to-63 tests pass unchanged;
  `test_oracle.py -k jump` passes all 17 metrics (`score_visible`, `score_legible` too); `test_all_games.py -k jump`.
## W: blobs and motion from the camera sources (M5's wiring) (opus, worktree)
The seam is `FrameFeatures.update(frame_bgr, t)` (`arcade/sources/blobs.py:202-234`): pure, driven by synthetic
frames. `MediaPipeCamera.step` (`pose_mediapipe.py:163-178`) calls it on each capture it runs the model on.
- `FrameFeatures(size=(160, 120), calibration=None, *, mirror: bool = True, work: tuple[int, int] = WORK_SIZE,
  hide_still: bool = True)`, `WORK_SIZE = (160, 120)`: `update` first shrinks a frame wider than `work[0]` to `work`
  (`cv2.INTER_AREA`; the Mac's 640x480 becomes 160x120: S1 measured `find_blobs` 10 ms at 640x480, 0.4 ms at
  160x120; Q130). `mirror` False: blob x not flipped and `motion_grid(..., mirror=False)` (new keyword, default
  True) does not flip, so a `cfg.mirror = false` setup keeps blobs, motion and keypoints in one space. A blob within
  a `calibration.static_mask` light's radius (frame widths, `_fw`) is dropped before tracking (S1's open item 3).
  `hide_still` is an attribute: False skips `StaticMask` (it hides a still lamp after 5 s, `blobs.py:24`, long
  before calibrate's `clear` step, which must see the lamp to record it).
- `MediaPipeCamera`: `provides = CAMERA_INPUTS` (class attribute); `self.features = FrameFeatures(size,
  calibration, mirror=cfg.mirror)` (`size` the wall's, the motion grid; the calibration the source's, as its
  `BodyTracker`'s); `step` returns `(capture_t, bodies, blobs, motion)`; the docstrings (:1-3, :124) lose "until M5".
- Raw captures for `record --raw` (cut with it): `tap: Callable[[RawRecord], None] | None = None` attribute; when set,
  a due capture also calls `tap(RawRecord(capture_t, detections=<merged, mirrored, before the tracker>,
  frame=<the unflipped frame shrunk to 160x120, grey>))` on the camera's thread (samples empty: no audio, Q99).
- Changed assert (named): `tests/arcade/test_pose_mediapipe.py:149`, before `blobs == () and motion is None`, after
  `blobs == () and motion.shape == (64, 128) and not motion.any()` (the first capture of the fake's blue frame: no
  light, no motion yet); the test's name stays.
- Changed setup (named; no assert changes): `tests/arcade/test_blobs.py:89`, `FrameFeatures()` becomes
  `FrameFeatures(work=(200, 150))`, so the test's 200 px frames are not shrunk and its asserts at :99-100 hold.
- Acceptance (`tests/arcade/test_blobs.py`): `test_a_640x480_frame_is_shrunk_first` (a red light drawn at the same
  place at 640x480 and 160x120 gives the same blob x, y within 1/160; `find_blobs` spied: it sees (120, 160, 3));
  `test_mirror_off_keeps_camera_x_for_blobs_and_motion`; `test_a_blob_in_the_static_mask_is_dropped`;
  `test_hide_still_off_keeps_a_still_lamp` (still 12 s: shown on every frame; hidden after 5 s by default); perf
  `test_features_under_3ms_at_640x480_input` (`thread_time`, mean of 50). (`test_pose_mediapipe.py`):
  `test_step_returns_blobs_and_motion` (the fake capture gives a frame with a red light moving 8 px a capture: the
  second due capture has one blob, an id, `vx` over 0, and lit motion cells); `test_features_use_the_wall_grid_and_
  the_sources_calibration`; `test_mediapipe_provides_every_camera_input`; `test_tap_gets_one_raw_record_per_due_
  capture` (grey 160x120 unflipped, detections mirrored; none on a skipped frame; none without a tap).
## R: `record` (opus, worktree; `arcade/sources/record.py`, spec 6.5's exemption module)
The recording runs a `Runner` with a `RecordScene` as its lobby and no games, so every frame (countdown, REC, cue)
passes the limiter and the governor like any lobby's; the scene writes the Sensed the runner gives it, once a tick.
- `COUNTDOWN = 3` (s: "3", "2", "1" at 2x, centred, one each; nothing written), `REC_COLOR = (255, 0, 0)`,
  `TEXT_COLOR = (255, 255, 255)`. REC: "REC" in `REC_COLOR` at (1, 1), 1x, and the whole seconds recorded "12S" in
  `TEXT_COLOR` right of it, on every tick of the recording; the current cue (the last whose time has passed) centred
  at rows 28 to 35, 1x (cue texts at most 21 characters). Draw order: the bodies seen as figures (`figure_rect`,
  `draw_figure`, `PLAYER_COLORS` by order; a figure fills rows 0 to 63), then rows 60 to 63 black, then each text
  over a black box with a 1 px gutter (`feel.find_text` needs it).
- `RecordScript(name: str, seconds: float, cues: tuple[tuple[float, str], ...])` (frozen); `RECORD_SCRIPTS: dict[str,
  RecordScript]`: spec 9.5's twelve (`empty-room` 30 s, `walk-in-stand-leave` 20, `door-point` 30, `wrist-sweep` 20,
  `exit-gesture` 15, `jumps-squats` 20, `poses-8` 40, `torch-paint` 30, `idle-still` 20, `claps-tempo-voice` 30,
  `music-speaker` 30, `two-people-cross` 30), cues written from each one's description (for example `door-point`:
  "POINT AT DOOR 1", "HOLD", ... "SWEEP, DON'T STOP"). New: `tools/make_cues.py` is the show's sound cues, not these.
- `refusal(cfg, *, consent: bool, raw: bool) -> str | None` (the reason, or None; it needs no open source): no
  consent; `backend == "colorlight"` without `allow_record`; `raw` on `colorlight` always; `raw` unless `cfg.camera
  == "mediapipe"` (the only source with a `tap`).
- `RecordScene(script, writer, *, with_motion: bool, raw_camera=None)`: the `LobbyLike` methods (`reset`,
  `update`, `draw`, `done`, `debug_state`, `set_available`, `set_status`, `end_session`, `request = None`);
  `debug_state`: `phase` ("countdown", "rec", "end"), `seconds`, `cue`, `written`. In "rec" `update` writes
  `dataclasses.replace(sensed, t=t - start, camera_t=camera_t - start, motion=<empty (0, 0) unless with_motion>)`
  (a sensed file starts at 0, the cue times' base). `done()` once `script.seconds` are recorded. With `raw_camera`
  the scene writes no Sensed: it sets `raw_camera.tap = writer.write` on the tick "rec" starts and `None` on the
  tick it ends, so a raw file holds rec's captures only (raw replay's t0 is then the cues' base, within a capture).
- `record(cfg, script, camera, audio, display, font, out, *, raw=False, with_motion=False, clock=time.monotonic,
  sleep=time.sleep) -> int` (records written): header `make_header("raw" if raw else "sensed", fps=cfg.camera_fps
  if raw else cfg.fps, script=script.name, cues=script.cues, git=<short sha or None>)` plus `header["inputs"]`
  (sorted: the camera's `provides`, default every camera input, less `"motion"` unless `with_motion`; raw:
  `["motion", "pose"]` and `header["mirror"] = cfg.mirror`). `Runner(cfg, display, font, scene, [], strict=True)`
  (not strict, a raising scene becomes the title card, `runner.py:404`, and `until` never fires), `loop(camera,
  audio, until=scene.done)`; in a `finally`: the tap `None`, `camera.close()` (joins the thread), the writer closed.
- `main(args) -> int`: `args.config`, `args.script` (a `RECORD_SCRIPTS` name), `args.i_have_consent`, `args.raw`,
  `args.with_motion`, `args.out` (default `data_dir/recordings/<script>-<UTC yyyymmddThhmmss>.jsonl.gz`); a refusal
  prints the reason and returns 2 before any source or display opens; else `make_sources` (main thread),
  `build_display` (imported inside), `record(...)`, the path printed, 0; sources and display closed in a `finally`.
- Acceptance (`tests/arcade/test_record.py`, actors through `ScriptedCamera` and `NoSource`, `FakeClock`,
  `headless.RecordingDisplay`; a 2 s test script): the amendment's `test_record_requires_consent`,
  `test_record_refused_on_colorlight_without_allow_record`, `test_raw_refused_on_colorlight` (even with
  `allow_record`), `test_record_script_writes_cues` (the header's cues and script; records from t 0),
  `test_record_drops_motion_by_default` (and keeps it with `with_motion`; `inputs` says which),
  `test_rec_glyph_on_every_recorded_tick` (every pushed frame of "rec" has `REC_COLOR`'s "REC" at (1, 1) after the
  limiter and governor: `RecordingDisplay.frames`); new `test_countdown_writes_nothing_and_shows_3_2_1`,
  `test_a_refusal_opens_nothing` (`make_sources` spied: not called), `test_raw_refused_without_the_mediapipe_
  camera`, `test_raw_writes_tap_records_and_closes_after_the_camera` (a stand-in camera with `tap` that captures
  from the start: the raw file holds rec's records only, none from the countdown or after `done()`; closed after
  `close()`), `test_a_raising_scene_ends_record_and_closes_the_writer` (the raise comes out; the file is closed),
  `test_rec_frames_keep_the_flash_rule_and_rows_60_to_63_dark` (held 0; a body in view on every tick, the scene's
  own `draw` on a clear canvas as `test_jump.py:462` does: `canvas.frame[60:]` all 0). Module helpers
  `sheet_scene(games, cfg)` and `sheet_frames()` (a person walking in during `door-point`) for I2's sheet.
- `tests/arcade/test_privacy.py` (spec 6.5; core Task 20's, never built): `test_no_forbidden_calls` parses every
  `arcade/**/*.py` with `ast` and fails on an attribute or name `imwrite`, `imencode`, `VideoWriter`, `savez`,
  `tofile`, an attribute `.save`, and an import of the module `wave` (a name `wave` is allowed: `freeze.py:504`).
## C: `calibrate` (opus, worktree; spec 6.6 as a `Calibrator` driven by Sensed)
The `Calibrator` is the runner's lobby too (its drawing passes the limiter and governor), no games, writing
`data_dir/calibration.json` with `save_calibration` (`arcade/calibration.py`) on success only. It reads the
largest body's raw anchor (`Body.anchor`, camera space: bodies are placed against the default `Calibration()`).
- Constants: `HOLD_SECONDS = 2.0` (both hands up), `STILL_SECONDS = 2.0`, `STILL_FW = 0.02` (the anchor within this
  of its median over the window), `BASELINE_SECONDS = 3.0`, `CLEAR_SECONDS = 10.0`, `STEP_TIMEOUT = 60.0`,
  `END_SECONDS = 2.0`, `MARGIN = 0.05`, `MIN_HEIGHT_SHARE = 0.8`, `STATIC_SHARE = 0.8`, `STATIC_RADIUS = 0.03`,
  `VIEW = (30, 10, 67, 50)` (x, y, w, h: the 4:3 camera frame on the wall).
- Steps (`phase`), each with its words at 1x at row 1 over a black box, every confident keypoint as a dot at its
  camera place in `VIEW`, the zone so far as a 1 px outline there; rows 60 to 63 dark:
  1. `aim` "AIM: HANDS UP": ends when a body holds both hands up `HOLD_SECONDS`.
  2. `far_left` "STAND FAR LEFT", `far_right` "STAND FAR RIGHT", `near` "STAND AT THE FRONT": each ends when one body
     has stood still `STILL_SECONDS` (`STILL_FW`): it keeps the median anchor and the body's height.
  3. `baseline` "STAND STILL": still `BASELINE_SECONDS`: `baseline_scale` = the median `scale`.
  4. `clear` "CLEAR THE FRAME <n>": `CLEAR_SECONDS` with no body (a body restarts it): `static_mask` = the blobs seen
     in at least `STATIC_SHARE` of the captures, radius `STATIC_RADIUS`; `audio_floor_db` the last `floor_db` when
     the audio is available, else the default. (Spec 6.6 step 5, exposure lock, is the IMX500's, core Task 19.)
  5. `saved` "SAVED" for `END_SECONDS`, then `done()`. Zone: x from the stands' anchors, min to max, widened by
     `MARGIN`; y from `min(0.2, top - MARGIN)` to `max(0.8, bottom + MARGIN)` (never thinner than the default's: a
     jump lifts the anchor out of a thin zone, `jump.py:15`); clamped to 0..1 (`_from_json` needs x0 < x1, y0 < y1,
     else `failed`); `min_height` = `MIN_HEIGHT_SHARE` x the smallest stand height; `calibrated=True`.
  Nobody comes: a step that has not ended in `STEP_TIMEOUT` is `failed` ("NO ONE CAME", `END_SECONDS`, `done()`),
  no file written. `result: Calibration | None`, `failed: str | None`.
- `Calibrator(data_dir: Path)`: the `LobbyLike` methods, `request = None`; `debug_state`: `phase`, `seconds`,
  `stands` (count), `zone` (or None). `main(args) -> int`: `make_sources(cfg, cfg.size, calibration=Calibration())`,
  `camera.features.hide_still = False` when the camera has `features` (`getattr`; no import of W), `build_display`
  inside, `Runner(cfg, display, font, cal, [], calibration=Calibration(), strict=True)` (as R), `loop(..., until=
  cal.done)`; 0 when saved, 1 when failed; sources and display closed in a `finally`.
- Acceptance (`tests/arcade/test_calibrate.py`, actors through `run_headless(..., lobby=calibrator)`): the
  amendment's `test_calibrate_with_actors_writes_zone` (a person who raises both hands, stands at x 0.3 far, 0.7
  far, 0.5 near, stands still, leaves; a still lamp blob: the zone's x holds the three anchors within `MARGIN`, its
  y spans at least 0.2 to 0.8, `min_height` 0.8 of the far height, `baseline_scale` within 0.01, one static light,
  `calibrated` true); `test_a_jump_stays_in_the_calibrated_zone` (that zone; a 0.15 jump at each stand's height:
  `in_zone` on every tick); `test_main_turns_hide_still_off` (a stand-in camera with `features`);
  `test_nobody_comes_writes_no_file` (empty 61 s of `aim`: `failed`, no file); `test_a_body_restarts_the_clear`;
  `test_a_walking_body_does_not_stand` (no stand while the anchor moves 0.05 fw a second);
  `test_every_step_keeps_rows_60_to_63_dark_and_the_flash_rule`; `test_a_zone_that_would_not_load_fails`. Module
  helpers `sheet_scene(games, cfg)` and `sheet_frames()` for I2's sheet.
## RP: raw replay and the reader's range check (opus, worktree, batch 2; cut second, keep the range check)
- Range (`scenario.py`; it20's note 7): a record holding a value out of range is a bad line (skipped, counted, one
  warning): a box value outside [0, 1] (both sources clamp it: `pose_mediapipe.box_of`, :73-80; `actors.body_box`,
  :39-43); a keypoint x or y outside [-1, 2] (raw detections hold the model's landmarks before `Body` clamps them;
  one frame past either edge is far), a keypoint `conf` outside [0, 1]; any other float of a body, blob or audio
  over `MAX_ABS = 1e3` in size (`t`, `camera_t` stay finite only). Constants `BOX_RANGE = (0.0, 1.0)`,
  `KEYPOINT_RANGE = (-1.0, 2.0)`, `MAX_ABS`. So a box of 1e308 never reaches `figure.py:27`.
- Header: `make_header(..., inputs: Iterable[str] | None = None)`: the key `inputs` (sorted list) only when given
  (`test_scenario.py:115` pins a header without it); `check_header` accepts it absent or a list of names from
  `CAMERA_INPUTS | AUDIO_INPUTS`, and `mirror` absent or a bool. `ScenarioReader.inputs -> frozenset[str]`: the
  header's, or every camera input. `ReplayCamera.provides`: the reader's `inputs & CAMERA_INPUTS` (`open_replay`).
- Raw replay: `open_replay(path, calibration=None, clock=...)` on a raw file returns `(RawReplayCamera, NoAudio)`.
  `RawReplayCamera(reader, calibration, clock)`: `latest()` runs every raw record whose `t - t0` (t0 the first
  record's) is at most `clock() - opened + 1e-9` through `FrameFeatures(MOTION_GRID, calibration, mirror=<the
  header's `mirror`, default True>)` (the grey frame as BGR) and `BodyTracker(calibration)` (its detections at `t`),
  and returns the newest `(opened + t - t0, bodies, blobs, motion)`; None before the first; `available` until the
  records end; `provides = {"pose", "motion"}` (a grey frame has no saturated halo: no blobs; Q140). `blobs` is
  imported inside the raw path only. `NoAudio`: `latest()` None, `available` False (no audio source, Q99).
- Changed assert (named): `tests/arcade/test_scenario.py:212-218`, `test_raw_file_is_not_replayed_yet`: its
  `pytest.raises(ValueError, match="raw")` (:217-218) goes with the test; raw replay is what this task builds.
- Acceptance (`tests/arcade/test_scenario.py`): `test_raw_file_replays_through_features_and_tracker` (three raw
  records 0.1 s apart, a standing body's detections and a bright block moving across the frame: tracked bodies with
  one id, lit motion cells from the second capture, no blobs); `test_raw_replay_paces_by_capture_time` (at +0.05 s
  the first capture, at +0.1 s the second); `test_raw_replay_ends_unavailable`; `test_a_box_out_of_range_is_
  skipped` (1e308, -0.5, 1.5 in each box place: skipped, the good lines kept); `test_a_keypoint_far_out_of_range_is_
  skipped` (1e308, -1.5, 2.5 in x and y, conf 1.5; -0.2 and 1.2 pass); `test_a_float_over_max_abs_is_skipped`;
  `test_a_raw_detection_out_of_range_is_skipped`; `test_header_inputs_round_trip_and_set_replay_provides`;
  `test_a_header_without_inputs_provides_every_camera_input`.
## S: `stats` (sonnet, worktree, batch 2; cut first)
- `arcade/stats.py`: `GameStats(sessions: int, median_seconds: float | None, reasons: dict[str, int])` (frozen);
  `summarise(path: Path) -> tuple[dict[str, GameStats], int]` (per game; the int counts bad lines, skipped);
  `table(stats) -> str` (one line a game, `MENU_ORDER` first, then the rest sorted); `main(args) -> int` reads
  `args.sessions` or `cfg.data_dir / "sessions.jsonl"`, prints the table (or "no sessions"), returns 0.
- Acceptance (`tests/arcade/test_stats.py`): `test_stats_summarises_sessions` (jump 10, 20, 40 s with reasons left,
  done, done (`scores.REASONS`); one pong: jump 3 sessions, median 20, `{"done": 2, "left": 1}`);
  `test_stats_skips_a_bad_line`; `test_stats_without_a_file_says_so`; `test_a_null_duration_is_not_in_the_median`.
## I1: integration (the orchestrator, after RP and S)
- `arcade/sources/__init__.py`: exports `open_replay`, `ScenarioReader`, `ScenarioWriter`, `make_header` (never
  `blobs`); `make_sources(cfg, size, clock, script=None, *, calibration=None, replay: str | Path | None = None)`:
  `replay` (or `cfg.camera == "replay"` with `cfg.scenario`; ValueError when `scenario` is empty) gives
  `open_replay(path, calibration or load_calibration(cfg.data_dir), clock)` as both camera and audio.
- `arcade/sources/scripted.py`: `ScriptedCamera(frames, clock, provides=CAMERA_INPUTS)`; `SCRIPT_INPUTS = {"walkup":
  frozenset({"pose"})}`, passed by `make_sources` (walkup holds no light: it offers no blob game).
- `arcade/main.py` glue: `COMMANDS = ("run", "doctor", "calibrate", "record", "stats")`; `run --replay PATH`
  (mutually exclusive with `--script`, passed to `make_sources`); `run --require LIST` (default none: runs
  `doctor(require, probes, TIMEOUT)` first and returns 1 when it fails; Q145); subparsers `calibrate --config`,
  `record --config --script {RECORD_SCRIPTS} --i-have-consent --raw --with-motion --out`, `stats --config
  --sessions`; dispatch `if args.command == "record": from arcade.sources.record import main as record_main; return
  record_main(args)`, the same for `calibrate` (`arcade.calibrate`) and `stats` (`arcade.stats`); logging as `run`'s.
- `arcade/sources/README.md`: four lines: `provides`, the wiring, raw replay, record and calibrate.
- Acceptance: `test_main.py`: `test_main_dispatches_the_new_commands` (each module's `main` spied: called once with
  the parsed flags); `test_run_replay_plays_a_scenario_file` (an actors file written with `ScenarioWriter`; `run
  --replay --seconds 0.2` exits 0 and loops a `ReplayCamera`); `test_run_require_exits_nonzero_without_camera`
  (failing probes: 1, the runner never built). `test_sources.py`: `test_make_sources_replay_from_the_flag_and_the_
  config`, `test_walkup_provides_pose_only`. Unchanged and passing: `test_make_sources_none_and_scripted`,
  `test_main_builds_runner_with_the_small_lobby_and_games_once`, `test_run_opens_a_128x64_wall_by_default`,
  `test_doctor.py::test_importing_main_loads_no_hardware_module`.
- The full suite once with `--durations=25`: passes, 3 skips, at most 540 s (expected about 470 s).
## Decisions taken
- Two batches (at most four at once), the cut-first tasks in batch 2; the subset after each merge and one full run
  depart from config.md rule 6, for time (it20). Cut order: S, then RP's raw replay (keep the range check), then
  record's `--raw` (W's `tap`, R's raw path and tests; `--raw` then always refused). Core: E1, G6, W, R (sensed), C.
## I2 (the operator's, in verify)
- `tools/arcade_evidence.py --iteration 21 --games jump`: `games.md` every budget "yes", no override. Sheets read
  again: Jump's "GET SET", "JUMP!", the hint, the bell with "DING!", `over`'s word, at zone x 0.15, 0.5, 0.85.
- Record: `python -m tools.arcade_shot jump --lobby tests.arcade.test_record:sheet_scene --scenario
  tests.arcade.test_record:sheet_frames --out docs/superpowers/workflow/evidence/it21/record --look both` (3, 2, 1,
  REC, the counter, a cue). Calibrate: the same with `tests.arcade.test_calibrate` (`.../it21/calibrate`): each
  step's words, the dots, the zone. Images stay local (Q98).
- The owner's (never the loop's): `calibrate`, `run` on the webcam with a phone torch, `record`, `run --replay`.
