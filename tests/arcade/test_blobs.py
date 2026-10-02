"""Blobs and motion from camera frames (core Task 15 as amended, spec 5 and 6.1, C11, C17): synthetic frames only."""
import time
import zlib

import cv2
import numpy as np
import pytest

import arcade.sources.blobs as blobs_module
from arcade.calibration import Calibration
from arcade.sensed import Blob
from arcade.sources.blobs import (HALO_PX, MATCH_DIST, MAX_AREA, WORK_SIZE, BlobTracker, FrameFeatures, find_blobs,
                                  motion_grid)

W, H = 160, 120              # the low-resolution stream (spec 6.1)
RED = (0, 0, 200)            # BGR: a saturated red glow, its value under LIGHT_V so only the core is the component
WHITE = (255, 255, 255)


def dark_frame(w=W, h=H, level=30):
    return np.full((h, w, 3), level, np.uint8)


def light(frame, center, core=2, halo=RED, core_color=WHITE):
    """A light as a camera sees one at night: an overexposed core inside a glow of its own colour, wider than the
    core by more than the 3 px halo."""
    cv2.circle(frame, center, core + HALO_PX + 1, halo, -1)
    cv2.circle(frame, center, core, core_color, -1)
    return frame


def light_640(frame, center, core=2, halo=RED):
    """light() as the Mac's 640x480 capture sees it: center and core in 160x120 pixels, drawn four times larger
    around the 640x480 pixel that covers the same place (4 x + 1.5, rounded up)."""
    x, y = center
    big = (4 * x + 2, 4 * y + 2)
    cv2.circle(frame, big, 4 * (core + HALO_PX + 1), halo, -1)
    cv2.circle(frame, big, 4 * core, WHITE, -1)
    return frame


# ----- the light-source test (the amendment) -----

def test_small_saturated_red_is_a_red_blob():
    f = light(dark_frame(), (120, 30), core=2, core_color=(200, 200, 255))   # a pastel, overexposed core
    blobs = find_blobs(f)
    assert len(blobs) == 1
    b = blobs[0]
    assert b.x == pytest.approx(120.5 / W, abs=0.01) and b.y == pytest.approx(30.5 / H, abs=0.01)
    assert b.color == (255, 0, 0)            # the halo's hue at full saturation, not the core's pastel
    assert 0.01 < b.size < 0.05 and b.id == -1


def test_large_lamp_rejected():
    assert 113 > MAX_AREA * W * H            # a core of radius 6 is 113 px, over 0.5 percent of the frame
    assert find_blobs(light(dark_frame(), (80, 60), core=6)) == ()
    assert len(find_blobs(light(dark_frame(), (80, 60), core=5))) == 1   # 81 px: the same lamp, smaller, is a light


def test_white_core_without_saturated_halo_rejected():
    f = dark_frame()
    light(f, (40, 60), halo=(180, 180, 180))     # a white lamp: its glow is white too
    light(f, (120, 60))
    blobs = find_blobs(f)
    assert len(blobs) == 1 and blobs[0].x == pytest.approx(120.5 / W, abs=0.01)


def test_no_blobs_in_a_dim_frame():
    assert find_blobs(dark_frame(level=120)) == ()


def test_blobs_sorted_by_size_and_capped():
    f = dark_frame()
    for i in range(10):
        light(f, (10 + i * 14, 40), core=1 + i % 3)
    light(f, (100, 90), core=5)
    blobs = find_blobs(f, max_blobs=5)
    assert len(blobs) == 5 and blobs[0].x == pytest.approx(100.5 / W, abs=0.01)
    assert all(blobs[i].size >= blobs[i + 1].size for i in range(4))


def test_a_non_finite_centroid_is_dropped(monkeypatch):
    f = light(dark_frame(), (80, 60))
    assert len(find_blobs(f)) == 1
    real = cv2.connectedComponentsWithStats

    def nan_centroids(*args, **kwargs):
        n, labels, stats, centroids = real(*args, **kwargs)
        return n, labels, stats, np.full_like(centroids, np.nan)

    monkeypatch.setattr(cv2, "connectedComponentsWithStats", nan_centroids)
    assert find_blobs(f) == ()               # not a light at (0, 0), which Blob would make of NaN
    blobs, _ = FrameFeatures().update(f, 0.0)
    assert blobs == ()


# ----- ids and velocities (C11, C17) -----

def test_blob_ids_persist_and_velocities_follow():
    # 200 px wide, so 0.02 fw is 4 whole pixels. The disc moves left in the camera, so right on the mirrored wall.
    ff = FrameFeatures(work=(200, 150))
    dt = 0.1
    seen = []
    for k in range(5):
        blobs, _ = ff.update(light(dark_frame(200, 150), (150 - 4 * k, 75)), k * dt)
        assert len(blobs) == 1
        seen.append(blobs[0])
    assert [b.id for b in seen] == [1] * 5
    assert (seen[0].vx, seen[0].vy) == (0.0, 0.0)
    for prev, b in zip(seen, seen[1:]):
        assert b.x - prev.x == pytest.approx(0.02, abs=1e-9)
        assert b.vx == pytest.approx(0.02 / dt, rel=1e-6) and b.vy == pytest.approx(0.0, abs=1e-9)


def test_a_blob_lost_and_found_far_away_gets_a_new_id():
    tr = BlobTracker()
    red = (255, 0, 0)
    (a,) = tr.update((Blob(0.3, 0.5, 0.02, red),), 0.0)
    (b,) = tr.update((Blob(0.32, 0.5, 0.02, red),), 0.1)
    assert a.id == b.id == 1
    assert tr.update((), 0.2) == ()
    (c,) = tr.update((Blob(0.7, 0.5, 0.02, red),), 0.3)
    assert c.id == 2 and (c.vx, c.vy) == (0.0, 0.0)
    (d,) = tr.update((Blob(0.7 + 1.5 * MATCH_DIST, 0.5, 0.02, red),), 0.4)   # a jump past MATCH_DIST in one capture
    assert d.id == 3


# ----- the static mask and the zone -----

def test_static_blob_masked_after_5s_unmasked_on_move():
    ff = FrameFeatures()

    def shown(x, t):
        return ff.update(light(dark_frame(), (x, 60)), t)[0]

    first = shown(80, 0.0)
    assert len(first) == 1
    for i in range(1, 50):                   # still, at 10 fps, to 4.9 s
        assert len(shown(80, i / 10)) == 1
    assert shown(80, 5.0) == () and shown(80, 5.5) == ()
    moved = shown(88, 5.6)                   # 8 px is 0.05 fw: past STATIC_MOVE, within MATCH_DIST
    assert len(moved) == 1 and moved[0].id == first[0].id
    assert len(shown(88, 10.5)) == 1 and shown(88, 10.6) == ()


def test_static_lamps_do_not_crowd_out_a_moving_light():
    # Nine still lamps, each larger than the moving light: the cap of 8 comes after the mask, not before it.
    ff = FrameFeatures()
    for i in range(51):
        f = dark_frame()
        for k in range(9):
            light(f, (10 + 16 * k, 15), core=3)
        light(f, (20 + 2 * i, 90), core=1)   # 2 px a capture: 0.0125 fw, past STATIC_MOVE
        blobs, _ = ff.update(f, i / 10)
        if i < 50:
            assert len(blobs) == 8 and all(b.y < 0.5 for b in blobs)
    assert len(blobs) == 1 and blobs[0].y > 0.5


def test_out_of_zone_blob_flagged():
    cal = Calibration(zone=(0.5, 0.2, 0.9, 0.8))
    f = dark_frame()
    light(f, (48, 60))                       # camera x 0.3: mirrored 0.7, inside the zone
    light(f, (112, 60))                      # camera x 0.7: mirrored 0.3, outside it
    blobs, _ = FrameFeatures(calibration=cal).update(f, 0.0)
    by_x = sorted(blobs, key=lambda b: b.x)
    assert [round(b.x, 1) for b in by_x] == [0.3, 0.7]
    assert [b.in_zone for b in by_x] == [False, True]


# ----- the motion grid (spec 5) -----

def test_uniform_brightness_step_gives_no_motion():
    rng = np.random.default_rng(7)
    a = rng.integers(40, 200, (H, W), dtype=np.uint8)
    b = np.rint(a * 1.25).astype(np.uint8)  # auto-exposure steps up a quarter
    g = motion_grid(a, b, Calibration().zone, (16, 8))
    assert g.shape == (8, 16) and not g.any()


def test_shake_returns_empty_and_counts():
    yy, xx = np.mgrid[0:H, 0:W]
    scene = np.where((yy // 8 + xx // 8) % 2, 200, 40).astype(np.uint8)
    shaken = np.roll(scene, 4, axis=1)       # the pole moves half a square
    assert motion_grid(scene, shaken, Calibration().zone, (16, 8)).shape == (0, 0)
    ff = FrameFeatures((16, 8))
    ff.update(cv2.cvtColor(scene, cv2.COLOR_GRAY2BGR), 0.0)
    _, motion = ff.update(cv2.cvtColor(shaken, cv2.COLOR_GRAY2BGR), 0.1)
    assert motion.shape == (0, 0) and ff.shakes == 1


def test_motion_zone_crop_maps_to_wall_cell():
    # The zone is x 40..120 px; at the wall's 2:1 the crop is 80 by 40 px, centred on the zone's middle row 60, so
    # rows 40..80. Mirrored, camera columns 40..50 are 110..120: the crop's last 10 columns, and rows 40..50 its
    # first 10 rows.
    zone = (0.25, 0.25, 0.75, 0.75)
    a = np.full((H, W), 100, np.uint8)
    b = a.copy()
    b[40:50, 40:50] = 150
    g = motion_grid(a, b, zone, (8, 4))      # cells of 10 by 10 px
    assert g.shape == (4, 8) and np.argwhere(g).tolist() == [[0, 7]]
    wall = motion_grid(a, b, zone, (128, 64))   # the wall's grid: 1.6 cells a pixel, the square on cells 112..128
    rows, cols = np.nonzero(wall)
    assert wall.shape == (64, 128) and rows.size
    assert cols.min() >= 111 and rows.max() <= 16
    assert np.mean(cols) == pytest.approx(120, abs=1.5) and np.mean(rows) == pytest.approx(8, abs=1.5)


def test_frame_features_first_frame_has_no_motion():
    ff = FrameFeatures((16, 12))
    f = light(dark_frame(), (120, 30))
    blobs, motion = ff.update(f, 0.0)
    assert len(blobs) == 1 and motion.shape == (12, 16) and not motion.any()
    g = f.copy()
    g[60:120, 90:120] = 120                  # someone steps in right of the camera's centre: the wall's left
    blobs, motion = ff.update(g, 0.1)        # (mirrored columns 40..70, 42 with the blur's 2 px: cells 1 to 6)
    assert len(blobs) == 1 and motion.any() and not motion[:, 8:].any() and ff.shakes == 0


# ----- the camera sources' wiring (iteration 21, M5) -----

def test_a_640x480_frame_is_shrunk_first(monkeypatch):
    assert WORK_SIZE == (160, 120)
    (small,), _ = FrameFeatures().update(light(dark_frame(), (120, 30)), 0.0)
    real, seen = blobs_module.find_blobs, []

    def spy(frame, *args, **kwargs):
        seen.append(frame.shape)
        return real(frame, *args, **kwargs)

    monkeypatch.setattr(blobs_module, "find_blobs", spy)
    blobs, motion = FrameFeatures().update(light_640(dark_frame(640, 480), (120, 30)), 0.0)
    assert seen == [(120, 160, 3)]           # find_blobs costs 10 ms at 640x480, 0.4 ms at 160x120 (Q130)
    assert len(blobs) == 1
    assert blobs[0].x == pytest.approx(small.x, abs=1 / 160) and blobs[0].y == pytest.approx(small.y, abs=1 / 160)
    assert motion.shape == (120, 160) and not motion.any()


def test_mirror_off_keeps_camera_x_for_blobs_and_motion():
    f = light(dark_frame(), (120, 30))       # camera x 0.75
    g = f.copy()
    g[60:120, 90:120] = 120                  # someone steps in right of the camera's centre (camera columns 90..120)
    on, off = FrameFeatures((16, 12)), FrameFeatures((16, 12), mirror=False)
    (b_on,), _ = on.update(f, 0.0)
    (b_off,), _ = off.update(f, 0.0)
    assert b_on.x == pytest.approx(1 - 120.5 / W, abs=0.01)
    assert b_off.x == pytest.approx(120.5 / W, abs=0.01) and b_off.y == b_on.y
    _, m_on = on.update(g, 0.1)
    _, m_off = off.update(g, 0.1)
    assert m_on.any() and not m_on[:, 8:].any()      # mirrored: the wall's left
    assert m_off.any() and not m_off[:, :8].any()    # not mirrored: the camera's right stays right
    a = np.full((H, W), 100, np.uint8)
    c = a.copy()
    c[40:50, 40:50] = 150                    # as test_motion_zone_crop_maps_to_wall_cell: unflipped, the first cell
    zone = (0.25, 0.25, 0.75, 0.75)
    assert np.argwhere(motion_grid(a, c, zone, (8, 4), mirror=False)).tolist() == [[0, 0]]
    assert np.argwhere(motion_grid(a, c, zone, (8, 4))).tolist() == [[0, 7]]


def test_a_blob_in_the_static_mask_is_dropped():
    f = dark_frame()
    light(f, (120, 30))                      # a lamp the calibration saw: mirrored x 0.25, y 0.25
    light(f, (40, 90))                       # a light someone carries: mirrored x 0.75, y 0.75
    lamp, carried = sorted(FrameFeatures().update(f, 0.0)[0], key=lambda b: b.x)
    # The radius is in frame widths (_fw): 0.048 frame heights below the lamp is 0.036 fw, within a 0.04 radius;
    # 0.06 heights is 0.045 fw, outside it.
    for dy in (0.0, 0.048):
        cal = Calibration(static_mask=((lamp.x, lamp.y + dy, 0.04),))
        (blob,) = FrameFeatures(calibration=cal).update(f, 0.0)[0]
        assert blob.x == carried.x and blob.id == 1, dy   # dropped before the tracker: the lamp took no id
    cal = Calibration(static_mask=((lamp.x, lamp.y + 0.06, 0.04),))
    assert sorted(b.x for b in FrameFeatures(calibration=cal).update(f, 0.0)[0]) == [lamp.x, carried.x]


def test_hide_still_off_keeps_a_still_lamp():
    # StaticMask hides a still lamp after 5 s; calibrate's clear step (10 s) must see it to record it, so it turns
    # hide_still off on the running camera's features.
    keyword, attribute, default = FrameFeatures(hide_still=False), FrameFeatures(), FrameFeatures()
    assert default.hide_still is True
    attribute.hide_still = False
    f = light(dark_frame(), (80, 60))
    for i in range(121):                     # still for 12 s at 10 fps
        t = i / 10
        assert len(keyword.update(f, t)[0]) == 1 and len(attribute.update(f, t)[0]) == 1, t
        assert len(default.update(f, t)[0]) == (1 if i < 50 else 0), t


# ----- cost -----

@pytest.mark.perf
def test_features_under_3ms_at_160x120():
    # spec 6.1's low-resolution stream: a textured scene, a body moving and six lights. Timed on the thread's CPU
    # clock (time.thread_time), the code's own cost.
    rng = np.random.default_rng(11)
    base = cv2.blur(rng.integers(20, 180, (H, W, 3), dtype=np.uint8), (5, 5))
    frames = []
    for i in range(10):
        f = base.copy()
        f[30:110, 20 + 6 * i:60 + 6 * i] = 150
        for k in range(6):
            light(f, (12 + 26 * k, 14 + i), core=1 + k % 3, halo=((0, 0, 200), (0, 180, 0), (200, 60, 0))[k % 3])
        frames.append(f)
    order = list(range(10)) + list(range(8, 0, -1))   # back and forth, 6 px a capture: never a shake
    ff = FrameFeatures()
    ff.update(frames[0], 0.0)
    spent = []
    for n in range(1, 61):
        start = time.thread_time()
        blobs, motion = ff.update(frames[order[n % len(order)]], n / 10)
        spent.append(time.thread_time() - start)
    assert len(blobs) == 6 and motion.shape == (120, 160) and motion.any() and ff.shakes == 0
    mean = sum(spent) / len(spent)
    print(f"FrameFeatures.update at 160x120: mean {mean * 1e3:.3f} ms, max {max(spent) * 1e3:.3f} ms")
    assert mean < 0.003


@pytest.mark.perf
def test_features_under_3ms_at_640x480_input():
    # The Mac's capture (pose_mediapipe.CAPTURE_SIZE): the same scene drawn at 640x480, shrunk to WORK_SIZE first.
    # Cores of 2 to 4 px at 160x120: a 1 px core (4 px at 640) is under MIN_AREA once shrunk (S1's Q1).
    rng = np.random.default_rng(zlib.crc32(b"features at 640x480"))
    base = cv2.blur(rng.integers(20, 180, (480, 640, 3), dtype=np.uint8), (5, 5))
    frames = []
    for i in range(10):
        f = base.copy()
        f[120:440, 80 + 24 * i:240 + 24 * i] = 150
        for k in range(6):
            light_640(f, (12 + 26 * k, 14 + i), core=2 + k % 3, halo=((0, 0, 200), (0, 180, 0), (200, 60, 0))[k % 3])
        frames.append(f)
    order = list(range(10)) + list(range(8, 0, -1))   # back and forth, 6 px a capture at 160x120: never a shake
    ff = FrameFeatures()
    ff.update(frames[0], 0.0)
    spent = []
    for n in range(1, 51):
        start = time.thread_time()
        blobs, motion = ff.update(frames[order[n % len(order)]], n / 10)
        spent.append(time.thread_time() - start)
    assert len(blobs) == 6 and motion.shape == (120, 160) and motion.any() and ff.shakes == 0
    mean = sum(spent) / len(spent)
    print(f"FrameFeatures.update at 640x480 input: mean {mean * 1e3:.3f} ms, max {max(spent) * 1e3:.3f} ms")
    assert mean < 0.003
