"""ColorlightDisplay: the facade on the steady sender. The sender runs by hand (tests.colorlight_fakes.Cranked)
in place of the child, on a fake clock; the socket is a fake. The child itself: tests/test_colorlight_child.py."""
import errno
import math
import socket
from types import SimpleNamespace

import numpy as np
import pytest

import show.display.colorlight as colorlight
from show.config import Config
from show.display import make_display
from show.display.colorlight import DEAD_S, RESTART_S, SAFE_BRIGHTNESS, START_S, ColorlightDisplay, stats_line
from show.display.colorlight_packets import sync_bytes
from show.display.colorlight_sender import CLOSE_FRAMES, ERRORS, PAUSE
from show.display.fake import FakeDisplay
from tests.colorlight_fakes import BRIGHTNESS, ROW, SYNC, Cranked, FakeClock, FakeSocket, bursts, kinds, row_pixels

W, H = 128, 32
PRIME = H                      # packets of the first burst (the rows): no sync before a whole frame
FIRST_ROW = PRIME + 2          # burst 2's first row: after its one sync


def display(sock=None, clock=None, cranked=None, **kw):
    sock, clock = sock or FakeSocket(), clock or FakeClock()
    c = cranked or Cranked(sock, clock)
    d = ColorlightDisplay(W, H, "eth0", sock=sock, launch=c.launch, clock=clock.seconds, sleep=c.sleep, **kw)
    return d, sock, clock, c


def black():
    return np.zeros((H, W, 3), np.uint8)


def red():
    f = black()
    f[..., 0] = 200
    return f


def test_it_opens_dark_at_the_safe_brightness_and_the_first_sync_carries_it():
    d, sock, clock, c = display()
    assert d.brightness == SAFE_BRIGHTNESS == 0.4 and c.launches == 1
    c.crank(3)
    out = bursts(sock.sent)
    assert kinds(out[0]) == [BRIGHTNESS] * 2 + [ROW] * H                       # the prime, before any push
    assert [p for p in out[1] if p[12] == SYNC] == [sync_bytes(102)] * SYNC_REPS
    assert [p for p in out[1] if p[12] == BRIGHTNESS] == [brightness_bytes(102)] * 2
    assert not any(row_pixels(p, W).any() for b in out for p in b if p[12] == ROW)
    d.close()


def test_push_copies_the_frame_and_the_wire_shows_it_bgr_until_the_next_push():
    d, sock, clock, c = display()
    frame = red()
    d.push(frame)
    frame[...] = 7                                                              # the caller's array, changed after
    sock.sent.clear()
    c.crank(4)
    assert len(bursts(sock.sent)) == 4
    for burst in bursts(sock.sent):
        assert all((row_pixels(p, W) == (0, 0, 200)).all() for p in burst if p[12] == ROW)
    d.close()


def test_set_brightness_reaches_every_packet_and_nan_is_dark():
    d, sock, clock, c = display()
    d.set_brightness(0.2)
    assert d.brightness == 0.2
    sock.sent.clear()
    c.crank(2)
    assert [p[35] for p in sock.sent if p[12] == SYNC] == [51] * 4              # two bursts, two syncs each
    assert [p[13] for p in sock.sent if p[12] == BRIGHTNESS] == [51] * 4
    d.set_brightness(math.nan)
    sock.sent.clear()
    c.crank(2)
    assert [p[35] for p in sock.sent if p[12] == SYNC] == [0] * 4
    assert [p[13] for p in sock.sent if p[12] == BRIGHTNESS] == [0] * 4
    d.close()


def test_push_rejects_a_frame_of_the_wrong_shape_or_type_and_sends_nothing_new():
    d, sock, clock, c = display()
    d.push(red())
    with pytest.raises(ValueError, match="frame shape"):
        d.push(np.zeros((W, H, 3), np.uint8))
    for frame in (np.zeros((H, W, 3)), np.full((H, W, 3), 300, np.int64), np.zeros((H, W, 4), np.uint8)):
        with pytest.raises(ValueError, match="frame"):
            d.push(frame)
    sock.sent.clear()
    c.crank(2)
    rows = [p for p in sock.sent if p[12] == ROW]
    assert rows and all((row_pixels(p, W) == (0, 0, 200)).all() for p in rows)
    d.close()


def test_a_failed_send_comes_back_from_the_next_push_which_stores_nothing():
    sock = FakeSocket(fail={FIRST_ROW: OSError(errno.ENETDOWN, "Network is down")})
    d, sock, clock, c = display(sock)
    c.crank(2)                                                                  # burst 2's first row fails
    assert d.slot.h[PAUSE] == 1
    with pytest.raises(OSError, match="send failed") as e:
        d.push(red())
    assert e.value.errno == errno.ENETDOWN
    assert d.slot.h[PAUSE] == 1 and d.slot.h[ERRORS] == 1
    n = len(sock.sent)
    c.crank(3)
    assert len(sock.sent) == n                                                  # paused: the wall keeps its picture
    d.push(red())                                                               # the hold's repush: the restart
    assert d.slot.h[PAUSE] == 0
    c.crank(2)
    out = bursts(sock.sent[n:])
    assert kinds(out[0]) == [BRIGHTNESS] * 2 + [ROW] * H and out[1][0][12] == SYNC
    assert all((row_pixels(p, W) == (0, 0, 200)).all() for p in out[1] if p[12] == ROW)
    d.close()


def test_a_dead_sender_raises_then_is_restarted_after_a_second_starting_dark():
    d, sock, clock, c = display()
    d.push(red())
    c.crank(2)
    c.alive = False                                                             # the child died
    with pytest.raises(OSError, match="not running"):
        d.push(red())
    clock.sleep(RESTART_S / 2)
    with pytest.raises(OSError, match="not running"):
        d.push(red())
    clock.sleep(RESTART_S)
    sock.sent.clear()
    d.push(red())                                                               # restarted, and this frame taken
    assert c.launches == 2 and d.restarts == 1 and c.alive
    c.crank(2)
    out = bursts(sock.sent)
    assert kinds(out[0]) == [BRIGHTNESS] * 2 + [ROW] * H                       # the prime, and it is not black:
    assert all((row_pixels(p, W) == (0, 0, 200)).all() for b in out for p in b if p[12] == ROW)   # the slot's frame
    d.close()


def test_a_restart_resumes_on_the_slots_last_frame_not_dark(caplog):
    d, sock, clock, c = display()
    d.push(red())
    c.crank(2)
    c.alive = False
    with pytest.raises(OSError, match="not running"):                          # the death is noticed here
        d.push(red())
    clock.sleep(RESTART_S * 2)
    sock.sent.clear()
    with caplog.at_level("WARNING", logger="show.display.colorlight"):
        d.push(np.full((H, W, 3), 50, np.uint8))                                # the restart takes this frame...
    c.crank(1)
    first, second = bursts(sock.sent)[:2]                                       # the start's prime, then one burst
    assert all((row_pixels(p, W) == (0, 0, 200)).all() for p in first if p[12] == ROW)   # ...after the last frame,
    assert all((row_pixels(p, W) == 50).all() for p in second if p[12] == ROW)          # and nothing black
    assert sum("real-time priority" in r.message for r in caplog.records) == 1  # once: the first start, not this
    d.close()


def test_close_with_a_dead_child_starts_a_fresh_one_to_drain_black():
    d, sock, clock, c = display()
    d.push(red())
    c.crank(2)
    c.alive = False                                                             # died, or was killed, before the close
    sock.sent.clear()
    d.close()
    out = bursts(sock.sent)
    assert c.launches == 2 and len(out) >= CLOSE_FRAMES
    assert not any(row_pixels(p, W).any() for b in out for p in b if p[12] == ROW)
    assert not c.alive and sock.closed == 1


def test_push_does_not_clear_a_pause_from_a_failure_it_has_not_seen():
    d, sock, clock, c = display()
    slot, write = d.slot, d.slot.write

    def write_as_the_child_fails(frame):                                        # the failure lands during the push
        slot.h[ERRORS] += 1
        slot.h[PAUSE] = 1
        write(frame)

    slot.write = write_as_the_child_fails
    d.push(red())
    assert slot.h[PAUSE] == 1                                                   # still paused: the hold comes next
    slot.write = write
    with pytest.raises(OSError, match="send failed"):
        d.push(red())
    d.close()


def test_a_child_that_stops_beating_counts_as_dead():
    d, sock, clock, c = display()
    c.beats = 0                                                                 # alive, but never ticks again
    d.push(red())
    clock.sleep(DEAD_S)
    with pytest.raises(OSError, match="not running"):
        d.push(red())
    d.close()


def test_a_child_that_never_starts_is_an_error_at_open():
    sock, clock = FakeSocket(), FakeClock()
    c = Cranked(sock, clock, beats=0)
    with pytest.raises(OSError, match="did not start"):
        ColorlightDisplay(W, H, "eth0", sock=sock, launch=c.launch, clock=clock.seconds, sleep=c.sleep)
    assert clock.seconds() >= START_S and sock.closed == 1


def test_close_drains_black_for_a_second_stops_after_a_whole_burst_and_closes_the_socket():
    d, sock, clock, c = display()
    d.push(red())
    c.crank(3)
    sock.sent.clear()
    slot = d.slot
    d.close()
    out = bursts(sock.sent)
    assert len(out) >= CLOSE_FRAMES
    assert not any(row_pixels(p, W).any() for p in out[-1] if p[12] == ROW)
    assert sock.sent[-1][12] == ROW and sock.sent[-1][14] == H - 1
    assert not c.alive and sock.closed == 1 and slot._mm is None
    d.close()                                                                   # twice: harmless
    assert sock.closed == 1


def test_close_after_the_child_died_closes_the_socket_and_the_slot():
    d, sock, clock, c = display()
    c.alive = False
    slot = d.slot
    d.close()
    assert sock.closed == 1 and slot._mm is None


def test_close_in_a_pause_restarts_the_stream_on_black():
    sock = FakeSocket(fail={FIRST_ROW: OSError(errno.EIO, "io")})
    d, sock, clock, c = display(sock)
    c.crank(2)
    assert d.slot.h[PAUSE] == 1
    n = len(sock.sent)
    d.close()
    out = bursts(sock.sent[n:])
    assert len(out) >= CLOSE_FRAMES and not any(row_pixels(p, W).any() for b in out for p in b if p[12] == ROW)


def test_stats_and_the_line_for_the_log():
    d, sock, clock, c = display()
    c.crank(5)                                                                  # the start's prime, then five
    s = d.stats()
    assert s["frames"] == 5 and s["restarts"] == 0 and s["rt"] is False
    line = stats_line(d)
    assert "5 frames" in line and "real-time no" in line
    assert stats_line(FakeDisplay()) is None
    d.close()
    assert stats_line(d) is None                                                # closed: no line, no exception


def test_the_raw_socket_bypasses_the_queue_before_it_binds(monkeypatch):
    calls = []

    class Raw(FakeSocket):
        def __init__(self, family, kind):
            super().__init__()
            calls.append(("socket", family, kind))

        def setsockopt(self, level, option, value):
            calls.append(("setsockopt", level, option, value))

        def bind(self, address):
            calls.append(("bind", address))

    monkeypatch.setattr(socket, "AF_PACKET", 17, raising=False)
    monkeypatch.setattr(socket, "socket", Raw)
    sock = colorlight._open_raw_socket("eth0")
    assert calls == [("socket", 17, socket.SOCK_RAW), ("setsockopt", 263, 20, 1), ("bind", ("eth0", 0))]
    assert isinstance(sock, Raw)


def test_without_raw_sockets_a_clear_error(monkeypatch):
    monkeypatch.delattr(socket, "AF_PACKET", raising=False)
    with pytest.raises(OSError, match="Linux raw sockets"):
        ColorlightDisplay(W, H, "eth0")


def test_raw_socket_permission_error_names_cap_net_raw(monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(socket, "AF_PACKET", 17, raising=False)
    monkeypatch.setattr(socket, "socket", denied)
    with pytest.raises(PermissionError, match="CAP_NET_RAW"):
        ColorlightDisplay(W, H, "eth0")


def test_failed_bind_closes_the_socket_and_names_the_interface(monkeypatch):
    class Unbindable(FakeSocket):
        def __init__(self, *args):
            super().__init__()
            opened.append(self)

        def setsockopt(self, *args):
            pass

        def bind(self, address):
            raise OSError(19, "No such device")

    opened = []
    monkeypatch.setattr(socket, "AF_PACKET", 17, raising=False)
    monkeypatch.setattr(socket, "socket", Unbindable)
    with pytest.raises(OSError, match="eth7: No such device"):
        ColorlightDisplay(W, H, "eth7")
    assert len(opened) == 1 and opened[0].closed == 1


def test_width_that_cannot_split_evenly_rejected():
    with pytest.raises(ValueError, match="width 257"):
        ColorlightDisplay(257, 4, "eth0", sock=FakeSocket())


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


def test_pause_stops_the_stream_until_the_next_push():
    d, sock, clock, c = display()
    d.push(red())
    c.crank(2)
    d.pause()                                                                   # the production stop: the flag
    n = len(sock.sent)
    c.crank(5)
    assert len(sock.sent) == n and d.slot.h[PAUSE] == 1                         # nothing on the wire, no error
    d.push(red())                                                               # a push resumes it: a prime first
    c.crank(2)
    assert kinds(bursts(sock.sent[n:])[0]) == [BRIGHTNESS] * 2 + [ROW] * H
    d.close()


def test_the_cap_net_raw_hint_keeps_cap_sys_nice(monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(socket, "AF_PACKET", 17, raising=False)
    monkeypatch.setattr(socket, "socket", denied)
    with pytest.raises(PermissionError, match="cap_net_raw,cap_sys_nice"):     # setcap clears the ambient set:
        ColorlightDisplay(W, H, "eth0")                                         # both, or the sender loses its priority


def test_close_with_a_hung_child_replaces_it_to_drain_black():
    d, sock, clock, c = display()
    d.push(red())
    c.crank(2)
    c.beats = 0                                                                 # alive, hung: no beat from now on
    d.push(red())                                                               # the last look that saw it beat
    clock.sleep(DEAD_S)
    sock.sent.clear()
    launch = c.launch
    d._launch = lambda slot, sock: (setattr(c, "beats", None), launch(slot, sock))[1]   # a fresh child beats
    d.close()
    out = bursts(sock.sent)
    assert c.launches == 2 and len(out) >= CLOSE_FRAMES
    assert not any(row_pixels(p, W).any() for b in out for p in b if p[12] == ROW)
