"""Quick Draw (spec 8, game 4): hands low; WAIT for a random 2 to 5 s (Q71); then DRAW!; the first hand up wins the
round, a hand up during WAIT loses it (TOO SOON). First to WIN_ROUNDS rounds. Solo plays a CPU gunslinger (green)
in seat b; a second body joins at the next round's ready and takes seat b with its rounds (Pong's seat rule).

Two seats, a (left, player 1's) and b (right). A human seat reads its body through a Cursor then a Glide (arcade/
input.py): the hand's height in the reach box, v from V_TOP to V_BOTTOM, is the bar's y from BAR_TOP to BAR_BOTTOM
(scaled to the wall's height), and the DRAW_V line is where the bar draws. A bar draws only after it sat ARM_PX below
the line during the round's play, so a still hand never draws (C41, C42). Solo, a best is stored at the match's end
when player 1 won a round by a draw (Q72: rounds won); a game that ever had a human in seat b stores none (Q23).

Seat a is player 1's and never the CPU's: while player 1 is gone it is empty (its bar down, no draw, no round), so
their rounds and best are only the ones they won (Q72); their leaving is the runner's to end.

debug_state: phase, signal ("wait" or "draw" in play, else None), round, score (player 1's rounds), left, right (the
seats' rounds), cpu ("right" or None: seat a is never the CPU), humans, active, hint (the hand-up hint is wanted),
hand_xy (player 1's bar centre), left_xy, right_xy (the bars), wait_left (s until DRAW while waiting, to 0.1, else
None) and react (the last winning draw's time, s, or None)."""
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

WIN_ROUNDS = 3
WAIT_SECONDS = (2.0, 5.0)   # Q71: the spec says 2 to 6
READY_SECONDS = 1.0         # least
DRAW_TIMEOUT = 1.5          # s after DRAW with nobody drawn: the CPU's round, a void round with no CPU
CPU_DRAW = (0.25, 0.80)    # s after DRAW the CPU draws (rng.uniform per round and seat)
RESULT_SECONDS = 1.5
OVER_SECONDS = 2.5
ARM_PX = 6                  # a bar draws only after it sat this far below the line in this round's play
ACTIVE_PX = 3               # a bar this far from its anchor is input
HINT_IDLE_SECONDS = 2.0
HINT_FADE = 0.3             # s in and out: never a blink
CAMERA_FPS = 10             # capture_grace(10): what a human may be missing before leaving the seat
V_TOP, V_BOTTOM = 0.25, 0.75        # the reach box's v that is the bar's top and bottom
DRAW_V = 0.45                       # the line, in the same v: a hand at shoulder height (0.51) is below it
BAR_TOP, BAR_BOTTOM = 16, 56        # px at 64 rows (scaled with the height)
LINE_Y = BAR_TOP + (DRAW_V - V_TOP) / (V_BOTTOM - V_TOP) * (BAR_BOTTOM - BAR_TOP)     # 32
BAR_W, BAR_H = 12, 3
TICK_W, TICK_GAP = 4, 1     # the line: a 4 px tick either side of each bar, 2 px tall
CPU_BAR_SPEED = 320.0       # px/s at 64 rows: the CPU's bar rises in 0.13 s
SCORE_SCALE = 2
CPU_COLOR = (0, 200, 0)
LINE_COLOR = (255, 120, 0)
DRAW_COLOR = (255, 255, 255)
SOON_COLOR = (255, 0, 0)
HINT_LINES = ("HAND UP ON DRAW!",)
HINT_TOP = 44               # px at 64 rows: under the bars' resting place, over the runner's marker row
GLYPH_H = 7

ICON = icon_from_rows([
    "................",
    "....##.##.##....",
    "....##.##.##....",
    "....##.##.##....",
    "....##.##.##....",
    "....##########..",
    "....##########..",
    "....##########..",
    "....##########..",
    ".....########...",
    "................",
    "................",
    "################",
    "################",
    "................",
    "................",
])


class Seat:
    """One side's player: a human (ctrl is a body id) or, with ctrl None, the CPU in seat b and nobody in seat a
    (player 1's: never the CPU's), with the rounds it has won."""

    def __init__(self, index: int, grace: float, y: float):
        self.index, self.grace = index, grace
        self.color = PLAYER_COLORS[index]
        self.ctrl: int | None = None
        self.rounds = 0
        self.seen = -math.inf       # when the human's body was last seen
        self.cursor = Cursor(grace=grace)
        self.glide = Glide(grace=grace)
        self.y = self.anchor = y    # the bar's centre; the y at the last tick counted as input
        self.idle = 0.0             # s since the bar last moved ACTIVE_PX
        self.armed = False          # sat ARM_PX below the line in this round's play
        self.cpu_up = False         # the CPU drew this round: its bar is up

    def take(self, body, t: float) -> None:
        self.ctrl, self.seen = body.id, t
        self.cursor, self.glide = Cursor(grace=self.grace), Glide(grace=self.grace)
        self.color = PLAYER_COLORS[self.index]

    def release(self) -> None:
        self.ctrl = None


class Quickdraw(Game):
    info = GameInfo(name="quickdraw", title="DRAW!", verb="DRAW", icon=ICON, needs=frozenset({"pose"}),
                    layouts=frozenset({"128x64"}), players=2, kind="score")
    PHASES = ("ready", "play", "result", "over")
    CAPTION_KEYS = ("phase", "signal", "left", "right")
    SCENARIOS = MappingProxyType({})     # filled below, once the scripts exist

    def reset(self, size, rng: random.Random, fx) -> None:
        self.w, self.h = size
        self.rng, self.fx = rng, fx
        k = self.h / 64
        self.bar_top, self.bar_bottom, self.line_y = BAR_TOP * k, BAR_BOTTOM * k, LINE_Y * k
        self.grace = capture_grace(CAMERA_FPS)
        self.t = 0.0
        self.phase, self.phase_t = "ready", 0.0
        self.seats = [Seat(0, self.grace, self.bar_bottom), Seat(1, self.grace, self.bar_bottom)]
        self.round = 1
        self._wait = WAIT_SECONDS[0]
        self._cpu = [CPU_DRAW[1], CPU_DRAW[1]]
        self._signal = "wait"
        self._flashed = False
        self._assigned = False
        self._duel = False              # a human ever sat in seat b: no best (Q23)
        self._drew = False              # player 1 won a round by a draw: a best needs it (C41)
        self._winner: int | None = None
        self._soon: int | None = None   # the seat that drew too soon in the last round
        self._react: float | None = None
        self._active = False
        self._hint_level = 0.0

    # ----- seats -----

    def _bodies(self, sensed: Sensed) -> dict:
        found = {b.id: b for b in sensed.bodies}
        for b in (sensed.player, sensed.player2):
            if b is not None:
                found[b.id] = b
        return found

    def _humans(self) -> int:
        return sum(seat.ctrl is not None for seat in self.seats)

    @staticmethod
    def _is_cpu(seat: Seat) -> bool:
        """Only seat b is ever the CPU; seat a without a human is empty: it draws nothing and wins nothing."""
        return seat.ctrl is None and seat.index == 1

    def _color(self, seat: Seat):
        return CPU_COLOR if self._is_cpu(seat) else seat.color

    def _release_stale(self) -> None:
        for seat in self.seats:
            if seat.ctrl is not None and self.t - seat.seen > self.grace:
                seat.release()

    def _assign(self, sensed: Sensed) -> None:
        """Settle the seats for a round: a human missing longer than the grace leaves its seat (seat b to the CPU,
        seat a empty, rounds kept), and the bodies not seated take the free seats, seat a first."""
        self._release_stale()
        bound = {seat.ctrl for seat in self.seats}
        candidates = [b for b in (sensed.player, sensed.player2) if b is not None and b.id not in bound]
        for seat in self.seats:
            if seat.ctrl is None and candidates:
                seat.take(candidates.pop(0), self.t)
                self._duel = self._duel or seat.index == 1

    # ----- the tick -----

    def update(self, sensed: Sensed, dt: float) -> None:
        self.t += dt
        self.phase_t += dt
        self._active = False
        found = self._bodies(sensed)
        for seat in self.seats:
            if seat.ctrl in found:
                seat.seen = self.t
        if not self._assigned:
            self._assign(sensed)
            self._assigned = True
        self._move_bars(sensed, found, dt)
        if self.phase == "ready":
            self._release_stale()
            if self.phase_t >= READY_SECONDS - 1e-9 and self._hands_down():
                self._to_play()
        elif self.phase == "play":
            self._play()
        elif self.phase == "result":
            if self.phase_t >= RESULT_SECONDS - 1e-9:
                if any(seat.rounds >= WIN_ROUNDS for seat in self.seats):
                    self._finish()
                else:
                    self._to_ready(sensed)
        self._update_hint(dt)

    def _hands_down(self) -> bool:
        return all(seat.y > self.line_y for seat in self.seats if seat.ctrl is not None)

    def _bar_y(self, v: float) -> float:
        share = min(1.0, max(0.0, (v - V_TOP) / (V_BOTTOM - V_TOP)))
        return self.bar_top + share * (self.bar_bottom - self.bar_top)

    def _move_bars(self, sensed: Sensed, found: dict, dt: float) -> None:
        for seat in self.seats:
            if seat.ctrl is None and not self._is_cpu(seat):
                seat.y = self.bar_bottom                # empty seat a: down, as a seat in dropout; never input
                seat.anchor, seat.idle = seat.y, 0.0
                continue
            if seat.ctrl is None:
                target = self.bar_top if seat.cpu_up else self.bar_bottom
                step = CPU_BAR_SPEED * self.h / 64 * dt
                seat.y += max(-step, min(step, target - seat.y))
                seat.anchor, seat.idle = seat.y, 0.0
                continue
            cursor = seat.cursor.update(found.get(seat.ctrl), sensed.t)
            v = seat.glide.update(None if cursor is None else cursor[1], sensed.t, sensed.camera_t)
            seat.y = self.bar_bottom if v is None else self._bar_y(v)      # a hand not seen is a hand down
            if abs(seat.y - seat.anchor) >= ACTIVE_PX - 1e-9:
                self._active, seat.anchor, seat.idle = True, seat.y, 0.0
            else:
                seat.idle += dt

    def _set(self, phase: str) -> None:
        self.phase, self.phase_t = phase, 0.0

    def _to_ready(self, sensed: Sensed) -> None:
        self.round += 1
        self._soon = None
        for seat in self.seats:
            seat.cpu_up = False
        self._assign(sensed)
        self._set("ready")

    def _to_play(self) -> None:
        self._wait = self.rng.uniform(*WAIT_SECONDS)
        self._cpu = [self.rng.uniform(*CPU_DRAW) for _ in self.seats]
        self._signal = "wait"
        self._flashed = False
        for seat in self.seats:
            seat.armed = False
        self._set("play")

    def _play(self) -> None:
        crossed = []
        for seat in self.seats:
            if seat.ctrl is None:
                continue
            seat.armed = seat.armed or seat.y >= self.line_y + ARM_PX - 1e-9
            if seat.armed and seat.y <= self.line_y + 1e-9:
                crossed.append(seat)
        if self._signal == "wait":
            if crossed:
                self._too_soon(crossed)
            elif self.phase_t >= self._wait - 1e-9:
                self._signal = "draw"
                self._flashed = self.fx.flash(DRAW_COLOR, 0.15)
            return
        since = self.phase_t - self._wait
        if crossed:
            winner = min(crossed, key=lambda s: (s.y, s.index))       # a tie on the tick goes to the higher hand
            self._won(winner.index, since, "draw")
            return
        due = [seat for seat in self.seats if self._is_cpu(seat) and since >= self._cpu[seat.index] - 1e-9]
        if due:
            winner = min(due, key=lambda s: (self._cpu[s.index], s.index))
            self._won(winner.index, self._cpu[winner.index], "draw")
        elif since >= DRAW_TIMEOUT - 1e-9:
            self._void()

    def _too_soon(self, soon: list) -> None:
        other = self.seats[1 - soon[0].index]
        if len(soon) == len(self.seats) or self._humans() == 0 or (other.ctrl is None and not self._is_cpu(other)):
            self._void()                        # nobody in the other seat to give the round to: an empty seat a
            return
        self._soon = soon[0].index
        self._won(other.index, None, "soon")

    def _void(self) -> None:
        self._to_ready_void()

    def _to_ready_void(self) -> None:
        self.round += 1
        self._soon = None
        for seat in self.seats:
            seat.cpu_up = False
        self._set("ready")

    def _won(self, index: int, react: float | None, how: str) -> None:
        seat = self.seats[index]
        seat.rounds += 1
        self._winner, self._react = index, None if react is None else round(react, 2)
        if index == 0 and seat.ctrl is not None and how == "draw":
            self._drew = True
        if seat.ctrl is None and how == "draw":
            seat.cpu_up = True
        cx = self._bar_x(index)
        color = self._color(seat)
        self.fx.burst(cx, seat.y, color)
        if seat.ctrl is not None:
            self.fx.echo(index + 1, "ok")
        self._set("result")

    def _finish(self) -> None:
        a, b = self.seats
        winner = a if a.rounds >= b.rounds else b
        if self._humans() == 1 and not self._duel and winner is a and a.ctrl is not None:
            self.fx.celebrate(a.color)
        if not self._duel and self._drew:
            self.scores.record(a.rounds)
        self._set("over")

    def done(self) -> bool:
        return self.phase == "over" and self.phase_t >= OVER_SECONDS - 1e-9

    # ----- the hint -----

    def _update_hint(self, dt: float) -> None:
        target = 1.0 if self._shows_hint() else 0.0
        step = dt / HINT_FADE
        self._hint_level = min(target, self._hint_level + step) if target > self._hint_level \
            else max(target, self._hint_level - step)

    def _shows_hint(self) -> bool:
        return (self.phase in ("ready", "play")
                and any(seat.ctrl is not None and seat.idle >= HINT_IDLE_SECONDS - 1e-9 for seat in self.seats))

    # ----- drawing -----

    def _bar_x(self, index: int) -> int:
        return self.w // 8 if index == 0 else self.w - self.w // 8

    def _center(self, canvas: Canvas, text: str, y: float, color, scale: int = 1) -> None:
        width = canvas.text_width(text, scale) - scale        # the last glyph's cell gap is not drawn
        if width <= self.w:
            canvas.text((self.w - width) // 2, round(y), text, color, scale)

    def draw(self, canvas: Canvas) -> None:
        k = self.h / 64
        if self._hint_level > 0.0 and self.phase != "result":       # never over the time under DRAW!
            color = tuple(round(c * self._hint_level) for c in LINE_COLOR)
            for n, line in enumerate(HINT_LINES):
                self._center(canvas, line, HINT_TOP * k + n * (GLYPH_H + 2), color)
        for seat in self.seats:
            cx = self._bar_x(seat.index)
            text = str(seat.rounds)
            width = canvas.text_width(text, SCORE_SCALE)
            canvas.text((self.w // 4 if seat.index == 0 else 3 * self.w // 4) - width // 2, 1, text,
                        self._color(seat), SCORE_SCALE)
            canvas.fill_rect(cx - BAR_W // 2 - TICK_GAP - TICK_W, self.line_y - 1, TICK_W, 2, LINE_COLOR)
            canvas.fill_rect(cx + BAR_W // 2 + TICK_GAP, self.line_y - 1, TICK_W, 2, LINE_COLOR)
            canvas.fill_rect(cx - BAR_W / 2, seat.y - BAR_H / 2, BAR_W, BAR_H,
                             self._color(seat))
        top = self.line_y - CELL_H
        if self.phase in ("play", "result"):
            if self._signal == "draw":
                self._center(canvas, "DRAW!", top, DRAW_COLOR, 2)
            else:
                self._center(canvas, "WAIT", top, LINE_COLOR, 2)
            if self.phase == "result" and self._react is not None:
                self._center(canvas, f"{self._react:.2f}", self.line_y + 9 * k, DRAW_COLOR)
            if self.phase == "result" and self._soon is not None:
                half = self.w // 4 if self._soon == 0 else 3 * self.w // 4
                width = canvas.text_width("TOO SOON") - 1
                canvas.text(half - width // 2, round(self.line_y + 9 * k), "TOO SOON", SOON_COLOR)
        elif self.phase == "ready" and not self._hands_down():
            self._center(canvas, "HANDS DOWN", self.line_y - GLYPH_H // 2, LINE_COLOR)

    def debug_state(self) -> dict:
        a, b = self.seats
        cap = lambda v, top: min(max(0.0, v), top - 0.01)
        bar = lambda seat: (float(self._bar_x(seat.index)), round(cap(seat.y, self.h), 2))
        waiting = self.phase == "play" and self._signal == "wait"
        return {"phase": self.phase, "signal": self._signal if self.phase == "play" else None,
                "round": self.round, "score": a.rounds, "left": a.rounds, "right": b.rounds,
                "cpu": "right" if self._is_cpu(b) else None, "humans": self._humans(), "active": bool(self._active),
                "hint": bool(self._shows_hint()), "hand_xy": bar(a), "left_xy": bar(a), "right_xy": bar(b),
                "wait_left": round(max(0.0, self._wait - self.phase_t), 1) if waiting else None,
                "react": self._react}


HEIGHT_V = 1.0      # the wrist at hip height: a hand down
UP_V = 0.1          # a hand drawn: above the reach box's V_TOP, the bar at its top


def _hand(person: Person, at: float, hold: float = 1.0) -> Person:
    """The wrist from hip height to the top in 0.15 s at `at`, held for `hold` s, then down."""
    return person.wrist("right", HEIGHT_V, UP_V, 0.15, at=at).wrist("right", UP_V, UP_V, hold, at=at + 0.15)


def canonical():
    """The wall empty for 2 s, one player walks up, raises a hand at 4.5 s (the lobby's launch) and lowers it, sweeps
    the wrist from hip to top and back once (so fidelity and range see the bar's whole travel), then draws every 7 s
    from 11 s, whichever signal it meets: 60 s."""
    person = Person(0.3, id=1).arrive(2.0).raise_hand(4.5, 0.5)
    person.wrist("right", HEIGHT_V, 0.0, 1.0, at=5.2).wrist("right", 0.0, HEIGHT_V, 1.0, at=6.2)
    for n in range(8):
        _hand(person, 11.0 + 7.0 * n, 1.2)
    return scene(persons=[person], ticks=1800)


def idle_body(body_id: int = 1, seconds: float = 60.0):
    """One body standing, hands down, for 60 s (body_id and seconds let tests vary the noise and the length)."""
    return scene(persons=[Person(0.3, id=body_id)], ticks=round(seconds / TICK))


def nobody():
    return scene(ticks=900)


def duel():
    """Two players, one each side, both raising a hand again and again on their own beat (3.0 and 3.4 s), so rounds
    end by whichever hand is up first, 50 s."""
    p1, p2 = Person(0.3, id=1), Person(0.7, id=2)
    for n in range(20):
        _hand(p1, 2.0 + 3.0 * n, 0.8)
        _hand(p2, 2.6 + 3.4 * n, 0.8)
    return scene(persons=[p1, p2], ticks=1500)


def early():
    """A hand up at 2.0 s, before any DRAW can come (play starts at 1.0 s and WAIT is 2 s at least): 20 s."""
    return scene(persons=[_hand(Person(0.3, id=1), 2.0, 1.0)], ticks=600)


Quickdraw.SCENARIOS = MappingProxyType({"canonical": canonical, "idle_body": idle_body, "nobody": nobody,
                                        "duel": duel, "early": early})
GAME = Quickdraw
