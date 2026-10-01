Decision: iteration 18 done. The suite has room again and Dodge is back on main: the oracle's bot plays are made by 4 worker processes before its reports (no seed, assert or band changed, nothing under `arcade/` changed for it), which takes the suite from 325.84 s to 270.35 s; with Dodge's return (708a42e, the four files of it15 unchanged) it reads 301.58 s on the quieter Mac and 312.30 s and 308.37 s beside another session, 1866 passed, 3 skipped, 1869 collected, under Q81's 420 s; Dodge's feel row, timeline, GIF and sheets are it15's, equal but for the stamp (plan review APPROVED in round 2 after one blocking finding; code review APPROVED in 1 round, no blocking finding); nobody has played Dodge on the camera yet, the first live play is the owner's

# Evidence, iteration 18 (the suite's time; Dodge's return)

Code head 708a42e (the reviewed range is 311e796..708a42e: 6 files, 1250 insertions, 9 deletions). Dodge's sheets
are stamped `708a42e` (the plain sheets `clean`) and were made from a clean detached checkout of it
(verify-script.py.txt). Nothing here was run on the Pi or on the card.

## The suite's time (the Mac, shared with another session; the limit is 420 s, Q81)

| Run | Head | Collected | Passed | Skipped | Time | Load (before to after) | File |
|---|---|---|---|---|---|---|---|
| Before (orient) | 86f0607 | 1809 | 1806 | 3 | 325.84 s | about 3 | orient-durations.txt |
| Before, Dodge reverted in (a scratch checkout) | 86f0607 + revert | 1862 | 1858 | 4 (the pose test too: no model in a scratch checkout) | 371.06 s | about 3 | orient-durations-dodge.txt |
| After the pool | 23c57d0 | 1815 | 1812 | 3 | 270.35 s | 2.08 to 1.43 | durations-after-pool.txt |
| After Dodge's return | 708a42e | 1869 | 1866 | 3 | 301.58 s | 1.95 to 1.59 | durations-after-dodge.txt |
| Verify, run 1 (beside the reviewer) | 708a42e | 1869 | 1866 | 3 | 312.30 s | 3.03 to 5.86 | pytest-1.txt |
| Verify, run 2 (the reviewer done) | 708a42e | 1869 | 1866 | 3 | 308.37 s | 2.31 to 4.30 | pytest-idle.txt |

- The pool saves about 55 s without Dodge and about 70 s with it (371.06 s against 301.58 s).
- The setup of the oracle's first report, where all the plays are made: 59.80 s before, 26.91 s after the pool,
  33.91 s with Dodge (165 plays and Pong's canonical run).
- Dodge now costs about 31 s (301.58 s against 270.35 s); it cost about 45 s before. A further pose game of
  Dodge's kind should cost about the same: about 110 s are left under the limit on these runs.
- The three skips are the baseline's: two `/proc` descriptor tests and the `unshare` test, all because this is
  macOS.

## Dodge at 708a42e against it15 (evidence/it15/dodge-83fe13a/)

| What | it18 | Against it15 |
|---|---|---|
| The feel row (`dodge/feel.json`, 17 metrics, 20 seeds) | every budget met, failures none: win_good 0.95, win_lazy 0.35, win_none 0.0, round_seconds 49.5, fidelity 0.9934, range 0.9606, response 1 tick and 100 px, lit 0.0335, dim 0.0034, score_visible 1.0, score_legible 1.0, flash_area_raw 0.0, square_flashes 0.0 | equal, key by key |
| The timeline (`dodge-128x64-timeline.txt`) | lobby attract, mirror, invite; ready at 4.57 s; the hit at 11.0 s; the card; the lobby | the same bytes |
| The GIF, 48 frames | the canonical round | every frame equal, pixel by pixel |
| The five sheets | led, plain, distance, the half-second sheet, raw against pushed | equal below the stamp's row |
| `arcade_shot` (`dodge/arcade.txt`) | 1650 frames, none black, held 0, flash_area raw 0.005 and pushed 0.005, concurrent_area 0.026 (limit 0.1), square_flashes 5 (budget 6) | equal |

The operator's reading of the sheets is the first item of the journal's entry for iteration 18.

## Files

| file | what it shows |
|---|---|
| dodge/feel.json, dodge/games.md | Dodge's feel row at 128x64, 20 seeds, with its budgets |
| dodge/dodge-128x64-led.png, -plain.png, -distance.png | the canonical round, 20 frames, at three looks |
| dodge/dodge-128x64-canonical.gif, -timeline.txt, -trace.jsonl | the same round as a GIF, its phases by second, its trace |
| dodge/it18-dodge.png, it18-dodge-distance.png | the round and the lobby after it, a frame each half second (55 s) |
| dodge/it18-dodge-raw-vs-pushed.png | the ticks around the hit, raw beside pushed |
| dodge/arcade.txt | the two commands, their output and exit codes, `git status` before and after |
| verify-script.py.txt | the script that made Dodge's evidence from the detached checkout |
| orient-durations.txt, orient-durations-dodge.txt | where the suite's time went before the plan |
| durations-after-pool.txt, durations-after-dodge.txt | the orchestrator's two suite runs with the 20 slowest items |
| pytest-1.txt, pytest-idle.txt | the operator's two suite runs at the code head |
| plan-review.md, plan-review-round2.md | the plan's adversarial review: BLOCKED on one finding, then APPROVED |
| orchestrator-report.md | the build: tasks, deviations, tests, commits, minutes |
| code-review.md | the code review: APPROVED, the probes of the pool and of its failure paths, the notes |

Note (2026-10-01, owner decision Q98): the PNG and GIF files named above are not in git; they are on the Mac in
this folder. The commit ids named here are the ones before the trim of the unpushed commits; the table of ids
before and after is ../sha-map-2026-10-01.md.
