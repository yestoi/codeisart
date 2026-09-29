import argparse

import numpy as np
import pytest

from tools.ledvision import wall_cam


def test_parse_size():
    assert wall_cam.parse_size("1280x720") == (1280, 720)
    assert wall_cam.parse_size("1920X1080") == (1920, 1080)
    for bad in ("1280", "x720", "wide x tall"):
        with pytest.raises(argparse.ArgumentTypeError):
            wall_cam.parse_size(bad)


def blinking(n=12, shape=(60, 100)):
    """Frames with a steady saturated band (rows 10-12), sensor noise, and one LED at x=70, y=40 that blinks."""
    rng = np.random.default_rng(0)
    frames = rng.integers(40, 46, size=(n, *shape)).astype(np.uint8)
    frames[:, 10:13, :] = 255
    frames[::2, 40, 70] = 230
    return frames


def test_flash_peaks_find_the_blinking_led_not_the_steady_band():
    peaks = wall_cam.flash_peaks(wall_cam.flash_range(blinking()), count=3)
    x, y, spread = peaks[0]
    assert (x, y) == (70, 40) and spread > 150
    assert all(not 10 <= py <= 12 for _, py, _ in peaks)


def test_flash_peaks_are_kept_apart():
    frames = blinking()
    frames[::2, 40, 74] = 200          # a second blink 4 px from the first: the same LED's glow
    frames[::2, 20, 10] = 200          # a third, far away: another point
    peaks = wall_cam.flash_peaks(wall_cam.flash_range(frames), count=3, apart=15)
    found = [(x, y) for x, y, _ in peaks[:2]]
    assert found[0] == (70, 40) and found[1] == (10, 20)


def test_parse_box():
    assert wall_cam.parse_box("622,218,995,405") == (622, 218, 995, 405)
    for bad in ("622,218,995", "a,b,c,d", "995,218,622,405"):
        with pytest.raises(argparse.ArgumentTypeError):
            wall_cam.parse_box(bad)


def test_panel_cell_counts_from_the_top_left_as_seen_from_the_front():
    box = (600, 200, 984, 392)               # 64 columns x 32 rows, 6 px each
    assert wall_cam.panel_cell(601, 201, box) == (1, 1)
    assert wall_cam.panel_cell(983, 391, box) == (32, 64)
    assert wall_cam.panel_cell(600 + 6 * 8 + 3, 200 + 6 * 8 + 3, box) == (9, 9)
    assert wall_cam.panel_cell(599, 300, box) is None and wall_cam.panel_cell(700, 392, box) is None
