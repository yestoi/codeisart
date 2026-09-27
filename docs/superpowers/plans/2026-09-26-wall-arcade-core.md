# Wall Arcade Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The arcade framework end to end, per spec revision 3: an environment spike, the shared display foundation with the raw Colorlight backend, config and calibration, the Sensed record with player and presence, scripted actors, canvas, LED-look previews, the runner with session rules, flash governor, brightness limiter and effects, the attract director with four modes, the mirror and the doors, Paint as the first game, the headless tools, feel metrics, bots and the evidence package, and the live camera and microphone sources for the Mac and the Raspberry Pi 5.

**Architecture:** One Python process ticking at 30 Hz. Camera and audio sources run in threads and expose their latest result; the runner builds one `Sensed` record per tick, hands it to the current game, and pushes the game's canvas to a display backend shared with the show daemon. Everything a game sees is data, so tests drive games with scripted actors against a recording display and assert on `debug_state()` first and pixels second.

**Tech Stack:** Python 3.12 through uv on the Mac (`uv venv --python 3.12 .venv`; the system Python 3.14 is not used) and the Pi 5's system Python with `--system-site-packages`; numpy, pygame (SDL preview), one OpenCV (`opencv-contrib-python`), sounddevice, Pillow, pytest. Mac extra: mediapipe 1.x. Pi 5: picamera2, `python3-munkres` and `python3-scipy` from apt, and the raw Colorlight backend over the wired port to the 5A-75E.

**Spec:** `docs/superpowers/specs/2026-09-26-wall-arcade-design.md`, revision 3 (commit 44d860a). Read the "Amendments for spec revision 3" section below before any task. The nine games after Paint, the attract modes after the first four, and the three project skills (spec sections 8, 7.7 and 11) are a second plan, written after this one is executed so it can describe real files.

## Global Constraints

- Frames are numpy arrays of shape `(height, width, 3)`, dtype uint8, RGB, row-major. Every game must run at both `128x32` and `64x64`; every game test is parametrized over both.
- Brightness is never applied by scaling pixels. The runner calls `display.set_brightness(cfg.brightness)` once; the DDP backend does not scale (daemon plan amendment for Task 15). The `brightness` config value is a hard ceiling no game can raise.
- Tick rate 30 Hz; `dt` handed to games is clamped to 100 ms. The runner's clock and every game's random source are injected.
- Keypoints are normalized to 0..1 in 17-point COCO order, mirrored once at the source when `mirror` is true, never again.
- Modules that import `mediapipe`, `picamera2`, `cv2.VideoCapture` devices, or `sounddevice` do so inside the class constructor or thread, never at module import. Tests never need hardware extras.
- Tests run headless: `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy` are set in `tests/conftest.py` before pygame is imported.
- No `print` in library code; use `logging.getLogger("arcade")`.
- Commit after every task with the message given in the task.

## Amendments for spec revision 3 (apply while executing)

The spec was revised to revision 3 after the six-lens review
(`docs/superpowers/reviews/2026-09-26-arcade-adversarial-review.md`; verified corrected code in
`docs/superpowers/reviews/2026-09-26-arcade-review-lenses/05-plan.md`, cited below as "05-plan").

### How to read this plan now

The task bodies below show revision 2 code, and the spec (revision 3) overrides them wherever they differ. The
operator's writing-plans step turns each milestone slice into an iteration plan that applies the amendments below to
the task bodies it uses. Test modules are copied verbatim from either this plan or the iteration plan, and any
difference from both is a deviation the reviewer must see.

### Global Constraints, revised

These replace the first two Global Constraints bullets and add three.

- Every game declares `layouts`; its tests are parametrized over the declared layouts, and the other layout gets the
  run-and-legible tests (spec 9.1). 128x32 is the default and design layout.
- Brightness: the runner calls `display.set_brightness(cfg.brightness)` once. The Colorlight backend enforces it at
  the panel with the card's brightness packet; SDL and fake model it in the preview; DDP logs once that it is Falcon
  Player's setting. Pixels pushed to hardware are never scaled for `brightness`. The brightness limiter (spec 7.6)
  is a separate, picture-level cap that does scale frames.
- Never seed from `hash()` of a str; use `zlib.crc32` and print the seed in the assertion message.
- The test harness runs `strict=True`: game exceptions re-raise. Runner keys win in `state()`, and games must not
  use them (spec 7.1 list).
- Python 3.12 through uv on the Mac; one OpenCV distribution, `opencv-contrib-python`.

### Task 0: Environment spike

**Files:**
- Create: `pyproject.toml`, `arcade/__init__.py`, `arcade/__main__.py`, `arcade/main.py` (doctor only; Task 18 grows it), `arcade/sources/__init__.py`, `arcade/sources/README.md` (written by the tool), `tools/env_check.py`, `tests/__init__.py`, `tests/arcade/__init__.py`
- Modify: `.gitignore` (add `models/`, `data/`, `shots/`)
- Test: `tests/arcade/test_doctor.py`

**Interfaces:**
- Produces: `arcade.main.doctor(require, probes, timeout=5.0, out=None) -> int` (0 all available, 1 any unavailable, 2 unknown name); `Probe = Callable[[float], tuple[bool, str]]`; `probe_camera(timeout, index=0)`, `probe_mic(timeout, device="")`, `probe_pose(timeout, model=MODEL_PATH)`; `main(argv) -> int` with `doctor --require camera,mic,pose [--timeout S] [--camera-index N] [--audio-device NAME] [--model PATH]`; `tools/env_check.py`, which rewrites the versions block of `arcade/sources/README.md`.

Before any other task. The Mac's system Python (3.14) is not used. This task's `pyproject.toml` and venv replace
Task 1 Step 1's; the `__init__.py` files later tasks list as Create already exist.

- [ ] **Step 1: Toolchain, `pyproject.toml`, install**

```bash
uv python install 3.12 && uv venv --python 3.12 .venv && . .venv/bin/activate
```

`pyproject.toml` (the daemon's dependencies plus the arcade's, each bounded below its next major):

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
mac = ["mediapipe>=1.0,<2"]
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

Create empty `arcade/__init__.py`, `arcade/sources/__init__.py`, `tests/__init__.py`, `tests/arcade/__init__.py`;
add `models/`, `data/`, `shots/` to `.gitignore`. Then `uv pip install -e '.[dev,mac]'` and check `uv pip list |
grep -i opencv` prints exactly one line, `opencv-contrib-python`. On the Pi 5, later: `uv venv
--system-site-packages .venv` (apt's picamera2 must be visible), then `uv pip install -e '.[dev,pi]'`.

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

Run: `pytest tests/arcade/test_doctor.py -v` Expected: FAIL with `ModuleNotFoundError: No module named
'arcade.main'`

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

Run: `pytest tests/arcade/test_doctor.py -v` Expected: 5 passed

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

Run: `python tools/env_check.py` Expected: `PoseLandmarker VIDEO mode ran: ...`, and `arcade/sources/README.md`
holds the versions table. If `mp.tasks.vision` does not resolve in the installed mediapipe, use the working import
path here, in `probe_pose` and in Task 16, and record it in the README.

**SDL duplication (macOS).** opencv and pygame each bundle `libSDL2`; importing both prints objc "implemented in
both" warnings that can crash. Task 6 moves `look.py`'s blur to numpy, so only the camera source imports cv2 and
replay or no-camera runs never load both. The live Mac run with the camera still loads both; if the owner's live
smoke crashes, switch `pygame` to `pygame-ce` (same `import pygame`).

- [ ] **Step 5: Run the doctor, then commit**

Run: `python -m arcade doctor --require pose` (loop-verifiable; expected exit 0), then `python -m arcade doctor
--require camera,mic,pose`. A camera or mic permission failure becomes an owner item in the journal and the loop
continues; granting macOS permissions is the owner's.

```bash
git add pyproject.toml .gitignore arcade/__init__.py arcade/__main__.py arcade/main.py arcade/sources/__init__.py \
    arcade/sources/README.md tools/env_check.py tests/__init__.py tests/arcade/__init__.py tests/arcade/test_doctor.py
git commit -m "chore(arcade): environment spike, pinned deps, doctor"
```

### Per-task amendments

- **Task 1, foundation.** Use Task 0's `pyproject.toml` and venv, not Step 1's. Execute daemon Tasks 1, 2, 5, 16 and
  15 in that order with the daemon amendments for Tasks 1, 5, 15 and 16 (the `0x0107` frame packet before the rows,
  the prebuilt packet array, constants diffed against chubby75 and Falcon Player before the first panel test). The
  raw Colorlight backend is the arcade's primary wall path, not descope step 1. `DisplayConfig` gains `iface`;
  `make_display`'s colorlight branch passes `getattr(cfg, "iface", None) or cfg.colorlight_iface`, so the daemon's
  `Config` keeps working. `ColorlightDisplay.set_brightness` sends `brightness_packet(level)` (the daemon code
  already does); `DDPDisplay.set_brightness` stores the level and logs once "brightness is Falcon Player's setting".
  `FakeDisplay` keeps `last` and `count` as Step 3 shows. Tests: add `test_colorlight_set_brightness_sends_packet`
  (fake socket, last sent equals `brightness_packet(0.4)`), `test_make_display_reads_iface` (SimpleNamespace config
  with `iface="eth9"`, monkeypatched `ColorlightDisplay` records its arguments, because raw sockets are Linux-only),
  `test_ddp_brightness_logged_once` (caplog, two calls, one record).
- **Task 2, config.** `ArcadeConfig` has exactly the spec 4.3 fields and defaults plus `font_path` and `fps`:
  `width=128, height=32`, `backend` in `sdl|fake|colorlight|ddp`, `iface="eth0"`, `camera_fps=10`,
  `audio_device=""`, `apl_cap_day=0.12`, `apl_cap_night=0.06`, `night_start="01:00"`, `night_end="06:00"`,
  `night_lux=5.0`, `dwell_seconds=1.2`, `present_on_seconds=1.0`, `present_off_seconds=3.0`,
  `player_lost_seconds=0.5`, `leave_seconds=8`, `inactive_seconds=30`, `max_session_seconds=180`,
  `exit_seconds=3.0`, `allow_record=False`. Remove `idle_seconds`. Add `cfg.layout -> f"{width}x{height}"`.
  Enumerated fields and `HH:MM` times are validated at load. `arcade.toml` lists every field with its default. Also
  create `arcade/calibration.py` (spec 4.1, 6.6): `Calibration(zone, min_height, baseline_scale, static_mask,
  audio_floor_db, calibrated)`, `load_calibration(data_dir)` returning the defaults (zone the central 60 percent,
  `min_height=0.45`, `calibrated=False`) when the file is absent or corrupt, `save_calibration(data_dir, cal)` with
  fsync then rename. Tests: change `test_defaults_when_file_missing` to the new defaults and `not hasattr(cfg,
  "idle_seconds")`; add `test_rejects_bad_enum_values` (backend `matrix`, camera `kinect`, look `crt`),
  `test_rejects_bad_night_time` (`"25:00"`), `test_layout_name`, and in `tests/arcade/test_calibration.py`:
  `test_default_calibration`, `test_calibration_round_trip`, `test_corrupt_calibration_falls_back_to_defaults`.
- **Task 3, Sensed.** Fields exactly as spec 5; new fields default (`Body`: `vx=vy=0.0`, `scale=0.0` meaning
  "compute nose-to-mid-hip", `in_zone=True`, `zone_x=zone_y=0.5`, `seen_ago=0.0`; `Blob.in_zone=True`; `Audio` adds
  `level_smooth`, `voice_db=-90.0`, `floor_db=-90.0`, `voice`, `clap`; `Sensed` adds `camera_t`, `camera_fresh`,
  `camera_seq`, `player=None`, `player2=None`, `present=False`). Remove `Sensed.primary` and the body-box
  rasterizing in `with_motion`: `motion` is all False at wall size when empty, and `with_motion(size)` only
  resamples a grid of another shape. Helper properties per spec 5: `shoulder_mid`, `hip_mid`, `torso`, `raise_line`
  (0.3 torso above the shoulder midpoint; the nose only when both shoulders are under `MIN_CONF`), `raised_wrist`
  and `both_hands_up` against it, `cursor` (the wrist further from its hip, through `reach`), `reach(kp) -> (u, v)`
  (u across 1.5 shoulder widths each side of the shoulder midpoint; v from 1.05 torso above the shoulder midpoint,
  head plus a forearm, down to hip height; both clamped 0..1). Add `place(body, calibration) -> Body` setting
  `in_zone`, `zone_x`, `zone_y`; actors and the tracker both call it. Create `arcade/sources/mirror.py` with
  `mirror_keypoints(kps)` (x to 1 - x, index order kept, labels never swapped) and `mirror_box`. Tests: keep
  `test_body_cleans_bad_keypoints` (Review Focus 1); replace `test_raised_wrist_and_both_hands` with
  `test_raise_line_is_above_shoulders` (0.1 torso above is not raised, 0.4 is),
  `test_nose_fallback_only_without_shoulders`, `test_hooded_body_still_raises` (nose conf 0); replace
  `test_sensed_defaults_and_primary` with `test_sensed_defaults` (no `primary` attribute); add
  `test_with_motion_resamples_never_rasterizes`, `test_reach_box_corners`, `test_cursor_is_wrist_further_from_hip`,
  `test_place_uses_calibration_zone`, and in `tests/arcade/test_mirror.py` `test_mirror_flips_x_keeps_labels`,
  `test_mirror_twice_is_identity`.
- **Task 4, actors.** Per spec 6.4. Replace `_on_tick` with 05-plan S10's `_fires(t, when)` (`when - 1e-9 <= t <
  when + TICK - 1e-9`) in `claps` and `tempo` (`n = math.floor((t - start) / period + 1e-9)`). Add
  `Person.wrist(hand, y_from, y_to, seconds, at)` with y in reach-box v units, `Person.pose(name, at, seconds)`
  reading `arcade/poses.py` (`POSES: dict[str, tuple[tuple[float, float], ...]]`, 17 offsets in body-height units
  from the hip centre, at least `t_pose` and `arms_up`), `motion_rect(x0, y0, x1, y1, start, seconds)` returning a
  grid on the fixed 128x64 scenario grid, `level_ramp([(t, level), ...])`, and `scene(persons=, blobs=, motion=,
  audio=, ticks=)` that stamps `camera_t`, `camera_fresh`, `camera_seq` and calls `place()` with the default
  calibration. `degrade(scene, fps=10, latency=0.15, keypoint_dropout=0.15, jitter=0.01)` samples and holds at
  `fps`, delays by `latency`, drops and jitters keypoints by `zlib.crc32` of (tick, body id, joint), never `random`;
  `REAL_NOISE` holds those defaults until the real fixtures refit them. Festival scenes: `crowd(n)` (small
  out-of-zone bodies behind the player), `headlamps()` (out-of-zone blobs), `camp_kick(bpm)` (broadband onsets, no
  claps, voice at the floor), `wind()`, `shake(start, seconds)` (what the gated source yields: an empty grid and
  keypoint jitter 0.03). Tests: add `test_tempo_128_exactly_one_beat_per_period` (128 beats in 60 s, no gap under 14
  ticks), `test_claps_fire_exactly_once`, `test_wrist_ramp_in_reach_units`, `test_pose_from_table`,
  `test_unknown_pose_raises`, `test_motion_rect_grid`, `test_level_ramp_interpolates`,
  `test_degrade_samples_holds_and_delays`, `test_degrade_is_deterministic`, `test_crowd_is_out_of_zone`,
  `test_camp_kick_has_onsets_but_no_claps`. `test_scene_assigns_ids_and_ticks` now expects `frames[0].motion` all
  False, not None.
- **Task 5, canvas.** Apply 05-plan S4: `_i(v)` (round, clamp to plus or minus `1 << 20`, NaN, infinity or garbage
  to `-(1 << 20)`) and `_c(color)` (clamp 0..255) at the top of `pixel`, `fill_rect`, `line`, `_disc` and `blit`; in
  `line`, skip when an endpoint exceeds `4 * (width + height)`. Add `text(x, y, s, color, scale=1)` and
  `text_width(s, scale=1)` (scale 2 is 10 by 14 with 2 px strokes), `blit_rgb(sprite, x, y)` with black transparent,
  `sprite_from_rows(rows, palette) -> (h, w, 3) uint8` (`.` is black, an unknown character raises `ValueError`).
  Interface line: "Coordinates may be int or float and are rounded; colours are clamped to 0..255." Tests: add
  `test_float_coordinates_round`, `test_nan_inf_and_huge_never_raise_or_hang` (asserts each call returns within 50
  ms), `test_colours_clamped`, `test_line_with_float_endpoint_terminates`, `test_text_scale_two` (width 12 for
  `"8"`, four times the scale-1 lit count), `test_blit_rgb_black_is_transparent`, `test_sprite_from_rows_palette`.
  Step 4's expected count becomes 13.
- **Task 6, look.** `render(frame, mode, scale=8, gamma=2.2, metres=5.0)`. `distance` models spec 9.4: a Gaussian of
  sigma `metres * tan(1.5 arcmin) / 0.005` wall pixels (P5 pitch) times `scale`, plus a luminance-weighted halation
  Gaussian of three times that sigma, both built from numpy box blurs, so `look.py` never imports cv2 (the Task 0
  SDL mitigation). `led` and `plain` unchanged. `PreviewDisplay.set_brightness` forwards to the inner display and
  scales the rendered preview only. Tests: keep `test_distance_blurs` with `metres=5.0`; add
  `test_distance_blur_grows_with_metres` (spread at 10 m over spread at 2 m), `test_look_never_imports_cv2`
  (subprocess, as Task 0's import test), `test_preview_models_brightness`.
- **Task 7, game protocol, registry, scores.** `GameInfo` per spec 7.1 (`verb`, 16x16 `icon`, `layouts`, `players`,
  `exit_gesture`, `kind`, `abandon_seconds`), validated in `__post_init__`; `icon_from_rows` takes 16 rows of 16.
  `Game` gains `scores`, `SCENARIOS`, `CAPTION_KEYS`, `PHASES` (see Task 20) and `reset(size, rng, fx)`; `draw()`
  must work right after `reset()`. `RUNNER_KEYS` (spec 7.1 list) and the `fx_` prefix live in `game.py`;
  `draw_figure(canvas, body, rect, color, stroke=2)` too (the mirror and Copy Me share it). Scores per spec 7.5 and
  05-plan S7: `Scores(path | None, clock=datetime.now)`, `None` keeps everything in memory; bests keyed game then
  layout; `for_game(name, layout)` returns the view games get as `self.scores`, with `record(value, margin=0.0) ->
  bool`, `best()`, `last_night()`; bests roll over at 16:00 local time; write with fsync then rename. The spec types
  `scores` as `Scores`; the per-game view satisfies its `self.scores.record(value)`. `SessionLog(path |
  None).append(game, layout, start, duration, players, score, reason)` validates the reason against spec 7.5's six.
  Registry: `MENU_ORDER = ("copyme", "pong", "paint", "quickdraw", "dodge", "tug", "flap", "swat", "strongman",
  "freeze")`; `all_games()` imports each existing `arcade.games.<name>` with `importlib`, skips missing modules,
  logs and skips a module that raises, and reads its `GAME` attribute. Games never append to a list. Tests: replace
  `test_icon_from_rows` (16x16) and `test_registry_lookup`; add `test_menu_order_lists_the_ten_spec_games`,
  `test_discovery_skips_missing_modules`, `test_broken_module_is_logged_and_skipped` (monkeypatched
  `import_module`), `test_game_info_validates` (bad icon shape, kind, layout, needs),
  `test_scores_in_memory_never_writes`, `test_scores_per_layout`, `test_scores_roll_over_at_1600`,
  `test_scores_margin`, `test_sessions_log_appends_json_line`, `test_sessions_log_rejects_unknown_reason`.
- **Task 8, runner and harness.** Per spec 7.2. `Runner(cfg, display, font, lobby, games, seed=0, clock, sleep, log,
  scores=None, sessions=None, calibration=None, strict=False)`; `attract=` and `in_attract` go (the lobby is the
  attract). `LobbyLike` replaces `MenuLike`: a `Game` plus `request: str | None`, `set_available(names)`,
  `set_status(camera_ok, mic_ok, inputs, calibrated)`, `end_session(result)`. States LOBBY and GAME. Tick order:
  sense, build Sensed, derive `player`, `player2`, `present` (classes `PlayerLock` and `Presence` in `runner.py`),
  session rules, `update`, `draw`, `Juice.render`, `FlashGovernor.apply`, `BrightnessLimiter.apply`, `push`. Games
  get only in-zone blobs; the lobby sees all. Session rules: leave (`leave_seconds` or `abandon_seconds`, reason
  `left`), inactivity (prompt 5 s, a raised hand cancels, reason `inactive`), cap (only while an in-zone body beyond
  `info.players` waits, applied at the next tick whose `phase` is not `play`, reason `capped`), deliberate exit with
  `Hold(exit_seconds, grace=0.25)` and a runner-drawn ring only when `info.exit_gesture`, then 05-plan S2's block
  (the lobby gets no bodies, blobs or player until both hands are down). Crash guard per 05-plan B2 around
  `__init__`, `reset`, `update`, `draw` and `done`, `last_error = traceback.format_exc()`, and a static dim red
  16x16 icon fading over 0.5 s replaces the 30-tick noise glitch; a lobby that raises is replaced by a built-in
  title card until restart; `strict` re-raises (05-plan S3). `state()` per 05-plan S5 with runner keys `game, t,
  idle, attract, hidden, crashes, glitch, flash_held_ticks, player, present` and the `fx_*` keys winning. `sense()`
  reads the new `latest()` shapes (`(capture_t, bodies, blobs, motion) | None`, `(capture_t, Audio)`) and treats
  results older than 1.0 s (camera) or 0.5 s (audio) as empty and unavailable. `run_headless(cfg, font, game_cls,
  sensed_iter, seed=0, strict=True, trace=False, raw=False)` uses `Scores(None)`, `SessionLog(None)` and a
  `NullLobby`, sets `runner.game` to the launched instance, and keeps per-tick `state()` (`trace`) and pre-governor
  frames (`raw`). `helpers.run(game_cls, sensed_iter, size, font, ticks=None, seed=0, strict=True, **cfg_over)`
  returns `(frames, runner.game, runner)`, which meets spec 9.1's signature. New modules in this task:
  `arcade/flash.py` (`FlashGovernor(h, w, gamma)` per spec 7.6, prototype `FlashLimiter` in
  `.../2026-09-26-arcade-review-lenses/flashguard2.py`, plus `flash_area(frames, gamma) -> float` for tests and
  tools), `arcade/brightness.py` (`BrightnessLimiter(cfg, clock, lux=None)` with `apply`, `is_night`, `cap`; LUT
  scaling never below 0.5), `arcade/juice.py` (`Juice(rng)` per spec 8.1, one per launch, `freeze` skips `update`,
  shake as a slice copy, `fx_*` keys), `arcade/input.py` (`Edge`, `Hold(seconds, grace=0.25)` with `progress`,
  `OneEuro(min_cutoff=1.0, beta=0.007, d_cutoff=1.0)`, and Task 11's `to_wall`). Tests in `test_runner.py`: drop
  `test_idle_attract_and_presence_returns`, rewrite the exit and crash tests, add
  `test_init_reset_and_done_raises_are_guarded`, `test_crash_shows_static_dim_icon_then_lobby`,
  `test_strict_reraises`, `test_run_headless_returns_launched_instance_after_done`, `test_state_runner_keys_win`,
  `test_last_error_holds_traceback`, `test_lobby_crash_falls_back_to_title_card`,
  `test_crowd_of_six_never_steals_the_player`, `test_player_switches_after_1_3x_for_one_second`,
  `test_player_reacquired_by_position_keeps_slot`, `test_presence_hysteresis_ignores_out_of_zone`,
  `test_leave_ends_session_with_card`, `test_abandon_seconds_overrides_leave`, `test_inactivity_prompt_then_end`,
  `test_cap_only_when_someone_waits`, `test_exit_gesture_disabled_by_info`,
  `test_exit_then_hands_still_up_reaches_lobby_as_no_bodies`, `test_session_logged_with_reason`,
  `test_push_path_order`, `test_stale_camera_is_unavailable`. New modules: `test_flash.py`
  (`test_15hz_white_strobe_held_to_3_per_second`, `test_static_and_moving_sprite_pass_bit_identical`,
  `test_saturated_red_counts_double`, perf `test_governor_under_half_ms_at_128x32`), `test_brightness.py`
  (`test_frame_under_cap_passes_identical`, `test_white_frame_scaled_not_below_half`,
  `test_night_by_clock_spans_midnight`, `test_lux_overrides_clock`), `test_juice.py`
  (`test_particle_pool_capped_at_96`, `test_shake_decays_to_zero`, `test_freeze_skips_update_keeps_drawing`,
  `test_flash_rate_limited`, `test_fx_keys_in_runner_state`, perf `test_full_pool_under_half_ms`), `test_input.py`
  (`test_edge_fires_once`, `test_hold_tolerates_200ms_dropout_resets_after_300ms`,
  `test_one_euro_cuts_jitter_and_lags_under_200ms`).
- **Task 9, menu: superseded** by the attract director and doors (spec 7.3, 7.7). Create
  `arcade/attract/__init__.py`, `arcade/attract/director.py` (`Director(games, cfg, modes=None, scores=None)`
  implementing `LobbyLike`: tiers EMPTY, PASSING, NEAR, ENGAGED with spec 7.7's hysteresis; sub-states ATTRACT,
  INVITE, PLAY, CARD; the mirror within 0.5 s of stepping in; the breathing 16 px hand-up pictogram after 1.5 s; a
  raised hand requests the featured game, which rotates every 15 minutes among offerable games; the 3, 2, 1 at 5 s
  near; doors from an end card per spec 7.3 at 128x32 and 64x64, selected by `zone_x` while a hand is up; the card
  per spec 7.3; every 20 s at EMPTY a 5 s demo replay or tonight's best card; blobs never select while a body
  is present and body centre never selects; `debug_state` keys per spec 7.7), `arcade/attract/modes/__init__.py` (`ModeInfo(name, needs, calm,
  layouts, duration=(40, 150))`, the `Mode` protocol with `attend(focus)` and `settled()`, `MODE_ORDER` with the
  thirteen spec 7.7 names, the same guarded discovery as games) and four modes, `watcher.py`, `echo.py`, `warp.py`,
  `contours.py`, as described in the review's section 5 table. Survives from Task 9: the dwell accumulation (now
  decaying over 0.3 s instead of resetting), `_perimeter` for the door fill ring, `_reason_unavailable` (now also
  checking `layouts`), and the two-pixel status glyph. Dropped: the twelve tiles, `TITLE_SLOT`, the title band,
  `DIM_COLOR`, `cursor_of` from raw frame coordinates, and the body-centre and blob cursor fallbacks. Review Focus 3
  moves here: the director lays out at 64x32, 96x48 and 128x64. Tests (`test_director.py`):
  `test_standing_still_10s_never_selects_a_door` (in INVITE it launches only the featured game, through the 3, 2, 1
  at 5 s, the spec's ten-second guarantee), `test_crowd_of_six_never_steals_the_player`,
  `test_walk_stand_raise_passes_attract_invite_play`, `test_mirror_within_half_second`, `test_pictogram_after_1_5s`,
  `test_no_mode_repeats_back_to_back`, `test_no_luminance_step_over_0_1_across_substate_change`,
  `test_hands_still_up_after_exit_select_nothing`, `test_door_fill_decays_over_0_3s`,
  `test_unofferable_games_never_shown` (needs and layouts), `test_camera_down_favours_no_input_modes`,
  `test_lays_out_at_64x32_96x48_128x64`, `test_blob_never_selects_with_body_present`. `test_modes.py`, parametrized over discovered modes and 128x32, 64x64:
  debug keys `lit_fraction`, `apl`, `focus` present, `flash_area` at most 0.10, APL under `apl_cap_day`; plus
  `test_watcher_pupil_follows_walk`, `test_echo_black_3s_after_motion_stops`, `test_warp_speeds_up_under_loud`,
  `test_contours_lit_fraction_0_05_to_0_2`.
- **Task 10, paint.** `GAME = Paint`; `GameInfo(verb="PAINT", layouts both, players=1, kind="toy",
  abandon_seconds=45, needs={"blobs"})`. Only `in_zone` blobs paint; each tracked blob draws a segment from its last
  position (skipped above a quarter of the wall width) in its halo colour; a raised wrist paints through
  `body.cursor` when no blob is present; trails fade over 20 s; after 60 s, or 10 s without input, a 5 s gallery
  freeze of the fullest frame, then `done()` (starting values). Key `idle` becomes `since_input`; keys `phase`,
  `active`, `lit`, `since_input`, `brush_xy`; `CAPTION_KEYS = ("phase", "lit", "since_input")`; `SCENARIOS`
  canonical, idle_body, nobody, fail (no light), win (full gallery). No registry edit. Tests: add
  `test_out_of_zone_blob_never_paints`, `test_fast_blob_draws_connected_segment`, `test_wrist_paints_without_blob`,
  `test_gallery_freeze_then_done`, `test_session_survives_8s_empty_ends_at_45s` (through the runner). Step 4's count
  is 6 plus the new tests (05-plan: the sized tests run twice).
- **Task 11, puppet: superseded** as a game; it becomes the director's mirror layer. Its drawing moves to
  `game.draw_figure` (Task 7) and its uniform `to_wall(body, rect)` to `arcade/input.py` (Task 8). No
  `arcade/games/puppet.py`, not in `MENU_ORDER`. Its tests move into `test_director.py` as
  `test_mirror_draws_2px_figure_in_player_colour`, `test_two_bodies_two_colours`,
  `test_low_confidence_limbs_skipped`, and into `test_input.py` as `test_to_wall_is_uniform`. Tasks 13, 14 and 18
  that name `puppet` use `paint`.
- **Task 12, scenarios.** Files are `.jsonl.gz` (`gzip.open` in text mode) with a header record first: `{"kind":
  "header", "version": 1, "type": "sensed" | "raw", "fps", "grid": [128, 64], "script", "cues": [[t, "RAISE RIGHT
  HAND"], ...], "created", "git"}`. Sensed records store `motion` as base64 `np.packbits` on the fixed 128x64 grid,
  resampled on replay. Raw records (spec 6.3): capture time, raw detections, a 160x120 grey frame as base64 bytes,
  plus a 16 kHz WAV whose RIFF header is written with `struct` (the privacy test forbids the `wave` module in
  `arcade/`). Replay returns the new `latest()` shapes; raw replay runs `FrameFeatures` and `BodyTracker` (after
  Tasks 15 and 16). Tests: keep the garbage-line test (Review Focus 4); add `test_gz_round_trip_with_header`,
  `test_header_cues_readable`, `test_motion_packed_on_128x64_resampled_to_wall`, `test_raw_record_round_trip`
  (detections, frame bytes, WAV length from its header), `test_sensed_line_has_only_schema_fields`.
- **Task 13, contact sheets.** Per spec 9.4 and 05-plan S9: a provenance header band (git short sha, dirty flag,
  game, size, look, seed, scenario); refuse an all-black run unless `--allow-black`, naming the game's `needs`; cap
  sheets at 1,536 px wide (fewer columns, then smaller scale); `--look both` (default) writes `<stem>-plain.png` and
  `<stem>-led.png`; `--flash-report` prints `flash_area` of the raw frames and the mean picture level; each cell
  captioned `#30 1.00s` plus its `CAPTION_KEYS` from `run_headless(trace=True)`; `--scenario NAME` resolves
  `game.SCENARIOS[NAME]`, else a file; `--ticks` is honoured with `--scenario` (it was ignored); `--audio` is
  rejected unless the evaluated script returns an `Audio`; prints frames, non-black count, final `runner.state()`
  and `ScenarioReader.skipped`. Tests: replace `max() > 0` with `test_cells_match_render` (each cell region equals
  `render(frame)`); add `test_header_has_provenance`, `test_all_black_refused_unless_allowed`,
  `test_width_capped_at_1536`, `test_both_looks_written`, `test_flash_report_prints`,
  `test_scenario_name_from_game`, `test_ticks_honoured_with_scenario`, `test_audio_without_call_rejected`.
- **Task 14, REPL.** Per spec 9.4 and 05-plan S9: `--log PATH` appends each verb and reply as JSON lines; `hand`
  must be `left|right|both|none` and `blob` has 2 or 5 parts, else an error; `x=0.3,0.7` makes one body per value;
  `pose=NAME`, `motion=x0,y0,x1,y1`; `beat=` builds `tempo(bpm, start=t0)` for the whole step; every `step` reply
  carries `"input": {"bodies", "hand", "blobs", "pose", "motion", "beat"}`; `launch`, `lobby` (`menu` kept as an
  alias) and `reset` clear `display.last`, and `shot` refuses with `error: no frame since the last launch, lobby or
  reset; step 1 first`; `log` prints `runner.last_error`. The Session builds the runner with the `Director`.
  `tools/repl_to_test.py LOG OUT.py` turns a log into a pytest module replaying the verbs through `Session` and
  asserting each recorded reply's `game`, `phase` and `score`. Tests: replace `test_menu_dwell_via_steps` with
  `test_hand_up_in_lobby_starts_featured_game`; add `test_unknown_hand_is_error`,
  `test_blob_with_three_parts_is_error`, `test_step_echoes_input`, `test_two_bodies`, `test_pose_verb`,
  `test_motion_verb`, `test_beat_fires_every_15_ticks_over_step`, `test_shot_refuses_stale_frame`,
  `test_log_verb_shows_traceback`, `test_log_file_written`, `test_repl_to_test_generates_passing_test`.
- **Task 15, blobs and motion.** Per spec 6.1 and 5, on the 160x120 stream: a light source is value at or above 220
  whose 3 px halo has saturation 0.5 or more; hue from the halo; colour from `cv2.mean` over the component's
  bounding box with its mask; components over 0.5 percent of the frame rejected; a `StaticMask` hides a blob still
  for 5 s until it moves; `Blob.in_zone` from the calibration zone. `motion_grid`: 5x5 blur, divide by the frame
  median, threshold, cell fill 0.2, more than 35 percent of cells returns an empty grid and increments `shakes`,
  crop to the zone at the wall's aspect, then downsample. Tests: replace the old blob tests with
  `test_small_saturated_red_is_a_red_blob`, `test_large_lamp_rejected`,
  `test_white_core_without_saturated_halo_rejected`, `test_static_blob_masked_after_5s_unmasked_on_move`,
  `test_out_of_zone_blob_flagged`, `test_uniform_brightness_step_gives_no_motion`,
  `test_shake_returns_empty_and_counts`, `test_motion_zone_crop_maps_to_wall_cell`, perf
  `test_features_under_3ms_at_160x120`.
- **Task 16, camera base and tracker.** MediaPipe runs on the unflipped frame and `mirror_keypoints` flips once;
  drop `cv2.flip`. Inference is paced to `camera_fps`. `ThreadedCamera` stamps each result with the capture clock,
  `latest()` returns `None` past 1.0 s and `available` stays False until a fresh result, a `step()` returning `None`
  holds the last result, and `close()` sets stop, joins the thread, then releases the capture and the landmarker.
  `BodyTracker` per spec 5: anchor on the shoulder midpoint, then nose, then hips; constant-velocity prediction from
  capture timestamps; global assignment on distance plus scale difference through `assign(cost)` (scipy's
  `linear_sum_assignment` when importable, exhaustive search for up to six otherwise; Task 19 reuses it); coast 300
  ms emitting `seen_ago`; drop after 0.5 s; never reuse an id; One Euro on every keypoint; `vx`, `vy`, `scale`; and
  `place()`. Review Focus 2 becomes: "Two people of the same height cross at the same depth, one hiding the other
  for three frames. Their ids must not swap." Tests: replace `test_tracker_keeps_ids_when_two_people_cross` with
  `test_ids_survive_same_height_crossing_with_occlusion` (10 fps, y 0.5 for both, one detection for the three
  crossing frames); replace `test_tracker_orders_by_confidence_and_handles_gaps` with
  `test_coast_300ms_then_drop_at_0_5s`, `test_ids_never_reused`, `test_velocity_from_irregular_timestamps`,
  `test_one_euro_smooths_keypoints`; add `test_stale_result_is_none_and_unavailable`, `test_step_none_holds_last`,
  `test_close_joins_before_release`, `test_raised_right_hand_gives_right_wrist_x_over_half` (unflipped landmarks
  through the parser and mirror), and the hardware-marked `test_mediapipe_runs_on_clip` (a five-second clip built
  from a public MediaPipe sample image that `tools/fetch_models.py` fetches, URL verified at implementation time;
  skipped without mediapipe; the doctor is the gate).
- **Task 17, audio.** Per spec 5 and 6.2: a callback fills a 2 s ring buffer at 16 kHz mono and stamps its time; per
  block, a 512-point FFT gives `voice_db` (300 Hz to 3.4 kHz, dBFS, no gain), `floor_db` (rolling 30 s 90th
  percentile), `voice = clamp((voice_db - floor_db) / 30)`, `clap` (2 to 6 kHz spectral-flux onset, crest factor
  over 4, 12 dB over the floor), `level` with its slow gain, `level_smooth` (50 ms attack, 300 ms release), `onset`,
  `beat`, `bpm`. Windows are seconds, updated per block, never per tick; `latest()` returns `(capture_t, Audio)` and
  the runner applies 0.5 s staleness. `audio_device` selects by name. The first second of exact zeros logs once that
  macOS microphone permission is probably denied and sets `available = False`. Tests: add
  `test_kick_plus_pink_noise_gives_no_claps_in_20s` (125 bpm), `test_claps_12db_over_floor_caught_90_percent`,
  `test_voice_db_is_absolute`, `test_floor_is_30s_90th_percentile`, `test_level_smooth_attack_release`,
  `test_features_independent_of_block_size`, `test_exact_zeros_warn_once_and_unavailable`,
  `test_latest_carries_capture_time`; keep the bpm test.
- **Task 18, sources and CLI.** Keep Task 0's `doctor` and its tests; `run` becomes the default command, with
  `--require camera,mic,pose` refusing to start after five seconds. Add `calibrate` (spec 6.6 as a `Calibrator`
  state machine driven by Sensed, writing `calibration.json`), `record --script NAME --i-have-consent [--raw]
  [--with-motion]` (refused without consent; refused on `colorlight` unless `allow_record`; `--raw` always refused
  on `colorlight`; 3, 2, 1 then the red REC glyph and a seconds counter on the wall for the whole recording; motion
  dropped unless `--with-motion`; cues written to the header), and `stats` (per game: sessions, median duration, end
  reasons). `main` builds `Runner(cfg, display, font, Director(all_games(), cfg, scores=scores), all_games(),
  scores=scores, sessions=SessionLog(cfg.data_dir / "sessions.jsonl"), calibration=load_calibration(cfg.data_dir))`.
  `--backend` accepts `colorlight`. `tools/latency_probe.py` (spec 9.4) lands here at interface level: flash a
  square, count pushes until the camera reports the blob. Tests: add
  `test_run_require_exits_nonzero_without_camera`, `test_calibrate_with_actors_writes_zone`,
  `test_record_requires_consent`, `test_record_refused_on_colorlight_without_allow_record`,
  `test_raw_refused_on_colorlight`, `test_record_script_writes_cues`, `test_record_drops_motion_by_default`,
  `test_rec_glyph_on_every_recorded_tick`, `test_stats_summarises_sessions`,
  `test_main_builds_runner_with_director`; the replay test launches `paint`.
- **Task 19, IMX500 on the Pi 5.** `sudo apt install imx500-all python3-picamera2 python3-munkres python3-scipy`.
  Before importing picamera2's HigherHRNet postprocess, install a `munkres` shim in `sys.modules` whose
  `Munkres().compute` calls `assign()` (Task 16), and truncate each output tensor to the top 8 candidates per joint.
  `FrameRate` from `camera_fps`; `step()` returns `None` without an output tensor; normalise by the model input
  size, never by picamera2's boxes; `mirror_keypoints`, not `cv2.flip`; `close()` joins, then `picam2.close()`.
  Parsers are pluggable (`PARSERS = {"higherhrnet": ..., "yolo11n-pose": ...}`, a constructor argument, not a config
  field). Exposure and white balance lock after a 3 s warm-up and re-converge after 30 s without bodies; `lux` from
  metadata feeds the brightness limiter. Pi 5 target: `AmbientCapabilities=CAP_NET_RAW` for the Colorlight socket,
  the wired port dedicated to the card, the RTC battery fitted. Tests: add `test_munkres_shim_matches_assign`,
  `test_truncates_to_top8_per_joint`, `test_parse_normalises_by_input_size`, `test_missing_tensor_returns_none`,
  `test_parser_registry`, and the shared `test_raised_right_hand_gives_right_wrist_x_over_half` fixture through this
  parser.
- **Task 20, generic game tests.** Per spec 9.1 and 9.2. Seeds: `[zlib.crc32(f"{name}:{layout}:{i}".encode()) for i
  in range(5)]`, printed on failure. `random_mix` is 05-plan B1's, extended to add `motion_rect` when `"motion" in
  needs`. Sizes: every declared layout plus 96x48. Soak runs under `degrade` and with `hostile_mix` (five bodies,
  eight blobs, keypoints at 0 and 1, confidence-0 limbs, flickering presence, short both-hands-up), raises nothing,
  draws a non-black frame, and reaches every phase in the game's `PHASES` (a class attribute, default `("play",)`,
  added because spec 9.2's "every declared phase" needs a declaration). Counterfactual: `actors.Script` records each
  `Person` call, clap and blob as an event and `build(drop=...)` omits one; frames must diverge by `RESPONSE_PX =
  12` within `LATENCY_TICKS = 2` (spec 11), overridable per game with a comment. Also `_xy` lit on every tick of
  every scenario, flash (raw frames under `claps` at 12 Hz, `tempo(180)` and an alternating motion grid have
  `flash_area` at most 0.10), namespacing (no key in `RUNNER_KEYS` or starting `fx_`), and budget (`BUDGET_MS =
  float(os.environ.get("ARCADE_TICK_BUDGET_MS", "2.0"))`, the whole `runner.tick` through `run_headless` with
  `RecordingDisplay(keep_all=False)`, mean under the budget and p95 under twice it, 300 ticks). A collection hook in
  `tests/arcade/conftest.py` fails unless each declared layout of each game has at least three items in
  `test_<game>.py`. Privacy (spec 6.5) is `tests/arcade/test_privacy.py` here: `test_no_forbidden_calls` tokenizes
  every `arcade/**/*.py` (comments and strings excluded) and fails on the names `imwrite`, `imencode`,
  `VideoWriter`, `wave`, `savez`, on `np.save` and on `.save` attribute access;
  `test_scenario_lines_hold_only_sensed_fields` encodes every actor scene and every festival scene.
- **Tasks 21 to 23 (new, interface level; the iteration plan writes their code and tests).**
  - **Task 21, feel metrics.** Create `arcade/feel.py` (`measure(game_cls, layout, seeds) -> dict` computing spec
    9.3's metrics from `SCENARIOS`, counterfactual runs and traces) and `arcade/feel_budgets.toml` (per `kind`; a
    game override needs an `override_reason` key beside it, since TOML drops comments). `pytest -m feel` asserts the
    budgets. Tests assert a spy game that follows the player's x passes fidelity and response, a screensaver that
    ignores input fails both, and an override without a reason is rejected.
  - **Task 22, bots.** Create `arcade/bots.py` (`Bot` protocol `(debug_state, t) -> actor spec` with
    `reaction_ticks` and position noise; `play(game_cls, bot, seed, layout, ticks)` closed loop; `win_rate(game_cls,
    bot, seeds=20)`). Every game module exports `BOTS = {"good": ..., "lazy": ...}`. Tests assert determinism under
    a seed, that reaction delay is honoured, and that on a target spy game `good` beats `lazy` beats no input.
  - **Task 23, feel table and evidence.** Create `tools/arcade_feel.py` (prints the feel table for a game and
    layout) and `tools/arcade_evidence.py --iteration N --games changed` (spec 9.6; "changed" from `git diff
    --name-only` since the last evidence commit; GIF at most 6 s and 300 KB). Tests run it for paint into a
    temporary directory and assert the file set, the GIF caps, the README's first line pattern, and that unchanged
    games are not regenerated.

### Spec drift already known

05-plan's Minor list named three places where the spec disagreed with the plan's names. Revision 3 already uses the
plan's names, so keep them: `scene(...)` (not `combine`), `--person` on the contact sheet tool (not `--actors`), and
games that keep their own buffer blit it (no "kept canvas").

### Done when (revision 3)

Loop-verifiable:

- `pytest` passes on the Mac with no hardware attached, including `-m perf` and `-m feel`, and the journal records
  the collected and skipped counts.
- `python tools/env_check.py` has written `arcade/sources/README.md`, and `python -m arcade doctor --require pose`
  exits 0.
- `python tools/arcade_shot.py --game paint --scenario canonical --size 128x32 --out shots/paint.png` writes
  non-black plain and LED sheets with provenance headers, and the same at 64x64.
- Headless, the director takes a walk, a stand and a raised hand from ATTRACT through INVITE to the featured game at
  128x32 and 64x64, and runs with the mirror at 64x32.
- Paint passes the soak, counterfactual, `_xy`, flash, namespacing and budget tests, and the layout collection hook
  is active.
- `python tools/arcade_play.py --game paint --log probe.jsonl` answers validated verbs, and `tools/repl_to_test.py`
  turns the log into a passing test.
- `python tools/arcade_evidence.py --iteration 1 --games paint` writes a complete package.
- The privacy tests pass.

Owner-verified:

- `python -m arcade doctor --require camera,mic,pose` exits 0 on the Mac with permissions granted.
- Live smoke, `python -m arcade --backend sdl --camera mediapipe`, at both layouts: the mirror appears within half a
  second, a raised hand starts a game, walking away returns to attract, and both hands for 3 s exits. Recorded in
  `docs/superpowers/workflow/live-smoke.md`.
- The first real fixtures (`empty-room`, `walk-in-stand-leave`, `door-point`, `exit-gesture`) are recorded and their
  cue assertions pass.
- Pi 5 day: Colorlight constants verified with the `rgb` pattern, the IMX500 parser chosen, and
  `ARCADE_TICK_BUDGET_MS=20` perf numbers committed to `docs/superpowers/workflow/evidence/pi-perf.md`.
- The second plan (nine games, nine more attract modes, project skills) can be written against the real `Game`,
  actors, director and tools.

## Review Focus

1. A pose model returns a keypoint outside 0..1 or NaN. `Body` must clamp coordinates and set that keypoint's confidence to 0, never raise or draw off-canvas. Test in Task 3.
2. Two people cross paths in front of the camera. Their ids must not swap when their tracks stay a body-width apart vertically. Test in Task 16.
3. A wall size that is neither 128x32 nor 64x64 (a future four-panel 128x64, or 96x48 from mismatched config). The menu must lay out without raising and the canvas must clip. Test in Task 9.
4. A scenario file with a truncated or garbage line. Replay skips the line with a warning and never raises into the runner. Test in Task 12.
5. A camera thread that dies mid-session. The source reports unavailable, `latest()` keeps returning the empty result, and the runner keeps ticking. Test in Task 16 (thread base) and Task 8 (runner survives a raising source).

---

## File Structure

```
pyproject.toml                       (modified) packages show* and arcade*, new deps and extras  (rev 3: created in Task 0)
arcade.toml                          default arcade config
show/display/__init__.py             (modified) DisplayConfig protocol, make_display duck-typed
show/display/fake.py                 (modified per amendment) last, count
show/display/ddp.py                  data type 0x0B, no scaling
show/display/colorlight.py           daemon Task 16, the arcade's wall path; set_brightness sends the packet  (new, rev 3)
arcade/__init__.py
arcade/__main__.py                   python -m arcade
arcade/config.py                     ArcadeConfig, load_config
arcade/calibration.py                Calibration, load_calibration, save_calibration  (new, rev 3)
arcade/sensed.py                     Keypoint, Body, Blob, Audio, Sensed, COCO constants, SKELETON
arcade/canvas.py                     Canvas drawing over a frame
arcade/look.py                       gamma LUT, render(frame, mode, scale, gamma)
arcade/preview.py                    PreviewDisplay wrapping SDLDisplay with a look mode
arcade/game.py                       GameInfo, Game protocol, icon_from_rows
arcade/input.py                      Edge, Hold, OneEuro, to_wall  (new, rev 3)
arcade/juice.py                      shared effects, one instance per launch  (new, rev 3)
arcade/flash.py                      FlashGovernor, flash_area  (new, rev 3)
arcade/brightness.py                 BrightnessLimiter and the night schedule  (new, rev 3)
arcade/poses.py                      POSES in body-relative units  (new, rev 3)
arcade/bots.py                       Bot protocol, play, win_rate (Task 22)  (new, rev 3)
arcade/feel.py                       feel metrics (Task 21)  (new, rev 3)
arcade/feel_budgets.toml             per-kind feel budgets (Task 21)  (new, rev 3)
arcade/attract/__init__.py           (new, rev 3)
arcade/attract/director.py           Director: tiers, modes, mirror, invite, doors, cards  (new, rev 3)
arcade/attract/modes/__init__.py     ModeInfo, Mode protocol, MODE_ORDER, discovery  (new, rev 3)
arcade/attract/modes/<name>.py       watcher, echo, warp, contours in this plan  (new, rev 3)
arcade/scores.py                     Scores persistence
arcade/headless.py                   RecordingDisplay, run_headless
arcade/runner.py                     Runner
arcade/menu.py                       Menu  (superseded, rev 3: arcade/attract/director.py)
arcade/games/__init__.py             registry: GAMES, get_game, all_games  (rev 3: MENU_ORDER, importlib discovery, guarded imports)
arcade/games/paint.py                Paint
arcade/games/puppet.py               Puppet  (superseded, rev 3: the director's mirror layer)
arcade/sources/__init__.py           make_sources(cfg, size)
arcade/sources/camera.py             CameraSource protocol, NoCamera, ThreadedCamera, BodyTracker
arcade/sources/mirror.py             mirror_keypoints, mirror_box  (new, rev 3)
arcade/sources/README.md             versions from tools/env_check.py; source decisions  (new, rev 3)
arcade/sources/audio.py              AudioSource protocol, NoAudio, AudioFeatures, SoundDeviceAudio
arcade/sources/actors.py             Person, make_keypoints, moving_blob, silence, claps, tempo, loud, scene
arcade/sources/scenario.py           encode, decode, ScenarioReader, ScenarioWriter
arcade/sources/replay.py             ReplayStream, ReplayCamera, ReplayAudio, open_replay
arcade/sources/record.py             record(camera, audio, path, size, seconds, fps)
arcade/sources/blobs.py              find_blobs, motion_grid, FrameFeatures
arcade/sources/pose_mediapipe.py     MP_TO_COCO, landmarks_to_keypoints, box_of, MediaPipeCamera
arcade/sources/pose_imx500.py        parse_higherhrnet, IMX500Camera
arcade/main.py                       CLI
tools/arcade_shot.py                 contact sheets
tools/arcade_play.py                 step-verb REPL
tools/fetch_models.py                downloads the MediaPipe model
tools/env_check.py                   Task 0 environment spike  (new, rev 3)
tools/repl_to_test.py                REPL log to pytest case  (new, rev 3)
tools/latency_probe.py               camera-to-wall latency with a mirror  (new, rev 3)
tools/arcade_feel.py                 feel table (Task 23)  (new, rev 3)
tools/arcade_evidence.py             evidence package (Task 23)  (new, rev 3)
tests/arcade/conftest.py             font, size fixtures
tests/arcade/helpers.py              make_cfg, run, StubMenu
tests/arcade/test_*.py               one per module, plus test_all_games.py (soak and budget)
tests/arcade/fixtures/real/          owner-recorded .jsonl.gz fixtures (spec 9.5)  (new, rev 3)
```

---

### Task 1: Foundation from the show daemon plan

**Files:**
- Create: everything named in daemon plan Tasks 1, 2, 5 and 15 (`docs/superpowers/plans/2026-09-22-show-daemon.md`)
- Modify: `pyproject.toml`, `show/display/__init__.py`, `show/display/fake.py`, `show/display/ddp.py`, `tests/test_display.py`, `tests/test_ddp.py`

**Interfaces:**
- Produces: `show.font.Font` with `Font.load(path)`, `font.atlas() -> np.ndarray (256, 8, 6) bool`, constants `CELL_W = 6`, `CELL_H = 8`; `show.display.Display` protocol (`push`, `set_brightness`, `close`); `show.display.DisplayConfig` protocol; `make_display(cfg, on_key=None)`; `FakeDisplay` with `.last`, `.count`, `.brightness`, `.closed`; `SDLDisplay(width, height, scale, on_key)`; `DDPDisplay(width, height, host, port, sock=None)`.

Execute daemon plan Tasks 1, 2, 5 and 15 in order, exactly as written there, with the changes below. Read the daemon plan's "Amendments" section first; only the amendments for Tasks 1, 5 and 15 apply here.

- [ ] **Step 1: Daemon Task 1 with this `pyproject.toml`**

Use this file instead of the one in the daemon plan (it adds the arcade package, its dependencies and extras; everything else is the daemon's):

```toml
[project]
name = "codeisart-show"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pyte>=0.8.2",
    "numpy>=1.26",
    "pygame>=2.5",
    "sdnotify>=0.3",
    "opencv-python>=4.9",
    "sounddevice>=0.4.6",
    "Pillow>=10",
]

[project.optional-dependencies]
pi = ["gpiozero>=2.0", "lgpio"]
mac = ["mediapipe>=0.10.14"]
dev = ["pytest>=8"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["show*", "arcade*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
markers = ["perf: timing budget tests"]
```

Apply the daemon amendment for Task 1 (the extra `Config` fields; remove `matrix_multiplexing`). Create the venv with Python 3.12 on the Mac: `python3.12 -m venv .venv && . .venv/bin/activate && pip install -e '.[dev,mac]'`. On the Pi, later: `python3 -m venv --system-site-packages .venv` so apt's `python3-picamera2` is visible, then `pip install -e '.[dev,pi]'`.

Run: `pytest tests/test_config.py -v`
Expected: 4 passed

- [ ] **Step 2: Daemon Task 2 (font) as written**

Run: `pytest tests/test_font.py -v`
Expected: all passed, and `fonts/5x7.bin` exists and is committed.

- [ ] **Step 3: Daemon Task 5 with the duck-typed config and the fake display amendment**

Use these files in place of the daemon plan's `show/display/__init__.py` and `show/display/fake.py`. `sdl.py` is unchanged.

`show/display/__init__.py`:

```python
from __future__ import annotations

from typing import Callable, Protocol

import numpy as np


class DisplayConfig(Protocol):
    """Any object with these attributes can be handed to make_display."""

    width: int
    height: int
    backend: str
    sdl_scale: int
    ddp_host: str
    ddp_port: int


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
    if cfg.backend == "ddp":
        from show.display.ddp import DDPDisplay
        return DDPDisplay(cfg.width, cfg.height, cfg.ddp_host, cfg.ddp_port)
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

Replace the daemon plan's `tests/test_display.py` with:

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
    with pytest.raises(ValueError):
        make_display(Config(backend="hologram"))


def test_make_display_accepts_any_config_object():
    cfg = SimpleNamespace(width=64, height=64, backend="fake", sdl_scale=8,
                          ddp_host="127.0.0.1", ddp_port=4048)
    assert isinstance(make_display(cfg), FakeDisplay)
```

Run: `pytest tests/test_display.py -v`
Expected: 4 passed

- [ ] **Step 4: Daemon Task 15 (DDP) with its amendment**

In the daemon plan's `show/display/ddp.py` set `DATA_TYPE_RGB8 = 0x0B` and make `push` send `frame.tobytes()` with no scaling:

```python
    def push(self, frame: np.ndarray) -> None:
        for packet in packets(np.ascontiguousarray(frame).tobytes(), self._seq):
            self.sock.sendto(packet, self.addr)
        self._seq = self._seq % 15 + 1
```

The `ddp` branch of `make_display` is already present from Step 3. Adjust the daemon plan's tests: in `test_packets_split_and_flag_last` expect `dtype == 0x0B`; in `test_push_scales_brightness_and_cycles_sequence` rename to `test_push_does_not_scale_and_cycles_sequence` and assert `data[10:13] == bytes([200, 200, 200])`.

Run: `pytest tests/ -v`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore show show.toml fonts tools/extract_glcdfont.py tests
git commit -m "feat: show daemon foundation (config, font, display protocol, DDP) shared with the arcade"
```

---

### Task 2: Arcade config

**Files:**
- Create: `arcade/__init__.py`, `arcade/config.py`, `arcade.toml`
- Test: `tests/__init__.py` (create if the daemon tasks did not), `tests/arcade/__init__.py`, `tests/arcade/test_config.py`

**Interfaces:**
- Produces: `ArcadeConfig` dataclass (fields below), `load_config(path: Path | str) -> ArcadeConfig`, `cfg.size -> (width, height)`.

Two fields beyond the spec's table are needed by later tasks and are added here: `font_path` (the daemon's 5x7 font) and `fps` (30).

- [ ] **Step 1: Write the failing tests**

`tests/__init__.py` and `tests/arcade/__init__.py`: empty files, so tests can import `tests.arcade.helpers`.

`tests/arcade/test_config.py`:

```python
from pathlib import Path

import pytest

from arcade.config import ArcadeConfig, load_config


def test_defaults_when_file_missing(tmp_path):
    cfg = load_config(tmp_path / "nope.toml")
    assert cfg.size == (64, 64)
    assert cfg.backend == "sdl" and cfg.camera == "mediapipe" and cfg.audio == "sounddevice"
    assert cfg.look == "led" and cfg.gamma == 2.2 and cfg.brightness == 0.4
    assert cfg.mirror is True and cfg.fps == 30
    assert cfg.font_path == Path("fonts/5x7.bin")


def test_values_from_file(tmp_path):
    p = tmp_path / "arcade.toml"
    p.write_text('width = 128\nheight = 32\nbackend = "ddp"\ncamera = "replay"\nscenario = "s.jsonl"\ndata_dir = "d"\n')
    cfg = load_config(p)
    assert cfg.size == (128, 32)
    assert cfg.backend == "ddp" and cfg.camera == "replay" and cfg.scenario == "s.jsonl"
    assert cfg.data_dir == Path("d")


@pytest.mark.parametrize("line", ['backend = "hologram"', 'camera = "kinect"', 'audio = "tape"',
                                  'look = "crt"', 'brightness = 1.5', 'brightnes = 0.2'])
def test_bad_values_rejected(tmp_path, line):
    p = tmp_path / "arcade.toml"
    p.write_text(line + "\n")
    with pytest.raises(ValueError):
        load_config(p)


def test_default_file_in_repo_loads():
    cfg = load_config(Path(__file__).resolve().parents[2] / "arcade.toml")
    assert isinstance(cfg, ArcadeConfig)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/arcade/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arcade'`

- [ ] **Step 3: Implement config**

`arcade/__init__.py`: empty file.

`arcade/config.py`:

```python
from __future__ import annotations

import dataclasses
import tomllib
from dataclasses import dataclass
from pathlib import Path

BACKENDS = ("sdl", "fake", "ddp")
CAMERAS = ("mediapipe", "imx500", "replay", "none")
AUDIOS = ("sounddevice", "replay", "none")
LOOKS = ("plain", "led", "distance")


@dataclass
class ArcadeConfig:
    width: int = 64
    height: int = 64
    backend: str = "sdl"
    sdl_scale: int = 8
    ddp_host: str = "127.0.0.1"
    ddp_port: int = 4048
    camera: str = "mediapipe"
    camera_index: int = 0
    audio: str = "sounddevice"
    scenario: str = ""
    mirror: bool = True
    brightness: float = 0.4
    gamma: float = 2.2
    look: str = "led"
    dwell_seconds: float = 1.0
    idle_seconds: float = 60.0
    exit_seconds: float = 1.5
    data_dir: Path = Path("data")
    font_path: Path = Path("fonts/5x7.bin")
    fps: int = 30

    @property
    def size(self) -> tuple[int, int]:
        return (self.width, self.height)


def load_config(path: Path | str) -> ArcadeConfig:
    path = Path(path)
    raw = tomllib.loads(path.read_text()) if path.exists() else {}
    names = {f.name for f in dataclasses.fields(ArcadeConfig)}
    unknown = sorted(set(raw) - names)
    if unknown:
        raise ValueError(f"unknown config keys: {unknown}")
    for key in ("data_dir", "font_path"):
        if key in raw:
            raw[key] = Path(raw[key])
    cfg = ArcadeConfig(**raw)
    for name, allowed in (("backend", BACKENDS), ("camera", CAMERAS), ("audio", AUDIOS), ("look", LOOKS)):
        if getattr(cfg, name) not in allowed:
            raise ValueError(f"{name} must be one of {allowed}, got {getattr(cfg, name)!r}")
    if not 0 < cfg.brightness <= 1:
        raise ValueError("brightness must be in (0, 1]")
    if cfg.width < 8 or cfg.height < 8:
        raise ValueError("width and height must be at least 8")
    return cfg
```

`arcade.toml`:

```toml
# Flat config. Every key is a field of arcade.config.ArcadeConfig.
width = 64
height = 64
backend = "sdl"          # sdl | fake | ddp
sdl_scale = 8
ddp_host = "127.0.0.1"
ddp_port = 4048
camera = "mediapipe"     # mediapipe | imx500 | replay | none
camera_index = 0
audio = "sounddevice"    # sounddevice | replay | none
scenario = ""
mirror = true
brightness = 0.4         # hard ceiling, set on the display, never in software
gamma = 2.2              # what the previews model; 1.0 if the card applies gamma itself
look = "led"             # plain | led | distance
dwell_seconds = 1.0
idle_seconds = 60
exit_seconds = 1.5
data_dir = "data"
font_path = "fonts/5x7.bin"
fps = 30
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/arcade/test_config.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add arcade/__init__.py arcade/config.py arcade.toml tests/__init__.py tests/arcade
git commit -m "feat(arcade): config"
```

---

### Task 3: The Sensed record

**Files:**
- Create: `arcade/sensed.py`
- Test: `tests/arcade/test_sensed.py`

**Interfaces:**
- Produces: constants `NOSE, LEFT_EYE, RIGHT_EYE, LEFT_EAR, RIGHT_EAR, LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_ELBOW, RIGHT_ELBOW, LEFT_WRIST, RIGHT_WRIST, LEFT_HIP, RIGHT_HIP, LEFT_KNEE, RIGHT_KNEE, LEFT_ANKLE, RIGHT_ANKLE` (0..16), `KEYPOINT_NAMES`, `SKELETON` (pairs of indices); `Keypoint(x, y, conf=1.0)`; `Body(id, box, keypoints)` with `.nose`, `.left_wrist`, `.right_wrist`, `.raised_wrist`, `.both_hands_up`, `.center`, `.height`, `.confidence`; `Blob(x, y, size, color)`; `Audio(level=0, peak=0, onset=False, beat=False, bpm=None)`; `Sensed(t, bodies=(), blobs=(), motion=None, audio=Audio())` with `.primary` and `.with_motion(size)`; `rasterize_boxes(bodies, size) -> np.ndarray`.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_sensed.py`:

```python
import math

import numpy as np
import pytest

from arcade.sensed import (LEFT_WRIST, NOSE, RIGHT_WRIST, SKELETON, Audio, Blob, Body, Keypoint,
                           Sensed, rasterize_boxes)


def kps(**over):
    pts = [Keypoint(0.5, 0.2 + i * 0.04) for i in range(17)]
    for idx, kp in over.items():
        pts[int(idx)] = kp
    return tuple(pts)


def test_body_requires_17_keypoints():
    with pytest.raises(ValueError):
        Body(1, (0, 0, 1, 1), tuple(Keypoint(0, 0) for _ in range(5)))


def test_body_cleans_bad_keypoints():
    pts = kps(**{str(LEFT_WRIST): Keypoint(1.7, -0.2, 0.9), str(RIGHT_WRIST): Keypoint(math.nan, 0.5, 0.9)})
    b = Body(1, (0, 0, 1, 1), pts)
    assert b.left_wrist == Keypoint(1.0, 0.0, 0.0)
    assert b.right_wrist.conf == 0.0 and b.right_wrist.x == 0.0


def test_raised_wrist_and_both_hands():
    b = Body(1, (0.3, 0.1, 0.7, 0.9), kps())
    assert b.raised_wrist is None and not b.both_hands_up
    up = kps(**{str(LEFT_WRIST): Keypoint(0.4, 0.05), str(RIGHT_WRIST): Keypoint(0.6, 0.1)})
    b = Body(1, (0.3, 0.1, 0.7, 0.9), up)
    assert b.raised_wrist == Keypoint(0.4, 0.05) and b.both_hands_up
    low_conf = kps(**{str(LEFT_WRIST): Keypoint(0.4, 0.05, 0.1)})
    assert Body(1, (0.3, 0.1, 0.7, 0.9), low_conf).raised_wrist is None
    assert b.center == (0.5, 0.5) and b.height == pytest.approx(0.8)
    assert b.nose == b.keypoints[NOSE]


def test_sensed_defaults_and_primary():
    s = Sensed(t=1.0)
    assert s.bodies == () and s.blobs == () and s.motion is None and s.audio == Audio()
    assert s.primary is None
    b = Body(2, (0, 0, 1, 1), kps())
    assert Sensed(0.0, bodies=(b,)).primary is b


def test_with_motion_rasterizes_boxes_and_keeps_existing():
    b = Body(1, (0.25, 0.5, 0.75, 1.0), kps())
    s = Sensed(0.0, bodies=(b,)).with_motion((8, 4))
    assert s.motion.shape == (4, 8) and s.motion.dtype == bool
    assert s.motion[2:, 2:6].all() and not s.motion[:2].any()
    given = np.ones((4, 8), bool)
    assert Sensed(0.0, motion=given).with_motion((8, 4)).motion is given
    wrong = np.ones((2, 2), bool)
    assert Sensed(0.0, motion=wrong).with_motion((8, 4)).motion.shape == (4, 8)


def test_skeleton_indices_valid():
    assert all(0 <= a < 17 and 0 <= b < 17 for a, b in SKELETON)
    assert Blob(0.1, 0.2, 0.05, (255, 0, 0)).color == (255, 0, 0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/arcade/test_sensed.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arcade.sensed'`

- [ ] **Step 3: Implement**

`arcade/sensed.py`:

```python
from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass, field

import numpy as np

(NOSE, LEFT_EYE, RIGHT_EYE, LEFT_EAR, RIGHT_EAR, LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_ELBOW,
 RIGHT_ELBOW, LEFT_WRIST, RIGHT_WRIST, LEFT_HIP, RIGHT_HIP, LEFT_KNEE, RIGHT_KNEE, LEFT_ANKLE,
 RIGHT_ANKLE) = range(17)

KEYPOINT_NAMES = ("nose", "left_eye", "right_eye", "left_ear", "right_ear", "left_shoulder",
                  "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist",
                  "left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle")

SKELETON = ((LEFT_SHOULDER, LEFT_ELBOW), (LEFT_ELBOW, LEFT_WRIST), (RIGHT_SHOULDER, RIGHT_ELBOW),
            (RIGHT_ELBOW, RIGHT_WRIST), (LEFT_SHOULDER, RIGHT_SHOULDER), (LEFT_SHOULDER, LEFT_HIP),
            (RIGHT_SHOULDER, RIGHT_HIP), (LEFT_HIP, RIGHT_HIP), (LEFT_HIP, LEFT_KNEE),
            (LEFT_KNEE, LEFT_ANKLE), (RIGHT_HIP, RIGHT_KNEE), (RIGHT_KNEE, RIGHT_ANKLE),
            (NOSE, LEFT_SHOULDER), (NOSE, RIGHT_SHOULDER))

MIN_CONF = 0.3


@dataclass(frozen=True)
class Keypoint:
    x: float
    y: float
    conf: float = 1.0


def _clean(kp: Keypoint) -> Keypoint:
    x, y, conf = kp.x, kp.y, kp.conf
    bad = any(v is None or math.isnan(v) for v in (x, y, conf))
    if bad:
        return Keypoint(0.0, 0.0, 0.0)
    return Keypoint(min(1.0, max(0.0, x)), min(1.0, max(0.0, y)),
                    0.0 if not 0.0 <= x <= 1.0 or not 0.0 <= y <= 1.0 else min(1.0, max(0.0, conf)))


@dataclass(frozen=True)
class Body:
    id: int
    box: tuple[float, float, float, float]
    keypoints: tuple[Keypoint, ...]

    def __post_init__(self):
        if len(self.keypoints) != 17:
            raise ValueError(f"a body has 17 keypoints, got {len(self.keypoints)}")
        object.__setattr__(self, "keypoints", tuple(_clean(k) for k in self.keypoints))

    @property
    def nose(self) -> Keypoint:
        return self.keypoints[NOSE]

    @property
    def left_wrist(self) -> Keypoint:
        return self.keypoints[LEFT_WRIST]

    @property
    def right_wrist(self) -> Keypoint:
        return self.keypoints[RIGHT_WRIST]

    @property
    def raised_wrist(self) -> Keypoint | None:
        """The higher wrist if it is above the nose and confident, else None."""
        best = None
        for w in (self.left_wrist, self.right_wrist):
            if w.conf >= MIN_CONF and w.y < self.nose.y and (best is None or w.y < best.y):
                best = w
        return best

    @property
    def both_hands_up(self) -> bool:
        return all(w.conf >= MIN_CONF and w.y < self.nose.y for w in (self.left_wrist, self.right_wrist))

    @property
    def center(self) -> tuple[float, float]:
        x0, y0, x1, y1 = self.box
        return ((x0 + x1) / 2, (y0 + y1) / 2)

    @property
    def height(self) -> float:
        return self.box[3] - self.box[1]

    @property
    def confidence(self) -> float:
        return sum(k.conf for k in self.keypoints) / 17


@dataclass(frozen=True)
class Blob:
    x: float
    y: float
    size: float
    color: tuple[int, int, int]


@dataclass(frozen=True)
class Audio:
    level: float = 0.0
    peak: float = 0.0
    onset: bool = False
    beat: bool = False
    bpm: float | None = None


def rasterize_boxes(bodies: tuple[Body, ...], size: tuple[int, int]) -> np.ndarray:
    w, h = size
    grid = np.zeros((h, w), dtype=bool)
    for b in bodies:
        x0, y0, x1, y1 = b.box
        c0, c1 = int(x0 * w), max(int(x0 * w) + 1, int(math.ceil(x1 * w)))
        r0, r1 = int(y0 * h), max(int(y0 * h) + 1, int(math.ceil(y1 * h)))
        grid[max(r0, 0):min(r1, h), max(c0, 0):min(c1, w)] = True
    return grid


@dataclass(frozen=True, eq=False)
class Sensed:
    t: float
    bodies: tuple[Body, ...] = ()
    blobs: tuple[Blob, ...] = ()
    motion: np.ndarray | None = None
    audio: Audio = field(default_factory=Audio)

    @property
    def primary(self) -> Body | None:
        return self.bodies[0] if self.bodies else None

    def with_motion(self, size: tuple[int, int]) -> "Sensed":
        w, h = size
        if self.motion is not None and self.motion.shape == (h, w):
            return self
        return dataclasses.replace(self, motion=rasterize_boxes(self.bodies, size))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/arcade/test_sensed.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add arcade/sensed.py tests/arcade/test_sensed.py
git commit -m "feat(arcade): Sensed input record with body helpers"
```

---

### Task 4: Actors

**Files:**
- Create: `arcade/sources/__init__.py` (empty for now), `arcade/sources/actors.py`
- Test: `tests/arcade/test_actors.py`

**Interfaces:**
- Consumes: `Keypoint`, `Body`, `Blob`, `Audio`, `Sensed` and the COCO constants from Task 3.
- Produces: `TICK = 1/30`; `make_keypoints(cx, cy, h, left_up=False, right_up=False, conf=1.0) -> tuple[Keypoint, ...]`; `body_box(keypoints) -> tuple`; `Person(x=0.5, y=0.55, height=0.6, id=None)` with chainable `.walk(x_to, seconds, at=None)`, `.raise_hand(at, seconds=0.5, hand="right")`, `.both_hands_up(at, seconds)`, `.jump(at, height=0.15, seconds=0.6)`, `.leave(at)`, `.arrive(at)`, and `.present(t) -> bool`, `.body_at(t, id) -> Body`; blob scripts `moving_blob(x0, y0, x1, y1, seconds, color=(255,255,255), size=0.03, start=0.0) -> Callable[[float], Blob | None]`; audio scripts `silence()`, `claps(times)`, `tempo(bpm, start=0.0)`, `loud(level)` each `-> Callable[[float], Audio]`; `scene(persons=(), blobs=(), audio=None, ticks=90) -> Iterator[Sensed]`.

The spec (6.4) lists actors as functions; here they are methods on `Person` so one body can walk and raise a hand at once. `pose(named)` waits for the hole-in-the-wall game in the second plan.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_actors.py`:

```python
import pytest

from arcade.sensed import LEFT_WRIST, NOSE, RIGHT_WRIST
from arcade.sources.actors import (TICK, Person, claps, loud, make_keypoints, moving_blob, scene,
                                   silence, tempo)


def test_make_keypoints_is_a_standing_figure():
    kps = make_keypoints(0.5, 0.5, 0.6)
    assert len(kps) == 17
    assert kps[NOSE].y < kps[LEFT_WRIST].y
    up = make_keypoints(0.5, 0.5, 0.6, right_up=True)
    assert up[RIGHT_WRIST].y < up[NOSE].y and up[LEFT_WRIST].y > up[NOSE].y


def test_person_walks_and_holds_position():
    p = Person(0.1).walk(0.9, seconds=2.0)
    assert p.body_at(0.0, 0).center[0] == pytest.approx(0.1, abs=0.02)
    assert p.body_at(1.0, 0).center[0] == pytest.approx(0.5, abs=0.02)
    assert p.body_at(5.0, 0).center[0] == pytest.approx(0.9, abs=0.02)


def test_person_chained_walks_start_where_the_last_ended():
    p = Person(0.2).walk(0.6, 1.0).walk(0.2, 1.0)
    assert p.body_at(1.0, 0).center[0] == pytest.approx(0.6, abs=0.02)
    assert p.body_at(2.0, 0).center[0] == pytest.approx(0.2, abs=0.02)


def test_hands_and_jump_and_presence():
    p = Person().raise_hand(at=1.0, seconds=0.5).both_hands_up(at=3.0, seconds=1.0).jump(at=5.0, height=0.2)
    assert p.body_at(0.5, 0).raised_wrist is None
    assert p.body_at(1.2, 0).raised_wrist is not None and not p.body_at(1.2, 0).both_hands_up
    assert p.body_at(3.5, 0).both_hands_up
    standing = p.body_at(4.0, 0).nose.y
    assert p.body_at(5.3, 0).nose.y < standing - 0.1
    q = Person().leave(at=2.0)
    assert q.present(1.9) and not q.present(2.1)
    r = Person().arrive(at=2.0)
    assert not r.present(1.9) and r.present(2.1)


def test_scene_assigns_ids_and_ticks():
    frames = list(scene(persons=[Person(0.2), Person(0.8)], ticks=3))
    assert len(frames) == 3
    assert [b.id for b in frames[0].bodies] == [0, 1]
    assert frames[1].t == pytest.approx(TICK)
    assert frames[0].motion is None


def test_blob_and_audio_scripts():
    b = moving_blob(0.0, 0.5, 1.0, 0.5, seconds=2.0, color=(255, 0, 0))
    assert b(-0.1) is None and b(2.1) is None
    assert b(1.0).x == pytest.approx(0.5) and b(1.0).color == (255, 0, 0)
    assert silence()(3.0).level == 0.0
    c = claps([1.0, 2.0])
    hits = [i for i in range(90) if c(i * TICK).onset]
    assert len(hits) == 2
    t = tempo(120)
    beats = [i for i in range(90) if t(i * TICK).beat]
    assert beats == [0, 15, 30, 45, 60, 75]
    assert t(0.1).bpm == 120
    assert loud(0.9)(0.0).level == 0.9
    frames = list(scene(blobs=[b], audio=c, ticks=60))
    assert frames[30].blobs[0].x == pytest.approx(0.5, abs=0.01)
    assert frames[30].audio.onset
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/arcade/test_actors.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arcade.sources'`

- [ ] **Step 3: Implement actors**

`arcade/sources/__init__.py`: empty file for now (Task 18 fills it).

`arcade/sources/actors.py`:

```python
"""Scripted synthetic input for tests and tools. Deterministic: no randomness, no wall clock."""
from __future__ import annotations

from typing import Callable, Iterable, Iterator

from arcade.sensed import (LEFT_ANKLE, LEFT_EAR, LEFT_ELBOW, LEFT_EYE, LEFT_HIP, LEFT_KNEE,
                           LEFT_SHOULDER, LEFT_WRIST, NOSE, RIGHT_ANKLE, RIGHT_EAR, RIGHT_ELBOW,
                           RIGHT_EYE, RIGHT_HIP, RIGHT_KNEE, RIGHT_SHOULDER, RIGHT_WRIST, Audio,
                           Blob, Body, Keypoint, Sensed)

TICK = 1 / 30


def make_keypoints(cx: float, cy: float, h: float, left_up: bool = False, right_up: bool = False,
                   conf: float = 1.0) -> tuple[Keypoint, ...]:
    """A standing figure centred at (cx, cy) with total height h, coordinates normalized."""

    def p(dx: float, dy: float) -> Keypoint:
        return Keypoint(cx + dx * h, cy + dy * h, conf)

    pts: list[Keypoint | None] = [None] * 17
    pts[NOSE] = p(0.0, -0.45)
    pts[LEFT_EYE], pts[RIGHT_EYE] = p(-0.03, -0.47), p(0.03, -0.47)
    pts[LEFT_EAR], pts[RIGHT_EAR] = p(-0.06, -0.46), p(0.06, -0.46)
    pts[LEFT_SHOULDER], pts[RIGHT_SHOULDER] = p(-0.12, -0.30), p(0.12, -0.30)
    pts[LEFT_ELBOW] = p(-0.16, -0.45) if left_up else p(-0.16, -0.15)
    pts[RIGHT_ELBOW] = p(0.16, -0.45) if right_up else p(0.16, -0.15)
    pts[LEFT_WRIST] = p(-0.15, -0.60) if left_up else p(-0.18, 0.0)
    pts[RIGHT_WRIST] = p(0.15, -0.60) if right_up else p(0.18, 0.0)
    pts[LEFT_HIP], pts[RIGHT_HIP] = p(-0.08, 0.0), p(0.08, 0.0)
    pts[LEFT_KNEE], pts[RIGHT_KNEE] = p(-0.08, 0.22), p(0.08, 0.22)
    pts[LEFT_ANKLE], pts[RIGHT_ANKLE] = p(-0.08, 0.45), p(0.08, 0.45)
    return tuple(pts)  # type: ignore[arg-type]


def body_box(keypoints: Iterable[Keypoint]) -> tuple[float, float, float, float]:
    xs = [k.x for k in keypoints]
    ys = [k.y for k in keypoints]
    clamp = lambda v: min(1.0, max(0.0, v))
    return (clamp(min(xs) - 0.02), clamp(min(ys) - 0.02), clamp(max(xs) + 0.02), clamp(max(ys) + 0.02))


class Person:
    """A scripted body. Every method returns self so scripts chain."""

    def __init__(self, x: float = 0.5, y: float = 0.55, height: float = 0.6, id: int | None = None):
        self.x0, self.y0, self.h, self.id = x, y, height, id
        self._moves: list[tuple[float, float, float, float]] = []
        self._hands: list[tuple[float, float, str]] = []
        self._jumps: list[tuple[float, float, float]] = []
        self._arrive = 0.0
        self._leave: float | None = None

    def _x_at(self, t: float) -> float:
        x = self.x0
        for t0, t1, xa, xb in self._moves:
            if t >= t1:
                x = xb
            elif t0 <= t < t1:
                x = xa + (xb - xa) * (t - t0) / (t1 - t0)
        return x

    def walk(self, x_to: float, seconds: float, at: float | None = None) -> "Person":
        t0 = (self._moves[-1][1] if self._moves else 0.0) if at is None else at
        self._moves.append((t0, t0 + seconds, self._x_at(t0), x_to))
        return self

    def raise_hand(self, at: float, seconds: float = 0.5, hand: str = "right") -> "Person":
        self._hands.append((at, at + seconds, hand))
        return self

    def both_hands_up(self, at: float, seconds: float) -> "Person":
        self._hands.append((at, at + seconds, "both"))
        return self

    def jump(self, at: float, height: float = 0.15, seconds: float = 0.6) -> "Person":
        self._jumps.append((at, seconds, height))
        return self

    def leave(self, at: float) -> "Person":
        self._leave = at
        return self

    def arrive(self, at: float) -> "Person":
        self._arrive = at
        return self

    def present(self, t: float) -> bool:
        return t >= self._arrive and (self._leave is None or t < self._leave)

    def body_at(self, t: float, id: int) -> Body:
        left = right = False
        for t0, t1, hand in self._hands:
            if t0 <= t < t1:
                left = left or hand in ("left", "both")
                right = right or hand in ("right", "both")
        lift = 0.0
        for at, seconds, height in self._jumps:
            if at <= t < at + seconds:
                u = (t - at) / seconds
                lift = max(lift, height * 4 * u * (1 - u))
        kps = make_keypoints(self._x_at(t), self.y0 - lift, self.h, left, right)
        return Body(self.id if self.id is not None else id, body_box(kps), kps)


BlobScript = Callable[[float], Blob | None]
AudioScript = Callable[[float], Audio]


def moving_blob(x0: float, y0: float, x1: float, y1: float, seconds: float,
                color: tuple[int, int, int] = (255, 255, 255), size: float = 0.03,
                start: float = 0.0) -> BlobScript:
    def script(t: float) -> Blob | None:
        if t < start or t > start + seconds:
            return None
        u = (t - start) / seconds if seconds > 0 else 1.0
        return Blob(x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, size, color)
    return script


def silence() -> AudioScript:
    return lambda t: Audio()


def loud(level: float) -> AudioScript:
    return lambda t: Audio(level=level, peak=level)


def _on_tick(t: float, when: float) -> bool:
    return abs(t - when) < TICK / 2


def claps(times: list[float]) -> AudioScript:
    def script(t: float) -> Audio:
        hit = any(_on_tick(t, c) for c in times)
        return Audio(level=0.8 if hit else 0.05, peak=1.0 if hit else 0.05, onset=hit)
    return script


def tempo(bpm: float, start: float = 0.0) -> AudioScript:
    period = 60.0 / bpm

    def script(t: float) -> Audio:
        n = round((t - start) / period)
        hit = t >= start - TICK / 2 and _on_tick(t, start + n * period)
        return Audio(level=0.6 if hit else 0.3, peak=0.9 if hit else 0.3, onset=hit, beat=hit, bpm=bpm)
    return script


def scene(persons: Iterable[Person] = (), blobs: Iterable[BlobScript] = (),
          audio: AudioScript | None = None, ticks: int = 90) -> Iterator[Sensed]:
    persons = list(persons)
    blobs = list(blobs)
    audio = audio or silence()
    for i in range(ticks):
        t = i * TICK
        bodies = tuple(p.body_at(t, idx) for idx, p in enumerate(persons) if p.present(t))
        present_blobs = tuple(b for b in (s(t) for s in blobs) if b is not None)
        yield Sensed(t=t, bodies=bodies, blobs=present_blobs, motion=None, audio=audio(t))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/arcade/test_actors.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add arcade/sources tests/arcade/test_actors.py
git commit -m "feat(arcade): scripted actors for deterministic input"
```

---

### Task 5: Canvas

**Files:**
- Create: `arcade/canvas.py`
- Test: `tests/arcade/conftest.py`, `tests/arcade/test_canvas.py`

**Interfaces:**
- Consumes: `Font`, `CELL_W`, `CELL_H` from `show.font`.
- Produces: `Canvas(width, height, font)` with `.frame` (the `(h, w, 3)` uint8 array), `.width`, `.height`, `.size`, `clear(color=(0,0,0))`, `pixel(x, y, color)`, `line(x0, y0, x1, y1, color)`, `rect(x, y, w, h, color)`, `fill_rect(x, y, w, h, color)`, `circle(cx, cy, r, color)`, `fill_circle(cx, cy, r, color)`, `blit(mask, x, y, color)`, `text(x, y, s, color) -> int`, `text_width(s) -> int`. All coordinates are integer wall pixels; drawing off the edge clips and never raises.
- Test fixtures: `font5x7` (session, the real font) and `size` (parametrized `(128, 32)` and `(64, 64)`).

- [ ] **Step 1: Write the fixtures and the failing tests**

`tests/arcade/conftest.py`:

```python
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from show.font import Font

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def font5x7() -> Font:
    return Font.load(ROOT / "fonts" / "5x7.bin")


@pytest.fixture(params=[(128, 32), (64, 64)], ids=["128x32", "64x64"])
def size(request) -> tuple[int, int]:
    return request.param
```

`tests/arcade/test_canvas.py`:

```python
import numpy as np

from arcade.canvas import Canvas

RED = (255, 0, 0)


def lit(c: Canvas) -> int:
    return int((c.frame.max(axis=2) > 0).sum())


def test_new_canvas_is_black_and_sized(font5x7, size):
    c = Canvas(*size, font5x7)
    assert c.frame.shape == (size[1], size[0], 3) and c.frame.dtype == np.uint8
    assert c.size == size and lit(c) == 0


def test_pixel_and_clipping(font5x7):
    c = Canvas(16, 8, font5x7)
    c.pixel(3, 2, RED)
    c.pixel(-1, 0, RED)
    c.pixel(16, 8, RED)
    assert lit(c) == 1 and tuple(c.frame[2, 3]) == RED


def test_rects_and_clear(font5x7):
    c = Canvas(16, 8, font5x7)
    c.fill_rect(2, 1, 4, 3, RED)
    assert lit(c) == 12
    c.clear()
    c.rect(0, 0, 16, 8, RED)
    assert lit(c) == 2 * 16 + 2 * 6
    c.fill_rect(10, 4, 100, 100, RED)
    assert lit(c) == 2 * 16 + 2 * 6 + (6 * 4 - 6 - 3)


def test_line_and_circles(font5x7):
    c = Canvas(16, 16, font5x7)
    c.line(0, 0, 15, 15, RED)
    assert lit(c) == 16 and tuple(c.frame[7, 7]) == RED
    c.clear()
    c.fill_circle(8, 8, 3, RED)
    n_fill = lit(c)
    assert 25 <= n_fill <= 37 and tuple(c.frame[8, 8]) == RED
    c.clear()
    c.circle(8, 8, 3, RED)
    assert 12 <= lit(c) < n_fill and tuple(c.frame[8, 8]) == (0, 0, 0)
    c.circle(0, 0, 40, RED)


def test_text_uses_font_and_clips(font5x7):
    c = Canvas(32, 8, font5x7)
    assert c.text_width("AB") == 12
    w = c.text(0, 0, "A", RED)
    assert w == 6 and lit(c) > 5
    a = c.frame.copy()
    c.clear()
    c.text(30, 0, "A", RED)
    assert lit(c) < lit_of(a)
    c.clear()
    c.text(0, 0, "☃", RED)
    assert lit(c) > 0


def lit_of(frame: np.ndarray) -> int:
    return int((frame.max(axis=2) > 0).sum())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/arcade/test_canvas.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arcade.canvas'`

- [ ] **Step 3: Implement canvas**

`arcade/canvas.py`:

```python
from __future__ import annotations

import numpy as np

from show.font import CELL_H, CELL_W, Font

Color = tuple[int, int, int]


class Canvas:
    """Integer-pixel drawing over an (h, w, 3) uint8 frame. Everything clips, nothing raises."""

    def __init__(self, width: int, height: int, font: Font):
        self.width, self.height = width, height
        self.font = font
        self.frame = np.zeros((height, width, 3), dtype=np.uint8)

    @property
    def size(self) -> tuple[int, int]:
        return (self.width, self.height)

    def clear(self, color: Color = (0, 0, 0)) -> None:
        self.frame[:] = color

    def pixel(self, x: int, y: int, color: Color) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.frame[y, x] = color

    def fill_rect(self, x: int, y: int, w: int, h: int, color: Color) -> None:
        x0, y0 = max(x, 0), max(y, 0)
        x1, y1 = min(x + w, self.width), min(y + h, self.height)
        if x0 < x1 and y0 < y1:
            self.frame[y0:y1, x0:x1] = color

    def rect(self, x: int, y: int, w: int, h: int, color: Color) -> None:
        if w <= 0 or h <= 0:
            return
        self.fill_rect(x, y, w, 1, color)
        self.fill_rect(x, y + h - 1, w, 1, color)
        self.fill_rect(x, y, 1, h, color)
        self.fill_rect(x + w - 1, y, 1, h, color)

    def line(self, x0: int, y0: int, x1: int, y1: int, color: Color) -> None:
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.pixel(x0, y0, color)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def _disc(self, cx: int, cy: int, r: int, color: Color, ring: bool) -> None:
        x0, y0 = max(cx - r, 0), max(cy - r, 0)
        x1, y1 = min(cx + r + 1, self.width), min(cy + r + 1, self.height)
        if x0 >= x1 or y0 >= y1:
            return
        yy, xx = np.ogrid[y0:y1, x0:x1]
        d2 = (xx - cx) ** 2 + (yy - cy) ** 2
        mask = d2 <= (r + 0.5) ** 2
        if ring:
            mask &= d2 >= (r - 0.5) ** 2
        self.frame[y0:y1, x0:x1][mask] = color

    def fill_circle(self, cx: int, cy: int, r: int, color: Color) -> None:
        self._disc(cx, cy, max(r, 0), color, ring=False)

    def circle(self, cx: int, cy: int, r: int, color: Color) -> None:
        self._disc(cx, cy, max(r, 0), color, ring=True)

    def blit(self, mask: np.ndarray, x: int, y: int, color: Color) -> None:
        h, w = mask.shape
        x0, y0 = max(x, 0), max(y, 0)
        x1, y1 = min(x + w, self.width), min(y + h, self.height)
        if x0 >= x1 or y0 >= y1:
            return
        sub = mask[y0 - y:y1 - y, x0 - x:x1 - x]
        self.frame[y0:y1, x0:x1][sub] = color

    def text_width(self, s: str) -> int:
        return CELL_W * len(s)

    def text(self, x: int, y: int, s: str, color: Color) -> int:
        atlas = self.font.atlas()
        for i, ch in enumerate(s):
            code = ord(ch) if ord(ch) < 256 else ord("?")
            self.blit(atlas[code], x + i * CELL_W, y, color)
        return self.text_width(s)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/arcade/test_canvas.py -v`
Expected: 6 passed (the sized test runs twice)

- [ ] **Step 5: Commit**

```bash
git add arcade/canvas.py tests/arcade/conftest.py tests/arcade/test_canvas.py
git commit -m "feat(arcade): canvas drawing primitives"
```

---

### Task 6: Look, the preview render modes

**Files:**
- Create: `arcade/look.py`, `arcade/preview.py`
- Test: `tests/arcade/test_look.py`

**Interfaces:**
- Produces: `gamma_lut(gamma: float) -> np.ndarray (256,) uint8`; `apply_gamma(frame, gamma) -> np.ndarray`; `render(frame, mode: str, scale: int = 8, gamma: float = 2.2) -> np.ndarray` of shape `(h*scale, w*scale, 3)`; `PreviewDisplay(inner: Display, mode, scale, gamma)` implementing the `Display` protocol.

Gamma direction: an uncorrected LED wall drives light output proportional to the byte value, so mid greys look brighter on the wall than the same bytes look on a monitor. To show that, the preview maps `v -> 255 * (v/255) ** (1/gamma)`. With `gamma = 1.0` the preview shows the bytes as they are, which is right when the Colorlight card applies gamma itself.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_look.py`:

```python
import numpy as np
import pytest

from arcade.look import apply_gamma, gamma_lut, render
from arcade.preview import PreviewDisplay
from show.display.fake import FakeDisplay


def frame_with_dot(w=8, h=4):
    f = np.zeros((h, w, 3), np.uint8)
    f[1, 2] = (128, 0, 0)
    return f


def test_gamma_lut_brightens_midtones_and_identity_at_one():
    lut = gamma_lut(2.2)
    assert lut[0] == 0 and lut[255] == 255 and lut[128] > 128
    assert np.array_equal(gamma_lut(1.0), np.arange(256, dtype=np.uint8))
    f = frame_with_dot()
    assert apply_gamma(f, 2.2)[1, 2, 0] == lut[128]


def test_plain_is_nearest_neighbour():
    out = render(frame_with_dot(), "plain", scale=4, gamma=2.2)
    assert out.shape == (16, 32, 3)
    assert (out[4:8, 8:12, 0] == 128).all() and out[0, 0].sum() == 0


def test_led_draws_round_dots_with_dark_gaps():
    out = render(frame_with_dot(), "led", scale=8, gamma=1.0)
    cell = out[8:16, 16:24, 0]
    assert cell[4, 4] == 128
    assert cell[0, 0] == 0 and cell[0, 7] == 0
    assert 0 < (cell > 0).sum() < 64
    assert out[0:8, 0:8].sum() == 0


def test_distance_blurs():
    out = render(frame_with_dot(), "distance", scale=8, gamma=1.0)
    assert out.shape == (32, 64, 3)
    assert out[12, 20, 0] > 0 and out[12, 20, 0] < 128
    assert out[9, 13, 0] > 0


def test_unknown_mode_rejected():
    with pytest.raises(ValueError):
        render(frame_with_dot(), "crt")


def test_preview_display_renders_before_push():
    inner = FakeDisplay()
    d = PreviewDisplay(inner, "plain", scale=2, gamma=1.0)
    d.push(frame_with_dot())
    assert inner.last.shape == (8, 16, 3)
    d.set_brightness(0.3)
    assert inner.brightness == 0.3
    d.close()
    assert inner.closed
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/arcade/test_look.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arcade.look'`

- [ ] **Step 3: Implement look and preview**

`arcade/look.py`:

```python
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

MODES = ("plain", "led", "distance")


@lru_cache(maxsize=8)
def gamma_lut(gamma: float) -> np.ndarray:
    v = np.arange(256, dtype=np.float64) / 255.0
    return np.clip(np.round(255.0 * v ** (1.0 / gamma)), 0, 255).astype(np.uint8)


def apply_gamma(frame: np.ndarray, gamma: float) -> np.ndarray:
    if gamma == 1.0:
        return frame
    return gamma_lut(gamma)[frame]


@lru_cache(maxsize=8)
def _led_kernel(scale: int) -> np.ndarray:
    c = (scale - 1) / 2
    yy, xx = np.mgrid[0:scale, 0:scale]
    d = np.hypot(xx - c, yy - c) / scale
    return np.where(d <= 0.36, 1.0, np.where(d <= 0.5, 0.3, 0.0)).astype(np.float32)


def _nearest(frame: np.ndarray, scale: int) -> np.ndarray:
    return np.repeat(np.repeat(frame, scale, axis=0), scale, axis=1)


def render(frame: np.ndarray, mode: str, scale: int = 8, gamma: float = 2.2) -> np.ndarray:
    if mode not in MODES:
        raise ValueError(f"look must be one of {MODES}, got {mode!r}")
    if mode == "plain":
        return _nearest(frame, scale)
    f = apply_gamma(frame, gamma)
    h, w = f.shape[:2]
    if mode == "led":
        k = _led_kernel(scale)
        out = f[:, None, :, None, :].astype(np.float32) * k[None, :, None, :, None]
        return out.reshape(h * scale, w * scale, 3).astype(np.uint8)
    big = _nearest(f, scale)
    r = max(1, scale // 2)
    blurred = cv2.blur(cv2.blur(big, (2 * r + 1, 2 * r + 1)), (2 * r + 1, 2 * r + 1))
    return blurred.astype(np.uint8)
```

`arcade/preview.py`:

```python
from __future__ import annotations

import numpy as np

from arcade.look import render
from show.display import Display


class PreviewDisplay:
    """Renders a wall frame in a look mode before handing it to a real (usually SDL) display."""

    def __init__(self, inner: Display, mode: str, scale: int, gamma: float):
        self.inner, self.mode, self.scale, self.gamma = inner, mode, scale, gamma

    def push(self, frame: np.ndarray) -> None:
        self.inner.push(render(frame, self.mode, self.scale, self.gamma))

    def set_brightness(self, level: float) -> None:
        self.inner.set_brightness(level)

    def close(self) -> None:
        self.inner.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/arcade/test_look.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add arcade/look.py arcade/preview.py tests/arcade/test_look.py
git commit -m "feat(arcade): LED-look and distance preview render modes"
```

---

### Task 7: Game protocol, registry, scores

**Files:**
- Create: `arcade/game.py`, `arcade/games/__init__.py`, `arcade/scores.py`
- Test: `tests/arcade/test_game.py`, `tests/arcade/test_scores.py`

**Interfaces:**
- Consumes: `Canvas` (Task 5), `Sensed` (Task 3).
- Produces: `GameInfo(name, title, icon, needs)`; `Game` protocol with `info`, `reset(size, rng)`, `update(sensed, dt)`, `draw(canvas)`, `done() -> bool`, `debug_state() -> dict`; `icon_from_rows(rows: list[str]) -> np.ndarray (8, 8) bool`; registry `GAMES: list[type]`, `all_games() -> list[type]`, `get_game(name) -> type`; `Scores(path)` with `best(name) -> float | None`, `record(name, value) -> bool`.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_game.py`:

```python
import pytest

from arcade.game import GameInfo, icon_from_rows
from arcade.games import GAMES, all_games, get_game


def test_icon_from_rows():
    icon = icon_from_rows(["#......#", "........", "........", "........",
                           "........", "........", "........", "#......#"])
    assert icon.shape == (8, 8) and icon.dtype == bool
    assert icon[0, 0] and icon[7, 7] and not icon[3, 3] and icon.sum() == 4
    with pytest.raises(ValueError):
        icon_from_rows(["#"])


def test_game_info_is_frozen():
    info = GameInfo("x", "X", icon_from_rows(["." * 8] * 8), frozenset({"pose"}))
    with pytest.raises(Exception):
        info.name = "y"  # type: ignore[misc]


def test_registry_lookup():
    assert all_games() == GAMES
    for cls in GAMES:
        assert get_game(cls.info.name) is cls
    with pytest.raises(KeyError):
        get_game("nope")
```

`tests/arcade/test_scores.py`:

```python
from arcade.scores import Scores


def test_scores_record_and_persist(tmp_path):
    p = tmp_path / "d" / "scores.json"
    s = Scores(p)
    assert s.best("jump") is None
    assert s.record("jump", 0.4) is True
    assert s.record("jump", 0.3) is False
    assert s.record("jump", 0.5) is True
    assert s.best("jump") == 0.5
    assert Scores(p).best("jump") == 0.5


def test_scores_survive_corrupt_file(tmp_path):
    p = tmp_path / "scores.json"
    p.write_text("{not json")
    s = Scores(p)
    assert s.best("x") is None
    assert s.record("x", 1.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/arcade/test_game.py tests/arcade/test_scores.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arcade.game'`

- [ ] **Step 3: Implement**

`arcade/game.py`:

```python
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from arcade.canvas import Canvas
from arcade.sensed import Sensed

INPUTS = frozenset({"pose", "blobs", "motion", "audio"})


@dataclass(frozen=True)
class GameInfo:
    name: str
    title: str
    icon: np.ndarray
    needs: frozenset[str]


class Game(Protocol):
    info: GameInfo

    def reset(self, size: tuple[int, int], rng: random.Random) -> None: ...
    def update(self, sensed: Sensed, dt: float) -> None: ...
    def draw(self, canvas: Canvas) -> None: ...
    def done(self) -> bool: ...
    def debug_state(self) -> dict: ...


def icon_from_rows(rows: list[str]) -> np.ndarray:
    if len(rows) != 8 or any(len(r) != 8 for r in rows):
        raise ValueError("an icon is 8 rows of 8 characters")
    return np.array([[ch == "#" for ch in row] for row in rows], dtype=bool)
```

`arcade/games/__init__.py`:

```python
"""Registry. Menu order is list order. Games register by appending in their own module import below."""
from __future__ import annotations

GAMES: list[type] = []


def all_games() -> list[type]:
    return GAMES


def get_game(name: str) -> type:
    for cls in GAMES:
        if cls.info.name == name:
            return cls
    raise KeyError(name)
```

`arcade/scores.py`:

```python
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("arcade")


class Scores:
    """Best-of-the-night per game in one JSON file, written atomically. Higher is better."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._data: dict[str, dict] = {}
        try:
            self._data = json.loads(self.path.read_text())
            if not isinstance(self._data, dict):
                raise ValueError("scores file is not an object")
        except FileNotFoundError:
            pass
        except (ValueError, OSError) as e:
            log.warning("ignoring unreadable scores file %s: %s", self.path, e)
            self._data = {}

    def best(self, name: str) -> float | None:
        entry = self._data.get(name)
        return None if entry is None else float(entry["best"])

    def record(self, name: str, value: float) -> bool:
        current = self.best(name)
        if current is not None and value <= current:
            return False
        self._data[name] = {"best": float(value), "when": datetime.now(timezone.utc).isoformat()}
        self._write()
        return True

    def _write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, indent=1))
        os.replace(tmp, self.path)
```

Add `data/` to `.gitignore` (the scores file lives there).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/arcade/test_game.py tests/arcade/test_scores.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add arcade/game.py arcade/games/__init__.py arcade/scores.py .gitignore tests/arcade/test_game.py tests/arcade/test_scores.py
git commit -m "feat(arcade): game protocol, registry, scores"
```

---

### Task 8: Headless harness and the runner

**Files:**
- Create: `arcade/headless.py`, `arcade/runner.py`
- Test: `tests/arcade/helpers.py`, `tests/arcade/test_runner.py`

**Interfaces:**
- Consumes: `ArcadeConfig` (Task 2), `Sensed`, `Audio` (Task 3), `TICK` (Task 4), `Canvas` (Task 5), `Game`, `GameInfo` (Task 7).
- Produces: `RecordingDisplay(keep_all=True)` with `.frames`, `.last`, `.count`, `.brightness`, `.closed`; `NullMenu` (a menu that never selects); `run_headless(cfg, font, game_cls, sensed_iter, seed=0) -> tuple[list[np.ndarray], Runner]`; `MenuLike` protocol (a `Game` plus `selected: str | None`, `set_unavailable(names)`, `set_status(camera_ok, mic_ok, inputs)`); `Runner(cfg, display, font, menu, games, attract=None, seed=0, clock=time.monotonic, sleep=time.sleep, log=None)` with `tick(sensed, dt)`, `launch(name, attract=False)`, `go_menu()`, `sense(camera, audio) -> Sensed`, `loop(camera, audio, max_ticks=None)`, `state() -> dict`, `.current`, `.current_name`, `.hidden`, `.crashes`, `.in_attract`, `.canvas`.
- Test helpers: `make_cfg(size, **over) -> ArcadeConfig`, `run(game_cls, sensed_iter, size, font, seed=0, **cfg_over) -> (frames, game, runner)`, `StubMenu`, `SpyGame`.

Camera sources expose `latest() -> (bodies, blobs, motion)` and `available: bool`; audio sources expose `latest() -> Audio` and `available: bool`. The runner only relies on those two shapes.

- [ ] **Step 1: Write the helpers and the failing tests**

`tests/arcade/helpers.py`:

```python
from __future__ import annotations

import random
from dataclasses import replace
from typing import Iterable

import numpy as np

from arcade.canvas import Canvas
from arcade.config import ArcadeConfig
from arcade.game import GameInfo, icon_from_rows
from arcade.headless import run_headless
from arcade.sensed import Sensed
from show.font import Font

BLANK_ICON = icon_from_rows(["." * 8] * 8)


def make_cfg(size: tuple[int, int], **over) -> ArcadeConfig:
    return replace(ArcadeConfig(width=size[0], height=size[1], backend="fake", camera="none", audio="none"), **over)


def run(game_cls: type, sensed_iter: Iterable[Sensed], size: tuple[int, int], font: Font,
        seed: int = 0, **cfg_over):
    cfg = make_cfg(size, **cfg_over)
    frames, runner = run_headless(cfg, font, game_cls, sensed_iter, seed=seed)
    return frames, runner.current, runner


class SpyGame:
    """Records calls. Class attributes configure failure and completion for a test."""

    info = GameInfo("spy", "Spy", BLANK_ICON, frozenset())
    raise_on_update = False
    finish_after: int | None = None

    def __init__(self):
        self.updates = 0
        self.draws = 0
        self.size = None

    def reset(self, size, rng: random.Random):
        self.size = size
        self.rng = rng

    def update(self, sensed: Sensed, dt: float):
        self.updates += 1
        if self.raise_on_update:
            raise RuntimeError("boom")

    def draw(self, canvas: Canvas):
        self.draws += 1
        canvas.pixel(0, 0, (255, 255, 255))

    def done(self) -> bool:
        return self.finish_after is not None and self.updates >= self.finish_after

    def debug_state(self) -> dict:
        return {"updates": self.updates}


class StubMenu:
    info = GameInfo("menu", "Menu", BLANK_ICON, frozenset())

    def __init__(self):
        self.selected: str | None = None
        self.unavailable: set[str] = set()
        self.status = None
        self.resets = 0
        self.updates = 0

    def reset(self, size, rng):
        self.resets += 1

    def update(self, sensed, dt):
        self.updates += 1

    def draw(self, canvas):
        canvas.pixel(1, 0, (0, 255, 0))

    def done(self):
        return False

    def debug_state(self):
        return {"selected": self.selected}

    def set_unavailable(self, names: set[str]):
        self.unavailable = set(names)

    def set_status(self, camera_ok: bool, mic_ok: bool, inputs: set[str]):
        self.status = (camera_ok, mic_ok, set(inputs))


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, s: float) -> None:
        self.now += s
```

`tests/arcade/test_runner.py`:

```python
import numpy as np
import pytest

from arcade.headless import RecordingDisplay
from arcade.runner import Runner
from arcade.sensed import Audio, Sensed
from arcade.sources.actors import TICK, Person, scene
from tests.arcade.helpers import FakeClock, SpyGame, StubMenu, make_cfg

SIZE = (64, 64)


def make_runner(font5x7, games=(SpyGame,), attract=None, **over):
    cfg = make_cfg(SIZE, **over)
    display = RecordingDisplay()
    menu = StubMenu()
    runner = Runner(cfg, display, font5x7, menu, list(games), attract=attract, seed=1)
    return runner, display, menu


def feed(runner, frames, dt=TICK):
    for s in frames:
        runner.tick(s, dt)


def test_starts_in_menu_and_sets_brightness(font5x7):
    runner, display, menu = make_runner(font5x7, brightness=0.25)
    assert runner.current is menu and display.brightness == 0.25 and menu.resets == 1
    feed(runner, scene(ticks=2))
    assert display.count == 2 and menu.updates == 2
    assert runner.state()["game"] == "menu"


def test_menu_selection_launches_next_tick(font5x7):
    runner, display, menu = make_runner(font5x7)
    menu.selected = "spy"
    feed(runner, scene(ticks=1))
    assert runner.current_name == "spy" and isinstance(runner.current, SpyGame)
    feed(runner, scene(ticks=1))
    assert runner.current.updates == 1 and runner.current.size == SIZE
    assert runner.state()["updates"] == 1 and menu.selected is None


def test_done_returns_to_menu(font5x7):
    SpyGame.finish_after = 3
    try:
        runner, display, menu = make_runner(font5x7)
        runner.launch("spy")
        feed(runner, scene(ticks=2))
        assert runner.current_name == "spy"
        feed(runner, scene(ticks=1))
        assert runner.current is menu and menu.resets == 2
    finally:
        SpyGame.finish_after = None


def test_exit_gesture_needs_hold(font5x7):
    runner, display, menu = make_runner(font5x7, exit_seconds=1.0)
    runner.launch("spy")
    short = scene(persons=[Person().both_hands_up(at=0.0, seconds=0.5)], ticks=45)
    feed(runner, short)
    assert runner.current_name == "spy"
    runner.launch("spy")
    feed(runner, scene(persons=[Person().both_hands_up(at=0.0, seconds=5.0)], ticks=31))
    assert runner.current is menu
    feed(runner, scene(persons=[Person().both_hands_up(at=0.0, seconds=5.0)], ticks=31))
    assert runner.current is menu


def test_crash_guard_glitch_then_menu_and_hide_after_three(font5x7):
    SpyGame.raise_on_update = True
    try:
        runner, display, menu = make_runner(font5x7)
        for n in range(1, 4):
            runner.launch("spy")
            feed(runner, scene(ticks=1))
            assert runner.current_name == "spy" and runner.crashes["spy"] == n
            glitch = display.last
            assert glitch.sum() > 0
            feed(runner, scene(ticks=Runner.GLITCH_TICKS))
            assert runner.current is menu
        assert runner.hidden == {"spy"} and menu.unavailable == {"spy"}
        menu.selected = "spy"
        feed(runner, scene(ticks=2))
        assert runner.current is menu
    finally:
        SpyGame.raise_on_update = False


def test_idle_attract_and_presence_returns(font5x7):
    class Ambient(SpyGame):
        info = SpyGame.info.__class__("ambient", "Ambient", SpyGame.info.icon, frozenset())

    runner, display, menu = make_runner(font5x7, games=(SpyGame, Ambient), attract="ambient", idle_seconds=1.0)
    feed(runner, scene(ticks=29))
    assert runner.current is menu
    feed(runner, scene(ticks=2))
    assert runner.current_name == "ambient" and runner.in_attract
    feed(runner, scene(persons=[Person()], ticks=1))
    assert runner.current is menu and not runner.in_attract


class RaisingCamera:
    available = True

    def latest(self):
        raise OSError("camera gone")


class QuietAudio:
    available = False

    def latest(self):
        return Audio()


class GoodCamera:
    available = True

    def latest(self):
        return ((), (), None)


def test_sense_survives_raising_source_and_reports_status(font5x7):
    runner, display, menu = make_runner(font5x7)
    s = runner.sense(RaisingCamera(), QuietAudio())
    assert s.bodies == () and s.motion.shape == (64, 64)
    assert menu.status == (False, False, set())
    runner.sense(GoodCamera(), QuietAudio())
    assert menu.status == (True, False, {"pose", "blobs", "motion"})


class BadDisplay(RecordingDisplay):
    def push(self, frame):
        raise OSError("socket")


def test_push_failure_is_logged_not_raised(font5x7):
    cfg = make_cfg(SIZE)
    runner = Runner(cfg, BadDisplay(), font5x7, StubMenu(), [SpyGame], seed=1)
    feed(runner, scene(ticks=2))


def test_loop_runs_max_ticks_with_fake_clock(font5x7):
    cfg = make_cfg(SIZE)
    clock = FakeClock()
    display = RecordingDisplay()
    runner = Runner(cfg, display, font5x7, StubMenu(), [SpyGame], seed=1, clock=clock, sleep=clock.sleep)
    runner.loop(GoodCamera(), QuietAudio(), max_ticks=10)
    assert display.count == 10
    assert clock.now == pytest.approx(100.0 + 10 / cfg.fps, abs=0.05)


def test_dt_is_clamped(font5x7):
    runner, display, menu = make_runner(font5x7)
    runner.launch("spy")
    runner.tick(Sensed(0.0), dt=5.0)
    assert runner.t == pytest.approx(0.1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/arcade/test_runner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arcade.headless'`

- [ ] **Step 3: Implement the harness and the runner**

`arcade/headless.py`:

```python
"""Headless pieces shared by tests and the agent tools."""
from __future__ import annotations

import random
from typing import Iterable

import numpy as np

from arcade.config import ArcadeConfig
from arcade.game import GameInfo, icon_from_rows
from arcade.sensed import Sensed
from arcade.sources.actors import TICK
from show.font import Font


class RecordingDisplay:
    def __init__(self, keep_all: bool = True):
        self.keep_all = keep_all
        self.frames: list[np.ndarray] = []
        self.last: np.ndarray | None = None
        self.count = 0
        self.brightness = 1.0
        self.closed = False

    def push(self, frame: np.ndarray) -> None:
        copy = frame.copy()
        if self.keep_all:
            self.frames.append(copy)
        self.last = copy
        self.count += 1

    def set_brightness(self, level: float) -> None:
        self.brightness = level

    def close(self) -> None:
        self.closed = True


class NullMenu:
    """A menu that shows nothing and never selects. For tools that launch a game directly."""

    info = GameInfo("menu", "Menu", icon_from_rows(["." * 8] * 8), frozenset())

    def __init__(self):
        self.selected: str | None = None

    def reset(self, size, rng: random.Random) -> None:
        pass

    def update(self, sensed: Sensed, dt: float) -> None:
        pass

    def draw(self, canvas) -> None:
        pass

    def done(self) -> bool:
        return False

    def debug_state(self) -> dict:
        return {}

    def set_unavailable(self, names: set[str]) -> None:
        pass

    def set_status(self, camera_ok: bool, mic_ok: bool, inputs: set[str]) -> None:
        pass


def run_headless(cfg: ArcadeConfig, font: Font, game_cls: type, sensed_iter: Iterable[Sensed],
                 seed: int = 0):
    from arcade.runner import Runner

    display = RecordingDisplay()
    runner = Runner(cfg, display, font, NullMenu(), [game_cls], seed=seed)
    runner.launch(game_cls.info.name)
    for sensed in sensed_iter:
        runner.tick(sensed, TICK)
    return display.frames, runner
```

`arcade/runner.py`:

```python
from __future__ import annotations

import logging
import random
import time
from typing import Callable, Protocol

import numpy as np

from arcade.canvas import Canvas
from arcade.config import ArcadeConfig
from arcade.game import Game
from arcade.sensed import Audio, Sensed
from show.display import Display
from show.font import Font

CAMERA_INPUTS = frozenset({"pose", "blobs", "motion"})
AUDIO_INPUTS = frozenset({"audio"})
MAX_DT = 0.1


class MenuLike(Game, Protocol):
    selected: str | None

    def set_unavailable(self, names: set[str]) -> None: ...
    def set_status(self, camera_ok: bool, mic_ok: bool, inputs: set[str]) -> None: ...


class Runner:
    """Fixed-tick loop: sources -> Sensed -> current game -> canvas -> display.

    Owns the exit gesture, idle attract, and the crash guard so every game gets them.
    """

    GLITCH_TICKS = 30
    MAX_CRASHES = 3

    def __init__(self, cfg: ArcadeConfig, display: Display, font: Font, menu: MenuLike,
                 games: list[type], attract: str | None = None, seed: int = 0,
                 clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep,
                 log: logging.Logger | None = None):
        self.cfg, self.display, self.menu = cfg, display, menu
        self.games: dict[str, type] = {g.info.name: g for g in games}
        self.attract, self.seed, self.clock, self.sleep = attract, seed, clock, sleep
        self.log = log or logging.getLogger("arcade")
        self.canvas = Canvas(cfg.width, cfg.height, font)
        self.t = 0.0
        self.running = True
        self.crashes: dict[str, int] = {}
        self.hidden: set[str] = set()
        self._exit_held = 0.0
        self._idle = 0.0
        self._glitch = 0
        self.in_attract = False
        self.current: Game = menu
        self.current_name = "menu"
        self.display.set_brightness(cfg.brightness)
        self.menu.reset(cfg.size, random.Random(seed))

    # ----- game switching -----

    def launch(self, name: str, attract: bool = False) -> None:
        game = self.games[name]()
        game.reset(self.cfg.size, random.Random(self.seed))
        self.current, self.current_name, self.in_attract = game, name, attract
        self._exit_held = 0.0

    def go_menu(self) -> None:
        self.current, self.current_name, self.in_attract = self.menu, "menu", False
        self.menu.selected = None
        self._exit_held = 0.0
        self.menu.reset(self.cfg.size, random.Random(self.seed))

    # ----- one tick -----

    def tick(self, sensed: Sensed, dt: float) -> None:
        dt = min(dt, MAX_DT)
        self.t += dt
        sensed = sensed.with_motion(self.cfg.size)
        if self._glitch > 0:
            self._glitch -= 1
            self._draw_glitch()
            self._push()
            if self._glitch == 0:
                self.go_menu()
            return

        present = bool(sensed.bodies or sensed.blobs)
        self._idle = 0.0 if present else self._idle + dt

        if self.current is not self.menu:
            body = sensed.primary
            self._exit_held = self._exit_held + dt if (body is not None and body.both_hands_up) else 0.0
            if self._exit_held >= self.cfg.exit_seconds:
                self.go_menu()
            elif self.in_attract and present:
                self.go_menu()
        elif (self.attract is not None and self.attract in self.games
              and self.attract not in self.hidden and self._idle >= self.cfg.idle_seconds):
            self.launch(self.attract, attract=True)

        try:
            self.current.update(sensed, dt)
            self.canvas.clear()
            self.current.draw(self.canvas)
        except Exception:
            self._crashed()
            return

        if self.current is self.menu:
            choice = self.menu.selected
            if choice is not None:
                self.menu.selected = None
                if choice in self.games and choice not in self.hidden:
                    self.launch(choice)
        elif self.current.done():
            self.go_menu()
        self._push()

    def _crashed(self) -> None:
        name = self.current_name
        self.log.exception("game %s crashed", name)
        self.crashes[name] = self.crashes.get(name, 0) + 1
        if self.crashes[name] >= self.MAX_CRASHES:
            self.hidden.add(name)
            self.menu.set_unavailable(set(self.hidden))
        self._glitch = self.GLITCH_TICKS
        self._draw_glitch()
        self._push()

    def _draw_glitch(self) -> None:
        rng = np.random.default_rng(self._glitch)
        h, w = self.canvas.height, self.canvas.width
        self.canvas.frame[:] = 0
        self.canvas.frame[rng.random((h, w)) < 0.15] = (255, 255, 255)

    def _push(self) -> None:
        try:
            self.display.push(self.canvas.frame)
        except Exception:
            self.log.exception("display push failed")

    # ----- sources and loop -----

    def sense(self, camera, audio) -> Sensed:
        try:
            bodies, blobs, motion = camera.latest()
            camera_ok = bool(getattr(camera, "available", True))
        except Exception:
            self.log.exception("camera source failed")
            bodies, blobs, motion, camera_ok = (), (), None, False
        try:
            a = audio.latest()
            mic_ok = bool(getattr(audio, "available", True))
        except Exception:
            self.log.exception("audio source failed")
            a, mic_ok = Audio(), False
        inputs = (CAMERA_INPUTS if camera_ok else frozenset()) | (AUDIO_INPUTS if mic_ok else frozenset())
        self.menu.set_status(camera_ok, mic_ok, set(inputs))
        return Sensed(self.t, tuple(bodies), tuple(blobs), motion, a).with_motion(self.cfg.size)

    def loop(self, camera, audio, max_ticks: int | None = None) -> None:
        period = 1.0 / self.cfg.fps
        last = self.clock()
        next_deadline = last + period
        ticks = 0
        while self.running and (max_ticks is None or ticks < max_ticks):
            now = self.clock()
            dt, last = now - last, now
            self.tick(self.sense(camera, audio), dt)
            ticks += 1
            delay = next_deadline - self.clock()
            if delay > 0:
                self.sleep(delay)
                next_deadline += period
            else:
                next_deadline = self.clock() + period

    def state(self) -> dict:
        return {"game": self.current_name, "t": round(self.t, 3), "idle": round(self._idle, 3),
                "attract": self.in_attract, "hidden": sorted(self.hidden),
                **self.current.debug_state()}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/arcade/test_runner.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add arcade/headless.py arcade/runner.py tests/arcade/helpers.py tests/arcade/test_runner.py
git commit -m "feat(arcade): runner with exit gesture, idle attract, crash guard; headless harness"
```

---

### Task 9: Menu

**Files:**
- Create: `arcade/menu.py`
- Test: `tests/arcade/test_menu.py`

**Interfaces:**
- Consumes: `Canvas`, `Sensed`, `GameInfo`, `MenuLike`.
- Produces: `Menu(games: list[type], cfg: ArcadeConfig)` implementing `MenuLike`, with `.tiles: list[tuple[int, int, int, int]]` after `reset`, `.selected`, `.hover: int` (-1 when none), `.dwell: float` (0..1), `cursor_of(sensed, size) -> tuple[int, int] | None`, `debug_state() -> {"hover", "dwell", "selected", "unavailable"}`.

Layout: twelve tiles of 10 by 10 with a one-pixel gap, three columns when the wall is narrower than 96 pixels, else six; the grid is centred above an 8-pixel title row at the bottom. Slot 11 is the title tile and never selects.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_menu.py`:

```python
import random

import pytest

from arcade.canvas import Canvas
from arcade.game import GameInfo, icon_from_rows
from arcade.menu import SLOTS, TITLE_SLOT, Menu, cursor_of
from arcade.sensed import Blob, Body, Keypoint, Sensed
from arcade.sources.actors import TICK, Person, make_keypoints, scene
from tests.arcade.helpers import SpyGame, make_cfg

ICON = icon_from_rows(["#" * 8] * 8)


def game(name, needs=frozenset()):
    return type(name.title(), (SpyGame,), {"info": GameInfo(name, name.title(), ICON, frozenset(needs))})


GAMES = [game("aaa"), game("bbb"), game("ccc", {"audio"})]


def make_menu(size, **over):
    cfg = make_cfg(size, **over)
    m = Menu(GAMES, cfg)
    m.reset(size, random.Random(0))
    m.set_status(True, False, {"pose", "blobs", "motion"})
    return m, cfg


def wrist_at(px, py, size):
    """A Sensed whose primary body has a raised wrist at wall pixel (px, py)."""
    w, h = size
    kps = list(make_keypoints(0.5, 0.6, 0.6, right_up=True))
    kps[10] = Keypoint((px + 0.5) / w, (py + 0.5) / h)
    body = Body(0, (0.3, 0.1, 0.7, 0.9), tuple(kps))
    return Sensed(0.0, bodies=(body,))


def hold(menu, sensed, seconds):
    for _ in range(int(seconds / TICK)):
        menu.update(sensed, TICK)


@pytest.mark.parametrize("size", [(64, 64), (128, 32), (96, 48), (128, 64)])
def test_layout_fits_any_size(size):
    m, _ = make_menu(size)
    assert len(m.tiles) == SLOTS
    for x, y, w, h in m.tiles:
        assert 0 <= x and x + w <= size[0] and 0 <= y and y + h <= size[1] - 8
    xs = {t[0] for t in m.tiles}
    assert len(xs) == (3 if size[0] < 96 else 6)


def test_cursor_fallbacks(size):
    w, h = size
    s = wrist_at(5, 5, size)
    assert cursor_of(s, size) == (5, 5)
    blob_only = Sensed(0.0, blobs=(Blob(0.5, 0.5, 0.02, (255, 255, 255)),))
    assert cursor_of(blob_only, size) == (w // 2, h // 2)
    body = Body(0, (0.2, 0.2, 0.4, 0.8), make_keypoints(0.3, 0.5, 0.6))
    assert cursor_of(Sensed(0.0, bodies=(body,)), size) == (int(0.3 * w), int(0.5 * h))
    assert cursor_of(Sensed(0.0), size) is None


def test_dwell_selects_and_pass_through_does_not(size):
    m, cfg = make_menu(size, dwell_seconds=1.0)
    x, y, w, h = m.tiles[1]
    s = wrist_at(x + w // 2, y + h // 2, size)
    hold(m, s, 0.5)
    assert m.selected is None and m.hover == 1 and 0.4 < m.dwell < 0.6
    hold(m, s, 0.6)
    assert m.selected == "bbb" and m.debug_state()["selected"] == "bbb"
    m.selected = None
    m.reset(size, random.Random(0))
    for i in range(12):
        tx, ty, tw, th = m.tiles[i % SLOTS]
        m.update(wrist_at(tx + 1, ty + 1, size), TICK)
    assert m.selected is None
    m.update(Sensed(0.0), TICK)
    assert m.hover == -1 and m.dwell == 0.0


def test_unavailable_and_title_tile_never_select(size):
    m, cfg = make_menu(size, dwell_seconds=0.5)
    x, y, w, h = m.tiles[2]
    hold(m, wrist_at(x + 5, y + 5, size), 1.0)
    assert m.selected is None and "ccc" in m.debug_state()["unavailable"]
    m.set_status(True, True, {"pose", "blobs", "motion", "audio"})
    hold(m, wrist_at(x + 5, y + 5, size), 1.0)
    assert m.selected == "ccc"
    m.selected = None
    m.set_unavailable({"aaa"})
    x, y, w, h = m.tiles[0]
    hold(m, wrist_at(x + 5, y + 5, size), 1.0)
    assert m.selected is None
    x, y, w, h = m.tiles[TITLE_SLOT]
    hold(m, wrist_at(x + 5, y + 5, size), 1.0)
    assert m.selected is None


def test_draw_shows_tiles_status_and_title(font5x7, size):
    m, cfg = make_menu(size)
    c = Canvas(*size, font5x7)
    x, y, w, h = m.tiles[1]
    m.update(wrist_at(x + 5, y + 5, size), TICK)
    m.draw(c)
    assert c.frame[y + 1:y + 9, x + 1:x + 9].max() > 0
    assert tuple(c.frame[0, size[0] - 2]) != (0, 0, 0) and c.frame[0, size[0] - 1].sum() < 100
    assert c.frame[size[1] - 8:, :].max() > 0
    ex, ey, ew, eh = m.tiles[5]
    assert c.frame[ey + 1:ey + 9, ex + 1:ex + 9].max() == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/arcade/test_menu.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arcade.menu'`

- [ ] **Step 3: Implement the menu**

`arcade/menu.py`:

```python
from __future__ import annotations

import random

from arcade.canvas import Canvas
from arcade.config import ArcadeConfig
from arcade.game import GameInfo, icon_from_rows
from arcade.sensed import Sensed

SLOTS = 12
TITLE_SLOT = 11
TILE = 10
GAP = 1
TITLE_ROW = 8
TILE_COLOR = (90, 200, 255)
DIM_COLOR = (40, 40, 60)
RING_COLOR = (255, 220, 80)
CURSOR_COLOR = (255, 255, 255)
TEXT_COLOR = (200, 200, 200)
SCROLL_PX_PER_S = 20.0

TITLE_ICON = icon_from_rows(["..####..", ".#....#.", "#......#", "#.####.#",
                             "#.#..#.#", "#.####.#", "#......#", ".######."])


def cursor_of(sensed: Sensed, size: tuple[int, int]) -> tuple[int, int] | None:
    """Raised wrist, else the largest blob, else the body centre, else None."""
    w, h = size
    body = sensed.primary
    if body is not None and body.raised_wrist is not None:
        p = body.raised_wrist
        return (min(w - 1, int(p.x * w)), min(h - 1, int(p.y * h)))
    if sensed.blobs:
        b = sensed.blobs[0]
        return (min(w - 1, int(b.x * w)), min(h - 1, int(b.y * h)))
    if body is not None:
        cx, cy = body.center
        return (min(w - 1, int(cx * w)), min(h - 1, int(cy * h)))
    return None


def _perimeter(x: int, y: int, size: int) -> list[tuple[int, int]]:
    pts = [(x + i, y) for i in range(size)]
    pts += [(x + size - 1, y + i) for i in range(1, size)]
    pts += [(x + size - 1 - i, y + size - 1) for i in range(1, size)]
    pts += [(x, y + size - 1 - i) for i in range(1, size - 1)]
    return pts


class Menu:
    info = GameInfo("menu", "Wall Arcade", TITLE_ICON, frozenset())

    def __init__(self, games: list[type], cfg: ArcadeConfig):
        self.games = list(games)[:TITLE_SLOT]
        self.cfg = cfg
        self.selected: str | None = None
        self.tiles: list[tuple[int, int, int, int]] = []
        self.hover = -1
        self.dwell = 0.0
        self._held = 0.0
        self._t = 0.0
        self._cursor: tuple[int, int] | None = None
        self._hidden: set[str] = set()
        self._inputs: set[str] = set()
        self._camera_ok = False
        self._mic_ok = False

    # ----- MenuLike -----

    def set_unavailable(self, names: set[str]) -> None:
        self._hidden = set(names)

    def set_status(self, camera_ok: bool, mic_ok: bool, inputs: set[str]) -> None:
        self._camera_ok, self._mic_ok, self._inputs = camera_ok, mic_ok, set(inputs)

    # ----- Game -----

    def reset(self, size: tuple[int, int], rng: random.Random) -> None:
        w, h = size
        cols = 3 if w < 96 else 6
        rows = SLOTS // cols
        grid_w = cols * TILE + (cols - 1) * GAP
        grid_h = rows * TILE + (rows - 1) * GAP
        x0 = max(0, (w - grid_w) // 2)
        y0 = max(0, (h - TITLE_ROW - grid_h) // 2)
        self.tiles = [(x0 + (i % cols) * (TILE + GAP), y0 + (i // cols) * (TILE + GAP), TILE, TILE)
                      for i in range(SLOTS)]
        self.hover, self.dwell, self._held, self._t, self._cursor = -1, 0.0, 0.0, 0.0, None

    def _reason_unavailable(self, index: int) -> str | None:
        if index >= len(self.games):
            return "title" if index == TITLE_SLOT else "empty"
        info = self.games[index].info
        if info.name in self._hidden:
            return "out of order"
        missing = info.needs - self._inputs
        if "audio" in missing:
            return "needs mic"
        if missing:
            return "needs camera"
        return None

    def _tile_at(self, px: int, py: int) -> int:
        for i, (x, y, w, h) in enumerate(self.tiles):
            if x <= px < x + w and y <= py < y + h:
                return i
        return -1

    def update(self, sensed: Sensed, dt: float) -> None:
        self._t += dt
        self._cursor = cursor_of(sensed, (self.cfg.width, self.cfg.height))
        tile = self._tile_at(*self._cursor) if self._cursor is not None else -1
        if tile != self.hover:
            self.hover, self._held = tile, 0.0
        elif tile >= 0:
            self._held += dt
        self.dwell = min(1.0, self._held / self.cfg.dwell_seconds) if tile >= 0 else 0.0
        if tile >= 0 and self._held >= self.cfg.dwell_seconds and self._reason_unavailable(tile) is None:
            self.selected = self.games[tile].info.name
            self._held = 0.0

    def draw(self, canvas: Canvas) -> None:
        for i, (x, y, w, h) in enumerate(self.tiles):
            if i == TITLE_SLOT:
                canvas.blit(TITLE_ICON, x + 1, y + 1, TEXT_COLOR)
                continue
            if i >= len(self.games):
                continue
            color = DIM_COLOR if self._reason_unavailable(i) else TILE_COLOR
            canvas.blit(self.games[i].info.icon, x + 1, y + 1, color)
        if self.hover >= 0 and self.dwell > 0:
            x, y, w, h = self.tiles[self.hover]
            pts = _perimeter(x, y, w)
            for px, py in pts[:int(self.dwell * len(pts))]:
                canvas.pixel(px, py, RING_COLOR)
        if self._cursor is not None:
            cx, cy = self._cursor
            for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                canvas.pixel(cx + dx, cy + dy, CURSOR_COLOR)
        self._draw_title(canvas)
        canvas.pixel(canvas.width - 2, 0, (0, 255, 0) if self._camera_ok else (60, 0, 0))
        canvas.pixel(canvas.width - 1, 0, (0, 255, 0) if self._mic_ok else (60, 0, 0))

    def _draw_title(self, canvas: Canvas) -> None:
        if 0 <= self.hover < len(self.games):
            text = self.games[self.hover].info.title
            reason = self._reason_unavailable(self.hover)
            if reason:
                text = f"{text}: {reason}"
        else:
            text = self.info.title
        tw = canvas.text_width(text)
        y = canvas.height - TITLE_ROW
        if tw <= canvas.width:
            canvas.text((canvas.width - tw) // 2, y, text, TEXT_COLOR)
        else:
            offset = int(self._t * SCROLL_PX_PER_S) % (tw + canvas.width)
            canvas.text(canvas.width - offset, y, text, TEXT_COLOR)

    def done(self) -> bool:
        return False

    def debug_state(self) -> dict:
        return {"hover": self.hover, "dwell": round(self.dwell, 3), "selected": self.selected,
                "unavailable": sorted(g.info.name for i, g in enumerate(self.games)
                                      if self._reason_unavailable(i))}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/arcade/test_menu.py -v`
Expected: 12 passed

- [ ] **Step 5: Commit**

```bash
git add arcade/menu.py tests/arcade/test_menu.py
git commit -m "feat(arcade): hover-and-dwell menu"
```

---

### Task 10: Light painting

**Files:**
- Create: `arcade/games/paint.py`
- Modify: `arcade/games/__init__.py` (register)
- Test: `tests/arcade/test_paint.py`

**Interfaces:**
- Produces: `Paint` game, `info.name == "paint"`, `needs == {"blobs"}`, `debug_state() -> {"lit": int, "idle": float}`. Constants `FADE_SECONDS = 20.0`, `CLEAR_AFTER = 30.0`.

The trail is a float array the game owns, so fading is exact and the runner can keep clearing the canvas every tick. Blob `size` is a fraction of frame width; the stamp radius is `max(1, round(size * width))`.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_paint.py`:

```python
import numpy as np

from arcade.games import get_game
from arcade.games.paint import CLEAR_AFTER, FADE_SECONDS, Paint
from arcade.sources.actors import TICK, moving_blob, scene
from tests.arcade.helpers import run


def test_registered():
    assert get_game("paint") is Paint and "blobs" in Paint.info.needs


def test_blob_leaves_trail_in_its_color(font5x7, size):
    w, h = size
    frames, game, _ = run(Paint, scene(blobs=[moving_blob(0.1, 0.5, 0.9, 0.5, 1.0, color=(255, 0, 0))], ticks=31),
                          size, font5x7)
    last = frames[-1]
    row = last[h // 2]
    assert (row[:, 0] > 0).sum() >= int(0.7 * w)
    assert row[:, 1].max() == 0 and row[:, 2].max() == 0
    assert game.debug_state()["lit"] > 0


def test_trail_fades_to_black_and_state_idles(font5x7, size):
    ticks = 31 + int((FADE_SECONDS + 1) / TICK)
    frames, game, _ = run(Paint, scene(blobs=[moving_blob(0.1, 0.5, 0.9, 0.5, 1.0)], ticks=ticks), size, font5x7)
    mid = frames[31 + int(FADE_SECONDS / 2 / TICK)]
    assert 0 < mid.max() < 200
    assert frames[-1].max() == 0
    assert game.debug_state()["lit"] == 0 and game.debug_state()["idle"] > FADE_SECONDS


def test_stationary_blob_keeps_repainting(font5x7):
    ticks = int(25 / TICK)
    frames, game, _ = run(Paint, scene(blobs=[moving_blob(0.5, 0.5, 0.5, 0.5, 25.0, color=(0, 255, 0))], ticks=ticks),
                          (64, 64), font5x7)
    assert frames[-1].max() == 255 and game.debug_state()["idle"] == 0.0
    assert CLEAR_AFTER > FADE_SECONDS
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/arcade/test_paint.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arcade.games.paint'`

- [ ] **Step 3: Implement**

`arcade/games/paint.py`:

```python
from __future__ import annotations

import random

import numpy as np

from arcade.canvas import Canvas
from arcade.game import GameInfo, icon_from_rows
from arcade.sensed import Sensed

FADE_SECONDS = 20.0
CLEAR_AFTER = 30.0

ICON = icon_from_rows(["......#.", ".....#..", "....#...", "...#....",
                       "..##....", ".###....", "###.....", "##......"])


class Paint:
    """Every bright blob paints its colour; the picture fades over FADE_SECONDS."""

    info = GameInfo("paint", "Light painting", ICON, frozenset({"blobs"}))

    def reset(self, size: tuple[int, int], rng: random.Random) -> None:
        w, h = size
        self.trail = np.zeros((h, w, 3), dtype=np.float32)
        self.idle = 0.0

    def update(self, sensed: Sensed, dt: float) -> None:
        h, w = self.trail.shape[:2]
        self.trail -= 255.0 * dt / FADE_SECONDS
        np.clip(self.trail, 0.0, 255.0, out=self.trail)
        if not sensed.blobs:
            self.idle += dt
            if self.idle >= CLEAR_AFTER:
                self.trail[:] = 0.0
            return
        self.idle = 0.0
        yy, xx = np.ogrid[0:h, 0:w]
        for b in sensed.blobs:
            r = max(1, round(b.size * w))
            cx, cy = int(b.x * w), int(b.y * h)
            mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
            color = np.array(b.color, dtype=np.float32)
            self.trail[mask] = np.maximum(self.trail[mask], color)

    def draw(self, canvas: Canvas) -> None:
        canvas.frame[:] = self.trail.astype(np.uint8)

    def done(self) -> bool:
        return False

    def debug_state(self) -> dict:
        return {"lit": int((self.trail.max(axis=2) > 0).sum()), "idle": round(self.idle, 2)}
```

Append to `arcade/games/__init__.py`, after `get_game`:

```python
from arcade.games.paint import Paint  # noqa: E402

GAMES.append(Paint)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/arcade/test_paint.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add arcade/games/paint.py arcade/games/__init__.py tests/arcade/test_paint.py
git commit -m "feat(arcade): light painting game"
```

---

### Task 11: Pose puppet

**Files:**
- Create: `arcade/games/puppet.py`
- Modify: `arcade/games/__init__.py` (register)
- Test: `tests/arcade/test_puppet.py`

**Interfaces:**
- Produces: `Puppet` game, `info.name == "puppet"`, `needs == {"pose"}`, `debug_state() -> {"bodies": int}`.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_puppet.py`:

```python
import numpy as np

from arcade.games import get_game
from arcade.games.puppet import COLORS, Puppet
from arcade.sensed import Body, Keypoint
from arcade.sources.actors import Person, make_keypoints, scene
from tests.arcade.helpers import run


def lit(frame):
    return int((frame.max(axis=2) > 0).sum())


def test_registered():
    assert get_game("puppet") is Puppet and Puppet.info.needs == {"pose"}


def test_draws_one_figure_where_the_body_is(font5x7, size):
    w, h = size
    frames, game, _ = run(Puppet, scene(persons=[Person(0.25, 0.5, 0.6)], ticks=2), size, font5x7)
    f = frames[-1]
    assert game.debug_state()["bodies"] == 1
    left, right = f[:, :w // 2], f[:, w // 2:]
    assert lit(left) > 10 and lit(right) == 0
    assert tuple(f.reshape(-1, 3)[f.reshape(-1, 3).sum(axis=1).argmax()]) == COLORS[0]


def test_two_bodies_two_colours_and_empty_is_black(font5x7, size):
    frames, game, _ = run(Puppet, scene(persons=[Person(0.25), Person(0.75)], ticks=2), size, font5x7)
    colors = {tuple(px) for px in frames[-1].reshape(-1, 3) if px.sum() > 0}
    assert colors == {COLORS[0], COLORS[1]}
    frames, game, _ = run(Puppet, scene(ticks=2), size, font5x7)
    assert lit(frames[-1]) == 0 and game.debug_state()["bodies"] == 0


def test_low_confidence_limbs_are_skipped(font5x7, size):
    kps = list(make_keypoints(0.5, 0.5, 0.6))
    for i in range(5, 17):
        kps[i] = Keypoint(kps[i].x, kps[i].y, 0.0)
    body = Body(0, (0.3, 0.2, 0.7, 0.8), tuple(kps))
    from arcade.sensed import Sensed
    frames, _, _ = run(Puppet, [Sensed(0.0, bodies=(body,))], size, font5x7)
    full, _, _ = run(Puppet, scene(persons=[Person(0.5, 0.5, 0.6)], ticks=1), size, font5x7)
    assert 0 < lit(frames[-1]) < lit(full[-1])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/arcade/test_puppet.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arcade.games.puppet'`

- [ ] **Step 3: Implement**

`arcade/games/puppet.py`:

```python
from __future__ import annotations

import random

from arcade.canvas import Canvas
from arcade.game import GameInfo, icon_from_rows
from arcade.sensed import MIN_CONF, SKELETON, Body, Sensed

COLORS = ((80, 255, 120), (255, 120, 80))
ICON = icon_from_rows(["...##...", "...##...", ".######.", "#..##..#",
                       "...##...", "..#..#..", ".#....#.", "#......#"])


class Puppet:
    """Up to two stick figures that mirror the people in front of the camera."""

    info = GameInfo("puppet", "Pose puppet", ICON, frozenset({"pose"}))

    def reset(self, size: tuple[int, int], rng: random.Random) -> None:
        self.size = size
        self.bodies: tuple[Body, ...] = ()

    def update(self, sensed: Sensed, dt: float) -> None:
        self.bodies = sensed.bodies[:2]

    def draw(self, canvas: Canvas) -> None:
        w, h = canvas.size
        for body, color in zip(self.bodies, COLORS):
            pts = [(int(k.x * (w - 1)), int(k.y * (h - 1))) for k in body.keypoints]
            for a, b in SKELETON:
                if body.keypoints[a].conf >= MIN_CONF and body.keypoints[b].conf >= MIN_CONF:
                    canvas.line(*pts[a], *pts[b], color)
            if body.nose.conf >= MIN_CONF:
                canvas.fill_circle(*pts[0], max(1, round(body.height * h * 0.06)), color)

    def done(self) -> bool:
        return False

    def debug_state(self) -> dict:
        return {"bodies": len(self.bodies)}
```

Append to `arcade/games/__init__.py`:

```python
from arcade.games.puppet import Puppet  # noqa: E402

GAMES.append(Puppet)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/arcade/test_puppet.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add arcade/games/puppet.py arcade/games/__init__.py tests/arcade/test_puppet.py
git commit -m "feat(arcade): pose puppet game"
```

---

### Task 12: Scenario files and replay sources

**Files:**
- Create: `arcade/sources/scenario.py`, `arcade/sources/replay.py`
- Test: `tests/arcade/test_scenario.py`

**Interfaces:**
- Consumes: `Sensed`, `Body`, `Blob`, `Audio`, `Keypoint` (Task 3).
- Produces: `encode(sensed) -> str` (one JSON line), `decode(line) -> Sensed`; `ScenarioReader(path)` iterable of `Sensed` with `.skipped: int`; `ScenarioWriter(path)` with `write(sensed)`, `close()`, context manager; `ReplayStream(records)` with `.current`, `.finished`, `advance()`; `ReplayCamera(stream)` and `ReplayAudio(stream)` (both `available = True`); `open_replay(path) -> (ReplayCamera, ReplayAudio)`.

The runner calls `camera.latest()` then `audio.latest()` each tick. `ReplayCamera.latest()` advances the shared stream; `ReplayAudio.latest()` reads the same record. At end of file the last record is held.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_scenario.py`:

```python
import json

import numpy as np

from arcade.sensed import Audio, Blob, Sensed
from arcade.sources.actors import Person, claps, moving_blob, scene
from arcade.sources.replay import ReplayAudio, ReplayCamera, ReplayStream, open_replay
from arcade.sources.scenario import ScenarioReader, ScenarioWriter, decode, encode


def sample():
    s = next(iter(scene(persons=[Person(0.3)], blobs=[moving_blob(0, 0, 1, 1, 1, color=(1, 2, 3))],
                        audio=claps([0.0]), ticks=1)))
    return s.with_motion((16, 8))


def test_round_trip():
    s = sample()
    line = encode(s)
    assert "\n" not in line and json.loads(line)["t"] == 0.0
    d = decode(line)
    assert d.t == s.t and len(d.bodies) == 1 and d.bodies[0].id == 0
    assert d.bodies[0].nose.x == round(s.bodies[0].nose.x, 4)
    assert d.blobs[0].color == (1, 2, 3)
    assert d.motion.shape == (8, 16) and np.array_equal(d.motion, s.motion)
    assert d.audio == Audio(level=0.8, peak=1.0, onset=True)
    assert decode(encode(Sensed(1.5))).motion is None


def test_reader_skips_bad_lines(tmp_path):
    p = tmp_path / "s.jsonl"
    good = encode(Sensed(0.0))
    p.write_text(good + "\n\n{not json\n" + encode(Sensed(0.5))[:-8] + "\n" + '{"t": "x"}\n' + good + "\n")
    r = ScenarioReader(p)
    got = list(r)
    assert len(got) == 2 and r.skipped == 3


def test_writer_and_open_replay(tmp_path):
    p = tmp_path / "rec.jsonl"
    with ScenarioWriter(p) as w:
        for s in scene(persons=[Person()], ticks=3):
            w.write(s.with_motion((8, 8)))
    cam, aud = open_replay(p)
    assert cam.available and aud.available
    bodies, blobs, motion = cam.latest()
    assert len(bodies) == 1 and motion.shape == (8, 8) and aud.latest() == Audio()
    cam.latest()
    cam.latest()
    assert cam.stream.finished is False
    bodies4, _, _ = cam.latest()
    assert cam.stream.finished is True and len(bodies4) == 1


def test_replay_of_empty_stream_yields_empty_sensed():
    cam = ReplayCamera(ReplayStream(iter([])))
    assert cam.latest() == ((), (), None)
    assert ReplayAudio(cam.stream).latest() == Audio()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/arcade/test_scenario.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arcade.sources.replay'`

- [ ] **Step 3: Implement**

`arcade/sources/scenario.py`:

```python
"""Scenario files: one JSON object per line, one Sensed per tick."""
from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Iterator

import numpy as np

from arcade.sensed import Audio, Blob, Body, Keypoint, Sensed

log = logging.getLogger("arcade")


def encode(s: Sensed) -> str:
    motion = None
    if s.motion is not None:
        h, w = s.motion.shape
        motion = {"w": w, "h": h, "bits": base64.b64encode(np.packbits(s.motion.ravel())).decode("ascii")}
    obj = {
        "t": round(s.t, 4),
        "bodies": [{"id": b.id, "box": [round(v, 4) for v in b.box],
                    "kp": [[round(k.x, 4), round(k.y, 4), round(k.conf, 3)] for k in b.keypoints]}
                   for b in s.bodies],
        "blobs": [[round(b.x, 4), round(b.y, 4), round(b.size, 4), list(b.color)] for b in s.blobs],
        "motion": motion,
        "audio": {"level": s.audio.level, "peak": s.audio.peak, "onset": s.audio.onset,
                  "beat": s.audio.beat, "bpm": s.audio.bpm},
    }
    return json.dumps(obj, separators=(",", ":"))


def decode(line: str) -> Sensed:
    obj = json.loads(line)
    t = float(obj["t"])
    bodies = tuple(Body(int(b["id"]), tuple(float(v) for v in b["box"]),
                        tuple(Keypoint(float(x), float(y), float(c)) for x, y, c in b["kp"]))
                   for b in obj.get("bodies", []))
    blobs = tuple(Blob(float(x), float(y), float(size), (int(c[0]), int(c[1]), int(c[2])))
                  for x, y, size, c in obj.get("blobs", []))
    motion = None
    m = obj.get("motion")
    if m:
        bits = np.unpackbits(np.frombuffer(base64.b64decode(m["bits"]), dtype=np.uint8))
        motion = bits[: m["w"] * m["h"]].astype(bool).reshape(m["h"], m["w"])
    a = obj.get("audio", {})
    audio = Audio(float(a.get("level", 0.0)), float(a.get("peak", 0.0)), bool(a.get("onset", False)),
                  bool(a.get("beat", False)), None if a.get("bpm") is None else float(a["bpm"]))
    return Sensed(t, bodies, blobs, motion, audio)


class ScenarioReader:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.skipped = 0

    def __iter__(self) -> Iterator[Sensed]:
        with self.path.open() as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield decode(line)
                except (ValueError, KeyError, TypeError, IndexError) as e:
                    self.skipped += 1
                    log.warning("%s:%d skipped: %s", self.path, lineno, e)


class ScenarioWriter:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("w")

    def write(self, s: Sensed) -> None:
        self._fh.write(encode(s) + "\n")

    def close(self) -> None:
        self._fh.close()

    def __enter__(self) -> "ScenarioWriter":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
```

`arcade/sources/replay.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator

from arcade.sensed import Audio, Sensed
from arcade.sources.scenario import ScenarioReader


class ReplayStream:
    """Shared cursor over recorded Sensed records. Holds the last record after the end."""

    def __init__(self, records: Iterable[Sensed]):
        self._it: Iterator[Sensed] = iter(records)
        self.current: Sensed | None = None
        self.finished = False

    def advance(self) -> Sensed:
        if not self.finished:
            try:
                self.current = next(self._it)
            except StopIteration:
                self.finished = True
        if self.current is None:
            self.current = Sensed(0.0)
        return self.current


class ReplayCamera:
    available = True

    def __init__(self, stream: ReplayStream):
        self.stream = stream

    def latest(self):
        s = self.stream.advance()
        return (s.bodies, s.blobs, s.motion)

    def close(self) -> None:
        pass


class ReplayAudio:
    available = True

    def __init__(self, stream: ReplayStream):
        self.stream = stream

    def latest(self) -> Audio:
        return self.stream.current.audio if self.stream.current is not None else Audio()

    def close(self) -> None:
        pass


def open_replay(path: Path | str) -> tuple[ReplayCamera, ReplayAudio]:
    stream = ReplayStream(ScenarioReader(path))
    return ReplayCamera(stream), ReplayAudio(stream)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/arcade/test_scenario.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add arcade/sources/scenario.py arcade/sources/replay.py tests/arcade/test_scenario.py
git commit -m "feat(arcade): scenario files and replay sources"
```

---

### Task 13: Contact sheet tool

**Files:**
- Create: `tools/arcade_shot.py`
- Test: `tests/arcade/test_shot.py`

**Interfaces:**
- Consumes: `run_headless` (Task 8), `render` (Task 6), `get_game` (Task 7), actors (Task 4), `ScenarioReader` (Task 12), `Canvas`, `Font`.
- Produces: `tools/arcade_shot.py` with `main(argv) -> Path`, `contact_sheet(frames, indices, mode, scale, gamma, font, cols) -> np.ndarray`, `ACTOR_NAMESPACE`, `build_inputs(args) -> Iterable[Sensed]`.

Usage: `python tools/arcade_shot.py --game paint --blob "moving_blob(0.1,0.5,0.9,0.5,2)" --ticks 90 --every 10 --look led --out shots/paint.png`. Repeat `--person`, `--blob` for more actors; `--audio` once; `--scenario file.jsonl` instead of actors; `--size 128x32`. Expressions are evaluated with only the actor builders in scope.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_shot.py`:

```python
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import arcade_shot  # noqa: E402


def test_contact_sheet_geometry(font5x7):
    frames = [np.zeros((32, 64, 3), np.uint8) for _ in range(3)]
    sheet = arcade_shot.contact_sheet(frames, [0, 1, 2], "plain", 2, 1.0, font5x7, cols=2)
    gap = arcade_shot.GAP
    assert sheet.shape == (gap + 2 * (16 + 64 + gap), gap + 2 * (128 + gap), 3)


def test_main_writes_png_from_actors(tmp_path):
    out = tmp_path / "paint.png"
    path = arcade_shot.main(["--game", "paint", "--blob", "moving_blob(0.1,0.5,0.9,0.5,1.0)",
                             "--ticks", "30", "--every", "10", "--size", "64x64", "--scale", "2",
                             "--look", "led", "--out", str(out)])
    assert path == out and out.exists()
    img = Image.open(out)
    assert img.size[0] == arcade_shot.GAP + 3 * (128 + arcade_shot.GAP)
    assert np.asarray(img).max() > 0


def test_main_from_scenario(tmp_path):
    from arcade.sources.actors import Person, scene
    from arcade.sources.scenario import ScenarioWriter

    rec = tmp_path / "rec.jsonl"
    with ScenarioWriter(rec) as w:
        for s in scene(persons=[Person()], ticks=5):
            w.write(s)
    out = tmp_path / "puppet.png"
    arcade_shot.main(["--game", "puppet", "--scenario", str(rec), "--every", "2", "--out", str(out)])
    assert out.exists()


def test_bad_expression_is_rejected(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        arcade_shot.main(["--game", "paint", "--blob", "__import__('os')", "--out", str(tmp_path / "x.png")])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/arcade/test_shot.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arcade_shot'`

- [ ] **Step 3: Implement the tool**

`tools/arcade_shot.py`:

```python
#!/usr/bin/env python3
"""Run a game headlessly and write a labelled contact sheet of frames.

    python tools/arcade_shot.py --game paint --blob "moving_blob(0.1,0.5,0.9,0.5,2)" \
        --ticks 90 --every 10 --look led --out shots/paint.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arcade.canvas import Canvas  # noqa: E402
from arcade.config import ArcadeConfig  # noqa: E402
from arcade.games import get_game  # noqa: E402
from arcade.headless import run_headless  # noqa: E402
from arcade.look import render  # noqa: E402
from arcade.sensed import Sensed  # noqa: E402
from arcade.sources import actors  # noqa: E402
from arcade.sources.scenario import ScenarioReader  # noqa: E402
from show.font import CELL_H, Font  # noqa: E402

GAP = 4
LABEL_H = CELL_H
ACTOR_NAMESPACE = {name: getattr(actors, name) for name in
                   ("Person", "moving_blob", "silence", "claps", "tempo", "loud")}


def evaluate(expr: str):
    try:
        return eval(expr, {"__builtins__": {}}, dict(ACTOR_NAMESPACE))  # noqa: S307 - dev tool, closed namespace
    except Exception as e:
        raise ValueError(f"bad actor expression {expr!r}: {e}") from e


def parse_size(text: str) -> tuple[int, int]:
    w, h = text.lower().split("x")
    return int(w), int(h)


def build_inputs(args) -> Iterable[Sensed]:
    if args.scenario:
        return ScenarioReader(args.scenario)
    persons = [evaluate(p) for p in args.person]
    blobs = [evaluate(b) for b in args.blob]
    audio = evaluate(args.audio) if args.audio else None
    return actors.scene(persons=persons, blobs=blobs, audio=audio, ticks=args.ticks)


def contact_sheet(frames: list[np.ndarray], indices: list[int], mode: str, scale: int, gamma: float,
                  font: Font, cols: int) -> np.ndarray:
    h, w = frames[0].shape[:2]
    cell_w, cell_h = w * scale, LABEL_H * scale + h * scale
    cols = max(1, min(cols, len(indices)))
    rows = (len(indices) + cols - 1) // cols
    sheet = np.zeros((GAP + rows * (cell_h + GAP), GAP + cols * (cell_w + GAP), 3), np.uint8)
    for n, idx in enumerate(indices):
        label = Canvas(w, LABEL_H, font)
        label.text(0, 0, f"t{idx}", (200, 200, 200))
        cell = np.concatenate([render(label.frame, "plain", scale, 1.0),
                               render(frames[idx], mode, scale, gamma)], axis=0)
        y = GAP + (n // cols) * (cell_h + GAP)
        x = GAP + (n % cols) * (cell_w + GAP)
        sheet[y:y + cell_h, x:x + cell_w] = cell
    return sheet


def main(argv: list[str] | None = None) -> Path:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--game", required=True)
    p.add_argument("--size", default="64x64")
    p.add_argument("--ticks", type=int, default=90)
    p.add_argument("--every", type=int, default=10)
    p.add_argument("--look", default="led", choices=("plain", "led", "distance"))
    p.add_argument("--scale", type=int, default=6)
    p.add_argument("--gamma", type=float, default=2.2)
    p.add_argument("--cols", type=int, default=6)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--person", action="append", default=[])
    p.add_argument("--blob", action="append", default=[])
    p.add_argument("--audio", default=None)
    p.add_argument("--scenario", default=None)
    p.add_argument("--font", default=str(ROOT / "fonts" / "5x7.bin"))
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)

    w, h = parse_size(args.size)
    cfg = ArcadeConfig(width=w, height=h, backend="fake", camera="none", audio="none")
    font = Font.load(Path(args.font))
    frames, _ = run_headless(cfg, font, get_game(args.game), build_inputs(args), seed=args.seed)
    if not frames:
        raise ValueError("no frames produced; check --ticks or the scenario file")
    indices = list(range(0, len(frames), max(1, args.every)))
    sheet = contact_sheet(frames, indices, args.look, args.scale, args.gamma, font, args.cols)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(sheet).save(out)
    print(out)
    return out


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/arcade/test_shot.py -v`
Expected: 4 passed. Then look at one yourself: `python tools/arcade_shot.py --game puppet --person "Person(0.3).walk(0.7,3).raise_hand(1.5,1)" --out shots/puppet.png` and open `shots/puppet.png`. Add `shots/` to `.gitignore`.

- [ ] **Step 5: Commit**

```bash
git add tools/arcade_shot.py tests/arcade/test_shot.py .gitignore
git commit -m "feat(arcade): contact sheet tool for headless visual checks"
```

---

### Task 14: Step-verb REPL for agents

**Files:**
- Create: `tools/arcade_play.py`
- Test: `tests/arcade/test_play.py`

**Interfaces:**
- Consumes: `Runner`, `RecordingDisplay`, `NullMenu` (Task 8), `Menu` (Task 9), `all_games`, `get_game` (Task 7), actors (Task 4), `render` (Task 6).
- Produces: `tools/arcade_play.py` with `Session(cfg, font, game=None, seed=0)` exposing `execute(line) -> str` and `main(argv)`. Verbs, one per line on stdin, each answered with one line:

```
step N [x=0.3] [y=0.55] [hand=left|right|both|none] [jump=0.2] [blob=x,y[,r,g,b]] [clap] [level=0.8] [beat=120] [none]
state
shot PATH.png
launch NAME
menu
reset
quit
```

`step` holds the described input for N ticks and replies with the runner state as JSON. `x=` puts one standing body at that position; `none` means nobody present; `hand=` raises a wrist; `jump=` lifts the body by that fraction; `blob=` adds a bright blob; `clap` fires an onset on the first tick only; `level=` sets the audio level; `beat=` marks a beat on the first tick with that tempo.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_play.py`:

```python
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import arcade_play  # noqa: E402

from tests.arcade.helpers import make_cfg


def session(font5x7, size=(64, 64), game=None):
    return arcade_play.Session(make_cfg(size), font5x7, game=game, seed=0)


def test_step_and_state_on_a_game(font5x7):
    s = session(font5x7, game="puppet")
    reply = json.loads(s.execute("step 3 x=0.3 hand=right"))
    assert reply["game"] == "puppet" and reply["bodies"] == 1 and reply["t"] > 0
    reply = json.loads(s.execute("step 2 none"))
    assert reply["bodies"] == 0
    assert json.loads(s.execute("state"))["game"] == "puppet"


def test_menu_dwell_via_steps(font5x7):
    s = session(font5x7)
    st = json.loads(s.execute("state"))
    assert st["game"] == "menu"
    x, y, w, h = s.runner.menu.tiles[0]
    reply = json.loads(s.execute(f"step 40 blob={(x + 5) / 64:.3f},{(y + 5) / 64:.3f}"))
    assert reply["game"] == "paint"
    s.execute("menu")
    assert json.loads(s.execute("state"))["game"] == "menu"
    s.execute("launch puppet")
    assert json.loads(s.execute("state"))["game"] == "puppet"


def test_shot_and_reset_and_errors(font5x7, tmp_path):
    s = session(font5x7, game="paint")
    s.execute("step 10 blob=0.5,0.5,255,0,0")
    out = tmp_path / "f.png"
    assert s.execute(f"shot {out}").startswith("wrote") and out.exists()
    assert json.loads(s.execute("state"))["lit"] > 0
    s.execute("reset")
    assert json.loads(s.execute("state"))["lit"] == 0
    assert s.execute("bogus").startswith("error")
    assert s.execute("step x").startswith("error")
    assert s.execute("launch nope").startswith("error")


def test_main_reads_stdin(font5x7, monkeypatch, capsys):
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO("step 1 x=0.5\nquit\n"))
    arcade_play.main(["--game", "puppet", "--size", "64x64"])
    out = capsys.readouterr().out.strip().splitlines()
    assert json.loads(out[0])["bodies"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/arcade/test_play.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arcade_play'`

- [ ] **Step 3: Implement**

`tools/arcade_play.py`:

```python
#!/usr/bin/env python3
"""Step-verb REPL so an agent can probe a game deterministically without a window.

    python tools/arcade_play.py --game frogger
    step 30 x=0.2
    step 15 x=0.2 hand=right
    state
    shot /tmp/frogger.png
    quit
"""
from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arcade.config import ArcadeConfig  # noqa: E402
from arcade.games import all_games, get_game  # noqa: E402
from arcade.headless import RecordingDisplay  # noqa: E402
from arcade.look import render  # noqa: E402
from arcade.menu import Menu  # noqa: E402
from arcade.runner import Runner  # noqa: E402
from arcade.sensed import Audio, Blob, Sensed  # noqa: E402
from arcade.sources.actors import TICK, body_box, make_keypoints  # noqa: E402
from arcade.sensed import Body  # noqa: E402
from show.font import Font  # noqa: E402

HELP = "verbs: step N [x= y= hand= jump= blob= clap level= beat= none] | state | shot PATH | launch NAME | menu | reset | quit"


def parse_step(tokens: list[str]) -> tuple[int, dict]:
    if not tokens or not tokens[0].isdigit():
        raise ValueError("step needs a tick count: step N ...")
    n = int(tokens[0])
    spec: dict = {"x": 0.5, "y": 0.55, "hand": "none", "jump": 0.0, "blob": None, "clap": False,
                  "level": 0.0, "beat": None, "body": False}
    for tok in tokens[1:]:
        if tok == "none":
            spec["body"] = False
            spec["_none"] = True
        elif tok == "clap":
            spec["clap"] = True
        elif "=" in tok:
            key, value = tok.split("=", 1)
            if key in ("x", "y", "jump", "level"):
                spec[key] = float(value)
                if key in ("x", "y", "jump"):
                    spec["body"] = True
            elif key == "hand":
                spec["hand"] = value
                spec["body"] = True
            elif key == "blob":
                parts = [float(v) for v in value.split(",")]
                color = tuple(int(v) for v in parts[2:5]) if len(parts) >= 5 else (255, 255, 255)
                spec["blob"] = Blob(parts[0], parts[1], 0.03, color)
            elif key == "beat":
                spec["beat"] = float(value)
            else:
                raise ValueError(f"unknown key {key!r}")
        else:
            raise ValueError(f"unknown token {tok!r}")
    if spec.get("_none"):
        spec["body"] = False
    return n, spec


def sensed_from(spec: dict, t: float, first: bool) -> Sensed:
    bodies = ()
    if spec["body"]:
        hand = spec["hand"]
        kps = make_keypoints(spec["x"], spec["y"] - spec["jump"], 0.6,
                             left_up=hand in ("left", "both"), right_up=hand in ("right", "both"))
        bodies = (Body(0, body_box(kps), kps),)
    blobs = (spec["blob"],) if spec["blob"] is not None else ()
    onset = spec["clap"] and first
    beat = spec["beat"] is not None and first
    audio = Audio(level=max(spec["level"], 0.8 if onset else 0.0), peak=1.0 if onset else spec["level"],
                  onset=onset or beat, beat=beat, bpm=spec["beat"])
    return Sensed(t, bodies, blobs, None, audio)


class Session:
    def __init__(self, cfg: ArcadeConfig, font: Font, game: str | None = None, seed: int = 0):
        self.cfg, self.font, self.seed = cfg, font, seed
        self.display = RecordingDisplay(keep_all=False)
        self.menu = Menu(all_games(), cfg)
        self.runner = Runner(cfg, self.display, font, self.menu, all_games(), seed=seed)
        self.runner.menu.set_status(True, True, {"pose", "blobs", "motion", "audio"})
        if game is not None:
            self.runner.launch(get_game(game).info.name)

    def execute(self, line: str) -> str:
        try:
            tokens = shlex.split(line)
            if not tokens:
                return HELP
            verb, rest = tokens[0], tokens[1:]
            if verb == "step":
                n, spec = parse_step(rest)
                for i in range(n):
                    self.runner.tick(sensed_from(spec, self.runner.t, i == 0), TICK)
                return json.dumps(self.runner.state())
            if verb == "state":
                return json.dumps(self.runner.state())
            if verb == "shot":
                if not rest:
                    raise ValueError("shot needs a path")
                frame = self.display.last if self.display.last is not None else self.runner.canvas.frame
                img = render(frame, self.cfg.look, self.cfg.sdl_scale, self.cfg.gamma)
                Path(rest[0]).parent.mkdir(parents=True, exist_ok=True)
                Image.fromarray(img).save(rest[0])
                return f"wrote {rest[0]}"
            if verb == "launch":
                if not rest:
                    raise ValueError("launch needs a game name")
                self.runner.launch(get_game(rest[0]).info.name)
                return json.dumps(self.runner.state())
            if verb == "menu":
                self.runner.go_menu()
                return json.dumps(self.runner.state())
            if verb == "reset":
                if self.runner.current is self.runner.menu:
                    self.runner.go_menu()
                else:
                    self.runner.launch(self.runner.current_name)
                return json.dumps(self.runner.state())
            if verb in ("help", "?"):
                return HELP
            raise ValueError(f"unknown verb {verb!r}")
        except KeyError as e:
            return f"error: unknown game {e}"
        except Exception as e:  # the REPL must never die on a typo
            return f"error: {e}"


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--game", default=None)
    p.add_argument("--size", default="64x64")
    p.add_argument("--look", default="led", choices=("plain", "led", "distance"))
    p.add_argument("--scale", type=int, default=6)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--font", default=str(ROOT / "fonts" / "5x7.bin"))
    args = p.parse_args(argv)
    w, h = (int(v) for v in args.size.lower().split("x"))
    cfg = ArcadeConfig(width=w, height=h, backend="fake", camera="none", audio="none",
                       look=args.look, sdl_scale=args.scale)
    session = Session(cfg, Font.load(Path(args.font)), game=args.game, seed=args.seed)
    for line in sys.stdin:
        line = line.strip()
        if line == "quit":
            break
        print(session.execute(line), flush=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/arcade/test_play.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add tools/arcade_play.py tests/arcade/test_play.py
git commit -m "feat(arcade): step-verb REPL for agent playtesting"
```

---

### Task 15: Blobs and motion from camera frames

**Files:**
- Create: `arcade/sources/blobs.py`
- Test: `tests/arcade/test_blobs.py`

**Interfaces:**
- Consumes: `Blob` (Task 3).
- Produces: `find_blobs(frame_bgr, max_blobs=8, min_area=4, floor=200) -> tuple[Blob, ...]`, `motion_grid(prev_gray, gray, size, threshold=25, fill=0.1) -> np.ndarray` (bool, `(h, w)`), `FrameFeatures(size)` with `update(frame_bgr) -> (blobs, motion)`.

Frames are BGR uint8 `(H, W, 3)`, OpenCV's order. Brightness for blob detection is the per-pixel maximum channel, not luminance, so a saturated red glow stick counts as bright. Blob `size` is `sqrt(area) / frame_width`. Colours are returned as RGB.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_blobs.py`:

```python
import cv2
import numpy as np
import pytest

from arcade.sources.blobs import FrameFeatures, find_blobs, motion_grid


def dark_frame(w=64, h=48, level=30):
    return np.full((h, w, 3), level, np.uint8)


def test_bright_disc_becomes_one_blob_with_rgb_colour():
    f = dark_frame()
    cv2.circle(f, (48, 12), 4, (0, 0, 255), -1)  # BGR red
    blobs = find_blobs(f)
    assert len(blobs) == 1
    b = blobs[0]
    assert b.x == pytest.approx(48 / 64, abs=0.02) and b.y == pytest.approx(12 / 48, abs=0.03)
    assert b.color == (255, 0, 0) and 0.05 < b.size < 0.15


def test_blobs_sorted_by_size_and_capped():
    f = dark_frame(128, 96)
    for i in range(10):
        cv2.circle(f, (10 + i * 11, 40), 1 + i % 3, (255, 255, 255), -1)
    cv2.circle(f, (100, 80), 8, (255, 255, 255), -1)
    blobs = find_blobs(f, max_blobs=5)
    assert len(blobs) == 5 and blobs[0].x == pytest.approx(100 / 128, abs=0.02)
    assert all(blobs[i].size >= blobs[i + 1].size for i in range(4))


def test_no_blobs_in_a_dim_frame():
    assert find_blobs(dark_frame(level=120)) == ()


def test_motion_grid_marks_changed_region_only():
    a = np.zeros((48, 64), np.uint8)
    b = a.copy()
    b[24:48, 32:64] = 200
    g = motion_grid(a, b, (16, 12))
    assert g.shape == (12, 16) and g.dtype == bool
    assert g[6:, 8:].all() and not g[:6].any() and not g[:, :8].any()


def test_frame_features_first_frame_has_no_motion():
    ff = FrameFeatures((16, 12))
    blobs, motion = ff.update(dark_frame())
    assert blobs == () and motion.shape == (12, 16) and not motion.any()
    f = dark_frame()
    f[:, 32:] = 255
    blobs, motion = ff.update(f)
    assert motion[:, 8:].all() and len(blobs) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/arcade/test_blobs.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arcade.sources.blobs'`

- [ ] **Step 3: Implement**

`arcade/sources/blobs.py`:

```python
"""Bright-blob and motion extraction from a BGR camera frame. Needs no model."""
from __future__ import annotations

import cv2
import numpy as np

from arcade.sensed import Blob


def find_blobs(frame_bgr: np.ndarray, max_blobs: int = 8, min_area: int = 4, floor: int = 200) -> tuple[Blob, ...]:
    bright = frame_bgr.max(axis=2)
    threshold = max(floor, int(np.percentile(bright, 99.5)))
    mask = (bright >= threshold).astype(np.uint8)
    if not mask.any():
        return ()
    n, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    h, w = bright.shape
    comps = sorted(((int(stats[i, cv2.CC_STAT_AREA]), i) for i in range(1, n)
                    if stats[i, cv2.CC_STAT_AREA] >= min_area), reverse=True)
    blobs = []
    for area, i in comps[:max_blobs]:
        cx, cy = centroids[i]
        b, g, r = frame_bgr[labels == i].mean(axis=0)
        blobs.append(Blob(float(cx) / w, float(cy) / h, float(np.sqrt(area)) / w, (int(r), int(g), int(b))))
    return tuple(blobs)


def motion_grid(prev_gray: np.ndarray, gray: np.ndarray, size: tuple[int, int],
                threshold: int = 25, fill: float = 0.1) -> np.ndarray:
    moving = (cv2.absdiff(prev_gray, gray) > threshold).astype(np.float32)
    small = cv2.resize(moving, size, interpolation=cv2.INTER_AREA)
    return small > fill


class FrameFeatures:
    def __init__(self, size: tuple[int, int]):
        self.size = size
        self._prev: np.ndarray | None = None

    def update(self, frame_bgr: np.ndarray) -> tuple[tuple[Blob, ...], np.ndarray]:
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        blobs = find_blobs(frame_bgr)
        if self._prev is None or self._prev.shape != gray.shape:
            motion = np.zeros((self.size[1], self.size[0]), dtype=bool)
        else:
            motion = motion_grid(self._prev, gray, self.size)
        self._prev = gray
        return blobs, motion
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/arcade/test_blobs.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add arcade/sources/blobs.py tests/arcade/test_blobs.py
git commit -m "feat(arcade): bright-blob and motion extraction"
```

---

### Task 16: Camera source base, body tracker, MediaPipe camera, model fetch

**Files:**
- Create: `arcade/sources/camera.py`, `arcade/sources/pose_mediapipe.py`, `tools/fetch_models.py`
- Test: `tests/arcade/test_camera.py`, `tests/arcade/test_pose_mediapipe.py`, `tests/arcade/test_fetch_models.py`

**Interfaces:**
- Consumes: `Body`, `Blob`, `Keypoint` (Task 3), `FrameFeatures` (Task 15).
- Produces: `CameraSource` protocol (`available: bool`, `latest() -> (bodies, blobs, motion)`, `close()`); `EMPTY = ((), (), None)`; `NoCamera`; `ThreadedCamera` base with `start()`, `step()` to override, `latest()`, `close()`; `BodyTracker(max_dist=0.2, max_missed=10)` with `update(detections: list[tuple[box, keypoints]]) -> tuple[Body, ...]`; `MP_TO_COCO`, `MODEL_URL`, `MODEL_PATH`, `landmarks_to_keypoints(landmarks) -> tuple[Keypoint, ...]`, `box_of(keypoints, min_conf=0.3) -> box`, `MediaPipeCamera(size, index=0, mirror=True, model_path=MODEL_PATH)`; `tools/fetch_models.py` with `fetch(dest_dir, urlopen=urllib.request.urlopen) -> list[Path]`.

MediaPipe facts used here (from its Python docs): the Tasks API, `PoseLandmarker.create_from_options` with `running_mode=VIDEO` and `num_poses=2`; `detect_for_video(mp.Image, timestamp_ms)` needs strictly increasing timestamps; `result.pose_landmarks` is a list per person of 33 `NormalizedLandmark` with `.x`, `.y`, `.visibility`; the image must be RGB. The lite model URL is `https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task` (verified reachable on 2026-09-26).

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_camera.py`:

```python
import threading
import time

from arcade.sensed import Keypoint
from arcade.sources.actors import body_box, make_keypoints
from arcade.sources.camera import EMPTY, BodyTracker, NoCamera, ThreadedCamera


def det(cx, cy, conf=1.0):
    kps = make_keypoints(cx, cy, 0.5, conf=conf)
    return (body_box(kps), kps)


def test_no_camera():
    c = NoCamera()
    assert c.available is False and c.latest() == EMPTY
    c.close()


def test_tracker_keeps_ids_when_two_people_cross():
    tr = BodyTracker()
    first = tr.update([det(0.2, 0.3), det(0.8, 0.7)])
    ids = {round(b.center[1], 1): b.id for b in first}
    for i in range(1, 21):
        x = 0.2 + 0.6 * i / 20
        bodies = tr.update([det(x, 0.3), det(1.0 - x, 0.7)])
        for b in bodies:
            assert b.id == ids[round(b.center[1], 1)]
    assert len({b.id for b in bodies}) == 2


def test_tracker_orders_by_confidence_and_handles_gaps():
    tr = BodyTracker(max_missed=3)
    bodies = tr.update([det(0.3, 0.5, conf=0.5), det(0.7, 0.5, conf=0.9)])
    assert bodies[0].center[0] > 0.5 and bodies[0].id != bodies[1].id
    lost_id = bodies[1].id
    for _ in range(3):
        tr.update([det(0.7, 0.5)])
    back = tr.update([det(0.31, 0.5), det(0.7, 0.5)])
    assert {b.id for b in back} >= {lost_id}
    for _ in range(4):
        tr.update([])
    fresh = tr.update([det(0.31, 0.5)])
    assert fresh[0].id not in (lost_id, bodies[0].id)


class DyingCamera(ThreadedCamera):
    def __init__(self):
        super().__init__()
        self.calls = 0
        self.died = threading.Event()

    def step(self):
        self.calls += 1
        if self.calls == 1:
            return ((), (), None)
        self.died.set()
        raise RuntimeError("usb unplugged")


def test_threaded_camera_reports_unavailable_when_its_thread_dies():
    cam = DyingCamera()
    cam.available = True
    cam.start()
    assert cam.died.wait(2.0)
    for _ in range(50):
        if not cam.available:
            break
        time.sleep(0.01)
    assert cam.available is False and cam.latest() == EMPTY
    cam.close()
```

`tests/arcade/test_pose_mediapipe.py`:

```python
from types import SimpleNamespace

from arcade.sensed import LEFT_SHOULDER, LEFT_WRIST, NOSE, RIGHT_ANKLE
from arcade.sources.camera import EMPTY
from arcade.sources.pose_mediapipe import MP_TO_COCO, MediaPipeCamera, box_of, landmarks_to_keypoints


def fake_landmarks():
    return [SimpleNamespace(x=i / 100, y=i / 50, visibility=0.9 if i != 15 else 0.1) for i in range(33)]


def test_landmark_mapping():
    kps = landmarks_to_keypoints(fake_landmarks())
    assert len(kps) == 17 and len(MP_TO_COCO) == 17
    assert kps[NOSE].x == 0.0
    assert kps[LEFT_SHOULDER].x == 0.11
    assert kps[LEFT_WRIST].x == 0.15 and kps[LEFT_WRIST].conf == 0.1
    assert kps[RIGHT_ANKLE].x == 0.28


def test_box_ignores_low_confidence_points():
    kps = landmarks_to_keypoints(fake_landmarks())
    x0, y0, x1, y1 = box_of(kps)
    assert x0 == 0.0 and x1 == 0.28 and y1 == min(1.0, 0.56)
    none = box_of(tuple(k.__class__(k.x, k.y, 0.0) for k in kps))
    assert none == (0.0, 0.0, 0.0, 0.0)


def test_camera_without_model_is_unavailable(tmp_path):
    cam = MediaPipeCamera((64, 64), index=99, model_path=tmp_path / "missing.task")
    assert cam.available is False and cam.latest() == EMPTY
    cam.close()
```

`tests/arcade/test_fetch_models.py`:

```python
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import fetch_models  # noqa: E402


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def test_fetch_writes_missing_models_and_skips_existing(tmp_path):
    calls = []

    def fake_urlopen(url):
        calls.append(url)
        return FakeResponse(b"MODELBYTES")

    written = fetch_models.fetch(tmp_path, urlopen=fake_urlopen)
    assert [p.name for p in written] == list(fetch_models.MODELS)
    assert (tmp_path / "pose_landmarker_lite.task").read_bytes() == b"MODELBYTES"
    assert calls == list(fetch_models.MODELS.values())
    assert fetch_models.fetch(tmp_path, urlopen=fake_urlopen) == []
    assert len(calls) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/arcade/test_camera.py tests/arcade/test_pose_mediapipe.py tests/arcade/test_fetch_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arcade.sources.camera'`

- [ ] **Step 3: Implement**

`arcade/sources/camera.py`:

```python
from __future__ import annotations

import logging
import math
import threading
from typing import Protocol

import numpy as np

from arcade.sensed import Blob, Body, Keypoint

log = logging.getLogger("arcade")

Detections = list[tuple[tuple[float, float, float, float], tuple[Keypoint, ...]]]
CameraResult = tuple[tuple[Body, ...], tuple[Blob, ...], "np.ndarray | None"]
EMPTY: CameraResult = ((), (), None)


class CameraSource(Protocol):
    available: bool

    def latest(self) -> CameraResult: ...
    def close(self) -> None: ...


class NoCamera:
    available = False

    def latest(self) -> CameraResult:
        return EMPTY

    def close(self) -> None:
        pass


class BodyTracker:
    """Assigns stable ids by nearest centre across frames. Never reuses an id."""

    def __init__(self, max_dist: float = 0.2, max_missed: int = 10):
        self.max_dist, self.max_missed = max_dist, max_missed
        self._tracks: dict[int, tuple[tuple[float, float], int]] = {}
        self._next = 1

    def update(self, detections: Detections) -> tuple[Body, ...]:
        dets = []
        for box, kps in detections:
            center = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
            conf = sum(k.conf for k in kps) / len(kps)
            dets.append((conf, center, box, kps))
        dets.sort(key=lambda d: -d[0])
        unmatched = set(self._tracks)
        bodies = []
        for conf, center, box, kps in dets:
            best, best_d = None, self.max_dist
            for tid in unmatched:
                (tx, ty), _ = self._tracks[tid]
                d = math.hypot(center[0] - tx, center[1] - ty)
                if d < best_d:
                    best, best_d = tid, d
            if best is None:
                best = self._next
                self._next += 1
            else:
                unmatched.discard(best)
            self._tracks[best] = (center, 0)
            bodies.append(Body(best, box, kps))
        for tid in unmatched:
            center, missed = self._tracks[tid]
            if missed + 1 > self.max_missed:
                del self._tracks[tid]
            else:
                self._tracks[tid] = (center, missed + 1)
        return tuple(bodies)


class ThreadedCamera:
    """Runs step() in a daemon thread and publishes its result. A failing step marks the source unavailable."""

    def __init__(self):
        self._lock = threading.Lock()
        self._latest: CameraResult = EMPTY
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.available = False

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name=type(self).__name__, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            while not self._stop.is_set():
                result = self.step()
                if result is not None:
                    with self._lock:
                        self._latest = result
        except Exception:
            log.exception("%s thread died; camera unavailable", type(self).__name__)
            with self._lock:
                self._latest = EMPTY
            self.available = False

    def step(self) -> CameraResult | None:
        raise NotImplementedError

    def latest(self) -> CameraResult:
        with self._lock:
            return self._latest

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
```

`arcade/sources/pose_mediapipe.py`:

```python
"""Mac camera: OpenCV webcam + MediaPipe Pose Landmarker (Tasks API, VIDEO mode)."""
from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np

from arcade.sensed import MIN_CONF, Keypoint
from arcade.sources.blobs import FrameFeatures
from arcade.sources.camera import BodyTracker, CameraResult, ThreadedCamera

log = logging.getLogger("arcade")

# MediaPipe's 33 landmarks -> COCO 17: nose, eyes, ears, shoulders, elbows, wrists, hips, knees, ankles.
MP_TO_COCO = (0, 2, 5, 7, 8, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28)
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/"
             "float16/1/pose_landmarker_lite.task")
MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "pose_landmarker_lite.task"
CAPTURE_SIZE = (640, 480)


def landmarks_to_keypoints(landmarks) -> tuple[Keypoint, ...]:
    out = []
    for i in MP_TO_COCO:
        lm = landmarks[i]
        vis = getattr(lm, "visibility", None)
        out.append(Keypoint(float(lm.x), float(lm.y), 1.0 if vis is None else float(vis)))
    return tuple(out)


def box_of(keypoints: tuple[Keypoint, ...], min_conf: float = MIN_CONF) -> tuple[float, float, float, float]:
    pts = [k for k in keypoints if k.conf >= min_conf]
    if not pts:
        return (0.0, 0.0, 0.0, 0.0)
    clamp = lambda v: min(1.0, max(0.0, v))
    return (clamp(min(k.x for k in pts)), clamp(min(k.y for k in pts)),
            clamp(max(k.x for k in pts)), clamp(max(k.y for k in pts)))


class MediaPipeCamera(ThreadedCamera):
    def __init__(self, size: tuple[int, int], index: int = 0, mirror: bool = True,
                 model_path: Path = MODEL_PATH, clock=time.monotonic):
        super().__init__()
        self.size, self.mirror, self.clock = size, mirror, clock
        self.tracker = BodyTracker()
        self.features = FrameFeatures(size)
        self._t0 = clock()
        self._last_ts = -1
        try:
            import cv2
            import mediapipe as mp
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision

            if not Path(model_path).exists():
                raise FileNotFoundError(f"{model_path} missing; run: python tools/fetch_models.py")
            self._cv2, self._mp = cv2, mp
            self._cap = cv2.VideoCapture(index)
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_SIZE[0])
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_SIZE[1])
            if not self._cap.isOpened():
                raise RuntimeError(f"camera index {index} did not open")
            options = vision.PoseLandmarkerOptions(
                base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
                running_mode=vision.RunningMode.VIDEO, num_poses=2)
            self._landmarker = vision.PoseLandmarker.create_from_options(options)
            self.available = True
            self.start()
        except Exception as e:
            log.warning("mediapipe camera unavailable: %s", e)
            self.available = False

    def step(self) -> CameraResult | None:
        ok, frame = self._cap.read()
        if not ok:
            raise RuntimeError("camera read failed")
        if self.mirror:
            frame = self._cv2.flip(frame, 1)
        rgb = self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2RGB)
        ts = max(self._last_ts + 1, int((self.clock() - self._t0) * 1000))
        self._last_ts = ts
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        result = self._landmarker.detect_for_video(image, ts)
        detections = []
        for landmarks in result.pose_landmarks:
            kps = landmarks_to_keypoints(landmarks)
            detections.append((box_of(kps), kps))
        bodies = self.tracker.update(detections)
        blobs, motion = self.features.update(frame)
        return (bodies, blobs, motion)

    def close(self) -> None:
        super().close()
        cap = getattr(self, "_cap", None)
        if cap is not None:
            cap.release()
        lm = getattr(self, "_landmarker", None)
        if lm is not None:
            lm.close()
```

`tools/fetch_models.py`:

```python
#!/usr/bin/env python3
"""Download the model files the Mac camera source needs into models/ (gitignored)."""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arcade.sources.pose_mediapipe import MODEL_URL  # noqa: E402

MODELS = {"pose_landmarker_lite.task": MODEL_URL}


def fetch(dest_dir: Path, urlopen=urllib.request.urlopen) -> list[Path]:
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, url in MODELS.items():
        target = dest_dir / name
        if target.exists() and target.stat().st_size > 0:
            continue
        with urlopen(url) as resp:
            data = resp.read()
        target.write_bytes(data)
        written.append(target)
    return written


if __name__ == "__main__":
    for p in fetch(ROOT / "models"):
        print(f"fetched {p}")
```

Add `models/` to `.gitignore`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/arcade/test_camera.py tests/arcade/test_pose_mediapipe.py tests/arcade/test_fetch_models.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add arcade/sources/camera.py arcade/sources/pose_mediapipe.py tools/fetch_models.py .gitignore tests/arcade/test_camera.py tests/arcade/test_pose_mediapipe.py tests/arcade/test_fetch_models.py
git commit -m "feat(arcade): body tracker, threaded camera base, MediaPipe camera, model fetch"
```

---

### Task 17: Audio source and features

**Files:**
- Create: `arcade/sources/audio.py`
- Test: `tests/arcade/test_audio.py`

**Interfaces:**
- Consumes: `Audio` (Task 3).
- Produces: `AudioSource` protocol (`available`, `latest() -> Audio`, `close()`); `NoAudio`; `RATE = 16000`; `AudioFeatures(rate=RATE)` with `feed(samples: np.ndarray)` and `latest(t: float) -> Audio`; `SoundDeviceAudio(clock=time.monotonic)`.

Feature definitions: `level` is the RMS of the last 50 ms divided by a slowly decaying running maximum (an automatic gain so a quiet field and a sound camp both span 0..1); `peak` is the raw peak; `onset` fires when the 50 ms energy exceeds three times the median of the last 20 ticks, rose by at least half over the previous tick, is above an absolute floor, and at least 100 ms passed since the last onset; `bpm` is `60 / median interval` of the last eight onsets when every interval is within 15 percent of that median and between 0.25 and 2 s, else `None`; `beat` is `onset and bpm is not None`.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_audio.py`:

```python
import numpy as np
import pytest

from arcade.sensed import Audio
from arcade.sources.audio import RATE, AudioFeatures, NoAudio, SoundDeviceAudio

TICK = 1 / 30
CHUNK = int(RATE * TICK)


def burst(amplitude=0.5, n=CHUNK):
    return amplitude * np.where(np.arange(n) % 2 == 0, 1.0, -1.0).astype(np.float32)


def quiet(n=CHUNK):
    return np.zeros(n, np.float32)


def drive(features, pattern):
    """pattern: iterable of bools per tick (True = burst). Returns list of Audio."""
    out = []
    for i, loud in enumerate(pattern):
        features.feed(burst() if loud else quiet())
        out.append(features.latest(i * TICK))
    return out


def test_silence_is_quiet_and_no_onset():
    f = AudioFeatures()
    out = drive(f, [False] * 40)
    assert all(a.level == 0.0 and not a.onset and a.bpm is None for a in out)


def test_single_clap_fires_one_onset():
    f = AudioFeatures()
    out = drive(f, [False] * 30 + [True] + [False] * 20)
    onsets = [i for i, a in enumerate(out) if a.onset]
    assert onsets == [30]
    assert out[30].level == pytest.approx(1.0) and out[30].peak == pytest.approx(0.5)
    assert out[32].level < 0.2


def test_sustained_noise_does_not_repeat_onsets():
    f = AudioFeatures()
    out = drive(f, [False] * 30 + [True] * 30)
    assert sum(a.onset for a in out) == 1


def test_steady_claps_lock_tempo():
    f = AudioFeatures()
    pattern = [i % 15 == 0 for i in range(30 * 6)]
    out = drive(f, [False] * 30 + pattern)
    locked = [a for a in out if a.bpm is not None]
    assert locked and all(a.bpm == pytest.approx(120, abs=3) for a in locked)
    beats = [i for i, a in enumerate(out) if a.beat]
    assert beats and all((i - 30) % 15 == 0 for i in beats)


def test_no_audio_and_sounddevice_fallback():
    assert NoAudio().latest() == Audio() and NoAudio().available is False
    s = SoundDeviceAudio(device="definitely-not-a-device")
    assert s.available is False and s.latest() == Audio()
    s.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/arcade/test_audio.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arcade.sources.audio'`

- [ ] **Step 3: Implement**

`arcade/sources/audio.py`:

```python
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Protocol

import numpy as np

from arcade.sensed import Audio

log = logging.getLogger("arcade")

RATE = 16000
WINDOW_S = 0.05
BUFFER_S = 2.0
ONSET_RATIO = 3.0
ONSET_RISE = 1.5
ONSET_FLOOR_RMS = 0.02
REFRACTORY_S = 0.1
HISTORY = 20
TEMPO_ONSETS = 8
TEMPO_TOLERANCE = 0.15


class AudioSource(Protocol):
    available: bool

    def latest(self) -> Audio: ...
    def close(self) -> None: ...


class NoAudio:
    available = False

    def latest(self) -> Audio:
        return Audio()

    def close(self) -> None:
        pass


class AudioFeatures:
    def __init__(self, rate: int = RATE):
        self.rate = rate
        self._buf = np.zeros(int(rate * BUFFER_S), np.float32)
        self._win = int(rate * WINDOW_S)
        self._energies: deque[float] = deque(maxlen=HISTORY)
        self._onsets: deque[float] = deque(maxlen=TEMPO_ONSETS)
        self._ref = ONSET_FLOOR_RMS
        self._last_onset = -1.0
        self._prev_energy = 0.0

    def feed(self, samples: np.ndarray) -> None:
        s = np.asarray(samples, dtype=np.float32).ravel()
        n = len(s)
        if n >= len(self._buf):
            self._buf[:] = s[-len(self._buf):]
        elif n:
            self._buf[:-n] = self._buf[n:]
            self._buf[-n:] = s

    def latest(self, t: float) -> Audio:
        win = self._buf[-self._win:]
        rms = float(np.sqrt(np.mean(win * win)))
        peak = float(np.abs(win).max())
        self._ref = max(rms, self._ref * 0.995, ONSET_FLOOR_RMS)
        level = 0.0 if rms < ONSET_FLOOR_RMS / 2 else min(1.0, rms / self._ref)
        energy = rms * rms
        median = float(np.median(self._energies)) if len(self._energies) >= 5 else None
        onset = (median is not None and energy > ONSET_RATIO * median and rms >= ONSET_FLOOR_RMS
                 and energy > ONSET_RISE * self._prev_energy and t - self._last_onset >= REFRACTORY_S)
        self._energies.append(energy)
        self._prev_energy = energy
        if onset:
            self._last_onset = t
            self._onsets.append(t)
        bpm = None
        if len(self._onsets) >= 4:
            intervals = np.diff(np.array(self._onsets))
            m = float(np.median(intervals))
            if 0.25 <= m <= 2.0 and np.all(np.abs(intervals - m) <= TEMPO_TOLERANCE * m):
                bpm = 60.0 / m
        return Audio(level=level, peak=min(1.0, peak), onset=bool(onset), beat=bool(onset and bpm is not None), bpm=bpm)


class SoundDeviceAudio:
    """Default input device at 16 kHz mono; falls back to the device's own sample rate."""

    def __init__(self, device=None, clock=time.monotonic):
        self.clock = clock
        self.available = False
        self._lock = threading.Lock()
        self._features = AudioFeatures()
        self._stream = None
        try:
            import sounddevice as sd

            rate = RATE
            try:
                self._stream = sd.InputStream(samplerate=rate, channels=1, dtype="float32", device=device,
                                              blocksize=int(rate * WINDOW_S), callback=self._callback)
            except Exception:
                rate = int(sd.query_devices(device, "input")["default_samplerate"])
                self._features = AudioFeatures(rate)
                self._stream = sd.InputStream(samplerate=rate, channels=1, dtype="float32", device=device,
                                              blocksize=int(rate * WINDOW_S), callback=self._callback)
            self._stream.start()
            self.available = True
        except Exception as e:
            log.warning("microphone unavailable: %s", e)
            self._stream = None
            self.available = False

    def _callback(self, indata, frames, time_info, status) -> None:
        with self._lock:
            self._features.feed(indata[:, 0])

    def latest(self) -> Audio:
        if not self.available:
            return Audio()
        with self._lock:
            return self._features.latest(self.clock())

    def close(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/arcade/test_audio.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add arcade/sources/audio.py tests/arcade/test_audio.py
git commit -m "feat(arcade): audio features and sounddevice source"
```

---

### Task 18: Source factory, recording, CLI

**Files:**
- Create: `arcade/sources/record.py`, `arcade/main.py`, `arcade/__main__.py`
- Modify: `arcade/sources/__init__.py`
- Test: `tests/arcade/test_sources.py`, `tests/arcade/test_main.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `make_sources(cfg, size) -> (camera, audio)`; `record(camera, audio, path, size, seconds, fps=30, clock=time.monotonic, sleep=time.sleep) -> int` (records written); `arcade.main.build_display(cfg) -> Display`; `arcade.main.main(argv=None) -> int`.

CLI:

```
python -m arcade [--config arcade.toml] [--backend sdl|fake|ddp] [--camera ...] [--audio ...]
                 [--size WxH] [--look plain|led|distance] [--scenario FILE] [--game NAME]
                 [--seed N] [--ticks N] [--record OUT.jsonl --seconds S] [-v]
```

`--ticks` stops after N ticks (for smoke tests and agents). `--record` writes a scenario from the live sources instead of running the arcade.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_sources.py`:

```python
import pytest

from arcade.sensed import Audio
from arcade.sources import make_sources
from arcade.sources.actors import Person, scene
from arcade.sources.audio import NoAudio
from arcade.sources.camera import NoCamera
from arcade.sources.record import record
from arcade.sources.replay import ReplayAudio, ReplayCamera
from arcade.sources.scenario import ScenarioReader, ScenarioWriter
from tests.arcade.helpers import FakeClock, make_cfg


def test_none_sources():
    cam, aud = make_sources(make_cfg((64, 64)), (64, 64))
    assert isinstance(cam, NoCamera) and isinstance(aud, NoAudio)


def test_replay_sources_share_a_stream(tmp_path):
    p = tmp_path / "s.jsonl"
    with ScenarioWriter(p) as w:
        for s in scene(persons=[Person()], ticks=2):
            w.write(s)
    cam, aud = make_sources(make_cfg((64, 64), camera="replay", audio="replay", scenario=str(p)), (64, 64))
    assert isinstance(cam, ReplayCamera) and isinstance(aud, ReplayAudio) and cam.stream is aud.stream
    with pytest.raises(ValueError):
        make_sources(make_cfg((64, 64), camera="replay"), (64, 64))


def test_record_writes_ticks(tmp_path):
    clock = FakeClock()
    out = tmp_path / "rec.jsonl"
    n = record(NoCamera(), NoAudio(), out, (64, 64), seconds=0.5, fps=30, clock=clock, sleep=clock.sleep)
    assert 14 <= n <= 16
    got = list(ScenarioReader(out))
    assert len(got) == n and got[0].motion.shape == (64, 64) and got[0].audio == Audio()
```

`tests/arcade/test_main.py`:

```python
from pathlib import Path

from arcade.main import build_display, main
from arcade.preview import PreviewDisplay
from arcade.sources.scenario import ScenarioReader
from show.display.fake import FakeDisplay
from tests.arcade.helpers import make_cfg


def test_build_display_wraps_sdl_in_preview_and_passes_fake_through():
    assert isinstance(build_display(make_cfg((64, 64))), FakeDisplay)
    d = build_display(make_cfg((64, 64), backend="sdl", sdl_scale=2))
    assert isinstance(d, PreviewDisplay)
    d.close()


def test_main_runs_ticks_and_exits(tmp_path):
    rc = main(["--backend", "fake", "--camera", "none", "--audio", "none", "--ticks", "3",
               "--config", str(tmp_path / "none.toml")])
    assert rc == 0


def test_main_launches_named_game_and_replays(tmp_path):
    from arcade.sources.actors import Person, scene
    from arcade.sources.scenario import ScenarioWriter

    rec = tmp_path / "rec.jsonl"
    with ScenarioWriter(rec) as w:
        for s in scene(persons=[Person()], ticks=4):
            w.write(s)
    rc = main(["--backend", "fake", "--camera", "replay", "--audio", "replay", "--scenario", str(rec),
               "--game", "puppet", "--ticks", "4", "--size", "128x32", "--config", str(tmp_path / "none.toml")])
    assert rc == 0


def test_main_record_mode(tmp_path):
    out = tmp_path / "out.jsonl"
    rc = main(["--camera", "none", "--audio", "none", "--record", str(out), "--seconds", "0.1",
               "--config", str(tmp_path / "none.toml")])
    assert rc == 0 and len(list(ScenarioReader(out))) >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/arcade/test_sources.py tests/arcade/test_main.py -v`
Expected: FAIL with `ImportError: cannot import name 'make_sources'`

- [ ] **Step 3: Implement**

`arcade/sources/__init__.py` (replace the empty file):

```python
from __future__ import annotations

from arcade.config import ArcadeConfig


def make_sources(cfg: ArcadeConfig, size: tuple[int, int]):
    """Build (camera, audio) for the configured sources. Replay sources share one stream."""
    from arcade.sources.audio import NoAudio, SoundDeviceAudio
    from arcade.sources.camera import NoCamera

    replay_cam = replay_aud = None
    if cfg.camera == "replay" or cfg.audio == "replay":
        if not cfg.scenario:
            raise ValueError("camera/audio 'replay' needs scenario = <file.jsonl>")
        from arcade.sources.replay import open_replay
        replay_cam, replay_aud = open_replay(cfg.scenario)

    if cfg.camera == "none":
        camera = NoCamera()
    elif cfg.camera == "replay":
        camera = replay_cam
    elif cfg.camera == "mediapipe":
        from arcade.sources.pose_mediapipe import MediaPipeCamera
        camera = MediaPipeCamera(size, cfg.camera_index, cfg.mirror)
    elif cfg.camera == "imx500":
        from arcade.sources.pose_imx500 import IMX500Camera
        camera = IMX500Camera(size, cfg.mirror)
    else:
        raise ValueError(f"unknown camera {cfg.camera!r}")

    if cfg.audio == "none":
        audio = NoAudio()
    elif cfg.audio == "replay":
        audio = replay_aud
    elif cfg.audio == "sounddevice":
        audio = SoundDeviceAudio()
    else:
        raise ValueError(f"unknown audio {cfg.audio!r}")
    return camera, audio
```

`arcade/sources/record.py`:

```python
from __future__ import annotations

import time
from pathlib import Path

from arcade.sensed import Sensed
from arcade.sources.scenario import ScenarioWriter


def record(camera, audio, path: Path | str, size: tuple[int, int], seconds: float, fps: int = 30,
           clock=time.monotonic, sleep=time.sleep) -> int:
    """Sample the live sources at fps for `seconds` and write a scenario file. Returns records written."""
    period = 1.0 / fps
    t0 = clock()
    n = 0
    with ScenarioWriter(path) as w:
        while clock() - t0 < seconds:
            bodies, blobs, motion = camera.latest()
            a = audio.latest()
            w.write(Sensed(clock() - t0, tuple(bodies), tuple(blobs), motion, a).with_motion(size))
            n += 1
            sleep(period)
    return n
```

`arcade/main.py`:

```python
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from arcade.config import ArcadeConfig, load_config
from arcade.games import all_games, get_game
from arcade.menu import Menu
from arcade.preview import PreviewDisplay
from arcade.runner import Runner
from arcade.sources import make_sources
from arcade.sources.record import record
from show.display import Display, make_display
from show.font import Font

log = logging.getLogger("arcade")


def build_display(cfg: ArcadeConfig) -> Display:
    if cfg.backend == "sdl":
        from show.display.sdl import SDLDisplay
        inner = SDLDisplay(cfg.width * cfg.sdl_scale, cfg.height * cfg.sdl_scale, 1)
        return PreviewDisplay(inner, cfg.look, cfg.sdl_scale, cfg.gamma)
    return make_display(cfg)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="arcade", description="Wall arcade: camera and microphone games on the LED wall")
    p.add_argument("--config", default="arcade.toml")
    p.add_argument("--backend", choices=("sdl", "fake", "ddp"))
    p.add_argument("--camera", choices=("mediapipe", "imx500", "replay", "none"))
    p.add_argument("--audio", choices=("sounddevice", "replay", "none"))
    p.add_argument("--size", help="WxH, e.g. 128x32")
    p.add_argument("--look", choices=("plain", "led", "distance"))
    p.add_argument("--scenario")
    p.add_argument("--game", help="launch this game directly instead of the menu")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--ticks", type=int, help="stop after N ticks")
    p.add_argument("--record", help="write a scenario file from the live sources and exit")
    p.add_argument("--seconds", type=float, default=20.0, help="length of --record")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def apply_overrides(cfg: ArcadeConfig, args) -> ArcadeConfig:
    for name in ("backend", "camera", "audio", "look", "scenario"):
        value = getattr(args, name)
        if value is not None:
            setattr(cfg, name, value)
    if args.size:
        w, h = (int(v) for v in args.size.lower().split("x"))
        cfg.width, cfg.height = w, h
    return cfg


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = apply_overrides(load_config(args.config), args)
    camera, audio = make_sources(cfg, cfg.size)
    try:
        if args.record:
            n = record(camera, audio, args.record, cfg.size, args.seconds, cfg.fps)
            log.info("wrote %d records to %s", n, args.record)
            return 0
        font = Font.load(Path(cfg.font_path))
        display = build_display(cfg)
        try:
            games = all_games()
            runner = Runner(cfg, display, font, Menu(games, cfg), games, seed=args.seed)
            if args.game:
                runner.launch(get_game(args.game).info.name)
            runner.loop(camera, audio, max_ticks=args.ticks)
        except KeyboardInterrupt:
            pass
        finally:
            display.close()
        return 0
    finally:
        for src in (camera, audio):
            close = getattr(src, "close", None)
            if close:
                close()


if __name__ == "__main__":
    sys.exit(main())
```

`arcade/__main__.py`:

```python
import sys

from arcade.main import main

sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/arcade/test_sources.py tests/arcade/test_main.py -v`
Expected: 7 passed. Then the live smoke on the Mac: `python tools/fetch_models.py && python -m arcade` should open a window showing the LED-look menu, and a raised hand should move the cursor. If the window shows but no cursor appears, run with `-v` and look for the "mediapipe camera unavailable" line.

- [ ] **Step 5: Commit**

```bash
git add arcade/sources/__init__.py arcade/sources/record.py arcade/main.py arcade/__main__.py tests/arcade/test_sources.py tests/arcade/test_main.py
git commit -m "feat(arcade): source factory, scenario recording, CLI"
```

---

### Task 19: Raspberry Pi AI Camera source

**Files:**
- Create: `arcade/sources/pose_imx500.py`
- Test: `tests/arcade/test_pose_imx500.py`

**Interfaces:**
- Consumes: `ThreadedCamera`, `BodyTracker`, `CameraResult` (Task 16), `FrameFeatures` (Task 15), `box_of` (Task 16).
- Produces: `MODEL = "/usr/share/imx500-models/imx500_network_higherhrnet_coco.rpk"`, `XY_ORDER = (0, 1)`, `parse_higherhrnet(keypoints, scores, img_size, mirror, xy_order=XY_ORDER, min_score=0.3) -> Detections`, `IMX500Camera(size, mirror=True, model=MODEL)`.

picamera2 facts used here (from `picamera2/devices/imx500/postprocess_highernet.py` and `imx500.py` on GitHub main, 2026-09-26): `IMX500(model_path)` exposes `camera_num`, `network_intrinsics`, `get_outputs(metadata, add_batch=True)`, `show_network_fw_progress_bar()`; `postprocess_higherhrnet(outputs=..., img_size=(H, W), img_w_pad=(0, 0), img_h_pad=(0, 0), detection_threshold=0.3, network_postprocess=True)` returns `(keypoints, scores, boxes)` where each `keypoints[i]` is a flat list of 51 floats, 17 points of `(a, b, score)` scaled to `img_size` pixels, in COCO order. Whether `a` is x or y is settled at bring-up with `XY_ORDER`. The model file is installed by `sudo apt install imx500-all`.

Only the pure parsing function is unit-tested. The class needs the Pi.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_pose_imx500.py`:

```python
import numpy as np
import pytest

from arcade.sensed import NOSE, RIGHT_ANKLE
from arcade.sources.camera import EMPTY
from arcade.sources.pose_imx500 import IMX500Camera, parse_higherhrnet


def person(x0, y0):
    pts = []
    for i in range(17):
        pts += [x0 + i * 4.0, y0 + i * 8.0, 0.9]
    return pts


def test_parse_normalizes_scales_and_mirrors():
    kps = [person(100.0, 50.0), person(300.0, 60.0)]
    dets = parse_higherhrnet(kps, [0.8, 0.9], (640, 480), mirror=False)
    assert len(dets) == 2
    box, points = dets[0]
    assert len(points) == 17
    assert points[NOSE].x == pytest.approx(100 / 640) and points[NOSE].y == pytest.approx(50 / 480)
    assert points[RIGHT_ANKLE].x == pytest.approx((100 + 64) / 640)
    assert box[0] == pytest.approx(100 / 640) and box[2] == pytest.approx((100 + 64) / 640)
    mirrored = parse_higherhrnet(kps, [0.8, 0.9], (640, 480), mirror=True)
    assert mirrored[0][1][NOSE].x == pytest.approx(1 - 100 / 640)


def test_parse_drops_low_scores_and_swaps_axes():
    kps = [person(100.0, 50.0)]
    assert parse_higherhrnet(kps, [0.1], (640, 480), mirror=False) == []
    swapped = parse_higherhrnet(kps, [0.9], (640, 480), mirror=False, xy_order=(1, 0))
    assert swapped[0][1][NOSE].x == pytest.approx(50 / 640) and swapped[0][1][NOSE].y == pytest.approx(100 / 480)


def test_camera_without_picamera2_is_unavailable():
    cam = IMX500Camera((64, 64), model="/nonexistent.rpk")
    assert cam.available is False and cam.latest() == EMPTY
    cam.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/arcade/test_pose_imx500.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'arcade.sources.pose_imx500'`

- [ ] **Step 3: Implement**

`arcade/sources/pose_imx500.py`:

```python
"""Raspberry Pi AI Camera (IMX500): pose runs on the sensor, the Pi only parses keypoints."""
from __future__ import annotations

import logging

import numpy as np

from arcade.sensed import Keypoint
from arcade.sources.blobs import FrameFeatures
from arcade.sources.camera import BodyTracker, CameraResult, Detections, ThreadedCamera
from arcade.sources.pose_mediapipe import box_of

log = logging.getLogger("arcade")

MODEL = "/usr/share/imx500-models/imx500_network_higherhrnet_coco.rpk"
FRAME_SIZE = (640, 480)
# Bring-up: if the puppet moves up and down when you step sideways, change to (1, 0).
XY_ORDER = (0, 1)


def parse_higherhrnet(keypoints, scores, img_size: tuple[int, int], mirror: bool,
                      xy_order: tuple[int, int] = XY_ORDER, min_score: float = 0.3) -> Detections:
    w, h = img_size
    out: Detections = []
    for flat, score in zip(keypoints, scores):
        if score < min_score:
            continue
        arr = np.asarray(flat, dtype=np.float32).reshape(17, 3)
        xs = arr[:, xy_order[0]] / w
        ys = arr[:, xy_order[1]] / h
        if mirror:
            xs = 1.0 - xs
        kps = tuple(Keypoint(float(x), float(y), float(c)) for x, y, c in zip(xs, ys, arr[:, 2]))
        out.append((box_of(kps), kps))
    return out


class IMX500Camera(ThreadedCamera):
    def __init__(self, size: tuple[int, int], mirror: bool = True, model: str = MODEL):
        super().__init__()
        self.size, self.mirror = size, mirror
        self.tracker = BodyTracker()
        self.features = FrameFeatures(size)
        try:
            import cv2
            from picamera2 import Picamera2
            from picamera2.devices.imx500 import IMX500, NetworkIntrinsics
            from picamera2.devices.imx500.postprocess_highernet import postprocess_higherhrnet

            self._cv2 = cv2
            self._postprocess = postprocess_higherhrnet
            self._imx500 = IMX500(model)
            intrinsics = self._imx500.network_intrinsics or NetworkIntrinsics()
            intrinsics.task = "pose estimation"
            intrinsics.update_with_defaults()
            self._picam2 = Picamera2(self._imx500.camera_num)
            config = self._picam2.create_preview_configuration(
                main={"size": FRAME_SIZE, "format": "RGB888"},
                controls={"FrameRate": intrinsics.inference_rate}, buffer_count=12)
            self._imx500.show_network_fw_progress_bar()
            self._picam2.start(config, show_preview=False)
            self.available = True
            self.start()
        except Exception as e:
            log.warning("imx500 camera unavailable: %s", e)
            self.available = False

    def step(self) -> CameraResult | None:
        request = self._picam2.capture_request()
        try:
            metadata = request.get_metadata()
            frame = request.make_array("main")  # picamera2's RGB888 is BGR in memory, which FrameFeatures expects
        finally:
            request.release()
        detections: Detections = []
        outputs = self._imx500.get_outputs(metadata=metadata, add_batch=True)
        if outputs is not None:
            keypoints, scores, _boxes = self._postprocess(
                outputs=outputs, img_size=(FRAME_SIZE[1], FRAME_SIZE[0]), img_w_pad=(0, 0),
                img_h_pad=(0, 0), detection_threshold=0.3, network_postprocess=True)
            detections = parse_higherhrnet(keypoints, scores, FRAME_SIZE, self.mirror)
        bodies = self.tracker.update(detections)
        if self.mirror:
            frame = self._cv2.flip(frame, 1)
        blobs, motion = self.features.update(frame)
        return (bodies, blobs, motion)

    def close(self) -> None:
        super().close()
        cam = getattr(self, "_picam2", None)
        if cam is not None:
            try:
                cam.stop()
            except Exception:
                pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/arcade/test_pose_imx500.py -v`
Expected: 3 passed

- [ ] **Step 5: Record the decisions and the bring-up notes**

Create `arcade/sources/README.md`:

```markdown
# Sources

- Mac: OpenCV webcam + MediaPipe Pose Landmarker lite (Tasks API, VIDEO mode, num_poses=2).
  33 landmarks -> COCO 17 by index: (0, 2, 5, 7, 8, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28).
- Pi: Raspberry Pi AI Camera with the HigherHRNet COCO model from imx500-all; keypoints already in
  COCO order, scaled to 640x480, axis order settled by XY_ORDER at bring-up.
- Both feed BGR frames to FrameFeatures for blobs (max-channel brightness) and the motion grid.
- Audio: sounddevice, 16 kHz mono, features in AudioFeatures.
```

Add to `deploy/README.md` under a heading "Arcade on the Pi":

```
sudo apt install -y python3-picamera2 imx500-all python3-opencv libportaudio2
python3 -m venv --system-site-packages .venv && . .venv/bin/activate && pip install -e '.[dev,pi]'
python -m arcade --backend ddp --camera imx500 --game puppet -v
```

Check three things and fix the constants named: the puppet moves sideways when you do (else set `XY_ORDER = (1, 0)`), it faces you like a mirror (else `mirror = false`), and a red glow stick paints red in the paint game (else swap the colour order in `FrameFeatures`, which then needs a `bgr: bool` flag).

- [ ] **Step 6: Commit**

```bash
git add arcade/sources/pose_imx500.py arcade/sources/README.md tests/arcade/test_pose_imx500.py deploy/README.md
git commit -m "feat(arcade): Raspberry Pi AI Camera source"
```

---

### Task 20: Soak and budget tests for every registered game

**Files:**
- Test: `tests/arcade/test_all_games.py`

**Interfaces:**
- Consumes: `all_games()` (Task 7), `run` helper (Task 8), actors (Task 4), `Canvas` (Task 5).

Two generic tests the second plan's games inherit for free: every registered game survives 300 ticks of a random actor mix at both layouts and draws something, and every game's `update` plus `draw` averages under 8 ms per tick at 64 by 64 (the `perf` marker, so it can be deselected on a slow CI box with `-m "not perf"`).

- [ ] **Step 1: Write the tests**

`tests/arcade/test_all_games.py`:

```python
import random
import time

import pytest

from arcade.canvas import Canvas
from arcade.games import all_games
from arcade.sources.actors import TICK, Person, claps, moving_blob, scene, tempo
from tests.arcade.helpers import run

BUDGET_MS = 8.0


def random_mix(rng: random.Random, ticks: int):
    persons = [Person(rng.uniform(0.1, 0.9), 0.55, rng.uniform(0.4, 0.8), id=i)
               .walk(rng.uniform(0.1, 0.9), rng.uniform(1, 5))
               .raise_hand(at=rng.uniform(0, 5), seconds=1.0)
               .jump(at=rng.uniform(0, 8), height=0.2)
               for i in range(rng.randint(0, 2))]
    blobs = [moving_blob(rng.random(), rng.random(), rng.random(), rng.random(), rng.uniform(1, 6),
                         color=(rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)))
             for _ in range(rng.randint(0, 2))]
    audio = rng.choice([claps([1.0, 2.5, 4.0]), tempo(120), None])
    return scene(persons=persons, blobs=blobs, audio=audio, ticks=ticks)


@pytest.mark.parametrize("game_cls", all_games(), ids=lambda g: g.info.name)
def test_every_game_soaks_without_error(game_cls, size, font5x7):
    rng = random.Random(hash((game_cls.info.name, size)) & 0xFFFF)
    frames, game, runner = run(game_cls, random_mix(rng, 300), size, font5x7)
    assert len(frames) == 300
    assert any(f.max() > 0 for f in frames), "game never drew anything"
    assert runner.crashes == {}, "game raised during the soak"
    assert isinstance(game.debug_state(), dict)


@pytest.mark.perf
@pytest.mark.parametrize("game_cls", all_games(), ids=lambda g: g.info.name)
def test_every_game_fits_the_tick_budget(game_cls, font5x7):
    size = (64, 64)
    game = game_cls()
    game.reset(size, random.Random(0))
    canvas = Canvas(*size, font5x7)
    frames = list(random_mix(random.Random(1), 300))
    for s in frames[:30]:
        game.update(s.with_motion(size), TICK)
        game.draw(canvas)
    t0 = time.perf_counter()
    for s in frames[30:]:
        game.update(s.with_motion(size), TICK)
        canvas.clear()
        game.draw(canvas)
    per_tick_ms = (time.perf_counter() - t0) / 270 * 1000
    assert per_tick_ms < BUDGET_MS, f"{game_cls.info.name}: {per_tick_ms:.2f} ms per tick"
```

- [ ] **Step 2: Run them**

Run: `pytest tests/arcade/test_all_games.py -v`
Expected: all passed (4 soak cases, 2 perf cases with paint and puppet registered). If a perf case fails on your machine, first check the machine is not throttled, then profile the game: `python -m cProfile -s cumtime tools/arcade_shot.py --game <name> --ticks 300 --out /tmp/x.png | head -30`.

- [ ] **Step 3: Commit**

```bash
git add tests/arcade/test_all_games.py
git commit -m "test(arcade): soak and tick-budget tests for every registered game"
```

---

## Done when (revision 2; superseded by "Done when (revision 3)" in the amendments)

- `pytest` passes on the Mac with no hardware attached.
- `python tools/arcade_shot.py --game paint --blob "moving_blob(0.1,0.5,0.9,0.5,2)" --out shots/paint.png` produces a sheet that looks like a red streak fading on round LEDs.
- `python -m arcade` on the Mac shows the menu, a raised hand moves the cursor, dwelling on a tile launches the game, both hands up returns to the menu.
- The second plan (remaining nine games, project skills) can be written against the real `Game`, actors, and tools.
