# Spike: pose on the IMX500 sensor (the AI Camera), 2026-10-02 night

Owner: Trey. Run from the Mac over ssh, on the Pi 5 at the event wall, camera only, under the Pi's lock, with
`nice -n 10`; nothing sent to the card (promptviz held the wall throughout). Throwaway scripts in
`~/imx500-spike/` on the Pi; their JSON results in `~/imx500-spike/out/`.

## Why

MediaPipe's lite model on the Pi gave 15 captures a second (branch `wall-bringup`, `camera_fps = 15`) and the
owner's verdict on the wall was lag and stutter. The arcade spec names an `imx500` source (6.1, core plan Task 19,
HigherHRNet by default) as stage 3 of the 2026-10-02 design, "after; not needed for the vision". The owner pulled
it forward. This spike asks which on-sensor model, at what rate and latency, with how much shake.

## What the Pi has

picamera2 0.3.37 (apt, with `picamera2.devices.imx500`), imx500-all 1.13.0 with the model files under
`/usr/share/imx500-models/`, among them `imx500_network_higherhrnet_coco.rpk` and `imx500_network_posenet.rpk`.
`postprocess_highernet.py` needs `munkres`, which the venv lacks (installed to the spike's own `lib/`, not the venv).
No scipy. The sensor keeps the loaded network across process restarts; a different network means a new upload,
2 MB at about 9 kB/s, 166 to 233 s.

## Results

| model | stated rate | tensors a second | sensor to keypoints (median) | Pi-side parse | people seen |
|---|---|---|---|---|---|
| HigherHRNet, FrameRate 10 | 10 | 9.45 | 87 ms | 2.1 ms | median 3, max 10 (the crowd) |
| HigherHRNet, FrameRate 25 | 10 | 5.8 (frames 23.2) | 33 ms | 3.0 ms | median 5 |
| PoseNet, FrameRate 30, tensors only | 30 | 30.05 | 42 ms | — | — |
| PoseNet, FrameRate 30, decoded, main frame fetched | 30 | 28.85 | 48 ms | 2.9 ms (p95 8.1) | median 1, max 2 |

- HigherHRNet is capped at 10 a second by the sensor. Forcing a faster frame rate makes it worse: the sensor
  emits a tensor on about every fourth frame. Its keypoints come out on a 192x144 grid, 3.3 px steps at
  640x480; confidences in steps of 0.1; both ankles often the same point.
- PoseNet runs at the sensor's full 30 a second and keeps that rate with the 640x480 main frame fetched each
  request (which the arcade does, for the blobs and the motion grid). Its three output tensors are
  `[23, 31, 17]` heatmaps (log-odds), `[23, 31, 34]` short offsets (17 y then 17 x, input pixels) and
  `[23, 31, 64]` mid offsets (forward y, forward x, backward y, backward x, 16 edges each), on a 481x353 input,
  stride 16. picamera2 has no Python decoder for it; the spike's `posenet_decode.py` is a port of tfjs
  posenet's multi-pose decoding (local maxima, displacement traversal along the 16-edge chain, two offset
  refinements, root NMS at 20 px, instance score as the mean of unclaimed keypoint scores). On the saved
  tensors it finds one clear standing body per frame at score 0.73 to 0.89 (shoulders level, nose above
  ankles); on the Pi it costs 2.9 ms a frame. Duplicates come out at an instance score near 0 and go at the
  0.3 threshold.
- Shake, PoseNet, the best body's nose at 640x480: the standard deviation over one-second windows, median 8.2
  px across 24 seconds of people moving at the event, the stillest second 1.5 px. The wrist 9.5 px median.
  At the wall's 128 columns that is 1.6 px median, 0.3 px at rest, before the tracker's One Euro filter.
- Axis order: both models give (x, y) in the tensor's own columns: `XY_ORDER = (0, 1)` for HigherHRNet, and
  PoseNet's y-first layout as the decoder reads it. No swap at bring-up.
- For comparison: MediaPipe lite on the Pi was timed at 56 ms an inference (2026-09-30) and holds 15 captures
  a second with the wall's sender steady.

## Recommendation

PoseNet on the sensor, decoded by the ported decoder: 30 captures a second (double MediaPipe's 15, three
times HigherHRNet's 10), 48 ms from the sensor's timestamp to keypoints, and the Pi's CPU freed of inference
(3 ms a frame instead of 56). HigherHRNet is out. The open risk is keypoint quality: PoseNet is an older,
MobileNet-based model, and its wrists and ankles at 2 to 3 m may read worse than MediaPipe's; the first play
on the wall judges that, and the tracker's filter is tuned for MediaPipe's shake. The YOLO11n-pose export
(the spec's other candidate) needs Sony's converter on an x86 box and stays out unless PoseNet's quality fails.

The saved tensors (`posenet_raw.npz`, 30 samples, 9.8 MB) are in the spike's scratch and are the fixtures for
the decoder's tests (two samples, compressed).
