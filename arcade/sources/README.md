# Sources

Measured facts and decisions (spec 12).

## Pose on the sensor (Q182, 2026-10-02)

- The Pi reads bodies from PoseNet on the IMX500 (`camera = "imx500"`): `PoseCamera` (formerly `MediaPipeCamera`, the name stays as an alias) with `IMX500Pose`, which
  decodes the three tensors `Picamera2Capture` keeps from each request's metadata. The decoder in
  `pose_imx500.py` is a port of tfjs posenet's multi-pose decoding; the spike that chose it over HigherHRNet
  (10 a second, the sensor's cap) is `docs/superpowers/reviews/2026-10-02-imx500-pose-spike.md`. Measured: 30
  tensors a second, 48 ms sensor to keypoints, 3 ms to decode on the Pi; a still nose 1.5 px at 640 wide.
- The Mac keeps MediaPipe (`MediaPipeDetector`, 33 landmarks cut to COCO 17 by `MP_TO_COCO`); both detectors give
  the same 17 keypoints, normalised and unmirrored, and the tracker does not know which ran.
- Not done: the tracker's filter is tuned on MediaPipe's shake; `night_lux` from the sensor's metadata; the
  30 s reopen retry; `record --raw` still accepts `camera = "mediapipe"` only (`record.py` checks the name; the
  imx500 camera has the same tap and could be let in).

## Inputs, wiring, replay, record and calibrate (iteration 21)

- `provides`: a camera claims the camera inputs it serves (`MediaPipeCamera` all three, `walkup` pose only, a replay its header's `inputs`); the runner hands the lobby and the games only those (C35).
- The wiring: `MediaPipeCamera` runs `FrameFeatures` on each capture the model sees (shrunk to 160x120, mirrored as `cfg.mirror`, the calibration's static lights dropped), so blobs and the motion grid come from the live camera.
- Raw replay: `open_replay` on a raw file runs its grey frames and detections through `FrameFeatures` and `BodyTracker` again (pose and motion, no blobs, no audio); `run --replay PATH` plays any scenario file.
- `record` (consent required, refused on the wall unless `allow_record`; `--raw` on the mediapipe camera only) and `calibrate` (writes `calibration.json` on success only) run as the runner's lobby, so their screens pass the limiter and the governor.

<!-- env_check:begin -->
## Environment (tools/env_check.py, 2026-09-27)

- Python 3.12.13 on macOS-15.6-arm64-arm-64bit
- PoseLandmarker VIDEO mode ran: 0 poses, 9.9 ms per frame
- SDL duplicate-class warnings importing cv2 with pygame: 17

| Package | Version |
|---|---|
| mediapipe | 1.0.0 |
| opencv-contrib-python | 5.0.0.93 |
| numpy | 2.5.3 |
| pygame | 2.6.1 |
| sounddevice | 0.5.6 |
| Pillow | 12.3.0 |
| pytest | 9.1.1 |

pyproject.toml bounds each package below its next major version.
<!-- env_check:end -->
