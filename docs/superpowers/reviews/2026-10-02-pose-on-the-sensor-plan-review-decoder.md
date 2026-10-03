# Plan review, decoder lens: pose on the sensor (2026-10-02)

Plan: `docs/superpowers/plans/2026-10-02-pose-on-the-sensor.md`. Spec: `docs/superpowers/specs/2026-10-02-pose-on-the-sensor-design.md`.
Lens: the PoseNet decoder (Task 3), the picamera2 and IMX500 facts (Task 2, `open_imx500`), the crowd.

Method: the plan's Task 3 module and its tests were typed in as written into the scratchpad
(`review-decoder/pose_imx500_plan.py`, `review-decoder/test_plan_decoder.py`), the fixtures built with Task 0's
command from the spike's `posenet_raw.npz`, and the tests run with the main venv. Layout, unit and crowd probes ran
against all 30 saved samples. Nothing on the Pi; nothing in the repository changed.

Result of the plan's own tests as written: 8 passed, 1 failed (`test_zero_tensors_give_no_body`).

## Critical (would break the build or the wall)

### C1. Task 3, `test_zero_tensors_give_no_body` fails as written: a zero heatmap is sigmoid 0.5, not "no body"

Plan line 554-555: `assert decode_multiple([np.zeros(s, np.float32) for s in SHAPES]) == []`.

The heatmaps are log-odds; `_sigmoid(0) = 0.5 >= score_thr 0.3`, and with every cell equal, every cell is "the
maximum of its neighbourhood" (`>=`), so `_local_maxima` yields 12121 roots and the decoder returns ten poses at
instance score 0.5. The decoder is right; the test's premise is wrong, and Step 4's "Expected: 10 passed" will not
happen.

Evidence:
```
$ .venv/bin/python -m pytest test_plan_decoder.py -q
FAILED test_plan_decoder.py::test_zero_tensors_give_no_body - assert [(0.5, [...]), ...] == []
  Left contains 10 more items, first extra item: (0.5, [(0.9979..., 0.9971..., 0.5), ...
1 failed, 8 passed
```

Fix: a cold heatmap, not a zero one. `heat = np.full(SHAPES[0], -20.0, np.float32)` with zero offsets and mid
offsets, and rename the test "a cold heatmap gives no body". Keep the spec's section 4 wording in step.

### C2. A crowd kills the camera thread: the tracker's `assign()` has no scipy on the Pi and stops at 6 by 6

Task 3 `decode_multiple(..., max_poses=10)` and `IMX500Pose` pass every body at instance 0.3 or better to
`PoseCamera.step`, which hands them to `BodyTracker.update`. `arcade/sources/camera.py:45-58`: without scipy,
`assign()` runs `_exhaustive`, which raises `ValueError` when both sides exceed `MAX_EXHAUSTIVE = 6`. The spike
report says the Pi has no scipy and the plan's Tech Stack says "no new dependency". MediaPipe never got here
(`NUM_POSES = 2`). PoseNet in a crowd can: the spike saw 10 people with HigherHRNet in the same crowd. Seven
detections against seven live tracks (coasting ones count for `DROP_SECONDS`) raise inside `step()`, `ThreadedCamera._run`
logs "thread died; camera unavailable", and nothing restarts it ("there is no 30 s retry yet"). The wall goes to
the no-camera state until someone restarts the process. Short of that, the exhaustive search is slow when many
tracks coast:

```
6x6: 0 ms   7x6: 2 ms   8x6: 8 ms   10x6: 63 ms   6x10: 65 ms   (Mac; the Pi 5 is slower)
7x7: ValueError: assign: 7x7 needs scipy (exhaustive search stops at 6)
Mac venv: no scipy
```

Fix: cap the bodies the detector hands on. In `IMX500Pose.detect`, keep the best `MAX_BODIES = 4` by instance score
(`decode_multiple(outputs, max_poses=MAX_BODIES)` is not enough on its own: the cap must hold after the
`min_instance` filter too, which it does when `max_poses` is the cap). Four is plenty for a one-player lobby
(`player_sized` picks the player) and keeps `assign()` at P(n, 4). Separately, put `scipy` in the `pi` extra: the
tracker already prefers it, and it ends both the raise and the cost. Add a test that a tensor with seven roots
above threshold gives at most four bodies.

## Important (wrong but survivable)

### I1. The "second body" is not a duplicate near 0: 27 of 30 samples carry one at 0.33 to 0.72, and `merge_duplicates` keeps it

Plan line 544: `assert sum(1 for p in poses if p[0] > 0.3) <= 2   # the duplicates score near 0`; spike report:
"Duplicates come out at an instance score near 0 and go at the 0.3 threshold". True for same-root duplicates, but
on the saved tensors a second body above 0.3 is the rule, not the exception, and it is 0.10 to 0.17 frame units
from the first (60 to 110 px at 640), far outside `DUP_DISTANCE = 0.04`:

```
s1:  second pose inst 0.46; dist nose 0.115 lsho 0.083 rsho 0.140
s6:  second pose inst 0.72; dist nose 0.096 lsho 0.098 rsho 0.098   (16 confident points, nose conf 0.99)
s9:  second pose inst 0.70; dist nose 0.142 lsho 0.136 rsho 0.145
s28: second pose inst 0.67; dist nose 0.107 lsho 0.097 rsho 0.128
samples with 2 bodies after merge_duplicates: 27 of 30
```

Its y structure (nose 0.58, shoulders 0.63, hips 0.75, knees 0.87) is a differently scaled body beside the first
(nose 0.55, shoulders 0.59, hips 0.71, knees 0.80), so it is most likely a real second person at the event, not a
ghost; the tensors alone cannot settle it. The plan's test passes on s1 (two above 0.3) and s4 (one), so the build
is fine, but the comment and the spec's section 6 ("2 with PoseNet's 0.3 instance threshold") describe the data
wrongly, and the wall session has no step that tells a ghost from a bystander.

Fix: change the comment to "a second person, or none"; add to the wall session (spec section 5, step 3) "one
person alone in front of the wall: one figure, not two", and if two appear, `MIN_INSTANCE` is the knob (0.5
clears every second body in these 30 samples except s6 and s9).

### I2. Clipping to [0, 1] in the decoder changes what the tracker sees compared with MediaPipe's path

Plan Review Focus 3 and `decode_multiple`'s return (line 755): every coordinate is clipped to [0, 1] "so `box_of` and
the tracker never see a coordinate past the frame". They never did: `box_of` clamps (`pose_mediapipe.py:85-92`), and
`Body.__post_init__` runs `_clean` on every keypoint (`sensed.py:49-55`), which clamps the coordinate *and zeroes
the confidence* of a point outside the frame. The scenario writer also admits raw keypoints in
`KEYPOINT_RANGE = (-1.0, 2.0)`. So the clip is not needed for safety, and it changes behaviour: an ankle decoded at
y 1.04 (the spike saw them) reaches the tracker as a *confident* ankle on the bottom edge, where the MediaPipe
detector's identical ankle becomes conf 0.0.

```
clipped ankle (1.0, conf .82)   -> Keypoint(x=0.5, y=1.0, conf=0.82)
unclipped ankle (1.04, conf .82) -> Keypoint(x=0.5, y=1.0, conf=0.0)
```

The plan promises "the tracker does not know which ran" (Task 7 README text). Fix: either drop the clip and let
`_clean` rule for both detectors, or clip and set conf to 0.0 when the raw point lay outside the input (one line in
the return comprehension). Keep `test_keypoints_are_clipped_to_the_frame` either way, asserting the chosen rule.

## Minor

### M1. Review Focus 2's trigger cannot happen as described, and its outcome is harsh

"HigherHRNet still loaded from the spike: its tensors have other shapes". `open_imx500` calls `IMX500(MODEL)` with
the posenet file, which replaces the network on the sensor; during the upload the metadata carries no tensor
(Review Focus 1's case), not HigherHRNet's. The shape check is still worth having, but its hint "(is another
network on the sensor?)" names a cause the code has just ruled out, and a single odd tensor kills the camera thread
for good. Fix: log once and return `[]` from `IMX500Pose.detect` on `ValueError`, or keep the raise and reword the
hint to "the sensor's firmware or model file is not the posenet this decoder knows".

### M2. `show_network_fw_progress_bar()` before `Picamera2()` differs from the spike and the demos

Plan line 804-805 calls it before `Picamera2(imx.camera_num)` exists. The spike's `posenet_live.py` and
picamera2's IMX500 demos call it after the Picamera2 object and the configuration, right before `start()`. It
probably only polls the IMX500 device the helper opened itself, so the order may not matter, but the proven order
costs nothing. Fix: build the `Picamera2` first, call the progress bar, then `Picamera2Capture(..., camera=cam)`
(which configures and starts).

### M3. `test_keypoints_are_clipped_to_the_frame` passes trivially

`off + 400` pushes every point past the input on both axes, so all 17 clip to 1.0; the test proves the clip runs,
not the walk-off case it names (a chain step off the map while the root is inside). Fine as a smoke test; if I2's
fix zeroes conf, assert that too.

### M4. Rounding: `round()` on numpy floats is half-to-even; tfjs `Math.round` is half-up

`_cell` differs from tfjs at exact .5 cell boundaries only. Immaterial to results; noting it so nobody chases it.

### M5. The plan's `_due` pacer at 30 of 30

Outside this lens but seen while reading: `PoseCamera._due` stamps frames with the read-return clock and skips a
frame that lands more than `EARLY` early. At 30 captures for 30 tensors a jittery read drops a tensor now and then
(the spike measured 28.85/s without the pacer). Harmless; `SensorTimestamp` from the metadata would pace exactly if
the lag line shows it matters.

## Checked and fine

- **Tensor layout and units, against the data.** Decoding all 30 samples with alternative layouts and scoring the
  best body's instance score (the mean heatmap score at the traversed cells; a wrong layout lands off the peaks):
  ```
  plan (y-first short offsets; mid = fwd y, fwd x, bwd y, bwd x; pixels)   mean 0.833  min 0.733
  mid x-first                                                              mean 0.677  min 0.546
  bwd first                                                                mean 0.413  min 0.332
  short offsets x-first                                                    mean 0.363  min 0.143
  mid in map units (x16)                                                   mean 0.159  min 0.107
  ```
  The instance score cannot tell pixels from "already divided by 16" (0.835 vs 0.833, the refinement snaps both),
  so the units were settled by the residual between the displaced point and the refined child: 6.2 px median for
  the plan's pixels, 16.9 px for mid/16, and the body degenerates for mid x16. The raw short offsets lie in
  [-16, 15.9], one stride cell: input pixels. The spike's "rpicam-apps divides by STRIDE" does not apply to what
  `get_outputs` hands over; the plan's raw use is right.
- **One backward then one forward pass reaches every keypoint from any root.** `EDGES` lists every parent edge
  before its child edges (0..3 head, 4..9 left side, 10..15 right side). The reverse pass from any root climbs to
  the nose because each ancestor edge has a lower index; the forward pass from the nose fills every branch because
  each parent edge comes first. That is tfjs's `decodePose` exactly (reverse over edges with `displacementsBwd`,
  then in order with `displacementsFwd`).
- **tfjs semantics otherwise.** Local maximum window radius 1 with `>=` (tfjs rejects only a strictly greater
  neighbour); root NMS against the same keypoint id of earlier poses within 20 px; instance score as the mean over
  keypoints not claimed by an earlier pose; two offset refinements; displacement index `edge` for y and
  `edge + 16` for x; short offsets `kp` for y and `kp + 17` for x; cell = clamp(round(pos / 16)). All as in
  `decodeMultiplePoses` / `traverseToTargetKeypoint` / `getInstanceScore`.
- **The plan's thresholds hold on the fixtures.** s1: instance 0.85, nose (0.387, 0.554), shoulders dy 0.000,
  two poses above 0.3. s4: instance 0.89, nose (0.424, 0.565), shoulders dy 0.006, one pose above 0.3. Nose above
  both ankles (0.91), left shoulder x > right shoulder x in both. Across all 30 samples the best body scores 0.73
  to 0.90 and the shoulders are level within 0.014, so the 0.02 and 0.7 margins are safe. Decode 4 to 5 ms on the
  Mac including warm-up.
- **Task 0 fixtures.** Every value of s1 and s4 is float16-exact; the compressed files are 75,492 and 75,084 bytes;
  `git check-ignore` exits 1 (not ignored; `.gitignore:16` anchors the arcade data rule away from
  `tests/arcade/fixtures/`).
- **`IMX500Pose.detect` and the fakes.** `test_detect_decodes...` (one or two bodies, nose x 0.39, conf > 0.3),
  `test_detect_without_a_tensor...` (returns before `get_outputs`), `test_bodies_under_min_instance...` and
  `test_describe...` ("posenet 30/s" with an int rate) all pass as written. The truthiness test on
  `metadata.get("CnnOutputTensor")` is the one the spike's `posenet_shapes.py` ran on the Pi.
- **picamera2 facts.** `IMX500(model).camera_num`, `.network_intrinsics`, `NetworkIntrinsics().task` /
  `update_with_defaults()` / `inference_rate`, `show_network_fw_progress_bar()`, `get_outputs(md, add_batch=False)`,
  `capture_request()`, `request.get_metadata()`, `request.make_array("main")`, `request.release()` and
  `buffer_count=12` were all exercised by the spike's scripts on the Pi's picamera2 0.3.37. `capture_request(wait=)`
  goes through the same `dispatch_functions` timeout path as the wall-proven `capture_array("main", wait=READ_TIMEOUT)`
  (a float is a timeout; `TimeoutError` after it). `create_video_configuration` accepts `buffer_count` (default 6,
  preview's is 4). Task 2's `read()` releases the request in `finally` before the `except` branch returns.
- **Video configuration in place of the spike's preview configuration.** Video adds default controls
  `FrameDurationLimits (33333, 33333)` and `NoiseReductionMode Fast` and `queue=True`; the explicit `FrameRate 30`
  agrees with the limits (and is applied after them). Both pick the IMX500's binned 2028x1520 mode at 30, so the
  main stream is the full 4:3 field. With no `set_auto_aspect_ratio` call the inference ROI stays the full sensor,
  so normalising by 481x353 maps onto the 640x480 frame with no crop correction, as the spec says. Caveat: the
  spike measured this by the body's sanity, not against the frame; the mirror figure in the wall session is the
  check (the plan has it).
- **The upload case.** Frames without a tensor give `[]` per due frame; the tracker coasts 0.3 s and drops at 0.5 s,
  so the lobby sees no body, which is the right state. The plan's "the last result holds" is loose wording: a new
  result with no bodies is published, as for an empty frame today.
