"""Replay sources (spec 6.1, 6.2): a sensed scenario file played back as the camera and the microphone, one record
per runner tick."""
from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Callable, Iterable, Iterator

from arcade.calibration import Calibration
from arcade.sensed import CAMERA_INPUTS, Audio, Sensed
from arcade.sources.camera import CameraResult
from arcade.sources.scenario import ScenarioReader


class ReplayStream:
    """The shared cursor over recorded Sensed records, on clock (the runner's). advance() reads the next record
    (current, read at read_t); a record with camera_fresh is a new capture (shot), stamped capture_t: read_t less
    its age (t - camera_t), as old as the recording had it. A record without one holds the last capture, as a live
    camera holds its result, so a 10 fps recording replays 10 captures a second, not 30. After the end (finished)
    the last record is held; an empty stream gives one empty, fresh record."""

    def __init__(self, records: Iterable[Sensed], clock: Callable[[], float] = time.monotonic):
        self._it: Iterator[Sensed] = iter(records)
        self.clock = clock
        self.current: Sensed | None = None     # the record the last advance() read
        self.read_t: float | None = None       # when it was read, on clock
        self.shot: Sensed | None = None        # the record of the newest capture, None before the first
        self.capture_t: float | None = None    # that capture's time, on clock
        self.finished = False

    def advance(self) -> Sensed:
        if not self.finished:
            try:
                record = next(self._it)
            except StopIteration:
                self.finished = True
            else:
                self._take(record)
        if self.current is None:
            self._take(Sensed(0.0, camera_fresh=True))
        return self.current

    def _take(self, record: Sensed) -> None:
        now = self.clock()
        self.current, self.read_t = record, now
        if record.camera_fresh:
            age = record.t - record.camera_t
            self.shot, self.capture_t = record, now - (age if math.isfinite(age) and age > 0.0 else 0.0)

    def close(self) -> None:
        close = getattr(self._it, "close", None)
        if close is not None:
            close()


class ReplayCamera:
    """The camera of a replay: latest() advances the shared stream one record (the runner calls it once a tick,
    before the audio's) and gives the newest capture as camera.py's CameraResult, its motion on the file's 128x64
    grid (the runner resamples it to the wall) or the empty grid; None before the recording's first capture.
    available until the stream has finished; the held last capture then goes stale in the runner. provides is the
    camera inputs the recording holds (C35; open_replay gives the header's), every one by default."""

    def __init__(self, stream: ReplayStream, provides: frozenset[str] = CAMERA_INPUTS):
        self.stream = stream
        self.provides = frozenset(provides) & CAMERA_INPUTS

    @property
    def available(self) -> bool:
        return not self.stream.finished

    def latest(self) -> CameraResult | None:
        self.stream.advance()
        shot = self.stream.shot
        if shot is None:
            return None
        return self.stream.capture_t, shot.bodies, shot.blobs, shot.motion

    def close(self) -> None:
        self.stream.close()


class ReplayAudio:
    """The microphone of a replay: the audio of the record the camera last read, stamped when it was read (the
    runner's (capture_t, Audio)); None before the first read."""

    def __init__(self, stream: ReplayStream):
        self.stream = stream

    @property
    def available(self) -> bool:
        return not self.stream.finished

    def latest(self) -> tuple[float, Audio] | None:
        s = self.stream
        return None if s.current is None else (s.read_t, s.current.audio)

    def close(self) -> None:
        self.stream.close()


def open_replay(path: Path | str, calibration: Calibration | None = None,
                clock: Callable[[], float] = time.monotonic) -> tuple[ReplayCamera, ReplayAudio]:
    """The camera and microphone of a sensed scenario file, sharing one stream on clock. calibration is the one
    the recording was made with (the header holds none, C21): every body and blob is placed against it, the
    default one when None. A file without a header raises ValueError here, and so does a raw file."""
    reader = ScenarioReader(path, calibration)
    if reader.header["type"] != "sensed":
        raise ValueError(f"{path}: a raw recording replays through the feature extraction and the tracker, "
                         "which are not built yet")
    stream = ReplayStream(reader, clock)
    return ReplayCamera(stream, reader.inputs), ReplayAudio(stream)
