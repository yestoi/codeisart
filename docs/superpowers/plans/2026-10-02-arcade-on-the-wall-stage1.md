# The Arcade on the Wall, Stage 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The arcade's walk-up loop plays on the real 128x64 wall, from the Pi 5, through the Raspberry Pi AI Camera, and the operator is pointed at M8.

**Architecture:** The AI Camera is read as a plain camera: a small picamera2 capture object takes the place of `cv2.VideoCapture` inside the existing MediaPipe source, chosen by a new config key `capture`. `arcade run --game NAME` narrows the lobby and the runner to one game. Nothing in the governor, the limiter or the driver changes.

**Tech Stack:** Python 3.12 on the Mac (uv venv), Python 3.13 on the Pi 5 (Raspberry Pi OS Trixie); picamera2 0.3.37 and `imx500-all` 1.13.0 from apt on the Pi; MediaPipe 1.0.1 with `models/pose_landmarker_lite.task`; pytest.

**Spec:** `docs/superpowers/specs/2026-10-02-arcade-on-the-wall-design.md` (sections 3, 4 and 6). The arcade's own spec is `docs/superpowers/specs/2026-09-26-wall-arcade-design.md`.

## Global Constraints

- The wall is 128x64 and no other (Q82). No file for a bigger wall.
- Not changed: `arcade/flash.py`, `arcade/brightness.py`, `show/wall.py`, `show/display/colorlight*.py` and their wall-proven settings (60.00 frames a second, rows paced over 15.5 ms, the S2 sync first, the pinned real-time sender).
- picamera2, cv2 and mediapipe are imported inside a constructor or a function, never at module import (`tests/arcade/test_doctor.py::test_importing_main_loads_no_hardware_module` holds).
- No existing assert changes. A task that finds it must change one stops and reports.
- Tests on the Mac: the task's own files after each task; the full suite once, in Task 6, under 540 s (Q102). No agents are spawned for the build (the Mac has 8 GB).
- Every Pi command is one ssh call whose whole remote command starts with `flock -w 300 /tmp/pi5.lock ` (`docs/superpowers/workflow/pi-lock.md`); no scp; nothing kept in the Pi's `/tmp`. Two forms only: `ssh trey@codeisart.local "flock -w 300 /tmp/pi5.lock <one command>"` (single quotes may stand inside it), or the same with `sh -s` or `.venv/bin/python -` as the command and the script on the call's standard input. No script is written inside `sh -c '...'`.
- One exception, and only at the owner's word in the session: the early stop of a wall run (`sudo systemctl kill -s INT arcade-wall`) is sent without the lock, because the run it stops holds the lock until it ends.
- Nothing goes to the card without the owner's "go". One run at a time; a run ends by its own `--seconds` or by one SIGINT, never by `timeout`.
- No package install, reboot or network change on the Pi while a picture is on the wall.
- Evidence images never enter git (Q98). Camera frames of people stay in the scratchpad or the Pi's ignored `data/`.
- Commits go to main while the operator is gated (Tasks 1 to 7). After the owner starts the loop, this session commits only on branch `wall-bringup` in its own worktree (spec section 6).
- The repo is public: no address, password or network name in any committed file.

## What the Pi looked like on 2026-10-02 10:10 (read-only check)

- Up, reachable as `trey@codeisart.local`; `promptviz-party.service` and `show.service` inactive.
- `~/codeisart` is at `56e585d`. origin/main is `600bc3c` since 10:01 (the operator's session pushed iterations 19 to 21); the Mac's main is this session's commits ahead of it.
- `rpicam-hello --list-cameras`: "No cameras available!". The kernel log names no sensor. `camera_auto_detect=1`.
- Not installed: `imx500-all`, `python3-picamera2`. apt offers 1.13.0-1 and 0.3.37-1.
- The venv has `include-system-site-packages = false`, numpy 2.5.3, mediapipe 1.0.1, opencv-contrib-python 5.0.0.93, and `models/pose_landmarker_lite.task`.
- User trey is in group `video`.

## Review Focus

1. picamera2 is not installed (the Mac, or a Pi before its setup) and `capture = "picamera2"`: the arcade starts with the camera unavailable and logs why; it does not raise. Test in Task 3.
2. The camera gives another size or pixel format than asked: the capture refuses with the two formats named and closes the camera, so wrong colours or a stretched body never reach the pose model. Test in Task 2.
3. Frames stop mid-run (the ribbon works loose): a read waits at most `READ_TIMEOUT` and gives `(False, None)`, the camera thread ends, the arcade goes on with the camera unavailable, and the doctor says "no frames" instead of hanging. Test in Task 2 (the thread's part is `test_read_failure_kills_the_thread_and_the_camera_is_unavailable`, existing).
4. `release()` after a start that failed, and twice: never raises, so the arcade's shutdown always reaches `display.close()` and the wall goes black. Test in Task 2.
5. `arcade doctor --capture picamera2` where picamera2 is missing or no camera is attached: "camera UNAVAILABLE" with the reason, exit 1, no traceback. Test in Task 3.
6. `--game` with a name that is no game: refused with the list of names, exit 2, before a camera or the wall opens. Test in Task 4.

---

### Task 1: The config key `capture`

**Files:**
- Modify: `arcade/config.py:11-14` (the enums), `:28-30` (the fields), `:92` (the enum check)
- Modify: `arcade.toml` (one line after `camera_fps`)
- Test: `tests/arcade/test_config.py`

**Interfaces:**
- Produces: `arcade.config.CAPTURES = ("opencv", "picamera2")`; `ArcadeConfig.capture: str = "opencv"`; `load_config` refuses another value with a `ValueError` that names `capture`.

- [ ] **Step 1: Write the failing tests** (append to `tests/arcade/test_config.py`)

```python
def test_capture_defaults_to_opencv_and_takes_picamera2(tmp_path):
    assert ArcadeConfig().capture == "opencv"
    assert load_config(write(tmp_path, 'capture = "picamera2"')).capture == "picamera2"


def test_capture_rejects_another_value(tmp_path):
    with pytest.raises(ValueError, match="capture"):
        load_config(write(tmp_path, 'capture = "webcam"'))
```

- [ ] **Step 2: Run them, expect failure**

Run: `.venv/bin/python -m pytest tests/arcade/test_config.py -q -k capture`
Expected: 1 failed (`AttributeError: 'ArcadeConfig' object has no attribute 'capture'`), 1 passed (the refusal already passes: an unknown key's error names `capture`; after step 3 it passes for the right reason, the enum check).

- [ ] **Step 3: Implement**

In `arcade/config.py`, after the `CAMERAS` line:

```python
CAPTURES = ("opencv", "picamera2")   # where the mediapipe camera's frames come from
```

In `ArcadeConfig`, after `camera_fps: int = 10`:

```python
    capture: str = "opencv"
```

In `load_config`, the enum loop becomes:

```python
    for name, allowed in (("backend", BACKENDS), ("camera", CAMERAS), ("capture", CAPTURES), ("audio", AUDIOS),
                          ("look", LOOKS)):
```

In `arcade.toml`, after the `camera_fps = 10` line:

```toml
capture = "opencv"       # opencv | picamera2 (the Pi's ribbon cameras): the mediapipe camera's frames
```

- [ ] **Step 4: Run the file**

Run: `.venv/bin/python -m pytest tests/arcade/test_config.py -q`
Expected: all pass (`test_default_file_in_repo_lists_every_field_with_its_default` included).

- [ ] **Step 5: Commit**

```bash
git add arcade/config.py arcade.toml tests/arcade/test_config.py
git commit -m "feat(arcade): the config key capture (opencv | picamera2)"
```

---

### Task 2: `Picamera2Capture`

**Files:**
- Create: `arcade/sources/capture_picamera2.py`
- Test: `tests/arcade/test_capture_picamera2.py`

**Interfaces:**
- Produces: `Picamera2Capture(size: tuple[int, int], index: int = 0, camera=None)` with `read() -> tuple[bool, np.ndarray | None]` (a BGR frame of `size`, waiting at most `READ_TIMEOUT` for the camera's next frame) and `release() -> None`. `FORMAT = "RGB888"`, `FRAME_RATE = 30`, `READ_TIMEOUT = 2.0`. `camera` is a `picamera2.Picamera2`-like object for tests.

picamera2 facts used (the calls are from the picamera2 docs, 2026-10-02; the pixel layout and `camera_configuration()` are from memory and are checked on the real camera in Task 8 step 5): `Picamera2(camera_num)`, `create_video_configuration(main={"size", "format"}, controls={"FrameRate": n})`, `configure(config)`, `camera_configuration()` (the configuration in force, a dict with `"main"`), `start()`, `capture_array("main", wait=seconds)` (the next frame, an `(h, w, 3)` uint8 array for a 24-bit format; `TimeoutError` after `seconds`; without `wait` it blocks for good when frames stop), `stop()`, `close()`. In picamera2 the format named `"RGB888"` lays a pixel out as `[B, G, R]` in memory, which is OpenCV's BGR.

- [ ] **Step 1: Write the failing tests** (`tests/arcade/test_capture_picamera2.py`)

```python
"""The picamera2 capture (the Pi's ribbon cameras), against a fake Picamera2: no camera and no picamera2 here."""
import numpy as np
import pytest

from arcade.sources.capture_picamera2 import FORMAT, FRAME_RATE, READ_TIMEOUT, Picamera2Capture


class FakeCam:
    def __init__(self, given=None, fail_read=False, fail_stop=False):
        self.calls, self.given, self.fail_read, self.fail_stop = [], given, fail_read, fail_stop
        self.frame = np.zeros((480, 640, 3), np.uint8)
        self.frame[..., 0] = 200

    def create_video_configuration(self, main, controls):
        self.calls.append(("create", dict(main), dict(controls)))
        return {"main": dict(main), "controls": dict(controls)}

    def configure(self, config):
        self.calls.append("configure")
        self.config = config

    def camera_configuration(self):
        return {"main": self.given or self.config["main"]}

    def start(self):
        self.calls.append("start")

    def capture_array(self, name, wait=None):
        self.waits = getattr(self, "waits", []) + [wait]
        if self.fail_read:
            raise TimeoutError("no frame")
        self.calls.append(("capture", name))
        return self.frame

    def stop(self):
        self.calls.append("stop")
        if self.fail_stop:
            raise RuntimeError("already stopped")

    def close(self):
        self.calls.append("close")


def test_opens_at_the_size_and_format_and_reads_bgr_frames():
    cam = FakeCam()
    cap = Picamera2Capture((640, 480), camera=cam)
    assert cam.calls == [("create", {"size": (640, 480), "format": FORMAT}, {"FrameRate": FRAME_RATE}),
                         "configure", "start"]
    ok, frame = cap.read()
    assert ok and frame.shape == (480, 640, 3) and tuple(frame[0, 0]) == (200, 0, 0)   # as OpenCV's BGR: blue
    assert cam.calls[-1] == ("capture", "main")


@pytest.mark.parametrize("given", [{"size": (656, 480), "format": "RGB888"}, {"size": (640, 480), "format": "XBGR8888"}])
def test_another_size_or_format_is_refused_and_the_camera_closed(given):
    cam = FakeCam(given=given)
    with pytest.raises(RuntimeError, match="picamera2 gave"):
        Picamera2Capture((640, 480), camera=cam)
    assert "start" not in cam.calls and cam.calls[-2:] == ["stop", "close"]


def test_a_read_waits_at_most_the_timeout_and_a_failed_one_is_not_ok(caplog):
    cam = FakeCam(fail_read=True)
    cap = Picamera2Capture((640, 480), camera=cam)
    assert cap.read() == (False, None) and cam.waits == [READ_TIMEOUT]
    assert "picamera2 read failed" in caplog.text and "Traceback" not in caplog.text


def test_no_camera_attached_says_so_with_the_ribbon_hint(monkeypatch):
    import sys
    import types

    def none_attached(index):
        raise IndexError("list index out of range")

    monkeypatch.setitem(sys.modules, "picamera2", types.SimpleNamespace(Picamera2=none_attached))
    with pytest.raises(RuntimeError, match="no camera 0.*ribbon"):
        Picamera2Capture((640, 480))


def test_release_stops_and_closes_once_and_never_raises():
    cam = FakeCam(fail_stop=True)
    cap = Picamera2Capture((640, 480), camera=cam)
    cap.release()
    cap.release()
    assert cam.calls.count("stop") == 1 and cam.calls.count("close") == 1


def test_importing_the_module_loads_no_picamera2():
    import sys

    assert "picamera2" not in sys.modules
```

- [ ] **Step 2: Run them, expect failure**

Run: `.venv/bin/python -m pytest tests/arcade/test_capture_picamera2.py -q`
Expected: collection error, `ModuleNotFoundError: No module named 'arcade.sources.capture_picamera2'`.

- [ ] **Step 3: Implement** (`arcade/sources/capture_picamera2.py`)

```python
"""The Pi's ribbon cameras as MediaPipeCamera's capture (cfg.capture "picamera2"): picamera2 frames in OpenCV's
layout. The AI Camera (IMX500) is read as a plain camera here: no network is loaded onto its sensor."""
from __future__ import annotations

import logging

FORMAT = "RGB888"     # picamera2's name for 24-bit pixels laid out [B, G, R] in memory: OpenCV's BGR
FRAME_RATE = 30
READ_TIMEOUT = 2.0    # s a read waits for a frame: without it a camera whose frames stop blocks its reader for good

log = logging.getLogger("arcade")


class Picamera2Capture:
    """read() -> (ok, bgr) at size, waiting at most READ_TIMEOUT for the camera's next frame; release() stops and
    closes it, once, and never raises.

    camera (a picamera2.Picamera2-like object) is injectable; without one picamera2 is imported and
    Picamera2(index) opened here (RuntimeError with the ribbon hint when no camera answers). RuntimeError, with
    the camera closed, when it does not give size and FORMAT."""

    def __init__(self, size: tuple[int, int], index: int = 0, camera=None):
        if camera is None:
            from picamera2 import Picamera2   # here: apt's package, on the Pi only

            try:
                camera = Picamera2(index)
            except Exception as e:
                raise RuntimeError(f"picamera2 found no camera {index} (is the ribbon seated: rpicam-hello "
                                   f"--list-cameras): {e!r}") from e
        self._cam, self._released = camera, False
        try:
            camera.configure(camera.create_video_configuration(main={"size": size, "format": FORMAT},
                                                                controls={"FrameRate": FRAME_RATE}))
            got = camera.camera_configuration()["main"]
            if tuple(got["size"]) != tuple(size) or got["format"] != FORMAT:
                raise RuntimeError(f"picamera2 gave {tuple(got['size'])} {got['format']}, not {tuple(size)} {FORMAT}")
            camera.start()
        except Exception:
            self.release()
            raise

    def read(self):
        try:
            return True, self._cam.capture_array("main", wait=READ_TIMEOUT)
        except Exception as e:
            log.warning("picamera2 read failed: %r", e)
            return False, None

    def release(self) -> None:
        if self._released:
            return
        self._released = True
        for call in (self._cam.stop, self._cam.close):
            try:
                call()
            except Exception:
                log.exception("picamera2 %s failed", call.__name__)
```

- [ ] **Step 4: Run the file**

Run: `.venv/bin/python -m pytest tests/arcade/test_capture_picamera2.py -q`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add arcade/sources/capture_picamera2.py tests/arcade/test_capture_picamera2.py
git commit -m "feat(arcade): Picamera2Capture, the Pi's ribbon cameras as the mediapipe camera's capture"
```

---

### Task 3: The source and the doctor follow `capture`

**Files:**
- Modify: `arcade/sources/pose_mediapipe.py:111-122` (`open_capture`), `:175` (its call)
- Modify: `arcade/main.py:34-52` (`probe_camera`), `:136-141` (`make_probes`), `:163` (run's doctor call), `:204-209` (the doctor's flags), `:232` (the doctor's call)
- Test: `tests/arcade/test_pose_mediapipe.py`, `tests/arcade/test_doctor.py`

**Interfaces:**
- Consumes: `ArcadeConfig.capture`, `CAPTURES` (Task 1); `Picamera2Capture(size, index)` (Task 2).
- Produces: `pose_mediapipe.open_capture(index: int, kind: str = "opencv")`; `arcade.main.probe_picamera2(timeout: float, index: int = 0) -> tuple[bool, str]`; `make_probes(camera_index=0, audio_device="", model=MODEL_PATH, capture="opencv")`; the flag `arcade doctor --capture {opencv,picamera2}`. `probe_camera(timeout, index=0)` keeps its signature and its messages.

- [ ] **Step 1: Write the failing tests**

Append to `tests/arcade/test_pose_mediapipe.py`:

```python
def test_the_camera_opens_the_capture_the_config_names(monkeypatch):
    seen = []
    monkeypatch.setattr(pm, "open_capture", lambda index, kind="opencv": seen.append((index, kind)) or FakeCapture())
    cfg = ArcadeConfig(camera_index=1, capture="picamera2")
    cam = MediaPipeCamera(cfg, cfg.size, landmarker=FakeLandmarker(), start=False)
    assert seen == [(1, "picamera2")]
    cam.close()


def test_open_capture_picamera2_builds_the_picamera2_capture(monkeypatch):
    import arcade.sources.capture_picamera2 as cp

    built = []
    monkeypatch.setattr(cp, "Picamera2Capture", lambda size, index: built.append((size, index)) or "capture")
    assert pm.open_capture(2, "picamera2") == "capture" and built == [(pm.CAPTURE_SIZE, 2)]


def test_without_picamera2_the_camera_is_unavailable_and_says_so(monkeypatch, caplog):
    import sys

    monkeypatch.setitem(sys.modules, "picamera2", None)        # import picamera2 raises ImportError
    cfg = ArcadeConfig(capture="picamera2")
    cam = MediaPipeCamera(cfg, cfg.size, landmarker=FakeLandmarker())
    assert cam.available is False and cam.latest() is None
    assert "mediapipe camera unavailable" in caplog.text and "picamera2" in caplog.text
    cam.close()
```

Append to `tests/arcade/test_doctor.py`:

```python
class FrameCapture:
    def __init__(self, frame):
        self.frame, self.released = frame, False

    def read(self):
        return self.frame is not None, self.frame

    def release(self):
        self.released = True


def test_probe_picamera2_reads_one_frame_and_releases(monkeypatch):
    import numpy as np

    import arcade.sources.capture_picamera2 as cp
    from arcade.main import probe_picamera2

    caps = []
    monkeypatch.setattr(cp, "Picamera2Capture",
                        lambda size, index: caps.append(FrameCapture(np.full((480, 640, 3), 9, np.uint8))) or caps[-1])
    assert probe_picamera2(1.0, 0) == (True, "picamera2 0: 640x480")
    assert caps[0].released


def test_doctor_reports_a_missing_picamera2_as_unavailable(monkeypatch, capsys):
    import sys

    monkeypatch.setitem(sys.modules, "picamera2", None)        # import picamera2 raises ImportError
    assert main(["doctor", "--require", "camera", "--capture", "picamera2", "--timeout", "1"]) == 1
    out = capsys.readouterr().out
    assert "camera  UNAVAILABLE" in out and "picamera2" in out


def test_make_probes_picks_the_camera_probe_by_capture(monkeypatch):
    import arcade.main

    monkeypatch.setattr(arcade.main, "probe_camera", lambda timeout, index=0: (True, "opencv"))
    monkeypatch.setattr(arcade.main, "probe_picamera2", lambda timeout, index=0: (True, "picamera2"))
    assert arcade.main.make_probes()["camera"](1.0) == (True, "opencv")
    assert arcade.main.make_probes(capture="picamera2")["camera"](1.0) == (True, "picamera2")
```

- [ ] **Step 2: Run them, expect failure**

Run: `.venv/bin/python -m pytest tests/arcade/test_pose_mediapipe.py tests/arcade/test_doctor.py -q -k "capture or picamera2"`
Expected: the 6 new tests fail (`open_capture() takes 1 positional argument`, `cannot import name 'probe_picamera2'`, `unrecognized arguments: --capture`); 2 existing tests the `-k` also picks pass.

- [ ] **Step 3: Implement the source's side** (`arcade/sources/pose_mediapipe.py`)

`open_capture` becomes:

```python
def open_capture(index: int, kind: str = "opencv"):
    """The capture cfg.capture names, at CAPTURE_SIZE: cv2.VideoCapture(index) ("opencv"; RuntimeError if it does
    not open) or capture_picamera2.Picamera2Capture ("picamera2", the Pi's ribbon cameras). Call it on the main
    thread: macOS asks for camera access only from there."""
    if kind == "picamera2":
        from arcade.sources import capture_picamera2   # here: looked up at the call, and it imports picamera2

        return capture_picamera2.Picamera2Capture(CAPTURE_SIZE, index)
    import cv2

    cap = cv2.VideoCapture(index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_SIZE[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_SIZE[1])
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f"camera index {index} did not open")
    return cap
```

In `MediaPipeCamera.__init__`, the line `self._cap = open_capture(cfg.camera_index)` becomes:

```python
                self._cap = open_capture(cfg.camera_index, cfg.capture)
```

and the class docstring's phrase "then MediaPipe and the camera open here" gains "(the capture cfg.capture names)".

- [ ] **Step 4: Implement the doctor's side** (`arcade/main.py`)

Add `CAPTURES` to the config import: `from arcade.config import CAPTURES, ArcadeConfig, load_config`.

`probe_camera` becomes two probes over one helper:

```python
def _first_frame(cap, timeout: float, label: str, hint: str) -> tuple[bool, str]:
    """(True, the size) at cap's first frame that is not all black within timeout, else (False, why); releases
    cap. The deadline is checked between reads, so one blocking read can overrun it."""
    frames, deadline = 0, time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            ok, frame = cap.read()
            if not ok or frame is None:
                time.sleep(0.05)
                continue
            frames += 1
            if frame.any():
                return True, f"{label}: {frame.shape[1]}x{frame.shape[0]}"
        why = f"{frames} frames, all black" if frames else f"no frames in {timeout:.0f} s"
        return False, f"{label}: {why} ({hint})"
    finally:
        cap.release()


def probe_camera(timeout: float, index: int = 0) -> tuple[bool, str]:
    """Runs on the calling thread, unlike probe_pose: macOS asks for camera access only from the main thread."""
    import cv2  # inside the probe, so importing arcade.main never loads OpenCV

    return _first_frame(cv2.VideoCapture(index), timeout, f"device {index}",
                        "macOS: grant this terminal camera access")


def probe_picamera2(timeout: float, index: int = 0) -> tuple[bool, str]:
    """The Pi's ribbon camera through picamera2 (capture "picamera2"), opened as the arcade opens it."""
    from arcade.sources import capture_picamera2
    from arcade.sources.pose_mediapipe import CAPTURE_SIZE

    return _first_frame(capture_picamera2.Picamera2Capture(CAPTURE_SIZE, index), timeout, f"picamera2 {index}",
                        "is the ribbon seated: rpicam-hello --list-cameras")
```

`make_probes` becomes:

```python
def make_probes(camera_index: int = 0, audio_device: str = "", model: Path = MODEL_PATH,
                capture: str = "opencv") -> dict[str, Probe]:
    """The doctor's probes by name; the camera's is the one capture names. The probe functions are looked up when
    a probe runs."""
    return {"camera": lambda t: (probe_picamera2 if capture == "picamera2" else probe_camera)(t, camera_index),
            "mic": lambda t: probe_mic(t, audio_device),
            "pose": lambda t: probe_pose(t, Path(model))}
```

In `run`, the doctor call becomes:

```python
        code = doctor(_names(args.require), make_probes(cfg.camera_index, cfg.audio_device, capture=cfg.capture),
                      TIMEOUT)
```

In `build_parser`, after the doctor's `--camera-index` line:

```python
    d.add_argument("--capture", choices=CAPTURES, default="opencv", help="picamera2: the Pi's ribbon cameras")
```

In `main`, the doctor's call becomes:

```python
        return doctor(_names(args.require),
                      make_probes(args.camera_index, args.audio_device, Path(args.model), args.capture), args.timeout)
```

- [ ] **Step 5: Run the files that touch these**

Run: `.venv/bin/python -m pytest tests/arcade/test_pose_mediapipe.py tests/arcade/test_doctor.py tests/arcade/test_main.py tests/arcade/test_sources.py tests/arcade/test_record.py tests/arcade/test_calibrate.py -q`
Expected: all pass, the six new ones included; no existing test changed.

- [ ] **Step 6: Commit**

```bash
git add arcade/sources/pose_mediapipe.py arcade/main.py tests/arcade/test_pose_mediapipe.py tests/arcade/test_doctor.py
git commit -m "feat(arcade): the mediapipe camera and the doctor follow cfg.capture"
```

---

### Task 4: `arcade run --game NAME`

**Files:**
- Modify: `arcade/main.py` (`run`, `build_parser`)
- Test: `tests/arcade/test_main.py`

**Interfaces:**
- Consumes: `all_games() -> list[type]` (each class has `info.name`); `Lobby(games, cfg)` keeps `games` as a dict by name.
- Produces: `arcade run --game NAME`: the lobby and the runner get that one game. An unknown name prints `run: unknown game 'NAME'; known: <names in menu order>` and returns 2 before the doctor, the sources and the display.

- [ ] **Step 1: Write the failing test** (append to `tests/arcade/test_main.py`)

```python
def test_run_game_offers_only_that_game_and_refuses_an_unknown_one(tmp_path, monkeypatch, capsys):
    built, opened = [], []

    class SpyRunner:
        def __init__(self, cfg, display, font, lobby, games, **kw):
            built.append((lobby, games))

        def loop(self, camera, audio, max_ticks=None):
            pass

    real_make_sources = arcade.main.make_sources
    monkeypatch.setattr(arcade.main, "make_sources", lambda *a, **kw: opened.append(a) or real_make_sources(*a, **kw))
    monkeypatch.setattr(arcade.main, "Runner", SpyRunner)
    config = str(_toml(tmp_path))
    assert main(["run", "--config", config, "--script", "walkup", "--seconds", "0", "--game", "pong"]) == 0
    lobby, games = built[0]
    assert [g.info.name for g in games] == ["pong"] and list(lobby.games) == ["pong"]

    assert main(["run", "--config", config, "--script", "walkup", "--seconds", "0", "--game", "tetris"]) == 2
    assert len(built) == 1 and len(opened) == 1               # refused before a source or a runner
    out = capsys.readouterr().out
    assert "unknown game 'tetris'" in out and "copyme, pong" in out
```

- [ ] **Step 2: Run it, expect failure**

Run: `.venv/bin/python -m pytest tests/arcade/test_main.py -q -k run_game`
Expected: FAIL, `unrecognized arguments: --game pong` (SystemExit 2).

- [ ] **Step 3: Implement** (`arcade/main.py`)

In `run`, right after `log.info("wall %s, backend %s", cfg.layout, cfg.backend)`:

```python
    games = all_games()
    if args.game is not None:
        names = [game.info.name for game in games]
        if args.game not in names:
            print(f"run: unknown game {args.game!r}; known: {', '.join(names)}")   # CLI output, as the doctor's
            return 2
        games = [game for game in games if game.info.name == args.game]
```

and the line `games = all_games()` inside the inner `try` is removed (the `Runner(...)` call keeps using `games`). The docstring of `run` gains: "--game offers that one game only: a raised hand starts it."

In `build_parser`, after the `--require` line of `run`:

```python
    r.add_argument("--game", metavar="NAME", help="offer only this game: a raised hand starts it")
```

- [ ] **Step 4: Run the file**

Run: `.venv/bin/python -m pytest tests/arcade/test_main.py -q`
Expected: all pass (`test_main_builds_runner_with_the_small_lobby_and_games_once` still counts one `all_games` call).

- [ ] **Step 5: Commit**

```bash
git add arcade/main.py tests/arcade/test_main.py
git commit -m "feat(arcade): run --game NAME offers one game"
```

---

### Task 5: The Pi's config, the `pi` extra and the runbook

**Files:**
- Create: `arcade.pi.toml`
- Create: `docs/runbooks/arcade-on-the-pi.md`
- Modify: `pyproject.toml:12` (the `pi` extra)
- Modify: `tests/arcade/test_config.py` (`test_the_shipped_arcade_configs_are_in_the_gamma_bound`'s list is not an assert: the tuple of names gains `arcade.pi.toml`; one new test)

**Interfaces:**
- Consumes: `capture` (Task 1), `--game` (Task 4), `doctor --capture` (Task 3).
- Produces: `arcade.pi.toml` (`backend = "colorlight"`, `capture = "picamera2"`); the runbook's start line, used by Task 9.

- [ ] **Step 1: Write the failing test** (append to `tests/arcade/test_config.py`)

```python
def test_the_pi_config_drives_the_card_through_picamera2():
    cfg = load_config(Path(__file__).resolve().parents[2] / "arcade.pi.toml")
    assert (cfg.backend, cfg.iface, cfg.capture, cfg.camera, cfg.camera_fps) == \
        ("colorlight", "eth0", "picamera2", "mediapipe", 10)
    assert cfg.size == (128, 64) and cfg.allow_record is False
```

and in `test_the_shipped_arcade_configs_are_in_the_gamma_bound` the tuple becomes `("arcade.toml", "arcade.mac.toml", "arcade.pi.toml")`.

- [ ] **Step 2: Run it, expect failure**

Run: `.venv/bin/python -m pytest tests/arcade/test_config.py -q -k "pi_config or gamma_bound"`
Expected: 1 failed (a missing file loads as the defaults, so `backend` is `"sdl"`), 1 passed (the gamma bound holds for defaults too).

- [ ] **Step 3: Write `arcade.pi.toml`**

```toml
# The Pi 5 at the wall: the Colorlight card on eth0 and the AI Camera read as a plain camera through picamera2
# (the pose runs in MediaPipe on the Pi: 10 captures a second hold there). Every other key is its default.
# Start it as docs/runbooks/arcade-on-the-pi.md says.
backend = "colorlight"
capture = "picamera2"
```

- [ ] **Step 4: The `pi` extra** (`pyproject.toml`)

```toml
pi = ["gpiozero>=2.0,<3", "lgpio", "mediapipe>=1.0,<2"]   # mediapipe: the arcade's pose on the Pi (1.0.1 runs there)
```

- [ ] **Step 5: Write the runbook** (`docs/runbooks/arcade-on-the-pi.md`)

````markdown
# Runbook: the arcade on the Pi 5

How the Pi is set up for the arcade and how a run is started and stopped. The wall's own faults are in
`wall-shimmer.md`. Ground rules, from the wall sessions:

- Nothing goes to the card without the owner's "go". One run at a time; let a run go dark before the next.
- Nothing reconfigures the Pi while a picture is on the wall: no package installs, no reboots, no network changes.
- While `docs/superpowers/workflow/pi-lock.md` exists, every command below runs under the Pi's lock, as that file
  says.
- A run ends by its own `--seconds` or by one SIGINT. Never `timeout`: its second signal skips the close.

## 1. Once: the camera's packages (the wall dark)

```
sudo apt update
sudo apt install -y imx500-all
sudo apt install -y --no-install-recommends python3-picamera2
sudo reboot
```

`imx500-all` brings the AI Camera's firmware files and models; `python3-picamera2` the capture library. The
ribbon goes in with the Pi off: the camera port is not hot-pluggable. After the boot, `rpicam-hello
--list-cameras` names `imx500`.

## 2. Once: the venv sees apt's picamera2

In `~/codeisart/.venv/pyvenv.cfg` set `include-system-site-packages = true`. The venv's own numpy, OpenCV and
MediaPipe stay in front of apt's. Then:

```
.venv/bin/pip install -e '.[pi,dev]'
.venv/bin/python -c "import picamera2, cv2, mediapipe, numpy; print(numpy.__version__, cv2.__version__)"
```

The pose model is `models/pose_landmarker_lite.task` (ignored by git). If it is missing:

```
mkdir -p models && curl -fL -o models/pose_landmarker_lite.task \
  https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task
```

## 3. Look before a run (no card)

```
rpicam-hello --list-cameras
.venv/bin/python -m arcade doctor --require camera,pose --capture picamera2
systemctl is-active promptviz-party.service show.service
```

The camera's line names `imx500`; the doctor prints `camera  ok  picamera2 0: 640x480` and `pose    ok`. A unit
that is active holds the card: the owner stops it (`sudo systemctl stop <unit>`) and starts it again afterwards.

## 4. A run

```
sudo systemd-run --unit=arcade-wall --pipe --wait --collect --quiet --uid=trey \
  -p AmbientCapabilities='CAP_NET_RAW CAP_SYS_NICE' -p WorkingDirectory=/home/trey/codeisart \
  /home/trey/codeisart/.venv/bin/python -m arcade run --config arcade.pi.toml --seconds 300 -v
```

Over ssh under the lock the whole line is one command in double quotes after `flock -w 300 /tmp/pi5.lock `
(not inside `sh -c '...'`: the capabilities' single quotes would end it).

`--game NAME` (copyme, pong, quickdraw, dodge, flap, swat, jump, freeze) offers that one game. The run's last
line is the sender's: `0 late (over 1 ms)` is a clean run.

`calibrate --config arcade.pi.toml` takes the place of `run ...` for a calibration; it writes
`data/calibration.json`, which every later run loads. If the figure is gone or out of place after one, remove
that file: the defaults return.

A run holds the Pi's lock until it ends, so keep `--seconds` short. To end one early, once, at the owner's word,
the one command that is sent without the lock: `sudo systemctl kill -s INT arcade-wall`. The wall goes black as
the arcade closes.

## 5. The camera's place

Chest height, looking level, the hips in view when the player steps in; no lamp or bright fixture in the picture;
light on the player. The player stands 2 to 2.5 m away.
````

- [ ] **Step 6: Run the config tests**

Run: `.venv/bin/python -m pytest tests/arcade/test_config.py tests/test_gitignore.py tests/test_deploy.py -q`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add arcade.pi.toml pyproject.toml docs/runbooks/arcade-on-the-pi.md tests/arcade/test_config.py
git commit -m "feat(arcade): arcade.pi.toml, mediapipe in the pi extra, the runbook for the arcade on the Pi"
```

---

### Task 6: The full suite, once

**Files:** none changed.

- [ ] **Step 1: The full suite, once, with nothing else running on the Mac**

Run: `.venv/bin/python -m pytest -q` (about 455 s; the limit is 540 s, Q102)
Expected: 2340 passed, 3 skipped (2323 before, plus 2 + 7 + 6 + 1 + 1 new). A time over 540 s or a timing failure is read once more before anything is decided on it. A failure stops the plan here: nothing is pushed and the loop is not started on a red main.

---

### Task 7: Point the operator at M8

**Files:**
- Modify: `docs/superpowers/workflow/decisions.md` (append Q181)
- Modify: `docs/superpowers/workflow/roadmap.md` (the M8 line moves above M7b's; one paragraph; one line under "Spec revision 4 notes")
- Modify: `docs/superpowers/workflow/state.md` (the `phase`, `milestone` and `plan` lines; Q181 on the `decisions` line)
- Modify: `docs/superpowers/workflow/config.md` (the run of Q101's order), `docs/superpowers/workflow/journal.md` (one entry at its end)
- Modify: `docs/superpowers/workflow/gate.md` (the answer, at its top; its Default paragraph)
- Modify: `docs/superpowers/workflow/live-smoke.md` (the `Strongman` row is `Jump`)

The loop reads these when the owner starts it. gate.md is the owner's to delete; this task does not delete it.

- [ ] **Step 1: Append to `decisions.md`**

```markdown
### Q181: What does the loop build next: M7b (iteration 22's written plan) or M8?
asked: not asked by the loop; the owner decided it in another session on 2026-10-02, about 10:00 CDT, after stopping the loop (Q180)
default: none taken; the owner said it
deadline: none
answer: M8 first. "I want to hold the it22 plan and rethink what needs to happen to get what we built running. Lets do it proper but only the essentials to show a complete vision. Even if it's just one game working but the full experience attract/play/etc." Asked what the wall does when nobody plays, he chose the spec's full director. The design is `docs/superpowers/specs/2026-10-02-arcade-on-the-wall-design.md` (approved, ee5ab0d), section 4: iteration 22 is M8 (the arcade spec's 7.3 and 7.7 as written; the demo replays of 7.3 step 1 are cut; with `run --game` the director offers only that game). If one iteration cannot hold it, the first holds the director, the tiers, Watcher, Echo, Warp, Contours and the crossfades; the second the doors, the ten-second guarantee and the rotation. Iteration 22's written plan (`docs/superpowers/plans/2026-10-02-it22-suite-room-paint-tug.md`) is kept for M7b's return: its tasks R (the suite's room) and C57 may be taken into M8's plan if the suite needs the room; Paint, Tug, E2 and I0 wait. M8's plan writer writes its report to `evidence/it22/m8-plan-writer-report.md` (`evidence/it22/plan-writer-report.md` is the Paint and Tug writer's and is kept), and M8's plan review goes to `evidence/it22/m8-plan-review.md`. This replaces, for iteration 22, the journal's and the roadmap's "Iteration 22: the suite's room, C57, then M7b's Paint and Tug" and config.md's order "M7b, M8". The camera on the Pi and the first plays on the wall are the owner's other session's (the same spec, section 3): the loop does not use the Pi and does not edit `arcade/sources/capture_picamera2.py`, `arcade.pi.toml` or `docs/runbooks/`; that session commits on branch `wall-bringup` while the loop runs and merges between iterations
status: answered (owner, 2026-10-02)
```

- [ ] **Step 2: `roadmap.md`**

Move the whole line that starts `- [ ] M8, the full lobby.` to sit directly above the line that starts `- [ ] M7b, the games that need M5`. Directly after the paragraph that ends "the full suite runs once an iteration." add:

```markdown
Owner decision Q181 (2026-10-02): M8 comes before M7b. Iteration 22 is M8, by
`docs/superpowers/specs/2026-10-02-arcade-on-the-wall-design.md` section 4; this replaces the sentence above,
"Iteration 22: the suite's room (the soaks in workers), C57, then M7b's Paint and Tug", and config.md's order
"M7b, M8". The written plan for Paint and Tug waits for M7b's return. The camera on the Pi (picamera2 frames
into the MediaPipe source, `capture = "picamera2"`), `run --game` and the first plays on the wall are the owner's
other session's work, on main before the loop starts and on branch `wall-bringup` after.
```

In the "Carried fixes" section, C57's phrase "the first task in `arcade/games/jump.py` in it22's plan" becomes "the first task in `arcade/games/jump.py` in the written Paint and Tug plan (M8's plan may take it; else M7b's return, Q181)".

In `config.md`, the run of Q101's Scope line: "M5 (no audio source, Q99), M7b, M8, M6" becomes "M5 (no audio source, Q99), M8, M7b, M6 (the order since Q181, 2026-10-02)".

Under "## Spec revision 4 notes" add:

```markdown
- 4.3 (config) gains `capture` (`opencv` | `picamera2`, default `opencv`): where the mediapipe camera's frames come from. 6.1: on the Pi the AI Camera is first read as a plain camera through picamera2 into the MediaPipe source; `pose_imx500` (the pose on the sensor) follows as stage 3 of the 2026-10-02 design. 9.4: `arcade run --game NAME` offers one game.
```

- [ ] **Step 3: `state.md`** — replace three whole lines (each is one long line; match on its first word):

```
phase: gated (the owner's word, Q180), then re-scoped by Q181 (2026-10-02): on the owner's restart (gate.md deleted, "start the workflow loop") iteration 22 starts at orient with M8, not at the review of the written plan
milestone: M8 (the full lobby: the director, the tiers, Watcher, Echo, Warp, Contours, the crossfades, the doors, the ten-second guarantee, the rotation), by docs/superpowers/specs/2026-10-02-arcade-on-the-wall-design.md section 4 and Q181; two iterations if one cannot hold it. After it: M7b (Paint, Tug, the written plan), M6
plan: none yet for iteration 22's M8. docs/superpowers/plans/2026-10-02-it22-suite-room-paint-tug.md is written, NOT reviewed, and kept for M7b's return (Q181); its tasks R and C57 may be taken into M8's plan
```

Also in `state.md`: the `decisions:` line gains, at its start, "Q181 answered (owner, 2026-10-02: M8 before M7b); ".

- [ ] **Step 4: `gate.md`** — insert below its title line:

```markdown
ANSWERED by the owner on 2026-10-02 (Q181, decisions.md): the loop goes on with M8, not with the written plan.
state.md and roadmap.md say so. The owner deletes this file and says "start the workflow loop" in an
`OPERATOR=1` session.
```

and its "Default" paragraph's two sentences from "The loop then enters iteration 22 at the plan review" to "It does not write the plan again." become: "The loop then starts iteration 22 at orient with M8 (Q181); the written Paint and Tug plan is kept, not reviewed and not built." In the table "What needs the owner", the row "The plan review" gets, in its last cell: "Superseded by Q181: that plan waits for M7b."

- [ ] **Step 5: `live-smoke.md`** — the row `| Strongman | 128x64 |  |  |  |  |  |` becomes `| Jump | 128x64 |  |  |  |  |  |`.

- [ ] **Step 6: Read what the loop will be shown**

Run: `OPERATOR=1 CLAUDE_PROJECT_DIR=$PWD python3 scripts/operator/reinject.py --fresh </dev/null`
Expected: it runs without an error; the state it prints says `phase: gated`, milestone M8, plan "none yet for iteration 22's M8"; Q181 is in what it prints of the decisions. The journal's last entry still says "then M7b's Paint and Tug": add, at the journal's end, the entry

```markdown
## The owner's re-scope — 2026-10-02 (Q181)
Not an iteration. The owner, in another session: M8 comes before M7b; iteration 22 is M8 (state.md, roadmap.md,
decisions.md Q181; the design is docs/superpowers/specs/2026-10-02-arcade-on-the-wall-design.md section 4). The
line above, "Iteration 22: ... then M7b's Paint and Tug", no longer holds. The same session put the picamera2
capture, `capture`, `run --game` and `arcade.pi.toml` on main.
```

and run the command again: the last journal entry it prints is this one.

- [ ] **Step 7: Commit, and tell the owner**

```bash
git add docs/superpowers/workflow/decisions.md docs/superpowers/workflow/roadmap.md docs/superpowers/workflow/state.md docs/superpowers/workflow/gate.md docs/superpowers/workflow/live-smoke.md docs/superpowers/workflow/config.md docs/superpowers/workflow/journal.md
git commit -m "docs(workflow): Q181, the loop builds M8 next; the camera on the Pi is the owner's other session's"
```

- [ ] **Step 8: Check what a push would publish**

Run: `git status --short` and `git diff --stat origin/main..main -- '*.png' '*.jpg' '*.jpeg' '*.gif' '*.mp4' | tail -3`
Expected: a clean tree; no image or video in the range (Q98).

- [ ] **Step 9: Ask the owner for the push, then hand over**

The Pi takes its code from GitHub. origin/main is `600bc3c` (pushed from the operator's session at 10:01); main is ahead by this session's commits only (the spec, this plan and its review, Tasks 1 to 7). Ask: "Push main to origin now?" On his yes: `git push origin main`. Without it the plan stops here: nothing reaches the Pi another way.

Then create the worktree for the rest of this plan: `git worktree add ../codeisart-wall -b wall-bringup main`. Tell the owner: the loop can start (delete gate.md, `OPERATOR=1 claude --autocompact 300k`, "start the workflow loop"). Tasks 8 and 9 do not wait for it.

---

### Task 8: The Pi's setup (with the owner's "go"; the wall dark)

**Files:** none in the repo, unless Task 8b runs.

Every command goes in one of the two forms of the Global Constraints: `ssh trey@codeisart.local "flock -w 300 /tmp/pi5.lock <one command>"`, or a script on the call's standard input to `sh -s` or to `/home/trey/codeisart/.venv/bin/python -`. A script on standard input starts with `cd /home/trey/codeisart`.

- [ ] **Step 1: The packages** (the owner's "go": it fetches from the network and reboots the Pi; the wall dark, no unit active). On standard input to `sh -s`:

```sh
sudo apt-get update
sudo apt-get install -y imx500-all
sudo apt-get install -y --no-install-recommends python3-picamera2
dpkg -l imx500-all python3-picamera2 | grep '^ii'
```

Expected: two `ii` lines. Then, in a call of its own, `sudo reboot`; wait for the Pi to answer again.

- [ ] **Step 2: The camera is seen.** `rpicam-hello --list-cameras`, and in a second call `sudo dmesg` read on the Mac for `imx500`.
Expected: a camera line naming `imx500`. On 2026-10-02 10:10, before the packages, it read "No cameras available!" and the kernel log named no sensor; whether the packages change that is not known. If no camera is listed: the owner reseats the ribbon at both ends with the Pi off (the Pi 5's small 22-pin connector) and tries the other CAM/DISP port; if it is still not listed, set `camera_auto_detect=0` and `dtoverlay=imx500` in `/boot/firmware/config.txt` (at his word), reboot, and read the driver's own error from `sudo dmesg`. Nothing below starts until a camera is listed.

- [ ] **Step 3: The code.** On standard input to `sh -s`:

```sh
cd /home/trey/codeisart
git pull --ff-only
git log --oneline -1
git status --short
```

Expected: main's head from Task 7. `show.soak.toml` is untracked there and stays.

- [ ] **Step 4: The venv sees picamera2.** The venv is the show's too, so the check prints where each of the show's and the arcade's compiled packages comes from. Three calls:

  1. `ssh trey@codeisart.local "flock -w 300 /tmp/pi5.lock sed -i 's/^include-system-site-packages = false/include-system-site-packages = true/' /home/trey/codeisart/.venv/pyvenv.cfg"`
  2. `ssh trey@codeisart.local "flock -w 300 /tmp/pi5.lock /home/trey/codeisart/.venv/bin/pip install -q -e '/home/trey/codeisart[pi,dev]'"`
  3. On standard input to `/home/trey/codeisart/.venv/bin/python -`:

```python
import importlib

for name in ("numpy", "cv2", "mediapipe", "pygame", "PIL", "pyte", "picamera2", "libcamera"):
    try:
        mod = importlib.import_module(name)
        print(name, getattr(mod, "__version__", "-"), mod.__file__)
    except Exception as e:
        print(name, "FAILED", repr(e))
import show.main, arcade.main   # the two programs still import
print("show and arcade import")
```

Expected: numpy 2.5.3, cv2 5.0.0.93, mediapipe, pygame, PIL and pyte from `/home/trey/codeisart/.venv/`; picamera2 and libcamera from `/usr/lib/python3/dist-packages/`; no `FAILED`; the last line printed. If picamera2 or libcamera fails (their compiled parts against the venv's numpy), go to Task 8b; do not downgrade the venv's numpy or OpenCV. If a package of the show's now comes from `/usr/lib` or the last line is missing, set the flag back to `false` (call 1 with the two words swapped), record it, and go to Task 8b.

- [ ] **Step 5: One frame, and its colours.** On standard input to `/home/trey/codeisart/.venv/bin/python -` (no file is written on the Pi); the call's standard output goes through `base64 -d` into `<scratchpad>/frame-check.jpg` on the Mac:

```python
import base64, os, sys

os.chdir("/home/trey/codeisart")
sys.path.insert(0, ".")
import cv2

from arcade.sources.capture_picamera2 import READ_TIMEOUT, Picamera2Capture

cap = Picamera2Capture((640, 480))
for _ in range(20):                      # let the exposure settle
    cap.read()
ok, frame = cap.read()
cap.release()
print(ok, frame.shape, frame.mean(axis=(0, 1)).round(1), "wait", READ_TIMEOUT, file=sys.stderr)
sys.stdout.write(base64.b64encode(cv2.imencode(".jpg", frame)[1].tobytes()).decode())
```

Read the image.
Expected: `True (480, 640, 3)` on standard error (so 0.3.37 takes `wait=` as a number and gives the size asked), and a picture whose colours are right (skin is not blue). If red and blue are swapped, `FORMAT` in `arcade/sources/capture_picamera2.py` becomes `"BGR888"` (its comment follows; Task 2's tests read the constant), committed on `wall-bringup`. If the constructor raises "picamera2 gave (w, h) ...": the size the camera gives is recorded and the question goes to the owner before anything is changed. The image stays in the scratchpad.

- [ ] **Step 6: The doctor.** `ssh trey@codeisart.local "flock -w 300 /tmp/pi5.lock sh -s"` with `cd /home/trey/codeisart && .venv/bin/python -m arcade doctor --require camera,pose --capture picamera2` on standard input.
Expected: `camera  ok  picamera2 0: 640x480` and `pose    ok  mediapipe 1.0.1: landmarker ran in <n> ms`.

- [ ] **Step 7: The pose sees a body, 15 s** (no card, no display). The owner stands 2 m in front of the camera for the first ten seconds and steps out of its view for the last five. On standard input to `/home/trey/codeisart/.venv/bin/python -`:

```python
import os, sys, time

os.chdir("/home/trey/codeisart")
sys.path.insert(0, ".")
from arcade.config import ArcadeConfig
from arcade.sources import make_sources

cfg = ArcadeConfig(capture="picamera2")
camera, audio = make_sources(cfg, cfg.size)
try:
    for _ in range(15):
        time.sleep(1.0)
        got = camera.latest()
        print("no result" if got is None else f"t {got[0]:.1f} bodies {len(got[1])}", flush=True)
finally:
    camera.close()
```

Expected: `bodies 1` on most of the first ten lines, `bodies 0` on the last ones, never `no result` after the first line or two. `no result` throughout means the camera thread died: its reason is in the log lines above the output.

- [ ] **Step 8: The start line once with no card, 10 s.** First a no-card config in the ignored `data/`: `ssh trey@codeisart.local "flock -w 300 /tmp/pi5.lock sh -s"` with `cd /home/trey/codeisart && printf 'backend = "fake"\ncapture = "picamera2"\n' > data/arcade.nocard.toml` on standard input. Then the runbook's start line as one command, with `--config data/arcade.nocard.toml --seconds 10 -v`:
`ssh trey@codeisart.local "flock -w 300 /tmp/pi5.lock sudo systemd-run --unit=arcade-wall --pipe --wait --collect --quiet --uid=trey -p AmbientCapabilities='CAP_NET_RAW CAP_SYS_NICE' -p WorkingDirectory=/home/trey/codeisart /home/trey/codeisart/.venv/bin/python -m arcade run --config data/arcade.nocard.toml --seconds 10 -v"`.
Expected: the line `wall 128x64, backend fake`, no "mediapipe camera unavailable", no traceback, the call back after about 10 s: picamera2 opens inside the unit as user trey before the card is ever live. Then remove the config (`rm /home/trey/codeisart/data/arcade.nocard.toml`, as one command).

### Task 8b (only if Task 8 step 4 fails): frames from `rpicam-vid`

**Files:**
- Create: `arcade/sources/capture_rpicam.py`
- Modify: `arcade/config.py` (`CAPTURES` gains `"rpicam"`), `arcade/sources/pose_mediapipe.py` (`open_capture`'s third kind), `arcade.pi.toml` (`capture = "rpicam"`)
- Test: `tests/arcade/test_capture_rpicam.py`

**Interfaces:**
- Produces: `RpicamCapture(size, index=0, popen=subprocess.Popen)` with the same `read()` and `release()`.

- [ ] **Step 1: The failing test** (`tests/arcade/test_capture_rpicam.py`)

```python
"""The rpicam-vid capture, against a fake process: one I420 frame in, one BGR frame out."""
import io

import numpy as np

from arcade.sources.capture_rpicam import RpicamCapture


class FakeProc:
    def __init__(self, data):
        self.stdout, self.terminated = io.BytesIO(data), False

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        return 0


def test_reads_i420_frames_as_bgr_and_ends_not_ok():
    w, h = 64, 48
    yuv = np.full(w * h * 3 // 2, 128, np.uint8)
    yuv[:w * h] = 200                                              # a light grey frame: Y 200, U and V 128
    procs = []
    cap = RpicamCapture((w, h), popen=lambda cmd, **kw: procs.append((cmd, FakeProc(yuv.tobytes()))) or procs[-1][1])
    cmd = procs[0][0]
    assert cmd[0] == "rpicam-vid" and "yuv420" in cmd and str(w) in cmd and str(h) in cmd
    ok, frame = cap.read()
    assert ok and frame.shape == (h, w, 3) and abs(int(frame[0, 0, 0]) - int(frame[0, 0, 2])) <= 2   # grey
    assert cap.read() == (False, None)                             # the stream ended
    cap.release()
    cap.release()
    assert procs[0][1].terminated
```

- [ ] **Step 2: Run it, expect `ModuleNotFoundError`.** `.venv/bin/python -m pytest tests/arcade/test_capture_rpicam.py -q`

- [ ] **Step 3: Implement** (`arcade/sources/capture_rpicam.py`)

```python
"""The Pi's ribbon cameras without picamera2 (cfg.capture "rpicam"): rpicam-vid's raw I420 frames from a pipe."""
from __future__ import annotations

import subprocess

import numpy as np

FRAME_RATE = 30


class RpicamCapture:
    """read() -> (ok, bgr) at size, blocking for one frame of rpicam-vid's stream; (False, None) once it ends.
    release() ends the process, once."""

    def __init__(self, size: tuple[int, int], index: int = 0, popen=subprocess.Popen):
        self.w, self.h = size
        self._proc = popen(["rpicam-vid", "--camera", str(index), "-t", "0", "-n", "--width", str(self.w),
                            "--height", str(self.h), "--framerate", str(FRAME_RATE), "--codec", "yuv420",
                            "--flush", "-o", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self._released = False

    def read(self):
        import cv2

        size = self.w * self.h * 3 // 2
        data = self._proc.stdout.read(size)
        if len(data) < size:
            return False, None
        yuv = np.frombuffer(data, np.uint8).reshape(self.h * 3 // 2, self.w)
        return True, cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)

    def release(self) -> None:
        if self._released:
            return
        self._released = True
        self._proc.terminate()
        try:
            self._proc.wait(timeout=2)
        except Exception:
            pass
```

In `arcade/config.py`: `CAPTURES = ("opencv", "picamera2", "rpicam")`. In `open_capture`, before the `import cv2` line:

```python
    if kind == "rpicam":
        from arcade.sources import capture_rpicam

        return capture_rpicam.RpicamCapture(CAPTURE_SIZE, index)
```

`arcade.pi.toml`: `capture = "rpicam"`; `test_the_pi_config_drives_the_card_through_picamera2` is this plan's own test and follows (its name and the value). The doctor gets its probe in `arcade/main.py`:

```python
def probe_rpicam(timeout: float, index: int = 0) -> tuple[bool, str]:
    """The Pi's ribbon camera through rpicam-vid (capture "rpicam"), opened as the arcade opens it."""
    from arcade.sources import capture_rpicam
    from arcade.sources.pose_mediapipe import CAPTURE_SIZE

    return _first_frame(capture_rpicam.RpicamCapture(CAPTURE_SIZE, index), timeout, f"rpicam {index}",
                        "is the ribbon seated: rpicam-hello --list-cameras")
```

and `make_probes`' camera line becomes:

```python
    camera = {"picamera2": "probe_picamera2", "rpicam": "probe_rpicam"}.get(capture, "probe_camera")
    return {"camera": lambda t: globals()[camera](t, camera_index),
```

- [ ] **Step 4: Run** `.venv/bin/python -m pytest tests/arcade/test_capture_rpicam.py tests/arcade/test_config.py tests/arcade/test_doctor.py tests/arcade/test_pose_mediapipe.py -q`; all pass. Commit on `wall-bringup`, push the branch with the owner's word, check it out on the Pi, and go on at Task 8 step 5 with `RpicamCapture`.

---

### Task 9: The wall session (with the owner at the wall)

**Files:**
- Modify: `docs/superpowers/workflow/live-smoke.md` (the owner's rows), `docs/superpowers/workflow/evidence/hardware.md` (the gamma check), `arcade.pi.toml` (only if the gamma check says so)
- Create: `docs/superpowers/workflow/evidence/wall-arcade-2026-10-02.md` (the session's record: each run, its command, the sender's last line, the owner's words)

By the wall session protocol: each run is announced (what is on the wall, how long, what to look for), starts on the owner's "go" after a 5 s lead, and is asked back in one or two words. A run is checked to have started (its first log lines) before the owner is asked anything. Runs use the runbook's start line (section 4), sent as Task 8 step 8 sends it (one command in double quotes after the lock), with a `--seconds` that ends them. A run holds the Pi's lock until it ends; the early stop is the Global Constraints' one exception and needs the owner's word each time.

- [ ] **Step 1: The card is free.** `systemctl is-active promptviz-party.service show.service`. An active unit is stopped only at the owner's word, and started again at the session's end.

- [ ] **Step 2: The gamma check** (the owner's open item since 2026-09-30). The config's `gamma` is the light model of the limiter and the governor: `arcade/look.py:68` is `light = (byte / 255) ** (2.2 / gamma)`, so 2.2 says the wall's light is linear in the bytes and 1.0 says the card applies a 2.2 curve. The mapping below is the tool's own (`tools/wall_pattern.py:84-87`). Then, 20 s, in the start line's form (Task 8):
`sudo systemd-run --unit=arcade-wall --pipe --wait --collect --quiet --uid=trey -p AmbientCapabilities='CAP_NET_RAW CAP_SYS_NICE' -p WorkingDirectory=/home/trey/codeisart /home/trey/codeisart/.venv/bin/python tools/wall_pattern.py gamma --backend colorlight --iface eth0 --width 128 --height 64 --seconds 20`.
The top row has three blocks: a flat grey of 128 on the left, a one-pixel checkerboard of black and white in the middle (half the light), a flat grey of 186 on the right. Ask, from 3 m, eyes half shut: "which flat block is as bright as the checkerboard: left, right, or neither (and is the checkerboard brighter or darker than the right one)?"
  - "left": the card sends the bytes as they are; `gamma = 2.2` stands (the default; nothing to change).
  - "right": the card applies gamma; `arcade.pi.toml` gains `gamma = 1.0`.
  - "neither, the checkerboard is brighter than the right block": the card's curve is steeper than 2.2 (it was saved with 2.8); `gamma = 1.0` is the nearest value the arcade allows and `arcade.pi.toml` gains it. Record it as an owner item: the model then reads mid greys brighter than the wall shows them, which errs toward holding a flash, not toward passing one.
  - Anything else ("neither, darker than the left", or he cannot tell): nothing is changed and the reading is recorded.
  A changed `arcade.pi.toml` is committed on `wall-bringup`, pushed at the owner's word and pulled on the Pi before step 3. The owner's words and the outcome go into `evidence/hardware.md` under a new dated heading. No file of the governor, the limiter or the driver is edited: only the number they are given.

- [ ] **Step 3: The mirror.** `run --config arcade.pi.toml --seconds 60 -v`. The owner steps in: his figure appears; he raises his right hand: the figure's hand on the wall's same side goes up (a mirror). Asked back: "figure: yes or no; hand on your side: yes or no; lag: fine or slow".

- [ ] **Step 4: `calibrate`.** `calibrate --config arcade.pi.toml` (it ends by itself: "SAVED", or a failure's words). The owner follows the wall: hands up, stand far left, far right, near, stand still, clear the frame. Expected: `data/calibration.json` on the Pi; its text (`cat /home/trey/codeisart/data/calibration.json`) goes into the session's record. A failure's words ("NO ONE CAME", "NOT SAVED") are recorded and the step is run once more after the cause is named. Then step 3's 60 s mirror once more: if the figure is gone or out of place with the calibration, the file is removed (`rm /home/trey/codeisart/data/calibration.json`, as one command) and the session goes on with the defaults; the fault is a carried fix.

- [ ] **Step 5: Copy Me through the lobby.** `run --config arcade.pi.toml --seconds 240 -v`. The owner walks up, waits for the hand-up sign, raises a hand, plays the three rounds, reads the card, walks away; the title returns. Asked back for `live-smoke.md`'s Copy Me row: responded, understood, want another go (1 to 5), broken, notes. The sender's last line is recorded (a clean run reads `0 late (over 1 ms)`).

- [ ] **Step 6: The other games, as far as time allows**, each `run --config arcade.pi.toml --game <name> --seconds 180 -v`, in this order: `pong`, `quickdraw`, `dodge`, `jump`, `flap`, `swat`, `freeze`. One row of `live-smoke.md` each.

- [ ] **Step 7: Faults.** A fault that stops play (a game cannot start, cannot be read, or crashes) is fixed in the session on `wall-bringup` with a test that fails first, the changed files' tests run on the Mac, the branch pushed at the owner's word and checked out on the Pi. Anything else is written into the session's record as a carried fix for the loop. No change to the governor, the limiter or the driver.

- [ ] **Step 8: Close.** The wall dark; a unit stopped in step 1 started again at the owner's word. Commit the record, `live-smoke.md`, `hardware.md` (and `arcade.pi.toml` if step 2 changed it) on `wall-bringup`; merge to main between the loop's iterations (state.md's `phase` reads `orient` or `gated`), never while its orchestrator has worktree agents out.

Done (spec section 3) when: a person walks up, sees their figure, raises a hand, plays one game to its card and walks away to the title; the sender's line reads no late frame; one game's row in `live-smoke.md` is filled.
