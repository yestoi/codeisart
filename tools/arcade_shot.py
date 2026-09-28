"""Contact sheets of a game (or the lobby and a game) run headless through the real runner, for the operator.

    python -m tools.arcade_shot pong --lobby small --scenario duel --every 30 --cols 6 --out sheets/pong
    python -m tools.arcade_shot pong --lobby small --scenario duel --raw-vs-pushed --out sheets/strobe

Writes OUT.png (one cell per --every ticks, captioned tick, time, game and phase, under a title band with the
git sha) and OUT-distance.png (the same cells as the eye sees them from 5 m). --raw-vs-pushed also writes
OUT-raw-vs-pushed.png (raw | pushed pairs), prints the luminance timelines and the flash numbers, and exits 1
when what reached the wall flashes over the budget. A game or lobby is a name ("pong"), or "module:Attr".
"""
from __future__ import annotations

import argparse
import importlib
import itertools
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
from PIL import Image, ImageDraw
from PIL.PngImagePlugin import PngInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:          # run as a script, the repository is not on the path
    sys.path.insert(0, str(ROOT))

from arcade.config import ArcadeConfig            # noqa: E402
from arcade.flash import BUDGET, SMALL_AREA, concurrent_area, flash_area, square_flashes    # noqa: E402
from arcade.headless import run_headless            # noqa: E402
from arcade.look import render                      # noqa: E402
from arcade.sensed import Sensed                    # noqa: E402
from arcade.sources.actors import TICK, Person, scene      # noqa: E402
from show.font import Font                          # noqa: E402

TITLE_H, CAP_H, PAD = 14, 10, 4
DEFAULT_TICKS = 300
BACKGROUND, INK, TITLE_INK = (40, 40, 60), (200, 200, 200), (255, 255, 0)


def _by_path(spec: str):
    module, _, attr = spec.partition(":")
    return getattr(importlib.import_module(module), attr)


def resolve_game(spec: str) -> type:
    """A game by name ("pong") or by "module:Attr"."""
    if ":" in spec:
        return _by_path(spec)
    from arcade.games import get_game
    return get_game(spec)


def resolve_lobby(spec: str) -> Callable[[list[type], ArcadeConfig], object] | None:
    """None for "none", the small lobby for "small", else "module:Attr"; called as f(games, cfg)."""
    if spec == "none":
        return None
    if spec == "small":
        from arcade.attract.lobby import Lobby
        return Lobby
    return _by_path(spec)


def resolve_scenario(spec: str | None, games: list[type], ticks: int | None) -> Iterable[Sensed]:
    """A scenario of the first game by name, or "module:attr" (a callable); None is one person standing
    in the middle for DEFAULT_TICKS. ticks, when given, cuts the run short."""
    if spec is None:
        sensed = scene(persons=[Person(0.5, id=1)], ticks=DEFAULT_TICKS)
    elif ":" in spec:
        sensed = _by_path(spec)()
    else:
        sensed = games[0].SCENARIOS[spec]()
    return sensed if ticks is None else itertools.islice(sensed, ticks)


def shoot(games, sensed, cfg, font, lobby=None, seed=0, strict=True):
    """Run headless with trace and raw frames: (pushed, raw, trace, runner)."""
    frames, runner = run_headless(cfg, font, games, sensed, seed=seed, strict=strict, trace=True, raw=True,
                                  lobby=None if lobby is None else lobby(games, cfg))
    return frames, runner.raw_frames, runner.trace, runner


def git_sha() -> str:
    """The short sha of the repository in the current directory, with "+dirty" when the tree has changes."""
    def git(*args):
        return subprocess.run(["git", *args], capture_output=True, text=True).stdout.strip()
    sha = git("rev-parse", "--short", "HEAD") or "unknown"
    return sha + ("+dirty" if git("status", "--porcelain") else "")


def save_png(image: Image.Image, path: Path, sha: str) -> None:
    info = PngInfo()
    info.add_text("git", sha)
    image.save(path, pnginfo=info)


def _caption(trace, i: int) -> str:
    state = trace[i] if i < len(trace) else {}
    return f"#{i} {i * TICK:.2f}s {state.get('game', '')} {state.get('phase', '')}".strip()


def contact_sheet(frames, trace, look: str, scale: int, every: int, cols: int, title: str,
                  gamma: float = 2.2) -> Image.Image:
    """Every `every`-th frame as a captioned cell, cols to a row, under a title band."""
    ticks = range(0, len(frames), every)
    h, w = frames[0].shape[:2]
    cw, ch = w * scale, h * scale
    rows = -(-len(ticks) // cols)
    sheet = Image.new("RGB", (PAD + cols * (cw + PAD), TITLE_H + rows * (ch + CAP_H + PAD)), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    draw.text((PAD, 1), title, fill=TITLE_INK)
    for k, i in enumerate(ticks):
        row, col = divmod(k, cols)
        x, y = PAD + col * (cw + PAD), TITLE_H + row * (ch + CAP_H + PAD)
        draw.text((x, y - 1), _caption(trace, i), fill=INK)
        cell = render(frames[i], look, scale, gamma, metres=5.0) if look == "distance" else render(frames[i], look, scale, gamma)
        sheet.paste(Image.fromarray(cell), (x, y + CAP_H))
    return sheet


def _biggest_change(raw) -> int:
    if len(raw) < 2:
        return 0
    steps = [np.abs(raw[i].astype(np.int16) - raw[i - 1]).sum() for i in range(1, len(raw))]
    return int(np.argmax(steps)) + 1


def raw_vs_pushed(raw, pushed, start: int, count: int = 40, scale: int = 2, title: str = "") -> Image.Image:
    """count ticks from start, each a raw | pushed pair, four pairs to a row."""
    cols = 4
    n = max(0, min(count, len(raw) - start))
    h, w = raw[0].shape[:2]
    cw, ch = w * scale + PAD, h * scale + CAP_H
    rows = -(-n // cols)
    sheet = Image.new("RGB", (PAD + cols * (2 * cw + PAD), TITLE_H + rows * (ch + PAD)), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    draw.text((PAD, 1), title, fill=TITLE_INK)
    for k in range(n):
        i = start + k
        row, col = divmod(k, cols)
        x, y = PAD + col * (2 * cw + PAD), TITLE_H + row * (ch + PAD)
        draw.text((x, y - 1), f"t{i} raw", fill=INK)
        draw.text((x + cw, y - 1), "pushed", fill=(120, 220, 120))
        for j, frame in enumerate((raw[i], pushed[i])):
            sheet.paste(Image.fromarray(render(frame, "plain", scale)), (x + j * cw, y + CAP_H))
    return sheet


def timeline(frames) -> str:
    return "".join("#" if f.mean() > 128 else ("+" if f.mean() > 8 else ".") for f in frames)


def _size(text: str) -> tuple[int, int]:
    w, _, h = text.partition("x")
    return int(w), int(h)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.arcade_shot", description=__doc__.split("\n")[0])
    ap.add_argument("games", nargs="+", metavar="GAME")
    ap.add_argument("--out", required=True, metavar="STEM")
    ap.add_argument("--lobby", default="none")
    ap.add_argument("--size", default="128x32")
    ap.add_argument("--scenario")
    ap.add_argument("--ticks", type=int)
    ap.add_argument("--every", type=int, default=15)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--look", default="plain", choices=["plain", "led"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-strict", action="store_true")
    ap.add_argument("--raw-vs-pushed", action="store_true")
    ap.add_argument("--from", dest="start", type=int)
    args = ap.parse_args(argv)

    width, height = _size(args.size)
    cfg = ArcadeConfig(width=width, height=height, backend="fake", camera="none", audio="none")
    font = Font.load(cfg.font_path if cfg.font_path.is_absolute() else ROOT / cfg.font_path)
    games = [resolve_game(g) for g in args.games]
    lobby = resolve_lobby(args.lobby)
    sensed = resolve_scenario(args.scenario, games, args.ticks)
    frames, raw, trace, runner = shoot(games, sensed, cfg, font, lobby=lobby, seed=args.seed,
                                       strict=not args.no_strict)
    sha = git_sha()
    title = (f"{sha} {args.size} seed {args.seed} games {','.join(args.games)} lobby {args.lobby} "
             f"scenario {args.scenario or 'standing'}")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    save_png(contact_sheet(frames, trace, args.look, args.scale, args.every, args.cols, title, cfg.gamma),
             out.with_name(out.name + ".png"), sha)
    save_png(contact_sheet(frames, trace, "distance", max(4, args.scale), args.every, args.cols,
                           title + " (5 m)", cfg.gamma), out.with_name(out.name + "-distance.png"), sha)
    if not args.raw_vs_pushed:
        return 0

    start = args.start if args.start is not None else max(0, min(_biggest_change(raw) - 20, len(raw) - 40))
    save_png(raw_vs_pushed(raw, frames, start, 40, args.scale, title + f" raw | pushed from t{start}"),
             out.with_name(out.name + "-raw-vs-pushed.png"), sha)
    g = cfg.gamma
    concurrent, flashes = concurrent_area(frames, g), square_flashes(frames, g)
    print("HEAD", sha)
    print("raw    ", timeline(raw))
    print("pushed ", timeline(frames))
    print("held", runner.governor.held_ticks, "of", len(frames))
    print(f"flash_area raw {flash_area(raw, g):.3f} pushed {flash_area(frames, g):.3f}")
    print(f"concurrent_area(pushed) {concurrent:.3f} (limit {SMALL_AREA})")
    print(f"square_flashes(pushed) {flashes} BUDGET {BUDGET}")
    return 1 if flashes > BUDGET or concurrent >= SMALL_AREA else 0


if __name__ == "__main__":
    sys.exit(main())
