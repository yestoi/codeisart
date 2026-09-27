"""Named body poses for actors and the Copy Me game (spec 6.4, 8).

Each pose is 17 (dx, dy) offsets in COCO order, in units of body height, from the hip centre; y grows
downward. Only the offsets are stored so a pose fits any body size and position.
"""
from __future__ import annotations

_HEAD = ((0.0, -0.45), (-0.03, -0.47), (0.03, -0.47), (-0.06, -0.46), (0.06, -0.46))
_SHOULDERS = ((-0.12, -0.30), (0.12, -0.30))
_LEGS = ((-0.08, 0.0), (0.08, 0.0), (-0.08, 0.22), (0.08, 0.22), (-0.08, 0.45), (0.08, 0.45))


def _pose(left_elbow, right_elbow, left_wrist, right_wrist) -> tuple[tuple[float, float], ...]:
    return _HEAD + _SHOULDERS + (left_elbow, right_elbow, left_wrist, right_wrist) + _LEGS


POSES: dict[str, tuple[tuple[float, float], ...]] = {
    "stand": _pose((-0.16, -0.15), (0.16, -0.15), (-0.18, 0.0), (0.18, 0.0)),
    "arms_up": _pose((-0.16, -0.45), (0.16, -0.45), (-0.15, -0.60), (0.15, -0.60)),
    "t_pose": _pose((-0.24, -0.30), (0.24, -0.30), (-0.36, -0.30), (0.36, -0.30)),
}
