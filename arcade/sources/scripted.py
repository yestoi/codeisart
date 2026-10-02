"""A camera that plays scripted frames (arcade.sources.actors.scene) live: `python -m arcade run --script NAME`."""
from __future__ import annotations

import time
from typing import Callable, Iterable

from arcade.sensed import CAMERA_INPUTS, Sensed
from arcade.sources.actors import Person, scene
from arcade.sources.camera import CameraResult


class ScriptedCamera:
    """One frame of frames per latest() call, stamped clock() as it is read, so the runner sees a fresh capture every
    tick on its own clock whatever t the script gave the frame. latest() is None once the frames run out; available
    is whether the last latest() gave a frame. provides is the camera inputs the script stands for (C35): every one
    unless given (a subclass may set its own as a class attribute)."""

    provides: frozenset[str] = CAMERA_INPUTS

    def __init__(self, frames: Iterable[Sensed], clock: Callable[[], float] = time.monotonic,
                 provides: Iterable[str] | None = None):
        self._frames = iter(frames)
        self.clock = clock
        if provides is not None:
            self.provides = frozenset(provides)
        self.available = False

    def latest(self) -> CameraResult | None:
        frame = next(self._frames, None)
        self.available = frame is not None
        if frame is None:
            return None
        return self.clock(), frame.bodies, frame.blobs, frame.motion

    def close(self) -> None:
        pass


def walkup():
    """A person walks in from the left edge, stands in the zone (the lobby's mirror, then the invite at 1.5 s near)
    and raises the right hand at 3.2 s, then stands until 30 s."""
    person = Person(0.05, id=1).walk(0.45, 1.5, at=0.3).raise_hand(3.2, 0.6)
    return scene(persons=[person], ticks=30 * 30)


SCRIPTS = {"walkup": walkup}
SCRIPT_INPUTS = {"walkup": frozenset({"pose"})}   # walkup holds no light: it offers no blob game (C35)
