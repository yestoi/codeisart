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
