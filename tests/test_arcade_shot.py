import subprocess
import sys

import numpy as np
import pytest
from PIL import Image

from arcade.flash import FlashGovernor
from arcade.look import render
from arcade.sources.actors import Person, scene
from tests.arcade.helpers import SpyGame, StubLobby, spy_info
from tools import arcade_shot as shot

WHITE = (255, 255, 255)


def stand(n):
    return scene(persons=[Person(0.5, id=1)], ticks=n)


def stand_seven():
    return stand(7)


def stand_ninety():
    return stand(90)


class Blink(SpyGame):
    """A short stub game with a scenario of its own: 7 ticks, a lone person."""

    info = spy_info("blink")
    SCENARIOS = {"short": stand_seven}

    def draw(self, canvas):
        super().draw(canvas)
        canvas.pixel(2, 2, WHITE)


class Strobe(SpyGame):
    """The whole wall white and black on alternate ticks: the governor holds it."""

    info = spy_info("strobe")

    def draw(self, canvas):
        super().draw(canvas)
        canvas.clear(WHITE if self.draws % 2 else (0, 0, 0))


class StepLobby(StubLobby):
    """Requests the first game it is given on tick 3."""

    def __init__(self, games, cfg):
        super().__init__()
        self.games = games

    def update(self, sensed, dt):
        super().update(sensed, dt)
        if self.updates == 4:
            self.request = self.games[0].info.name


def cfg128():
    from arcade.config import ArcadeConfig
    return ArcadeConfig(width=128, height=32, backend="fake", camera="none", audio="none")


def test_png_has_the_git_sha_text_chunk(tmp_path):
    path = tmp_path / "a.png"
    shot.save_png(Image.new("RGB", (4, 4)), path, "abc1234+dirty")
    assert Image.open(path).text["git"] == "abc1234+dirty"


def test_git_sha_is_short_hex_with_optional_dirty():
    sha = shot.git_sha().removesuffix("+dirty")
    assert 4 <= len(sha) <= 12 and all(c in "0123456789abcdef" for c in sha)


def test_cells_match_render(font):
    cfg = cfg128()
    frames, raw, trace, runner = shot.shoot([Blink], stand(4), cfg, font)
    scale = 2
    sheet = np.asarray(shot.contact_sheet(frames, trace, "plain", scale, every=1, cols=2, title="t"))
    cw, ch = 128 * scale, 32 * scale
    k = 3
    row, col = divmod(k, 2)
    x, y = shot.PAD + col * (cw + shot.PAD), shot.TITLE_H + row * (ch + shot.CAP_H + shot.PAD) + shot.CAP_H
    assert (sheet[y:y + ch, x:x + cw] == render(frames[k], "plain", scale, cfg.gamma)).all()


def test_scenario_from_the_game_and_ticks_honoured():
    assert len(list(shot.resolve_scenario("short", [Blink], None))) == 7
    assert len(list(shot.resolve_scenario("short", [Blink], 3))) == 3
    assert len(list(shot.resolve_scenario("tests.test_arcade_shot:stand_seven", [Blink], None))) == 7
    default = list(shot.resolve_scenario(None, [Blink], None))
    assert len(default) == 300 and default[0].bodies[0].id == 1
    assert len(list(shot.resolve_scenario(None, [Blink], 10))) == 10


def test_lobby_and_game_by_module_path(font):
    assert shot.resolve_game("tests.test_arcade_shot:Blink") is Blink
    assert shot.resolve_lobby("none") is None
    make = shot.resolve_lobby("tests.test_arcade_shot:StepLobby")
    frames, raw, trace, runner = shot.shoot([Blink], stand(8), cfg128(), font, lobby=make)
    assert [s["game"] for s in trace[:3]] == ["lobby"] * 3
    assert trace[-1]["game"] == "blink"
    assert len(frames) == len(raw) == len(trace) == 8


def test_distance_sheet_written_at_scale_4_or_more(tmp_path):
    out = tmp_path / "s"
    code = shot.main(["tests.test_arcade_shot:Blink", "--out", str(out), "--scenario", "short", "--every", "2",
                      "--scale", "1"])
    assert code == 0
    plain, dist = Image.open(f"{out}.png"), Image.open(f"{out}-distance.png")
    assert dist.width >= 128 * 4 and plain.width < dist.width
    assert plain.text["git"] and dist.text["git"]


def test_import_does_not_load_games_or_the_lobby():
    code = ("import sys, tools.arcade_shot; "
            "bad = [m for m in ('arcade.games.pong', 'arcade.attract', 'arcade.attract.lobby') if m in sys.modules]; "
            "print(bad); sys.exit(1 if bad else 0)")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def strobe_args(tmp_path):
    return ["tests.test_arcade_shot:Strobe", "--out", str(tmp_path / "st"), "--scenario",
            "tests.test_arcade_shot:stand_ninety", "--raw-vs-pushed"]


def test_raw_vs_pushed_sheet_and_report(tmp_path, capsys):
    assert shot.main(strobe_args(tmp_path)) == 0
    out = capsys.readouterr().out
    assert (tmp_path / "st-raw-vs-pushed.png").exists()
    for word in ("raw", "pushed", "held", "flash_area", "concurrent_area", "square_flashes", "BUDGET"):
        assert word in out
    assert "#" in out and "." in out


def test_raw_vs_pushed_exits_1_when_pushed_flashes(tmp_path, monkeypatch):
    monkeypatch.setattr(FlashGovernor, "apply", lambda self, frame: frame)
    assert shot.main(strobe_args(tmp_path)) == 1
