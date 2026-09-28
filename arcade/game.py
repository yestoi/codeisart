"""The game interface (spec 7.1): GameInfo, the Game protocol, the runner's reserved state keys and icons."""
from __future__ import annotations

import math
import random
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, ClassVar, Protocol

import numpy as np

from arcade.canvas import Canvas
from arcade.look import is_real
from arcade.scores import GameScores
from arcade.sensed import Sensed

INPUTS = frozenset({"pose", "blobs", "motion", "audio"})
KINDS = ("control", "toy", "score")               # selects the feel budget set (spec 9.3)
LAYOUTS = frozenset({"128x32", "64x64"})
ICON_SIZE = 16
RUNNER_KEYS = frozenset({"game", "t", "idle", "attract", "hidden", "crashes", "glitch", "flash_held_ticks", "player",
                         "present"})
FX_PREFIX = "fx_"                                 # the effects' keys in state(); runner keys, too
NAME = re.compile(r"[a-z][a-z0-9_]*")             # a registry key is the game's module name
LAYOUT = re.compile(r"[1-9][0-9]*x[1-9][0-9]*")


def reserved(key: str) -> bool:
    """True for a debug_state key a game must not use: the runner's own (it wins in state()) and fx_*."""
    return key in RUNNER_KEYS or key.startswith(FX_PREFIX)


def _text(name: str, value) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"GameInfo.{name} must be a non-empty string, got {value!r}")


@dataclass(frozen=True, eq=False)
class GameInfo:
    """What the lobby, the runner and the tests know about a game before launching it (spec 7.1).

    Validated when built: name a lowercase identifier (the module name), title and verb non-empty, icon
    16x16 bool (kept as a read-only copy), needs a subset of INPUTS, layouts a non-empty set of "WxH" names,
    players 1 or 2, exit_gesture a bool, kind one of KINDS, abandon_seconds None or a finite number over 0.
    A bad value raises ValueError, so a broken game module is skipped at discovery, not launched.
    """

    name: str
    title: str
    verb: str
    icon: np.ndarray
    needs: frozenset[str]
    layouts: frozenset[str] = LAYOUTS
    players: int = 1
    exit_gesture: bool = True
    kind: str = "control"
    abandon_seconds: float | None = None

    def __post_init__(self):
        if not isinstance(self.name, str) or not NAME.fullmatch(self.name):
            raise ValueError(f"GameInfo.name must be a lowercase identifier, got {self.name!r}")
        _text("title", self.title)
        _text("verb", self.verb)
        icon = np.array(self.icon)
        if icon.shape != (ICON_SIZE, ICON_SIZE) or icon.dtype != bool:
            raise ValueError(f"GameInfo.icon must be a {ICON_SIZE}x{ICON_SIZE} bool array, got {icon.shape} "
                             f"{icon.dtype}")
        icon.flags.writeable = False
        object.__setattr__(self, "icon", icon)
        for name in ("needs", "layouts"):
            value = getattr(self, name)
            if isinstance(value, str) or not isinstance(value, (set, frozenset, tuple, list)):
                raise ValueError(f"GameInfo.{name} must be a set of strings, got {value!r}")
            object.__setattr__(self, name, frozenset(value))
        if not self.needs <= INPUTS:
            raise ValueError(f"GameInfo.needs must be a subset of {sorted(INPUTS)}, got "
                             f"{sorted(map(str, self.needs))}")
        if not self.layouts or not all(isinstance(v, str) and LAYOUT.fullmatch(v) for v in self.layouts):
            raise ValueError(f"GameInfo.layouts must be non-empty WxH names, got {sorted(map(str, self.layouts))}")
        if isinstance(self.players, bool) or not isinstance(self.players, int) or self.players not in (1, 2):
            raise ValueError(f"GameInfo.players must be 1 or 2, got {self.players!r}")
        if not isinstance(self.exit_gesture, bool):
            raise ValueError(f"GameInfo.exit_gesture must be a bool, got {self.exit_gesture!r}")
        if self.kind not in KINDS:
            raise ValueError(f"GameInfo.kind must be one of {KINDS}, got {self.kind!r}")
        a = self.abandon_seconds
        if a is not None and (not is_real(a) or not 0.0 < a < math.inf):
            raise ValueError(f"GameInfo.abandon_seconds must be None or a finite number over 0, got {a!r}")


class Game(Protocol):
    """A game (spec 7.1). A fresh instance per launch; state across plays only through scores.

    The runner sets scores (the per-game view Scores.for_game(name, layout)) before reset(). draw() must
    work right after reset(). debug_state() is a small flat dict: a phase key with values from PHASES, score
    when there is one, active on any tick with meaningful input, *_xy for wall coordinates of a visible
    entity, and never a reserved() key. fx is the launch's effects object (arcade/juice.py, core Task 8).
    A game may subclass Game to inherit PHASES, SCENARIOS and CAPTION_KEYS defaults.
    """

    info: ClassVar[GameInfo]
    scores: GameScores
    SCENARIOS: ClassVar[Mapping[str, Callable]] = MappingProxyType({})     # shared by every subclass: read-only
    CAPTION_KEYS: ClassVar[tuple[str, ...]] = ()
    PHASES: ClassVar[tuple[str, ...]] = ("play",)

    def reset(self, size: tuple[int, int], rng: random.Random, fx: Any) -> None: ...
    def update(self, sensed: Sensed, dt: float) -> None: ...
    def draw(self, canvas: Canvas) -> None: ...
    def done(self) -> bool: ...
    def debug_state(self) -> dict: ...


def icon_from_rows(rows: list[str]) -> np.ndarray:
    """A read-only 16x16 bool icon from 16 rows of 16 characters, "#" on and "." off (2 px strokes)."""
    if len(rows) != ICON_SIZE or any(not isinstance(r, str) or len(r) != ICON_SIZE for r in rows):
        raise ValueError(f"an icon is {ICON_SIZE} rows of {ICON_SIZE} characters")
    bad = {ch for row in rows for ch in row} - {"#", "."}
    if bad:
        raise ValueError(f"icon rows use only '#' and '.', got {sorted(bad)}")
    icon = np.array([[ch == "#" for ch in row] for row in rows], dtype=bool)
    icon.flags.writeable = False
    return icon
