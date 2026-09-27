from __future__ import annotations

from typing import Callable, Protocol

import numpy as np


class DisplayConfig(Protocol):
    """Any object with these attributes can be handed to make_display.

    `iface` is the wired interface for the colorlight backend; the daemon's Config calls it
    `colorlight_iface`, and make_display reads either.
    """

    width: int
    height: int
    backend: str
    sdl_scale: int
    ddp_host: str
    ddp_port: int
    iface: str


class Display(Protocol):
    def push(self, frame: np.ndarray) -> None: ...
    def set_brightness(self, level: float) -> None: ...
    def close(self) -> None: ...


def make_display(cfg: DisplayConfig, on_key: Callable[[int], None] | None = None) -> Display:
    if cfg.backend == "fake":
        from show.display.fake import FakeDisplay
        return FakeDisplay()
    if cfg.backend == "sdl":
        from show.display.sdl import SDLDisplay
        return SDLDisplay(cfg.width, cfg.height, cfg.sdl_scale, on_key)
    raise ValueError(f"unknown display backend {cfg.backend!r}")
