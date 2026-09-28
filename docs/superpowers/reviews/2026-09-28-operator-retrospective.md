# Operator retrospective, iterations 1 to 5

Date: 2026-09-28. Covers the two operator sessions from 2026-09-27 13:17 to 2026-09-28 13:17 (local
time, 24 hours of wall clock), HEAD `b1da614`. Status: accepted by the owner 2026-09-28 and applied the
same day. The rules as applied are in `docs/superpowers/workflow/config.md` under "Loop rules"; where they
differ from section 5 here (the wake-up is 9 minutes, the first playable is split in two), they win.

Sources: the two session transcripts and their 81 subagent transcripts under
`~/.claude/projects/-Users-trey-dev-codeisart/` (`9fa65dce…`, `b5ce046f…`), the journal, roadmap,
decisions and evidence directories, the code at HEAD, and a test run made for this review
(448 passed, 0 skipped, 21 s).

## 1. Verdict

The code is good and the loop is safe. The loop is slow because of how it is built, not because the
agents are slow, and the roadmap order puts every contact with a player, a camera and a panel at
the end.

- **Quality: high.** Clean, documented, deterministic modules with 448 tests. The plan reviews
  caught real defects before they shipped: NaN brightness driving the wall at full, the
  turn-taking flash pattern that beat the governor, a numpy `active` that would have thrown
  players out of their sessions.
- **Speed: about 10% of the wall clock was implementation.** See section 2.
- **Direction: the engine is right, the order is wrong.** After five iterations nothing can be
  played, nothing reads a camera, and no command can light a panel. The first game is at M7 and the
  first panel contact is GATE B, the last line of the roadmap.
- **Parallelism: 81 subagents were spawned and they ran as a chain.** No more than two ever worked
  at once, and no worktree isolation was used.

## 2. Where the 24 hours went

Minutes, from transcript timestamps.

| Iteration | Plan and plan review (active) | Waiting on owner | Stalled | Implement | Iteration review | Tasks |
|---|---|---|---|---|---|---|
| it01 | 16 (no plan review yet) | 0 | 0 | 33 | 2 | 7 |
| it02 | 66 | 122 (Q7) | 0 | 32 | 4 | 6 |
| it03 | 70 | 0 | 0 | 24 | 3 | 4 |
| it04 | 245 | 363 (Q11 to Q13 overnight, Q14) | 206 | 28 | 3 | 4 |
| it05 | 177 | 0 | 0 | 28 | 4 | 4 |
| Total | 574 (9.6 h) | 485 (8.1 h) | 206 (3.4 h) | 145 (2.4 h) | 16 | 25 |

Output tokens by role (3.43 million in total):

| Role | Agents | Output tokens | Share |
|---|---|---|---|
| Plan writers (with one helper) | 8 | 1,640,000 | 48% |
| Plan reviewers | 5 | 670,000 | 20% |
| Per-task reviewers | 32 | 510,000 | 15% |
| Per-task implementers | 26 | 177,000 | 5% |
| Implementation orchestrators | 5 | 173,000 | 5% |
| Main operator | 1 | 170,000 | 5% |
| Iteration reviewers | 5 | 94,000 | 3% |

## 3. Findings

**F1. The code is written in the plan, then copied.** The it05 plan is 5,296 lines and holds 4,351
lines of Python. The it05 review says "all 15 files byte-identical to the plan". Plans for it01 to
it05 total 17,979 lines; the repository holds 9,348 lines of code and tests. Implementers finish a
task in one to two minutes because they transcribe. The real implementation happens inside one
serial plan writer, which also replays the plan and runs mutation tests on it.

**F2. The same code is reviewed four times.** Plan review (two or three rounds, with its own replay
and mutation runs), a review after every task, a whole-branch review, then the iteration review.
Reviewers produced seven times the output of implementers.

**F3. Review findings became a backlog that grows.** C1 to C36 in five iterations, twelve still
open. Each iteration starts by paying carried items. Many are hardening against inputs nothing
produces yet (an unhashable player kind in `echo`, a huge-int lux reading, a numpy-array `phase`),
in an engine with no games and no real sources.

**F4. Waiting and stalls cost 11.5 hours.** Owner questions blocked for 8.1 hours before the
standing instruction of 2026-09-28. The loop then sat dead for 3.4 hours (04:33 to 07:59 local):
the operator ended its turn waiting on a plan writer, the writer was waiting on mutation runs, its
monitor expired, and nothing woke either. `stop.py` also counts turns spent waiting on agents
against the run cap (journal it01, it02; still open).

**F5. `state.md` is stale.** It says the it06 plan writer is in flight. That agent lived 30 seconds
and died with the session. The next session must treat the it06 plan as not started.

**F6. Roadmap order.** M4 (evidence tooling, feel metrics, bots), M5 (real sources), GATE A, M6
(skills) all come before the first game in M7. The gamma question, the colour order, and whether
the card honours the brightness packet all wait for GATE B, while every colour choice made before
then depends on them.

**F7. The piece with the deadline has had no work.** The show daemon (install 2026-11-11, 44 days
away) has its foundation tasks only. All operator effort so far went to the arcade, which has no
deadline.

## 4. What the research says

Collected by two research agents on 2026-09-28. The URLs are theirs; the pages were not re-read for
this document.

- One feature at a time against a pass/fail list, with a verifier the agent can trust, beats
  detailed plans. Planner output is best kept to product context and high-level design, because
  errors in a granular plan cascade.
  (anthropic.com/engineering/effective-harnesses-for-long-running-agents,
  anthropic.com/engineering/harness-design-long-running-apps)
- Parallel agents work when the units are independent and a test oracle judges them; they collapse
  when every agent hits the same shared code. (anthropic.com/engineering/building-c-compiler,
  cursor.com/blog/scaling-agents)
- Claude Code's guidance: parallel work needs disjoint file ownership; a reviewer told to find gaps
  will find some even in sound work, and chasing every finding leads to over-engineering.
  (code.claude.com/docs/en/best-practices, code.claude.com/docs/en/sub-agents,
  code.claude.com/docs/en/worktrees)
- Games: agents that cannot see the game edit blind. What works is deterministic headless runs,
  state assertions, scripted replays kept as regression tests, and frames read by the model. No
  source shows an agent judging fun; that stays with a human.
- "Write games, not engines": grow the engine from a game that runs.
  (geometrian.com/projects/blog/write_games_not_engines.html)

## 5. Proposed changes for the next operator session

Ranked by expected effect.

1. **Vertical slice first.** The next iteration delivers `python -m arcade run` with the MediaPipe
   camera source, the mirror, and one game (Pong is the simplest; Copy Me is the hero), playable on
   the Mac webcam in the SDL preview and on the panel. The director's four modes wait.
2. **Hardware now, not at GATE B.** A pattern tool over `ColorlightDisplay` (rgb bars, brightness
   steps, gamma steps, row and column index) answers the pixel order, brightness packet, firmware
   and gamma questions this week. It needs Linux and CAP_NET_RAW, so it runs from the Omarchy box
   or a Pi, not the Mac.
3. **Thin plans.** A plan holds interfaces, acceptance tests by name, constraints and decisions. No
   function bodies. Implementers write the code test-first. No mutation testing of plans.
4. **One review per iteration.** One fresh-context review of the diff, limited to correctness,
   safety and requirements. Adversarial plan review stays only for slices that touch `flash.py`,
   `brightness.py` or the Colorlight backend, one round.
5. **Carried fixes need a failing test or a real input.** Triage C28 to C36 once: keep C30 (crash
   guard) and C33; hold C34 until real lamp recordings exist; close C29 and C32 as not needed until
   something fails.
6. **Fan out the games.** After the first game proves the Game protocol, freeze it. Then three or
   four implementers at a time, each in its own worktree (`isolation: worktree`), one game each,
   owning only `arcade/games/<name>.py` and its test module. One integrator merges in order, owns
   `MENU_ORDER`, and runs the full suite. Engine changes go through a single serial lane.
   Independent lanes that can start sooner: real sources (M5), evidence tooling (M4), the show
   daemon.
7. **No blocking questions.** Make the standing instruction permanent: default at once, list at
   the check-in. Gate only on destructive actions and scope changes.
8. **Fix the stall paths.** `stop.py` skips counting while an agent is in flight; the operator
   sets a fallback wake-up whenever it waits on an agent; `state.md` is rewritten when an agent is
   found dead.

Expected result: an iteration drops from about 3.5 hours to about 1 hour for engine slices, and
games arrive three or four per iteration instead of two.
