# Iteration 21: the plan writer's report

Plan: `docs/superpowers/plans/2026-10-02-it21-m5-wiring-record-calibrate.md` (299 lines, none over 118 characters).
Written at HEAD 3a3fe02. No code written, nothing committed, no full suite run.

## What I read
- The it20 plan (form), `workflow/config.md` loop rules 1, 2, 5, 6 and 10, the roadmap's M5 line, Carried (C56, C35,
  C34, C21, C11/C17) and the four it20 notes the brief names.
- Spec 4.1, 4.3, 5, 6.1 to 6.6, 9.5, 10; the core plan's amendments for Tasks 12, 15, 16, 18 and 20 (lines 580 to
  720) and Task 18's draft `record` (lines 5245 to 5270).
- it20's S1 and S2 reports (open items), and the code the plan changes: `arcade/runner.py` (`sense` 577-608,
  `_source` 566, `available` 334, `loop` 610, `CAMERA_INPUTS` 54), `arcade/sensed.py` (`Blob` 270-287, `place`
  311), `arcade/sources/camera.py`, `pose_mediapipe.py`, `blobs.py`, `scenario.py`, `replay.py`, `scripted.py`,
  `actors.body_box`, `sources/__init__.py`, `arcade/calibration.py`, `arcade/main.py`, `arcade/config.py`,
  `arcade/scores.SessionLog`, `arcade/games/jump.py` (layout and draw), `arcade/figure.py` (`to_wall`,
  `figure_rect`), `arcade/headless.py` (`run_headless`, `RecordingDisplay`), `tools/arcade_shot.py` (`--lobby`,
  `--scenario` take `module:attr`), `tools/make_cues.py`.
- Tests the plan cites or must not break: `test_runner.py` (657-711), `test_pose_mediapipe.py` (42-149),
  `test_scenario.py` (115, 212-218, 288-297), `test_main.py`, `test_sources.py`, `test_doctor.py:46`,
  `test_jump.py` (118-130, 405-415, 490-540), `test_blobs.py`, `test_calibration.py`. Every test name the plan says
  exists was grepped: `test_sense_survives_raising_source_and_reports_status`, `test_latest_has_no_blobs_and_no_
  motion`, `test_raw_file_is_not_replayed_yet`, `test_gz_round_trip_with_header`, `test_registered_and_declared`,
  `test_importing_main_loads_no_hardware_module`, `test_run_opens_a_128x64_wall_by_default`,
  `test_make_sources_none_and_scripted`, `test_main_builds_runner_with_the_small_lobby_and_games_once`,
  `test_tick_budget_with_the_governors_share`, `test_strobe_session_is_held`, `test_protocol_members_are_the_frozen_
  set` (carried from it20's plan), `test_loop_runs_max_ticks_with_fake_clock`.

## What I measured (by reading; no suite run)
- Jump at 128x64: the figure's rect is a `FIGURE_H` square (56) centred on `round(zone_x * 127)`: x 36 to 91 at
  zone 0.5, -9 to 46 at 0.15, 80 to 135 at 0.85. The striker is columns 6 to 15, rows 6 to 57. The score's box is
  rows 0 to 17 at the right. The 5x7 font's cell is 6x8: "GET SET" is 41 px at 1x, "JUMP!" 29 px at 1x and 58 at
  2x. At zone 0.5 the free columns beside the rect are 17 to 35 (19) and 92 to 127 (36): "GET SET" fits in neither.
  The bell's rows are 24 (40 cm) to 34 (28 cm), so the "DING!" pop sits at rows about 20 to 38.
- `FrameFeatures.update` always mirrors blob x and `motion_grid` always flips: wrong when `cfg.mirror` is false.
- `calibration.static_mask` is never applied (S1's item 3).
- The fake capture in `test_pose_mediapipe.py` gives a 48x64 blue frame at value 200, under `LIGHT_V`: no blob, and
  the first frame has no motion, so the changed assert at :149 stays strict.
- `test_scenario.py:115` pins the whole header dict: the new `inputs` key must be absent unless given.
- `make_header` and `check_header` accept extra keys today, so record can write `inputs` before RP lands.
- `test_main.py::test_run_opens_a_128x64_wall_by_default` pins `run`'s INFO lines: no new INFO line in `run`.
- `arcade/` holds no `imwrite`, `imencode`, `VideoWriter`, `savez`, `.save` or `import wave`; `freeze.py:504`
  defines a function `wave`, so a name-level ban on `wave` would fail on today's code.
- Suite shares are estimates from the sizes of the new tests (headless ticks at about 1 ms; the calibrate scene is
  about 60 s of actor ticks): about +13 s on 457.24 s.

## Decisions, with reasons
1. **C56 layout: a bottom band under a 50-row figure.** I checked words beside the figure, the brief's first idea:
   they cannot fit at zone 0.5. At the top they would hit the score and the striker. A band at rows 50 to 59 and
   columns 18 to 127 never meets the figure's rect (rows 0 to 49) at any `zone_x`, so the tests check fixed numbers.
   The cost is a figure 6 rows shorter (`FIGURE_H` 56 to 50). That is the only changed assert in Jump's file
   (`test_jump.py:130`). Fidelity reads `player_xy` on axis 0, and the column mapping does not change.
2. **The hint replaces the prompt** ("RING THE BELL!" names the goal; "JUMP!" never shows twice). `over` says
   "BELL RUNG!" or "NICE TRY!". `result` keeps its 2x number, as Q127 left it.
3. **C35 by `provides`**, defaulting to today's three camera inputs. So `test_runner.py:697` does not change: its
   fake has no `provides`. The brief expected that assert to change. Under the default the brief itself suggests,
   it does not, and the plan says so. The runner also blanks what a camera does not provide, so a game never gets
   blobs that the lobby was not told about. `Runner.available()` is the list of games that are not hidden. The
   lobby already filters by `needs <= inputs` (`lobby.py:145`), so `available()` does not change.
   `CAMERA_INPUTS` moves to `sensed.py`, so replay can import it without importing the runner.
4. **REC and calibrate are lobby scenes.** The runner's lobby slot draws on the canvas before the limiter and the
   governor, so there is no path around them and no change to the runner's order. The runner only gains
   `loop(until=)` so both can stop when their scene is done. That is the serial lane's work (E1).
5. **The wiring's seam is `FrameFeatures.update`.** It is already pure. It gains the shrink to 160x120, `mirror`
   and the static mask. `MediaPipeCamera` only constructs it and calls it on frames it runs the model on.
6. **Raw recording via a `tap` on the camera, called on the source thread.** Spec 6.5 says no frame leaves its source
   thread, and `encode_raw` uses base64 and `struct`, so no privacy exemption is needed.
7. **The range check**: box in [0, 1] (both sources clamp it), keypoints in [-1, 2] (raw detections are the model's
   landmarks before `Body` clamps them), conf in [0, 1], every other float at most 1e3 in size, times finite only.
8. **`test_privacy.py` is built here** (spec 6.5; core Task 20 planned it and it was never built). Its `wave` rule is
   on imports.
9. **Lanes**: E1 serial, then two parallel batches, with the cut-first tasks (stats, raw replay) in batch 2. Then
   the orchestrator's glue and one full run.
10. **Record scripts are new**: spec 9.5's twelve, with cue lists written from its descriptions. They go in
    `record.py` as `RECORD_SCRIPTS`.

## Owner questions (each defaulted; none blocks)
- **Q136** Jump's prompt in a 1x band at rows 50 to 59 under a figure shortened from 56 to 50 rows, instead of the
  big 2x "JUMP!" across the middle. Default: as planned.
- **Q137** Jump's words: the hint "RING THE BELL!" replaces "JUMP!" after 2 s idle; `over` says "BELL RUNG!" or
  "NICE TRY!". Default: as planned.
- **Q138** A camera source without `provides` claims pose, blobs and motion (today's behaviour). The walkup script
  claims pose only, so it offers no blob game. Default: as planned.
- **Q139** The reader's bounds: box [0, 1], keypoint x and y [-1, 2], conf [0, 1], other floats |v| <= 1e3.
  Default: as planned.
- **Q140** Raw recordings hold a grey 160x120 frame (spec 6.3), so raw replay gives pose and motion but never blobs.
  Re-tuning the lamp rule (C34) on raw files would need colour frames: 3x the size, and a privacy call. Default:
  grey; C34 is refitted on sensed recordings of `torch-paint` and `empty-room`.
- **Q141** The REC screen shows the bodies' figures under the cue, so the performer sees what is recorded. Default:
  yes.
- **Q142** The loop writes the twelve recording scripts' cue lists from spec 9.5's descriptions. Default: the owner
  reads them at GATE A, before recording.
- **Q143** Calibrate's flow: aim ends on both hands up for 2 s; each stand ends after 2 s still; every step times out
  at 60 s; a timeout writes no file and exits 1. Default: as planned.
- **Q144** Calibrate's zone is the three stands' shoulder anchors, min to max, widened by 0.05. `min_height` is 0.8 of
  the smallest stand height. Default: as planned.
- **Q145** `run --require LIST` runs the doctor's probes before the run and exits 1 when one fails. It does not watch
  the live sources for 5 s. Default: as planned.
- **Q146** `record --raw` records the pose source's grey frames and detections only, with no sound (no audio source,
  Q99). Default: as planned.
- **Q147** Recordings go to `data_dir/recordings/<script>-<UTC stamp>.jsonl.gz` by default (`data/` is not in git);
  `--out` overrides. Default: as planned.

## What I found wrong in the brief
1. `tests/arcade/test_privacy.py` does not exist. Core Task 20 planned it and it was never built. The plan builds it
   in R, with the `wave` rule on imports (`freeze.py:504` defines `wave()`).
2. `tools/make_cues.py` generates the show's four sound cues, and it uses `wave`, in `tools/`. It has nothing to do
   with recording, and no recording scripts exist anywhere. Record's `RECORD_SCRIPTS` are new in this slice.
3. Under the default the brief suggests (today's behaviour for a source without `provides`),
   `test_sense_survives_raising_source_and_reports_status`'s status assert (`test_runner.py:697`) does NOT change.
4. `Runner.available()` lists the games that are not hidden, not the inputs. Input filtering lives in the lobby
   (`needs <= inputs`), so only `sense()` changes.
5. The asserts that do change are elsewhere: `test_pose_mediapipe.py:149` (the camera now gives a grid and blobs),
   `test_scenario.py:217-218` (raw replay is built), and `test_jump.py:130` (`FIGURE_H`).
6. `run` is already the default command (`main.py:209-211`). `--require` exists only on `doctor`.
7. `import arcade.main` must not load `cv2` (`test_doctor.py:46`), but `blobs.py` imports `cv2` at its top. The
   exports cannot include `blobs`, and raw replay must import it inside its path.
