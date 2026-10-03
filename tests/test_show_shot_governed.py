import re
import shutil
from pathlib import Path

import pytest

from show.config import load_config
from tests.show_helpers import HELLO_C, write_entry
from tools import show_shot as ss

ROOT = Path(__file__).resolve().parents[1]


def _git_status_entries() -> str:
    import subprocess
    return subprocess.run(["git", "status", "--porcelain", "entries"], cwd=ROOT, capture_output=True,
                          text=True).stdout


@pytest.mark.skipif(shutil.which("cc") is None, reason="needs a C compiler")
def test_governed_entry_session_runs_the_entry_through_the_governor(tmp_path):
    cfg = load_config(ROOT / "show.poc.toml")
    entry_dir = write_entry(tmp_path, "mine", 4, HELLO_C, run_seconds=3.0)
    frames, strips, held = ss.frames_from_session("entry", cfg, seconds=6.0, every_ms=250,
                                                  entry_dir=entry_dir)
    assert frames and len(frames) == len(strips)
    assert all(re.fullmatch(r"\d+\.\ds held \d+ area [\d.]+ sq \d+", label) for label, _ in frames)
    assert "Test Author, 2026" in strips
    assert not any("mine" in s for s in strips)
    assert "station = 4" in (entry_dir / "entry.toml").read_text()      # the source copy is untouched
    assert _git_status_entries() == ""


def test_governed_needs_an_entry(tmp_path):
    with pytest.raises(SystemExit) as exc:
        ss.main(["--governed", "--session", "presses", "--out", str(tmp_path / "out")])
    assert exc.value.code == 2


@pytest.mark.skipif(shutil.which("cc") is None, reason="needs a C compiler")
def test_a_reel_session_plays_the_list_through_the_governor_and_ends_with_the_reel(tmp_path):
    cfg = load_config(ROOT / "show.demo.toml")
    frames, strips, held = ss.frames_from_session("reel", cfg, seconds=60.0, every_ms=250, reel="hello:1")
    assert frames and len(frames) == len(strips)
    assert all(re.fullmatch(r"\d+\.\ds held \d+ area [\d.]+ sq \d+", label) for label, _ in frames)
    assert "THIS IS THE CODE" in strips and "RUNNING" in strips          # the phase strip of show.demo.toml
    last_t = float(frames[-1][0].split("s")[0])
    assert last_t < 30.0                                                  # over when the reel is, not at 60 s
    assert _git_status_entries() == ""


def test_the_reel_option_on_the_command_line(tmp_path, monkeypatch):
    seen = {}

    def fake(name, cfg, seconds, every_ms, meter=None, entry_dir=None, reel=None):
        seen.update(name=name, reel=reel, seconds=seconds)
        return [("0.0s held 0 area 0.0000 sq 0", ss.np.zeros((cfg.height, cfg.width, 3), ss.np.uint8))], [""], 0
    monkeypatch.setattr(ss, "frames_from_session", fake)
    assert ss.main(["--reel", "hello:1,hello:2", "--config", "show.demo.toml", "--out", str(tmp_path / "out"),
                    "--allow-black"]) == 0
    assert seen == {"name": "reel", "reel": "hello:1,hello:2", "seconds": ss.SESSION_SECONDS}
