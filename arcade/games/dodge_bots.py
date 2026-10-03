"""Dodge's bots (spec 9.3). A bot's x is in zone coordinates, 0 to 1 across the mat; the block is at
(x - ZONE_LO) / (ZONE_HI - ZONE_LO) of its travel. `won` is the run survived.

good watches the rocks (debug_state's rocks, (x, y, w) of every solid part, its threat_xy being the one over the block) and, when one is about to fall
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
    NEAR = 10.0                 # a 6 px rock's centre this close threatens; a wider one by its extra half-width more
    EDGE = 9.0                  # px from a rock's edge the block's centre keeps to call it safe (a 6 px rock: 12,
    EDGE_TIGHT = 5.0            # as before the sizes); when nothing is that clear, this much (a gate's gap)
    ABOVE = 44.0
    GRID = 0.02                 # of the mat, 2.4 px: a gate's gap (16 px, EDGE_TIGHT clear over 6) still holds a point

    def __init__(self):
        self.x = 0.5

    def _centre(self, x: float) -> float:
        """The wall x of the block's centre when the body stands at zone x."""
        share = min(1.0, max(0.0, (x - ZONE_LO) / (ZONE_HI - ZONE_LO)))
        return PLAYER_W / 2 + share * (self.WALL_W - PLAYER_W)

    def _threatened(self, rocks) -> bool:
        centre = self._centre(self.x)
        return any(abs(rx - centre) <= self.NEAR + max(0.0, rw - 6) / 2 and ry < self.ABOVE for rx, ry, rw in rocks)

    def _safe(self, x: float, rocks, edge: float | None = None) -> bool:
        centre, edge = self._centre(x), self.EDGE if edge is None else edge
        return all(abs(rx - centre) > rw / 2 + edge for rx, _, rw in rocks)

    def _step(self, rocks) -> float:
        """The zone x nearest the current target where no rock is over the block, EDGE clear, else EDGE_TIGHT
        clear (the way through a gate), else where it is."""
        n = round(1.0 / self.GRID)
        for edge in (self.EDGE, self.EDGE_TIGHT):
            options = sorted((abs(k * self.GRID - self.x), k * self.GRID) for k in range(n + 1)
                             if self._safe(k * self.GRID, rocks, edge))
            if options:
                return options[0][1]
        return self.x

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
