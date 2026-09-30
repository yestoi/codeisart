"""Bench (2026-09-30, not part of the repo): the colorlight sender's child with one knob from the environment,
for the ghosting review's sender-side trials. Everything else is show.display.colorlight_sender as it stands.

    GHOST_FPS          output frames a second (the driver's 60.32; the sync and rows are the S2 format's since
                       the driver took it, so the old rep knobs are gone)

Started only by ghost_knobs.py, in place of `python -m show.display.colorlight_sender`, with the same arguments.
"""
import os
import sys

from show.display import colorlight_sender as cs

FPS = float(os.environ.get("GHOST_FPS", cs.OUTPUT_FPS))
if not 50.0 <= FPS <= 65.0:
    raise SystemExit("ghost_child: GHOST_FPS out of range (50..65)")
cs.OUTPUT_FPS = FPS
cs.PERIOD_NS = round(1e9 / FPS)
cs.CLOSE_FRAMES = round(cs.CLOSE_HOLD_S * FPS)


class Sender(cs.Sender):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("period_ns", cs.PERIOD_NS)       # the class's default was bound at 60.32
        super().__init__(*args, **kwargs)


cs.Sender = Sender
sys.exit(cs.main(sys.argv[1:]))
