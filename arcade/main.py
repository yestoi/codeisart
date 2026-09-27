"""Arcade command line. Task 0 provides `doctor`; Task 18 adds run (the default), calibrate, record, stats."""
from __future__ import annotations

import argparse
import importlib.metadata
import sys
import threading
import time
from pathlib import Path
from typing import Callable, TextIO

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "pose_landmarker_lite.task"
TIMEOUT = 5.0
Probe = Callable[[float], tuple[bool, str]]


def probe_camera(timeout: float, index: int = 0) -> tuple[bool, str]:
    """Runs on the calling thread, unlike probe_pose: macOS asks for camera access only from the
    main thread. The deadline is checked between reads, so one blocking read can overrun it."""
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


def within(timeout: float, what: str, fn: Callable[[], tuple[bool, str]]) -> tuple[bool, str]:
    """fn's result if it finishes within timeout, else unavailable. fn runs in a daemon thread,
    which cannot be killed: a hung fn keeps running until the process exits, which for the
    doctor is right away. An exception in fn is raised here, so the doctor reports it."""
    box: dict = {}

    def target():
        try:
            box["result"] = fn()
        except BaseException as e:
            box["error"] = e

    worker = threading.Thread(target=target, name=f"doctor-{what}", daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        return False, f"{what} did not finish within {timeout:g} s"
    if "error" in box:
        raise box["error"]
    return box["result"]


def probe_pose(timeout: float, model: Path = MODEL_PATH) -> tuple[bool, str]:
    if not Path(model).exists():
        return False, f"model missing at {model}; run: python tools/env_check.py"
    import mediapipe as mp   # untimed: a cold first import can take seconds, but it does not hang

    return within(timeout, "pose landmarker", lambda: _run_pose(mp, Path(model)))


def _run_pose(mp, model: Path) -> tuple[bool, str]:
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
    if not require:
        print(f"doctor: --require names no source; choose from {', '.join(sorted(probes))}", file=out)
        return 2
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
