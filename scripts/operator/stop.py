#!/usr/bin/env python3
"""Stop hook for the arcade operator: keeps the loop running until it gates itself.

Allows the stop (exit 0, no output) when any of:
  - not the operator (OPERATOR=1 unset or state.md missing);
  - docs/superpowers/workflow/gate.md exists;
  - docs/superpowers/workflow/STOP exists (the owner's kill switch);
  - roadmap.md has no line matching '- [ ] M' (no unfinished milestone);
  - stop_hook_active is true and state.md says phase: gated;
  - the run's block counter in docs/superpowers/workflow/.blocks is at or above
    iterations-per-run from config.md (default 6).
Otherwise increments the counter and prints a block decision as JSON.

The counter is per run. The LOOP resets it when a gate is answered by deleting
docs/superpowers/workflow/.blocks (it is created here if missing, and ignored by git).
Any internal error allows the stop.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as c  # noqa: E402

DEFAULT_CAP = 6
UNCHECKED = re.compile(r"^\s*- \[ \] M", re.M)
CAP_LINE = re.compile(r"^\s*-\s*iterations-per-run:\s*(\d+)", re.M)


def read_cap():
    m = CAP_LINE.search(c.read_text(c.wf("config.md")) or "")
    return int(m.group(1)) if m else DEFAULT_CAP


def read_blocks():
    try:
        return int((c.read_text(c.wf(".blocks")) or "0").strip() or "0")
    except ValueError:
        return 0


def main():
    data = c.read_stdin_json()
    if not c.is_operator():
        return
    if os.path.exists(c.wf("gate.md")) or os.path.exists(c.wf("STOP")):
        return
    if not UNCHECKED.search(c.read_text(c.wf("roadmap.md")) or ""):
        return
    if data.get("stop_hook_active") is True and c.state_phase(c.read_text(c.wf("state.md"))) == "gated":
        return
    cap = read_cap()
    n = read_blocks()
    if n >= cap:
        return
    n += 1
    with open(c.wf(".blocks"), "w", encoding="utf-8") as f:
        f.write(f"{n}\n")
    reason = ("The arcade loop is not finished and no gate is open. Read "
              "docs/superpowers/workflow/state.md and continue from its phase. "
              f"Block {n} of {cap} this run.")
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # a false allow ends the turn; never crash into a loop
        print(f"stop: {e}", file=sys.stderr)
    sys.exit(0)
