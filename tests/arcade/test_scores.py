import json
import logging
import math
from datetime import datetime

import numpy as np
import pytest

import arcade.scores as scores_module
from arcade.scores import REASONS, GameScores, Scores, SessionLog, night_of


class Clock:
    """A settable local clock."""

    def __init__(self, when: str):
        self.now = datetime.fromisoformat(when)

    def __call__(self) -> datetime:
        return self.now

    def set(self, when: str) -> None:
        self.now = datetime.fromisoformat(when)


def test_scores_record_and_persist(tmp_path):
    p = tmp_path / "d" / "scores.json"
    clock = Clock("2026-11-11T21:00")
    s = Scores(p, clock)
    assert s.best("dodge", "128x32") is None
    assert s.record("dodge", "128x32", 0.4) is True
    assert s.record("dodge", "128x32", 0.3) is False
    assert s.record("dodge", "128x32", 0.4) is False                 # a tie is not a new best
    assert s.record("dodge", "128x32", 0.5) is True
    assert s.best("dodge", "128x32") == 0.5
    assert Scores(p, clock).best("dodge", "128x32") == 0.5
    assert json.loads(p.read_text()) == {"dodge": {"128x32": {"best": 0.5, "when": "2026-11-11T21:00:00"}}}
    assert not (tmp_path / "d" / "scores.json.tmp").exists()


def test_scores_write_fsyncs_then_renames(tmp_path, monkeypatch):
    calls = []
    real_fsync, real_replace = scores_module.os.fsync, scores_module.os.replace
    p = tmp_path / "scores.json"

    def fsync(fd):
        calls.append(("fsync", (tmp_path / "scores.json.tmp").read_text()))
        real_fsync(fd)

    def replace(src, dst):
        calls.append(("replace", str(src), str(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(scores_module.os, "fsync", fsync)
    monkeypatch.setattr(scores_module.os, "replace", replace)
    Scores(p, Clock("2026-11-11T21:00")).record("pong", "64x64", 7)
    assert [c[0] for c in calls] == ["fsync", "replace"]
    assert json.loads(calls[0][1])["pong"]["64x64"]["best"] == 7.0   # the whole file was on disk before the rename
    assert calls[1][1:] == (str(tmp_path / "scores.json.tmp"), str(p))
    calls.clear()
    monkeypatch.setattr(scores_module.os, "fsync", lambda fd: calls.append(("fsync", log.read_text())))
    log = tmp_path / "sessions.jsonl"
    SessionLog(log).append("pong", "64x64", datetime(2026, 11, 11, 21), 30.0, 1, 7, "done")
    assert len(calls) == 1 and json.loads(calls[0][1])["score"] == 7.0  # the line was written before the fsync


def test_scores_survive_corrupt_file(tmp_path, caplog):
    p = tmp_path / "scores.json"
    clock = Clock("2026-11-11T21:00")
    for text in ("{not json", "[1, 2]", '{"x": 5}'):
        p.write_text(text)
        with caplog.at_level(logging.WARNING, logger="arcade"):
            s = Scores(p, clock)
        assert s.best("x", "128x32") is None and caplog.records, text
        caplog.clear()
    good = {"best": 3.0, "when": "2026-11-11T20:00:00"}
    p.write_text(json.dumps({"x": {"128x32": good, "64x64": {"best": "high", "when": "x"}},
                             "y": {"128x32": {"best": math.inf, "when": "2026-11-11T20:00:00"},
                                   "64x64": {"best": 2.0, "when": "last night"}}},
                            allow_nan=True))
    with caplog.at_level(logging.WARNING, logger="arcade"):
        s = Scores(p, clock)
    assert [r.getMessage().split()[1] for r in caplog.records] == ["3"]   # "ignoring 3 malformed entries"
    assert s.best("x", "128x32") == 3.0 and s.best("x", "64x64") is None and s.best("y", "128x32") is None
    assert s.best("y", "64x64") is None and s.last_night("y", "64x64") is None
    assert s.record("x", "64x64", 1.0)
    p.write_text(json.dumps({"x": {"128x32": {"best": 3, "when": "2026-11-11T20:00:00"},
                                   "64x64": {"best": 1.0, "when": 5}}}))
    with caplog.at_level(logging.WARNING, logger="arcade"):
        s = Scores(p, clock)                                         # a "when" that is not a string is dropped
    assert s.best("x", "64x64") is None and type(s.best("x", "128x32")) is float


def test_scores_in_memory_never_writes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def refuse(*args, **kwargs):
        raise AssertionError("Scores(None) and SessionLog(None) must not touch the disk")

    monkeypatch.setattr(scores_module.os, "replace", refuse)
    monkeypatch.setattr(scores_module.os, "fsync", refuse)
    s = Scores(None, Clock("2026-11-11T21:00"))
    assert s.record("tug", "128x32", 12) and s.best("tug", "128x32") == 12.0
    log = SessionLog(None)
    log.append("tug", "128x32", datetime(2026, 11, 11, 21), 60.0, 2, 12, "done")
    assert log.records[0]["reason"] == "done"
    assert list(tmp_path.iterdir()) == []


def test_scores_per_layout():
    s = Scores(None, Clock("2026-11-11T21:00"))
    assert s.record("flap", "128x32", 10)
    assert s.record("flap", "64x64", 4)                              # the other layout has its own best
    assert s.best("flap", "128x32") == 10.0 and s.best("flap", "64x64") == 4.0 and s.best("pong", "64x64") is None
    view = s.for_game("flap", "64x64")
    assert isinstance(view, GameScores) and view.best() == 4.0
    assert view.record(5) and not view.record(3) and s.best("flap", "64x64") == 5.0
    assert s.best("flap", "128x32") == 10.0


def test_scores_roll_over_at_1600():
    clock = Clock("2026-11-11T22:00")
    s = Scores(None, clock)
    view = s.for_game("swat", "128x32")
    assert view.record(50)
    clock.set("2026-11-12T03:00")                                    # the same night, after midnight
    assert view.best() == 50.0 and not view.record(40) and view.last_night() is None
    clock.set("2026-11-12T15:59:59")
    assert view.best() == 50.0
    clock.set("2026-11-12T16:00")                                    # a new night
    assert view.best() is None and view.last_night() == 50.0
    assert view.record(20) and view.best() == 20.0 and view.last_night() == 50.0
    assert view.record(30) and view.last_night() == 50.0             # a second best tonight keeps last night
    clock.set("2026-11-13T17:00")                                    # two nights on: last night is the 12th's
    assert view.best() is None and view.last_night() == 30.0
    clock.set("2026-11-15T17:00")                                    # nights without a record: none
    assert view.last_night() is None
    assert night_of(datetime(2026, 11, 12, 1)) == night_of(datetime(2026, 11, 11, 16)) == datetime(2026, 11, 11).date()
    assert night_of(datetime(2026, 11, 11, 15, 59)) == datetime(2026, 11, 10).date()


def test_scores_last_night_survives_a_restart(tmp_path):
    p = tmp_path / "scores.json"
    clock = Clock("2026-11-11T23:00")
    Scores(p, clock).record("tug", "128x32", 9)
    clock.set("2026-11-12T20:00")
    Scores(p, clock).record("tug", "128x32", 4)
    s = Scores(p, clock)
    assert s.best("tug", "128x32") == 4.0 and s.last_night("tug", "128x32") == 9.0
    clock.set("2026-11-13T20:00")
    Scores(p, clock).record("tug", "128x32", 5)
    entry = json.loads(p.read_text())["tug"]["128x32"]
    assert entry["previous"] == {"best": 4.0, "when": "2026-11-12T20:00:00"}   # one night back, never nested


def test_scores_margin():
    s = Scores(None, Clock("2026-11-11T21:00"))
    roar = s.for_game("strongman", "128x32")
    assert roar.record(-30.0, margin=10.0)                           # the first of the night needs no margin
    assert not roar.record(-21.0, margin=10.0) and roar.best() == -30.0
    assert roar.record(-20.0, margin=10.0) and roar.best() == -20.0  # exactly 10 dB more is enough
    for bad in (-1.0, math.nan, math.inf, None, np.True_):
        with pytest.raises(ValueError):
            roar.record(0.0, margin=bad)
    assert roar.record(np.float32(-5.0), margin=np.float32(10.0)) and roar.best() == -5.0


def test_scores_take_numpy_numbers(tmp_path):
    # Games compute scores with numpy: Copy Me's match, Strongman's dB, a Tug tally from np.sum.
    p = tmp_path / "scores.json"
    s = Scores(p, Clock("2026-11-11T21:00"))
    assert s.record("tug", "128x32", np.int64(7)) and s.record("copyme", "64x64", np.float32(0.8))
    assert not s.record("tug", "128x32", np.int64(7)) and s.record("tug", "128x32", np.int64(8))
    assert s.best("tug", "128x32") == 8.0 and type(s.best("tug", "128x32")) is float
    assert s.best("copyme", "64x64") == pytest.approx(0.8)
    assert json.loads(p.read_text())["tug"]["128x32"]["best"] == 8.0
    assert not s.record("tug", "128x32", np.float64(np.nan)) and not s.record("tug", "128x32", np.True_)
    log = SessionLog(tmp_path / "sessions.jsonl")
    record = log.append("tug", "128x32", datetime(2026, 11, 11, 21), np.float32(45.5), 2, np.int64(12), "done")
    assert record["duration"] == 45.5 and record["score"] == 12.0
    assert json.loads((tmp_path / "sessions.jsonl").read_text()) == record


def test_scores_ignore_non_finite_values_and_unwritable_files(tmp_path, caplog):
    s = Scores(None, Clock("2026-11-11T21:00"))
    with caplog.at_level(logging.WARNING, logger="arcade"):
        for bad in (math.nan, math.inf, None, True, "12"):
            assert s.record("pong", "128x32", bad) is False
    assert s.best("pong", "128x32") is None and len(caplog.records) == 5
    blocker = tmp_path / "data"
    blocker.write_text("a file where the data directory should be")
    s = Scores(blocker / "scores.json", Clock("2026-11-11T21:00"))
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="arcade"):
        assert s.record("pong", "128x32", 3) is True                 # a failed write never reaches the game
    assert s.best("pong", "128x32") == 3.0 and caplog.records
    log = SessionLog(blocker / "sessions.jsonl")
    log.append("pong", "128x32", datetime(2026, 11, 11, 21), 30.0, 1, 3, "left")


def test_sessions_log_appends_json_line(tmp_path):
    p = tmp_path / "d" / "sessions.jsonl"
    log = SessionLog(p)
    log.append("paint", "64x64", datetime(2026, 11, 11, 21, 5), 45.5, 1, None, "left")
    log.append("pong", "128x32", datetime(2026, 11, 11, 21, 7), math.nan, 2, math.inf, "done")
    lines = p.read_text().splitlines()
    assert [json.loads(line) for line in lines] == [
        {"game": "paint", "layout": "64x64", "start": "2026-11-11T21:05:00", "duration": 45.5, "players": 1,
         "score": None, "reason": "left"},
        {"game": "pong", "layout": "128x32", "start": "2026-11-11T21:07:00", "duration": None, "players": 2,
         "score": None, "reason": "done"},
    ]
    assert log.records == []                                         # kept in memory only without a path
    assert REASONS == ("done", "left", "inactive", "capped", "exit", "crash")


def test_sessions_log_rejects_unknown_reason(tmp_path):
    p = tmp_path / "sessions.jsonl"
    log = SessionLog(p)
    for reason in ("quit", "", None, "DONE"):
        with pytest.raises(ValueError):
            log.append("pong", "128x32", datetime(2026, 11, 11, 21), 10.0, 1, 3, reason)
    with pytest.raises(ValueError):
        log.append("pong", "128x32", "21:00", 10.0, 1, 3, "done")
    assert not p.exists()
    for reason in REASONS:
        log.append("pong", "128x32", datetime(2026, 11, 11, 21), 10.0, 1, 3, reason)
    assert [json.loads(line)["reason"] for line in p.read_text().splitlines()] == list(REASONS)
