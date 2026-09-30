"""Raw Ethernet driver for the Colorlight 5A-75B/E receiving card (Linux only, needs CAP_NET_RAW), as a steady
sender: whatever rate the caller pushes at, the card gets OUTPUT_FPS (59) frames a second from a child process,
sync first, the pixels BGR, the sync within 100 us of its deadline (show/display/colorlight_sender.py). The spec:
docs/superpowers/specs/2026-09-29-route-a-steady-sender-design.md; the measurements behind it:
docs/superpowers/reviews/2026-09-29-sender-card-spike.md, section 5.

push(frame) checks the frame, then the sender's news (below), copies the frame into the shared slot and returns:
nothing is sent by the caller's thread. set_brightness stores the level; every sync and brightness packet from
the next tick carries it. The wall is black from the moment the display opens (the card keeps its last picture
through a restart otherwise), and close() runs black for CLOSE_HOLD_S, stops the sender after a whole burst,
closes the socket and unlinks the slot.

The sender's news comes back through push: a send that raised in the child (recorded, the sender paused) is
raised by the next push, which stores nothing, so show.wall.GovernedDisplay starts its hold as before; the
push that ends the hold (the counted frame again) clears the pause and the stream restarts on it. A child that
died, or stopped beating for DEAD_S, makes push raise "not running" until RESTART_S after, when the next push
starts it again (dark) and is taken.

Brightness: the display starts at SAFE_BRIGHTNESS (0.4, the power-supply cap of both configs) unless
make_display passes the configured level. A level that is NaN or not above 0 is sent as 0: dark, never bright.
"""
from __future__ import annotations

import errno
import logging
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

import numpy as np

from show.display.colorlight_packets import (BRIGHTNESS_PAYLOAD_LEN, CHUNK_PIXELS, DST_MAC, ETH_BRIGHTNESS,  # noqa: F401
                                             ETH_FRAME, ETH_ROW, FRAME_PAYLOAD_LEN, ROW_HEADER_LEN, SRC_MAC,
                                             brightness_packet, chunk_pixels, frame_packet, level_byte,
                                             row_buffers, row_packets)
from show.display.colorlight_sender import BEATS, CLOSE_HOLD_S, ERRNO, ERRORS, LEVEL, PAUSE, RT, STOP, Slot, stats_of

log = logging.getLogger(__name__)

SAFE_BRIGHTNESS = 0.4       # the level before set_brightness: arcade.toml's brightness, show.toml's cap
START_S = 2.0               # the child's first beat must come within this of its start
DEAD_S = 1.0                # a child that has not beaten for this long is dead
RESTART_S = 1.0             # a dead child is started again at the first push this long after it died
JOIN_S = 3.0                # the close waits this long for the child, then terminates it
POLL_S = 0.01               # the start's wait between looks at the beat
SOL_PACKET, PACKET_QDISC_BYPASS = 263, 20   # past the port's queue: it reorders one frame in a thousand
ROOT = Path(__file__).resolve().parents[2]  # the repository: on the child's path whatever the parent's cwd


class SenderProcess:
    """The child as the driver sees it: alive, joined, terminated (SIGKILL: the child ignores SIGTERM), its exit code."""

    def __init__(self, proc: subprocess.Popen):
        self._proc = proc
        self.pid = proc.pid

    def is_alive(self) -> bool:
        return self._proc.poll() is None

    def join(self, timeout: float | None = None) -> None:
        try:
            self._proc.wait(timeout)
        except subprocess.TimeoutExpired:
            pass

    def terminate(self) -> None:
        if self.is_alive():
            self._proc.kill()

    @property
    def exitcode(self) -> int | None:
        return self._proc.poll()


def spawn_sender(slot: Slot, sock) -> SenderProcess:
    """The sender in a child: this interpreter running show.display.colorlight_sender, the socket inherited as a
    descriptor (the parent keeps its own for a restart). A plain subprocess, not multiprocessing: a fork behind
    MediaPipe's threads is not safe, and multiprocessing's spawn starts a resource tracker that outlives the
    child and that the show's soak counts as a child left behind."""
    fd = sock.fileno()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    argv = [sys.executable, "-m", "show.display.colorlight_sender", slot.path, str(slot.width), str(slot.height),
            str(fd), str(int(sock.family)), str(int(sock.type)), str(sock.proto), str(os.getpid())]
    return SenderProcess(subprocess.Popen(argv, pass_fds=(fd,), env=env, cwd=str(ROOT)))


class ColorlightDisplay:
    def __init__(self, width: int, height: int, iface: str, sock=None, brightness: float = SAFE_BRIGHTNESS, *,
                 launch: Callable = spawn_sender, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep):
        chunk_pixels(width)                       # a width that does not split is refused before anything opens
        self.width, self.height = width, height
        self.brightness = brightness
        self.restarts = 0
        self._launch, self._clock, self._sleep = launch, clock, sleep
        self._child = None
        self._seen_errors = 0
        self._died_at: float | None = None
        self._beat = (0, 0.0)
        self.sock = sock if sock is not None else _open_raw_socket(iface)
        self.slot = None
        try:
            self.slot = Slot.create(width, height)
            self.slot.h[LEVEL] = level_byte(brightness)
            self._start()
        except BaseException:
            self.sock.close()
            if self.slot is not None:
                self.slot.close()
            raise

    # -- the child ---------------------------------------------------------------------------------------------

    def _start(self) -> None:
        h = self.slot.h
        h[STOP] = 0
        h[PAUSE] = 0
        before = int(h[BEATS])
        self._child = self._launch(self.slot, self.sock)
        deadline = self._clock() + START_S
        while int(h[BEATS]) == before:
            if not self._child.is_alive() or self._clock() >= deadline:
                self._reap()
                raise OSError(errno.ESRCH, "the colorlight sender did not start")
            self._sleep(POLL_S)
        self._beat = (int(h[BEATS]), self._clock())
        self._died_at = None
        if not h[RT]:
            log.warning("the colorlight sender runs without real-time priority (CAP_SYS_NICE or root gives it): "
                        "the sync may be late now and then")

    def _reap(self) -> None:
        child = self._child
        if child is None:
            return
        if child.is_alive():
            child.terminate()
        child.join(JOIN_S)

    def _alive(self) -> bool:
        if self._child is None or not self._child.is_alive():
            return False
        beats, now = int(self.slot.h[BEATS]), self._clock()
        if beats != self._beat[0]:
            self._beat = (beats, now)
            return True
        return now - self._beat[1] < DEAD_S

    def _check(self) -> None:
        """The sender's news since the last push: a failed send raises it; a dead sender raises, or is
        restarted once RESTART_S has passed."""
        h = self.slot.h
        errors = int(h[ERRORS])
        if errors != self._seen_errors:
            self._seen_errors = errors
            code = int(h[ERRNO])
            raise OSError(code, "the colorlight sender's send failed: %s"
                          % (os.strerror(code) if code else "unknown error"))
        if self._alive():
            return
        now = self._clock()
        if self._died_at is None:
            self._died_at = now
            self._reap()
            log.error("the colorlight sender died (exit code %s); a restart in %.0f s",
                      getattr(self._child, "exitcode", None), RESTART_S)
        if now - self._died_at < RESTART_S:
            raise OSError(errno.ESRCH, "the colorlight sender is not running")
        try:
            self._start()
        except OSError:
            self._died_at = self._clock()
            raise
        self.restarts += 1
        log.info("the colorlight sender restarted (%d so far)", self.restarts)

    # -- the Display protocol ----------------------------------------------------------------------------------

    def push(self, frame: np.ndarray) -> None:
        if frame.shape != (self.height, self.width, 3):
            raise ValueError(f"frame shape {frame.shape} is not ({self.height}, {self.width}, 3)")
        if frame.dtype != np.uint8:
            raise ValueError(f"frame dtype {frame.dtype} is not uint8; convert before push")
        self._check()
        self.slot.write(frame)
        self.slot.h[PAUSE] = 0

    def set_brightness(self, level: float) -> None:
        self.brightness = level
        self.slot.h[LEVEL] = level_byte(level)

    def stats(self) -> dict:
        s = stats_of(self.slot.h)
        s["restarts"] = self.restarts
        return s

    def close(self) -> None:
        """Black for CLOSE_HOLD_S, the sender stopped after a whole burst, the socket closed, the slot unlinked."""
        if self.slot is None:
            return
        try:
            child = self._child
            if child is not None and child.is_alive():
                self.slot.write(np.zeros((self.height, self.width, 3), np.uint8))
                self.slot.h[PAUSE] = 0
                self._sleep(CLOSE_HOLD_S)
                self.slot.h[STOP] = 1
                child.join(JOIN_S)
                if child.is_alive():
                    log.error("the colorlight sender did not stop in %.0f s; terminated", JOIN_S)
                    child.terminate()
                    child.join(JOIN_S)
        finally:
            self.sock.close()
            self.slot.close()
            self.slot = None


def stats_line(display) -> str | None:
    """One line for the log at a close, when the display is the colorlight driver; None otherwise."""
    stats = getattr(display, "stats", None)
    if stats is None:
        return None
    s = stats()
    return ("colorlight sender: %d frames, %d late (over 1 ms), worst %.0f us, sync to sync sd %.0f us, %d slips, "
            "%d send errors, %d restarts, real-time %s" % (s["frames"], s["late"], s["worst_us"], s["sd_us"],
                                                           s["slips"], s["errors"], s["restarts"],
                                                           "yes" if s["rt"] else "no"))


def _open_raw_socket(iface: str) -> socket.socket:
    if not hasattr(socket, "AF_PACKET"):
        raise OSError("the colorlight backend needs Linux raw sockets (AF_PACKET); "
                      "use --backend sdl on this machine")
    try:
        sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
    except PermissionError as e:
        raise PermissionError(f"a raw socket on {iface} needs CAP_NET_RAW: run under the arcade's systemd unit "
                              "(AmbientCapabilities=CAP_NET_RAW) or grant it once with "
                              "sudo setcap cap_net_raw+ep on the venv's real python binary") from e
    try:
        sock.setsockopt(SOL_PACKET, PACKET_QDISC_BYPASS, 1)
    except OSError as e:
        log.warning("cannot bypass the port's queue on %s (%s): packets go through it", iface, e)
    try:
        sock.bind((iface, 0))
    except OSError as e:
        sock.close()
        raise OSError(e.errno, f"cannot bind a raw socket to {iface}: {e.strerror or e}") from e
    return sock
