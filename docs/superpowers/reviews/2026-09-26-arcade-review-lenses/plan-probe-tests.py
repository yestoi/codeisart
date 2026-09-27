"""Reviewer probes. Each test asserts the behaviour the SPEC asks for; failures are findings."""
import json, random, sys
from pathlib import Path
import numpy as np
import pytest

from arcade.headless import RecordingDisplay, run_headless
from arcade.menu import Menu
from arcade.runner import Runner
from arcade.games import all_games
from arcade.sensed import Sensed
from arcade.sources.actors import TICK, Person, scene
from tests.arcade.helpers import SpyGame, StubMenu, make_cfg, run

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))


def feed(r, frames):
    for s in frames:
        r.tick(s, TICK)


class RaiseInReset(SpyGame):
    info = SpyGame.info.__class__("rr", "RR", SpyGame.info.icon, frozenset())
    def reset(self, size, rng):
        raise RuntimeError("reset boom")


class RaiseInDone(SpyGame):
    info = SpyGame.info.__class__("rd", "RD", SpyGame.info.icon, frozenset())
    def done(self):
        raise RuntimeError("done boom")


def test_crash_in_reset_via_menu_is_guarded(font5x7):
    menu = StubMenu()
    r = Runner(make_cfg((64, 64)), RecordingDisplay(), font5x7, menu, [RaiseInReset], seed=1)
    menu.selected = "rr"
    feed(r, scene(ticks=1))          # spec 7.2: exception in reset -> glitch -> menu, never raises
    assert r.crashes.get("rr") == 1


def test_crash_in_done_is_guarded(font5x7):
    r = Runner(make_cfg((64, 64)), RecordingDisplay(), font5x7, StubMenu(), [RaiseInDone], seed=1)
    r.launch("rd")
    feed(r, scene(ticks=1))
    assert r.crashes.get("rd") == 1


def test_game_left_alone_goes_to_attract(font5x7):
    class Ambient(SpyGame):
        info = SpyGame.info.__class__("ambient", "A", SpyGame.info.icon, frozenset())
    r = Runner(make_cfg((64, 64), idle_seconds=1.0), RecordingDisplay(), font5x7, StubMenu(),
               [SpyGame, Ambient], attract="ambient", seed=1)
    r.launch("spy")
    feed(r, scene(ticks=90))         # nobody in front of the wall for 3 s
    assert r.current_name in ("ambient", "menu"), r.current_name


def test_state_keys_not_clobbered_by_game(font5x7):
    from arcade.games.paint import Paint
    frames, game, r = run(Paint, scene(ticks=10), (64, 64), font5x7)
    st = r.state()
    assert st["idle"] == round(r._idle, 3), st   # paint's own "idle" overwrote the runner's


def test_run_helper_returns_game_even_after_done(font5x7):
    SpyGame.finish_after = 2
    try:
        frames, game, r = run(SpyGame, scene(ticks=5), (64, 64), font5x7)
        assert isinstance(game, SpyGame), type(game)
    finally:
        SpyGame.finish_after = None


def test_exit_gesture_does_not_flow_into_a_launch(font5x7):
    games = all_games()
    menu = Menu(games, make_cfg((64, 64)))
    r = Runner(make_cfg((64, 64)), RecordingDisplay(), font5x7, menu, games, seed=1)
    menu.set_status(True, True, {"pose", "blobs", "motion", "audio"})
    r.launch("puppet")
    launched = []
    for s in scene(persons=[Person(0.62, 0.55, 0.6).both_hands_up(at=0.0, seconds=4.0)], ticks=120):
        before = r.current_name
        r.tick(s, TICK)
        if before == "menu" and r.current_name != "menu":
            launched.append((round(s.t, 2), r.current_name))
    assert launched == [], launched


def test_repl_hand_typo_is_an_error(font5x7):
    import arcade_play
    s = arcade_play.Session(make_cfg((64, 64)), font5x7, game="puppet")
    assert s.execute("step 3 x=0.3 hand=rihgt").startswith("error")


def test_repl_shot_after_launch_is_not_stale(font5x7, tmp_path):
    import arcade_play
    s = arcade_play.Session(make_cfg((64, 64), look="plain", sdl_scale=1), font5x7, game="paint")
    s.execute("step 10 blob=0.5,0.5,255,0,0")
    s.execute("launch puppet")
    out = tmp_path / "a.png"
    reply = s.execute(f"shot {out}")
    assert reply.startswith("error") and not out.exists(), "shot shows the previous game's frame"


def test_repl_reports_crashes(font5x7):
    import arcade_play
    SpyGame.raise_on_update = True
    try:
        from arcade.games import GAMES
        GAMES.append(SpyGame)
        s = arcade_play.Session(make_cfg((64, 64)), font5x7, game="spy")
        st = json.loads(s.execute("step 40 x=0.5"))
        assert "crash" in json.dumps(st), st
    finally:
        SpyGame.raise_on_update = False
        GAMES.remove(SpyGame)


def test_shot_fails_on_crash(font5x7, tmp_path):
    import arcade_shot
    from arcade.games import GAMES
    SpyGame.raise_on_update = True
    GAMES.append(SpyGame)
    try:
        with pytest.raises(Exception):
            arcade_shot.main(["--game", "spy", "--ticks", "20", "--out", str(tmp_path / "s.png")])
    finally:
        SpyGame.raise_on_update = False
        GAMES.remove(SpyGame)


@pytest.mark.parametrize("size", [(32, 32), (48, 16), (8, 8)])
def test_menu_small_walls_do_not_raise(font5x7, size):
    from arcade.canvas import Canvas
    m = Menu(all_games(), make_cfg(size))
    m.reset(size, random.Random(0))
    c = Canvas(*size, font5x7)
    m.update(Sensed(0.0), TICK)
    m.draw(c)


def test_brightness_reaches_pixels_on_ddp():
    """Spec 4.3/10: brightness is a hard ceiling applied before push."""
    from show.display.ddp import DDPDisplay
    class S:
        def __init__(self): self.sent = []
        def sendto(self, d, a): self.sent.append(d)
    d = DDPDisplay(1, 1, "x", sock=S())
    d.set_brightness(0.4)
    d.push(np.full((1, 1, 3), 255, np.uint8))
    assert d.sock.sent[0][10] <= 102
