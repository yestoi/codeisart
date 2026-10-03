import numpy as np
import pytest

from arcade.attract.lobby import (BIG_ROWS, BIG_SCALE, BREATH_LOW, CARD_SECONDS, COLUMN_SLACK, HAND_UP, MODES,
                                  PICTOGRAM_COLOR, PICTOGRAM_SECONDS, TEXT_COLOR, TITLE_COLOR, Lobby)
from arcade.canvas import Canvas
from arcade.flash import BUDGET, SMALL_AREA, concurrent_area, flash_area, square_flashes
from arcade.game import reserved
from arcade.games import MENU_ORDER
from arcade.headless import run_headless
from arcade.juice import PLAYER_COLORS
from arcade.runner import LobbyLike, SessionResult
from arcade.sensed import Body, Sensed
from arcade.sources.actors import REAL_NOISE, TICK, Person, body_box, degrade, make_keypoints, scene
from tests.arcade.helpers import make_cfg, spy

AMBER, BLUE = PLAYER_COLORS
KEYS = {"mode", "near", "pictogram", "figures", "featured", "card_game", "card_score", "card_reason", "card_waiting",
        "figure_xy", "pictogram_xy"}


@pytest.fixture(params=[(128, 64), (128, 32), (64, 64)], ids=["128x64", "128x32", "64x64"])
def size(request) -> tuple[int, int]:
    """conftest's sizes plus the wall's own: every sized lobby test also runs at 128x64."""
    return request.param


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
    record = card_frame(font5x7, size, best=3.0, new_best=True)
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


# ----- laid out for 64 rows (iteration 8, P2) -----

def bands(frame) -> list[int]:
    """The heights of the runs of lit rows, top to bottom: one per line of text."""
    rows = np.flatnonzero(frame.any(axis=(1, 2)))
    runs = np.split(rows, np.flatnonzero(np.diff(rows) > 1) + 1)
    return [len(r) for r in runs]


def card_lobby(font, size, games, **result):
    """(frame, lobby): the card of a SessionResult for games[0] (result overrides), drawn at size."""
    cfg = make_cfg(size)
    lobby = Lobby(games, cfg)
    name = games[0].info.name
    lobby.end_session(SessionResult(**({"game": name, "layout": cfg.layout, "reason": "done", "score": 3.0,
                                        "duration": 5.0, "players": 1, "best": None, "waiting": False} | result)))
    lobby.update(Sensed(1.0), TICK)
    canvas = Canvas(*size, font)
    lobby.draw(canvas)
    return canvas.frame, lobby


def test_attract_title_is_2x_on_a_tall_wall_and_1x_on_128x32(font5x7, size):
    assert (BIG_ROWS, BIG_SCALE) == (48, 2)
    _, runner = lobby_run(font5x7, [spy("pong")], [], 1.0, size)
    frames = runner.raw_frames
    assert len(frames) >= 30 and all(np.array_equal(f, frames[0]) for f in frames)    # static over 30 ticks
    tall = size[1] >= BIG_ROWS                                   # "PONG" is 48 px wide at 2x: it fits 64 columns
    assert bands(frames[0]) == [7 * BIG_SCALE if tall else 7], size
    rows = np.flatnonzero(frames[0].any(axis=(1, 2)))
    assert abs((rows[0] + rows[-1]) / 2 - (size[1] - 1) / 2) <= 1, (size, rows)


def test_card_fits_64_rows_with_best(font5x7):
    frame, lobby = card_lobby(font5x7, (128, 64), [spy("pong")], best=3.0, new_best=True)
    assert colours(frame) == {TEXT_COLOR}
    assert bands(frame) == [7 * BIG_SCALE, 7 * BIG_SCALE, 7]         # "PONG 3" and "BEST!" at 2x, the prompt at 1x
    rows, cols = np.flatnonzero(frame.any(axis=(1, 2))), np.flatnonzero(frame.any(axis=(0, 2)))
    assert 0 < rows[0] and rows[-1] < 63 and 0 < cols[0] and cols[-1] < 127, (rows, cols)
    assert abs((rows[0] + rows[-1]) / 2 - 31.5) <= 1 and abs((cols[0] + cols[-1]) / 2 - 63.5) <= 1, (rows, cols)
    state = lobby.debug_state()
    assert set(state) == KEYS
    assert (state["mode"], state["card_game"], state["card_score"], state["card_reason"], state["card_waiting"]) == \
        ("card", "pong", 3.0, "done", False)


def test_card_falls_back_to_1x_when_2x_does_not_fit(font5x7):
    long = spy("pong", info={"title": "PONG CHAMPIONSHIP"})            # 204 px at 2x, 102 at 1x
    frame, _ = card_lobby(font5x7, (128, 64), [long])
    assert bands(frame) == [7, 7]                                     # "PONG CHAMPIONSHIP 3", then the prompt
    frame, _ = card_lobby(font5x7, (128, 64), [long], best=3.0, new_best=True)
    assert bands(frame) == [7, 7 * BIG_SCALE, 7]                      # BEST! still fits at 2x
    _, runner = lobby_run(font5x7, [long], [], 0.2, (128, 64))
    assert bands(runner.raw_frames[-1]) == [7]                        # the attract title too


# ----- "BEST!" only for a new best above 0 (iteration 9, P2: C43, Q41) -----

def test_end_card_says_best_only_for_a_new_best(font5x7, size):
    plain = card_frame(font5x7, size)
    tied = card_frame(font5x7, size, best=3.0, new_best=False)       # the night's best, not beaten tonight
    assert np.array_equal(plain, tied)
    zero = card_frame(font5x7, size, score=0.0, best=0.0, new_best=True)
    assert np.array_equal(zero, card_frame(font5x7, size, score=0.0))  # a first 0 is no record to cheer
    record = card_frame(font5x7, size, best=3.0, new_best=True)
    assert not np.array_equal(plain, record) and colours(record) == {TEXT_COLOR}
    assert record.any(axis=2).sum() > plain.any(axis=2).sum()


def scorer(score: float) -> type:
    """A "pong" spy that records score in tonight's scores on its last update and reports it, as a game's _finish."""
    base = spy("pong", finish_after=30, extra={"score": score})

    def update(self, sensed, dt):
        base.update(self, sensed, dt)
        if self.updates == self.finish_after:
            self.scores.record(score)

    return type("Scorer", (base,), {"update": update})


def card_bands(runner) -> list[list[int]]:
    """bands() of the first frame of every run of card ticks, in order."""
    modes = [s.get("mode") for s in runner.trace]
    starts = [i for i, m in enumerate(modes) if m == "card" and (i == 0 or modes[i - 1] != "card")]
    return [bands(runner.raw_frames[i]) for i in starts]


BIG, SMALL = 7 * BIG_SCALE, 7


def test_best_shows_once_for_a_repeated_score(font5x7):
    # it08's walk-up, sessions 1 to 3: every session's 3 said BEST!, as the night's best only equalled it.
    person = Person(0.5, id=1).raise_hand(at=1.0, seconds=0.5).raise_hand(at=6.5, seconds=0.5)
    _, runner = lobby_run(font5x7, [scorer(3.0)], [person], 9.0, (128, 64))
    assert [name for _, name in launches(runner)] == ["pong", "pong"]
    assert runner.scores.best("pong", "128x64") == 3.0
    assert card_bands(runner) == [[BIG, BIG, SMALL], [BIG, SMALL]]       # "PONG 3", BEST!, prompt; then no BEST!


def test_a_zero_score_never_says_best(font5x7):
    person = Person(0.5, id=1).raise_hand(at=1.0, seconds=0.5)
    _, runner = lobby_run(font5x7, [scorer(0.0)], [person], 3.5, (128, 64))
    assert runner.scores.best("pong", "128x64") == 0.0                  # the night's first: the runner's new_best
    assert card_bands(runner) == [[BIG, SMALL]]                          # "PONG 0", the prompt; no BEST!


@pytest.mark.parametrize("x", [0.3, 0.7])
def test_pictogram_beside_a_full_height_figure_on_128x64(font5x7, x):
    _, runner = lobby_run(font5x7, [spy("pong")], [Person(x, id=1)], 2.5, (128, 64))
    first = next(i for i, s in enumerate(runner.trace) if s["pictogram"])
    assert len(runner.trace) - first >= 15
    for s, frame in zip(runner.trace[first:], runner.raw_frames[first:]):
        icon = (frame[..., 1] > 0) & (frame[..., 0] == 0) & (frame[..., 2] == 0)
        figure = (frame == AMBER).all(axis=2)
        assert icon.sum() == HAND_UP.sum()                               # all of it inside the wall
        fr, fc = np.flatnonzero(figure.any(axis=1)), np.flatnonzero(figure.any(axis=0))
        ic = np.flatnonzero(icon.any(axis=0))
        assert fr[-1] - fr[0] + 1 >= 56, fr                               # the figure fills the wall's height
        assert ic[-1] < fc[0] or ic[0] > fc[-1], (ic, fc)                 # not over the figure's box
        px, py = s["pictogram_xy"]
        assert 8 <= px <= 128 - 8 and 8 <= py <= 64 - 8


def test_lobby_holds_no_tick_at_128x64(font5x7):
    game = spy("pong", finish_after=60, extra={"score": 2})
    person = Person(0.45, id=1).arrive(0.5).raise_hand(at=3.5, seconds=0.5)
    _, runner = lobby_run(font5x7, [game], [person], 10.0, (128, 64))
    assert {"attract", "mirror", "invite", "card"} <= {s.get("mode") for s in runner.trace}
    assert max(s["flash_held_ticks"] for s in runner.trace) == 0


def test_a_column_jitter_does_not_step_the_figure():
    # At 128 columns the camera's zone_x jitter moved the whole figure a column most captures, and the mirror
    # under REAL_NOISE reached concurrent_area 0.1006 at 128x64. The figure's column keeps COLUMN_SLACK px of play.
    assert COLUMN_SLACK == 1
    lobby = Lobby([spy("pong")], make_cfg((128, 64)))
    kps = make_keypoints(0.5, 0.55, 0.6)

    def figure_x(column: float, t: float) -> int:
        lobby.update(Sensed(t, player=Body(1, body_box(kps), kps, zone_x=column / 127)), TICK)
        return lobby.debug_state()["figure_xy"][0]

    still = {figure_x(50.4 if i % 2 else 50.6, i * TICK) for i in range(30)}       # columns 50 and 51 in turn
    assert len(still) == 1, still
    moved = figure_x(60.0, 1.0)
    assert moved - still.pop() == 60 - 51 - COLUMN_SLACK                             # it follows a real move
    assert figure_x(59.4, 1.1) == moved


def test_mirror_figure_moves_between_captures(font5x7):
    # The Pi's pose rate is 15 a second and the wall draws 30: the figure glides from capture to capture
    # (figure.FigureGlide) instead of stepping with them.
    size = (128, 64)
    lobby = Lobby([spy("pong")], make_cfg(size))
    lobby.reset(size, None)

    def tick(t, camera_t, cx):
        kps = make_keypoints(cx, 0.55, 0.6)
        body = Body(1, body_box(kps), kps, zone_x=cx)
        lobby.update(Sensed(t, camera_t=camera_t, bodies=(body,), player=body, present=True), TICK)
        assert lobby.mode == "mirror"
        return lobby.debug_state()["figure_xy"][0]

    period = 1 / 15
    left = tick(0.0, 0.0, 0.3)
    assert tick(period, period, 0.7) == left                 # the new capture starts the move from the old place
    mid = tick(1.5 * period, period, 0.7)
    right = tick(2 * period, period, 0.7)
    assert left < mid < right, (left, mid, right)
    assert right - left > 30                                  # 0.3 to 0.7 of a 128-wide wall


# ----- step-in start (docs/superpowers/specs/2026-10-03-step-in-start-design.md) -----

from arcade.attract.lobby import STEP_IN_SECONDS


def step_in_run(font, persons, seconds, size=(128, 64)):
    """The lobby with --game's flag over a scene, through the real runner. The one game is a spy called pong
    that ends 30 updates (1 s) after it starts, so its card follows and the count can start again."""
    games = [spy("pong", finish_after=30)]
    return lobby_run(font, games, persons, seconds, size=size,
                     setup=lambda lobby: setattr(lobby, "start_on_step_in", True))


def test_step_in_starts_the_game_after_two_seconds(font5x7):
    _, runner = step_in_run(font5x7, [Person(0.5, id=1).arrive(1.0)], 4.0)
    starts = launches(runner)
    assert len(starts) == 1 and starts[0][1] == "pong"
    at = starts[0][0] * TICK
    assert 1.0 + STEP_IN_SECONDS - 0.1 <= at <= 1.0 + STEP_IN_SECONDS + 0.2, at


def test_a_crossing_does_not_start(font5x7):
    """Review Focus 4: in the zone for 1.5 s and out again."""
    person = Person(0.5, id=1).arrive(1.0).leave(2.5)
    _, runner = step_in_run(font5x7, [person], 5.0)
    assert launches(runner) == []


def test_step_in_count_restarts_after_leaving(font5x7):
    """Review Focus 1: in at 1.0, out at 2.0, back at 3.0 as a new track id (the tracker never reuses one, and a
    Person has one arrive and one leave): the game starts near 5.0, not 4.0."""
    persons = [Person(0.5, id=1).arrive(1.0).leave(2.0), Person(0.5, id=2).arrive(3.0)]
    _, runner = step_in_run(font5x7, persons, 7.0)
    starts = launches(runner)
    assert len(starts) == 1
    at = starts[0][0] * TICK
    assert at >= 3.0 + STEP_IN_SECONDS - 0.1, at


def test_raised_hand_does_not_start_in_step_in_mode(font5x7):
    """Review Focus 3: a hand up at 1.2 s for half a second, with the player gone by 1.9 s."""
    person = Person(0.5, id=1).arrive(1.0).raise_hand(at=1.2, seconds=0.5).leave(1.9)
    _, runner = step_in_run(font5x7, [person], 4.0)
    assert launches(runner) == []


def test_after_the_card_the_count_starts_again(font5x7):
    """Review Focus 2: the player stays; the second game starts two seconds after the card ends, not at once."""
    _, runner = step_in_run(font5x7, [Person(0.5, id=1).arrive(0.5)], 12.0)
    starts = launches(runner)
    assert len(starts) >= 2, starts
    card_start, card_len = card_run(runner)
    card_end = card_start + card_len
    assert starts[1][0] - card_end >= round(STEP_IN_SECONDS / TICK) - 3, (starts, card_end)


def test_second_body_does_not_shorten_the_count(font5x7):
    """Review Focus 5: a second body arriving at 2.0 s does not start the game before the player's two seconds."""
    _, runner = step_in_run(font5x7, [Person(0.4, id=1).arrive(1.5), Person(0.6, id=2, height=0.5).arrive(2.0)], 5.0)
    starts = launches(runner)
    assert len(starts) == 1 and starts[0][0] * TICK >= 1.5 + STEP_IN_SECONDS - 0.1


def test_no_pictogram_in_step_in_mode(font5x7):
    """Also the spec's 1.9 s: a player present 1.4 s (0.5 to 1.9) has not started the game."""
    lobby, runner = step_in_run(font5x7, [Person(0.5, id=1).arrive(0.5)], 1.9)
    assert all(s.get("pictogram") in (None, False) for s in runner.trace)
    assert all(s.get("mode") != "invite" for s in runner.trace)
    assert launches(runner) == []


def test_without_the_flag_nothing_changes(font5x7):
    _, runner = lobby_run(font5x7, [spy("pong", finish_after=30)], [Person(0.5, id=1).arrive(1.0)], 6.0)
    assert launches(runner) == [], "standing still never starts a game in the default lobby"


def test_step_in_debug_state_has_progress(font5x7):
    lobby, runner = step_in_run(font5x7, [Person(0.5, id=1).arrive(0.5)], 1.5)
    last = runner.trace[-1]
    assert 0.0 < last["step_in"] < 1.0


# ----- the step-in card's words (owner, 2026-10-03: no "HAND UP" where a hand does nothing) -----

from arcade.attract.lobby import card_prompt


def test_card_prompt_words():
    assert card_prompt(waiting=False, step_in=False) == "HAND UP = AGAIN"
    assert card_prompt(waiting=True, step_in=False) == "NEXT: RAISE A HAND"
    assert card_prompt(waiting=False, step_in=True) == "STAY = AGAIN"
    assert card_prompt(waiting=True, step_in=True) == "NEXT: STEP IN"


def test_step_in_card_never_asks_for_a_hand(font5x7, size):
    """In step-in mode the card draws the step-in words: its frame differs from the default card's, and the default
    card is unchanged."""
    cfg = make_cfg(size)
    lobby = Lobby([spy("pong")], cfg, start_on_step_in=True)
    lobby.end_session(SessionResult(game="pong", layout=cfg.layout, reason="done", score=3.0, duration=5.0,
                                    players=1, best=None, waiting=False))
    lobby.update(Sensed(1.0), TICK)
    canvas = Canvas(*size, font5x7)
    lobby.draw(canvas)
    assert lobby.debug_state()["mode"] == "card"
    default = card_frame(font5x7, size)
    assert not np.array_equal(canvas.frame, default), "the step-in card reads differently"
    assert np.array_equal(default, card_frame(font5x7, size)), "the default card is as it was"
