"""Bench (2026-09-30, not part of the repo): is the fainter second picture the arcade's, or the picture's?

Pictures with no arcade behind them, through tools/wall_pattern.py's own run (the governor, the colorlight driver,
its close). Each carries its number, bottom right.

    1  the lobby's frame as the arcade pushed it, standing still
    2  the same frame sliding sideways, 10 pixels a second
    3  a white bar sweeping 30 pixels a second inside a border (pixel value 128)
    4  two-row lines at pixel values 64, 128 and 255, left to right: orange above, white below

    cd ~/codeisart && sudo .venv/bin/python ~/bench/ghost_test.py 1 --iface eth0 --seconds 20 --fps 30
"""
import sys
from pathlib import Path

sys.path.insert(0, "/home/trey/codeisart")

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from show.font import Font  # noqa: E402
from show.renderer import draw_text  # noqa: E402
from tools import wall_pattern as wp  # noqa: E402

HERE = Path(__file__).resolve().parent
LOBBY = cv2.imread(str(HERE / "lobby.png"))[::8, ::8, ::-1].copy()      # saved 8 times its size, BGR
FONT = Font.load(wp.FONT_PATH)


def label(frame, n):
    h, w = frame.shape[:2]
    frame[h - 10:, w - 8:] = 0
    draw_text(frame, w - 7, h - 9, str(n), FONT, (255, 255, 255))
    return frame


def still(width, height, t):
    return label(LOBBY.copy(), 1)


def slide(width, height, t):
    return label(np.roll(LOBBY, int(t * 10) % width, axis=1), 2)


def bar(width, height, t):
    frame = wp.border(width, height, t)
    x = int(t * 30) % width
    frame[:, x:x + 3] = wp.WHITE
    return label(frame, 3)


def levels(width, height, t):
    frame = np.zeros((height, width, 3), np.uint8)
    third = width // 3
    for i, level in enumerate((64, 128, 255)):
        x0, x1 = i * third + 4, (i + 1) * third - 4
        frame[16:18, x0:x1] = (level, level // 2, 0)       # orange
        frame[40:42, x0:x1] = (level, level, level)        # white
    return label(frame, 4)


PICTURES = {"1": still, "2": slide, "3": bar, "4": levels}
for name, fn in PICTURES.items():
    wp.PATTERNS[name] = fn
    wp.LOOK_FOR[name] = fn.__name__
sys.exit(wp.main(sys.argv[1:]))
