"""Copy Me (spec 8 row 1, the hero): a target pose grows over the player's figure as a magenta outline; each judged limb
within tolerance turns green; three rounds, easy to silly."""
import dataclasses
import math
import random
import statistics
import sys
import tomllib
import zlib
from pathlib import Path

import numpy as np
import pytest

from arcade import feel
from arcade.attract.lobby import Lobby
from arcade.bots import Move, for_game, seeds
from arcade.calibration import Calibration
from arcade.canvas import Canvas
from arcade.figure import FRAME_ASPECT
from arcade.flash import SMALL_AREA, concurrent_area
from arcade.game import REQUIRED_SCENARIOS, reserved
from arcade.games import MENU_ORDER, get_game
from arcade.games.copyme import (ACTIVE_DEG, FIGURE_H, FREEZE_SECONDS, FRESH_SHARE, GAME, GROW_FROM, GROW_SECONDS,
                                 HINT_IDLE_SECONDS, JUDGE_MIN_DEG, LADDER, LIMB_TOLERANCE_DEG, MATCH_COLOR,
                                 MATCH_SHARE, OUTLINE_COLOR, OVER_SECONDS, READY_SECONDS, RESULT_SECONDS, ROUNDS,
                                 SCORE_WINDOW, SHOW_SECONDS, SWEEP, WALK_SPEED, WIN_MATCHES, Copyme, score_pose)
from arcade.headless import OPENING_NIGHT, run_headless
from arcade.juice import PLAYER_COLORS, Juice
from arcade.poses import POSES
from arcade.scores import Scores
from arcade.sensed import (LEFT_ANKLE, LEFT_ELBOW, LEFT_HIP, LEFT_KNEE, LEFT_WRIST, RIGHT_ANKLE, RIGHT_HIP,
                           RIGHT_KNEE, Body, Keypoint, place)
from arcade.sources.actors import REAL_NOISE, TICK, Person, body_box, degrade, scene
from show.font import CELL_H
from tests.arcade.helpers import make_cfg, played, run

WALL = (128, 64)
CAL = Calibration()
ZONE = CAL.zone                      # the camera-x span of the mat: a body at camera x is at (x - x0) / (x1 - x0)
TARGETS = [name for rung in LADDER for name in rung]
ROUND_SECONDS = SHOW_SECONDS + GROW_SECONDS + RESULT_SECONDS


def cam_x(zone_x: float) -> float:
    """The camera x a Person stands at to be at zone_x on the mat."""
    return ZONE[0] + zone_x * (ZONE[2] - ZONE[0])


def seed(layout: str, i: int) -> int:
    return zlib.crc32(f"copyme:{layout}:{i}".encode())


def show_at(k: int) -> float:
    """Game time round k's show starts, for a player in view from the first tick."""
    return READY_SECONDS + (k - 1) * ROUND_SECONDS


def play_at(k: int) -> float:
    return show_at(k) + SHOW_SECONDS


def make(size=WALL, i=0, targets=None) -> Copyme:
    """A Copy Me reset the way the runner resets it (targets, when given, replace the three drawn)."""
    game = Copyme()
    layout = f"{size[0]}x{size[1]}"
    game.scores = Scores(None, lambda: OPENING_NIGHT).for_game("copyme", layout)
    game.reset(size, random.Random(seed(layout, i)), Juice(random.Random(1), size))
    if targets is not None:
        game.targets = tuple(targets)
    return game


def step(game: Copyme, frame) -> None:
    """One tick with the runner's lock applied: the largest body is the player, the next player 2."""
    bodies = frame.bodies
    game.update(dataclasses.replace(frame, player=bodies[0] if bodies else None,
                                    player2=bodies[1] if len(bodies) > 1 else None), TICK)


def drive(game: Copyme, frames, until=None):
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


def stander(zone_x=0.5, ticks=1200):
    """A body standing still, hands down, at zone_x on the mat."""
    return scene(persons=[Person(cam_x(zone_x), id=1)], ticks=ticks)


def copier(zone_x: float, body_id: int, target: str = "t_pose", rounds=(1, 2, 3)) -> Person:
    """A body standing through every ready, show and result, holding target through each listed round's play from
    0.2 s in (a pose struck in the round)."""
    person = Person(cam_x(zone_x), id=body_id)
    for k in rounds:
        person.pose(target, at=play_at(k) + 0.2, seconds=GROW_SECONDS - 0.2)
    return person


def drawn(game, font) -> np.ndarray:
    canvas = Canvas(*WALL, font)
    game.draw(canvas)
    return canvas.frame


def count(frame: np.ndarray, color) -> int:
    return int((frame == np.array(color, np.uint8)).all(axis=2).sum())


def posed(name: str, x: float = 0.5, height: float = 0.6, offsets=None) -> Body:
    """A body holding POSES[name] (or offsets), hips at camera x and y 0.55, as Person places a pose."""
    if offsets is not None:
        POSES["_test"] = tuple(offsets)
        name = "_test"
    try:
        return Person(x, height=height, id=1).pose(name, at=0.0, seconds=1.0).body_at(0.5, 1)
    finally:
        POSES.pop("_test", None)


def _hip(kps) -> tuple[float, float]:
    return (kps[LEFT_HIP].x + kps[RIGHT_HIP].x) / 2, (kps[LEFT_HIP].y + kps[RIGHT_HIP].y) / 2


def _turn(point: Keypoint, about: tuple[float, float], deg: float) -> Keypoint:
    """point turned deg degrees (positive: clockwise on the wall, y down) about `about`, in the frame's true aspect."""
    a = math.radians(deg)
    dx, dy = (point.x - about[0]) * FRAME_ASPECT, point.y - about[1]
    rx, ry = dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)
    return Keypoint(about[0] + rx / FRAME_ASPECT, about[1] + ry, point.conf)


def turned(body: Body, deg: float, joints=None, about=None, conf=None) -> Body:
    """body with the joints (all by default) turned deg about `about` (the hip centre by default), confidences
    replaced from conf ({index: conf}) when given, and its box measured again."""
    kps = list(body.keypoints)
    centre = _hip(kps) if about is None else about
    for i in (range(17) if joints is None else joints):
        kps[i] = _turn(kps[i], centre, deg)
    for i, c in (conf or {}).items():
        kps[i] = Keypoint(kps[i].x, kps[i].y, c)
    return dataclasses.replace(body, keypoints=tuple(kps), box=body_box(kps))


def offsets_turned(offsets, joints, about: int, deg: float):
    """offsets with the joints turned deg about the joint `about`, in the frame's true aspect."""
    pts = [Keypoint(dx, dy) for dx, dy in offsets]
    centre = (pts[about].x, pts[about].y)
    for i in joints:
        pts[i] = _turn(pts[i], centre, deg)
    return tuple((p.x, p.y) for p in pts)


# ----- registration, the poses -----

def test_registered_and_declared():
    assert get_game("copyme") is Copyme and GAME is Copyme and MENU_ORDER[0] == "copyme"
    info = Copyme.info
    assert (info.name, info.title, info.verb) == ("copyme", "COPY ME", "COPY")
    assert info.needs == frozenset({"pose"}) and info.layouts == frozenset({"128x64"})
    assert info.players == 2 and info.exit_gesture is False and info.kind == "score"
    assert Copyme.PHASES == ("ready", "show", "play", "result", "over")
    assert Copyme.CAPTION_KEYS == ("phase", "round", "target", "score")
    assert set(Copyme.SCENARIOS) == {"canonical", "idle_body", "nobody", "duo"}
    assert (ROUNDS, READY_SECONDS, SHOW_SECONDS, GROW_SECONDS, GROW_FROM, SCORE_WINDOW) == (3, 1.5, 1.5, 3.0, 0.3, 1.0)
    assert (RESULT_SECONDS, FREEZE_SECONDS, OVER_SECONDS) == (2.0, 1.5, 3.0)
    assert (LIMB_TOLERANCE_DEG, JUDGE_MIN_DEG, ACTIVE_DEG, MATCH_SHARE, FRESH_SHARE) == (30.0, 60.0, 30.0, 0.75, 0.5)
    assert (WIN_MATCHES, FIGURE_H, HINT_IDLE_SECONDS) == (2, 60, 2.0)
    assert (OUTLINE_COLOR, MATCH_COLOR) == ((255, 0, 255), (0, 200, 0))
    icon = info.icon
    assert icon.any() and not icon.all()


def test_new_poses_keep_the_old_three():
    assert all(len(offsets) == 17 for offsets in POSES.values())
    head = ((0.0, -0.45), (-0.03, -0.47), (0.03, -0.47), (-0.06, -0.46), (0.06, -0.46))
    legs = ((-0.08, 0.0), (0.08, 0.0), (-0.08, 0.22), (0.08, 0.22), (-0.08, 0.45), (0.08, 0.45))
    shoulders = ((-0.12, -0.30), (0.12, -0.30))
    assert POSES["stand"] == head + shoulders + ((-0.16, -0.15), (0.16, -0.15), (-0.18, 0.0), (0.18, 0.0)) + legs
    assert POSES["arms_up"] == head + shoulders + ((-0.16, -0.45), (0.16, -0.45), (-0.15, -0.60), (0.15, -0.60)) + legs
    assert POSES["t_pose"] == head + shoulders + ((-0.24, -0.30), (0.24, -0.30), (-0.36, -0.30), (0.36, -0.30)) + legs
    assert LADDER == (("arms_up", "t_pose", "right_up", "left_up"), ("y_pose", "flex", "airplane"),
                      ("disco", "teapot"))
    assert set(TARGETS) <= set(POSES) and len(set(TARGETS)) == 9
    assert "star" not in POSES                                  # unjudged legs would make it y_pose
    for name in TARGETS:
        assert POSES[name][:7] == head + shoulders and POSES[name][11:] == legs, name


# ----- scoring -----

def test_every_target_judges_two_limbs_and_stand_matches_none():
    stand = posed("stand")
    for name in TARGETS:
        share, judged, matched = score_pose(stand, POSES[name])
        assert judged >= 2 and share == 0.0 and matched == 0, (name, share, judged, matched)


@pytest.mark.parametrize("x, height", [(0.3, 0.4), (0.3, 0.8), (0.7, 0.4), (0.7, 0.8)])
def test_a_body_in_the_target_pose_shares_one(x, height):
    for name in TARGETS:
        share, judged, matched = score_pose(posed(name, x, height), POSES[name])
        assert share == pytest.approx(1.0) and matched == judged >= 2, (name, share, judged, matched)


@pytest.mark.parametrize("deg", [-10.0, 10.0])
def test_a_lean_keeps_the_share(deg):
    for name in TARGETS:
        share, judged, matched = score_pose(turned(posed(name), deg), POSES[name])
        assert share == pytest.approx(1.0) and matched == judged, (name, deg, share, judged, matched)


def _forearm_off(deg: float) -> Body:
    """A placed body in t_pose with its left forearm turned deg about the elbow."""
    body = place(posed("t_pose", cam_x(0.5)), CAL)
    elbow = (body.keypoints[LEFT_ELBOW].x, body.keypoints[LEFT_ELBOW].y)
    return place(turned(body, deg, joints=(LEFT_WRIST,), about=elbow), CAL)


def test_limbs_within_tolerance_turn_green(font5x7):
    """In show (the outline small at the hips, clear of the arms), each judged limb within tolerance is redrawn in
    MATCH_COLOR: a forearm 20 degrees off stays green, 40 degrees off is the player's colour."""
    def colours(deg: float):
        game = make(targets=("t_pose", "y_pose", "disco"))
        frames = stander()
        advance(game, frames, "show")
        frame = next(frames)
        for _ in range(3):
            step(game, dataclasses.replace(frame, bodies=(_forearm_off(deg),)))
        f = drawn(game, font5x7)
        return count(f, MATCH_COLOR), count(f, PLAYER_COLORS[0]), game.debug_state()

    green0, amber0, state0 = colours(0.0)
    green20, amber20, state20 = colours(20.0)
    green40, amber40, state40 = colours(40.0)
    assert state0["share"] == state20["share"] == 1.0 and state40["share"] == 0.75, (state20, state40)
    assert green0 >= 40 and abs(green20 - green0) <= 4 and abs(amber20 - amber0) <= 4, (green0, green20)
    assert green40 <= green0 - 10 and amber40 >= amber0 + 10, (green0, green40, amber0, amber40)


def test_legs_cropped_scores_the_upper_body():
    leg_out = offsets_turned(POSES["t_pose"], (LEFT_KNEE, LEFT_ANKLE), LEFT_HIP, 70.0)   # the left leg 70 deg out
    share, judged, matched = score_pose(posed("t", offsets=leg_out), leg_out)
    assert (share, judged, matched) == (pytest.approx(1.0), 6, 6)
    standing_legs = posed("t_pose")
    share, judged, matched = score_pose(standing_legs, leg_out)
    assert judged == 6 and matched == 4 and share == pytest.approx(4 / 6), (share, judged, matched)
    cropped = turned(standing_legs, 0.0, joints=(), conf={i: 0.0 for i in (LEFT_KNEE, RIGHT_KNEE, LEFT_ANKLE,
                                                                            RIGHT_ANKLE)})
    share, judged, matched = score_pose(cropped, leg_out)
    assert (share, judged, matched) == (pytest.approx(1.0), 4, 4)


def test_share_is_weighted_by_confidence():
    body = posed("t_pose")
    elbow = (body.keypoints[LEFT_ELBOW].x, body.keypoints[LEFT_ELBOW].y)
    off = turned(body, 60.0, joints=(LEFT_WRIST,), about=elbow, conf={LEFT_WRIST: 0.4})
    share, judged, matched = score_pose(off, POSES["t_pose"])
    assert judged == 4 and matched == 3 and share == pytest.approx(3 / 3.4), (share, judged, matched)
    unseen = turned(body, 60.0, joints=(LEFT_WRIST,), about=elbow, conf={LEFT_WRIST: 0.0})
    assert score_pose(unseen, POSES["t_pose"]) == (pytest.approx(1.0), 4, 3)
    faint = turned(body, 0.0, joints=(), conf={LEFT_WRIST: 0.2})          # under MIN_CONF: no angle, its weight
    assert score_pose(faint, POSES["t_pose"]) == (pytest.approx(3 / 3.2), 4, 3)
    nothing = turned(body, 0.0, joints=(), conf={i: 0.0 for i in range(5, 11)})
    assert score_pose(nothing, POSES["t_pose"]) == (0.0, 4, 0)            # none seen: 0


# ----- the rounds -----

def _outline_box(frame: np.ndarray) -> tuple[int, int, int, int]:
    """(top, height, left, width) of the outline's pixels, zeros without any."""
    mask = (frame == np.array(OUTLINE_COLOR, np.uint8)).all(axis=2)
    rows, cols = np.flatnonzero(mask.any(axis=1)), np.flatnonzero(mask.any(axis=0))
    if not len(rows):
        return 0, 0, 0, 0
    return int(rows[0]), int(rows[-1] - rows[0] + 1), int(cols[0]), int(cols[-1] - cols[0] + 1)


def test_the_outline_grows_over_three_seconds(font5x7):
    """The outline scales about the hips, so its size is measured as t_pose's arm span: the hint's and the name's
    lines (rows 41 and on) may cover its feet, never its shoulders."""
    game = make(targets=("t_pose",) * 3)
    frames = stander()
    advance(game, frames, "show")
    shown = _outline_box(drawn(game, font5x7))[3]
    advance(game, frames, "play")
    start = _outline_box(drawn(game, font5x7))[3]
    boxes = []
    for _ in drive(game, frames, until=lambda g: g.debug_state()["phase"] != "play"):
        boxes.append((game.phase_t, game.debug_state()["phase"], _outline_box(drawn(game, font5x7))))
    assert boxes[-2][1] == "play" and boxes[-1][1] == "result", boxes[-3:]
    last = boxes[-2][2]                            # 3.0 s less a tick
    full = boxes[-1][2]                            # result's first frame: the frozen frame at full size
    assert full[1] >= 45 and full[3] >= 50 and last[3] / full[3] >= 0.97, (last, full)
    mid = next(box[3] for t, phase, box in boxes if t >= GROW_SECONDS / 2 - 1e-9)
    assert shown == start and start / full[3] == pytest.approx(GROW_FROM, abs=0.05), (shown, start, full)
    assert mid / full[3] == pytest.approx(GROW_FROM + (1 - GROW_FROM) / 2, abs=0.05), (mid, full)


def test_round_k_draws_from_rung_k(font5x7):
    seen = [set() for _ in LADDER]
    for i in range(20):
        game = make(i=i)
        assert len(game.targets) == ROUNDS
        for k, target in enumerate(game.targets):
            assert target in LADDER[k], (i, k, target)
            seen[k].add(target)
    assert all(len(s) >= 2 for s in seen), seen                 # the draw is the rng's, not a fixed pick
    game = make(i=3)
    shown = {}
    frames = stander()
    for _ in drive(game, frames, until=lambda g: g.debug_state()["phase"] == "over"):
        state = game.debug_state()
        if state["phase"] == "show" and state["round"] not in shown:
            shown[state["round"]] = state["target"]
            name = state["target"].replace("_", " ").upper()
            assert feel.find_text(drawn(game, font5x7), font5x7, name, scales=(1,)) is not None, name
    assert shown == {1: game.targets[0], 2: game.targets[1], 3: game.targets[2]}


@pytest.mark.parametrize("strike_at, points", [(0.0, 0), (play_at(1) + 0.2, 100)])
def test_points_need_a_fresh_pose(strike_at, points):
    """t_pose held from ready scores nothing on a t_pose round (it was not struck in the round); struck from stand
    during play, it scores 100."""
    game = make(targets=("t_pose", "y_pose", "disco"))
    person = Person(cam_x(0.5), id=1).pose("t_pose", at=strike_at, seconds=play_at(1) + GROW_SECONDS - strike_at)
    advance(game, scene(persons=[person], ticks=900), "result")
    state = game.debug_state()
    assert state["round"] == 1 and state["score"] == points and state["matches"] == (1 if points else 0), state


def test_a_match_flashes_pops_and_says_match(font5x7):
    game = make(targets=("t_pose",) * 3)
    advance(game, scene(persons=[copier(0.5, 1)], ticks=900), "result")
    fx = game.fx.debug_state()
    assert fx["fx_flash"] > 0.0 and fx["fx_pops"] == 1, fx
    assert feel.find_text(drawn(game, font5x7), font5x7, "MATCH!", scales=(2,)) is not None
    miss = make(targets=("t_pose",) * 3)
    advance(miss, stander(), "result")
    fx = miss.fx.debug_state()
    assert fx["fx_flash"] == 0.0 and fx["fx_pops"] == 1, fx
    assert feel.find_text(drawn(miss, font5x7), font5x7, "MISS", scales=(1,)) is not None
    assert miss.debug_state()["score"] == 0


def test_the_best_frame_is_frozen_in_result(font5x7):
    game = make(targets=("t_pose",) * 3)
    person = copier(0.5, 1, rounds=(1,))
    person.walk(cam_x(0.7), 1.0, at=play_at(1) + GROW_SECONDS).pose("arms_up", at=play_at(1) + GROW_SECONDS,
                                                                     seconds=RESULT_SECONDS)
    frames = scene(persons=[person], ticks=900)
    advance(game, frames, "result")
    first = drawn(game, font5x7)
    later = []
    for _ in drive(game, frames, until=lambda g: g.debug_state()["phase"] != "result"):
        if game.debug_state()["phase"] == "result":
            later.append((game.phase_t, drawn(game, font5x7)))
    frozen = [f for t, f in later if t < FREEZE_SECONDS - 1e-9]
    live = [f for t, f in later if t >= FREEZE_SECONDS - 1e-9]
    assert len(frozen) >= round(FREEZE_SECONDS / TICK) - 2 and live
    assert all(np.array_equal(f, first) for f in frozen)
    assert not np.array_equal(live[-1], first)                 # then the body as it is now


def test_three_rounds_then_over_and_done_after_the_hold():
    game = make()
    runs = []                                       # (phase, round, game time it began)
    for _ in drive(game, stander(), until=lambda g: g.done()):
        state = game.debug_state()
        if not runs or runs[-1][0] != state["phase"]:
            runs.append((state["phase"], state["round"], game.t))
    assert [p for p, _, _ in runs] == ["ready"] + ["show", "play", "result"] * ROUNDS + ["over"], runs
    assert [r for p, r, _ in runs if p == "show"] == [1, 2, 3]
    starts = [t for _, _, t in runs]
    lengths = [b - a for a, b in zip(starts[1:], starts[2:])]
    assert lengths == pytest.approx([SHOW_SECONDS, GROW_SECONDS, RESULT_SECONDS] * ROUNDS, abs=TICK + 1e-6)
    assert game.done() and game.t - starts[-1] == pytest.approx(OVER_SECONDS, abs=TICK + 1e-6)


def test_exit_gesture_is_off(font5x7):
    person = Person(cam_x(0.5), id=1).pose("arms_up", at=1.0, seconds=5.0)
    _, game, runner = run(Copyme, scene(persons=[person], ticks=round(7.0 / TICK)), WALL, font5x7)
    assert runner.current_name == "copyme" and not game.done()


# ----- two players -----

def test_a_second_player_joins_at_the_next_show_and_the_game_records_nothing():
    solo = make(targets=("t_pose",) * 3)
    for _ in drive(solo, scene(persons=[copier(0.3, 1)], ticks=900), until=lambda g: g.done()):
        pass
    assert solo.debug_state()["score"] == 300 and solo.scores.best() == 300

    game = make(targets=("t_pose",) * 3)
    late = copier(0.7, 2).arrive(play_at(1) + 1.0)
    states = []
    for _ in drive(game, scene(persons=[copier(0.3, 1), late], ticks=900), until=lambda g: g.done()):
        states.append(game.debug_state())
    first = [s for s in states if s["round"] <= 1]
    later = [s for s in states if s["round"] >= 2]
    assert all(s["other"] is None and s["humans"] == 1 and s["player2_xy"] is None for s in first)
    assert all(s["other"] is not None and s["humans"] == 2 for s in later)
    assert later[0]["phase"] == "show" and later[0]["player2_xy"] is not None
    end = states[-1]
    assert end["score"] == 300 and end["other"] == 200 and end["matches"] == 3, end
    assert game.scores.best() is None                                   # a game that had a seat b records nothing


def test_seat_bs_match_alone_flashes_and_says_match(font5x7):
    game = make(targets=("t_pose",) * 3)
    frames = scene(persons=[Person(cam_x(0.3), id=1), copier(0.7, 2, rounds=(1,))], ticks=900)
    advance(game, frames, "result")
    state, fx = game.debug_state(), game.fx.debug_state()
    assert state["matches"] == 0 and state["other"] == 100 and fx["fx_flash"] > 0, (state, fx)
    found = feel.find_text(drawn(game, font5x7), font5x7, "MATCH!", scales=(2,))
    assert found is not None, "the flash and MATCH! go together: each seat's pop says whose"


def test_a_seat_b_who_leaves_is_dropped():
    game = make(targets=("t_pose",) * 3)
    gone = Person(cam_x(0.7), id=2).leave(play_at(1) + 0.5)
    frames = scene(persons=[copier(0.3, 1), gone], ticks=900)
    advance(game, frames, "show")
    state = game.debug_state()
    assert state["humans"] == 2 and state["other"] == 0 and state["player2_xy"] is not None, state
    advance(game, frames, "result")
    assert game.debug_state()["other"] == 0                           # gone, but kept until the next show
    advance(game, frames, "show")
    state = game.debug_state()
    assert state["round"] == 2 and state["humans"] == 1 and state["other"] is None, state
    assert state["player2_xy"] is None
    for _ in drive(game, frames, until=lambda g: g.done()):
        pass
    assert game.debug_state()["score"] == 300 and game.scores.best() is None


def test_the_figure_column_holds_within_the_slack():
    game = make()
    base = next(stander())
    body = base.bodies[0]

    def at_column(c: int):
        return dataclasses.replace(base, bodies=(dataclasses.replace(body, zone_x=c / (WALL[0] - 1)),))

    for _ in range(3):
        step(game, at_column(60))
    x0 = game.debug_state()["player_xy"][0]
    for c in (61, 59, 60, 61):
        step(game, at_column(c))
        assert game.debug_state()["player_xy"][0] == x0, c
    step(game, at_column(63))                               # two columns past the slack's edge at 61: it moves
    assert game.debug_state()["player_xy"][0] == x0 + 2


# ----- movement (C41, C42), the hint -----

def test_idle_body_scores_nothing(font5x7):
    s = seed("128x64", 2)
    _, game, _ = run(Copyme, Copyme.SCENARIOS["idle_body"](), WALL, font5x7, ticks=round(27 / TICK), seed=s)
    state = game.debug_state()
    assert game.done() and state["score"] == 0 and state["matches"] == 0, (s, state)
    assert game.scores.best() is None
    probe = make()
    for _ in drive(probe, Copyme.SCENARIOS["idle_body"](), until=lambda g: g.debug_state()["hint"]):
        pass
    assert probe.debug_state()["hint"] is True and HINT_IDLE_SECONDS - TICK <= probe.t <= 3.0, probe.t
    assert feel.find_text(drawn(probe, font5x7), font5x7, "STRIKE THE SHAPE", scales=(1,)) is not None


@pytest.mark.parametrize("i", range(3))
def test_a_still_body_under_real_noise_scores_nothing(i):
    s = seeds(Copyme, "128x64", 3)[i]
    person = Person(cam_x(0.3 + 0.2 * i), id=s % 1000 + 1)
    frames = list(degrade(scene(persons=[person], ticks=round(60 / TICK)), **REAL_NOISE))
    captures = [f.bodies[0] for f in frames if f.camera_fresh and f.bodies]
    assert len(captures) > 500
    for name in TARGETS:
        matched = [score_pose(body, POSES[name])[2] for body in captures]
        assert not any(matched), (s, name, matched.index(max(matched)))
    game = make(i=i)
    active = []
    for _ in drive(game, frames, until=lambda g: g.done()):
        active.append(game.debug_state()["active"])
    state = game.debug_state()
    assert game.done() and state["score"] == 0 and game.scores.best() is None, (s, state)
    assert not any(active), (s, active.index(True) * TICK)
    walker = make()
    seen = [walker.debug_state()["active"] for _ in drive(walker, scene(persons=[copier(0.5, 1)], ticks=240))]
    assert any(seen) and all(type(a) is bool for a in seen)


# ----- the drawing -----

def test_score_is_drawn_at_2x_top_left_from_the_first_tick(font5x7):
    game = make()
    frame = drawn(game, font5x7)
    found = feel.find_text(frame, font5x7, "0", scales=(2,))
    assert found is not None and found[1] == 1 and found[0] <= 3, found
    assert feel.find_text(frame, font5x7, "COPY THE SHAPE", scales=(1,)) is not None
    game.seats[0].total = 140
    found = feel.find_text(drawn(game, font5x7), font5x7, "140", scales=(2,))
    assert found is not None and found[1] == 1 and found[0] <= 3, found


@pytest.mark.parametrize("name", ["canonical", "duo"])
def test_own_drawing_keeps_the_flash_rule(font5x7, name):
    s = seed("128x64", 5)
    _, runner = run_headless(make_cfg(WALL), font5x7, Copyme, Copyme.SCENARIOS[name](), seed=s, raw=True)
    raw = runner.raw_frames
    assert len(raw) > 300
    assert concurrent_area(raw) < SMALL_AREA, s
    assert runner.governor.held_ticks == 0, s
    if name == "duo":
        assert any(f.any(axis=2).all() for f in raw), s           # a match's flash was among them


# ----- the debug state, scenarios, the lobby -----

def test_debug_state_is_clean(font5x7):
    game = make()
    score_box = (CELL_H * 2 + 1, 4 * 6 * 2)              # rows and columns a 3-digit 2x score and its box may cover
    for _ in drive(game, Copyme.SCENARIOS["duo"](), until=lambda g: g.done()):
        state = game.debug_state()
        assert not [k for k in state if reserved(k)], state
        assert type(state["active"]) is bool and type(state["hint"]) is bool
        assert state["phase"] in Copyme.PHASES and all(k in state for k in Copyme.CAPTION_KEYS)
        frame = drawn(game, font5x7)
        for key in ("player_xy", "player2_xy"):
            xy = state[key]
            if xy is None:
                continue
            x, y = xy
            assert 0 <= x < WALL[0] and 0 <= y < WALL[1], (key, state)
            if y <= score_box[0] and (x <= score_box[1] or x >= WALL[0] - score_box[1]):
                continue                                      # under a score, which is drawn last
            assert frame[int(y), int(x)].any(), (key, state)
    assert {"phase", "round", "target", "score", "other", "share", "matches", "judged", "active", "hint", "humans",
            "player_xy", "player2_xy"} <= set(state)


def test_required_scenarios_start_with_an_empty_wall():
    assert set(REQUIRED_SCENARIOS) <= set(Copyme.SCENARIOS)
    built = {name: list(script()) for name, script in Copyme.SCENARIOS.items()}
    assert all(built.values()), {name: len(frames) for name, frames in built.items()}
    canonical = built["canonical"]
    assert all(not f.bodies for f in canonical[:round(2.0 / TICK)]) and canonical[round(2.0 / TICK) + 1].bodies
    xs = [f.bodies[0].zone_x for f in canonical[:round(feel.FEEL_SECONDS / TICK)] if f.bodies]
    assert min(xs) <= SWEEP[0] + 1e-6 and max(xs) >= SWEEP[1] - 1e-6, (min(xs), max(xs))   # in the measured 20 s
    assert SWEEP[1] - SWEEP[0] >= 0.65                                   # the feel's range (0.6) with the backlash
    steps = [abs(b - a) for a, b in zip(xs, xs[1:])]
    assert max(steps) <= WALK_SPEED * TICK + 1e-6, max(steps)           # slow: the flash rule (own drawing)
    assert len(built["idle_body"]) == round(60 / TICK)
    assert len(built["nobody"]) == round(30 / TICK)
    assert all(not f.bodies for f in built["nobody"])
    assert all(len(f.bodies) == 2 for f in built["duo"])


def test_canonical_drives_the_lobby_to_copyme_and_matches_every_round(font5x7):
    cfg = make_cfg(WALL)
    _, runner = run_headless(cfg, font5x7, [Copyme], Copyme.SCENARIOS["canonical"](), trace=True,
                             lobby=Lobby([Copyme], cfg), seed=seeds(Copyme, "128x64", 1)[0])
    games = [s["game"] for s in runner.trace]
    assert games[0] == "lobby" and "copyme" in games
    first = games.index("copyme")
    raised = round(4.5 / TICK)
    assert raised <= first <= raised + 1, (first, raised)
    stop = next((k for k in range(first, len(games)) if games[k] != "copyme"), len(games))
    assert stop * TICK >= feel.FEEL_SECONDS, (stop * TICK, [s.get("phase") for s in runner.trace[first:stop]][-5:])
    end = runner.trace[stop - 1]
    assert end["phase"] == "over" and end["matches"] == ROUNDS and end["score"] == 100 * ROUNDS, end


def test_seeded_runs_repeat(font5x7):
    duo = lambda s: run(Copyme, Copyme.SCENARIOS["duo"](), WALL, font5x7, ticks=120, seed=seed("128x64", s))[0]
    a, b = duo(6), duo(6)
    assert all(np.array_equal(x, y) for x, y in zip(a, b))
    assert any(any(not np.array_equal(x, y) for x, y in zip(a, other)) for other in (duo(7), duo(8)))


# ----- bots -----

def test_bots_module_is_found():
    bots, won = for_game(Copyme)
    assert set(bots) == {"good", "lazy"} and bots["good"] is not bots["lazy"]
    assert won({"phase": "over", "matches": WIN_MATCHES}) and won({"phase": "over", "matches": 3})
    assert not won({"phase": "over", "matches": WIN_MATCHES - 1})
    assert not won({"phase": "play", "matches": 3})
    good, lazy = bots["good"](), bots["lazy"]()
    assert (good.reaction_ticks, good.noise, lazy.reaction_ticks, lazy.noise) == (6, 0.01, 14, 0.03)
    state = lambda phase, k, target: {"phase": phase, "round": k, "target": target}
    assert good({}, 0.0) == Move(x=0.5) and good(state("ready", 0, None), 0.0) == Move(x=0.5)
    for k, target in ((1, "t_pose"), (2, "flex"), (3, "teapot")):
        assert good(state("show", k, target), 0.0) == Move(x=0.5, pose=target)
    assert lazy(state("play", 1, "t_pose"), 0.0).pose == "t_pose"
    assert lazy(state("play", 2, "flex"), 0.0).pose is None
    assert lazy(state("play", 3, LADDER[2][0]), 0.0).pose == LADDER[2][0]
    assert lazy(state("play", 3, LADDER[2][1]), 0.0).pose is None


def test_good_beats_lazy_beats_nobody():
    ss = seeds(Copyme, "128x64", 5)
    wins = {name: sum(played(Copyme, name, s).won for s in ss) for name in ("good", "lazy", "none")}
    assert wins["good"] >= 4 and wins["none"] == 0 and wins["lazy"] < wins["good"], (ss, wins)


def test_good_round_length_in_band():
    plays = [played(Copyme, "good", s) for s in seeds(Copyme, "128x64", 5)]
    lengths = [p.seconds for p in plays if p.done]
    assert len(lengths) >= 4, [(p.seed, p.seconds, p.done) for p in plays]
    assert 20 <= statistics.median(lengths) <= 120, ([p.seed for p in plays], lengths)


def test_feel_file_overrides_have_reasons():
    data = tomllib.loads((Path(__file__).resolve().parents[2] / "arcade/games/copyme_feel.toml").read_text())
    assert data["fidelity"] == {"input": "zone_x", "xy": "player_xy", "axis": 0}
    assert "budgets" not in data                                   # the plan: no budget override


# ----- C55: the outline on player 2, and the wall's marker rows -----

MIN_COLOR_DISTANCE = 150.0


def test_the_outline_differs_from_every_figure_colour(font5x7, monkeypatch):
    """The outline reads on both seats: far (RGB Euclidean) from each seat's colour and from MATCH_COLOR, and in a duo
    frame of play no outline pixel is drawn in seat b's colour. Each outline stroke (a line or circle draw_view draws
    itself, after its figure) is drawn again alone on a blank canvas, so its own pixels are read, under either seat."""
    outline = np.array(OUTLINE_COLOR, float)
    for other in (*PLAYER_COLORS[:2], MATCH_COLOR):
        assert float(np.linalg.norm(outline - np.array(other, float))) >= MIN_COLOR_DISTANCE, (OUTLINE_COLOR, other)
    game = make()
    advance(game, Copyme.SCENARIOS["duo"](), "play")
    strokes: list[tuple[tuple, np.ndarray]] = []                     # (the seat's figure colour, the stroke alone)

    def spied(real):
        def stroke(canvas, *args):
            caller = sys._getframe(1)
            if caller.f_code.co_name == "draw_view" and Path(caller.f_code.co_filename).name == "copyme.py":
                alone = Canvas(*WALL, font5x7)
                real(alone, *args)
                strokes.append((tuple(caller.f_locals["color"]), alone.frame))
            return real(canvas, *args)
        return stroke

    with monkeypatch.context() as m:
        m.setattr(Canvas, "line", spied(Canvas.line))
        m.setattr(Canvas, "circle", spied(Canvas.circle))
        frame = drawn(game, font5x7)
    assert count(frame, OUTLINE_COLOR) > 0 and count(frame, PLAYER_COLORS[1]) > 0
    assert OUTLINE_COLOR != PLAYER_COLORS[1]
    assert {seat for seat, _ in strokes} == set(PLAYER_COLORS[:2]), {seat for seat, _ in strokes}
    seat_b = {seat: sum(count(alone, PLAYER_COLORS[1]) for s, alone in strokes if s == seat) for seat, _ in strokes}
    lit = {seat: sum(int(alone.any(axis=2).sum()) for s, alone in strokes if s == seat) for seat, _ in strokes}
    assert all(lit.values()), lit                                           # each seat's outline lights pixels
    assert not any(seat_b.values()), f"outline pixels in seat b's colour {PLAYER_COLORS[1]}, by seat: {seat_b}"


@pytest.mark.parametrize("name", ["canonical", "duo"])
def test_own_drawing_keeps_rows_60_to_63_dark(font5x7, name):
    """The runner's marker and echoes own rows 60 to 63: no phase of Copy Me's own drawing lights them."""
    game = make(i=2)
    canvas = Canvas(*WALL, font5x7)
    lit = []
    for _ in drive(game, Copyme.SCENARIOS[name]()):
        canvas.clear()
        game.draw(canvas)
        if canvas.frame[60:].any():
            lit.append(round(game.t, 2))
    assert game.debug_state()["round"] >= 1
    assert not lit, f"{name}: rows 60 to 63 lit on {len(lit)} ticks, from t {lit[:3]}"
