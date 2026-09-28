"""Test helpers: configs, a spy game, a stub lobby and a fake clock."""
from __future__ import annotations

import random
from dataclasses import replace

from arcade.canvas import Canvas
from arcade.config import ArcadeConfig
from arcade.game import Game, GameInfo, icon_from_rows
from arcade.sensed import Sensed

BLANK_ICON = icon_from_rows(["." * 16] * 16)
CROSS_ICON = icon_from_rows(["#" * 16] * 2 + ["##" + "." * 12 + "##"] * 12 + ["#" * 16] * 2)


def make_cfg(size: tuple[int, int], **over) -> ArcadeConfig:
    return replace(ArcadeConfig(width=size[0], height=size[1], backend="fake", camera="none", audio="none"), **over)


def spy_info(name: str = "spy", **over) -> GameInfo:
    return GameInfo(**(dict(name=name, title=name.title(), verb="SPY", icon=CROSS_ICON, needs=frozenset({"pose"}))
                       | over))


class SpyGame(Game):
    """Records calls. Class attributes configure it: raise_in names the methods that raise ("init", "reset",
    "update", "draw", "done", "debug_state"), finish_after ends the game after that many updates, extra adds to
    debug_state."""

    info = spy_info()
    raise_in: frozenset[str] = frozenset()
    finish_after: int | None = None
    extra: dict = {}

    def __init__(self):
        if "init" in self.raise_in:
            raise RuntimeError("boom in init")
        self.updates = self.draws = 0
        self.size = self.rng = self.fx = self.scores_at_reset = None
        self.seen: list[Sensed] = []

    def reset(self, size, rng: random.Random, fx) -> None:
        self.scores_at_reset = getattr(self, "scores", None)
        if "reset" in self.raise_in:
            raise RuntimeError("boom in reset")
        self.size, self.rng, self.fx = size, rng, fx

    def update(self, sensed: Sensed, dt: float) -> None:
        self.updates += 1
        self.seen.append(sensed)
        if "update" in self.raise_in:
            raise RuntimeError("boom in update")

    def draw(self, canvas: Canvas) -> None:
        self.draws += 1
        if "draw" in self.raise_in:
            raise RuntimeError("boom in draw")
        canvas.pixel(0, 0, (255, 255, 255))

    def done(self) -> bool:
        if "done" in self.raise_in:
            raise RuntimeError("boom in done")
        return self.finish_after is not None and self.updates >= self.finish_after

    def debug_state(self) -> dict:
        if "debug_state" in self.raise_in:
            raise RuntimeError("boom in debug_state")
        return {"updates": self.updates, **self.extra}


def spy(name: str = "spy", info: dict | None = None, **attrs) -> type:
    """A SpyGame subclass called name, with GameInfo fields info and class attributes attrs."""
    return type(name.title(), (SpyGame,), {"info": spy_info(name, **(info or {})), **attrs})


class StubLobby:
    """A lobby that records what the runner tells it. Set request to launch a game on the next tick."""

    info = None

    def __init__(self, raise_in: frozenset[str] = frozenset()):
        self.raise_in = raise_in
        self.request: str | None = None
        self.available: set[str] | None = None
        self.status = None
        self.results: list = []
        self.resets = self.updates = 0
        self.seen: list[Sensed] = []

    def reset(self, size, rng, fx=None) -> None:
        self.resets += 1

    def update(self, sensed: Sensed, dt: float) -> None:
        self.updates += 1
        self.seen.append(sensed)
        if "update" in self.raise_in:
            raise RuntimeError("lobby boom")

    def draw(self, canvas: Canvas) -> None:
        canvas.pixel(1, 0, (0, 255, 0))

    def done(self) -> bool:
        return False

    def debug_state(self) -> dict:
        return {"request": self.request}

    def set_available(self, names: set[str]) -> None:
        self.available = set(names)

    def set_status(self, camera_ok: bool, mic_ok: bool, inputs: set[str], calibrated: bool) -> None:
        self.status = (camera_ok, mic_ok, set(inputs), calibrated)

    def end_session(self, result) -> None:
        self.results.append(result)


class FakeClock:
    def __init__(self, now: float = 100.0):
        self.now = now

    def __call__(self) -> float:
        return self.now

    def sleep(self, s: float) -> None:
        self.now += s
