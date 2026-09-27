import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from arcade.main import doctor, main, probe_pose, within

ROOT = Path(__file__).resolve().parents[2]


def fixed(ok, detail="fine"):
    return lambda timeout: (ok, detail)


def boom(timeout):
    raise OSError("device busy")


def test_exit_code_and_report(capsys):
    assert doctor(["camera", "mic"], {"camera": fixed(True), "mic": fixed(True)}) == 0
    assert "UNAVAILABLE" not in capsys.readouterr().out
    assert doctor(["camera", "mic"], {"camera": fixed(True), "mic": fixed(False, "no frames")}) == 1
    out = capsys.readouterr().out
    assert "mic" in out and "UNAVAILABLE" in out and "no frames" in out


def test_raising_probe_counts_as_unavailable(capsys):
    assert doctor(["pose"], {"pose": boom}) == 1
    assert "OSError: device busy" in capsys.readouterr().out


def test_unknown_source_exits_two():
    assert doctor(["radar"], {"camera": fixed(True)}) == 2
    assert main(["doctor", "--require", "radar"]) == 2


def test_every_probe_gets_five_seconds():
    seen = []
    spy = lambda timeout: (seen.append(timeout), (True, ""))[1]
    assert doctor(["camera", "mic"], {"camera": spy, "mic": spy}) == 0 and seen == [5.0, 5.0]


def test_importing_main_loads_no_hardware_module():
    code = "import sys, arcade.main; print(sorted({'cv2', 'mediapipe', 'sounddevice'} & set(sys.modules)))"
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "[]"


@pytest.mark.parametrize("require", ["", " , "])
def test_require_naming_nothing_exits_two(capsys, require):
    assert main(["doctor", "--require", require]) == 2
    assert "names no source" in capsys.readouterr().out
    assert doctor([], {"camera": fixed(True)}) == 2


def test_within_gives_up_at_the_timeout():
    release = threading.Event()
    t0 = time.monotonic()
    ok, detail = within(0.2, "slow thing", lambda: (release.wait(5), (True, "late"))[1])
    assert not ok and detail == "slow thing did not finish within 0.2 s"
    assert time.monotonic() - t0 < 1.0
    release.set()   # let the worker finish instead of leaving it sleeping
    assert within(1.0, "quick thing", lambda: (True, "done")) == (True, "done")


def test_within_raises_what_the_function_raised(capsys):
    with pytest.raises(OSError, match="device busy"):
        within(1.0, "boom", lambda: boom(0))
    release = threading.Event()
    slow = lambda timeout: within(timeout, "pose landmarker", lambda: (release.wait(5), (True, ""))[1])
    assert doctor(["pose"], {"pose": slow}, timeout=0.2) == 1
    assert "did not finish within 0.2 s" in capsys.readouterr().out
    release.set()


def test_probe_pose_without_model_is_unavailable(tmp_path):
    ok, detail = probe_pose(1.0, tmp_path / "missing.task")
    assert not ok and "model missing" in detail
