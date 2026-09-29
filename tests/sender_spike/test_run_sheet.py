"""Every command of the phase 1 run sheet is one the sender accepts: no minute at the wall lost to a typing error."""
import pathlib
import re
import shlex

import pytest

from tools.sender_spike import send

SHEET = pathlib.Path(__file__).resolve().parents[2] / "docs/superpowers/reviews/2026-09-29-sender-card-spike/01-run-sheet.md"
LAYOUTS = ["", "--order sync-rows", "--gap-ms 12"]
LIFT = "--sync-level 0.1 --pixel 128 --level-field-proven"


def commands():
    text = SHEET.read_text()
    found = re.findall(r"`(run|plain) (\w+)((?: [^`;]*)?)(?:;[^`]*)?`", text)
    return [(name, flags.strip()) for helper, name, flags in found if "..." not in flags and "$" not in flags]


def test_the_sheet_has_its_runs():
    names = [name for name, flags in commands()]
    for name in ("A0", "A1", "A2", "A3", "B1", "B3", "B4", "B6", "C1", "C2", "D1", "D2", "L1", "L7", "E2", "F1"):
        assert name in names, name
    assert len(names) >= 30


@pytest.mark.parametrize("name, flags", commands())
def test_the_sender_accepts_the_command(name, flags):
    for layout in LAYOUTS if "LAYOUT" in flags else [""]:
        if layout == "--gap-ms 12" and "--fps 120" in flags:
            continue                                        # the sheet says so: 12 ms does not fit in 8.3
        plan = send.plan_from(shlex.split(flags.replace("LAYOUT", layout)))
        assert plan.seconds <= 10 and plan.iface == "enp5s0"


@pytest.mark.parametrize("name, flags", [c for c in commands() if "--s2" in c[1] or "--source-type" in c[1]])
def test_the_dim_runs_are_dim_and_can_be_lifted_only_within_the_cap(name, flags):
    assert send.plan_from(shlex.split(flags)).pixel == 25
    if "--sync-level" not in flags:
        lifted = send.plan_from(shlex.split(flags + " " + LIFT))
        assert lifted.pixel == 128 and lifted.sync.level == 25


def test_the_ladder_adds_one_thing_a_rung():
    import dataclasses
    by_name = dict(commands())
    rungs = [send.plan_from(shlex.split(by_name[n])) for n in ("L1", "L2", "L3", "L4", "L5", "L6", "L7")]
    base = send.plan_from(["--pixel", "25"])

    def flat(plan):
        d = dataclasses.asdict(plan)
        d.update({"sync." + k: v for k, v in d.pop("sync").items()})
        return d

    def step(a, b):
        return {k for k in flat(a) if flat(a)[k] != flat(b)[k]}

    assert step(base, rungs[0]) == {"sync.source_type"}
    assert step(rungs[0], rungs[1]) == {"sync.counter", "sync.counter_start", "sync.bytes16", "sync.byte26",
                                        "sync.declared_rate", "sync.level", "sync.byte36"}
    assert step(rungs[1], rungs[2]) == {"sync_reps"}
    assert step(rungs[2], rungs[3]) == {"bright_reps"}
    assert step(rungs[3], rungs[4]) == {"row_tail"}
    assert step(rungs[4], rungs[5]) == {"sync.length"}
    assert step(rungs[5], rungs[6]) == {"order"}
    assert rungs[6] == send.plan_from(["--s2"])
