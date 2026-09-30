import logging
import math
import os
import statistics
import time
import zlib

import numpy as np
import pytest

from arcade.canvas import Canvas
from arcade.flash import (BACKSTOP_PASSES, BUDGET, FIELD_AREA, FPS, RED_SHARE, SMALL_AREA, THRESHOLD, WINDOW,
                          FlashGovernor, concurrent_area, flash_area, largest_share, signals, square_flashes,
                          square_means)
from arcade.look import gamma_lut, light_lut

GOVERNOR_MS = float(os.environ.get("ARCADE_GOVERNOR_BUDGET_MS", "0.5"))   # 0.5 on the Mac; 2 on the Pi 5 (Q79)


def strobe(hz, w, h, n=90, color=(255, 255, 255), cols=None, off=(0, 0, 0), fps=FPS):
    """A strobe of hz flashes a second at fps: color for the first half of each period and off for the
    second (the review prototype), over the first cols columns (all of them by default)."""
    frames = []
    for i in range(n):
        f = np.zeros((h, w, 3), np.uint8)
        f[:, :cols] = color if int(i * 2 * hz / fps) % 2 == 0 else off
        frames.append(f)
    return frames


def govern(frames, gamma=2.2, **kwargs):
    h, w = frames[0].shape[:2]
    g = FlashGovernor(h, w, gamma, **kwargs)
    return [g.apply(f) for f in frames], g


def changes(frames, y, x):
    """The frames at which one pixel's value changes (from the frame before)."""
    v = [int(f[y, x].sum()) for f in frames]
    return [i for i in range(1, len(v)) if v[i] != v[i - 1]]


def most_changes_in_a_second(frames, y, x, n=FPS):
    """The most changes of one pixel's value in any n consecutive frames."""
    c = changes(frames, y, x)
    return max(sum(1 for i in c if start <= i < start + n) for start in range(len(frames)))


def test_15hz_white_strobe_held_to_3_per_second(size):
    w, h = size
    raw = strobe(15, w, h)
    out, g = govern(raw)
    assert flash_area(raw) == 1.0 and flash_area(out) == 0.0
    assert most_changes_in_a_second(raw, 0, 0) == 30                  # the strobe changes every frame
    assert most_changes_in_a_second(out, 0, 0) == 6 == BUDGET        # 3 flashes a second get through, no more
    assert most_changes_in_a_second(out, h - 1, w - 1, FPS + 1) == 6  # the window is the 30 frames before
    assert g.held_ticks > 0 and g.held_ticks == sum(not np.array_equal(a, b) for a, b in zip(raw, out))
    assert all(set(np.unique(f)) <= {0, 255} for f in out)          # held pixels keep a previous frame's value


def test_3_flashes_a_second_pass_and_4_do_not():
    w, h = 16, 8
    for hz in (1, 2, 2.9):
        raw = strobe(hz, w, h)
        out, g = govern(raw)
        assert g.held_ticks == 0 and all(a is b for a, b in zip(raw, out)), hz
        assert flash_area(raw) == 0.0, hz
    # Exactly 3 a second is the limit: every flash gets through, but a transition waits a frame when the 30
    # frames before already hold 6 (one frame of margin for a late tick, loop decision 11).
    raw = strobe(3, w, h, n=150)
    out, g = govern(raw)
    assert flash_area(raw) == 0.0 and g.held_ticks > 0
    assert len(changes(out, 3, 3)) == len(changes(raw, 3, 3)) and most_changes_in_a_second(out, 3, 3, FPS + 1) == 6
    raw = strobe(4, w, h)
    out, g = govern(raw)
    assert g.held_ticks > 0 and flash_area(raw) == 1.0 and flash_area(out) == 0.0
    assert most_changes_in_a_second(out, 3, 3) == 6
    seventh = grey([255, 0] * 4 + [0] * 5)                           # a 7th transition with 6 in the frames before
    out, g = govern(seventh)
    assert concurrent_area(seventh) == 1.0 and flash_area(seventh) == 1.0 and g.held_ticks == 6   # white to the end
    assert concurrent_area(out) == 0.0 and flash_area(out) == 0.0


def test_window_and_budget_follow_the_keywords():
    # The runner ticks at cfg.fps: at 60 fps a second is 60 frames, so 2 flashes a second pass and 4 do not.
    for hz, flashing in ((2, False), (4, True)):
        raw = strobe(hz, 16, 8, n=180, fps=60)
        out, g = govern(raw, fps=60)
        assert (g.held_ticks > 0) is flashing and flash_area(raw, fps=60) == float(flashing), hz
        assert flash_area(out, fps=60) == 0.0 and most_changes_in_a_second(out, 3, 3, 61) <= 6, hz
    five = strobe(5, 16, 8, n=180, fps=60)                          # 5 a second at 60 fps: 10 changes in 60 frames
    assert flash_area(five, fps=30) == 0.0 and flash_area(five, fps=60) == 1.0   # a 30-frame window misses it
    assert govern(five, fps=30)[1].held_ticks == 0 and govern(five, fps=60)[1].held_ticks > 0
    two = strobe(2, 16, 8)                                          # 4 transitions a second
    out, g = govern(two, budget=2)
    assert flash_area(two) == 0.0 and flash_area(two, budget=2) == 1.0
    assert concurrent_area(two) == 0.0 and concurrent_area(two, budget=2) == 1.0
    assert g.held_ticks > 0 and flash_area(out, budget=2) == 0.0 and most_changes_in_a_second(out, 0, 0) == 2
    grey = strobe(15, 16, 8, color=(60, 60, 60))                   # a swing of 0.235 of light
    assert flash_area(grey) == 1.0 and flash_area(grey, threshold=0.3) == 0.0
    assert govern(grey, threshold=0.3)[1].held_ticks == 0 and govern(grey)[1].held_ticks > 0


TITLES = "COPY ME  PONG  PAINT  QUICKDRAW  DODGE  TUG  FLAP  SWAT  STRONGMAN  FREEZE"


def scrolling(font, w, h, scale, speed, text=TITLES):
    """Static text, a 4x4 ball at 60 px a second and text scrolling right to left at speed px a second
    until it has gone by."""
    frames = []
    for i in range(int((w + len(text) * 6 * scale) * FPS / speed)):
        c = Canvas(w, h, font)
        c.text(2, 1, "SCORE 12", (255, 200, 0))                      # static
        c.fill_rect((i * 2) % (w - 4), 10, 4, 4, (255, 255, 255))    # the ball
        c.text(w - int(i * speed / FPS), h - 15, text, (0, 255, 255), scale=scale)
        frames.append(c.frame.copy())
    return frames


def test_static_and_moving_sprite_pass_bit_identical(font5x7, size):
    # The door titles scroll at scale 2: at 10 px a second no pixel of any title changes more than 6 times
    # in a second, so the governor never touches them.
    w, h = size
    frames = scrolling(font5x7, w, h, scale=2, speed=10)
    out, g = govern(frames)
    assert g.held_ticks == 0 and all(a is b for a, b in zip(frames, out))
    assert flash_area(frames) == 0.0


def test_fine_text_scrolling_fast_is_a_small_area_and_passes(font5x7, size):
    # At 20 to 30 px a second the strokes of 1x and 2x text turn pixels on and off more than 3 times a second
    # (5 to 29% of the wall, pixel by pixel), but a square never has 10% of its pixels going the same way
    # at once and its mean light hardly moves: the flash is small (Q13) and nothing is held.
    w, h = size
    for scale, speed in ((1, 20), (1, 30), (2, 20), (2, 25), (2, 30)):
        frames = scrolling(font5x7, w, h, scale, speed, text="COPY ME  QUICKDRAW")
        out, g = govern(frames)
        assert g.held_ticks == 0 and all(a is b for a, b in zip(frames, out)), (scale, speed)
        assert flash_area(frames) > 0.05 and concurrent_area(frames) < 0.09, (scale, speed)   # measured 0.08
        assert square_flashes(frames) <= 2, (scale, speed)
    frames = scrolling(font5x7, w, h, 2, 60, text="COPY ME  QUICKDRAW")    # twice as fast: a 2 px jump a frame
    out, g = govern(frames)
    assert concurrent_area(frames) > SMALL_AREA and g.held_ticks > 0 and concurrent_area(out) < SMALL_AREA


def test_a_flash_just_over_the_small_area_is_held():
    assert WINDOW == 32 and SMALL_AREA == 0.1                        # 102 pixels of a 32 x 32 square are under
    tenth = grey([128, 0] * 45, h=10, w=10)
    for f in tenth:
        f[1:] = 0                                                    # a row of a 10 x 10 wall: exactly a tenth
    out, g = govern(tenth)
    assert concurrent_area(tenth) == pytest.approx(0.1) and g.held_ticks > 0 and flash_area(out) == 0.0
    blink = strobe(15, 128, 32, cols=1)
    for f in blink:
        f[1:] = 0
    for f in blink[60:]:
        f[:, 64:] = 255                                              # half the wall lights once as the pixel does
    out, g = govern(blink)
    assert g.held_ticks == 0 and concurrent_area(blink) == pytest.approx(1 / 1024)   # only flashing pixels count
    for color, off in (((255, 255, 255), (0, 0, 0)), ((87, 0, 0), (0, 0, 255))):   # red against blue counts too
        for n, held in ((102, False), (103, True)):
            frames = strobe(15, 64, 32, color=color, off=off)
            for f in frames:
                f[:] = 0
            for f, src in zip(frames, strobe(15, 1, n, color=color, off=off)):
                f[:10, :10] = src[:100, 0].reshape(10, 10, 3)
                f[10, :n - 100] = src[100:, 0]
            out, g = govern(frames)
            assert (g.held_ticks > 0) is held, (color, n)
            assert flash_area(frames) == pytest.approx(n / 2048) and concurrent_area(frames) == pytest.approx(n / 1024)
            assert flash_area(out) == (0.0 if held else n / 2048), (color, n)
    one = strobe(15, 3, 3, cols=1, color=(128, 128, 128))
    for f in one:
        f[1:] = 0                                                    # one pixel of 9, held alone: the mean moves 0.056
    out, g = govern(one)
    assert g.held_ticks > 0 and g.held_ticks == sum(not np.array_equal(a, b) for a, b in zip(one, out))


def test_many_small_flashes_add_up_and_are_held():
    one = strobe(15, 128, 32)
    for f in one:
        f[:, 2:] = 0                                                 # a 32 x 2 strip: 6% of its square
    out, g = govern(one)
    assert g.held_ticks == 0 and flash_area(out) == pytest.approx(64 / 4096)
    assert square_flashes(one) == 0 and square_flashes(one, window=8) == 30   # a quarter of an 8 x 8 square
    dots = strobe(15, 128, 32)
    for f in dots:
        f[(np.arange(32) % 4 >= 2)] = 0
        f[:, (np.arange(128) % 4 >= 2)] = 0                          # 2 x 2 dots every 4 px: a quarter of the wall
    out, g = govern(dots)
    assert concurrent_area(dots) == 0.25 and g.held_ticks > 0 and flash_area(out) == 0.0
    board = np.indices((32, 128)).sum(axis=0) % 2 == 0
    reversal = [np.where(board ^ (i % 2 == 1), 255, 0).astype(np.uint8)[..., None].repeat(3, axis=2)
                for i in range(90)]                                  # a checkerboard reversing: mean light constant
    out, g = govern(reversal)
    assert concurrent_area(reversal) == 0.5 and g.held_ticks > 0 and flash_area(out) == 0.0
    assert square_flashes(reversal) == 0                             # held on the pixels going the same way


def test_a_flash_spread_over_frames_is_held():
    # Three sets of columns, each 9% of a square, light one frame after another and go out the same way: no
    # frame turns 10% of a square one way, but each square's mean light swings 0.27 five times a second.
    x = np.arange(128)
    frames = []
    for i in range(150):
        p = i % 6
        f = np.zeros((32, 128, 3), np.uint8)
        for k in (range(p) if p <= 3 else range(p - 3, 3)):
            f[:, x % 11 == k] = 255
        frames.append(f)
    out, g = govern(frames)
    assert concurrent_area(frames) < SMALL_AREA and square_flashes(frames) == 10 and g.held_ticks > 0
    assert square_flashes(out) <= BUDGET              # the square backstop holds the mean too (B7)
    red = [np.where(f > 0, np.array([255, 0, 0], np.uint8), f) for f in frames]
    assert govern(red)[1].held_ticks > 0                            # red means swing 0.06 of luminance, 0.12 doubled
    # At exactly 3 a second each square's mean makes its 7th transition with 6 in the frames before: held.
    three = []
    for i in range(90):
        f = np.zeros((32, 128, 3), np.uint8)
        for k in range(3):
            if k + 1 <= i % 10 < k + 6:
                f[:, x % 11 == k] = 255
        three.append(f)
    assert concurrent_area(three) < SMALL_AREA and govern(three)[1].held_ticks > 0


def turns(groups, w, h, n=150, period=31, burst=6):
    """groups interleaved dithers take turns: each flashes 3 times in burst frames, then rests while the next
    takes its turn. Every pixel stays within its budget, while every square's mean light flashes."""
    y, x = np.indices((h, w))
    group = (x + 2 * y) % groups
    frames = []
    for i in range(n):
        f = np.zeros((h, w, 3), np.uint8)
        k, j = divmod(i % period, burst)
        if k < groups and j % 2 == 0:
            f[group == k] = 255
        frames.append(f)
    return frames


def test_pixels_taking_turns_are_held_by_the_square(size, caplog):
    # 5 dithers flash the whole wall's mean light 0.2 at 15 Hz, 2 dithers swing it 0.5 six times a second, and no
    # pixel is over its own budget. The square backstop (B7) holds whole squares until no square's mean flashes
    # past its budget: here every square flashes, so every frame shows the input or the previous output whole.
    w, h = size
    for groups in (5, 2):
        frames = turns(groups, w, h)
        with caplog.at_level(logging.WARNING, logger="arcade"):
            out, g = govern(frames)
        assert flash_area(frames) == 0.0 and concurrent_area(frames) == 0.0, groups
        assert square_flashes(frames) >= 12 and g.held_ticks > 0 and square_flashes(out) <= BUDGET, groups
        assert all(np.array_equal(o, f) or np.array_equal(o, p) for o, f, p in zip(out[1:], frames[1:], out)), groups
    assert not caplog.records                                        # the backstop ends by itself, never capped


def grating(w, h, every, n=150):
    """1 px lines every `every` px over the whole wall, reversing every frame (15 Hz)."""
    x = np.arange(w)
    frames = [np.zeros((h, w, 3), np.uint8) for _ in range(n)]
    for i, f in enumerate(frames):
        f[:, x % every == (0 if i % 2 else every // 2)] = 255
    return frames


def test_a_reversing_grating_is_held_by_the_field_cap(size):
    # 1 px lines every 11 px reversing: 12 pairs across 128 px, and 18.75% of the wall flips over budget in each
    # frame, though no square has 10% going one way and every square's mean is constant. Over-budget flips on
    # FIELD_AREA of the wall or more are held (Q15; BT.1702-3 Guideline 2 counts more than 5 pairs).
    assert FIELD_AREA == 0.125
    w, h = size
    frames = grating(w, h, 11)
    out, g = govern(frames)
    assert concurrent_area(frames) < SMALL_AREA and square_flashes(frames) == 0 and flash_area(frames) == 0.1875
    assert g.held_ticks > 0 and flash_area(out) == 0.0
    frames = grating(w, h, 16)                                       # 8 pairs: exactly 12.5% of the wall
    out, g = govern(frames)
    assert flash_area(frames) == FIELD_AREA and g.held_ticks > 0 and flash_area(out) == 0.0
    for f in frames:
        f[0, 0] = 0                                                  # one pixel less: under the cap, not held
    out, g = govern(frames)
    assert g.held_ticks == 0 and all(a is b for a, b in zip(frames, out))


def test_titles_scrolling_pass_under_the_field_cap(font5x7, size):
    # The ten titles at 1x and 2x, 20 to 30 px a second: over-budget pixels flip on at most 9.9% of the wall in
    # a frame (1x at 30 px a second on 128x32), under FIELD_AREA, so nothing is held.
    w, h = size
    for scale, speed in ((1, 20), (1, 30), (2, 20), (2, 25), (2, 30)):
        frames = scrolling(font5x7, w, h, scale, speed)
        out, g = govern(frames)
        assert g.held_ticks == 0 and all(a is b for a, b in zip(frames, out)), (scale, speed)


def test_the_backstop_gives_up_by_holding_the_whole_frame(monkeypatch, caplog):
    # A wall governor never hangs: when a square still flashes after BACKSTOP_PASSES passes (here a square
    # tracker whose first square always flips), every pixel of the wall keeps the previous output, which flips
    # nothing, and it is logged once.
    assert BACKSTOP_PASSES == 8
    g = FlashGovernor(32, 64)
    g.apply(np.zeros((32, 64, 3), np.uint8))
    calls = []

    def always(v):
        calls.append(1)
        flip = np.zeros(v.shape, bool)
        flip[:, 0, 0] = True                                         # the left square, never the right half
        return flip, flip

    monkeypatch.setattr(g._squares, "flips", always)
    out = None
    with caplog.at_level(logging.WARNING, logger="arcade"):
        for i in range(12):
            f = np.full((32, 64, 3), 20 * (i + 1), np.uint8)
            prev, held, calls[:] = out, g.held_ticks, []
            out = g.apply(f)
            if i >= BUDGET:                                          # the squares' windows are over budget
                assert len(calls) == BACKSTOP_PASSES and np.array_equal(out, prev) and g.held_ticks == held + 1, i
    assert not np.array_equal(out, f)
    assert len(caplog.records) == 1 and "backstop" in caplog.records[0].getMessage()
    assert np.array_equal(g._shown, signals(out, 2.2)) and g._square_window.count.max() == BUDGET   # nothing counted


def test_governor_copes_with_a_reused_buffer():
    # The runner draws every tick into the same canvas array: the governor keeps its own copy of what it showed.
    raw = strobe(15, 16, 8)
    expected = [f.copy() for f in govern(raw)[0]]
    g, buf, out = FlashGovernor(8, 16), np.zeros((8, 16, 3), np.uint8), []
    for f in raw:
        buf[:] = f
        out.append(g.apply(buf).copy())
    assert all(np.array_equal(a, b) for a, b in zip(out, expected)) and flash_area(out) == 0.0


def test_saturated_red_counts_double():
    assert RED_SHARE == 0.8 and THRESHOLD == 0.1
    px = np.array([[[255, 0, 0], [255, 63, 0], [255, 64, 0], [0, 255, 0], [0, 0, 0], [128, 32, 0], [0, 0, 255]]],
                  np.uint8)
    plain, red, excess = signals(px, 2.2)[:, 0]
    assert plain[0] == pytest.approx(0.2126, rel=1e-5) and red[0] == pytest.approx(2 * 0.2126, rel=1e-5)
    assert red[1] == pytest.approx(2 * (0.2126 + 0.7152 * 63 / 255), rel=1e-5)     # red is 80.2% of the light
    assert red[2] == pytest.approx(0.2126 + 0.7152 * 64 / 255, rel=1e-5)           # 79.9%: counted once
    assert red[3] == plain[3] == pytest.approx(0.7152, rel=1e-5) and red[4] == 0.0
    assert red[5] == pytest.approx(2 * (0.2126 * 128 + 0.7152 * 32) / 255, rel=1e-5)   # exactly 80%: counts
    assert excess[0] == pytest.approx(1.0) and excess[1] == pytest.approx(192 / 255) and excess[3] == 0.0
    assert plain[6] == red[6] == pytest.approx(0.0722, rel=1e-6) and excess[6] == 0.0   # Rec. 709 blue
    # A dim red strobe swings 0.075 of light: under the threshold as luminance, over it counted double.
    dim_red = strobe(15, 8, 4, color=(90, 0, 0))
    out, g = govern(dim_red)
    assert flash_area(dim_red) == 1.0 and g.held_ticks > 0 and flash_area(out) == 0.0
    blue = strobe(15, 8, 4, color=(0, 0, 255))                       # 0.072 of light, not red: never a flash
    out, g = govern(blue)
    assert flash_area(blue) == 0.0 and g.held_ticks == 0


RED_PAIRS = (((87, 0, 0), (0, 0, 255)),        # the Pokemon strobe: luminance and doubled luminance barely move
             ((255, 0, 0), (0, 152, 0)),       # doubling red lifts it onto the green: luminance moves 0.21
             ((189, 0, 0), (255, 66, 0)),
             ((255, 0, 0), (255, 60, 60)))


def test_red_traded_against_another_colour_is_a_flash():
    for color, off in RED_PAIRS:
        for hz in (15, 12):
            raw = strobe(hz, 128, 32, color=color, off=off)
            out, g = govern(raw)
            assert flash_area(raw) == 1.0 and g.held_ticks > 0 and flash_area(out) == 0.0, (color, off, hz)
    # Each measure catches a swing the other two miss.
    for a, b, which in (((51, 10, 0), (89, 38, 26), 0), ((128, 13, 13), (128, 0, 33), 1), ((87, 0, 0), (0, 0, 255), 2),
                        ((200, 0, 0), (200, 0, 40), 2)):                # blue alone takes red's excess away
        swing = np.abs(np.subtract(*signals(np.array([[a, b]], np.uint8), 2.2)[:, 0].T))
        assert [bool(s >= THRESHOLD) for s in swing] == [k == which for k in range(3)], (a, b)
        raw = strobe(15, 8, 4, color=a, off=b)
        out, g = govern(raw)
        assert flash_area(raw) == 1.0 and g.held_ticks > 0 and flash_area(out) == 0.0, (a, b)


def test_held_pixels_are_measured_as_shown():
    # A pixel held on one signal keeps its other signals' extremes where the shown colour put them, not where the
    # input went: random colours on four large blocks never get past the budget on any signal.
    seed = zlib.crc32(b"flash-held")
    rng = np.random.default_rng(seed)
    palette = np.array([(0, 0, 0), (255, 255, 255), (255, 0, 0), (0, 152, 0), (0, 0, 255), (87, 0, 0), (255, 66, 0)],
                       np.uint8)
    for trial in range(20):
        frames = [palette[rng.integers(0, len(palette), (2, 2))].repeat(4, axis=0).repeat(8, axis=1) for _ in range(60)]
        out, g = govern(frames)
        assert g.held_ticks > 0 and flash_area(out) == 0.0, (trial, seed)
    # The squares count what is shown too: a half-wall strobe brought down to the budget no longer holds a
    # one-pixel blinker elsewhere (measured: 131 of its 179 changes pass; counting the input, 50 would; without
    # the square flag, 155 would).
    frames = strobe(3.5, 128, 32, n=180, cols=64)
    for i, f in enumerate(frames):
        f[0, 127] = 255 * (i % 2 == 0)
    out, g = govern(frames)
    assert g.held_ticks > 0 and len(changes(out, 0, 127)) > 120 and flash_area(out) == pytest.approx(1 / 4096)
    assert len(changes(out, 0, 127)) < 140                          # the square flag still holds the blinker (N26)


def grey(values, h=4, w=8):
    return [np.full((h, w, 3), v, np.uint8) for v in values]


def test_transitions_follow_extremes_not_steps():
    # A fade is one transition however many frames it takes: white to black in 8 steps of 0.125 and back,
    # about 2 fades a second, passes untouched.
    fade = [255 - 32 * i for i in range(8)] + [32 * i for i in range(8)]
    frames = grey((fade * 6)[:90])
    out, g = govern(frames)
    assert g.held_ticks == 0 and all(a is b for a, b in zip(frames, out)) and flash_area(frames) == 0.0
    # Steps under the threshold still add up: 0 to 0.3 of light and back in steps of 0.075 is a 3.75 Hz flash.
    tri = [0, 19, 38, 57, 76, 57, 38, 19]
    frames = grey((tri * 12)[:90])
    out, g = govern(frames)
    assert flash_area(frames) == 1.0 and g.held_ticks > 0 and flash_area(out) == 0.0
    # A flicker at the top of a fade swings from the fade's peak, not from where the fade began.
    frames = grey([32 * i for i in range(8)] + [255, 200] * 41)
    out, g = govern(frames)
    assert flash_area(frames) == 1.0 and g.held_ticks > 0 and flash_area(out) == 0.0
    # The first swing counts either way: a slow fall from the first frame, then a rise, is two transitions.
    fall = grey([128 - 8 * i for i in range(16)] + [128])
    assert flash_area(fall, budget=1) == 1.0 and flash_area(fall[::-1], budget=1) == 1.0
    rise = grey([8 * i for i in range(17)] + [0])                    # and a slow rise from the first frame, then a fall
    assert flash_area(rise, budget=1) == 1.0
    # A swing of exactly the threshold is a transition, up or down: red (51, 0, 0) is its own excess.
    exact = strobe(15, 8, 4, color=(51, 0, 0))
    th = float(light_lut(2.2)[51])
    assert flash_area(exact, threshold=th) == 1.0 and govern(exact, threshold=th)[1].held_ticks > 0
    assert flash_area(exact, threshold=th * 1.001) == 0.0


def test_governor_follows_gamma():
    # The same bytes are less light when the card applies gamma (gamma 1.0): a grey swing of 0 to 60 is 0.235
    # of light on an uncorrected wall and 0.043 on a gamma-correcting one.
    grey = strobe(15, 8, 4, color=(60, 60, 60))
    assert flash_area(grey, gamma=2.2) == 1.0 and flash_area(grey, gamma=1.0) == 0.0
    assert govern(grey, gamma=1.0)[1].held_ticks == 0 and govern(grey, gamma=2.2)[1].held_ticks > 0


def test_only_the_flashing_part_is_held(font5x7):
    w, h = 32, 16
    frames = []
    for i in range(60):
        f = np.zeros((h, w, 3), np.uint8)
        if i % 2 == 0:
            f[:, :8] = 255                                           # a strobing strip on the left
        f[8:12, 12 + i % 16: 16 + i % 16] = (0, 255, 0)              # a sprite moving on the right
        frames.append(f)
    out, g = govern(frames)
    assert g.held_ticks > 0
    assert all(np.array_equal(a[:, 8:], b[:, 8:]) for a, b in zip(frames, out))
    assert flash_area(out) == 0.0 and flash_area(frames) == pytest.approx(8 / 32)


def test_squares_are_every_square():
    mask = np.zeros((32, 128), bool)
    mask[5:15, 100:110] = True
    assert largest_share(mask) == 100 / 1024 and largest_share(mask, 10) == 1.0 and largest_share(mask, 20) == 0.25
    assert largest_share(mask[:8, :16] | True, 32) == 1.0                   # a small wall: the square is cut to it
    assert largest_share(np.zeros((8, 8), bool)) == 0.0
    s = np.zeros((3, 64, 64), np.float32)
    s[1, 40:50, 3:13] = 1.0
    means = square_means(s)
    assert means.shape == (3, 33, 33) and means[0].max() == 0.0 and means[1].max() == pytest.approx(100 / 1024)
    assert means[1, 32, 0] == pytest.approx(100 / 1024) and means[1, 0, 0] == 0.0 and means[1, 18, 13] == 0.0
    assert square_means(s[:, :8, :16]).shape == (3, 1, 1) and square_means(s, 8).shape == (3, 57, 57)
    assert np.allclose(square_means(np.ones((3, 8, 16), np.float32)), 1.0)   # a cut square's mean is over its area


def test_light_lut_matches_the_led_preview():
    for gamma in (1.0, 2.2, 1.8):
        lut = light_lut(gamma)
        shown = (gamma_lut(gamma).astype(np.float64) / 255) ** 2.2   # what the led look's monitor emits
        assert np.abs(lut - shown).max() < 0.01 and not lut.flags.writeable, gamma
    assert light_lut(2.2)[128] == pytest.approx(128 / 255) and light_lut(1.0)[128] == pytest.approx((128 / 255) ** 2.2)


def test_governor_rejects_bad_input():
    g = FlashGovernor(4, 8)
    for bad in (np.zeros((8, 4, 3), np.uint8), np.zeros((4, 8, 3), np.float32), np.zeros((4, 8), np.uint8)):
        with pytest.raises(ValueError):
            g.apply(bad)
    for kwargs in (dict(gamma=0.0), dict(gamma=float("nan")), dict(gamma=None), dict(gamma=[2.2]), dict(fps=1),
                   dict(budget=0), dict(threshold=0.0), dict(threshold=None), dict(threshold=math.inf),
                   dict(threshold=math.nan), dict(fps=30.0), dict(budget=True)):
        with pytest.raises(ValueError):
            FlashGovernor(4, 8, **kwargs)
    FlashGovernor(4, 8, fps=2, budget=1, threshold=np.float32(0.5))
    first = np.full((4, 8, 3), 200, np.uint8)
    assert g.apply(first) is first and g.held_ticks == 0             # the first frame passes


@pytest.mark.perf
def test_governor_under_half_ms_at_128x32():
    seed = zlib.crc32(b"flash-perf")
    rng = np.random.default_rng(seed)
    frames = [rng.integers(0, 256, (32, 128, 3), dtype=np.uint8) for _ in range(40)]
    g = FlashGovernor(32, 128)
    for f in frames[:10]:
        g.apply(f)
    times = []
    for f in frames[10:]:
        start = time.thread_time()
        g.apply(f)
        times.append(time.thread_time() - start)
    assert g.held_ticks > 0                                          # the held path is the one timed
    median = statistics.median(times) * 1000
    assert median < GOVERNOR_MS, f"median {median:.3f} ms, budget {GOVERNOR_MS} ms, seed={seed}"
