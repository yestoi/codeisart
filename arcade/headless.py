"""Headless pieces shared by the tests and the agent tools: a recording display, a lobby that never requests, and
run_headless, which runs one game through the real runner (spec 9.1)."""
from __future__ import annotations

import random
from datetime import datetime
from typing import Iterable

import numpy as np

from arcade.config import ArcadeConfig
from arcade.scores import Scores, SessionLog
from arcade.sensed import Sensed
from arcade.sources.actors import TICK
from show.font import Font

OPENING_NIGHT = datetime(2026, 11, 11, 21, 0)    # headless local time: evidence never depends on the time of day


class RecordingDisplay:
    """A display that keeps copies of what it was pushed: every frame (keep_all) or only the last."""

    def __init__(self, keep_all: bool = True):
        self.keep_all = keep_all
        self.frames: list[np.ndarray] = []
        self.last: np.ndarray | None = None
        self.count = 0
        self.brightness = 1.0
        self.closed = False

    def push(self, frame: np.ndarray) -> None:
        copy = frame.copy()
        if self.keep_all:
            self.frames.append(copy)
        self.last = copy
        self.count += 1

    def set_brightness(self, level: float) -> None:
        self.brightness = level

    def close(self) -> None:
        self.closed = True


class NullLobby:
    """A lobby that draws nothing and never requests a game: for tools and tests that launch a game directly."""

    info = None

    def __init__(self):
        self.request: str | None = None
        self.results: list = []

    def reset(self, size, rng: random.Random, fx=None) -> None:
        pass

    def update(self, sensed: Sensed, dt: float) -> None:
        pass

    def draw(self, canvas) -> None:
        pass

    def done(self) -> bool:
        return False

    def debug_state(self) -> dict:
        return {}

    def set_available(self, names: set[str]) -> None:
        pass

    def set_status(self, camera_ok: bool, mic_ok: bool, inputs: set[str], calibrated: bool) -> None:
        pass

    def end_session(self, result) -> None:
        self.results.append(result)


def run_headless(cfg: ArcadeConfig, font: Font, game_cls: type, sensed_iter: Iterable[Sensed], seed: int = 0,
                 strict: bool = True, trace: bool = False, raw: bool = False, display=None):
    """Run game_cls through the real runner, one tick of TICK per Sensed, and return (frames, runner).

    The runner has in-memory scores and sessions, a NullLobby, and a local clock fixed at OPENING_NIGHT (the
    brightness limiter's day cap). runner.game is the launched instance, kept after done() or a crash; with trace
    runner.trace holds state() after every tick, and with raw runner.raw_frames every frame before the limiter.
    display defaults to a RecordingDisplay keeping every frame; frames is its list (empty for another display).
    """
    from arcade.runner import Runner

    display = RecordingDisplay() if display is None else display
    runner = Runner(cfg, display, font, NullLobby(), [game_cls], seed=seed, strict=strict,
                    scores=Scores(None, lambda: OPENING_NIGHT), sessions=SessionLog(None),
                    local_clock=lambda: OPENING_NIGHT)
    runner.trace = [] if trace else None
    runner.raw_frames = [] if raw else None
    runner.launch(game_cls.info.name)
    for sensed in sensed_iter:
        runner.tick(sensed, TICK)
    return getattr(display, "frames", []), runner
