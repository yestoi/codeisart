import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # before anything imports pygame
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from show.config import Config
from show.font import Font

# Column bytes for a capital A in the glcdfont layout (bit 0 = top row).
A_COLUMNS = bytes([0x7E, 0x11, 0x11, 0x11, 0x7E])


@pytest.fixture
def font() -> Font:
    data = bytearray(256 * 5)
    data[65 * 5 : 66 * 5] = A_COLUMNS
    return Font(bytes(data))


@pytest.fixture
def fast_cfg() -> Config:
    return Config(typewriter_cps=1_000_000, dwell=0.1, error_hold=0.1, attract_lps=1000.0)
