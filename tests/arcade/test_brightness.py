import dataclasses
import logging
import math
import zlib
from datetime import datetime, timedelta

import numpy as np
import pytest

from arcade.brightness import LUX_HOLD_S, LUX_RELEASE, MIN_FACTOR, RELEASE, BrightnessLimiter, apl
from arcade.config import ArcadeConfig
from arcade.flash import BUDGET, SMALL_AREA, FlashGovernor, concurrent_area, flash_area, square_flashes


class Clock:
    """A settable local clock."""

    def __init__(self, when: str = "2026-11-11T21:00"):
        self.set(when)

    def __call__(self) -> datetime:
        return self.now

    def set(self, when: str) -> None:
        self.now = datetime.fromisoformat(when)

    def tick(self, seconds: float = 1 / 30) -> None:
        self.now += timedelta(seconds=seconds)


def limiter(clock=None, lux=None, **over):
    return BrightnessLimiter(dataclasses.replace(ArcadeConfig(), **over), clock or Clock(), lux)


def frame(value, h=32, w=128):
    return np.full((h, w, 3), value, np.uint8)


def test_apl_is_the_mean_light_after_gamma():
    assert apl(frame(0), 2.2) == 0.0 and apl(frame(255), 2.2) == pytest.approx(1.0)
    assert apl(frame(128), 2.2) == pytest.approx(128 / 255, rel=1e-6)        # the card sends bytes as they are
    assert apl(frame(128), 1.0) == pytest.approx((128 / 255) ** 2.2, rel=1e-5)  # the card applies gamma
    half = frame(0)
    half[:, :64, 0] = 255                                                   # red on half the wall: 1/6 of the light
    assert apl(half, 2.2) == pytest.approx(1 / 6, rel=1e-6)


def test_frame_under_cap_passes_identical():
    lim = limiter()
    dim = frame(0)
    dim[:, :, 1] = 30                                                       # APL 0.039, under the day cap 0.12
    assert lim.apply(dim) is dim and lim.factor == 1.0 and lim.scaled_ticks == 0
    at_cap = frame(0)
    at_cap[:4, :, :] = 255
    at_cap[4:5, :32, :] = 255                                               # 544 of 4096 pixels white: APL 0.1328
    lim = limiter(apl_cap_day=544 / 4096)
    assert lim.apply(at_cap) is at_cap and lim.scaled_ticks == 0            # exactly at the cap is not over it


def test_white_frame_scaled_not_below_half():
    lim = limiter()
    out = lim.apply(frame(255))
    assert MIN_FACTOR == 0.5 and lim.factor == 0.5 and lim.scaled_ticks == 1
    assert out.dtype == np.uint8 and np.all(out == 128)                     # 255 * 0.5 rounds to 128
    assert apl(out, 2.2) == pytest.approx(128 / 255, rel=1e-6)             # over the cap: the floor wins
    f = frame(255)
    f[0, 0] = 5
    assert limiter().apply(f)[0, 0, 0] == 3                                 # 2.5 rounds half up, not to even


def test_factor_falls_at_once_and_rises_slowly():
    assert RELEASE == pytest.approx(0.01)                                  # a tenth of a flash's swing a tick
    lim = limiter()
    lim.apply(frame(255))
    black = frame(0)
    factors = []
    for _ in range(50):
        out = lim.apply(black)
        factors.append(lim.factor)
        assert np.all(out == 0)
    assert factors[0] == pytest.approx(0.51) and factors[-2] == pytest.approx(0.99) and factors[-1] == 1.0
    assert lim.scaled_ticks == 50 and lim.apply(black) is black             # back to 1.0: the frame as it is
    f = frame(0)
    f[:6, :, :] = 200                                                       # needs 0.816: falls there at once
    lim.apply(f)
    assert lim.factor == pytest.approx(0.12 / apl(f, 2.2))
    lim.apply(frame(255))
    assert lim.factor == 0.5
    lim.apply(f)
    assert lim.factor == pytest.approx(0.51)                                # needs more: rises by RELEASE
    lim.apply(frame(255))
    lim.apply(frame(61))                                                    # needs 0.502: rises to it, not past
    assert lim.factor == pytest.approx(0.12 / apl(frame(61), 2.2)) and lim.factor < 0.505


def test_frame_over_cap_lands_on_the_cap():
    f = frame(0)
    f[:6, :, :] = 200                                                       # APL 0.1471 against a cap of 0.12
    lim = limiter()
    out = lim.apply(f)
    assert lim.factor == pytest.approx(0.12 / apl(f, 2.2))
    assert abs(apl(out, 2.2) - 0.12) < 1 / 255 and np.all(out[6:] == 0)     # black stays black
    assert np.all(out[:6] == math.floor(200 * lim.factor + 0.5))            # one lookup table for every channel
    assert f[0, 0, 0] == 200                                                # the input is not changed


def test_scaling_follows_gamma():
    # Grey 128 is 0.502 of the light on an uncorrected wall but 0.2195 when the card applies gamma (1.0).
    lim = limiter(gamma=1.0)
    out = lim.apply(frame(128))
    assert lim.factor == pytest.approx(0.12 / (128 / 255) ** 2.2, rel=1e-5)
    assert np.all(out == 97) and abs(apl(out, 1.0) - 0.12) < 0.002         # 128 * 0.547 ** (1 / 2.2) = 97.3
    lim = limiter(gamma=2.2)
    assert np.all(lim.apply(frame(128)) == 64) and lim.factor == 0.5        # 0.239 would be under the floor


def test_night_by_clock_spans_midnight():
    clock = Clock()
    lim = limiter(clock)                                                    # the defaults: 01:00 to 06:00
    for when, night in (("2026-11-11T21:00", False), ("2026-11-12T00:59", False), ("2026-11-12T01:00", True),
                        ("2026-11-12T05:59", True), ("2026-11-12T06:00", False)):
        clock.set(when)
        assert lim.is_night() is night and lim.cap() == (0.06 if night else 0.12), when
    lim = limiter(clock, night_start="22:00", night_end="06:00")
    for when, night in (("2026-11-11T21:59", False), ("2026-11-11T22:00", True), ("2026-11-12T00:00", True),
                        ("2026-11-12T05:59", True), ("2026-11-12T06:00", False), ("2026-11-12T12:00", False)):
        clock.set(when)
        assert lim.is_night() is night, when
    lim = limiter(clock, night_start="03:00", night_end="03:00")            # equal times: never night
    for when in ("2026-11-12T02:59", "2026-11-12T03:00", "2026-11-12T03:01"):
        clock.set(when)
        assert lim.is_night() is False, when
    clock.set("2026-11-12T02:00")
    assert np.all(limiter(clock).apply(frame(40)) == 20)                    # APL 0.157, night cap 0.06: the floor
    clock.set("2026-11-12T12:00")
    assert np.all(limiter(clock).apply(frame(40)) == 31)                    # day cap 0.12: 40 * 0.765


def test_lux_only_adds_night():
    clock = Clock("2026-11-12T02:00")                                       # night by the clock
    reading = [300.0]
    lim = limiter(clock, lux=lambda: reading[0])
    assert lim.is_night() and lim.cap() == 0.06                             # a bright sensor never ends it
    clock.set("2026-11-11T21:00")                                           # day by the clock
    for value, night in ((5.0, False), (np.float64(900.0), False), (None, False), (math.nan, False),
                         (-math.inf, False), (True, False), ("2", False), (4.99, True)):
        reading[0] = value
        assert lim.is_night() is night, value                               # no reading: the clock decides
    for value in (np.float32(1.0), -1.0, 0):
        lim = limiter(clock, lux=lambda: value)
        assert lim.is_night() is True and lim.cap() == 0.06, value         # dark by the sensor
    assert limiter(clock, lux=lambda: 0.0, night_lux=0).is_night() is False  # night_lux 0: lux never adds night


def test_lux_night_ends_after_10_bright_seconds():
    assert LUX_RELEASE == 1.5 and LUX_HOLD_S == 10.0
    clock = Clock("2026-11-11T21:00")
    reading = [4.9]
    lim = limiter(clock, lux=lambda: reading[0])
    for i in range(600):                                                    # 20 s of a reading flapping at 5
        reading[0] = (4.9, 5.1)[i % 2]
        assert lim.cap() == 0.06, i
        clock.tick()
    for value in (7.49, 7.0, 5.0):                                          # under 1.5 x night_lux: still dark
        reading[0] = value
        clock.tick(9.0)
        assert lim.is_night(), value
    reading[0] = 7.5
    lim.is_night()
    clock.tick(9.9)
    assert lim.is_night()
    clock.tick(0.1)
    assert not lim.is_night()                                               # 10 s since the last dark reading
    reading[0] = 5.1
    assert not lim.is_night()                                               # day again: 5.1 is not dark
    reading[0] = 4.0
    assert lim.is_night()
    reading[0] = None                                                       # the sensor goes away
    clock.tick(9.9)
    assert lim.is_night()
    clock.tick(0.1)
    assert not lim.is_night()                                               # then the clock decides
    reading[0] = 4.0
    lim.is_night()
    clock.set("2026-11-11T20:00")                                           # a clock set back keeps the night
    reading[0] = 900.0
    assert lim.is_night()


def test_a_failing_lux_sensor_is_no_reading(caplog):
    clock = Clock("2026-11-11T21:00")

    def broken():
        raise OSError("no metadata")

    lim = limiter(clock, lux=broken)
    with caplog.at_level(logging.ERROR, logger="arcade.brightness"):
        assert [lim.is_night() for _ in range(3)] == [False] * 3
        clock.set("2026-11-12T02:00")
        assert lim.is_night() and lim.cap() == 0.06
    assert len(caplog.records) == 1 and "lux" in caplog.records[0].getMessage()


def limited_then_governed(frames, lux=None, clock=None, governor=None):
    """The runner's order (Q11): limiter, then governor, then push. Returns what the limiter made and what is
    pushed."""
    lim = limiter(clock, lux=lux)
    g = governor or FlashGovernor(*frames[0].shape[:2])
    limited = [lim.apply(f) for f in frames]
    return limited, [g.apply(f) for f in limited]


def test_limiter_then_governor_never_strobes():
    # A static score strip, with the left and right halves each flashing 2.5 times a second out of phase: a
    # limiter that followed each frame's level at once would strobe the strip between 255 and 128.
    frames = []
    for i in range(120):
        f = frame(0)
        f[:4, :32] = 255
        if i % 12 < 3:
            f[4:, :64] = 255
        elif 6 <= i % 12 < 9:
            f[4:, 64:] = 255
        frames.append(f)
    limited, pushed = limited_then_governed(frames)
    assert flash_area(frames) == 0.0 and flash_area(limited) == 0.0 and flash_area(pushed) == 0.0
    assert len({int(f[0, 0, 0]) for f in limited}) > 1                     # the strip does dim and recover
    # A static frame under a lux reading flapping across night_lux: the cap holds, the picture does not move.
    reading = iter([4.9, 5.1] * 60)
    limited, pushed = limited_then_governed([frame(40)] * 120, lux=lambda: next(reading))
    assert all(np.array_equal(f, limited[0]) for f in limited) and np.all(limited[0] == 20)
    # Random blocks switching at random under a flapping, failing sensor: the pushed frames keep the bound, on
    # every pixel outside a small flash and on every square's mean light.
    seed = zlib.crc32(b"limiter-then-governor")
    rng = np.random.default_rng(seed)
    for trial in range(30):
        blocks = [(rng.integers(0, 32), rng.integers(0, 128), rng.integers(2, 20), rng.integers(2, 64),
                   rng.integers(0, 256, 3)) for _ in range(8)]
        on = rng.random(8) < 0.5
        frames = []
        for _ in range(60):
            on ^= rng.random(8) < 0.3
            f = frame(0)
            for (y, x, h, w, c), lit in zip(blocks, on):
                if lit:
                    f[y:y + h, x:x + w] = c
            frames.append(f)
        values = iter(rng.choice([4.9, 5.1, np.nan], 60))
        g = FlashGovernor(32, 128)
        limited, pushed = limited_then_governed(frames, lux=lambda: next(values), governor=g)
        assert g.held_ticks > 0 and concurrent_area(pushed) < SMALL_AREA, (trial, seed)
        assert square_flashes(pushed) <= BUDGET, (trial, seed)


def test_limiter_rejects_bad_config_and_frames():
    for over in (dict(apl_cap_day=0.0), dict(apl_cap_night=1.5), dict(apl_cap_day=math.nan),
                 dict(apl_cap_night=None), dict(apl_cap_day=True), dict(night_lux=-1.0), dict(night_lux=math.nan),
                 dict(night_lux="5"), dict(night_start="1:00"), dict(night_end="24:00"), dict(night_start="01:000"),
                 dict(night_start=None), dict(gamma=0.0), dict(gamma=math.inf), dict(gamma="2.2")):
        with pytest.raises(ValueError):
            limiter(**over)
    limiter(apl_cap_day=np.float64(0.2), night_lux=0, night_start="23:59", night_end="00:00")
    limiter(apl_cap_day=1.0, apl_cap_night=1.0)                             # a cap of all the light is allowed
    lim = limiter()
    for bad in (np.zeros((4, 8, 3), np.float32), np.zeros((4, 8), np.uint8), np.zeros((4, 8, 4), np.uint8)):
        with pytest.raises(ValueError):
            lim.apply(bad)
