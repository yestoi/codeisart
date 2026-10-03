"""Arcade command line: `run` (the default), `doctor`, `calibrate`, `record` and `stats` (the last three in their
own modules, imported only when their command runs)."""
from __future__ import annotations

import argparse
import importlib.metadata
import logging
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, TextIO

from arcade.attract.lobby import Lobby
from arcade.calibration import load_calibration
from arcade.config import CAMERAS, CAPTURES, ArcadeConfig, load_config
from arcade.games import all_games
from arcade.preview import PreviewDisplay
from arcade.runner import Runner
from arcade.scores import Scores, SessionLog
from arcade.sources import SCRIPTS, make_sources
from show.display import Display, make_display
from show.display.colorlight import stats_line
from show.font import Font

COMMANDS = ("run", "doctor", "calibrate", "record", "stats")
MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "pose_landmarker_lite.task"
TIMEOUT = 5.0
UPLOAD_WAIT = 300.0           # s the imx500 probe waits for the first tensor once frames flow without one: the
UPLOAD_NOTICE_AFTER = 3.0     # sensor is taking the network (2 MB at about 9 kB/s, 3 to 4 min); the notice after 3 s
Probe = Callable[[float], tuple[bool, str]]
log = logging.getLogger(__name__)


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


def probe_imx500(timeout: float, upload_wait: float = UPLOAD_WAIT) -> tuple[bool, str]:
    """The AI Camera with posenet on its sensor (camera "imx500"), opened as the arcade opens it: (True, the model,
    its rate and the frame size) at the first frame that carries a tensor. Frames without one past
    UPLOAD_NOTICE_AFTER mean the network is uploading: it says so, prints the wait every 30 s, and waits up to
    upload_wait instead of timeout (^C ends it). The camera index is the IMX500 object's, not --camera-index."""
    from arcade.config import ArcadeConfig
    from arcade.sources import pose_imx500

    cfg = ArcadeConfig(camera="imx500")           # index is unused: the IMX500 object picks its own camera number
    try:
        capture, detector = pose_imx500.open_imx500(cfg, cfg.size)
    except Exception as e:
        return False, f"imx500: {type(e).__name__}: {e} (apt: imx500-all python3-picamera2; the ribbon seated)"
    label = f"imx500 {pose_imx500.describe(detector.imx)}"
    frames, start = 0, time.monotonic()
    deadline, notified, told = start + timeout, False, start
    try:
        while time.monotonic() < deadline:
            ok, frame = capture.read()
            if not ok or frame is None:
                time.sleep(0.05)
                continue
            frames += 1
            if capture.metadata.get("CnnOutputTensor"):
                return True, f"{label}: {frame.shape[1]}x{frame.shape[0]}"
            now = time.monotonic()
            if not notified and now - start >= UPLOAD_NOTICE_AFTER:
                notified, told = True, now
                deadline = start + upload_wait
                print("imx500: frames but no tensor yet: uploading the network to the sensor, up to 4 minutes "
                      "(^C stops the wait)", file=sys.stdout, flush=True)   # CLI output, as the doctor's lines
            elif notified and now - told >= 30.0:
                told = now
                print(f"imx500: still waiting, {now - start:.0f} s", file=sys.stdout, flush=True)
        why = f"{frames} frames, no tensor in {time.monotonic() - start:.0f} s" if frames else f"no frames in {timeout:.0f} s"
        return False, f"{label}: {why} (is posenet on the sensor: another network means a new upload)"
    finally:
        capture.release()


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


def make_probes(camera_index: int = 0, audio_device: str = "", model: Path = MODEL_PATH,
                capture: str = "opencv", camera: str = "mediapipe") -> dict[str, Probe]:
    """The doctor's probes by name. camera "imx500" is one probe for both the camera and the pose (the sensor runs
    the model); otherwise the camera's probe is the one capture names and the pose's is MediaPipe's. The probe
    functions are looked up when a probe runs."""
    if camera == "imx500":
        done: dict[str, tuple[bool, str]] = {}

        def imx(t: float) -> tuple[bool, str]:        # one opening of the camera serves both names
            if "result" not in done:
                done["result"] = probe_imx500(t)
            return done["result"]

        return {"camera": imx, "mic": lambda t: probe_mic(t, audio_device), "pose": imx}
    return {"camera": lambda t: (probe_picamera2 if capture == "picamera2" else probe_camera)(t, camera_index),
            "mic": lambda t: probe_mic(t, audio_device),
            "pose": lambda t: probe_pose(t, Path(model))}


def _names(text: str) -> list[str]:
    return [n.strip() for n in text.split(",") if n.strip()]


def build_display(cfg: ArcadeConfig) -> Display:
    """sdl: a window of the wall at sdl_scale, rendered in cfg.look by PreviewDisplay (the SDL display itself at
    scale 1, since the preview has already scaled). Any other backend: show.display.make_display."""
    if cfg.backend == "sdl":
        from show.display.sdl import SDLDisplay
        inner = SDLDisplay(cfg.width * cfg.sdl_scale, cfg.height * cfg.sdl_scale, 1)
        return PreviewDisplay(inner, cfg.look, cfg.sdl_scale, cfg.gamma)
    return make_display(cfg)


def run(args) -> int:
    """The arcade: the small lobby and every game, until --seconds pass, the window closes or ^C. --require runs the
    doctor on those sources first and stops with its code when one fails (Q145); --replay plays a scenario file.
    --game offers that one game only: a player standing in the zone for 2 s starts it; with --leave-after SECONDS the
    run ends once the zone has been empty that long, three times that before the first game (Runner.left); with --once
    it ends when the first game has ended (one playthrough), either rule ending it when both are given."""
    cfg = load_config(args.config)
    log.info("wall %s, backend %s", cfg.layout, cfg.backend)
    games = all_games()
    if args.game is not None:
        names = [game.info.name for game in games]
        if args.game not in names:
            print(f"run: unknown game {args.game!r}; known: {', '.join(names)}")   # CLI output, as the doctor's
            return 2
        games = [game for game in games if game.info.name == args.game]
    if _names(args.require):
        code = doctor(_names(args.require), make_probes(cfg.camera_index, cfg.audio_device, capture=cfg.capture,
                                                        camera=cfg.camera), TIMEOUT)
        if code:
            return code
    data_dir = Path(cfg.data_dir)
    calibration = load_calibration(data_dir)
    camera, audio = make_sources(cfg, cfg.size, script=args.script, calibration=calibration,   # main thread
                                 replay=args.replay)
    try:
        font = Font.load(Path(cfg.font_path))
        display = build_display(cfg)
        try:
            runner = Runner(cfg, display, font, Lobby(games, cfg, start_on_step_in=args.game is not None), games,
                            scores=Scores(data_dir / "scores.json"), sessions=SessionLog(data_dir / "sessions.jsonl"),
                            calibration=calibration, local_clock=datetime.now, lux=None)
            max_ticks = None if args.seconds is None else round(args.seconds * cfg.fps)
            leave, once = args.leave_after, args.once
            until = None if leave is None and not once else \
                (lambda: (leave is not None and runner.left(leave)) or (once and runner.ended >= 1))
            runner.loop(camera, audio, max_ticks=max_ticks, until=until)
        except KeyboardInterrupt:
            pass
        finally:
            line = stats_line(display)
            if line:
                log.info(line)
            display.close()
        return 0
    finally:
        for source in (camera, audio):
            source.close()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="arcade", description="Wall arcade")
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run", help="run the arcade (the default command)")
    r.add_argument("--config", default="arcade.toml", help="the flat config; a missing file means the defaults")
    r.add_argument("--seconds", type=float, help="stop after this many seconds of ticks (seconds * fps)")
    played = r.add_mutually_exclusive_group()
    played.add_argument("--script", choices=sorted(SCRIPTS), help="play a scripted camera instead of cfg.camera")
    played.add_argument("--replay", metavar="PATH", help="play a scenario file instead of cfg.camera")
    r.add_argument("--require", default="", help="comma list of camera, mic, pose: the doctor checks them first")
    r.add_argument("--game", metavar="NAME", help="offer only this game: a player standing in the zone for 2 s starts it")
    r.add_argument("--leave-after", type=float, metavar="SECONDS",
                   help="with --game: stop once the zone has been empty this long (three times this before the first game)")
    r.add_argument("--once", action="store_true", help="with --game: stop when the first game has ended")
    r.add_argument("-v", "--verbose", action="store_true")
    d = sub.add_parser("doctor", help="exit 1 if a required source is unavailable after the timeout")
    d.add_argument("--require", default="camera,mic,pose", help="comma list of camera, mic, pose")
    d.add_argument("--timeout", type=float, default=TIMEOUT)
    d.add_argument("--camera-index", type=int, default=0)
    d.add_argument("--capture", choices=CAPTURES, default="opencv", help="picamera2: the Pi's ribbon cameras")
    d.add_argument("--camera", choices=CAMERAS, default="mediapipe", help="imx500: posenet on the AI Camera's sensor")
    d.add_argument("--audio-device", default="")
    d.add_argument("--model", default=str(MODEL_PATH))
    c = sub.add_parser("calibrate", help="find the play zone with one person; writes data_dir/calibration.json")
    c.add_argument("--config", default="arcade.toml")
    from arcade.sources.record import RECORD_SCRIPTS   # here: only the parser needs the names
    rec = sub.add_parser("record", help="record a scenario file of one script (spec 9.5), with consent")
    rec.add_argument("--config", default="arcade.toml")
    rec.add_argument("--script", required=True, choices=sorted(RECORD_SCRIPTS))
    rec.add_argument("--i-have-consent", action="store_true", help="everyone in view agreed to be recorded")
    rec.add_argument("--raw", action="store_true", help="grey frames and detections (the mediapipe camera only)")
    rec.add_argument("--with-motion", action="store_true", help="keep the motion grid in a sensed file")
    rec.add_argument("--out", help="the file; default data_dir/recordings/<script>-<UTC time>.jsonl.gz")
    s = sub.add_parser("stats", help="sessions per game, their median length and how they ended")
    s.add_argument("--config", default="arcade.toml")
    s.add_argument("--sessions", help="the sessions log; default data_dir/sessions.jsonl")
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or (argv[0] not in COMMANDS and argv[0] not in ("-h", "--help")):
        argv.insert(0, "run")                     # run is the default command
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        return doctor(_names(args.require),
                      make_probes(args.camera_index, args.audio_device, Path(args.model), args.capture, args.camera),
                      args.timeout)
    logging.basicConfig(level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if args.command == "record":
        from arcade.sources.record import main as record_main
        return record_main(args)
    if args.command == "calibrate":
        from arcade.calibrate import main as calibrate_main
        return calibrate_main(args)
    if args.command == "stats":
        from arcade.stats import main as stats_main
        return stats_main(args)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
