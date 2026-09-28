# Gate: the iteration cap, after iteration 7 (2026-09-28)

Question: iterations 6 and 7 are done and the loop has stopped, as Q21 says. Does the operator move to the
show daemon now, or build M4b (the four-panel wall, 128x64) on the arcade first?

Default: Q21 stands. The operator moves to the show daemon's foundation tasks
(docs/superpowers/plans/2026-09-22-show-daemon.md); the arcade waits, with M4b first in line on its return.
Deadline: none (the loop waits for the owner; nothing is in flight)

## Where the arcade stands
- HEAD 6ebbb6d for the code; 675 tests pass, 0 skipped, 134 s. Nothing is pushed.
- it06: the small lobby, Pong, `python -m arcade run` on the camera (evidence/it06/README.md).
- it07: the oracle for games. Feel metrics with budgets, bots, the stripe check, tests for every game, the
  evidence tool, the game guide. Pong passes all 15 budgets at 128x32 (evidence/it07/README.md, feel.json).
- The Game protocol is frozen: tag `game-protocol-v1` on 6ebbb6d.
- Next milestone: M4b, 128x64 (Q32). Then M7a, six pose games in parallel.

## Decisions taken by default, for the owner to confirm or change (decisions.md)
| Q | Default taken | Operator's remark |
|---|---|---|
| Q22 | The idle lobby shows the game's title | In the it07 sheet: "PONG" in amber |
| Q23 | A duel's end card shows player 1's points | **Reads wrong**: a winner as player 2 sees "PONG 0". Lean: both scores, in the players' colours |
| Q24 | A hand raised during the end card does nothing | |
| Q25 | A hand already up must be lowered and raised again | |
| Q26 | Feel budgets: response at most 2 ticks, fidelity at least 0.8, range at least 0.6, rounds of 20 to 120 s, and the rest | `response_ticks` is fragile (C38) |
| Q27 | Win bands: good at least 0.7, lazy 0.1 to 0.7, no input at most 0.05 | Pong: 1.0, 0.2, 0.0 |
| Q28 | A lit pixel is dim when every channel is under 140; at most 10% dim | Pong's net is an override, 0.3 |
| Q29 | The GIF: 6 s from 1 s before the launch | |
| Q30 | The stripe rule: more than 5 equal pairs, changing, over 25% of the wall | |
| Q31 | Score visible at least 0.8, legible at 5 m at least 0.9; no budget for an idle hint | No metric measures a hint now |
| Q32 | Answered by the owner: 2 x 2, 128x64, top of the roadmap | M4b |

## Owner items (roadmap.md, "Owner items")
- The first live smoke: `.venv/bin/python -m arcade run`, Pong on the webcam, then on the panel; fill live-smoke.md.
  Watch for: rounds that run to the 90 s cap at 1 to 4 points; scores at 1x; whether a stranger finds the raised hand.
- The 2 x 2 wiring: the `index` pattern at 128x64, the result into evidence/hardware.md.
- Hardware bring-up with `tools/wall_pattern.py` (pixel order, brightness, gamma, firmware).
- Ten merged worktrees under `.claude/worktrees/` can be cleared.

Evidence: docs/superpowers/workflow/evidence/it06/, docs/superpowers/workflow/evidence/it07/, journal.md
(iterations 6 and 7).
