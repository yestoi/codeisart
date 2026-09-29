"""Step 6 of the spike's brief: what timing Linux gives on the wall's port.

Runs send.py once for each way of waiting (sleep, hybrid, spin), of scheduling (plain, chrt -f 50) and of
queueing (the port's queue, PACKET_QDISC_BYPASS), with the kernel's and the port's transmit stamps, and
prints one table. The packets are the base's, the picture is dim (pixel 25). As root, on the Omarchy box:

    sudo .venv/bin/python tools/sender_spike/timing_matrix.py --iface enp5s0 --out timing-$(date +%F-%H%M)

The port needs a link for the driver's and the port's stamps: for this measurement the wall's cable goes
into another gigabit port (a switch, a laptop), not into the card. Without a link only the loop's own clock
and the time of entering the queue are measured, and the runs that bypass the queue fail.
"""
import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SEND = os.path.join("tools", "sender_spike", "send.py")


def commands(iface, python, out, seconds, dry_run=False):
    """[(name, argv)]: the twelve runs with the sync on the tick, then two in the base's order.
    A dry matrix opens no socket: the loop's clock alone, and the queue is left out."""
    runs = [(wait, sched, queue, "sync-rows") for wait in ("sleep", "hybrid", "spin")
            for sched in ("other", "fifo50") for queue in (("qdisc",) if dry_run else ("qdisc", "bypass"))]
    runs += [("hybrid", sched, "qdisc", "rows-sync") for sched in ("other", "fifo50")]
    out_runs = []
    for wait, sched, queue, order in runs:
        name = "-".join([wait, sched, queue] + (["rows-sync"] if order == "rows-sync" else []))
        argv = (["chrt", "-f", "50"] if sched == "fifo50" else []) + [
            python, SEND, "--iface", iface, "--order", order, "--wait", wait,
            "--dry-run" if dry_run else "--stamp-hw", "--pixel", "25",
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
    return got


def table(rows, fps):
    """Markdown. sd and worst (the interval furthest from the period) are in microseconds."""
    period = 1000 / fps
    head = ["run", "scheduling", "late", "not ours", "loop sd", "loop worst", "driver sd", "driver worst",
            "driver stamps", "port sd", "port worst", "port stamps", "queue max"]
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
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def link(iface):
    try:
        with open("/sys/class/net/%s/carrier" % iface) as f:
            return f.read().strip() == "1"
    except OSError:
        return False


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    a.add_argument("--iface", default="enp5s0")
    a.add_argument("--out", required=True, help="a directory for each run's output and log")
    a.add_argument("--seconds", type=float, default=10)
    a.add_argument("--python", default=sys.executable)
    a.add_argument("--dry-run", action="store_true", help="no socket, no root: the loop's clock alone")
    args = a.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    if not args.dry_run:
        print("timing_matrix: %s has %s" % (args.iface, "a link" if link(args.iface) else
                                            "NO LINK: only the loop's clock will be measured"), flush=True)
    rows = []
    for name, cmd in commands(args.iface, args.python, args.out, args.seconds, args.dry_run):
        print("timing_matrix: %s" % name, flush=True)
        done = subprocess.run(cmd, cwd=os.path.dirname(os.path.dirname(HERE)), capture_output=True, text=True)
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
