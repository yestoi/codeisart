"""Flap's bots (spec 9.3). A sweep is both wrists to 0.1, then to 0.95 (UP_TICKS then DOWN_TICKS of a Move with hand
"both"); one sweep at a time. Both sweep in ready until they see play, and whenever gap_xy is None; nothing in over. In
play they sweep only while the bird falls (bird_vy > 0) and is level with the next gap's y or under it. `won` is the
run survived."""
from __future__ import annotations

from arcade.bots import Move

UP, DOWN = 0.1, 0.95
UP_TICKS = 4
DOWN_TICKS = 4


def won(state: dict) -> bool:
    return state.get("phase") == "over" and bool(state.get("survived"))


class Good:
    reaction_ticks, noise = 5, 0.02

    def __init__(self):
        self.n = 0                      # ticks into the sweep in hand, 0 when none

    def _wants(self, state: dict) -> bool:
        phase = state.get("phase")
        if phase == "ready":
            return True
        if phase != "play":
            return False
        gap = state.get("gap_xy")
        if gap is None:
            return True
        return state.get("bird_vy", 0.0) > 0 and state["bird_xy"][1] >= gap[1]

    def __call__(self, state: dict, t: float) -> Move:
        if self.n == 0 and self._wants(state):
            self.n = 1
        if self.n == 0:
            return Move(hand="both", wrist_y=DOWN)
        wrist = UP if self.n <= UP_TICKS else DOWN
        self.n = 0 if self.n >= UP_TICKS + DOWN_TICKS else self.n + 1
        return Move(hand="both", wrist_y=wrist)


class Lazy(Good):
    reaction_ticks, noise = 10, 0.05


BOTS = {"good": Good, "lazy": Lazy}
