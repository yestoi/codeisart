"""Replay sources (spec 6.1, 6.2): a sensed scenario file played back as the camera and the microphone, one record
per runner tick; a raw one as the camera, each capture through the feature extraction and the tracker again."""
from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Callable, Iterable, Iterator

import numpy as np

from arcade.calibration import Calibration
from arcade.sensed import CAMERA_INPUTS, MOTION_GRID, Audio, Sensed
from arcade.sources.camera import BodyTracker, CameraResult
from arcade.sources.scenario import RawRecord, ScenarioReader


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


RAW_PROVIDES = frozenset({"pose", "motion"})   # a grey frame has no saturated halo, so no light is found (Q140)
DUE_SLACK = 1e-9                               # s: + 0.1 s on the clock can read 0.0999...; the capture is due


class RawReplayCamera:
    """The camera of a raw recording (spec 6.3, the owner's re-tuning files): each capture runs again through
    FrameFeatures on the wall's motion grid (its grey frame as BGR, mirrored as the header says, true by default)
    and BodyTracker (its detections, already mirrored, at its t), both against calibration, as the source ran them.

    Paced by capture time: latest() runs, in order, every capture whose t less the first's (t0) is at most the time
    since this camera opened (+ DUE_SLACK), and gives the newest one's (opened + t - t0, bodies, blobs, motion);
    None before the first. available until the captures end: the call that runs the last is still available, the
    next finds none left (as ReplayCamera); the last result is then held. provides is RAW_PROVIDES."""

    provides = RAW_PROVIDES

    def __init__(self, reader: ScenarioReader, calibration: Calibration | None = None,
                 clock: Callable[[], float] = time.monotonic):
        from arcade.sources.blobs import FrameFeatures   # here: blobs imports cv2, and importing us must not

        self.reader, self.clock = reader, clock
        self.features = FrameFeatures(MOTION_GRID, calibration, mirror=reader.header.get("mirror", True))
        self.tracker = BodyTracker(calibration)
        self.finished = False
        self._result: CameraResult | None = None
        self._it: Iterator[RawRecord] = iter(reader)
        self._next: RawRecord | None = self._read()
        self.t0 = self._next.t if self._next is not None else 0.0
        self.opened = float(clock())

    @property
    def available(self) -> bool:
        return not self.finished

    def _read(self) -> RawRecord | None:
        return next(self._it, None)

    def _run(self, r: RawRecord) -> CameraResult:
        blobs, motion = self.features.update(np.repeat(r.frame[:, :, None], 3, axis=2), r.t)
        return self.opened + (r.t - self.t0), self.tracker.update(r.detections, r.t), blobs, motion

    def latest(self) -> CameraResult | None:
        if not self.finished:
            since = self.clock() - self.opened + DUE_SLACK
            ran = False
            while self._next is not None and self._next.t - self.t0 <= since:
                self._result, ran = self._run(self._next), True
                self._next = self._read()
            if self._next is None and not ran:
                self.finished = True
        return self._result

    def close(self) -> None:
        close = getattr(self._it, "close", None)
        if close is not None:
            close()


class NoAudio:
    """The microphone of a raw replay: none (a raw file's sound is not replayed, Q99)."""

    available = False

    def latest(self) -> None:
        return None

    def close(self) -> None:
        pass


def open_replay(path: Path | str, calibration: Calibration | None = None,
                clock: Callable[[], float] = time.monotonic
                ) -> tuple[ReplayCamera, ReplayAudio] | tuple[RawReplayCamera, NoAudio]:
    """The camera and microphone of a scenario file. A sensed file: a ReplayCamera and a ReplayAudio sharing one
    stream on clock, the camera providing the header's camera inputs (every one without them). A raw file: a
    RawReplayCamera on clock and NoAudio. calibration is the one the recording was made with (the header holds
    none, C21): every body and blob is placed against it, the default one when None. A file without a header
    raises ValueError here."""
    reader = ScenarioReader(path, calibration)
    if reader.header["type"] == "raw":
        return RawReplayCamera(reader, calibration, clock), NoAudio()
    stream = ReplayStream(reader, clock)
    return ReplayCamera(stream, reader.inputs), ReplayAudio(stream)
