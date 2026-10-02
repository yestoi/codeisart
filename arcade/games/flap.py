"""Flap (spec 8 row 7): both wrists sweep from above to below the shoulders and the bird rises; gravity is gentle, the
gaps are wide, a crash holds and fades, and a run survives RUN_SECONDS.

The flap (C44, C46): each wrist is read as body.reach(wrist)'s v on every new capture (by sensed.camera_t) when its
keypoint is at MIN_CONF or more, its last value held for capture_grace(CAMERA_FPS). A flap fires on the capture where
both wrists are below the line (v over V_BELOW) and both were above it (v under V_ABOVE) within the last FLAP_WINDOW.
One wrist alone never flaps, so a hanging body never does either (C41). The wing gauge, a marker at the left edge, is
the hand's height: Cursor, then a Glide; it shows the two lines a flap crosses and is the control the oracle measures.

Phases: ready (the bird level at READY_Y, the first pipe standing at the right edge, until the first flap once
READY_SECONDS have passed), play, over (a crash's red fade, or SAFE!; a flap after the fade starts a new run while
runs < MAX_RUNS; done OVER_SECONDS after the run ended). The score is the gaps passed in the run; the best run is
recorded once (C41: a gap passed needs flaps, so a still body banks nothing).

debug_state: phase, score (gaps passed; the best run in over), runs (started), active, hint, survived, crashed, arms
("up" while both wrists are over the line within the window, else "down"), bird_xy (the bird's centre), bird_vy (px/s,
down positive), gap_xy (the next gap's centre, None past the last), wing_xy (the gauge marker's centre) and t_left."""
from __future__ import annotations

import random
from collections import deque
from types import MappingProxyType

from arcade.canvas import Canvas
from arcade.game import Game, GameInfo, icon_from_rows
from arcade.input import Cursor, Glide, capture_grace
from arcade.juice import PLAYER_COLORS
from arcade.sensed import LEFT_WRIST, MIN_CONF, RIGHT_WRIST, Sensed
from arcade.sources.actors import TICK, Person, scene
from show.font import CELL_H

RUN_SECONDS = 45.0
READY_SECONDS = 1.0
READY_Y = 30
FLAP_WINDOW = 0.4
V_ABOVE = 0.40                  # a wrist with v under this is over the line (above the shoulders)
V_BELOW = 0.62                  # and with v over this under it (below the shoulders)
BIRD_X = 28
BIRD_W = 5
BIRD_H = 4
GRAVITY = 24.0                  # px/s2
FLAP_VY = -22.0                 # px/s, set (not added) by a flap
MAX_FALL = 30.0                 # px/s
PIPE_W = 6
GAP_H = (34, 30)                # px, linear over the run (at a pipe's spawn)
PIPE_EVERY = 3.0                # s between pipes
SCROLL = 20.0                   # px/s
GAP_Y = (14, 44)                # the range of a gap's centre
GAP_STEP = 6                    # a gap's centre lies within this of the one before
FLOOR_Y = 59                    # the bird's bottom touching this row crashes; rows 60 to 63 stay free
CRASH_SECONDS = 1.2
MAX_RUNS = 3
OVER_SECONDS = 3.0
GAUGE_W = 8
V_TOP, V_BOTTOM = 0.15, 0.85    # the hand heights the gauge spans
GAUGE_TOP, GAUGE_BOTTOM = 4, 56
GAUGE_H = 2
TICK_W = 3
ACTIVE_PX = 3
HINT_IDLE_SECONDS = 2.0
CAMERA_FPS = 10
SCORE_SCALE = 2
BIRD_COLOR = PLAYER_COLORS[0]
PIPE_COLOR = (0, 200, 0)
CRASH_COLOR = (255, 0, 0)
SAFE_COLOR = (0, 200, 0)
TEXT_COLOR = (255, 120, 0)
SCORE_COLOR = (255, 255, 255)
TICK_COLOR = (255, 255, 255)
READY_TEXT = "FLAP TO FLY"
HINT_TEXT = "ARMS UP THEN DOWN"
AGAIN_TEXT = "FLAP AGAIN"
GLYPH_H = 7

ICON = icon_from_rows([
    "................",
    "................",
    ".##..........##.",
    ".###........###.",
    "..###......###..",
    "..####....####..",
    "...####..####...",
    "....##########..",
    ".....########...",
    "......######....",
    ".......####.....",
    "................",
    "................",
    "................",
    "................",
    "................",
])


class Pipe:
    """A pipe pair: x its left edge, gap_y the gap's centre, gap_h its height (px)."""

    def __init__(self, x: float, gap_y: float, gap_h: float):
        self.x, self.gap_y, self.gap_h = x, gap_y, gap_h
        self.passed = False

    @property
    def gap_top(self) -> float:
        return self.gap_y - self.gap_h / 2

    @property
    def gap_bottom(self) -> float:
        return self.gap_y + self.gap_h / 2


def gap_height(run_t: float) -> float:
    share = min(1.0, max(0.0, run_t / RUN_SECONDS))
    return GAP_H[0] + (GAP_H[1] - GAP_H[0]) * share


class Flap(Game):
    info = GameInfo(name="flap", title="FLAP", verb="FLAP", icon=ICON, needs=frozenset({"pose"}),
                    layouts=frozenset({"128x64"}), players=1, exit_gesture=False, kind="score")
    PHASES = ("ready", "play", "over")
    CAPTION_KEYS = ("phase", "score", "runs")
    SCENARIOS = MappingProxyType({})

    def reset(self, size, rng: random.Random, fx) -> None:
        self.w, self.h = size
        self.rng, self.fx = rng, fx
        self.grace = capture_grace(CAMERA_FPS)
        self.cursor = Cursor(grace=self.grace)
        self.glide = Glide(grace=self.grace)
        self.t = 0.0
        self.phase, self.phase_t = "ready", 0.0
        self.runs = 1
        self.best = 0
        self._banked = False
        self.flaps = 0
        self.gauge_v = V_BOTTOM
        self._rows: deque[tuple[float, int]] = deque()
        self._body: int | None = None
        self._active = False
        self._idle = 0.0
        self._hint = False
        self._cam = -1.0
        self._reset_wrists()
        self._new_run()

    def _reset_wrists(self) -> None:
        self._v: list[float | None] = [None, None]          # each wrist's last v, and when it was seen (by camera_t)
        self._seen = [-1e9, -1e9]
        self._above = [-1e9, -1e9]                           # camera_t of each wrist's last capture over the line

    def _new_run(self) -> None:
        self.score = 0
        self.run_t = 0.0
        self.bird_y = float(READY_Y)
        self.vy = 0.0
        self.crashed = self.survived = False
        self._armed = False
        self._prev_gap = float(READY_Y)
        self.pipes: list[Pipe] = []
        self.spawn_k = 0
        self._spawn(at=self.w - PIPE_W)
        self.spawn_k = 1

    # ----- the tick -----

    def update(self, sensed: Sensed, dt: float) -> None:
        self.t += dt
        self.phase_t += dt
        player = sensed.player
        if player is not None and player.id != self._body:
            self._body = player.id
            self.cursor, self.glide = Cursor(grace=self.grace), Glide(grace=self.grace)
            self._reset_wrists()
        self._read_gauge(sensed, player)
        flap = self._read_flap(sensed, player)
        if flap:
            self.flaps += 1
            self.fx.echo(1, "down")
        self._active = flap or self._gauge_moved()
        if self.phase == "ready":
            if flap:
                self._on_flap()
            elif self._armed and self.phase_t >= READY_SECONDS - 1e-9:
                self._start()
        elif self.phase == "play":
            self._step_run(dt)
            if flap and self.phase == "play":
                self.vy = FLAP_VY                       # after the tick's gravity: vy is FLAP_VY on the flap's tick
        elif flap:
            self._on_flap()
        self._update_hint(dt)

    def _read_gauge(self, sensed: Sensed, player) -> None:
        uv = self.cursor.update(player, sensed.t)
        v = self.glide.update(None if uv is None else uv[1], sensed.t, sensed.camera_t)
        if v is not None:
            self.gauge_v = v
        self._rows.append((self.t, self._gauge_row()))
        while self._rows and self.t - self._rows[0][0] > 1.0 + 1e-9:
            self._rows.popleft()

    def _gauge_row(self) -> int:
        share = min(1.0, max(0.0, (self.gauge_v - V_TOP) / (V_BOTTOM - V_TOP)))
        return round(GAUGE_TOP + share * (GAUGE_BOTTOM - GAUGE_TOP))

    def _gauge_moved(self) -> bool:
        rows = [r for _, r in self._rows]
        return bool(rows) and max(rows) - min(rows) >= ACTIVE_PX

    def _read_flap(self, sensed: Sensed, player) -> bool:
        """True on a capture where both wrists are below the line and both were above it within FLAP_WINDOW."""
        cam = sensed.camera_t
        if player is None or not cam > self._cam:
            return False
        self._cam = cam
        below = []
        for i, kp in enumerate((player.keypoints[LEFT_WRIST], player.keypoints[RIGHT_WRIST])):
            if kp.conf >= MIN_CONF:
                self._v[i], self._seen[i] = player.reach(kp)[1], cam
            elif cam - self._seen[i] > self.grace + 1e-9:
                self._v[i] = None
            v = self._v[i]
            if v is not None and v < V_ABOVE:
                self._above[i] = cam
            below.append(v is not None and v > V_BELOW)
        if all(below) and all(cam - a <= FLAP_WINDOW + 1e-9 for a in self._above):
            self._above = [-1e9, -1e9]
            return True
        return False

    def _arms_up(self) -> bool:
        return all(self._cam - a <= FLAP_WINDOW + 1e-9 for a in self._above)

    # ----- phases -----

    def _set(self, phase: str) -> None:
        self.phase, self.phase_t = phase, 0.0

    def _on_flap(self) -> None:
        """What a recognised flap does in the current phase."""
        if self.phase == "ready":
            if self.phase_t >= READY_SECONDS - 1e-9:
                self._start()
            else:
                self._armed = True
        elif self.phase == "play":
            self.vy = FLAP_VY
        elif self.crashed and self.runs < MAX_RUNS and self.phase_t >= CRASH_SECONDS - 1e-9:
            self.runs += 1
            self._new_run()
            self._start()

    def _start(self) -> None:
        self._set("play")
        self.vy = FLAP_VY

    def _spawn(self, at: float | None = None) -> None:
        """The next pipe: its gap's centre within GAP_STEP of the last one's, its height by the run's time."""
        lo, hi = GAP_Y
        gap = min(hi, max(lo, self._prev_gap + self.rng.uniform(-GAP_STEP, GAP_STEP)))
        self._prev_gap = gap
        self.pipes.append(Pipe(self.w if at is None else at, gap, gap_height(self.run_t)))

    def _step_run(self, dt: float) -> None:
        self.run_t += dt
        while self.run_t >= self.spawn_k * PIPE_EVERY - 1e-9 and \
                self.spawn_k * PIPE_EVERY + (self.w - BIRD_X) / SCROLL <= RUN_SECONDS:
            self._spawn()
            self.spawn_k += 1
        self.vy = min(MAX_FALL, self.vy + GRAVITY * dt)
        self.bird_y += self.vy * dt
        top = BIRD_H / 2
        if self.bird_y < top:
            self.bird_y, self.vy = top, max(0.0, self.vy)
        for pipe in self.pipes:
            pipe.x -= SCROLL * dt
        self.pipes = [p for p in self.pipes if p.x + PIPE_W > 0]
        if self.bird_y + BIRD_H / 2 >= FLOOR_Y or any(self._hits(p) for p in self.pipes):
            self._crash()
            return
        for pipe in self.pipes:
            if not pipe.passed and pipe.x + PIPE_W <= BIRD_X - BIRD_W / 2:
                pipe.passed = True
                self.score += 1
        if self.run_t >= RUN_SECONDS - 1e-9:
            self.survived = True
            self.fx.celebrate(SAFE_COLOR)
            self._end_run()

    def _hits(self, pipe: Pipe) -> bool:
        left, right = BIRD_X - BIRD_W / 2, BIRD_X + BIRD_W / 2
        if not (left < pipe.x + PIPE_W and right > pipe.x):
            return False
        return self.bird_y - BIRD_H / 2 < pipe.gap_top or self.bird_y + BIRD_H / 2 > pipe.gap_bottom

    def _crash(self) -> None:
        self.crashed = True
        self.fx.freeze(0.2)
        self.fx.shake(2, 0.3)
        self._end_run()

    def _end_run(self) -> None:
        self.best = max(self.best, self.score)
        self._set("over")
        if self.survived or self.runs >= MAX_RUNS:
            self._bank()

    def _bank(self) -> None:
        if not self._banked and self.best > 0:
            self._banked = True
            self.scores.record(self.best)          # once, for the best run, and only when a gap was passed (C41)

    def _update_hint(self, dt: float) -> None:
        self._idle = 0.0 if self._active else self._idle + dt
        if self._active or self.phase == "over":
            self._hint = False
        elif self._idle >= HINT_IDLE_SECONDS - 1e-9:
            self._hint = True

    def done(self) -> bool:
        if self.phase == "over" and self.phase_t >= OVER_SECONDS - 1e-9:
            self._bank()
            return True
        return False

    # ----- drawing -----

    def draw(self, canvas: Canvas) -> None:
        w = self.w
        for pipe in self.pipes:
            top, bottom = round(pipe.gap_top), round(pipe.gap_bottom)
            if top > 0:
                canvas.fill_rect(pipe.x, 0, PIPE_W, top, PIPE_COLOR)
            if bottom < FLOOR_Y:
                canvas.fill_rect(pipe.x, bottom, PIPE_W, FLOOR_Y - bottom, PIPE_COLOR)
        canvas.fill_rect(0, FLOOR_Y, w, 1, PIPE_COLOR)
        self._draw_bird(canvas)
        self._draw_gauge(canvas)
        if self.phase == "ready":
            width = canvas.text_width(READY_TEXT) - 1
            canvas.text((w - width) // 2, round(self.h * 0.7), READY_TEXT, TEXT_COLOR)
        elif self.phase == "over" and self.survived:
            width = canvas.text_width("SAFE!", SCORE_SCALE) - SCORE_SCALE
            canvas.text((w - width) // 2, round(self.h * 0.4) - CELL_H, "SAFE!", SAFE_COLOR, SCORE_SCALE)
        elif self.phase == "over" and self.runs < MAX_RUNS and self.phase_t >= CRASH_SECONDS:
            width = canvas.text_width(AGAIN_TEXT) - 1
            canvas.text((w - width) // 2, round(self.h * 0.7), AGAIN_TEXT, TEXT_COLOR)
        if self._hint and self.phase != "over":
            width = canvas.text_width(HINT_TEXT) - 1
            canvas.text((w - width) // 2, round(self.h * 0.7) + GLYPH_H + 3, HINT_TEXT, TEXT_COLOR)
        text = str(self._shown_score())
        x0 = w - canvas.text_width(text, SCORE_SCALE)
        canvas.fill_rect(x0 - 1, 0, w - x0 + 1, CELL_H * SCORE_SCALE + 2, (0, 0, 0))
        canvas.text(x0, 1, text, SCORE_COLOR, SCORE_SCALE)

    def _shown_score(self) -> int:
        return self.best if self.phase == "over" else self.score

    def _bird_color(self):
        if self.crashed and self.phase == "over":
            level = max(0.0, 1.0 - self.phase_t / CRASH_SECONDS)
            return (round(CRASH_COLOR[0] * level), 0, 0)
        return BIRD_COLOR

    def _draw_bird(self, canvas: Canvas) -> None:
        color = self._bird_color()
        left, top = BIRD_X - BIRD_W // 2, round(self.bird_y - BIRD_H / 2)
        canvas.fill_rect(left, top, BIRD_W, BIRD_H, color)
        if self.gauge_v < V_ABOVE:
            canvas.fill_rect(left, top - 2, 2, 2, color)                  # wings up
        else:
            canvas.fill_rect(left, top + BIRD_H, 2, 2, color)             # wings down

    def _draw_gauge(self, canvas: Canvas) -> None:
        for v in (V_ABOVE, V_BELOW):
            row = round(GAUGE_TOP + (v - V_TOP) / (V_BOTTOM - V_TOP) * (GAUGE_BOTTOM - GAUGE_TOP))
            canvas.fill_rect(GAUGE_W, row, TICK_W, 1, TICK_COLOR)
        canvas.fill_rect(0, self._gauge_row(), GAUGE_W, GAUGE_H, BIRD_COLOR)

    def _t_left(self) -> float:
        return max(0.0, RUN_SECONDS - self.run_t)

    def debug_state(self) -> dict:
        nxt = next((p for p in self.pipes if not p.passed), None)
        return {"phase": self.phase, "score": self._shown_score(), "runs": self.runs, "active": bool(self._active),
                "hint": bool(self._hint), "survived": bool(self.survived), "crashed": bool(self.crashed),
                "arms": "up" if self._arms_up() else "down",
                "bird_xy": (float(BIRD_X), round(self.bird_y, 2)), "bird_vy": round(self.vy, 2),
                "gap_xy": None if nxt is None else (round(nxt.x + PIPE_W / 2, 2), round(nxt.gap_y, 2)),
                "wing_xy": (GAUGE_W / 2, self._gauge_row() + GAUGE_H / 2), "t_left": round(self._t_left(), 1)}


# ----- scripts -----

RAISE_AT = 4.5
SWEEP_FROM = 5.0
SWEEP_SECONDS = 2.5             # one slow stroke of both wrists; six of them fill the measured 20 s
FLAP_EVERY = 1.8                # the level period: 2 * FLAP_VY / GRAVITY
FIRST_FLAP = 20.4


def cam_x(zone_x: float) -> float:
    from arcade.calibration import Calibration

    x0, _, x1, _ = Calibration().zone
    return x0 + zone_x * (x1 - x0)


def _flap_arm(person: Person, hand: str, at: float) -> None:
    """The wrist rises over 0.6 s, waits 0.1 s up, and snaps down over 0.25 s at `at`."""
    person.wrist(hand, 0.95, 0.1, 0.6, at=at - 0.7)
    person.wrist(hand, 0.1, 0.1, 0.1, at=at - 0.1)
    person.wrist(hand, 0.1, 0.95, 0.25, at=at)


def canonical():
    """The wall empty for 2 s, a walk-up, the raised hand that launches the game at 4.5 s, then six slow strokes of
    both wrists (0.95 to 0.1 and back, three full sweeps) for the gauge, then a flap every FLAP_EVERY s (the level
    period: the bird hovers past pipes until one catches it); 60 s."""
    person = Person(cam_x(0.5), id=1).arrive(2.0).raise_hand(RAISE_AT, 0.5)
    for k in range(6):
        a, b = (0.95, 0.1) if k % 2 == 0 else (0.1, 0.95)
        for hand in ("left", "right"):
            person.wrist(hand, a, b, SWEEP_SECONDS, at=SWEEP_FROM + k * SWEEP_SECONDS)
    t = FIRST_FLAP
    while t < 58.0:
        for hand in ("left", "right"):
            _flap_arm(person, hand, t)
        t += FLAP_EVERY
    return scene(persons=[person], ticks=round(60.0 / TICK))


def idle_body(body_id: int = 1, seconds: float = 60.0):
    return scene(persons=[Person(cam_x(0.3), id=body_id)], ticks=round(seconds / TICK))


def nobody():
    return scene(ticks=900)


def one_arm():
    """The right wrist flaps every FLAP_EVERY s for 20 s; the left hangs: never flies."""
    person = Person(cam_x(0.5), id=1).arrive(0.5).raise_hand(RAISE_AT, 0.5)
    t = 6.0
    while t < 19.0:
        _flap_arm(person, "right", t)
        t += FLAP_EVERY
    return scene(persons=[person], ticks=round(20.0 / TICK))


Flap.SCENARIOS = MappingProxyType({"canonical": canonical, "idle_body": idle_body, "nobody": nobody,
                                   "one_arm": one_arm})
GAME = Flap
