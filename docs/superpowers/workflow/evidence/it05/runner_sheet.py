"""Operator's sheet: the Strobe test game's raw frames vs what the runner pushed, ticks 0-39, 128x32."""
import subprocess, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, ".")
from tests.arcade.helpers import make_cfg
from tests.arcade.test_headless import Strobe, stand
from arcade.headless import run_headless
from arcade.look import render
from show.font import Font

sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
font = Font.load("fonts/5x7.bin")
frames, r = run_headless(make_cfg((128, 32)), font, Strobe, stand(90), raw=True)
raw = r.raw_frames
S, cols, n0, n = 2, 4, 0, 40
cw, ch = 128 * S + 6, 32 * S + 16
sheet = Image.new("RGB", (cols * 2 * cw + 20, (n // cols) * ch + 30), (40, 40, 60))
d = ImageDraw.Draw(sheet)
d.text((4, 4), f"it05 runner path, Strobe game, 128x32, HEAD {sha}: left pair = raw | pushed, per tick", fill=(255, 255, 0))
for k in range(n):
    i = n0 + k
    row, col = divmod(k, cols)
    x, y = col * 2 * cw + (20 if col else 0) * 0 + col * 5, 30 + row * ch
    for j, f in enumerate((raw[i], frames[i])):
        img = Image.fromarray(render(f, "plain", S))
        sheet.paste(img, (x + j * cw, y + 10))
    d.text((x, y), f"t{i} raw", fill=(200, 200, 200)); d.text((x + cw, y), "pushed", fill=(120, 220, 120))
sheet.save(sys.argv[1])
lum = lambda fs: "".join("#" if f.mean() > 128 else ("+" if f.mean() > 8 else ".") for f in fs[:90])
print("HEAD", sha)
print("raw    ", lum(raw))
print("pushed ", lum(frames))
print("held", r.governor.held_ticks, "of", len(frames))
