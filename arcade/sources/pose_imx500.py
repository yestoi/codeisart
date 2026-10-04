"""The Pi's AI Camera (IMX500) as the pose source: PoseNet runs on the sensor, the Pi decodes its three output
tensors into bodies (spec 6.1 as amended by docs/superpowers/specs/2026-10-02-pose-on-the-sensor-design.md).

The decoder is a port of tfjs posenet's multi-pose decoding (decodeMultiplePoses), written against the tensors the
rpicam-apps imx500_posenet stage documents: heatmaps [23, 31, 17] as log-odds, short offsets [23, 31, 34] (17 y
then 17 x, in input pixels), mid offsets [23, 31, 64] (forward y, forward x, backward y, backward x; 16 edges
each), on a 481x353 input with stride 16. Measured on the spike of 2026-10-02 (the review of that date): 30
tensors a second; a 20-pose decode is a few ms on the Pi (see the note above _coords). picamera2 is imported inside open_imx500 only."""
from __future__ import annotations

import logging
import time

import numpy as np

from arcade.sensed import Keypoint

log = logging.getLogger("arcade")

MODEL = "/usr/share/imx500-models/imx500_network_posenet.rpk"
INPUT_SIZE = (481, 353)                   # the network's input, w x h; coordinates are normalised by it
STRIDE = 16
SHAPES = ((23, 31, 17), (23, 31, 34), (23, 31, 64))
NUM_KP = 17
BUFFER_COUNT = 12                         # picamera2's IMX500 demos run with 12 buffers
# parent -> child, tfjs posenet's poseChain (COCO indices)
EDGES = ((0, 1), (1, 3), (0, 2), (2, 4), (0, 5), (5, 7), (7, 9), (5, 11), (11, 13), (13, 15),
         (0, 6), (6, 8), (8, 10), (6, 12), (12, 14), (14, 16))
NUM_EDGES = len(EDGES)
LOCAL_MAX_RADIUS = 1                      # heatmap cells: a root is the maximum of its 3x3 neighbourhood
REFINE_STEPS = 2                          # offset refinements after a displacement step (tfjs: 2)
MIN_INSTANCE = 0.3                        # a body's instance score (mean keypoint score) to count; 0.5 clears
                                          # most second bodies in the spike's samples (the knob if ghosts appear)
MAX_BODIES = 4                            # bodies handed to the tracker a capture (assign() without scipy: 6 at most)
MAX_POSES = 20                            # roots the decoder follows: two or three same-person duplicates follow each
                                          # real body, so 10 would spend the budget before a crowd's fourth person
LAG_EVERY = 1.0                           # s between two sensor-to-decode lines at DEBUG (run -v)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _check(outputs) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    arrs = [np.asarray(o, dtype=np.float32) for o in outputs]
    if len(arrs) != 3:
        raise ValueError(f"posenet gives 3 tensors, got {len(arrs)}")
    shapes = tuple(tuple(int(d) for d in a.shape) for a in arrs)
    if shapes != SHAPES:
        raise ValueError(f"not posenet's tensors: shapes {shapes}, wanted {SHAPES} (the sensor's firmware or model "
                         f"file is not the posenet this decoder knows)")
    return arrs[0], arrs[1], arrs[2]


def _local_maxima(scores: np.ndarray, thr: float) -> list[tuple[float, int, int, int]]:
    """(score, keypoint, row, col) of every cell at or above thr that is the maximum of its neighbourhood, best first."""
    h, w, _ = scores.shape
    r = LOCAL_MAX_RADIUS
    padded = np.pad(scores, ((r, r), (r, r), (0, 0)), constant_values=-np.inf)
    around = scores.copy()                                   # each cell's neighbourhood maximum, itself included
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            np.maximum(around, padded[r + dy:r + dy + h, r + dx:r + dx + w, :], out=around)
    ys, xs, kps = np.nonzero((scores >= thr) & (scores >= around))
    out = [(float(scores[y, x, k]), k, y, x) for y, x, k in zip(ys.tolist(), xs.tolist(), kps.tolist())]
    out.sort(reverse=True)
    return out


# The walk below is plain Python on scalars, indexing the tensors one element at a time. Night One (2026-10-03): the
# first port did the same arithmetic on 2-element numpy arrays (np.clip, sums), and with a crowd at the wall the
# decoder followed MAX_POSES roots at 30 tensors a second in 40 to 50 ms each on the Pi: a whole core, and the GIL
# with it, so the arcade's 30 fps loop starved and Dodge went jerky. Scalars decode the same 20 poses in a few ms.

def _coords(kp: int, y: int, x: int, off: np.ndarray) -> tuple[float, float]:
    """A keypoint's (y, x) in input pixels from its heatmap cell and the short offsets."""
    return (y * STRIDE + float(off[y, x, kp]), x * STRIDE + float(off[y, x, kp + NUM_KP]))


def _cell(pos: tuple[float, float], h: int, w: int) -> tuple[int, int]:
    cy, cx = pos[0] / STRIDE, pos[1] / STRIDE
    return (0 if cy < 0 else h - 1 if cy > h - 1 else int(round(cy)),
            0 if cx < 0 else w - 1 if cx > w - 1 else int(round(cx)))


def _traverse(edge: int, src: tuple[float, float], target: int, scores, off, disp) -> tuple[float, tuple[float, float]]:
    h, w, _ = scores.shape
    y, x = _cell(src, h, w)
    pos = (src[0] + float(disp[y, x, edge]), src[1] + float(disp[y, x, edge + NUM_EDGES]))
    for _ in range(REFINE_STEPS):
        pos = _coords(target, *_cell(pos, h, w), off)
    ty, tx = _cell(pos, h, w)
    return float(scores[ty, tx, target]), pos


def _decode_pose(root, scores, off, fwd, bwd) -> tuple[list[tuple[float, float]], list[float]]:
    score, kp, y, x = root
    kps: list[tuple[float, float]] = [(0.0, 0.0)] * NUM_KP
    ksc = [0.0] * NUM_KP
    kps[kp], ksc[kp] = _coords(kp, y, x, off), score
    for e in reversed(range(NUM_EDGES)):
        parent, child = EDGES[e]
        if ksc[child] > 0 and ksc[parent] == 0:
            ksc[parent], kps[parent] = _traverse(e, kps[child], parent, scores, off, bwd)
    for e in range(NUM_EDGES):
        parent, child = EDGES[e]
        if ksc[parent] > 0 and ksc[child] == 0:
            ksc[child], kps[child] = _traverse(e, kps[parent], child, scores, off, fwd)
    return kps, ksc


def decode_multiple(outputs, score_thr: float = 0.3, max_poses: int = MAX_POSES,
                    nms_radius_px: float = 20.0) -> list[tuple[float, list[tuple[float, float, float]]]]:
    """Every body in the three tensors, best first: (instance score, 17 (x, y, conf) in COCO order), x and y
    normalised by INPUT_SIZE and NOT clipped (a point past the frame stays past it, as MediaPipe's would; Body's
    _clean clamps it and zeroes its confidence for both detectors alike), conf the keypoint's sigmoid score. The
    instance score is the mean of the keypoint scores not already claimed by an earlier body (within
    nms_radius_px), so a same-root duplicate scores near 0. ValueError when the tensors are not posenet's."""
    heat, off, mid = _check(outputs)
    scores = _sigmoid(heat)
    fwd, bwd = mid[:, :, :2 * NUM_EDGES], mid[:, :, 2 * NUM_EDGES:]
    sq = nms_radius_px ** 2
    poses: list[tuple[list[tuple[float, float]], list[float], float]] = []
    taken = np.empty((max_poses, NUM_KP, 2), dtype=np.float32)       # the poses' keypoints so far, for the nms
    for root in _local_maxima(scores, score_thr):
        n = len(poses)
        if n >= max_poses:
            break
        _, kp, y, x = root
        ry, rx = _coords(kp, y, x, off)
        if any((p[0][kp][0] - ry) ** 2 + (p[0][kp][1] - rx) ** 2 <= sq for p in poses):
            continue
        kps, ksc = _decode_pose(root, scores, off, fwd, bwd)
        arr = np.array(kps, dtype=np.float32)
        if n:
            keep = (((taken[:n] - arr) ** 2).sum(axis=2) > sq).all(axis=0)
            inst = float((np.array(ksc, dtype=np.float32) * keep).sum() / NUM_KP)
        else:
            inst = float(np.float32(sum(ksc)) / NUM_KP)
        taken[n] = arr
        poses.append((kps, ksc, inst))
    poses.sort(key=lambda p: p[2], reverse=True)
    w, h = INPUT_SIZE
    return [(inst, [(float(k[1] / w), float(k[0] / h), float(c)) for k, c in zip(kps, ksc)])
            for kps, ksc, inst in poses]


def _now_ns() -> int:
    """The clock SensorTimestamp is on: CLOCK_BOOTTIME on Linux (the Pi), the monotonic clock elsewhere."""
    return time.clock_gettime_ns(getattr(time, "CLOCK_BOOTTIME", time.CLOCK_MONOTONIC))


class IMX500Pose:
    """The PoseDetector for the sensor: detect() ignores the frame and decodes the tensor in capture.metadata (the
    frame the capture just read); no tensor (the network still uploading, or a dropped one) is no body this
    capture. At most MAX_BODIES bodies, best first, reach the tracker: its assign() has no scipy on the Pi and
    stops at 6 by 6, and a crowd at the wall must not end the camera thread. A tensor the decoder (or picamera2's
    get_outputs) cannot read is logged once and is no body; the thread lives. imx is picamera2's IMX500
    (get_outputs(metadata)); capture a Picamera2Capture. Coordinates need no crop correction: the network sees the
    whole sensor, as the 4:3 main stream does.

    last_sensor_ms is the age of the last tensor's frame at decode, from the request's SensorTimestamp (ns on the
    boot clock): the sensor's share of the lag, which the runner's capture-age line leaves out. At DEBUG (run -v)
    its median and max are logged once a second."""

    def __init__(self, capture, imx, min_instance: float = MIN_INSTANCE, max_bodies: int = MAX_BODIES):
        self._capture, self._imx, self.min_instance, self.max_bodies = capture, imx, min_instance, max_bodies
        self._complained = False
        self.last_sensor_ms: float | None = None
        self._sensor_ages: list[float] = []
        self._sensor_logged: int | None = None

    def _note_sensor_age(self, metadata: dict) -> None:
        stamp = metadata.get("SensorTimestamp")
        if not stamp:
            return
        now = _now_ns()
        self.last_sensor_ms = (now - stamp) / 1e6
        if not log.isEnabledFor(logging.DEBUG):
            return
        self._sensor_ages.append(self.last_sensor_ms)
        if self._sensor_logged is None:
            self._sensor_logged = now
        elif now - self._sensor_logged >= LAG_EVERY * 1e9:
            ages = sorted(self._sensor_ages)
            log.debug("sensor to decode: median %.0f ms, max %.0f ms (%d tensors)",
                      ages[len(ages) // 2], ages[-1], len(ages))
            self._sensor_ages, self._sensor_logged = [], now

    def detect(self, bgr: np.ndarray, ts_ms: int) -> list[tuple[Keypoint, ...]]:
        metadata = self._capture.metadata
        if not metadata.get("CnnOutputTensor"):
            return []
        try:
            outputs = self._imx.get_outputs(metadata, add_batch=False)
            if outputs is None:
                return []
            poses = decode_multiple(outputs)
        except Exception as e:
            if not self._complained:
                self._complained = True
                log.warning("imx500: %s; no bodies until it changes", e)
            return []
        self._note_sensor_age(metadata)
        kept = [pts for inst, pts in poses if inst >= self.min_instance][:self.max_bodies]   # poses are best first
        return [tuple(Keypoint(x, y, c) for x, y, c in pts) for pts in kept]

    def close(self) -> None:
        """The capture owns the camera; the sensor keeps its network."""

    @property
    def imx(self):
        """picamera2's IMX500 object, for the doctor's describe()."""
        return self._imx


def describe(imx) -> str:
    """'posenet 30/s': the model and its stated inference rate, for the doctor's line."""
    intrinsics = getattr(imx, "network_intrinsics", None)
    rate = getattr(intrinsics, "inference_rate", None)
    return f"posenet {rate:g}/s" if rate else "posenet"


def open_imx500(cfg, size: tuple[int, int]):
    """(Picamera2Capture, IMX500Pose) for camera = "imx500": the IMX500 object first (it owns the camera number
    and the network upload, which runs on the sensor when it does not hold posenet yet; no progress bar: picamera2's
    is a non-daemon child that can keep the process from exiting when the camera fails after it started, and the
    doctor prints its own notice), then the capture on that camera at the model's rate with BUFFER_COUNT buffers.
    Raises when picamera2 is missing or the camera does not open; the caller logs once. Call it on the main
    thread."""
    from picamera2 import Picamera2                                # here: apt's package, on the Pi only
    from picamera2.devices.imx500 import IMX500, NetworkIntrinsics

    from arcade.sources.capture_picamera2 import Picamera2Capture
    from arcade.sources.pose_mediapipe import CAPTURE_SIZE

    imx = IMX500(MODEL)
    intrinsics = imx.network_intrinsics or NetworkIntrinsics()
    intrinsics.task = "pose estimation"
    intrinsics.update_with_defaults()
    cam = Picamera2(imx.camera_num)
    capture = Picamera2Capture(CAPTURE_SIZE, camera=cam, frame_rate=float(intrinsics.inference_rate or 30),
                               buffer_count=BUFFER_COUNT)
    log.info("imx500: %s on camera %s", describe(imx), imx.camera_num)
    return capture, IMX500Pose(capture, imx)
