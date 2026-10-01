"""The oracle's plain bot plays, made by worker processes before its reports (it18 T-pool).

fill() makes every report play that PLAYS does not hold yet in up to PLAY_WORKERS plain `python -m
tests.arcade.pooled` subprocesses, each a fresh interpreter in this checkout, and stores them in PLAYS by the memo's
key (tests/arcade/test_oracle.py's shared_plays), so a report then finds them there. A play is a pure function of
(game, bot, seed, layout), and a worker runs the real bots.play with its defaults, so its play is the one the memo
would make. Not multiprocessing: its resource tracker outlives the pool as a child of this process, and
tests/test_show_soak.py's children_left would count it.

A worker that cannot start, fails, runs past the deadline or returns a short or foreign file gives one
RuntimeWarning and stores nothing: the memo then makes its plays in this process, as before the pool.

    python -m tests.arcade.pooled <jobs.json> <out.pickle>      # a worker, run by fill() only
"""
from __future__ import annotations

import json
import os
import pickle
import subprocess
import sys
import tempfile
import time
import warnings
from pathlib import Path
from typing import Sequence

import arcade
from arcade import bots
from arcade.games import get_game
from tests.arcade.helpers import PLAYS, play_key

PLAY_WORKERS = 4                  # worker processes at most: the Pi 5 has 4 cores, the shared Mac 4 fast ones (Q97)
WORKER_TIMEOUT_S = 120.0          # from the first worker's start to the last's end; past it the rest are killed
                                  # (the 180 plays take about 33 s; a hang must not push the suite past 10 minutes)
ROLES = ("good", "lazy", "none")  # feel._bot_plays' three bots, in its order; "none" is bots.Nobody
ROOT = Path(__file__).resolve().parents[2]   # the checkout this file is in (a worktree's own): the workers' cwd
PYTHON = sys.executable           # the workers' interpreter (a module constant so a test can replace it)
Job = tuple[str, str, int, str]   # (game name, role, seed, layout): plain data across the process boundary
Key = tuple[str, str, int, str]   # helpers.play_key's


def bot_for(game_cls, role: str) -> bots.Bot:
    """A fresh bot of game_cls for role: bots.Nobody() for "none", else for_game()[0][role]()."""
    return bots.Nobody() if role == "none" else bots.for_game(game_cls)[0][role]()


def jobs(reports: Sequence[tuple[type, str, Sequence[int]]]) -> list[Job]:
    """One job per play of the reports: for each (game_cls, layout, seeds) in order, for each role in ROLES, for
    each seed in order."""
    return [(game_cls.info.name, role, seed, layout)
            for game_cls, layout, seeds in reports for role in ROLES for seed in seeds]


def play_job(job: Job) -> bots.Play:
    """The worker's play: the game by name, a fresh bot for the role, bots.play with every other default."""
    name, role, seed, layout = job
    game_cls = get_game(name)
    return bots.play(game_cls, bot_for(game_cls, role), seed, layout)


def _tail(path: Path) -> str:
    """The last 20 lines of a worker's stderr file ("" when there is none)."""
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(lines[-20:])


def _read(out: Path, share: list) -> tuple[list | None, str]:
    """(the plays of a worker that exited 0, "") when its file holds one per job of its share and its arcade is
    this checkout's, else (None, why)."""
    try:
        with open(out, "rb") as f:
            data = pickle.load(f)
        plays, where = data["plays"], data["arcade"]
    except Exception as e:                             # a missing, short or foreign file: its share is not stored
        return None, f"its file did not load ({e!r})"
    if len(plays) != len(share):
        return None, f"its file holds {len(plays)} plays for its {len(share)} jobs"
    if Path(where).resolve().parents[1] != ROOT:
        return None, f"it imported the arcade at {where}, not {ROOT}'s"
    return plays, ""


def fill(reports, plays: dict = PLAYS, workers: int = PLAY_WORKERS) -> set[Key]:
    """Every play of jobs(reports) whose key is not in plays, made by up to `workers` worker processes and stored
    in plays by the memo's key. Returns the keys it stored. No worker outlives it, on any path."""
    games = {game_cls.info.name: game_cls for game_cls, _, _ in reports}
    todo = []                                          # (job, key) for each play not in plays yet
    for job in jobs(reports):
        name, role, seed, layout = job
        key = play_key(games[name], type(bot_for(games[name], role)).__name__, seed, layout)
        if key not in plays:
            todo.append((job, key))
    cores = os.cpu_count() or 1
    n = min(workers, cores, len(todo))
    if n < 2:
        if len(todo) >= 2 and workers >= 2:            # the core count made it
            warnings.warn(f"pooled.fill: {cores} core(s), so no worker; the memo makes the {len(todo)} plays in "
                          f"this process", RuntimeWarning, stacklevel=2)
        return set()
    shares = [todo[k::n] for k in range(n)]            # round robin: each worker gets a mix of the games and bots
    stored: set[Key] = set()
    with tempfile.TemporaryDirectory(prefix="pooled-") as tmp:
        tmp = Path(tmp)
        procs: list[subprocess.Popen | None] = []
        why: dict[int, str] = {}                       # worker k: why it failed before its exit was read
        try:
            deadline = time.monotonic() + WORKER_TIMEOUT_S
            for k, share in enumerate(shares):
                (tmp / f"jobs-{k}.json").write_text(json.dumps([job for job, _ in share]))
                with open(tmp / f"err-{k}.txt", "wb") as err:
                    try:
                        procs.append(subprocess.Popen(
                            [PYTHON, "-m", "tests.arcade.pooled", str(tmp / f"jobs-{k}.json"),
                             str(tmp / f"out-{k}.pickle")],
                            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=err))
                    except OSError as e:
                        procs.append(None)
                        why[k] = f"it could not start ({e!r})"
            for k, proc in enumerate(procs):
                if proc is None:
                    continue
                try:
                    proc.wait(timeout=max(0.0, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    why[k] = f"it ran past the pool's {WORKER_TIMEOUT_S:g} s and was killed"
        finally:
            for proc in procs:
                if proc is not None and proc.poll() is None:
                    proc.kill()
                    proc.wait()
        for k, (share, proc) in enumerate(zip(shares, procs)):
            code = None if proc is None else proc.returncode
            made, reason = None, why.get(k) or ("" if code == 0 else "it exited non-zero")
            if not reason:
                made, reason = _read(tmp / f"out-{k}.pickle", share)
            if made is None:
                warnings.warn(f"pooled.fill: worker {k} of {n} ({len(share)} plays): {reason}, exit code {code}; the "
                              f"memo makes its plays in this process. Its stderr's last 20 lines:\n"
                              f"{_tail(tmp / f'err-{k}.txt')}", RuntimeWarning, stacklevel=2)
                continue
            for (_, key), play in zip(share, made):
                plays[key] = play
                stored.add(key)
    return stored


def main(argv: list[str] | None = None) -> int:
    """The worker: argv is [jobs.json, out.pickle]. Plays each job in order and pickles {"arcade": this process's
    arcade.__file__, "plays": [bots.Play, ...]} to out.pickle. An exception is not caught: exit 1, its traceback on
    stderr."""
    jobs_path, out_path = sys.argv[1:] if argv is None else argv
    todo = [tuple(job) for job in json.loads(Path(jobs_path).read_text())]
    result = {"arcade": arcade.__file__, "plays": [play_job(job) for job in todo]}
    with open(out_path, "wb") as f:
        pickle.dump(result, f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
