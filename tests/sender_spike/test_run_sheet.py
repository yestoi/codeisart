"""Every command of the phase 1 run sheet is one the sender accepts: no minute at the wall lost to a typing error."""
import pathlib
import re
import shlex

import pytest

from tools.sender_spike import send

SHEET = pathlib.Path(__file__).resolve().parents[2] / "docs/superpowers/reviews/2026-09-29-sender-card-spike/01-run-sheet.md"
LAYOUTS = ["", "--order sync-rows", "--gap-ms 12"]
RATES = ["", "--fps 20"]
LIFT = "--pixel 128 --level-field-proven"
HELPER = {"run": "--qdisc-bypass --stamp", "plain": "--qdisc-bypass --stamp", "queued": "--stamp",
          "old": "--stamp"}


def commands():
    text = SHEET.read_text()
    found = re.findall(r"`(run|plain|queued|old) (\w+)((?: [^`;]*)?)(?:;[^`]*)?`", text)
    return [(name, (HELPER[helper] + " " + flags.strip()).strip()) for helper, name, flags in found
            if "..." not in flags and "$" not in flags]


def forms(flags):
    """The command with each thing its placeholders may stand for."""
    out = [flags]
    for word, values in (("LAYOUT", LAYOUTS), ("RATE", RATES)):
        out = [f.replace(word, v) for f in out for v in (values if word in f else [""])]
    return out


def test_the_sheet_has_its_runs():
    names = [name for name, flags in commands()]
    for name in ("A0", "A1", "A2", "A2q", "A3", "A4", "A5", "B1", "B3", "B4", "B6", "C1", "C2", "D0", "D1", "D2",
                 "L1", "L8", "E2", "F1", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9"):
        assert name in names, name
    assert len(names) == len(set(names)) >= 40             # a name is a file: none is used twice


def test_no_jitter_run_is_below_what_the_sender_can_hold():
    # step 6, 2026-09-29: the port's worst is 52 us; jitter below three times that cannot be told from none
    for name, flags in commands():
        plan = send.plan_from(shlex.split(forms(flags)[0]))
        assert plan.jitter_ms == 0 or plan.jitter_ms >= 0.16, name


def test_the_helpers_of_the_sheet_are_the_ones_the_test_knows():
    text = SHEET.read_text()
    assert "run()    { local n=$1; shift; sudo chrt -f 50 .venv/bin/python tools/sender_spike/send.py --iface enp5s0 \\\n" \
           "              --qdisc-bypass --stamp --log runs/$n.csv" in text
    assert "queued() { local n=$1; shift; sudo chrt -f 50 .venv/bin/python tools/sender_spike/send.py --iface enp5s0 \\\n" \
           "              --stamp --log runs/$n.csv" in text
    assert "plain()  { local n=$1; shift; sudo .venv/bin/python tools/sender_spike/send.py --iface enp5s0 \\\n" \
           "              --qdisc-bypass --stamp --log runs/$n.csv" in text
    assert "old()    { local n=$1; shift; sudo .venv/bin/python tools/sender_spike/send.py --iface enp5s0 \\\n" \
           "              --stamp --log runs/$n.csv" in text


@pytest.mark.parametrize("name, flags", commands())
def test_the_sender_accepts_the_command(name, flags):
    for form in forms(flags):
        if "--gap-ms 12" in form and "--fps 120" in form:
            continue                                        # the sheet says so: 12 ms does not fit in 8.3
        plan = send.plan_from(shlex.split(form))
        assert plan.seconds <= 10 and plan.iface == "enp5s0" and plan.stamp == "sw"
        assert plan.qdisc_bypass == (name not in ("A1", "A2q"))


@pytest.mark.parametrize("name, flags", [c for c in commands() if "--s2" in c[1] or "--source-type" in c[1]])
def test_the_dim_runs_are_dim_and_can_be_lifted_only_within_the_cap(name, flags):
    for form in forms(flags):
        plan = send.plan_from(shlex.split(form))
        assert plan.pixel == 25
        if plan.sync.level <= 102:
            assert send.plan_from(shlex.split(form + " " + LIFT)).pixel == 128
        else:
            with pytest.raises(ValueError, match="25"):
                send.plan_from(shlex.split(form + " " + LIFT))


def test_every_rung_but_the_last_has_the_dim_bases_light():
    by_name = dict(commands())
    for rung in ("L1", "L2", "L3", "L4", "L5", "L6", "L7"):
        for form in forms(by_name[rung]):
            plan = send.plan_from(shlex.split(form))
            assert (plan.sync.level, plan.pixel) == (25, 25), rung
    top = send.plan_from(shlex.split(forms(by_name["L8"])[0]))
    assert (top.sync.level, top.pixel) == (255, 25)


def test_the_ladder_adds_one_thing_a_rung():
    import dataclasses
    by_name = dict(commands())
    rungs = [send.plan_from(shlex.split(forms(by_name[n])[0]))
             for n in ("L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8")]
    base = send.plan_from(shlex.split(HELPER["run"] + " --pixel 25"))

    def flat(plan):
        d = dataclasses.asdict(plan)
        d.update({"sync." + k: v for k, v in d.pop("sync").items()})
        return d

    def step(a, b):
        return {k for k in flat(a) if flat(a)[k] != flat(b)[k]}

    assert step(base, rungs[0]) == {"sync.source_type"}
    assert step(rungs[0], rungs[1]) == {"sync.counter", "sync.counter_start", "sync.bytes16", "sync.byte26",
                                        "sync.declared_rate", "sync.byte36"}
    assert step(rungs[1], rungs[2]) == {"sync_reps"}
    assert step(rungs[2], rungs[3]) == {"bright_reps"}
    assert step(rungs[3], rungs[4]) == {"row_tail"}
    assert step(rungs[4], rungs[5]) == {"sync.length"}
    assert step(rungs[5], rungs[6]) == {"order"}
    assert step(rungs[6], rungs[7]) == {"sync.level"}
    assert step(rungs[7], send.plan_from(shlex.split(HELPER["run"] + " --s2"))) == set()


def test_the_helpers_run_in_bash_and_a_blind_pair_keeps_its_names(tmp_path):
    """The sheet's own helper text, with stand-ins for sudo and tee: a pair is two runs under the pair's name."""
    import subprocess
    text = SHEET.read_text()
    start = text.index("   run()    {")
    block = text[start:text.index("   ```", start)]
    script = ("sudo() { echo \"$*\" >> calls.txt; }\n" "tee() { if [ \"$1\" = -a ]; then cat >> \"$2\"; else cat > \"$2\"; fi; }\n" + block
              + "\nmkdir -p runs\nfor i in 1 2 3 4 5 6 7 8; do ab P$i '--order sync-rows' ''; done\n"
                "run A2\nold A1 --wait sleep\nsay A2 picture, none, clean\n")
    done = subprocess.run(["bash", "-c", script], cwd=tmp_path, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    calls = (tmp_path / "calls.txt").read_text().splitlines()
    pairs = [c for c in calls if "runs/P" in c]
    assert len(pairs) == 16
    for i in range(1, 9):
        first, second = pairs[2 * i - 2], pairs[2 * i - 1]
        assert "--log runs/P%d_1.csv" % i in first and "--log runs/P%d_2.csv" % i in second
        assert ("--order sync-rows" in first) != ("--order sync-rows" in second)
        order = (tmp_path / "runs" / ("P%d.order" % i)).read_text()
        assert order.startswith("1: --order sync-rows") == ("--order sync-rows" in first)
    assert "flags" not in done.stdout and "--order" not in done.stdout                   # a pair tells nothing
    assert calls[-2].startswith("chrt -f 50 .venv/bin/python tools/sender_spike/send.py --iface enp5s0 "
                                "--qdisc-bypass --stamp --log runs/A2.csv")
    assert calls[-1] == (".venv/bin/python tools/sender_spike/send.py --iface enp5s0 "
                         "--stamp --log runs/A1.csv --wait sleep")
    assert "A2 picture, none, clean" in (tmp_path / "runs" / "verdicts.txt").read_text()


def test_the_short_form_compares_like_with_like():
    import dataclasses
    by_name = {n: send.plan_from(shlex.split(f)) for n, f in commands() if n in ["S%d" % i for i in range(1, 10)]}
    assert len(by_name) == 9
    s1, s2, s3, s4, s5, s6, s7, s8, s9 = (by_name["S%d" % i] for i in range(1, 10))
    for test, control in ((s4, s3), (s7, s6)):             # the same rate, the same light
        assert (test.fps, test.pixel, test.sync.level) == (control.fps, control.pixel, control.sync.level)
    assert (s4.fps, s7.fps) == (20, 60)
    for whole in (s4, s7):                                 # the S2's packets, order and single sync
        assert whole.sync == dataclasses.replace(send.S2_SYNC, level=25)
        assert (whole.sync_reps, whole.bright_reps, whole.row_tail, whole.order) == (1, 0, b"\x00\x00", "sync-rows")
    assert s8.sync == send.S2_SYNC and s8.fps == 60.32 and s8.pixel == 25     # the capture, byte for byte
    assert s5 == s3 and s9 == s1                           # the controls are the runs they repeat
    assert (s2.fps, s2.pixel) == (20, 128)                 # the run on record as flickering
    assert s1 == send.plan_from(shlex.split(HELPER["run"]))
