"""M3b's "done when" (spec 7.3, 8, 7.6): people walk up to the wall, the small lobby mirrors them and invites them,
a raised hand starts Pong, Pong plays to a result, and the end card shows it; the whole run keeps the flash rule.

Everything runs through the real runner from the lobby (run_headless(..., lobby=...)) on Pong's own scenarios,
after LEAD_IN of an empty wall: the scenarios have player 1 in front of the camera from their first frame, so
without it the wall would never be seen in attract before someone arrives. Times are read off the Sensed stream
(the first tick a body appears, the first tick the locked player's wrist is raised), not hard-coded. Trace entry
i is stream frame i."""
import zlib
from dataclasses import dataclass

import numpy as np
import pytest

from arcade.attract.lobby import Lobby
from arcade.feel import INPUTS
from arcade.flash import BUDGET, SMALL_AREA, concurrent_area, flash_area, square_flashes
from arcade.games.pong import MAX_SECONDS, WIN_POINTS, Pong
from arcade.headless import run_headless
from arcade.runner import SessionResult
from arcade.sources.actors import TICK, scene
from tests.arcade.helpers import make_cfg

WALL = (128, 64)
LEAD_IN = 1.0                  # seconds of an empty wall before the scenario
RAW_FLASH_AREA = 0.10          # spec 7.6: a game's raw output may flash at most 10 percent of the wall
MIRROR_SECONDS = 0.5           # spec 7.3: the figure within this of arrival
PICTOGRAM_SECONDS = 1.5        # the pictogram after this long near
CARD_SECONDS = 3.0             # the end card
FAR = INPUTS["far"]            # Pong's control (pong_feel.toml): -ln(body.scale), nearer is up


class RecordingLobby(Lobby):
    """The small lobby, keeping every SessionResult the runner hands it."""

    def __init__(self, games, cfg):
        super().__init__(games, cfg)
        self.results: list[SessionResult] = []

    def end_session(self, result) -> None:
        self.results.append(result)
        super().end_session(result)


@dataclass
class WalkUp:
    name: str
    seed: int
    cfg: object
    stream: list
    frames: list
    runner: object
    results: list

    @property
    def trace(self) -> list[dict]:
        return self.runner.trace

    def arrival(self) -> int:
        """The first frame with a body in it."""
        return next(i for i, s in enumerate(self.stream) if s.bodies)

    def body(self, i: int, body_id: int):
        return next((b for b in self.stream[i].bodies if b.id == body_id), None)

    def raise_index(self, after: int) -> tuple[int, int]:
        """(frame, player id): the first frame after `after` where the locked player's wrist is raised."""
        for i in range(after, len(self.stream)):
            pid = self.trace[i]["player"]
            body = None if pid is None else self.body(i, pid)
            if body is not None and body.raised_wrist is not None:
                return i, pid
        raise AssertionError(f"{self.name} seed {self.seed}: the player never raises a hand")

    def launch(self) -> int:
        return next(i for i, s in enumerate(self.trace) if s["game"] == "pong")

    def session_end(self, launch: int) -> int:
        """The first tick after launch that is not Pong's: the tick it ended on."""
        return next(i for i in range(launch, len(self.trace)) if self.trace[i]["game"] != "pong")

    def first_card(self) -> tuple[int, int]:
        """(first, stop) indices of the card after the first session; stop is the first tick after it."""
        end = self.session_end(self.launch())
        start = next(i for i in range(end, len(self.trace)) if self.trace[i].get("mode") == "card")
        stop = next((i for i in range(start, len(self.trace)) if self.trace[i].get("mode") != "card"),
                    len(self.trace))
        return start, stop

    def pong_states(self) -> list[dict]:
        """Pong's states in the first session: from the tick after the launch (the launch tick has no game state
        yet) to the last tick before it ended."""
        launch = self.launch()
        return self.trace[launch + 1:self.session_end(launch)]


def walk_up(name: str, font) -> WalkUp:
    seed = zlib.crc32(f"first_playable:{name}".encode())
    cfg = make_cfg(WALL)
    stream = list(scene(ticks=round(LEAD_IN / TICK))) + list(Pong.SCENARIOS[name]())
    lobby = RecordingLobby([Pong], cfg)
    frames, runner = run_headless(cfg, font, [Pong], stream, seed=seed, trace=True, raw=True, lobby=lobby)
    return WalkUp(name, seed, cfg, stream, frames, runner, lobby.results)


@pytest.fixture(scope="module")
def duel(font5x7) -> WalkUp:
    return walk_up("duel", font5x7)


@pytest.fixture(scope="module")
def solo(font5x7) -> WalkUp:
    return walk_up("solo", font5x7)


def test_two_players_walk_up_play_pong_and_see_the_card(duel):
    run, trace, seed = duel, duel.trace, duel.seed
    assert len(trace) == len(duel.stream)

    # Attract until someone arrives, then their mirror figure within 0.5 s.
    arrival = run.arrival()
    assert all(s["mode"] == "attract" and s["figures"] == 0 for s in trace[:arrival]), seed
    assert any(s["mode"] == "attract" for s in trace[:arrival]), f"seed {seed}: never in attract, arrival {arrival}"
    shown = next(i for i, s in enumerate(trace) if s.get("figures", 0) >= 1)
    assert trace[shown]["mode"] == "mirror" and shown - arrival <= round(MIRROR_SECONDS / TICK), (seed, arrival, shown)

    # The pictogram once the player has been near 1.5 s, before the raise.
    raised, player1 = run.raise_index(arrival)
    lobby_ticks = trace[:raised]
    assert all(not s["pictogram"] for s in lobby_ticks if s["near"] <= PICTOGRAM_SECONDS - 0.1), seed
    pictogram = next(i for i, s in enumerate(lobby_ticks) if s["pictogram"])
    assert trace[pictogram]["mode"] == "invite" and trace[pictogram]["near"] <= PICTOGRAM_SECONDS + 0.1, seed
    assert abs((pictogram - arrival) * TICK - PICTOGRAM_SECONDS) <= 2 * TICK, (seed, arrival, pictogram)

    # A raised hand starts Pong within a tick.
    launch = run.launch()
    assert all(s["game"] == "lobby" for s in trace[:launch])
    assert 0 <= launch - raised <= 1, (seed, raised, launch)

    # Two humans, no CPU; each paddle follows its own player's steps in depth (M4c: the control Pong's feel file
    # declares, "far"), and only its own: the players step on their own phases (C42: both players' points bank).
    states = run.pong_states()
    assert states, seed
    assert all(s["humans"] == 2 and s["cpu"] is None for s in states), seed
    first = launch + 1
    player2 = next(b.id for b in run.stream[first].bodies if b.id != player1)
    for key, pid, other in (("left_xy", player1, player2), ("right_xy", player2, player1)):
        far = np.array([FAR(run.body(first + k, pid)) for k in range(len(states))])
        not_mine = np.array([FAR(run.body(first + k, other)) for k in range(len(states))])
        paddle = np.array([s[key][1] for s in states])
        assert paddle.max() - paddle.min() >= WALL[1] / 2, (seed, key, paddle.min(), paddle.max())
        assert np.corrcoef(far, paddle)[0, 1] > 0.95, (seed, key, np.corrcoef(far, paddle)[0, 1])
        assert abs(np.corrcoef(not_mine, paddle)[0, 1]) < 0.5, (seed, key, np.corrcoef(not_mine, paddle)[0, 1])

    # Pong ends done, at 5 points or at 90 s.
    last = states[-1]
    end = run.session_end(launch)
    played = trace[end]["t"] - trace[launch]["t"]
    assert last["phase"] == "over", (seed, last)
    assert max(last["left"], last["right"]) == WIN_POINTS or played >= MAX_SECONDS, (seed, last, played)
    assert all(max(s["left"], s["right"]) <= WIN_POINTS for s in states), seed

    # The runner's SessionResult.
    assert run.results, seed
    result = run.results[0]
    assert (result.game, result.reason, result.players, result.score) == ("pong", "done", 2, last["score"]), \
        (seed, result, last)

    # Then the end card with that score for 3 s. The tick Pong ended on shows only the runner's keys.
    start, stop = run.first_card()
    assert start - end <= 1, (seed, end, start)
    assert stop < len(trace), f"seed {seed}: the scenario ends during the card"
    assert abs((stop - start) - round(CARD_SECONDS / TICK)) <= 1, (seed, start, stop)
    for s in trace[start:stop]:
        assert (s["card_game"], s["card_score"], s["card_reason"]) == ("pong", result.score, "done"), (seed, s)


def test_solo_walk_up_plays_the_cpu(solo):
    run, seed = solo, solo.seed
    states = run.pong_states()
    assert states, seed
    assert all(s["humans"] == 1 and s["cpu"] == "right" for s in states), seed
    assert run.results, seed
    result = run.results[0]
    assert (result.game, result.reason, result.players) == ("pong", "done", 1), (seed, result)
    assert result.score == states[-1]["score"], (seed, result, states[-1])
    best = run.runner.scores.best("pong", run.cfg.layout)
    assert best is not None and result.best == result.score, (seed, best, result)


def test_first_playable_keeps_the_flash_rule(duel):
    seed, cfg = duel.seed, duel.cfg
    assert "pong" in {s["game"] for s in duel.trace} and duel.results, seed
    pushed, raw = duel.frames, duel.runner.raw_frames
    assert len(pushed) == len(raw) == len(duel.stream)
    kw = {"gamma": cfg.gamma, "fps": cfg.fps}
    assert square_flashes(pushed, **kw) <= BUDGET, seed
    assert concurrent_area(pushed, **kw) < SMALL_AREA, seed
    assert flash_area(raw, **kw) <= RAW_FLASH_AREA, seed
    # From the empty wall through the walk-up, the invite, the launch, the game and its card, nothing flashes.
    _, stop = duel.first_card()
    assert flash_area(pushed[:stop], **kw) == 0.0, seed
    # Over the whole run the governor passes only a small-area flash (Q13): the scenario's steps go on between
    # games, and the lobby's mirror figure follows the stepping body, so a pixel or two of its outline can switch
    # more than 3 times a second. The governor never adds a flash.
    assert flash_area(pushed, **kw) <= flash_area(raw, **kw), seed


def test_canonical_round_from_attract_to_the_card(font5x7):
    cfg = make_cfg(WALL)
    lobby = RecordingLobby([Pong], cfg)

    def until_the_card_is_gone(runner):
        """Canonical's frames, stopped on the first tick after the first card has shown."""
        carded = False
        for frame in Pong.SCENARIOS["canonical"]():
            yield frame
            mode = runner.trace[-1].get("mode")
            carded = carded or mode == "card"
            if carded and mode != "card" and mode is not None:
                return

    _, runner = run_headless(cfg, font5x7, [Pong], until_the_card_is_gone, trace=True, lobby=lobby)
    trace = runner.trace
    modes = []
    for s in trace:
        mode = s.get("mode") if s["game"] == "lobby" else s["game"]
        if mode is not None and (not modes or modes[-1] != mode):    # the tick a game ends on has no lobby mode
            modes.append(mode)
    assert modes[:5] == ["attract", "mirror", "invite", "pong", "card"], modes
    assert len(trace) < len(list(Pong.SCENARIOS["canonical"]())), "the run was cut short only by the card ending"
    assert len(lobby.results) == 1, lobby.results
    last = next(s for s in reversed(trace) if s["game"] == "pong")
    card = next(s for s in trace if s.get("mode") == "card")
    assert card["card_game"] == "pong" and card["card_score"] == last["score"] == lobby.results[0].score, (card, last)
