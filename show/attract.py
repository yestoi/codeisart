"""Attract mode: the entries' sources scroll on the terminal while nobody plays (spec 4.5)."""
from __future__ import annotations

import logging
from typing import Iterable

from show.entries import Entry
from show.terminal import Terminal

log = logging.getLogger(__name__)

BANNER = b"CODE IS ART, A.I. IS NOT\nPress the button on any portrait to compile and run it.\n\n"
BANNER_EVERY = 40  # source lines between banners
MAX_LINES_PER_TICK = 23  # a late tick feeds at most a screen


class Attract:
    def __init__(self, entries: Iterable[Entry], term: Terminal, lines_per_second: float, rows: int = 23):
        self.term = term
        self.lps = lines_per_second
        self.rows = rows
        # (bytes, is_source): headers do not count toward the banner
        self.lines: list[tuple[bytes, bool]] = []
        for e in sorted(entries, key=lambda e: e.station):
            try:
                text = e.source.read_bytes()
            except OSError as exc:
                log.error("attract: skipping %s, cannot read %s: %s", e.slug, e.source, exc)
                continue
            self.lines += [(b"", False), (f"---- {e.title} -- {e.plaque} ----".encode(), False), (b"", False)]
            src = text.replace(b"\r\n", b"\n").split(b"\n")
            if src and src[-1] == b"":
                src.pop()
            self.lines += [(s, True) for s in src]
        self._i = 0
        self._source_lines = 0
        self._t0: float | None = None
        self._emitted = 0

    def start(self, now: float) -> None:
        self.term.reset(self.rows)
        self.term.feed(BANNER)
        self._t0 = now
        self._emitted = 0

    def idle_seconds(self, now: float) -> float:
        return 0.0 if self._t0 is None else now - self._t0

    def tick(self, now: float) -> None:
        try:
            if not self.lines or self._t0 is None:
                return
            want = int((now - self._t0) * self.lps)
            n = min(want - self._emitted, MAX_LINES_PER_TICK)
            for _ in range(n):
                line, is_source = self.lines[self._i % len(self.lines)]
                self.term.feed(line + b"\n")
                self._i += 1
                if is_source:
                    self._source_lines += 1
                    if self._source_lines % BANNER_EVERY == 0:
                        self.term.feed(BANNER)
            self._emitted = max(want, self._emitted)
        except Exception:
            log.exception("attract: tick failed")
