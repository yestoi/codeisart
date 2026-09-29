"""The governed wall's close after a failed push (it13 T-wall, note it12 3).

The safety tests are the plan's, as given (docs/superpowers/plans/2026-09-29-it13-pattern-and-soak.md, T-wall):
a send that raised left the counted frame unshown, so close sends it before the governed black.
"""
import numpy as np
import pytest

from arcade.flash import FlashGovernor
from show.wall import GovernedDisplay
from tests.test_main import FailingPushes, no_devices, playing_loop  # noqa: F401 (no_devices: the autouse fixture)
from tests.test_wall import FPS, H, W, strobe

# -- the plan's safety tests, as given ------------------------------------------------------------------------------

LIT = np.full((H, W, 3), (51, 255, 51), np.uint8)


def test_close_after_a_failed_push_sends_the_counted_frame_before_black():
    inner, reference = FailingPushes({31}), FlashGovernor(H, W, 2.2, fps=FPS)
    wall, frames = GovernedDisplay(inner, H, W, fps=FPS), strobe(31)
    for f in frames[:30]:
        wall.push(f)
        reference.apply(f)
    with pytest.raises(OSError):
        wall.push(frames[30])                                     # governed and counted, never shown
    assert wall.unsent and wall.failed == 1 and wall.governed == 30
    black = np.zeros((H, W, 3), np.uint8)
    want = [reference.apply(frames[30]).copy(), reference.apply(black).copy(), reference.apply(black).copy()]
    wall.close()
    assert inner.count == 33 and inner.closed and not wall.unsent
    assert all(np.array_equal(got, w) for got, w in zip(inner.pushed[-3:], want))


def test_close_after_a_mended_failure_is_the_clean_close():
    inner = FailingPushes({6})
    wall = GovernedDisplay(inner, H, W, fps=FPS)
    for _ in range(5):
        wall.push(LIT)
    with pytest.raises(OSError):
        wall.push(LIT)                                            # call 6
    wall.repush()
    wall.push(LIT)                                                # calls 7 and 8: the loop's next step mends it
    assert not wall.unsent and wall.failed == 1
    wall.close()                                                  # calls 9 and 10: black, nothing sent again
    assert inner.count == 9 and inner.closed
    assert not inner.pushed[-1].any() and not inner.pushed[-2].any() and inner.pushed[-3].any()


def test_close_when_the_repush_fails_still_darkens_and_closes():
    inner = FailingPushes({6, 7})
    wall = GovernedDisplay(inner, H, W, fps=FPS)
    for _ in range(5):
        wall.push(LIT)
    with pytest.raises(OSError):
        wall.push(LIT)                                            # call 6
    wall.close()                                                  # call 7, the repush, fails; 8 and 9 black
    assert inner.closed and inner.count == 7 and wall.failed == 2
    assert not inner.pushed[-1].any() and not inner.pushed[-2].any()


def test_the_loop_s_close_after_a_failed_push_sends_the_counted_frame_first(tmp_path):
    inner = FailingPushes({3})
    loop = playing_loop(tmp_path, inner)                          # call 1
    loop.step(0.10)
    loop.step(0.15)                                               # call 2; call 3 fails: its frame was governed
    counted = loop.wall.last.copy()
    loop._close()                                                 # calls 4 (the counted frame), 5 and 6 (black)
    assert inner.count == 5 and inner.closed and np.array_equal(inner.pushed[2], counted)

# -- the rest --------------------------------------------------------------------------------------------------------


def test_last_is_the_governed_frame_and_read_only():
    inner = FailingPushes(set())
    wall = GovernedDisplay(inner, H, W, fps=FPS)
    assert wall.last is None and not wall.unsent and wall.failed == 0
    for f in (LIT, LIT, np.zeros_like(LIT)):
        out = wall.push(f)
    assert np.array_equal(wall.last, out) and np.array_equal(wall.last, inner.pushed[-1])
    with pytest.raises(ValueError):
        wall.last[0, 0, 0] = 1
    assert np.array_equal(wall.last, inner.pushed[-1])


def test_a_close_with_nothing_pushed_sends_only_black():
    inner = FailingPushes(set())
    wall = GovernedDisplay(inner, H, W, fps=FPS)
    wall.close()
    assert inner.count == 2 and inner.closed and not any(p.any() for p in inner.pushed)


def test_a_keyboard_interrupt_in_the_close_s_repush_still_closes_the_display():
    class Interrupted(FailingPushes):
        def push(self, frame):
            if self.calls == 1:                                   # the second call, the close's repush
                self.calls += 1
                raise KeyboardInterrupt
            super().push(frame)

    inner = Interrupted({1})
    wall = GovernedDisplay(inner, H, W, fps=FPS)
    with pytest.raises(OSError):
        wall.push(LIT)
    with pytest.raises(KeyboardInterrupt):
        wall.close()
    assert inner.closed and inner.count == 0 and wall.failed == 1 and wall.unsent
