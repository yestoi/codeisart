import dataclasses
import math
import zlib

import numpy as np
import pytest

from arcade.input import (CAPTURE_GRACE, DEPTH_SPAN, GLIDE_BETA, GLIDE_MIN_CUTOFF, PIN, RECENTRE_RATE,
                          RECENTRE_SECONDS, RECENTRE_TO, Cursor, Depth, Edge, Glide, Hold, OneEuro, capture_grace)
from arcade.sensed import LEFT_HIP, LEFT_WRIST, MIN_CONF, RIGHT_HIP, RIGHT_WRIST, Body, Keypoint
from arcade.sources.actors import REAL_NOISE, TICK, Person, degrade, scene

IDS = range(40)          # body ids key degrade's noise (zlib.crc32 of tick, id, joint): 40 different captures


def ticks(values, start=0.0):
    """(value, t) pairs at 30 Hz."""
    return [(v, start + i * TICK) for i, v in enumerate(values)]


def summed(values):
    """(value, t) pairs at 30 Hz with t summed tick by tick, as the runner adds dt: 3 ticks from tick 13 to
    tick 16 come to 0.10000000000000003 s."""
    t, out = 0.0, []
    for v in values:
        out.append((v, t))
        t += TICK
    return out


def test_edge_fires_once():
    e = Edge(grace=0.25)
    fired = [e.update(v, t) for v, t in ticks([False] * 3 + [True] * 10 + [False] * 2 + [True] * 5)]
    assert fired.count(True) == 1 and fired[3]                       # a 67 ms blink is the same press
    e = Edge(grace=0.25)
    fired = [e.update(v, t) for v, t in ticks([True] * 3 + [False] * 7 + [True] * 3 + [False] * 9 + [True])]
    assert [i for i, f in enumerate(fired) if f] == [0, 22]          # 233 ms is a blink, 300 ms a new press
    assert Edge().grace == 0.25 and not Edge().on
    assert Edge(np.float64(0.1)).grace == 0.1 and Hold(np.int64(3), np.float32(0.5)).seconds == 3.0
    assert type(Hold(np.int64(3)).seconds) is float and type(Edge(np.float32(0.5)).grace) is float
    e = Edge(grace=0.1)
    assert [e.update(v, t) for v, t in ((True, 0.0), (False, 0.1), (True, 0.2))] == [True, False, False]
    assert e.on                                                       # false for exactly grace is not more than it
    e = Edge(grace=0.1)
    fired = [e.update(v, t) for v, t in summed([True] * 14 + [False] * 3 + [True])]
    assert [i for i, f in enumerate(fired) if f] == [0]               # false for the grace, summed: not re-armed


def test_hold_tolerates_200ms_dropout_resets_after_300ms():
    h = Hold(1.0, grace=0.25)
    run = ticks([True] * 15 + [False] * 6 + [True] * 20)             # 0.5 s, a 200 ms dropout, then on
    fired = [h.update(v, t) for v, t in run]
    assert [i for i, f in enumerate(fired) if f] == [30]              # 1.0 s after the hold began, not later
    assert h.progress == 1.0 and h.fired
    h = Hold(1.0, grace=0.25)
    run = ticks([True] * 15 + [False] * 9 + [True] * 31)             # a 300 ms dropout ends the hold
    fired, progress = [], []
    for v, t in run:
        fired.append(h.update(v, t))
        progress.append(h.progress)
    assert progress[14] == pytest.approx(14 / 30) and progress[23] == 0.0 and h.start == pytest.approx(24 * TICK)
    assert [i for i, f in enumerate(fired) if f] == [54]              # a whole second after the new hold
    assert Hold(2.0).grace == 0.25
    h, t, fired = Hold(3.0), 0.0, []
    for _ in range(100):
        fired.append(h.update(True, t))
        t += TICK                                                     # the runner adds dt: 90 ticks sum to 2.999...
    assert [i for i, f in enumerate(fired) if f] == [90]
    h = Hold(1.0, grace=0.1)
    fired = [h.update(v, t) for v, t in summed([True] * 14 + [False] * 3 + [True] * 20)]
    assert [i for i, f in enumerate(fired) if f] == [30]              # a dropout of the grace, summed, holds
    h = Hold(1.0)
    h.update(True, 5.0)
    h.update(True, 4.0)
    assert h.progress == 0.0                                          # progress never leaves 0..1


def test_hold_fires_once_per_hold_and_at_zero_seconds():
    h = Hold(0.5, grace=0.0)
    fired = [h.update(v, t) for v, t in ticks([True] * 30 + [False] + [True] * 16)]
    assert [i for i, f in enumerate(fired) if f] == [15, 46]          # held on: once; released: again
    z = Hold(0.0)
    assert z.progress == 0.0 and z.update(True, 5.0) and z.progress == 1.0 and not z.update(True, 5.1)
    assert not z.update(False, 5.2) and z.progress == 1.0            # within the grace the hold stands
    h.reset()
    assert h.start is None and h.progress == 0.0 and not h.fired


def test_capture_grace_is_sized_in_captures():
    assert CAPTURE_GRACE == 5
    assert capture_grace(10) == pytest.approx(0.55) and capture_grace(30) == pytest.approx(5.5 / 30)
    assert capture_grace(10, captures=2) == pytest.approx(0.25)       # the amendment's 0.25 s is two captures
    assert capture_grace(10, captures=0) == pytest.approx(0.05)       # no missed capture: half a capture
    assert capture_grace(np.int64(10)) == pytest.approx(0.55)          # a numpy number is a number
    for bad in (0, -1, math.nan, math.inf, None, True, np.True_):
        with pytest.raises(ValueError):
            capture_grace(bad)
    for bad in (-1, 2.0, True):
        with pytest.raises(ValueError):
            capture_grace(10, captures=bad)
    for make in (lambda v: Edge(v), lambda v: Hold(1.0, v), lambda v: Hold(v), lambda v: Cursor(v)):
        for bad in (-0.1, math.nan, math.inf, None, True, np.True_, "1"):
            with pytest.raises(ValueError):
                make(bad)


def test_exit_hold_survives_spec_noise_with_the_capture_grace():
    # C10: both hands up is seen on about 72 percent of captures at the spec 6.4 noise, and runs of 3 or more
    # misses (0.3 s) end a hold with the amendment's 0.25 s grace. Sized in captures, the 3 s exit holds.
    short = 0
    for body_id in IDS:
        person = Person(0.5, id=body_id).both_hands_up(0.0, 5.0)
        frames = list(degrade(scene(persons=[person], ticks=210), **REAL_NOISE))
        hold, amended = Hold(3.0, grace=capture_grace(10)), Hold(3.0, grace=0.25)
        fired, progress = [], {}
        for s in frames:
            up = bool(s.bodies) and s.bodies[0].both_hands_up
            if hold.update(up, s.t):
                fired.append(s.t)
            short += amended.update(up, s.t) and s.t < 5.0
            progress[round(s.t, 3)] = hold.progress
        assert len(fired) == 1 and 3.15 <= fired[0] < 4.4, (body_id, fired)   # 2 ids in 400 fire after 3.8
        assert progress[5.8] == 0.0, body_id                          # hands down at 5 s: reset within 0.8 s
    assert short < 0.8 * len(IDS), short                              # the 0.25 s grace loses over a fifth


def test_edge_fires_once_per_raise_under_spec_noise():
    # A raised wrist drops out of 15 percent of captures: without a grace, a blink mid-raise is a new press.
    bare = 0
    for body_id in IDS:
        person = Person(0.5, id=body_id).raise_hand(0.5, 1.0).raise_hand(2.5, 1.0)
        edge, raw, count, raw_count = Edge(grace=capture_grace(10)), Edge(grace=0.0), 0, 0
        for s in degrade(scene(persons=[person], ticks=120), **REAL_NOISE):
            up = bool(s.bodies) and s.bodies[0].raised_wrist is not None
            count += edge.update(up, s.t)
            raw_count += raw.update(up, s.t)
        assert count == 2, (body_id, count)
        bare += raw_count > 2
    assert bare > len(IDS) // 2, bare


def test_cursor_keeps_its_hand_through_dropouts():
    # C10: Body.cursor jumps to the hanging wrist whenever the raised one drops out of a capture.
    raw_jumps = 0
    for body_id in IDS:
        person = Person(0.5, id=body_id).raise_hand(0.5, 3.0, "right")
        cursor, last, last_raw = Cursor(grace=capture_grace(10)), None, None
        for s in degrade(scene(persons=[person], ticks=110), **REAL_NOISE):
            body = s.bodies[0] if s.bodies else None
            point = cursor.update(body, s.t)
            if 1.0 <= s.t <= 3.5:
                raw = body.cursor
                assert point is not None and cursor.hand == "right", (body_id, s.t)
                assert last is None or abs(point[0] - last[0]) < 0.1, (body_id, s.t, point, last)
                raw_jumps += last_raw is not None and raw is not None and abs(raw[0] - last_raw[0]) > 0.2
                last, last_raw = point, raw
    assert raw_jumps > len(IDS), raw_jumps                            # the stateless cursor jumps, often


def test_cursor_holds_for_grace_then_lets_go_and_switches_with_hysteresis():
    body = Person(0.5).raise_hand(0.0, 5.0, "right").body_at(1.0, 1)
    c = Cursor(grace=0.25)
    point = c.update(body, 1.0)
    assert c.hand == "right" and point == body.cursor
    assert c.update(None, 1.2) == point and c.update(None, 1.25) == point   # held through the grace
    assert c.update(None, 1.3) is None and c.hand is None
    both = Person(0.5).both_hands_up(0.0, 5.0).body_at(1.0, 1)
    c = Cursor()
    c.update(both, 0.0)
    first = c.hand
    kps = list(both.keypoints)
    other = RIGHT_WRIST if first == "left" else LEFT_WRIST
    kps[other] = Keypoint(kps[other].x, kps[other].y - 0.02)          # a little further: not enough to switch
    c.update(Body(1, both.box, tuple(kps)), 0.1)
    assert c.hand == first
    kps[other] = Keypoint(kps[other].x, 0.0)                          # much further: switch
    c.update(Body(1, both.box, tuple(kps)), 0.2)
    assert c.hand != first and c.hand is not None
    for bad in (0.9, math.inf, None, "2"):
        with pytest.raises(ValueError):
            Cursor(switch=bad)
    assert (Cursor().grace, Cursor().switch) == (0.25, 1.25)
    assert Cursor(switch=np.float32(1.25)).switch == 1.25 and type(Cursor(switch=np.float32(1.25)).switch) is float
    kps = list(both.keypoints)
    kps[LEFT_WRIST], kps[RIGHT_WRIST] = Keypoint(0.25, 0.25), Keypoint(0.75, 0.25)
    kps[LEFT_HIP] = kps[RIGHT_HIP] = Keypoint(0.5, 0.75)
    level = Body(1, both.box, tuple(kps))                             # both wrists exactly as far out
    c = Cursor(switch=1.0)
    c.update(level, 0.0)
    first = c.hand
    c.update(level, 0.1)
    assert c.hand == first                                            # switch 1.0: only a longer reach switches
    c = Cursor(grace=0.1)
    seen = [c.update(body if v else None, t) for v, t in summed([True] * 14 + [False] * 3)]
    assert seen[16] == seen[13] == body.cursor                        # gone for the grace, summed: still held


def test_cursor_measures_reach_as_body_cursor_does():
    # Cursor's first choice of hand is Body.cursor's: an unconfident wrist is not a hand, and a wrist's reach is
    # measured from its own hip only when that hip is confident, else from the hips seen, else the shoulders.
    both = Person(0.5).both_hands_up(0.0, 5.0).body_at(1.0, 1)
    one = Person(0.5).raise_hand(0.0, 5.0, "right").body_at(1.0, 1)
    kps = list(both.keypoints)
    kps[RIGHT_WRIST] = Keypoint(0.99, 0.0, 0.1)                       # far out, but not seen
    unseen = Body(1, both.box, tuple(kps))
    kps = list(one.keypoints)
    kps[LEFT_HIP] = Keypoint(0.0, 0.0, 0.1)                           # a stray, unconfident left hip
    stray = Body(1, one.box, tuple(kps))
    for body, hand in ((unseen, "left"), (stray, "right"), (one, "right")):
        c = Cursor()
        assert c.update(body, 0.0) == body.cursor and c.hand == hand, hand
    kps = list(one.keypoints)
    kps[LEFT_HIP] = Keypoint(0.0, 0.0, MIN_CONF)                      # just confident enough: the reach is from it
    edge = Body(1, one.box, tuple(kps))
    wrist = edge.keypoints[LEFT_WRIST]
    assert Cursor._reach(edge, "left") == math.hypot(wrist.x, wrist.y)


def test_one_euro_cuts_jitter_and_lags_under_200ms():
    seed = zlib.crc32(b"one-euro")
    rng = np.random.default_rng(seed)
    times = np.arange(0.0, 10.0, 0.1)                                 # captures at 10 fps
    noisy = 0.5 + rng.uniform(-0.01, 0.01, times.size)               # a still wrist with the spec's jitter
    f = OneEuro()
    out = np.array([f(x, t) for x, t in zip(noisy, times)])
    assert out[20:].std() < 0.5 * noisy[20:].std(), f"seed={seed}"
    speed = 0.3                                                       # a wrist crossing the frame in 3 s
    f = OneEuro()
    ramp = [f(speed * t, t) for t in times[:30]]
    lag = (speed * times[29] - ramp[-1]) / speed
    assert 0.1 < lag < 0.2, lag
    fast, slow = OneEuro(beta=5.0), OneEuro(beta=0.0)                 # beta is the adaptive part: speed cuts lag
    for t in times[:30]:
        a, b = fast(speed * t, t), slow(speed * t, t)
    assert a > b + 0.01


def test_one_euro_holds_repeated_captures_and_ignores_non_finite():
    f = OneEuro()
    assert f(0.2, 1.0) == 0.2 and f.value == 0.2                      # the first sample passes through
    v = f(0.8, 1.1)
    assert 0.2 < v < 0.8
    assert f(0.9, 1.1) == v and f(0.9, 1.05) == v                     # the same capture again, or an older one
    assert f(math.nan, 1.2) == v and f(0.5, math.inf) == v and f.value == v
    f.reset()
    assert f.value is None and f(0.4, 0.0) == 0.4
    assert math.isnan(OneEuro()(math.nan, 0.0))
    for kwargs in (dict(min_cutoff=0.0), dict(d_cutoff=math.inf), dict(beta=-1.0), dict(min_cutoff=math.nan),
                   dict(beta=None), dict(d_cutoff=True), dict(min_cutoff="1")):
        with pytest.raises(ValueError):
            OneEuro(**kwargs)
    f = OneEuro()
    assert (f.min_cutoff, f.beta, f.d_cutoff) == (1.0, 0.007, 1.0)      # the paper's defaults


def test_one_euro_matches_the_paper():
    # Casiez et al. 2012, as written there: alpha = 1 / (1 + tau / Te), tau = 1 / (2 pi fc); the derivative is
    # low-passed at d_cutoff before it sets the cutoff.
    def alpha(cutoff, te):
        return 1.0 / (1.0 + 1.0 / (2.0 * math.pi * cutoff * te))

    seed = zlib.crc32(b"one-euro-paper")
    rng = np.random.default_rng(seed)
    times = np.cumsum(rng.uniform(0.05, 0.15, 60))
    xs = np.sin(times * 3.0) * 0.4 + 0.5 + rng.normal(0.0, 0.01, times.size)
    f = OneEuro(min_cutoff=0.8, beta=2.0, d_cutoff=1.5)
    x_hat, dx_hat, last = xs[0], 0.0, times[0]
    assert f(xs[0], times[0]) == x_hat
    for x, t in zip(xs[1:], times[1:]):
        te = t - last
        dx_hat += alpha(1.5, te) * ((x - x_hat) / te - dx_hat)
        x_hat += alpha(0.8 + 2.0 * abs(dx_hat), te) * (x - x_hat)
        last = t
        assert f(x, t) == pytest.approx(x_hat, abs=1e-12), f"seed={seed}"


def test_one_euro_casts_its_samples():
    # C26 pins it04's ruled deviation B5: the filter stores floats. C29: a numpy sample comes out as a float, and a
    # sample that is not a real number, or too big for a float, is not a sample.
    assert type(OneEuro(np.float32(1)).min_cutoff) is float and type(OneEuro(beta=np.int64(0)).beta) is float
    f = OneEuro()
    first = f(np.float32(0.25), np.float64(1.0))
    assert type(first) is float and type(f.value) is float and first == 0.25
    v = f(np.float32(0.75), np.int64(2))
    assert type(v) is float and 0.25 < v < 0.75
    for x, t in ((None, 3.0), ("0.9", 3.0), (0.9, None), (np.True_, 3.0), (10**400, 3.0), (0.9, 10**400)):
        assert f(x, t) == v and f.value == v
    assert math.isnan(OneEuro()(None, 0.0))                          # nothing yet: NaN, as for a NaN sample
    for kwargs in (dict(min_cutoff=10**400), dict(beta=-10**400), dict(d_cutoff=np.float64(np.inf))):
        with pytest.raises(ValueError):
            OneEuro(**kwargs)
    with pytest.raises(ValueError):
        capture_grace(10**400)
    with pytest.raises(ValueError):
        Hold(10**400)


# ----- Glide and Depth (C44): a control captured at the camera's rate, given on every tick -----

def captures(seconds, fps=10, start=0.0, summed=False):
    """(t, camera_t) at 30 Hz, the camera capturing at fps: camera_t is the newest capture at or before t (no
    latency: a capture is seen on the tick it is taken). summed adds TICK tick by tick, as the runner adds dt."""
    out, t = [], start
    for i in range(round(seconds / TICK)):
        if not summed:
            t = start + i * TICK
        out.append((t, start + math.floor(i * TICK * fps + 1e-9) / fps))
        if summed:
            t += TICK
    return out


def test_glide_moves_on_every_tick_between_captures():
    # At 10 fps a captured value holds for three ticks: the paddle steps ten times a second. The Glide moves it
    # on every tick, and only towards the newest filtered capture: interpolation, never extrapolation.
    ramp = lambda c: 0.2 + 0.4 * c
    for summed in (False, True):
        g, ref = Glide(), OneEuro(GLIDE_MIN_CUTOFF, GLIDE_BETA)
        newest, last_cam, prev = None, None, None
        for t, cam in captures(1.5, summed=summed):
            if cam != last_cam:
                newest, last_cam = ref(ramp(cam), cam), cam
            v = g.update(ramp(cam), t, cam)
            assert type(v) is float and v <= newest + 1e-12, (summed, t, v, newest)
            assert cam == 0.0 or v > prev, (summed, t, v, prev)       # from the second capture: every tick
            assert g.value == v
            prev = v
    g = Glide()
    assert g.update(0.3, 0.0, 0.0) == 0.3                             # the first value passes through
    assert g.update(0.3, TICK, 0.0) == 0.3 and g.update(0.9, 2 * TICK, 0.0) == 0.3   # a held capture is not new


def test_glide_lag_is_bounded():
    # C44's accepted lag: one capture period (the glide) plus One Euro's 1 / (2 pi fc).
    for size in (0.25, 0.5, 1.0):
        g, crossed = Glide(), None
        for t, cam in captures(2.0):
            v = g.update(0.0 if cam < 1.0 else size, t, cam)
            if crossed is None and cam >= 1.0 and v >= 0.9 * size:
                crossed = t
        assert crossed is not None and crossed - 1.0 <= 0.35, (size, crossed)
    g, worst = Glide(), 0.0
    for t, cam in captures(2.0):
        v = g.update(cam, t, cam)                                     # one range a second
        worst = max(worst, t - v)
    assert worst <= 0.25, worst


def test_glide_holds_through_grace_then_lets_go():
    g = Glide(grace=0.55)
    for t, cam in captures(1.0):
        held = g.update(0.4, t, cam)
    last = t
    seen = []
    for i, bad in enumerate([None, math.nan, math.inf, None] * 6, start=1):
        t = last + i * TICK
        seen.append((t - last, g.update(bad, t, cam + i * TICK)))
    assert all(v == held for dt, v in seen if dt <= 0.55), seen      # dropped for up to the grace: held
    assert all(v is None for dt, v in seen if dt > 0.55 + 1e-6), seen
    assert g.value is None
    assert g.update(0.9, t + TICK, cam + 2.0) == 0.9                  # fresh: no glide from the old value
    assert g.update(0.9, t + 2 * TICK, cam + 2.0) == 0.9
    for bad in (-0.1, math.nan, math.inf, None, True):
        with pytest.raises(ValueError):
            Glide(grace=bad)
    assert Glide().grace == capture_grace(10)


BASE = Person(0.5, height=0.7).body_at(0.0, 1)


def at(ratio):
    """BASE with its scale times ratio: nearer the camera when ratio > 1."""
    return dataclasses.replace(BASE, scale=BASE.scale * ratio)


def depth_run(depth, ratio_at, seconds, fps=10):
    """[(t, value)] of depth fed a body whose scale ratio is ratio_at(capture time)."""
    return [(t, depth.update(at(ratio_at(cam)), t, cam)) for t, cam in captures(seconds, fps)]


def settled(ratio, seconds=1.5):
    """A fresh Depth's value after the body first seen at ratio 1 has stood at ratio for seconds (< 2: no
    recentre), and the Depth."""
    d = Depth()
    return depth_run(d, lambda c: 1.0 if c < 0.2 else ratio, 0.2 + seconds)[-1][1], d


def test_depth_starts_at_half_and_reads_the_log_ratio():
    d = Depth()
    assert d.update(at(1.0), 0.0, 0.0) == 0.5 and d.raw == 0.5
    assert d.update(None, TICK, 0.0) == 0.5                            # a dropout within the grace holds
    for ratio, want in ((1.35, 1.0), (0.741, 0.0), (1.16, 0.75)):
        v, d = settled(ratio)
        assert v == pytest.approx(want, abs=0.01), ratio
        assert d.raw == pytest.approx(0.5 + math.log(ratio) / DEPTH_SPAN), ratio
    for ratio, want in ((2.0, 1.0), (0.5, 0.0)):
        v, d = settled(ratio)
        assert v == pytest.approx(want, abs=1e-3) and 0.0 <= v <= 1.0, ratio   # unclamped would be 1.66 or -0.66
        assert (d.raw > 1.0) if want else (d.raw < 0.0), (ratio, d.raw)   # raw is unclamped
    values = [settled(r)[0] for r in (0.8, 0.9, 1.0, 1.1, 1.2)]
    assert values == sorted(values) and len(set(values)) == 5, values   # nearer is always larger


def test_depth_ratio_inverts_the_map():
    assert Depth.ratio(0.5) == 1.0
    assert Depth.ratio(1.0) == pytest.approx(1.350, abs=1e-3) and Depth.ratio(0.0) == pytest.approx(0.741, abs=1e-3)
    for v in (0.0, 0.25, 0.5, 0.9, 1.0):
        got, _ = settled(Depth.ratio(v))
        assert got == pytest.approx(v, abs=0.01), v
    assert Depth.ratio(0.75, span=1.2) == pytest.approx(math.exp(0.3))


def test_depth_recentres_after_two_seconds_pinned():
    # Pinned at an end (a player who stepped back past the range) for RECENTRE_SECONDS, the centre follows: the
    # reading rises from the end at RECENTRE_RATE until the body reads RECENTRE_TO inside it, and stays.
    assert (RECENTRE_SECONDS, RECENTRE_RATE, RECENTRE_TO, PIN) == (2.0, 0.25, 0.15, 0.02)
    run = depth_run(Depth(), lambda c: 1.0 if c < 0.5 else 0.6, 6.0)   # at 0.6 from 0.5 s
    v = lambda when: min(run, key=lambda e: abs(e[0] - when))[1]
    assert all(x < 0.01 for t, x in run if 0.9 <= t <= 2.5), run      # reads 0 for 2 s
    rise = v(2.9) - v(2.7)
    assert rise == pytest.approx(0.2 * RECENTRE_RATE, abs=0.015), rise
    assert all(x == pytest.approx(RECENTRE_TO, abs=0.01) for t, x in run if t >= 3.6), run
    back = depth_run(Depth(), lambda c: 0.6 if 0.5 <= c < 2.4 else 1.0, 4.0)   # pinned 1.9 s, then back
    assert all(x < 0.01 for t, x in back if 0.9 <= t < 2.4), back
    assert back[-1][1] == pytest.approx(0.5, abs=0.01)                # the centre did not move
    near = depth_run(Depth(), lambda c: 1.0 if c < 0.5 else 1.6, 6.0) # the other end: from 1 down to 0.85
    assert near[-1][1] == pytest.approx(1.0 - RECENTRE_TO, abs=0.01)


def test_depth_still_body_under_real_noise_stays_within_0_18():
    # A still body's scale jitters from capture to capture (the nose and hips jitter and drop out; without the
    # nose the scale is 1.5 torsos); degrade measures it from the noisy keypoints. Measured in it09 (S1, these
    # 10 bodies, 60 s each): the raw reading ranges over 0.19 to 0.21, Depth's output over 0.10 to 0.168, which
    # is 8.1 px of Pong's 48 px travel. The plan's 0.15 came from a probe that did not reproduce (the operator's
    # ruling). Pong's travel threshold sits above this bound.
    spreads = {}
    for n in range(10):
        seed = zlib.crc32(f"depth-still-{n}".encode())
        body_id = seed % 1000
        d, values = Depth(), []
        person = Person(0.5, height=0.7, id=body_id)
        for s in degrade(scene(persons=[person], ticks=round(60 / TICK)), **REAL_NOISE):
            v = d.update(s.bodies[0] if s.bodies else None, s.t, s.camera_t)
            if s.t >= 1.0:
                values.append(v)
        assert None not in values, f"seed {seed} (body id {body_id})"
        spreads[f"seed {seed} (body id {body_id})"] = round(max(values) - min(values), 3)
    assert max(spreads.values()) <= 0.18, spreads
    assert max(spreads.values()) >= 0.05, spreads        # the noise is on: a body with no jitter proves nothing


def test_depth_rejects_a_bad_span():
    for bad in (0, 0.0, -0.6, math.nan, math.inf, -math.inf, None, True):
        with pytest.raises(ValueError):
            Depth(span=bad)
    with pytest.raises(ValueError):
        Depth(grace=-1.0)
    assert Depth().span == DEPTH_SPAN == 0.6 and Depth(span=np.float32(0.5)).span == 0.5
