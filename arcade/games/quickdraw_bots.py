"""Quick Draw's bots (spec 9.3): the human is in seat a (the left bar), so a bot stands at zone x 0.3.

wrist_y is the wrist in the reach box, 1.0 hip height (a hand down) and 0.1 a hand drawn (the bar at its top). A bot
sees debug_state() reaction_ticks late, so it draws when it sees signal == "draw", and the lazy one also draws early
on some rounds, judging by the wait_left it saw."""
from __future__ import annotations

from arcade.bots import Move

HUMAN_X = 0.3
DOWN, DRAWN = 1.0, 0.1


def won(state: dict) -> bool:
    """The match is over and player 1's rounds are above the other seat's."""
    return state.get("phase") == "over" and state.get("score", 0) > state.get("right", 0)


class Good:
    """Reacts in 6 ticks (0.2 s), a little noise: hand down until it sees DRAW, then up."""

    reaction_ticks, noise = 6, 0.02

    def _early(self, state: dict) -> bool:
        return False

    def __call__(self, state: dict, t: float) -> Move:
        drawing = state.get("phase") == "play" and (state.get("signal") == "draw" or self._early(state))
        return Move(x=HUMAN_X, wrist_y=DRAWN if drawing else DOWN)


class Lazy(Good):
    """Slow (40 ticks, 1.33 s: with the bar's lag it crosses near 1.45 s, late in the CPU's 0.9 to 1.6 s window, so it
    wins a round now and then and loses most) and sloppy, and on every fourth round (2, 6, ...) it draws early: once
    the wait_left it saw is under EARLY_LEFT, which, seen 1.33 s late, puts its hand up before DRAW (TOO SOON)."""

    reaction_ticks, noise = 40, 0.05
    EARLY_LEFT = 1.6

    def _early(self, state: dict) -> bool:
        left = state.get("wait_left")
        return state.get("round", 0) % 4 == 2 and left is not None and left < self.EARLY_LEFT


BOTS = {"good": Good, "lazy": Lazy}
