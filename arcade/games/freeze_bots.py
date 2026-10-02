"""Freeze's bots (spec 9.3). A bot's x is in zone coordinates; it sees debug_state() late (reaction_ticks).

good dances on green (sways x 0.1 and swings both wrists 0.2 to 0.8 every 0.3 s) and, on red, holds x and drops
its hands; lazy is slower and sloppier, and its one mistake hangs on the rng: when the first green lasted over
LAZY_GREEN seconds (it counts that green's ticks: about half the seeds) it keeps dancing 1 s into the first red.
`won` is a solo run survived with at least WIN_SCORE reds counted."""
from __future__ import annotations

import math

from arcade.bots import Move
from arcade.games.freeze import WIN_SCORE
from arcade.sources.actors import TICK

LAZY_GREEN = 4.5                # seconds: lazy slips on the first red when the first green lasted over this
SWAY = 0.1                      # of the mat, each side
SWAY_SECONDS = 1.2
SWING = (0.2, 0.8)              # the wrists' v, alternating
SWING_SECONDS = 0.3
SLIP_SECONDS = 1.0              # how long lazy goes on dancing into the red


def won(state: dict) -> bool:
    """The run is over, the player is in, and at least WIN_SCORE reds counted."""
    return state.get("phase") == "over" and state.get("out") is False and state.get("score", 0) >= WIN_SCORE


def dancing(t: float) -> Move:
    return Move(x=0.5 + SWAY * math.sin(2 * math.pi * t / SWAY_SECONDS), hand="both",
                wrist_y=SWING[int(t / SWING_SECONDS) % 2])


class Good:
    """Reacts in 6 ticks with a little noise: dances on green, holds on red."""

    reaction_ticks, noise = 6, 0.005

    def __init__(self):
        self.green_ticks = 0           # the first green's length in ticks seen
        self.reds = 0                  # reds seen begun
        self.red_ticks = 0             # ticks seen of the current red
        self._light = "none"

    def _see(self, light: str) -> None:
        if light == "red" and self._light != "red":
            self.reds += 1
            self.red_ticks = 0
        if light == "green" and self.reds == 0:
            self.green_ticks += 1
        if light == "red":
            self.red_ticks += 1
        self._light = light

    def _slip(self) -> bool:
        return False

    def __call__(self, state: dict, t: float) -> Move:
        light = state.get("light", "none")
        self._see(light)
        if light == "green" or (light == "red" and self._slip()):
            return dancing(t)
        return Move(x=0.5)


class Lazy(Good):
    """Slower (10 ticks) and sloppier (0.01); dances 1 s into the first red when the first green was long."""

    reaction_ticks, noise = 10, 0.01

    def _slip(self) -> bool:
        return self.reds == 1 and self.green_ticks * TICK > LAZY_GREEN and self.red_ticks * TICK <= SLIP_SECONDS


BOTS = {"good": Good, "lazy": Lazy}
