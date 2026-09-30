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
