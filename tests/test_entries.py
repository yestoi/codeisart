import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from show.entries import REQUIRED, Entry, EntryError, load_entries, load_entry, rescan
from tests.show_helpers import HELLO_C, write_entry


def test_entry_loads_with_its_plaque(tmp_path):
    d = write_entry(tmp_path, "a", 1, HELLO_C)
    e = load_entry(d)
    assert e.slug == "a" and e.station == 1 and e.year == 2026
    assert e.plaque == "Created by Test Author, 2026, Not A.I."
    assert e.source == d / "prog.c"
    assert e.fallback is None
    assert e.fallback_path == d / "fallback.cast"
    assert e.run_seconds == 5.0 and e.build_seconds == 30.0


def test_fallback_detected_when_present(tmp_path):
    d = write_entry(tmp_path, "a", 1, HELLO_C, fallback="{}\n")
    assert load_entry(d).fallback == d / "fallback.cast"


def test_missing_toml_is_an_error(tmp_path):
    (tmp_path / "bad").mkdir()
    with pytest.raises(EntryError):
        load_entry(tmp_path / "bad")


def test_bad_toml_is_an_error(tmp_path):
    d = write_entry(tmp_path, "a", 1, HELLO_C)
    (d / "entry.toml").write_text("title = = nope\n")
    with pytest.raises(EntryError):
        load_entry(d)


def test_missing_source_is_an_error(tmp_path):
    d = write_entry(tmp_path, "a", 1, HELLO_C)
    (d / "prog.c").unlink()
    with pytest.raises(EntryError):
        load_entry(d)


@pytest.mark.parametrize("key", REQUIRED)
def test_missing_key_is_an_error(tmp_path, key):
    d = write_entry(tmp_path, "a", 1, HELLO_C)
    lines = (d / "entry.toml").read_text().splitlines()
    (d / "entry.toml").write_text("\n".join(l for l in lines if not l.startswith(key + " ")) + "\n")
    with pytest.raises(EntryError, match=key):
        load_entry(d)


def _set(d, key, value):
    lines = (d / "entry.toml").read_text().splitlines()
    lines = [l for l in lines if not l.startswith(key + " ")] + [f"{key} = {value}"]
    (d / "entry.toml").write_text("\n".join(lines) + "\n")


@pytest.mark.parametrize("bad", ["0", "-1", "true", "1.5", '"2"'])
def test_station_must_be_an_integer_of_at_least_one(tmp_path, bad):
    d = write_entry(tmp_path, "a", 1, HELLO_C)
    _set(d, "station", bad)
    with pytest.raises(EntryError):
        load_entry(d)


def test_station_six_and_up_loads(tmp_path):
    d = write_entry(tmp_path, "a", 6, HELLO_C)
    assert load_entry(d).station == 6


@pytest.mark.parametrize("key", ["run_seconds", "build_seconds"])
@pytest.mark.parametrize("bad", ["0", "-3", "true", '"5"'])
def test_seconds_must_be_positive_numbers(tmp_path, key, bad):
    d = write_entry(tmp_path, "a", 1, HELLO_C)
    _set(d, key, bad)
    with pytest.raises(EntryError):
        load_entry(d)


def test_year_must_be_an_integer(tmp_path):
    d = write_entry(tmp_path, "a", 1, HELLO_C)
    _set(d, "year", '"2026"')
    with pytest.raises(EntryError):
        load_entry(d)


def test_full_screen_defaults_false_and_reads_true(tmp_path):
    assert load_entry(write_entry(tmp_path, "a", 1, HELLO_C)).full_screen is False
    assert load_entry(write_entry(tmp_path, "b", 2, HELLO_C, full_screen=True)).full_screen is True
    assert load_entry(write_entry(tmp_path, "c", 3, HELLO_C, full_screen=False)).full_screen is False


@pytest.mark.parametrize("bad", ["1", '"yes"', "1.0"])
def test_full_screen_must_be_a_bool(tmp_path, bad):
    d = write_entry(tmp_path, "a", 1, HELLO_C)
    _set(d, "full_screen", bad)
    with pytest.raises(EntryError):
        load_entry(d)


def test_rows_defaults_none_and_reads_an_integer(tmp_path):
    assert load_entry(write_entry(tmp_path, "a", 1, HELLO_C)).rows is None
    assert load_entry(write_entry(tmp_path, "b", 2, HELLO_C, rows=24)).rows == 24
    assert load_entry(write_entry(tmp_path, "c", 3, HELLO_C, rows=1)).rows == 1


@pytest.mark.parametrize("bad", ["0", "-1", "true", "23.5", '"24"'])
def test_rows_must_be_an_integer_of_at_least_one(tmp_path, bad):
    d = write_entry(tmp_path, "a", 1, HELLO_C)
    _set(d, "rows", bad)
    with pytest.raises(EntryError, match="rows must be an integer >= 1"):
        load_entry(d)


def test_load_entries_skips_bad_and_duplicate_stations(tmp_path, caplog):
    write_entry(tmp_path, "a", 1, HELLO_C)
    write_entry(tmp_path, "b", 2, HELLO_C)
    write_entry(tmp_path, "c", 2, HELLO_C)          # duplicate station
    (tmp_path / "d").mkdir()                        # no entry.toml
    entries = load_entries(tmp_path)
    assert sorted(entries) == [1, 2]
    assert entries[2].slug == "b"
    assert "skipping" in caplog.text


def test_no_entries_raises(tmp_path):
    with pytest.raises(EntryError):
        load_entries(tmp_path)


def test_missing_root_raises_entry_error(tmp_path):
    with pytest.raises(EntryError):
        load_entries(tmp_path / "nope")


def test_entries_are_hashable_and_equal_by_value(tmp_path):
    d = write_entry(tmp_path, "a", 1, HELLO_C)
    e1, e2 = load_entry(d), load_entry(d)
    assert e1 is not e2 and e1 == e2
    assert len({e1, e2}) == 1
    assert isinstance(e1, Entry)


def test_rescan_picks_up_a_new_entry(tmp_path):
    write_entry(tmp_path, "a", 1, HELLO_C)
    current = load_entries(tmp_path)
    write_entry(tmp_path, "b", 2, HELLO_C)
    fresh = rescan(tmp_path, current)
    assert sorted(fresh) == [1, 2]
    assert sorted(current) == [1]


def test_rescan_keeps_current_when_the_directory_is_empty_or_gone(tmp_path):
    write_entry(tmp_path, "a", 1, HELLO_C)
    current = load_entries(tmp_path)
    empty = tmp_path / "empty"
    empty.mkdir()
    assert rescan(empty, current) is current
    assert rescan(tmp_path / "gone", current) is current


# ---- the sample entry entries/hello (T-hello) ----

HELLO_DIR = Path(__file__).resolve().parents[1] / "entries" / "hello"
NEEDS_CC = pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler")


def test_sample_entry_loads():
    e = load_entry(HELLO_DIR)
    assert e.slug == "hello"
    assert e.station == 6
    assert e.plaque == "Created by Trey, 2026, Not A.I."
    assert e.fallback is None
    assert e.full_screen is False
    words = e.build.split()
    assert "-Wall" in words
    assert "-w" not in words


def _built_copy(tmp_path):
    dst = tmp_path / "hello"
    shutil.copytree(HELLO_DIR, dst)
    entry = load_entry(dst)
    env = {**os.environ, "LC_ALL": "C"}
    proc = subprocess.run(entry.build, shell=True, cwd=dst, env=env,
                          capture_output=True, text=True, timeout=30)
    return entry, dst, proc


@NEEDS_CC
def test_sample_entry_builds_with_one_warning(tmp_path):
    entry, dst, proc = _built_copy(tmp_path)
    print("build stderr:", proc.stderr)
    assert proc.returncode == 0
    warnings = [ln for ln in proc.stderr.splitlines() if "warning:" in ln]
    assert len(warnings) == 1, warnings
    print("warning line:", warnings[0])
    assert "unused variable" in warnings[0]
    assert "-Wunused-variable" in warnings[0]


@NEEDS_CC
def test_sample_entry_runs_with_large_motion(tmp_path):
    entry, dst, proc = _built_copy(tmp_path)
    assert proc.returncode == 0, proc.stderr
    env = {**os.environ, "LINES": "23", "COLUMNS": "80"}
    t0 = time.monotonic()
    run = subprocess.run(entry.run, shell=True, cwd=dst, env=env,
                         stdin=subprocess.DEVNULL, capture_output=True,
                         text=True, timeout=entry.run_seconds)
    secs = time.monotonic() - t0
    assert run.returncode == 0
    assert secs < entry.run_seconds
    assert run.stdout.rstrip().endswith("hello, world")
    frames = [f for f in run.stdout.split("\x1b[H") if "#" in f]
    cols = []
    for f in frames:
        first = next(r for r in f.split("\n") if "#" in r)
        cols.append(first.index("#"))
    print(f"run {secs:.2f}s, frames {len(frames)}, band columns {min(cols)}..{max(cols)}")
    assert len(frames) >= 40
    assert max(cols) - min(cols) >= 20
    assert not re.search(r"[^\x20-\x7e\n\x1b]", run.stdout)


@NEEDS_CC
def test_sample_entry_band_leaves_no_trail(tmp_path):
    import pyte

    entry, dst, proc = _built_copy(tmp_path)
    assert proc.returncode == 0, proc.stderr
    env = {**os.environ, "LINES": "23", "COLUMNS": "80", "LC_ALL": "C"}
    run = subprocess.run(entry.run, shell=True, cwd=dst, env=env,
                         stdin=subprocess.DEVNULL, capture_output=True,
                         text=True, timeout=entry.run_seconds)
    assert run.returncode == 0
    pieces = run.stdout.split("\x1b[H")
    frames = [p.split("\x1b[2J")[0] for p in pieces[1:] if "#" in p]
    assert len(frames) >= 40
    screen = pyte.Screen(80, 23)
    stream = pyte.Stream(screen)
    stream.feed(pieces[0])
    worst = (0, -1)
    broken = 0   # rows that are not one band of at most 6 '#', over all frames
    for n, frame in enumerate(frames):
        # a tty turns \n into \r\n (onlcr); pyte does not, so do it here
        stream.feed("\x1b[H" + frame.replace("\n", "\r\n"))
        for row in screen.display:
            body = row.strip(" ")
            count = body.count("#")
            if count > worst[0]:
                worst = (count, n)
            if count and not (count <= 6 and body == "#" * count):
                broken += 1
    print(f"frames {len(frames)}, worst row {worst[0]} '#' in frame {worst[1]}")
    assert worst[0] <= 6 and broken == 0, (
        f"a row holds {worst[0]} '#' in frame {worst[1]}; {broken} rows "
        "are not one contiguous band of 6")


def test_sample_entry_lines_fit_the_wall():
    lines = (HELLO_DIR / "hello.c").read_text().splitlines()
    long = [(n, len(ln)) for n, ln in enumerate(lines, 1) if len(ln) > 80]
    assert long == [], f"lines longer than 80 characters (line, length): {long}"
