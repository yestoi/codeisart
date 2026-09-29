from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from tools import make_cues

ROOT = Path(__file__).resolve().parents[1]


def read_wav(path: Path):
    with wave.open(str(path), "rb") as w:
        assert (w.getframerate(), w.getsampwidth(), w.getnchannels()) == (22050, 2, 1)
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")


def test_make_cues_writes_four_wavs(tmp_path):
    assert make_cues.main([str(tmp_path)]) == 0
    for cue in ("keypress", "compile", "run", "error"):
        data = read_wav(tmp_path / f"{cue}.wav")
        assert len(data) > 500
        assert np.abs(data).max() > 0


def test_error_cue_is_a_soft_two_tone(tmp_path):
    make_cues.main([str(tmp_path)])
    x = read_wav(tmp_path / "error.wav").astype(float)
    peak_level = np.abs(x).max() / 32768.0
    near = float(np.mean(np.abs(x) >= 0.99 * np.abs(x).max()))
    half = len(x) // 2
    freqs = []
    for part in (x[:half], x[half:]):
        spec = np.abs(np.fft.rfft(part * np.hanning(len(part))))
        freqs.append(np.argmax(spec) * make_cues.RATE / len(part))
    print(f"error cue: peaks {freqs[0]:.1f} Hz then {freqs[1]:.1f} Hz, "
          f"{near * 100:.2f}% of samples near the peak, peak {peak_level:.3f} of full scale")
    assert freqs[0] > freqs[1] + 50            # two peaks, falling
    assert near < 0.05                         # a square wave has nearly all
    assert peak_level <= 0.5


def test_committed_cues_match_the_generator(tmp_path):
    make_cues.main([str(tmp_path)])
    for cue in ("keypress", "compile", "run", "error"):
        assert (ROOT / "audio" / f"{cue}.wav").read_bytes() == (tmp_path / f"{cue}.wav").read_bytes()
