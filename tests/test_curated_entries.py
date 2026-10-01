"""The entries under entries/ (it16, D5): each loads, keeps its warnings, carries its licence and its sums,
and plays through the pipeline by a fake clock, its program drawing inside the wall's 80 columns.

A play copies the directory into tmp_path (nothing lands in the checkout) and ticks the player with `now`
advancing FAKE_STEP a tick: the typing, the build's timeout and the run's cut follow the fake clock, so a
40 s run takes about 3 real seconds. When RUN begins a witness joins the terminal's listeners: a screen
WITNESS_COLUMNS wide that sees the program's bytes alone, so a line past 80 columns stays on its row.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import time
from dataclasses import dataclass, field, replace
from pathlib import Path

import pyte
import pyte.modes
import pytest

from show.config import Config, load_config
from show.entries import EntryError, load_entries, load_entry
from show.pipeline import EntryPlayer, Phase
from show.terminal import Terminal

ROOT = Path(__file__).resolve().parents[1]
ENTRIES = ROOT / "entries"
DIRS = sorted(p for p in ENTRIES.iterdir() if p.is_dir())
CURATED = [d for d in DIRS if (d / "LICENSE.md").is_file()]
COMMIT = "cb48eb9572c2735a6f12ec56790e014311674a96"   # the archive's ioccc-src/winner at the operator's fetch

FAKE_STEP = 0.2          # fake seconds a tick
TICK = 0.01              # real seconds slept a tick
PLAY_DEADLINE = 8.0      # real seconds a play is given to reach DONE
WITNESS_COLUMNS = 160    # the witness's width: a line past the wall's columns is not wrapped
WALL_COLUMNS = 80
PEAK_LIT_MIN = 100       # non-space cells the program lights at some RUN tick
FINAL_LIT_MIN = 100      # non-space cells the program leaves lit as DWELL begins
REP = re.compile(rb"\x1b\[\d*b")   # REP, "repeat the last character": pyte drops it (review B5)
SUM_LINE = re.compile(r"^([0-9a-f]{64})  (\S+)$", re.MULTILINE)

HAPPY = [Phase.SOURCE, Phase.BUILD, Phase.RUN, Phase.DWELL, Phase.DONE]

needs_cc = pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler")


def slug(d: Path) -> str:
    return d.name


def why_not_loaded(d: Path) -> str:
    try:
        e = load_entry(d)
    except EntryError as exc:
        return str(exc)
    return f"station {e.station} is taken by another directory"


def test_the_entries_directory_loads_whole():
    loaded = sorted(e.slug for e in load_entries(ENTRIES).values())
    missing = {d.name: why_not_loaded(d) for d in DIRS if d.name not in loaded}
    assert loaded == [d.name for d in DIRS], f"skipped by load_entries: {missing}"


def test_every_entry_but_hello_has_a_licence():
    assert {d.name for d in DIRS if not (d / "LICENSE.md").is_file()} == {"hello"}


@pytest.mark.parametrize("entry_dir", DIRS, ids=slug)
def test_entry_build_keeps_its_warnings(entry_dir):
    build = load_entry(entry_dir).build
    words = build.split()
    assert "-Wall" in words, build
    assert "-w" not in words, build
    if entry_dir in CURATED:
        assert "-fsigned-char" in words, build


@pytest.mark.parametrize("entry_dir", CURATED, ids=slug)
def test_curated_sources_match_the_licence_sums(entry_dir):
    text = (entry_dir / "LICENSE.md").read_text()
    summed = []
    for value, name in SUM_LINE.findall(text):
        path = entry_dir / name
        assert path.parent == entry_dir and path.is_file(), f"LICENSE.md sums {name}: not a file of {entry_dir}"
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == value, f"{name}: sha256 {actual}, LICENSE.md says {value}"
        summed.append(path)
    source = load_entry(entry_dir).source
    assert source in summed, f"the source {source.name} is not among the sums {[p.name for p in summed]}"
    assert COMMIT in text
    assert "CC BY-SA 4.0" in text


# ---- the play ----

class Witness(pyte.Screen):
    """The RUN's bytes alone, on a screen WITNESS_COLUMNS wide with LNM, as the show's terminal has.

    It keeps the bytes (a chunk can split an escape) and notes, as text is drawn, the first text that
    reaches x >= WALL_COLUMNS (spaces too: the wall would wrap them) and the first character >= 128. The
    blanks pyte's erase lays to the full width are not the program's cells, so they are not counted.
    """

    def __init__(self, rows: int):
        super().__init__(WITNESS_COLUMNS, rows)
        self.set_mode(pyte.modes.LNM)
        self.run_bytes = bytearray()
        self.past_wall: str | None = None
        self.non_ascii: str | None = None
        self._stream = pyte.ByteStream(self)

    def feed(self, data: bytes) -> None:
        self.run_bytes += data
        self._stream.feed(data)

    def draw(self, data: str) -> None:
        y, x = self.cursor.y, self.cursor.x
        if self.past_wall is None and x + len(data) > WALL_COLUMNS:
            self.past_wall = f"row {y + 1}, columns {x + 1} to {x + len(data)}: {data!r}"
        if self.non_ascii is None and any(ord(c) >= 128 for c in data):
            self.non_ascii = f"row {y + 1}, column {x + 1}: {data!r}"
        super().draw(data)

    def lit(self, rows: int) -> int:
        return sum(1 for line in self.display[:rows] for ch in line if ch != " ")

    def text(self) -> str:
        return "\n".join(line.rstrip() for line in self.display if line.strip()) or "(blank)"


@dataclass
class Play:
    phases: list[Phase] = field(default_factory=list)
    at: dict[Phase, float] = field(default_factory=dict)   # the fake time a phase began
    witness: Witness | None = None
    peak: int = 0               # the most lit cells on the witness after a RUN tick
    final: int | None = None    # the witness's lit cells as DWELL began
    seconds: float = 0.0        # real seconds of the play

    def mark(self, phase: Phase, now: float) -> None:
        self.phases.append(phase)
        self.at[phase] = now


def play_config() -> Config:
    """No frame is rendered: the show's 128x64 config, no build minimum, no dwell, no capture."""
    return replace(load_config(ROOT / "show.poc.toml"), min_build_seconds=0.0, dwell=0.0, capture=False)


def play(entry_dir: Path, tmp_path: Path, cfg: Config) -> tuple[EntryPlayer, Play]:
    copy = tmp_path / entry_dir.name
    shutil.copytree(entry_dir, copy)
    player = EntryPlayer(load_entry(copy), Terminal(cfg.columns, cfg.rows - 1), cfg)
    rec = Play()
    lit_rows = cfg.rows - 1
    now = 0.0
    t0 = time.monotonic()
    try:
        player.start(now)
        rec.mark(player.phase, now)
        while not player.done and time.monotonic() - t0 < PLAY_DEADLINE:
            now += FAKE_STEP
            ticked = player.phase
            player.tick(now)
            if player.phase != rec.phases[-1]:
                rec.mark(player.phase, now)
            if player.phase == Phase.RUN and rec.witness is None:   # after `$ <run>`: the program's bytes alone
                rec.witness = Witness(player.rows)
                player.term.listeners.append(rec.witness.feed)
            if ticked == Phase.RUN:
                lit = rec.witness.lit(lit_rows)
                rec.peak = max(rec.peak, lit)
                if player.phase == Phase.DWELL:
                    rec.final = lit
            time.sleep(TICK)
        rec.seconds = time.monotonic() - t0
    finally:
        player.stop()
    return player, rec


@needs_cc
@pytest.mark.parametrize("entry_dir", DIRS, ids=slug)
def test_entry_plays_through(entry_dir, tmp_path):
    cfg = play_config()
    player, rec = play(entry_dir, tmp_path, cfg)
    print(f"{entry_dir.name}: {rec.seconds:.2f} s real, peak {rec.peak}, final {rec.final}")
    screen = "\n".join(line.rstrip() for line in player.term.screen.display if line.strip())
    assert rec.phases == HAPPY, (
        f"phases {[p.value for p in rec.phases]} after {rec.seconds:.1f} real s (deadline {PLAY_DEADLINE}); "
        f"failure {player.failure!r}; the screen:\n{screen}")
    assert player.failure is None
    assert not any(line.startswith("***") for line in player.term.screen.display), screen
    w = rec.witness
    if entry_dir in CURATED:
        ran = rec.at[Phase.DWELL] - rec.at[Phase.RUN]
        assert ran >= player.run_timeout(), (
            f"RUN ended by itself after {ran:.1f} fake s, before the cut at {player.run_timeout():.1f} "
            f"(exit {player.term.returncode}); the program's screen:\n{w.text()}")
    assert rec.peak >= PEAK_LIT_MIN, (
        f"the program lit at most {rec.peak} cells in RUN (minimum {PEAK_LIT_MIN}); at its end:\n{w.text()}")
    assert rec.final >= FINAL_LIT_MIN, (
        f"the program left {rec.final} cells lit as DWELL began (minimum {FINAL_LIT_MIN}):\n{w.text()}")
    assert w.past_wall is None, f"the program drew past column {WALL_COLUMNS}: {w.past_wall}"
    assert w.non_ascii is None, f"the program drew a character >= 128: {w.non_ascii}"
    rep = REP.search(bytes(w.run_bytes))
    assert rep is None, f"the run sent REP {rep.group()!r}, which pyte drops (review B5)"
