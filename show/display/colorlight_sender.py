"""The steady sender of the Colorlight driver: 59 frames a second to the card, whatever the caller's rate.

The spec: docs/superpowers/specs/2026-09-29-route-a-steady-sender-design.md. What the card wants was measured
on 2026-09-29 (docs/superpowers/reviews/2026-09-29-sender-card-spike.md, section 5): the sync first, then the
brightness packets, then the rows, then idle; 59 frames a second, not 60; the sync within 100 us of its
deadline; pixels BGR.

The Slot is one frame in shared memory (a file-backed mmap, /dev/shm where there is one) with a header of int64
fields and one lock. The parent writes a frame under the lock; the sender tries the lock without waiting at each
tick and keeps the frame it has when it cannot get it, so the parent can never make it late.

The Sender runs in a child process (sender_main): real-time priority SCHED_FIFO 50 when it can have it, garbage
collection off, absolute deadlines on perf_counter_ns, a sleep to SPIN_NS before each deadline and then a
busy-wait. It sends the last frame it took until a new one comes. It starts dark, and sends black for
CLOSE_HOLD_S when its parent dies. A send that raises ends the burst (no sync follows a torn frame), records
the error and pauses the sender until the parent's next push clears the pause; the first burst after a start or
a pause is a prime (brightness and rows, no sync), so the sync that follows shows a whole frame.
"""
from __future__ import annotations

import mmap
import multiprocessing
import os
import tempfile

import numpy as np

OUTPUT_FPS = 59.0                       # measured steadiest (N15b, N19); 60.00 drops a frame every ~15 s
PERIOD_NS = round(1e9 / OUTPUT_FPS)
SPIN_NS = 2_000_000                     # sleep to this before the deadline, then busy-wait
LATE_NS = 1_000_000                     # a sync this long after its deadline is counted late
PAUSE_POLL_S = 0.005                    # while paused: nothing sent, the flags read this often
CLOSE_HOLD_S = 1.0                      # black runs this long at the close, and when the parent dies
CLOSE_FRAMES = round(CLOSE_HOLD_S * OUTPUT_FPS)
SYNC_REPS = 2
BRIGHTNESS_REPS = 2
RT_PRIORITY = 50
SENDER_CPU = None                       # a core to pin the child to; None until the Pi says it helps

# The header's int64 fields. Both sides read and write single fields without the lock: a field is one aligned
# 64-bit store, and no reading depends on two fields changing together.
(FRAME, LEVEL, STOP, PAUSE, BEATS, FRAMES, ERRNO, ERRORS, RT, SLIPS, LATE, WORST, DEV_N, DEV_SUM,
 DEV_SUMSQ) = range(15)
HEADER_LEN = 16                         # int64s; 128 bytes before the frame


class Slot:
    """One frame and the header, shared by the parent (create) and the sender (open)."""

    def __init__(self, path: str, width: int, height: int, lock, mm: mmap.mmap, own: bool):
        self.path, self.width, self.height, self.lock, self._mm, self._own = path, width, height, lock, mm, own
        self.h = np.frombuffer(mm, np.int64, HEADER_LEN)
        self.pixels = np.frombuffer(mm, np.uint8, height * width * 3, HEADER_LEN * 8).reshape(height, width, 3)
        self._seen = 0

    @staticmethod
    def size(width: int, height: int) -> int:
        return HEADER_LEN * 8 + height * width * 3

    @classmethod
    def create(cls, width: int, height: int, lock=None, directory: str | None = None) -> "Slot":
        if directory is None and os.path.isdir("/dev/shm"):
            directory = "/dev/shm"
        fd, path = tempfile.mkstemp(prefix="colorlight-", suffix=".slot", dir=directory)
        try:
            os.ftruncate(fd, cls.size(width, height))
            mm = mmap.mmap(fd, cls.size(width, height))
        finally:
            os.close(fd)
        if lock is None:
            lock = multiprocessing.get_context("spawn").Lock()   # the child is spawned: a spawn-context lock
        return cls(path, width, height, lock, mm, own=True)

    @classmethod
    def open(cls, path: str, width: int, height: int, lock) -> "Slot":
        fd = os.open(path, os.O_RDWR)
        try:
            mm = mmap.mmap(fd, cls.size(width, height))
        finally:
            os.close(fd)
        return cls(path, width, height, lock, mm, own=False)

    def write(self, frame: np.ndarray) -> None:
        """The parent's push: a copy of the frame under the lock, and the counter moved."""
        with self.lock:
            self.pixels[...] = frame
            self.h[FRAME] += 1

    def take(self, into: np.ndarray) -> bool:
        """The sender's read: a new frame copied into `into` (True), or nothing, at once, when there is none
        or the lock is held."""
        if not self.lock.acquire(block=False):
            return False
        try:
            if self.h[FRAME] == self._seen:
                return False
            into[...] = self.pixels
            self._seen = int(self.h[FRAME])
            return True
        finally:
            self.lock.release()

    def close(self) -> None:
        if self._mm is None:
            return
        self.h = self.pixels = None          # the views must go before the map closes
        self._mm.close()
        self._mm = None
        if self._own:
            try:
                os.unlink(self.path)
            except FileNotFoundError:
                pass
