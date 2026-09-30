"""The sender core: one burst a tick, sync first, whole frames, BGR, the level in every packet, the pause after a
failed send, the prime after a start. No real time: a fake clock and a fake socket."""
import errno

import numpy as np
import pytest

from show.display.colorlight_packets import brightness_bytes, row_packets, sync_bytes
from show.display.colorlight_sender import (BEATS, BRIGHTNESS_REPS, CLOSE_FRAMES, ERRNO, ERRORS, FRAMES, LEVEL,
                                            PAUSE, STOP, SYNC_REPS, Sender, Slot)
from tests.colorlight_fakes import BRIGHTNESS, ROW, SYNC, FakeClock, FakeSocket, bursts, kinds, row_pixels

W, H = 128, 64
PRIME = BRIGHTNESS_REPS + H                      # packets of the first burst: no sync before a whole frame
FULL = SYNC_REPS + BRIGHTNESS_REPS + H


@pytest.fixture
def slot():
    s = Slot.create(W, H)
    yield s
    s.close()


def make(slot, sock=None, clock=None, **kw):
    sock, clock = sock or FakeSocket(), clock or FakeClock()
    return Sender(slot, sock.send, clock=clock.now, sleep=clock.sleep, **kw), sock, clock


def red(width=W, height=H):
    f = np.zeros((height, width, 3), np.uint8)
    f[..., 0] = 200
    return f


def test_the_first_burst_is_a_prime_and_the_second_a_whole_frame_sync_first(slot):
    sender, sock, _ = make(slot)
    assert sender.tick() and sender.tick()
    first, second = bursts(sock.sent)
    assert kinds(first) == [BRIGHTNESS] * BRIGHTNESS_REPS + [ROW] * H        # the prime: no sync before rows
    assert kinds(second) == [SYNC] * SYNC_REPS + [BRIGHTNESS] * BRIGHTNESS_REPS + [ROW] * H
    assert [p[14] for p in second if p[12] == ROW] == list(range(H))
    assert slot.h[FRAMES] == 1 and slot.h[BEATS] == 2                        # frames count syncs sent


def test_it_starts_dark_and_repeats_the_last_frame(slot):
    sender, sock, _ = make(slot)
    for _ in range(3):
        sender.tick()
    for burst in bursts(sock.sent):
        assert not any(row_pixels(p, W).any() for p in burst if p[12] == ROW)
    slot.write(red())
    sock.sent.clear()
    for _ in range(3):
        sender.tick()
    for burst in bursts(sock.sent):
        rows = [p for p in burst if p[12] == ROW]
        assert all((row_pixels(p, W) == (0, 0, 200)).all() for p in rows)    # BGR on the wire


@pytest.mark.parametrize("width,height", [(128, 64), (512, 4), (384, 4)])
def test_the_rows_are_the_reference_rows_of_the_bgr_frame(width, height):
    s = Slot.create(width, height)
    try:
        sender, sock, _ = make(s)
        frame = np.random.default_rng(width).integers(0, 256, (height, width, 3), dtype=np.uint8)
        s.write(frame)
        sender.tick()
        rows = [p for p in sock.sent if p[12] == ROW]
        assert rows == [p for y in range(height) for p in row_packets(y, frame[y, :, ::-1])]
    finally:
        s.close()


def test_the_level_rides_in_every_sync_and_brightness_packet_and_is_dark_until_set(slot):
    sender, sock, _ = make(slot)
    sender.tick()
    sender.tick()
    assert [p for p in sock.sent if p[12] == SYNC] == [sync_bytes(0)] * SYNC_REPS
    assert [p for p in sock.sent if p[12] == BRIGHTNESS] == [brightness_bytes(0)] * 2 * BRIGHTNESS_REPS
    slot.h[LEVEL] = 102
    sock.sent.clear()
    sender.tick()
    assert [p for p in sock.sent if p[12] == SYNC] == [sync_bytes(102)] * SYNC_REPS
    assert [p for p in sock.sent if p[12] == BRIGHTNESS] == [brightness_bytes(102)] * BRIGHTNESS_REPS


def test_a_burst_is_one_frame_even_when_a_push_lands_inside_it(slot):
    other = np.full((H, W, 3), 50, np.uint8)
    sock = FakeSocket(hook=lambda n, p: slot.write(other) if p[12] == ROW and p[14] == 20 and not slot.h[FRAMES] else None)
    sender, sock, _ = make(slot, sock)
    slot.write(red())
    sender.tick()                                        # the prime: red, with the push at row 20
    sender.tick()
    first, second = bursts(sock.sent)
    assert all((row_pixels(p, W) == (0, 0, 200)).all() for p in first if p[12] == ROW)
    assert all((row_pixels(p, W) == 50).all() for p in second if p[12] == ROW)


def test_a_failed_send_ends_the_burst_records_the_error_and_pauses(slot):
    sock = FakeSocket(fail={PRIME + 5: OSError(errno.ENETDOWN, "Network is down")})   # burst 2's first row
    sender, sock, clock = make(slot, sock)
    sender.tick()
    sender.tick()
    second = bursts(sock.sent)[1]
    assert kinds(second) == [SYNC] * 2 + [BRIGHTNESS] * 2                    # the rows after the failure: none
    assert slot.h[PAUSE] == 1 and slot.h[ERRORS] == 1 and slot.h[ERRNO] == errno.ENETDOWN
    sent = len(sock.sent)
    assert sender.tick() and sender.tick()
    assert len(sock.sent) == sent and slot.h[BEATS] == 4                     # paused: nothing, but it beats
    assert clock.slept[-1] > 0                                               # a paused tick sleeps, not spins
    slot.h[PAUSE] = 0                                                        # the parent's push
    sender.tick()
    assert kinds(sock.sent[sent:]) == [BRIGHTNESS] * 2 + [ROW] * H           # the restart primes: no sync
    sender.tick()
    assert sock.sent[-FULL][12] == SYNC


def test_a_row_failing_after_the_syncs_means_no_sync_until_a_push(slot):
    sock = FakeSocket(fail={PRIME + 4 + 30: OSError(errno.EIO, "io")})      # burst 2, row 26
    sender, sock, _ = make(slot, sock)
    for _ in range(6):
        sender.tick()
    syncs = [i for i, p in enumerate(sock.sent) if p[12] == SYNC]
    assert syncs == [PRIME, PRIME + 1]                                       # burst 2's, and none after


def test_stop_ends_the_ticks_without_a_send(slot):
    sender, sock, _ = make(slot)
    sender.tick()
    slot.h[STOP] = 1
    n = len(sock.sent)
    assert not sender.tick() and len(sock.sent) == n


def test_run_sends_black_for_a_second_when_the_parent_is_gone(slot):
    alive = [True, True, True, False]
    sender, sock, _ = make(slot, parent_alive=lambda: alive.pop(0) if alive else False)
    slot.write(red())
    sender.run()
    out = bursts(sock.sent)
    assert len(out) == 3 + CLOSE_FRAMES + 1                                  # 3 ticks alive, a prime, then black
    assert all((row_pixels(p, W) == (0, 0, 200)).all() for p in out[2] if p[12] == ROW)
    assert not any(row_pixels(p, W).any() for burst in out[3:] for p in burst if p[12] == ROW)
