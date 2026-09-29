"""Station lights: a lightbox (steady level) and a ring (pulses) per station."""
from __future__ import annotations

import logging
import math

log = logging.getLogger(__name__)

MODES = ("off", "on", "bright", "pulse")
LIGHTBOX = {"off": 0.0, "on": 0.4, "bright": 1.0, "pulse": 0.4}
SLOW_HZ = 0.5
FAST_HZ = 2.0
FLASH_S = 0.3
FLASH_PERIOD = 0.1


def pulse_level(now: float, hz: float) -> float:
    return 0.5 + 0.5 * math.sin(2 * math.pi * hz * now)


def levels(mode: str, now: float, flash_start: float | None) -> tuple[float, float]:
    box = LIGHTBOX[mode]
    if flash_start is not None and 0.0 <= now - flash_start < FLASH_S:
        return box, 1.0 if int((now - flash_start) / FLASH_PERIOD) % 2 == 0 else 0.0
    if mode == "off":
        ring = 0.0
    elif mode == "on":
        ring = pulse_level(now, SLOW_HZ)
    elif mode == "pulse":
        ring = pulse_level(now, FAST_HZ)
    else:
        ring = 1.0
    return box, ring


class FakeLights:
    def __init__(self) -> None:
        self.modes: dict[int, str] = {}
        self.levels: dict[int, tuple[float, float]] = {}
        self._flash: dict[int, float] = {}

    def set(self, station: int, mode: str) -> None:
        if mode not in MODES:
            raise ValueError(f"unknown light mode {mode!r}")
        self.modes[station] = mode

    def flash(self, station: int, now: float) -> None:
        self._flash[station] = now

    def all_off(self) -> None:
        for station in self.modes:
            self.modes[station] = "off"
        self._flash.clear()

    def tick(self, now: float) -> None:
        for station, mode in self.modes.items():
            self.levels[station] = levels(mode, now, self._flash.get(station))
        self._write()

    def _write(self) -> None:
        pass


class GpioLights(FakeLights):
    def __init__(self, ring_pins: list[int], lightbox_pins: list[int]) -> None:
        super().__init__()
        from gpiozero import PWMLED

        self._rings = [PWMLED(p) for p in ring_pins]
        self._boxes = [PWMLED(p) for p in lightbox_pins]

    def _write(self) -> None:
        for station, (box, ring) in self.levels.items():
            i = station - 1
            if 0 <= i < len(self._boxes):
                self._boxes[i].value = box
            if 0 <= i < len(self._rings):
                self._rings[i].value = ring

    def close(self) -> None:
        for led in self._rings + self._boxes:
            try:
                led.close()
            except Exception:
                log.exception("closing a light failed")


def make_lights(ring_pins: list[int], lightbox_pins: list[int]) -> FakeLights:
    try:
        return GpioLights(ring_pins, lightbox_pins)
    except Exception:
        log.error("lights unavailable, using fake lights", exc_info=True)
        return FakeLights()
