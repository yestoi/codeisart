import math
import socket
from types import SimpleNamespace

import numpy as np
import pytest

import show.display.colorlight as colorlight
from show.config import Config
from show.display import make_display
from show.display.colorlight import (BRIGHTNESS_EVERY, DST_MAC, SAFE_BRIGHTNESS, SRC_MAC, ColorlightDisplay,
                                     brightness_packet, frame_packet, row_packets)


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


@pytest.mark.parametrize("width,height", [(128, 32), (64, 64), (512, 4), (384, 4)])
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


@pytest.mark.parametrize("frame", [np.zeros((32, 128, 3)), np.full((32, 128, 3), 300, np.int64),
                                   np.zeros((32, 128, 4), np.uint8), np.zeros((32, 128), np.uint8)],
                         ids=["float64", "int64", "rgba", "grey"])
def test_push_rejects_a_frame_that_is_not_uint8_rgb(frame):
    sock = FakeSocket()
    d = ColorlightDisplay(128, 32, "eth0", sock=sock)
    with pytest.raises(ValueError, match="frame"):
        d.push(frame)
    assert sock.sent == []   # nothing reaches the wall, not even the frame packet


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


def test_starts_at_the_safe_brightness_until_told():
    sock = FakeSocket()
    d = ColorlightDisplay(128, 32, "eth0", sock=sock)
    assert d.brightness == SAFE_BRIGHTNESS == 0.4
    d.push(np.zeros((32, 128, 3), np.uint8))
    assert sock.sent[0] == frame_packet(0.4) and sock.sent[0][35] == 102   # never 255 before set_brightness
    assert ColorlightDisplay(128, 32, "eth0", sock=FakeSocket(), brightness=0.1).brightness == 0.1


def test_brightness_packet_resent_every_3_pushes():
    sock = FakeSocket()
    d = ColorlightDisplay(64, 64, "eth0", sock=sock)   # never told a level: resends the safe one
    frame = np.zeros((64, 64, 3), np.uint8)
    per_push = 1 + 64
    assert BRIGHTNESS_EVERY == 3
    d.push(frame)
    d.push(frame)
    assert len(sock.sent) == 2 * per_push and all(p[12] != 0x0A for p in sock.sent)
    d.push(frame)
    third = sock.sent[2 * per_push:]
    assert third[0] == frame_packet(SAFE_BRIGHTNESS)
    assert third[1] == brightness_packet(SAFE_BRIGHTNESS)   # after the frame packet, before the rows
    assert len(third) == per_push + 1 and all(p[12] == 0x55 for p in third[2:])
    d.set_brightness(0.2)   # sending a level restarts the count
    sock.sent.clear()
    for _ in range(6):
        d.push(frame)
    resent = [i for i, p in enumerate(sock.sent) if p[12] == 0x0A]
    assert resent == [2 * per_push + 1, 5 * per_push + 2]
    assert all(sock.sent[i] == brightness_packet(0.2) for i in resent)


def test_set_brightness_restarts_the_resend_count():
    sock = FakeSocket()
    d = ColorlightDisplay(64, 64, "eth0", sock=sock)
    frame = np.zeros((64, 64, 3), np.uint8)
    d.push(frame)
    d.push(frame)
    d.set_brightness(0.2)   # two pushes in: without the restart the next push would resend
    sock.sent.clear()
    d.push(frame)
    d.push(frame)
    assert all(p[12] != 0x0A for p in sock.sent)
    d.push(frame)
    assert [p for p in sock.sent if p[12] == 0x0A] == [brightness_packet(0.2)]


def test_nan_or_negative_brightness_fails_dark():
    sock = FakeSocket()
    d = ColorlightDisplay(128, 32, "eth0", sock=sock, brightness=math.nan)
    d.push(np.zeros((32, 128, 3), np.uint8))
    assert sock.sent[0][35] == 0
    d.set_brightness(math.nan)
    assert sock.sent[-1] == brightness_packet(0.0)


def test_without_raw_sockets_a_clear_error(monkeypatch):
    monkeypatch.delattr(socket, "AF_PACKET", raising=False)
    with pytest.raises(OSError, match="Linux raw sockets"):
        ColorlightDisplay(128, 32, "eth0")


def test_raw_socket_permission_error_names_cap_net_raw(monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(socket, "AF_PACKET", 17, raising=False)   # present on Linux, added here for the Mac
    monkeypatch.setattr(socket, "socket", denied)
    with pytest.raises(PermissionError, match="CAP_NET_RAW"):
        ColorlightDisplay(128, 32, "eth0")


def test_failed_bind_closes_the_socket_and_names_the_interface(monkeypatch):
    class Unbindable(FakeSocket):
        def __init__(self, *args):
            super().__init__()
            opened.append(self)

        def bind(self, address):
            raise OSError(19, "No such device")

    opened = []
    monkeypatch.setattr(socket, "AF_PACKET", 17, raising=False)
    monkeypatch.setattr(socket, "socket", Unbindable)
    with pytest.raises(OSError, match="eth7: No such device"):
        ColorlightDisplay(128, 32, "eth7")
    assert len(opened) == 1 and opened[0].closed


class Recorder:
    """Replaces ColorlightDisplay in make_display tests: raw sockets are Linux-only."""

    def __init__(self, width, height, iface, sock=None, **kwargs):
        self.args = (width, height, iface)
        self.kwargs = kwargs


def test_make_display_reads_iface(monkeypatch):
    monkeypatch.setattr(colorlight, "ColorlightDisplay", Recorder)
    cfg = SimpleNamespace(width=128, height=32, backend="colorlight", sdl_scale=8,
                          ddp_host="127.0.0.1", ddp_port=4048, iface="eth9")
    assert make_display(cfg).args == (128, 32, "eth9")


def test_make_display_falls_back_to_colorlight_iface(monkeypatch):
    monkeypatch.setattr(colorlight, "ColorlightDisplay", Recorder)
    assert make_display(Config(backend="colorlight", colorlight_iface="eth3")).args == (512, 192, "eth3")


@pytest.mark.parametrize("cfg", [SimpleNamespace(width=128, height=32, backend="colorlight", sdl_scale=8,
                                                 ddp_host="127.0.0.1", ddp_port=4048, iface=""),
                                 Config(backend="colorlight", colorlight_iface="")],
                         ids=["arcade-shape-empty-iface", "daemon-empty-colorlight-iface"])
def test_make_display_without_an_interface_is_a_clear_error(monkeypatch, cfg):
    monkeypatch.setattr(colorlight, "ColorlightDisplay", Recorder)
    with pytest.raises(ValueError, match="iface"):
        make_display(cfg)


def test_make_display_starts_at_the_configured_brightness(monkeypatch):
    monkeypatch.setattr(colorlight, "ColorlightDisplay", Recorder)
    arcade = SimpleNamespace(width=128, height=32, backend="colorlight", sdl_scale=8, ddp_host="127.0.0.1",
                             ddp_port=4048, iface="eth9", brightness=0.25)
    assert make_display(arcade).kwargs == {"brightness": 0.25}
    daemon = Config(backend="colorlight", colorlight_iface="eth3", brightness=0.9, brightness_cap=0.4)
    assert make_display(daemon).kwargs == {"brightness": 0.4}             # the daemon's capped level
    bare = SimpleNamespace(width=128, height=32, backend="colorlight", sdl_scale=8, ddp_host="127.0.0.1",
                           ddp_port=4048, iface="eth9")
    assert make_display(bare).kwargs == {"brightness": SAFE_BRIGHTNESS}
