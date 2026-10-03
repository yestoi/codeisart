"""The Pi's AI Camera (IMX500) as the pose source: PoseNet runs on the sensor, the Pi decodes its three output
tensors into bodies (spec 6.1 as amended by docs/superpowers/specs/2026-10-02-pose-on-the-sensor-design.md).

The decoder is a port of tfjs posenet's multi-pose decoding (decodeMultiplePoses), written against the tensors the
rpicam-apps imx500_posenet stage documents: heatmaps [23, 31, 17] as log-odds, short offsets [23, 31, 34] (17 y
then 17 x, in input pixels), mid offsets [23, 31, 64] (forward y, forward x, backward y, backward x; 16 edges
each), on a 481x353 input with stride 16. Measured on the spike of 2026-10-02 (the review of that date): 30
tensors a second, 3 ms to decode on the Pi. picamera2 is imported inside open_imx500 only."""
from __future__ import annotations

import logging

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
    out = []
    for kp in range(NUM_KP):
        s = scores[:, :, kp]
        for y, x in zip(*np.where(s >= thr)):
            y0, y1 = max(0, y - LOCAL_MAX_RADIUS), min(h, y + LOCAL_MAX_RADIUS + 1)
            x0, x1 = max(0, x - LOCAL_MAX_RADIUS), min(w, x + LOCAL_MAX_RADIUS + 1)
            if s[y, x] >= s[y0:y1, x0:x1].max():
                out.append((float(s[y, x]), kp, int(y), int(x)))
    out.sort(reverse=True)
    return out


def _coords(kp: int, y: int, x: int, off: np.ndarray) -> np.ndarray:
    """A keypoint's (y, x) in input pixels from its heatmap cell and the short offsets."""
    return np.array([y * STRIDE + off[y, x, kp], x * STRIDE + off[y, x, kp + NUM_KP]], dtype=np.float32)


def _cell(pos: np.ndarray, h: int, w: int) -> tuple[int, int]:
    return (int(np.clip(round(pos[0] / STRIDE), 0, h - 1)), int(np.clip(round(pos[1] / STRIDE), 0, w - 1)))


def _traverse(edge: int, src: np.ndarray, target: int, scores, off, disp) -> tuple[float, np.ndarray]:
    h, w, _ = scores.shape
    y, x = _cell(src, h, w)
    pos = src + np.array([disp[y, x, edge], disp[y, x, edge + NUM_EDGES]], dtype=np.float32)
    for _ in range(REFINE_STEPS):
        pos = _coords(target, *_cell(pos, h, w), off)
    ty, tx = _cell(pos, h, w)
    return float(scores[ty, tx, target]), pos


def _decode_pose(root, scores, off, fwd, bwd) -> tuple[np.ndarray, np.ndarray]:
    score, kp, y, x = root
    kps = np.zeros((NUM_KP, 2), dtype=np.float32)
    ksc = np.zeros(NUM_KP, dtype=np.float32)
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


def decode_multiple(outputs, score_thr: float = 0.3, max_poses: int = 10,
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
    poses: list[tuple[np.ndarray, np.ndarray, float]] = []
    for root in _local_maxima(scores, score_thr):
        if len(poses) >= max_poses:
            break
        _, kp, y, x = root
        root_pos = _coords(kp, y, x, off)
        if any(((p[0][kp] - root_pos) ** 2).sum() <= sq for p in poses):
            continue
        kps, ksc = _decode_pose(root, scores, off, fwd, bwd)
        keep = np.ones(NUM_KP, dtype=bool)
        for pk, _, _ in poses:
            keep &= ((pk - kps) ** 2).sum(axis=1) > sq
        poses.append((kps, ksc, float((ksc * keep).sum() / NUM_KP)))
    poses.sort(key=lambda p: p[2], reverse=True)
    w, h = INPUT_SIZE
    return [(inst, [(float(k[1] / w), float(k[0] / h), float(c)) for k, c in zip(kps, ksc)])
            for kps, ksc, inst in poses]


class IMX500Pose:
    """The PoseDetector for the sensor: detect() ignores the frame and decodes the tensor in capture.metadata (the
    frame the capture just read); no tensor (the network still uploading, or a dropped one) is no body this
    capture. At most MAX_BODIES bodies, best first, reach the tracker: its assign() has no scipy on the Pi and
    stops at 6 by 6, and a crowd at the wall must not end the camera thread. A tensor the decoder does not know
    is logged once and is no body. imx is picamera2's IMX500 (get_outputs(metadata)); capture a Picamera2Capture.
    Coordinates need no crop correction: the network sees the whole sensor, as the 4:3 main stream does."""

    def __init__(self, capture, imx, min_instance: float = MIN_INSTANCE, max_bodies: int = MAX_BODIES):
        self._capture, self._imx, self.min_instance, self.max_bodies = capture, imx, min_instance, max_bodies
        self._complained = False

    def detect(self, bgr: np.ndarray, ts_ms: int) -> list[tuple[Keypoint, ...]]:
        metadata = self._capture.metadata
        if not metadata.get("CnnOutputTensor"):
            return []
        outputs = self._imx.get_outputs(metadata, add_batch=False)
        if outputs is None:
            return []
        try:
            poses = decode_multiple(outputs)
        except ValueError as e:
            if not self._complained:
                self._complained = True
                log.warning("imx500: %s; no bodies until it changes", e)
            return []
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
    and the network upload, which it shows as a progress bar when the sensor does not hold posenet yet), then the
    capture on that camera at the model's rate with BUFFER_COUNT buffers. Raises when picamera2 is missing or the
    camera does not open; the caller logs once. Call it on the main thread."""
    from picamera2 import Picamera2                                # here: apt's package, on the Pi only
    from picamera2.devices.imx500 import IMX500, NetworkIntrinsics

    from arcade.sources.capture_picamera2 import Picamera2Capture
    from arcade.sources.pose_mediapipe import CAPTURE_SIZE

    imx = IMX500(MODEL)
    intrinsics = imx.network_intrinsics or NetworkIntrinsics()
    intrinsics.task = "pose estimation"
    intrinsics.update_with_defaults()
    cam = Picamera2(imx.camera_num)
    imx.show_network_fw_progress_bar()          # the demos' order: after the camera object, before it starts
    capture = Picamera2Capture(CAPTURE_SIZE, camera=cam, frame_rate=float(intrinsics.inference_rate or 30),
                               buffer_count=BUFFER_COUNT)
    log.info("imx500: %s on camera %s", describe(imx), imx.camera_num)
    return capture, IMX500Pose(capture, imx)
