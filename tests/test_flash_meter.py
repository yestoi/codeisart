"""tools.flash_meter (it13 T-wall): arcade.flash's counting, a frame at a time, for the soak and the patterns."""
import numpy as np
import pytest

from arcade.flash import BUDGET, flash_area, square_flashes
from show.display.fake import FakeDisplay
from show.wall import GovernedDisplay
from tests.test_wall import FPS, H, W, strobe
from tools.flash_meter import FlashMeter

SIZES = ((64, 128), (16, 24))     # the arcade's four panels 2 x 2, and a wall under one WINDOW square (cut to it)


def strobes(h, w, n, period):
    on, off = np.full((h, w, 3), (51, 255, 51), np.uint8), np.zeros((h, w, 3), np.uint8)
    return [on if (k // period) % 2 == 0 else off for k in range(n)]


@pytest.mark.parametrize("h, w", SIZES)
def test_the_meter_agrees_with_flash_area_and_square_flashes(h, w):
    rng = np.random.default_rng(13)
    cases = [strobes(h, w, 24, p) for p in (1, 2, 3)]           # period 3 passes the budget from frame 22 on
    cases.append([rng.integers(0, 256, (h, w, 3), np.uint8) for _ in range(20)])
    for frames in cases:
        meter, got = FlashMeter(FPS), []
        for f in frames:
            got.append(meter.add(f))
        assert got[0] == (0.0, 0) and meter.frames == len(frames)
        assert meter.area_max == max(a for a, _ in got) == flash_area(frames, fps=FPS)
        assert meter.squares_max == max(s for _, s in got) == square_flashes(frames, fps=FPS)
    for frames in cases[:3]:                                     # not 0 == 0
        assert flash_area(frames, fps=FPS) > 0.5 and square_flashes(frames, fps=FPS) > BUDGET


def test_take_gives_the_maxima_since_the_last_take():
    meter = FlashMeter(FPS)
    frames = strobes(64, 128, 30, 1)
    for f in frames:
        meter.add(f)
    first = meter.take()
    assert first == (meter.area_max, meter.squares_max) and first[0] > 0.5 and first[1] > BUDGET
    assert meter.take() == (0.0, 0)                           # nothing added since
    still = np.zeros((64, 128, 3), np.uint8)
    got = [meter.add(still) for _ in range(40)]                # the strobe's last flips leave the window
    assert meter.take() == (max(a for a, _ in got), max(s for _, s in got))
    assert got[-1] == (0.0, 0) and meter.take() == (0.0, 0)
    assert meter.frames == 70 and (meter.area_max, meter.squares_max) == first   # over every frame added


def test_governed_frames_meter_inside_the_budget():
    wall, meter = GovernedDisplay(FakeDisplay(), H, W, fps=FPS), FlashMeter(FPS)
    for f in strobe(100):
        meter.add(wall.push(f))
    assert meter.frames == 100 and meter.squares_max <= BUDGET and meter.area_max == 0.0
    assert wall.governor.held_ticks > 0
