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
  A row wider than CHUNK_PIXELS is split into equal packets.

Falcon Player's loop sends each display frame packet and then the next frame's rows; push()
does the same, so the card shows a pushed frame when the next push starts. Verify the pixel
order with the rgb test pattern on the panel before trusting colours.

Brightness. The display starts at SAFE_BRIGHTNESS (0.4, the power-supply cap of both the arcade
and the show daemon configs) unless make_display passes the configured level, so a push before
set_brightness never runs the wall at 255. Falcon Player sends the 0x0A packet with every frame
(twice on firmware 13 and later); this driver sends it on set_brightness and again every
BRIGHTNESS_EVERY pushes, between the display frame packet and the rows, so a card that browns out
and restarts is back at the cap within 0.1 s at 30 Hz. The display frame packet carries the level
on every push as well. A level that is NaN or not above 0 is sent as 0: it fails dark, never bright.
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
CHUNK_PIXELS = 256          # most pixels per row packet; Falcon Player allows up to 497
ROW_HEADER_LEN = 14 + 7     # Ethernet header plus the 7-byte row header
FRAME_PAYLOAD_LEN = 98
BRIGHTNESS_PAYLOAD_LEN = 63
SAFE_BRIGHTNESS = 0.4       # the level before set_brightness: arcade.toml's brightness, show.toml's cap
BRIGHTNESS_EVERY = 3        # pushes between brightness packets: 0.1 s at 30 Hz


def _eth(ethertype: int) -> bytes:
    return DST_MAC + SRC_MAC + ethertype.to_bytes(2, "big")


def _level(level: float) -> int:
    if not level > 0.0:   # NaN, zero or negative: dark
        return 0
    return int(min(1.0, level) * 255)


def _row_header(row: int, offset: int, count: int) -> bytes:
    return _eth(ETH_ROW | (row >> 8)) + bytes([row & 0xFF, offset >> 8, offset & 0xFF,
                                               count >> 8, count & 0xFF, 0x08, 0x88])


def _chunk_pixels(width: int) -> int:
    """Pixels per row packet: the row split into the fewest equal packets of at most CHUNK_PIXELS."""
    chunks = math.ceil(width / CHUNK_PIXELS) if width > 0 else 0
    if chunks == 0 or width % chunks:
        raise ValueError(f"width {width} does not split into {chunks} equal row packets")
    return width // chunks


def row_packets(row: int, pixels: np.ndarray) -> list[bytes]:
    """Reference encoder for one row of (width, 3) RGB pixels; push() must match it byte for byte."""
    chunk = _chunk_pixels(pixels.shape[0])
    out = []
    for off in range(0, pixels.shape[0], chunk):
        data = np.ascontiguousarray(pixels[off : off + chunk], dtype=np.uint8)
        out.append(_row_header(row, off, chunk) + data.tobytes())
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
    def __init__(self, width: int, height: int, iface: str, sock=None, brightness: float = SAFE_BRIGHTNESS):
        self._chunk = _chunk_pixels(width)
        chunks = width // self._chunk
        self.width, self.height = width, height
        # One prebuilt packet per (row, chunk); headers are fixed, push() fills the pixels.
        self._packets = np.zeros((height, chunks, ROW_HEADER_LEN + self._chunk * 3), np.uint8)
        for y in range(height):
            for c in range(chunks):
                header = _row_header(y, c * self._chunk, self._chunk)
                self._packets[y, c, :ROW_HEADER_LEN] = np.frombuffer(header, np.uint8)
        self._pixels = self._packets[:, :, ROW_HEADER_LEN:]
        if sock is None:
            sock = _open_raw_socket(iface)
        self.sock = sock
        self.brightness = brightness
        self._since_brightness = 0   # pushes since the last brightness packet

    def set_brightness(self, level: float) -> None:
        self.brightness = level
        self.sock.send(brightness_packet(level))
        self._since_brightness = 0

    def push(self, frame: np.ndarray) -> None:
        if frame.shape != (self.height, self.width, 3):
            raise ValueError(f"frame shape {frame.shape} is not ({self.height}, {self.width}, 3)")
        if frame.dtype != np.uint8:
            raise ValueError(f"frame dtype {frame.dtype} is not uint8; convert before push")
        self.sock.send(frame_packet(self.brightness))   # shows the rows sent by the previous push
        self._since_brightness += 1
        if self._since_brightness >= BRIGHTNESS_EVERY:
            self.sock.send(brightness_packet(self.brightness))
            self._since_brightness = 0
        self._pixels[...] = frame.reshape(self.height, -1, self._chunk * 3)
        for packet in self._packets.reshape(-1, self._packets.shape[-1]):
            self.sock.send(packet.data)

    def close(self) -> None:
        self.sock.close()


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
        sock.bind((iface, 0))
    except OSError as e:
        sock.close()
        raise OSError(e.errno, f"cannot bind a raw socket to {iface}: {e.strerror or e}") from e
    return sock
