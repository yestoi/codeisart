import itertools
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from arcade.games import all_games
from arcade.sources.actors import Person, scene
from tests.arcade.helpers import SpyGame, spy_info
from tools import arcade_evidence as ev

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def canonical():
    """2 s of an empty wall, then a person who stands and raises a hand: the lobby launches the game."""
    return itertools.chain(scene(ticks=60),
                           scene(persons=[Person(0.5, id=1).raise_hand(3.0, 1.0)], ticks=840))


class Stub(SpyGame):
    info = spy_info("paint", layouts=frozenset({"128x32", "64x64"}))
    SCENARIOS = {"canonical": canonical}

    def draw(self, canvas):
        super().draw(canvas)
        canvas.pixel(3 + self.draws % 20, 5, (255, 120, 0))

    def debug_state(self):
        return {**super().debug_state(), "phase": "serve" if self.draws < 40 else "play"}


def stub_report(game_cls, layout, seeds=None, font=None):
    return {"metrics": {"rally": 4.5, "empty": None},
            "budgets": {"rally": {"min": 2.0, "max": 9.0, "reason": "a rally"}},
            "failures": []}


@pytest.fixture(scope="module")
def packaged(tmp_path_factory):
    out = tmp_path_factory.mktemp("pkg")
    files = ev.package([Stub], out, "abc1234", range(2), report=stub_report)
    return out, files


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


def make_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    (repo / "README").write_text("x")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    return repo


def commit(repo, *paths, msg="c"):
    for p in paths:
        f = repo / p
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f.read_text() + "x" if f.exists() else "x")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", msg)


def test_file_set_per_game_and_layout(packaged):
    out, files = packaged
    names = {p.name for p in out.iterdir()}
    for layout in ("128x32", "64x64"):
        for suffix in ("plain.png", "led.png", "distance.png", "canonical.gif", "trace.jsonl", "timeline.txt"):
            assert f"paint-{layout}-{suffix}" in names, sorted(names)
    assert {"feel.json", "games.md"} <= names and "README.md" not in names
    assert all(p.exists() for p in files) and {p.name for p in files} <= names


def test_gif_under_6s_and_300kb_with_the_sha(packaged):
    out, _ = packaged
    path = out / "paint-128x32-canonical.gif"
    with Image.open(path) as im:
        assert im.info["comment"] == b"abc1234"
        total = 0
        for i in range(im.n_frames):
            im.seek(i)
            total += im.info["duration"]
    assert total <= 6000 and path.stat().st_size <= 300_000, (total, path.stat().st_size)
    with Image.open(out / "paint-128x32-plain.png") as png:
        assert png.text["git"] == "abc1234"


def test_gif_raises_when_over_the_cap_at_any_scale(tmp_path):
    rng = np.random.default_rng(1)
    noise = [rng.integers(0, 256, (32, 128, 3), dtype=np.uint8) for _ in range(180)]
    with pytest.raises(ValueError, match="300"):
        ev.gif(noise, tmp_path / "n.gif", "s")
    flat = [np.full((32, 128, 3), (i % 2) * 255, dtype=np.uint8) for i in range(180)]
    assert ev.gif(flat, tmp_path / "f.gif", "s") == (tmp_path / "f.gif").stat().st_size


def test_dirty_tree_refused_unless_allowed(tmp_path, monkeypatch, capsys):
    repo = make_repo(tmp_path)
    monkeypatch.chdir(repo)
    clean = ev.clean_sha(repo / "out", False)
    assert clean == git(repo, "rev-parse", "--short", "HEAD").strip()
    (repo / "dirty.py").write_text("x")
    with pytest.raises(SystemExit) as e:
        ev.clean_sha(repo / "out", False)
    assert e.value.code == 2 and "dirty.py" in capsys.readouterr().err
    assert ev.clean_sha(repo / "out", True) == clean + "+dirty"


def test_sha_taken_once_and_own_outputs_never_dirty_it(tmp_path, monkeypatch):
    repo = make_repo(tmp_path)
    monkeypatch.chdir(repo)
    out = repo / "evidence" / "it99"
    sha = ev.clean_sha(out, False)
    out.mkdir(parents=True)
    (out / "games.md").write_text("mine")
    (out / "sub").mkdir()
    (out / "sub" / "a.png").write_text("mine")
    assert ev.clean_sha(out, False) == sha            # its own files never mark it
    calls = []
    real = ev.clean_sha
    monkeypatch.setattr(ev, "clean_sha", lambda *a: calls.append(a) or real(*a))
    monkeypatch.setattr(ev, "package", lambda games, out, sha, seeds, **k: calls.append(sha) or [])
    monkeypatch.setattr(ev, "changed_games", lambda since: ["pong"])
    monkeypatch.setattr("arcade.games.get_game", lambda name: Stub)
    assert ev.main(["--iteration", "99", "--out", str(out)]) == 0
    assert len(calls) == 2 and calls[1] == sha        # clean_sha once, and package got its sha


def test_changed_games_from_git_diff(tmp_path, monkeypatch):
    repo = make_repo(tmp_path)
    monkeypatch.chdir(repo)
    commit(repo, "docs/superpowers/workflow/evidence/it01/games.md")
    commit(repo, "arcade/games/pong.py", "tests/arcade/test_paint.py", "arcade/games/dodge_bots.py",
           "arcade/games/tug_feel.toml", "docs/notes.md")
    assert sorted(ev.changed_games(None)) == ["dodge", "paint", "pong", "tug"]
    assert ev.changed_games("HEAD") == []
    assert sorted(ev.changed_games("HEAD~1")) == ["dodge", "paint", "pong", "tug"]
    commit(repo, "docs/superpowers/workflow/evidence/it02/games.md")
    assert ev.changed_games(None) == []               # since the last commit touching evidence/


def test_engine_change_marks_every_game(tmp_path, monkeypatch):
    repo = make_repo(tmp_path)
    monkeypatch.chdir(repo)
    for engine in ("arcade/game.py", "arcade/runner.py", "arcade/headless.py"):
        commit(repo, engine)
        assert ev.changed_games("HEAD~1") == [g.info.name for g in all_games()], engine


def test_timeline_at_most_ten_lines(packaged):
    out, _ = packaged
    lines = (out / "paint-128x32-timeline.txt").read_text().splitlines()
    assert 1 <= len(lines) <= 10 and all(len(line.split(None, 1)) == 2 for line in lines), lines
    many = [{"t": i, "game": "g", "phase": str(i)} for i in range(200)]
    assert len(ev.timeline_lines(many).splitlines()) == 10
    rows = [json.loads(line) for line in (out / "paint-128x32-trace.jsonl").read_text().splitlines()]
    assert rows and rows[0]["game"] == "lobby" and any(r["game"] == "paint" for r in rows)


def test_feel_json_and_games_md_from_report(packaged):
    out, _ = packaged
    feel = json.loads((out / "feel.json").read_text())
    assert feel["paint"]["64x64"]["metrics"]["rally"] == 4.5 and feel["paint"]["128x32"]["metrics"]["empty"] is None
    md = (out / "games.md").read_text()
    assert "abc1234" in md and "| rally | 4.5 | 2.0 to 9.0 | yes |" in md
    for name in ("paint-128x32-plain.png", "paint-64x64-led.png", "paint-128x32-canonical.gif"):
        assert f"![{name}]({name})" in md


def test_runs_as_a_script_and_as_a_module():
    for cmd in ([PY, "-m", "tools.arcade_evidence", "--help"],
                [PY, str(ROOT / "tools" / "arcade_evidence.py"), "--help"]):
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        assert r.returncode == 0 and "--iteration" in r.stdout, r.stderr
