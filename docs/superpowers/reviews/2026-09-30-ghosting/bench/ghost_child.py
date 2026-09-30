"""Bench (2026-09-30, not part of the repo): the colorlight sender's child with one knob from the environment,
for the ghosting review's sender-side trials. Everything else is show.display.colorlight_sender as it stands.

    GHOST_FPS          output frames a second (the driver's 60.00)
    GHOST_SPREAD_MS    the rows spread over this many ms after the sync, handed to the driver's own pacing (the
                       driver's 15.5, the evening's answer at 60.00); 0: a burst
    GHOST_ORDER        sync-rows (the driver's) or rows-sync (the sync held until the last row has gone)
    GHOST_COUNTER      on (the driver's) or off: byte 14 frozen at 0
    GHOST_SYNC_REPS    syncs a frame (the driver's 1); 2 in the S2 format is a black wall

Started only by ghost_knobs.py, in place of `python -m show.display.colorlight_sender`, with the same arguments.
"""
import os
import sys

from show.display import colorlight_sender as cs

FPS = float(os.environ.get("GHOST_FPS", cs.OUTPUT_FPS))
COUNTER_OFF = os.environ.get("GHOST_COUNTER", "on") == "off"
SYNC_REPS = int(os.environ.get("GHOST_SYNC_REPS", "1"))
SPREAD_MS = os.environ.get("GHOST_SPREAD_MS")                 # None: the driver's own spread
ORDER = os.environ.get("GHOST_ORDER", "sync-rows")            # or rows-sync: the rows first, the sync after the last
if ORDER not in ("sync-rows", "rows-sync"):
    raise SystemExit("ghost_child: GHOST_ORDER is sync-rows or rows-sync")
if not 1 <= SYNC_REPS <= 3:
    raise SystemExit("ghost_child: GHOST_SYNC_REPS is 1 to 3")
if not 50.0 <= FPS <= 65.0:
    raise SystemExit("ghost_child: GHOST_FPS out of range (50..65)")
cs.OUTPUT_FPS = FPS
cs.PERIOD_NS = round(1e9 / FPS)
cs.CLOSE_FRAMES = round(cs.CLOSE_HOLD_S * FPS)
SPREAD_NS = cs.ROW_SPREAD_NS if SPREAD_MS is None else round(float(SPREAD_MS) * 1e6)
if not 0 <= SPREAD_NS < cs.PERIOD_NS:
    raise SystemExit("ghost_child: GHOST_SPREAD_MS is 0 to under the period (%.2f ms); over 64.5 frames a second the "
                     "driver's 15.5 is not, so set it" % (cs.PERIOD_NS / 1e6))


class Sender(cs.Sender):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("period_ns", cs.PERIOD_NS)       # the class's defaults were bound at the driver's rate
        kwargs.setdefault("row_spread_ns", SPREAD_NS)
        super().__init__(*args, **kwargs)
        if ORDER == "rows-sync":                           # the sync held back until the last row has gone
            inner, n_rows = self.send, len(self.rows)
            state = {"held": None, "k": 0}

            def rows_then_sync(packet):
                if packet[12] == 0x01:
                    state["held"], state["k"] = packet, 0
                    return len(packet)
                n = inner(packet)
                state["k"] += 1
                if state["k"] >= n_rows and state["held"] is not None:
                    inner(state["held"])
                    state["held"] = None
                return n
            self.send = rows_then_sync
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
