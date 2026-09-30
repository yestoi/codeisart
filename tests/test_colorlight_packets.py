"""The packets of show/display/colorlight_packets.py: byte for byte the spike's, which are the working test sender's."""
import math
from dataclasses import replace

import numpy as np
import pytest

from show.display.colorlight_packets import (COUNTER_OFFSET, DST_MAC, ETH_FRAME, FRAME_PAYLOAD_LEN, LEVEL_OFFSET,
                                             ROW_HEADER_LEN, ROW_TAIL, SRC_MAC, SYNC_LEN, chunk_pixels, frame_packet,
                                             level_byte, row_buffers, row_packets, sync_bytes)
from tools.sender_spike import send

# What the wall was clean with on 2026-09-30 (docs/superpowers/reviews/2026-09-30-ghosting/07-wall-session.md,
# "the winning configuration"): the spike sender's --s2 --byte36 05 with the level in the sync.
WINNING = ["--s2", "--fps", "60.32", "--sync-level", "0.1", "--byte36", "05", "--dry-run"]


def s2_sync(level, frame):
    """The spike's sync for the winning run, its counter from 0, for frame n."""
    return send.sync_packet(replace(send.S2_SYNC, level=level, byte36=0x05, counter_start=0), frame)


def test_sync_is_the_winning_runs_byte_for_byte():
    plan = send.plan_from(WINNING)
    for b in (0, 25, 102, 255):
        for n in (0, 1, 189, 255, 256, 1000):
            assert sync_bytes(b, n) == s2_sync(b, n)
            assert sync_bytes(b, n) == send.sync_packet(replace(plan.sync, level=b, counter_start=0), n)
    assert len(sync_bytes(25)) == 14 + FRAME_PAYLOAD_LEN == SYNC_LEN == 1036 == plan.sync.length
    assert sync_bytes(25) == sync_bytes(25, 0)


def test_the_winning_run_is_one_sync_a_frame_no_brightness_packet_rows_behind_it():
    plan = send.plan_from(WINNING)
    assert plan.sync_reps == 1 and plan.bright_reps == 0 and plan.order == "sync-rows"
    assert plan.row_tail == ROW_TAIL == b"\x00\x00"
    assert plan.fps == 60.32
    assert plan.sync.byte36 == 0x05 and plan.sync.level == level_byte(0.1) == 25


def test_sync_layout_the_s2_sender_cards():
    p = sync_bytes(127, 189)
    assert p[:12] == DST_MAC + SRC_MAC and p[12:14] == b"\x01\x00" and ETH_FRAME == 0x0100
    assert p[COUNTER_OFFSET] == 189 and COUNTER_OFFSET == 14
    assert p[16:19] == b"\xff\xff\xff" and p[26] == 0x01 and p[31:33] == b"\x01\x3c"
    assert p[LEVEL_OFFSET] == 127 and LEVEL_OFFSET == 35 and p[36] == 0x05 and p[38:41] == bytes([127] * 3)
    fixed = {12, 13, 14, 16, 17, 18, 26, 31, 32, 35, 36, 38, 39, 40}
    assert all(p[i] == 0 for i in range(12, len(p)) if i not in fixed)
    assert sync_bytes(127, 256)[COUNTER_OFFSET] == 0 and sync_bytes(127, 511)[COUNTER_OFFSET] == 255


def test_rows_are_the_winning_runs_byte_for_byte():
    bars = send.bars(128)                                   # 64 rows of 128 * 3 bytes
    ours = [row_packets(y, np.frombuffer(bars[y], np.uint8).reshape(128, 3))[0] for y in range(64)]
    assert ours == send.row_packets(bars, tail=send.plan_from(WINNING).row_tail)
    assert ours != send.row_packets(bars)                    # the old tail 08 88 is gone
    assert all(p[19:21] == b"\x00\x00" for p in ours)


def test_level_byte_is_dark_for_nan_zero_and_negative_and_capped_at_255():
    assert level_byte(math.nan) == 0 and level_byte(0.0) == 0 and level_byte(-0.5) == 0
    assert level_byte(0.4) == 102 and level_byte(1.0) == 255 and level_byte(1.7) == 255


def test_frame_packet_is_the_sync_with_the_level_byte():
    fp = frame_packet(0.5)
    assert fp == sync_bytes(127, 0) and len(fp) == 1036
    assert frame_packet(0.5, 7) == sync_bytes(127, 7)
    assert fp[35] == 127 and fp[36] == 0x05 and fp[38:41] == bytes([127, 127, 127])


def test_nan_or_negative_brightness_fails_dark_in_the_s2_format():
    for level in (math.nan, 0.0, -0.5):
        p = frame_packet(level, 3)
        assert p[35] == 0 and p[38:41] == b"\x00\x00\x00"
        assert p == s2_sync(0, 3)                            # dark, and still the S2's format
    assert frame_packet(1.7)[35] == 255


def test_row_packets_chunk_512_pixels_into_two():
    pixels = np.zeros((512, 3), np.uint8)
    pixels[0] = (255, 0, 0)
    pixels[256] = (0, 0, 255)
    pk = row_packets(5, pixels)
    assert len(pk) == 2
    assert pk[0][:6] == DST_MAC and pk[0][6:12] == SRC_MAC and pk[0][12:14] == b"\x55\x00"
    assert pk[0][14:21] == bytes([5, 0, 0, 1, 0, 0x00, 0x00])          # row 5, offset 0, count 256, tail 00 00
    assert pk[0][21:24] == bytes([255, 0, 0])                          # bytes as given: the sender swaps
    assert pk[1][14:21] == bytes([5, 1, 0, 1, 0, 0x00, 0x00])          # offset 256
    assert pk[1][21:24] == bytes([0, 0, 255])
    assert all(len(p) == ROW_HEADER_LEN + 256 * 3 for p in pk)


def test_row_packets_split_384_pixels_equally():
    pixels = np.zeros((384, 3), np.uint8)
    pixels[192] = (0, 255, 0)
    pk = row_packets(2, pixels)
    assert [len(p) for p in pk] == [ROW_HEADER_LEN + 192 * 3] * 2
    assert pk[1][14:21] == bytes([2, 0, 192, 0, 192, 0x00, 0x00])
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
    assert packets.shape == (height, width // chunk, ROW_HEADER_LEN + chunk * 3)
    assert pixels.shape == (height, width // chunk, chunk * 3)
    pixels[...] = frame.reshape(height, -1, chunk * 3)
    sent = [bytes(p) for p in packets.reshape(-1, packets.shape[-1])]
    assert sent == [p for y in range(height) for p in row_packets(y, frame[y])]
    assert all(p[19:21] == b"\x00\x00" for p in sent)                  # the tail in every chunk
