import dataclasses
import json
import logging
import math
import os
import stat

import pytest

from arcade.calibration import Calibration, load_calibration, save_calibration


def test_default_calibration(tmp_path):
    cal = load_calibration(tmp_path)
    assert cal == Calibration()
    assert cal.zone == (0.2, 0.2, 0.8, 0.8)   # the central 60 percent of the frame
    assert cal.min_height == 0.45 and cal.calibrated is False
    assert cal.static_mask == () and cal.baseline_scale == 0.0 and cal.audio_floor_db == -90.0


def test_calibration_round_trip(tmp_path):
    cal = Calibration(zone=(0.1, 0.3, 0.7, 0.95), min_height=0.5, baseline_scale=0.31,
                      static_mask=((0.12, 0.4, 0.02), (0.9, 0.1, 0.05)), audio_floor_db=-62.5, calibrated=True)
    save_calibration(tmp_path / "data", cal)
    assert load_calibration(tmp_path / "data") == cal
    assert [p.name for p in (tmp_path / "data").iterdir()] == ["calibration.json"]   # no temp file left


@pytest.mark.parametrize("text", ["", "{not json", "[]", '{"zone": [0.1, 0.2, 0.3]}',
                                  '{"zone": [0.8, 0.2, 0.2, 0.8], "min_height": 0.4, "baseline_scale": 0,'
                                  ' "static_mask": [], "audio_floor_db": -60, "calibrated": true}'])
def test_corrupt_calibration_falls_back_to_defaults(tmp_path, caplog, text):
    (tmp_path / "calibration.json").write_text(text)
    with caplog.at_level(logging.WARNING, logger="arcade"):
        assert load_calibration(tmp_path) == Calibration()
    assert "calibration.json" in caplog.text


@pytest.mark.parametrize("key,value", [("min_height", -3), ("min_height", 1.5), ("min_height", True),
                                       ("baseline_scale", -1),
                                       ("static_mask", [[5, 5, 0.02]]), ("static_mask", [[0.5, 0.5, -2]]),
                                       ("static_mask", [[0.5, 0.5, 0]]), ("static_mask", [[0.5, 0.5]]),
                                       ("audio_floor_db", math.nan), ("audio_floor_db", 12.0),
                                       ("calibrated", "no"), ("calibrated", 1), ("zone", [0.1, 0.2, 0.9, "0.8"])],
                         ids=["height-negative", "height-over-1", "height-bool", "scale-negative", "light-outside",
                              "radius-negative", "radius-zero", "light-two-values", "floor-nan", "floor-positive",
                              "calibrated-string", "calibrated-int", "zone-string"])
def test_bad_value_falls_back_to_defaults_naming_the_key(tmp_path, caplog, key, value):
    good = Calibration(zone=(0.1, 0.2, 0.9, 0.8), min_height=0.5, calibrated=True)
    (tmp_path / "calibration.json").write_text(json.dumps(dataclasses.asdict(good) | {key: value}))
    with caplog.at_level(logging.WARNING, logger="arcade"):
        assert load_calibration(tmp_path) == Calibration()
    assert key in caplog.text


def test_missing_key_takes_its_default_and_keeps_the_rest(tmp_path, caplog):
    data = dataclasses.asdict(Calibration(zone=(0.1, 0.3, 0.7, 0.95), min_height=0.5, audio_floor_db=-62.5,
                                          calibrated=True))
    del data["audio_floor_db"]
    (tmp_path / "calibration.json").write_text(json.dumps(data))
    with caplog.at_level(logging.WARNING, logger="arcade"):
        cal = load_calibration(tmp_path)
    assert cal == Calibration(zone=(0.1, 0.3, 0.7, 0.95), min_height=0.5, calibrated=True)
    assert cal.audio_floor_db == -90.0 and "audio_floor_db" in caplog.text


def test_unknown_key_is_ignored_with_a_warning(tmp_path, caplog):
    cal = Calibration(zone=(0.1, 0.3, 0.7, 0.95), min_height=0.5, calibrated=True)
    (tmp_path / "calibration.json").write_text(json.dumps(dataclasses.asdict(cal) | {"exposure": 7}))
    with caplog.at_level(logging.WARNING, logger="arcade"):
        assert load_calibration(tmp_path) == cal
    assert "exposure" in caplog.text


def test_save_fsyncs_the_file_then_its_directory(tmp_path, monkeypatch):
    synced = []
    real_fsync = os.fsync

    def spy(fd):
        synced.append(stat.S_ISDIR(os.fstat(fd).st_mode))
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", spy)
    save_calibration(tmp_path, Calibration())
    assert synced == [False, True]   # the bytes, then the rename
