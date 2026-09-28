"""Operator's own flash trace at HEAD: raw vs governed, whole-field strobes, turn-taking, grating, titles-free control."""
import sys, subprocess
import numpy as np
sys.path.insert(0, ".")
sys.path.insert(0, "tests/arcade")
from arcade.flash import FlashGovernor, flash_area, square_flashes, concurrent_area, BUDGET
from test_flash import turns, grating

def strobe(w, h, a, b, hz, n=150):
    per = round(30 / (2 * hz))
    return [np.full((h, w, 3), a if (i // per) % 2 == 0 else b, np.uint8) for i in range(n)]

def run(name, frames):
    h, w = frames[0].shape[:2]
    g = FlashGovernor(h, w)
    out = [g.apply(f) for f in frames]
    print(f"{w}x{h} {name:34s} square_flashes {square_flashes(frames):3d} -> {square_flashes(out):3d}   "
          f"flash_area {flash_area(frames):.3f} -> {flash_area(out):.3f}   "
          f"concurrent {concurrent_area(out):.3f}   held_ticks {g.held_ticks}")
    return square_flashes(out)

print("HEAD", subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip(), " BUDGET", BUDGET)
worst = 0
for w, h in [(128, 32), (64, 64)]:
    worst = max(worst, run("white/black 15 Hz", strobe(w, h, (255,)*3, (0,)*3, 15)))
    worst = max(worst, run("red/blue 12 Hz (Pokemon)", strobe(w, h, (87, 0, 0), (0, 0, 255), 12)))
    worst = max(worst, run("red/green 10 Hz", strobe(w, h, (255, 0, 0), (0, 152, 0), 10)))
    worst = max(worst, run("5 dithers taking turns", turns(5, w, h)))
    worst = max(worst, run("2 dithers taking turns", turns(2, w, h)))
    worst = max(worst, run("grating every 11 px, 15 Hz", grating(w, h, 11)))
    run("static control", [np.full((h, w, 3), 128, np.uint8)] * 60)
print("worst governed square_flashes", worst, "<= BUDGET" if worst <= BUDGET else "OVER BUDGET")
