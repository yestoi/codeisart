"""Pong's bots (spec 9.3): the human is on the left, the CPU on the right, so a bot stands at zone x 0.3.

The paddle follows the body's Depth (arcade/input.py), nearer up: its centre is paddle_h / 2 + (1 - near) *
(h - paddle_h), so a bot that wants the paddle's centre at y stands at near = 1 - (y - paddle_h / 2) / (h - paddle_h).
bots.play moves near at a body's pace (BODY_RANGE_SECONDS for the whole range)."""
from __future__ import annotations

from arcade.bots import Move
from arcade.games.pong import NEAR_IS_UP, PADDLE_SHARE, PADDLE_W

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
    PADDLE_X = float(PADDLE_W)
    AIM_OFFSET = 0.6        # of the paddle's half: a return about 30 degrees off flat, away from the CPU

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

    def _near(self, y: float | None) -> float:
        """The Depth value that puts the paddle's centre at y (0.5, the middle, for None), clamped to 0..1."""
        if y is None:
            return 0.5
        paddle_h = round(self.WALL_H * PADDLE_SHARE)
        up = 1.0 - (y - paddle_h / 2) / (self.WALL_H - paddle_h)
        return min(1.0, max(0.0, up if NEAR_IS_UP else 1.0 - up))

    def _angle(self, y: float | None, state: dict) -> float | None:
        """Where to put the paddle's centre so the ball meets it AIM_OFFSET of its half off centre, on the side
        that sends the ball away from the CPU's paddle (a flat return is one the CPU always reaches)."""
        if y is None or not self.AIM_OFFSET:
            return y
        cpu = state.get("right_xy", (0.0, self.WALL_H / 2))[1]
        away = -1.0 if cpu >= self.WALL_H / 2 else 1.0              # the ball goes up (-) when the CPU is low
        half = round(self.WALL_H * PADDLE_SHARE) / 2 + 1.0
        return y - away * self.AIM_OFFSET * half

    def __call__(self, state: dict, t: float) -> Move:
        return Move(x=HUMAN_X, near=self._near(self._angle(self._aim(state), state)))


class Lazy(Good):
    """Slow (8 ticks) and sloppy (0.08), and only moves while the ball is in the human's half."""

    reaction_ticks, noise = 8, 0.08
    AIM_OFFSET = 0.0

    def _wanted(self, bx: float) -> bool:
        return bx < self.WALL_W / 2

    def _aim(self, state: dict) -> float | None:
        """Chases the ball's y as it is, with no prediction, and only while it is in the human's half."""
        if "ball_xy" not in state or state.get("phase") != "play" or not self._wanted(state["ball_xy"][0]):
            return None
        return state["ball_xy"][1]


BOTS = {"good": Good, "lazy": Lazy}
