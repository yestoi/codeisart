"""ArcadeConfig: the flat arcade.toml (spec 4.3). Calibration lives in arcade/calibration.py."""
from __future__ import annotations

import dataclasses
import math
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

BACKENDS = ("sdl", "fake", "colorlight", "ddp")
CAMERAS = ("mediapipe", "imx500", "replay", "none")
AUDIOS = ("sounddevice", "replay", "none")
LOOKS = ("plain", "led", "distance")
HHMM = re.compile(r"([01]\d|2[0-3]):[0-5]\d")


@dataclass
class ArcadeConfig:
    width: int = 128
    height: int = 32
    backend: str = "sdl"
    sdl_scale: int = 8
    iface: str = "eth0"
    ddp_host: str = "127.0.0.1"
    ddp_port: int = 4048
    camera: str = "mediapipe"
    camera_index: int = 0
    camera_fps: int = 10
    audio: str = "sounddevice"
    audio_device: str = ""
    scenario: str = ""
    mirror: bool = True
    brightness: float = 0.4
    apl_cap_day: float = 0.12
    apl_cap_night: float = 0.06
    night_start: str = "01:00"
    night_end: str = "06:00"
    night_lux: float = 5.0
    gamma: float = 2.2
    look: str = "led"
    dwell_seconds: float = 1.2
    present_on_seconds: float = 1.0
    present_off_seconds: float = 3.0
    player_lost_seconds: float = 0.5
    leave_seconds: float = 8.0
    inactive_seconds: float = 30.0
    max_session_seconds: float = 180.0
    exit_seconds: float = 3.0
    allow_record: bool = False
    data_dir: Path = Path("data")
    font_path: Path = Path("fonts/5x7.bin")
    fps: int = 30

    @property
    def size(self) -> tuple[int, int]:
        return (self.width, self.height)

    @property
    def layout(self) -> str:
        return f"{self.width}x{self.height}"


def _coerce(name: str, value, default):
    """A TOML value as the field's type. Ints are accepted for float fields; true/false only for bools."""
    if isinstance(default, Path):
        if isinstance(value, str):
            return Path(value)
    elif isinstance(default, bool):
        if isinstance(value, bool):
            return value
    elif isinstance(value, bool):
        pass
    elif isinstance(default, float) and isinstance(value, (int, float)):
        return float(value)
    elif isinstance(value, type(default)):
        return value
    kind = "a path string" if isinstance(default, Path) else type(default).__name__
    raise ValueError(f"{name} must be {kind}, got {value!r}")


def load_config(path: Path | str) -> ArcadeConfig:
    path = Path(path)
    raw = tomllib.loads(path.read_text()) if path.exists() else {}
    defaults = ArcadeConfig()
    names = {f.name for f in dataclasses.fields(ArcadeConfig)}
    unknown = sorted(set(raw) - names)
    if unknown:
        raise ValueError(f"unknown config keys: {unknown}")
    cfg = ArcadeConfig(**{k: _coerce(k, v, getattr(defaults, k)) for k, v in raw.items()})
    for name, allowed in (("backend", BACKENDS), ("camera", CAMERAS), ("audio", AUDIOS), ("look", LOOKS)):
        if getattr(cfg, name) not in allowed:
            raise ValueError(f"{name} must be one of {allowed}, got {getattr(cfg, name)!r}")
    for name in ("night_start", "night_end"):
        if not HHMM.fullmatch(getattr(cfg, name)):
            raise ValueError(f"{name} must be HH:MM (00:00 to 23:59), got {getattr(cfg, name)!r}")
    for name in ("brightness", "apl_cap_day", "apl_cap_night"):
        if not 0 < getattr(cfg, name) <= 1:   # NaN fails too
            raise ValueError(f"{name} must be in (0, 1], got {getattr(cfg, name)}")
    for name in ("fps", "camera_fps", "gamma"):
        if not getattr(cfg, name) > 0:
            raise ValueError(f"{name} must be greater than 0, got {getattr(cfg, name)}")
    if not math.isfinite(cfg.gamma):
        raise ValueError(f"gamma must be finite, got {cfg.gamma}")
    if cfg.sdl_scale < 1:
        raise ValueError(f"sdl_scale must be at least 1, got {cfg.sdl_scale}")
    for name in [f.name for f in dataclasses.fields(ArcadeConfig) if f.name.endswith("_seconds")] + ["night_lux"]:
        if not getattr(cfg, name) >= 0:
            raise ValueError(f"{name} must be 0 or more, got {getattr(cfg, name)}")
    if cfg.width < 8 or cfg.height < 8:
        raise ValueError(f"width and height must be at least 8, got {cfg.layout}")
    return cfg
