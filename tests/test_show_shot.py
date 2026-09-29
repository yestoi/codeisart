import os
import shutil
from pathlib import Path

import pyte
import pyte.modes
import pytest
from PIL import Image

from show.config import Config
from show.font import CELL_H, Font
from tools import show_shot as ss
from tools.arcade_shot import CAP_H, PAD, TITLE_H, git_sha

ROOT = Path(__file__).resolve().parents[1]
PROTOTYPE = "0,0,128,64"     # a crop keeps the sheets small: the tests need the cheap path
CHILD_SECONDS = 0.5


@pytest.fixture(scope="module")
def real_font() -> Font:
    return Font.load(ROOT / "fonts" / "5x7.bin")


def lit(region) -> float:
    return float((region.max(axis=2) > 0).mean())


def test_script_writes_stamped_plain_led_and_distance_sheets(tmp_path):
    stem = tmp_path / "out"
    code = ss.main(["--script", "strip", "--look", "both", "--crop", PROTOTYPE, "--out", str(stem)])
    assert code == 0
    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == ["out-distance.png", "out-led.png", "out-plain.png"]
    for name in names:
        assert Image.open(tmp_path / name).text["git"] == git_sha()


@pytest.mark.parametrize("script", ["strip", "edges"])
def test_every_frame_has_the_strip_lit(script, real_font):
    cfg = Config()
    steps = ss.SCRIPTS[script]()
    frames = ss.frames_from_steps(steps, cfg, real_font)
    assert len(frames) == len(steps)
    for step, (label, frame) in zip(steps, frames):
        assert frame.shape == (cfg.height, cfg.width, 3)
        assert lit(frame[-CELL_H:]) > 0.5, label     # reverse video: mostly lit


def test_fullscreen_script_hides_and_shows_the_strip(real_font):
    cfg = Config()
    steps = ss.SCRIPTS["fullscreen"]()
    assert [s.strip_visible for s in steps][:2] == [False, True]
    assert all(s.full_screen for s in steps[:2])
    frames = ss.frames_from_steps(steps, cfg, real_font)
    hidden, shown = frames[0][1], frames[1][1]
    assert lit(hidden[-CELL_H:]) < 0.5 and lit(hidden[-CELL_H:]) > 0   # program text on row 24
    assert lit(shown[-CELL_H:]) > 0.5                                  # the strip over it
    rows = (cfg.rows - 1) * CELL_H
    assert (hidden[:rows] == shown[:rows]).all()


def test_black_session_is_refused(tmp_path):
    stem = tmp_path / "out"
    assert ss.main(["--command", "true", "--seconds", "0.3", "--look", "plain", "--out", str(stem)]) == 1
    assert list(tmp_path.iterdir()) == []
    assert ss.main(["--command", "true", "--seconds", "0.3", "--look", "plain", "--allow-black",
                    "--crop", PROTOTYPE, "--out", str(stem)]) == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == ["out-distance.png", "out.png"]


def test_command_output_reaches_the_frames(tmp_path, real_font):
    pidfile = tmp_path / "pid"
    command = f"printf hello; echo $$ > {pidfile}; exec sleep 30"
    frames = ss.frames_from_command(command, Config(), real_font, seconds=CHILD_SECONDS, every_ms=100,
                                    cwd=tmp_path)
    rows = (Config().rows - 1) * CELL_H
    assert frames and any(lit(f[:rows]) > 0 for _, f in frames)
    pid = int(pidfile.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_crop_gives_the_prototype_window(tmp_path):
    stem = tmp_path / "out"
    assert ss.main(["--script", "strip", "--look", "plain", "--crop", PROTOTYPE, "--scale", "2",
                    "--cols", "2", "--out", str(stem)]) == 0
    width, height = Image.open(tmp_path / "out.png").size
    n = len(ss.SCRIPTS["strip"]())
    assert width == PAD + 2 * (128 * 2 + PAD)
    assert height == TITLE_H + -(-n // 2) * (64 * 2 + CAP_H + PAD)


@pytest.mark.skipif(shutil.which("cc") is None, reason="needs a C compiler")
def test_cc_script_compiles_and_runs():
    screen = pyte.Screen(80, 23)
    screen.set_mode(pyte.modes.LNM)
    stream = pyte.ByteStream(screen)
    for step in ss.SCRIPTS["cc"]():
        stream.feed(step.data)
    text = "\n".join(screen.display)
    assert "warning" in text
    assert "result 42" in text
