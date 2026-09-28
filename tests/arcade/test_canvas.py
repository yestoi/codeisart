import contextlib
import math
import signal
import threading
import time
import warnings

import numpy as np
import pytest

from arcade.canvas import Canvas, sprite_from_rows

RED = (255, 0, 0)


def lit(c: Canvas) -> int:
    return int((c.frame.max(axis=2) > 0).sum())


@contextlib.contextmanager
def deadline(seconds: float):
    """Fails a block that runs past seconds instead of hanging the suite (05-plan S4's infinite line).

    It replaces any outer SIGALRM timer while it runs. Off the main thread, or where there is no setitimer
    (Windows), it just runs the block."""
    if threading.current_thread() is not threading.main_thread() or not hasattr(signal, "setitimer"):
        yield
        return
    def expired(signum, frame):
        raise TimeoutError(f"still running after {seconds} s")
    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def test_new_canvas_is_black_and_sized(font5x7, size):
    c = Canvas(*size, font5x7)
    assert c.frame.shape == (size[1], size[0], 3) and c.frame.dtype == np.uint8
    assert c.size == size and lit(c) == 0


def test_pixel_and_clipping(font5x7):
    c = Canvas(16, 8, font5x7)
    c.pixel(3, 2, RED)
    c.pixel(-1, 0, RED)
    c.pixel(16, 8, RED)
    assert lit(c) == 1 and tuple(c.frame[2, 3]) == RED


def test_rects_and_clear(font5x7):
    c = Canvas(16, 8, font5x7)
    c.fill_rect(2, 1, 4, 3, RED)
    assert lit(c) == 12
    c.clear()
    c.rect(0, 0, 16, 8, RED)
    assert lit(c) == 2 * 16 + 2 * 6
    c.fill_rect(10, 4, 100, 100, RED)
    assert lit(c) == 2 * 16 + 2 * 6 + (6 * 4 - 6 - 3)


def test_line_and_circles(font5x7):
    c = Canvas(16, 16, font5x7)
    c.line(0, 0, 15, 15, RED)
    assert lit(c) == 16 and tuple(c.frame[7, 7]) == RED
    c.clear()
    c.fill_circle(8, 8, 3, RED)
    n_fill = lit(c)
    assert 25 <= n_fill <= 37 and tuple(c.frame[8, 8]) == RED
    c.clear()
    c.circle(8, 8, 3, RED)
    assert 12 <= lit(c) < n_fill and tuple(c.frame[8, 8]) == (0, 0, 0)
    c.circle(0, 0, 40, RED)


def test_text_uses_font_and_clips(font5x7):
    c = Canvas(32, 8, font5x7)
    assert c.text_width("AB") == 12
    w = c.text(0, 0, "A", RED)
    assert w == 6 and lit(c) > 5
    a = c.frame.copy()
    c.clear()
    c.text(30, 0, "A", RED)
    assert lit(c) < lit_of(a)
    c.clear()
    c.text(0, 0, "☃", RED)
    assert lit(c) > 0


def lit_of(frame: np.ndarray) -> int:
    return int((frame.max(axis=2) > 0).sum())


def test_float_coordinates_round(font5x7):
    c = Canvas(16, 8, font5x7)
    c.pixel(2.5, 0.5, RED)                          # half rounds up: a 0.5 px step moves every tick
    c.pixel(np.float32(5.4), np.int64(3), RED)
    assert tuple(c.frame[1, 3]) == RED and tuple(c.frame[3, 5]) == RED and lit(c) == 2
    c.clear()
    c.fill_rect(1.2, 1.2, 2.6, 2.6, RED)            # x 1, y 1, 3 by 3
    assert lit(c) == 9 and c.frame[1:4, 1:4, 0].all()
    c.clear()
    c.fill_circle(8.4, 4.4, 1.6, RED)               # centre (8, 4), radius 2
    assert tuple(c.frame[4, 8]) == RED and tuple(c.frame[4, 10]) == RED and tuple(c.frame[4, 11]) == (0, 0, 0)
    c.clear()
    c.blit(np.ones((2, 2), bool), 0.6, 0.4, RED)    # at (1, 0)
    c.text(9.5, 0.2, "I", RED)                      # at (10, 0)
    assert c.frame[0:2, 1:3, 0].all() and not c.frame[:, 0].any() and c.frame[:, 10:16].any()
    c.clear()
    c.text(0, 0.5, "I", RED)                        # at (0, 1): text rounds as pixel does
    one = Canvas(16, 8, font5x7)
    one.text(0, 1, "I", RED)
    assert np.array_equal(c.frame, one.frame)
    c.clear()
    c.text(-1, 0, "B", RED)                         # scrolling in from the left: B's four visible columns
    b = Canvas(16, 8, font5x7)
    b.text(5, 0, "B", RED)
    assert c.frame[:, 0:4].any() and np.array_equal(c.frame[:, 0:4], b.frame[:, 6:10])


def test_nan_inf_and_huge_never_raise_or_hang(font5x7):
    c = Canvas(64, 32, font5x7)
    nan, inf = math.nan, math.inf
    sprite = np.full((4, 4, 3), 200, np.uint8)
    c.text(0, 0, "A", RED)                          # build the font atlas before timing
    calls = [
        lambda: c.pixel(nan, 3, RED), lambda: c.pixel(inf, -inf, RED), lambda: c.pixel(10**12, 5, RED),
        lambda: c.pixel(None, "x", RED), lambda: c.pixel(10**400, 0, RED),
        lambda: c.line(0, 0, nan, 5, RED), lambda: c.line(0, 0, 10**9, 0, RED),
        lambda: c.line(-inf, 0, inf, 0, RED), lambda: c.line(0, 0, 1e300, -1e300, RED),
        lambda: c.fill_rect(nan, 0, 5, 5, RED), lambda: c.fill_rect(0, 0, 10**9, 10**9, RED),
        lambda: c.rect(nan, nan, nan, nan, RED), lambda: c.rect(-10**9, -10**9, 2 * 10**9, 2 * 10**9, RED),
        lambda: c.circle(5, 5, 10**9, RED), lambda: c.fill_circle(nan, nan, 3, RED),
        lambda: c.fill_circle(5, 5, inf, RED), lambda: c.fill_circle(10**9, 10**9, 10**9, RED),
        lambda: c.fill_circle(5, 5, 1e200, RED),       # (r + 0.5) ** 2 overflows a float unless _i clamps
        lambda: c.blit(np.ones((3, 3), bool), nan, 0, RED), lambda: c.blit_rgb(sprite, inf, 0),
        lambda: c.blit_rgb(sprite, -10**9, 10**9),
        lambda: c.text(nan, 0, "HI", RED), lambda: c.text(0, 0, "HI", RED, scale=10**9),
        lambda: c.text(0, 0, "X" * 10000, RED, scale=2), lambda: c.text(-10**6, 0, "X" * 10000, RED),
        lambda: c.text(0, inf, "HI", RED, scale=nan),
    ]
    for i, call in enumerate(calls):
        start = time.perf_counter()
        with deadline(1.0):
            call()
        assert time.perf_counter() - start < 0.05, f"call {i} took too long"
    assert c.frame.shape == (32, 64, 3) and c.frame.dtype == np.uint8
    e = Canvas(16, 8, font5x7)
    e.rect(3, 0, 0, 4, RED)                         # a health bar at width 0 draws nothing
    e.rect(10, 0, -3, 4, RED)
    e.fill_rect(0, 0, inf, 4, RED)                  # an infinite width lands at -_FAR: nothing
    assert lit(e) == 0


def test_colours_clamped(font5x7):
    c = Canvas(16, 8, font5x7)
    c.pixel(0, 0, (300, -5, 127.6))
    assert tuple(c.frame[0, 0]) == (255, 0, 128)
    c.fill_rect(1, 0, 1, 1, (math.nan, math.inf, -math.inf))
    assert tuple(c.frame[0, 1]) == (0, 255, 0)
    c.line(0, 2, 3, 2, (np.int64(999), np.float32(-1), 7))
    assert tuple(c.frame[2, 3]) == (255, 0, 7)
    c.text(0, 3, "I", (999, 0, 0))
    assert c.frame[3:8, :, 0].max() == 255
    c.clear((256, 256, 256))
    assert (c.frame == 255).all()
    c.clear()
    with warnings.catch_warnings():
        warnings.simplefilter("error")              # a NaN never reaches a byte cast
        c.blit_rgb(np.array([[[300.0, 127.6, 0.4], [np.nan, 0, 0], [-5, 0, 0], [np.inf, 0, 0]]], np.float32), 0, 5)
        c.blit_rgb(np.array([[[300, 0, 0], [-1, 0, 0]]], np.int64), 0, 6)
        c.blit_rgb(np.array([[[0.5, 126.5, 2.5]]], np.float32), 0, 7)
    assert [tuple(p) for p in c.frame[5, :4]] == [(255, 128, 0), (0, 0, 0), (0, 0, 0), (255, 0, 0)]
    assert [tuple(p) for p in c.frame[6, :2]] == [(255, 0, 0), (0, 0, 0)]   # a paint buffer clamps, never wraps
    assert tuple(c.frame[7, 0]) == (1, 127, 3)                               # half up, as coordinates round


def test_line_with_float_endpoint_terminates(font5x7):
    c = Canvas(16, 8, font5x7)
    start = time.perf_counter()
    with deadline(1.0):
        c.line(0, 0, 10.5, 0, RED)                  # used to step past 10.5 forever
    assert time.perf_counter() - start < 0.05
    assert lit(c) == 12 and c.frame[0, :12, 0].all()
    c.clear()
    c.line(0.4, 0.6, 7.6, 3.4, RED)                 # (0, 1) to (8, 3)
    assert tuple(c.frame[1, 0]) == RED and tuple(c.frame[3, 8]) == RED and lit(c) == 9


def test_text_scale_two(font5x7):
    c = Canvas(32, 16, font5x7)
    assert c.text_width("8", scale=2) == 12 and c.text_width("88", scale=2) == 24
    one = Canvas(32, 16, font5x7)
    one.text(0, 0, "8", RED)
    assert c.text(0, 0, "8", RED, scale=2) == 12
    assert lit(c) == 4 * lit(one)
    big, small = c.frame[:16, :12, 0] > 0, one.frame[:8, :6, 0] > 0
    assert np.array_equal(big, small.repeat(2, axis=0).repeat(2, axis=1))    # 2 px strokes
    rows, cols = np.nonzero(c.frame[:, :, 0])
    assert rows.max() - rows.min() + 1 == 14 and cols.max() - cols.min() + 1 == 10   # the 5x7 glyph at 10x14
    num = Canvas(32, 16, font5x7)
    assert num.text(0, 0, 8, RED, scale=2) == 12 and np.array_equal(num.frame, c.frame)   # numbers are drawn as str


def test_blit_rgb_black_is_transparent(font5x7):
    c = Canvas(8, 8, font5x7)
    c.clear((0, 0, 255))
    sprite = np.array([[[255, 0, 0], [0, 0, 0]], [[0, 0, 0], [0, 255, 0]]], np.uint8)
    c.blit_rgb(sprite, 1, 1)
    assert tuple(c.frame[1, 1]) == (255, 0, 0) and tuple(c.frame[2, 2]) == (0, 255, 0)
    assert tuple(c.frame[1, 2]) == (0, 0, 255) and tuple(c.frame[2, 1]) == (0, 0, 255)   # black showed through
    c.clear()
    c.blit_rgb(sprite, -1, 6.6)                     # at (-1, 7): only the black top-right cell is on-canvas
    c.blit_rgb(sprite, 6.5, -1)                     # at (7, -1): only the black bottom-left cell is on-canvas
    assert lit(c) == 0
    c.blit_rgb(sprite, 7, 7)
    assert lit(c) == 1 and tuple(c.frame[7, 7]) == (255, 0, 0)


def test_sprite_from_rows_palette():
    s = sprite_from_rows(["R.", ".G"], {"R": (255, 0, 0), "G": (0, 300, 0)})
    assert s.shape == (2, 2, 3) and s.dtype == np.uint8
    assert tuple(s[0, 0]) == (255, 0, 0) and tuple(s[1, 1]) == (0, 255, 0)            # clamped
    assert tuple(s[0, 1]) == (0, 0, 0) and tuple(s[1, 0]) == (0, 0, 0)
    assert sprite_from_rows([".R"], {".": (9, 9, 9), "R": RED})[0, 0].sum() == 0       # "." is always black
    with pytest.raises(ValueError, match="'X'"):
        sprite_from_rows(["RX"], {"R": RED})
    with pytest.raises(ValueError, match="length"):
        sprite_from_rows(["RR", "R"], {"R": RED})
    assert np.array_equal(Canvas.sprite_from_rows(["R"], {"R": RED}), sprite_from_rows(["R"], {"R": RED}))


def test_circle_is_the_one_pixel_rim_of_fill_circle(font5x7):
    for r in (1, 3, 6):
        ring, inner, disc = (Canvas(16, 16, font5x7) for _ in range(3))
        ring.circle(8, 8, r, RED)
        inner.fill_circle(8, 8, r - 1, RED)
        disc.fill_circle(8, 8, r, RED)
        rim, core, whole = (c.frame[:, :, 0] > 0 for c in (ring, inner, disc))
        assert not (rim & core).any() and np.array_equal(rim | core, whole), r


def test_blit_takes_any_mask_as_bool(font5x7):
    c = Canvas(8, 4, font5x7)
    c.blit(np.array([[1, 0], [0, 1]], np.uint8), 3, 0, RED)   # an int mask is a mask, not row indices
    assert lit(c) == 2 and tuple(c.frame[0, 3]) == RED and tuple(c.frame[1, 4]) == RED


def test_line_skip_starts_past_four_times_the_extent(font5x7):
    # Spec 7.4: a line whose endpoints exceed four times the canvas extent is skipped.
    c = Canvas(16, 8, font5x7)
    reach = 4 * (16 + 8)
    c.line(0, 0, reach, 0, RED)
    assert c.frame[0, :, 0].all()
    c.clear()
    c.line(0, 0, reach + 1, 0, RED)
    c.line(0, -reach - 1, 0, 7, RED)
    assert lit(c) == 0


@pytest.mark.parametrize("w,h", [(64, 32), (96, 48), (128, 64)])
def test_other_wall_sizes_draw_and_clip(font5x7, w, h):
    # Core Review Focus 3: a single panel at bring-up (64x32), or a wall of another size from config.
    c = Canvas(w, h, font5x7)
    c.text(w - 10, h - 8, "88", RED, scale=2)
    c.fill_circle(w - 1, h - 1, 5, RED)
    c.line(-5, h // 2, w + 5, h // 2, RED)
    c.rect(-1, -1, w + 2, h + 2, RED)
    c.blit_rgb(np.full((5, 5, 3), 90, np.uint8), w - 2, -2)
    assert c.frame.shape == (h, w, 3) and c.frame[h // 2, :, 0].all()
    assert c.text_width("88", scale=2) == 24 and lit(c) > w


def test_tiny_negative_and_non_finite_radii_draw_the_centre_as_fill_circle_does(font5x7):
    # C18: a ring whose radius rounds to 0 or lands at -_FAR (negative, infinite, NaN, not a number) is its
    # centre pixel, as the disc is; it used to draw nothing while fill_circle drew the centre.
    for r in (0, 0.25, 0.49, -2, -math.inf, math.inf, math.nan, None):
        ring, disc = Canvas(16, 16, font5x7), Canvas(16, 16, font5x7)
        ring.circle(8, 8, r, RED)
        disc.fill_circle(8, 8, r, RED)
        assert lit(ring) == 1 and tuple(ring.frame[8, 8]) == RED, r
        assert np.array_equal(ring.frame, disc.frame), r
    c = Canvas(16, 16, font5x7)
    c.circle(8, 8, 0.5, RED)                        # rounds half up to 1: the eight neighbours, not the centre
    assert lit(c) == 8 and not c.frame[8, 8].any()


def test_huge_python_ints_clamp_like_huge_floats(font5x7):
    # C18: 10**400 has no float, so it used to land at -_FAR: a radius drew 1 px where 1e300 fills.
    draws = [lambda c, v: c.fill_circle(5, 5, v, RED), lambda c, v: c.fill_rect(0, 0, v, 4, RED),
             lambda c, v: c.text(0, 0, "H", RED, scale=v), lambda c, v: c.pixel(v, 0, RED),
             lambda c, v: c.pixel(-v, 0, RED), lambda c, v: c.circle(5, 5, v, RED)]
    lights = []
    for draw in draws:
        huge, big = Canvas(16, 8, font5x7), Canvas(16, 8, font5x7)
        with deadline(1.0):
            draw(huge, 10**400)
            draw(big, 1e300)
        assert np.array_equal(huge.frame, big.frame)
        lights.append(lit(huge))
    assert lights == [128, 64, 128, 0, 0, 0]       # a disc and a rect fill, one glyph pixel fills, a ring is off
