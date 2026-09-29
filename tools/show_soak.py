"""The soak: a real ShowLoop on fakes for minutes to hours, watched, never fed (spec 4.7; it13 T-soak).

    python -m tools.show_soak --minutes 5 --press-every 5 --out data/soak
    python -m tools.show_soak --config show.poc.toml --minutes 2 --press-every 5 --out data/soak

The loop makes and governs its display and steps in real time; the soak presses a station every --press-every
seconds, and watches `wall.last` (a FlashMeter on each new governed frame), `wall.failed`, the `show` logger's
errors, the step's and the governor's cost, open files, memory and children. It sends nothing to a display.
The report is <out>/soak-<stamp>.json; the exit is 0 clear, 1 with must-be-zero counts that are not (printed),
2 for bad arguments. Without --real-devices the lights and the audio are fakes and no button is read.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import os
import random
import resource
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Callable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:          # run as a script, the repository is not on the path
    sys.path.insert(0, str(ROOT))

from arcade.flash import BUDGET                                                   # noqa: E402
from show.audio import FakeAudio                                                  # noqa: E402
from show.config import Config, load_config                                       # noqa: E402
from show.lights import FakeLights                                                # noqa: E402
from show.main import ShowLoop, sigterm_raises                                    # noqa: E402
from show.pipeline import EntryPlayer                                             # noqa: E402
from tools.arcade_shot import git_sha                                             # noqa: E402
from tools.flash_meter import FlashMeter                                          # noqa: E402

PRESS_EVERY_S = 180.0   # the core plan's week 5: a press every 3 minutes
WINDOW_S = 60.0         # a report row this often: frames, meter maxima, held, fds, rss
STATIONS = (1, 2, 3, 4, 5, 6)   # 1 to 5 may be empty (Q62); 6 is hello; the rng repeats some
BACKENDS = ("fake", "sdl", "colorlight", "ddp")
BIN_MS, BINS = 0.1, 10000       # the timing histograms: 0.1 ms bins up to 1 s, the last bin holds the rest
EPS = 1e-9                      # a float clock's rounding, in seconds
MAX_ERRORS_KEPT = 20


class SoakOver(KeyboardInterrupt):
    """Raised by the step wrapper when the time is up, so run's finally closes as a stop does."""


class Timings:
    """Durations in ms in a fixed histogram: median and p95 to a bin, the worst exactly."""

    def __init__(self) -> None:
        self.bins = np.zeros(BINS, np.int64)
        self.worst = 0.0

    def add(self, ms: float) -> None:
        self.bins[min(BINS - 1, max(0, int(ms / BIN_MS)))] += 1
        self.worst = max(self.worst, ms)

    def summary(self) -> dict:
        total = int(self.bins.sum())
        if total == 0:
            return {"count": 0, "median": 0.0, "p95": 0.0, "worst": 0.0}
        cum = np.cumsum(self.bins)
        at = lambda q: round(float(np.searchsorted(cum, q * total)) * BIN_MS, 1)   # noqa: E731
        return {"count": total, "median": at(0.5), "p95": at(0.95), "worst": round(self.worst, 3)}


class ErrorLog(logging.Handler):
    """ERROR and over on the `show` logger: counted, the first MAX_ERRORS_KEPT kept; before the first step they
    are setup's."""

    def __init__(self) -> None:
        super().__init__(logging.ERROR)
        self.stepping, self.setup, self.after, self.kept = False, 0, 0, []

    def emit(self, record: logging.LogRecord) -> None:
        if not self.stepping:
            self.setup += 1
        else:
            self.after += 1
        if len(self.kept) < MAX_ERRORS_KEPT:
            self.kept.append(f"{record.name}: {record.getMessage()}")


def open_fds() -> int:
    for path in ("/proc/self/fd", "/dev/fd"):
        try:
            return len(os.listdir(path))
        except OSError:
            continue
    return -1


def peak_rss_kb() -> int:
    """The process's peak resident set (ru_maxrss is bytes on macOS, KiB on Linux)."""
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak // 1024 if sys.platform == "darwin" else peak


def children_of_this_process() -> int:
    try:
        out = subprocess.run(["pgrep", "-P", str(os.getpid())], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return 0
    return len(out.split())


def rooted(cfg: Config) -> Config:
    """Relative paths resolved against the repository root, as show_shot does."""
    return replace(cfg, **{name: (ROOT / p if not p.is_absolute() else p) for name in
                           ("entries_dir", "audio_dir", "font_path") for p in [getattr(cfg, name)]})


def soak(cfg: Config, minutes: float, press_every: float = PRESS_EVERY_S, *, seed=0, stations=STATIONS,
         window_s=WINDOW_S, real_devices=False, display=None, player_factory=EntryPlayer, clock=time.monotonic,
         sleep=time.sleep, perf=time.perf_counter) -> dict:
    """Run the show for `minutes` (by `clock`), pressing a station chosen by the seed every `press_every`; the
    report. The loop makes and governs its display (`display` is only handed to it, for tests)."""
    if not minutes > 0 or not press_every > 0 or not window_s > 0:
        raise ValueError("minutes, press_every and window_s must be over 0")
    cfg = rooted(cfg)
    duration, rng = minutes * 60.0, random.Random(seed)
    counts = {"plays_started": 0, "plays_ended": 0}

    def make_player(entry, term, config):
        player = player_factory(entry, term, config)
        counts["plays_started"] += 1
        stop, stopped = player.stop, []

        def counted_stop():
            if not stopped:
                stopped.append(True)
                counts["plays_ended"] += 1
            return stop()

        player.stop = counted_stop
        return player

    loop = ShowLoop(cfg, display=display, player_factory=make_player, notify=lambda state: None,
                    rng=random.Random(seed))
    loop.clock, loop.sleep = clock, sleep
    if not real_devices:
        loop._devices = True                       # no GPIO, button or sound device: fakes
        loop.lights, loop.audio = FakeLights(), FakeAudio()
    errors, step_ms, governor_ms = ErrorLog(), Timings(), Timings()
    state = {"steps": 0, "presses": 0, "returns": 0, "seen": 0, "meter": None, "meter_frames": 0,
             "finished": False, "was_playing": False, "next_press": None, "start": None, "window_start": None}
    windows: list[dict] = []
    final: dict = {}
    first = {"fds": open_fds(), "rss_kb": peak_rss_kb()}

    def close_window(now: float) -> None:
        wall, meter = loop.wall, state["meter"]
        area, squares = meter.take() if meter is not None else (0.0, 0)
        windows.append({"t": round(now - state["start"], 3), "steps": state["steps"],
                        "governed": wall.governed if wall is not None else 0,
                        "frames": state["meter_frames"], "area_max": round(area, 6), "squares_max": squares,
                        "held_ticks": wall.governor.held_ticks if wall is not None else 0,
                        "fds": open_fds(), "rss_kb": peak_rss_kb()})
        state["meter_frames"] = 0
        state["window_start"] = now

    def watch_wall() -> None:
        wall = loop.wall
        if wall is None or state["meter"] is not None:
            return
        state["meter"] = FlashMeter(wall.governor.fps, wall.governor.gamma)
        apply = wall.governor.apply

        def timed_apply(frame):
            t = perf()
            try:
                return apply(frame)
            finally:
                governor_ms.add((perf() - t) * 1000.0)

        wall.governor.apply = timed_apply

    real_step = loop.step

    def step(now: float) -> None:
        if state["start"] is None:
            state["start"] = state["window_start"] = state["next_press"] = now
            errors.stepping = True
        if now - state["start"] >= duration - EPS:
            state["finished"] = True
            final.update(counts, returns=state["returns"], steps=state["steps"])
            raise SoakOver
        if now + EPS >= state["next_press"]:
            loop.presses.put(rng.choice(stations))
            state["presses"] += 1
            state["next_press"] += press_every
        watch_wall()
        t = perf()
        real_step(now)
        step_ms.add((perf() - t) * 1000.0)         # the meter's time below is kept out of it
        state["steps"] += 1
        wall = loop.wall
        if wall is not None and wall.governed != state["seen"]:
            state["seen"] = wall.governed
            if wall.last is not None:
                state["meter"].add(wall.last)
                state["meter_frames"] += 1
        playing = loop.show is not None and loop.show.playing
        if state["was_playing"] and not playing:
            state["returns"] += 1
        state["was_playing"] = playing
        if now - state["window_start"] >= window_s - EPS:
            close_window(now)

    loop.step = step
    root = logging.getLogger("show")
    root.addHandler(errors)
    started_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    t_begin = clock()
    try:
        loop.run()
    finally:
        root.removeHandler(errors)
    if state["start"] is not None and state["meter_frames"]:
        close_window(clock())
    elapsed = clock() - t_begin
    wall, meter = loop.wall, state["meter"]
    counts.update(final)
    return {
        "steps": state["steps"], "governed": wall.governed if wall is not None else 0,
        "push_failures": wall.failed if wall is not None else 0,
        "held_ticks": wall.governor.held_ticks if wall is not None else 0,
        "presses": state["presses"], "plays_started": counts["plays_started"], "plays_ended": counts["plays_ended"],
        "returns_to_attract": final.get("returns", state["returns"]),
        "errors_logged": errors.after, "errors_at_setup": errors.setup, "errors": errors.kept,
        "step_ms": step_ms.summary(), "governor_ms": governor_ms.summary(),
        "governor": {"held_ticks": wall.governor.held_ticks if wall is not None else 0,
                     "fps": wall.governor.fps if wall is not None else None},
        "meter": {"frames": meter.frames if meter else 0, "area_max": meter.area_max if meter else 0.0,
                  "squares_max": meter.squares_max if meter else 0, "budget": BUDGET},
        "windows": windows, "fds": {"first": first["fds"], "last": open_fds()},
        "rss_kb": {"first": first["rss_kb"], "last": peak_rss_kb()}, "children_left": children_of_this_process(),
        "run_ended_early": 0 if state["finished"] else 1,
        "sha": git_sha(), "config": json.loads(json.dumps(dataclasses.asdict(cfg), default=str)),
        "times": {"started_at": started_at, "elapsed_s": round(elapsed, 3), "minutes": minutes,
                  "press_every": press_every, "seed": seed, "window_s": window_s},
    }


def failures(report: dict) -> list[str]:
    """The must-be-zero counts that are not, by name."""
    found = [f"{name}={report[name]}" for name in ("push_failures", "errors_logged", "children_left",
                                                   "run_ended_early") if report.get(name)]
    over = [w["t"] for w in report.get("windows", []) if w["squares_max"] > BUDGET]
    if over:
        found.append(f"windows with squares_max over {BUDGET}: at {over}")
    return found


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="python -m tools.show_soak", description=__doc__.split("\n")[0])
    ap.add_argument("--minutes", type=float, default=5.0)
    ap.add_argument("--press-every", type=float, default=PRESS_EVERY_S, metavar="SECONDS")
    ap.add_argument("--config", type=Path, default=Path("show.toml"))
    ap.add_argument("--backend", choices=BACKENDS, default="fake")
    ap.add_argument("--real-devices", action="store_true", help="the real lights, audio and buttons (the Pi)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--window-s", type=float, default=WINDOW_S)
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "soak")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    for name in ("minutes", "press_every", "window_s"):
        if not getattr(args, name) > 0:
            print(f"--{name.replace('_', '-')} must be over 0, got {getattr(args, name)}", file=sys.stderr)
            return 2
    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    try:
        cfg = replace(load_config(config_path), backend=args.backend)
    except Exception as exc:
        print(f"config: {exc}", file=sys.stderr)
        return 2
    with sigterm_raises():                          # SDL's mixer would swallow SIGTERM otherwise
        report = soak(cfg, args.minutes, args.press_every, seed=args.seed, window_s=args.window_s,
                      real_devices=args.real_devices, player_factory=EntryPlayer)
    bad = failures(report)
    report["failures"] = bad
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / f"soak-{time.strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{report['steps']} steps, {report['presses']} presses, step p95 {report['step_ms']['p95']} ms, "
          f"squares_max {report['meter']['squares_max']}; report {path}")
    for line in bad:
        print(f"FAIL {line}", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
