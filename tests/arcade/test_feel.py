import collections
import json
import math
import statistics
import sys
import types

import pytest

from arcade import bots, feel
from arcade.bots import Move, Nobody
from arcade.game import Game, GameInfo
from arcade.sources.actors import TICK, Person, scene
from tests.arcade.helpers import CROSS_ICON

WALL = "128x32"
ORANGE, GREEN, WHITE = (255, 120, 0), (0, 200, 0), (255, 255, 255)


def sweeping():
    """Canonical for the stubs: nobody for 2 s, a person standing from 2.0 s, the right wrist sweeping reach v 0 to
    1 and back from 3.0 s, one sweep each way per 1.2 s."""
    person, t = Person(0.3, id=1).arrive(2.0), 3.0
    while t < feel.FEEL_SECONDS + 1:
        person.wrist("right", 0.0, 1.0, 0.6, at=t).wrist("right", 1.0, 0.0, 0.6, at=t + 0.6)
        t += 1.2
    return scene(persons=[person], ticks=round((feel.FEEL_SECONDS + 1) / TICK))


class Stub(Game):
    """A game that lasts a little longer than canonical's feel window."""

    SCENARIOS = {"canonical": sweeping}
    LIMIT = feel.FEEL_SECONDS + 1

    def reset(self, size, rng, fx):
        self.w, self.h = size
        self.t = 0.0

    def update(self, sensed, dt):
        self.t += dt

    def done(self):
        return self.t >= self.LIMIT - 1e-9

    def debug_state(self):
        return {"phase": "over" if self.done() else "play"}


class Follower(Stub):
    """A 12 px wide paddle at the cursor's reach v; won once it is held at the top for HOLD seconds."""

    info = GameInfo(name="follower", title="Follower", verb="FOLLOW", icon=CROSS_ICON, needs=frozenset({"pose"}))
    PHASES = ("play", "over")
    HOLD = 0.5

    def reset(self, size, rng, fx):
        super().reset(size, rng, fx)
        self.y, self.held, self.won = None, 0.0, False

    def update(self, sensed, dt):
        super().update(sensed, dt)
        p = sensed.player
        c = None if p is None else p.cursor
        self.y = None if c is None else c[1] * (self.h - 1)
        self.held = self.held + dt if self.y is not None and self.y <= 2 else 0.0
        self.won = self.won or self.held >= self.HOLD - 1e-9

    def draw(self, canvas):
        if self.y is not None:
            canvas.fill_rect(10, round(self.y) - 3, 12, 6, ORANGE)
        canvas.pixel(self.w - 1, 0, GREEN)

    def done(self):
        return self.won or super().done()

    def debug_state(self):
        state = {**super().debug_state(), "active": self.y is not None, "won": self.won}
        if self.y is not None:
            state["paddle_xy"] = (16, round(self.y, 2))
        return state


class Screensaver(Stub):
    """Ignores every input: a dot drifting on its own."""

    info = GameInfo(name="screensaver", title="Saver", verb="WATCH", icon=CROSS_ICON, needs=frozenset({"pose"}))

    def draw(self, canvas):
        x, y = self.dot()
        canvas.fill_rect(round(x) - 2, round(y) - 2, 4, 4, ORANGE)

    def dot(self):
        return ((self.t * 11.0) % self.w, self.h / 2 + 10 * math.sin(2 * math.pi * self.t / 3.1))

    def debug_state(self):
        return {**super().debug_state(), "active": True, "dot_xy": self.dot()}


class Still(Stub):
    """Rows 0-15 white, 16-23 (140, 0, 0) (not dim: a channel at 140), 24-31 (139, 139, 139) (dim)."""

    info = GameInfo(name="still", title="Still", verb="LOOK", icon=CROSS_ICON, needs=frozenset({"pose"}), kind="toy")

    def draw(self, canvas):
        canvas.fill_rect(0, 0, self.w, 16, WHITE)
        canvas.fill_rect(0, 16, self.w, 8, (140, 0, 0))
        canvas.fill_rect(0, 24, self.w, 8, (139, 139, 139))

    def debug_state(self):
        return {**super().debug_state(), "active": True}


class Good:
    """Holds the wrist at the top: wins the follower in HOLD seconds."""

    reaction_ticks, noise = 0, 0.0

    def __call__(self, state, t):
        return Move(x=0.5, wrist_y=0.0)


class Lazy(Good):
    """Stands there, hands down."""

    def __call__(self, state, t):
        return Move(x=0.5)


def _bots_module(name, good, lazy, won):
    module = types.ModuleType(f"arcade.games.{name}_bots")
    module.BOTS, module.won = {"good": good, "lazy": lazy}, won
    return module


@pytest.fixture(scope="module", autouse=True)
def stub_bots():
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "arcade.games.follower_bots",
                   _bots_module("follower", Good, Lazy, lambda state: state.get("won") is True))
        for name in ("screensaver", "still"):
            mp.setitem(sys.modules, f"arcade.games.{name}_bots",
                       _bots_module(name, Nobody, Nobody, lambda state: False))
        yield


FIDELITY = '[fidelity]\ninput = "cursor_y"\nxy = "{xy}"\naxis = 1\n'


@pytest.fixture(scope="module")
def follower_own(tmp_path_factory):
    path = tmp_path_factory.mktemp("feel") / "follower_feel.toml"
    path.write_text(FIDELITY.format(xy="paddle_xy"))
    return path


@pytest.fixture(scope="module")
def follower_report(follower_own, font5x7):
    runs = bots.seeds(Follower, WALL, 2)
    return runs, feel.report(Follower, WALL, seeds=runs, font=font5x7, own=follower_own)


def test_follower_passes_fidelity_and_response(follower_report, follower_own):
    runs, report = follower_report
    m = report["metrics"]
    assert feel.control(Follower, own=follower_own) == ("cursor_y", "paddle_xy", 1)
    assert m["response_ticks"] <= feel.LATENCY_TICKS, f"seeds {runs}: {m}"
    assert m["fidelity"] > 0.99 and m["range"] > 0.9, f"seeds {runs}: {m}"
    assert not [f for f in report["failures"] if f.split()[0] in ("response_ticks", "fidelity", "range")], \
        f"seeds {runs}: {report['failures']}"


def test_screensaver_fails_both(tmp_path, font5x7):
    own = tmp_path / "screensaver_feel.toml"
    own.write_text(FIDELITY.format(xy="dot_xy"))
    runs = bots.seeds(Screensaver, WALL, 1)
    m = feel.measure(Screensaver, WALL, seeds=runs, font=font5x7, own=own)
    assert m["response_ticks"] == 5 * feel.LATENCY_TICKS, f"seeds {runs}: {m}"
    assert m["fidelity"] is None or abs(m["fidelity"]) < 0.5, f"seeds {runs}: {m}"
    failing = {f.split()[0] for f in feel.judge(m, feel.budgets(Screensaver, WALL, own=own))}
    assert {"response_ticks", "fidelity"} <= failing, f"seeds {runs}: {failing}"
    assert m["win_good"] == m["win_lazy"] == m["win_none"] == 0.0


def test_override_without_reason_is_rejected(tmp_path):
    own = tmp_path / "follower_feel.toml"
    own.write_text('[budgets."128x32".dim_fraction]\nmax = 0.3\nreason = "the net is dim on purpose"\n'
                   '[budgets."128x32".lit_fraction]\nmax = 0.6\n')
    with pytest.raises(ValueError, match="lit_fraction"):
        feel.budgets(Follower, WALL, own=own)
    own.write_text('[budgets."128x32".liveliness]\nmin = 0.0001\nreason = "  "\n')
    with pytest.raises(ValueError, match="liveliness"):
        feel.budgets(Follower, WALL, own=own)
    own.write_text('[budgets."128x32".dim_fraction]\nmax = 0.3\nreason = "the net is dim on purpose"\n')
    got = feel.budgets(Follower, WALL, own=own)
    assert got["dim_fraction"] == feel.Budget("dim_fraction", None, 0.3, "the net is dim on purpose")
    assert got["lit_fraction"] == feel.Budget("lit_fraction", 0.01, 0.5, None)
    assert feel.budgets(Follower, "64x64", own=own)["dim_fraction"].max == 0.1     # another layout's table
    assert feel.budgets(Follower, WALL, own=tmp_path / "absent.toml") == feel.budgets(Follower, "64x64", own=own)
    assert feel.control(Follower, own=own) is None and feel.control(Follower, own=tmp_path / "absent.toml") is None


def test_layout_table_overrides_the_kind(tmp_path):
    defaults = tmp_path / "budgets.toml"
    defaults.write_text('[control.lit_fraction]\nmin = 0.01\nmax = 0.5\n[control.liveliness]\nmin = 0.001\n'
                        '[toy.lit_fraction]\nmin = 0.2\n'
                        '[control.layouts."64x64".lit_fraction]\nmax = 0.3\n')
    own = tmp_path / "follower_feel.toml"
    own.write_text('[budgets."64x64".lit_fraction]\nmin = 0.05\nreason = "a bigger paddle"\n')
    wide = feel.budgets(Follower, WALL, defaults=defaults, own=own)
    assert wide == {"lit_fraction": feel.Budget("lit_fraction", 0.01, 0.5, None),
                    "liveliness": feel.Budget("liveliness", 0.001, None, None)}
    square = feel.budgets(Follower, "64x64", defaults=defaults)
    assert square["lit_fraction"] == feel.Budget("lit_fraction", 0.01, 0.3, None)       # min kept, max replaced
    ours = feel.budgets(Follower, "64x64", defaults=defaults, own=own)
    assert ours["lit_fraction"] == feel.Budget("lit_fraction", 0.05, 0.3, "a bigger paddle")
    assert ours["liveliness"] == wide["liveliness"]
    assert set(feel.budgets(Still, WALL, defaults=defaults)) == {"lit_fraction"}       # the toy's own set


def test_judge_names_each_failing_budget():
    budgets = {"win_lazy": feel.Budget("win_lazy", 0.1, 0.7, None),
               "fidelity": feel.Budget("fidelity", 0.8, None, None),
               "round_seconds": feel.Budget("round_seconds", 20.0, 120.0, None),
               "lit_fraction": feel.Budget("lit_fraction", 0.01, 0.5, None),
               "range": feel.Budget("range", 0.6, None, "why")}
    metrics = {"win_lazy": 0.85, "fidelity": 0.5, "round_seconds": None, "lit_fraction": 0.2, "liveliness": 9.0}
    assert feel.judge(metrics, budgets) == ["win_lazy 0.85 > max 0.7", "fidelity 0.5 < min 0.8",
                                            "round_seconds None misses min 20, max 120", "range None misses min 0.6"]
    assert feel.judge({"lit_fraction": 0.5, "win_lazy": 0.1}, {k: budgets[k] for k in ("lit_fraction", "win_lazy")}) \
        == []


def test_dim_fraction_counts_dim_lit_pixels(font5x7):
    runs = bots.seeds(Still, WALL, 1)
    m = feel.measure(Still, WALL, seeds=runs, font=font5x7)
    # Raw frames: a quarter of the lit pixels is dim, less the two the player's marker (fx) lights from 2 s. The
    # limiter dims the pushed frames of so bright a wall to (128, 128, 128) and under: counted there it would be 1.
    assert m["dim_fraction"] == pytest.approx(0.25, abs=1e-3), f"seeds {runs}: {m}"
    assert m["lit_fraction"] == pytest.approx(1.0) and m["liveliness"] < 1e-5
    assert m["fidelity"] is None and m["range"] is None                     # no [fidelity]: not measured
    assert m["response_ticks"] == 5 * feel.LATENCY_TICKS


def test_good_plays_are_reused(monkeypatch, follower_own, font5x7):
    calls = collections.Counter()
    real = bots.play

    def counting(game_cls, bot, seed, *args, **kwargs):
        calls[type(bot).__name__] += 1
        return real(game_cls, bot, seed, *args, **kwargs)

    monkeypatch.setattr(bots, "play", counting)
    runs = bots.seeds(Follower, WALL, 3)
    m = feel.measure(Follower, WALL, seeds=runs, font=font5x7, own=follower_own)
    assert calls == {"Good": 3, "Lazy": 3, "Nobody": 3}, f"seeds {runs}"
    plays = [real(Follower, Good(), s, WALL, font=font5x7) for s in runs]
    assert all(p.done and p.won for p in plays), f"seeds {runs}"
    assert m["round_seconds"] == statistics.median(p.seconds for p in plays), f"seeds {runs}: {m}"
    assert m["phases_reached"] == 1.0 and (m["win_good"], m["win_lazy"], m["win_none"]) == (1.0, 0.0, 0.0)


def test_measure_repeats_under_seeds(follower_report, follower_own, font5x7):
    runs, report = follower_report
    again = feel.measure(Follower, WALL, seeds=len(runs), font=font5x7, own=follower_own)   # n: bots.seeds(..., n)
    assert again == report["metrics"], f"seeds {runs}"
    assert set(again) == {"response_ticks", "fidelity", "range", "lit_fraction", "dim_fraction", "liveliness",
                          "flash_area_raw", "square_flashes", "win_good", "win_lazy", "win_none", "round_seconds",
                          "phases_reached"}


def test_report_is_json_ok(follower_report):
    runs, report = follower_report
    back = json.loads(json.dumps(report, allow_nan=False))
    assert back == report and set(back) == {"metrics", "budgets", "failures"}, f"seeds {runs}"
    assert back["budgets"]["response_ticks"] == {"min": None, "max": 2.0, "reason": None}
    assert set(back["budgets"]) == set(feel.budgets(Follower, WALL))
    assert back["failures"] == feel.judge(report["metrics"], feel.budgets(Follower, WALL))
