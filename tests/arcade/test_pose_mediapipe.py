"""The MediaPipe camera (spec 6.1), with a fake capture and a fake landmarker: no real camera is opened."""
import threading
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from arcade.config import ArcadeConfig
from arcade.main import MODEL_PATH
from arcade.runner import _camera_result, _provides
from arcade.calibration import Calibration
from arcade.poses import POSES
from arcade.sensed import (CAMERA_INPUTS, LEFT_HIP, LEFT_SHOULDER, LEFT_WRIST, MIN_CONF, NOSE, RIGHT_ANKLE,
                           RIGHT_HIP, RIGHT_SHOULDER, RIGHT_WRIST, Keypoint)
from arcade.sources.actors import make_keypoints
from arcade.sources.blobs import WORK_SIZE, FrameFeatures
from arcade.sources.mirror import mirror_keypoints
import arcade.sources.pose_mediapipe as pm
from arcade.sources.pose_mediapipe import MP_TO_COCO, MediaPipeCamera, box_of, landmarks_to_keypoints
from arcade.sources.scenario import FRAME_SHAPE, RawRecord, encode_raw


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
    def __init__(self, clock=None, dt=0.0, frames=None, make=None):
        self.clock, self.dt, self.reads, self.released = clock, dt, 0, False
        self.frames, self.make = frames, make

    def read(self):
        self.reads += 1
        if self.clock is not None:
            self.clock.t += self.dt
        if self.frames is not None and self.reads > self.frames:
            return False, None
        if self.make is not None:
            return True, self.make(self.reads)
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


def camera(people=(), clock=None, dt=0.1, mirror=True, fps=10, frames=None, make=None, **kw):
    clock = clock or FakeClock()
    cfg = ArcadeConfig(camera_fps=fps, mirror=mirror, camera="mediapipe")
    cap, lmk = FakeCapture(clock, dt, frames, make), FakeLandmarker(people)
    cam = MediaPipeCamera(cfg, cfg.size, clock=clock, capture=cap, landmarker=lmk, start=False, **kw)
    return cam, cap, lmk, clock


def moving_light(reads):
    """The Mac's 640x480 BGR capture of a dark room and a red light that moves 8 px left in the camera a read (2 px
    in the 160x120 working frame: right on the mirrored wall)."""
    frame = np.full((480, 640, 3), 30, np.uint8)
    center = (400 - 8 * reads, 240)
    cv2.circle(frame, center, 24, (0, 0, 200), -1)
    cv2.circle(frame, center, 8, (255, 255, 255), -1)
    return frame


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
    assert len(bodies) == 1 and blobs == () and motion.shape == (64, 128) and not motion.any()


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


def detection(kps):
    return (box_of(kps), tuple(kps))


def with_hips(kps, conf):
    kps = list(kps)
    for i in (LEFT_HIP, RIGHT_HIP):
        kps[i] = Keypoint(kps[i].x, kps[i].y, conf)
    return tuple(kps)


def shifted(kps, dx=0.0, dy=0.0, only=None):
    return tuple(Keypoint(k.x + dx, k.y + dy, k.conf) if only is None or i in only else k
                 for i, k in enumerate(kps))


def test_duplicate_poses_are_merged_keeping_the_more_confident_hips():
    """C45: the model's duplicates put the noses 0.01 to 0.02 apart; one person comes out, the better hips kept."""
    low = with_hips(make_keypoints(0.5, 0.55, 0.6), 0.2)
    high = with_hips(shifted(make_keypoints(0.5, 0.55, 0.6), dx=0.015), 0.9)
    for dets in ([detection(low), detection(high)], [detection(high), detection(low)]):
        out = pm.merge_duplicates(dets)
        assert len(out) == 1 and out[0][1] == high


def test_a_tie_in_hip_confidence_keeps_the_earlier():
    a = make_keypoints(0.5, 0.55, 0.6)
    b = shifted(a, dx=0.015)
    assert pm.merge_duplicates([detection(a), detection(b)]) == [detection(a)]


def test_two_people_shoulder_to_shoulder_are_never_merged():
    """Shoulders touching: the centres one shoulder width apart, at the zone's smallest body (3 m) and at 2 m."""
    for h in (Calibration().min_height, 0.6):
        width = POSES["stand"][RIGHT_SHOULDER][0] * h - POSES["stand"][LEFT_SHOULDER][0] * h
        a = make_keypoints(0.5 - width / 2, 0.55, h)
        b = make_keypoints(0.5 + width / 2, 0.55, h)
        assert pm.merge_duplicates([detection(a), detection(b)]) == [detection(a), detection(b)], h


def test_a_child_in_front_of_an_adult_is_never_merged():
    adult = make_keypoints(0.5, 0.55, 0.6)
    child = shifted(shifted(adult, dx=0.03, only={NOSE}), dy=0.1, only={LEFT_SHOULDER, RIGHT_SHOULDER})
    assert pm.merge_duplicates([detection(adult), detection(child)]) == [detection(adult), detection(child)]


def test_a_pose_without_a_nose_or_a_shoulder_is_never_merged():
    a = make_keypoints(0.5, 0.55, 0.6)
    for i in (NOSE, LEFT_SHOULDER, RIGHT_SHOULDER):
        k = a[i]
        dim = tuple(Keypoint(k.x, k.y, MIN_CONF - 0.01) if j == i else p for j, p in enumerate(shifted(a, dx=0.01)))
        for dets in ([detection(a), detection(dim)], [detection(dim), detection(a)]):
            assert pm.merge_duplicates(dets) == dets, i


def test_merge_keeps_the_order_of_the_others():
    a, c = make_keypoints(0.2, 0.55, 0.6), make_keypoints(0.8, 0.55, 0.6)
    b = with_hips(make_keypoints(0.5, 0.55, 0.6), 0.5)
    b2 = with_hips(shifted(b, dx=0.01), 0.9)
    assert pm.merge_duplicates([detection(a), detection(b), detection(c), detection(b2)]) == [
        detection(a), detection(b2), detection(c)]


def test_step_gives_one_body_for_a_doubled_pose():
    one = person_landmarks()
    two = [SimpleNamespace(x=lm.x + 0.01, y=lm.y, visibility=lm.visibility) for lm in one]
    cam, *_ = camera([one, two])
    ids = set()
    for _ in range(20):
        _, bodies, _, _ = cam.step()
        assert len(bodies) == 1
        ids.add(bodies[0].id)
    assert len(ids) == 1


# ----- blobs and motion (M5's wiring, iteration 21) -----

def test_step_returns_blobs_and_motion():
    cam, *_ = camera([person_landmarks()], make=moving_light)     # 0.1 s a read at 10 fps: every capture is due
    _, _, first, motion = cam.step()
    assert len(first) == 1 and motion.shape == (64, 128) and not motion.any()
    _, bodies, (blob,), motion = cam.step()
    assert len(bodies) == 1
    assert blob.id == first[0].id == 1 and blob.vx > 0.0          # moving right on the mirrored wall
    assert blob.x < 0.5 and blob.color[0] > 200                   # camera x 0.6, mirrored as the keypoints
    assert motion.shape == (64, 128) and motion.any() and motion.mean() < 0.1


def test_features_use_the_wall_grid_and_the_sources_calibration():
    cal = Calibration(zone=(0.1, 0.2, 0.9, 0.8))
    cam, *_ = camera(calibration=cal)
    f = cam.features
    assert isinstance(f, FrameFeatures) and f.size == cam.size == (128, 64) and f.work == WORK_SIZE
    assert f.calibration is cal and cam.tracker.calibration is cal
    assert f.mirror is True and f.hide_still is True
    off, *_ = camera(mirror=False)
    assert off.features.mirror is False and off.features.calibration == Calibration()


def test_mediapipe_provides_every_camera_input():
    cam, *_ = camera()
    assert MediaPipeCamera.provides == CAMERA_INPUTS
    assert _provides(cam) == CAMERA_INPUTS                         # the runner's reading (C35)


def test_tap_gets_one_raw_record_per_due_capture():
    one = person_landmarks(right_hand_up=True)
    two = [SimpleNamespace(x=lm.x + 0.01, y=lm.y, visibility=lm.visibility) for lm in one]   # the model's double
    cam, cap, lmk, _ = camera([one, two], dt=1 / 30, fps=10, make=moving_light)   # one read in three is due
    assert cam.tap is None
    got = []
    cam.tap = lambda record: got.append((cap.reads, record))
    due = []
    for _ in range(12):
        before = len(got)
        result = cam.step()
        assert len(got) - before == (result is not None)         # none on a skipped frame
        if result is not None:
            due.append(result)
    assert 3 <= len(due) < 12 and len(got) == len(due) == len(lmk.calls)
    raw = mirror_keypoints(landmarks_to_keypoints(one))
    for (reads, record), (capture_t, *_) in zip(got, due):
        assert isinstance(record, RawRecord) and record.t == capture_t and record.samples.size == 0
        assert record.detections == ((box_of(raw), raw),)          # merged, mirrored, before the tracker
        shrunk = cv2.resize(moving_light(reads), WORK_SIZE, interpolation=cv2.INTER_AREA)
        assert record.frame.shape == FRAME_SHAPE and record.frame.dtype == np.uint8
        assert np.array_equal(record.frame, cv2.cvtColor(shrunk, cv2.COLOR_BGR2GRAY))   # grey and unflipped
        encode_raw(record)                                         # record --raw's writer takes it
    cam.tap = None
    steps = [cam.step() for _ in range(6)]
    assert any(r is not None for r in steps) and len(got) == len(due)   # none without a tap
    small, *_ = camera()                                           # the fake's 64x48 frame: still FRAME_SHAPE
    records = []
    small.tap = records.append
    small.step()
    assert len(records) == 1 and records[0].frame.shape == FRAME_SHAPE
    encode_raw(records[0])


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


def test_the_camera_opens_the_capture_the_config_names(monkeypatch):
    seen = []
    monkeypatch.setattr(pm, "open_capture", lambda index, kind="opencv": seen.append((index, kind)) or FakeCapture())
    cfg = ArcadeConfig(camera_index=1, capture="picamera2")
    cam = MediaPipeCamera(cfg, cfg.size, landmarker=FakeLandmarker(), start=False)
    assert seen == [(1, "picamera2")]
    cam.close()


def test_open_capture_picamera2_builds_the_picamera2_capture(monkeypatch):
    import arcade.sources.capture_picamera2 as cp

    built = []
    monkeypatch.setattr(cp, "Picamera2Capture", lambda size, index: built.append((size, index)) or "capture")
    assert pm.open_capture(2, "picamera2") == "capture" and built == [(pm.CAPTURE_SIZE, 2)]


def test_without_picamera2_the_camera_is_unavailable_and_says_so(monkeypatch, caplog):
    import sys

    monkeypatch.setitem(sys.modules, "picamera2", None)        # import picamera2 raises ImportError
    cfg = ArcadeConfig(capture="picamera2")
    cam = MediaPipeCamera(cfg, cfg.size, landmarker=FakeLandmarker())
    assert cam.available is False and cam.latest() is None
    assert "mediapipe camera unavailable" in caplog.text and "picamera2" in caplog.text
    cam.close()
