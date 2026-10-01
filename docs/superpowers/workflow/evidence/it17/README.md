Decision: iteration 17 done. C54 is closed: on the 128x64 wall the short strip shows thadgavin's attribution in three pieces before `Not A.I.` (`Gavin Buttimore and`, `Thaddaeus Frogley,`, `2000`), three seconds each, whole words and the year, where it16 showed `Gavin Buttimore and T`; a fitting attribution is two texts as before (plan review APPROVED in 1 round; code review APPROVED in 1 round, no blocking finding; the Pi's check passes); whether the bare `2000` reads as the year is the owner's eye at the wall

# Evidence, iteration 17 (D5's slack: C54, the strip's wrap; the banner check; the README's two lines)

Code head 86f0607 (the reviewed range is f8bcc14..86f0607). Every sheet is stamped `86f0607` clean and was made
from a clean detached checkout of it (verify-script.py.txt): governed, `show.poc.toml` (128x64, the ink view), the
led look, one frame a second for 70 s. Nothing here was run on the card.

## The governor's numbers, the whole play (BUDGET 6 squares, SMALL_AREA 0.1; show-shot.txt)

| Entry | Held ticks | Largest area | Most squares | it16 (9e3b8f0) | What the sheet shows |
|---|---|---|---|---|---|
| thadgavin | 398 | 0.0499 | 6 | 400, 0.0575, 6 | The strip cycles `Gavin Buttimore and`, `Thaddaeus Frogley,`, `2000`, `Not A.I.`, three frames each, through the plasma (11.3 s to 53.3 s); the play ends in the fifth cycle after `Thaddaeus Frogley,`. The plasma is it16's (Q87) |
| sloane | 0 | 0.0345 | 3 | 0, 0.0223, 3 | `Andy Sloane, 2006` and `Not A.I.` in turn, as before; the picture is it16's (Q93). The largest area is at 5.1 s, in the typed source, as in it16 (the play is in real time, the second's sample differs) |

The strip's pieces change nothing the governor counts: both plays are within a run's variation of it16's, the areas
under SMALL_AREA and the squares at or under the budget. The operator's reading of the sheets is the first item of
the journal's entry for iteration 17.

## Files

| file | what it shows |
|---|---|
| it17-thadgavin-p1..p3.png, it17-sloane-p1..p3.png | the play at the led look, 70 frames: attract, the typed source, the build, the run, attract again |
| it17-`<name>`-distance-p1..p3.png | the same frames at the distance look |
| show-shot.txt | the command of each sheet and its line a second: held, area, squares, the strip's text |
| pytest-idle.txt | the full suite at 86f0607: 1806 passed, 3 skipped, 328.26 s; 1809 collected |
| verify-script.py.txt | the script that made the sheets from the detached checkout |
| pi-checks.md | the Pi 5's check under the lock: the show's Linux tests with it17's twelve, 147 passed, 0 skipped, 34.61 s |
| plan-review.md | the plan's adversarial review: APPROVED, no blocking finding |
| orchestrator-report.md | the build: tasks, deviations, tests, commits, minutes |
| code-review.md | the code review: APPROVED, the two changed asserts, the banner probe, the notes |
