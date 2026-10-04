"""Paint (spec 8 row 3; pose and blobs): lights paint. Each in-zone light leaves a stroke in its colour on the paper,
drawn as segments between the tracker's positions; a lifted wrist paints in its seat's colour when nobody has had a
light for LIGHT_QUIET_SECONDS; strokes fade to FADE_FLOOR over FADE_SECONDS, then go off; after PAINT_SECONDS the
picture freezes in a white frame for GALLERY_SECONDS, then the game is done. A toy: no score, no best.

The paper is its own buffer (h - FREE_ROWS rows at full colour, with the time each pixel was painted) blitted at the
top of the wall, so the runner's marker rows at the bottom are never painted. A tracked light (id >= 0) continues its
stroke while its step stays under MAX_SEGMENT_PX; a stroke unseen for LOST_SECONDS has ended, and a new id first seen
within LINK_PX of a stroke that ended under LOST_SECONDS ago continues it (the tracker re-identifying a light). An
untracked light (id -1) stamps a dot per capture. Brushes move on fresh captures only. A seat's wrist reads through a
Cursor (hand hysteresis, a grace over dropouts): the pen is down while its v is under PEN_V, and its x is the body's
zone_x spread by ARM_SPAN of the reach box's u. A new body in a seat starts its own stroke.

debug_state: phase, painted (the share of paper pixels showing, 3 decimals), strokes (live), lights (on the last
capture), brush_xy (player 1's wrist brush, the stamped pixel, None when it did not paint on the last capture),
light_xy (the first light's, or None), active (a brush painted on the last capture or a light was seen), brush_px
and hint (the hint is wanted: nothing painted for HINT_IDLE_SECONDS)."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np

from arcade.canvas import Canvas
from arcade.game import Game, GameInfo, icon_from_rows
from arcade.input import Cursor
from arcade.juice import PLAYER_COLORS
from arcade.sensed import Sensed
from arcade.sources.actors import TICK, Person, moving_blob, scene
from show.font import CELL_H

PAINT_SECONDS = 60.0
GALLERY_SECONDS = 5.0
FADE_SECONDS = 20.0
FADE_FLOOR = 0.56           # 255 x 0.56 = 143: a fading pixel's top channel never falls under the dim level 140
FREE_ROWS = 4               # the bottom rows are the runner's (the marker, the echoes): never painted
BRUSH_PX = (2, 3)           # one drawn per game by the rng (Q166)
RING_R = 3                  # a 1 px white ring round each brush that painted on the last capture
MAX_SEGMENT_PX = 32         # a longer step is a new stroke, not a line across the wall
LOST_SECONDS = 0.3          # a stroke unseen this long has ended
LINK_PX = 12                # a new id this close to a stroke ended under LOST_SECONDS ago continues it
LIGHT_QUIET_SECONDS = 1.0   # the wrists paint only after no light has been seen for this long
PEN_V = 0.8                 # the wrist's reach-box v under this is pen down (a hanging hand reads 1.0)
ARM_SPAN = 0.5              # the brush's x is zone_x spread by this much of the reach box's u about its middle
WHITE_BELOW_S = 0.25        # a light with less saturation than this paints white
WIN_PAINTED = 0.22          # the bots' win: this share of the paper showing at the gallery (Q169). Measured on
                            # 2026-10-03 over the oracle's 20 seeds: Good shows 0.30 to 0.37, Lazy 0.20 to 0.22 with
                            # the 2 px brush and 0.22 to 0.23 with the 3 px, so Lazy's win hangs on the rng's brush
FRAME_COLOR = (255, 255, 255)
RING_COLOR = (255, 255, 255)
WHITE = (255, 255, 255)
CURSOR_GRACE = 0.25         # the Cursor holds a wrist this long over a dropout (input.Cursor's default)
HINT_TEXT = "HAND UP = PAINT"
HINT_IDLE_SECONDS = 2.0     # nothing painted this long: the hint fades in (a still body sees it within 3 s)
HINT_FADE = 0.3             # s in and out: never a blink
HINT_COLOR = (255, 160, 0)

ICON = icon_from_rows([
    "................",
    "................",
    "................",
    "................",
    "....###.........",
    "...##.##........",
    "..##...##.......",
    "##.....##....##.",
    "##......##..##..",
    ".........####...",
    "..........##....",
    "................",
    "................",
    "................",
    "................",
    "................",
])


def _clamp01(v: float) -> float:
    return 0.0 if v < 0.0 else 1.0 if v > 1.0 else v


def _channel(v) -> float:
    """A colour channel as a float in 0..255: NaN and None are 0, infinities and out-of-range values clamp (Q158)."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(f):
        return 0.0
    return min(255.0, max(0.0, f))


def light_color(color) -> tuple[int, int, int]:
    """A light's paint: each channel clamped to 0..255 and scaled so the largest is 255; white when its saturation
    ((max - min) / max) is under WHITE_BELOW_S or it is black."""
    try:
        r, g, b = (_channel(c) for c in color)
    except (TypeError, ValueError):
        return WHITE
    top, low = max(r, g, b), min(r, g, b)
    if top <= 0.0 or (top - low) / top < WHITE_BELOW_S:
        return WHITE
    scale = 255.0 / top
    return tuple(int(math.floor(c * scale + 0.5)) for c in (r, g, b))


def stamp_segment(paper: np.ndarray, painted_at: np.ndarray, a, b, color, brush_px: int, t: float) -> int:
    """Stamp the brush (a square of brush_px) at every pixel from a to b (wall px, floats) on the paper, clipped to
    it: paper takes color and painted_at takes t there. Returns the pixels stamped. Pure: nothing else is read."""
    h, w = painted_at.shape
    (x0, y0), (x1, y1) = a, b
    if not all(math.isfinite(v) for v in (x0, y0, x1, y1)):
        return 0
    steps = max(1, int(math.ceil(max(abs(x1 - x0), abs(y1 - y0)))))
    if steps > 4 * (w + h):                                # a segment from nowhere to nowhere: nothing (spec 7.4)
        return 0
    us = np.linspace(0.0, 1.0, steps + 1)
    cx = np.floor(x0 + (x1 - x0) * us + 0.5).astype(int)
    cy = np.floor(y0 + (y1 - y0) * us + 0.5).astype(int)
    d = max(1, int(brush_px))
    offs = np.arange(-((d - 1) // 2), -((d - 1) // 2) + d)
    xs = (cx[:, None, None] + offs[None, :, None] + 0 * offs[None, None, :]).ravel()
    ys = (cy[:, None, None] + 0 * offs[None, :, None] + offs[None, None, :]).ravel()
    keep = (xs >= 0) & (xs < w) & (ys >= 0) & (ys < h)
    if not keep.any():
        return 0
    flat = np.unique(ys[keep] * w + xs[keep])
    paper.reshape(-1, 3)[flat] = np.array(color, float)
    painted_at.reshape(-1)[flat] = t
    return int(flat.size)


def _stamp_px(x: float, y: float) -> tuple[int, int]:
    """The pixel a brush at (x, y) stamps its centre on, as stamp_segment rounds."""
    return int(math.floor(x + 0.5)), int(math.floor(y + 0.5))


@dataclass
class _Stroke:
    x: float
    y: float
    seen: float             # paper time of the last point


class Paint(Game):
    info = GameInfo(name="paint", title="PAINT", verb="PAINT", icon=ICON, needs=frozenset({"pose", "blobs"}),
                    layouts=frozenset({"128x64"}), players=2, exit_gesture=False, kind="toy",
                    abandon_seconds=45.0)
    PHASES = ("paint", "gallery")
    CAPTION_KEYS = ("phase", "painted", "lights")

    def reset(self, size, rng: random.Random, fx) -> None:
        self.w, self.h = int(size[0]), int(size[1])
        self.ph = max(1, self.h - FREE_ROWS)
        self.paper = np.zeros((self.ph, self.w, 3), float)
        self.painted_at = np.full((self.ph, self.w), np.nan)
        self.brush_px = rng.choice(BRUSH_PX)
        self.t = 0.0                    # game time
        self.paper_t = 0.0              # the paper's clock: it stops in the gallery, so the fade stops with it
        self.phase, self.phase_t = "paint", 0.0
        self.strokes: dict[tuple, _Stroke] = {}
        self.light_seen_t = -math.inf
        self.painted_t = 0.0            # paper time of the last stamp (the hint's clock)
        self.lights = 0
        self.light_xy: tuple[int, int] | None = None
        self.brush_xy: tuple[int, int] | None = None
        self.cursors = [Cursor(CURSOR_GRACE), Cursor(CURSOR_GRACE)]
        self.seat_ids: list[int | None] = [None, None]
        self.rings: list[tuple[float, float]] = []
        self.active = False
        self.hint_level = 0.0

    # ----- update -----

    def update(self, sensed: Sensed, dt: float) -> None:
        self.t += dt
        if self.phase == "gallery":
            self.phase_t += dt
            return
        self.paper_t += dt
        if sensed.camera_fresh:
            self._capture(sensed)
        target = 1.0 if self._idle() else 0.0
        step = dt / HINT_FADE if HINT_FADE > 0 else 1.0
        self.hint_level = (min(target, self.hint_level + step) if target > self.hint_level
                           else max(target, self.hint_level - step))
        if self.t >= PAINT_SECONDS - 1e-9:
            self.phase, self.phase_t = "gallery", 0.0
            self.rings, self.active = [], False
            self.brush_xy = self.light_xy = None
            self.hint_level = 0.0

    def _idle(self) -> bool:
        return self.paper_t - self.painted_t >= HINT_IDLE_SECONDS - 1e-9

    def _capture(self, sensed: Sensed) -> None:
        pt = self.paper_t
        self.rings, self.active = [], False
        self.light_xy = self.brush_xy = None
        blobs = sensed.blobs
        self.lights = len(blobs)
        if blobs:
            self.light_seen_t, self.active = pt, True
        present = {("light", b.id) for b in blobs if b.id >= 0}
        for blob in blobs:
            x, y = blob.zone_x * (self.w - 1), blob.zone_y * (self.ph - 1)
            color = light_color(blob.color)
            if blob.id >= 0:
                key = ("light", blob.id)
                stroke = self.strokes.get(key)
                if stroke is None:
                    stroke = self._relink(x, y, pt, present)
                self._continue(key, stroke, x, y, color, pt)
            else:
                self._stamp((x, y), (x, y), color, pt)
            if self.light_xy is None:
                self.light_xy = _stamp_px(x, y)
            self.rings.append((x, y))
        for key in [k for k, s in self.strokes.items() if k[0] == "light" and pt - s.seen > 2 * LOST_SECONDS]:
            del self.strokes[key]
        quiet = pt - self.light_seen_t >= LIGHT_QUIET_SECONDS - 1e-9
        for seat, body in enumerate((sensed.player, sensed.player2)):
            key = ("seat", seat)
            body_id = None if body is None else body.id
            if body_id != self.seat_ids[seat]:
                self.seat_ids[seat] = body_id
                self.cursors[seat] = Cursor(CURSOR_GRACE)
                self.strokes.pop(key, None)
            uv = self.cursors[seat].update(body, self.t)
            if body is None or not quiet or uv is None or uv[1] >= PEN_V:
                self.strokes.pop(key, None)                 # a resting wrist lifts the brush
                continue
            u, v = uv
            x = _clamp01(body.zone_x + ARM_SPAN * (u - 0.5)) * (self.w - 1)
            y = v / PEN_V * (self.ph - 1)
            self._continue(key, self.strokes.get(key), x, y, PLAYER_COLORS[seat], pt)
            self.rings.append((x, y))
            self.active = True
            if seat == 0:
                self.brush_xy = _stamp_px(x, y)

    def _relink(self, x: float, y: float, pt: float, present: set) -> _Stroke | None:
        """The nearest light stroke within LINK_PX whose id is not in this capture and that was seen within the link
        window, taken over by the new id (its old key goes); None when there is none."""
        best, best_d = None, LINK_PX
        for key, stroke in self.strokes.items():
            if key[0] != "light" or key in present or pt - stroke.seen > 2 * LOST_SECONDS:
                continue
            d = math.hypot(x - stroke.x, y - stroke.y)
            if d <= best_d:
                best, best_d = key, d
        if best is None:
            return None
        return self.strokes.pop(best)

    def _continue(self, key: tuple, stroke: _Stroke | None, x: float, y: float, color, pt: float) -> None:
        if stroke is None or math.hypot(x - stroke.x, y - stroke.y) > MAX_SEGMENT_PX:
            self._stamp((x, y), (x, y), color, pt)
        else:
            self._stamp((stroke.x, stroke.y), (x, y), color, pt)
        self.strokes[key] = _Stroke(x, y, pt)

    def _stamp(self, a, b, color, pt: float) -> None:
        if stamp_segment(self.paper, self.painted_at, a, b, color, self.brush_px, pt):
            self.painted_t = pt

    # ----- draw -----

    def _showing(self) -> np.ndarray:
        """The paper as it shows: each pixel's colour times its fade factor, 0 once FADE_SECONDS old or unpainted."""
        age = self.paper_t - self.painted_at
        with np.errstate(invalid="ignore"):
            factor = 1.0 - (1.0 - FADE_FLOOR) * age / FADE_SECONDS
            factor = np.where(np.isfinite(age) & (age < FADE_SECONDS), factor, 0.0)
        return self.paper * factor[:, :, None]

    def _lit(self) -> np.ndarray:
        age = self.paper_t - self.painted_at
        with np.errstate(invalid="ignore"):
            return np.isfinite(age) & (age < FADE_SECONDS)

    def draw(self, canvas: Canvas) -> None:
        shown = self._showing()
        if self.phase == "paint":
            for x, y in self.rings:
                _ring(shown, x, y, RING_R, RING_COLOR)
        canvas.blit_rgb(shown, 0, 0)
        if self.phase == "gallery":
            canvas.rect(0, 0, self.w, self.ph, FRAME_COLOR)
            return
        if self.hint_level > 0.0 and self.ph >= CELL_H + 2:
            color = tuple(int(c * self.hint_level) for c in HINT_COLOR)
            if any(color):
                x = (self.w - canvas.text_width(HINT_TEXT)) // 2
                canvas.text(x, (self.ph - CELL_H) // 2, HINT_TEXT, color)

    def done(self) -> bool:
        return self.phase == "gallery" and self.phase_t >= GALLERY_SECONDS - 1e-9

    def debug_state(self) -> dict:
        live = sum(1 for s in self.strokes.values() if self.paper_t - s.seen <= LOST_SECONDS)
        return {"phase": self.phase, "painted": round(float(self._lit().mean()), 3), "strokes": live,
                "lights": self.lights, "brush_xy": self.brush_xy, "light_xy": self.light_xy,
                "active": bool(self.active), "brush_px": int(self.brush_px),
                "hint": bool(self.phase == "paint" and self._idle())}


def _ring(rgb: np.ndarray, cx: float, cy: float, r: int, color) -> None:
    """A 1 px ring of radius r at (cx, cy) on an (h, w, 3) buffer, clipped to it (as Canvas draws one)."""
    h, w = rgb.shape[:2]
    cx, cy = _stamp_px(cx, cy)
    x0, y0, x1, y1 = max(cx - r, 0), max(cy - r, 0), min(cx + r + 1, w), min(cy + r + 1, h)
    if x0 >= x1 or y0 >= y1:
        return
    yy, xx = np.ogrid[y0:y1, x0:x1]
    d2 = (xx - cx) ** 2 + (yy - cy) ** 2
    mask = (d2 <= (r + 0.5) ** 2) & (d2 >= (r - 0.5) ** 2)
    rgb[y0:y1, x0:x1][mask] = np.array(color, float)


GAME = Paint


# ----- scripts -----

CANONICAL_SECONDS = 72.0
RAISE_AT = 4.5
DUO_SECONDS = 65.0


def cam_x(zone_x: float) -> float:
    """The camera x a Person stands at to be at zone_x of the mat (the default calibration's zone)."""
    from arcade.calibration import Calibration

    x0, _, x1, _ = Calibration().zone
    return x0 + zone_x * (x1 - x0)


def sweep(person: Person, start: float, end: float, hand: str = "right", half: float = 0.5) -> None:
    """The wrist sweeps v 0.1 to 0.7 and back about once a second from start to end."""
    t = start
    while t < end - 1e-9:
        person.wrist(hand, 0.1, 0.7, half, at=t)
        person.wrist(hand, 0.7, 0.1, half, at=t + half)
        t += 2 * half


def canonical():
    """The wall empty for 2 s, one player walks up at zone x 0.3, raises a hand at 4.5 s (the game launches); from
    6 s the right wrist sweeps the paper's height about once a second while the body walks zone x 0.3 to 0.7 and
    back every 8 s (inside the measured 20 s); from 13 s a tracked light crosses the zone for 4 s (the wrists rest
    while it shows); 72 s, into the gallery."""
    person = Person(cam_x(0.3), id=1).arrive(2.0).raise_hand(RAISE_AT, 0.5)
    t = 6.0
    while t < CANONICAL_SECONDS:
        person.walk(cam_x(0.7), 8.0, at=t)
        person.walk(cam_x(0.3), 8.0, at=t + 8.0)
        t += 16.0
    sweep(person, 6.0, CANONICAL_SECONDS)
    light = moving_blob(cam_x(0.25), 0.35, cam_x(0.75), 0.6, seconds=4.0, start=13.0, color=(0, 255, 0), id=1)
    return scene(persons=[person], blobs=[light], ticks=round(CANONICAL_SECONDS / TICK))


def idle_body(body_id: int = 1, seconds: float = 60.0):
    """One body standing, hands down, for 60 s (body_id and seconds let tests vary the noise and the length)."""
    return scene(persons=[Person(cam_x(0.3), id=body_id)], ticks=round(seconds / TICK))


def nobody():
    return scene(ticks=900)


def duo():
    """Two bodies from the start, both seats' wrists sweeping (the nearer, player 1, paints amber; the other blue);
    65 s, into the gallery."""
    a = Person(cam_x(0.3), height=0.62, id=1)
    b = Person(cam_x(0.7), id=2)
    sweep(a, 0.0, DUO_SECONDS)
    sweep(b, 0.0, DUO_SECONDS, hand="left")
    return scene(persons=[a, b], ticks=round(DUO_SECONDS / TICK))


Paint.SCENARIOS = MappingProxyType({"canonical": canonical, "idle_body": idle_body, "nobody": nobody, "duo": duo})
