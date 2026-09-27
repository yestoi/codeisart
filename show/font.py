from __future__ import annotations

from pathlib import Path

import numpy as np

CELL_W = 6
CELL_H = 8
GLYPH_COLS = 5
GLYPH_ROWS = 7
NUM_GLYPHS = 256


class Font:
    """5x7 column-major glyphs placed in 6x8 cells. Column 5 and row 7 are spacing."""

    def __init__(self, data: bytes):
        if len(data) != NUM_GLYPHS * GLYPH_COLS:
            raise ValueError(f"font data must be {NUM_GLYPHS * GLYPH_COLS} bytes, got {len(data)}")
        self._data = data
        self._atlas: np.ndarray | None = None

    @classmethod
    def load(cls, path: Path) -> "Font":
        return cls(Path(path).read_bytes())

    def glyph(self, code: int) -> list[int]:
        if not 0 <= code < NUM_GLYPHS:
            code = ord("?")
        cols = self._data[code * GLYPH_COLS : (code + 1) * GLYPH_COLS]
        rows = []
        for r in range(CELL_H):
            bits = 0
            if r < GLYPH_ROWS:
                for c in range(GLYPH_COLS):
                    if (cols[c] >> r) & 1:
                        bits |= 1 << (CELL_W - 1 - c)
            rows.append(bits)
        return rows

    def atlas(self) -> np.ndarray:
        if self._atlas is None:
            a = np.zeros((NUM_GLYPHS, CELL_H, CELL_W), dtype=bool)
            for code in range(NUM_GLYPHS):
                for r, bits in enumerate(self.glyph(code)):
                    for c in range(CELL_W):
                        a[code, r, c] = bool((bits >> (CELL_W - 1 - c)) & 1)
            self._atlas = a
        return self._atlas
