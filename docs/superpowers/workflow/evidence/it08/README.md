Decision: iteration 8 done. M4b landed: the wall is 128x64 by default and the only layout games are judged for (Q32, Q33); Pong passes all 16 budgets there; C38, C39, C40 and C41 closed; two new fixes carried (C42, C43). The loop gates here (Q33) and the operator moves to the show daemon.

# Evidence, iteration 8 (the four-panel wall, 128x64)

- **HEAD at verify:** 99e09f6 (head.txt). The code's last commit is 2e016e5; 43c95c7 and 99e09f6 add only the operator's workflow files. `feel.json`, `games.md` and all six stamped PNGs carry 99e09f6 and were made from a clean tree.
- **Plan:** docs/superpowers/plans/2026-09-28-it08-four-panel-wall-128x64.md (167d513), 285 lines. Not a safety slice, so no plan review.
- **Implementation review:** APPROVED in round 1, 0 blocking (reviewer-round1.md). The orchestrator's report, with its 11 deviations, is orchestrator-report.md.
- **Diff:** 167d513..2e016e5, 32 files, 806 lines added, 235 removed. `arcade/flash.py`, `arcade/brightness.py`, `show/display/colorlight.py` and the runner are unchanged.

| Check | Result | File |
|---|---|---|
| Collected | 723 (it07: 675) | collect.txt |
| Test command | 723 passed, 0 skipped, 139.7 s (it07: 133.6 s) | pytest.txt |
| Changed asserts in 167d513..2e016e5 | 20 changed assert lines, none weakened (the review read each) | reviewer-round1.md |
| `arcade doctor --require camera,pose` | camera ok, pose ok (landmarker 11 ms), exit 0 | doctor.txt |
| Evidence tool | exit 0, 8 files | games.md |
| Pong's feel at 128x64, 20 seeds | 16 budgets, `failures` empty | feel.json |
| Strobe check, lobby plus Pong duel, 3000 ticks | held 0; `flash_area` raw 0.000, pushed 0.000; `concurrent_area(pushed)` 0.001 of 0.1; `square_flashes(pushed)` 3 of 6; 3000 frames, none black; exit 0 | strobe-check.txt |
| Raw against pushed, 40 ticks at the largest raw change | the card to mirror step at t2216, one step, raw and pushed alike | it08-128x64-strobe-raw-vs-pushed.png |
| Canonical sheet, plain, LED look and at 5 m | attract title, mirror, raised hand, a round of Pong to 0-5 in 18 s, the card, a second launch | pong-128x64-plain.png, -led.png, -distance.png |
| Canonical GIF, 6 s from 1 s before the launch | 256x128, 52 frames, 14.9 KB; first frame read, motion not judged by eye | pong-128x64-canonical.gif |
| Timeline and trace of the canonical run | attract 0.03, launch 4.53, points from 6.20, over 17.90, second launch 23.83 | pong-128x64-timeline.txt, -trace.jsonl |
| Walk-up sheet, 100 s through the small lobby | five sessions, each from a raised hand to the card | it08-walkup-plain.png, -led.png |
| The wall pattern for the 2 x 2 check | seams at column 64 and row 32, four corner marks, ticks every 8 px | index-128x64.png |
| `arcade run` with no size given | logs "wall 128x64, backend sdl", exit 0 | run-default.txt |
| Tick budget at 8192 pixels | 0.53 to 0.59 ms a tick against 2.0 ms (the suite's test and the orchestrator's runs) | orchestrator-report.md |

## Pong's feel table (from feel.json)

| Metric | Value | Budget | Margin | it07, at 128x32 |
|---|---|---|---|---|
| response_ticks | 1.0 | at most 2 | fair: it is latency alone now (C38) | 2.0 |
| response_px | 28.0 | at least 12 | wide | new |
| fidelity | 0.994 | at least 0.8 | wide | 0.995 |
| range | 0.762 | at least 0.6 | fair | 0.774 |
| lit_fraction | 0.026 | 0.01 to 0.5 | near the floor: Pong is a sparse picture | 0.022 |
| dim_fraction | 0.153 | at most 0.3 (Pong's own, default 0.1; reason: the dim net) | fair | 0.189 |
| liveliness | 0.0026 | at least 0.001 | fair | 0.0035 |
| flash_area_raw | 0.0 | at most 0.1 | wide | 0.0 |
| square_flashes | 0 | at most 6 | wide | 0 |
| score_visible | 0.974 | at least 0.8 | fair | 0.959 |
| score_legible | 1.0 | at least 0.9 | wide; the oracle looks for 2x digits only (C39) | 1.0 at 1x |
| win_good | 1.0 | at least 0.7 | wide | 1.0 |
| win_lazy | 0.55 | 0.1 to 0.7 | fair; it moved from 0.2 with the retune | 0.2 |
| win_none | 0.0 | at most 0.05 | wide | 0.0 |
| round_seconds | 46.6 | 20 to 120 | fair: rounds end by points now, not at the cap | 92.0 |
| phases_reached | 1.0 | 1.0 | exact | 1.0 |
| presence_answer_seconds | 0.0 | none | measured only; games.md prints "-" (C40) | 0.0 |

No band in `arcade/feel_budgets.toml` was loosened: the only change to that file adds `response_px` min 12. Pong's one override moved from 128x32 to 128x64 with the same number and reason.

How the evidence was made (the plan's I2). `arcade_shot` stamps `+dirty` when `git status` lists anything, so its sheets and the pattern were written to the scratchpad from a clean tree before the evidence tool made this folder, then copied in. A first run was thrown away: a hook had added a footer to state.md, and the sheets read `43c95c7+dirty`. The footer was committed (99e09f6) and every command was run again.

```
.venv/bin/python -m tools.arcade_shot pong --lobby small --scenario duel --raw-vs-pushed --flash-report --out <scratch>/it08-128x64-strobe > <scratch>/strobe-check.txt
.venv/bin/python -m tools.arcade_shot pong --lobby small --scenario canonical --look both --out <scratch>/it08-walkup
.venv/bin/python -m tools.wall_pattern index --png <scratch>/index-128x64.png
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m arcade run --seconds 5 --script walkup > <scratch>/run-default.txt 2>&1
.venv/bin/python -m tools.arcade_evidence --iteration 8 --games pong --out docs/superpowers/workflow/evidence/it08
```

The two long strobe sheets and the walk-up's distance sheet (2.6 MB each) were read and left out of the repository.

**The operator's read of the sheets.**
- The empty wall shows "PONG" at 2x in amber, centred.
- The mirror figure stands the wall's full height with 2 px strokes. With the hand up, the green pictogram is beside the hand.
- Pong: amber paddle and score at the left, the green CPU at the right, both scores at 2x over their halves, a white 2 px ball, a dim blue net, "+1" pops under the scorer's digit, a row of rings when the round ends.
- The card is three lines: "PONG 0" and "BEST!" at 2x, "HAND UP = AGAIN" at 1x.
- At 5 m the scores and the card's big lines read well. The 1x prompt reads, less easily.
- On the strobe sheet the duel's card "PONG 5 / HAND UP = AGAIN" stands still for 20 frames, then two mirrors (amber, blue) appear in one step and the pictogram fades in from dim to bright green. Raw and pushed are the same.

**What is weak.**
- The card says "BEST!" for a round lost 0 to 5, and says it again when the next round ends on the same score. `arcade/attract/lobby.py:298` compares the score with tonight's best using `>=`, and the first score of a night is always a best. The code is it06's; 128x64 made it easy to see. Carried as C43, with Q41.
- Pong's movement rule (C41's fix) judges single ticks. The review reproduced two wrong outputs: under real camera noise a still raised hand banks points on 7 seeds of 10 and stores a best on 10 of 10; on clean input a slow player who moved 17 to 20 px in a rally loses the point. Carried as C42. C41's own case holds: a body with its hands down scores nothing.
- The scripted body loses every round in the sheets (0-5 three times, 2-5 once). A script is not a player; the good bot wins 20 plays of 20. The sheets show the phases, not a good game.
- The balance is for the owner's hands (Q40): the CPU moves 22 px a second and a bot with a 0.33 s delay beats it 40 times of 40; the fastest ball asks a human for up to 4.8 px a tick.
- The top of a script's sweep counts as a raised hand, so Pong starts again within a second of each card. Q24 and Q25 hold. Whether a real player's arm does the same is for the live smoke.
- A walking figure trails its body by 1 column (the lobby's `COLUMN_SLACK`, which fixed a flicker of 0.1006 against 0.1 at 128x64).
- The GIF was checked by its first frame, its length and its size, not watched.
- Nothing here ran on the panels. The 2 x 2 wiring is untested.

Success criteria: Pong meets its feel budgets in full at 128x64; at a size it does not declare (128x32, 96x48) it runs, and its scores stay legible; `arcade run` opens 128x64 by default; the flash governor and the limiter hold through the lobby and Pong. The owner's live smoke is still open: `.venv/bin/python -m arcade run`.
