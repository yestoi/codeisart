"""Bench (2026-09-30 evening, not part of the repo): pictures pushed straight into the colorlight driver, no governor,
no arcade, no wall_pattern: ColorlightDisplay itself, one push a tick on absolute deadlines. To rule the arcade's
stack out of the flicker seen on the lobby.

    cd ~/codeisart && sudo .venv/bin/python ~/bench/direct_play.py video --file ~/bench/rick.mp4 --seconds 30
    ... scroll --seconds 30            # the spike's bars at pixel 128 moving 8 px/s
    ... slide --seconds 30             # ~/bench/lobby.png sliding sideways 10 px/s
    ... --dry-run                      # the driver on a socket that discards: no card, no root
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, "/home/trey/codeisart")

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from show.display.colorlight import ColorlightDisplay, DiscardSocket, stats_line  # noqa: E402

W, H = 128, 64


def bars(pixel=128):
    cols = np.array([(pixel, 0, 0), (0, pixel, 0), (0, 0, pixel), (pixel, pixel, pixel)], np.uint8)
    row = np.repeat(cols, W // 4, axis=0)
    return np.repeat(row[None, :, :], H, axis=0)


def video_frames(path, fps):
    cmd = ["ffmpeg", "-v", "error", "-stream_loop", "-1", "-i", str(path), "-r", str(fps),
           "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = W * H * 3
    try:
        while True:
            buf = p.stdout.read(n)
            if len(buf) < n:
                return
            yield np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    finally:
        p.kill()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=("video", "scroll", "slide", "vframe", "noise", "gradient", "toggle", "jump"))
    ap.add_argument("--file", default="/home/trey/bench/rick.mp4")
    ap.add_argument("--png", default="/home/trey/bench/lobby.png")
    ap.add_argument("--seconds", type=float, default=30.0)
    ap.add_argument("--fps", type=float, default=30.0, help="pushes a second")
    ap.add_argument("--brightness", type=float, default=0.1)
    ap.add_argument("--pixel", type=int, default=128)
    ap.add_argument("--speed", type=float, default=None, help="px/s: scroll 8, slide 10")
    ap.add_argument("--iface", default="eth0")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out-fps", help="the sender's rate (bench child): 60.00 unless set")
    ap.add_argument("--sync-reps", help="syncs a frame (bench child): 1 unless set")
    ap.add_argument("--counter", help="on or off (bench child)")
    ap.add_argument("--spread-ms", help="rows spread over this many ms after the sync (bench child); 15.5 unless set; 0 is a burst")
    ap.add_argument("--order", help="sync-rows or rows-sync (bench child)")
    a = ap.parse_args()
    if a.out_fps or a.sync_reps or a.counter or a.spread_ms or a.order:
        import os, subprocess as sp
        from show.display import colorlight as cl
        if a.out_fps:
            os.environ["GHOST_FPS"] = a.out_fps
        if a.sync_reps:
            os.environ["GHOST_SYNC_REPS"] = a.sync_reps
        if a.counter:
            os.environ["GHOST_COUNTER"] = a.counter
        if a.spread_ms:
            os.environ["GHOST_SPREAD_MS"] = a.spread_ms
        if a.order:
            os.environ["GHOST_ORDER"] = a.order
        root, here = Path("/home/trey/codeisart"), Path(__file__).resolve().parent

        def spawn_bench_sender(slot, sock):
            fd = sock.fileno()
            env = dict(os.environ)
            env["PYTHONPATH"] = str(root) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
            child = [sys.executable, str(here / "ghost_child.py"), slot.path, str(slot.width), str(slot.height),
                     str(fd), str(int(sock.family)), str(int(sock.type)), str(sock.proto), str(os.getpid()),
                     str(slot.fd)]
            fds = (fd, slot.fd) if fd >= 0 else (slot.fd,)
            return cl.SenderProcess(sp.Popen(child, pass_fds=fds, env=env, cwd=str(root)))
        cl.ColorlightDisplay.__init__.__kwdefaults__["launch"] = spawn_bench_sender
        print(f"direct_play: bench child, rate {os.environ.get('GHOST_FPS', '60.00')}, syncs a frame "
              f"{os.environ.get('GHOST_SYNC_REPS', '1')}, counter {os.environ.get('GHOST_COUNTER', 'on')}, "
              f"spread {os.environ.get('GHOST_SPREAD_MS', '15.5')} ms, order {os.environ.get('GHOST_ORDER', 'sync-rows')}", flush=True)
    if not 0 <= a.brightness <= 0.4:
        raise SystemExit("brightness is 0 to 0.4")
    if not 0 <= a.pixel <= 255:
        raise SystemExit("pixel is 0 to 255")

    if a.what == "video":
        src = video_frames(a.file, a.fps)
        def frame(t):
            return next(src)
    elif a.what == "vframe":                                   # one frame of the video, 2 s in, held still
        src = video_frames(a.file, a.fps)
        for _ in range(int(2 * a.fps)):
            still = next(src)
        still = still.copy()
        def frame(t):
            return still
    elif a.what == "noise":                                    # every pixel a new random value each push, 0 to pixel
        rng = np.random.default_rng(1)
        def frame(t):
            return rng.integers(0, a.pixel + 1, (H, W, 3), dtype=np.uint8)
    elif a.what == "toggle":                                   # a band at pixel on black; the black at 12 on odd pushes
        base = np.zeros((H, W, 3), np.uint8)
        base[:, W // 2 - 16 : W // 2 + 16, :] = a.pixel                 # a white band, 32 wide, its pixels never change
        lifted = base.copy()
        lifted[base == 0] = 12
        def frame(t):
            return lifted if int(round(t * a.fps)) % 2 else base
    elif a.what == "jump":                                     # a 4-px white bar at pixel, 32 px further on every push
        def frame(t):
            f = np.zeros((H, W, 3), np.uint8)
            x = (int(round(t * a.fps)) * 32) % W
            f[:, x : x + 4, :] = a.pixel
            return f
    elif a.what == "gradient":                                 # a still: red across, green down, blue diagonal
        xs = np.linspace(0, a.pixel, W, dtype=np.float32)
        ys = np.linspace(0, a.pixel, H, dtype=np.float32)
        g = np.zeros((H, W, 3), np.uint8)
        g[..., 0] = xs[None, :]
        g[..., 1] = ys[:, None]
        g[..., 2] = ((xs[None, :] + ys[:, None]) / 2)
        def frame(t):
            return g
    elif a.what == "scroll":
        base, speed = bars(a.pixel), a.speed or 8.0
        def frame(t):
            return np.roll(base, int(t * speed) % W, axis=1)
    else:
        img = cv2.imread(a.png)
        if img is None:
            raise SystemExit(f"no picture at {a.png}")
        img = cv2.cvtColor(cv2.resize(img, (W, H), interpolation=cv2.INTER_NEAREST), cv2.COLOR_BGR2RGB)
        speed = a.speed or 10.0
        def frame(t):
            return np.roll(img, int(t * speed) % W, axis=1)

    kw = {"brightness": a.brightness}
    if a.dry_run:
        kw["sock"] = DiscardSocket()
    d = ColorlightDisplay(W, H, a.iface, **kw)
    print(f"direct_play: {a.what} for {a.seconds:g} s at {a.fps:g} pushes a second, level {a.brightness:g}, "
          f"no governor, straight into the driver", flush=True)
    period = 1.0 / a.fps
    t0 = time.perf_counter()
    n = 0
    try:
        while True:
            t = n * period
            if t >= a.seconds:
                break
            due = t0 + t
            while time.perf_counter() < due:
                time.sleep(min(0.002, max(0.0, due - time.perf_counter())))
            d.push(np.ascontiguousarray(frame(t)))
            n += 1
    except KeyboardInterrupt:
        pass
    finally:
        d.push(np.zeros((H, W, 3), np.uint8))
        d.close()
        print(f"pushed {n} frames in {time.perf_counter() - t0:.1f} s")
        print(stats_line(d) or "no stats")


if __name__ == "__main__":
    main()
