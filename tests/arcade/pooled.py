"""The oracle's plain bot plays, made by worker processes before its reports (it18 T-pool, it20 R).

start() launches up to PLAY_WORKERS plain `python -m tests.arcade.pooled` subprocesses, each a fresh interpreter in
this checkout, for every report play that PLAYS does not hold yet; Pool.join() waits for them and stores their plays
in PLAYS by the memo's key (tests/arcade/test_oracle.py's shared_plays), so a report, and a game's own tests through
helpers.played, then find them there. fill() is start().join(). A play is a pure function of (game, bot, seed,
layout), and a worker runs the real bots.play with its defaults, so its play is the one the memo would make. Not
multiprocessing: its resource tracker outlives the pool as a child of this process, and tests/test_show_soak.py's
children_left would count it.

In a session, tests/conftest.py starts the pool (RUNNING) when collection ends, for the rows the selected tests read
(rows_for), and joins it before the first test that is not beside_the_pool: the soaks run while the workers play.

A worker that cannot start, fails, runs past the deadline or returns a short or foreign file gives one
RuntimeWarning at the join and stores nothing: the memo then makes its plays in this process, as before the pool.

    python -m tests.arcade.pooled <jobs.json> <out.pickle>      # a worker, run by start() only
"""
from __future__ import annotations

import json
import os
import pickle
import shutil
import subprocess
import sys
import tempfile
import time
import warnings
from pathlib import Path
from typing import Iterable, Sequence

import arcade
from arcade import bots
from arcade.games import get_game
from tests.arcade.helpers import PLAYS, play_key

PLAY_WORKERS = 4                  # worker processes at most: the Pi 5 has 4 cores, the shared Mac 4 fast ones (Q97)
WORKER_TIMEOUT_S = 180.0          # from the first worker's start to the last's end; past it the rest are killed
                                  # (eight games' 480 plays take about 105 s alone, 120 to 140 s beside the soaks;
                                  # a hang must not push the suite past 10 minutes)
BESIDE_THE_POOL = ("tests/arcade/test_actors.py", "tests/arcade/test_all_games.py")   # files that run beside it
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


class Pool:
    """The workers start() launched for one set of reports. join() waits for them and stores their plays; stop()
    kills them and stores nothing. Neither leaves a child or the temporary directory on any path.

    keys: every report key asked for; before: those already in plays at the start; started: time.monotonic() at
    the start; elapsed: seconds from the start to the last worker's end (its file's write; the join's read for a
    worker that failed), set by the join; waited: the first join's own wait, kept by a second."""

    def __init__(self, keys: frozenset[Key], before: frozenset[Key], plays: dict, shares: list, tmp: Path | None,
                 note: str = ""):
        self.keys, self.before, self.plays, self.shares, self.tmp = keys, before, plays, shares, tmp
        self.note = note                               # the core-count warning the join gives ("" for none)
        self.started, self._wall = time.monotonic(), time.time()
        self.elapsed: float | None = None
        self.waited: float | None = None
        self.procs: list[subprocess.Popen | None] = []
        self.why: dict[int, str] = {}                  # worker k: why it failed before its exit was read
        self.stored: set[Key] | None = None            # set by the first join or by stop()
        self.deadline = self.started + WORKER_TIMEOUT_S

    @property
    def joined(self) -> bool:
        return self.stored is not None

    def _kill(self) -> None:
        """Kill every worker still running and wait for each."""
        for proc in self.procs:
            if proc is not None and proc.poll() is None:
                proc.kill()
                proc.wait()

    def _reap(self) -> None:
        """Kill and wait for every worker still running, and remove the temporary directory."""
        self._kill()
        if self.tmp is not None:
            shutil.rmtree(self.tmp, ignore_errors=True)

    def stop(self) -> None:
        """Kill and reap every worker and remove the temporary directory; no play is stored, now or by a join."""
        if self.stored is None:
            self.stored = set()
        self._reap()

    def join(self) -> set[Key]:
        """Wait for the workers to the deadline, kill and reap the rest, and store every play a worker made in
        plays. Returns the keys stored; a second call returns the same set at once."""
        if self.stored is not None:
            return self.stored
        t0 = time.monotonic()
        stored: set[Key] = set()
        ends: list[float] = []                         # each worker's end, wall clock
        try:
            if self.note:
                warnings.warn(self.note, RuntimeWarning, stacklevel=2)
            for k, proc in enumerate(self.procs):
                if proc is None:
                    continue
                try:
                    proc.wait(timeout=max(0.0, self.deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    self.why[k] = f"it ran past the pool's {WORKER_TIMEOUT_S:g} s and was killed"
            self._kill()                               # the rest killed before the read: their exit codes are read
            n = len(self.shares)
            for k, (share, proc) in enumerate(zip(self.shares, self.procs)):
                code = None if proc is None else proc.returncode
                made, reason = None, self.why.get(k) or ("" if code == 0 else "it exited non-zero")
                out = self.tmp / f"out-{k}.pickle"
                if not reason:
                    made, reason = _read(out, share)
                if made is None:
                    ends.append(time.time())
                    warnings.warn(f"pooled.fill: worker {k} of {n} ({len(share)} plays): {reason}, exit code {code}; "
                                  f"the memo makes its plays in this process. Its stderr's last 20 lines:\n"
                                  f"{_tail(self.tmp / f'err-{k}.txt')}", RuntimeWarning, stacklevel=2)
                    continue
                ends.append(out.stat().st_mtime)
                for (_, key), play in zip(share, made):
                    self.plays[key] = play
                    stored.add(key)
        finally:
            self.stored = stored
            self._reap()
            self.waited = time.monotonic() - t0
            self.elapsed = max(ends) - self._wall if ends else 0.0
        return stored


RUNNING: Pool | None = None   # the session's pool, started by tests/conftest.py when collection ends


def start(reports, plays: dict = PLAYS, workers: int = PLAY_WORKERS) -> Pool:
    """Launch up to `workers` worker processes for every play of jobs(reports) whose key is not in plays, and
    return at once. A pool of no worker when the plays or the cores are too few (its join returns set(), with the
    core-count warning when the cores made it)."""
    games = {game_cls.info.name: game_cls for game_cls, _, _ in reports}
    keys, todo = set(), []                             # todo: (job, key) for each play not in plays yet
    for job in jobs(reports):
        name, role, seed, layout = job
        key = play_key(games[name], type(bot_for(games[name], role)).__name__, seed, layout)
        keys.add(key)
        if key not in plays:
            todo.append((job, key))
    before = frozenset(keys & plays.keys())
    cores = os.cpu_count() or 1
    n = min(workers, cores, len(todo))
    if n < 2:
        note = (f"pooled.fill: {cores} core(s), so no worker; the memo makes the {len(todo)} plays in this process"
                if len(todo) >= 2 and workers >= 2 else "")   # the core count made it
        return Pool(frozenset(keys), before, plays, [], None, note)
    shares = [todo[k::n] for k in range(n)]            # round robin: each worker gets a mix of the games and bots
    pool = Pool(frozenset(keys), before, plays, shares, Path(tempfile.mkdtemp(prefix="pooled-")))
    try:
        for k, share in enumerate(shares):
            (pool.tmp / f"jobs-{k}.json").write_text(json.dumps([job for job, _ in share]))
            with open(pool.tmp / f"err-{k}.txt", "wb") as err:
                try:
                    pool.procs.append(subprocess.Popen(
                        [PYTHON, "-m", "tests.arcade.pooled", str(pool.tmp / f"jobs-{k}.json"),
                         str(pool.tmp / f"out-{k}.pickle")],
                        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=err))
                except OSError as e:
                    pool.procs.append(None)
                    pool.why[k] = f"it could not start ({e!r})"
    except BaseException:
        pool.stop()
        raise
    return pool


def fill(reports, plays: dict = PLAYS, workers: int = PLAY_WORKERS) -> set[Key]:
    """Every play of jobs(reports) whose key is not in plays, made by up to `workers` worker processes and stored
    in plays by the memo's key: start(...).join(). Returns the keys it stored. No worker outlives it, on any path."""
    return start(reports, plays, workers).join()


def beside_the_pool(nodeid: str, perf: bool) -> bool:
    """True when the test may run while the workers play: its file is in BESIDE_THE_POOL and it is not timed."""
    return nodeid.split("::")[0] in BESIDE_THE_POOL and not perf


def rows_for(items: Iterable, report_plays: Sequence) -> list:
    """The rows of report_plays the selected items read, in report_plays' order: an item that needs pooled_plays
    with a game_cls parameter reads that game's row, one that needs pong_report Pong's, any other that needs
    pooled_plays (the pool's own test) every row. Items that need no pooled_plays ask for nothing."""
    wanted: set[str] = set()
    names = [game_cls.info.name for game_cls, _, _ in report_plays]
    for item in items:
        if "pooled_plays" not in item.fixturenames:
            continue
        params = getattr(getattr(item, "callspec", None), "params", {})
        if "game_cls" in params:
            wanted.add(params["game_cls"].info.name)
        elif "pong_report" in item.fixturenames:
            wanted.add("pong")
        else:
            wanted.update(names)
    return [row for row, name in zip(report_plays, names) if name in wanted]


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
