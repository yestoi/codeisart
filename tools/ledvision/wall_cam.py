"""A photo of the wall from a webcam, for an agent (or the owner) to look at between LEDVision steps.

    python -m tools.ledvision.wall_cam                        # shots/wall.png from camera 0
    python -m tools.ledvision.wall_cam --out shots/g8-p1.png --index 1
    python -m tools.ledvision.wall_cam --list                 # which camera indexes open, and their size
    python -m tools.ledvision.wall_cam --size 1280x720        # the camera whose frames are that size
    python -m tools.ledvision.wall_cam --size 1280x720 --flash 5 --out shots/g8-p001.png
                                                              # what blinks over 5 s, and where

Point the camera square at the FRONT of the wall so left and right read as they do for a viewer, fill the frame
with the four panels, and dim the room: at 40% the panels still clip a webcam's auto exposure, and a single
lit LED is easiest to place against dark panels. On macOS the terminal running this needs Camera permission
(System Settings > Privacy & Security > Camera) or every read comes back empty.

Camera indexes move when a camera comes or goes (an iPhone's Continuity Camera does), so pick the laptop's by
its frame size with --size. The wizard's Guide 8 point blinks and a still photo often misses it; --flash
records for a few seconds and saves, per pixel, the brightest minus the darkest frame: steady light (lit
lines, daylight on the unlit packages) cancels out and the blinking point is left. It prints where it is.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


def open_camera(index: int, width: int, height: int):
    import cv2

    cap = cv2.VideoCapture(index)
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    return cap


def grab(index: int, width: int, height: int, warmup: int, settle: float):
    """One frame after warmup frames and settle seconds, so auto exposure and focus have caught up."""
    cap = open_camera(index, width, height)
    try:
        if not cap.isOpened():
            return None
        deadline = time.monotonic() + settle
        frame, n = None, 0
        while n < warmup or time.monotonic() < deadline:
            ok, got = cap.read()
            if ok:
                frame = got
            n += 1
            if n > warmup + 300:
                break
        return frame
    finally:
        cap.release()


def parse_size(text: str) -> tuple[int, int]:
    """'1280x720' -> (1280, 720)."""
    w, _, h = text.lower().partition("x")
    if not (w.isdigit() and h.isdigit()):
        raise argparse.ArgumentTypeError(f"a size is WIDTHxHEIGHT, e.g. 1280x720, not {text!r}")
    return int(w), int(h)


def parse_box(text: str) -> tuple[int, int, int, int]:
    """'LEFT,TOP,RIGHT,BOTTOM' in photo pixels -> a tuple; right of left and below top."""
    parts = text.split(",")
    if len(parts) != 4 or not all(v.strip().isdigit() for v in parts):
        raise argparse.ArgumentTypeError(f"a box is LEFT,TOP,RIGHT,BOTTOM in pixels, not {text!r}")
    x0, y0, x1, y1 = (int(v) for v in parts)
    if x1 <= x0 or y1 <= y0:
        raise argparse.ArgumentTypeError(f"the box's right and bottom must be past its left and top: {text!r}")
    return x0, y0, x1, y1


def panel_cell(x: int, y: int, box: tuple[int, int, int, int], cols: int = 64, rows: int = 32):
    """The (row, column) of the panel under photo pixel (x, y), both from 1 at the top left as seen from the
    front, or None outside the box (the panel's outer edges: left, top, right, bottom)."""
    x0, y0, x1, y1 = box
    if not (x0 <= x < x1 and y0 <= y < y1):
        return None
    return (y - y0) * rows // (y1 - y0) + 1, (x - x0) * cols // (x1 - x0) + 1


def find_camera(size: tuple[int, int], width: int, height: int) -> int | None:
    """The first index 0 to 4 whose frames are size (width, height)."""
    for i in range(5):
        frame = grab(i, width, height, warmup=3, settle=0)
        if frame is not None and (frame.shape[1], frame.shape[0]) == size:
            return i
    return None


def record(index: int, width: int, height: int, warmup: int, seconds: float):
    """Grey frames for seconds, stacked (frames, rows, columns), after warmup frames; None if nothing came."""
    import cv2
    import numpy as np

    cap = open_camera(index, width, height)
    try:
        if not cap.isOpened():
            return None
        for _ in range(warmup):
            cap.read()
        frames, start = [], time.monotonic()
        while time.monotonic() - start < seconds:
            ok, got = cap.read()
            if ok:
                frames.append(cv2.cvtColor(got, cv2.COLOR_BGR2GRAY))
        return np.stack(frames) if frames else None
    finally:
        cap.release()


def flash_range(frames):
    """Per pixel, the brightest frame minus the darkest: what changed while recording."""
    import numpy as np

    stack = np.asarray(frames, dtype=np.int16)
    return (stack.max(axis=0) - stack.min(axis=0)).astype(np.uint8)


def flash_peaks(spread, count: int = 6, apart: int = 15) -> list[tuple[int, int, int]]:
    """The count strongest blinks as (x, y, spread), at least apart pixels from each other.

    Ranked on a 3x3 mean so one noisy pixel does not beat an LED's glow, then placed on the strongest pixel of
    that 3x3; the spread reported is that pixel's own.
    """
    import numpy as np

    h, w = spread.shape
    padded = np.pad(spread.astype(np.float32), 1, mode="edge")
    score = sum(padded[dy:dy + h, dx:dx + w] for dy in range(3) for dx in range(3)) / 9
    peaks = []
    for _ in range(count):
        y, x = np.unravel_index(int(np.argmax(score)), score.shape)
        if score[y, x] <= 0:
            break
        y0, x0 = max(0, y - 1), max(0, x - 1)
        dy, dx = np.unravel_index(int(np.argmax(spread[y0:y + 2, x0:x + 2])), spread[y0:y + 2, x0:x + 2].shape)
        peaks.append((int(x0 + dx), int(y0 + dy), int(spread[y0 + dy, x0 + dx])))
        score[max(0, y - apart):y + apart + 1, max(0, x - apart):x + apart + 1] = -1
    return peaks


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="wall_cam", description="Photograph the LED wall from a webcam")
    p.add_argument("--out", default="shots/wall.png")
    p.add_argument("--index", type=int, default=0, help="camera index (see --list)")
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--warmup", type=int, default=15, help="frames read and dropped before the photo")
    p.add_argument("--settle", type=float, default=1.0, help="seconds to keep reading before the photo")
    p.add_argument("--list", action="store_true", help="probe indexes 0 to 4 and exit")
    p.add_argument("--size", type=parse_size,
                   help="use the camera whose frames are WIDTHxHEIGHT (e.g. 1280x720) instead of --index")
    p.add_argument("--flash", type=float, metavar="SECONDS",
                   help="record this long; --out gets what changed (brightest minus darkest, stretched), "
                        "<out>-max.png the brightest frame, and the strongest blinks are printed")
    p.add_argument("--panel", type=parse_box, metavar="L,T,R,B",
                   help="with --flash: a 64x32 panel's outer edges in the photo; each blink then gets its row "
                        "and column on that panel (measure the edges on a dark photo after the camera moves)")
    args = p.parse_args(argv)

    import cv2

    if args.list:
        for i in range(5):
            frame = grab(i, args.width, args.height, warmup=3, settle=0)
            print(f"{i}: " + ("no frame" if frame is None else f"{frame.shape[1]}x{frame.shape[0]}"))
        return 0
    index = args.index
    if args.size:
        index = find_camera(args.size, args.width, args.height)
        if index is None:
            print(f"no camera gives {args.size[0]}x{args.size[1]} frames (see --list)", file=sys.stderr)
            return 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.flash:
        frames = record(index, args.width, args.height, args.warmup, args.flash)
        if frames is None:
            print(f"camera {index} gave no frames", file=sys.stderr)
            return 1
        spread = flash_range(frames)
        cv2.imwrite(str(out), cv2.normalize(spread, None, 0, 255, cv2.NORM_MINMAX))
        cv2.imwrite(str(out.with_name(out.stem + "-max.png")), frames.max(axis=0))
        print(f"{out} {spread.shape[1]}x{spread.shape[0]}, {len(frames)} frames, camera {index}")
        for x, y, v in flash_peaks(spread):
            cell = panel_cell(x, y, args.panel) if args.panel else None
            where = f", panel row {cell[0]} column {cell[1]}" if cell else (", off the panel" if args.panel else "")
            print(f"  blink at x={x} y={y}: {v}{where}")
        return 0
    frame = grab(index, args.width, args.height, args.warmup, args.settle)
    if frame is None:
        print(f"camera {index} gave no frame (wrong --index, in use, or no Camera permission)", file=sys.stderr)
        return 1
    cv2.imwrite(str(out), frame)
    print(f"{out} {frame.shape[1]}x{frame.shape[0]}, camera {index}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
