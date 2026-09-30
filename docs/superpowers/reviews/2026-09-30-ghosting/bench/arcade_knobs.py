"""Bench (2026-09-30, not part of the repo): arcade_load.py with the sender child at a chosen rate, as ghost_knobs.py
does for ghost_map.py: the child is ghost_child.py (the repo sender with GHOST_FPS), everything else the arcade.

    cd ~/codeisart && sudo .venv/bin/python ~/bench/arcade_knobs.py --out-fps 60 --wall --seconds 40
"""
import os
import runpy
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path.cwd()
if not (ROOT / "tools" / "wall_pattern.py").is_file():
    raise SystemExit("arcade_knobs: run it from the repository (cd ~/codeisart)")
sys.path.insert(0, str(ROOT))

argv = sys.argv[1:]
KNOBS = {"--out-fps": "GHOST_FPS", "--counter": "GHOST_COUNTER", "--spread-ms": "GHOST_SPREAD_MS", "--order": "GHOST_ORDER"}
while argv and argv[0] in KNOBS:
    os.environ[KNOBS[argv[0]]] = argv[1]
    argv = argv[2:]

from show.display import colorlight as cl  # noqa: E402


def spawn_bench_sender(slot, sock):
    fd = sock.fileno()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    child = [sys.executable, str(HERE / "ghost_child.py"), slot.path, str(slot.width), str(slot.height), str(fd),
             str(int(sock.family)), str(int(sock.type)), str(sock.proto), str(os.getpid()), str(slot.fd)]
    fds = (fd, slot.fd) if fd >= 0 else (slot.fd,)
    return cl.SenderProcess(subprocess.Popen(child, pass_fds=fds, env=env, cwd=str(ROOT)))


init = cl.ColorlightDisplay.__init__
if init.__kwdefaults__ and "launch" in init.__kwdefaults__:
    init.__kwdefaults__["launch"] = spawn_bench_sender
else:
    raise SystemExit("arcade_knobs: ColorlightDisplay launch default not found")
print("arcade_knobs: the S2 format, %s frames a second, counter %s" % (
    os.environ.get("GHOST_FPS", "60.00"), os.environ.get("GHOST_COUNTER", "on")), flush=True)
sys.argv = [str(HERE / "arcade_load.py"), *argv]
runpy.run_path(str(HERE / "arcade_load.py"), run_name="__main__")
