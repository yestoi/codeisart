#!/usr/bin/env python3
"""SessionStart hook for the arcade operator (matchers: compact, and startup|resume with --fresh).

Prints to stdout, which Claude Code adds to context: the re-entry banner (after a
compaction) or the new-session banner (--fresh),
state.md, the last '## Iteration' journal entry, the last open question in
decisions.md, gate.md if present, the note that config.md's Loop rules
override the skill, and the instruction to invoke the workflow-loop skill.
With --fresh it also says that the last session's agents are gone, and lists
the state files and their purposes. Inert unless OPERATOR=1 and state.md exists.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as c  # noqa: E402

BANNER = ("You are the arcade operator. Context was compacted. Re-enter the workflow loop "
          "at the phase in state.md. Do not restart the iteration, do not re-plan a committed "
          "plan, do not re-spawn an agent named in `in_flight` (SendMessage it instead). "
          "Files are truth.")

FILES = [
    ("config.md", "phase, test command, evidence command, freshness check, gates, iteration cap per run"),
    ("roadmap.md", "end goal, milestones with status, Carried fixes queue"),
    ("journal.md", "append-only iteration log, workflow-loop format plus test count, skip count, evidence dir"),
    ("state.md", "the resume pointer: iteration number, current phase, plan path, BASE sha, "
                 "orchestrator agent name, what is in flight"),
    ("decisions.md", "every question asked of the owner, its default, its deadline, and the answer, one block each"),
    ("gate.md", "exists only while the loop is stopped for the owner: the question, the evidence paths, "
                "the default and deadline"),
    ("live-smoke.md", "the owner's per-game live-webcam verdicts (responded y/n, understood y/n, "
                      "want another go 1 to 5, broken)"),
    ("evidence/itNN/", "README with the decision on line 1, feel table, reviewer verdict, sheets, GIFs, traces"),
    ("evidence/pi-perf.md", "the Pi's measured tick times, once the Pi exists"),
]

FRESH_BANNER = ("You are the arcade operator, starting a new session. Enter the workflow loop at the phase in "
                "state.md. Do not redo an iteration the journal marks done and do not re-plan a committed plan. "
                "Files are truth.")

FRESH = ("This is a new session, so every agent of the last session is gone. If `in_flight` names an "
         "agent, do not wait for it and do not SendMessage it: keep what it committed or wrote to disk, "
         "set `in_flight` to none in state.md, and start that phase's work again from the files.")

RULES = ("config.md's Loop rules override the workflow-loop skill and its sub-skills wherever they differ. "
         "Never change directory in a Bash command (use absolute paths or `git -C`).")

FINAL = "Invoke the workflow-loop skill with the Skill tool and resume at the phase in state.md."


def main():
    c.read_stdin_json()
    if not c.is_operator():
        return
    fresh = "--fresh" in sys.argv[1:]
    out = [FRESH_BANNER if fresh else BANNER, ""]
    if fresh:
        out += [FRESH, ""]
    out += [RULES, ""]
    if fresh:
        out.append("## Workflow state files (docs/superpowers/workflow/)")
        out += [f"- {name}: {purpose}" for name, purpose in FILES]
        out.append("")
    out.append("## state.md")
    out.append((c.read_text(c.wf("state.md")) or "").rstrip())
    out.append("")
    out.append("## Last journal entry")
    entry = c.last_iteration_entry(c.read_text(c.wf("journal.md")))
    out.append(entry if entry else "(journal.md has no '## Iteration' entry yet)")
    out.append("")
    out.append("## Open question in decisions.md")
    q = c.last_open_question(c.read_text(c.wf("decisions.md")))
    out.append(q if q else "(no open question in decisions.md)")
    out.append("")
    gate = c.read_text(c.wf("gate.md"))
    if gate is not None:
        out.append("## gate.md (the loop is gated; wait for the owner's answer)")
        out.append(gate.rstrip())
        out.append("")
    out.append(FINAL)
    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"reinject: {e}", file=sys.stderr)
    sys.exit(0)
