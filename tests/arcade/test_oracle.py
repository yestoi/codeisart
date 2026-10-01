"""The oracle end to end on every game (I1, it15's I0): feel's report against the budgets, the bots' ranking, and
Pong's evidence package.

One 20-seed report (spec 9.3's count) is measured per game per module and shared. The reports' plain bot plays come
from worker processes first (tests/arcade/pooled.py): before the first report, the pool stores every one PLAYS does
not hold yet, so each report finds them there and runs only its canonical part in this process. A failing budget is
fixed in the game's own files or sent to the owner, never loosened here."""
import dataclasses
import json
import shutil

import pytest

from arcade import bots, feel
from arcade.games import all_games
from arcade.games.pong import Pong
from tests.arcade import pooled
from tests.arcade.helpers import PLAYS, play_key

LAYOUT = "128x64"
SEEDS = bots.seeds(Pong, LAYOUT, 20)
OTHER_GAMES = [game for game in all_games() if game is not Pong]   # Pong keeps its own three tests below

# Every report's (game, layout, seeds): the pool fills these plays and the reports read them, from this one table.
REPORT_PLAYS: list[tuple[type, str, list[int]]] = [(Pong, LAYOUT, SEEDS)] + [
    (game, layout, bots.seeds(game, layout, 20)) for game in OTHER_GAMES for layout in [bots._layout(game, None)]]

REPORTS: dict[str, dict] = {}   # one 20-seed report per game (by name), shared by its two tests


def report_keys() -> set[pooled.Key]:
    """The memo's key of every job of REPORT_PLAYS."""
    games = {game.info.name: game for game, _, _ in REPORT_PLAYS}
    return {play_key(games[name], type(pooled.bot_for(games[name], role)).__name__, seed, layout)
            for name, role, seed, layout in pooled.jobs(REPORT_PLAYS)}


@pytest.fixture(scope="module", autouse=True)
def shared_plays():
    """bots.play, memoised in PLAYS for plays with the default won, seconds and no frames, for this module. Yields
    the unpatched bots.play."""
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
        yield real


@pytest.fixture(scope="module")
def pooled_plays(shared_plays) -> tuple[set[pooled.Key], set[pooled.Key]]:
    """(the report keys already in PLAYS, the keys pooled.fill stored): every report play PLAYS does not hold yet,
    made by worker processes once a module, before the first report. The workers are gone when it returns."""
    before = report_keys() & PLAYS.keys()
    return before, pooled.fill(REPORT_PLAYS)


@pytest.fixture(scope="module")
def pong_report(shared_plays, pooled_plays) -> dict:
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
def game_report(shared_plays, pooled_plays):
    """The game's 20-seed report at its layout, with its seeds (both from REPORT_PLAYS), measured once per module
    in REPORTS."""
    table = {game.info.name: (layout, seeds) for game, layout, seeds in REPORT_PLAYS}

    def report(game_cls) -> tuple[dict, str, list[int]]:
        layout, seeds = table[game_cls.info.name]
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


def test_jobs_name_every_report_play():
    jobs = pooled.jobs([(Pong, LAYOUT, SEEDS)])
    assert len(jobs) == 60
    assert jobs == [("pong", role, seed, "128x64") for role in ("good", "lazy", "none") for seed in SEEDS]
    odd = [job for job in jobs if not all(type(field) in (str, int) for field in job)]
    assert odd == [], f"a job field that is neither a str nor an int: {odd[:3]}"
    assert [tuple(job) for job in json.loads(json.dumps(jobs))] == jobs


def test_the_pool_made_every_missing_play(pooled_plays):
    from tools.show_soak import children_of_this_process

    before, stored = pooled_plays
    keys = report_keys()
    assert keys <= PLAYS.keys(), f"report plays missing from PLAYS: {sorted(keys - PLAYS.keys())[:5]}"
    missing = keys - before
    assert stored == missing, (f"the pool stored {len(stored)} of the {len(missing)} missing report plays (the "
                               f"fill's warnings say why): not stored {sorted(missing - stored)[:5]}, "
                               f"not asked for {sorted(stored - missing)[:5]}")
    pong = {key for key in keys if key[0] == "pong"}
    assert len(pong) == 60 and pong <= stored, f"Pong's keys not pooled: {sorted(pong - stored)[:5]}"
    assert children_of_this_process() == 0


@pytest.mark.parametrize("game_cls, layout, seeds", REPORT_PLAYS, ids=[game.info.name for game, _, _ in REPORT_PLAYS])
def test_pooled_plays_are_the_in_process_plays(game_cls, layout, seeds, shared_plays, pooled_plays):
    real = shared_plays                    # the unpatched bots.play: the memo would hand back PLAYS[key] itself
    seed = seeds[19]                       # the report's last seed: no game's own tests play it first
    bot = pooled.bot_for(game_cls, "good")
    key = play_key(game_cls, type(bot).__name__, seed, layout)
    assert key in pooled_plays[1], f"{key} was not made by the pool"
    pooled_play, made = PLAYS[key], real(game_cls, bot, seed, layout)
    differ = [f"{field.name}: pooled {getattr(pooled_play, field.name)!r}, in process {getattr(made, field.name)!r}"
              for field in dataclasses.fields(bots.Play)
              if getattr(pooled_play, field.name) != getattr(made, field.name)]
    assert differ == [], f"{game_cls.info.name} at {layout}, good bot, seed {seed}: " + "; ".join(differ)


def _cannot_start(*args, **kwargs):
    raise OSError("no worker can start in this test")


@pytest.mark.parametrize("failure", ["cannot-start", "exit-1"])
def test_fill_warns_and_stores_nothing_when_its_workers_fail(failure):
    from tools.show_soak import children_of_this_process

    store: dict = {}
    with pytest.warns(RuntimeWarning):
        with pytest.MonkeyPatch.context() as mp:   # scoped to the fill: children_of_this_process runs pgrep
            if failure == "cannot-start":
                mp.setattr(pooled.subprocess, "Popen", _cannot_start)
            else:
                mp.setattr(pooled, "PYTHON", shutil.which("false"))   # exits 1 and writes no file
            stored = pooled.fill([(Pong, LAYOUT, SEEDS[:1])], plays=store, workers=2)
    assert stored == set()
    assert store == {}
    assert children_of_this_process() == 0
