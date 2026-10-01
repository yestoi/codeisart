from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

REQUIRED = ("title", "author", "year", "station", "source", "build", "run")


class EntryError(Exception):
    pass


@dataclass(frozen=True)
class Entry:
    slug: str
    dir: Path
    title: str
    author: str
    year: int
    station: int
    source: Path
    build: str
    run: str
    build_seconds: float = 60.0
    run_seconds: float = 20.0
    fallback: Path | None = None
    full_screen: bool = False
    rows: int | None = None  # the pty's rows in RUN and FALLBACK; None: as today

    @property
    def plaque(self) -> str:
        return f"Created by {self.author}, {self.year}, Not A.I."

    @property
    def fallback_path(self) -> Path:
        return self.dir / "fallback.cast"


def _is_int(v: object) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_number(v: object) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def load_entry(dir: Path) -> Entry:
    toml_path = dir / "entry.toml"
    if not toml_path.is_file():
        raise EntryError(f"{dir}: missing entry.toml")
    try:
        data = tomllib.loads(toml_path.read_text())
    except (tomllib.TOMLDecodeError, UnicodeDecodeError, OSError) as exc:
        raise EntryError(f"{toml_path}: {exc}") from exc
    missing = [k for k in REQUIRED if k not in data]
    if missing:
        raise EntryError(f"{toml_path}: missing keys {missing}")
    for k in ("title", "author", "source", "build", "run"):
        if not isinstance(data[k], str) or not data[k]:
            raise EntryError(f"{toml_path}: {k} must be a non-empty string")
    if not _is_int(data["year"]):
        raise EntryError(f"{toml_path}: year must be an integer")
    if not _is_int(data["station"]) or data["station"] < 1:
        raise EntryError(f"{toml_path}: station must be an integer >= 1")
    seconds = {}
    for k, default in (("build_seconds", 60.0), ("run_seconds", 20.0)):
        v = data.get(k, default)
        if not _is_number(v) or v <= 0:
            raise EntryError(f"{toml_path}: {k} must be a number > 0")
        seconds[k] = float(v)
    full_screen = data.get("full_screen", False)
    if not isinstance(full_screen, bool):
        raise EntryError(f"{toml_path}: full_screen must be true or false")
    rows = data.get("rows")
    if rows is not None and (not _is_int(rows) or rows < 1):
        raise EntryError(f"{toml_path}: rows must be an integer >= 1")
    source = dir / data["source"]
    if not source.is_file():
        raise EntryError(f"{toml_path}: source {source} does not exist")
    fallback = dir / "fallback.cast"
    return Entry(
        slug=dir.name, dir=dir, title=data["title"], author=data["author"],
        year=data["year"], station=data["station"], source=source,
        build=data["build"], run=data["run"],
        build_seconds=seconds["build_seconds"], run_seconds=seconds["run_seconds"],
        fallback=fallback if fallback.is_file() else None,
        full_screen=full_screen, rows=rows,
    )


def load_entries(root: Path) -> dict[int, Entry]:
    if not root.is_dir():
        raise EntryError(f"{root}: not a directory")
    entries: dict[int, Entry] = {}
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        try:
            e = load_entry(d)
        except EntryError as exc:
            log.error("skipping %s: %s", d, exc)
            continue
        if e.station in entries:
            log.error("skipping %s: station %d already used by %s",
                      d, e.station, entries[e.station].slug)
            continue
        entries[e.station] = e
    if not entries:
        raise EntryError(f"no valid entries in {root}")
    return entries


def rescan(root: Path, current: dict[int, Entry]) -> dict[int, Entry]:
    try:
        return load_entries(root)
    except Exception as exc:  # never raises: the show keeps what it has
        log.error("rescan of %s failed, keeping current entries: %s", root, exc)
        return current
