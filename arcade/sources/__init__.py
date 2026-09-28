"""The source factory: make_sources builds the (camera, audio) pair the runner reads each tick."""
from __future__ import annotations

import time
from typing import Callable

from arcade.calibration import Calibration, load_calibration
from arcade.config import ArcadeConfig
from arcade.sources.scripted import SCRIPTS, ScriptedCamera


class NoSource:
    """The none camera or audio: no result, never available."""

    available = False

    def latest(self) -> None:
        return None

    def close(self) -> None:
        pass


def make_sources(cfg: ArcadeConfig, size: tuple[int, int], clock: Callable[[], float] = time.monotonic,
                 script: str | None = None, *, calibration: Calibration | None = None):
    """(camera, audio) for cfg. script names a SCRIPTS entry played by a ScriptedCamera instead of cfg.camera;
    mediapipe opens the camera here, on the calling (main) thread, and places bodies against calibration
    (load_calibration(cfg.data_dir) when None). Audio is the none source until M5. Captures are stamped on clock."""
    if script is not None:
        if script not in SCRIPTS:
            raise ValueError(f"unknown script {script!r}; known: {', '.join(sorted(SCRIPTS))}")
        camera = ScriptedCamera(SCRIPTS[script](), clock)
    elif cfg.camera == "mediapipe":
        from arcade.sources import pose_mediapipe   # here: it resolves arcade.main.MODEL_PATH, and main imports us
        cal = calibration if calibration is not None else load_calibration(cfg.data_dir)
        camera = pose_mediapipe.MediaPipeCamera(cfg, size, clock, calibration=cal)
    elif cfg.camera == "none":
        camera = NoSource()
    else:
        raise ValueError(f"camera {cfg.camera!r} is not available yet; use mediapipe or none")
    return camera, NoSource()


__all__ = ["SCRIPTS", "NoSource", "ScriptedCamera", "make_sources"]
