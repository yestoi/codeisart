"""Light sources and the motion grid from a BGR camera frame (spec 5, 6.1; core Task 15 as amended; C11, C17).
Needs no model."""
from __future__ import annotations

import colorsys
import dataclasses
import math

import cv2
import numpy as np

from arcade.calibration import Calibration
from arcade.sensed import MOTION_GRID, Blob, place_blob

LIGHT_V = 220          # a light's core: value (the largest channel) at or above this
HALO_PX = 3            # the halo: the ring this many pixels around the core
HALO_S = 0.5           # whose mean colour has at least this saturation (a white lamp's glow is white too)
MAX_AREA = 0.005       # a core over this share of the frame is a lamp or floodlight, not something carried
MIN_AREA = 4           # pixels: the draft's floor under a core
MAX_BLOBS = 8          # spec 5: at most 8, largest first
SCAN_BLOBS = 32        # FrameFeatures tracks and masks this many before keeping MAX_BLOBS, so still scenery
                       # larger than a carried light does not take the 8 places and hide it
MATCH_DIST = 0.1       # frame widths: a blob this near a blob of the previous capture keeps its id
STATIC_SECONDS = 5.0   # a blob still this long is scenery, masked until it moves
STATIC_MOVE = 0.01     # frame widths: moving less than this from where it stopped is still
FRAME_ASPECT = 4 / 3   # the camera's width over its height (both streams are 4:3) until a frame gives its own

MOTION_T = 0.25        # a pixel moved: the two median-normalised frames differ by more than this
CELL_FILL = 0.2        # a cell is lit when more than this share of its pixels moved
SHAKE_SHARE = 0.35     # more than this share of the cells lit is a shake: the grid is empty
WALL_ASPECT = MOTION_GRID[0] / MOTION_GRID[1]    # the wall's width over its height (128x64, Q82)

_HALO = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * HALO_PX + 1, 2 * HALO_PX + 1))


def find_blobs(frame_bgr: np.ndarray, max_blobs: int = MAX_BLOBS, min_area: int = MIN_AREA) -> tuple[Blob, ...]:
    """The light sources in a BGR frame, in camera coordinates (not mirrored), largest first, at most max_blobs.

    A light is a component of pixels with value at or above LIGHT_V, between min_area pixels and MAX_AREA of the
    frame, whose HALO_PX ring has a mean colour of saturation HALO_S or more. Its colour is the halo's hue at full
    saturation, at the value of the core's mean colour (cv2.mean over the component's bounding box with its mask):
    an LED's core saturates white, so the core alone would give a pastel. size is sqrt(area) / frame width.
    """
    h, w = frame_bgr.shape[:2]
    b, g, r = cv2.split(frame_bgr)
    bright = (cv2.max(cv2.max(b, g), r) >= LIGHT_V).astype(np.uint8)
    n, labels, stats, centroids = cv2.connectedComponentsWithStats(bright, connectivity=8)
    if n <= 1:
        return ()
    areas = stats[1:, cv2.CC_STAT_AREA]
    max_area = MAX_AREA * w * h
    found = []
    for i in (np.argsort(-areas, kind="stable") + 1).tolist():
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area < min_area:
            break
        cx, cy = (float(v) for v in centroids[i])
        if area > max_area or not (math.isfinite(cx) and math.isfinite(cy)):   # C17: Blob would make NaN a 0.0
            continue
        color = _light_color(frame_bgr, bright, labels, stats[i], i)
        if color is None:
            continue
        found.append(Blob((cx + 0.5) / w, (cy + 0.5) / h, math.sqrt(area) / w, color))
        if len(found) == max_blobs:
            break
    return tuple(found)


def _light_color(frame_bgr: np.ndarray, bright: np.ndarray, labels: np.ndarray, stat: np.ndarray,
                 i: int) -> tuple[int, int, int] | None:
    """The light's RGB colour, or None when its halo is not saturated."""
    h, w = bright.shape
    x, y, bw, bh = (int(v) for v in stat[:4])
    x0, y0 = max(0, x - HALO_PX), max(0, y - HALO_PX)
    x1, y1 = min(w, x + bw + HALO_PX), min(h, y + bh + HALO_PX)
    core = (labels[y0:y1, x0:x1] == i).astype(np.uint8)
    ring = cv2.dilate(core, _HALO)
    ring[bright[y0:y1, x0:x1] > 0] = 0            # the halo is not lit core, this component's or another's
    if not ring.any():
        return None
    hb, hg, hr, _ = cv2.mean(frame_bgr[y0:y1, x0:x1], mask=ring)
    hue, saturation, _ = colorsys.rgb_to_hsv(hr / 255.0, hg / 255.0, hb / 255.0)
    if saturation < HALO_S:
        return None
    cb, cg, cr, _ = cv2.mean(frame_bgr[y:y + bh, x:x + bw], mask=core[y - y0:y - y0 + bh, x - x0:x - x0 + bw])
    red, green, blue = colorsys.hsv_to_rgb(hue, 1.0, max(cb, cg, cr) / 255.0)
    return (round(red * 255), round(green * 255), round(blue * 255))


def motion_grid(prev_gray: np.ndarray, gray: np.ndarray, zone: tuple[float, float, float, float],
                size: tuple[int, int]) -> np.ndarray:
    """The cells that moved between two grey frames, bool (height, width) for size (width, height) (spec 5).

    Each frame is blurred 5x5 and divided by its own median, so an exposure step moves nothing; a pixel moves
    when the two differ by more than MOTION_T. The frame is flipped left to right (the zone is in the mirrored
    space the keypoints use), cropped to the zone at the wall's aspect (_crop), and downsampled to size; a cell
    is lit when more than CELL_FILL of it moved. More than SHAKE_SHARE of the cells lit is the camera moving,
    not people: the grid is then empty, shape (0, 0), and the caller counts a shake.
    """
    moving = cv2.absdiff(_normalised(prev_gray), _normalised(gray)) > MOTION_T
    moving = moving[:, ::-1]
    r0, r1, c0, c1 = _crop(moving.shape, zone)
    fill = cv2.resize(moving[r0:r1, c0:c1].astype(np.float32), size, interpolation=cv2.INTER_AREA)
    lit = fill > CELL_FILL
    if lit.mean() > SHAKE_SHARE:
        return np.zeros((0, 0), bool)
    return lit


def _normalised(gray: np.ndarray) -> np.ndarray:
    blurred = cv2.blur(gray, (5, 5))
    return blurred.astype(np.float32) / max(_median(blurred), 1.0)


def _median(gray: np.ndarray) -> float:
    """The median of a uint8 frame, from its histogram (np.median sorts: 0.12 ms at 160x120)."""
    counts = np.cumsum(np.bincount(gray.ravel(), minlength=256))
    return float(np.searchsorted(counts, (counts[-1] + 1) // 2))


def _crop(shape: tuple[int, int], zone: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    """(r0, r1, c0, c1): the zone's columns, and rows at the wall's aspect centred on the zone's middle, inside
    the frame. The crop keeps the zone's width so that a grid column is the zone_x a body there has."""
    h, w = shape
    x0, y0, x1, y1 = zone
    c0 = min(w - 1, round(x0 * w))
    c1 = max(c0 + 1, min(w, round(x1 * w)))
    rows = max(1, min(h, round((c1 - c0) / WALL_ASPECT)))
    r0 = min(max(0, round((y0 + y1) / 2 * h - rows / 2)), h - rows)
    return r0, r0 + rows, c0, c1


def _fw(dx: float, dy: float, aspect: float) -> float:
    """A step in frame widths: y is in frame heights, aspect is the frame's width over its height."""
    return math.hypot(dx, dy / aspect)


class BlobTracker:
    """Ids and velocities for the blobs of each capture (C11, C17). A blob takes the id of the nearest blob of the
    previous capture within MATCH_DIST frame widths, nearest pairs first, one each; any other gets a new id, from 1
    up and never reused, and vx, vy 0. vx, vy are the matched step over the time between the captures, in the
    blobs' own units per second (x in frame widths, y in frame heights, as Body.vx and vy); a repeated capture
    time keeps the last velocity. There is no coasting: a blob missing for a capture is new when it returns."""

    def __init__(self, aspect: float = FRAME_ASPECT):
        self.aspect = aspect
        self._last: tuple[Blob, ...] = ()
        self._t = 0.0
        self._next_id = 1

    def update(self, blobs: tuple[Blob, ...], t: float) -> tuple[Blob, ...]:
        pairs = sorted((_fw(b.x - a.x, b.y - a.y, self.aspect), j, i)
                       for i, a in enumerate(self._last) for j, b in enumerate(blobs))
        match: dict[int, Blob] = {}
        taken: set[int] = set()
        for d, j, i in pairs:
            if d > MATCH_DIST:
                break
            if j not in match and i not in taken:
                match[j] = self._last[i]
                taken.add(i)
        dt = t - self._t
        out = []
        for j, b in enumerate(blobs):
            a = match.get(j)
            if a is None:
                out.append(dataclasses.replace(b, id=self._next_id, vx=0.0, vy=0.0))
                self._next_id += 1
            elif dt > 0.0:
                out.append(dataclasses.replace(b, id=a.id, vx=(b.x - a.x) / dt, vy=(b.y - a.y) / dt))
            else:
                out.append(dataclasses.replace(b, id=a.id, vx=a.vx, vy=a.vy))
        self._last, self._t = tuple(out), t
        return self._last


class StaticMask:
    """Hides a tracked blob that has stayed within STATIC_MOVE frame widths of where it stopped for STATIC_SECONDS
    (scenery: a lamp, a lit sign), until it moves that far; it is then shown and its clock starts again. Keyed by
    the tracker's id; an untracked blob (id -1) is always shown."""

    def __init__(self, aspect: float = FRAME_ASPECT):
        self.aspect = aspect
        self._still: dict[int, tuple[float, float, float]] = {}    # id -> (x, y, since)

    def update(self, blobs: tuple[Blob, ...], t: float) -> tuple[Blob, ...]:
        still, shown = {}, []
        for b in blobs:
            if b.id < 0:
                shown.append(b)
                continue
            x, y, since = self._still.get(b.id, (b.x, b.y, t))
            if _fw(b.x - x, b.y - y, self.aspect) >= STATIC_MOVE:
                x, y, since = b.x, b.y, t
            still[b.id] = (x, y, since)
            if t - since < STATIC_SECONDS - 1e-9:
                shown.append(b)
        self._still = still
        return tuple(shown)


class FrameFeatures:
    """Blobs and the motion grid of each camera frame (spec 6.1), for the camera sources (wired in iteration 21).

    update(frame_bgr, t) takes a BGR frame of any size (spec 6.1: the low-resolution stream, about 160 by 120) and
    its capture time, and returns (blobs, motion): the light sources mirrored as mirror_keypoints mirrors keypoints
    (x becomes 1 - x), tracked (BlobTracker), the still ones masked (StaticMask), largest first, at most MAX_BLOBS,
    each placed against the calibration zone (place_blob sets in_zone); and the motion grid for size (width,
    height): all False on the first frame (and after a change of frame size), empty (0, 0) on a shake, which
    shakes counts."""

    def __init__(self, size: tuple[int, int] = (160, 120), calibration: Calibration | None = None):
        self.size = size
        self.calibration = calibration or Calibration()
        self.shakes = 0
        self.tracker = BlobTracker()
        self.mask = StaticMask()
        self._prev: np.ndarray | None = None

    def update(self, frame_bgr: np.ndarray, t: float) -> tuple[tuple[Blob, ...], np.ndarray]:
        h, w = frame_bgr.shape[:2]
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        if self._prev is None or self._prev.shape != gray.shape:
            motion = np.zeros((self.size[1], self.size[0]), bool)
        else:
            motion = motion_grid(self._prev, gray, self.calibration.zone, self.size)
            if motion.size == 0:
                self.shakes += 1
        self._prev = gray
        self.tracker.aspect = self.mask.aspect = w / h
        found = find_blobs(frame_bgr, max_blobs=SCAN_BLOBS)    # MAX_BLOBS after the mask: lamps do not crowd out
        mirrored = tuple(dataclasses.replace(b, x=1.0 - b.x) for b in found)
        shown = self.mask.update(self.tracker.update(mirrored, t), t)[:MAX_BLOBS]
        return tuple(place_blob(b, self.calibration) for b in shown), motion
