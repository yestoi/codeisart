"""Bench (2026-09-30, not part of the repo): ghost_map.py's pictures with the sender's cadence changed, one knob at
a time. The pictures still run through tools/wall_pattern.py's own governed run; only the child that puts the
frames on the wire is replaced by ghost_child.py (beside this file), which is the repo's sender with its sync
repeats, brightness-packet repeats and output rate taken from these flags.

    cd ~/codeisart && sudo .venv/bin/python ~/bench/ghost_knobs.py [--sync-reps N] [--bright-reps N] [--out-fps F] \
        8 --step 0 --row 18 --iface eth0 --seconds 20

Everything after the knobs is ghost_map.py's command line.
"""
import os
import runpy
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path.cwd()
if not (ROOT / "tools" / "wall_pattern.py").is_file():
    raise SystemExit("ghost_knobs: run it from the repository (cd ~/codeisart)")
sys.path.insert(0, str(ROOT))

KNOBS = {"--sync-reps": "GHOST_SYNC_REPS", "--bright-reps": "GHOST_BRIGHT_REPS", "--out-fps": "GHOST_FPS"}
argv = sys.argv[1:]
while argv and argv[0] in KNOBS:
    os.environ[KNOBS[argv[0]]] = argv[1]
    argv = argv[2:]

from show.display import colorlight as cl  # noqa: E402


def spawn_bench_sender(slot, sock):
    """cl.spawn_sender with ghost_child.py in place of the module: the same arguments, descriptors and environment."""
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
    raise SystemExit("ghost_knobs: ColorlightDisplay's launch default not found; the driver has changed")

print("ghost_knobs: sync x%s, brightness x%s, %s frames a second" % (
    os.environ.get("GHOST_SYNC_REPS", "2"), os.environ.get("GHOST_BRIGHT_REPS", "2"),
    os.environ.get("GHOST_FPS", "59")), flush=True)
sys.argv = [str(HERE / "ghost_map.py"), *argv]
runpy.run_path(str(HERE / "ghost_map.py"), run_name="__main__")
