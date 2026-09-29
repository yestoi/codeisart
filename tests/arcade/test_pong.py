"""Pong (spec 8, game 2): a paddle on each side that follows a body stepping in depth, a beatable CPU, first to 5
or the leader at 90 s."""
import dataclasses
import functools
import math
import random
import statistics
import tomllib
import zlib
from pathlib import Path

import numpy as np
import pytest

from arcade.canvas import Canvas
from arcade.flash import BUDGET, SMALL_AREA, concurrent_area, flash_area, square_flashes
from arcade.attract.lobby import Lobby
from arcade import feel
from arcade.bots import Nobody, for_game, play, seeds
from arcade.game import REQUIRED_SCENARIOS, reserved
from arcade.games import get_game
from arcade.games.pong import (_steps, BALL_COLOR, BALL_GAIN, BALL_MAX, BALL_START, GAME, HINT_COLOR,
                               HINT_IDLE_SECONDS, HINT_LINES, MAX_SECONDS, TRAVEL_SHARE, WIN_POINTS, Pong, idle_body)
from arcade.headless import OPENING_NIGHT, run_headless
from arcade.input import Depth
from arcade.juice import Juice
from arcade.scores import Scores
from arcade.sources.actors import REAL_NOISE, TICK, Person, degrade, scene
from tests.arcade.helpers import make_cfg, run

WALL = (128, 64)
HEIGHT = 0.7                    # the scripts' body (bots.BODY_HEIGHT): stepping to 0.78 keeps it in the zone
TRAVEL = 48                     # the paddle's range at 128x64: h - paddle_h


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


def stander(x=0.3, ticks=3000, near=None):
    """A body standing still, hands down; with near, it steps (0.5 s from 0.2 s) to the size a Depth that first
    saw it reads as near, and stays there."""
    p = Person(x, id=1, height=HEIGHT)
    if near is not None:
        p.scale_to(Depth.ratio(near), 0.5, at=0.2)
    return scene(persons=[p], ticks=ticks)


def from_first_body(frames):
    """frames from the first one with a body in it: the runner launches a game only when someone is there, and
    a degraded scene has no capture for its first 0.15 s."""
    started = False
    for f in frames:
        started = started or bool(f.bodies)
        if started:
            yield f


def advance(game, frames, phase):
    for _ in drive(game, frames, until=lambda g: g.debug_state()["phase"] == phase):
        pass
    assert game.debug_state()["phase"] == phase, f"never reached {phase}"


def test_registered_and_declared():
    assert get_game("pong") is Pong and GAME is Pong
    info = Pong.info
    assert (info.name, info.title, info.verb) == ("pong", "PONG", "BLOCK")
    assert info.needs == frozenset({"pose"}) and info.layouts == frozenset({"128x64"})
    assert info.players == 2 and info.kind == "score"
    assert Pong.PHASES == ("serve", "play", "point", "over")
    assert Pong.CAPTION_KEYS == ("phase", "left", "right", "near")
    assert set(Pong.SCENARIOS) == {"solo", "duel", "canonical", "idle_body", "nobody"}


@pytest.mark.parametrize("ratio", [1.3, 0.77])
def test_paddle_follows_depth(font5x7, ratio):
    """A body that steps to 1.3 of the size it was first seen at (nearer) puts the paddle at the top, to 0.77 at
    the bottom. Settled after 1.5 s, before any recentre (2 s pinned)."""
    p = Person(0.3, id=1, height=HEIGHT).scale_to(ratio, 0.5, at=0.5)
    _, game, _ = run(Pong, scene(persons=[p], ticks=75), WALL, font5x7, seed=seed("128x64", 1))
    state = game.debug_state()
    y = state["left_xy"][1]
    if ratio > 1:
        assert y <= 12, state
    else:
        assert y >= 52, state
    assert state["near"] == round(0.5 + math.log(ratio) / 0.6, 2), state


def test_the_hand_does_not_move_the_paddle(font5x7):
    """Q42: the raised hand only launches; a still body sweeping its wrist 0 to 1 leaves the paddle where it is."""
    game = make()
    p = Person(0.3, id=1, height=HEIGHT).wrist("right", 0.0, 1.0, 1.0, at=0.5).wrist("right", 1.0, 0.0, 1.0)
    ys = [game.debug_state()["left_xy"][1] for _ in drive(game, scene(persons=[p], ticks=90))]
    assert len(set(ys)) == 1, sorted(set(ys))


@pytest.mark.parametrize("x, cpu", [(0.3, "right"), (0.7, "left")])
def test_solo_player_gets_the_cpu_on_the_other_side(font5x7, x, cpu):
    _, game, _ = run(Pong, stander(x=x, ticks=45), WALL, font5x7, seed=seed("128x64", 2))
    state = game.debug_state()
    assert state["cpu"] == cpu and state["humans"] == 1, state


def test_cpu_is_beatable():
    game = make()
    frames = scene(persons=[_steps(Person(0.3, id=1, height=HEIGHT), start=0.0, end=20.0)], ticks=600)   # C42
    advance(game, frames, "play")
    game.vx = game.vy = 0.0                         # the ball held while the player steps through the rally
    for _ in drive(game, frames, until=lambda g: g.t >= 3.0):
        pass
    game.right_y = 4.0                              # the CPU paddle parked at the top
    game.bx, game.by = 96.0, 3.0                    # at BALL_MAX, reaching the far side of the field in 0.5 s
    game.speed = BALL_MAX
    game.vy = 70.0
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
    s = seed("128x64", 3)
    _, game, _ = run(Pong, Pong.SCENARIOS[name](), WALL, font5x7, seed=s)
    state = game.debug_state()
    assert game.done(), f"{name} seed {s}: {state}"
    assert state["phase"] == "over" and max(state["left"], state["right"]) >= 1, state


def test_scenarios_have_the_right_humans(font5x7):
    for name, humans in (("solo", 1), ("duel", 2)):
        _, game, _ = run(Pong, Pong.SCENARIOS[name](), WALL, font5x7, seed=seed("128x64", 4))
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
    s = seed("128x64", 5)
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
    frames = stander(x=0.3, ticks=6000, near=0.5)
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
    frames = stander(x=0.3, ticks=6000, near=0.5)
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
    frames = stander(x=0.3, ticks=6000, near=0.5)
    advance(game, frames, "play")
    game.seats[0].points, game.seats[1].points = 1, 2           # the CPU (right) leads
    game.t = MAX_SECONDS - 0.05
    advance(game, frames, "over")
    assert game.winner == "right"
    assert (game.debug_state()["left"], game.debug_state()["right"]) == (1, 2)


def test_time_limit_tie_goes_to_player_ones_side():
    game = make()
    frames = stander(x=0.3, ticks=6000, near=0.5)
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
    quiet = [still.debug_state()["active"] for _ in drive(still, stander(ticks=20, near=0.5))]
    assert quiet and not any(quiet[1:])


def test_seeded_runs_repeat(font5x7):
    a, _, _ = run(Pong, Pong.SCENARIOS["duel"](), WALL, font5x7, ticks=400, seed=seed("128x64", 6))
    b, _, _ = run(Pong, Pong.SCENARIOS["duel"](), WALL, font5x7, ticks=400, seed=seed("128x64", 6))
    c, _, _ = run(Pong, Pong.SCENARIOS["duel"](), WALL, font5x7, ticks=400, seed=seed("128x64", 7))
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


def test_required_scenarios_start_with_an_empty_wall():
    assert set(REQUIRED_SCENARIOS) <= set(Pong.SCENARIOS)
    for name in REQUIRED_SCENARIOS:
        frames = list(Pong.SCENARIOS[name]())
        assert frames, name
    canonical = list(Pong.SCENARIOS["canonical"]())
    assert len(canonical) == round(100 / TICK)
    assert all(not f.bodies for f in canonical[:round(2.0 / TICK)]) and canonical[round(2.0 / TICK) + 1].bodies
    assert len(list(Pong.SCENARIOS["idle_body"]())) == round(60 / TICK)
    assert len(list(Pong.SCENARIOS["nobody"]())) == round(30 / TICK)
    assert all(not f.bodies for f in Pong.SCENARIOS["nobody"]())


def test_canonical_drives_the_lobby_to_pong(font5x7):
    cfg = make_cfg(WALL)
    lobby = Lobby([Pong], cfg)
    _, runner = run_headless(cfg, font5x7, [Pong], Pong.SCENARIOS["canonical"](), trace=True, lobby=lobby)
    games = [s["game"] for s in runner.trace]
    assert games[0] == "lobby" and "pong" in games
    first = games.index("pong")
    raised = round(4.5 / TICK)                 # the scene frame the hand goes up on
    assert raised <= first <= raised + 1, (first, raised)


def _rally_with_ball_past_the_cpu(travel: float):
    """A human on the left in a rally; the ball is held still while the body steps over 3 s from 1.5 s so the
    paddle travels `travel` px (0: stands still), then the ball goes out behind the CPU on the right. Returns the
    game after the point phase began, the frames and the rally's travel as the game measured it."""
    game = make()
    p = Person(0.3, id=1, height=HEIGHT)
    if travel:
        p.scale_to(Depth.ratio(0.5 + travel / TRAVEL), 3.0, at=1.5)
    frames = scene(persons=[p], ticks=900)
    advance(game, frames, "play")
    game.vx = game.vy = 0.0
    for _ in drive(game, frames, until=lambda g: g.t >= 5.0):
        pass
    assert game.debug_state()["phase"] == "play"
    seat = game.seats[game.left_seat]
    moved = seat.hi - seat.lo
    game.bx, game.vx = game.w + 5.0, BALL_START
    advance(game, frames, "point")
    return game, frames, moved


def test_a_still_paddle_banks_no_point():
    """C42: a player who moved the paddle under TRAVEL_SHARE of its range in the rally (10 px of 48) banks nothing."""
    game, frames, moved = _rally_with_ball_past_the_cpu(travel=10)
    assert moved == pytest.approx(10, abs=0.1), moved
    state = game.debug_state()
    assert (state["left"], state["right"]) == (0, 0), state
    assert game.fx.debug_state()["fx_pops"] == 0                 # no "+1" for a point nobody banked
    advance(game, frames, "serve")
    assert game.debug_state()["phase"] == "serve"


def test_a_moving_player_still_scores():
    game, frames, moved = _rally_with_ball_past_the_cpu(travel=20)
    assert moved == pytest.approx(20, abs=0.1), moved
    state = game.debug_state()
    assert (state["left"], state["right"]) == (1, 0), state
    assert game.fx.debug_state()["fx_pops"] == 1


@pytest.mark.parametrize("travel, points", [(17, 1), (10, 0), (0, 0)])
def test_a_slow_player_keeps_the_point(travel, points):
    """C42: a slow player whose paddle travels 17 px over 3 s in the rally banks the point; 10 px, or none, does
    not. The threshold is TRAVEL_SHARE of the paddle's range: 14.4 px at 128x64 (the operator's ruling, from 12)."""
    assert TRAVEL_SHARE * TRAVEL == pytest.approx(14.4)
    game, _, moved = _rally_with_ball_past_the_cpu(travel=travel)
    assert moved == pytest.approx(travel, abs=0.1), moved
    state = game.debug_state()
    assert (state["left"], state["right"]) == (points, 0), (travel, moved, state)


def _still_under_noise(i: int, persons: int = 1):
    """Still bodies, hands down, for 95 s (past MAX_SECONDS) under degrade(REAL_NOISE), from the first capture;
    body ids from the seed, so each seed has its own noise."""
    s = seeds(Pong, "128x64", 10)[i]
    ids = [s % 1000 + 1000 * k for k in range(persons)]
    people = [Person(x, id=body_id) for x, body_id in zip((0.3, 0.7), ids)]
    return s, from_first_body(degrade(scene(persons=people, ticks=round(95 / TICK)), **REAL_NOISE))


def test_a_still_body_under_real_noise_banks_nothing():
    """C42 under REAL_NOISE: a still body's jitter never adds up to a rally's travel. The human side scores 0 and
    no best is stored, on 10 seeds of 10."""
    out = {}
    for i in range(10):
        s, frames = _still_under_noise(i)
        game = make(i=i)
        worst = 0.0
        for _ in drive(game, frames, until=lambda g: g.done()):
            seat = game._score_seat()
            if game.phase == "play":
                worst = max(worst, seat.hi - seat.lo)
        state = game.debug_state()
        out[s] = (state["score"], state["left"], game.scores.best(), round(worst, 2))
    assert all(v[:3] == (0, 0, None) for v in out.values()), out
    assert all(v[3] < TRAVEL_SHARE * TRAVEL for v in out.values()), out


def test_a_still_body_under_real_noise_is_not_input():
    """`active` judges the paddle's movement as C42 does, so a still body's jitter never keeps a session alive
    (the runner's STILL PLAYING? prompt): with the ball held at the centre, no tick is active; a step is."""
    s, frames = _still_under_noise(1)
    game = make(i=1)
    active = []
    for _ in drive(game, frames, until=lambda g: g.t >= 60.0):
        game.bx, game.by, game.vx, game.vy = game.w / 2, game.h / 2, 0.0, 0.0
        active.append(game.debug_state()["active"])
    assert not any(active), (s, active.index(True) * TICK)
    stepper = make(i=1)
    p = Person(0.3, id=1, height=HEIGHT).scale_to(1.28, 0.8, at=2.0)
    seen = [stepper.debug_state()["active"] for _ in drive(stepper, scene(persons=[p], ticks=120))]
    assert any(seen)


def test_a_duel_with_both_bodies_still_scores_nothing():
    """Two still bodies under REAL_NOISE: nobody banks a point, the game runs to MAX_SECONDS and stores no best."""
    s, frames = _still_under_noise(0, persons=2)
    game = make()
    for _ in drive(game, frames, until=lambda g: g.done()):
        pass
    state = game.debug_state()
    assert state["humans"] == 2 and (state["left"], state["right"]) == (0, 0), (s, state)
    assert state["phase"] == "over" and game.t >= MAX_SECONDS - TICK, (s, game.t, state)
    assert game.scores.best() is None, s


def _points_entered(game, frames) -> int:
    entered, last = 0, game.debug_state()["phase"]
    for _ in drive(game, frames, until=lambda g: g.done()):
        phase = game.debug_state()["phase"]
        entered += phase == "point" and last != "point"
        last = phase
    return entered


def test_duel_script_banks_every_point():
    """C42: both of the duel's players step, so every goal banks: the point phases equal left + right."""
    game = make()
    entered = _points_entered(game, Pong.SCENARIOS["duel"]())
    state = game.debug_state()
    assert game.done() and state["humans"] == 2, state
    assert entered == state["left"] + state["right"] and entered >= 1, (entered, state)


def test_best_needs_travel_in_the_game():
    """Solo stores a best; a still body stores none (C41's best, judged by travel)."""
    game = make()
    for _ in drive(game, Pong.SCENARIOS["solo"](), until=lambda g: g.done()):
        pass
    assert game.done() and game.scores.best() == game.debug_state()["score"], game.debug_state()
    still = make()
    for _ in drive(still, stander(ticks=2800), until=lambda g: g.done()):
        pass
    assert still.done() and still.scores.best() is None, still.debug_state()


def _stepping_then_still(first: float, seconds: float = 60.0, gap: float = 9.0):
    """A body standing still until `first`, then a step in and back (1.6 s), then still for `gap`, and so on."""
    p, t = Person(0.3, id=1, height=HEIGHT), first
    while t < seconds:
        p.scale_to(1.28, 0.8, at=t).scale_to(1.0, 0.8)
        t += 1.6 + gap
    return scene(persons=[p], ticks=round(seconds / TICK))


def test_hint_at_first_serve_and_after_idle(font5x7):
    game = make()
    frames = _stepping_then_still(3.0)
    step(game, next(frames))
    assert game.debug_state()["hint"] is True and game.debug_state()["phase"] == "serve"
    for _ in drive(game, frames, until=lambda g: not g.debug_state()["hint"]):
        pass
    counted = game.t
    seat = game.seats[game.left_seat]
    assert game.phase == "play" and seat.hi - seat.lo >= TRAVEL_SHARE * TRAVEL, (counted, seat.hi - seat.lo)
    played = 0.0
    for _ in drive(game, frames, until=lambda g: g.debug_state()["hint"]):
        played += TICK if game.phase == "play" else 0.0
    assert game.debug_state()["hint"] is True, game.t
    assert HINT_IDLE_SECONDS - 2 * TICK <= played, (counted, game.t, played)
    # The ball is drawn over the hint: put it on a lit pixel of the hint, fully faded in, and look.
    for _ in drive(game, frames, until=lambda g: g._hint_level >= 1.0 and g.phase in ("serve", "play")):
        pass
    canvas = Canvas(*WALL, font5x7)
    game.draw(canvas)
    ys, xs = np.nonzero((canvas.frame == HINT_COLOR).all(axis=2))
    assert len(ys), "the hint is not drawn"
    k = len(ys) // 2
    game.bx, game.by = xs[k] + 0.5, ys[k] + 0.5
    canvas.clear()
    game.draw(canvas)
    assert tuple(canvas.frame[ys[k], xs[k]]) == BALL_COLOR


def test_hint_fits_and_keeps_the_flash_rule(font5x7):
    canvas = Canvas(*WALL, font5x7)
    widths = [canvas.text_width(line) - 1 for line in HINT_LINES]
    assert widths == [71, 95] and max(widths) <= WALL[0], widths
    s = seed("128x64", 9)
    _, runner = run_headless(make_cfg(WALL), font5x7, Pong, _stepping_then_still(2.0, seconds=60.0, gap=12.0),
                             seed=s, raw=True, trace=True)
    hints = [st.get("hint") for st in runner.trace if "hint" in st]
    turns = sum(a != b for a, b in zip(hints, hints[1:]))
    assert turns >= 3, (s, turns)                                  # out, back in after the idle, and out again
    raw = runner.raw_frames
    assert concurrent_area(raw) < SMALL_AREA, s
    assert flash_area(raw) == 0.0, s
    assert square_flashes(raw) <= BUDGET, s


def test_scores_drawn_at_2x(font5x7):
    game = make()
    game.seats[game.left_seat].points, game.seats[game.right_seat].points = 3, 5
    canvas = Canvas(*WALL, font5x7)
    game.draw(canvas)
    for points, centre in ((3, WALL[0] / 4), (5, 3 * WALL[0] / 4)):
        found = feel.find_text(canvas.frame, font5x7, str(points), scales=(2,))
        assert found is not None, points
        x, y, mask = found
        assert mask.shape == (14, 10) and y == 1, (points, mask.shape, y)
        assert abs(x + mask.shape[1] / 2 - centre) <= 1, (points, x)
        assert feel.find_text(canvas.frame, font5x7, str(points), scales=(1,)) is None, points


def test_cpu_speed_follows_the_height():
    steps = {}
    for size in ((128, 32), (128, 64)):
        game = make(size)
        game.phase, game.vx = "play", BALL_START
        game.by = size[1] - 2.0
        y = game.right_y
        steps[size[1]] = game._cpu_y("right", y, TICK) - y
    assert steps[64] == pytest.approx(2 * steps[32]) and steps[32] > 0, steps


def test_idle_body_scores_nothing_over_seeds():
    for i, s in enumerate(seeds(Pong, "128x64", 10)):
        game = make(i=i)
        for _ in drive(game, stander(ticks=2800), until=lambda g: g.done()):
            pass
        state = game.debug_state()
        assert state["phase"] == "over", (s, state)
        assert state["score"] == 0 and state["left"] == 0, (s, state)
        assert game.scores.best() is None, (s, game.scores.best())


def test_idle_body_scores_nothing(font5x7):
    s = seed("128x64", 8)
    _, game, runner = run(Pong, Pong.SCENARIOS["idle_body"](), WALL, font5x7, seed=s)
    state = game.debug_state()
    assert state["humans"] == 1 and state["phase"] == "over", (s, state)
    assert not for_game(Pong)[1](state) and state["left"] < state["right"], (s, state)    # the CPU beats a body that never plays
    assert state["score"] == state["left"], (s, state)


@pytest.mark.parametrize("x, side", [(0.3, "left"), (0.7, "right")])
def test_a_walk_up_takes_a_cpu_seat_at_once(x, side):
    game = make(i=3)
    frames = scene(persons=[Person(x, id=1).arrive(2.0).raise_hand(2.5, 0.2)], ticks=900)
    for _ in drive(game, frames, until=lambda g: g.t >= 1.5):
        pass
    assert game.debug_state()["humans"] == 0
    for _ in drive(game, frames, until=lambda g: g.t >= 2.3):
        pass
    state = game.debug_state()
    assert state["humans"] == 1 and state["cpu"] == ("right" if side == "left" else "left"), (seed("128x64", 3), state)
    assert game.seats[game.left_seat if side == "left" else game.right_seat].ctrl == 1
    assert game._p1 == (game.left_seat if side == "left" else game.right_seat)
    seated = (game.left_seat, game.right_seat)
    for _ in drive(game, frames, until=lambda g: g.t >= 6.0):
        pass
    assert (game.left_seat, game.right_seat) == seated      # never moved to the other side mid-rally


def test_score_stays_with_player_one_when_they_leave():
    game = make()
    p1 = Person(0.3, id=1).raise_hand(0.0, 100.0)
    frames = scene(persons=[p1.leave(4.0), Person(0.7, id=2)], ticks=3000)
    for _ in drive(game, frames, until=lambda g: g.t >= 3.0 and g.phase == "play"):
        pass
    assert game.debug_state()["humans"] == 2
    game.seats[0].points = 2
    for _ in drive(game, frames, until=lambda g: g.t >= 5.5 and g.phase == "play"):
        pass
    game.bx, game.vx = -5.0, -BALL_START if game.left_seat == 0 else BALL_START
    game.bx = -5.0 if game.left_seat == 0 else game.w + 5.0
    advance(game, frames, "serve")
    state = game.debug_state()
    assert state["humans"] == 1 and game.seats[0].ctrl is None, state
    assert state["score"] == game.seats[0].points >= 2, state


def test_bots_module_is_found():
    bots, won = for_game(Pong)
    assert set(bots) == {"good", "lazy"}
    assert won({"phase": "over", "left": 3, "right": 2, "cpu": "right", "humans": 1})
    assert not won({"phase": "over", "left": 2, "right": 3, "cpu": "right", "humans": 1})
    assert not won({"phase": "play", "left": 4, "right": 0, "cpu": "right", "humans": 1})
    assert won({"phase": "over", "left": 2, "right": 3, "cpu": "left", "humans": 1})
    assert not won({"phase": "over", "left": 0, "right": 0, "cpu": "right", "humans": 1})


@functools.lru_cache(maxsize=None)
def bot_play(name: str, s: int):
    """One play of a named bot ("none" is Nobody) on seed s, shared by the two bot tests."""
    make = Nobody if name == "none" else for_game(Pong)[0][name]
    return play(Pong, make(), s)


def test_good_beats_lazy_beats_nobody():
    ss = seeds(Pong, "128x64", 5)
    wins = {name: sum(bot_play(name, s).won for s in ss) for name in ("good", "lazy", "none")}
    assert wins["good"] >= 4 and wins["none"] == 0 and wins["lazy"] < wins["good"], (ss, wins)


def test_good_round_length_in_band():
    plays = [bot_play("good", s) for s in seeds(Pong, "128x64", 5)]
    lengths = [p.seconds for p in plays if p.done]
    assert len(lengths) >= 4, [(p.seed, p.seconds, p.done) for p in plays]
    assert 20 <= statistics.median(lengths) <= 120, ([p.seed for p in plays], lengths)


def test_feel_file_overrides_have_reasons():
    data = tomllib.loads((Path(__file__).resolve().parents[2] / "arcade/games/pong_feel.toml").read_text())
    assert data["fidelity"] == {"input": "far", "xy": "left_xy", "axis": 1}
    overrides = data["budgets"]["128x64"]
    assert "dim_fraction" in overrides
    for metric, table in overrides.items():
        assert table.get("reason", "").strip(), metric
        assert "min" in table or "max" in table, metric
