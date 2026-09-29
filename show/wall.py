"""The governed wall (Q50): every frame the show sends passes the flash governor on its way to the display.

`GovernedDisplay` wraps the display the loop opened, at birth: `push` runs `FlashGovernor.apply` and sends what
it returns, `repush` sends the last governed frame again (after a failed push, so the wall shows what the
governor counted), and `close` darkens the wall with governed black, sending the counted frame first when the
last send did not complete (it13 T-wall). `_send` is the only way to the display. No software brightness: the
device holds the level (daemon plan amendment for Task 5).
"""
from __future__ import annotations

import logging

import numpy as np

from arcade.flash import FlashGovernor
from show.display import Display

log = logging.getLogger(__name__)

GAMMA_MIN, GAMMA_MAX = 1.0, 2.2   # the card applies gamma .. the card sends bytes as they are (as show.config checks)


class GovernedDisplay:
    def __init__(self, display: Display, height: int, width: int, fps: int = 30, gamma: float = 2.2):
        # A Config built in code skips load_config's check; the governor's own checks follow. The display is
        # never closed here, whatever raises: it is the caller's.
        if isinstance(gamma, bool) or not isinstance(gamma, (int, float)) or not GAMMA_MIN <= gamma <= GAMMA_MAX:
            raise ValueError(f"gamma must be {GAMMA_MIN} (the card applies gamma) to {GAMMA_MAX} (bytes as they "
                             f"are), got {gamma!r}")
        self.governor = FlashGovernor(height, width, gamma, fps=fps)
        self.display = display
        self.governed = 0                       # frames governed and pushed
        self._last: np.ndarray | None = None    # the last governed frame, a copy
        self.unsent = False                     # a send began and display.push has not returned (it raised)
        self.failed = 0                         # sends that raised an Exception, all told

    @property
    def last(self) -> np.ndarray | None:
        """The last governed frame, a read-only view; None before any push."""
        if self._last is None:
            return None
        view = self._last.view()
        view.flags.writeable = False
        return view

    def push(self, frame: np.ndarray) -> np.ndarray:
        """Govern the frame, then send it; returns what was sent. A frame of another shape raises, unsent."""
        out = self.governor.apply(frame)
        self._last = out.copy()
        self._send(self._last)
        self.governed += 1
        return out

    def repush(self) -> None:
        """Send the last governed frame again, not governed again (nothing yet governed: nothing sent)."""
        if self._last is not None:
            self._send(self._last)

    def set_brightness(self, level: float) -> None:
        self.display.set_brightness(level)

    def close(self) -> None:
        """The counted frame again if the last send did not complete, then two governed black frames, then the
        display closed, whatever the pushes do. A failed repush still lets the black go."""
        black = np.zeros(self.governor.shape, np.uint8)
        push = self.push                       # the governed path; _send stays push's and repush's alone
        try:
            if self.unsent:
                try:
                    self.repush()               # what the governor counted, before black follows it
                except Exception:
                    log.exception("closing: resending the last governed frame failed; black still goes")
            for _ in range(2):
                push(black)
        finally:
            self.display.close()

    def _send(self, frame: np.ndarray) -> None:
        self.unsent = True
        try:
            self.display.push(frame)
        except Exception:
            self.failed += 1
            raise
        self.unsent = False
