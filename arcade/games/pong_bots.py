"""Pong's bots (spec 9.3): the human is on the left, the CPU on the right, so a bot stands at zone x 0.3.

The paddle follows the cursor's reach-box height, so aiming the paddle at the ball's y is wrist_y = y / (h - 1)."""
from __future__ import annotations

from arcade.bots import Move

HUMAN_X = 0.3


def won(state: dict) -> bool:
    """The round is over and the human side's points are above the CPU's."""
    if state.get("phase") != "over":
        return False
    cpu = state.get("cpu")
    human, other = ("right", "left") if cpu == "left" else ("left", "right")
    return state[human] > state[other]


def _fold(y: float, top: float, bottom: float) -> float:
    """y reflected back into [top, bottom], the way the ball bounces off the walls."""
    span = bottom - top
    y = (y - top) % (2 * span)
    return top + (y if y <= span else 2 * span - y)


class Good:
    """Reacts in 3 ticks, with a little noise. While the ball comes towards the human (its x fell since the last
    look) it puts the paddle's centre where the ball will cross the paddle, off the walls; else it centres."""

    reaction_ticks, noise = 3, 0.02
    WALL_W, WALL_H = 128, 64
    PADDLE_X = 2.0

    def __init__(self):
        self._last: tuple[float, float] | None = None

    def _aim(self, state: dict) -> float | None:
        """The ball's y (px) where it reaches the paddle, or None when it is not coming or not in play."""
        if "ball_xy" not in state:
            return None
        bx, by = state["ball_xy"]
        last, self._last = self._last, (bx, by)
        if state.get("phase") != "play" or last is None or bx >= last[0] or not self._wanted(bx):
            return None
        slope = (by - last[1]) / (bx - last[0])            # px of y per px of x, left-going
        return _fold(by + slope * (self.PADDLE_X - bx), 1.0, self.WALL_H - 1.0)

    def _wanted(self, bx: float) -> bool:
        return True

    def __call__(self, state: dict, t: float) -> Move:
        y = self._aim(state)
        return Move(x=HUMAN_X, wrist_y=0.5 if y is None else y / (self.WALL_H - 1))


class Lazy(Good):
    """Slow (8 ticks) and sloppy (0.08), and only moves while the ball is in the human's half."""

    reaction_ticks, noise = 8, 0.08

    def _wanted(self, bx: float) -> bool:
        return bx < self.WALL_W / 2

    def _aim(self, state: dict) -> float | None:
        """Chases the ball's y as it is, with no prediction, and only while it is in the human's half."""
        if "ball_xy" not in state or state.get("phase") != "play" or not self._wanted(state["ball_xy"][0]):
            return None
        return state["ball_xy"][1]


BOTS = {"good": Good, "lazy": Lazy}
