import math
import zlib

import numpy as np
import pytest

from arcade.input import CAPTURE_GRACE, Cursor, Edge, Hold, OneEuro, capture_grace
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
