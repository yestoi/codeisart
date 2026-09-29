"""Quick Draw (spec 8, game 4): hands low, WAIT, then DRAW!; the first hand up wins the round, a hand up in WAIT loses
it; first to 3 rounds. One bar per seat shows the hand's height, and the draw is the bar crossing the line."""
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
from arcade.bots import _sensed, for_game, seeds
from arcade.calibration import Calibration
from arcade.canvas import Canvas
from arcade.game import REQUIRED_SCENARIOS, reserved
from arcade.games import MENU_ORDER, get_game
from arcade.games.quickdraw import (ACTIVE_PX, ARM_PX, BAR_BOTTOM, CPU_COLOR, CPU_DRAW, DRAW_COLOR, DRAW_TIMEOUT,
                                    GAME, GLYPH_H, HINT_IDLE_SECONDS, HINT_LINES, LINE_COLOR, LINE_Y, OVER_SECONDS,
                                    READY_SECONDS, RESULT_SECONDS, WAIT_SECONDS, WIN_ROUNDS, Quickdraw, idle_body)
from arcade.games.quickdraw_bots import Good
from arcade.headless import OPENING_NIGHT, RecordingDisplay, run_headless
from arcade.juice import PLAYER_COLORS, Juice
from arcade.scores import Scores
from arcade.sources.actors import REAL_NOISE, TICK, Person, degrade, scene
from tests.arcade.helpers import make_cfg, played, run

WALL = (128, 64)


def seed(layout: str, i: int) -> int:
    return zlib.crc32(f"quickdraw:{layout}:{i}".encode())


def make(size=WALL, i=0) -> Quickdraw:
    """A Quickdraw reset the way the runner resets it, for tests that poke its state."""
    game = Quickdraw()
    layout = f"{size[0]}x{size[1]}"
    game.scores = Scores(None, lambda: OPENING_NIGHT).for_game("quickdraw", layout)
    game.reset(size, random.Random(seed(layout, i)), Juice(random.Random(1), size))
    return game


def step(game: Quickdraw, frame) -> None:
    """One tick with the runner's lock applied: the two largest bodies are player and player2."""
    bodies = frame.bodies
    game.update(dataclasses.replace(frame, player=bodies[0] if bodies else None,
                                    player2=bodies[1] if len(bodies) > 1 else None), TICK)


def drive(game: Quickdraw, frames, until=None):
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


def from_first_body(frames):
    """frames from the first one with a body in it (a degraded scene has no capture for its first 0.15 s)."""
    started = False
    for f in frames:
        started = started or bool(f.bodies)
        if started:
            yield f


def hand(person: Person, at: float, hold: float = 1.0, v: float = 0.1) -> Person:
    """The wrist from hip height to v (reach box, 0 top) in 0.15 s at `at`, then held for `hold` s."""
    return person.wrist("right", 1.0, v, 0.15, at=at).wrist("right", v, v, hold, at=at + 0.15)


def pinned(game: Quickdraw, wait: float, cpu: float) -> None:
    """The round in play gets a known WAIT and a CPU that draws `cpu` s after DRAW."""
    game._wait, game._cpu = wait, [cpu, cpu]


def test_registered_and_declared():
    assert get_game("quickdraw") is Quickdraw and GAME is Quickdraw and "quickdraw" in MENU_ORDER
    info = Quickdraw.info
    assert (info.name, info.title, info.verb) == ("quickdraw", "DRAW!", "DRAW")
    assert info.needs == frozenset({"pose"}) and info.layouts == frozenset({"128x64"})
    assert info.players == 2 and info.kind == "score"
    assert Quickdraw.PHASES == ("ready", "play", "result", "over")
    assert Quickdraw.CAPTION_KEYS == ("phase", "signal", "left", "right")
    assert set(Quickdraw.SCENARIOS) == {"canonical", "idle_body", "nobody", "duel", "early"}
    assert (WIN_ROUNDS, WAIT_SECONDS, CPU_DRAW) == (3, (2.0, 5.0), CPU_DRAW) and 0 < CPU_DRAW[0] < CPU_DRAW[1] < DRAW_TIMEOUT


def test_bar_follows_hand_height():
    """The wrist from hip height (down) to the top of the reach box moves the bar from BAR_BOTTOM to BAR_TOP."""
    game = make()
    p = Person(0.3, id=1).wrist("right", 1.0, 1.0, 2.0, at=0.0).wrist("right", 1.0, 0.0, 0.5, at=2.0) \
        .wrist("right", 0.0, 0.0, 5.0, at=2.5)
    ys = {}
    for frame in drive(game, scene(persons=[p], ticks=150)):
        ys[round(game.t, 2)] = game.debug_state()["hand_xy"][1]
    assert ys[1.5] == 56 and ys[4.5] == 16, (ys[1.5], ys[4.5])
    assert ys[2.0] == 56 and 16 < ys[2.3] < 56          # halfway up in between: the bar follows, it does not snap


def test_first_draw_after_the_signal_wins_the_round():
    """A hand that crosses the line 0.3 s after DRAW beats a CPU that draws 0.4 s after it; DRAW! comes with one
    white flash. (The bar lags the wrist by the Glide's 0.1 s, so the wrist starts at 3.13 s.)"""
    game = make()
    p = hand(Person(0.3, id=1), at=3.13)         # play starts at 1.0 s; WAIT 2.0 s pinned below: DRAW at 3.0 s
    frames = scene(persons=[p], ticks=300)
    advance(game, frames, "play")
    pinned(game, wait=2.0, cpu=0.4)
    flashes = []
    for _ in drive(game, frames, until=lambda g: g.debug_state()["phase"] == "result"):
        flashes.append(game.fx.debug_state()["fx_flash"])
    state = game.debug_state()
    assert (state["left"], state["right"], state["phase"]) == (1, 0, "result"), state
    assert 0.25 <= state["react"] < 0.4, state
    assert 1.0 in flashes and game._flashed is True, flashes


def test_the_cpu_that_draws_first_wins_the_round():
    game = make()
    frames = scene(persons=[hand(Person(0.3, id=1), at=3.3)], ticks=300)
    advance(game, frames, "play")
    pinned(game, wait=2.0, cpu=0.2)
    advance(game, frames, "result")
    state = game.debug_state()
    assert (state["left"], state["right"]) == (0, 1) and state["react"] == pytest.approx(0.2, abs=0.01), state


def test_a_hand_up_during_wait_loses_the_round():
    game = make()
    frames = scene(persons=[hand(Person(0.3, id=1), at=2.0)], ticks=300)
    advance(game, frames, "play")
    pinned(game, wait=4.0, cpu=0.5)
    advance(game, frames, "result")
    state = game.debug_state()
    assert (state["left"], state["right"], state["react"]) == (0, 1, None), state
    canvas = Canvas(*WALL, feel_font())
    game.draw(canvas)
    red = np.argwhere((canvas.frame == (255, 0, 0)).all(axis=2))
    assert len(red) > 20 and red[:, 1].max() < WALL[0] // 2, "TOO SOON over the loser's half, in red"


def feel_font():
    from arcade.bots import ROOT, _font
    return _font(ROOT / make_cfg(WALL).font_path)


def test_too_soon_gives_the_round_to_the_other_human():
    game = make()
    frames = scene(persons=[hand(Person(0.3, id=1), at=2.0), Person(0.7, id=2)], ticks=300)
    advance(game, frames, "play")
    pinned(game, wait=4.0, cpu=0.5)
    advance(game, frames, "result")
    state = game.debug_state()
    assert state["humans"] == 2 and (state["left"], state["right"]) == (0, 1), state


def test_nobody_drawing_is_a_void_round_in_a_duel():
    game = make()
    frames = scene(persons=[Person(0.3, id=1), Person(0.7, id=2)], ticks=600)
    advance(game, frames, "play")
    pinned(game, wait=2.0, cpu=0.5)
    start = game.t
    advance(game, frames, "ready")
    state = game.debug_state()
    assert (state["left"], state["right"], state["round"]) == (0, 0, 2), state
    assert game.t - start == pytest.approx(2.0 + DRAW_TIMEOUT, abs=0.1), game.t - start


def test_ready_waits_for_hands_down():
    game = make()
    p = Person(0.3, id=1).wrist("right", 0.1, 0.1, 3.0, at=0.0)         # a hand up at launch, lowered at 3.0 s
    frames = scene(persons=[p], ticks=300)
    for _ in drive(game, frames, until=lambda g: g.t >= 2.5):
        assert game.debug_state()["phase"] == "ready"
    advance(game, frames, "play")
    assert game.t >= 3.0 and game.t <= 3.0 + READY_SECONDS + 0.5, game.t


def test_a_hand_that_never_sat_below_the_arm_line_does_not_draw():
    """v 0.48 is a bar 2.4 px below the line: ready lets play start, but the bar has not sat ARM_PX below it, so
    rising over the line is no draw (and no too soon)."""
    assert ARM_PX == 6
    game = make()
    p = Person(0.3, id=1).wrist("right", 0.48, 0.48, 3.4, at=0.0).wrist("right", 0.3, 0.3, 5.0, at=3.4)
    frames = scene(persons=[p], ticks=300)
    advance(game, frames, "play")
    pinned(game, wait=2.0, cpu=0.6)
    advance(game, frames, "result")
    state = game.debug_state()
    assert (state["left"], state["right"]) == (0, 1) and state["react"] == pytest.approx(0.6, abs=0.01), state


def rig_over(game, frames):
    """Player 1 has 2 rounds and draws 0.3 s after DRAW; the round is played to its result."""
    advance(game, frames, "play")
    game.seats[0].rounds = 2
    pinned(game, wait=2.0, cpu=0.6)
    advance(game, frames, "result")


def test_first_to_three_ends_the_match_and_done_after_the_hold():
    game = make()
    frames = scene(persons=[hand(Person(0.3, id=1), at=3.3)], ticks=600)
    rig_over(game, frames)
    assert game.debug_state()["left"] == WIN_ROUNDS and not game.done()
    for _ in drive(game, frames, until=lambda g: g.debug_state()["phase"] == "over"):
        assert not game.done()
    over_at = game.t
    assert game.scores.best() == WIN_ROUNDS and game.debug_state()["score"] == WIN_ROUNDS
    assert game.fx.debug_state()["fx_particles"] > 0                       # a solo win celebrates
    assert over_at > 0 and not game.done()
    for _ in drive(game, frames, until=lambda g: g.done()):
        assert game.debug_state()["score"] == WIN_ROUNDS
    assert game.done() and game.t - over_at == pytest.approx(OVER_SECONDS, abs=TICK * 2)
    assert RESULT_SECONDS > 0


def test_a_lost_match_stores_no_best_without_a_draw():
    """The CPU takes 3 rounds from a hand that never rises: over, score 0, no best (C41)."""
    game = make()
    for _ in drive(game, scene(persons=[Person(0.3, id=1)], ticks=1500), until=lambda g: g.done()):
        pass
    state = game.debug_state()
    assert game.done() and (state["left"], state["right"], state["score"]) == (0, WIN_ROUNDS, 0), state
    assert game.scores.best() is None


def test_phases_only_go_forward_and_leave_play_every_round():
    game = make()
    seen = []
    for _ in drive(game, scene(persons=[Person(0.3, id=1)], ticks=1500), until=lambda g: g.done()):
        phase = game.debug_state()["phase"]
        if not seen or seen[-1] != phase:
            seen.append(phase)
    allowed = {"ready": {"play"}, "play": {"result", "ready"}, "result": {"ready", "over"}, "over": set()}
    for a, b in zip(seen, seen[1:]):
        assert b in allowed[a], seen
    assert seen[0] == "ready" and seen[-1] == "over" and seen.count("play") == WIN_ROUNDS, seen


def test_waits_and_cpu_draws_come_from_the_seeded_rng_within_their_bands():
    game = make()
    waits, cpus = [], []
    last = None
    for _ in drive(game, scene(persons=[Person(0.3, id=1)], ticks=1500), until=lambda g: g.done()):
        if game.phase == "play" and game._wait != last:
            last = game._wait
            waits.append(last)
            cpus.append(game._cpu[1])
    assert len(waits) == WIN_ROUNDS and len(set(waits)) == len(waits), waits
    assert all(WAIT_SECONDS[0] <= x <= WAIT_SECONDS[1] for x in waits), waits
    assert all(CPU_DRAW[0] <= x <= CPU_DRAW[1] for x in cpus), cpus


def test_idle_body_scores_nothing(font5x7):
    s = seed("128x64", 8)
    _, game, runner = run(Quickdraw, Quickdraw.SCENARIOS["idle_body"](), WALL, font5x7, seed=s)
    state = game.debug_state()
    assert state["humans"] == 1 and state["phase"] == "over", (s, state)
    assert state["score"] == 0 == state["left"] and state["right"] == WIN_ROUNDS, (s, state)
    assert game.scores.best() is None, s
    assert not for_game(Quickdraw)[1](state)


def test_idle_body_gets_the_hint_within_three_seconds():
    game = make()
    for _ in drive(game, idle_body(), until=lambda g: g.debug_state()["hint"]):
        pass
    assert game.debug_state()["hint"] and game.t <= 3.0, game.t
    assert HINT_IDLE_SECONDS <= 2.0 + 1e-9


def _still_under_noise(i: int, persons: int = 1):
    s = seeds(Quickdraw, "128x64", 10)[i]
    ids = [s % 1000 + 1000 * k for k in range(persons)]
    people = [Person(x, id=body_id) for x, body_id in zip((0.3, 0.7), ids)]
    return s, from_first_body(degrade(scene(persons=people, ticks=round(60 / TICK)), **REAL_NOISE))


def test_a_still_body_under_real_noise_never_draws():
    """5 seeds of a hand that hangs under degrade(REAL_NOISE): the bar never reaches the line, no round, no best."""
    out = {}
    for i in range(5):
        s, frames = _still_under_noise(i)
        game = make(i=i)
        top = 64.0
        for _ in drive(game, frames, until=lambda g: g.done()):
            top = min(top, game.debug_state()["hand_xy"][1])
        state = game.debug_state()
        out[s] = (state["left"], game.scores.best(), state["right"], round(top, 1))
    assert all(v[0] == 0 and v[1] is None and v[2] == WIN_ROUNDS and v[3] > 32 + ARM_PX for v in out.values()), out


def test_a_still_body_under_real_noise_is_not_input():
    s, frames = _still_under_noise(1)
    game = make(i=1)
    active = [game.debug_state()["active"] for _ in drive(game, frames, until=lambda g: g.done())]
    assert active and not any(active[1:]), (s, active.index(True, 1) * TICK)


def test_duel_first_hand_wins_and_records_nothing():
    game = make()
    for _ in drive(game, Quickdraw.SCENARIOS["duel"](), until=lambda g: g.done()):
        pass
    state = game.debug_state()
    assert game.done() and state["humans"] == 2 and max(state["left"], state["right"]) == WIN_ROUNDS, state
    assert game.scores.best() is None and state["cpu"] is None


def test_a_second_player_takes_the_cpu_seat_at_the_next_round():
    game = make()
    frames = scene(persons=[Person(0.3, id=1), Person(0.7, id=2).arrive(1.5)], ticks=900)
    advance(game, frames, "play")
    assert game.debug_state()["humans"] == 1 and game.debug_state()["cpu"] == "right"
    for _ in drive(game, frames, until=lambda g: g.debug_state()["phase"] == "result"):
        pass
    state = game.debug_state()
    assert state["humans"] == 1 and (state["left"], state["right"]) == (0, 1), state       # still the CPU's round
    advance(game, frames, "ready")
    state = game.debug_state()
    assert state["humans"] == 2 and state["cpu"] is None and (state["left"], state["right"]) == (0, 1), state


def test_a_player_who_leaves_gives_the_seat_to_the_cpu():
    game = make()
    frames = scene(persons=[Person(0.3, id=1), Person(0.7, id=2).leave(5.0)], ticks=1500)
    assert game.debug_state()["humans"] == 0
    for _ in drive(game, frames, until=lambda g: g.t >= 1.0):
        pass
    assert game.debug_state()["humans"] == 2
    for _ in drive(game, frames, until=lambda g: g.debug_state()["humans"] == 1):
        pass
    assert game.debug_state()["cpu"] == "right" and game.debug_state()["phase"] == "ready"
    advance(game, frames, "result")
    assert game.debug_state()["right"] >= 1, game.debug_state()      # the CPU draws for seat b
    assert game.scores.best() is None


def _leaves_in_result_after_two_rounds(s: int, font):
    """The good bot plays through the real runner (closed loop, as arcade/bots.py plays; `_sensed` is its private
    helper) and walks out of view, no body at all, on the first `result` tick with 2 rounds won. Returns the
    debug_state after every tick, the index of the first state after the leave, and the runner."""
    bot = Good()
    states, gone_at = [], []

    def feed(runner):
        cal, before = Calibration(), None
        for i in range(round(60 / TICK)):
            k = i - 1 - bot.reaction_ticks
            now = states[-1] if states else {}
            if not gone_at and now.get("score", 0) >= 2 and now.get("phase") == "result":
                gone_at.append(len(states))
            move = None if gone_at else bot(states[k] if k >= 0 else {}, i * TICK)
            sensed, before = _sensed(i, move, before, cal)
            yield sensed
            states.append(dict(runner.game.debug_state()))
            if runner.current_name != "quickdraw":
                return

    _, runner = run_headless(make_cfg(WALL), font, Quickdraw, feed, seed=s, display=RecordingDisplay(keep_all=False))
    assert gone_at and runner.current_name != "quickdraw" and runner.lobby.results, (s, states[-1])
    return states, gone_at[0], runner


def test_a_solo_player_who_leaves_in_result_banks_no_round_they_did_not_play(font5x7):
    """it15 review B1: a solo player wins 2 rounds and walks away during `result`. Seat a is player 1's and never
    the CPU's: empty, it draws nothing and wins nothing, so player 1's rounds stay 2 until the runner's leave rule
    ends the session, and the score and best recorded are never over 2."""
    out = {}
    for s in seeds(Quickdraw, "128x64", 5):
        states, at, runner = _leaves_in_result_after_two_rounds(s, font5x7)
        gone_at = [at]
        after = states[at:]
        result, best = runner.lobby.results[-1], runner.game.scores.best()
        out[s] = (result.score, best, after[-1]["left"], after[-1]["right"])
        assert states[gone_at[0] - 1]["left"] == 2, (s, states[gone_at[0] - 1])
        assert max(st["left"] for st in after) == 2, (s, out[s])                   # no round for an empty seat
        assert result.score <= 2 and (best is None or best <= 2), (s, out[s])
        assert all(st["cpu"] != "left" for st in after), s
        empty = [st for st in after if st["humans"] == 0]
        assert empty, (s, after[-1])
        assert all(st["cpu"] == "right" for st in empty), (s, [st["cpu"] for st in empty][:5])  # seat b's CPU only
        assert all(st["left_xy"][1] == BAR_BOTTOM for st in empty), (s, [st["left_xy"] for st in empty])


def test_a_player_back_after_the_grace_gets_seat_a_with_their_rounds_only():
    """Player 1 wins round 1 by a draw, walks out during its result and comes back, a new body, 5 s later. While
    seat a is empty the CPU there would draw first (each round pinned so seat a's CPU, were there one, beats seat
    b's), yet seat a wins nothing; back, the player sits in seat a with the 1 round they won, nothing more."""
    game = make()
    frames = scene(persons=[hand(Person(0.3, id=1), at=3.13).leave(4.0), Person(0.3, id=3).arrive(9.0)],
                   ticks=900)
    advance(game, frames, "play")
    pinned(game, wait=2.0, cpu=0.4)
    advance(game, frames, "result")
    assert game.debug_state()["left"] == 1 and game.seats[0].ctrl == 1, game.debug_state()
    playing = False
    for _ in drive(game, frames, until=lambda g: g.seats[0].ctrl == 3):
        if game.phase == "play" and not playing:
            game._wait, game._cpu = 2.0, [0.3, 0.6]
        playing = game.phase == "play"
        assert game.debug_state()["left"] == 1, (round(game.t, 2), game.debug_state())
    state = game.debug_state()
    assert game.seats[0].ctrl == 3 and state["phase"] == "ready", (round(game.t, 2), state)
    assert (state["left"], state["humans"], state["cpu"]) == (1, 1, "right") and state["right"] >= 1, state


def test_the_hint_is_not_drawn_over_the_reaction_time():
    """In `result` the hint line is not drawn, so the time under DRAW! has its rows to itself: an idle hand, the
    hint up, loses the first round to the CPU's draw, and the rows of the time hold only its white text."""
    game = make()
    advance(game, idle_body(), "result")
    state = game.debug_state()
    assert state["react"] is not None and game._hint_level > 0.0, (state, game._hint_level)
    canvas = Canvas(*WALL, feel_font())
    game.draw(canvas)
    top = round(LINE_Y + 9)
    rows = canvas.frame[top:top + GLYPH_H]
    lit = rows.any(axis=2)
    assert (rows[lit] == DRAW_COLOR).all(), sorted({tuple(int(c) for c in px) for px in rows[lit]})
    found = feel.find_text(canvas.frame, feel_font(), f"{state['react']:.2f}", scales=(1,))
    assert found is not None and found[1] == top, (state["react"], found and found[:2])


def test_debug_state_is_clean():
    game = make()
    canvas = Canvas(*WALL, feel_font())
    states = []
    for name in ("duel", "canonical"):
        game = make()
        for _ in drive(game, Quickdraw.SCENARIOS[name](), until=lambda g: g.t > 30):
            state = game.debug_state()
            states.append(state)
            assert not [k for k in state if reserved(k)], state
            assert type(state["active"]) is bool and type(state["hint"]) is bool
            canvas.clear()
            game.draw(canvas)
            for key in ("hand_xy", "left_xy", "right_xy"):
                x, y = state[key]
                assert 0 <= x < WALL[0] and 0 <= y < WALL[1], (key, state)
                assert canvas.frame[int(y), int(x)].any(), (key, state)
    assert {"phase", "signal", "round", "score", "left", "right", "cpu", "humans", "active", "hint", "hand_xy",
            "left_xy", "right_xy", "wait_left", "react"} <= set(states[-1])
    assert set(Quickdraw.CAPTION_KEYS) <= set(states[-1])
    assert {s["phase"] for s in states} <= set(Quickdraw.PHASES)


def test_draw_works_right_after_reset():
    canvas = Canvas(*WALL, feel_font())
    make().draw(canvas)
    assert canvas.frame.any()


def test_scores_drawn_at_2x_and_the_bottom_rows_stay_free():
    game = make()
    game.seats[0].rounds, game.seats[1].rounds = 1, 2
    canvas = Canvas(*WALL, feel_font())
    game.draw(canvas)
    for points, centre in ((1, WALL[0] / 4), (2, 3 * WALL[0] / 4)):
        found = feel.find_text(canvas.frame, feel_font(), str(points), scales=(2,))
        assert found is not None, points
        x, y, mask = found
        assert mask.shape[0] == 14 and y == 1 and abs(x + mask.shape[1] / 2 - centre) <= 2, (points, x, y, mask.shape)
    assert not canvas.frame[60:].any()


def test_signal_texts_and_colours():
    game = make()
    canvas = Canvas(*WALL, feel_font())
    frames = scene(persons=[Person(0.3, id=1)], ticks=400)
    advance(game, frames, "play")
    pinned(game, wait=2.0, cpu=0.5)
    canvas.clear()
    game.draw(canvas)
    assert feel.find_text(canvas.frame, feel_font(), "WAIT", scales=(2,)) is not None
    assert (canvas.frame == LINE_COLOR).all(axis=2).any() and not (canvas.frame == (255, 255, 255)).all(axis=2).any()
    for _ in drive(game, frames, until=lambda g: g.debug_state()["signal"] == "draw"):
        pass
    canvas.clear()
    game.draw(canvas)
    assert feel.find_text(canvas.frame, feel_font(), "DRAW!", scales=(2,)) is not None
    assert (canvas.frame == CPU_COLOR).all(axis=2).any() and (canvas.frame == PLAYER_COLORS[0]).all(axis=2).any()


def test_hint_fits_and_shows_only_for_an_idle_human():
    canvas = Canvas(*WALL, feel_font())
    assert all(canvas.text_width(line) - 1 <= WALL[0] for line in HINT_LINES)
    game = make()
    frames = scene(persons=[Person(0.3, id=1)], ticks=300)
    for _ in drive(game, frames, until=lambda g: g._hint_level >= 1.0):
        pass
    canvas.clear()
    game.draw(canvas)
    assert (canvas.frame == LINE_COLOR).all(axis=2).sum() > 100
    moving = make()
    p = Person(0.3, id=1).wrist("right", 1.0, 0.0, 1.5, at=0.0).wrist("right", 0.0, 1.0, 1.5, at=1.5)
    for _ in drive(moving, scene(persons=[p], ticks=90)):
        assert not moving.debug_state()["hint"]


def test_active_needs_the_bar_to_move():
    game = make()
    p = Person(0.3, id=1).wrist("right", 1.0, 1.0, 1.0, at=0.0).wrist("right", 1.0, 0.2, 0.6, at=1.0)
    states = [(game.t, game.debug_state()["active"]) for _ in drive(game, scene(persons=[p], ticks=90))]
    assert not any(a for t, a in states if t < 1.0) and any(a for t, a in states if t >= 1.0), states
    assert ACTIVE_PX == 3


def test_seeded_runs_repeat(font5x7):
    a, _, _ = run(Quickdraw, Quickdraw.SCENARIOS["duel"](), WALL, font5x7, ticks=600, seed=seed("128x64", 6))
    b, _, _ = run(Quickdraw, Quickdraw.SCENARIOS["duel"](), WALL, font5x7, ticks=600, seed=seed("128x64", 6))
    c, _, _ = run(Quickdraw, Quickdraw.SCENARIOS["duel"](), WALL, font5x7, ticks=600, seed=seed("128x64", 7))
    assert all(np.array_equal(x, y) for x, y in zip(a, b))
    assert any(not np.array_equal(x, y) for x, y in zip(a, c))


def test_required_scenarios_start_with_an_empty_wall():
    assert set(REQUIRED_SCENARIOS) <= set(Quickdraw.SCENARIOS)
    for name in Quickdraw.SCENARIOS:
        assert list(Quickdraw.SCENARIOS[name]()), name
    canonical = list(Quickdraw.SCENARIOS["canonical"]())
    assert len(canonical) == round(60 / TICK)
    assert all(not f.bodies for f in canonical[:round(2.0 / TICK)]) and canonical[round(2.0 / TICK) + 1].bodies
    assert len(list(Quickdraw.SCENARIOS["idle_body"]())) == round(60 / TICK)
    assert len(list(Quickdraw.SCENARIOS["nobody"]())) == round(30 / TICK)
    assert all(not f.bodies for f in Quickdraw.SCENARIOS["nobody"]())
    assert len(list(Quickdraw.SCENARIOS["duel"]())) == round(50 / TICK)
    assert len(list(Quickdraw.SCENARIOS["early"]())) == round(20 / TICK)


def test_early_scenario_loses_its_first_round():
    game = make()
    advance(game, Quickdraw.SCENARIOS["early"](), "result")
    state = game.debug_state()
    assert (state["left"], state["right"], state["react"]) == (0, 1, None), state


def test_canonical_drives_the_lobby_to_quickdraw(font5x7):
    cfg = make_cfg(WALL)
    lobby = Lobby([Quickdraw], cfg)
    _, runner = run_headless(cfg, font5x7, [Quickdraw], Quickdraw.SCENARIOS["canonical"](), trace=True, lobby=lobby)
    games = [s["game"] for s in runner.trace]
    assert games[0] == "lobby" and "quickdraw" in games
    first = games.index("quickdraw")
    raised = round(4.5 / TICK)                 # the scene frame the hand goes up on
    assert raised <= first <= raised + 1, (first, raised)


def test_bots_module_is_found():
    bots, won = for_game(Quickdraw)
    assert set(bots) == {"good", "lazy"} and bots["good"] is not bots["lazy"]
    assert won({"phase": "over", "score": 3, "left": 3, "right": 1})
    assert not won({"phase": "over", "score": 1, "left": 1, "right": 3})
    assert not won({"phase": "result", "score": 3, "left": 3, "right": 0})
    assert not won({"phase": "over", "score": 0, "left": 0, "right": 0})


def test_good_beats_lazy_beats_nobody():
    ss = seeds(Quickdraw, "128x64", 5)
    wins = {name: sum(played(Quickdraw, name, s).won for s in ss) for name in ("good", "lazy", "none")}
    assert wins["good"] >= 4 and wins["none"] == 0 and wins["lazy"] < wins["good"], (ss, wins)


def test_good_round_length_in_band():
    plays = [played(Quickdraw, "good", s) for s in seeds(Quickdraw, "128x64", 5)]
    lengths = [p.seconds for p in plays if p.done]
    assert len(lengths) >= 4, [(p.seed, p.seconds, p.done) for p in plays]
    assert 20 <= statistics.median(lengths) <= 120, ([p.seed for p in plays], lengths)


def test_feel_file_declares_the_control_and_needs_no_override():
    data = tomllib.loads((Path(__file__).resolve().parents[2] / "arcade/games/quickdraw_feel.toml").read_text())
    assert data["fidelity"] == {"input": "cursor_y", "xy": "hand_xy", "axis": 1}
    assert "budgets" not in data                                # No budget override (the plan)
