"""Shared helpers for the arcade operator hooks.

Every hook is inert (exit 0, no output) unless BOTH the environment variable
OPERATOR=1 is set AND docs/superpowers/workflow/state.md exists under the
project root. Nothing here depends on conversation state: files are truth.

The project root is CLAUDE_PROJECT_DIR, which Claude Code sets for hook commands.
A hook runs in the session's working directory, and that moves when a command
changes directory, so the working directory is only the fallback: the nearest
directory at or above it that holds docs/superpowers/workflow/.
"""
import json
import os
import re
import sys

WORKFLOW_REL = os.path.join("docs", "superpowers", "workflow")


def root():
    project = os.environ.get("CLAUDE_PROJECT_DIR")
    if project and os.path.isdir(project):
        return project
    here = os.getcwd()
    d = here
    while True:
        if os.path.isdir(os.path.join(d, WORKFLOW_REL)):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return here
        d = parent


def wf(*parts):
    return os.path.join(root(), WORKFLOW_REL, *parts)


def is_operator():
    return os.environ.get("OPERATOR") == "1" and os.path.isfile(wf("state.md"))


def read_stdin_json():
    try:
        data = json.loads(sys.stdin.read() or "{}")
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def read_text(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def unfenced_lines(text):
    """Yield (index, line, in_fence) so parsers can skip examples in code fences."""
    in_fence = False
    for i, line in enumerate(text.splitlines()):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            yield i, line, True
            continue
        yield i, line, in_fence


def last_iteration_entry(journal_text):
    """Return the last '## Iteration' entry (heading to EOF or next '## '), or None."""
    if not journal_text:
        return None
    lines = journal_text.splitlines()
    start = None
    for i, line, fenced in unfenced_lines(journal_text):
        if not fenced and line.startswith("## Iteration"):
            start = i
    if start is None:
        return None
    end = len(lines)
    for i, line, fenced in unfenced_lines(journal_text):
        if i > start and not fenced and line.startswith("## ") and not line.startswith("## Iteration"):
            end = i
            break
        if i > start and not fenced and line.startswith("## Iteration"):
            end = i
            break
    return "\n".join(lines[start:end]).rstrip()


ANSWER_EMPTY = re.compile(r"^\s*(?:-\s*)?answer:\s*$")


def last_open_question(decisions_text):
    """Return the last '### Q' block whose 'answer:' line is empty, or None."""
    if not decisions_text:
        return None
    lines = decisions_text.splitlines()
    blocks = []
    cur = None
    for i, line, fenced in unfenced_lines(decisions_text):
        if not fenced and line.startswith("#"):
            if cur is not None:
                blocks.append(cur)
                cur = None
            if line.startswith("### Q"):
                cur = [i, i + 1]
            continue
        if cur is not None:
            cur[1] = i + 1
    if cur is not None:
        blocks.append(cur)
    found = None
    for s, e in blocks:
        body = lines[s:e]
        if any(ANSWER_EMPTY.match(l) for l in body):
            found = "\n".join(body).rstrip()
    return found


IN_FLIGHT = re.compile(r"^\s*in_flight:[ \t]*(.*)$", re.M)


def agent_in_flight(state_text):
    """True when state.md's in_flight line names something: not empty and not starting with 'none'."""
    m = IN_FLIGHT.search(state_text or "")
    value = m.group(1).strip() if m else ""
    return bool(value) and not value.lower().startswith("none")


def state_phase(state_text):
    if not state_text:
        return None
    m = re.search(r"^\s*phase:\s*(\S+)", state_text, re.M)
    return m.group(1) if m else None
