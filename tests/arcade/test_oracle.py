"""The oracle end to end on Pong (I1): feel's report against the budgets, the bots' ranking, the evidence package.

One 20-seed report (spec 9.3's count) is measured per module and shared. A failing budget is fixed in Pong's own
files or sent to the owner, never loosened here."""
import json

import pytest

from arcade import bots, feel
from arcade.games.pong import Pong

LAYOUT = "128x64"
SEEDS = bots.seeds(Pong, LAYOUT, 20)

# Every plain bot play this module measures, by (game name, bot class name, seed, layout): a play is a pure function
# of those (bots.play is seeded, a bot factory takes no arguments, both callers use the project font), so the
# evidence package's report and test_pong's bot tests read the plays the 20-seed report already made.
PLAYS: dict[tuple[str, str, int, str], bots.Play] = {}


def play_key(game_cls, bot_name: str, seed: int, layout: str | None = None) -> tuple[str, str, int, str]:
    return (game_cls.info.name, bot_name, seed, bots._layout(game_cls, layout))


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


def test_evidence_package_for_pong(tmp_path):
    from tools import arcade_evidence

    arcade_evidence.package([Pong], tmp_path, "test", SEEDS[:2])
    names = {p.name for p in tmp_path.iterdir()}
    for suffix in ("plain.png", "led.png", "distance.png", "canonical.gif", "trace.jsonl", "timeline.txt"):
        assert f"pong-{LAYOUT}-{suffix}" in names, sorted(names)
    assert "games.md" in names and "README.md" not in names
    metrics = json.loads((tmp_path / "feel.json").read_text())["pong"][LAYOUT]["metrics"]
    assert {"response_ticks", "fidelity", "win_good", "win_lazy", "win_none", "round_seconds"} <= set(metrics)
