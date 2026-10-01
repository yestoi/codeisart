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
                                  "docs/superpowers/workflow/evidence/it02/shots/sheet.txt"])
def test_nested_dirs_with_the_same_names_are_tracked(path):
    assert not ignored(path)


@pytest.mark.parametrize("path", ["docs/superpowers/workflow/evidence/it19/it19-pong.png",
                                  "docs/superpowers/workflow/evidence/it19/dodge/dodge-128x64-canonical.gif",
                                  "docs/superpowers/workflow/evidence/hardware/40-panel.jpg"])
def test_evidence_images_stay_local(path):
    """Owner decision Q98: the loop's evidence images are not published; the evidence's text is."""
    assert ignored(path)


@pytest.mark.parametrize("path", ["docs/superpowers/workflow/evidence/it19/README.md",
                                  "docs/superpowers/workflow/evidence/it19/dodge/feel.json",
                                  "docs/superpowers/workflow/evidence/it19/pytest-idle.txt",
                                  "docs/superpowers/plans/sketch.png", "vision.png"])
def test_evidence_text_and_other_images_are_tracked(path):
    assert not ignored(path)
