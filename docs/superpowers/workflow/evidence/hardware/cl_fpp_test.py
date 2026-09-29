"""Throwaway: send R/G/B/W bars to a Colorlight card the way Falcon Player does for firmware 13+.

Per frame: brightness packet (x2 with --dup), all row packets, sync packet (x2 with --dup). Packet bytes are
the same as show/display/colorlight.py. Ends with black frames. Needs CAP_NET_RAW (sudo).

    sudo .venv/bin/python cl_fpp_test.py --iface enp5s0 --seconds 10          # FPP's firmware-13 order
    sudo .venv/bin/python cl_fpp_test.py --iface enp5s0 --seconds 10 --no-dup # same, single packets
"""
import argparse
import socket
import time

DST = bytes.fromhex("112233445566")
SRC = bytes.fromhex("222233445566")
W, H = 128, 64


def eth(t):
    return DST + SRC + t.to_bytes(2, "big")


def rows(frame):
    out = []
    for y in range(H):
        hdr = eth(0x5500 | (y >> 8)) + bytes([y & 0xFF, 0, 0, W >> 8, W & 0xFF, 0x08, 0x88])
        out.append(hdr + bytes(frame[y]))
    return out


def sync(b):
    p = bytearray(98)
    p[21] = b
    p[22] = 0x05
    p[24] = p[25] = p[26] = b
    return eth(0x0107) + bytes(p)


def bright(b):
    p = bytearray(63)
    p[0] = p[1] = b
    p[2] = 0xFF
    return eth(0x0A00 | b) + bytes(p)


def bars(level):
    cols = [(level, 0, 0), (0, level, 0), (0, 0, level), (level, level, level)]
    row = b"".join(bytes(cols[x // 32]) for x in range(W))
    return [row] * H


def wait_until(t, spin):
    if spin:
        while time.perf_counter() < t:
            pass
    else:
        time.sleep(max(0.0, t - time.perf_counter()))


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--iface", default="enp5s0")
    a.add_argument("--seconds", type=float, default=10)
    a.add_argument("--fps", type=float, default=20)
    a.add_argument("--brightness", type=float, default=0.1)
    a.add_argument("--no-dup", action="store_true")
    a.add_argument("--spin", action="store_true", help="busy-wait for the gap and the frame period")
    a.add_argument("--tail-seconds", type=float, default=1.0, help="black frames at --fps after the bars")
    a.add_argument("--sync-reps", type=int, default=0, help="show-frame packets per frame (0: as --no-dup says)")
    a.add_argument("--gap-ms", type=float, default=0.0, help="pause after the rows, before the sync")
    args = a.parse_args()
    b = int(min(args.brightness, 0.4) * 255)
    reps = 1 if args.no_dup else 2
    sreps = args.sync_reps or reps
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
    s.bind((args.iface, 0))
    pic = rows(bars(128))
    dark = rows([bytes(W * 3)] * H)
    n, end = 0, time.perf_counter() + args.seconds
    print(f"cl_fpp_test: bars at brightness {b}/255, brightness x{reps}, sync x{sreps}, "
          f"{args.seconds:g} s on {args.iface}", flush=True)
    while time.perf_counter() < end:
        t0 = time.perf_counter()
        for _ in range(reps):
            s.send(bright(b))
        for p in pic:
            s.send(p)
        if args.gap_ms:
            wait_until(time.perf_counter() + args.gap_ms / 1000, args.spin)
        for _ in range(sreps):
            s.send(sync(b))
        n += 1
        wait_until(t0 + 1 / args.fps, args.spin)
    end = time.perf_counter() + args.tail_seconds
    while time.perf_counter() < end:
        t0 = time.perf_counter()
        for _ in range(reps):
            s.send(bright(b))
        for p in dark:
            s.send(p)
        if args.gap_ms:
            wait_until(time.perf_counter() + args.gap_ms / 1000, args.spin)
        for _ in range(sreps):
            s.send(sync(b))
        wait_until(t0 + 1 / args.fps, args.spin)
    print(f"cl_fpp_test: sent {n} frames, then black", flush=True)


if __name__ == "__main__":
    main()
