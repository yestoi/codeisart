"""The slot the parent and the sender share: one frame and a header, a lock the sender never waits on."""
import os

import numpy as np

from show.display.colorlight_sender import FRAME, HEADER_LEN, LEVEL, PAUSE, STOP, Slot


def test_a_frame_written_is_taken_whole_and_only_once():
    slot = Slot.create(8, 4)
    try:
        frame = np.arange(8 * 4 * 3, dtype=np.uint8).reshape(4, 8, 3)
        into = np.zeros((4, 8, 3), np.uint8)
        assert not slot.take(into) and not into.any()          # nothing written yet
        slot.write(frame)
        assert slot.h[FRAME] == 1
        assert slot.take(into) and (into == frame).all()
        assert not slot.take(into)                              # the same frame is not new twice
        frame[0, 0] = 7
        assert not slot.take(into) and into[0, 0, 0] == 0       # write copied: the caller's array is not shared
    finally:
        slot.close()


def test_take_does_not_wait_for_a_held_lock():
    slot = Slot.create(8, 4)
    try:
        slot.write(np.ones((4, 8, 3), np.uint8))
        into = np.zeros((4, 8, 3), np.uint8)
        assert slot.lock.acquire(block=False)
        try:
            assert not slot.take(into) and not into.any()       # the parent holds it: the last frame again
        finally:
            slot.lock.release()
        assert slot.take(into) and into.all()
    finally:
        slot.close()


def test_the_header_starts_at_zero_and_is_shared_through_the_file():
    slot = Slot.create(8, 4)
    try:
        assert len(slot.h) == HEADER_LEN and not slot.h.any()
        slot.h[LEVEL], slot.h[STOP], slot.h[PAUSE] = 102, 1, 1
        other = Slot.open(slot.path, 8, 4, slot.lock)
        try:
            assert other.h[LEVEL] == 102 and other.h[STOP] == 1 and other.h[PAUSE] == 1
            slot.write(np.full((4, 8, 3), 9, np.uint8))
            into = np.zeros((4, 8, 3), np.uint8)
            assert other.take(into) and (into == 9).all()
        finally:
            other.close()
        assert os.path.exists(slot.path)
    finally:
        slot.close()
    assert not os.path.exists(slot.path)                        # the creator unlinks; a second close is harmless
    slot.close()
