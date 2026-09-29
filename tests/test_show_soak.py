"""The soak (it13 T-soak): a real ShowLoop on fakes under a fake clock, watched by a flash meter.

The soak never pushes to a display: the loop makes and governs it. No test here starts a real player, opens a
device or waits for a clock; the one CLI test runs 0.3 s of real time.
"""
import json
import random
import subprocess
from pathlib import Path

import pytest

import tools.show_soak as show_soak
from arcade.flash import BUDGET, flash_area, square_flashes
from show.main import ShowLoop
from tests.test_main import StrobePlayer, small_cfg
from tests.test_wall import Recorder
from tools.show_soak import failures, main, soak

FPS = 20


class FakePlayer:
    """Plays for a second, printing a line each tick; `done` after that."""

    def __init__(self, entry, term, cfg):
        self.term, self.done, self.crowd, self.began = term, False, False, 0.0

    def start(self, now, crowd=False):
        self.began = now
        self.term.reset(23)

    def stop(self):
        self.done = True

    def tick(self, now):
        self.term.feed(b"line\r\n")
        self.done = now - self.began >= 1.0
        return []


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds


def run_soak(cfg, seconds=3.0, press_every=0.5, **kw):
    clock = FakeClock()
    kw.setdefault("player_factory", FakePlayer)
    kw.setdefault("display", Recorder())
    return soak(cfg, seconds / 60.0, press_every, clock=clock, sleep=clock.sleep, **kw), kw["display"]


def test_a_short_soak_counts_steps_presses_and_plays(tmp_path):
    report, display = run_soak(small_cfg(tmp_path), stations=(1,))
    assert report["steps"] == 60 and report["governed"] >= 60 and report["presses"] == 6
    assert report["plays_started"] >= 1 and report["plays_ended"] >= 1 and report["returns_to_attract"] >= 1
    assert report["plays_started"] - report["plays_ended"] <= 1
    assert report["run_ended_early"] == 0 and report["push_failures"] == 0 and report["errors_logged"] == 0
    assert report["step_ms"]["worst"] >= report["step_ms"]["p95"] >= report["step_ms"]["median"] >= 0
    assert report["windows"] and report["meter"]["frames"] == 60 and failures(report) == []
    assert display.closed


def test_a_strobing_entry_soaks_inside_the_budget(tmp_path):
    report, display = run_soak(small_cfg(tmp_path), seconds=4.0, stations=(1,), player_factory=StrobePlayer)
    frames = display.pushed
    assert len(frames) >= 80 and flash_area(frames, fps=FPS) == 0.0 and square_flashes(frames, fps=FPS) <= BUDGET
    assert report["governor"]["held_ticks"] > 0 and report["meter"]["squares_max"] <= BUDGET
    assert failures(report) == []


def test_the_wrappers_change_no_frame(tmp_path):
    cfg = small_cfg(tmp_path)
    report, display = run_soak(cfg, stations=(1, 2, 3), seed=7, player_factory=StrobePlayer)
    rng = random.Random(7)                                        # the same seed, the same clock, no wrappers
    plain = Recorder()
    loop = ShowLoop(cfg, display=plain, player_factory=StrobePlayer, notify=lambda s: None, rng=random.Random(7))
    loop._devices = True
    from show.audio import FakeAudio
    from show.lights import FakeLights
    loop.lights, loop.audio = FakeLights(), FakeAudio()
    loop.start(0.0)
    for k in range(report["steps"]):
        now = k / FPS
        if k % 10 == 0:
            loop.presses.put(rng.choice((1, 2, 3)))
        loop.step(now)
    n = report["steps"]
    assert len(display.pushed) >= n and len(plain.pushed) == n
    assert all((a == b).all() for a, b in zip(display.pushed[:n], plain.pushed))


class Failing(Recorder):
    def push(self, frame):
        raise OSError("no carrier")


def test_a_failing_display_fails_the_soak(tmp_path):
    report, _ = run_soak(small_cfg(tmp_path), seconds=1.0, display=Failing())
    assert report["push_failures"] > 0
    assert any("push_failures" in f for f in failures(report))


class Raising(FakePlayer):
    def tick(self, now):
        raise RuntimeError("the player broke")


def test_a_logged_error_fails_the_soak(tmp_path):
    report, _ = run_soak(small_cfg(tmp_path), seconds=1.0, stations=(1,), player_factory=Raising)
    assert report["errors_logged"] > 0 and 0 < len(report["errors"]) <= 20
    assert any("errors_logged" in f for f in failures(report))


def test_children_left_are_counted(tmp_path):
    child = subprocess.Popen(["sleep", "30"])
    try:
        report, _ = run_soak(small_cfg(tmp_path), seconds=0.5)
        assert report["children_left"] >= 1
        assert any("children_left" in f for f in failures(report))
    finally:
        child.kill()
        child.wait()


def test_a_meter_window_over_the_budget_fails_the_soak(tmp_path):
    report, _ = run_soak(small_cfg(tmp_path), seconds=0.5)
    assert failures(report) == []
    report["windows"][0]["squares_max"] = BUDGET + 1
    assert any("squares_max" in f for f in failures(report))
    assert any("run_ended_early" in f for f in failures({**report, "run_ended_early": 1}))


def test_main_writes_the_report(tmp_path, monkeypatch):
    monkeypatch.setattr(show_soak, "EntryPlayer", FakePlayer)
    cfg = small_cfg(tmp_path)
    toml = tmp_path / "show.toml"
    toml.write_text(f'backend = "fake"\nwidth = 128\nheight = 64\nview = "ink"\nfps = {FPS}\n'
                    f'entries_dir = "{cfg.entries_dir}"\nfont_path = "{cfg.font_path}"\naudio_dir = "{tmp_path}"\n')
    out = tmp_path / "out"
    assert main(["--config", str(toml), "--minutes", "0.005", "--out", str(out), "--window-s", "0.1"]) == 0
    (path,) = out.glob("soak-*.json")
    report = json.loads(path.read_text())
    assert report["steps"] > 0 and report["presses"] >= 1 and report["run_ended_early"] == 0
    assert report["sha"] and report["config"]["fps"] == FPS and len(report["windows"]) >= 2


def test_the_soak_never_names_the_display_path():
    source = Path(show_soak.__file__).read_text()
    assert "make_" + "display" not in source and ".push" + "(" not in source


@pytest.mark.parametrize("minutes", ["0", "-1"])
def test_minutes_must_be_over_0(tmp_path, minutes):
    assert main(["--minutes", minutes, "--out", str(tmp_path / "out")]) == 2
    assert not (tmp_path / "out").exists()
