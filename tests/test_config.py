from pathlib import Path

import pytest

from show.config import Config, load_config

ROOT = Path(__file__).resolve().parents[1]


def test_defaults_when_file_missing(tmp_path):
    cfg = load_config(tmp_path / "nope.toml")
    assert cfg.backend == "sdl"
    assert (cfg.columns, cfg.rows) == (80, 24)
    assert (cfg.width, cfg.height) == (512, 192)
    assert cfg.phosphor_rgb == (51, 255, 51)
    assert cfg.button_pins == [5, 6, 13, 19, 26]
    assert cfg.lightbox_pins == [17, 22, 23, 24, 27]
    assert cfg.fps == 20 and cfg.volume == 0.6 and cfg.pump_bytes == 4096
    assert not hasattr(cfg, "matrix_multiplexing")
    assert cfg.strip_look == "bright-on-field" and cfg.gamma == 2.2


def test_values_from_file(tmp_path):
    p = tmp_path / "show.toml"
    p.write_text('backend = "ddp"\nbrightness = 0.9\nbrightness_cap = 0.4\nphosphor = "amber"\nentries_dir = "e"\n')
    cfg = load_config(p)
    assert cfg.backend == "ddp"
    assert cfg.effective_brightness == 0.4
    assert cfg.phosphor_rgb == (255, 176, 0)
    assert cfg.entries_dir == Path("e")


def test_unknown_phosphor_rejected(tmp_path):
    p = tmp_path / "show.toml"
    p.write_text('phosphor = "blue"\n')
    with pytest.raises(ValueError):
        load_config(p)


def test_unknown_key_rejected(tmp_path):
    p = tmp_path / "show.toml"
    p.write_text('brightnes = 0.5\n')
    with pytest.raises(ValueError):
        load_config(p)


def test_repo_show_toml_matches_defaults():
    assert load_config(ROOT / "show.toml") == Config()


def test_view_defaults_to_text_and_rejects_others(tmp_path):
    assert Config().view == "text"
    p = tmp_path / "show.toml"
    p.write_text('view = "blocks"\n')
    with pytest.raises(ValueError):
        load_config(p)


def test_repo_poc_toml_is_the_128x64_ink_view():
    cfg = load_config(ROOT / "show.poc.toml")
    assert (cfg.width, cfg.height, cfg.view) == (128, 64, "ink")
    assert (cfg.columns, cfg.rows) == (80, 24)


def test_strip_look_gamma_and_fps_are_checked(tmp_path):
    p = tmp_path / "show.toml"
    for bad in ('strip_look = "stripes"', "gamma = 0", "gamma = -1.0", "gamma = 0.22", "gamma = 22.0",
                "fps = 20.0", "fps = 0", "fps = 1"):
        p.write_text(bad + "\n")
        with pytest.raises(ValueError):
            load_config(p)
    for look in ("reverse", "dim-reverse", "bright-on-field"):
        p.write_text(f'strip_look = "{look}"\n')
        assert load_config(p).strip_look == look
    p.write_text("gamma = 1.0\n")
    assert load_config(p).gamma == 1.0


def test_the_strip_is_off_everywhere_and_must_be_true_or_false(tmp_path):
    assert Config().strip is False                       # Q100: the portraits carry the credit, not the wall
    for name in ("show.toml", "show.poc.toml"):
        assert load_config(ROOT / name).strip is False, name
    p = tmp_path / "show.toml"
    p.write_text("strip = true\n")
    assert load_config(p).strip is True
    for bad in ('strip = "no"', "strip = 0", "strip = 1"):
        p.write_text(bad + "\n")
        with pytest.raises(ValueError):
            load_config(p)


def test_the_default_strip_look_is_the_loop_s_reading_everywhere():
    assert Config().strip_look == "bright-on-field"
    for name in ("show.toml", "show.poc.toml"):
        assert load_config(ROOT / name).strip_look == "bright-on-field", name


# -- the reel (2026-10-03): cards, the hold, the quiet build, the phase strip ----------------------------------------

def test_reel_keys_default_off_and_are_checked(tmp_path):
    cfg = Config()
    assert cfg.card_seconds == 0.0 and cfg.source_hold == 0.0 and cfg.build_quiet is False
    assert cfg.strip_phase is False and cfg.end_card == []
    p = tmp_path / "show.toml"
    p.write_text('card_seconds = 2.5\nsource_hold = 2\nbuild_quiet = true\nstrip_phase = true\n'
                 'end_card = ["CODE IS ART", "A.I. IS NOT"]\n')
    cfg = load_config(p)
    assert cfg.card_seconds == 2.5 and cfg.source_hold == 2 and cfg.build_quiet is True and cfg.strip_phase is True
    assert cfg.end_card == ["CODE IS ART", "A.I. IS NOT"]
    for bad in ("card_seconds = -1", 'card_seconds = "2"', "card_seconds = true", "source_hold = -0.5",
                "build_quiet = 1", 'strip_phase = "yes"', 'end_card = "CODE IS ART"', "end_card = [1, 2]"):
        p.write_text(bad + "\n")
        with pytest.raises(ValueError):
            load_config(p)


def test_the_demo_configs_are_the_reel_on_the_128x64_ink_view():
    for name in ("show.demo.toml", "show.engulf.toml"):
        cfg = load_config(ROOT / name)
        assert (cfg.width, cfg.height, cfg.view) == (128, 64, "ink"), name
        assert cfg.strip is True and cfg.strip_phase is True and cfg.strip_look == "plain", name
        assert cfg.card_seconds > 0 and cfg.source_hold > 0 and cfg.build_quiet is True, name
        assert cfg.end_card and all(len(line) <= 21 for line in cfg.end_card), name
        assert cfg.typewriter_cps == 600 and cfg.effective_brightness <= cfg.brightness_cap, name
