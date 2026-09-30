"""Fakes for the colorlight driver's tests: a socket that keeps what it was sent, a clock that only moves when
read or slept, and the sender run by hand in place of the child."""
import numpy as np

from show.display.colorlight_packets import ROW_HEADER_LEN

SYNC, BRIGHTNESS, ROW = 0x01, 0x0A, 0x55


class FakeSocket:
    """Stands in for the AF_PACKET socket, which exists only on Linux. `fail` maps a send number (from 1) to the
    OSError to raise instead of keeping the packet; `hook(n, packet)` runs before send n is kept."""

    def __init__(self, fail=None, hook=None):
        self.sent, self.calls, self.closed = [], 0, 0
        self.fail, self.hook = fail or {}, hook

    def send(self, data):
        self.calls += 1
        if self.hook is not None:
            self.hook(self.calls, bytes(data))
        if self.calls in self.fail:
            raise self.fail[self.calls]
        self.sent.append(bytes(data))       # a copy: the sender reuses its packet buffers
        return len(self.sent[-1])

    def close(self):
        self.closed += 1


class FakeClock:
    """Nanoseconds that move `step_ns` at every read and by the whole sleep at every sleep, so a busy-wait ends."""

    def __init__(self, step_ns=10_000, start_ns=1_000_000_000):
        self.t, self.step, self.slept = start_ns, step_ns, []

    def now(self):
        self.t += self.step
        return self.t

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.t += int(seconds * 1e9)

    def seconds(self):
        return self.t / 1e9


def kinds(packets):
    return [p[12] for p in packets]


def bursts(packets):
    """The packets cut at each burst's start: a first sync, or a brightness packet right after a row (a prime)."""
    out, cur = [], []
    for p in packets:
        starts = (p[12] == SYNC and (not cur or cur[-1][12] != SYNC)) or (p[12] == BRIGHTNESS and cur and cur[-1][12] == ROW)
        if starts and cur:
            out.append(cur)
            cur = []
        cur.append(p)
    if cur:
        out.append(cur)
    return out


def row_pixels(packet, width):
    """(chunk, 3) pixels of one row packet, as on the wire."""
    return np.frombuffer(packet[ROW_HEADER_LEN:], np.uint8).reshape(-1, 3)
