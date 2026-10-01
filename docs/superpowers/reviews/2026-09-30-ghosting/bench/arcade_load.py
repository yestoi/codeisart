"""Bench (2026-09-30, not part of the repo): the colorlight driver under the arcade itself, on the Pi 5.

The arcade as arcade.main.run builds it: the lobby, every game, the runner's loop at cfg.fps, the governor. Its
camera is the real MediaPipeCamera (the pose model, in its own thread of this process), fed a still photograph of
a person 30 times a second in place of a USB camera. Its display is the colorlight driver on a socket that
discards, or with --wall the card on cfg.iface.

    cd ~/codeisart && sudo .venv/bin/python ~/bench/arcade_load.py --seconds 120
    ... --camera-fps 30      # inference three times as often as arcade.toml asks
    ... --no-camera          # the arcade alone: the base line
    ... --wall               # the card, at --brightness (0.1)
"""
import argparse
import logging
import re
import statistics
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

REPO = Path("/home/trey/codeisart")
sys.path.insert(0, str(REPO))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from arcade.attract.lobby import Lobby  # noqa: E402
from arcade.calibration import load_calibration  # noqa: E402
from arcade.config import load_config  # noqa: E402
from arcade.games import all_games  # noqa: E402
from arcade.runner import Runner  # noqa: E402
from arcade.scores import Scores, SessionLog  # noqa: E402
from arcade.sources import NoSource  # noqa: E402
from arcade.sources import pose_mediapipe  # noqa: E402
from show.display import make_display  # noqa: E402
from show.display.colorlight import stats_line  # noqa: E402
from show.font import Font  # noqa: E402
from tools.wall_pattern import dry_display  # noqa: E402


class StillCapture:
    """cv2.VideoCapture's read() and release(): one picture, a frame due every 1/fps, as a camera blocks."""

    def __init__(self, bgr, fps=30.0):
        self.frame, self.period, self.due = bgr, 1.0 / fps, time.monotonic()

    def read(self):
        wait = self.due - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self.due = max(self.due, time.monotonic() - self.period) + self.period
        return True, self.frame

    def release(self):
        pass


def summary(ms):
    ms = np.asarray(ms) * 1000
    return f"median {np.median(ms):.1f}, p95 {np.percentile(ms, 95):.1f}, max {ms.max():.1f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--camera-fps", type=int)
    ap.add_argument("--no-camera", action="store_true")
    ap.add_argument("--wall", action="store_true")
    ap.add_argument("--brightness", type=float, default=0.1)
    ap.add_argument("--png", help="save the last frame pushed to the display here, 8 times its size")
    ap.add_argument("--picture", default=str(Path(__file__).resolve().parent / "person.jpg"))
    args = ap.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    tmp = Path(tempfile.mkdtemp(prefix="arcade-load-"))
    text = (REPO / "arcade.toml").read_text()
    for key, value in (("backend", '"colorlight"'), ("brightness", f"{args.brightness}"),
                       ("data_dir", f'"{tmp}"'), ("font_path", f'"{REPO / "fonts" / "5x7.bin"}"')):
        text, n = re.subn(rf"(?m)^{key} = \S+", f"{key} = {value}", text)
        assert n == 1, key
    if args.camera_fps:
        text = re.sub(r"(?m)^camera_fps = \S+", f"camera_fps = {args.camera_fps}", text)
    (tmp / "arcade.toml").write_text(text)
    cfg = load_config(tmp / "arcade.toml")

    infer, found = [], []
    detect = pose_mediapipe.Landmarker.detect

    def timed_detect(self, rgb, ts_ms):
        start = time.perf_counter()
        out = detect(self, rgb, ts_ms)
        infer.append(time.perf_counter() - start)
        found.append(len(out))
        return out

    pose_mediapipe.Landmarker.detect = timed_detect
    starts, spent = [], []
    tick = Runner.tick

    def timed_tick(self, sensed, dt):
        start = time.perf_counter()
        out = tick(self, sensed, dt)
        starts.append(start)
        spent.append(time.perf_counter() - start)
        return out

    Runner.tick = timed_tick

    calibration = load_calibration(tmp)
    if args.no_camera:
        camera = NoSource()
    else:
        picture = cv2.imread(args.picture)
        assert picture is not None, args.picture
        picture = cv2.resize(picture, pose_mediapipe.CAPTURE_SIZE)
        camera = pose_mediapipe.MediaPipeCamera(cfg, cfg.size, calibration=calibration,
                                                capture=StillCapture(picture))
    display = make_display(cfg) if args.wall else dry_display(cfg.width, cfg.height, cfg.brightness)
    kept, push = {}, display.push

    def keeping_push(frame):
        kept["frame"] = np.array(frame, copy=True)
        kept.setdefault("all", []).append(kept["frame"])
        del kept["all"][:-150]                     # the last five seconds
        return push(frame)

    display.push = keeping_push
    line, cpu0, wall0 = None, time.process_time(), time.perf_counter()
    try:
        games = all_games()
        runner = Runner(cfg, display, Font.load(Path(cfg.font_path)), Lobby(games, cfg), games,
                        scores=Scores(tmp / "scores.json"), sessions=SessionLog(tmp / "sessions.jsonl"),
                        calibration=calibration, local_clock=datetime.now, lux=None)
        try:
            runner.loop(camera, NoSource(), max_ticks=round(args.seconds * cfg.fps))
        except KeyboardInterrupt:
            pass
        cpu, wall = time.process_time() - cpu0, time.perf_counter() - wall0
        line = stats_line(display)
        seen = camera.latest()
        bodies = None if seen is None else len(seen[1])
    finally:
        display.close()
        camera.close()

    gaps = np.diff(starts)
    late = int((gaps > 1.5 / cfg.fps).sum())
    what = "no camera" if args.no_camera else f"mediapipe at {cfg.camera_fps} a second"
    print(f"arcade, {what}, {'the wall' if args.wall else 'dry'}, {wall:.0f} s:")
    print(f"  ticks: {len(starts)}, {len(gaps) / (starts[-1] - starts[0]):.2f} a second, {late} late (a gap over "
          f"{1500 / cfg.fps:.0f} ms); a tick ms: {summary(spent)}; tick to tick ms: {summary(gaps)}")
    if infer:
        people = statistics.median(found)
        print(f"  pose: {len(infer)} inferences, {len(infer) / wall:.1f} a second, ms: {summary(infer)}; "
              f"people found (median) {people:g}")
    print(f"  this process: {100 * cpu / wall:.0f} % of one core")
    try:
        state = runner.state()
        print("  the runner at the end:", {k: state[k] for k in ("mode", "game", "players") if k in state})
    except Exception as e:                      # a line for the report, never a failure
        print(f"  the runner's state: {e!r}")
    print("  " + (line or "no sender stats"))
    print(f"  bodies the tracker held at the end: {bodies}")
    if args.png and "frame" in kept:
        big = np.repeat(np.repeat(kept["frame"], 8, axis=0), 8, axis=1)
        cv2.imwrite(args.png, big[:, :, ::-1])
        print(f"  the last frame pushed: {args.png}")
        frames = np.stack(kept["all"])
        distinct = len({f.tobytes() for f in frames})
        lit = frames.max(axis=3) > 0
        share = lit.mean(axis=0)                   # how often each pixel was lit in the last five seconds
        print(f"  the last {len(frames)} frames pushed: {distinct} distinct; pixels lit in every one "
              f"{int((share == 1).sum())}, lit in some only {int(((share > 0) & (share < 1)).sum())}; "
              f"levels seen {sorted(set(np.unique(frames).tolist()))[:12]}")
        heat = np.zeros(frames.shape[1:], np.uint8)
        heat[..., 1] = (share == 1) * 255          # green: always lit
        heat[..., 0] = ((share > 0) & (share < 1)) * (80 + 175 * share).astype(np.uint8)   # red: sometimes
        path = args.png.replace(".png", "-often.png")
        cv2.imwrite(path, np.repeat(np.repeat(heat, 8, axis=0), 8, axis=1)[:, :, ::-1])
        path = args.png.replace(".png", "-max.png")
        cv2.imwrite(path, np.repeat(np.repeat(frames.max(axis=0), 8, axis=0), 8, axis=1)[:, :, ::-1])


if __name__ == "__main__":
    main()
