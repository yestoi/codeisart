"""The show's state machine: attract, play, queue, the strip (core Task 12, it12 T-state). Fake clocks, no children."""
import dataclasses
import logging
import random
from pathlib import Path

from show.audio import FakeAudio
from show.config import Config
from show.entries import load_entry
from show.lights import FakeLights
from show.state import (ATTRACT_SHORT, ATTRACT_STRIP, FULL_SCREEN_EVERY_S, FULL_SCREEN_SHOW_S, NOTICE_S, Show,
                        eligible, strip_chars, wrap_words)
from show.terminal import Terminal
from tests.show_helpers import HELLO_C, write_entry

ROOT = Path(__file__).resolve().parents[1]


class FakePlayer:
    """The player protocol Show may use: done, crowd, start(now, crowd), tick(now) -> cues, stop()."""

    def __init__(self, entry, term, cfg, fail=()):
        self.entry, self.term, self.cfg = entry, term, cfg
        self.fail = set(fail)  # any of "start", "tick", "stop"
        self.done = False
        self.crowd = False
        self.started_crowd = None
        self.pending: list[str] = []
        self.stopped = False

    def start(self, now, crowd):
        self.started_crowd = crowd
        self.crowd = crowd
        if "start" in self.fail:
            raise RuntimeError("start failed")
        self.term.reset()
        self.term.feed(f"playing {self.entry.slug}\n".encode())

    def tick(self, now):
        if "tick" in self.fail:
            raise RuntimeError("tick failed")
        ev, self.pending = self.pending, []
        return ev

    def stop(self):
        self.stopped = True
        if "stop" in self.fail:
            raise RuntimeError("stop failed")
        self.done = True


def players(fails: dict[str, set[str]] | None = None):
    """A player factory that keeps every player it made; `fails` maps a slug to what its player raises in."""
    made: list[FakePlayer] = []

    def factory(entry, term, cfg):
        p = FakePlayer(entry, term, cfg, (fails or {}).get(entry.slug, ()))
        made.append(p)
        return p

    factory.made = made
    return factory


class CountingLights(FakeLights):
    def __init__(self):
        super().__init__()
        self.flashes: list[tuple[int, float]] = []

    def flash(self, station, now):
        super().flash(station, now)
        self.flashes.append((station, now))


class BrokenLights(FakeLights):
    def set(self, station, mode):
        raise OSError("gpio gone")

    def flash(self, station, now):
        raise OSError("gpio gone")


def load(tmp_path, slug, station, source=HELLO_C, **kw):
    return load_entry(write_entry(tmp_path, slug, station, source, **kw))


def make_show(tmp_path, cfg, entries=None, factory=None, lights=None, rng=None, start=0.0):
    if entries is None:
        entries = {1: load(tmp_path, "a", 1), 2: load(tmp_path, "b", 2)}
    term, audio = Terminal(), FakeAudio()
    lights = CountingLights() if lights is None else lights
    show = Show(cfg, entries, term, lights, audio, player_factory=factory or players(), rng=rng)
    show.start(start)
    return show, term, lights, audio


def screen(term):
    return "\n".join(term.screen.display)


def finish(show, now):
    show.player.done = True
    show.tick(now)


def ink(cfg):
    return dataclasses.replace(cfg, view="ink", width=128, height=64)


NOW_A = "NOW: a by Test Author, 2026, Not A.I."


# -- the core plan's nine, on strip() ---------------------------------------------------------------------------


def test_start_is_attract_with_lights_on(tmp_path, fast_cfg):
    show, term, lights, audio = make_show(tmp_path, fast_cfg)
    assert not show.playing and show.current is None
    assert lights.modes == {1: "on", 2: "on"}
    assert "CODE IS ART" in screen(term)
    assert show.strip(0.0) == ATTRACT_STRIP


def test_press_starts_immediately_when_idle(tmp_path, fast_cfg):
    show, term, lights, audio = make_show(tmp_path, fast_cfg)
    show.press(1, 1.0)
    assert show.playing and show.current.slug == "a"
    assert lights.modes[1] == "bright"
    assert audio.played == ["keypress"]
    assert "playing a" in screen(term)
    assert show.strip(1.0) == NOW_A + " | PLAYING"
    assert show.strip(1.0 + NOTICE_S) == NOW_A


def test_unknown_station_is_ignored(tmp_path, fast_cfg):
    show, *_ = make_show(tmp_path, fast_cfg)
    show.press(9, 1.0)
    assert not show.playing and len(show.queue) == 0


def test_repeat_press_does_not_restart_or_queue(tmp_path, fast_cfg):
    show, term, lights, audio = make_show(tmp_path, fast_cfg)
    show.press(1, 1.0)
    player = show.player
    show.press(1, 1.5)
    show.press(1, 1.6)
    assert show.player is player and len(show.queue) == 0
    assert audio.played == ["keypress"] * 3
    assert lights.flashes == [(1, 1.0), (1, 1.5), (1, 1.6)]
    assert show.strip(1.6) == NOW_A + " | PLAYING"


def test_second_entry_queues_and_shows_next(tmp_path, fast_cfg):
    show, term, lights, audio = make_show(tmp_path, fast_cfg)
    show.press(1, 1.0)
    show.press(2, 1.1)
    show.press(2, 1.2)
    assert len(show.queue) == 1
    assert lights.modes[2] == "pulse"
    assert audio.played == ["keypress"] * 3
    assert show.strip(1.2) == NOW_A + " | QUEUED #1"
    assert show.strip(1.2 + NOTICE_S) == NOW_A + " | NEXT: b (1 queued)"


def test_cues_are_forwarded_to_audio(tmp_path, fast_cfg):
    show, term, lights, audio = make_show(tmp_path, fast_cfg)
    show.press(1, 1.0)
    show.player.pending = ["cue:compile", "not a cue"]
    show.tick(2.0)
    assert audio.played == ["keypress", "compile"]


def test_finished_player_starts_next_then_attract(tmp_path, fast_cfg):
    show, term, lights, audio = make_show(tmp_path, fast_cfg)
    show.press(1, 1.0)
    show.press(2, 1.1)
    finish(show, 2.0)
    assert show.playing and show.current.slug == "b"
    assert lights.modes == {1: "on", 2: "bright"}
    assert audio.played == ["keypress", "keypress"]  # the next queued starts with no cue
    assert show.strip(2.0) == "NOW: b by Test Author, 2026, Not A.I."  # no NEXT, no stale notice
    finish(show, 3.0)
    assert not show.playing
    assert lights.modes == {1: "on", 2: "on"}
    assert "CODE IS ART" in screen(term)
    assert show.strip(3.0) == ATTRACT_STRIP


def test_abort_stops_player_clears_queue_and_returns_to_attract(tmp_path, fast_cfg):
    show, term, lights, audio = make_show(tmp_path, fast_cfg)
    show.press(1, 1.0)
    show.press(2, 1.1)
    player = show.player
    show.abort(2.0)
    assert player.stopped and not show.playing and len(show.queue) == 0
    assert lights.modes == {1: "on", 2: "on"}
    assert "CODE IS ART" in screen(term)
    assert show.strip(2.0) == ATTRACT_STRIP


def test_tick_in_attract_scrolls_and_leaves_lights_to_the_loop(tmp_path, fast_cfg):
    show, term, lights, audio = make_show(tmp_path, fast_cfg)
    show.tick(5.0)
    assert "int main" in screen(term)
    assert lights.levels == {}  # lights.tick is the loop's, not the show's


# -- presses (spec 4.5) ------------------------------------------------------------------------------------------


def test_press_on_a_queued_station_shows_its_position(tmp_path, fast_cfg):
    entries = {s: load(tmp_path, slug, s) for s, slug in ((1, "a"), (2, "b"), (3, "c"))}
    show, term, lights, audio = make_show(tmp_path, fast_cfg, entries)
    show.press(1, 1.0)
    show.press(2, 1.1)
    show.press(3, 1.2)
    assert show.strip(1.2) == NOW_A + " | QUEUED #2"
    show.press(3, 5.0)
    assert len(show.queue) == 2 and [e.slug for e in show.queue] == ["b", "c"]
    assert show.strip(5.0) == NOW_A + " | QUEUED #2"
    assert show.strip(5.0 + NOTICE_S - 0.1) == NOW_A + " | QUEUED #2"
    assert show.strip(5.0 + NOTICE_S) == NOW_A + " | NEXT: b (2 queued)"
    assert NOTICE_S == 2.0


def test_press_on_an_empty_station_is_acknowledged(tmp_path, fast_cfg):
    show, term, lights, audio = make_show(tmp_path, fast_cfg)
    show.press(4, 1.0)  # Q62: cue and flash, nothing written, nothing queued
    assert audio.played == ["keypress"] and lights.flashes == [(4, 1.0)]
    assert not show.playing and show.strip(1.0) == ATTRACT_STRIP
    show.press(1, 2.0)
    show.press(4, 2.5)
    assert len(show.queue) == 0 and show.strip(2.5) == NOW_A + " | PLAYING"
    assert audio.played == ["keypress"] * 3 and lights.flashes[-1] == (4, 2.5)
    assert 4 not in lights.modes


def test_crowd_is_set_while_the_queue_is_not_empty(tmp_path, fast_cfg):
    entries = {s: load(tmp_path, slug, s) for s, slug in ((1, "a"), (2, "b"), (3, "c"))}
    factory = players()
    show, *_ = make_show(tmp_path, fast_cfg, entries, factory)
    show.press(1, 1.0)
    assert factory.made[0].started_crowd is False
    show.tick(1.1)
    assert show.player.crowd is False
    show.press(2, 1.2)
    show.tick(1.3)
    assert show.player.crowd is True
    show.press(3, 1.4)
    finish(show, 2.0)  # b starts with c still queued
    assert show.current.slug == "b" and factory.made[1].started_crowd is True
    finish(show, 3.0)  # c starts with nothing behind it
    assert show.current.slug == "c" and factory.made[2].started_crowd is False
    show.tick(3.1)
    assert show.player.crowd is False


# -- a raise is logged, the player stopped, the next queued or attract follows (spec 4.6) ------------------------


def test_a_start_that_raises_returns_to_attract(tmp_path, fast_cfg, caplog):
    factory = players({"a": {"start"}})
    show, term, lights, audio = make_show(tmp_path, fast_cfg, factory=factory)
    with caplog.at_level(logging.ERROR, logger="show.state"):
        show.press(1, 1.0)
    assert not show.playing and show.current is None
    assert factory.made[0].stopped
    assert lights.modes == {1: "on", 2: "on"}
    assert "CODE IS ART" in screen(term) and show.strip(1.0) == ATTRACT_STRIP
    assert any("a" in r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR)


def test_a_start_that_raises_moves_to_the_next_queued(tmp_path, fast_cfg):
    entries = {s: load(tmp_path, slug, s) for s, slug in ((1, "a"), (2, "b"), (3, "c"))}
    factory = players({"b": {"start"}})
    show, term, lights, audio = make_show(tmp_path, fast_cfg, entries, factory)
    show.press(1, 1.0)
    show.press(2, 1.1)
    show.press(3, 1.2)
    finish(show, 2.0)
    assert show.playing and show.current.slug == "c" and len(show.queue) == 0
    assert factory.made[1].stopped
    assert lights.modes == {1: "on", 2: "on", 3: "bright"}
    assert "playing c" in screen(term)


def test_a_stop_that_raises_does_not_escape_abort(tmp_path, fast_cfg, caplog):
    factory = players({"a": {"stop"}})
    show, term, lights, audio = make_show(tmp_path, fast_cfg, factory=factory)
    show.press(1, 1.0)
    show.press(2, 1.1)
    with caplog.at_level(logging.ERROR, logger="show.state"):
        show.abort(2.0)
    assert factory.made[0].stopped
    assert not show.playing and len(show.queue) == 0
    assert "CODE IS ART" in screen(term)
    assert any(r.levelno >= logging.ERROR for r in caplog.records)


def test_a_tick_that_raises_returns_to_attract(tmp_path, fast_cfg, caplog):
    factory = players({"a": {"tick"}})
    show, term, lights, audio = make_show(tmp_path, fast_cfg, factory=factory)
    show.press(1, 1.0)
    with caplog.at_level(logging.ERROR, logger="show.state"):
        show.tick(2.0)
    assert factory.made[0].stopped
    assert not show.playing and lights.modes == {1: "on", 2: "on"}
    assert "CODE IS ART" in screen(term)
    assert any(r.levelno >= logging.ERROR for r in caplog.records)
    show.tick(3.0)  # attract goes on
    assert "int main" in screen(term)


def test_a_lights_error_never_aborts_the_show(tmp_path, fast_cfg):
    show, term, lights, audio = make_show(tmp_path, fast_cfg, lights=BrokenLights())
    assert "CODE IS ART" in screen(term)
    show.press(1, 1.0)
    assert show.playing and show.current.slug == "a"
    show.press(2, 1.1)
    assert len(show.queue) == 1 and audio.played == ["keypress", "keypress"]
    show.tick(1.2)
    finish(show, 2.0)
    assert show.playing and show.current.slug == "b"
    show.relight()
    show.abort(3.0)
    assert not show.playing and "CODE IS ART" in screen(term)


# -- idle autoplay and the festival stations (Q56) ---------------------------------------------------------------


def test_idle_autoplay_after_the_configured_minutes(tmp_path, fast_cfg):
    assert fast_cfg.attract_autoplay_minutes == 5.0
    show, term, lights, audio = make_show(tmp_path, fast_cfg, rng=random.Random(1))
    show.tick(299.0)
    assert not show.playing
    show.tick(300.0)
    assert show.playing and show.current.slug in ("a", "b")
    assert audio.played == [] and lights.modes[show.current.station] == "bright"
    finish(show, 310.0)  # attract again, and its idle clock starts over
    show.tick(609.0)
    assert not show.playing
    show.tick(610.0)
    assert show.playing


def test_an_unchanged_rescan_keeps_the_idle_clock(tmp_path, fast_cfg):
    a_dir, b_dir = write_entry(tmp_path, "a", 1, HELLO_C), write_entry(tmp_path, "b", 2, HELLO_C)
    show, term, lights, audio = make_show(tmp_path, fast_cfg, {1: load_entry(a_dir), 2: load_entry(b_dir)})
    attract = show.attract
    for n in range(1, 10):
        if n == 5:
            (a_dir / "fallback.cast").write_text("")  # a captured recording changes the Entry, not its slug
        show.set_entries({1: load_entry(a_dir), 2: load_entry(b_dir)}, 30.0 * n)
        show.tick(30.0 * n)
    assert show.attract is attract
    assert show.entries[1].fallback is not None  # the new values are kept for the next play
    show.tick(299.0)
    assert not show.playing
    show.tick(300.0)
    assert show.playing


def test_autoplay_and_attract_leave_out_stations_above_5(tmp_path, fast_cfg):
    a = load(tmp_path, "a", 1, "int festival_a;\n")
    hello = load(tmp_path, "hello", 6, "int hello_six;\n")
    assert eligible({1: a, 6: hello}) == {1: a}
    assert eligible({6: hello}) == {6: hello}
    term = Terminal()
    for seed in range(50):
        show = Show(fast_cfg, {1: a, 6: hello}, term, FakeLights(), FakeAudio(), player_factory=players(),
                    rng=random.Random(seed))
        show.start(0.0)
        if seed == 0:
            for t in (1.0, 2.0, 3.0):  # the whole corpus, twice over
                show.tick(t)
                assert "hello_six" not in screen(term)
            assert "festival_a" in screen(term)
        show.tick(300.0)
        assert show.current.station == 1
    alone, term, lights, audio = make_show(tmp_path, fast_cfg, {6: hello}, rng=random.Random(0))
    alone.tick(1.0)
    assert "hello_six" in screen(term)
    alone.tick(300.0)
    assert alone.playing and alone.current.station == 6


def test_a_press_on_station_6_still_plays(tmp_path, fast_cfg):
    entries = {1: load(tmp_path, "a", 1), 6: load(tmp_path, "hello", 6)}
    show, term, lights, audio = make_show(tmp_path, fast_cfg, entries)
    show.press(6, 1.0)
    assert show.playing and show.current.station == 6
    assert lights.modes == {1: "on", 6: "bright"}


# -- the strip ---------------------------------------------------------------------------------------------------


def test_strip_while_playing_carries_the_year(tmp_path, fast_cfg):
    show, *_ = make_show(tmp_path, fast_cfg, {1: load(tmp_path, "a", 1, year=1984)})
    show.press(1, 1.0)
    assert show.strip(5.0) == "NOW: a by Test Author, 1984, Not A.I."


def test_strip_is_cut_to_80(tmp_path, fast_cfg):
    long = "x" * 70
    entries = {1: load(tmp_path, long, 1), 2: load(tmp_path, "b", 2)}
    show, *_ = make_show(tmp_path, fast_cfg, entries)
    assert strip_chars(fast_cfg) == 80
    show.press(1, 1.0)
    show.press(2, 1.1)
    for t in (1.1, 5.0):
        s = show.strip(t)
        assert len(s) == 80 and s == (f"NOW: {long} by Test Author, 2026, Not A.I. | "
                                      f"{'QUEUED #1' if t < 3 else 'NEXT: b (1 queued)'}")[:80]


def test_short_strip_alternates_every_3_s(tmp_path, fast_cfg):
    cfg = ink(fast_cfg)
    assert strip_chars(cfg) == 21
    show, *_ = make_show(tmp_path, cfg)
    assert show.strip(0.0) == ATTRACT_SHORT[0] == "PRESS A BUTTON"
    assert show.strip(2.9) == "PRESS A BUTTON"
    assert show.strip(3.0) == ATTRACT_SHORT[1] == "ON ANY PORTRAIT"
    assert show.strip(5.9) == "ON ANY PORTRAIT"
    assert show.strip(6.0) == "PRESS A BUTTON"
    show.press(1, 7.0)
    assert show.strip(7.0) == "PLAYING"  # a notice is the whole strip
    show.press(2, 7.5)
    finish(show, 10.0)  # b starts at 10 from the queue: no notice
    assert show.current.slug == "b"
    for t, want in ((10.0, "Test Author, 2026"), (12.9, "Test Author, 2026"), (13.0, "Not A.I."),
                    (15.9, "Not A.I."), (16.0, "Test Author, 2026")):
        assert show.strip(t) == want, t
    show.press(2, 17.0)
    assert show.strip(17.0) == "PLAYING" and show.strip(18.9) == "PLAYING"
    assert show.strip(19.0) == "Not A.I."
    show.press(1, 20.0)
    assert show.strip(20.0) == "QUEUED #1"
    assert show.strip(22.0) == "Test Author, 2026"
    finish(show, 23.0)
    show.abort(30.0)  # attract's halves count from its own start
    assert show.strip(30.0) == "PRESS A BUTTON" and show.strip(33.0) == "ON ANY PORTRAIT"


def test_short_strip_cuts_each_part_to_the_width(tmp_path, fast_cfg):
    cfg = dataclasses.replace(fast_cfg, columns=10)
    assert strip_chars(cfg) == 10
    show, *_ = make_show(tmp_path, cfg)
    assert show.strip(0.0) == "PRESS A BU" and show.strip(3.0) == "ON ANY POR"
    show.press(1, 1.0)
    assert show.strip(1.0) == "PLAYING"
    assert show.strip(3.0) == "Test" and show.strip(4.0) == "Author," and show.strip(7.0) == "2026"
    assert show.strip(10.0) == "Not A.I." and show.strip(13.0) == "Test"


# -- a long attribution in pieces (C54, Q91) ---------------------------------------------------------------------


def test_wrap_words_keeps_a_text_that_fits_whole():
    assert wrap_words("Test Author, 2026", 21) == ["Test Author, 2026"]
    assert wrap_words("Test Author, 2026", 17) == ["Test Author, 2026"]
    assert wrap_words("a  b", 4) == ["a  b"]  # a text that fits is not re-spaced


def test_wrap_words_breaks_greedily_at_spaces():
    assert wrap_words("Gavin Buttimore and Thaddaeus Frogley, 2000", 21) == [
        "Gavin Buttimore and", "Thaddaeus Frogley,", "2000"]
    assert wrap_words("Test Author, 2026", 10) == ["Test", "Author,", "2026"]
    assert wrap_words("ab cd ef", 5) == ["ab cd", "ef"]  # a piece may fill the width exactly


def test_wrap_words_cuts_a_word_longer_than_the_width():
    assert wrap_words("Supercalifragilistic Smith, 1999", 10) == ["Supercalif", "Smith,", "1999"]
    assert wrap_words("Ab Supercalifragilistic", 10) == ["Ab", "Supercalif"]  # the rest is dropped, not carried


def test_wrap_words_pieces_fit_and_keep_the_words():
    dirs = sorted(d for d in (ROOT / "entries").iterdir() if (d / "entry.toml").is_file())
    texts = [f"{e.author}, {e.year}" for e in map(load_entry, dirs)]
    assert len(texts) >= 6
    for text in texts:
        for width in range(1, 46):
            pieces = wrap_words(text, width)
            assert pieces and all(1 <= len(p) <= width for p in pieces), (text, width, pieces)
            if all(len(word) <= width for word in text.split()):
                assert " ".join(pieces) == " ".join(text.split()), (text, width, pieces)


def test_short_strip_wraps_a_long_attribution(tmp_path, fast_cfg):
    cfg = ink(fast_cfg)
    assert strip_chars(cfg) == 21
    entries = {1: load(tmp_path, "a", 1), 3: load_entry(ROOT / "entries" / "thadgavin")}
    show, *_ = make_show(tmp_path, cfg, entries)
    show.press(1, 1.0)
    show.press(3, 1.5)
    t0 = 10.0
    finish(show, t0)  # thadgavin starts from the queue: no notice
    assert show.current.slug == "thadgavin"
    for dt, want in ((0.0, "Gavin Buttimore and"), (2.9, "Gavin Buttimore and"), (3.0, "Thaddaeus Frogley,"),
                     (6.0, "2000"), (9.0, "Not A.I."), (11.9, "Not A.I."), (12.0, "Gavin Buttimore and")):
        assert show.strip(t0 + dt) == want, dt
    show.press(1, t0 + 13.0)
    assert show.strip(t0 + 13.0) == "QUEUED #1" and show.strip(t0 + 14.9) == "QUEUED #1"
    assert show.strip(t0 + 15.0) == "Thaddaeus Frogley,"  # the cycle counts from the entry's start
    assert all(len(show.strip(t0 + k / 10)) <= 21 for k in range(200))


def test_short_strip_keeps_a_fitting_attribution_in_two_texts(tmp_path, fast_cfg):
    cfg = ink(fast_cfg)
    for slug, attribution in (("sloane", "Andy Sloane, 2006"), ("imc", "Ian Collier, 1992"),
                              ("endoh1", "Yusuke Endoh, 2012"), ("endoh3", "Yusuke Endoh, 2020"),
                              ("hello", "Trey, 2026")):
        entry = load_entry(ROOT / "entries" / slug)
        show, *_ = make_show(tmp_path, cfg, {entry.station: entry})
        show.press(entry.station, 1.0)
        assert show.current.slug == slug
        # two texts, today's strings at today's times: a four-text cycle would give a piece at 7.0
        for t, want in ((3.0, attribution), (4.0, "Not A.I."), (7.0, attribution), (10.0, "Not A.I.")):
            assert show.strip(t) == want, (slug, t)


def test_strip_chars_follows_the_view():
    assert strip_chars(Config()) == 80
    assert strip_chars(Config(columns=40)) == 40
    assert strip_chars(Config(view="ink", width=128, height=64)) == 21
    assert strip_chars(Config(view="ink")) == 512 // 6


def test_full_screen_entry_shows_the_strip_2_s_in_10(tmp_path, fast_cfg):
    assert (FULL_SCREEN_EVERY_S, FULL_SCREEN_SHOW_S) == (10.0, 2.0)
    entries = {1: load(tmp_path, "a", 1, full_screen=True), 2: load(tmp_path, "b", 2)}
    show, *_ = make_show(tmp_path, fast_cfg, entries)
    assert not show.full_screen and show.strip_visible(1.0)
    show.press(1, 5.0)
    assert show.full_screen
    for t, want in ((5.0, True), (6.9, True), (7.0, False), (14.9, False), (15.0, True), (16.9, True),
                    (17.0, False), (25.0, True)):
        assert show.strip_visible(t) is want, t
    show.press(2, 7.5)
    finish(show, 8.0)
    assert show.current.slug == "b" and not show.full_screen
    assert all(show.strip_visible(8.0 + k) for k in range(12))


# -- rescan and relight ------------------------------------------------------------------------------------------


def test_set_entries_rebuilds_attract_and_drops_gone_queued(tmp_path, fast_cfg):
    a, b = load(tmp_path, "a", 1, "int a1;\n"), load(tmp_path, "b", 2, "int b2;\n")
    c, d = load(tmp_path, "c", 3, "int c3;\n"), load(tmp_path, "d", 4, "int d4;\n")
    show, term, lights, audio = make_show(tmp_path, fast_cfg, {1: a, 2: b, 3: c})
    show.press(1, 1.0)
    show.press(2, 1.1)
    show.press(3, 1.2)
    attract = show.attract
    show.set_entries({1: a, 3: c, 4: d}, 5.0)
    assert show.attract is not attract
    assert show.playing and show.current.slug == "a"  # the playing entry plays on
    assert [e.slug for e in show.queue] == ["c"]
    assert show.strip(5.0) == NOW_A + " | NEXT: c (1 queued)"
    assert lights.modes == {1: "bright", 2: "off", 3: "pulse", 4: "on"}
    finish(show, 6.0)
    assert show.current.slug == "c"
    finish(show, 7.0)
    show.tick(8.0)
    text = screen(term)
    assert "int d4;" in text and "int b2;" not in text
    # a change in attract keeps the idle clock
    show.set_entries({1: a, 4: d}, 100.0)
    assert show.attract.idle_seconds(100.0) == 93.0
    assert lights.modes[3] == "off"
    show.tick(306.9)  # idle since attract began at 7.0
    assert not show.playing
    show.tick(307.0)
    assert show.playing


def test_relight_restores_the_modes(tmp_path, fast_cfg):
    entries = {s: load(tmp_path, slug, s) for s, slug in ((1, "a"), (2, "b"), (3, "c"))}
    show, term, lights, audio = make_show(tmp_path, fast_cfg, entries)
    show.press(1, 1.0)
    show.press(2, 1.1)
    lights.all_off()
    assert set(lights.modes.values()) == {"off"}
    show.relight()
    assert lights.modes == {1: "bright", 2: "pulse", 3: "on"}
    show.abort(2.0)
    lights.all_off()
    show.relight()
    assert lights.modes == {1: "on", 2: "on", 3: "on"}
