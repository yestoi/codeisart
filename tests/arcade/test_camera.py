"""The camera base (ThreadedCamera), the body tracker and assign() (spec 5, 6; core Task 16 amendment)."""
import itertools
import math
import threading
import zlib

import pytest

from arcade.calibration import Calibration
from arcade.sensed import Body, Keypoint
from arcade.sources.actors import body_box, make_keypoints
from arcade.sources.camera import COAST_SECONDS, DROP_SECONDS, STALE_SECONDS, BodyTracker, ThreadedCamera, assign


def det(cx, cy=0.5, h=0.5, conf=1.0):
    kps = make_keypoints(cx, cy, h, conf=conf)
    return (body_box(kps), kps)


class FakeClock:
    def __init__(self, t=100.0):
        self.t = t

    def __call__(self):
        return self.t


# ----- assign -----

def brute(cost):
    rows, cols = len(cost), len(cost[0]) if cost else 0
    best = None
    if rows <= cols:
        for perm in itertools.permutations(range(cols), rows):
            total = sum(cost[r][c] for r, c in zip(range(rows), perm))
            if best is None or total < best[0]:
                best = (total, sorted(zip(range(rows), perm)))
    else:
        for perm in itertools.permutations(range(rows), cols):
            total = sum(cost[r][c] for r, c in zip(perm, range(cols)))
            if best is None or total < best[0]:
                best = (total, sorted(zip(perm, range(cols))))
    return best


@pytest.mark.parametrize("shape", [(1, 1), (2, 2), (2, 5), (5, 2), (3, 4), (6, 6)])
def test_assign_finds_the_global_minimum(shape):
    seed = zlib.crc32(f"assign-{shape}".encode())
    rows, cols = shape
    cost = [[((seed >> ((r * cols + c) % 24)) % 97) / 10 + r * 0.01 for c in range(cols)] for r in range(rows)]
    pairs = assign(cost)
    total, _ = brute(cost)
    assert len(pairs) == min(rows, cols), f"seed {seed}"
    assert len({r for r, _ in pairs}) == len(pairs) and len({c for _, c in pairs}) == len(pairs), f"seed {seed}"
    assert math.isclose(sum(cost[r][c] for r, c in pairs), total), f"seed {seed}: {pairs}"


def test_assign_beats_greedy():
    # greedy takes (0, 0) at 1.0 and then pays 10 for (1, 1); the global minimum is 2 + 2
    assert sorted(assign([[1.0, 2.0], [2.0, 10.0]])) == [(0, 1), (1, 0)]


def test_assign_empty():
    assert assign([]) == [] and assign([[], []]) == []


# ----- tracker -----

@pytest.mark.parametrize("front", ["a", "b"])
def test_ids_survive_same_height_crossing_with_occlusion(front):
    """Review Focus 2: same height, same depth, one hides the other for three frames; the ids must not swap."""
    tr = BodyTracker()
    ids = None
    for i in range(21):
        t = i / 10
        xa, xb = 0.2 + 0.03 * i, 0.8 - 0.03 * i
        if i in (9, 10, 11):
            dets = [det(xa if front == "a" else xb)]
        else:
            dets = [det(xa), det(xb)]
        bodies = tr.update(dets, t)
        fresh = {b.id: b.anchor.x for b in bodies if b.seen_ago == 0.0}
        if ids is None:
            ids = {"a": min(fresh, key=lambda k: abs(fresh[k] - xa)), "b": min(fresh, key=lambda k: abs(fresh[k] - xb))}
            assert ids["a"] != ids["b"]
        elif i in (9, 10, 11):
            assert set(fresh) == {ids[front]}, f"frame {i}: {fresh} {ids}"
        else:
            assert set(fresh) == {ids["a"], ids["b"]}, f"frame {i}: {fresh} {ids}"
            assert abs(fresh[ids["a"]] - xa) < abs(fresh[ids["a"]] - xb), f"frame {i}: {fresh} {ids}"


def exact_det(cx):
    """det(cx) with every offset snapped to 1/64: with binary-fraction positions and times, predictions are exact,
    so a tie in distance is a tie, not decided by rounding."""
    kps = tuple(Keypoint(cx + round((k.x - 0.5) * 64) / 64, round(k.y * 64) / 64) for k in make_keypoints(0.5, 0.5, 0.5))
    return (body_box(kps), kps)


def test_tie_goes_to_the_track_seen_most_recently():
    """At the crossing both tracks predict the very same point; the one hidden a frame longer is less sure."""
    tr = BodyTracker()
    step = 1 / 16
    first = tr.update([exact_det(0.75), exact_det(0.25)], 0.0)       # b is created first: its track is listed first
    ids = {round(b.anchor.x, 4): b.id for b in first}
    a, b = ids[0.25], ids[0.75]
    tr.update([exact_det(0.75 - step), exact_det(0.25 + step)], step)
    tr.update([exact_det(0.75 - 2 * step), exact_det(0.25 + 2 * step)], 2 * step)
    (only,) = [x for x in tr.update([exact_det(0.25 + 3 * step)], 3 * step) if x.seen_ago == 0.0]
    assert only.id == a
    fresh = [x for x in tr.update([exact_det(0.5)], 4 * step) if x.seen_ago == 0.0]
    assert [x.id for x in fresh] == [a], (a, b)


def test_scale_difference_keeps_depths_apart():
    """A near and a far person move so that distance alone would swap them; the scale term keeps their ids."""
    tr = BodyTracker()
    near, far = det(0.4, h=0.8), det(0.6, 0.38, h=0.4)       # shoulders level
    first = tr.update([near, far], 0.0)
    by_scale = sorted(first, key=lambda x: -x.scale)
    assert by_scale[0].scale - by_scale[1].scale > 0.1
    ids = (by_scale[0].id, by_scale[1].id)
    then = {x.id: x for x in tr.update([det(0.54, h=0.8), det(0.5, 0.38, h=0.4)], 0.1)}
    assert then[ids[0]].height > 0.6 and then[ids[1]].height < 0.6       # the box is this capture's detection


def test_coast_300ms_then_drop_at_0_5s():
    tr = BodyTracker()
    (first,) = tr.update([det(0.4)], 0.0)
    tr.update([det(0.4)], 0.1)
    coasting = tr.update([], 0.35)
    assert [b.id for b in coasting] == [first.id]
    assert math.isclose(coasting[0].seen_ago, 0.25)
    assert tr.update([], 0.1 + COAST_SECONDS - 0.01)[0].seen_ago > 0.0
    assert tr.update([], 0.1 + COAST_SECONDS + 0.05) == ()      # past 300 ms: kept, not emitted
    back = tr.update([det(0.4)], 0.1 + DROP_SECONDS - 0.05)     # still inside 0.5 s: the same id
    assert [b.id for b in back] == [first.id] and back[0].seen_ago == 0.0
    tr.update([], 0.1 + DROP_SECONDS)
    later = tr.update([det(0.4)], 0.1 + DROP_SECONDS + DROP_SECONDS + 0.05)
    assert [b.id for b in later] != [first.id]


def test_ids_never_reused():
    tr = BodyTracker()
    seen = set()
    t = 0.0
    for _ in range(5):
        (b,) = tr.update([det(0.5)], t)
        assert b.id not in seen
        seen.add(b.id)
        t += DROP_SECONDS + 0.1                                 # gone long enough to be dropped
    assert len(seen) == 5


def test_velocity_from_irregular_timestamps():
    tr = BodyTracker()
    for t in (0.0, 0.07, 0.19, 0.25, 0.41, 0.44):
        (b,) = tr.update([det(0.2 + 0.3 * t, 0.5 - 0.1 * t)], t)
    assert math.isclose(b.vx, 0.3, abs_tol=1e-6) and math.isclose(b.vy, -0.1, abs_tol=1e-6)


def test_one_euro_smooths_keypoints():
    """A person standing still with a jittery detector: the smoothed keypoints move far less than the raw."""
    tr = BodyTracker()
    raw_err, out_err = [], []
    seed = zlib.crc32(b"one-euro")
    for i in range(60):
        jitter = 0.01 * (1 if (seed >> (i % 31)) & 1 else -1)
        kps = tuple(Keypoint(k.x + jitter, k.y - jitter, k.conf) for k in make_keypoints(0.5, 0.5, 0.5))
        (b,) = tr.update([(body_box(kps), kps)], i / 10)
        if i >= 10:
            true = make_keypoints(0.5, 0.5, 0.5)
            raw_err.append(abs(jitter))
            out_err.append(max(abs(o.x - k.x) for o, k in zip(b.keypoints, true)))
    assert sum(out_err) < 0.5 * sum(raw_err), f"seed {seed}: {sum(out_err):.4f} vs {sum(raw_err):.4f}"


def test_one_euro_follows_a_fast_move():
    """The filter must not lag a real move: a walk at 1 frame width per second is within 0.05 after 0.5 s."""
    tr = BodyTracker()
    for i in range(11):
        (b,) = tr.update([det(0.2 + 0.1 * i / 2)], i / 20)
    assert abs(b.anchor.x - 0.7) < 0.05, b.anchor


def test_tracker_scale_and_placement():
    cal = Calibration(zone=(0.0, 0.0, 1.0, 1.0), min_height=0.3)
    tr = BodyTracker(calibration=cal)
    (b,) = tr.update([det(0.25, h=0.6)], 0.0)
    assert isinstance(b, Body) and b.in_zone
    assert math.isclose(b.zone_x, b.anchor.x) and b.scale > 0.0
    small = BodyTracker(calibration=Calibration(zone=(0.0, 0.0, 1.0, 1.0), min_height=0.9))
    assert small.update([det(0.25, h=0.6)], 0.0)[0].in_zone is False


def test_tracker_scale_follows_a_step_within_three_captures():
    """Depth reads Body.scale and smooths it itself (its Glide): the tracker's own smoothing must be quick, or two
    smoothers in a row lag a step (C44). At SCALE_TAU 0.3 s the third capture after a step had 63 percent of it."""
    tr = BodyTracker()
    before, after = Body(0, *det(0.5, h=0.5)).scale, Body(0, *det(0.5, h=0.65)).scale
    assert after == pytest.approx(1.3 * before)
    for i in range(10):
        tr.update([det(0.5, h=0.5)], i / 10)
    got = [tr.update([det(0.5, h=0.65)], 1.0 + i / 10)[0].scale for i in range(3)]
    share = [(g - before) / (after - before) for g in got]
    assert share == sorted(share) and share[2] >= 0.9, share


def test_tracker_orders_largest_scale_first():
    tr = BodyTracker()
    bodies = tr.update([det(0.2, h=0.3), det(0.7, h=0.6)], 0.0)
    assert bodies[0].scale > bodies[1].scale and bodies[0].anchor.x > 0.5


def test_detection_without_confident_points_is_ignored():
    tr = BodyTracker()
    assert tr.update([det(0.5, conf=0.0)], 0.0) == ()


# ----- ThreadedCamera -----

class Scripted(ThreadedCamera):
    """step() gives the scripted results in turn, then None forever; counts its calls."""

    def __init__(self, results, clock):
        super().__init__(clock=clock)
        self.results = list(results)
        self.calls = 0
        self.done = threading.Event()

    def step(self):
        self.calls += 1
        if self.results:
            r = self.results.pop(0)
            if isinstance(r, Exception):
                raise r
            return r
        self.done.set()
        self._stop.wait(0.005)
        return None


def test_stale_result_is_none_and_unavailable():
    clock = FakeClock(10.0)
    cam = Scripted([], clock)
    assert STALE_SECONDS == 1.0 and cam.available is False and cam.latest() is None   # nothing yet
    cam.publish((10.0, (), (), None))
    assert cam.available is True and cam.latest() == (10.0, (), (), None)
    clock.t = 10.0 + STALE_SECONDS + 0.01
    assert cam.latest() is None and cam.available is False
    cam.publish((clock.t, (), (), None))                             # a fresh result makes it available again
    assert cam.available is True and cam.latest()[0] == clock.t


def test_step_none_holds_last():
    clock = FakeClock(5.0)
    result = (5.0, (), (), None)
    cam = Scripted([result], clock)
    cam.start()
    try:
        assert cam.done.wait(2.0)
        while cam.calls < 5:
            cam.done.clear()
            assert cam.done.wait(2.0)
        assert cam.latest() == result and cam.available is True
    finally:
        cam.close()


def test_thread_death_makes_the_camera_unavailable():
    clock = FakeClock(5.0)
    cam = Scripted([(5.0, (), (), None), RuntimeError("usb unplugged")], clock)
    cam.start()
    cam._thread.join(2.0)
    assert not cam._thread.is_alive()
    assert cam.available is False and cam.latest() is None
    cam.close()


class Releasing(ThreadedCamera):
    def __init__(self):
        super().__init__(clock=FakeClock())
        self.alive_at_release = None
        self.started = threading.Event()

    def step(self):
        self.started.set()
        self._stop.wait(0.01)
        return None

    def release(self):
        self.alive_at_release = self._thread.is_alive()


def test_close_joins_before_release():
    cam = Releasing()
    cam.start()
    assert cam.started.wait(2.0)
    cam.close()
    assert cam.alive_at_release is False
    cam.close()                                                       # twice is harmless
