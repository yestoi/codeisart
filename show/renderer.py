"""Terminal cells to wall pixels: a 6x8 dot-matrix font in one phosphor color, and the strip on the last row."""
from __future__ import annotations

import numpy as np
import pyte

from show.font import CELL_H, CELL_W, Font

NORMAL = 0.7            # normal text at 70 % of the phosphor, bold at 100 %
QUESTION = ord("?")     # stands in for anything outside Latin-1


def _code(ch: str) -> int:
    code = ord(ch)
    return code if code < 256 else QUESTION


class Renderer:
    def __init__(self, font: Font, width: int, height: int, columns: int, rows: int,
                 phosphor: tuple[int, int, int], glow: bool = False):
        if columns * CELL_W > width or rows * CELL_H > height:
            raise ValueError(f"{columns}x{rows} terminal does not fit a {width}x{height} display")
        self.width, self.height, self.columns, self.rows = width, height, columns, rows
        self.glow = glow
        self.x0 = (width - columns * CELL_W) // 2
        self.y0 = (height - rows * CELL_H) // 2
        self._atlas = font.atlas()
        bold_rgb = np.array(phosphor, dtype=np.float64)
        # palette index 0 black, 1 normal, 2 bold
        self._palette = np.array([(0, 0, 0), bold_rgb * NORMAL, bold_rgb], dtype=np.float64).astype(np.uint8)
        self._frame: np.ndarray | None = None
        self._screen: pyte.Screen | None = None
        self._key: tuple | None = None

    def render(self, screen: pyte.Screen, cursor_on: bool = False, strip: str = "", *,
               full_screen: bool = False, strip_visible: bool = True) -> np.ndarray:
        """The frame, (height, width, 3) uint8 at full phosphor; read-only, and the same object while nothing changed."""
        cursor = screen.cursor
        key = (cursor.x, cursor.y, cursor.hidden, cursor_on, strip, full_screen, strip_visible)
        if self._frame is not None and screen is self._screen and not screen.dirty and key == self._key:
            return self._frame
        frame = self._draw(screen, cursor_on, strip, not full_screen or strip_visible)
        screen.dirty.clear()
        frame.flags.writeable = False
        self._frame, self._screen, self._key = frame, screen, key
        return frame

    def _draw(self, screen: pyte.Screen, cursor_on: bool, strip: str, show_strip: bool) -> np.ndarray:
        rows, columns = self.rows, self.columns
        program_rows = rows - 1 if show_strip else rows
        codes = np.full((rows, columns), 32, dtype=np.intp)
        level = np.ones((rows, columns), dtype=np.uint8)       # 1 normal, 2 bold
        rev = np.zeros((rows, columns), dtype=bool)
        buffer = screen.buffer
        for y in range(min(program_rows, screen.lines)):
            line = buffer.get(y)
            if not line:
                continue
            code_row, level_row, rev_row = codes[y], level[y], rev[y]
            for x, ch in line.items():
                if x >= columns:
                    continue
                data = ch.data
                if data:
                    code = ord(data[0])
                    code_row[x] = code if code < 256 else QUESTION
                if ch.bold:
                    level_row[x] = 2
                if ch.reverse:
                    rev_row[x] = True
        if show_strip:
            codes[-1] = [_code(ch) for ch in strip[:columns].ljust(columns)]
            level[-1] = 1
            rev[-1] = True
        masks = self._atlas[codes] ^ rev[:, :, None, None]     # (rows, columns, 8, 6)
        if cursor_on and not screen.cursor.hidden:
            cy, cx = screen.cursor.y, min(screen.cursor.x, screen.columns - 1)   # pending wrap: the last cell
            if 0 <= cy < min(program_rows, screen.lines) and 0 <= cx < columns:
                masks[cy, cx] = ~masks[cy, cx]
        index = masks * level[:, :, None, None]
        index = index.transpose(0, 2, 1, 3).reshape(rows * CELL_H, columns * CELL_W)
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        frame[self.y0 : self.y0 + rows * CELL_H, self.x0 : self.x0 + columns * CELL_W] = self._palette[index]
        if self.glow:
            frame = apply_glow(frame)
        return frame


def apply_glow(frame: np.ndarray, amount: float = 0.3) -> np.ndarray:
    """Each pixel at least `amount` of its brightest 4-neighbour; the edges are padded black, never wrapped."""
    f = frame.astype(np.uint16)
    p = np.pad(f, ((1, 1), (1, 1), (0, 0)))
    neighbours = np.maximum(np.maximum(p[:-2, 1:-1], p[2:, 1:-1]), np.maximum(p[1:-1, :-2], p[1:-1, 2:]))
    out = np.maximum(f, (neighbours * amount).astype(np.uint16))
    return np.clip(out, 0, 255).astype(np.uint8)


def draw_text(frame: np.ndarray, x: int, y: int, text: str, font: Font,
              color: tuple[int, int, int]) -> None:
    """Draw text into frame at (x, y), clipped at every edge; anything outside Latin-1 is '?'."""
    height, width = frame.shape[:2]
    r0, r1 = max(0, -y), min(CELL_H, height - y)
    if r0 >= r1:
        return
    atlas = font.atlas()
    for i, ch in enumerate(text):
        cx = x + i * CELL_W
        if cx >= width:
            break
        c0, c1 = max(0, -cx), min(CELL_W, width - cx)
        if c0 >= c1:
            continue
        glyph = atlas[_code(ch), r0:r1, c0:c1]
        frame[y + r0 : y + r1, cx + c0 : cx + c1][glyph] = color
