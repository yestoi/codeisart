import logging

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
