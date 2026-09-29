"""Test patterns for the wall: the first light on the panels, and the answers the arcade's colours wait for.

    python tools/wall_pattern.py rgb   --iface eth0                  # pixel order
    python tools/wall_pattern.py index --iface eth0                  # every panel where it should be
    python tools/wall_pattern.py steps --iface eth0 --brightness 0.4 # the brightness packet
    python tools/wall_pattern.py gamma --iface eth0                  # who applies gamma
    python tools/wall_pattern.py rgb   --backend sdl                 # the same picture in a window
    python tools/wall_pattern.py rgb   --png rgb.png                 # or as a file, with no display

The colorlight backend needs Linux and CAP_NET_RAW (show/display/colorlight.py), so on the wall this runs
from the Omarchy box or a Pi, after the card's one-time LEDVision setup. The default is 128x64, the four
panels 2 x 2; `--width 128 --height 32` is one row of two panels, `--width 64 --height 64` a column.
It runs until Ctrl-C, or for --seconds, and leaves the wall dark. Brightness is the card's brightness packet,
0.1 unless asked, and never over CAP (0.4, what the power supplies are sized for). No pattern lights half the
wall. Each pattern prints what to look for; write what the panel shows into
docs/superpowers/workflow/evidence/hardware.md.
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:          # run as a script, the repository is not on the path
    sys.path.insert(0, str(ROOT))

from show.display import make_display  # noqa: E402
from show.font import CELL_H, CELL_W, Font  # noqa: E402

CAP = 0.4                     # the brightness the power supplies are sized for (arcade.toml, show.toml)
PANEL_W, PANEL_H = 64, 32      # one panel
LEVEL = 128                   # the byte the solid colours use
STEP_SECONDS = 2.0            # how long `steps` holds each level
STEPS = (0.125, 0.25, 0.5, 1.0)   # shares of --brightness, low to high
HARDWARE_MD = "docs/superpowers/workflow/evidence/hardware.md"
FONT_PATH = ROOT / "fonts" / "5x7.bin"

RED, GREEN, BLUE, WHITE = (LEVEL, 0, 0), (0, LEVEL, 0), (0, 0, LEVEL), (LEVEL, LEVEL, LEVEL)
CYAN, YELLOW, DIM = (0, LEVEL, LEVEL), (LEVEL, LEVEL, 0), (40, 40, 40)

LOOK_FOR = {
    "rgb": "Four bands from the left: red (R), green (G), blue (B), white (W), each with its letter cut out "
           "dark at the top. Bands in another order or colour: the card's pixel order is not RGB; write the "
           "order you see. Letters mirrored or upside down: the panel is rotated or the chain runs the other "
           "way.",
    "index": "A red corner top left, green top right, blue bottom left, white bottom right, a dim tick every "
             "8 pixels along the top and the left edge, and a cyan line beside a yellow line where the two "
             "panels meet. A corner in the wrong place or a broken line: the panels are swapped or the "
             "LEDVision layout is wrong.",
    "steps": "A grey block that gets brighter every 2 seconds in four steps, with a bar along the bottom that "
             "grows a quarter of the wall a step. Each step should look about twice as bright as the one "
             "before. No change at all: the card ignores the brightness packet on this firmware (write the "
             "firmware version). Uneven steps: write which ones.",
    "gamma": "Top row, from a few metres so the middle patch blends: a grey patch (128), a fine checker, a "
             "lighter patch (186). The checker matches the LEFT patch: the card sends bytes as they are, keep "
             "gamma = 2.2 in arcade.toml. It matches the RIGHT patch: the card applies gamma, set gamma = 1.0. "
             "Bottom: 16 grey steps from black to white; write how many of the dark ones you can tell apart.",
}


def _blank(width: int, height: int) -> np.ndarray:
    return np.zeros((height, width, 3), np.uint8)


def _cut(frame: np.ndarray, text: str, x: int, y: int) -> None:
    """text as dark holes in frame, its top left at (x, y), clipped to the frame."""
    atlas = Font.load(FONT_PATH).atlas()
    for i, ch in enumerate(text):
        x0 = x + i * CELL_W
        cell = frame[y:y + CELL_H, max(x0, 0):x0 + CELL_W]
        glyph = atlas[ord(ch) if ord(ch) < len(atlas) else ord("?")][:cell.shape[0], :cell.shape[1]]
        cell[glyph] = 0


def rgb(width: int, height: int, t: float) -> np.ndarray:
    frame, band = _blank(width, height), width // 4
    for i, (colour, letter) in enumerate(zip((RED, GREEN, BLUE, WHITE), "RGBW")):
        frame[:, i * band:(i + 1) * band] = colour
        _cut(frame, letter, i * band + (band - CELL_W) // 2, 2)
    return frame


def index(width: int, height: int, t: float) -> np.ndarray:
    frame = _blank(width, height)
    frame[0, ::8] = DIM
    frame[::8, 0] = DIM
    for x in range(PANEL_W, width, PANEL_W):       # a seam at every panel edge inside the wall
        frame[:, x - 1] = CYAN
        frame[:, x] = YELLOW
    for y in range(PANEL_H, height, PANEL_H):
        frame[y - 1, :] = CYAN
        frame[y, :] = YELLOW
    for (y, x), colour in zip(((0, 0), (0, width - 2), (height - 2, 0), (height - 2, width - 2)),
                              (RED, GREEN, BLUE, WHITE)):
        frame[y:y + 2, x:x + 2] = colour
    return frame


def gamma(width: int, height: int, t: float) -> np.ndarray:
    frame, third, half = _blank(width, height), width // 3, height // 2
    frame[:half, :third] = 128
    yy, xx = np.mgrid[:half, :third]
    frame[:half, third:2 * third] = (((yy + xx) % 2) * 255)[..., None]
    frame[:half, 2 * third:3 * third] = 186          # 255 * 0.5 ** (1 / 2.2): half the light under gamma 2.2
    ramp = np.round((np.arange(width) * 16 // width) * 255 / 15).astype(np.uint8)
    frame[height - height // 4:] = ramp[None, :, None]
    return frame


def step_of(t: float) -> int:
    return int(max(t, 0.0) // STEP_SECONDS) % len(STEPS)


def steps(width: int, height: int, t: float) -> np.ndarray:
    frame = _blank(width, height)
    frame[2:height - 4, width // 4:3 * width // 4] = LEVEL
    frame[height - 2:, :(step_of(t) + 1) * width // len(STEPS)] = LEVEL
    return frame


PATTERNS: dict[str, Callable[[int, int, float], np.ndarray]] = {"rgb": rgb, "index": index, "steps": steps,
                                                                "gamma": gamma}


def _refusal(pattern: str, brightness: float) -> str | None:
    if pattern not in PATTERNS:
        return f"wall_pattern: unknown pattern {pattern!r}; choose from {', '.join(sorted(PATTERNS))}"
    if not (isinstance(brightness, (int, float)) and math.isfinite(brightness) and 0.0 < brightness <= CAP):
        return f"wall_pattern: brightness must be over 0 and at most {CAP} (the power supply cap), got {brightness!r}"
    return None


def run(pattern: str, display, width: int, height: int, brightness: float = 0.1, seconds: float = 0.0,
        fps: float = 20.0, clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep, out: Callable[[str], None] = print) -> int:
    """Show pattern on display until seconds have passed (0: until Ctrl-C), then two black frames (the card
    shows a frame when the next one starts) and close. Returns 0, or 2 without touching the display when the
    pattern is unknown or the brightness is not in (0, CAP]."""
    refusal = _refusal(pattern, brightness)
    if refusal:
        out(refusal)
        return 2
    out(f"{pattern} at {width}x{height}, brightness {brightness:g}. Ctrl-C to stop.")
    out(LOOK_FOR[pattern])
    out(f"Write what the panel shows into {HARDWARE_MD}.")
    level = brightness * STEPS[0] if pattern == "steps" else brightness
    try:
        display.set_brightness(level)
        start = clock()
        while True:
            t = clock() - start
            if seconds > 0 and t >= seconds:
                break
            if pattern == "steps" and brightness * STEPS[step_of(t)] != level:
                level = brightness * STEPS[step_of(t)]
                display.set_brightness(level)
            display.push(PATTERNS[pattern](width, height, t))
            sleep(1.0 / fps)
    except KeyboardInterrupt:
        pass
    finally:
        black = _blank(width, height)
        display.push(black)
        display.push(black)
        display.close()
    return 0


def save_png(pattern: str, width: int, height: int, path: str, scale: int = 8) -> None:
    from PIL import Image

    frame = PATTERNS[pattern](width, height, 0.0)
    Image.fromarray(frame).resize((width * scale, height * scale), Image.NEAREST).save(path)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="wall_pattern", description="Test patterns for the LED wall")
    p.add_argument("pattern", choices=sorted(PATTERNS))
    p.add_argument("--backend", default="colorlight", choices=["colorlight", "sdl", "ddp"])
    p.add_argument("--iface", default="eth0", help="the wired interface the card is on (colorlight)")
    p.add_argument("--width", type=int, default=128)
    p.add_argument("--height", type=int, default=64)
    p.add_argument("--brightness", type=float, default=0.1, help=f"over 0, at most {CAP}")
    p.add_argument("--seconds", type=float, default=0.0, help="0 runs until Ctrl-C")
    p.add_argument("--fps", type=float, default=20.0)
    p.add_argument("--sdl-scale", type=int, default=8)
    p.add_argument("--ddp-host", default="127.0.0.1")
    p.add_argument("--ddp-port", type=int, default=4048)
    p.add_argument("--png", default="", help="save the pattern to this file and exit; no display is opened")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.png:
        save_png(args.pattern, args.width, args.height, args.png)
        print(f"wall_pattern: saved {args.pattern} to {args.png}")
        return 0
    refusal = _refusal(args.pattern, args.brightness)
    if refusal:
        print(refusal)
        return 2
    cfg = SimpleNamespace(backend=args.backend, width=args.width, height=args.height, iface=args.iface,
                          sdl_scale=args.sdl_scale, ddp_host=args.ddp_host, ddp_port=args.ddp_port,
                          brightness=args.brightness)
    try:
        display = make_display(cfg)
    except (OSError, ValueError) as e:
        print(f"wall_pattern: cannot open the {args.backend} display: {e}")
        return 1
    return run(args.pattern, display, args.width, args.height, brightness=args.brightness,
               seconds=args.seconds, fps=args.fps, sleep=time.sleep)


if __name__ == "__main__":
    sys.exit(main())
