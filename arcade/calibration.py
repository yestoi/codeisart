"""Per-setup calibration (spec 6.6), stored in data_dir/calibration.json and read at startup."""
from __future__ import annotations

import dataclasses
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("arcade")

FILENAME = "calibration.json"


@dataclass(frozen=True)
class Calibration:
    zone: tuple[float, float, float, float] = (0.2, 0.2, 0.8, 0.8)   # x0, y0, x1, y1 in camera space, 0..1
    min_height: float = 0.45                 # shortest body, as a fraction of frame height, that counts in-zone
    baseline_scale: float = 0.0              # the operator's standing scale; 0.0 means not measured
    static_mask: tuple[tuple[float, float, float], ...] = ()   # static lights as (x, y, radius), 0..1
    audio_floor_db: float = -90.0
    calibrated: bool = False


def _from_json(d: dict) -> Calibration:
    zone = tuple(float(v) for v in d["zone"])
    if len(zone) != 4 or not (0.0 <= zone[0] < zone[2] <= 1.0 and 0.0 <= zone[1] < zone[3] <= 1.0):
        raise ValueError(f"zone must be x0 < x1 and y0 < y1 within 0..1, got {zone}")
    mask = tuple(tuple(float(v) for v in light) for light in d["static_mask"])
    if any(len(light) != 3 for light in mask):
        raise ValueError("static_mask entries must be (x, y, radius)")
    return Calibration(zone=zone, min_height=float(d["min_height"]), baseline_scale=float(d["baseline_scale"]),
                       static_mask=mask, audio_floor_db=float(d["audio_floor_db"]),
                       calibrated=bool(d["calibrated"]))


def load_calibration(data_dir: Path | str) -> Calibration:
    """The saved calibration, or the uncalibrated defaults when the file is absent or unreadable."""
    path = Path(data_dir) / FILENAME
    if not path.exists():
        return Calibration()
    try:
        return _from_json(json.loads(path.read_text()))
    except (OSError, ValueError, KeyError, TypeError) as e:
        log.warning("ignoring %s (%s: %s); using the uncalibrated defaults", path, type(e).__name__, e)
        return Calibration()


def save_calibration(data_dir: Path | str, cal: Calibration) -> None:
    path = Path(data_dir) / FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(FILENAME + ".tmp")
    with open(tmp, "w") as f:
        json.dump(dataclasses.asdict(cal), f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
