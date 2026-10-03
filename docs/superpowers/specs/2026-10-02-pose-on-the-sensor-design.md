# Pose on the sensor: the IMX500 source, stage 3 brought forward

Date: 2026-10-02 night. Owner: Trey. Status: approved in chat; for the owner's review of this text.
Amends `docs/superpowers/specs/2026-10-02-arcade-on-the-wall-design.md`: its stage 3 comes before its stage 2.

## 1. Goal

The arcade reads bodies from the Raspberry Pi AI Camera's own inference (PoseNet on the IMX500 sensor) at 30
captures a second, in place of MediaPipe on the Pi's CPU at 15. Every game, the tracker and the lobby see the
same 17 COCO keypoints they see today; no game changes. The owner's verdict on the wall tonight was lag and
stutter at 15 captures a second; the spike (`docs/superpowers/reviews/2026-10-02-imx500-pose-spike.md`) measured
PoseNet at 30 a second with 48 ms from the sensor's timestamp to keypoints and 3 ms of Pi CPU a frame, and ruled
HigherHRNet out (10 a second, a hard cap).

What the owner said: "It was bad, we need to pull it forward." (lag, and stutter or jitter). Build it as option
1: the spike first (done), then one pose camera with two detectors. "Lets not change what is being displayed on
the screen right now if we can help it": nothing goes to the card until the owner's "go".

## 2. Where it stands

- `MediaPipeCamera` (`arcade/sources/pose_mediapipe.py`) is the one live camera source: it reads frames from an
  injected capture (`read() -> (ok, bgr)`, `release()`), stamps them, runs the frames due at `cfg.camera_fps`
  through a `Landmarker` (MediaPipe, 33 landmarks), cuts them to the 17 COCO points, mirrors, merges duplicates,
  feeds the frame to `FrameFeatures` (blobs, motion grid), calls the record tap, and runs the `BodyTracker`.
- `Picamera2Capture` (`arcade/sources/capture_picamera2.py`) reads the main stream with `capture_array`; it
  carries no request metadata, and the IMX500's output tensor lives in that metadata.
- `camera = "imx500"` is already an accepted value of `ArcadeConfig.camera`; `make_sources` refuses it.
- The sensor holds the PoseNet network since the spike; a different network means a 3 to 4 minute upload.
- The decoder: picamera2 has no Python decoder for PoseNet. The spike's `posenet_decode.py` (a port of tfjs
  posenet's multi-pose decoding) works on the sensor's tensors; it moves into the repository.

## 3. Design

### 3.1 One pose camera, two detectors

`MediaPipeCamera` becomes `PoseCamera`; `MediaPipeCamera = PoseCamera` stays as an alias for the tests and the
doctor. Its `landmarker` argument becomes `detector`, a `PoseDetector`:

```
class PoseDetector(Protocol):
    def detect(self, bgr: np.ndarray, ts_ms: int) -> list[tuple[Keypoint, ...]]: ...   # 17 COCO keypoints each,
    def close(self) -> None: ...                                                       # normalised, unmirrored
```

`step()` changes in one place: `for kps in self._detector.detect(frame, ts)` replaces the landmarker loop and
the `landmarks_to_keypoints` call. Everything after it (mirror, merge, features, tap, tracker) stays as it is.
`MediaPipeDetector` wraps today's `Landmarker`: `detect` converts the frame to RGB, runs it, and returns
`landmarks_to_keypoints` of each pose. `landmarks_to_keypoints` and `MP_TO_COCO` stay where they are.

### 3.2 The capture keeps its metadata

`Picamera2Capture.read()` uses `capture_request()` and returns `make_array("main")`; the request's
`get_metadata()` is kept as `self.metadata` (the latest frame's) before the request is released. The read
timeout stands. The constructor takes `frame_rate` (default `FRAME_RATE`, 30) and `buffer_count` (default
picamera2's), so the IMX500 path can ask for the model's rate and the 12 buffers the demo uses. `camera=` stays
injectable, so the IMX500 path hands in `Picamera2(imx.camera_num)`.

### 3.3 The IMX500 detector

`arcade/sources/pose_imx500.py`:

- `posenet_decode`: the ported decoder as a module-level function set, `decode_multiple(outputs, score_thr,
  max_poses, nms_radius_px) -> list[(instance_score, [(x, y, conf) x 17])]`, with x and y normalised by the
  model's input size (481x353). The tensor layout, the edge list and the stride are constants with a comment
  naming their source (the rpicam-apps `imx500_posenet` stage and tfjs posenet). An output whose shapes are not
  `[23, 31, 17]`, `[23, 31, 34]`, `[23, 31, 64]` raises `ValueError` naming them (the detector logs it once and
  gives no bodies; the camera thread lives): a wrong network on the sensor
  is told, not decoded.
- `IMX500Pose(capture, imx, min_instance=0.3, max_bodies=4)`: at most `MAX_BODIES = 4` bodies reach the tracker
  (its `assign()` has no scipy on the Pi and stops at 6 by 6). `detect(bgr, ts_ms)` ignores the frame, reads
  `capture.metadata`, returns `[]` when it carries no `CnnOutputTensor` (the frame before the first tensor, or a
  dropped one; the camera's last result then holds as it does for a frame with no body), otherwise
  `imx.get_outputs(metadata)` decoded, bodies under `min_instance` dropped, each body's keypoints as
  `Keypoint(x, y, conf)` in COCO order. The sensor's full field is what the main stream shows (the ROI is the
  whole sensor; both are the full 4:3 field scaled), so normalised coordinates map onto the frame without a
  crop correction. `close()` does nothing (the capture owns the camera).
- `open_imx500(cfg, size) -> (Picamera2Capture, IMX500Pose)`: imports picamera2 and
  `picamera2.devices.imx500` here, never at module import; `IMX500(MODEL)` with
  `MODEL = "/usr/share/imx500-models/imx500_network_posenet.rpk"`; the intrinsics' task set to pose estimation;
  `show_network_fw_progress_bar()`; then `Picamera2Capture(CAPTURE_SIZE, camera=Picamera2(imx.camera_num),
  frame_rate=intrinsics.inference_rate, buffer_count=12)`. A failure raises with picamera2's message; the
  caller logs once and leaves the camera unavailable, as the mediapipe path does.

### 3.4 Wiring

- `make_sources`: `cfg.camera == "imx500"` opens the pair and builds `PoseCamera(cfg, size, clock,
  calibration=cal, capture=capture, detector=detector)`. `cfg.capture` is not consulted for `imx500` (the
  capture is picamera2 by nature); the doctor says so when `capture = "opencv"` is set beside it (not built;
  `capture` is ignored for imx500).
- `cfg.camera_fps` still paces the inference: at 30 every tensor is taken; lower drops frames as today.
- The doctor (`arcade/main.py`): a `probe_imx500` opens the pair as the arcade does and waits for the first
  frame carrying a tensor. It waits `--timeout` (default 5 s); when 3 s pass with frames but no tensor it prints
  "uploading the network to the sensor, up to 4 minutes" and waits up to 300 s instead. Its line prints the
  model's file name, the stated rate and the first frame's size (`camera  ok  imx500 posenet 30/s 640x480`).
  `make_probes` picks it when `camera == "imx500"` (the doctor gains `--camera`, default `mediapipe`, and
  `run --require` passes `cfg.camera`). `probe_pose` for `imx500` is the same probe: there is no
  model file on disk to check.
- `arcade.pi.toml`: `camera = "imx500"`, `camera_fps = 30`; `capture = "picamera2"` stays in the file (ignored
  by `imx500`, needed by the fallback). The `mediapipe` path on the Pi stays as the fallback: `run` has no
  `--camera` flag, so the owner sets `camera = "mediapipe"` and `camera_fps = 15` in the file to go back.
- Lag as a number: with `-v` the runner logs, once a second, the age of the latest capture at the push
  (`push time - capture_t`, median and max over the second; `capture_t` is the frame's arrival at the Pi, so on the
  sensor path this leaves out the sensor's own 42 to 48 ms), and the imx500 detector logs the sensor's share
  (`SensorTimestamp` to the decode) once a second. The sum is the lag; a MediaPipe run's capture-age line holds its
  inference, so the two paths compare by the sum (the final review, I1). The owner reads them into `live-smoke.md`.
- No progress bar for the network upload: picamera2's is a non-daemon child that can keep the doctor or the run
  from exiting when the camera fails after it started (the final review, M1); the doctor's own notice stands in.
- `pyproject.toml`: nothing new. picamera2 is apt's; the decoder is numpy; munkres and scipy are not needed
  (HigherHRNet is out).

### 3.5 Not changed

The flash governor, the limiter, the driver and its wall-proven settings; the tracker and its filter (the
spike's shake is below MediaPipe's at rest; a retune, if the wall asks for one, is a carried fix); the games;
the lobby; the Mac path (MediaPipe through OpenCV).

## 4. Tests

- `tests/arcade/test_pose_imx500.py`: the decoder on two tensor samples from the spike, saved compressed under
  `tests/arcade/fixtures/posenet/` (float16, about 100 KB each): one body at instance score above 0.7 with the
  nose near (0.40, 0.56), shoulders level within 0.02, nose above both ankles, 17 keypoints each in [0, 1]; a
  wrong shape raises; a zero tensor gives no body. `IMX500Pose` against a fake capture whose `metadata` carries a
  real sample's tensor as `CnnOutputTensor` and a fake `imx` whose `get_outputs` returns it: one body, and `[]`
  when the metadata has no tensor. `open_imx500` without picamera2 raises, and `make_sources` with
  `camera = "imx500"` on the Mac leaves the camera unavailable and does not raise. The fixtures are test data,
  not evidence images: they are committed (Q98 keeps the loop's evidence PNGs out, not fixtures).
- `tests/arcade/test_capture_picamera2.py`: `read()` returns the frame and sets `metadata` from the request;
  the request is released on the failure path too; `frame_rate` and `buffer_count` reach the configuration.
- `tests/arcade/test_pose_mediapipe.py`: the existing injected-landmarker tests move to an injected detector;
  `MediaPipeDetector` turns fake landmarks into 17 keypoints (the `landmarks_to_keypoints` tests stand).
- The doctor's `imx500` probe with fakes: the model name and rate in its line; the upload notice when the first
  tensor is late.
- The full suite once on the Mac before the code goes to `wall-bringup`'s tip, under 540 s (Q102).

## 5. The wall session (on the owner's "go", by the wall session protocol)

1. promptviz stopped at the owner's word; the wall dark.
2. `doctor --require camera,pose --camera imx500 --capture picamera2` (the doctor takes no `--config`): the line
   names posenet and 30.
3. The mirror figure alone: one person alone in front of the wall is one figure, not two (27 of the spike's 30
   samples decode a second body at instance 0.33 to 0.72 about a tenth of the frame from the first, most likely a
   bystander at the event; if a ghost shows, `MIN_INSTANCE` in `pose_imx500.py` is the knob: 0.5 clears all but
   two of those samples); is left left, does the figure stand still when the owner does, does a raised hand
   read; the `-v` lag line's number.
4. Copy Me through the lobby, then the other games by `--game` as time allows.
5. Verdicts into `live-smoke.md`, the lag number beside them. A fault that stops play is fixed in the session;
   the rest are carried fixes.

Done when: from the Pi with the AI Camera on `camera = "imx500"`, a person walks up, sees their figure, raises
a hand, plays one game to its card and walks away; the sender's line reads no late frame; the lag line is read;
one game's row in `live-smoke.md` has the owner's verdict against tonight's.

## 6. Risks

- **Keypoint quality.** PoseNet is MobileNet-based and older than MediaPipe's model; wrists and ankles at 2 to
  3 m may read worse, and Copy Me's outline and Jump's nose rise depend on them. The wall judges; the fallback
  is `camera = "mediapipe"`, which stays built.
- **The crowd.** The spike saw up to 10 people with HigherHRNet, and a second body above 0.3 in 27 of 30 PoseNet
  samples.
  The tracker and `player_sized` (wall-bringup, 97972ba) pick the player; the threshold is a constant to tune.
- **The upload.** A power cycle may cost a 3 to 4 minute network upload at the first start; the doctor says so.
- **Two sessions on the sources.** The loop's M8 touches `arcade/attract/` and `arcade/main.py`; this work
  touches `arcade/sources/` and `arcade/main.py`'s doctor. The loop stays gated until this is on main, or its
  plan leaves the doctor alone.

## 7. Left out

HigherHRNet and the YOLO11n-pose export; the tracker's retune; `night_lux` from the sensor's metadata; the 30 s
camera reopen retry; the start at boot; anything for a bigger wall.

## 8. The record

Owner decision Q182 (decisions.md): stage 3 before stage 2. `roadmap.md`: the line S3 before M8, in the owner's
session on `wall-bringup`; GATE B loses "IMX500 source with munkres and scipy". The 2026-10-02 design's section 5
points here.
