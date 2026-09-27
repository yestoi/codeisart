# Arcade Operator Design

Date: 2026-09-26. Status: DRAFT, awaiting the owner's approval. Nothing here is installed yet.

The operator is one long-running Claude Code session on the Mac that builds the wall arcade mostly
unattended: it plans a slice, implements it through fresh subagents, has it reviewed, verifies it
headlessly, writes the evidence to disk, and either continues or stops at a gate for a human decision.
The owner is away from the computer for most of it and answers from a phone. Its context is compacted
automatically around 300k tokens, so every fact the loop needs lives in a committed file, never only in
the conversation.

This document adapts the `workflow-loop` skill (`~/.claude/skills/workflow-loop/`) to a project whose
"deploy" is a local Python process and whose "walkthrough" is a set of PNGs, GIFs and metrics rather than
a web page. It draws on the verification lens of the adversarial review
(`docs/superpowers/reviews/2026-09-26-arcade-adversarial-review.md`, sections 6 and 8).

## 1. Goals

- The owner launches it, walks away, and comes back to committed evidence and a short list of decisions.
- Decisions that are the owner's (section 5) are never made by the loop; decisions that are not are
  made, journaled, and never asked.
- A compaction, a crash, a closed laptop or a killed terminal loses nothing: the next session resumes
  from files at the phase it stopped in.
- Games are judged fun by a human. The loop's job is to make that judgment cheap: two minutes on a
  phone with a contact sheet, a GIF and a one-line question.

### Non-goals

- Running on the Pi. Phase 1 is the Mac. The Pi phase is a separate config change (section 8).
- Cloud scheduling. The webcam, the microphone and later the Pi are local.
- Replacing the review. The loop executes an approved spec and plan; it does not redesign.

## 2. Approaches considered

**A. One interactive session driving the workflow-loop skill, kept alive by hooks (recommended).**
State in files, a `Stop` hook that refuses to let the session end while the roadmap is unfinished and no
gate is open, `PreCompact` and `SessionStart(compact)` hooks that snapshot and re-inject state, Remote
Control so the owner answers from a phone, push notifications at gates. Subagents keep their own context
and only their final reports enter the operator's, so the operator's context grows mostly from reading
evidence PNGs, which is what compaction is for.

**B. A shell loop around `claude -p`, one fresh process per iteration (the Ralph loop).** No compaction
story because every iteration starts empty, and state is forced into files, which is good discipline. But
every iteration re-reads the spec, the plan and the journal from scratch, a headless process cannot
surface a permission prompt or take a phone answer mid-iteration, and a question to the owner has to be
polled from a file by a wrapper script. It is the right fallback if approach A's `Stop` hook proves
unreliable, and approach A is written so that the same files drive it.

**C. Cloud routines or scheduled agents.** Not applicable: the work needs the local webcam, microphone,
repo and later the Pi on the LAN.

Approach A is recommended, built on approach B's rule that files are the only truth.

## 3. State files

All under `docs/superpowers/workflow/`, all committed.

| File | Holds | Written by |
|---|---|---|
| `config.md` | phase, test command, evidence command, freshness check, gates, iteration cap per run | bootstrap, owner edits |
| `roadmap.md` | end goal, milestones with status, Carried fixes queue | loop |
| `journal.md` | append-only iteration log, workflow-loop format plus test count, skip count, evidence dir | loop |
| `state.md` | the resume pointer: iteration number, current phase (orient, plan, implement, review, verify, synthesize, report, gated), plan path, BASE sha, orchestrator agent name, what is in flight | loop at every phase transition; `PreCompact` hook appends a footer |
| `decisions.md` | every question asked of the owner, its default, its deadline, and the answer, one block each | loop asks, owner answers (by phone message, the loop transcribes) |
| `gate.md` | exists only while the loop is stopped for the owner: the question, the evidence paths, the default and deadline | loop creates, loop deletes after transcribing the answer |
| `live-smoke.md` | the owner's per-game live-webcam verdicts (responded y/n, understood y/n, want another go 1 to 5, broken) | owner |
| `evidence/itNN/` | README with the decision on line 1, feel table, reviewer verdict, sheets, GIFs, traces | `tools/arcade_evidence.py` |
| `evidence/pi-perf.md` | the Pi's measured tick times, once the Pi exists | loop, on the Pi |

`state.md` is the file that makes compaction and crashes survivable. It is short (under 30 lines) and
rewritten, not appended, at every phase change. Example:

```markdown
# Operator state
iteration: 7
phase: review
plan: docs/superpowers/plans/2026-10-03-it07-menu-presence.md
base: 3f2a9c1
orchestrator: it07-orch (SendMessage to it for re-review)
in_flight: reviewer agent it07-review spawned 14:02, awaiting verdict
carried: flash governor test flake (see roadmap Carried fixes)
next_gate: after iteration 8 (iteration cap), or on any human-only decision
last_compaction: 2026-10-03T13:40Z at iteration 7 phase implement
```

## 4. The loop, adapted

The workflow-loop steps with the arcade substitutions. Steps not listed are unchanged.

1. **Orient.** Read `config.md`, `roadmap.md`, the last two `journal.md` entries, `state.md`,
   `decisions.md`. If `gate.md` exists and has no answer, stop (the `Stop` hook lets this through). If
   `state.md` says a phase is in flight, resume there; do not restart the iteration. Iteration number is
   the last journal entry plus one.
2. **Plan.** writing-plans as usual, one slice plus all Carried fixes. A slice is one to three plan tasks
   or one to two games. Commit. Write `state.md`.
2a. **Plan review (added 2026-09-27, owner decision Q6).** Before the plan is committed, one opus
   reviewer attacks the iteration plan against the spec, the core plan's amendments, the review lenses
   and the operator design's gate table. It looks for:
   - spec drift and wrong defaults;
   - weak, missing or unfalsifiable tests;
   - safety gaps (brightness, flashing);
   - unverified hardware and protocol assumptions;
   - carried fixes the plan misses or only half addresses;
   - decisions the plan takes that section 5 reserves for the owner.

   Its verdict is APPROVED or BLOCKED. The blocking findings go back to the plan writer (SendMessage; it keeps
   context), which revises and re-replays the plan; the plan is then re-reviewed once. If it is still blocked
   after two rounds, the loop gates. Non-blocking notes are either folded into the plan by the writer or
   journaled. The verdict is saved to `evidence/itNN/plan-review.md`.
3. **Implement.** One orchestrator agent, one fresh implementer per task, as the skill says. Two rules
   added to the orchestrator prompt: game test modules are copied from the plan verbatim and any
   difference is a Deviation; never edit `arcade/games/__init__.py` except to add a name to
   `MENU_ORDER` in its spec position.
4. **Review.** The reviewer prompt gains: "List every removed or changed `assert` in
   `git diff BASE..HEAD -- tests/`. Each needs a justification in its commit message or it is BLOCKING."
   and "Run `pytest --collect-only -q | tail -1` and `pytest -rs -q | grep -c SKIPPED`; a drop in the
   count or a rise in skips without a journaled reason is BLOCKING."
5. **Deploy.** Phase 1 has none. The config says `Deploy: none`. Phase 2 (Pi) sets it to an rsync and a
   service restart, run inline in the main session, never in an agent.
6. **Verify (replaces Walk).** Run inline: the test command; `python -m arcade doctor` with the sources
   the slice needs; `python tools/arcade_evidence.py --iteration N --games changed`. The freshness check
   is the sheet header: every PNG in `evidence/itNN/` carries the git sha, and it must equal HEAD. A
   mismatch is a tooling defect, fixed before anything is judged. No walker agent is needed in phase 1;
   the evidence command is deterministic.
7. **Synthesize.** Read the sheets and GIFs with the Read tool and judge the pixels. Read `feel.json`.
   Score the success criteria. Write the verdict into the journal entry immediately, before any other
   tool call, because reading images is what fills the context and triggers compaction.
8. **Report.** Journal entry, roadmap update, commit state and evidence. Then one of:
   - No human decision pending and iteration cap not reached: rewrite `state.md` to `phase: orient`
     for N+1 and continue.
   - A human-only decision, or the iteration cap reached: write `gate.md`, send the owner a push
     notification (one line: what to decide and where), send the evidence README and the two most
     relevant PNGs as files, rewrite `state.md` to `phase: gated`, and end the turn.

**Iteration cap.** `config.md` sets `iterations-per-run: 6`. After six iterations the loop gates for a
check-in even if nothing needs deciding. This is the owner's throttle on unattended spend and drift; it
is raised by editing the config.

**Defaults and deadlines.** Every question in `decisions.md` has a default and a deadline expressed as
an iteration number. Loop-decidable questions are never asked; they are journaled. Human-only questions
block. Questions in between ("dwell time: the fixtures say 1.2 s; confirm?") take the default at the
deadline and are marked `defaulted` so the owner can override later.

## 5. Gates: what the human decides

From the review's gate table, made concrete for this project.

| Decision | Who | How the loop handles it |
|---|---|---|
| Fold review findings into spec revision 3 and the plan amendments | Human, before the loop starts | Pre-flight item, not a loop gate |
| Keep, cut, merge or add a game | Human | Gate with sheets, GIF, feel table, and the review's verdict line |
| Whether a game feels good on the live webcam | Human | `live-smoke.md`; the loop turns each "n" or a score of 2 or less into a Carried fix |
| Loosen a feel budget, change a plan-literal test, drop a test | Human | Gate; tightening is the loop's |
| Brightness ceiling, night level, where gamma is applied | Human | Gate at prototype week |
| Record, delete or re-record real-input fixtures | Human | Gate: the loop writes the recording script and cue list, the owner records |
| Move to the Pi; write the Pi config | Human | Gate when the Pi and camera are in hand |
| Push to the public remote, publish evidence outside the machine | Human, standing consent once | `PreToolUse` hook blocks `git push` unless `docs/superpowers/workflow/push-allowed` exists |
| Write the second plan (remaining games, project skills) | Loop, after the owner's first live smoke | Journaled; owner skims order and budgets, default proceed |
| Difficulty numbers within bot win-rate bands, colour palettes within wall-look metrics, menu order, icon art, dependency pins, Python version, skill wording | Loop | Journaled, never asked |
| Dwell time, session timeouts, presence thresholds | Loop proposes from fixtures, defaults at deadline | `decisions.md` with `defaulted` |

## 6. Hooks and settings

Project-level, in `.claude/settings.json`, scripts in `scripts/operator/`. Hooks are inherited by
subagents, so every script first checks that it is running for the operator (an `OPERATOR=1`
environment variable set when the session is launched, or the presence of
`docs/superpowers/workflow/state.md`) and exits 0 otherwise.

```json
{
  "hooks": {
    "PreCompact": [
      { "matcher": "auto|manual",
        "hooks": [ { "type": "command", "command": "scripts/operator/precompact.sh", "timeout": 10 } ] }
    ],
    "SessionStart": [
      { "matcher": "compact",
        "hooks": [ { "type": "command", "command": "scripts/operator/reinject.sh", "timeout": 10 } ] },
      { "matcher": "startup|resume",
        "hooks": [ { "type": "command", "command": "scripts/operator/reinject.sh --fresh", "timeout": 10 } ] }
    ],
    "Stop": [
      { "hooks": [ { "type": "command", "command": "scripts/operator/stop.sh", "timeout": 10 } ] }
    ],
    "PreToolUse": [
      { "matcher": "Bash",
        "hooks": [ { "type": "command", "command": "scripts/operator/guard-bash.sh", "timeout": 5 } ] }
    ]
  }
}
```

**`precompact.sh`.** Appends a footer to `state.md`: the timestamp, the trigger (`auto` or `manual` from
stdin), `git rev-parse --short HEAD`, `git status --short | head -20`, the heading of the last journal
entry, and whether `gate.md` exists. It cannot know what the model was thinking; that is why the loop
rewrites `state.md` at every phase transition. The hook is the safety net for a compaction that lands
mid-phase. It never blocks compaction.

**`reinject.sh`.** Prints to stdout, which Claude Code adds to context after compaction: `state.md`,
the last journal entry, the open block of `decisions.md`, `gate.md` if present, and a fixed re-entry
instruction: "You are the arcade operator. Context was compacted. Re-enter the workflow loop at the
phase in state.md. Do not restart the iteration, do not re-plan a committed plan, do not re-spawn an
agent named in `in_flight` (SendMessage it instead). Files are truth." With `--fresh` it prints the same
plus the workflow-loop skill's file list, so a new session after a crash orients itself.

**`stop.sh`.** Reads the hook JSON from stdin. Allows the stop (exit 0, no output) when any of: not the
operator; `gate.md` exists; `roadmap.md` has no unchecked milestone; a `STOP` file exists in the workflow
dir (the owner's kill switch, creatable by a one-line phone message: "stop the loop"); the run's block
count file exceeds `iterations-per-run`. Otherwise prints
`{"decision":"block","reason":"The arcade loop is not finished and no gate is open. Read docs/superpowers/workflow/state.md and continue from its phase."}`
and increments the block count. Claude Code caps consecutive blocks at 8 by default
(`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` raises it); the iteration cap in config is set below that so the
loop's own gate fires first. This is the least certain piece of the design (section 9).

**`guard-bash.sh`.** Blocks `git push` unless `push-allowed` exists; blocks `git reset --hard`,
`git checkout -- .`, `git clean`, `rm -rf` outside the scratchpad, and anything touching `data_dir`
fixtures the owner recorded. Exit 2 with a one-line reason.

**Settings for the operator session** (user or project scope): `autoCompactWindow` at 300000 (the
`/autocompact 300k` command, or `claude --autocompact 300k` at launch), `agentPushNotifEnabled` true
(already set), a status line showing context percentage so the owner can glance at it when present.

**Not a hook:** the evidence and notification steps are the loop's own tool calls
(`SendUserFile`, `PushNotification`), because they need judgment about which two PNGs matter.

## 7. The human channel

- **Remote Control** is on for the session. The owner reads the push notification, opens the session on
  the phone, sees the evidence README and PNGs as file cards, and types an answer in plain words.
- The loop transcribes the answer into `decisions.md` under the question, deletes `gate.md`, commits,
  rewrites `state.md`, and continues. It never acts on an answer it has not written down first.
- A message that is not an answer ("stop the loop", "skip pong for now", "show me paint at 64x64") is
  handled as an instruction, journaled as an owner intervention, and the loop resumes.
- The Mac must stay awake with the lid open or `caffeinate -dims` running; a sleeping Mac ends the
  session. This is a pre-flight item and an assumption to verify on the first run (section 9).

## 8. Milestones for the roadmap

Written into `roadmap.md` at bootstrap; the owner edits before iteration 1.

- M0 (owner, before launch): spec revision 3 and plan amendments from the review; pre-flight checklist.
- M1: Task 0 environment spike (uv, Python 3.12, pins, one OpenCV, `doctor`), foundation Tasks 1 and 2.
- M2: Sensed with timestamps, velocity, `player`, `present`, zone; actors with `degrade` and festival
  scenes; canvas with text scale; look with the metre-aware `distance`.
- M3: game protocol with `SCENARIOS`, `_xy`, `MENU_ORDER`; runner with session rules, flash governor,
  brightness limiter; attract director with four modes and the mirror.
- M4: the new walk-up flow and opt-in menu; paint; contact sheet with provenance and black refusal; REPL
  with `--log`; `arcade_evidence.py`; feel metrics and budgets; bots; counterfactual and `_xy` tests.
- M5: sources (blobs on lores, gated motion grid, MediaPipe unflipped with shared mirroring, audio with
  voice band and clap), record with `--script` and `--raw`, calibrate.
- GATE A (human): record the fixture set, first live smoke, confirm dwell and presence thresholds,
  approve game order for the second plan.
- M6: project skills (`arcade-verify`, `wall-look`, `arcade-game-authoring`) and the vendored
  `cv-mediapipe` and `game-feel` skills.
- M7: second plan, games in the approved order, two per iteration, each iteration's evidence a gate
  only when a keep-or-cut question arises.
- GATE B (human): Pi in hand; Pi config, `pi_perf`, IMX500 source with munkres and scipy, systemd unit,
  status file.

## 9. Risks and what to verify on the first run

- **`Stop` hook as the driver.** Confirmed in the docs: the block JSON shape, `stop_hook_active`, and
  the 8-block cap. Not confirmed: whether the cap counts consecutive blocks across turns that did real
  work between them. First run: set `iterations-per-run: 2`, watch the loop gate itself twice, then raise
  it. If the cap ends the session early, the fallback is approach B: a shell loop that runs
  `claude --continue -p "continue the arcade loop"` while no `gate.md` exists.
- **Sleep and Remote Control.** Verify a phone answer reaches a session on a Mac with the lid closed
  under `caffeinate`. If not, lid open.
- **Compaction mid-agent.** If compaction lands while an orchestrator is running, the re-injected
  `state.md` names the agent; the operator must SendMessage it, not spawn another. Verify once by
  forcing `/compact` during iteration 1's implement phase.
- **Image reads fill context.** A 128x32 sheet at 1,536 px wide is one image; six games at two sizes and
  two looks is 24. Read only changed games, and read `feel.json` first so a failing game gets its sheet
  read and a passing one gets a glance.
- **macOS camera and microphone permission.** The first live process that opens the webcam triggers a
  system prompt no agent can answer. The owner runs `python -m arcade doctor --require camera,mic` once
  by hand in pre-flight.
- **Bypass permissions plus a public repo.** The session runs without permission prompts, so the
  `guard-bash.sh` hook and the push block are the only brakes on the remote. Keep them.

## 10. Pre-flight checklist (owner, about an hour)

1. Read the review; decide section 10 of it; approve spec revision 3 and the plan amendments (a
   separate session does the editing, with the owner present).
2. Approve this design. Then the bootstrap writes `config.md`, `roadmap.md`, `journal.md`, `state.md`,
   `decisions.md`, the hook scripts and `.claude/settings.json`, and commits.
3. `uv python install 3.12`; `uv venv --python 3.12 .venv`; grant the terminal camera and microphone
   access by running the doctor once.
4. `/autocompact 300k`; `/remote-control`; `caffeinate -dims` in another terminal; phone notifications
   on.
5. Say "start the workflow loop". Stay for iteration 1 (about an hour) to watch one gate fire.
6. Leave.
