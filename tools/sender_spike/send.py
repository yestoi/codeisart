"""Spike sender: the test sender's loop (cl_fpp_test.py) with one flag for each thing the S2 sender card does.

With no flags it sends what cl_fpp_test.py sends, at 60 frames a second: brightness x2, the rows, sync x2,
idle. Each flag changes one thing. The brief: docs/superpowers/specs/2026-09-29-sender-card-spike.md.

    sudo .venv/bin/python tools/sender_spike/send.py --iface enp5s0                  # the base
    sudo .venv/bin/python tools/sender_spike/send.py --iface enp5s0 --source-type 00 # one variable
    .venv/bin/python tools/sender_spike/send.py --dry-run                            # no socket: timing only

Offsets count from the start of the Ethernet frame (the packet type is byte 12).
Sends packet types 0x01, 0x55 and 0x0A and no other. Needs CAP_NET_RAW (sudo) unless --dry-run.
"""
import argparse
import gc
import math
import os
import random
import struct
import sys
import time
from dataclasses import dataclass, field, replace

DST = bytes.fromhex("112233445566")
SRC = bytes.fromhex("222233445566")
W, H = 128, 64
SYNC, BRIGHTNESS, ROW = 0x01, 0x0A, 0x55

SCROLL_PIXELS_A_SECOND = 8
PICTURES = ("bars", "scroll")

LEVEL_CAP = 0.4        # the old cap: never a level above it
BASE_PIXEL = 128       # the test sender's bars
DIM_PIXEL = 25         # safety rule 3: the most a pixel holds while the card's brightness is in doubt
ROOM_MS = 1.0          # kept free in each period for the rows to go out
LATE_NS = 1_000_000    # a frame that starts this long after it was due is counted as late


@dataclass(frozen=True)
class SyncSpec:
    """The sync packet's fields. The defaults are the test sender's at 10 % brightness."""
    source_type: int = 0x07           # byte 13
    counter: bool = False             # byte 14 counts the frames
    counter_start: int = 0
    bytes16: bytes = b"\x00\x00\x00"  # bytes 16 to 18
    byte26: int = 0x00
    declared_rate: bytes = b"\x00\x00"  # bytes 31, 32
    level: int = 25                   # byte 35, and bytes 38 to 40
    byte36: int = 0x05
    mark37_every: int = 0             # byte 37 is 1 in every nth sync; 0: never
    length: int = 112


# The S2's header in a sync of the test sender's length, and the S2's sync as captured.
S2_HEADER = SyncSpec(source_type=0x00, counter=True, counter_start=189, bytes16=b"\xff\xff\xff", byte26=0x01,
                     declared_rate=b"\x01\x3c", level=0xFF, byte36=0x00)
S2_SYNC = SyncSpec(**{**S2_HEADER.__dict__, "length": 1036})


def sync_packet(spec, frame):
    p = bytearray(spec.length)
    p[0:6], p[6:12], p[12], p[13] = DST, SRC, SYNC, spec.source_type
    if spec.counter:
        p[14] = (spec.counter_start + frame) % 256
    p[16:19] = spec.bytes16
    p[26] = spec.byte26
    p[31:33] = spec.declared_rate
    p[35] = spec.level
    p[36] = spec.byte36
    if spec.mark37_every and frame and frame % spec.mark37_every == 0:
        p[37] = 1
    p[38] = p[39] = p[40] = spec.level
    return bytes(p)


def brightness_packet(level):
    p = bytearray(77)
    p[0:6], p[6:12], p[12] = DST, SRC, BRIGHTNESS
    p[13] = p[14] = p[15] = level
    p[16] = 0xFF
    return bytes(p)


def row_packets(rows, tail=b"\x08\x88"):
    """One packet a row. `rows` is H rows of W * 3 bytes, in the order they go on the wire."""
    out = []
    for y, row in enumerate(rows):
        head = DST + SRC + bytes([ROW, y >> 8, y & 0xFF, 0, 0, W >> 8, W & 0xFF]) + tail
        out.append(head + bytes(row))
    return out


def bars(level):
    cols = [(level, 0, 0), (0, level, 0), (0, 0, level), (level, level, level)]
    row = b"".join(bytes(cols[x // 32]) for x in range(W))
    return [row] * H


def black():
    return [bytes(W * 3)] * H


def picture(kind, level, frame, fps):
    """The rows of one frame. "scroll" is the bars moving right, 8 pixels a second."""
    rows = bars(level)
    if kind == "bars":
        return rows
    shift = int(frame / fps * SCROLL_PIXELS_A_SECOND) % W
    row = rows[0]
    row = row[len(row) - shift * 3:] + row[:len(row) - shift * 3]
    return [row] * H


@dataclass(frozen=True)
class Plan:
    """One run. The defaults are the base: the test sender at 60 frames a second."""
    sync: SyncSpec = SyncSpec()
    sync_reps: int = 2
    bright_reps: int = 2
    bright_level: int = 25            # the byte of the 0x0A packet
    row_tail: bytes = b"\x08\x88"     # bytes 19, 20 of a row packet
    order: str = "rows-sync"          # or "sync-rows": the sync on the tick, the rows right behind it
    gap_ms: float = 0.0               # rows-sync: the pause after the last row, before the sync
    fps: float = 60.0
    seconds: float = 10.0
    tail_seconds: float = 1.0         # black frames after the picture
    pixel: int = BASE_PIXEL
    picture: str = "bars"
    jitter_ms: float = 0.0            # each sync is held back by a random time up to this
    seed: int = 1
    wait: str = "hybrid"              # sleep, then busy-wait the last spin_ms; or "spin"; or "sleep"
    spin_ms: float = 2.0
    qdisc_bypass: bool = False
    level_field_proven: bool = False
    iface: str = "enp5s0"
    dry_run: bool = False
    log: str = ""
    stamp: str = ""                   # "sw": the kernel stamps each frame's first sync; "hw": the port too


def level_byte(level):
    return int(level * 255)


def brightness_in_doubt(plan):
    """True when the plan leaves the fields by which the base sets the wall's brightness."""
    return (plan.sync.source_type != 0x07 or plan.sync.byte36 != 0x05 or plan.bright_reps == 0
            or plan.sync.level > level_byte(LEVEL_CAP))


def pixel_cap(plan):
    if not brightness_in_doubt(plan):
        return BASE_PIXEL
    if plan.level_field_proven and plan.sync.level <= level_byte(LEVEL_CAP):
        return BASE_PIXEL
    return DIM_PIXEL


def check(plan):
    """Raise ValueError for a plan the brief's safety rules forbid, or that cannot be sent."""
    cap = level_byte(LEVEL_CAP)
    if plan.bright_level > cap:
        raise ValueError("the brightness packet's level is above the cap of %g" % LEVEL_CAP)
    if plan.sync.level > cap and not brightness_in_doubt(plan):
        raise ValueError("the sync's level is above the cap of %g" % LEVEL_CAP)
    if not 0 <= plan.pixel <= BASE_PIXEL:
        raise ValueError("--pixel is 0 to %d" % BASE_PIXEL)
    if plan.pixel > pixel_cap(plan):
        raise ValueError(
            "safety rule 3: this sync leaves the card's brightness in doubt, so a pixel holds %d or less "
            "(--level-field-proven lifts that, with the owner's word, while every level is within %g)"
            % (DIM_PIXEL, LEVEL_CAP))
    if not 15 <= plan.fps <= 240:
        raise ValueError("--fps is 15 to 240")
    if not 0 < plan.seconds <= 60:
        raise ValueError("--seconds is above 0 and at most 60")
    if not 0 <= plan.tail_seconds <= 5:
        raise ValueError("--tail-seconds is 0 to 5")
    if not 1 <= plan.sync_reps <= 3:
        raise ValueError("--sync-reps is 1 to 3: a frame has its sync")
    if not 0 <= plan.bright_reps <= 2:
        raise ValueError("--bright-reps is 0 to 2")
    if not 112 <= plan.sync.length <= 1514:
        raise ValueError("--sync-len is 112 to 1514")
    if not 0 <= plan.jitter_ms <= 5:
        raise ValueError("--jitter-ms is 0 to 5")
    if plan.gap_ms < 0 or (plan.gap_ms and plan.order != "rows-sync"):
        raise ValueError("--gap-ms is the pause between the rows and the sync: it needs --order rows-sync")
    if plan.gap_ms + plan.jitter_ms + ROOM_MS >= 1000 / plan.fps:
        raise ValueError("the gap, the jitter and %g ms for the rows do not fit in the period of %.3f ms"
                         % (ROOM_MS, 1000 / plan.fps))
    if not 0 < plan.spin_ms <= 5:
        raise ValueError("--spin-ms is above 0 and at most 5")
    if plan.stamp and plan.dry_run:
        raise ValueError("a dry run has no socket to stamp")
    return plan


def hex_bytes(flag, text, n):
    words = {2: "two", 3: "three"}[n]
    try:
        value = bytes.fromhex(text)
    except ValueError:
        value = b""
    if len(value) != n:
        raise ValueError("%s takes %s bytes of hex" % (flag, words))
    return value


def hex_byte(flag, text):
    try:
        value = int(text, 16)
    except ValueError:
        value = -1
    if not 0 <= value <= 255:
        raise ValueError("%s takes one byte of hex" % flag)
    return value


def parser():
    a = argparse.ArgumentParser(
        description="The test sender's loop with one flag for each thing the S2 sender card does.",
        epilog="With no flags: the base (cl_fpp_test.py at 60 fps). Sends for --seconds, then black.")
    a.add_argument("--iface", default="enp5s0")
    a.add_argument("--dry-run", action="store_true", help="no socket: the loop and its timing only")
    a.add_argument("--seconds", type=float, default=10.0)
    a.add_argument("--tail-seconds", type=float, default=1.0, help="black frames after the picture")
    a.add_argument("--fps", type=float, default=60.0)
    a.add_argument("--log", default="", help="write one line a frame to this file (CSV)")
    g = a.add_argument_group("the cycle")
    g.add_argument("--order", choices=("rows-sync", "sync-rows"),
                   help="rows-sync (the base): brightness, rows, sync. sync-rows: the sync on the tick, "
                        "brightness and rows right behind it, then idle")
    g.add_argument("--gap-ms", type=float, default=0.0, help="rows-sync: pause after the last row, before the sync")
    g.add_argument("--sync-reps", type=int, help="sync packets a frame (base 2, S2 1)")
    g.add_argument("--bright-reps", type=int, help="brightness packets a frame (base 2, S2 0)")
    g.add_argument("--jitter-ms", type=float, default=0.0,
                   help="hold each sync back by a random time from 0 to this")
    g.add_argument("--seed", type=int, default=1, help="of the random times")
    g = a.add_argument_group("the sync packet")
    g.add_argument("--s2-header", action="store_true", help="bytes 13 to 40 as the S2's; all else as the base")
    g.add_argument("--s2", action="store_true",
                   help="the whole imitation: --s2-header --sync-len 1036 --sync-reps 1 --bright-reps 0 "
                        "--row-tail 0000 --order sync-rows. The rate stays --fps")
    g.add_argument("--source-type", metavar="HEX", help="byte 13 (base 07, S2 00)")
    g.add_argument("--counter", choices=("on", "off"), help="byte 14 counts the frames (base off, S2 on)")
    g.add_argument("--bytes16", metavar="HEX", help="bytes 16 to 18 (base 000000, S2 ffffff)")
    g.add_argument("--byte26", metavar="HEX", help="byte 26 (base 00, S2 01)")
    g.add_argument("--declared-rate", metavar="HEX", help="bytes 31, 32 (base 0000, S2 013c)")
    g.add_argument("--byte36", metavar="HEX", help="byte 36 (base 05, S2 00)")
    g.add_argument("--sync-len", type=int, help="length of the sync packet (base 112, S2 1036)")
    g = a.add_argument_group("the rows and the picture")
    g.add_argument("--row-tail", metavar="HEX", help="bytes 19, 20 of a row packet (base 0888, S2 0000)")
    g.add_argument("--picture", choices=PICTURES, default="bars")
    g.add_argument("--pixel", type=int, help="the bars' value (base %d; %d while the card's brightness is "
                                             "in doubt)" % (BASE_PIXEL, DIM_PIXEL))
    g = a.add_argument_group("brightness (0 to 1, capped at %g)" % LEVEL_CAP)
    g.add_argument("--brightness", type=float, default=0.1, help="the level in both packets")
    g.add_argument("--sync-level", type=float, help="the sync's level alone (S2: 1.0, then pixels are dim)")
    g.add_argument("--bright-level", type=float, help="the brightness packet's level alone")
    g.add_argument("--level-field-proven", action="store_true",
                   help="the owner's word that a run has shown which level field the card obeys: "
                        "lifts the pixel cap of %d while every level is within the cap" % DIM_PIXEL)
    g = a.add_argument_group("timing")
    g.add_argument("--wait", choices=("hybrid", "spin", "sleep"), default="hybrid",
                   help="hybrid: sleep, then busy-wait the last --spin-ms. spin: busy-wait all of it")
    g.add_argument("--spin-ms", type=float, default=2.0)
    g.add_argument("--qdisc-bypass", action="store_true", help="PACKET_QDISC_BYPASS: past the port's queue")
    g.add_argument("--stamp", action="store_true",
                   help="the kernel stamps each frame's first sync as it enters the queue and as the driver "
                        "takes it; their intervals are printed")
    g.add_argument("--stamp-hw", action="store_true",
                   help="--stamp, and the port's own clock as the packet leaves (turns the port's "
                        "time stamping on for the run; needs CAP_NET_ADMIN)")
    return a


def plan_from(argv):
    """The plan the flags ask for. ValueError when the safety rules forbid it."""
    args = parser().parse_args(argv)
    for name in ("brightness", "sync_level", "bright_level"):
        level = getattr(args, name)
        if level is not None and not 0 <= level <= 1:
            raise ValueError("--%s is 0 to 1" % name.replace("_", "-"))
    if args.brightness > LEVEL_CAP:
        raise ValueError("--brightness is above the cap of %g" % LEVEL_CAP)
    s2ish = args.s2 or args.s2_header
    sync = S2_HEADER if s2ish else SyncSpec(level=level_byte(args.brightness))
    fields = {}
    if args.source_type is not None:
        fields["source_type"] = hex_byte("--source-type", args.source_type)
    if args.counter is not None:
        fields["counter"] = args.counter == "on"
    if args.bytes16 is not None:
        fields["bytes16"] = hex_bytes("--bytes16", args.bytes16, 3)
    if args.byte26 is not None:
        fields["byte26"] = hex_byte("--byte26", args.byte26)
    if args.declared_rate is not None:
        fields["declared_rate"] = hex_bytes("--declared-rate", args.declared_rate, 2)
    if args.byte36 is not None:
        fields["byte36"] = hex_byte("--byte36", args.byte36)
    if args.sync_level is not None:
        fields["level"] = level_byte(args.sync_level)
    if args.sync_len is not None:
        fields["length"] = args.sync_len
    elif args.s2:
        fields["length"] = S2_SYNC.length
    sync = replace(sync, **fields)

    def pick(value, s2_value, base_value):
        return value if value is not None else s2_value if args.s2 else base_value

    plan = Plan(
        sync=sync,
        sync_reps=pick(args.sync_reps, 1, 2),
        bright_reps=pick(args.bright_reps, 0, 2),
        bright_level=level_byte(args.brightness if args.bright_level is None else args.bright_level),
        row_tail=hex_bytes("--row-tail", pick(args.row_tail, "0000", "0888"), 2),
        order=pick(args.order, "sync-rows", "rows-sync"),
        gap_ms=args.gap_ms, fps=args.fps, seconds=args.seconds, tail_seconds=args.tail_seconds,
        picture=args.picture, jitter_ms=args.jitter_ms, seed=args.seed,
        wait=args.wait, spin_ms=args.spin_ms, qdisc_bypass=args.qdisc_bypass,
        level_field_proven=args.level_field_proven, iface=args.iface, dry_run=args.dry_run, log=args.log,
        stamp="hw" if args.stamp_hw else "sw" if args.stamp else "")
    plan = replace(plan, pixel=pixel_cap(plan) if args.pixel is None else args.pixel)
    return check(plan)


def describe(plan):
    """One line that names every variable of the run, for the report."""
    s = plan.sync
    sync = "sync x%d, %d bytes, source type 0x%02x, counter %s, bytes 16-18 %s, byte 26 %02x, " \
           "bytes 31-32 %s, level %d, byte 36 %02x" % (
               plan.sync_reps, s.length, s.source_type, "on" if s.counter else "off", s.bytes16.hex(),
               s.byte26, s.declared_rate.hex(), s.level, s.byte36)
    bright = "brightness packet x%d at %d" % (plan.bright_reps, plan.bright_level) if plan.bright_reps \
        else "no brightness packet"
    cycle = "order %s" % plan.order + (", gap %g ms" % plan.gap_ms if plan.gap_ms else "") \
        + (", jitter 0 to %g ms (seed %d)" % (plan.jitter_ms, plan.seed) if plan.jitter_ms else "")
    timing = "wait %s" % plan.wait + (" (spin %g ms)" % plan.spin_ms if plan.wait == "hybrid" else "") \
        + (", qdisc bypass" if plan.qdisc_bypass else "") \
        + {"": "", "sw": ", stamps", "hw": ", stamps with the port's clock"}[plan.stamp]
    return "%g fps for %g s, then %g s black; %s; %s; %s; row tail %s; %s at pixel %d; %s" % (
        plan.fps, plan.seconds, plan.tail_seconds, cycle, sync, bright,
        " ".join("%02x" % b for b in plan.row_tail), plan.picture, plan.pixel, timing)


def guard(packets):
    """Safety rule 1: nothing goes to the card but sync, rows and brightness. ValueError otherwise."""
    for p in packets:
        if len(p) < 21 or p[0:6] != DST or p[6:12] != SRC or p[12] not in (SYNC, ROW, BRIGHTNESS):
            raise ValueError("refused: only packet types 0x01, 0x55 and 0x0A go to the card, from %s to %s"
                             % (SRC.hex(), DST.hex()))
    return packets


@dataclass
class Log:
    """What the loop did, a value a frame. Times are time.perf_counter_ns values."""
    frames: int = 0                               # frames of the picture; the black ones follow
    ticks: list = field(default_factory=list)     # when the frame was due
    syncs: list = field(default_factory=list)     # when its first sync was handed over
    added: list = field(default_factory=list)     # the random time its sync was held back by
    bursts: list = field(default_factory=list)    # from its first packet to the end of its last
    late: int = 0                                 # frames that started after their tick
    interrupted: bool = False


def run(plan, send, now, wait):
    """Send the plan's picture, then black. `send` takes a packet, `now` gives ns, `wait` blocks until a ns."""
    check(plan)
    period = 1e9 / plan.fps
    n_picture = round(plan.seconds * plan.fps)
    n_black = round(plan.tail_seconds * plan.fps)
    jitter = random.Random(plan.seed)
    top, gap = int(plan.jitter_ms * 1e6), int(plan.gap_ms * 1e6)
    sync_first = plan.order == "sync-rows"

    bright = guard([brightness_packet(plan.bright_level)] * plan.bright_reps)
    pictures, body = {}, []
    for n in range(n_picture):
        rows = picture(plan.picture, plan.pixel, n, plan.fps)
        if rows[0] not in pictures:
            pictures[rows[0]] = bright + guard(row_packets(rows, plan.row_tail))
        body.append(pictures[rows[0]])
    dark = bright + guard(row_packets(black(), plan.row_tail))
    fixed = not plan.sync.counter and not plan.sync.mark37_every
    one = guard([sync_packet(plan.sync, 0)])
    syncs = [one * plan.sync_reps if fixed else guard([sync_packet(plan.sync, n)]) * plan.sync_reps
             for n in range(n_picture + n_black)]

    log = Log(frames=n_picture)

    def frame(n, tick, packets):
        added = jitter.randrange(top + 1) if top else 0
        due = tick + added if sync_first else tick
        wait(due)
        first = now()
        if first - due > LATE_NS:
            log.late += 1
        if sync_first:
            at = first
            for p in syncs[n]:
                send(p)
            for p in packets:
                send(p)
        else:
            for p in packets:
                send(p)
            if gap or added:
                wait(now() + gap + added)
            at = now()
            for p in syncs[n]:
                send(p)
        log.ticks.append(tick)
        log.syncs.append(at)
        log.added.append(added)
        log.bursts.append(now() - first)

    start = now() + int(period)
    done = 0
    try:
        for n in range(n_picture):
            frame(n, start + round(n * period), body[n])
            done = n + 1
    except KeyboardInterrupt:
        log.interrupted = True
        start = now() + int(period) - round(done * period)
    log.frames = done
    for n in range(done, done + n_black):
        frame(n, start + round(n * period), dark)
    return log


def waiter(kind, spin_ns, now, sleep):
    """The wait of the loop. sleep: one sleep, late by what the system adds. spin: busy-wait, a whole core.
    hybrid: sleep to spin_ns short of the target, busy-wait the rest."""
    def wait(target):
        if kind != "spin":
            ahead = target - now() - (spin_ns if kind == "hybrid" else 0)
            if ahead > 0:
                sleep(ahead / 1e9)
        if kind != "sleep":
            while now() < target:
                pass
    return wait


EDGES_US = (-2000, -1000, -500, -200, -100, -50, -20, 20, 50, 100, 200, 500, 1000, 2000)


def intervals(log):
    """From each sync of the picture to the next, ns."""
    syncs = log.syncs[:log.frames]
    return [b - a for a, b in zip(syncs, syncs[1:])]


def spread(values):
    if not values:
        return None
    ordered = sorted(values)
    mean = sum(ordered) / len(ordered)

    def rank(p):
        return ordered[max(0, math.ceil(p / 100 * len(ordered)) - 1)]

    return {"mean": mean, "sd": math.sqrt(sum((v - mean) ** 2 for v in ordered) / len(ordered)),
            "min": ordered[0], "max": ordered[-1], "p50": rank(50), "p99": rank(99)}


def histogram(values_ns):
    """[(label, count)] over EDGES_US: a value sits in the bin whose lower edge it has reached."""
    labels = ["below %d" % EDGES_US[0]]
    labels += ["%d to %d" % (a, b) for a, b in zip(EDGES_US, EDGES_US[1:])]
    labels += ["%d and above" % EDGES_US[-1]]
    counts = [0] * len(labels)
    for v in values_ns:
        counts[sum(1 for e in EDGES_US if v >= e * 1000)] += 1
    return list(zip(labels, counts))


def spread_line(title, values, unit_ns, digits, names=("mean", "sd", "min", "max", "p50", "p99")):
    s = spread(values)
    return "send: %s: %s" % (title, " ".join("%s %.*f" % (k, digits, s[k] / unit_ns) for k in names))


def report(plan, log):
    total = len(log.syncs)
    out = ["send: sent %d frames and %d black; %d late%s" % (
        log.frames, total - log.frames, log.late, "; interrupted" if log.interrupted else "")]
    gaps = intervals(log)
    if len(gaps) < 2:
        return "\n".join(out + ["send: too few frames to measure"])
    n = log.frames
    out.append("send: measured %.3f fps over the picture" % (len(gaps) * 1e9 / (log.syncs[n - 1] - log.syncs[0])))
    out.append(spread_line("sync to sync, ms", gaps, 1e6, 3))
    out.append("send: sync to sync less the period of %.3f ms, us: count" % (1000 / plan.fps))
    period = 1e9 / plan.fps
    out += ["    %-16s %6d" % row for row in histogram([g - period for g in gaps])]
    short = ("mean", "sd", "min", "max")
    out.append(spread_line("added to each sync, us", log.added[:n], 1e3, 1, short))
    own = [s - t - a for s, t, a in zip(log.syncs[:n], log.ticks[:n], log.added[:n])]
    out.append(spread_line("sync after its tick, less the added time, us", own, 1e3, 1))
    out.append(spread_line("burst, first packet to last, us", log.bursts[:n], 1e3, 1, short))
    return "\n".join(out)


def write_log(path, plan, log, stamps=None):
    """One line a frame. The loop's times count from the first tick; each stamp clock from its first stamp."""
    t0 = log.ticks[0] if log.ticks else 0
    kinds = [k for k in ("queue", "driver", "port") if (stamps or {}).get(k)]
    zero = {k: min(stamps[k].values()) for k in kinds}
    if "queue" in zero and "driver" in zero:
        zero["driver"] = zero["queue"]                    # one clock: keep the time in the queue readable
    with open(path, "w") as f:
        f.write("# %s\n" % describe(plan))
        f.write(",".join(["frame", "black", "tick_ns", "sync_ns", "added_ns", "burst_ns"]
                         + [k + "_ns" for k in kinds]) + "\n")
        for n, (tick, sync, added, burst) in enumerate(zip(log.ticks, log.syncs, log.added, log.bursts)):
            row = [n, int(n >= log.frames), tick - t0, sync - t0, added, burst]
            row += [stamps[k][n] - zero[k] if n in stamps[k] else "" for k in kinds]
            f.write(",".join(str(v) for v in row) + "\n")


SOL_PACKET, PACKET_QDISC_BYPASS = 263, 20
SOL_SOCKET, SO_TIMESTAMPING = 1, 37
MSG_DONTWAIT, MSG_ERRQUEUE = 0x40, 0x2000
SOF_TX_HARDWARE, SOF_TX_SOFTWARE, SOF_SOFTWARE, SOF_RAW_HARDWARE = 1 << 0, 1 << 1, 1 << 4, 1 << 6
SOF_OPT_ID, SOF_TX_SCHED, SOF_OPT_TSONLY, SOF_OPT_TX_SWHW = 1 << 7, 1 << 8, 1 << 11, 1 << 14
SIOCSHWTSTAMP, SIOCGHWTSTAMP, HWTSTAMP_TX_ON = 0x89B0, 0x89B1, 1
ENOMSG, SO_EE_ORIGIN_TIMESTAMPING, SCM_TSTAMP_SND, SCM_TSTAMP_SCHED = 42, 4, 0, 1


def parse_stamp(ancdata):
    """(frame, "queue" | "driver" | "port", ns) from one message of the socket's error queue, or None.
    queue: the packet entered the port's queue. driver: the driver took it. port: the port's clock as it left."""
    times = key = kind = None
    for level, option, data in ancdata:
        if (level, option) == (SOL_SOCKET, SO_TIMESTAMPING) and len(data) >= 48:
            t = struct.unpack("qqqqqq", data[:48])
            times = (t[0] * 10**9 + t[1], t[4] * 10**9 + t[5])
        elif len(data) >= 16:
            errno, origin, _, _, _, info, value = struct.unpack("IBBBBII", data[:16])
            if errno == ENOMSG and origin == SO_EE_ORIGIN_TIMESTAMPING:
                kind, key = info, value
    if times is None or key is None:
        return None
    software, hardware = times
    if kind == SCM_TSTAMP_SCHED and software:
        return key, "queue", software
    if kind == SCM_TSTAMP_SND and hardware:
        return key, "port", hardware
    if kind == SCM_TSTAMP_SND and software:
        return key, "driver", software
    return None


class Plain:
    """What the loop sends through, without stamps."""
    stamps = {}

    def __init__(self, send=lambda packet: None, close=lambda: None):
        self.send, self.close = send, close

    def drain(self):
        pass

    def draining(self, wait):
        return wait


class Stamper:
    """Sends through the socket; the first sync of each frame asks the kernel for its transmit stamps.
    The kernel numbers the packets that ask, from 0: that number is the frame."""

    def __init__(self, sock, hardware, close=None):
        self.sock, self.close = sock, close or sock.close
        self.stamps = {}
        self.last = None
        ask = SOF_TX_SCHED | SOF_TX_SOFTWARE | (SOF_TX_HARDWARE if hardware else 0)
        self.ask = [(SOL_SOCKET, SO_TIMESTAMPING, struct.pack("I", ask))]
        sock.setsockopt(SOL_SOCKET, SO_TIMESTAMPING,
                        SOF_SOFTWARE | SOF_RAW_HARDWARE | SOF_OPT_ID | SOF_OPT_TSONLY | SOF_OPT_TX_SWHW)

    def send(self, packet):
        kind = packet[12]
        if kind == SYNC and self.last != SYNC:
            self.sock.sendmsg([packet], self.ask)
        else:
            self.sock.send(packet)
        self.last = kind

    def drain(self):
        while True:
            try:
                _, ancdata, _, _ = self.sock.recvmsg(1, 512, MSG_ERRQUEUE | MSG_DONTWAIT)
            except BlockingIOError:
                return
            stamp = parse_stamp(ancdata)
            if stamp:
                self.stamps.setdefault(stamp[1], {})[stamp[0]] = stamp[2]

    def draining(self, wait):
        """The loop's wait, with the error queue emptied before it: the idle time pays for the reading."""
        def drain_and_wait(target):
            self.drain()
            wait(target)
        return drain_and_wait


def stamp_report(plan, frames, stamps):
    """The intervals between the syncs of the picture by the kernel's stamps."""
    out = []
    period = 1e9 / plan.fps
    for kind, where in (("driver", "at the driver"), ("port", "at the port")):
        got = stamps.get(kind, {})
        if not got and not (kind == "port" and plan.stamp == "hw"):
            continue
        out.append("send: %s: %d of %d stamps" % (kind, sum(1 for n in range(frames) if n in got), frames))
        gaps = [got[n + 1] - got[n] for n in range(frames - 1) if n in got and n + 1 in got]
        if len(gaps) < 2:
            continue
        out.append(spread_line("sync to sync %s, ms" % where, gaps, 1e6, 3))
        out.append("send: sync to sync %s less the period of %.3f ms, us: count" % (where, 1000 / plan.fps))
        out += ["    %-16s %6d" % row for row in histogram([g - period for g in gaps])]
    queue, driver = stamps.get("queue", {}), stamps.get("driver", {})
    held = [driver[n] - queue[n] for n in range(frames) if n in queue and n in driver]
    if held:
        out.append(spread_line("from the queue to the driver, us", held, 1e3, 1))
    return "\n".join(out) if out else "send: no stamps came back"


def hwtstamp(sock, iface, config=None):
    """The port's time stamp settings (flags, tx_type, rx_filter): read, or set to `config`."""
    import ctypes
    import fcntl
    cfg = ctypes.create_string_buffer(struct.pack("iii", *(config or (0, 0, 0))), 12)
    request = struct.pack("16sP", iface.encode(), ctypes.addressof(cfg)).ljust(40, b"\0")
    fcntl.ioctl(sock, SIOCSHWTSTAMP if config else SIOCGHWTSTAMP, request)
    return struct.unpack("iii", cfg.raw)


def open_socket(plan):
    """The sink of a raw socket on the plan's port. Linux only; needs CAP_NET_RAW."""
    import socket
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
    if plan.qdisc_bypass:
        s.setsockopt(SOL_PACKET, PACKET_QDISC_BYPASS, 1)
    s.bind((plan.iface, 0))
    if not plan.stamp:
        return Plain(s.send, s.close)
    close = s.close
    if plan.stamp == "hw":
        before = hwtstamp(s, plan.iface)
        hwtstamp(s, plan.iface, (0, HWTSTAMP_TX_ON, before[2]))

        def close():
            hwtstamp(s, plan.iface, before)               # leave the port as it was found
            s.close()
    return Stamper(s, plan.stamp == "hw", close)


def scheduling():
    if not hasattr(os, "sched_getscheduler"):
        return "not read on this system"
    names = {getattr(os, n): n for n in ("SCHED_OTHER", "SCHED_FIFO", "SCHED_RR", "SCHED_BATCH", "SCHED_IDLE")
             if hasattr(os, n)}
    policy = os.sched_getscheduler(0)
    return "%s priority %d, cpus %s" % (names.get(policy, policy), os.sched_getparam(0).sched_priority,
                                        ",".join(str(c) for c in sorted(os.sched_getaffinity(0))))


def port_counter(iface, root="/sys/class/net"):
    """How many packets the port has sent, or None where the system does not say."""
    try:
        with open(os.path.join(root, iface, "statistics", "tx_packets")) as f:
            return int(f.read())
    except (OSError, ValueError):
        return None


def main(argv=None, now=time.perf_counter_ns, sleep=time.sleep, open_sink=open_socket, port_counter=port_counter):
    argv = sys.argv[1:] if argv is None else argv
    try:
        plan = plan_from(argv)
    except ValueError as e:
        parser().error(str(e))
    print("send: %s" % describe(plan), flush=True)
    print("send: %s; scheduling: %s" % ("dry run, no socket" if plan.dry_run else "on " + plan.iface,
                                        scheduling()), flush=True)
    sink = Plain() if plan.dry_run else open_sink(plan)
    before = None if plan.dry_run else port_counter(plan.iface)
    gc.disable()
    try:
        log = run(plan, sink.send, now, sink.draining(waiter(plan.wait, int(plan.spin_ms * 1e6), now, sleep)))
        if plan.stamp:
            sleep(0.05)                                   # the last stamps are on their way
            sink.drain()
    finally:
        gc.enable()
        sink.close()
    print(report(plan, log), flush=True)
    after = None if before is None else port_counter(plan.iface)
    if after is not None:
        ours = len(log.syncs) * (plan.sync_reps + plan.bright_reps + H)
        print("send: the port sent %d packets during the run: %d ours, %d not ours"
              % (after - before, ours, after - before - ours), flush=True)
    if plan.stamp:
        print(stamp_report(plan, log.frames, sink.stamps), flush=True)
    if plan.log:
        write_log(plan.log, plan, log, sink.stamps)
        print("send: a line a frame in %s" % plan.log, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
