# Final review: pose on the sensor (fb6a678..282c4c8, wall-bringup)

Reviewer: fresh context, read-only. Read: the plan (header, Review Focus, Tasks 0 and 8, self-review), the spec, the
spike report, both plan reviews, the ledger, the whole diff, and the surrounding code (`camera.py` ThreadedCamera and
BodyTracker, `sensed.py` `_clean`, `runner.py` `sense`/`_push`/`loop`, `main.py` doctor and `run`). picamera2's
`IMX500` source was read from its GitHub main branch (`picamera2/devices/imx500/imx500.py`) for the progress bar
and device fd. Ran: `test_pose_imx500.py`, `test_capture_picamera2.py`, `test_doctor.py`, `test_sources.py`
(48 passed, 1.2 s), and a scratch probe (`PYTHONPATH=worktree`) for the assignment cost, bad tensors, the camera end
to end with tensorless frames, and a raising `get_outputs`. Nothing on the Pi; the full suite not run.

## Strengths

- The seam is right and small. `PoseCamera.step` differs from the old `MediaPipeCamera.step` in one place: the
  detector loop. `MediaPipeDetector.detect` does exactly what the old loop did (`bgr[:, :, ::-1]`, then
  `landmarks_to_keypoints` per pose, same order), the model check and `FileNotFoundError` text are the same, and
  the warning reads "mediapipe camera unavailable" for `camera = "mediapipe"` as before. The Mac path is unchanged
  in behaviour.
- Frame and metadata cannot come from different requests. `Picamera2Capture.read` takes both from one request, sets
  `metadata` only on success (`{}` on either failure), and `PoseCamera.step` calls `detect` on the same thread right
  after that `read`. `make_array` copies the buffer, so releasing the request in `finally` is safe.
- Every Critical and Important finding of both plan reviews is in the code: the `pm.PoseCamera` monkeypatch
  (test_sources), the `models/` link, the Mac suite as a ruling, one memoised probe for both names with the
  wait printed every 30 s and ^C named, the spec's doctor command corrected, the cold-heatmap test, the four-body
  cap, no clipping, the tolerant detector, the corrected second-body comment and the wall-session ghost check.
- The decoder is a faithful, readable port; the constants name their sources; the fixtures are small and the tests
  assert physical facts (level shoulders, nose above ankles, left shoulder right of the right one unmirrored).
- `open_imx500` keeps picamera2 out of module import, and `make_sources` degrades to an unavailable, never-started
  camera that closes cleanly.

## Review Focus, item by item

1. **No `CnnOutputTensor`.** Holds. `detect` returns `[]` before `get_outputs`; the probe ran a camera with every
   third frame tensorless: the thread kept going and the bodies coasted one capture (`seen_ago` 0.033) and came
   back. The plan's "the last result holds" is loose: a new result with coasting, then no, bodies is published, as
   MediaPipe's empty frames always did. Correct behaviour.
2. **Unknown tensor.** Holds for what the decoder raises: shapes named, logged once, `[]`, thread alive. Narrower
   than the invariant it serves: see Minor M2.
3. **Off-frame keypoints.** Holds. No clip in `decode_multiple`; `mirror_keypoints` then `Body._clean` clamp and
   zero the confidence for either detector; `box_of` clamps as it did for MediaPipe.
4. **`make_array` raises.** Holds; tested (`test_a_failed_read_releases_the_request`).
5. **`run --require camera` with imx500.** Holds: `run` passes `camera=cfg.camera`; one probe opens the pair as the
   arcade does, prints the upload notice after 3 s of tensorless frames and waits up to 300 s; tested with fakes.
6. **The crowd.** The raise is gone: with at most four detections `min(rows, cols) <= 4`, under `MAX_EXHAUSTIVE`.
   Two softer effects remain (Minor M3, M4).

## Issues

### Critical

None.

### Important

**I1. The runbook reads the lag line as sensor-to-wall; it measures read-to-push, and it is not comparable with
tonight's MediaPipe number.**
`docs/runbooks/arcade-on-the-pi.md:74-76` says the line is "the lag from the sensor's frame to the wall's frame"
with "a median near 70 to 90 ms (48 ms to keypoints plus the tick and the sender)". The code
(`arcade/runner.py:569-576`) computes `clock() - _camera_capture`, and `_camera_capture` is `capture_t`, stamped
by `PoseCamera.step` when `read()` returns (`arcade/sources/pose_mediapipe.py:226`).

- **What is left out.** On the sensor path the exposure, readout and the on-sensor inference all happen before the
  request reaches `read()`, so the 42 to 48 ms the spike measured is outside the number. The line will read roughly
  that much less than the true lag, likely 20 to 40 ms, against the runbook's 70 to 90.
- **Why tonight's number differs.** On MediaPipe's path the 56 ms inference ran after `capture_t`, so it sat inside
  the span.
- **The effect.** The two numbers the owner writes into `live-smoke.md`, imx500's against tonight's, measure
  different spans. The comparison will flatter the sensor by about 100 ms. The spec's formula (`push time -
  capture_t`) is what was built, but the spec's purpose ("lag as a number", read against tonight's verdict) is not
  served by the runbook's reading of it.
- **Fix, minimum.** Reword the runbook and the spec line. The number runs from the frame's arrival at the Pi to the
  push. Add the sensor's 42 to 48 ms for the full lag. MediaPipe's runs include its inference.
- **Fix, better.** Also log the sensor's share from the request's `SensorTimestamp`, which is ns on
  CLOCK_MONOTONIC, the base of `time.monotonic()` on Linux. For example, the detector keeps `read time -
  SensorTimestamp`, and the lag line prints both numbers.

### Minor

**M1. picamera2's progress bar is a non-daemon child that can keep the process from exiting on a failure path.**
`arcade/sources/pose_imx500.py:192`.

- **How it works.** `show_network_fw_progress_bar()` starts a `multiprocessing.Process` without `daemon=True`. Its
  loop ends only when the network stage reports more than 95 % uploaded. At exit, `multiprocessing` joins every
  non-daemon child.
- **When it hangs.** The camera may fail to configure or start after the bar has started. Or the probe may give up,
  or be stopped, before the upload ends. In either case the child can loop forever. The doctor then prints its
  UNAVAILABLE line and does not exit, and `run --require camera` does not return 1. Under
  `systemd-run --wait` and the Pi's lock, the lock stays held.
- **Conditions.** This happens only when the bar is available. That means `cat /sys/kernel/debug/...` succeeds (root)
  or `sudo -n /usr/sbin/debug_stream_imx500.sh` does. Otherwise picamera2 prints "progress bar is not available" and
  starts no child. I could not check which applies to user trey on the Pi.
- **Fix.** Drop the call, since the doctor already prints its own notice. Or terminate leftover
  `multiprocessing.active_children()` in `open_imx500`'s failure path and after a failed probe.
- **Wall check.** The first `--seconds` run must end by itself.

**M2. The detector's guard covers only the decoder's `ValueError`.** `arcade/sources/pose_imx500.py:147-155`.

- **What escapes.** `self._imx.get_outputs(...)` sits outside the `try`. A tensor whose length disagrees with
  `CnnOutputTensorInfo` raises in its `reshape`, and a missing info raises in `get_output_shapes`. An `inf` in the
  offsets raises `OverflowError` in `_cell`'s `round()`: measured, "cannot convert float infinity to integer".
- **The effect.** Any of these ends the camera thread for the night, since there is no retry. All are unlikely.
- **Fix.** Wrap `get_outputs` and `decode_multiple` together in `except Exception`, logged once. A NaN already
  lands in the `ValueError` branch, with the message "cannot convert float NaN to integer".

**M3. In a crowd, the ten-pose budget goes to duplicates before people.** `arcade/sources/pose_imx500.py:101`
(`max_poses=10`).

- **The duplicates.** With `max_poses=100` the fixtures decode 6 poses for sample1, scored 0.85, 0.46, 0.12, 0.07,
  0.03 and 0.03, and 5 for sample2. That is two to three same-person duplicates per real body, and each one
  consumes a slot.
- **The effect.** With 4 or more people, only about the first three or four, ranked by their single strongest
  keypoint, get decoded. The instance-score sort and the cap of four then choose among those.
- **Fix.** Raise `max_poses` to about 20; decoding is cheap. Or stop counting poses whose instance falls under
  `min_instance` toward the limit.

**M4. "Best first" is the best instance score, which is not necessarily the player.**
`arcade/sources/pose_imx500.py:157`.

- **The risk.** A player close to the wall with feet out of frame loses roughly 0.1 of instance score. Fully
  visible bystanders can then outrank the player and take the four slots.
- **What follows.** The tracker and `player_sized` can only pick from what reaches them.
- **Fix.** Nothing now. If the wall shows the player being dropped in a crowd, rank the four by box height, or by
  instance times box height.

**M5. The tracker's assignment cost still grows with coasting tracks.**

- **Why.** Without scipy, `assign()` tries P(tracks, 4) pairings. In a crowd, tracks for people who drop out of the
  top four live for `DROP_SECONDS` (0.5 s).
- **Cost.** Measured on the Mac with 4 detections:

  | tracks | cost |
  |---|---|
  | 12 | 4.2 ms |
  | 16 | 15.5 ms |
  | 20 | 41.8 ms |

  The Pi 5 is slower, and the budget is 33 ms a capture.
- **Fix.** None needed tonight. If the wall shows the capture rate falling in a crowd, scipy in the `pi` extra
  ends it, which the plan had deferred.

**M6. The lag line keeps reporting after the camera has gone.** `arcade/runner.py:569-576`.

- **Why.** `_camera_capture` holds the last fresh capture. When the camera goes stale or its thread dies, every
  later push appends an ever-growing age, so the line reads, for example, "median 45000 ms".
- **Fix.** Append only while the capture is within `CAMERA_STALE`, or log "no camera" instead.

**M7. Doctor probe details.** `arcade/main.py:72-109`.

- **Any tensor passes.** The probe reports ok on any tensor without decoding it. A network the decoder does not
  know passes the doctor, and the arcade then shows no bodies. Fix: call `detector.detect(frame, 0)` once on the
  first tensor and report the shapes error.
- **Long timeouts shrink.** A `--timeout` above 300 is cut to 300 when the notice fires (line 100). Fix: use
  `max(timeout, upload_wait)`.
- **^C prints a traceback.** ^C during the wait leaves `doctor` and `run` with a traceback, because `doctor` catches
  only `Exception`.
- **The rate can drop out.** When `network_intrinsics` is None, `open_imx500` (line 188) builds a fresh
  `NetworkIntrinsics` without attaching it, so `describe` drops the rate from the doctor's line.

**M8. The worktree's `models` symlink is not ignored.**

- **Why.** `.gitignore:17` has `/models/`, which matches directories only. The symlink created in Task 0 shows as
  `?? models`, and `git add -A` would commit a link to `/Users/trey/dev/codeisart/models`.
- **Fix.** Add `/models` to `.gitignore`, or stage by path.

## Declined to judge

- **The `_due` pacer.** It stamps read-return times instead of `SensorTimestamp` at 30 of 30. The plan's
  self-review lists it as "not taken" (decoder review M5).
- **scipy in the Pi extra.** The plan lists it as "not taken"; its effect is noted in M5.
- **Which frame a tensor belongs to.** Whether the tensor in request N infers frame N or an earlier one affects how
  keypoints line up with blobs and motion. The spec is silent, and the wall's mirror figure is the check.
- **The second body at instance 0.33 to 0.72.** The spec's wall session, step 3, owns it, with `MIN_INSTANCE` as
  the knob.
- **The One Euro filter tuned on MediaPipe's shake.** Spec 3.5 says the tracker is not changed.
- **`record --raw` refusing `camera = "imx500"`.** The README lists it as not done.
- **The doctor's notice for `capture = "opencv"` beside imx500.** The spec now says it is not built.
- **The 30 s camera reopen retry.** Spec section 7 leaves it out.
- **The progress-bar `fork()` from a threaded parent.** The libcamera thread exists by then. This is picamera2's own
  design, and its demos do the same.
- **Added lines over 120 characters.** Eight added lines exceed 120 characters (the module docstring, the test
  imports). The repository configures no linter.
- **The Task 8 ruling.** The executor chose to run the full suite on the Mac. The plan said to ask the owner. The
  ruling is reasonable, because promptviz holds the Pi and the owner asked that nothing disturb it, and Q102 allows
  under 540 s. It is still the owner's rule to waive, and the hand-off should say it was waived.
- **The Task 1 ruling.** The executor used `person_landmarks(right_hand_up=True)` for the second person. It has no
  behavioural effect.

## Recommendations

1. Fix I1 in the runbook and spec now; the better fix (the sensor's share from `SensorTimestamp`) can follow.
2. Take M2's `except Exception`, M3's `max_poses`, M6's staleness guard and M8's ignore line before the wall. Each
   is a line or two.
3. Add to the wall session: check that the first `run --seconds` and the doctor end by themselves (M1). In a crowd,
   watch whether the player keeps their figure (M4) and whether the capture rate holds (M5).
4. One test would cover the gap between the unit tests and the thread. It runs a `PoseCamera` with `IMX500Pose`
   over a fake capture that mixes frames with and without tensors, plus one bad tensor. It asserts that `step()`
   never raises and the bodies coast and return. The scratch probe for this review did exactly that and passed.

## Assessment

**Ready to merge: With fixes.** The code does what the plan and spec ask, the Mac path is unchanged and all six
Review Focus items hold. I1 should be fixed before the owner reads the lag number at the wall, and M1, M2 and M3 are
cheap to take with it.
