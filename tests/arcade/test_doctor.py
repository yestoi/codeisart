import subprocess
import sys
from pathlib import Path

from arcade.main import doctor, main

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
