import collections
import json
import math
import statistics
import sys
import tomllib
import types

import numpy as np
import pytest

from arcade import bots, feel
from arcade.attract import lobby
from arcade.bots import Move, Nobody
from arcade.canvas import Canvas
from arcade.config import ArcadeConfig
from arcade.game import KINDS, Game, GameInfo
from arcade.headless import run_headless
from arcade.input import Depth
from arcade.sensed import Body, Keypoint
from arcade.sources.actors import TICK, Person, scene
from tests.arcade.helpers import CROSS_ICON

WALL = "128x64"
ORANGE, GREEN, WHITE = (255, 120, 0), (0, 200, 0), (255, 255, 255)
RAISE = 2.5                         # s: canonical's raised hand, which the lobby launches the stubs on
CANONICAL = 8.0                     # s: the stubs' canonical, shorter than feel's window (feel measures what is there)
BOTH = (1, 2)                       # the scales find_text looks at when a test says both
STUBS = ("follower", "screensaver", "still", "scorer", "creeper", "pinned", "arrival", "tiny", "depth")


def _cfg() -> ArcadeConfig:
    w, h = (int(v) for v in WALL.split("x"))
    return ArcadeConfig(w, h, backend="fake", camera="none", audio="none")


def sweeping():
    """Canonical for the stubs, the way the guide says: nobody for 2 s, a person walking up at 2.0 s and raising the
    right hand at RAISE for 0.5 s (the lobby launches the game), then the right wrist sweeping reach v 0 to 1 and
    back from RAISE + 1 s, one sweep each way per 1.2 s, for CANONICAL s in all."""
    person, t = Person(0.3, id=1).arrive(2.0).raise_hand(RAISE, 0.5), RAISE + 1.0
    while t < CANONICAL:
        person.wrist("right", 0.0, 1.0, 0.6, at=t).wrist("right", 1.0, 0.0, 0.6, at=t + 0.6)
        t += 1.2
    return scene(persons=[person], ticks=round(CANONICAL / TICK))


def idle_body():
    """One body standing still, hands down, from the first tick."""
    return scene(persons=[Person(0.3, id=1)], ticks=round((feel.PRESENCE_WINDOW + 1) / TICK))


def nobody():
    return scene(ticks=round((feel.PRESENCE_WINDOW + 1) / TICK))


class Stub(Game):
    """A game that lasts longer than canonical."""

    SCENARIOS = {"canonical": sweeping, "idle_body": idle_body, "nobody": nobody}
    LIMIT = CANONICAL

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
    """A 12 px wide paddle at the cursor's reach v (place()); won once it is held at the top for HOLD seconds."""

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
        self.y = None if c is None else self.place(c, sensed.t)
        self.held = self.held + dt if self.y is not None and self.y <= 2 else 0.0
        self.won = self.won or self.held >= self.HOLD - 1e-9

    def place(self, cursor, t):
        return cursor[1] * (self.h - 1)

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


class Pinned(Follower):
    """The follower with its paddle pinned at the wall's bottom edge until the runner's PIN s, over half of the
    sweeping in canonical: a clamped control. Canonical only (no presence runs)."""

    info = GameInfo(name="pinned", title="Pinned", verb="FOLLOW", icon=CROSS_ICON, needs=frozenset({"pose"}))
    SCENARIOS = {"canonical": sweeping}
    PIN = 6.0 + TICK / 2

    def place(self, cursor, t):
        return self.h - 1.0 if t < self.PIN else super().place(cursor, t)


class Creeper(Stub):
    """A 2 px square paddle that moves 1 px a tick, up or down as the cursor's reach v moved on the tick. Canonical
    only (no presence runs)."""

    info = GameInfo(name="creeper", title="Creeper", verb="FOLLOW", icon=CROSS_ICON, needs=frozenset({"pose"}))
    SCENARIOS = {"canonical": sweeping}

    def reset(self, size, rng, fx):
        super().reset(size, rng, fx)
        self.y, self.v = self.h // 2, None

    def update(self, sensed, dt):
        super().update(sensed, dt)
        p = sensed.player
        v = None if p is None or p.cursor is None else p.cursor[1]
        if v is not None and self.v is not None and v != self.v:
            self.y = min(self.h - 2, max(0, self.y + (1 if v > self.v else -1)))
        self.v = v

    def draw(self, canvas):
        canvas.fill_rect(10, self.y, 2, 2, ORANGE)

    def debug_state(self):
        return {**super().debug_state(), "active": self.v is not None, "paddle_xy": (10, self.y)}


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
    """The top half white, the next quarter (140, 0, 0) (not dim: a channel at 140), the bottom quarter
    (139, 139, 139) (dim)."""

    info = GameInfo(name="still", title="Still", verb="LOOK", icon=CROSS_ICON, needs=frozenset({"pose"}), kind="toy")

    def draw(self, canvas):
        half, quarter = self.h // 2, self.h // 4
        canvas.fill_rect(0, 0, self.w, half, WHITE)
        canvas.fill_rect(0, half, self.w, quarter, (140, 0, 0))
        canvas.fill_rect(0, half + quarter, self.w, self.h - half - quarter, (139, 139, 139))

    def debug_state(self):
        return {**super().debug_state(), "active": True}


class Scorer(Stub):
    """A point every 2 s, drawn white at 2x at the top left, hidden for the first second of every 4;
    done after one of those 4 s (a tick past it: the done tick ends the session, so 120 ticks count)."""

    info = GameInfo(name="scorer", title="Scorer", verb="COUNT", icon=CROSS_ICON, needs=frozenset({"pose"}),
                    kind="score")
    LIMIT = 4.0 + TICK / 2

    def points(self):
        return int(self.t // 2.0)

    def draw(self, canvas):
        if self.t % 4.0 >= 1.0:
            canvas.text(3, 2, self.points(), WHITE, scale=2)

    def debug_state(self):
        return {**super().debug_state(), "active": True, "score": self.points()}


class Tiny(Scorer):
    """The scorer's points, always shown and always at 1x."""

    info = GameInfo(name="tiny", title="Tiny", verb="COUNT", icon=CROSS_ICON, needs=frozenset({"pose"}), kind="score")

    def draw(self, canvas):
        canvas.text(3, 2, self.points(), WHITE, scale=1)


class Arrival(Stub):
    """Records (sensed.t, sensed.player) on each instance's first update in firsts; done after a second."""

    info = GameInfo(name="arrival", title="Arrival", verb="ARRIVE", icon=CROSS_ICON, needs=frozenset({"pose"}))
    LIMIT = 1.0
    firsts: list = []

    def update(self, sensed, dt):
        if self.t == 0.0:
            type(self).firsts.append((sensed.t, sensed.player))
        super().update(sensed, dt)

    def draw(self, canvas):
        canvas.pixel(0, 0, GREEN)

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
    """The stubs' bots, and the stubs in the lobby's menu: the lobby features only a MENU_ORDER game."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "arcade.games.follower_bots",
                   _bots_module("follower", Good, Lazy, lambda state: state.get("won") is True))
        for name in STUBS[1:]:
            mp.setitem(sys.modules, f"arcade.games.{name}_bots",
                       _bots_module(name, Nobody, Nobody, lambda state: False))
        mp.setattr(lobby, "MENU_ORDER", (*lobby.MENU_ORDER, *STUBS))
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


@pytest.fixture(scope="module")
def canonical_of(follower_report, follower_own, font5x7, tmp_path_factory):
    """feel's canonical metrics of a stub at WALL under its first seed with PROBES = probes, each computed once
    (the follower's at the default PROBES is its report's). No [fidelity] but the follower's."""
    absent = tmp_path_factory.mktemp("none") / "absent.toml"
    cache = {(Follower, feel.PROBES): follower_report[1]["metrics"]}

    def get(game, probes=feel.PROBES):
        if (game, probes) not in cache:
            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(feel, "PROBES", probes)
                own = follower_own if game is Follower else absent
                cache[game, probes] = feel._canonical(_cfg(), font5x7, game, bots.seeds(game, WALL, 1)[0], own)
        return cache[game, probes]

    return get


@pytest.mark.parametrize("game", [Follower, Creeper], ids=["follower", "creeper"])
def test_response_ticks_does_not_depend_on_the_probe_count(canonical_of, game):
    got = {n: canonical_of(game, n)["response_ticks"] for n in (4, 8, 16)}
    assert got == {4: 1.0, 8: 1.0, 16: 1.0}, f"seed {bots.seeds(game, WALL, 1)}: {got}"


def test_a_clamped_control_is_not_probed(monkeypatch, tmp_path, font5x7):
    own = tmp_path / "pinned_feel.toml"
    own.write_text(FIDELITY.format(xy="paddle_xy"))
    seen = []
    real = feel._response

    def recording(*args):
        seen.append(list(args[-1]))
        return real(*args)

    monkeypatch.setattr(feel, "_response", recording)
    runs = bots.seeds(Pinned, WALL, 1)
    m = feel._canonical(_cfg(), font5x7, Pinned, runs[0], own)
    (probes,) = seen
    free = math.ceil(Pinned.PIN / TICK) - 1          # the first record whose update the pin lets through
    assert probes and all(p + 1 >= free for p in probes), f"seeds {runs}: probes {probes}, free from {free}"
    assert m["response_ticks"] == 1.0, f"seeds {runs}: {m}"


def test_response_px_counts_the_change_after_two_ticks(canonical_of):
    slow, fast = canonical_of(Creeper)["response_px"], canonical_of(Follower)["response_px"]
    assert slow < feel.RESPONSE_PX <= fast, f"seeds {bots.seeds(Creeper, WALL, 1)}: creeper {slow}, follower {fast}"
    assert "response_px" in {f.split()[0] for f in feel.judge({"response_px": slow}, feel.budgets(Creeper, WALL))}


def test_measure_launches_through_the_lobby(monkeypatch, font5x7):
    monkeypatch.setattr(Arrival, "firsts", [])
    runs = bots.seeds(Arrival, WALL, 1)
    feel.measure(Arrival, WALL, seeds=runs, font=font5x7)
    t, player = Arrival.firsts[0]                  # canonical's run comes first
    launched = round(t / TICK) - 2                 # runner t after record j is (j + 1) ticks; updated the tick after
    raised = round(RAISE / TICK)                   # the scene record the hand goes up on
    assert isinstance(player, Body), f"seeds {runs}: {player}"
    assert raised <= launched <= raised + 1, f"seeds {runs}: launched {launched}, raised {raised}"


def test_measure_needs_canonical_to_launch_the_game(font5x7):
    standing = lambda: scene(persons=[Person(0.3, id=1).arrive(2.0)], ticks=round(CANONICAL / TICK))
    unraised = type("Unraised", (Follower,), {"SCENARIOS": {**Follower.SCENARIOS, "canonical": standing}})
    with pytest.raises(ValueError, match="follower never launched"):
        feel.measure(unraised, WALL, seeds=[1], font=font5x7)


def test_measure_refuses_an_undeclared_layout(font5x7):
    assert "128x32" not in Follower.info.layouts
    with pytest.raises(ValueError, match=r"follower.*128x32"):
        feel.measure(Follower, "128x32", seeds=[1], font=font5x7)
    with pytest.raises(ValueError, match=r"follower.*128x32"):
        feel.report(Follower, "128x32", seeds=[1], font=font5x7)


def test_a_1x_score_is_not_visible(font5x7):
    cfg = _cfg()
    pushed, runner = run_headless(cfg, font5x7, Tiny, scene(ticks=60), trace=True)
    current = [s["game"] == "tiny" for s in runner.trace]
    assert all(current)
    assert feel._score(font5x7, pushed, runner.trace, current, cfg.gamma)["score_visible"] == 0.0


def test_override_without_reason_is_rejected(tmp_path):
    own = tmp_path / "follower_feel.toml"
    own.write_text(f'[budgets."{WALL}".dim_fraction]\nmax = 0.3\nreason = "the net is dim on purpose"\n'
                   f'[budgets."{WALL}".lit_fraction]\nmax = 0.6\n')
    with pytest.raises(ValueError, match="lit_fraction"):
        feel.budgets(Follower, WALL, own=own)
    own.write_text(f'[budgets."{WALL}".liveliness]\nmin = 0.0001\nreason = "  "\n')
    with pytest.raises(ValueError, match="liveliness"):
        feel.budgets(Follower, WALL, own=own)
    own.write_text(f'[budgets."{WALL}".dim_fraction]\nmax = 0.3\nreason = "the net is dim on purpose"\n')
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
    # Raw frames, the game's from its launch: a quarter of the lit pixels is dim, less the two the player's marker
    # (fx) lights. The limiter dims the pushed frames of so bright a wall to (128, 128, 128) and under: counted
    # there it would be 1.
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
                          "phases_reached", "score_visible", "score_legible", "presence_answer_seconds",
                          "response_px"}


def test_report_is_json_ok(follower_report):
    runs, report = follower_report
    back = json.loads(json.dumps(report, allow_nan=False))
    assert back == report and set(back) == {"metrics", "budgets", "failures"}, f"seeds {runs}"
    assert back["budgets"]["response_ticks"] == {"min": None, "max": 2.0, "reason": None}
    assert back["budgets"]["response_px"] == {"min": 12.0, "max": None, "reason": None}
    assert set(back["budgets"]) == set(feel.budgets(Follower, WALL))
    assert back["failures"] == feel.judge(report["metrics"], feel.budgets(Follower, WALL))


def _drawn(font, text, x, y, color=WHITE, scale=1):
    canvas = Canvas(128, 32, font)
    canvas.text(x, y, text, color, scale=scale)
    return canvas.frame


def test_find_text_locates_the_score_at_either_scale(font5x7):
    frame = _drawn(font5x7, "37", 40, 3)
    x, y, mask = feel.find_text(frame, font5x7, "37", scales=BOTH)
    assert (x, y) == (40, 3) and int(mask.sum()) == int(frame.any(axis=2).sum())
    x, y, mask = feel.find_text(_drawn(font5x7, "1", 10, 12, GREEN, scale=2), font5x7, "1", scales=BOTH)
    assert (x, y) == (12, 12) and mask.shape == (14, 6)            # "1" is lit in its glyph's columns 1 to 3
    assert feel.find_text(_drawn(font5x7, "0", 3, 0), font5x7, "0", scales=BOTH)[:2] == (3, 0)   # off the wall is dark
    assert feel.find_text(_drawn(font5x7, "38", 40, 3), font5x7, "37", scales=BOTH) is None
    assert feel.find_text(_drawn(font5x7, "37", 40, 3), font5x7, "7", scales=BOTH) is not None   # a digit of 37
    touching = _drawn(font5x7, "37", 40, 3)
    touching[2, 45] = ORANGE                                        # a lit pixel in the glyph's gutter
    assert feel.find_text(touching, font5x7, "37", scales=BOTH) is None
    assert feel.find_text(np.zeros((32, 128, 3), np.uint8), font5x7, "0", scales=BOTH) is None


def test_legibility_passes_a_bright_score_at_5m_and_fails_one_in_glare_or_far(font5x7):
    floor = feel.budgets(Scorer, WALL)["score_legible"].min
    for color, scale in ((WHITE, 1), (GREEN, 1), (ORANGE, 2)):
        for digit in "0123456789":
            frame = _drawn(font5x7, digit, 60, 4, color, scale)
            found = feel.find_text(frame, font5x7, digit, scales=BOTH)
            assert feel.legibility(frame, *found, 2.2) >= floor, (color, scale, digit)
    frame = _drawn(font5x7, "8", 60, 4)
    assert feel.legibility(frame, *feel.find_text(frame, font5x7, "8", scales=BOTH), 2.2) == 1.0      # whole at 5 m
    frame = _drawn(font5x7, "5", 60, 4)
    found = feel.find_text(frame, font5x7, "5", scales=BOTH)
    assert feel.legibility(frame, *found, 2.2, metres=10.0) < floor       # 1x is too small at 10 m (spec 7.4)
    glare = np.full((32, 128, 3), 255, np.uint8)                   # a white field up to a 1 px dark gutter
    glare[3:12, 59:66] = 0
    glare |= _drawn(font5x7, "8", 60, 4, (140, 0, 0))
    x, y, mask = feel.find_text(glare, font5x7, "8", scales=BOTH)
    assert (x, y) == (60, 4)
    assert feel.legibility(glare, x, y, mask, 2.2) < floor


@pytest.fixture(scope="module")
def scorer_report(font5x7):
    runs = bots.seeds(Scorer, WALL, 1)
    return runs, feel.report(Scorer, WALL, seeds=runs, font=font5x7)


def test_score_visibility_counts_the_ticks_it_is_shown(scorer_report):
    runs, report = scorer_report
    m = report["metrics"]
    assert m["score_visible"] == pytest.approx(0.75, abs=0.01), f"seeds {runs}: {m}"
    assert m["score_legible"] >= report["budgets"]["score_legible"]["min"], f"seeds {runs}: {m}"
    assert [f for f in report["failures"] if f.startswith("score_")] == ["score_visible 0.75 < min 0.8"], \
        f"seeds {runs}: {report['failures']}"                        # hidden one tick in four: too often
    assert m["presence_answer_seconds"] == feel.PRESENCE_WINDOW, f"seeds {runs}: {m}"   # draws nothing for a body
    assert "presence_answer_seconds" not in report["budgets"], f"seeds {runs}"
    assert not [f for f in report["failures"] if f.startswith("presence_answer")], \
        f"seeds {runs}: {report['failures']}"                        # measured, never judged


def test_a_score_that_is_never_shown_misses_both(follower_report):
    runs, report = follower_report
    m = report["metrics"]
    assert m["score_visible"] is None and m["score_legible"] is None, f"seeds {runs}: {m}"   # no score key
    table = feel.budgets(Scorer, WALL)
    assert "score_visible" not in feel.budgets(Follower, WALL)          # only the score kind is judged on it
    liar = {"score_visible": 0.0, "score_legible": None}
    assert feel.judge(liar, {k: table[k] for k in liar}) \
        == ["score_visible 0 < min 0.8", "score_legible None misses min 0.9"]


def test_presence_answer_times_the_first_answer_to_a_present_body(follower_report, font5x7):
    runs, report = follower_report
    assert report["metrics"]["presence_answer_seconds"] < 0.5, f"seeds {runs}: {report['metrics']}"
    assert "presence_answer_seconds" not in report["budgets"], f"seeds {runs}"
    cfg = _cfg()
    assert feel._presence_answer(cfg, font5x7, Screensaver, runs[0]) == feel.PRESENCE_WINDOW, f"seed {runs[0]}"
    blind = type("Blind", (Follower,), {"SCENARIOS": {"canonical": sweeping}})
    assert feel._presence_answer(cfg, font5x7, blind, runs[0]) is None


def test_presence_answer_has_no_default_budget():
    stubs = {g.info.kind: g for g in (Follower, Scorer, Still)}
    assert set(stubs) == set(KINDS)
    raw = tomllib.loads(feel.DEFAULTS.read_text())
    for kind, game in stubs.items():
        tables = [raw[kind], *raw[kind].get("layouts", {}).values()]
        table = feel.budgets(game, WALL)
        assert all("presence_answer_seconds" not in t for t in tables), kind
        assert "presence_answer_seconds" not in table, kind
        for value in (None, 0.0, feel.PRESENCE_WINDOW, 1e9):
            failures = feel.judge({"presence_answer_seconds": value}, table)
            assert not [f for f in failures if f.startswith("presence_answer")], (kind, value, failures)
    assert feel.judge({"presence_answer_seconds": None}, {}) == []


def test_near_and_far_read_the_log_scale():
    for ratio in (0.74, 1.0, 1.35):
        p = Person(0.5, height=0.7).scale_to(ratio, 0.5, at=0.0).body_at(1.0, 1)
        assert feel.INPUTS["near"](p) == -feel.INPUTS["far"](p) == math.log(p.scale), ratio
    assert feel.INPUTS["near"](p) > feel.INPUTS["near"](Person(0.5, height=0.7).body_at(1.0, 1))   # nearer is larger
    nothing = Body(1, (0.0, 0.0, 0.0, 0.0), tuple(Keypoint(0.5, 0.5, 0.0) for _ in range(17)))
    assert nothing.scale == 0.0 and feel.INPUTS["near"](nothing) is None and feel.INPUTS["far"](nothing) is None


def stepping():
    """Canonical for a body in depth: sweeping's walk-up and raised hand, then from RAISE + 1 s the body steps in
    and out between ratios 0.78 and 1.28 of its first size, 0.8 s each way (Pong's canonical steps so), for
    CANONICAL s in all."""
    person, t = Person(0.3, height=bots.BODY_HEIGHT, id=1).arrive(2.0).raise_hand(RAISE, 0.5), RAISE + 1.0
    person.scale_to(1.28, 0.8, at=t)
    while t < CANONICAL:
        t += 0.8
        person.scale_to(0.78, 0.8, at=t).scale_to(1.28, 0.8, at=t + 0.8)
        t += 0.8
    return scene(persons=[person], ticks=round(CANONICAL / TICK))


class DepthFollower(Stub):
    """A 3 px wide, PADDLE_H tall paddle whose centre y is (1 - value) * (h - 1) from a Depth, nearer up (the
    paddle may run off an edge). The Depth is fresh at reset, so it centres where the body stood at the launch."""

    info = GameInfo(name="depth", title="Depth", verb="STEP", icon=CROSS_ICON, needs=frozenset({"pose"}))
    SCENARIOS = {"canonical": stepping}
    PADDLE_W, PADDLE_H = 3, 16

    def reset(self, size, rng, fx):
        super().reset(size, rng, fx)
        self.depth, self.y = Depth(), None

    def update(self, sensed, dt):
        super().update(sensed, dt)
        v = self.depth.update(sensed.player, sensed.t, sensed.camera_t)
        if v is not None:
            self.y = (1.0 - v) * (self.h - 1)

    def draw(self, canvas):
        if self.y is not None:
            canvas.fill_rect(10, round(self.y - self.PADDLE_H / 2), self.PADDLE_W, self.PADDLE_H, ORANGE)

    def debug_state(self):
        state = {**super().debug_state(), "active": self.y is not None}
        if self.y is not None:
            state["paddle_xy"] = (11, round(self.y, 2))
        return state


def test_depth_follower_passes_fidelity_and_response(tmp_path, font5x7):
    own = tmp_path / "depth_feel.toml"
    own.write_text('[fidelity]\ninput = "far"\nxy = "paddle_xy"\naxis = 1\n')
    assert feel.control(DepthFollower, own=own) == ("far", "paddle_xy", 1)
    seed = bots.seeds(DepthFollower, WALL, 1)[0]
    m = feel._canonical(_cfg(), font5x7, DepthFollower, seed, own)
    got = {k: m[k] for k in ("fidelity", "range", "response_ticks", "response_px")}
    assert m["fidelity"] >= 0.8 and m["range"] >= 0.6, f"seed {seed}: {got}"
    assert m["response_ticks"] <= feel.LATENCY_TICKS, f"seed {seed}: {got}"
    assert m["response_px"] >= feel.RESPONSE_PX, f"seed {seed}: {got}"
