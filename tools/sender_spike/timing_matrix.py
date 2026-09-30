"""Step 6 of the spike's brief: what timing Linux gives on the wall's port.

Runs send.py once for each way of waiting (sleep, hybrid, spin), of scheduling (plain, chrt -f 50) and of
queueing (the port's queue, PACKET_QDISC_BYPASS), with the kernel's and the port's transmit stamps, and
prints one table. The packets are the base's, the picture is dim (pixel 25). As root, on the Omarchy box:

    sudo .venv/bin/python tools/sender_spike/timing_matrix.py --iface enp5s0 --card-unplugged \
        --out timing-$(date +%F-%H%M)

The port needs a link for the driver's and the port's stamps: for this measurement the wall's cable goes
into another gigabit port (a switch, a laptop), NOT into the card: twelve of the runs send the sync before
the rows, which the card has not seen yet. --card-unplugged is the owner's word that it is so. Without a
link only the loop's own clock and the time of entering the queue are measured, and the runs that bypass
the queue fail.

Where the busy-wait runs at real-time priority with the port's clock, stamps of the port may be missing:
the driver reads them in a task of ordinary priority, which the busy-wait holds off. That is the
measurement's doing, not the port's.
"""
import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SEND = os.path.join("tools", "sender_spike", "send.py")


def commands(iface, python, out, seconds, dry_run=False):
    """[(name, argv)]: the run sheet's own command first, to prove the stamps it uses; then the twelve
    runs with the sync on the tick; then the base's order, through the port's queue and past it, which
    shows whether the queue lets the sync overtake the rows ("order broken").
    A dry matrix opens no socket: the loop's clock alone, and the queue is left out."""
    runs = [(wait, sched, queue, "sync-rows") for wait in ("sleep", "hybrid", "spin")
            for sched in ("other", "fifo50") for queue in (("qdisc",) if dry_run else ("qdisc", "bypass"))]
    runs += [("hybrid", sched, "qdisc", "rows-sync") for sched in ("other", "fifo50")]
    if not dry_run:                               # the run sheet's own command, with the stamps it uses
        runs.insert(0, ("hybrid", "fifo50", "bypass", "stamp-sw"))
        runs.append(("hybrid", "fifo50", "bypass", "rows-sync"))
    out_runs = []
    for wait, sched, queue, order in runs:
        name = "-".join([wait, sched, queue] + ([order] if order != "sync-rows" else []))
        stamps = "--dry-run" if dry_run else "--stamp" if order == "stamp-sw" else "--stamp-hw"
        order = "rows-sync" if order == "stamp-sw" else order
        argv = (["chrt", "-f", "50"] if sched == "fifo50" else []) + [
            python, SEND, "--iface", iface, "--order", order, "--wait", wait, stamps, "--pixel", "25",
            "--seconds", "%g" % seconds, "--tail-seconds", "0.2", "--log", os.path.join(out, name + ".csv")]
        out_runs.append((name, argv + (["--qdisc-bypass"] if queue == "bypass" else [])))
    return out_runs


def numbers(line):
    return {name: float(value) for name, value in re.findall(r"(\w+) (-?[\d.]+)", line.split(": ", 2)[-1])}


def parse(text):
    """The numbers of one run of send.py, from what it printed."""
    got = {"stamps": {}}
    for line in text.splitlines():
        if "scheduling: " in line:
            got["scheduling"] = line.split("scheduling: ")[1]
        elif m := re.search(r"and \d+ black; (\d+) late", line):
            got["slips"] = int(s.group(1)) if (s := re.search(r"(\d+) slips", line)) else 0
            got["late"] = int(m.group(1))
        elif m := re.search(r"(\d+) not ours", line):
            got["not ours"] = int(m.group(1))
        elif m := re.search(r"send: (driver|port): (\d+) of (\d+) stamps", line):
            got["stamps"][m.group(1)] = (int(m.group(2)), int(m.group(3)))
        elif "sync to sync, ms" in line:
            got["loop"] = numbers(line)
        elif "sync to sync at the driver, ms" in line:
            got["driver"] = numbers(line)
        elif "sync to sync at the port, ms" in line:
            got["port"] = numbers(line)
        elif "from the queue to the driver, us" in line:
            got["queue"] = numbers(line)
        elif m := re.search(r"left before the (?:last row|sync) of its frame in (\d+) of (\d+) frames", line):
            got["overtaken"] = (int(m.group(1)), int(m.group(2)))
        elif m := re.search(r"queue held packets during the run: (\d+) requeues, (\d+) new flows", line):
            got["queue events"] = (int(m.group(1)), int(m.group(2)))
        elif "queue held no packet" in line:
            got["queue events"] = (0, 0)
    return got


def table(rows, fps):
    """Markdown. sd and worst (the interval furthest from the period) are in microseconds."""
    period = 1000 / fps
    head = ["run", "scheduling", "late", "not ours", "loop sd", "loop worst", "driver sd", "driver worst",
            "driver stamps", "port sd", "port worst", "port stamps", "queue max", "order broken", "queue held"]
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]

    def two(got, clock):
        s = got.get(clock)
        if not s:
            return ["", ""]
        return ["%.0f" % (s["sd"] * 1000), "%.0f" % (max(s["max"] - period, period - s["min"]) * 1000)]

    for name, got, error in rows:
        if got is None or "loop" not in got:
            out.append("| %s | failed: %s |" % (name, error.strip().splitlines()[-1] if error.strip() else "no output"))
            continue
        cells = [name, got.get("scheduling", ""), str(got.get("late", "")), str(got.get("not ours", ""))]
        cells += two(got, "loop")
        for clock in ("driver", "port"):
            stamps = got["stamps"].get(clock)
            cells += two(got, clock) + ["%d/%d" % stamps if stamps else ""]
        cells.append("%.1f" % got["queue"]["max"] if "queue" in got else "")
        cells.append("%d/%d" % got["overtaken"] if "overtaken" in got else "")
        cells.append("%d, %d" % got["queue events"] if "queue events" in got else "")
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def link(iface):
    try:
        with open("/sys/class/net/%s/carrier" % iface) as f:
            return f.read().strip() == "1"
    except OSError:
        return False


def main(argv=None, runner=subprocess.run):
    a = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    a.add_argument("--iface", default="enp5s0")
    a.add_argument("--out", required=True, help="a directory for each run's output and log")
    a.add_argument("--seconds", type=float, default=10)
    a.add_argument("--python", default=sys.executable)
    a.add_argument("--dry-run", action="store_true", help="no socket, no root: the loop's clock alone")
    a.add_argument("--card-unplugged", action="store_true",
                   help="the owner's word that the cable is in another port, not in the card")
    args = a.parse_args(argv)
    if not args.dry_run and not args.card_unplugged:
        a.error("the matrix sends the sync before the rows, which the card has not seen yet: put the wall's "
                "cable into another gigabit port and say so with --card-unplugged (or use --dry-run)")
    os.makedirs(args.out, exist_ok=True)
    if not args.dry_run:
        print("timing_matrix: %s has %s" % (args.iface, "a link" if link(args.iface) else
                                            "NO LINK: only the loop's clock will be measured"), flush=True)
    rows = []
    for name, cmd in commands(args.iface, args.python, args.out, args.seconds, args.dry_run):
        print("timing_matrix: %s" % name, flush=True)
        done = runner(cmd, cwd=os.path.dirname(os.path.dirname(HERE)), capture_output=True, text=True)
        with open(os.path.join(args.out, name + ".txt"), "w") as f:
            f.write("$ %s\n%s%s" % (" ".join(cmd), done.stdout, done.stderr))
        rows.append((name, parse(done.stdout) if done.returncode == 0 else None, done.stderr))
    text = table(rows, fps=60)
    with open(os.path.join(args.out, "table.md"), "w") as f:
        f.write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
