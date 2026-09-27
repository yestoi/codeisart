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
    assert cfg.fps == 20 and cfg.volume == 0.6 and cfg.pump_bytes == 4096
    assert not hasattr(cfg, "matrix_multiplexing")


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
