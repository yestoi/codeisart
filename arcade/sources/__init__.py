"""The source factory: make_sources builds the (camera, audio) pair the runner reads each tick."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from arcade.calibration import Calibration, load_calibration
from arcade.config import ArcadeConfig
from arcade.sources.replay import open_replay
from arcade.sources.scenario import ScenarioReader, ScenarioWriter, make_header
from arcade.sources.scripted import SCRIPT_INPUTS, SCRIPTS, ScriptedCamera


class NoSource:
    """The none camera or audio: no result, never available."""

    available = False

    def latest(self) -> None:
        return None

    def close(self) -> None:
        pass


def make_sources(cfg: ArcadeConfig, size: tuple[int, int], clock: Callable[[], float] = time.monotonic,
                 script: str | None = None, *, calibration: Calibration | None = None,
                 replay: str | Path | None = None):
    """(camera, audio) for cfg. script names a SCRIPTS entry played by a ScriptedCamera instead of cfg.camera, claiming
    its SCRIPT_INPUTS; replay is a scenario file's path, played by open_replay as both the camera and the audio, as
    is cfg.scenario when cfg.camera is "replay" and no script is given (script and replay are exclusive).
    mediapipe opens the camera here, on the calling (main) thread. Bodies are placed against calibration
    (load_calibration(cfg.data_dir) when None). Audio is otherwise the none source (Q99). Captures are stamped on
    clock."""
    if script is not None and replay is not None:
        raise ValueError("a script and a replay are exclusive; give one")
    if script is None and replay is None and cfg.camera == "replay":
        if not cfg.scenario:
            raise ValueError("camera replay needs scenario, the path of a scenario file")
        replay = cfg.scenario
    if replay is not None:
        return open_replay(replay, calibration if calibration is not None else load_calibration(cfg.data_dir), clock)
    if script is not None:
        if script not in SCRIPTS:
            raise ValueError(f"unknown script {script!r}; known: {', '.join(sorted(SCRIPTS))}")
        camera = ScriptedCamera(SCRIPTS[script](), clock, provides=SCRIPT_INPUTS.get(script))
    elif cfg.camera == "mediapipe":
        from arcade.sources import pose_mediapipe   # here: it resolves arcade.main.MODEL_PATH, and main imports us
        cal = calibration if calibration is not None else load_calibration(cfg.data_dir)
        camera = pose_mediapipe.MediaPipeCamera(cfg, size, clock, calibration=cal)
    elif cfg.camera == "none":
        camera = NoSource()
    else:
        raise ValueError(f"camera {cfg.camera!r} is not available yet; use mediapipe or none")
    return camera, NoSource()


__all__ = ["SCRIPTS", "NoSource", "ScenarioReader", "ScenarioWriter", "ScriptedCamera", "make_header", "make_sources",
           "open_replay"]
