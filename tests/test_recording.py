import json

import pytest

from show.recording import CastError, CastPlayer, CastWriter

HEADER = {"version": 2, "width": 80, "height": 23}


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def test_writer_produces_v2_cast(tmp_path):
    clock = Clock()
    w = CastWriter(tmp_path / "x.cast", 80, 23, clock)
    clock.t += 0.5
    w.write(b"hi\n")
    clock.t += 0.25
    w.write(b"\xff")          # invalid utf-8 must not raise
    w.close()
    lines = (tmp_path / "x.cast").read_text().splitlines()
    header = json.loads(lines[0])
    assert header["version"] == 2 and header["width"] == 80 and header["height"] == 23
    assert json.loads(lines[1]) == [0.5, "o", "hi\n"]
    assert json.loads(lines[2])[0] == 0.75


def test_player_replays_with_timing_and_gap_compression(tmp_path):
    p = tmp_path / "x.cast"
    p.write_text(
        json.dumps(HEADER) + "\n"
        + json.dumps([0.0, "o", "a"]) + "\n"
        + "\n"
        + json.dumps([1.0, "o", "b"]) + "\n"
        + json.dumps([1.5, "i", "ignored"]) + "\n"
        + json.dumps([31.0, "o", "c"]) + "\n"
    )
    player = CastPlayer(p, max_gap=2.0)
    assert player.duration == 3.0            # 30 s pause compressed to 2 s
    player.start(10.0)
    assert player.tick(10.0) == b"a"
    assert player.tick(10.5) == b""
    assert player.tick(11.0) == b"b"
    assert not player.done
    assert player.tick(13.0) == b"c"
    assert player.done


def test_negative_gap_is_clamped_to_zero(tmp_path):
    p = tmp_path / "x.cast"
    p.write_text(
        json.dumps(HEADER) + "\n"
        + json.dumps([2.0, "o", "a"]) + "\n"
        + json.dumps([1.0, "o", "b"]) + "\n"
    )
    player = CastPlayer(p)
    assert [t for t, _ in player.events] == [2.0, 2.0]
    assert player.duration == 2.0


def test_empty_cast_is_done_immediately(tmp_path):
    p = tmp_path / "x.cast"
    p.write_text(json.dumps(HEADER) + "\n")
    player = CastPlayer(p)
    player.start(0.0)
    assert player.tick(0.0) == b"" and player.done and player.duration == 0.0


def test_a_character_split_across_writes_survives(tmp_path):
    raw = "é".encode()
    assert len(raw) == 2
    w = CastWriter(tmp_path / "x.cast", 80, 23)
    w.write(raw[:1])
    w.write(raw[1:])
    w.close()
    text = "".join(json.loads(line)[2]
                   for line in (tmp_path / "x.cast").read_text().splitlines()[1:])
    assert text == "é"
    player = CastPlayer(tmp_path / "x.cast")
    player.start(0.0)
    assert player.tick(1000.0).decode() == "é"


def test_round_trip_through_writer_and_player(tmp_path):
    clock = Clock()
    w = CastWriter(tmp_path / "x.cast", 80, 23, clock)
    w.write(b"one ")
    clock.t += 0.5
    w.write(b"two ")
    clock.t += 30.0
    w.write(b"three")
    w.close()
    w.close()                                # idempotent
    player = CastPlayer(tmp_path / "x.cast", max_gap=2.0)
    assert player.duration == 2.5
    player.start(0.0)
    assert player.tick(0.0) == b"one "
    assert player.tick(0.5) == b"two "
    assert not player.done
    assert player.tick(2.5) == b"three"
    assert player.done


def test_writer_is_a_context_manager(tmp_path):
    with CastWriter(tmp_path / "x.cast", 80, 23) as w:
        w.write(b"x")
    assert len((tmp_path / "x.cast").read_text().splitlines()) == 2


@pytest.mark.parametrize("content", [
    "not json\n",
    "",
    "[1, 2]\n",                                       # header not an object
    json.dumps(HEADER) + "\nnot json\n",
    json.dumps(HEADER) + "\n" + json.dumps({"a": 1}) + "\n",   # event not a list
    json.dumps(HEADER) + "\n" + json.dumps([1.0, "o"]) + "\n",  # too short
    json.dumps({"version": 2}) + "\n",                # no geometry
])
def test_malformed_cast_raises_cast_error(tmp_path, content):
    p = tmp_path / "x.cast"
    p.write_text(content)
    with pytest.raises(CastError):
        CastPlayer(p)


def test_missing_or_binary_file_raises_cast_error(tmp_path):
    with pytest.raises(CastError):
        CastPlayer(tmp_path / "absent.cast")
    p = tmp_path / "b.cast"
    p.write_bytes(b"\xff\xfe\x00\x80")
    with pytest.raises(CastError):
        CastPlayer(p)


def test_player_exposes_the_header_geometry(tmp_path):
    p = tmp_path / "x.cast"
    p.write_text(json.dumps({"version": 2, "width": 80, "height": 23}) + "\n")
    player = CastPlayer(p)
    assert (player.columns, player.rows) == (80, 23)
