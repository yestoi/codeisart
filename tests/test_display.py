import os
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np
import pygame
import pytest

from show.config import Config
from show.display import make_display
from show.display.fake import FakeDisplay
from show.display.sdl import SDLDisplay


def test_fake_display_keeps_last_and_count():
    d = FakeDisplay()
    frame = np.zeros((192, 512, 3), np.uint8)
    d.push(frame)
    frame[0, 0] = 255
    d.push(frame)
    assert d.count == 2
    assert d.last.sum() == 765
    d.set_brightness(0.2)
    assert d.brightness == 0.2
    d.close()
    assert d.closed


def test_sdl_display_pushes_headless():
    pressed = []
    d = SDLDisplay(512, 192, scale=1, on_key=pressed.append)
    d.push(np.zeros((192, 512, 3), np.uint8))
    assert d.window.get_size() == (512, 192)
    assert tuple(d.window.get_at((0, 0)))[:3] == (0, 0, 0)
    d.push(np.full((192, 512, 3), 40, np.uint8))
    assert tuple(d.window.get_at((511, 191)))[:3] == (40, 40, 40)
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_3))
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a))   # not 1..9: ignored
    frame = np.zeros((192, 512, 3), np.uint8)
    frame[5, 7] = (200, 10, 30)
    d.push(frame)
    assert pressed == [2]                                                    # key 3 is index 2
    assert tuple(d.window.get_at((7, 5)))[:3] == (200, 10, 30)               # row 5, column 7: not transposed
    assert tuple(d.window.get_at((5, 7)))[:3] == (0, 0, 0)
    d.set_brightness(0.15)
    assert d.brightness == 0.15
    d.close()
    assert not pygame.display.get_init()


def test_make_display_fake_and_unknown():
    assert isinstance(make_display(Config(backend="fake")), FakeDisplay)
    for backend in ("hologram", "matrix"):  # the matrix backend was removed (daemon Task 17)
        with pytest.raises(ValueError):
            make_display(Config(backend=backend))


def test_make_display_accepts_any_config_object():
    cfg = SimpleNamespace(width=64, height=64, backend="fake", sdl_scale=8,
                          ddp_host="127.0.0.1", ddp_port=4048)
    assert isinstance(make_display(cfg), FakeDisplay)
