"""Pong (spec 8, game 2): a paddle on each side that follows a hand, a beatable CPU, first to 5 or the leader at 90 s."""
import dataclasses
import math
import random
import zlib

import numpy as np
import pytest

from arcade.canvas import Canvas
from arcade.flash import BUDGET, flash_area, square_flashes
from arcade.game import reserved
from arcade.games import get_game
from arcade.games.pong import BALL_GAIN, BALL_MAX, BALL_START, GAME, MAX_SECONDS, WIN_POINTS, Pong
from arcade.headless import OPENING_NIGHT, run_headless
from arcade.juice import Juice
from arcade.scores import Scores
from arcade.sources.actors import TICK, Person, scene
from tests.arcade.helpers import make_cfg, run

WALL = (128, 32)


def seed(layout: str, i: int) -> int:
    return zlib.crc32(f"pong:{layout}:{i}".encode())


def make(size=WALL, i=0) -> Pong:
    """A Pong reset the way the runner resets it, for tests that poke its state."""
    game = Pong()
    layout = f"{size[0]}x{size[1]}"
    game.scores = Scores(None, lambda: OPENING_NIGHT).for_game("pong", layout)
    game.reset(size, random.Random(seed(layout, i)), Juice(random.Random(1), size))
    return game


def step(game: Pong, frame) -> None:
    """One tick with the runner's lock applied: the two largest bodies are player and player2."""
    bodies = frame.bodies
    game.update(dataclasses.replace(frame, player=bodies[0] if bodies else None,
                                    player2=bodies[1] if len(bodies) > 1 else None), TICK)


def drive(game: Pong, frames, until=None):
    """Steps game over frames, yielding after each; stops after the tick where until(game) is true."""
    for frame in frames:
        step(game, frame)
        yield frame
        if until is not None and until(game):
            return


def stander(x=0.3, ticks=3000, wrist=None):
    p = Person(x, id=1)
    if wrist is not None:
        p.wrist("right", wrist, wrist, seconds=ticks * TICK, at=0.0)
    return scene(persons=[p], ticks=ticks)


def advance(game, frames, phase):
    for _ in drive(game, frames, until=lambda g: g.debug_state()["phase"] == phase):
        pass
    assert game.debug_state()["phase"] == phase, f"never reached {phase}"


def test_registered_and_declared():
    assert get_game("pong") is Pong and GAME is Pong
    info = Pong.info
    assert (info.name, info.title, info.verb) == ("pong", "PONG", "BLOCK")
    assert info.needs == frozenset({"pose"}) and info.layouts == frozenset({"128x32"})
    assert info.players == 2 and info.kind == "score"
    assert Pong.PHASES == ("serve", "play", "point", "over")
    assert Pong.CAPTION_KEYS == ("phase", "left", "right")
    assert set(Pong.SCENARIOS) == {"solo", "duel"}


@pytest.mark.parametrize("wrist", [0.1, 0.9])
def test_paddle_follows_hand_height(font5x7, wrist):
    _, game, _ = run(Pong, stander(wrist=wrist, ticks=45), WALL, font5x7, seed=seed("128x32", 1))
    state = game.debug_state()
    y = state["left_xy"][1]
    if wrist < 0.5:
        assert y <= 8, state
    else:
        assert y >= 23, state


@pytest.mark.parametrize("x, cpu", [(0.3, "right"), (0.7, "left")])
def test_solo_player_gets_the_cpu_on_the_other_side(font5x7, x, cpu):
    _, game, _ = run(Pong, stander(x=x, ticks=45), WALL, font5x7, seed=seed("128x32", 2))
    state = game.debug_state()
    assert state["cpu"] == cpu and state["humans"] == 1, state


def test_cpu_is_beatable():
    game = make()
    frames = stander(x=0.3, ticks=600)
    advance(game, frames, "play")
    game.right_y = 4.0                              # the CPU paddle parked at the top
    game.bx, game.by = 64.0, 3.0                    # midfield, at BALL_MAX, reaching the bottom corner in 0.6 s
    game.speed = BALL_MAX
    game.vy = 43.0
    game.vx = math.sqrt(BALL_MAX ** 2 - game.vy ** 2)
    advance(game, frames, "point")
    state = game.debug_state()
    assert (state["left"], state["right"]) == (1, 0), state


def test_phase_leaves_play_after_every_point():
    game = make()
    seen = []
    for _ in drive(game, stander(ticks=2400), until=lambda g: g.done()):
        phase = game.debug_state()["phase"]
        if not seen or seen[-1] != phase:
            seen.append(phase)
    allowed = {"serve": {"play"}, "play": {"point"}, "point": {"serve", "over"}, "over": set()}
    for a, b in zip(seen, seen[1:]):
        assert b in allowed[a], seen
    assert seen.count("point") >= 2 and seen[0] == "serve", seen


@pytest.mark.parametrize("name", ["solo", "duel"])
def test_duel_and_solo_scenarios_reach_a_result(font5x7, name):
    s = seed("128x32", 3)
    _, game, _ = run(Pong, Pong.SCENARIOS[name](), WALL, font5x7, seed=s)
    state = game.debug_state()
    assert game.done(), f"{name} seed {s}: {state}"
    assert state["phase"] == "over" and max(state["left"], state["right"]) >= 1, state


def test_scenarios_have_the_right_humans(font5x7):
    for name, humans in (("solo", 1), ("duel", 2)):
        _, game, _ = run(Pong, Pong.SCENARIOS[name](), WALL, font5x7, seed=seed("128x32", 4))
        assert game.debug_state()["humans"] == humans, name       # the duel's second body joins at a serve


def test_runs_and_stays_legible_on_64x64(font5x7):
    frames, _, _ = run(Pong, Pong.SCENARIOS["duel"](), (64, 64), font5x7, ticks=300, seed=seed("64x64", 0))
    assert len(frames) == 300 and any(f.any() for f in frames)
    game = make((64, 64))
    canvas = Canvas(64, 64, font5x7)
    lit_ball = False
    for _ in drive(game, Pong.SCENARIOS["duel"](), until=lambda g: g.t > 10.0):
        canvas.clear()
        game.draw(canvas)
        state = game.debug_state()
        for key in ("left_xy", "right_xy"):
            x, y = state[key]
            assert canvas.frame[int(y), int(x)].any(), (key, state)
        if state["phase"] in ("serve", "play"):
            x, y = state["ball_xy"]
            assert canvas.frame[int(y), int(x)].any(), state
            lit_ball = True
    assert lit_ball


def test_own_drawing_keeps_the_flash_rule(font5x7):
    s = seed("128x32", 5)
    _, runner = run_headless(make_cfg(WALL), font5x7, Pong, Pong.SCENARIOS["duel"](), seed=s, raw=True)
    raw = runner.raw_frames
    assert len(raw) > 300
    assert flash_area(raw) == 0.0, s
    assert square_flashes(raw) <= BUDGET, s


def test_second_player_joins_at_the_next_serve():
    game = make()
    frames = scene(persons=[Person(0.3, id=1), Person(0.7, id=2).arrive(1.0)], ticks=900)
    for _ in drive(game, frames, until=lambda g: g.t >= 2.6):
        pass
    state = game.debug_state()
    assert state["phase"] in ("play", "point") and state["humans"] == 1 and state["cpu"] == "right", state
    game.bx, game.vx = -5.0, -BALL_START           # the ball goes out behind the left paddle
    advance(game, frames, "serve")
    state = game.debug_state()
    assert state["humans"] == 2 and state["cpu"] is None, state


def test_ball_speeds_up_on_each_hit_up_to_the_max():
    game = make()
    frames = stander(x=0.3, ticks=6000, wrist=0.5)
    advance(game, frames, "play")
    speeds = [game.speed]
    assert speeds[0] == BALL_START
    for _ in range(40):
        game.bx, game.by = 20.0, game.left_y
        game.vx, game.vy = -game.speed, 0.0
        before = game.speed
        for _ in drive(game, frames, until=lambda g: g.vx > 0 or g.debug_state()["phase"] != "play"):
            pass
        assert game.debug_state()["phase"] == "play"
        speeds.append(game.speed)
        if speeds[-1] == BALL_MAX and speeds[-2] == BALL_MAX:
            break
    for a, b in zip(speeds, speeds[1:]):
        assert b == pytest.approx(min(a * BALL_GAIN, BALL_MAX)), speeds
    assert speeds[-1] == BALL_MAX and max(speeds) <= BALL_MAX


def test_first_to_5_goes_over_then_done():
    game = make()
    frames = stander(x=0.3, ticks=6000, wrist=0.5)
    for n in range(1, WIN_POINTS + 1):
        advance(game, frames, "play")
        game.bx, game.vx = -5.0, -BALL_START        # out behind the human on the left: the CPU scores
        advance(game, frames, "point")
        assert game.debug_state()["right"] == n
        assert not game.done()
    advance(game, frames, "over")
    assert not game.done()
    for _ in drive(game, frames, until=lambda g: g.done()):
        pass
    assert game.done() and game.winner == "right"


def test_time_limit_ends_at_90s():
    game = make()
    frames = stander(x=0.3, ticks=6000, wrist=0.5)
    advance(game, frames, "play")
    game.seats[0].points, game.seats[1].points = 1, 2           # the CPU (right) leads
    game.t = MAX_SECONDS - 0.05
    advance(game, frames, "over")
    assert game.winner == "right"
    assert (game.debug_state()["left"], game.debug_state()["right"]) == (1, 2)


def test_time_limit_tie_goes_to_player_ones_side():
    game = make()
    frames = stander(x=0.3, ticks=6000, wrist=0.5)
    advance(game, frames, "play")
    game.seats[0].points = game.seats[1].points = 2
    game.t = MAX_SECONDS
    advance(game, frames, "over")
    assert game.winner == "left"


def test_active_is_a_bool_and_true_on_input():
    game = make()
    states = [game.debug_state()["active"]]
    for _ in drive(game, Pong.SCENARIOS["solo"](), until=lambda g: g.t > 12):
        states.append(game.debug_state()["active"])
    assert all(type(a) is bool for a in states)
    assert not any(states[:60])                                  # a still player: nothing before the sweeps
    assert any(states[150:])
    still = make()
    quiet = [still.debug_state()["active"] for _ in drive(still, stander(ticks=20, wrist=0.5))]
    assert quiet and not any(quiet[1:])


def test_seeded_runs_repeat(font5x7):
    a, _, _ = run(Pong, Pong.SCENARIOS["duel"](), WALL, font5x7, ticks=400, seed=seed("128x32", 6))
    b, _, _ = run(Pong, Pong.SCENARIOS["duel"](), WALL, font5x7, ticks=400, seed=seed("128x32", 6))
    c, _, _ = run(Pong, Pong.SCENARIOS["duel"](), WALL, font5x7, ticks=400, seed=seed("128x32", 7))
    assert all(np.array_equal(x, y) for x, y in zip(a, b))
    assert any(not np.array_equal(x, y) for x, y in zip(a, c))


def test_debug_keys_not_reserved_and_xy_on_the_wall():
    game = make()
    state = game.debug_state()
    for _ in drive(game, Pong.SCENARIOS["duel"](), until=lambda g: g.t > 15):
        state = game.debug_state()
        assert not [k for k in state if reserved(k)], state
        for key in ("ball_xy", "left_xy", "right_xy"):
            x, y = state[key]
            assert 0 <= x < WALL[0] and 0 <= y < WALL[1], (key, state)
    assert {"phase", "score", "left", "right", "cpu", "humans", "active", "speed"} <= set(state)
