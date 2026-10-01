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
