"""Input helpers shared by games, the lobby and the runner (spec 4.1): Edge, Hold, Cursor and the One Euro filter.

The camera captures at camera_fps (10) while the runner ticks at 30 Hz, so a Sensed body holds for three ticks
and a keypoint that drops out of one capture is missing for a tenth of a second. At the spec 6.4 dropout (15
percent per keypoint) one wrist is missing from 15 percent of captures and both hands up reads false on 28
percent, in runs (C10, measured over 6000 s of degrade(REAL_NOISE) captures): 3 or more captures in a row about
every 7 s of holding, 5 or more about every 5 minutes, 6 about every 25 minutes, 7 or more never. Every helper
here takes a grace in seconds. The lobby and the runner give theirs capture_grace(cfg.camera_fps), which is
sized in captures (Q10); a game chooses its own, and a grace delays a release by that long.
"""
from __future__ import annotations

import math

from arcade.look import is_real
from arcade.sensed import LEFT_HIP, LEFT_WRIST, MIN_CONF, RIGHT_HIP, RIGHT_WRIST, Body

CAPTURE_GRACE = 5        # missed captures in a row that a hold, an edge or the cursor rides out
EPSILON = 1e-9           # tick times are sums of 1/30: a 3.0 s hold must not miss by a rounding error


def _check(name: str, value: float) -> float:
    if not is_real(value) or not 0.0 <= value < math.inf:
        raise ValueError(f"{name} must be a finite number of seconds, 0 or more, got {value!r}")
    return float(value)


def capture_grace(camera_fps: float, captures: int = CAPTURE_GRACE) -> float:
    """Seconds that cover this many missed captures in a row, plus half a capture so a run of exactly that
    many never trips on a rounding error: 0.55 s at 10 fps. A run one capture longer ends the hold."""
    if not is_real(camera_fps) or not 0.0 < camera_fps < math.inf:
        raise ValueError(f"camera_fps must be over 0 and finite, got {camera_fps!r}")
    if isinstance(captures, bool) or not isinstance(captures, int) or captures < 0:
        raise ValueError(f"captures must be an int, 0 or more, got {captures!r}")
    return (captures + 0.5) / float(camera_fps)


class Edge:
    """A rising edge that fires once per press. update(value, t) is True on the first true value after the
    value has been false for more than grace seconds (or ever). A blink no longer than grace, a wrist missing
    from a capture or two, neither fires again nor re-arms."""

    def __init__(self, grace: float = 0.25):
        self.grace = _check("grace", grace)
        self.on = False
        self._last = -math.inf

    def update(self, value: bool, t: float) -> bool:
        if value:
            fire = not self.on
            self.on, self._last = True, t
            return fire
        if self.on and t - self._last > self.grace + EPSILON:
            self.on = False
        return False


class Hold:
    """update(value, t) is True once, on the first tick with value true that is seconds or more after the hold
    began. Dropouts of up to grace seconds keep the hold; a longer one ends it (progress back to 0), and it
    fires again only after a new hold. progress runs 0..1 for a ring drawn round the hands."""

    def __init__(self, seconds: float, grace: float = 0.25):
        self.seconds, self.grace = _check("seconds", seconds), _check("grace", grace)
        self.reset()

    def reset(self) -> None:
        self.start: float | None = None
        self.fired = False
        self._last = self._now = -math.inf

    @property
    def progress(self) -> float:
        if self.start is None:
            return 0.0
        if self.seconds == 0.0:
            return 1.0
        return min(1.0, max(0.0, (self._now - self.start) / self.seconds))

    def update(self, value: bool, t: float) -> bool:
        self._now = t
        if value:
            if self.start is None:
                self.start = t
            self._last = t
        elif self.start is not None and t - self._last > self.grace + EPSILON:
            self.reset()
            return False
        if not value or self.fired or self.start is None or t - self.start < self.seconds - EPSILON:
            return False
        self.fired = True
        return True


class Cursor:
    """Body.cursor with hand hysteresis (C10). The stateless cursor jumps to the other wrist whenever the
    pointing one drops out of a capture; this one keeps the hand it chose and holds its last position for
    up to grace seconds while that wrist is missing, and changes hands only when the other wrist reaches
    switch times further from its hip. update(body, t) returns (u, v) in the reach box, or None."""

    def __init__(self, grace: float = 0.25, switch: float = 1.25):
        self.grace = _check("grace", grace)
        if not is_real(switch) or not 1.0 <= switch < math.inf:
            raise ValueError(f"switch must be 1 or more and finite, got {switch!r}")
        self.switch = float(switch)
        self.hand: str | None = None
        self._last: tuple[float, float] | None = None
        self._seen = -math.inf

    @staticmethod
    def _reach(body: Body, hand: str) -> float | None:
        """How far this hand's confident wrist is from its hip (as Body.cursor measures it), else None."""
        wrist, hip = (body.keypoints[LEFT_WRIST], body.keypoints[LEFT_HIP]) if hand == "left" else \
            (body.keypoints[RIGHT_WRIST], body.keypoints[RIGHT_HIP])
        if wrist.conf < MIN_CONF:
            return None
        ref = next((k for k in (hip if hip.conf >= MIN_CONF else None, body.hip_mid, body.shoulder_mid)
                    if k is not None), wrist)
        return math.hypot(wrist.x - ref.x, wrist.y - ref.y)

    def update(self, body: Body | None, t: float) -> tuple[float, float] | None:
        reach = {} if body is None else {h: d for h in ("left", "right") if (d := self._reach(body, h)) is not None}
        if self.hand not in reach:
            if self._last is not None and t - self._seen <= self.grace + EPSILON:
                return self._last                            # the pointing wrist is missing: hold it
            self.hand = max(reach, key=reach.get) if reach else None
        else:
            other = "left" if self.hand == "right" else "right"
            if other in reach and reach[other] > self.switch * reach[self.hand]:
                self.hand = other
        if self.hand is None:
            return None
        wrist = body.keypoints[LEFT_WRIST if self.hand == "left" else RIGHT_WRIST]
        self._last, self._seen = body.reach(wrist), t
        return self._last


class OneEuro:
    """The One Euro filter (Casiez, Roussel and Vogel, CHI 2012) for one coordinate, timed by capture time.

    A sample at a time no later than the last one (the same capture held over several ticks) returns the
    last output unchanged, and so does a sample that is not finite. beta = 0.007 is the paper's value for
    pixel units; in the 0..1 camera units the arcade uses it barely adapts, so the tracker (core Task 16)
    passes its own when it is tuned against the real fixtures."""

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.007, d_cutoff: float = 1.0):
        for name, v in (("min_cutoff", min_cutoff), ("d_cutoff", d_cutoff)):
            if not is_real(v) or not 0.0 < v < math.inf:
                raise ValueError(f"{name} must be over 0 and finite, got {v!r}")
        if not is_real(beta) or not 0.0 <= beta < math.inf:
            raise ValueError(f"beta must be 0 or more and finite, got {beta!r}")
        self.min_cutoff, self.beta, self.d_cutoff = float(min_cutoff), float(beta), float(d_cutoff)
        self.reset()

    def reset(self) -> None:
        self.value: float | None = None
        self._dx = 0.0
        self._t = -math.inf

    @staticmethod
    def _alpha(dt: float, cutoff: float) -> float:
        r = 2.0 * math.pi * cutoff * dt
        return r / (r + 1.0)

    def __call__(self, x: float, t: float) -> float:
        if not (math.isfinite(x) and math.isfinite(t)):
            return x if self.value is None else self.value
        if self.value is None:
            self.value, self._t = x, t
            return x
        dt = t - self._t
        if dt <= 0.0:
            return self.value
        self._dx += self._alpha(dt, self.d_cutoff) * ((x - self.value) / dt - self._dx)
        cutoff = self.min_cutoff + self.beta * abs(self._dx)
        self.value += self._alpha(dt, cutoff) * (x - self.value)
        self._t = t
        return self.value
