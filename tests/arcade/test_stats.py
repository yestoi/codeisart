"""stats: a read-only summary of data_dir/sessions.jsonl (it21 S)."""
from datetime import datetime
from types import SimpleNamespace

from arcade import scores, stats
from arcade.scores import SessionLog

T0 = datetime(2026, 10, 2, 12, 0, 0)


def _log(path, rows):
    log = SessionLog(path)
    for game, duration, reason in rows:
        log.append(game, "solo", T0, duration, 1, None, reason)


def test_stats_summarises_sessions(tmp_path):
    assert set(("left", "done")) <= set(scores.REASONS)
    p = tmp_path / "sessions.jsonl"
    _log(p, [("jump", 10.0, "left"), ("jump", 20.0, "done"), ("jump", 40.0, "done"), ("pong", 5.0, "done")])
    result, bad = stats.summarise(p)
    assert bad == 0
    assert result["jump"] == stats.GameStats(3, 20.0, {"done": 2, "left": 1})
    assert result["pong"].sessions == 1
    lines = stats.table(result).splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("pong") and lines[1].startswith("jump")   # MENU_ORDER: pong before jump


def test_stats_skips_a_bad_line(tmp_path):
    p = tmp_path / "sessions.jsonl"
    _log(p, [("jump", 10.0, "done")])
    with open(p, "a") as f:
        f.write('not json\n[1]\n{"game": 3}\n\n')
    result, bad = stats.summarise(p)
    assert bad == 3
    assert result["jump"].sessions == 1


def test_stats_without_a_file_says_so(tmp_path, capsys):
    cfg = tmp_path / "arcade.toml"
    cfg.write_text(f'data_dir = "{tmp_path / "empty"}"\n')
    assert stats.main(SimpleNamespace(config=str(cfg), sessions=None)) == 0
    assert "no sessions" in capsys.readouterr().out
    assert stats.main(SimpleNamespace(config=None, sessions=str(tmp_path / "nope.jsonl"))) == 0
    assert "no sessions" in capsys.readouterr().out


def test_a_null_duration_is_not_in_the_median(tmp_path):
    p = tmp_path / "sessions.jsonl"
    _log(p, [("jump", 10.0, "done"), ("jump", float("nan"), "crash"), ("jump", 30.0, "done")])
    assert '"duration": null' in p.read_text()
    result, _ = stats.summarise(p)
    assert result["jump"].sessions == 3
    assert result["jump"].median_seconds == 20.0
    only_null = tmp_path / "n.jsonl"
    _log(only_null, [("pong", float("nan"), "crash")])
    assert stats.summarise(only_null)[0]["pong"].median_seconds is None
