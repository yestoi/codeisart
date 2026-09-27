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
    # x0, y0, x1, y1, 0..1, in the mirrored display space the keypoints use (after mirror_keypoints):
    # a change of the mirror setting after calibrating flips the zone.
    zone: tuple[float, float, float, float] = (0.2, 0.2, 0.8, 0.8)
    min_height: float = 0.45                 # shortest body, as a fraction of frame height, that counts in-zone
    baseline_scale: float = 0.0              # the operator's standing scale; 0.0 means not measured
    static_mask: tuple[tuple[float, float, float], ...] = ()   # static lights as (x, y, radius), 0..1, same space
    audio_floor_db: float = -90.0
    calibrated: bool = False


FIELDS = tuple(f.name for f in dataclasses.fields(Calibration))


def _number(name: str, value, lo: float, hi: float) -> float:
    """A JSON number within [lo, hi]. Booleans, strings and NaN are rejected."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not lo <= value <= hi:
        raise ValueError(f"{name} must be a number in [{lo}, {hi}], got {value!r}")
    return float(value)


def _from_json(d) -> Calibration:
    """Every key present is validated, and one bad value rejects the file; a missing key takes its default."""
    if not isinstance(d, dict):
        raise ValueError(f"expected a JSON object, got {type(d).__name__}")
    values: dict = {}
    if "zone" in d:
        if not isinstance(d["zone"], list) or len(d["zone"]) != 4:
            raise ValueError(f"zone must be [x0, y0, x1, y1], got {d['zone']!r}")
        zone = tuple(_number("zone", v, 0.0, 1.0) for v in d["zone"])
        if not (zone[0] < zone[2] and zone[1] < zone[3]):
            raise ValueError(f"zone must have x0 < x1 and y0 < y1, got {zone}")
        values["zone"] = zone
    for name in ("min_height", "baseline_scale"):
        if name in d:
            values[name] = _number(name, d[name], 0.0, 1.0)
    if "static_mask" in d:
        if not isinstance(d["static_mask"], list):
            raise ValueError(f"static_mask must be a list of [x, y, radius], got {d['static_mask']!r}")
        mask = []
        for light in d["static_mask"]:
            if not isinstance(light, list) or len(light) != 3:
                raise ValueError(f"static_mask entries must be [x, y, radius], got {light!r}")
            x, y, r = (_number("static_mask", v, 0.0, 1.0) for v in light)
            if r == 0.0:
                raise ValueError(f"static_mask radius must be over 0, got {light!r}")
            mask.append((x, y, r))
        values["static_mask"] = tuple(mask)
    if "audio_floor_db" in d:
        values["audio_floor_db"] = _number("audio_floor_db", d["audio_floor_db"], -200.0, 0.0)
    if "calibrated" in d:
        if not isinstance(d["calibrated"], bool):
            raise ValueError(f"calibrated must be true or false, got {d['calibrated']!r}")
        values["calibrated"] = d["calibrated"]
    return dataclasses.replace(Calibration(), **values)


def load_calibration(data_dir: Path | str) -> Calibration:
    """The saved calibration, or the uncalibrated defaults when the file is absent or unreadable."""
    path = Path(data_dir) / FILENAME
    if not path.exists():
        return Calibration()
    try:
        data = json.loads(path.read_text())
        cal = _from_json(data)
    except (OSError, ValueError) as e:
        log.warning("ignoring %s (%s: %s); using the uncalibrated defaults", path, type(e).__name__, e)
        return Calibration()
    missing = [name for name in FIELDS if name not in data]
    unknown = sorted(set(data) - set(FIELDS))
    if missing or unknown:
        log.warning("%s: missing %s take their defaults; unknown %s ignored", path, missing, unknown)
    return cal


def save_calibration(data_dir: Path | str, cal: Calibration) -> None:
    path = Path(data_dir) / FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(FILENAME + ".tmp")
    with open(tmp, "w") as f:
        json.dump(dataclasses.asdict(cal), f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY)   # the rename lives in the directory: sync it too
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
