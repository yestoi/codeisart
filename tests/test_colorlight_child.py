"""The child process: liveness only. It sends on a socket it was handed, beats, stops after a whole burst. No
assertion on rates: those are measured on the target."""
import socket
import time

from show.display.colorlight import spawn_sender
from show.display.colorlight_sender import BEATS, FRAMES, STOP, Slot, set_realtime

LENGTHS = {0x01: 112, 0x0A: 77}


def packets(stream):
    """Whole packets from the front of a byte stream, and the tail that is not one yet."""
    out, i = [], 0
    while i + 21 <= len(stream):
        kind = stream[i + 12]
        n = LENGTHS.get(kind) or 21 + int.from_bytes(stream[i + 17:i + 19], "big") * 3
        if i + n > len(stream):
            break
        out.append(stream[i:i + n])
        i += n
    return out, stream[i:]


def test_the_child_sends_on_the_socket_it_was_handed_beats_and_stops_after_a_whole_burst():
    ours, theirs = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    slot = Slot.create(8, 4)
    child = None
    try:
        child = spawn_sender(slot, theirs)
        theirs.close()                                   # the child has its own; the end of the stream is its close
        ours.settimeout(20.0)
        stream, got = b"", []
        deadline = time.monotonic() + 20.0
        while sum(1 for p in got if p[12] == 0x01) < 6 and time.monotonic() < deadline:
            stream += ours.recv(65536)
            whole, stream = packets(stream)
            got += whole
        assert sum(1 for p in got if p[12] == 0x01) >= 6, "no third frame in 20 s"
        assert slot.h[BEATS] > 0 and slot.h[FRAMES] >= 3
        slot.h[STOP] = 1
        child.join(10.0)
        assert not child.is_alive() and child.exitcode == 0
        while True:                                      # the rest, to the child's close
            chunk = ours.recv(65536)
            if not chunk:
                break
            stream += chunk
        rest, tail = packets(stream)
        got += rest
        assert tail == b""
        rows = [p for p in got if p[12] == 0x55]
        assert rows and rows[-1][14] == 3                # the last packet out is the last row of a whole burst
        assert got[-1][12] == 0x55
    finally:
        if child is not None and child.is_alive():
            child.terminate()
            child.join(5.0)
        ours.close()
        slot.close()


def test_set_realtime_says_whether_it_got_it():
    got = set_realtime(50)
    assert got in (True, False)
    if got:                                             # root on Linux: put it back
        import os
        os.sched_setscheduler(0, os.SCHED_OTHER, os.sched_param(0))
