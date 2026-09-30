"""Bench (2026-09-30, the ghosting review, lane 05; not part of the package): the pictures that map the wall's
fainter second picture in one short session.

Modelled on the morning's ghost_test.py: the pictures are registered with tools/wall_pattern.py and run through
that tool's own main, so every frame passes the flash governor (show.wall.GovernedDisplay) and the wall is closed
by the driver's own close. Nothing here sends anything itself. Every picture is still for --hold seconds (6
unless asked, never under 3), so no pixel changes more than once in 3 s and the governor holds nothing; the most
any picture lights is 12 % of the wall (picture 6). Pixel bytes go to the card as drawn: --brightness is the
card's own level (the sync and brightness packets), never a scaling of the bytes.

    1a 1b 1c 1d  one single row at full value, stepping through the 16 rows of a half: 1a rows 0-15, 1b 16-31
                 (the top panels), 1c 32-47, 1d 48-63 (the bottom panels). The label gives the wall row.
    2   the same row lit over 1, 4, 16, 64 and 128 pixels in turn (the first three start at column 24)
    3   a level ladder on one row: 32, 64, 96, 128, 160, 192, 224, 255 left to right; red, green, blue, white
    4   left panel against right panel: a row alone against the row and its partner on the same scan line
        (8 away), then against the row and the one on line k + 4; each pair shown both ways round
    5   one pixel; a column over 4 rows (lines 0 to 3 of the row's band); over the 16 rows of the half; full height
    6   a lit field 16 rows high on the left panel with one dark row stepping through it (the inverse)
    7   picture 8's first step at the pixel value that gives the same light at this --brightness as 255 gives
        at 0.1, if the card's level is linear and its gamma 2.8: run it at 0.1, 0.2 and 0.4
    8   the match: a source segment, and beside the place of its copy eight reference patches at 1, 2, 4, 7,
        10, 15, 25 and 40 % of the source's light (gamma 2.8); the source steps 255, 224, 192, 160, 128

The label sits in the other panel row (the other chain) from the rows under test, at pixel value 96. The ruler
(dim ticks at value 64 on the even rows at both ends of the wall: 3 pixels at rows 0, 8, 16, 24 of a panel, 2
at 4, 12, 20, 28, 1 at the rest) is there to count rows in a photograph; --no-ruler removes it.

This script's own flags (the rest go to wall_pattern.py: --iface, --brightness, --seconds, --fps, --stop-for,
--dry-run, --png, --width, --height):

    --hold S      seconds a step is held (6; at least 3)
    --step N      stay on step N (0 is the first) for the whole run: for a long look, for --stop-for, for --png
    --value V     the full pixel value (255)
    --row R       the wall row pictures 2 to 8 work on (2: scan line 2 of the top half)
    --channel C   r, g, b or w: the colour of the lit pixels in every picture but 3 (w)
    --offset N    picture 7 and 8: the row of the reference patches, counted from --row (4)
    --no-ruler    no ruler

    cd ~/codeisart && sudo .venv/bin/python docs/superpowers/reviews/2026-09-30-ghosting/ghost_map.py 1a \
        --iface eth0 --seconds 100
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np


def _root() -> Path:
    """The repository: above this file where it lives in the repo, or the working directory (a copy in ~/bench)."""
    for p in (*Path(__file__).resolve().parents, Path.cwd()):
        if (p / "tools" / "wall_pattern.py").is_file():
            return p
    raise SystemExit("ghost_map: tools/wall_pattern.py not found: run it from the repository (cd ~/codeisart)")


ROOT = _root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from show.font import CELL_H, CELL_W, Font  # noqa: E402
from show.renderer import draw_text  # noqa: E402
from tools import wall_pattern as wp  # noqa: E402

HALF = 16                 # the rows one data set (R1 or R2) feeds: a scan line lights two of them, 8 apart
LINES = 8                 # scan lines: row r is on line r % 8
CARD_GAMMA = 2.8          # the card's saved gamma: light is (byte / 255) ** 2.8
BASE_BRIGHTNESS = 0.1     # picture 7's reference level
MIN_HOLD = 3.0            # no step is shorter: a pixel changes at most once in this long
LABEL = 96                # the label's pixel value: 6.5 % of full light under gamma 2.8
RULER = 64                # the ruler's: 2 %, under which the morning's pictures showed no copy
MARGIN = 6                # columns kept at each end of the wall for the ruler
ANCHOR = 24               # picture 2: where the 1, 4 and 16 pixel segments start
COLUMN = 20               # picture 5: the pixel's and the column's x
LENGTHS = (1, 4, 16, 64, 128)
LEVELS = (32, 64, 96, 128, 160, 192, 224, 255)
SOURCES = (255, 224, 192, 160, 128)                       # picture 8: the source's values, in turn
SHARES = (0.01, 0.02, 0.04, 0.07, 0.10, 0.15, 0.25, 0.40)  # its patches: shares of the source's light
SOURCE_W = 28             # picture 7 and 8: the source segment's width
CHANNELS = {"r": (1, 0, 0), "g": (0, 1, 0), "b": (0, 0, 1), "w": (1, 1, 1)}
NAMES = {"r": "red", "g": "green", "b": "blue", "w": "white"}

S = SimpleNamespace(hold=6.0, step=None, value=255, row=2, channel="w", offset=4, ruler=True,
                    brightness=BASE_BRIGHTNESS)
_font: Font | None = None


def ink(value: int, channel: str | None = None) -> tuple[int, int, int]:
    return tuple(value * c for c in CHANNELS[channel or S.channel])


def partner8(row: int) -> int:
    """The other row of the half on the same scan line."""
    top = row - row % HALF
    return top + (row % HALF + LINES) % HALF


def partner4(row: int) -> int:
    """The row of the same band (the 8 rows one data bit position reaches) on scan line (k + 4) % 8."""
    band = row - row % LINES
    return band + (row % LINES + LINES // 2) % LINES


def share_value(value: int, share: float) -> int:
    """The pixel value whose light is `share` of value's, under the card's gamma."""
    return round(value * share ** (1.0 / CARD_GAMMA))


def equal_light_value(value: int, brightness: float) -> int:
    """The pixel value that gives at `brightness` the light `value` gives at BASE_BRIGHTNESS (a linear level)."""
    return min(255, round(value * (BASE_BRIGHTNESS / brightness) ** (1.0 / CARD_GAMMA)))


def _blank(width: int, height: int) -> np.ndarray:
    return np.zeros((height, width, 3), np.uint8)


def _span(width: int) -> tuple[int, int]:
    m = MARGIN if S.ruler else 0
    return m, width - m


def label(frame: np.ndarray, text: str, row: int) -> None:
    """text at LABEL in the panel row the test row is not in: bottom right for the top panels, top right for the
    bottom ones."""
    global _font
    if _font is None:
        _font = Font.load(wp.FONT_PATH)
    h, w = frame.shape[:2]
    y = h - CELL_H - 1 if row < h // 2 else 1
    draw_text(frame, w - len(text) * CELL_W - 1, y, text, _font, (LABEL,) * 3)


def ruler(frame: np.ndarray, row: int) -> None:
    """Ticks on the even rows of the test row's panel (both halves, so a copy that crosses is read too)."""
    if not S.ruler:
        return
    top = row - row % wp.PANEL_H
    for y in range(top, min(top + wp.PANEL_H, frame.shape[0]), 2):
        n = 3 if (y - top) % 8 == 0 else 2 if (y - top) % 4 == 0 else 1
        frame[y, :n] = RULER
        frame[y, -n:] = RULER


def rows_picture(half: int):
    def picture(width: int, height: int, i: int):
        frame, row = _blank(width, height), half * HALF + i
        ruler(frame, row)
        x0, x1 = _span(width)
        frame[row, x0:x1] = ink(S.value)
        return frame, f"r{row:02d}", row
    return picture


def lengths(width: int, height: int, i: int):
    frame, n = _blank(width, height), LENGTHS[i]
    x0 = ANCHOR if n <= 16 else 0          # 64 is the left panel's whole row, 128 the wall's; no ruler here
    frame[S.row, x0:x0 + n] = ink(S.value)
    return frame, f"n{n}", S.row


def ladder(width: int, height: int, i: int):
    frame, channel = _blank(width, height), "rgbw"[i]
    ruler(frame, S.row)
    x0, x1 = _span(width)
    pitch = (x1 - x0) // len(LEVELS)
    for j, level in enumerate(LEVELS):
        a = x0 + j * pitch + 2
        frame[S.row, a:a + pitch - 4] = ink(level, channel)
    return frame, NAMES[channel], S.row


def pairs(width: int, height: int, i: int):
    frame = _blank(width, height)
    ruler(frame, S.row)
    a, a8, a4 = S.row, partner8(S.row), partner4(S.row)
    left, right = (((a,), (a, a8)), ((a, a8), (a,)), ((a,), (a, a4)), ((a, a4), (a,)),
                   ((a4,), (a, a4)), ((a, a4), (a4,)))[i]
    x0, x1 = _span(width)
    for rows, (c0, c1) in ((left, (x0, width // 2 - 2)), (right, (width // 2 + 2, x1))):
        for r in rows:
            frame[r, c0:c1] = ink(S.value)
    return frame, "|".join("+".join(str(r) for r in rows) for rows in (left, right)), S.row


def points(width: int, height: int, i: int):
    frame = _blank(width, height)
    ruler(frame, S.row)
    band, top = S.row - S.row % LINES, S.row - S.row % HALF
    if i == 0:
        frame[S.row, COLUMN] = ink(S.value)
        return frame, "pixel", S.row
    y0, y1 = ((band, band + LINES // 2), (top, top + HALF), (0, height))[i - 1]
    frame[y0:y1, COLUMN] = ink(S.value)
    return frame, f"col{y1 - y0}", S.row


def inverse(width: int, height: int, i: int):
    frame, top = _blank(width, height), S.row - S.row % HALF
    ruler(frame, S.row)
    x0, _ = _span(width)
    frame[top:top + HALF, x0:width // 2] = ink(S.value)
    frame[top + i, x0:width // 2] = 0
    return frame, f"d{top + i:02d}", S.row


def _match(width: int, height: int, value: int) -> np.ndarray:
    frame = _blank(width, height)
    ruler(frame, S.row)
    x0, x1 = _span(width)
    frame[S.row, x0:x0 + SOURCE_W] = ink(value)
    a0 = x0 + SOURCE_W + 4
    pitch = (x1 - a0) // len(SHARES)
    for j, share in enumerate(SHARES):
        a = a0 + j * pitch
        frame[S.row + S.offset, a:a + pitch - 3] = ink(share_value(value, share))
    return frame


def match(width: int, height: int, i: int):
    return _match(width, height, SOURCES[i]), f"s{SOURCES[i]}", S.row


def equal_light(width: int, height: int, i: int):
    value = equal_light_value(S.value, S.brightness)
    return _match(width, height, value), f"v{value}", S.row


# name: (the picture, its steps, what to look for)
PICTURES = {
    "1a": (rows_picture(0), HALF, ""), "1b": (rows_picture(1), HALF, ""),
    "1c": (rows_picture(2), HALF, ""), "1d": (rows_picture(3), HALF, ""),
    "2": (lengths, len(LENGTHS),
          "One row lit over 1, 4, 16, 64 and 128 pixels in turn (the label: n1 to n128). Photograph each step "
          "with the same locked exposure. Look at the copy under columns 24 to 27, which are lit in every step: "
          "the same in every step, or stronger as more of the row is lit? Write which."),
    "3": (ladder, 4,
          "Eight segments on one row, pixel values 32, 64, 96, 128, 160, 192, 224, 255 from the left; red, "
          "green, blue, then white. Two photographs a step: one with the exposure down until the 255 segment "
          "no longer clips, one two stops brighter for the dim end. Write, for each colour, the lowest segment "
          "that has a copy, and whether the copy of a white segment is white."),
    "4": (pairs, 6,
          "Left panel against right panel; the label says which rows each side lights (left|right). Steps 0 and "
          "1: a row alone against the row and its partner on the same scan line. Steps 2 and 3: a row alone "
          "against the row and the one on scan line k + 4. Steps 4 and 5: the k + 4 row alone against both. Is "
          "the copy stronger on the side with two rows? With both k and k + 4 lit, is there a copy anywhere, "
          "and on which row?"),
    "5": (points, 4,
          "One pixel; then a column 4 rows long; then 16 rows (the whole half); then the wall's full height. "
          "The pixel: is its copy one pixel, in the same column, and on which row? The 4-row column: how many "
          "rows look lit? The 16-row and the full column: any light in the columns beside it, or past its ends?"),
    "6": (inverse, HALF,
          "A lit block 16 rows high on the left panel with one dark row stepping down it (the label: the dark "
          "row). Is the dark row fully dark, or does it glow? Is another row of the block dimmer than its "
          "neighbours, and how many rows from the dark one, above or below?"),
    "7": (equal_light, 1,
          "Run at --brightness 0.1, 0.2 and 0.4. The source segment (top left) should look equally bright in "
          "all three; if it does not, the card's level is not linear: write that. The copy under it: the same "
          "in all three, or weaker at the higher level? Which patch to its right matches it (patches are 1, 2, "
          "4, 7, 10, 15, 25, 40 % of the source, left to right)?"),
    "8": (match, len(SOURCES),
          "A source segment at the left, stepping 255, 224, 192, 160, 128 (the label: s255 ...). To the right, "
          "on the row --offset below it, eight patches at 1, 2, 4, 7, 10, 15, 25 and 40 % of the source's "
          "light, left to right. Which patch is as bright as the source's copy? Write its number (1 to 8 from "
          "the left) for each step; photograph each with the exposure low enough that patch 8 does not clip. If "
          "the copy is not on the patches' row, give --offset the row it is on (from picture 1)."),
}
ROWS_LOOK = ("One single row across the wall, moving down a row every step; the label gives the wall row (r00 "
             "to r63; its scan line is the row number modulo 8). For every step: on which row is the fainter "
             "copy (count with the ruler's ticks at the wall's ends: every second row, longer at every fourth "
             "and eighth), is there a second copy, and does any copy fall in the other half of the panel or on "
             "the other panel row? Photograph each step, the exposure locked and turned down until the lit row "
             "no longer clips.")


def pattern(name: str):
    picture, count, _ = PICTURES[name]

    def fn(width: int, height: int, t: float) -> np.ndarray:
        i = S.step % count if S.step is not None else int(max(t, 0.0) // S.hold) % count
        frame, text, row = picture(width, height, i)
        label(frame, f"{name} {text}", row)
        return frame
    fn.__name__ = f"ghost_map_{name}"
    return fn


def own_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    p.add_argument("--hold", type=float, default=S.hold)
    p.add_argument("--step", type=int, default=None)
    p.add_argument("--value", type=int, default=S.value)
    p.add_argument("--row", type=int, default=S.row)
    p.add_argument("--channel", choices=sorted(CHANNELS), default=S.channel)
    p.add_argument("--offset", type=int, default=S.offset)
    p.add_argument("--no-ruler", action="store_true")
    return p


def _refusal(name: str, width: int, height: int) -> str | None:
    if not S.hold >= MIN_HOLD:
        return f"ghost_map: --hold must be at least {MIN_HOLD:g} s, got {S.hold!r}"
    if S.step is not None and S.step < 0:
        return f"ghost_map: --step must be 0 or more, got {S.step!r}"
    if not 1 <= S.value <= 255:
        return f"ghost_map: --value must be 1 to 255, got {S.value!r}"
    if width < 2 * wp.PANEL_W or width % wp.PANEL_W or height % HALF:
        return f"ghost_map: the pictures want a wall at least two panels wide, in whole panels, got {width}x{height}"
    if not 0 <= S.row < height:
        return f"ghost_map: --row must be 0 to {height - 1}, got {S.row!r}"
    if name in ("7", "8") and not 0 <= S.row + S.offset < height:
        return f"ghost_map: --row plus --offset must be 0 to {height - 1}, got {S.row + S.offset}"
    if name in ("1b", "1c", "1d") and ("1a", "1b", "1c", "1d").index(name) * HALF >= height:
        return f"ghost_map: picture {name} is below a wall {height} rows high"
    if name == "7" and not S.brightness >= BASE_BRIGHTNESS:
        return (f"ghost_map: picture 7 needs --brightness {BASE_BRIGHTNESS:g} or more (under it the value would "
                f"pass 255), got {S.brightness!r}")
    return None


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    if not argv or "-h" in argv or "--help" in argv:
        print(__doc__)
        return 0
    own, rest = own_parser().parse_known_args(argv)
    if "--config" in rest:
        print("ghost_map: no --config here: give the wall by --width and --height")
        return 2
    S.hold, S.step, S.value, S.row, S.channel = own.hold, own.step, own.value, own.row, own.channel
    S.offset, S.ruler = own.offset, not own.no_ruler
    for name, (_, _, look) in PICTURES.items():
        wp.PATTERNS[name] = pattern(name)
        wp.LOOK_FOR[name] = look or ROWS_LOOK
    args = wp.build_parser().parse_args(rest)      # the tool's own parse: an unknown picture or flag ends here
    S.brightness = args.brightness
    refusal = _refusal(args.pattern, args.width, args.height) if args.pattern in PICTURES else None
    if refusal:
        print(refusal)
        return 2
    return wp.main(rest)


if __name__ == "__main__":
    sys.exit(main())
