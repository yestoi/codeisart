#!/usr/bin/env python3
"""PreToolUse(Write|Edit|MultiEdit|NotebookEdit) hook for the arcade operator.

Blocks (exit 2, one-line reason on stderr) any write through the file tools to
tests/arcade/fixtures/real/, the owner-recorded fixtures only the owner may change.
Everything else is allowed. Inert unless OPERATOR=1 and state.md exists.
Internal errors block, like guard_bash.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as c  # noqa: E402

PROTECTED = os.path.join("tests", "arcade", "fixtures", "real")


def block(reason):
    sys.stderr.write(f"operator guard: blocked ({reason}). See scripts/operator/README.md.\n")
    sys.exit(2)


def main():
    data = c.read_stdin_json()
    if not c.is_operator():
        return
    if data.get("tool_name") not in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        return
    ti = data.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("notebook_path") or ""
    if not path:
        return
    real = os.path.realpath(os.path.join(c.root(), path)) if not os.path.isabs(path) else os.path.realpath(path)
    prot = os.path.realpath(os.path.join(c.root(), PROTECTED))
    parts = [p for p in path.replace("\\", "/").split("/") if p]
    seg = ["tests", "arcade", "fixtures", "real"]
    by_segments = any(parts[i:i + 4] == seg for i in range(len(parts)))
    if real == prot or real.startswith(prot + os.sep) or by_segments:
        block("write to the owner-recorded fixtures")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        block(f"guard_write internal error: {e}")
    sys.exit(0)
