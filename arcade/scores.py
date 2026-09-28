"""Best-of-the-night scores and the sessions log (spec 7.5). Neither ever raises into a game for a bad file."""
from __future__ import annotations

import json
import logging
import math
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable

from arcade.look import is_real

log = logging.getLogger("arcade")

ROLLOVER_HOUR = 16       # a night runs from 16:00 local time to 16:00 the next day
REASONS = ("done", "left", "inactive", "capped", "exit", "crash")


def night_of(when: datetime) -> date:
    """The night a moment belongs to, named by the date of its evening: 01:00 on the 12th is the 11th's."""
    return (when - timedelta(hours=ROLLOVER_HOUR)).date()


def _finite(value) -> float | None:
    """value as a finite float, else None (NaN, infinity, None, a bool or anything that is not a number). A
    numpy number is a number: games compute scores with numpy."""
    if not is_real(value):
        return None
    try:
        value = float(value)
    except (OverflowError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _entry(raw) -> dict | None:
    """A {"best", "when"} record from the file, or None if it is malformed."""
    if not isinstance(raw, dict) or _finite(raw.get("best")) is None or not isinstance(raw.get("when"), str):
        return None
    try:
        datetime.fromisoformat(raw["when"])
    except ValueError:
        return None
    return {"best": float(raw["best"]), "when": raw["when"]}


def _write_atomic(path: Path, text: str) -> None:
    """Write through a temporary file in the same directory: flush, fsync, then rename over the old file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


class Scores:
    """{game: {layout: {"best", "when"}}} in one JSON file (spec 7.5); higher is better.

    Scores(None) keeps everything in memory and never writes, for tests and tools. Tonight's best rolls over
    at 16:00 local time. An entry replaced by the first record of a new night keeps the old one under
    "previous", so last_night() can show the night before tonight. A missing, unreadable or malformed file
    starts empty with a warning; a write that fails (a read-only or full disk) logs a warning and keeps the
    scores in memory. clock returns local time (datetime.now).
    """

    def __init__(self, path: Path | str | None, clock: Callable[[], datetime] = datetime.now):
        self.path = None if path is None else Path(path)
        self.clock = clock
        self._data: dict[str, dict[str, dict]] = {}
        if self.path is not None:
            self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text())
        except FileNotFoundError:
            return
        except (ValueError, OSError) as e:
            log.warning("ignoring unreadable scores file %s: %s", self.path, e)
            return
        if not isinstance(raw, dict):
            log.warning("ignoring scores file %s: not an object", self.path)
            return
        dropped = 0
        for game, layouts in raw.items():
            for layout, value in (layouts.items() if isinstance(layouts, dict) else ()):
                entry = _entry(value)
                if entry is None:
                    dropped += 1
                    continue
                previous = _entry(value.get("previous"))
                if previous is not None:
                    entry["previous"] = previous
                self._data.setdefault(game, {})[layout] = entry
            dropped += not isinstance(layouts, dict)
        if dropped:
            log.warning("ignoring %d malformed entries in scores file %s", dropped, self.path)

    def for_game(self, name: str, layout: str) -> GameScores:
        """The view a game gets as self.scores."""
        return GameScores(self, name, layout)

    def _tonight(self, entry: dict | None, night: date) -> float | None:
        if entry is None or night_of(datetime.fromisoformat(entry["when"])) != night:
            return None
        return entry["best"]

    def best(self, name: str, layout: str) -> float | None:
        """Tonight's best for this game on this layout, or None."""
        return self._tonight(self._data.get(name, {}).get(layout), night_of(self.clock()))

    def last_night(self, name: str, layout: str) -> float | None:
        """The best of the night before tonight, or None (also when that night had no record)."""
        entry = self._data.get(name, {}).get(layout)
        yesterday = night_of(self.clock()) - timedelta(days=1)
        for candidate in (entry, (entry or {}).get("previous")):
            best = self._tonight(candidate, yesterday)
            if best is not None:
                return best
        return None

    def record(self, name: str, layout: str, value: float, margin: float = 0.0) -> bool:
        """True if value is tonight's new best: the first of the night, or above the best by margin or more
        (strictly above at margin 0). A value that is not a finite number is never a best."""
        if _finite(margin) is None or margin < 0.0:
            raise ValueError(f"margin must be a finite number, 0 or more, got {margin!r}")
        v = _finite(value)
        if v is None:
            log.warning("ignoring score %r for %s %s: not a finite number", value, name, layout)
            return False
        now = self.clock()
        night = night_of(now)
        entry = self._data.get(name, {}).get(layout)
        best = self._tonight(entry, night)
        if best is not None and not (v > best and v >= best + margin):
            return False
        new = {"best": v, "when": now.isoformat()}
        if best is None and entry is not None:
            new["previous"] = {"best": entry["best"], "when": entry["when"]}    # the last night that had one
        elif entry is not None and "previous" in entry:
            new["previous"] = entry["previous"]
        self._data.setdefault(name, {})[layout] = new
        self._save()
        return True

    def _save(self) -> None:
        if self.path is None:
            return
        try:
            _write_atomic(self.path, json.dumps(self._data, indent=1))
        except OSError as e:
            log.warning("could not write scores file %s, keeping scores in memory: %s", self.path, e)


class GameScores:
    """One game's scores on one layout: what a game sees as self.scores (spec 7.1)."""

    def __init__(self, scores: Scores, name: str, layout: str):
        self.scores, self.name, self.layout = scores, name, layout

    def record(self, value: float, margin: float = 0.0) -> bool:
        return self.scores.record(self.name, self.layout, value, margin)

    def best(self) -> float | None:
        return self.scores.best(self.name, self.layout)

    def last_night(self) -> float | None:
        return self.scores.last_night(self.name, self.layout)


class SessionLog:
    """One JSON line per session in data_dir/sessions.jsonl (spec 7.5), appended and fsynced.

    SessionLog(None) keeps the records in memory (records) and never writes. A reason outside REASONS raises
    ValueError (a runner bug); a write that fails logs a warning. A duration or score that is not a finite
    number is written as null.
    """

    def __init__(self, path: Path | str | None):
        self.path = None if path is None else Path(path)
        self.records: list[dict] = []

    def append(self, game: str, layout: str, start: datetime, duration: float, players: int, score: float | None,
               reason: str) -> dict:
        if reason not in REASONS:
            raise ValueError(f"session end reason must be one of {REASONS}, got {reason!r}")
        if not isinstance(start, datetime):
            raise ValueError(f"session start must be a datetime, got {start!r}")
        record = {"game": game, "layout": layout, "start": start.isoformat(), "duration": _finite(duration),
                  "players": players, "score": _finite(score), "reason": reason}
        if self.path is None:
            self.records.append(record)
            return record
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a") as f:
                f.write(json.dumps(record) + "\n")
                f.flush()
                os.fsync(f.fileno())
        except OSError as e:
            log.warning("could not append to sessions log %s: %s", self.path, e)
        return record
