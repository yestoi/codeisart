#!/usr/bin/env python3
"""PreToolUse(Bash) hook for the arcade operator: blocks destructive or outward commands.

Exit 2 with a one-line reason on stderr blocks the call; exit 0 allows it.
Blocks when the command:
  - pushes: `git push` (also `gh pr create`, `gh repo sync`, `gh release create`,
    which push too) unless docs/superpowers/workflow/push-allowed exists;
  - `git reset --hard`, `git checkout -- .`, `git checkout .`, `git restore .`,
    `git clean`, `git branch -D`;
  - recursive `rm` (-r, -R, --recursive, with or without -f) with any target not under
    /private/tmp/ or /tmp/ and not inside a .venv directory; targets containing
    `..`, `$`, `~` or a leading glob are never trusted;
  - writes to tests/arcade/fixtures/real/ (rm, mv, tee, truncate, unlink, ln,
    sed -i, any `>` redirect, or cp with it as the destination).
Regexes are deliberately conservative: a false block is cheap, a false allow is not.
Quoted strings are scanned too, so `bash -c "git push"` is caught.
Inert unless OPERATOR=1 and state.md exists. Internal errors block.
"""
import os
import re
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as c  # noqa: E402

GIT = r"\bgit(?:\s+(?:-C|-c|--git-dir|--work-tree|--namespace)\s+\S+|\s+--?[\w-]+(?:=\S+)?)*\s+"
SEG = r"[^;&|\n]*"
PUSH = [re.compile(GIT + r"push\b"),
        re.compile(r"\bgh\s+(?:pr\s+create|repo\s+sync|release\s+create)\b")]
DESTRUCTIVE = [
    (re.compile(GIT + r"reset\b" + SEG + r"--hard\b"), "git reset --hard"),
    (re.compile(GIT + r"checkout\b" + SEG + r"\s--\s+\.(?:/)?(?=\s|$|[;&|)])"), "git checkout -- ."),
    (re.compile(GIT + r"checkout\s+(?:[^\s;&|]+\s+)*\.(?:/)?(?=\s|$|[;&|)])"), "git checkout ."),
    (re.compile(GIT + r"restore\b" + SEG + r"\s\.(?:/)?(?=\s|$|[;&|)])"), "git restore ."),
    (re.compile(GIT + r"clean\b"), "git clean"),
    (re.compile(GIT + r"branch\b" + SEG + r"\s(?:-[a-zA-Z]*D\b|--delete\s+--force|--force\s+--delete)"),
     "git branch -D"),
]
FIXTURES = re.compile(r"fixtures/real")
FIXTURE_WRITE = re.compile(r"(?:^|[\s;&|(`])(?:rm|mv|tee|truncate|unlink|ln|shred)\b|\bsed\s+(?:\S+\s+)*-i|>|\bgit\s+(?:rm|mv)\b")
SPLIT = re.compile(r"&&|\|\||[;&|\n()`]|\$\(")


def block(reason):
    sys.stderr.write(f"operator guard: blocked ({reason}). See scripts/operator/README.md.\n")
    sys.exit(2)


def tokens(segment):
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.replace('"', " ").replace("'", " ").split()


def rm_target_ok(t):
    if not t or any(x in t for x in ("..", "$", "~")) or t[0] in "*?[{":
        return False
    if t.startswith("/private/tmp/") or t.startswith("/tmp/"):
        return len(t.rstrip("/")) > len("/private/tmp") and t.rstrip("/") not in ("/tmp", "/private/tmp")
    return ".venv" in t.strip("/").split("/")


def check_rm(toks, depth):
    for i, tok in enumerate(toks):
        if tok != "rm" and not tok.endswith("/rm"):
            continue
        recursive, targets, opts_done = False, [], False
        for a in toks[i + 1:]:
            if not opts_done and a == "--":
                opts_done = True
            elif not opts_done and a.startswith("--"):
                recursive = recursive or a == "--recursive"
            elif not opts_done and a.startswith("-") and len(a) > 1:
                recursive = recursive or "r" in a or "R" in a
            else:
                targets.append(a)
        if recursive:
            bad = [t for t in targets if not rm_target_ok(t)] or ([] if targets else ["(no target)"])
            if bad:
                block(f"recursive rm outside /private/tmp/, /tmp/ or .venv: {bad[0]}")


def check_cp_dest(toks):
    for i, tok in enumerate(toks):
        if tok != "cp" and not tok.endswith("/cp"):
            continue
        args = toks[i + 1:]
        for j, a in enumerate(args):
            if a in ("-t", "--target-directory") and j + 1 < len(args) and FIXTURES.search(args[j + 1]):
                block("cp into tests/arcade/fixtures/real/")
            if a.startswith("--target-directory=") and FIXTURES.search(a):
                block("cp into tests/arcade/fixtures/real/")
        plain = [a for a in args if not a.startswith("-")]
        if plain and FIXTURES.search(plain[-1]):
            block("cp into tests/arcade/fixtures/real/")


def analyse(command, depth=0):
    if depth > 4:
        block("command nesting too deep to analyse")
    for rx in PUSH:
        if rx.search(command) and not os.path.exists(c.wf("push-allowed")):
            block("push needs docs/superpowers/workflow/push-allowed")
    for rx, name in DESTRUCTIVE:
        if rx.search(command):
            block(name)
    for segment in SPLIT.split(command):
        if not segment.strip():
            continue
        if FIXTURES.search(segment) and FIXTURE_WRITE.search(segment):
            block("write touching tests/arcade/fixtures/real/")
        toks = tokens(segment)
        check_rm(toks, depth)
        if FIXTURES.search(segment):
            check_cp_dest(toks)
        for t in toks:
            if re.search(r"\s", t):
                analyse(t, depth + 1)


def main():
    data = c.read_stdin_json()
    if not c.is_operator() or data.get("tool_name") != "Bash":
        return
    command = (data.get("tool_input") or {}).get("command") or ""
    if not isinstance(command, str):
        block("unreadable command")
    analyse(command)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        block(f"guard error: {e}")
    sys.exit(0)
