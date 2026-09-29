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


# The ink view: the 128x64 proof of concept, one dot a cell (show.poc.toml)

PW, PH = 128, 64
PSTRIP_Y = PH - 8                             # 56: the strip keeps the bottom text row
INK_Y0, INK_H = 3, 49                         # 23 rows at 1.6 px a column and 6:8 cells, centred in 56


def ink_renderer(font: Font, **kw) -> Renderer:
    return Renderer(font, PW, PH, COLS, ROWS, GREEN, view="ink", **kw)


def half_a_font() -> Font:
    """'A' as in font3, and '.' holding the first half of A's ink by columns."""
    data = bytearray(256 * 5)
    data[65 * 5 : 66 * 5] = A_COLUMNS
    data[46 * 5 : 46 * 5 + 2] = A_COLUMNS[:2]
    return Font(bytes(data))


def test_ink_view_takes_the_80x24_terminal_on_128x64(font):
    frame = ink_renderer(font).render(make_screen(), strip="NOW")
    assert frame.shape == (PH, PW, 3)
    assert frame[:PSTRIP_Y].sum() == 0
    assert lit_fraction(frame[PSTRIP_Y:]) > 0.5              # reverse video: mostly lit


def lit_fraction(region: np.ndarray) -> float:
    return float((region.max(axis=2) > 0).mean())


def test_ink_view_fills_its_area_with_a_screen_of_ink(font):
    frame = ink_renderer(font).render(make_screen("A" * COLS * (ROWS - 1)))
    area = frame[INK_Y0 : INK_Y0 + INK_H]
    assert (area == np.array(DIM, dtype=np.uint8)).all()
    assert frame[:INK_Y0].sum() == 0 and frame[INK_Y0 + INK_H : PSTRIP_Y].sum() == 0


def test_ink_view_lights_a_dot_by_the_glyphs_ink():
    font = half_a_font()
    a = ink_renderer(font).render(make_screen("A" * COLS))[INK_Y0, 0, 1]
    dot = ink_renderer(font).render(make_screen("." * COLS))[INK_Y0, 0, 1]
    ink_a, ink_dot = font.atlas()[ord("A")].sum(), font.atlas()[ord(".")].sum()
    assert a == int(255 * NORMAL)
    assert dot == int(255 * NORMAL * ink_dot / ink_a)
    assert 0 < dot < a


def test_ink_view_bold_is_full_and_reverse_inverts(font):
    bold = ink_renderer(font).render(make_screen("\x1b[1m" + "A" * COLS))
    assert bold[INK_Y0, 0].tolist() == list(GREEN)
    reverse = ink_renderer(font).render(make_screen("\x1b[7m" + " " * COLS))
    assert reverse[INK_Y0, 0].tolist() == list(DIM)
    reverse_a = ink_renderer(font).render(make_screen("\x1b[7m" + "A" * COLS))
    assert reverse_a[INK_Y0, 0].sum() == 0


def test_ink_view_strip_is_the_font_cut_to_the_width(font):
    frame = ink_renderer(font).render(make_screen(), strip="A" * 40)
    x0 = (PW - 21 * 6) // 2                              # 21 characters fit 128 px
    lit = frame[PSTRIP_Y:].any(axis=2)
    for k in range(21):
        assert (lit[:, x0 + k * 6 : x0 + k * 6 + 6] == ~mask(font, "A")).all()
    assert lit[:, :x0].all() and lit[:, x0 + 21 * 6 :].all()


def test_ink_view_full_screen_without_the_strip_draws_every_row(font):
    frame = ink_renderer(font).render(make_screen("A" * COLS * ROWS, lines=ROWS), full_screen=True,
                                      strip_visible=False)
    rows_lit = frame.any(axis=2).all(axis=1)
    assert rows_lit[2 : 2 + 51].all()                   # 24 rows are 51 px, centred in 56
    assert not rows_lit[:2].any() and not rows_lit[2 + 51 :].any()


def test_ink_view_draws_no_cursor(font):
    frame = ink_renderer(font).render(make_screen(), cursor_on=True)
    assert frame[:PSTRIP_Y].sum() == 0


def test_unknown_view_rejected(font):
    with pytest.raises(ValueError):
        Renderer(font, W, H, COLS, ROWS, GREEN, view="blocks")


def test_text_view_still_refuses_the_128x64_wall(font):
    with pytest.raises(ValueError):
        Renderer(font, PW, PH, COLS, ROWS, GREEN)


# The strip's three looks (Q54)

LOOKS = ("reverse", "dim-reverse", "bright-on-field")
FIELD_LETTERS = {"reverse": (0.70, 0.0), "dim-reverse": (0.35, 0.0), "bright-on-field": (0.25, 1.0)}
INK_STRIP_X0 = (PW - (PW // 6) * 6) // 2               # 4: 21 characters fit 128 px


def look_renderer(font: Font, view: str, look: str) -> Renderer:
    if view == "ink":
        return Renderer(font, PW, PH, COLS, ROWS, GREEN, view="ink", strip_look=look)
    return Renderer(font, W, H, COLS, ROWS, GREEN, strip_look=look)


def strip_cells(frame: np.ndarray, view: str) -> np.ndarray:
    """The strip's text row, (8, width, 3), cut to the columns the terminal (or the font) covers."""
    if view == "ink":
        return frame[-8:]
    return frame[-8:, X0 : X0 + 480]


def shade(share: float) -> tuple:
    return tuple((np.array(GREEN, dtype=np.float64) * share).astype(np.uint8))


def colors(region: np.ndarray) -> set:
    return {tuple(p) for p in region.reshape(-1, 3)}


def test_strip_look_names_match_the_config():
    from show import config, renderer as renderer_module
    assert set(renderer_module.STRIP_LOOKS) == set(config.STRIP_LOOKS)
    assert dict(renderer_module.STRIP_LOOKS) == FIELD_LETTERS


def test_unknown_strip_look_rejected(font):
    with pytest.raises(ValueError):
        Renderer(font, W, H, COLS, ROWS, GREEN, strip_look="neon")


@pytest.mark.parametrize("view", ["text", "ink"])
def test_reverse_is_the_present_strip(font, view):
    default = (ink_renderer(font) if view == "ink" else renderer(font)).render(make_screen(), strip="A")
    reverse = look_renderer(font, view, "reverse").render(make_screen(), strip="A")
    assert np.array_equal(default, reverse)
    assert colors(strip_cells(reverse, view)) == {(0, 0, 0), DIM}


@pytest.mark.parametrize("view", ["text", "ink"])
def test_dim_reverse_is_a_35_percent_field_with_dark_letters(font, view):
    frame = look_renderer(font, view, "dim-reverse").render(make_screen(), strip="A")
    assert colors(strip_cells(frame, view)) == {(0, 0, 0), shade(0.35)}
    x0 = INK_STRIP_X0 if view == "ink" else X0
    lit = frame[-8:, x0 : x0 + 6].any(axis=2)
    assert (lit == ~mask(font, "A")).all()


@pytest.mark.parametrize("view", ["text", "ink"])
def test_bright_on_field_is_full_letters_on_a_25_percent_field(font, view):
    frame = look_renderer(font, view, "bright-on-field").render(make_screen(), strip="A")
    assert colors(strip_cells(frame, view)) == {shade(0.25), GREEN}
    x0 = INK_STRIP_X0 if view == "ink" else X0
    letters = (frame[-8:, x0 : x0 + 6] == np.array(GREEN)).all(axis=2)
    assert (letters == mask(font, "A")).all()


@pytest.mark.parametrize("view", ["text", "ink"])
def test_program_rows_are_the_same_in_every_look(font, view):
    screen = make_screen("A\x1b[1mA\x1b[0m\x1b[7mA" * 10)
    frames = [look_renderer(font, view, look).render(screen, strip="NOW") for look in LOOKS]
    assert frames[0][:-8].any()
    for frame in frames[1:]:
        assert np.array_equal(frame[:-8], frames[0][:-8])


@pytest.mark.parametrize("view", ["text", "ink"])
@pytest.mark.parametrize("look", LOOKS)
def test_an_empty_strip_is_lit_in_every_look(font, view, look):
    frame = look_renderer(font, view, look).render(make_screen(), strip="")
    assert colors(strip_cells(frame, view)) == {shade(FIELD_LETTERS[look][0])}


@pytest.mark.parametrize("view", ["text", "ink"])
def test_renderer_for_passes_view_and_look(font, view):
    from show.config import Config
    from show.renderer import renderer_for
    cfg = Config(view=view, strip_look="bright-on-field", glow=True,
                 width=PW if view == "ink" else W, height=PH if view == "ink" else H)
    r = renderer_for(cfg, font)
    assert (r.view, r.strip_look, r.glow) == (view, "bright-on-field", True)
    assert (r.width, r.height, r.columns, r.rows) == (cfg.width, cfg.height, cfg.columns, cfg.rows)
