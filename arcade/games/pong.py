"""Pong (spec 8, game 2): each paddle follows its player's body stepping in depth (M4c: nearer the camera is up),
sides by where the players stand, a beatable CPU fills an empty seat. First to WIN_POINTS, else the leader at
MAX_SECONDS (a tie goes to player 1's side).

Two seats, a and b (index 0 and 1): seat 0 is player 1's. A seat is held by a body id (a human) or by the CPU (None).
Seats, and which side of the wall each stands on, are settled at every serve; points belong to the seat. A human
seat reads its body through a Depth (arcade/input.py), reset when a body takes the seat, so the middle of the
paddle's travel is where the player stood then; the raised hand only launches (the lobby's rule). A human's goal
banks only when the paddle travelled TRAVEL_SHARE of its range in that rally (C42), and a best needs such a rally.

debug_state: phase, score (player 1's points), left, right, cpu ("left", "right" or None), humans, active, speed,
ball_xy, left_xy, right_xy, near (player 1's Depth value to 2 places, or None) and hint (the step hint is wanted)."""
from __future__ import annotations

import math
import random
from types import MappingProxyType

from arcade.canvas import Canvas
from arcade.game import Game, GameInfo, icon_from_rows
from arcade.input import Depth, capture_grace
from arcade.juice import PLAYER_COLORS
from arcade.sensed import Sensed
from arcade.sources.actors import TICK, Person, scene
from show.font import CELL_H

WIN_POINTS = 5
MAX_SECONDS = 90.0
SERVE_SECONDS = 1.0
POINT_SECONDS = 1.0
OVER_SECONDS = 2.0
BALL_START = 55.0       # px/s: 2.3 s a crossing; a body needs its step
BALL_GAIN = 1.08        # the speed times this on each paddle hit
BALL_MAX = 95.0         # px/s: 1.35 s a crossing at the fastest
MAX_ANGLE = 50          # degrees off horizontal at the paddle's edge: vertical speed at most 73 px/s
CPU_SPEED = 0.3         # wall heights per second (19 px/s at 64 rows): beatable by an angled return (Q46: 0.35)
SCORE_SCALE = 2         # spec 7.4: both scores 10x14, top row y 1, centred on w/4 and 3w/4
PADDLE_W = 3            # px: a smoothed control's 2-tick answer must show 12 px (spec 11)
PADDLE_SHARE = 0.25     # of the height: 16 px at 64 rows
TRAVEL_SHARE = 0.3      # C42: a rally counts when the paddle's travel (max y - min y) is at least this share of its
                        # range (h - paddle_h): 14.4 px at 128x64, over a still body's 8 px under REAL_NOISE (S1's
                        # measure; the operator's ruling, from the plan's 0.25), under a slow player's 17
NEAR_IS_UP = True       # Q43: stepping towards the camera raises the paddle
HINT_LINES = ("STEP IN = UP", "STEP BACK = DOWN")   # 1x: 71 and 95 px wide
HINT_COLOR = (255, 160, 0)
HINT_IDLE_SECONDS = 5.0 # in play with the rally's travel under TRAVEL_SHARE this long: the hint again
HINT_FADE = 0.3         # s in and out: never a blink
HINT_GAP = 2            # px between the hint's two lines
GLYPH_H = 7             # the 5x7 font's rows at 1x
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

    def __init__(self, color, grace: float):
        self.ctrl: int | None = None
        self.color = color
        self.points = 0
        self.seen = -math.inf       # when the human's body was last seen
        self.zone_x = 0.5
        self.depth = Depth(grace=grace)
        self.near: float | None = None      # the Depth's value on the last tick
        self.lo = self.hi = math.nan        # the rally's lowest and highest paddle y (C42), from its launch
        self.anchor = math.nan              # the paddle y at the last tick counted as input (active)
        self.travelled = False      # a rally of this game counted (C42): a best needs it

    def take(self, body) -> None:
        """A body takes the seat: its Depth centres where the body stands now."""
        self.ctrl, self.zone_x = body.id, body.zone_x
        self.depth.reset()
        self.near = None

    def rally(self, y: float) -> None:
        """The rally's travel starts over at paddle y."""
        self.lo = self.hi = y

    @property
    def travel(self) -> float:
        return self.hi - self.lo if self.hi >= self.lo else 0.0


class Pong(Game):
    info = GameInfo(name="pong", title="PONG", verb="BLOCK", icon=ICON, needs=frozenset({"pose"}),
                    layouts=frozenset({"128x64"}), players=2, kind="score")
    PHASES = ("serve", "play", "point", "over")
    CAPTION_KEYS = ("phase", "left", "right", "near")
    SCENARIOS = MappingProxyType({})     # filled below, once the scripts exist

    def reset(self, size, rng: random.Random, fx) -> None:
        self.w, self.h = size
        self.rng, self.fx = rng, fx
        self.paddle_h = round(self.h * PADDLE_SHARE)
        self.travel_px = TRAVEL_SHARE * (self.h - self.paddle_h)
        self.t = 0.0
        self.phase, self.phase_t = "serve", 0.0
        self.grace = capture_grace(CAMERA_FPS)
        self.seats = [Seat(PLAYER_COLORS[0], self.grace), Seat(PLAYER_COLORS[1], self.grace)]
        self.left_seat, self.right_seat = 0, 1
        self.left_y = self.right_y = (self.h - 1) / 2
        self.bx, self.by = self.w / 2, self.h / 2
        self.vx = self.vy = 0.0
        self.speed = BALL_START
        self.serve_dir = rng.choice((-1, 1))
        self.winner: str | None = None
        self._hint = True                       # wanted: at the first serve, and after HINT_IDLE_SECONDS idle
        self._mask_key, self._mask = None, {}   # draw's cached masks, and the canvas they were drawn for
        self._hint_level = 0.0                  # shown: fades towards wanted at 1 / HINT_FADE a second
        self._idle = 0.0                        # seconds in play since a rally's travel last counted
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
                seat.ctrl, seat.near = None, None
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
                seat.take(candidates.pop(0))
                seat.seen = self.t
        if self._p1 is None:
            taken = [i for i, seat in enumerate(self.seats) if seat.ctrl is not None]
            lead = next((i for i in taken if sensed.player is not None and self.seats[i].ctrl == sensed.player.id),
                        taken[0] if taken else None)
            self._p1 = lead
        self._synced = False                # paddles jump to the bodies once, without counting as input
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

    def _walk_up(self, sensed: Sensed) -> None:
        """The first body in view, with no human seated, takes the CPU seat on its side of the wall at once, mid-rally."""
        body = sensed.player
        if body is None or self._humans() or any(seat.ctrl == body.id for seat in self.seats):
            return
        index = self.left_seat if body.zone_x <= 0.5 else self.right_seat
        seat = self.seats[index]
        seat.take(body)
        seat.seen = self.t
        seat.color = PLAYER_COLORS[0]
        if self._p1 is None:
            self._p1 = index
        self._synced = False

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
        elif self.phase != "over":
            self._walk_up(sensed)
        self._move_paddles(sensed, found, dt)
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
        self._update_hint(dt)

    def _update_hint(self, dt: float) -> None:
        """The hint is wanted at the first serve; a rally whose travel counts takes it away, and HINT_IDLE_SECONDS
        in play without one bring it back. It fades towards what is wanted, and only while a human is seated."""
        humans = [seat for seat in self.seats if seat.ctrl is not None]
        if self.phase == "play":
            if any(seat.travel >= self.travel_px - 1e-9 for seat in humans):
                self._idle, self._hint = 0.0, False
            else:
                self._idle += dt
                if self._idle >= HINT_IDLE_SECONDS - 1e-9:
                    self._hint = True
        target = 1.0 if self._shows_hint() else 0.0
        step = dt / HINT_FADE
        self._hint_level = min(target, self._hint_level + step) if target > self._hint_level \
            else max(target, self._hint_level - step)

    def _shows_hint(self) -> bool:
        return self._hint and self.phase != "over" and self._humans() > 0

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
        for seat, y in self._paddles():
            seat.rally(y)
        self._set("play")

    def _paddles(self):
        """(seat, paddle y) for the left side, then the right."""
        return ((self.seats[self.left_seat], self.left_y), (self.seats[self.right_seat], self.right_y))

    def _clamp(self, y: float) -> float:
        half = self.paddle_h / 2
        return min(self.h - half, max(half, y))

    def _depth_y(self, v: float) -> float:
        """The paddle's centre for a Depth value: the control's whole range is the paddle's whole travel."""
        up = v if NEAR_IS_UP else 1.0 - v
        return self.paddle_h / 2 + (1.0 - up) * (self.h - self.paddle_h)

    def _move_paddles(self, sensed: Sensed, found: dict, dt: float) -> None:
        for side in ("left", "right"):
            seat = self.seats[self.left_seat if side == "left" else self.right_seat]
            y = self.left_y if side == "left" else self.right_y
            if seat.ctrl is None:
                new = self._cpu_y(side, y, dt)
            else:
                seat.near = seat.depth.update(found.get(seat.ctrl), sensed.t, sensed.camera_t)
                new = y if seat.near is None else self._clamp(self._depth_y(seat.near))
                if not self._synced or math.isnan(seat.lo):
                    seat.rally(new)                 # a jump to a new body is not travel
                    seat.anchor = new
                else:
                    if abs(new - seat.anchor) >= self.travel_px - 1e-9:
                        self._active = True         # input, judged as C42 judges it: not a still body's jitter
                        seat.anchor = new
                    if self.phase == "play":
                        seat.lo, seat.hi = min(seat.lo, new), max(seat.hi, new)
                        if seat.travel >= self.travel_px - 1e-9:
                            seat.travelled = True
            if side == "left":
                self.left_y = new
            else:
                self.right_y = new
        self._synced = True

    def _cpu_y(self, side: str, y: float, dt: float) -> float:
        toward = self.vx < 0 if side == "left" else self.vx > 0
        target = self.by if self.phase == "play" and toward else (self.h - 1) / 2
        step = CPU_SPEED * self.h * dt
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
        banked = seat.ctrl is None or seat.travel >= self.travel_px - 1e-9     # C42: by the rally's travel
        self.serve_dir = direction              # served toward the side that conceded
        self.bx = 0.0 if direction < 0 else self.w - 1.0
        self.vx = self.vy = 0.0
        self._set("point")
        if not banked:
            return
        seat.points += 1
        color = seat.color if seat.ctrl is not None else CPU_COLOR
        self.fx.shake(2, 0.3)
        self.fx.pop("+1", self.w // 4 if scorer == self.left_seat else 3 * self.w // 4, self.h // 2, color)

    def _finish(self) -> None:
        a, b = self.seats
        leader = b if b.points > a.points else a
        self.winner = "left" if leader is self.seats[self.left_seat] else "right"
        self.fx.celebrate(leader.color if leader.ctrl is not None else CPU_COLOR)
        if not self._duel and self._humans() == 1 and self._score_seat().travelled:
            self.scores.record(self._score_seat().points)
        self._set("over")

    def done(self) -> bool:
        return self.phase == "over" and self.phase_t >= OVER_SECONDS - 1e-9

    # ----- drawing -----

    def _color(self, seat: Seat):
        return seat.color if seat.ctrl is not None else CPU_COLOR

    def _masks(self, canvas: Canvas) -> dict:
        """The net's and the hint's lit pixels on this canvas, drawn once (a bool mask each); the scores' by text.
        draw lights them in their colours, pixel for pixel what fill_rect and text would draw each tick."""
        key = (canvas.width, canvas.height, id(canvas.font), self.w, self.h)
        if self._mask_key != key:
            scratch = Canvas(canvas.width, canvas.height, canvas.font)
            for y in range(0, self.h, 4):
                scratch.fill_rect(self.w // 2, y, 1, 2, (255, 255, 255))
            net = scratch.frame.any(axis=2)
            scratch.clear()
            self._draw_hint(scratch, (255, 255, 255))
            self._mask_key, self._mask = key, {"net": net, "hint": scratch.frame.any(axis=2), "score": {}}
        return self._mask

    def _score_mask(self, canvas: Canvas, masks: dict, text: str):
        if text not in masks["score"]:
            scratch = Canvas(canvas.text_width(text, SCORE_SCALE), CELL_H * SCORE_SCALE, canvas.font)
            scratch.text(0, 0, text, (255, 255, 255), SCORE_SCALE)
            masks["score"][text] = scratch.frame.any(axis=2)
        return masks["score"][text]

    def draw(self, canvas: Canvas) -> None:
        w = self.w
        masks = self._masks(canvas)
        canvas.frame[masks["net"]] = NET_COLOR
        if self._hint_level > 0.0:
            canvas.frame[masks["hint"]] = tuple(round(c * self._hint_level) for c in HINT_COLOR)
        left, right = self.seats[self.left_seat], self.seats[self.right_seat]
        for seat, centre in ((left, w // 4), (right, 3 * w // 4)):
            text = str(seat.points)
            width = canvas.text_width(text, SCORE_SCALE)
            canvas.blit(self._score_mask(canvas, masks, text), centre - width // 2, 1, self._color(seat))
        ph = self.paddle_h
        canvas.fill_rect(0, self.left_y - ph / 2, PADDLE_W, ph, self._color(left))
        canvas.fill_rect(w - PADDLE_W, self.right_y - ph / 2, PADDLE_W, ph, self._color(right))
        if self.phase in ("serve", "play"):
            canvas.fill_rect(self.bx - BALL / 2, self.by - BALL / 2, BALL, BALL, BALL_COLOR)

    def _draw_hint(self, canvas: Canvas, color) -> None:
        """HINT_LINES, 1x, centred, as a block around three quarters of the height; a line wider than the wall is
        left out. draw fades it by scaling the colour, so the low channel stays 0."""
        top = round(self.h * 3 / 4) - (len(HINT_LINES) * (GLYPH_H + HINT_GAP) - HINT_GAP) // 2
        for k, line in enumerate(HINT_LINES):
            width = canvas.text_width(line) - 1      # the last glyph's cell gap is not drawn
            if width <= self.w:
                canvas.text((self.w - width) // 2, top + k * (GLYPH_H + HINT_GAP), line, color)

    def debug_state(self) -> dict:
        cpus = [side for side, i in (("left", self.left_seat), ("right", self.right_seat))
                if self.seats[i].ctrl is None]
        p1 = self._score_seat()
        near = None if p1.ctrl is None or p1.near is None else round(p1.near, 2)
        cap = lambda v, top: min(max(0.0, v), top - 0.01)
        return {"phase": self.phase, "score": self._score_seat().points,
                "left": self.seats[self.left_seat].points, "right": self.seats[self.right_seat].points,
                "cpu": cpus[0] if len(cpus) == 1 else None, "humans": self._humans(), "active": bool(self._active),
                "speed": round(self.speed, 3),
                "ball_xy": (round(cap(self.bx, self.w), 2), round(cap(self.by, self.h), 2)),
                "left_xy": (PADDLE_W / 2, round(self.left_y, 2)),
                "right_xy": (self.w - PADDLE_W / 2, round(self.right_y, 2)),
                "near": near, "hint": bool(self._shows_hint())}


STEP_NEAR, STEP_FAR = 1.28, 0.78   # the scripts' step: ratios of the size the body was first seen at
STEP_SECONDS = 0.8                  # each way: a brisk step
STEP_HOLD = 0.4                     # s the scripts stand at each end, so the paddle settles there
STEP_HEIGHT = 0.7                   # the scripts' body (bots.BODY_HEIGHT): at STEP_FAR it is still in the zone


def _steps(person: Person, start: float = 4.0, end: float = 100.0) -> Person:
    """The body stepping in to STEP_NEAR, then between STEP_FAR and STEP_NEAR, STEP_SECONDS each way with
    STEP_HOLD at each end, from start until end."""
    t = start
    person.scale_to(STEP_NEAR, STEP_SECONDS, at=t)
    t += STEP_SECONDS + STEP_HOLD
    near = False
    while t < end:
        person.scale_to(STEP_NEAR if near else STEP_FAR, STEP_SECONDS, at=t)
        near = not near
        t += STEP_SECONDS + STEP_HOLD
    return person


def _stepper(x: float, id: int) -> Person:
    return Person(x, id=id, height=STEP_HEIGHT)


def canonical():
    """The wall empty for 2 s, then one player walks up, raises a hand at 4.5 s and steps from 6 s: 100 s."""
    person = _stepper(0.3, 1).arrive(2.0).raise_hand(4.5, 0.5)
    return scene(persons=[_steps(person, start=6.0)], ticks=3000)


def idle_body(body_id: int = 1, seconds: float = 60.0):
    """One body standing, hands down, for 60 s (body_id and seconds let tests vary the noise and the length)."""
    return scene(persons=[Person(0.3, id=body_id)], ticks=round(seconds / TICK))


def nobody():
    return scene(ticks=900)


def solo():
    """One player who walks up, raises a hand at 2.5 s and then steps the paddle up and down from 4 s."""
    return scene(persons=[_steps(_stepper(0.3, 1).raise_hand(2.5, 0.5))], ticks=3000)


def duel():
    """The solo player plus a second on the right, arriving at 0.5 s, who steps on its own phase (a quarter of a
    cycle later, so neither paddle follows the other's player), so both players' points bank (C42)."""
    other = _steps(_stepper(0.7, 2).arrive(0.5), start=4.0 + (STEP_SECONDS + STEP_HOLD) / 2)
    return scene(persons=[_steps(_stepper(0.3, 1).raise_hand(2.5, 0.5)), other], ticks=3000)


Pong.SCENARIOS = MappingProxyType({"canonical": canonical, "idle_body": idle_body, "nobody": nobody,
                                     "solo": solo, "duel": duel})
GAME = Pong
