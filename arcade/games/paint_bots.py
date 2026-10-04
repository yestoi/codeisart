"""Paint's bots (spec 9.3). Good holds a green light and sweeps it over the paper: the body walks zone x 0.05 to 0.72
(the light at the wrist stays inside the zone) while the wrist zigzags the reach box 0.15 to 1.0, the two periods
incommensurate so the lines do not retrace; by the gallery 30 percent or more of the paper shows (measured
2026-10-03: 0.30 to 0.31 with the 2 px brush, 0.36 to 0.37 with the 3 px). Lazy has no light: its wrist paints in the
seat's colour over a slow drift in the middle, and what shows at the gallery hangs on the rng's brush (0.20 to 0.22
with 2 px, 0.22 to 0.23 with 3 px, against WIN_PAINTED 0.22). `won` is WIN_PAINTED of the paper showing at the
gallery; Nobody paints nothing."""
from __future__ import annotations

from arcade.bots import Move
from arcade.games.paint import WIN_PAINTED

X_TICKS, Y_TICKS = 120, 29            # Good: one walk across in 4 s, one wrist zigzag in about 1 s (29 is prime)
LAZY_X_TICKS, LAZY_Y_TICKS = 240, 90  # Lazy: a slow drift, 8 s across and 3 s up and down


def _tri(u: float) -> float:
    """A triangle wave over u in [0, 1): 0 to 1 and back."""
    return 2 * u if u < 0.5 else 2 * (1 - u)


def won(state: dict) -> bool:
    return state.get("phase") == "gallery" and float(state.get("painted") or 0.0) >= WIN_PAINTED


class Good:
    reaction_ticks, noise = 4, 0.01

    def __init__(self):
        self.n = 0

    def __call__(self, state: dict, t: float) -> Move:
        self.n += 1
        x = 0.05 + 0.67 * _tri((self.n % X_TICKS) / X_TICKS)
        wrist = 0.15 + 0.85 * _tri((self.n % Y_TICKS) / Y_TICKS)
        return Move(x=x, wrist_y=wrist, light=(0, 255, 0))


class Lazy:
    reaction_ticks, noise = 10, 0.03

    def __init__(self):
        self.n = 0

    def __call__(self, state: dict, t: float) -> Move:
        self.n += 1
        x = 0.33 + 0.34 * _tri((self.n % LAZY_X_TICKS) / LAZY_X_TICKS)
        wrist = 0.28 + 0.37 * _tri((self.n % LAZY_Y_TICKS) / LAZY_Y_TICKS)
        return Move(x=x, wrist_y=wrist)


BOTS = {"good": Good, "lazy": Lazy}
