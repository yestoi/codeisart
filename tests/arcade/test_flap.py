"""Flap (spec 8 row 7): both wrists sweep from above to below the shoulders within FLAP_WINDOW, the bird rises, gravity
is gentle, gaps are wide; a crash holds and fades; a run survives RUN_SECONDS."""
import dataclasses
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
from arcade.game import REQUIRED_SCENARIOS, reserved
from arcade.games import MENU_ORDER, get_game
from arcade.games.flap import (BIRD_COLOR, BIRD_H, BIRD_W, BIRD_X, CRASH_SECONDS, FLAP_VY, FLAP_WINDOW, FLOOR_Y, GAME,
                               GAP_H, GAP_STEP, GAP_Y, GAUGE_BOTTOM, GAUGE_TOP, GAUGE_W, GRAVITY, MAX_RUNS,
                               OVER_SECONDS, PIPE_EVERY, PIPE_W, READY_SECONDS, READY_Y, RUN_SECONDS, SCROLL, V_ABOVE,
                               V_BELOW, V_BOTTOM, V_TOP, Flap, Pipe)
from arcade.headless import OPENING_NIGHT, run_headless
from arcade.juice import Juice
from arcade.scores import Scores
from arcade.sources.actors import REAL_NOISE, TICK, Person, degrade, scene
from tests.arcade.helpers import make_cfg, played, run

WALL = (128, 64)
ZONE = Calibration().zone
CANONICAL_SECONDS = 60.0


def cam_x(zone_x: float) -> float:
    return ZONE[0] + zone_x * (ZONE[2] - ZONE[0])


def seed(layout: str, i: int) -> int:
    return zlib.crc32(f"flap:{layout}:{i}".encode())


def make(size=WALL, i=0) -> Flap:
    """A Flap reset the way the runner resets it, for tests that poke its state."""
    game = Flap()
    layout = f"{size[0]}x{size[1]}"
    game.scores = Scores(None, lambda: OPENING_NIGHT).for_game("flap", layout)
    game.reset(size, random.Random(seed(layout, i)), Juice(random.Random(1), size))
    return game


def step(game: Flap, frame) -> None:
    bodies = frame.bodies
    game.update(dataclasses.replace(frame, player=bodies[0] if bodies else None,
                                    player2=bodies[1] if len(bodies) > 1 else None), TICK)


def drive(game: Flap, frames, until=None):
    for frame in frames:
        step(game, frame)
        yield frame
        if until is not None and until(game):
            return


def arm(person: Person, hand: str, down_at: float, down_seconds: float = 0.1) -> Person:
    """One wrist up (v 0.1) from down_at - 0.7, then down to 0.95 over down_seconds from down_at."""
    person.wrist(hand, 0.95, 0.1, 0.6, at=down_at - 0.7)
    person.wrist(hand, 0.1, 0.1, 0.1, at=down_at - 0.1)
    person.wrist(hand, 0.1, 0.95, down_seconds, at=down_at)
    return person


def flapper(times, stagger=0.0, ticks=None):
    """A body whose wrists both go up and snap down at each of times (the right wrist stagger seconds later)."""
    p = Person(cam_x(0.5), id=1)
    for t in times:
        arm(p, "left", t)
        arm(p, "right", t + stagger)
    return scene(persons=[p], ticks=ticks or round((max(times) + 1.5) / TICK))


def stander(ticks=3000):
    return scene(persons=[Person(cam_x(0.5), id=1)], ticks=ticks)


def playing():
    """A game in play with a still player, no pipes and no spawns, and the frames to go on with."""
    game = make()
    frames = stander()
    game.phase = "play"
    game.phase_t = 0.0
    game.pipes.clear()
    game.spawn_k = 10 ** 6
    return game, frames


def from_first_body(frames):
    started = False
    for f in frames:
        started = started or bool(f.bodies)
        if started:
            yield f


# ----- registration, the flap -----

def test_registered_and_declared():
    assert get_game("flap") is Flap and GAME is Flap and "flap" in MENU_ORDER
    info = Flap.info
    assert (info.name, info.title, info.verb) == ("flap", "FLAP", "FLAP")
    assert info.needs == frozenset({"pose"}) and info.layouts == frozenset({"128x64"})
    assert info.players == 1 and info.kind == "score" and info.exit_gesture is False
    assert Flap.PHASES == ("ready", "play", "over")
    assert Flap.CAPTION_KEYS == ("phase", "score", "runs")
    assert set(Flap.SCENARIOS) >= {"canonical", "idle_body", "nobody", "one_arm"}
    assert (RUN_SECONDS, READY_SECONDS, READY_Y, FLAP_WINDOW, V_ABOVE, V_BELOW) == (45.0, 1.0, 30, 0.4, 0.40, 0.62)
    assert (BIRD_X, BIRD_W, BIRD_H, FLAP_VY, PIPE_W, FLOOR_Y, MAX_RUNS) == (28, 5, 4, -22.0, 6, 59, 3)


@pytest.mark.parametrize("stagger, flaps", [(0.0, 1), (0.3, 1), (0.5, 0)])
def test_both_wrists_down_within_the_window_flap(stagger, flaps):
    """The second wrist's drop must come within FLAP_WINDOW of the first's: 0.3 s flaps, 0.5 s does not."""
    game = make()
    for _ in drive(game, flapper([2.0], stagger=stagger)):
        pass
    assert game.flaps == flaps, (stagger, game.flaps)


def test_one_wrist_never_flaps():
    game = make()
    for _ in drive(game, Flap.SCENARIOS["one_arm"]()):
        pass
    assert game.flaps == 0 and game.debug_state()["phase"] == "ready"
    left = Person(cam_x(0.5), id=1)
    arm(left, "left", 2.0)
    game = make()
    for _ in drive(game, scene(persons=[left], ticks=150)):
        pass
    assert game.flaps == 0


def test_a_flap_sets_the_bird_rising():
    game, _ = playing()
    for frame in flapper([2.0]):                    # falling: a flap sets the speed, it does not add to it
        game.bird_y, game.vy = 20.0, 17.0
        step(game, frame)
        if game.flaps:
            break
    assert game.flaps == 1 and game.vy == FLAP_VY and game.debug_state()["bird_vy"] == FLAP_VY
    assert game.fx._echoes[1][0] == "down"
    step(game, next(iter(stander(5))))
    assert game.vy == pytest.approx(FLAP_VY + GRAVITY * TICK)


def test_gravity_is_gentle():
    game, frames = playing()
    y0 = game.debug_state()["bird_xy"][1]
    for _, _ in zip(range(30), drive(game, frames)):
        pass
    assert game.debug_state()["bird_xy"][1] - y0 <= 13.0, game.debug_state()


def test_the_gauge_follows_hand_height():
    ys = {}
    for v in (0.3, 0.7):
        p = Person(cam_x(0.5), id=1)
        for hand in ("left", "right"):
            p.wrist(hand, v, v, 3.0, at=0.0)
        game = make()
        for _ in drive(game, scene(persons=[p], ticks=60)):
            pass
        ys[v] = game.debug_state()["wing_xy"]
        want = GAUGE_TOP + (v - V_TOP) / (V_BOTTOM - V_TOP) * (GAUGE_BOTTOM - GAUGE_TOP) + 1
        assert ys[v][1] == pytest.approx(want, abs=2.5), (v, ys[v], want)
        assert ys[v][0] == GAUGE_W / 2
    assert ys[0.7][1] > ys[0.3][1] + 15


def test_exit_gesture_is_off(font5x7):
    frames = flapper([0.8 + 0.3 * k for k in range(16)], ticks=round(5.5 / TICK))
    _, game, runner = run(Flap, frames, WALL, font5x7, seed=seed("128x64", 1))
    assert runner.current_name == "flap", runner.current_name


def test_gap_centres_step_at_most_gap_step():
    for i in range(5):
        game = make(i=i)
        gaps = [game.pipes[0].gap_y]
        game.spawn_k = 1
        for _ in range(12):
            game.run_t = game.spawn_k * PIPE_EVERY
            game._spawn()
            gaps.append(game.pipes[-1].gap_y)
        assert all(abs(b - a) <= GAP_STEP + 1e-9 for a, b in zip(gaps, gaps[1:])), (i, gaps)
        assert abs(gaps[0] - READY_Y) <= GAP_STEP + 1e-9 and all(GAP_Y[0] <= g <= GAP_Y[1] for g in gaps), gaps
        assert game.pipes[-1].gap_h == pytest.approx(GAP_H[0] + (GAP_H[1] - GAP_H[0]) * game.run_t / RUN_SECONDS)


# ----- ready, play, crashes -----

def test_ready_holds_the_bird_until_the_first_flap():
    game = make()
    state = game.debug_state()
    assert state["phase"] == "ready" and state["bird_xy"][1] == READY_Y and state["gap_xy"] is not None
    for _ in drive(game, stander(150)):
        pass
    assert game.debug_state()["phase"] == "ready" and game.debug_state()["bird_xy"][1] == READY_Y
    assert game.pipes[0].x == WALL[0] - PIPE_W
    game = make()                                   # a flap at 0.6 s waits for READY_SECONDS
    seen = []
    for _ in drive(game, flapper([0.9], ticks=120)):
        seen.append((game.t, game.debug_state()["phase"]))
    assert game.flaps >= 1
    first_play = next(t for t, ph in seen if ph == "play")
    assert first_play == pytest.approx(READY_SECONDS, abs=2 * TICK), first_play
    late = make()
    for _ in drive(late, flapper([2.5], ticks=100), until=lambda g: g.debug_state()["phase"] == "play"):
        pass
    assert late.t > 2.5 and late.flaps == 1 and late.debug_state()["bird_vy"] < 0


def aim(game, gap_y, x):
    game.pipes.clear()
    game.pipes.append(Pipe(x, gap_y, 34.0))
    game.bird_y = float(gap_y)
    game.vy = 0.0


def test_passing_a_gap_scores_one():
    game, frames = playing()
    aim(game, 30, BIRD_X + 10.0)
    for _ in drive(game, frames, until=lambda g: g.debug_state()["score"] >= 1 or g.debug_state()["phase"] != "play"):
        game.vy, game.bird_y = 0.0, 30.0
    state = game.debug_state()
    assert state["score"] == 1 and state["phase"] == "play", state
    assert state["gap_xy"] is None, state


@pytest.mark.parametrize("what", ["top pipe", "bottom pipe", "floor"])
def test_a_pipe_or_the_floor_crashes_and_the_top_clamps(what):
    game, frames = playing()
    if what == "floor":
        game.bird_y = FLOOR_Y - BIRD_H / 2 - 0.2
        game.vy = 20.0
    else:
        aim(game, 30, BIRD_X)
        game.bird_y = 30 - 17 + 1.0 if what == "top pipe" else 30 + 17 - 1.0
    step(game, next(frames))
    state = game.debug_state()
    assert state["phase"] == "over" and state["crashed"] is True and state["survived"] is False, (what, state)
    clamp, frames = playing()
    clamp.bird_y = BIRD_H / 2 + 0.3
    clamp.vy = -22.0
    step(clamp, next(frames))
    step(clamp, next(frames))
    state = clamp.debug_state()
    assert state["phase"] == "play" and state["bird_xy"][1] == pytest.approx(BIRD_H / 2, abs=0.1) and state["bird_vy"] >= 0, state


def test_a_gap_edge_graze_is_no_crash():
    game, frames = playing()
    aim(game, 30, BIRD_X)
    game.bird_y = 30 - 17 + BIRD_H / 2 + 0.2
    step(game, next(frames))
    assert game.debug_state()["phase"] == "play"


def test_a_crash_holds_and_fades(font5x7):
    cfg = make_cfg(WALL)
    p = Person(cam_x(0.5), id=1)
    arm(p, "left", 1.3)
    arm(p, "right", 1.3)
    frames = scene(persons=[p], ticks=round(12 / TICK))
    _, runner = run_headless(cfg, font5x7, Flap, frames, seed=seed("128x64", 2), raw=True, trace=True)
    states = runner.trace
    overs = [k for k, s in enumerate(states) if s.get("phase") == "over"]
    assert overs, [s.get("phase") for s in states][::30]
    first = overs[0]
    raw = runner.raw_frames
    reds = []
    for k in range(first, len(raw)):
        if states[k].get("phase") != "over":
            break
        x, y = states[k]["bird_xy"]
        reds.append(int(raw[k][int(y), int(x)][0]))
    secs = len(reds) * TICK
    assert secs >= CRASH_SECONDS
    fall = [r for r in reds[:round((CRASH_SECONDS + 0.4) / TICK)]]
    assert all(b <= a for a, b in zip(fall, fall[1:])), fall
    assert fall[0] >= 200 and fall[-1] == 0 or min(fall) == 0
    assert max(s.get("flash_held_ticks", 0) for s in states) == 0
    from arcade.flash import flash_area

    assert flash_area(runner.raw_frames) < 0.1


def test_a_flap_in_over_restarts_up_to_max_runs():
    game, frames = playing()
    assert game.debug_state()["runs"] == 1
    for run_no in range(1, MAX_RUNS + 1):
        game.score = run_no
        game._crash()
        assert game.debug_state()["phase"] == "over"
        game.phase_t = CRASH_SECONDS - 0.2
        game._on_flap()                           # a flap during the fade does not restart
        assert game.debug_state()["phase"] == "over"
        game.phase_t = CRASH_SECONDS + 0.1
        game._on_flap()
        if run_no < MAX_RUNS:
            assert game.debug_state()["phase"] == "play" and game.debug_state()["runs"] == run_no + 1
            assert game.debug_state()["score"] == 0 and game.debug_state()["bird_vy"] == FLAP_VY
        else:
            assert game.debug_state()["phase"] == "over" and game.debug_state()["runs"] == MAX_RUNS
    assert game.debug_state()["score"] == MAX_RUNS


def test_the_best_run_is_recorded_once_at_the_end():
    game, frames = playing()
    game.score = 4
    game._crash()
    game.phase_t = CRASH_SECONDS + 0.1
    game._on_flap()
    game.score = 2
    game._crash()
    assert game.scores.best() is None
    for _ in drive(game, frames, until=lambda g: g.done()):
        pass
    assert game.scores.best() == 4 and game.debug_state()["score"] == 4


def test_surviving_the_run_wins_and_done_after_the_hold(font5x7):
    game, frames = playing()
    game.run_t = RUN_SECONDS - 0.5
    for _ in drive(game, frames, until=lambda g: g.debug_state()["phase"] == "over"):
        game.bird_y, game.vy = 30.0, 0.0
    state = game.debug_state()
    assert state["phase"] == "over" and state["survived"] is True and state["crashed"] is False, state
    assert not game.done()
    canvas = Canvas(*WALL, font5x7)
    game.draw(canvas)
    assert feel.find_text(canvas.frame, font5x7, "SAFE!", scales=(2,)) is not None
    for _ in drive(game, frames, until=lambda g: g.done()):
        pass
    assert game.done() and game.phase_t >= OVER_SECONDS - TICK
    assert game.debug_state()["survived"] is True


def test_score_is_drawn_at_2x_top_right(font5x7):
    game = make()
    game.score = 7
    canvas = Canvas(*WALL, font5x7)
    game.draw(canvas)
    x, y, mask = feel.find_text(canvas.frame, font5x7, "7", scales=(2,))
    assert y == 1 and x + 10 <= WALL[0] and x + 10 >= WALL[0] - 3
    assert feel.find_text(canvas.frame, font5x7, "7", scales=(1,)) is None
    assert feel.find_text(canvas.frame, font5x7, "FLAP TO FLY", scales=(1,)) is not None


# ----- movement (C41, C42), the hint -----

def test_idle_body_scores_nothing(font5x7):
    s = seed("128x64", 2)
    _, game, _ = run(Flap, Flap.SCENARIOS["idle_body"](), WALL, font5x7, seed=s)
    state = game.debug_state()
    assert state["phase"] == "ready" and state["score"] == 0 and state["survived"] is False, (s, state)
    assert game.scores.best() is None
    probe = make()
    for _ in drive(probe, Flap.SCENARIOS["idle_body"](), until=lambda g: g.debug_state()["hint"]):
        pass
    assert probe.debug_state()["hint"] is True and probe.t <= 3.0, probe.t


@pytest.mark.parametrize("i", range(5))
def test_a_still_body_under_real_noise_never_flaps(i):
    s = seeds(Flap, "128x64", 5)[i]
    person = Person(cam_x(0.3 + 0.1 * i), id=s % 1000 + 1)
    frames = from_first_body(degrade(scene(persons=[person], ticks=round(60 / TICK)), **REAL_NOISE))
    game = make(i=i)
    active = []
    for _ in drive(game, frames):
        active.append(game.debug_state()["active"])
    state = game.debug_state()
    assert game.flaps == 0 and state["phase"] == "ready" and state["score"] == 0, (s, state)
    assert not any(active), (s, active.index(True) * TICK)
    assert game.scores.best() is None


# ----- the debug state, scenarios, the lobby -----

def test_debug_state_is_clean(font5x7):
    game = make()
    canvas = Canvas(*WALL, font5x7)
    states = []
    frames = flapper([1.5 + 1.8 * k for k in range(6)], ticks=round(16 / TICK))
    for _ in drive(game, frames, until=lambda g: g.done()):
        state = game.debug_state()
        states.append(state)
        assert not [k for k in state if reserved(k)], state
        assert type(state["active"]) is bool and type(state["hint"]) is bool and type(state["survived"]) is bool
        assert state["phase"] in Flap.PHASES and all(k in state for k in Flap.CAPTION_KEYS)
        assert state["arms"] in ("up", "down")
        canvas.clear()
        game.draw(canvas)
        for key in ("bird_xy", "gap_xy", "wing_xy"):
            xy = state[key]
            if xy is None or (key == "bird_xy" and state["phase"] == "over" and state["crashed"]):
                continue
            x, y = xy
            if key == "gap_xy":
                continue                                    # the gap is where nothing is lit
            assert 0 <= x < WALL[0] and 0 <= y < WALL[1], (key, state)
            assert canvas.frame[int(y), int(x)].any(), (key, state)
    assert {"phase", "score", "runs", "active", "hint", "survived", "crashed", "arms", "bird_xy", "bird_vy", "gap_xy",
            "wing_xy", "t_left"} <= set(states[-1])
    assert any(s["arms"] == "up" for s in states) and states[-1]["phase"] == "over"


def test_the_gauge_lines_and_wings_are_drawn(font5x7):
    game = make()
    canvas = Canvas(*WALL, font5x7)
    game.draw(canvas)
    for v in (V_ABOVE, V_BELOW):
        row = round(GAUGE_TOP + (v - V_TOP) / (V_BOTTOM - V_TOP) * (GAUGE_BOTTOM - GAUGE_TOP))
        assert canvas.frame[row, GAUGE_W:GAUGE_W + 3].any(axis=1).all(), (v, row)
    assert tuple(canvas.frame[int(game.debug_state()["bird_xy"][1]), BIRD_X]) == BIRD_COLOR


def test_required_scenarios_start_with_an_empty_wall():
    assert set(REQUIRED_SCENARIOS) <= set(Flap.SCENARIOS)
    for name in Flap.SCENARIOS:
        assert list(Flap.SCENARIOS[name]()), name
    canonical = list(Flap.SCENARIOS["canonical"]())
    assert len(canonical) == round(CANONICAL_SECONDS / TICK)
    assert all(not f.bodies for f in canonical[:round(2.0 / TICK)]) and canonical[round(2.0 / TICK) + 1].bodies
    assert len(list(Flap.SCENARIOS["idle_body"]())) == round(60 / TICK)
    assert len(list(Flap.SCENARIOS["nobody"]())) == round(30 / TICK)
    assert len(list(Flap.SCENARIOS["one_arm"]())) == round(20 / TICK)
    assert all(not f.bodies for f in Flap.SCENARIOS["nobody"]())


def test_canonical_drives_the_lobby_to_flap(font5x7):
    cfg = make_cfg(WALL)
    lobby = Lobby([Flap], cfg)
    _, runner = run_headless(cfg, font5x7, [Flap], Flap.SCENARIOS["canonical"](), trace=True, lobby=lobby,
                             seed=seeds(Flap, "128x64", 1)[0])
    games = [s["game"] for s in runner.trace]
    assert games[0] == "lobby" and "flap" in games
    first = games.index("flap")
    raised = round(4.5 / TICK)
    assert raised <= first <= raised + 1, (first, raised)
    stop = next((k for k in range(first, len(games)) if games[k] != "flap"), len(games))
    assert stop * TICK >= feel.FEEL_SECONDS, (stop * TICK, [s.get("phase") for s in runner.trace[first:stop]][-5:])
    sweeps = [f.bodies[0].reach(f.bodies[0].keypoints[9])[1] for f in Flap.SCENARIOS["canonical"]() if f.bodies]
    assert min(sweeps[:round(20 / TICK)]) < 0.15 and max(sweeps[round(6 / TICK):round(20 / TICK)]) > 0.9


def test_seeded_runs_repeat(font5x7):
    frames = lambda: Flap.SCENARIOS["canonical"]()
    a, _, _ = run(Flap, frames(), WALL, font5x7, ticks=900, seed=seed("128x64", 6))
    b, _, _ = run(Flap, frames(), WALL, font5x7, ticks=900, seed=seed("128x64", 6))
    c, _, _ = run(Flap, frames(), WALL, font5x7, ticks=900, seed=seed("128x64", 7))
    assert all(np.array_equal(x, y) for x, y in zip(a, b))
    assert any(not np.array_equal(x, y) for x, y in zip(a, c))


# ----- bots -----

def test_bots_module_is_found():
    bots, won = for_game(Flap)
    assert set(bots) == {"good", "lazy"} and bots["good"] is not bots["lazy"]
    assert won({"phase": "over", "survived": True})
    assert not won({"phase": "over", "survived": False})
    assert not won({"phase": "play", "survived": False})


def test_good_beats_lazy_beats_nobody():
    ss = seeds(Flap, "128x64", 5)
    wins = {name: sum(played(Flap, name, s).won for s in ss) for name in ("good", "lazy", "none")}
    assert wins["good"] >= 4 and wins["none"] == 0 and wins["lazy"] < wins["good"], (ss, wins)


def test_good_round_length_in_band():
    plays = [played(Flap, "good", s) for s in seeds(Flap, "128x64", 5)]
    lengths = [p.seconds for p in plays if p.done]
    assert len(lengths) >= 4, [(p.seed, p.seconds, p.done) for p in plays]
    assert 20 <= statistics.median(lengths) <= 120, ([p.seed for p in plays], lengths)


def test_feel_file_overrides_have_reasons():
    data = tomllib.loads((Path(__file__).resolve().parents[2] / "arcade/games/flap_feel.toml").read_text())
    assert data["fidelity"] == {"input": "cursor_y", "xy": "wing_xy", "axis": 1}
    assert "budgets" not in data
    for metric, table in data.get("budgets", {}).get("128x64", {}).items():
        assert table.get("reason", "").strip(), metric
