"""Jump (spec 8 row 9 as Q99 changed it): a high striker. Stand still, then for JUMP_WINDOW seconds the bar shoots up
with the nose's rise over the torso; the window's best peak stays as a line; past the bell line the bell rings; three
attempts, the best is the night's."""
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
from arcade.flash import flash_area
from arcade.game import REQUIRED_SCENARIOS, reserved
from arcade.games import MENU_ORDER, get_game
from arcade.games.jump import (ACTIVE_RISE, ATTEMPTS, BAR_BOTTOM, BAR_TOP, BAR_TOP_CM, BAR_W, BAR_X, BELL_CM,
                               FIGURE_H, GAME, HINT_IDLE_SECONDS, HIP_SHARE, JUMP_WINDOW, MIN_RISE, OVER_SECONDS,
                               RESULT_SECONDS, SETTLE_SECONDS, STILL, TORSO_CM, Jump, measure_rise)
from arcade.headless import OPENING_NIGHT, run_headless
from arcade.juice import Juice
from arcade.scores import Scores
from arcade.sensed import NOSE, Keypoint
from arcade.sources.actors import REAL_NOISE, TICK, Person, degrade, scene
from tests.arcade.helpers import make_cfg, played, run

WALL = (128, 64)
ZONE = Calibration().zone
CANONICAL_SECONDS = 40.0
CYCLE = SETTLE_SECONDS + JUMP_WINDOW + RESULT_SECONDS          # one attempt, 9 s
LIFT_CM = TORSO_CM / Person().body_at(0.0, 1).torso            # centimetres per unit of frame height lifted


def cam_x(zone_x: float) -> float:
    return ZONE[0] + zone_x * (ZONE[2] - ZONE[0])


def seed(layout: str, i: int) -> int:
    return zlib.crc32(f"jump:{layout}:{i}".encode())


def make(size=WALL, i=0) -> Jump:
    """A Jump reset the way the runner resets it, for tests that poke its state."""
    game = Jump()
    layout = f"{size[0]}x{size[1]}"
    game.scores = Scores(None, lambda: OPENING_NIGHT).for_game("jump", layout)
    game.reset(size, random.Random(seed(layout, i)), Juice(random.Random(1), size))
    return game


def step(game: Jump, frame) -> None:
    bodies = frame.bodies
    game.update(dataclasses.replace(frame, player=bodies[0] if bodies else None,
                                    player2=bodies[1] if len(bodies) > 1 else None), TICK)


def drive(game: Jump, frames, until=None):
    for frame in frames:
        step(game, frame)
        yield frame
        if until is not None and until(game):
            return


def jumper(jumps, ticks=None, x=0.5):
    """A body standing from the start that jumps (at, height) for each of jumps; frames up to ticks."""
    p = Person(cam_x(x), id=1)
    for at, height in jumps:
        p.jump(at, height=height)
    end = max((at for at, _ in jumps), default=0.0) + 2.0
    return scene(persons=[p], ticks=ticks or round(end / TICK))


def stander(seconds=40.0):
    return scene(persons=[Person(cam_x(0.5), id=1)], ticks=round(seconds / TICK))


def shifted(frames, dy_by_time):
    """frames with every keypoint of the body moved by dy_by_time(t) in y (a body standing differently)."""
    for f in frames:
        dy = dy_by_time(f.t)
        if f.bodies and dy:
            b = f.bodies[0]
            kps = tuple(Keypoint(k.x, k.y + dy, k.conf) for k in b.keypoints)
            f = dataclasses.replace(f, bodies=(dataclasses.replace(b, keypoints=kps),))
        yield f


def nodding(frames, start, stop, torsos=0.6):
    """frames whose body's nose alone rises by torsos of its torso between start and stop."""
    for f in frames:
        if f.bodies and start <= f.t < stop:
            b = f.bodies[0]
            kps = list(b.keypoints)
            n = kps[NOSE]
            kps[NOSE] = Keypoint(n.x, n.y - torsos * b.torso, n.conf)
            f = dataclasses.replace(f, bodies=(dataclasses.replace(b, keypoints=tuple(kps)),))
        yield f


def phases_of(game_states):
    out = []
    for s in game_states:
        if not out or out[-1][0] != s["phase"]:
            out.append((s["phase"], 1))
        else:
            out[-1] = (s["phase"], out[-1][1] + 1)
    return out


# ----- registration, the measure -----

def test_registered_and_declared():
    assert get_game("jump") is Jump and GAME is Jump and "jump" in MENU_ORDER
    info = Jump.info
    assert (info.name, info.title, info.verb) == ("jump", "JUMP", "JUMP")
    assert info.needs == frozenset({"pose"}) and info.layouts == frozenset({"128x64"})
    assert info.players == 1 and info.kind == "score" and info.exit_gesture is False
    assert Jump.PHASES == ("ready", "play", "result", "over")
    assert Jump.CAPTION_KEYS == ("phase", "attempt", "peak_cm", "best_cm")
    assert set(Jump.SCENARIOS) >= {"canonical", "idle_body", "nobody"}
    assert (ATTEMPTS, SETTLE_SECONDS, JUMP_WINDOW, RESULT_SECONDS, OVER_SECONDS) == (3, 1.5, 5.0, 2.5, 3.0)
    assert (MIN_RISE, HIP_SHARE, STILL, ACTIVE_RISE, TORSO_CM, BELL_CM, BAR_TOP_CM) == \
        (0.15, 0.5, 0.1, 0.25, 50.0, (28.0, 40.0), 60.0)
    assert (BAR_X, BAR_W, BAR_TOP, BAR_BOTTOM, FIGURE_H, HINT_IDLE_SECONDS) == (6, 10, 6, 57, 56, 2.0)


def raised(torsos, x=0.5, height=0.6):
    """(body raised by torsos of its torso, the still body's nose y, hip y, torso)."""
    still = Person(cam_x(x), height=height, id=1).body_at(0.0, 1)
    torso = still.torso
    body = Person(cam_x(x), 0.55 - torsos * torso, height=height, id=1).body_at(0.0, 1)
    return body, still.nose.y, still.hip_mid.y, torso


def test_rise_is_nose_over_torso():
    body, nose_y, hip_y, torso = raised(0.5)
    rise = measure_rise(body, nose_y, hip_y, torso)
    assert rise == pytest.approx(0.5, abs=0.01) and round(rise * TORSO_CM) == 25, rise


def test_rise_ignores_size_and_place():
    cms = []
    for height in (0.4, 0.8):
        for x in (0.3, 0.7):
            body, nose_y, hip_y, torso = raised(0.5, x=x, height=height)
            rise = measure_rise(body, nose_y, hip_y, torso)
            assert rise is not None, (height, x)
            cms.append(round(rise * TORSO_CM))
    assert max(cms) - min(cms) <= 1 and abs(cms[0] - 25) <= 1, cms


def test_measure_rise_is_none_when_not_counted():
    body, nose_y, hip_y, torso = raised(0.1)                       # under MIN_RISE
    assert measure_rise(body, nose_y, hip_y, torso) is None
    body, nose_y, hip_y, torso = raised(0.5)
    kps = list(body.keypoints)
    kps[NOSE] = Keypoint(kps[NOSE].x, kps[NOSE].y, 0.0)            # no nose
    assert measure_rise(dataclasses.replace(body, keypoints=tuple(kps)), nose_y, hip_y, torso) is None
    assert measure_rise(body, nose_y, hip_y, 0.0) is None


def test_a_nod_never_counts():
    body, nose_y, hip_y, torso = raised(0.0)
    kps = list(body.keypoints)
    n = kps[NOSE]
    kps[NOSE] = Keypoint(n.x, n.y - 0.6 * torso, n.conf)
    assert measure_rise(dataclasses.replace(body, keypoints=tuple(kps)), nose_y, hip_y, torso) is None
    game = make()
    for _ in drive(game, nodding(stander(9.0), 2.0, 3.0)):
        pass
    state = game.debug_state()
    assert state["heights"] == [0] and state["peak_cm"] == 0 and state["rang"] is False, state


# ----- the window, the bar, the baseline -----

def test_a_window_banks_its_best_peak_at_its_end():
    game = make()
    states = []
    for _ in drive(game, jumper([(2.5, 0.10), (4.5, 0.15)], ticks=round(9.0 / TICK))):
        states.append(game.debug_state())
    opened = next(k for k, s in enumerate(states) if s["phase"] == "play")
    closed = next(k for k, s in enumerate(states) if s["phase"] == "result")
    assert abs((closed - opened) * TICK - JUMP_WINDOW) <= 2 * TICK, (opened, closed)
    live = [s for s in states[opened:closed]]
    assert all(s["heights"] == [] and s["best_cm"] == 0 for s in live)           # nothing banks before the end
    want = round(0.15 * LIFT_CM)
    assert max(s["peak_cm"] for s in live) == pytest.approx(want, abs=2)
    assert live[-1]["peak_cm"] == max(s["peak_cm"] for s in live)                  # the best peak holds as a line
    after = states[closed]
    assert after["heights"] == [pytest.approx(want, abs=2)] and after["best_cm"] == after["heights"][0]
    assert after["score"] == after["best_cm"] and type(after["score"]) is int


def test_the_bar_follows_the_rise_live():
    game = make()
    rows = []
    for _ in drive(game, jumper([(2.5, 0.12)], ticks=round(6.0 / TICK))):
        s = game.debug_state()
        if s["phase"] == "play":
            rows.append((s["rise"], s["bar_xy"][1]))
    assert rows[0][1] == BAR_BOTTOM                                                # rest: the bar top on the floor
    for rise, y in rows:
        cm = min(max(rise * TORSO_CM, 0.0), BAR_TOP_CM)
        want = BAR_BOTTOM - round(cm / BAR_TOP_CM * (BAR_BOTTOM - BAR_TOP - 1))
        assert abs(y - want) <= 1.0, (rise, y, want)
    top = max(rows)[0]
    assert min(y for _, y in rows) < BAR_BOTTOM - 10 and top > 0.5, rows


def test_ready_takes_a_new_baseline_before_each_attempt():
    """A body that stands higher after attempt 1 (hips and nose up 0.05) is not a jump in attempt 2: ready
    measures again."""
    game = make()
    for _ in drive(game, shifted(stander(16.0), lambda t: -0.05 if t >= 8.0 else 0.0)):
        pass
    state = game.debug_state()
    assert state["heights"] == [0, 0], state
    assert state["phase"] in ("play", "result", "ready") and state["attempt"] == 2, state


def test_ready_waits_for_stillness():
    """A body still for SETTLE_SECONDS opens the window; one that keeps bouncing never does."""
    game = make()
    first = None
    for f in drive(game, stander(4.0)):
        if first is None and game.debug_state()["phase"] == "play":
            first = game.t
    assert first is not None and SETTLE_SECONDS - 0.07 <= first <= SETTLE_SECONDS + 0.3, first
    bounce = Person(cam_x(0.5), id=1)
    for k in range(20):
        bounce.jump(0.4 * k, height=0.03, seconds=0.4)
    game = make()
    for _ in drive(game, scene(persons=[bounce], ticks=round(8.0 / TICK))):
        pass
    assert game.debug_state()["phase"] == "ready"


def test_the_score_shows_from_the_first_tick(font5x7):
    game = make()
    state = game.debug_state()
    assert state["score"] == 0 and type(state["score"]) is int and state["best_cm"] == 0
    canvas = Canvas(*WALL, font5x7)
    game.draw(canvas)
    x, y, mask = feel.find_text(canvas.frame, font5x7, "0", scales=(2,))
    assert y == 1 and x + 10 >= WALL[0] - 3


def test_no_jump_in_the_window_banks_zero():
    game = make()
    for _ in drive(game, stander(31.0), until=lambda g: g.done()):
        pass
    state = game.debug_state()
    assert state["heights"] == [0, 0, 0] and state["best_cm"] == 0 and state["phase"] == "over", state
    assert game.scores.best() is None


def test_the_bell_rings_once_and_checks_the_flash(font5x7):
    pops, flashes = [], []
    p = Person(cam_x(0.5), id=1).jump(2.5, height=0.15).jump(4.0, height=0.15)         # two jumps over the bell
    frames = scene(persons=[p], ticks=round(9.0 / TICK))
    cfg = make_cfg(WALL)

    class Spy(Jump):
        def reset(self, size, rng, fx):
            super().reset(size, rng, fx)
            orig_pop, orig_flash = fx.pop, fx.flash
            fx.pop = lambda text, *a: (pops.append(text), orig_pop(text, *a))[1]
            fx.flash = lambda *a, **k: flashes.append(orig_flash(*a, **k)) or flashes[-1]
    Spy.info = Jump.info
    _, runner = run_headless(cfg, font5x7, Spy, frames, seed=seed("128x64", 3), trace=True)
    assert pops == ["DING!"] and flashes == [True], (pops, flashes)
    assert max(s.get("flash_held_ticks", 0) for s in runner.trace) == 0
    assert runner.trace[-1]["rang"] is True


def test_a_miss_rings_nothing():
    pops = []
    game = make()
    game.bell_cm = 40.0
    orig = game.fx.pop
    game.fx.pop = lambda text, *a: (pops.append(text), orig(text, *a))[1]
    for _ in drive(game, jumper([(2.5, 0.08)], ticks=round(9.0 / TICK))):
        pass
    state = game.debug_state()
    assert pops == [] and state["rang"] is False and state["heights"][0] > 10, (pops, state)


def test_three_attempts_then_over_and_done_after_the_hold():
    game = make()
    states = []
    for _ in drive(game, stander(40.0), until=lambda g: g.done()):
        states.append(game.debug_state())
    seq = phases_of(states)
    assert [p for p, _ in seq] == ["ready", "play", "result"] * ATTEMPTS + ["over"], seq
    attempts = [s["attempt"] for s in states]
    assert attempts[0] == 1 and attempts[-1] == ATTEMPTS and attempts == sorted(attempts)
    lengths = dict(zip(range(len(seq)), (n * TICK for _, n in seq)))
    for k in range(ATTEMPTS):
        assert lengths[3 * k + 1] == pytest.approx(JUMP_WINDOW, abs=2 * TICK), lengths
        assert lengths[3 * k + 2] == pytest.approx(RESULT_SECONDS, abs=2 * TICK), lengths
    assert game.done() and game.phase_t >= OVER_SECONDS - TICK
    assert seq[-1][1] * TICK == pytest.approx(OVER_SECONDS, abs=2 * TICK)


def test_the_best_is_recorded_once():
    game = make()
    calls = []
    orig = game.scores.record
    game.scores.record = lambda v, *a, **k: (calls.append(v), orig(v, *a, **k))[1]
    jumps = [(2.5, 0.10), (CYCLE + 2.5, 0.15)]
    for _ in drive(game, jumper(jumps, ticks=round(36.0 / TICK))):
        pass
    state = game.debug_state()
    assert state["phase"] == "over" or game.done(), state
    assert state["heights"][0] < state["heights"][1] and state["heights"][2] == 0, state
    assert calls == [state["best_cm"]] and game.scores.best() == state["best_cm"] > 0, (calls, state)
    assert state["score"] == state["best_cm"]


def test_exit_gesture_is_off(font5x7):
    p = Person(cam_x(0.5), id=1).both_hands_up(0.5, 5.5)
    _, game, runner = run(Jump, scene(persons=[p], ticks=round(6.0 / TICK)), WALL, font5x7, seed=seed("128x64", 1))
    assert runner.current_name == "jump", runner.current_name


def test_the_bell_is_drawn_once_per_game_by_the_rng():
    bells = {make(i=i).debug_state()["bell_cm"] for i in range(6)}
    assert len(bells) > 1 and all(BELL_CM[0] <= b <= BELL_CM[1] for b in bells), bells
    a, b = make(i=2), make(i=2)
    assert a.debug_state()["bell_cm"] == b.debug_state()["bell_cm"]
    for _ in drive(a, stander(12.0)):
        pass
    assert a.debug_state()["bell_cm"] == b.debug_state()["bell_cm"]


# ----- movement (C41, C42), the hint -----

def test_idle_body_scores_nothing(font5x7):
    s = seed("128x64", 2)
    _, game, _ = run(Jump, Jump.SCENARIOS["idle_body"](), WALL, font5x7, seed=s)
    state = game.debug_state()
    assert state["score"] == 0 and state["best_cm"] == 0 and set(state["heights"]) <= {0}, (s, state)
    assert game.scores.best() is None
    probe = make()
    for _ in drive(probe, Jump.SCENARIOS["idle_body"](), until=lambda g: g.debug_state()["hint"]):
        pass
    state = probe.debug_state()
    assert state["hint"] is True and state["phase"] == "play", state
    assert probe.t <= SETTLE_SECONDS + HINT_IDLE_SECONDS + 0.3, probe.t


@pytest.mark.parametrize("i", range(5))
def test_a_still_body_under_real_noise_never_counts(i):
    s = seeds(Jump, "128x64", 5)[i]
    person = Person(cam_x(0.3 + 0.1 * i), id=s % 1000 + 1)
    frames = degrade(scene(persons=[person], ticks=round(34 / TICK)), **REAL_NOISE)
    game = make(i=i)
    active, phases = [], set()
    for _ in drive(game, frames):
        state = game.debug_state()
        active.append(state["active"])
        phases.add(state["phase"])
    state = game.debug_state()
    assert "play" in phases, (s, phases)                                           # real noise still opens windows
    assert set(state["heights"]) <= {0} and state["best_cm"] == 0 and state["rang"] is False, (s, state)
    assert not any(active), (s, active.index(True) * TICK)
    assert game.scores.best() is None


def test_active_on_a_jump_and_not_on_a_stand():
    game = make()
    seen = []
    for _ in drive(game, jumper([(2.5, 0.10)], ticks=round(5.0 / TICK))):
        seen.append(game.debug_state()["active"])
    assert any(seen) and not any(seen[:round(2.0 / TICK)]) and all(type(a) is bool for a in seen)


# ----- drawing -----

def test_own_drawing_keeps_the_flash_rule(font5x7):
    cfg = make_cfg(WALL)
    lobby = Lobby([Jump], cfg)
    _, runner = run_headless(cfg, font5x7, [Jump], Jump.SCENARIOS["canonical"](), trace=True, lobby=lobby, raw=True,
                             seed=seeds(Jump, "128x64", 1)[0])
    games = [s["game"] for s in runner.trace]
    first = games.index("jump")
    stop = next((k for k in range(first, len(games)) if games[k] != "jump"), len(games))
    area = flash_area(runner.raw_frames[first:stop])
    assert area < 0.1, area
    assert max(s.get("flash_held_ticks", 0) for s in runner.trace) == 0


@pytest.mark.parametrize("name", ["idle_body", "nobody", "canonical"])
def test_own_drawing_keeps_rows_60_to_63_dark(font5x7, name):
    """The runner's marker and echoes own rows 60 to 63: the striker, the figure and the text stay above them."""
    game = make(i=2)
    canvas = Canvas(*WALL, font5x7)
    lit = []
    for _ in drive(game, Jump.SCENARIOS[name]()):
        canvas.clear()
        game.draw(canvas)
        if canvas.frame[60:].any():
            lit.append(round(game.t, 2))
    assert not lit, f"{name}: rows 60 to 63 lit on {len(lit)} ticks, from t {lit[:3]}"


def test_the_striker_the_bell_and_the_result_are_drawn(font5x7):
    game = make()
    for _ in drive(game, jumper([(2.5, 0.15)], ticks=round(8.0 / TICK)), until=lambda g: g.phase == "result"):
        pass
    canvas = Canvas(*WALL, font5x7)
    game.draw(canvas)
    frame = canvas.frame
    assert tuple(frame[BAR_TOP, BAR_X]) == (0, 200, 255) and tuple(frame[BAR_BOTTOM, BAR_X + BAR_W - 1]) == (0, 200, 255)
    state = game.debug_state()
    text = str(state["peak_cm"])
    assert feel.find_text(frame, font5x7, text, scales=(2,)) is not None, state
    bell_row = BAR_BOTTOM - round(state["bell_cm"] / BAR_TOP_CM * (BAR_BOTTOM - BAR_TOP - 1))
    assert tuple(frame[bell_row - 1, BAR_X + BAR_W // 2]) == (255, 200, 0), bell_row


# ----- the debug state, scenarios, the lobby -----

def test_debug_state_is_clean(font5x7):
    game = make()
    canvas = Canvas(*WALL, font5x7)
    states = []
    frames = jumper([(2.5, 0.12), (CYCLE + 2.5, 0.15)], ticks=round(40 / TICK))
    for _ in drive(game, frames, until=lambda g: g.done()):
        state = game.debug_state()
        states.append(state)
        assert not [k for k in state if reserved(k)], state
        assert type(state["active"]) is bool and type(state["hint"]) is bool and type(state["rang"]) is bool
        assert state["phase"] in Jump.PHASES and all(k in state for k in Jump.CAPTION_KEYS)
        canvas.clear()
        game.draw(canvas)
        for key in ("player_xy", "bar_xy"):
            xy = state[key]
            if xy is None:
                continue
            x, y = xy
            assert 0 <= x < WALL[0] and 0 <= y < WALL[1], (key, state)
            assert canvas.frame[int(y), int(x)].any(), (key, state)
    assert {"phase", "attempt", "score", "rise", "peak_cm", "best_cm", "bell_cm", "rang", "heights", "active", "hint",
            "player_xy", "bar_xy"} <= set(states[-1])
    assert states[-1]["phase"] == "over" and any(s["player_xy"] is not None for s in states)


def test_the_figure_is_on_its_own_column(font5x7):
    ends = []
    for x in (0.2, 0.8):
        game = make()
        for _ in drive(game, scene(persons=[Person(cam_x(x), id=1)], ticks=20)):
            pass
        ends.append(game.debug_state()["player_xy"][0])
    assert ends[1] - ends[0] > 40, ends


def test_required_scenarios_start_with_an_empty_wall():
    assert set(REQUIRED_SCENARIOS) <= set(Jump.SCENARIOS)
    for name in Jump.SCENARIOS:
        assert list(Jump.SCENARIOS[name]()), name
    canonical = list(Jump.SCENARIOS["canonical"]())
    assert len(canonical) == round(CANONICAL_SECONDS / TICK)
    assert all(not f.bodies for f in canonical[:round(2.0 / TICK)]) and canonical[round(2.0 / TICK) + 1].bodies
    assert len(list(Jump.SCENARIOS["idle_body"]())) == round(60 / TICK)
    assert len(list(Jump.SCENARIOS["nobody"]())) == round(30 / TICK)
    assert all(not f.bodies for f in Jump.SCENARIOS["nobody"]())


def test_canonical_drives_the_lobby_to_jump(font5x7):
    cfg = make_cfg(WALL)
    lobby = Lobby([Jump], cfg)
    _, runner = run_headless(cfg, font5x7, [Jump], Jump.SCENARIOS["canonical"](), trace=True, lobby=lobby,
                             seed=seeds(Jump, "128x64", 1)[0])
    games = [s["game"] for s in runner.trace]
    assert games[0] == "lobby" and "jump" in games
    first = games.index("jump")
    raised = round(4.5 / TICK)
    assert raised <= first <= raised + 1, (first, raised)
    stop = next((k for k in range(first, len(games)) if games[k] != "jump"), len(games))
    assert stop * TICK >= feel.FEEL_SECONDS, (stop * TICK, [s.get("phase") for s in runner.trace[first:stop]][-5:])
    xs = [f.bodies[0].zone_x for f in Jump.SCENARIOS["canonical"]() if f.bodies]
    walk = xs[:round(20 / TICK)]
    assert min(walk) < 0.2 and max(walk) > 0.8
    in_game = [s for s in runner.trace[first:stop] if "heights" in s]
    assert in_game[-1]["heights"] and all(h > 0 for h in in_game[-1]["heights"]), in_game[-1]   # every window jumped
    assert max(len(s["heights"]) for s in in_game) == ATTEMPTS


def test_canonical_walks_at_most_a_tenth_of_the_zone_a_second():
    xs = [f.bodies[0].zone_x for f in Jump.SCENARIOS["canonical"]() if f.bodies]
    assert max(abs(b - a) for a, b in zip(xs, xs[1:])) / TICK <= 0.1 + 1e-6


def test_seeded_runs_repeat(font5x7):
    frames = lambda: Jump.SCENARIOS["canonical"]()
    a, _, _ = run(Jump, frames(), WALL, font5x7, ticks=900, seed=seed("128x64", 6))
    b, _, _ = run(Jump, frames(), WALL, font5x7, ticks=900, seed=seed("128x64", 6))
    c, _, _ = run(Jump, frames(), WALL, font5x7, ticks=900, seed=seed("128x64", 7))
    assert all(np.array_equal(x, y) for x, y in zip(a, b))
    assert any(not np.array_equal(x, y) for x, y in zip(a, c))


# ----- bots -----

def test_bots_module_is_found():
    bots, won = for_game(Jump)
    assert set(bots) == {"good", "lazy"} and bots["good"] is not bots["lazy"]
    assert won({"phase": "over", "rang": True})
    assert not won({"phase": "over", "rang": False})
    assert not won({"phase": "play", "rang": True})


def test_good_beats_lazy_beats_nobody():
    ss = seeds(Jump, "128x64", 5)
    wins = {name: sum(played(Jump, name, s).won for s in ss) for name in ("good", "lazy", "none")}
    assert wins["good"] >= 4 and wins["none"] == 0 and wins["lazy"] < wins["good"], (ss, wins)


def test_good_round_length_in_band():
    plays = [played(Jump, "good", s) for s in seeds(Jump, "128x64", 5)]
    lengths = [p.seconds for p in plays if p.done]
    assert len(lengths) >= 4, [(p.seed, p.seconds, p.done) for p in plays]
    assert 20 <= statistics.median(lengths) <= 120, ([p.seed for p in plays], lengths)


def test_feel_file_overrides_have_reasons():
    data = tomllib.loads((Path(__file__).resolve().parents[2] / "arcade/games/jump_feel.toml").read_text())
    assert data["fidelity"] == {"input": "zone_x", "xy": "player_xy", "axis": 0}
    assert "budgets" not in data
    for metric, table in data.get("budgets", {}).get("128x64", {}).items():
        assert table.get("reason", "").strip(), metric
