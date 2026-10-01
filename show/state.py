"""The show's state machine: attract, play and the queue, the lights' modes, the strip's text (spec 4.4 to 4.6).

`Show` uses only this much of a player: `done`, `crowd`, `start(now, crowd)`, `tick(now) -> events`, `stop()`.
A raise from a player or from attract is logged, the player is stopped (guarded), and the next queued entry or
attract follows (spec 4.6). Lights calls are guarded apart and never abort the show; `lights.tick` is the loop's.
"""
from __future__ import annotations

import logging
import random
from typing import Callable

from show.attract import Attract
from show.config import Config
from show.entries import Entry
from show.font import CELL_W
from show.pipeline import EntryPlayer
from show.queue import EntryQueue
from show.terminal import Terminal

log = logging.getLogger(__name__)

ATTRACT_STRIP = "PRESS A BUTTON ON ANY PORTRAIT"
ATTRACT_SHORT = ("PRESS A BUTTON", "ON ANY PORTRAIT")
NOTICE_S = 2.0  # spec 4.5: "PLAYING" / "QUEUED #n" for 2 s
ALTERNATE_S = 3.0  # Q58: a short strip alternates every 3 s
SHORT_BELOW = 40  # Q58: fewer characters than this fit, the strip alternates
FESTIVAL_STATIONS = 5  # Q56: stations 1 to 5 have portraits
FULL_SCREEN_EVERY_S = 10.0  # amendment Task 3: a full-screen entry shows the strip 2 s in every 10
FULL_SCREEN_SHOW_S = 2.0


def strip_chars(cfg: Config) -> int:
    """How many characters fit on the strip: the columns in the text view, a cell's width each in the ink view."""
    return cfg.columns if cfg.view == "text" else cfg.width // CELL_W


def wrap_words(text: str, width: int) -> list[str]:
    """The text in pieces of 1 to `width` characters (C54, Q91; width >= 1). A text that fits is the one piece, its
    spaces kept. Else its words (`text.split()`), each cut to `width` (the rest dropped), fill the pieces greedily in
    order: a word joins the open piece after one space when it fits, else it opens the next piece."""
    if len(text) <= width:
        return [text]
    pieces: list[str] = []
    for word in text.split():
        word = word[:width]
        if pieces and len(pieces[-1]) + 1 + len(word) <= width:
            pieces[-1] += " " + word
        else:
            pieces.append(word)
    return pieces


def eligible(entries: dict[int, Entry]) -> dict[int, Entry]:
    """Attract's and autoplay's entries: stations 1 to 5 when any of them is loaded, else all (Q56)."""
    festival = {s: e for s, e in entries.items() if 1 <= s <= FESTIVAL_STATIONS}
    return festival if festival else dict(entries)


class Show:
    def __init__(self, cfg: Config, entries: dict[int, Entry], term: Terminal, lights, audio,
                 player_factory: Callable = EntryPlayer, rng: random.Random | None = None):
        self.cfg = cfg
        self.lights, self.audio = lights, audio
        self.player_factory = player_factory
        self.rng = rng if rng is not None else random.Random()
        self._entries = dict(entries)
        self._term = term
        self._queue = EntryQueue()
        self._player = None
        self._current: Entry | None = None
        self._started = 0.0  # the current entry's start
        self._attract_t0 = 0.0  # attract's start, for the short strip's halves
        self._notice: tuple[str, float] | None = None
        self.attract = self._make_attract()

    # -- state ---------------------------------------------------------------------------------------------------

    @property
    def entries(self) -> dict[int, Entry]:
        return self._entries

    @property
    def term(self) -> Terminal:
        return self._term

    @property
    def queue(self) -> EntryQueue:
        return self._queue

    @property
    def player(self):
        return self._player

    @property
    def current(self) -> Entry | None:
        return self._current

    @property
    def playing(self) -> bool:
        return self._player is not None

    @property
    def full_screen(self) -> bool:
        return self._current is not None and self._current.full_screen

    # -- the loop's calls ----------------------------------------------------------------------------------------

    def start(self, now: float) -> None:
        self.relight()
        self._to_attract(now)

    def press(self, station: int, now: float) -> None:
        """Every press is acknowledged: the cue and the button's flash (spec 4.5). Never raises."""
        try:
            self._cue("keypress")
            self._flash(station, now)
            entry = self._entries.get(station)
            if entry is None:
                log.info("press on station %d, which has no entry", station)
                return
            if self._player is None:
                if self._play_next(now, entry):
                    self._notice = ("PLAYING", now)
                return
            if self._current is not None and self._current.station == station:
                self._notice = ("PLAYING", now)
                return
            if self._queued_position(station) is None:
                self._queue.push(entry)
                self._light(station, "pulse")
            self._notice = (f"QUEUED #{self._queued_position(station)}", now)
        except Exception:
            log.exception("press on station %d failed", station)
            self._recover(now)

    def tick(self, now: float) -> None:
        """Advance the player or attract; autoplay when idle long enough. Never raises."""
        try:
            if self._player is None:
                self.attract.tick(now)
                if self.attract.idle_seconds(now) >= self.cfg.attract_autoplay_minutes * 60:
                    pool = eligible(self._entries)
                    if pool:
                        entry = self.rng.choice([pool[s] for s in sorted(pool)])
                        log.info("idle autoplay: %s", entry.slug)
                        self._play_next(now, entry)
                return
            self._player.crowd = len(self._queue) > 0
            for event in self._player.tick(now):
                if event.startswith("cue:"):
                    self._cue(event[4:])
            if self._player.done:
                self._end_current()
                self._play_next(now)
        except Exception:
            log.exception("show tick failed")
            self._recover(now)

    def abort(self, now: float) -> None:
        """Stop the player, clear the queue, attract. Never raises."""
        try:
            self._stop_player()
            self._player = None
            self._current = None
            self._queue.clear()
            self.relight()
            self._to_attract(now)
        except Exception:
            log.exception("abort failed")

    def strip(self, now: float) -> str:
        w = strip_chars(self.cfg)
        notice = self._active_notice(now) if self._current is not None else None
        if w < SHORT_BELOW:
            if self._current is None:
                return ATTRACT_SHORT[int((now - self._attract_t0) // ALTERNATE_S) % 2][:w]
            if notice is not None:
                return notice[:w]
            e = self._current
            texts = wrap_words(f"{e.author}, {e.year}", w) + ["Not A.I."[:w]]  # C54: a long attribution in pieces
            return texts[int((now - self._started) // ALTERNATE_S) % len(texts)]
        if self._current is None:
            return ATTRACT_STRIP[:w]
        e = self._current
        text = f"NOW: {e.title} by {e.author}, {e.year}, Not A.I."
        nxt = self._queue.peek()
        if notice is not None:
            text += f" | {notice}"
        elif nxt is not None:
            text += f" | NEXT: {nxt.title} ({len(self._queue)} queued)"
        return text[:w]

    def strip_visible(self, now: float) -> bool:
        if not self.full_screen:
            return True
        return (now - self._started) % FULL_SCREEN_EVERY_S < FULL_SCREEN_SHOW_S

    def set_entries(self, entries: dict[int, Entry], now: float) -> None:
        """A rescan. Unchanged stations and slugs change nothing but the entries' values; a change rebuilds
        attract keeping the idle clock, and a queued station that is gone is dropped. Never raises."""
        try:
            new = dict(entries)
            changed = {s: e.slug for s, e in new.items()} != {s: e.slug for s, e in self._entries.items()}
            gone = [s for s in self._entries if s not in new]
            self._entries = new
            queued = [e.station for e in self._queue]
            self._queue.clear()
            for station in queued:
                if station in new:
                    self._queue.push(new[station])
            if not changed:
                return
            log.info("entries changed: stations %s", sorted(new))
            for station in gone:
                if self._current is None or self._current.station != station:
                    self._light(station, "off")
            self.relight()
            idle = self.attract.idle_seconds(now)
            self.attract = self._make_attract()
            if self._player is None:
                self.attract.start(now, idle_from=now - idle)
        except Exception:
            log.exception("set_entries failed")
            self._recover(now)

    def relight(self) -> None:
        """The state's light modes again (after lights.all_off()): playing bright, queued pulse, loaded on."""
        queued = {e.station for e in self._queue}
        for station in sorted(self._entries):
            if self._current is not None and self._current.station == station:
                self._light(station, "bright")
            elif station in queued:
                self._light(station, "pulse")
            else:
                self._light(station, "on")
        if self._current is not None and self._current.station not in self._entries:
            self._light(self._current.station, "bright")

    # -- inside --------------------------------------------------------------------------------------------------

    def _make_attract(self) -> Attract:
        return Attract(eligible(self._entries).values(), self._term, self.cfg.attract_lps, rows=self.cfg.rows - 1)

    def _to_attract(self, now: float) -> None:
        self._notice = None
        self._attract_t0 = now
        try:
            self.attract.start(now)
        except Exception:
            log.exception("attract failed to start")

    def _play_next(self, now: float, entry: Entry | None = None) -> bool:
        """Start `entry`, else the next queued, else attract; True when an entry plays."""
        while True:
            if entry is None:
                entry = self._queue.pop()
            if entry is None:
                self._to_attract(now)
                return False
            if self._begin(entry, now):
                return True
            entry = None

    def _begin(self, entry: Entry, now: float) -> bool:
        log.info("playing %s (station %d)", entry.slug, entry.station)
        self._notice = None
        self._current = entry
        self._started = now
        try:
            self._player = self.player_factory(entry, self._term, self.cfg)
            self._player.start(now, len(self._queue) > 0)
        except Exception:
            log.exception("%s: the player failed to start", entry.slug)
            self._end_current()
            return False
        self._light(entry.station, "bright")
        return True

    def _end_current(self) -> None:
        """The current entry is over: its player stopped (guarded), its station back to "on"."""
        entry = self._current
        self._stop_player()
        self._player = None
        self._current = None
        if entry is not None:
            self._light(entry.station, "on" if entry.station in self._entries else "off")

    def _stop_player(self) -> None:
        if self._player is None:
            return
        try:
            self._player.stop()
        except Exception:
            log.exception("stopping the player failed")

    def _recover(self, now: float) -> None:
        """After a raise: the player stopped, the next queued or attract (spec 4.6)."""
        try:
            self._end_current()
            self._play_next(now)
        except Exception:
            log.exception("recovery failed; attract")
            self._player = None
            self._current = None
            self._to_attract(now)

    def _queued_position(self, station: int) -> int | None:
        for i, e in enumerate(self._queue, start=1):
            if e.station == station:
                return i
        return None

    def _active_notice(self, now: float) -> str | None:
        if self._notice is None:
            return None
        text, t = self._notice
        return text if 0.0 <= now - t < NOTICE_S else None

    def _light(self, station: int, mode: str) -> None:
        try:
            self.lights.set(station, mode)
        except Exception:
            log.exception("lights: set %d %s failed", station, mode)

    def _flash(self, station: int, now: float) -> None:
        try:
            self.lights.flash(station, now)
        except Exception:
            log.exception("lights: flash %d failed", station)

    def _cue(self, cue: str) -> None:
        try:
            self.audio.play(cue)
        except Exception:
            log.exception("audio: cue %s failed", cue)
