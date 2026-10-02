"""Swat (spec 8, game 8; the effects showcase): fruit arcs up and falls, the player's blade (the body's place on the
mat plus the hand's reach) cuts what its swipe crosses, bombs cost, 60 s, two may play and share one score."""
import dataclasses
import itertools
import math
import random
import statistics
import tomllib
import zlib
from pathlib import Path

import numpy as np
import pytest

from arcade import feel
from arcade.attract.lobby import Lobby
from arcade.bots import for_game, seeds
from arcade.calibration import Calibration
from arcade.canvas import Canvas
from arcade.flash import BUDGET, flash_area, square_flashes
from arcade.game import REQUIRED_SCENARIOS, reserved
from arcade.games import MENU_ORDER, get_game
from arcade.games.swat import (BOMB_COST, COMBO, CUT_MIN_PX, CUT_V_MAX, FRUIT_R, GAME, GOAL, OVER_SECONDS,
                               READY_SECONDS, ROUND_SECONDS, SPAWN_Y, Swat)
from arcade.headless import OPENING_NIGHT, run_headless
from arcade.juice import Juice
from arcade.scores import Scores
from arcade.sources.actors import REAL_NOISE, TICK, Person, degrade, scene
from tests.arcade.helpers import make_cfg, played, run

WALL = (128, 64)
ZONE = Calibration().zone
CANONICAL_SECONDS = 70.0


def cam_x(zone_x: float) -> float:
    return ZONE[0] + zone_x * (ZONE[2] - ZONE[0])


def seed(layout: str, i: int) -> int:
    return zlib.crc32(f"swat:{layout}:{i}".encode())


def make(size=WALL, i=0) -> Swat:
    """A Swat reset the way the runner resets it, for tests that poke its state. Its Juice is not advanced by step():
    effects are read from fx.debug_state() on the tick they were called."""
    game = Swat()
    layout = f"{size[0]}x{size[1]}"
    game.scores = Scores(None, lambda: OPENING_NIGHT).for_game("swat", layout)
    game.reset(size, random.Random(seed(layout, i)), Juice(random.Random(1), size))
    return game


def step(game: Swat, frame) -> None:
    bodies = frame.bodies
    game.update(dataclasses.replace(frame, player=bodies[0] if bodies else None,
                                    player2=bodies[1] if len(bodies) > 1 else None), TICK)


def drive(game: Swat, frames, until=None):
    for frame in frames:
        step(game, frame)
        yield frame
        if until is not None and until(game):
            return


def advance(game, frames, phase):
    for _ in drive(game, frames, until=lambda g: g.debug_state()["phase"] == phase):
        pass
    assert game.debug_state()["phase"] == phase, f"never reached {phase}"


def holder(zone_x=0.5, v=0.5, ticks=3000, hand="right"):
    """A body at zone_x holding one hand still at reach-box height v from the start."""
    return scene(persons=[Person(cam_x(zone_x), id=1).wrist(hand, v, v, ticks * TICK, at=0.0)], ticks=ticks)


def stander(zone_x=0.5, ticks=3000):
    return scene(persons=[Person(cam_x(zone_x), id=1)], ticks=ticks)


def playing(frames=None):
    """A game in its play phase, its spawns held off, no fruit, and the frames to go on with."""
    game = make()
    frames = holder() if frames is None else frames
    advance(game, frames, "play")
    game.spawn_in = 1e9
    game.fruit.clear()
    return game, frames


def blade(game, seat=0):
    return game.seats[seat].blade


def fx_calls(game):
    """Wrap the game's Juice so every call is recorded as (name, args, return)."""
    calls = []
    for name in ("flash", "burst", "pop", "banner", "freeze", "shake", "echo", "celebrate"):
        real = getattr(game.fx, name)

        def spy(*args, _real=real, _name=name, **kwargs):
            out = _real(*args, **kwargs)
            calls.append((_name, args, out))
            return out
        setattr(game.fx, name, spy)
    return calls


# ----- registration, the blade -----

def test_registered_and_declared():
    assert get_game("swat") is Swat and GAME is Swat and "swat" in MENU_ORDER
    info = Swat.info
    assert (info.name, info.title, info.verb) == ("swat", "SWAT", "SWAT")
    assert info.needs == frozenset({"pose"}) and info.layouts == frozenset({"128x64"})
    assert info.players == 2 and info.kind == "score"
    assert Swat.PHASES == ("ready", "play", "over")
    assert Swat.CAPTION_KEYS == ("phase", "score", "t_left")
    assert set(Swat.SCENARIOS) == {"canonical", "idle_body", "nobody", "duo"}
    assert (ROUND_SECONDS, READY_SECONDS, FRUIT_R, BOMB_COST, COMBO, CUT_MIN_PX, CUT_V_MAX) == (
        60.0, 3.0, 2, 3, 3, 3, 0.85)


@pytest.mark.parametrize("hand, zone_x, v, x, y", [
    ("right", 0.02, 0.5, 0.0, None),          # the right hand's reach is +12 px: the far left is reachable
    ("left", 0.98, 0.5, 127.0, None),         # and the left hand reaches the far right
    ("right", 0.5, 0.5, 75.5, 29.5),
    ("right", 0.5, 0.0, None, 2.0),           # the reach box's top: the top blade row
    ("right", 0.5, 0.8, None, 2 + (0.8 - 0.15) / 0.7 * 55),
])
def test_blade_follows_body_and_hand(hand, zone_x, v, x, y):
    game = make()
    for _ in drive(game, holder(zone_x, v, ticks=60, hand=hand)):
        pass
    bx, by = blade(game)
    if x is not None:
        assert bx == pytest.approx(x, abs=1.0), (bx, by)
    if y is not None:
        assert by == pytest.approx(y, abs=1.0), (bx, by)
    assert game.debug_state()["blade_xy"] == pytest.approx((bx, by), abs=0.01)


def test_the_body_and_the_hand_span_the_wall_and_the_rows():
    xs, ys = [], []
    for zone_x in (0.0, 0.15, 0.5, 0.85, 1.0):
        for v in (0.0, 0.15, 0.5, 0.85, 1.0):
            game = make()
            for _ in drive(game, holder(zone_x, v, ticks=45)):
                pass
            xs.append(blade(game)[0])
            ys.append(blade(game)[1])
    assert min(xs) <= 1.0 and max(xs) >= 126.0 and min(ys) <= 2.5 and max(ys) >= 56.5, (min(xs), max(xs), min(ys), max(ys))
    assert all(0 <= x <= 127 and 2 <= y <= 57 for x, y in zip(xs, ys))


# ----- cutting -----

def test_a_swipe_through_a_fruit_cuts_it():
    """The segment between two ticks passes the fruit although neither end is on it: a fruit put at the middle of the
    longest segment a fast wrist swipe makes, replayed on a fresh game."""
    def frames():
        return scene(persons=[Person(cam_x(0.5), id=1).wrist("right", 0.5, 0.5, 8.0, at=0.0)
                              .wrist("right", 0.15, 0.85, 0.3, at=8.0)], ticks=400)

    probe, segs = make(), []
    real = probe.swipe
    probe.swipe = lambda seat, a, b, v: (segs.append((a, b, v)) if seat is probe.seats[0] else None, real(seat, a, b, v))[1]
    for _ in drive(probe, frames()):
        pass
    ok = [(k, a, b) for k, (a, b, v) in enumerate(segs)
          if k >= round(8.0 / TICK) and a and b and v < CUT_V_MAX and math.dist(a, b) > 8.0]
    assert ok, "the swipe never made a segment over 8 px"
    k, a, b = ok[0]
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    assert min(math.dist(mid, a), math.dist(mid, b)) > FRUIT_R + 1
    game = make()
    for n, frame in enumerate(frames()):
        if n == k:
            game.spawn_in = 1e9
            game.fruit.clear()
            game.spawn(mid[0], mid[1], 0.0, 0.0)
        step(game, frame)
        if n == k:
            break
    assert game.score == 1 and game.cut == 1 and game.fruit == [], (a, b, mid, game.debug_state())


def test_swipe_is_the_segment_not_the_end_points():
    """swipe(): a fruit between two blade positions, both more than FRUIT_R + 1 from it, is cut; a fruit off the line is not."""
    game, _ = playing()
    seat = game.seats[0]
    game.spawn(60.0, 30.0, 0.0, 0.0)
    game.spawn(60.0, 45.0, 0.0, 0.0)
    game.swipe(seat, (50.0, 30.0), (70.0, 30.0), 0.5)
    assert game.score == 1 and [round(f.y) for f in game.fruit] == [45]


def test_a_slow_hand_cuts_nothing():
    game = make()
    frames = scene(persons=[Person(cam_x(0.5), id=1).wrist("right", 0.4, 0.5, 12.0, at=0.0)], ticks=600)
    advance(game, frames, "play")
    game.spawn_in = 1e9
    moved = []
    for _ in drive(game, frames, until=lambda g: g.t >= 8.0):
        before = blade(game)
        game.fruit.clear()
        game.spawn(blade(game)[0], blade(game)[1], 0.0, 0.0)           # a fruit right under the blade, every tick
        moved.append(before)
    assert game.score == 0 and game.cut == 0, game.debug_state()
    assert max(math.dist(a, b) for a, b in zip(moved, moved[1:])) < CUT_MIN_PX
    assert game.debug_state()["active"] is False


def test_a_hanging_hand_never_cuts():
    """A 24 px blade jump (what a hand swap at v 0.95 does) over a fruit: no cut at v 0.95, a cut at v 0.5."""
    for v, cuts in ((0.95, 0), (CUT_V_MAX, 0), (0.5, 1)):
        game, _ = playing()
        game.spawn(63.0, 56.0, 0.0, 0.0)
        game.swipe(game.seats[0], (51.0, 56.0), (75.0, 56.0), v)
        assert game.score == cuts, (v, game.debug_state())


def test_a_short_move_is_no_swipe():
    game, _ = playing()
    game.spawn(60.0, 30.0, 0.0, 0.0)
    game.swipe(game.seats[0], (59.0, 30.0), (60.0, 30.0), 0.5)             # 1 px: under CUT_MIN_PX
    assert game.score == 0 and len(game.fruit) == 1


# ----- fruit -----

def test_fruit_arcs_up_and_falls_out():
    game = make()
    frames = stander(ticks=3000)
    advance(game, frames, "play")
    tracks: dict[int, list[tuple[float, float]]] = {}
    for _ in drive(game, frames, until=lambda g: g.t >= READY_SECONDS + 22.0):
        for f in game.fruit:
            tracks.setdefault(id(f), []).append((f.x, f.y))
        assert len(game.fruit) <= 9 and all(f.y + FRUIT_R <= 59.5 for f in game.fruit)
    done = [t for t in tracks.values() if t[-1][1] >= SPAWN_Y - 2 and len(t) > 30]
    assert len(done) >= 8, len(tracks)
    for t in done:
        top = min(y for _, y in t)
        assert 8 <= top <= 30, top
        assert all(0 <= x <= 127 for x, _ in t), t[0]
    assert all(y + FRUIT_R <= 59 for t in tracks.values() for _, y in t)       # never into rows 60 to 63
    live = [f for f in game.fruit]
    assert all(f.vy < 0 or f.y < SPAWN_Y for f in live)                          # nothing falling below the spawn row


def test_a_fruit_that_falls_back_to_the_spawn_row_is_gone():
    game, _ = playing(stander())
    game.spawn(30.0, SPAWN_Y - 1.0, 0.0, 20.0)
    for _ in range(5):
        step(game, next(iter(stander(ticks=1))))
    assert game.fruit == []


# ----- bombs, combos, the effects -----

def test_a_bomb_costs_shakes_and_never_flashes(font5x7):
    game, _ = playing()
    calls = fx_calls(game)
    game.score = 5
    game.spawn(60.0, 30.0, 0.0, 0.0, bomb=True)
    game.swipe(game.seats[0], (50.0, 30.0), (70.0, 30.0), 0.5)
    assert game.score == 2 and game.bombs_hit == 1 and game.fruit == []
    game.fx.render(Canvas(*WALL, font5x7))
    keys = game.fx.debug_state()
    assert keys["fx_shake"] != [0, 0] and keys["fx_frozen"] is True and keys["fx_echoes"] == 1, keys
    assert keys["fx_flash"] == 0.0 and not [c for c in calls if c[0] == "flash"]
    game.score = 1
    game.spawn(60.0, 30.0, 0.0, 0.0, bomb=True)
    game.swipe(game.seats[0], (50.0, 30.0), (70.0, 30.0), 0.5)
    assert game.score == 0 and game.bombs_hit == 2


def test_a_combo_flashes_once_and_checks_the_return():
    game, _ = playing()
    calls = fx_calls(game)
    for x in (55.0, 65.0, 75.0):
        game.spawn(x, 30.0, 0.0, 0.0)
    game.swipe(game.seats[0], (45.0, 30.0), (85.0, 30.0), 0.5)
    assert game.score == 3
    flashes = [c for c in calls if c[0] == "flash"]
    assert len(flashes) == 1 and flashes[0][2] is True
    assert ("pop" in [c[0] for c in calls]) and any(c[0] == "pop" and c[1][0] == "COMBO" for c in calls)
    state = game.fx.debug_state()
    assert state["fx_flash"] == 1.0 and state["fx_particles"] == 0, state          # no burst on a flash's tick
    # a second combo at once: flash refuses (False) and the game goes on, bursting as a cut does
    for x in (55.0, 65.0, 75.0):
        game.spawn(x, 40.0, 0.0, 0.0)
    game.swipe(game.seats[0], (85.0, 40.0), (45.0, 40.0), 0.5)
    flashes = [c for c in calls if c[0] == "flash"]
    assert [c[2] for c in flashes] == [True, False] and game.score == 6
    assert game.fx.debug_state()["fx_particles"] > 0


def test_each_effect_fires_on_its_event(font5x7):
    game, _ = playing()
    calls = fx_calls(game)
    game.spawn(60.0, 30.0, 0.0, 0.0)
    game.swipe(game.seats[0], (50.0, 30.0), (70.0, 30.0), 0.5)
    names = [c[0] for c in calls]
    assert "burst" in names and any(c[0] == "pop" and c[1][0] == "+1" for c in calls)
    keys = game.fx.debug_state()
    assert keys["fx_pops"] == 1 and keys["fx_particles"] > 0 and keys["fx_flash"] == 0.0 and keys["fx_frozen"] is False
    game.score = GOAL - 1
    game.spawn(60.0, 40.0, 0.0, 0.0)
    game.swipe(game.seats[0], (50.0, 40.0), (70.0, 40.0), 0.5)
    assert game.score == GOAL and game.fx.debug_state()["fx_banner"] == "GOAL!"
    game.fx.banner("x", 0.0)
    game.spawn(60.0, 20.0, 0.0, 0.0)
    game.swipe(game.seats[0], (50.0, 20.0), (70.0, 20.0), 0.5)
    assert game.fx.debug_state()["fx_banner"] != "GOAL!"                       # once, not on every cut past the goal
    # over: celebrate for a score at the goal, nothing under it
    for score, wave in ((GOAL, True), (GOAL - 1, False)):
        g, frames = playing()
        g.score = score
        g.cut = 1
        g.run_t = ROUND_SECONDS - 0.05
        before = g.fx.debug_state()["fx_particles"]
        advance(g, frames, "over")
        assert (g.fx.debug_state()["fx_particles"] > before) is wave, score


def test_the_ready_counts_3_2_1_go():
    game = make()
    banners = []
    for _ in drive(game, holder(ticks=200), until=lambda g: g.debug_state()["phase"] != "ready"):
        text = game.fx.debug_state()["fx_banner"]
        game.fx.update(TICK)
        if text is not None and (not banners or banners[-1] != text):
            banners.append(text)
    assert banners == ["3", "2", "1", "GO!"], banners
    assert game.t == pytest.approx(READY_SECONDS, abs=2 * TICK)


# ----- the round -----

def test_the_round_ends_at_sixty_seconds_and_done_after_the_hold():
    game, frames = playing()
    assert game.debug_state()["t_left"] == ROUND_SECONDS
    start = game.t
    game.cut = 1
    game.score = 4
    for _ in drive(game, frames, until=lambda g: g.debug_state()["phase"] == "over"):
        pass
    assert game.t - start == pytest.approx(ROUND_SECONDS, abs=2 * TICK)
    state = game.debug_state()
    assert state["phase"] == "over" and state["t_left"] == 0.0 and state["score"] == 4 and not game.done()
    for _ in drive(game, frames, until=lambda g: g.done()):
        pass
    assert game.done() and game.phase_t >= OVER_SECONDS - TICK and game.debug_state()["score"] == 4
    assert game.scores.best() == 4


def test_two_share_one_score_and_record_nothing():
    two = scene(persons=[Person(cam_x(0.3), id=1).wrist("right", 0.5, 0.5, 80, at=0.0),
                         Person(cam_x(0.7), id=2, height=0.55).wrist("right", 0.5, 0.5, 80, at=0.0)], ticks=3000)
    game, frames = playing(two)
    assert game.debug_state()["blade2_xy"] is not None
    game.spawn(30.0, 30.0, 0.0, 0.0)
    game.spawn(90.0, 30.0, 0.0, 0.0)
    game.swipe(game.seats[0], (20.0, 30.0), (40.0, 30.0), 0.5)
    game.swipe(game.seats[1], (80.0, 30.0), (100.0, 30.0), 0.5)
    assert game.score == 2 and game.cut == 2
    game.run_t = ROUND_SECONDS - 0.05
    for _ in drive(game, frames, until=lambda g: g.done()):
        pass
    assert game.done() and game.debug_state()["score"] == 2
    assert game.scores.best() is None


def test_a_second_blade_shows_once_the_second_player_is_seen():
    game = make()
    one = scene(persons=[Person(cam_x(0.3), id=1).wrist("right", 0.5, 0.5, 80, at=0.0)], ticks=100)
    for _ in drive(game, one):
        pass
    assert game.debug_state()["blade2_xy"] is None
    duo = Swat.SCENARIOS["duo"]()
    for _ in drive(game, duo, until=lambda g: g.debug_state()["blade2_xy"] is not None):
        pass
    assert game.debug_state()["blade2_xy"] is not None


# ----- movement (C41, C42), the hint -----

def test_idle_body_scores_nothing(font5x7):
    s = seed("128x64", 2)
    _, game, _ = run(Swat, Swat.SCENARIOS["idle_body"](), WALL, font5x7, ticks=round(20 / TICK), seed=s)
    state = game.debug_state()
    assert state["score"] == 0 and state["cut"] == 0, (s, state)
    assert game.scores.best() is None
    probe = make()
    for _ in drive(probe, Swat.SCENARIOS["idle_body"](), until=lambda g: g.debug_state()["hint"]):
        pass
    assert probe.debug_state()["hint"] is True and probe.t <= 3.0, probe.t


@pytest.mark.parametrize("i", range(5))
@pytest.mark.parametrize("height", [0.6, 0.45])
def test_a_still_body_under_real_noise_scores_nothing(i, height):
    s = seeds(Swat, "128x64", 5)[i]
    person = Person(cam_x(0.3 + 0.1 * i), id=s % 1000 + 1, height=height)
    frames = degrade(scene(persons=[person], ticks=round(25 / TICK)), **REAL_NOISE)
    game = make(i=i)
    active = []
    for f in frames:
        if not f.bodies:
            continue
        step(game, f)
        active.append(game.debug_state()["active"])
    state = game.debug_state()
    assert state["score"] == 0 and state["cut"] == 0 and not any(active) and game.scores.best() is None, (s, height, state)


def test_a_moving_blade_is_active_and_a_still_one_is_not():
    game = make()
    frames = scene(persons=[Person(cam_x(0.5), id=1).wrist("right", 0.2, 0.2, 5.0, at=0.0)
                            .wrist("right", 0.2, 0.8, 0.3, at=5.0)], ticks=300)
    seen = [game.debug_state()["active"] for _ in drive(game, frames)]
    assert any(seen[150:162]) and not any(seen[100:148]) and not any(seen[170:]) and all(type(a) is bool for a in seen)


# ----- the debug state, scenarios, the lobby -----

def test_debug_state_is_clean(font5x7):
    game = make()
    canvas = Canvas(*WALL, font5x7)
    states = []
    for _ in drive(game, Swat.SCENARIOS["duo"](), until=lambda g: g.t >= 25):
        state = game.debug_state()
        states.append(state)
        assert not [k for k in state if reserved(k)], state
        assert type(state["active"]) is bool and type(state["hint"]) is bool
        assert state["phase"] in Swat.PHASES and all(k in state for k in Swat.CAPTION_KEYS)
        canvas.clear()
        game.draw(canvas)
        for key in ("blade_xy", "blade2_xy", "target_xy", "bomb_xy"):
            xy = state[key]
            if xy is None:
                continue
            x, y = xy
            assert 0 <= x < WALL[0] and 0 <= y < WALL[1], (key, state)
            if x >= WALL[0] - 14 and y < 18:                       # under the score's black box, drawn last
                continue
            assert canvas.frame[int(y), int(x)].any(), (key, state)
    assert {"phase", "score", "cut", "bombs_hit", "active", "hint", "t_left", "blade_xy", "blade2_xy", "target_xy",
            "bomb_xy"} <= set(state)
    assert any(s["target_xy"] is not None for s in states) and any(s["bomb_xy"] is not None for s in states)
    assert any(s["blade2_xy"] is not None for s in states)


def test_target_and_bomb_are_the_nearest_to_the_blade():
    game, _ = playing()
    bx, by = blade(game)
    game.spawn(bx + 30, by, 0.0, 0.0)
    game.spawn(bx + 10, by, 0.0, 0.0)
    game.spawn(bx + 50, by, 0.0, 0.0, bomb=True)
    game.spawn(bx + 5, by, 0.0, 0.0, bomb=True)
    state = game.debug_state()
    assert state["target_xy"] == pytest.approx((bx + 10, by), abs=0.01), state
    assert state["bomb_xy"] == pytest.approx((bx + 5, by), abs=0.01), state


def test_score_is_drawn_at_2x_top_right(font5x7):
    game = make()
    game.score = 7
    canvas = Canvas(*WALL, font5x7)
    game.draw(canvas)
    found = feel.find_text(canvas.frame, font5x7, "7", scales=(2,))
    assert found is not None
    x, y, mask = found
    assert y == 1 and mask.shape == (14, 10) and WALL[0] - 13 <= x + 10 <= WALL[0], (x, y)
    assert feel.find_text(canvas.frame, font5x7, "7", scales=(1,)) is None


def test_the_run_bar_and_the_blades_are_drawn(font5x7):
    game, _ = playing(Swat.SCENARIOS["duo"]())
    canvas = Canvas(*WALL, font5x7)
    game.draw(canvas)
    assert tuple(canvas.frame[0, 0]) == (255, 120, 0)
    bx, by = blade(game)
    assert (canvas.frame[round(by) - 1:round(by) + 2, round(bx) - 1:round(bx) + 2] > 0).any(axis=2).all()


def test_required_scenarios_start_with_an_empty_wall():
    assert set(REQUIRED_SCENARIOS) <= set(Swat.SCENARIOS)
    for name in ("idle_body", "nobody", "duo"):
        assert next(iter(Swat.SCENARIOS[name]())), name
    canonical = list(Swat.SCENARIOS["canonical"]())
    assert len(canonical) == round(CANONICAL_SECONDS / TICK)
    assert all(not f.bodies for f in canonical[:round(2.0 / TICK)]) and canonical[round(2.0 / TICK) + 1].bodies
    assert len(list(Swat.SCENARIOS["idle_body"]())) == round(60 / TICK)
    assert all(len(f.bodies) == 2 for f in itertools.islice(Swat.SCENARIOS["duo"](), round(5 / TICK), None))
    assert len(list(Swat.SCENARIOS["nobody"]())) == round(30 / TICK)
    assert all(not f.bodies for f in Swat.SCENARIOS["nobody"]())


def test_canonical_drives_the_lobby_to_swat(font5x7):
    cfg = make_cfg(WALL)
    lobby = Lobby([Swat], cfg)
    window = itertools.islice(Swat.SCENARIOS["canonical"](), round((feel.FEEL_SECONDS + 5) / TICK))
    _, runner = run_headless(cfg, font5x7, [Swat], window, trace=True, lobby=lobby,
                             seed=seeds(Swat, "128x64", 1)[0])
    games = [s["game"] for s in runner.trace]
    assert games[0] == "lobby" and "swat" in games
    first = games.index("swat")
    raised = round(4.5 / TICK)
    assert raised <= first <= raised + 1, (first, raised)
    stop = next((k for k in range(first, len(games)) if games[k] != "swat"), len(games))
    assert stop * TICK >= feel.FEEL_SECONDS, (stop * TICK, [s.get("phase") for s in runner.trace[first:stop]][-5:])
    assert max(s["cut"] for s in runner.trace if s.get("game") == "swat" and "cut" in s) >= 1


@pytest.mark.parametrize("name", ["canonical", "duo"])
def test_own_drawing_keeps_the_flash_rule(font5x7, name):
    s = seed("128x64", 5)
    frames = itertools.islice(Swat.SCENARIOS[name](), round(40 / TICK))      # the ready, the play, the swipes: 40 s
    _, runner = run_headless(make_cfg(WALL), font5x7, Swat, frames, seed=s, raw=True, trace=True)
    raw = runner.raw_frames
    assert len(raw) > 700
    assert flash_area(raw) < 0.1, s
    assert max(st["flash_held_ticks"] for st in runner.trace) == 0, s
    assert square_flashes(raw) <= BUDGET, s


def test_seeded_runs_repeat(font5x7):
    a, _, _ = run(Swat, Swat.SCENARIOS["duo"](), WALL, font5x7, ticks=400, seed=seed("128x64", 6))
    b, _, _ = run(Swat, Swat.SCENARIOS["duo"](), WALL, font5x7, ticks=400, seed=seed("128x64", 6))
    c, _, _ = run(Swat, Swat.SCENARIOS["duo"](), WALL, font5x7, ticks=400, seed=seed("128x64", 7))
    assert all(np.array_equal(x, y) for x, y in zip(a, b))
    assert any(not np.array_equal(x, y) for x, y in zip(a, c))


# ----- bots -----

def test_bots_module_is_found():
    bots, won = for_game(Swat)
    assert set(bots) == {"good", "lazy"} and bots["good"] is not bots["lazy"]
    assert won({"phase": "over", "score": GOAL})
    assert not won({"phase": "over", "score": GOAL - 1})
    assert not won({"phase": "play", "score": GOAL + 3})


def test_good_beats_lazy_beats_nobody():
    ss = seeds(Swat, "128x64", 5)
    wins = {name: sum(played(Swat, name, s).won for s in ss) for name in ("good", "lazy", "none")}
    assert wins["good"] >= 3 and wins["none"] == 0 and wins["lazy"] < wins["good"], (ss, wins)


def test_good_round_length_in_band():
    plays = [played(Swat, "good", s) for s in seeds(Swat, "128x64", 5)]
    lengths = [p.seconds for p in plays if p.done]
    assert len(lengths) >= 4, [(p.seed, p.seconds, p.done) for p in plays]
    assert 20 <= statistics.median(lengths) <= 120, ([p.seed for p in plays], lengths)


def test_feel_file_overrides_have_reasons():
    data = tomllib.loads((Path(__file__).resolve().parents[2] / "arcade/games/swat_feel.toml").read_text())
    assert data["fidelity"] == {"input": "cursor_y", "xy": "blade_xy", "axis": 1}
    assert "budgets" not in data                                   # the plan: no budget override
    for metric, table in data.get("budgets", {}).get("128x64", {}).items():
        assert table.get("reason", "").strip(), metric


@pytest.mark.parametrize("name", ["canonical", "duo"])
def test_own_drawing_keeps_rows_60_to_63_dark(font5x7, name):
    """The runner's marker and echoes own rows 60 to 63: no phase of Swat's own drawing lights them."""
    game = make(i=2)
    canvas = Canvas(*WALL, font5x7)
    lit = []
    for _ in drive(game, Swat.SCENARIOS[name]()):
        canvas.clear()
        game.draw(canvas)
        if canvas.frame[60:].any():
            lit.append(round(game.t, 2))
    assert game.t > READY_SECONDS
    assert not lit, f"{name}: rows 60 to 63 lit on {len(lit)} ticks, from t {lit[:3]}"
