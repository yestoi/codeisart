"""Bench (2026-09-30, not part of the repo): the colorlight sender's child with three knobs from the environment,
for the ghosting review's sender-side trials. Everything else is show.display.colorlight_sender as it stands.

    GHOST_SYNC_REPS    sync packets a frame (the driver's 2)
    GHOST_BRIGHT_REPS  0x0A brightness packets a frame (the driver's 2)
    GHOST_FPS          output frames a second (the driver's 59)

Started only by ghost_knobs.py, in place of `python -m show.display.colorlight_sender`, with the same arguments.
"""
import os
import sys

from show.display import colorlight_sender as cs

cs.SYNC_REPS = int(os.environ.get("GHOST_SYNC_REPS", cs.SYNC_REPS))
cs.BRIGHTNESS_REPS = int(os.environ.get("GHOST_BRIGHT_REPS", cs.BRIGHTNESS_REPS))
FPS = float(os.environ.get("GHOST_FPS", cs.OUTPUT_FPS))
if not 1 <= cs.SYNC_REPS <= 4 or not 0 <= cs.BRIGHTNESS_REPS <= 4 or not 50.0 <= FPS <= 65.0:
    raise SystemExit("ghost_child: knobs out of range (sync 1..4, bright 0..4, fps 50..65)")
cs.OUTPUT_FPS = FPS
cs.PERIOD_NS = round(1e9 / FPS)
cs.CLOSE_FRAMES = round(cs.CLOSE_HOLD_S * FPS)


class Sender(cs.Sender):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("period_ns", cs.PERIOD_NS)       # the class's default was bound at 59
        super().__init__(*args, **kwargs)


cs.Sender = Sender
sys.exit(cs.main(sys.argv[1:]))
