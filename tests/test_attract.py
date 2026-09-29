import logging

from show.attract import BANNER, BANNER_EVERY, MAX_LINES_PER_TICK, Attract
from show.entries import load_entry
from show.terminal import Terminal
from tests.show_helpers import write_entry


def _text(term):
    return "\n".join(term.screen.display)


def test_attract_scrolls_sources_in_station_order(tmp_path):
    b = load_entry(write_entry(tmp_path, "b", 2, "int b;\n"))
    a = load_entry(write_entry(tmp_path, "a", 1, "int a;\n"))
    term = Terminal()
    attract = Attract([b, a], term, lines_per_second=1.0)
    attract.start(0.0)
    assert "CODE IS ART" in _text(term)
    attract.tick(0.5)
    assert "int a;" not in _text(term)
    attract.tick(3.0)  # 3 lines: blank, header for a, blank
    text = _text(term)
    assert "a -- Created by Test Author, 2026, Not A.I." in text
    attract.tick(4.0)
    assert "int a;" in _text(term)
    assert "int b;" not in _text(term)


def test_attract_wraps_around(tmp_path):
    a = load_entry(write_entry(tmp_path, "a", 1, "int a;\n"))
    term = Terminal()
    attract = Attract([a], term, lines_per_second=100.0)
    attract.start(0.0)
    attract.tick(10.0)  # far more lines than the corpus has
    assert "int a;" in _text(term)


def test_banner_returns_every_40_source_lines(tmp_path):
    src = "".join(f"int v{i};\n" for i in range(100))
    a = load_entry(write_entry(tmp_path, "a", 1, src))
    term = Terminal()
    fed: list[bytes] = []
    term.listeners.append(fed.append)
    attract = Attract([a], term, lines_per_second=1.0)
    attract.start(0.0)
    assert BANNER_EVERY == 40
    assert fed.count(BANNER) == 1
    # 3 header lines + 39 source lines: no second banner yet; the 40th source line brings it
    for n in range(1, 3 + 39 + 1):
        attract.tick(float(n))
    assert fed.count(BANNER) == 1
    attract.tick(float(3 + 40))
    assert fed.count(BANNER) == 2
    for n in range(3 + 41, 3 + 100 + 1):
        attract.tick(float(n))
    assert fed.count(BANNER) == 3  # after lines 40 and 80, not after 100's end


def test_start_resets_a_24_row_terminal_to_23(tmp_path):
    a = load_entry(write_entry(tmp_path, "a", 1, "int a;\n"))
    term = Terminal(rows=24)
    Attract([a], term, lines_per_second=1.0).start(0.0)
    assert term.rows == 23
    assert term.screen.lines == 23


def test_idle_seconds_counts_from_start(tmp_path):
    a = load_entry(write_entry(tmp_path, "a", 1, "int a;\n"))
    attract = Attract([a], Terminal(), lines_per_second=1.0)
    attract.start(100.0)
    assert attract.idle_seconds(100.0) == 0.0
    assert attract.idle_seconds(107.5) == 7.5
    attract.start(200.0)
    assert attract.idle_seconds(201.0) == 1.0


def test_no_entries_shows_the_banner_and_ticks_without_error():
    term = Terminal()
    attract = Attract([], term, lines_per_second=5.0)
    attract.start(0.0)
    attract.tick(50.0)
    assert "CODE IS ART" in _text(term)


def test_an_unreadable_source_is_skipped(tmp_path, caplog):
    gone = load_entry(write_entry(tmp_path, "a", 1, "int gone;\n"))
    other = load_entry(write_entry(tmp_path, "b", 2, "int other;\n"))
    gone.source.unlink()  # loaded fine, unreadable by the time Attract reads it
    term = Terminal()
    with caplog.at_level(logging.ERROR, logger="show.attract"):
        attract = Attract([gone, other], term, lines_per_second=100.0)
    assert any("a" in r.getMessage() and str(gone.source) in r.getMessage() for r in caplog.records)
    attract.start(0.0)
    attract.tick(1.0)
    text = _text(term)
    assert "int other;" in text
    assert "int gone;" not in text


def test_a_late_tick_feeds_at_most_a_screen(tmp_path):
    src = "".join(f"int v{i};\n" for i in range(200))
    a = load_entry(write_entry(tmp_path, "a", 1, src))
    term = Terminal()
    attract = Attract([a], term, lines_per_second=1.0)
    attract.start(0.0)
    fed: list[bytes] = []
    term.listeners.append(fed.append)
    attract.tick(1000.0)
    lines = sum(d.count(b"\n") for d in fed if d != BANNER)
    assert MAX_LINES_PER_TICK == 23
    assert 0 < lines <= 23
    fed.clear()
    attract.tick(1001.0)  # the clock caught up: one line, not a backlog
    assert sum(d.count(b"\n") for d in fed if d != BANNER) == 1
