Decision: iteration 19 done. Copy Me, Flap, Swat and Freeze are on main (bb9fd70..d81599e) and each reads as a game at 128x64 from the invite to its end: 17 feel metrics a game, every budget met, no override; the suite reads 2092 collected, 2089 passed, 3 skipped in 476.51 s under Q102's 540 s (plan review approved in round 2 after nine findings; code review APPROVED in round 2 after one blocking finding, rows 60 to 63 lit by Freeze's topple and Flap's hint, fixed test-first); one flaw is carried, C55: Copy Me's cyan outline is not seen on player 2's blue figure; nobody has played any of the four on a camera yet, the first live plays are the owner's

# Evidence, iteration 19 (four pose games: Copy Me, Flap, Swat, Freeze)

Code head d81599e (the reviewed range is bb9fd70..d81599e). The sheets are stamped `095c58d`, HEAD when they were
made; 77b20b1 and 095c58d change only `docs/`. Made with
`.venv/bin/python tools/arcade_evidence.py --iteration 19 --games copyme,flap,swat,freeze` on a clean tree.
Nothing here was run on the Pi or on the card. The images (`*-led.png`, `*-plain.png`, `*-distance.png`,
`*-canonical.gif`) are on the Mac beside this file and are not committed (Q98); what they show is said in words
below.

## Feel (games.md, feel.json; 128x64, 20 report seeds)

| Game | win good / lazy / none | round s | fidelity | range | flash_area_raw | square_flashes | lit | score_visible |
|---|---|---|---|---|---|---|---|---|
| Copy Me | 1.0 / 0.4 / 0.0 | 24.0 | 0.9996 | 0.701 | 0.0111 | 4 | 0.108 | 0.978 |
| Flap | 1.0 / 0.6 / 0.0 | 49.0 | 0.9903 | 0.825 | 0.0 | 0 | 0.056 | 1.0 |
| Swat | 0.95 / 0.35 / 0.0 | 66.2 | 0.9543 | 0.873 | 0.0031 | 2 | 0.028 | 1.0 |
| Freeze | 1.0 / 0.4 / 0.0 | 52.9 | 0.9999 | 0.921 | 0.0186 | 5 | 0.099 | 1.0 |

`failures: []` for all four; `phases_reached` 1.0; `response_ticks` 1.0 to 1.5 (budget 2). Freeze's 5 square
flashes are one under the budget of 6. Copy Me's range 0.701 is the nearest to its floor (0.6), and its round of
24 s the nearest to the 20 s floor.

## What each sheet shows (read by the operator with the Read tool)

| File | What it shows |
|---|---|
| `copyme-128x64-led.png` | The name in dim amber, the mirror figure, the green hand-up pictogram, then the game from 6 s. `show`: the amber figure with the target as a small cyan figure on its chest and the pose's name in white at the bottom (`ARMS UP`, `AIRPLANE`, `DISCO`); the score top left in amber at 2x. `play`: the cyan outline grows to the figure's size; `STRIKE THE SHAPE` while the player waits. At zero one sample is a light grey field: the engine's flash. `result`: `MATCH!` in green at 2x, the matched arm green, `+100` on the chest; the score reads 100, 200, 300. `over`: three green dots and the score. The words cover the lower legs (Q120). |
| `flap-128x64-led.png` | `ready` from 6 s to 20 s: the bird is a 5 by 4 amber block at column 28, the gauge's marker runs between two white ticks at the left edge, `FLAP TO FLY` in amber, the green floor line on row 59, the score `0` top right. `play` from 21 s: green pipes in pairs with a wide gap, the bird between them, the score 1 at 27 s. The sheet ends before any crash. |
| `swat-128x64-led.png` | The amber run bar on row 0, `1` and `GO!`, then squares of four colours and round red bombs, one to three at a time; the blade is a small amber block with a thin trail. A cut shows `+1` in the fruit's colour and a ring of dots; the bomb at 24 s shows `-3` in red and the score falls from 2 to 0; `SWIPE!` is the hint at 10.5 s. Small and sparse (lit 0.028), nothing hard to tell apart. |
| `freeze-128x64-led.png`, `freeze-128x64-canonical.gif` | `ready`: `DANCE ON GREEN` in green over `FREEZE ON RED` in red. `play`: a 1 px green border and `DANCE` at 2x, then a red border and `FREEZE`: one colour change, no filled field. The scripted player is out on the first red both times: `OUT` in red, the figure on its side in dim amber above the bottom rows, fading; the card `FREEZE 0` / `HAND UP = AGAIN`. No sample shows a red stood through or a score above 0. From 12 s the figure stands half off the wall at the mat's right end. |
| `*-plain.png`, `*-distance.png` | The same samples without the LED look, and at the 5 m look. |
| `*-timeline.txt`, `*-trace.jsonl` | The phases with their times, and the canonical run's trace (committed). |

The operator's own extra sheets (the scratchpad, not in the repository): Copy Me `duo` (seat b's blue figure hides
the cyan outline: C55; the two scores cover a head under them), Flap's later play (score 10, the red crash,
`FLAP AGAIN`), Swat `duo` (two blades, one score), Freeze `duo` (the round ends at the first out, `P1 WIN`), and
Flap's `idle_body` after the fix at 095c58d (`ARMS UP THEN DOWN` on rows 37 to 43, one line above `FLAP TO FLY`,
nothing in rows 60 to 63; `flash_area` raw 0.000, held ticks 0).

What no sheet shows: Swat's combo, a Freeze round won, any of the four under a real camera.

## The suite's time (the Mac, shared; the limit is 540 s, Q102)

| Run | Head | Collected | Passed | Skipped | Time | Load | File |
|---|---|---|---|---|---|---|---|
| Baseline (the pre-flight) | 820349b | 1881 | 1878 | 3 | 312.10 s | 3.2 to 3.9 | state.md |
| After I0 | a5dbf29 | 1883 | 1880 | 3 | 311.17 s | | orchestrator-report.md |
| After the G1 merge (Copy Me) | 96bf4c5 | 1933 | 1929, 1 timing failure that passed alone | 3 | 341.46 s | 3 to 4.5 | orchestrator-report.md |
| After the G2 merge (Flap) | 051bd7e | 1980 | 1977 | 3 | 395.25 s | 3 to 4.5 | orchestrator-report.md |
| After the G3 merge (Swat) | 4241bb0 | 2037 | 2034 | 3 | 422.30 s | 3 to 4.5 | orchestrator-report.md |
| After the G4 merge (Freeze) | 0cbd396 | 2086 | 2083 | 3 | 484.03 s | 3 to 4.5 | orchestrator-report.md |
| After the review's fixes | d81599e | 2092 | 2089 | 3 | 484.37 s | | orchestrator-report.md |
| Verify | d81599e (tree of 095c58d) | 2092 | 2089 | 3 | 476.51 s | 4.27 at the end | pytest-idle.txt |

- The four games cost about 165 to 172 s together; the plan expected about 125 s.
- The oracle's pool setup, where every game's 60 report plays are made: 89.63 s for seven games (33.91 s for
  three in it18). The pool's deadline is 120 s.
- Each game's own `test_good_beats_lazy_beats_nobody` (5 seeds, 3 bots) takes 7 to 10 s; each game's soak 3 to
  6 s a size, at two sizes.
- About 56 to 63 s are left under the limit, with Jump, Paint and Tug still to come: iteration 20's plan buys
  room first.
- The three skips are the baseline's: two `/proc` descriptor tests and the `unshare` test, all because this is
  macOS.

## The reviews

- `plan-review.md`: round 1 BLOCKED on B1 to B8, fixed in the plan; round 2 closed all eight, blocked on one new
  line (N1) and gave four notes, all taken; approved with that line.
- `code-review.md`: round 1 BLOCKED on rows 60 to 63 (Freeze's topple on 52 ticks of every out; Flap's hint on
  990 ticks of `idle_body` and its floor-crash wings on 37 ticks). Fixed test-first in 1acbe6e and d81599e with six
  new test items. Round 2 APPROVED: 0 lit ticks in every probe, the new tests fail on the old code, no assert
  removed or changed, the flash numbers unmoved.
- `orchestrator-report.md`, `G1-report.md` to `G4-report.md`, `plan-writer-report.md`: what was built, the lever
  values, the deviations, the minutes.

## Other checks

- `arcade doctor`: camera ok, mic ok, `pose ok mediapipe 1.0.0: landmarker ran in 17 ms` (the second run; the
  first, right after the evidence run, read `pose UNAVAILABLE pose landmarker did not finish within 5 s`).
- Owner questions Q104 to Q120 are in decisions.md, each defaulted.
