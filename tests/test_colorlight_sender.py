"""The sender core: one burst a tick, sync first, whole frames, BGR, the level in every packet, the pause after a
failed send, the prime after a start. No real time: a fake clock and a fake socket."""
import errno

import numpy as np
import pytest

from show.display.colorlight_packets import brightness_bytes, row_packets, sync_bytes
from show.display.colorlight_sender import (BEATS, BRIGHTNESS_REPS, CLOSE_FRAMES, DEV_N, ERRNO, ERRORS, FRAMES, LEVEL,
                                            LATE, PAUSE, SLIPS, STOP, SYNC_REPS, Sender, Slot)
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


# --- the pacing, on the fake clock

from show.display.colorlight_sender import LATE_NS, PERIOD_NS, SPIN_NS, stats_of, wait_until  # noqa: E402


def sync_times(sock, clock, sender, n):
    """The clock's reading at each burst's first sync, for n ticks."""
    times = []
    sock.hook = lambda k, p: times.append(clock.t) if p[12] == SYNC and sock.sent and sock.sent[-1][12] != SYNC else None
    for _ in range(n):
        sender.tick()
    return times


def test_syncs_sit_on_an_absolute_grid_with_no_drift(slot):
    sender, sock, clock = make(slot)
    times = sync_times(sock, clock, sender, 2001)                    # the prime, then 2000 syncs
    assert len(times) == 2000
    for k, t in enumerate(times):
        assert abs(t - (times[0] + k * PERIOD_NS)) <= 3 * clock.step, k
    assert clock.slept.count(0.0) == 0 and all(0 < s <= PERIOD_NS / 1e9 for s in clock.slept)


def test_the_wait_sleeps_to_spin_ns_before_the_deadline_then_spins():
    clock = FakeClock(step_ns=10_000)
    target = clock.t + 10_000_000
    wait_until(target, clock.now, clock.sleep, SPIN_NS)
    assert len(clock.slept) == 1
    assert abs(clock.slept[0] - (10_000_000 - SPIN_NS - clock.step) / 1e9) < 2 * clock.step / 1e9
    assert target <= clock.t < target + 2 * clock.step
    clock.slept.clear()
    wait_until(clock.t + SPIN_NS // 2, clock.now, clock.sleep, SPIN_NS)    # inside the spin: no sleep at all
    assert clock.slept == []


def test_a_stall_moves_the_grid_once_with_no_catch_up(slot):
    sender, sock, clock = make(slot)
    times = sync_times(sock, clock, sender, 4)
    clock.t += 100_000_000                                           # a 100 ms stall between ticks
    more = sync_times(sock, clock, sender, 3)
    assert slot.h[SLIPS] == 1
    assert more[0] - times[-1] > 100_000_000                         # the late burst goes at once...
    assert abs((more[1] - more[0]) - PERIOD_NS) <= 3 * clock.step   # ...and the grid restarts from it
    assert abs((more[2] - more[1]) - PERIOD_NS) <= 3 * clock.step
    assert slot.h[FRAMES] == 6 and slot.h[LATE] == 1


def test_stats_read_the_header(slot):
    sender, sock, clock = make(slot)
    for _ in range(11):
        sender.tick()
    s = stats_of(slot.h)
    assert s["frames"] == 10 and s["late"] == 0 and s["slips"] == 0 and s["errors"] == 0 and s["rt"] is False
    assert 0 <= s["worst_us"] < 3 * clock.step / 1e3 and abs(s["mean_us"]) < 3 * clock.step / 1e3
    assert s["sd_us"] < 3 * clock.step / 1e3
    assert stats_of(np.zeros(16, np.int64)) == {"frames": 0, "late": 0, "slips": 0, "worst_us": 0.0, "mean_us": 0.0,
                                                "sd_us": 0.0, "errors": 0, "rt": False, "wake_worst_us": 0.0}


# --- the plan review's findings (2026-09-30)

def test_a_gap_of_seconds_between_syncs_does_not_overflow_the_stats(slot):
    sender, sock, clock = make(slot)
    sync_times(sock, clock, sender, 3)
    clock.t += 4_000_000_000                                         # a 4 s stall (a suspend, a swap storm)
    n = int(slot.h[DEV_N])
    sender.tick()                                                    # the slipped frame: no interval counted
    sender.tick()
    assert slot.h[SLIPS] == 1 and int(slot.h[DEV_N]) == n + 1        # the frame after it counts again
    assert stats_of(slot.h)["sd_us"] < 3 * clock.step / 1e3


def test_the_parent_death_drain_stays_black_whatever_is_pushed(slot):
    alive = [True, True, False]
    sender, sock, _ = make(slot, parent_alive=lambda: alive.pop(0) if alive else False)
    slot.write(red())
    pushed = []
    sock.hook = lambda n, p: (slot.write(red()), pushed.append(n)) if p[12] == ROW and p[14] == 3 and not pushed and slot.h[FRAMES] >= 3 else None
    sender.run()
    out = bursts(sock.sent)
    assert pushed                                                    # a frame did land during the drain
    assert not any(row_pixels(p, W).any() for burst in out[3:] for p in burst if p[12] == ROW)


@pytest.mark.parametrize("width", [128, 512, 384])
def test_the_bgr_swap_writes_into_the_packets_without_a_copy(width):
    s = Slot.create(width, 4)
    try:
        sender, sock, _ = make(s)
        assert np.shares_memory(sender.bgr, sender.packets) and sender.bgr.size == 4 * width * 3
    finally:
        s.close()


# --- at the wall, 2026-09-30: a lone sync a few hundred us late shows; is it the sleep waking past its margin?

def test_the_worst_wake_past_the_spin_margin_is_recorded(slot):
    clock = FakeClock()
    real_sleep = clock.sleep

    def oversleeps(seconds):
        real_sleep(seconds + (0.0025 if len(clock.slept) == 4 else 0.0))   # the 4th sleep wakes 2.5 ms late
    clock.sleep = oversleeps
    sender, sock, _ = make(slot, clock=clock)
    for _ in range(8):
        sender.tick()
    s = stats_of(slot.h)
    assert 2400 < s["wake_worst_us"] < 2600                       # how late the sleep returned, at worst
    assert 400 < s["worst_us"] < 600                               # and so the sync, past the 2 ms spin


def test_the_spin_margin_can_be_set_from_the_environment(monkeypatch):
    from show.display.colorlight_sender import spin_ns_from_env
    monkeypatch.delenv("COLORLIGHT_SPIN_MS", raising=False)
    assert spin_ns_from_env() == SPIN_NS
    monkeypatch.setenv("COLORLIGHT_SPIN_MS", "4")
    assert spin_ns_from_env() == 4_000_000
    monkeypatch.setenv("COLORLIGHT_SPIN_MS", "nonsense")
    assert spin_ns_from_env() == SPIN_NS


def test_the_sender_pins_itself_to_the_highest_core_it_may_use(monkeypatch):
    # At the wall, 2026-09-30: unpinned at SCHED_FIFO 50 a sync was 300 to 850 us late once a minute and the owner
    # saw it; pinned to one core the worst was 36 us. The last core, so the show's own threads keep the first ones.
    from show.display import colorlight_sender as cs
    monkeypatch.setattr(cs, "SENDER_CPU", None)
    monkeypatch.setattr(cs.os, "sched_getaffinity", lambda pid: {0, 1, 2, 3}, raising=False)
    assert cs.sender_cpu() == 3
    monkeypatch.setattr(cs, "SENDER_CPU", 1)
    assert cs.sender_cpu() == 1
    monkeypatch.setattr(cs, "SENDER_CPU", None)
    monkeypatch.setattr(cs.os, "sched_getaffinity", lambda pid: {0}, raising=False)
    assert cs.sender_cpu() is None                                 # one core: nothing to choose, no pin
