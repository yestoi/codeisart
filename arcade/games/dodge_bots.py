"""Dodge's bots (spec 9.3). A bot's x is in zone coordinates, 0 to 1 across the mat; the block is at
(x - ZONE_LO) / (ZONE_HI - ZONE_LO) of its travel. `won` is the run survived.

good watches the rocks (debug_state's rocks, its threat_xy being the one over the block) and, when one is about to fall
on the place it stands, walks to the nearest place no rock is over; lazy is slower and sloppier and
only reacts to a rock that is well on its way down."""
from __future__ import annotations

from arcade.bots import Move
from arcade.games.dodge import PLAYER_W, ZONE_HI, ZONE_LO


def won(state: dict) -> bool:
    """The run is over and it was survived."""
    return state.get("phase") == "over" and bool(state.get("survived"))


class Good:
    """Reacts in 5 ticks, with a little noise. A rock above row ABOVE within NEAR px of where it stands (its own
    target, not the late block) sends it to the nearest zone x with no rock within CLEAR px of the block's centre."""

    reaction_ticks, noise = 5, 0.02
    WALL_W = 128
    NEAR = 10.0
    CLEAR = 12.0
    ABOVE = 44.0
    GRID = 0.02

    def __init__(self):
        self.x = 0.5

    def _centre(self, x: float) -> float:
        """The wall x of the block's centre when the body stands at zone x."""
        share = min(1.0, max(0.0, (x - ZONE_LO) / (ZONE_HI - ZONE_LO)))
        return PLAYER_W / 2 + share * (self.WALL_W - PLAYER_W)

    def _threatened(self, rocks) -> bool:
        centre = self._centre(self.x)
        return any(abs(rx - centre) <= self.NEAR and ry < self.ABOVE for rx, ry in rocks)

    def _safe(self, x: float, rocks) -> bool:
        centre = self._centre(x)
        return all(abs(rx - centre) > self.CLEAR for rx, _ in rocks)

    def _step(self, rocks) -> float:
        """The zone x nearest the current target where no rock is over the block, else where it is."""
        n = round(1.0 / self.GRID)
        options = sorted((abs(k * self.GRID - self.x), k * self.GRID) for k in range(n + 1)
                         if self._safe(k * self.GRID, rocks))
        return options[0][1] if options else self.x

    def __call__(self, state: dict, t: float) -> Move:
        rocks = state.get("rocks", ())
        if state.get("phase") == "play" and self._threatened(rocks):
            self.x = self._step(rocks)
        return Move(x=self.x)


class Lazy(Good):
    """Slow (12 ticks) and sloppy (0.05), and only reacts to a rock above row 40."""

    reaction_ticks, noise = 12, 0.05
    ABOVE = 40.0


BOTS = {"good": Good, "lazy": Lazy}
