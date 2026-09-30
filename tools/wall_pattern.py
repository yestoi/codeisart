"""Test patterns for the wall: the first light on the panels, and the answers the arcade's colours wait for.

    python tools/wall_pattern.py rgb   --iface eth0                  # pixel order
    python tools/wall_pattern.py index --iface eth0                  # every panel where it should be
    python tools/wall_pattern.py panels --iface eth0                 # each panel's row and column, "r,c"
    python tools/wall_pattern.py grid  --iface eth0                  # alignment and tearing: lines every 8 px
    python tools/wall_pattern.py border --iface eth0                 # the last row and column: a line on every edge
    python tools/wall_pattern.py steps --iface eth0 --brightness 0.4 # the sync's level byte
    python tools/wall_pattern.py gamma --iface eth0                  # who applies gamma
    python tools/wall_pattern.py rgb   --backend sdl                 # the same picture in a window
    python tools/wall_pattern.py rgb   --png rgb.png                 # or as a file, with no display
    python tools/wall_pattern.py rgb   --dry-run --seconds 30        # the driver's timing on this machine, no card
    python tools/wall_pattern.py panels --config show.toml           # the show's wall, cap and gamma

The colorlight backend needs Linux and CAP_NET_RAW (show/display/colorlight.py), so on the wall this runs
from the Omarchy box or a Pi, after the card's one-time LEDVision setup. The default is 128x64, the four
panels 2 x 2; `--width 128 --height 32` is one row of two panels, `--width 64 --height 64` a column.
It runs until Ctrl-C, or for --seconds, and leaves the wall dark. On the colorlight backend the driver sends 60.32
frames a second from a child process whatever --fps is (--fps paces the pushes only), and prints the sender's
timing at the end; --dry-run is that driver on a socket that discards, no card and no root. Brightness is the level
byte of the card's sync packet, 0.1 unless asked, and never over CAP (0.4, what the power supplies are sized for)
or the config's brightness_cap. No pattern lights half the wall (no `white`, Q64). Every frame passes the flash governor
(show.wall.GovernedDisplay) on its way to the display, as the show's do. `--config show.toml` takes the wall
from the show's config (backend, size, interface, DDP address, gamma, cap); a flag on the line wins. Each
pattern prints what to look for; write what the panel shows into docs/superpowers/workflow/evidence/hardware.md.
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

from show.config import load_config  # noqa: E402
from show.display.colorlight import ColorlightDisplay, DiscardSocket, stats_line  # noqa: E402
from show.display import make_display  # noqa: E402
from show.font import CELL_H, CELL_W, Font  # noqa: E402
from show.renderer import draw_text  # noqa: E402
from show.wall import GAMMA_MAX, GAMMA_MIN, GovernedDisplay  # noqa: E402

CAP = 0.4                     # the brightness the power supplies are sized for (arcade.toml, show.toml)
PANEL_W, PANEL_H = 64, 32      # one panel
LEVEL = 128                   # the byte the solid colours use
STEP_SECONDS = 2.0            # how long `steps` holds each level
STEPS = (0.125, 0.25, 0.5, 1.0)   # shares of --brightness, low to high
MAX_FPS = 60.0                # the push rate the tool refuses over
STOP_AT_S = 5.0               # --stop-for: the stream is stopped this far into the run
BACKENDS = ("colorlight", "sdl", "ddp")   # the displays the tool can choose; a config's `fake` is refused


def dry_display(width: int, height: int, brightness: float, **kw):
    """The driver on a socket that keeps nothing: its timing with no card and no root (--dry-run)."""
    return ColorlightDisplay(width, height, "", sock=DiscardSocket(), brightness=brightness, **kw)
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
             "before. No change at all: the card ignores the sync's level on this firmware (write the firmware "
             "version; on 13.17 it obeys it when the sync's byte 36 is 05, measured 2026-09-30). Uneven steps: "
             "write which ones.",
    "gamma": "Top row, from a few metres so the middle patch blends: a grey patch (128), a fine checker, a "
             "lighter patch (186). The checker matches the LEFT patch: the card sends bytes as they are, keep "
             "gamma = 2.2 in arcade.toml. It matches the RIGHT patch: the card applies gamma, set gamma = 1.0. "
             "Bottom: 16 grey steps from black to white; write how many of the dark ones you can tell apart.",
    "grid": "Thin white lines every 8 pixels, across and down, the first along the top and the left edge. A line "
            "that breaks, doubles or steps sideways at a panel edge: the panels are misaligned or the LEDVision "
            "layout is wrong. Lines that shimmer or tear while it runs: write where.",
    "border": "One thin white line along all four edges of the wall, and nothing inside it. An edge with no line, "
              "or a line one pixel in from the edge: the card's width or height is not the wall's, or the last "
              "row or column of a panel is dead; write which edge.",
    "panels": "Each panel shows its row and column, \"r,c\", in white at its top left: 0,0 top left, 0,1 to its "
              "right, 1,0 below it. A label in the wrong place, mirrored or upside down: the panels are swapped, "
              "rotated or chained the other way; write what each panel shows.",
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


def grid(width: int, height: int, t: float) -> np.ndarray:
    frame = _blank(width, height)
    frame[::8] = WHITE
    frame[:, ::8] = WHITE
    return frame


def border(width: int, height: int, t: float) -> np.ndarray:
    frame = _blank(width, height)
    frame[0] = frame[-1] = WHITE
    frame[:, 0] = frame[:, -1] = WHITE
    return frame


def panels(width: int, height: int, t: float) -> np.ndarray:
    frame, font = _blank(width, height), Font.load(FONT_PATH)
    for r in range(height // PANEL_H):
        for c in range(width // PANEL_W):
            draw_text(frame, c * PANEL_W + 2, r * PANEL_H + 2, f"{r},{c}", font, WHITE)
    return frame


PATTERNS: dict[str, Callable[[int, int, float], np.ndarray]] = {"rgb": rgb, "index": index, "steps": steps,
                                                                "gamma": gamma, "grid": grid, "border": border,
                                                                "panels": panels}


def _number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def governor_fps(fps: float) -> int:
    """The governor's frames a second: never under the push rate, so its window is never under a real second."""
    return max(2, math.ceil(fps))


def _refusal(pattern: str, brightness: float, cap: float = CAP) -> str | None:
    limit = min(cap, CAP)
    if pattern not in PATTERNS:
        return f"wall_pattern: unknown pattern {pattern!r}; choose from {', '.join(sorted(PATTERNS))}"
    if not (_number(brightness) and math.isfinite(brightness) and 0.0 < brightness <= limit):
        return (f"wall_pattern: brightness must be over 0 and at most {limit:g} (the power supply cap), "
                f"got {brightness!r}")
    return None


def _rate_refusal(fps: float, gamma: float) -> str | None:
    if not (_number(fps) and math.isfinite(fps) and 0.0 < fps <= MAX_FPS):
        return f"wall_pattern: fps must be over 0 and at most {MAX_FPS:g}, got {fps!r}"
    if not (_number(gamma) and GAMMA_MIN <= gamma <= GAMMA_MAX):
        return (f"wall_pattern: gamma must be {GAMMA_MIN} (the card applies gamma) to {GAMMA_MAX} (bytes as they "
                f"are), got {gamma!r}")
    return None


def run(pattern: str, display, width: int, height: int, brightness: float = 0.1, seconds: float = 0.0,
        fps: float = 20.0, clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep, out: Callable[[str], None] = print,
        gamma: float = 2.2, cap: float = CAP, stop_for: float = 0.0) -> int:
    """Show pattern on display, every frame through the flash governor, a push due every 1/fps after the last was
    due (a late one runs at once and the grid restarts from it), until seconds have passed (0: until Ctrl-C);
    then the sender's stats, said, and the governed wall closed: two governed black frames, then the display's
    own close. Returns 0; 1 after an OSError from the display or from the close, said, the wall closed; or 2
    without touching the display when the pattern is unknown, the brightness is not in (0, min(cap, CAP)], the
    fps not in (0, MAX_FPS] or the gamma not in [GAMMA_MIN, GAMMA_MAX]. The display is reached only through the
    wall. stop_for > 0: STOP_AT_S into the run the display is paused (the driver's own stop, as after a failed
    send) and nothing is pushed for stop_for seconds; the push after that restarts the stream: the owner's Q66
    check at the wall (the picture stays, steady, no blink at the stop or the restart)."""
    refusal = _refusal(pattern, brightness, cap) or _rate_refusal(fps, gamma)
    if refusal:
        out(refusal)
        return 2
    wall = GovernedDisplay(display, height, width, governor_fps(fps), gamma, from_dark=True)   # no clock: no hold
    out(f"{pattern} at {width}x{height}, brightness {brightness:g}. Ctrl-C to stop.")
    out(LOOK_FOR[pattern])
    out(f"Write what the panel shows into {HARDWARE_MD}.")
    # `steps` sets the device brightness, which the governor does not see: at most once every STEP_SECONDS,
    # and never over brightness, itself at most min(cap, CAP).
    level = brightness * STEPS[0] if pattern == "steps" else brightness
    code = 0
    stopped = None                       # when the stream was stopped (--stop-for), or None
    try:
        wall.set_brightness(level)
        start = clock()
        period = 1.0 / fps
        due = start + period                 # when the second push is due; the clock is read once a push
        now = clock()
        while True:
            t = now - start
            if seconds > 0 and t >= seconds:
                break
            if pattern == "steps" and brightness * STEPS[step_of(t)] != level:
                level = brightness * STEPS[step_of(t)]
                wall.set_brightness(level)
            if stop_for > 0 and stopped is None and t >= STOP_AT_S:
                stopped = t
                pause = getattr(display, "pause", None)
                if pause is not None:
                    pause()
                out(f"wall_pattern: stopped the stream for {stop_for:g} s at {t:.1f} s: the picture should stay, "
                    "steady, with no blink at the stop or at the restart")
            if stopped is None or t >= stopped + stop_for:
                wall.push(PATTERNS[pattern](width, height, t))
            now = clock()
            if now < due:                    # on time: sleep to the deadline, the next one a period after it
                sleep(due - now)
                now, due = due, due + period
            else:                            # late: the next push runs at once, the grid restarts from now
                due = now + period           # (as arcade/runner.py: no catch-up burst)
    except KeyboardInterrupt:
        pass
    except OSError as e:
        out(f"wall_pattern: the display failed: {e}")
        code = 1
    finally:
        line = stats_line(display)
        if line:
            out(line)
        try:
            wall.close()    # the counted frame again if its send failed, then governed black, then closed
        except OSError as e:                 # a torn burst's error, carried back into the close's own black:
            out(f"wall_pattern: closing the wall failed: {e}")   # the display's close has still landed black
            code = 1
    return code


def save_png(pattern: str, width: int, height: int, path: str, scale: int = 8) -> None:
    from PIL import Image

    frame = PATTERNS[pattern](width, height, 0.0)
    Image.fromarray(frame).resize((width * scale, height * scale), Image.NEAREST).save(path)


def build_parser(defaults: bool = True) -> argparse.ArgumentParser:
    """The flags; with defaults=False a flag not on the line is left out of the result (what --config fills)."""
    def d(value):
        return value if defaults else argparse.SUPPRESS

    p = argparse.ArgumentParser(prog="wall_pattern", description="Test patterns for the LED wall")
    p.add_argument("pattern", choices=sorted(PATTERNS))
    p.add_argument("--config", default=d(""), help="take the wall from this show config (show.toml); flags win")
    p.add_argument("--backend", default=d("colorlight"), choices=list(BACKENDS))
    p.add_argument("--iface", default=d("eth0"), help="the wired interface the card is on (colorlight)")
    p.add_argument("--width", type=int, default=d(128))
    p.add_argument("--height", type=int, default=d(64))
    p.add_argument("--brightness", type=float, default=d(0.1), help=f"over 0, at most {CAP} and the config's cap")
    p.add_argument("--seconds", type=float, default=d(0.0), help="0 runs until Ctrl-C")
    p.add_argument("--fps", type=float, default=d(20.0), help=f"over 0, at most {MAX_FPS:g}")
    p.add_argument("--gamma", type=float, default=d(2.2),
                   help=f"the governor's light model, {GAMMA_MIN} to {GAMMA_MAX}")
    p.add_argument("--sdl-scale", type=int, default=d(8))
    p.add_argument("--ddp-host", default=d("127.0.0.1"))
    p.add_argument("--ddp-port", type=int, default=d(4048))
    p.add_argument("--png", default=d(""), help="save the pattern to this file and exit; no display is opened")
    p.add_argument("--dry-run", action="store_true",
                   help="the colorlight driver on a socket that discards: its timing alone, no card, no root")
    p.add_argument("--stop-for", type=float, default=d(0.0),
                   help=f"stop the stream {STOP_AT_S:g} s into the run for this many seconds (the Q66 check)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cap = CAP
    if args.config:
        try:
            cfg = load_config(Path(args.config))
        except (OSError, ValueError) as e:
            print(f"wall_pattern: cannot load {args.config}: {e}")
            return 2
        given = vars(build_parser(defaults=False).parse_args(argv))
        for name, value in (("backend", cfg.backend), ("width", cfg.width), ("height", cfg.height),
                            ("iface", cfg.colorlight_iface), ("ddp_host", cfg.ddp_host),
                            ("ddp_port", cfg.ddp_port), ("gamma", cfg.gamma)):
            if name not in given:
                setattr(args, name, value)
        cap = min(CAP, cfg.brightness_cap)
    if args.png:
        save_png(args.pattern, args.width, args.height, args.png)
        print(f"wall_pattern: saved {args.pattern} to {args.png}")
        return 0
    if args.dry_run:
        refusal = _refusal(args.pattern, args.brightness, cap) or _rate_refusal(args.fps, args.gamma)
        if refusal:
            print(refusal)
            return 2
        display = dry_display(args.width, args.height, args.brightness)
        return run(args.pattern, display, args.width, args.height, brightness=args.brightness,
                   seconds=args.seconds, fps=args.fps, sleep=time.sleep, gamma=args.gamma, cap=cap,
                   stop_for=args.stop_for)
    if args.backend not in BACKENDS:
        print(f"wall_pattern: the tool has no {args.backend!r} display; choose --backend from {', '.join(BACKENDS)}")
        return 2
    refusal = _refusal(args.pattern, args.brightness, cap) or _rate_refusal(args.fps, args.gamma)
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
               seconds=args.seconds, fps=args.fps, sleep=time.sleep, gamma=args.gamma, cap=cap,
               stop_for=args.stop_for)


if __name__ == "__main__":
    sys.exit(main())
