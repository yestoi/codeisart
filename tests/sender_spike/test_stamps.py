"""Transmit time stamps (SO_TIMESTAMPING) in tools/sender_spike/send.py, against a socket that is not one.

What the kernel really returns is checked on the first run with a real socket; these tests hold the
sender's side: which packets ask for a stamp, how the answers are read and matched, what is printed.
"""
import re
import struct

import pytest

from tools.sender_spike import send
from tests.sender_spike.test_report import Clock, bins, numbers

SOL_SOCKET, SCM_TIMESTAMPING = 1, 37
SOL_PACKET, PACKET_TX_TIMESTAMP = 263, 16
ENOMSG, ORIGIN_TIMESTAMPING = 42, 4
SND, SCHED = 0, 1


def answer(key, kind=SND, software_ns=0, hardware_ns=0):
    """The ancillary data of one message on the error queue, as recvmsg gives it."""
    def ts(ns):
        return struct.pack("qq", ns // 10**9, ns % 10**9)
    return [(SOL_SOCKET, SCM_TIMESTAMPING, ts(software_ns) + ts(0) + ts(hardware_ns)),
            (SOL_PACKET, PACKET_TX_TIMESTAMP, struct.pack("IBBBBII", ENOMSG, ORIGIN_TIMESTAMPING, 0, 0, 0, kind, key))]


class FakeSocket:
    def __init__(self):
        self.sent, self.asked, self.queue, self.options, self.closed = [], [], [], [], False

    def send(self, packet):
        self.sent.append(packet)

    def sendmsg(self, buffers, ancdata):
        self.sent.append(b"".join(buffers))
        self.asked.append((len(self.sent) - 1, ancdata))

    def recvmsg(self, bufsize, ancbufsize, flags):
        assert flags == send.MSG_ERRQUEUE | send.MSG_DONTWAIT
        if not self.queue:
            raise BlockingIOError
        return b"", self.queue.pop(0), 0, None

    def setsockopt(self, *a):
        self.options.append(a)

    def close(self):
        self.closed = True


T0 = 1_790_000_000 * 10**9


def test_a_stamp_is_read_from_the_error_queue():
    assert send.parse_stamp(answer(7, SND, software_ns=T0 + 5)) == (7, "driver", T0 + 5)
    assert send.parse_stamp(answer(7, SCHED, software_ns=T0 + 1)) == (7, "queue", T0 + 1)
    assert send.parse_stamp(answer(9, SND, hardware_ns=123_456_789_000)) == (9, "port", 123_456_789_000)


def test_what_is_not_a_stamp_is_none():
    assert send.parse_stamp([]) is None
    assert send.parse_stamp([(SOL_SOCKET, SCM_TIMESTAMPING, bytes(48))]) is None
    assert send.parse_stamp(answer(1, kind=2, software_ns=T0)) is None          # an ACK stamp: not ours


def test_only_the_first_sync_of_a_frame_asks_for_a_stamp():
    sock = FakeSocket()
    sink = send.Stamper(sock, hardware=False)
    plan = send.plan_from(["--seconds", "1", "--tail-seconds", "0"])
    clock = Clock(oversleep=0, per_read=1000)
    send.run(plan, sink.send, clock.now, send.waiter("sleep", 0, clock.now, clock.sleep))
    assert len(sock.sent) == 68 * 60
    asked = [i for i, anc in sock.asked]
    assert asked == [68 * n + 66 for n in range(60)]
    assert all(sock.sent[i][12] == 0x01 for i in asked)
    level, kind, data = sock.asked[0][1][0]
    assert (level, kind) == (SOL_SOCKET, SCM_TIMESTAMPING)
    assert struct.unpack("I", data)[0] == send.SOF_TX_SCHED | send.SOF_TX_SOFTWARE


def test_the_port_clock_is_asked_for_only_with_hardware():
    sock = FakeSocket()
    sink = send.Stamper(sock, hardware=True)
    sink.send(send.sync_packet(send.SyncSpec(), 0))
    flags = struct.unpack("I", sock.asked[0][1][0][2])[0]
    assert flags == send.SOF_TX_SCHED | send.SOF_TX_SOFTWARE | send.SOF_TX_HARDWARE


def test_the_socket_is_told_to_report_stamps_without_the_packet():
    sock = FakeSocket()
    send.Stamper(sock, hardware=False)
    (level, option, flags), = sock.options
    assert (level, option) == (SOL_SOCKET, SCM_TIMESTAMPING)
    assert flags == (send.SOF_SOFTWARE | send.SOF_RAW_HARDWARE | send.SOF_OPT_ID | send.SOF_OPT_TSONLY
                     | send.SOF_OPT_TX_SWHW)


def test_drain_empties_the_queue_and_keeps_the_stamps_by_frame():
    sock = FakeSocket()
    sink = send.Stamper(sock, hardware=True)
    sock.queue = [answer(0, SCHED, software_ns=T0), answer(0, SND, software_ns=T0 + 40_000),
                  answer(0, SND, hardware_ns=5_000_000), answer(1, SCHED, software_ns=T0 + 16_000_000)]
    sink.drain()
    assert sock.queue == []
    assert sink.stamps == {"queue": {0: T0, 1: T0 + 16_000_000}, "driver": {0: T0 + 40_000}, "port": {0: 5_000_000}}
    sock.queue = [answer(1, SND, software_ns=T0 + 16_050_000)]
    sink.drain()
    assert sink.stamps["driver"] == {0: T0 + 40_000, 1: T0 + 16_050_000}


def test_waiting_drains_first():
    sock = FakeSocket()
    sink = send.Stamper(sock, hardware=False)
    sock.queue = [answer(0, SND, software_ns=T0)]
    order = []
    wait = sink.draining(lambda target: order.append(("wait", target, len(sock.queue))))
    wait(123)
    assert order == [("wait", 123, 0)]


def stamps_at(times_by_kind):
    return {kind: dict(enumerate(times)) for kind, times in times_by_kind.items()}


def test_the_report_gives_sync_to_sync_by_the_drivers_clock():
    period = 16_666_667
    driver = [T0 + n * period for n in range(600)]
    driver[100] += 300_000                                 # one sync left the queue 0.3 ms late
    queue = [T0 + n * period - 20_000 for n in range(600)]
    text = send.stamp_report(send.plan_from([]), 600, stamps_at({"queue": queue, "driver": driver}))
    got = numbers(text, "sync to sync at the driver, ms")
    assert got["min"] == 16.367 and got["max"] == 16.967 and got["mean"] == 16.667
    assert {k: v for k, v in bins(text).items() if v} == {"-500 to -200": 1, "-20 to 20": 597, "200 to 500": 1}
    in_queue = numbers(text, "from the queue to the driver, us")
    assert in_queue["min"] == 20.0 and in_queue["max"] == 320.0
    assert "at the port" not in text


def test_the_report_gives_the_ports_clock_when_it_has_it():
    period = 16_666_667
    times = [n * period for n in range(600)]
    text = send.stamp_report(send.plan_from([]), 600, stamps_at({
        "queue": [T0 + t for t in times], "driver": [T0 + t + 5_000 for t in times],
        "port": [777 + t for t in times]}))
    assert numbers(text, "sync to sync at the port, ms")["sd"] == 0.0
    assert text.count("less the period") == 2


def test_the_report_leaves_the_black_frames_out():
    period = 16_666_667
    driver = [T0 + n * period for n in range(60)] + [T0 + 10**9 + n * 50_000_000 for n in range(60)]
    text = send.stamp_report(send.plan_from([]), 60, stamps_at({"driver": driver}))
    assert numbers(text, "sync to sync at the driver, ms")["max"] == 16.667


def test_the_report_counts_the_stamps_that_did_not_come():
    period = 16_666_667
    stamps = {"driver": {n: T0 + n * period for n in range(600) if n not in (10, 11, 300)}}
    text = send.stamp_report(send.plan_from([]), 600, stamps)
    assert "driver: 597 of 600 stamps" in text
    got = numbers(text, "sync to sync at the driver, ms")
    assert got["max"] == 16.667                            # a gap in the stamps is not a long interval


def test_the_report_without_any_stamp_says_so():
    text = send.stamp_report(send.plan_from([]), 600, {})
    assert "no stamps came back" in text


def test_stamp_flags_are_variables_of_the_plan():
    assert send.plan_from([]).stamp == ""
    assert send.plan_from(["--stamp"]).stamp == "sw"
    assert send.plan_from(["--stamp-hw"]).stamp == "hw"
    assert "stamps" in send.describe(send.plan_from(["--stamp"]))
    assert "port's clock" in send.describe(send.plan_from(["--stamp-hw"]))


def test_stamps_need_a_socket():
    with pytest.raises(ValueError, match="dry run"):
        send.plan_from(["--stamp", "--dry-run"])


def test_the_command_prints_the_stamps_and_writes_them_to_the_log(tmp_path, capsys):
    period = 16_666_667
    sock = FakeSocket()

    class Answering(send.Stamper):
        def send(self, packet):
            first = packet[12] == 0x01 and self.last != 0x01
            super().send(packet)
            if first:
                n = len(sock.asked) - 1
                sock.queue += [answer(n, SCHED, software_ns=T0 + n * period),
                               answer(n, SND, software_ns=T0 + n * period + 30_000)]

    clock = Clock(oversleep=0, per_read=1000)
    path = tmp_path / "s.csv"
    send.main(["--stamp", "--seconds", "1", "--log", str(path)], now=clock.now, sleep=clock.sleep,
              open_sink=lambda plan: Answering(sock, hardware=False))
    out = capsys.readouterr().out
    assert "driver: 60 of 60 stamps" in out
    assert numbers(out, "sync to sync at the driver, ms")["sd"] == 0.0
    assert numbers(out, "from the queue to the driver, us")["mean"] == 30.0
    assert sock.closed and sock.queue == []
    lines = path.read_text().splitlines()
    assert lines[1] == "frame,black,tick_ns,sync_ns,added_ns,burst_ns,queue_ns,driver_ns"
    assert lines[2].split(",")[6:] == ["0", "30000"]
    assert lines[2 + 119].split(",")[6:] == [str(119 * period), str(119 * period + 30_000)]
