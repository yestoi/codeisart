"""Jump's bots (spec 9.3). Both stand (x 0.5) in ready and, in play, make one arc of ARC_TICKS ticks per window,
DELAY_TICKS after they see it open: lift = peak * 4u(1 - u), as Person.jump does. Good's peak reaches BELL_CM[1] + 4 cm
(about 0.16 of the frame, the most that stays in the zone at Person's height 0.6); lazy's reaches the middle of BELL_CM,
so it wins when the rng's bell is low. `won` is the bell rung by the end."""
from __future__ import annotations

from arcade.bots import Move
from arcade.games.jump import BELL_CM, TORSO_CM
from arcade.sources.actors import Person

TORSO = Person().body_at(0.0, 1).torso          # Person's torso in frame heights: a lift of x frame heights is x / TORSO torsos
ARC_TICKS = 18                                  # 0.6 s, as Person.jump
DELAY_TICKS = 5


def lift_for(cm: float) -> float:
    """The lift (share of the frame height) that raises the nose by cm."""
    return cm / TORSO_CM * TORSO


def won(state: dict) -> bool:
    return state.get("phase") == "over" and bool(state.get("rang"))


class Good:
    reaction_ticks, noise = 4, 0.01
    peak = lift_for(BELL_CM[1] + 4.0)

    def __init__(self):
        self.n = 0                              # ticks since the bot saw play, 0 outside it

    def __call__(self, state: dict, t: float) -> Move:
        self.n = self.n + 1 if state.get("phase") == "play" else 0
        u = (self.n - DELAY_TICKS) / ARC_TICKS
        lift = self.peak * 4 * u * (1 - u) if 0.0 < u < 1.0 else 0.0
        return Move(x=0.5, lift=lift)


class Lazy(Good):
    reaction_ticks, noise = 10, 0.03
    peak = lift_for(sum(BELL_CM) / 2)


BOTS = {"good": Good, "lazy": Lazy}
