#!/usr/bin/env python3
"""Stop hook for the arcade operator: keeps the loop running until it gates itself.

Allows the stop (exit 0, no output) when any of:
  - not the operator (OPERATOR=1 unset or state.md missing);
  - docs/superpowers/workflow/gate.md exists;
  - docs/superpowers/workflow/STOP exists (the owner's kill switch);
  - roadmap.md has no line matching '- [ ] M' (no unfinished milestone);
  - stop_hook_active is true and state.md says phase: gated;
  - state.md's in_flight line names an agent and state.md was written in the last
    IN_FLIGHT_FRESH seconds: the operator is waiting for that agent's report, which
    starts its next turn. This stop is not counted. Once state.md is older than that
    the stop is blocked and counted as usual, and the reason says to check the agent;
  - the run's block counter in docs/superpowers/workflow/.blocks is at or above
    iterations-per-run from config.md (default 6).
Otherwise increments the counter and prints a block decision as JSON.

The counter counts blocks since the last commit: .blocks-head holds the HEAD the count
belongs to, and a block at another HEAD starts the count again at 1. A loop that commits
is making progress and is kept running; one that is blocked cap times with nothing
committed is let go. (Before 2026-09-28 the count only rose, reached its cap in the first
afternoon and the hook then allowed every stop for the rest of the run.) The LOOP still
resets the counter when a gate is answered by deleting docs/superpowers/workflow/.blocks.
Both files are created here if missing, and ignored by git. The iteration cap itself is
the loop's: it writes gate.md at step 8.
Any internal error allows the stop.
"""
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as c  # noqa: E402

DEFAULT_CAP = 6
IN_FLIGHT_FRESH = 45 * 60    # seconds: the operator's fallback wake-up is 20 minutes, so two were missed
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


def head():
    """HEAD's sha, or None when git cannot say."""
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=c.root(), capture_output=True, text=True, timeout=4)
        return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None
    except Exception:
        return None


def state_age():
    """Seconds since state.md was written, or None if that cannot be read."""
    try:
        return time.time() - os.path.getmtime(c.wf("state.md"))
    except OSError:
        return None


def main():
    data = c.read_stdin_json()
    if not c.is_operator():
        return
    if os.path.exists(c.wf("gate.md")) or os.path.exists(c.wf("STOP")):
        return
    if not UNCHECKED.search(c.read_text(c.wf("roadmap.md")) or ""):
        return
    state = c.read_text(c.wf("state.md"))
    if data.get("stop_hook_active") is True and c.state_phase(state) == "gated":
        return
    waiting, age = c.agent_in_flight(state), state_age()
    if waiting and age is not None and age < IN_FLIGHT_FRESH:
        return
    cap = read_cap()
    n = read_blocks()
    now, counted_at = head(), (c.read_text(c.wf(".blocks-head")) or "").strip()
    if now and counted_at and now != counted_at:
        n = 0
    if n >= cap:
        return
    n += 1
    with open(c.wf(".blocks"), "w", encoding="utf-8") as f:
        f.write(f"{n}\n")
    if now:
        with open(c.wf(".blocks-head"), "w", encoding="utf-8") as f:
            f.write(f"{now}\n")
    reason = ("The arcade loop is not finished and no gate is open. Read "
              "docs/superpowers/workflow/state.md and continue from its phase. ")
    if waiting:
        reason += ("state.md names an agent in in_flight but has not been written for "
                   f"{int((age or 0) // 60)} minutes. Check the agent with ListAgents: if it is working, "
                   "rewrite state.md with the time you checked; if it is gone, set in_flight to none and "
                   "redo its work from the files. ")
    reason += f"Block {n} of {cap} this run."
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # a false allow ends the turn; never crash into a loop
        print(f"stop: {e}", file=sys.stderr)
    sys.exit(0)
