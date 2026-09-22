# Code is Art Show Daemon Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `show` daemon that turns a 512x192 LED wall into a real 80x24 terminal, plays IOCCC entries on button press (source, live gcc compile, live run), and never leaves the wall blank.

**Architecture:** One Python process with a state machine (attract / playing / queue). A pseudo-terminal plus pyte holds terminal state; a numpy renderer rasterizes it with a 6x8 bitmap font; a pluggable display backend pushes frames (SDL preview for development, DDP to Falcon Player and raw Colorlight Ethernet for the wall, rpi-rgb-led-matrix as backup). Entries run as real subprocesses with resource limits; fallback recordings replay through the same terminal on failure.

**Tech Stack:** Python 3.11+, pyte, numpy, pygame (SDL preview), gpiozero (Pi only), sdnotify, pytest. A C compiler (`cc`) is required on the dev machine and the Pi.

**Spec:** `docs/superpowers/specs/2026-09-22-code-is-art-design.md`

## Global Constraints

- Python >= 3.11 (tomllib is stdlib). Target hardware is a Raspberry Pi 4; Raspberry Pi 5 is not supported by the matrix backup library.
- Wall is 512 x 192 pixels; terminal is 80 x 24 cells with a 6x8 font, centered (16 px margin each side).
- Software brightness cap is 0.40 of full; night operating range is 0.10 to 0.20. The cap is enforced in config, not left to operators.
- Stations are numbered 1 to 5. Button pin list index 0 is station 1.
- Every entry command runs as `sh -c <command>` inside the entry directory with CPU, core, and file-size limits, and a wall-clock timeout.
- The daemon never exits on an entry error. Any exception in the show loop logs and returns to attract mode.
- Everything the wall shows during an entry is real: real pty, real gcc, real execution. Recordings replay only after a failure.
- Plaque text is exactly `Created by <author>, Not A.I.`.

## Review Focus

1. Program output containing UTF-8 box drawing or other non-Latin-1 characters must render as `?` and never raise. Test in Task 3.
2. A program that floods output (an infinite print loop) must not stall the frame loop; a single pump reads a bounded number of bytes. Test in Task 4.
3. Mashing the same button while its entry plays or is queued must neither restart nor duplicate it. Test in Task 12.
4. A build failure on an entry with no fallback recording must show the error, hold, and return to attract without an exception. Test in Task 10.
5. A program that leaves the cursor at column 80 (pending wrap) or hides the cursor must render without an index error. Test in Task 3.

---

## File Structure

```
pyproject.toml                 project metadata, deps, pytest config
show.toml                      runtime config (flat TOML, keys = Config fields)
.gitignore
show/__init__.py
show/config.py                 Config dataclass, load_config(path)
show/font.py                   Font: 5x7 glyphs in 6x8 cells, atlas()
show/renderer.py               Renderer: pyte screen -> RGB frame; draw_text; apply_glow
show/terminal.py               Terminal: pty + pyte, feed/run/pump/kill
show/display/__init__.py       Display protocol, make_display(cfg, on_key)
show/display/fake.py           FakeDisplay (tests, --backend fake)
show/display/sdl.py            SDLDisplay preview window, keys 1-9 as buttons
show/display/ddp.py            DDPDisplay -> Falcon Player (primary wall path)
show/display/colorlight.py     ColorlightDisplay raw Ethernet (secondary wall path)
show/display/matrix.py         MatrixDisplay rpi-rgb-led-matrix (backup)
show/entries.py                Entry dataclass, load_entry, load_entries
show/queue.py                  EntryQueue
show/recording.py              CastWriter, CastPlayer (asciinema v2 format)
show/sandbox.py                limits(): rlimit preexec for child processes
show/pipeline.py               Phase, EntryPlayer: source -> build -> run -> fallback -> dwell
show/attract.py                Attract: idle source scroller
show/state.py                  Show: attract/playing/queue state machine
show/input.py                  PressQueue, ButtonInput (gpiozero)
show/lights.py                 FakeLights, GpioLights, pulse_level
show/audio.py                  FakeAudio, AudioCues
show/main.py                   CLI, wiring, frame loop, watchdog
tools/extract_glcdfont.py      builds fonts/5x7.bin from Adafruit glcdfont.c
tools/make_cues.py             generates audio/*.wav cue sounds
tools/test_pattern.py          hardware diagnostic patterns
fonts/                         glcdfont.c, LICENSE.glcdfont, 5x7.bin
entries/hello/                 sample entry (hello.c, entry.toml)
deploy/show.service            systemd unit
deploy/README.md               Pi install steps
tests/                         one test module per show module, helpers.py, conftest.py
```

---

### Task 1: Project scaffold and config

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `show/__init__.py`, `show/config.py`, `show.toml`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `Config` dataclass (fields listed in the implementation), `load_config(path: Path) -> Config`, `Config.phosphor_rgb -> tuple[int,int,int]`, `Config.effective_brightness -> float`, `PHOSPHORS` dict.

- [ ] **Step 1: Create project files**

`pyproject.toml`:

```toml
[project]
name = "codeisart-show"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["pyte>=0.8.2", "numpy>=1.26", "pygame>=2.5", "sdnotify>=0.3"]

[project.optional-dependencies]
pi = ["gpiozero>=2.0", "Pillow>=10"]
dev = ["pytest>=8"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["show*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`.gitignore`:

```
.venv/
__pycache__/
*.pyc
*.egg-info/
entries/*/*
!entries/*/*.c
!entries/*/entry.toml
!entries/*/fallback.cast
```

`show/__init__.py`: empty file.

`show.toml`:

```toml
# Flat config. Every key is a field of show.config.Config.
backend = "sdl"          # sdl | fake | ddp | colorlight | matrix
brightness = 0.15        # night operating level
brightness_cap = 0.40    # never exceeded, sized to the power supplies
phosphor = "green"       # green | amber
glow = false
entries_dir = "entries"
audio_dir = "audio"
font_path = "fonts/5x7.bin"
button_pins = [5, 6, 13, 19, 26]
light_pins = [12, 16, 20, 21, 25]
ddp_host = "127.0.0.1"
ddp_port = 4048
colorlight_iface = "eth0"
matrix_multiplexing = 0
dwell = 4.0
error_hold = 3.0
typewriter_cps = 400
attract_lps = 3.0
fps = 30
capture = false
```

Then create the venv and install:

```bash
cd /Users/trey/dev/codeisart
python3 -m venv .venv && . .venv/bin/activate && pip install -e '.[dev]'
```

- [ ] **Step 2: Write the failing tests**

`tests/test_config.py`:

```python
from pathlib import Path

import pytest

from show.config import Config, load_config


def test_defaults_when_file_missing(tmp_path):
    cfg = load_config(tmp_path / "nope.toml")
    assert cfg.backend == "sdl"
    assert (cfg.columns, cfg.rows) == (80, 24)
    assert (cfg.width, cfg.height) == (512, 192)
    assert cfg.phosphor_rgb == (51, 255, 51)
    assert cfg.button_pins == [5, 6, 13, 19, 26]


def test_values_from_file(tmp_path):
    p = tmp_path / "show.toml"
    p.write_text('backend = "ddp"\nbrightness = 0.9\nbrightness_cap = 0.4\nphosphor = "amber"\nentries_dir = "e"\n')
    cfg = load_config(p)
    assert cfg.backend == "ddp"
    assert cfg.effective_brightness == 0.4
    assert cfg.phosphor_rgb == (255, 176, 0)
    assert cfg.entries_dir == Path("e")


def test_unknown_phosphor_rejected(tmp_path):
    p = tmp_path / "show.toml"
    p.write_text('phosphor = "blue"\n')
    with pytest.raises(ValueError):
        load_config(p)


def test_unknown_key_rejected(tmp_path):
    p = tmp_path / "show.toml"
    p.write_text('brightnes = 0.5\n')
    with pytest.raises(ValueError):
        load_config(p)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'show.config'`

- [ ] **Step 4: Implement config**

`show/config.py`:

```python
from __future__ import annotations

import dataclasses
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

PHOSPHORS: dict[str, tuple[int, int, int]] = {
    "green": (51, 255, 51),
    "amber": (255, 176, 0),
}


@dataclass
class Config:
    backend: str = "sdl"
    width: int = 512
    height: int = 192
    brightness: float = 0.15
    brightness_cap: float = 0.40
    sdl_scale: int = 2
    columns: int = 80
    rows: int = 24
    phosphor: str = "green"
    glow: bool = False
    entries_dir: Path = Path("entries")
    audio_dir: Path = Path("audio")
    font_path: Path = Path("fonts/5x7.bin")
    button_pins: list[int] = field(default_factory=lambda: [5, 6, 13, 19, 26])
    light_pins: list[int] = field(default_factory=lambda: [12, 16, 20, 21, 25])
    ddp_host: str = "127.0.0.1"
    ddp_port: int = 4048
    colorlight_iface: str = "eth0"
    matrix_multiplexing: int = 0
    dwell: float = 4.0
    error_hold: float = 3.0
    typewriter_cps: int = 400
    attract_lps: float = 3.0
    fps: int = 30
    capture: bool = False

    @property
    def phosphor_rgb(self) -> tuple[int, int, int]:
        return PHOSPHORS[self.phosphor]

    @property
    def effective_brightness(self) -> float:
        return min(self.brightness, self.brightness_cap)


def load_config(path: Path) -> Config:
    data = tomllib.loads(path.read_text()) if path.exists() else {}
    cfg = Config()
    fields = {f.name: f for f in dataclasses.fields(Config)}
    for key, value in data.items():
        if key not in fields:
            raise ValueError(f"{path}: unknown config key {key!r}")
        if isinstance(getattr(cfg, key), Path):
            value = Path(value)
        setattr(cfg, key, value)
    if cfg.phosphor not in PHOSPHORS:
        raise ValueError(f"{path}: phosphor must be one of {sorted(PHOSPHORS)}")
    if not 0.0 <= cfg.brightness_cap <= 1.0:
        raise ValueError(f"{path}: brightness_cap must be between 0 and 1")
    return cfg
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore show/__init__.py show/config.py show.toml tests/test_config.py
git commit -m "feat: project scaffold and flat TOML config"
```

---

### Task 2: Font

**Files:**
- Create: `tools/extract_glcdfont.py`, `show/font.py`, `fonts/glcdfont.c`, `fonts/LICENSE.glcdfont`, `fonts/5x7.bin`
- Test: `tests/test_font.py`, `tests/conftest.py`

**Interfaces:**
- Produces: `CELL_W = 6`, `CELL_H = 8`, `Font(data: bytes)`, `Font.load(path) -> Font`, `Font.glyph(code: int) -> list[int]` (8 rows, bit 5 is the leftmost pixel), `Font.atlas() -> np.ndarray` of shape `(256, 8, 6)` bool.

The glyph source is Adafruit's classic 5x7 `glcdfont.c` (BSD license), the dot-matrix font used on countless LED signs. Each glyph is 5 column bytes, bit 0 is the top row. It sits in a 6x8 cell with column 5 and row 7 as spacing.

- [ ] **Step 1: Fetch the font source and write the extractor**

```bash
mkdir -p fonts tools
curl -L -o fonts/glcdfont.c https://raw.githubusercontent.com/adafruit/Adafruit-GFX-Library/master/glcdfont.c
curl -L -o fonts/LICENSE.glcdfont https://raw.githubusercontent.com/adafruit/Adafruit-GFX-Library/master/license.txt
```

`tools/extract_glcdfont.py`:

```python
"""Extract the 5x7 glyph table from Adafruit's glcdfont.c into a 1280-byte file.

Usage: python tools/extract_glcdfont.py fonts/glcdfont.c fonts/5x7.bin
"""
import re
import sys
from pathlib import Path

src = Path(sys.argv[1]).read_text()
body = src[src.index("{") + 1 : src.rindex("}")]
values = [int(h, 16) for h in re.findall(r"0x([0-9A-Fa-f]{2})", body)]
if len(values) < 128 * 5:
    sys.exit(f"only {len(values)} bytes found; expected at least 640")
data = bytes(values[: 256 * 5]).ljust(256 * 5, b"\0")
Path(sys.argv[2]).write_bytes(data)
print(f"wrote {len(data)} bytes to {sys.argv[2]}")
```

Run: `python tools/extract_glcdfont.py fonts/glcdfont.c fonts/5x7.bin`
Expected: `wrote 1280 bytes to fonts/5x7.bin`

- [ ] **Step 2: Write the failing tests**

`tests/conftest.py`:

```python
import pytest

from show.config import Config
from show.font import Font

# Column bytes for a capital A in the glcdfont layout (bit 0 = top row).
A_COLUMNS = bytes([0x7E, 0x11, 0x11, 0x11, 0x7E])


@pytest.fixture
def font() -> Font:
    data = bytearray(256 * 5)
    data[65 * 5 : 66 * 5] = A_COLUMNS
    return Font(bytes(data))


@pytest.fixture
def fast_cfg() -> Config:
    return Config(typewriter_cps=1_000_000, dwell=0.1, error_hold=0.1, attract_lps=1000.0)
```

`tests/test_font.py`:

```python
from pathlib import Path

import pytest

from show.font import CELL_H, CELL_W, Font


def test_cell_size():
    assert (CELL_W, CELL_H) == (6, 8)


def test_space_is_blank(font):
    assert font.glyph(ord(" ")) == [0] * 8


def test_a_rows(font):
    rows = font.glyph(ord("A"))
    assert rows[0] == 0b011100
    assert rows[1] == 0b100010
    assert rows[4] == 0b111110
    assert rows[7] == 0
    assert all(r < 64 for r in rows)


def test_out_of_range_code_uses_question_mark(font):
    assert font.glyph(1000) == font.glyph(ord("?"))


def test_atlas_shape_and_content(font):
    atlas = font.atlas()
    assert atlas.shape == (256, 8, 6)
    assert atlas.dtype == bool
    assert atlas[65, 4].tolist() == [True, True, True, True, True, False]


def test_wrong_size_rejected():
    with pytest.raises(ValueError):
        Font(b"\0" * 10)


def test_real_font_file_loads():
    real = Font.load(Path("fonts/5x7.bin"))
    assert real.glyph(ord(" ")) == [0] * 8
    assert any(real.glyph(ord("A"))[:7])
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_font.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'show.font'`

- [ ] **Step 4: Implement the font**

`show/font.py`:

```python
from __future__ import annotations

from pathlib import Path

import numpy as np

CELL_W = 6
CELL_H = 8
GLYPH_COLS = 5
GLYPH_ROWS = 7
NUM_GLYPHS = 256


class Font:
    """5x7 column-major glyphs placed in 6x8 cells. Column 5 and row 7 are spacing."""

    def __init__(self, data: bytes):
        if len(data) != NUM_GLYPHS * GLYPH_COLS:
            raise ValueError(f"font data must be {NUM_GLYPHS * GLYPH_COLS} bytes, got {len(data)}")
        self._data = data
        self._atlas: np.ndarray | None = None

    @classmethod
    def load(cls, path: Path) -> "Font":
        return cls(Path(path).read_bytes())

    def glyph(self, code: int) -> list[int]:
        if not 0 <= code < NUM_GLYPHS:
            code = ord("?")
        cols = self._data[code * GLYPH_COLS : (code + 1) * GLYPH_COLS]
        rows = []
        for r in range(CELL_H):
            bits = 0
            if r < GLYPH_ROWS:
                for c in range(GLYPH_COLS):
                    if (cols[c] >> r) & 1:
                        bits |= 1 << (CELL_W - 1 - c)
            rows.append(bits)
        return rows

    def atlas(self) -> np.ndarray:
        if self._atlas is None:
            a = np.zeros((NUM_GLYPHS, CELL_H, CELL_W), dtype=bool)
            for code in range(NUM_GLYPHS):
                for r, bits in enumerate(self.glyph(code)):
                    for c in range(CELL_W):
                        a[code, r, c] = bool((bits >> (CELL_W - 1 - c)) & 1)
            self._atlas = a
        return self._atlas
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_font.py -v`
Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
git add tools/extract_glcdfont.py show/font.py fonts/ tests/test_font.py tests/conftest.py
git commit -m "feat: 5x7 bitmap font from glcdfont with 6x8 cell atlas"
```

---

### Task 3: Renderer

**Files:**
- Create: `show/renderer.py`
- Test: `tests/test_renderer.py`

**Interfaces:**
- Consumes: `Font`, `CELL_W`, `CELL_H` from Task 2.
- Produces: `Renderer(font, width, height, columns, rows, phosphor, glow=False)`, `Renderer.render(screen: pyte.Screen, cursor_on: bool = False, status: str | None = None) -> np.ndarray` shape `(height, width, 3)` uint8 at full phosphor brightness (backends apply brightness), `draw_text(frame, x, y, text, font, color) -> None`, `apply_glow(frame, amount=0.3) -> np.ndarray`.

Normal text is drawn at 70% of the phosphor color, bold at 100%, reverse video inverts the cell mask. The status row, when given, replaces the bottom terminal row in reverse video (used for "UP NEXT").

- [ ] **Step 1: Write the failing tests**

`tests/test_renderer.py`:

```python
import numpy as np
import pyte

from show.renderer import Renderer, apply_glow, draw_text

GREEN = (51, 255, 51)
DIM = tuple((np.array(GREEN) * 0.7).astype(np.uint8))


def make_screen(text: str = "") -> pyte.Screen:
    screen = pyte.Screen(80, 24)
    pyte.Stream(screen).feed(text)
    return screen


def test_frame_shape_and_blank(font):
    r = Renderer(font, 512, 192, 80, 24, GREEN)
    frame = r.render(make_screen())
    assert frame.shape == (192, 512, 3) and frame.dtype == np.uint8
    assert frame.sum() == 0


def test_terminal_must_fit(font):
    import pytest
    with pytest.raises(ValueError):
        Renderer(font, 400, 192, 80, 24, GREEN)


def test_glyph_lands_in_centered_cell(font):
    r = Renderer(font, 512, 192, 80, 24, GREEN)
    frame = r.render(make_screen("A"))
    lit = frame[0:8, 16:22].any(axis=2)          # x0 = (512 - 480) // 2 = 16
    assert lit[0].tolist() == [False, True, True, True, False, False]
    assert lit[4].tolist() == [True] * 5 + [False]
    assert frame[:, 22:].sum() == 0 and frame[8:, :].sum() == 0
    assert tuple(frame[4, 16]) == DIM


def test_bold_is_full_phosphor_and_reverse_inverts(font):
    r = Renderer(font, 512, 192, 80, 24, GREEN)
    frame = r.render(make_screen("\x1b[1mA\x1b[0m\x1b[7mA"))
    assert tuple(frame[4, 16]) == GREEN
    rev = frame[0:8, 22:28].any(axis=2)
    assert rev[0].tolist() == [True, False, False, False, True, True]
    assert rev[7].all()


def test_cursor_inverts_cell_and_clamps_at_column_80(font):
    r = Renderer(font, 512, 192, 80, 24, GREEN)
    screen = make_screen("A" * 80)               # pyte leaves cursor.x == 80 (pending wrap)
    frame = r.render(screen, cursor_on=True)
    last = frame[0:8, 16 + 79 * 6 : 16 + 80 * 6].any(axis=2)
    assert last[7].all()


def test_hidden_cursor_not_drawn(font):
    r = Renderer(font, 512, 192, 80, 24, GREEN)
    frame = r.render(make_screen("\x1b[?25l"), cursor_on=True)
    assert frame.sum() == 0


def test_non_latin1_char_renders_as_question_mark(font):
    r = Renderer(font, 512, 192, 80, 24, GREEN)
    frame = r.render(make_screen("█é"))   # '?' is blank in the synthetic font
    assert frame.sum() == 0


def test_status_row_is_reverse_video(font):
    r = Renderer(font, 512, 192, 80, 24, GREEN)
    frame = r.render(make_screen(), status="UP NEXT")
    row = frame[23 * 8 : 24 * 8, 16 : 16 + 480].any(axis=2)
    assert row[7].all()
    assert frame[: 23 * 8].sum() == 0


def test_draw_text(font):
    frame = np.zeros((16, 32, 3), np.uint8)
    draw_text(frame, 2, 4, "A", font, (255, 0, 0))
    assert tuple(frame[4, 3]) == (255, 0, 0)     # row 0, column 1 of A
    assert tuple(frame[4, 2]) == (0, 0, 0)


def test_glow_spreads_light(font):
    frame = np.zeros((8, 8, 3), np.uint8)
    frame[4, 4] = (0, 200, 0)
    out = apply_glow(frame, 0.5)
    assert tuple(out[4, 4]) == (0, 200, 0)
    assert tuple(out[4, 5]) == (0, 100, 0)
    assert tuple(out[3, 4]) == (0, 100, 0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_renderer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'show.renderer'`

- [ ] **Step 3: Implement the renderer**

`show/renderer.py`:

```python
from __future__ import annotations

import numpy as np
import pyte

from show.font import CELL_H, CELL_W, Font


class Renderer:
    def __init__(self, font: Font, width: int, height: int, columns: int, rows: int,
                 phosphor: tuple[int, int, int], glow: bool = False):
        if columns * CELL_W > width or rows * CELL_H > height:
            raise ValueError(f"{columns}x{rows} terminal does not fit {width}x{height} display")
        self.width, self.height, self.columns, self.rows = width, height, columns, rows
        self.atlas = font.atlas()
        self.glow = glow
        self.x0 = (width - columns * CELL_W) // 2
        self.y0 = (height - rows * CELL_H) // 2
        self.bold_rgb = np.array(phosphor, dtype=np.uint8)
        self.fg_rgb = (np.array(phosphor) * 0.7).astype(np.uint8)

    def cells(self, screen: pyte.Screen) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        codes = np.full((self.rows, self.columns), 32, dtype=np.int32)
        bold = np.zeros((self.rows, self.columns), dtype=bool)
        rev = np.zeros((self.rows, self.columns), dtype=bool)
        for y in range(self.rows):
            line = screen.buffer.get(y)
            if not line:
                continue
            for x, ch in line.items():
                if x >= self.columns:
                    continue
                code = ord(ch.data[0]) if ch.data else 32
                codes[y, x] = code if code < 256 else ord("?")
                bold[y, x] = bool(ch.bold)
                rev[y, x] = bool(ch.reverse)
        return codes, bold, rev

    def render(self, screen: pyte.Screen, cursor_on: bool = False,
               status: str | None = None) -> np.ndarray:
        codes, bold, rev = self.cells(screen)
        if status is not None:
            text = status[: self.columns].ljust(self.columns)
            codes[-1] = [min(ord(c), 255) for c in text]
            bold[-1] = False
            rev[-1] = True
        masks = self.atlas[codes] ^ rev[:, :, None, None]          # (rows, cols, 8, 6)
        cursor_row_free = status is None or screen.cursor.y < self.rows - 1
        if cursor_on and not screen.cursor.hidden and cursor_row_free:
            cy = min(screen.cursor.y, self.rows - 1)
            cx = min(screen.cursor.x, self.columns - 1)
            masks[cy, cx] = ~masks[cy, cx]
        pix = masks.transpose(0, 2, 1, 3).reshape(self.rows * CELL_H, self.columns * CELL_W)
        colors = np.where(bold[:, :, None], self.bold_rgb, self.fg_rgb)   # (rows, cols, 3)
        colors = np.repeat(np.repeat(colors, CELL_H, axis=0), CELL_W, axis=1)
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        region = frame[self.y0 : self.y0 + self.rows * CELL_H, self.x0 : self.x0 + self.columns * CELL_W]
        region[pix] = colors[pix]
        if self.glow:
            frame = apply_glow(frame)
        return frame


def apply_glow(frame: np.ndarray, amount: float = 0.3) -> np.ndarray:
    f = frame.astype(np.uint16)
    out = f.copy()
    for shift in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        neighbor = np.roll(f, shift, axis=(0, 1))
        out = np.maximum(out, (neighbor * amount).astype(np.uint16))
    return np.clip(out, 0, 255).astype(np.uint8)


def draw_text(frame: np.ndarray, x: int, y: int, text: str, font: Font,
              color: tuple[int, int, int]) -> None:
    atlas = font.atlas()
    if y + CELL_H > frame.shape[0]:
        return
    for i, ch in enumerate(text):
        cx = x + i * CELL_W
        if cx + CELL_W > frame.shape[1]:
            break
        cell = frame[y : y + CELL_H, cx : cx + CELL_W]
        cell[atlas[min(ord(ch), 255)]] = color
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_renderer.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add show/renderer.py tests/test_renderer.py
git commit -m "feat: vectorized terminal renderer with cursor, reverse, bold, status row"
```

---

### Task 4: Terminal (pty + pyte)

**Files:**
- Create: `show/terminal.py`
- Test: `tests/test_terminal.py`

**Interfaces:**
- Produces: `Terminal(columns=80, rows=24)` with `screen: pyte.Screen`, `listeners: list[Callable[[bytes], None]]`, `feed(data: bytes)`, `reset()`, `run(cmd: list[str], cwd: Path, env: dict | None = None, preexec=None)`, `pump(max_bytes=262144) -> int`, `running: bool`, `finished: bool` (process exited and pty EOF seen), `returncode: int | None`, `kill()`.

LNM mode is set on the screen so a bare `\n` in locally fed text acts as CR+LF. Child processes get a real pty with the window size set, so their `\n` is translated by the tty layer.

- [ ] **Step 1: Write the failing tests**

`tests/test_terminal.py`:

```python
import time
from pathlib import Path

from show.terminal import Terminal


def wait_finished(t: Terminal, seconds: float = 10.0) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline and not t.finished:
        t.pump()
        time.sleep(0.005)


def test_feed_updates_screen_with_lnm():
    t = Terminal(80, 24)
    t.feed(b"hello\nworld")
    assert t.screen.display[0].startswith("hello")
    assert t.screen.display[1].startswith("world")
    assert (t.screen.cursor.x, t.screen.cursor.y) == (5, 1)


def test_reset_clears_and_keeps_lnm():
    t = Terminal(80, 24)
    t.feed(b"abc")
    t.reset()
    t.feed(b"x\ny")
    assert t.screen.display[0].startswith("x")
    assert t.screen.display[1].startswith("y")


def test_run_captures_child_output_and_exit_code():
    t = Terminal(80, 24)
    t.run(["sh", "-c", "printf 'hi there\\n'; exit 3"], cwd=Path("."))
    wait_finished(t)
    assert t.finished
    assert t.returncode == 3
    assert t.screen.display[0].startswith("hi there")


def test_child_sees_window_size():
    t = Terminal(80, 24)
    t.run(["sh", "-c", "stty size"], cwd=Path("."))
    wait_finished(t)
    assert t.screen.display[0].startswith("24 80")


def test_listeners_receive_bytes():
    t = Terminal(80, 24)
    got = []
    t.listeners.append(got.append)
    t.feed(b"abc")
    assert got == [b"abc"]


def test_kill_stops_running_child():
    t = Terminal(80, 24)
    t.run(["sh", "-c", "sleep 30"], cwd=Path("."))
    assert t.running
    t.kill()
    assert t.finished
    assert t.returncode is not None and t.returncode < 0


def test_pump_is_bounded():
    t = Terminal(80, 24)
    t.run(["sh", "-c", "head -c 2000000 /dev/zero | tr '\\0' x"], cwd=Path("."))
    time.sleep(0.3)
    assert t.pump(max_bytes=100) <= 100
    t.kill()


def test_run_while_running_is_an_error():
    import pytest
    t = Terminal(80, 24)
    t.run(["sh", "-c", "sleep 30"], cwd=Path("."))
    with pytest.raises(RuntimeError):
        t.run(["true"], cwd=Path("."))
    t.kill()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_terminal.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'show.terminal'`

- [ ] **Step 3: Implement the terminal**

`show/terminal.py`:

```python
from __future__ import annotations

import fcntl
import os
import pty
import select
import signal
import struct
import subprocess
import termios
from pathlib import Path
from typing import Callable

import pyte
import pyte.modes


class Terminal:
    def __init__(self, columns: int = 80, rows: int = 24):
        self.columns, self.rows = columns, rows
        self.screen = pyte.Screen(columns, rows)
        self.screen.set_mode(pyte.modes.LNM)
        self.stream = pyte.ByteStream(self.screen)
        self.listeners: list[Callable[[bytes], None]] = []
        self.proc: subprocess.Popen | None = None
        self.master_fd: int | None = None

    def reset(self) -> None:
        self.screen.reset()
        self.screen.set_mode(pyte.modes.LNM)

    def feed(self, data: bytes) -> None:
        self.stream.feed(data)
        for fn in list(self.listeners):
            fn(data)

    def run(self, cmd: list[str], cwd: Path, env: dict | None = None, preexec=None) -> None:
        if self.running:
            raise RuntimeError("a process is already running in this terminal")
        self._close_master()
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", self.rows, self.columns, 0, 0))
        full_env = {**os.environ, "TERM": "xterm", "COLUMNS": str(self.columns),
                    "LINES": str(self.rows), **(env or {})}
        self.proc = subprocess.Popen(
            cmd, cwd=str(cwd), env=full_env, stdin=slave, stdout=slave, stderr=slave,
            start_new_session=True, preexec_fn=preexec, close_fds=True,
        )
        os.close(slave)
        os.set_blocking(master, False)
        self.master_fd = master

    def pump(self, max_bytes: int = 262144) -> int:
        if self.master_fd is None:
            return 0
        total = 0
        while total < max_bytes:
            ready, _, _ = select.select([self.master_fd], [], [], 0)
            if not ready:
                break
            try:
                data = os.read(self.master_fd, min(65536, max_bytes - total))
            except BlockingIOError:
                break
            except OSError:          # EIO on Linux once the child side is closed
                data = b""
            if not data:
                self._close_master()
                break
            self.feed(data)
            total += len(data)
        return total

    @property
    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    @property
    def finished(self) -> bool:
        return self.proc is not None and self.proc.poll() is not None and self.master_fd is None

    @property
    def returncode(self) -> int | None:
        return None if self.proc is None else self.proc.poll()

    def kill(self) -> None:
        if self.proc is not None and self.running:
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.proc.wait()
        self.pump()
        self._close_master()

    def _close_master(self) -> None:
        if self.master_fd is not None:
            os.close(self.master_fd)
            self.master_fd = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_terminal.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add show/terminal.py tests/test_terminal.py
git commit -m "feat: pty-backed terminal with pyte screen, bounded pump, kill"
```

---

### Task 5: Display interface, fake and SDL backends

**Files:**
- Create: `show/display/__init__.py`, `show/display/fake.py`, `show/display/sdl.py`
- Test: `tests/test_display.py`

**Interfaces:**
- Consumes: `Config` from Task 1.
- Produces: `Display` protocol with `push(frame: np.ndarray) -> None`, `set_brightness(level: float) -> None`, `close() -> None`; `FakeDisplay()` with `.frames`, `.brightness`, `.closed`; `SDLDisplay(width, height, scale=2, on_key=None)` where `on_key(index)` gets 0 for key `1`; `make_display(cfg, on_key=None) -> Display`.

Later tasks add `ddp`, `colorlight`, and `matrix` branches to `make_display`.

- [ ] **Step 1: Write the failing tests**

`tests/test_display.py`:

```python
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np
import pytest

from show.config import Config
from show.display import make_display
from show.display.fake import FakeDisplay
from show.display.sdl import SDLDisplay


def test_fake_display_records_frames():
    d = FakeDisplay()
    frame = np.zeros((192, 512, 3), np.uint8)
    d.push(frame)
    frame[0, 0] = 255
    d.push(frame)
    assert len(d.frames) == 2
    assert d.frames[0].sum() == 0 and d.frames[1].sum() == 765
    d.set_brightness(0.2)
    assert d.brightness == 0.2
    d.close()
    assert d.closed


def test_sdl_display_pushes_headless():
    pressed = []
    d = SDLDisplay(512, 192, scale=1, on_key=pressed.append)
    d.push(np.zeros((192, 512, 3), np.uint8))
    d.push(np.full((192, 512, 3), 40, np.uint8))
    d.set_brightness(0.15)
    d.close()


def test_make_display_fake_and_unknown():
    assert isinstance(make_display(Config(backend="fake")), FakeDisplay)
    with pytest.raises(ValueError):
        make_display(Config(backend="hologram"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_display.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'show.display'`

- [ ] **Step 3: Implement the display package**

`show/display/__init__.py`:

```python
from __future__ import annotations

from typing import Callable, Protocol

import numpy as np

from show.config import Config


class Display(Protocol):
    def push(self, frame: np.ndarray) -> None: ...
    def set_brightness(self, level: float) -> None: ...
    def close(self) -> None: ...


def make_display(cfg: Config, on_key: Callable[[int], None] | None = None) -> Display:
    if cfg.backend == "fake":
        from show.display.fake import FakeDisplay
        return FakeDisplay()
    if cfg.backend == "sdl":
        from show.display.sdl import SDLDisplay
        return SDLDisplay(cfg.width, cfg.height, cfg.sdl_scale, on_key)
    raise ValueError(f"unknown display backend {cfg.backend!r}")
```

`show/display/fake.py`:

```python
from __future__ import annotations

import numpy as np


class FakeDisplay:
    def __init__(self):
        self.frames: list[np.ndarray] = []
        self.brightness = 1.0
        self.closed = False

    def push(self, frame: np.ndarray) -> None:
        self.frames.append(frame.copy())

    def set_brightness(self, level: float) -> None:
        self.brightness = level

    def close(self) -> None:
        self.closed = True
```

`show/display/sdl.py`:

```python
from __future__ import annotations

from typing import Callable

import numpy as np
import pygame


class SDLDisplay:
    """Preview window. Keys 1..9 call on_key(0..8). Shows full brightness on purpose."""

    def __init__(self, width: int, height: int, scale: int = 2,
                 on_key: Callable[[int], None] | None = None):
        pygame.init()
        self.size = (width * scale, height * scale)
        self.on_key = on_key
        self.window = pygame.display.set_mode(self.size)
        pygame.display.set_caption("Code is Art")
        self.brightness = 1.0

    def push(self, frame: np.ndarray) -> None:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                raise KeyboardInterrupt
            if ev.type == pygame.KEYDOWN and self.on_key is not None and pygame.K_1 <= ev.key <= pygame.K_9:
                self.on_key(ev.key - pygame.K_1)
        surf = pygame.surfarray.make_surface(np.ascontiguousarray(frame.transpose(1, 0, 2)))
        pygame.transform.scale(surf, self.size, self.window)
        pygame.display.flip()

    def set_brightness(self, level: float) -> None:
        self.brightness = level

    def close(self) -> None:
        pygame.quit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_display.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add show/display tests/test_display.py
git commit -m "feat: display protocol with fake and SDL preview backends"
```

---

### Task 6: Entries

**Files:**
- Create: `show/entries.py`, `entries/hello/hello.c`, `entries/hello/entry.toml`
- Test: `tests/test_entries.py`, `tests/helpers.py`

**Interfaces:**
- Produces: `EntryError(Exception)`, frozen dataclass `Entry(slug, dir, title, author, year, station, source, build, run, build_seconds=60.0, run_seconds=20.0, fallback: Path | None = None)` with `plaque` and `fallback_path` properties, `load_entry(dir: Path) -> Entry`, `load_entries(root: Path) -> dict[int, Entry]` keyed by station.

Invalid entries are skipped with a logged error so one bad directory never stops the show. Zero valid entries raises.

- [ ] **Step 1: Create the sample entry**

`entries/hello/hello.c`:

```c
#include <stdio.h>
#include <unistd.h>
int main(void){const char*m="hello, world";for(int i=0;m[i];i++){putchar(m[i]);fflush(stdout);usleep(80000);}putchar('\n');return 0;}
```

`entries/hello/entry.toml`:

```toml
title = "hello"
author = "Trey"
year = 2026
station = 1
source = "hello.c"
build = "cc -o hello hello.c"
run = "./hello"
build_seconds = 60
run_seconds = 10
```

- [ ] **Step 2: Write the failing tests**

`tests/helpers.py`:

```python
from pathlib import Path


def write_entry(root: Path, slug: str, station: int, source: str, *,
                build: str = "cc -o prog prog.c", run: str = "./prog",
                run_seconds: float = 5.0, build_seconds: float = 30.0,
                fallback: str | None = None) -> Path:
    d = root / slug
    d.mkdir(parents=True)
    (d / "prog.c").write_text(source)
    (d / "entry.toml").write_text(
        f'title = "{slug}"\nauthor = "Test Author"\nyear = 2026\nstation = {station}\n'
        f'source = "prog.c"\nbuild = "{build}"\nrun = "{run}"\n'
        f'run_seconds = {run_seconds}\nbuild_seconds = {build_seconds}\n'
    )
    if fallback is not None:
        (d / "fallback.cast").write_text(fallback)
    return d


HELLO_C = '#include <stdio.h>\nint main(void){puts("hello, world");return 0;}\n'
```

`tests/test_entries.py`:

```python
from pathlib import Path

import pytest

from helpers import HELLO_C, write_entry
from show.entries import Entry, EntryError, load_entries, load_entry


def test_sample_entry_loads():
    e = load_entry(Path("entries/hello"))
    assert e.slug == "hello" and e.station == 1
    assert e.plaque == "Created by Trey, Not A.I."
    assert e.source == Path("entries/hello/hello.c")
    assert e.fallback is None
    assert e.fallback_path == Path("entries/hello/fallback.cast")


def test_fallback_detected_when_present(tmp_path):
    d = write_entry(tmp_path, "a", 1, HELLO_C, fallback="{}\n")
    assert load_entry(d).fallback == d / "fallback.cast"


def test_missing_toml_is_an_error(tmp_path):
    (tmp_path / "bad").mkdir()
    with pytest.raises(EntryError):
        load_entry(tmp_path / "bad")


def test_missing_source_is_an_error(tmp_path):
    d = write_entry(tmp_path, "a", 1, HELLO_C)
    (d / "prog.c").unlink()
    with pytest.raises(EntryError):
        load_entry(d)


def test_load_entries_skips_bad_and_duplicate_stations(tmp_path, caplog):
    write_entry(tmp_path, "a", 1, HELLO_C)
    write_entry(tmp_path, "b", 2, HELLO_C)
    write_entry(tmp_path, "c", 2, HELLO_C)          # duplicate station
    (tmp_path / "d").mkdir()                        # no entry.toml
    entries = load_entries(tmp_path)
    assert sorted(entries) == [1, 2]
    assert entries[2].slug == "b"
    assert "skipping" in caplog.text


def test_no_entries_raises(tmp_path):
    with pytest.raises(EntryError):
        load_entries(tmp_path)


def test_entry_is_hashable():
    e = load_entry(Path("entries/hello"))
    assert len({e, e}) == 1
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_entries.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'show.entries'`

- [ ] **Step 4: Implement entries**

`show/entries.py`:

```python
from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

REQUIRED = ("title", "author", "year", "station", "source", "build", "run")


class EntryError(Exception):
    pass


@dataclass(frozen=True)
class Entry:
    slug: str
    dir: Path
    title: str
    author: str
    year: int
    station: int
    source: Path
    build: str
    run: str
    build_seconds: float = 60.0
    run_seconds: float = 20.0
    fallback: Path | None = None

    @property
    def plaque(self) -> str:
        return f"Created by {self.author}, Not A.I."

    @property
    def fallback_path(self) -> Path:
        return self.dir / "fallback.cast"


def load_entry(dir: Path) -> Entry:
    toml_path = dir / "entry.toml"
    if not toml_path.exists():
        raise EntryError(f"{dir}: missing entry.toml")
    try:
        data = tomllib.loads(toml_path.read_text())
    except tomllib.TOMLDecodeError as exc:
        raise EntryError(f"{toml_path}: {exc}") from exc
    missing = [k for k in REQUIRED if k not in data]
    if missing:
        raise EntryError(f"{toml_path}: missing keys {missing}")
    source = dir / data["source"]
    if not source.exists():
        raise EntryError(f"{toml_path}: source {source} does not exist")
    station = int(data["station"])
    if station < 1:
        raise EntryError(f"{toml_path}: station must be >= 1")
    fallback = dir / "fallback.cast"
    return Entry(
        slug=dir.name, dir=dir, title=str(data["title"]), author=str(data["author"]),
        year=int(data["year"]), station=station, source=source,
        build=str(data["build"]), run=str(data["run"]),
        build_seconds=float(data.get("build_seconds", 60.0)),
        run_seconds=float(data.get("run_seconds", 20.0)),
        fallback=fallback if fallback.exists() else None,
    )


def load_entries(root: Path) -> dict[int, Entry]:
    entries: dict[int, Entry] = {}
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        try:
            e = load_entry(d)
        except EntryError as exc:
            log.error("skipping %s: %s", d, exc)
            continue
        if e.station in entries:
            log.error("skipping %s: station %d already used by %s", d, e.station, entries[e.station].slug)
            continue
        entries[e.station] = e
    if not entries:
        raise EntryError(f"no valid entries in {root}")
    return entries
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_entries.py -v`
Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
git add show/entries.py entries/hello tests/test_entries.py tests/helpers.py
git commit -m "feat: entry loading with validation and sample hello entry"
```

---

### Task 7: Entry queue

**Files:**
- Create: `show/queue.py`
- Test: `tests/test_queue.py`

**Interfaces:**
- Consumes: `Entry` from Task 6.
- Produces: `EntryQueue()` with `push(entry) -> bool` (False when already queued), `pop() -> Entry | None`, `peek() -> Entry | None`, `clear()`, `__len__`, `__contains__`.

- [ ] **Step 1: Write the failing tests**

`tests/test_queue.py`:

```python
from helpers import HELLO_C, write_entry
from show.entries import load_entry
from show.queue import EntryQueue


def test_fifo_and_dedupe(tmp_path):
    a = load_entry(write_entry(tmp_path, "a", 1, HELLO_C))
    b = load_entry(write_entry(tmp_path, "b", 2, HELLO_C))
    q = EntryQueue()
    assert q.push(a) is True
    assert q.push(b) is True
    assert q.push(a) is False
    assert len(q) == 2 and a in q
    assert q.peek() == a
    assert q.pop() == a
    assert q.pop() == b
    assert q.pop() is None and q.peek() is None


def test_clear(tmp_path):
    a = load_entry(write_entry(tmp_path, "a", 1, HELLO_C))
    q = EntryQueue()
    q.push(a)
    q.clear()
    assert len(q) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_queue.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'show.queue'`

- [ ] **Step 3: Implement the queue**

`show/queue.py`:

```python
from __future__ import annotations

from collections import deque

from show.entries import Entry


class EntryQueue:
    def __init__(self):
        self._items: deque[Entry] = deque()

    def push(self, entry: Entry) -> bool:
        if entry in self._items:
            return False
        self._items.append(entry)
        return True

    def pop(self) -> Entry | None:
        return self._items.popleft() if self._items else None

    def peek(self) -> Entry | None:
        return self._items[0] if self._items else None

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)

    def __contains__(self, entry: object) -> bool:
        return entry in self._items
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_queue.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add show/queue.py tests/test_queue.py
git commit -m "feat: deduplicating entry queue"
```

---

### Task 8: Recording (asciinema v2 cast)

**Files:**
- Create: `show/recording.py`
- Test: `tests/test_recording.py`

**Interfaces:**
- Produces: `CastWriter(path, columns, rows, clock=time.monotonic)` with `.path`, `write(data: bytes)`, `close()`; `CastPlayer(path, max_gap=2.0)` with `start(now)`, `tick(now) -> bytes`, `done: bool`, `duration: float`.

The format is asciinema v2: one JSON header line, then `[seconds, "o", text]` lines. Pauses longer than `max_gap` are compressed on playback so a recording never stalls the wall.

- [ ] **Step 1: Write the failing tests**

`tests/test_recording.py`:

```python
import json

from show.recording import CastPlayer, CastWriter


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def test_writer_produces_v2_cast(tmp_path):
    clock = Clock()
    w = CastWriter(tmp_path / "x.cast", 80, 24, clock)
    clock.t += 0.5
    w.write(b"hi\n")
    clock.t += 0.25
    w.write(b"\xff")          # invalid utf-8 must not raise
    w.close()
    lines = (tmp_path / "x.cast").read_text().splitlines()
    header = json.loads(lines[0])
    assert header["version"] == 2 and header["width"] == 80 and header["height"] == 24
    assert json.loads(lines[1]) == [0.5, "o", "hi\n"]
    assert json.loads(lines[2])[0] == 0.75


def test_player_replays_with_timing_and_gap_compression(tmp_path):
    p = tmp_path / "x.cast"
    p.write_text(
        json.dumps({"version": 2, "width": 80, "height": 24}) + "\n"
        + json.dumps([0.0, "o", "a"]) + "\n"
        + json.dumps([1.0, "o", "b"]) + "\n"
        + json.dumps([1.5, "i", "ignored"]) + "\n"
        + json.dumps([31.0, "o", "c"]) + "\n"
    )
    player = CastPlayer(p, max_gap=2.0)
    assert player.duration == 3.0            # 30 s pause compressed to 2 s
    player.start(10.0)
    assert player.tick(10.0) == b"a"
    assert player.tick(10.5) == b""
    assert player.tick(11.0) == b"b"
    assert not player.done
    assert player.tick(13.0) == b"c"
    assert player.done


def test_empty_cast_is_done_immediately(tmp_path):
    p = tmp_path / "x.cast"
    p.write_text(json.dumps({"version": 2, "width": 80, "height": 24}) + "\n")
    player = CastPlayer(p)
    player.start(0.0)
    assert player.tick(0.0) == b"" and player.done and player.duration == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_recording.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'show.recording'`

- [ ] **Step 3: Implement recording**

`show/recording.py`:

```python
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable


class CastWriter:
    def __init__(self, path: Path, columns: int, rows: int,
                 clock: Callable[[], float] = time.monotonic):
        self.path = Path(path)
        self._clock = clock
        self._t0 = clock()
        self._fh = self.path.open("w", encoding="utf-8")
        header = {"version": 2, "width": columns, "height": rows, "timestamp": int(time.time())}
        self._fh.write(json.dumps(header) + "\n")

    def write(self, data: bytes) -> None:
        t = round(self._clock() - self._t0, 4)
        self._fh.write(json.dumps([t, "o", data.decode("utf-8", "replace")]) + "\n")

    def close(self) -> None:
        self._fh.close()


class CastPlayer:
    def __init__(self, path: Path, max_gap: float = 2.0):
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        self.header = json.loads(lines[0]) if lines else {}
        self.events: list[tuple[float, bytes]] = []
        t = last = 0.0
        for line in lines[1:]:
            if not line.strip():
                continue
            ts, kind, text = json.loads(line)
            if kind != "o":
                continue
            t += min(ts - last, max_gap)
            last = ts
            self.events.append((t, text.encode("utf-8")))
        self._i = 0
        self._t0 = 0.0

    def start(self, now: float) -> None:
        self._t0 = now
        self._i = 0

    def tick(self, now: float) -> bytes:
        out = b""
        elapsed = now - self._t0
        while self._i < len(self.events) and self.events[self._i][0] <= elapsed:
            out += self.events[self._i][1]
            self._i += 1
        return out

    @property
    def done(self) -> bool:
        return self._i >= len(self.events)

    @property
    def duration(self) -> float:
        return self.events[-1][0] if self.events else 0.0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_recording.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add show/recording.py tests/test_recording.py
git commit -m "feat: asciinema v2 cast writer and gap-compressing player"
```

---

### Task 9: Sandbox limits

**Files:**
- Create: `show/sandbox.py`
- Test: `tests/test_sandbox.py`

**Interfaces:**
- Produces: `limits(cpu_seconds: float, memory_bytes: int = 256 * 1024 * 1024) -> Callable[[], None]`, a `preexec_fn` for `subprocess.Popen` / `Terminal.run`.

Sets CPU time, disables core dumps, caps output file size at 64 MB, and on Linux caps address space. Wall-clock timeouts are the pipeline's job (Task 10); this is the safety net under them.

- [ ] **Step 1: Write the failing tests**

`tests/test_sandbox.py`:

```python
import os
import signal
import subprocess

import pytest

from show.sandbox import limits


def test_cpu_limit_kills_busy_loop():
    p = subprocess.Popen(["sh", "-c", "while :; do :; done"], preexec_fn=limits(1),
                         start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        rc = p.wait(timeout=15)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        pytest.fail("busy loop was not killed by the CPU limit")
    assert rc < 0


def test_limited_process_can_still_run_normally():
    out = subprocess.run(["sh", "-c", "echo ok"], preexec_fn=limits(5), capture_output=True, text=True)
    assert out.stdout.strip() == "ok" and out.returncode == 0


def test_fractional_cpu_rounds_up_to_one_second():
    import resource
    out = subprocess.run(
        ["python3", "-c", "import resource; print(resource.getrlimit(resource.RLIMIT_CPU)[0])"],
        preexec_fn=limits(0.2), capture_output=True, text=True,
    )
    assert out.stdout.strip() == "1"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_sandbox.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'show.sandbox'`

- [ ] **Step 3: Implement limits**

`show/sandbox.py`:

```python
from __future__ import annotations

import math
import resource
import sys
from typing import Callable

MAX_OUTPUT_FILE = 64 * 1024 * 1024


def limits(cpu_seconds: float, memory_bytes: int = 256 * 1024 * 1024) -> Callable[[], None]:
    """Return a preexec_fn that applies resource limits to the child process."""
    cpu = max(1, int(math.ceil(cpu_seconds)))

    def apply() -> None:
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT_FILE, MAX_OUTPUT_FILE))
        if sys.platform.startswith("linux"):
            resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))

    return apply
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_sandbox.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add show/sandbox.py tests/test_sandbox.py
git commit -m "feat: rlimit-based sandbox for entry processes"
```

---

### Task 10: Entry pipeline

**Files:**
- Create: `show/pipeline.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `Terminal` (Task 4), `Entry` (Task 6), `CastWriter`/`CastPlayer` (Task 8), `limits` (Task 9), `Config` (Task 1).
- Produces: `Phase` enum (`SOURCE, BUILD, RUN, ERROR_HOLD, FALLBACK, DWELL, DONE`), `EntryPlayer(entry, term, cfg, clock=time.monotonic)` with `start(now)`, `tick(now) -> list[str]` (events `"cue:compile"`, `"cue:run"`, `"cue:error"`), `done: bool`, `failure: str | None`, `phase`, `stop()`.

Flow: typewriter the source at `cfg.typewriter_cps`, run the build command, run the program, dwell, done. Failure means build exit != 0, build timeout, or the program dying by signal (return code < 0, or > 128 when `sh` reports it). A run timeout is a normal end, since many entries animate forever. On failure: show the reason, hold `cfg.error_hold`, then replay `fallback.cast` if present. With `cfg.capture` on and no fallback present, the run is recorded to `fallback.cast` and kept only if the run did not crash.

- [ ] **Step 1: Write the failing tests**

`tests/test_pipeline.py`:

```python
import json
import time

from helpers import HELLO_C, write_entry
from show.entries import load_entry
from show.pipeline import EntryPlayer, Phase
from show.terminal import Terminal

CRASH_C = "int main(void){int*p=0;return *p;}\n"
BROKEN_C = "int main( {\n"
FOREVER_C = '#include <stdio.h>\nint main(void){for(;;){puts("tick");fflush(stdout);}}\n'
EXIT1_C = "int main(void){return 1;}\n"


def drive(player: EntryPlayer, seconds: float = 40.0) -> list[str]:
    events: list[str] = []
    deadline = time.monotonic() + seconds
    while not player.done and time.monotonic() < deadline:
        events += player.tick(time.monotonic())
        time.sleep(0.005)
    assert player.done, f"player stuck in {player.phase}"
    return events


def screen_text(term: Terminal) -> str:
    return "\n".join(term.screen.display)


def cast(text: str) -> str:
    return json.dumps({"version": 2, "width": 80, "height": 24}) + "\n" + json.dumps([0.0, "o", text]) + "\n"


def test_happy_path_compiles_and_runs(tmp_path, fast_cfg):
    entry = load_entry(write_entry(tmp_path, "hello", 1, HELLO_C))
    term = Terminal()
    player = EntryPlayer(entry, term, fast_cfg)
    player.start(time.monotonic())
    events = drive(player)
    assert "cue:compile" in events and "cue:run" in events and "cue:error" not in events
    assert player.failure is None
    text = screen_text(term)
    assert "Created by Test Author, Not A.I." in text
    assert "$ cc -o prog prog.c" in text
    assert "hello, world" in text


def test_build_failure_without_fallback_holds_then_finishes(tmp_path, fast_cfg):
    entry = load_entry(write_entry(tmp_path, "broken", 1, BROKEN_C))
    term = Terminal()
    player = EntryPlayer(entry, term, fast_cfg)
    player.start(time.monotonic())
    events = drive(player)
    assert "cue:error" in events
    assert player.failure is not None and player.failure.startswith("build failed")
    assert "*** build failed" in screen_text(term)


def test_crash_with_fallback_replays_recording(tmp_path, fast_cfg):
    entry = load_entry(write_entry(tmp_path, "crash", 1, CRASH_C, fallback=cast("recorded output\n")))
    term = Terminal()
    player = EntryPlayer(entry, term, fast_cfg)
    player.start(time.monotonic())
    events = drive(player)
    assert "cue:error" in events
    assert player.failure is not None and player.failure.startswith("crashed")
    assert "recorded output" in screen_text(term)


def test_run_timeout_is_a_normal_end(tmp_path, fast_cfg):
    entry = load_entry(write_entry(tmp_path, "forever", 1, FOREVER_C, run_seconds=1.0))
    term = Terminal()
    player = EntryPlayer(entry, term, fast_cfg)
    player.start(time.monotonic())
    drive(player)
    assert player.failure is None
    assert not term.running


def test_nonzero_exit_is_not_a_crash(tmp_path, fast_cfg):
    entry = load_entry(write_entry(tmp_path, "exit1", 1, EXIT1_C))
    term = Terminal()
    player = EntryPlayer(entry, term, fast_cfg)
    player.start(time.monotonic())
    events = drive(player)
    assert player.failure is None and "cue:error" not in events


def test_capture_writes_fallback_only_on_success(tmp_path, fast_cfg):
    fast_cfg.capture = True
    good = load_entry(write_entry(tmp_path, "good", 1, HELLO_C))
    term = Terminal()
    player = EntryPlayer(good, term, fast_cfg)
    player.start(time.monotonic())
    drive(player)
    assert good.fallback_path.exists()
    assert "hello, world" in good.fallback_path.read_text()

    bad = load_entry(write_entry(tmp_path, "bad", 2, CRASH_C))
    player = EntryPlayer(bad, Terminal(), fast_cfg)
    player.start(time.monotonic())
    drive(player)
    assert not bad.fallback_path.exists()


def test_stop_kills_process_and_finishes(tmp_path, fast_cfg):
    entry = load_entry(write_entry(tmp_path, "forever", 1, FOREVER_C, run_seconds=30.0))
    term = Terminal()
    player = EntryPlayer(entry, term, fast_cfg)
    player.start(time.monotonic())
    deadline = time.monotonic() + 30
    while player.phase != Phase.RUN and time.monotonic() < deadline:
        player.tick(time.monotonic())
        time.sleep(0.005)
    assert player.phase == Phase.RUN
    player.stop()
    assert player.done and not term.running
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'show.pipeline'`

- [ ] **Step 3: Implement the pipeline**

`show/pipeline.py`:

```python
from __future__ import annotations

import time
from enum import Enum
from typing import Callable

from show.config import Config
from show.entries import Entry
from show.recording import CastPlayer, CastWriter
from show.sandbox import limits
from show.terminal import Terminal

BUILD_MEMORY = 512 * 1024 * 1024
RUN_MEMORY = 256 * 1024 * 1024


class Phase(str, Enum):
    SOURCE = "source"
    BUILD = "build"
    RUN = "run"
    ERROR_HOLD = "error_hold"
    FALLBACK = "fallback"
    DWELL = "dwell"
    DONE = "done"


def signal_of(returncode: int) -> int | None:
    """Signal number if the process died by signal, else None. sh reports 128+n."""
    if returncode < 0:
        return -returncode
    if returncode > 128:
        return returncode - 128
    return None


class EntryPlayer:
    def __init__(self, entry: Entry, term: Terminal, cfg: Config,
                 clock: Callable[[], float] = time.monotonic):
        self.entry, self.term, self.cfg, self.clock = entry, term, cfg, clock
        self.phase = Phase.DONE
        self.events: list[str] = []
        self.failure: str | None = None
        self._src = b""
        self._pos = 0
        self._t0 = 0.0
        self._cast: CastPlayer | None = None
        self._writer: CastWriter | None = None

    # -- lifecycle -----------------------------------------------------------

    def start(self, now: float) -> None:
        e = self.entry
        self.term.reset()
        self.term.feed(f"{e.title} ({e.year})\n{e.plaque}\n\n$ cat {e.source.name}\n".encode())
        self._src = e.source.read_bytes().replace(b"\r\n", b"\n")
        self._pos = 0
        self.failure = None
        self._enter(Phase.SOURCE, now)

    def tick(self, now: float) -> list[str]:
        getattr(self, f"_tick_{self.phase.value}")(now)
        events, self.events = self.events, []
        return events

    def stop(self) -> None:
        self.term.kill()
        self._stop_capture(keep=False)
        self.phase = Phase.DONE

    @property
    def done(self) -> bool:
        return self.phase == Phase.DONE

    # -- phases --------------------------------------------------------------

    def _enter(self, phase: Phase, now: float) -> None:
        self.phase = phase
        self._t0 = now

    def _tick_source(self, now: float) -> None:
        want = min(len(self._src), int((now - self._t0) * self.cfg.typewriter_cps))
        if want > self._pos:
            self.term.feed(self._src[self._pos:want])
            self._pos = want
        if self._pos >= len(self._src):
            self.term.feed(f"\n$ {self.entry.build}\n".encode())
            self.term.run(["sh", "-c", self.entry.build], cwd=self.entry.dir,
                          preexec=limits(self.entry.build_seconds, BUILD_MEMORY))
            self.events.append("cue:compile")
            self._enter(Phase.BUILD, now)

    def _tick_build(self, now: float) -> None:
        self.term.pump()
        if self.term.finished:
            rc = self.term.returncode
            if rc != 0:
                self._fail(f"build failed (exit {rc})", now)
            else:
                self._start_run(now)
        elif now - self._t0 > self.entry.build_seconds:
            self.term.kill()
            self._fail("build timed out", now)

    def _start_run(self, now: float) -> None:
        self.term.feed(f"$ {self.entry.run}\n".encode())
        if self.cfg.capture and self.entry.fallback is None:
            self._writer = CastWriter(self.entry.fallback_path, self.term.columns, self.term.rows, self.clock)
            self.term.listeners.append(self._writer.write)
        self.term.run(["sh", "-c", self.entry.run], cwd=self.entry.dir,
                      preexec=limits(self.entry.run_seconds + 5, RUN_MEMORY))
        self.events.append("cue:run")
        self._enter(Phase.RUN, now)

    def _tick_run(self, now: float) -> None:
        self.term.pump()
        if self.term.finished:
            sig = signal_of(self.term.returncode or 0)
            self._stop_capture(keep=sig is None)
            if sig is not None:
                self._fail(f"crashed (signal {sig})", now)
            else:
                self._enter(Phase.DWELL, now)
        elif now - self._t0 > self.entry.run_seconds:
            self.term.kill()
            self._stop_capture(keep=True)
            self._enter(Phase.DWELL, now)

    def _tick_error_hold(self, now: float) -> None:
        if now - self._t0 < self.cfg.error_hold:
            return
        if self.entry.fallback is None:
            self._enter(Phase.DWELL, now)
            return
        self.term.reset()
        self.term.feed(f"$ {self.entry.run}   (recording)\n".encode())
        self._cast = CastPlayer(self.entry.fallback)
        self._cast.start(now)
        self._enter(Phase.FALLBACK, now)

    def _tick_fallback(self, now: float) -> None:
        assert self._cast is not None
        data = self._cast.tick(now)
        if data:
            self.term.feed(data)
        if self._cast.done:
            self._enter(Phase.DWELL, now)

    def _tick_dwell(self, now: float) -> None:
        if now - self._t0 >= self.cfg.dwell:
            self._enter(Phase.DONE, now)

    def _tick_done(self, now: float) -> None:
        pass

    # -- helpers -------------------------------------------------------------

    def _fail(self, reason: str, now: float) -> None:
        self.failure = reason
        self._stop_capture(keep=False)
        self.term.feed(f"\n*** {reason} ***\n".encode())
        self.events.append("cue:error")
        self._enter(Phase.ERROR_HOLD, now)

    def _stop_capture(self, keep: bool) -> None:
        if self._writer is None:
            return
        self.term.listeners.remove(self._writer.write)
        self._writer.close()
        if not keep:
            self._writer.path.unlink(missing_ok=True)
        self._writer = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_pipeline.py -v`
Expected: 7 passed. If `test_crash_with_fallback_replays_recording` reports `failure is None`, the platform's `sh` swallowed the signal into a plain exit code below 129; check `signal_of` against the actual return code printed by adding `print(term.returncode)` temporarily.

- [ ] **Step 5: Commit**

```bash
git add show/pipeline.py tests/test_pipeline.py
git commit -m "feat: entry pipeline with live build, sandboxed run, fallback replay, capture"
```

---

### Task 11: Attract mode

**Files:**
- Create: `show/attract.py`
- Test: `tests/test_attract.py`

**Interfaces:**
- Consumes: `Entry`, `Terminal`.
- Produces: `Attract(entries: Iterable[Entry], term: Terminal, lines_per_second: float)` with `start(now)`, `tick(now)`.

- [ ] **Step 1: Write the failing tests**

`tests/test_attract.py`:

```python
from helpers import write_entry
from show.attract import Attract
from show.entries import load_entry
from show.terminal import Terminal


def test_attract_scrolls_sources_in_station_order(tmp_path):
    b = load_entry(write_entry(tmp_path, "b", 2, "int b;\n"))
    a = load_entry(write_entry(tmp_path, "a", 1, "int a;\n"))
    term = Terminal()
    attract = Attract([b, a], term, lines_per_second=1.0)
    attract.start(0.0)
    text = "\n".join(term.screen.display)
    assert "CODE IS ART" in text
    attract.tick(0.5)
    assert "int a;" not in "\n".join(term.screen.display)
    attract.tick(3.0)                      # 3 lines: blank, header for a, blank
    text = "\n".join(term.screen.display)
    assert "a (2026)" in text and "Created by Test Author, Not A.I." in text
    attract.tick(4.0)
    assert "int a;" in "\n".join(term.screen.display)


def test_attract_wraps_around(tmp_path):
    a = load_entry(write_entry(tmp_path, "a", 1, "int a;\n"))
    term = Terminal()
    attract = Attract([a], term, lines_per_second=100.0)
    attract.start(0.0)
    attract.tick(10.0)                     # far more lines than the corpus has
    assert "int a;" in "\n".join(term.screen.display)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_attract.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'show.attract'`

- [ ] **Step 3: Implement attract mode**

`show/attract.py`:

```python
from __future__ import annotations

from typing import Iterable

from show.entries import Entry
from show.terminal import Terminal

BANNER = b"CODE IS ART, A.I. IS NOT\nPress the button on any portrait to compile and run it.\n\n"


class Attract:
    def __init__(self, entries: Iterable[Entry], term: Terminal, lines_per_second: float):
        self.term = term
        self.lps = lines_per_second
        self.lines: list[bytes] = []
        for e in sorted(entries, key=lambda e: e.station):
            self.lines += [b"", f"---- {e.title} ({e.year}) -- {e.plaque} ----".encode(), b""]
            self.lines += e.source.read_bytes().replace(b"\r\n", b"\n").split(b"\n")
        self._i = 0
        self._t0 = 0.0
        self._emitted = 0

    def start(self, now: float) -> None:
        self.term.reset()
        self.term.feed(BANNER)
        self._t0 = now
        self._emitted = 0

    def tick(self, now: float) -> None:
        if not self.lines:
            return
        want = int((now - self._t0) * self.lps)
        while self._emitted < want:
            self.term.feed(self.lines[self._i % len(self.lines)] + b"\n")
            self._i += 1
            self._emitted += 1
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_attract.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add show/attract.py tests/test_attract.py
git commit -m "feat: attract mode scrolls entry sources when idle"
```

---

### Task 12: Show state machine

**Files:**
- Create: `show/state.py`
- Test: `tests/test_show.py`

**Interfaces:**
- Consumes: `EntryQueue`, `Attract`, `EntryPlayer`, `Terminal`, `Entry`, `Config`.
- Produces: `Lights` protocol (`set(station: int, mode: str)`, `tick(now)`; modes `off`, `on`, `bright`, `pulse`), `Audio` protocol (`play(cue: str)`), `Show(cfg, entries: dict[int, Entry], term, lights, audio, player_factory=EntryPlayer)` with `start(now)`, `press(station: int, now: float)`, `tick(now)`, `playing: bool`, `current: Entry | None`, `queue: EntryQueue`, `status_line() -> str | None`, `abort(now)`.

- [ ] **Step 1: Write the failing tests**

`tests/test_show.py`:

```python
from helpers import HELLO_C, write_entry
from show.entries import load_entry
from show.state import Show
from show.terminal import Terminal


class FakePlayer:
    def __init__(self, entry, term, cfg):
        self.entry, self.term = entry, term
        self.started = False
        self.done = False
        self.pending: list[str] = []
        self.stopped = False

    def start(self, now):
        self.started = True
        self.term.reset()
        self.term.feed(f"playing {self.entry.slug}\n".encode())

    def tick(self, now):
        ev, self.pending = self.pending, []
        return ev

    def stop(self):
        self.stopped = True
        self.done = True


class FakeLights:
    def __init__(self):
        self.modes = {}
        self.ticks = 0

    def set(self, station, mode):
        self.modes[station] = mode

    def tick(self, now):
        self.ticks += 1


class FakeAudio:
    def __init__(self):
        self.played = []

    def play(self, cue):
        self.played.append(cue)


def make_show(tmp_path, fast_cfg):
    entries = {
        1: load_entry(write_entry(tmp_path, "a", 1, HELLO_C)),
        2: load_entry(write_entry(tmp_path, "b", 2, HELLO_C)),
    }
    term, lights, audio = Terminal(), FakeLights(), FakeAudio()
    show = Show(fast_cfg, entries, term, lights, audio, player_factory=FakePlayer)
    show.start(0.0)
    return show, term, lights, audio


def screen(term):
    return "\n".join(term.screen.display)


def test_start_is_attract_with_lights_on(tmp_path, fast_cfg):
    show, term, lights, audio = make_show(tmp_path, fast_cfg)
    assert not show.playing
    assert lights.modes == {1: "on", 2: "on"}
    assert "CODE IS ART" in screen(term)


def test_press_starts_immediately_when_idle(tmp_path, fast_cfg):
    show, term, lights, audio = make_show(tmp_path, fast_cfg)
    show.press(1, 1.0)
    assert show.playing and show.current.slug == "a"
    assert lights.modes[1] == "bright"
    assert audio.played == ["keypress"]
    assert "playing a" in screen(term)


def test_unknown_station_is_ignored(tmp_path, fast_cfg):
    show, *_ = make_show(tmp_path, fast_cfg)
    show.press(9, 1.0)
    assert not show.playing


def test_repeat_press_does_not_restart_or_queue(tmp_path, fast_cfg):
    show, term, lights, audio = make_show(tmp_path, fast_cfg)
    show.press(1, 1.0)
    player = show.player
    show.press(1, 1.5)
    show.press(1, 1.6)
    assert show.player is player and len(show.queue) == 0
    assert audio.played == ["keypress"]


def test_second_entry_queues_and_shows_up_next(tmp_path, fast_cfg):
    show, term, lights, audio = make_show(tmp_path, fast_cfg)
    show.press(1, 1.0)
    show.press(2, 1.1)
    show.press(2, 1.2)
    assert len(show.queue) == 1
    assert lights.modes[2] == "pulse"
    assert show.status_line() == " UP NEXT: b by Test Author  (1 queued) "
    assert audio.played == ["keypress", "keypress"]


def test_cues_are_forwarded_to_audio(tmp_path, fast_cfg):
    show, term, lights, audio = make_show(tmp_path, fast_cfg)
    show.press(1, 1.0)
    show.player.pending = ["cue:compile"]
    show.tick(2.0)
    assert audio.played[-1] == "compile"


def test_finished_player_starts_next_then_attract(tmp_path, fast_cfg):
    show, term, lights, audio = make_show(tmp_path, fast_cfg)
    show.press(1, 1.0)
    show.press(2, 1.1)
    show.player.done = True
    show.tick(2.0)
    assert show.playing and show.current.slug == "b"
    assert lights.modes == {1: "on", 2: "bright"}
    assert show.status_line() is None
    show.player.done = True
    show.tick(3.0)
    assert not show.playing
    assert lights.modes == {1: "on", 2: "on"}
    assert "CODE IS ART" in screen(term)


def test_abort_stops_player_clears_queue_and_returns_to_attract(tmp_path, fast_cfg):
    show, term, lights, audio = make_show(tmp_path, fast_cfg)
    show.press(1, 1.0)
    show.press(2, 1.1)
    player = show.player
    show.abort(2.0)
    assert player.stopped and not show.playing and len(show.queue) == 0
    assert "CODE IS ART" in screen(term)


def test_tick_in_attract_scrolls_and_ticks_lights(tmp_path, fast_cfg):
    show, term, lights, audio = make_show(tmp_path, fast_cfg)
    show.tick(5.0)
    assert lights.ticks == 1
    assert "int main" in screen(term)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_show.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'show.state'`

- [ ] **Step 3: Implement the state machine**

`show/state.py`:

```python
from __future__ import annotations

import logging
from typing import Callable, Protocol

from show.attract import Attract
from show.config import Config
from show.entries import Entry
from show.pipeline import EntryPlayer
from show.queue import EntryQueue
from show.terminal import Terminal

log = logging.getLogger(__name__)


class Lights(Protocol):
    def set(self, station: int, mode: str) -> None: ...
    def tick(self, now: float) -> None: ...


class Audio(Protocol):
    def play(self, cue: str) -> None: ...


class Show:
    def __init__(self, cfg: Config, entries: dict[int, Entry], term: Terminal,
                 lights: Lights, audio: Audio, player_factory: Callable = EntryPlayer):
        self.cfg, self.entries, self.term = cfg, entries, term
        self.lights, self.audio = lights, audio
        self.player_factory = player_factory
        self.queue = EntryQueue()
        self.player = None
        self.current: Entry | None = None
        self.attract = Attract(entries.values(), term, cfg.attract_lps)

    def start(self, now: float) -> None:
        for station in self.entries:
            self.lights.set(station, "on")
        self.attract.start(now)

    @property
    def playing(self) -> bool:
        return self.player is not None

    def press(self, station: int, now: float) -> None:
        entry = self.entries.get(station)
        if entry is None:
            log.warning("press on unknown station %d ignored", station)
            return
        if self.player is None:
            self._begin(entry, now)
            return
        if entry == self.current:
            return
        if self.queue.push(entry):
            self.lights.set(station, "pulse")
            self.audio.play("keypress")

    def tick(self, now: float) -> None:
        self.lights.tick(now)
        if self.player is None:
            self.attract.tick(now)
            return
        for event in self.player.tick(now):
            if event.startswith("cue:"):
                self.audio.play(event[4:])
        if self.player.done:
            self._finish(now)

    def status_line(self) -> str | None:
        nxt = self.queue.peek()
        if nxt is None:
            return None
        return f" UP NEXT: {nxt.title} by {nxt.author}  ({len(self.queue)} queued) "

    def abort(self, now: float) -> None:
        if self.player is not None:
            self.player.stop()
        self.player = None
        self.current = None
        self.queue.clear()
        for station in self.entries:
            self.lights.set(station, "on")
        self.attract.start(now)

    def _begin(self, entry: Entry, now: float) -> None:
        log.info("playing %s (station %d)", entry.slug, entry.station)
        self.current = entry
        self.player = self.player_factory(entry, self.term, self.cfg)
        self.player.start(now)
        self.lights.set(entry.station, "bright")
        self.audio.play("keypress")

    def _finish(self, now: float) -> None:
        assert self.current is not None
        self.lights.set(self.current.station, "on")
        self.player = None
        self.current = None
        nxt = self.queue.pop()
        if nxt is not None:
            self._begin(nxt, now)
        else:
            self.attract.start(now)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_show.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add show/state.py tests/test_show.py
git commit -m "feat: show state machine with queue, lights, audio cues, abort"
```

---

### Task 13: Input, lights, and audio

**Files:**
- Create: `show/input.py`, `show/lights.py`, `show/audio.py`, `tools/make_cues.py`, `audio/` (generated wavs)
- Test: `tests/test_io.py`

**Interfaces:**
- Produces: `PressQueue()` with `put(station: int)`, `drain() -> list[int]`; `ButtonInput(pins: list[int], presses: PressQueue)` with `close()` (Pi only, gpiozero); `FakeLights()`, `GpioLights(pins)` (Pi only), `pulse_level(now) -> float`, `MODES` dict; `FakeAudio()`, `AudioCues(dir: Path)` with `play(cue)`; `tools/make_cues.py` writes `audio/keypress.wav`, `compile.wav`, `run.wav`, `error.wav`.

Button callbacks fire on a gpiozero thread, so they only enqueue; the main loop drains the queue. Station numbers are 1-based: pin list index 0 is station 1.

- [ ] **Step 1: Write the failing tests**

`tests/test_io.py`:

```python
import wave
from pathlib import Path

from show.audio import AudioCues, FakeAudio
from show.input import PressQueue
from show.lights import MODES, FakeLights, pulse_level


def test_press_queue_drains_in_order():
    q = PressQueue()
    q.put(3)
    q.put(1)
    assert q.drain() == [3, 1]
    assert q.drain() == []


def test_fake_lights_and_modes():
    lights = FakeLights()
    lights.set(1, "pulse")
    lights.tick(0.0)
    assert lights.modes == {1: "pulse"}
    assert set(MODES) == {"off", "on", "bright"}
    assert MODES["off"] == 0.0 and MODES["bright"] == 1.0


def test_pulse_level_is_between_0_and_1():
    levels = [pulse_level(t / 10) for t in range(100)]
    assert all(0.0 <= v <= 1.0 for v in levels)
    assert max(levels) > 0.9 and min(levels) < 0.1


def test_audio_missing_cue_is_noop(tmp_path):
    AudioCues(tmp_path).play("nothing_here")


def test_fake_audio_records():
    a = FakeAudio()
    a.play("compile")
    assert a.played == ["compile"]


def test_make_cues_writes_wavs(tmp_path):
    import subprocess, sys
    subprocess.run([sys.executable, "tools/make_cues.py", str(tmp_path)], check=True)
    for name in ("keypress", "compile", "run", "error"):
        with wave.open(str(tmp_path / f"{name}.wav")) as w:
            assert w.getframerate() == 22050 and w.getnframes() > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_io.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'show.audio'`

- [ ] **Step 3: Implement input, lights, audio, and the cue generator**

`show/input.py`:

```python
from __future__ import annotations

import queue


class PressQueue:
    """Thread-safe hand-off from button callbacks (gpiozero thread, SDL) to the main loop."""

    def __init__(self):
        self._q: queue.Queue[int] = queue.Queue()

    def put(self, station: int) -> None:
        self._q.put(station)

    def drain(self) -> list[int]:
        out: list[int] = []
        while True:
            try:
                out.append(self._q.get_nowait())
            except queue.Empty:
                return out


class ButtonInput:
    """Five arcade buttons on Pi GPIO, active low with internal pull-ups."""

    def __init__(self, pins: list[int], presses: PressQueue):
        from gpiozero import Button  # Pi only

        self.buttons = []
        for index, pin in enumerate(pins):
            button = Button(pin, pull_up=True, bounce_time=0.05)
            button.when_pressed = (lambda station: (lambda: presses.put(station)))(index + 1)
            self.buttons.append(button)

    def close(self) -> None:
        for button in self.buttons:
            button.close()
```

`show/lights.py`:

```python
from __future__ import annotations

import math

MODES = {"off": 0.0, "on": 0.15, "bright": 1.0}


def pulse_level(now: float) -> float:
    return 0.5 + 0.5 * math.sin(now * 4.0)


class FakeLights:
    def __init__(self):
        self.modes: dict[int, str] = {}

    def set(self, station: int, mode: str) -> None:
        self.modes[station] = mode

    def tick(self, now: float) -> None:
        pass


class GpioLights:
    """Portrait button LEDs on PWM-capable GPIO through a MOSFET board."""

    def __init__(self, pins: list[int]):
        from gpiozero import PWMLED  # Pi only

        self.leds = {index + 1: PWMLED(pin) for index, pin in enumerate(pins)}
        self.modes = {station: "off" for station in self.leds}

    def set(self, station: int, mode: str) -> None:
        if station not in self.leds:
            return
        self.modes[station] = mode
        if mode != "pulse":
            self.leds[station].value = MODES[mode]

    def tick(self, now: float) -> None:
        level = pulse_level(now)
        for station, mode in self.modes.items():
            if mode == "pulse":
                self.leds[station].value = level
```

`show/audio.py`:

```python
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


class FakeAudio:
    def __init__(self):
        self.played: list[str] = []

    def play(self, cue: str) -> None:
        self.played.append(cue)


class AudioCues:
    def __init__(self, dir: Path):
        self.dir = Path(dir)
        self.player = shutil.which("aplay") or shutil.which("afplay")

    def play(self, cue: str) -> None:
        path = self.dir / f"{cue}.wav"
        if self.player is None or not path.exists():
            return
        try:
            subprocess.Popen([self.player, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as exc:
            log.warning("could not play %s: %s", path, exc)
```

`tools/make_cues.py`:

```python
"""Generate the four cue sounds as 16-bit mono WAVs.

Usage: python tools/make_cues.py [output_dir]   (default: audio)
"""
import sys
import wave
from pathlib import Path

import numpy as np

RATE = 22050


def tone(freq_start: float, freq_end: float, seconds: float, square: bool = False) -> np.ndarray:
    t = np.linspace(0, seconds, int(RATE * seconds), endpoint=False)
    freq = np.linspace(freq_start, freq_end, t.size)
    phase = 2 * np.pi * np.cumsum(freq) / RATE
    wave_ = np.sign(np.sin(phase)) if square else np.sin(phase)
    envelope = np.minimum(1.0, np.minimum(t / 0.005, (seconds - t) / 0.02))
    return wave_ * envelope * 0.5


def silence(seconds: float) -> np.ndarray:
    return np.zeros(int(RATE * seconds))


CUES = {
    "keypress": tone(880, 880, 0.06),
    "compile": tone(300, 900, 0.25),
    "run": np.concatenate([tone(660, 660, 0.08), silence(0.03), tone(990, 990, 0.08)]),
    "error": tone(150, 150, 0.35, square=True),
}


def main(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, samples in CUES.items():
        pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2")
        with wave.open(str(out_dir / f"{name}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(pcm.tobytes())
        print(f"wrote {out_dir / name}.wav")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("audio"))
```

Then generate the shipped cues:

```bash
python tools/make_cues.py audio
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_io.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add show/input.py show/lights.py show/audio.py tools/make_cues.py audio tests/test_io.py
git commit -m "feat: button input queue, portrait lights, audio cues and generator"
```

---

### Task 14: Main loop, CLI, systemd unit

**Files:**
- Create: `show/main.py`, `deploy/show.service`, `deploy/README.md`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `main(argv: list[str] | None = None) -> int`, `gpio_available() -> bool`, `parse_args(argv)`. CLI flags: `--config PATH` (default `show.toml`), `--backend NAME` (overrides config), `--play SLUG` (press that entry's station at start and exit when it finishes), `--capture` (sets `cfg.capture`).

The loop runs at `cfg.fps`: drain presses, tick the show, render, push, pet the watchdog. Any exception inside `show.tick` is logged and the show aborts to attract mode; the process keeps running.

- [ ] **Step 1: Write the failing tests**

`tests/test_main.py`:

```python
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from pathlib import Path

from helpers import HELLO_C, write_entry
from show.main import main, parse_args


def test_parse_args_defaults():
    args = parse_args([])
    assert args.config == Path("show.toml") and args.backend is None
    assert args.play is None and args.capture is False


def test_play_one_entry_headless_and_exit(tmp_path):
    write_entry(tmp_path / "entries", "quick", 1, HELLO_C)
    cfg = tmp_path / "show.toml"
    cfg.write_text(
        f'backend = "fake"\nentries_dir = "{tmp_path / "entries"}"\n'
        f'font_path = "{Path("fonts/5x7.bin").resolve()}"\naudio_dir = "{tmp_path}"\n'
        'typewriter_cps = 100000\ndwell = 0.1\nerror_hold = 0.1\nfps = 60\n'
    )
    assert main(["--config", str(cfg), "--play", "quick"]) == 0


def test_unknown_play_slug_is_an_error(tmp_path):
    write_entry(tmp_path / "entries", "quick", 1, HELLO_C)
    cfg = tmp_path / "show.toml"
    cfg.write_text(f'backend = "fake"\nentries_dir = "{tmp_path / "entries"}"\n'
                   f'font_path = "{Path("fonts/5x7.bin").resolve()}"\n')
    assert main(["--config", str(cfg), "--play", "nope"]) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_main.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'show.main'`

- [ ] **Step 3: Implement main and the deploy files**

`show/main.py`:

```python
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import sdnotify

from show.audio import AudioCues
from show.config import load_config
from show.display import make_display
from show.entries import load_entries
from show.font import Font
from show.input import PressQueue
from show.lights import FakeLights
from show.renderer import Renderer
from show.state import Show
from show.terminal import Terminal

log = logging.getLogger("show")


def gpio_available() -> bool:
    try:
        import gpiozero  # noqa: F401
    except ImportError:
        return False
    return Path("/dev/gpiomem").exists() or Path("/dev/gpiochip0").exists()


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="show", description="Code is Art LED wall show")
    p.add_argument("--config", type=Path, default=Path("show.toml"))
    p.add_argument("--backend", default=None, help="override display backend")
    p.add_argument("--play", default=None, metavar="SLUG", help="play one entry and exit")
    p.add_argument("--capture", action="store_true", help="record fallback.cast for entries lacking one")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    cfg = load_config(args.config)
    if args.backend:
        cfg.backend = args.backend
    if args.capture:
        cfg.capture = True

    entries = load_entries(cfg.entries_dir)
    play_station = None
    if args.play:
        matches = [s for s, e in entries.items() if e.slug == args.play]
        if not matches:
            log.error("no entry with slug %r (have %s)", args.play, sorted(e.slug for e in entries.values()))
            return 2
        play_station = matches[0]

    font = Font.load(cfg.font_path)
    renderer = Renderer(font, cfg.width, cfg.height, cfg.columns, cfg.rows, cfg.phosphor_rgb, cfg.glow)
    presses = PressQueue()
    display = make_display(cfg, on_key=lambda index: presses.put(index + 1))
    display.set_brightness(cfg.effective_brightness)
    term = Terminal(cfg.columns, cfg.rows)
    audio = AudioCues(cfg.audio_dir)
    buttons = None
    if gpio_available():
        from show.input import ButtonInput
        from show.lights import GpioLights
        lights = GpioLights(cfg.light_pins)
        buttons = ButtonInput(cfg.button_pins, presses)
    else:
        lights = FakeLights()
        log.info("GPIO not available; buttons come from the display window keys 1-9")

    show = Show(cfg, entries, term, lights, audio)
    notifier = sdnotify.SystemdNotifier()
    frame_time = 1.0 / cfg.fps
    push_failures = 0
    now = time.monotonic()
    show.start(now)
    if play_station is not None:
        show.press(play_station, now)
    notifier.notify("READY=1")

    try:
        while True:
            now = time.monotonic()
            for station in presses.drain():
                show.press(station, now)
            try:
                show.tick(now)
            except Exception:
                log.exception("show tick failed; returning to attract")
                show.abort(now)
            frame = renderer.render(term.screen, cursor_on=int(now * 2) % 2 == 0, status=show.status_line())
            try:
                display.push(frame)
                push_failures = 0
            except Exception:
                push_failures += 1
                if push_failures == 1 or push_failures % 300 == 0:
                    log.exception("display push failed (%d in a row); show keeps running", push_failures)
            notifier.notify("WATCHDOG=1")
            if play_station is not None and not show.playing:
                return 0
            time.sleep(max(0.0, frame_time - (time.monotonic() - now)))
    except KeyboardInterrupt:
        return 0
    finally:
        show.abort(time.monotonic())
        if buttons is not None:
            buttons.close()
        display.close()


if __name__ == "__main__":
    sys.exit(main())
```

`deploy/show.service`:

```ini
[Unit]
Description=Code is Art LED wall show
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
User=pi
WorkingDirectory=/home/pi/codeisart
ExecStart=/home/pi/codeisart/.venv/bin/python -m show.main --config show.toml
Restart=always
RestartSec=2
WatchdogSec=15
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

`deploy/README.md`:

```markdown
# Pi 4 deployment

1. Flash Raspberry Pi OS Lite (64-bit) or the Falcon Player image if using the DDP path.
2. `sudo apt install -y git python3-venv python3-dev build-essential libsdl2-dev alsa-utils`
3. `git clone <repo> /home/pi/codeisart && cd /home/pi/codeisart`
4. `python3 -m venv .venv && .venv/bin/pip install -e '.[pi]'`
5. Edit `show.toml`: set `backend` to `ddp`, `colorlight`, or `matrix`, and `brightness`.
6. `sudo cp deploy/show.service /etc/systemd/system/ && sudo systemctl daemon-reload`
7. `sudo systemctl enable --now show`
8. Hardware watchdog: in `/etc/systemd/system.conf` set `RuntimeWatchdogSec=20`, then reboot.
   Add `dtparam=watchdog=on` to `/boot/firmware/config.txt` if `/dev/watchdog` is missing.
9. Check: `journalctl -u show -f`. A button press should log `playing <slug>`.

The raw Colorlight backend needs raw socket rights: `sudo setcap cap_net_raw+ep .venv/bin/python3`
(resolve the symlink first: `readlink -f .venv/bin/python`).
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_main.py -v`
Expected: 3 passed

- [ ] **Step 5: Run the full suite and the preview**

Run: `pytest -q`
Expected: all tests pass.

Run: `python -m show.main --backend sdl`
Expected: a window opens showing the green attract scroll; pressing `1` plays the hello entry with a visible compile and "hello, world"; Ctrl-C exits cleanly.

- [ ] **Step 6: Commit**

```bash
git add show/main.py deploy tests/test_main.py
git commit -m "feat: main loop with CLI, watchdog, systemd unit and deploy notes"
```

---

### Task 15: DDP display backend (primary wall path via Falcon Player)

**Files:**
- Create: `show/display/ddp.py`
- Modify: `show/display/__init__.py` (add the `ddp` branch)
- Test: `tests/test_ddp.py`

**Interfaces:**
- Produces: `DDPDisplay(width, height, host, port=4048, sock=None)`, `packets(data: bytes, seq: int) -> list[bytes]`.

DDP (Distributed Display Protocol) is what Falcon Player accepts as input; FPP then drives the Colorlight card through its native "ColorLight 5A-75" channel output. Header is 10 bytes: flags (`0x40` = version 1, `|0x01` = push on the last packet of a frame), sequence (1..15), data type `0x01`, destination id `0x01`, 32-bit big-endian byte offset, 16-bit big-endian data length. Data is row-major RGB. At most 1440 data bytes per packet. Brightness is applied by scaling pixels before sending.

- [ ] **Step 1: Write the failing tests**

`tests/test_ddp.py`:

```python
import struct

import numpy as np

from show.config import Config
from show.display import make_display
from show.display.ddp import DDPDisplay, packets


class FakeSocket:
    def __init__(self):
        self.sent = []

    def sendto(self, data, addr):
        self.sent.append((data, addr))

    def close(self):
        pass


def test_packets_split_and_flag_last():
    data = bytes(512 * 192 * 3)
    pk = packets(data, seq=3)
    assert len(pk) == 205
    flags, seq, dtype, dest, off, length = struct.unpack("!BBBBIH", pk[0][:10])
    assert (flags, seq, dtype, dest, off, length) == (0x40, 3, 1, 1, 0, 1440)
    flags, _, _, _, off, length = struct.unpack("!BBBBIH", pk[-1][:10])
    assert flags == 0x41 and off == 204 * 1440 and length == 294912 - 204 * 1440
    assert sum(len(p) - 10 for p in pk) == len(data)


def test_push_scales_brightness_and_cycles_sequence():
    sock = FakeSocket()
    d = DDPDisplay(4, 1, "10.0.0.2", 4048, sock=sock)
    d.set_brightness(0.5)
    frame = np.full((1, 4, 3), 200, np.uint8)
    d.push(frame)
    data, addr = sock.sent[0]
    assert addr == ("10.0.0.2", 4048)
    assert data[10:13] == bytes([100, 100, 100])
    seqs = []
    for _ in range(16):
        d.push(frame)
        seqs.append(sock.sent[-1][0][1])
    assert seqs[0] == 2 and 15 in seqs and 0 not in seqs and seqs[-1] == 2


def test_make_display_ddp():
    d = make_display(Config(backend="ddp"))
    assert isinstance(d, DDPDisplay)
    d.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ddp.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'show.display.ddp'`

- [ ] **Step 3: Implement the DDP backend**

`show/display/ddp.py`:

```python
from __future__ import annotations

import socket
import struct

import numpy as np

DDP_PORT = 4048
MAX_DATA = 1440
FLAG_VERSION1 = 0x40
FLAG_PUSH = 0x01
DATA_TYPE_RGB8 = 0x01
DEST_DEFAULT = 0x01


def packets(data: bytes, seq: int) -> list[bytes]:
    out = []
    total = len(data)
    for off in range(0, total, MAX_DATA):
        chunk = data[off : off + MAX_DATA]
        last = off + len(chunk) >= total
        flags = FLAG_VERSION1 | (FLAG_PUSH if last else 0)
        header = struct.pack("!BBBBIH", flags, seq & 0x0F, DATA_TYPE_RGB8, DEST_DEFAULT, off, len(chunk))
        out.append(header + chunk)
    return out


class DDPDisplay:
    def __init__(self, width: int, height: int, host: str, port: int = DDP_PORT, sock=None):
        self.width, self.height = width, height
        self.addr = (host, port)
        self.sock = sock or socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.brightness = 1.0
        self._seq = 1

    def set_brightness(self, level: float) -> None:
        self.brightness = level

    def push(self, frame: np.ndarray) -> None:
        scaled = (frame.astype(np.float32) * self.brightness).astype(np.uint8)
        for packet in packets(scaled.tobytes(), self._seq):
            self.sock.sendto(packet, self.addr)
        self._seq = self._seq % 15 + 1

    def close(self) -> None:
        self.sock.close()
```

Modify `show/display/__init__.py`: add before the final `raise`:

```python
    if cfg.backend == "ddp":
        from show.display.ddp import DDPDisplay
        return DDPDisplay(cfg.width, cfg.height, cfg.ddp_host, cfg.ddp_port)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ddp.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add show/display/ddp.py show/display/__init__.py tests/test_ddp.py
git commit -m "feat: DDP display backend for Falcon Player"
```

---

### Task 16: Raw Colorlight display backend (secondary wall path)

**Files:**
- Create: `show/display/colorlight.py`
- Modify: `show/display/__init__.py` (add the `colorlight` branch)
- Test: `tests/test_colorlight.py`

**Interfaces:**
- Produces: `ColorlightDisplay(width, height, iface, sock=None)`, `row_packets(row: int, pixels: np.ndarray) -> list[bytes]`, `frame_packet(brightness: float) -> bytes`, `brightness_packet(level: float) -> bytes`.

This talks to the 5A-75E directly over a raw Ethernet socket (Linux only, needs `cap_net_raw`). The packet layout below is transcribed from the chubby75 5A-75B protocol notes and Falcon Player's `ColorLight-5a-75.cpp`. **Before the hardware test in Task 18, diff the constants in this file against those two sources**, in particular the byte offsets inside `frame_packet` and the pixel byte order. A wrong pixel order shows up immediately with the `rgb` test pattern. Rows wider than 497 pixels do not fit one Ethernet frame, so each row is sent as chunks of 256 pixels using the pixel-offset field.

- [ ] **Step 1: Write the failing tests**

`tests/test_colorlight.py`:

```python
import numpy as np

from show.display.colorlight import (ColorlightDisplay, DST_MAC, SRC_MAC, brightness_packet,
                                     frame_packet, row_packets)


class FakeSocket:
    def __init__(self):
        self.sent = []

    def send(self, data):
        self.sent.append(data)

    def close(self):
        pass


def test_row_packets_chunk_512_pixels_into_two():
    pixels = np.zeros((512, 3), np.uint8)
    pixels[0] = (255, 0, 0)          # red pixel at column 0
    pixels[256] = (0, 0, 255)        # blue pixel at column 256
    pk = row_packets(5, pixels)
    assert len(pk) == 2
    header = pk[0][:14]
    assert header[:6] == DST_MAC and header[6:12] == SRC_MAC and header[12:14] == b"\x55\x00"
    payload = pk[0][14:]
    assert payload[:7] == bytes([5, 0, 0, 1, 0, 0x08, 0x88])          # row 5, offset 0, count 256
    assert payload[7:10] == bytes([0, 0, 255])                        # BGR order
    payload2 = pk[1][14:]
    assert payload2[:7] == bytes([5, 1, 0, 1, 0, 0x08, 0x88])         # offset 256
    assert payload2[7:10] == bytes([255, 0, 0])
    assert all(len(p) <= 1514 for p in pk)


def test_row_above_255_sets_ethertype_low_byte():
    pk = row_packets(300, np.zeros((8, 3), np.uint8))
    assert pk[0][12:14] == b"\x55\x01" and pk[0][14] == 300 & 0xFF


def test_frame_and_brightness_packets():
    fp = frame_packet(0.5)
    assert fp[12:14] == b"\x01\x07" and len(fp) == 14 + 98
    assert fp[14 + 21] == 127 and fp[14 + 22] == 0x05
    bp = brightness_packet(1.0)
    assert bp[12:14] == b"\x0a\xff" and bp[14] == 255 and bp[15] == 0x05


def test_push_sends_rows_then_frame_packet():
    sock = FakeSocket()
    d = ColorlightDisplay(512, 4, "eth0", sock=sock)
    d.set_brightness(0.2)
    assert sock.sent[-1][12:14] == b"\x0a\xff"
    d.push(np.zeros((4, 512, 3), np.uint8))
    frame_packets = sock.sent[1:]
    assert len(frame_packets) == 4 * 2 + 1
    assert frame_packets[-1][12:14] == b"\x01\x07"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_colorlight.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'show.display.colorlight'`

- [ ] **Step 3: Implement the Colorlight backend**

`show/display/colorlight.py`:

```python
"""Raw Ethernet driver for Colorlight 5A-75B/E receiving cards.

Layout transcribed from the chubby75 project notes and Falcon Player's
ColorLight-5a-75.cpp. VERIFY ON HARDWARE (Task 18) before trusting the byte offsets.
"""
from __future__ import annotations

import socket

import numpy as np

DST_MAC = bytes.fromhex("112233445566")
SRC_MAC = bytes.fromhex("222233445566")
ETH_ROW = 0x5500
ETH_FRAME = 0x0107
ETH_BRIGHTNESS = 0x0AFF
CHUNK_PIXELS = 256
FRAME_PAYLOAD_LEN = 98
BRIGHTNESS_PAYLOAD_LEN = 63


def _eth(ethertype: int) -> bytes:
    return DST_MAC + SRC_MAC + ethertype.to_bytes(2, "big")


def row_packets(row: int, pixels: np.ndarray) -> list[bytes]:
    out = []
    for off in range(0, pixels.shape[0], CHUNK_PIXELS):
        chunk = pixels[off : off + CHUNK_PIXELS]
        n = chunk.shape[0]
        header = bytes([row & 0xFF, off >> 8, off & 0xFF, n >> 8, n & 0xFF, 0x08, 0x88])
        bgr = np.ascontiguousarray(chunk[:, ::-1]).astype(np.uint8).tobytes()
        out.append(_eth(ETH_ROW | (row >> 8)) + header + bgr)
    return out


def frame_packet(brightness: float) -> bytes:
    b = int(max(0.0, min(1.0, brightness)) * 255)
    payload = bytearray(FRAME_PAYLOAD_LEN)
    payload[21] = b
    payload[22] = 0x05
    payload[24] = payload[25] = payload[26] = b
    return _eth(ETH_FRAME) + bytes(payload)


def brightness_packet(level: float) -> bytes:
    b = int(max(0.0, min(1.0, level)) * 255)
    payload = bytearray(BRIGHTNESS_PAYLOAD_LEN)
    payload[0] = b
    payload[1] = 0x05
    payload[2] = payload[3] = payload[4] = b
    return _eth(ETH_BRIGHTNESS) + bytes(payload)


class ColorlightDisplay:
    def __init__(self, width: int, height: int, iface: str, sock=None):
        self.width, self.height = width, height
        if sock is None:
            sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)   # Linux only
            sock.bind((iface, 0))
        self.sock = sock
        self.brightness = 1.0

    def set_brightness(self, level: float) -> None:
        self.brightness = level
        self.sock.send(brightness_packet(level))

    def push(self, frame: np.ndarray) -> None:
        for y in range(self.height):
            for packet in row_packets(y, frame[y]):
                self.sock.send(packet)
        self.sock.send(frame_packet(self.brightness))

    def close(self) -> None:
        self.sock.close()
```

Modify `show/display/__init__.py`: add before the final `raise`:

```python
    if cfg.backend == "colorlight":
        from show.display.colorlight import ColorlightDisplay
        return ColorlightDisplay(cfg.width, cfg.height, cfg.colorlight_iface)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_colorlight.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add show/display/colorlight.py show/display/__init__.py tests/test_colorlight.py
git commit -m "feat: raw Ethernet Colorlight display backend (verify on hardware)"
```

---

### Task 17: rpi-rgb-led-matrix backup backend

**Files:**
- Create: `show/display/matrix.py`
- Modify: `show/display/__init__.py` (add the `matrix` branch)
- Test: `tests/test_matrix.py`

**Interfaces:**
- Produces: `MatrixDisplay(width, height, multiplexing=0, panel_cols=64, panel_rows=32, chain=16, parallel=3)`, `matrix_options(...) -> dict` (pure function so the geometry is unit-testable without the library).

Geometry: three parallel chains of 16 panels with the library's `U-mapper`, which folds each chain into two rows of 8. That yields 8 x 64 = 512 wide and 3 x 2 x 32 = 192 tall. The `rgbmatrix` Python binding is built from the library source on the Pi (see the step below), never from pip.

- [ ] **Step 1: Write the failing test**

`tests/test_matrix.py`:

```python
from show.display.matrix import matrix_options


def test_default_geometry_matches_the_wall():
    o = matrix_options(512, 192, multiplexing=3)
    assert (o["rows"], o["cols"], o["chain_length"], o["parallel"]) == (32, 64, 16, 3)
    assert o["pixel_mapper_config"] == "U-mapper"
    assert o["multiplexing"] == 3
    assert o["pwm_bits"] == 7


def test_geometry_that_does_not_fit_is_rejected():
    import pytest
    with pytest.raises(ValueError):
        matrix_options(500, 192)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_matrix.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'show.display.matrix'`

- [ ] **Step 3: Implement the matrix backend**

`show/display/matrix.py`:

```python
from __future__ import annotations

import numpy as np


def matrix_options(width: int, height: int, multiplexing: int = 0, panel_cols: int = 64,
                   panel_rows: int = 32, chain: int = 16, parallel: int = 3) -> dict:
    folded_cols = panel_cols * chain // 2          # U-mapper folds each chain into two rows
    folded_rows = panel_rows * 2 * parallel
    if (folded_cols, folded_rows) != (width, height):
        raise ValueError(f"chain {chain} x parallel {parallel} gives {folded_cols}x{folded_rows}, "
                         f"not {width}x{height}")
    return {
        "rows": panel_rows, "cols": panel_cols, "chain_length": chain, "parallel": parallel,
        "pixel_mapper_config": "U-mapper", "multiplexing": multiplexing, "pwm_bits": 7,
        "hardware_mapping": "regular", "gpio_slowdown": 4, "brightness": 100,
        "disable_hardware_pulsing": False,
    }


class MatrixDisplay:
    def __init__(self, width: int, height: int, multiplexing: int = 0, **geometry):
        from PIL import Image
        from rgbmatrix import RGBMatrix, RGBMatrixOptions   # built on the Pi from source

        opts = RGBMatrixOptions()
        for key, value in matrix_options(width, height, multiplexing, **geometry).items():
            setattr(opts, key, value)
        self._image = Image
        self.matrix = RGBMatrix(options=opts)
        self.canvas = self.matrix.CreateFrameCanvas()

    def push(self, frame: np.ndarray) -> None:
        self.canvas.SetImage(self._image.fromarray(frame))
        self.canvas = self.matrix.SwapOnVSync(self.canvas)

    def set_brightness(self, level: float) -> None:
        self.matrix.brightness = int(round(level * 100))

    def close(self) -> None:
        self.matrix.Clear()
```

Modify `show/display/__init__.py`: add before the final `raise`:

```python
    if cfg.backend == "matrix":
        from show.display.matrix import MatrixDisplay
        return MatrixDisplay(cfg.width, cfg.height, cfg.matrix_multiplexing)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_matrix.py -v`
Expected: 2 passed

- [ ] **Step 5: Install the library on the Pi (document in deploy/README.md)**

Append to `deploy/README.md`:

```markdown
## Matrix backup path (Active-3 adapter, no Colorlight)

    sudo apt install -y python3-dev cython3 libgraphicsmagick++-dev
    git clone https://github.com/hzeller/rpi-rgb-led-matrix /home/pi/rpi-rgb-led-matrix
    cd /home/pi/rpi-rgb-led-matrix && make build-python PYTHON=/home/pi/codeisart/.venv/bin/python
    sudo make install-python PYTHON=/home/pi/codeisart/.venv/bin/python

Add `isolcpus=3` to `/boot/firmware/cmdline.txt` and `dtparam=audio=off` to config.txt.
The daemon must run as root for this backend: set `User=root` in show.service.
Set `matrix_multiplexing` in show.toml to whichever value makes the `index` test pattern read correctly on 1/8-scan outdoor panels (try 0 through 17).
```

- [ ] **Step 6: Commit**

```bash
git add show/display/matrix.py show/display/__init__.py tests/test_matrix.py deploy/README.md
git commit -m "feat: rpi-rgb-led-matrix backup display backend"
```

---

### Task 18: Test pattern tool and hardware bring-up

**Files:**
- Create: `tools/test_pattern.py`
- Test: `tests/test_pattern_tool.py`

**Interfaces:**
- Consumes: `Font`, `draw_text`, `make_display`, `load_config`.
- Produces: `make_pattern(name: str, width: int, height: int, font: Font) -> np.ndarray` for names `index`, `white`, `rgb`, `grid`; CLI `python tools/test_pattern.py --pattern rgb --backend ddp --brightness 0.2`.

Patterns: `index` outlines each 64x32 module and labels it `r,c` (proves mapping and chain order), `white` is full white (dead pixel hunt, run at low brightness), `rgb` is red, green, blue vertical thirds (proves channel order), `grid` is one-pixel lines every 8 px (proves alignment and tearing).

- [ ] **Step 1: Write the failing tests**

`tests/test_pattern_tool.py`:

```python
import sys

import numpy as np

sys.path.insert(0, "tools")
from test_pattern import make_pattern  # noqa: E402


def test_rgb_thirds(font):
    f = make_pattern("rgb", 512, 192, font)
    assert tuple(f[0, 0]) == (255, 0, 0)
    assert tuple(f[0, 256]) == (0, 255, 0)
    assert tuple(f[0, 511]) == (0, 0, 255)


def test_white_and_grid(font):
    assert make_pattern("white", 512, 192, font).min() == 255
    g = make_pattern("grid", 512, 192, font)
    assert g[0].all() and g[8].all() and not g[4, 4].any()


def test_index_outlines_modules(font):
    f = make_pattern("index", 512, 192, font)
    assert f[0, :64].any(axis=1).all()          # top border of module 0,0
    assert f[31, :64].any(axis=1).all()         # bottom border
    assert f[:32, 63].any(axis=1).all()         # right border
    assert not f[16, 40].any()                  # interior mostly dark


def test_unknown_pattern(font):
    import pytest
    with pytest.raises(ValueError):
        make_pattern("plaid", 512, 192, font)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_pattern_tool.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'test_pattern'`

- [ ] **Step 3: Implement the tool**

`tools/test_pattern.py`:

```python
"""Push a diagnostic pattern to the wall until Ctrl-C.

Usage: python tools/test_pattern.py --pattern index|white|rgb|grid [--backend ddp] [--brightness 0.2]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from show.config import load_config          # noqa: E402
from show.display import make_display        # noqa: E402
from show.font import Font                   # noqa: E402
from show.renderer import draw_text          # noqa: E402

MODULE_W, MODULE_H = 64, 32


def make_pattern(name: str, width: int, height: int, font: Font) -> np.ndarray:
    frame = np.zeros((height, width, 3), np.uint8)
    if name == "white":
        frame[:] = 255
    elif name == "rgb":
        third = width // 3
        frame[:, :third] = (255, 0, 0)
        frame[:, third : 2 * third] = (0, 255, 0)
        frame[:, 2 * third :] = (0, 0, 255)
    elif name == "grid":
        frame[::8, :] = 255
        frame[:, ::8] = 255
    elif name == "index":
        for r in range(height // MODULE_H):
            for c in range(width // MODULE_W):
                y, x = r * MODULE_H, c * MODULE_W
                frame[y, x : x + MODULE_W] = (0, 90, 0)
                frame[y + MODULE_H - 1, x : x + MODULE_W] = (0, 90, 0)
                frame[y : y + MODULE_H, x] = (0, 90, 0)
                frame[y : y + MODULE_H, x + MODULE_W - 1] = (0, 90, 0)
                draw_text(frame, x + 4, y + 4, f"{r},{c}", font, (255, 255, 255))
    else:
        raise ValueError(f"unknown pattern {name!r}")
    return frame


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, default=Path("show.toml"))
    p.add_argument("--pattern", default="index", choices=["index", "white", "rgb", "grid"])
    p.add_argument("--backend", default=None)
    p.add_argument("--brightness", type=float, default=None)
    args = p.parse_args(argv)
    cfg = load_config(args.config)
    if args.backend:
        cfg.backend = args.backend
    if args.brightness is not None:
        cfg.brightness = args.brightness
    display = make_display(cfg)
    display.set_brightness(cfg.effective_brightness)
    frame = make_pattern(args.pattern, cfg.width, cfg.height, Font.load(cfg.font_path))
    print(f"pushing {args.pattern} at brightness {cfg.effective_brightness:.2f}; Ctrl-C to stop")
    try:
        while True:
            display.push(frame)
            time.sleep(1 / 30)
    except KeyboardInterrupt:
        return 0
    finally:
        display.close()


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_pattern_tool.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add tools/test_pattern.py tests/test_pattern_tool.py
git commit -m "feat: hardware test pattern tool"
```

- [ ] **Step 6: Two-module bring-up (hardware, week 2)**

No tests; record results in `deploy/README.md` under a "Bring-up log" heading and commit.

1. Wire 2 modules in one chain to port 1 of the 5A-75E, 5 V supply, Ethernet from the Pi.
2. Install Falcon Player on the Pi. In FPP, add a channel output of type "ColorLight 5A-75", panel size 64x32, layout 2 wide x 1 high, 1/8 scan. Enable DDP input.
3. Run `python tools/test_pattern.py --backend ddp --pattern rgb --brightness 0.1`. Expect red, green, blue thirds. If the colors are swapped, change the color order in FPP's panel settings, not in this code.
4. Run `--pattern index`. Expect `0,0` on the left module, `0,1` on the right, text upright. Fix orientation in FPP.
5. Run `python -m show.main --backend ddp` and press a button (or key `1` if an SDL window is attached). Expect the hello entry.
6. Raw path: `sudo setcap cap_net_raw+ep $(readlink -f .venv/bin/python)`, stop FPP, run `--backend colorlight --pattern rgb`. If nothing lights or colors are wrong, compare `show/display/colorlight.py` constants against the chubby75 notes and FPP source and fix them. Commit the fix.
7. Backup path: move the modules to the Active-3 adapter, run `--backend matrix --pattern index`, try `matrix_multiplexing` values until the pattern reads correctly.
8. Decide the primary path, set `backend` in `show.toml`, and note refresh quality (phone camera flicker) for each path.

---

### Task 19: Entry curation and fallback recordings

**Files:**
- Create: `entries/<slug>/` for five IOCCC entries, each with the original source, `entry.toml`, and `fallback.cast`
- Modify: `deploy/README.md` (curation notes)

No unit tests; the pipeline tests already cover the machinery. Each entry is validated by running it through the real show.

- [ ] **Step 1: Pick five entries**

Criteria: terminal output that fits 80x24, builds on a current gcc (possibly with flags such as `-w -std=gnu89 -fno-strict-aliasing`), runs without input, and looks alive for 10 to 30 seconds. Good sources: the IOCCC winners archive at `https://www.ioccc.org/years.html`. Prefer entries whose source is itself visual art (shaped code), since that is what goes on the portraits. Record the author name exactly as credited; it goes on the plaque.

- [ ] **Step 2: Create each entry directory**

For each entry, with `<slug>` a short lowercase name:

```
entries/<slug>/<original>.c      the source exactly as published
entries/<slug>/entry.toml
```

`entry.toml` template:

```toml
title = "<entry title or year/name>"
author = "<author as credited>"
year = 1998
station = 2                      # 1..5, unique
source = "<original>.c"
build = "gcc -w -std=gnu89 -o prog <original>.c -lm"
run = "./prog"
build_seconds = 60
run_seconds = 20
```

Verify on the laptop: `python -m show.main --backend sdl --play <slug>`. Adjust flags until the build succeeds and the run looks right. Reassign `station` so the five entries cover 1 through 5.

- [ ] **Step 3: Capture fallback recordings**

For each entry: `python -m show.main --backend fake --capture --play <slug>`. Confirm `entries/<slug>/fallback.cast` exists and replay it by temporarily breaking the build (`build = "false"`), running `--backend sdl --play <slug>`, and watching the recording play after the error hold. Restore the build line.

- [ ] **Step 4: Run the full suite and commit**

```bash
pytest -q
git add entries deploy/README.md
git commit -m "feat: five curated IOCCC entries with fallback recordings"
```

Keep `entries/hello` for tests and demos without occupying a portrait: set its `station = 6` in `entries/hello/entry.toml` and change the assertion in `tests/test_entries.py::test_sample_entry_loads` to `e.station == 6`.

---

## Hardware milestones (from the spec schedule)

These are not code tasks. They gate the software tasks above and are tracked here so the plan is the single checklist.

- [ ] **Week 1 (Sep 22 to 28):** Order 54 P5 outdoor 64x32 modules from a US stock seller, 2 more from a fast-shipping seller for the prototype, one 5A-75E plus a spare 5A-75B, Pi 4 (4 GB), Active-3 adapter, six 5 V 300 W rain-rated supplies, fuses, HUB75 ribbons. Check for US stock P6 modules; switch only if delivery is under one week. Software Tasks 1 to 7 land this week.
- [ ] **Week 2 (Sep 29 to Oct 5):** Software Tasks 8 to 15 land; show runs in the SDL preview. Task 18 bring-up on 2 modules; primary drive path chosen.
- [ ] **Week 3 (Oct 6 to 12):** Frame and sealed cabinet built with drip roof. Order portrait prints and lightboxes. Assemble five 4-conductor station cables, optoisolator input board, MOSFET LED board. Tasks 16, 17, 19 land.
- [ ] **Week 4 (Oct 13 to 19):** Test every module on arrival with the `white` pattern at 0.1 brightness. Mount all 48. Wire six row chains and six supplies. Run `index` on the full wall; fix chain order in FPP.
- [ ] **Week 5 (Oct 20 to 26):** Buttons, lights, audio integrated on the Pi. Overnight soak: buttons pressed by a cron script every 3 minutes, `journalctl` and `vcgencmd measure_temp` logged. Zero restarts expected.
- [ ] **Week 6 (Oct 27 to Nov 2):** Hose test 15 minutes while running. Pack spares (6 modules, 1 card, 1 supply, ribbons, fuses). Transport rig.
- [ ] **Week 7 (Nov 3 to 10):** Buffer. Final `show.toml` brightness set on a dark night.
- [ ] **Nov 11:** Install.
