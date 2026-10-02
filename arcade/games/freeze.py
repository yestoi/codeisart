"""Freeze (spec 8 row 10, pose only): everyone dances on green; on red anyone still moving after GRACE is out and
their figure topples; last one standing, or, alone, survive the reds.

Movement is the body's keypoint travel, no music and no motion grid (Q99). Per camera capture (camera_t newer than
the last), a seat's sample is the reach-box (u, v) of each confident wrist of its held skeleton (KeypointHold, so a
dropped shoulder does not move the box) and the zone_x. The travel since an anchor time is the largest of each wrist's
u span and v span, and the zone_x span over STEP_SCALE: a span, not a per-tick difference, because the tracker smooths
(spec 5). Moving is a travel over MOVE_TRAVEL.

The lights are the game's timer, drawn from the launch's rng at reset: green for GREEN_SECONDS (a draw), red for
RED_SECONDS (a draw), REDS reds. A red's anchor is red + GRACE (capture time): a seat that joined and whose travel
passes MOVE_TRAVEL before the green is out (fx.echo(seat, "hit"), its figure topples about its feet over
TOPPLE_SECONDS and fades). A red counts, COUNT_LAG after it ends (late captures of it still arrive), for a seat that is
still in and whose travel over the green before it reached DANCE_TRAVEL; a body that never dances scores nothing and
stores no best (C41, C42). A body seen joins at the next green (the first green too); a joined seat missing past the
grace is out without a topple. Solo plays to REDS or out; two (both joined) to the last one standing or REDS; the
last one standing also counts the red it stood through. Solo only: scores.record(score) once at over when a red
counted; with a seat b, nothing.

Shown: the figures (the lobby's recipe: figure_rect with COLUMN_SLACK of backlash, draw_figure, KeypointHold), a 1 px
border in the light's colour and its word at 2x over a black box on rows 43 to 58 (DANCE or FREEZE): red lit area at
most RED_AREA of the wall, one change per light, never a full-field colour, no flash; the scores at 2x last.

debug_state: phase, light ("none", "green", "red"), score (seat a's counted reds), other (seat b's), out, out2,
danced (seat a's travel over the green now or last reached DANCE_TRAVEL), reds_left, in_grace, active (travel over
MOVE_TRAVEL in 1 s, either seat), hint, player_xy and player2_xy (the head disc's centre, None when not drawn; an
out figure keeps its last upright place)."""
from __future__ import annotations

import math
import random
from collections import deque
from types import MappingProxyType

from arcade.canvas import Canvas
from arcade.figure import HEAD, KeypointHold, STROKE, draw_figure, figure_rect, to_wall
from arcade.game import Game, GameInfo, icon_from_rows
from arcade.input import EPSILON, capture_grace
from arcade.juice import PLAYER_COLORS
from arcade.sensed import LEFT_ANKLE, MIN_CONF, NOSE, RIGHT_ANKLE, SKELETON, Body, Sensed
from arcade.sources.actors import TICK, Person, scene

REDS = 6
GREEN_SECONDS = (3.0, 6.0)
RED_SECONDS = (2.5, 4.0)
GRACE = 0.5                     # seconds into a red (capture time) before a move can put a seat out
MOVE_TRAVEL = 0.25              # a travel over this is moving
DANCE_TRAVEL = 0.5              # a green's travel this big is a dance
STEP_SCALE = 0.4                # zone_x span that counts as one unit of travel
READY_SECONDS = 3.0
TOPPLE_SECONDS = 1.0            # the fall; the fade takes twice this
OVER_SECONDS = 3.0
WIN_SCORE = 4
FIGURE_H = 60
HINT_IDLE_SECONDS = 2.0
RED_AREA = 0.12                 # the most of the wall that may be saturated red at once
COUNT_LAG = 0.3                 # a red counts this long after it ends: its last captures are still on their way
COLUMN_SLACK = 1                # px a figure's column may jitter without moving it (the lobby's, C46)
CAMERA_FPS = 10
WINDOW_SECONDS = 1.0            # `active`: travel over MOVE_TRAVEL inside this
BORDER_ROWS = 60                # the border's rows 0 and 59; rows 60 to 63 stay free
WORD_TOP = 44                   # the word's rows 44 to 57 (2x glyphs are 14 rows)
SCORE_SCALE = 2
GREEN = (0, 200, 0)
RED = (255, 0, 0)
HINT_COLOR = (255, 120, 0)
SCORE_COLOR = (255, 255, 255)
BLACK = (0, 0, 0)
READY_LINES = (("DANCE ON GREEN", GREEN), ("FREEZE ON RED", RED))
HINT_TEXT = "MOVE!"

ICON = icon_from_rows([
    "................",
    "..##....######..",
    "..##....######..",
    "........######..",
    "..##....######..",
    "######..######..",
    "..##....######..",
    "..##.......##...",
    "..##.......##...",
    "..##.......##...",
    ".##.##.....##...",
    ".##.##.....##...",
    ".##.##.....##...",
    ".#...#.....##...",
    ".#...#.....##...",
    "................",
])


def _round(v: float) -> int:
    return math.floor(v + 0.5)


class Span:
    """The min and max of five channels since an anchor: each wrist's reach u and v, and the zone_x."""

    def __init__(self):
        self.lo = [math.inf] * 5
        self.hi = [-math.inf] * 5

    def add(self, sample: tuple) -> None:
        for k, v in enumerate(sample):
            if v is not None:
                self.lo[k], self.hi[k] = min(self.lo[k], v), max(self.hi[k], v)

    @property
    def travel(self) -> float:
        """The largest span of a wrist channel, and the zone_x span over STEP_SCALE (0 for a channel never seen)."""
        wrists = max((hi - lo for lo, hi in zip(self.lo[:4], self.hi[:4]) if hi >= lo), default=0.0)
        zone = self.hi[4] - self.lo[4] if self.hi[4] >= self.lo[4] else 0.0
        return max(wrists, zone / STEP_SCALE)


def sample_of(body: Body) -> tuple:
    """(left u, left v, right u, right v, zone_x): a wrist under MIN_CONF gives None for both of its channels."""
    out: list = []
    for wrist in (body.left_wrist, body.right_wrist):
        out.extend(body.reach(wrist) if wrist.conf >= MIN_CONF else (None, None))
    return (*out, body.zone_x)


class Seat:
    """One player's side: who, the held skeleton and where it is drawn, the travel, the count and the fall."""

    def __init__(self, grace: float):
        self.hold = KeypointHold(grace)
        self.id: int | None = None
        self.joined = self.out = self.left = False
        self.score = 0
        self.body: Body | None = None               # the held skeleton last seen
        self.rect_x: int | None = None              # its column with backlash
        self.rect_id: int | None = None
        self.seen_at = -math.inf
        self.cap = -math.inf                        # capture time of the last sample taken
        self.seg: int | None = None                 # the light segment the span belongs to
        self.span = Span()
        self.travel: dict[int, float] = {}          # segment: its travel so far
        self.window: deque = deque()                # (capture time, sample) of the last WINDOW_SECONDS
        self.fall: tuple | None = None              # (body, rect, t out, direction): the topple
        self.head: tuple[float, float] | None = None


class Freeze(Game):
    info = GameInfo(name="freeze", title="FREEZE", verb="FREEZE", icon=ICON, needs=frozenset({"pose"}),
                    layouts=frozenset({"128x64"}), players=2, exit_gesture=False, kind="score")
    PHASES = ("ready", "play", "over")
    CAPTION_KEYS = ("phase", "light", "score")
    SCENARIOS = MappingProxyType({})     # filled below, once the scripts exist

    def reset(self, size, rng: random.Random, fx) -> None:
        self.w, self.h = size
        self.rng, self.fx = rng, fx
        self.grace = capture_grace(CAMERA_FPS)
        self.seats = [Seat(self.grace), Seat(self.grace)]
        self.plan: list[tuple[str, float]] = []
        for _ in range(REDS):
            self.plan.append(("green", rng.uniform(*GREEN_SECONDS)))
            self.plan.append(("red", rng.uniform(*RED_SECONDS)))
        self.sched: list[tuple[str, float, float]] = []       # (light, start, end) once play begins
        self.cur = -1
        self.counted = 0
        self.duo = False
        self._t0: float | None = None
        self.t = 0.0
        self.phase, self._phase_start = "ready", 0.0
        self.phase_t = 0.0
        self._idle = 0.0
        self._active = False
        self._hint = False

    # ----- the tick -----

    def update(self, sensed: Sensed, dt: float) -> None:
        if self._t0 is None:
            self._t0 = sensed.t
        self.t = sensed.t - self._t0
        self.phase_t = self.t - self._phase_start
        for i, body in enumerate(self._bodies(sensed)):
            self._observe(i, body, sensed.camera_t - self._t0)
        for i, seat in enumerate(self.seats):
            if seat.joined and not seat.out and self.t - seat.seen_at > self.grace + EPSILON:
                self._out(i, topple=False)               # missing past the grace: gone without a topple
        if self.phase == "ready" and self.phase_t >= READY_SECONDS - 1e-9:
            self._begin_play()
        if self.phase == "play":
            self._advance()
        self._update_hint(dt)

    def _bodies(self, sensed: Sensed) -> list[Body | None]:
        """Each seat's body this tick: the one with the seat's id; an unbound seat takes the next unclaimed body."""
        free = {b.id: b for b in (sensed.player, sensed.player2) if b is not None}
        bodies: list[Body | None] = [None, None]
        for i, seat in enumerate(self.seats):
            if seat.id is not None:
                bodies[i] = free.pop(seat.id, None)
        for i, seat in enumerate(self.seats):
            if seat.id is None and free:
                body = free.pop(next(iter(free)))
                seat.id, bodies[i] = body.id, body
        return bodies

    def _observe(self, i: int, body: Body | None, cam: float) -> None:
        seat = self.seats[i]
        if body is None or seat.out:
            return
        seat.seen_at = self.t
        held = seat.hold.update(body, self.t)
        seat.body = held
        x = figure_rect(held, (self.w, FIGURE_H))[0]
        if seat.rect_x is not None and seat.rect_id == held.id:        # the same person: x with backlash
            x = min(max(seat.rect_x, x - COLUMN_SLACK), x + COLUMN_SLACK)
        seat.rect_x, seat.rect_id = x, held.id
        seat.head = self._head(held, self._rect(seat))
        if cam > seat.cap + 1e-9:                                       # a new capture
            seat.cap = cam
            self._sample(i, cam, sample_of(held))

    def _sample(self, i: int, cam: float, sample: tuple) -> None:
        seat = self.seats[i]
        seat.window.append((cam, sample))
        while seat.window and seat.window[0][0] < cam - WINDOW_SECONDS - 1e-9:
            seat.window.popleft()
        idx = self._segment_at(cam)
        if idx != seat.seg:
            seat.seg, seat.span = idx, Span()
        if idx is None:
            return
        light, start, _ = self.sched[idx]
        if light == "red" and cam < start + GRACE - 1e-9:
            return                                                       # inside the grace: not judged
        seat.span.add(sample)
        seat.travel[idx] = seat.span.travel
        if light == "red" and seat.joined and seat.span.travel > MOVE_TRAVEL:
            self._out(i)

    def _segment_at(self, cam: float) -> int | None:
        for k, (_, start, end) in enumerate(self.sched):
            if start - 1e-9 <= cam < end - 1e-9:
                return k
        return None

    def _begin_play(self) -> None:
        self.phase, self._phase_start, self.phase_t = "play", self.t, 0.0
        at = self.t
        for light, seconds in self.plan:
            self.sched.append((light, at, at + seconds))
            at += seconds

    def _advance(self) -> None:
        while self.cur + 1 < len(self.sched) and self.t >= self.sched[self.cur + 1][1] - 1e-9:
            self.cur += 1
            if self.sched[self.cur][0] == "green":                       # a body seen joins at a green
                for seat in self.seats:
                    if not seat.joined and not seat.out and seat.seen_at >= self.t - 1e-9:
                        seat.joined = True
                self.duo = self.duo or all(seat.joined for seat in self.seats)
        while self.counted < REDS and self.t >= self.sched[2 * self.counted + 1][2] + COUNT_LAG - 1e-9:
            self._count(2 * self.counted + 1)
            self.counted += 1
        if self.counted == REDS or self._decided():
            self._finish()

    def _count(self, red: int) -> None:
        for seat in self.seats:
            if seat.joined and not seat.out and seat.travel.get(red - 1, 0.0) >= DANCE_TRAVEL - 1e-9:
                seat.score += 1

    def _standing(self) -> int:
        return sum(seat.joined and not seat.out for seat in self.seats)

    def _decided(self) -> bool:
        """Someone joined and no one is left to beat: nobody in solo, one in a duo."""
        return any(seat.joined for seat in self.seats) and self._standing() <= (1 if self.duo else 0)

    def _out(self, i: int, topple: bool = True) -> None:
        seat = self.seats[i]
        seat.out, seat.left = True, not topple
        if topple and seat.body is not None:
            rect = self._rect(seat)
            feet = self._feet(seat.body, rect)
            seat.fall = (seat.body, rect, self.t, 1 if feet[0] < self.w / 2 else -1)
            self.fx.echo(i + 1, "hit")

    def _finish(self) -> None:
        if self.phase == "over":
            return
        if (self.duo and self.cur >= 0 and self.sched[self.cur][0] == "red" and self.counted < REDS
                and self.counted == (self.cur - 1) // 2):
            self._count(self.cur)                                       # the survivor stood through this red
            self.counted += 1
        self.phase, self._phase_start, self.phase_t = "over", self.t, 0.0
        a = self.seats[0]
        if not self.duo and a.joined and a.score > 0:
            self.scores.record(a.score)                                  # once, and only for a red that counted
        if any(seat.joined and not seat.out and seat.score > 0 for seat in self.seats):
            self.fx.celebrate(GREEN)

    def _update_hint(self, dt: float) -> None:
        self._active = any(self._moving(seat) for seat in self.seats)
        self._idle = 0.0 if self._active else self._idle + dt
        near = any(self.t - seat.seen_at <= self.grace + EPSILON for seat in self.seats)
        self._hint = (near and not self._active and self._idle >= HINT_IDLE_SECONDS - 1e-9
                      and self.phase in ("ready", "play") and self.light != "red")

    def _moving(self, seat: Seat) -> bool:
        if seat.out or not seat.window or self.t - seat.seen_at > self.grace + EPSILON:
            return False
        if self.t - seat.window[-1][0] > WINDOW_SECONDS + 0.4:           # the captures stopped coming
            return False
        span = Span()
        for _, sample in seat.window:
            span.add(sample)
        return span.travel > MOVE_TRAVEL

    def done(self) -> bool:
        return self.phase == "over" and self.phase_t >= OVER_SECONDS - 1e-9

    # ----- what the light is -----

    @property
    def light(self) -> str:
        if self.phase != "play" or self.cur < 0:
            return "none"
        light, _, end = self.sched[self.cur]
        return "none" if self.t >= end - 1e-9 and self.cur == len(self.sched) - 1 else light

    # ----- drawing -----

    def _rect(self, seat: Seat) -> tuple[int, int, int, int]:
        return (seat.rect_x, 0, FIGURE_H, FIGURE_H)

    def _head(self, body: Body, rect) -> tuple[float, float]:
        f = to_wall(body, rect)
        if body.nose.conf >= MIN_CONF:
            x, y = f(body.nose.x, body.nose.y)
        else:
            x0, y0, x1, _ = body.box
            x, y = f((x0 + x1) / 2, y0)
        return (min(max(x, 0), self.w - 0.01), min(max(y, 0), self.h - 0.01))

    def _feet(self, body: Body, rect) -> tuple[float, float]:
        """Where the figure stands, in wall pixels: its confident ankles' middle, else its lowest keypoint."""
        f = to_wall(body, rect)
        pts = [f(body.keypoints[k].x, body.keypoints[k].y) for k in (LEFT_ANKLE, RIGHT_ANKLE)
               if body.keypoints[k].conf >= MIN_CONF]
        if pts:
            return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
        seen = [f(k.x, k.y) for k in body.keypoints if k.conf >= MIN_CONF]
        return max(seen, key=lambda p: p[1]) if seen else (rect[0] + rect[2] / 2, rect[1] + rect[3] - 1)

    def draw(self, canvas: Canvas) -> None:
        for i, seat in enumerate(self.seats):                          # seat b is drawn over seat a
            self._draw_seat(canvas, i, seat)
        light = self.light
        if light != "none":
            color, word = (GREEN, "DANCE") if light == "green" else (RED, "FREEZE")
            self._border(canvas, color)
            self._word(canvas, word, color)
        if self.phase == "ready":
            top = 24
            for k, (line, color) in enumerate(READY_LINES):
                width = canvas.text_width(line) - 1
                x = (self.w - width) // 2
                canvas.fill_rect(x - 1, top + 9 * k - 1, width + 2, 9, BLACK)
                canvas.text(x, top + 9 * k, line, color)
        elif self.phase == "over":
            result = self._result()
            if result is not None:
                self._word(canvas, *result)
        if self._hint:
            width = canvas.text_width(HINT_TEXT) - 1
            x = (self.w - width) // 2
            canvas.fill_rect(x - 1, 12, width + 2, 9, BLACK)
            canvas.text(x, 13, HINT_TEXT, HINT_COLOR)
        self._scores(canvas)

    def _result(self) -> tuple[str, tuple] | None:
        a = self.seats[0]
        if self.duo:
            ins = [i for i, seat in enumerate(self.seats) if seat.joined and not seat.out]
            return (f"P{ins[0] + 1} WIN", GREEN) if len(ins) == 1 else ("DRAW", RED)
        if a.out:
            return ("OUT", RED)
        if a.joined and a.score >= WIN_SCORE:
            return ("SAFE!", GREEN)
        return None

    def _word(self, canvas: Canvas, text: str, color) -> None:
        width = canvas.text_width(text, SCORE_SCALE) - SCORE_SCALE
        x = (self.w - width) // 2
        canvas.fill_rect(x - 1, WORD_TOP - 1, width + 2, 2 * 7 + 2, BLACK)
        canvas.text(x, WORD_TOP, text, color, SCORE_SCALE)

    def _border(self, canvas: Canvas, color) -> None:
        canvas.fill_rect(0, 0, self.w, 1, color)
        canvas.fill_rect(0, BORDER_ROWS - 1, self.w, 1, color)
        canvas.fill_rect(0, 0, 1, BORDER_ROWS, color)
        canvas.fill_rect(self.w - 1, 0, 1, BORDER_ROWS, color)

    def _scores(self, canvas: Canvas) -> None:
        text = str(self.seats[0].score)
        x0 = self.w - canvas.text_width(text, SCORE_SCALE)
        canvas.fill_rect(x0 - 1, 0, self.w - x0 + 1, 7 * SCORE_SCALE + 2, BLACK)
        canvas.text(x0, 1, text, SCORE_COLOR, SCORE_SCALE)
        if self.duo:
            other = str(self.seats[1].score)
            width = canvas.text_width(other, SCORE_SCALE)
            canvas.fill_rect(0, 0, width + 1, 7 * SCORE_SCALE + 2, BLACK)
            canvas.text(0, 1, other, SCORE_COLOR, SCORE_SCALE)

    def _shown(self, seat: Seat) -> bool:
        return seat.body is not None and not seat.out and self.t - seat.seen_at <= self.grace + EPSILON

    def _draw_seat(self, canvas: Canvas, i: int, seat: Seat) -> None:
        color = PLAYER_COLORS[i]
        if seat.fall is not None:
            self._draw_fall(canvas, seat, color)
        elif self._shown(seat):
            draw_figure(canvas, seat.body, self._rect(seat), color)

    def _fall_level(self, seat: Seat) -> float:
        """1 while upright, falling to 0 over twice TOPPLE_SECONDS from the out."""
        return max(0.0, 1.0 - (self.t - seat.fall[2]) / (2 * TOPPLE_SECONDS))

    def _draw_fall(self, canvas: Canvas, seat: Seat, color) -> None:
        """The held skeleton's segments rotated 90 degrees about its feet over TOPPLE_SECONDS, fading (draw_figure
        cannot rotate). Lifted as far as its lowest lit row would pass row BORDER_ROWS - 1: it lies down above the
        runner's rows 60 to 63, never on them."""
        body, rect, t_out, side = seat.fall
        level = self._fall_level(seat)
        shade = tuple(_round(c * level) for c in color)
        if not any(shade):
            return
        angle = side * (math.pi / 2) * min(1.0, (self.t - t_out) / TOPPLE_SECONDS)
        fx, fy = self._feet(body, rect)
        c, s = math.cos(angle), math.sin(angle)
        f = to_wall(body, rect)
        pts = []
        for k in body.keypoints:
            x, y = f(k.x, k.y)
            dx, dy = x - fx, y - fy
            pts.append((_round(fx + dx * c - dy * s), _round(fy + dx * s + dy * c)))
        kps = body.keypoints
        segments = [(a, b) for a, b in SKELETON if kps[a].conf >= MIN_CONF and kps[b].conf >= MIN_CONF]
        radius = max(1, _round(HEAD * rect[3]))
        head = kps[NOSE].conf >= MIN_CONF
        below = STROKE - 1 - (STROKE - 1) // 2                          # a thick line's rows under its points
        lows = [pts[i][1] + below for ab in segments for i in ab] + ([pts[NOSE][1] + radius] if head else [])
        lift = max(0, max(lows, default=0) - (BORDER_ROWS - 1))
        pts = [(x, y - lift) for x, y in pts]
        for a, b in segments:
            self._thick_line(canvas, pts[a], pts[b], shade)
        if head:
            canvas.fill_circle(*pts[NOSE], radius, shade)

    @staticmethod
    def _thick_line(canvas: Canvas, a, b, color) -> None:
        """A line STROKE px thick across its run: copies offset along the minor axis, as the figure's."""
        steep = abs(b[1] - a[1]) > abs(b[0] - a[0])
        first = -((STROKE - 1) // 2)
        for k in range(first, first + STROKE):
            dx, dy = (k, 0) if steep else (0, k)
            canvas.line(a[0] + dx, a[1] + dy, b[0] + dx, b[1] + dy, color)

    # ----- the debug state -----

    def _xy(self, seat: Seat):
        if seat.fall is not None:
            return seat.head if self._fall_level(seat) > 0.0 else None
        return seat.head if self._shown(seat) else None

    def _danced(self) -> bool:
        if self.cur < 0:
            return False
        green = self.cur if self.sched[self.cur][0] == "green" else self.cur - 1
        return self.seats[0].travel.get(green, 0.0) >= DANCE_TRAVEL - 1e-9

    def debug_state(self) -> dict:
        a, b = self.seats
        in_grace = self.light == "red" and self.t < self.sched[self.cur][1] + GRACE - 1e-9
        return {"phase": self.phase, "light": self.light, "score": a.score, "other": b.score, "out": bool(a.out),
                "out2": bool(b.out), "danced": bool(self._danced()), "reds_left": REDS - self.counted,
                "in_grace": bool(in_grace), "active": bool(self._active), "hint": bool(self._hint),
                "player_xy": self._xy(a), "player2_xy": self._xy(b)}


# ----- scripts -----

CANONICAL_SECONDS = 60.0
RAISE_AT = 4.5
DANCE_SECONDS, HOLD_SECONDS = 2.0, 3.0      # the canonical cannot read the lights: it dances and holds in turn


def cam_x(zone_x: float) -> float:
    """The camera x a Person stands at to be at zone_x of the mat (the default calibration's zone)."""
    from arcade.calibration import Calibration

    x0, _, x1, _ = Calibration().zone
    return x0 + zone_x * (x1 - x0)


def wave(person: Person, start: float, end: float, half: float = 0.45) -> None:
    """Both arms up and down (half seconds each way, slow enough that a pixel under an arm keeps the flash rule)
    from start to end."""
    t = start
    while t < end - 1e-9:
        for hand in ("left", "right"):
            person.wrist(hand, 0.2, 0.8, half, at=t)
            person.wrist(hand, 0.8, 0.2, half, at=t + half)
        t += 2 * half


def canonical():
    """The wall empty for 2 s, one player walks up, raises a hand at 4.5 s (the game launches), sweeps the whole mat
    slowly (the figure follows: a quick sweep of a figure would trip the flash governor) while the lights are still
    green or not yet on, then waves its arms 2 s and holds 3 s in turn (steps trip the flash governor: a figure sliding sideways is
    many strokes crossing every pixel): some reds catch it moving."""
    person = Person(cam_x(0.5), id=1).arrive(2.0).raise_hand(RAISE_AT, 0.5)
    person.walk(cam_x(0.03), 2.0, at=5.0)
    person.walk(cam_x(0.97), 4.0, at=7.0)                       # at the far wall by 11.0, the first red's grace
    t = 13.0
    while t + DANCE_SECONDS < CANONICAL_SECONDS:
        wave(person, t, t + DANCE_SECONDS)
        t += DANCE_SECONDS + HOLD_SECONDS
    return scene(persons=[person], ticks=round(CANONICAL_SECONDS / TICK))


def idle_body(body_id: int = 1, seconds: float = 60.0):
    """One body standing, hands down, for 60 s (body_id and seconds let tests vary the noise and the length)."""
    return scene(persons=[Person(cam_x(0.3), id=body_id)], ticks=round(seconds / TICK))


def nobody():
    return scene(ticks=900)


def duo():
    """Two bodies from the start: the nearer (player) freezes, standing still; the other keeps dancing, so the first
    red puts it out and the one who froze is the last one standing; 55 s."""
    a = Person(cam_x(0.3), height=0.62, id=1)
    b = Person(cam_x(0.7), id=2)
    wave(b, 0.0, 54.0)
    return scene(persons=[a, b], ticks=round(55 / TICK))


Freeze.SCENARIOS = MappingProxyType({"canonical": canonical, "idle_body": idle_body, "nobody": nobody, "duo": duo})
GAME = Freeze
