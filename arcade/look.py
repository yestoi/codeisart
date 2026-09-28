"""Preview render modes (spec 9.4): how a wall frame looks as flat pixels, as LED dots, and from a distance.

Pure numpy: this module never imports cv2, so the SDL preview never loads OpenCV's own SDL next to pygame's.
"""
from __future__ import annotations

import math
import numbers
import operator
from functools import lru_cache

import numpy as np

MODES = ("plain", "led", "distance")

MONITOR_GAMMA = 2.2        # a preview's bytes are decoded by an sRGB monitor
PITCH_M = 0.005            # P5 modules: 5 mm between LEDs
BLUR_ARCMIN = 1.5          # what the eye resolves at night (spec 9.4)
HALATION_SIGMAS = 3.0      # the glow around bright pixels spreads three times as far as the blur
HALATION = 0.3             # the share of a white pixel's light scattered into the glow (times luminance); under 1
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)   # Rec. 709 weights on linear light


def _frozen(a: np.ndarray) -> np.ndarray:
    """A cached array is shared by every caller, so it is read-only: an in-place edit raises."""
    a.flags.writeable = False
    return a


@lru_cache(maxsize=8)
def gamma_lut(gamma: float) -> np.ndarray:
    v = np.arange(256, dtype=np.float64) / 255.0
    return _frozen(np.clip(np.round(255.0 * v ** (1.0 / gamma)), 0, 255).astype(np.uint8))


def apply_gamma(frame: np.ndarray, gamma: float) -> np.ndarray:
    """frame through gamma_lut(gamma), always a new array: at 1.0 a copy, so a caller may write into it."""
    if gamma == 1.0:
        return frame.copy()
    return gamma_lut(gamma)[frame]


@lru_cache(maxsize=8)
def _led_kernel(scale: int) -> np.ndarray:
    c = (scale - 1) / 2
    yy, xx = np.mgrid[0:scale, 0:scale]
    d = np.hypot(xx - c, yy - c) / scale
    return _frozen(np.where(d <= 0.36, 1.0, np.where(d <= 0.5, 0.3, 0.0)).astype(np.float32))


def _nearest(frame: np.ndarray, scale: int) -> np.ndarray:
    return np.repeat(np.repeat(frame, scale, axis=0), scale, axis=1)


def distance_sigma(metres: float) -> float:
    """The eye's blur at this distance, in wall pixels: 1.5 arcmin across the 5 mm pitch (0.436 at 5 m).

    The preview blurs sigma * scale preview pixels with three box blurs, which cannot go below one pixel:
    at scale 1 and 5 m the boxes have radius 0 and the core is not blurred at all (the glow still is), so
    judge distance at scale 4 or more."""
    return metres * math.tan(math.radians(BLUR_ARCMIN / 60.0)) / PITCH_M


@lru_cache(maxsize=8)
def _light_lut(gamma: float) -> np.ndarray:
    """Byte to the light the preview shows, 0..1: the led look's bytes as a monitor decodes them."""
    v = np.arange(256, dtype=np.float64) / 255.0
    return _frozen((v ** (MONITOR_GAMMA / gamma)).astype(np.float32))


def light_lut(gamma: float) -> np.ndarray:
    """Byte to the light the wall emits, 0..1 of full: the led and distance looks' own read-only table, shared
    with the flash governor and the brightness limiter so all of them agree. With gamma 2.2 the card sends bytes
    as they are and the light is linear in the byte; with 1.0 the card applies gamma and the light is
    (byte / 255) ** 2.2. A gamma that is not a finite number over 0 raises ValueError."""
    if not (is_real(gamma) and 0.0 < gamma < math.inf):
        raise ValueError(f"gamma must be over 0 and finite, got {gamma!r}")
    return _light_lut(float(gamma))


def _box_radii(sigma: float, n: int = 3) -> list[int]:
    """Radii of n box blurs whose sum approximates a Gaussian of this sigma (Kovesi's widths)."""
    sigma = min(sigma, 1e6)               # wider than any preview already; keeps the squares finite
    ideal = math.sqrt(12.0 * sigma * sigma / n + 1.0)
    lo = int(ideal)
    lo -= 1 - lo % 2                      # the largest odd width at or under the ideal
    m = round((12.0 * sigma * sigma - n * lo * lo - 4 * n * lo - 3 * n) / (-4 * lo - 4))
    return [(lo if i < m else lo + 2) // 2 for i in range(n)]


def _box(a: np.ndarray, r: int, axis: int) -> np.ndarray:
    """Mean over 2r + 1 cells along axis; cells past the edge are dark, as the air beside the wall is."""
    if r <= 0:
        return a
    if r >= a.shape[axis]:                  # every window holds the whole line: one mean, and no huge pads
        return np.broadcast_to(a.sum(axis=axis, keepdims=True) / (2 * r + 1), a.shape).copy()
    a = np.moveaxis(a, axis, 0)
    pad = np.zeros((r + 1,) + a.shape[1:], a.dtype), a, np.zeros((r,) + a.shape[1:], a.dtype)
    c = np.cumsum(np.concatenate(pad), axis=0)
    out = (c[2 * r + 1:] - c[:-2 * r - 1]) / (2 * r + 1)
    return np.moveaxis(out, 0, axis)


@lru_cache(maxsize=16)
def _spread(n: int, scale: int, sigma: float) -> np.ndarray:
    """(n * scale, n): how one wall pixel's light lands on a preview line after the nearest-neighbour
    upscale and three box blurs. The blur is linear and separable, so it is built once per size."""
    m = np.repeat(np.eye(n, dtype=np.float32), scale, axis=0)
    for r in _box_radii(sigma):
        m = _box(m, r, 0)
    return _frozen(np.ascontiguousarray(m))


def _gauss(light: np.ndarray, scale: int, sigma: float) -> np.ndarray:
    """light (h, w, 3) at wall resolution, upscaled by scale and blurred by a Gaussian of sigma preview px."""
    h, w, _ = light.shape
    rows = (_spread(h, scale, sigma) @ light.reshape(h, w * 3)).reshape(h * scale, w, 3)
    return np.einsum("Ywc,Xw->YXc", rows, _spread(w, scale, sigma), optimize=True)


def _distance(frame: np.ndarray, scale: int, gamma: float, metres: float) -> np.ndarray:
    """Light is conserved: a luminance-weighted share of each pixel's light scatters into the wide glow and
    the rest stays in the eye's blur, so a flat field keeps the led look's level at every distance."""
    light = _light_lut(gamma)[frame]
    sigma = distance_sigma(metres) * scale
    scattered = HALATION * light * (light @ LUMA)[..., None]
    core = _gauss(light - scattered, scale, sigma)
    halo = _gauss(scattered, scale, HALATION_SIGMAS * sigma)
    shown = np.clip(core + halo, 0.0, 1.0) ** (1.0 / MONITOR_GAMMA)
    return np.round(shown * 255.0).astype(np.uint8)


def is_real(v) -> bool:
    """A real number (NaN and infinities included), not a bool, None or a string."""
    return isinstance(v, numbers.Real) and not isinstance(v, (bool, np.bool_))


def check_settings(mode: str, scale: int, gamma: float, metres: float = 5.0) -> int:
    """Raises ValueError unless these render settings are valid; returns scale as an int.

    mode is one of MODES; scale is any integer type of at least 1 (a numpy integer from a computed fit,
    never a float or a bool); gamma is over 0 and finite; metres is 0 or more and finite. None, a string
    or a bool for gamma or metres raises ValueError too, not TypeError."""
    if mode not in MODES:
        raise ValueError(f"look must be one of {MODES}, got {mode!r}")
    try:
        size = operator.index(scale)                   # an int or a numpy integer; never a float
    except TypeError:
        size = 0
    if isinstance(scale, (bool, np.bool_)) or size < 1:
        raise ValueError(f"scale must be an int of at least 1, got {scale!r}")
    if not (is_real(gamma) and 0.0 < gamma < math.inf):
        raise ValueError(f"gamma must be over 0 and finite, got {gamma!r}")
    if not (is_real(metres) and 0.0 <= metres < math.inf):
        raise ValueError(f"metres must be 0 or more and finite, got {metres!r}")
    return size


def render(frame: np.ndarray, mode: str, scale: int = 8, gamma: float = 2.2, metres: float = 5.0) -> np.ndarray:
    """frame (h, w, 3) uint8 drawn at scale for a monitor.

    plain: nearest-neighbour, the bytes as they are. led: round dots with dark gaps, after gamma (with
    gamma 2.2 the preview shows the light of an uncorrected wall; with 1.0, the bytes as the card
    applies gamma). distance: each pixel as a full square of the led look's light (not its dot), seen
    from metres away: blurred by 1.5 arcmin, with a luminance-weighted share scattered into a glow three
    times wider, for legibility checks (spec 9.4). At 5 m the real eye still resolves the 5 mm dot grid,
    so text reads slightly smoother in this preview than on the wall. Settings are checked by
    check_settings; scale may be any integer type.
    """
    scale = check_settings(mode, scale, gamma, metres)
    if frame.ndim != 3 or frame.shape[2] != 3 or frame.dtype != np.uint8:
        raise ValueError(f"frame must be (height, width, 3) uint8, got {frame.shape} {frame.dtype}")
    if mode == "plain":
        return _nearest(frame, scale)
    if mode == "distance":
        return _distance(frame, scale, gamma, metres)
    f = apply_gamma(frame, gamma)
    h, w = f.shape[:2]
    k = _led_kernel(scale)
    out = f[:, None, :, None, :].astype(np.float32) * k[None, :, None, :, None]
    return out.reshape(h * scale, w * scale, 3).astype(np.uint8)


def dim(image: np.ndarray, level: float) -> np.ndarray:
    """A preview image showing level (0..1) of its light: a monitor decodes bytes with MONITOR_GAMMA, so
    the bytes scale by level ** (1 / MONITOR_GAMMA). NaN or a level not over 0 gives black; None, a
    string or a bool is not a level and raises ValueError."""
    if not is_real(level):
        raise ValueError(f"level must be a number, got {level!r}")
    if not level > 0.0:
        return np.zeros_like(image)
    if level >= 1.0:
        return image
    factor = level ** (1.0 / MONITOR_GAMMA)
    return np.round(image.astype(np.float32) * factor).astype(np.uint8)
