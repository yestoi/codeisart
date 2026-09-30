"""The packets of tools/sender_spike/send.py, without a socket and without the wall."""
import importlib.util
import os
import pathlib
import sys

import pytest

from tools.sender_spike import send

ROOT = pathlib.Path(__file__).resolve().parents[2]
CAPTURE = pathlib.Path("/Users/trey/dev/codeisart-sender-spike-refs/pcaps/s2/S2 Sender.pcapng")

# The S2's sync as captured (Falcon Player issue 1849), bytes 0 to 40; the rest of its 1036 bytes is zero.
# Byte 14 is the frame counter: 0xbd in the capture's first sync.
S2_SYNC_HEAD = bytes.fromhex(
    "112233445566" "222233445566" "01" "00" "bd" "00" "ffffff" "00000000000000" "01" "00000000" "013c"
    "0000" "ff" "00" "00" "ffffff")


def old_sender():
    spec = importlib.util.spec_from_file_location(
        "cl_fpp_test", ROOT / "docs/superpowers/workflow/evidence/hardware/cl_fpp_test.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def changed(a, b):
    """Offsets where two packets of one length differ."""
    assert len(a) == len(b)
    return [i for i in range(len(a)) if a[i] != b[i]]


# --- the default is the test sender's, byte for byte

def test_default_sync_is_the_test_senders():
    assert send.sync_packet(send.SyncSpec(), 0) == old_sender().sync(25)


def test_default_sync_does_not_change_with_the_frame_number():
    assert send.sync_packet(send.SyncSpec(), 7) == old_sender().sync(25)


def test_default_brightness_packet_is_the_test_senders():
    assert send.brightness_packet(25) == old_sender().bright(25)


def test_default_rows_are_the_test_senders():
    old = old_sender()
    assert send.row_packets(send.bars(128)) == old.rows(old.bars(128))


def test_black_rows_are_the_test_senders():
    old = old_sender()
    assert send.row_packets(send.black()) == old.rows([bytes(128 * 3)] * 64)


# --- each field changes the bytes it names and no others

BASE = send.sync_packet(send.SyncSpec(), 0)


@pytest.mark.parametrize("field, value, offsets", [
    ("source_type", 0x00, [13]),
    ("bytes16", b"\xff\xff\xff", [16, 17, 18]),
    ("byte26", 0x01, [26]),
    ("declared_rate", b"\x01\x3c", [31, 32]),
    ("declared_rate", b"\x01\x1e", [31, 32]),
    ("level", 0xFF, [35, 38, 39, 40]),
    ("byte36", 0x00, [36]),
])
def test_a_sync_field_changes_only_its_bytes(field, value, offsets):
    packet = send.sync_packet(send.SyncSpec(**{field: value}), 0)
    assert changed(BASE, packet) == offsets


def test_the_counter_changes_only_byte_14():
    spec = send.SyncSpec(counter=True)
    assert send.sync_packet(spec, 0) == BASE
    assert changed(BASE, send.sync_packet(spec, 5)) == [14]
    assert send.sync_packet(spec, 5)[14] == 5


def test_the_counter_wraps_at_256():
    spec = send.SyncSpec(counter=True)
    assert send.sync_packet(spec, 255)[14] == 255
    assert send.sync_packet(spec, 256)[14] == 0
    assert send.sync_packet(spec, 257)[14] == 1


def test_the_counter_can_start_anywhere():
    assert send.sync_packet(send.SyncSpec(counter=True, counter_start=189), 0)[14] == 189
    assert send.sync_packet(send.SyncSpec(counter=True, counter_start=189), 100)[14] == (189 + 100) % 256


def test_mark37_sets_byte_37_in_every_nth_sync_only():
    spec = send.SyncSpec(mark37_every=241)
    assert send.sync_packet(spec, 0) == BASE
    assert send.sync_packet(spec, 240) == BASE
    assert changed(BASE, send.sync_packet(spec, 241)) == [37]
    assert send.sync_packet(spec, 241)[37] == 1
    assert send.sync_packet(spec, 242) == BASE
    assert send.sync_packet(spec, 482)[37] == 1


def test_sync_length_pads_with_zeros_and_changes_nothing_else():
    long = send.sync_packet(send.SyncSpec(length=1036), 0)
    assert len(long) == 1036
    assert long[:112] == BASE
    assert not any(long[112:])


def test_row_tail_changes_only_bytes_19_and_20():
    base = send.row_packets(send.bars(128))
    s2 = send.row_packets(send.bars(128), tail=b"\x00\x00")
    assert len(s2) == len(base) == 64
    for a, b in zip(base, s2):
        assert changed(a, b) == [19, 20]
        assert b[19:21] == b"\x00\x00"


def test_a_row_packet_is_405_bytes_and_names_its_row():
    packets = send.row_packets(send.bars(128))
    assert [len(p) for p in packets] == [405] * 64
    assert [p[14] for p in packets] == list(range(64))
    assert all(p[12] == 0x55 and p[13] == 0 for p in packets)


# --- the S2's sync

def test_s2_sync_is_the_captures_byte_for_byte():
    packet = send.sync_packet(send.S2_SYNC, 0)
    assert packet[:41] == S2_SYNC_HEAD
    assert len(packet) == 1036
    assert not any(packet[41:])


def test_s2_sync_differs_between_frames_in_the_counter_only():
    assert changed(send.sync_packet(send.S2_SYNC, 0), send.sync_packet(send.S2_SYNC, 1)) == [14]


def test_s2_header_in_a_short_sync_is_the_captures_first_112_bytes():
    packet = send.sync_packet(send.S2_HEADER, 0)
    assert len(packet) == 112
    assert packet[:41] == S2_SYNC_HEAD
    assert not any(packet[41:])


@pytest.mark.skipif(not CAPTURE.exists(), reason="the capture is outside git")
def test_s2_sync_against_the_capture_file():
    sys.path.insert(0, str(ROOT / "tools/sender_spike"))
    import pcapng
    syncs = [b for ts, b, orig in pcapng.read(str(CAPTURE)) if b[12] == 0x01]
    import dataclasses
    assert len(syncs) == 818
    plain = [s for s in syncs if s[37] == 0]
    assert len(plain) == 815
    for s in plain:
        assert send.sync_packet(dataclasses.replace(send.S2_SYNC, counter_start=s[14]), 0) == s
    marked = [s for s in syncs if s[37] == 1]
    assert len(marked) == 3
    for s in marked:                                       # frame 1 of a spec that marks every sync
        spec = dataclasses.replace(send.S2_SYNC, counter_start=(s[14] - 1) % 256, mark37_every=1)
        assert send.sync_packet(spec, 1) == s


def test_s2_rows_against_the_capture_header():
    # the S2's row header, bytes 12 to 20, for row 5 of a 128-pixel row
    packet = send.row_packets(send.bars(25), tail=b"\x00\x00")[5]
    assert packet[:21] == bytes.fromhex("112233445566" "222233445566" "5500" "05" "0000" "0080" "0000")


# --- brightness packet

def test_brightness_packet_carries_the_level_three_times():
    p = send.brightness_packet(25)
    assert len(p) == 77
    assert p[12] == 0x0A and p[13] == 25 and p[14] == 25 and p[15] == 25 and p[16] == 0xFF
    assert not any(p[17:])


# --- pictures

def test_bars_are_four_columns_of_32_pixels():
    rows = send.bars(128)
    assert len(rows) == 64 and all(len(r) == 384 for r in rows)
    row = rows[0]
    assert row[0:3] == bytes([128, 0, 0]) and row[32 * 3:32 * 3 + 3] == bytes([0, 128, 0])
    assert row[64 * 3:64 * 3 + 3] == bytes([0, 0, 128]) and row[96 * 3:96 * 3 + 3] == bytes([128, 128, 128])


def test_no_picture_holds_a_value_above_its_level():
    for kind in send.PICTURES:
        for frame in (0, 1, 59, 600):
            rows = send.picture(kind, 25, frame, 60.0)
            assert len(rows) == 64 and all(len(r) == 384 for r in rows)
            assert max(max(r) for r in rows) == 25


def test_the_scroll_moves_slowly():
    # 8 pixels a second: no pixel changes more than once in 4 s, so nothing strobes
    first = send.picture("scroll", 25, 0, 60.0)
    assert send.picture("scroll", 25, 1, 60.0) == first
    assert send.picture("scroll", 25, 60, 60.0) != first
    one_second = send.picture("scroll", 25, 60, 60.0)
    assert one_second[0][8 * 3:] == first[0][:-8 * 3]


def test_bars_do_not_move():
    assert send.picture("bars", 128, 0, 60.0) == send.picture("bars", 128, 500, 60.0) == send.bars(128)


def test_the_scroll_speed_is_a_flag():
    # 2026-09-29 at the wall: "Lets have more movement." A bar is 32 pixels: at 32 a second the picture
    # shifts a bar's width each second, and no pixel changes colour faster than once a second
    slow = send.picture("scroll", 25, 60, 60.0, speed=8)
    fast = send.picture("scroll", 25, 60, 60.0, speed=32)
    first = send.picture("scroll", 25, 0, 60.0, speed=32)
    assert slow == send.picture("scroll", 25, 60, 60.0)
    assert fast[0][32 * 3:] == first[0][:-32 * 3]
    assert send.plan_from(["--picture", "scroll", "--scroll", "32"]).scroll == 32
    assert send.plan_from([]).scroll == 8


def test_the_scroll_is_never_a_strobe():
    import pytest
    with pytest.raises(ValueError, match="64"):
        send.plan_from(["--picture", "scroll", "--scroll", "65"])
    with pytest.raises(ValueError, match="64"):
        send.plan_from(["--picture", "scroll", "--scroll", "0"])
