"""The oracle end to end on every game (I1, it15's I0): feel's report against the budgets, the bots' ranking, and
Pong's evidence package.

One 20-seed report (spec 9.3's count) is measured per game per module and shared. A failing budget is fixed in the
game's own files or sent to the owner, never loosened here."""
import json

import pytest

from arcade import bots, feel
from arcade.games import all_games
from arcade.games.pong import Pong
from tests.arcade.helpers import PLAYS, play_key

LAYOUT = "128x64"
SEEDS = bots.seeds(Pong, LAYOUT, 20)
OTHER_GAMES = [game for game in all_games() if game is not Pong]   # Pong keeps its own three tests below

REPORTS: dict[str, dict] = {}   # one 20-seed report per game (by name), shared by its two tests


@pytest.fixture(scope="module", autouse=True)
def shared_plays():
    """bots.play, memoised in PLAYS for plays with the default won, seconds and no frames, for this module."""
    real = bots.play

    def memo(game_cls, bot, seed, layout=None, won=None, seconds=bots.MAX_PLAY_SECONDS, keep_frames=False,
             font=None):
        plain = won in (None, bots.for_game(game_cls)[1]) and seconds == bots.MAX_PLAY_SECONDS and not keep_frames
        key = play_key(game_cls, type(bot).__name__, seed, layout)
        if plain and key in PLAYS:
            return PLAYS[key]
        result = real(game_cls, bot, seed, layout, won=won, seconds=seconds, keep_frames=keep_frames, font=font)
        if plain:
            PLAYS[key] = result
        return result

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(bots, "play", memo)
        yield


@pytest.fixture(scope="module")
def pong_report(shared_plays) -> dict:
    return feel.report(Pong, LAYOUT, seeds=SEEDS)


@pytest.mark.feel
def test_feel_pong_meets_its_budgets(pong_report):
    failures = pong_report["failures"]
    assert failures == [], f"Pong at {LAYOUT}, seeds {SEEDS}: " + "; ".join(failures)


def test_bots_rank_on_pong(pong_report):
    m = pong_report["metrics"]
    ranking = f"good {m['win_good']}, lazy {m['win_lazy']}, none {m['win_none']} (seeds {SEEDS})"
    assert m["win_good"] > m["win_lazy"] > m["win_none"], ranking
    assert m["phases_reached"] == 1.0, f"phases_reached {m['phases_reached']} over the good plays, seeds {SEEDS}"


@pytest.fixture(scope="module")
def game_report(shared_plays):
    """The game's 20-seed report at its layout, with its seeds, measured once per module in REPORTS."""
    def report(game_cls) -> tuple[dict, str, list[int]]:
        layout = bots._layout(game_cls, None)
        seeds = bots.seeds(game_cls, layout, 20)
        if game_cls.info.name not in REPORTS:
            REPORTS[game_cls.info.name] = feel.report(game_cls, layout, seeds=seeds)
        return REPORTS[game_cls.info.name], layout, seeds
    return report


# Defined only when there is a game to judge: an empty parameter set would collect one skipped test each.
if OTHER_GAMES:
    @pytest.mark.feel
    @pytest.mark.parametrize("game_cls", OTHER_GAMES, ids=lambda game: game.info.name)
    def test_feel_meets_its_budgets(game_cls, game_report):
        report, layout, seeds = game_report(game_cls)
        failures = report["failures"]
        assert failures == [], f"{game_cls.info.name} at {layout}, seeds {seeds}: " + "; ".join(failures)

    @pytest.mark.parametrize("game_cls", OTHER_GAMES, ids=lambda game: game.info.name)
    def test_bots_rank(game_cls, game_report):
        report, layout, seeds = game_report(game_cls)
        m = report["metrics"]
        ranking = (f"{game_cls.info.name} at {layout}: good {m['win_good']}, lazy {m['win_lazy']}, "
                   f"none {m['win_none']} (seeds {seeds})")
        assert m["win_good"] > m["win_lazy"] > m["win_none"], ranking
        assert m["phases_reached"] == 1.0, f"phases_reached {m['phases_reached']} over the good plays, seeds {seeds}"


def test_evidence_package_for_pong(tmp_path):
    from tools import arcade_evidence

    arcade_evidence.package([Pong], tmp_path, "test", SEEDS[:2])
    names = {p.name for p in tmp_path.iterdir()}
    for suffix in ("plain.png", "led.png", "distance.png", "canonical.gif", "trace.jsonl", "timeline.txt"):
        assert f"pong-{LAYOUT}-{suffix}" in names, sorted(names)
    assert "games.md" in names and "README.md" not in names
    metrics = json.loads((tmp_path / "feel.json").read_text())["pong"][LAYOUT]["metrics"]
    assert {"response_ticks", "fidelity", "win_good", "win_lazy", "win_none", "round_seconds"} <= set(metrics)
