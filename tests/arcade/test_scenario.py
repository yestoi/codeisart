"""Scenario files (spec 6.3) and the replay sources: core plan Task 12 as its amendment, C21 and Review Focus 4
change it (it20 S2)."""
import base64
import dataclasses
import gzip
import json
import logging
import struct

import numpy as np
import pytest

from arcade.calibration import Calibration
from arcade.headless import NullLobby
from arcade.runner import Runner
from arcade.sensed import MOTION_GRID, Audio, Blob, Body, Keypoint, Sensed
from arcade.sources.actors import TICK, Person, claps, degrade, motion_rect, moving_blob, scene
from arcade.sources.replay import ReplayAudio, ReplayCamera, ReplayStream, open_replay
from arcade.sources.scenario import (RawRecord, ScenarioReader, ScenarioWriter, decode, decode_raw, encode, encode_raw,
                                     make_header, wav_samples)
from show.display.fake import FakeDisplay
from tests.arcade.helpers import FakeClock, make_cfg, run


def sample():
    """One scene tick with a body, a coloured blob, a clap and a lit motion rectangle, its grid at 16x8."""
    s = next(iter(scene(persons=[Person(0.3)], blobs=[moving_blob(0, 0, 1, 1, 1, color=(1, 2, 3))],
                        motion=[motion_rect(0.25, 0.25, 0.5, 0.75, 0.0, 1.0)], audio=claps([0.0]), ticks=1)))
    return s.with_motion((16, 8))


def write_lines(path, lines):
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        fh.write("".join(line + "\n" for line in lines))


def warnings_in(caplog):
    return [r for r in caplog.records if r.levelno == logging.WARNING and r.name == "arcade"]


def record(path, frames, header=None):
    with ScenarioWriter(path, header or make_header()) as w:
        for s in frames:
            w.write(s)
    return path


def wall_runner(font, clock):
    return Runner(make_cfg((128, 64)), FakeDisplay(), font, NullLobby(), [], clock=clock, sleep=clock.sleep)


def test_round_trip():
    s = sample()
    line = encode(s)
    assert "\n" not in line and json.loads(line)["t"] == 0.0
    d = decode(line)
    assert d.t == s.t and len(d.bodies) == 1 and d.bodies[0].id == 0
    assert d.bodies[0].nose.x == round(s.bodies[0].nose.x, 4)
    assert d.blobs[0].color == (1, 2, 3)
    assert s.motion.any() and d.motion.shape == (64, 128)            # the file's fixed grid
    assert np.array_equal(d.with_motion((16, 8)).motion, s.motion)   # resampled back, every lit cell kept
    assert d.audio == s.audio and d.audio.clap and d.audio.onset
    assert decode(encode(Sensed(1.5))).motion.shape == (0, 0)       # no grid is the empty grid, never None


def test_reader_skips_bad_lines(tmp_path, caplog):
    p = tmp_path / "s.jsonl.gz"
    good = encode(Sensed(0.0))
    write_lines(p, [json.dumps(make_header()), good, "", "{not json", encode(Sensed(0.5))[:-8], '{"t": "x"}', good])
    r = ScenarioReader(p)
    with caplog.at_level(logging.WARNING, logger="arcade"):
        got = list(r)
    assert len(got) == 2 and r.skipped == 3
    assert len(warnings_in(caplog)) == 3                   # one warning a bad line, and nothing raised


def test_a_cut_off_recording_replays_what_it_holds(tmp_path, caplog):
    """A recording stopped by a power cut has no gzip end: the lines before the cut are read, then one warning."""
    p = tmp_path / "cut.jsonl.gz"
    frames = list(scene(persons=[Person(0.4)], ticks=300))
    with ScenarioWriter(p, make_header()) as w:
        for s in frames:
            w.write(s)
    whole = p.read_bytes()
    p.write_bytes(whole[: len(whole) * 6 // 10])
    r = ScenarioReader(p)
    with caplog.at_level(logging.WARNING, logger="arcade"):
        got = list(r)
    assert 0 < len(got) < len(frames) and r.skipped == 1 and len(warnings_in(caplog)) == 1


def test_a_file_without_a_header_is_refused(tmp_path):
    p = tmp_path / "bare.jsonl.gz"
    write_lines(p, [encode(Sensed(0.0))])
    with pytest.raises(ValueError, match="header"):
        ScenarioReader(p)
    plain = tmp_path / "plain.jsonl.gz"
    plain.write_text(json.dumps(make_header()) + "\n")
    with pytest.raises(ValueError, match="gzip"):
        ScenarioReader(plain)
    with pytest.raises(ValueError, match="type"):
        make_header(type="video")


def test_gz_round_trip_with_header(tmp_path):
    p = tmp_path / "walk.jsonl.gz"
    header = make_header(fps=30, script="walkup", cues=[(0.3, "WALK IN")], created="2026-10-02T00:00:00+00:00",
                         git="b4f1e9b")
    frames = list(scene(persons=[Person(0.05, id=1).walk(0.45, 1.5, at=0.3)], ticks=60))
    with ScenarioWriter(p, header) as w:
        for s in frames:
            w.write(s)
    assert p.read_bytes()[:2] == b"\x1f\x8b"               # gzip
    r = ScenarioReader(p)
    assert r.header == {"kind": "header", "version": 1, "type": "sensed", "fps": 30, "grid": [128, 64],
                        "script": "walkup", "cues": [[0.3, "WALK IN"]], "created": "2026-10-02T00:00:00+00:00",
                        "git": "b4f1e9b"}
    got = list(r)
    assert r.skipped == 0 and len(got) == len(frames)
    for a, b in zip(frames, got):
        assert b.t == round(a.t, 4) and [x.id for x in b.bodies] == [x.id for x in a.bodies]
        for x, y in zip(a.bodies, b.bodies):
            assert all(abs(k.x - j.x) <= 5e-5 and abs(k.y - j.y) <= 5e-5 for k, j in zip(x.keypoints, y.keypoints))
            assert (y.in_zone, y.zone_x) == (x.in_zone, pytest.approx(x.zone_x, abs=1e-3))


def test_header_cues_readable(tmp_path):
    p = tmp_path / "cues.jsonl.gz"
    cues = [(1.0, "RAISE RIGHT HAND"), (3.5, "HOLD"), (6.0, "SWEEP LEFT")]
    with ScenarioWriter(p, make_header(script="door-point", cues=cues)):
        pass
    assert ScenarioReader(p).cues == tuple(cues)
    with gzip.open(p, "rt") as fh:                         # plain JSON on the first line, readable without arcade
        first = json.loads(fh.readline())
    assert first["kind"] == "header" and first["script"] == "door-point"
    assert first["cues"] == [[1.0, "RAISE RIGHT HAND"], [3.5, "HOLD"], [6.0, "SWEEP LEFT"]]


def test_sensed_line_has_only_schema_fields():
    s = sample()
    body = s.bodies[0]
    rich = dataclasses.replace(s, camera_seq=9, player=body, player2=body, present=True)
    obj = json.loads(encode(rich))
    assert set(obj) == {"t", "camera_t", "camera_fresh", "bodies", "blobs", "motion", "audio"}
    assert set(obj["bodies"][0]) == {"id", "box", "keypoints", "vx", "vy", "scale", "seen_ago", "measured",
                                     "torso_per_width"}
    assert set(obj["blobs"][0]) == {"x", "y", "size", "color", "id", "vx", "vy"}
    names = lambda cls: {f.name for f in dataclasses.fields(cls)}   # noqa: E731
    assert set(obj["audio"]) == names(Audio)
    # every key is a field of the record it encodes: no image, no sound, nothing the runner sets
    assert set(obj) <= names(Sensed) and set(obj["bodies"][0]) <= names(Body) and set(obj["blobs"][0]) <= names(Blob)
    assert isinstance(obj["motion"], str) and all(len(kp) == 3 for kp in obj["bodies"][0]["keypoints"])


def test_blob_ids_and_velocities_round_trip():
    tracked = Blob(0.4, 0.5, 0.03, (255, 0, 0), id=7, vx=0.25, vy=-0.125)
    outside = Blob(0.05, 0.05, 0.02, (0, 255, 0), False)   # untracked (-1), outside the default zone
    d = decode(encode(Sensed(0.0, blobs=(tracked, outside))))
    assert d.blobs == (tracked, outside)
    assert [(b.id, b.vx, b.vy) for b in d.blobs] == [(7, 0.25, -0.125), (-1, 0.0, 0.0)]


def test_decode_places_bodies_with_the_recordings_calibration():
    cal = Calibration(zone=(0.0, 0.1, 0.5, 0.9), min_height=0.3)
    s = next(iter(scene(persons=[Person(0.4, id=3)], blobs=[moving_blob(0.6, 0.5, 0.6, 0.5, 1)], ticks=1,
                        calibration=cal)))
    line = encode(s)
    recorded, placed = s.bodies[0], decode(line, cal).bodies[0]
    assert placed.in_zone is recorded.in_zone is True
    assert placed.zone_x == pytest.approx(recorded.zone_x, abs=1e-3) == pytest.approx(0.8, abs=1e-3)
    assert placed.zone_y == pytest.approx(recorded.zone_y, abs=1e-3)
    assert decode(line, cal).blobs[0].in_zone is False     # x 0.6 is outside this zone
    default = decode(line)                                 # no calibration: the default zone, 0.2 to 0.8
    assert default.bodies[0].zone_x == pytest.approx((0.4 - 0.2) / 0.6, abs=1e-3)
    assert default.blobs[0].in_zone is True


def raw_sample():
    """One raw capture: a detection, a 160x120 grey frame and 0.1 s of 16 kHz sound (values exact at 4 places)."""
    kps = tuple(Keypoint(j / 20, (j + 1) / 20, 0.5 + j / 40) for j in range(17))
    frame = (np.arange(120 * 160) % 251).astype(np.uint8).reshape(120, 160)
    samples = (np.sin(np.arange(1600) / 7) * 12000).astype(np.int16)
    return RawRecord(12.25, detections=(((0.25, 0.2, 0.75, 0.95), kps),), frame=frame, samples=samples)


def test_raw_record_round_trip(tmp_path):
    r = raw_sample()
    obj = json.loads(encode_raw(r))
    assert set(obj) == {"t", "detections", "frame", "wav"}
    assert len(base64.b64decode(obj["frame"])) == 160 * 120
    wav = base64.b64decode(obj["wav"])
    assert wav[:4] == b"RIFF" and wav[8:16] == b"WAVEfmt " and wav[36:40] == b"data"
    channels, rate, bits = (struct.unpack_from("<H", wav, 22)[0], struct.unpack_from("<I", wav, 24)[0],
                            struct.unpack_from("<H", wav, 34)[0])
    assert (channels, rate, bits) == (1, 16000, 16)
    assert struct.unpack_from("<I", wav, 40)[0] // 2 == 1600 == len(wav_samples(wav)[1])   # its length, from its header
    d = decode_raw(encode_raw(r))
    assert d.t == 12.25 and d.detections == r.detections
    p = tmp_path / "raw.jsonl.gz"
    with ScenarioWriter(p, make_header("raw", fps=10)) as w:
        w.write(r)
    reader = ScenarioReader(p)
    (got,) = list(reader)
    assert reader.header["type"] == "raw" and reader.skipped == 0
    assert got.detections == r.detections and got.t == 12.25
    assert got.frame.dtype == np.uint8 and got.frame.shape == (120, 160) and np.array_equal(got.frame, r.frame)
    assert got.samples.dtype == np.int16 and np.array_equal(got.samples, r.samples)
    with ScenarioWriter(tmp_path / "s.jsonl.gz", make_header()) as w, pytest.raises(TypeError):
        w.write(r)                                         # a sensed file takes Sensed records only


def test_raw_file_is_not_replayed_yet(tmp_path):
    """Raw replay runs FrameFeatures and BodyTracker (iteration 21): until then open_replay refuses a raw file."""
    p = tmp_path / "raw.jsonl.gz"
    with ScenarioWriter(p, make_header("raw", fps=10)) as w:
        w.write(raw_sample())
    with pytest.raises(ValueError, match="raw"):
        open_replay(p)


def test_writer_and_open_replay(tmp_path):
    p = record(tmp_path / "rec.jsonl.gz", scene(persons=[Person()], ticks=3))
    clock = FakeClock()
    cam, aud = open_replay(p, clock=clock)
    assert cam.available and aud.available
    capture_t, bodies, blobs, motion = cam.latest()
    assert capture_t == clock.now and len(bodies) == 1 and blobs == () and motion.shape == (64, 128)
    assert aud.latest() == (clock.now, Audio())
    clock.sleep(1 / 30)
    cam.latest()
    clock.sleep(1 / 30)
    third = cam.latest()
    assert cam.stream.finished is False and third[0] == clock.now    # each record a new capture, stamped as read
    clock.sleep(1 / 30)
    capture4, bodies4, _, _ = cam.latest()
    assert cam.stream.finished is True and len(bodies4) == 1          # the last record is held,
    assert capture4 == third[0] and not cam.available and not aud.available   # as an old capture, the source done
    cam.close()


def test_replay_of_empty_stream_yields_empty_sensed():
    clock = FakeClock()
    cam = ReplayCamera(ReplayStream(iter([]), clock))
    capture_t, bodies, blobs, motion = cam.latest()
    assert (capture_t, bodies, blobs, motion.shape) == (clock.now, (), (), (0, 0))
    assert ReplayAudio(cam.stream).latest() == (clock.now, Audio())


def test_motion_packed_on_128x64_resampled_to_wall(tmp_path, font5x7):
    s = sample()                                           # its grid at 16x8
    packed = base64.b64decode(json.loads(encode(s))["motion"])
    assert len(packed) == 128 * 64 // 8
    on_grid = np.unpackbits(np.frombuffer(packed, np.uint8)).astype(bool).reshape(64, 128)
    assert np.array_equal(on_grid, s.with_motion(MOTION_GRID).motion)
    clock = FakeClock()
    got = wall_runner(font5x7, clock).sense(*open_replay(record(tmp_path / "m.jsonl.gz", [s]), clock=clock))
    assert got.camera_fresh and [b.id for b in got.bodies] == [0]
    assert got.motion.shape == (64, 128) and np.array_equal(got.motion, on_grid)   # the wall's grid, every cell kept


def test_open_replay_takes_the_recordings_calibration(tmp_path):
    cal = Calibration(zone=(0.0, 0.1, 0.5, 0.9), min_height=0.3)
    p = record(tmp_path / "cal.jsonl.gz", scene(persons=[Person(0.4, id=3)], ticks=1, calibration=cal))
    (body,) = open_replay(p, cal, clock=FakeClock())[0].latest()[1]
    assert body.in_zone and body.zone_x == pytest.approx(0.8, abs=1e-3)


def test_replay_holds_a_capture_as_the_recording_did(tmp_path, font5x7):
    """A 10 fps camera's capture is held over three ticks. Replay stamps a new capture only where the recording
    had one, as old as it was, so the runner sees the recording's fresh ticks and camera ages, not 30 captures a
    second; before the recording's first capture there is no camera."""
    frames = list(degrade(scene(persons=[Person(0.5, id=1)], ticks=30)))
    clock = FakeClock()
    runner = wall_runner(font5x7, clock)
    cam, aud = open_replay(record(tmp_path / "deg.jsonl.gz", frames), clock=clock)
    seen = []
    for _ in frames:
        seen.append(runner.sense(cam, aud))
        clock.sleep(1 / 30)
    assert [s.camera_fresh for s in seen] == [f.camera_fresh for f in frames]
    assert [[b.id for b in s.bodies] for s in seen] == [[b.id for b in f.bodies] for f in frames]
    for s, f in zip(seen, frames):
        if f.camera_seq:                                   # runner.t stays 0 here: camera_t is minus the age
            assert -s.camera_t == pytest.approx(f.t - f.camera_t, abs=1e-3)
    assert sum(f.camera_fresh for f in frames) == 9 and seen[-1].audio == frames[-1].audio


# ----- hostile lines (it20 B3): a line that will not decode is skipped, and a non-finite number makes a bad line -----

NESTED = "[" * 200000 + "]" * 200000                       # json.loads raises RecursionError on it (about 400 KB)
NON_FINITE = ("NaN", "Infinity", "-Infinity", "1e999")      # json.loads reads each as a float; 1e999 is inf
KP = ("bodies", 0, "keypoints", 5)
FLOAT_FIELDS = ([("bodies", 0, "box", i) for i in range(4)] + [KP + (i,) for i in range(3)]
                + [("bodies", 0, k) for k in ("vx", "vy", "scale", "seen_ago", "torso_per_width")]
                + [("blobs", 0, k) for k in ("x", "y", "size", "vx", "vy")]
                + [("audio", k) for k in ("level", "level_smooth", "peak", "voice_db", "floor_db", "voice", "bpm")]
                + [("t",), ("camera_t",)])


def good_lines():
    """The reviewer's probe's good lines: a standing body at 0.5, three ticks."""
    return [encode(s) for s in scene(persons=[Person(0.5, id=1)], ticks=3)]


def with_token(line, path, token):
    """line with the value at path (keys and indexes into its JSON) written as the bare token, NaN or 1e999."""
    obj = json.loads(line)
    *outer, last = path
    target = obj
    for k in outer:
        target = target[k]
    target[last] = "@@"
    return json.dumps(obj).replace('"@@"', token)


def read_all(path, caplog):
    r = ScenarioReader(path)
    with caplog.at_level(logging.WARNING, logger="arcade"):
        got = list(r)
    return got, r.skipped, len(warnings_in(caplog))


def test_a_deeply_nested_line_is_skipped(tmp_path, caplog):
    good = good_lines()
    p = tmp_path / "nested.jsonl.gz"
    write_lines(p, [json.dumps(make_header()), good[0], NESTED, good[1], good[2]])
    got, skipped, warned = read_all(p, caplog)
    assert [s.t for s in got] == [decode(line).t for line in good]   # the lines after it are read too
    assert skipped == 1 and warned == 1


def test_replay_reads_past_a_deeply_nested_line(tmp_path):
    """latest() once a tick, as the runner calls it: no exception, every good record a capture in turn, then the
    stream finishes and holds the last one."""
    good = good_lines()
    ts = [decode(line).t for line in good]
    p = tmp_path / "nested.jsonl.gz"
    write_lines(p, [json.dumps(make_header()), good[0], NESTED, good[1], good[2]])
    clock = FakeClock()
    cam, _ = open_replay(p, clock=clock)
    seen = []
    for _ in range(4):
        capture_t, bodies, _, _ = cam.latest()
        seen.append((cam.stream.current.t, capture_t == clock.now, len(bodies), cam.stream.finished))
        clock.sleep(1 / 30)
    cam.close()
    assert seen == [(t, True, 1, False) for t in ts] + [(ts[-1], False, 1, True)]


def test_a_header_that_cannot_be_parsed_is_refused(tmp_path):
    p = tmp_path / "nested-header.jsonl.gz"
    write_lines(p, [NESTED, encode(Sensed(0.0))])
    with pytest.raises(ValueError, match="header"):
        ScenarioReader(p)
    with pytest.raises(ValueError, match="header"):
        open_replay(p)


def infinity_box(line):
    """The probe's line: a standing body's keypoints in the box [0, 0, Infinity, Infinity]."""
    obj = json.loads(line)
    obj["bodies"][0]["box"] = [0, 0, float("inf"), float("inf")]
    return json.dumps(obj)


def test_a_non_finite_box_is_skipped(tmp_path, caplog):
    line = infinity_box(good_lines()[2])
    assert '"box": [0, 0, Infinity, Infinity]' in line
    p = tmp_path / "infbox.jsonl.gz"
    write_lines(p, [json.dumps(make_header()), line])
    got, skipped, warned = read_all(p, caplog)
    assert got == [] and skipped == 1 and warned == 1
    assert open_replay(p, clock=FakeClock())[0].latest()[1] == ()   # the empty stream's record: no body reaches a game


def test_a_non_finite_box_never_reaches_a_game(tmp_path, font5x7):
    """The probe's run: a standing player whose box is Infinity for 3 s, then good lines, replayed into Jump.
    Today's reader let the box through, the body became the player and Jump's draw raised in the runner's tick."""
    from arcade.games.jump import Jump

    zone = Calibration().zone
    lines, bad = [], 0
    for s in scene(persons=[Person(zone[0] + 0.5 * (zone[2] - zone[0]), id=1)], ticks=round(4 / TICK)):
        line = encode(s)
        if s.bodies and s.t < 3.0:
            line, bad = infinity_box(line), bad + 1
        lines.append(line)
    p = tmp_path / "infbox-run.jsonl.gz"
    write_lines(p, [json.dumps(make_header())] + lines)
    reader = ScenarioReader(p)
    _, _, runner = run(Jump, iter(reader), (128, 64), font5x7, seed=1, strict=False)
    st = runner.state()
    assert st["crashes"] == {} and st["hidden"] == [] and st["game"] == "jump"
    assert bad > 60 and reader.skipped == bad


def test_a_non_finite_blob_value_is_skipped(tmp_path, caplog):
    good = encode(sample())
    p = tmp_path / "blob.jsonl.gz"
    write_lines(p, [json.dumps(make_header()), with_token(good, ("blobs", 0, "size"), "Infinity"), good])
    got, skipped, warned = read_all(p, caplog)
    assert [len(s.blobs) for s in got] == [1] and skipped == 1 and warned == 1


def test_a_non_finite_audio_value_is_skipped(tmp_path, caplog):
    good = encode(sample())
    p = tmp_path / "audio.jsonl.gz"
    write_lines(p, [json.dumps(make_header()), with_token(good, ("audio", "level"), "NaN"), good])
    got, skipped, warned = read_all(p, caplog)
    assert [s.audio for s in got] == [decode(good).audio] and skipped == 1 and warned == 1


@pytest.mark.parametrize("path", FLOAT_FIELDS, ids=lambda path: ".".join(map(str, path)))
def test_every_float_field_refuses_a_non_finite_number(tmp_path, caplog, path):
    """Each of NaN, Infinity, -Infinity and 1e999 in the field makes its line a skipped one; the good line after
    them is read."""
    good = encode(sample())
    p = tmp_path / "field.jsonl.gz"
    write_lines(p, [json.dumps(make_header())] + [with_token(good, path, tok) for tok in NON_FINITE] + [good])
    got, skipped, warned = read_all(p, caplog)
    assert [s.t for s in got] == [decode(good).t] and skipped == len(NON_FINITE) == warned
