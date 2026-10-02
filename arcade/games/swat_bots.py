"""Swat's bots (spec 9.3). A bot's x is in zone coordinates, 0 to 1 across the mat; wrist_y is the wrist in the reach
box. The right hand's reach is +ARM_PX / 4 px (its u is 0.75), so the blade's x is the body's place (the zone mapped
onto -12 .. 139) plus 12. `won` is the round over with the goal reached.

good steps its body so the blade's x meets the nearest fruit's (debug_state's target_xy, led by the fruit's drift)
and swipes the wrist 0.15 either side of the fruit's height every 3 ticks; with a bomb within 8 px of the blade it
drops its hand (a hanging hand cuts nothing). lazy is slower and sloppier, swipes every 8 ticks and ignores bombs."""
from __future__ import annotations

from arcade.bots import Move
from arcade.games.swat import ARM_PX, BLADE_BOTTOM, BLADE_TOP, V_BOTTOM, V_TOP, ZONE_HI, ZONE_LO


def won(state: dict) -> bool:
    """The round is over and the goal was reached."""
    from arcade.games.swat import GOAL

    return state.get("phase") == "over" and (state.get("score") or 0) >= GOAL


class Good:
    """Reacts in 5 ticks, with a little noise."""

    reaction_ticks, noise = 5, 0.02
    WALL_W = 128
    SWIPE_EVERY = 3
    HALF = 0.15              # the swipe's half stroke in v, either side of the fruit's height
    AVOID_PX = 8.0           # a bomb this near the blade: hand down
    LEAD_TICKS = 6           # ticks the fruit's drift is led by

    def __init__(self):
        self.k = 0
        self.last: tuple[float, float] | None = None
        self.x = 0.5

    def _zone_for(self, blade_x: float) -> float:
        """The zone x that puts the right hand's blade at wall x blade_x."""
        span = self.WALL_W - 1 + ARM_PX / 2
        share = (blade_x - ARM_PX / 4 + ARM_PX / 4) / span
        return ZONE_LO + min(1.0, max(0.0, share)) * (ZONE_HI - ZONE_LO)

    @staticmethod
    def _v_for(row: float) -> float:
        return V_TOP + (row - BLADE_TOP) / (BLADE_BOTTOM - BLADE_TOP) * (V_BOTTOM - V_TOP)

    def _lead(self, target) -> tuple[float, float]:
        """target (x, y) led by its drift since the last tick the same fruit was seen (a jump is another fruit)."""
        x, y = target
        if self.last is not None and abs(x - self.last[0]) < 4 and abs(y - self.last[1]) < 4:
            dx, dy = x - self.last[0], y - self.last[1]
            x, y = x + dx * self.LEAD_TICKS, y + dy * self.LEAD_TICKS
        return x, y

    def __call__(self, state: dict, t: float) -> Move:
        self.k += 1
        blade, target, bomb = state.get("blade_xy"), state.get("target_xy"), state.get("bomb_xy")
        if state.get("phase") != "play" or target is None:
            self.last = None
            return Move(x=self.x, wrist_y=0.5 if state.get("phase") == "play" else None)
        led = self._lead(target)
        self.last = target
        self.x = self._zone_for(led[0])
        if blade is not None and bomb is not None and ((bomb[0] - blade[0]) ** 2 + (bomb[1] - blade[1]) ** 2) ** 0.5 \
                < self.AVOID_PX:
            return Move(x=self.x)
        mid = self._v_for(led[1])
        up = (self.k // self.SWIPE_EVERY) % 2 == 0
        return Move(x=self.x, wrist_y=min(0.8, max(0.1, mid + (-self.HALF if up else self.HALF))))


class Lazy(Good):
    """Slow (12 ticks) and sloppy (0.05), swipes every 8 ticks and ignores bombs."""

    reaction_ticks, noise = 12, 0.05
    SWIPE_EVERY = 8
    HALF = 0.07              # short strokes
    LEAD_TICKS = 0           # no lead on the fruit's drift
    AVOID_PX = 0.0


BOTS = {"good": Good, "lazy": Lazy}
