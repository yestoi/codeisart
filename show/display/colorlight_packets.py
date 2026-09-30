"""The packets of the Colorlight 5A-75B/E protocol: what Colorlight's own S2 sender card puts on the wire, as the
spike sender imitated it and as the wall was clean with on 2026-09-30 (docs/superpowers/reviews/2026-09-30-ghosting/,
00-path-forward.md section 2 and 07-wall-session.md finding 7).

Every packet: destination MAC 11:22:33:44:55:66, source MAC 22:22:33:44:55:66, the packet type at byte 12,
whose first data byte shares the EtherType at byte 13. Offsets count from the start of the Ethernet frame.

- 0x01 the sync ("display frame"), 1036 bytes, EtherType 0x0100 (source type 0x00): a frame counter at 14,
  bytes 16 to 18 ff ff ff, byte 26 01, the declared rate 01 3c at 31 and 32, the level at 35 and 38 to 40,
  byte 36 = 0x05. The card shows the rows it holds when a sync arrives. Byte 36 is the brightness switch:
  at 05 the card obeys the level byte, at 00 (the S2's own) it ignores every level field. One sync a frame, the
  rows right behind it, and no 0x0A brightness packet: fed this at 60.32 frames a second the card draws no
  second picture; our old 112-byte sync at 59 made it copy bright rows a few rows away.
- 0x55 a row, EtherType 0x5500 | row >> 8: row & 0xFF, pixel offset (2 bytes), pixel count (2 bytes), then
  the tail 00 00, then three bytes a pixel in the order the card takes them (BGR on this card, measured
  2026-09-29; the sender swaps, these builders copy bytes as given). A row wider than CHUNK_PIXELS is split
  into equal packets.

tests/test_colorlight_packets.py pins every byte to the spike sender's builders (tools/sender_spike/send.py,
`--s2 --byte36 05`), which are what went on the wire. A level that is NaN or not above 0 is 0: dark, never bright.
The 0x0A brightness packet builders below are kept only until the sender stops importing them.
"""
from __future__ import annotations

import math

import numpy as np

DST_MAC = bytes.fromhex("112233445566")
SRC_MAC = bytes.fromhex("222233445566")
ETH_ROW = 0x5500
ETH_FRAME = 0x0100          # packet type 0x01, source type 0x00 (the S2's; our old sync said 0x07)
ETH_BRIGHTNESS = 0x0A00
CHUNK_PIXELS = 256          # most pixels per row packet; Falcon Player allows up to 497
ROW_HEADER_LEN = 14 + 7     # Ethernet header plus the 7-byte row header
ROW_TAIL = b"\x00\x00"      # bytes 19 and 20 of a row packet (the S2's; the test sender's was 08 88)
SYNC_LEN = 1036             # the S2's sync, as captured
FRAME_PAYLOAD_LEN = SYNC_LEN - 14
BRIGHTNESS_PAYLOAD_LEN = 63
COUNTER_OFFSET = 14         # the frame counter, one byte, wrapping
LEVEL_OFFSET = 35           # the level byte; it is repeated at 38 to 40


def _eth(ethertype: int) -> bytes:
    return DST_MAC + SRC_MAC + ethertype.to_bytes(2, "big")


def level_byte(level: float) -> int:
    """The byte of a level 0 to 1: NaN, zero or negative is 0 (dark), above 1 is 255."""
    if not level > 0.0:
        return 0
    return int(min(1.0, level) * 255)


def _row_header(row: int, offset: int, count: int) -> bytes:
    return _eth(ETH_ROW | (row >> 8)) + bytes([row & 0xFF, offset >> 8, offset & 0xFF,
                                               count >> 8, count & 0xFF]) + ROW_TAIL


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


def sync_bytes(b: int, counter: int = 0) -> bytes:
    """The S2's sync with the level byte b and the frame counter (kept to a byte)."""
    payload = bytearray(FRAME_PAYLOAD_LEN)
    payload[COUNTER_OFFSET - 14] = counter & 0xFF
    payload[16 - 14 : 19 - 14] = b"\xff\xff\xff"
    payload[26 - 14] = 0x01
    payload[31 - 14 : 33 - 14] = b"\x01\x3c"                # the declared rate: 60 Hz
    payload[LEVEL_OFFSET - 14] = b
    payload[36 - 14] = 0x05                                 # the brightness switch: the level is obeyed
    payload[38 - 14] = payload[39 - 14] = payload[40 - 14] = b
    return _eth(ETH_FRAME) + bytes(payload)


def brightness_bytes(b: int) -> bytes:
    """The brightness packet with the level byte b."""
    payload = bytearray(BRIGHTNESS_PAYLOAD_LEN)
    payload[0] = payload[1] = b
    payload[2] = 0xFF
    return _eth(ETH_BRIGHTNESS | b) + bytes(payload)


def frame_packet(brightness: float, counter: int = 0) -> bytes:
    return sync_bytes(level_byte(brightness), counter)


def brightness_packet(level: float) -> bytes:
    return brightness_bytes(level_byte(level))
