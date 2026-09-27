# Arcade operator hooks

Claude Code hooks that keep one long-running session driving the `workflow-loop` skill for the
wall arcade. Design: `docs/superpowers/specs/2026-09-26-arcade-operator-design.md` (sections 3 to 6).
Wired up in `.claude/settings.json`.

Every script is **inert** (exit 0, no output) unless both hold:

- the session was launched with `OPERATOR=1` in its environment, and
- `docs/superpowers/workflow/state.md` exists.

Every other Claude session in this repo is unaffected. Never put `OPERATOR=1` in a settings file.

## Scripts

| Script | Hook | What it does |
|---|---|---|
| `precompact.py` | `PreCompact` (auto, manual) | Appends a `## Compaction footer` to `state.md`: time, trigger, HEAD, up to 20 lines of `git status --short`, the last journal heading, whether `gate.md` exists. Keeps only the newest footer. Never blocks. |
| `reinject.py` | `SessionStart` (compact; startup and resume with `--fresh`) | Prints the re-entry banner, `state.md`, the last journal entry, the open question in `decisions.md`, `gate.md` if present, and "invoke the workflow-loop skill". `--fresh` adds the list of state files. |
| `stop.py` | `Stop` | Refuses to let the session stop while the roadmap has an unchecked `- [ ] M` milestone and no gate is open. Allows the stop on `gate.md`, `STOP`, a finished roadmap, `stop_hook_active` while `phase: gated`, or when the per-run counter in `workflow/.blocks` reaches `iterations-per-run` from `config.md`. |
| `guard_bash.py` | `PreToolUse` (Bash) | Blocks (exit 2) `git push` and `gh pr create` unless `workflow/push-allowed` exists; `git reset --hard`, `git checkout .`, `git checkout -- .`, `git restore .`, `git clean`, `git branch -D`; recursive `rm` outside `/private/tmp/`, `/tmp/` or a `.venv`; any write to `tests/arcade/fixtures/real/`. |
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
