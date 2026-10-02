# Sources

Measured facts and decisions (spec 12).

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
