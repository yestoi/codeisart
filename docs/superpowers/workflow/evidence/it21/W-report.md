# it21 W report: blobs and motion from the camera sources (M5's wiring)

Implementer: opus, worktree `/Users/trey/dev/codeisart/.claude/worktrees/agent-aa733f494812f7d90`, branch
`worktree-agent-aa733f494812f7d90`. Started at 90c3397 (checked: `git rev-parse --short HEAD` printed 90c3397).
Code commit: a5e98c8. `arcade` resolves to the worktree (`python -c "import arcade; print(arcade.__file__)"`, checked).

## Files changed
- `arcade/sources/blobs.py`:
  - `WORK_SIZE = (160, 120)`; new module function `shrink(frame, work=WORK_SIZE)`: `cv2.resize(frame, work,
    interpolation=cv2.INTER_AREA)` when `frame.shape[1] > work[0]`, else the frame itself.
  - `motion_grid(prev_gray, gray, zone, size, *, mirror=True)`: the flip of the moved-pixel mask only with `mirror`.
  - `FrameFeatures(size=(160, 120), calibration=None, *, mirror=True, work=WORK_SIZE, hide_still=True)`, all four
    kept as attributes. `update` shrinks first, then: grey; motion (`mirror` passed on); `find_blobs` (32);
    x flipped only with `mirror`; blobs within a `calibration.static_mask` light's radius dropped (`_static`:
    `_fw(dx, dy, aspect) <= r`, frame widths, the working frame's aspect) BEFORE the tracker; tracker;
    `StaticMask` only while `hide_still`; `[:MAX_BLOBS]`; `place_blob`.
  - `_prev` is now the public attribute `gray` (the last working frame in grey, unflipped): the tap reads it.
  - Docstrings: `motion_grid`'s and `FrameFeatures`' updated ("wired in iteration 21" gone).
- `arcade/sources/pose_mediapipe.py`:
  - `provides = CAMERA_INPUTS` (class attribute, imported from `arcade.sensed`).
  - `__init__`: `self.features = FrameFeatures(size, calibration, mirror=cfg.mirror)` (the wall's size, the
    source's calibration, the same object its `BodyTracker` gets); `self.tap = None`. `FrameFeatures` is imported
    inside `__init__`, so importing `pose_mediapipe` still loads no `cv2` (it is imported lazily too).
  - `step`: on a due capture, after the detections are merged: `blobs, motion = self.features.update(frame,
    capture_t)`; `tap = self.tap` (read once); when set, `tap(RawRecord(capture_t, detections=tuple(merged),
    frame=raw_frame(self.features.gray)))` on the camera's thread (samples default empty); returns
    `(capture_t, bodies, blobs, motion)`.
  - New module function `raw_frame(gray)`: the grey frame itself when it is `FRAME_SHAPE` (120, 160) (a 640x480
    capture's working frame is), else resized to it with `INTER_AREA` (a frame 160 px wide or narrower is not
    shrunk by `FrameFeatures`, the tests' 64x48 fake for one), so `encode_raw` always takes the tap's record.
  - Docstrings: the module's (:1-3) and the class's (:124) lose "until M5"; the class's documents `tap`.
- `tests/arcade/test_blobs.py`: the named setup change at :89 (now :101), `FrameFeatures()` to
  `FrameFeatures(work=(200, 150))`; a `light_640` helper (the 160x120 light drawn 4 times larger at 640x480);
  5 new tests.
- `tests/arcade/test_pose_mediapipe.py`: the named assert change at :149 (now :165): `blobs == () and
  motion.shape == (64, 128) and not motion.any()`, the test's name unchanged; `FakeCapture` gains `make` (a frame
  per read) and `camera()` passes it; a `moving_light` frame maker; 4 new tests.
- No other assert changed; nothing removed or loosened.

## TDD
RED: the tests were written first. With no code, both files failed at collection (`cannot import name
'WORK_SIZE'`). With only the constant added, 11 failed, each for its own missing piece: `FrameFeatures()` took no
`work` (the :89 setup), `mirror` or `hide_still`; the spy saw `(480, 640, 3)`, not `(120, 160, 3)`; the static-mask
lamp was not dropped (two blobs); the 640x480 perf mean was 3.71 ms (over 3 ms); `motion` was `None` (:149);
`step` gave no blobs; `MediaPipeCamera` had no `features`, `provides` or `tap`. GREEN after the code above.

## New tests
- `test_blobs.py`: `test_a_640x480_frame_is_shrunk_first` (the spied `find_blobs` sees `(120, 160, 3)`; the blob
  of the light drawn at 640x480 lies within 1/160 of the 160x120 one in x and y); `test_mirror_off_keeps_camera_x_
  for_blobs_and_motion` (blob x 0.75 without the flip; the motion of the camera's right stays in the grid's right
  half; `motion_grid(..., mirror=False)` puts camera columns 40..50 in cell (0, 0), mirrored (0, 7));
  `test_a_blob_in_the_static_mask_is_dropped` (dropped at 0 and at 0.048 frame heights = 0.036 fw from a 0.04 radius
  light, kept at 0.06 heights = 0.045 fw: the radius is in frame widths; the carried light then has id 1, so the
  lamp never reached the tracker); `test_hide_still_off_keeps_a_still_lamp` (12 s still at 10 fps: shown on all 121
  frames with `hide_still=False` by keyword and by attribute; hidden from 5.0 s by default);
  `test_features_under_3ms_at_640x480_input` (perf, `thread_time`, mean of 50, seed `zlib.crc32`).
- `test_pose_mediapipe.py`: `test_step_returns_blobs_and_motion` (640x480 frames, a red light moving 8 px left a
  read; the first capture: one blob, an all-False (64, 128) grid; the second: the same id 1, `vx > 0`, x mirrored,
  lit cells, under 10 percent lit); `test_features_use_the_wall_grid_and_the_sources_calibration` (`size` (128, 64),
  `work` `WORK_SIZE`, the same `Calibration` object as the tracker's, `mirror` from the config, `hide_still` True);
  `test_mediapipe_provides_every_camera_input` (the class attribute, and the runner's `_provides`);
  `test_tap_gets_one_raw_record_per_due_capture` (30 fps reads, 10 fps inference, a doubled pose: one record per due
  capture and none on a skipped read; `t` the capture time; detections `((box_of(raw), raw),)` with `raw` the
  mirrored, unsmoothed keypoints of the first pose; the frame `FRAME_SHAPE` uint8 and equal to the INTER_AREA
  shrink of that read's frame in grey, unflipped; `encode_raw` takes it; none after `tap = None`; the fake's 64x48
  frame still gives a `FRAME_SHAPE` frame).

## Runs (from the worktree root)
- Mine: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs
  --durations=15 tests/arcade/test_blobs.py tests/arcade/test_pose_mediapipe.py`: 46 passed, 1 skipped in 0.68 s
  (was 37 passed, 1 skipped: 9 new tests). The skip is `test_real_landmarker_runs_on_a_blank_frame` (no `models/`
  in a worktree; expected).
- Guards: the same command on `tests/arcade/test_blobs.py tests/arcade/test_pose_mediapipe.py
  tests/arcade/test_doctor.py tests/arcade/test_sources.py tests/arcade/test_runner.py tests/arcade/test_scenario.py`:
  196 passed, 1 skipped in 6.11 s (`test_importing_main_loads_no_hardware_module` among them).
- Extra guard (`make_sources` builds a `MediaPipeCamera` by default): `tests/arcade/test_main.py`: 5 passed in 1.61 s.
- The whole suite was not run (the task's rule).

## Time added (`--durations=15`)
`test_hide_still_off_keeps_a_still_lamp` 0.11 s, `test_features_under_3ms_at_640x480_input` 0.03 s; the other
seven under 0.005 s each (hidden by pytest). About 0.15 s in all, inside W's +1.5 s share.

## Perf (thread_time, this Mac, shared)
- `FrameFeatures.update` at 640x480 input: mean 0.444 ms, max 0.547 ms (50 updates; 6 lights, a moving body).
  Before the shrink (the RED run): mean 3.71 ms. A probe of the same scene: 3.54 ms thread, 3.59 ms wall unshrunk.
- At 160x120 (the existing test, unchanged): mean 0.411 ms, max 0.571 ms.
- `shrink` alone, 640x480 to 160x120 (probe, 200 calls): 0.017 ms thread and 0.017 ms wall (cv2 at 8 threads: no
  hidden work on other threads). The plan review measured 0.39 ms; I could not reproduce that.

## Deviations from the plan
1. `FrameFeatures._prev` became the public `gray`: the tap takes the working frame from it, with no second
   shrink or colour conversion. Each update makes a new array and never writes into the old one, so a record
   can keep it.
2. Two new helpers the plan does not name: `blobs.shrink` and `pose_mediapipe.raw_frame` (see above).
3. `FrameFeatures` is imported inside `MediaPipeCamera.__init__`, not at the top of `pose_mediapipe`. This is
   stricter than the plan needs, since the module is already imported lazily. `opencv-contrib-python` is a core
   dependency (`pyproject.toml`), so the import cannot fail where `cv2` exists.
4. `hide_still` False skips `StaticMask` entirely, so its clock does not run while the flag is off. Turning it back
   on resumes from the mask's last state. Nothing turns it back on today: calibrate exits.
5. A blob exactly on a static light's radius is dropped (`<=`).
6. The 640x480 perf scene uses cores of 2 to 4 px (in 160x120 terms), not the 160x120 test's 1 to 3: a 1 px core
   (4 px radius at 640x480) is under `MIN_AREA` once shrunk (see Q-W1).

## Notes for the other tasks
- R: the tap runs on the camera's thread. A tap that raises ends that thread (`ThreadedCamera` logs it, and the
  camera becomes unavailable). `step` reads `tap` once per capture, so clearing it from the main thread is safe,
  but a call that has already started finishes. Close the camera (it joins the thread) before closing the writer,
  as the plan orders.
- C: every `MediaPipeCamera` has `features` (it is built before the model and camera checks, so an unavailable
  camera has one too); `camera.features.hide_still = False` works on it.
- RP: `FrameFeatures(MOTION_GRID, calibration, mirror=...)` matches. A raw frame (120, 160) is not shrunk, because
  it is not wider than 160. A raw record's frame is the unflipped working frame, so raw replay passes the header's
  `mirror` as the source did.

## Questions for the owner (each with the default taken)
- **Q-W1, the smallest light after the shrink.** Blobs are now found at 160x120 on the Mac too. A core needs
  `MIN_AREA` = 4 px there, which is about 64 px at 640x480: a light core 9 px across at 640x480 is no longer seen.
  S1's Q1 (refit `MIN_AREA` at 160x120 with GATE A's recorded lights) now covers the Mac's camera as well.
  Default: keep 4.
- **Q-W2, a camera that is not 4:3.** A camera that ignores `CAPTURE_SIZE` and gives 1280x720 is shrunk to
  160x120, as the plan says. Positions stay right in frame units. But the frame-width distances (`MATCH_DIST`,
  `STATIC_MOVE`, the static mask's radius) then use a 4:3 aspect instead of 16:9, so y distances count 1.33 times
  too much, and a raw record's frame is squashed the same way. Default: the plan's reading (the Mac's camera
  gives 640x480).

## Privacy and the import guard
No `imwrite`, `imencode`, `VideoWriter`, `savez`, `tofile`, `.save` or `import wave` in either module (checked
with grep). Raw frames leave only through `tap`, as a `RawRecord` for `scenario.encode_raw`. `import arcade.main`
still loads no `cv2` (`test_doctor.py` passes).
