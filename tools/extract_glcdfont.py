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
