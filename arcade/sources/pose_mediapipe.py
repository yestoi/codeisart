"""Mac camera (spec 6.1): OpenCV capture at 640 by 480 and MediaPipe's Pose Landmarker in VIDEO mode, num_poses 2,
on the unflipped frame; mirror_keypoints flips x once afterwards when cfg.mirror. Pose only until M5: latest() is
(capture_t, bodies, (), None)."""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable, Sequence

import numpy as np

from arcade.calibration import Calibration
from arcade.sensed import MIN_CONF, Keypoint
from arcade.sources.camera import BodyTracker, CameraResult, ThreadedCamera
from arcade.sources.mirror import mirror_keypoints

log = logging.getLogger("arcade")

# MediaPipe's 33 landmarks -> COCO 17: nose, eyes, ears, shoulders, elbows, wrists, hips, knees, ankles.
MP_TO_COCO = (0, 2, 5, 7, 8, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28)
CAPTURE_SIZE = (640, 480)
NUM_POSES = 2
EARLY = 0.25              # a frame up to this share of a period before inference is due counts as due


def landmarks_to_keypoints(landmarks) -> tuple[Keypoint, ...]:
    """The 17 COCO keypoints of one person's 33 landmarks; visibility is the confidence (1.0 when missing)."""
    out = []
    for i in MP_TO_COCO:
        lm = landmarks[i]
        vis = getattr(lm, "visibility", None)
        out.append(Keypoint(float(lm.x), float(lm.y), 1.0 if vis is None else float(vis)))
    return tuple(out)


def box_of(keypoints: Sequence[Keypoint], min_conf: float = MIN_CONF) -> tuple[float, float, float, float]:
    """The box around the keypoints at min_conf or more, clamped to 0..1; all zeros without one."""
    pts = [k for k in keypoints if k.conf >= min_conf]
    if not pts:
        return (0.0, 0.0, 0.0, 0.0)
    clamp = lambda v: min(1.0, max(0.0, v))
    return (clamp(min(k.x for k in pts)), clamp(min(k.y for k in pts)),
            clamp(max(k.x for k in pts)), clamp(max(k.y for k in pts)))


class Landmarker:
    """MediaPipe's PoseLandmarker, VIDEO mode: detect(rgb, ts_ms) gives each person's 33 landmarks.
    ts_ms must increase strictly from call to call."""

    def __init__(self, model_path: Path, num_poses: int = NUM_POSES):
        import mediapipe as mp   # here, so importing this module never loads MediaPipe

        vision = mp.tasks.vision
        options = vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO, num_poses=num_poses)
        self._mp = mp
        self._landmarker = vision.PoseLandmarker.create_from_options(options)

    def detect(self, rgb: np.ndarray, ts_ms: int) -> list:
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        return list(self._landmarker.detect_for_video(image, ts_ms).pose_landmarks)

    def close(self) -> None:
        self._landmarker.close()


def open_capture(index: int):
    """cv2.VideoCapture(index) at CAPTURE_SIZE; RuntimeError if it does not open. Call it on the main thread: macOS
    asks for camera access only from there."""
    import cv2

    cap = cv2.VideoCapture(index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_SIZE[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_SIZE[1])
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f"camera index {index} did not open")
    return cap


class MediaPipeCamera(ThreadedCamera):
    """Reads every frame the camera gives (so its buffer never holds an old one), stamps it with clock() in
    seconds as the read returns, and runs inference on the frames due at cfg.camera_fps; the others return None
    and the last result holds.

    size is the wall size, kept for M5's motion grid; model_path None is the doctor's arcade.main.MODEL_PATH.
    capture (read() -> (ok, bgr), release()) and landmarker (detect(rgb, ts_ms), close()) are injectable; without
    them the model is checked first, then MediaPipe and the camera open here, on the calling (main) thread. A
    failure logs once and leaves the camera unavailable (latest() None); there is no 30 s retry yet."""

    def __init__(self, cfg, size: tuple[int, int], clock: Callable[[], float] = time.monotonic, *,
                 calibration: Calibration | None = None, model_path: Path | None = None, capture=None,
                 landmarker=None, start: bool = True):
        super().__init__(clock=clock)
        self.size, self.mirror = size, cfg.mirror
        self.period = 1.0 / cfg.camera_fps
        self.tracker = BodyTracker(calibration)
        self._cap, self._landmarker = capture, landmarker
        self._next_due: float | None = None
        self._last_ts = -1
        if model_path is None:
            from arcade.main import MODEL_PATH as model_path   # here: arcade.main will import the sources (X2)
        try:
            if self._landmarker is None:
                if not Path(model_path).exists():
                    raise FileNotFoundError(f"pose model missing at {model_path}")
                self._landmarker = Landmarker(Path(model_path))
            if self._cap is None:
                self._cap = open_capture(cfg.camera_index)
        except Exception as e:
            log.warning("mediapipe camera unavailable: %s", e)
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
        for landmarks in self._landmarker.detect(frame[:, :, ::-1], ts):     # BGR to RGB
            kps = landmarks_to_keypoints(landmarks)
            if self.mirror:
                kps = mirror_keypoints(kps)
            detections.append((box_of(kps), kps))
        return (capture_t, self.tracker.update(detections, capture_t), (), None)

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
        if self._landmarker is not None:
            self._landmarker.close()
