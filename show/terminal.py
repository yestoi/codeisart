"""The show's terminal: a pty for the child, a pyte screen for the wall.

The screen has LNM set, so a bare "\\n" fed locally is CR LF. A child gets a real pty with the window size
set (its own "\\n" is translated by the tty layer), runs in its own session, and is killed with its whole
process group. The pump is bounded by bytes and by time, and reads at most READ_CHUNK at a time so the
clock is checked often (spec 4.6).
"""
from __future__ import annotations

import fcntl
import logging
import os
import pty
import select
import signal
import struct
import subprocess
import termios
import time
from pathlib import Path
from typing import Callable

import pyte
import pyte.modes

log = logging.getLogger(__name__)

READ_CHUNK = 1024
KILL_WAIT = 1.0  # seconds kill() waits for the shell after SIGKILL
KILL_POLL = 0.001  # seconds between polls while kill() waits
DRAIN_MAX = 2.0  # seconds after the exit that a pty still delivering data is drained before the kill


class Terminal:
    def __init__(self, columns: int = 80, rows: int = 23):
        self.columns, self.rows = columns, rows
        self.screen = pyte.Screen(columns, rows)
        self.screen.set_mode(pyte.modes.LNM)
        self.stream = pyte.ByteStream(self.screen)
        self.listeners: list[Callable[[bytes], None]] = []
        self.proc: subprocess.Popen | None = None
        self.master_fd: int | None = None
        self._exit_seen: float | None = None  # monotonic time finished_or_orphaned first saw the exit
        self._last_read: float | None = None  # monotonic time pump last read a byte of this run
        self._pgid: int | None = None  # the current run's process group; None before a run and once forgotten
        self.muted = False  # the reel's quiet build: the child's output is pumped and dropped, the screen stands still

    def feed(self, data: bytes) -> None:
        if self.muted:
            return
        self.stream.feed(data)
        for fn in list(self.listeners):
            fn(data)

    def reset(self, rows: int | None = None) -> None:
        """Clear the screen and restore the geometry (undoes ESC[?3h); rows given, it becomes the geometry."""
        if rows is not None:
            self.rows = rows
        # Resize first: pyte's reset() lays tab stops out over the current width, which may be 132.
        self.screen.resize(self.rows, self.columns)
        self.screen.reset()
        self.screen.set_mode(pyte.modes.LNM)

    def run(self, cmd: list[str], cwd: Path, env: dict | None = None, preexec=None) -> None:
        if self.running:
            raise RuntimeError("a process is already running in this terminal")
        # The last run's group is not signalled here: its number may belong to another group by now (C48).
        self._close_master()
        self.proc = None
        self._pgid = None
        self._exit_seen = None
        self._last_read = None
        master, slave = pty.openpty()
        try:
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", self.rows, self.columns, 0, 0))
            full_env = {**os.environ, "TERM": "xterm", "COLUMNS": str(self.columns),
                        "LINES": str(self.rows), **(env or {})}
            proc = subprocess.Popen(
                cmd, cwd=str(cwd), env=full_env, stdin=slave, stdout=slave, stderr=slave,
                start_new_session=True, preexec_fn=preexec, close_fds=True,
            )
        except BaseException:
            os.close(master)
            os.close(slave)
            raise
        os.close(slave)
        os.set_blocking(master, False)
        self.proc = proc
        self._pgid = proc.pid  # start_new_session: the child leads its own group
        self.master_fd = master

    def pump(self, max_bytes: int = 4096, budget_ms: float = 8.0) -> int:
        """Feed what the child wrote; stop at max_bytes, at budget_ms, when nothing is ready, or at EOF."""
        if self.master_fd is None:
            return 0
        deadline = time.monotonic() + budget_ms / 1000.0
        total = 0
        while total < max_bytes:
            ready, _, _ = select.select([self.master_fd], [], [], 0)
            if not ready:
                break
            try:
                data = os.read(self.master_fd, min(READ_CHUNK, max_bytes - total))
            except BlockingIOError:
                break
            except OSError:  # EIO on Linux once the child side is closed
                data = b""
            if not data:
                self._close_master()
                break
            self.feed(data)
            total += len(data)
            now = time.monotonic()
            self._last_read = now
            if now >= deadline:
                break
        return total

    @property
    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    @property
    def finished(self) -> bool:
        return self.proc is not None and self.proc.poll() is not None and self.master_fd is None

    @property
    def returncode(self) -> int | None:
        return None if self.proc is None else self.proc.poll()

    def finished_or_orphaned(self, grace: float = 0.5, drain_max: float = DRAIN_MAX) -> bool:
        """Finished (EOF and exit): the group signalled once, True. Exited, and nothing read for grace s
        since the later of the exit's first sighting and the last read, or drain_max s since that sighting:
        kill() and True. The caller pumps between calls.

        The finished path signals the group too: on macOS the shell's exit revokes the pty (EOF at once)
        while orphans that ignore SIGHUP live on. A pty still delivering data after the exit (Linux holds
        about 64 KB) is drained, up to drain_max, so the output's tail reaches the screen.
        """
        if self.finished:
            self._signal_group()
            return True
        if self.proc is None or self.proc.poll() is None:
            return False
        now = time.monotonic()
        if self._exit_seen is None:
            self._exit_seen = now
        quiet_since = max(self._exit_seen, self._last_read or self._exit_seen)
        if now - quiet_since < grace and now - self._exit_seen < drain_max:
            return False
        self.kill()
        return True

    def kill(self) -> None:
        """SIGKILL to the process group (also after the shell exited: its orphans), wait, a last pump, close.

        The group is forgotten at the end: every member got the signal. A pump that raises (the screen
        refuses a sequence, C49) is logged once and not retried: the master is closed, so the dying child
        never waits on a reader, and the wait goes on unpumped. The master is closed and the group
        forgotten whatever happens.
        """
        if self.proc is None:
            return
        try:
            self._signal_group()
            # Wait, reading the master meanwhile: on macOS a child killed with a full pty output queue sits
            # in close() until the queue drains (about 0.6 s otherwise).
            deadline = time.monotonic() + KILL_WAIT
            try:
                while self.proc.poll() is None and time.monotonic() < deadline:
                    self.pump()
                    time.sleep(KILL_POLL)
                self.pump()
            except Exception:
                log.exception("the pump raised while killing; the rest of the output is dropped")
                self._close_master()
                while self.proc.poll() is None and time.monotonic() < deadline:
                    time.sleep(KILL_POLL)
        finally:
            self._pgid = None
            self._close_master()

    def _signal_group(self) -> None:
        """SIGKILL to the current run's group, unless forgotten (C48: its number may have been reused).

        Forgotten when it is gone, and after a signal sent once the leader is reaped: every member got it
        and none can join. Kept on EPERM (macOS: the group holds only the unreaped leader).
        """
        if self._pgid is None:
            return
        reaped = self.proc is not None and self.proc.returncode is not None
        try:
            os.killpg(self._pgid, signal.SIGKILL)
        except ProcessLookupError:  # the group is gone
            self._pgid = None
            return
        except PermissionError:  # macOS: the group holds only the unreaped leader (EPERM)
            return
        if reaped:
            self._pgid = None

    def _close_master(self) -> None:
        if self.master_fd is not None:
            os.close(self.master_fd)
            self.master_fd = None
