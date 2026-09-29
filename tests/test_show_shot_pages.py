"""show_shot's sheets in pages, an explicit --cols honoured, the session's flash numbers (it13 T-shot)."""
import re
import shutil

import numpy as np
import pytest
from PIL import Image

from arcade.flash import BUDGET
from show.config import Config
from tools import show_shot as ss
from tools.flash_meter import FlashMeter

FAST = dict(typewriter_cps=5000, min_build_seconds=0.2, dwell=0.5)


def test_pages_keep_every_cell_under_the_height():
    frames = [(f"f{k}", np.full((192, 512, 3), k + 1, np.uint8)) for k in range(30)]
    got = ss.pages(frames, "plain", 4, "title", 2.2, 1)
    assert len(got) > 1 and all(page.height <= ss.PAGE_MAX_H for page in got)
    cell = 192 * 4 + ss.CAP_H + ss.PAD
    assert sum(round((page.height - ss.TITLE_H) / cell) for page in got) == 30       # every cell, none twice
    for k, page in enumerate(got):          # in order: the first cell's pixel of each page steps up the ramp
        first = page.getpixel((ss.PAD + 2, ss.TITLE_H + ss.CAP_H + 2))
        assert first != (0, 0, 0), k
    lit = [page.getpixel((ss.PAD + 2, ss.TITLE_H + ss.CAP_H + 2))[0] for page in got]
    assert lit == sorted(lit) and len(set(lit)) == len(lit)


def test_a_long_command_writes_numbered_pages(tmp_path):
    stem = tmp_path / "out"
    assert ss.main(["--command", "seq 1 50; sleep 1", "--seconds", "0.3", "--every-ms", "50", "--look", "plain",
                    "--cols", "1", "--out", str(stem)]) == 0
    names = sorted(p.name for p in tmp_path.iterdir())
    plain = [n for n in names if re.fullmatch(r"out-p\d+\.png", n)]
    distance = [n for n in names if re.fullmatch(r"out-distance-p\d+\.png", n)]
    assert len(plain) > 1 and len(distance) > 1, names
    assert "out.png" not in names and "out-distance.png" not in names
    for n in plain + distance:
        assert Image.open(tmp_path / n).height <= ss.PAGE_MAX_H


def test_cols_is_honoured_or_refused(tmp_path, capsys):
    ok = tmp_path / "ok"
    assert ss.main(["--command", "seq 1 5", "--seconds", "0.1", "--every-ms", "20", "--look", "plain", "--cols", "3",
                    "--scale", "1", "--out", str(ok)]) == 0
    width = Image.open(tmp_path / "ok.png").width
    assert width == ss.PAD + 3 * (512 + ss.PAD)                        # three columns, as asked
    no = tmp_path / "no"
    with pytest.raises(SystemExit) as gone:
        ss.main(["--command", "seq 1 5", "--seconds", "0.1", "--look", "plain", "--cols", "6", "--scale", "4",
                 "--out", str(no)])
    assert gone.value.code == 2
    assert "4" in capsys.readouterr().err                              # the columns that fit
    assert not [p for p in tmp_path.iterdir() if p.name.startswith("no")]


@pytest.mark.skipif(shutil.which("cc") is None, reason="needs a C compiler")
def test_the_strobe_session_labels_its_flash_numbers():
    cfg = Config(**FAST)
    meter = FlashMeter(cfg.fps, cfg.gamma)
    frames, strips, held = ss.frames_from_session("strobe", cfg, seconds=0.9, every_ms=100, presses=[(0.1, 1)],
                                                  meter=meter)
    assert frames and meter.frames > 0
    for label, _ in frames:
        assert re.search(r" area \d\.\d{4} sq \d+$", label), label
    assert meter.squares_max <= BUDGET
