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
