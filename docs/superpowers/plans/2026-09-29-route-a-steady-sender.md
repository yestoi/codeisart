# Route A: the steady sender, implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `show/display/colorlight.py` drives the Colorlight 5A-75E (firmware 13.17) without the flicker: a child process sends 59 frames a second, sync first, BGR, the sync within 100 us of its deadline, whatever the caller's rate.

**Architecture:** Three modules. `colorlight_packets.py` holds the byte builders (unchanged bytes, moved). `colorlight_sender.py` holds the `Slot` (one frame in a file-backed mmap plus a header of int64 fields and one lock), the `Sender` core (one `tick()` a frame, testable with a fake socket and a fake clock) and `sender_main` (the child: real-time priority, gc off). `colorlight.py` keeps `ColorlightDisplay`, the unchanged `Display` protocol: `push` copies to the slot and returns, the sender's errors come back from the next `push`, `close` drains black for a second.

**Tech Stack:** Python 3.11+ (the Pi's system Python), numpy, `multiprocessing` (spawn), `mmap`, `os.sched_setscheduler`, AF_PACKET raw sockets (Linux). Tests: pytest, no real time in the suite.

**Spec:** `docs/superpowers/specs/2026-09-29-route-a-steady-sender-design.md`

## Global Constraints

- Only packet types 0x01, 0x55 and 0x0A go to the card; nothing goes to the card without the owner's word; commits on branch `route-a` only, never pushed.
- Output rate `OUTPUT_FPS = 59.0`, a constant. Never the content's rate.
- Frame order on the wire: sync x2, brightness x2, rows, idle. Pixels BGR. Packet bytes as the spike's builders make them.
- Timing recipe: SCHED_FIFO 50, absolute deadlines on `perf_counter_ns`, sleep to `SPIN_NS = 2 ms` before the deadline then spin, `PACKET_QDISC_BYPASS`. Never a pure spin, never `time.sleep` alone.
- The sender originates no content but black: at the start, at the close, and when its parent dies.
- `arcade/flash.py` and `show/wall.py` do not change.
- No test asserts a rate or an interval in real time.
- Run tests from this worktree with the main checkout's venv: `../codeisart/.venv/bin/python -m pytest`.

## Review Focus

Inputs the spec implies that no task's tests would otherwise exercise; each has its test added to the owning task:

1. A width that splits into several row packets (512): the BGR swap must land in each chunk (Task 3).
2. `set_brightness` with NaN, or a level never set before the first tick: the sync and brightness packets carry 0, never 255 (Task 3).
3. A row's `send` raising after the syncs went out: no sync at the next tick, nothing until a push (Task 3).
4. A launcher whose child never beats: the constructor raises `OSError` after `START_S` and does not hang (Task 6).
5. `close()` twice, or after the child died: no exception, the socket closed once (Task 6).

---

### Task 1: The packets in their own module

**Files:**
- Create: `show/display/colorlight_packets.py`
- Modify: `show/display/colorlight.py` (imports the builders from the new module; the rest is rewritten in Task 6)
- Create: `tests/test_colorlight_packets.py`
- Modify: `tests/test_colorlight.py` (the five packet tests move out)

**Interfaces:**
- Produces: `DST_MAC, SRC_MAC, ETH_ROW, ETH_FRAME, ETH_BRIGHTNESS, CHUNK_PIXELS, ROW_HEADER_LEN, FRAME_PAYLOAD_LEN, BRIGHTNESS_PAYLOAD_LEN`; `level_byte(level: float) -> int`; `sync_bytes(b: int) -> bytes` (112 bytes); `brightness_bytes(b: int) -> bytes` (77 bytes); `frame_packet(level: float) -> bytes` = `sync_bytes(level_byte(level))`; `brightness_packet(level: float) -> bytes`; `row_packets(row: int, pixels: np.ndarray) -> list[bytes]`; `chunk_pixels(width: int) -> int`; `row_buffers(width: int, height: int) -> tuple[np.ndarray, np.ndarray]` (the prebuilt row packets `(height, chunks, ROW_HEADER_LEN + chunk * 3)` uint8, and the view of their pixel bytes `(height, chunks, chunk * 3)`).

- [ ] **Step 1: Write the failing tests**

`tests/test_colorlight_packets.py`:

```python
"""The packets of show/display/colorlight_packets.py: byte for byte the spike's, which are the working test sender's."""
import math

import numpy as np
import pytest

from show.display.colorlight_packets import (BRIGHTNESS_PAYLOAD_LEN, DST_MAC, FRAME_PAYLOAD_LEN, ROW_HEADER_LEN,
                                             SRC_MAC, brightness_bytes, brightness_packet, chunk_pixels,
                                             frame_packet, level_byte, row_buffers, row_packets, sync_bytes)
from tools.sender_spike import send


def test_sync_is_the_spikes_byte_for_byte():
    for b in (0, 25, 102, 255):
        assert sync_bytes(b) == send.sync_packet(send.SyncSpec(level=b), 0)
    assert len(sync_bytes(25)) == 14 + FRAME_PAYLOAD_LEN == 112


def test_brightness_is_the_spikes_byte_for_byte():
    for b in (0, 25, 102, 255):
        assert brightness_bytes(b) == send.brightness_packet(b)
    assert len(brightness_bytes(25)) == 14 + BRIGHTNESS_PAYLOAD_LEN == 77


def test_rows_are_the_spikes_byte_for_byte():
    bars = send.bars(128)                                   # 64 rows of 128 * 3 bytes
    ours = [row_packets(y, np.frombuffer(bars[y], np.uint8).reshape(128, 3))[0] for y in range(64)]
    assert ours == send.row_packets(bars)


def test_level_byte_is_dark_for_nan_zero_and_negative_and_capped_at_255():
    assert level_byte(math.nan) == 0 and level_byte(0.0) == 0 and level_byte(-0.5) == 0
    assert level_byte(0.4) == 102 and level_byte(1.0) == 255 and level_byte(1.7) == 255


def test_frame_packet_matches_falcon_player():
    fp = frame_packet(0.5)
    assert fp[:12] == DST_MAC + SRC_MAC and fp[12:14] == b"\x01\x07" and len(fp) == 112
    assert fp[35] == 127 and fp[36] == 0x05 and fp[38:41] == bytes([127, 127, 127])
    assert sum(fp[14:]) == 127 * 4 + 5


def test_brightness_packet_matches_falcon_player():
    bp = brightness_packet(0.4)
    assert bp[:12] == DST_MAC + SRC_MAC and len(bp) == 77
    assert bp[12] == 0x0A and bp[13:17] == bytes([102, 102, 102, 0xFF])
    assert not any(bp[17:])
    assert brightness_packet(1.7)[13] == 255 and brightness_packet(-1.0)[13] == 0


def test_nan_or_negative_brightness_fails_dark():
    assert brightness_packet(math.nan)[13] == 0 and brightness_packet(math.nan)[14:16] == b"\x00\x00"
    assert frame_packet(math.nan)[35] == 0 and frame_packet(math.nan)[38:41] == b"\x00\x00\x00"
    assert frame_packet(0.0)[35] == 0 and frame_packet(-0.5)[35] == 0


def test_row_packets_chunk_512_pixels_into_two():
    pixels = np.zeros((512, 3), np.uint8)
    pixels[0] = (255, 0, 0)
    pixels[256] = (0, 0, 255)
    pk = row_packets(5, pixels)
    assert len(pk) == 2
    assert pk[0][:6] == DST_MAC and pk[0][6:12] == SRC_MAC and pk[0][12:14] == b"\x55\x00"
    assert pk[0][14:21] == bytes([5, 0, 0, 1, 0, 0x08, 0x88])          # row 5, offset 0, count 256
    assert pk[0][21:24] == bytes([255, 0, 0])                          # bytes as given: the sender swaps
    assert pk[1][14:21] == bytes([5, 1, 0, 1, 0, 0x08, 0x88])          # offset 256
    assert pk[1][21:24] == bytes([0, 0, 255])
    assert all(len(p) == ROW_HEADER_LEN + 256 * 3 for p in pk)


def test_row_packets_split_384_pixels_equally():
    pixels = np.zeros((384, 3), np.uint8)
    pixels[192] = (0, 255, 0)
    pk = row_packets(2, pixels)
    assert [len(p) for p in pk] == [ROW_HEADER_LEN + 192 * 3] * 2
    assert pk[1][14:21] == bytes([2, 0, 192, 0, 192, 0x08, 0x88])
    assert pk[1][21:24] == bytes([0, 255, 0])


def test_row_above_255_sets_ethertype_low_byte():
    pk = row_packets(300, np.zeros((8, 3), np.uint8))
    assert pk[0][12:14] == b"\x55\x01" and pk[0][14] == 300 & 0xFF


def test_width_that_cannot_split_evenly_is_refused():
    with pytest.raises(ValueError, match="width 257"):
        chunk_pixels(257)
    assert chunk_pixels(128) == 128 and chunk_pixels(512) == 256 and chunk_pixels(384) == 192


@pytest.mark.parametrize("width,height", [(128, 64), (512, 4), (384, 4)])
def test_row_buffers_are_the_reference_rows_once_filled(width, height):
    rng = np.random.default_rng(width * height)
    frame = rng.integers(0, 256, (height, width, 3), dtype=np.uint8)
    packets, pixels = row_buffers(width, height)
    chunk = chunk_pixels(width)
    assert packets.shape == (height, width // chunk, ROW_HEADER_LEN + chunk * 3) and pixels.shape == (height, width // chunk, chunk * 3)
    pixels[...] = frame.reshape(height, -1, chunk * 3)
    sent = [bytes(p) for p in packets.reshape(-1, packets.shape[-1])]
    assert sent == [p for y in range(height) for p in row_packets(y, frame[y])]
```

Remove from `tests/test_colorlight.py`: `test_row_packets_chunk_512_pixels_into_two`, `test_row_packets_split_384_pixels_equally`, `test_row_above_255_sets_ethertype_low_byte`, `test_frame_packet_matches_falcon_player`, `test_brightness_packet_matches_falcon_player`, and the three `assert` lines of `test_nan_or_negative_brightness_fails_dark` that test the builders (keep its display part for now; Task 6 rewrites the file).

- [ ] **Step 2: Run the new tests to see them fail**

Run: `../codeisart/.venv/bin/python -m pytest tests/test_colorlight_packets.py -q`
Expected: FAIL, `ModuleNotFoundError: show.display.colorlight_packets`.

- [ ] **Step 3: Create the module and point the driver at it**

`show/display/colorlight_packets.py`:

```python
"""The packets of the Colorlight 5A-75B/E protocol, byte for byte the working test sender's (2026-09-29).

Every packet: destination MAC 11:22:33:44:55:66, source MAC 22:22:33:44:55:66, the packet type at byte 12,
whose first data byte shares the EtherType at byte 13. Offsets count from the start of the Ethernet frame.

- 0x01 the sync ("display frame"), 112 bytes, EtherType 0x0107: the level at 35 and 38 to 40, byte 36 = 0x05.
  The card shows the rows it holds when a sync arrives.
- 0x0A brightness, 77 bytes: the level at 13 to 15, byte 16 = 0xFF.
- 0x55 a row, EtherType 0x5500 | row >> 8: row & 0xFF, pixel offset (2 bytes), pixel count (2 bytes), 0x08,
  0x88, then three bytes a pixel in the order the card takes them (BGR on this card, measured 2026-09-29;
  the sender swaps, these builders copy bytes as given). A row wider than CHUNK_PIXELS is split into equal
  packets.

Constants diffed on 2026-09-27 against Falcon Player's ColorLight-5a-75.cpp and H. Kubota's notes; the spike
of 2026-09-29 (tools/sender_spike/send.py, tests/test_colorlight_packets.py) pins them to the bytes that worked.
A level that is NaN or not above 0 is 0: dark, never bright.
"""
from __future__ import annotations

import math

import numpy as np

DST_MAC = bytes.fromhex("112233445566")
SRC_MAC = bytes.fromhex("222233445566")
ETH_ROW = 0x5500
ETH_FRAME = 0x0107
ETH_BRIGHTNESS = 0x0A00
CHUNK_PIXELS = 256          # most pixels per row packet; Falcon Player allows up to 497
ROW_HEADER_LEN = 14 + 7     # Ethernet header plus the 7-byte row header
FRAME_PAYLOAD_LEN = 98
BRIGHTNESS_PAYLOAD_LEN = 63


def _eth(ethertype: int) -> bytes:
    return DST_MAC + SRC_MAC + ethertype.to_bytes(2, "big")


def level_byte(level: float) -> int:
    """The byte of a level 0 to 1: NaN, zero or negative is 0 (dark), above 1 is 255."""
    if not level > 0.0:
        return 0
    return int(min(1.0, level) * 255)


def _row_header(row: int, offset: int, count: int) -> bytes:
    return _eth(ETH_ROW | (row >> 8)) + bytes([row & 0xFF, offset >> 8, offset & 0xFF,
                                               count >> 8, count & 0xFF, 0x08, 0x88])


def chunk_pixels(width: int) -> int:
    """Pixels per row packet: the row split into the fewest equal packets of at most CHUNK_PIXELS."""
    chunks = math.ceil(width / CHUNK_PIXELS) if width > 0 else 0
    if chunks == 0 or width % chunks:
        raise ValueError(f"width {width} does not split into {chunks} equal row packets")
    return width // chunks


def row_packets(row: int, pixels: np.ndarray) -> list[bytes]:
    """Reference encoder for one row of (width, 3) pixels, bytes as given; the sender's rows must match it."""
    chunk = chunk_pixels(pixels.shape[0])
    out = []
    for off in range(0, pixels.shape[0], chunk):
        data = np.ascontiguousarray(pixels[off : off + chunk], dtype=np.uint8)
        out.append(_row_header(row, off, chunk) + data.tobytes())
    return out


def row_buffers(width: int, height: int) -> tuple[np.ndarray, np.ndarray]:
    """One prebuilt packet per (row, chunk) with its header filled, and the view of the pixel bytes to fill."""
    chunk = chunk_pixels(width)
    chunks = width // chunk
    packets = np.zeros((height, chunks, ROW_HEADER_LEN + chunk * 3), np.uint8)
    for y in range(height):
        for c in range(chunks):
            packets[y, c, :ROW_HEADER_LEN] = np.frombuffer(_row_header(y, c * chunk, chunk), np.uint8)
    return packets, packets[:, :, ROW_HEADER_LEN:]


def sync_bytes(b: int) -> bytes:
    """The sync packet with the level byte b."""
    payload = bytearray(FRAME_PAYLOAD_LEN)
    payload[21] = b
    payload[22] = 0x05
    payload[24] = payload[25] = payload[26] = b
    return _eth(ETH_FRAME) + bytes(payload)


def brightness_bytes(b: int) -> bytes:
    """The brightness packet with the level byte b."""
    payload = bytearray(BRIGHTNESS_PAYLOAD_LEN)
    payload[0] = payload[1] = b
    payload[2] = 0xFF
    return _eth(ETH_BRIGHTNESS | b) + bytes(payload)


def frame_packet(brightness: float) -> bytes:
    return sync_bytes(level_byte(brightness))


def brightness_packet(level: float) -> bytes:
    return brightness_bytes(level_byte(level))
```

In `show/display/colorlight.py`, delete the constants and the builders (`_eth` to `brightness_packet`, and `_level`, `_row_header`, `_chunk_pixels`) and put at the top of the imports:

```python
from show.display.colorlight_packets import (BRIGHTNESS_PAYLOAD_LEN, CHUNK_PIXELS, DST_MAC, ETH_BRIGHTNESS,  # noqa: F401
                                             ETH_FRAME, ETH_ROW, FRAME_PAYLOAD_LEN, ROW_HEADER_LEN, SRC_MAC,
                                             brightness_packet, chunk_pixels, frame_packet, level_byte,
                                             row_buffers, row_packets)
```

and in `ColorlightDisplay.__init__` replace `_chunk_pixels(width)` with `chunk_pixels(width)` and the packet-building loop with `self._packets, self._pixels = row_buffers(width, height)`. Everything else in the file stays for now.

- [ ] **Step 4: Run the packet tests, the driver tests and the spike tests**

Run: `../codeisart/.venv/bin/python -m pytest tests/test_colorlight_packets.py tests/test_colorlight.py tests/test_wall_pattern.py tests/sender_spike -q`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add show/display/colorlight_packets.py show/display/colorlight.py tests/test_colorlight_packets.py tests/test_colorlight.py
git commit -m "refactor(colorlight): the packets in their own module, pinned to the spike's bytes"
```

---

### Task 2: The Slot

**Files:**
- Create: `show/display/colorlight_sender.py`
- Create: `tests/test_colorlight_slot.py`

**Interfaces:**
- Produces: `Slot.create(width, height, lock=None, directory=None) -> Slot`; `Slot.open(path, width, height, lock) -> Slot`; `slot.write(frame)`; `slot.take(into) -> bool`; `slot.close()`; `slot.h` (a numpy int64 view of the header), `slot.path`, `slot.lock`, `slot.width`, `slot.height`; the header indices `FRAME, LEVEL, STOP, PAUSE, BEATS, FRAMES, ERRNO, ERRORS, RT, SLIPS, LATE, WORST, DEV_N, DEV_SUM, DEV_SUMSQ` and `HEADER_LEN = 16`.

- [ ] **Step 1: Write the failing tests**

`tests/test_colorlight_slot.py`:

```python
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
```

- [ ] **Step 2: Run them to see them fail**

Run: `../codeisart/.venv/bin/python -m pytest tests/test_colorlight_slot.py -q`
Expected: FAIL, `ModuleNotFoundError: show.display.colorlight_sender`.

- [ ] **Step 3: Write the Slot**

`show/display/colorlight_sender.py`:

```python
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

import gc
import math
import mmap
import multiprocessing
import os
import tempfile
import time
from typing import Callable

import numpy as np

from show.display.colorlight_packets import brightness_bytes, row_buffers, sync_bytes

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
```

- [ ] **Step 4: Run the slot tests**

Run: `../codeisart/.venv/bin/python -m pytest tests/test_colorlight_slot.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add show/display/colorlight_sender.py tests/test_colorlight_slot.py
git commit -m "feat(colorlight): the slot, one frame the parent and the sender share"
```

---

### Task 3: The Sender core: one burst, whole frames, BGR, the level, the pause and the prime

**Files:**
- Modify: `show/display/colorlight_sender.py`
- Create: `tests/colorlight_fakes.py`
- Create: `tests/test_colorlight_sender.py`

**Interfaces:**
- Consumes: `Slot` (Task 2), `row_buffers`, `sync_bytes`, `brightness_bytes` (Task 1).
- Produces: `Sender(slot, send, *, clock=time.perf_counter_ns, sleep=time.sleep, period_ns=PERIOD_NS, spin_ns=SPIN_NS, parent_alive=lambda: True)`; `sender.tick() -> bool` (False once the stop flag is set); `sender.run()`; `wait_until(target_ns, clock, sleep, spin_ns)`; `stats_of(h) -> dict`; the test fakes `FakeSocket`, `FakeClock`.

- [ ] **Step 1: Write the fakes**

`tests/colorlight_fakes.py`:

```python
"""Fakes for the colorlight driver's tests: a socket that keeps what it was sent, a clock that only moves when
read or slept."""
import numpy as np

from show.display.colorlight_packets import ROW_HEADER_LEN

SYNC, BRIGHTNESS, ROW = 0x01, 0x0A, 0x55


class FakeSocket:
    """Stands in for the AF_PACKET socket, which exists only on Linux. `fail` maps a send number (from 1) to the
    OSError to raise instead of keeping the packet; `hook(n, packet)` runs before send n is kept."""

    def __init__(self, fail=None, hook=None):
        self.sent, self.calls, self.closed = [], 0, 0
        self.fail, self.hook = fail or {}, hook

    def send(self, data):
        self.calls += 1
        if self.hook is not None:
            self.hook(self.calls, bytes(data))
        if self.calls in self.fail:
            raise self.fail[self.calls]
        self.sent.append(bytes(data))       # a copy: the sender reuses its packet buffers
        return len(self.sent[-1])

    def close(self):
        self.closed += 1


class FakeClock:
    """Nanoseconds that move `step_ns` at every read and by the whole sleep at every sleep, so a busy-wait ends."""

    def __init__(self, step_ns=10_000, start_ns=1_000_000_000):
        self.t, self.step, self.slept = start_ns, step_ns, []

    def now(self):
        self.t += self.step
        return self.t

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.t += int(seconds * 1e9)

    def seconds(self):
        return self.t / 1e9


def kinds(packets):
    return [p[12] for p in packets]


def bursts(packets):
    """The packets cut at each first sync (or, with no sync, at each first brightness packet after a row)."""
    out, cur = [], []
    for p in packets:
        starts = p[12] == SYNC and (not cur or cur[-1][12] != SYNC) or (p[12] == BRIGHTNESS and cur and cur[-1][12] == ROW)
        if starts and cur:
            out.append(cur)
            cur = []
        cur.append(p)
    if cur:
        out.append(cur)
    return out


def row_pixels(packet, width):
    """(width, 3) pixels of one row packet, as on the wire (a chunk's worth)."""
    return np.frombuffer(packet[ROW_HEADER_LEN:], np.uint8).reshape(-1, 3)
```

- [ ] **Step 2: Write the failing burst tests**

`tests/test_colorlight_sender.py`:

```python
"""The sender core: one burst a tick, sync first, whole frames, BGR, the level in every packet, the pause after a
failed send, the prime after a start. No real time: a fake clock and a fake socket."""
import errno

import numpy as np
import pytest

from show.display.colorlight_packets import brightness_bytes, row_packets, sync_bytes
from show.display.colorlight_sender import (BRIGHTNESS_REPS, CLOSE_FRAMES, ERRNO, ERRORS, FRAMES, LEVEL, PAUSE,
                                            PERIOD_NS, STOP, SYNC_REPS, BEATS, Sender, Slot)
from tests.colorlight_fakes import BRIGHTNESS, ROW, SYNC, FakeClock, FakeSocket, bursts, kinds, row_pixels

W, H = 128, 64


@pytest.fixture
def slot():
    s = Slot.create(W, H)
    yield s
    s.close()


def make(slot, sock=None, clock=None, **kw):
    sock, clock = sock or FakeSocket(), clock or FakeClock()
    return Sender(slot, sock.send, clock=clock.now, sleep=clock.sleep, **kw), sock, clock


def red(width=W, height=H):
    f = np.zeros((height, width, 3), np.uint8)
    f[..., 0] = 200
    return f


def test_the_first_burst_is_a_prime_and_the_second_a_whole_frame_sync_first(slot):
    sender, sock, _ = make(slot)
    assert sender.tick() and sender.tick()
    first, second = bursts(sock.sent)
    assert kinds(first) == [BRIGHTNESS] * BRIGHTNESS_REPS + [ROW] * H        # the prime: no sync before rows
    assert kinds(second) == [SYNC] * SYNC_REPS + [BRIGHTNESS] * BRIGHTNESS_REPS + [ROW] * H
    assert [p[14] for p in second if p[12] == ROW] == list(range(H))
    assert slot.h[FRAMES] == 1 and slot.h[BEATS] == 2                        # frames count syncs sent


def test_it_starts_dark_and_repeats_the_last_frame(slot):
    sender, sock, _ = make(slot)
    for _ in range(3):
        sender.tick()
    for burst in bursts(sock.sent):
        assert not any(row_pixels(p, W).any() for p in burst if p[12] == ROW)
    slot.write(red())
    sock.sent.clear()
    for _ in range(3):
        sender.tick()
    for burst in bursts(sock.sent):
        rows = [p for p in burst if p[12] == ROW]
        assert all((row_pixels(p, W) == (0, 0, 200)).all() for p in rows)    # BGR on the wire


@pytest.mark.parametrize("width,height", [(128, 64), (512, 4), (384, 4)])
def test_the_rows_are_the_reference_rows_of_the_bgr_frame(slot, width, height):
    s = Slot.create(width, height)
    try:
        sender, sock, _ = make(s)
        frame = np.random.default_rng(width).integers(0, 256, (height, width, 3), dtype=np.uint8)
        s.write(frame)
        sender.tick()
        rows = [p for p in sock.sent if p[12] == ROW]
        assert rows == [p for y in range(height) for p in row_packets(y, frame[y, :, ::-1])]
    finally:
        s.close()


def test_the_level_rides_in_every_sync_and_brightness_packet_and_is_dark_until_set(slot):
    sender, sock, _ = make(slot)
    sender.tick()
    sender.tick()
    assert [p for p in sock.sent if p[12] == SYNC] == [sync_bytes(0)] * SYNC_REPS
    assert [p for p in sock.sent if p[12] == BRIGHTNESS] == [brightness_bytes(0)] * 2 * BRIGHTNESS_REPS
    slot.h[LEVEL] = 102
    sock.sent.clear()
    sender.tick()
    assert [p for p in sock.sent if p[12] == SYNC] == [sync_bytes(102)] * SYNC_REPS
    assert [p for p in sock.sent if p[12] == BRIGHTNESS] == [brightness_bytes(102)] * BRIGHTNESS_REPS


def test_a_burst_is_one_frame_even_when_a_push_lands_inside_it(slot):
    other = np.full((H, W, 3), 50, np.uint8)
    sock = FakeSocket(hook=lambda n, p: slot.write(other) if p[12] == ROW and p[14] == 20 and not slot.h[FRAMES] else None)
    sender, sock, _ = make(slot, sock)
    slot.write(red())
    sender.tick()                                        # the prime: red, with the push at row 20
    sender.tick()
    first, second = bursts(sock.sent)
    assert all((row_pixels(p, W) == (0, 0, 200)).all() for p in first if p[12] == ROW)
    assert all((row_pixels(p, W) == 50).all() for p in second if p[12] == ROW)


def test_a_failed_send_ends_the_burst_records_the_error_and_pauses(slot):
    # the prime is 2 + 64 packets; burst 2's packet 5 is its first row
    sock = FakeSocket(fail={66 + 5: OSError(errno.ENETDOWN, "Network is down")})
    sender, sock, clock = make(slot, sock)
    sender.tick()
    sender.tick()
    second = bursts(sock.sent)[1]
    assert kinds(second) == [SYNC] * 2 + [BRIGHTNESS] * 2                    # the rows after the failure: none
    assert slot.h[PAUSE] == 1 and slot.h[ERRORS] == 1 and slot.h[ERRNO] == errno.ENETDOWN
    sent = len(sock.sent)
    assert sender.tick() and sender.tick()
    assert len(sock.sent) == sent and slot.h[BEATS] == 4                     # paused: nothing, but it beats
    assert clock.slept[-1] > 0                                               # a paused tick sleeps, not spins
    slot.h[PAUSE] = 0                                                        # the parent's push
    sender.tick()
    assert kinds(sock.sent[sent:]) == [BRIGHTNESS] * 2 + [ROW] * H           # the restart primes: no sync
    sender.tick()
    assert sock.sent[-H - 4][12] == SYNC


def test_a_row_failing_after_the_syncs_means_no_sync_until_a_push(slot):
    sock = FakeSocket(fail={66 + 4 + 30: OSError(errno.EIO, "io")})         # burst 2, row 26
    sender, sock, _ = make(slot, sock)
    for _ in range(6):
        sender.tick()
    syncs = [i for i, p in enumerate(sock.sent) if p[12] == SYNC]
    assert syncs == [66, 67]                                                 # burst 2's, and none after


def test_stop_ends_the_ticks_without_a_send(slot):
    sender, sock, _ = make(slot)
    sender.tick()
    slot.h[STOP] = 1
    n = len(sock.sent)
    assert not sender.tick() and len(sock.sent) == n


def test_run_sends_black_for_a_second_when_the_parent_is_gone(slot):
    alive = [True, True, True, False]
    sender, sock, _ = make(slot, parent_alive=lambda: alive.pop(0) if alive else False)
    slot.write(red())
    sender.run()
    out = bursts(sock.sent)
    assert len(out) == 3 + CLOSE_FRAMES + 1                                  # 3 ticks alive, a prime, then black
    assert all((row_pixels(p, W) == (0, 0, 200)).all() for p in out[2] if p[12] == ROW)
    assert not any(row_pixels(p, W).any() for burst in out[3:] for p in burst if p[12] == ROW)
```

- [ ] **Step 3: Run them to see them fail**

Run: `../codeisart/.venv/bin/python -m pytest tests/test_colorlight_sender.py -q`
Expected: FAIL, `ImportError: cannot import name 'Sender'`.

- [ ] **Step 4: Write the Sender**

Append to `show/display/colorlight_sender.py`:

```python
def wait_until(target_ns: int, clock: Callable[[], int], sleep: Callable[[float], None], spin_ns: int = SPIN_NS) -> None:
    """Sleep to spin_ns before the target, then busy-wait to it. time.sleep alone wakes 0.6 to 2.4 ms late; a
    pure busy-wait at real-time priority once stalled 37 ms (the spike's step 6)."""
    ahead = target_ns - clock() - spin_ns
    if ahead > 0:
        sleep(ahead / 1e9)
    while clock() < target_ns:
        pass


class Sender:
    """One output frame a tick. Testable with a fake socket and a fake clock; the child runs it for real."""

    def __init__(self, slot: Slot, send: Callable[[bytes], int], *, clock: Callable[[], int] = time.perf_counter_ns,
                 sleep: Callable[[float], None] = time.sleep, period_ns: int = PERIOD_NS, spin_ns: int = SPIN_NS,
                 parent_alive: Callable[[], bool] = lambda: True):
        self.slot, self.send, self.clock, self.sleep = slot, send, clock, sleep
        self.period, self.spin, self.parent_alive = period_ns, spin_ns, parent_alive
        self.packets, self.pixels = row_buffers(slot.width, slot.height)
        self.rows = self.packets.reshape(-1, self.packets.shape[-1])
        self.frame = np.zeros((slot.height, slot.width, 3), np.uint8)      # black: the dark start
        self._level = -1
        self._syncs: list[bytes] = []
        self._brights: list[bytes] = []
        self.deadline: int | None = None
        self._last_sync: int | None = None
        self._primed = False                                                 # a sync goes only after a whole frame

    def _level_packets(self) -> None:
        level = int(self.slot.h[LEVEL])
        if level != self._level:
            self._level = level
            self._syncs = [sync_bytes(level)] * SYNC_REPS
            self._brights = [brightness_bytes(level)] * BRIGHTNESS_REPS

    def tick(self) -> bool:
        """One burst on its deadline, or a paused poll. False once the stop flag is set (nothing sent)."""
        h = self.slot.h
        h[BEATS] += 1
        if h[STOP]:
            return False
        if h[PAUSE]:
            self.deadline = self._last_sync = None
            self._primed = False
            self.sleep(PAUSE_POLL_S)
            return True
        if self.slot.take(self.frame):
            self.pixels[...] = self.frame[:, :, ::-1].reshape(self.pixels.shape)   # BGR, before the wait
        self._level_packets()
        now = self.clock()
        if self.deadline is None:
            self.deadline = now
        elif now - self.deadline > self.period:                              # a period or more behind: the grid
            self.deadline = now                                              # moves, no catch-up burst
            h[SLIPS] += 1
        wait_until(self.deadline, self.clock, self.sleep, self.spin)
        at = self.clock()
        try:
            if self._primed:
                for p in self._syncs:
                    self.send(p)
            for p in self._brights:
                self.send(p)
            for row in self.rows:
                self.send(row.data)
        except OSError as e:
            h[ERRNO] = e.errno or 0
            h[ERRORS] += 1
            h[PAUSE] = 1                                                     # nothing more until a push
            return True
        if self._primed:
            h[FRAMES] += 1
            late = at - self.deadline
            if late > LATE_NS:
                h[LATE] += 1
            if late > h[WORST]:
                h[WORST] = late
            if self._last_sync is not None:
                dev = (at - self._last_sync) - self.period
                h[DEV_N] += 1
                h[DEV_SUM] += dev
                h[DEV_SUMSQ] += dev * dev
            self._last_sync = at
        self._primed = True
        self.deadline += self.period
        return True

    def run(self) -> None:
        """Ticks until the stop flag; when the parent is gone, black for CLOSE_HOLD_S, then out."""
        while self.parent_alive():
            if not self.tick():
                return
        self.frame[...] = 0
        self.pixels[...] = 0
        self.slot.h[PAUSE] = 0
        for _ in range(CLOSE_FRAMES + 1):                                    # the prime, then CLOSE_FRAMES syncs
            if not self.tick():
                return


def stats_of(h: np.ndarray) -> dict:
    """The sender's numbers so far, from the header: frames sent (with a sync), late ones, slips, the worst
    lateness and the spread of the sync-to-sync interval, in microseconds."""
    n = int(h[DEV_N])
    mean = h[DEV_SUM] / n if n else 0.0
    var = h[DEV_SUMSQ] / n - mean * mean if n else 0.0
    return {"frames": int(h[FRAMES]), "late": int(h[LATE]), "slips": int(h[SLIPS]), "worst_us": h[WORST] / 1e3,
            "mean_us": mean / 1e3, "sd_us": math.sqrt(max(var, 0.0)) / 1e3, "errors": int(h[ERRORS]),
            "rt": bool(h[RT])}
```

- [ ] **Step 5: Run the sender tests**

Run: `../codeisart/.venv/bin/python -m pytest tests/test_colorlight_sender.py -q`
Expected: PASS. If `test_a_failed_send_ends_the_burst...` fails on the packet count, recount: the prime is `BRIGHTNESS_REPS + H` = 66 packets; burst 2's fifth packet is its first row.

- [ ] **Step 6: Commit**

```bash
git add show/display/colorlight_sender.py tests/colorlight_fakes.py tests/test_colorlight_sender.py
git commit -m "feat(colorlight): the sender core: sync first, whole frames, BGR, the pause and the prime"
```

---

### Task 4: The pacing on a fake clock

**Files:**
- Modify: `tests/test_colorlight_sender.py`
- Modify: `show/display/colorlight_sender.py` (only if a test finds a fault)

**Interfaces:**
- Consumes: `Sender`, `wait_until`, `stats_of`, `FakeClock`.

- [ ] **Step 1: Write the failing pacing tests**

Append to `tests/test_colorlight_sender.py`:

```python
from show.display.colorlight_sender import LATE_NS, SPIN_NS, stats_of, wait_until


def sync_times(sock, clock, sender, n):
    """The clock's reading at each burst's first sync, for n ticks."""
    times = []
    sock.hook = lambda k, p: times.append(clock.t) if p[12] == SYNC and sock.sent and sock.sent[-1][12] != SYNC else None
    for _ in range(n):
        sender.tick()
    return times


def test_syncs_sit_on_an_absolute_grid_with_no_drift(slot):
    sender, sock, clock = make(slot)
    times = sync_times(sock, clock, sender, 2001)                    # the prime, then 2000 syncs
    assert len(times) == 2000
    for k, t in enumerate(times):
        assert abs(t - (times[0] + k * PERIOD_NS)) <= 3 * clock.step, k
    assert clock.slept.count(0.0) == 0 and all(0 < s <= PERIOD_NS / 1e9 for s in clock.slept)


def test_the_wait_sleeps_to_spin_ns_before_the_deadline_then_spins():
    clock = FakeClock(step_ns=10_000)
    target = clock.t + 10_000_000
    wait_until(target, clock.now, clock.sleep, SPIN_NS)
    assert len(clock.slept) == 1 and abs(clock.slept[0] - (10_000_000 - SPIN_NS - clock.step) / 1e9) < 2 * clock.step / 1e9
    assert target <= clock.t < target + 2 * clock.step
    clock.slept.clear()
    wait_until(clock.t + SPIN_NS // 2, clock.now, clock.sleep, SPIN_NS)    # inside the spin: no sleep at all
    assert clock.slept == []


def test_a_stall_moves_the_grid_once_with_no_catch_up(slot):
    sender, sock, clock = make(slot)
    times = sync_times(sock, clock, sender, 4)
    clock.t += 100_000_000                                           # a 100 ms stall between ticks
    more = sync_times(sock, clock, sender, 3)
    assert slot.h[SLIPS] == 1
    assert more[0] - times[-1] > 100_000_000                         # the late burst goes at once...
    assert abs((more[1] - more[0]) - PERIOD_NS) <= 3 * clock.step   # ...and the grid restarts from it
    assert abs((more[2] - more[1]) - PERIOD_NS) <= 3 * clock.step
    assert slot.h[FRAMES] == 6 and slot.h[LATE] == 1


def test_stats_read_the_header(slot):
    sender, sock, clock = make(slot)
    for _ in range(11):
        sender.tick()
    s = stats_of(slot.h)
    assert s["frames"] == 10 and s["late"] == 0 and s["slips"] == 0 and s["errors"] == 0 and s["rt"] is False
    assert 0 <= s["worst_us"] < 3 * clock.step / 1e3 and abs(s["mean_us"]) < 3 * clock.step / 1e3
    assert s["sd_us"] < 3 * clock.step / 1e3
    assert stats_of(np.zeros(16, np.int64)) == {"frames": 0, "late": 0, "slips": 0, "worst_us": 0.0, "mean_us": 0.0,
                                                "sd_us": 0.0, "errors": 0, "rt": False}
```

- [ ] **Step 2: Run them**

Run: `../codeisart/.venv/bin/python -m pytest tests/test_colorlight_sender.py -q`
Expected: PASS (the core of Task 3 already paces). A failure names a real fault in `tick` or `wait_until`; fix it there, not in the test, unless the test's arithmetic is wrong (the sync's clock reading is the `at = self.clock()` after the wait, one `step` after the spin's last read).

- [ ] **Step 3: Commit**

```bash
git add tests/test_colorlight_sender.py show/display/colorlight_sender.py
git commit -m "test(colorlight): the sender's pacing on a fake clock: an absolute grid, slips, stats"
```

---

### Task 5: The child process and its scheduling

**Files:**
- Modify: `show/display/colorlight_sender.py` (`set_realtime`, `sender_main`)
- Modify: `show/display/colorlight.py` (`spawn_sender`)
- Modify: `arcade/__main__.py` (the `__name__` guard: the spawned child re-imports the main module)
- Create: `tests/test_colorlight_child.py`

**Interfaces:**
- Produces: `set_realtime(priority: int) -> bool`; `sender_main(path, width, height, lock, sock, parent_pid)`; `spawn_sender(slot, sock) -> multiprocessing.Process` (in `colorlight.py`).

- [ ] **Step 1: Write the failing liveness test**

`tests/test_colorlight_child.py`:

```python
"""The child process: liveness only. It sends on a socket it was handed, beats, stops after a whole burst. No
assertion on rates: those are measured on the target."""
import socket
import time

import pytest

from show.display.colorlight import spawn_sender
from show.display.colorlight_sender import BEATS, FRAMES, RT, STOP, Slot, set_realtime

LENGTHS = {0x01: 112, 0x0A: 77}


def packets(stream):
    """Whole packets from the front of a byte stream, and the tail that is not one yet."""
    out, i = [], 0
    while i + 21 <= len(stream):
        kind = stream[i + 12]
        n = LENGTHS.get(kind) or 21 + int.from_bytes(stream[i + 17:i + 19], "big") * 3
        if i + n > len(stream):
            break
        out.append(stream[i:i + n])
        i += n
    return out, stream[i:]


def test_the_child_sends_on_the_socket_it_was_handed_beats_and_stops_after_a_whole_burst():
    ours, theirs = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    slot = Slot.create(8, 4)
    child = None
    try:
        child = spawn_sender(slot, theirs)
        theirs.close()                                   # the child has its own; the end of the stream is its close
        ours.settimeout(20.0)
        stream, got = b"", []
        deadline = time.monotonic() + 20.0
        while sum(1 for p in got if p[12] == 0x01) < 6 and time.monotonic() < deadline:
            stream += ours.recv(65536)
            got, stream = packets(bytes(stream)) if not got else (got + packets(stream)[0], packets(stream)[1])
        assert sum(1 for p in got if p[12] == 0x01) >= 6, "no third frame in 20 s"
        assert slot.h[BEATS] > 0 and slot.h[FRAMES] >= 3
        slot.h[STOP] = 1
        child.join(10.0)
        assert not child.is_alive() and child.exitcode == 0
        while True:                                      # the rest, to the child's close
            chunk = ours.recv(65536)
            if not chunk:
                break
            stream += chunk
        rest, tail = packets(stream)
        got += rest
        assert tail == b""
        rows = [p for p in got if p[12] == 0x55]
        assert rows and rows[-1][14] == 3                # the last packet out is the last row of a whole burst
        assert got[-1][12] == 0x55
    finally:
        if child is not None and child.is_alive():
            child.terminate()
            child.join(5.0)
        ours.close()
        slot.close()


def test_set_realtime_says_whether_it_got_it():
    got = set_realtime(50)
    assert got in (True, False)
    if got:                                             # root on Linux: put it back
        import os
        os.sched_setscheduler(0, os.SCHED_OTHER, os.sched_param(0))
```

- [ ] **Step 2: Run it to see it fail**

Run: `../codeisart/.venv/bin/python -m pytest tests/test_colorlight_child.py -q`
Expected: FAIL, `ImportError: cannot import name 'spawn_sender'`.

- [ ] **Step 3: Write the child entry, the scheduling and the spawn**

Append to `show/display/colorlight_sender.py`:

```python
def set_realtime(priority: int = RT_PRIORITY) -> bool:
    """SCHED_FIFO at `priority` for this process; False where it cannot be had (no CAP_SYS_NICE, or not Linux)."""
    try:
        os.sched_setscheduler(0, os.SCHED_FIFO, os.sched_param(priority))
    except (AttributeError, OSError):
        return False
    if SENDER_CPU is not None:
        try:
            os.sched_setaffinity(0, {SENDER_CPU})
        except (AttributeError, OSError):
            pass
    return True


def sender_main(path: str, width: int, height: int, lock, sock, parent_pid: int) -> None:
    """The child: the slot attached, the priority asked for, garbage collection off, the sender run to the stop
    flag or the parent's death. `sock` is the parent's socket, duplicated into this process by multiprocessing."""
    slot = Slot.open(path, width, height, lock)
    try:
        slot.h[RT] = 1 if set_realtime() else 0
        gc.disable()
        Sender(slot, sock.send, parent_alive=lambda: os.getppid() == parent_pid).run()
    finally:
        sock.close()
        slot.close()
```

In `show/display/colorlight.py` add (imports `multiprocessing`, `os`, and from `colorlight_sender` import `Slot, sender_main`):

```python
def spawn_sender(slot: Slot, sock) -> multiprocessing.Process:
    """The sender in a child of the spawn kind (a fork behind MediaPipe's threads is not safe). The socket goes
    across as a duplicated descriptor; the parent keeps its own for a restart."""
    ctx = multiprocessing.get_context("spawn")
    child = ctx.Process(target=sender_main, name="colorlight-sender", daemon=True,
                        args=(slot.path, slot.width, slot.height, slot.lock, sock, os.getpid()))
    child.start()
    return child
```

`arcade/__main__.py` becomes:

```python
import sys

from arcade.main import main

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the child test**

Run: `../codeisart/.venv/bin/python -m pytest tests/test_colorlight_child.py -q`
Expected: PASS within a few seconds on the Mac. If the spawn fails to unpickle the socket, the error names `multiprocessing.reduction`: check that `theirs` is a `socket.socket` (not a fake) and that `multiprocessing.get_context("spawn").Lock()` made the slot's lock (a fork-context lock cannot cross into a spawn child).

- [ ] **Step 5: Commit**

```bash
git add show/display/colorlight_sender.py show/display/colorlight.py arcade/__main__.py tests/test_colorlight_child.py
git commit -m "feat(colorlight): the sender's child process, real-time priority when it can have it"
```

---

### Task 6: The facade: `ColorlightDisplay` on the steady sender

**Files:**
- Modify: `show/display/colorlight.py` (rewrite the class and the module docstring)
- Modify: `tests/colorlight_fakes.py` (the `Cranked` launcher)
- Modify: `tests/test_colorlight.py` (rewrite: the old order and cadence tests go)
- Modify: `tests/test_wall_pattern.py` (`test_the_colorlight_backend_gets_the_level_in_its_first_packets` and the two `FakeSocket` users)

**Interfaces:**
- Consumes: `Slot`, `Sender`, `stats_of`, `spawn_sender`, the header fields, `CLOSE_HOLD_S`, `OUTPUT_FPS`.
- Produces: `ColorlightDisplay(width, height, iface, sock=None, brightness=SAFE_BRIGHTNESS, *, launch=spawn_sender, clock=time.monotonic, sleep=time.sleep)` with `push(frame)`, `set_brightness(level)`, `close()`, `stats() -> dict` (the sender's plus `restarts`), `restarts: int`, `brightness: float`, `sock`, `slot`; constants `START_S = 2.0, DEAD_S = 1.0, RESTART_S = 1.0, JOIN_S = 3.0, POLL_S = 0.01`; `stats_line(display) -> str | None`; the test launcher `Cranked`.

- [ ] **Step 1: Add the hand-cranked launcher to the fakes**

Append to `tests/colorlight_fakes.py`:

```python
class Cranked:
    """The sender run by hand in the test's own process, in place of the child: the facade's sleeps crank its
    ticks (a sleep of s seconds is round(s * 59) ticks, at least one), its join runs it to the stop flag."""

    def __init__(self, sock, clock, fps=59.0, launches=None):
        from show.display.colorlight_sender import Sender
        self._Sender, self.sock, self.clock, self.fps = Sender, sock, clock, fps
        self.sender, self.alive, self.exitcode, self.launches = None, False, None, 0
        self.beats = launches                           # None: the sender beats; 0: a child that never beats

    def launch(self, slot, sock):
        self.launches += 1
        self.sender = self._Sender(slot, self.sock.send, clock=self.clock.now, sleep=self.clock.sleep)
        self.alive = True
        return self

    def is_alive(self):
        return self.alive

    def crank(self, n=1):
        for _ in range(n):
            if self.alive and self.beats != 0 and not self.sender.tick():
                self.alive = False

    def sleep(self, seconds):
        self.clock.sleep(seconds)
        self.crank(max(1, round(seconds * self.fps)))

    def join(self, timeout=None):
        for _ in range(10_000):
            if not self.alive:
                return
            self.crank()

    def terminate(self):
        self.alive = False
        self.exitcode = -15

    def kill(self):
        self.terminate()
```

- [ ] **Step 2: Write the failing facade tests**

Rewrite `tests/test_colorlight.py` as:

```python
"""ColorlightDisplay: the facade on the steady sender. The sender runs by hand (tests.colorlight_fakes.Cranked)
in place of the child, on a fake clock; the socket is a fake. The child itself: tests/test_colorlight_child.py."""
import errno
import math
import socket
from types import SimpleNamespace

import numpy as np
import pytest

import show.display.colorlight as colorlight
from show.config import Config
from show.display import make_display
from show.display.colorlight import (DEAD_S, RESTART_S, SAFE_BRIGHTNESS, START_S, ColorlightDisplay, stats_line)
from show.display.colorlight_packets import brightness_bytes, level_byte, sync_bytes
from show.display.colorlight_sender import CLOSE_FRAMES, ERRORS, PAUSE, SYNC_REPS
from show.display.fake import FakeDisplay
from tests.colorlight_fakes import BRIGHTNESS, ROW, SYNC, Cranked, FakeClock, FakeSocket, bursts, kinds, row_pixels

W, H = 128, 32


def display(sock=None, clock=None, cranked=None, **kw):
    sock, clock = sock or FakeSocket(), clock or FakeClock()
    c = cranked or Cranked(sock, clock)
    d = ColorlightDisplay(W, H, "eth0", sock=sock, launch=c.launch, clock=clock.seconds, sleep=c.sleep, **kw)
    return d, sock, clock, c


def black():
    return np.zeros((H, W, 3), np.uint8)


def red():
    f = black()
    f[..., 0] = 200
    return f


def test_it_opens_dark_at_the_safe_brightness_and_the_first_sync_carries_it():
    d, sock, clock, c = display()
    assert d.brightness == SAFE_BRIGHTNESS == 0.4 and c.launches == 1
    c.crank(3)
    out = bursts(sock.sent)
    assert kinds(out[0]) == [BRIGHTNESS] * 2 + [ROW] * H                       # the prime, before any push
    assert [p for p in out[1] if p[12] == SYNC] == [sync_bytes(102)] * SYNC_REPS
    assert [p for p in out[1] if p[12] == BRIGHTNESS] == [brightness_bytes(102)] * 2
    assert not any(row_pixels(p, W).any() for b in out for p in b if p[12] == ROW)
    d.close()


def test_push_copies_the_frame_and_the_wire_shows_it_bgr_until_the_next_push():
    d, sock, clock, c = display()
    frame = red()
    d.push(frame)
    frame[...] = 7                                                              # the caller's array, changed after
    sock.sent.clear()
    c.crank(4)
    for burst in bursts(sock.sent):
        assert all((row_pixels(p, W) == (0, 0, 200)).all() for p in burst if p[12] == ROW)
    d.close()


def test_set_brightness_reaches_every_packet_and_nan_is_dark():
    d, sock, clock, c = display()
    d.set_brightness(0.2)
    assert d.brightness == 0.2
    sock.sent.clear()
    c.crank(2)
    assert all(p[35] == 51 for p in sock.sent if p[12] == SYNC)
    assert all(p[13] == 51 for p in sock.sent if p[12] == BRIGHTNESS)
    d.set_brightness(math.nan)
    sock.sent.clear()
    c.crank(2)
    assert all(p[35] == 0 for p in sock.sent if p[12] == SYNC) and all(p[13] == 0 for p in sock.sent if p[12] == BRIGHTNESS)
    d.close()


def test_push_rejects_a_frame_of_the_wrong_shape_or_type_and_sends_nothing_new():
    d, sock, clock, c = display()
    d.push(red())
    with pytest.raises(ValueError, match="frame shape"):
        d.push(np.zeros((W, H, 3), np.uint8))
    for frame in (np.zeros((H, W, 3)), np.full((H, W, 3), 300, np.int64), np.zeros((H, W, 4), np.uint8)):
        with pytest.raises(ValueError, match="frame"):
            d.push(frame)
    sock.sent.clear()
    c.crank(2)
    assert all((row_pixels(p, W) == (0, 0, 200)).all() for p in sock.sent if p[12] == ROW)
    d.close()


def test_a_failed_send_comes_back_from_the_next_push_which_stores_nothing():
    sock = FakeSocket(fail={66 + 5: OSError(errno.ENETDOWN, "Network is down")})
    d, sock, clock, c = display(sock)
    c.crank(2)                                                                  # burst 2's first row fails
    assert d.slot.h[PAUSE] == 1
    with pytest.raises(OSError, match="ENETDOWN|Network is down|send failed") as e:
        d.push(red())
    assert e.value.errno == errno.ENETDOWN
    assert d.slot.h[PAUSE] == 1 and d.slot.h[ERRORS] == 1
    n = len(sock.sent)
    c.crank(3)
    assert len(sock.sent) == n                                                  # paused: the wall keeps its picture
    d.push(red())                                                               # the hold's repush: the restart
    assert d.slot.h[PAUSE] == 0
    c.crank(2)
    out = bursts(sock.sent[n:])
    assert kinds(out[0]) == [BRIGHTNESS] * 2 + [ROW] * H and out[1][0][12] == SYNC
    assert all((row_pixels(p, W) == (0, 0, 200)).all() for p in out[1] if p[12] == ROW)
    d.close()


def test_a_dead_sender_raises_then_is_restarted_after_a_second_starting_dark():
    d, sock, clock, c = display()
    d.push(red())
    c.crank(2)
    c.alive = False                                                             # the child died
    with pytest.raises(OSError, match="not running"):
        d.push(red())
    clock.sleep(RESTART_S / 2)
    with pytest.raises(OSError, match="not running"):
        d.push(red())
    clock.sleep(RESTART_S)
    sock.sent.clear()
    d.push(red())                                                               # restarted, and this frame taken
    assert c.launches == 2 and d.restarts == 1 and c.alive
    c.crank(2)
    assert all((row_pixels(p, W) == (0, 0, 200)).all() for p in bursts(sock.sent)[1] if p[12] == ROW)
    d.close()


def test_a_child_that_stops_beating_counts_as_dead():
    d, sock, clock, c = display()
    c.beats = 0                                                                 # alive, but never ticks again
    d.push(red())
    clock.sleep(DEAD_S)
    with pytest.raises(OSError, match="not running"):
        d.push(red())
    d.close()


def test_a_child_that_never_starts_is_an_error_at_open():
    sock, clock = FakeSocket(), FakeClock()
    c = Cranked(sock, clock, launches=0)
    with pytest.raises(OSError, match="did not start"):
        ColorlightDisplay(W, H, "eth0", sock=sock, launch=c.launch, clock=clock.seconds, sleep=c.sleep)
    assert clock.seconds() >= START_S and sock.closed == 1


def test_close_drains_black_for_a_second_stops_after_a_whole_burst_and_closes_the_socket():
    d, sock, clock, c = display()
    d.push(red())
    c.crank(3)
    sock.sent.clear()
    d.close()
    out = bursts(sock.sent)
    assert len(out) >= CLOSE_FRAMES
    assert not any(row_pixels(p, W).any() for p in out[-1] if p[12] == ROW)
    assert sock.sent[-1][12] == ROW and sock.sent[-1][14] == H - 1
    assert not c.alive and sock.closed == 1 and d.slot._mm is None
    d.close()                                                                   # twice: harmless
    assert sock.closed == 1


def test_close_after_the_child_died_closes_the_socket_and_the_slot():
    d, sock, clock, c = display()
    c.alive = False
    d.close()
    assert sock.closed == 1 and d.slot._mm is None


def test_close_in_a_pause_restarts_the_stream_on_black():
    sock = FakeSocket(fail={66 + 5: OSError(errno.EIO, "io")})
    d, sock, clock, c = display(sock)
    c.crank(2)
    assert d.slot.h[PAUSE] == 1
    n = len(sock.sent)
    d.close()
    out = bursts(sock.sent[n:])
    assert len(out) >= CLOSE_FRAMES and not any(row_pixels(p, W).any() for b in out for p in b if p[12] == ROW)


def test_stats_and_the_line_for_the_log():
    d, sock, clock, c = display()
    c.crank(5)
    s = d.stats()
    assert s["frames"] == 4 and s["restarts"] == 0 and s["rt"] is False
    line = stats_line(d)
    assert "4 frames" in line and "real-time no" in line
    assert stats_line(FakeDisplay()) is None
    d.close()


def test_the_raw_socket_bypasses_the_queue_before_it_binds(monkeypatch):
    calls = []

    class Raw(FakeSocket):
        def __init__(self, family, kind):
            super().__init__()
            calls.append(("socket", family, kind))

        def setsockopt(self, level, option, value):
            calls.append(("setsockopt", level, option, value))

        def bind(self, address):
            calls.append(("bind", address))

    monkeypatch.setattr(socket, "AF_PACKET", 17, raising=False)
    monkeypatch.setattr(socket, "socket", Raw)
    sock = colorlight._open_raw_socket("eth0")
    assert calls == [("socket", 17, socket.SOCK_RAW), ("setsockopt", 263, 20, 1), ("bind", ("eth0", 0))]
    assert isinstance(sock, Raw)


def test_without_raw_sockets_a_clear_error(monkeypatch):
    monkeypatch.delattr(socket, "AF_PACKET", raising=False)
    with pytest.raises(OSError, match="Linux raw sockets"):
        ColorlightDisplay(W, H, "eth0")


def test_raw_socket_permission_error_names_cap_net_raw(monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(socket, "AF_PACKET", 17, raising=False)
    monkeypatch.setattr(socket, "socket", denied)
    with pytest.raises(PermissionError, match="CAP_NET_RAW"):
        ColorlightDisplay(W, H, "eth0")


def test_failed_bind_closes_the_socket_and_names_the_interface(monkeypatch):
    class Unbindable(FakeSocket):
        def __init__(self, *args):
            super().__init__()
            opened.append(self)

        def setsockopt(self, *args):
            pass

        def bind(self, address):
            raise OSError(19, "No such device")

    opened = []
    monkeypatch.setattr(socket, "AF_PACKET", 17, raising=False)
    monkeypatch.setattr(socket, "socket", Unbindable)
    with pytest.raises(OSError, match="eth7: No such device"):
        ColorlightDisplay(W, H, "eth7")
    assert len(opened) == 1 and opened[0].closed == 1


def test_width_that_cannot_split_evenly_rejected():
    with pytest.raises(ValueError, match="width 257"):
        ColorlightDisplay(257, 4, "eth0", sock=FakeSocket())


class Recorder:
    """Replaces ColorlightDisplay in make_display tests: raw sockets are Linux-only."""

    def __init__(self, width, height, iface, sock=None, **kwargs):
        self.args = (width, height, iface)
        self.kwargs = kwargs


def test_make_display_reads_iface(monkeypatch):
    monkeypatch.setattr(colorlight, "ColorlightDisplay", Recorder)
    cfg = SimpleNamespace(width=128, height=32, backend="colorlight", sdl_scale=8,
                          ddp_host="127.0.0.1", ddp_port=4048, iface="eth9")
    assert make_display(cfg).args == (128, 32, "eth9")


def test_make_display_falls_back_to_colorlight_iface(monkeypatch):
    monkeypatch.setattr(colorlight, "ColorlightDisplay", Recorder)
    assert make_display(Config(backend="colorlight", colorlight_iface="eth3")).args == (512, 192, "eth3")


@pytest.mark.parametrize("cfg", [SimpleNamespace(width=128, height=32, backend="colorlight", sdl_scale=8,
                                                 ddp_host="127.0.0.1", ddp_port=4048, iface=""),
                                 Config(backend="colorlight", colorlight_iface="")],
                         ids=["arcade-shape-empty-iface", "daemon-empty-colorlight-iface"])
def test_make_display_without_an_interface_is_a_clear_error(monkeypatch, cfg):
    monkeypatch.setattr(colorlight, "ColorlightDisplay", Recorder)
    with pytest.raises(ValueError, match="iface"):
        make_display(cfg)


def test_make_display_starts_at_the_configured_brightness(monkeypatch):
    monkeypatch.setattr(colorlight, "ColorlightDisplay", Recorder)
    arcade = SimpleNamespace(width=128, height=32, backend="colorlight", sdl_scale=8, ddp_host="127.0.0.1",
                             ddp_port=4048, iface="eth9", brightness=0.25)
    assert make_display(arcade).kwargs == {"brightness": 0.25}
    daemon = Config(backend="colorlight", colorlight_iface="eth3", brightness=0.9, brightness_cap=0.4)
    assert make_display(daemon).kwargs == {"brightness": 0.4}
    bare = SimpleNamespace(width=128, height=32, backend="colorlight", sdl_scale=8, ddp_host="127.0.0.1",
                           ddp_port=4048, iface="eth9")
    assert make_display(bare).kwargs == {"brightness": SAFE_BRIGHTNESS}
```

In `tests/test_wall_pattern.py`: delete its own `FakeSocket` class and import `Cranked, FakeClock, FakeSocket, SYNC` from `tests.colorlight_fakes`; replace `test_the_colorlight_backend_gets_the_level_in_its_first_packets` with:

```python
def test_the_colorlight_backend_gets_the_level_in_its_first_packets():
    sock, fake = FakeSocket(), FakeClock()
    c = Cranked(sock, fake)
    display = ColorlightDisplay(128, 32, "eth0", sock=sock, brightness=0.1, launch=c.launch, clock=fake.seconds,
                                sleep=c.sleep)
    clock = iter(np.arange(0.0, 100.0, 1.0))
    run("rgb", display, brightness=0.1, seconds=1.0, fps=1, clock=lambda: next(clock), sleep=lambda s: c.crank(2))
    levels = {p[35] for p in sock.sent if p[12] == SYNC}
    assert levels == {int(0.1 * 255)}
    assert sock.closed == 1
```

(The `frame_packet`/`brightness_packet` imports of that file go if nothing else uses them.)

- [ ] **Step 3: Run them to see them fail**

Run: `../codeisart/.venv/bin/python -m pytest tests/test_colorlight.py tests/test_wall_pattern.py -q`
Expected: FAIL, `ImportError: cannot import name 'DEAD_S'`.

- [ ] **Step 4: Rewrite the facade**

`show/display/colorlight.py` in full:

```python
"""Raw Ethernet driver for the Colorlight 5A-75B/E receiving card (Linux only, needs CAP_NET_RAW), as a steady
sender: whatever rate the caller pushes at, the card gets OUTPUT_FPS (59) frames a second from a child process,
sync first, the pixels BGR, the sync within 100 us of its deadline (show/display/colorlight_sender.py). The spec:
docs/superpowers/specs/2026-09-29-route-a-steady-sender-design.md; the measurements behind it:
docs/superpowers/reviews/2026-09-29-sender-card-spike.md, section 5.

push(frame) checks the frame, then the sender's news (below), copies the frame into the shared slot and returns:
nothing is sent by the caller's thread. set_brightness stores the level; every sync and brightness packet from
the next tick carries it. The wall is black from the moment the display opens (the card keeps its last picture
through a restart otherwise), and close() runs black for CLOSE_HOLD_S, stops the sender after a whole burst,
closes the socket and unlinks the slot.

The sender's news comes back through push: a send that raised in the child (recorded, the sender paused) is
raised by the next push, which stores nothing, so show.wall.GovernedDisplay starts its hold as before; the
push that ends the hold (the counted frame again) clears the pause and the stream restarts on it. A child that
died, or stopped beating for DEAD_S, makes push raise "not running" until RESTART_S after, when the next push
starts it again (dark) and is taken.

Brightness: the display starts at SAFE_BRIGHTNESS (0.4, the power-supply cap of both configs) unless
make_display passes the configured level. A level that is NaN or not above 0 is sent as 0: dark, never bright.
"""
from __future__ import annotations

import errno
import logging
import multiprocessing
import os
import socket
import time
from typing import Callable

import numpy as np

from show.display.colorlight_packets import (BRIGHTNESS_PAYLOAD_LEN, CHUNK_PIXELS, DST_MAC, ETH_BRIGHTNESS,  # noqa: F401
                                             ETH_FRAME, ETH_ROW, FRAME_PAYLOAD_LEN, ROW_HEADER_LEN, SRC_MAC,
                                             brightness_packet, chunk_pixels, frame_packet, level_byte,
                                             row_buffers, row_packets)
from show.display.colorlight_sender import (BEATS, CLOSE_HOLD_S, ERRNO, ERRORS, LEVEL, PAUSE, RT, STOP, Slot,
                                            sender_main, stats_of)

log = logging.getLogger(__name__)

SAFE_BRIGHTNESS = 0.4       # the level before set_brightness: arcade.toml's brightness, show.toml's cap
START_S = 2.0               # the child's first beat must come within this of its start
DEAD_S = 1.0                # a child that has not beaten for this long is dead
RESTART_S = 1.0             # a dead child is started again at the first push this long after it died
JOIN_S = 3.0                # the close waits this long for the child, then terminates it
POLL_S = 0.01               # the start's wait between looks at the beat
SOL_PACKET, PACKET_QDISC_BYPASS = 263, 20   # past the port's queue: it reorders one frame in a thousand


def spawn_sender(slot: Slot, sock) -> multiprocessing.Process:
    """The sender in a child of the spawn kind (a fork behind MediaPipe's threads is not safe). The socket goes
    across as a duplicated descriptor; the parent keeps its own for a restart."""
    ctx = multiprocessing.get_context("spawn")
    child = ctx.Process(target=sender_main, name="colorlight-sender", daemon=True,
                        args=(slot.path, slot.width, slot.height, slot.lock, sock, os.getpid()))
    child.start()
    return child


class ColorlightDisplay:
    def __init__(self, width: int, height: int, iface: str, sock=None, brightness: float = SAFE_BRIGHTNESS, *,
                 launch: Callable = spawn_sender, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep):
        chunk_pixels(width)                       # a width that does not split is refused before anything opens
        self.width, self.height = width, height
        self.brightness = brightness
        self.restarts = 0
        self._launch, self._clock, self._sleep = launch, clock, sleep
        self._child = None
        self._seen_errors = 0
        self._died_at: float | None = None
        self._beat = (0, 0.0)
        self.sock = sock if sock is not None else _open_raw_socket(iface)
        self.slot = None
        try:
            self.slot = Slot.create(width, height)
            self.slot.h[LEVEL] = level_byte(brightness)
            self._start()
        except BaseException:
            self.sock.close()
            if self.slot is not None:
                self.slot.close()
            raise

    # -- the child ---------------------------------------------------------------------------------------------

    def _start(self) -> None:
        h = self.slot.h
        h[STOP] = 0
        h[PAUSE] = 0
        before = int(h[BEATS])
        self._child = self._launch(self.slot, self.sock)
        deadline = self._clock() + START_S
        while int(h[BEATS]) == before:
            if not self._child.is_alive() or self._clock() >= deadline:
                self._reap()
                raise OSError(errno.ESRCH, "the colorlight sender did not start")
            self._sleep(POLL_S)
        self._beat = (int(h[BEATS]), self._clock())
        self._died_at = None
        if not h[RT]:
            log.warning("the colorlight sender runs without real-time priority (CAP_SYS_NICE or root gives it): "
                        "the sync may be late now and then")

    def _reap(self) -> None:
        child = self._child
        if child is None:
            return
        if child.is_alive():
            child.terminate()
        child.join(JOIN_S)

    def _alive(self) -> bool:
        if self._child is None or not self._child.is_alive():
            return False
        beats, now = int(self.slot.h[BEATS]), self._clock()
        if beats != self._beat[0]:
            self._beat = (beats, now)
            return True
        return now - self._beat[1] < DEAD_S

    def _check(self) -> None:
        """The sender's news since the last push: a failed send raises it; a dead sender raises, or is
        restarted once RESTART_S has passed."""
        h = self.slot.h
        errors = int(h[ERRORS])
        if errors != self._seen_errors:
            self._seen_errors = errors
            code = int(h[ERRNO])
            raise OSError(code, "the colorlight sender's send failed: %s"
                          % (os.strerror(code) if code else "unknown error"))
        if self._alive():
            return
        now = self._clock()
        if self._died_at is None:
            self._died_at = now
            self._reap()
            log.error("the colorlight sender died (exit code %s); a restart in %.0f s",
                      getattr(self._child, "exitcode", None), RESTART_S)
        if now - self._died_at < RESTART_S:
            raise OSError(errno.ESRCH, "the colorlight sender is not running")
        try:
            self._start()
        except OSError:
            self._died_at = self._clock()
            raise
        self.restarts += 1
        log.info("the colorlight sender restarted (%d so far)", self.restarts)

    # -- the Display protocol ----------------------------------------------------------------------------------

    def push(self, frame: np.ndarray) -> None:
        if frame.shape != (self.height, self.width, 3):
            raise ValueError(f"frame shape {frame.shape} is not ({self.height}, {self.width}, 3)")
        if frame.dtype != np.uint8:
            raise ValueError(f"frame dtype {frame.dtype} is not uint8; convert before push")
        self._check()
        self.slot.write(frame)
        self.slot.h[PAUSE] = 0

    def set_brightness(self, level: float) -> None:
        self.brightness = level
        self.slot.h[LEVEL] = level_byte(level)

    def stats(self) -> dict:
        s = stats_of(self.slot.h)
        s["restarts"] = self.restarts
        return s

    def close(self) -> None:
        """Black for CLOSE_HOLD_S, the sender stopped after a whole burst, the socket closed, the slot unlinked."""
        if self.slot is None:
            return
        try:
            child = self._child
            if child is not None and child.is_alive():
                self.slot.write(np.zeros((self.height, self.width, 3), np.uint8))
                self.slot.h[PAUSE] = 0
                self._sleep(CLOSE_HOLD_S)
                self.slot.h[STOP] = 1
                child.join(JOIN_S)
                if child.is_alive():
                    log.error("the colorlight sender did not stop in %.0f s; terminated", JOIN_S)
                    child.terminate()
                    child.join(JOIN_S)
        finally:
            self.sock.close()
            self.slot.close()
            self.slot = None


def stats_line(display) -> str | None:
    """One line for the log at a close, when the display is the colorlight driver; None otherwise."""
    stats = getattr(display, "stats", None)
    if stats is None:
        return None
    s = stats()
    return ("colorlight sender: %d frames, %d late (over 1 ms), worst %.0f us, sync to sync sd %.0f us, %d slips, "
            "%d send errors, %d restarts, real-time %s" % (s["frames"], s["late"], s["worst_us"], s["sd_us"],
                                                           s["slips"], s["errors"], s["restarts"],
                                                           "yes" if s["rt"] else "no"))


def _open_raw_socket(iface: str) -> socket.socket:
    if not hasattr(socket, "AF_PACKET"):
        raise OSError("the colorlight backend needs Linux raw sockets (AF_PACKET); "
                      "use --backend sdl on this machine")
    try:
        sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
    except PermissionError as e:
        raise PermissionError(f"a raw socket on {iface} needs CAP_NET_RAW: run under the arcade's systemd unit "
                              "(AmbientCapabilities=CAP_NET_RAW) or grant it once with "
                              "sudo setcap cap_net_raw+ep on the venv's real python binary") from e
    try:
        sock.setsockopt(SOL_PACKET, PACKET_QDISC_BYPASS, 1)
    except OSError as e:
        log.warning("cannot bypass the port's queue on %s (%s): packets go through it", iface, e)
    try:
        sock.bind((iface, 0))
    except OSError as e:
        sock.close()
        raise OSError(e.errno, f"cannot bind a raw socket to {iface}: {e.strerror or e}") from e
    return sock
```

Note `close()` after a close: `self.slot is None` returns at once, so the socket is closed once. The test `d.slot._mm is None` after close reads the slot before it is set to None: keep a reference in the test instead (`slot = d.slot` before `d.close()`, then `assert slot._mm is None`); adjust the two tests that read `d.slot` after `close()` accordingly.

- [ ] **Step 5: Run the facade tests, the pattern tests and the hold tests**

Run: `../codeisart/.venv/bin/python -m pytest tests/test_colorlight.py tests/test_wall_pattern.py tests/test_wall_hold.py tests/test_wall_close_hold.py tests/test_wall.py -q`
Expected: PASS. In `test_a_failed_send_comes_back...` the failing send number is 66 + 5 because the prime (2 + H = 34 packets at H = 32!) — recount for H = 32: the prime is `2 + 32 = 34` packets, burst 2's first row is packet 34 + 4 + 1 = 39. Set `fail={39: ...}` in both tests that use it (or compute `PRIME = 2 + H; FIRST_ROW = PRIME + 5`).

- [ ] **Step 6: Run the whole suite**

Run: `../codeisart/.venv/bin/python -m pytest -q -x`
Expected: PASS but for the known skips.

- [ ] **Step 7: Commit**

```bash
git add show/display/colorlight.py tests/colorlight_fakes.py tests/test_colorlight.py tests/test_wall_pattern.py
git commit -m "feat(colorlight): ColorlightDisplay on the steady sender: push copies, errors come back, close drains black"
```

---

### Task 7: The hold's third display model and the sweeps against it

**Files:**
- Modify: `tests/test_wall_hold.py`
- Modify: `tests/test_wall_close_hold.py`

**Interfaces:**
- Produces: `SteadyDisplay(tears, split=H // 2, fps=20)` beside `TornDisplay`; `torn_display(tears, split, model)` with `model` in `"probe"`, `"card"`, `"steady"`.

- [ ] **Step 1: Write the model and parametrize the sweeps**

In `tests/test_wall_hold.py`, after `TornDisplay`:

```python
class SteadyDisplay:
    """The steady sender's model (route A): push raises the error its last torn burst carried back and stores
    nothing, or stores the frame and clears the pause; then the tick's bursts run, ceil(59 / fps) of them. A burst
    numbered in `tears` (bursts counted from 1) writes the rows above `split`, sends no sync and pauses the sender;
    the burst after a push that ends a pause is a prime (rows, no sync). The sync of a burst shows the rows the
    burst before it sent. shown: (tick, the wall after each burst)."""
    def __init__(self, tears, split=H // 2, fps=20):
        self.tears, self.split, self.per_tick = tears, split, math.ceil(59 / fps)
        self.bursts, self.tick, self.closed = 0, 0, False
        self.rows, self.screen, self.shown = DARK.copy(), DARK.copy(), []
        self.pending, self.paused, self.primed, self.error = DARK.copy(), False, False, None

    def push(self, frame):
        if self.error is not None:
            error, self.error = self.error, None
            raise error
        self.pending = frame.copy()
        self.paused = False
        self._run()

    def _run(self):
        for _ in range(self.per_tick):
            if self.paused:
                self.shown.append((self.tick, self.screen.copy()))
                continue
            self.bursts += 1
            if self.primed:
                self.screen = self.rows.copy()                # the sync: the last burst's rows show
            self.primed = True
            if self.tears(self.bursts):
                self.rows[:self.split] = self.pending[:self.split]
                self.paused, self.primed, self.error = True, False, OSError("torn")
            else:
                self.rows = self.pending.copy()
            self.shown.append((self.tick, self.screen.copy()))

    def set_brightness(self, level):
        pass

    def close(self):
        self.pending, self.paused = DARK.copy(), False      # the driver's own black, held a second
        self._run()
        self._run()
        self.closed = True


MODELS = ("probe", "card", "steady")


def torn_display(tears, split=H // 2, model="probe", fps=20):
    if model == "steady":
        return SteadyDisplay(tears, split=split, fps=fps)
    return TornDisplay(tears, split=split, card=model == "card")
```

Add `import math` at the top. Then in the two sweeps replace `@pytest.mark.parametrize("card", [False, True], ids=["probe", "card"])` with `@pytest.mark.parametrize("model", MODELS)`, the parameter `card` with `model`, and `TornDisplay(TEARS[tears], card=card)` with `torn_display(TEARS[tears], model=model, fps=fps)`, `TornDisplay(lambda n, call=call: n == call, split=split, card=card)` with `torn_display(lambda n, call=call: n == call, split=split, model=model)`.

In `tests/test_wall_close_hold.py` import `MODELS, torn_display` too, and in `test_a_close_j_ticks_after_a_tear_stays_in_the_budget_and_ends_black` replace the `card` parametrize with `@pytest.mark.parametrize("model", MODELS)`, `card` with `model`, and `TornDisplay(lambda n: n in torn, split=33, card=card)` with `torn_display(lambda n: n in torn, split=33, model=model)`. The steady model's `rows` after the close are black, so `not shown.rows.any()` holds for it too.

- [ ] **Step 2: Run the sweeps**

Run: `../codeisart/.venv/bin/python -m pytest tests/test_wall_hold.py tests/test_wall_close_hold.py -q`
Expected: PASS for all three models. If a `steady` case fails the budget, that is a finding about the hold under the steady sender, not a test bug: write down which case (pattern, hz, fps, tears) and the count against `BUDGET`, and stop for the owner; do not loosen the test.

- [ ] **Step 3: Commit**

```bash
git add tests/test_wall_hold.py tests/test_wall_close_hold.py
git commit -m "test(wall): the steady sender as a third display model in the hold and close sweeps"
```

---

### Task 8: The pattern tool: deadline pacing, a dry run, the sender's stats

**Files:**
- Modify: `tools/wall_pattern.py`
- Modify: `tests/test_wall_pattern.py`

**Interfaces:**
- Consumes: `ColorlightDisplay`, `stats_line`.
- Produces: `wp.run(..., clock, sleep, ...)` paced by absolute deadlines; `wp.dry_display(width, height, brightness)`; the `--dry-run` flag (`--backend colorlight` with a socket that discards: the driver's timing alone, no root).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_wall_pattern.py`:

```python
def test_run_is_paced_by_deadlines_not_by_sleep_after_push():
    display, slept, now = Recording(), [], [0.0]

    def clock():
        now[0] += 0.02                      # every read costs 20 ms: a slow render
        return now[0]

    def sleep(s):
        slept.append(s)
        now[0] += s

    run("rgb", display, brightness=0.1, seconds=2.0, fps=10, clock=clock, sleep=sleep)
    assert all(0 < s < 0.1 for s in slept)                       # never the whole period: the render's time is taken off
    assert 17 <= len(display.frames) - 2 <= 21                   # about 10 a second for 2 s, the two black ones aside


def test_run_restarts_the_grid_after_a_late_tick_with_no_catch_up():
    display, slept, now = Recording(), [], [0.0]
    reads = [0]

    def clock():
        reads[0] += 1
        now[0] += 0.5 if reads[0] == 6 else 0.001              # one stall of half a second
        return now[0]

    def sleep(s):
        slept.append(s)
        now[0] += s

    run("rgb", display, brightness=0.1, seconds=1.5, fps=10, clock=clock, sleep=sleep)
    assert min(slept) > 0.05 and len(display.frames) - 2 <= 12  # no burst of pushes after the stall


def test_run_prints_the_senders_stats_at_the_end():
    class WithStats(Recording):
        def stats(self):
            return {"frames": 5, "late": 0, "slips": 0, "worst_us": 30.0, "mean_us": 0.0, "sd_us": 4.0,
                    "errors": 0, "restarts": 0, "rt": True}

    said = []
    clock = iter(np.arange(0.0, 100.0, 1.0))
    run("rgb", WithStats(), brightness=0.1, seconds=1.0, fps=1, clock=lambda: next(clock), out=said.append)
    assert any("colorlight sender: 5 frames" in s and "real-time yes" in s for s in said)


def test_dry_run_builds_the_colorlight_driver_on_a_socket_that_discards(monkeypatch):
    made = {}

    def fake_dry(width, height, brightness):
        made.update(width=width, height=height, brightness=brightness)
        return Recording()

    monkeypatch.setattr(wp, "dry_display", fake_dry)
    monkeypatch.setattr(wp.time, "sleep", lambda s: None)
    assert wp.main(["rgb", "--dry-run", "--brightness", "0.2", "--seconds", "0.01"]) == 0
    assert made == {"width": 128, "height": 64, "brightness": 0.2}


def test_dry_display_is_the_driver_with_a_discarding_socket():
    from tests.colorlight_fakes import Cranked, FakeClock, FakeSocket

    sock, clock = FakeSocket(), FakeClock()
    c = Cranked(sock, clock)
    d = wp.dry_display(128, 64, 0.1, launch=c.launch, clock=clock.seconds, sleep=c.sleep)
    assert d.width == 128 and d.brightness == 0.1
    assert d.sock.send(b"x" * 405) == 405 and d.sock is not sock       # the discarding sink, not a raw socket
    d.sock = sock                                                       # so close() closes the fake
    d.close()
```

- [ ] **Step 2: Run them to see them fail**

Run: `../codeisart/.venv/bin/python -m pytest tests/test_wall_pattern.py -q`
Expected: FAIL: the pacing test's `slept` holds `0.1` values; `dry_display` missing.

- [ ] **Step 3: Change the tool**

In `tools/wall_pattern.py`:

- Import `stats_line` and `ColorlightDisplay`: `from show.display.colorlight import ColorlightDisplay, stats_line  # noqa: E402`.
- Add after `MAX_FPS`:

```python
class _Discard:
    """A socket that keeps nothing: the driver's timing with no card and no root (--dry-run)."""
    def send(self, data):
        return len(data)

    def close(self):
        pass


def dry_display(width: int, height: int, brightness: float, **kw):
    return ColorlightDisplay(width, height, "", sock=_Discard(), brightness=brightness, **kw)
```

- In `run`, replace the loop and the docstring's pacing sentence with deadline pacing, and print the stats before the close:

```python
    try:
        wall.set_brightness(level)
        start = clock()
        due = start
        while True:
            t = clock() - start
            if seconds > 0 and t >= seconds:
                break
            if pattern == "steps" and brightness * STEPS[step_of(t)] != level:
                level = brightness * STEPS[step_of(t)]
                wall.set_brightness(level)
            wall.push(PATTERNS[pattern](width, height, t))
            due += 1.0 / fps                 # the next push is due a period after this one was, not after it returned
            wait = due - clock()
            if wait > 0:
                sleep(wait)
            else:                            # late: run at once, the grid restarts from now (no catch-up burst)
                due = clock()
    except KeyboardInterrupt:
        pass
    except OSError as e:
        out(f"wall_pattern: the display failed: {e}")
        code = 1
    finally:
        line = stats_line(display)
        if line:
            out(line)
        wall.close()        # the counted frame again if its send failed, then governed black, then closed
    return code
```

- In `build_parser` add `p.add_argument("--dry-run", action="store_true", help="the colorlight driver on a socket that discards: its timing alone, no card, no root; prints the sender's stats")`.
- In `main`, before `if args.backend not in BACKENDS`:

```python
    if args.dry_run:
        refusal = _refusal(args.pattern, args.brightness, cap) or _rate_refusal(args.fps, args.gamma)
        if refusal:
            print(refusal)
            return 2
        display = dry_display(args.width, args.height, args.brightness)
        return run(args.pattern, display, args.width, args.height, brightness=args.brightness,
                   seconds=args.seconds, fps=args.fps, sleep=time.sleep, gamma=args.gamma, cap=cap)
```

- The module docstring gains the line `python tools/wall_pattern.py rgb --dry-run --seconds 30   # the driver's timing on this machine, no card` and, in the paragraph on the colorlight backend, "the driver sends 59 frames a second from a child process whatever --fps is; --fps paces the pushes only".

- [ ] **Step 4: Run the tool's tests**

Run: `../codeisart/.venv/bin/python -m pytest tests/test_wall_pattern.py -q`
Expected: PASS. If `test_run_is_paced_by_deadlines...` counts fall outside 17 to 21, print `len(display.frames)` and check the clock's reads per loop (three a tick: the `t`, the `wait`, and the pattern's none) before touching the bounds.

- [ ] **Step 5: Commit**

```bash
git add tools/wall_pattern.py tests/test_wall_pattern.py
git commit -m "feat(wall_pattern): deadline pacing, a dry run of the driver, the sender's stats"
```

---

### Task 9: The loops log the sender's stats at the close; the unit grants the priority

**Files:**
- Modify: `arcade/main.py` (the `finally: display.close()` in `run`)
- Modify: `show/main.py` (`_close`, before `self.wall.close()`)
- Modify: `deploy/show.service`, `deploy/README.md`
- Modify: `tests/test_deploy.py`

**Interfaces:**
- Consumes: `stats_line` (Task 6).

- [ ] **Step 1: Write the failing deploy test change**

In `tests/test_deploy.py`, find the assertion that pins `AmbientCapabilities` (it reads `== "CAP_NET_RAW"`) and change it to `== "CAP_NET_RAW CAP_SYS_NICE"`; add to the README test that names the colorlight backend:

```python
def test_readme_says_the_sender_needs_cap_sys_nice():
    text = (ROOT / "deploy/README.md").read_text()
    assert "CAP_SYS_NICE" in text and "59 frames" in text
```

(`ROOT` as the file already defines it; if it reads the files another way, follow that way.)

- [ ] **Step 2: Run it to see it fail**

Run: `../codeisart/.venv/bin/python -m pytest tests/test_deploy.py -q`
Expected: FAIL on the capabilities and the README.

- [ ] **Step 3: Change the unit, the README and the loops**

`deploy/show.service`: the capabilities line becomes

```
# CAP_NET_RAW for the colorlight backend's raw socket; CAP_SYS_NICE for its sender's real-time priority (SCHED_FIFO).
AmbientCapabilities=CAP_NET_RAW CAP_SYS_NICE
```

`deploy/README.md`: the heading `# Pi 4 deployment` becomes `# Pi 5 deployment` with a first line "The show's target is a Raspberry Pi 5 (2026-09-29); the steps were written on a Pi 4 and are the same." The "Colorlight raw backend" section becomes:

```
## Colorlight raw backend

The unit grants `CAP_NET_RAW` (`AmbientCapabilities`), needed only for the `colorlight`
backend, and `CAP_SYS_NICE`: the driver sends from a child process at real-time priority
(SCHED_FIFO 50), 59 frames a second whatever the show's `fps`, because the card flickers at
any other rate (docs/superpowers/reviews/2026-09-29-sender-card-spike.md). Without the
capability the sender runs at ordinary priority and logs a warning; the sync may then be
late now and then. The card sits on the Pi's own Ethernet port; a USB adapter batches
packets and has not been measured.
```

`arcade/main.py`, in `run`:

```python
        finally:
            line = stats_line(display)
            if line:
                log.info(line)
            display.close()
```

with `from show.display.colorlight import stats_line` among the imports.

`show/main.py`, in `_close`, the wall's block:

```python
        if self.wall is not None:
            try:
                line = stats_line(self.wall.display)
                if line:
                    log.info(line)
                self._now = self.clock()                      # the wall's clock at the close: its wait (C53)
                self.wall.close()
            except Exception:
                log.exception("closing the wall failed")
```

with `from show.display.colorlight import stats_line` among the imports (`show.display.colorlight` imports no Linux-only module at import time: check `python -c "import show.display.colorlight"` passes on the Mac).

- [ ] **Step 4: Run the deploy tests, the show's and the arcade's**

Run: `../codeisart/.venv/bin/python -m pytest tests/test_deploy.py tests/test_main.py tests/arcade/test_main.py -q` (use the show's and the arcade's main test files as they are named; `ls tests | grep main`).
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add arcade/main.py show/main.py deploy/show.service deploy/README.md tests/test_deploy.py
git commit -m "feat: the loops log the sender's stats at the close; the unit grants CAP_SYS_NICE"
```

---

### Task 10: The bench: the driver's timing on the Omarchy box, no card

**Files:** none in the repo (a report file under `docs/superpowers/reviews/2026-09-29-route-a/` if the numbers are worth keeping).

This task runs the driver on the machine that stands in for the target tonight. Nothing goes to the card: the dry run has no socket.

- [ ] **Step 1: rsync the tree to the box's test tree**

```bash
rsync -a --delete --exclude .venv --exclude .git --exclude __pycache__ --exclude entries ./ omarchy:~/Work/codeisart-wall/
```

- [ ] **Step 2: The suite there**

```bash
ssh omarchy 'cd ~/Work/codeisart-wall && .venv/bin/python -m pytest tests/test_colorlight.py tests/test_colorlight_sender.py tests/test_colorlight_child.py tests/test_colorlight_slot.py tests/test_colorlight_packets.py -q'
```

Expected: PASS, including the child test on Linux (a spawn child with a socketpair).

- [ ] **Step 3: The dry run at ordinary priority, then at real-time**

```bash
ssh omarchy 'cd ~/Work/codeisart-wall && .venv/bin/python tools/wall_pattern.py grid --dry-run --seconds 30 --fps 20'
ssh omarchy 'cd ~/Work/codeisart-wall && chrt -f 50 .venv/bin/python tools/wall_pattern.py grid --dry-run --seconds 30 --fps 20'
```

The second needs the owner's sudo hour or `CAP_SYS_NICE` (the child asks for the priority itself; `chrt` on the parent is a second way). Read the stats line: worst under 100 us and sd under 20 us at real-time is the spike's bar; late 0.

- [ ] **Step 4: Write the numbers down**

In `docs/superpowers/reviews/2026-09-29-route-a/00-bench.md`: the two stats lines, the scheduling, the box, the date and time. Commit.

---

### Task 11: At the wall (the owner present, the LEDVision VM off, sudo granted)

**Files:** `docs/superpowers/reviews/2026-09-29-route-a/00-bench.md` (the verdicts appended), `docs/superpowers/workflow/evidence/hardware.md` (a dated entry).

Nothing goes to the card without the owner's word for each run. Before any run: `tools/ledvision/vm.py status` says off; the owner is in front of the wall.

- [ ] **Step 1: The rgb check** — `sudo .venv/bin/python tools/wall_pattern.py rgb --iface enp5s0 --brightness 0.1 --seconds 20`: red, green, blue, white from the left. Ctrl-C lands black, three times of three (`grid`, 3 runs).
- [ ] **Step 2: Steady by eye** — `grid` for 60 s at the tool's default 20 pushes a second, then `--fps 30`: no flicker, the bottom rows clean. The stats line at the end: late 0, worst under 100 us.
- [ ] **Step 3: Q66 at 59** — `grid --seconds 20 --stop-for 5`: 5 s in, the stream stops by the driver's own pause (a SIGSTOP would read as a dead child and be restarted after 1 s) and restarts 5 s later: the picture stays, steady, no blink at the stop or the restart. The owner's word on it.
- [ ] **Step 4: The cable** — during `grid`, pull the cable for 5 s: does the tool print "the display failed" (send raised), what the wall shows, what it does when the cable returns.
- [ ] **Step 5: The 240 fps clip** — the phone at 240 fps on `grid` at 59, then on the wall holding a frame (the child stopped): gone, or too fast to see.
- [ ] **Step 6: Write it down** — the verdicts in `00-bench.md` and a dated entry in `hardware.md`; commit.

---

## Self-review

- Spec coverage: section 1 (Tasks 1, 3), 2 (Tasks 2 to 6), 3 (Tasks 3, 6), 4 (Tasks 3, 6, 7), 5 (Tasks 8, 9), 6 (Tasks 3, 6, 8, 9), 7 (Tasks 5, 9), 8 (Tasks 1 to 9), 9 (Tasks 10, 11; the Pi itself waits on the owner), 10 (nothing built).
- Names used across tasks: `Slot.create/open/write/take/close`, `slot.h`, the header indices, `Sender(slot, send, *, clock, sleep, period_ns, spin_ns, parent_alive)`, `tick`, `run`, `wait_until`, `stats_of`, `set_realtime`, `sender_main`, `spawn_sender(slot, sock)`, `ColorlightDisplay(..., launch=, clock=, sleep=)`, `stats`, `stats_line`, `Cranked(sock, clock, launches=)`, `FakeSocket(fail=, hook=)`, `FakeClock(step_ns=)`, `bursts`, `kinds`, `row_pixels`, `torn_display(tears, split, model, fps)`, `dry_display(width, height, brightness, **kw)`.
- Packet counts in tests depend on `H`: the prime is `BRIGHTNESS_REPS + H` packets, a full burst `SYNC_REPS + BRIGHTNESS_REPS + H`; Task 3 uses H = 64 (prime 66), Task 6 uses H = 32 (prime 34). The implementer recounts before trusting a literal.
