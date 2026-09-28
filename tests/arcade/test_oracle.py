"""The oracle end to end on Pong (I1): feel's report against the budgets, the bots' ranking, the evidence package.

One 20-seed report (spec 9.3's count) is measured per module and shared. A failing budget is fixed in Pong's own
files or sent to the owner, never loosened here."""
import json

import pytest

from arcade import bots, feel
from arcade.games.pong import Pong

LAYOUT = "128x32"
SEEDS = bots.seeds(Pong, LAYOUT, 20)


@pytest.fixture(scope="module")
def pong_report() -> dict:
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
