"""Dodge (spec 8, game 5; side steps only, Q70): rocks fall, the player's block follows the body's x across the mat,
a run ends on the first hit or survives RUN_SECONDS."""
import dataclasses
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
from arcade.bots import Nobody, for_game, seeds
from arcade.calibration import Calibration
from arcade.canvas import Canvas
from arcade.flash import BUDGET, flash_area, square_flashes
from arcade.game import REQUIRED_SCENARIOS, reserved
from arcade.games import MENU_ORDER, get_game
from arcade.games import dodge
from arcade.games.dodge import (ACTIVE_PX, AIM_EVERY, DODGE_TRAVEL_PX, GAME, HINT_IDLE_SECONDS, HIT_SECONDS,
                                HIT_SLACK, OVER_SECONDS, PLAYER_H, PLAYER_W, PLAYER_Y, READY_SECONDS, ROCK_H,
                                ROCK_SPEED, ROCK_W, RUN_SECONDS, SPAWN_EVERY, Dodge)
from arcade.headless import OPENING_NIGHT, run_headless
from arcade.juice import PLAYER_COLORS, Juice
from arcade.scores import Scores
from arcade.sources.actors import REAL_NOISE, TICK, Person, degrade, scene
from tests.arcade.helpers import make_cfg, played, run

WALL = (128, 64)
ZONE = Calibration().zone            # the camera-x span of the mat: a body at camera x is at (x - x0) / (x1 - x0)
CANONICAL_SECONDS = 55.0
MAT_MAX = WALL[0] - PLAYER_W         # the block's left edge at the far wall


def cam_x(zone_x: float) -> float:
    """The camera x a Person stands at to be at zone_x on the mat."""
    return ZONE[0] + zone_x * (ZONE[2] - ZONE[0])


def seed(layout: str, i: int) -> int:
    return zlib.crc32(f"dodge:{layout}:{i}".encode())


def make(size=WALL, i=0) -> Dodge:
    """A Dodge reset the way the runner resets it, for tests that poke its state."""
    game = Dodge()
    layout = f"{size[0]}x{size[1]}"
    game.scores = Scores(None, lambda: OPENING_NIGHT).for_game("dodge", layout)
    game.reset(size, random.Random(seed(layout, i)), Juice(random.Random(1), size))
    return game


def step(game: Dodge, frame) -> None:
    """One tick with the runner's lock applied: the largest body is the player."""
    bodies = frame.bodies
    game.update(dataclasses.replace(frame, player=bodies[0] if bodies else None,
                                    player2=bodies[1] if len(bodies) > 1 else None), TICK)


def drive(game: Dodge, frames, until=None):
    """Steps game over frames, yielding after each; stops after the tick where until(game) is true."""
    for frame in frames:
        step(game, frame)
        yield frame
        if until is not None and until(game):
            return


def advance(game, frames, phase):
    for _ in drive(game, frames, until=lambda g: g.debug_state()["phase"] == phase):
        pass
    assert game.debug_state()["phase"] == phase, f"never reached {phase}"


def stander(zone_x=0.5, ticks=3000):
    """A body standing still, hands down, at zone_x on the mat."""
    return scene(persons=[Person(cam_x(zone_x), id=1)], ticks=ticks)


def playing(zone_x=0.5, ticks=3000):
    """A game in its play phase with a still player at zone_x, its spawns held off, and the frames to go on with."""
    game = make()
    frames = stander(zone_x, ticks)
    advance(game, frames, "play")
    game.spawn_in = 1e9
    game.rocks.clear()
    return game, frames


def block_centre(game) -> float:
    return game.debug_state()["player_xy"][0]


def from_first_body(frames):
    started = False
    for f in frames:
        started = started or bool(f.bodies)
        if started:
            yield f


# ----- registration, control -----

def test_registered_and_declared():
    assert get_game("dodge") is Dodge and GAME is Dodge and "dodge" in MENU_ORDER
    info = Dodge.info
    assert (info.name, info.title, info.verb) == ("dodge", "DODGE", "DODGE")
    assert info.needs == frozenset({"pose"}) and info.layouts == frozenset({"128x64"})
    assert info.players == 1 and info.kind == "score"
    assert Dodge.PHASES == ("ready", "play", "hit", "over")
    assert Dodge.CAPTION_KEYS == ("phase", "score", "speed")
    assert set(Dodge.SCENARIOS) == {"canonical", "idle_body", "nobody", "solo"}
    assert (RUN_SECONDS, PLAYER_W, PLAYER_H, ROCK_W, ROCK_H) == (45.0, 6, 8, 6, 4)
    assert (ROCK_SPEED, SPAWN_EVERY, AIM_EVERY, HIT_SLACK) == ((20.0, 38.0, 56.0), (1.2, 0.4), 3, 2)
    assert (dodge.KNEE_SECONDS, dodge.AIM_TIGHT_AT, dodge.AIM_TIGHT_EVERY) == (30.0, 25.0, 2)


@pytest.mark.parametrize("zone_x, left", [(0.15, 0.0), (0.5, MAT_MAX / 2), (0.85, MAT_MAX),
                                          (0.02, 0.0), (0.98, MAT_MAX)])
def test_block_follows_zone_x(font5x7, zone_x, left):
    """0.15 to 0.85 of the mat spans the wall; past either end the block stays at the wall."""
    _, game, _ = run(Dodge, stander(zone_x, ticks=45), WALL, font5x7, seed=seed("128x64", 1))
    assert block_centre(game) == pytest.approx(left + PLAYER_W / 2, abs=1.0), game.debug_state()


def test_block_glides_between_captures():
    """C46/C44: zone_x goes through a Glide, so the block moves on nearly every tick of a walk although the camera
    (10 fps) shows a new capture every third tick."""
    game = make()
    p = Person(cam_x(0.2), id=1).walk(cam_x(0.8), 4.0, at=1.0)
    frames = degrade(scene(persons=[p], ticks=210), **REAL_NOISE)
    xs = [block_centre(game) for _ in drive(game, from_first_body(frames))]
    moving = [b - a for a, b in zip(xs[60:160], xs[61:161])]
    assert sum(abs(d) > 0.05 for d in moving) >= 85, sum(abs(d) > 0.05 for d in moving)


# ----- the rocks -----

def rock_at(game, dx: int, y=52.0):
    """A rock whose left edge is dx px to the right of the block's, at y (top)."""
    game.rocks.clear()
    game.spawn_rock(game.block_x + dx)
    game.rocks[0].y = y
    return game.rocks[0]


@pytest.mark.parametrize("overlap, hit", [(2, False), (3, True)])
def test_a_rock_on_the_block_ends_the_run(overlap, hit):
    """HIT_SLACK: a rock overlapping the block by 2 px is a graze, by 3 px a hit."""
    game, frames = playing()
    rock_at(game, PLAYER_W - overlap)
    step(game, next(frames))
    assert (game.debug_state()["phase"] == "hit") is hit, (overlap, game.debug_state())
    game, frames = playing()
    rock_at(game, -(ROCK_W - overlap))                   # the same from the left
    step(game, next(frames))
    assert (game.debug_state()["phase"] == "hit") is hit, (overlap, game.debug_state())


def test_a_rock_high_above_or_already_past_is_no_hit():
    game, frames = playing()
    rock_at(game, 0, y=30.0)
    step(game, next(frames))
    assert game.debug_state()["phase"] == "play"


def test_an_aimed_rock_falls_at_the_player():
    """Every third spawn (the first, the fourth, ...) is placed at the block's x at its spawn; the rest at random."""
    game = make()
    frames = stander(0.3, ticks=3000)
    seen, spawned = [], 0
    for _ in drive(game, frames, until=lambda g: len(seen) >= 9):
        for rock in game.rocks:
            if rock not in seen:
                seen.append(rock)
                assert (rock.x + ROCK_W / 2 == pytest.approx(game.block_x + PLAYER_W / 2, abs=0.5)) \
                    is (len(seen) % AIM_EVERY == 1), (len(seen), rock.x, game.block_x)
        game.rocks.clear()                                # nothing hits: the player is never under a rock
    assert len(seen) == 9 and len({round(r.x) for r in seen}) > 3


def test_speed_and_spawns_ramp():
    """Two segments (the 2026-10-03 review): easier early, much harder late, with the knee at 30 s."""
    assert dodge.speed_at(0.0) == pytest.approx(20.0) and dodge.speed_at(RUN_SECONDS) == pytest.approx(56.0)
    assert dodge.speed_at(15.0) == pytest.approx(29.0) and dodge.speed_at(30.0) == pytest.approx(38.0)
    assert dodge.speed_at(37.5) == pytest.approx(47.0)
    assert dodge.spawn_gap(0.0) == pytest.approx(1.2) and dodge.spawn_gap(RUN_SECONDS) == pytest.approx(0.4)
    assert dodge.spawn_gap(RUN_SECONDS / 2) == pytest.approx(0.8)
    game, frames = playing()
    game.spawn_in = 0.0
    game.run_t = 0.0
    step(game, next(frames))
    rock = game.rocks[0]
    step(game, next(frames))
    assert rock.y - (-ROCK_H / 2) == pytest.approx(2 * 20.0 * TICK, abs=0.05), rock.y          # 2 ticks at 20 px/s
    assert game.spawn_in == pytest.approx(1.2 - TICK, abs=0.05)
    game.run_t = RUN_SECONDS - 1.0
    game.rocks.clear()
    y0 = rock.y
    game.rocks.append(rock)
    step(game, next(frames))
    assert rock.y - y0 == pytest.approx(dodge.speed_at(RUN_SECONDS - 1.0) * TICK, abs=0.1), rock.y - y0
    assert game.debug_state()["speed"] == pytest.approx(dodge.speed_at(game.run_t), abs=0.01)


def test_spawns_follow_the_gap_of_the_run_time():
    game, frames = playing()
    game.spawn_in = 0.0
    times = []
    for _ in drive(game, frames, until=lambda g: len(times) >= 6):
        if game.rocks:
            times.append(game.run_t)
            game.rocks.clear()
    for a, b in zip(times, times[1:]):
        assert b - a == pytest.approx(dodge.spawn_gap(a), abs=2 * TICK), times


# ----- score and the end of a run -----

def test_score_counts_dodges_with_travel():
    game, frames = playing(0.4)
    game.spawn_rock(1.0)                                 # far from the player, at the top
    still = game.rocks[0]
    still.y = 44.0
    game.spawn_rock(WALL[0] - 20.0)
    moved = game.rocks[1]
    moved.y = 44.0
    moved.lo, moved.hi = game.block_x, game.block_x + DODGE_TRAVEL_PX     # the player has moved that far since
    for _ in drive(game, frames, until=lambda g: not g.rocks):
        pass
    assert game.debug_state()["phase"] == "play"
    assert game.debug_state()["score"] == 1, game.debug_state()


def test_surviving_the_run_wins_and_done_after_the_hold():
    game, frames = playing()
    game.run_t = RUN_SECONDS - 0.5
    for _ in drive(game, frames, until=lambda g: g.debug_state()["phase"] == "over"):
        pass
    state = game.debug_state()
    assert state["phase"] == "over" and state["survived"] is True and state["t_left"] == 0.0, state
    assert not game.done()
    for _ in drive(game, frames, until=lambda g: g.done()):
        pass
    assert game.done() and game.phase_t >= OVER_SECONDS - TICK
    assert game.debug_state()["survived"] is True


def test_a_hit_goes_to_hit_then_over_then_done():
    game, frames = playing()
    game.score = 4
    rock_at(game, 0)
    seen = []
    for _ in drive(game, frames, until=lambda g: g.done()):
        phase = game.debug_state()["phase"]
        if not seen or seen[-1] != phase:
            seen.append(phase)
    assert seen == ["hit", "over"], seen
    state = game.debug_state()
    assert state["survived"] is False and state["score"] == 4, state
    assert game.scores.best() == 4


def test_hit_lasts_hit_seconds_and_the_block_fades_red(font5x7):
    game, frames = playing()
    rock_at(game, 0)
    colours = []
    canvas = Canvas(*WALL, font5x7)
    for _ in drive(game, frames, until=lambda g: g.debug_state()["phase"] == "over"):
        canvas.clear()
        game.draw(canvas)
        if game.debug_state()["phase"] == "hit":
            x, y = game.debug_state()["player_xy"]
            colours.append(tuple(canvas.frame[int(y), int(x)]))
    assert HIT_SECONDS / TICK - 2 <= len(colours) <= HIT_SECONDS / TICK + 2, len(colours)
    assert colours[0] == (255, 0, 0) and all(c[1] == c[2] == 0 for c in colours), colours
    reds = [c[0] for c in colours]
    assert all(b <= a for a, b in zip(reds, reds[1:])) and reds[-1] < reds[0] // 2, reds


def test_score_is_drawn_at_2x_top_right(font5x7):
    game = make()
    game.score = 7
    canvas = Canvas(*WALL, font5x7)
    game.draw(canvas)
    found = feel.find_text(canvas.frame, font5x7, "7", scales=(2,))
    assert found is not None
    x, y, mask = found
    assert y == 1 and mask.shape == (14, 10) and x + 10 >= WALL[0] - 3 and x + 10 <= WALL[0], (x, y)
    assert feel.find_text(canvas.frame, font5x7, "7", scales=(1,)) is None


def test_ready_shows_the_hint_text_for_two_seconds(font5x7):
    game = make()
    assert game.debug_state()["phase"] == "ready"
    canvas = Canvas(*WALL, font5x7)
    game.draw(canvas)
    assert feel.find_text(canvas.frame, font5x7, "STEP SIDE", scales=(1,)) is not None
    assert feel.find_text(canvas.frame, font5x7, "TO SIDE", scales=(1,)) is not None
    frames = stander(ticks=200)
    for _ in drive(game, frames, until=lambda g: g.debug_state()["phase"] != "ready"):
        pass
    assert game.t == pytest.approx(READY_SECONDS, abs=2 * TICK)
    game.spawn_in = 1e9
    canvas.clear()
    game.draw(canvas)
    assert feel.find_text(canvas.frame, font5x7, "STEP SIDE", scales=(1,)) is None


def test_safe_is_drawn_at_2x_and_the_run_bar_shrinks(font5x7):
    game, frames = playing()
    canvas = Canvas(*WALL, font5x7)
    game.draw(canvas)
    full = int((canvas.frame[0] > 0).any(axis=1).sum())
    game.run_t = RUN_SECONDS / 2
    canvas.clear()
    game.draw(canvas)
    half = int((canvas.frame[0] > 0).any(axis=1).sum())
    assert full == WALL[0] - dodge.BAR_RESERVE and half == pytest.approx(full / 2, abs=2), (full, half)
    game.run_t = RUN_SECONDS - 0.05
    advance(game, frames, "over")
    canvas.clear()
    game.draw(canvas)
    assert feel.find_text(canvas.frame, font5x7, "SAFE!", scales=(2,)) is not None


# ----- movement (C41, C42), the hint, leaving -----

def test_idle_body_scores_nothing(font5x7):
    s = seed("128x64", 2)
    _, game, _ = run(Dodge, Dodge.SCENARIOS["idle_body"](), WALL, font5x7, seed=s)
    state = game.debug_state()
    assert state["phase"] == "over" and state["score"] == 0 and state["survived"] is False, (s, state)
    assert game.scores.best() is None
    probe = make()
    for _ in drive(probe, Dodge.SCENARIOS["idle_body"](), until=lambda g: g.debug_state()["hint"]):
        pass
    assert probe.debug_state()["hint"] is True and probe.t <= 3.0, probe.t
    assert HINT_IDLE_SECONDS - TICK <= probe.t


def _still_under_noise(i: int):
    s = seeds(Dodge, "128x64", 5)[i]
    person = Person(cam_x(0.3 + 0.1 * i), id=s % 1000 + 1)
    return s, from_first_body(degrade(scene(persons=[person], ticks=round(60 / TICK)), **REAL_NOISE))


@pytest.mark.parametrize("i", range(5))
def test_a_still_body_under_real_noise_scores_nothing(i):
    s, frames = _still_under_noise(i)
    game = make(i=i)
    for _ in drive(game, frames, until=lambda g: g.done()):
        pass
    state = game.debug_state()
    assert game.done() and state["score"] == 0 and game.scores.best() is None, (s, state)


def test_a_still_body_under_real_noise_is_not_input():
    s, frames = _still_under_noise(1)
    game = make(i=1)
    active = []
    for _ in drive(game, frames, until=lambda g: g.t >= 5.0):
        active.append(game.debug_state()["active"])
    assert not any(active), (s, active.index(True) * TICK)
    stepper = make()
    seen = [stepper.debug_state()["active"] for _ in drive(stepper, scene(persons=[
        Person(cam_x(0.3), id=1).walk(cam_x(0.6), 1.0, at=1.0)], ticks=120))]
    assert any(seen) and all(type(a) is bool for a in seen)


def test_a_player_who_leaves_ends_nothing_by_itself():
    """Nobody in view holds the rocks for the grace, then the run goes on; done() stays False with no exception."""
    game = make()
    frames = scene(persons=[Person(cam_x(0.3), id=1).leave(6.0)], ticks=600)
    advance(game, frames, "play")
    game.spawn_in = 1e9
    for _ in drive(game, frames, until=lambda g: g.t >= 6.0):
        pass
    game.spawn_rock(100.0)
    game.rocks[0].y = 20.0
    step(game, next(frames))                                   # the first tick with nobody
    y, run_t = game.rocks[0].y, game.run_t
    for _ in drive(game, frames, until=lambda g: g.t >= 6.0 + 0.3):
        pass
    assert game.rocks[0].y == y and game.run_t == run_t          # held, not falling
    for _ in drive(game, frames, until=lambda g: g.t >= 6.0 + 1.5):
        pass
    assert game.rocks[0].y > y and game.run_t > run_t and not game.done()      # the run goes on
    assert game.debug_state()["phase"] == "play"


# ----- the debug state, scenarios, the lobby -----

def test_debug_state_is_clean(font5x7):
    game = make()
    canvas = Canvas(*WALL, font5x7)
    states = []
    for _ in drive(game, Dodge.SCENARIOS["solo"](), until=lambda g: g.done()):
        state = game.debug_state()
        states.append(state)
        assert not [k for k in state if reserved(k)], state
        assert type(state["active"]) is bool and type(state["hint"]) is bool
        assert state["phase"] in Dodge.PHASES and all(k in state for k in Dodge.CAPTION_KEYS)
        canvas.clear()
        game.draw(canvas)
        for key in ("player_xy", "threat_xy"):
            xy = state[key]
            if xy is None or (key == "player_xy" and state["phase"] == "over"):      # a hit block has faded away
                continue
            x, y = xy
            assert 0 <= x < WALL[0] and 0 <= y < WALL[1], (key, state)
            assert canvas.frame[int(y), int(x)].any(), (key, state)
    assert {"phase", "score", "active", "hint", "speed", "survived", "player_xy", "threat_xy", "t_left"} <= set(state)
    assert any(s["threat_xy"] is not None for s in states)


def test_threat_is_the_lowest_rock_over_the_block():
    game, frames = playing()
    rock_at(game, 0, y=10.0)
    game.spawn_rock(game.block_x + 1)
    game.rocks[1].y = 30.0
    game.spawn_rock(game.block_x + PLAYER_W + 4 + ROCK_W)      # beyond the widened columns
    game.rocks[2].y = 45.0
    game.spawn_rock(game.block_x + PLAYER_W + 3)               # inside the 4 px widening
    game.rocks[3].y = 40.0
    xy = game.debug_state()["threat_xy"]
    assert xy == pytest.approx((game.rocks[3].x + ROCK_W / 2, 40.0 + ROCK_H / 2), abs=0.01), xy
    game.rocks.clear()
    assert game.debug_state()["threat_xy"] is None


def test_rocks_lists_every_rock_centre_for_the_bots():
    game, _ = playing()
    assert game.debug_state()["rocks"] == ()
    game.spawn_rock(10.0)
    game.spawn_rock(90.0)
    game.rocks[1].y = 30.0
    assert game.debug_state()["rocks"] == ((13.0, -2.0 + ROCK_H / 2, 6), (93.0, 30.0 + ROCK_H / 2, 6))


def test_the_step_hint_is_drawn_over_the_player_when_wanted(font5x7):
    game, frames = playing()
    assert game.debug_state()["hint"] is True                 # 2 s of ready with a still body
    canvas = Canvas(*WALL, font5x7)
    game.draw(canvas)
    x, y, mask = feel.find_text(canvas.frame, font5x7, "STEP!", scales=(1,))
    assert abs(x + mask.shape[1] / 2 - block_centre(game)) <= 2 and y + mask.shape[0] < PLAYER_Y, (x, y)
    game._hint = False
    canvas.clear()
    game.draw(canvas)
    assert feel.find_text(canvas.frame, font5x7, "STEP!", scales=(1,)) is None


def test_canonical_steps_out_from_under_the_aimed_rocks(font5x7):
    """The script sweeps the mat and then dodges the aimed rocks by its own timing: the game sees no aimed hit in
    the measured window (the random rocks are luck), and the sweep covers the whole mat."""
    landings = dodge.aimed_landings(4.5 + READY_SECONDS, feel.FEEL_SECONDS)
    assert len(landings) >= 4 and all(a < b < c for a, b, c in landings), landings
    frames = list(Dodge.SCENARIOS["canonical"]())
    xs = [f.bodies[0].zone_x for f in frames if f.bodies]
    assert min(xs) < 0.05 and max(xs) > 0.95, (min(xs), max(xs))


def test_required_scenarios_start_with_an_empty_wall():
    assert set(REQUIRED_SCENARIOS) <= set(Dodge.SCENARIOS)
    for name in Dodge.SCENARIOS:
        assert list(Dodge.SCENARIOS[name]()), name
    canonical = list(Dodge.SCENARIOS["canonical"]())
    assert len(canonical) == round(CANONICAL_SECONDS / TICK)
    assert all(not f.bodies for f in canonical[:round(2.0 / TICK)]) and canonical[round(2.0 / TICK) + 1].bodies
    assert len(list(Dodge.SCENARIOS["idle_body"]())) == round(60 / TICK)
    assert len(list(Dodge.SCENARIOS["nobody"]())) == round(30 / TICK)
    assert all(not f.bodies for f in Dodge.SCENARIOS["nobody"]())


def test_canonical_drives_the_lobby_to_dodge_and_survives_the_measured_window(font5x7):
    cfg = make_cfg(WALL)
    lobby = Lobby([Dodge], cfg)
    _, runner = run_headless(cfg, font5x7, [Dodge], Dodge.SCENARIOS["canonical"](), trace=True, lobby=lobby,
                             seed=seeds(Dodge, "128x64", 1)[0])
    games = [s["game"] for s in runner.trace]
    assert games[0] == "lobby" and "dodge" in games
    first = games.index("dodge")
    raised = round(4.5 / TICK)
    assert raised <= first <= raised + 1, (first, raised)
    stop = next((k for k in range(first, len(games)) if games[k] != "dodge"), len(games))
    assert stop * TICK >= feel.FEEL_SECONDS, (stop * TICK, [s.get("phase") for s in runner.trace[first:stop]][-5:])


def test_solo_ends_in_a_hit(font5x7):
    s = seed("128x64", 3)
    _, game, _ = run(Dodge, Dodge.SCENARIOS["solo"](), WALL, font5x7, seed=s)
    state = game.debug_state()
    assert game.done() and state["survived"] is False, (s, state)


@pytest.mark.parametrize("name", ["canonical", "solo"])
def test_own_drawing_keeps_the_flash_rule(font5x7, name):
    s = seed("128x64", 5)
    _, runner = run_headless(make_cfg(WALL), font5x7, Dodge, Dodge.SCENARIOS[name](), seed=s, raw=True)
    raw = runner.raw_frames
    assert len(raw) > 300
    assert flash_area(raw) == 0.0, s
    assert square_flashes(raw) <= BUDGET, s


def test_seeded_runs_repeat(font5x7):
    a, _, _ = run(Dodge, Dodge.SCENARIOS["solo"](), WALL, font5x7, ticks=400, seed=seed("128x64", 6))
    b, _, _ = run(Dodge, Dodge.SCENARIOS["solo"](), WALL, font5x7, ticks=400, seed=seed("128x64", 6))
    c, _, _ = run(Dodge, Dodge.SCENARIOS["solo"](), WALL, font5x7, ticks=400, seed=seed("128x64", 7))
    assert all(np.array_equal(x, y) for x, y in zip(a, b))
    assert any(not np.array_equal(x, y) for x, y in zip(a, c))


# ----- bots -----

def test_bots_module_is_found():
    bots, won = for_game(Dodge)
    assert set(bots) == {"good", "lazy"} and bots["good"] is not bots["lazy"]
    assert won({"phase": "over", "survived": True})
    assert not won({"phase": "over", "survived": False})
    assert not won({"phase": "play", "survived": False})


def test_good_beats_lazy_beats_nobody():
    ss = seeds(Dodge, "128x64", 5)
    wins = {name: sum(played(Dodge, name, s).won for s in ss) for name in ("good", "lazy", "none")}
    assert wins["good"] >= 4 and wins["none"] == 0 and wins["lazy"] < wins["good"], (ss, wins)


def test_good_round_length_in_band():
    plays = [played(Dodge, "good", s) for s in seeds(Dodge, "128x64", 5)]
    lengths = [p.seconds for p in plays if p.done]
    assert len(lengths) >= 4, [(p.seed, p.seconds, p.done) for p in plays]
    assert 20 <= statistics.median(lengths) <= 120, ([p.seed for p in plays], lengths)


def test_feel_file_overrides_have_reasons():
    data = tomllib.loads((Path(__file__).resolve().parents[2] / "arcade/games/dodge_feel.toml").read_text())
    assert data["fidelity"] == {"input": "zone_x", "xy": "player_xy", "axis": 0}
    assert "budgets" not in data                                   # the plan: no budget override
    for metric, table in data.get("budgets", {}).get("128x64", {}).items():
        assert table.get("reason", "").strip(), metric


def test_the_player_is_the_man_centred_on_the_hitbox(font5x7):
    """The Burning Man figure (the owner, 2026-10-03, after a three-lens review): a 10x12 sprite at rows 46 to 57,
    centred on the unchanged 6x8 hitbox, its 6 px base exactly the hitbox's columns, its spine through row 54 (the
    centre pixel the debug_state's player_xy names), and its x rounded by the canvas as the block's was."""
    from arcade.games.dodge import MAN, MAN_H, MAN_W
    assert MAN.shape == (MAN_H, MAN_W) == (12, 10) and MAN.dtype == bool
    assert list(np.flatnonzero(MAN[-1])) == [2, 3, 4, 5, 6, 7], "the base is the hitbox's 6 columns"
    assert list(np.flatnonzero(MAN[8])) == [4, 5], "the spine runs through row 54"
    assert not MAN[2, 3:7].any() and MAN[0, 4:6].all(), "a head apart from the shoulders"
    for block_x in (40.0, 40.5, 0.0, 122.0):
        game = make()
        game.block_x = block_x
        canvas = Canvas(*WALL, font5x7)
        canvas.clear()
        game.draw(canvas)
        left = math.floor(block_x - 2 + 0.5)                   # the canvas rounds half up, as fill_rect did
        window = canvas.frame[46:58, max(0, left):left + MAN_W]
        skip = max(0, -left)
        mask = MAN[:, skip:skip + window.shape[1]]
        assert np.array_equal(np.all(window == PLAYER_COLORS[0], axis=2), mask), block_x
        assert np.array_equal(window.any(axis=2), mask), "nothing else lit there"
        base_cols = np.flatnonzero(np.all(canvas.frame[57] == PLAYER_COLORS[0], axis=1))
        hit_left = math.floor(block_x + 0.5)
        assert list(base_cols) == list(range(hit_left, hit_left + PLAYER_W)), block_x
        x, y = game.debug_state()["player_xy"]
        assert tuple(canvas.frame[int(y), int(x)]) == PLAYER_COLORS[0]
    assert not np.any(canvas.frame[44:46, 110:128].any()), "nothing above row 46 near the figure"


# ----- harder (the owner, 2026-10-03): sizes, gates, the reach, the late cadence -----


def test_the_aimed_cadence_tightens_late():
    assert dodge.aim_every(0.0) == 3 and dodge.aim_every(24.9) == 3 and dodge.aim_every(25.0) == 2


def test_rock_sizes_arrive_on_a_schedule_and_aimed_rocks_stay_small():
    """Rocks from the start (the opening is the old game's), pebbles and slabs from 10 s, beams from 20 s; every
    aimed rock is the 6x4 rock, so the canonical script's arithmetic holds."""
    assert dodge.SIZES == {"pebble": (3, 3), "rock": (6, 4), "slab": (12, 4), "beam": (24, 3)}
    assert dodge.SIZE_FROM == {"pebble": 10.0, "rock": 0.0, "slab": 10.0, "beam": 20.0}
    game = make()
    frames = stander(0.3, ticks=3000)
    seen = []
    for _ in drive(game, frames, until=lambda g: g.run_t >= 44.0):
        for rock in game.rocks:
            if rock not in seen:
                seen.append((game.run_t, rock))
        game.rocks.clear()                                # nothing hits: the player is never under a rock
    n = 0
    for t, rock in seen:
        aimed = n % dodge.aim_every(t) == 0
        n += 1
        if aimed:
            assert (rock.w, rock.h) == (ROCK_W, ROCK_H) and rock.gap is None, (t, rock.w, rock.h)
        elif rock.gap is None:
            assert (rock.w, rock.h) in dodge.SIZES.values(), (rock.w, rock.h)
            name = next(k for k, v in dodge.SIZES.items() if v == (rock.w, rock.h))
            assert t >= dodge.SIZE_FROM[name], (t, name)
    sizes = {(r.w, r.h) for t, r in seen if r.gap is None}
    assert len(sizes) == 4, sizes
    assert any(r.gap is not None for t, r in seen), "a gate came"
    assert all(t >= dodge.GATE_AFTER for t, r in seen if r.gap is not None)


def test_a_wide_rock_and_a_pebble_hit_by_the_same_overlap_rule():
    game, frames = playing()
    game.spawn_rock(game.block_x - 10, w=24, h=3)        # a beam over the block
    game.rocks[0].y = 52.0
    step(game, next(frames))
    assert game.debug_state()["phase"] == "hit"
    game, frames = playing()
    game.spawn_rock(game.block_x + 1, w=3, h=3)          # a pebble inside the columns: a hit
    game.rocks[0].y = 52.0
    step(game, next(frames))
    assert game.debug_state()["phase"] == "hit"
    game, frames = playing()
    game.spawn_rock(game.block_x - 1, w=3, h=3)          # a pebble on the edge: a graze, the decoy
    game.rocks[0].y = 52.0
    step(game, next(frames))
    assert game.debug_state()["phase"] == "play"


def test_a_gate_is_one_rock_with_a_gap_that_scores_once():
    game, frames = playing(0.4)
    bx = game.block_x
    game.spawn_gate(bx - 4.0)                            # the 14 px gap opens 4 px left of the block: it stands inside
    assert len(game.rocks) == 1 and game.spawned == 1
    gate = game.rocks[0]
    assert gate.gap == (bx - 4.0, dodge.GAP_W) and (gate.x, gate.w) == (0.0, WALL[0])
    rocks = game.debug_state()["rocks"]
    right = bx - 4.0 + dodge.GAP_W
    assert rocks == ((round((bx - 4.0) / 2, 1), -1.5 + 1.5, round(bx - 4.0, 1)),
                     (round((right + WALL[0]) / 2, 1), -1.5 + 1.5, round(WALL[0] - right, 1))), rocks
    gate.y = 52.0
    step(game, next(frames))
    assert game.debug_state()["phase"] == "play", "the block stands in the gap"
    gate.lo, gate.hi = bx, bx + DODGE_TRAVEL_PX
    gate.y = 60.0
    step(game, next(frames))
    assert game.debug_state()["score"] == 1 and not game.rocks
    game, frames = playing(0.4)
    game.spawn_gate(game.block_x + 20.0)
    game.rocks[0].y = 52.0
    step(game, next(frames))
    assert game.debug_state()["phase"] == "hit", "under a beam of the gate"


def test_the_reach_is_what_a_body_covers_before_the_rock_lands():
    """(fall time - 0.6 s of reaction and camera lag) * 87 px/s, floored at 8: a step, never a teleport."""
    fall = (PLAYER_Y - ROCK_H + HIT_SLACK - dodge.SPAWN_Y) / 56.0
    assert dodge.reach(56.0) == pytest.approx((fall - dodge.DEAD_SECONDS) * dodge.BODY_PX_PER_S, abs=0.5)
    assert dodge.reach(20.0) > dodge.reach(38.0) > dodge.reach(56.0) > 8.0
    assert dodge.reach(500.0) == 8.0


def test_a_gate_s_gap_is_within_reach_and_on_the_wall():
    for zone_x in (0.15, 0.5, 0.85):
        game, _ = playing(zone_x)
        game.run_t = 40.0
        centre = game.block_x + PLAYER_W / 2
        for _ in range(60):
            game.rocks.clear()
            game.spawn_gate()
            gx, gw = game.rocks[0].gap
            assert gw == dodge.GAP_W and dodge.GAP_MARGIN <= gx and gx + gw <= WALL[0] - dodge.GAP_MARGIN, gx
            assert abs(gx + gw / 2 - centre) <= dodge.reach(dodge.speed_at(40.0)) + 1e-6, (zone_x, gx)


def test_a_random_spawn_leaves_an_escape_within_reach():
    game, _ = playing()
    assert game.escapable(game.block_x, ROCK_W)
    game.spawn_rock(0.0, w=WALL[0], h=3)                 # a wall-wide bar already falling: nowhere to go
    game.rocks[0].y = 20.0
    assert not game.escapable(game.block_x + 40, ROCK_W)
    game.rocks.clear()
    game.spawn_gate(game.block_x)                        # a gate whose gap is at the block
    assert game.escapable(game.block_x + 40, ROCK_W)
    game, _ = playing()
    game.run_t = 40.0
    for _ in range(200):                                 # with rocks in flight the next one still leaves a way out
        game.spawn_random()
        new = game.rocks[-1]
        for r in game.rocks[:-1]:
            r.y = 20.0
        if len(game.rocks) > 3:
            game.rocks.pop(0)
        assert new.gap is not None or game.escapable(new.x, new.w) or new.w == ROCK_W, (new.x, new.w)


def test_rock_tints_are_never_saturated_red():
    """The governor doubles the signal of a pixel whose red is 0.8 of its light (arcade/flash.py RED_SHARE): a
    beam in red, orange or amber would trip the square rule. Cyan, blue, green, white only."""
    for name, color in dodge.TINTS.items():
        assert name in dodge.SIZES
        r, g, b = color
        assert r < 0.5 * (r + g + b), (name, color)
    assert dodge.GATE_COLOR[0] < 0.5 * sum(dodge.GATE_COLOR)


def test_good_sees_the_width_of_a_beam_and_the_gap_of_a_gate():
    from arcade.games.dodge_bots import Good
    bot = Good()
    bot.x = 0.5
    centre = bot._centre(0.5)
    assert not bot._threatened(((centre + 18.0, 30.0, 6),))
    assert bot._threatened(((centre + 18.0, 30.0, 24),)), "the beam's end comes as near as a rock at NEAR"
    gap, half = centre, dodge.GAP_W / 2
    beams = ((gap - half - 32.0, 30.0, 64), (gap + half + 32.0, 30.0, 64))
    assert not bot._safe(0.5, beams), "the gap is not EDGE clear on both sides"
    assert bot._safe(0.5, beams, Good.EDGE_TIGHT) and not bot._safe(0.6, beams, Good.EDGE_TIGHT)
    assert bot._step(beams) == pytest.approx(0.5, abs=Good.GRID), "so Good takes the gap EDGE_TIGHT clear"


def test_a_good_play_keeps_the_flash_rule_through_the_late_run(font5x7):
    """The sizes, the gates and the 56 px/s end come after 20 s of play, past the canonical script's measured
    window: a Good play that survives the run shows the wall's frames keep the flash rule to the end."""
    from arcade.bots import play
    from arcade.games.dodge_bots import Good
    p = play(Dodge, Good(), seeds(Dodge, "128x64", 2)[1], keep_frames=True, font=font5x7)
    assert p.won and p.seconds >= RUN_SECONDS, (p.won, p.seconds)
    assert flash_area(p.frames) <= 0.1 and square_flashes(p.frames) <= BUDGET
