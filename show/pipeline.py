"""The entry pipeline (spec 4.3): type the source, build it live, run it sandboxed, dwell; on a failure the
reason, a hold and the fallback recording.

The player is ticked by the show's loop and never raises from `tick`. Each build and run ends through
`Terminal.finished_or_orphaned()`, so a backgrounded child never holds the pty and the output's tail is
drained before the kill. Crowd mode (spec 4.5) is a flag read every tick: the source types at 4x, the run
is capped at `crowd_run_seconds`, the dwell is skipped.
"""
from __future__ import annotations

import logging
import os
import re
import time
from enum import Enum
from typing import Callable

from show import sandbox
from show.config import Config
from show.entries import Entry
from show.recording import CastError, CastPlayer, CastWriter
from show.sandbox import limits, wrap
from show.terminal import Terminal

log = logging.getLogger(__name__)

BUILD_MEMORY = 512 * 1024 * 1024
RUN_MEMORY = sandbox.DEFAULT_MEMORY
CPU_MARGIN = 5.0  # CPU seconds over a phase's wall-clock timeout, so the timeout ends it first
CROWD_SPEEDUP = 4  # spec 4.5: the source types at 4x in crowd mode
BUILD_ENV = {"LC_ALL": "C"}  # it10 note 4: straight quotes in the compiler's diagnostics
CAPTURE_TEMP = "fallback.cast.part"

# A shell operator, quote, glob, expansion, assignment, comment or newline: the run line is left to sh.
_SHELL_SYNTAX = re.compile(r"""[|&;<>()$`\\"'*?\[\]{}~=#!\n]""")


class Phase(str, Enum):
    SOURCE = "source"
    BUILD = "build"
    RUN = "run"
    ERROR_HOLD = "error_hold"
    FALLBACK = "fallback"
    DWELL = "dwell"
    DONE = "done"


def signal_of(returncode: int) -> int | None:
    """The signal that ended the process: only a negative return code (a non-zero exit is normal)."""
    return -returncode if returncode < 0 else None


def run_command(run: str) -> str:
    """`exec ` before a plain command, so the program is the pty's process and a crash reads as a signal."""
    run = run.strip()
    if _SHELL_SYNTAX.search(run) or run.startswith("exec "):
        return run
    return "exec " + run


class EntryPlayer:
    def __init__(self, entry: Entry, term: Terminal, cfg: Config,
                 clock: Callable[[], float] = time.monotonic):
        self.entry, self.term, self.cfg, self.clock = entry, term, cfg, clock
        self.phase = Phase.DONE
        self.failure: str | None = None
        self.crowd = False
        self._events: list[str] = []
        self._t0 = 0.0
        self._src = b""
        self._typed = 0.0  # characters due so far, fractional
        self._fed = 0  # characters of the source fed
        self._last = 0.0  # the last tick's time, for the typewriter
        self._build_end: int | str | None = None  # the build's return code, or "timeout"
        self._cast: CastPlayer | None = None
        self._writer: CastWriter | None = None

    # -- lifecycle -----------------------------------------------------------

    @property
    def done(self) -> bool:
        return self.phase == Phase.DONE

    @property
    def rows(self) -> int:
        return self.cfg.rows if self.entry.full_screen else self.cfg.rows - 1

    def run_timeout(self) -> float:
        cap = self.cfg.crowd_run_seconds if self.crowd else self.cfg.idle_run_seconds
        return min(self.entry.run_seconds, cap)

    def start(self, now: float, crowd: bool = False) -> None:
        e = self.entry
        self.crowd = crowd
        self.failure = None
        self._events = []
        self._build_end = None
        self._cast = None
        self._src = e.source.read_bytes().replace(b"\r\n", b"\n")
        self._typed = 0.0
        self._fed = 0
        self._last = now
        self.term.reset(self.rows)
        self.term.feed(f"{e.title}\n{e.plaque}\n\n$ cat {e.source.name}\n".encode())
        self._enter(Phase.SOURCE, now)

    def tick(self, now: float) -> list[str]:
        """Advance the phase; events "cue:compile", "cue:run", "cue:error". Never raises."""
        try:
            getattr(self, f"_tick_{self.phase.value}")(now)
        except Exception as exc:
            self._on_exception(exc, now)
        self._last = now
        events, self._events = self._events, []
        return events

    def stop(self) -> None:
        """Kill the child, drop a capture in progress, DONE."""
        try:
            self._kill()
        finally:
            self._stop_capture(keep=False)
            self.phase = Phase.DONE

    # -- phases --------------------------------------------------------------

    def _enter(self, phase: Phase, now: float) -> None:
        self.phase = phase
        self._t0 = now

    def _tick_source(self, now: float) -> None:
        rate = self.cfg.typewriter_cps * (CROWD_SPEEDUP if self.crowd else 1)
        self._typed += max(0.0, now - self._last) * rate
        want = min(len(self._src), int(self._typed))
        if want > self._fed:
            chunk, self._fed = self._src[self._fed:want], want
            self.term.feed(chunk)
        if want < len(self._src):
            return
        tail = b"" if not self._src or self._src.endswith(b"\n") else b"\n"
        self.term.feed(tail + f"$ {self.entry.build}\n".encode())
        self.term.run(["sh", "-c", self.entry.build], cwd=self.entry.dir, env=BUILD_ENV,
                      preexec=limits(self.entry.build_seconds + CPU_MARGIN, BUILD_MEMORY))
        self._events.append("cue:compile")
        self._enter(Phase.BUILD, now)

    def _tick_build(self, now: float) -> None:
        if self._build_end is None:
            self._pump()
            if self.term.finished_or_orphaned():
                self._build_end = self.term.returncode
            elif now - self._t0 > self.entry.build_seconds:
                self._kill()
                self._build_end = "timeout"
        if self._build_end is None or now - self._t0 < self.cfg.min_build_seconds:
            return
        if self._build_end == "timeout":
            self._fail("build timed out", now)
        elif self._build_end != 0:
            self._fail(f"build failed (exit {self._build_end})", now)
        else:
            self._start_run(now)

    def _start_run(self, now: float) -> None:
        self.term.feed(f"$ {self.entry.run}\n".encode())
        if self.cfg.capture and self.entry.fallback is None:
            self._writer = CastWriter(self.entry.dir / CAPTURE_TEMP, self.term.columns, self.term.rows,
                                      self.clock)
            self.term.listeners.append(self._writer.write)
        # The CPU limit is a safety net under the longest wall-clock timeout crowd mode may give.
        longest = min(self.entry.run_seconds, max(self.cfg.crowd_run_seconds, self.cfg.idle_run_seconds))
        self.term.run(wrap(run_command(self.entry.run)), cwd=self.entry.dir,
                      preexec=limits(longest + CPU_MARGIN, RUN_MEMORY))
        self._events.append("cue:run")
        self._enter(Phase.RUN, now)

    def _tick_run(self, now: float) -> None:
        self._pump()
        if self.term.finished_or_orphaned():
            sig = signal_of(self.term.returncode or 0)
            self._stop_capture(keep=sig is None)
            if sig is not None:
                self._fail(f"crashed (signal {sig})", now)
            else:
                self._enter(Phase.DWELL, now)
        elif now - self._t0 > self.run_timeout():
            self._kill()
            self._stop_capture(keep=True)
            self._enter(Phase.DWELL, now)

    def _tick_error_hold(self, now: float) -> None:
        if now - self._t0 < self.cfg.error_hold:
            return
        cast = self._load_fallback()
        if cast is None:
            self._enter(Phase.DWELL, now)
            return
        self.term.reset(self.rows)
        self.term.feed(f"$ {self.entry.run}   (recording)\n".encode())
        cast.start(now)
        self._cast = cast
        self._enter(Phase.FALLBACK, now)

    def _tick_fallback(self, now: float) -> None:
        assert self._cast is not None
        data = self._cast.tick(now)
        if data:
            self.term.feed(data)
        if self._cast.done or now - self._t0 >= self.run_timeout():
            self._cast = None
            self._enter(Phase.DWELL, now)

    def _tick_dwell(self, now: float) -> None:
        if self.crowd or now - self._t0 >= self.cfg.dwell:
            self._enter(Phase.DONE, now)

    def _tick_done(self, now: float) -> None:
        pass

    # -- helpers -------------------------------------------------------------

    def _pump(self) -> None:
        self.term.pump(self.cfg.pump_bytes, self.cfg.pump_ms)

    def _kill(self) -> None:
        """Kill this player's child: only BUILD and RUN own one (the terminal may serve the next player)."""
        if self.phase in (Phase.BUILD, Phase.RUN):
            self.term.kill()

    def _load_fallback(self) -> CastPlayer | None:
        if self.entry.fallback is None:
            return None
        try:
            return CastPlayer(self.entry.fallback)
        except CastError as exc:
            log.error("%s: the fallback cannot be played, none is: %s", self.entry.slug, exc)
            return None

    def _fail(self, reason: str, now: float) -> None:
        self.failure = reason
        self._events.append("cue:error")
        self._enter(Phase.ERROR_HOLD, now)
        self.term.feed(f"\n*** {reason} ***\n".encode())

    def _on_exception(self, exc: Exception, now: float) -> None:
        """While feeding or pumping (SOURCE, BUILD, RUN): kill the child and fail the entry, so the fallback
        or the end follows (it10 note 1). Anywhere else (the hold, the fallback, the dwell): end the entry."""
        log.exception("%s: exception in %s", self.entry.slug, self.phase.value)
        if self.phase in (Phase.SOURCE, Phase.BUILD, Phase.RUN):
            try:
                self._kill()  # SOURCE owns no child yet
            except Exception:
                log.exception("%s: kill after the exception failed", self.entry.slug)
            try:
                self._stop_capture(keep=False)
            except Exception:
                log.exception("%s: dropping the capture failed", self.entry.slug)
            try:
                self._fail(f"terminal error ({type(exc).__name__})", now)
            except Exception:
                log.exception("%s: showing the failure failed", self.entry.slug)
            return
        self._cast = None
        self._enter(Phase.DONE, now)

    def _stop_capture(self, keep: bool) -> None:
        """Close the capture; keep it (os.replace onto fallback.cast) only after a clean run."""
        writer, self._writer = self._writer, None
        if writer is None:
            return
        if writer.write in self.term.listeners:
            self.term.listeners.remove(writer.write)
        try:
            writer.close()
            if keep:
                os.replace(writer.path, self.entry.fallback_path)
        finally:
            if not keep:
                writer.path.unlink(missing_ok=True)
