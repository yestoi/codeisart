"""Dodge (spec 8, game 5; side steps only, Q70): rocks fall, the player's block (drawn as the Man, MAN) follows the body's x across the mat,
and a run ends on the first hit or survives RUN_SECONDS.

The whole body is the control: the hips' zone_x, through a Glide (by sensed.camera_t, C44: never raw), mapped from
ZONE_LO..ZONE_HI of the mat to the wall's width, so the middle of the mat reaches both walls. Every AIM_EVERY-th rock
(every AIM_TIGHT_EVERY-th from AIM_TIGHT_AT) falls at the block's x at its spawn, so a still body is hit within about
4 s; a rock that passes counts as a dodge only when the player's x span since its spawn was DODGE_TRAVEL_PX (C41, C42),
and a best is stored only for a run that counted one. Hitboxes forgive: each box is shrunk HIT_SLACK px in total
(half a slack on every side), so a 2 px graze is no hit and 3 px is. Nobody in view holds the run (rocks, spawns,
the clock) for the Glide's grace, then the run goes on with the block where it was.

Harder (the owner, 2026-10-03, after the review of that day): the random rocks come in SIZES on a schedule
(SIZE_FROM: rocks from the start as before, pebbles and slabs from 10 s, beams from 20 s), each in its own tint, none of them
red (the governor doubles saturated red); the aimed rock is always the 6x4 rock, so the canonical script's
arithmetic holds. A 3x3 pebble hits only when it sits inside the block's columns: a decoy. From GATE_AFTER some
random spawns are a gate, one rock across the wall with a GAP_W gap whose centre is within reach(speed) of the
block, the distance a body covers in the rock's fall time less DEAD_SECONDS of reaction and camera lag, at
BODY_PX_PER_S; one spawn, one score, one gate at a time, and no aimed rock while a gate is still falling (the aimed
cadence's mirror in aimed_landings holds until the first gate, past the measured window). Any random spawn leaves a block position
within reach that no rock in flight covers (escapable; eight tries, then a plain rock). The fall is two linear segments, ROCK_SPEED at 0 s,
KNEE_SECONDS and RUN_SECONDS: easier than before until the knee, much harder after it.

Phases: ready (READY_SECONDS, the steps hint), play, hit (the hit-stop and the fade of a red block), over (holds).

debug_state: phase, score (rocks dodged), active, hint (the step hint is wanted), speed (px/s, rocks now), survived,
player_xy (the block's centre), threat_xy (the centre of the lowest solid part whose columns overlap the block's
widened by THREAT_SLACK px on each side, else None), rocks (every solid part's centre and width, a tuple of
(x, y, w); a gate is two; for the bots, which see only debug_state) and t_left (seconds of the run left)."""
from __future__ import annotations

import math
import random
from types import MappingProxyType

import numpy as np

from arcade.canvas import Canvas
from arcade.game import Game, GameInfo, icon_from_rows
from arcade.input import Glide, capture_grace
from arcade.juice import PLAYER_COLORS
from arcade.sensed import Sensed
from arcade.sources.actors import TICK, Person, scene
from show.font import CELL_H

RUN_SECONDS = 45.0
PLAYER_W = 6            # the hitbox: unchanged by the figure drawn over it (the Man, below)
PLAYER_H = 8            # rows 50 to 57: a 1 px step changes 16 px
PLAYER_Y = 50
MAN = np.array([[ch == "#" for ch in row] for row in (     # the Burning Man figure (the owner, 2026-10-03): 10x12
    "#...##...#",                                           # at rows 46 to 57, a head apart from the shoulders, arms
    ".#..##..#.",                                           # at 45 degrees to head height, the spine through row 54
    "..#....#..",                                           # (player_xy's centre pixel), the feet on the hitbox's outer
    "...####...",                                           # columns (the bar between them confused people at the
    "....##....",                                           # party, the owner, 2026-10-03). 1 px arms: a three-lens
    "....##....",                                           # review (legibility, iconography, gameplay) chose them over
    "....##....",                                           # 2 px for the Man's proportions; if they vanish on the wall
    "....##....",                                           # at 0.1, thicken.
    "....##....",
    "...#..#...",
    "..#....#..",
    "..#....#..")], dtype=bool)
MAN.flags.writeable = False
MAN_H, MAN_W = MAN.shape
MAN_DX, MAN_DY = (MAN_W - PLAYER_W) // 2, MAN_H - PLAYER_H   # the figure's offset from the hitbox's top left
ROCK_W = 6
ROCK_H = 4
ROCK_SPEED = (20.0, 38.0, 56.0) # px/s at 0 s, at KNEE_SECONDS and at RUN_SECONDS: two linear segments
KNEE_SECONDS = 30.0
SPAWN_EVERY = (1.2, 0.4)        # s between rocks, linear over the run
AIM_EVERY = 3                   # every third rock falls at the block's x at its spawn
AIM_TIGHT_AT = 25.0             # s into the run from when every AIM_TIGHT_EVERY-th rock is aimed
AIM_TIGHT_EVERY = 2
SIZES = {"pebble": (3, 3), "rock": (6, 4), "slab": (12, 4), "beam": (24, 3)}   # (w, h) px of the random rocks
SIZE_FROM = {"pebble": 10.0, "rock": 0.0, "slab": 10.0, "beam": 20.0}           # s into the run a size first comes
SIZE_WEIGHT = {"pebble": 2, "rock": 4, "slab": 2, "beam": 1}
GATE_AFTER = 20.0               # s into the run from when a random spawn may be a gate
GATE_SHARE = 0.25               # of the random spawns after GATE_AFTER
GAP_W = 16                      # px: the gate's gap, the 6 px block with 5 px of slack either side
GAP_MARGIN = 10                 # px the gap keeps from either edge: the far edge needs the body at the zone's rim
GATE_H = 3
DEAD_SECONDS = 0.6              # a guest's reaction plus the camera's lag before the block moves
BODY_PX_PER_S = 87.0            # the block's pace for a body crossing half the mat in a second
REACH_MIN = 8.0                 # px: a gate's gap is never nearer than a step
ESCAPE_MARGIN = 4.0             # px clear on either side of the block an escape must have: a hole of 14, not of 7
ESCAPE_TRIES = 8
HIT_SLACK = 2                   # px each box is shrunk before the overlap test (half on every side)
THREAT_SLACK = 4                # px each side the block's columns are widened by for threat_xy
DODGE_TRAVEL_PX = 12            # a passed rock counts only if the player's x span since its spawn was this
ACTIVE_PX = 3
READY_SECONDS = 2.0
HIT_SECONDS = 0.6
OVER_SECONDS = 2.5
HINT_IDLE_SECONDS = 2.0
SCORE_SCALE = 2
ZONE_LO, ZONE_HI = 0.15, 0.85   # of the mat: the block's whole travel
CAMERA_FPS = 10                 # capture_grace(10): what the player may be missing before the run goes on
SPAWN_Y = -ROCK_H / 2           # a rock enters half in view, so its centre is on the wall
GONE_Y = 60                     # a rock is gone (passed, counted) when its bottom reaches this row: 60 to 63 stay free
ROCK_COLOR = (0, 200, 255)
TINTS = {"pebble": (150, 230, 255), "rock": ROCK_COLOR, "slab": (0, 140, 255), "beam": (0, 255, 140)}
GATE_COLOR = (0, 255, 140)      # cyan, blue, green, white only: red at 0.8 of the light is doubled by the governor
BAR_COLOR = (255, 120, 0)
TEXT_COLOR = (255, 120, 0)
SCORE_COLOR = (255, 255, 255)
SAFE_COLOR = (0, 200, 0)
HIT_COLOR = (255, 0, 0)
EMBER = (120, 0, 0)     # the hit's second half: one step down from HIT_COLOR that crosses all three of the flash
                        # governor's light signals in the same frame, so the burn costs one transition, not three
                        # (a smooth red fade crossed them in three frames and the Man's 1 px arm tips, which also
                        # step on and off with the body, went over the budget of 6 in a second)
READY_LINES = ("STEP SIDE", "TO SIDE")
HINT_TEXT = "STEP!"
GLYPH_H = 7
BAR_RESERVE = 2 * 6 * SCORE_SCALE + 2   # px kept clear at the right of row 0 for a two-digit score and its dark gutter

ICON = icon_from_rows([
    "................",
    "..####....####..",
    "..####....####..",
    "..####....####..",
    "..####....####..",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "......####......",
    "......####......",
    "......####......",
    "......####......",
    "................",
])


def _lerp(pair: tuple[float, float], run_t: float) -> float:
    share = min(1.0, max(0.0, run_t / RUN_SECONDS))
    return pair[0] + (pair[1] - pair[0]) * share


def speed_at(run_t: float) -> float:
    """The rocks' fall in px/s, run_t seconds into the run: ROCK_SPEED[0] to [1] over the first KNEE_SECONDS, [1] to
    [2] over the rest."""
    a, b, c = ROCK_SPEED
    if run_t <= KNEE_SECONDS:
        return a + (b - a) * max(0.0, run_t / KNEE_SECONDS)
    return b + (c - b) * min(1.0, (run_t - KNEE_SECONDS) / (RUN_SECONDS - KNEE_SECONDS))


def aim_every(run_t: float) -> int:
    """Every how-many-th spawn is aimed, run_t seconds into the run."""
    return AIM_TIGHT_EVERY if run_t >= AIM_TIGHT_AT - 1e-9 else AIM_EVERY


def reach(speed: float) -> float:
    """How far (px) the block can get before a rock falling at speed reaches its rows: the fall time less
    DEAD_SECONDS, at BODY_PX_PER_S, never under REACH_MIN."""
    fall = (PLAYER_Y - ROCK_H + HIT_SLACK - SPAWN_Y) / speed
    return max(REACH_MIN, (fall - DEAD_SECONDS) * BODY_PX_PER_S)


def spawn_gap(run_t: float) -> float:
    """Seconds from a spawn to the next one, run_t seconds into the run."""
    return _lerp(SPAWN_EVERY, run_t)


class Rock:
    """A falling rock: x, y its top-left corner (px), w by h; lo, hi the block's left edge extremes since its spawn.
    gap, (left edge, width), makes it a gate: solid on both sides of the gap only (spans)."""

    def __init__(self, x: float, y: float, at: float, w: int = ROCK_W, h: int = ROCK_H, color=ROCK_COLOR,
                 gap: tuple[float, float] | None = None):
        self.x, self.y, self.w, self.h, self.color, self.gap = x, y, w, h, color, gap
        self.lo = self.hi = at

    @property
    def spans(self) -> tuple[tuple[float, float], ...]:
        """(left, right) of every solid part."""
        if self.gap is None:
            return ((self.x, self.x + self.w),)
        gx, gw = self.gap
        return tuple((a, b) for a, b in ((self.x, gx), (gx + gw, self.x + self.w)) if b > a)

    @property
    def travel(self) -> float:
        return self.hi - self.lo


class Dodge(Game):
    info = GameInfo(name="dodge", title="DODGE", verb="DODGE", icon=ICON, needs=frozenset({"pose"}),
                    layouts=frozenset({"128x64"}), players=1, kind="score")
    PHASES = ("ready", "play", "hit", "over")
    CAPTION_KEYS = ("phase", "score", "speed")
    SCENARIOS = MappingProxyType({})     # filled below, once the scripts exist

    def reset(self, size, rng: random.Random, fx) -> None:
        self.w, self.h = size
        self.rng, self.fx = rng, fx
        self.grace = capture_grace(CAMERA_FPS)
        self.glide = Glide(grace=self.grace)
        self.t = 0.0
        self.phase, self.phase_t = "ready", 0.0
        self.run_t = 0.0
        self.rocks: list[Rock] = []
        self.spawn_in = 0.0
        self.spawned = 0
        self.score = 0
        self.survived = False
        self.block_x = (self.w - PLAYER_W) / 2
        self._body: int | None = None           # the id the Glide is following
        self._anchor = math.nan                 # the block x at the last tick counted as input (active)
        self._active = False
        self._idle = 0.0                        # seconds since the block last moved ACTIVE_PX
        self._absent = 0.0                      # seconds with nobody in view
        self._hint = False

    # ----- the tick -----

    def update(self, sensed: Sensed, dt: float) -> None:
        self.t += dt
        self.phase_t += dt
        player = sensed.player
        self._move_block(sensed, player, dt)
        self._absent = 0.0 if player is not None else self._absent + dt
        if self.phase == "ready":
            if self.phase_t >= READY_SECONDS - 1e-9:
                self._set("play")
                self.run_t, self.spawn_in = 0.0, 0.0
        elif self.phase == "play":
            if player is not None or self._absent > self.grace:
                self._step_run(dt)
        elif self.phase == "hit":
            if self.phase_t >= HIT_SECONDS - 1e-9:
                self._to_over()
        self._update_hint(dt)

    def _move_block(self, sensed: Sensed, player, dt: float) -> None:
        """The block follows zone_x through the Glide; a jump to a new body, or the first read, is not input."""
        self._active = False
        if player is not None and player.id != self._body:
            self._body = player.id
            self.glide.reset()
            self._anchor = math.nan
        v = self.glide.update(None if player is None else player.zone_x, sensed.t, sensed.camera_t)
        if v is None:
            return
        share = min(1.0, max(0.0, (v - ZONE_LO) / (ZONE_HI - ZONE_LO)))
        self.block_x = share * (self.w - PLAYER_W)
        if math.isnan(self._anchor):
            self._anchor = self.block_x
        elif abs(self.block_x - self._anchor) >= ACTIVE_PX - 1e-9:
            self._active = True
            self._anchor = self.block_x

    def _set(self, phase: str) -> None:
        self.phase, self.phase_t = phase, 0.0

    def _step_run(self, dt: float) -> None:
        self.run_t += dt
        self.spawn_in -= dt
        while self.spawn_in <= 0.0:
            # No aimed rock while a gate is still falling: the block is in, or heading for, its gap, and a rock
            # at that x would leave no way out of a gap 16 px wide (the Good bot died there 17 times in 20).
            gate_up = any(r.gap is not None and r.y < PLAYER_Y for r in self.rocks)
            if self.spawned % aim_every(self.run_t) == 0 and not gate_up:
                self.spawn_rock(self.block_x)
            else:
                self.spawn_random()
            self.spawn_in += spawn_gap(self.run_t)
        fall = speed_at(self.run_t) * dt
        for rock in self.rocks:
            rock.y += fall
            rock.lo, rock.hi = min(rock.lo, self.block_x), max(rock.hi, self.block_x)
        if any(self._hits(rock) for rock in self.rocks):
            self._hit()
            return
        for rock in [r for r in self.rocks if r.y + r.h >= GONE_Y]:
            self.rocks.remove(rock)
            if rock.travel >= DODGE_TRAVEL_PX - 1e-9:
                self.score += 1
        if self.run_t >= RUN_SECONDS - 1e-9:
            self.survived = True
            self.fx.celebrate(SAFE_COLOR)
            self._to_over()

    def spawn_rock(self, x: float, w: int = ROCK_W, h: int = ROCK_H, color=ROCK_COLOR,
                   gap: tuple[float, float] | None = None) -> None:
        """A rock at x (its left edge), w by h, just above the wall; it remembers where the block is now."""
        self.rocks.append(Rock(x, -h / 2, self.block_x, w, h, color, gap))
        self.spawned += 1

    def spawn_gate(self, gap_x: float | None = None) -> bool:
        """One rock across the wall with a GAP_W gap at gap_x (its left edge); None puts the gap's centre within
        reach of the block's, GAP_MARGIN from either edge, where no rock still falling covers it (ESCAPE_TRIES
        draws; none clear: no gate, False)."""
        if gap_x is None:
            centre = self.block_x + PLAYER_W / 2
            r = reach(speed_at(self.run_t))
            lo = max(float(GAP_MARGIN), centre - r - GAP_W / 2)
            hi = min(float(self.w - GAP_MARGIN - GAP_W), centre + r - GAP_W / 2)
            falling = self._falling_spans()
            for _ in range(ESCAPE_TRIES):
                gap_x = self.rng.uniform(lo, max(lo, hi))
                if not any(c > gap_x and a < gap_x + GAP_W for a, c in falling):
                    break
            else:
                return False
        self.spawn_rock(0.0, w=self.w, h=GATE_H, color=GATE_COLOR, gap=(gap_x, GAP_W))
        return True

    def spawn_random(self) -> None:
        """A random rock of a size the run has reached (SIZE_FROM, SIZE_WEIGHT), or from GATE_AFTER a gate for
        GATE_SHARE of them; a rock lands where the block still has an escape within reach (escapable), else, after
        ESCAPE_TRIES, a plain rock, which a step always clears."""
        t = self.run_t
        gate_up = any(r.gap is not None and r.y < PLAYER_Y for r in self.rocks)
        if t >= GATE_AFTER - 1e-9 and not gate_up and self.rng.random() < GATE_SHARE and self.spawn_gate():
            return                          # one gate at a time: two gaps 0.7 s apart is two finds, not one
        names = [n for n in SIZES if t >= SIZE_FROM[n] - 1e-9]
        name = self.rng.choices(names, [SIZE_WEIGHT[n] for n in names])[0]
        w, h = SIZES[name]
        for _ in range(ESCAPE_TRIES):
            x = self.rng.uniform(0.0, self.w - w)
            if self.escapable(x, w):
                break
        else:
            name, (w, h) = "rock", SIZES["rock"]
            x = self.rng.uniform(0.0, self.w - w)
        self.spawn_rock(x, w=w, h=h, color=TINTS[name])

    def _falling_spans(self) -> list[tuple[float, float]]:
        """The solid parts of every rock still above the block's rows."""
        return [span for rock in self.rocks if rock.y < PLAYER_Y for span in rock.spans]

    def escapable(self, x: float, w: int, gap: tuple[float, float] | None = None) -> bool:
        """Whether some block position within reach of the block's (on the wall), ESCAPE_MARGIN clear on either
        side, is clear of a rock at x, w wide, with gap, and of every rock still above the block's rows."""
        r, m = reach(speed_at(self.run_t)), ESCAPE_MARGIN
        spans = list(Rock(x, 0.0, 0.0, w, ROCK_H, gap=gap).spans) + self._falling_spans()
        lo, hi = max(0, math.ceil(self.block_x - r)), min(self.w - PLAYER_W, math.floor(self.block_x + r))
        for b in range(lo, hi + 1):
            if not any(c > b - m and a < b + PLAYER_W + m for a, c in spans):
                return True
        return False

    def _hits(self, rock: Rock) -> bool:
        """Overlap of the block with a solid part of the rock, each box shrunk by HIT_SLACK in all (half a slack on
        every side)."""
        s = HIT_SLACK
        if not (rock.y + rock.h - s / 2 > PLAYER_Y + s / 2 and PLAYER_Y + PLAYER_H - s / 2 > rock.y + s / 2):
            return False
        return any(c - s / 2 > self.block_x + s / 2 and self.block_x + PLAYER_W - s / 2 > a + s / 2
                   for a, c in rock.spans)

    def _hit(self) -> None:
        self._set("hit")
        self.fx.freeze(0.2)
        self.fx.shake(3, 0.3)

    def _to_over(self) -> None:
        if self.score > 0:
            self.scores.record(self.score)          # once, and only for a run that counted a dodge (C41)
        self._set("over")

    def _update_hint(self, dt: float) -> None:
        self._idle = 0.0 if self._active else self._idle + dt
        if self._active or self.phase not in ("ready", "play"):
            self._hint = False
        elif self._idle >= HINT_IDLE_SECONDS - 1e-9:
            self._hint = True

    def done(self) -> bool:
        return self.phase == "over" and self.phase_t >= OVER_SECONDS - 1e-9

    # ----- drawing -----

    def draw(self, canvas: Canvas) -> None:
        w = self.w
        for rock in self.rocks:
            for a, c in rock.spans:
                canvas.fill_rect(a, rock.y, c - a, rock.h, rock.color)
        left = round((w - BAR_RESERVE) * self._t_left() / RUN_SECONDS)
        if left > 0:
            canvas.fill_rect(0, 0, left, 1, BAR_COLOR)
        if self.phase != "over" or self.survived:
            canvas.blit(MAN, self.block_x - MAN_DX, PLAYER_Y - MAN_DY, self._block_color())   # the canvas rounds x
        text = str(self.score)
        x0 = w - canvas.text_width(text, SCORE_SCALE)
        canvas.fill_rect(x0 - 1, 0, w - x0 + 1, CELL_H * SCORE_SCALE + 2, (0, 0, 0))    # the score's dark gutter
        canvas.text(x0, 1, text, SCORE_COLOR, SCORE_SCALE)
        if self.phase == "ready":
            top = round(self.h * 0.4) - (len(READY_LINES) * (GLYPH_H + 2) - 2) // 2
            for k, line in enumerate(READY_LINES):
                width = canvas.text_width(line) - 1
                canvas.text((w - width) // 2, top + k * (GLYPH_H + 2), line, TEXT_COLOR)
        elif self._hint and self.phase == "play":
            width = canvas.text_width(HINT_TEXT) - 1
            x = min(max(0, round(self.block_x + PLAYER_W / 2 - width / 2)), w - width)
            canvas.text(x, PLAYER_Y - GLYPH_H - 5, HINT_TEXT, TEXT_COLOR)
        if self.phase == "over" and self.survived:
            width = canvas.text_width("SAFE!", SCORE_SCALE) - SCORE_SCALE
            canvas.text((w - width) // 2, round(self.h * 0.4) - CELL_H, "SAFE!", SAFE_COLOR, SCORE_SCALE)

    def _block_color(self):
        """Amber; from a hit, HIT_COLOR for the first half of HIT_SECONDS, EMBER for the second, black at over."""
        if self.phase in ("hit", "over") and not self.survived:
            if self.phase == "over":
                return (0, 0, 0)
            return HIT_COLOR if self.phase_t < HIT_SECONDS / 2 - 1e-9 else EMBER
        return PLAYER_COLORS[0]

    def _t_left(self) -> float:
        return max(0.0, RUN_SECONDS - self.run_t)

    def _threat(self):
        """The lowest solid part (rock, left, right) whose columns overlap the block's widened by THREAT_SLACK."""
        lo, hi = self.block_x - THREAT_SLACK, self.block_x + PLAYER_W + THREAT_SLACK
        near = [(r, a, c) for r in self.rocks for a, c in r.spans if a < hi and c > lo]
        return max(near, key=lambda t: t[0].y, default=None)

    def debug_state(self) -> dict:
        threat = self._threat()
        return {"phase": self.phase, "score": self.score, "active": bool(self._active),
                "hint": bool(self._hint), "speed": round(speed_at(self.run_t), 2), "survived": bool(self.survived),
                "player_xy": (round(self.block_x + PLAYER_W / 2, 2), PLAYER_Y + PLAYER_H / 2),
                "threat_xy": None if threat is None
                else (round((threat[1] + threat[2]) / 2, 2), round(threat[0].y + threat[0].h / 2, 2)),
                "rocks": tuple((round((a + c) / 2, 1), round(r.y + r.h / 2, 1), round(c - a, 1))
                               for r in self.rocks for a, c in r.spans),
                "t_left": round(self._t_left(), 1)}


# ----- scripts -----

CANONICAL_SECONDS = 55.0
RAISE_AT = 4.5
STEP_SECONDS = 0.5              # the scripted body's sidestep across half the mat
AWAY = 0.2                      # of the mat: a landing this close to where a rock was aimed is a hit


def cam_x(zone_x: float) -> float:
    """The camera x a Person stands at to be at zone_x of the mat (the default calibration's zone)."""
    from arcade.calibration import Calibration

    x0, _, x1, _ = Calibration().zone
    return x0 + zone_x * (x1 - x0)


def aimed_landings(start: float, end: float) -> list[tuple[float, float, float]]:
    """(spawn, first, last) times of every aimed rock of a run whose play starts at `start`, spawned before `end`:
    when it spawns, and the span during which its box can overlap the block's rows. The game's own arithmetic."""
    born, run_t, spawn_in, n = [], 0.0, 0.0, 0
    while start + run_t < end:
        run_t += TICK
        spawn_in -= TICK
        while spawn_in <= 0.0:
            if n % aim_every(run_t) == 0:
                born.append(run_t)
            n += 1
            spawn_in += spawn_gap(run_t)
    out = []
    for run_t in born:
        y, first, spawn = SPAWN_Y, None, run_t
        while y + ROCK_H < GONE_Y:
            run_t += TICK
            y += speed_at(run_t) * TICK
            if first is None and y > PLAYER_Y - ROCK_H + HIT_SLACK:
                first = run_t
        out.append((start + spawn, start + first, start + run_t))
    return out


def canonical():
    """The wall empty for 2 s, then one player walks up, raises a hand at 4.5 s (the game launches), sweeps the whole
    mat while the rocks are still on their way, then steps out from under each aimed rock; CANONICAL_SECONDS."""
    person = Person(cam_x(0.5), id=1).arrive(2.0).raise_hand(RAISE_AT, 0.5)
    path: list[tuple[float, float, float, float]] = []      # (from t, to t, from x, to x) of the walks, in order

    def pos(t: float) -> float:
        x = 0.5
        for t0, t1, xa, xb in path:
            x = xb if t >= t1 else (xa + (xb - xa) * (t - t0) / (t1 - t0) if t >= t0 else x)
        return x

    def walk(x: float, seconds: float, at: float) -> float:
        path.append((at, at + seconds, pos(at), x))
        person.walk(x, seconds, at=at)
        return at + seconds

    t = walk(0.03, 0.8, 5.0)
    t = walk(0.97, 1.6, t)
    t = walk(0.2, 1.0, t)
    for spawn, first, last in aimed_landings(RAISE_AT + READY_SECONDS, CANONICAL_SECONDS):
        aimed_at = pos(spawn)
        span = [first - 0.2 + k * TICK for k in range(round((last - first + 0.4) / TICK) + 1)]
        if all(abs(pos(u) - aimed_at) >= AWAY for u in span):
            continue
        start = max(spawn + 0.1, t)
        if start + STEP_SECONDS < first - 0.1:
            t = walk(0.75 if aimed_at < 0.5 else 0.25, STEP_SECONDS, start)
    return scene(persons=[person], ticks=round(CANONICAL_SECONDS / TICK))


def idle_body(body_id: int = 1, seconds: float = 60.0):
    """One body standing, hands down, for 60 s (body_id and seconds let tests vary the noise and the length)."""
    return scene(persons=[Person(cam_x(0.3), id=body_id)], ticks=round(seconds / TICK))


def nobody():
    return scene(ticks=900)


def solo():
    """One player who walks up at 0.5 s, steps aside once at 1 s, and then stands until the first aimed rock finds
    them: a scripted run to a hit, 30 s."""
    person = Person(cam_x(0.5), id=1).arrive(0.5).walk(cam_x(0.4), 0.5, at=1.0)
    return scene(persons=[person], ticks=round(30 / TICK))


Dodge.SCENARIOS = MappingProxyType({"canonical": canonical, "idle_body": idle_body, "nobody": nobody,
                                    "solo": solo})
GAME = Dodge
