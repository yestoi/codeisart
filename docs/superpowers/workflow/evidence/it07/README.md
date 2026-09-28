Decision: iteration 7 done. M4a (the oracle for games) landed and Pong passes it at 128x32; C37 closed; the Game protocol is frozen at tag `game-protocol-v1` (6ebbb6d). The loop gates here on the iteration cap (owner decision Q21); the next arcade milestone is M4b, the four-panel wall at 128x64 (Q32).

# Evidence, iteration 7 (feel metrics and budgets, bots, the pattern check, the generic tests, the evidence tool, the game guide)

- **HEAD at verify:** 06172ed (head.txt). The code's last commit is 6ebbb6d, the review's fix; 06172ed adds only the operator's workflow files. `feel.json`, `games.md` and all six PNGs carry 06172ed and were made from a clean tree.
- **Plan:** docs/superpowers/plans/2026-09-28-it07-oracle-for-games.md (6ddaf78), 298 lines. Not a safety slice, so no plan review.
- **Implementation review:** APPROVED after 2 rounds. Round 1 blocked on one finding, B1: `idle_hint_seconds` passed without an idle hint (reviewer-round1.md). The fix 6ebbb6d renamed it `presence_answer_seconds` and took its budget away; round 2 confirmed it (reviewer-round2.md). The orchestrator's report, with the fix as its last section, is orchestrator-report.md.

| Check | Result | File |
|---|---|---|
| Collected | 675 (it06: 596) | collect.txt |
| Test command | 675 passed, 0 skipped, 133.6 s (it06: 36.9 s) | pytest.txt |
| Removed or changed asserts in 6ddaf78..6ebbb6d | one removed assert line in the whole diff, extended not weakened (round 1, ruling 3); the fix's changes ruled in round 2 | reviewer-round1.md, reviewer-round2.md |
| `arcade doctor --require camera,pose` | camera ok, pose ok (landmarker 18 ms), exit 0 | doctor.txt |
| Evidence tool, first run from the command line by the operator | exit 0, 8 files | games.md |
| Pong's feel at 128x32, 20 seeds | 15 budgets, `failures` empty | feel.json |
| Strobe check, lobby plus Pong duel, 3000 ticks | held 0; `flash_area` raw 0.000, pushed 0.000; `concurrent_area(pushed)` 0.001 of 0.1; `square_flashes(pushed)` 2 of 6; exit 0 | strobe-check.txt |
| Canonical sheet, plain, LED look and at 5 m | attract title, mirror, raised hand, Pong to 0-3 in 30 s | pong-128x32-plain.png, -led.png, -distance.png |
| Canonical GIF, 6 s from 1 s before the launch | 9.6 KB; first frame read, motion not judged by eye | pong-128x32-canonical.gif |
| Timeline and trace of the canonical run | attract 0.03, invite 3.53, serve 4.57, play 5.53 | pong-128x32-timeline.txt, -trace.jsonl |
| Raw against pushed, 40 ticks at the largest raw change | the card to mirror step at t958, one step, raw and pushed alike | it07-128x32-strobe-raw-vs-pushed.png |

## Pong's feel table (from feel.json)

| Metric | Value | Budget | Margin |
|---|---|---|---|
| response_ticks | 2.0 | at most 2 | none: see "What is weak" |
| fidelity | 0.995 | at least 0.8 | wide |
| range | 0.774 | at least 0.6 | fair |
| lit_fraction | 0.022 | 0.01 to 0.5 | near the floor: Pong is a sparse picture |
| dim_fraction | 0.189 | at most 0.3 (Pong's own, default 0.1; reason: the dim net) | fair |
| liveliness | 0.0035 | at least 0.001 | fair |
| flash_area_raw | 0.0 | at most 0.1 | wide |
| square_flashes | 0 | at most 6 | wide |
| score_visible | 0.959 | at least 0.8 | fair |
| score_legible | 1.0 | at least 0.9 | wide |
| win_good | 1.0 | at least 0.7 | wide |
| win_lazy | 0.2 | 0.1 to 0.7 | near the floor |
| win_none | 0.0 | at most 0.05 | wide |
| round_seconds | 92.0 | 20 to 120 | every round runs to the 90 s cap |
| phases_reached | 1.0 | 1.0 | exact |
| presence_answer_seconds | 0.0 | none | measured only |

How the evidence was made (the plan's I2). `arcade_evidence` takes the sha once and ignores its own `--out`; `arcade_shot` still stamps `+dirty` when `git status` lists anything, so its sheets were written outside the repository, with the new evidence folder moved aside for that run, and copied in:

```
.venv/bin/python -m tools.arcade_evidence --iteration 7 --games pong --out docs/superpowers/workflow/evidence/it07
.venv/bin/python -m tools.arcade_shot pong --lobby small --scenario duel --raw-vs-pushed --out <scratch>/it07-128x32-strobe > <scratch>/strobe-check.txt
```

**The operator's read of the sheets.**
- The empty wall shows the lobby's title "PONG" in amber (0 and 1.5 s). it06's sheet had no attract; this one has.
- The body's mirror stands in amber at 3.0 s and has its hand up beside the green pictogram at 4.5 s.
- Pong plays from 6.0 s: amber paddle and score at the left, the green CPU at the right, a white ball, a dim blue net. The "+1" under the CPU's 3 at 21.0 s reads.
- At 5 m every digit reads, and the net is visible without competing with the ball.
- The scripted body loses 0-3 in 30 s. A script is not a player; the good bot wins 20 plays of 20.
- On the strobe sheet the end card stands still for 20 frames, then the two mirrors appear in one step and the pictogram fades in over about 12 ticks. Raw and pushed are the same.

**What is weak.**
- `response_ticks` sits on its max. The reviewer measured that Pong answers in 1 tick and that the 2.0 comes from where the probes fall (5.0 with 4 or 16 probes on one seed). The metric is fragile, not Pong. Carried as C38.
- Every judged round ends at the 90 s cap, at 1 to 4 points against 0. No stated requirement is missed; whether a round should reach 5 points is for the owner's live test.
- The scores are drawn at 1x. They read at 5 m; spec 7.4 asks for 2x, which reads to 10 m. Carried as C39.
- No metric measures an idle hint. The one built in this iteration measured the seat's colour and was taken out of the budgets by the review.
- `games.md` prints "yes" for `presence_answer_seconds`, which has no budget. Carried as C40.
- An idle body banks 1 or 2 points on 3 seeds of 10, and they are stored as a best.
- The GIF was checked by its first frame, its length and its size, not watched.
- All of this is at 128x32. The wall is now four panels, 128x64 (Q32): nothing here was run at that size.

Success criteria: Pong runs headlessly from scripts and bots and gives sheets, a GIF and feel metrics an agent can judge; it meets its feel budgets on the one layout it declares; the flash governor and the limiter hold through the lobby and Pong. The owner's live smoke is still open: `.venv/bin/python -m arcade run`.
