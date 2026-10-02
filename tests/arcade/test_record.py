"""record (spec 6.3, 6.5, 9.5): consent and the colorlight rules, 3 2 1 then REC on the wall, the cues in the
header, motion dropped unless asked for, a raw file of rec's captures only, and the writer closed on every path.

Actors play through ScriptedCamera and NoSource on a FakeClock (GuardClock: a record that never stops fails instead
of hanging), the frames through headless.RecordingDisplay. TEST_SCRIPT is 2 s: 90 countdown ticks, 60 recorded, then
the tick that ends it."""
from __future__ import annotations

import argparse
import random
import re
from pathlib import Path

import pytest

import arcade.main
import arcade.sources.record as record_mod
from arcade import feel
from arcade.canvas import Canvas
from arcade.flash import SMALL_AREA, concurrent_area
from arcade.headless import RecordingDisplay, run_headless
from arcade.sensed import Sensed
from arcade.sources import NoSource, ScriptedCamera
from arcade.sources.actors import TICK, Person, motion_rect, moving_blob, scene
from arcade.sources.record import (COUNTDOWN, REC_COLOR, RECORD_SCRIPTS, TEXT_COLOR, RecordScene, RecordScript,
                                   git_sha, main, record, refusal)
from arcade.sources.scenario import RawRecord, ScenarioReader, ScenarioWriter
from tests.arcade.helpers import FakeClock, make_cfg

ROOT = Path(__file__).resolve().parents[2]
WALL = (128, 64)
FPS = 30
TEST_SCRIPT = RecordScript("test-2s", 2.0, ((0.0, "RAISE RIGHT HAND"), (1.0, "HOLD")))
COUNT_TICKS = COUNTDOWN * FPS                       # 90
REC_TICKS = round(TEST_SCRIPT.seconds * FPS)        # 60


class GuardClock(FakeClock):
    """A FakeClock whose sleep fails past LIMIT ticks: a record whose loop never stops fails, never hangs."""

    LIMIT = 1000

    def __init__(self):
        super().__init__(100.0)
        self.start = self.now
        self.sleeps = 0

    def sleep(self, s: float) -> None:
        self.sleeps += 1
        if self.sleeps > self.LIMIT:
            raise AssertionError(f"record ran past {self.LIMIT} ticks")
        super().sleep(s)


class ListWriter:
    """A writer that keeps what it is given."""

    def __init__(self):
        self.records: list = []

    def write(self, record) -> None:
        self.records.append(record)


class ClosingCamera(ScriptedCamera):
    def __init__(self, frames, clock, events: list | None = None):
        super().__init__(frames, clock)
        self.closed = False
        self.events = events if events is not None else []

    def close(self) -> None:
        self.closed = True
        self.events.append(("camera closed", getattr(self, "tap", "no tap")))


class TapCamera(ClosingCamera):
    """A stand-in for MediaPipeCamera's raw tap (W): it captures on every latest() from the start and hands the
    capture to tap while one is set; close() makes one last capture, as a thread stopped mid-capture would."""

    def __init__(self, frames, clock, events: list):
        super().__init__(frames, clock, events)
        self.tap = None
        self.captures: list[tuple[float, bool]] = []      # (capture time, handed to the tap)

    def _capture(self) -> None:
        t, tap = self.clock(), self.tap
        if tap is not None:
            tap(RawRecord(t))
        self.captures.append((t, tap is not None))

    def latest(self):
        self._capture()
        return super().latest()

    def close(self) -> None:
        self._capture()
        super().close()


def logged_writer(events: list) -> type:
    class LoggedWriter(ScenarioWriter):
        def close(self) -> None:
            events.append("writer closed")
            super().close()
    return LoggedWriter


def person_frames(ticks: int = 400):
    """A person in view on every tick, walking across with the right hand up a while, a light and lit motion."""
    person = Person(0.3, id=1).walk(0.7, 4.0, at=0.5).raise_hand(3.5, 1.0)
    return scene(persons=[person], blobs=[moving_blob(0.3, 0.4, 0.6, 0.4, 10.0)],
                 motion=[motion_rect(0.2, 0.2, 0.6, 0.8, 0.0, 100.0)], ticks=ticks)


def run_record(out: Path, font, camera_cls=ClosingCamera, cfg=None, **kw) -> tuple[int, RecordingDisplay, object]:
    clock = GuardClock()
    camera = camera_cls(person_frames(), clock)
    display = RecordingDisplay()
    n = record(cfg or make_cfg(WALL), TEST_SCRIPT, camera, NoSource(), display, font, out, clock=clock,
               sleep=clock.sleep, **kw)
    return n, display, camera


@pytest.fixture(scope="module")
def recorded(tmp_path_factory, font5x7):
    """One default (sensed, no motion) recording of TEST_SCRIPT: (path, records written, pushed frames, camera)."""
    out = tmp_path_factory.mktemp("record") / "sensed.jsonl.gz"
    n, display, camera = run_record(out, font5x7)
    return out, n, display.frames, camera


def args(config: Path, *, consent: bool, raw: bool = False, script: str = "door-point", out=None,
         with_motion: bool = False) -> argparse.Namespace:
    return argparse.Namespace(config=str(config), script=script, i_have_consent=consent, raw=raw,
                              with_motion=with_motion, out=out)


# ----- refusals -----

def test_record_requires_consent():
    cfg = make_cfg(WALL)
    why = refusal(cfg, consent=False, raw=False)
    assert why is not None and "consent" in why
    assert refusal(cfg, consent=True, raw=False) is None
    raw_cfg = make_cfg(WALL, camera="mediapipe")
    assert "consent" in refusal(raw_cfg, consent=False, raw=True)
    assert refusal(raw_cfg, consent=True, raw=True) is None


def test_record_refused_on_colorlight_without_allow_record():
    why = refusal(make_cfg(WALL, backend="colorlight"), consent=True, raw=False)
    assert why is not None and "allow_record" in why
    assert refusal(make_cfg(WALL, backend="colorlight", allow_record=True), consent=True, raw=False) is None


def test_raw_refused_on_colorlight():
    cfg = make_cfg(WALL, backend="colorlight", allow_record=True, camera="mediapipe")
    why = refusal(cfg, consent=True, raw=True)
    assert why is not None and "--raw" in why and "colorlight" in why
    assert refusal(cfg, consent=True, raw=False) is None


def test_raw_refused_without_the_mediapipe_camera():
    for camera in ("none", "replay", "imx500"):
        why = refusal(make_cfg(WALL, camera=camera), consent=True, raw=True)
        assert why is not None and "mediapipe" in why, camera
        assert refusal(make_cfg(WALL, camera=camera), consent=True, raw=False) is None, camera
    assert refusal(make_cfg(WALL, camera="mediapipe"), consent=True, raw=True) is None


def test_a_refusal_opens_nothing(monkeypatch, tmp_path, capsys):
    opened = []
    monkeypatch.setattr(record_mod, "make_sources", lambda *a, **k: opened.append("sources"))
    monkeypatch.setattr(arcade.main, "build_display", lambda cfg: opened.append("display"))
    config = tmp_path / "arcade.toml"
    for text, kw, why in (('camera = "none"\n', {"consent": False}, "consent"),
                          ('backend = "colorlight"\ncamera = "none"\n', {"consent": True}, "allow_record"),
                          ('backend = "colorlight"\nallow_record = true\n', {"consent": True, "raw": True}, "--raw"),
                          ('camera = "none"\n', {"consent": True, "raw": True}, "mediapipe"),
                          ('camera = "none"\n', {"consent": True, "script": "no-such-script"}, "no-such-script")):
        config.write_text(text)
        assert main(args(config, **kw)) == 2, text
        assert why in capsys.readouterr().out, text
    assert opened == []


# ----- main -----

class Source:
    def __init__(self):
        self.closed = False

    def close(self) -> None:
        self.closed = True


@pytest.mark.parametrize("raising", [False, True], ids=["records", "record-raises"])
def test_main_records_then_closes_the_sources_and_the_display(monkeypatch, tmp_path, capsys, raising):
    camera, audio, display, calls = Source(), Source(), RecordingDisplay(), []
    monkeypatch.setattr(record_mod, "make_sources", lambda cfg, size, *a, **k: (camera, audio))
    monkeypatch.setattr(arcade.main, "build_display", lambda cfg: display)

    def fake_record(cfg, script, cam, aud, disp, font, out, **kw):
        calls.append((cfg, script, cam, aud, disp, Path(out), kw))
        if raising:
            raise RuntimeError("record boom")
        return 7
    monkeypatch.setattr(record_mod, "record", fake_record)
    config = tmp_path / "arcade.toml"
    font = ROOT / "fonts" / "5x7.bin"
    config.write_text(f'camera = "none"\ndata_dir = "{tmp_path / "data"}"\nfont_path = "{font}"\n')
    if raising:
        with pytest.raises(RuntimeError, match="record boom"):
            main(args(config, consent=True))
    else:
        assert main(args(config, consent=True, with_motion=True)) == 0
    cfg, script, cam, aud, disp, out, kw = calls[0]
    assert script is RECORD_SCRIPTS["door-point"] and (cam, aud, disp) == (camera, audio, display)
    assert out.parent == tmp_path / "data" / "recordings"
    assert re.fullmatch(r"door-point-\d{8}T\d{6}\.jsonl\.gz", out.name), out.name
    assert kw == {"raw": False, "with_motion": not raising}
    assert camera.closed and audio.closed and display.closed
    if not raising:
        assert str(out) in capsys.readouterr().out
        given = tmp_path / "mine.jsonl.gz"
        assert main(args(config, consent=True, out=str(given))) == 0
        assert calls[-1][5] == given and str(given) in capsys.readouterr().out


# ----- the scripts -----

SPEC_SECONDS = {"empty-room": 30, "walk-in-stand-leave": 20, "door-point": 30, "wrist-sweep": 20,
                "exit-gesture": 15, "jumps-squats": 20, "poses-8": 40, "torch-paint": 30, "idle-still": 20,
                "claps-tempo-voice": 30, "music-speaker": 30, "two-people-cross": 30}


def test_the_twelve_scripts_of_spec_9_5():
    assert {name: s.seconds for name, s in RECORD_SCRIPTS.items()} == SPEC_SECONDS
    for name, s in RECORD_SCRIPTS.items():
        times = [t for t, _ in s.cues]
        assert s.name == name and isinstance(s.cues, tuple)
        assert times[0] == 0.0 and times == sorted(set(times)) and times[-1] < s.seconds, name
        for _, text in s.cues:
            assert 0 < len(text) <= 21 and text == text.upper() and text.isascii(), (name, text)
    texts = [text for _, text in RECORD_SCRIPTS["door-point"].cues]
    assert [t for t in texts if t.startswith("POINT AT")] == ["POINT AT DOOR 1", "POINT AT DOOR 2", "POINT AT DOOR 3"]
    assert texts.count("HOLD") == 3 and "SWEEP, DON'T STOP" in texts
    with pytest.raises(AttributeError):
        RECORD_SCRIPTS["door-point"].seconds = 1.0


def test_every_cue_shows_whole_at_rows_28_to_35(font5x7):
    """Each script's every cue, drawn by the scene after its time: centred, 1x, its top row 28."""
    canvas = Canvas(*WALL, font5x7)
    for s in RECORD_SCRIPTS.values():
        scene_ = RecordScene(s, ListWriter(), with_motion=False)
        scene_.reset(WALL, random.Random(0))
        scene_.update(Sensed(0.0), TICK)
        for at, text in s.cues:
            scene_.update(Sensed(COUNTDOWN + at), TICK)
            assert scene_.debug_state()["cue"] == text
            canvas.clear()
            scene_.draw(canvas)
            found = feel.find_text(canvas.frame, font5x7, text, scales=(1,))
            assert found is not None and found[1] == 28, (s.name, text, found)
            x, _, mask = found
            assert abs(2 * x + mask.shape[1] - WALL[0]) <= 2, (s.name, text, x)       # centred
            assert not canvas.frame[60:].any()


# ----- the scene and the wall -----

def test_countdown_writes_nothing_and_shows_3_2_1(recorded, font5x7):
    writer = ListWriter()
    scene_ = RecordScene(TEST_SCRIPT, writer, with_motion=False)
    scene_.reset(WALL, random.Random(0))
    for k in range(COUNT_TICKS):
        scene_.update(Sensed(k * TICK), TICK)
        assert scene_.debug_state() == {"phase": "countdown", "seconds": 0, "cue": None, "written": 0}, k
    assert writer.records == [] and not scene_.done()
    scene_.update(Sensed(COUNT_TICKS * TICK), TICK)
    assert scene_.debug_state() == {"phase": "rec", "seconds": 0, "cue": "RAISE RIGHT HAND", "written": 1}
    assert [r.t for r in writer.records] == [0.0]

    _, n, frames, _ = recorded
    assert len(frames) == COUNT_TICKS + n + 1                     # the countdown, rec, the tick that ends it
    for i, digit in enumerate("321"):
        for k in range(i * FPS, (i + 1) * FPS):
            found = feel.find_text(frames[k], font5x7, digit, scales=(2,))
            assert found is not None, (digit, k)
            x, y, mask = found
            assert abs(2 * x + mask.shape[1] - WALL[0]) <= 2 and abs(2 * y + mask.shape[0] - WALL[1]) <= 4, found
            assert feel.find_text(frames[k], font5x7, "REC", scales=(1,)) is None, k


def test_rec_glyph_on_every_recorded_tick(recorded, font5x7):
    _, n, frames, _ = recorded
    rec = frames[COUNT_TICKS:COUNT_TICKS + n]
    assert len(rec) == REC_TICKS
    for k, frame in enumerate(rec):
        found = feel.find_text(frame, font5x7, "REC", scales=(1,))
        assert found is not None and found[:2] == (1, 1), (k, found)
        x, y, mask = found
        lit = frame[y:y + mask.shape[0], x:x + mask.shape[1]][mask]
        assert (lit[:, 0] > 0).all() and not lit[:, 1:].any(), k                     # REC_COLOR, pure red
        counter = feel.find_text(frame, font5x7, f"{k // FPS}S", scales=(1,))
        assert counter is not None and counter[1] == 1 and counter[0] > x + mask.shape[1], (k, counter)
        cue = "RAISE RIGHT HAND" if k < FPS else "HOLD"
        found = feel.find_text(frame, font5x7, cue, scales=(1,))
        assert found is not None and found[1] == 28, (k, cue)
    assert feel.find_text(frames[-1], font5x7, "REC", scales=(1,)) is None          # the end tick records nothing
    assert REC_COLOR == (255, 0, 0) and TEXT_COLOR == (255, 255, 255)


def test_rec_frames_keep_the_flash_rule_and_rows_60_to_63_dark(font5x7):
    person = Person(0.25, id=1).walk(0.75, 4.0, at=0.5).raise_hand(3.5, 1.0)
    feed = list(scene(persons=[person, Person(0.6, height=0.5, id=2)], ticks=COUNT_TICKS + REC_TICKS + 1))
    assert all(len(f.bodies) == 2 for f in feed)                  # bodies in view on every tick
    _, runner = run_headless(make_cfg(WALL), font5x7, [], feed, lobby=RecordScene(TEST_SCRIPT, ListWriter(),
                             with_motion=False), trace=True, raw=True)
    assert {s["phase"] for s in runner.trace} == {"countdown", "rec", "end"}
    assert runner.governor.held_ticks == 0
    assert concurrent_area(runner.raw_frames) < SMALL_AREA
    assert not any(f[60:].any() for f in runner.raw_frames)

    scene_ = RecordScene(TEST_SCRIPT, ListWriter(), with_motion=False)
    scene_.reset(WALL, random.Random(0))
    canvas = Canvas(*WALL, font5x7)
    lit, drawn = [], 0
    for f in feed:
        scene_.update(f, TICK)
        canvas.clear()
        scene_.draw(canvas)
        drawn += bool(canvas.frame[:60].any())
        if canvas.frame[60:].any():
            lit.append((round(f.t, 2), scene_.debug_state()["phase"]))
    assert not lit, f"rows 60 to 63 lit on {len(lit)} ticks, from {lit[:3]}"
    assert drawn == len(feed)                                     # the figures are drawn on every tick


# ----- the file -----

def test_record_script_writes_cues(recorded):
    out, n, _, camera = recorded
    reader = ScenarioReader(out)
    records = list(reader)
    assert reader.header["script"] == "test-2s" and reader.cues == TEST_SCRIPT.cues
    assert reader.header["type"] == "sensed" and reader.header["fps"] == FPS
    assert reader.header["git"] == git_sha() and git_sha() is not None
    assert n == len(records) == REC_TICKS and reader.skipped == 0
    ts = [r.t for r in records]
    assert ts[0] == 0.0 and all(b > a for a, b in zip(ts, ts[1:])) and ts[-1] < TEST_SCRIPT.seconds
    assert all(len(r.bodies) == 1 and r.blobs for r in records)
    assert camera.closed


def test_record_drops_motion_by_default(recorded, tmp_path, font5x7):
    out, _, _, _ = recorded
    reader = ScenarioReader(out)
    assert reader.header["inputs"] == ["blobs", "pose"]                 # every camera input less motion
    assert all(r.motion.size == 0 for r in reader)

    class PoseAndMotion(ClosingCamera):
        provides = frozenset({"pose", "motion"})
    kept = tmp_path / "motion.jsonl.gz"
    n, _, _ = run_record(kept, font5x7, PoseAndMotion, with_motion=True)
    reader = ScenarioReader(kept)
    records = list(reader)
    assert reader.header["inputs"] == ["motion", "pose"] and n == len(records) == REC_TICKS
    assert all(r.motion.shape == (64, 128) and r.motion.any() and not r.blobs for r in records)


def test_raw_writes_tap_records_and_closes_after_the_camera(tmp_path, font5x7, monkeypatch):
    events: list = []
    monkeypatch.setattr(record_mod, "ScenarioWriter", logged_writer(events))
    clock = GuardClock()
    camera = TapCamera(person_frames(), clock, events)
    cfg = make_cfg(WALL, camera="mediapipe", camera_fps=10, mirror=False)
    out = tmp_path / "raw.jsonl.gz"
    n = record(cfg, TEST_SCRIPT, camera, NoSource(), RecordingDisplay(keep_all=False), font5x7, out, raw=True,
               clock=clock, sleep=clock.sleep)
    reader = ScenarioReader(out)
    records = list(reader)
    h = reader.header
    assert (h["type"], h["fps"], h["inputs"], h["mirror"], h["script"]) == ("raw", 10, ["motion", "pose"], False,
                                                                           "test-2s")
    assert reader.cues == TEST_SCRIPT.cues and reader.skipped == 0
    tapped = [t for t, written in camera.captures if written]
    assert n == len(records) == len(tapped) == REC_TICKS
    assert [r.t for r in records] == pytest.approx(tapped, abs=1e-6)
    rec_start = clock.start + COUNTDOWN
    before = [written for t, written in camera.captures if t < rec_start - 1e-6]
    assert len(before) == COUNT_TICKS and not any(before)          # the countdown's captures: made, none written
    assert all(rec_start - 1e-6 < t <= rec_start + TEST_SCRIPT.seconds + 1e-6 for t in tapped)
    assert camera.captures[-1][1] is False                         # the capture at close(), after done(): not written
    assert events == [("camera closed", None), "writer closed"]    # the tap cleared, the camera, then the writer


@pytest.mark.parametrize("raw", [False, True], ids=["sensed", "raw"])
def test_a_raising_scene_ends_record_and_closes_the_writer(tmp_path, font5x7, monkeypatch, raw):
    events: list = []
    monkeypatch.setattr(record_mod, "ScenarioWriter", logged_writer(events))

    class Raising(RecordScene):
        updates = 0

        def update(self, sensed, dt):
            super().update(sensed, dt)
            Raising.updates += 1
            if Raising.updates == COUNT_TICKS + 10:
                raise RuntimeError("scene boom")
    monkeypatch.setattr(record_mod, "RecordScene", Raising)
    clock = GuardClock()
    camera = (TapCamera if raw else ClosingCamera)(person_frames(), clock, events)
    out = tmp_path / "boom.jsonl.gz"
    with pytest.raises(RuntimeError, match="scene boom"):
        record(make_cfg(WALL, camera="mediapipe"), TEST_SCRIPT, camera, NoSource(), RecordingDisplay(keep_all=False),
               font5x7, out, raw=raw, clock=clock, sleep=clock.sleep)
    assert events == [("camera closed", None if raw else "no tap"), "writer closed"]
    reader = ScenarioReader(out)
    records = list(reader)
    assert reader.skipped == 0                                     # a whole gzip stream: closed, not cut off
    want = sum(written for _, written in camera.captures) if raw else 10
    assert len(records) == want and want > 0


# ----- I2's sheet: python -m tools.arcade_shot jump --lobby tests.arcade.test_record:sheet_scene
#       --scenario tests.arcade.test_record:sheet_frames --out docs/superpowers/workflow/evidence/it21/record -----

def sheet_scene(games, cfg) -> RecordScene:
    """door-point's recording as the lobby (tools.arcade_shot calls it as f(games, cfg)); its records are kept in
    memory and dropped."""
    return RecordScene(RECORD_SCRIPTS["door-point"], ListWriter(), with_motion=False)


def sheet_frames():
    """12 s: 3, 2, 1, then door-point's first cues while a person walks in from the left (3.5 s to 5.5 s), stands
    and points with the right hand up (6 s to 9 s: "POINT AT DOOR 1", "HOLD")."""
    person = Person(0.05, id=1).arrive(3.5).walk(0.5, 2.0, at=3.5).raise_hand(6.0, 3.0)
    return scene(persons=[person], ticks=12 * FPS)


def test_the_sheet_helpers(font5x7):
    scene_ = sheet_scene([], make_cfg(WALL))
    assert isinstance(scene_, RecordScene) and scene_.script is RECORD_SCRIPTS["door-point"]
    frames = list(sheet_frames())
    assert len(frames) == 12 * FPS and not frames[0].bodies and frames[-1].bodies
