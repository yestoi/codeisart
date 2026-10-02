"""Copy Me's bots (spec 9.3). A bot stands at the mat's centre and strikes the round's target (debug_state's target)
through show and play, standing before and between (so each round's pose is struck fresh). `won` is a game over with
WIN_MATCHES rounds matched.

good copies every round; lazy is slower and sloppier, copies round 1, stands through round 2, and in round 3 copies
only the easier of its two silly poses (LADDER[2][0]), so it wins on about half the draws."""
from __future__ import annotations

from arcade.bots import Move
from arcade.games.copyme import LADDER, WIN_MATCHES


def won(state: dict) -> bool:
    """The game is over with WIN_MATCHES or more rounds matched."""
    return state.get("phase") == "over" and (state.get("matches") or 0) >= WIN_MATCHES


class Good:
    """Reacts in 6 ticks, with a little noise; strikes the target in show and play, stands otherwise."""

    reaction_ticks, noise = 6, 0.01

    def copies(self, state: dict) -> bool:
        return True

    def __call__(self, state: dict, t: float) -> Move:
        target = state.get("target")
        if state.get("phase") in ("show", "play") and target is not None and self.copies(state):
            return Move(x=0.5, pose=target)
        return Move(x=0.5)


class Lazy(Good):
    """Slow (14 ticks) and sloppy (0.03): copies round 1, stands in round 2, copies round 3 only on LADDER[2][0]."""

    reaction_ticks, noise = 14, 0.03

    def copies(self, state: dict) -> bool:
        k = state.get("round")
        return k == 1 or (k == 3 and state.get("target") == LADDER[2][0])


BOTS = {"good": Good, "lazy": Lazy}
