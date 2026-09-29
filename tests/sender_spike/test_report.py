"""What tools/sender_spike/send.py measures and prints, and how it waits. No wall clock."""
import csv
import re

import pytest

from tools.sender_spike import send
from tests.sender_spike.test_loop import Bench

MS = 1_000_000
US = 1_000


def log_of(sync_times, frames=None, added=None, ticks=None, bursts=None):
    n = len(sync_times)
    return send.Log(frames=n if frames is None else frames, ticks=ticks or list(sync_times),
                    syncs=list(sync_times), added=added or [0] * n, bursts=bursts or [200 * US] * n)


def bins(text):
    return {label: int(count) for label, count in re.findall(r"^\s+(\S.*?)\s{2,}(\d+)$", text, re.M)}


def numbers(text, title):
    line = [ln for ln in text.splitlines() if title in ln][0].split(title + ":")[1]
    return {name: float(value) for name, value in re.findall(r"(\w+) (-?[\d.]+)", line)}


def test_intervals_are_between_the_syncs_of_the_picture():
    log = log_of([0, 10 * MS, 21 * MS, 30 * MS, 100 * MS], frames=4)       # the fifth frame is black
    assert send.intervals(log) == [10 * MS, 11 * MS, 9 * MS]


def test_spread_of_known_values():
    s = send.spread([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    assert s["mean"] == 5.5 and s["min"] == 1 and s["max"] == 10
    assert s["sd"] == pytest.approx(2.8723, abs=1e-4)
    assert s["p50"] == 5 and s["p99"] == 10


def test_spread_of_nothing_is_none():
    assert send.spread([]) is None


def test_histogram_counts_each_value_once_in_its_bin():
    values = [-3000 * US, -1500 * US, -30 * US, -5 * US, 0, 5 * US, 19 * US, 20 * US, 60 * US, 2500 * US]
    h = send.histogram(values)
    assert sum(count for label, count in h) == len(values)
    got = {label: count for label, count in h if count}
    assert got == {"below -2000": 1, "-2000 to -1000": 1, "-50 to -20": 1, "-20 to 20": 4, "20 to 50": 1,
                   "50 to 100": 1, "2000 and above": 1}


def test_histogram_has_the_same_bins_every_time():
    assert [label for label, count in send.histogram([])] == [label for label, count in send.histogram([7])]
    assert len(send.histogram([])) == 15


def test_the_report_gives_the_measured_rate_and_the_spread():
    sync = [n * 16_666_667 for n in range(601)]
    sync[300] += 60 * US                                  # one sync 60 us late
    text = send.report(send.plan_from([]), log_of(sync, frames=601))
    assert "601 frames" in text
    assert "60.000 fps" in text
    assert numbers(text, "sync to sync, ms") == {
        "mean": 16.667, "sd": 0.003, "min": 16.607, "max": 16.727, "p50": 16.667, "p99": 16.667}
    assert {k: v for k, v in bins(text).items() if v} == {"-100 to -50": 1, "-20 to 20": 598, "50 to 100": 1}


def test_the_report_gives_the_added_jitter_and_the_senders_own_error():
    bench = Bench()
    bench.run(["--order", "sync-rows", "--jitter-ms", "0.5", "--seconds", "2"])
    text = send.report(bench.plan, bench.log)
    added = numbers(text, "added to each sync, us")
    assert 200 < added["mean"] < 300 and 0 <= added["min"] < 50 and 450 < added["max"] <= 500
    own = numbers(text, "sync after its tick, less the added time, us")
    assert own["mean"] == pytest.approx(0.05, abs=0.06)    # the bench reads its clock in 50 ns
    assert own["max"] <= 0.1


def test_the_report_counts_late_frames_and_says_when_it_was_interrupted():
    bench = Bench(stop_at=68 * 10 + 5)
    bench.run([])
    text = send.report(bench.plan, bench.log)
    assert "10 frames" in text and "60 black" in text and "interrupted" in text
    assert "0 late" in text and "0 slips" in text


def test_the_report_counts_the_slips():
    from tests.sender_spike.test_loop import Stalling
    bench = Stalling(at=68 * 20 + 30)
    bench.run(["--seconds", "1"])
    assert "1 late; 1 slips" in send.report(bench.plan, bench.log)


def test_the_report_of_a_run_too_short_to_measure():
    text = send.report(send.plan_from([]), log_of([0], frames=1))
    assert "1 frames" in text and "too few" in text


def test_the_log_file_has_a_line_a_frame(tmp_path):
    bench = Bench()
    bench.run(["--jitter-ms", "0.5", "--seconds", "1"])
    path = tmp_path / "run.csv"
    send.write_log(str(path), bench.plan, bench.log)
    lines = path.read_text().splitlines()
    assert lines[0].startswith("# ") and "jitter 0 to 0.5 ms" in lines[0]
    rows = list(csv.DictReader(lines[1:]))
    assert len(rows) == 120
    assert rows[0].keys() == {"frame", "black", "tick_ns", "sync_ns", "added_ns", "burst_ns"}
    assert [r["black"] for r in rows] == ["0"] * 60 + ["1"] * 60
    assert int(rows[0]["tick_ns"]) == 0                   # times count from the first tick
    assert int(rows[7]["added_ns"]) == bench.log.added[7]
    assert int(rows[7]["sync_ns"]) == bench.log.syncs[7] - bench.log.ticks[0]


# --- waiting

class Clock:
    def __init__(self, oversleep=70_000, per_read=100):
        self.t, self.oversleep, self.per_read = 0, oversleep, per_read
        self.slept, self.reads = [], 0

    def now(self):
        self.reads += 1
        self.t += self.per_read
        return self.t

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.t += int(seconds * 1e9) + self.oversleep


def test_spin_never_sleeps_and_ends_on_the_target():
    c = Clock()
    send.waiter("spin", 2 * MS, c.now, c.sleep)(5 * MS)
    assert c.slept == []
    assert 5 * MS <= c.t < 5 * MS + 2 * c.per_read


def test_sleep_sleeps_once_and_takes_what_it_gets():
    c = Clock()
    send.waiter("sleep", 2 * MS, c.now, c.sleep)(5 * MS)
    assert len(c.slept) == 1 and c.slept[0] == pytest.approx(0.005, abs=1e-6)
    assert c.t == pytest.approx(5 * MS + c.oversleep, abs=1000)
    assert c.reads == 1


def test_hybrid_sleeps_short_of_the_target_and_spins_the_rest():
    c = Clock()
    send.waiter("hybrid", 2 * MS, c.now, c.sleep)(5 * MS)
    assert len(c.slept) == 1 and c.slept[0] == pytest.approx(0.003, abs=1e-6)
    assert 5 * MS <= c.t < 5 * MS + 2 * c.per_read


def test_hybrid_does_not_sleep_when_the_target_is_near():
    c = Clock()
    send.waiter("hybrid", 2 * MS, c.now, c.sleep)(1 * MS)
    assert c.slept == [] and 1 * MS <= c.t < 1 * MS + 2 * c.per_read


def test_a_target_in_the_past_returns_at_once():
    for kind in ("spin", "sleep", "hybrid"):
        c = Clock()
        c.t = 9 * MS
        send.waiter(kind, 2 * MS, c.now, c.sleep)(5 * MS)
        assert c.slept == [] and c.t < 9 * MS + 3 * c.per_read


# --- the command

class Sockets:
    def __init__(self):
        self.opened, self.sent, self.closed = [], [], 0

    def open(self, plan):
        self.opened.append((plan.iface, plan.qdisc_bypass))
        return send.Plain(self.sent.append, self.close)

    def close(self):
        self.closed += 1


def test_a_dry_run_opens_no_socket_and_prints_the_report(capsys):
    c, s = Clock(oversleep=0, per_read=1000), Sockets()
    assert send.main(["--dry-run", "--seconds", "1"], now=c.now, sleep=c.sleep, open_sink=s.open) == 0
    out = capsys.readouterr().out
    assert s.opened == []
    assert "dry run" in out and "60 frames" in out and "sync to sync, ms" in out
    assert "60 fps for 1 s" in out


def test_a_run_sends_to_the_port_it_was_given_and_closes_it(capsys):
    c, s = Clock(oversleep=0, per_read=1000), Sockets()
    assert send.main(["--iface", "eth9", "--qdisc-bypass", "--seconds", "1"],
                     now=c.now, sleep=c.sleep, open_sink=s.open) == 0
    assert s.opened == [("eth9", True)]
    assert len(s.sent) == 68 * 120 and s.closed == 1
    assert "eth9" in capsys.readouterr().out


def test_a_forbidden_plan_sends_nothing(capsys):
    c, s = Clock(), Sockets()
    with pytest.raises(SystemExit) as e:
        send.main(["--s2", "--pixel", "128"], now=c.now, sleep=c.sleep, open_sink=s.open)
    assert e.value.code == 2
    assert s.opened == [] and "safety rule 3" in capsys.readouterr().err


def test_the_log_flag_writes_the_file(tmp_path, capsys):
    c, s = Clock(oversleep=0, per_read=1000), Sockets()
    path = tmp_path / "a.csv"
    send.main(["--dry-run", "--seconds", "1", "--log", str(path)], now=c.now, sleep=c.sleep, open_sink=s.open)
    assert len(path.read_text().splitlines()) == 2 + 120


def test_the_command_says_what_else_the_port_sent(capsys):
    c, s = Clock(oversleep=0, per_read=1000), Sockets()
    counts = iter([1000, 1000 + 68 * 120 + 3])
    send.main(["--seconds", "1"], now=c.now, sleep=c.sleep, open_sink=s.open,
              port_counter=lambda iface: next(counts))
    assert "the port sent 8163 packets during the run: 8160 ours, 3 not ours" in capsys.readouterr().out


def test_a_quiet_port_is_reported_as_quiet(capsys):
    c, s = Clock(oversleep=0, per_read=1000), Sockets()
    counts = iter([5, 5 + 68 * 120])
    send.main(["--seconds", "1"], now=c.now, sleep=c.sleep, open_sink=s.open,
              port_counter=lambda iface: next(counts))
    assert "8160 ours, 0 not ours" in capsys.readouterr().out


def test_a_port_without_a_counter_is_not_reported(capsys):
    c, s = Clock(oversleep=0, per_read=1000), Sockets()
    send.main(["--seconds", "1"], now=c.now, sleep=c.sleep, open_sink=s.open, port_counter=lambda iface: None)
    assert "the port sent" not in capsys.readouterr().out


def test_the_port_counter_reads_the_systems_file(tmp_path):
    (tmp_path / "eth9" / "statistics").mkdir(parents=True)
    (tmp_path / "eth9" / "statistics" / "tx_packets").write_text("35391282\n")
    assert send.port_counter("eth9", root=str(tmp_path)) == 35391282
    assert send.port_counter("eth8", root=str(tmp_path)) is None


class Pipe:
    """Standard output into a pipe whose reader goes away, as `tee` does on Ctrl-C."""

    def __init__(self):
        self.broken, self.text = False, ""

    def write(self, text):
        if self.broken:
            raise BrokenPipeError(32, "Broken pipe")
        self.text += text

    def flush(self):
        if self.broken:
            raise BrokenPipeError(32, "Broken pipe")


def test_a_reader_that_went_away_does_not_lose_the_log(tmp_path, monkeypatch):
    c, s, pipe = Clock(oversleep=0, per_read=1000), Sockets(), Pipe()
    path = tmp_path / "a.csv"
    monkeypatch.setattr("sys.stdout", pipe)

    def open_sink(plan):
        def send_and_break(packet):
            s.sent.append(packet)
            pipe.broken = len(s.sent) > 100                # the reader dies during the run
        return send.Plain(send_and_break, s.close)

    assert send.main(["--seconds", "1", "--log", str(path)], now=c.now, sleep=c.sleep, open_sink=open_sink,
                     port_counter=lambda iface: None) == 0
    assert len(s.sent) == 68 * 120 and s.closed == 1       # the run went on to its black end
    assert len(path.read_text().splitlines()) == 2 + 120   # and the log has all of it
    assert "sync to sync" not in pipe.text


def test_the_report_is_kept_beside_the_log(tmp_path, capsys):
    c, s = Clock(oversleep=0, per_read=1000), Sockets()
    path = tmp_path / "a.csv"
    send.main(["--seconds", "1", "--log", str(path)], now=c.now, sleep=c.sleep, open_sink=s.open,
              port_counter=lambda iface: None)
    lines = path.read_text().splitlines()
    out = capsys.readouterr().out
    kept = (tmp_path / "a.report.txt").read_text()
    assert "sync to sync, ms" in kept and "60 fps for 1 s" in kept
    assert kept.strip() in out
