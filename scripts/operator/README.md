# Arcade operator hooks

Claude Code hooks that keep one long-running session driving the `workflow-loop` skill for the
wall arcade. Design: `docs/superpowers/specs/2026-09-26-arcade-operator-design.md` (sections 3 to 6).
Wired up in `.claude/settings.json`.

Every script is **inert** (exit 0, no output) unless both hold:

- the session was launched with `OPERATOR=1` in its environment, and
- `docs/superpowers/workflow/state.md` exists.

Every other Claude session in this repo is unaffected. Never put `OPERATOR=1` in a settings file.

`.claude/settings.json` also sets `worktree.baseRef` to `"head"`, so a subagent's worktree starts from the
local HEAD. The default starts it from the last pushed commit, which the push guard keeps far behind.

The hook commands in `.claude/settings.json` start with `python3 "$CLAUDE_PROJECT_DIR/scripts/operator/`.
A hook runs in the session's working directory. With a relative path, one `cd` in a Bash command made
Python exit 2 on every hook ("can't open file"), which Claude Code reads as a block: Bash, Write and Edit
were all refused until the owner typed `! cd` back to the root (2026-09-28). The scripts find the
workflow files the same way: `CLAUDE_PROJECT_DIR` first, then the nearest directory at or above the
working directory that holds `docs/superpowers/workflow/`.

## Scripts

| Script | Hook | What it does |
|---|---|---|
| `precompact.py` | `PreCompact` (auto, manual) | Appends a `## Compaction footer` to `state.md`: time, trigger, HEAD, up to 20 lines of `git status --short`, the last journal heading, whether `gate.md` exists. Keeps only the newest footer. Never blocks. |
| `reinject.py` | `SessionStart` (compact; startup and resume with `--fresh`) | Prints the re-entry banner, the note that `config.md`'s Loop rules override the skill, `state.md`, the last journal entry, the open question in `decisions.md`, `gate.md` if present, `pi-lock.md` if present (before `state.md`), and "invoke the workflow-loop skill". `--fresh` adds that the last session's agents are gone (an agent named in `in_flight` is not waited for) and the list of state files. |
| `stop.py` | `Stop` | Refuses to let the session stop while the roadmap has an unchecked `- [ ] M` milestone and no gate is open. Allows the stop on `gate.md`, `STOP`, a finished roadmap, `stop_hook_active` while `phase: gated`, or when the counter in `workflow/.blocks` reaches `stop-blocks` from `config.md` (`iterations-per-run` when that line is missing); the counter starts again whenever HEAD has moved since the last block (`workflow/.blocks-head`), so only blocks with nothing committed between them add up. Also allows it, without counting, while `state.md`'s `in_flight` names an agent and `state.md` was written in the last 45 minutes: the agent's report starts the next turn. Past 45 minutes it blocks and tells the operator to check the agent. |
| `guard_bash.py` | `PreToolUse` (Bash) | Blocks (exit 2) `git push` and `gh pr create` unless `workflow/push-allowed` exists; `git reset --hard`, `git checkout .`, `git checkout -- .`, `git restore .`, `git clean`, `git branch -D`; recursive `rm` outside `/private/tmp/`, `/tmp/` or a `.venv`; any write to `tests/arcade/fixtures/real/`. While `workflow/pi-lock.md` exists: any `ssh`, `scp`, `rsync` or `sftp` to `codeisart.local` except `ssh <host> '<remote>'` whose remote command is one quoted string that starts `flock -w 300 /tmp/pi5.lock ` and is one command or one `sh -c '<script>'` (a command whose text only quotes such a line, a commit message for one, is refused too: write that text with the Write or Edit tool). |
| `guard_write.py` | `PreToolUse` (Write, Edit, MultiEdit, NotebookEdit) | Blocks (exit 2) any file-tool write under `tests/arcade/fixtures/real/`, closing the gap `guard_bash.py` cannot cover. |
| `_common.py` | none | Shared guard and file parsing. |

Tests: `bash scripts/operator/test_hooks.sh` (standard library only, runs in a temp dir).

## Launching the operator

From the repo root, with the pre-flight checklist in the design (section 10) done:

```sh
caffeinate -dims &          # or keep the lid open; a sleeping Mac ends the session
OPERATOR=1 claude --autocompact 300k
```

Then in the session: `/remote-control`, and say "start the workflow loop".

## Kill switch

Either of:

- `touch docs/superpowers/workflow/STOP` (the Stop hook then lets the session end), or
- message the session "stop the loop" (from the phone via Remote Control); the loop creates `STOP`
  and journals it.

Delete `STOP` before the next run.

## Answering a gate

When the loop needs you it writes `docs/superpowers/workflow/gate.md`, sets `phase: gated` in
`state.md`, sends a push notification with the evidence, and ends its turn.

1. Read `gate.md` and the evidence README it points at.
2. Reply in the session in plain words (the phone is fine).
3. The loop writes your answer into `decisions.md` under the question, deletes `gate.md` and
   `workflow/.blocks` (resetting the Stop-hook counter for the next run), commits, rewrites
   `state.md`, and continues.

To allow pushing to the remote once and for all, `touch docs/superpowers/workflow/push-allowed`.

While the Pi is shared with another session, `docs/superpowers/workflow/pi-lock.md` holds the rule: every
Pi command runs under `flock -w 300 /tmp/pi5.lock` inside the ssh call. The file is printed after every
compaction and at every session start, and the Bash guard refuses a Pi command without the lock while it
exists. To lift the rule, delete the file.
