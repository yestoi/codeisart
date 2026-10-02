# it21 orchestrator report: C56 (Jump's layout), M5's second lane (the wiring with C35, raw replay, record, calibrate, stats)

Plan: `docs/superpowers/plans/2026-10-02-it21-m5-wiring-record-calibrate.md`. Main was at fd7de35 with a clean tree at
06:55:32 (state.md aside: it showed as modified later in the run; it is the operator's, never staged). BASE for batch 1
(after E1) is 90c3397; BASE2 for batch 2 (after the G6, W, R and C merges) is 4c23259. The task reports are
`E1-report.md`, `G6-report.md`, `W-report.md`, `R-report.md`, `C-report.md`, `RP-report.md` and `S-report.md` in this
folder; the final run's output is `final-durations.txt`.

## Completed

- **E1** (opus, main checkout, serial; a0dabbc, report 90c3397). `CAMERA_INPUTS`/`AUDIO_INPUTS` now live in
  `arcade/sensed.py` (the runner imports them: `arcade.runner.CAMERA_INPUTS is arcade.sensed.CAMERA_INPUTS`). A camera
  may declare `provides`; `Runner._source` reads it in the same `try` as `latest()` (a raising or malformed one fails
  the camera, logged once); `sense()` claims `provides & CAMERA_INPUTS` and drops bodies, blobs or the grid a camera
  does not provide. `loop(..., until=None)` stops after the first tick on which `until()` is True. `Blob.vy`'s comment
  says frame heights per second (Q131). 4 new tests, failing first; `test_runner.py:694`, `:697`, `:711` unchanged.
  I read the diff and checked it against the plan before batch 1.
- **G6** (sonnet, worktree; c9a80f5). C56: `FIGURE_H` 56 to 50; the prompt band rows 50 to 59, columns 18 to 127, 1x,
  centred, over a black box; "GET SET" in `ready`, "JUMP!" or the hint "RING THE BELL!" (never both, no 2x "JUMP!")
  in `play`, "BELL RUNG!"/"NICE TRY!" in `over`; the pop and `result` unchanged. The one named assert changed
  (`test_jump.py:130`, 56 to 50); 4 new tests. Jump's oracle: all 17 metrics pass over 20 seeds (score_visible 0.978,
  score_legible 1.0, flash_area_raw 0.0037, square_flashes 4).
- **W** (opus, worktree; a5e98c8, report a629ccc). `FrameFeatures` shrinks a frame wider than 160 to `WORK_SIZE`
  (160x120, INTER_AREA), takes `mirror` (and `motion_grid(..., mirror=)`), drops a blob within a
  `calibration.static_mask` light before tracking, and has the `hide_still` attribute. `MediaPipeCamera`: `provides =
  CAMERA_INPUTS`, `features` on the wall's grid with the source's calibration and `cfg.mirror`, `step` returns blobs
  and motion, and the `tap` gets one `RawRecord` per due capture (grey 160x120 unflipped, detections mirrored). The
  named assert (`test_pose_mediapipe.py:149`) and the named setup (`test_blobs.py:89`) changed, nothing else; 9 new
  tests. Perf: `FrameFeatures.update` at 640x480 input 0.444 ms mean (3.71 ms before the shrink).
- **R** (opus, worktree; 79ae0e0, report 17e125e). `arcade/sources/record.py`: spec 9.5's twelve `RECORD_SCRIPTS`
  with cues, `refusal`, `RecordScene` as the runner's lobby (3 2 1 at 2x, red "REC" at (1, 1), the seconds, the cue
  at rows 28 to 35, figures under the texts, rows 60 to 63 black), `record()` with a strict runner on the given clock
  and the tap set on rec's first tick and cleared on its last and in the `finally` (camera closed before the
  writer), `main`. `tests/arcade/test_privacy.py` (spec 6.5's rule over every `arcade/**/*.py`, plus 22 snippet
  cases). 18 + 23 tests; the implementer mutated the code 8 times and each mutation was caught.
- **C** (opus, worktree; b3b08c1). `arcade/calibrate.py`: the `Calibrator` lobby (aim, three stands, baseline, clear,
  saved / failed), the zone never thinner in y than the default's, `min_height`, the static lights seen in 80 % of the
  clear's captures, the file written only on success after a load-back check; `main` turns `hide_still` off through
  `getattr`, runs a strict runner until `done`, returns 0 or 1. 9 tests (one beyond the plan's list).
- **RP** (opus, worktree; 2f374f5 range check and header, d7bf392 raw replay, report b1b4d62). The reader skips a
  record with a box outside [0, 1], a keypoint x or y outside [-1, 2], a conf outside [0, 1] or another float over
  `MAX_ABS` (1e3); `make_header(..., inputs=)`, `check_header` accepts `inputs` and `mirror`; `ScenarioReader.inputs`;
  `ReplayCamera.provides`; `open_replay` on a raw file gives `(RawReplayCamera, NoAudio)` (FrameFeatures and
  BodyTracker again, paced by capture time with the 1e-9 slack, pose and motion only). The named test
  (`test_raw_file_is_not_replayed_yet`) removed; 9 new tests. Nothing was cut.
- **S** (sonnet, worktree; ffa6774). `arcade/stats.py`: `GameStats`, `summarise`, `table`, `main` (read only).
  4 tests. Nothing was cut.
- **I1** (mine, main checkout, test-first; 4895b1f). The five new tests were written first and failed (an
  ImportError on `ScenarioWriter` from `arcade.sources`; three `SystemExit: 2` from the parser), then passed.
  - `arcade/sources/__init__.py`: exports `open_replay`, `ScenarioReader`, `ScenarioWriter`, `make_header` (never
    `blobs`); `make_sources(..., replay=None)`: a replay path, or `cfg.camera == "replay"` with `cfg.scenario` (no
    script given; ValueError when `scenario` is empty), gives `open_replay(path, calibration or
    load_calibration(cfg.data_dir), clock)` as the camera and the audio; a script and a replay together raise.
  - `arcade/sources/scripted.py`: `ScriptedCamera(frames, clock, provides=None)` with a class attribute `provides =
    CAMERA_INPUTS` (see deviation 1); `SCRIPT_INPUTS = {"walkup": frozenset({"pose"})}`, passed by `make_sources`.
  - `arcade/main.py`: `COMMANDS` gains calibrate, record, stats; `run --replay PATH` (a mutually exclusive group with
    `--script`) and `run --require LIST` (default none; the doctor runs on those probes before any source opens and
    `run` returns its code when it fails); the `calibrate`, `record` and `stats` subparsers; each new command imports
    its module's `main` only when it runs, with `run`'s logging setup; `make_probes()` shared by `doctor` and `run
    --require`.
  - `arcade/sources/README.md`: four lines (provides, the wiring, raw replay, record and calibrate).
  - Tests: `test_main_dispatches_the_new_commands`, `test_run_replay_plays_a_scenario_file`,
    `test_run_require_exits_nonzero_without_camera` (`test_main.py`); `test_make_sources_replay_from_the_flag_and_the_
    config`, `test_walkup_provides_pose_only` (`test_sources.py`). The four named unchanged tests pass unchanged.
  - Smoke from the main checkout: `python -m arcade record --help` lists the twelve scripts; `python -m arcade stats
    --sessions <missing file>` prints "no sessions", exit 0; `python -m arcade record --script door-point` without
    consent prints the refusal, exit 2 (nothing opened).
- No merge was reverted, no task was sent back, nothing was cut. The worktrees and branches are kept. Nothing was
  pushed or deployed; nothing went to the Pi or the card; nothing was fetched; no image was committed.

### Each merge's subset

Command, from `/Users/trey/dev/codeisart`: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
/Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs --durations=10 <files>`, `test_all_games.py` named first.

| After | Files (after `test_all_games.py`) | Passed | Failed | Time | Pool (plays, elapsed, join wait) |
|---|---|---|---|---|---|
| G6 merge (7c80539) | test_jump, test_oracle, test_game | 203 | 0 | 172.82 s | 480, 121.9 s, 13.4 s |
| W merge (f133085) | test_blobs, test_pose_mediapipe, test_oracle, test_game, test_doctor | 196 | 0 | 165.84 s | 480, 125.8 s, 13.6 s |
| R merge (6085d01) | test_record, test_privacy, test_oracle, test_game, test_doctor | 190 | 0 | 172.14 s | 480, 132.9 s, 15.0 s |
| C merge (4c23259) | test_calibrate, test_calibration, test_privacy, test_oracle, test_game, test_doctor | 204 | 0 | 170.00 s | 480, 128.9 s, 10.9 s |
| RP merge (f7bd5da) | test_scenario, test_record, test_oracle, test_game, test_doctor | 224 | 0 | 160.56 s | 480, 118.9 s, 13.2 s |
| S merge (f9ea1e7) | test_stats, test_oracle, test_game | 143 | 0 | 189.64 s | (as the others) |

No skip in any subset (the main checkout has `models/`). No timing test failed. `test_doctor.py` was added to the
subsets of the merges that touch imports (cheap; it guards `import arcade.main` against cv2).

### The full run (once, after I1)

At 4895b1f, from `/Users/trey/dev/codeisart`, 07:50:57 to 07:58:32 (load average 8.45 at the start, 3.74 at the end):
`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs
--durations=25` -> **2323 passed, 3 skipped, 0 failed in 454.57 s** (2326 collected); `pooled: 480 plays, 4 workers,
135.6 s, the join waited 11.0 s`. The whole output is `final-durations.txt`.

- Collected 2326 against the baseline's 2236: +90, counted per file with `--collect-only` against an archive of fd7de35
  (E1 4 in `test_runner.py`; G6 10, its 4 new tests with their parameters; W 9 (5 in `test_blobs.py`, 4 in
  `test_pose_mediapipe.py`); R 41 (18 in `test_record.py`, 23 in `test_privacy.py`); C 9; RP 8 (9 new, 1 removed as
  the plan names); S 4; I1 5 (3 in `test_main.py`, 2 in `test_sources.py`)).
- Skips: the base's 3, all Linux-only (`test_colorlight_child.py:142`, `test_colorlight_slot.py:105`,
  `test_sandbox.py:153`). No rise.
- Time: 454.57 s, under the 540 s cap and under the baseline's 457.24 s (the load differs between runs; C's report puts
  its tests at about 2.6 s, the largest of the new files). No timing test failed; nothing rerun.
- After the full run I committed one import-order change (d2f1b63, `arcade/sources/__init__.py`, stdlib imports in
  one block, no code change) and reran the import-sensitive files (`test_sources`, `test_main`, `test_doctor`,
  `test_record`, `test_calibrate`, `test_scenario`, `test_privacy`): 131 passed in 6.75 s.

The `--durations=25` table:

```
11.00s setup    tests/arcade/test_all_games.py::test_every_game_fits_the_tick_budget[copyme-128x64]
10.27s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[freeze-128x64]
9.98s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[pong-128x64]
9.29s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[pong-96x48]
8.57s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[jump-128x64]
8.36s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[copyme-128x64]
7.85s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[quickdraw-128x64]
7.77s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[copyme-96x48]
7.46s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[swat-128x64]
6.69s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[flap-128x64]
6.55s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[quickdraw-96x48]
6.46s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[jump-96x48]
6.31s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[freeze-96x48]
6.23s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[dodge-128x64]
6.07s call     tests/test_show_shot_governed.py::test_governed_entry_session_runs_the_entry_through_the_governor
5.23s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[flap-96x48]
5.13s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[dodge-96x48]
5.00s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[swat-96x48]
4.55s call     tests/test_show_shot.py::test_entry_mode_plays_the_sample_entry_through_the_pipeline
3.72s call     tests/test_curated_entries.py::test_entry_plays_through[sloane]
3.64s call     tests/arcade/test_first_playable.py::test_first_playable_keeps_the_flash_rule
3.61s call     tests/test_show_shot.py::test_strobe_session_is_held
3.58s call     tests/test_entries.py::test_sample_entry_band_leaves_no_trail
3.55s call     tests/test_curated_entries.py::test_entry_plays_through[endoh1]
3.50s call     tests/test_curated_entries.py::test_entry_plays_through[imc]
pooled: 480 plays, 4 workers, 135.6 s, the join waited 11.0 s
2323 passed, 3 skipped in 454.57s (0:07:34)
```

No new test of this iteration is in the slowest 25.

## Test status (command + counts)

- Command, from `/Users/trey/dev/codeisart`: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
  /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs --durations=25`.
- Full run at 4895b1f: 2326 collected, 2323 passed, 3 skipped (the base's three, Linux-only), 0 failed, 454.57 s
  (cap 540 s; baseline 2236 collected, 457.24 s).
- Six merge subsets (table above): 203, 196, 190, 204, 224 and 143 passed, 0 failed, 0 skipped.
- After d2f1b63 (import order only): the seven import-sensitive files, 131 passed.

## Deviations

### Mine

1. **`ScriptedCamera`'s `provides` default.** The plan writes `ScriptedCamera(frames, clock, provides=CAMERA_INPUTS)`.
   Built that way (an instance attribute set from the default), it shadowed a subclass's class attribute: R's
   `test_record_drops_motion_by_default` (`test_record.py:369`) builds `PoseAndMotion(ClosingCamera)` with
   `provides = frozenset({"pose", "motion"})` as a class attribute, and its header's `inputs` came out as all three.
   That assert is not one the plan names, so I changed my code, not the test: `provides` is a class attribute
   (`CAMERA_INPUTS`) and the keyword defaults to None, setting the instance's only when given. Same behaviour for every
   caller the plan names (the default claims every camera input; walkup claims pose).
2. **`run --require` returns the doctor's code**, not always 1: 1 when a probe fails (as the plan and its test say),
   2 when `--require` names an unknown source (the doctor's usage code). The probes use `cfg.camera_index` and
   `cfg.audio_device` (the run's own camera and microphone) and `MODEL_PATH`. The doctor runs after `load_config` and
   the "wall ..." INFO line, before the calibration, the sources and the display.
3. **`record --script` is required** (argparse `choices` from `RECORD_SCRIPTS`, imported inside `build_parser`). The
   plan lists the flag without saying; record's `main` refuses a missing name anyway.
4. **The doctor no longer calls `logging.basicConfig`; every other command does** (as `run` did), `-v` only on `run`
   (the plan names no `-v` for the new subparsers).
5. **`test_doctor.py` added to five merge subsets**, beyond the plan's subset (it is 1 s and guards the cv2 rule).
6. **One edit made with a Python one-off instead of the Edit tool** (the first `scripted.py` change); the file was
   then read back and edited with the Edit tool. No other file was written that way.
7. **The S subset ran while I wrote I1's code in the same checkout.** The subset collects and starts its pool in its
   first seconds; my edits came after that, in an order that kept every intermediate state importable. It passed
   (143). The full run after I1 covers it in any case.

### Flagged for the loop's review (not changed by me)

8. **C imports a private name**: `arcade.calibrate` imports `arcade.calibration._from_json` to check the file before
   writing it (C's deviation 4), so a saved file always loads back. `calibration.py` was not C's file.
9. **C draws blobs as dots** (`LIGHT`, magenta) in the view, beyond the plan's keypoints and zone, and shows "NOT
   SAVED" (not "NO ONE CAME") when the zone would not load or the write fails. Static drawing; its flash test covers it.
10. **W's perf disagrees with the plan review's figure**: the shrink alone measured 0.017 ms, not 0.39 ms. The perf
    test (under 3 ms, mean 0.444 ms) holds either way.
11. **R's raw file covers (start, start + seconds]**, within one capture of the cues' base (the tap is set after that
    tick's `latest()`), as the review's round 2 read it.
12. **R's record ends on a frame with the figures only** (no REC, no cue) on the tick rec reaches `script.seconds`.

### The implementers' (details in their reports)

- **E1**: `s.motion` without "motion" is the all-False wall grid (the existing `None` to empty to `with_motion`
  path), not `None`; names in `provides` outside `CAMERA_INPUTS` are cut, not a failure; `provides` is read only for
  the camera; `loop` breaks before the period's sleep, and a raising `until()` leaves `loop`.
- **G6**: none. Its red step was the ImportError for the new constants; the four behavioural tests were not watched
  failing one by one.
- **W**: `FrameFeatures._prev` became the public `gray` (the tap reads it); new helpers `blobs.shrink` and
  `pose_mediapipe.raw_frame` (a frame of 160 px or narrower is resized to `FRAME_SHAPE` for the tap); `FrameFeatures`
  is imported inside `MediaPipeCamera.__init__`; `hide_still` False stops `StaticMask`'s clock; a blob exactly on a
  static light's radius is dropped.
- **R**: extra constants (`REC_XY`, `CUE_Y`, `MARKER_ROWS`, `MAX_CUE`); `main` loads the font first and treats an
  unknown script as a refusal (2); the privacy rule also catches `savez_compressed` and `from cv2 import imwrite`;
  every body is drawn, in zone or not; `RecordScene.__init__` resets at 128x64 so `debug_state()` works early.
- **C**: blobs drawn as dots; "NOT SAVED" for a failure that is not a timeout; `test_nobody_comes_writes_no_file`
  runs 62.5 s (61 s does not reach `done()`); `_from_json` imported; one extra test
  (`test_dots_and_the_zone_are_drawn_in_the_view`).
- **RP**: a fourth constant `CONF_RANGE`; `available` turns False one call after the last capture (as it20's D2);
  a header's `inputs` or `mirror` present as null is refused; bounds inclusive.
- **S**: none.

### Owner questions raised by the implementers (each defaulted; verbatim)

- **E1**:
  - Q-E1a: `getattr(camera, "provides", CAMERA_INPUTS)` (the plan review's instruction) treats a `provides` property
    that raises `AttributeError` as absent, so that camera claims every input instead of failing. Any other exception
    fails the camera (tested with `OSError`). Acceptable, or should an `AttributeError` raised inside a property also
    fail the camera (it would need `inspect.getattr_static` to tell "absent" from "raised")?
- **G6**: none.
- **W**:
  - **Q-W1, the smallest light after the shrink.** Blobs are now found at 160x120 on the Mac too. A core needs
    `MIN_AREA` = 4 px there, which is about 64 px at 640x480: a light core 9 px across at 640x480 is no longer seen.
    S1's Q1 (refit `MIN_AREA` at 160x120 with GATE A's recorded lights) now covers the Mac's camera as well.
    Default: keep 4.
  - **Q-W2, a camera that is not 4:3.** A camera that ignores `CAPTURE_SIZE` and gives 1280x720 is shrunk to
    160x120, as the plan says. Positions stay right in frame units. But the frame-width distances (`MATCH_DIST`,
    `STATIC_MOVE`, the static mask's radius) then use a 4:3 aspect instead of 16:9, so y distances count 1.33 times
    too much, and a raw record's frame is squashed the same way. Default: the plan's reading (the Mac's camera
    gives 640x480).
- **R**:
  - Q-Ra: once the M5 audio source exists, should a sensed file's `inputs` also list `"audio"` while the microphone is
    available? Today it is the camera's names only, as the plan says, and no game reads audio (Q99).
  - Q-Rb: the cue texts (Q142 leaves them to you) are in `RECORD_SCRIPTS`. Change any wording you want; each must
    stay 21 characters or fewer, and the tests check that.
  - Q-Rc: ^C during a recording keeps the partial file (closed properly) and exits with the traceback. Should `main`
    catch it, print the path and return 1 instead?
  - Q-Rd: the end tick (the last frame) shows the figures only. Would you like a short "SAVED" card instead?
- **C**:
  1. A stand is not required to be away from the stands before it. If the operator is still standing at the far left
     2 s after "STAND FAR RIGHT" shows, far_right records the same place and the zone is too narrow, silently (the
     outline on the wall shows it). A guard (a stand at least, say, 0.1 fw from every earlier stand) is about four
     lines; not built, as the plan does not name it.
  2. A body that drops out for one capture (no body in a tick) restarts a stand's window. With a real tracker this is
     rare while a person stands still, so no grace was added.
  3. The camera frame's edge is not drawn (only the zone so far): while aiming, the wall shows dots on black with no
     frame line round `VIEW`. A 1 px outline of `VIEW` would show where the camera's frame ends; not built.
- **RP**:
  - Q-RP1: a blob's `color` is ints (`int(c)`), so a color of 1e308 still decodes to a huge int; the plan's range is
    for floats only. A game that puts a blob's colour into a uint8 frame would raise on it. Range-check `color` to
    0..255 in a later slice? (Not done: not in the plan.)
  - Q-RP2: a record's `t` far in the future (finite, e.g. 1e300) in a raw file is never due: the replay then holds its
    last capture, available, until it goes stale in the runner. Acceptable (finite-only was the plan's rule for t).
- **S**: none.
- **Mine (I1)**: Q-I1a: should `run --require` also watch the live sources for a few seconds after they open (the
  plan's Q145 says no: the doctor's probes only)? Default: probes only, as planned.

## Commits (sha + subject)

| sha | subject |
|---|---|
| a0dabbc | feat(arcade): it21 E1, per-input availability (C35), a loop that stops on until, the vy unit |
| 90c3397 | docs(workflow): it21 E1, the implementer's report (BASE) |
| c9a80f5 | feat(arcade): it21 G6, Jump's words in a prompt band clear of the figure (C56) |
| a5e98c8 | feat(arcade): it21 W, blobs and motion from the MediaPipe camera, the raw tap |
| a629ccc | docs(workflow): it21 W, the implementer's report |
| 79ae0e0 | feat(arcade): it21 R, record with consent: 3 2 1, REC, cues, raw tap on rec only; the privacy rule |
| 17e125e | docs(workflow): it21 R, the implementer's report |
| b3b08c1 | feat(arcade): it21 C, calibrate: the Calibrator lobby (spec 6.6) and its main |
| 7c80539 | merge: it21 G6, Jump's words in a prompt band clear of the figure (C56) |
| f133085 | merge: it21 W, blobs and motion from the MediaPipe camera, the raw tap (M5's wiring) |
| 6085d01 | merge: it21 R, record with consent (REC, cues, the raw tap on rec only) and the privacy rule |
| 4c23259 | merge: it21 C, calibrate: the Calibrator lobby (spec 6.6) and its main (BASE2) |
| ffa6774 | feat(arcade): it21 S, stats: a read-only summary of the sessions log |
| 2f374f5 | feat(arcade): it21 RP, the reader's range check and the header's inputs |
| d7bf392 | feat(arcade): it21 RP, raw replay through FrameFeatures and BodyTracker |
| b1b4d62 | docs(workflow): it21 RP, the implementer's report |
| f7bd5da | merge: it21 RP, raw replay and the reader's range check (M5) |
| f9ea1e7 | merge: it21 S, stats: a read-only summary of the sessions log |
| 4895b1f | feat(arcade): it21 I1, the glue: calibrate, record and stats commands, run --replay and --require, provides for scripts |
| d2f1b63 | style(arcade): it21 I1, arcade.sources' stdlib imports in one block |
| (this file) | docs(workflow): it21, the orchestrator's report and the final run's durations |

The G6 and S reports ride in their feature commits (c9a80f5, ffa6774), the C report in b3b08c1. The branches are
kept, as are their worktrees under `.claude/worktrees/`:

| Task | Branch | Worktree |
|---|---|---|
| G6 | `worktree-agent-a54904f503cc92790` | `agent-a54904f503cc92790` |
| W | `worktree-agent-aa733f494812f7d90` | `agent-aa733f494812f7d90` |
| R | `worktree-agent-a47649598ce80c7b1` | `agent-a47649598ce80c7b1` |
| C | `worktree-agent-ad3dc68e4cc19d5c8` | `agent-ad3dc68e4cc19d5c8` |
| RP | `worktree-agent-a02d14efeb9c96e2b` | `agent-a02d14efeb9c96e2b` |
| S | `worktree-agent-ad6c0ea2b50435287` | `agent-ad6c0ea2b50435287` |

## Minutes (serial lane, parallel tasks, integration)

Times from `date` and the commits' clock.

- **Serial lane:** about 7 min, from 06:55:32 (reading the plan) to the BASE at 07:02:07. E1 (opus) ran 6.4 min
  (06:55:58 to 07:02:21).
- **Parallel tasks:** about 27.5 min of wall time.
  - Batch 1, spawned at about 07:03, back at 07:21:26 (18.5 min, bound by R): G6 2.3 min (sonnet), W 12.1 min,
    R 16.3 min, C 15.6 min (opus).
  - Batch 2, spawned at about 07:35, back at 07:44:16 (9 min, bound by RP): RP 8.9 min (opus), S 0.9 min (sonnet).
- **Integration:** about 31 min. Batch 1's four merges and subsets 07:21:26 to 07:34:33 (13 min); RP's merge and
  subset 07:44:16 to 07:47:06 (3 min); S's merge and subset 07:47:27 to 07:50:43, with I1 written beside it (I1
  committed 07:50:52); the full run 07:50:57 to 07:58:32 (7.6 min); the import-order commit and this report to about
  08:04.
- **In all:** about 68 min against the plan's target of about 100 min for the implement phase.
