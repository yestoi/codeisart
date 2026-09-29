"""Contact sheets of the show's terminal on the wall, for the operator.

    python -m tools.show_shot --script strip --look both --out sheets/strip
    python -m tools.show_shot --command "seq 1 60" --seconds 2 --every-ms 250 --look both --out sheets/seq
    python -m tools.show_shot --script strip --crop 0,0,128,64 --look led --out sheets/prototype
    python -m tools.show_shot --config show.poc.toml --command "./donut" --look led --out sheets/poc-donut
    python -m tools.show_shot --entry entries/hello --look both --out sheets/hello
    python -m tools.show_shot --entry entries/hello --capture-first --build "false" --out sheets/fallback
    python -m tools.show_shot --attract entries --look both --out sheets/attract

Scripts: strip, edges, fullscreen, cc. --entry DIR plays an entry through the show's pipeline (in a temporary
copy, real time; --capture-first records the fallback with the entry's own build, then --build replaces it) and
--attract DIR scrolls the entries' sources; both keep --seconds (default 60 and 10) and --every-ms. Writes OUT.png (or OUT-plain.png and OUT-led.png with --look both) and
OUT-distance.png (10 m, the middle of spec 1's 15 to 40 feet), each stamped with the git sha. Exits 1 and writes
nothing when every frame's program rows are black, unless --allow-black.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:          # run as a script, the repository is not on the path
    sys.path.insert(0, str(ROOT))

from arcade.look import render                                                    # noqa: E402
from show.attract import Attract                                                  # noqa: E402
from show.config import Config, load_config                                       # noqa: E402
from show.entries import Entry, load_entries, load_entry                          # noqa: E402
from show.font import CELL_H, CELL_W, Font                                              # noqa: E402
from show.pipeline import EntryPlayer, Phase                                      # noqa: E402
from show.renderer import Renderer                                                # noqa: E402
from show.terminal import Terminal                                                # noqa: E402
from tools.arcade_shot import BACKGROUND, CAP_H, INK, PAD, TITLE_H, TITLE_INK, fit_width, git_sha, save_png  # noqa: E402

ATTRACT_STRIP = "PRESS A BUTTON ON ANY PORTRAIT"
PLAY_STRIP = "NOW: hello by Trey, 2026, Not A.I. | NEXT: -"       # a sample until D3's strip() (Q52)
SHOW_MAX_WIDTH = 2080                                             # one 512 px frame at the led look's scale 4
DISTANCE_METRES = 10.0
DISTANCE_MIN_SCALE = 4

C_SOURCE = """#include <stdio.h>
int main(void) {
    int unused;
    printf("result %d\\n", 42);
    return 0;
}
"""


@dataclass(frozen=True)
class Step:
    label: str
    data: bytes = b""
    strip: str = ATTRACT_STRIP
    full_screen: bool = False
    strip_visible: bool = True
    cursor_on: bool = True


def _strip_script() -> list[Step]:
    def lines(a: int, b: int) -> bytes:
        return "".join(f"line {i:02d}: the quick brown fox jumps over the lazy dog\n" for i in range(a, b)).encode()
    return [
        Step("attract"),
        Step("play", lines(1, 10), strip=PLAY_STRIP),
        Step("play, scrolled", lines(10, 41), strip=PLAY_STRIP),
    ]


def _edges_script() -> list[Step]:
    return [
        Step("80 A, cursor at column 80", b"A" * 80),
        Step("block and CJK as ?", "\n█ 中文 ██".encode()),
        Step("bold and reverse", b"\n\x1b[1mbold\x1b[0m normal \x1b[7mreverse\x1b[0m \x1b[1;7mboth\x1b[0m"),
        Step("cursor hidden", b"\x1b[?25l"),
    ]


def _fullscreen_script() -> list[Step]:
    rows = "\n".join(f"ROW {i:02d} " + "#" * 20 for i in range(1, 25)).encode()
    return [
        Step("full screen, strip hidden", rows, full_screen=True, strip_visible=False),
        Step("full screen, strip shown", full_screen=True, strip_visible=True),
    ]


def _cc_script() -> list[Step]:
    cc = shutil.which("cc")
    if cc is None:
        raise RuntimeError("the cc script needs a C compiler (cc) on the path")
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "hello.c").write_text(C_SOURCE)

        def run(*cmd: str) -> bytes:
            return subprocess.run(cmd, cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout

        compiled = run(cc, "-Wall", "hello.c", "-o", "hello")
        ran = run(str(Path(tmp) / "hello"))
    return [
        Step("cat", b"$ cat hello.c\n" + C_SOURCE.encode(), strip=PLAY_STRIP),
        Step("cc -Wall", b"$ cc -Wall hello.c -o hello\n" + compiled, strip=PLAY_STRIP),
        Step("run", b"$ ./hello\n" + ran + b"$ ", strip=PLAY_STRIP),
    ]


SCRIPTS: dict[str, Callable[[], list[Step]]] = {
    "strip": _strip_script,
    "edges": _edges_script,
    "fullscreen": _fullscreen_script,
    "cc": _cc_script,
}


def _renderer(cfg: Config, font: Font) -> Renderer:
    return Renderer(font, cfg.width, cfg.height, cfg.columns, cfg.rows, cfg.phosphor_rgb, cfg.glow, cfg.view)


def frames_from_steps(steps: list[Step], cfg: Config, font: Font) -> list[tuple[str, np.ndarray]]:
    """One frame per step, the terminal's state carried from step to step; each frame is a copy."""
    renderer = _renderer(cfg, font)
    term = Terminal(cfg.columns, cfg.rows - 1)
    frames = []
    for step in steps:
        want = cfg.rows if step.full_screen else cfg.rows - 1
        if term.rows != want:
            term.reset(want)
        term.feed(step.data)
        frame = renderer.render(term.screen, step.cursor_on, step.strip, full_screen=step.full_screen,
                                strip_visible=step.strip_visible)
        frames.append((step.label, frame.copy()))
    return frames


def frames_from_command(command: str, cfg: Config, font: Font, seconds: float, every_ms: int,
                        cwd: Path) -> list[tuple[str, np.ndarray]]:
    """A real child in a terminal, pumped at cfg.fps; a frame every every_ms, and one at the end."""
    renderer = _renderer(cfg, font)
    term = Terminal(cfg.columns, cfg.rows - 1)
    frames: list[tuple[str, np.ndarray]] = []

    def keep(t: float) -> None:
        frame = renderer.render(term.screen, True, PLAY_STRIP)
        frames.append((f"{t:.2f}s", frame.copy()))

    try:
        term.run(["sh", "-c", command], cwd)
        start = time.monotonic()
        next_keep = 0.0
        while True:
            term.pump(cfg.pump_bytes, cfg.pump_ms)
            t = time.monotonic() - start
            done = term.finished_or_orphaned() or t >= seconds
            if t >= next_keep and not done:
                keep(t)
                next_keep += every_ms / 1000.0
            if done:
                break
            time.sleep(1.0 / cfg.fps)
        keep(time.monotonic() - start)
    finally:
        term.kill()
    return frames


def play_strip(entry: Entry) -> str:
    """The strip while an entry plays (Q52): nothing is queued in a sheet, so NEXT is a dash."""
    return f"NOW: {entry.title} by {entry.author}, {entry.year}, Not A.I. | NEXT: -"


def _play(entry: Entry, cfg: Config, font: Font, seconds: float, every_ms: int, keep_frames: bool):
    """One real-time play of an entry through the pipeline; the frames, the phases seen, the failure."""
    renderer = _renderer(cfg, font)
    term = Terminal(cfg.columns, cfg.rows - 1)
    player = EntryPlayer(entry, term, cfg)
    strip = play_strip(entry)
    frames: list[tuple[str, np.ndarray]] = []
    phases: list[tuple[str, float]] = []

    def keep(label_phase: str, t: float) -> None:
        if keep_frames:
            frame = renderer.render(term.screen, True, strip, full_screen=entry.full_screen)
            frames.append((f"{label_phase} {t:.1f}s", frame.copy()))

    try:
        start = time.monotonic()
        player.start(start)
        seen = None
        next_keep = 0.0
        while True:
            now = time.monotonic()
            player.tick(now)
            t = now - start
            phase = player.phase.value
            if phase != seen:
                phases.append((phase, t))
                seen = phase
                keep(phase, t)
                next_keep = t + every_ms / 1000.0
            elif t >= next_keep and not player.done:
                keep(phase, t)
                next_keep += every_ms / 1000.0
            if player.done or t >= seconds:
                break
            time.sleep(1.0 / cfg.fps)
        if not player.done:
            keep(player.phase.value, time.monotonic() - start)
    finally:
        player.stop()
        term.kill()
    return frames, phases, player.failure


def frames_from_entry(entry_dir: Path, cfg: Config, font: Font, seconds: float, every_ms: int,
                      build: str | None = None, capture_first: bool = False
                      ) -> tuple[list[tuple[str, np.ndarray]], list[tuple[str, float]], str | None]:
    """The entry played in a temporary copy (no build product in the checkout): the frames, the phases seen
    with their start times, the failure. --capture-first plays it once with its own build and capture on,
    keeping no frames; then `build` replaces the copy's build."""
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / Path(entry_dir).resolve().name
        shutil.copytree(entry_dir, copy)
        if capture_first:
            _play(load_entry(copy), replace(cfg, capture=True), font, seconds, every_ms, keep_frames=False)
        entry = load_entry(copy)
        if build is not None:
            entry = replace(entry, build=build)
        return _play(entry, cfg, font, seconds, every_ms, keep_frames=True)


def frames_from_attract(entries_dir: Path, cfg: Config, font: Font, seconds: float,
                        every_ms: int) -> list[tuple[str, np.ndarray]]:
    """Attract mode on the terminal at cfg.attract_lps, in real time; a frame every every_ms, and one at the end."""
    renderer = _renderer(cfg, font)
    term = Terminal(cfg.columns, cfg.rows - 1)
    attract = Attract(load_entries(entries_dir).values(), term, cfg.attract_lps, cfg.rows - 1)
    frames: list[tuple[str, np.ndarray]] = []

    def keep(t: float) -> None:
        frames.append((f"{t:.2f}s", renderer.render(term.screen, True, ATTRACT_STRIP).copy()))

    start = time.monotonic()
    attract.start(start)
    next_keep = 0.0
    while True:
        now = time.monotonic()
        attract.tick(now)
        t = now - start
        if t >= seconds:
            break
        if t >= next_keep:
            keep(t)
            next_keep += every_ms / 1000.0
        time.sleep(1.0 / cfg.fps)
    keep(time.monotonic() - start)
    return frames


def sheet(frames, look: str, scale: int, title: str, gamma: float, cols: int) -> Image.Image:
    """The frames as captioned cells, cols to a row, under a title band."""
    h, w = frames[0][1].shape[:2]
    cols, scale = fit_width(w, PAD, PAD, cols, scale, SHOW_MAX_WIDTH)
    cw, ch = w * scale, h * scale
    rows = -(-len(frames) // cols)
    image = Image.new("RGB", (PAD + cols * (cw + PAD), TITLE_H + rows * (ch + CAP_H + PAD)), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.text((PAD, 1), title, fill=TITLE_INK)
    for k, (label, frame) in enumerate(frames):
        row, col = divmod(k, cols)
        x, y = PAD + col * (cw + PAD), TITLE_H + row * (ch + CAP_H + PAD)
        draw.text((x, y - 1), label, fill=INK)
        cell = render(frame, look, scale, gamma, metres=DISTANCE_METRES) if look == "distance" \
            else render(frame, look, scale, gamma)
        image.paste(Image.fromarray(cell), (x, y + CAP_H))
    return image


def _crop(text: str) -> tuple[int, int, int, int]:
    x, y, w, h = (int(v) for v in text.split(","))
    return x, y, w, h


def _program_black(frames, cfg: Config) -> bool:
    """No frame's rows above the strip hold anything but the cursor's block on a blank cell.

    Counted by cells (the wall's text grid): a glyph is a partly lit cell, and more than one fully lit cell
    is more than the cursor. With glow on, the cursor's neighbours are partly lit: judge black by eye then.
    The ink view draws no cursor: any lit pixel above the strip's text row is a program."""
    if cfg.view == "ink":
        return all(frame[: cfg.height - CELL_H].max() == 0 for _, frame in frames)
    y0 = (cfg.height - cfg.rows * CELL_H) // 2
    x0 = (cfg.width - cfg.columns * CELL_W) // 2
    rows = cfg.rows - 1
    for _, frame in frames:
        region = frame[y0 : y0 + rows * CELL_H, x0 : x0 + cfg.columns * CELL_W].max(axis=2) > 0
        cells = region.reshape(rows, CELL_H, cfg.columns, CELL_W).sum(axis=(1, 3))
        if ((cells > 0) & (cells < CELL_H * CELL_W)).any() or (cells == CELL_H * CELL_W).sum() > 1:
            return False
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.show_shot", description=__doc__.split("\n")[0])
    what = ap.add_mutually_exclusive_group(required=True)
    what.add_argument("--script", choices=sorted(SCRIPTS))
    what.add_argument("--command")
    what.add_argument("--entry", type=Path, metavar="DIR")
    what.add_argument("--attract", type=Path, metavar="DIR")
    ap.add_argument("--out", required=True, metavar="STEM")
    ap.add_argument("--seconds", type=float, help="default 3 (--command), 60 (--entry), 10 (--attract)")
    ap.add_argument("--every-ms", type=int, default=500)
    ap.add_argument("--look", default="plain", choices=["plain", "led", "both"])
    ap.add_argument("--gamma", type=float, default=2.2)
    ap.add_argument("--crop", metavar="X,Y,W,H")
    ap.add_argument("--cwd", type=Path)
    ap.add_argument("--allow-black", action="store_true")
    ap.add_argument("--scale", type=int, default=4)
    ap.add_argument("--cols", type=int, default=2)
    ap.add_argument("--config", type=Path, default=ROOT / "show.toml")
    ap.add_argument("--build", metavar="CMD", help="with --entry: replace the copy's build command")
    ap.add_argument("--capture-first", action="store_true",
                    help="with --entry: play the copy once with its own build and capture on, keeping no frames")
    args = ap.parse_args(argv)

    cfg = load_config(args.config if args.config.is_absolute() else ROOT / args.config)
    font = Font.load(cfg.font_path if cfg.font_path.is_absolute() else ROOT / cfg.font_path)
    if (args.build or args.capture_first) and not args.entry:
        ap.error("--build and --capture-first go with --entry")
    if args.script:
        frames = frames_from_steps(SCRIPTS[args.script](), cfg, font)
        what_text = f"script {args.script}"
    elif args.entry:
        seconds = 60.0 if args.seconds is None else args.seconds
        frames, phases, failure = frames_from_entry(args.entry, cfg, font, seconds, args.every_ms,
                                                    args.build, args.capture_first)
        for phase, t in phases:
            print(f"{t:6.2f}s  {phase}")
        if failure:
            print(f"failure: {failure}")
        what_text = f"entry {args.entry.name}"
    elif args.attract:
        seconds = 10.0 if args.seconds is None else args.seconds
        frames = frames_from_attract(args.attract, cfg, font, seconds, args.every_ms)
        what_text = f"attract {args.attract.name}"
    else:
        seconds = 3.0 if args.seconds is None else args.seconds
        if args.cwd is not None:
            frames = frames_from_command(args.command, cfg, font, seconds, args.every_ms, args.cwd)
        else:
            with tempfile.TemporaryDirectory() as tmp:
                frames = frames_from_command(args.command, cfg, font, seconds, args.every_ms, Path(tmp))
        what_text = f"command {args.command!r}"
    if _program_black(frames, cfg) and not args.allow_black:
        print("refused: every frame's program rows are black; pass --allow-black to write the sheets anyway",
              file=sys.stderr)
        return 1
    if args.crop:
        x, y, w, h = _crop(args.crop)
        frames = [(label, f[y : y + h, x : x + w].copy()) for label, f in frames]
    sha = git_sha()
    base = (f"{sha} {'dirty' if sha.endswith('+dirty') else 'clean'} {what_text} gamma {args.gamma} "
            f"crop {args.crop or 'none'}")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    looks = ["plain", "led"] if args.look == "both" else [args.look]
    for look in looks:
        name = f"{out.name}-{look}.png" if args.look == "both" else out.name + ".png"
        save_png(sheet(frames, look, args.scale, f"{base} look {look}", args.gamma, args.cols),
                 out.with_name(name), sha)
    save_png(sheet(frames, "distance", max(DISTANCE_MIN_SCALE, args.scale),
                   f"{base} look distance ({DISTANCE_METRES:.0f} m)", args.gamma, args.cols),
             out.with_name(out.name + "-distance.png"), sha)
    return 0


if __name__ == "__main__":
    sys.exit(main())
