"""The effects toolkit (spec 8.1): one Juice per launch, runner-owned, seeded, passed to the game's reset().

A game calls shake, flash, burst, pop, banner, freeze, celebrate and echo from update(); the runner draws the
effects after the game's draw (render), advances them once a tick (update) and skips the game's update while
frozen. Shake, flash and bursts each keep the governor's flash rule by themselves (spec 7.6, it04 N11), whatever
the colour, saturated red included, which the governor counts three ways:

- shake jumps the frame from side to side along one axis, and the offset changes at most once every SHAKE_STEP
  (0.25 s). A jump changes each pixel once whatever the picture, so no pixel changes more than 4 times a second
  under a shake, under the 6 of the governor's budget. (A smooth shake would sweep fine detail across a pixel
  many times a cycle.)
- flash adds its colour for its seconds and stops: one rise and one fall. The next starts FLASH_GAP (0.5 s) after
  one ends, so no pixel changes more than 4 times a second. (A red flash fading over several frames counts up to
  three falls, one per way, and at 2 a second the governor would hold the whole wall.)
- burst particles all fly at BURST_SPEED for BURST_LIFE, so each passes a pixel once; a burst whose origin is
  within BURST_NEAR of one accepted in the last BURST_GAP (0.5 s) is dropped, so no pixel sees more than two
  bursts a second. That is 4 changes for most pixels; a few by the origin, which one particle takes two frames
  to cross or two cross in turn, reach the governor's 6 and no more.

Banner text, pops and effects together are the game's to pace: a banner whose text changes every tick, a pop
every tick, or bursts over a flash can flash a small part of the wall. The governor runs after all of it and
holds what goes over.

Numbers from a game are taken as they come: a NaN, an infinity, a negative duration or anything that is not a
number makes that call do nothing (and return False where it returns a bool). Nothing here raises into a game.
"""
from __future__ import annotations

import math
import random

import numpy as np

from arcade.canvas import Canvas, _c
from arcade.look import is_real
from arcade.sensed import Body
from show.font import CELL_H

MAX_PARTICLES = 96
SHAKE_STEP = 0.25        # seconds between two changes of the shake's offset: 4 a second at most
SHAKE_MAX = 8            # pixels
FLASH_GAP = 0.5          # seconds from the end of one flash to the start of the next
BURST_SPEED = 30.0       # px/s, every particle
BURST_LIFE = 0.5         # seconds: a burst reaches BURST_SPEED * BURST_LIFE = 15 px
BURST_GAP = 0.5          # seconds before another burst may start near an accepted one
BURST_NEAR = 32          # px: two particle discs of 15 px whose origins are this far apart never meet
BURST_N = 12             # particles in a burst by default
POP_RISE = 6             # px over POP_SECONDS
POP_SECONDS = 0.8
MAX_POPS = 8
ECHO_SECONDS = 0.25
ECHOES = {               # 3x3 glyphs drawn over a player's marker
    "up": (".#.", "###", "..."),
    "down": ("...", "###", ".#."),
    "hit": ("#.#", ".#.", "#.#"),
    "ok": (".#.", "###", ".#."),
}
PLAYER_COLORS = ((255, 120, 0), (0, 160, 255))    # player 1 amber, player 2 blue: low channels at 0 or near
CELEBRATE_GAP = 0.5      # seconds between celebrate's two waves


def _number(v) -> float | None:
    """v as a finite float, else None."""
    if not is_real(v):
        return None
    try:
        v = float(v)
    except OverflowError:
        return None
    return v if math.isfinite(v) else None


def _seconds(v) -> float | None:
    v = _number(v)
    return v if v is not None and v >= 0.0 else None


def marker_x(body: Body, width: int) -> int:
    """The left column of a player's 2 px marker on the bottom row: zone_x across the wall."""
    return max(0, min(width - 2, math.floor(body.zone_x * (width - 2) + 0.5)))


class Juice:
    """Effects for one launch, timed by update(dt). rng is the launch's random.Random (the shake's axis and the
    bursts' angles); size is the wall's (width, height), for celebrate. debug_state() gives the fx_* keys the
    runner merges into state()."""

    def __init__(self, rng: random.Random, size: tuple[int, int] = (128, 32)):
        self.rng, self.size = rng, size
        self.t = 0.0
        # shake: jumps of alternating sign whose size decays linearly from amp over [start, start + length)
        self._axis, self._sign = 0, 1
        self._amp, self._start, self._length = 0.0, 0.0, 0.0
        self._offset = (0, 0)
        self._moved = -math.inf                                      # when the offset last changed
        self._flash_color = (0, 0, 0)
        self._flash_start, self._flash_seconds = -math.inf, 0.0
        self._flash_end = -math.inf
        self._pos = np.zeros((MAX_PARTICLES, 2))
        self._vel = np.zeros((MAX_PARTICLES, 2))
        self._rgb = np.zeros((MAX_PARTICLES, 3))
        self._born = np.full(MAX_PARTICLES, -math.inf)
        self._next = 0
        self._bursts: list[tuple[float, float, float]] = []         # (t, x, y) of accepted bursts
        self._pops: list[tuple[float, str, float, float, tuple]] = []
        self._banner: tuple[str, float] | None = None               # (text, until)
        self._freeze_until = -math.inf
        self._waves: list[tuple[float, tuple]] = []                  # celebrate's second waves: (at, colour)
        self._echoes: dict[int, tuple[str, float]] = {}              # player -> (kind, until)

    # ----- what a game calls -----

    def shake(self, px, seconds) -> None:
        """Shake the frame by up to px pixels (at most SHAKE_MAX), decaying to 0 over seconds: the frame jumps to
        alternate sides at most every SHAKE_STEP. A shake while one runs restarts it if it is at least as big."""
        px, seconds = _seconds(px), _seconds(seconds)
        if px is None or seconds is None or px == 0.0 or seconds == 0.0:
            return
        px = min(px, float(SHAKE_MAX))
        if self._amplitude() == 0.0 and self._offset == (0, 0):
            self._axis, self._sign = self.rng.randrange(2), self.rng.choice((-1, 1))
        elif px < self._amplitude():
            return
        self._amp, self._start, self._length = px, self.t, seconds

    def flash(self, color, seconds=0.2) -> bool:
        """Add color to the whole frame for seconds, then stop: one rise and one fall. False (and nothing) while a
        flash shows or under FLASH_GAP after one ended."""
        seconds = _seconds(seconds)
        if seconds is None or seconds == 0.0 or self.t - self._flash_end < FLASH_GAP - 1e-9:
            return False
        try:
            self._flash_color = _c(color)
        except (TypeError, ValueError):
            return False
        self._flash_start, self._flash_seconds, self._flash_end = self.t, seconds, self.t + seconds
        return True

    def burst(self, x, y, color, n=BURST_N) -> bool:
        """n particles (1 to MAX_PARTICLES) from (x, y) in wall pixels, evenly spread round the circle, fading over
        BURST_LIFE. The pool keeps the newest MAX_PARTICLES. False (and nothing) for a burst within BURST_NEAR of
        one accepted in the last BURST_GAP."""
        x, y = _number(x), _number(y)
        if x is None or y is None or isinstance(n, bool) or not isinstance(n, (int, np.integer)):
            return False
        try:
            rgb = _c(color)
        except (TypeError, ValueError):
            return False
        n = max(1, min(MAX_PARTICLES, int(n)))
        self._bursts = [b for b in self._bursts if self.t - b[0] < BURST_GAP - 1e-9]
        if any(math.hypot(x - bx, y - by) < BURST_NEAR for _, bx, by in self._bursts):
            return False
        self._bursts.append((self.t, x, y))
        start = self.rng.random() * 2.0 * math.pi / n
        for i in range(n):
            a = start + 2.0 * math.pi * i / n
            k = self._next % MAX_PARTICLES
            self._pos[k] = (x, y)
            self._vel[k] = (BURST_SPEED * math.cos(a), BURST_SPEED * math.sin(a))
            self._rgb[k] = rgb
            self._born[k] = self.t
            self._next += 1
        return True

    def pop(self, text, x, y, color) -> None:
        """text centred on (x, y), rising POP_RISE pixels over POP_SECONDS; the newest MAX_POPS are kept."""
        x, y = _number(x), _number(y)
        if x is None or y is None:
            return
        try:
            rgb = _c(color)
        except (TypeError, ValueError):
            return
        self._pops = (self._pops + [(self.t, str(text), x, y, rgb)])[-MAX_POPS:]

    def banner(self, text, seconds=1.0) -> None:
        """text across the middle of the wall on a black box for seconds, at 2x when it fits; replaces a banner."""
        seconds = _seconds(seconds)
        if seconds is None:
            return
        self._banner = (str(text), self.t + seconds)

    def freeze(self, seconds) -> None:
        """Hit-stop: the runner skips the game's update for seconds and keeps drawing."""
        seconds = _seconds(seconds)
        if seconds is not None:
            self._freeze_until = max(self._freeze_until, self.t + seconds)

    def celebrate(self, color) -> None:
        """Bursts across the middle of the wall now and again after CELEBRATE_GAP."""
        self._wave(color)
        self._waves.append((self.t + CELEBRATE_GAP, color))

    def echo(self, player, kind) -> None:
        """Acknowledge a recognised gesture at once: kind's glyph over player 1's or 2's marker for ECHO_SECONDS."""
        if player in (1, 2) and not isinstance(player, bool) and kind in ECHOES:
            self._echoes[player] = (kind, self.t + ECHO_SECONDS)

    @property
    def frozen(self) -> bool:
        return self.t < self._freeze_until - 1e-9

    # ----- what the runner calls -----

    def update(self, dt: float) -> None:
        """Advance every effect by dt seconds (the runner's clamped tick)."""
        dt = _seconds(dt) or 0.0
        self.t += dt
        for at, color in [w for w in self._waves if w[0] <= self.t + 1e-9]:
            self._waves.remove((at, color))
            self._wave(color)
        self._pops = [p for p in self._pops if self.t - p[0] < POP_SECONDS - 1e-9]
        if self._banner is not None and self.t >= self._banner[1] - 1e-9:
            self._banner = None
        self._echoes = {p: e for p, e in self._echoes.items() if self.t < e[1] - 1e-9}

    def render(self, canvas: Canvas, player: Body | None = None, player2: Body | None = None) -> None:
        """Draw the effects over the game's frame: particles, pops, the banner and the flash, then the shake as a
        slice copy (black fills the gap), then the players' markers and echoes, which never shake."""
        frame = canvas.frame
        h, w = frame.shape[:2]
        self._draw_particles(frame)
        for at, text, x, y, rgb in self._pops:
            rise = POP_RISE * min(1.0, (self.t - at) / POP_SECONDS)
            canvas.text(x - canvas.text_width(text) / 2, y - CELL_H / 2 - rise, text, rgb)
        if self._banner is not None:
            text = self._banner[0]
            scale = 2 if canvas.text_width(text, 2) <= w - 2 and 2 * CELL_H <= h - 2 else 1
            tw, th = canvas.text_width(text, scale), CELL_H * scale
            x, y = (w - tw) // 2, (h - th) // 2
            canvas.fill_rect(x - 1, y - 1, tw + 2, th + 2, (0, 0, 0))
            canvas.text(x, y, text, (255, 255, 255), scale)
        level = self._flash_level()
        if level > 0.0:
            add = np.array(self._flash_color, np.float64) * level
            frame[:] = np.minimum(frame + np.floor(add + 0.5).astype(np.uint16), 255).astype(np.uint8)
        self._shake_step()
        dx, dy = self._offset
        if dx or dy:
            shifted = np.zeros_like(frame)
            shifted[max(dy, 0):h + min(dy, 0), max(dx, 0):w + min(dx, 0)] = \
                frame[max(-dy, 0):h + min(-dy, 0), max(-dx, 0):w + min(-dx, 0)]
            frame[:] = shifted
        for number, body in ((1, player), (2, player2)):
            if body is None:
                continue
            x, color = marker_x(body, w), PLAYER_COLORS[number - 1]
            canvas.fill_rect(x, h - 1, 2, 1, color)
            echo = self._echoes.get(number)
            if echo is not None:
                glyph = np.array([[ch == "#" for ch in row] for row in ECHOES[echo[0]]])
                canvas.blit(glyph, min(x, w - 3), h - 5, color)

    def debug_state(self) -> dict:
        return {"fx_shake": list(self._offset), "fx_particles": int(self._alive().sum()), "fx_frozen": self.frozen,
                "fx_flash": round(self._flash_level(), 3), "fx_banner": None if self._banner is None else
                self._banner[0], "fx_pops": len(self._pops), "fx_echoes": len(self._echoes)}

    # ----- inside -----

    def _wave(self, color) -> None:
        w, h = self.size
        for x in range(BURST_NEAR // 2, w, BURST_NEAR):
            self.burst(x, h / 2, color)

    def _alive(self) -> np.ndarray:
        return self.t - self._born < BURST_LIFE - 1e-9

    def _draw_particles(self, frame: np.ndarray) -> None:
        alive = self._alive()
        if not alive.any():
            return
        age = (self.t - self._born[alive])[:, None]
        pos = np.floor(self._pos[alive] + self._vel[alive] * age + 0.5).astype(np.int64)
        rgb = np.floor(self._rgb[alive] * (1.0 - age / BURST_LIFE) + 0.5).astype(np.uint8)
        h, w = frame.shape[:2]
        inside = (pos[:, 0] >= 0) & (pos[:, 0] < w) & (pos[:, 1] >= 0) & (pos[:, 1] < h)
        frame[pos[inside, 1], pos[inside, 0]] = rgb[inside]

    def _flash_level(self) -> float:
        age = self.t - self._flash_start
        return 1.0 if 0.0 <= age < self._flash_seconds - 1e-9 else 0.0

    def _amplitude(self) -> float:
        if self._length <= 0.0:
            return 0.0
        return max(0.0, self._amp * (1.0 - (self.t - self._start) / self._length))

    def _shake_step(self) -> None:
        """Move the offset to the other side at the envelope's size, at most once every SHAKE_STEP."""
        if self.t - self._moved < SHAKE_STEP - 1e-9:
            return
        v = self._sign * math.floor(self._amplitude() + 0.5)
        offset = (v, 0) if self._axis == 0 else (0, v)
        if offset != self._offset:
            self._offset, self._moved, self._sign = offset, self.t, -self._sign
