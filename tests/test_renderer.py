import statistics
import time

import numpy as np
import pyte
import pytest

from show.font import Font
from show.renderer import NORMAL, Renderer, apply_glow, draw_text

GREEN = (51, 255, 51)
DIM = tuple((np.array(GREEN) * NORMAL).astype(np.uint8))
W, H, COLS, ROWS = 512, 192, 80, 24
X0, Y0 = 16, 0
STRIP_Y = (ROWS - 1) * 8                      # 184
RENDER_BUDGET_S = 0.005
RENDER_SAMPLES = 50

A_COLUMNS = bytes([0x7E, 0x11, 0x11, 0x11, 0x7E])
Q_COLUMNS = bytes([0x02, 0x01, 0x51, 0x09, 0x06])        # '?'
E_ACUTE_COLUMNS = bytes([0x38, 0x54, 0x56, 0x55, 0x18])  # 'é'


@pytest.fixture
def font3() -> Font:
    """A, ? and é drawn; everything else blank."""
    data = bytearray(256 * 5)
    data[65 * 5 : 66 * 5] = A_COLUMNS
    data[63 * 5 : 64 * 5] = Q_COLUMNS
    data[233 * 5 : 234 * 5] = E_ACUTE_COLUMNS
    return Font(bytes(data))


def make_screen(text: str = "", columns: int = COLS, lines: int = ROWS - 1) -> pyte.Screen:
    screen = pyte.Screen(columns, lines)
    pyte.Stream(screen).feed(text)
    return screen


def renderer(font: Font, **kw) -> Renderer:
    return Renderer(font, W, H, COLS, ROWS, GREEN, **kw)


def cell(frame: np.ndarray, row: int, col: int, x0: int = X0, y0: int = Y0) -> np.ndarray:
    return frame[y0 + row * 8 : y0 + row * 8 + 8, x0 + col * 6 : x0 + col * 6 + 6].any(axis=2)


def mask(font: Font, ch: str) -> np.ndarray:
    return font.atlas()[ord(ch)]


def test_frame_shape_and_only_the_strip_lit_when_blank(font):
    frame = renderer(font).render(make_screen())
    assert frame.shape == (H, W, 3) and frame.dtype == np.uint8
    assert frame[:STRIP_Y].sum() == 0
    assert frame[191, X0 : X0 + 480].any(axis=1).all()
    assert frame[:, :X0].sum() == 0 and frame[:, X0 + 480 :].sum() == 0


def test_terminal_must_fit(font):
    with pytest.raises(ValueError):
        Renderer(font, 400, 192, 80, 24, GREEN)
    with pytest.raises(ValueError):
        Renderer(font, 512, 184, 80, 24, GREEN)


def test_origin_is_centered_on_both_tiers(font):
    full = renderer(font)
    assert (full.x0, full.y0) == (16, 0)
    reduced = Renderer(font, 512, 128, 80, 16, GREEN)
    assert (reduced.x0, reduced.y0) == (16, 0)
    frame = reduced.render(make_screen(lines=15))
    assert frame.shape == (128, 512, 3)
    assert frame[:120].sum() == 0 and frame[120:128, X0 : X0 + 480].any(axis=2).all()


def test_glyph_lands_in_centered_cell(font):
    frame = renderer(font).render(make_screen("A"))
    lit = frame[0:8, 16:22].any(axis=2)          # x0 = (512 - 480) // 2 = 16
    assert lit[0].tolist() == [False, True, True, True, False, False]
    assert lit[4].tolist() == [True] * 5 + [False]
    assert frame[:STRIP_Y, 22:].sum() == 0 and frame[8:STRIP_Y, :].sum() == 0
    assert tuple(frame[4, 16]) == DIM


def test_bold_is_full_phosphor_and_reverse_inverts(font):
    frame = renderer(font).render(make_screen("\x1b[1mA\x1b[0m\x1b[7mA"))
    assert tuple(frame[4, 16]) == GREEN
    rev = frame[0:8, 22:28].any(axis=2)
    assert rev[0].tolist() == [True, False, False, False, True, True]
    assert rev[7].all()
    assert tuple(frame[7, 22]) == DIM


def test_strip_is_reverse_video_on_the_last_row(font):
    r = renderer(font)
    frame = r.render(make_screen(), strip="A")
    assert (cell(frame, 23, 0) == ~mask(font, "A")).all()
    assert frame[STRIP_Y:192, X0 + 6 : X0 + 480].any(axis=2).all()
    assert tuple(frame[191, X0]) == DIM
    long = "A" * 79 + " " + "A" * 5          # 85 columns: the tail is cut, never wrapped
    frame = r.render(make_screen(), strip=long)
    assert (cell(frame, 23, 78) == ~mask(font, "A")).all()
    assert cell(frame, 23, 79).all()
    assert frame[:STRIP_Y].sum() == 0
    assert frame[:, X0 + 480 :].sum() == 0


def test_program_rows_never_reach_the_strip(font):
    screen = make_screen("A" * 80 * 24, lines=24)
    frame = renderer(font).render(screen, strip="NOW")
    strip_only = renderer(font).render(make_screen(), strip="NOW")
    assert (cell(frame, 22, 5) == mask(font, "A")).all()
    assert np.array_equal(frame[STRIP_Y:], strip_only[STRIP_Y:])


def test_full_screen_draws_the_programs_last_row_when_the_strip_is_hidden(font):
    screen = make_screen("A" * 80 * 24, lines=24)
    r = renderer(font)
    hidden = r.render(screen, strip="NOW", full_screen=True, strip_visible=False)
    for col in (0, 40, 79):
        assert (cell(hidden, 23, col) == mask(font, "A")).all()
    screen.dirty.add(0)
    shown = r.render(screen, strip="NOW", full_screen=True, strip_visible=True)
    strip_only = renderer(font).render(make_screen(), strip="NOW")
    assert np.array_equal(shown[STRIP_Y:], strip_only[STRIP_Y:])
    assert np.array_equal(shown[:STRIP_Y], hidden[:STRIP_Y])


def test_cursor_inverts_cell_and_clamps_at_column_80(font):
    screen = make_screen("A" * 80)
    assert screen.cursor.x == 80                 # pyte's pending wrap
    frame = renderer(font).render(screen, cursor_on=True)
    assert (cell(frame, 0, 79) == ~mask(font, "A")).all()
    assert (cell(frame, 0, 78) == mask(font, "A")).all()


def test_cursor_on_a_blank_cell_is_a_block(font):
    frame = renderer(font).render(make_screen("\x1b[3;5H"), cursor_on=True)
    assert cell(frame, 2, 4).all()
    assert frame[:STRIP_Y].any(axis=2).sum() == 48


def test_cursor_under_the_strip_is_not_drawn(font):
    screen = make_screen("\x1b[24;1H", lines=24)
    assert screen.cursor.y == 23
    on = renderer(font).render(screen, cursor_on=True, strip="NOW", full_screen=True)
    off = renderer(font).render(screen, cursor_on=False, strip="NOW", full_screen=True)
    assert np.array_equal(on, off)
    normal = renderer(font).render(screen, cursor_on=True, strip="NOW")
    assert np.array_equal(normal, off)
    bare = renderer(font).render(screen, cursor_on=True, strip="NOW", full_screen=True,
                                 strip_visible=False)
    assert cell(bare, 23, 0).all()


def test_hidden_cursor_not_drawn(font):
    frame = renderer(font).render(make_screen("\x1b[?25l"), cursor_on=True)
    assert frame[:STRIP_Y].sum() == 0


def test_non_latin1_char_renders_as_question_mark(font3):
    r = Renderer(font3, W, H, COLS, ROWS, GREEN)
    frame = r.render(make_screen("█é"), strip="█é")
    assert mask(font3, "?").any() and mask(font3, "é").any()
    assert (cell(frame, 0, 0) == mask(font3, "?")).all()
    assert (cell(frame, 0, 1) == mask(font3, "é")).all()
    assert (cell(frame, 23, 0) == ~mask(font3, "?")).all()
    assert (cell(frame, 23, 1) == ~mask(font3, "é")).all()


def test_wide_character_does_not_raise(font3):
    r = Renderer(font3, W, H, COLS, ROWS, GREEN)
    screen = make_screen("中A")                  # pyte: '中' at 0, '' at 1, 'A' at 2
    frame = r.render(screen, strip="中")
    assert (cell(frame, 0, 0) == mask(font3, "?")).all()
    assert not cell(frame, 0, 1).any()
    assert (cell(frame, 0, 2) == mask(font3, "A")).all()
    assert (cell(frame, 23, 0) == ~mask(font3, "?")).all()


def test_screen_wider_or_taller_than_the_wall_is_cut(font):
    big = make_screen("A" * 100 * 30, columns=100, lines=30)
    frame = renderer(font).render(big, strip="NOW")
    strip_only = renderer(font).render(make_screen(), strip="NOW")
    assert (cell(frame, 22, 79) == mask(font, "A")).all()
    assert frame[:, X0 + 480 :].sum() == 0
    assert np.array_equal(frame[STRIP_Y:], strip_only[STRIP_Y:])


def test_screen_smaller_than_the_wall_is_drawn_top_left(font):
    small = make_screen("A" * 10 * 3, columns=10, lines=3)
    frame = renderer(font).render(small)
    assert (cell(frame, 2, 9) == mask(font, "A")).all()
    assert frame[3 * 8 : STRIP_Y].sum() == 0
    assert frame[:STRIP_Y, X0 + 60 :].sum() == 0


def test_unchanged_screen_returns_the_cached_frame(font):
    r = renderer(font)
    screen = make_screen("A")
    first = r.render(screen, cursor_on=True, strip="NOW")
    assert not screen.dirty
    again = r.render(screen, cursor_on=True, strip="NOW")
    assert again is first
    assert not again.flags.writeable
    with pytest.raises(ValueError):
        again[0, 0] = 0


def test_dirty_screen_or_new_strip_or_cursor_blink_redraws(font):
    r = renderer(font)                           # the conftest font draws only A
    screen = make_screen()
    stream = pyte.Stream(screen)
    frame = r.render(screen, strip="A")

    def changed(new: np.ndarray, looks_different: bool = True) -> None:
        nonlocal frame
        assert new is not frame
        assert np.array_equal(new, frame) != looks_different
        frame = new

    stream.feed("A")
    changed(r.render(screen, strip="A"))
    changed(r.render(screen, strip="AA"))
    changed(r.render(screen, cursor_on=True, strip="AA"))
    stream.feed("\x1b[5;5H")                     # a cursor move alone
    screen.dirty.clear()
    changed(r.render(screen, cursor_on=True, strip="AA"))
    stream.feed("\x1b[?25l")
    screen.dirty.clear()
    changed(r.render(screen, cursor_on=True, strip="AA"))
    tall = make_screen("A" * 80 * 24, lines=24)
    r2 = renderer(font)
    frame = r2.render(tall, strip="A")
    changed(r2.render(tall, strip="A", full_screen=True), looks_different=False)
    changed(r2.render(tall, strip="A", full_screen=True, strip_visible=False))


def test_draw_text(font):
    frame = np.zeros((16, 32, 3), np.uint8)
    draw_text(frame, 2, 4, "A", font, (255, 0, 0))
    assert tuple(frame[4, 3]) == (255, 0, 0)     # row 0, column 1 of A
    assert tuple(frame[4, 2]) == (0, 0, 0)


def test_draw_text_clips_at_every_edge(font):
    a = mask(font, "A")
    frame = np.zeros((16, 32, 3), np.uint8)
    draw_text(frame, -3, 0, "A", font, (255, 0, 0))
    assert (frame[0:8, 0:3].any(axis=2) == a[:, 3:]).all()
    assert frame[:, 3:].sum() == 0

    frame = np.zeros((16, 32, 3), np.uint8)
    draw_text(frame, 29, 0, "AA", font, (255, 0, 0))
    assert (frame[0:8, 29:32].any(axis=2) == a[:, :3]).all()

    frame = np.zeros((16, 32, 3), np.uint8)
    draw_text(frame, 0, 12, "A", font, (255, 0, 0))
    assert (frame[12:16, 0:6].any(axis=2) == a[:4]).all()

    frame = np.zeros((16, 32, 3), np.uint8)
    draw_text(frame, 0, -5, "A", font, (255, 0, 0))
    assert (frame[0:3, 0:6].any(axis=2) == a[5:]).all()
    assert frame[3:].sum() == 0

    frame = np.zeros((16, 32, 3), np.uint8)
    for x, y in ((-100, 0), (100, 0), (0, -100), (0, 100)):
        draw_text(frame, x, y, "AAAA", font, (255, 0, 0))
    assert frame.sum() == 0


def test_draw_text_non_latin1_is_question_mark(font3):
    frame = np.zeros((8, 12, 3), np.uint8)
    draw_text(frame, 0, 0, "█é", font3, (255, 0, 0))
    assert (frame[:, 0:6].any(axis=2) == mask(font3, "?")).all()
    assert (frame[:, 6:12].any(axis=2) == mask(font3, "é")).all()


def test_glow_spreads_light(font):
    frame = np.zeros((8, 8, 3), np.uint8)
    frame[4, 4] = (0, 200, 0)
    out = apply_glow(frame, 0.5)
    assert tuple(out[4, 4]) == (0, 200, 0)
    assert tuple(out[4, 5]) == (0, 100, 0)
    assert tuple(out[3, 4]) == (0, 100, 0)


def test_glow_does_not_wrap_around_edges():
    frame = np.zeros((8, 8, 3), np.uint8)
    frame[0, 0] = (0, 200, 0)
    out = apply_glow(frame, 0.5)
    assert tuple(out[0, 1]) == (0, 100, 0) and tuple(out[1, 0]) == (0, 100, 0)
    assert out[:, 7].sum() == 0 and out[7, :].sum() == 0


def test_renderer_glow_option_spreads_the_glyph(font):
    plain = renderer(font).render(make_screen("A"))
    glowing = renderer(font, glow=True).render(make_screen("A"))
    assert plain[0, 16].sum() == 0 and glowing[0, 16].sum() > 0


@pytest.mark.perf
def test_render_is_fast(font):
    r = renderer(font)
    screen = make_screen("\x1b[1mA\x1b[0m" + "A" * (80 * 23 - 1))
    times = []
    for i in range(RENDER_SAMPLES):
        screen.dirty.update(range(screen.lines))
        start = time.thread_time()
        r.render(screen, cursor_on=bool(i % 2), strip=f"NOW {i}")
        times.append(time.thread_time() - start)
    median = statistics.median(times)
    print(f"render median {median * 1000:.2f} ms, max {max(times) * 1000:.2f} ms, "
          f"min {min(times) * 1000:.2f} ms over {RENDER_SAMPLES}")
    assert median < RENDER_BUDGET_S
