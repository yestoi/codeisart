"""Probe (2026-09-30 night, the framed-wall session): the arcade's lobby run dry (no card), every pushed frame
measured and every brightness call logged, to tell a flicker in the picture from one on the card.

    cd ~/codeisart && sudo .venv/bin/python <this dir>/lobby_probe.py [SECONDS] [PICTURE]

Healthy (2026-09-30): the level set once (0.1); the brightest byte 255 in every frame; the lit pixels steady (551
once the figure is up); the mean light swelling about 5 % once a second (the lobby's own breathing) and nothing else.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import arcade_load as al  # noqa: E402

STATS, LEVELS = [], []
make = al.dry_display

def probing(w, h, b):
    d = make(w, h, b)
    push, setb = d.push, d.set_brightness
    def p(frame):
        f = np.asarray(frame)
        STATS.append((int(f.max()), float(f.mean()), int((f.max(axis=2) > 0).sum())))
        return push(frame)
    def s(level):
        LEVELS.append((len(STATS), level))
        return setb(level)
    d.push, d.set_brightness = p, s
    return d

al.dry_display = probing
seconds = sys.argv[1] if len(sys.argv) > 1 else "20"
picture = sys.argv[2] if len(sys.argv) > 2 else "/home/trey/bench/person.jpg"  # the Pi's bench media, not in git (under sudo, Path.home() is root's)
sys.argv = ["arcade_load", "--seconds", seconds, "--picture", picture]
try:
    al.main()
finally:
    a = np.array(STATS)
    print(f"frames {len(a)}")
    for name, col in (("max byte", 0), ("mean", 1), ("lit pixels", 2)):
        c = a[:, col]
        d = np.abs(np.diff(c))
        print(f"{name}: min {c.min():.3f} median {np.median(c):.3f} max {c.max():.3f}; frame-to-frame change: median {np.median(d):.3f} max {d.max():.3f}, changes {int((d > 0).sum())}")
    print("brightness calls:", LEVELS[:10], "... total", len(LEVELS))
    tail = a[-90:]
    print("last 3 s, mean per frame:", " ".join(f"{m:.2f}" for m in tail[::3, 1]))
