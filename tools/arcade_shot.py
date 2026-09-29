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
from arcade.runner import LOBBY                     # noqa: E402
from arcade.sensed import Sensed                    # noqa: E402
from arcade.sources.actors import TICK, Person, scene      # noqa: E402
from show.font import Font                          # noqa: E402

TITLE_H, CAP_H, PAD = 14, 10, 4
MAX_WIDTH = 1536
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


def caption_keys_of(games) -> dict[str, tuple[str, ...]]:
    return {g.info.name: tuple(getattr(g, "CAPTION_KEYS", ())) for g in games}


def _caption(trace, i: int, caption_keys: dict[str, tuple[str, ...]] | None = None) -> str:
    """"#30 1.00s pong ..." then the game's CAPTION_KEYS values from the trace (the lobby's mode in the lobby).
    Without caption_keys, the phase, as before."""
    state = trace[i] if i < len(trace) else {}
    game = state.get("game", "")
    if caption_keys is None:
        extra = [state.get("phase", "")]
    elif game == LOBBY:
        extra = [state.get("mode", "")]
    else:
        extra = [state.get(k, "") for k in caption_keys.get(game, ())]
    return " ".join(str(x) for x in [f"#{i} {i * TICK:.2f}s {game}", *extra] if x != "").strip()


def fit_width(unit: int, pad: int, edge: int, cols: int, scale: int, cap: int = MAX_WIDTH) -> tuple[int, int]:
    """(cols, scale) so a sheet edge + cols * (unit * scale + pad) is at most cap: fewer columns first, then a
    smaller scale (never below 1)."""
    while True:
        fit = (cap - edge) // (unit * scale + pad)
        if fit >= 1 or scale <= 1:
            return max(1, min(cols, fit)), scale
        scale -= 1


def contact_sheet(frames, trace, look: str, scale: int, every: int, cols: int, title: str,
                  gamma: float = 2.2, *, caption_keys=None) -> Image.Image:
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
        draw.text((x, y - 1), _caption(trace, i, caption_keys), fill=INK)
        cell = render(frames[i], look, scale, gamma, metres=5.0) if look == "distance" else render(frames[i], look, scale, gamma)
        sheet.paste(Image.fromarray(cell), (x, y + CAP_H))
    return sheet


def _biggest_change(raw) -> int:
    if len(raw) < 2:
        return 0
    steps = [np.abs(raw[i].astype(np.int16) - raw[i - 1]).sum() for i in range(1, len(raw))]
    return int(np.argmax(steps)) + 1


def raw_vs_pushed(raw, pushed, start: int, count: int = 40, scale: int = 2, title: str = "", *,
                  cols: int = 4) -> Image.Image:
    """count ticks from start, each a raw | pushed pair, cols (four) pairs to a row."""
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
    ap.add_argument("--size", default="128x64")
    ap.add_argument("--scenario")
    ap.add_argument("--ticks", type=int)
    ap.add_argument("--every", type=int, default=15)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--look", default="plain", choices=["plain", "led", "both"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-strict", action="store_true")
    ap.add_argument("--raw-vs-pushed", action="store_true")
    ap.add_argument("--allow-black", action="store_true")
    ap.add_argument("--flash-report", action="store_true")
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
    nonblack = sum(1 for f in frames if f[:-1].any())      # the bottom row holds the player markers (fx)
    print("frames", len(frames), "non-black", nonblack)
    print("state", runner.state())
    if nonblack == 0 and not args.allow_black:
        needs = sorted({n for g in games for n in g.info.needs})
        print(f"refused: every pushed frame is black (games need {', '.join(needs) or 'nothing'}); "
              f"give the scenario what they need, or pass --allow-black", file=sys.stderr)
        return 2
    base = (f"{sha} {'dirty' if sha.endswith('+dirty') else 'clean'} games {','.join(args.games)} "
            f"size {args.size} seed {args.seed} lobby {args.lobby} scenario {args.scenario or 'standing'}")
    keys = caption_keys_of(games)
    h, w = frames[0].shape[:2]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    def sheet(look: str, scale: int, label: str) -> Image.Image:
        cols, scale = fit_width(w, PAD, PAD, args.cols, scale)
        return contact_sheet(frames, trace, look, scale, args.every, cols, f"{base} look {label}", cfg.gamma,
                             caption_keys=keys)

    looks = ["plain", "led"] if args.look == "both" else [args.look]
    for look in looks:
        name = f"{out.name}-{look}.png" if args.look == "both" else out.name + ".png"
        save_png(sheet(look, args.scale, look), out.with_name(name), sha)
    save_png(sheet("distance", max(4, args.scale), "distance (5 m)"), out.with_name(out.name + "-distance.png"), sha)
    if args.flash_report:
        g = cfg.gamma
        print(f"flash_area raw {flash_area(raw, g):.3f} pushed {flash_area(frames, g):.3f}")
        print(f"mean_level {float(np.mean([f.mean() for f in frames])):.2f} of 255")
    if not args.raw_vs_pushed:
        return 0

    start = args.start if args.start is not None else max(0, min(_biggest_change(raw) - 20, len(raw) - 40))
    pcols, pscale = fit_width(2 * w, 3 * PAD, PAD, 4, args.scale)
    save_png(raw_vs_pushed(raw, frames, start, 40, pscale, base + f" raw | pushed from t{start}", cols=pcols),
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
