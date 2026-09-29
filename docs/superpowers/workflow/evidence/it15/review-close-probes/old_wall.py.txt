"""The governed wall (Q50): every frame the show sends passes the flash governor on its way to the display.

`GovernedDisplay` wraps the display the loop opened, at birth: `push` runs `FlashGovernor.apply` and sends what
it returns, `repush` sends the last governed frame again (after a failed push, so the wall shows what the
governor counted), and `close` darkens the wall with governed black, sending the counted frame first when the
last send did not complete (it13 T-wall). `_send` is the only way to the display. No software brightness: the
device holds the level (daemon plan amendment for Task 5).

it14 T-wall: with a clock, a failed send starts a quiet hold (C51, Q66): nothing for HOLD_S, the counted frame,
HOLD_S, the counted frame, HOLD_S, then the governor starts again from the counted frame and new frames go.
from_dark (C52) primes the governor with black at birth, unsent, so the first frame is counted against the dark
wall.
"""
from __future__ import annotations

import logging
from typing import Callable

import numpy as np

from arcade.flash import FlashGovernor
from show.display import Display

log = logging.getLogger(__name__)

GAMMA_MIN, GAMMA_MAX = 1.0, 2.2   # the card applies gamma .. the card sends bytes as they are (as show.config checks)
HOLD_S = 1.0         # after a failed send, the wall is still this long before each counted send (C51, Q66)
SETTLE_SENDS = 2     # the counted frame is sent this many times, HOLD_S apart, then new frames HOLD_S later


class GovernedDisplay:
    def __init__(self, display: Display, height: int, width: int, fps: int = 30, gamma: float = 2.2, *,
                 from_dark: bool = False, clock: Callable[[], float] | None = None):
        # A Config built in code skips load_config's check; the governor's own checks follow. The display is
        # never closed here, whatever raises: it is the caller's.
        if isinstance(gamma, bool) or not isinstance(gamma, (int, float)) or not GAMMA_MIN <= gamma <= GAMMA_MAX:
            raise ValueError(f"gamma must be {GAMMA_MIN} (the card applies gamma) to {GAMMA_MAX} (bytes as they "
                             f"are), got {gamma!r}")
        self.governor = FlashGovernor(height, width, gamma, fps=fps)
        self._made = (height, width, gamma, fps)  # the governor's arguments, for its re-init at a hold's end
        self.display = display
        self.governed = 0                       # frames governed and pushed
        self._last: np.ndarray | None = None    # the last governed frame, a copy
        self.unsent = False                     # a send began and the display's push has not returned (it raised)
        self.failed = 0                         # sends that raised an Exception, all told
        self._clock = clock                     # seconds, for the hold; None: no hold
        self.holding = False                    # from a failed send (clock given) until push governs again
        self._since = 0.0                       # the hold's failed send, or its last counted send
        self._settled = 0                       # the counted sends of this hold
        if from_dark:                           # C52: the dark wall is the governor's first frame, not sent
            self.governor.apply(np.zeros(self.governor.shape, np.uint8))

    @property
    def last(self) -> np.ndarray | None:
        """The last governed frame, a read-only view; None before any push."""
        if self._last is None:
            return None
        view = self._last.view()
        view.flags.writeable = False
        return view

    def push(self, frame: np.ndarray) -> np.ndarray | None:
        """Govern the frame, then send it; returns what was sent. A frame of another shape raises, unsent.

        After a send that raised (with a clock), the wall holds (C51, Q66): the frame is dropped, not governed,
        and nothing is sent (None) until HOLD_S after the failed send; then the counted frame goes again (a copy
        returned), SETTLE_SENDS times, HOLD_S apart; HOLD_S after the last, the governor starts again from the
        counted frame (B1) and this push governs and sends its own. A send that raises starts the hold again from
        that time; the exception goes on to the caller."""
        failed = self.failed
        try:
            if self.holding:
                now = self._clock()
                if now < self._since + HOLD_S:
                    return None
                if self._settled < SETTLE_SENDS:
                    self._since = now
                    self.repush()
                    self._settled += 1
                    return self._last.copy()
                self._end_hold()
            return self._govern(frame)
        except Exception:
            if self.failed > failed and self._clock is not None:      # a send raised, not a frame refused
                self.holding, self._since, self._settled = True, self._clock(), 0
            raise

    def _end_hold(self) -> None:
        """The governor made again in place (the wrapper and spies on it kept, held_ticks carried), then the
        counted frame applied once, not sent: a torn send leaves the wall's transitions unlike the governor's,
        so with them unknown again a change either way counts (B1)."""
        height, width, gamma, fps = self._made
        held = self.governor.held_ticks
        self.governor.__init__(height, width, gamma, fps=fps)
        self.governor.held_ticks = held
        self.governor.apply(self._last)
        self.holding = False

    def _govern(self, frame: np.ndarray) -> np.ndarray:
        """The one governed path (push's and close's): apply, send, count."""
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
        try:
            if self.unsent:
                try:
                    self.repush()               # what the governor counted, before black follows it
                except Exception:
                    log.exception("closing: resending the last governed frame failed; black still goes")
            for _ in range(2):
                self._govern(black)             # not held: the governed path, never push's hold
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
