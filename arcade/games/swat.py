"""Swat (spec 8, game 8; the effects showcase): fruit arcs up and falls, the player's blade cuts what its swipe crosses,
bombs cost, the round is ROUND_SECONDS and GOAL is the win.

The blade, per seat (one or two players, who share one score): the seat's Cursor (the wrist in the reach box) then two
Glides give (u, v); a Glide gives the hips' zone_x (C44, C46: never raw). x is zone_x from ZONE_LO..ZONE_HI onto
-ARM_PX / 4 .. w - 1 + ARM_PX / 4, so either hand reaches both edges, plus (u - 0.5) * ARM_PX, clamped to the wall; y is
v from V_TOP..V_BOTTOM onto BLADE_TOP..BLADE_BOTTOM. A player steps to reach the far side and swipes with the hand.

A cut: the segment from the blade's last tick to this one is at least CUT_MIN_PX long and passes within FRUIT_R + 1
px of a fruit's centre, while the seat's Cursor v (not glided) is under CUT_V_MAX: a hanging hand never cuts (C41,
C42; under real noise the Cursor swaps a still body's hands and the blade jumps along the bottom row). COMBO cuts
in one swipe (a run of ticks that each moved CUT_MIN_PX with a raised hand) pop and flash. A bomb costs BOMB_COST, never
below 0. Solo only: scores.record(score) once at over when a fruit was cut; with a second seat ever seen, nothing (Q23).

Phases: ready (READY_SECONDS, 3 2 1 GO!), play, over (holds the total).

debug_state: phase, score (cut fruit minus bomb costs, shared), cut (fruit cut), bombs_hit, active (a blade moved
CUT_MIN_PX this tick with its v under CUT_V_MAX), hint (the swipe hint is wanted), t_left, blade_xy (seat a's blade,
or None), blade2_xy (seat b's, or None), target_xy (the fruit nearest seat a's blade, else None) and bomb_xy (the
nearest bomb, else None)."""
from __future__ import annotations

import math
import random
from types import MappingProxyType

from arcade.canvas import Canvas
from arcade.game import Game, GameInfo, icon_from_rows
from arcade.input import Cursor, Glide, capture_grace
from arcade.juice import PLAYER_COLORS
from arcade.sensed import Sensed
from arcade.sources.actors import TICK, Person, scene
from show.font import CELL_H

ROUND_SECONDS = 60.0
READY_SECONDS = 3.0
OVER_SECONDS = 3.0
FRUIT_R = 2                     # a fruit lights a (2 R + 1) px square
SPAWN_EVERY = (1.4, 0.8)        # s between fruit, linear over the round (tuned: the plan's 1.1, 0.6)
BOMB_SHARE = 0.2                # tuned: the plan's 0.15
LAUNCH_VY = (-53.0, -42.0)      # px/s: apexes of rows 10 to 28 from SPAWN_Y
DRIFT_VX = (-18.0, 18.0)
GRAVITY = 30.0                  # px/s2
SPAWN_Y = 57                    # a fruit lights rows 55 to 59 there; rows 60 to 63 stay free
BOMB_COST = 3
GOAL = 30                       # tuned: the plan's 25
CUT_MIN_PX = 3
CUT_V_MAX = 0.85
ARM_PX = 48
ZONE_LO, ZONE_HI = 0.15, 0.85
V_TOP, V_BOTTOM = 0.15, 0.85
BLADE_TOP, BLADE_BOTTOM = 2, 57
TRAIL = 4                       # ticks of a blade's trail
COMBO = 3
HINT_IDLE_SECONDS = 2.0
CAMERA_FPS = 10
FRUIT_COLORS = ((0, 200, 0), (255, 200, 0), (0, 200, 255), (255, 0, 255))
BOMB_COLOR = (255, 0, 0)
BAR_COLOR = (255, 120, 0)
TEXT_COLOR = (255, 120, 0)
SCORE_COLOR = (255, 255, 255)
SCORE_SCALE = 2
READY_TEXTS = ("3", "2", "1", "GO!")
HINT_TEXT = "SWIPE!"
BAR_RESERVE = 2 * 6 * SCORE_SCALE + 2   # px kept clear at the right of row 0 for a two-digit score and its gutter
SIDE_MARGIN = FRUIT_R

ICON = icon_from_rows([
    "................",
    "..........##....",
    "........##......",
    "......##........",
    "....####........",
    "...######.......",
    "..########......",
    "..########......",
    "..########......",
    "..########..##..",
    "...######.##....",
    "....####.##.....",
    "..........##....",
    ".........##.....",
    "................",
    "................",
])


def _lerp(pair: tuple[float, float], t: float) -> float:
    share = min(1.0, max(0.0, t / ROUND_SECONDS))
    return pair[0] + (pair[1] - pair[0]) * share


def spawn_gap(run_t: float) -> float:
    """Seconds from a spawn to the next one, run_t seconds into the round."""
    return _lerp(SPAWN_EVERY, run_t)


def _clamp01(v: float) -> float:
    return min(1.0, max(0.0, v))


def _seg_dist(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    """The distance from point p to the segment a-b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = dx * dx + dy * dy
    k = 0.0 if n == 0.0 else _clamp01(((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / n)
    return math.hypot(p[0] - (a[0] + k * dx), p[1] - (a[1] + k * dy))


class Fruit:
    """A fruit or a bomb: its centre (x, y) and velocity (vx, vy) in px and px/s."""

    def __init__(self, x: float, y: float, vx: float, vy: float, bomb: bool, color):
        self.x, self.y, self.vx, self.vy, self.bomb, self.color = x, y, vx, vy, bomb, color


class Seat:
    """One player's blade: Cursor, two Glides for (u, v), a Glide for zone_x."""

    def __init__(self, grace: float):
        self.cursor = Cursor(grace=grace)
        self.gu, self.gv, self.gx = Glide(grace=grace), Glide(grace=grace), Glide(grace=grace)
        self.body: int | None = None
        self.blade: tuple[float, float] | None = None
        self.v: float | None = None             # the Cursor's v, not glided: what CUT_V_MAX judges
        self.trail: list[tuple[float, float]] = []
        self.streak = 0                          # fruit cut in the swipe so far
        self.seen = False                        # a body has ever taken this seat
        self.moved = False                       # the blade moved CUT_MIN_PX this tick with a raised hand

    def reset(self) -> None:
        self.cursor = Cursor(grace=self.cursor.grace)
        for g in (self.gu, self.gv, self.gx):
            g.reset()
        self.blade, self.v, self.trail, self.streak = None, None, [], 0


class Swat(Game):
    info = GameInfo(name="swat", title="SWAT", verb="SWAT", icon=ICON, needs=frozenset({"pose"}),
                    layouts=frozenset({"128x64"}), players=2, kind="score")
    PHASES = ("ready", "play", "over")
    CAPTION_KEYS = ("phase", "score", "t_left")
    SCENARIOS = MappingProxyType({})     # filled below, once the scripts exist

    def reset(self, size, rng: random.Random, fx) -> None:
        self.w, self.h = size
        self.rng, self.fx = rng, fx
        self.grace = capture_grace(CAMERA_FPS)
        self.seats = [Seat(self.grace), Seat(self.grace)]
        self.t = 0.0
        self.phase, self.phase_t = "ready", 0.0
        self.run_t = 0.0
        self.fruit: list[Fruit] = []
        self.spawn_in = 0.0
        self.score = 0
        self.cut = 0
        self.bombs_hit = 0
        self.goal_shown = False
        self._ready_step = -1
        self._active = False
        self._idle = 0.0
        self._hint = False

    # ----- the tick -----

    def update(self, sensed: Sensed, dt: float) -> None:
        self.t += dt
        self.phase_t += dt
        for seat, body in zip(self.seats, (sensed.player, sensed.player2)):
            self._seat_tick(seat, body, sensed)
        self._active = any(seat.moved for seat in self.seats)
        if self.phase == "ready":
            self._ready()
        elif self.phase == "play":
            self._step_play(dt)
        self._update_hint(dt)
        for seat in self.seats:
            if seat.blade is not None:
                seat.trail = (seat.trail + [seat.blade])[-TRAIL:]
            else:
                seat.trail = seat.trail[1:]

    def _seat_tick(self, seat: Seat, body, sensed: Sensed) -> None:
        """Move the seat's blade, and cut (play only) what the tick's segment crosses."""
        if body is not None and body.id != seat.body:
            seat.body = body.id
            seat.reset()
        if body is not None:
            seat.seen = True
        cur = seat.cursor.update(body, sensed.t)
        u = seat.gu.update(None if cur is None else cur[0], sensed.t, sensed.camera_t)
        v = seat.gv.update(None if cur is None else cur[1], sensed.t, sensed.camera_t)
        zx = seat.gx.update(None if body is None else body.zone_x, sensed.t, sensed.camera_t)
        before = seat.blade
        if u is None or v is None or zx is None:
            seat.blade, seat.v = None, None
        else:
            share = _clamp01((zx - ZONE_LO) / (ZONE_HI - ZONE_LO))
            lo, hi = -ARM_PX / 4, self.w - 1 + ARM_PX / 4
            x = min(self.w - 1.0, max(0.0, lo + share * (hi - lo) + (u - 0.5) * ARM_PX))
            y = BLADE_TOP + _clamp01((v - V_TOP) / (V_BOTTOM - V_TOP)) * (BLADE_BOTTOM - BLADE_TOP)
            seat.blade, seat.v = (x, y), cur[1] if cur is not None else None
        self.swipe(seat, before, seat.blade, seat.v)

    def swipe(self, seat: Seat, a, b, v) -> None:
        """The blade went from a to b this tick with the Cursor at height v (either end None: no blade). A raised hand
        (v under CUT_V_MAX) that moved CUT_MIN_PX is a swipe: it cuts every fruit within FRUIT_R + 1 px of its
        segment, a bomb costs, and COMBO fruit in one swipe pop and flash."""
        seat.moved = (a is not None and b is not None and v is not None and v < CUT_V_MAX
                      and math.dist(a, b) >= CUT_MIN_PX - 1e-9)
        if not seat.moved:
            seat.streak = 0
            return
        if self.phase != "play":
            return
        hits = [f for f in self.fruit if _seg_dist((f.x, f.y), a, b) <= FRUIT_R + 1 + 1e-9]
        if not hits:
            return
        combo = False
        for f in hits:
            self.fruit.remove(f)
            if f.bomb:
                self._bomb(seat, f)
            else:
                self.score += 1
                self.cut += 1
                seat.streak += 1
                if seat.streak >= COMBO:
                    seat.streak, combo = 0, True
        flashed = False
        if combo:
            self.fx.pop("COMBO", self.w / 2, self.h / 2 - 8, (255, 255, 255))
            flashed = bool(self.fx.flash((255, 255, 255), 0.15))
        for f in hits:
            if not f.bomb:
                self.fx.pop("+1", f.x, f.y - 4, f.color)
                if not flashed:
                    self.fx.burst(f.x, f.y, f.color)
        if not self.goal_shown and self.score >= GOAL:
            self.goal_shown = True
            self.fx.banner("GOAL!", 1.0)

    def _bomb(self, seat: Seat, f: Fruit) -> None:
        seat.streak = 0
        self.bombs_hit += 1
        self.score = max(0, self.score - BOMB_COST)
        self.fx.freeze(0.15)
        self.fx.shake(3, 0.3)
        self.fx.echo(self.seats.index(seat) + 1, "hit")
        self.fx.pop(f"-{BOMB_COST}", f.x, f.y - 4, BOMB_COLOR)

    def _ready(self) -> None:
        k = min(len(READY_TEXTS) - 1, int(self.phase_t / (READY_SECONDS / len(READY_TEXTS)) + 1e-9))
        if k != self._ready_step:
            self._ready_step = k
            self.fx.banner(READY_TEXTS[k], READY_SECONDS / len(READY_TEXTS))
        if self.phase_t >= READY_SECONDS - 1e-9:
            self._set("play")
            self.run_t, self.spawn_in = 0.0, 0.0

    def _set(self, phase: str) -> None:
        self.phase, self.phase_t = phase, 0.0

    def _step_play(self, dt: float) -> None:
        self.run_t += dt
        self.spawn_in -= dt
        while self.spawn_in <= 0.0:
            self._spawn_random()
            self.spawn_in += spawn_gap(self.run_t)
        for f in self.fruit:
            f.x += f.vx * dt
            f.y += f.vy * dt
            f.vy += GRAVITY * dt
        self.fruit = [f for f in self.fruit if not (f.vy > 0 and f.y >= SPAWN_Y)]
        if self.run_t >= ROUND_SECONDS - 1e-9:
            self._to_over()

    def spawn(self, x: float, y: float, vx: float, vy: float, bomb: bool = False, color=None) -> Fruit:
        f = Fruit(x, y, vx, vy, bomb, BOMB_COLOR if bomb else (FRUIT_COLORS[0] if color is None else color))
        self.fruit.append(f)
        return f

    def _spawn_random(self) -> None:
        rng = self.rng
        vy, vx = rng.uniform(*LAUNCH_VY), rng.uniform(*DRIFT_VX)
        drift = abs(vx) * 2 * abs(vy) / GRAVITY                    # the sideways travel of the whole flight
        lo = SIDE_MARGIN + (drift if vx < 0 else 0.0)
        hi = self.w - 1 - SIDE_MARGIN - (drift if vx > 0 else 0.0)
        x = rng.uniform(lo, max(lo, hi))
        bomb = rng.random() < BOMB_SHARE
        color = rng.choice(FRUIT_COLORS)
        self.spawn(x, SPAWN_Y, vx, vy, bomb, color)

    def _to_over(self) -> None:
        if self.cut > 0 and not any(seat.seen for seat in self.seats[1:]):
            self.scores.record(self.score)          # solo, once, only when a fruit was cut (C41, Q23)
        self._set("over")
        if self.score >= GOAL:
            self.fx.celebrate((0, 200, 0))

    def _update_hint(self, dt: float) -> None:
        self._idle = 0.0 if self._active else self._idle + dt
        if self._active or self.phase == "over":
            self._hint = False
        elif self._idle >= HINT_IDLE_SECONDS - 1e-9:
            self._hint = True

    def done(self) -> bool:
        return self.phase == "over" and self.phase_t >= OVER_SECONDS - 1e-9

    # ----- drawing -----

    def draw(self, canvas: Canvas) -> None:
        w = self.w
        for f in self.fruit:
            x, y = round(f.x), round(f.y)
            if f.bomb:                                   # a fat plus: its corners are dark, a fruit is a full square
                canvas.fill_rect(x - FRUIT_R, y - 1, 2 * FRUIT_R + 1, 3, f.color)
                canvas.fill_rect(x - 1, y - FRUIT_R, 3, 2 * FRUIT_R + 1, f.color)
            else:
                canvas.fill_rect(x - FRUIT_R, y - FRUIT_R, 2 * FRUIT_R + 1, 2 * FRUIT_R + 1, f.color)
        for number, seat in enumerate(self.seats):
            color = PLAYER_COLORS[number]
            for p, q in zip(seat.trail, seat.trail[1:]):
                canvas.line(round(p[0]), round(p[1]), round(q[0]), round(q[1]), color)
            if seat.blade is not None:
                canvas.fill_rect(round(seat.blade[0]) - 1, round(seat.blade[1]) - 1, 3, 3, color)
        left = round((w - BAR_RESERVE) * self._t_left() / ROUND_SECONDS)
        if left > 0:
            canvas.fill_rect(0, 0, left, 1, BAR_COLOR)
        if self._hint and self.phase != "over":
            width = canvas.text_width(HINT_TEXT) - 1
            canvas.text((w - width) // 2, self.h // 2 - 4, HINT_TEXT, TEXT_COLOR)
        text = str(self.score)
        x0 = w - canvas.text_width(text, SCORE_SCALE)
        canvas.fill_rect(x0 - 1, 0, w - x0 + 1, CELL_H * SCORE_SCALE + 2, (0, 0, 0))    # the score's dark gutter
        canvas.text(x0, 1, text, SCORE_COLOR, SCORE_SCALE)

    def _t_left(self) -> float:
        return max(0.0, ROUND_SECONDS - self.run_t) if self.phase != "ready" else ROUND_SECONDS

    def debug_state(self) -> dict:
        a, b = self.seats[0].blade, self.seats[1].blade
        near = lambda bomb: None if a is None or not (c := [f for f in self.fruit if f.bomb is bomb]) else min(
            c, key=lambda f: math.hypot(f.x - a[0], f.y - a[1]))
        target, bomb = near(False), near(True)
        xy = lambda p: None if p is None else (round(p[0], 2), round(p[1], 2))
        return {"phase": self.phase, "score": self.score, "cut": self.cut, "bombs_hit": self.bombs_hit,
                "active": bool(self._active), "hint": bool(self._hint), "t_left": round(self._t_left(), 1),
                "blade_xy": xy(a), "blade2_xy": xy(b),
                "target_xy": None if target is None else xy((target.x, target.y)),
                "bomb_xy": None if bomb is None else xy((bomb.x, bomb.y))}


# ----- scripts -----

CANONICAL_SECONDS = 70.0
RAISE_AT = 4.5


def cam_x(zone_x: float) -> float:
    """The camera x a Person stands at to be at zone_x of the mat (the default calibration's zone)."""
    from arcade.calibration import Calibration

    x0, _, x1, _ = Calibration().zone
    return x0 + zone_x * (x1 - x0)


def _swipes(person: Person, start: float, end: float, lo: float = 0.2, hi: float = 0.8, seconds: float = 0.4,
            hand: str = "right") -> None:
    """The hand sweeps lo to hi and back, each stroke `seconds`, from `start` to `end`."""
    t, up = start, True
    while t < end - 1e-9:
        person.wrist(hand, lo if up else hi, hi if up else lo, seconds, at=t)
        t, up = t + seconds, not up


def canonical():
    """The wall empty for 2 s, one player walks up, raises a hand at 4.5 s (the game launches), sweeps the wrist
    from the top of the reach box to the hip, walks across the mat with the hand up, then swipes fast 0.2 to 0.8
    every 0.4 s at the centre for the rest of CANONICAL_SECONDS."""
    person = Person(cam_x(0.5), id=1).arrive(2.0).raise_hand(RAISE_AT, 0.5)
    person.wrist("right", 0.0, 1.0, 1.5, at=5.0)
    person.wrist("right", 0.5, 0.5, 5.0, at=6.5)
    person.walk(cam_x(0.05), 0.8, at=7.0).walk(cam_x(0.95), 2.4, at=7.8).walk(cam_x(0.5), 0.8, at=10.2)
    _swipes(person, 11.5, CANONICAL_SECONDS)
    return scene(persons=[person], ticks=round(CANONICAL_SECONDS / TICK))


def duo():
    """Two players walk up at 1 s and swipe, each at their own pace, for 70 s."""
    a = Person(cam_x(0.3), id=1).arrive(1.0)
    b = Person(cam_x(0.7), id=2, height=0.55).arrive(1.5)
    _swipes(a, 2.0, CANONICAL_SECONDS, seconds=0.4)
    _swipes(b, 2.0, CANONICAL_SECONDS, 0.3, 0.7, 0.5)
    return scene(persons=[a, b], ticks=round(CANONICAL_SECONDS / TICK))


def idle_body(body_id: int = 1, seconds: float = 60.0):
    """One body standing, hands down, for 60 s (body_id and seconds let tests vary the noise and the length)."""
    return scene(persons=[Person(cam_x(0.3), id=body_id)], ticks=round(seconds / TICK))


def nobody():
    return scene(ticks=900)


Swat.SCENARIOS = MappingProxyType({"canonical": canonical, "idle_body": idle_body, "nobody": nobody, "duo": duo})
GAME = Swat
