import dataclasses
import logging
import json
import math
import random
import zlib
from datetime import datetime

import numpy as np
import pytest

from arcade.calibration import Calibration
from arcade.canvas import Canvas
from arcade.flash import flash_area
from arcade.game import RUNNER_KEYS
from arcade.headless import OPENING_NIGHT, RecordingDisplay
from arcade.input import capture_grace
from arcade.juice import Juice
from arcade.runner import CLOCK_SLACK, CRASH_RED, CRASH_SECONDS, MAX_DT, PROMPT_SECONDS, RING, Runner, SessionResult
from arcade.scores import GameScores, SessionLog
from arcade.sensed import Audio, Blob, Sensed, place_blob
from arcade.sources.actors import REAL_NOISE, TICK, Person, crowd, degrade, moving_blob, scene
from tests.arcade.helpers import CROSS_ICON, FakeClock, SpyGame, StubLobby, make_cfg, spy

SIZE = (64, 64)
WHITE = (255, 255, 255)
LAMP = lambda t: Blob(0.5, 0.5, 0.02, (255, 200, 0))             # parked in the zone


def make_runner(font, games=(SpyGame,), lobby=None, display=None, cfg=None, **kw):
    cfg = cfg or make_cfg(SIZE)
    display = display or RecordingDisplay()
    lobby = lobby or StubLobby()
    kw = {"seed": 1, "local_clock": lambda: OPENING_NIGHT} | kw
    return Runner(cfg, display, font, lobby, list(games), **kw), display, lobby


def feed(runner, frames, dt=TICK):
    for s in frames:
        runner.tick(s, dt)


def ticks(seconds):
    return round(seconds / TICK)


def stand(**kw):
    """One person standing in the zone for the whole scene."""
    return scene(persons=[Person(id=1)], **kw)


class Strobe(SpyGame):
    """The whole wall white and black on alternate ticks."""

    info = spy("strobe").info

    def draw(self, canvas):
        canvas.clear(WHITE if self.draws % 2 else (0, 0, 0))
        self.draws += 1


class Smear(SpyGame):
    """Paints the whole wall, then raises: a crash in draw must leave only the icon."""

    def draw(self, canvas):
        canvas.clear(WHITE)
        raise RuntimeError("boom in draw")


def test_starts_in_lobby_and_sets_brightness(font5x7):
    runner, display, lobby = make_runner(font5x7, cfg=make_cfg(SIZE, brightness=0.25))
    assert runner.current is lobby and display.brightness == 0.25 and lobby.resets == 1
    assert lobby.available == {"spy"} and runner.game is None
    feed(runner, scene(ticks=2))
    assert display.count == 2 and lobby.updates == 2
    state = runner.state()
    assert state["game"] == "lobby" and state["request"] is None and state["attract"] is True
    assert display.last[0, 1].tolist() == [0, 255, 0]                 # the lobby drew


def test_lobby_request_launches_next_tick(font5x7, caplog):
    runner, display, lobby = make_runner(font5x7)
    lobby.request = "spy"
    feed(runner, scene(ticks=1))
    assert runner.current_name == "spy" and isinstance(runner.game, SpyGame) and lobby.request is None
    assert runner.game.size == SIZE and runner.game.updates == 0
    feed(runner, scene(ticks=1))
    assert runner.game.updates == 1 and runner.state()["updates"] == 1 and runner.state()["game"] == "spy"
    runner.end_session("exit")
    lobby.request = "nope"
    with caplog.at_level(logging.WARNING, logger="arcade"):
        feed(runner, scene(ticks=1))
    assert runner.current_name == "lobby" and "nope" in caplog.text


def test_scores_view_and_fx_given_before_reset(font5x7):
    runner, _, _ = make_runner(font5x7)
    assert runner.launch("spy")
    game = runner.game
    assert isinstance(game.scores_at_reset, GameScores)
    assert (game.scores.name, game.scores.layout) == ("spy", "64x64") and isinstance(game.fx, Juice)
    first = game.rng.random()
    again, _, _ = make_runner(font5x7)
    again.launch("spy")
    assert again.game.rng.random() == first                          # seeded: the same seed, the same launch
    again.launch("spy")
    assert again.game.rng.random() != first                          # a second launch is another run
    assert first == pytest.approx(random.Random(zlib.crc32(b"1:spy:1")).random())


def test_done_returns_to_lobby_with_result(font5x7):
    sessions = SessionLog(None)
    done = spy(finish_after=3, extra={"score": np.int64(7)})
    runner, display, lobby = make_runner(font5x7, games=(done,), sessions=sessions)
    runner.launch("spy")
    feed(runner, stand(ticks=2))
    assert runner.current_name == "spy"
    feed(runner, stand(ticks=1))
    assert runner.current is lobby and runner.game.updates == 3      # the launched instance is kept
    (result,) = lobby.results
    assert isinstance(result, SessionResult)
    assert (result.game, result.layout, result.reason, result.score, result.players) == ("spy", "64x64", "done", 7,
                                                                                         1)
    assert result.duration == pytest.approx(3 * TICK) and result.best is None and result.waiting is False
    record = sessions.records[0]
    assert record["reason"] == "done" and record["score"] == 7.0 and record["start"] == "2026-11-11T21:00:00"


@pytest.mark.parametrize("where", ["init", "reset", "update", "draw", "done", "debug_state"])
def test_init_reset_and_done_raises_are_guarded(font5x7, where, caplog):
    sessions = SessionLog(None)
    runner, display, lobby = make_runner(font5x7, games=(spy(raise_in=frozenset({where})),), sessions=sessions)
    with caplog.at_level(logging.ERROR, logger="arcade"):
        started = runner.launch("spy")
        feed(runner, stand(ticks=1))
    assert started is (where not in ("init", "reset"))
    assert runner.crashes == {"spy": 1} and f"boom in {where}" in runner.last_error
    assert "game spy crashed" in caplog.text and sessions.records[-1]["reason"] == "crash"
    assert lobby.results[-1].reason == "crash"
    feed(runner, stand(ticks=ticks(CRASH_SECONDS) + 1))
    assert runner.current is lobby and runner.state()["glitch"] is False


@pytest.mark.parametrize("game", [spy(raise_in=frozenset({"update"})), Smear], ids=["update", "draw"])
def test_crash_shows_static_dim_icon_then_lobby(font5x7, game):
    assert CRASH_SECONDS == 0.5 and CRASH_RED == (96, 0, 0)            # loop decision 17
    runner, display, lobby = make_runner(font5x7, games=(game,))
    runner.launch("spy")
    feed(runner, stand(ticks=1))
    assert runner.state()["glitch"] is True and runner.state()["game"] == "spy"
    frames = [display.last]
    while runner.state()["glitch"]:
        feed(runner, stand(ticks=1))
        frames.append(display.last)
    assert len(frames) == ticks(CRASH_SECONDS) + 1
    lit = frames[0].any(axis=2)
    assert lit.sum() == CROSS_ICON.sum() and frames[0][..., 1:].max() == 0   # only the icon, never half a frame
    assert frames[0][lit, 0].max() == CRASH_RED[0]                     # dim: 96 at most
    reds = [int(f[..., 0].max()) for f in frames[:-1]]
    assert reds == sorted(reds, reverse=True) and reds[-1] < 40        # one slow fade, never a strobe
    assert all(np.array_equal(f.any(axis=2), lit) for f in frames[:-1] if f.any())   # static: the same pixels
    assert frames[-1][0, 1].tolist() == [0, 255, 0]                    # then the lobby


def test_crash_hides_after_three(font5x7):
    runner, display, lobby = make_runner(font5x7, games=(spy(raise_in=frozenset({"draw"})), spy("paint")))
    for n in range(1, 4):
        lobby.request = "spy"
        feed(runner, stand(ticks=2 + ticks(CRASH_SECONDS)))
        assert runner.crashes["spy"] == n and runner.current is lobby
    assert runner.hidden == {"spy"} and lobby.available == {"paint"} and runner.state()["hidden"] == ["spy"]
    lobby.request = "spy"
    feed(runner, stand(ticks=2))
    assert runner.current is lobby and runner.crashes["spy"] == 3
    lobby.request = "paint"
    feed(runner, stand(ticks=1))
    assert runner.current_name == "paint"


def test_crash_icon_has_no_game_keys_and_the_log_keeps_the_last_score(font5x7):
    # Loop decisions 16 and 24: the lobby's result and the session log carry the last score the game reported,
    # and state() during the icon has none of the game's keys. A crash at launch reports no score, never a key
    # of the lobby's.
    class Late(SpyGame):
        extra = {"score": 5}

        def update(self, sensed, dt):
            super().update(sensed, dt)
            if self.updates == 3:
                raise RuntimeError("late")

    sessions = SessionLog(None)
    broken = spy("broken", raise_in=frozenset({"reset"}))
    runner, _, lobby = make_runner(font5x7, games=(Late, broken), sessions=sessions)
    runner.launch("spy")
    feed(runner, stand(ticks=3))
    state = runner.state()
    assert state["glitch"] is True and "score" not in state and "updates" not in state
    assert lobby.results[-1].score == 5 and sessions.records[-1]["score"] == 5.0
    feed(runner, stand(ticks=ticks(CRASH_SECONDS) + 1))
    lobby.debug_state = lambda: {"request": None, "score": 99}
    feed(runner, stand(ticks=1))
    assert runner.state()["score"] == 99                               # the lobby's own key
    assert not runner.launch("broken")
    assert lobby.results[-1].score is None and sessions.records[-1]["score"] is None


def test_strict_reraises(font5x7):
    runner, _, _ = make_runner(font5x7, games=(spy(raise_in=frozenset({"update"})),), strict=True)
    runner.launch("spy")
    with pytest.raises(RuntimeError, match="boom in update"):
        feed(runner, stand(ticks=1))
    runner, _, _ = make_runner(font5x7, games=(spy(raise_in=frozenset({"init"})),), strict=True)
    with pytest.raises(RuntimeError, match="boom in init"):
        runner.launch("spy")
    runner, _, _ = make_runner(font5x7, lobby=StubLobby(raise_in=frozenset({"update"})), strict=True)
    with pytest.raises(RuntimeError, match="lobby boom"):
        feed(runner, scene(ticks=1))


def test_last_error_holds_traceback(font5x7):
    runner, _, _ = make_runner(font5x7, games=(spy(raise_in=frozenset({"draw"})),))
    assert runner.last_error is None
    runner.launch("spy")
    feed(runner, stand(ticks=1))
    assert runner.last_error.startswith("Traceback (most recent call last)")
    assert "RuntimeError: boom in draw" in runner.last_error and "def draw" not in runner.last_error


def test_lobby_crash_falls_back_to_title_card(font5x7, caplog):
    lobby = StubLobby(raise_in=frozenset({"update"}))
    runner, display, _ = make_runner(font5x7, lobby=lobby)
    with caplog.at_level(logging.ERROR, logger="arcade"):
        feed(runner, scene(ticks=3))
    assert lobby.updates == 1 and "lobby boom" in runner.last_error and "title card" in caplog.text
    assert runner.state()["title_card"] is True and runner.state()["game"] == "lobby"
    assert display.last.any() and display.last[0, 1].tolist() == [0, 0, 0]   # the card, not the lobby
    runner.launch("spy")
    feed(runner, stand(ticks=2))
    runner.end_session("exit")
    feed(runner, scene(ticks=1))
    assert runner.state()["title_card"] is True and runner.hidden == set()   # the lobby is never hidden
    assert lobby.updates == 1 and lobby.results == []                  # the broken lobby is never called again


def test_state_runner_keys_win(font5x7):
    greedy = spy(extra={"t": "mine", "present": "mine", "fx_shake": "mine", "phase": "play", "crashes": "mine"})
    runner, _, _ = make_runner(font5x7, games=(greedy,))
    runner.launch("spy")
    feed(runner, stand(ticks=40))
    state = runner.state()
    assert set(RUNNER_KEYS) <= set(state)
    assert state["t"] == pytest.approx(40 * TICK, abs=1e-3) and state["present"] is True and state["crashes"] == {}
    assert state["fx_shake"] == [0, 0] and state["phase"] == "play" and state["updates"] == 40
    assert state["player"] == 1 and state["glitch"] is False and state["flash_held_ticks"] == 0
    assert state["attract"] is False and state["idle"] == 0.0 and state["game"] == "spy"


def test_fx_keys_in_runner_state(font5x7):
    class Bursting(SpyGame):
        def update(self, sensed, dt):
            super().update(sensed, dt)
            if self.updates == 1:
                self.fx.burst(32, 32, WHITE)

    runner, display, lobby = make_runner(font5x7, games=(Bursting,))
    feed(runner, scene(ticks=1))
    assert not any(k.startswith("fx_") for k in runner.state())       # the lobby has no effects
    runner.launch("spy")
    feed(runner, stand(ticks=1))
    state = runner.state()
    assert state["fx_particles"] == 12 and {"fx_shake", "fx_frozen", "fx_flash", "fx_banner"} <= set(state)
    assert display.last.any(axis=2).sum() > 1                          # the particles reached the wall


def test_freeze_skips_the_games_update(font5x7):
    class Freezing(SpyGame):
        def update(self, sensed, dt):
            super().update(sensed, dt)
            if self.updates == 1:
                self.fx.freeze(0.2)

    runner, _, _ = make_runner(font5x7, games=(Freezing,))
    runner.launch("spy")
    counts = []
    for s in stand(ticks=10):
        runner.tick(s, TICK)
        counts.append((runner.game.updates, runner.game.draws, runner.state()["fx_frozen"]))
    assert [c[0] for c in counts] == [1, 1, 1, 1, 1, 1, 2, 3, 4, 5]    # six ticks frozen: no update
    assert [c[1] for c in counts] == list(range(1, 11))               # drawn every tick
    assert counts[0][2] is True and counts[-1][2] is False


def test_the_game_shakes_and_the_overlays_do_not(font5x7):
    # The tick order: the game draws, Juice renders (its shake moves the game's picture), then the overlays, so
    # the exit ring is drawn where the player is and never shakes.
    class Shaken(SpyGame):
        def update(self, sensed, dt):
            super().update(sensed, dt)
            if self.updates == 1:
                self.fx.shake(8, 6.0)

        def draw(self, canvas):
            canvas.pixel(32, 20, WHITE)

    runner, display, _ = make_runner(font5x7, games=(Shaken,))
    runner.launch("spy")
    checked = 0
    for s in scene(persons=[Person(id=1).both_hands_up(at=0.0, seconds=2.5)], ticks=ticks(2.5)):
        runner.tick(s, TICK)
        dx, dy = runner.state()["fx_shake"]
        progress = runner._exit.progress
        if not (dx or dy) or progress == 0.0:
            continue
        ring = Canvas(*SIZE, font5x7)
        ring.circle(runner.player.zone_x * (SIZE[0] - 1), SIZE[1] / 2,
                    (1.0 - progress) * (min(SIZE) / 2 - 2) + 1, RING)
        drawn = ring.frame.any(axis=2)
        assert np.array_equal(np.all(display.last == RING, axis=2), drawn)          # the ring, unshaken
        if not drawn[20 + dy, 32 + dx]:
            assert np.argwhere(np.all(display.last == WHITE, axis=2)).tolist() == [[20 + dy, 32 + dx]]   # shaken
            checked += 1
    assert checked > ticks(1.0)


def test_governor_and_limiter_are_built_from_the_runners_settings(font5x7):
    # it04 B4: the governor counts a second at cfg.fps, so at 60 ticks a second a strobe still shows at most 3
    # flashes a second; the limiter reads the lux callable the runner was given.
    lux = lambda: 500.0
    runner, display, _ = make_runner(font5x7, games=(Strobe,), cfg=make_cfg(SIZE, fps=60), lux=lux)
    assert runner.governor.fps == 60 and runner.limiter.lux is lux
    runner.launch("strobe")
    feed(runner, stand(ticks=120), dt=1 / 60)
    assert flash_area(display.frames, fps=60) == 0.0 and runner.governor.held_ticks > 0


def test_crowd_of_six_never_steals_the_player(font5x7):
    runner, _, _ = make_runner(font5x7)
    runner.launch("spy")
    frames = degrade(scene(persons=[Person(x=0.5, id=1)] + crowd(6), ticks=ticks(6.0)), **REAL_NOISE)
    ids = []
    for s in frames:
        runner.tick(s, TICK)
        ids.append(runner.state()["player"])
    assert set(ids[ticks(0.2):]) == {1}                               # after the camera's first capture
    assert runner.player2 is None                                     # the crowd is out of the zone


def test_player_switches_after_1_3x_for_one_second(font5x7):
    runner, _, _ = make_runner(font5x7)
    small = Person(x=0.35, height=0.5, id=1)
    big = Person(x=0.65, height=0.7, id=2).arrive(1.0)                # 1.4 times the scale
    ids = []
    for s in scene(persons=[small, big], ticks=ticks(3.0)):
        runner.tick(s, TICK)
        ids.append((runner.player.id, None if runner.player2 is None else runner.player2.id))
    switch = ids.index((2, 1))
    assert set(ids[:ticks(1.0)]) == {(1, None)} and set(ids[ticks(1.0):switch]) == {(1, 2)}
    assert switch == ticks(2.0) and set(ids[switch:]) == {(2, 1)}      # one second after the rival came
    runner, _, _ = make_runner(font5x7)
    close = Person(x=0.65, height=0.6, id=2).arrive(1.0)              # 1.2 times: never switches
    feed(runner, scene(persons=[Person(x=0.35, height=0.5, id=1), close], ticks=ticks(4.0)))
    assert runner.player.id == 1 and runner.player2.id == 2


def test_player_reacquired_by_position_keeps_slot(font5x7):
    runner, _, _ = make_runner(font5x7)
    lost = Person(x=0.4, height=0.7, id=1).leave(1.0)
    other = Person(x=0.75, height=0.5, id=3)                          # in the zone all along, smaller
    far = Person(x=0.2, height=0.7, id=8).arrive(1.05)                # new, but a third of the zone away
    back = Person(x=0.42, height=0.7, id=7).arrive(1.25)              # re-detected: a new id, nearby
    seen = []
    for s in scene(persons=[lost, other, far, back], ticks=ticks(2.0)):
        runner.tick(s, TICK)
        seen.append((None if runner.player is None else runner.player.id,
                     None if runner.player2 is None else runner.player2.id))
    assert seen[ticks(1.0) - 1] == (1, 3)
    assert {p for p, _ in seen[ticks(1.0):ticks(1.25)]} == {None}     # the slot is kept, empty
    assert {p2 for _, p2 in seen[ticks(1.1):ticks(1.25)]} == {8}      # the far one is only the second body
    assert {p for p, _ in seen[ticks(1.25):]} == {7}                  # the new id by the old place keeps it
    runner, _, _ = make_runner(font5x7)
    beside = Person(x=0.45, height=0.5, id=3)                         # there all along, next to the player
    ids = []
    for s in scene(persons=[Person(x=0.35, height=0.7, id=1).leave(1.0), beside], ticks=ticks(1.6)):
        runner.tick(s, TICK)
        ids.append(None if runner.player is None else runner.player.id)
    assert set(ids[ticks(1.0):ticks(1.45)]) == {None}                 # a body that was there is not the player back
    assert set(ids[ticks(1.55):]) == {3}                              # nobody came back: the lock moves on


def test_presence_hysteresis_ignores_out_of_zone(font5x7):
    runner, _, _ = make_runner(font5x7)
    feed(runner, scene(persons=crowd(6), ticks=ticks(3.0)))
    assert runner.state()["present"] is False                         # out of the zone: never present
    runner, _, _ = make_runner(font5x7)
    present = []
    for s in scene(persons=[Person(id=1).leave(3.0)], ticks=ticks(7.0)):
        runner.tick(s, TICK)
        present.append(runner.state()["present"])
    on, off = present.index(True), present.index(False, present.index(True))
    assert on == ticks(1.0) and off == ticks(6.0) - 1                 # on after 1 s, off 3 s after leaving
    assert runner.state()["idle"] == pytest.approx(4.0, abs=0.05)                  # since the last sighting
    runner, _, _ = make_runner(font5x7)
    feed(runner, scene(blobs=[LAMP], ticks=ticks(3.0)))
    assert runner.state()["present"] is False                         # a parked light is a lamp, not a person
    carried = moving_blob(0.25, 0.5, 0.75, 0.5, 3.0)                  # a sixth of the frame a second
    for frames in (scene(blobs=[carried], ticks=ticks(1.5)),
                   degrade(scene(blobs=[carried], ticks=ticks(1.5)), **REAL_NOISE)):
        runner, _, _ = make_runner(font5x7)
        feed(runner, frames)
        assert runner.state()["present"] is True                      # at 30 and at 10 captures a second
    runner, _, _ = make_runner(font5x7)
    feed(runner, scene(blobs=[moving_blob(0.1, 0.25, 0.1, 0.75, 3.0)], ticks=ticks(2.0)))
    assert runner.state()["present"] is False                         # moving, but left of the zone
    runner, _, _ = make_runner(font5x7)
    feed(runner, degrade(scene(blobs=[moving_blob(0.4, 0.5, 0.49, 0.5, 3.0)], ticks=ticks(2.0)), **REAL_NOISE))
    assert runner.state()["present"] is False                         # drifting 0.03 a second, timed by camera_t


def ended(runner, lobby, frames):
    """Feed frames and return (the reason the first session ended, the runner time it ended) or None."""
    for s in frames:
        runner.tick(s, TICK)
        if lobby.results:
            return lobby.results[0].reason, runner.t
    return None


def test_leave_ends_session_with_card(font5x7):
    runner, _, lobby = make_runner(font5x7, cfg=make_cfg(SIZE, leave_seconds=2.0))
    runner.launch("spy")
    reason, t = ended(runner, lobby, scene(persons=[Person(id=1).leave(1.0)], blobs=[LAMP], ticks=ticks(5.0)))
    assert reason == "left" and t == pytest.approx(1.0 + 2.0, abs=TICK + 1e-9)   # a parked lamp holds nothing
    assert lobby.results[0].players == 1 and runner.current is lobby


def test_abandon_seconds_overrides_leave(font5x7):
    paint = spy(info={"abandon_seconds": 4.0})
    runner, _, lobby = make_runner(font5x7, games=(paint,), cfg=make_cfg(SIZE, leave_seconds=2.0))
    runner.launch("spy")
    reason, t = ended(runner, lobby, scene(persons=[Person(id=1).leave(1.0)], ticks=ticks(8.0)))
    assert reason == "left" and t == pytest.approx(1.0 + 4.0, abs=TICK + 1e-9)


def test_a_moving_light_holds_the_session(font5x7):
    # spec 7.2: presence evidence is an in-zone body or a moving in-zone blob, and leave follows the evidence. A
    # light carried across the zone with nobody detected keeps the session; once it is gone, leave runs.
    runner, _, lobby = make_runner(font5x7, games=(spy(extra={"active": True}),),
                                   cfg=make_cfg(SIZE, leave_seconds=1.0))
    runner.launch("spy")
    carried = moving_blob(0.25, 0.5, 0.75, 0.5, 4.0)
    reason, t = ended(runner, lobby, scene(blobs=[carried], ticks=ticks(7.0)))
    assert reason == "left" and t == pytest.approx(4.0 + 1.0, abs=2 * TICK)


def test_the_lobby_draws_on_the_tick_a_rule_ends_the_session(font5x7):
    # Loop decision 14: the tick a rule ends the session, the lobby ticks with dt 0 and draws, so the wall never
    # shows a blank frame.
    runner, display, lobby = make_runner(font5x7, cfg=make_cfg(SIZE, leave_seconds=1.0))
    runner.launch("spy")
    reason, _ = ended(runner, lobby, scene(persons=[Person(id=1).leave(0.5)], ticks=ticks(3.0)))
    assert reason == "left" and lobby.updates == 1 and display.last[0, 1].tolist() == [0, 255, 0]


def test_inactivity_prompt_then_end(font5x7):
    runner, display, lobby = make_runner(font5x7, cfg=make_cfg(SIZE, inactive_seconds=2.0))
    runner.launch("spy")
    reason, t = ended(runner, lobby, stand(ticks=ticks(10.0)))
    assert PROMPT_SECONDS == 5.0                                       # spec 7.2
    assert reason == "inactive" and t == pytest.approx(2.0 + PROMPT_SECONDS, abs=TICK + 1e-9)
    runner, display, lobby = make_runner(font5x7, cfg=make_cfg(SIZE, inactive_seconds=2.0))
    runner.launch("spy")
    feed(runner, stand(ticks=ticks(2.5)))
    white = np.all(display.last == 255, axis=2)
    assert white.sum() > 40 and white[:, :2].sum() + white[:, -2:].sum() <= 2   # "STILL PLAYING? HAND UP", wrapped
    assert runner.current_name == "spy"


def test_inactivity_prompt_cancelled_by_a_raised_hand_or_activity(font5x7):
    runner, _, lobby = make_runner(font5x7, cfg=make_cfg(SIZE, inactive_seconds=2.0))
    runner.launch("spy")
    hand = Person(id=1).raise_hand(at=3.0, seconds=0.5)
    reason, t = ended(runner, lobby, scene(persons=[hand], ticks=ticks(12.0)))
    assert reason == "inactive" and t > 3.0 + 2.0 + PROMPT_SECONDS - TICK   # the prompt restarted after the hand
    busy = spy(extra={"active": True})
    runner, _, lobby = make_runner(font5x7, games=(busy,), cfg=make_cfg(SIZE, inactive_seconds=2.0))
    runner.launch("spy")
    assert ended(runner, lobby, stand(ticks=ticks(10.0))) is None


@pytest.mark.parametrize("active, counts", [(True, True), (np.True_, True), (False, False), (np.False_, False),
                                            (1, False), ("yes", False), (np.int64(1), False)])
def test_active_is_a_bool_and_numpy_bools_count(font5x7, active, counts):
    # Plan review B1: spec 7.1's active boolean. np.True_ is what a numpy comparison gives a game, and it counts;
    # a number or a string is not a boolean and never does.
    runner, _, lobby = make_runner(font5x7, games=(spy(extra={"active": active}),),
                                   cfg=make_cfg(SIZE, inactive_seconds=2.0))
    runner.launch("spy")
    result = ended(runner, lobby, stand(ticks=ticks(2.0 + PROMPT_SECONDS + 1.0)))
    assert (result is None) if counts else (result[0] == "inactive"), f"active={active!r}"


def test_cap_only_when_someone_waits(font5x7):
    cfg = make_cfg(SIZE, max_session_seconds=2.0)
    runner, _, lobby = make_runner(font5x7, games=(spy(extra={"phase": "over", "active": True}),), cfg=cfg)
    runner.launch("spy")
    assert ended(runner, lobby, stand(ticks=ticks(4.0))) is None      # nobody waits: no cap
    two = [Person(x=0.35, id=1), Person(x=0.65, height=0.5, id=2)]
    runner, _, lobby = make_runner(font5x7, games=(spy(extra={"phase": "play", "active": True}),), cfg=cfg)
    runner.launch("spy")
    assert ended(runner, lobby, scene(persons=two, ticks=ticks(3.0))) is None   # mid-round: never
    runner.game.extra = {"phase": "over", "active": True}
    reason, t = ended(runner, lobby, scene(persons=two, ticks=ticks(1.0)))
    assert reason == "capped" and lobby.results[0].waiting is True and lobby.results[0].players == 1
    pair = spy(info={"players": 2}, extra={"phase": "over", "active": True})
    runner, _, lobby = make_runner(font5x7, games=(pair,), cfg=cfg)
    runner.launch("spy")
    assert ended(runner, lobby, scene(persons=two, ticks=ticks(4.0))) is None   # two players: nobody waits


def test_exit_gesture_disabled_by_info(font5x7):
    arms = spy(info={"exit_gesture": False}, extra={"active": True})
    runner, display, lobby = make_runner(font5x7, games=(arms,))
    runner.launch("spy")
    assert ended(runner, lobby, scene(persons=[Person(id=1).both_hands_up(at=0.0, seconds=6.0)],
                                      ticks=ticks(6.0))) is None
    assert not np.any(np.all(display.last == RING, axis=2))          # and no ring


@pytest.mark.parametrize("body_id", range(8))
def test_exit_hold_rides_out_camera_noise(font5x7, body_id):
    # C10's runner half: the exit is Hold(exit_seconds, grace=capture_grace(camera_fps)), so the 15% keypoint
    # dropout of spec 6.4 does not break a 3 s hold, and a closing ring shows while it fills.
    runner, display, lobby = make_runner(font5x7, games=(spy(extra={"active": True}),))
    assert runner.grace == capture_grace(10) == pytest.approx(0.55)
    runner.launch("spy")
    person = Person(id=body_id).both_hands_up(at=0.5, seconds=6.0)
    rings = []
    for s in degrade(scene(persons=[person], ticks=ticks(6.0)), **REAL_NOISE):
        runner.tick(s, TICK)
        rings.append(bool(np.any(np.all(display.last == RING, axis=2))))
        if lobby.results:
            break
    assert lobby.results[0].reason == "exit", f"body_id={body_id}"
    assert 0.5 + 3.0 < runner.t < 0.5 + 4.4, f"body_id={body_id} t={runner.t}"
    assert sum(rings) > ticks(2.0)


def test_exit_then_hands_still_up_reaches_lobby_as_no_bodies(font5x7):
    runner, _, lobby = make_runner(font5x7, games=(spy(extra={"active": True}),))
    runner.launch("spy")
    person = Person(id=1).both_hands_up(at=0.0, seconds=5.0)
    reason, t = ended(runner, lobby, scene(persons=[person], ticks=ticks(4.0)))
    assert reason == "exit" and t == pytest.approx(3.0, abs=2 * TICK)
    lobby.seen.clear()
    feed(runner, (s for s in scene(persons=[person], ticks=ticks(8.0)) if s.t > t))
    blocked = [s.bodies == () and s.player is None and s.blobs == () for s in lobby.seen]
    down = ticks(5.0 - t)                                             # lobby ticks until the hands come down
    assert all(blocked[:down]) and not any(blocked[down + ticks(capture_grace(10)) + 1:])
    assert lobby.request is None and runner.current is lobby


def test_exit_hold_is_reset_on_launch(font5x7):
    # C27's caller rule: the runner updates its exit hold every tick and resets it on launch, so hands held up in
    # the lobby do not end the next game at once.
    runner, _, lobby = make_runner(font5x7, games=(spy(extra={"active": True}),))
    person = Person(id=1).both_hands_up(at=0.0, seconds=9.0)
    frames = scene(persons=[person], ticks=ticks(9.0))
    feed(runner, (next(frames) for _ in range(ticks(4.0))))           # 4 s of hands up in the lobby
    runner.launch("spy")
    reason, t = ended(runner, lobby, frames)
    assert reason == "exit" and t == pytest.approx(4.0 + 3.0, abs=2 * TICK)


def test_exit_needs_the_players_own_two_hands(font5x7):
    # C10: the exit is the player's both hands. A bystander's two hands, or the player's one, never end the game.
    bystander = [Person(x=0.35, height=0.7, id=1), Person(x=0.65, height=0.5, id=2).both_hands_up(at=0.0, seconds=6.0)]
    one_hand = [Person(id=1).raise_hand(at=0.0, seconds=6.0)]
    for persons in (bystander, one_hand):
        runner, display, lobby = make_runner(font5x7, games=(spy(extra={"active": True}),))
        runner.launch("spy")
        assert ended(runner, lobby, scene(persons=persons, ticks=ticks(6.0))) is None
        assert runner.player.id == 1 and not np.any(np.all(display.last == RING, axis=2))


@pytest.mark.parametrize("body_id", [None, 0, 1, 2, 3])
def test_exit_block_holds_until_both_hands_are_down_for_the_grace(font5x7, body_id):
    # After an exit the lobby sees nobody while any in-zone body shows a raised wrist, and for the grace after:
    # lowering one hand is not enough, nor is a keypoint dropout (body_id: REAL_NOISE seeds), so spec 7.3's "a
    # raised hand starts play at once" cannot relaunch the game.
    runner, _, lobby = make_runner(font5x7, games=(spy(extra={"active": True}),))
    runner.launch("spy")
    person = Person(id=body_id or 1).both_hands_up(at=0.0, seconds=5.0).raise_hand(at=5.0, seconds=2.0)
    frames = scene(persons=[person], ticks=ticks(10.0))
    if body_id is not None:
        frames = degrade(frames, **REAL_NOISE)
    reason, t = ended(runner, lobby, frames)
    assert reason == "exit" and t < 5.0
    lobby.seen.clear()
    feed(runner, frames)
    blocked = [s.bodies == () and s.player is None for s in lobby.seen]
    down, grace = ticks(7.0 - t), ticks(capture_grace(10))            # the last hand comes down at 7 s
    assert all(blocked[:down + grace - 1]), f"body_id={body_id}"
    assert not any(blocked[down + grace + ticks(0.2):]), f"body_id={body_id}"
    assert runner.current is lobby and lobby.request is None


def test_session_logged_with_reason(font5x7, tmp_path):
    sessions = SessionLog(tmp_path / "sessions.jsonl")
    pair = spy(info={"players": 2}, extra={"score": np.float32(12.5), "active": True})
    runner, _, lobby = make_runner(font5x7, games=(pair,), sessions=sessions,
                                   cfg=make_cfg(SIZE, leave_seconds=1.0))
    runner.launch("spy")
    two = [Person(x=0.35, id=1).leave(2.0), Person(x=0.65, height=0.5, id=2).leave(2.0)]
    feed(runner, scene(persons=two, ticks=ticks(4.0)))
    (line,) = [json.loads(x) for x in (tmp_path / "sessions.jsonl").read_text().splitlines()]
    assert line == {"game": "spy", "layout": "64x64", "start": "2026-11-11T21:00:00",
                    "duration": pytest.approx(3.0, abs=2 * TICK), "players": 2, "score": 12.5, "reason": "left"}


def test_push_path_order(font5x7):
    # Q11: limiter, then governor, then push. A frame the limiter changes reaches the governor, and what the
    # governor returns is what is pushed.
    class White(SpyGame):
        def draw(self, canvas):
            canvas.clear(WHITE)

    calls = []
    runner, display, _ = make_runner(font5x7, games=(White,), local_clock=lambda: datetime(2026, 11, 12, 2, 0))
    limiter, governor = runner.limiter.apply, runner.governor.apply

    def limit(frame):
        calls.append(("limiter", frame is runner.canvas.frame, int(frame.max())))
        out = limiter(frame)
        calls.append(("limited", out))
        return out

    def govern(frame):
        calls.append(("governor", frame is calls[-1][1]))
        out = governor(frame)
        calls.append(("governed", out))
        return out

    runner.limiter.apply, runner.governor.apply = limit, govern
    runner.launch("spy")
    feed(runner, stand(ticks=1))
    assert [c[0] for c in calls] == ["limiter", "limited", "governor", "governed"]
    assert calls[0][1:] == (True, 255) and calls[2][1] is True
    assert np.array_equal(display.last, calls[3][1]) and display.last.max() == 128   # 02:00 is night: scaled
    runner, display, _ = make_runner(font5x7, games=(White,))
    runner.launch("spy")
    feed(runner, stand(ticks=1))
    assert display.last.max() == 128 and runner.limiter.is_night() is False          # 21:00: the day cap
    assert runner.limiter.cap() == runner.cfg.apl_cap_day


class Camera:
    """latest() gives what result says; available as set."""

    def __init__(self, result=None, available=True):
        self.result, self.available = result, available

    def latest(self):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_stale_camera_is_unavailable(font5x7):
    clock = FakeClock()
    runner, _, lobby = make_runner(font5x7, clock=clock)
    body = next(stand(ticks=1)).bodies[0]
    audio = Camera((clock.now, Audio()))
    s = runner.sense(Camera((clock.now - 1.5, (body,), (), None)), audio)
    assert s.bodies == () and not s.camera_fresh and lobby.status[0] is False
    camera = Camera((clock.now - 0.2, (body,), (), None))
    s = runner.sense(camera, audio)
    assert s.bodies == (body,) and s.camera_fresh and s.camera_seq == 1 and lobby.status[0] is True
    assert s.camera_t == pytest.approx(runner.t - 0.2)
    s = runner.sense(camera, audio)
    assert not s.camera_fresh and s.camera_seq == 1                   # the same capture again
    clock.now += 0.9
    s = runner.sense(camera, audio)
    assert s.bodies == () and lobby.status[:3] == (False, False, set())   # both stale now
    assert runner.sense(Camera(None), Camera((clock.now, Audio()))).bodies == ()


def test_sense_survives_raising_source_and_reports_status(font5x7, caplog):
    clock = FakeClock()
    runner, _, lobby = make_runner(font5x7, clock=clock, calibration=Calibration(calibrated=True))
    with caplog.at_level(logging.ERROR, logger="arcade"):
        for _ in range(5):
            s = runner.sense(Camera(OSError("camera gone")), Camera(OSError("mic gone")))
    assert s.bodies == () and s.motion.shape == (64, 64) and lobby.status == (False, False, set(), True)
    assert len(caplog.records) == 2                                   # each failing source logged once
    s = runner.sense(Camera((clock.now, (), (), None)), Camera((clock.now - 0.1, Audio(level=0.5)), available=False))
    assert lobby.status == (True, False, {"pose", "blobs", "motion"}, True) and s.audio.level == 0.5


def test_sense_builds_keyword_sensed(font5x7):
    # C21: Sensed and Audio take keywords after t, so sense() can never bind the bodies to camera_t.
    clock = FakeClock()
    runner, _, lobby = make_runner(font5x7, clock=clock)
    feed(runner, scene(ticks=3))
    body = next(stand(ticks=1)).bodies[0]
    grid = np.zeros((64, 128), bool)
    grid[:32, :64] = True
    s = runner.sense(Camera((clock.now, (body,), (), grid)), Camera((clock.now, Audio(voice=0.4))))
    assert s.t == runner.t and s.bodies == (body,) and s.audio.voice == 0.4 and s.motion.shape == (64, 64)
    assert s.motion[:32, :32].all() and not s.motion[32:].any()
    assert lobby.status == (True, True, {"pose", "blobs", "motion", "audio"}, False)


WALL = (128, 64)                                                      # the wall in hand (Q82): the C35 tests' size


class Seeing(Camera):
    """A Camera that declares provides (C35)."""

    def __init__(self, result=None, available=True, provides=None):
        super().__init__(result, available)
        self.provides = provides


class RaisingProvides(Camera):
    """A Camera whose provides raises when read."""

    @property
    def provides(self):
        raise OSError("provides gone")


def test_sense_claims_only_what_the_camera_provides(font5x7):
    # C35: a camera claims only the inputs it provides, so the lobby offers only the games those inputs serve; what
    # it does not provide never reaches the lobby or a game, whatever its latest() holds. A camera without "motion"
    # gives no grid: Sensed holds it as the empty grid, which with_motion makes all False at the wall's size.
    clock = FakeClock()
    runner, _, lobby = make_runner(font5x7, clock=clock, cfg=make_cfg(WALL))
    body, blob = next(stand(ticks=1)).bodies[0], LAMP(0.0)
    got = (clock.now, (body,), (blob,), np.ones((64, 128), bool))
    s = runner.sense(Seeing(got, provides={"pose"}), Camera(None))
    assert lobby.status[:3] == (True, False, {"pose"})
    assert s.bodies == (body,) and s.blobs == () and s.motion.shape == (64, 128) and not s.motion.any()
    s = runner.sense(Seeing(got, provides=frozenset({"pose", "blobs"})), Camera(None))
    assert lobby.status[:3] == (True, False, {"pose", "blobs"})
    assert s.bodies == (body,) and s.blobs == (blob,) and not s.motion.any()
    s = runner.sense(Seeing(got, provides={"motion", "audio", "sonar"}), Camera((clock.now, Audio())))
    assert lobby.status[:3] == (True, True, {"motion", "audio"})        # a camera never claims the microphone
    assert s.bodies == () and s.blobs == () and s.motion.shape == (64, 128) and s.motion.all()
    s = runner.sense(Seeing(got, provides=set()), Camera(None))
    assert lobby.status[:3] == (True, False, set()) and s.bodies == () and s.blobs == () and not s.motion.any()


def test_a_camera_without_provides_claims_every_camera_input(font5x7):
    # The fake Camera has no provides: every camera input, as before C35. The names live in arcade.sensed and the
    # runner's are the same objects.
    import arcade.runner
    import arcade.sensed

    assert arcade.runner.CAMERA_INPUTS is arcade.sensed.CAMERA_INPUTS == frozenset({"pose", "blobs", "motion"})
    assert arcade.runner.AUDIO_INPUTS is arcade.sensed.AUDIO_INPUTS == frozenset({"audio"})
    clock = FakeClock()
    runner, _, lobby = make_runner(font5x7, clock=clock, cfg=make_cfg(WALL))
    body, blob = next(stand(ticks=1)).bodies[0], LAMP(0.0)
    camera = Camera((clock.now, (body,), (blob,), np.ones((64, 128), bool)))
    assert not hasattr(camera, "provides")
    s = runner.sense(camera, Camera(None))
    assert lobby.status[:3] == (True, False, {"pose", "blobs", "motion"})
    assert s.bodies == (body,) and s.blobs == (blob,) and s.motion.all()


def test_a_raising_provides_fails_the_camera(font5x7, caplog):
    # A provides that raises, or is not a set of strings, fails the camera as a raising latest() does: unavailable,
    # nothing from it, logged once per run of failures; a good one next time recovers it.
    clock = FakeClock()
    runner, _, lobby = make_runner(font5x7, clock=clock, cfg=make_cfg(WALL), calibration=Calibration(calibrated=True))
    body = next(stand(ticks=1)).bodies[0]
    got = (clock.now, (body,), (), None)
    with caplog.at_level(logging.ERROR, logger="arcade"):
        for _ in range(3):
            s = runner.sense(RaisingProvides(got), Camera(None))
            assert s.bodies == () and lobby.status == (False, False, set(), True)
        for bad in (["pose"], ("pose",), "pose", {1}, None, {"pose": True}):
            s = runner.sense(Seeing(got, provides=bad), Camera(None))
            assert s.bodies == () and lobby.status == (False, False, set(), True), f"{bad!r}"
    messages = [r.getMessage() for r in caplog.records]
    assert messages.count("camera source failed") == 1 and "provides gone" in caplog.text
    s = runner.sense(Seeing(got, provides={"pose"}), Camera(None))
    assert s.bodies == (body,) and lobby.status == (True, False, {"pose"}, True)


def test_games_see_the_runners_clock(font5x7):
    # Sensed.t is the runner's t for the tick, and camera_t moves with it, so a game sees one clock live and
    # headless, wherever a scenario starts.
    runner, _, _ = make_runner(font5x7)
    runner.launch("spy")
    feed(runner, [Sensed(50.0 + i * TICK, camera_t=49.9 + i * TICK, camera_fresh=True) for i in range(3)])
    s = runner.game.seen[-1]
    assert s.t == runner.t == pytest.approx(3 * TICK) and s.camera_t == pytest.approx(runner.t - 0.1)
    clock = FakeClock()
    runner, _, lobby = make_runner(font5x7, clock=clock)
    feed(runner, scene(ticks=3))
    s = runner.sense(Camera((clock.now - 0.05, (), (), None)), Camera((clock.now, Audio())))
    runner.tick(s, TICK)
    assert lobby.seen[-1].t == runner.t and lobby.seen[-1].camera_t == pytest.approx(runner.t - 0.05)


def test_sense_treats_a_malformed_result_as_a_failed_source(font5x7, caplog):
    # A latest() of another shape goes the way of one that raises: the source is unavailable, logged once per run
    # of failures, and neither sense() nor the loop raises.
    clock = FakeClock()
    runner, _, lobby = make_runner(font5x7, clock=clock, sleep=clock.sleep)
    body = next(stand(ticks=1)).bodies[0]
    cameras = [(clock.now, (body,), ()), (clock.now,), 5, (clock.now, ("body",), (), None),
               (clock.now, (), ("blob",), None), (clock.now, (), (), "grid"), (clock.now, (), (), np.zeros(4, bool)),
               ("now", (), (), None)]
    cameras += [(t, (body,), (), None) for t in (math.inf, math.nan, clock.now + 3600)]   # not the runner's clock
    audios = [(clock.now, 0.5), (clock.now,), "loud", ("now", Audio())]
    audios += [(t, Audio(level=0.5)) for t in (math.inf, math.nan, clock.now + 3600)]
    with caplog.at_level(logging.ERROR, logger="arcade"):
        for got in cameras:
            s = runner.sense(Camera(got), Camera((clock.now, Audio())))
            assert s.bodies == () and lobby.status[:2] == (False, True), f"{got!r}"
        for got in audios:
            s = runner.sense(Camera((clock.now, (body,), (), None)), Camera(got))
            assert s.bodies == (body,) and lobby.status[:2] == (True, False), f"{got!r}"
        runner.loop(Camera(5), Camera("loud"), max_ticks=3)
    messages = [r.getMessage() for r in caplog.records]
    assert messages.count("camera source failed") == 2 and messages.count("audio source failed") == 1


def test_launch_refuses_an_unhashable_name_and_ends_a_crash_icon(font5x7, caplog):
    runner, _, lobby = make_runner(font5x7, games=(spy(raise_in=frozenset({"update"})), spy("paint")))
    lobby.request = ["spy"]                                           # a lobby bug: a list, not a name
    with caplog.at_level(logging.WARNING, logger="arcade"):
        feed(runner, stand(ticks=1))
    assert runner.current is lobby and "not launching ['spy']: unknown" in caplog.text
    runner.launch("spy")
    feed(runner, stand(ticks=1))
    assert runner.state()["glitch"] is True
    assert runner.launch("paint")
    feed(runner, stand(ticks=1))
    assert runner.current_name == "paint" and runner.game.updates == 1 and runner.state()["glitch"] is False
    feed(runner, stand(ticks=ticks(CRASH_SECONDS) + 1))
    assert runner.current_name == "paint"                             # the old icon never sends it to the lobby


class Live:
    """A camera whose latest() stamps each capture on clock, plus ahead seconds."""

    def __init__(self, clock, bodies, ahead=0.0):
        self.clock, self.bodies, self.ahead = clock, bodies, ahead

    def latest(self):
        return self.clock.now + self.ahead, self.bodies, (), None


def test_a_body_stamped_ahead_of_the_runners_clock_holds_nothing(font5x7, caplog):
    # R2-N2: a source on another clock or unit (picamera2 stamps nanoseconds since boot) repeats its last capture
    # with a time far ahead. It is malformed, so the frozen body holds neither presence nor the session. A stamp
    # within CLOCK_SLACK is a capture that landed as sense() read the clock, and counts.
    assert CLOCK_SLACK == 0.1
    clock = FakeClock()
    runner, _, lobby = make_runner(font5x7, clock=clock, sleep=clock.sleep, cfg=make_cfg(SIZE, leave_seconds=2.0))
    body = next(stand(ticks=1)).bodies[0]
    runner.loop(Live(clock, (body,), ahead=CLOCK_SLACK / 2), Camera(None), max_ticks=ticks(2.0))
    assert runner.presence.present and lobby.status[0] is True
    assert runner.sense(Live(clock, (body,), ahead=2 * CLOCK_SLACK), Camera(None)).bodies == ()
    runner.sense(Live(clock, (body,)), Camera(None))
    caplog.clear()
    with caplog.at_level(logging.ERROR, logger="arcade"):
        assert runner.sense(Camera((-math.inf, (body,), (), None)), Camera(None)).bodies == ()
    assert "camera source failed" in caplog.text                      # malformed, not merely stale
    assert runner.launch("spy")
    runner.loop(Camera((clock.now + 3600, (body,), (), None)), Camera(None), max_ticks=ticks(6.0))
    assert [r.reason for r in lobby.results] == ["left"] and runner.current is lobby
    assert not runner.presence.present and lobby.status[0] is False


def test_launch_is_refused_while_a_game_runs(font5x7, caplog):
    # R2-N3: a launch comes from the lobby or during the crash icon. Mid-session it would drop the session with no
    # log line and no end card, so it is refused.
    runner, _, lobby = make_runner(font5x7, games=(SpyGame, spy("paint")))
    assert runner.launch("spy")
    feed(runner, stand(ticks=ticks(1.0)))
    first = runner.game
    with caplog.at_level(logging.WARNING, logger="arcade"):
        assert runner.launch("paint") is False
    assert "not launching 'paint': spy is running" in caplog.text
    feed(runner, stand(ticks=1))
    assert runner.current is first and first.updates == ticks(1.0) + 1 and lobby.results == []
    runner.end_session("exit")
    assert [r.game for r in lobby.results] == ["spy"] and runner.launch("paint")


class StuckLobby(StubLobby):
    """A lobby whose request is a read-only property: the runner can read it, never clear it."""

    request = property(lambda self: "spy")

    def __init__(self):
        vars(self).update(raise_in=frozenset(), available=None, status=None, results=[], resets=0, updates=0,
                          seen=[])


def test_a_request_that_cannot_be_cleared_is_a_lobby_that_raised(font5x7, caplog):
    # R2-N4: the runner reads and clears the request inside the lobby guard, so tick() never raises for it and the
    # game is not launched again on every lobby tick.
    runner, _, lobby = make_runner(font5x7, lobby=StuckLobby())
    with caplog.at_level(logging.ERROR, logger="arcade"):
        feed(runner, stand(ticks=3))
    assert runner.state()["title_card"] is True and runner.current_name == "lobby" and runner.game is None
    assert "AttributeError" in runner.last_error and "title card" in caplog.text


def test_push_failure_is_logged_once_a_minute(font5x7, caplog):
    class BadDisplay(RecordingDisplay):
        def push(self, frame):
            raise OSError("socket")

    runner, _, _ = make_runner(font5x7, display=BadDisplay())
    with caplog.at_level(logging.ERROR, logger="arcade"):
        feed(runner, scene(ticks=90))
        assert len(caplog.records) == 1
        feed(runner, scene(ticks=ticks(60.0)))
    assert len(caplog.records) == 2 and "display push failed" in caplog.records[0].getMessage()


def test_governor_interventions_logged_once_a_minute_with_the_game(font5x7, caplog):
    runner, display, _ = make_runner(font5x7, games=(Strobe,))
    runner.launch("strobe")
    with caplog.at_level(logging.INFO, logger="arcade"):
        feed(runner, stand(ticks=90))
    held = [r for r in caplog.records if "flash governor" in r.getMessage()]
    assert len(held) == 1 and "strobe" in held[0].getMessage()
    assert runner.state()["flash_held_ticks"] == runner.governor.held_ticks > 0


def test_loop_runs_max_ticks_with_fake_clock(font5x7):
    clock = FakeClock()
    runner, display, _ = make_runner(font5x7, clock=clock, sleep=clock.sleep)
    runner.loop(Camera((clock.now, (), (), None)), Camera((clock.now, Audio())), max_ticks=10)
    assert display.count == 10 and clock.now == pytest.approx(100.0 + 10 / runner.cfg.fps, abs=0.05)


def test_loop_stops_when_until_is_true(font5x7):
    # record and calibrate stop the loop on their scene's done(): it ends after the first tick on which until() is
    # True, and max_ticks still bounds it.
    clock = FakeClock()
    camera, audio = Camera((clock.now, (), (), None)), Camera((clock.now, Audio()))
    wall = lambda: make_runner(font5x7, clock=clock, sleep=clock.sleep, cfg=make_cfg(WALL))
    runner, display, _ = wall()
    runner.loop(camera, audio, until=lambda: display.count >= 3)
    assert display.count == 3
    runner, display, _ = wall()
    runner.loop(camera, audio, max_ticks=2, until=lambda: display.count >= 3)
    assert display.count == 2
    runner, display, _ = wall()
    runner.loop(camera, audio, until=lambda: True)
    assert display.count == 1                                           # asked after the tick, never before


def test_dt_is_clamped(font5x7):
    runner, _, _ = make_runner(font5x7)
    runner.launch("spy")
    runner.tick(Sensed(0.0), dt=5.0)
    assert runner.t == pytest.approx(MAX_DT) and MAX_DT == 0.1           # spec 7.2: 100 ms
    for bad in (math.nan, -1.0, math.inf, None):
        runner.tick(Sensed(0.0), dt=bad)
    assert runner.t == pytest.approx(MAX_DT)


def test_games_get_only_in_zone_blobs(font5x7):
    cal = Calibration()
    inside, outside = place_blob(Blob(0.5, 0.5, 0.02, WHITE), cal), place_blob(Blob(0.05, 0.5, 0.02, WHITE), cal)
    runner, _, lobby = make_runner(font5x7)
    feed(runner, [Sensed(0.0, blobs=(inside, outside))])
    assert lobby.seen[-1].blobs == (inside, outside)                  # the lobby sees them all
    runner.launch("spy")
    feed(runner, [Sensed(TICK, blobs=(inside, outside))])
    assert runner.game.seen[-1].blobs == (inside,)


def crowd_of_three():
    """Three people in the zone: two wait for a one-player game."""
    return [Person(x=0.3, height=0.6, id=1), Person(x=0.5, height=0.55, id=2), Person(x=0.7, height=0.5, id=3)]


def test_an_array_phase_never_raises_out_of_tick(font5x7):
    # C30a: phase is compared only when it is a str. An array's != gives an array, and `and` on it raises out of
    # tick() with no guard; a non-str phase counts as "play", as a missing key does.
    game = spy(info={"players": 1}, extra={"phase": np.array(["a", "b"]), "active": True})
    runner, _, lobby = make_runner(font5x7, games=(game,), strict=False, cfg=make_cfg(SIZE, max_session_seconds=1.0))
    runner.launch("spy")
    assert ended(runner, lobby, scene(persons=crowd_of_three(), ticks=90)) is None   # never capped, never raised
    assert runner.current_name == "spy"


def test_a_numpy_str_phase_still_caps(font5x7):
    game = spy(info={"players": 1}, extra={"phase": np.str_("serve"), "active": True})
    runner, _, lobby = make_runner(font5x7, games=(game,), strict=False, cfg=make_cfg(SIZE, max_session_seconds=1.0))
    runner.launch("spy")
    reason, t = ended(runner, lobby, scene(persons=crowd_of_three(), ticks=90))
    assert reason == "capped" and t == pytest.approx(1.0, abs=TICK + 1e-9)


def test_an_object_motion_grid_is_a_failed_source(font5x7, caplog):
    # C30b: a motion grid is bool, int, uint or float. An object grid would reach np.asarray(..., bool) and the
    # resample, which call bool() on whatever its cells hold; it is a malformed result, so the camera failed.
    clock = FakeClock()
    runner, _, lobby = make_runner(font5x7, clock=clock)
    body = next(stand(ticks=1)).bodies[0]
    grid = np.full((64, 128), None, object)
    with caplog.at_level(logging.ERROR, logger="arcade"):
        for _ in range(3):
            s = runner.sense(Camera((clock.now, (body,), (), grid)), Camera((clock.now, Audio())))
            assert s.bodies == () and lobby.status[0] is False
    assert [r.getMessage() for r in caplog.records].count("camera source failed") == 1
    for kind in (bool, np.uint8, np.int32, np.float32):                   # the grids a camera gives still count
        s = runner.sense(Camera((clock.now, (body,), (), np.zeros((64, 128), kind))), Camera((clock.now, Audio())))
        assert s.bodies == (body,) and lobby.status[0] is True, kind


@pytest.mark.parametrize("stage", ["limiter", "governor"])
def test_a_raising_limiter_or_governor_pushes_nothing(font5x7, stage, caplog):
    # C30: a frame that did not pass both ceilings never reaches the wall.
    runner, display, _ = make_runner(font5x7)

    def boom(frame):
        raise RuntimeError(f"boom in {stage}")

    setattr(getattr(runner, stage), "apply", boom)
    with caplog.at_level(logging.ERROR, logger="arcade"):
        feed(runner, stand(ticks=3))
    assert display.count == 0
    assert [r.getMessage() for r in caplog.records].count("display push failed (logged once a minute)") == 1


def test_rival_timer_restarts_when_the_player_returns(font5x7):
    # C31: the switch needs SWITCH_SECONDS of a larger rival while the player is seen. A rival that came while the
    # player was briefly lost starts its second when the player is back.
    t0 = 0.5
    a, b = Person(x=0.35, height=0.5, id=1), Person(x=0.65, height=0.75, id=2).arrive(t0)
    gap = (ticks(t0 + 0.2), ticks(t0 + 0.6))                          # scene ticks with A missing
    frames = [dataclasses.replace(s, bodies=tuple(x for x in s.bodies if x.id != 1)) if gap[0] <= i < gap[1] else s
              for i, s in enumerate(scene(persons=[a, b], ticks=ticks(3.0)))]
    both = frames[ticks(t0) + 1].bodies
    assert all(x.in_zone for x in both) and max(x.scale for x in both) / min(x.scale for x in both) >= 1.45
    runner, _, _ = make_runner(font5x7)
    seen = []
    for s in frames:
        runner.tick(s, TICK)
        seen.append((runner.t, None if runner.player is None else runner.player.id))
    at = lambda t: min(seen, key=lambda e: abs(e[0] - t))[1]
    assert at(t0) == 1 and at(t0 + 0.4) is None and at(t0 + 0.7) == 1
    assert at(t0 + 1.1) == 1, seen                                     # the rival's time before the gap is gone
    first_b = next(t for t, p in seen if p == 2)
    assert first_b == pytest.approx(t0 + 1.6, abs=TICK + 1e-9), seen


@pytest.mark.parametrize("score, want", [(np.array([3]), None), (4, 4.0), (math.nan, None)],
                         ids=["array", "int", "nan"])
def test_session_result_score_is_a_finite_float_or_none(font5x7, score, want):
    # C30c: the end card formats the score, and an array would crash the lobby.
    runner, _, lobby = make_runner(font5x7, games=(spy(extra={"score": score}),))
    runner.launch("spy")
    feed(runner, stand(ticks=2))
    result = runner.end_session("exit")
    assert result.score == want and type(result.score) is type(want)
    assert lobby.results[-1] is result


def test_session_result_says_new_best_only_when_the_best_rose(font5x7):
    # C43: the end card says BEST! only for a new best. The runner reads tonight's best at launch and compares.
    class Recorder(SpyGame):
        info = spy("rec").info
        plays = iter([3, 3, 4, None])                                  # one score a session; None records nothing

        def reset(self, size, rng, fx):
            super().reset(size, rng, fx)
            score = next(self.plays)
            if score is not None:
                self.scores.record(score)

    runner, _, lobby = make_runner(font5x7, games=(Recorder,))
    got = []
    for _ in range(4):
        assert runner.launch("rec")
        feed(runner, stand(ticks=2))
        got.append(runner.end_session("exit"))
    assert [r.new_best for r in got] == [True, False, True, False], got
    assert [r.best for r in got] == [3.0, 3.0, 4.0, 4.0], got
    assert lobby.results == got
    assert SessionResult("g", "64x64", "done", None, 1.0, 1, None, False).new_best is False   # defaulted


def test_verbose_logs_the_capture_age_at_push_once_a_second(font5x7, caplog):
    from arcade.headless import NullLobby
    from arcade.sources import NoSource
    from arcade.sources.scripted import ScriptedCamera
    from show.display.fake import FakeDisplay
    from tests.arcade.helpers import FakeClock, make_cfg

    clock = FakeClock(500.0)
    cfg = make_cfg((128, 64))
    frames = scene(persons=[Person(0.5, id=7)], ticks=cfg.fps * 3)
    camera = ScriptedCamera(frames, clock)
    runner = Runner(cfg, FakeDisplay(), font5x7, NullLobby(), [], clock=clock, sleep=clock.sleep)
    with caplog.at_level(logging.DEBUG, logger="arcade"):
        runner.loop(camera, NoSource(), max_ticks=cfg.fps * 2 + 2)
    lines = [r.message for r in caplog.records if r.message.startswith("capture age at push")]
    assert 1 <= len(lines) <= 3
    assert "median" in lines[0] and "max" in lines[0] and lines[0].endswith("pushes)")
    with caplog.at_level(logging.INFO, logger="arcade"):
        caplog.clear()
        runner.loop(camera, NoSource(), max_ticks=cfg.fps)
    assert not [r for r in caplog.records if r.message.startswith("capture age at push")]


def test_the_lag_line_stops_when_the_camera_goes_stale(font5x7, caplog):
    from arcade.headless import NullLobby
    from arcade.sources import NoSource
    from arcade.sources.scripted import ScriptedCamera
    from show.display.fake import FakeDisplay
    from tests.arcade.helpers import FakeClock, make_cfg

    clock = FakeClock(500.0)
    cfg = make_cfg((128, 64))
    camera = ScriptedCamera(scene(persons=[Person(0.5, id=7)], ticks=cfg.fps), clock)
    runner = Runner(cfg, FakeDisplay(), font5x7, NullLobby(), [], clock=clock, sleep=clock.sleep)
    with caplog.at_level(logging.DEBUG, logger="arcade"):
        runner.loop(camera, NoSource(), max_ticks=cfg.fps)
        caplog.clear()
        clock.sleep(10.0)                                         # the camera is gone; its last capture is 10 s old
        runner.loop(NoSource(), NoSource(), max_ticks=cfg.fps * 2)
    lines = [r.message for r in caplog.records if r.message.startswith("capture age at push")]
    assert lines == []
