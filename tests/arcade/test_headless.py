import itertools
import os
import statistics
import time

import numpy as np
import pytest

from arcade.flash import FlashGovernor
from arcade.game import RUNNER_KEYS
from arcade.headless import OPENING_NIGHT, NullLobby, RecordingDisplay, run_headless
from arcade.sources.actors import Person, scene
from tests.arcade.helpers import SpyGame, StubLobby, make_cfg, run, spy

BUDGET_MS = float(os.environ.get("ARCADE_TICK_BUDGET_MS", "2.0"))
SIZES = [(128, 32), (64, 64)]
WHITE = (255, 255, 255)


def stand(ticks):
    return scene(persons=[Person(id=1)], ticks=ticks)


class Speckle(SpyGame):
    """Draws a pixel its rng picks: frames that depend on the seed."""

    info = spy("speckle").info

    def draw(self, canvas):
        super().draw(canvas)
        canvas.pixel(self.rng.randrange(canvas.width), self.rng.randrange(canvas.height), WHITE)


class Strobe(SpyGame):
    """The whole wall white and black on alternate ticks, with a burst every second: the governor holds it."""

    info = spy("strobe").info

    def draw(self, canvas):
        super().draw(canvas)
        canvas.clear(WHITE if self.draws % 2 else (0, 0, 0))
        if self.draws % 30 == 0:
            self.fx.burst(canvas.width // 2, canvas.height // 2, (255, 120, 0))


class Static(SpyGame):
    """A fixed high-contrast picture: the governor passes it."""

    info = spy("static").info

    def draw(self, canvas):
        super().draw(canvas)
        for x in range(0, canvas.width, 8):
            canvas.fill_rect(x, 0, 4, canvas.height, WHITE)


def test_run_headless_returns_launched_instance_after_done(font5x7):
    frames, runner = run_headless(make_cfg((64, 64)), font5x7, spy(finish_after=5), stand(12))
    assert len(frames) == 12 and all(f.shape == (64, 64, 3) and f.dtype == np.uint8 for f in frames)
    game = runner.game
    assert isinstance(game, SpyGame) and game.updates == 5 and runner.current_name == "lobby"
    assert isinstance(runner.lobby, NullLobby) and [r.reason for r in runner.lobby.results] == ["done"]
    assert frames[4][0, 0].any() and not frames[5].any()             # then the null lobby draws nothing
    assert runner.lobby.request is None and runner.game is game


def test_run_headless_keeps_the_crashed_instance_when_not_strict(font5x7):
    boom = spy(raise_in=frozenset({"update"}))
    frames, runner = run_headless(make_cfg((64, 64)), font5x7, boom, stand(30), strict=False)
    assert len(frames) == 30 and isinstance(runner.game, boom) and runner.game.updates == 1
    assert runner.crashes == {"spy": 1} and "boom in update" in runner.last_error
    with pytest.raises(RuntimeError, match="boom in update"):
        run_headless(make_cfg((64, 64)), font5x7, boom, stand(30))  # strict is the default


def test_trace_and_raw_frames(font5x7):
    class White(SpyGame):
        def draw(self, canvas):
            canvas.clear(WHITE)

    cfg = make_cfg((64, 64))
    frames, runner = run_headless(cfg, font5x7, White, stand(10), trace=True, raw=True)
    assert len(runner.trace) == len(runner.raw_frames) == 10
    assert all(set(RUNNER_KEYS) <= set(s) for s in runner.trace) and runner.trace[-1]["updates"] == 10
    assert runner.raw_frames[-1][:-1].min() == 255                    # before the limiter (the marker row aside)
    assert frames[-1].max() < 255 and runner.limiter.scaled_ticks > 0  # after it: the day cap
    frames, runner = run_headless(cfg, font5x7, White, stand(10))
    assert runner.trace is None and runner.raw_frames is None


def test_local_time_is_fixed_to_opening_night(font5x7):
    frames, runner = run_headless(make_cfg((64, 64), leave_seconds=0.5), font5x7, SpyGame,
                                  scene(persons=[Person(id=1).leave(0.5)], ticks=40))
    assert runner.local_clock() == OPENING_NIGHT == runner.limiter.clock()
    assert runner.limiter.is_night() is False and runner.limiter.cap() == runner.cfg.apl_cap_day
    (record,) = runner.sessions.records
    assert record["start"] == "2026-11-11T21:00:00" and record["reason"] == "left"
    assert runner.sessions.path is None and runner.scores.path is None   # nothing written


def test_seeded_runs_repeat(font5x7):
    cfg = make_cfg((64, 64))
    a, _ = run_headless(cfg, font5x7, Speckle, stand(20), seed=3)
    b, _ = run_headless(cfg, font5x7, Speckle, stand(20), seed=3)
    c, _ = run_headless(cfg, font5x7, Speckle, stand(20), seed=4)
    assert all(np.array_equal(x, y) for x, y in zip(a, b))
    assert not all(np.array_equal(x, y) for x, y in zip(a, c))


def test_another_display_gets_the_frames(font5x7):
    display = RecordingDisplay(keep_all=False)
    frames, runner = run_headless(make_cfg((128, 32)), font5x7, SpyGame, stand(7), display=display)
    assert frames == [] and display.count == 7 and display.last.shape == (32, 128, 3)
    assert runner.display is display


def test_helpers_run_takes_ticks_and_config(font5x7):
    endless = itertools.cycle(list(stand(3)))
    frames, game, runner = run(SpyGame, endless, (128, 32), font5x7, ticks=10, brightness=0.3)
    assert len(frames) == 10 and game.updates == 10 and game is runner.game
    assert runner.cfg.brightness == 0.3 == runner.display.brightness and runner.cfg.size == (128, 32)
    assert runner.strict is True
    frames, game, runner = run(spy(raise_in=frozenset({"draw"})), stand(5), (64, 64), font5x7, strict=False)
    assert len(frames) == 5 and runner.crashes == {"spy": 1}


class RequestingLobby(StubLobby):
    """Requests the game called name in its update on tick at (counted from 0), once."""

    def __init__(self, name: str, at: int):
        super().__init__()
        self.name, self.at = name, at

    def update(self, sensed, dt):
        super().update(sensed, dt)
        if self.updates - 1 == self.at:
            self.request = self.name


def test_with_a_lobby_the_run_starts_in_the_lobby(font5x7):
    lobby = StubLobby()
    frames, runner = run_headless(make_cfg((64, 64)), font5x7, SpyGame, stand(10), trace=True, lobby=lobby)
    assert runner.lobby is lobby and lobby.updates == 10 and lobby.available == {"spy"}
    assert [s["game"] for s in runner.trace] == ["lobby"] * 10
    assert runner.game is None and len(frames) == 10
    assert all(f[0, 1].any() and not f[0, 0].any() for f in frames)  # the stub lobby's pixel, never the spy's


def test_the_lobbys_request_launches_the_game(font5x7):
    lobby = RequestingLobby("spy", at=5)
    frames, runner = run_headless(make_cfg((64, 64)), font5x7, SpyGame, stand(12), trace=True, lobby=lobby)
    assert [s["game"] for s in runner.trace] == ["lobby"] * 5 + ["spy"] * 7
    assert isinstance(runner.game, SpyGame) and runner.game.updates == 6   # ticks 6 to 11
    assert lobby.updates == 6 and lobby.request is None                   # the runner took the request


def test_several_games_are_offered_to_the_lobby(font5x7):
    first, second = spy("first"), spy("second")
    lobby = RequestingLobby("second", at=3)
    _, runner = run_headless(make_cfg((64, 64)), font5x7, [first, second], stand(8), trace=True, lobby=lobby)
    assert lobby.available == {"first", "second"} and set(runner.games) == {"first", "second"}
    assert [s["game"] for s in runner.trace] == ["lobby"] * 3 + ["second"] * 5
    assert type(runner.game) is second


def test_a_sequence_without_a_lobby_launches_the_first(font5x7):
    first, second = spy("first"), spy("second")
    _, runner = run_headless(make_cfg((64, 64)), font5x7, (first, second), stand(6), trace=True)
    assert isinstance(runner.lobby, NullLobby) and set(runner.games) == {"first", "second"}
    assert [s["game"] for s in runner.trace] == ["first"] * 6
    assert type(runner.game) is first and runner.game.updates == 6


def timed(frames, stamps):
    for s in frames:
        stamps.append(time.thread_time())
        yield s
    stamps.append(time.thread_time())


@pytest.mark.perf
@pytest.mark.parametrize("size", SIZES, ids=lambda s: f"{s[0]}x{s[1]}")
@pytest.mark.parametrize("game_cls", [Strobe, Static], ids=lambda g: g.info.name)
def test_tick_budget_with_the_governors_share(game_cls, size, font5x7, monkeypatch, capsys):
    # spec 9.2's budget, with a scenario on the governor's holding path (it04 N23, C27) and the governor's share.
    # Timed on the thread's CPU clock, which is the code's cost, what the budget is for. perf_counter also counts
    # the time the thread waits preempted, and under parallel agent load that failed this test (plan review B2).
    spent = []
    apply = FlashGovernor.apply

    def timed_apply(self, frame):
        start = time.thread_time()
        out = apply(self, frame)
        spent.append(time.thread_time() - start)
        return out

    monkeypatch.setattr(FlashGovernor, "apply", timed_apply)
    frames = list(stand(330))
    stamps = []
    _, runner = run_headless(make_cfg(size), font5x7, game_cls, timed(frames, stamps),
                             display=RecordingDisplay(keep_all=False))
    ticks = np.diff(stamps)[30:] * 1000                               # the first second warms up
    governor = np.array(spent[30:]) * 1000
    assert len(ticks) == len(governor) == 300
    held = runner.governor.held_ticks
    assert (held > 0) is (game_cls is Strobe)                          # the strobe is held, the static never
    mean, p95, share = ticks.mean(), float(np.percentile(ticks, 95)), governor.sum() / ticks.sum()
    report = (f"{game_cls.info.name} {size[0]}x{size[1]}: tick mean {mean:.3f} ms, p95 {p95:.3f} ms, governor "
              f"{governor.mean():.3f} ms ({share:.0%} of the tick), held {held} ticks")
    with capsys.disabled():
        print(f"\n{report}")
    assert mean < BUDGET_MS and p95 < 2 * BUDGET_MS, report
    assert statistics.median(governor) < 0.5, report
