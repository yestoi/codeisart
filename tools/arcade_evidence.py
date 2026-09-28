"""The per-iteration evidence package (spec 9.6): images, a GIF, a trace, a timeline and the feel table per game.

    python -m tools.arcade_evidence --iteration N [--games changed|NAME[,NAME]] [--since REV] [--out DIR]

Writes games.md (never README.md, which is the operator's), feel.json and, per game and declared layout,
<game>-<layout>-plain.png, -led.png, -distance.png, -canonical.gif, -trace.jsonl and -timeline.txt. Every file
carries the sha taken once at the start; files under --out never dirty it.
"""
from __future__ import annotations

import argparse
import dataclasses
import itertools
import json
import re
import subprocess
import sys
import zlib
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:          # run as a script, the repository is not on the path
    sys.path.insert(0, str(ROOT))

from arcade.config import ArcadeConfig            # noqa: E402
from arcade.look import render                      # noqa: E402
from arcade.sources.actors import TICK              # noqa: E402
from show.font import Font                          # noqa: E402
from tools import arcade_shot as shot               # noqa: E402

EMPTY = 2.0            # seconds of an empty wall at the start of every game's canonical scenario
GIF_SECONDS = 6.0
GIF_BYTES = 300_000
GIF_EVERY = 3          # ticks per GIF frame
GIF_MS = 100
SHEET_SECONDS = 30.0
LEAD_SECONDS = 1.0     # the GIF starts this long before the launch
EVIDENCE_DIR = "docs/superpowers/workflow/evidence/"
ENGINE_FILES = ("arcade/game.py", "arcade/runner.py", "arcade/headless.py")
SHEET_EVERY, SHEET_COLS = 45, 5
TIMELINE_LINES = 10

_GAME_FILE = re.compile(r"^arcade/games/([a-z0-9]+?)(?:_bots|_feel)?\.(?:py|toml)$")
_TEST_FILE = re.compile(r"^tests/arcade/test_([a-z0-9]+)\.py$")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout


def changed_games(since: str | None) -> list[str]:
    """Names of the games with one of their four files in `git diff --name-only since..HEAD`, or every game
    when game.py, runner.py or headless.py changed. since defaults to the last commit touching the evidence
    directory (with none, every game)."""
    from arcade.games import MENU_ORDER, all_games

    everyone = [g.info.name for g in all_games()]
    if since is None:
        since = _git("log", "-1", "--format=%H", "--", EVIDENCE_DIR).strip()
        if not since:
            return everyone
    files = _git("diff", "--name-only", f"{since}..HEAD").split()
    if any(f in ENGINE_FILES for f in files):
        return everyone
    names = set()
    for f in files:
        m = _GAME_FILE.match(f) or _TEST_FILE.match(f)
        if m:
            names.add(m.group(1))
    return [n for n in MENU_ORDER if n in names]


def clean_sha(out: Path, allow_dirty: bool) -> str:
    """The short sha of HEAD, once at the start. A dirty tree (files under out ignored) exits 2 naming the
    paths, or with allow_dirty gives sha + "+dirty"."""
    sha = _git("rev-parse", "--short", "HEAD").strip() or "unknown"
    top = Path(_git("rev-parse", "--show-toplevel").strip() or ".").resolve()
    skip = Path(out).resolve()
    entries = _git("status", "--porcelain", "-z", "--untracked-files=all").split("\0")
    dirty, i = [], 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 4:
            continue
        if entry[0] in "RC":
            i += 1                                  # the original name follows a rename
        path = (top / entry[3:]).resolve()
        if path != skip and skip not in path.parents:
            dirty.append(entry[3:])
    if not dirty:
        return sha
    if allow_dirty:
        return sha + "+dirty"
    print("the working tree is dirty; commit or pass --allow-dirty:\n  " + "\n  ".join(dirty), file=sys.stderr)
    raise SystemExit(2)


def gif(frames, path: Path, sha: str, scale: int = 2) -> int:
    """frames (pushed, uint8 h x w x 3) as a plain GIF: every GIF_EVERY-th at GIF_MS, comment = sha; scale 1
    when over GIF_BYTES; raises ValueError when still over. Returns the size in bytes."""
    picked = list(frames)[::GIF_EVERY][:int(GIF_SECONDS * 1000 / GIF_MS)]
    size = 0
    for s in dict.fromkeys((scale, 1)):
        images = [Image.fromarray(render(f, "plain", s)) for f in picked]
        images[0].save(path, save_all=True, append_images=images[1:], duration=GIF_MS, loop=0,
                       comment=sha.encode())
        size = path.stat().st_size
        if size <= GIF_BYTES:
            return size
    path.unlink()
    raise ValueError(f"{path.name}: {size} bytes at scale 1, over the {GIF_BYTES} byte cap")


def timeline_lines(trace) -> str:
    """One `t game/phase` line per change of (game, phase), thinned evenly to at most TIMELINE_LINES."""
    rows, last = [], None
    for state in trace:
        key = (state.get("game"), state.get("phase", state.get("mode")))
        if key != last:
            last = key
            phase = "" if key[1] is None else f"/{key[1]}"
            rows.append(f"{state.get('t', 0):.2f} {key[0]}{phase}")
    if len(rows) > TIMELINE_LINES:
        rows = [rows[round(i * (len(rows) - 1) / (TIMELINE_LINES - 1))] for i in range(TIMELINE_LINES)]
    return "\n".join(rows) + "\n"


def _json_default(o):
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    if dataclasses.is_dataclass(o) and not isinstance(o, type):
        return dataclasses.asdict(o)
    if hasattr(o, "item"):
        return o.item()
    return str(o)


def _budget(b) -> tuple[float | None, float | None]:
    if b is None:
        return None, None
    if isinstance(b, dict):
        return b.get("min"), b.get("max")
    return getattr(b, "min", None), getattr(b, "max", None)


def _fmt(v) -> str:
    return "-" if v is None else (str(round(v, 4)) if isinstance(v, float) else str(v))


def _feel_table(rep: dict) -> list[str]:
    lines = ["| metric | value | budget | ok |", "| --- | --- | --- | --- |"]
    for metric, value in rep.get("metrics", {}).items():
        lo, hi = _budget(rep.get("budgets", {}).get(metric))
        budget = "-" if lo is None and hi is None else f"{_fmt(lo)} to {_fmt(hi)}"
        ok = value is not None and (lo is None or value >= lo) and (hi is None or value <= hi)
        lines.append(f"| {metric} | {_fmt(value)} | {budget} | {'yes' if ok else 'no'} |")
    for failure in rep.get("failures", []):
        lines.append(f"\nFAIL: {failure}")
    return lines


def _launch_tick(trace, name: str) -> int:
    return next((i for i, s in enumerate(trace) if s.get("game") == name), 0)


def package(games: list[type], out: Path, sha: str, seeds, report=None, font=None) -> list[Path]:
    """Write the evidence of games into out; returns the files written."""
    if report is None:
        from arcade.feel import report
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    if font is None:
        cfg0 = ArcadeConfig()
        font = Font.load(cfg0.font_path if cfg0.font_path.is_absolute() else ROOT / cfg0.font_path)
    lobby = shot.resolve_lobby("small")
    written: list[Path] = []
    feel: dict = {}
    md = [f"# Evidence {sha}", ""]

    def keep(p: Path) -> Path:
        written.append(p)
        return p

    for game in games:
        name = game.info.name
        feel[name] = {}
        md += [f"## {name}", ""]
        for layout in sorted(game.info.layouts):
            w, h = shot._size(layout)
            cfg = ArcadeConfig(width=w, height=h, backend="fake", camera="none", audio="none")
            ticks = int(SHEET_SECONDS / TICK)
            sensed = itertools.islice(game.SCENARIOS["canonical"](), ticks)
            frames, _, trace, _ = shot.shoot([game], sensed, cfg, font, lobby=lobby, seed=0)
            stem = f"{name}-{layout}"
            title = f"{sha} {layout} {name} canonical"
            images = []
            for look, suffix, scale in (("plain", "plain", 2), ("led", "led", 2), ("distance", "distance", 4)):
                sheet = shot.contact_sheet(frames, trace, look, scale, SHEET_EVERY, SHEET_COLS, title, cfg.gamma)
                shot.save_png(sheet, keep(out / f"{stem}-{suffix}.png"), sha)
                images.append(f"{stem}-{suffix}.png")
            start = max(0, _launch_tick(trace, name) - round(LEAD_SECONDS / TICK))
            gif(frames[start:start + round(GIF_SECONDS / TICK)], keep(out / f"{stem}-canonical.gif"), sha)
            images.append(f"{stem}-canonical.gif")
            keep(out / f"{stem}-trace.jsonl").write_text(
                "".join(json.dumps(s, default=_json_default) + "\n" for s in trace))
            keep(out / f"{stem}-timeline.txt").write_text(timeline_lines(trace))
            rep = report(game, layout, seeds, font=font)
            feel[name][layout] = rep
            md += [f"### {layout}", "", *_feel_table(rep), ""]
            md += [f"![{img}]({img})" for img in images] + [""]
    keep(out / "feel.json").write_text(json.dumps(feel, indent=1, default=_json_default) + "\n")
    keep(out / "games.md").write_text("\n".join(md) + "\n")
    return written


def _seeds(n: int) -> list[int]:
    try:
        from arcade import feel
        known = list(getattr(feel, "FEEL_SEEDS", ()))
    except ImportError:                    # feel.py not there yet: crc32 seeds only
        known = []
    return known[:n] + [zlib.crc32(f"evidence{i}".encode()) for i in range(len(known), n)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.arcade_evidence", description=__doc__.split("\n")[0])
    ap.add_argument("--iteration", type=int, required=True, metavar="N")
    ap.add_argument("--games", default="changed", metavar="changed|NAME[,NAME]")
    ap.add_argument("--since", metavar="REV", help="default: the last commit touching the evidence directory")
    ap.add_argument("--out", metavar="DIR", help="default: docs/superpowers/workflow/evidence/itNN")
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--allow-dirty", action="store_true")
    args = ap.parse_args(argv)

    out = Path(args.out or f"{EVIDENCE_DIR}it{args.iteration:02d}")
    sha = clean_sha(out, args.allow_dirty)
    names = changed_games(args.since) if args.games == "changed" else [n for n in args.games.split(",") if n]
    if not names:
        print("no game changed since", args.since or "the last evidence commit")
        return 0
    from arcade.games import get_game
    games = [get_game(n) for n in names]
    files = package(games, out, sha, _seeds(args.seeds))
    print(f"{sha}: {len(files)} files in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
