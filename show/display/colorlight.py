"""Raw Ethernet driver for Colorlight 5A-75B/E receiving cards (Linux only, needs CAP_NET_RAW).

Constants diffed on 2026-09-27 against Falcon Player's src/channeloutput/ColorLight-5a-75.cpp
(master) and H. Kubota's protocol notes (hkubota.wordpress.com, 2022-01-31, updated 2022-09-29).
chubby75 documents the card's hardware, not this protocol. Every packet: destination MAC
11:22:33:44:55:66, source MAC 22:22:33:44:55:66, then a packet-type byte at offset 12 whose
first data byte shares the EtherType field at offset 13.

- 0x01 display frame, 112 bytes, EtherType 0x0107: data[21] brightness, data[22] 0x05,
  data[24..26] brightness for R, G, B (data counted from offset 14).
- 0x0A brightness, 77 bytes, EtherType 0x0A<b>: then b, b, 0xFF, zeros.
- 0x55 row data, EtherType 0x5500 | row >> 8: row & 0xFF, pixel offset (2 bytes), pixel count
  (2 bytes), 0x08, 0x88, then pixels in RGB order (Falcon Player; Kubota's panel needed BGR).

Falcon Player's loop sends each display frame packet and then the next frame's rows; push()
does the same, so the card shows a pushed frame when the next push starts. Verify the pixel
order with the rgb test pattern on the panel before trusting colours.
"""
from __future__ import annotations

import math
import socket

import numpy as np

DST_MAC = bytes.fromhex("112233445566")
SRC_MAC = bytes.fromhex("222233445566")
ETH_ROW = 0x5500
ETH_FRAME = 0x0107
ETH_BRIGHTNESS = 0x0A00
CHUNK_PIXELS = 256          # pixels per row packet; Falcon Player allows up to 497
ROW_HEADER_LEN = 14 + 7     # Ethernet header plus the 7-byte row header
FRAME_PAYLOAD_LEN = 98
BRIGHTNESS_PAYLOAD_LEN = 63


def _eth(ethertype: int) -> bytes:
    return DST_MAC + SRC_MAC + ethertype.to_bytes(2, "big")


def _level(level: float) -> int:
    return int(max(0.0, min(1.0, level)) * 255)


def _row_header(row: int, offset: int, count: int) -> bytes:
    return _eth(ETH_ROW | (row >> 8)) + bytes([row & 0xFF, offset >> 8, offset & 0xFF,
                                               count >> 8, count & 0xFF, 0x08, 0x88])


def row_packets(row: int, pixels: np.ndarray) -> list[bytes]:
    """Reference encoder for one row of (width, 3) RGB pixels; push() must match it byte for byte."""
    out = []
    for off in range(0, pixels.shape[0], CHUNK_PIXELS):
        chunk = np.ascontiguousarray(pixels[off : off + CHUNK_PIXELS], dtype=np.uint8)
        out.append(_row_header(row, off, chunk.shape[0]) + chunk.tobytes())
    return out


def frame_packet(brightness: float) -> bytes:
    b = _level(brightness)
    payload = bytearray(FRAME_PAYLOAD_LEN)
    payload[21] = b
    payload[22] = 0x05
    payload[24] = payload[25] = payload[26] = b
    return _eth(ETH_FRAME) + bytes(payload)


def brightness_packet(level: float) -> bytes:
    b = _level(level)
    payload = bytearray(BRIGHTNESS_PAYLOAD_LEN)
    payload[0] = payload[1] = b
    payload[2] = 0xFF
    return _eth(ETH_BRIGHTNESS | b) + bytes(payload)


class ColorlightDisplay:
    def __init__(self, width: int, height: int, iface: str, sock=None):
        chunks = math.ceil(width / CHUNK_PIXELS)
        if width % chunks:
            raise ValueError(f"width {width} does not split into {chunks} equal row packets")
        self.width, self.height = width, height
        self._chunk = width // chunks
        # One prebuilt packet per (row, chunk); headers are fixed, push() fills the pixels.
        self._packets = np.zeros((height, chunks, ROW_HEADER_LEN + self._chunk * 3), np.uint8)
        for y in range(height):
            for c in range(chunks):
                header = _row_header(y, c * self._chunk, self._chunk)
                self._packets[y, c, :ROW_HEADER_LEN] = np.frombuffer(header, np.uint8)
        self._pixels = self._packets[:, :, ROW_HEADER_LEN:]
        if sock is None:
            if not hasattr(socket, "AF_PACKET"):
                raise OSError("the colorlight backend needs Linux raw sockets (AF_PACKET); "
                              "use --backend sdl on this machine")
            sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
            sock.bind((iface, 0))
        self.sock = sock
        self.brightness = 1.0

    def set_brightness(self, level: float) -> None:
        self.brightness = level
        self.sock.send(brightness_packet(level))

    def push(self, frame: np.ndarray) -> None:
        if frame.shape != (self.height, self.width, 3):
            raise ValueError(f"frame shape {frame.shape} is not ({self.height}, {self.width}, 3)")
        self.sock.send(frame_packet(self.brightness))   # shows the rows sent by the previous push
        self._pixels[...] = frame.reshape(self.height, -1, self._chunk * 3)
        for packet in self._packets.reshape(-1, self._packets.shape[-1]):
            self.sock.send(packet.data)

    def close(self) -> None:
        self.sock.close()
