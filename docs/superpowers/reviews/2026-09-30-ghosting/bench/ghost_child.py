"""Bench (2026-09-30, not part of the repo): the colorlight sender's child with one knob from the environment,
for the ghosting review's sender-side trials. Everything else is show.display.colorlight_sender as it stands.

    GHOST_FPS          output frames a second (the driver's 60.32)
    GHOST_SPREAD_MS    the rows spread over this many ms after the sync (the driver's 0: a burst); 15.5 was the
                       evening's answer at 60.00
    GHOST_ORDER        sync-rows (the driver's) or rows-sync
    GHOST_COUNTER      on (the driver's) or off: byte 14 frozen at 0
    GHOST_SYNC_REPS    syncs a frame (the driver's 1); 2 in the S2 format is a black wall

Started only by ghost_knobs.py, in place of `python -m show.display.colorlight_sender`, with the same arguments.
"""
import os
import sys
import time

from show.display import colorlight_sender as cs

FPS = float(os.environ.get("GHOST_FPS", cs.OUTPUT_FPS))
COUNTER_OFF = os.environ.get("GHOST_COUNTER", "on") == "off"
SYNC_REPS = int(os.environ.get("GHOST_SYNC_REPS", "1"))
SPREAD_MS = float(os.environ.get("GHOST_SPREAD_MS", "0"))   # rows spread over this many ms after the sync; 0: a burst
ORDER = os.environ.get("GHOST_ORDER", "sync-rows")            # or rows-sync: the rows first, the sync after the last
if not 0 <= SPREAD_MS <= 16.45:
    raise SystemExit("ghost_child: GHOST_SPREAD_MS is 0 to 16.45")
if ORDER not in ("sync-rows", "rows-sync"):
    raise SystemExit("ghost_child: GHOST_ORDER is sync-rows or rows-sync")
if not 1 <= SYNC_REPS <= 3:
    raise SystemExit("ghost_child: GHOST_SYNC_REPS is 1 to 3")
if not 50.0 <= FPS <= 65.0:
    raise SystemExit("ghost_child: GHOST_FPS out of range (50..65)")
cs.OUTPUT_FPS = FPS
cs.PERIOD_NS = round(1e9 / FPS)
cs.CLOSE_FRAMES = round(cs.CLOSE_HOLD_S * FPS)


class Sender(cs.Sender):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("period_ns", cs.PERIOD_NS)       # the class's default was bound at 60.32
        super().__init__(*args, **kwargs)
        if SPREAD_MS or ORDER != "sync-rows":               # the burst's timing and order, bench knobs
            inner = self.send
            n_rows = len(self.rows)
            state = {"t0": None, "k": 0, "held": None}
            step = SPREAD_MS * 1e-3 / n_rows

            def paced(packet):
                if packet[12] == 0x01:                        # a sync: the burst starts here
                    state["t0"], state["k"] = time.perf_counter(), 0
                    if ORDER == "rows-sync":
                        state["held"] = packet
                        return len(packet)
                    return inner(packet)
                if state["t0"] is None:                       # a prime: rows with no sync before them
                    state["t0"], state["k"] = time.perf_counter(), 0
                k = state["k"]
                if step:
                    due = state["t0"] + (k + 1) * step
                    while True:
                        left = due - time.perf_counter()
                        if left <= 0:
                            break
                        if left > 0.0003:
                            time.sleep(left - 0.0002)
                n = inner(packet)
                state["k"] = k + 1
                if state["k"] >= n_rows:                      # the last row of the burst
                    held, state["t0"], state["held"] = state["held"], None, None
                    if held is not None:
                        inner(held)
                return n
            self.send = paced
        if SYNC_REPS > 1:                                  # every sync goes out SYNC_REPS times, back to back
            inner = self.send

            def send_reps(packet):
                n = inner(packet)
                if packet[12] == 0x01:
                    for _ in range(SYNC_REPS - 1):
                        inner(packet)
                return n
            self.send = send_reps

    def tick(self):                                        # GHOST_COUNTER=off: byte 14 stays 0 (bench, 2026-09-30 evening)
        ok = super().tick()
        if COUNTER_OFF:
            self._counter = 0
        return ok


cs.Sender = Sender
sys.exit(cs.main(sys.argv[1:]))
