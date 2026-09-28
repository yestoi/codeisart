"""The brightness limiter (spec 7.6): caps the wall's average picture level, lower at night.

Runner-level, before the flash governor (Q11: limiter, then governor, then push). Unlike the display brightness
(a hard ceiling the card applies, never pixel scaling), this is a picture-level cap that does scale frames.
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, time
from typing import Callable

import numpy as np

from arcade.config import HHMM, ArcadeConfig
from arcade.flash import THRESHOLD
from arcade.look import MONITOR_GAMMA, is_real, light_lut

log = logging.getLogger(__name__)

MIN_FACTOR = 0.5         # the limiter never takes more than half the light: at most one bit lost
RELEASE = THRESHOLD / 10  # the factor rises at most this much a tick: 10 ticks to brighten a pixel by a flash
LUX_RELEASE = 1.5        # lux night ends only once no reading has been under 1.5 x night_lux ...
LUX_HOLD_S = 10.0        # ... for 10 seconds (Q12, loop decision 14)


def apl(frame: np.ndarray, gamma: float) -> float:
    """Average picture level: the mean light of every channel of every pixel, 0..1, after gamma (the
    light_lut model). Mean channel light is what the LEDs draw and what the review's APL figures measured."""
    return float(light_lut(gamma)[frame].mean())


def _hhmm(name: str, value) -> time:
    if not isinstance(value, str) or not HHMM.fullmatch(value):
        raise ValueError(f"{name} must be HH:MM (00:00 to 23:59), got {value!r}")
    return time(int(value[:2]), int(value[3:]))


class BrightnessLimiter:
    """apply(frame) scales frames down to cap() through a lookup table, never below MIN_FACTOR of their light.

    The factor falls at once to what the frame needs (cap / APL, at least MIN_FACTOR) and rises back by at
    most RELEASE a tick, so a level that comes and goes, or a cap that changes, never strobes the picture.
    A frame is returned as it is (the same array) while the factor is 1.0.

    cap() is apl_cap_night at night and apl_cap_day otherwise. is_night() is the clock's night OR lux night
    (Q12: lux only adds night). The clock's night is night_start <= now < night_end, spanning midnight when
    night_start is later than night_end; equal times mean never. Lux night starts at a reading under night_lux
    (lux() is the IMX500's lux metadata) and ends once no reading has been under LUX_RELEASE x night_lux for
    LUX_HOLD_S. None, NaN, an infinity, a reading that is not a number and an exception from lux() are no
    reading (an exception is logged once). clock returns local time: the runner passes a local clock, never
    its monotonic one. factor is the last scale applied and scaled_ticks counts the frames scaled. The config
    is checked here, since an ArcadeConfig built in code skips load_config: ValueError on a bad value, and on
    a frame that is not (h, w, 3) uint8.
    """

    def __init__(self, cfg: ArcadeConfig, clock: Callable[[], datetime] = datetime.now,
                 lux: Callable[[], float | None] | None = None):
        for name in ("apl_cap_day", "apl_cap_night"):
            v = getattr(cfg, name)
            if not is_real(v) or not 0.0 < v <= 1.0:
                raise ValueError(f"{name} must be in (0, 1], got {v!r}")
        if not is_real(cfg.night_lux) or not cfg.night_lux >= 0:
            raise ValueError(f"night_lux must be 0 or more, got {cfg.night_lux!r}")
        self.start, self.end = _hhmm("night_start", cfg.night_start), _hhmm("night_end", cfg.night_end)
        light_lut(cfg.gamma)                                         # checks gamma
        self.cfg, self.clock, self.lux = cfg, clock, lux
        self.factor, self.scaled_ticks = 1.0, 0
        self._dim_at: datetime | None = None                         # the last dark reading while lux night
        self._lux_failed = False

    def _reading(self) -> float | None:
        if self.lux is None:
            return None
        try:
            v = self.lux()
        except Exception:
            if not self._lux_failed:
                log.exception("lux reading failed: the clock decides the night")
                self._lux_failed = True
            return None
        return float(v) if is_real(v) and math.isfinite(v) else None

    def is_night(self) -> bool:
        now = self.clock()
        reading = self._reading()
        dark = self.cfg.night_lux * (1.0 if self._dim_at is None else LUX_RELEASE)
        if reading is not None and reading < dark:
            self._dim_at = now
        elif self._dim_at is not None and (now - self._dim_at).total_seconds() >= LUX_HOLD_S:
            self._dim_at = None
        t = now.time()
        if self.start < self.end:
            clock_night = self.start <= t < self.end
        else:
            clock_night = self.start > self.end and (t >= self.start or t < self.end)
        return clock_night or self._dim_at is not None

    def cap(self) -> float:
        return self.cfg.apl_cap_night if self.is_night() else self.cfg.apl_cap_day

    def apply(self, frame: np.ndarray) -> np.ndarray:
        if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError(f"frame must be (h, w, 3) uint8, got {frame.shape} {frame.dtype}")
        level, cap = apl(frame, self.cfg.gamma), self.cap()
        need = 1.0 if level <= cap else max(MIN_FACTOR, cap / level)
        self.factor = need if need < self.factor else min(need, self.factor + RELEASE)
        if self.factor == 1.0:
            return frame
        self.scaled_ticks += 1
        # light is (v / 255) ** (MONITOR_GAMMA / gamma): scaled by factor, v scales by factor ** (gamma / MONITOR_GAMMA)
        scale = self.factor ** (self.cfg.gamma / MONITOR_GAMMA)
        lut = np.floor(np.arange(256) * scale + 0.5).astype(np.uint8)      # scale <= 1: 255 at most
        return lut[frame]
