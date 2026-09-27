import dataclasses
import tomllib
from pathlib import Path

import pytest

from arcade.config import ArcadeConfig, load_config

REPO_TOML = Path(__file__).resolve().parents[2] / "arcade.toml"


def write(tmp_path, text):
    p = tmp_path / "arcade.toml"
    p.write_text(text + "\n")
    return p


def test_defaults_when_file_missing(tmp_path):
    cfg = load_config(tmp_path / "nope.toml")
    assert cfg.size == (128, 32)
    assert cfg.backend == "sdl" and cfg.sdl_scale == 8 and cfg.iface == "eth0"
    assert (cfg.ddp_host, cfg.ddp_port) == ("127.0.0.1", 4048)
    assert cfg.camera == "mediapipe" and cfg.camera_index == 0 and cfg.camera_fps == 10
    assert cfg.audio == "sounddevice" and cfg.audio_device == "" and cfg.scenario == ""
    assert cfg.mirror is True and cfg.brightness == 0.4 and cfg.gamma == 2.2 and cfg.look == "led"
    assert (cfg.apl_cap_day, cfg.apl_cap_night, cfg.night_lux) == (0.12, 0.06, 5.0)
    assert (cfg.night_start, cfg.night_end) == ("01:00", "06:00")
    assert cfg.dwell_seconds == 1.2
    assert (cfg.present_on_seconds, cfg.present_off_seconds, cfg.player_lost_seconds) == (1.0, 3.0, 0.5)
    assert (cfg.leave_seconds, cfg.inactive_seconds, cfg.max_session_seconds) == (8.0, 30.0, 180.0)
    assert cfg.exit_seconds == 3.0 and cfg.allow_record is False
    assert cfg.data_dir == Path("data") and cfg.font_path == Path("fonts/5x7.bin") and cfg.fps == 30
    assert not hasattr(cfg, "idle_seconds")


def test_values_from_file(tmp_path):
    cfg = load_config(write(tmp_path, 'width = 64\nheight = 64\nbackend = "colorlight"\niface = "eth1"\n'
                                      'camera = "replay"\nscenario = "s.jsonl"\ndata_dir = "d"\nleave_seconds = 10'))
    assert cfg.size == (64, 64) and cfg.layout == "64x64"
    assert cfg.backend == "colorlight" and cfg.iface == "eth1"
    assert cfg.camera == "replay" and cfg.scenario == "s.jsonl"
    assert cfg.data_dir == Path("d")
    assert cfg.leave_seconds == 10.0 and isinstance(cfg.leave_seconds, float)


@pytest.mark.parametrize("line,field", [('backend = "hologram"', "backend"), ('audio = "tape"', "audio"),
                                        ("brightness = 1.5", "brightness"), ("brightness = 0", "brightness"),
                                        ("brightnes = 0.2", "brightnes"), ("width = 4", "width")])
def test_bad_values_rejected(tmp_path, line, field):
    with pytest.raises(ValueError, match=field):
        load_config(write(tmp_path, line))


@pytest.mark.parametrize("line,field", [('backend = "matrix"', "backend"), ('camera = "kinect"', "camera"),
                                        ('look = "crt"', "look")])
def test_rejects_bad_enum_values(tmp_path, line, field):
    with pytest.raises(ValueError, match=field):
        load_config(write(tmp_path, line))


@pytest.mark.parametrize("line", ['night_start = "25:00"', 'night_end = "6pm"', 'night_start = "12:60"'])
def test_rejects_bad_night_time(tmp_path, line):
    with pytest.raises(ValueError, match="HH:MM"):
        load_config(write(tmp_path, line))


@pytest.mark.parametrize("line,field", [('brightness = "0.4"', "brightness"), ("width = 12.5", "width"),
                                        ('mirror = "yes"', "mirror"), ("width = true", "width")])
def test_wrong_type_rejected(tmp_path, line, field):
    with pytest.raises(ValueError, match=field):
        load_config(write(tmp_path, line))


def test_layout_name():
    assert ArcadeConfig().layout == "128x32"
    assert ArcadeConfig(width=64, height=64).layout == "64x64"


def test_default_file_in_repo_lists_every_field_with_its_default():
    keys = set(tomllib.loads(REPO_TOML.read_text()))
    assert keys == {f.name for f in dataclasses.fields(ArcadeConfig)}
    assert load_config(REPO_TOML) == ArcadeConfig()
