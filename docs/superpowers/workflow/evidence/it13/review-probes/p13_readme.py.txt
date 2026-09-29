import sys; sys.path.insert(0, "/Users/trey/dev/codeisart")
import os
import subprocess
import tempfile

from show import main as show_main
from tools import show_soak, wall_pattern as wp

print("WATCHDOG_EVERY_S", show_main.WATCHDOG_EVERY_S)
a = show_soak.parse_args(["--minutes", "600", "--press-every", "180", "--real-devices"])
print("soak args", vars(a))
b = wp.build_parser().parse_args(["--config", "show.toml", "panels"])
print("pattern args", vars(b))
out = tempfile.mkdtemp()
env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
for pat in ("panels", "grid"):
    r = subprocess.run([sys.executable, "tools/wall_pattern.py", "--config", "show.toml", pat, "--png",
                        os.path.join(out, pat + ".png")], cwd="/Users/trey/dev/codeisart", env=env,
                       capture_output=True, text=True, timeout=60)
    print(pat, r.returncode, r.stdout.strip(), r.stderr.strip()[-200:])
    from PIL import Image
    print("  png size", Image.open(os.path.join(out, pat + ".png")).size)
