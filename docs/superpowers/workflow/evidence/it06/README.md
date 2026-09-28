Decision: iteration 6 done. M3b (first playable, headless) and M3c (the camera source and `python -m arcade run`) both landed; C30 and C31 closed; C37 carried. Continue to iteration 7 with M4a, the oracle for games.

# Evidence, iteration 6 (the small lobby, Pong, arcade_shot, the camera, `arcade run`)

- **HEAD at verify:** c15f86c (head.txt). The code's last commit is b6cede1; c15f86c adds only the operator's state file. All PNGs carry `git` = c15f86c in a text chunk and were made from a clean tree.
- **Plan:** docs/superpowers/plans/2026-09-28-it06-first-playable-headless.md (ab40231), 299 lines. Not a safety slice, so no plan review.
- **Implementation review:** APPROVED in round 1, 0 blocking (reviewer-verdict.md, reviewer-notes.md). The orchestrator's report is orchestrator-report.md.

| Check | Result | File |
|---|---|---|
| Collected | 596 (it05: 448; 478 at this iteration's base) | collect.txt |
| Test command | 596 passed, 0 skipped, 36.9 s | pytest.txt |
| Removed test lines since ab40231 | one import line in test_headless.py, replaced by a longer one; no assert removed or changed | removed-test-lines.txt |
| `arcade doctor --require camera,pose` | camera ok, pose ok (landmarker 16 ms), exit 0 | doctor.txt |
| Strobe check, lobby plus Pong duel, 3000 ticks | held 0; `flash_area` raw 0.000, pushed 0.000; `concurrent_area(pushed)` 0.001 of 0.1; `square_flashes(pushed)` 2 of 6; exit 0 | strobe-check.txt |
| First-playable sheet, one cell a second | walk-up, mirror, pictogram, Pong, end card, three sessions | it06-128x32-first-playable.png |
| The same at 5 m | figures, digits, paddles, ball and card text all readable | it06-128x32-first-playable-distance.png |
| Raw against pushed, 40 ticks at the largest raw change | the card to mirror step at t773, one step, raw and pushed alike | it06-128x32-strobe-raw-vs-pushed.png |
| `MediaPipeCamera` on the real camera (the reviewer, 6 s) | 60 results at 10 fps, age 0.011 to 0.023 s, nobody in view, clean close | reviewer-verdict.md |
| `python -m arcade run --seconds 5 --script walkup`, SDL dummy | exit 0 (orchestrator; the reviewer ran 8 s, Pong launches at tick 96) | orchestrator-report.md |

No feel table and no GIFs yet: both come with M4a.

How the sheets were made (the plan's I2, with the output outside the repository first, because `arcade_shot` stamps `+dirty` when `git status` lists anything, its own new files included):

```
.venv/bin/python -m tools.arcade_shot pong --lobby small --scenario duel --every 30 --cols 6 --out <scratch>/it06-128x32-first-playable
.venv/bin/python -m tools.arcade_shot pong --lobby small --scenario duel --raw-vs-pushed --out <scratch>/it06-128x32-strobe > <scratch>/strobe-check.txt
```

The second command also wrote a plain and a distance sheet of the same run (1.6 MB); they repeat the first command's sheets and are not kept.

**The operator's read of the sheets.**
- Player 1's figure is orange at the left from tick 0, player 2's blue at the right by 1.0 s. Both fill the wall's height and read as people, at scale 2 and at 5 m.
- The green hand-up pictogram stands beside player 1 at 2.0 s. Pong serves at 3.0 s.
- Pong shows a paddle at each edge in its player's colour, the two digits in the same colours, a dim blue dashed net, a white ball, "+1" under the scorer's digit, and four dotted rings in the winner's colour when the game is over. Paddles are clamped to the wall (`pong.py:205`).
- Game 1 ends 0-5 at about 21 s, then the card shows for 3 s, then the mirror, then the next game. Games 2 and 3 end 5-1 and 5-0.
- The step from the card to the mirror is the largest change of the run. It is one step; nothing flashes.

**What is weak.**
- After a duel that player 2 wins 5-0 the card reads "PONG 0". That is Q23's default; on the wall the winner reads a zero. It goes to the owner at the gate.
- The attract title is not in the sheet, because the duel script starts with player 1 in view. Only the test sees it.
- The scripted sweep is not a player: shifting the script by one second turns game 1 from 5-0 into 0-5, and the solo script under real noise scores 0. Difficulty is judged with M4a's bots.
- On 64x64 under real noise the mirror's limbs blink (raw `concurrent_area` 0.131 to 0.151). The governor holds it under the limit, so the wall is safe, and the figure smears. Carried as C37.

Success criteria: Pong runs headlessly from a script through the real runner and gives a sheet an agent can judge. The flash governor and the limiter hold through the lobby and Pong. The walk-up to the serve is 3.0 s in the script; whether a stranger finds the raised hand is the owner's live smoke, which can now be played: `python -m arcade run`.
