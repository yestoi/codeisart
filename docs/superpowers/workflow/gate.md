# Gate: after iteration 8 (2026-09-28)

Question: iteration 8 (M4b, the four-panel wall at 128x64) is done and the loop has stopped, as Q33 says. Does
the operator move to the show daemon now?

Default: Q33 stands. The operator moves to the show daemon's foundation tasks
(docs/superpowers/plans/2026-09-22-show-daemon.md); the arcade waits, with C42, C43 and M7a first in line on
its return.
Deadline: none (the loop waits for the owner; nothing is in flight)

## Where the arcade stands
- HEAD 2e016e5 for the code; 723 tests pass, 0 skipped, 140 s. Nothing is pushed.
- The wall is 128x64 by default and the only layout games are judged for. The engine still runs at any size.
- Pong passes all 16 feel budgets at 128x64 (evidence/it08/README.md, feel.json). Scores at 2x.
- The small lobby is laid out for 64 rows: big title, full-height figure, a three-line card.
- `tools/wall_pattern.py index` draws the 2 x 2 wall's seams for the wiring check.
- The Game protocol is frozen at `game-protocol-v1`; `LAYOUTS` changed after it as a data value (Q33).
- Next milestone on return: M7a, six pose games in parallel, at 128x64.

## What needs the owner's ruling
| Item | What happens today | Operator's lean |
|---|---|---|
| Q23 | A duel's end card shows player 1's points. **Reads wrong**: a winner as player 2 sees "PONG 0" | Both scores, in the players' colours |
| Q35, C42 | A point counts if the paddle moved 1 px on any tick of the rally. Camera jitter counts as movement; a slow player loses points | Judge the paddle's travel over the whole rally, above the jitter |
| Q41, C43 | The card says "BEST!" for a round lost 0 to 5, and again on a repeat of the best | Only for a new best above 0 |
| Q40 | Pong is faster: rounds end by points in 34 to 73 s. The CPU is easy, the ball is fast | Keep it until the owner has played it |

## Decisions taken by default, for the owner to confirm or change (decisions.md)
| Q | Default taken | Operator's remark |
|---|---|---|
| Q22 | The idle lobby shows the game's title | "PONG" at 2x in amber |
| Q24 | A hand raised during the end card does nothing | The scripts' sweep relaunches Pong within a second of the card |
| Q25 | A hand already up must be lowered and raised again | |
| Q26 | Feel budgets: response at most 2 ticks, fidelity at least 0.8, range at least 0.6, rounds of 20 to 120 s | |
| Q27 | Win bands: good at least 0.7, lazy 0.1 to 0.7, no input at most 0.05 | Pong: 1.0, 0.55, 0.0 |
| Q28 | A lit pixel is dim when every channel is under 140; at most 10% dim | Pong's net is an override, 0.3 |
| Q29 | The GIF: 6 s from 1 s before the launch | |
| Q30 | The stripe rule: more than 5 equal pairs, changing, over 25% of the wall | |
| Q31 | Score visible at least 0.8, legible at 5 m at least 0.9; no budget for an idle hint | No metric measures a hint |
| Q34 | Pong at 128x64: paddle 16 px, ball 2 px, scores at 2x over each half | Speeds are Q40's |
| Q36 | A good round need not reach 5 points before the cap | After the retune all 20 do |
| Q37 | The lobby on 64 rows: title, card head and "BEST!" at 2x, prompt at 1x, figure 64 px | |
| Q38 | `response_px` at least 12 two ticks after the input | Pong: 28 |
| Q39 | `wall_pattern index` draws a seam at every 64 columns and 32 rows | evidence/it08/index-128x64.png |

## Owner items (roadmap.md, "Owner items")
- The first live smoke: `.venv/bin/python -m arcade run`, Pong on the webcam, then on the panels; fill live-smoke.md.
  Watch for: whether the CPU is too easy and the ball too fast; whether a playing arm starts the next game by
  itself after the card; whether a still hand scores; whether a stranger finds the raised hand.
- The 2 x 2 wiring: the `index` pattern at 128x64, the result into evidence/hardware.md. If the card can only show
  the four panels as 256x32, tell the operator: the remap goes into the display backend, a safety slice.
- Hardware bring-up with `tools/wall_pattern.py` (pixel order, brightness, gamma, firmware).
- Fourteen merged worktrees under `.claude/worktrees/` can be cleared.

Evidence: docs/superpowers/workflow/evidence/it08/, journal.md (iteration 8).
