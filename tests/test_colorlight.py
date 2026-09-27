import socket
from types import SimpleNamespace

import numpy as np
import pytest

import show.display.colorlight as colorlight
from show.config import Config
from show.display import make_display
from show.display.colorlight import (DST_MAC, SRC_MAC, ColorlightDisplay, brightness_packet,
                                     frame_packet, row_packets)


class FakeSocket:
    """Stands in for the AF_PACKET socket, which exists only on Linux."""

    def __init__(self):
        self.sent = []
        self.closed = False

    def send(self, data):
        self.sent.append(bytes(data))  # copy: push() reuses its packet buffer
        return len(self.sent[-1])

    def close(self):
        self.closed = True


def test_row_packets_chunk_512_pixels_into_two():
    pixels = np.zeros((512, 3), np.uint8)
    pixels[0] = (255, 0, 0)          # red pixel at column 0
    pixels[256] = (0, 0, 255)        # blue pixel at column 256
    pk = row_packets(5, pixels)
    assert len(pk) == 2
    header = pk[0][:14]
    assert header[:6] == DST_MAC and header[6:12] == SRC_MAC and header[12:14] == b"\x55\x00"
    payload = pk[0][14:]
    assert payload[:7] == bytes([5, 0, 0, 1, 0, 0x08, 0x88])          # row 5, offset 0, count 256
    assert payload[7:10] == bytes([255, 0, 0])                        # RGB order, as Falcon Player
    payload2 = pk[1][14:]
    assert payload2[:7] == bytes([5, 1, 0, 1, 0, 0x08, 0x88])         # offset 256
    assert payload2[7:10] == bytes([0, 0, 255])
    assert all(len(p) == 14 + 7 + 256 * 3 for p in pk)


def test_row_above_255_sets_ethertype_low_byte():
    pk = row_packets(300, np.zeros((8, 3), np.uint8))
    assert pk[0][12:14] == b"\x55\x01" and pk[0][14] == 300 & 0xFF


def test_frame_packet_matches_falcon_player():
    fp = frame_packet(0.5)
    assert fp[:12] == DST_MAC + SRC_MAC and fp[12:14] == b"\x01\x07" and len(fp) == 112
    assert fp[35] == 127 and fp[36] == 0x05 and fp[38:41] == bytes([127, 127, 127])
    assert sum(fp[14:]) == 127 * 4 + 5


def test_brightness_packet_matches_falcon_player():
    bp = brightness_packet(0.4)
    assert bp[:12] == DST_MAC + SRC_MAC and len(bp) == 77
    assert bp[12] == 0x0A and bp[13:17] == bytes([102, 102, 102, 0xFF])
    assert not any(bp[17:])
    assert brightness_packet(1.7)[13] == 255 and brightness_packet(-1.0)[13] == 0


def test_push_sends_frame_packet_then_rows():
    sock = FakeSocket()
    d = ColorlightDisplay(512, 4, "eth0", sock=sock)
    d.set_brightness(0.2)
    assert sock.sent[-1][12] == 0x0A
    d.push(np.zeros((4, 512, 3), np.uint8))
    pushed = sock.sent[1:]
    assert len(pushed) == 1 + 4 * 2
    assert pushed[0][12:14] == b"\x01\x07" and pushed[0][35] == 51
    assert all(p[12] == 0x55 for p in pushed[1:])


@pytest.mark.parametrize("width,height", [(128, 32), (64, 64), (512, 4)])
def test_push_matches_reference_encoder(width, height):
    rng = np.random.default_rng(width * height)
    sock = FakeSocket()
    d = ColorlightDisplay(width, height, "eth0", sock=sock)
    for _ in range(2):  # the second push must overwrite the first push's pixels
        frame = rng.integers(0, 256, (height, width, 3), dtype=np.uint8)
        sock.sent.clear()
        d.push(frame)
        expected = [p for y in range(height) for p in row_packets(y, frame[y])]
        assert sock.sent[1:] == expected


def test_push_rejects_a_frame_of_the_wrong_shape():
    d = ColorlightDisplay(64, 64, "eth0", sock=FakeSocket())
    with pytest.raises(ValueError, match="frame shape"):
        d.push(np.zeros((32, 128, 3), np.uint8))   # same byte count, wrong layout


def test_width_that_cannot_split_evenly_rejected():
    with pytest.raises(ValueError, match="width 257"):
        ColorlightDisplay(257, 4, "eth0", sock=FakeSocket())


def test_colorlight_set_brightness_sends_packet():
    sock = FakeSocket()
    d = ColorlightDisplay(128, 32, "eth0", sock=sock)
    d.set_brightness(0.4)
    assert sock.sent[-1] == brightness_packet(0.4)
    assert d.brightness == 0.4
    d.push(np.zeros((32, 128, 3), np.uint8))
    assert sock.sent[1] == frame_packet(0.4)
    d.close()
    assert sock.closed


def test_without_raw_sockets_a_clear_error(monkeypatch):
    monkeypatch.delattr(socket, "AF_PACKET", raising=False)
    with pytest.raises(OSError, match="Linux raw sockets"):
        ColorlightDisplay(128, 32, "eth0")


class Recorder:
    """Replaces ColorlightDisplay in make_display tests: raw sockets are Linux-only."""

    def __init__(self, width, height, iface, sock=None):
        self.args = (width, height, iface)


def test_make_display_reads_iface(monkeypatch):
    monkeypatch.setattr(colorlight, "ColorlightDisplay", Recorder)
    cfg = SimpleNamespace(width=128, height=32, backend="colorlight", sdl_scale=8,
                          ddp_host="127.0.0.1", ddp_port=4048, iface="eth9")
    assert make_display(cfg).args == (128, 32, "eth9")


def test_make_display_falls_back_to_colorlight_iface(monkeypatch):
    monkeypatch.setattr(colorlight, "ColorlightDisplay", Recorder)
    assert make_display(Config(backend="colorlight", colorlight_iface="eth3")).args == (512, 192, "eth3")
