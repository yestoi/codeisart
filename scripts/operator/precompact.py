#!/usr/bin/env python3
"""PreCompact hook for the arcade operator.

Appends a compaction footer to docs/superpowers/workflow/state.md: timestamp,
trigger, HEAD short sha, up to 20 lines of `git status --short`, the heading of
the last '## Iteration' entry in journal.md, and whether gate.md exists. Only
the most recent footer is kept. Never blocks compaction; never exits non-zero.
Inert unless OPERATOR=1 and state.md exists.
"""
import datetime
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as c  # noqa: E402

FOOTER_MARK = "## Compaction footer "


def git(*args):
    try:
        r = subprocess.run(["git", *args], cwd=c.root(), capture_output=True,
                           text=True, timeout=4)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def main():
    data = c.read_stdin_json()
    if not c.is_operator():
        return
    state_path = c.wf("state.md")
    state = c.read_text(state_path) or ""

    idx = state.find("\n" + FOOTER_MARK)
    if state.startswith(FOOTER_MARK):
        idx = 0
    if idx != -1:
        state = state[:idx]
    state = state.rstrip() + "\n"

    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    trigger = data.get("trigger") or "unknown"
    head = (git("rev-parse", "--short", "HEAD") or "").strip() or "unknown"
    status = git("status", "--short")
    status_lines = status.splitlines()[:20] if status is not None else ["(git unavailable)"]
    entry = c.last_iteration_entry(c.read_text(c.wf("journal.md")))
    last_heading = entry.splitlines()[0] if entry else "(no iteration entry yet)"
    gate = "present" if os.path.isfile(c.wf("gate.md")) else "absent"

    footer = [
        "",
        f"{FOOTER_MARK}{ts}",
        f"- trigger: {trigger}",
        f"- head: {head}",
        f"- last journal entry: {last_heading}",
        f"- gate.md: {gate}",
        "- git status --short (up to 20 lines):",
        "```",
        *(status_lines or ["(clean)"]),
        "```",
    ]
    with open(state_path, "w", encoding="utf-8") as f:
        f.write(state + "\n".join(footer) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never block or fail compaction
        print(f"precompact: {e}", file=sys.stderr)
    sys.exit(0)
