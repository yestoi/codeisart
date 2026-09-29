"""Input helpers shared by games, the lobby and the runner (spec 4.1): Edge, Hold, Cursor, the One Euro filter, and
the controls (C44): Glide (a captured value given smoothly on every tick) and Depth (the body's size as 0..1).

The camera captures at camera_fps (10) while the runner ticks at 30 Hz, so a Sensed body holds for three ticks
and a keypoint that drops out of one capture is missing for a tenth of a second. At the spec 6.4 dropout (15
percent per keypoint) one wrist is missing from 15 percent of captures and both hands up reads false on 28
percent, in runs (C10, measured over 6000 s of degrade(REAL_NOISE) captures): 3 or more captures in a row about
every 7 s of holding, 5 or more about every 5 minutes, 6 about every 25 minutes, 7 or more never. Every helper
here takes a grace in seconds. The lobby and the runner give theirs capture_grace(cfg.camera_fps), which is
sized in captures (Q10); a game chooses its own, and a grace delays a release by that long.

The caller rule (C27): call update on a Hold, an Edge or a Cursor every tick, with the value false when there is
nothing to see, or reset() it when it comes back into use (the runner resets its exit hold on every launch). A
helper not updated for a while still holds its last state, so a Hold could fire at once on the first tick after
the gap.
"""
from __future__ import annotations

import math

from arcade.look import is_real
from arcade.sensed import LEFT_HIP, LEFT_WRIST, MIN_CONF, RIGHT_HIP, RIGHT_WRIST, Body

CAPTURE_GRACE = 5        # missed captures in a row that a hold, an edge or the cursor rides out
EPSILON = 1e-9           # tick times are sums of 1/30: a 3.0 s hold must not miss by a rounding error

DEPTH_SPAN = 0.6          # ln(scale / scale0) across the whole 0..1: 0 at a ratio of 0.741 (about 0.7 m back from
                          # 2 m), 1 at 1.350 (about 0.5 m nearer); 0.5 where the body was first seen
PIN = 0.02                # an unclamped value within this of 0 or 1 is pinned at that end
RECENTRE_SECONDS = 2.0    # pinned this long, the centre starts to follow the body
RECENTRE_RATE = 0.25      # value units a second the reading moves inward while it follows,
RECENTRE_TO = 0.15        # until the body reads this far inside the end
GLIDE_MIN_CUTOFF = 1.0    # Hz: One Euro on the value, by capture time
GLIDE_BETA = 2.0          # per (value unit per second): a moving body is barely smoothed
GLIDE_PERIOD = (1 / 60, 0.25)   # s: the measured capture period is clamped to this


def _float(value) -> float:
    """value as a float: NaN if it is not a real number, an infinity if it is an int too big for a float."""
    if not is_real(value):
        return math.nan
    try:
        return float(value)
    except OverflowError:
        return math.inf if value > 0 else -math.inf


def _check(name: str, value: float) -> float:
    v = _float(value)
    if not 0.0 <= v < math.inf:
        raise ValueError(f"{name} must be a finite number of seconds, 0 or more, got {value!r}")
    return v


def _positive(name: str, value: float, zero: bool = False) -> float:
    """value as a float if it is finite and over 0 (or 0 itself, with zero), else ValueError."""
    v = _float(value)
    if not (0.0 <= v if zero else 0.0 < v) or not v < math.inf:
        raise ValueError(f"{name} must be {'0 or more' if zero else 'over 0'} and finite, got {value!r}")
    return v


def capture_grace(camera_fps: float, captures: int = CAPTURE_GRACE) -> float:
    """Seconds that cover this many missed captures in a row, plus half a capture so a run of exactly that
    many never trips on a rounding error: 0.55 s at 10 fps. A run one capture longer ends the hold."""
    fps = _positive("camera_fps", camera_fps)
    if isinstance(captures, bool) or not isinstance(captures, int) or captures < 0:
        raise ValueError(f"captures must be an int, 0 or more, got {captures!r}")
    return (captures + 0.5) / fps


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
    last output unchanged, and so does a sample that is not a finite real number (NaN before the first). A
    numpy sample is taken as a float, and the output is always a float. beta = 0.007 is the paper's value for
    pixel units; in the 0..1 camera units the arcade uses it barely adapts, so the tracker (core Task 16)
    passes its own when it is tuned against the real fixtures."""

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.007, d_cutoff: float = 1.0):
        self.min_cutoff, self.d_cutoff = _positive("min_cutoff", min_cutoff), _positive("d_cutoff", d_cutoff)
        self.beta = _positive("beta", beta, zero=True)
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
        x, t = _float(x), _float(t)
        if not (math.isfinite(x) and math.isfinite(t)):
            return math.nan if self.value is None else self.value
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



class Glide:
    """A value captured at the camera's rate, given on every tick: One Euro filtered by capture time, then
    moved linearly from the last output to the newest filtered value over one measured capture period.

    At camera_fps 10 a capture holds for three ticks, so a control read straight from it moves ten times a
    second. update(value, t, camera_t) takes a new capture when camera_t is later than the last one (a held
    capture is one sample, not three) and on every tick moves the output a tick's share of the way from where
    it was when that capture arrived to the capture's filtered value, arriving as the next capture is due. It
    interpolates and never extrapolates: a paddle that overshoots on a reversal feels worse than one 0.1 s late.
    The lag this adds (C44) is at most one capture period plus One Euro's 1 / (2 pi fc).

    A value that is None or not finite holds the output for grace seconds (by t); longer gives None and
    reset(), and the next value is output as it is, with no glide from the old one."""

    def __init__(self, grace: float = capture_grace(10), min_cutoff: float = GLIDE_MIN_CUTOFF,
                 beta: float = GLIDE_BETA):
        self.grace = _check("grace", grace)
        self._filter = OneEuro(min_cutoff, beta)
        self.reset()

    def reset(self) -> None:
        self.value: float | None = None
        self._filter.reset()
        self._from = self._to = 0.0
        self._start, self._period = 0.0, GLIDE_PERIOD[1]
        self._capture = -math.inf             # camera_t of the newest capture seen, with a value or without
        self._seen = -math.inf                # t of the last tick with a value
        self._tick: float | None = None       # t of the last update

    def update(self, value: float | None, t: float, camera_t: float) -> float | None:
        v, cam = _float(value), _float(camera_t)
        new = math.isfinite(cam) and cam > self._capture
        period = cam - self._capture
        if new:
            self._capture = cam
        last_tick, self._tick = self._tick, t
        if not (math.isfinite(v) and math.isfinite(cam)):
            if self.value is not None and t - self._seen <= self.grace + EPSILON:
                return self.value                                    # dropped out: hold
            self.reset()
            return None
        self._seen = t
        if self.value is None:
            self.value = self._from = self._to = self._filter(v, cam)
            self._start = t
            return self.value
        if new:
            lo, hi = GLIDE_PERIOD
            self._from, self._to = self.value, self._filter(v, cam)
            self._start = last_tick if last_tick is not None and last_tick < t else t
            self._period = min(hi, max(lo, period))
        share = min(1.0, max(0.0, (t - self._start) / self._period))
        self.value = self._from + share * (self._to - self._from)
        return self.value


class Depth:
    """Body.scale as a 0..1 control, 1 nearest the camera: 0.5 + ln(scale / scale0) / span, clamped, through a
    Glide. scale0 is the scale of the first capture after reset(); pinned at an end for RECENTRE_SECONDS the
    centre follows as the constants say. A body that is None or has no scale is a dropout.

    Pinned means the unclamped value is within PIN of an end or past it. Once it has been pinned at one end for
    RECENTRE_SECONDS of captures, scale0 moves so the body reads at that end, then keeps moving so the reading
    comes inward at RECENTRE_RATE a second until the body reads RECENTRE_TO inside the end; there it stops. A
    body that leaves the end sooner resets the clock. scale0 survives a dropout: a player who is missed for a
    moment comes back to the same centre; the caller reset()s the Depth when another body takes the control.

    The first measure (C47): a track born without hips has the shoulder-width fallback for its scale (Body.measured
    False), short on a real person (0.62 of the measure in the owner's spike), and reads its measure once its hips
    are seen: a step of about 0.8 in value that nobody took. So when the centre came from a capture that was not
    measured, the first measured capture after it takes a new centre: scale0 moves so that capture reads what the
    last one read (raw), and the pinned clock restarts. That jump is no travel and no input. Once per reset(); a
    body measured from its first capture never takes it."""

    def __init__(self, span: float = DEPTH_SPAN, grace: float = capture_grace(10)):
        self.span = _positive("span", span)
        self.glide = Glide(grace)
        self.reset()

    def reset(self) -> None:
        self.glide.reset()
        self.raw: float | None = None
        self._scale0: float | None = None
        self._capture = -math.inf             # camera_t of the newest capture read
        self._value: float | None = None      # that capture's clamped value, given to the Glide on every tick
        self._pinned: tuple[int, float] | None = None   # (end, capture time) the reading was first pinned there
        self._follow = 0                      # -1 or 1 while the centre follows a body pinned at 0 or 1
        self._unmeasured = False              # the centre came from a capture whose body was not measured

    @staticmethod
    def ratio(value: float, span: float = DEPTH_SPAN) -> float:
        """The scale / scale0 that reads value (unclamped): exp((value - 0.5) * span)."""
        return math.exp((value - 0.5) * span)

    def update(self, body: Body | None, t: float, camera_t: float) -> float | None:
        scale = math.nan if body is None else _float(body.scale)
        cam = _float(camera_t)
        if not (math.isfinite(scale) and scale > 0.0 and math.isfinite(cam)):
            out = self.glide.update(None, t, camera_t)
            if out is None:
                self._value, self._pinned, self._follow = None, None, 0
            return out
        if cam > self._capture or self._value is None:
            dt = max(0.0, cam - self._capture) if math.isfinite(self._capture) else 0.0
            self._capture = cam
            self._value = min(1.0, max(0.0, self._read(scale, cam, dt, bool(body.measured))))
        return self.glide.update(self._value, t, cam)

    def _shift(self, by: float) -> None:
        """Move the centre so every reading rises by `by` value units."""
        self._scale0 *= math.exp(-by * self.span)

    def _read(self, scale: float, cam: float, dt: float, measured: bool = True) -> float:
        if self._scale0 is None:
            self._scale0, self._unmeasured = scale, not measured
        elif self._unmeasured and measured:
            self._scale0 = scale * math.exp(-(self.raw - 0.5) * self.span)   # this capture reads what the last did
            self._unmeasured, self._pinned = False, None
        u = 0.5 + math.log(scale / self._scale0) / self.span
        if self._follow:
            goal = RECENTRE_TO if self._follow < 0 else 1.0 - RECENTRE_TO
            gap = (goal - u) * -self._follow                         # how far the reading is outside the goal
            if gap > 0.0:
                step = min(gap, RECENTRE_RATE * dt) * -self._follow
                self._shift(step)
                u += step
            if gap <= RECENTRE_RATE * dt + EPSILON:
                self._follow = 0
        else:
            end = -1 if u <= PIN else 1 if u >= 1.0 - PIN else 0
            if not end:
                self._pinned = None
            elif self._pinned is None or self._pinned[0] != end:
                self._pinned = (end, cam)
            elif cam - self._pinned[1] >= RECENTRE_SECONDS - EPSILON:
                snap = min(1.0, max(0.0, u)) - u                     # the body reads at the end it is pinned to
                self._shift(snap)
                u += snap
                self._follow, self._pinned = end, None
        self.raw = u
        return u
