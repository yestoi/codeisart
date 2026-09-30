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
import re
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


def picture(kind, level, frame, fps, speed=SCROLL_PIXELS_A_SECOND):
    """The rows of one frame. "scroll" is the bars moving right, `speed` pixels a second."""
    rows = bars(level)
    if kind == "bars":
        return rows
    shift = int(frame / fps * speed) % W
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
    scroll: int = SCROLL_PIXELS_A_SECOND  # pixels a second of the moving picture
    jitter_ms: float = 0.0            # each frame, its sync with it, is held back by a random time up to this
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
    """True when a packet holds anything the base's does not, or the brightness packet is gone.
    What the fields mean is not known, so what the card then does with the brightness is not known."""
    base = SyncSpec(level=plan.sync.level, counter_start=plan.sync.counter_start)
    return (plan.sync != base or plan.row_tail != Plan.row_tail or plan.bright_reps == 0
            or plan.sync.level > level_byte(LEVEL_CAP))


def pixel_cap(plan):
    if not brightness_in_doubt(plan):
        return BASE_PIXEL
    if plan.level_field_proven and plan.sync.level <= level_byte(LEVEL_CAP):
        return BASE_PIXEL
    return DIM_PIXEL


# A field takes the values seen on the wire (the base's and the S2's) and the brief's H3, and no other:
# the card is the only good one, and nobody knows what another value would ask of it.
SEEN = {
    "--source-type": (0x07, 0x00),
    "--bytes16": (b"\x00\x00\x00", b"\xff\xff\xff"),
    "--byte26": (0x00, 0x01),
    "--declared-rate": (b"\x00\x00", b"\x01\x3c", b"\x01\x1e"),
    "--byte36": (0x05, 0x00),
    "--row-tail": (b"\x08\x88", b"\x00\x00"),
    "--sync-len": (112, 1036),
}
SEEN_AS = {"--source-type": "00 or 07", "--bytes16": "000000 or ffffff", "--byte26": "00 or 01",
           "--declared-rate": "0000, 013c or 011e", "--byte36": "00 or 05", "--row-tail": "0888 or 0000",
           "--sync-len": "112 or 1036"}


def seen(flag, value):
    if value not in SEEN[flag]:
        raise ValueError("%s is %s: the values seen on the wire, and no other" % (flag, SEEN_AS[flag]))
    return value


def check(plan):
    """Raise ValueError for a plan the brief's safety rules forbid, or that cannot be sent."""
    cap = level_byte(LEVEL_CAP)
    for flag, value in (("--source-type", plan.sync.source_type), ("--bytes16", plan.sync.bytes16),
                        ("--byte26", plan.sync.byte26), ("--declared-rate", plan.sync.declared_rate),
                        ("--byte36", plan.sync.byte36), ("--row-tail", plan.row_tail),
                        ("--sync-len", plan.sync.length)):
        seen(flag, value)
    if plan.sync.mark37_every:
        raise ValueError("byte 37 is not sent: what it asks of a card is not known (the owner's word first)")
    if not 0 <= plan.bright_level <= cap:
        raise ValueError("the brightness packet's level is above the cap of %g" % LEVEL_CAP)
    if not 0 <= plan.sync.level <= 255:
        raise ValueError("the sync's level is a byte")
    if plan.sync.level > cap and plan.sync.source_type != 0x00:
        raise ValueError("the sync's level is above the cap of %g: only the S2's own sync (source type 00) "
                         "carries its 0xff, and then the pixels are dim" % LEVEL_CAP)
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
    if not 0 <= plan.jitter_ms <= 5:
        raise ValueError("--jitter-ms is 0 to 5")
    if not 1 <= plan.scroll <= 64:
        raise ValueError("--scroll is 1 to 64 pixels a second: no pixel changes colour faster than twice a second")
    if not 0 <= plan.gap_ms < 1000:
        raise ValueError("--gap-ms is 0 or more, and less than the period")
    if plan.gap_ms and plan.order != "rows-sync":
        raise ValueError("--gap-ms is the pause between the rows and the sync: it needs --order rows-sync")
    if plan.gap_ms + plan.jitter_ms + ROOM_MS >= 1000 / plan.fps:
        raise ValueError("the gap, the jitter and %g ms for the rows do not fit in the period of %.3f ms"
                         % (ROOM_MS, 1000 / plan.fps))
    if not 0 < plan.spin_ms <= 5:
        raise ValueError("--spin-ms is above 0 and at most 5")
    if plan.stamp and plan.dry_run:
        raise ValueError("a dry run has no socket to stamp")
    return plan


def hex_bytes(flag, text):
    try:
        return seen(flag, bytes.fromhex(text))
    except ValueError:
        return seen(flag, None)


def hex_byte(flag, text):
    try:
        return seen(flag, int(text, 16))
    except ValueError:
        return seen(flag, None)


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
                   help="hold each frame, and its sync with it, back by a random time from 0 to this")
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
    g.add_argument("--declared-rate", metavar="HEX", help="bytes 31, 32 (base 0000, S2 013c; 011e for H3)")
    g.add_argument("--byte36", metavar="HEX", help="byte 36 (base 05, S2 00)")
    g.add_argument("--sync-len", type=int, help="length of the sync packet (base 112, S2 1036)")
    g = a.add_argument_group("the rows and the picture")
    g.add_argument("--row-tail", metavar="HEX", help="bytes 19, 20 of a row packet (base 0888, S2 0000)")
    g.add_argument("--picture", choices=PICTURES, default="bars")
    g.add_argument("--scroll", type=int, default=SCROLL_PIXELS_A_SECOND,
                   help="pixels a second of the moving picture (a bar is 32 wide; at most 64)")
    g.add_argument("--pixel", type=int, help="the bars' value (base %d; %d while the card's brightness is "
                                             "in doubt)" % (BASE_PIXEL, DIM_PIXEL))
    g = a.add_argument_group("brightness (0 to 1, capped at %g)" % LEVEL_CAP)
    g.add_argument("--brightness", type=float, default=0.1, help="the level in both packets")
    g.add_argument("--sync-level", type=float,
                   help="the sync's level alone. --brightness does not reach an S2-style sync, which carries "
                        "its own 1.0; this flag does")
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
        fields["bytes16"] = hex_bytes("--bytes16", args.bytes16)
    if args.byte26 is not None:
        fields["byte26"] = hex_byte("--byte26", args.byte26)
    if args.declared_rate is not None:
        fields["declared_rate"] = hex_bytes("--declared-rate", args.declared_rate)
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
        row_tail=hex_bytes("--row-tail", pick(args.row_tail, "0000", "0888")),
        order=pick(args.order, "sync-rows", "rows-sync"),
        gap_ms=args.gap_ms, fps=args.fps, seconds=args.seconds, tail_seconds=args.tail_seconds,
        picture=args.picture, scroll=args.scroll, jitter_ms=args.jitter_ms, seed=args.seed,
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
    proven = ", level field proven (the owner's word)" if plan.level_field_proven else ""
    shown = plan.picture + (" at %d px/s" % plan.scroll if plan.picture == "scroll" else "")
    return "%g fps for %g s, then %g s black; %s; %s; %s; row tail %s; %s at pixel %d%s; %s" % (
        plan.fps, plan.seconds, plan.tail_seconds, cycle, sync, bright,
        " ".join("%02x" % b for b in plan.row_tail), shown, plan.pixel, proven, timing)


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
    slips: int = 0                                # times the grid was moved, a frame being a period late
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

    bright = [brightness_packet(plan.bright_level)] * plan.bright_reps
    pictures, body = {}, []
    for n in range(n_picture):
        rows = picture(plan.picture, plan.pixel, n, plan.fps, plan.scroll)
        if rows[0] not in pictures:
            pictures[rows[0]] = bright + row_packets(rows, plan.row_tail)
        body.append(pictures[rows[0]])
    dark = bright + row_packets(black(), plan.row_tail)
    fixed = not plan.sync.counter and not plan.sync.mark37_every
    one = [sync_packet(plan.sync, 0)] * plan.sync_reps
    syncs = [one if fixed else [sync_packet(plan.sync, n)] * plan.sync_reps for n in range(n_picture + n_black)]
    for packets in list(pictures.values()) + [dark] + ([one] if fixed else syncs):
        guard(packets)                            # everything the loop will send, before it sends anything

    log = Log(frames=n_picture)
    moved = 0                                     # what the slips have added to the grid

    def frame(n, tick, packets):
        nonlocal moved
        added = jitter.randrange(top + 1) if top else 0
        tick += moved
        due = tick + added                        # jitter holds the whole frame back, in either order:
        behind = now() - due                      # a pause between rows and sync would be a second variable
        if behind > period:                       # set aside for a period or more: move the grid,
            moved, tick, due = moved + behind, tick + behind, due + behind    # never catch up in a burst
            log.slips += 1
            log.late += 1
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
            if gap:
                wait(now() + gap)
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
        start, moved = now() + int(period) - round(done * period), 0
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
    out = ["send: sent %d frames and %d black; %d late; %d slips%s" % (
        log.frames, total - log.frames, log.late, log.slips, "; interrupted" if log.interrupted else "")]
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
    kinds = [k for k in ("queue", "driver", "port", "queue-row", "driver-row", "port-row")
             if (stamps or {}).get(k)]
    zero = {}
    for k in kinds:                                       # the kernel's clock has one zero, the port's another
        clock = "port" if k.startswith("port") else "kernel"
        zero[clock] = min(zero.get(clock, stamps[k][min(stamps[k])]), min(stamps[k].values()))
    if "queue" in kinds:
        zero["kernel"] = min(stamps["queue"].values())    # the first sync entering the queue
    with open(path, "w") as f:
        f.write("# %s\n" % describe(plan))
        f.write(",".join(["frame", "black", "tick_ns", "sync_ns", "added_ns", "burst_ns"]
                         + [k.replace("-", "_") + "_ns" for k in kinds]) + "\n")
        for n, (tick, sync, added, burst) in enumerate(zip(log.ticks, log.syncs, log.added, log.bursts)):
            row = [n, int(n >= log.frames), tick - t0, sync - t0, added, burst]
            row += [stamps[k][n] - zero["port" if k.startswith("port") else "kernel"] if n in stamps[k] else ""
                    for k in kinds]
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
    """Sends through the socket. The last row and the first sync of each frame ask the kernel for their
    transmit stamps, so that the order in which the two left can be read. The kernel numbers the packets
    that ask, from 0; `asked` says which packet each number was."""

    def __init__(self, sock, hardware, close=None):
        self.sock, self.close = sock, close or sock.close
        self.stamps = {}                  # "queue", "driver", "port" of the sync, and the same with "-row"
        self.asked = []                   # ("sync" | "row", frame) for each packet that asked, in order
        self.count = {"sync": 0, "row": 0}
        self.last = None
        kernel = SOF_TX_SCHED | SOF_TX_SOFTWARE
        # The port stamps one packet at a time: its clock is kept for the sync. The row asks the kernel alone.
        self.ask = {"sync": [(SOL_SOCKET, SO_TIMESTAMPING,
                              struct.pack("I", kernel | (SOF_TX_HARDWARE if hardware else 0)))],
                    "row": [(SOL_SOCKET, SO_TIMESTAMPING, struct.pack("I", kernel))]}
        sock.setsockopt(SOL_SOCKET, SO_TIMESTAMPING,
                        SOF_SOFTWARE | SOF_RAW_HARDWARE | SOF_OPT_ID | SOF_OPT_TSONLY | SOF_OPT_TX_SWHW)

    def send(self, packet):
        kind = packet[12]
        what = ("sync" if kind == SYNC and self.last != SYNC
                else "row" if kind == ROW and packet[13] == 0 and packet[14] == H - 1 else None)
        if what:
            self.asked.append((what, self.count[what]))
            self.count[what] += 1
            self.sock.sendmsg([packet], self.ask[what])
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
            if stamp and stamp[0] < len(self.asked):
                what, frame = self.asked[stamp[0]]
                self.stamps.setdefault(stamp[1] + ("-row" if what == "row" else ""), {})[frame] = stamp[2]

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
    rows = stamps.get("driver-row", {})
    behind = [driver[n] - rows[n] for n in range(frames) if n in rows and n in driver]
    if behind:                                    # the port's queue may let one packet overtake another
        out.append(spread_line("the sync behind the last row at the driver, us", behind, 1e3, 1))
        if plan.order == "rows-sync":
            out.append("send: the sync left before the last row of its frame in %d of %d frames"
                       % (sum(1 for b in behind if b < 0), len(behind)))
        else:
            out.append("send: the last row left before the sync of its frame in %d of %d frames"
                       % (sum(1 for b in behind if b > 0), len(behind)))
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


def tc(argv):
    import subprocess
    return subprocess.run(argv, capture_output=True, text=True, timeout=5).stdout


def queue_counter(iface, tc=tc):
    """(requeues, new flows) of the port's queue so far, as `tc -s` counts them, or None.
    Both stand still while packets go straight from the socket to the driver. They move when the port's
    queue held packets, and a queue that sorts by flow (fq_codel: the packet type is the flow) may then
    have let a sync overtake rows."""
    try:
        text = tc(["tc", "-s", "qdisc", "show", "dev", iface])
    except (OSError, ValueError, __import__("subprocess").SubprocessError):
        return None
    requeues = re.search(r"requeues (\d+)", text)
    flows = re.search(r"new_flow_count (\d+)", text)
    return (int(requeues.group(1)), int(flows.group(1))) if requeues and flows else None


def main(argv=None, now=time.perf_counter_ns, sleep=time.sleep, open_sink=open_socket, port_counter=port_counter,
         queue_counter=queue_counter):
    argv = sys.argv[1:] if argv is None else argv
    try:
        plan = plan_from(argv)
    except ValueError as e:
        parser().error(str(e))
    head = "send: %s\nsend: %s; scheduling: %s" % (
        describe(plan), "dry run, no socket" if plan.dry_run else "on " + plan.iface, scheduling())
    print(head, flush=True)
    sink = Plain() if plan.dry_run else open_sink(plan)
    before = None if plan.dry_run else port_counter(plan.iface)
    queue = None if plan.dry_run else queue_counter(plan.iface)
    gc.disable()
    try:
        log = run(plan, sink.send, now, sink.draining(waiter(plan.wait, int(plan.spin_ms * 1e6), now, sleep)))
        if plan.stamp:
            sleep(0.05)                                   # the last stamps are on their way
            sink.drain()
    finally:
        gc.enable()
        sink.close()
    text = [report(plan, log)]
    after = None if before is None else port_counter(plan.iface)
    if after is not None:
        ours = len(log.syncs) * (plan.sync_reps + plan.bright_reps + H)
        text.append("send: the port sent %d packets during the run: %d ours, %d not ours"
                    % (after - before, ours, after - before - ours))
    queue_after = None if queue is None else queue_counter(plan.iface)
    if queue_after is not None:
        held = (queue_after[0] - queue[0], queue_after[1] - queue[1])
        text.append("send: the port's queue held packets during the run: %d requeues, %d new flows; packets "
                    "may have left in another order than they were sent" % held if any(held)
                    else "send: the port's queue held no packet during the run")
    if plan.stamp:
        text.append(stamp_report(plan, log.frames, sink.stamps))
    if plan.log:                                          # the files first: a pipe's reader may be gone
        write_log(plan.log, plan, log, sink.stamps)
        kept = os.path.splitext(plan.log)[0] + ".report.txt"
        with open(kept, "w") as f:
            f.write("\n".join([head] + text) + "\n")
        text.append("send: a line a frame in %s, this report in %s" % (plan.log, kept))
    try:
        print("\n".join(text), flush=True)
    except BrokenPipeError:                               # Ctrl-C took `tee` too; the files have the run
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except (AttributeError, OSError, ValueError):
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
