from pathlib import Path

import pytest

from show.font import CELL_H, CELL_W, Font

ROOT = Path(__file__).resolve().parents[1]


def test_cell_size():
    assert (CELL_W, CELL_H) == (6, 8)


def test_space_is_blank(font):
    assert font.glyph(ord(" ")) == [0] * 8


def test_a_rows(font):
    rows = font.glyph(ord("A"))
    assert rows[0] == 0b011100
    assert rows[1] == 0b100010
    assert rows[4] == 0b111110
    assert rows[7] == 0
    assert all(r < 64 for r in rows)


def test_out_of_range_code_uses_question_mark(font):
    assert font.glyph(1000) == font.glyph(ord("?"))


def test_atlas_shape_and_content(font):
    atlas = font.atlas()
    assert atlas.shape == (256, 8, 6)
    assert atlas.dtype == bool
    assert atlas[65, 4].tolist() == [True, True, True, True, True, False]


def test_wrong_size_rejected():
    with pytest.raises(ValueError):
        Font(b"\0" * 10)


def test_real_font_file_loads():
    real = Font.load(ROOT / "fonts" / "5x7.bin")
    assert real.glyph(ord(" ")) == [0] * 8
    assert any(real.glyph(ord("A"))[:7])
