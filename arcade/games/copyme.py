"""Copy Me (spec 8 row 1, the hero): a target pose grows over the player's figure as a magenta outline; each judged limb
within tolerance turns green; at zero a flash, a pop and the round's best frame held. Three rounds, easy to silly.

Each seat's figure is its body's held keypoints (KeypointHold, C37) drawn in its player's colour in a square of
FIGURE_H px on its column (figure_rect's, from raw zone_x with COLUMN_SLACK px of backlash, C46: the lobby's mirror),
kept for the grace after the body was last seen. The target is POSES[target] placed on the body as Person places a
pose: at its hip centre, one height (the torso over TORSO_SHARE) on both axes, upright. The figure's map takes the
union of the body's box and the full target's, so neither leaves the square while the outline grows about the hips.

Scoring (score_pose, pure): an angle is a segment's direction with x times the frame's aspect, measured from the
torso's up axis, so position, size and a lean do not matter. The segments judged are the LIMBS whose target angle is
more than JUDGE_MIN_DEG off stand's (a leg only when both its keypoints are seen); share is the confidence-weighted
share of judged segments within LIMB_TOLERANCE_DEG. A round's points are round(100 * share) at the best tick of play's
last SCORE_WINDOW, and they count only when the seat's share was under FRESH_SHARE at some tick of that round's show or
play: a pose held from before the round scores nothing (C41). A standing body matches no target.

Seats: seat a is player 1's (sensed.player); a second body (sensed.player2) takes seat b at the next show and both
copy the same target; a seat b unseen past the grace leaves at the next show. Solo, the total is recorded once at over
when it is over 0; a game that ever had a seat b records nothing (Q23).

Phases: ready (READY_SECONDS and player 1 in view; "COPY THE SHAPE"), show (the target small, its name), play (the
outline grows over GROW_SECONDS, nothing drawn over it), result (the best frame frozen for FREEZE_SECONDS, then the
body as it is; "MATCH!" with the flash when a seat matched, else "MISS"; each seat's "+N" pop), over.

debug_state: phase, round (0 in ready, then 1 to ROUNDS), target (the round's pose name, None in ready), score (seat
a's total), other (seat b's total, None without a seat b), share (seat a's share now against the round's target, the
next one in ready), matches (seat a's rounds that counted with share >= MATCH_SHARE), judged (its judged segments),
active (its mean judged-angle error moved ACTIVE_DEG within ACTIVE_SECONDS), hint ("STRIKE THE SHAPE" is wanted),
humans (seats with a human), player_xy and player2_xy (each seat's head-disc centre as drawn, None when not drawn)."""
from __future__ import annotations

import dataclasses
import functools
import math
import random
from types import MappingProxyType
from typing import NamedTuple

from arcade.canvas import Canvas
from arcade.figure import FRAME_ASPECT, HEAD, KeypointHold, _thick_line, draw_figure, figure_rect, to_wall
from arcade.game import Game, GameInfo, icon_from_rows
from arcade.input import EPSILON, capture_grace
from arcade.juice import PLAYER_COLORS
from arcade.poses import POSES
from arcade.sensed import (LEFT_ANKLE, LEFT_ELBOW, LEFT_HIP, LEFT_KNEE, LEFT_SHOULDER, LEFT_WRIST, MIN_CONF, NOSE,
                           RIGHT_ANKLE, RIGHT_ELBOW, RIGHT_HIP, RIGHT_KNEE, RIGHT_SHOULDER, RIGHT_WRIST, SKELETON,
                           Body, Sensed)
from arcade.sources.actors import TICK, Person, scene

ROUNDS = 3
READY_SECONDS = 1.5
SHOW_SECONDS = 1.5
GROW_SECONDS = 3.0
GROW_FROM = 0.3
SCORE_WINDOW = 1.0
RESULT_SECONDS = 2.0
FREEZE_SECONDS = 1.5
OVER_SECONDS = 3.0
LIMB_TOLERANCE_DEG = 30.0
JUDGE_MIN_DEG = 60.0
ACTIVE_DEG = 30.0
ACTIVE_SECONDS = 1.0            # the window ACTIVE_DEG is measured over
MATCH_SHARE = 0.75
FRESH_SHARE = 0.5
WIN_MATCHES = 2
FIGURE_H = 60                   # rows 0 to 59: 60 to 63 stay free (the runner's marker)
HINT_IDLE_SECONDS = 2.0
OUTLINE_COLOR = (255, 0, 255)
MATCH_COLOR = (0, 200, 0)
MISS_COLOR = (255, 120, 0)
TEXT_COLOR = (255, 255, 255)
FLASH_COLOR = (255, 255, 255)
FLASH_SECONDS = 0.15
COLUMN_SLACK = 1                # px a figure's column may jitter without moving it (the lobby's)
CAMERA_FPS = 10                 # capture_grace(10): what a seat's body may be missing before its figure goes
SCORE_SCALE = 2
GLYPH_H = 7
LINE_Y = 51                     # the 1x line under the figures: "COPY THE SHAPE", the target's name, MISS
HINT_Y = 42                     # the hint's 1x line, over it
MATCH_Y = 44                    # "MATCH!" at 2x, rows 44 to 57
POP_Y = 30                      # a round's "+N" starts here, under the scores
BOX_MARGIN = 0.02               # a body box's margin round its keypoints (the tracker's and actors.body_box's)
BLACK = (0, 0, 0)

LADDER = (("arms_up", "t_pose", "right_up", "left_up"), ("y_pose", "flex", "airplane"), ("disco", "teapot"))

# The eight arm and leg segments of SKELETON (sensed.py), arms first.
LIMBS = ((LEFT_SHOULDER, LEFT_ELBOW), (LEFT_ELBOW, LEFT_WRIST), (RIGHT_SHOULDER, RIGHT_ELBOW),
         (RIGHT_ELBOW, RIGHT_WRIST), (LEFT_HIP, LEFT_KNEE), (LEFT_KNEE, LEFT_ANKLE), (RIGHT_HIP, RIGHT_KNEE),
         (RIGHT_KNEE, RIGHT_ANKLE))
LEGS = frozenset(range(4, 8))       # LIMBS' indices of the leg segments

_STAND = POSES["stand"]
TORSO_SHARE = -(_STAND[LEFT_SHOULDER][1] + _STAND[RIGHT_SHOULDER][1]) / 2     # shoulders over hips, per height
STAND_TOP = min(dy for _, dy in _STAND)          # the eyes, per height above the hips
STAND_BOTTOM = max(dy for _, dy in _STAND)       # the ankles

ICON = icon_from_rows([
    "###..##..##..###",
    "#..............#",
    "#..##..##..##..#",
    "...##..##..##...",
    ".....######.....",
    "#....######....#",
    "#......##......#",
    ".......##.......",
    ".......##.......",
    "#.....####.....#",
    "#....##..##....#",
    ".....##..##.....",
    "....##....##....",
    "#...##....##...#",
    "#..............#",
    "###..##..##..###",
])


# ----- scoring -----

def _seen(*points) -> bool:
    return all(p.conf >= MIN_CONF for p in points)


def _axis(kps) -> tuple[float, float]:
    """The torso's up direction in true aspect: hip centre to shoulder centre with both hips and both shoulders seen;
    with the shoulders alone, the shoulder line's normal (up); else the frame's vertical. Body.hip_mid lets one hip
    stand in for two, which tilts the axis up to 20 degrees on a still body, so this asks for pairs."""
    ls, rs, lh, rh = kps[LEFT_SHOULDER], kps[RIGHT_SHOULDER], kps[LEFT_HIP], kps[RIGHT_HIP]
    if _seen(ls, rs, lh, rh):
        return ((ls.x + rs.x - lh.x - rh.x) / 2 * FRAME_ASPECT, (ls.y + rs.y - lh.y - rh.y) / 2)
    if _seen(ls, rs):
        dx, dy = (rs.x - ls.x) * FRAME_ASPECT, rs.y - ls.y
        return (dy, -dx) if dx >= 0 else (-dy, dx)
    return (0.0, -1.0)


def _angle(axis: tuple[float, float], a, b) -> float:
    """The direction of the segment a to b (x times FRAME_ASPECT) from the axis, in degrees, -180 to 180."""
    vx, vy = (b.x - a.x) * FRAME_ASPECT, b.y - a.y
    return math.degrees(math.atan2(axis[0] * vy - axis[1] * vx, axis[0] * vx + axis[1] * vy))


def _off(a: float, b: float) -> float:
    """The gap between two angles in degrees, 0 to 180."""
    return abs((a - b + 180.0) % 360.0 - 180.0)


class _Point:
    __slots__ = ("x", "y", "conf")

    def __init__(self, x: float, y: float):
        self.x, self.y, self.conf = x, y, 1.0


@functools.lru_cache(maxsize=64)
def pose_angles(offsets) -> tuple[float, ...]:
    """Every LIMBS segment's angle in a pose's offsets, placed as Person places them (x and y times one height)."""
    pts = [_Point(dx, dy) for dx, dy in offsets]
    axis = _axis(pts)
    return tuple(_angle(axis, pts[a], pts[b]) for a, b in LIMBS)


STAND_ANGLES = pose_angles(POSES["stand"])


@functools.lru_cache(maxsize=64)
def judged_limbs(offsets) -> tuple[int, ...]:
    """LIMBS' indices whose angle in the offsets differs from stand's by more than JUDGE_MIN_DEG."""
    return tuple(i for i, angle in enumerate(pose_angles(offsets)) if _off(angle, STAND_ANGLES[i]) > JUDGE_MIN_DEG)


def limb_errors(body: Body, offsets) -> dict[int, float | None]:
    """{LIMBS index: the body's angle off the target's in degrees, None when a keypoint is unseen} for every judged
    segment: an arm always, a leg only when both its keypoints are seen (legs cropped: the upper body alone)."""
    target, kps = pose_angles(offsets), body.keypoints
    axis = _axis(kps)
    out: dict[int, float | None] = {}
    for i in judged_limbs(offsets):
        a, b = kps[LIMBS[i][0]], kps[LIMBS[i][1]]
        if not _seen(a, b):
            if i not in LEGS:
                out[i] = None
            continue
        out[i] = _off(_angle(axis, a, b), target[i])
    return out


def _tally(body: Body, errors: dict[int, float | None]) -> tuple[float, frozenset[int]]:
    """(share, the matched segments) of limb_errors' result: each segment weighs min(conf_a, conf_b); one with a
    keypoint under MIN_CONF has no angle, so it weighs and never hits (out of frame, conf 0, it weighs nothing)."""
    kps, total, hit, matched = body.keypoints, 0.0, 0.0, set()
    for i, err in errors.items():
        weight = min(kps[LIMBS[i][0]].conf, kps[LIMBS[i][1]].conf)
        total += weight
        if err is not None and err <= LIMB_TOLERANCE_DEG:
            hit += weight
            matched.add(i)
    return (hit / total if total > 0.0 else 0.0), frozenset(matched)


def score_pose(body: Body, offsets) -> tuple[float, int, int]:
    """(share, judged, matched) of a body against a target pose's offsets. share is the sum of min(conf_a, conf_b)
    over the judged segments within LIMB_TOLERANCE_DEG, over the same sum over every judged segment (0.0 with none
    seen); matched counts the seen ones within tolerance."""
    errors = limb_errors(body, offsets)
    share, matched = _tally(body, errors)
    return share, len(errors), len(matched)


# ----- the figures -----

def _anchor(body: Body) -> tuple[float, float, float]:
    """(hip x, hip y, height) a target is placed at on this body, in frame coordinates: the height is the torso over
    TORSO_SHARE (the box's height without hips or shoulders); the hips are both hips' centre, else under the
    shoulders by a torso, else the box's foot less stand's ankles."""
    kps, (x0, y0, x1, y1) = body.keypoints, body.box
    torso = body.torso
    h = torso / TORSO_SHARE if torso > 0.0 else max(y1 - y0 - 2 * BOX_MARGIN, 1e-3) / (STAND_BOTTOM - STAND_TOP)
    lh, rh = kps[LEFT_HIP], kps[RIGHT_HIP]
    if _seen(lh, rh):
        return (lh.x + rh.x) / 2, (lh.y + rh.y) / 2, h
    s = body.shoulder_mid
    if s is not None:
        return s.x, s.y + TORSO_SHARE * h, h
    return (x0 + x1) / 2, y1 - BOX_MARGIN - STAND_BOTTOM * h, h


class Framed(NamedTuple):
    """What to_wall and draw_figure read of a body: the box the figure maps from and the keypoints (a Body's box
    swapped without building a new Body, whose checks would run again on every tick)."""

    box: tuple[float, float, float, float]
    keypoints: tuple


@dataclasses.dataclass(frozen=True)
class View:
    """One seat's figure as drawn: body (held keypoints, its box the one the figure and the outline map from), rect,
    the matched segments (drawn green), and the target's hip point and full-size points (None: no outline)."""

    body: Body | Framed
    rect: tuple[int, int, int, int]
    matched: frozenset[int] = frozenset()
    hip: tuple[float, float] | None = None
    target: tuple[tuple[float, float], ...] | None = None

    def head(self) -> tuple[int, int] | None:
        """The head disc's centre on the wall, None when the nose is not seen (no disc)."""
        nose = self.body.keypoints[NOSE]
        return to_wall(self.body, self.rect)(nose.x, nose.y) if nose.conf >= MIN_CONF else None


def make_view(body: Body, rect, offsets=None, matched: frozenset[int] = frozenset()) -> View:
    """body's View in rect, with the target offsets placed on it when given."""
    if offsets is None:
        return View(body, rect)
    hx, hy, h = _anchor(body)
    pts = tuple((hx + dx * h, hy + dy * h) for dx, dy in offsets)
    x0, y0, x1, y1 = body.box
    box = (min(x0, min(p[0] for p in pts) - BOX_MARGIN), min(y0, min(p[1] for p in pts) - BOX_MARGIN),
           max(x1, max(p[0] for p in pts) + BOX_MARGIN), max(y1, max(p[1] for p in pts) + BOX_MARGIN))
    return View(Framed(box, body.keypoints), rect, matched, (hx, hy), pts)


def draw_view(canvas: Canvas, view: View, color, grow: float | None) -> None:
    """The figure in color, its matched segments in MATCH_COLOR (2 px), then the target's outline (1 px) scaled by
    grow about the hips (None: no outline)."""
    draw_figure(canvas, view.body, view.rect, color)
    f = to_wall(view.body, view.rect)
    kps = view.body.keypoints
    for i in sorted(view.matched):
        a, b = kps[LIMBS[i][0]], kps[LIMBS[i][1]]
        _thick_line(canvas, f(a.x, a.y), f(b.x, b.y), MATCH_COLOR, 2)
    if grow is None or view.target is None:
        return
    hx, hy = view.hip
    pts = [f(hx + (x - hx) * grow, hy + (y - hy) * grow) for x, y in view.target]
    for a, b in SKELETON:
        canvas.line(*pts[a], *pts[b], OUTLINE_COLOR)
    canvas.circle(*pts[NOSE], max(1, round(HEAD * view.rect[3] * grow)), OUTLINE_COLOR)


class Seat:
    """One player's place: its body's keypoint hold, its figure's slot (held body, sensed t last seen, rect x), the
    body id seat b is bound to, its total and matches, and this round's scoring."""

    def __init__(self, index: int, grace: float):
        self.index, self.grace = index, grace
        self.hold = KeypointHold(grace)
        self.slot: tuple[Body, float, int] | None = None
        self.id: int | None = None
        self.total = 0
        self.matches = 0
        self.view: View | None = None
        self.share, self.judged = 0.0, 0
        self.errors: dict[int, float | None] = {}
        self.new_round()

    def new_round(self) -> None:
        self.fresh = False
        self.best = 0.0
        self.frozen: View | None = None
        self.matched = False

    def see(self, body: Body | None, t: float, width: int) -> None:
        held = self.hold.update(body, t)
        if held is None:
            return
        x = figure_rect(held, (width, FIGURE_H))[0]
        if self.slot is not None and self.slot[0].id == held.id:          # the same person: x with backlash
            x = min(max(self.slot[2], x - COLUMN_SLACK), x + COLUMN_SLACK)
        self.slot = (held, t, x)

    def shown(self, t: float) -> Body | None:
        """The held body, kept for the grace after it was last seen."""
        if self.slot is None or t - self.slot[1] > self.grace + EPSILON:
            return None
        return self.slot[0]

    def unseat(self) -> None:
        self.id, self.slot, self.total, self.matches = None, None, 0, 0
        self.hold = KeypointHold(self.grace)


class Copyme(Game):
    info = GameInfo(name="copyme", title="COPY ME", verb="COPY", icon=ICON, needs=frozenset({"pose"}),
                    layouts=frozenset({"128x64"}), players=2, exit_gesture=False, kind="score")
    PHASES = ("ready", "show", "play", "result", "over")
    CAPTION_KEYS = ("phase", "round", "target", "score")
    SCENARIOS = MappingProxyType({})     # filled below, once the scripts exist

    def reset(self, size, rng: random.Random, fx) -> None:
        self.w, self.h = size
        self.rng, self.fx = rng, fx
        self.grace = capture_grace(CAMERA_FPS)
        self.targets = tuple(rng.choice(rung) for rung in LADDER)
        self.t, self.now = 0.0, 0.0
        self.phase, self.phase_t = "ready", 0.0
        self.round = 0
        self.seats = [Seat(0, self.grace), Seat(1, self.grace)]
        self._had_b = False             # a human ever sat in seat b: no best (Q23)
        self._samples: list[tuple[float, float]] = []      # (t, seat a's mean judged error) over ACTIVE_SECONDS
        self._active = False
        self._idle = 0.0
        self._hint = False

    # ----- the tick -----

    def update(self, sensed: Sensed, dt: float) -> None:
        self.t += dt
        self.phase_t += dt
        self.now = sensed.t
        if self.phase == "ready":
            if self.phase_t >= READY_SECONDS - EPSILON and sensed.player is not None:
                self._to_show(sensed)
        elif self.phase == "show":
            if self.phase_t >= SHOW_SECONDS - EPSILON:
                self._set("play")
        elif self.phase == "play":
            if self.phase_t >= GROW_SECONDS - EPSILON:
                self._end_round()
        elif self.phase == "result":
            if self.phase_t >= RESULT_SECONDS - EPSILON:
                if self.round < ROUNDS:
                    self._to_show(sensed)
                else:
                    self._to_over()
        a, b = self.seats
        for seat, body in zip(self.seats, self._bodies(sensed)):
            if seat is a or b.id is not None:
                seat.see(body, sensed.t, self.w)
        self._judge(dt)

    def _bodies(self, sensed: Sensed) -> tuple[Body | None, Body | None]:
        """Seat a's body (player 1, unless that is seat b's) and seat b's (its bound id's)."""
        b_id = self.seats[1].id
        found = {body.id: body for body in (sensed.player, sensed.player2) if body is not None}
        a = sensed.player if sensed.player is not None and sensed.player.id != b_id else None
        return a, (found.get(b_id) if b_id is not None else None)

    def _set(self, phase: str) -> None:
        self.phase, self.phase_t = phase, 0.0

    def _to_show(self, sensed: Sensed) -> None:
        """The next round: seat b settled (a seat b unseen past the grace leaves; a second body takes an empty one),
        each seat's round scoring cleared."""
        b = self.seats[1]
        if b.id is not None and b.shown(sensed.t) is None:
            b.unseat()
        two = sensed.player2
        if b.id is None and two is not None and (sensed.player is None or two.id != sensed.player.id):
            b.id, self._had_b = two.id, True
        for seat in self.seats:
            seat.new_round()
        self.round += 1
        self._samples.clear()
        self._set("show")

    def _end_round(self) -> None:
        """Play's zero: each seat's points from its best share (counted only when fresh), the flash on a match, a pop
        over each seat's frozen figure."""
        matched = []
        for seat in self.seats:
            if seat.frozen is None:
                continue
            points = round(100 * seat.best) if seat.fresh else 0
            seat.matched = seat.fresh and seat.best >= MATCH_SHARE
            seat.total += points
            seat.matches += seat.matched
            x = seat.frozen.rect[0] + FIGURE_H / 2
            color = MATCH_COLOR if seat.matched else PLAYER_COLORS[seat.index]
            self.fx.pop(f"+{points}", min(max(x, 12.0), self.w - 12.0), POP_Y, color)
            if seat.matched:
                matched.append(x)
        if matched and not self.fx.flash(FLASH_COLOR, FLASH_SECONDS):
            for x in matched:                          # a flash refused (FLASH_GAP): a burst at the figure instead
                self.fx.burst(x, POP_Y, MATCH_COLOR)
        self._set("result")

    def _to_over(self) -> None:
        a = self.seats[0]
        if not self._had_b:
            if a.matches >= WIN_MATCHES:
                self.fx.celebrate(MATCH_COLOR)
            if a.total > 0:
                self.scores.record(a.total)            # once, solo, and only for a game in which a round counted
        self._set("over")

    def _judge_target(self) -> str:
        """The pose judged now: the round's, the first one in ready."""
        return self.targets[max(self.round, 1) - 1]

    def _judge(self, dt: float) -> None:
        """Each seat's share and view this tick; freshness and the best frame in show and play; seat a's activity."""
        offsets = POSES[self._judge_target()]
        live = self.phase in ("show", "play")
        window = self.phase == "play" and self.phase_t >= GROW_SECONDS - SCORE_WINDOW - EPSILON
        for seat in self.seats:
            seat.view, seat.share, seat.judged, seat.errors = None, 0.0, 0, {}
            body = seat.shown(self.now)
            if body is None:
                continue
            seat.errors = limb_errors(body, offsets)
            seat.share, matched = _tally(body, seat.errors)
            seat.judged = len(seat.errors)
            rect = (seat.slot[2], 0, FIGURE_H, FIGURE_H)
            seat.view = make_view(body, rect, offsets, matched) if live else make_view(body, rect)
            if live and seat.share < FRESH_SHARE:
                seat.fresh = True
            if window and (seat.frozen is None or seat.share > seat.best):
                seat.best, seat.frozen = seat.share, seat.view
        self._update_active(self.seats[0].errors)
        self._idle = 0.0 if self._active else self._idle + dt
        self._hint = (self._idle >= HINT_IDLE_SECONDS - EPSILON and self.phase in ("ready", "show", "play")
                      and self.seats[0].view is not None)

    def _update_active(self, errors: dict[int, float | None]) -> None:
        """Active: seat a's mean judged-angle error moved ACTIVE_DEG or more within ACTIVE_SECONDS. A mean is taken
        only with every judged segment seen, so a keypoint that drops out does not change what is averaged."""
        self._active = False
        if not errors or any(err is None for err in errors.values()):
            return
        self._samples.append((self.t, sum(errors.values()) / len(errors)))
        self._samples = [(t, e) for t, e in self._samples if self.t - t <= ACTIVE_SECONDS + EPSILON]
        values = [e for _, e in self._samples]
        self._active = max(values) - min(values) >= ACTIVE_DEG

    def done(self) -> bool:
        return self.phase == "over" and self.phase_t >= OVER_SECONDS - EPSILON

    # ----- drawing -----

    def _drawn(self, seat: Seat) -> tuple[View | None, float | None]:
        """(the view drawn for seat, the outline's scale or None)."""
        if self.phase == "result" and self.phase_t < FREEZE_SECONDS - EPSILON and seat.frozen is not None:
            return seat.frozen, 1.0
        if self.phase == "show":
            return seat.view, GROW_FROM
        if self.phase == "play":
            return seat.view, GROW_FROM + (1.0 - GROW_FROM) * min(1.0, self.phase_t / GROW_SECONDS)
        return seat.view, None

    def draw(self, canvas: Canvas) -> None:
        for seat in self.seats:                                  # seat b is drawn over seat a
            view, grow = self._drawn(seat)
            if view is not None:
                draw_view(canvas, view, PLAYER_COLORS[seat.index], grow)
        a = self.seats[0]
        if self.phase == "ready":
            self._centred(canvas, "COPY THE SHAPE", LINE_Y, TEXT_COLOR)
        elif self.phase == "show":              # play draws nothing over the growing outline
            self._centred(canvas, self._judge_target().replace("_", " ").upper(), LINE_Y, TEXT_COLOR)
        elif self.phase == "result":
            if any(seat.matched for seat in self.seats):     # with the flash; each seat's pop says whose
                self._centred(canvas, "MATCH!", MATCH_Y, MATCH_COLOR, SCORE_SCALE)
            else:
                self._centred(canvas, "MISS", LINE_Y, MISS_COLOR)
        if self._hint:
            self._centred(canvas, "STRIKE THE SHAPE", HINT_Y, TEXT_COLOR)
        self._score(canvas, a.total, 0)
        b = self.seats[1]
        if b.id is not None:
            self._score(canvas, b.total, 1)

    def _centred(self, canvas: Canvas, text: str, y: int, color, scale: int = 1) -> None:
        """text centred across the wall at row y over a black box 1 px wider all round."""
        width = canvas.text_width(text, scale) - scale           # the last glyph's cell gap is not drawn
        x = (self.w - width) // 2
        canvas.fill_rect(x - 1, y - 1, width + 2, GLYPH_H * scale + 2, BLACK)
        canvas.text(x, y, text, color, scale)

    def _score(self, canvas: Canvas, total: int, index: int) -> None:
        """A seat's total at 2x on row 1, seat a's at the left edge, seat b's at the right, each over a black box
        1 px wider than the text (drawn last, so a figure under it never hides it)."""
        text = str(total)
        width = canvas.text_width(text, SCORE_SCALE)
        x = 1 if index == 0 else self.w - width
        canvas.fill_rect(x - 1, 0, width + 1, GLYPH_H * SCORE_SCALE + 3, BLACK)
        canvas.text(x, 1, text, PLAYER_COLORS[index], SCORE_SCALE)

    def debug_state(self) -> dict:
        a, b = self.seats
        heads = []
        for seat in self.seats:
            view, _ = self._drawn(seat)
            heads.append(None if view is None else view.head())
        return {"phase": self.phase, "round": self.round,
                "target": None if self.round == 0 else self._judge_target(), "score": a.total,
                "other": b.total if b.id is not None else None, "share": round(a.share, 3), "matches": a.matches,
                "judged": a.judged, "active": bool(self._active), "hint": bool(self._hint),
                "humans": int(a.view is not None) + int(b.id is not None), "player_xy": heads[0],
                "player2_xy": heads[1]}


# ----- scripts -----

CANONICAL_SECONDS = 30.0
RAISE_AT = 4.5                  # the lobby launches on the raised hand
SWEEP = (0.15, 0.85)            # canonical's player walks across the mat from one to the other, one way
WALK_SPEED = 0.1                # zone per second: a figure of 2 px lines walked faster trips the flash rule's area
CYCLE_LEAD = 0.25               # the pose cycle runs this long either side of play's last SCORE_WINDOW (launch lag)
FLASH_SECOND = 1.0              # the flash rule counts a pixel's transitions over a second: no walk that near a cycle
FREEZE_MARGIN = 0.1             # a walk starts this long after a frozen frame ends (the launch's tick of lag)


def cam_x(zone_x: float) -> float:
    """The camera x a Person stands at to be at zone_x of the mat (the default calibration's zone)."""
    from arcade.calibration import Calibration

    x0, _, x1, _ = Calibration().zone
    return x0 + zone_x * (x1 - x0)


def play_starts(launch: float) -> list[float]:
    """When each round's play starts for a game launched at `launch` with its player in view from then."""
    first = launch + READY_SECONDS + SHOW_SECONDS
    return [first + k * (SHOW_SECONDS + GROW_SECONDS + RESULT_SECONDS) for k in range(ROUNDS)]


def cycles(launch: float) -> list[tuple[float, float]]:
    """Each round's pose cycle, (from, to) seconds: play's last SCORE_WINDOW and CYCLE_LEAD either side of it."""
    return [(start + GROW_SECONDS - SCORE_WINDOW - CYCLE_LEAD, start + GROW_SECONDS + CYCLE_LEAD)
            for start in play_starts(launch)]


def strike_every(person: Person, launch: float, reverse: bool = False) -> Person:
    """Through each round's cycle, the person cycles every pose of the round's rung, each held SCORE_WINDOW over the
    rung's size, so the whole rung recurs in play's last SCORE_WINDOW whichever target was drawn; they stand before
    and after (each round's pose is struck fresh)."""
    for (start, end), rung in zip(cycles(launch), LADDER):
        order = tuple(reversed(rung)) if reverse else rung
        dwell = SCORE_WINDOW / len(order)
        for j in range(math.ceil((end - start) / dwell - 1e-9)):
            person.pose(order[j % len(order)], at=start + j * dwell, seconds=dwell)
    return person


def walk_windows(launch: float) -> list[tuple[float, float]]:
    """(from, to) seconds a canonical player may walk: from the raised hand, and after each round's frozen frame,
    until FLASH_SECOND before the next cycle (a walk's transitions and a cycle's in one second fill too much of a
    square), and never while the frame is frozen (the figure would not follow the body)."""
    out, at = [], launch + 0.5
    for (cycle, _), start in zip(cycles(launch), play_starts(launch)):
        out.append((at, cycle - FLASH_SECOND))
        at = start + GROW_SECONDS + FREEZE_SECONDS + FREEZE_MARGIN
    return out


def canonical():
    """The wall empty for 2 s, then one player walks up at the mat's left and raises a hand at 4.5 s (the lobby
    launches the game), walks slowly across the mat (SWEEP, at WALK_SPEED) between the rounds' pose cycles inside the
    measured 20 s, and strikes every pose of each round's rung in its play: every round shows green limbs, a frozen
    frame and a pop; CANONICAL_SECONDS."""
    x, end = SWEEP
    person = Person(cam_x(x), id=1).arrive(2.0).raise_hand(RAISE_AT, 0.5)
    for start, stop in walk_windows(RAISE_AT):
        if x >= end:
            break
        to = min(end, x + WALK_SPEED * (stop - start))
        person.walk(cam_x(to), (to - x) / WALK_SPEED, at=start)
        x = to
    strike_every(person, RAISE_AT)
    return scene(persons=[person], ticks=round(CANONICAL_SECONDS / TICK))


def idle_body(body_id: int = 1, seconds: float = 60.0):
    """One body standing, hands down, for 60 s (body_id and seconds let tests vary the noise and the length)."""
    return scene(persons=[Person(cam_x(0.3), id=body_id)], ticks=round(seconds / TICK))


def nobody():
    return scene(ticks=900)


def duo():
    """Two players in view from the start, one each side, each striking every pose of each round's rung in its play
    (strike_every; the second in the other order): 26 s, the whole game."""
    left = strike_every(Person(cam_x(0.3), id=1), 0.0)
    right = strike_every(Person(cam_x(0.7), id=2), 0.0, reverse=True)
    return scene(persons=[left, right], ticks=round(26.0 / TICK))


Copyme.SCENARIOS = MappingProxyType({"canonical": canonical, "idle_body": idle_body, "nobody": nobody, "duo": duo})
GAME = Copyme
