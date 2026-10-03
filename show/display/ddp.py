from __future__ import annotations

import logging
import socket
import struct

import numpy as np

log = logging.getLogger(__name__)

DDP_PORT = 4048
MAX_DATA = 1440
FLAG_VERSION1 = 0x40
FLAG_PUSH = 0x01
DATA_TYPE_RGB8 = 0x0B   # RGB, 8 bits per channel
DEST_DEFAULT = 0x01


def packets(data: bytes, seq: int) -> list[bytes]:
    out = []
    total = len(data)
    for off in range(0, total, MAX_DATA):
        chunk = data[off : off + MAX_DATA]
        last = off + len(chunk) >= total
        flags = FLAG_VERSION1 | (FLAG_PUSH if last else 0)
        header = struct.pack("!BBBBIH", flags, seq & 0x0F, DATA_TYPE_RGB8, DEST_DEFAULT, off, len(chunk))
        out.append(header + chunk)
    return out


class DDPDisplay:
    """Sends frames unscaled; the panel brightness is Falcon Player's output setting."""

    def __init__(self, width: int, height: int, host: str, port: int = DDP_PORT, sock=None):
        self.width, self.height = width, height
        self.addr = (host, port)
        self.sock = sock or socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.brightness = 1.0
        self._seq = 1
        self._brightness_logged = False

    def set_brightness(self, level: float) -> None:
        self.brightness = level
        if not self._brightness_logged:
            self._brightness_logged = True
            log.info("DDP sends pixels unscaled; brightness %.2f is Falcon Player's setting", level)

    def push(self, frame: np.ndarray) -> None:
        if frame.dtype != np.uint8 or frame.shape != (self.height, self.width, 3):
            raise ValueError(f"frame {frame.shape} {frame.dtype} is not ({self.height}, {self.width}, 3) uint8")
        for packet in packets(np.ascontiguousarray(frame).tobytes(), self._seq):
            self.sock.sendto(packet, self.addr)
        self._seq = self._seq % 15 + 1

    def close(self, keep_picture: bool = False) -> None:   # keep_picture: the Colorlight hand-off, nothing here
        self.sock.close()
