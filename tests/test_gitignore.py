import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def ignored(path: str) -> bool:
    """git check-ignore on a path name; the path need not exist. The user's global excludes are left out."""
    run = subprocess.run(["git", "-c", "core.excludesFile=/dev/null", "check-ignore", "-q", "--no-index", path],
                         cwd=ROOT)
    assert run.returncode in (0, 1), f"git check-ignore failed for {path}"
    return run.returncode == 0


@pytest.mark.parametrize("path", ["models/pose_landmarker_lite.task", "data/calibration.json", "shots/paint.png"])
def test_top_level_runtime_dirs_are_ignored(path):
    assert ignored(path)


@pytest.mark.parametrize("path", ["tests/arcade/fixtures/data/walk.jsonl.gz", "tools/models/notes.md",
                                  "docs/superpowers/workflow/evidence/it02/shots/sheet.png"])
def test_nested_dirs_with_the_same_names_are_tracked(path):
    assert not ignored(path)
