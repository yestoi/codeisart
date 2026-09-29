"""Bots (spec 9.3): scripted players that close the loop through the real runner, to judge a game's difficulty.

A bot reads the game's debug_state() and returns a Move, one body's actor spec for the tick. play() runs it
through run_headless with a callable feed and applies the bot's reaction delay and position noise from the
seed, so bots stay simple and every play repeats. A game's own bots live in arcade/games/<name>_bots.py
(BOTS = {"good": ..., "lazy": ...} and won(state)); this module stays generic.
"""
from __future__ import annotations

import dataclasses
import functools
import importlib
import random
import statistics
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterator, Mapping, Protocol, Sequence

import numpy as np

from arcade.calibration import Calibration
from arcade.config import ArcadeConfig
from arcade.headless import RecordingDisplay, run_headless
from arcade.sensed import MOTION_GRID, Audio, Sensed, place
from arcade.sources.actors import TICK, Person
from show.font import Font

if TYPE_CHECKING:
    from arcade.runner import Runner

MAX_PLAY_SECONDS = 180.0
ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Move:
    """A bot's actor spec for one tick, one body (id 1): hips at zone x (0 the zone's left edge, 1 its right);
    the hand's wrist at reach-box v wrist_y (0 top, 1 hip height), or down with None."""

    x: float = 0.5
    hand: str = "right"
    wrist_y: float | None = None


class Bot(Protocol):
    """reaction_ticks: the bot sees debug_state() that many ticks late; noise: the SD added to x and wrist_y."""

    reaction_ticks: int
    noise: float

    def __call__(self, state: dict, t: float) -> Move | None: ...    # None: nobody in view


class Nobody:
    """No input: nobody in view, ever."""

    reaction_ticks = 0
    noise = 0.0

    def __call__(self, state: dict, t: float) -> Move | None:
        return None


@dataclass(frozen=True)
class Play:
    """One play. ticks and seconds as run; done the game's done() at the end; won the won() of the last
    debug_state(); phases every phase seen; frames the pushed frames when keep_frames, else None."""

    seed: int
    ticks: int
    seconds: float
    done: bool
    won: bool
    state: dict
    phases: frozenset[str]
    frames: list[np.ndarray] | None


def seeds(game_cls, layout: str, n: int) -> list[int]:
    """n seeds for game_cls at layout, from zlib.crc32 (never hash())."""
    name = game_cls.info.name
    return [zlib.crc32(f"{name}:{layout}:{i}".encode()) for i in range(n)]


def for_game(game_cls) -> tuple[Mapping[str, Callable[[], Bot]], Callable[[dict], bool]]:
    """(BOTS, won) from arcade.games.<name>_bots. A missing module raises ModuleNotFoundError naming the file."""
    name = game_cls.info.name
    module_name = f"arcade.games.{name}_bots"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        if e.name != module_name:
            raise
        raise ModuleNotFoundError(f"{name} has no bots: add arcade/games/{name}_bots.py with BOTS = "
                                  f"{{'good': ..., 'lazy': ...}} and won(state)", name=module_name) from e
    return module.BOTS, module.won


@functools.lru_cache(maxsize=None)
def _font(path: Path) -> Font:
    return Font.load(path)


def _clamp01(v: float) -> float:
    return min(1.0, max(0.0, v))


def _sensed(i: int, move: Move | None, before: float | None, cal: Calibration) -> tuple[Sensed, float | None]:
    """Tick i's record, shaped as actors._frames makes it, and the body's camera x (None without a body).

    The Move becomes a Person(x, id=1) with its hips at zone x, moved there from its x on the tick before (so
    vx is the tick's step) and its wrist held at wrist_y, placed with cal."""
    t = i * TICK
    bodies, cx = (), None
    if move is not None:
        x0, _, x1, _ = cal.zone
        cx = min(x1, max(x0, x0 + move.x * (x1 - x0)))
        person = Person(cx if before is None else before, id=1).walk(cx, TICK / 2, at=t - TICK)
        if move.wrist_y is not None:
            person.wrist(move.hand, move.wrist_y, move.wrist_y, 2 * TICK, at=t - TICK)
        bodies = (place(person.body_at(t, 1), cal),)
    w, h = MOTION_GRID
    return Sensed(t, camera_t=t, camera_fresh=True, camera_seq=i + 1, bodies=bodies, blobs=(),
                  motion=np.zeros((h, w), bool), audio=Audio()), cx


def _layout(game_cls, layout: str | None) -> str:
    """layout, else the game's one declared layout when it declares exactly one, else the wall's default."""
    if layout is not None:
        return layout
    declared = game_cls.info.layouts
    return next(iter(declared)) if len(declared) == 1 else ArcadeConfig().layout


def play(game_cls, bot: Bot, seed: int, layout: str | None = None, won: Callable[[dict], bool] | None = None,
         seconds: float = MAX_PLAY_SECONDS, keep_frames: bool = False, font: Font | None = None) -> Play:
    """Play game_cls with bot through the real runner (run_headless, seeded with seed) at layout; None is the
    game's one declared layout when it declares exactly one, else ArcadeConfig().layout.

    Each tick the bot gets the game's debug_state() of bot.reaction_ticks ticks ago ({} before there is one)
    and the tick's t; noise from random.Random(seed), SD bot.noise, is added to the Move's x and wrist_y,
    each clamped to 0..1. The feed stops after the tick on which the game is done() or its session ends
    otherwise (left, inactive: the game gets no more updates), or after seconds. won defaults to the game's
    for_game(...)[1], applied to the last debug_state().
    """
    if won is None:
        won = for_game(game_cls)[1]
    w, h = (int(v) for v in _layout(game_cls, layout).split("x"))
    cfg = ArcadeConfig(w, h, backend="fake", camera="none", audio="none")
    font = font if font is not None else _font(ROOT / cfg.font_path)
    name = game_cls.info.name
    noise = random.Random(seed)
    states: list[dict] = []
    ticks = 0

    def feed(runner: Runner) -> Iterator[Sensed]:
        nonlocal ticks
        cal, before = Calibration(), None
        for i in range(round(seconds / TICK)):
            k = i - 1 - bot.reaction_ticks
            move = bot(states[k] if k >= 0 else {}, i * TICK)
            if move is not None and bot.noise > 0:
                move = dataclasses.replace(move, x=_clamp01(move.x + noise.gauss(0.0, bot.noise)))
                if move.wrist_y is not None:
                    move = dataclasses.replace(move, wrist_y=_clamp01(move.wrist_y + noise.gauss(0.0, bot.noise)))
            sensed, before = _sensed(i, move, before, cal)
            yield sensed
            ticks += 1
            states.append(dict(runner.game.debug_state()))
            if runner.current_name != name:                  # done(), or the session ended otherwise
                return

    display = RecordingDisplay(keep_all=keep_frames)
    frames, runner = run_headless(cfg, font, game_cls, feed, seed=seed, display=display)
    state = states[-1] if states else {}
    phases = frozenset(s["phase"] for s in states if isinstance(s.get("phase"), str))
    return Play(seed=seed, ticks=ticks, seconds=ticks * TICK, done=bool(runner.game.done()), won=bool(won(state)),
                state=state, phases=phases, frames=frames if keep_frames else None)


def win_rate(game_cls, bot_factory: Callable[[], Bot], seeds: Sequence[int], layout: str | None = None) -> float:
    """The share of seeds a fresh bot_factory() bot wins on game_cls at layout (None as play() says)."""
    if not seeds:
        raise ValueError("win_rate needs at least one seed")
    return statistics.fmean(play(game_cls, bot_factory(), s, layout).won for s in seeds)
