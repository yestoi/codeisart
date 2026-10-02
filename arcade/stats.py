"""`stats`: a read-only summary of the sessions log, one line a game (it21 S).

Reads data_dir/sessions.jsonl (written by arcade.scores.SessionLog) and writes nothing.
"""
from __future__ import annotations

import json
import math
import statistics
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from arcade.config import load_config
from arcade.games import MENU_ORDER


@dataclass(frozen=True)
class GameStats:
    sessions: int
    median_seconds: float | None
    reasons: dict[str, int]


def summarise(path: Path) -> tuple[dict[str, GameStats], int]:
    """Per game stats and the count of bad lines (skipped). A null or non-finite duration is not in the median."""
    durations: dict[str, list[float]] = {}
    reasons: dict[str, Counter] = {}
    bad = 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                bad += 1
                continue
            game = rec.get("game") if isinstance(rec, dict) else None
            reason = rec.get("reason") if isinstance(rec, dict) else None
            if not isinstance(game, str) or not isinstance(reason, str):
                bad += 1
                continue
            d = rec.get("duration")
            durations.setdefault(game, [])
            reasons.setdefault(game, Counter())[reason] += 1
            if isinstance(d, (int, float)) and not isinstance(d, bool) and math.isfinite(d):
                durations[game].append(float(d))
    out = {}
    for game, counter in reasons.items():
        ds = durations[game]
        out[game] = GameStats(sum(counter.values()), statistics.median(ds) if ds else None, dict(sorted(counter.items())))
    return out, bad


def table(stats: dict[str, GameStats]) -> str:
    """One line a game: MENU_ORDER first, then the rest sorted."""
    order = [g for g in MENU_ORDER if g in stats] + sorted(g for g in stats if g not in MENU_ORDER)
    lines = []
    for g in order:
        s = stats[g]
        median = "-" if s.median_seconds is None else f"{s.median_seconds:.1f}s"
        why = " ".join(f"{k}={v}" for k, v in s.reasons.items())
        lines.append(f"{g:<12} {s.sessions:>5} sessions  median {median:>8}  {why}")
    return "\n".join(lines)


def main(args) -> int:
    path = getattr(args, "sessions", None)
    if path is None:
        cfg = load_config(getattr(args, "config", None) or "arcade.toml")
        path = Path(cfg.data_dir) / "sessions.jsonl"
    path = Path(path)
    if not path.is_file():
        print("no sessions")
        return 0
    result, bad = summarise(path)
    if not result:
        print("no sessions")
    else:
        print(table(result))
    if bad:
        print(f"{bad} bad line(s) skipped")
    return 0
