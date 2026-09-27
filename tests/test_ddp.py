import logging
import struct

import numpy as np
import pytest

from show.config import Config
from show.display import make_display
from show.display.ddp import DDPDisplay, packets


class FakeSocket:
    def __init__(self):
        self.sent = []

    def sendto(self, data, addr):
        self.sent.append((data, addr))

    def close(self):
        pass


def test_packets_split_and_flag_last():
    data = bytes(512 * 192 * 3)
    pk = packets(data, seq=3)
    assert len(pk) == 205
    flags, seq, dtype, dest, off, length = struct.unpack("!BBBBIH", pk[0][:10])
    assert (flags, seq, dtype, dest, off, length) == (0x40, 3, 0x0B, 1, 0, 1440)
    flags, _, _, _, off, length = struct.unpack("!BBBBIH", pk[-1][:10])
    assert flags == 0x41 and off == 204 * 1440 and length == 294912 - 204 * 1440
    assert sum(len(p) - 10 for p in pk) == len(data)


def test_push_does_not_scale_and_cycles_sequence():
    sock = FakeSocket()
    d = DDPDisplay(4, 1, "10.0.0.2", 4048, sock=sock)
    d.set_brightness(0.5)
    frame = np.full((1, 4, 3), 200, np.uint8)
    d.push(frame)
    data, addr = sock.sent[0]
    assert addr == ("10.0.0.2", 4048)
    assert data[10:13] == bytes([200, 200, 200])
    seqs = []
    for _ in range(16):
        d.push(frame)
        seqs.append(sock.sent[-1][0][1])
    assert seqs[0] == 2 and 15 in seqs and 0 not in seqs and seqs[-1] == 2


@pytest.mark.parametrize("frame", [np.zeros((1, 4, 3)), np.full((1, 4, 3), 300, np.int64),
                                   np.zeros((2, 8, 3), np.uint8), np.zeros((1, 4), np.uint8)],
                         ids=["float64", "int64", "wrong-size", "grey"])
def test_push_rejects_a_frame_that_is_not_uint8_rgb(frame):
    sock = FakeSocket()
    d = DDPDisplay(4, 1, "10.0.0.2", 4048, sock=sock)
    with pytest.raises(ValueError, match="frame"):
        d.push(frame)
    assert sock.sent == []


def test_make_display_ddp():
    d = make_display(Config(backend="ddp"))
    assert isinstance(d, DDPDisplay)
    d.close()


def test_ddp_brightness_logged_once(caplog):
    caplog.set_level(logging.INFO, logger="show.display.ddp")
    d = DDPDisplay(4, 1, "10.0.0.2", 4048, sock=FakeSocket())
    d.set_brightness(0.4)
    d.set_brightness(0.2)
    records = [r for r in caplog.records if "Falcon Player" in r.getMessage()]
    assert len(records) == 1 and d.brightness == 0.2
