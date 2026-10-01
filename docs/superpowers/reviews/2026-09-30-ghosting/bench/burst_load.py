"""Probe (2026-09-30 night, the framed-wall session): a bursty CPU load on cores 0-2 (never 3, the sender's core),
like the pose model: busy 60 ms, idle 40 ms, ten times a second, one process a core (about 61 % each).
Run beside a still on the wall: a picture that changes with the load means the Pi's work reaches the wall.

    python3 burst_load.py SECONDS
"""
import os, sys, time
from multiprocessing import Process

def work(core, seconds):
    os.sched_setaffinity(0, {core})
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        t = time.monotonic() + 0.060
        while time.monotonic() < t:
            pass
        time.sleep(0.040)

if __name__ == "__main__":
    seconds = float(sys.argv[1])
    ps = [Process(target=work, args=(c, seconds)) for c in (0, 1, 2)]
    [p.start() for p in ps]
    [p.join() for p in ps]
    print(f"burst load done: {seconds:g} s on cores 0-2")
