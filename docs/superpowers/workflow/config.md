# Workflow config — wall arcade
- Phase: 1 (Mac). Phase 2 (Pi 5) is a config change made at GATE B.
- Deploy: none (phase 1, Mac)
- App URL: none (local Python process; verification is headless)
- Test: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs` (run from repo root). In a worktree, run the same command with the main checkout's interpreter, `/Users/trey/dev/codeisart/.venv/bin/python`, from the worktree's root.
- Evidence: `.venv/bin/python tools/arcade_evidence.py --iteration <N> --games changed`, written to docs/superpowers/workflow/evidence/itNN/. That tool is built in M4a. Until then, evidence is `tools/arcade_shot.py` output (built in M3b; run it as `python -m tools.arcade_shot`) plus the test command's output saved to the same evidence dir, with a README.md whose first line is the decision.
- Screenshots dir: docs/superpowers/workflow/evidence/
- Freshness check: every PNG in evidence/itNN/ carries the git sha in its header and it must equal HEAD. Before M4a, the evidence README records HEAD by hand (`git rev-parse --short HEAD`). A mismatch is a tooling defect, fixed before anything is judged.
- Gates: gate-deploys: false, gate-iteration-plans: false
- Plan review: only for a safety slice (Loop rule 4), one round. Verdict in evidence/itNN/plan-review.md. (Owner decision 2026-09-28; it replaces Q6's review of every plan.)
- iterations-per-run: 6
  (Keep it below 8, Claude Code's consecutive Stop-hook block cap. The Stop hook reads this line as the number of blocks it gives with nothing committed between them. The loop counts iterations itself and gates at step 8.)

## Loop rules
Owner-approved 2026-09-28, after the retrospective in docs/superpowers/reviews/2026-09-28-operator-retrospective.md.
These override the workflow-loop skill (its step 1's "every item in Carried fixes", its Orchestrator Prompt and
its Reviewer Prompt included), superpowers:writing-plans, superpowers:subagent-driven-development, sections 4
and 5 of the operator design, and the core plan's "How to read this plan now" (test modules are no longer
copied verbatim) wherever they differ. Use the prompts under "Prompts" below in place of the skill's. Agents do
not read this file by themselves.

1. **Thin plans.** An iteration plan holds the slice and its files, the interfaces (signatures, dataclass
   fields, constants with their values), the acceptance tests by name with one line each on what they
   assert, the constraints, and the decisions taken. It holds no function bodies and no test bodies. It stays
   under 300 lines. The plan writer does not replay the plan and does not run mutation tests. If the plan
   phase passes 30 minutes, the plan is too detailed: commit what is there and move on.
   Where the core plan already has a body for a task, the iteration plan names its lines and lists what
   the amendments and the roadmap's notes change. It does not copy the body, and the implementer treats the
   core plan's code as a draft to test, not as text to paste.
2. **Implementers write the code.** Each implementer works test-first (superpowers:test-driven-development)
   from the plan's interfaces and acceptance tests, runs the test command, and commits. Use `model: opus` for
   engine, safety, lobby and source tasks, `model: sonnet` for games and tools. The plan writer is one agent,
   `model: opus`.
3. **One review per iteration.** One fresh-context reviewer (`model: opus`) reads BASE..HEAD once. It reports
   only: correctness bugs, safety gaps (brightness, flashing), requirements the spec or plan states that the
   code misses, and removed or weakened asserts. There is no review after each task and no separate
   whole-branch review inside the orchestrator. Blocking findings are fixed and re-reviewed once.
4. **Safety slices.** A slice is a safety slice when it changes `arcade/flash.py`, `arcade/brightness.py`,
   `show/display/colorlight.py`, or the order in which the runner applies the limiter, the governor and the
   push. Only a safety slice gets an adversarial plan review, one round: if it blocks, the writer fixes and
   the reviewer confirms, and that is the end of it. For a safety slice the plan may hold the exact test
   bodies for the safety property.
5. **What is carried.** A finding becomes a Carried fix only when it is (a) a failing test or a wrong output
   reproduced from an input that a source, game or config in the repository produces today, or (b) a safety
   gap. Anything else is one line under "Noted, not carried" in the journal entry. An iteration takes the
   Carried fixes tagged for the files its slice touches, not the whole queue.
6. **Parallel work.** Tasks that own different files run at the same time. The orchestrator spawns them in
   one message, each with `isolation: "worktree"`, at most four at once. Each implementer commits on its
   worktree's branch. The orchestrator is the integrator: it merges the branches into main one at a time in
   plan order, runs the full test command after each merge, and is the only one that edits shared files
   (`arcade/games/__init__.py`, `arcade/sources/__init__.py`, `arcade/bots.py`, `arcade/feel_budgets.toml`,
   `arcade/main.py`, `arcade/config.py`, `arcade.toml`, `pyproject.toml`, `.gitignore`,
   `tests/arcade/helpers.py`, `tests/conftest.py`). Engine files (`arcade/runner.py`, `arcade/headless.py`,
   `arcade/game.py`, `arcade/sensed.py`, `arcade/canvas.py`, `arcade/juice.py`, `arcade/input.py`) are one
   serial lane in the main checkout: one task at a time, done before the parallel tasks that build on it
   start, and no game task is in flight while one of them changes. A file no rule names belongs to the task
   the plan gives it to; the plan lists every file of every task, and no file appears under two tasks.
   - Worktrees start from HEAD, so commit the plan and the state files before spawning.
   - `/models/` and `/data/` are not in git. A task that needs the pose model, the camera or the microphone
     runs in the main checkout, not in a worktree.
   - In a worktree, run tools as modules from the worktree's root (`python -m tools.arcade_shot`), never by
     path: run by path, a tool imports the main checkout's `arcade`, not the worktree's.
   - A merge that breaks the suite is undone with `git revert -m 1 <merge sha>`, and the task goes back to
     its implementer. `git reset --hard` and `git branch -D` are blocked by the guard; a failed branch is
     left where it is and named in the journal.
7. **Waiting on an agent.** Before ending a turn to wait, write `state.md` with the agent's name and the
   time in `in_flight`, and start a fallback wake-up: the Bash command `sleep 540` with
   `run_in_background: true`, whose exit starts a turn (tested 2026-09-28; 540 because a Bash command is
   limited to 600 seconds). On a wake-up with no report, check the agent (ListAgents, or its commits and
   files). If it is working, rewrite `state.md` with the time of the check and start another wake-up. If it
   is gone, set `in_flight` to none and redo its work from the files. No agent runs a single command that
   takes over 10 minutes: no mutation runs, no long soaks.
8. **Owner questions never block.** Write the block in `decisions.md`, take the default at once, mark it
   `defaulted`, and list it at the next check-in. The loop writes `gate.md` only for: a destructive or
   irreversible action, a change to the roadmap's scope or end goal, or the iteration cap. A step that only
   the owner can do (hardware, a live smoke, a recording) goes into "Owner items" in the roadmap and the loop
   carries on with the next milestone that does not need it.
9. **Never change directory.** No `cd` in a Bash command: use absolute paths and `git -C`. Agents in a
   worktree use the worktree's absolute path.
10. **Time and size.** A slice is what fits the time, not a count of tasks: about six tasks when most run
    in parallel. An engine iteration should take about 90 minutes and a games iteration about two hours. The
    journal entry records the minutes spent in plan, implement and review. An iteration that takes twice its
    target says why under "Loop decisions".

## Prompts
These replace the skill's Orchestrator Prompt and Reviewer Prompt. Fill the angle brackets.

Orchestrator (step 3, `model: opus`):
```
You are the implementation orchestrator and integrator for iteration <N> of the wall arcade.
Repository: /Users/trey/dev/codeisart. Read the plan at <plan-path> fully before dispatching.
The plan is thin: interfaces, acceptance tests by name, constraints. Implementers write the code.
1. Serial lane first, in the main checkout, one implementer at a time: <the plan's engine tasks>.
2. Then the parallel tasks, spawned in ONE message, each with isolation: "worktree", at most four at once.
   A task that needs the pose model, the camera or the microphone runs in the main checkout instead.
3. Every implementer: superpowers:test-driven-development; model opus for engine, safety, lobby and source
   tasks, sonnet for games and tools; given its task, its files, the plan's constraints and these rules:
   touch only your files; never use `cd` (absolute paths, `git -C`); test with
   `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs`
   from your checkout's root; run tools as modules (`python -m tools.<name>`); no command over 10 minutes;
   commit on your branch; report the files changed, the test counts and any deviation from the plan.
4. Merge the branches into main one at a time in plan order with `git -C /Users/trey/dev/codeisart merge
   --no-ff <branch>`, and run the full test command after each. Undo a merge that breaks the suite with
   `git revert -m 1 <sha>` and send the task back once. You alone edit the shared files (config.md rule 6).
5. No review agents: the loop reviews the whole iteration once.
Rules: never deploy; never push; if a task is blocked or the plan is wrong, record the deviation and go on
with the tasks that do not depend on it; do not invent scope.
Your final message is machine-read. Return exactly:
## Completed
## Deviations
## Test status (command + counts)
## Commits (sha + subject)
## Minutes (serial lane, parallel tasks, integration)
```

Reviewer (step 4, `model: opus`, one per iteration):
```
Review commits <BASE>..HEAD in /Users/trey/dev/codeisart against the plan at <plan-path> and the spec
docs/superpowers/specs/2026-09-26-wall-arcade-design.md. Never use `cd`. Report only:
- correctness bugs you can show with an input the code will meet (give the input and the wrong result);
- safety gaps: a path by which a frame reaches the display without the limiter and the governor, or
  brightness over the configured level;
- requirements the spec or the plan states that the code does not meet;
- removed or weakened asserts: list every removed or changed `assert` in `git diff <BASE>..HEAD -- tests/`;
- a drop in `pytest --collect-only -q | tail -1` or a rise in skipped tests.
Do not report style, naming, hardening against inputs nothing produces, or tests you would have added.
Your final message is machine-read. Return exactly:
## Verdict: APPROVED | BLOCKED
## Blocking findings (file:line, the input, what happens, why it blocks)
## Noted, not carried (one line each)
```

## Verify checklist
Replaces the walkthrough checklist; run inline in the main session (design section 4, step 6). No walker agent in phase 1.
1. Freshness: the evidence sha equals HEAD (see Freshness check above).
2. The test command is green.
3. Skip count has not risen since the last journal entry (`-rs` output, count of SKIPPED), unless the rise is journaled with a reason.
4. Collected count has not dropped (`pytest --collect-only -q | tail -1`), unless journaled with a reason.
5. `.venv/bin/python -m arcade doctor` passes for the sources this slice needs (once doctor exists, from M1).
6. Evidence written to evidence/itNN/ with the matching sha: README with the decision on line 1, sheets, GIFs, feel table once feel metrics exist (M4a).
7. The main session has read the changed games' sheets and GIFs itself with the Read tool (read `feel.json` first; a failing game gets its sheet read closely) and written the verdict into the journal before any other tool call.

## Success criteria
- The roadmap end goal: a stranger is playing within ten seconds of walking up, unprompted.
- Every game in the accepted list runs headlessly from scripted inputs and produces sheets, GIFs and feel metrics an agent can judge.
- Every game meets its feel budgets in full on each layout it declares; on undeclared layouts it runs and stays legible.
- 128x32 is the design layout; 64x64 is first-class for single-player games and square visuals.
- The flash governor and brightness limiter hold on every game and attract mode (at most 3 full-field flashes per second).
- The owner's live smoke (live-smoke.md) scores each shipped game "responded: y" and "understood: y" on both layouts it declares.
