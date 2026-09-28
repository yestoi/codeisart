import math
import statistics
import subprocess
import sys
import time
import warnings
import zlib
from pathlib import Path

import numpy as np
import pytest

import arcade.look as look
from arcade.config import LOOKS
from arcade.look import MODES, apply_gamma, distance_sigma, gamma_lut, render
from arcade.preview import PreviewDisplay
from show.display.fake import FakeDisplay

ROOT = Path(__file__).resolve().parents[2]


def frame_with_dot(w=8, h=4):
    f = np.zeros((h, w, 3), np.uint8)
    f[1, 2] = (128, 0, 0)
    return f


def test_gamma_lut_brightens_midtones_and_identity_at_one():
    lut = gamma_lut(2.2)
    assert lut[0] == 0 and lut[255] == 255 and lut[128] > 128
    assert np.array_equal(gamma_lut(1.0), np.arange(256, dtype=np.uint8))
    f = frame_with_dot()
    assert apply_gamma(f, 2.2)[1, 2, 0] == lut[128]


def test_plain_is_nearest_neighbour():
    out = render(frame_with_dot(), "plain", scale=4, gamma=2.2)
    assert out.shape == (16, 32, 3)
    assert (out[4:8, 8:12, 0] == 128).all() and out[0, 0].sum() == 0


def test_led_draws_round_dots_with_dark_gaps():
    out = render(frame_with_dot(), "led", scale=8, gamma=1.0)
    cell = out[8:16, 16:24, 0]
    assert cell[4, 4] == 128
    assert cell[0, 0] == 0 and cell[0, 7] == 0
    assert 0 < (cell > 0).sum() < 64
    assert out[0:8, 0:8].sum() == 0


def test_distance_blurs():
    out = render(frame_with_dot(), "distance", scale=8, gamma=1.0, metres=5.0)
    assert out.shape == (32, 64, 3)
    assert out[12, 20, 0] > 0 and out[12, 20, 0] < 128
    assert out[9, 13, 0] > 0


def test_unknown_mode_rejected():
    with pytest.raises(ValueError):
        render(frame_with_dot(), "crt")


def test_preview_display_renders_before_push():
    inner = FakeDisplay()
    d = PreviewDisplay(inner, "plain", scale=2, gamma=1.0)
    d.push(frame_with_dot())
    assert inner.last.shape == (8, 16, 3)
    d.set_brightness(0.3)
    assert inner.brightness == 0.3
    d.close()
    assert inner.closed


def spread(out: np.ndarray) -> float:
    """Root-mean-square distance of the red light from its centre, in preview pixels."""
    light = (out[:, :, 0] / 255.0) ** 2.2
    yy, xx = np.mgrid[0:out.shape[0], 0:out.shape[1]]
    cy, cx = (light * yy).sum() / light.sum(), (light * xx).sum() / light.sum()
    return math.sqrt((light * ((yy - cy) ** 2 + (xx - cx) ** 2)).sum() / light.sum())


def test_distance_blur_grows_with_metres():
    f = np.zeros((9, 16, 3), np.uint8)
    f[4, 8] = (255, 0, 0)
    near, mid, far = (spread(render(f, "distance", scale=8, gamma=2.2, metres=m)) for m in (2.0, 5.0, 10.0))
    assert near < mid < far and far > 1.5 * near
    assert distance_sigma(5.0) == pytest.approx(5.0 * math.tan(math.radians(1.5 / 60)) / 0.005)
    assert distance_sigma(5.0) == pytest.approx(0.436, abs=1e-3)   # 1.5 arcmin at 5 m is under half a P5 pixel
    sharp = render(f, "distance", scale=8, gamma=2.2, metres=0.0)
    assert (sharp[:, :, 0] > 0).sum() == 64                          # at 0 m nothing spreads past the LED
    start = time.perf_counter()
    assert render(f, "distance", scale=8, gamma=2.2, metres=1e300).max() == 0   # too far to see: no overflow
    assert time.perf_counter() - start < 0.5                                     # and no giant blur buffers


def test_distance_halation_follows_luminance():
    # 16 preview px (2 wall px) from a lit pixel the 5 m blur has died out; only the halation glow is left,
    # and it follows luminance: a green pixel glows further than an equally bright blue one.
    def far_glow(color, channel):
        f = np.zeros((5, 16, 3), np.uint8)
        f[2, 2] = color
        return int(render(f, "distance", scale=8, gamma=2.2, metres=5.0)[20, 36, channel])

    green, blue, white = far_glow((0, 255, 0), 1), far_glow((0, 0, 255), 2), far_glow((255, 255, 255), 0)
    assert blue > 0 and green > 2 * blue and white >= green
    f = np.zeros((5, 16, 3), np.uint8)
    f[2, 2] = (0, 255, 0)
    assert render(f, "distance", scale=8, gamma=2.2, metres=5.0)[20, 60].sum() == 0   # 5 wall px: dark
    assert render(np.zeros((32, 128, 3), np.uint8), "distance").sum() == 0



def test_distance_conserves_light_and_keeps_strokes_apart():
    # The glow redistributes light, never adds it: a flat field keeps the led look's level at any distance.
    for color in ((128, 128, 128), (255, 200, 0), (60, 60, 60)):
        flat = np.full((32, 128, 3), color, np.uint8)
        for metres in (0.0, 5.0, 10.0):
            inner = render(flat, "distance", scale=8, gamma=2.2, metres=metres)[128, 512]
            assert np.abs(inner.astype(int) - gamma_lut(2.2)[list(color)]).max() <= 1, (color, metres)
    # Spec 7.4: 1 px strokes read at 5 m and scale-2 text (2 px strokes) to about 10 m, so the gap between
    # two strokes stays darker than the strokes. This bounds HALATION (0.5 passes, 0.6 fails).
    one = np.zeros((9, 16, 3), np.uint8)
    one[:, 6] = one[:, 8] = 255                                      # 1 px strokes, 1 px gap
    two = np.zeros((9, 20, 3), np.uint8)
    two[:, 6:8] = two[:, 10:12] = 255                                # 2 px strokes and gap
    near = render(one, "distance", scale=8, gamma=2.2, metres=5.0)[36, :, 0]
    far = render(two, "distance", scale=8, gamma=2.2, metres=10.0)[36, :, 0]
    assert near[60] < 0.85 * near[52] and far[72] < 0.85 * far[56]   # the gap stays darker


def test_distance_blur_has_its_width_and_dark_edges(monkeypatch):
    # One lit white wall pixel spreads as a Gaussian convolved with the 8 px square: per axis, variance
    # sigma**2 + (scale**2 - 1) / 12 in preview pixels. With no glow that sigma is the eye's blur; with
    # all of white's light scattered it is the glow's, three times wider (the amendment's 3 sigma).
    for halation, widths in ((0.0, 1.0), (1.0, 3.0)):
        monkeypatch.setattr(look, "HALATION", halation)
        for metres in (5.0, 10.0):
            f = np.zeros((9, 71, 3), np.uint8)
            f[4, 35] = 255
            light = (render(f, "distance", scale=8, gamma=2.2, metres=metres)[:, :, 0] / 255.0) ** 2.2
            col, x = light.sum(axis=0), np.arange(71 * 8)
            centre = (col * x).sum() / col.sum()
            variance = (col * (x - centre) ** 2).sum() / col.sum()
            expected = (widths * distance_sigma(metres) * 8) ** 2 + (8 ** 2 - 1) / 12
            assert variance == pytest.approx(expected, rel=0.1), (halation, metres)
    monkeypatch.setattr(look, "HALATION", 0.0)
    white = render(np.full((32, 128, 3), 255, np.uint8), "distance", scale=8, gamma=2.2, metres=5.0)
    assert white[0, 0, 0] < white[0, 512, 0] < white[128, 512, 0] == 255   # the air beside the wall is dark


def test_led_honours_gamma_and_cached_tables_are_read_only():
    assert render(frame_with_dot(), "led", scale=8, gamma=2.2)[12, 20, 0] == gamma_lut(2.2)[128]
    lut = gamma_lut(2.2)
    assert not lut.flags.writeable
    with pytest.raises(ValueError):
        lut[128] = 0                                                 # would corrupt every later preview
    render(frame_with_dot(), "distance", scale=8)
    assert not any(a.flags.writeable for a in (look._led_kernel(8), look._light_lut(2.2), look._spread(4, 8, 3.5)))


@pytest.mark.perf
def test_distance_keeps_up_with_the_preview():
    # look = "distance" renders every tick of an SDL run, and the preview dims it: a 128x32 wall at scale 8
    # must fit in a 30 Hz tick.
    seed = zlib.crc32(b"distance-perf")
    f = np.random.default_rng(seed).integers(0, 256, (32, 128, 3), dtype=np.uint8)
    d = PreviewDisplay(FakeDisplay(), "distance", scale=8, gamma=2.2)
    d.set_brightness(0.4)
    d.push(f)                                                        # builds the cached blur matrices
    times = []
    for _ in range(5):
        start = time.thread_time()
        d.push(f)
        times.append(time.thread_time() - start)
    assert statistics.median(times) < 1 / 30, f"median {statistics.median(times) * 1000:.1f} ms, seed={seed}"


def test_render_rejects_bad_input():
    good = frame_with_dot()
    bad = [
        dict(frame=good.astype(np.float32)), dict(frame=good[:, :, 0]), dict(frame=good[:, :, :2]),
        dict(scale=0), dict(scale=2.5), dict(scale=True), dict(scale=np.float64(2.0)), dict(scale=np.int64(0)),
        dict(gamma=0.0), dict(gamma=math.nan),
        dict(gamma=math.inf), dict(metres=-1.0), dict(metres=math.nan), dict(metres=math.inf),
    ]
    for case in bad:
        args = dict(frame=good, mode="distance", scale=2, gamma=2.2, metres=5.0) | case
        with pytest.raises(ValueError):
            render(**args)
    assert MODES == LOOKS                                            # every configurable look renders
    for mode in MODES:                                               # a computed numpy scale is an int
        assert render(good, mode, scale=np.int64(2)).shape == (8, 16, 3)


def test_look_never_imports_cv2():
    code = "import sys, arcade.look, arcade.preview; print(sorted({'cv2', 'pygame'} & set(sys.modules)))"
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "[]"


def test_preview_models_brightness():
    inner = FakeDisplay()
    d = PreviewDisplay(inner, "plain", scale=1, gamma=1.0)
    wall = np.full((4, 8, 3), 255, np.uint8)
    d.push(wall)
    assert (inner.last == 255).all()                                 # full brightness until told otherwise
    d.set_brightness(0.25)
    d.push(wall)
    assert inner.brightness == 0.25 and (wall == 255).all()          # the wall frame itself is never scaled
    assert (inner.last == round(255 * 0.25 ** (1 / 2.2))).all()      # 136: the monitor shows a quarter of the light
    assert np.allclose((inner.last / 255.0) ** 2.2, 0.25, atol=0.01)
    with warnings.catch_warnings():
        warnings.simplefilter("error")                               # a NaN level never reaches the byte cast
        for level, expect in ((0.0, 0), (-1.0, 0), (math.nan, 0), (1.0, 255), (1.5, 255)):
            d.set_brightness(level)
            d.push(wall)
            assert (inner.last == expect).all(), level
    assert inner.brightness == 1.5                                   # forwarded unchanged, even above 1
    far = PreviewDisplay(FakeDisplay(), "distance", scale=4, gamma=2.2, metres=10.0)
    far.push(frame_with_dot())
    assert np.array_equal(far.inner.last, render(frame_with_dot(), "distance", scale=4, gamma=2.2, metres=10.0))


def test_apply_gamma_at_one_returns_a_copy():
    # C19: the led look and later callers (core Task 11) may write into the result.
    f = frame_with_dot()
    for gamma in (1.0, 2.2):
        out = apply_gamma(f, gamma)
        assert out is not f and not np.shares_memory(out, f) and out.dtype == np.uint8, gamma
        out[1, 2] = 0
        assert f[1, 2, 0] == 128, gamma                              # the caller's frame is untouched
    assert np.array_equal(apply_gamma(f, 1.0), f)


def test_settings_that_are_not_numbers_raise_value_error_at_construction():
    # C20: None, a string or a bool is a ValueError like any other bad setting, and PreviewDisplay checks its
    # settings when it is built, not on the first push.
    good = frame_with_dot()
    for case in (dict(gamma=None), dict(metres=None), dict(gamma="2.2"), dict(metres="5"), dict(gamma=True)):
        args = dict(mode="distance", scale=4, gamma=2.2, metres=5.0) | case
        with pytest.raises(ValueError):
            render(good, **args)
        with pytest.raises(ValueError):
            PreviewDisplay(FakeDisplay(), **args)
    for case in (dict(mode="crt"), dict(scale=0), dict(scale=2.0), dict(gamma=0.0), dict(metres=-1.0)):
        with pytest.raises(ValueError):
            PreviewDisplay(FakeDisplay(), **(dict(mode="led", scale=4, gamma=2.2, metres=5.0) | case))
    assert look.check_settings("led", np.int64(3), np.float64(2.2), 0) == 3
    assert type(look.check_settings("led", np.int64(3), 1.0)) is int
    assert type(PreviewDisplay(FakeDisplay(), "plain", np.int64(2), 1.0).scale) is int
    image = np.full((2, 2, 3), 200, np.uint8)
    for level in (None, "0.5", True):
        with pytest.raises(ValueError):
            look.dim(image, level)
    assert look.dim(image, math.nan).sum() == 0 and look.dim(image, 0).sum() == 0   # NaN and 0 are still black
    inner = FakeDisplay()
    d = PreviewDisplay(inner, "plain", scale=1, gamma=1.0)
    d.set_brightness(0.5)
    with pytest.raises(ValueError):
        d.set_brightness(None)
    assert d.level == 0.5 and inner.brightness == 0.5                         # neither kept nor forwarded


def test_light_lut_is_the_looks_table_checked():
    # The flash governor and the brightness limiter read the looks' own light table through this public name.
    assert look.light_lut(2.2) is look._light_lut(2.2) and look.light_lut(np.float32(1.0)) is look._light_lut(1.0)
    assert look.light_lut(2)[255] == 1.0 and not look.light_lut(1.8).flags.writeable
    gamma = np.float32(1.7)                                          # worked in float64, as the float it equals
    v = np.arange(256) / 255.0
    assert np.array_equal(look.light_lut(gamma), (v ** (look.MONITOR_GAMMA / float(gamma))).astype(np.float32))
    for bad in (0.0, -1.0, math.nan, math.inf, None, True, "2.2"):
        with pytest.raises(ValueError):
            look.light_lut(bad)
