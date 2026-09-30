"""Play a video on the wall, every frame through the flash governor, at the video's rate.

    python tools/wall_video.py ~/Videos/clip.mp4 --iface enp5s0                # 30 frames a second, brightness 0.1
    python tools/wall_video.py clip.mp4 --iface enp5s0 --fps 20 --loop --seconds 60
    python tools/wall_video.py clip.mp4 --backend sdl                           # the same in a window

ffmpeg decodes and scales the file (letterboxed) to the wall's size as raw RGB; each frame goes through
show.wall.GovernedDisplay (the flash governor at --fps, the show's gamma) to the display, so nothing the governor
would hold reaches the wall. Brightness is the level in the card's sync, 0.1 unless asked, never over CAP (0.4). Pushes
are paced by absolute deadlines, as wall_pattern.py; the colorlight driver sends 60.00 a second whatever --fps is, the rows paced across each frame. Ends
dark: the governed black frames, then the driver's own drain. Prints the sender's stats at the end.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Callable, Iterator

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from show.display import make_display  # noqa: E402
from show.display.colorlight import stats_line  # noqa: E402
from show.wall import GovernedDisplay  # noqa: E402
from tools.wall_pattern import CAP, MAX_FPS, governor_fps  # noqa: E402


def ffmpeg_argv(path: str, width: int, height: int, fps: float, loop: bool) -> list[str]:
    """ffmpeg decoding `path` to raw rgb24 frames of width x height at fps on stdout, letterboxed on black."""
    return ["ffmpeg", "-v", "error", "-nostdin"] + (["-stream_loop", "-1"] if loop else []) + [
        "-i", path, "-an", "-sn",
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
               f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,fps={fps:g}",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]


def frames(stream, width: int, height: int) -> Iterator[np.ndarray]:
    """Whole (height, width, 3) uint8 frames from a byte stream of raw rgb24; a short tail is dropped."""
    size = width * height * 3
    while True:
        buf = b""
        while len(buf) < size:
            chunk = stream.read(size - len(buf))
            if not chunk:
                return
            buf += chunk
        yield np.frombuffer(buf, np.uint8).reshape(height, width, 3)


def play(source: Iterator[np.ndarray], display, width: int, height: int, *, fps: float = 30.0,
         brightness: float = 0.1, seconds: float = 0.0, gamma: float = 2.2, clock: Callable[[], float] = time.monotonic,
         sleep: Callable[[float], None] = time.sleep, out: Callable[[str], None] = print) -> int:
    """Push the source's frames through the governor at fps until the source ends, seconds pass (0: never) or
    Ctrl-C; then the sender's stats and the governed close. 0, or 1 after an OSError from the display."""
    if not 0.0 < brightness <= CAP:
        out(f"wall_video: brightness must be over 0 and at most {CAP:g} (the power supply cap), got {brightness!r}")
        return 2
    if not 0.0 < fps <= MAX_FPS:
        out(f"wall_video: fps must be over 0 and at most {MAX_FPS:g}, got {fps!r}")
        return 2
    wall = GovernedDisplay(display, height, width, governor_fps(fps), gamma, from_dark=True)
    code, shown = 0, 0
    try:
        wall.set_brightness(brightness)
        start = clock()
        period = 1.0 / fps
        due = start + period
        now = clock()
        for frame in source:
            if seconds > 0 and now - start >= seconds:
                break
            wall.push(frame)
            shown += 1
            now = clock()
            if now < due:
                sleep(due - now)
                now, due = due, due + period
            else:
                due = now + period
    except KeyboardInterrupt:
        pass
    except OSError as e:
        out(f"wall_video: the display failed: {e}")
        code = 1
    finally:
        out(f"wall_video: {shown} frames shown, {wall.governor.held_ticks} ticks held by the governor")
        line = stats_line(display)
        if line:
            out(line)
        try:
            wall.close()
        except OSError as e:
            out(f"wall_video: closing the wall failed: {e}")
            code = 1
    return code


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="wall_video", description="Play a video on the LED wall, governed")
    p.add_argument("file")
    p.add_argument("--backend", default="colorlight", choices=("colorlight", "sdl", "ddp"))
    p.add_argument("--iface", default="eth0")
    p.add_argument("--width", type=int, default=128)
    p.add_argument("--height", type=int, default=64)
    p.add_argument("--fps", type=float, default=30.0, help=f"the video's rate on the wall, at most {MAX_FPS:g}")
    p.add_argument("--brightness", type=float, default=0.1, help=f"over 0, at most {CAP}")
    p.add_argument("--seconds", type=float, default=0.0, help="0: to the end of the file (or Ctrl-C)")
    p.add_argument("--loop", action="store_true", help="play the file over and over")
    p.add_argument("--gamma", type=float, default=2.2)
    p.add_argument("--sdl-scale", type=int, default=8)
    p.add_argument("--ddp-host", default="127.0.0.1")
    p.add_argument("--ddp-port", type=int, default=4048)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not Path(args.file).is_file():
        print(f"wall_video: no such file {args.file}")
        return 2
    cfg = SimpleNamespace(backend=args.backend, width=args.width, height=args.height, iface=args.iface,
                          sdl_scale=args.sdl_scale, ddp_host=args.ddp_host, ddp_port=args.ddp_port,
                          brightness=min(args.brightness, CAP))
    try:
        display = make_display(cfg)
    except (OSError, ValueError) as e:
        print(f"wall_video: cannot open the {args.backend} display: {e}")
        return 1
    proc = subprocess.Popen(ffmpeg_argv(args.file, args.width, args.height, args.fps, args.loop),
                            stdout=subprocess.PIPE)
    try:
        return play(frames(proc.stdout, args.width, args.height), display, args.width, args.height, fps=args.fps,
                    brightness=args.brightness, seconds=args.seconds, gamma=args.gamma)
    finally:
        proc.stdout.close()
        proc.terminate()
        proc.wait(5)


if __name__ == "__main__":
    sys.exit(main())
