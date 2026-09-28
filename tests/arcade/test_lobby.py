import numpy as np
import pytest

from arcade.attract.lobby import (BREATH_LOW, CARD_SECONDS, HAND_UP, MODES, PICTOGRAM_COLOR, PICTOGRAM_SECONDS,
                                  TEXT_COLOR, TITLE_COLOR, Lobby)
from arcade.canvas import Canvas
from arcade.flash import BUDGET, SMALL_AREA, concurrent_area, flash_area, square_flashes
from arcade.game import reserved
from arcade.games import MENU_ORDER
from arcade.headless import run_headless
from arcade.juice import PLAYER_COLORS
from arcade.runner import LobbyLike, SessionResult
from arcade.sensed import Sensed
from arcade.sources.actors import REAL_NOISE, TICK, Person, degrade, scene
from tests.arcade.helpers import make_cfg, spy

AMBER, BLUE = PLAYER_COLORS
KEYS = {"mode", "near", "pictogram", "figures", "featured", "card_game", "card_score", "card_reason", "card_waiting",
        "figure_xy", "pictogram_xy"}


def lobby_run(font, games, persons, seconds, size=(128, 32), lobby=None, strict=True, setup=None):
    """The small lobby over a scene of persons for seconds, through the real runner: (lobby, runner). The trace's
    entry i is scene frame i, at runner t (i + 1) * TICK."""
    cfg = make_cfg(size)
    lobby = Lobby(games, cfg) if lobby is None else lobby
    if setup is not None:
        setup(lobby)
    _, runner = run_headless(cfg, font, games, scene(persons=persons, ticks=round(seconds / TICK)), trace=True,
                             raw=True, lobby=lobby, strict=strict)
    return lobby, runner


def colours(frame) -> set:
    return {tuple(int(v) for v in px) for px in frame[frame.any(axis=2)]}


def frame_index(t: float) -> int:
    """The scene frame (and trace entry) a Person script time t first shows on."""
    return round(t / TICK)


def launches(runner) -> list[tuple[int, str]]:
    """(trace index, game) of every tick a game starts from the lobby."""
    games = [s["game"] for s in runner.trace]
    return [(i, g) for i, g in enumerate(games) if g != "lobby" and (i == 0 or games[i - 1] == "lobby")]


def card_run(runner) -> tuple[int, int]:
    """(first index, length) of the first run of card ticks."""
    modes = [s.get("mode") for s in runner.trace]
    start = modes.index("card")
    end = next((i for i in range(start, len(modes)) if modes[i] != "card"), len(modes))
    return start, end - start


def test_implements_lobbylike():
    game_only = {"scores", "PHASES", "SCENARIOS", "CAPTION_KEYS"}    # a launched game's: never read from the lobby
    members = set(LobbyLike.__protocol_attrs__) - game_only
    assert members == {"reset", "update", "draw", "done", "debug_state", "set_available", "set_status",
                       "end_session", "request", "info"}
    lobby = Lobby([spy("pong")], make_cfg((128, 32)))
    for name in members - {"request", "info"}:
        assert callable(getattr(lobby, name)), name
    assert lobby.info is None and lobby.request is None and lobby.done() is False
    assert MODES == ("attract", "mirror", "invite", "card")
    assert HAND_UP.shape == (16, 16) and HAND_UP.dtype == bool and not HAND_UP.flags.writeable


def test_two_bodies_two_colours(font5x7, size):
    persons = [Person(0.3, id=1), Person(0.7, id=2)]
    _, runner = lobby_run(font5x7, [spy("pong")], persons, 1.0, size)
    frame, state = runner.raw_frames[-1], runner.trace[-1]
    assert state["mode"] == "mirror" and state["figures"] == 2
    assert colours(frame) == {AMBER, BLUE}
    cols = {c: np.flatnonzero((frame == c).all(axis=2).any(axis=0)).mean() for c in (AMBER, BLUE)}
    player_left = state["player"] == 1                               # Person 1 stands left
    assert bool(cols[AMBER] < cols[BLUE]) is player_left, (state["player"], cols)


def test_attract_shows_the_featured_title_statically(font5x7, size):
    _, runner = lobby_run(font5x7, [spy("paint"), spy("pong")], [], 2.0, size)
    frames = runner.raw_frames
    assert all(np.array_equal(f, frames[0]) for f in frames)
    assert colours(frames[0]) == {TITLE_COLOR}
    assert {s["mode"] for s in runner.trace} == {"attract"} and runner.trace[-1]["featured"] == "pong"
    assert runner.trace[-1]["figures"] == 0 and runner.trace[-1]["figure_xy"] is None
    lit = np.flatnonzero(frames[0].any(axis=(0, 2)))
    assert abs((lit[0] + lit[-1]) / 2 - (size[0] - 1) / 2) <= 3        # centred
    _, runner = lobby_run(font5x7, [spy("pong", info={"layouts": frozenset({"1x1"})})], [], 0.5, size)
    assert runner.trace[-1]["featured"] is None and not any(f.any() for f in runner.raw_frames)


def test_mirror_within_half_second(font5x7, size):
    arrive = frame_index(1.0)
    _, runner = lobby_run(font5x7, [spy("pong")], [Person(0.5, id=1).arrive(1.0)], 1.6, size)
    trace = runner.trace
    assert all(s["mode"] == "attract" and s["figures"] == 0 for s in trace[:arrive])
    shown = next(i for i, s in enumerate(trace) if s["figures"] == 1)
    assert shown - arrive <= round(0.5 / TICK), (shown, arrive)
    assert trace[shown]["mode"] == "mirror" and AMBER in colours(runner.raw_frames[shown])
    assert all(s["figures"] == 1 for s in trace[shown:])
    x, y = trace[-1]["figure_xy"]
    assert 0 <= x < size[0] and 0 <= y < size[1]


@pytest.mark.parametrize("x", [0.3, 0.7])
def test_pictogram_after_1_5s(font5x7, x):
    _, runner = lobby_run(font5x7, [spy("pong")], [Person(x, id=1)], 4.5)
    trace = runner.trace
    assert all(not s["pictogram"] for s in trace if s["near"] <= 1.4)
    first = next(i for i, s in enumerate(trace) if s["pictogram"])
    assert trace[first]["near"] <= 1.6 and trace[first]["mode"] == "invite"
    assert all(s["pictogram"] and s["mode"] == "invite" for s in trace[first:])
    green = []
    for frame in runner.raw_frames[first:first + 60]:
        icon = (frame[..., 1] > 0) & (frame[..., 0] == 0) & (frame[..., 2] == 0)
        assert icon.any()
        green.append(int(frame[..., 1][icon].max()))
        figure = (frame == AMBER).all(axis=2)
        icon_cols, figure_cols = np.flatnonzero(icon.any(axis=0)), np.flatnonzero(figure.any(axis=0))
        assert set(icon_cols).isdisjoint(figure_cols)                   # beside the figure, not over it
        assert bool(icon_cols.min() > figure_cols.max()) is (x < 0.5)  # on the side with more room
    green = np.array(green)
    assert green.max() == PICTOGRAM_COLOR[1] and abs(green.min() - BREATH_LOW * PICTOGRAM_COLOR[1]) <= 2
    peak = int(green[:30].argmax())
    assert abs(int(green[30:].argmax()) + 30 - peak - 30) <= 1, green   # it swings at 1 Hz
    assert green[(peak + 15) % 30] < 0.5 * PICTOGRAM_COLOR[1]
    px, py = trace[first]["pictogram_xy"]
    assert 0 <= px < 128 and 0 <= py < 32
    assert PICTOGRAM_SECONDS == 1.5


@pytest.mark.parametrize("at", [0.5, 2.5])                           # in mirror, then in invite
def test_raised_hand_requests_the_featured_game(font5x7, at):
    games = [spy("paint"), spy("pong")]
    _, runner = lobby_run(font5x7, games, [Person(0.5, id=1).raise_hand(at=at, seconds=0.5)], at + 1.0)
    raised = frame_index(at)
    assert all(s["game"] == "lobby" for s in runner.trace[:raised])
    (start, name), = launches(runner)
    assert name == "pong" and start - raised <= 1, (start, raised)
    assert type(runner.game).info.name == "pong"


def test_hand_up_on_arrival_does_not_start(font5x7):
    person = Person(0.5, id=1).arrive(1.0).raise_hand(at=1.0, seconds=3.0).raise_hand(at=5.0, seconds=0.5)
    _, runner = lobby_run(font5x7, [spy("pong")], [person], 6.0)
    raised = frame_index(5.0)
    assert any(s["pictogram"] for s in runner.trace[:raised])        # it was inviting all along
    (start, name), = launches(runner)
    assert name == "pong" and 0 <= start - raised <= 1, (start, raised)


def test_featured_is_first_in_menu_order_that_fits(font5x7):
    cfg = make_cfg((128, 32))
    copyme = spy("copyme", raise_in=frozenset({"reset"}))
    wrong_layout = spy("pong", info={"layouts": frozenset({"64x64"})})
    needs_audio = spy("paint", info={"needs": frozenset({"pose", "audio"})})
    games = [needs_audio, spy("dodge"), wrong_layout, spy("quickdraw"), copyme]
    lobby = Lobby(games, cfg)
    lobby.set_available({g.info.name for g in games})
    assert lobby.featured() == "copyme"
    lobby.set_available({"pong", "paint", "quickdraw", "dodge"})       # copyme hidden
    assert lobby.featured() == "paint"                                # every input until set_status
    lobby.set_status(True, False, {"pose", "blobs", "motion"}, True)
    assert lobby.featured() == "quickdraw"
    lobby.set_available(set())
    assert lobby.featured() is None
    assert Lobby([spy("spy")], cfg).featured() is None                 # not in MENU_ORDER
    assert MENU_ORDER.index("copyme") < MENU_ORDER.index("pong") < MENU_ORDER.index("paint")

    # Through the runner: copyme crashes three times and is hidden, then the next that fits is requested.
    person = Person(0.5, id=1)
    for at in (1.0, 5.0, 9.0, 13.0):
        person.raise_hand(at=at, seconds=0.5)
    _, runner = lobby_run(font5x7, games, [person], 14.0, strict=False,
                          setup=lambda lb: lb.set_status(True, False, {"pose", "blobs", "motion"}, True))
    assert runner.crashes == {"copyme": 3} and runner.hidden == {"copyme"}
    assert [name for _, name in launches(runner)] == ["copyme"] * 3 + ["quickdraw"]
    assert type(runner.game).info.name == "quickdraw"


def test_end_card_shows_the_result_for_3_seconds(font5x7, size):
    game = spy("pong", finish_after=30, extra={"score": 3})
    _, runner = lobby_run(font5x7, [game], [Person(0.5, id=1).raise_hand(at=1.0, seconds=0.5)], 5.5, size)
    start, length = card_run(runner)
    assert abs(length - round(CARD_SECONDS / TICK)) <= 1, length
    for s, frame in zip(runner.trace[start:start + length], runner.raw_frames[start:start + length]):
        assert (s["card_game"], s["card_score"], s["card_reason"], s["card_waiting"]) == ("pong", 3.0, "done", False)
        assert s["figures"] == 0 and colours(frame) == {TEXT_COLOR}
    after = runner.trace[start + length]
    assert after["mode"] in ("mirror", "invite") and after["figures"] == 1
    assert all(after[k] is None for k in ("card_game", "card_score", "card_reason", "card_waiting"))


def card_frame(font, size, **result):
    cfg = make_cfg(size)
    lobby = Lobby([spy("pong")], cfg)
    lobby.reset(cfg.size, None)
    lobby.end_session(SessionResult(**({"game": "pong", "layout": cfg.layout, "reason": "done", "score": 3.0,
                                        "duration": 5.0, "players": 1, "best": None, "waiting": False} | result)))
    lobby.update(Sensed(1.0), TICK)
    canvas = Canvas(*size, font)
    lobby.draw(canvas)
    assert lobby.debug_state()["mode"] == "card"
    return canvas.frame


def test_end_card_says_best_on_a_record(font5x7, size):
    plain = card_frame(font5x7, size)
    record = card_frame(font5x7, size, best=3.0)
    beaten = card_frame(font5x7, size, best=4.0)
    no_score = card_frame(font5x7, size, score=None, best=3.0)
    assert np.array_equal(plain, beaten) and not np.array_equal(plain, record)
    assert not np.array_equal(plain, no_score) and colours(record) == {TEXT_COLOR}
    assert record.any(axis=2).sum() > plain.any(axis=2).sum()


def test_end_card_says_next_when_someone_waits(font5x7):
    game = spy("pong", finish_after=30, extra={"score": 3})
    player = lambda: Person(0.3, id=1).raise_hand(at=1.0, seconds=0.5)
    _, alone = lobby_run(font5x7, [game], [player()], 3.0)
    waiting = [Person(0.5, height=0.55, id=2), Person(0.7, height=0.55, id=3)]   # smaller: Person 1 is the player
    _, crowd = lobby_run(font5x7, [game], [player()] + waiting, 3.0)
    (a, _), (c, _) = card_run(alone), card_run(crowd)
    assert alone.trace[a]["card_waiting"] is False and crowd.trace[c]["card_waiting"] is True
    assert not np.array_equal(alone.raw_frames[a], crowd.raw_frames[c])


def test_hands_during_the_card_do_nothing(font5x7):
    game = spy("pong", finish_after=30, extra={"score": 3})
    person = (Person(0.5, id=1).raise_hand(at=1.0, seconds=0.5)
              .raise_hand(at=3.0, seconds=0.5)                         # during the card
              .raise_hand(at=4.6, seconds=1.0)                         # up as the card ends
              .raise_hand(at=6.5, seconds=0.5))                        # after it
    _, runner = lobby_run(font5x7, [game], [person], 7.5)
    start, length = card_run(runner)
    assert runner.trace[start]["t"] < 3.0 < 4.6 < runner.trace[start + length - 1]["t"] < 5.6
    assert abs(length - round(CARD_SECONDS / TICK)) <= 1
    (first, _), (second, _) = launches(runner)
    assert first < start and 0 <= second - frame_index(6.5) <= 1, (first, second)


def test_lobby_frames_keep_the_flash_rule(font5x7, size):
    game = spy("pong", finish_after=60, extra={"score": 2})
    person = Person(0.45, id=1).arrive(0.5).raise_hand(at=3.5, seconds=0.5)
    _, runner = lobby_run(font5x7, [game], [person], 10.0, size)
    modes = {s.get("mode") for s in runner.trace}
    assert {"attract", "mirror", "invite", "card"} <= modes and "pong" in {s["game"] for s in runner.trace}
    raw = runner.raw_frames
    assert flash_area(raw) == 0.0
    assert concurrent_area(raw) < SMALL_AREA
    assert square_flashes(raw) <= BUDGET


@pytest.mark.parametrize("size", [(128, 32), (64, 64)])
def test_mirror_under_real_noise_keeps_the_area_rule(font5x7, size):
    # C37, the input of evidence/it06/reviewer-notes.md: before the hold, 64x64 reached 0.131 to 0.151.
    cfg = make_cfg(size)
    runs = [((pid, x),) for pid, x in ((1, 0.45), (2, 0.3), (3, 0.6), (7, 0.5))] + [((1, 0.3), (2, 0.7))]
    for who in runs:
        game = spy("pong")
        lobby = Lobby([game], cfg)
        persons = [Person(x, id=pid).arrive(0.5) for pid, x in who]
        _, runner = run_headless(cfg, font5x7, [game], degrade(scene(persons=persons, ticks=600), **REAL_NOISE),
                                 lobby=lobby, raw=True)
        assert lobby.debug_state()["figures"] == len(who), (size, who)       # the mirror was drawn to the end
        area = concurrent_area(runner.raw_frames)
        assert area < SMALL_AREA, (size, who, area)


def test_debug_keys_are_not_reserved(font5x7):
    game = spy("pong", finish_after=30, extra={"score": 3})
    lobby, runner = lobby_run(font5x7, [game], [Person(0.5, id=1).raise_hand(at=2.0, seconds=0.5)], 4.0)
    assert set(lobby.debug_state()) == KEYS and not any(reserved(k) for k in KEYS)
    for before, s in zip(runner.trace, runner.trace[1:]):
        if s["game"] == "lobby" and before["game"] == "lobby":     # a game that ends on done skips the lobby's tick
            assert KEYS <= set(s) and s["mode"] in MODES
            for key in ("figure_xy", "pictogram_xy"):
                assert s[key] is None or (len(s[key]) == 2 and all(isinstance(v, int) for v in s[key]))
