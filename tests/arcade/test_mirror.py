import pytest

from arcade.sensed import LEFT_WRIST, RIGHT_WRIST, Keypoint
from arcade.sources.mirror import mirror_box, mirror_keypoints


def pts():
    out = [Keypoint(0.5, 0.5, 0.9) for _ in range(17)]
    out[RIGHT_WRIST] = Keypoint(0.2, 0.3, 0.8)    # the camera sees the person's right hand on the image left
    out[LEFT_WRIST] = Keypoint(0.7, 0.6, 0.4)
    return tuple(out)


def test_mirror_flips_x_keeps_labels():
    m = mirror_keypoints(pts())
    assert isinstance(m, tuple) and len(m) == 17
    assert m[RIGHT_WRIST].x == pytest.approx(0.8) and (m[RIGHT_WRIST].y, m[RIGHT_WRIST].conf) == (0.3, 0.8)
    assert m[LEFT_WRIST].x == pytest.approx(0.3) and (m[LEFT_WRIST].y, m[LEFT_WRIST].conf) == (0.6, 0.4)
    assert mirror_box((0.1, 0.2, 0.3, 0.9)) == pytest.approx((0.7, 0.2, 0.9, 0.9))


def test_mirror_twice_is_identity():
    original = pts()
    back = mirror_keypoints(mirror_keypoints(original))
    for a, b in zip(original, back):
        assert (b.x, b.y, b.conf) == pytest.approx((a.x, a.y, a.conf))
    assert mirror_box(mirror_box((0.1, 0.2, 0.3, 0.9))) == pytest.approx((0.1, 0.2, 0.3, 0.9))
