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
    assert cfg.size == (128, 64)
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


@pytest.mark.parametrize("line,field", [("apl_cap_day = 0", "apl_cap_day"), ("apl_cap_day = 5", "apl_cap_day"),
                                        ("apl_cap_night = -0.1", "apl_cap_night"),
                                        ("apl_cap_night = nan", "apl_cap_night"), ("fps = 0", "fps"),
                                        ("fps = -3", "fps"), ("camera_fps = 0", "camera_fps"), ("gamma = 0", "gamma"),
                                        ("gamma = nan", "gamma"), ("gamma = inf", "gamma"),
                                        ("sdl_scale = 0", "sdl_scale"),
                                        ("night_lux = -1", "night_lux"), ("dwell_seconds = nan", "dwell_seconds")])
def test_rejects_out_of_range_values(tmp_path, line, field):
    with pytest.raises(ValueError, match=field):
        load_config(write(tmp_path, line))


@pytest.mark.parametrize("field", [f.name for f in dataclasses.fields(ArcadeConfig) if f.name.endswith("_seconds")])
def test_every_seconds_field_rejects_negative(tmp_path, field):
    with pytest.raises(ValueError, match=field):
        load_config(write(tmp_path, f"{field} = -1.0"))


def test_range_edges_accepted(tmp_path):
    cfg = load_config(write(tmp_path, "apl_cap_day = 1.0\napl_cap_night = 1\ndwell_seconds = 0\nsdl_scale = 1\n"
                                      "night_lux = 0"))
    assert (cfg.apl_cap_day, cfg.apl_cap_night, cfg.dwell_seconds, cfg.sdl_scale, cfg.night_lux) == (1.0, 1.0, 0.0, 1, 0.0)


def test_layout_name():
    assert ArcadeConfig().layout == "128x64"
    assert ArcadeConfig(width=64, height=64).layout == "64x64"


def test_default_file_in_repo_lists_every_field_with_its_default():
    keys = set(tomllib.loads(REPO_TOML.read_text()))
    assert keys == {f.name for f in dataclasses.fields(ArcadeConfig)}
    assert load_config(REPO_TOML) == ArcadeConfig()


def test_distance_look_needs_sdl_scale_4(tmp_path):
    # C20: at sdl_scale under 4 the distance look's eye blur rounds away (look.distance_sigma), so the preview
    # would look sharper than the wall seen from 5 m.
    for scale in (1, 3):
        with pytest.raises(ValueError, match="sdl_scale"):
            load_config(write(tmp_path, f'look = "distance"\nsdl_scale = {scale}'))
    assert load_config(write(tmp_path, 'look = "distance"\nsdl_scale = 4')).sdl_scale == 4
    assert load_config(write(tmp_path, 'look = "plain"\nsdl_scale = 1')).sdl_scale == 1


@pytest.mark.parametrize("value", [0.22, 22.0, 0.5, 2.3])
def test_gamma_outside_1_to_2_2_is_refused(tmp_path, value):
    # C50: the governor models the wall's light by this gamma; the show's is bound the same (1.0 to 2.2).
    with pytest.raises(ValueError, match="gamma"):
        load_config(write(tmp_path, f"gamma = {value}"))


def test_gamma_1_and_2_2_are_taken(tmp_path):
    assert load_config(write(tmp_path, "gamma = 1.0")).gamma == 1.0
    assert load_config(write(tmp_path, "gamma = 2.2")).gamma == 2.2


def test_the_shipped_arcade_configs_are_in_the_gamma_bound():
    root = Path(__file__).resolve().parents[2]
    for name in ("arcade.toml", "arcade.mac.toml", "arcade.pi.toml"):
        assert 1.0 <= load_config(root / name).gamma <= 2.2, name


def test_capture_defaults_to_opencv_and_takes_picamera2(tmp_path):
    assert ArcadeConfig().capture == "opencv"
    assert load_config(write(tmp_path, 'capture = "picamera2"')).capture == "picamera2"


def test_capture_rejects_another_value(tmp_path):
    with pytest.raises(ValueError, match="capture"):
        load_config(write(tmp_path, 'capture = "webcam"'))


def test_the_pi_config_reads_pose_from_the_sensor():
    cfg = load_config(Path(__file__).resolve().parents[2] / "arcade.pi.toml")
    assert (cfg.backend, cfg.iface, cfg.capture, cfg.camera, cfg.camera_fps, cfg.gamma) == \
        ("colorlight", "eth0", "picamera2", "imx500", 30, 1.0)   # 30: posenet's rate on the sensor (Q182)
    assert cfg.size == (128, 64) and cfg.allow_record is False


def test_the_pi_config_says_the_card_applies_gamma():
    # The wall, 2026-10-02: the checker matched the RIGHT patch of wall_pattern.py gamma, so the card applies gamma.
    cfg = load_config(Path(__file__).resolve().parents[2] / "arcade.pi.toml")
    assert cfg.gamma == 1.0
