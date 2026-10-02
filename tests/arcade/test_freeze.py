"""Freeze (spec 8 row 10, pose only): dance on green, freeze on red; anyone still moving after the grace is out and
their figure topples; last one standing, or survive the reds alone."""
import dataclasses
import random
import statistics
import tomllib
import zlib
from pathlib import Path

import numpy as np
import pytest

from arcade import bots, feel
from arcade.attract.lobby import Lobby
from arcade.bots import Move, Nobody, for_game, seeds
from arcade.calibration import Calibration
from arcade.canvas import Canvas
from arcade.config import ArcadeConfig
from arcade.flash import BUDGET, flash_area, square_flashes
from arcade.game import REQUIRED_SCENARIOS, reserved
from arcade.games import MENU_ORDER, get_game
from arcade.games.freeze import (COUNT_LAG, DANCE_TRAVEL, GAME, GRACE, GREEN_SECONDS, HINT_IDLE_SECONDS,
                                 MOVE_TRAVEL, OVER_SECONDS, READY_SECONDS, RED_AREA, RED_SECONDS, REDS,
                                 TOPPLE_SECONDS, WIN_SCORE, Freeze)
from arcade.headless import OPENING_NIGHT, run_headless
from arcade.juice import Juice
from arcade.scores import Scores
from arcade.sources.actors import REAL_NOISE, TICK, Person, degrade, scene
from tests.arcade.helpers import make_cfg, played, run

WALL = (128, 64)
ZONE = Calibration().zone
CANONICAL_SECONDS = 60.0
RED = (255, 0, 0)


def cam_x(zone_x: float) -> float:
    """The camera x a Person stands at to be at zone_x on the mat."""
    return ZONE[0] + zone_x * (ZONE[2] - ZONE[0])


def seed(layout: str, i: int) -> int:
    return zlib.crc32(f"freeze:{layout}:{i}".encode())


def make(size=WALL, i=0) -> Freeze:
    """A Freeze reset the way the runner resets it, for tests that poke its state."""
    game = Freeze()
    layout = f"{size[0]}x{size[1]}"
    game.scores = Scores(None, lambda: OPENING_NIGHT).for_game("freeze", layout)
    game.reset(size, random.Random(seed(layout, i)), Juice(random.Random(1), size))
    return game


def step(game: Freeze, frame) -> None:
    """One tick with the runner's lock applied: the largest body is the player, the next player 2."""
    bodies = frame.bodies
    game.update(dataclasses.replace(frame, player=bodies[0] if bodies else None,
                                    player2=bodies[1] if len(bodies) > 1 else None), TICK)


def drive(game: Freeze, frames, until=None):
    for frame in frames:
        step(game, frame)
        yield frame
        if until is not None and until(game):
            return


def from_first_body(frames):
    started = False
    for f in frames:
        started = started or bool(f.bodies)
        if started:
            yield f


def puppet(game: Freeze, fn, until, max_ticks: int = 3600, canvas=None, each=None) -> int:
    """Closed loop with no reaction delay: fn(state, t) is the tick's Move (or None), built into a record the way
    arcade.bots does; stops after the tick where until(game). Returns the ticks run."""
    before, cal = None, Calibration()
    i0 = getattr(game, "_puppet_i", 0)                      # a second call goes on where the first stopped
    for i in range(i0, i0 + max_ticks):
        game._puppet_i = i + 1
        move = fn(game.debug_state(), i * TICK)
        sensed, before = bots._sensed(i, move, before, cal)
        step(game, sensed)
        if each is not None:
            each(game)
        if until(game):
            return i + 1 - i0
    raise AssertionError(f"until never held in {max_ticks} ticks: {game.debug_state()}")


STILL = Move(x=0.5)


def dance(t: float) -> Move:
    return Move(x=0.5, hand="both", wrist_y=0.2 if int(t / 0.3) % 2 == 0 else 0.8)


def over(game) -> bool:
    return game.debug_state()["phase"] == "over"


# ----- registration -----

def test_registered_and_declared():
    assert get_game("freeze") is Freeze and GAME is Freeze and "freeze" in MENU_ORDER
    info = Freeze.info
    assert (info.name, info.title, info.verb) == ("freeze", "FREEZE", "FREEZE")
    assert info.needs == frozenset({"pose"}) and info.layouts == frozenset({"128x64"})
    assert info.players == 2 and info.exit_gesture is False and info.kind == "score"
    assert Freeze.PHASES == ("ready", "play", "over")
    assert Freeze.CAPTION_KEYS == ("phase", "light", "score")
    assert set(Freeze.SCENARIOS) == {"canonical", "idle_body", "nobody", "duo"}
    assert (REDS, GREEN_SECONDS, RED_SECONDS, GRACE) == (6, (3.0, 6.0), (2.5, 4.0), 0.5)
    assert (MOVE_TRAVEL, DANCE_TRAVEL, READY_SECONDS, TOPPLE_SECONDS, OVER_SECONDS) == (0.25, 0.5, 3.0, 1.0, 3.0)
    assert (WIN_SCORE, RED_AREA, HINT_IDLE_SECONDS) == (4, 0.12, 2.0)


# ----- the lights -----

def still_lights(i: int):
    game = make(i=i)
    seen = []
    puppet(game, lambda s, t: STILL, over, each=lambda g: seen.append(g.debug_state()["light"]))
    return game, seen


def runs(seen):
    out = []
    for light in seen:
        if out and out[-1][0] == light:
            out[-1][1] += 1
        else:
            out.append([light, 1])
    return [(light, n * TICK) for light, n in out if light != "none"]


@pytest.mark.parametrize("i", range(3))
def test_the_lights_follow_the_rng_plan(i):
    game, seen = still_lights(i)
    spans = runs(seen)
    assert [light for light, _ in spans] == ["green", "red"] * REDS, (seed("128x64", i), spans)
    for (light, seconds), (plan_light, planned) in zip(spans, game.plan):
        lo, hi = GREEN_SECONDS if light == "green" else RED_SECONDS
        assert plan_light == light and lo <= planned <= hi, (seed("128x64", i), game.plan)
        assert abs(seconds - planned) <= 2 * TICK, (light, seconds, planned)
    again = make(i=i)
    assert again.plan == game.plan and make(i=i + 1).plan != game.plan


def test_the_game_starts_in_ready_with_no_light():
    game = make()
    state = game.debug_state()
    assert state["phase"] == "ready" and state["light"] == "none" and state["reds_left"] == REDS


# ----- out, the grace, the count -----

def test_moving_after_the_grace_is_out():
    game = make(i=1)

    def fn(state, t):
        if state["light"] == "red" and state["in_grace"]:
            return STILL
        return dance(t)
    puppet(game, fn, over)
    state = game.debug_state()
    assert state["out"] is True and state["score"] == 0 and state["phase"] == "over", (seed("128x64", 1), state)
    assert game.scores.best() is None


def test_moving_inside_the_grace_is_not_out():
    game = make(i=1)

    def fn(state, t):
        if state["light"] == "red":
            return dance(t) if state["in_grace"] else STILL
        return dance(t) if state["light"] == "green" else STILL
    puppet(game, fn, lambda g: g.debug_state()["score"] >= 1)
    state = game.debug_state()
    assert state["out"] is False and state["score"] == 1 and state["phase"] == "play", state


def _still_under_noise(i: int):
    s = seeds(Freeze, "128x64", 5)[i]
    person = Person(cam_x(0.3 + 0.1 * i), id=s % 1000 + 1)
    return s, from_first_body(degrade(scene(persons=[person], ticks=round(60 / TICK)), **REAL_NOISE))


@pytest.mark.parametrize("i", range(5))
def test_a_still_body_under_real_noise_is_never_out(i):
    """Through every red: a still body's jitter, dropouts and capture latency never reach MOVE_TRAVEL."""
    s, frames = _still_under_noise(i)
    game = make(i=i)
    for _ in drive(game, frames, until=over):
        state = game.debug_state()
        assert state["out"] is False and state["out2"] is False, (s, game.t, state)
    state = game.debug_state()
    assert state["phase"] == "over" and state["score"] == 0 and state["reds_left"] == 0, (s, state)
    assert game.scores.best() is None


def test_a_red_counts_only_after_a_dance():
    """The puppet dances in every other green: only the reds after those count."""
    game = make(i=2)
    mem = {"prev": "none", "green": -1}

    def fn(state, t):
        if state["light"] == "green" and mem["prev"] != "green":
            mem["green"] += 1
        mem["prev"] = state["light"]
        return dance(t) if state["light"] == "green" and mem["green"] % 2 == 0 else STILL
    puppet(game, fn, over)
    state = game.debug_state()
    assert state["out"] is False and state["score"] == REDS // 2 and state["reds_left"] == 0, state


def test_an_out_seat_counts_nothing_after():
    game = make(i=0)
    puppet(game, lambda s, t: dance(t), over)
    state = game.debug_state()
    assert state["out"] is True and state["score"] == 0, state


def waving(person: Person, start: float, end: float) -> Person:
    """person waves both arms (0.3 s up, 0.3 s down) from start to end."""
    t = start
    while t < end:
        for hand in ("left", "right"):
            person.wrist(hand, 0.2, 0.8, 0.3, at=t)
            person.wrist(hand, 0.8, 0.2, 0.3, at=t + 0.3)
        t += 0.6
    return person


def test_a_second_body_joins_on_the_next_green():
    """B arrives during the first red and waves all the while: not judged in that red (it has not joined), judged
    in the next. A stands still."""
    game = make(i=3)
    red1 = READY_SECONDS + game.plan[0][1]
    red1_end = red1 + game.plan[1][1]
    a = Person(cam_x(0.3), height=0.62, id=1)
    b = waving(Person(cam_x(0.7), id=2).arrive(red1 + 0.2), red1 + 0.2, 50.0)
    frames = scene(persons=[a, b], ticks=round(55 / TICK))
    for _ in drive(game, frames, until=over):
        if red1 + 1.0 < game.t < red1_end + 0.3:
            assert game.debug_state()["out2"] is False, (game.t, game.debug_state())
    state = game.debug_state()
    assert state["out2"] is True and state["out"] is False and state["phase"] == "over", state


# ----- shown -----

def red_share(frame: np.ndarray) -> float:
    return float(np.mean((frame == RED).all(axis=2)))


def test_the_red_light_keeps_its_area(font5x7):
    game = make(i=1)
    canvas = Canvas(*WALL, font5x7)
    shares, borders, lights = [], [], []

    def each(g):
        canvas.clear()
        g.draw(canvas)
        light = g.debug_state()["light"]
        lights.append(light)
        borders.append(tuple(int(v) for v in canvas.frame[30, 0]))
        if light == "red":
            shares.append(red_share(canvas.frame))
    puppet(game, lambda s, t: STILL, over, each=each)
    assert shares and max(shares) <= RED_AREA, max(shares)
    assert max(shares) > 0.03                                    # the border and the word are red
    changes = sum(1 for a, b in zip(borders, borders[1:]) if a != b)
    light_changes = sum(1 for a, b in zip(lights, lights[1:]) if a != b)
    assert changes == light_changes == 2 * REDS + 1, (changes, light_changes)    # in, 2 x REDS - 1 between, out
    assert {b for b, l in zip(borders, lights) if l == "green"} == {(0, 200, 0)}
    assert {b for b, l in zip(borders, lights) if l == "red"} == {RED}


def test_the_word_shows_at_2x_over_a_black_box(font5x7):
    game = make(i=1)
    canvas = Canvas(*WALL, font5x7)
    seen = {}

    def each(g):
        light = g.debug_state()["light"]
        if light in ("green", "red") and light not in seen:
            canvas.clear()
            g.draw(canvas)
            seen[light] = feel.find_text(canvas.frame, font5x7, "DANCE" if light == "green" else "FREEZE",
                                         scales=(2,))
    puppet(game, lambda s, t: STILL, over, each=each)
    for light in ("green", "red"):
        x, y, mask = seen[light]
        assert 44 <= y and y + mask.shape[0] <= 58 and abs(x + mask.shape[1] / 2 - WALL[0] / 2) <= 2, (light, x, y)


def test_ready_says_the_rules_at_1x(font5x7):
    game = make()
    canvas = Canvas(*WALL, font5x7)
    game.draw(canvas)
    assert feel.find_text(canvas.frame, font5x7, "DANCE ON GREEN", scales=(1,)) is not None
    assert feel.find_text(canvas.frame, font5x7, "FREEZE ON RED", scales=(1,)) is not None


def test_score_is_drawn_at_2x_from_the_first_tick(font5x7):
    game = make()
    canvas = Canvas(*WALL, font5x7)
    game.draw(canvas)
    assert feel.find_text(canvas.frame, font5x7, "0", scales=(2,)) is not None
    game.seats[0].score = 7
    canvas.clear()
    game.draw(canvas)
    assert feel.find_text(canvas.frame, font5x7, "7", scales=(2,)) is not None
    assert feel.find_text(canvas.frame, font5x7, "7", scales=(1,)) is None


def figure_pixels(frame: np.ndarray) -> np.ndarray:
    """The amber of a player's figure (red and green both lit, blue 0): not the border, the word or the score."""
    return (frame[..., 0] > 0) & (frame[..., 1] > 0) & (frame[..., 2] == 0)


def test_an_out_figure_topples_and_fades(font5x7):
    game = make(i=1)
    canvas = Canvas(*WALL, font5x7)
    boxes = []

    def fn(state, t):
        if state["light"] == "red" and not state["in_grace"]:
            return dance(t)
        return STILL
    puppet(game, fn, lambda g: g.debug_state()["out"])
    t_out = game.t

    def each(g):
        canvas.clear()
        g.draw(canvas)
        m = figure_pixels(canvas.frame)
        ys, xs = np.nonzero(m)
        boxes.append((g.t - t_out, None if not len(ys) else (xs.max() - xs.min() + 1, ys.max() - ys.min() + 1,
                                                            int(canvas.frame[m][:, 0].max()))))
    puppet(game, lambda s, t: STILL, lambda g: g.t >= t_out + 2.5, each=each)
    first, mid, late = boxes[1][1], boxes[round(TOPPLE_SECONDS / TICK) + 1][1], boxes[-1][1]
    assert first[1] > first[0], first                                    # still upright at the start: taller
    assert mid[0] > mid[1], mid                                          # lying: wider than tall
    assert late is None or late[2] < mid[2] // 3, (mid, late)            # faded
    assert boxes[-1][1] is None or boxes[-1][1][2] < 60
    state = game.debug_state()
    assert state["player_xy"] is None or 0 <= state["player_xy"][0] < WALL[0]


@pytest.mark.parametrize("name", ["canonical", "duo"])
def test_own_drawing_keeps_rows_60_to_63_dark(font5x7, name):
    """The runner's marker and echoes own rows 60 to 63: the game's own frames never light them, a topple included."""
    game = make()
    canvas = Canvas(*WALL, font5x7)
    lit, fell = [], False
    for _ in drive(game, Freeze.SCENARIOS[name](), until=lambda g: g.done()):
        canvas.clear()
        game.draw(canvas)
        fell = fell or any(seat.fall is not None for seat in game.seats)
        if canvas.frame[60:].any():
            lit.append(round(game.t, 2))
    assert fell, f"{name}: nobody toppled, so the rows were never tested with a topple"
    assert not lit, f"{name}: rows 60 to 63 lit on {len(lit)} ticks, from t {lit[:3]}"


def test_an_out_figure_keeps_the_flash_rule(font5x7):
    """Through the real runner: a body that moves in every red is out; its topple and fade hold 0 governor ticks."""
    cfg = make_cfg(WALL)
    s = seed("128x64", 4)

    def feed(runner):
        before, cal = None, Calibration()
        for i in range(round(25 / TICK)):
            state = runner.game.debug_state() if runner.game is not None else {}
            move = dance(i * TICK) if state.get("light", "none") != "none" or state.get("phase") != "ready" else STILL
            sensed, before = bots._sensed(i, move, before, cal)
            yield sensed
            if runner.current_name != "freeze":
                return
    _, runner = run_headless(cfg, font5x7, Freeze, feed, seed=s, raw=True)
    state = runner.game.debug_state()
    assert state["out"] is True and state["phase"] == "over", (s, state)
    assert runner.governor.held_ticks == 0, s
    assert flash_area(runner.raw_frames) < 0.1, s


@pytest.mark.parametrize("name", ["canonical", "duo"])
def test_own_drawing_keeps_the_flash_rule(font5x7, name):
    s = seed("128x64", 5)
    _, runner = run_headless(make_cfg(WALL), font5x7, Freeze, Freeze.SCENARIOS[name](), seed=s, raw=True)
    raw = runner.raw_frames
    assert len(raw) > 300
    assert flash_area(raw) < 0.1 and runner.governor.held_ticks == 0, (s, runner.governor.held_ticks)
    assert square_flashes(raw) <= BUDGET, s


def test_the_column_backlash_holds_one_column(font5x7):
    game = make()

    def head_x(zone_x: float) -> float:
        puppet(game, lambda s, t: Move(x=zone_x), lambda g: True, max_ticks=1)
        return game.debug_state()["player_xy"][0]
    base = 64 / 127                                                # a whole column: no rounding either way
    x0 = head_x(base)
    for _ in range(3):
        head_x(base)
    assert head_x(base + 1.0 / 127) == x0                        # a one column jitter does not move it
    assert head_x(base + 2.0 / 127) == pytest.approx(x0 + 1)     # two columns move it by one
    assert head_x(base + 8.0 / 127) == pytest.approx(x0 + 7)


# ----- two players, a solo win -----

def test_last_one_standing_with_two_and_nothing_recorded(font5x7):
    s = seed("128x64", 3)
    _, game, runner = run(Freeze, Freeze.SCENARIOS["duo"](), WALL, font5x7, seed=s)
    state = game.debug_state()
    assert state["phase"] == "over" and state["out"] is False and state["out2"] is True, (s, state)
    assert game.scores.best() is None
    assert game.done() or runner.current_name != "freeze"


def test_a_solo_who_survives_wins_and_done_after_the_hold():
    game = make(i=5)
    bot = for_game(Freeze)[0]["good"]()
    puppet(game, lambda s, t: bot(s, t), over)
    state = game.debug_state()
    assert state["out"] is False and state["score"] == REDS and state["reds_left"] == 0, (seed("128x64", 5), state)
    assert game.scores.best() == REDS
    assert not game.done()
    puppet(game, lambda s, t: bot(s, t), lambda g: g.done())
    assert game.done() and game.phase_t >= OVER_SECONDS - TICK
    assert game.debug_state()["score"] == REDS and game.scores.best() == REDS


def test_exit_gesture_is_off(font5x7):
    """Both hands up for 5 s (a freeze with the arms raised) leaves the session on."""
    frames = scene(persons=[Person(cam_x(0.5), id=1).both_hands_up(0.5, 8.0)], ticks=round(6.5 / TICK))
    _, game, runner = run(Freeze, frames, WALL, font5x7, seed=seed("128x64", 6))
    assert runner.current_name == "freeze" and game.debug_state()["phase"] != "over"


def test_a_player_who_leaves_is_out_without_a_topple():
    game = make(i=1)
    frames = scene(persons=[Person(cam_x(0.5), id=1).leave(5.0)], ticks=round(15 / TICK))
    for _ in drive(game, frames, until=lambda g: g.debug_state()["out"]):
        pass
    state = game.debug_state()
    assert state["out"] is True and game.t - 5.0 <= 1.0 and game.seats[0].fall is None, (game.t, state)


# ----- movement (C41, C42), the hint -----

def test_idle_body_scores_nothing(font5x7):
    s = seed("128x64", 2)
    _, game, _ = run(Freeze, Freeze.SCENARIOS["idle_body"](), WALL, font5x7, seed=s)
    state = game.debug_state()
    assert state["score"] == 0 and state["out"] is False, (s, state)     # the session ends inactive at 35 s, or over
    assert game.scores.best() is None
    probe = make()
    for _ in drive(probe, Freeze.SCENARIOS["idle_body"](), until=lambda g: g.debug_state()["hint"]):
        pass
    assert probe.debug_state()["hint"] is True and probe.t <= 3.0, probe.t
    assert HINT_IDLE_SECONDS - TICK <= probe.t


def test_active_follows_the_travel_in_a_second():
    game = make(i=1)
    seen = []
    puppet(game, lambda s, t: STILL if t < 1.0 else dance(t), lambda g: g.t >= 3.0,
           each=lambda g: seen.append(g.debug_state()["active"]))
    assert not any(seen[:25]) and any(seen[40:]) and all(type(a) is bool for a in seen)


# ----- the debug state, scenarios, the lobby -----

def test_debug_state_is_clean(font5x7):
    game = make()
    canvas = Canvas(*WALL, font5x7)
    keys = {"phase", "light", "score", "other", "out", "out2", "danced", "reds_left", "in_grace", "active", "hint",
            "player_xy", "player2_xy"}
    lit = 0
    for _ in drive(game, Freeze.SCENARIOS["canonical"](), until=lambda g: g.done()):
        state = game.debug_state()
        assert not [k for k in state if reserved(k)], state
        assert keys <= set(state), keys - set(state)
        assert type(state["active"]) is bool and type(state["hint"]) is bool and type(state["out"]) is bool
        assert state["phase"] in Freeze.PHASES and all(k in state for k in Freeze.CAPTION_KEYS)
        canvas.clear()
        game.draw(canvas)
        xy = state["player_xy"]
        if xy is not None and not state["out"]:
            x, y = xy
            assert 0 <= x < WALL[0] and 0 <= y < WALL[1], state
            if y < 18 and (x < 14 or x >= WALL[0] - 16):          # the score's black box may cover a head at an edge
                continue
            assert canvas.frame[int(y), int(x)].any(), state
            lit += 1
    assert lit > 100


def test_required_scenarios_start_with_an_empty_wall():
    assert set(REQUIRED_SCENARIOS) <= set(Freeze.SCENARIOS)
    for name in Freeze.SCENARIOS:
        assert list(Freeze.SCENARIOS[name]()), name
    canonical = list(Freeze.SCENARIOS["canonical"]())
    assert len(canonical) == round(CANONICAL_SECONDS / TICK)
    assert all(not f.bodies for f in canonical[:round(2.0 / TICK)]) and canonical[round(2.0 / TICK) + 1].bodies
    assert len(list(Freeze.SCENARIOS["idle_body"]())) == round(60 / TICK)
    assert len(list(Freeze.SCENARIOS["nobody"]())) == round(30 / TICK)
    assert all(not f.bodies for f in Freeze.SCENARIOS["nobody"]())
    assert max(len(f.bodies) for f in Freeze.SCENARIOS["duo"]()) == 2


def test_canonical_drives_the_lobby_to_freeze(font5x7):
    cfg = make_cfg(WALL)
    lobby = Lobby([Freeze], cfg)
    _, runner = run_headless(cfg, font5x7, [Freeze], Freeze.SCENARIOS["canonical"](), trace=True, lobby=lobby,
                             seed=seeds(Freeze, "128x64", 1)[0])
    games = [s["game"] for s in runner.trace]
    assert games[0] == "lobby" and "freeze" in games
    first = games.index("freeze")
    raised = round(4.5 / TICK)
    assert raised <= first <= raised + 1, (first, raised)
    frames = list(Freeze.SCENARIOS["canonical"]())
    xs = [f.bodies[0].zone_x for f in frames[:round(feel.FEEL_SECONDS / TICK)] if f.bodies]
    assert min(xs) < 0.05 and max(xs) > 0.95, (min(xs), max(xs))        # the sweep fidelity and range need


def test_seeded_runs_repeat(font5x7):
    a, _, _ = run(Freeze, Freeze.SCENARIOS["canonical"](), WALL, font5x7, ticks=400, seed=seed("128x64", 6))
    b, _, _ = run(Freeze, Freeze.SCENARIOS["canonical"](), WALL, font5x7, ticks=400, seed=seed("128x64", 6))
    c, _, _ = run(Freeze, Freeze.SCENARIOS["canonical"](), WALL, font5x7, ticks=400, seed=seed("128x64", 7))
    assert all(np.array_equal(x, y) for x, y in zip(a, b))
    assert any(not np.array_equal(x, y) for x, y in zip(a, c))


# ----- bots -----

def test_bots_module_is_found():
    found, won = for_game(Freeze)
    assert set(found) == {"good", "lazy"} and found["good"] is not found["lazy"]
    assert won({"phase": "over", "out": False, "score": WIN_SCORE})
    assert not won({"phase": "over", "out": False, "score": WIN_SCORE - 1})
    assert not won({"phase": "over", "out": True, "score": REDS})
    assert not won({"phase": "play", "out": False, "score": REDS})


def test_good_beats_lazy_beats_nobody():
    ss = seeds(Freeze, "128x64", 5)
    wins = {name: sum(played(Freeze, name, s).won for s in ss) for name in ("good", "lazy", "none")}
    assert wins["good"] >= 4 and wins["none"] == 0 and wins["lazy"] < wins["good"], (ss, wins)


def test_good_round_length_in_band():
    plays = [played(Freeze, "good", s) for s in seeds(Freeze, "128x64", 5)]
    lengths = [p.seconds for p in plays if p.done]
    assert len(lengths) >= 4, [(p.seed, p.seconds, p.done) for p in plays]
    assert 20 <= statistics.median(lengths) <= 120, ([p.seed for p in plays], lengths)


def test_feel_file_overrides_have_reasons():
    data = tomllib.loads((Path(__file__).resolve().parents[2] / "arcade/games/freeze_feel.toml").read_text())
    assert data["fidelity"] == {"input": "zone_x", "xy": "player_xy", "axis": 0}
    assert "budgets" not in data                                   # the plan: no budget override
    for metric, table in data.get("budgets", {}).get("128x64", {}).items():
        assert table.get("reason", "").strip(), metric
