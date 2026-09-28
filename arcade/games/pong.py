"""Pong (spec 8, game 2): paddles follow hand height, sides by where the players stand, a beatable CPU fills an
empty seat. First to WIN_POINTS, else the leader at MAX_SECONDS (a tie goes to player 1's side).

Two seats, a and b (index 0 and 1): seat 0 is player 1's. A seat is held by a body id (a human) or by the CPU (None).
Seats, and which side of the wall each stands on, are settled at every serve; points belong to the seat."""
from __future__ import annotations

import math
import random
from types import MappingProxyType

from arcade.canvas import Canvas
from arcade.game import Game, GameInfo, icon_from_rows
from arcade.input import capture_grace
from arcade.juice import PLAYER_COLORS
from arcade.sensed import Sensed
from arcade.sources.actors import Person, scene

WIN_POINTS = 5
MAX_SECONDS = 90.0
SERVE_SECONDS = 1.0
POINT_SECONDS = 1.0
OVER_SECONDS = 2.0
BALL_START = 60.0       # px/s
BALL_GAIN = 1.08        # the speed times this on each paddle hit
BALL_MAX = 110.0
MAX_ANGLE = 60          # degrees off horizontal at the paddle's edge
CPU_SPEED = 24.0        # px/s: beatable by a ball that arrives late
PADDLE_W = 2
BALL = 2
JOIN_SECONDS = 1.0
SERVE_SPREAD = 20       # degrees either way off horizontal at a serve
CAMERA_FPS = 10         # capture_grace(10): what a human may be missing before the CPU takes the seat
CPU_COLOR = (0, 200, 0)
BALL_COLOR = (255, 255, 255)
NET_COLOR = (0, 0, 96)

ICON = icon_from_rows([
    "................",
    "................",
    "..##........##..",
    "..##........##..",
    "..##........##..",
    "..##........##..",
    "..##........##..",
    "..##...##...##..",
    "..##...##...##..",
    "..##........##..",
    "..##........##..",
    "..##........##..",
    "..##........##..",
    "..##........##..",
    "................",
    "................",
])


class Seat:
    """One side's player: a human (ctrl is a body id) or the CPU (None), with the points it has."""

    def __init__(self, color):
        self.ctrl: int | None = None
        self.color = color
        self.points = 0
        self.seen = -math.inf       # when the human's body was last seen
        self.zone_x = 0.5


class Pong(Game):
    info = GameInfo(name="pong", title="PONG", verb="BLOCK", icon=ICON, needs=frozenset({"pose"}),
                    layouts=frozenset({"128x32"}), players=2, kind="score")
    PHASES = ("serve", "play", "point", "over")
    CAPTION_KEYS = ("phase", "left", "right")
    SCENARIOS = MappingProxyType({})     # filled below, once the scripts exist

    def reset(self, size, rng: random.Random, fx) -> None:
        self.w, self.h = size
        self.rng, self.fx = rng, fx
        self.paddle_h = self.h // 4
        self.t = 0.0
        self.phase, self.phase_t = "serve", 0.0
        self.seats = [Seat(PLAYER_COLORS[0]), Seat(PLAYER_COLORS[1])]
        self.left_seat, self.right_seat = 0, 1
        self.left_y = self.right_y = (self.h - 1) / 2
        self.bx, self.by = self.w / 2, self.h / 2
        self.vx = self.vy = 0.0
        self.speed = BALL_START
        self.serve_dir = rng.choice((-1, 1))
        self.winner: str | None = None
        self.grace = capture_grace(CAMERA_FPS)
        self._assigned = False
        self._synced = False
        self._duel = False
        self._active = False
        self._p1: int | None = None             # the seat player 1 took at the first serve they were there for
        self._last: dict[int, float] = {}       # body id -> when last seen
        self._since: dict[int, float] = {}      # body id -> when its present run began

    # ----- seats -----

    def _bodies(self, sensed: Sensed) -> dict:
        found = {b.id: b for b in sensed.bodies}
        for b in (sensed.player, sensed.player2):
            if b is not None:
                found[b.id] = b
        return found

    def _track(self, found: dict) -> None:
        for body_id, body in found.items():
            if self.t - self._last.get(body_id, -math.inf) > self.grace:
                self._since[body_id] = self.t
            self._last[body_id] = self.t
            for seat in self.seats:
                if seat.ctrl == body_id:
                    seat.seen, seat.zone_x = self.t, body.zone_x

    def _assign(self, sensed: Sensed) -> None:
        """Settle the seats and the sides for a serve."""
        for seat in self.seats:
            if seat.ctrl is not None and self.t - seat.seen > self.grace:
                seat.ctrl = None
        bound = {seat.ctrl for seat in self.seats}
        candidates = []
        if sensed.player is not None and sensed.player.id not in bound:
            candidates.append(sensed.player)
        p2 = sensed.player2
        first = not self._assigned         # whoever stands there when the game starts was already waiting
        if (p2 is not None and p2.id not in bound
                and (first or self.t - self._since.get(p2.id, self.t) >= JOIN_SECONDS - 1e-9)):
            candidates.append(p2)
        for seat in self.seats:
            if seat.ctrl is None and candidates:
                body = candidates.pop(0)
                seat.ctrl, seat.seen, seat.zone_x = body.id, self.t, body.zone_x
        if self._p1 is None:
            taken = [i for i, seat in enumerate(self.seats) if seat.ctrl is not None]
            lead = next((i for i in taken if sensed.player is not None and self.seats[i].ctrl == sensed.player.id),
                        taken[0] if taken else None)
            self._p1 = lead
        self._synced = False                # paddles jump to the hands once, without counting as input
        for seat in self.seats:
            if seat.ctrl is not None:
                seat.color = PLAYER_COLORS[0] if sensed.player is not None and seat.ctrl == sensed.player.id \
                    else PLAYER_COLORS[1]
        humans = [i for i, seat in enumerate(self.seats) if seat.ctrl is not None]
        self._duel = self._duel or len(humans) == 2
        if len(humans) == 2:
            a, b = sorted(humans, key=lambda i: (self.seats[i].zone_x, i))
            self.left_seat, self.right_seat = a, b
        elif len(humans) == 1:
            me = humans[0]
            other = 1 - me
            if self.seats[me].zone_x <= 0.5:
                self.left_seat, self.right_seat = me, other
            else:
                self.left_seat, self.right_seat = other, me
        else:
            self.left_seat, self.right_seat = 0, 1

    def _humans(self) -> int:
        return sum(seat.ctrl is not None for seat in self.seats)

    def _score_seat(self) -> Seat:
        """Player 1's seat, by the body seated at the first serve: it stays theirs when they leave (Q23)."""
        return self.seats[self._p1 or 0]

    # ----- the tick -----

    def update(self, sensed: Sensed, dt: float) -> None:
        self.t += dt
        self.phase_t += dt
        self._active = False
        found = self._bodies(sensed)
        self._track(found)
        if not self._assigned:
            self._assign(sensed)
            self._assigned = True
        self._move_paddles(found, dt)
        if self.phase == "serve":
            if self.t >= MAX_SECONDS:
                self._finish()
            elif self.phase_t >= SERVE_SECONDS - 1e-9:
                self._launch()
        elif self.phase == "play":
            if self.t >= MAX_SECONDS:
                self._finish()
            else:
                self._step_ball(dt)
        elif self.phase == "point":
            if self.phase_t >= POINT_SECONDS - 1e-9:
                if self.t >= MAX_SECONDS or any(seat.points >= WIN_POINTS for seat in self.seats):
                    self._finish()
                else:
                    self._assign(sensed)
                    self._to_serve()

    def _set(self, phase: str) -> None:
        self.phase, self.phase_t = phase, 0.0

    def _to_serve(self) -> None:
        self.bx, self.by = self.w / 2, self.h / 2
        self.vx = self.vy = 0.0
        self.speed = BALL_START
        self._set("serve")

    def _launch(self) -> None:
        a = math.radians(self.rng.uniform(-SERVE_SPREAD, SERVE_SPREAD))
        self.vx, self.vy = self.serve_dir * self.speed * math.cos(a), self.speed * math.sin(a)
        self._set("play")

    def _clamp(self, y: float) -> float:
        half = self.paddle_h / 2
        return min(self.h - half, max(half, y))

    def _move_paddles(self, found: dict, dt: float) -> None:
        for side in ("left", "right"):
            seat = self.seats[self.left_seat if side == "left" else self.right_seat]
            y = self.left_y if side == "left" else self.right_y
            if seat.ctrl is None:
                new = self._cpu_y(side, y, dt)
            else:
                body = found.get(seat.ctrl)
                cursor = None if body is None else body.cursor
                new = y if cursor is None else self._clamp(cursor[1] * (self.h - 1))
                if abs(new - y) >= 1.0 and self._synced:
                    self._active = True
            if side == "left":
                self.left_y = new
            else:
                self.right_y = new
        self._synced = True

    def _cpu_y(self, side: str, y: float, dt: float) -> float:
        toward = self.vx < 0 if side == "left" else self.vx > 0
        target = self.by if self.phase == "play" and toward else (self.h - 1) / 2
        step = CPU_SPEED * dt
        return self._clamp(y + max(-step, min(step, target - y)))

    def _step_ball(self, dt: float) -> None:
        old_x, old_y = self.bx, self.by
        self.bx += self.vx * dt
        self.by += self.vy * dt
        if self.by < 1.0:
            self.by, self.vy = 2.0 - self.by, -self.vy
        elif self.by > self.h - 1.0:
            self.by, self.vy = 2.0 * (self.h - 1.0) - self.by, -self.vy
        half = BALL / 2
        if self.vx < 0 and old_x - half >= PADDLE_W and self.bx - half < PADDLE_W:
            frac = (old_x - half - PADDLE_W) / (old_x - self.bx)
            if self._hits(self.left_y, old_y + (self.by - old_y) * frac):
                self._bounce("left", self.left_seat, self.by)
                return
        elif self.vx > 0 and old_x + half <= self.w - PADDLE_W and self.bx + half > self.w - PADDLE_W:
            frac = (self.w - PADDLE_W - old_x - half) / (self.bx - old_x)
            if self._hits(self.right_y, old_y + (self.by - old_y) * frac):
                self._bounce("right", self.right_seat, self.by)
                return
        if self.bx <= 0:
            self._goal(self.right_seat, -1)
        elif self.bx >= self.w:
            self._goal(self.left_seat, 1)

    def _hits(self, paddle_y: float, ball_y: float) -> bool:
        return abs(ball_y - paddle_y) <= self.paddle_h / 2 + BALL / 2

    def _bounce(self, side: str, seat_index: int, ball_y: float) -> None:
        paddle_y = self.left_y if side == "left" else self.right_y
        offset = max(-1.0, min(1.0, (ball_y - paddle_y) / (self.paddle_h / 2 + BALL / 2)))
        a = math.radians(MAX_ANGLE) * offset
        self.speed = min(self.speed * BALL_GAIN, BALL_MAX)
        sign = 1 if side == "left" else -1
        self.vx, self.vy = sign * self.speed * math.cos(a), self.speed * math.sin(a)
        self.bx = PADDLE_W + BALL / 2 if side == "left" else self.w - PADDLE_W - BALL / 2
        seat = self.seats[seat_index]
        if seat.ctrl is not None:
            self._active = True
        self.fx.burst(self.bx, self.by, seat.color if seat.ctrl is not None else CPU_COLOR)

    def _goal(self, scorer: int, direction: int) -> None:
        seat = self.seats[scorer]
        seat.points += 1
        self.serve_dir = direction              # served toward the side that conceded
        self.bx = 0.0 if direction < 0 else self.w - 1.0
        self.vx = self.vy = 0.0
        color = seat.color if seat.ctrl is not None else CPU_COLOR
        self.fx.shake(2, 0.3)
        self.fx.pop("+1", self.w // 4 if scorer == self.left_seat else 3 * self.w // 4, self.h // 2, color)
        self._set("point")

    def _finish(self) -> None:
        a, b = self.seats
        leader = b if b.points > a.points else a
        self.winner = "left" if leader is self.seats[self.left_seat] else "right"
        self.fx.celebrate(leader.color if leader.ctrl is not None else CPU_COLOR)
        if not self._duel and self._humans() == 1:
            self.scores.record(self._score_seat().points)
        self._set("over")

    def done(self) -> bool:
        return self.phase == "over" and self.phase_t >= OVER_SECONDS - 1e-9

    # ----- drawing -----

    def _color(self, seat: Seat):
        return seat.color if seat.ctrl is not None else CPU_COLOR

    def draw(self, canvas: Canvas) -> None:
        w, h = self.w, self.h
        for y in range(0, h, 4):
            canvas.fill_rect(w // 2, y, 1, 2, NET_COLOR)
        left, right = self.seats[self.left_seat], self.seats[self.right_seat]
        canvas.text(w // 4 - 3, 0, left.points, self._color(left))
        canvas.text(3 * w // 4 - 3, 0, right.points, self._color(right))
        ph = self.paddle_h
        canvas.fill_rect(0, self.left_y - ph / 2, PADDLE_W, ph, self._color(left))
        canvas.fill_rect(w - PADDLE_W, self.right_y - ph / 2, PADDLE_W, ph, self._color(right))
        if self.phase in ("serve", "play"):
            canvas.fill_rect(self.bx - BALL / 2, self.by - BALL / 2, BALL, BALL, BALL_COLOR)

    def debug_state(self) -> dict:
        cpus = [side for side, i in (("left", self.left_seat), ("right", self.right_seat))
                if self.seats[i].ctrl is None]
        cap = lambda v, top: min(max(0.0, v), top - 0.01)
        return {"phase": self.phase, "score": self._score_seat().points,
                "left": self.seats[self.left_seat].points, "right": self.seats[self.right_seat].points,
                "cpu": cpus[0] if len(cpus) == 1 else None, "humans": self._humans(), "active": bool(self._active),
                "speed": round(self.speed, 3),
                "ball_xy": (round(cap(self.bx, self.w), 2), round(cap(self.by, self.h), 2)),
                "left_xy": (PADDLE_W / 2, round(self.left_y, 2)),
                "right_xy": (self.w - PADDLE_W / 2, round(self.right_y, 2))}


def _sweeps(person: Person, start: float = 4.0, end: float = 100.0) -> Person:
    """The right wrist sweeping 0 to 1 and back, one sweep each way per 1.2 s."""
    t = start
    while t < end:
        person.wrist("right", 0.0, 1.0, 0.6, at=t).wrist("right", 1.0, 0.0, 0.6, at=t + 0.6)
        t += 1.2
    return person


def canonical():
    """The wall empty for 2 s, then one player walks up, raises a hand at 4.5 s and sweeps from 6 s: 100 s."""
    person = Person(0.3, id=1).arrive(2.0).raise_hand(4.5, 0.5)
    return scene(persons=[_sweeps(person, start=6.0)], ticks=3000)


def idle_body():
    """One body standing, hands down, for 60 s."""
    return scene(persons=[Person(0.3, id=1)], ticks=1800)


def nobody():
    return scene(ticks=900)


def solo():
    """One player who walks up, raises a hand at 2.5 s and then sweeps the paddle up and down."""
    return scene(persons=[_sweeps(Person(0.3, id=1).raise_hand(2.5, 0.5))], ticks=3000)


def duel():
    """The solo player plus a second on the right, arriving at 0.5 s and holding the paddle at mid-height."""
    other = Person(0.7, id=2).arrive(0.5).wrist("right", 0.5, 0.5, 100.0, at=0.5)
    return scene(persons=[_sweeps(Person(0.3, id=1).raise_hand(2.5, 0.5)), other], ticks=3000)


Pong.SCENARIOS = MappingProxyType({"canonical": canonical, "idle_body": idle_body, "nobody": nobody,
                                     "solo": solo, "duel": duel})
GAME = Pong
