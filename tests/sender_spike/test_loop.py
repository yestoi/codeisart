"""The loop of tools/sender_spike/send.py, with a clock that is not the wall's and a sink that is not a socket."""
import pytest

from tools.sender_spike import send

START = 5_000_000_000


class Bench:
    """A clock that moves when something waits, reads it or sends; a sink that keeps what it is given."""

    def __init__(self, per_send=3_000, per_read=50, stop_at=None):
        self.t = START
        self.per_send, self.per_read, self.stop_at = per_send, per_read, stop_at
        self.sent = []          # (time, packet)
        self.waits = []

    def now(self):
        self.t += self.per_read
        return self.t

    def wait(self, target):
        self.waits.append(target)
        self.t = max(self.t, target)

    def send(self, packet):
        if self.stop_at is not None and len(self.sent) == self.stop_at:
            self.stop_at = None
            raise KeyboardInterrupt
        self.sent.append((self.t, packet))
        self.t += self.per_send

    def run(self, argv):
        self.plan = send.plan_from(argv)
        self.log = send.run(self.plan, self.send, self.now, self.wait)
        return self.frames()

    def frames(self):
        """The packets grouped into frames: a frame ends with its last row (sync-rows) or last sync."""
        first = 0x01 if self.plan.order == "sync-rows" else (0x0A if self.plan.bright_reps else 0x55)
        out, prev = [], None
        for t, p in self.sent:
            kind = p[12]
            if kind == first and prev != first and (first != 0x55 or prev != 0x55):
                out.append([])
            out[-1].append((t, p))
            prev = kind
        return out


def kinds(frame):
    return [p[12] for t, p in frame]


def is_black(frame):
    return all(not any(p[21:]) for t, p in frame if p[12] == 0x55)


def test_the_base_sends_brightness_twice_the_rows_and_sync_twice():
    frames = Bench().run([])
    assert len(frames) == 600 + 60
    assert all(kinds(f) == [0x0A] * 2 + [0x55] * 64 + [0x01] * 2 for f in frames)


def test_the_base_frame_is_the_test_senders_packets():
    import tests.sender_spike.test_packets as tp
    old = tp.old_sender()
    frame = Bench().run(["--seconds", "1"])[0]
    assert [p for t, p in frame] == [old.bright(25)] * 2 + old.rows(old.bars(128)) + [old.sync(25)] * 2


def test_sync_rows_puts_the_sync_first():
    frames = Bench().run(["--order", "sync-rows", "--seconds", "1"])
    assert all(kinds(f) == [0x01] * 2 + [0x0A] * 2 + [0x55] * 64 for f in frames)


def test_the_s2_frame_is_one_sync_and_the_rows():
    frames = Bench().run(["--s2", "--seconds", "1"])
    assert len(frames) == 60 + 60
    assert all(kinds(f) == [0x01] + [0x55] * 64 for f in frames)
    assert all(len(f[0][1]) == 1036 for f in frames)
    assert all(p[19:21] == b"\x00\x00" for f in frames for t, p in f[1:])


def test_the_counter_counts_every_frame_the_black_ones_too():
    frames = Bench().run(["--s2", "--seconds", "1"])
    counters = [f[0][1][14] for f in frames]
    assert counters == [(189 + n) % 256 for n in range(120)]


def test_both_syncs_of_a_frame_carry_one_counter():
    frames = Bench().run(["--counter", "on", "--seconds", "1"])
    assert all(f[-1][1] == f[-2][1] for f in frames)
    assert [f[-1][1][14] for f in frames[:3]] == [0, 1, 2]


@pytest.mark.parametrize("argv", [[], ["--s2"], ["--order", "sync-rows"], ["--bright-reps", "0"],
                                  ["--sync-reps", "3", "--gap-ms", "12"], ["--fps", "120"]])
def test_no_sync_goes_out_without_its_rows(argv):
    bench = Bench()
    bench.run(argv + ["--seconds", "1"])
    between, prev = [0], None                              # rows between one group of syncs and the next
    for t, p in bench.sent:
        if p[12] == 0x55:
            between[-1] += 1
        elif p[12] == 0x01 and prev != 0x01:
            between.append(0)
        prev = p[12] if p[12] != 0x0A else prev
    assert set(between[1:-1]) == {64}
    assert between[0] in (0, 64) and between[-1] in (0, 64)
    assert sum(between) == 64 * len(bench.frames())


def test_it_ends_in_black():
    frames = Bench().run(["--seconds", "2", "--tail-seconds", "0.5"])
    assert len(frames) == 120 + 30
    assert not any(is_black(f) for f in frames[:120])
    assert all(is_black(f) for f in frames[120:])


def test_no_tail_when_it_is_asked_for():
    frames = Bench().run(["--seconds", "1", "--tail-seconds", "0"])
    assert len(frames) == 60 and not any(is_black(f) for f in frames)


def test_a_black_frame_has_the_layout_of_the_others():
    frames = Bench().run(["--s2", "--seconds", "1"])
    assert kinds(frames[-1]) == kinds(frames[0])
    assert frames[-1][1][1][:21] == frames[0][1][1][:21]


def test_ctrl_c_still_ends_in_black():
    bench = Bench(stop_at=68 * 10 + 5)
    frames = bench.run([])
    assert bench.log.interrupted
    black = [f for f in frames if is_black(f)]
    assert len(black) == 60 and frames[-60:] == black
    assert len(frames) < 600


def test_frames_start_on_a_grid_that_does_not_drift():
    bench = Bench()
    frames = bench.run(["--fps", "60.32", "--seconds", "5"])
    period = 1e9 / 60.32
    t0 = frames[0][0][0]
    for n in (1, 2, 100, 301, 330):
        assert abs(frames[n][0][0] - t0 - n * period) <= 1


def test_the_sync_of_sync_rows_sits_on_the_tick():
    bench = Bench()
    bench.run(["--order", "sync-rows", "--seconds", "2"])
    gaps = [b - a for a, b in zip(bench.log.syncs, bench.log.syncs[1:])]
    assert max(abs(g - 1e9 / 60) for g in gaps) <= 1


def test_the_gap_is_a_pause_after_the_last_row():
    frames = Bench().run(["--gap-ms", "12", "--seconds", "1"])
    for f in frames:
        last_row = [t for t, p in f if p[12] == 0x55][-1]
        sync = [t for t, p in f if p[12] == 0x01][0]
        assert 12_000_000 <= sync - last_row <= 12_010_000


def test_no_gap_no_wait_before_the_sync():
    bench = Bench()
    frames = bench.run(["--seconds", "1"])
    f = frames[3]
    assert f[66][0] - f[65][0] < 10_000
    assert len(bench.waits) == len(frames)                 # one wait a frame: for its tick


def test_jitter_holds_each_sync_back_by_a_logged_random_time():
    bench = Bench()
    bench.run(["--order", "sync-rows", "--jitter-ms", "0.5", "--seconds", "2"])
    added = bench.log.added
    assert len(added) == 120 + 60
    assert all(0 <= a <= 500_000 for a in added)
    assert len(set(added)) > 100
    assert max(added) > 400_000 and min(added) < 100_000
    for n in (0, 1, 50, 119):
        assert abs(bench.log.syncs[n] - bench.log.ticks[n] - added[n]) <= 100


def test_jitter_in_the_base_order_comes_after_the_rows():
    bench = Bench()
    frames = bench.run(["--jitter-ms", "1", "--seconds", "1"])
    for n, f in enumerate(frames):
        last_row = [t for t, p in f if p[12] == 0x55][-1]
        sync = [t for t, p in f if p[12] == 0x01][0]
        assert abs(sync - last_row - bench.per_send - bench.log.added[n]) <= 200


def test_the_random_times_come_from_the_seed():
    a, b, c = Bench(), Bench(), Bench()
    a.run(["--jitter-ms", "1", "--seconds", "1"])
    b.run(["--jitter-ms", "1", "--seconds", "1"])
    c.run(["--jitter-ms", "1", "--seconds", "1", "--seed", "2"])
    assert a.log.added == b.log.added != c.log.added


def test_no_jitter_is_logged_as_none():
    bench = Bench()
    bench.run(["--seconds", "1"])
    assert bench.log.added == [0] * 120


def test_the_log_has_a_line_for_every_frame():
    bench = Bench()
    frames = bench.run(["--seconds", "1"])
    log = bench.log
    assert len(log.ticks) == len(log.syncs) == len(log.added) == len(log.bursts) == len(frames)
    assert log.frames == 60 and not log.interrupted and log.late == 0
    assert log.syncs[5] == [t for t, p in frames[5] if p[12] == 0x01][0]
    assert log.bursts[5] == pytest.approx(68 * 3_000, abs=500)


def test_frames_that_miss_their_tick_are_counted_and_still_sent():
    bench = Bench(per_send=300_000)                        # 68 packets take 20 ms: more than a period
    frames = bench.run(["--seconds", "1", "--tail-seconds", "0"])
    assert len(frames) == 60
    assert bench.log.late >= 58


@pytest.mark.parametrize("argv", [[], ["--s2"], ["--s2-header"], ["--picture", "scroll"],
                                  ["--s2", "--picture", "scroll"], ["--pixel", "60"]])
def test_no_pixel_is_above_the_plans(argv):
    bench = Bench()
    bench.run(argv + ["--seconds", "2"])
    top = max(max(p[21:]) for t, p in bench.sent if p[12] == 0x55)
    assert top == bench.plan.pixel


def test_the_scroll_moves_on_the_wire():
    frames = Bench().run(["--picture", "scroll", "--seconds", "2"])
    first = [p for t, p in frames[0] if p[12] == 0x55]
    assert [p for t, p in frames[5] if p[12] == 0x55] == first
    assert [p for t, p in frames[119] if p[12] == 0x55] != first


@pytest.mark.parametrize("argv", [[], ["--s2"], ["--s2-header", "--sync-len", "1036"], ["--bright-reps", "1"]])
def test_only_the_three_packet_types_go_to_the_card(argv):
    bench = Bench()
    bench.run(argv + ["--seconds", "1"])
    assert {p[12] for t, p in bench.sent} <= {0x01, 0x0A, 0x55}
    assert all(p[0:6] == send.DST and p[6:12] == send.SRC for t, p in bench.sent)


@pytest.mark.parametrize("packet", [
    send.DST + send.SRC + bytes([0x07]) + bytes(271),
    send.DST + send.SRC + bytes([0x02]) + bytes(100),
    send.DST + send.SRC + bytes([0x11]) + bytes(100),
    bytes.fromhex("ffffffffffff") + send.SRC + bytes([0x55]) + bytes(100),
    send.DST + send.SRC,
], ids=["detect", "receiver layout", "save", "another destination", "no packet type"])
def test_the_guard_refuses_any_other_packet(packet):
    with pytest.raises(ValueError, match="0x01, 0x55"):
        send.guard([packet])


def test_run_checks_its_plan():
    import dataclasses
    plan = dataclasses.replace(send.plan_from(["--s2"]), pixel=128)
    bench = Bench()
    with pytest.raises(ValueError, match="25"):
        send.run(plan, bench.send, bench.now, bench.wait)
    assert bench.sent == []
