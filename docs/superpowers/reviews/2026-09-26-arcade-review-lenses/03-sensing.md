# Adversarial review, lens 3: sensing reality

Scope: the wall arcade spec sections 4 to 8 and plan Tasks 3, 8, 9, 15, 16, 17, 19, read against a night
at a regional burn: white floodlight, a sound camp in earshot, headlamps, art cars, flow toys, dust.
IMX500 claims were checked against the picamera2 source and the model zoo (sources at the end).
Munkres and the plan's blob and motion code were benchmarked on the Mac. No repo file was edited.

## Blockers

### B1. Pose dropouts reset dwell and exit, and the Pi source publishes a dropout as "nobody" (Tasks 19, 8, 9)

When `get_outputs()` returns `None`, `IMX500Camera.step()` sets `detections = []`. That happens on
any frame whose metadata has no `CnnOutputTensor`, and the tracker then publishes `()`. The frame
rate comes from `intrinsics.inference_rate` after `update_with_defaults()`, which defaults to 30.0
when the `.rpk` has no rate. Raspberry Pi's own HigherHRNet demo defaults to 10. A sensor running
faster than the network yields tensor-less frames, and bodies blink.

Blinks and one-frame wrist confidence dips break three things:

- **Menu dwell.** The cursor falls from the wrist to a blob or the body centre, `tile` changes, and
  `_held` resets. A one-second ring never fills if the wrist drops out every 300 ms.
- **Exit gesture.** `_exit_held` resets on any tick with no body or without both hands up.
- **Frogger.** A hop edge-triggered on `raised_wrist` fires twice when the wrist blinks mid-raise.

Fixes:

1. Set `FrameRate` to 10 explicitly. Raise it at bring-up only while the tensor-less frame count
   stays at zero.
2. When `outputs is None`, return `None` from `step()`. `ThreadedCamera` already keeps the last
   result in that case.
3. `BodyTracker` coasts a missed track for 300 ms and emits `seen_ago`.
4. Dwell and exit get a 250 ms grace period before they reset.
5. Tests: the menu launches when the wrist is missing every third tick. Exit fires when
   `both_hands_up` blinks false one tick in five.

### B2. A hung sensor looks live, and `Sensed` has no age (spec 5, 6; Tasks 16, 17)

`ThreadedCamera` handles a thread that raises (Review Focus 5) but not one that blocks. A CSI glitch
or an IMX500 firmware hang blocks `capture_request()`, and a webcam stall blocks `cap.read()`.
`latest()` then serves the last frame forever. A frozen wrist over a tile relaunches that game every
second. A frozen body with hands up exits every game after 1.5 s. Idle never triggers. When the USB
mic is unplugged, its callback stops and `level` freezes at the last 50 ms.

The missing timestamp also causes staleness. At 10 fps against a 30 Hz tick, two ticks in three
repeat the last frame. Any per-tick difference then reads 0, 0, 3x: nose velocity for jump take-off,
pong paddle speed, boid flee. Thresholds tuned on the Mac's 30 fps fire differently on the Pi. Dwell,
exit and peak-hold are time-based, so they only need the watchdog.

Fixes:

- `ThreadedCamera` stores `_latest_t` from the capture timestamp: `SensorTimestamp` on the Pi, the
  clock at `read()` on the Mac. Past 1.0 s old, `latest()` returns `EMPTY` and sets
  `available = False`. The audio source does the same 0.5 s after its last callback.
- `Sensed` gains `camera_t` (capture time on the runner clock), `camera_fresh` (true on the tick a
  new frame arrived), and `camera_seq`.
- `Body` gains `vx, vy` per second, filtered in the tracker from capture timestamps. Games never
  difference keypoints across ticks.
- Tests: a camera whose `step` blocks after one result, and an audio source whose callback stops,
  must both go `EMPTY` and unavailable within the timeout on a fake clock.

### B3. Bystanders and background lights own the input (spec 5, 7.2, 7.3; Tasks 8, 16, 19)

HigherHRNet is bottom-up. picamera2 returns up to 30 people anywhere in frame, so every passer-by
at 5 to 15 m becomes a `Body`.

- **Primary.** `primary` is the body with the highest mean keypoint confidence. A full-body
  passer-by at 6 m often beats a player at 2 m whose ankles are cropped. Cursor and exit gesture
  follow whoever wins that frame.
- **Close players are dropped.** picamera2's person score is the mean over all 17 joints, with
  missing joints counted as 0. `parse_higherhrnet` filters that score at 0.3. A close player with
  legs out of frame scores 10/17 of their visible confidence, below 0.3 at night.
- **Idle.** Idle needs no bodies and no blobs for 60 s. A 66-degree view at a burn at night always
  holds a headlamp, a bike light, an art car, or a passer-by, so attract never starts.
- **Attract exit.** Any body or blob returns to the menu, so attract flaps whenever anyone walks by.

Fixes:

- Calibrate a play zone (S5). Add `Body.in_zone` and `Body.scale`, the smoothed nose-to-mid-hip
  length.
- The runner derives two fields with hysteresis:
  - `Sensed.player` is the in-zone body with the largest scale. It stays until absent 0.5 s, or
    until another body is 1.3x larger for 1 s. It replaces `primary`.
  - `Sensed.present` turns true after an in-zone body or moving blob lasts 1 s, and false after
    3 s without one. Idle and attract exit read only `present`.
- Replace `min_score` with at least 5 of the 11 upper-body joints above 0.3.
- Tests use a `crowd(6)` actor behind a standing player. The player's id stays primary. A
  passer-by's raised hand never launches a game. Attract starts with crowd and headlamps outside
  the zone.

### B4. The audio features measure the sound camp, and `scream` cannot score (spec 5, 8; Task 17)

- **Scream.** Every scream reads exactly 1.0, because the gain rule
  `_ref = max(rms, 0.995 * _ref, floor)` has a 4.6 s half-life at 30 Hz. Any sound loudest in the
  last few seconds therefore reads `level = rms / _ref = 1.0`. Best of the night pegs on the first
  play. `peak` pegs too: it is the raw sample peak, and a mic gained for a quiet field clips on a
  scream.
- **Level.** An omni USB mic at the wall hears the camp's kick-heavy mix about as loud as a shout
  at 1 to 2 m. `level` pumps at the camp's tempo all night.
- **Onset.** The onset rule compares against the median of the last 0.67 s. At 125 bpm that median
  is the level between kicks. A sidechained dance mix at distance swings 4 to 10x in energy, so
  onset fires on most kicks. `flappy` flaps on every bass hit, and wind on the capsule adds more.
  `beat` locks to the camp, not the player.
- **Tempo lock.** It needs all seven intervals within 15 percent. One clap, one offbeat bass note,
  or one missed kick breaks it.

Fixes:

1. **Hardware.** A cardioid dynamic vocal mic on a gooseneck at mouth height, through a USB
   interface, with gain locked in `alsamixer` and a windscreen. A shout at 5 to 20 cm sits
   25 to 35 dB above the camp.
2. **Features.** Keep broadband `level` for ambient use and add these:
   - `voice_db`: absolute dBFS in the 300 Hz to 3.4 kHz band, with no automatic gain.
   - `floor_db`: the rolling 30 s 90th percentile of `voice_db`.
   - `voice`: `(voice_db - floor_db) / 30`, clamped to 0..1.
   - `clap`: a 2 to 6 kHz spectral-flux onset with crest factor above 4 and at least 12 dB over
     the floor.
   - A 512-point FFT per audio block computes all of these cheaply.
3. **Games.**
   - `scream` scores dB over the floor, and a new best needs at least 10 dB.
   - `flappy` flaps on `clap` or a voice onset, or on a downward arm flap using wrist `vy`.
   - `beat` becomes an ambient mode that visualizes the music in the air.
4. **Tests.** Feed raw samples into `AudioFeatures`: a 125 bpm 50 Hz kick plus pink noise gives
   zero claps over 20 s. Claps 12 dB over the floor are detected at least 90 percent of the time.

### B5. The Pi camera will not start, and its postprocess collapses in a crowd (Task 19)

`postprocess_highernet.py` imports `munkres` at module level. Raspberry Pi's AI Camera docs install
it as `python3-munkres`, and the plan's apt line omits it. The import sits inside `__init__`'s
`try`, so the first Pi day ends with "imx500 camera unavailable". Add `python3-munkres`.

Grouping runs pure-Python Munkres 16 times per frame on an n by n matrix, where n is the people in
view. Measured on one Mac core:

| People | Per call | Per frame | Pi 4 estimate |
|---|---|---|---|
| 6 | 0.09 ms | 1.5 ms | about 10 ms |
| 15 | 2.4 ms | 38 ms | 190 to 300 ms |
| 30 | 11.7 ms | 188 ms | 1 to 1.5 s |

A crowd behind the player drops the camera to 1 to 5 fps while it holds the GIL. Shim
`py_max_match` with `scipy.optimize.linear_sum_assignment` from apt `python3-scipy`, and truncate
each output tensor to the top 8 candidates per joint.

## Serious

### S1. Left and right are different hands on Mac and Pi (spec 5; Tasks 16, 19)

MediaPipe runs on the flipped frame, so it labels the mirrored figure: the player's real right hand
comes back as `LEFT_WRIST`. The IMX500 path mirrors x after inference, so the same hand is
`RIGHT_WRIST`. Positions agree and labels do not. `raised_wrist` hides this. `holewall`, puppet arm
colours, and any "right hand" prompt break on one platform.

Fix: run MediaPipe unflipped, and mirror x in one shared `mirror_keypoints()` without swapping
labels. Test: the same raised-right-hand fixture through both parsers returns `RIGHT_WRIST` at
x > 0.5.

### S2. BodyTracker fails on real crossings, and Review Focus 2 tests a fictional one (Task 16)

- **Anchor.** Ankles and knees drop out constantly at night. The box centre then jumps a quarter to
  half a body height, past `max_dist = 0.2`, and the body gets a new id. Ids are never reused, so
  pong's id-ordered players flip.
- **Matching.** Matching is greedy by confidence with no motion model. Same-depth people crossing in
  x swap ids whenever confidence reorders them.
- **Timeout.** `max_missed = 10` counts frames: 1 s on the Pi, 0.33 s on the Mac.
- **The test.** The test keeps tracks at y = 0.3 and y = 0.7. People on one floor share a centre y.
  In the real case they cross at equal y, and the rear person is fully hidden for 3 to 6 frames.
- **Dev coverage.** MediaPipe with `num_poses = 2` returns two of six people, so dev work never sees
  a crowd.

Fixes:

- Anchor on the shoulder midpoint, falling back to the nose, then the hips.
- Predict with constant velocity.
- Assign globally, costing distance plus a scale-difference term.
- Measure the timeout in seconds, at 0.5 s.
- Replace the test: two bodies at y = 0.55, heights 0.6 and 0.45, cross over 2 s. Only the front
  one is detected for 5 midpoint frames, confidence jitters by 0.1, and ankles drop out randomly.
  Ids hold. Pong assigns paddles by screen side.

### S3. At night the brightest pixels are faces, shirts and headlamps (spec 6.1; Task 15; `paint`)

Blobs threshold the max channel at the 99.5th percentile, floored at 200. With exposure set for
floodlit players, skin clears 200 in red and white clothing saturates. The percentile means about
0.5 percent of the frame always passes, so `paint` paints faces pink. Without the floodlight,
headlamps and art cars win. A glow stick's core saturates white, so its mean colour comes out
pastel. Blobs also feed idle (B3) and the menu's fallback cursor, which lets a headlamp steer the
menu.

Fixes:

- **Light-source test.** Keep pixels with V of at least 220 whose 3 px halo has HSV saturation of
  at least 0.5. Take the hue from the halo and emit it at full saturation.
- **Size cap.** Reject components over 0.5 percent of the frame.
- **Static mask.** Mask a blob that stays still for 5 s until it moves.
- **Zone.** Keep only blobs inside the play zone.
- **Menu.** Drop the blob fallback cursor while a body is present.

Cost: the spec says a low-resolution stream, but the plan uses the 640x480 main frame.
`find_blobs` measured 10.3 ms at 640x480 on the Mac, 4.3 ms of it `np.percentile`. At 160x120 it
measured 0.8 ms. The 640x480 figure means 50 to 80 ms on a Pi, inside a 100 ms frame budget. Use the
`lores` stream, and replace the per-blob full-frame mask mean with `cv2.mean` over the bounding box.

### S4. The motion grid sees exposure, flicker, noise and shake as motion (spec 5, 6.1; Task 15; `life`, `ambient`)

Measured with the plan's `motion_grid`, threshold 25 and fill 0.1:

- **Sensor noise.** Noise at sigma 12 on a static dark scene lit 83 percent of 64x64 cells. Sigma 8
  lit none. Night gain on a small sensor sits near that knee.
- **Shake.** A one-pixel shake lights every textured edge.
- **Auto-exposure.** A step of about 25 percent flashes every pixel above about 100.
- **Flicker.** LED floodlights on 60 Hz mains flicker at 120 Hz. With a rolling shutter that shows
  as bands, which drift on generator power.
- **Wind.** Tent walls in the beam and dust clouds move.

Life floods and ambient turns to noise. Idle does not use motion.

Fixes:

1. Lock exposure and white balance after a 3 s warm-up from metadata (`AeEnable`, `AwbEnable`
   false). Re-converge after 30 s without `present`.
2. Pin exposure to a multiple of 8333 µs, or use libcamera's `AeFlickerMode` if the image exposes
   it. Better, use a DC battery floodlight, checked with phone slow motion.
3. Blur 5x5 before differencing and set fill to 0.2.
4. When more than 35 percent of cells are set, emit an empty grid and count a "shake".
5. Crop the zone at the wall's aspect before downsampling. 4:3 squeezed into 128x32 squashes the
   vertical axis 3x.
6. Mount the camera on the wall frame, not on a pole.

### S5. Geometry: body x and nose y depend on distance, and nothing calibrates them (spec 2, 5, 8)

The AI Camera has a 78.3-degree diagonal field of view, about 66 by 52 degrees. The frame covers
about 1.3Z by 1.0Z at distance Z: 2.6 by 2.0 m at 2 m, 7.8 by 5.9 m at 6 m.

- **Framing.** Full body with arms up needs Z of at least 2.3 m. A 64 cm wall, or 32 cm stacked,
  draws people to 1 to 2 m. At 1.5 m the camera sees head to hips plus raised hands. That covers the
  menu, frogger, exit, pong, holewall and scream, but puppet loses legs and jump loses headroom.
- **Frogger.** Crossing all columns takes 2.6 m of walking at 2 m and 7.8 m at 6 m. The edge columns
  need the body half out of frame, so detection drops before the frog gets there.
- **Jump.** A 30 cm jump is 0.15 of frame height at 2 m and 0.05 at 6 m, so standing close triples
  the score. At 10 fps the peak error is only about 1 cm.

Proposal:

- **Placement.**
  - Camera under the wall's centre at about 1.3 m, level.
  - A "stand here" mat at 2 m.
  - Floodlight at 2.5 m or higher, 30 to 45 degrees off-axis, behind the camera plane, out of
    frame and out of players' eyes. Glare also dims a wall at 0.4 brightness.
- **`arcade calibrate`.** The wall shows the camera view while the operator:
  1. aims the camera;
  2. stands at the mat's two edges to set the zone;
  3. stands still to set the baseline scale;
  4. clears the frame for 10 s to capture the static-light mask and the audio floor;
  5. locks exposure.

  Results are saved to `data_dir/calibration.json`.
- **Mapping.** Sources map x into the zone once, like mirroring. Add `Sensed.zone`, `Body.scale` and
  `Body.in_zone`.
- **Game formulas.**
  - Jump height is `(baseline_nose_y - nose_y) / scale * 0.65 m`.
  - Frogger maps zone x from 0.1 to 0.9 onto the columns.
  - Test: column 0 is reachable at both 2 m and 6 m scale.

### S6. The Pi model is weaker and slower than the Mac's, and everything is tuned on the Mac (spec 2, 12; Tasks 16, 19)

- **HigherHRNet.** It is the model zoo's only pose model, with 288x384 input and COCO mAP 0.188
  quantized. The demo runs it at 10 fps.
- **PoseNet.** It runs through `rpicam-apps` JSON, but picamera2 has no Python decoder for it. The
  spec's open item is really "HigherHRNet, or write a decoder".
- **YOLO11n-pose.** Ultralytics exports it to IMX500, with about 62 ms per inference and a
  recommended 16 fps. Its published mAP is from the tiny coco8-pose set. Make the parser pluggable and
  try both models on the first Pi day.
- **Latency.** Sensor and tensor take 100 to 200 ms, plus a tick, plus the DDP frames from the
  2026-09-22 review. That is about 200 to 300 ms against about 100 ms on the Mac, so pong feels
  sluggish on the Pi.
- **Failure modes.** MediaPipe's BlazePose detects the face as a person proxy, and its model card
  covers a single person at 2 to 4 m, so goggles and bandanas defeat it. HigherHRNet ignores faces
  but loses wrists first. Dev testing exercises the wrong failure.

Add `tools/latency_probe.py`: the wall flashes a square that a mirror shows the camera, and the tool
counts pushes until the blob appears.

### S7. Dev-to-Pi gap: recordings cannot re-run the pipeline, actors are perfect, and the budget is loose (spec 6.3, 6.4, 9; Tasks 4, 12, 18, 20)

- **Recordings.** `record.py` stores post-tracker `Sensed` at 30 Hz with repeated frames. That
  cannot re-tune the tracker, blobs, motion or audio.
  - Add `--raw` capture, one record per camera frame: `t_capture`, raw detections, a 160x120 frame
    (about 10 MB per minute), and a 16 kHz WAV.
  - Add replay sources that run the real `FrameFeatures`, `BodyTracker` and `AudioFeatures` on it.
  - Record a backyard night before the event: the real floodlight, techno 30 m off, three people, a
    glow stick and a headlamp. Commit a clip as a fixture that asserts a stable primary id and no
    music flaps.
- **Actors.** Actors emit perfect 30 fps keypoints and ready-made `Audio`. Add
  `degrade(scene, fps=10, latency=0.15, keypoint_dropout=0.15, jitter=0.01)`, and the festival
  actors `crowd`, `headlamps`, `camp_kick`, `wind` and `shake`. The Task 20 soak also runs under
  `degrade`.
- **Budget.** 8 ms per game tick on the Mac becomes 40 to 64 ms on a Pi 4, over the 33 ms tick. Set
  3 ms with a documented `CPU_SCALE = 6`, and run `pytest -m perf` on the Pi on day one at 20 ms.

## Minor

- **Coordinates (Task 19).** picamera2 scales (x, y) by (H ratio, W ratio), which works only because
  both are 4:3. Its boxes are (y0, x0, y1, x1). Pass `img_size=(288, 384)`, normalize by (384, 288),
  never use its boxes, and assert that `ScalerCrop` covers the full sensor.
- **Close (Task 16).** `MediaPipeCamera.close()` releases the capture even when `join` timed out
  mid-`read()`. Release only after the thread exits. `IMX500Camera` never calls `picam2.close()`.
- **Audio device (Task 17).**
  - Log callback `status` overflows.
  - A denied macOS mic permission delivers pure zeros, so warn after 2 s of exact silence.
  - Add an `audio_device` config field matched by name. A systemd system service on Bookworm has no
    PipeWire session.
- **Audio timing (Task 17).** `AudioFeatures.latest()` advances its history once per call, so the
  gain decay and the median window depend on the tick rate. Define them in seconds and update per
  block.
- **Jump noise.** Keypoint jitter of 0.005 to 0.01 reads as a jump. Require a 0.1 scale rise over 2
  frames, and freeze the baseline while airborne.
- **Frogger hop.** Re-arm the hop only after the wrist has been down 300 ms.
- **Silent smoke runs (Tasks 16, 18).** Every source swallows setup errors and reports unavailable,
  so the live smoke test exits 0 with no camera. Add a `--require camera,mic` flag that exits
  non-zero when a named source is unavailable after 5 s. The loop-lens review covers the related
  mediapipe version and packaging facts.
- **Dust.** Fit a lens hood and wipe the lens nightly, because dusty glass under a floodlight veils
  the image.

## Checked and found OK

- IMX500 output is in COCO order. `match_by_tag` writes by COCO index, and `joint_order` only orders
  grouping. Missing joints come back as (0, 0) with score 0, which `Body` handles.
- The flat layout is (x, y, score), so `XY_ORDER = (0, 1)` is correct.
- `img_size` is (H, W), matching the demo.
- `RGB888` is BGR in memory, as the plan assumes.
- The binned 2028x1520 mode at 30 fps keeps the full field of view, so the main stream matches the
  default inference ROI.
- MediaPipe timestamps increase strictly, and out-of-range landmarks are cleaned (Review Focus 1).
- There is no deadlock: one lock per source, never nested.
- A raising `step` is handled, and hardware imports are lazy.

## Sources

- picamera2 `postprocess_highernet.py` and `imx500.py` on main, and the HigherHRNet demo at
  v0.3.30: https://github.com/raspberrypi/picamera2
- Model zoo: https://github.com/raspberrypi/imx500-models
- AI Camera docs, including `python3-munkres` and PoseNet:
  https://www.raspberrypi.com/documentation/accessories/ai-camera.html
- AI Camera specs (78.3 degrees, 2028x1520 at 30 fps): Raspberry Pi product page and reseller listings
- Ultralytics IMX500 export: https://docs.ultralytics.com/integrations/sony-imx500
- MediaPipe Pose Landmarker: https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker
- BlazePose model card:
  https://developers.google.com/static/ml-kit/images/vision/pose-detection/pose_model_card.pdf
- BlazePose paper: Bazarevsky et al. 2020, arXiv:2006.10204
- Benchmarks run on the Mac, 2026-09-26.

## Game inputs as designed

| Game | Input | Verdict |
|---|---|---|
| menu | raised wrist, blob fallback | needs change: zone, player hysteresis, dwell grace |
| paint | blobs | needs change: saturation, static mask, zone, locked exposure |
| puppet | bodies | OK |
| frogger | body x, raised wrist | needs change: zone-mapped x, hop debounce |
| pong | wrists or blobs | needs change: paddles by side, blobs only in zone |
| jump | nose y | needs change: torso normalization, headroom |
| holewall | keypoints | needs change: shared mirroring, upper-body scoring |
| life | motion, boxes | OK after the motion gate and blur |
| ambient | motion, wrists | OK |
| scream | audio level | unrealistic: near-field mic and voice-band dB, or cut |
| flappy | audio onset | unrealistic: flaps on the kick; use near-field clap or voice, or arm flap |
| beat | beat, bpm | unrealistic as a game: recast as an ambient mode |
