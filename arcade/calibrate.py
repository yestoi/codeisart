"""`arcade calibrate` (spec 6.6): once per setup, writes data_dir/calibration.json, read at startup.

The Calibrator is the runner's lobby, with no games, so everything it draws passes the brightness limiter and the
flash governor as any lobby's does. It reads Sensed only. main opens the sources against the default Calibration(),
so a body's anchor (the shoulders, sensed.Body.anchor) is its raw camera place, mirrored as the wall shows it, and
the runner hands the lobby every body and every blob, in the zone or not.

Steps (phase), each with its words at 1x at row 1 over a black box, every confident keypoint (DOT) and every light
(LIGHT) as a dot at its camera place in VIEW, and the zone so far as a 1 px outline there (ZONE); rows 60 to 63 dark:
1. aim, "AIM: HANDS UP": ends when a body holds both hands up HOLD_SECONDS (the wall shows what the camera sees).
2. far_left, far_right, near: each ends when one body (the largest) has stood still STILL_SECONDS, its anchor within
   STILL_FW of its median over the window; the stand keeps the median anchor and the median height.
3. baseline, "STAND STILL": still BASELINE_SECONDS; baseline_scale is the median scale.
4. clear, "CLEAR THE FRAME <n>": CLEAR_SECONDS with no body (a body restarts it). static_mask is the lights seen in at
   least STATIC_SHARE of its captures, radius STATIC_RADIUS; audio_floor_db the last floor_db heard while the
   microphone is available, else the default.
5. saved, "SAVED", END_SECONDS, then done(). The zone: x from the stands' anchors, min to max, widened by MARGIN; y
   from min(0.2, top - MARGIN) to max(0.8, bottom + MARGIN), never thinner than the default's (the anchor is the
   shoulders and a jump lifts it: a thin zone drops a jumper, jump.py:15); clamped to 0..1. min_height is
   MIN_HEIGHT_SHARE of the smallest stand's height.
A step that has not ended in STEP_TIMEOUT fails ("NO ONE CAME"); a calibration that would not load back fails ("NOT
SAVED"); a failure shows END_SECONDS, then done(), and writes no file. Spec 6.6 step 5, the exposure and white
balance lock, is the IMX500's (core Task 19).
"""
from __future__ import annotations

import dataclasses
import json
import math
import statistics
from collections import deque
from pathlib import Path

from arcade.calibration import FILENAME, Calibration, _from_json, save_calibration
from arcade.canvas import Canvas
from arcade.config import load_config
from arcade.input import EPSILON, Hold
from arcade.runner import Runner
from arcade.sensed import MIN_CONF, Blob, Body, Sensed
from arcade.sources import make_sources
from show.font import CELL_H, Font

HOLD_SECONDS = 2.0           # both hands up this long ends aim
STILL_SECONDS = 2.0          # a stand: one body still this long
STILL_FW = 0.02              # still: the anchor within this (frame widths) of its median over the window
BASELINE_SECONDS = 3.0       # the baseline: still this long
CLEAR_SECONDS = 10.0         # the clear: this long with no body
STEP_TIMEOUT = 60.0          # a step not ended in this fails: nobody came
END_SECONDS = 2.0            # "SAVED" or the failure shows this long, then done()
MARGIN = 0.05                # the zone reaches this far past the stands' anchors
MIN_HEIGHT_SHARE = 0.8       # min_height is this share of the smallest stand's height
STATIC_SHARE = 0.8           # a light seen in at least this share of the clear's captures is static
STATIC_RADIUS = 0.03         # a static light's radius in the mask (frame widths)
VIEW = (30, 10, 67, 50)      # (x, y, w, h): the 4:3 camera frame on the 128x64 wall, rows 10 to 59

TEXT = (255, 255, 255)
DOT = (0, 255, 0)            # a confident keypoint
LIGHT = (255, 0, 255)        # a blob
ZONE = (255, 200, 0)         # the zone so far
STANDS = ("far_left", "far_right", "near")
NEXT = {"aim": "far_left", "far_left": "far_right", "far_right": "near", "near": "baseline", "baseline": "clear"}
WORDS = {"aim": "AIM: HANDS UP", "far_left": "STAND FAR LEFT", "far_right": "STAND FAR RIGHT",
         "near": "STAND AT THE FRONT", "baseline": "STAND STILL", "clear": "CLEAR THE FRAME", "saved": "SAVED"}
NO_ONE_CAME = "NO ONE CAME"
NOT_SAVED = "NOT SAVED"
DEFAULT = Calibration()


def view_xy(x: float, y: float) -> tuple[int, int]:
    """The wall pixel of camera place (x, y), 0..1, in VIEW (rounded half up, as Canvas rounds)."""
    vx, vy, vw, vh = VIEW
    return math.floor(vx + x * (vw - 1) + 0.5), math.floor(vy + y * (vh - 1) + 0.5)


def _clamp01(v: float) -> float:
    return min(1.0, max(0.0, v))


def zone_of(anchors: list[tuple[float, float]]) -> tuple[float, float, float, float] | None:
    """The zone (x0, y0, x1, y1) of the stands' anchors so far, None without one: x min to max widened by MARGIN, y
    never inside the default zone's y, clamped to 0..1."""
    if not anchors:
        return None
    xs, ys = [a[0] for a in anchors], [a[1] for a in anchors]
    return (_clamp01(min(xs) - MARGIN), _clamp01(min(DEFAULT.zone[1], min(ys) - MARGIN)),
            _clamp01(max(xs) + MARGIN), _clamp01(max(DEFAULT.zone[3], max(ys) + MARGIN)))


class _Still:
    """One body's (anchor x, anchor y, height, scale) over the last `seconds`: still once that body (one id) has
    been seen for `seconds` with every anchor of the window within STILL_FW of the window's median. A tick without
    the body, or with another one, starts again."""

    def __init__(self, seconds: float):
        self.seconds = seconds
        self.id: int | None = None
        self.since = 0.0
        self.samples: deque[tuple[float, float, float, float, float]] = deque()

    def update(self, body: Body | None, t: float) -> bool:
        anchor = None if body is None else body.anchor
        if anchor is None:
            self.id = None
            self.samples.clear()
            return False
        if body.id != self.id:
            self.id, self.since = body.id, t
            self.samples.clear()
        self.samples.append((t, anchor.x, anchor.y, body.height, body.scale))
        while self.samples[0][0] < t - self.seconds - EPSILON:
            self.samples.popleft()
        if t - self.since < self.seconds - EPSILON:
            return False
        mx, my = self.median(1), self.median(2)
        return all(math.hypot(s[1] - mx, s[2] - my) <= STILL_FW + EPSILON for s in self.samples)

    def median(self, i: int) -> float:
        """The window's median of field i: 1 anchor x, 2 anchor y, 3 height, 4 scale."""
        return statistics.median(s[i] for s in self.samples)


class _Lights:
    """The lights of the clear's captures, each joined to the nearest light seen within STATIC_RADIUS (once a
    capture), as [x sum, y sum, captures seen, last capture]."""

    def __init__(self):
        self.captures = 0
        self.seen: list[list] = []

    def add(self, blobs: tuple[Blob, ...]) -> None:
        self.captures += 1
        for b in blobs:
            near = [(math.hypot(b.x - s[0] / s[2], b.y - s[1] / s[2]), i) for i, s in enumerate(self.seen)
                    if s[3] != self.captures]
            d, i = min(near, default=(math.inf, -1))
            if d <= STATIC_RADIUS:
                s = self.seen[i]
                s[0], s[1], s[2], s[3] = s[0] + b.x, s[1] + b.y, s[2] + 1, self.captures
            else:
                self.seen.append([b.x, b.y, 1, self.captures])

    def static(self) -> tuple[tuple[float, float, float], ...]:
        """(x, y, STATIC_RADIUS) of every light seen in at least STATIC_SHARE of the captures, most seen first."""
        keep = [s for s in self.seen if self.captures and s[2] >= STATIC_SHARE * self.captures - EPSILON]
        return tuple((s[0] / s[2], s[1] / s[2], STATIC_RADIUS) for s in sorted(keep, key=lambda s: -s[2]))


class Calibrator:
    """spec 6.6 as the runner's lobby (LobbyLike; it never requests a game). result is the saved Calibration, failed
    the reason none was saved; done() once "SAVED" or the failure has shown END_SECONDS."""

    info = None

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.request: str | None = None
        self._start()

    def _start(self) -> None:
        self.phase = "aim"
        self.result: Calibration | None = None
        self.failed: str | None = None
        self.stands: list[tuple[float, float, float]] = []      # (anchor x, anchor y, height), medians
        self.baseline_scale: float | None = None
        self.t = 0.0
        self._since: float | None = None                          # the phase's start, set on the first update
        self._hold = Hold(HOLD_SECONDS)
        self._still = _Still(STILL_SECONDS)
        self._lights = _Lights()
        self._clear_since = 0.0
        self._failed_words = NO_ONE_CAME
        self._mic_ok = False
        self._floor: float | None = None
        self._bodies: tuple[Body, ...] = ()
        self._blobs: tuple[Blob, ...] = ()

    # ----- LobbyLike -----

    def reset(self, size, rng, fx=None) -> None:
        self._start()

    def update(self, sensed: Sensed, dt: float) -> None:
        t = self.t = sensed.t
        if self._since is None:
            self._since = t
        self._bodies, self._blobs = sensed.bodies, sensed.blobs
        phase = self.phase
        if phase in ("saved", "failed"):
            return
        largest = max(sensed.bodies, key=lambda b: b.scale, default=None)
        if phase == "aim":
            if self._hold.update(any(b.both_hands_up for b in sensed.bodies), t):
                self._next(NEXT[phase])
        elif phase in STANDS:
            if self._still.update(largest, t):
                self.stands.append((self._still.median(1), self._still.median(2), self._still.median(3)))
                self._next(NEXT[phase])
        elif phase == "baseline":
            if self._still.update(largest, t):
                self.baseline_scale = self._still.median(4)
                self._next(NEXT[phase])
        else:
            self._clear(sensed, t)
        if self.phase == phase and t - self._since >= STEP_TIMEOUT - EPSILON:
            self._fail(f"no one came: {phase} did not end in {STEP_TIMEOUT:g} s", NO_ONE_CAME)

    def draw(self, canvas: Canvas) -> None:
        zone = zone_of([s[:2] for s in self.stands])
        if zone is not None:
            (x0, y0), (x1, y1) = view_xy(zone[0], zone[1]), view_xy(zone[2], zone[3])
            canvas.rect(x0, y0, x1 - x0 + 1, y1 - y0 + 1, ZONE)
        for b in self._blobs:
            canvas.pixel(*view_xy(b.x, b.y), LIGHT)
        for body in self._bodies:
            for k in body.keypoints:
                if k.conf >= MIN_CONF:
                    canvas.pixel(*view_xy(k.x, k.y), DOT)
        text = self._words()
        width = canvas.text_width(text)
        x = (canvas.width - width) // 2
        canvas.fill_rect(x - 1, 0, width + 2, CELL_H + 2, (0, 0, 0))   # rows 0 to 9: a gutter round the text
        canvas.text(x, 1, text, TEXT)

    def done(self) -> bool:
        return (self.phase in ("saved", "failed") and self._since is not None
                and self.t - self._since >= END_SECONDS - EPSILON)

    def debug_state(self) -> dict:
        zone = zone_of([s[:2] for s in self.stands])
        return {"phase": self.phase, "seconds": round(self.t - (self._since or 0.0), 3), "stands": len(self.stands),
                "zone": None if zone is None else tuple(round(v, 3) for v in zone)}

    def set_available(self, names: set[str]) -> None:
        pass

    def set_status(self, camera_ok: bool, mic_ok: bool, inputs: set[str], calibrated: bool) -> None:
        self._mic_ok = bool(mic_ok)

    def end_session(self, result) -> None:
        pass

    # ----- the steps -----

    def _next(self, phase: str) -> None:
        self.phase, self._since = phase, self.t
        self._still = _Still(BASELINE_SECONDS if phase == "baseline" else STILL_SECONDS)
        if phase == "clear":
            self._clear_since, self._lights = self.t, _Lights()

    def _fail(self, why: str, words: str) -> None:
        self.failed, self._failed_words = why, words
        self._next("failed")

    def _clear(self, sensed: Sensed, t: float) -> None:
        if self._mic_ok:
            self._floor = sensed.audio.floor_db
        if sensed.bodies:
            self._clear_since, self._lights = t, _Lights()
            return
        if sensed.camera_fresh:
            self._lights.add(sensed.blobs)
        if t - self._clear_since >= CLEAR_SECONDS - EPSILON:
            self._save()

    def _save(self) -> None:
        cal = Calibration(zone=zone_of([s[:2] for s in self.stands]),
                          min_height=MIN_HEIGHT_SHARE * min(s[2] for s in self.stands),
                          baseline_scale=self.baseline_scale, static_mask=self._lights.static(),
                          audio_floor_db=DEFAULT.audio_floor_db if self._floor is None else self._floor,
                          calibrated=True)
        try:
            _from_json(json.loads(json.dumps(dataclasses.asdict(cal))))   # what load_calibration will read back
            save_calibration(self.data_dir, cal)
        except (ValueError, OSError) as e:
            self._fail(f"not saved: {e}", NOT_SAVED)
            return
        self.result = cal
        self._next("saved")

    def _words(self) -> str:
        if self.phase == "clear":
            left = CLEAR_SECONDS - (self.t - self._clear_since)
            return f"{WORDS['clear']} {max(1, math.ceil(left - EPSILON))}"
        if self.phase == "failed":
            return self._failed_words
        return WORDS[self.phase]


def main(args) -> int:
    """`arcade calibrate --config PATH`: 0 when calibration.json was saved, 1 when it was not. The sources are opened
    on this (the main) thread against the default calibration, and they and the display are closed on every path."""
    from arcade.main import build_display   # here: arcade.main imports this module inside its dispatch

    cfg = load_config(args.config)
    data_dir = Path(cfg.data_dir)
    cal = Calibrator(data_dir)
    camera, audio = make_sources(cfg, cfg.size, calibration=Calibration())
    try:
        features = getattr(camera, "features", None)
        if features is not None:
            features.hide_still = False      # StaticMask hides a still lamp in 5 s, long before clear records it
        font = Font.load(Path(cfg.font_path))
        display = build_display(cfg)
        try:
            runner = Runner(cfg, display, font, cal, [], calibration=Calibration(), strict=True)
            runner.loop(camera, audio, until=cal.done)
        except KeyboardInterrupt:
            pass
        finally:
            display.close()
    finally:
        for source in (camera, audio):
            source.close()
    if cal.result is None:
        print(f"calibrate: nothing saved ({cal.failed or 'stopped before the end'})")
        return 1
    print(f"calibrate: saved {data_dir / FILENAME}")
    return 0
