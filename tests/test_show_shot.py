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


def test_poc_config_writes_ink_sheets_at_128x64(tmp_path):
    stem = tmp_path / "poc"
    code = ss.main(["--config", "show.poc.toml", "--command", "printf '%0.s#' $(seq 1 400)",
                    "--seconds", str(CHILD_SECONDS), "--look", "plain", "--out", str(stem)])
    assert code == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == ["poc-distance.png", "poc.png"]


def test_program_black_in_the_ink_view_is_any_lit_dot(real_font):
    cfg = Config(width=128, height=64, view="ink")
    frames = ss.frames_from_steps([ss.Step("blank")], cfg, real_font)
    assert ss._program_black(frames, cfg)
    frames = ss.frames_from_steps([ss.Step("dot", b".")], cfg, real_font)
    assert not ss._program_black(frames, cfg)


# -- the real pipeline and attract mode (it11 T-shot) ---------------------------------------------------------

from dataclasses import replace                                         # noqa: E402

from show.pipeline import Phase                                         # noqa: E402
from tests.show_helpers import HELLO_C, write_entry                     # noqa: E402

PLAY_DEADLINE = 20.0     # a named deadline for one played entry, not a hang guard's guess at its duration


@pytest.fixture
def play_cfg() -> Config:
    return Config(typewriter_cps=5000, dwell=0.2, error_hold=0.2, min_build_seconds=0.2)


def _git_status_entries() -> str:
    import subprocess
    return subprocess.run(["git", "status", "--porcelain", "entries"], cwd=ROOT, capture_output=True,
                          text=True).stdout


@pytest.mark.skipif(shutil.which("cc") is None, reason="needs a C compiler")
def test_entry_mode_plays_the_sample_entry_through_the_pipeline(play_cfg, real_font):
    frames, phases, failure = ss.frames_from_entry(ROOT / "entries" / "hello", play_cfg, real_font,
                                                   seconds=PLAY_DEADLINE, every_ms=500)
    print("phases:", [(p.value if hasattr(p, "value") else p, round(t, 2)) for p, t in phases])
    names = [p.value if hasattr(p, "value") else p for p, _ in phases]
    assert names == [Phase.SOURCE.value, Phase.BUILD.value, Phase.RUN.value, Phase.DWELL.value,
                     Phase.DONE.value]
    assert failure is None
    assert not (frames[0][1] == frames[-1][1]).all()
    assert _git_status_entries() == ""
    assert not (ROOT / "entries" / "hello" / "hello").exists()


@pytest.mark.skipif(shutil.which("cc") is None, reason="needs a C compiler")
def test_entry_mode_with_a_broken_build_replays_the_captured_fallback(tmp_path, play_cfg, real_font):
    d = write_entry(tmp_path, "broken", 1, HELLO_C)
    frames, phases, failure = ss.frames_from_entry(d, play_cfg, real_font, seconds=PLAY_DEADLINE,
                                                   every_ms=200, build="false", capture_first=True)
    names = [p.value if hasattr(p, "value") else p for p, _ in phases]
    print("phases:", [(n, round(t, 2)) for n, (_, t) in zip(names, phases)])
    assert Phase.ERROR_HOLD.value in names and Phase.FALLBACK.value in names
    assert failure is not None and failure.startswith("build failed")
    assert not (d / "fallback.cast").exists()      # the copy held the capture, not the original


def test_attract_mode_scrolls(tmp_path, play_cfg, real_font):
    for i in (1, 2):
        write_entry(tmp_path, f"e{i}", i, HELLO_C * 8)
    frames = ss.frames_from_attract(tmp_path, play_cfg, real_font, seconds=0.6, every_ms=200)
    assert len(frames) >= 3
    assert not (frames[0][1] == frames[-1][1]).all()
    for label, frame in frames:
        assert lit(frame[-CELL_H:]) > 0.5, label
    ink = Config(width=128, height=64, view="ink")
    frames = ss.frames_from_attract(tmp_path, ink, real_font, seconds=0.3, every_ms=150)
    for label, frame in frames:
        assert frame.shape == (64, 128, 3), label
        assert frame[: 64 - CELL_H].max() > 0, label


def test_play_strip_names_the_entry(tmp_path):
    from show.entries import load_entry
    entry = load_entry(write_entry(tmp_path, "abc", 1, HELLO_C))
    assert ss.play_strip(entry) == "NOW: abc by Test Author, 2026, Not A.I. | NEXT: -"


@pytest.mark.skipif(shutil.which("cc") is None, reason="needs a C compiler")
def test_entry_and_attract_modes_write_stamped_sheets(tmp_path):
    src = tmp_path / "src"
    write_entry(src, "one", 1, HELLO_C)
    conf = tmp_path / "fast.toml"
    conf.write_text("typewriter_cps = 5000\ndwell = 0.2\nerror_hold = 0.2\nmin_build_seconds = 0.2\n"
                    "attract_lps = 1000.0\n")
    fast = ["--every-ms", "300", "--seconds", "0.5", "--look", "both", "--config", str(conf)]
    for mode, target in (("--attract", src), ("--entry", src / "one")):
        stem = tmp_path / mode.strip("-") / "sheet"
        assert ss.main([mode, str(target), "--out", str(stem)] + fast) == 0
        names = sorted(p.name for p in stem.parent.iterdir())
        assert names == ["sheet-distance.png", "sheet-led.png", "sheet-plain.png"], names
        for name in names:
            assert Image.open(stem.parent / name).text["git"] == git_sha()
