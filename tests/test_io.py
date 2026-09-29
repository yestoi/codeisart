from __future__ import annotations

import logging
import math
import sys
import threading
import types
from datetime import datetime, time
from pathlib import Path

import pytest

from show import audio, input as show_input, lights
from show.audio import AudioCues, FakeAudio, in_quiet_hours, parse_quiet_hours
from show.input import ButtonInput, PressQueue, make_buttons
from show.lights import (FakeLights, GpioLights, LIGHTBOX, MODES, FAST_HZ, SLOW_HZ, FLASH_S, levels,
                         make_lights, pulse_level)


# ---------------------------------------------------------------- fake gpiozero

class FakeButton:
    made: list["FakeButton"] = []

    def __init__(self, pin, pull_up=True, bounce_time=None):
        self.pin, self.pull_up, self.bounce_time = pin, pull_up, bounce_time
        self.when_pressed = None
        self.closed = False
        FakeButton.made.append(self)

    def close(self):
        self.closed = True


class FakePWMLED:
    made: list["FakePWMLED"] = []

    def __init__(self, pin):
        self.pin = pin
        self.value = 0.0
        FakePWMLED.made.append(self)

    def close(self):
        pass


@pytest.fixture
def fake_gpiozero(monkeypatch):
    FakeButton.made = []
    FakePWMLED.made = []
    mod = types.ModuleType("gpiozero")
    mod.Button = FakeButton
    mod.PWMLED = FakePWMLED
    monkeypatch.setitem(sys.modules, "gpiozero", mod)
    return mod


@pytest.fixture
def no_gpiozero(monkeypatch):
    monkeypatch.setitem(sys.modules, "gpiozero", None)     # import raises ImportError


# ---------------------------------------------------------------- input

def test_press_queue_drains_in_order():
    q = PressQueue()
    for s in (3, 1, 2):
        q.put(s)
    assert q.drain() == [3, 1, 2]
    assert q.drain() == []


def test_press_queue_is_thread_safe():
    q = PressQueue()

    def work():
        for i in range(1000):
            q.put(i % 5 + 1)

    threads = [threading.Thread(target=work) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert len(q.drain()) == 4000


def test_buttons_map_pins_to_stations(fake_gpiozero):
    q = PressQueue()
    inp = ButtonInput([5, 6, 13], q)
    assert [b.pin for b in FakeButton.made] == [5, 6, 13]
    assert all(b.pull_up and b.bounce_time == 0.05 for b in FakeButton.made)
    FakeButton.made[0].when_pressed()
    FakeButton.made[2].when_pressed()
    assert q.drain() == [1, 3]
    inp.close()
    assert all(b.closed for b in FakeButton.made)


def test_make_buttons_without_gpiozero_is_none_and_logs(no_gpiozero, caplog):
    with caplog.at_level(logging.ERROR):
        assert make_buttons([5, 6], PressQueue()) is None
    assert any(r.levelno >= logging.ERROR for r in caplog.records)


# ---------------------------------------------------------------- lights

def test_levels_follow_the_modes():
    for mode, box in LIGHTBOX.items():
        assert levels(mode, 0.3, None)[0] == box
    assert LIGHTBOX == {"off": 0.0, "on": 0.4, "bright": 1.0, "pulse": 0.4}
    assert levels("off", 0.3, None)[1] == 0.0
    assert levels("bright", 0.3, None)[1] == 1.0
    # the slow ring: peak at a quarter period (0.5 s), trough at three quarters (1.5 s)
    assert levels("on", 0.5, None)[1] == pytest.approx(1.0)
    assert levels("on", 1.5, None)[1] == pytest.approx(0.0, abs=1e-9)
    # the fast ring: peak at 0.125 s, trough at 0.375 s
    assert levels("pulse", 0.125, None)[1] == pytest.approx(1.0)
    assert levels("pulse", 0.375, None)[1] == pytest.approx(0.0, abs=1e-9)
    assert pulse_level(0.25, 1.0) == pytest.approx(1.0)
    assert pulse_level(0.0, 2.0) == pytest.approx(0.5)
    assert (SLOW_HZ, FAST_HZ) == (0.5, 2.0)


def test_flash_blinks_the_ring_for_0_3_s_then_returns():
    for mode in ("off", "on", "bright", "pulse"):
        t0 = 10.0
        assert levels(mode, t0 + 0.05, t0)[1] == 1.0            # full
        assert levels(mode, t0 + 0.15, t0)[1] == 0.0            # dark, even over "bright"
        assert levels(mode, t0 + 0.25, t0)[1] == 1.0            # full again
        after = t0 + FLASH_S + 0.01
        assert levels(mode, after, t0) == levels(mode, after, None)
        # the lightbox is untouched by a flash
        assert levels(mode, t0 + 0.15, t0)[0] == LIGHTBOX[mode]


def test_all_off_darkens_everything():
    fl = FakeLights()
    for s in (1, 2, 3):
        fl.set(s, "bright")
    fl.flash(2, 5.0)
    fl.all_off()
    fl.tick(5.05)
    assert set(fl.modes.values()) <= {"off"}
    assert all(v == (0.0, 0.0) for v in fl.levels.values())


def test_unknown_mode_is_an_error():
    fl = FakeLights()
    with pytest.raises(ValueError):
        fl.set(1, "strobe")
    assert set(MODES) == {"off", "on", "bright", "pulse"}


def test_fake_lights_record_levels_on_tick():
    fl = FakeLights()
    fl.set(1, "bright")
    fl.tick(1.0)
    assert fl.modes[1] == "bright"
    assert fl.levels[1] == (1.0, 1.0)


def test_gpio_lights_write_both_outputs(fake_gpiozero):
    gl = GpioLights([12, 16], [17, 22])
    assert [l.pin for l in FakePWMLED.made] == [12, 16, 17, 22]
    gl.set(1, "bright")
    gl.set(2, "on")
    gl.tick(0.5)
    by_pin = {l.pin: l.value for l in FakePWMLED.made}
    assert by_pin[12] == 1.0 and by_pin[17] == 1.0             # station 1: ring, lightbox
    assert by_pin[16] == pytest.approx(1.0) and by_pin[22] == 0.4   # station 2: slow ring at peak
    gl.close()


def test_make_lights_without_gpiozero_falls_back_and_logs(no_gpiozero, caplog):
    with caplog.at_level(logging.ERROR):
        fl = make_lights([12, 16], [17, 22])
    assert type(fl) is FakeLights
    assert any(r.levelno >= logging.ERROR for r in caplog.records)


def test_make_lights_with_gpiozero_is_gpio(fake_gpiozero):
    assert isinstance(make_lights([12], [17]), GpioLights)


# ---------------------------------------------------------------- audio

def test_quiet_hours_parse_and_wrap_midnight():
    assert parse_quiet_hours("") is None
    w = parse_quiet_hours("23:00-06:00")
    assert w == (time(23, 0), time(6, 0))
    assert in_quiet_hours(w, time(23, 30))
    assert in_quiet_hours(w, time(5, 59))
    assert not in_quiet_hours(w, time(6, 0))
    assert not in_quiet_hours(w, time(12, 0))
    day = parse_quiet_hours("02:00-08:00")
    assert in_quiet_hours(day, time(2, 0)) and not in_quiet_hours(day, time(8, 0))
    assert not in_quiet_hours(None, time(3, 0))
    for bad in ("nonsense", "25:00-08:00", "02:00", "02:00-"):
        with pytest.raises(ValueError):
            parse_quiet_hours(bad)


class FakeSound:
    def __init__(self, path):
        self.path = path
        self.volume = None
        self.plays = 0

    def set_volume(self, v):
        self.volume = v

    def play(self):
        self.plays += 1


class FakeMixer:
    def __init__(self):
        self.sounds: dict[str, FakeSound] = {}

    def Sound(self, path):
        s = FakeSound(path)
        self.sounds[Path(path).stem] = s
        return s


@pytest.fixture
def wavdir(tmp_path):
    d = tmp_path / "audio"
    d.mkdir()
    for cue in audio.CUES:
        (d / f"{cue}.wav").write_bytes(b"RIFF")
    return d


def at(h, m=0):
    return lambda: datetime(2026, 11, 11, h, m)


def test_bad_quiet_hours_log_and_mean_none(wavdir, caplog):
    mixer = FakeMixer()
    with caplog.at_level(logging.WARNING):
        cues = AudioCues(wavdir, quiet_hours="garbage", clock=at(3), mixer=mixer)
    assert any(r.levelno >= logging.WARNING for r in caplog.records)
    cues.play("keypress")
    assert mixer.sounds["keypress"].plays == 1


def test_cues_are_muted_in_quiet_hours(wavdir):
    mixer = FakeMixer()
    cues = AudioCues(wavdir, quiet_hours="02:00-08:00", clock=at(3), mixer=mixer)
    cues.play("keypress")
    assert mixer.sounds["keypress"].plays == 0
    cues2 = AudioCues(wavdir, quiet_hours="02:00-08:00", clock=at(9), mixer=mixer)
    cues2.play("keypress")
    assert mixer.sounds["keypress"].plays == 1


def test_volume_is_set_on_each_sound(wavdir):
    mixer = FakeMixer()
    AudioCues(wavdir, volume=0.6, mixer=mixer)
    assert set(mixer.sounds) == set(audio.CUES)
    assert all(s.volume == 0.6 for s in mixer.sounds.values())
    mixer2 = FakeMixer()
    AudioCues(wavdir, volume=1.7, mixer=mixer2)
    assert all(s.volume == 1.0 for s in mixer2.sounds.values())
    mixer3 = FakeMixer()
    AudioCues(wavdir, volume=-2, mixer=mixer3)
    assert all(s.volume == 0.0 for s in mixer3.sounds.values())


def test_missing_or_unknown_cue_is_a_noop(tmp_path):
    empty = tmp_path / "none"
    empty.mkdir()
    cues = AudioCues(empty, mixer=FakeMixer())
    cues.play("keypress")              # file missing
    cues.play("zzz")                   # unknown
    fa = FakeAudio()
    fa.play("run")
    assert fa.played == ["run"]


def test_mixer_failure_mutes_and_logs(wavdir, monkeypatch, caplog):
    class Boom:
        def init(self, *a, **k):
            raise RuntimeError("no device")

    fake_pygame = types.ModuleType("pygame")
    fake_pygame.mixer = Boom()
    monkeypatch.setitem(sys.modules, "pygame", fake_pygame)
    with caplog.at_level(logging.ERROR):
        cues = AudioCues(wavdir)
    assert any(r.levelno >= logging.ERROR for r in caplog.records)
    cues.play("keypress")              # muted, no raise


def test_play_never_raises(wavdir):
    class Exploding(FakeMixer):
        def Sound(self, path):
            s = super().Sound(path)
            def bad():
                raise OSError("device gone")
            s.play = bad
            return s

    cues = AudioCues(wavdir, mixer=Exploding())
    cues.play("keypress")
    cues.play("error")
    bad_clock = AudioCues(wavdir, quiet_hours="02:00-08:00", mixer=FakeMixer(),
                          clock=lambda: (_ for _ in ()).throw(RuntimeError("clock")))
    bad_clock.play("run")
