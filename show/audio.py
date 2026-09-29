"""Sound cues through pygame.mixer, with a volume and quiet hours."""
from __future__ import annotations

import logging
from datetime import datetime, time
from pathlib import Path
from typing import Callable

log = logging.getLogger(__name__)

CUES = ("keypress", "compile", "run", "error")


def parse_quiet_hours(spec: str) -> tuple[time, time] | None:
    if not spec.strip():
        return None
    try:
        start, end = spec.strip().split("-")
        return time.fromisoformat(start.strip()), time.fromisoformat(end.strip())
    except ValueError:
        raise ValueError(f"quiet_hours must look like 02:00-08:00, got {spec!r}") from None


def in_quiet_hours(window: tuple[time, time] | None, t: time) -> bool:
    if window is None:
        return False
    start, end = window
    if start <= end:
        return start <= t < end
    return t >= start or t < end


class FakeAudio:
    def __init__(self) -> None:
        self.played: list[str] = []

    def play(self, cue: str) -> None:
        self.played.append(cue)


class AudioCues:
    def __init__(self, dir: Path, volume: float = 0.6, quiet_hours: str = "",
                 clock: Callable[[], datetime] = datetime.now, mixer=None) -> None:
        self._clock = clock
        self._sounds: dict[str, object] = {}
        try:
            self._window = parse_quiet_hours(quiet_hours)
        except ValueError:
            log.warning("bad quiet_hours %r, no quiet hours", quiet_hours)
            self._window = None
        if mixer is None:
            try:
                import pygame

                pygame.mixer.init()
                mixer = pygame.mixer
            except Exception:
                log.error("audio unavailable, cues are muted", exc_info=True)
                return
        volume = min(1.0, max(0.0, float(volume)))
        for cue in CUES:
            path = Path(dir) / f"{cue}.wav"
            try:
                if not path.exists():
                    log.warning("missing cue file %s", path)
                    continue
                sound = mixer.Sound(str(path))
                sound.set_volume(volume)
                self._sounds[cue] = sound
            except Exception:
                log.error("could not load cue %s", path, exc_info=True)

    def play(self, cue: str) -> None:
        try:
            sound = self._sounds.get(cue)
            if sound is None:
                return
            if in_quiet_hours(self._window, self._clock().time()):
                return
            sound.play()
        except Exception:
            log.error("playing cue %s failed", cue, exc_info=True)
