import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from show.font import Font

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def font5x7() -> Font:
    return Font.load(ROOT / "fonts" / "5x7.bin")


@pytest.fixture(params=[(128, 32), (64, 64)], ids=["128x32", "64x64"])
def size(request) -> tuple[int, int]:
    return request.param
