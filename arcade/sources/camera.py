"""The camera base (spec 6): ThreadedCamera runs a capture thread and publishes stamped results; BodyTracker gives
stable ids, smoothed keypoints and velocities (spec 5); assign() is the global matcher both share with Task 19."""
from __future__ import annotations

import dataclasses
import itertools
import logging
import math
import threading
import time
from typing import Callable, Sequence

import numpy as np

from arcade.calibration import Calibration
from arcade.sensed import MIN_CONF, Blob, Body, Keypoint, place

log = logging.getLogger("arcade")

Box = tuple[float, float, float, float]
Detections = Sequence[tuple[Box, Sequence[Keypoint]]]
# (capture_t, bodies, blobs, motion): capture_t on the injected clock, in seconds (runner._camera_result)
CameraResult = tuple[float, tuple[Body, ...], tuple[Blob, ...], "np.ndarray | None"]

STALE_SECONDS = 1.0       # an older result is None and the camera unavailable (spec 6)
COAST_SECONDS = 0.3       # a missed track is still emitted, with seen_ago, for this long (spec 5)
DROP_SECONDS = 0.5        # and forgotten after this long; its id is never used again
MAX_EXHAUSTIVE = 6        # assign() without scipy searches every pairing up to this many on the smaller side
MAX_COST = 0.25           # frame units: a detection further than this (plus the terms below) from a track is new
SCALE_WEIGHT = 1.0        # cost per frame unit of scale difference (people at different depths)
COAST_COST = 0.1          # cost per second since a track was last seen: its prediction is less sure, so a tie
                          # between two tracks (two people crossing) goes to the one seen most recently
VELOCITY_TAU = 0.1        # s: time constant of the velocity's smoothing after its first measurement
SCALE_TAU = 0.1           # s: time constant of the scale's smoothing; input.Depth's Glide smooths the control
                          # itself, and at 0.3 s the two smoothers in a row lagged a ramp by 0.3 s (C44)
RATIO_TAU = 1.0           # s: time constant of the smoothing of a track's learned scale per shoulder width (Q48)
ONE_EURO = dict(min_cutoff=1.0, beta=4.0, d_cutoff=1.0)   # keypoints in frame units per second


# ----- assignment -----

def assign(cost: Sequence[Sequence[float]]) -> list[tuple[int, int]]:
    """The (row, column) pairs of least total cost, min(rows, columns) of them, sorted by row. scipy's
    linear_sum_assignment when importable; otherwise every pairing is tried, which allows at most MAX_EXHAUSTIVE on
    the smaller side (ValueError beyond)."""
    rows = len(cost)
    cols = len(cost[0]) if rows else 0
    if rows == 0 or cols == 0:
        return []
    try:
        from scipy.optimize import linear_sum_assignment
    except ImportError:
        return _exhaustive(cost, rows, cols)
    r, c = linear_sum_assignment(np.asarray(cost, float))
    return sorted(zip(r.tolist(), c.tolist()))


def _exhaustive(cost: Sequence[Sequence[float]], rows: int, cols: int) -> list[tuple[int, int]]:
    if min(rows, cols) > MAX_EXHAUSTIVE:
        raise ValueError(f"assign: {rows}x{cols} needs scipy (exhaustive search stops at {MAX_EXHAUSTIVE})")
    best, best_pairs = math.inf, []
    if rows <= cols:
        for perm in itertools.permutations(range(cols), rows):
            total = sum(cost[r][c] for r, c in enumerate(perm))
            if total < best:
                best, best_pairs = total, list(enumerate(perm))
    else:
        for perm in itertools.permutations(range(rows), cols):
            total = sum(cost[r][c] for c, r in enumerate(perm))
            if total < best:
                best, best_pairs = total, [(r, c) for c, r in enumerate(perm)]
    return sorted(best_pairs)


# ----- smoothing -----

def _alpha(dt: float, cutoff: float) -> float:
    tau = 1.0 / (2.0 * math.pi * cutoff)
    return 1.0 / (1.0 + tau / dt)


class OneEuro:
    """The One Euro filter (Casiez et al. 2012): little lag when moving fast, little jitter when still."""

    def __init__(self, min_cutoff: float, beta: float, d_cutoff: float):
        self.min_cutoff, self.beta, self.d_cutoff = min_cutoff, beta, d_cutoff
        self.x: float | None = None
        self.dx = 0.0
        self.t = 0.0

    def __call__(self, x: float, t: float) -> float:
        if self.x is None:
            self.x, self.dx, self.t = x, 0.0, t
            return x
        dt = t - self.t
        if dt <= 0.0:
            return self.x
        self.dx += _alpha(dt, self.d_cutoff) * ((x - self.x) / dt - self.dx)
        self.x += _alpha(dt, self.min_cutoff + self.beta * abs(self.dx)) * (x - self.x)
        self.t = t
        return self.x

    def reset(self) -> None:
        self.x = None


# ----- tracker -----

@dataclasses.dataclass
class _Track:
    id: int
    x: float                      # raw anchor at the last sighting
    y: float
    seen: float                   # capture time of the last sighting
    scale: float
    box: Box
    keypoints: tuple[Keypoint, ...]
    filters: list[tuple[OneEuro, OneEuro]]
    vx: float = 0.0
    vy: float = 0.0
    moved: bool = False           # vx, vy measured at least once
    measured: bool = False        # a capture with a confident nose and a hip seen (_measured) at least once
    per_width: float = 0.0        # this person's measured scale per shoulder width, 0.0 until learned
    torso_per_width: float = 0.0  # this person's measured torso per shoulder width, 0.0 until learned (C46)

    def predict(self, t: float) -> tuple[float, float]:
        dt = t - self.seen
        return self.x + self.vx * dt, self.y + self.vy * dt


def _anchor(body: Body) -> tuple[float, float]:
    a = body.anchor
    return (a.x, a.y) if a is not None else body.center


def _measured(raw: Body) -> bool:
    """raw.scale is the nose-to-mid-hip length, not the fallback from the shoulder width."""
    return raw.nose.conf >= MIN_CONF and raw.hip_mid is not None


def _reading(tr: _Track, raw: Body) -> float | None:
    """The scale this capture reads for tr (Q48), None to hold tr's. The fallback from the shoulder width reads
    short on a real person (0.62 of the measure in the owner's spike), so a track once measured reads its own
    learned scale per shoulder width instead, and holds without both shoulders; a track never measured reads the
    fallback, as a body always did."""
    if _measured(raw) or not tr.measured:
        return raw.scale
    width = raw.shoulder_width
    if tr.per_width > 0.0 and width > 0.0:
        return tr.per_width * width
    return None


class BodyTracker:
    """spec 5: anchors on the shoulder midpoint (then nose, then hips), predicts with constant velocity from capture
    times, assigns globally on distance plus scale difference, coasts a missed track for COAST_SECONDS (emitting
    seen_ago), drops it after DROP_SECONDS, and never reuses an id. Keypoints are One Euro filtered; a keypoint under
    MIN_CONF passes through raw and restarts its filter. A coasting body holds its last keypoints and box. The
    scale is smoothed by SCALE_TAU; a track once measured with its hips reads its learned scale per shoulder width
    when they drop out, and holds its scale without both shoulders (Q48, _reading). A track born without hips is
    not measured (Body.measured False) until a capture with its nose and a hip, whose measure the scale takes at
    once, not through SCALE_TAU (C47). Its torso per shoulder width is learned as its scale per width is, and its
    bodies carry it, so the torso without hips is this person's (C46).

    update() takes the detections of one capture, keypoints already mirrored, and returns the bodies placed
    against the calibration, largest scale first."""

    def __init__(self, calibration: Calibration | None = None):
        self.calibration = calibration or Calibration()
        self._tracks: list[_Track] = []
        self._next_id = 1

    def update(self, detections: Detections, t: float) -> tuple[Body, ...]:
        self._tracks = [tr for tr in self._tracks if t - tr.seen <= DROP_SECONDS]
        raws = []
        for box, kps in detections:
            raw = Body(0, tuple(box), tuple(kps))
            if any(k.conf >= MIN_CONF for k in raw.keypoints):
                raws.append(raw)
        pairs = self._match(raws, t)
        matched = {d: i for i, d in pairs}
        for d, raw in enumerate(raws):
            if d in matched:
                self._refresh(self._tracks[matched[d]], raw, t)
            else:
                self._tracks.append(self._new(raw, t))
        bodies = [self._body(tr, t) for tr in self._tracks if t - tr.seen <= COAST_SECONDS + 1e-9]
        bodies.sort(key=lambda b: (-b.scale, b.id))
        return tuple(bodies)

    def _match(self, raws: list[Body], t: float) -> list[tuple[int, int]]:
        if not raws or not self._tracks:
            return []
        cost = []
        for tr in self._tracks:
            px, py = tr.predict(t)
            row = []
            for raw in raws:
                ax, ay = _anchor(raw)
                c = math.hypot(ax - px, ay - py)
                scale = _reading(tr, raw)       # the same rule as _refresh: a hip dropout costs nothing
                if tr.scale > 0.0 and scale is not None and scale > 0.0:
                    c += SCALE_WEIGHT * abs(scale - tr.scale)
                row.append(c + COAST_COST * (t - tr.seen) if c <= MAX_COST else math.inf)
            cost.append(row)
        big = 1e6   # linear_sum_assignment and the exhaustive sum both need finite costs
        pairs = assign([[big if math.isinf(c) else c for c in row] for row in cost])
        return [(i, d) for i, d in pairs if not math.isinf(cost[i][d])]

    def _new(self, raw: Body, t: float) -> _Track:
        ax, ay = _anchor(raw)
        filters = [(OneEuro(**ONE_EURO), OneEuro(**ONE_EURO)) for _ in raw.keypoints]
        tr = _Track(self._next_id, ax, ay, t, raw.scale, raw.box, raw.keypoints, filters)
        self._next_id += 1
        self._learn(tr, raw, 0.0)
        tr.keypoints = self._smooth(tr, raw, t)
        return tr

    def _refresh(self, tr: _Track, raw: Body, t: float) -> None:
        ax, ay = _anchor(raw)
        dt = t - tr.seen
        scale = _reading(tr, raw)
        first = not tr.measured and _measured(raw)      # the first measure: one step, not four captures (C47)
        if dt > 0.0:
            mx, my = (ax - tr.x) / dt, (ay - tr.y) / dt
            if tr.moved:
                a = 1.0 - math.exp(-dt / VELOCITY_TAU)
                tr.vx, tr.vy = tr.vx + a * (mx - tr.vx), tr.vy + a * (my - tr.vy)
            else:
                tr.vx, tr.vy, tr.moved = mx, my, True
            if scale is not None and scale > 0.0:
                tr.scale = scale if tr.scale <= 0.0 or first else \
                    tr.scale + (1.0 - math.exp(-dt / SCALE_TAU)) * (scale - tr.scale)
        self._learn(tr, raw, dt)
        tr.x, tr.y, tr.seen, tr.box = ax, ay, t, raw.box
        tr.keypoints = self._smooth(tr, raw, t)

    @staticmethod
    def _learn(tr: _Track, raw: Body, dt: float) -> None:
        """A measured capture teaches tr its scale and its torso per shoulder width: the first at once, then
        smoothed by RATIO_TAU so one bad capture does not move them far."""
        if not _measured(raw):
            return
        tr.measured = True
        width = raw.shoulder_width
        if width <= 0.0:
            return
        if raw.scale > 0.0:
            tr.per_width = BodyTracker._ratio(tr.per_width, raw.scale / width, dt)
        if raw.torso > 0.0:
            tr.torso_per_width = BodyTracker._ratio(tr.torso_per_width, raw.torso / width, dt)

    @staticmethod
    def _ratio(learned: float, ratio: float, dt: float) -> float:
        if learned <= 0.0:
            return ratio
        if dt > 0.0:
            return learned + (1.0 - math.exp(-dt / RATIO_TAU)) * (ratio - learned)
        return learned

    @staticmethod
    def _smooth(tr: _Track, raw: Body, t: float) -> tuple[Keypoint, ...]:
        out = []
        for k, (fx, fy) in zip(raw.keypoints, tr.filters):
            if k.conf >= MIN_CONF:
                out.append(Keypoint(fx(k.x, t), fy(k.y, t), k.conf))
            else:
                fx.reset(), fy.reset()
                out.append(k)
        return tuple(out)

    def _body(self, tr: _Track, t: float) -> Body:
        seen_ago = 0.0 if tr.seen == t else t - tr.seen
        body = Body(tr.id, tr.box, tr.keypoints, vx=tr.vx, vy=tr.vy, scale=tr.scale, seen_ago=seen_ago,
                    measured=tr.measured, torso_per_width=tr.torso_per_width)
        return place(body, self.calibration)


# ----- threaded source -----

class ThreadedCamera:
    """Runs step() in a daemon thread and publishes each result it gives; None holds the last one. latest() is
    None before the first result, past STALE_SECONDS on the clock, and after step() raised (the thread then ends,
    logged); available is whether latest() has a result. close() stops and joins the thread, then release()s."""

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self.clock = clock
        self._lock = threading.Lock()
        self._latest: CameraResult | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._released = False

    @property
    def available(self) -> bool:
        return self.latest() is not None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name=type(self).__name__, daemon=True)
        self._thread.start()

    def step(self) -> CameraResult | None:
        raise NotImplementedError

    def release(self) -> None:
        """Frees the device and model; runs after the thread has stopped."""

    def poll(self) -> None:
        """One step(), published unless it gave None: the thread's loop body."""
        result = self.step()
        if result is not None:
            self.publish(result)

    def publish(self, result: CameraResult) -> None:
        with self._lock:
            self._latest = result

    def _run(self) -> None:
        try:
            while not self._stop.is_set():
                self.poll()
        except Exception:
            log.exception("%s thread died; camera unavailable", type(self).__name__)
            with self._lock:
                self._latest = None

    def latest(self) -> CameraResult | None:
        with self._lock:
            got = self._latest
        if got is None or self.clock() - got[0] > STALE_SECONDS:
            return None
        return got

    def close(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)
            if thread.is_alive():
                log.warning("%s thread did not stop in 2 s; leaving its device open", type(self).__name__)
                return
        if not self._released:
            self._released = True
            self.release()
