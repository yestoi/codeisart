"""The pattern check (C24, BT.1702-3 Guideline 2, owner Q15): reversing, oscillating or moving stripes of more
than five light-dark pairs over a quarter of the wall."""
import itertools

import numpy as np

from arcade.flash import THRESHOLD, signals
from arcade.games.pong import NET_COLOR, Pong
from arcade.headless import run_headless
from arcade.pattern import PATTERN_AREA, PATTERN_PAIRS, pattern_area, stripes
from tests.arcade.helpers import make_cfg

WHITE = (255, 255, 255)


def bars(n, width=4, gap=None, x0=8, w=64, h=32, color=WHITE, vertical=False):
    """n light bars of width px, gap px apart (width by default), from x0, on a black w x h frame; bars across
    the rows (vertical stripes) unless vertical, which turns the frame to h x w with the bars along the rows."""
    gap = width if gap is None else gap
    frame = np.zeros((h, w, 3), np.uint8)
    for k in range(n):
        x = x0 + k * (width + gap)
        frame[:, x:x + width] = color
    return frame.transpose(1, 0, 2).copy() if vertical else frame


def test_six_pair_stripes_reversing_count():
    assert PATTERN_PAIRS == 5 and PATTERN_AREA == 0.25
    a = bars(6, x0=8)
    b = bars(6, x0=12)                                  # the same grating with light and dark swapped
    mask = stripes(a)
    assert mask.shape == (32, 64) and mask.dtype == bool
    assert mask[:, 8:52].all() and not mask[:, 60:].any()
    assert stripes(bars(6, vertical=True))[8:52, :].all()          # stripes along a column count too
    area = pattern_area([a, b, a, b])
    assert PATTERN_AREA < area <= 1.0, area


def test_five_pairs_do_not_count():
    a, b = bars(PATTERN_PAIRS, x0=8), bars(PATTERN_PAIRS, x0=12)
    assert not stripes(a).any()
    assert pattern_area([a, b, a, b]) == 0.0


def test_static_stripes_count_zero():
    a = bars(8)
    assert stripes(a).mean() > PATTERN_AREA
    assert pattern_area([a] * 5) == 0.0


def test_moving_stripes_count():
    frames = [bars(8, x0=4 + k % 8) for k in range(12)]           # one px a frame
    assert pattern_area(frames) > PATTERN_AREA
    one_row = [np.pad(f[:1], ((0, 31), (0, 0), (0, 0))) for f in frames]
    assert 0.0 < pattern_area(one_row) <= 1 / 32 + 1e-9           # the share is of the striped pixels only


def test_uneven_bands_are_not_stripes():
    uneven = [bars(10, width=1, gap=3, x0=4 + k % 2) for k in range(4)]       # light 1 px, dark 3 px
    assert not stripes(uneven[0]).any()
    assert pattern_area(uneven) == 0.0
    within_one = [bars(8, width=2, gap=3, x0=4 + k % 2) for k in range(4)]   # 2 and 3: equal within 1 px
    assert stripes(within_one[0]).mean() > PATTERN_AREA
    assert pattern_area(within_one) > PATTERN_AREA


def test_dim_bands_are_not_stripes():
    dim = bars(8, color=(20, 20, 20))                  # a swing under THRESHOLD in every signal
    assert signals(dim, 2.2).max() < THRESHOLD
    assert not stripes(dim).any()
    red = bars(8, color=(255, 0, 0))                   # saturated red counts through its own signals
    assert stripes(red).mean() > PATTERN_AREA


def test_a_dashed_net_is_under_the_limit(font5x7):
    frame = np.zeros((32, 128, 3), np.uint8)
    for y in range(0, 32, 4):
        frame[y:y + 2, 64] = WHITE                     # Pong's net, drawn white: eight dashes in a column
    flipped = np.roll(frame, 2, axis=0)                # every dash reversing each tick
    assert stripes(frame)[:, 64].all()
    assert 0.0 < pattern_area([frame, flipped] * 3) <= 32 / (32 * 128) + 1e-9
    net = frame.copy()
    net[:, 64][net[:, 64].any(axis=1)] = NET_COLOR      # the real net is dim on purpose: no stripes at all
    assert not stripes(net).any()
    _, runner = run_headless(make_cfg((128, 32)), font5x7, Pong,
                             itertools.islice(Pong.SCENARIOS["duel"](), 150), raw=True)
    assert pattern_area(runner.raw_frames) <= PATTERN_AREA
