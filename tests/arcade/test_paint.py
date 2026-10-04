"""Paint (spec 8 row 3, pose and blobs): lights paint. Each in-zone light leaves a stroke in its colour; a lifted
wrist paints in its seat's colour when nobody has a light; strokes fade over 20 s; after 60 s the picture freezes in
a white frame for 5 s. A toy: no score."""
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
from arcade.bots import for_game, seeds
from arcade.calibration import Calibration
from arcade.canvas import Canvas
from arcade.flash import BUDGET, flash_area, square_flashes
from arcade.game import REQUIRED_SCENARIOS, reserved
from arcade.games import MENU_ORDER, get_game
from arcade.games.paint import (ARM_SPAN, BRUSH_PX, FADE_FLOOR, FADE_SECONDS, FRAME_COLOR, FREE_ROWS, GALLERY_SECONDS,
                                GAME, HINT_IDLE_SECONDS, HINT_TEXT, LIGHT_QUIET_SECONDS, LINK_PX, LOST_SECONDS,
                                MAX_SEGMENT_PX, PAINT_SECONDS, PEN_V, RING_R, WHITE_BELOW_S, WIN_PAINTED, Paint,
                                light_color, stamp_segment)
from arcade.headless import OPENING_NIGHT, run_headless
from arcade.juice import PLAYER_COLORS, Juice
from arcade.scores import Scores
from arcade.sensed import Blob, Sensed, place_blob
from arcade.sources.actors import REAL_NOISE, TICK, Person, degrade, moving_blob, scene
from tests.arcade.helpers import make_cfg, played, run

WALL = (128, 64)
PAPER_H = WALL[1] - FREE_ROWS
ZONE = Calibration().zone
CANONICAL_SECONDS = 72.0
GREEN, WHITE, BLACK = (0, 255, 0), (255, 255, 255), (0, 0, 0)
AMBER, BLUE = PLAYER_COLORS


def cam_x(zone_x: float) -> float:
    """The camera x a Person stands at to be at zone_x on the mat."""
    return ZONE[0] + zone_x * (ZONE[2] - ZONE[0])


def seed(layout: str, i: int) -> int:
    return zlib.crc32(f"paint:{layout}:{i}".encode())


def make(size=WALL, i=0, brush: int | None = 2) -> Paint:
    """A Paint reset the way the runner resets it, for tests that poke its state; brush pins the rng's brush."""
    game = Paint()
    layout = f"{size[0]}x{size[1]}"
    game.scores = Scores(None, lambda: OPENING_NIGHT).for_game("paint", layout)
    game.reset(size, random.Random(seed(layout, i)), Juice(random.Random(1), size))
    if brush is not None:
        game.brush_px = brush
    return game


def step(game: Paint, frame) -> None:
    """One tick with the runner's lock applied: the largest body is the player, the next player 2."""
    bodies = frame.bodies
    game.update(dataclasses.replace(frame, player=bodies[0] if bodies else None,
                                    player2=bodies[1] if len(bodies) > 1 else None), TICK)


def drive(game: Paint, frames, until=None):
    for frame in frames:
        step(game, frame)
        yield frame
        if until is not None and until(game):
            return


def paper_px(zone_x: float, zone_y: float) -> tuple[float, float]:
    """Where a light at (zone_x, zone_y) lands on the paper, in wall px."""
    return zone_x * (WALL[0] - 1), zone_y * (PAPER_H - 1)


def light(i: int, zone_x: float, zone_y: float, color=GREEN, id: int = 1) -> Sensed:
    """Tick i's record with one placed light at (zone_x, zone_y) of the zone and nobody in view."""
    x0, y0, x1, y1 = ZONE
    blob = place_blob(Blob(x0 + zone_x * (x1 - x0), y0 + zone_y * (y1 - y0), 0.03, color, id=id), Calibration())
    t = i * TICK
    return Sensed(t, camera_t=t, camera_fresh=True, camera_seq=i + 1, blobs=(blob,))


def empty(i: int) -> Sensed:
    t = i * TICK
    return Sensed(t, camera_t=t, camera_fresh=True, camera_seq=i + 1)


def shown(game: Paint, font) -> np.ndarray:
    canvas = Canvas(*WALL, font)
    game.draw(canvas)
    return canvas.frame


def painted(game: Paint, color=None) -> np.ndarray:
    """The paper's painted pixels (bool, PAPER_H x W), or those holding color."""
    has = np.isfinite(game.painted_at)
    if color is None:
        return has
    return has & (game.paper == np.array(color, float)).all(axis=2)


# ----- registration -----

def test_registered_and_declared():
    assert get_game("paint") is Paint and GAME is Paint and "paint" in MENU_ORDER
    info = Paint.info
    assert (info.name, info.title, info.verb) == ("paint", "PAINT", "PAINT")
    assert info.needs == frozenset({"pose", "blobs"}) and info.layouts == frozenset({"128x64"})
    assert info.players == 2 and info.exit_gesture is False and info.kind == "toy" and info.abandon_seconds == 45.0
    assert Paint.PHASES == ("paint", "gallery")
    assert Paint.CAPTION_KEYS == ("phase", "painted", "lights")
    assert set(Paint.SCENARIOS) == {"canonical", "idle_body", "nobody", "duo"}
    assert (PAINT_SECONDS, GALLERY_SECONDS, FADE_SECONDS, FADE_FLOOR, FREE_ROWS) == (60.0, 5.0, 20.0, 0.56, 4)
    assert (BRUSH_PX, RING_R, MAX_SEGMENT_PX, LOST_SECONDS, LINK_PX) == ((2, 3), 3, 32, 0.3, 12)
    assert (LIGHT_QUIET_SECONDS, PEN_V, ARM_SPAN, WHITE_BELOW_S, WIN_PAINTED) == (1.0, 0.8, 0.5, 0.25, 0.22)
    assert FRAME_COLOR == WHITE and round(255 * FADE_FLOOR) >= 140          # no fading channel falls under dim
    assert HINT_IDLE_SECONDS <= 3.0 and HINT_TEXT


# ----- lights -----

def test_a_tracked_light_draws_segments_in_its_colour():
    game = make()
    xs = [0.2 + 0.04 * k for k in range(11)]                                 # 5 px a capture, under MAX_SEGMENT_PX
    for i, zx in enumerate(xs):
        step(game, light(i, zx, 0.5))
    x_from, x_to = paper_px(xs[0], 0.5)[0], paper_px(xs[-1], 0.5)[0]
    y = paper_px(0.5, 0.5)[1]
    green = painted(game, GREEN)
    for col in range(math.ceil(x_from), math.floor(x_to) + 1):
        assert green[round(y) - 2:round(y) + 3, col].any(), f"column {col} has no green: the segment is broken"
    assert not green[:round(y) - 3].any() and not green[round(y) + 4:].any()  # a stroke, not a smear
    assert painted(game).sum() == green.sum()
    state = game.debug_state()
    assert state["strokes"] == 1 and state["lights"] == 1 and state["active"] is True
    assert state["light_xy"] == pytest.approx(paper_px(xs[-1], 0.5), abs=0.75)       # the stamped pixel


def test_a_step_over_max_segment_starts_a_new_stroke():
    game = make()
    step(game, light(0, 0.1, 0.5))
    step(game, light(1, 0.9, 0.5))                                           # 102 px in one capture
    xa, xb = paper_px(0.1, 0.5)[0], paper_px(0.9, 0.5)[0]
    green = painted(game, GREEN)
    assert green[:, round(xa) - 2:round(xa) + 3].any() and green[:, round(xb) - 2:round(xb) + 3].any()
    assert not green[:, round(xa) + 4:round(xb) - 4].any(), "a jump over MAX_SEGMENT_PX drew a line across the wall"
    assert game.debug_state()["strokes"] == 1                                 # the id's one live stroke, restarted


def test_a_new_id_near_a_lost_stroke_continues_it():
    def run_with(gap_px: float) -> np.ndarray:
        game = make()
        i = 0
        for _ in range(3):
            step(game, light(i, 0.3, 0.5)); i += 1
        for _ in range(6):                                                    # 0.2 s unseen: under LOST_SECONDS
            step(game, empty(i)); i += 1
        step(game, light(i, 0.3 + gap_px / (WALL[0] - 1), 0.5, id=2))
        return painted(game, GREEN)
    xa = paper_px(0.3, 0.5)[0]
    near = run_with(LINK_PX - 2)
    assert near[:, round(xa) + 3:round(xa) + LINK_PX - 4].any(), "a new id within LINK_PX did not continue the stroke"
    far = run_with(LINK_PX + 20)
    assert not far[:, round(xa) + 3:round(xa) + LINK_PX + 16].any(), "a new id far from the stroke was joined to it"


def test_a_new_id_after_the_link_window_starts_fresh():
    game = make()
    i = 0
    for _ in range(3):
        step(game, light(i, 0.3, 0.5)); i += 1
    for _ in range(round(2 * LOST_SECONDS / TICK) + 2):                      # the stroke ended and is unlinkable
        step(game, empty(i)); i += 1
    assert game.debug_state()["strokes"] == 0
    step(game, light(i, 0.3 + 6 / (WALL[0] - 1), 0.5, id=2))
    xa = paper_px(0.3, 0.5)[0]
    assert not painted(game, GREEN)[:, round(xa) + 3:round(xa) + 4].any()


def test_an_untracked_light_paints_dots_only():
    game = make()
    xs = [0.2 + 0.05 * k for k in range(6)]                                  # about 6 px a capture
    for i, zx in enumerate(xs):
        step(game, light(i, zx, 0.5, id=-1))
    green = painted(game, GREEN)
    assert green.sum() == len(xs) * game.brush_px ** 2, "an untracked light drew segments or lost dots"
    assert game.debug_state()["strokes"] == 0


def test_a_light_colour_is_clamped_and_saturated():
    assert light_color((1e308, -5, 0)) == (255, 0, 0)
    assert light_color((200, 100, 0))[0] == 255 and light_color((200, 100, 0))[1:] in ((127, 0), (128, 0))
    assert light_color((100, 100, 100)) == WHITE and light_color((0, 0, 0)) == WHITE
    assert light_color((255, 230, 220)) == WHITE                              # under WHITE_BELOW_S of saturation
    assert light_color((float("nan"), 10, 0)) == (0, 255, 0)
    game = make()
    step(game, light(0, 0.5, 0.5, color=(1e308, -5, 0)))                     # Q158: no exception, red on the paper
    assert painted(game, (255, 0, 0)).any()


# ----- wrists -----

def wrist_frames(v: float, seconds: float, zone_x: float = 0.5, body_id: int = 1):
    person = Person(cam_x(zone_x), id=body_id).wrist("right", v, v, seconds, at=0.0)
    return scene(persons=[person], ticks=round(seconds / TICK))


def test_a_lifted_wrist_paints_when_nobody_has_a_light():
    game = make()
    frames = list(drive(game, wrist_frames(0.3, 1.0)))
    body = frames[-1].bodies[0]
    u, v = body.cursor
    want = (min(1.0, max(0.0, body.zone_x + ARM_SPAN * (u - 0.5))) * (WALL[0] - 1), v / PEN_V * (PAPER_H - 1))
    state = game.debug_state()
    assert state["brush_xy"] == pytest.approx(want, abs=1.5), (state["brush_xy"], want)
    assert painted(game, AMBER).any() and not painted(game, BLUE).any()
    assert state["active"] is True


def test_a_resting_wrist_lifts_the_brush():
    game = make()
    for _ in drive(game, scene(persons=[Person(cam_x(0.5), id=1)], ticks=60)):
        pass
    assert not painted(game).any() and game.debug_state()["brush_xy"] is None
    assert game.debug_state()["active"] is False


def test_a_light_stops_the_wrists():
    game = make()
    person = Person(cam_x(0.2), id=1).walk(cam_x(0.8), 6.0, at=0.0)          # walking, so a sweep keeps finding paper
    t = 0.0
    while t < 6.0:                                                            # the wrist sweeps all along
        person.wrist("right", 0.1, 0.7, 0.5, at=t)
        person.wrist("right", 0.7, 0.1, 0.5, at=t + 0.5)
        t += 1.0
    lamp = moving_blob(0.5, 0.77, 0.55, 0.77, seconds=1.0, start=2.0, color=GREEN, id=1)   # low: under the sweep
    amber_at = {}
    for frame in drive(game, scene(persons=[person], blobs=[lamp], ticks=round(6.0 / TICK))):
        amber_at[round(frame.t, 3)] = int(painted(game, AMBER).sum())
    at = lambda s: amber_at[round(s, 3)]
    assert at(2.0 - TICK) > at(1.0) > 0                                       # painting before the light
    assert at(3.0) == at(2.0 - TICK), "the wrist painted while the light was seen"
    assert at(2.0 + LIGHT_QUIET_SECONDS + 0.9) == at(3.0), "the wrist painted inside the quiet second"
    assert at(5.9) > at(4.5), "the wrist never came back after the light left"
    assert painted(game, GREEN).any()


def test_two_seats_paint_in_their_colours():
    game = make()
    for _ in drive(game, Paint.SCENARIOS["duo"](), until=lambda g: g.t > 10.0):
        pass
    assert painted(game, AMBER).any() and painted(game, BLUE).any()


def test_a_new_body_in_a_seat_starts_its_own_stroke():
    game = make()
    for _ in drive(game, wrist_frames(0.3, 0.5, zone_x=0.3, body_id=1)):
        pass
    before, (xa, _) = int(painted(game, AMBER).sum()), game.debug_state()["brush_xy"]
    frames = list(wrist_frames(0.3, 0.5, zone_x=0.7, body_id=2))
    step(game, dataclasses.replace(frames[0], t=0.5, camera_t=0.5, camera_seq=100))
    xb = game.debug_state()["brush_xy"][0]
    assert xb - xa > 20, (xa, xb)
    assert not painted(game, AMBER)[:, xa + 4:xb - 3].any(), "a new id in the seat was joined to the old stroke"
    assert painted(game, AMBER).sum() > before


# ----- fade, gallery -----

def test_trails_fade_to_the_floor_then_go_off(font5x7):
    game = make()
    step(game, light(0, 0.5, 0.2, color=WHITE))                               # high on the paper, clear of the hint
    t0 = game.paper_t
    x, y = game.debug_state()["light_xy"]
    assert tuple(shown(game, font5x7)[y, x]) == WHITE                          # age 0: full colour
    i = 1
    while game.paper_t - t0 < FADE_SECONDS - 0.1 - 1e-9:
        step(game, empty(i)); i += 1
    dot = shown(game, font5x7)[y - 2:y + 3, x - 2:x + 3]
    lit = dot[dot.any(axis=2)]
    assert lit.size and lit.max(axis=1).min() >= 143 and lit.max() < 255, lit   # 19.9 s: at the floor, still bright
    while game.paper_t - t0 < FADE_SECONDS + TICK / 2:
        step(game, empty(i)); i += 1
    assert not shown(game, font5x7)[y - 2:y + 3, x - 2:x + 3].any()           # 20 s: off
    assert game.debug_state()["painted"] == 0.0


def test_painting_again_renews_a_pixel(font5x7):
    game = make()
    step(game, light(0, 0.5, 0.2, color=WHITE))
    x, y = game.debug_state()["light_xy"]
    i = 1
    while game.t < 10.0:
        step(game, empty(i)); i += 1
    assert 0 < shown(game, font5x7)[y, x].max() < 255
    step(game, light(i, 0.5, 0.2, color=WHITE))
    assert tuple(shown(game, font5x7)[y, x]) == WHITE


def test_the_gallery_freezes_the_paper_then_done(font5x7):
    game = make()
    i = 0
    while game.t < PAINT_SECONDS - 1.0:
        step(game, empty(i)); i += 1
    step(game, light(i, 0.5, 0.5, color=WHITE)); i += 1                       # fresh paint just before the gallery
    assert game.debug_state()["phase"] == "paint" and not game.done()
    while game.debug_state()["phase"] == "paint":
        step(game, empty(i)); i += 1
    assert game.t == pytest.approx(PAINT_SECONDS, abs=TICK + 1e-6)
    x, y = (round(c) for c in paper_px(0.5, 0.5))
    opening = shown(game, font5x7)
    w, h = WALL
    for corner in ((0, 0), (w - 1, 0), (0, PAPER_H - 1), (w - 1, PAPER_H - 1)):
        assert tuple(opening[corner[1], corner[0]]) == FRAME_COLOR, corner
    assert not opening[PAPER_H:].any()
    for _ in range(round(2.0 / TICK)):
        step(game, light(i, 0.3, 0.3, color=GREEN)); i += 1                   # nothing paints in the gallery
    later = shown(game, font5x7)
    assert np.array_equal(later, opening), "the paper changed in the gallery"
    assert not painted(game, GREEN).any()
    assert not game.done()
    while not game.done():
        step(game, empty(i)); i += 1
    assert game.t == pytest.approx(PAINT_SECONDS + GALLERY_SECONDS, abs=TICK + 1e-6)
    assert game.debug_state()["phase"] == "gallery" and game.debug_state()["active"] is False


# ----- stillness, noise, rules -----

def test_idle_body_paints_nothing(font5x7):
    game = make()
    for _ in drive(game, Paint.SCENARIOS["idle_body"]()):
        state = game.debug_state()
        assert state["painted"] == 0.0 and state["brush_xy"] is None and state["active"] is False
    assert not painted(game).any()


def test_the_hint_shows_within_three_seconds_of_a_still_body(font5x7):
    game = make()
    found = None
    for frame in drive(game, Paint.SCENARIOS["idle_body"](), until=lambda g: g.t > 3.5):
        if feel.find_text(shown(game, font5x7), font5x7, HINT_TEXT, scales=(1,)) is not None:
            found = frame.t
            break
    assert found is not None and found <= 3.0, found
    assert game.debug_state()["hint"] is True
    for _ in drive(game, wrist_frames(0.3, 1.0)):
        pass
    assert game.debug_state()["hint"] is False                                # painting hides it


def test_exit_gesture_is_off(font5x7):
    """Both hands up for 5 s (two wrists painting high) leaves the session on."""
    frames = scene(persons=[Person(cam_x(0.5), id=1).both_hands_up(0.5, 8.0)], ticks=round(6.5 / TICK))
    _, game, runner = run(Paint, frames, WALL, font5x7, seed=seed("128x64", 6))
    assert runner.current_name == "paint" and game.debug_state()["phase"] == "paint"


@pytest.mark.parametrize("body_id", [1, 2, 7])
def test_a_still_body_under_real_noise_paints_nothing(body_id):
    game = make()
    for _ in drive(game, degrade(Paint.SCENARIOS["idle_body"](body_id=body_id, seconds=30.0), **REAL_NOISE)):
        pass
    assert not painted(game).any(), f"body {body_id}: a still body painted {int(painted(game).sum())} px under noise"


@pytest.mark.parametrize("body_id", [1, 2, 7])
def test_wrists_paint_under_real_noise(font5x7, body_id):
    game = make()
    person = Person(cam_x(0.5), id=body_id)
    for k in range(8):
        person.wrist("right", 0.1, 0.7, 0.5, at=k)
        person.wrist("right", 0.7, 0.1, 0.5, at=k + 0.5)
    frames = degrade(scene(persons=[person], ticks=round(8.0 / TICK)), **REAL_NOISE)
    canvas = Canvas(*WALL, font5x7)
    for _ in drive(game, frames):
        canvas.clear()
        game.draw(canvas)
        assert not canvas.frame[PAPER_H:].any()
    assert painted(game, AMBER).sum() > 50 and not painted(game, BLUE).any()


def test_a_degraded_light_draws_one_stroke():
    """A tracked light under real noise, missing on 2 of every 10 captures and re-identified after each gap: the
    paper holds one unbroken stroke."""
    game = make()
    lamp = moving_blob(0.3, 0.5, 0.7, 0.5, seconds=6.0, color=GREEN, id=1)
    rng = random.Random(seed("128x64", 9))
    captures, next_id, drop = 0, 2, set()
    last_seq = None
    for frame in degrade(scene(blobs=[lamp], ticks=round(6.0 / TICK)), **REAL_NOISE):
        if frame.camera_fresh and frame.camera_seq != last_seq:
            last_seq = frame.camera_seq
            if captures % 10 == 0:
                drop = set(rng.sample(range(captures + 1, captures + 10), 2))
            if captures in drop:
                frame = dataclasses.replace(frame, blobs=())
            elif captures - 1 in drop:
                frame = dataclasses.replace(frame, blobs=tuple(dataclasses.replace(b, id=next_id) for b in frame.blobs))
                next_id += 1
            captures += 1
            keep = frame
        else:
            frame = dataclasses.replace(frame, blobs=keep.blobs) if last_seq is not None else frame
        step(game, frame)
        assert game.debug_state()["strokes"] <= 1
    green = painted(game, GREEN)
    xa, xb = paper_px(0.3, 0.5)[0], paper_px(0.7, 0.5)[0]
    for col in range(math.ceil(xa) + 1, math.floor(xb)):
        assert green[:, col].any(), f"column {col} is dark: the stroke broke at a gap"


@pytest.mark.parametrize("name", ["canonical", "duo"])
def test_own_drawing_keeps_the_flash_rule(font5x7, name):
    s = seed("128x64", 5)
    _, runner = run_headless(make_cfg(WALL), font5x7, Paint, Paint.SCENARIOS[name](), seed=s, raw=True)
    raw = runner.raw_frames
    assert len(raw) > 300
    assert flash_area(raw) < 0.1 and runner.governor.held_ticks == 0, (s, runner.governor.held_ticks)
    assert square_flashes(raw) <= BUDGET, s


@pytest.mark.parametrize("name", ["canonical", "idle_body", "duo"])
def test_own_drawing_keeps_rows_60_to_63_dark(font5x7, name):
    """The runner's marker and echoes own rows 60 to 63: the game's own frames never light them, the gallery's frame
    and the brush rings included."""
    game = make(brush=None)
    canvas = Canvas(*WALL, font5x7)
    lit, phases = [], set()
    for _ in drive(game, Paint.SCENARIOS[name](), until=lambda g: g.done()):
        canvas.clear()
        game.draw(canvas)
        phases.add(game.debug_state()["phase"])
        if canvas.frame[PAPER_H:].any():
            lit.append(round(game.t, 2))
    assert not lit, f"{name}: rows 60 to 63 lit on {len(lit)} ticks, from t {lit[:3]}"
    if name != "nobody":
        assert "gallery" in phases, f"{name} never reached the gallery, so its frame was not tested"


def test_debug_state_is_clean(font5x7):
    game = make()
    canvas = Canvas(*WALL, font5x7)
    keys = {"phase", "painted", "strokes", "lights", "brush_xy", "light_xy", "active", "brush_px", "hint"}
    lit = 0
    for _ in drive(game, Paint.SCENARIOS["canonical"](), until=lambda g: g.done()):
        state = game.debug_state()
        assert not [k for k in state if reserved(k)], state
        assert keys <= set(state), keys - set(state)
        assert type(state["active"]) is bool and type(state["hint"]) is bool
        assert state["phase"] in Paint.PHASES and all(k in state for k in Paint.CAPTION_KEYS)
        assert 0.0 <= state["painted"] <= 1.0 and state["brush_px"] in BRUSH_PX
        canvas.clear()
        game.draw(canvas)
        for key in ("brush_xy", "light_xy"):
            xy = state[key]
            if xy is not None:
                x, y = xy
                assert 0 <= x < WALL[0] and 0 <= y < PAPER_H, (key, state)
                assert canvas.frame[round(y), round(x)].any(), (key, state)
                lit += 1
    assert lit > 100


def test_required_scenarios_start_with_an_empty_wall():
    assert set(REQUIRED_SCENARIOS) <= set(Paint.SCENARIOS)
    for name in Paint.SCENARIOS:
        assert list(Paint.SCENARIOS[name]()), name
    canonical = list(Paint.SCENARIOS["canonical"]())
    assert len(canonical) == round(CANONICAL_SECONDS / TICK)
    assert all(not f.bodies and not f.blobs for f in canonical[:round(2.0 / TICK)]) and canonical[round(2.0 / TICK) + 1].bodies
    assert any(f.blobs and f.blobs[0].id == 1 and f.blobs[0].in_zone for f in canonical)
    assert len(list(Paint.SCENARIOS["idle_body"]())) == round(60 / TICK)
    assert len(list(Paint.SCENARIOS["nobody"]())) == round(30 / TICK)
    assert all(not f.bodies and not f.blobs for f in Paint.SCENARIOS["nobody"]())
    assert max(len(f.bodies) for f in Paint.SCENARIOS["duo"]()) == 2


def test_canonical_drives_the_lobby_to_paint(font5x7):
    cfg = make_cfg(WALL)
    lobby = Lobby([Paint], cfg)
    _, runner = run_headless(cfg, font5x7, [Paint], Paint.SCENARIOS["canonical"](), trace=True, lobby=lobby,
                             seed=seeds(Paint, "128x64", 1)[0])
    games = [s["game"] for s in runner.trace]
    assert games[0] == "lobby" and "paint" in games
    first = games.index("paint")
    raised = round(4.5 / TICK)
    assert raised <= first <= raised + 1, (first, raised)
    frames = list(Paint.SCENARIOS["canonical"]())
    window = [f for f in frames[:round(feel.FEEL_SECONDS / TICK)] if f.bodies]
    vs = [f.bodies[0].cursor[1] for f in window if f.t >= 6.0 and f.bodies[0].cursor is not None]
    xs = [f.bodies[0].zone_x for f in window]
    assert min(vs) < 0.15 and max(vs) > 0.65, (min(vs), max(vs))              # the wrist sweeps the paper's height
    assert min(xs) < 0.35 and max(xs) > 0.65, (min(xs), max(xs))              # and walks the mat


def test_seeded_runs_repeat(font5x7):
    a, ga, _ = run(Paint, Paint.SCENARIOS["canonical"](), WALL, font5x7, ticks=400, seed=seed("128x64", 6))
    b, _, _ = run(Paint, Paint.SCENARIOS["canonical"](), WALL, font5x7, ticks=400, seed=seed("128x64", 6))
    assert all(np.array_equal(x, y) for x, y in zip(a, b))
    brushes = set()
    for i in range(6):
        _, g, _ = run(Paint, Paint.SCENARIOS["nobody"](), WALL, font5x7, ticks=2, seed=seed("128x64", i))
        brushes.add(g.brush_px)
    assert brushes == set(BRUSH_PX), brushes                                 # the rng draws both brushes


# ----- bots -----

def test_bots_module_is_found():
    found, won = for_game(Paint)
    assert set(found) == {"good", "lazy"} and found["good"] is not found["lazy"]
    assert won({"phase": "gallery", "painted": WIN_PAINTED})
    assert not won({"phase": "gallery", "painted": WIN_PAINTED - 0.01})
    assert not won({"phase": "paint", "painted": 1.0})


def test_good_beats_lazy_beats_nobody():
    ss = seeds(Paint, "128x64", 5)
    wins = {name: sum(played(Paint, name, s).won for s in ss) for name in ("good", "lazy", "none")}
    assert wins["good"] >= 4 and wins["none"] == 0 and wins["lazy"] < wins["good"], (ss, wins)


def test_good_round_length_is_the_paint_and_gallery():
    plays = [played(Paint, "good", s) for s in seeds(Paint, "128x64", 5)]
    lengths = [p.seconds for p in plays if p.done]
    assert len(lengths) >= 4, [(p.seed, p.seconds, p.done) for p in plays]
    assert statistics.median(lengths) == pytest.approx(PAINT_SECONDS + GALLERY_SECONDS, abs=1.0), lengths


def test_feel_file_overrides_have_reasons():
    data = tomllib.loads((Path(__file__).resolve().parents[2] / "arcade/games/paint_feel.toml").read_text())
    assert data["fidelity"] == {"input": "cursor_y", "xy": "brush_xy", "axis": 1}
    assert "budgets" not in data                                              # the plan: no budget override
    for metric, table in data.get("budgets", {}).get("128x64", {}).items():
        assert table.get("reason", "").strip(), metric


# ----- the pure helpers -----

def test_stamp_segment_fills_a_line_with_the_brush():
    paper = np.zeros((PAPER_H, WALL[0], 3), float)
    at = np.full((PAPER_H, WALL[0]), np.nan)
    n = stamp_segment(paper, at, (10.0, 20.0), (40.0, 20.0), GREEN, 2, 1.5)
    assert n == int(np.isfinite(at).sum()) and n >= 31 * 2
    assert (paper[np.isfinite(at)] == np.array(GREEN, float)).all() and (at[np.isfinite(at)] == 1.5).all()
    assert np.isfinite(at)[18:22, 10:42].sum() == n                          # 2 px tall, from x 10 to 41
    n3 = stamp_segment(paper, at, (60.0, 20.0), (60.0, 20.0), WHITE, 3, 2.0)
    assert n3 == 9                                                            # a dot of brush 3 is 3 x 3
    assert stamp_segment(paper, at, (-50.0, -50.0), (-40.0, -40.0), WHITE, 3, 2.0) == 0   # off the paper: nothing
    assert stamp_segment(paper, at, (126.0, 58.0), (140.0, 70.0), WHITE, 3, 2.0) > 0     # clipped at the edge
