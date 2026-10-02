"""Named body poses for actors and the Copy Me game (spec 6.4, 8). Copy Me's ladder of them is in
arcade/games/copyme.py (LADDER).

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
    # Copy Me's targets (spec 8 row 1). Angles are read with x times the frame's 4:3 aspect, so "45 degrees" is
    # dx * 4/3 equal to dy. One arm up, the other as stand:
    "right_up": _pose((-0.16, -0.15), (0.16, -0.45), (-0.18, 0.0), (0.15, -0.60)),
    "left_up": _pose((-0.16, -0.45), (0.16, -0.15), (-0.15, -0.60), (0.18, 0.0)),
    # Both arms up and out at 45 degrees.
    "y_pose": _pose((-0.20, -0.41), (0.20, -0.41), (-0.28, -0.52), (0.28, -0.52)),
    # Upper arms level, forearms straight up.
    "flex": _pose((-0.23, -0.30), (0.23, -0.30), (-0.23, -0.45), (0.23, -0.45)),
    # The left arm up and out at 45, the right down and out at 45 (near stand's, so only the left is judged).
    "airplane": _pose((-0.20, -0.41), (0.20, -0.19), (-0.28, -0.52), (0.28, -0.08)),
    # The left hand on the hip (elbow out, forearm back in), the right arm up and out at 45.
    "disco": _pose((-0.26, -0.16), (0.20, -0.41), (-0.10, -0.04), (0.28, -0.52)),
    # The left hand on the hip, the right upper arm level with its forearm straight up.
    "teapot": _pose((-0.26, -0.16), (0.23, -0.30), (-0.10, -0.04), (0.23, -0.45)),
}
