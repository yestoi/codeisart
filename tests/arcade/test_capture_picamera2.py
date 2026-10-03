"""The picamera2 capture (the Pi's ribbon cameras), against a fake Picamera2: no camera and no picamera2 here."""
import numpy as np
import pytest

from arcade.sources.capture_picamera2 import FORMAT, FRAME_RATE, READ_TIMEOUT, Picamera2Capture


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


def test_opens_at_the_size_and_format_and_reads_bgr_frames():
    cam = FakeCam()
    cap = Picamera2Capture((640, 480), camera=cam)
    assert cam.calls == [("create", {"size": (640, 480), "format": FORMAT}, {"FrameRate": FRAME_RATE}),
                         "configure", "start"]
    ok, frame = cap.read()
    assert ok and frame.shape == (480, 640, 3) and tuple(frame[0, 0]) == (200, 0, 0)   # as OpenCV's BGR: blue
    assert cam.calls[-1] == ("capture", "main")


@pytest.mark.parametrize("given", [{"size": (656, 480), "format": "RGB888"}, {"size": (640, 480), "format": "XBGR8888"}])
def test_another_size_or_format_is_refused_and_the_camera_closed(given):
    cam = FakeCam(given=given)
    with pytest.raises(RuntimeError, match="picamera2 gave"):
        Picamera2Capture((640, 480), camera=cam)
    assert "start" not in cam.calls and cam.calls[-2:] == ["stop", "close"]


def test_a_read_waits_at_most_the_timeout_and_a_failed_one_is_not_ok(caplog):
    cam = FakeCam(fail_read=True)
    cap = Picamera2Capture((640, 480), camera=cam)
    assert cap.read() == (False, None) and cam.waits == [READ_TIMEOUT]
    assert "picamera2 read failed" in caplog.text and "Traceback" not in caplog.text


def test_no_camera_attached_says_so_with_the_ribbon_hint(monkeypatch):
    import sys
    import types

    def none_attached(index):
        raise IndexError("list index out of range")

    monkeypatch.setitem(sys.modules, "picamera2", types.SimpleNamespace(Picamera2=none_attached))
    with pytest.raises(RuntimeError, match="no camera 0.*ribbon"):
        Picamera2Capture((640, 480))


def test_release_stops_and_closes_once_and_never_raises():
    cam = FakeCam(fail_stop=True)
    cap = Picamera2Capture((640, 480), camera=cam)
    cap.release()
    cap.release()
    assert cam.calls.count("stop") == 1 and cam.calls.count("close") == 1


def test_importing_the_module_loads_no_picamera2():
    import sys

    assert "picamera2" not in sys.modules


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
