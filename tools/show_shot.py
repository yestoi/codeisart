"""Contact sheets of the show's terminal on the wall, for the operator.

    python -m tools.show_shot --script strip --look both --out sheets/strip
    python -m tools.show_shot --command "seq 1 60" --seconds 2 --every-ms 250 --look both --out sheets/seq
    python -m tools.show_shot --script strip --crop 0,0,128,64 --look led --out sheets/prototype
    python -m tools.show_shot --config show.poc.toml --command "./donut" --look led --out sheets/poc-donut
    python -m tools.show_shot --entry entries/hello --look both --out sheets/hello
    python -m tools.show_shot --entry entries/hello --capture-first --build "false" --out sheets/fallback
    python -m tools.show_shot --attract entries --look both --out sheets/attract
    python -m tools.show_shot --session presses --every-ms 1000 --look both --out sheets/presses
    python -m tools.show_shot --strips --look both --cols 3 --out sheets/strips

--session presses|strobe runs the whole show (ShowLoop on a fake display, real children, hello built in a temporary
copy) and takes the frames AFTER the flash governor, each labelled `held <n>` (the governor's held ticks so far);
--strips draws the strip's looks under hello's playing strip. Scripts: strip, edges, fullscreen, cc. --entry DIR plays an entry through the show's pipeline (in a temporary
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
from show.audio import FakeAudio                                                  # noqa: E402
from show.display.fake import FakeDisplay                                         # noqa: E402
from show.entries import Entry, load_entries, load_entry                          # noqa: E402
from show.font import CELL_H, CELL_W, Font                                              # noqa: E402
from show.lights import FakeLights                                                # noqa: E402
from show.main import ShowLoop, parse_play                                                    # noqa: E402
from show.pipeline import EntryPlayer, Phase                                      # noqa: E402
from show.renderer import STRIP_LOOKS, renderer_for                               # noqa: E402
from show.state import ALTERNATE_S, NOTICE_S, SHORT_BELOW, Show, strip_chars      # noqa: E402
from show.terminal import Terminal                                                # noqa: E402
from tools.flash_meter import FlashMeter                                          # noqa: E402
from tools.arcade_shot import BACKGROUND, CAP_H, INK, PAD, TITLE_H, TITLE_INK, fit_width, git_sha, save_png  # noqa: E402

ATTRACT_STRIP = "PRESS A BUTTON ON ANY PORTRAIT"
PLAY_STRIP = "NOW: hello by Trey, 2026, Not A.I. | NEXT: -"       # a sample until D3's strip() (Q52)
SHOW_MAX_WIDTH = 2080                                             # one 512 px frame at the led look's scale 4
COLS_MAX_WIDTH = 4 * SHOW_MAX_WIDTH                               # an explicit --cols is honoured up to this width, px
PAGE_MAX_H = 4000                                                 # a written page is at most this tall, px
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


def _renderer(cfg: Config, font: Font):
    return renderer_for(cfg, font)


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


SESSIONS = ("presses", "strobe", "entry", "reel")
PRESSES = {"presses": [(1.0, 1), (3.0, 2), (3.5, 1)], "strobe": [(1.0, 1)], "entry": [(1.0, 1)], "reel": []}
SESSION_SECONDS = 40.0
STROBE_S = 3.0
STROBE_PERIOD_S = 0.05
STROBE_C = r"""#include <stdio.h>
#include <unistd.h>
int main(void)
{
    static char buf[65536];
    setvbuf(stdout, buf, _IOFBF, sizeof buf);   /* a whole screen goes out in one write */
    printf("\033[?25l\033[2J");                 /* the cursor hidden first, the screen cleared, as hello.c does */
    fflush(stdout);
    usleep(1100000);                            /* a second of black: the build's text is out of the governor's window */
    for (int k = 0; k < %(n)d; k++) {
        if (k %% 2 == 0)                        /* a reverse screen ... */
            printf("\033[H\033[7m%%*s\033[0m", %(cells)d - 1, "");
        else                                    /* ... and black by turns */
            printf("\033[H\033[2J");
        fflush(stdout);
        usleep(%(us)d);
    }
    return 0;
}
"""


def _session_entries(name: str, cfg: Config, dest: Path, entry_dir: Path | None = None,
                     reel: str | None = None) -> None:
    """The session's entries in dest (a temporary directory): hello at stations 1 and 2, the strobe at 1,
    entry_dir's copy alone at station 1, or the reel's entries copied from the checkout at their own stations."""
    if name == "reel":
        if reel is None:
            raise ValueError("the reel session needs reel")
        for slug in dict.fromkeys(slug for slug, _ in parse_play(reel)):
            src = ROOT / cfg.entries_dir / slug
            if not src.is_dir():
                raise ValueError(f"no entry {slug!r} under {cfg.entries_dir}")
            shutil.copytree(src, dest / slug)
        return
    if name == "entry":
        if entry_dir is None:
            raise ValueError("the entry session needs entry_dir")
        copy = dest / Path(entry_dir).resolve().name
        shutil.copytree(entry_dir, copy)
        lines = (copy / "entry.toml").read_text().splitlines(keepends=True)
        (copy / "entry.toml").write_text("".join("station = 1\n" if line.startswith("station") else line
                                                 for line in lines))
        return
    if name == "strobe":
        d = dest / "strobe"
        d.mkdir(parents=True)
        (d / "prog.c").write_text(STROBE_C % {"n": int(STROBE_S / STROBE_PERIOD_S), "cells": (cfg.rows - 1) * cfg.columns,
                                              "us": int(STROBE_PERIOD_S * 1e6)})
        (d / "shown.txt").write_text("\n")         # the source typed on the wall: a blank one, no glyphs under the strobe
        (d / "entry.toml").write_text(
            'title = "strobe"\nauthor = "Trey"\nyear = 2026\nstation = 1\nsource = "shown.txt"\n'
            'build = "cc -o prog prog.c"\nrun = "./prog"\nbuild_seconds = 30\nrun_seconds = 10\n')
        return
    src = ROOT / "entries" / "hello"
    for slug, station in (("hello", 1), ("hello-2", 2)):
        shutil.copytree(src, dest / slug)
        lines = (src / "entry.toml").read_text().splitlines(keepends=True)
        (dest / slug / "entry.toml").write_text("".join(
            f"station = {station}\n" if line.startswith("station") else
            f'title = "{slug}"\n' if line.startswith("title") else line for line in lines))


def frames_from_session(name: str, cfg: Config, seconds: float = SESSION_SECONDS, every_ms: int = 500,
                        presses: list[tuple[float, int]] | None = None, meter: FlashMeter | None = None,
                        entry_dir: Path | None = None, reel: str | None = None
                        ) -> tuple[list[tuple[str, np.ndarray]], list[str], int]:
    """The show itself: a ShowLoop on a fake display, stepped at most at cfg.fps in real time (its children are
    real), button presses put on loop.presses at their times (`presses` overrides the session's). The frames are
    what the governor let through (the display's last push), one every every_ms and one at each press, labelled
    `<t>s held <n> area <a> sq <s>`: the governor's held ticks so far, and the flash area and square flashes the
    meter (made from the governor's fps and gamma when None) gave the frames pushed since the last cell; then
    the strip text of each frame and the governor's held_ticks at the end.
    Session "entry" plays entry_dir's copy alone, at station 1. Session "reel" plays `reel` (--play's list) through
    the loop's reel and ends when the reel does, or at `seconds`.
    Built in a temporary copy of the entries: nothing lands in the checkout."""
    if name not in SESSIONS:
        raise ValueError(f"session must be one of {SESSIONS}, got {name!r}")
    todo = sorted(PRESSES[name] if presses is None else presses)
    frames: list[tuple[str, np.ndarray]] = []
    strips: list[str] = []
    held_ticks = 0
    seen = 0                                       # display.count at the last step
    with tempfile.TemporaryDirectory() as tmp:
        entries = Path(tmp) / "entries"
        _session_entries(name, cfg, entries, entry_dir, reel)
        font_path = cfg.font_path if cfg.font_path.is_absolute() else ROOT / cfg.font_path
        display = FakeDisplay()
        loop = ShowLoop(replace(cfg, entries_dir=entries, font_path=font_path, capture=False), display=display,
                        notify=lambda state: None)
        loop._devices = True                       # no GPIO, button or sound device in a sheet: fakes
        loop.lights, loop.audio = FakeLights(), FakeAudio()
        period = 1.0 / cfg.fps
        try:
            start = time.monotonic()
            loop.start(0.0)
            if name == "reel":
                loop.start_reel(reel or "")
            next_keep = due = 0.0
            while True:
                t = time.monotonic() - start
                if t < due:
                    time.sleep(due - t)
                    t = time.monotonic() - start
                if t >= seconds or loop.reel_done:
                    break
                pressed = False
                while todo and todo[0][0] <= t:
                    loop.presses.put(todo.pop(0)[1])
                    pressed = True
                loop.step(t)
                due = t + period
                if display.count > seen and display.last is not None:      # a frame pushed: after the governor
                    seen = display.count
                    if meter is None and loop.wall is not None:
                        meter = FlashMeter(loop.wall.governor.fps, loop.wall.governor.gamma)
                    if meter is not None:
                        meter.add(display.last)
                if (pressed or t >= next_keep) and display.last is not None:
                    held_ticks = loop.wall.governor.held_ticks
                    area, squares = meter.take() if meter is not None else (0.0, 0)
                    frames.append((f"{t:.1f}s held {held_ticks} area {area:.4f} sq {squares}", display.last.copy()))
                    strips.append(loop.show.strip(t) if loop.show is not None else "")
                    if t >= next_keep:
                        next_keep = t + every_ms / 1000.0
            if loop.wall is not None:
                held_ticks = loop.wall.governor.held_ticks
        finally:
            loop._close()
    return frames, strips, held_ticks


class _NoPlayer:
    """A player that plays nothing: Show only needs one to be current."""
    done, crowd = False, False

    def __init__(self, entry, term, cfg):
        pass

    def start(self, now, crowd=False):
        pass

    def stop(self):
        pass

    def tick(self, now):
        return []


def playing_strips(cfg: Config) -> list[tuple[str, str]]:
    """hello's playing strip as Show builds it once the PLAYING notice is over: one text where the whole strip
    fits, both halves of the alternation where it does not (label suffix, text)."""
    entry = load_entry(ROOT / "entries" / "hello")
    show = Show(cfg, {entry.station: entry}, Terminal(cfg.columns, cfg.rows - 1), FakeLights(), FakeAudio(),
                _NoPlayer)
    show.press(entry.station, 0.0)
    if strip_chars(cfg) >= SHORT_BELOW:
        return [("", show.strip(NOTICE_S))]
    return [(" first half", show.strip(NOTICE_S)), (" second half", show.strip(NOTICE_S + ALTERNATE_S))]


def frames_from_strips(cfg: Config, font: Font) -> list[tuple[str, np.ndarray]]:
    """The strip script's play screen drawn by each strip look, under hello's playing strip."""
    play = _strip_script()[1]
    frames = []
    for look in STRIP_LOOKS:
        renderer = renderer_for(replace(cfg, strip_look=look, strip=True), font)   # the sheet's subject
        term = Terminal(cfg.columns, cfg.rows - 1)
        term.feed(play.data)
        for suffix, text in playing_strips(cfg):
            frames.append((look + suffix, renderer.render(term.screen, True, text).copy()))
    return frames


def sheet(frames, look: str, scale: int, title: str, gamma: float, cols: int,
          cap: int = SHOW_MAX_WIDTH) -> Image.Image:
    """The frames as captioned cells, cols to a row, under a title band."""
    h, w = frames[0][1].shape[:2]
    cols, scale = fit_width(w, PAD, PAD, cols, scale, cap)
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


def pages(frames, look: str, scale: int, title: str, gamma: float, cols: int, cap: int = SHOW_MAX_WIDTH,
          max_height: int = PAGE_MAX_H) -> list[Image.Image]:
    """sheet()'s cells in pages of whole rows (one row at least), each titled `<title> page <k>/<n>`."""
    h, w = frames[0][1].shape[:2]
    cols, scale = fit_width(w, PAD, PAD, cols, scale, cap)
    rows = max(1, (max_height - TITLE_H) // (h * scale + CAP_H + PAD))
    per = rows * cols
    chunks = [frames[k : k + per] for k in range(0, len(frames), per)]
    return [sheet(chunk, look, scale, f"{title} page {k}/{len(chunks)}", gamma, cols, cap)
            for k, chunk in enumerate(chunks, 1)]


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
    what.add_argument("--session", choices=[s for s in SESSIONS if s != "reel"])
    what.add_argument("--reel", metavar="SPEC", help="the show's --play list (a:18,b:12,c) through the governor")
    what.add_argument("--strips", action="store_true")
    ap.add_argument("--out", required=True, metavar="STEM")
    ap.add_argument("--seconds", type=float, help="default 3 (--command), 60 (--entry), 10 (--attract), 40 (--session)")
    ap.add_argument("--every-ms", type=int, default=500)
    ap.add_argument("--look", default="plain", choices=["plain", "led", "both"])
    ap.add_argument("--gamma", type=float, default=2.2)
    ap.add_argument("--crop", metavar="X,Y,W,H")
    ap.add_argument("--cwd", type=Path)
    ap.add_argument("--allow-black", action="store_true")
    ap.add_argument("--scale", type=int, default=4)
    ap.add_argument("--cols", type=int, default=None,
                    help="columns to a row: default 2 fitted to the width; given, honoured up to 8320 px")
    ap.add_argument("--config", type=Path, default=ROOT / "show.toml")
    ap.add_argument("--build", metavar="CMD", help="with --entry: replace the copy's build command")
    ap.add_argument("--governed", action="store_true",
                    help="with --entry: play it through the show's governor (the session 'entry'), print held, area, squares")
    ap.add_argument("--capture-first", action="store_true",
                    help="with --entry: play the copy once with its own build and capture on, keeping no frames")
    args = ap.parse_args(argv)

    cfg = load_config(args.config if args.config.is_absolute() else ROOT / args.config)
    font = Font.load(cfg.font_path if cfg.font_path.is_absolute() else ROOT / cfg.font_path)
    if (args.build or args.capture_first) and not args.entry:
        ap.error("--build and --capture-first go with --entry")
    if args.governed and not args.entry:
        ap.error("--governed goes with --entry")
    if args.script:
        frames = frames_from_steps(SCRIPTS[args.script](), cfg, font)
        what_text = f"script {args.script}"
    elif args.entry and args.governed:
        seconds = SESSION_SECONDS if args.seconds is None else args.seconds
        meter = FlashMeter(cfg.fps, cfg.gamma)
        frames, strips, held_ticks = frames_from_session("entry", cfg, seconds, args.every_ms, meter=meter,
                                                         entry_dir=args.entry)
        for (label, _), text in zip(frames, strips):
            print(f"{label}  {text}")
        print(f"held {held_ticks} area {meter.area_max:.4f} squares {meter.squares_max}")
        what_text = f"entry {args.entry.name} governed held {held_ticks}"
    elif args.entry:
        seconds = 60.0 if args.seconds is None else args.seconds
        frames, phases, failure = frames_from_entry(args.entry, cfg, font, seconds, args.every_ms,
                                                    args.build, args.capture_first)
        for phase, t in phases:
            print(f"{t:6.2f}s  {phase}")
        if failure:
            print(f"failure: {failure}")
        what_text = f"entry {args.entry.name}"
    elif args.session or args.reel:
        seconds = SESSION_SECONDS if args.seconds is None else args.seconds
        meter = FlashMeter(cfg.fps, cfg.gamma)
        name = "reel" if args.reel else args.session
        frames, strips, held_ticks = frames_from_session(name, cfg, seconds, args.every_ms, meter=meter,
                                                         reel=args.reel)
        for (label, _), text in zip(frames, strips):
            print(f"{label}  {text}")
        print(f"held {held_ticks} area {meter.area_max:.4f} squares {meter.squares_max}")
        what_text = f"{'reel ' + args.reel if args.reel else 'session ' + args.session} held {held_ticks}"
    elif args.strips:
        frames = frames_from_strips(cfg, font)
        what_text = "strips " + " ".join(STRIP_LOOKS)
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
    cols, cap = (2, SHOW_MAX_WIDTH) if args.cols is None else (args.cols, COLS_MAX_WIDTH)
    if args.cols is not None:
        w = frames[0][1].shape[1]
        fit = min((cap - PAD) // (w * scale + PAD) for scale in (args.scale, max(DISTANCE_MIN_SCALE, args.scale)))
        if args.cols > fit:
            ap.error(f"--cols {args.cols} does not fit: {fit} columns fit at --scale {args.scale} in {cap} px")
    sha = git_sha()
    base = (f"{sha} {'dirty' if sha.endswith('+dirty') else 'clean'} {what_text} gamma {args.gamma} "
            f"crop {args.crop or 'none'}")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    def write(stem: str, look: str, scale: int, title: str) -> None:
        made = pages(frames, look, scale, title, args.gamma, cols, cap)
        for k, page in enumerate(made, 1):
            save_png(page, out.with_name(stem + (f"-p{k}" if len(made) > 1 else "") + ".png"), sha)

    looks = ["plain", "led"] if args.look == "both" else [args.look]
    for look in looks:
        write(f"{out.name}-{look}" if args.look == "both" else out.name, look, args.scale, f"{base} look {look}")
    write(out.name + "-distance", "distance", max(DISTANCE_MIN_SCALE, args.scale),
          f"{base} look distance ({DISTANCE_METRES:.0f} m)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
