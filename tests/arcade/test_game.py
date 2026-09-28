import dataclasses
import importlib
import inspect
import itertools
import logging
import math
import random
import types
from types import MappingProxyType

import numpy as np
import pytest

import arcade.game as game_module
import arcade.games as games
from arcade.canvas import Canvas
from arcade.game import (FX_PREFIX, INPUTS, KINDS, LAYOUTS, REQUIRED_SCENARIOS, RUNNER_KEYS, Game, GameInfo,
                         icon_from_rows, reserved)
from arcade.games import MENU_ORDER, all_games, get_game
from arcade.headless import run_headless
from arcade.juice import Juice
from arcade.scores import GameScores
from arcade.sensed import Sensed
from arcade.sources.actors import TICK, Person, scene
from tests.arcade.helpers import SpyGame, make_cfg, spy_info

BLANK = ["." * 16] * 16


def info(**over):
    return GameInfo(**(dict(name="dodge", title="Dodge", verb="DODGE", icon=icon_from_rows(BLANK),
                            needs=frozenset({"pose"})) | over))


def test_icon_from_rows():
    rows = ["#" + "." * 14 + "#"] + ["." * 16] * 14 + ["#" + "." * 14 + "#"]
    icon = icon_from_rows(rows)
    assert icon.shape == (16, 16) and icon.dtype == bool and not icon.flags.writeable
    assert icon[0, 0] and icon[15, 15] and not icon[7, 7] and icon.sum() == 4
    for bad in (["#"], ["." * 16] * 15, ["." * 16] * 15 + ["." * 15], ["." * 16] * 15 + ["." * 15 + "x"],
                [["."] * 16] * 16):
        with pytest.raises(ValueError):
            icon_from_rows(bad)


def test_game_info_is_frozen():
    i = info()
    with pytest.raises(Exception):
        i.name = "y"  # type: ignore[misc]
    with pytest.raises(ValueError):
        i.icon[0, 0] = True                                          # the icon is a read-only copy


def test_game_info_defaults_follow_the_spec():
    i = info()
    assert i.layouts == LAYOUTS == frozenset({"128x64"})
    assert (i.players, i.exit_gesture, i.kind, i.abandon_seconds) == (1, True, "control", None)
    assert INPUTS == frozenset({"pose", "blobs", "motion", "audio"}) and KINDS == ("control", "toy", "score")
    rows = ["#" * 16] + ["." * 16] * 15
    source = np.array([[ch == "#" for ch in r] for r in rows])
    i = info(icon=source, needs={"blobs", "audio"}, layouts=["64x32"], players=2, exit_gesture=False, kind="toy",
             abandon_seconds=45)
    source[0, 0] = False                                             # the caller's array is copied
    assert i.icon[0, 0] and i.needs == frozenset({"blobs", "audio"}) and i.layouts == frozenset({"64x32"})
    assert isinstance(i.needs, frozenset) and isinstance(i.layouts, frozenset)
    assert info(needs=frozenset()).needs == frozenset()             # a no-input toy is allowed
    assert info(abandon_seconds=np.float32(30)).abandon_seconds == 30  # a numpy number is a number


@pytest.mark.parametrize("over", [
    dict(icon=np.zeros((8, 8), bool)), dict(icon=np.zeros((16, 16), np.uint8)), dict(icon=None),
    dict(kind="arcade"), dict(layouts=frozenset({"128 x 32"})), dict(layouts=frozenset()), dict(layouts="128x32"),
    dict(layouts=frozenset({"0x32"})), dict(needs=frozenset({"pose", "sonar"})), dict(needs="pose"), dict(needs=""),
    dict(name="Dodge"), dict(name="3d"), dict(name=""), dict(name="_x"), dict(title=""), dict(verb="  "),
    dict(verb=None),
    dict(players=0), dict(players=3), dict(players=True), dict(players=1.0), dict(exit_gesture=1),
    dict(abandon_seconds=0), dict(abandon_seconds=-5.0), dict(abandon_seconds=math.inf),
    dict(abandon_seconds=math.nan), dict(abandon_seconds=True), dict(abandon_seconds="45"),
    dict(abandon_seconds=np.True_), dict(abandon_seconds=np.float32(0)),
])
def test_game_info_validates(over):
    with pytest.raises(ValueError):
        info(**over)


def test_reserved_keys_are_the_runners():
    assert RUNNER_KEYS == {"game", "t", "idle", "attract", "hidden", "crashes", "glitch", "flash_held_ticks", "player",
                           "present"}
    assert FX_PREFIX == "fx_" and reserved("fx_shake") and reserved("t") and reserved("present")
    assert not reserved("score") and not reserved("phase") and not reserved("ball_xy") and not reserved("tx")
    assert not reserved("fxlevel") and not reserved("fx")                  # the prefix is fx_, underscore and all


def test_game_protocol_defaults():
    class Toy(Game):
        info = info(name="paint")

    assert Toy.PHASES == ("play",) and Toy.CAPTION_KEYS == () and Toy.SCENARIOS == {}
    with pytest.raises(TypeError):
        Toy.SCENARIOS["serve"] = lambda: None                        # one default shared by every game: read-only


def test_protocol_members_are_the_frozen_set():
    # The canary for game-protocol-v1: a change here is a change to the frozen protocol, and needs a journaled
    # reason and no game task in flight (roadmap M4a).
    members = {n for n in vars(Game) if not n.startswith("_")} | set(Game.__annotations__)
    assert members == {"info", "scores", "SCENARIOS", "CAPTION_KEYS", "PHASES", "reset", "update", "draw", "done",
                       "debug_state"}
    params = {n: tuple(inspect.signature(getattr(Game, n)).parameters)
              for n in ("reset", "update", "draw", "done", "debug_state")}
    assert params == {"reset": ("self", "size", "rng", "fx"), "update": ("self", "sensed", "dt"),
                      "draw": ("self", "canvas"), "done": ("self",), "debug_state": ("self",)}
    assert inspect.signature(Game.reset).parameters["fx"].annotation == "Juice"
    assert [f.name for f in dataclasses.fields(GameInfo)] == ["name", "title", "verb", "icon", "needs", "layouts",
                                                               "players", "exit_gesture", "kind", "abandon_seconds"]
    for name in ("REQUIRED_SCENARIOS", "INPUTS", "KINDS", "LAYOUTS", "RUNNER_KEYS", "reserved", "icon_from_rows"):
        assert hasattr(game_module, name), name


def test_required_scenarios():
    assert REQUIRED_SCENARIOS == ("canonical", "idle_body", "nobody")

    class Stub(Game):
        info = info(name="stub")
        SCENARIOS = MappingProxyType({name: (lambda: iter(())) for name in REQUIRED_SCENARIOS})

    assert set(REQUIRED_SCENARIOS) <= set(Stub.SCENARIOS)
    assert not set(REQUIRED_SCENARIOS) <= set(Game.SCENARIOS)             # the default declares none


class Recorder(SpyGame):
    """Records what the runner passes: the dt of each update and the canvas at each draw."""

    info = spy_info("recorder", players=2)

    def __init__(self):
        super().__init__()
        self.dts, self.canvases = [], []

    def update(self, sensed, dt):
        super().update(sensed, dt)
        self.dts.append(dt)

    def draw(self, canvas):
        self.canvases.append((canvas, canvas.frame.copy()))
        super().draw(canvas)


def test_runner_passes_what_the_protocol_says(font5x7):
    feed = scene(persons=[Person(0.4, id=1), Person(0.6, id=2, height=0.5)], ticks=8)
    frames, runner = run_headless(make_cfg((128, 32)), font5x7, Recorder, itertools.islice(feed, 4))
    first = runner.game
    assert isinstance(first.scores_at_reset, GameScores)                  # scores set before reset
    assert first.size == (128, 32) and all(type(v) is int for v in first.size)
    assert type(first.rng) is random.Random and isinstance(first.fx, Juice)
    assert len(first.seen) == 4 and all(isinstance(s, Sensed) for s in first.seen)
    assert first.dts == [TICK] * 4
    assert all(s.player is not None and s.player.id == 1 and s.player2 is not None and s.player2.id == 2
               for s in first.seen)
    assert all(isinstance(c, Canvas) and not pixels.any() for c, pixels in first.canvases)   # a cleared canvas
    runner.end_session("done")
    assert runner.launch("recorder")
    for sensed in feed:
        runner.tick(sensed, TICK)
    second = runner.game
    assert second is not first and isinstance(second, Recorder) and second.updates == 4 and first.updates == 4
    assert second.fx is not first.fx and second.rng is not first.rng


def test_menu_order_lists_the_ten_spec_games():
    assert MENU_ORDER == ("copyme", "pong", "paint", "quickdraw", "dodge", "tug", "flap", "swat", "strongman",
                          "freeze")
    assert len(set(MENU_ORDER)) == 10


def fake_modules(monkeypatch, modules):
    """import_module that serves these fake arcade.games.<name> modules; anything else is missing."""
    real = importlib.import_module

    def import_module(name, package=None):
        short = name.rpartition(".")[2]
        if name.startswith("arcade.games.") and short in modules:
            found = modules[short]
            if isinstance(found, BaseException):
                raise found
            return found
        if name.startswith("arcade.games."):
            raise ModuleNotFoundError(f"No module named {name!r}", name=name)
        return real(name, package)

    monkeypatch.setattr(games.importlib, "import_module", import_module)


def module_with(game):
    m = types.ModuleType("fake")
    m.GAME = game
    return m


def game_class(name):
    return type(name.title(), (), {"info": info(name=name)})


def test_discovery_skips_missing_modules(monkeypatch, caplog):
    fake_modules(monkeypatch, {})
    assert all_games() == []                                         # no game module at all
    pong, dodge = game_class("pong"), game_class("dodge")
    fake_modules(monkeypatch, {"dodge": module_with(dodge), "pong": module_with(pong)})
    with caplog.at_level(logging.DEBUG, logger="arcade"):
        assert all_games() == [pong, dodge]                          # MENU_ORDER, not the order found
    assert caplog.records == []                                      # a game not written yet is not an error
    assert get_game("dodge") is dodge
    for name in ("copyme", "nope"):
        with pytest.raises(KeyError):
            get_game(name)


def test_broken_module_is_logged_and_skipped(monkeypatch, caplog):
    tug = game_class("tug")
    missing_dep = ModuleNotFoundError("No module named 'scipy'", name="scipy")
    missing_helper = ModuleNotFoundError("No module named 'arcade.games.strongman_audio'",
                                         name="arcade.games.strongman_audio")   # the game is there, its helper not
    missing_parent = ModuleNotFoundError("No module named 'arcade.games'", name="arcade.games")
    fake_modules(monkeypatch, {
        "copyme": RuntimeError("bad import"), "pong": SyntaxError("bad syntax"), "paint": missing_dep,
        "strongman": missing_helper, "freeze": missing_parent,
        "quickdraw": module_with(game_class("dodge")),               # GAME named after another game
        "dodge": types.ModuleType("fake"),                           # no GAME
        "flap": module_with(game_class("flap")()),                   # GAME is an instance, not the class
        "swat": module_with(type("Swat", (), {"info": "swat"})),     # info is not a GameInfo
        "tug": module_with(tug),
    })
    with caplog.at_level(logging.ERROR, logger="arcade"):
        assert all_games() == [tug]
    skipped = sorted(r.getMessage().split()[1] for r in caplog.records)
    assert skipped == ["copyme", "dodge", "flap", "freeze", "paint", "pong", "quickdraw", "strongman", "swat"]
    assert all(r.name == "arcade" for r in caplog.records)
    tracebacks = [r for r in caplog.records if r.exc_info]
    assert sorted(r.getMessage().split()[1] for r in tracebacks) == ["copyme", "freeze", "paint", "pong", "strongman"]
