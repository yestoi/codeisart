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
