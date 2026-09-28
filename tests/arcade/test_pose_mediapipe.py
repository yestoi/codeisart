"""The MediaPipe camera (spec 6.1), with a fake capture and a fake landmarker: no real camera is opened."""
import threading
from types import SimpleNamespace

import numpy as np
import pytest

from arcade.config import ArcadeConfig
from arcade.main import MODEL_PATH
from arcade.runner import _camera_result
from arcade.sensed import LEFT_SHOULDER, LEFT_WRIST, NOSE, RIGHT_ANKLE, RIGHT_WRIST
from arcade.sources.pose_mediapipe import MP_TO_COCO, MediaPipeCamera, box_of, landmarks_to_keypoints


def fake_landmarks():
    return [SimpleNamespace(x=i / 100, y=i / 50, visibility=0.9 if i != 15 else 0.1) for i in range(33)]


def person_landmarks(right_hand_up=False):
    """33 MediaPipe landmarks of a person facing the camera, in the UNFLIPPED frame: their right side is on the
    image's left (small x). Hip centre (0.5, 0.6), shoulders at y 0.35."""
    lm = [SimpleNamespace(x=0.5, y=0.5, visibility=0.0) for _ in range(33)]

    def put(i, x, y):
        lm[i] = SimpleNamespace(x=x, y=y, visibility=0.95)

    put(0, 0.5, 0.25)                                      # nose
    put(2, 0.52, 0.23), put(5, 0.48, 0.23), put(7, 0.54, 0.24), put(8, 0.46, 0.24)
    put(11, 0.58, 0.35), put(12, 0.42, 0.35)               # left shoulder on the image's right
    put(13, 0.60, 0.45), put(14, 0.40, 0.45 if not right_hand_up else 0.25)
    put(15, 0.60, 0.55), put(16, 0.40, 0.55 if not right_hand_up else 0.12)
    put(23, 0.55, 0.60), put(24, 0.45, 0.60)
    put(25, 0.55, 0.75), put(26, 0.45, 0.75), put(27, 0.55, 0.90), put(28, 0.45, 0.90)
    return lm


class FakeCapture:
    def __init__(self, clock=None, dt=0.0, frames=None):
        self.clock, self.dt, self.reads, self.released = clock, dt, 0, False
        self.frames = frames

    def read(self):
        self.reads += 1
        if self.clock is not None:
            self.clock.t += self.dt
        if self.frames is not None and self.reads > self.frames:
            return False, None
        frame = np.zeros((48, 64, 3), np.uint8)
        frame[..., 0] = 200                               # OpenCV's BGR: blue
        return True, frame

    def release(self):
        self.released = True


class FakeLandmarker:
    def __init__(self, people=()):
        self.people, self.calls, self.closed = list(people), [], False

    def detect(self, rgb, ts_ms):
        self.calls.append((rgb.shape, ts_ms))
        self.pixel = tuple(int(v) for v in rgb[0, 0])
        return self.people

    def close(self):
        self.closed = True


class FakeClock:
    def __init__(self, t=100.0):
        self.t = t

    def __call__(self):
        return self.t


def camera(people=(), clock=None, dt=0.1, mirror=True, fps=10, frames=None, **kw):
    clock = clock or FakeClock()
    cfg = ArcadeConfig(camera_fps=fps, mirror=mirror, camera="mediapipe")
    cap, lmk = FakeCapture(clock, dt, frames), FakeLandmarker(people)
    cam = MediaPipeCamera(cfg, cfg.size, clock=clock, capture=cap, landmarker=lmk, start=False, **kw)
    return cam, cap, lmk, clock


def test_landmark_mapping():
    kps = landmarks_to_keypoints(fake_landmarks())
    assert len(kps) == 17 and len(MP_TO_COCO) == 17
    assert kps[NOSE].x == 0.0
    assert kps[LEFT_SHOULDER].x == 0.11
    assert kps[LEFT_WRIST].x == 0.15 and kps[LEFT_WRIST].conf == 0.1
    assert kps[RIGHT_ANKLE].x == 0.28


def test_missing_visibility_counts_as_seen():
    lm = [SimpleNamespace(x=0.5, y=0.5, visibility=None) for _ in range(33)]
    assert all(k.conf == 1.0 for k in landmarks_to_keypoints(lm))


def test_box_ignores_low_confidence_points():
    kps = landmarks_to_keypoints(fake_landmarks())
    x0, y0, x1, y1 = box_of(kps)
    assert x0 == 0.0 and x1 == 0.28 and y1 == min(1.0, 0.56)
    none = box_of(tuple(k.__class__(k.x, k.y, 0.0) for k in kps))
    assert none == (0.0, 0.0, 0.0, 0.0)


def test_raised_right_hand_gives_right_wrist_x_over_half():
    """Unflipped landmarks through the parser and mirror_keypoints (spec 5): the right wrist lands at x > 0.5."""
    cam, *_ = camera([person_landmarks(right_hand_up=True)])
    cam.poll()
    _, (body,), _, _ = cam.latest()
    assert body.right_wrist.x > 0.5 and body.keypoints[LEFT_SHOULDER].x < 0.5
    assert body.raised_wrist == body.keypoints[RIGHT_WRIST]


def test_mirror_off_keeps_camera_x():
    cam, *_ = camera([person_landmarks(right_hand_up=True)], mirror=False)
    cam.poll()
    _, (body,), _, _ = cam.latest()
    assert body.right_wrist.x < 0.5


def test_capture_stamped_on_the_injected_clock_in_seconds():
    clock = FakeClock(1234.5)
    cam, cap, lmk, _ = camera([person_landmarks()], clock=clock, dt=0.0)
    cam.poll()
    got = cam.latest()
    assert got[0] == 1234.5 and isinstance(got[0], float)
    assert lmk.calls[0][1] == 1234500                     # detect_for_video's timestamp in ms
    assert lmk.calls[0][0] == (48, 64, 3)
    assert _camera_result(got, clock()) is not None       # the runner accepts it


def test_landmarker_gets_rgb():
    cam, cap, lmk, _ = camera([])
    cam.step()
    assert lmk.pixel == (0, 0, 200)


def test_latest_has_no_blobs_and_no_motion():
    cam, *_ = camera([person_landmarks()])
    cam.poll()
    capture_t, bodies, blobs, motion = cam.latest()
    assert len(bodies) == 1 and blobs == () and motion is None


def test_inference_paced_to_camera_fps():
    """A 30 fps capture read every frame (so the buffer never holds old frames), inference at 10 fps."""
    cam, cap, lmk, clock = camera([person_landmarks()], dt=1 / 30, fps=10)
    results = [cam.step() for _ in range(30)]
    assert cap.reads == 30
    assert 9 <= len(lmk.calls) <= 11
    assert sum(r is not None for r in results) == len(lmk.calls)
    stamps = [ts for _, ts in lmk.calls]
    assert stamps == sorted(set(stamps))                  # strictly increasing


def test_timestamps_strictly_increase_within_a_millisecond():
    """Captures 0.3 ms apart, all due: detect_for_video still gets strictly increasing whole milliseconds."""
    cam, cap, lmk, clock = camera([person_landmarks()], dt=0.0003, fps=5000)
    for _ in range(3):
        cam.step()
    stamps = [ts for _, ts in lmk.calls]
    assert len(stamps) == 3 and stamps == sorted(set(stamps))


def test_read_failure_kills_the_thread_and_the_camera_is_unavailable():
    cam, cap, lmk, clock = camera([person_landmarks()], frames=1)
    cam.start()
    cam._thread.join(2.0)
    assert not cam._thread.is_alive()
    assert cam.available is False and cam.latest() is None
    cam.close()
    assert cap.released and lmk.closed


def test_close_joins_before_release():
    alive = {}
    clock = FakeClock()
    cfg = ArcadeConfig(camera_fps=10)
    started = threading.Event()

    class Cap(FakeCapture):
        def read(self):
            started.set()
            threading.Event().wait(0.005)
            return super().read()

        def release(self):
            alive["cap"] = cam._thread.is_alive()

    class Lmk(FakeLandmarker):
        def close(self):
            alive["lmk"] = cam._thread.is_alive()

    cam = MediaPipeCamera(cfg, cfg.size, clock=clock, capture=Cap(clock, 0.01), landmarker=Lmk())
    assert started.wait(2.0)
    cam.close()
    assert alive == {"cap": False, "lmk": False}


def test_camera_without_model_is_unavailable(tmp_path):
    cfg = ArcadeConfig(camera_index=99)
    cam = MediaPipeCamera(cfg, cfg.size, model_path=tmp_path / "missing.task")
    assert cam.available is False and cam.latest() is None
    cam.close()


def test_default_model_is_the_doctors(tmp_path, monkeypatch, caplog):
    import arcade.main

    missing = tmp_path / "doctor.task"
    monkeypatch.setattr(arcade.main, "MODEL_PATH", missing)
    cfg = ArcadeConfig(camera_index=99)
    cam = MediaPipeCamera(cfg, cfg.size)
    assert cam.available is False and str(missing) in caplog.text
    cam.close()


def test_real_landmarker_runs_on_a_blank_frame():
    pytest.importorskip("mediapipe")
    if not MODEL_PATH.exists():
        pytest.skip(f"no model at {MODEL_PATH}")
    from arcade.sources.pose_mediapipe import Landmarker

    lmk = Landmarker(MODEL_PATH)
    try:
        assert lmk.detect(np.full((480, 640, 3), 96, np.uint8), 1) == []
        assert lmk.detect(np.full((480, 640, 3), 96, np.uint8), 2) == []
    finally:
        lmk.close()
