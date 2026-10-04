import math
import sys
import tomllib
import types
import zlib
from pathlib import Path

import numpy as np
import pytest

from arcade.bots import (BODY_HEIGHT, BODY_RANGE_SECONDS, LIGHT_SIZE, MAX_PLAY_SECONDS, Move, Nobody, Play, _sensed, for_game, play,
                         seeds, win_rate)
from arcade.calibration import Calibration
from arcade.config import ArcadeConfig
from arcade.game import KINDS, Game, GameInfo
from arcade.sensed import LEFT_HIP, RIGHT_HIP, RIGHT_WRIST
from arcade.input import DEPTH_SPAN, Depth
from arcade.poses import POSES
from arcade.sources.actors import TICK, Person
from tests.arcade.helpers import CROSS_ICON, SpyGame, spy, spy_info

ROOT = Path(__file__).resolve().parents[2]
ORANGE, WHITE = (255, 120, 0), (255, 255, 255)
never = lambda state: False


class Target(Game):
    """A spy: a seeded dot to hold the cursor on. The cursor is (zone_x, the cursor's reach v) on the wall; won
    when it stays within RADIUS px of the dot for HOLD seconds, over (and lost) after LIMIT seconds."""

    info = GameInfo(name="target", title="Target", verb="AIM", icon=CROSS_ICON, needs=frozenset({"pose"}),
                    kind="score")
    PHASES = ("seek", "over")
    RADIUS, HOLD, LIMIT = 2.0, 1.0, 5.0

    def reset(self, size, rng, fx):
        self.w, self.h = size
        self.dot = (rng.randint(2, self.w - 3), rng.randint(2, self.h - 3))
        self.t = self.held = 0.0
        self.cursor, self.won = None, False

    def update(self, sensed, dt):
        self.t += dt
        p = sensed.player
        self.cursor = None if p is None or p.cursor is None else (p.zone_x * (self.w - 1), p.cursor[1] * (self.h - 1))
        near = self.cursor is not None and math.dist(self.cursor, self.dot) <= self.RADIUS
        self.held = self.held + dt if near else 0.0
        self.won = self.won or self.held >= self.HOLD - 1e-9

    def draw(self, canvas):
        canvas.pixel(*self.dot, ORANGE)
        if self.cursor is not None:
            canvas.pixel(round(self.cursor[0]), round(self.cursor[1]), WHITE)

    def done(self):
        return self.won or self.t >= self.LIMIT - 1e-9

    def debug_state(self):
        state = {"phase": "over" if self.done() else "seek", "dot_xy": self.dot, "size": (self.w, self.h),
                 "won": self.won, "active": self.cursor is not None}
        if self.cursor is not None:
            state["cursor_xy"] = self.cursor
        return state


class Good:
    """Holds the cursor on the dot."""

    reaction_ticks, noise = 3, 0.005

    def __call__(self, state, t):
        if "dot_xy" not in state:
            return Move()
        (x, y), (w, h) = state["dot_xy"], state["size"]
        return Move(x=x / (w - 1), wrist_y=y / (h - 1))


class Lazy(Good):
    """Only chases a dot on the left half of the wall; otherwise stands there, hands down."""

    def __call__(self, state, t):
        if "dot_xy" in state and state["dot_xy"][0] >= state["size"][0] / 2:
            return Move()
        return super().__call__(state, t)


@pytest.fixture
def target_bots(monkeypatch):
    module = types.ModuleType("arcade.games.target_bots")
    module.BOTS = {"good": Good, "lazy": Lazy}
    module.won = lambda state: state.get("won") is True
    monkeypatch.setitem(sys.modules, "arcade.games.target_bots", module)
    return module


class Recorder:
    """Returns move every tick and records the (state, t) it was given."""

    def __init__(self, reaction_ticks=0, noise=0.0, move=Move()):
        self.reaction_ticks, self.noise, self.move = reaction_ticks, noise, move
        self.seen = []

    def __call__(self, state, t):
        self.seen.append((dict(state), t))
        return self.move


class Probe(SpyGame):
    """Reports the player's camera-space anchor x and right wrist y, before any clamping of place()."""

    info = spy_info("probe")
    finish_after = 91

    def update(self, sensed, dt):
        super().update(sensed, dt)
        self.player = sensed.player

    def debug_state(self):
        p = getattr(self, "player", None)
        if p is None:
            return {"updates": self.updates}
        return {"updates": self.updates, "anchor_x": p.anchor.x, "wrist_y": p.keypoints[RIGHT_WRIST].y,
                "in_zone": p.in_zone}


def test_play_repeats_under_a_seed(target_bots, font5x7):
    (seed, other) = seeds(Target, "128x32", 2)
    a = play(Target, Good(), seed, keep_frames=True, font=font5x7)
    b = play(Target, Good(), seed, keep_frames=True, font=font5x7)
    c = play(Target, Good(), other, font=font5x7)
    assert isinstance(a, Play) and a.seed == seed and c.frames is None
    assert (a.ticks, a.state, a.won, a.phases) == (b.ticks, b.state, b.won, b.phases), f"seed {seed}"
    assert len(a.frames) == a.ticks and all(np.array_equal(x, y) for x, y in zip(a.frames, b.frames)), f"seed {seed}"
    assert a.state["dot_xy"] != c.state["dot_xy"], f"seeds {seed}, {other}"
    assert seeds(Target, "128x32", 3)[:2] == [seed, other] and seeds(Target, "64x64", 1) != [seed]


def test_reaction_delay_is_honoured(font5x7):
    game = spy(finish_after=12)
    for k in (0, 4):
        bot = Recorder(reaction_ticks=k)
        result = play(game, bot, seed=1, won=never, font=font5x7)
        assert result.ticks == 12 and len(bot.seen) == 12
        for i, (state, t) in enumerate(bot.seen):
            assert t == pytest.approx(i * TICK)
            assert state == ({} if i <= k else {"updates": i - k}), f"reaction {k}, tick {i}"


def probe(noise, move, seed, font, game=Probe):
    bot = Recorder(noise=noise, move=move)
    play(game, bot, seed, won=never, font=font)
    return [s for s, _ in bot.seen[1:]]


def test_noise_is_seeded_and_clamped(font5x7):
    (seed, other) = seeds(Probe, "128x32", 2)
    edge = Move(x=1.0, wrist_y=0.0)
    still = probe(0.0, edge, seed, font5x7)[-1]
    top, right = still["wrist_y"], still["anchor_x"]                 # the wrist at reach v 0; the zone's right edge
    noisy = probe(0.2, edge, seed, font5x7)
    assert noisy == probe(0.2, edge, seed, font5x7) != probe(0.2, edge, other, font5x7), f"seeds {seed}, {other}"
    xs, ys = [s["anchor_x"] for s in noisy], [s["wrist_y"] for s in noisy]
    assert all(s["in_zone"] for s in noisy)                           # clamped to the zone: never out of it
    assert all(x <= right + 1e-9 for x in xs) and all(y >= top - 1e-9 for y in ys), f"seed {seed}"
    at_x, at_y = sum(math.isclose(x, right) for x in xs), sum(math.isclose(y, top) for y in ys)
    assert 0 < at_x < len(xs) and 0 < at_y < len(ys), f"seed {seed}: {at_x}, {at_y} of {len(xs)} at the edge"


def test_play_stops_on_done(font5x7):
    result = play(spy(finish_after=7), Recorder(), seed=0, won=never, keep_frames=True, font=font5x7)
    assert (result.ticks, result.done, result.won, len(result.frames)) == (7, True, False, 7)
    assert result.seconds == pytest.approx(7 * TICK) and result.state == {"updates": 7}
    endless = play(SpyGame, Recorder(), seed=0, won=never, seconds=1.0, font=font5x7)
    assert (endless.ticks, endless.done, endless.frames) == (30, False, None)
    assert MAX_PLAY_SECONDS == 180.0


def test_play_stops_when_the_session_ends(font5x7):
    # Nobody in view: the runner ends the session after leave_seconds (8 s) and the game gets no more updates.
    result = play(SpyGame, Nobody(), seed=0, won=never, font=font5x7)
    assert result.done is False and result.ticks == 240 and result.state == {"updates": 239}
    assert (Nobody.reaction_ticks, Nobody.noise, Nobody()({"phase": "play"}, 1.0)) == (0, 0.0, None)


def test_good_beats_lazy_beats_nobody_on_target(target_bots, font5x7):
    runs = seeds(Target, "128x32", 8)
    one = play(Target, Good(), runs[0], font=font5x7)
    assert one.done and one.won and one.phases == {"seek", "over"} and one.state["phase"] == "over", f"seed {runs[0]}"
    rates = {name: win_rate(Target, factory, runs) for name, factory in
             (("good", Good), ("lazy", Lazy), ("nobody", Nobody))}
    assert rates["good"] == 1.0 and 0.0 < rates["lazy"] < 1.0 and rates["nobody"] == 0.0, f"{rates}, seeds {runs}"


class Sized(SpyGame):
    """Reports the size it was reset to."""

    finish_after = 2

    def debug_state(self):
        return {"updates": self.updates, "size": self.size}


def test_play_defaults_to_the_declared_layout(font5x7):
    one = type("One", (Sized,), {"info": spy_info("one", layouts=frozenset({"96x48"}))})
    two = type("Two", (Sized,), {"info": spy_info("two", layouts=frozenset({"96x48", "64x64"}))})
    assert play(one, Recorder(), seed=0, won=never, font=font5x7).state["size"] == (96, 48)
    assert play(two, Recorder(), seed=0, won=never, font=font5x7).state["size"] == ArcadeConfig().size
    assert "x".join(map(str, ArcadeConfig().size)) == ArcadeConfig().layout not in two.info.layouts
    assert play(one, Recorder(), seed=0, layout="64x64", won=never, font=font5x7).state["size"] == (64, 64)


def test_for_game_names_the_missing_bots_module(target_bots):
    assert for_game(Target) == (target_bots.BOTS, target_bots.won)
    with pytest.raises(ModuleNotFoundError, match=r"arcade/games/spy_bots\.py"):
        for_game(SpyGame)
    with pytest.raises(ModuleNotFoundError, match=r"arcade/games/spy_bots\.py"):
        play(SpyGame, Nobody(), seed=0, seconds=0.1)                  # won defaults to the game's


METRICS = {"response_ticks": {"max": 2}, "response_px": {"min": 12}, "fidelity": {"min": 0.8}, "range": {"min": 0.6},
           "lit_fraction": {"min": 0.01, "max": 0.5}, "dim_fraction": {"max": 0.1}, "liveliness": {"min": 0.001},
           "flash_area_raw": {"max": 0.1}, "square_flashes": {"max": 6}, "phases_reached": {"min": 1.0},
           "round_seconds": {"min": 20, "max": 120}}
WINS = {"win_good": {"min": 0.7}, "win_lazy": {"min": 0.1, "max": 0.7}, "win_none": {"max": 0.05},
        "score_visible": {"min": 0.8}, "score_legible": {"min": 0.9}}


def test_budget_file_parses_and_has_every_kind():
    budgets = tomllib.loads((ROOT / "arcade" / "feel_budgets.toml").read_text())
    assert set(budgets) == set(KINDS)
    toy = {k: v for k, v in METRICS.items() if k not in ("round_seconds", "fidelity", "range")}
    assert budgets == {"control": METRICS, "score": METRICS | WINS, "toy": toy}
    for kind, table in budgets.items():
        for metric, bounds in table.items():
            assert bounds and set(bounds) <= {"min", "max"}, f"{kind}.{metric}"
            assert all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in bounds.values())
            if len(bounds) == 2:
                assert bounds["min"] < bounds["max"], f"{kind}.{metric}"


class Deep(SpyGame):
    """Reports the player's scale and what a fresh Depth, made at reset, reads from it."""

    info = spy_info("deep")
    finish_after = 80

    def reset(self, size, rng, fx):
        super().reset(size, rng, fx)
        self.depth, self.near, self.scale = Depth(), None, None

    def update(self, sensed, dt):
        super().update(sensed, dt)
        p = sensed.player
        self.near = self.depth.update(p, sensed.t, sensed.camera_t)
        self.scale = None if p is None else p.scale

    def debug_state(self):
        return {"updates": self.updates, "near": self.near, "scale": self.scale}


def _body_scale(height):
    return Person(0.5, height=height).body_at(0.0, 1).scale


def test_move_near_sizes_the_body(font5x7):
    centre = _body_scale(BODY_HEIGHT)
    for v in (0.0, 0.25, 0.5, 0.75, 0.9, 1.0):
        bot = Recorder(move=Move(near=v))
        play(Deep, bot, seed=0, won=never, font=font5x7)
        states = [s for s, _ in bot.seen[1:]]
        assert states[0]["scale"] == pytest.approx(centre, rel=1e-9), f"near {v}: the first tick is the centre"
        settled = [s["near"] for s in states[round(1.5 / TICK):round(2.2 / TICK)]]   # before a recentre at an end
        assert all(n == pytest.approx(v, abs=0.02) for n in settled), f"near {v}: {min(settled)}..{max(settled)}"
        assert states[-1]["scale"] == pytest.approx(centre * Depth.ratio(v), rel=1e-9), f"near {v}"
    bot = Recorder(move=Move())                                          # near None: the start size, as before
    play(Deep, bot, seed=0, won=never, font=font5x7)
    assert {s["scale"] for s, _ in bot.seen[1:]} == {_body_scale(0.6)}
    assert BODY_HEIGHT * Depth.ratio(0.0) == pytest.approx(0.52, abs=0.01)
    assert BODY_HEIGHT * Depth.ratio(1.0) == pytest.approx(0.95, abs=0.01)


class Stepper:
    """Asks for near 0 until 1.5 s, then near 1; records the states it is given."""

    reaction_ticks = 0

    def __init__(self, noise=0.0):
        self.noise, self.seen = noise, []

    def __call__(self, state, t):
        self.seen.append(state)
        return Move(near=0.0 if t < 1.5 - 1e-9 else 1.0)


def test_near_moves_at_a_bodys_pace(font5x7):
    centre = _body_scale(BODY_HEIGHT)
    step = TICK / BODY_RANGE_SECONDS
    for noise in (0.0, 0.1):
        seed = zlib.crc32(f"near-pace-{noise}".encode())
        bot = Stepper(noise)
        result = play(Deep, bot, seed, won=never, seconds=2.5, font=font5x7)
        # The bodies play() fed, read back as the near they stand at (nothing smooths them on the way).
        near = [0.5 + math.log(s["scale"] / centre) / DEPTH_SPAN for s in [*bot.seen[1:], result.state]]
        assert len(near) == round(2.5 / TICK), f"seed {seed}"
        assert all(abs(b - a) <= step + 1e-9 for a, b in zip(near, near[1:])), f"seed {seed}: faster than a body"
        assert max(near) - min(near) > 0.9, f"seed {seed}: {min(near)}..{max(near)}"
        if noise == 0.0:
            left = max(i for i, n in enumerate(near) if n <= 1e-9)
            there = next(i for i, n in enumerate(near) if n >= 1.0 - 1e-9)
            assert (there - left) * TICK >= BODY_RANGE_SECONDS - 1e-9, f"seed {seed}: {there - left} ticks"


class Hands(SpyGame):
    """Reports both wrists' reach v, the player's keypoints and their hip centre."""

    info = spy_info("hands")
    finish_after = 30

    def update(self, sensed, dt):
        super().update(sensed, dt)
        self.player = sensed.player

    def debug_state(self):
        p = getattr(self, "player", None)
        if p is None:
            return {"updates": self.updates}
        lh, rh = p.keypoints[LEFT_HIP], p.keypoints[RIGHT_HIP]
        return {"updates": self.updates, "left_v": p.reach(p.left_wrist)[1], "right_v": p.reach(p.right_wrist)[1],
                "keypoints": [(k.x, k.y) for k in p.keypoints], "hip": ((lh.x + rh.x) / 2, (lh.y + rh.y) / 2)}


def test_move_both_hands_moves_both_wrists(font5x7):
    for v in (0.1, 0.5, 0.9):
        states = probe(0.0, Move(hand="both", wrist_y=v), 0, font5x7, game=Hands)
        for s in states:
            assert s["left_v"] == pytest.approx(v, abs=0.02) and s["right_v"] == pytest.approx(v, abs=0.02), f"{v}: {s}"
    one = probe(0.0, Move(hand="right", wrist_y=0.1), 0, font5x7, game=Hands)[-1]
    assert one["right_v"] == pytest.approx(0.1, abs=0.02) and one["left_v"] > 0.5        # one hand: the other hangs


def test_move_pose_holds_the_named_pose(font5x7):
    h = Person().h                                                      # near None: Person's own height
    for s in probe(0.0, Move(pose="t_pose"), 0, font5x7, game=Hands):
        (cx, cy), points = s["hip"], s["keypoints"]
        for i, ((x, y), (dx, dy)) in enumerate(zip(points, POSES["t_pose"])):
            assert (x, y) == (pytest.approx(cx + dx * h, abs=1e-6), pytest.approx(cy + dy * h, abs=1e-6)), f"kp {i}"
    with pytest.raises(ValueError, match="unknown pose"):
        play(Hands, Recorder(move=Move(pose="no_such_pose")), seed=0, won=never, font=font5x7)


def test_move_lift_raises_the_whole_body():
    cal = Calibration()
    for i, before in ((0, None), (40, 0.45)):
        (still,), (lifted,) = (_sensed(i, move, before, cal)[0].bodies for move in (Move(), Move(lift=0.1)))
        for k, (a, b) in enumerate(zip(still.keypoints, lifted.keypoints)):
            assert (b.x, b.y) == (pytest.approx(a.x, abs=1e-6), pytest.approx(a.y - 0.1, abs=1e-6)), f"tick {i}, kp {k}"


def test_move_without_lift_is_todays_body(font5x7):
    cal = Calibration()
    for i, before in ((0, None), (40, 0.45)):
        (today,), (zero,) = (_sensed(i, move, before, cal)[0].bodies for move in (Move(), Move(lift=0.0)))
        assert [(k.x, k.y, k.conf) for k in zero.keypoints] == [(k.x, k.y, k.conf) for k in today.keypoints]
        assert (zero.in_zone, zero.zone_x, zero.zone_y) == (today.in_zone, today.zone_x, today.zone_y)
    seed = seeds(Probe, "128x32", 1)[0]
    noisy = [s["anchor_x"] for s in probe(0.05, Move(), seed, font5x7)]
    assert [s["anchor_x"] for s in probe(0.05, Move(lift=0.0), seed, font5x7)] == noisy
    assert [s["anchor_x"] for s in probe(0.05, Move(lift=0.1), seed, font5x7)] == noisy   # lift draws no noise


def test_move_light_is_a_placed_blob_at_the_wrist():
    # I0 (Paint): a bot holding a light is one tracked blob, id 1, at the Move hand's wrist, placed by place_blob.
    cal = Calibration()
    for i, before in ((0, None), (40, 0.45)):
        sensed, _ = _sensed(i, Move(x=0.3, wrist_y=0.2, light=(0, 255, 0)), before, cal)
        (body,), (blob,) = sensed.bodies, sensed.blobs
        wrist = body.keypoints[RIGHT_WRIST]
        assert (blob.x, blob.y) == (pytest.approx(wrist.x, abs=1e-6), pytest.approx(wrist.y, abs=1e-6)), f"tick {i}"
        assert (blob.id, blob.color, blob.size) == (1, (0, 255, 0), LIGHT_SIZE)
        assert blob.in_zone
        x0, y0, x1, y1 = cal.zone
        assert blob.zone_x == pytest.approx((wrist.x - x0) / (x1 - x0)) and blob.zone_y == pytest.approx((wrist.y - y0) / (y1 - y0))
    (both,) = _sensed(0, Move(hand="both", wrist_y=0.2, light=(255, 0, 0)), None, cal)[0].blobs
    assert (both.x, both.y) == (pytest.approx(wrist.x, abs=0.2), pytest.approx(wrist.y, abs=0.2))   # one light, the right wrist


def test_move_without_light_is_todays_record(font5x7):
    cal = Calibration()
    for i, before in ((0, None), (40, 0.45)):
        today, zero = (_sensed(i, move, before, cal)[0] for move in (Move(), Move(light=None)))
        assert today.bodies == zero.bodies and today.blobs == zero.blobs == ()
        assert not today.motion.any()
    seed = seeds(Probe, "128x32", 1)[0]
    noisy = [s["anchor_x"] for s in probe(0.05, Move(), seed, font5x7)]
    assert [s["anchor_x"] for s in probe(0.05, Move(light=(0, 255, 0)), seed, font5x7)] == noisy   # a light draws no noise
