# Iteration 1: Environment Spike and Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Roadmap milestone M1: a Python 3.12 toolchain with pinned dependencies and a `doctor`, the show daemon's display foundation (config, font, display protocol, the raw Colorlight backend as the arcade's wall path, DDP), and the arcade's config and calibration files.

**Architecture:** Two packages in one repo. `show/` is the display pipeline shared with the show daemon: a duck-typed `make_display(cfg)` builds a fake, SDL, raw Colorlight or DDP backend from any config object. `arcade/` holds the arcade's CLI (`doctor` only in this iteration), its flat TOML config and its per-setup calibration file. Everything is tested headless on the Mac; the Colorlight backend is tested through an injected fake socket because raw sockets are Linux-only.

**Tech Stack:** Python 3.12 from uv, numpy, pygame, opencv-contrib-python, sounddevice, Pillow, pyte, sdnotify, pytest; mediapipe 1.0.0 in the `mac` extra.

**Spec:** `docs/superpowers/specs/2026-09-26-wall-arcade-design.md`, revision 3 (sections 2, 3, 4.1 to 4.3, 6.6).

**Sources merged here (this plan overrides them where they differ):** core plan `docs/superpowers/plans/2026-09-26-wall-arcade-core.md` (Task 0; Task 1 with its per-task amendment; Task 2 with its per-task amendment; "Global Constraints, revised"), show daemon plan `docs/superpowers/plans/2026-09-22-show-daemon.md` (Tasks 1, 2, 5, 16, 15 with the daemon amendments for Tasks 1, 5, 15, 16, 17), and `docs/superpowers/reviews/2026-09-26-arcade-review-lenses/05-plan.md`. Every file below is final, amendment-applied code; an implementer needs nothing else.

## Global Constraints

Carried from the core plan ("Global Constraints" as replaced by "Global Constraints, revised"):

- Frames are numpy arrays of shape `(height, width, 3)`, dtype uint8, RGB, row-major.
- Every game declares `layouts`; its tests are parametrized over the declared layouts (spec 9.1). 128x32 is the default and design layout. (No games in this iteration.)
- Brightness: the runner calls `display.set_brightness(cfg.brightness)` once. The Colorlight backend enforces it at the panel with the card's brightness packet; SDL and fake model it in the preview; DDP logs once that it is Falcon Player's setting. Pixels pushed to hardware are never scaled for `brightness`.
- Tick rate 30 Hz; `dt` handed to games is clamped to 100 ms; clocks and random sources are injected.
- Never seed from `hash()` of a str; use `zlib.crc32` and print the seed in the assertion message.
- Modules that import `mediapipe`, `picamera2`, `cv2.VideoCapture` devices, or `sounddevice` do so inside the class constructor, probe function or thread, never at module import. Tests never need hardware extras.
- Tests run headless: `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy` are set in `tests/conftest.py` before pygame is imported.
- No `print` in library code; use `logging.getLogger("arcade")` in `arcade/` and `logging.getLogger(__name__)` in `show/`. CLI entry points and `tools/` may print.
- Python 3.12 through uv on the Mac; one OpenCV distribution, `opencv-contrib-python`.
- Commit after every task with the exact message and `git add` list given in the task.

Operator rules for this loop:

- Test modules are copied from this plan verbatim. Any difference, however small, is a Deviation and must be reported as one.
- Never push. Never run `git push` or `gh pr create`.
- Use `.venv/bin/python` (Python 3.12 from uv). Never use the system `python3` (3.14), never `pip`, never activate the venv in a way later commands depend on.
- Install with `uv pip install --python .venv/bin/python ...`.
- Run tests from the repo root with `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs` (append a path to run one module).

## Loop decisions taken by this plan (journal each one)

1. **mediapipe pin: `mediapipe>=1.0,!=1.0.1,<2`.** Checked 2026-09-27: 1.0.1 and 1.0.0 both ship `py3-none-macosx_11_0_arm64` wheels, but 1.0.1 aborts the process when a `PoseLandmarker` graph opens (`graph_service.h:139 Check failed: service_ Service is unavailable` from `DrishtiMetalHelper` in `TensorsToDetectionsCalculator::Open`), in IMAGE and VIDEO modes, with or without the CPU delegate, sandboxed or not. 1.0.0, 0.10.35, 0.10.21 and 0.10.14 all run it. The pin keeps 1.x (spec 4.2) and resolves to 1.0.0. `mp.tasks.vision`, `mp.tasks.BaseOptions`, `mp.Image` and `mp.ImageFormat` are the working import paths in 1.0.0, so `env_check.py` keeps its `startswith("1.")` check and `probe_pose` is unchanged.
2. **Colorlight constants, diffed 2026-09-27** against Falcon Player `src/channeloutput/ColorLight-5a-75.cpp` (master) and H. Kubota's protocol notes (chubby75 documents the card's hardware, not the protocol). Display-frame packet and row header: the daemon plan matches. Brightness packet: the daemon plan was wrong (`0x0AFF`, then b, 0x05, b, b, b); both sources say EtherType `0x0A<b>`, then b, b, 0xFF, zeros, 77 bytes. Pixel order: Falcon Player sends RGB (Kubota's panel needed BGR); this plan sends RGB, and the `rgb` test pattern on the panel (GATE B) is the check.
3. **Default calibration zone** reads "the central 60 percent of the frame" (spec 6.6) per axis: `(0.2, 0.2, 0.8, 0.8)`.

## Resolved conflicts (the arcade amendments win)

- **pyproject and venv.** Core Task 0's bounded `pyproject.toml` with `opencv-contrib-python` and `uv venv --python 3.12` replaces the daemon Task 1 file (no arcade deps, `python3 -m venv`, pip) and core Task 1 Step 1's (`opencv-python`, unbounded). It is written once, in Task 1; no later task edits it.
- **`.gitignore`.** The daemon's file would overwrite the repo's; Task 2 appends its `entries/` rules instead, keeping the operator's `docs/superpowers/workflow/.blocks` line.
- **Fake display.** `last` and `count` (daemon and core amendments), not the daemon's `frames` list.
- **`make_display`.** Duck-typed `DisplayConfig` protocol with `iface` (core amendment); the colorlight branch passes `getattr(cfg, "iface", None) or cfg.colorlight_iface`, so the daemon's `Config` still works. The daemon's `from show.config import Config` in `show/display/__init__.py` is gone. `matrix` raises `ValueError` (daemon amendment for Task 17).
- **Colorlight role and packets.** Primary wall path, not descope step 1. The display-frame packet is sent before the rows (daemon amendment; this is Falcon Player's wire order, so a pushed frame shows when the next push starts), which replaces the daemon test's rows-then-frame order. Packets are prebuilt as one `(height, chunks, 21 + 3 * chunk)` uint8 array filled by one strided assignment per frame; the daemon amendment's `(rows, 2, 789)` is the 512-wide case, and the arcade's 128 and 64 widths use one chunk per row. Brightness packet and pixel order per decision 2.
- **DDP.** Data type `0x0B`, no pixel scaling, `set_brightness` stores the level and logs once (core amendment), replacing the daemon's `0x01` and software scaling.
- **SDL.** `show/display/sdl.py` is the daemon's file unchanged; preview brightness modelling arrives with core Task 6's `PreviewDisplay`.
- **Config `fps`.** The daemon's `Config.fps` defaults to 20 (daemon amendment); the arcade's `ArcadeConfig.fps` is 30. They are different objects.
- **Arcade config.** Exactly spec 4.3's fields and defaults plus `font_path` and `fps`; `idle_seconds` is gone; `test_defaults_when_file_missing` is rewritten for the 128x32 defaults.

## Additions beyond the source plans (reviewer: check these on purpose)

- `tests/conftest.py` sets the SDL dummy drivers (Global Constraint); `test_real_font_file_loads` resolves the font from the repo root, not the working directory.
- `tests/test_config.py` gains `test_repo_show_toml_matches_defaults` (the task edits `show.toml`) and asserts the daemon amendment's new defaults.
- Colorlight: a frame of the wrong shape raises `ValueError`; a width that does not split into equal row packets raises `ValueError`; with no `AF_PACKET` (macOS) the constructor raises `OSError` naming Linux raw sockets; `row_packets` stays as the reference encoder that `push` is tested against byte for byte.
- Arcade config: TOML values of the wrong type raise `ValueError` naming the field (an int is accepted for a float field); `arcade.toml` is tested to list every field with its default.
- Calibration: `static_mask` is a tuple of `(x, y, radius)` lights in normalized camera coordinates, and `baseline_scale = 0.0` means not measured. Tasks 15 and 18 of the core plan consume and produce these.

## Review Focus

1. A TOML value of the wrong type in `arcade.toml` (`brightness = "0.4"`, `width = true`). Load must raise `ValueError` naming the field, never let a `TypeError` escape later from a comparison. Test: Task 7, `test_wrong_type_rejected`.
2. `calibration.json` truncated by a power cut or hand-edited into nonsense (empty, not JSON, a list, three zone numbers, an inverted zone). Startup must fall back to the uncalibrated defaults with a warning, never crash. Test: Task 7, `test_corrupt_calibration_falls_back_to_defaults`.
3. A frame whose shape disagrees with the Colorlight display, with the same byte count (a 128x32 frame pushed to a 64x64 display). The backend must raise, never paint scrambled rows on the wall. Test: Task 5, `test_push_rejects_a_frame_of_the_wrong_shape`.
4. `--backend colorlight` on the Mac, which has no `AF_PACKET`. The constructor must raise an `OSError` that says why and suggests `sdl`, not an `AttributeError`. Test: Task 5, `test_without_raw_sockets_a_clear_error`.
5. The prebuilt packet buffer is reused every push. A later frame must replace every pixel of an earlier one, and the headers must survive. Test: Task 5, `test_push_matches_reference_encoder` (two pushes per layout, byte-compared against `row_packets`).

## Environment facts verified 2026-09-27

- macOS 15.6 (Darwin 24.6) on arm64; uv 0.10.11 at `/opt/homebrew/bin/uv`; uv already has CPython 3.12.13. The repo has no `.venv`, `pyproject.toml`, `show/`, `arcade/`, `tests/`, `tools/` or `fonts/` yet.
- A scratch install of this plan's `pyproject.toml` resolved: mediapipe 1.0.0, opencv-contrib-python 5.0.0.93 (the only OpenCV), numpy 2.5.3, pygame 2.6.1, sounddevice 0.5.6, Pillow 12.3.0, pytest 9.1.1, pyte 0.8.2, sdnotify 0.3.2 (sdist, pure Python). All have cp312 or py3 arm64 wheels inside the bounds.
- With that install, `tools/env_check.py` ran (`PoseLandmarker VIDEO mode ran: 0 poses, 11.4 ms per frame`), importing `cv2` with `pygame` printed 17 SDL duplicate-class warnings without crashing, and `python -m arcade doctor --require camera,mic,pose` exited 0 in this session. The operator's terminal may still lack camera or microphone permission.
- Font source URLs return 200: `https://raw.githubusercontent.com/adafruit/Adafruit-GFX-Library/1.12.6/glcdfont.c` (9064 bytes, identical to `master`) and `.../1.12.6/license.txt` (1344 bytes). The extracted `fonts/5x7.bin` has sha256 `c6628e1c13dd7445117e2179862bbe27d43e3ac0ce0b6153b7eee906cccf96ae`.
- The pose model URL returns 200 (5,777,746 bytes).
- A setuptools editable install only maps the top-level packages present when it ran, so Task 2 reinstalls after creating `show/`.
- The whole plan's code was run in a scratch copy: every per-task count below was observed.

## File map

```
pyproject.toml                  Task 1  dependencies, extras, pytest config
.gitignore                      Task 1 (models/, data/, shots/), Task 2 (entries/ rules)
arcade/__init__.py              Task 1  empty
arcade/__main__.py              Task 1  python -m arcade
arcade/main.py                  Task 1  CLI: doctor and its probes
arcade/sources/__init__.py      Task 1  empty
arcade/sources/README.md        Task 1  written by tools/env_check.py
tools/env_check.py              Task 1  environment spike
tests/__init__.py               Task 1  empty
tests/arcade/__init__.py        Task 1  empty
tests/arcade/test_doctor.py     Task 1
show/__init__.py                Task 2  empty
show/config.py                  Task 2  daemon Config, load_config
show.toml                       Task 2  daemon runtime config
tests/test_config.py            Task 2
tools/extract_glcdfont.py       Task 3
fonts/glcdfont.c, fonts/LICENSE.glcdfont, fonts/5x7.bin   Task 3
show/font.py                    Task 3  Font, CELL_W, CELL_H
tests/conftest.py               Task 3  SDL dummy drivers, font and fast_cfg fixtures
tests/test_font.py              Task 3
show/display/__init__.py        Task 4, grown in Tasks 5 and 6: DisplayConfig, Display, make_display
show/display/fake.py            Task 4
show/display/sdl.py             Task 4
tests/test_display.py           Task 4
show/display/colorlight.py      Task 5
tests/test_colorlight.py        Task 5
show/display/ddp.py             Task 6
tests/test_ddp.py               Task 6
arcade/config.py                Task 7  ArcadeConfig, load_config
arcade.toml                     Task 7
arcade/calibration.py           Task 7  Calibration, load_calibration, save_calibration
tests/arcade/test_config.py     Task 7
tests/arcade/test_calibration.py Task 7
```

---

### Task 1: Environment spike (core plan Task 0)

**Files:**
- Create: `pyproject.toml`, `arcade/__init__.py`, `arcade/__main__.py`, `arcade/main.py`, `arcade/sources/__init__.py`, `arcade/sources/README.md` (written by the tool), `tools/env_check.py`, `tests/__init__.py`, `tests/arcade/__init__.py`
- Modify: `.gitignore` (append `models/`, `data/`, `shots/`)
- Test: `tests/arcade/test_doctor.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `arcade.main.doctor(require: list[str], probes: dict[str, Probe], timeout: float = 5.0, out: TextIO | None = None) -> int` (0 all available, 1 any unavailable, 2 unknown name); `Probe = Callable[[float], tuple[bool, str]]`; `probe_camera(timeout, index=0)`, `probe_mic(timeout, device="")`, `probe_pose(timeout, model=MODEL_PATH)`; `MODEL_PATH` (`models/pose_landmarker_lite.task`); `main(argv: list[str] | None = None) -> int` with `doctor --require camera,mic,pose [--timeout S] [--camera-index N] [--audio-device NAME] [--model PATH]`; `tools/env_check.py`, which downloads the model and rewrites the versions block of `arcade/sources/README.md`. The venv at `.venv` that every later task uses.

- [ ] **Step 1: Toolchain, `pyproject.toml`, install**

```bash
uv python install 3.12
uv venv --python 3.12 .venv
```

`pyproject.toml`:

```toml
[project]
name = "codeisart-show"
version = "0.1.0"
requires-python = ">=3.11"   # Mac: 3.12 from uv; Pi 5: its system Python
dependencies = [
    "pyte>=0.8.2,<0.9", "numpy>=1.26,<3", "pygame>=2.5,<3", "sdnotify>=0.3,<0.4",
    "opencv-contrib-python>=4.9,<6",   # the only OpenCV: mediapipe requires the contrib build
    "sounddevice>=0.4.6,<0.6", "Pillow>=10,<13",
]

[project.optional-dependencies]
pi = ["gpiozero>=2.0,<3", "lgpio"]
mac = ["mediapipe>=1.0,!=1.0.1,<2"]   # 1.0.1 aborts opening a PoseLandmarker on macOS arm64
dev = ["pytest>=8,<10"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["show*", "arcade*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
markers = ["perf: timing budget tests", "feel: feel budget tests", "hardware: needs a real device or model"]
```

Create these as empty files: `arcade/__init__.py`, `arcade/sources/__init__.py`, `tests/__init__.py`, `tests/arcade/__init__.py`.

Append to `.gitignore` (keep every existing line):

```
# arcade: pose model, runtime data, contact sheets
models/
data/
shots/
```

Install and check there is exactly one OpenCV:

```bash
uv pip install --python .venv/bin/python -e '.[dev,mac]'
uv pip list --python .venv/bin/python | grep -i -E "opencv|mediapipe"
```

Expected: exactly two lines, `mediapipe 1.0.0` and `opencv-contrib-python 5.0.0.93` (a later 5.x is fine). A second OpenCV line is a failure to fix before going on.

- [ ] **Step 2: Write the failing tests**

`tests/arcade/test_doctor.py`:

```python
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
```

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_doctor.py`
Expected: FAIL, a collection error with `ModuleNotFoundError: No module named 'arcade.main'`.

- [ ] **Step 3: Implement the doctor**

`arcade/__main__.py`:

```python
import sys

from arcade.main import main

sys.exit(main())
```

`arcade/main.py`:

```python
"""Arcade command line. Task 0 provides `doctor`; Task 18 adds run (the default), calibrate, record, stats."""
from __future__ import annotations

import argparse
import importlib.metadata
import sys
import time
from pathlib import Path
from typing import Callable, TextIO

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "pose_landmarker_lite.task"
TIMEOUT = 5.0
Probe = Callable[[float], tuple[bool, str]]


def probe_camera(timeout: float, index: int = 0) -> tuple[bool, str]:
    import cv2  # inside the probe, so importing arcade.main never loads OpenCV

    cap, frames, deadline = cv2.VideoCapture(index), 0, time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            ok, frame = cap.read()
            if not ok or frame is None:
                time.sleep(0.05)
                continue
            frames += 1
            if frame.any():
                return True, f"device {index}: {frame.shape[1]}x{frame.shape[0]}"
        why = f"{frames} frames, all black" if frames else f"no frames in {timeout:.0f} s"
        return False, f"device {index}: {why} (macOS: grant this terminal camera access)"
    finally:
        cap.release()


def probe_mic(timeout: float, device: str = "") -> tuple[bool, str]:
    import numpy as np
    import sounddevice as sd

    blocks: list = []
    with sd.InputStream(samplerate=16000, channels=1, dtype="float32", device=device or None,
                        callback=lambda data, n, t, status: blocks.append(data.copy())):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if any(np.any(b != 0.0) for b in list(blocks)):
                return True, f"{device or 'default input'}: {sum(len(b) for b in blocks)} samples"
            time.sleep(0.05)
    why = "exact zeros (macOS: grant this terminal microphone access)" if blocks else "no audio callbacks"
    return False, f"{device or 'default input'}: {why}"


def probe_pose(timeout: float, model: Path = MODEL_PATH) -> tuple[bool, str]:
    if not Path(model).exists():
        return False, f"model missing at {model}; run: python tools/env_check.py"
    import mediapipe as mp
    import numpy as np

    vision = mp.tasks.vision
    options = vision.PoseLandmarkerOptions(base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
                                           running_mode=vision.RunningMode.VIDEO, num_poses=2)
    frame = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.full((480, 640, 3), 96, np.uint8))
    with vision.PoseLandmarker.create_from_options(options) as landmarker:
        t0 = time.monotonic()
        landmarker.detect_for_video(frame, 0)
        ms = (time.monotonic() - t0) * 1000
    return True, f"mediapipe {importlib.metadata.version('mediapipe')}: landmarker ran in {ms:.0f} ms"


def doctor(require: list[str], probes: dict[str, Probe], timeout: float = TIMEOUT,
           out: TextIO | None = None) -> int:
    out = out or sys.stdout  # CLI output, not library logging
    unknown = [n for n in require if n not in probes]
    if unknown:
        print(f"doctor: unknown source {', '.join(unknown)}; choose from {', '.join(sorted(probes))}", file=out)
        return 2
    failed = 0
    for name in require:
        try:
            ok, detail = probes[name](timeout)
        except Exception as e:  # a probe that raises is a source that is unavailable
            ok, detail = False, f"{type(e).__name__}: {e}"
        print(f"{name:7s} {'ok' if ok else 'UNAVAILABLE'}  {detail}", file=out)
        failed += not ok
    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="arcade", description="Wall arcade")
    sub = p.add_subparsers(dest="command", required=True)
    d = sub.add_parser("doctor", help="exit 1 if a required source is unavailable after the timeout")
    d.add_argument("--require", default="camera,mic,pose", help="comma list of camera, mic, pose")
    d.add_argument("--timeout", type=float, default=TIMEOUT)
    d.add_argument("--camera-index", type=int, default=0)
    d.add_argument("--audio-device", default="")
    d.add_argument("--model", default=str(MODEL_PATH))
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    probes = {"camera": lambda t: probe_camera(t, args.camera_index),
              "mic": lambda t: probe_mic(t, args.audio_device),
              "pose": lambda t: probe_pose(t, Path(args.model))}
    return doctor([n.strip() for n in args.require.split(",") if n.strip()], probes, args.timeout)


if __name__ == "__main__":
    sys.exit(main())
```

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_doctor.py`
Expected: `5 passed`.

- [ ] **Step 4: The environment check**

`tools/env_check.py`:

```python
#!/usr/bin/env python3
"""Environment spike (Task 0, Mac): prove the toolchain works and record the versions that did."""
from __future__ import annotations

import importlib.metadata as md
import platform
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "arcade" / "sources" / "README.md"
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/"
             "float16/1/pose_landmarker_lite.task")
MODEL_PATH = ROOT / "models" / "pose_landmarker_lite.task"
PACKAGES = ("mediapipe", "opencv-contrib-python", "numpy", "pygame", "sounddevice", "Pillow", "pytest")
OPENCVS = {"opencv-python", "opencv-python-headless", "opencv-contrib-python", "opencv-contrib-python-headless"}
BEGIN, END = "<!-- env_check:begin -->", "<!-- env_check:end -->"


def version(name: str) -> str:
    try:
        return md.version(name)
    except md.PackageNotFoundError:
        return "MISSING"


def run_pose(jpeg: Path) -> str:
    import mediapipe as mp

    if not MODEL_PATH.exists():
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(MODEL_URL, timeout=60) as r:
            MODEL_PATH.with_suffix(".part").write_bytes(r.read())
        MODEL_PATH.with_suffix(".part").replace(MODEL_PATH)
    vision = mp.tasks.vision
    options = vision.PoseLandmarkerOptions(base_options=mp.tasks.BaseOptions(model_asset_path=str(MODEL_PATH)),
                                           running_mode=vision.RunningMode.VIDEO, num_poses=2)
    image = mp.Image.create_from_file(str(jpeg))
    with vision.PoseLandmarker.create_from_options(options) as landmarker:
        t0 = time.perf_counter()
        for ts in (0, 33, 66):  # VIDEO mode needs strictly increasing timestamps
            result = landmarker.detect_for_video(image, ts)
        ms = (time.perf_counter() - t0) / 3 * 1000
    return f"PoseLandmarker VIDEO mode ran: {len(result.pose_landmarks)} poses, {ms:.1f} ms per frame"


def main() -> int:
    from PIL import Image, ImageDraw

    if sys.version_info[:2] != (3, 12):
        sys.exit(f"expected Python 3.12 from uv, got {platform.python_version()}")
    opencvs = sorted({(d.metadata["Name"] or "").lower() for d in md.distributions()} & OPENCVS)
    if opencvs != ["opencv-contrib-python"]:
        sys.exit(f"exactly one OpenCV, opencv-contrib-python, must be installed; found {opencvs}")
    vers = {name: version(name) for name in PACKAGES}
    if "MISSING" in vers.values() or not vers["mediapipe"].startswith("1."):
        sys.exit(f"a package is missing or mediapipe is not 1.x: {vers}")
    with tempfile.TemporaryDirectory() as tmp:  # a grey frame with a figure: no pose needed, no raise allowed
        img = Image.new("RGB", (640, 480), (90, 90, 90))
        ImageDraw.Draw(img).ellipse((280, 60, 360, 420), fill=(230, 200, 170))
        img.save(Path(tmp) / "figure.jpg", "JPEG")
        pose_line = run_pose(Path(tmp) / "figure.jpg")
    probe = subprocess.run([sys.executable, "-c", "import cv2, pygame"], capture_output=True, text=True)
    sdl = probe.stderr.count("is implemented in both")  # opencv and pygame each bundle SDL2 on macOS
    rows = "\n".join(f"| {k} | {v} |" for k, v in vers.items())
    block = (f"{BEGIN}\n## Environment (tools/env_check.py, {date.today().isoformat()})\n\n"
             f"- Python {platform.python_version()} on {platform.platform()}\n- {pose_line}\n"
             f"- SDL duplicate-class warnings importing cv2 with pygame: {sdl}\n\n"
             f"| Package | Version |\n|---|---|\n{rows}\n\n"
             f"pyproject.toml bounds each package below its next major version.\n{END}\n")
    text = README.read_text() if README.exists() else "# Sources\n\nMeasured facts and decisions (spec 12).\n"
    if BEGIN in text and END in text:
        text = text.split(BEGIN, 1)[0] + block + text.split(END, 1)[1].lstrip("\n")
    else:
        text = text.rstrip("\n") + "\n\n" + block
    README.write_text(text)
    print(f"{pose_line}\nSDL duplicate warnings: {sdl}\nwrote {README}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Run: `.venv/bin/python tools/env_check.py`
Expected (MediaPipe and TensorFlow Lite log lines on stderr are normal): a line starting `PoseLandmarker VIDEO mode ran:`, a line `SDL duplicate warnings: <n>` (17 in the scratch run), and `wrote .../arcade/sources/README.md`. The model lands in `models/pose_landmarker_lite.task` (gitignored). `arcade/sources/README.md` now holds a `## Environment` block with the versions table. If the script aborts with `Check failed: service_ Service is unavailable`, mediapipe 1.0.1 was installed despite the pin: stop and report it.

**SDL duplication (macOS).** opencv and pygame each bundle `libSDL2`; importing both prints objc "implemented in both" warnings. Core Task 6 keeps `look.py` free of cv2 so only the camera source imports it. If the owner's live smoke crashes on this, switch `pygame` to `pygame-ce` (same `import pygame`). Nothing to do in this iteration.

- [ ] **Step 5: Run the doctor**

Run: `.venv/bin/python -m arcade doctor --require pose; echo "exit $?"`
Expected: `pose    ok  mediapipe 1.0.0: landmarker ran in <n> ms` and `exit 0`.

Run: `.venv/bin/python -m arcade doctor --require camera,mic,pose; echo "exit $?"`
Expected: three `ok` lines and `exit 0`. A camera or mic `UNAVAILABLE` line (macOS permission for the terminal) is not a task failure: report it so the operator records it as an owner item, and go on.

- [ ] **Step 6: Run the whole suite, then commit**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`
Expected: `5 passed`, no skips.

```bash
git add pyproject.toml .gitignore arcade/__init__.py arcade/__main__.py arcade/main.py arcade/sources/__init__.py \
    arcade/sources/README.md tools/env_check.py tests/__init__.py tests/arcade/__init__.py tests/arcade/test_doctor.py
git commit -m "chore(arcade): environment spike, pinned deps, doctor"
```

---

### Task 2: Show scaffold and config (daemon Task 1 with its amendment)

**Files:**
- Create: `show/__init__.py`, `show/config.py`, `show.toml`
- Modify: `.gitignore` (append the daemon's `entries/` rules)
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: the `.venv` and `pyproject.toml` from Task 1 (do not edit `pyproject.toml`).
- Produces: `show.config.Config` dataclass (fields as below; `fps` defaults to 20; no `matrix_multiplexing`), `load_config(path: Path) -> Config`, `Config.phosphor_rgb -> tuple[int, int, int]`, `Config.effective_brightness -> float`, `PHOSPHORS`. `Config` has `width`, `height`, `backend`, `sdl_scale`, `ddp_host`, `ddp_port`, `colorlight_iface`, which `make_display` reads in Tasks 4 to 6.

- [ ] **Step 1: Package and ignore rules**

Create `show/__init__.py` as an empty file. Append to `.gitignore` (keep every existing line):

```
# show daemon: entry build products stay local; sources, entry.toml and fallback casts are tracked
entries/*/*
!entries/*/*.c
!entries/*/entry.toml
!entries/*/fallback.cast
```

Reinstall so the editable install maps the new `show` package (it only maps packages present when it ran):

```bash
uv pip install --python .venv/bin/python -e '.[dev,mac]'
```

- [ ] **Step 2: Write the failing tests**

`tests/test_config.py`:

```python
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
```

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/test_config.py`
Expected: FAIL, a collection error with `ModuleNotFoundError: No module named 'show.config'`.

- [ ] **Step 3: Implement config**

`show/config.py`:

```python
from __future__ import annotations

import dataclasses
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

PHOSPHORS: dict[str, tuple[int, int, int]] = {
    "green": (51, 255, 51),
    "amber": (255, 176, 0),
}


@dataclass
class Config:
    backend: str = "sdl"
    width: int = 512
    height: int = 192
    brightness: float = 0.15
    brightness_cap: float = 0.40
    sdl_scale: int = 2
    columns: int = 80
    rows: int = 24
    phosphor: str = "green"
    glow: bool = False
    entries_dir: Path = Path("entries")
    audio_dir: Path = Path("audio")
    font_path: Path = Path("fonts/5x7.bin")
    button_pins: list[int] = field(default_factory=lambda: [5, 6, 13, 19, 26])
    light_pins: list[int] = field(default_factory=lambda: [12, 16, 20, 21, 25])
    ddp_host: str = "127.0.0.1"
    ddp_port: int = 4048
    colorlight_iface: str = "eth0"
    dwell: float = 4.0
    error_hold: float = 3.0
    typewriter_cps: int = 400
    attract_lps: float = 3.0
    fps: int = 20
    capture: bool = False
    volume: float = 0.6
    quiet_hours: str = ""
    crowd_run_seconds: float = 10.0
    idle_run_seconds: float = 40.0
    attract_autoplay_minutes: float = 5.0
    min_build_seconds: float = 1.5
    pump_bytes: int = 4096
    pump_ms: float = 8.0

    @property
    def phosphor_rgb(self) -> tuple[int, int, int]:
        return PHOSPHORS[self.phosphor]

    @property
    def effective_brightness(self) -> float:
        return min(self.brightness, self.brightness_cap)


def load_config(path: Path) -> Config:
    data = tomllib.loads(path.read_text()) if path.exists() else {}
    cfg = Config()
    fields = {f.name: f for f in dataclasses.fields(Config)}
    for key, value in data.items():
        if key not in fields:
            raise ValueError(f"{path}: unknown config key {key!r}")
        if isinstance(getattr(cfg, key), Path):
            value = Path(value)
        setattr(cfg, key, value)
    if cfg.phosphor not in PHOSPHORS:
        raise ValueError(f"{path}: phosphor must be one of {sorted(PHOSPHORS)}")
    if not 0.0 <= cfg.brightness_cap <= 1.0:
        raise ValueError(f"{path}: brightness_cap must be between 0 and 1")
    return cfg
```

`show.toml`:

```toml
# Flat config. Every key is a field of show.config.Config.
backend = "sdl"          # sdl | fake | colorlight | ddp
brightness = 0.15        # night operating level
brightness_cap = 0.40    # never exceeded, sized to the power supplies
phosphor = "green"       # green | amber
glow = false
entries_dir = "entries"
audio_dir = "audio"
font_path = "fonts/5x7.bin"
button_pins = [5, 6, 13, 19, 26]
light_pins = [12, 16, 20, 21, 25]
ddp_host = "127.0.0.1"
ddp_port = 4048
colorlight_iface = "eth0"
dwell = 4.0
error_hold = 3.0
typewriter_cps = 400
attract_lps = 3.0
fps = 20
capture = false
volume = 0.6
quiet_hours = ""         # e.g. "02:00-08:00"
crowd_run_seconds = 10.0
idle_run_seconds = 40.0
attract_autoplay_minutes = 5.0
min_build_seconds = 1.5
pump_bytes = 4096
pump_ms = 8.0
```

- [ ] **Step 4: Run the tests**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/test_config.py`
Expected: `5 passed`.

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`
Expected: `10 passed`, no skips.

- [ ] **Step 5: Commit**

```bash
git add .gitignore show/__init__.py show/config.py show.toml tests/test_config.py
git commit -m "feat(show): scaffold and flat TOML config (daemon Task 1)"
```

---

### Task 3: Font (daemon Task 2)

**Files:**
- Create: `tools/extract_glcdfont.py`, `show/font.py`, `fonts/glcdfont.c`, `fonts/LICENSE.glcdfont`, `fonts/5x7.bin`
- Test: `tests/conftest.py`, `tests/test_font.py`

**Interfaces:**
- Consumes: `show.config.Config` (Task 2), for the `fast_cfg` fixture.
- Produces: `show.font.CELL_W = 6`, `CELL_H = 8`, `Font(data: bytes)`, `Font.load(path) -> Font`, `Font.glyph(code: int) -> list[int]` (8 rows, bit 5 is the leftmost pixel), `Font.atlas() -> np.ndarray` of shape `(256, 8, 6)` bool; `fonts/5x7.bin` (1280 bytes); pytest fixtures `font` and `fast_cfg` in `tests/conftest.py`, which also sets the SDL dummy drivers for every test.

The glyph source is Adafruit's classic 5x7 `glcdfont.c` (BSD license). Each glyph is 5 column bytes, bit 0 is the top row, placed in a 6x8 cell with column 5 and row 7 as spacing.

- [ ] **Step 1: Fetch the font source and write the extractor**

```bash
mkdir -p fonts tools
curl -fL -o fonts/glcdfont.c https://raw.githubusercontent.com/adafruit/Adafruit-GFX-Library/1.12.6/glcdfont.c
curl -fL -o fonts/LICENSE.glcdfont https://raw.githubusercontent.com/adafruit/Adafruit-GFX-Library/1.12.6/license.txt
```

If the tag URL fails, use the same paths on `master` (identical content on 2026-09-27).

`tools/extract_glcdfont.py`:

```python
"""Extract the 5x7 glyph table from Adafruit's glcdfont.c into a 1280-byte file.

Usage: python tools/extract_glcdfont.py fonts/glcdfont.c fonts/5x7.bin
"""
import re
import sys
from pathlib import Path

src = Path(sys.argv[1]).read_text()
body = src[src.index("{") + 1 : src.rindex("}")]
values = [int(h, 16) for h in re.findall(r"0x([0-9A-Fa-f]{2})", body)]
if len(values) < 128 * 5:
    sys.exit(f"only {len(values)} bytes found; expected at least 640")
data = bytes(values[: 256 * 5]).ljust(256 * 5, b"\0")
Path(sys.argv[2]).write_bytes(data)
print(f"wrote {len(data)} bytes to {sys.argv[2]}")
```

Run: `.venv/bin/python tools/extract_glcdfont.py fonts/glcdfont.c fonts/5x7.bin && shasum -a 256 fonts/5x7.bin`
Expected: `wrote 1280 bytes to fonts/5x7.bin` and the hash `c6628e1c13dd7445117e2179862bbe27d43e3ac0ce0b6153b7eee906cccf96ae`.

- [ ] **Step 2: Write the failing tests**

`tests/conftest.py`:

```python
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # before anything imports pygame
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from show.config import Config
from show.font import Font

# Column bytes for a capital A in the glcdfont layout (bit 0 = top row).
A_COLUMNS = bytes([0x7E, 0x11, 0x11, 0x11, 0x7E])


@pytest.fixture
def font() -> Font:
    data = bytearray(256 * 5)
    data[65 * 5 : 66 * 5] = A_COLUMNS
    return Font(bytes(data))


@pytest.fixture
def fast_cfg() -> Config:
    return Config(typewriter_cps=1_000_000, dwell=0.1, error_hold=0.1, attract_lps=1000.0)
```

`tests/test_font.py`:

```python
from pathlib import Path

import pytest

from show.font import CELL_H, CELL_W, Font

ROOT = Path(__file__).resolve().parents[1]


def test_cell_size():
    assert (CELL_W, CELL_H) == (6, 8)


def test_space_is_blank(font):
    assert font.glyph(ord(" ")) == [0] * 8


def test_a_rows(font):
    rows = font.glyph(ord("A"))
    assert rows[0] == 0b011100
    assert rows[1] == 0b100010
    assert rows[4] == 0b111110
    assert rows[7] == 0
    assert all(r < 64 for r in rows)


def test_out_of_range_code_uses_question_mark(font):
    assert font.glyph(1000) == font.glyph(ord("?"))


def test_atlas_shape_and_content(font):
    atlas = font.atlas()
    assert atlas.shape == (256, 8, 6)
    assert atlas.dtype == bool
    assert atlas[65, 4].tolist() == [True, True, True, True, True, False]


def test_wrong_size_rejected():
    with pytest.raises(ValueError):
        Font(b"\0" * 10)


def test_real_font_file_loads():
    real = Font.load(ROOT / "fonts" / "5x7.bin")
    assert real.glyph(ord(" ")) == [0] * 8
    assert any(real.glyph(ord("A"))[:7])
```

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/test_font.py`
Expected: FAIL, `ImportError while loading conftest` with `ModuleNotFoundError: No module named 'show.font'`.

- [ ] **Step 3: Implement the font**

`show/font.py`:

```python
from __future__ import annotations

from pathlib import Path

import numpy as np

CELL_W = 6
CELL_H = 8
GLYPH_COLS = 5
GLYPH_ROWS = 7
NUM_GLYPHS = 256


class Font:
    """5x7 column-major glyphs placed in 6x8 cells. Column 5 and row 7 are spacing."""

    def __init__(self, data: bytes):
        if len(data) != NUM_GLYPHS * GLYPH_COLS:
            raise ValueError(f"font data must be {NUM_GLYPHS * GLYPH_COLS} bytes, got {len(data)}")
        self._data = data
        self._atlas: np.ndarray | None = None

    @classmethod
    def load(cls, path: Path) -> "Font":
        return cls(Path(path).read_bytes())

    def glyph(self, code: int) -> list[int]:
        if not 0 <= code < NUM_GLYPHS:
            code = ord("?")
        cols = self._data[code * GLYPH_COLS : (code + 1) * GLYPH_COLS]
        rows = []
        for r in range(CELL_H):
            bits = 0
            if r < GLYPH_ROWS:
                for c in range(GLYPH_COLS):
                    if (cols[c] >> r) & 1:
                        bits |= 1 << (CELL_W - 1 - c)
            rows.append(bits)
        return rows

    def atlas(self) -> np.ndarray:
        if self._atlas is None:
            a = np.zeros((NUM_GLYPHS, CELL_H, CELL_W), dtype=bool)
            for code in range(NUM_GLYPHS):
                for r, bits in enumerate(self.glyph(code)):
                    for c in range(CELL_W):
                        a[code, r, c] = bool((bits >> (CELL_W - 1 - c)) & 1)
            self._atlas = a
        return self._atlas
```

- [ ] **Step 4: Run the tests**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/test_font.py`
Expected: `7 passed`.

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`
Expected: `17 passed`, no skips.

- [ ] **Step 5: Commit**

```bash
git add tools/extract_glcdfont.py show/font.py fonts/glcdfont.c fonts/LICENSE.glcdfont fonts/5x7.bin \
    tests/conftest.py tests/test_font.py
git commit -m "feat(show): 5x7 bitmap font from glcdfont with 6x8 cell atlas (daemon Task 2)"
```

---

### Task 4: Display protocol, fake and SDL backends (daemon Task 5 with the arcade amendments)

**Files:**
- Create: `show/display/__init__.py`, `show/display/fake.py`, `show/display/sdl.py`
- Test: `tests/test_display.py`

**Interfaces:**
- Consumes: `show.config.Config` (Task 2); the SDL dummy drivers from `tests/conftest.py` (Task 3).
- Produces: `show.display.DisplayConfig` protocol (`width`, `height`, `backend`, `sdl_scale`, `ddp_host`, `ddp_port`, `iface`); `show.display.Display` protocol (`push(frame: np.ndarray) -> None`, `set_brightness(level: float) -> None`, `close() -> None`); `make_display(cfg, on_key: Callable[[int], None] | None = None) -> Display`, which reads attributes off any object and raises `ValueError` for an unknown backend; `FakeDisplay()` with `.last` (copy of the last frame or `None`), `.count`, `.brightness`, `.closed`; `SDLDisplay(width, height, scale=2, on_key=None)`, where `on_key(index)` gets 0 for key `1`. Tasks 5 and 6 add the `colorlight` and `ddp` branches.

- [ ] **Step 1: Write the failing tests**

`tests/test_display.py`:

```python
import os
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np
import pytest

from show.config import Config
from show.display import make_display
from show.display.fake import FakeDisplay
from show.display.sdl import SDLDisplay


def test_fake_display_keeps_last_and_count():
    d = FakeDisplay()
    frame = np.zeros((192, 512, 3), np.uint8)
    d.push(frame)
    frame[0, 0] = 255
    d.push(frame)
    assert d.count == 2
    assert d.last.sum() == 765
    d.set_brightness(0.2)
    assert d.brightness == 0.2
    d.close()
    assert d.closed


def test_sdl_display_pushes_headless():
    pressed = []
    d = SDLDisplay(512, 192, scale=1, on_key=pressed.append)
    d.push(np.zeros((192, 512, 3), np.uint8))
    d.push(np.full((192, 512, 3), 40, np.uint8))
    d.set_brightness(0.15)
    d.close()


def test_make_display_fake_and_unknown():
    assert isinstance(make_display(Config(backend="fake")), FakeDisplay)
    for backend in ("hologram", "matrix"):  # the matrix backend was removed (daemon Task 17)
        with pytest.raises(ValueError):
            make_display(Config(backend=backend))


def test_make_display_accepts_any_config_object():
    cfg = SimpleNamespace(width=64, height=64, backend="fake", sdl_scale=8,
                          ddp_host="127.0.0.1", ddp_port=4048)
    assert isinstance(make_display(cfg), FakeDisplay)
```

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/test_display.py`
Expected: FAIL, a collection error with `ModuleNotFoundError: No module named 'show.display'`.

- [ ] **Step 2: Implement the display package**

`show/display/__init__.py`:

```python
from __future__ import annotations

from typing import Callable, Protocol

import numpy as np


class DisplayConfig(Protocol):
    """Any object with these attributes can be handed to make_display.

    `iface` is the wired interface for the colorlight backend; the daemon's Config calls it
    `colorlight_iface`, and make_display reads either.
    """

    width: int
    height: int
    backend: str
    sdl_scale: int
    ddp_host: str
    ddp_port: int
    iface: str


class Display(Protocol):
    def push(self, frame: np.ndarray) -> None: ...
    def set_brightness(self, level: float) -> None: ...
    def close(self) -> None: ...


def make_display(cfg: DisplayConfig, on_key: Callable[[int], None] | None = None) -> Display:
    if cfg.backend == "fake":
        from show.display.fake import FakeDisplay
        return FakeDisplay()
    if cfg.backend == "sdl":
        from show.display.sdl import SDLDisplay
        return SDLDisplay(cfg.width, cfg.height, cfg.sdl_scale, on_key)
    raise ValueError(f"unknown display backend {cfg.backend!r}")
```

`show/display/fake.py`:

```python
from __future__ import annotations

import numpy as np


class FakeDisplay:
    """Keeps only the last frame and a count (daemon plan amendment for Task 5)."""

    def __init__(self):
        self.last: np.ndarray | None = None
        self.count = 0
        self.brightness = 1.0
        self.closed = False

    def push(self, frame: np.ndarray) -> None:
        self.last = frame.copy()
        self.count += 1

    def set_brightness(self, level: float) -> None:
        self.brightness = level

    def close(self) -> None:
        self.closed = True
```

`show/display/sdl.py`:

```python
from __future__ import annotations

from typing import Callable

import numpy as np
import pygame


class SDLDisplay:
    """Preview window. Keys 1..9 call on_key(0..8). Shows full brightness on purpose."""

    def __init__(self, width: int, height: int, scale: int = 2,
                 on_key: Callable[[int], None] | None = None):
        pygame.init()
        self.size = (width * scale, height * scale)
        self.on_key = on_key
        self.window = pygame.display.set_mode(self.size)
        pygame.display.set_caption("Code is Art")
        self.brightness = 1.0

    def push(self, frame: np.ndarray) -> None:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                raise KeyboardInterrupt
            if ev.type == pygame.KEYDOWN and self.on_key is not None and pygame.K_1 <= ev.key <= pygame.K_9:
                self.on_key(ev.key - pygame.K_1)
        surf = pygame.surfarray.make_surface(np.ascontiguousarray(frame.transpose(1, 0, 2)))
        pygame.transform.scale(surf, self.size, self.window)
        pygame.display.flip()

    def set_brightness(self, level: float) -> None:
        self.brightness = level

    def close(self) -> None:
        pygame.quit()
```

- [ ] **Step 3: Run the tests**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/test_display.py`
Expected: `4 passed`.

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`
Expected: `21 passed`, no skips.

- [ ] **Step 4: Commit**

```bash
git add show/display/__init__.py show/display/fake.py show/display/sdl.py tests/test_display.py
git commit -m "feat(show): display protocol with duck-typed config, fake and SDL backends (daemon Task 5)"
```

---

### Task 5: Raw Colorlight backend, the arcade's wall path (daemon Task 16 with its amendment)

**Files:**
- Create: `show/display/colorlight.py`
- Modify: `show/display/__init__.py` (add the `colorlight` branch)
- Test: `tests/test_colorlight.py`

**Interfaces:**
- Consumes: `make_display`, `DisplayConfig` (Task 4); `show.config.Config.colorlight_iface` (Task 2).
- Produces: `ColorlightDisplay(width: int, height: int, iface: str, sock=None)` with `push`, `set_brightness` (sends `brightness_packet(level)` and stores `.brightness`), `close`; module functions `row_packets(row: int, pixels: np.ndarray) -> list[bytes]`, `frame_packet(brightness: float) -> bytes`, `brightness_packet(level: float) -> bytes`; constants `DST_MAC`, `SRC_MAC`, `CHUNK_PIXELS = 256`. `sock` is anything with `send(bytes-like)` and `close()`; without one the constructor opens an `AF_PACKET` raw socket bound to `iface` (Linux with `CAP_NET_RAW`) or raises `OSError` where `AF_PACKET` does not exist.

Raw sockets are Linux-only, so every test injects `FakeSocket`, and the `make_display` tests replace `ColorlightDisplay` with a recorder. Nothing is skipped on the Mac. The protocol notes and the constant diff are in the module docstring; the panel check with the `rgb` pattern is a GATE B item.

- [ ] **Step 1: Write the failing tests**

`tests/test_colorlight.py`:

```python
import socket
from types import SimpleNamespace

import numpy as np
import pytest

import show.display.colorlight as colorlight
from show.config import Config
from show.display import make_display
from show.display.colorlight import (DST_MAC, SRC_MAC, ColorlightDisplay, brightness_packet,
                                     frame_packet, row_packets)


class FakeSocket:
    """Stands in for the AF_PACKET socket, which exists only on Linux."""

    def __init__(self):
        self.sent = []
        self.closed = False

    def send(self, data):
        self.sent.append(bytes(data))  # copy: push() reuses its packet buffer
        return len(self.sent[-1])

    def close(self):
        self.closed = True


def test_row_packets_chunk_512_pixels_into_two():
    pixels = np.zeros((512, 3), np.uint8)
    pixels[0] = (255, 0, 0)          # red pixel at column 0
    pixels[256] = (0, 0, 255)        # blue pixel at column 256
    pk = row_packets(5, pixels)
    assert len(pk) == 2
    header = pk[0][:14]
    assert header[:6] == DST_MAC and header[6:12] == SRC_MAC and header[12:14] == b"\x55\x00"
    payload = pk[0][14:]
    assert payload[:7] == bytes([5, 0, 0, 1, 0, 0x08, 0x88])          # row 5, offset 0, count 256
    assert payload[7:10] == bytes([255, 0, 0])                        # RGB order, as Falcon Player
    payload2 = pk[1][14:]
    assert payload2[:7] == bytes([5, 1, 0, 1, 0, 0x08, 0x88])         # offset 256
    assert payload2[7:10] == bytes([0, 0, 255])
    assert all(len(p) == 14 + 7 + 256 * 3 for p in pk)


def test_row_above_255_sets_ethertype_low_byte():
    pk = row_packets(300, np.zeros((8, 3), np.uint8))
    assert pk[0][12:14] == b"\x55\x01" and pk[0][14] == 300 & 0xFF


def test_frame_packet_matches_falcon_player():
    fp = frame_packet(0.5)
    assert fp[:12] == DST_MAC + SRC_MAC and fp[12:14] == b"\x01\x07" and len(fp) == 112
    assert fp[35] == 127 and fp[36] == 0x05 and fp[38:41] == bytes([127, 127, 127])
    assert sum(fp[14:]) == 127 * 4 + 5


def test_brightness_packet_matches_falcon_player():
    bp = brightness_packet(0.4)
    assert bp[:12] == DST_MAC + SRC_MAC and len(bp) == 77
    assert bp[12] == 0x0A and bp[13:17] == bytes([102, 102, 102, 0xFF])
    assert not any(bp[17:])
    assert brightness_packet(1.7)[13] == 255 and brightness_packet(-1.0)[13] == 0


def test_push_sends_frame_packet_then_rows():
    sock = FakeSocket()
    d = ColorlightDisplay(512, 4, "eth0", sock=sock)
    d.set_brightness(0.2)
    assert sock.sent[-1][12] == 0x0A
    d.push(np.zeros((4, 512, 3), np.uint8))
    pushed = sock.sent[1:]
    assert len(pushed) == 1 + 4 * 2
    assert pushed[0][12:14] == b"\x01\x07" and pushed[0][35] == 51
    assert all(p[12] == 0x55 for p in pushed[1:])


@pytest.mark.parametrize("width,height", [(128, 32), (64, 64), (512, 4)])
def test_push_matches_reference_encoder(width, height):
    rng = np.random.default_rng(width * height)
    sock = FakeSocket()
    d = ColorlightDisplay(width, height, "eth0", sock=sock)
    for _ in range(2):  # the second push must overwrite the first push's pixels
        frame = rng.integers(0, 256, (height, width, 3), dtype=np.uint8)
        sock.sent.clear()
        d.push(frame)
        expected = [p for y in range(height) for p in row_packets(y, frame[y])]
        assert sock.sent[1:] == expected


def test_push_rejects_a_frame_of_the_wrong_shape():
    d = ColorlightDisplay(64, 64, "eth0", sock=FakeSocket())
    with pytest.raises(ValueError, match="frame shape"):
        d.push(np.zeros((32, 128, 3), np.uint8))   # same byte count, wrong layout


def test_width_that_cannot_split_evenly_rejected():
    with pytest.raises(ValueError, match="width 257"):
        ColorlightDisplay(257, 4, "eth0", sock=FakeSocket())


def test_colorlight_set_brightness_sends_packet():
    sock = FakeSocket()
    d = ColorlightDisplay(128, 32, "eth0", sock=sock)
    d.set_brightness(0.4)
    assert sock.sent[-1] == brightness_packet(0.4)
    assert d.brightness == 0.4
    d.push(np.zeros((32, 128, 3), np.uint8))
    assert sock.sent[1] == frame_packet(0.4)
    d.close()
    assert sock.closed


def test_without_raw_sockets_a_clear_error(monkeypatch):
    monkeypatch.delattr(socket, "AF_PACKET", raising=False)
    with pytest.raises(OSError, match="Linux raw sockets"):
        ColorlightDisplay(128, 32, "eth0")


class Recorder:
    """Replaces ColorlightDisplay in make_display tests: raw sockets are Linux-only."""

    def __init__(self, width, height, iface, sock=None):
        self.args = (width, height, iface)


def test_make_display_reads_iface(monkeypatch):
    monkeypatch.setattr(colorlight, "ColorlightDisplay", Recorder)
    cfg = SimpleNamespace(width=128, height=32, backend="colorlight", sdl_scale=8,
                          ddp_host="127.0.0.1", ddp_port=4048, iface="eth9")
    assert make_display(cfg).args == (128, 32, "eth9")


def test_make_display_falls_back_to_colorlight_iface(monkeypatch):
    monkeypatch.setattr(colorlight, "ColorlightDisplay", Recorder)
    assert make_display(Config(backend="colorlight", colorlight_iface="eth3")).args == (512, 192, "eth3")
```

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/test_colorlight.py`
Expected: FAIL, a collection error with `ModuleNotFoundError: No module named 'show.display.colorlight'`.

- [ ] **Step 2: Implement the backend**

`show/display/colorlight.py`:

```python
"""Raw Ethernet driver for Colorlight 5A-75B/E receiving cards (Linux only, needs CAP_NET_RAW).

Constants diffed on 2026-09-27 against Falcon Player's src/channeloutput/ColorLight-5a-75.cpp
(master) and H. Kubota's protocol notes (hkubota.wordpress.com, 2022-01-31, updated 2022-09-29).
chubby75 documents the card's hardware, not this protocol. Every packet: destination MAC
11:22:33:44:55:66, source MAC 22:22:33:44:55:66, then a packet-type byte at offset 12 whose
first data byte shares the EtherType field at offset 13.

- 0x01 display frame, 112 bytes, EtherType 0x0107: data[21] brightness, data[22] 0x05,
  data[24..26] brightness for R, G, B (data counted from offset 14).
- 0x0A brightness, 77 bytes, EtherType 0x0A<b>: then b, b, 0xFF, zeros.
- 0x55 row data, EtherType 0x5500 | row >> 8: row & 0xFF, pixel offset (2 bytes), pixel count
  (2 bytes), 0x08, 0x88, then pixels in RGB order (Falcon Player; Kubota's panel needed BGR).

Falcon Player's loop sends each display frame packet and then the next frame's rows; push()
does the same, so the card shows a pushed frame when the next push starts. Verify the pixel
order with the rgb test pattern on the panel before trusting colours.
"""
from __future__ import annotations

import math
import socket

import numpy as np

DST_MAC = bytes.fromhex("112233445566")
SRC_MAC = bytes.fromhex("222233445566")
ETH_ROW = 0x5500
ETH_FRAME = 0x0107
ETH_BRIGHTNESS = 0x0A00
CHUNK_PIXELS = 256          # pixels per row packet; Falcon Player allows up to 497
ROW_HEADER_LEN = 14 + 7     # Ethernet header plus the 7-byte row header
FRAME_PAYLOAD_LEN = 98
BRIGHTNESS_PAYLOAD_LEN = 63


def _eth(ethertype: int) -> bytes:
    return DST_MAC + SRC_MAC + ethertype.to_bytes(2, "big")


def _level(level: float) -> int:
    return int(max(0.0, min(1.0, level)) * 255)


def _row_header(row: int, offset: int, count: int) -> bytes:
    return _eth(ETH_ROW | (row >> 8)) + bytes([row & 0xFF, offset >> 8, offset & 0xFF,
                                               count >> 8, count & 0xFF, 0x08, 0x88])


def row_packets(row: int, pixels: np.ndarray) -> list[bytes]:
    """Reference encoder for one row of (width, 3) RGB pixels; push() must match it byte for byte."""
    out = []
    for off in range(0, pixels.shape[0], CHUNK_PIXELS):
        chunk = np.ascontiguousarray(pixels[off : off + CHUNK_PIXELS], dtype=np.uint8)
        out.append(_row_header(row, off, chunk.shape[0]) + chunk.tobytes())
    return out


def frame_packet(brightness: float) -> bytes:
    b = _level(brightness)
    payload = bytearray(FRAME_PAYLOAD_LEN)
    payload[21] = b
    payload[22] = 0x05
    payload[24] = payload[25] = payload[26] = b
    return _eth(ETH_FRAME) + bytes(payload)


def brightness_packet(level: float) -> bytes:
    b = _level(level)
    payload = bytearray(BRIGHTNESS_PAYLOAD_LEN)
    payload[0] = payload[1] = b
    payload[2] = 0xFF
    return _eth(ETH_BRIGHTNESS | b) + bytes(payload)


class ColorlightDisplay:
    def __init__(self, width: int, height: int, iface: str, sock=None):
        chunks = math.ceil(width / CHUNK_PIXELS)
        if width % chunks:
            raise ValueError(f"width {width} does not split into {chunks} equal row packets")
        self.width, self.height = width, height
        self._chunk = width // chunks
        # One prebuilt packet per (row, chunk); headers are fixed, push() fills the pixels.
        self._packets = np.zeros((height, chunks, ROW_HEADER_LEN + self._chunk * 3), np.uint8)
        for y in range(height):
            for c in range(chunks):
                header = _row_header(y, c * self._chunk, self._chunk)
                self._packets[y, c, :ROW_HEADER_LEN] = np.frombuffer(header, np.uint8)
        self._pixels = self._packets[:, :, ROW_HEADER_LEN:]
        if sock is None:
            if not hasattr(socket, "AF_PACKET"):
                raise OSError("the colorlight backend needs Linux raw sockets (AF_PACKET); "
                              "use --backend sdl on this machine")
            sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
            sock.bind((iface, 0))
        self.sock = sock
        self.brightness = 1.0

    def set_brightness(self, level: float) -> None:
        self.brightness = level
        self.sock.send(brightness_packet(level))

    def push(self, frame: np.ndarray) -> None:
        if frame.shape != (self.height, self.width, 3):
            raise ValueError(f"frame shape {frame.shape} is not ({self.height}, {self.width}, 3)")
        self.sock.send(frame_packet(self.brightness))   # shows the rows sent by the previous push
        self._pixels[...] = frame.reshape(self.height, -1, self._chunk * 3)
        for packet in self._packets.reshape(-1, self._packets.shape[-1]):
            self.sock.send(packet.data)

    def close(self) -> None:
        self.sock.close()
```

`show/display/__init__.py` (the whole file; the `colorlight` branch is new):

```python
from __future__ import annotations

from typing import Callable, Protocol

import numpy as np


class DisplayConfig(Protocol):
    """Any object with these attributes can be handed to make_display.

    `iface` is the wired interface for the colorlight backend; the daemon's Config calls it
    `colorlight_iface`, and make_display reads either.
    """

    width: int
    height: int
    backend: str
    sdl_scale: int
    ddp_host: str
    ddp_port: int
    iface: str


class Display(Protocol):
    def push(self, frame: np.ndarray) -> None: ...
    def set_brightness(self, level: float) -> None: ...
    def close(self) -> None: ...


def make_display(cfg: DisplayConfig, on_key: Callable[[int], None] | None = None) -> Display:
    if cfg.backend == "fake":
        from show.display.fake import FakeDisplay
        return FakeDisplay()
    if cfg.backend == "sdl":
        from show.display.sdl import SDLDisplay
        return SDLDisplay(cfg.width, cfg.height, cfg.sdl_scale, on_key)
    if cfg.backend == "colorlight":
        from show.display.colorlight import ColorlightDisplay
        return ColorlightDisplay(cfg.width, cfg.height, getattr(cfg, "iface", None) or cfg.colorlight_iface)
    raise ValueError(f"unknown display backend {cfg.backend!r}")
```

- [ ] **Step 3: Run the tests**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/test_colorlight.py`
Expected: `14 passed`.

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`
Expected: `35 passed`, no skips.

- [ ] **Step 4: Commit**

```bash
git add show/display/colorlight.py show/display/__init__.py tests/test_colorlight.py
git commit -m "feat(show): raw Colorlight backend, packets checked against Falcon Player (daemon Task 16)"
```

---

### Task 6: DDP backend (daemon Task 15 with its amendment)

**Files:**
- Create: `show/display/ddp.py`
- Modify: `show/display/__init__.py` (add the `ddp` branch)
- Test: `tests/test_ddp.py`

**Interfaces:**
- Consumes: `make_display` (Tasks 4 and 5); `show.config.Config` (`ddp_host`, `ddp_port`).
- Produces: `DDPDisplay(width, height, host, port=4048, sock=None)` sending unscaled RGB with data type `0x0B`; `set_brightness` stores the level and logs once, on logger `show.display.ddp`, that brightness is Falcon Player's setting; `packets(data: bytes, seq: int) -> list[bytes]`.

DDP header, 10 bytes: flags (`0x40` version 1, `| 0x01` push on the last packet of a frame), sequence 1 to 15, data type `0x0B` (RGB, 8 bits per channel), destination `0x01`, 32-bit big-endian byte offset, 16-bit big-endian length; at most 1440 data bytes per packet.

- [ ] **Step 1: Write the failing tests**

`tests/test_ddp.py`:

```python
import logging
import struct

import numpy as np

from show.config import Config
from show.display import make_display
from show.display.ddp import DDPDisplay, packets


class FakeSocket:
    def __init__(self):
        self.sent = []

    def sendto(self, data, addr):
        self.sent.append((data, addr))

    def close(self):
        pass


def test_packets_split_and_flag_last():
    data = bytes(512 * 192 * 3)
    pk = packets(data, seq=3)
    assert len(pk) == 205
    flags, seq, dtype, dest, off, length = struct.unpack("!BBBBIH", pk[0][:10])
    assert (flags, seq, dtype, dest, off, length) == (0x40, 3, 0x0B, 1, 0, 1440)
    flags, _, _, _, off, length = struct.unpack("!BBBBIH", pk[-1][:10])
    assert flags == 0x41 and off == 204 * 1440 and length == 294912 - 204 * 1440
    assert sum(len(p) - 10 for p in pk) == len(data)


def test_push_does_not_scale_and_cycles_sequence():
    sock = FakeSocket()
    d = DDPDisplay(4, 1, "10.0.0.2", 4048, sock=sock)
    d.set_brightness(0.5)
    frame = np.full((1, 4, 3), 200, np.uint8)
    d.push(frame)
    data, addr = sock.sent[0]
    assert addr == ("10.0.0.2", 4048)
    assert data[10:13] == bytes([200, 200, 200])
    seqs = []
    for _ in range(16):
        d.push(frame)
        seqs.append(sock.sent[-1][0][1])
    assert seqs[0] == 2 and 15 in seqs and 0 not in seqs and seqs[-1] == 2


def test_make_display_ddp():
    d = make_display(Config(backend="ddp"))
    assert isinstance(d, DDPDisplay)
    d.close()


def test_ddp_brightness_logged_once(caplog):
    caplog.set_level(logging.INFO, logger="show.display.ddp")
    d = DDPDisplay(4, 1, "10.0.0.2", 4048, sock=FakeSocket())
    d.set_brightness(0.4)
    d.set_brightness(0.2)
    records = [r for r in caplog.records if "Falcon Player" in r.getMessage()]
    assert len(records) == 1 and d.brightness == 0.2
```

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/test_ddp.py`
Expected: FAIL, a collection error with `ModuleNotFoundError: No module named 'show.display.ddp'`.

- [ ] **Step 2: Implement the backend**

`show/display/ddp.py`:

```python
from __future__ import annotations

import logging
import socket
import struct

import numpy as np

log = logging.getLogger(__name__)

DDP_PORT = 4048
MAX_DATA = 1440
FLAG_VERSION1 = 0x40
FLAG_PUSH = 0x01
DATA_TYPE_RGB8 = 0x0B   # RGB, 8 bits per channel
DEST_DEFAULT = 0x01


def packets(data: bytes, seq: int) -> list[bytes]:
    out = []
    total = len(data)
    for off in range(0, total, MAX_DATA):
        chunk = data[off : off + MAX_DATA]
        last = off + len(chunk) >= total
        flags = FLAG_VERSION1 | (FLAG_PUSH if last else 0)
        header = struct.pack("!BBBBIH", flags, seq & 0x0F, DATA_TYPE_RGB8, DEST_DEFAULT, off, len(chunk))
        out.append(header + chunk)
    return out


class DDPDisplay:
    """Sends frames unscaled; the panel brightness is Falcon Player's output setting."""

    def __init__(self, width: int, height: int, host: str, port: int = DDP_PORT, sock=None):
        self.width, self.height = width, height
        self.addr = (host, port)
        self.sock = sock or socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.brightness = 1.0
        self._seq = 1
        self._brightness_logged = False

    def set_brightness(self, level: float) -> None:
        self.brightness = level
        if not self._brightness_logged:
            self._brightness_logged = True
            log.info("DDP sends pixels unscaled; brightness %.2f is Falcon Player's setting", level)

    def push(self, frame: np.ndarray) -> None:
        for packet in packets(np.ascontiguousarray(frame).tobytes(), self._seq):
            self.sock.sendto(packet, self.addr)
        self._seq = self._seq % 15 + 1

    def close(self) -> None:
        self.sock.close()
```

`show/display/__init__.py` (the whole file; the `ddp` branch is new):

```python
from __future__ import annotations

from typing import Callable, Protocol

import numpy as np


class DisplayConfig(Protocol):
    """Any object with these attributes can be handed to make_display.

    `iface` is the wired interface for the colorlight backend; the daemon's Config calls it
    `colorlight_iface`, and make_display reads either.
    """

    width: int
    height: int
    backend: str
    sdl_scale: int
    ddp_host: str
    ddp_port: int
    iface: str


class Display(Protocol):
    def push(self, frame: np.ndarray) -> None: ...
    def set_brightness(self, level: float) -> None: ...
    def close(self) -> None: ...


def make_display(cfg: DisplayConfig, on_key: Callable[[int], None] | None = None) -> Display:
    if cfg.backend == "fake":
        from show.display.fake import FakeDisplay
        return FakeDisplay()
    if cfg.backend == "sdl":
        from show.display.sdl import SDLDisplay
        return SDLDisplay(cfg.width, cfg.height, cfg.sdl_scale, on_key)
    if cfg.backend == "colorlight":
        from show.display.colorlight import ColorlightDisplay
        return ColorlightDisplay(cfg.width, cfg.height, getattr(cfg, "iface", None) or cfg.colorlight_iface)
    if cfg.backend == "ddp":
        from show.display.ddp import DDPDisplay
        return DDPDisplay(cfg.width, cfg.height, cfg.ddp_host, cfg.ddp_port)
    raise ValueError(f"unknown display backend {cfg.backend!r}")
```

- [ ] **Step 3: Run the tests**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/test_ddp.py`
Expected: `4 passed`.

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`
Expected: `39 passed`, no skips.

- [ ] **Step 4: Commit**

```bash
git add show/display/ddp.py show/display/__init__.py tests/test_ddp.py
git commit -m "feat(show): DDP backend with data type 0x0B, unscaled (daemon Task 15)"
```

---

### Task 7: Arcade config and calibration (core plan Task 2 with its amendment)

**Files:**
- Create: `arcade/config.py`, `arcade.toml`, `arcade/calibration.py`
- Test: `tests/arcade/test_config.py`, `tests/arcade/test_calibration.py`

**Interfaces:**
- Consumes: `arcade/__init__.py` and `tests/arcade/__init__.py` (Task 1); `make_display` reads `ArcadeConfig`'s `width`, `height`, `backend`, `sdl_scale`, `iface`, `ddp_host`, `ddp_port` (Tasks 4 to 6).
- Produces: `arcade.config.ArcadeConfig` dataclass with exactly spec 4.3's fields and defaults plus `font_path` and `fps` (listed in the code below; no `idle_seconds`), properties `size -> (width, height)` and `layout -> f"{width}x{height}"`; `load_config(path: Path | str) -> ArcadeConfig`, raising `ValueError` naming the field for unknown keys, wrong types, bad enums (`BACKENDS`, `CAMERAS`, `AUDIOS`, `LOOKS`), non-`HH:MM` night times, brightness outside (0, 1], and sizes under 8. `arcade.calibration.Calibration` (frozen dataclass: `zone: tuple[float, float, float, float]` as x0, y0, x1, y1 in camera space 0..1, `min_height: float`, `baseline_scale: float`, `static_mask: tuple[tuple[float, float, float], ...]` as (x, y, radius), `audio_floor_db: float`, `calibrated: bool`), `load_calibration(data_dir) -> Calibration` (defaults when absent; defaults plus a warning on logger `arcade` when corrupt), `save_calibration(data_dir, cal) -> None` (writes `data_dir/calibration.json` through a temp file, fsync, rename), `FILENAME = "calibration.json"`.

- [ ] **Step 1: Write the failing config tests**

`tests/arcade/test_config.py`:

```python
import dataclasses
import tomllib
from pathlib import Path

import pytest

from arcade.config import ArcadeConfig, load_config

REPO_TOML = Path(__file__).resolve().parents[2] / "arcade.toml"


def write(tmp_path, text):
    p = tmp_path / "arcade.toml"
    p.write_text(text + "\n")
    return p


def test_defaults_when_file_missing(tmp_path):
    cfg = load_config(tmp_path / "nope.toml")
    assert cfg.size == (128, 32)
    assert cfg.backend == "sdl" and cfg.sdl_scale == 8 and cfg.iface == "eth0"
    assert (cfg.ddp_host, cfg.ddp_port) == ("127.0.0.1", 4048)
    assert cfg.camera == "mediapipe" and cfg.camera_index == 0 and cfg.camera_fps == 10
    assert cfg.audio == "sounddevice" and cfg.audio_device == "" and cfg.scenario == ""
    assert cfg.mirror is True and cfg.brightness == 0.4 and cfg.gamma == 2.2 and cfg.look == "led"
    assert (cfg.apl_cap_day, cfg.apl_cap_night, cfg.night_lux) == (0.12, 0.06, 5.0)
    assert (cfg.night_start, cfg.night_end) == ("01:00", "06:00")
    assert cfg.dwell_seconds == 1.2
    assert (cfg.present_on_seconds, cfg.present_off_seconds, cfg.player_lost_seconds) == (1.0, 3.0, 0.5)
    assert (cfg.leave_seconds, cfg.inactive_seconds, cfg.max_session_seconds) == (8.0, 30.0, 180.0)
    assert cfg.exit_seconds == 3.0 and cfg.allow_record is False
    assert cfg.data_dir == Path("data") and cfg.font_path == Path("fonts/5x7.bin") and cfg.fps == 30
    assert not hasattr(cfg, "idle_seconds")


def test_values_from_file(tmp_path):
    cfg = load_config(write(tmp_path, 'width = 64\nheight = 64\nbackend = "colorlight"\niface = "eth1"\n'
                                      'camera = "replay"\nscenario = "s.jsonl"\ndata_dir = "d"\nleave_seconds = 10'))
    assert cfg.size == (64, 64) and cfg.layout == "64x64"
    assert cfg.backend == "colorlight" and cfg.iface == "eth1"
    assert cfg.camera == "replay" and cfg.scenario == "s.jsonl"
    assert cfg.data_dir == Path("d")
    assert cfg.leave_seconds == 10.0 and isinstance(cfg.leave_seconds, float)


@pytest.mark.parametrize("line,field", [('backend = "hologram"', "backend"), ('audio = "tape"', "audio"),
                                        ("brightness = 1.5", "brightness"), ("brightness = 0", "brightness"),
                                        ("brightnes = 0.2", "brightnes"), ("width = 4", "width")])
def test_bad_values_rejected(tmp_path, line, field):
    with pytest.raises(ValueError, match=field):
        load_config(write(tmp_path, line))


@pytest.mark.parametrize("line,field", [('backend = "matrix"', "backend"), ('camera = "kinect"', "camera"),
                                        ('look = "crt"', "look")])
def test_rejects_bad_enum_values(tmp_path, line, field):
    with pytest.raises(ValueError, match=field):
        load_config(write(tmp_path, line))


@pytest.mark.parametrize("line", ['night_start = "25:00"', 'night_end = "6pm"', 'night_start = "12:60"'])
def test_rejects_bad_night_time(tmp_path, line):
    with pytest.raises(ValueError, match="HH:MM"):
        load_config(write(tmp_path, line))


@pytest.mark.parametrize("line,field", [('brightness = "0.4"', "brightness"), ("width = 12.5", "width"),
                                        ('mirror = "yes"', "mirror"), ("width = true", "width")])
def test_wrong_type_rejected(tmp_path, line, field):
    with pytest.raises(ValueError, match=field):
        load_config(write(tmp_path, line))


def test_layout_name():
    assert ArcadeConfig().layout == "128x32"
    assert ArcadeConfig(width=64, height=64).layout == "64x64"


def test_default_file_in_repo_lists_every_field_with_its_default():
    keys = set(tomllib.loads(REPO_TOML.read_text()))
    assert keys == {f.name for f in dataclasses.fields(ArcadeConfig)}
    assert load_config(REPO_TOML) == ArcadeConfig()
```

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_config.py`
Expected: FAIL, a collection error with `ModuleNotFoundError: No module named 'arcade.config'`.

- [ ] **Step 2: Implement config**

`arcade/config.py`:

```python
"""ArcadeConfig: the flat arcade.toml (spec 4.3). Calibration lives in arcade/calibration.py."""
from __future__ import annotations

import dataclasses
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

BACKENDS = ("sdl", "fake", "colorlight", "ddp")
CAMERAS = ("mediapipe", "imx500", "replay", "none")
AUDIOS = ("sounddevice", "replay", "none")
LOOKS = ("plain", "led", "distance")
HHMM = re.compile(r"([01]\d|2[0-3]):[0-5]\d")


@dataclass
class ArcadeConfig:
    width: int = 128
    height: int = 32
    backend: str = "sdl"
    sdl_scale: int = 8
    iface: str = "eth0"
    ddp_host: str = "127.0.0.1"
    ddp_port: int = 4048
    camera: str = "mediapipe"
    camera_index: int = 0
    camera_fps: int = 10
    audio: str = "sounddevice"
    audio_device: str = ""
    scenario: str = ""
    mirror: bool = True
    brightness: float = 0.4
    apl_cap_day: float = 0.12
    apl_cap_night: float = 0.06
    night_start: str = "01:00"
    night_end: str = "06:00"
    night_lux: float = 5.0
    gamma: float = 2.2
    look: str = "led"
    dwell_seconds: float = 1.2
    present_on_seconds: float = 1.0
    present_off_seconds: float = 3.0
    player_lost_seconds: float = 0.5
    leave_seconds: float = 8.0
    inactive_seconds: float = 30.0
    max_session_seconds: float = 180.0
    exit_seconds: float = 3.0
    allow_record: bool = False
    data_dir: Path = Path("data")
    font_path: Path = Path("fonts/5x7.bin")
    fps: int = 30

    @property
    def size(self) -> tuple[int, int]:
        return (self.width, self.height)

    @property
    def layout(self) -> str:
        return f"{self.width}x{self.height}"


def _coerce(name: str, value, default):
    """A TOML value as the field's type. Ints are accepted for float fields; true/false only for bools."""
    if isinstance(default, Path):
        if isinstance(value, str):
            return Path(value)
    elif isinstance(default, bool):
        if isinstance(value, bool):
            return value
    elif isinstance(value, bool):
        pass
    elif isinstance(default, float) and isinstance(value, (int, float)):
        return float(value)
    elif isinstance(value, type(default)):
        return value
    kind = "a path string" if isinstance(default, Path) else type(default).__name__
    raise ValueError(f"{name} must be {kind}, got {value!r}")


def load_config(path: Path | str) -> ArcadeConfig:
    path = Path(path)
    raw = tomllib.loads(path.read_text()) if path.exists() else {}
    defaults = ArcadeConfig()
    names = {f.name for f in dataclasses.fields(ArcadeConfig)}
    unknown = sorted(set(raw) - names)
    if unknown:
        raise ValueError(f"unknown config keys: {unknown}")
    cfg = ArcadeConfig(**{k: _coerce(k, v, getattr(defaults, k)) for k, v in raw.items()})
    for name, allowed in (("backend", BACKENDS), ("camera", CAMERAS), ("audio", AUDIOS), ("look", LOOKS)):
        if getattr(cfg, name) not in allowed:
            raise ValueError(f"{name} must be one of {allowed}, got {getattr(cfg, name)!r}")
    for name in ("night_start", "night_end"):
        if not HHMM.fullmatch(getattr(cfg, name)):
            raise ValueError(f"{name} must be HH:MM (00:00 to 23:59), got {getattr(cfg, name)!r}")
    if not 0 < cfg.brightness <= 1:
        raise ValueError(f"brightness must be in (0, 1], got {cfg.brightness}")
    if cfg.width < 8 or cfg.height < 8:
        raise ValueError(f"width and height must be at least 8, got {cfg.layout}")
    return cfg
```

`arcade.toml`:

```toml
# Flat config. Every key is a field of arcade.config.ArcadeConfig, shown with its default (spec 4.3).
# Calibration results live in data_dir/calibration.json, not here.
width = 128              # 128x32 side by side (default), 64x64 stacked
height = 32
backend = "sdl"          # sdl | fake | colorlight | ddp
sdl_scale = 8
iface = "eth0"           # wired interface for the colorlight backend
ddp_host = "127.0.0.1"   # Falcon Player, if that path is ever used
ddp_port = 4048
camera = "mediapipe"     # mediapipe | imx500 | replay | none
camera_index = 0
camera_fps = 10
audio = "sounddevice"    # sounddevice | replay | none
audio_device = ""        # input device matched by name; empty means default
scenario = ""            # scenario file for the replay sources
mirror = true
brightness = 0.4         # hard ceiling: the card's brightness packet on colorlight, modelled by previews
apl_cap_day = 0.12
apl_cap_night = 0.06
night_start = "01:00"
night_end = "06:00"
night_lux = 5.0
gamma = 2.2              # what the previews and the governor model; 1.0 if the card applies gamma
look = "led"             # plain | led | distance
dwell_seconds = 1.2
present_on_seconds = 1.0
present_off_seconds = 3.0
player_lost_seconds = 0.5
leave_seconds = 8.0
inactive_seconds = 30.0
max_session_seconds = 180.0
exit_seconds = 3.0
allow_record = false     # must be true on colorlight before `arcade record` runs
data_dir = "data"
font_path = "fonts/5x7.bin"
fps = 30
```

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_config.py`
Expected: `20 passed`.

- [ ] **Step 3: Write the failing calibration tests**

`tests/arcade/test_calibration.py`:

```python
import logging

import pytest

from arcade.calibration import Calibration, load_calibration, save_calibration


def test_default_calibration(tmp_path):
    cal = load_calibration(tmp_path)
    assert cal == Calibration()
    assert cal.zone == (0.2, 0.2, 0.8, 0.8)   # the central 60 percent of the frame
    assert cal.min_height == 0.45 and cal.calibrated is False
    assert cal.static_mask == () and cal.baseline_scale == 0.0 and cal.audio_floor_db == -90.0


def test_calibration_round_trip(tmp_path):
    cal = Calibration(zone=(0.1, 0.3, 0.7, 0.95), min_height=0.5, baseline_scale=0.31,
                      static_mask=((0.12, 0.4, 0.02), (0.9, 0.1, 0.05)), audio_floor_db=-62.5, calibrated=True)
    save_calibration(tmp_path / "data", cal)
    assert load_calibration(tmp_path / "data") == cal
    assert [p.name for p in (tmp_path / "data").iterdir()] == ["calibration.json"]   # no temp file left


@pytest.mark.parametrize("text", ["", "{not json", "[]", '{"zone": [0.1, 0.2, 0.3]}',
                                  '{"zone": [0.8, 0.2, 0.2, 0.8], "min_height": 0.4, "baseline_scale": 0,'
                                  ' "static_mask": [], "audio_floor_db": -60, "calibrated": true}'])
def test_corrupt_calibration_falls_back_to_defaults(tmp_path, caplog, text):
    (tmp_path / "calibration.json").write_text(text)
    with caplog.at_level(logging.WARNING, logger="arcade"):
        assert load_calibration(tmp_path) == Calibration()
    assert "calibration.json" in caplog.text
```

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_calibration.py`
Expected: FAIL, a collection error with `ModuleNotFoundError: No module named 'arcade.calibration'`.

- [ ] **Step 4: Implement calibration**

`arcade/calibration.py`:

```python
"""Per-setup calibration (spec 6.6), stored in data_dir/calibration.json and read at startup."""
from __future__ import annotations

import dataclasses
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("arcade")

FILENAME = "calibration.json"


@dataclass(frozen=True)
class Calibration:
    zone: tuple[float, float, float, float] = (0.2, 0.2, 0.8, 0.8)   # x0, y0, x1, y1 in camera space, 0..1
    min_height: float = 0.45                 # shortest body, as a fraction of frame height, that counts in-zone
    baseline_scale: float = 0.0              # the operator's standing scale; 0.0 means not measured
    static_mask: tuple[tuple[float, float, float], ...] = ()   # static lights as (x, y, radius), 0..1
    audio_floor_db: float = -90.0
    calibrated: bool = False


def _from_json(d: dict) -> Calibration:
    zone = tuple(float(v) for v in d["zone"])
    if len(zone) != 4 or not (0.0 <= zone[0] < zone[2] <= 1.0 and 0.0 <= zone[1] < zone[3] <= 1.0):
        raise ValueError(f"zone must be x0 < x1 and y0 < y1 within 0..1, got {zone}")
    mask = tuple(tuple(float(v) for v in light) for light in d["static_mask"])
    if any(len(light) != 3 for light in mask):
        raise ValueError("static_mask entries must be (x, y, radius)")
    return Calibration(zone=zone, min_height=float(d["min_height"]), baseline_scale=float(d["baseline_scale"]),
                       static_mask=mask, audio_floor_db=float(d["audio_floor_db"]),
                       calibrated=bool(d["calibrated"]))


def load_calibration(data_dir: Path | str) -> Calibration:
    """The saved calibration, or the uncalibrated defaults when the file is absent or unreadable."""
    path = Path(data_dir) / FILENAME
    if not path.exists():
        return Calibration()
    try:
        return _from_json(json.loads(path.read_text()))
    except (OSError, ValueError, KeyError, TypeError) as e:
        log.warning("ignoring %s (%s: %s); using the uncalibrated defaults", path, type(e).__name__, e)
        return Calibration()


def save_calibration(data_dir: Path | str, cal: Calibration) -> None:
    path = Path(data_dir) / FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(FILENAME + ".tmp")
    with open(tmp, "w") as f:
        json.dump(dataclasses.asdict(cal), f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
```

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_calibration.py`
Expected: `7 passed`.

- [ ] **Step 5: Run the whole suite, then commit**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`
Expected: `66 passed`, no skips.

```bash
git add arcade/config.py arcade.toml arcade/calibration.py tests/arcade/test_config.py tests/arcade/test_calibration.py
git commit -m "feat(arcade): config and calibration (spec 4.3, 6.6)"
```

---

## Iteration verify

Run inline by the operator after Task 7, from the repo root.

1. `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest --collect-only -q | tail -1` prints `66 tests collected`.
2. `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs` prints `66 passed` with **0 skipped**. Per module: `tests/arcade/test_doctor.py` 5, `tests/test_config.py` 5, `tests/test_font.py` 7, `tests/test_display.py` 4, `tests/test_colorlight.py` 14, `tests/test_ddp.py` 4, `tests/arcade/test_config.py` 20, `tests/arcade/test_calibration.py` 7. No test may skip on the Mac: Colorlight uses fake sockets and a recorder, never `skipif`.
3. `.venv/bin/python tools/env_check.py` exits 0 and prints `PoseLandmarker VIDEO mode ran: ...`. It rewrites the versions block of `arcade/sources/README.md`; if `git diff arcade/sources/README.md` shows only the date and timing changed, discard the rewrite with `git restore arcade/sources/README.md`, and if a version changed, journal it.
4. `.venv/bin/python -m arcade doctor --require pose; echo "exit $?"` prints `pose    ok ...` and `exit 0`. Anything else fails the iteration.
5. `.venv/bin/python -m arcade doctor --require camera,mic,pose; echo "exit $?"`. Expected `exit 0`. A camera or mic `UNAVAILABLE` (macOS permission) is an owner item in the journal, not a failure; a pose failure is a failure.
6. `uv pip list --python .venv/bin/python | grep -i opencv` prints exactly one line, `opencv-contrib-python`.
7. `git log --oneline -7` shows the seven commit messages above, in order, and `git status --short` is clean apart from `docs/superpowers/workflow/` files.
