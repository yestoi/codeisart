"""`arcade record` (spec 6.3, 6.5, 9.5): the owner's scripted recordings, with consent, shown on the wall.

The recording runs a Runner with a RecordScene as its lobby and no games, so every frame it shows (3, 2, 1, then REC,
the seconds counter and the script's cue) passes the brightness limiter and the flash governor like any lobby's. The
scene writes the Sensed the runner gives it, once a tick, from "rec" on: a sensed file starts at t 0, the base of the
cue times in its header. Motion is dropped unless with_motion.

Raw (--raw, spec 6.3, 6.5): the scene writes no Sensed; it hands the camera's tap (MediaPipeCamera, on its source
thread) the writer while "rec" lasts, so the file holds rec's captures only, encoded by scenario.encode_raw (base64
and struct). Spec 6.5's rules hold before anything opens (refusal): consent always; on the colorlight backend only
with allow_record, and never raw; raw only from the mediapipe camera, the one source with a tap.
"""
from __future__ import annotations

import dataclasses
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import numpy as np

from arcade.canvas import Canvas, Color
from arcade.config import ArcadeConfig, load_config
from arcade.figure import draw_figure, figure_rect
from arcade.input import EPSILON
from arcade.juice import PLAYER_COLORS
from arcade.runner import Runner
from arcade.sensed import CAMERA_INPUTS, Body, Sensed
from arcade.sources import make_sources
from arcade.sources.scenario import ScenarioWriter, make_header
from show.font import CELL_H, Font

COUNTDOWN = 3                     # seconds of "3", "2", "1" before the recording; nothing is written
REC_COLOR = (255, 0, 0)           # "REC", top left
TEXT_COLOR = (255, 255, 255)      # the counter, the cue and the countdown
REC_XY = (1, 1)
CUE_Y = 28                        # the cue's rows: 28 to 35, at 1x
MARKER_ROWS = 4                   # rows 60 to 63 stay dark (the runner's marker)
MAX_CUE = 21                      # characters: 21 at 1x is 126 px of the wall's 128
ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class RecordScript:
    """A recording of spec 9.5: its name, its length in seconds and its cues, (t, text) from t 0, the first at 0."""

    name: str
    seconds: float
    cues: tuple[tuple[float, str], ...]


def _script(name: str, seconds: float, *cues: tuple[float, str]) -> RecordScript:
    return RecordScript(name, float(seconds), tuple((float(t), text) for t, text in cues))


RECORD_SCRIPTS: dict[str, RecordScript] = {s.name: s for s in (
    _script("empty-room", 30, (0, "STAY OUT OF VIEW"), (15, "TOGGLE THE ROOM LAMP"), (17, "STAY OUT OF VIEW")),
    _script("walk-in-stand-leave", 20, (0, "STAY OUT OF VIEW"), (3, "WALK IN"), (6, "STAND IN THE MIDDLE"),
            (14, "WALK OUT"), (17, "STAY OUT OF VIEW")),
    _script("door-point", 30, (0, "STAND IN THE MIDDLE"),
            (3, "POINT AT DOOR 1"), (4, "HOLD"), (6, "HAND DOWN"),
            (9, "POINT AT DOOR 2"), (10, "HOLD"), (12, "HAND DOWN"),
            (15, "POINT AT DOOR 3"), (16, "HOLD"), (18, "HAND DOWN"),
            (21, "SWEEP, DON'T STOP"), (27, "HAND DOWN")),
    _script("wrist-sweep", 20, (0, "STAND IN THE MIDDLE"), (2, "SWEEP SLOWLY"), (8, "SWEEP FAST"),
            (13, "LEAN AND SWEEP"), (18, "HAND DOWN")),
    _script("exit-gesture", 15, (0, "STAND IN THE MIDDLE"),
            (1, "HANDS UP, BRIEFLY"), (2, "HANDS DOWN"), (3.5, "HANDS UP, BRIEFLY"), (4.5, "HANDS DOWN"),
            (6, "HANDS UP, BRIEFLY"), (7, "HANDS DOWN"), (9, "BOTH HANDS UP, HOLD"), (13, "HANDS DOWN")),
    _script("jumps-squats", 20, (0, "STAND STILL"), (2, "JUMP 1"), (4, "JUMP 2"), (6, "JUMP 3"),
            (8, "STAND STILL"), (10, "SQUAT 1"), (12, "SQUAT 2"), (14, "SQUAT 3"), (16, "STAND STILL")),
    _script("poses-8", 40, (0, "STAND, ARMS DOWN"), (2, "ARMS UP"), (6, "T POSE"), (10, "RIGHT ARM UP"),
            (14, "LEFT ARM UP"), (18, "Y POSE"), (22, "FLEX"), (26, "AIRPLANE"), (30, "DISCO"),
            (34, "ARMS DOWN")),
    _script("torch-paint", 30, (0, "ROOM DARK, TORCH OFF"), (3, "TORCH ON"), (5, "PAINT A CIRCLE"),
            (12, "PAINT A ZIGZAG"), (19, "HOLD THE TORCH STILL"), (24, "TORCH OFF")),
    _script("idle-still", 20, (0, "STAND STILL"), (10, "KEEP STILL")),
    _script("claps-tempo-voice", 30, (0, "QUIET"), (3, "CLAP 4 TIMES"), (8, "CLAP ON A STEADY BEAT"),
            (16, "QUIET"), (19, "TALK OR SING"), (26, "QUIET")),
    _script("music-speaker", 30, (0, "QUIET"), (3, "PLAY A 125 BPM TRACK"), (27, "STOP THE TRACK")),
    _script("two-people-cross", 30, (0, "BOTH STAND APART"), (5, "WALK ACROSS, SWAP"), (10, "STAND STILL"),
            (15, "CROSS BACK"), (20, "STAND STILL"), (25, "BOTH WALK OUT")),
)}


def refusal(cfg: ArcadeConfig, *, consent: bool, raw: bool) -> str | None:
    """Why spec 6.5 refuses this recording, or None. It reads cfg only: no source need be open."""
    if not consent:
        return "recording needs --i-have-consent: everyone in view has agreed to be recorded"
    if cfg.backend == "colorlight" and not cfg.allow_record:
        return "the colorlight backend records only with allow_record = true in the config"
    if raw and cfg.backend == "colorlight":
        return "--raw is never recorded on the colorlight backend"
    if raw and cfg.camera != "mediapipe":
        return f'--raw needs camera = "mediapipe" (the only source with raw captures), not {cfg.camera!r}'
    return None


class RecordScene:
    """The recording as the runner's lobby (LobbyLike): "countdown" for COUNTDOWN s, then "rec" for script.seconds,
    then "end" (done). In "rec" it writes each tick's Sensed with t and camera_t from rec's start and motion empty
    unless with_motion; with raw_camera it writes nothing itself, and the camera's tap holds writer.write from the
    tick rec starts to the tick it ends."""

    info = None

    def __init__(self, script: RecordScript, writer, *, with_motion: bool, raw_camera=None):
        self.script, self.writer, self.with_motion, self.raw_camera = script, writer, with_motion, raw_camera
        self.request: str | None = None
        self.reset((128, 64), None)

    def reset(self, size, rng, fx=None) -> None:
        self.size = size
        self.phase = "countdown"
        self.written = 0
        self.bodies: tuple[Body, ...] = ()
        self._first: float | None = None      # the first tick's t: the countdown's base
        self._start = 0.0                     # rec's first tick's t: the file's t 0
        self._elapsed = 0.0                   # seconds since the countdown began, or since rec began in "rec"

    def update(self, sensed: Sensed, dt: float) -> None:
        t = sensed.t
        if self._first is None:
            self._first = t
        self.bodies = sensed.bodies
        if self.phase == "countdown":
            self._elapsed = t - self._first
            if self._elapsed < COUNTDOWN - EPSILON:
                return
            self.phase, self._start = "rec", t
            if self.raw_camera is not None:
                self.raw_camera.tap = self.writer.write
        if self.phase != "rec":
            return
        self._elapsed = t - self._start
        if self._elapsed >= self.script.seconds - EPSILON:
            self.phase = "end"
            if self.raw_camera is not None:
                self.raw_camera.tap = None
            return
        if self.raw_camera is None:
            motion = sensed.motion if self.with_motion else np.zeros((0, 0), bool)
            self.writer.write(dataclasses.replace(sensed, t=t - self._start, camera_t=sensed.camera_t - self._start,
                                                  motion=motion))
            self.written += 1

    @property
    def seconds(self) -> int:
        """The whole seconds recorded."""
        if self.phase == "countdown":
            return 0
        return int(min(self._elapsed, self.script.seconds) + EPSILON)

    @property
    def cue(self) -> str | None:
        """In "rec", the last cue whose time has passed."""
        if self.phase != "rec":
            return None
        passed = [text for at, text in self.script.cues if at <= self._elapsed + EPSILON]
        return passed[-1] if passed else None

    def draw(self, canvas: Canvas) -> None:
        """The bodies as figures, rows 60 to 63 black, then each text over a black box with a 1 px gutter."""
        size = canvas.size
        for i, body in enumerate(self.bodies):
            draw_figure(canvas, body, figure_rect(body, size), PLAYER_COLORS[i % len(PLAYER_COLORS)])
        canvas.fill_rect(0, canvas.height - MARKER_ROWS, canvas.width, MARKER_ROWS, (0, 0, 0))
        if self.phase == "countdown":
            digit = str(COUNTDOWN - int(self._elapsed + EPSILON))
            _label(canvas, (canvas.width - canvas.text_width(digit, 2)) // 2, (canvas.height - 2 * CELL_H) // 2,
                   digit, TEXT_COLOR, 2)
        elif self.phase == "rec":
            x, y = REC_XY
            _label(canvas, x, y, "REC", REC_COLOR)
            _label(canvas, x + canvas.text_width("REC "), y, f"{self.seconds}S", TEXT_COLOR)
            cue = self.cue
            if cue is not None:
                _label(canvas, (canvas.width - canvas.text_width(cue)) // 2, CUE_Y, cue, TEXT_COLOR)

    def done(self) -> bool:
        return self.phase == "end"

    def debug_state(self) -> dict:
        return {"phase": self.phase, "seconds": self.seconds, "cue": self.cue, "written": self.written}

    def set_available(self, names) -> None:
        pass

    def set_status(self, camera_ok, mic_ok, inputs, calibrated) -> None:
        pass

    def end_session(self, result) -> None:
        pass


def _label(canvas: Canvas, x: int, y: int, text: str, color: Color, scale: int = 1) -> None:
    """text at (x, y) over a black box one pixel wider than its cells all round: feel.find_text's dark gutter."""
    canvas.fill_rect(x - 1, y - 1, canvas.text_width(text, scale) + 2, CELL_H * scale + 2, (0, 0, 0))
    canvas.text(x, y, text, color, scale)


class _Counted:
    """A writer whose write counts the records it passes on: a raw file's records come from the camera's tap."""

    def __init__(self, writer):
        self._writer, self.count = writer, 0

    def write(self, record) -> None:
        self._writer.write(record)
        self.count += 1


def git_sha() -> str | None:
    """This checkout's short sha, None when there is none (no git, not a checkout)."""
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                             timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    sha = out.stdout.strip()
    return sha if out.returncode == 0 and sha else None


def record(cfg: ArcadeConfig, script: RecordScript, camera, audio, display, font: Font, out: Path | str, *,
           raw: bool = False, with_motion: bool = False, clock: Callable[[], float] = time.monotonic,
           sleep: Callable[[float], None] = time.sleep) -> int:
    """Record script to out from camera and audio, showing it on display; the records written. The header holds
    the script, its cues, the git sha and inputs (sorted): the camera's provides (every camera input without one)
    less motion unless with_motion; raw: motion and pose, and cfg.mirror. However it ends, the tap is cleared, then
    the camera closed (its thread joined), then the writer: a raise comes out after."""
    header = make_header("raw" if raw else "sensed", fps=cfg.camera_fps if raw else cfg.fps, script=script.name,
                         cues=script.cues, git=git_sha())
    if raw:
        header["inputs"], header["mirror"] = ["motion", "pose"], bool(cfg.mirror)
    else:
        provides = frozenset(getattr(camera, "provides", CAMERA_INPUTS)) & CAMERA_INPUTS
        header["inputs"] = sorted(provides if with_motion else provides - {"motion"})
    writer = None
    try:
        writer = ScenarioWriter(out, header)
        counted = _Counted(writer)
        scene = RecordScene(script, counted if raw else writer, with_motion=with_motion,
                            raw_camera=camera if raw else None)
        runner = Runner(cfg, display, font, scene, [], clock=clock, sleep=sleep, strict=True)
        runner.loop(camera, audio, until=scene.done)
    finally:
        try:
            if raw:
                camera.tap = None
            camera.close()
        finally:
            if writer is not None:
                writer.close()
    return counted.count if raw else scene.written         # after the join: a capture in flight is counted


def default_out(cfg: ArcadeConfig, script: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return Path(cfg.data_dir) / "recordings" / f"{script}-{stamp}.jsonl.gz"


def main(args) -> int:
    """`arcade record`: args.config, args.script (a RECORD_SCRIPTS name), args.i_have_consent, args.raw,
    args.with_motion, args.out (default data_dir/recordings/<script>-<UTC time>.jsonl.gz). A refusal or an unknown
    script prints why and returns 2 before any source or display opens; else 0 once recorded, the path printed."""
    cfg = load_config(args.config)
    why = refusal(cfg, consent=args.i_have_consent, raw=args.raw)
    if why is None and args.script not in RECORD_SCRIPTS:
        why = f"unknown script {args.script!r}; known: {', '.join(RECORD_SCRIPTS)}"
    if why is not None:
        print(f"record refused: {why}")
        return 2
    script = RECORD_SCRIPTS[args.script]
    out = Path(args.out) if args.out else default_out(cfg, script.name)
    font = Font.load(Path(cfg.font_path))
    camera, audio = make_sources(cfg, cfg.size)                     # the main thread: macOS asks for the camera here
    try:
        from arcade.main import build_display                       # here: arcade.main dispatches to this module
        display = build_display(cfg)
        try:
            n = record(cfg, script, camera, audio, display, font, out, raw=args.raw, with_motion=args.with_motion)
        finally:
            display.close()
        print(f"recorded {n} records of {script.name} to {out}")
        return 0
    finally:
        for source in (camera, audio):
            source.close()
