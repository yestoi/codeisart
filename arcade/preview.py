from __future__ import annotations

import numpy as np

from arcade.look import check_settings, dim, is_real, render
from show.display import Display


class PreviewDisplay:
    """Renders a wall frame in a look mode before handing it to a real (usually SDL) display.

    Brightness is modelled here: set_brightness forwards the level to the inner display (which stores it; the
    SDL window never dims) and scales the rendered preview so the monitor shows that fraction of the light.
    The wall frame itself is never scaled (Global Constraints: pixels pushed to hardware are never scaled).
    The settings are checked here, at construction, with look.check_settings (ValueError), not on the first push;
    a level that is not a number raises ValueError in set_brightness and is neither kept nor forwarded.
    """

    def __init__(self, inner: Display, mode: str, scale: int, gamma: float, metres: float = 5.0):
        scale = check_settings(mode, scale, gamma, metres)
        self.inner, self.mode, self.scale, self.gamma, self.metres = inner, mode, scale, gamma, metres
        self.level = 1.0

    def push(self, frame: np.ndarray) -> None:
        image = render(frame, self.mode, self.scale, self.gamma, self.metres)
        self.inner.push(dim(image, self.level))

    def set_brightness(self, level: float) -> None:
        if not is_real(level):
            raise ValueError(f"brightness must be a number, got {level!r}")
        self.level = level
        self.inner.set_brightness(level)

    def close(self) -> None:
        self.inner.close()
