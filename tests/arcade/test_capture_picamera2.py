"""The picamera2 capture (the Pi's ribbon cameras), against a fake Picamera2: no camera and no picamera2 here."""
import numpy as np
import pytest

from arcade.sources.capture_picamera2 import FORMAT, FRAME_RATE, READ_TIMEOUT, Picamera2Capture


class FakeCam:
    def __init__(self, given=None, fail_read=False, fail_stop=False):
        self.calls, self.given, self.fail_read, self.fail_stop = [], given, fail_read, fail_stop
        self.frame = np.zeros((480, 640, 3), np.uint8)
        self.frame[..., 0] = 200

    def create_video_configuration(self, main, controls):
        self.calls.append(("create", dict(main), dict(controls)))
        return {"main": dict(main), "controls": dict(controls)}

    def configure(self, config):
        self.calls.append("configure")
        self.config = config

    def camera_configuration(self):
        return {"main": self.given or self.config["main"]}

    def start(self):
        self.calls.append("start")

    def capture_array(self, name, wait=None):
        self.waits = getattr(self, "waits", []) + [wait]
        if self.fail_read:
            raise TimeoutError("no frame")
        self.calls.append(("capture", name))
        return self.frame

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
