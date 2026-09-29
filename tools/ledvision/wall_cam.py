"""A photo of the wall from a webcam, for an agent (or the owner) to look at between LEDVision steps.

    python -m tools.ledvision.wall_cam                        # shots/wall.png from camera 0
    python -m tools.ledvision.wall_cam --out shots/g8-p1.png --index 1
    python -m tools.ledvision.wall_cam --list                 # which camera indexes open, and their size

Point the camera square at the FRONT of the wall so left and right read as they do for a viewer, fill the frame
with the four panels, and dim the room: at 40% the panels still clip a webcam's auto exposure, and a single
lit LED is easiest to place against dark panels. On macOS the terminal running this needs Camera permission
(System Settings > Privacy & Security > Camera) or every read comes back empty.
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


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="wall_cam", description="Photograph the LED wall from a webcam")
    p.add_argument("--out", default="shots/wall.png")
    p.add_argument("--index", type=int, default=0, help="camera index (see --list)")
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--warmup", type=int, default=15, help="frames read and dropped before the photo")
    p.add_argument("--settle", type=float, default=1.0, help="seconds to keep reading before the photo")
    p.add_argument("--list", action="store_true", help="probe indexes 0 to 4 and exit")
    args = p.parse_args(argv)

    import cv2

    if args.list:
        for i in range(5):
            frame = grab(i, args.width, args.height, warmup=3, settle=0)
            print(f"{i}: " + ("no frame" if frame is None else f"{frame.shape[1]}x{frame.shape[0]}"))
        return 0
    frame = grab(args.index, args.width, args.height, args.warmup, args.settle)
    if frame is None:
        print(f"camera {args.index} gave no frame (wrong --index, in use, or no Camera permission)", file=sys.stderr)
        return 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), frame)
    print(f"{out} {frame.shape[1]}x{frame.shape[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
