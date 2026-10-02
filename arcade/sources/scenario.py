"""Scenario files (spec 6.3): gzip JSON lines, a header record first, then one record per line.

A sensed file holds one Sensed per runner tick. Its motion is packed (np.packbits, base64) on the fixed MOTION_GRID
of 128x64 whatever grid the record had, and the runner resamples it to the wall on replay; no grid is null and
decodes to the empty (0, 0) grid. A record holds only fields of the dataclasses it encodes (spec 6.5): no image,
no sound, nothing the runner sets (player, player2, present, camera_seq), and no zone placement, which decode()
does again with the caller's calibration (the header holds none; C21).

A raw file (the owner's re-tuning recordings) holds one RawRecord per camera capture: the capture time, the
model's detections, a 160x120 grey frame (base64) and the capture's sound as a 16 kHz WAV (base64), its RIFF header
packed with struct.

A bad line is skipped with one warning and counted in ScenarioReader.skipped, and a file cut off mid-write ends
with one warning: the reader never raises into the runner (Review Focus 4). A file without a header is refused
when it is opened.
"""
from __future__ import annotations

import base64
import dataclasses
import gzip
import json
import logging
import math
import struct
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import numpy as np

from arcade.calibration import Calibration
from arcade.sensed import MOTION_GRID, Audio, Blob, Body, Keypoint, Sensed, _resample, place, place_blob

log = logging.getLogger("arcade")

VERSION = 1
TYPES = ("sensed", "raw")
PACKED_BYTES = MOTION_GRID[0] * MOTION_GRID[1] // 8
AUDIO_FLAGS = ("clap", "onset", "beat")
# what a malformed line raises in decode: JSON, a missing key, a wrong type or count, an overflow
BAD_LINE = (ValueError, KeyError, TypeError, IndexError, AttributeError, ArithmeticError)


# ----- the header -----

def make_header(type: str = "sensed", *, fps: float = 30, script: str | None = None,
                cues=(), created: str | None = None, git: str | None = None) -> dict:
    """A version 1 header. cues are (t, text) pairs, the script's ground truth for cue assertions; created defaults
    to now in UTC; git is the caller's (this module never reads the checkout)."""
    if created is None:
        created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return check_header({"kind": "header", "version": VERSION, "type": type, "fps": fps, "grid": list(MOTION_GRID),
                         "script": script, "cues": [[float(t), str(text)] for t, text in cues],
                         "created": created, "git": git})


def _number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def check_header(obj) -> dict:
    """obj when it is a version 1 header, else ValueError naming what is wrong."""
    if not isinstance(obj, dict) or obj.get("kind") != "header":
        raise ValueError("the first record is not a header")
    problems = []
    if obj.get("version") != VERSION or isinstance(obj.get("version"), bool):
        problems.append(f"version {obj.get('version')!r} (this reader reads {VERSION})")
    if obj.get("type") not in TYPES:
        problems.append(f"type {obj.get('type')!r} (one of {TYPES})")
    if not (_number(obj.get("fps")) and obj["fps"] > 0):
        problems.append(f"fps {obj.get('fps')!r}")
    if obj.get("grid") != list(MOTION_GRID):
        problems.append(f"grid {obj.get('grid')!r} (the fixed {list(MOTION_GRID)})")
    for key in ("script", "created", "git"):
        if obj.get(key) is not None and not isinstance(obj[key], str):
            problems.append(f"{key} {obj[key]!r}")
    cues = obj.get("cues")
    if not isinstance(cues, list) or not all(isinstance(c, list) and len(c) == 2 and _number(c[0])
                                             and isinstance(c[1], str) for c in cues):
        problems.append(f"cues {cues!r} (a list of [t, text])")
    if problems:
        raise ValueError("bad header: " + "; ".join(problems))
    return obj


# ----- sensed records -----

def _r(v, digits: int = 4) -> float:
    return round(float(v), digits)


def _finite(v) -> float:
    f = float(v)
    if not math.isfinite(f):
        raise ValueError(f"not a finite number: {v!r}")
    return f


def _bool(v) -> bool:
    if not isinstance(v, (bool, np.bool_)):
        raise TypeError(f"not true or false: {v!r}")
    return bool(v)


def _keypoints_obj(kps) -> list:
    return [[_r(k.x), _r(k.y), _r(k.conf, 3)] for k in kps]


def _keypoints(obj) -> tuple[Keypoint, ...]:
    return tuple(Keypoint(float(x), float(y), float(c)) for x, y, c in obj)


def _box(obj) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = (float(v) for v in obj)
    return (x0, y0, x1, y1)


def _packed(motion: np.ndarray) -> str | None:
    if motion.size == 0:
        return None
    w, h = MOTION_GRID
    grid = motion if motion.shape == (h, w) else _resample(motion, w, h)
    return base64.b64encode(np.packbits(grid.ravel())).decode("ascii")


def _motion(obj) -> np.ndarray:
    if obj is None:
        return np.zeros((0, 0), bool)
    raw = base64.b64decode(obj, validate=True)
    if len(raw) != PACKED_BYTES:
        raise ValueError(f"motion holds {len(raw)} bytes, not the {PACKED_BYTES} of the {MOTION_GRID} grid")
    w, h = MOTION_GRID
    return np.unpackbits(np.frombuffer(raw, np.uint8)).astype(bool).reshape(h, w)


def encode(s: Sensed) -> str:
    """One JSON line (no newline) for s."""
    a = s.audio
    obj = {
        "t": _r(s.t),
        "camera_t": _r(s.camera_t),
        "camera_fresh": bool(s.camera_fresh),
        "bodies": [{"id": int(b.id), "box": [_r(v) for v in b.box], "keypoints": _keypoints_obj(b.keypoints),
                    "vx": _r(b.vx), "vy": _r(b.vy), "scale": _r(b.scale), "seen_ago": _r(b.seen_ago),
                    "measured": bool(b.measured), "torso_per_width": _r(b.torso_per_width)}
                   for b in s.bodies],
        "blobs": [{"x": _r(b.x), "y": _r(b.y), "size": _r(b.size), "color": [int(c) for c in b.color],
                   "id": int(b.id), "vx": _r(b.vx), "vy": _r(b.vy)} for b in s.blobs],
        "motion": _packed(s.motion),
        "audio": {f.name: (bool(getattr(a, f.name)) if f.name in AUDIO_FLAGS
                           else None if getattr(a, f.name) is None else _r(getattr(a, f.name)))
                  for f in dataclasses.fields(Audio)},
    }
    return json.dumps(obj, separators=(",", ":"))


def _body(b: dict) -> Body:
    return Body(int(b["id"]), _box(b["box"]), _keypoints(b["keypoints"]), vx=float(b.get("vx", 0.0)),
                vy=float(b.get("vy", 0.0)), scale=float(b.get("scale", 0.0)), seen_ago=float(b.get("seen_ago", 0.0)),
                measured=_bool(b.get("measured", True)), torso_per_width=float(b.get("torso_per_width", 0.0)))


def _blob(b: dict) -> Blob:
    red, green, blue = (int(c) for c in b["color"])
    return Blob(float(b["x"]), float(b["y"]), float(b["size"]), (red, green, blue), id=int(b.get("id", -1)),
                vx=float(b.get("vx", 0.0)), vy=float(b.get("vy", 0.0)))


def _audio(a: dict) -> Audio:
    if not isinstance(a, dict):
        raise TypeError(f"audio is not an object: {a!r:.80}")
    kw = {}
    for f in dataclasses.fields(Audio):
        if f.name in a:
            v = a[f.name]
            kw[f.name] = (_bool(v) if f.name in AUDIO_FLAGS
                          else None if f.name == "bpm" and v is None else float(v))
    return Audio(**kw)


def decode(line: str, calibration: Calibration | None = None) -> Sensed:
    """The Sensed of one line, every body and blob placed against calibration (the default one when None): pass
    the calibration the recording was made with (C21). A record without camera_t or camera_fresh (one written by
    hand) is a fresh capture at its t. A malformed line raises one of BAD_LINE."""
    obj = json.loads(line)
    if not isinstance(obj, dict):
        raise TypeError(f"a record is a JSON object, got {type(obj).__name__}")
    cal = calibration or Calibration()
    t = _finite(obj["t"])
    return Sensed(t, camera_t=_finite(obj.get("camera_t", t)), camera_fresh=_bool(obj.get("camera_fresh", True)),
                  bodies=tuple(place(_body(b), cal) for b in obj.get("bodies", ())),
                  blobs=tuple(place_blob(_blob(b), cal) for b in obj.get("blobs", ())),
                  motion=_motion(obj.get("motion")), audio=_audio(obj.get("audio", {})))


# ----- files -----

def _open_text(path: Path, mode: str):
    """gzip in text mode. A byte that is not UTF-8 reads as U+FFFD, so it spoils its line only (skipped), never the
    rest of the file; compression level 6 (zlib's default) keeps a live recording's write cheap."""
    if "w" in mode:
        return gzip.open(path, mode, compresslevel=6, encoding="utf-8")
    return gzip.open(path, mode, encoding="utf-8", errors="replace")


# ----- raw records (spec 6.3: the owner's re-tuning recordings, spec 6.5's rules) -----

FRAME_SHAPE = (120, 160)          # (height, width) of the grey frame a raw record holds
AUDIO_RATE = 16000                # Hz, mono, 16-bit
_RIFF = struct.Struct("<4sI4s4sIHHIIHH4sI")   # RIFF, WAVE, a 16-byte PCM fmt chunk, then the data chunk's header


@dataclass(frozen=True, eq=False)
class RawRecord:
    """One camera capture as the sources saw it: its capture time, the model's detections (box and keypoints,
    mirrored, before the tracker), the grey frame and the sound since the last capture (int16 at AUDIO_RATE)."""

    t: float
    _: dataclasses.KW_ONLY
    detections: tuple[tuple[tuple[float, float, float, float], tuple[Keypoint, ...]], ...] = ()
    frame: np.ndarray = field(default_factory=lambda: np.zeros(FRAME_SHAPE, np.uint8))
    samples: np.ndarray = field(default_factory=lambda: np.zeros(0, np.int16))


def wav_bytes(samples: np.ndarray, rate: int = AUDIO_RATE) -> bytes:
    """samples (1-D int16) as a mono 16-bit PCM WAV file, its RIFF header packed with struct."""
    pcm = np.asarray(samples)
    if pcm.dtype != np.int16 or pcm.ndim != 1:
        raise ValueError(f"a WAV holds 1-D int16 samples, got {pcm.dtype} {pcm.shape}")
    data = pcm.astype("<i2").tobytes()
    return _RIFF.pack(b"RIFF", 36 + len(data), b"WAVE", b"fmt ", 16, 1, 1, rate, rate * 2, 2, 16, b"data",
                      len(data)) + data


def wav_samples(blob: bytes) -> tuple[int, np.ndarray]:
    """(rate, samples) of a WAV written by wav_bytes; the sample count is the data chunk's size in its header."""
    if len(blob) < _RIFF.size:
        raise ValueError(f"a WAV of {len(blob)} bytes has no header")
    riff, _, form, fmt, fmt_size, pcm, channels, rate, _, _, bits, data, size = _RIFF.unpack_from(blob)
    if ((riff, form, fmt, data) != (b"RIFF", b"WAVE", b"fmt ", b"data")
            or (fmt_size, pcm, channels, bits) != (16, 1, 1, 16)):
        raise ValueError("not a mono 16-bit PCM WAV")
    if size % 2 or _RIFF.size + size > len(blob):
        raise ValueError(f"the WAV's data chunk says {size} bytes, it holds {len(blob) - _RIFF.size}")
    return rate, np.frombuffer(blob, "<i2", count=size // 2, offset=_RIFF.size).astype(np.int16)


def encode_raw(r: RawRecord) -> str:
    frame = np.asarray(r.frame)
    if frame.shape != FRAME_SHAPE or frame.dtype != np.uint8:
        raise ValueError(f"a raw frame is {FRAME_SHAPE} uint8, got {frame.shape} {frame.dtype}")
    obj = {"t": _r(r.t, 6),
           "detections": [{"box": [_r(v) for v in box], "keypoints": _keypoints_obj(kps)} for box, kps in r.detections],
           "frame": base64.b64encode(frame.tobytes()).decode("ascii"),
           "wav": base64.b64encode(wav_bytes(r.samples)).decode("ascii")}
    return json.dumps(obj, separators=(",", ":"))


def decode_raw(line: str) -> RawRecord:
    obj = json.loads(line)
    if not isinstance(obj, dict):
        raise TypeError(f"a record is a JSON object, got {type(obj).__name__}")
    pixels = base64.b64decode(obj["frame"], validate=True)
    h, w = FRAME_SHAPE
    if len(pixels) != h * w:
        raise ValueError(f"a raw frame holds {h * w} bytes, got {len(pixels)}")
    rate, samples = wav_samples(base64.b64decode(obj["wav"], validate=True))
    if rate != AUDIO_RATE:
        raise ValueError(f"raw sound is at {AUDIO_RATE} Hz, got {rate}")
    return RawRecord(_finite(obj["t"]),
                     detections=tuple((_box(d["box"]), _keypoints(d["keypoints"])) for d in obj["detections"]),
                     frame=np.frombuffer(pixels, np.uint8).reshape(FRAME_SHAPE).copy(), samples=samples)


class ScenarioWriter:
    """Writes header (checked) as the first line of a gzip file at path, then write(record) one line each: a
    Sensed in a sensed file, a RawRecord in a raw one (TypeError otherwise). A context manager; close() ends the
    gzip stream."""

    def __init__(self, path: Path | str, header: dict):
        self.header = check_header(dict(header))
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = _open_text(self.path, "wt")
        self._fh.write(json.dumps(self.header, separators=(",", ":")) + "\n")

    def write(self, record) -> None:
        kind, line = (Sensed, encode) if self.header["type"] == "sensed" else (RawRecord, encode_raw)
        if not isinstance(record, kind):
            raise TypeError(f"a {self.header['type']} file takes {kind.__name__} records, got {type(record).__name__}")
        self._fh.write(line(record) + "\n")

    def close(self) -> None:
        self._fh.close()

    def __enter__(self) -> "ScenarioWriter":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


class ScenarioReader:
    """A scenario file: header (checked when opened: ValueError for a file that is not gzip or has no header) and
    cues; iterating yields its records, bodies and blobs placed against calibration. skipped counts the bad lines
    of the last iteration, each skipped with one warning, and a tail lost to a cut-off write counts one."""

    def __init__(self, path: Path | str, calibration: Calibration | None = None):
        self.path = Path(path)
        self.calibration = calibration
        self.skipped = 0
        try:
            with _open_text(self.path, "rt") as fh:
                first = fh.readline()
        except (OSError, EOFError, zlib.error) as e:
            raise ValueError(f"{self.path}: not a gzip scenario file ({e})") from e
        try:
            self.header = check_header(json.loads(first))
        except ValueError as e:
            raise ValueError(f"{self.path}: no header: {e}") from e

    @property
    def cues(self) -> tuple[tuple[float, str], ...]:
        return tuple((float(t), text) for t, text in self.header["cues"])

    def _parse(self, line: str) -> Sensed | RawRecord:
        return decode(line, self.calibration) if self.header["type"] == "sensed" else decode_raw(line)

    def __iter__(self) -> Iterator[Sensed | RawRecord]:
        self.skipped = 0
        lineno = 1
        with _open_text(self.path, "rt") as fh:
            try:
                fh.readline()                                  # the header, checked when opened
                for lineno, line in enumerate(fh, 2):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = self._parse(line)
                    except BAD_LINE as e:
                        self.skipped += 1
                        log.warning("%s:%d skipped: %s: %s", self.path, lineno, type(e).__name__, e)
                        continue
                    yield record
            except (OSError, EOFError, zlib.error) as e:
                self.skipped += 1
                log.warning("%s: ends early after line %d (%s); the rest is lost", self.path, lineno, e)
