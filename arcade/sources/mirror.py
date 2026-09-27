"""The one place x is flipped (spec 5): after inference on both platforms, never swapping labels."""
from __future__ import annotations

from typing import Iterable

from arcade.sensed import Keypoint


def mirror_keypoints(keypoints: Iterable[Keypoint]) -> tuple[Keypoint, ...]:
    """x becomes 1 - x. Index order and confidence are kept, so RIGHT_WRIST is still the person's
    right wrist, and with the flip it lands on the right of the wall."""
    return tuple(Keypoint(1.0 - k.x, k.y, k.conf) for k in keypoints)


def mirror_box(box: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = box
    return (1.0 - x1, y0, 1.0 - x0, y1)
