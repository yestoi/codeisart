"""The Sensed record (spec 5): the only input games see, built once per tick by the runner."""
from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from arcade.calibration import Calibration

(NOSE, LEFT_EYE, RIGHT_EYE, LEFT_EAR, RIGHT_EAR, LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_ELBOW,
 RIGHT_ELBOW, LEFT_WRIST, RIGHT_WRIST, LEFT_HIP, RIGHT_HIP, LEFT_KNEE, RIGHT_KNEE, LEFT_ANKLE,
 RIGHT_ANKLE) = range(17)

KEYPOINT_NAMES = ("nose", "left_eye", "right_eye", "left_ear", "right_ear", "left_shoulder",
                  "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist",
                  "left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle")

SKELETON = ((LEFT_SHOULDER, LEFT_ELBOW), (LEFT_ELBOW, LEFT_WRIST), (RIGHT_SHOULDER, RIGHT_ELBOW),
            (RIGHT_ELBOW, RIGHT_WRIST), (LEFT_SHOULDER, RIGHT_SHOULDER), (LEFT_SHOULDER, LEFT_HIP),
            (RIGHT_SHOULDER, RIGHT_HIP), (LEFT_HIP, RIGHT_HIP), (LEFT_HIP, LEFT_KNEE),
            (LEFT_KNEE, LEFT_ANKLE), (RIGHT_HIP, RIGHT_KNEE), (RIGHT_KNEE, RIGHT_ANKLE),
            (NOSE, LEFT_SHOULDER), (NOSE, RIGHT_SHOULDER))

MIN_CONF = 0.3
RAISE_TORSOS = 0.3               # the raise line sits this many torso lengths above the shoulder midpoint
REACH_WIDTHS = 1.5               # the reach box spans this many shoulder widths each side of the shoulder midpoint,
REACH_TOP_TORSOS = 1.05          # and from this many torso lengths above it (head plus a forearm) down to the hips
TORSO_PER_SHOULDER_WIDTH = 1.25  # torso length estimated from shoulder width when no hip is seen
NOSE_TO_HIP_PER_TORSO = 1.5      # scale estimated from the torso when the nose is not seen
TORSO_FLOOR = 0.1                # a torso shorter than this share of the box height is not measured (C22)
MOTION_GRID = (128, 64)          # (width, height) of the fixed grid scenario files and actors store motion on


@dataclass(frozen=True)
class Keypoint:
    x: float
    y: float
    conf: float = 1.0


def _clean(kp: Keypoint) -> Keypoint:
    x, y, conf = kp.x, kp.y, kp.conf
    bad = any(v is None or math.isnan(v) for v in (x, y, conf))
    if bad:
        return Keypoint(0.0, 0.0, 0.0)
    return Keypoint(min(1.0, max(0.0, x)), min(1.0, max(0.0, y)),
                    0.0 if not 0.0 <= x <= 1.0 or not 0.0 <= y <= 1.0 else min(1.0, max(0.0, conf)))


def _clamp01(v: float) -> float:
    return min(1.0, max(0.0, v))


def _mid(a: Keypoint, b: Keypoint) -> Keypoint | None:
    """The midpoint of the confident ones of a and b; one alone stands in for the pair."""
    seen = [k for k in (a, b) if k.conf >= MIN_CONF]
    if not seen:
        return None
    return Keypoint(sum(k.x for k in seen) / len(seen), sum(k.y for k in seen) / len(seen),
                    min(k.conf for k in seen))


@dataclass(frozen=True)
class Body:
    """One tracked person. Keypoints are normalized camera coordinates, already mirrored and smoothed.

    scale 0.0 means "measure it": the nose-to-mid-hip length, or 1.5 torso lengths without a nose.

    measured (C47): the scale is this person's measure. The tracker passes False while a track has never been
    seen with its nose and a hip (its scale is then the shoulder-width fallback, short on a real person), and
    input.Depth takes the first measure without a jump. A body built anywhere else is measured.
    torso_per_width (C46): this person's torso per shoulder width, learned by the tracker, which the torso
    without hips uses in place of TORSO_PER_SHOULDER_WIDTH; 0.0 (and anything not finite and over 0) is the default.
    """

    id: int
    box: tuple[float, float, float, float]
    keypoints: tuple[Keypoint, ...]
    vx: float = 0.0
    vy: float = 0.0
    scale: float = 0.0
    in_zone: bool = True
    zone_x: float = 0.5
    zone_y: float = 0.5
    seen_ago: float = 0.0
    measured: bool = True
    torso_per_width: float = 0.0

    def __post_init__(self):
        if len(self.keypoints) != 17:
            raise ValueError(f"a body has 17 keypoints, got {len(self.keypoints)}")
        object.__setattr__(self, "keypoints", tuple(_clean(k) for k in self.keypoints))
        try:
            ratio = float(self.torso_per_width)
        except (TypeError, ValueError, OverflowError):
            ratio = 0.0
        object.__setattr__(self, "torso_per_width", ratio if math.isfinite(ratio) and ratio > 0.0 else 0.0)
        if self.scale == 0.0:
            object.__setattr__(self, "scale", self._measured_scale())

    def _measured_scale(self) -> float:
        hip = self.hip_mid
        if self.nose.conf >= MIN_CONF and hip is not None:
            return math.hypot(self.nose.x - hip.x, self.nose.y - hip.y)
        return NOSE_TO_HIP_PER_TORSO * self.torso

    @property
    def nose(self) -> Keypoint:
        return self.keypoints[NOSE]

    @property
    def left_wrist(self) -> Keypoint:
        return self.keypoints[LEFT_WRIST]

    @property
    def right_wrist(self) -> Keypoint:
        return self.keypoints[RIGHT_WRIST]

    @property
    def shoulder_mid(self) -> Keypoint | None:
        """The midpoint of the confident shoulders, None without one.

        With one shoulder, its y stands in for the pair, but x comes from both hips, else a confident
        nose, else the one hip seen, else that shoulder: the centre (and so anchor, zone_x and the reach
        box) does not jump half a shoulder or hip width when one shoulder and one hip drop out.
        """
        left, right = self.keypoints[LEFT_SHOULDER], self.keypoints[RIGHT_SHOULDER]
        seen = [k for k in (left, right) if k.conf >= MIN_CONF]
        if len(seen) != 1:
            return _mid(left, right)
        one = seen[0]
        hips = (self.keypoints[LEFT_HIP], self.keypoints[RIGHT_HIP])
        if all(h.conf >= MIN_CONF for h in hips):
            x = (hips[0].x + hips[1].x) / 2
        elif self.nose.conf >= MIN_CONF:
            x = self.nose.x
        else:
            hip = self.hip_mid
            x = hip.x if hip is not None else one.x
        return Keypoint(x, one.y, one.conf)

    @property
    def hip_mid(self) -> Keypoint | None:
        return _mid(self.keypoints[LEFT_HIP], self.keypoints[RIGHT_HIP])

    @property
    def shoulder_width(self) -> float:
        """Distance between the shoulders, 0.0 unless both are confident."""
        a, b = self.keypoints[LEFT_SHOULDER], self.keypoints[RIGHT_SHOULDER]
        if a.conf < MIN_CONF or b.conf < MIN_CONF:
            return 0.0
        return math.hypot(a.x - b.x, a.y - b.y)

    @property
    def torso(self) -> float:
        """Shoulder midpoint to hip midpoint; from the shoulder width without hips (by torso_per_width, else
        TORSO_PER_SHOULDER_WIDTH); 0.0 when unknown."""
        s, h = self.shoulder_mid, self.hip_mid
        if s is not None and h is not None:
            return math.hypot(s.x - h.x, s.y - h.y)
        return self._torso_ratio * self.shoulder_width

    @property
    def _torso_ratio(self) -> float:
        return self.torso_per_width or TORSO_PER_SHOULDER_WIDTH

    @property
    def anchor(self) -> Keypoint | None:
        """What the tracker and place() follow: the shoulder midpoint, then the nose, then the hips."""
        s = self.shoulder_mid
        if s is not None:
            return s
        if self.nose.conf >= MIN_CONF:
            return self.nose
        return self.hip_mid

    @property
    def raise_line(self) -> float | None:
        """A wrist above this y is raised: 0.3 torso above the shoulders.

        The nose stands in without shoulders, and when the torso cannot be measured (one shoulder and no
        hip) or is under TORSO_FLOOR of the box height (side-on shoulders with the hips hidden, C22),
        because a line a hair above the shoulders would count a wrist at the collarbone; with neither,
        None, and nothing is raised.
        """
        s, torso = self.shoulder_mid, self.torso
        if s is not None and torso > 0.0 and torso >= TORSO_FLOOR * self.height:
            return s.y - RAISE_TORSOS * torso
        if self.nose.conf >= MIN_CONF:
            return self.nose.y
        return None

    @property
    def raised_wrist(self) -> Keypoint | None:
        """The higher confident wrist above the raise line, else None."""
        line = self.raise_line
        if line is None:
            return None
        best = None
        for w in (self.left_wrist, self.right_wrist):
            if w.conf >= MIN_CONF and w.y < line and (best is None or w.y < best.y):
                best = w
        return best

    @property
    def both_hands_up(self) -> bool:
        line = self.raise_line
        return line is not None and all(w.conf >= MIN_CONF and w.y < line
                                        for w in (self.left_wrist, self.right_wrist))

    def reach(self, kp: Keypoint) -> tuple[float, float]:
        """kp in the body-relative reach box (spec 7.3), (u, v) each clamped to 0..1.

        u runs across 1.5 shoulder widths each side of the shoulder midpoint; v runs from 1.05 torso
        above the shoulder midpoint (head plus a forearm) down to hip height. Without shoulders the
        body box is the frame of reference.
        """
        s, torso = self.shoulder_mid, self.torso
        width = self.shoulder_width or torso / self._torso_ratio
        if s is None or torso <= 0.0 or width <= 0.0:
            x0, y0, x1, y1 = self.box
            u = (kp.x - x0) / (x1 - x0) if x1 > x0 else 0.5
            v = (kp.y - y0) / (y1 - y0) if y1 > y0 else 0.5
        else:
            hip = self.hip_mid
            top = s.y - REACH_TOP_TORSOS * torso
            bottom = hip.y if hip is not None else s.y + torso
            u = (kp.x - (s.x - REACH_WIDTHS * width)) / (2 * REACH_WIDTHS * width)
            v = (kp.y - top) / (bottom - top)
        return (_clamp01(u), _clamp01(v))

    @property
    def cursor(self) -> tuple[float, float] | None:
        """The confident wrist further from its hip, through reach(); None without a confident wrist.

        Stateless: when the pointing wrist drops out for a frame the cursor jumps to the other wrist
        (15 percent of captures at the spec 6.4 dropout), so every consumer needs a grace period or hysteresis.
        """
        best, far = None, -1.0
        for wrist, hip_index in ((self.left_wrist, LEFT_HIP), (self.right_wrist, RIGHT_HIP)):
            if wrist.conf < MIN_CONF:
                continue
            own = self.keypoints[hip_index]
            ref = next((k for k in (own if own.conf >= MIN_CONF else None, self.hip_mid, self.shoulder_mid)
                        if k is not None), wrist)
            d = math.hypot(wrist.x - ref.x, wrist.y - ref.y)
            if d > far:
                best, far = wrist, d
        return None if best is None else self.reach(best)

    @property
    def center(self) -> tuple[float, float]:
        x0, y0, x1, y1 = self.box
        return ((x0 + x1) / 2, (y0 + y1) / 2)

    @property
    def height(self) -> float:
        return self.box[3] - self.box[1]

    @property
    def confidence(self) -> float:
        return sum(k.conf for k in self.keypoints) / 17


@dataclass(frozen=True)
class Blob:
    """A light source. x and y are clamped to 0..1 (NaN and None to 0), as keypoints are, so a blob that leaves the
    frame (a headlamp crossing it) never maps outside the wall."""

    x: float
    y: float
    size: float
    color: tuple[int, int, int]
    in_zone: bool = True
    _: dataclasses.KW_ONLY
    id: int = -1                  # the tracker's id, -1 untracked (C11, C17)
    vx: float = 0.0               # frame widths per second, the source's
    vy: float = 0.0

    def __post_init__(self):
        for name in ("x", "y"):
            v = getattr(self, name)
            object.__setattr__(self, name, 0.0 if v is None or math.isnan(v) else _clamp01(v))


@dataclass(frozen=True, kw_only=True)
class Audio:
    """Every field is a keyword: Audio(0.8, 1.0) would silently put 1.0 in level_smooth."""

    level: float = 0.0            # broadband RMS with slow gain, 0..1, for ambient visuals only
    level_smooth: float = 0.0     # level with 50 ms attack and 300 ms release
    peak: float = 0.0
    voice_db: float = -90.0       # absolute dBFS in the 300 Hz to 3.4 kHz band
    floor_db: float = -90.0       # rolling 30 s 90th percentile of voice_db
    voice: float = 0.0            # (voice_db - floor_db) / 30, clamped 0..1
    clap: bool = False
    onset: bool = False
    beat: bool = False
    bpm: float | None = None


def _in(zone: tuple[float, float, float, float], x: float, y: float) -> bool:
    x0, y0, x1, y1 = zone
    return x0 <= x <= x1 and y0 <= y <= y1


def place(body: Body, calibration: Calibration) -> Body:
    """body with in_zone, zone_x and zone_y from the calibration (spec 6.6). Actors and the tracker call it.

    The anchor (shoulders, then nose, then hips; the box centre without any) maps into the zone, 0..1
    across the mat and clamped. In the zone means the anchor inside it and the body at least min_height tall.
    """
    x0, y0, x1, y1 = calibration.zone
    a = body.anchor
    ax, ay = (a.x, a.y) if a is not None else body.center
    inside = _in(calibration.zone, ax, ay) and body.height >= calibration.min_height
    return dataclasses.replace(body, in_zone=inside, zone_x=_clamp01((ax - x0) / (x1 - x0)),
                               zone_y=_clamp01((ay - y0) / (y1 - y0)))


def place_blob(blob: Blob, calibration: Calibration) -> Blob:
    """blob with in_zone from the calibration zone. The blob must be in the zone's space, the mirrored
    display space of the keypoints: a blob source mirrors x as mirror_keypoints does."""
    return dataclasses.replace(blob, in_zone=_in(calibration.zone, blob.x, blob.y))


def _resample(motion: np.ndarray, width: int, height: int) -> np.ndarray:
    """Nearest-cell resample that keeps every lit cell: a shrinking axis ORs the source cells it covers."""
    rows = (np.arange(height) * motion.shape[0]) // height
    cols = (np.arange(width) * motion.shape[1]) // width
    grid = np.logical_or.reduceat(motion.astype(bool), rows, axis=0)
    return np.logical_or.reduceat(grid, cols, axis=1)


@dataclass(frozen=True, eq=False)
class Sensed:
    """Every field after t is a keyword: Sensed(t, bodies) would silently put the bodies in camera_t."""

    t: float                                     # seconds since runner start
    _: dataclasses.KW_ONLY
    camera_t: float = 0.0                        # capture time of the newest camera frame, on the runner clock
    camera_fresh: bool = False                   # true on the tick a new camera frame arrived
    camera_seq: int = 0
    bodies: tuple[Body, ...] = ()                # tracked, stable ids, largest scale first
    player: Body | None = None                   # the locked player (spec 7.2), set by the runner
    player2: Body | None = None
    present: bool = False                        # someone is in the zone, with hysteresis, set by the runner
    blobs: tuple[Blob, ...] = ()                 # light sources, brightest first, at most 8
    motion: np.ndarray = field(default_factory=lambda: np.zeros((0, 0), bool))   # bool (height, width)
    audio: Audio = field(default_factory=Audio)

    def __post_init__(self):
        # One grid is shared by every tick that holds it (degrade, with_motion), so the record keeps a
        # read-only view; the producer's own array stays writeable, but must not change after hand-over.
        # None (an old scenario record) means the empty grid.
        motion = np.zeros((0, 0), bool) if self.motion is None else np.asarray(self.motion, bool)
        motion = motion.view()
        motion.flags.writeable = False
        object.__setattr__(self, "motion", motion)

    def with_motion(self, size: tuple[int, int]) -> "Sensed":
        """This record with motion as a (height, width) grid for size (width, height).

        An empty grid becomes all False; a grid of another shape is resampled. Bodies are never
        rasterized into it.
        """
        w, h = size
        if self.motion.shape == (h, w):
            return self
        if self.motion.size == 0:
            return dataclasses.replace(self, motion=np.zeros((h, w), bool))
        return dataclasses.replace(self, motion=_resample(self.motion, w, h))
