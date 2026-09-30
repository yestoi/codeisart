"""The child process: liveness only. It sends on a socket it was handed, beats, stops after a whole burst. No
assertion on rates: those are measured on the target."""
import os
import signal
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
        frames = int(slot.h[FRAMES])
        os.kill(child.pid, signal.SIGINT)                # Ctrl-C and systemctl stop reach the whole group:
        os.kill(child.pid, signal.SIGTERM)               # the child ignores both and keeps sending
        while int(slot.h[FRAMES]) < frames + 3 and time.monotonic() < deadline:
            stream += ours.recv(65536)
            whole, stream = packets(stream)
            got += whole
        assert child.is_alive() and int(slot.h[FRAMES]) >= frames + 3
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


def test_spawning_the_child_leaves_no_other_process_behind():
    # multiprocessing's spawn starts the resource tracker, a child that lives as long as the parent and that the
    # show's soak counts as a child left behind: the sender is a plain subprocess instead.
    import subprocess
    import sys

    code = """
import multiprocessing.resource_tracker as rt
import os, socket, subprocess
from show.display.colorlight import spawn_sender
from show.display.colorlight_sender import STOP, Slot
ours, theirs = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
slot = Slot.create(8, 4)
child = spawn_sender(slot, theirs)
theirs.close()
ours.settimeout(20.0)
while slot.h[5] < 3:          # FRAMES
    ours.recv(65536)
slot.h[STOP] = 1
child.join(10.0)
ours.close(); slot.close()
left = subprocess.run(["pgrep", "-P", str(os.getpid())], capture_output=True, text=True).stdout.split()
print("tracker", rt._resource_tracker._pid, "alive", child.is_alive(), "exit", child.exitcode, "left", len(left))
"""
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "tracker None alive False exit 0 left 0"


def test_the_child_runs_on_a_discard_socket_for_a_dry_run():
    from show.display.colorlight import DiscardSocket

    slot = Slot.create(8, 4)
    child = None
    try:
        child = spawn_sender(slot, DiscardSocket())
        deadline = time.monotonic() + 20.0
        while int(slot.h[FRAMES]) < 3 and child.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert child.is_alive() and int(slot.h[FRAMES]) >= 3
        slot.h[STOP] = 1
        child.join(10.0)
        assert not child.is_alive() and child.exitcode == 0
    finally:
        if child is not None and child.is_alive():
            child.terminate()
            child.join(5.0)
        slot.close()
