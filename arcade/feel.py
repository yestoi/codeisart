"""Feel metrics (spec 9.3, 11): what a game feels like on the wall, measured through the real runner and judged
against per-kind budgets.

measure() runs the game's canonical scenario (its first FEEL_SECONDS) through run_headless at a layout, with
counterfactual reruns for latency, looks for the score in its frames (in the project's font, then through look's
distance model at 5 m), compares idle_body with nobody for the idle hint, and plays the game's bots (arcade/bots.py) over seeds. budgets() reads
feel_budgets.toml (per GameInfo.kind, then its layout table) and the game's own <name>_feel.toml, whose every
override needs a reason. judge() names each budget a metric misses; report() is all three, JSON-ready.
"""
from __future__ import annotations

import dataclasses
import itertools
import math
import statistics
import sys
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Sequence

import numpy as np

from arcade import bots, flash, look
from arcade.canvas import Canvas
from arcade.config import ArcadeConfig
from arcade.headless import RecordingDisplay, run_headless
from arcade.sensed import Body, Sensed
from arcade.sources.actors import TICK
from show.font import CELL_H, CELL_W

RESPONSE_PX = 12                   # pixels that must change for a response to count (spec 11)
LATENCY_TICKS = 2                  # spec 11's response budget; 5 x this is the value when nothing responds
PROBES = 8                         # canonical ticks probed for latency
FEEL_SECONDS = 20.0                # the part of canonical measured
FEEL_SEEDS = 20                    # spec 9.3's bot plays per bot
DIM_LEVEL = 140                    # a lit pixel with every channel under this is dim (spec 11)
SCORE_SCALES = (1, 2)              # text scales a score is looked for at (spec 7.4: scores use 2)
LEGIBLE_METRES = 5.0               # the distance a score must read from (spec 9.4's distance look)
LEGIBLE_SCALE = 4                  # preview px per wall px for the distance look (look.distance_sigma: 4 or more)
IDLE_WINDOW = 6.0                  # seconds of idle_body compared; the value when the wall never answers a body
DEFAULTS = Path(__file__).with_name("feel_budgets.toml")
INPUTS = {"cursor_x": lambda p: None if p.cursor is None else p.cursor[0],
          "cursor_y": lambda p: None if p.cursor is None else p.cursor[1],
          "zone_x": lambda p: p.zone_x}
BOUNDS = ("min", "max")


@dataclass(frozen=True)
class Budget:
    """One metric's bounds (either may be None) and, for a game's own override, its reason."""

    metric: str
    min: float | None
    max: float | None
    reason: str | None


def own_file(game_cls) -> Path | None:
    """<name>_feel.toml beside the game's module (it may not exist); None for a module without a file."""
    module = sys.modules.get(game_cls.__module__)
    path = getattr(module, "__file__", None)
    return None if path is None else Path(path).with_name(f"{game_cls.info.name}_feel.toml")


def _load(path: Path | None) -> dict:
    return tomllib.loads(path.read_text()) if path is not None and path.is_file() else {}


def _number(where: str, metric: str, key: str, value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{where}: {metric}.{key} must be a finite number, got {value!r}")
    return float(value)


def _bounds(where: str, metric: str, table, allowed: set[str]) -> dict:
    if not isinstance(table, dict) or not set(table) & set(BOUNDS) or not set(table) <= allowed:
        raise ValueError(f"{where}: {metric} must be a table with min and/or max (keys {sorted(allowed)}), "
                         f"got {table!r}")
    return {k: _number(where, metric, k, table[k]) for k in BOUNDS if k in table}


def budgets(game_cls, layout: str, defaults: Path = DEFAULTS, own: Path | None = None) -> dict[str, Budget]:
    """game_cls's budgets at layout: its kind's table in defaults, then that kind's layouts."<layout>" table, then
    [budgets."<layout>"] of the game's own file (own, else own_file(game_cls); an absent file overrides nothing).

    A later table sets only the bounds it gives: a metric's other bound is kept. Every entry of the game's own
    file needs a non-empty reason: without one ValueError names the metric."""
    kind = game_cls.info.kind
    table = _load(defaults).get(kind, {})
    merged: dict[str, dict] = {}
    for metric, bounds in table.items():
        if metric != "layouts":
            merged[metric] = _bounds(f"{defaults} [{kind}]", metric, bounds, set(BOUNDS))
    for metric, bounds in table.get("layouts", {}).get(layout, {}).items():
        merged[metric] = merged.get(metric, {}) | _bounds(f"{defaults} [{kind}.layouts.{layout}]", metric, bounds,
                                                          set(BOUNDS))
    path = own if own is not None else own_file(game_cls)
    reasons: dict[str, str] = {}
    for metric, entry in _load(path).get("budgets", {}).get(layout, {}).items():
        reason = entry.get("reason") if isinstance(entry, dict) else None
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"{path}: the override of {metric} at {layout} needs a non-empty reason")
        merged[metric] = merged.get(metric, {}) | _bounds(f"{path} [budgets.{layout}]", metric, entry,
                                                          {*BOUNDS, "reason"})
        reasons[metric] = reason.strip()
    return {m: Budget(m, b.get("min"), b.get("max"), reasons.get(m)) for m, b in merged.items()}


def control(game_cls, own: Path | None = None) -> tuple[str, str, int] | None:
    """The game file's [fidelity] as (input, xy, axis): input one of INPUTS, read from sensed.player; xy a *_xy
    debug_state key; axis 0 (x) or 1 (y). None without the file or the table; a bad table raises ValueError."""
    path = own if own is not None else own_file(game_cls)
    table = _load(path).get("fidelity")
    if table is None:
        return None
    what, xy, axis = (table.get(k) if isinstance(table, dict) else None for k in ("input", "xy", "axis"))
    if (what not in INPUTS or not isinstance(xy, str) or not xy.endswith("_xy") or isinstance(axis, bool)
            or axis not in (0, 1)):
        raise ValueError(f"{path}: [fidelity] needs input in {sorted(INPUTS)}, xy a *_xy key and axis 0 or 1, "
                         f"got {table!r}")
    return what, xy, axis


def _cursor(p: Body) -> tuple[float, float] | None:
    return p.cursor


def _xy(state: dict, key: str) -> tuple[float, float] | None:
    v = state.get(key)
    if (isinstance(v, (tuple, list)) and len(v) == 2
            and all(isinstance(c, (int, float, np.number)) and not isinstance(c, bool) for c in v)):
        return float(v[0]), float(v[1])
    return None


def _pearson(a: list[float], b: list[float]) -> float | None:
    if len(a) < 2:
        return None
    x, y = np.asarray(a, float), np.asarray(b, float)
    if x.std() == 0.0 or y.std() == 0.0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def _lit(frame: np.ndarray) -> np.ndarray:
    return frame.any(axis=2)


@lru_cache(maxsize=256)
def _text_mask(font, text: str, scale: int) -> np.ndarray | None:
    """text's lit pixels in the font at scale, cropped to them (read-only); None when nothing is lit."""
    canvas = Canvas(CELL_W * scale * len(text), CELL_H * scale, font)
    canvas.text(0, 0, text, (255, 255, 255), scale=scale)
    lit = _lit(canvas.frame)
    rows, cols = np.flatnonzero(lit.any(axis=1)), np.flatnonzero(lit.any(axis=0))
    if not len(rows):
        return None
    mask = lit[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1].copy()
    mask.flags.writeable = False
    return mask


def _window_sums(lit: np.ndarray, h: int, w: int) -> np.ndarray:
    """The lit count of every h by w window of lit, indexed by its top-left corner."""
    c = np.pad(lit.astype(np.int32).cumsum(axis=0).cumsum(axis=1), ((1, 0), (1, 0)))
    return c[h:, w:] - c[:-h, w:] - c[h:, :-w] + c[:-h, :-w]


def find_text(frame: np.ndarray, font, text: str, scales: Sequence[int] = SCORE_SCALES):
    """(x, y, mask) where text shows on frame in the project's font: mask is the text's lit pixels at one of
    scales, cropped to them, and frame's lit pixels in the box at (x, y) are exactly mask with a 1 px dark gutter
    round it (off the wall is dark). The top-most, then left-most match at the first scale that has one; None when
    the text does not show."""
    lit = np.pad(_lit(frame), 1)
    for scale in scales:
        mask = _text_mask(font, str(text), scale)
        if mask is None or mask.shape[0] + 2 > lit.shape[0] or mask.shape[1] + 2 > lit.shape[1]:
            continue
        want = np.pad(mask, 1)
        h, w = want.shape
        for y, x in np.argwhere(_window_sums(lit, h, w) == int(mask.sum())):
            if np.array_equal(lit[y:y + h, x:x + w], want):
                return int(x), int(y), mask
    return None


@lru_cache(maxsize=512)
def _seen(data: bytes, shape: tuple[int, int, int], gamma: float, metres: float) -> np.ndarray:
    """Each wall pixel's relative luminance, 0..1, in look's distance render at metres: the mean light over the
    pixel's LEGIBLE_SCALE by LEGIBLE_SCALE footprint, decoded from the preview's bytes."""
    frame = np.frombuffer(data, np.uint8).reshape(shape)
    shown = look.render(frame, "distance", LEGIBLE_SCALE, gamma, metres).astype(np.float64) / 255.0
    h, w, s = shape[0], shape[1], LEGIBLE_SCALE
    light = (shown ** look.MONITOR_GAMMA).reshape(h, s, w, s, 3).mean(axis=(1, 3))
    return light @ look.LUMA.astype(np.float64)


def legibility(frame: np.ndarray, x: int, y: int, mask: np.ndarray, gamma: float,
               metres: float = LEGIBLE_METRES) -> float:
    """How much of the text find_text found at (x, y) survives as the eye sees it from metres (look's distance
    model: blur and halation): the share of its box and 1 px gutter that the best single threshold on each wall
    pixel's seen luminance puts on mask's side (lit on a stroke, dark elsewhere). 1.0 when the glyph comes back
    whole; about 0.5 when it is a blob."""
    h, w = mask.shape
    margin = math.ceil(3 * look.HALATION_SIGMAS * look.distance_sigma(metres)) + 1   # the glow's reach
    y0, x0 = max(0, y - 1 - margin), max(0, x - 1 - margin)
    crop = np.ascontiguousarray(frame[y0:y + h + 1 + margin, x0:x + w + 1 + margin])
    luma = np.pad(_seen(crop.tobytes(), crop.shape, float(gamma), float(metres)), 1)   # off the wall is dark
    box = luma[y - y0:y - y0 + h + 2, x - x0:x - x0 + w + 2].ravel()
    order = np.argsort(box, kind="stable")
    lit, seen = np.pad(mask, 1).ravel()[order], box[order]
    # A threshold after the k dimmest calls them dark and the rest lit; it cannot split equal luminances.
    right = np.concatenate(([0], np.cumsum(~lit))) + int(lit.sum()) - np.concatenate(([0], np.cumsum(lit)))
    splits = np.concatenate(([True], seen[1:] > seen[:-1], [True]))
    return float(right[splits].max() / lit.size)


def _score(font, pushed: list[np.ndarray], trace: list[dict], current: list[bool], gamma: float) -> dict:
    """score_visible: over the ticks the game runs with an integer debug_state()["score"], the share whose pushed
    frame shows it (find_text); score_legible: the median legibility() at LEGIBLE_METRES of those shown. None where
    no tick counts."""
    ticks, seen = 0, []
    for frame, state, on in zip(pushed, trace, current):
        score = state.get("score")
        if isinstance(score, float) and score.is_integer():
            score = int(score)
        if not on or isinstance(score, bool) or not isinstance(score, (int, np.integer)):
            continue
        ticks += 1
        found = find_text(frame, font, str(score))
        if found is not None:
            seen.append(legibility(frame, *found, gamma))
    return {"score_visible": len(seen) / ticks if ticks else None,
            "score_legible": float(statistics.median(seen)) if seen else None}


def _idle_hint(cfg, font, game_cls, seed: int) -> float | None:
    """Seconds from idle_body's first record with a body until its pushed frame differs in RESPONSE_PX pixels or
    more from nobody's under the same seed, over IDLE_WINDOW; IDLE_WINDOW when never; None without both
    scenarios or a body."""
    scripts = game_cls.SCENARIOS
    if "idle_body" not in scripts or "nobody" not in scripts:
        return None
    n = round(IDLE_WINDOW / TICK)
    idle = list(itertools.islice(scripts["idle_body"](), n))
    first = next((i for i, s in enumerate(idle) if s.bodies), None)
    if first is None:
        return None
    body, _ = run_headless(cfg, font, game_cls, idle, seed=seed)
    empty, _ = run_headless(cfg, font, game_cls, itertools.islice(scripts["nobody"](), n), seed=seed)
    for i in range(first, min(len(body), len(empty))):
        if int((body[i] != empty[i]).any(axis=2).sum()) >= RESPONSE_PX:
            return idle[i].t - idle[first].t
    return IDLE_WINDOW


def _held(records: list[Sensed], i: int, j: int) -> Sensed:
    """Record i's input at record j's times."""
    r = records[j]
    return dataclasses.replace(records[i], t=r.t, camera_t=r.camera_t, camera_fresh=r.camera_fresh,
                               camera_seq=r.camera_seq)


def _response(cfg, font, game_cls, records, seed, pushed, probes: list[int]) -> float | None:
    """The median over probes of the ticks after the probe until the pushed frames of a run that holds every later
    record at the probe's input differ from pushed in RESPONSE_PX pixels or more; 5 * LATENCY_TICKS when never."""
    if not probes:
        return None
    horizon = 5 * LATENCY_TICKS
    ticks = []
    for i in probes:
        held = records[:i + 1] + [_held(records, i, j) for j in range(i + 1, i + 1 + horizon)]
        frames, _ = run_headless(cfg, font, game_cls, held, seed=seed)
        if not all(np.array_equal(a, b) for a, b in zip(frames[:i + 1], pushed[:i + 1])):
            raise RuntimeError(f"{game_cls.info.name} does not repeat under seed {seed}: its frames before tick "
                               f"{i} differ between two runs of the same records")
        ticks.append(next((k for k in range(1, horizon + 1)
                           if int((frames[i + k] != pushed[i + k]).any(axis=2).sum()) >= RESPONSE_PX), horizon))
    return float(statistics.median(ticks))


def _probes(inputs: list, current: list[bool], horizon: int) -> list[int]:
    """Up to PROBES ticks, evenly spread, where the input exists and moves on the next record, the game running."""
    last = len(inputs) - 1 - horizon
    moves = [i for i in range(last + 1) if current[i] and inputs[i] is not None and inputs[i + 1] is not None
             and inputs[i + 1] != inputs[i]]
    if len(moves) <= PROBES:
        return moves
    return sorted({moves[round(k * (len(moves) - 1) / (PROBES - 1))] for k in range(PROBES)})


def _canonical(cfg, font, game_cls, seed, own) -> dict[str, float | None]:
    name = game_cls.info.name
    script = game_cls.SCENARIOS.get("canonical")
    if script is None:
        raise ValueError(f"{name} has no canonical scenario: SCENARIOS needs 'canonical' to be measured")
    records = list(itertools.islice(script(), round(FEEL_SECONDS / TICK)))
    players: list[Body | None] = []

    def feed(runner):
        for sensed in records:
            yield sensed
            players.append(runner.player)

    pushed, runner = run_headless(cfg, font, game_cls, feed, seed=seed, trace=True, raw=True)
    raw, trace = runner.raw_frames, runner.trace
    current = [s.get("game") == name for s in trace]
    ctl = control(game_cls, own)
    read: Callable = _cursor if ctl is None else INPUTS[ctl[0]]
    inputs = [None if p is None else read(p) for p in players]
    out: dict[str, float | None] = {}
    out["response_ticks"] = _response(cfg, font, game_cls, records, seed, pushed,
                                      _probes(inputs, current, 5 * LATENCY_TICKS))
    out["fidelity"] = out["range"] = None
    if ctl is not None:
        _, key, axis = ctl
        pairs = [(v, xy[axis]) for v, s, on in zip(inputs, trace, current)
                 if on and v is not None and (xy := _xy(s, key)) is not None]
        if pairs:
            a, b = zip(*pairs)
            out["fidelity"] = _pearson(list(a), list(b))
            out["range"] = (max(b) - min(b)) / ((cfg.width if axis == 0 else cfg.height) - 1)
    lit_raw = [_lit(f) for f in raw]
    lit_pixels = sum(int(m.sum()) for m in lit_raw)
    dim_pixels = sum(int((m & (f < DIM_LEVEL).all(axis=2)).sum()) for m, f in zip(lit_raw, raw))
    out["lit_fraction"] = float(np.mean([_lit(f).mean() for f in pushed])) if pushed else 0.0
    out["dim_fraction"] = dim_pixels / lit_pixels if lit_pixels else 0.0
    out["liveliness"] = (float(np.mean([(a != b).any(axis=2).mean() for a, b in zip(raw, raw[1:])]))
                         if len(raw) > 1 else 0.0)
    out["flash_area_raw"] = float(flash.flash_area(raw, cfg.gamma, cfg.fps))
    out["square_flashes"] = float(flash.square_flashes(pushed, cfg.gamma, cfg.fps))
    out |= _score(font, pushed, trace, current, cfg.gamma)
    out["idle_hint_seconds"] = _idle_hint(cfg, font, game_cls, seed)
    return out


def _bot_plays(game_cls, layout: str, runs: list[int], font) -> dict[str, float | None]:
    factories, won = bots.for_game(game_cls)
    rate = lambda plays: statistics.fmean(p.won for p in plays)
    good = [bots.play(game_cls, factories["good"](), s, layout, won=won, font=font) for s in runs]
    lazy = [bots.play(game_cls, factories["lazy"](), s, layout, won=won, font=font) for s in runs]
    none = [bots.play(game_cls, bots.Nobody(), s, layout, won=won, font=font) for s in runs]
    finished = [p.seconds for p in good if p.done]
    phases = set(game_cls.PHASES)
    seen = set().union(*(p.phases for p in good)) & phases
    return {"win_good": rate(good), "win_lazy": rate(lazy), "win_none": rate(none),
            "round_seconds": float(statistics.median(finished)) if finished else None,
            "phases_reached": len(seen) / len(phases) if phases else None}


def measure(game_cls, layout: str, seeds: int | Sequence[int] = FEEL_SEEDS, font=None, *,
            own: Path | None = None) -> dict[str, float | None]:
    """Every feel metric of game_cls at layout ("WxH"), None where it cannot be measured.

    Canonical is SCENARIOS["canonical"]'s first FEEL_SECONDS, run once through run_headless under the first seed;
    raw frames are the game's own drawing, pushed what the wall shows. response_ticks: at PROBES canonical ticks
    where control()'s input (else the player's cursor) moves on the next record, a second run holds every later
    record at that tick's input (times advance); the ticks after the probe until the pushed frames differ in
    RESPONSE_PX pixels or more, the median (1 is the next tick); 5 * LATENCY_TICKS when never. fidelity: Pearson
    r of control()'s input against its *_xy axis over the canonical ticks where both exist; range: that axis's
    span over the wall's extent - 1 (both None without [fidelity]). lit_fraction: pushed, the mean share of
    non-black pixels; dim_fraction: raw, the share of lit pixels with every channel under DIM_LEVEL;
    liveliness: raw, the mean share changing per tick; flash_area_raw (raw) and square_flashes (pushed) as
    arcade/flash.py counts them. score_visible and score_legible: pushed, as _score() says (the score read from
    debug_state()["score"]); idle_hint_seconds as _idle_hint() says, under the first seed. From bots.play over seeds (n: bots.seeds(game_cls, layout, n)): win_good,
    win_lazy, win_none (Nobody); round_seconds, the median length of the good plays that ended done();
    phases_reached, the share of PHASES seen over the good plays. own is the game's feel file (control()).
    """
    runs = bots.seeds(game_cls, layout, seeds) if isinstance(seeds, int) else list(seeds)
    if not runs:
        raise ValueError("measure needs at least one seed")
    w, h = (int(v) for v in layout.split("x"))
    cfg = ArcadeConfig(w, h, backend="fake", camera="none", audio="none")
    font = font if font is not None else bots._font(bots.ROOT / cfg.font_path)
    return _canonical(cfg, font, game_cls, runs[0], own) | _bot_plays(game_cls, layout, runs, font)


def _g(v: float) -> str:
    return f"{v:.4g}"


def judge(metrics: dict, budgets: dict[str, Budget]) -> list[str]:
    """One line per budget missed, in budget order: "win_lazy 0.85 > max 0.7", "fidelity 0.5 < min 0.8", and for
    a metric that is None or absent "round_seconds None misses min 20, max 120"."""
    out = []
    for metric, b in budgets.items():
        v = metrics.get(metric)
        if v is None:
            bounds = ", ".join(f"{k} {_g(x)}" for k, x in (("min", b.min), ("max", b.max)) if x is not None)
            out.append(f"{metric} None misses {bounds}")
        elif b.min is not None and v < b.min:
            out.append(f"{metric} {_g(v)} < min {_g(b.min)}")
        elif b.max is not None and v > b.max:
            out.append(f"{metric} {_g(v)} > max {_g(b.max)}")
    return out


def report(game_cls, layout: str, seeds: int | Sequence[int] = FEEL_SEEDS, font=None, *,
           own: Path | None = None) -> dict:
    """{"metrics": measure(...), "budgets": {metric: {"min", "max", "reason"}}, "failures": judge(...)}: plain
    floats, None and str, so json.dumps takes it."""
    metrics = measure(game_cls, layout, seeds, font, own=own)
    table = budgets(game_cls, layout, own=own)
    return {"metrics": metrics,
            "budgets": {m: {"min": b.min, "max": b.max, "reason": b.reason} for m, b in table.items()},
            "failures": judge(metrics, table)}
