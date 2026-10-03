# Pose on the Sensor (IMX500 PoseNet source) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The arcade on the Pi reads bodies from PoseNet running on the AI Camera's IMX500 sensor at 30 captures a second, through the same pose camera pipeline the games already use.

**Architecture:** `MediaPipeCamera` becomes `PoseCamera`, keeping its whole pipeline (rate pacing, blobs, motion grid, record tap, duplicate merge, tracker) and taking a `PoseDetector` (frame and timestamp in, 17-COCO-keypoint bodies out). `MediaPipeDetector` wraps today's landmarker; `IMX500Pose` decodes the PoseNet tensor the `Picamera2Capture` now keeps from each request's metadata. `camera = "imx500"` in config builds the pair; the doctor gains an `imx500` probe; the runner logs capture age at push with `-v`.

**Tech Stack:** Python 3.12, numpy; picamera2 0.3.37 and imx500-all 1.13.0 from apt on the Pi (never imported at module import); pytest. No new dependency.

**Spec:** `docs/superpowers/specs/2026-10-02-pose-on-the-sensor-design.md` (and the spike it rests on, `docs/superpowers/reviews/2026-10-02-imx500-pose-spike.md`).

## Global Constraints

- Work in the worktree `/Users/trey/dev/codeisart-wall` on branch `wall-bringup` (the Pi has it checked out). First merge `main` (cd233b8, the spec) into it. Every path below is relative to that worktree.
- Python and pytest are the main checkout's venv run from the worktree: `/Users/trey/dev/codeisart/.venv/bin/python -m pytest ...` with the worktree as the working directory (verified: `arcade` then imports from the worktree). Below, `PY` stands for `/Users/trey/dev/codeisart/.venv/bin/python`.
- Nothing goes to the card and nothing runs on the Pi in this plan. The wall session (spec section 5) is the owner's, on his "go", after the code is on `wall-bringup`'s tip. promptviz keeps the wall until then.
- picamera2 and `picamera2.devices.imx500` are imported inside functions only; importing any `arcade` module must work on the Mac without them.
- The flash governor, the limiter, the driver, the tracker and its filter, the games and the lobby do not change.
- The 17 keypoints are COCO order: 0 nose, 1 left eye, 2 right eye, 3 left ear, 4 right ear, 5 left shoulder, 6 right shoulder, 7 left elbow, 8 right elbow, 9 left wrist, 10 right wrist, 11 left hip, 12 right hip, 13 left knee, 14 right knee, 15 left ankle, 16 right ankle. Coordinates are normalised to [0, 1] in the unmirrored frame; confidence in [0, 1].
- `camera_fps = 30` on the Pi; `camera = "imx500"`; `capture = "picamera2"` stays in `arcade.pi.toml`.
- The suite: each task runs its own test files on the Mac. The full suite runs once at the end, where the owner says (plan review I1): his rule of 2026-10-02 sends full suites to the Pi, but promptviz holds the Pi's wall tonight and he asked that nothing disturb it, so Task 8 asks him and does not assume. Under 540 s (Q102) wherever it runs. Memory rule: no parallel agents beyond two; this plan is executed inline.
- Commit messages in the repository's form (`feat(arcade): ...`, `test(arcade): ...`, `docs(...): ...`), ending with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

## Review Focus

1. **A frame whose metadata has no `CnnOutputTensor`** (every frame during the network upload, and a dropped tensor): the detector returns no bodies and the camera keeps running; the last result holds. Test in Task 3 (`test_detect_without_a_tensor_gives_no_bodies`).
2. **A tensor the decoder does not know** (a firmware or model-file change; `open_imx500` always loads posenet, so HigherHRNet from the spike is replaced, not met): the decoder raises `ValueError` naming the shapes, the detector logs it once and gives no bodies, and the camera thread lives. Tests in Task 3 (`test_wrong_shapes_raise_naming_them`, `test_a_bad_tensor_logs_once_and_gives_no_bodies`).
3. **Keypoints decoded outside the frame** (the displacement chain can walk off the map; the spike saw ankles at y 1.04): the decoder does not clip them, so `Body._clean` treats them as it treats MediaPipe's (clamped, confidence zeroed) and the tracker cannot tell the detectors apart. Test in Task 3 (`test_keypoints_off_the_frame_stay_raw_and_the_body_cleans_them`).
6. **A crowd in front of the wall** (the spike saw up to 10 people): the tracker's `assign()` has no scipy on the Pi and raises past 6 by 6, which would end the camera thread for good; the detector hands on at most four bodies, best first. Test in Task 3 (`test_at_most_max_bodies_reach_the_tracker_best_first`).
4. **A read that fails after the request was taken** (`make_array` raises): the request is still released, or the camera's buffers run out within a second. Test in Task 2 (`test_a_failed_read_releases_the_request`).
5. **`run --require camera` with `camera = "imx500"`**: the doctor must open the pair as the arcade does and say "uploading" rather than fail at 5 s on the first start after a power cycle. Test in Task 5 (`test_probe_imx500_says_uploading_and_waits`).

---

### Task 0: The worktree and the fixtures

**Files:**
- Create: `tests/arcade/fixtures/posenet/sample1.npz`, `tests/arcade/fixtures/posenet/sample2.npz`

**Interfaces:**
- Produces: two compressed npz files, each with arrays `heat` `[23, 31, 17]`, `off` `[23, 31, 34]`, `mid` `[23, 31, 64]` as float16 (exact: the sensor's values are 1-byte-origin floats). sample1 is the spike's `s1` (one body, nose near x 0.39, y 0.55), sample2 its `s4` (nose near x 0.42, y 0.57).

- [ ] **Step 1: Merge main into wall-bringup, and give the worktree the model file**

```bash
git -C /Users/trey/dev/codeisart-wall merge --no-edit main
git -C /Users/trey/dev/codeisart-wall log --oneline -1
ln -s /Users/trey/dev/codeisart/models /Users/trey/dev/codeisart-wall/models
ls /Users/trey/dev/codeisart-wall/models/
```
Expected: a merge commit with no conflict (main has two docs commits wall-bringup lacks, the spec and this plan; `git merge-tree --write-tree wall-bringup main` was clean); `git status --short` empty; `pose_landmarker_lite.task` listed. `models/` is gitignored, so the worktree had none and the one test that runs the real landmarker was skipping there (plan review I2).

- [ ] **Step 2: Write the fixtures from the spike's tensors**

```bash
cd /Users/trey/dev/codeisart-wall && mkdir -p tests/arcade/fixtures/posenet && /Users/trey/dev/codeisart/.venv/bin/python - <<'EOF'
import numpy as np
z = np.load("/private/tmp/claude-502/-Users-trey-dev-codeisart/4a6da117-d7ef-4393-8d0d-f7dfcc021216/scratchpad/posenet_raw.npz")
for name, s in (("sample1", "s1"), ("sample2", "s4")):
    heat, off, mid = (z[f"{s}_o{j}"] for j in range(3))
    for a in (heat, off, mid):
        assert np.array_equal(a.astype(np.float16).astype(np.float32), a)
    np.savez_compressed(f"tests/arcade/fixtures/posenet/{name}.npz", heat=heat.astype(np.float16),
                        off=off.astype(np.float16), mid=mid.astype(np.float16))
    print(name, heat.shape, off.shape, mid.shape)
EOF
ls -la tests/arcade/fixtures/posenet/
```
Expected: two files of about 75 KB each. (The scratchpad file exists as this plan is written; if it is gone, stop and ask the owner: the copy on the Pi is reached only with his word, since nothing in this plan touches the Pi.)

- [ ] **Step 3: Check git takes them**

```bash
cd /Users/trey/dev/codeisart-wall && git check-ignore -v tests/arcade/fixtures/posenet/sample1.npz; echo "exit $?"
```
Expected: `exit 1` (not ignored). If it prints a rule, add `!tests/arcade/fixtures/posenet/*.npz` after that rule in `.gitignore`.

- [ ] **Step 4: Commit**

```bash
cd /Users/trey/dev/codeisart-wall && git add tests/arcade/fixtures/posenet && git commit -q -m "test(arcade): two PoseNet tensor samples from the IMX500 spike as fixtures

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 1: `PoseDetector`, `MediaPipeDetector`, `PoseCamera`

**Files:**
- Modify: `arcade/sources/pose_mediapipe.py` (the class `MediaPipeCamera`, lines 140-222; add the protocol and the detector after `Landmarker`, line 108)
- Modify: `tests/arcade/test_pose_mediapipe.py` (the `camera()` helper, line 89-93; the three direct constructions at lines 217, 398, 416; add two tests)

**Interfaces:**
- Produces: `class PoseDetector(Protocol)` with `detect(self, bgr: np.ndarray, ts_ms: int) -> list[tuple[Keypoint, ...]]` and `close(self) -> None`; `class MediaPipeDetector(model_path: Path | None = None, landmarker=None)` implementing it; `class PoseCamera(cfg, size, clock=time.monotonic, *, calibration=None, model_path=None, capture=None, detector=None, start=True)`; `MediaPipeCamera = PoseCamera`. The unavailable log line reads `"%s camera unavailable: %s", cfg.camera, e`.
- Consumes: today's `Landmarker`, `landmarks_to_keypoints`, `open_capture`, `mirror_keypoints`, `merge_duplicates`, `box_of`, `BodyTracker`, `FrameFeatures`.

- [ ] **Step 1: Write the failing tests**

In `tests/arcade/test_pose_mediapipe.py`, change the import line 20 to also import `MediaPipeDetector` and `PoseCamera`:

```python
from arcade.sources.pose_mediapipe import MP_TO_COCO, MediaPipeCamera, MediaPipeDetector, PoseCamera, box_of, landmarks_to_keypoints
```

Change the `camera()` helper (line 89-93) to build the camera through a detector:

```python
def camera(people=(), clock=None, dt=0.1, mirror=True, fps=10, frames=None, make=None, **kw):
    clock = clock or FakeClock()
    cfg = ArcadeConfig(camera_fps=fps, mirror=mirror, camera="mediapipe")
    cap, lmk = FakeCapture(clock, dt, frames, make), FakeLandmarker(people)
    cam = PoseCamera(cfg, cfg.size, clock=clock, capture=cap, detector=MediaPipeDetector(landmarker=lmk), start=False, **kw)
    return cam, cap, lmk, clock
```

At line 217 replace `landmarker=Lmk()` with `detector=MediaPipeDetector(landmarker=Lmk())`; at lines 398 and 416 replace `landmarker=FakeLandmarker()` with `detector=MediaPipeDetector(landmarker=FakeLandmarker())`.

Add at the end of the file:

```python
def test_mediapipe_detector_gives_17_keypoints_per_person_from_the_bgr_frame():
    lmk = FakeLandmarker([fake_landmarks(), fake_landmarks(right_hand_up=True)])
    det = MediaPipeDetector(landmarker=lmk)
    frame = np.zeros((48, 64, 3), np.uint8)
    frame[..., 0] = 200                                   # BGR: blue
    people = det.detect(frame, 1234)
    assert len(people) == 2 and all(len(p) == 17 for p in people)
    assert people[0] == landmarks_to_keypoints(fake_landmarks())
    assert lmk.calls == [((48, 64, 3), 1234)] and lmk.pixel == (0, 0, 200)   # the landmarker saw RGB
    det.close()
    assert lmk.closed


def test_mediapipe_detector_without_the_model_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="pose model missing"):
        MediaPipeDetector(tmp_path / "missing.task")


def test_the_old_name_is_the_new_class():
    assert MediaPipeCamera is PoseCamera
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd /Users/trey/dev/codeisart-wall && PY=/Users/trey/dev/codeisart/.venv/bin/python; $PY -m pytest tests/arcade/test_pose_mediapipe.py -q -x 2>&1 | tail -3
```
Expected: FAIL at import, `ImportError: cannot import name 'MediaPipeDetector'`.

- [ ] **Step 3: Implement**

In `arcade/sources/pose_mediapipe.py`, add `Protocol` to the typing import:

```python
from typing import TYPE_CHECKING, Callable, Protocol, Sequence
```

After the `Landmarker` class (after line 108) add:

```python
class PoseDetector(Protocol):
    """What PoseCamera runs on a due frame: detect(bgr, ts_ms) gives each person's 17 COCO keypoints, normalised
    to the unmirrored frame (x, y in [0, 1], conf in [0, 1]); ts_ms increases strictly from call to call. close()
    frees the model."""

    def detect(self, bgr: np.ndarray, ts_ms: int) -> list[tuple[Keypoint, ...]]: ...

    def close(self) -> None: ...


class MediaPipeDetector:
    """The PoseDetector over MediaPipe's Landmarker (the Mac, and the Pi's CPU fallback): the BGR frame goes in as
    RGB, each person's 33 landmarks come back as the 17 COCO keypoints. landmarker is injectable; without one
    the model file is checked (FileNotFoundError) and a Landmarker opened."""

    def __init__(self, model_path: Path | None = None, landmarker=None):
        if landmarker is None:
            if model_path is None or not Path(model_path).exists():
                raise FileNotFoundError(f"pose model missing at {model_path}")
            landmarker = Landmarker(Path(model_path))
        self._landmarker = landmarker

    def detect(self, bgr: np.ndarray, ts_ms: int) -> list[tuple[Keypoint, ...]]:
        return [landmarks_to_keypoints(lm) for lm in self._landmarker.detect(bgr[:, :, ::-1], ts_ms)]   # BGR to RGB

    def close(self) -> None:
        self._landmarker.close()
```

Rename the class and change its constructor and `step` (the whole class `MediaPipeCamera`, lines 140-222, becomes):

```python
class PoseCamera(ThreadedCamera):
    """Reads every frame the capture gives (so its buffer never holds an old one), stamps it with clock() in
    seconds as the read returns, and runs the frames due at cfg.camera_fps through the detector; the others return
    None and the last result holds. A due frame also goes through features (FrameFeatures: blobs and the motion
    grid), so it provides every camera input (C35).

    size is the wall size, the motion grid's; calibration is the body tracker's and the features'; model_path None
    is the doctor's arcade.main.MODEL_PATH (the MediaPipe detector's). capture (read() -> (ok, bgr), release())
    and detector (a PoseDetector) are injectable; without them a MediaPipeDetector on the model file and the
    capture cfg.capture names open here, on the calling (main) thread. A failure logs once and leaves the camera
    unavailable (latest() None); there is no 30 s retry yet. The imx500 source hands in both (pose_imx500.open_imx500).

    tap (record --raw's, set and cleared by the recording from its thread): when set, each due capture also calls
    it on the camera's thread with a RawRecord of the capture time, the detections (merged and mirrored, before
    the tracker) and the working frame in grey, unflipped, at FRAME_SHAPE; no samples (no audio, Q99)."""

    provides = CAMERA_INPUTS

    def __init__(self, cfg, size: tuple[int, int], clock: Callable[[], float] = time.monotonic, *,
                 calibration: Calibration | None = None, model_path: Path | None = None, capture=None,
                 detector: PoseDetector | None = None, start: bool = True):
        from arcade.sources.blobs import FrameFeatures   # here: blobs imports cv2, and importing us must not

        super().__init__(clock=clock)
        self.size, self.mirror = size, cfg.mirror
        self.period = 1.0 / cfg.camera_fps
        self.tracker = BodyTracker(calibration)
        self.features: FrameFeatures = FrameFeatures(size, calibration, mirror=cfg.mirror)
        self.tap: Callable[[RawRecord], None] | None = None
        self._cap, self._detector = capture, detector
        self._next_due: float | None = None
        self._last_ts = -1
        if model_path is None:
            from arcade.main import MODEL_PATH as model_path   # here: arcade.main will import the sources (X2)
        try:
            if self._detector is None:
                self._detector = MediaPipeDetector(Path(model_path))
            if self._cap is None:
                self._cap = open_capture(cfg.camera_index, cfg.capture)
        except Exception as e:
            log.warning("%s camera unavailable: %s", cfg.camera, e)
            return
        if start:
            self.start()

    def _due(self, capture_t: float) -> bool:
        if self._next_due is None or capture_t - self._next_due > self.period:
            self._next_due = capture_t + self.period       # first frame, or fallen a period behind: restart
            return True
        if capture_t >= self._next_due - EARLY * self.period:
            self._next_due += self.period
            return True
        return False

    def step(self) -> CameraResult | None:
        ok, frame = self._cap.read()
        capture_t = float(self.clock())
        if not ok or frame is None:
            raise RuntimeError("camera read failed")
        if not self._due(capture_t):
            return None
        ts = max(self._last_ts + 1, int(round(capture_t * 1000)))
        self._last_ts = ts
        detections = []
        for kps in self._detector.detect(frame, ts):
            if self.mirror:
                kps = mirror_keypoints(kps)
            detections.append((box_of(kps), kps))
        merged = merge_duplicates(detections)
        blobs, motion = self.features.update(frame, capture_t)
        tap = self.tap                                                       # read once: the recording clears it
        if tap is not None:
            tap(RawRecord(capture_t, detections=tuple(merged), frame=raw_frame(self.features.gray)))
        return (capture_t, self.tracker.update(merged, capture_t), blobs, motion)

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
        if self._detector is not None:
            self._detector.close()


MediaPipeCamera = PoseCamera   # the name the tests, the doctor and the README knew
```

Update the module docstring's first line to: `"""The pose camera (spec 6.1): a capture at 640 by 480 and a PoseDetector (MediaPipe's Pose Landmarker in VIDEO mode, num_poses 2, on the Mac; pose_imx500.IMX500Pose on the Pi) on the unflipped frame; mirror_keypoints flips x once afterwards when cfg.mirror. ...` keeping the rest.

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd /Users/trey/dev/codeisart-wall && PY=/Users/trey/dev/codeisart/.venv/bin/python; $PY -m pytest tests/arcade/test_pose_mediapipe.py tests/arcade/test_sources.py tests/arcade/test_record.py tests/arcade/test_calibrate.py -q 2>&1 | tail -3
```
Expected: all pass. (`test_without_picamera2_the_camera_is_unavailable_and_says_so` still finds "mediapipe camera unavailable": `cfg.camera` is `mediapipe` there.)

- [ ] **Step 5: Commit**

```bash
cd /Users/trey/dev/codeisart-wall && git add arcade/sources/pose_mediapipe.py tests/arcade/test_pose_mediapipe.py && git commit -q -m "feat(arcade): PoseCamera takes a PoseDetector; MediaPipeDetector wraps the landmarker

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: `Picamera2Capture` keeps its request metadata

**Files:**
- Modify: `arcade/sources/capture_picamera2.py` (whole file, 60 lines)
- Modify: `tests/arcade/test_capture_picamera2.py` (`FakeCam`, the first test; add three tests)

**Interfaces:**
- Produces: `Picamera2Capture(size, index=0, camera=None, frame_rate=FRAME_RATE, buffer_count=None)`; `read() -> (ok, bgr)` sets `self.metadata: dict` to the request's metadata (`{}` before the first read and after a failed one); `release()` as before. `FRAME_RATE = 30` stands.
- Consumes: picamera2's `capture_request(wait=)`, `request.get_metadata()`, `request.make_array("main")`, `request.release()`.

- [ ] **Step 1: Write the failing tests**

Replace `FakeCam.capture_array` in `tests/arcade/test_capture_picamera2.py` with a request fake, and give `create_video_configuration` a `buffer_count` keyword:

```python
class FakeRequest:
    def __init__(self, cam, fail_array=False):
        self.cam, self.fail_array, self.released = cam, fail_array, False

    def get_metadata(self):
        return {"SensorTimestamp": 123456789, "CnnOutputTensor": [1.0, 2.0]}

    def make_array(self, name):
        if self.fail_array:
            raise RuntimeError("buffer gone")
        self.cam.calls.append(("capture", name))
        return self.cam.frame

    def release(self):
        self.released = True


class FakeCam:
    def __init__(self, given=None, fail_read=False, fail_stop=False, fail_array=False):
        self.calls, self.given, self.fail_read, self.fail_stop = [], given, fail_read, fail_stop
        self.fail_array, self.requests = fail_array, []
        self.frame = np.zeros((480, 640, 3), np.uint8)
        self.frame[..., 0] = 200

    def create_video_configuration(self, main, controls, buffer_count=None):
        self.calls.append(("create", dict(main), dict(controls)) + ((buffer_count,) if buffer_count else ()))
        return {"main": dict(main), "controls": dict(controls)}

    def configure(self, config):
        self.calls.append("configure")
        self.config = config

    def camera_configuration(self):
        return {"main": self.given or self.config["main"]}

    def start(self):
        self.calls.append("start")

    def capture_request(self, wait=None):
        self.waits = getattr(self, "waits", []) + [wait]
        if self.fail_read:
            raise TimeoutError("no frame")
        self.requests.append(FakeRequest(self, self.fail_array))
        return self.requests[-1]

    def stop(self):
        self.calls.append("stop")
        if self.fail_stop:
            raise RuntimeError("already stopped")

    def close(self):
        self.calls.append("close")
```

Keep the first test as it is (its `calls` assertion still holds: no `buffer_count` given, so the create tuple has three members). Add:

```python
def test_read_keeps_the_requests_metadata_and_releases_the_request():
    cam = FakeCam()
    cap = Picamera2Capture((640, 480), camera=cam)
    assert cap.metadata == {}
    ok, frame = cap.read()
    assert ok and cap.metadata["CnnOutputTensor"] == [1.0, 2.0] and cap.metadata["SensorTimestamp"] == 123456789
    assert cam.requests[0].released and cam.waits == [READ_TIMEOUT]


def test_a_failed_read_releases_the_request():
    cam = FakeCam(fail_array=True)
    cap = Picamera2Capture((640, 480), camera=cam)
    ok, frame = cap.read()
    assert (ok, frame) == (False, None) and cap.metadata == {} and cam.requests[0].released


def test_frame_rate_and_buffer_count_reach_the_configuration():
    cam = FakeCam()
    Picamera2Capture((640, 480), camera=cam, frame_rate=30.0, buffer_count=12)
    assert cam.calls[0] == ("create", {"size": (640, 480), "format": FORMAT}, {"FrameRate": 30.0}, 12)
```

Check the existing failed-read test (search `fail_read=True` in the file): it asserts `(False, None)` on a `TimeoutError` from the camera; it stands, since `capture_request` raises the same way.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd /Users/trey/dev/codeisart-wall && PY=/Users/trey/dev/codeisart/.venv/bin/python; $PY -m pytest tests/arcade/test_capture_picamera2.py -q 2>&1 | tail -4
```
Expected: the first test fails with `AttributeError: 'FakeCam' object has no attribute 'capture_array'`; the new ones fail on `metadata` / the `buffer_count` keyword.

- [ ] **Step 3: Implement**

`arcade/sources/capture_picamera2.py` becomes:

```python
"""The Pi's ribbon cameras as PoseCamera's capture (cfg.capture "picamera2", and the imx500 source's capture):
picamera2 frames in OpenCV's layout, with each frame's request metadata kept (the IMX500's output tensor rides in
it as "CnnOutputTensor")."""
from __future__ import annotations

import logging

FORMAT = "RGB888"     # picamera2's name for 24-bit pixels laid out [B, G, R] in memory: OpenCV's BGR
FRAME_RATE = 30
READ_TIMEOUT = 2.0    # s a read waits for a frame: without it a camera whose frames stop blocks its reader for good

log = logging.getLogger("arcade")


class Picamera2Capture:
    """read() -> (ok, bgr) at size, waiting at most READ_TIMEOUT for the camera's next frame, and sets metadata to
    that frame's request metadata ({} before the first read and after a failed one); release() stops and closes
    the camera, once, and never raises.

    camera (a picamera2.Picamera2-like object) is injectable; without one picamera2 is imported and
    Picamera2(index) opened here (RuntimeError with the ribbon hint when no camera answers). frame_rate is the
    stream's FrameRate control (the IMX500 source passes its model's inference rate); buffer_count, when given, the
    stream's buffers (the IMX500 demo uses 12). RuntimeError, with the camera closed, when it does not give size
    and FORMAT."""

    def __init__(self, size: tuple[int, int], index: int = 0, camera=None, frame_rate: float = FRAME_RATE,
                 buffer_count: int | None = None):
        if camera is None:
            from picamera2 import Picamera2   # here: apt's package, on the Pi only

            try:
                camera = Picamera2(index)
            except Exception as e:
                raise RuntimeError(f"picamera2 found no camera {index} (is the ribbon seated: rpicam-hello "
                                   f"--list-cameras): {e!r}") from e
        self._cam, self._released = camera, False
        self.metadata: dict = {}
        try:
            extra = {"buffer_count": buffer_count} if buffer_count else {}
            camera.configure(camera.create_video_configuration(main={"size": size, "format": FORMAT},
                                                                controls={"FrameRate": frame_rate}, **extra))
            got = camera.camera_configuration()["main"]
            if tuple(got["size"]) != tuple(size) or got["format"] != FORMAT:
                raise RuntimeError(f"picamera2 gave {tuple(got['size'])} {got['format']}, not {tuple(size)} {FORMAT}")
            camera.start()
        except Exception:
            self.release()
            raise

    def read(self):
        try:
            request = self._cam.capture_request(wait=READ_TIMEOUT)
        except Exception as e:
            log.warning("picamera2 read failed: %r", e)
            self.metadata = {}
            return False, None
        try:
            metadata = request.get_metadata()
            frame = request.make_array("main")
        except Exception as e:
            log.warning("picamera2 read failed: %r", e)
            self.metadata = {}
            return False, None
        finally:
            request.release()
        self.metadata = metadata
        return True, frame

    def release(self) -> None:
        if self._released:
            return
        self._released = True
        for call in (self._cam.stop, self._cam.close):
            try:
                call()
            except Exception:
                log.exception("picamera2 %s failed", call.__name__)
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd /Users/trey/dev/codeisart-wall && PY=/Users/trey/dev/codeisart/.venv/bin/python; $PY -m pytest tests/arcade/test_capture_picamera2.py tests/arcade/test_doctor.py -q 2>&1 | tail -3
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/trey/dev/codeisart-wall && git add arcade/sources/capture_picamera2.py tests/arcade/test_capture_picamera2.py && git commit -q -m "feat(arcade): Picamera2Capture reads by request and keeps the frame's metadata; frame_rate and buffer_count

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: `pose_imx500`: the PoseNet decoder, `IMX500Pose`, `open_imx500`

**Files:**
- Create: `arcade/sources/pose_imx500.py`
- Test: `tests/arcade/test_pose_imx500.py`

**Interfaces:**
- Consumes: `Keypoint` (`arcade.sensed`), `Picamera2Capture(size, camera=, frame_rate=, buffer_count=)` with `.metadata` (Task 2), `CAPTURE_SIZE` (`arcade.sources.pose_mediapipe`), the fixtures (Task 0).
- Produces: `MODEL = "/usr/share/imx500-models/imx500_network_posenet.rpk"`; `INPUT_SIZE = (481, 353)`; `SHAPES = ((23, 31, 17), (23, 31, 34), (23, 31, 64))`; `MIN_INSTANCE = 0.3`; `MAX_BODIES = 4`; `decode_multiple(outputs, score_thr=0.3, max_poses=10, nms_radius_px=20.0) -> list[tuple[float, list[tuple[float, float, float]]]]` (instance score, 17 (x, y, conf) normalised to the input, not clipped, best first); `class IMX500Pose(capture, imx, min_instance=MIN_INSTANCE, max_bodies=MAX_BODIES)` with `detect(bgr, ts_ms) -> list[tuple[Keypoint, ...]]`, `close()` and the property `imx`; `open_imx500(cfg, size) -> tuple[Picamera2Capture, IMX500Pose]`; `describe(imx) -> str` ("posenet 30/s").

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_pose_imx500.py`:

```python
"""The IMX500 PoseNet source: the decoder on two tensor samples from the spike (2026-10-02, the event wall), the
detector against fakes, and the opener without picamera2. No camera and no picamera2 here."""
import sys
from pathlib import Path

import numpy as np
import pytest

from arcade.sensed import LEFT_ANKLE, LEFT_SHOULDER, NOSE, RIGHT_ANKLE, RIGHT_SHOULDER, Keypoint
from arcade.sources.pose_imx500 import INPUT_SIZE, MODEL, SHAPES, IMX500Pose, decode_multiple, describe, open_imx500

FIXTURES = Path(__file__).parent / "fixtures" / "posenet"


def sample(name):
    z = np.load(FIXTURES / f"{name}.npz")
    return [z["heat"].astype(np.float32), z["off"].astype(np.float32), z["mid"].astype(np.float32)]


@pytest.mark.parametrize("name, nose", [("sample1", (0.39, 0.55)), ("sample2", (0.42, 0.57))])
def test_decodes_one_standing_body_where_the_spike_saw_it(name, nose):
    poses = decode_multiple(sample(name))
    assert poses and poses[0][0] > 0.7                      # the best body first, a clear one
    score, pts = poses[0]
    assert len(pts) == 17 and all(0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 and 0.0 <= c <= 1.0 for x, y, c in pts)
    assert pts[NOSE][0] == pytest.approx(nose[0], abs=0.03) and pts[NOSE][1] == pytest.approx(nose[1], abs=0.03)
    assert abs(pts[LEFT_SHOULDER][1] - pts[RIGHT_SHOULDER][1]) < 0.02        # level shoulders
    assert pts[LEFT_SHOULDER][0] > pts[RIGHT_SHOULDER][0]                    # facing the camera, unmirrored
    assert pts[NOSE][1] < pts[LEFT_ANKLE][1] and pts[NOSE][1] < pts[RIGHT_ANKLE][1]
    assert sum(1 for p in poses if p[0] > 0.3) <= 2    # the first body and, in 27 of the spike's 30 samples, a
                                                        # second one at 0.33 to 0.72 about 0.1 away (a bystander at
                                                        # the event, most likely); same-root duplicates score near 0


def test_keypoints_off_the_frame_stay_raw_and_the_body_cleans_them():
    """The decoder does not clip: an ankle decoded past the frame reaches Body as MediaPipe's would, and Body's
    _clean clamps it and zeroes its confidence, so the tracker sees the same thing from either detector."""
    from arcade.sensed import Body

    heat, off, mid = sample("sample1")
    off = off + 400.0                                        # every offset pushed far past the input
    poses = decode_multiple([heat, off, mid])
    assert poses and any(x > 1.0 or y > 1.0 for x, y, _ in poses[0][1])
    kps = tuple(Keypoint(x, y, c) for x, y, c in poses[0][1])
    body = Body(1, (0.0, 0.0, 1.0, 1.0), kps)
    assert all(0.0 <= k.x <= 1.0 and 0.0 <= k.y <= 1.0 for k in body.keypoints)
    assert all(k.conf == 0.0 for k, raw in zip(body.keypoints, kps) if raw.x > 1.0 or raw.y > 1.0)


def test_a_cold_heatmap_gives_no_body():
    """Log-odds: a zero heatmap is sigmoid 0.5 everywhere (every cell a root); a cold one is no body."""
    heat = np.full(SHAPES[0], -20.0, np.float32)
    assert decode_multiple([heat, np.zeros(SHAPES[1], np.float32), np.zeros(SHAPES[2], np.float32)]) == []


def test_wrong_shapes_raise_naming_them():
    with pytest.raises(ValueError, match=r"\(1, 30, 17\)"):
        decode_multiple([np.zeros((1, 30, 17), np.float32), np.zeros((1, 30, 17), np.float32),
                         np.zeros((1, 30, 17), np.float32)])
    with pytest.raises(ValueError, match="3 tensors"):
        decode_multiple([np.zeros(SHAPES[0], np.float32)])


class FakeCapture:
    def __init__(self, metadata):
        self.metadata = metadata


class FakeIMX:
    def __init__(self, outputs):
        self.outputs, self.calls = outputs, []

    def get_outputs(self, metadata, add_batch=False):
        self.calls.append(add_batch)
        return self.outputs if metadata.get("CnnOutputTensor") else None


def test_detect_decodes_the_captures_metadata_into_keypoints():
    cap = FakeCapture({"CnnOutputTensor": [0.5] * 10, "SensorTimestamp": 1})
    det = IMX500Pose(cap, FakeIMX(sample("sample1")))
    people = det.detect(np.zeros((480, 640, 3), np.uint8), 1000)
    assert 1 <= len(people) <= 2 and all(len(p) == 17 and all(isinstance(k, Keypoint) for k in p) for p in people)
    best = people[0]
    assert best[NOSE].x == pytest.approx(0.39, abs=0.03) and best[NOSE].conf > 0.3
    det.close()


def test_detect_without_a_tensor_gives_no_bodies():
    imx = FakeIMX(sample("sample1"))
    det = IMX500Pose(FakeCapture({"SensorTimestamp": 1}), imx)
    assert det.detect(np.zeros((480, 640, 3), np.uint8), 1000) == [] and imx.calls == []
    assert IMX500Pose(FakeCapture({}), imx).detect(np.zeros((480, 640, 3), np.uint8), 1001) == []


def test_bodies_under_min_instance_are_dropped():
    det = IMX500Pose(FakeCapture({"CnnOutputTensor": [1.0]}), FakeIMX(sample("sample1")), min_instance=0.99)
    assert det.detect(np.zeros((480, 640, 3), np.uint8), 1000) == []


def test_at_most_max_bodies_reach_the_tracker_best_first():
    """The tracker's assign() has no scipy on the Pi and stops at 6x6: a crowd must not kill the camera thread."""
    from arcade.sources.pose_imx500 import MAX_BODIES

    assert len(decode_multiple(sample("sample1"))) > MAX_BODIES                   # the raw decode gives more
    det = IMX500Pose(FakeCapture({"CnnOutputTensor": [1.0]}), FakeIMX(sample("sample1")), min_instance=0.0)
    people = det.detect(np.zeros((480, 640, 3), np.uint8), 1000)
    assert len(people) == MAX_BODIES == 4
    assert people[0][NOSE].x == pytest.approx(0.39, abs=0.03)                     # the best body first


def test_a_bad_tensor_logs_once_and_gives_no_bodies(caplog):
    det = IMX500Pose(FakeCapture({"CnnOutputTensor": [1.0]}),
                     FakeIMX([np.zeros((1, 30, 17), np.float32)] * 3))
    frame = np.zeros((480, 640, 3), np.uint8)
    assert det.detect(frame, 1000) == [] and det.detect(frame, 1001) == []
    assert caplog.text.count("not posenet's tensors") == 1


def test_open_imx500_without_picamera2_raises(monkeypatch):
    from arcade.config import ArcadeConfig

    monkeypatch.setitem(sys.modules, "picamera2", None)
    with pytest.raises(ImportError):
        open_imx500(ArcadeConfig(camera="imx500"), (128, 64))


def test_describe_names_the_model_and_its_rate():
    class Intrinsics:
        inference_rate = 30

    class IMX:
        network_intrinsics = Intrinsics()

    assert describe(IMX()) == "posenet 30/s"
    assert MODEL.endswith("imx500_network_posenet.rpk") and INPUT_SIZE == (481, 353)
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd /Users/trey/dev/codeisart-wall && PY=/Users/trey/dev/codeisart/.venv/bin/python; $PY -m pytest tests/arcade/test_pose_imx500.py -q 2>&1 | tail -3
```
Expected: `ModuleNotFoundError: No module named 'arcade.sources.pose_imx500'`.

- [ ] **Step 3: Implement**

`arcade/sources/pose_imx500.py`:

```python
"""The Pi's AI Camera (IMX500) as the pose source: PoseNet runs on the sensor, the Pi decodes its three output
tensors into bodies (spec 6.1 as amended by docs/superpowers/specs/2026-10-02-pose-on-the-sensor-design.md).

The decoder is a port of tfjs posenet's multi-pose decoding (decodeMultiplePoses), written against the tensors the
rpicam-apps imx500_posenet stage documents: heatmaps [23, 31, 17] as log-odds, short offsets [23, 31, 34] (17 y
then 17 x, in input pixels), mid offsets [23, 31, 64] (forward y, forward x, backward y, backward x; 16 edges
each), on a 481x353 input with stride 16. Measured on the spike of 2026-10-02 (the review of that date): 30
tensors a second, 3 ms to decode on the Pi. picamera2 is imported inside open_imx500 only."""
from __future__ import annotations

import logging

import numpy as np

from arcade.sensed import Keypoint

log = logging.getLogger("arcade")

MODEL = "/usr/share/imx500-models/imx500_network_posenet.rpk"
INPUT_SIZE = (481, 353)                   # the network's input, w x h; coordinates are normalised by it
STRIDE = 16
SHAPES = ((23, 31, 17), (23, 31, 34), (23, 31, 64))
NUM_KP = 17
BUFFER_COUNT = 12                         # picamera2's IMX500 demos run with 12 buffers
# parent -> child, tfjs posenet's poseChain (COCO indices)
EDGES = ((0, 1), (1, 3), (0, 2), (2, 4), (0, 5), (5, 7), (7, 9), (5, 11), (11, 13), (13, 15),
         (0, 6), (6, 8), (8, 10), (6, 12), (12, 14), (14, 16))
NUM_EDGES = len(EDGES)
LOCAL_MAX_RADIUS = 1                      # heatmap cells: a root is the maximum of its 3x3 neighbourhood
REFINE_STEPS = 2                          # offset refinements after a displacement step (tfjs: 2)
MIN_INSTANCE = 0.3                        # a body's instance score (mean keypoint score) to count; 0.5 clears
                                          # most second bodies in the spike's samples (the knob if ghosts appear)
MAX_BODIES = 4                            # bodies handed to the tracker a capture (assign() without scipy: 6 at most)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _check(outputs) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    arrs = [np.asarray(o, dtype=np.float32) for o in outputs]
    if len(arrs) != 3:
        raise ValueError(f"posenet gives 3 tensors, got {len(arrs)}")
    shapes = tuple(tuple(int(d) for d in a.shape) for a in arrs)
    if shapes != SHAPES:
        raise ValueError(f"not posenet's tensors: shapes {shapes}, wanted {SHAPES} (the sensor's firmware or model "
                         f"file is not the posenet this decoder knows)")
    return arrs[0], arrs[1], arrs[2]


def _local_maxima(scores: np.ndarray, thr: float) -> list[tuple[float, int, int, int]]:
    """(score, keypoint, row, col) of every cell at or above thr that is the maximum of its neighbourhood, best first."""
    h, w, _ = scores.shape
    out = []
    for kp in range(NUM_KP):
        s = scores[:, :, kp]
        for y, x in zip(*np.where(s >= thr)):
            y0, y1 = max(0, y - LOCAL_MAX_RADIUS), min(h, y + LOCAL_MAX_RADIUS + 1)
            x0, x1 = max(0, x - LOCAL_MAX_RADIUS), min(w, x + LOCAL_MAX_RADIUS + 1)
            if s[y, x] >= s[y0:y1, x0:x1].max():
                out.append((float(s[y, x]), kp, int(y), int(x)))
    out.sort(reverse=True)
    return out


def _coords(kp: int, y: int, x: int, off: np.ndarray) -> np.ndarray:
    """A keypoint's (y, x) in input pixels from its heatmap cell and the short offsets."""
    return np.array([y * STRIDE + off[y, x, kp], x * STRIDE + off[y, x, kp + NUM_KP]], dtype=np.float32)


def _cell(pos: np.ndarray, h: int, w: int) -> tuple[int, int]:
    return (int(np.clip(round(pos[0] / STRIDE), 0, h - 1)), int(np.clip(round(pos[1] / STRIDE), 0, w - 1)))


def _traverse(edge: int, src: np.ndarray, target: int, scores, off, disp) -> tuple[float, np.ndarray]:
    h, w, _ = scores.shape
    y, x = _cell(src, h, w)
    pos = src + np.array([disp[y, x, edge], disp[y, x, edge + NUM_EDGES]], dtype=np.float32)
    for _ in range(REFINE_STEPS):
        pos = _coords(target, *_cell(pos, h, w), off)
    ty, tx = _cell(pos, h, w)
    return float(scores[ty, tx, target]), pos


def _decode_pose(root, scores, off, fwd, bwd) -> tuple[np.ndarray, np.ndarray]:
    score, kp, y, x = root
    kps = np.zeros((NUM_KP, 2), dtype=np.float32)
    ksc = np.zeros(NUM_KP, dtype=np.float32)
    kps[kp], ksc[kp] = _coords(kp, y, x, off), score
    for e in reversed(range(NUM_EDGES)):
        parent, child = EDGES[e]
        if ksc[child] > 0 and ksc[parent] == 0:
            ksc[parent], kps[parent] = _traverse(e, kps[child], parent, scores, off, bwd)
    for e in range(NUM_EDGES):
        parent, child = EDGES[e]
        if ksc[parent] > 0 and ksc[child] == 0:
            ksc[child], kps[child] = _traverse(e, kps[parent], child, scores, off, fwd)
    return kps, ksc


def decode_multiple(outputs, score_thr: float = 0.3, max_poses: int = 10,
                    nms_radius_px: float = 20.0) -> list[tuple[float, list[tuple[float, float, float]]]]:
    """Every body in the three tensors, best first: (instance score, 17 (x, y, conf) in COCO order), x and y
    normalised by INPUT_SIZE and NOT clipped (a point past the frame stays past it, as MediaPipe's would; Body's
    _clean clamps it and zeroes its confidence for both detectors alike), conf the keypoint's sigmoid score. The
    instance score is the mean of the keypoint scores not already claimed by an earlier body (within
    nms_radius_px), so a same-root duplicate scores near 0. ValueError when the tensors are not posenet's."""
    heat, off, mid = _check(outputs)
    scores = _sigmoid(heat)
    fwd, bwd = mid[:, :, :2 * NUM_EDGES], mid[:, :, 2 * NUM_EDGES:]
    sq = nms_radius_px ** 2
    poses: list[tuple[np.ndarray, np.ndarray, float]] = []
    for root in _local_maxima(scores, score_thr):
        if len(poses) >= max_poses:
            break
        _, kp, y, x = root
        root_pos = _coords(kp, y, x, off)
        if any(((p[0][kp] - root_pos) ** 2).sum() <= sq for p in poses):
            continue
        kps, ksc = _decode_pose(root, scores, off, fwd, bwd)
        keep = np.ones(NUM_KP, dtype=bool)
        for pk, _, _ in poses:
            keep &= ((pk - kps) ** 2).sum(axis=1) > sq
        poses.append((kps, ksc, float((ksc * keep).sum() / NUM_KP)))
    poses.sort(key=lambda p: p[2], reverse=True)
    w, h = INPUT_SIZE
    return [(inst, [(float(k[1] / w), float(k[0] / h), float(c)) for k, c in zip(kps, ksc)])
            for kps, ksc, inst in poses]


class IMX500Pose:
    """The PoseDetector for the sensor: detect() ignores the frame and decodes the tensor in capture.metadata (the
    frame the capture just read); no tensor (the network still uploading, or a dropped one) is no body this
    capture. At most MAX_BODIES bodies, best first, reach the tracker: its assign() has no scipy on the Pi and
    stops at 6 by 6, and a crowd at the wall must not end the camera thread. A tensor the decoder does not know
    is logged once and is no body. imx is picamera2's IMX500 (get_outputs(metadata)); capture a Picamera2Capture.
    Coordinates need no crop correction: the network sees the whole sensor, as the 4:3 main stream does."""

    def __init__(self, capture, imx, min_instance: float = MIN_INSTANCE, max_bodies: int = MAX_BODIES):
        self._capture, self._imx, self.min_instance, self.max_bodies = capture, imx, min_instance, max_bodies
        self._complained = False

    def detect(self, bgr: np.ndarray, ts_ms: int) -> list[tuple[Keypoint, ...]]:
        metadata = self._capture.metadata
        if not metadata.get("CnnOutputTensor"):
            return []
        outputs = self._imx.get_outputs(metadata, add_batch=False)
        if outputs is None:
            return []
        try:
            poses = decode_multiple(outputs)
        except ValueError as e:
            if not self._complained:
                self._complained = True
                log.warning("imx500: %s; no bodies until it changes", e)
            return []
        kept = [pts for inst, pts in poses if inst >= self.min_instance][:self.max_bodies]   # poses are best first
        return [tuple(Keypoint(x, y, c) for x, y, c in pts) for pts in kept]

    def close(self) -> None:
        """The capture owns the camera; the sensor keeps its network."""

    @property
    def imx(self):
        """picamera2's IMX500 object, for the doctor's describe()."""
        return self._imx


def describe(imx) -> str:
    """'posenet 30/s': the model and its stated inference rate, for the doctor's line."""
    intrinsics = getattr(imx, "network_intrinsics", None)
    rate = getattr(intrinsics, "inference_rate", None)
    return f"posenet {rate:g}/s" if rate else "posenet"


def open_imx500(cfg, size: tuple[int, int]):
    """(Picamera2Capture, IMX500Pose) for camera = "imx500": the IMX500 object first (it owns the camera number
    and the network upload, which it shows as a progress bar when the sensor does not hold posenet yet), then the
    capture on that camera at the model's rate with BUFFER_COUNT buffers. Raises when picamera2 is missing or the
    camera does not open; the caller logs once. Call it on the main thread."""
    from picamera2 import Picamera2                                # here: apt's package, on the Pi only
    from picamera2.devices.imx500 import IMX500, NetworkIntrinsics

    from arcade.sources.capture_picamera2 import Picamera2Capture
    from arcade.sources.pose_mediapipe import CAPTURE_SIZE

    imx = IMX500(MODEL)
    intrinsics = imx.network_intrinsics or NetworkIntrinsics()
    intrinsics.task = "pose estimation"
    intrinsics.update_with_defaults()
    cam = Picamera2(imx.camera_num)
    imx.show_network_fw_progress_bar()          # the demos' order: after the camera object, before it starts
    capture = Picamera2Capture(CAPTURE_SIZE, camera=cam, frame_rate=float(intrinsics.inference_rate or 30),
                               buffer_count=BUFFER_COUNT)
    log.info("imx500: %s on camera %s", describe(imx), imx.camera_num)
    return capture, IMX500Pose(capture, imx)
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd /Users/trey/dev/codeisart-wall && PY=/Users/trey/dev/codeisart/.venv/bin/python; $PY -m pytest tests/arcade/test_pose_imx500.py -v 2>&1 | tail -15
```
Expected: 13 passed. If `test_decodes_one_standing_body_where_the_spike_saw_it` fails on the nose position by more than 0.03, print `poses[0][1][0]` and compare with the spike report (sample1: nose (0.39, 0.55); sample2: (0.42, 0.57)); widen to 0.05 only if the shoulders and ankles assertions hold, and say so in the commit.

- [ ] **Step 5: Commit**

```bash
cd /Users/trey/dev/codeisart-wall && git add arcade/sources/pose_imx500.py tests/arcade/test_pose_imx500.py && git commit -q -m "feat(arcade): pose_imx500: the PoseNet decoder, IMX500Pose and open_imx500 (the AI Camera's sensor as the pose source)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: `make_sources` builds the imx500 camera

**Files:**
- Modify: `arcade/sources/__init__.py:48-55` (the `elif` chain in `make_sources`)
- Test: `tests/arcade/test_sources.py` (add two tests after `test_make_sources_mediapipe_gets_the_config_clock_and_calibration`, line 85-98)

**Interfaces:**
- Consumes: `open_imx500(cfg, size)` (Task 3), `PoseCamera(cfg, size, clock, calibration=, capture=, detector=)` (Task 1).
- Produces: `make_sources` with `cfg.camera == "imx500"` returns `(PoseCamera, NoSource())`; when `open_imx500` raises, the camera is a `PoseCamera` that is unavailable (`latest()` None) and the warning `imx500 camera unavailable: ...` is logged once; nothing raises.

- [ ] **Step 1: Write the failing tests**

Add to `tests/arcade/test_sources.py`:

```python
def test_make_sources_imx500_opens_the_pair_and_hands_it_to_the_pose_camera(monkeypatch):
    import arcade.sources.pose_imx500 as pi
    import arcade.sources.pose_mediapipe as pm

    seen = {}

    class Spy:
        def __init__(self, cfg, size, clock, *, calibration=None, capture=None, detector=None):
            seen.update(cfg=cfg, size=size, clock=clock, calibration=calibration, capture=capture, detector=detector)

    monkeypatch.setattr(pm, "PoseCamera", Spy)
    monkeypatch.setattr(pi, "open_imx500", lambda cfg, size: ("the capture", "the detector"))
    cfg, clock, cal = make_cfg((64, 64), camera="imx500"), FakeClock(), Calibration(zone=(0.1, 0.1, 0.9, 0.9))
    cam, aud = make_sources(cfg, (64, 64), clock, calibration=cal)
    assert isinstance(cam, Spy) and isinstance(aud, NoSource)
    assert seen == dict(cfg=cfg, size=(64, 64), clock=clock, calibration=cal, capture="the capture", detector="the detector")


def test_make_sources_imx500_without_picamera2_is_unavailable_and_says_so(monkeypatch, caplog):
    import sys

    monkeypatch.setitem(sys.modules, "picamera2", None)        # import picamera2 raises ImportError
    cfg = make_cfg((64, 64), camera="imx500")
    cam, aud = make_sources(cfg, (64, 64), FakeClock())
    assert cam.available is False and cam.latest() is None
    assert "imx500 camera unavailable" in caplog.text and "picamera2" in caplog.text
    cam.close()
```

Check the top of the file for `make_cfg`, `FakeClock`, `Calibration`, `NoSource` imports (they are used by the mediapipe test above; `make_cfg(size, **kw)` passes keywords to `ArcadeConfig`).

Also change the existing test `test_make_sources_mediapipe_gets_the_config_clock_and_calibration` (line 85-98): its `monkeypatch.setattr(pm, "MediaPipeCamera", Spy)` becomes `monkeypatch.setattr(pm, "PoseCamera", Spy)`. Rebinding the alias would not rebind the name `make_sources` now calls, and the real camera would open the Mac's webcam from a unit test (plan review C1).

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd /Users/trey/dev/codeisart-wall && PY=/Users/trey/dev/codeisart/.venv/bin/python; $PY -m pytest tests/arcade/test_sources.py -q -k imx500 2>&1 | tail -4
```
Expected: both fail with `ValueError: camera 'imx500' is not available yet`.

- [ ] **Step 3: Implement**

In `arcade/sources/__init__.py`, replace the `elif cfg.camera == "mediapipe":` branch through the `else: raise` (lines 48-55) with:

```python
    elif cfg.camera == "mediapipe":
        from arcade.sources import pose_mediapipe   # here: it resolves arcade.main.MODEL_PATH, and main imports us
        cal = calibration if calibration is not None else load_calibration(cfg.data_dir)
        camera = pose_mediapipe.PoseCamera(cfg, size, clock, calibration=cal)
    elif cfg.camera == "imx500":
        from arcade.sources import pose_imx500, pose_mediapipe   # here, as above
        cal = calibration if calibration is not None else load_calibration(cfg.data_dir)
        try:
            capture, detector = pose_imx500.open_imx500(cfg, size)   # main thread: it opens the camera
        except Exception as e:
            log.warning("imx500 camera unavailable: %s", e)
            capture, detector = _Unopened(), _Unopened()           # the camera is built, unavailable, and never starts
            camera = pose_mediapipe.PoseCamera(cfg, size, clock, calibration=cal, capture=capture, detector=detector,
                                               start=False)
        else:
            camera = pose_mediapipe.PoseCamera(cfg, size, clock, calibration=cal, capture=capture, detector=detector)
    elif cfg.camera == "none":
        camera = NoSource()
    else:
        raise ValueError(f"camera {cfg.camera!r} is not available yet; use mediapipe, imx500 or none")
```

The module has no logger today: add `import logging` to its imports (line 4 region) and `log = logging.getLogger("arcade")` after the imports. Then add above `make_sources`:

```python
class _Unopened:
    """A capture and detector for a PoseCamera whose device did not open: it never starts, and close() is a no-op."""

    metadata: dict = {}

    def read(self):
        return False, None

    def release(self) -> None:
        pass

    def detect(self, bgr, ts_ms):
        return []

    def close(self) -> None:
        pass
```

Update `make_sources`' docstring sentence `mediapipe opens the camera here, on the calling (main) thread.` to `mediapipe and imx500 open the camera here, on the calling (main) thread; an imx500 that does not open (no picamera2, no camera) logs once and gives an unavailable camera.`

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd /Users/trey/dev/codeisart-wall && PY=/Users/trey/dev/codeisart/.venv/bin/python; $PY -m pytest tests/arcade/test_sources.py tests/arcade/test_pose_mediapipe.py -q 2>&1 | tail -3
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/trey/dev/codeisart-wall && git add arcade/sources/__init__.py tests/arcade/test_sources.py && git commit -q -m "feat(arcade): camera = imx500 builds the PoseCamera on the sensor's detector; unavailable, not an error, without picamera2

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: The doctor's `imx500` probe and `--camera`

**Files:**
- Modify: `arcade/main.py` (`probe_picamera2` at line 61-67: add `probe_imx500` after it; `make_probes` at line 150-157; `run` at line 187-189; the `doctor` parser at line 229-236; `main` at line 258-260)
- Test: `tests/arcade/test_doctor.py` (add after `test_make_probes_picks_the_camera_probe_by_capture`, line 117-123)

**Interfaces:**
- Consumes: `open_imx500(cfg, size)` and `describe(imx)` (Task 3), `Picamera2Capture.metadata` (Task 2).
- Produces: `probe_imx500(timeout: float, upload_wait: float = UPLOAD_WAIT) -> tuple[bool, str]` with `UPLOAD_WAIT = 300.0` and `UPLOAD_NOTICE_AFTER = 3.0` (no index: the IMX500 object picks its own camera number, so `--camera-index` means nothing for imx500); `make_probes(camera_index=0, audio_device="", model=MODEL_PATH, capture="opencv", camera="mediapipe")`: with `camera == "imx500"` both `"camera"` and `"pose"` share one `probe_imx500` call (the camera opens once); `doctor --camera {mediapipe,imx500,...}` (choices `CAMERAS`); `run --require` passes `camera=cfg.camera`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/arcade/test_doctor.py`:

```python
class TensorCapture:
    """A fake Picamera2Capture whose frames carry a tensor from the nth read on."""

    def __init__(self, tensor_from=1, frame=None):
        import numpy as np

        self.reads, self.released, self.tensor_from = 0, False, tensor_from
        self.frame = frame if frame is not None else np.full((480, 640, 3), 9, np.uint8)
        self.metadata = {}

    def read(self):
        self.reads += 1
        self.metadata = {"SensorTimestamp": self.reads} | ({"CnnOutputTensor": [1.0]} if self.reads >= self.tensor_from else {})
        return True, self.frame

    def release(self):
        self.released = True


class FakeIMX:
    class network_intrinsics:
        inference_rate = 30


def test_probe_imx500_reports_the_model_the_rate_and_the_frame(monkeypatch):
    import arcade.sources.pose_imx500 as pi
    from arcade.main import probe_imx500

    cap = TensorCapture()
    monkeypatch.setattr(pi, "open_imx500", lambda cfg, size: (cap, pi.IMX500Pose(cap, FakeIMX())))
    assert probe_imx500(1.0) == (True, "imx500 posenet 30/s: 640x480")
    assert cap.released


def test_probe_imx500_says_uploading_and_waits(monkeypatch, capsys):
    import arcade.sources.pose_imx500 as pi
    from arcade.main import probe_imx500

    cap = TensorCapture(tensor_from=10 ** 9)                    # frames, never a tensor
    monkeypatch.setattr(pi, "open_imx500", lambda cfg, size: (cap, pi.IMX500Pose(cap, FakeIMX())))
    monkeypatch.setattr("arcade.main.UPLOAD_NOTICE_AFTER", 0.05)
    ok, why = probe_imx500(0.1, upload_wait=0.3)
    assert not ok and "no tensor" in why and cap.released
    assert "uploading the network to the sensor" in capsys.readouterr().out
    assert cap.reads > 2                                          # it kept reading past the 0.1 s timeout


def test_probe_imx500_without_picamera2_is_unavailable(monkeypatch):
    import sys

    from arcade.main import probe_imx500

    monkeypatch.setitem(sys.modules, "picamera2", None)
    ok, why = probe_imx500(1.0)
    assert not ok and "picamera2" in why


def test_make_probes_imx500_is_both_the_camera_and_the_pose_opened_once(monkeypatch):
    import arcade.main

    calls = []
    monkeypatch.setattr(arcade.main, "probe_imx500", lambda timeout: calls.append(timeout) or (True, "imx500"))
    probes = arcade.main.make_probes(camera="imx500")
    assert probes["camera"](1.0) == (True, "imx500") and probes["pose"](1.0) == (True, "imx500")
    assert calls == [1.0]                                          # the camera opened once for both names


def test_doctor_takes_camera_imx500(monkeypatch, capsys):
    import arcade.main

    monkeypatch.setattr(arcade.main, "probe_imx500", lambda timeout: (True, "imx500 posenet 30/s: 640x480"))
    assert main(["doctor", "--require", "camera,pose", "--camera", "imx500"]) == 0
    out = capsys.readouterr().out
    assert out.count("imx500 posenet 30/s") == 2
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd /Users/trey/dev/codeisart-wall && PY=/Users/trey/dev/codeisart/.venv/bin/python; $PY -m pytest tests/arcade/test_doctor.py -q -k imx500 2>&1 | tail -4
```
Expected: `ImportError: cannot import name 'probe_imx500'` and the `--camera` test failing on argparse.

- [ ] **Step 3: Implement**

In `arcade/main.py`, after `TIMEOUT = 5.0` (line 29) add:

```python
UPLOAD_WAIT = 300.0           # s the imx500 probe waits for the first tensor once frames flow without one: the
UPLOAD_NOTICE_AFTER = 3.0     # sensor is taking the network (2 MB at about 9 kB/s, 3 to 4 min); the notice after 3 s
```

After `probe_picamera2` (after line 67) add:

```python
def probe_imx500(timeout: float, upload_wait: float = UPLOAD_WAIT) -> tuple[bool, str]:
    """The AI Camera with posenet on its sensor (camera "imx500"), opened as the arcade opens it: (True, the model,
    its rate and the frame size) at the first frame that carries a tensor. Frames without one past
    UPLOAD_NOTICE_AFTER mean the network is uploading: it says so, prints the wait every 30 s, and waits up to
    upload_wait instead of timeout (^C ends it). The camera index is the IMX500 object's, not --camera-index."""
    from arcade.config import ArcadeConfig
    from arcade.sources import pose_imx500

    cfg = ArcadeConfig(camera="imx500")           # index is unused: the IMX500 object picks its own camera number
    try:
        capture, detector = pose_imx500.open_imx500(cfg, cfg.size)
    except Exception as e:
        return False, f"imx500: {type(e).__name__}: {e} (apt: imx500-all python3-picamera2; the ribbon seated)"
    label = f"imx500 {pose_imx500.describe(detector.imx)}"
    frames, start = 0, time.monotonic()
    deadline, notified, told = start + timeout, False, start
    try:
        while time.monotonic() < deadline:
            ok, frame = capture.read()
            if not ok or frame is None:
                time.sleep(0.05)
                continue
            frames += 1
            if capture.metadata.get("CnnOutputTensor"):
                return True, f"{label}: {frame.shape[1]}x{frame.shape[0]}"
            now = time.monotonic()
            if not notified and now - start >= UPLOAD_NOTICE_AFTER:
                notified, told = True, now
                deadline = start + upload_wait
                print("imx500: frames but no tensor yet: uploading the network to the sensor, up to 4 minutes "
                      "(^C stops the wait)", file=sys.stdout, flush=True)   # CLI output, as the doctor's lines
            elif notified and now - told >= 30.0:
                told = now
                print(f"imx500: still waiting, {now - start:.0f} s", file=sys.stdout, flush=True)
        why = f"{frames} frames, no tensor in {time.monotonic() - start:.0f} s" if frames else f"no frames in {timeout:.0f} s"
        return False, f"{label}: {why} (is posenet on the sensor: another network means a new upload)"
    finally:
        capture.release()
```

(The probe prints to `sys.stdout`, not the doctor's `out` argument: every caller today passes none, and the test reads capsys.)

Replace `make_probes` (lines 150-157) with:

```python
def make_probes(camera_index: int = 0, audio_device: str = "", model: Path = MODEL_PATH,
                capture: str = "opencv", camera: str = "mediapipe") -> dict[str, Probe]:
    """The doctor's probes by name. camera "imx500" is one probe for both the camera and the pose (the sensor runs
    the model); otherwise the camera's probe is the one capture names and the pose's is MediaPipe's. The probe
    functions are looked up when a probe runs."""
    if camera == "imx500":
        done: dict[str, tuple[bool, str]] = {}

        def imx(t: float) -> tuple[bool, str]:        # one opening of the camera serves both names
            if "result" not in done:
                done["result"] = probe_imx500(t)
            return done["result"]

        return {"camera": imx, "mic": lambda t: probe_mic(t, audio_device), "pose": imx}
    return {"camera": lambda t: (probe_picamera2 if capture == "picamera2" else probe_camera)(t, camera_index),
            "mic": lambda t: probe_mic(t, audio_device),
            "pose": lambda t: probe_pose(t, Path(model))}
```

In `run` (line 188) pass the camera: `make_probes(cfg.camera_index, cfg.audio_device, capture=cfg.capture, camera=cfg.camera)`.

In the `doctor` parser (after the `--capture` line, 234) add:

```python
    d.add_argument("--camera", choices=CAMERAS, default="mediapipe", help="imx500: posenet on the AI Camera's sensor")
```

and import `CAMERAS` where `CAPTURES` is imported from `arcade.config` (line 10 to 20 region: `from arcade.config import ...`).

In `main` (line 259-260) pass it: `make_probes(args.camera_index, args.audio_device, Path(args.model), args.capture, args.camera)`.

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd /Users/trey/dev/codeisart-wall && PY=/Users/trey/dev/codeisart/.venv/bin/python; $PY -m pytest tests/arcade/test_doctor.py tests/arcade/test_main.py -q 2>&1 | tail -3
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/trey/dev/codeisart-wall && git add arcade/main.py tests/arcade/test_doctor.py && git commit -q -m "feat(arcade): the doctor's imx500 probe (the model, its rate, the upload notice) and --camera

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: The lag line

**Files:**
- Modify: `arcade/runner.py` (`__init__` near line 332-334; `_push` at line 555-570)
- Test: `tests/arcade/test_runner.py` (add one test; the file has `font5x7`, `FakeDisplay`, `NullLobby`, `FakeClock` in use, see `test_lobby_request_launches_next_tick` at line 81)

**Interfaces:**
- Produces: with the logger at DEBUG (`run -v`), once a second a line `capture age at push: median 48 ms, max 61 ms (50 pushes)` on the `arcade` logger; the age is `clock() - capture_t` of the latest camera capture at each push. Nothing at INFO. `LAG_EVERY = 1.0`.

- [ ] **Step 1: Write the failing test**

Add to `tests/arcade/test_runner.py` (its module already imports `logging`, `Runner`, and `Person, scene` from `arcade.sources.actors`; the function imports the rest itself):

```python
def test_verbose_logs_the_capture_age_at_push_once_a_second(font5x7, caplog):
    from arcade.headless import NullLobby
    from arcade.sources import NoSource
    from arcade.sources.scripted import ScriptedCamera
    from show.display.fake import FakeDisplay
    from tests.arcade.helpers import FakeClock, make_cfg

    clock = FakeClock(500.0)
    cfg = make_cfg((128, 64))
    frames = scene(persons=[Person(0.5, id=7)], ticks=cfg.fps * 3)
    camera = ScriptedCamera(frames, clock)
    runner = Runner(cfg, FakeDisplay(), font5x7, NullLobby(), [], clock=clock, sleep=clock.sleep)
    with caplog.at_level(logging.DEBUG, logger="arcade"):
        runner.loop(camera, NoSource(), max_ticks=cfg.fps * 2 + 2)
    lines = [r.message for r in caplog.records if r.message.startswith("capture age at push")]
    assert 1 <= len(lines) <= 3
    assert "median" in lines[0] and "max" in lines[0] and lines[0].endswith("pushes)")
    with caplog.at_level(logging.INFO, logger="arcade"):
        caplog.clear()
        runner.loop(camera, NoSource(), max_ticks=cfg.fps)
    assert not [r for r in caplog.records if r.message.startswith("capture age at push")]
```

(`tests/arcade/test_sources.py`'s `test_scripted_camera_stamps_the_runner_clock` builds a `Runner` the same way: `Runner(make_cfg((128, 32)), FakeDisplay(), font5x7, NullLobby(), [], clock=clock, sleep=clock.sleep)`.)

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd /Users/trey/dev/codeisart-wall && PY=/Users/trey/dev/codeisart/.venv/bin/python; $PY -m pytest tests/arcade/test_runner.py -q -k capture_age 2>&1 | tail -4
```
Expected: FAIL, `assert 1 <= 0`.

- [ ] **Step 3: Implement**

In `arcade/runner.py`, beside `LOG_EVERY` (line 53) add:

```python
LAG_EVERY = 1.0              # seconds between two lag lines (capture age at push), at DEBUG: run -v
```

In `__init__`, after `self._camera_seq, self._camera_capture = 0, None` (line 334) add:

```python
        self._ages: list[float] = []            # capture ages at push since the last lag line, in ms
        self._lag_logged = -math.inf
```

In `_push`, after the `try/except` that pushes (after line 566, before `held = ...`) add:

```python
        if self._camera_capture is not None and self.log.isEnabledFor(logging.DEBUG):
            self._ages.append((self.clock() - self._camera_capture) * 1000.0)
            if self.t - self._lag_logged >= LAG_EVERY and self._ages:
                self._lag_logged = self.t
                ages = sorted(self._ages)
                self.log.debug("capture age at push: median %.0f ms, max %.0f ms (%d pushes)",
                               ages[len(ages) // 2], ages[-1], len(ages))
                self._ages = []
```

(`logging` and `math` are already imported in the module; check with `grep -n "^import" arcade/runner.py`.)

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd /Users/trey/dev/codeisart-wall && PY=/Users/trey/dev/codeisart/.venv/bin/python; $PY -m pytest tests/arcade/test_runner.py tests/arcade/test_headless.py -q 2>&1 | tail -3
```
Expected: all pass (the headless tests count governor calls, not log lines).

- [ ] **Step 5: Commit**

```bash
cd /Users/trey/dev/codeisart-wall && git add arcade/runner.py tests/arcade/test_runner.py && git commit -q -m "feat(arcade): run -v logs the capture age at push once a second (the lag as a number)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: The Pi's config, the runbook, the sources README

**Files:**
- Modify: `arcade.pi.toml`
- Modify: `tests/arcade/test_config.py:147-151` (`test_the_pi_config_drives_the_card_through_picamera2`)
- Modify: `docs/runbooks/arcade-on-the-pi.md` (sections 2, 3, 4)
- Modify: `arcade/sources/README.md` (a new section at the top)

**Interfaces:**
- Produces: `arcade.pi.toml` with `camera = "imx500"`, `camera_fps = 30`, `capture = "picamera2"` kept, `gamma = 1.0` kept, `backend = "colorlight"` kept.

- [ ] **Step 1: Write the failing test**

Replace the test at `tests/arcade/test_config.py:147-151` with:

```python
def test_the_pi_config_reads_pose_from_the_sensor():
    cfg = load_config(Path(__file__).resolve().parents[2] / "arcade.pi.toml")
    assert (cfg.backend, cfg.iface, cfg.capture, cfg.camera, cfg.camera_fps, cfg.gamma) == \
        ("colorlight", "eth0", "picamera2", "imx500", 30, 1.0)   # 30: posenet's rate on the sensor (Q182)
    assert cfg.size == (128, 64) and cfg.allow_record is False
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd /Users/trey/dev/codeisart-wall && PY=/Users/trey/dev/codeisart/.venv/bin/python; $PY -m pytest tests/arcade/test_config.py -q -k pi_config 2>&1 | tail -3
```
Expected: FAIL on `("colorlight", "eth0", "picamera2", "mediapipe", 15, 1.0)`.

- [ ] **Step 3: Change the config**

`arcade.pi.toml` becomes:

```toml
# The Pi 5 at the wall: the Colorlight card on eth0 and the AI Camera with PoseNet on its sensor (Q182, the spike of
# 2026-10-02: 30 a second, 48 ms sensor to keypoints). Every other key is its default.
# Start it as docs/runbooks/arcade-on-the-pi.md says. To fall back to MediaPipe on the Pi's CPU:
# camera = "mediapipe" and camera_fps = 15 (its steady rate; capture stays "picamera2").
backend = "colorlight"
camera = "imx500"
capture = "picamera2"
camera_fps = 30       # posenet's inference rate on the IMX500: every tensor is taken
gamma = 1.0           # the card applies gamma: wall_pattern.py gamma's checker matched the RIGHT patch (2026-10-02)
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd /Users/trey/dev/codeisart-wall && PY=/Users/trey/dev/codeisart/.venv/bin/python; $PY -m pytest tests/arcade/test_config.py -q 2>&1 | tail -3
```
Expected: all pass.

- [ ] **Step 5: The runbook**

In `docs/runbooks/arcade-on-the-pi.md`:

Section 2, after the MediaPipe model paragraph, add:

```markdown
The pose runs on the AI Camera's sensor (PoseNet, `camera = "imx500"` in `arcade.pi.toml`): no model file on the
Pi; `imx500-all` put `/usr/share/imx500-models/imx500_network_posenet.rpk` there. MediaPipe stays installed as
the fallback (`camera = "mediapipe"`, `camera_fps = 15`).
```

Section 3, replace the doctor line and its explanation with:

```
.venv/bin/python -m arcade doctor --require camera,pose --camera imx500 --capture picamera2
```

```markdown
The camera's line names `imx500`; the doctor prints `camera  ok  imx500 posenet 30/s: 640x480` and the same for
`pose`. The first start after a power cycle, or after another network was on the sensor, uploads PoseNet to it:
the doctor prints "uploading the network to the sensor, up to 4 minutes" and waits (2 MB at about 9 kB/s). The
sensor then keeps the network across restarts. A unit that is active holds the card: the owner stops it
(`sudo systemctl stop <unit>`) and starts it again afterwards.
```

Section 4, after the `--game` paragraph, add:

```markdown
`-v` also logs, once a second, `capture age at push: median N ms, max M ms`: the lag from the sensor's frame to
the wall's frame, the number for `live-smoke.md`. The spike's expectation is a median near 70 to 90 ms (48 ms to
keypoints plus the tick and the sender).
```

- [ ] **Step 6: The sources README, and the spec's doctor command**

In `docs/superpowers/specs/2026-10-02-pose-on-the-sensor-design.md`: section 5 step 2, replace `` `doctor --require camera,pose --config arcade.pi.toml` `` with `` `doctor --require camera,pose --camera imx500 --capture picamera2` (the doctor takes no `--config`) ``. Section 5 step 3, add "one person alone in front of the wall: one figure, not two (27 of the spike's 30 samples decode a second body at instance 0.33 to 0.72 about a tenth of the frame from the first, most likely a bystander at the event; if a ghost shows, `MIN_INSTANCE` in `pose_imx500.py` is the knob: 0.5 clears all but two of those samples)". Section 3.4, the sentence "the doctor says so when `capture = "opencv"` is set beside it" gets "(not built; `capture` is ignored for imx500)". Section 3.3's "A tensor whose shapes are not ... raises `ValueError`": add "the detector logs it once and gives no bodies; the camera thread lives". Section 3.3's `IMX500Pose`: add "at most `MAX_BODIES = 4` bodies reach the tracker (its `assign()` has no scipy on the Pi and stops at 6 by 6)". Section 6's crowd risk: replace "2 with PoseNet's 0.3 instance threshold" with "a second body above 0.3 in 27 of 30 samples".

At the top of `arcade/sources/README.md`, after `Measured facts and decisions (spec 12).`, add:

```markdown
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
```

- [ ] **Step 7: Commit**

```bash
cd /Users/trey/dev/codeisart-wall && git add arcade.pi.toml tests/arcade/test_config.py docs/runbooks/arcade-on-the-pi.md arcade/sources/README.md docs/superpowers/specs/2026-10-02-pose-on-the-sensor-design.md && git commit -q -m "feat(arcade): arcade.pi.toml reads pose from the sensor (imx500, 30/s); the runbook, the sources README, the spec's doctor command

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 8: The full suite and the hand-off to the wall

**Files:** none new.

- [ ] **Step 1: Run the full suite once, where the owner says**

Ask the owner first: the Mac (8 GB, about 455 s, against his rule of 2026-10-02 that full suites go to the Pi) or the Pi (his rule, but promptviz holds its wall tonight and a suite there may cost the party unit late frames; it would run as a bundle on stdin into a scratch clone under the lock, the memory's recipe, after promptviz stops at the wall session). On the Mac:

```bash
cd /Users/trey/dev/codeisart-wall && PY=/Users/trey/dev/codeisart/.venv/bin/python; $PY -m pytest -q -p no:cacheprovider 2>&1 | tail -3
```
Expected: everything passes, 3 skipped (the Mac's: `test_colorlight_slot`, `test_colorlight_child`, `test_sandbox`; the landmarker test runs now that `models/` is linked), under 540 s. Write the three numbers down. A failure is read once more before any decision (the Mac's load); a real failure is fixed in the task it belongs to with its own commit.

- [ ] **Step 2: Compile check for the Pi's Python**

```bash
cd /Users/trey/dev/codeisart-wall && /Users/trey/dev/codeisart/.venv/bin/python -m py_compile arcade/sources/pose_imx500.py arcade/sources/capture_picamera2.py arcade/sources/pose_mediapipe.py arcade/sources/__init__.py arcade/main.py arcade/runner.py && echo compiled
```

- [ ] **Step 3: Report**

Tell the owner: the branch tip, the suite's numbers, and that the wall session (spec section 5) waits for his "go": promptviz stopped at his word, then the code to the Pi as a git bundle on stdin under the lock (nothing is pushed to origin: `git bundle create - main..wall-bringup` piped into `git -C ~/codeisart fetch /dev/stdin wall-bringup` is the memory's recipe, then `git -C ~/codeisart checkout wall-bringup && git merge --ff-only FETCH_HEAD`, all in one locked ssh command), then the doctor, exactly:

```
.venv/bin/python -m arcade doctor --require camera,pose --camera imx500 --capture picamera2
```

(the `doctor` subcommand has no `--config`; the spec's section 5 wrote one and is corrected in Task 7), then the mirror figure, then Copy Me. Nothing in this plan touches the Pi or the card.

---

## Self-review notes

- Spec 3.1 (one camera, two detectors): Task 1. 3.2 (metadata, frame_rate, buffer_count): Task 2. 3.3 (decoder, `IMX500Pose`, `open_imx500`): Task 3. 3.4 wiring: Task 4 (`make_sources`), Task 5 (doctor, `--camera`, `run --require`), Task 7 (`arcade.pi.toml`), Task 6 (the lag line). 3.5 (not changed): no task touches the governor, limiter, driver, tracker, games or lobby. Section 4 tests: Tasks 0 to 7 each carry theirs; the full suite is Task 8. Section 5 (the wall session) is the owner's and is handed off in Task 8. Section 8 (the record) landed with the spec on main (cd233b8) and is merged in Task 0.
- Names: `PoseCamera`, `PoseDetector`, `MediaPipeDetector`, `IMX500Pose`, `open_imx500`, `describe`, `decode_multiple`, `Picamera2Capture.metadata`, `probe_imx500`, `make_probes(..., camera=)` are used with the same spelling in every task.
- Review Focus 1 to 5 each name their test and task.
- The decoder's instance threshold (`MIN_INSTANCE = 0.3`), body cap (`MAX_BODIES = 4`) and NMS radius (20 px of the 481x353 input) are the spike's and the plan review's; the first play may retune them (a constant each).
- Plan reviews (2026-10-02 night, two fresh-context adversarial reviewers): `docs/superpowers/reviews/2026-10-02-pose-on-the-sensor-plan-review-integration.md` (1 Critical, 4 Important, 10 Minor) and `...-plan-review-decoder.md` (2 Critical, 2 Important, 5 Minor). Every Critical and Important is folded in above: the `pm.PoseCamera` monkeypatch (Task 4), the `models/` link and the measured skips (Tasks 0, 8), the suite's place as the owner's choice (Task 8), one probe for both names with the wait printed (Task 5), the spec's doctor command (Task 7), the cold heatmap test, the four-body cap, no clipping, the tolerant detector (Task 3). Minors taken: the Pi fallback cut, the logger said plainly, `imx` public, the progress-bar order, the README's old name, `record --raw` noted. Not taken: scipy in the `pi` extra (the cap suffices tonight; a dependency change on the Pi waits), the `_due` pacer on `SensorTimestamp` (the lag line will say whether it matters).
