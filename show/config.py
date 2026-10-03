from __future__ import annotations

import dataclasses
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

PHOSPHORS: dict[str, tuple[int, int, int]] = {
    "green": (51, 255, 51),
    "amber": (255, 176, 0),
}
STRIP_LOOKS = ("reverse", "dim-reverse", "bright-on-field", "plain")


@dataclass
class Config:
    backend: str = "sdl"
    width: int = 512
    height: int = 192
    brightness: float = 0.15
    brightness_cap: float = 0.40
    sdl_scale: int = 2
    columns: int = 80
    rows: int = 24
    phosphor: str = "green"
    glow: bool = False
    view: str = "text"       # text | ink (one dot a cell, for a wall smaller than the terminal: the 128x64 PoC)
    strip: bool = False      # the strip on the last row; off (Q100): the portraits carry the credit, not the wall
    strip_look: str = "bright-on-field"   # the strip's look (Q54, the loop's reading)
    gamma: float = 2.2            # the governor's light model: 1.0 (the card applies gamma) to 2.2 (bytes as they are)
    entries_dir: Path = Path("entries")
    audio_dir: Path = Path("audio")
    font_path: Path = Path("fonts/5x7.bin")
    button_pins: list[int] = field(default_factory=lambda: [5, 6, 13, 19, 26])
    light_pins: list[int] = field(default_factory=lambda: [12, 16, 20, 21, 25])
    lightbox_pins: list[int] = field(default_factory=lambda: [17, 22, 23, 24, 27])
    ddp_host: str = "127.0.0.1"
    ddp_port: int = 4048
    colorlight_iface: str = "eth0"
    dwell: float = 4.0
    error_hold: float = 3.0
    typewriter_cps: int = 400
    attract_lps: float = 3.0
    fps: int = 20
    capture: bool = False
    volume: float = 0.6
    quiet_hours: str = ""
    crowd_run_seconds: float = 10.0
    idle_run_seconds: float = 40.0
    attract_autoplay_minutes: float = 5.0
    min_build_seconds: float = 1.5
    pump_bytes: int = 4096
    pump_ms: float = 8.0
    # The reel (2026-10-03): a title card before the source, the typed page held still before the build, nothing fed
    # to the terminal during the build, the phase on the strip, a card at the end of a --play list. All off by default.
    card_seconds: float = 0.0
    source_hold: float = 0.0
    build_quiet: bool = False
    strip_phase: bool = False
    end_card: list[str] = field(default_factory=list)

    @property
    def phosphor_rgb(self) -> tuple[int, int, int]:
        return PHOSPHORS[self.phosphor]

    @property
    def effective_brightness(self) -> float:
        return min(self.brightness, self.brightness_cap)


def load_config(path: Path) -> Config:
    data = tomllib.loads(path.read_text()) if path.exists() else {}
    cfg = Config()
    fields = {f.name: f for f in dataclasses.fields(Config)}
    for key, value in data.items():
        if key not in fields:
            raise ValueError(f"{path}: unknown config key {key!r}")
        if isinstance(getattr(cfg, key), Path):
            value = Path(value)
        setattr(cfg, key, value)
    if cfg.phosphor not in PHOSPHORS:
        raise ValueError(f"{path}: phosphor must be one of {sorted(PHOSPHORS)}")
    if cfg.view not in ("text", "ink"):
        raise ValueError(f"{path}: view must be text or ink")
    if not isinstance(cfg.strip, bool):
        raise ValueError(f"{path}: strip must be true or false")
    if cfg.strip_look not in STRIP_LOOKS:
        raise ValueError(f"{path}: strip_look must be one of {STRIP_LOOKS}")
    if isinstance(cfg.gamma, bool) or not isinstance(cfg.gamma, (int, float)) or not 1.0 <= cfg.gamma <= 2.2:
        raise ValueError(f"{path}: gamma must be 1.0 (the card applies gamma) to 2.2 (bytes as they are)")
    if isinstance(cfg.fps, bool) or not isinstance(cfg.fps, int) or cfg.fps < 2:
        raise ValueError(f"{path}: fps must be an int of at least 2")
    if not 0.0 <= cfg.brightness_cap <= 1.0:
        raise ValueError(f"{path}: brightness_cap must be between 0 and 1")
    for key in ("card_seconds", "source_hold"):
        value = getattr(cfg, key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"{path}: {key} must be a number of seconds, 0 or more")
    for key in ("build_quiet", "strip_phase"):
        if not isinstance(getattr(cfg, key), bool):
            raise ValueError(f"{path}: {key} must be true or false")
    if not isinstance(cfg.end_card, list) or not all(isinstance(line, str) for line in cfg.end_card):
        raise ValueError(f"{path}: end_card must be a list of strings")
    return cfg
