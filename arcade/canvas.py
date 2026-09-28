"""Canvas (spec 7.4): drawing over a (height, width, 3) uint8 frame. Everything clips; nothing raises or hangs."""
from __future__ import annotations

import math

import numpy as np

from show.font import CELL_H, CELL_W, Font

Color = tuple[int, int, int]

_FAR = 1 << 20   # coordinates are clamped to plus or minus this; NaN, infinity and garbage land at -_FAR


def _i(v) -> int:
    """A coordinate as an int: rounded half up (so 0.5 px steps are even), clamped to plus or minus _FAR.

    A huge number clamps to its end, a Python int too (10**400 is past any float but lands at _FAR like
    1e300). NaN, infinity and anything that is not a number land at -_FAR (05-plan S4). So a huge width
    or radius fills, an infinite width draws nothing, and an infinite, NaN, negative or sub-half-pixel
    radius draws only the centre pixel, for circle as for fill_circle: harmless either way, and nothing
    hangs."""
    if isinstance(v, int):
        return max(-_FAR, min(_FAR, v))
    try:
        return max(-_FAR, min(_FAR, math.floor(v + 0.5)))
    except (ValueError, OverflowError, TypeError):
        return -_FAR


def _channel(v) -> int:
    try:
        return max(0, min(255, math.floor(v + 0.5)))
    except OverflowError:
        return 255 if v > 0 else 0
    except (ValueError, TypeError):
        return 0


def _c(color) -> Color:
    """A colour as three ints clamped to 0..255; NaN is 0."""
    r, g, b = color
    return (_channel(r), _channel(g), _channel(b))


def sprite_from_rows(rows: list[str], palette: dict[str, Color]) -> np.ndarray:
    """An (h, w, 3) uint8 sprite from equal-length rows of palette characters; "." is always black."""
    lut = {**{k: _c(v) for k, v in palette.items()}, ".": (0, 0, 0)}
    widths = {len(r) for r in rows}
    if len(widths) > 1:
        raise ValueError(f"sprite rows differ in length: {sorted(widths)}")
    out = np.zeros((len(rows), widths.pop() if widths else 0, 3), np.uint8)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch not in lut:
                raise ValueError(f"sprite character {ch!r} at row {y}, column {x} is not in the palette")
            out[y, x] = lut[ch]
    return out


class Canvas:
    """Drawing over an (h, w, 3) uint8 frame. Coordinates may be int or float and are rounded; colours are
    clamped to 0..255. Out-of-range drawing clips, never raises, never hangs."""

    sprite_from_rows = staticmethod(sprite_from_rows)

    def __init__(self, width: int, height: int, font: Font):
        self.width, self.height = width, height
        self.font = font
        self.frame = np.zeros((height, width, 3), dtype=np.uint8)

    @property
    def size(self) -> tuple[int, int]:
        return (self.width, self.height)

    def clear(self, color: Color = (0, 0, 0)) -> None:
        self.frame[:] = _c(color)

    def pixel(self, x, y, color: Color) -> None:
        x, y = _i(x), _i(y)
        if 0 <= x < self.width and 0 <= y < self.height:
            self.frame[y, x] = _c(color)

    def fill_rect(self, x, y, w, h, color: Color) -> None:
        x, y, w, h = _i(x), _i(y), _i(w), _i(h)
        x0, y0 = max(x, 0), max(y, 0)
        x1, y1 = min(x + w, self.width), min(y + h, self.height)
        if x0 < x1 and y0 < y1:
            self.frame[y0:y1, x0:x1] = _c(color)

    def rect(self, x, y, w, h, color: Color) -> None:
        x, y, w, h = _i(x), _i(y), _i(w), _i(h)
        if w <= 0 or h <= 0:
            return
        self.fill_rect(x, y, w, 1, color)
        self.fill_rect(x, y + h - 1, w, 1, color)
        self.fill_rect(x, y, 1, h, color)
        self.fill_rect(x + w - 1, y, 1, h, color)

    def line(self, x0, y0, x1, y1, color: Color) -> None:
        """Bresenham. A line with an endpoint beyond four times the canvas extent is skipped (spec 7.4)."""
        x0, y0, x1, y1 = _i(x0), _i(y0), _i(x1), _i(y1)
        if max(abs(x0), abs(y0), abs(x1), abs(y1)) > 4 * (self.width + self.height):
            return
        color = _c(color)
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            if 0 <= x0 < self.width and 0 <= y0 < self.height:
                self.frame[y0, x0] = color
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def _disc(self, cx, cy, r, color: Color, ring: bool) -> None:
        cx, cy, r = _i(cx), _i(cy), max(_i(r), 0)
        x0, y0 = max(cx - r, 0), max(cy - r, 0)
        x1, y1 = min(cx + r + 1, self.width), min(cy + r + 1, self.height)
        if x0 >= x1 or y0 >= y1:
            return
        yy, xx = np.ogrid[y0:y1, x0:x1]
        d2 = (xx - cx) ** 2 + (yy - cy) ** 2
        mask = d2 <= (r + 0.5) ** 2
        if ring and r > 0:                  # a ring of radius 0 is its centre pixel, as the disc is
            mask &= d2 >= (r - 0.5) ** 2
        self.frame[y0:y1, x0:x1][mask] = _c(color)

    def fill_circle(self, cx, cy, r, color: Color) -> None:
        self._disc(cx, cy, r, color, ring=False)

    def circle(self, cx, cy, r, color: Color) -> None:
        self._disc(cx, cy, r, color, ring=True)

    def _window(self, h: int, w: int, x: int, y: int):
        """The on-canvas part of an h by w sprite at (x, y), as (frame slices, sprite slices), or None."""
        x0, y0 = max(x, 0), max(y, 0)
        x1, y1 = min(x + w, self.width), min(y + h, self.height)
        if x0 >= x1 or y0 >= y1:
            return None
        return (slice(y0, y1), slice(x0, x1)), (slice(y0 - y, y1 - y), slice(x0 - x, x1 - x))

    def blit(self, mask: np.ndarray, x, y, color: Color) -> None:
        """Lights the True cells of a bool mask in one colour."""
        mask = np.asarray(mask, bool)
        win = self._window(*mask.shape, _i(x), _i(y))
        if win is not None:
            dst, src = win
            self.frame[dst][mask[src]] = _c(color)

    def blit_rgb(self, sprite: np.ndarray, x, y) -> None:
        """Copies an (h, w, 3) sprite; black pixels are transparent. A sprite that is not uint8 (a game's
        float buffer) is rounded half up and clamped to 0..255 first, NaN to 0, so black is judged after."""
        sprite = np.asarray(sprite)
        if sprite.dtype != np.uint8:
            v = np.floor(np.nan_to_num(sprite.astype(np.float64), nan=0.0, posinf=255.0, neginf=0.0) + 0.5)
            sprite = np.clip(v, 0, 255).astype(np.uint8)
        win = self._window(*sprite.shape[:2], _i(x), _i(y))
        if win is not None:
            dst, src = win
            sub = sprite[src]
            lit = sub.any(axis=2)
            self.frame[dst][lit] = sub[lit]

    def _scale(self, scale) -> int:
        """Text scale as an int from 1 to the canvas's larger side (a bigger glyph cannot show)."""
        return max(1, min(_i(scale), max(self.width, self.height)))

    def text_width(self, s, scale=1) -> int:
        return CELL_W * self._scale(scale) * len(str(s))

    def text(self, x, y, s, color: Color, scale=1) -> int:
        """Draws s in the 5x7 font, each glyph pixel scale by scale (2 gives 10 by 14 with 2 px strokes);
        returns the width drawn, text_width(s, scale). Characters past 255 draw as "?"."""
        s, k = str(s), self._scale(scale)
        x, y, color = _i(x), _i(y), _c(color)
        cell_w = CELL_W * k
        if y >= self.height or y + CELL_H * k <= 0:
            return self.text_width(s, k)
        atlas = self.font.atlas()
        for i in range(max(0, -x // cell_w), len(s)):        # glyphs wholly off the left edge are skipped
            cx, ch = x + i * cell_w, s[i]
            if cx >= self.width:
                break
            if cx + cell_w <= 0:
                continue
            glyph = atlas[ord(ch) if ord(ch) < 256 else ord("?")]
            if k > 1:
                glyph = glyph.repeat(k, axis=0).repeat(k, axis=1)
            self.blit(glyph, cx, y, color)
        return self.text_width(s, k)
