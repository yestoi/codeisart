Decision: iteration 16 done. D5, the five IOCCC entries, is on main on stations 1 to 5 (plan review fixed six findings before any code; code review APPROVED in 1 round, no blocking finding; the Pi's three checks pass); all five play on the 128x64 sheets; one fix is carried, C54 (the short strip cuts thadgavin's attribution); the entries seen on the wall are the owner's (GATE C, wall-session.md)

# Evidence, iteration 16 (D5, the five entries)

Code head 9e3b8f0 (the fallback recordings' commit; the reviewed range is b4ff165..27a10bd). Every sheet is stamped
`9e3b8f0` clean and was made from a clean detached checkout of it (verify-script.py.txt): governed, `show.poc.toml`
(128x64, the ink view), the led look, one frame a second for 70 s. Nothing here was run on the card.

## The governor's numbers, the whole play (BUDGET 6 squares, SMALL_AREA 0.1; show-shot.txt)

| Entry | Station | Held ticks | Largest area | Most squares | Cast | What the sheet shows |
|---|---|---|---|---|---|---|
| sloane | 1 | 0 | 0.0223 | 3 | 0.73 MB | The donut over its checkered floor, a banner along the top. The floor and the hole read; the donut's body hardly stands out in the ink view (Q93) |
| imc | 2 | 11 (in the typed source and the build, none in the run) | 0.0575 | 3 | 0.01 MB | Six views of 6 s. View 2 is the clearest; view 3 is one lit block (Q92); views 5 and 6 are alike (Q86) |
| thadgavin | 3 | 400 (350 of them between 16 s and 42 s) | 0.0575 | 6 | 0.70 MB | A plasma, full field, from 11 s to 53 s; blocky held patches from 21 s to 31 s (Q87). The strip is cut: `Gavin Buttimore and T` (C54, Q91) |
| endoh1 | 4 | 14 (the first second of the melt) | 0.1196 | 2 | 1.54 MB | "Fluid" melts into a tank and sloshes until 46 s: the clearest of the five |
| endoh3 | 5 | 0 | 0.0068 | 2 | 0.02 MB | The clock: twelve marks, a hand that moves a step; sparse but clear |

The operator's reading of the sheets is the first item of the journal's entry for iteration 16.

## Files

| file | what it shows |
|---|---|
| it16-`<name>`-p1..p3.png | the play of each entry at the led look, 70 frames: attract, the typed source, the build, the run, attract again |
| it16-`<name>`-distance-p1..p3.png | the same frames at the distance look |
| show-shot.txt | the command of each sheet and its line a second: held, area, squares, the strip's text |
| pytest-idle.txt | the full suite at 9e3b8f0: 1794 passed, 3 skipped, 327.61 s; 1797 collected |
| verify-script.py.txt | the script that made the sheets from the detached checkout |
| pi-checks.md | the Pi 5's checks under the lock: (a) the Linux tests, 106 passed, twice; (b) the builds under gcc 14; (c) endoh3's loop in real time |
| pi-probe-early.md | the early probe on the Pi (the plasma's REP under `TERM=xterm`, the reason for `TERM=vt100`) |
| plan-review.md, plan-review-round2.md | the plan's adversarial review: BLOCKED on six, then APPROVED |
| orchestrator-report.md | the build: tasks, deviations, tests, commits, minutes |
| code-review.md | the code review: APPROVED, what "no blocking finding" covers, the notes |
| wall-session.md | the owner's sheet for the session at the wall (Q84): the runs, what to look for, the words back |

Note (2026-10-01, owner decision Q98): the PNG and GIF files named above are not in git; they are on the Mac in
this folder. The commit ids named here are the ones before the trim of the unpushed commits; the table of ids
before and after is ../sha-map-2026-10-01.md.
