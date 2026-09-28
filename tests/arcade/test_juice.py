import math
import random
import statistics
import time
import zlib

import numpy as np
import pytest

import arcade.juice as juice
from arcade.calibration import Calibration
from arcade.canvas import Canvas
from arcade.flash import flash_area
from arcade.juice import (BURST_LIFE, BURST_NEAR, ECHO_SECONDS, FLASH_GAP, MAX_PARTICLES, PLAYER_COLORS, POP_RISE,
                          SHAKE_STEP, Juice, marker_x)
from arcade.sensed import place
from arcade.sources.actors import TICK, Person

WHITE = (255, 255, 255)


def checker(size, block=4):
    """A high-contrast frame: white and black squares of block pixels, edges everywhere on both axes."""
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w]
    return np.where((((xx // block) + (yy // block)) % 2 == 0)[..., None], np.uint8(255), np.uint8(0)).repeat(3, 2)


def run(fx, canvas, ticks, each=None, base=None, **render):
    """Render ticks frames over base (black by default), calling each(fx, i) before each; returns the frames."""
    frames = []
    for i in range(ticks):
        if each is not None:
            each(fx, i)
        canvas.frame[:] = 0 if base is None else base
        fx.render(canvas, **render)
        frames.append(canvas.frame.copy())
        fx.update(TICK)
    return frames


def test_particle_pool_capped_at_96():
    fx = Juice(random.Random(1), (640, 64))
    for i in range(10):                                              # ten bursts of 12, far enough apart
        assert fx.burst(20 + i * 60, 30, WHITE)
    assert fx.debug_state()["fx_particles"] == MAX_PARTICLES == 96
    assert fx._pos[fx._alive()][:, 0].min() >= 20 + 2 * 60           # the oldest two bursts were replaced
    fx.update(BURST_LIFE)
    assert fx.debug_state()["fx_particles"] == 0
    assert fx.burst(20, 30, WHITE, n=500) and fx.debug_state()["fx_particles"] == 96
    angles = np.sort(np.arctan2(fx._vel[:, 1], fx._vel[:, 0]))
    gaps = np.diff(np.concatenate([angles, angles[:1] + 2 * math.pi]))
    assert gaps.max() == pytest.approx(2 * math.pi / 96)             # n is capped first: still a whole ring
    fx.update(BURST_LIFE)
    assert fx.burst(100, 30, WHITE, n=np.int64(5)) and fx.debug_state()["fx_particles"] == 5


def test_shake_decays_to_zero(font5x7):
    fx = Juice(random.Random(3), (128, 32))
    canvas = Canvas(128, 32, font5x7)
    offsets = []
    fx.shake(4, 1.0)
    for i in range(45):
        canvas.frame[:] = 0
        canvas.frame[16, 64] = WHITE
        fx.render(canvas)
        offsets.append(tuple(fx.debug_state()["fx_shake"]))
        ys, xs = np.nonzero(canvas.frame.any(axis=2))
        assert (xs.tolist(), ys.tolist()) == ([64 + offsets[-1][0]], [16 + offsets[-1][1]])   # the frame moved
        fx.update(TICK)
    axis = 0 if any(o[0] for o in offsets) else 1
    assert all(o[1 - axis] == 0 for o in offsets)                    # one axis only
    values = [o[axis] for o in offsets]
    changes = [i for i in range(1, 45) if values[i] != values[i - 1]]
    assert abs(values[0]) == 4 and changes                           # at once, at full size
    assert all(b - a >= SHAKE_STEP / TICK - 1e-6 for a, b in zip([0] + changes, changes))   # 4 moves a second
    sizes = [abs(values[i]) for i in [0] + changes]
    assert sizes == sorted(sizes, reverse=True) and sizes[-1] == 0   # decaying, then still
    signs = [values[i] > 0 for i in [0] + changes[:-1]]
    assert all(a != b for a, b in zip(signs, signs[1:]))             # side to side
    for i in [0] + changes:
        assert abs(values[i]) <= 4 * max(0.0, 1.0 - i * TICK) + 0.5  # under the decaying envelope
    assert values[36:] == [0] * 9 and fx.debug_state()["fx_shake"] == [0, 0]
    fx.shake(100, 0.5)                                               # capped at SHAKE_MAX
    run(fx, canvas, 3)
    assert max(abs(v) for v in fx.debug_state()["fx_shake"]) == juice.SHAKE_MAX
    fx.shake(1, 0.1)                                                 # smaller than the one running: ignored
    assert fx._amp == juice.SHAKE_MAX


def test_shake_slice_copy_fills_black(font5x7):
    fx = Juice(random.Random(0), (64, 64))
    canvas = Canvas(64, 64, font5x7)
    fx.shake(3, 2.0)
    for _ in range(3):
        fx.update(TICK)
    canvas.frame[:] = WHITE
    fx.render(canvas)
    dx, dy = fx.debug_state()["fx_shake"]
    assert (dx, dy) != (0, 0)
    lit = canvas.frame.any(axis=2)
    assert lit.sum() == (64 - abs(dx)) * (64 - abs(dy))              # the uncovered strip is black, not wrapped


def test_freeze_skips_update_keeps_drawing(font5x7):
    # Juice's half: frozen is true for the freeze's seconds and drawing goes on; the runner skips the game's
    # update while it is (test_runner.py, test_freeze_skips_the_games_update).
    fx = Juice(random.Random(0), (64, 64))
    canvas = Canvas(64, 64, font5x7)
    fx.freeze(0.2)
    fx.freeze(0.1)                                                   # a shorter freeze never cuts one short
    fx.burst(32, 32, WHITE)
    frozen = []
    for _ in range(9):
        canvas.frame[:] = 0
        fx.render(canvas)
        frozen.append(fx.frozen)
        assert canvas.frame.any()                                    # still drawn while frozen
        fx.update(TICK)
    assert frozen == [True] * 6 + [False] * 3
    assert fx.debug_state()["fx_frozen"] is False
    for bad in (math.nan, -1.0, None, "1"):
        fx.freeze(bad)
    assert not fx.frozen


def test_flash_rate_limited(font5x7):
    fx = Juice(random.Random(0), (64, 64))
    canvas = Canvas(64, 64, font5x7)
    assert fx.flash((200, 0, 0), 0.3)
    assert not fx.flash(WHITE, 0.3)                                  # one is showing: refused
    canvas.frame[:] = (0, 100, 0)
    fx.render(canvas)
    assert canvas.frame[0, 0].tolist() == [200, 100, 0]              # additive
    levels = [fx.debug_state()["fx_flash"]]
    for _ in range(23):
        fx.update(TICK)
        levels.append(fx.debug_state()["fx_flash"])
        assert not fx.flash(WHITE)                                   # refused until FLASH_GAP after it ended
    assert levels == [1.0] * 9 + [0.0] * 15                          # on for 0.3 s, then off: one rise, one fall
    fx.update(TICK)
    assert fx.t == pytest.approx(0.3 + FLASH_GAP) and fx.flash(WHITE, 0.1)
    canvas.frame[:] = (100, 100, 100)
    fx.render(canvas)
    assert canvas.frame[5, 5].tolist() == [255, 255, 255]            # clamped, never wrapped
    for bad in ((WHITE, 0.0), (WHITE, math.nan), (WHITE, -1), (None, 0.2)):
        fx.update(0.1 + FLASH_GAP)
        assert not fx.flash(*bad)


@pytest.mark.parametrize("effect", ["shake", "burst", "burst-spot", "flash", "flash-red"])
def test_effects_keep_the_flash_rule_by_themselves(font5x7, size, effect, monkeypatch):
    # it04 N11: an effect called as often as a game can, over a high-contrast frame (the shake) or black, must not
    # flash any of the wall past the governor's budget, saturated red included (the governor counts it three
    # ways, so a fading red flash would count three falls). The shake and the flash stay at 4 changes a second.
    # A shake whose sign alternated every tick would toggle every edge at 15 Hz; bursts at one spot every tick, or
    # flashes every few ticks, would flash too. With the effect's own limit taken away the same calls do flash,
    # so the limit is what keeps it.
    w, h = size
    red = (255, 0, 0)
    calls = {
        "shake": lambda fx, i: fx.shake(4, 0.5),
        "burst": lambda fx, i: fx.burst((i * 1.5) % w, h / 2 + (i % 5), WHITE),
        "burst-spot": lambda fx, i: fx.burst(w / 2, h / 2, red),
        "flash": lambda fx, i: i % 2 == 0 and fx.flash(WHITE, 0.03),
        "flash-red": lambda fx, i: i % 8 == 0 and fx.flash(red, 0.2),
    }
    base = checker(size) if effect == "shake" else None
    canvas = Canvas(w, h, font5x7)
    frames = run(Juice(random.Random(7), size), canvas, 150, calls[effect], base)
    assert flash_area(frames) == 0.0
    if effect in ("shake", "flash", "flash-red"):
        assert flash_area(frames, budget=4) == 0.0
    assert any(not np.array_equal(f, frames[0]) for f in frames)    # the effect did show
    limit = {"shake": "SHAKE_STEP", "flash": "FLASH_GAP", "flash-red": "FLASH_GAP"}.get(effect, "BURST_GAP")
    monkeypatch.setattr(juice, limit, 0.0)
    frames = run(Juice(random.Random(7), size), canvas, 150, calls[effect], base)
    assert flash_area(frames) > 0.0


def test_burst_near_a_recent_one_is_dropped():
    fx = Juice(random.Random(0), (128, 32))
    assert fx.burst(20, 16, WHITE)
    assert not fx.burst(20 + BURST_NEAR - 1, 16, WHITE)              # too near, too soon
    assert fx.burst(20 + BURST_NEAR, 16, WHITE)                      # far enough
    for _ in range(14):
        fx.update(TICK)
    assert not fx.burst(20, 16, WHITE)                               # 0.467 s: still too soon
    fx.update(TICK)                                                  # 0.5 s: BURST_GAP
    assert fx.burst(20, 16, WHITE)
    for bad in ((math.nan, 5, WHITE), (5, math.inf, WHITE), (5, 5, None), (5, 5, WHITE, True), (5, 5, WHITE, 2.5),
                ("5", 5, WHITE)):
        assert not fx.burst(*bad)


def test_particles_fly_at_one_speed_and_fade(font5x7):
    fx = Juice(random.Random(0), (64, 64))
    canvas = Canvas(64, 64, font5x7)
    fx.burst(32, 32, (0, 0, 240), n=8)
    for _ in range(6):
        fx.update(TICK)                                              # 0.2 s: 6 px out
    fx.render(canvas)
    ys, xs = np.nonzero(canvas.frame.any(axis=2))
    d = np.hypot(xs - 32, ys - 32)
    assert len(xs) >= 6 and np.all(np.abs(d - 6) <= 1.0)
    assert canvas.frame[ys, xs, 2].max() == 144 and canvas.frame[..., :2].max() == 0   # 240 x (1 - 0.2 / 0.5)


def test_pop_rises_six_pixels_then_goes(font5x7):
    fx = Juice(random.Random(0), (128, 32))
    canvas = Canvas(128, 32, font5x7)
    fx.pop("+1", 64, 20, (0, 255, 0))
    tops = []
    for _ in range(25):
        canvas.frame[:] = 0
        fx.render(canvas)
        ys, xs = np.nonzero(canvas.frame.any(axis=2))
        tops.append(int(ys.min()) if len(ys) else None)
        fx.update(TICK)
    assert tops[0] - tops[23] == POP_RISE and tops[24] is None
    assert tops[:24] == sorted(tops[:24], reverse=True)              # rising all the way
    assert fx.debug_state()["fx_pops"] == 0
    for i in range(12):
        fx.pop(str(i), 64, 20, (0, 255, 0))
    assert fx.debug_state()["fx_pops"] == juice.MAX_POPS == 8


def test_banner_is_boxed_and_ends(font5x7, size):
    w, h = size
    fx = Juice(random.Random(0), size)
    canvas = Canvas(w, h, font5x7)
    fx.banner("GO!", 0.5)
    canvas.frame[:] = (0, 0, 255)
    fx.render(canvas)
    white = np.all(canvas.frame == 255, axis=2)
    ys, xs = np.nonzero(white)
    assert ys.max() - ys.min() >= 12                                  # 2x glyphs, 14 px tall
    assert np.all(canvas.frame[ys.min() - 1, xs.min():xs.max() + 1] == 0)   # the black box
    assert fx.debug_state()["fx_banner"] == "GO!"
    fx.banner("A LONG BANNER HERE", 0.5)                              # too wide at 2x on either layout: 1x
    canvas.frame[:] = 0
    fx.render(canvas)
    ys, _ = np.nonzero(canvas.frame.any(axis=2))
    assert ys.max() - ys.min() <= 8
    for _ in range(15):
        fx.update(TICK)
    assert fx.debug_state()["fx_banner"] is None


def test_celebrate_bursts_across_the_wall_twice(font5x7):
    fx = Juice(random.Random(0), (128, 32))
    fx.celebrate((255, 200, 0))
    assert fx.debug_state()["fx_particles"] == 4 * juice.BURST_N    # four origins 32 px apart
    for _ in range(15):
        fx.update(TICK)
    assert fx.debug_state()["fx_particles"] == 4 * juice.BURST_N    # the second wave, 0.5 s on
    fx.update(BURST_LIFE)
    assert fx.debug_state()["fx_particles"] == 0


def test_markers_stay_on_the_bottom_row_and_echo_over_them(font5x7, size):
    w, h = size
    cal = Calibration()
    one = place(Person(x=0.3).body_at(0.0, 1), cal)
    two = place(Person(x=0.75).body_at(0.0, 2), cal)
    fx = Juice(random.Random(0), size)
    canvas = Canvas(w, h, font5x7)
    fx.shake(4, 1.0)
    fx.echo(1, "up")
    fx.echo(3, "up")                                                 # not a player: nothing
    fx.echo(2, "wave")                                               # not a kind: nothing
    assert fx.debug_state()["fx_echoes"] == 1
    for i in range(12):
        canvas.frame[:] = 0
        fx.render(canvas, player=one, player2=two)
        for body, color in ((one, PLAYER_COLORS[0]), (two, PLAYER_COLORS[1])):
            x = marker_x(body, w)
            assert canvas.frame[h - 1, x:x + 2].tolist() == [list(color)] * 2   # never shaken
        x = marker_x(one, w)
        echo = canvas.frame[h - 5:h - 2, x:x + 3]
        assert bool(np.all(echo[1] == PLAYER_COLORS[0])) == (i * TICK < ECHO_SECONDS - 1e-9), i
        fx.update(TICK)
    assert marker_x(one, w) < marker_x(two, w)
    edge = place(Person(x=0.95).body_at(0.0, 3), cal)
    assert marker_x(edge, w) == w - 2 and edge.zone_x == 1.0


def test_fx_keys_are_namespaced():
    fx = Juice(random.Random(0))
    state = fx.debug_state()
    assert set(state) == {"fx_shake", "fx_particles", "fx_frozen", "fx_flash", "fx_banner", "fx_pops", "fx_echoes"}
    assert state == {"fx_shake": [0, 0], "fx_particles": 0, "fx_frozen": False, "fx_flash": 0.0, "fx_banner": None,
                     "fx_pops": 0, "fx_echoes": 0}


def test_bad_numbers_do_nothing(font5x7):
    fx = Juice(random.Random(0), (64, 64))
    for px, seconds in ((math.nan, 1.0), (4, math.inf), (-4, 1.0), (None, 1.0), (4, "1"), (10**400, 1.0)):
        fx.shake(px, seconds)
    fx.pop("x", math.nan, 5, WHITE)
    fx.pop("x", 5, 5, None)
    fx.banner("x", math.nan)
    fx.update(math.nan)
    assert fx.t == 0.0
    assert fx.debug_state() == Juice(random.Random(0)).debug_state()
    canvas = Canvas(64, 64, font5x7)
    fx.render(canvas)
    assert not canvas.frame.any()


@pytest.mark.perf
def test_full_pool_under_half_ms(font5x7):
    seed = zlib.crc32(b"juice-perf")
    rng = random.Random(seed)
    fx = Juice(rng, (64, 64))
    canvas = Canvas(64, 64, font5x7)
    fx._bursts = []
    for i in range(8):
        fx.burst(8 + (i % 2) * 40, 8 + (i // 2) * 16, WHITE)
        fx._bursts = []                                              # fill the pool from nearby origins
    assert fx.debug_state()["fx_particles"] == MAX_PARTICLES
    fx.shake(3, 5.0)
    fx.flash((40, 40, 40), 5.0)
    fx.pop("+10", 32, 40, WHITE)
    fx.banner("GO!", 5.0)
    times = []
    for _ in range(200):
        canvas.frame[:] = 30
        t0 = time.thread_time()                                      # CPU time: the cost, not the load
        fx.render(canvas)
        times.append(time.thread_time() - t0)
    assert statistics.median(times) < 0.0005, f"seed={seed} median={statistics.median(times) * 1e3:.3f} ms"
