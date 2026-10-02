"""Jump (spec 8 row 9 as Q99 changed it): a high striker. Stand still ("GET SET"), then "JUMP!": for JUMP_WINDOW seconds
the bar shoots up with your nose's rise, you may jump as often as you like, the window's best peak stays as a line, and
past the bell line the bell rings. Three attempts; the best is the night's.

The measure (C41, C44, C46): torso is hip_mid to shoulder_mid in camera y (keypoints at MIN_CONF or more, held through
a dropout for capture_grace(CAMERA_FPS)). In ready, on every new capture (by sensed.camera_t), the nose's and the hip_mid's
camera y are kept for SETTLE_SECONDS; the window opens when both stay within STILL torso of their medians for the whole
span (x is free: a sway or a walk is still), and the medians are the baseline, new before every attempt. In play,
rise = (baseline nose y - nose y) / torso per capture, and a capture counts only while the hip_mid rose by at least
HIP_SHARE of the nose's rise (a nod or a head tilt never counts) and rise >= MIN_RISE; cm = round(rise * TORSO_CM).
A still body never reaches MIN_RISE with its hips (real noise moves a nose about 0.06 torsos), so it banks 0 and
records nothing.

The zone caps the rise: a body whose shoulders leave the zone's top is dropped by the runner, so the zone caps the
rise (about 47 cm at a body height of 0.6 of the frame, 33 cm at 0.7, 23 cm at 0.8).

Phases: ready (before EVERY attempt, until player 1 is still), play (the whole window, never early; its best peak
banks at its end), result (the attempt's peak held RESULT_SECONDS), over (the best held OVER_SECONDS; the best is
recorded once, when an attempt counted).

debug_state: phase, attempt (1 to ATTEMPTS), score (best_cm, an int), rise (torsos, live, 0 when not counted),
peak_cm (the attempt's best), best_cm, bell_cm, rang (the bell rang in any attempt), heights (banked cm per attempt),
active, hint, player_xy (the head disc's centre, None when no figure is drawn) and bar_xy (the bar top's centre)."""
from __future__ import annotations

import random
import statistics
from collections import deque
from types import MappingProxyType

from arcade.canvas import Canvas
from arcade.figure import KeypointHold, draw_figure, figure_rect, to_wall
from arcade.game import Game, GameInfo, icon_from_rows
from arcade.input import EPSILON, capture_grace
from arcade.juice import PLAYER_COLORS
from arcade.sensed import MIN_CONF, NOSE, Body, Sensed
from arcade.sources.actors import TICK, Person, scene
from show.font import CELL_H

ATTEMPTS = 3
SETTLE_SECONDS = 1.5
JUMP_WINDOW = 5.0
RESULT_SECONDS = 2.5
OVER_SECONDS = 3.0
MIN_RISE = 0.15                 # torsos
HIP_SHARE = 0.5                 # the hip_mid's rise over the nose's, at least
STILL = 0.1                     # torsos: how far the nose's and the hip_mid's camera y may stray from their medians
ACTIVE_RISE = 0.25              # torsos within 1 s
TORSO_CM = 50.0
BELL_CM = (28.0, 40.0)          # the bell's height, drawn once per game by the rng
BAR_TOP_CM = 60.0
BAR_X, BAR_W = 6, 10
BAR_TOP, BAR_BOTTOM = 6, 57
FIGURE_H = 56
HINT_IDLE_SECONDS = 2.0
CAMERA_FPS = 10
COLUMN_SLACK = 1                # px a figure's column may jitter without moving it (the lobby's)
MIN_SAMPLES = 5
SCORE_SCALE = 2
BAR_COLOR = (255, 160, 0)       # red share 0.61, under flash.RED_SHARE
BELL_COLOR = (255, 200, 0)
FRAME_COLOR = (0, 200, 255)
LINE_COLOR = (255, 255, 255)
TEXT_COLOR = (255, 160, 0)
SCORE_COLOR = (255, 255, 255)
BLACK = (0, 0, 0)
PLAYER_COLOR = PLAYER_COLORS[0]
BELL_W, BELL_H = 5, 4
INNER_H = BAR_BOTTOM - BAR_TOP - 1          # the bar's rows, from BAR_BOTTOM - 1 up
READY_TEXT = "GET SET"
PLAY_TEXT = "JUMP!"
FLASH = (255, 255, 255)

ICON = icon_from_rows([
    "................",
    "......####......",
    ".....######.....",
    "......####......",
    ".......##.......",
    ".....######.....",
    ".....##..##.....",
    ".....##..##.....",
    ".....##..##.....",
    ".....##..##.....",
    ".....##..##.....",
    ".....##..##.....",
    ".....######.....",
    ".....######.....",
    "................",
    "................",
])


def measure_rise(body: Body, base_nose_y: float, base_hip_y: float, torso: float) -> float | None:
    """The nose's rise over the baseline in torsos, None when the capture does not count: a nose or hip_mid under
    MIN_CONF, no torso, a rise under MIN_RISE, or a hip_mid that rose by less than HIP_SHARE of the nose's rise.

    A body whose shoulders leave the zone's top is dropped by the runner, so the zone caps the rise (about 47 cm at a
    body height of 0.6 of the frame, 33 cm at 0.7, 23 cm at 0.8)."""
    nose, hip = body.nose, body.hip_mid
    if nose.conf < MIN_CONF or hip is None or hip.conf < MIN_CONF or not torso > 0.0:
        return None
    rise = (base_nose_y - nose.y) / torso
    if rise < MIN_RISE or (base_hip_y - hip.y) / torso < HIP_SHARE * rise:
        return None
    return rise


def _torso(body: Body) -> float | None:
    """hip_mid to shoulder_mid in camera y, None when either is not seen."""
    s, h = body.shoulder_mid, body.hip_mid
    if s is None or h is None or s.conf < MIN_CONF or h.conf < MIN_CONF or not h.y - s.y > 1e-3:
        return None
    return h.y - s.y


def _row(cm: float) -> int:
    """The bar's top row at cm (BAR_BOTTOM at 0, BAR_TOP + 1 at BAR_TOP_CM)."""
    return BAR_BOTTOM - round(min(max(cm, 0.0), BAR_TOP_CM) / BAR_TOP_CM * INNER_H)


class Jump(Game):
    info = GameInfo(name="jump", title="JUMP", verb="JUMP", icon=ICON, needs=frozenset({"pose"}),
                    layouts=frozenset({"128x64"}), players=1, exit_gesture=False, kind="score")
    PHASES = ("ready", "play", "result", "over")
    CAPTION_KEYS = ("phase", "attempt", "peak_cm", "best_cm")
    SCENARIOS = MappingProxyType({})

    def reset(self, size, rng: random.Random, fx) -> None:
        self.w, self.h = size
        self.rng, self.fx = rng, fx
        self.grace = capture_grace(CAMERA_FPS)
        self.bell_cm = rng.uniform(*BELL_CM)
        self.t = 0.0
        self.attempt = 1
        self.heights: list[int] = []
        self.best_cm = 0
        self.rang = False
        self._banked = False
        self._hold = KeypointHold(self.grace)
        self._slot: tuple[Body, float, int] | None = None       # held body, game t last seen, its column's x
        self._cam = -1.0
        self._body: int | None = None
        self._active = False
        self._idle = 0.0
        self._hint = False
        self._begin("ready")

    def _begin(self, phase: str) -> None:
        self.phase, self.phase_t = phase, 0.0
        if phase == "ready":
            self._samples: deque[tuple[float, float, float, float]] = deque()   # camera_t, nose y, hip y, torso
            self.peak_cm = 0
            self._rang_now = False
            self._base: tuple[float, float, float] | None = None
        self.rise = 0.0
        self.cm = 0
        self._recent: deque[tuple[float, float]] = deque()

    # ----- the tick -----

    def update(self, sensed: Sensed, dt: float) -> None:
        self.t += dt
        self.phase_t += dt
        player = sensed.player
        if player is not None and player.id != self._body:
            self._body = player.id
            self._samples.clear()
        held = self._hold.update(player, sensed.t)
        self._seat(held)
        counted = False
        if held is None:
            if self._slot is None or self.t - self._slot[1] > self.grace + EPSILON:
                self._samples.clear()
                self.rise, self.cm = 0.0, 0
        elif sensed.camera_t > self._cam:
            self._cam = sensed.camera_t
            if self.phase == "ready":
                self._sample(held, sensed.camera_t)
            elif self.phase == "play":
                counted = self._measure(held)
        self._track_active(counted)
        if self.phase == "play" and self.phase_t >= JUMP_WINDOW - EPSILON:
            self._end_window()
        elif self.phase == "result" and self.phase_t >= RESULT_SECONDS - EPSILON:
            self._next_attempt()
        self._update_hint(dt)

    def _seat(self, held: Body | None) -> None:
        """The figure's slot: the held body and its column, which moves only past COLUMN_SLACK for the same person."""
        if held is None:
            return
        x = figure_rect(held, (self.w, FIGURE_H))[0]
        if self._slot is not None and self._slot[0].id == held.id:
            x = min(max(self._slot[2], x - COLUMN_SLACK), x + COLUMN_SLACK)
        self._slot = (held, self.t, x)

    def _sample(self, held: Body, cam: float) -> None:
        torso, nose, hip = _torso(held), held.nose, held.hip_mid
        if torso is None or nose.conf < MIN_CONF or hip is None:
            return
        self._samples.append((cam, nose.y, hip.y, torso))
        while self._samples and cam - self._samples[0][0] > SETTLE_SECONDS + EPSILON:
            self._samples.popleft()
        if len(self._samples) < MIN_SAMPLES or cam - self._samples[0][0] < SETTLE_SECONDS - 0.5 / CAMERA_FPS - EPSILON:
            return
        noses = [s[1] for s in self._samples]
        hips = [s[2] for s in self._samples]
        nose_med, hip_med = statistics.median(noses), statistics.median(hips)
        torso_med = statistics.median(s[3] for s in self._samples)
        limit = STILL * torso_med
        if all(abs(n - nose_med) <= limit and abs(h - hip_med) <= limit for n, h in zip(noses, hips)):
            self._base = (nose_med, hip_med, torso_med)
            self._begin("play")

    def _measure(self, held: Body) -> bool:
        """One capture of the window: the live rise, the peak, the bell. True when the capture counted."""
        base_nose, base_hip, torso = self._base
        rise = measure_rise(held, base_nose, base_hip, torso)
        self.rise = 0.0 if rise is None else rise
        self.cm = 0 if rise is None else round(rise * TORSO_CM)
        if rise is None:
            return False
        self.peak_cm = max(self.peak_cm, self.cm)
        if not self._rang_now and self.cm >= self.bell_cm:
            self._rang_now = self.rang = True
            self.fx.flash(FLASH, 0.15)                                  # the governor may refuse: nothing else hangs on it
            self.fx.pop("DING!", BAR_X + BAR_W + 16, _row(self.bell_cm), BELL_COLOR)
        return True

    def _track_active(self, counted: bool) -> None:
        self._recent.append((self.t, self.rise))
        while self._recent and self.t - self._recent[0][0] > 1.0 + EPSILON:
            self._recent.popleft()
        rises = [r for _, r in self._recent]
        self._active = counted or (self.phase == "play" and max(rises) - min(rises) >= ACTIVE_RISE)

    # ----- phases -----

    def _end_window(self) -> None:
        self.heights.append(self.peak_cm)
        self.best_cm = max(self.best_cm, self.peak_cm)
        self._begin_result()

    def _begin_result(self) -> None:
        peak = self.peak_cm
        self._begin("result")
        self.peak_cm = peak

    def _next_attempt(self) -> None:
        if self.attempt < ATTEMPTS:
            self.attempt += 1
            self._begin("ready")
            return
        peak = self.peak_cm
        self._begin("over")
        self.peak_cm = peak
        if not self._banked and self.best_cm > 0:
            self._banked = True
            if self.scores.record(self.best_cm):
                self.fx.banner("NEW BEST")

    def _update_hint(self, dt: float) -> None:
        self._idle = 0.0 if self._active else self._idle + dt
        if self._active or self.phase != "play":
            self._hint = False
        elif self._idle >= HINT_IDLE_SECONDS - EPSILON:
            self._hint = True

    def done(self) -> bool:
        return self.phase == "over" and self.phase_t >= OVER_SECONDS - EPSILON

    # ----- drawing -----

    def _view(self) -> tuple[Body, tuple[int, int, int, int]] | None:
        """The figure drawn now: the held body in its column's rect, None once it was last seen over the grace ago."""
        if self._slot is None or self.t - self._slot[1] > self.grace + EPSILON:
            return None
        body, _, x = self._slot
        return body, (x, 0, FIGURE_H, FIGURE_H)

    def draw(self, canvas: Canvas) -> None:
        view = self._view()
        if view is not None:
            draw_figure(canvas, view[0], view[1], PLAYER_COLOR)
        self._draw_striker(canvas)
        if self.phase == "ready":
            self._centred(canvas, READY_TEXT, 28, TEXT_COLOR)
        elif self.phase == "play":
            self._centred(canvas, PLAY_TEXT, 20, TEXT_COLOR, SCORE_SCALE)
            if self._hint:
                self._centred(canvas, PLAY_TEXT, 40, TEXT_COLOR)
        elif self.phase == "result":
            text = str(self.peak_cm)
            x = BAR_X + BAR_W + 4
            width = canvas.text_width(text, SCORE_SCALE) - SCORE_SCALE
            canvas.fill_rect(x - 1, 23, width + 2, CELL_H * SCORE_SCALE + 2, BLACK)
            canvas.text(x, 24, text, TEXT_COLOR, SCORE_SCALE)
        text = str(self.best_cm)
        x0 = self.w - canvas.text_width(text, SCORE_SCALE)
        canvas.fill_rect(x0 - 1, 0, self.w - x0 + 1, CELL_H * SCORE_SCALE + 2, BLACK)
        canvas.text(x0, 1, text, SCORE_COLOR, SCORE_SCALE)

    def _centred(self, canvas: Canvas, text: str, y: int, color, scale: int = 1) -> None:
        width = canvas.text_width(text, scale) - scale
        x = (self.w - width) // 2
        canvas.fill_rect(x - 1, y - 1, width + 2, CELL_H * scale + 2, BLACK)
        canvas.text(x, y, text, color, scale)

    def _draw_striker(self, canvas: Canvas) -> None:
        inner_x, inner_w = BAR_X + 1, BAR_W - 2
        canvas.fill_rect(inner_x, BAR_TOP + 1, inner_w, INNER_H, BLACK)
        top = _row(self.cm)
        canvas.fill_rect(inner_x, top, inner_w, BAR_BOTTOM - top, BAR_COLOR)
        line = self.best_cm if self.phase == "over" else self.peak_cm
        if line > 0:
            canvas.fill_rect(inner_x, _row(line), inner_w, 1, LINE_COLOR)
        canvas.rect(BAR_X, BAR_TOP, BAR_W, BAR_BOTTOM - BAR_TOP + 1, FRAME_COLOR)
        canvas.fill_rect(BAR_X + (BAR_W - BELL_W) // 2, _row(self.bell_cm) - BELL_H + 1, BELL_W, BELL_H, BELL_COLOR)

    def _player_xy(self) -> tuple[int, int] | None:
        view = self._view()
        if view is None or view[0].nose.conf < MIN_CONF:
            return None
        nose = view[0].nose
        return to_wall(view[0], view[1])(nose.x, nose.y)

    def debug_state(self) -> dict:
        return {"phase": self.phase, "attempt": self.attempt, "score": int(self.best_cm), "rise": round(self.rise, 3),
                "peak_cm": int(self.peak_cm), "best_cm": int(self.best_cm), "bell_cm": round(self.bell_cm, 2),
                "rang": bool(self.rang), "heights": list(self.heights), "active": bool(self._active),
                "hint": bool(self._hint), "player_xy": self._player_xy(),
                "bar_xy": (BAR_X + BAR_W / 2, float(_row(self.cm)))}


# ----- scripts -----

RAISE_AT = 4.5                  # the lobby launches on the raised hand
WALK_FROM = RAISE_AT + 1.0      # the walk starts once the raised hand is down
SWEEP = (0.15, 0.85)            # canonical's player walks across the mat from one end to the other and back to 0.5
WALK_SPEED = 0.1                # zone per second: a figure of 2 px lines walked faster trips the flash rule's area
CANONICAL_SECONDS = 40.0
JUMP_AT = 0.5                   # each jump this long after its window opens
JUMP_HEIGHT = 0.15              # of the frame: about 0.83 torsos at a body height of 0.6, over the bell


def cam_x(zone_x: float) -> float:
    from arcade.calibration import Calibration

    x0, _, x1, _ = Calibration().zone
    return x0 + zone_x * (x1 - x0)


def canonical():
    """The wall empty for 2 s, a walk-up, the raised hand that launches the game at 4.5 s, then the player walks across
    the mat (0.5 to 0.15 to 0.85 to 0.5 at WALK_SPEED; a walk is still in y, so the windows open during it: at launch +
    1.5 s + 9 s x k) and jumps once in each window; CANONICAL_SECONDS."""
    person = Person(cam_x(0.5), id=1).arrive(2.0).raise_hand(RAISE_AT, 0.5)
    x, at = 0.5, WALK_FROM
    for to in (SWEEP[0], SWEEP[1], 0.5):
        person.walk(cam_x(to), abs(to - x) / WALK_SPEED, at=at)
        at += abs(to - x) / WALK_SPEED
        x = to
    for k in range(ATTEMPTS):
        person.jump(RAISE_AT + SETTLE_SECONDS + k * (SETTLE_SECONDS + JUMP_WINDOW + RESULT_SECONDS) + JUMP_AT,
                    height=JUMP_HEIGHT, seconds=0.6)
    return scene(persons=[person], ticks=round(CANONICAL_SECONDS / TICK))


def idle_body(body_id: int = 1, seconds: float = 60.0):
    return scene(persons=[Person(cam_x(0.3), id=body_id)], ticks=round(seconds / TICK))


def nobody():
    return scene(ticks=900)


Jump.SCENARIOS = MappingProxyType({"canonical": canonical, "idle_body": idle_body, "nobody": nobody})
GAME = Jump
