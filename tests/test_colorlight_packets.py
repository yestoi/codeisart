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
    assert packets.shape == (height, width // chunk, ROW_HEADER_LEN + chunk * 3)
    assert pixels.shape == (height, width // chunk, chunk * 3)
    pixels[...] = frame.reshape(height, -1, chunk * 3)
    sent = [bytes(p) for p in packets.reshape(-1, packets.shape[-1])]
    assert sent == [p for y in range(height) for p in row_packets(y, frame[y])]
