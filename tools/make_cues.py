"""Generate the four sound cues (deterministic, so the committed bytes equal a fresh run).

    python -m tools.make_cues audio
"""
from __future__ import annotations

import sys
import wave
from pathlib import Path

import numpy as np

RATE = 22050


def _tone(freq: float, seconds: float, level: float, attack: float = 0.01, release: float = 0.05) -> np.ndarray:
    t = np.arange(int(RATE * seconds)) / RATE
    env = np.minimum(1.0, t / attack) * np.minimum(1.0, (seconds - t) / release) * np.exp(-2.5 * t / seconds)
    return level * env * np.sin(2 * np.pi * freq * t)


CUES: dict[str, np.ndarray] = {
    "keypress": _tone(1200, 0.04, 0.4, 0.003, 0.02),
    "compile": np.concatenate([_tone(440, 0.08, 0.35), _tone(554, 0.08, 0.35)]),
    "run": np.concatenate([_tone(523, 0.08, 0.35), _tone(659, 0.08, 0.35), _tone(784, 0.12, 0.35)]),
    "error": np.concatenate([_tone(330, 0.18, 0.4, 0.02, 0.06), _tone(220, 0.28, 0.4, 0.02, 0.10)]),
}


def _write(path: Path, samples: np.ndarray) -> None:
    pcm = np.round(np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: python -m tools.make_cues OUT_DIR", file=sys.stderr)
        return 2
    out = Path(args[0])
    out.mkdir(parents=True, exist_ok=True)
    for name, samples in CUES.items():
        _write(out / f"{name}.wav", samples)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
