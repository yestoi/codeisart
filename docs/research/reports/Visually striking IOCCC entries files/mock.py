"""Mock the five picks on the 128x64 PoC: Q53's 21x8 text window vs an 'ink' mode (one terminal cell -> one dot)."""
import sys
from pathlib import Path

import numpy as np
import pyte

REPO = Path("/Users/trey/dev/codeisart")
sys.path.insert(0, str(REPO))
from show.font import Font                      # noqa: E402
from tools.show_shot import sheet, save_png     # noqa: E402

S = Path(__file__).resolve().parents[1]
GREEN = np.array((51, 255, 51), dtype=np.float64)
W, H = 128, 64

font = Font.load(REPO / "fonts/5x7.bin")
atlas = font.atlas()                             # (256, 8, 6) bool
cover = atlas.reshape(256, -1).mean(axis=1)
cover = np.clip(cover / cover[ord("@")], 0, 1)   # '@' is full brightness


def screen_from(data: bytes, pick: float = 0.6) -> pyte.Screen:
    scr = pyte.Screen(80, 24)
    scr.set_mode(pyte.modes.LNM)
    st = pyte.ByteStream(scr)
    homes = [i for i in range(len(data)) if data.startswith(b"\x1b[H", i)]
    if len(homes) > 3:
        k = int(len(homes) * pick)
        data = data[: homes[k + 1]]
    st.feed(data)
    return scr


def codes_of(scr: pyte.Screen, rows: int = 23) -> np.ndarray:
    c = np.full((rows, 80), 32, dtype=np.intp)
    for y in range(rows):
        for x, ch in scr.buffer[y].items():
            if x < 80 and ch.data:
                o = ord(ch.data[0])
                c[y, x] = o if o < 256 else ord("?")
    return c


def to_rgb(level: np.ndarray) -> np.ndarray:
    return (level[:, :, None] * GREEN).astype(np.uint8)


def window(codes: np.ndarray) -> np.ndarray:
    """Q53: a 21x8 window of the 80x23 terminal in the 6x8 font, centred on the ink."""
    ys, xs = np.nonzero(codes != 32)
    cy, cx = (int(ys.mean()), int(xs.mean())) if len(ys) else (11, 40)
    y0 = min(max(cy - 4, 0), codes.shape[0] - 8)
    x0 = min(max(cx - 10, 0), 80 - 21)
    sub = codes[y0:y0 + 8, x0:x0 + 21]
    px = atlas[sub].transpose(0, 2, 1, 3).reshape(64, 126) * 0.7
    out = np.zeros((H, W))
    out[:, 1:127] = px
    return to_rgb(out)


RAMP = ".,-~:;=!*#$@"          # the donut's own luminance ramp
ramp_lv = np.zeros(256)
for i, ch in enumerate(RAMP):
    ramp_lv[ord(ch)] = 0.15 + 0.85 * i / (len(RAMP) - 1)


def ink(codes: np.ndarray, px_per_col: float, ramp: bool = False) -> np.ndarray:
    """One cell -> one dot whose brightness is that glyph's ink (or the donut ramp); cells keep the font's 6:8 shape."""
    lv = ramp_lv[codes] if ramp else cover[codes]
    ch_px = px_per_col * 8 / 6
    ow = min(W, int(round(80 * px_per_col)))
    oh = min(H, int(round(codes.shape[0] * ch_px)))
    cols_seen = ow / px_per_col
    rows_seen = oh / ch_px
    c0 = (80 - cols_seen) / 2
    r0 = max(0.0, (codes.shape[0] - rows_seen) / 2)
    xs = np.clip((c0 + (np.arange(ow) + 0.5) / px_per_col).astype(int), 0, 79)
    ys = np.clip((r0 + (np.arange(oh) + 0.5) / ch_px).astype(int), 0, codes.shape[0] - 1)
    out = np.zeros((H, W))
    oy, ox = (H - oh) // 2, (W - ow) // 2
    out[oy:oy + oh, ox:ox + ow] = lv[np.ix_(ys, xs)]
    return to_rgb(out)


PICKS = [
    ("donut.c (blog, 2006)", S / "dn/out.txt"),
    ("2006/sloane donut", S / "r9606/out/sloane.raw"),
    ("1992/imc mandelbrot", S / "out/imc92.txt"),
    ("2000/thadgavin plasma", S / "r9606/out/thadgavin.raw"),
    ("2012/endoh1 fluid", S / "poc/endoh1.raw"),
    ("2020/endoh3 clock", S / "runs/2020_endoh3/out.raw"),
]

frames = []
for name, path in PICKS:
    codes = codes_of(screen_from(path.read_bytes()))
    frames += [
        (f"{name}: 21x8 text window (Q53)", window(codes)),
        (f"{name}: ink, full 80x23", ink(codes, 1.6)),
        (f"{name}: ink 2x, centre 64x24", ink(codes, 2.0)),
    ]
    if "donut" in name:
        frames[-1] = (f"{name}: donut ramp, full 80x23", ink(codes, 1.6, ramp=True))
    (Path(__file__).parent / f"{name.split()[0].replace('/', '_')}.txt").write_text(
        "\n".join("".join(chr(c) for c in row) for row in codes))

out = Path(__file__).parent
for look in ("led", "distance"):
    img = sheet(frames, look, 4, f"Five picks on the 128x64 PoC ({look} look)", 2.2, 3)
    save_png(img, out / f"poc-{look}.png", "mock")
print("ok")
