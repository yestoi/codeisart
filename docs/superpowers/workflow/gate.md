# Gate: the iteration cap, after iteration 15 (2026-09-29)

Question: the run that Q49 started (iterations 10 to 15, `iterations-per-run: 6`) is done and the loop has
stopped. Does the operator start a new run, and with what?

Default: none is taken; the loop waits for the owner (Loop rule 8: the iteration cap). The operator's lean: a new
run on the arcade, first the suite's time with Dodge's return, then M7a's next games (Copy Me, Flap, Swat,
Freeze); the show waits at GATE C for the owner's entries and hardware.
Deadline: none (nothing is in flight)

## Where the work stands
- Code head 77c11d4; 1313 tests collected, 1312 pass, 1 skipped (the unshare test on the Mac), about 280 to 300 s.
  Local main is ahead of origin/main (56b97dd); the loop does not push.
- The show daemon: D0 to D4 are done (iterations 10 to 13). `python -m show` runs in the SDL preview; every
  frame passes the flash governor. Iteration 14 closed the governor's gaps after a failed push (C50, C51, C52's
  show half); iteration 15 closed the last one, the stop after a failed push (C53). GATE C is the owner's: the
  five entries, the Pi 4, the Linux box, Falcon Player.
- The arcade: Pong by the body (iteration 9); in iteration 15 the tracker's faults from the hand-read spike
  (C45 duplicate poses, C46 the torso without hips, C47 hips that arrive late) and Quick Draw, the first of
  M7a's six pose games. Dodge is built and reviewed but off main (below).
- Carried: only C52's arcade half, which waits on Q67.

## What needs the owner's ruling
| Item | What happens today | Operator's lean |
|---|---|---|
| Q66, a SAFETY GATE | After a failed push the wall sends nothing for 1 s. If the card blanks without packets, the hold itself breaks the flash budget | Before the show runs in front of people: on the real panels, after the last "Save to Receivers", stop the sender for 3 s; the picture must stay. Result into evidence/hardware.md |
| Q76 | On DRAW Quick Draw flashes the whole wall white for 0.17 s (pushed at half light; at most one in 4.5 s; inside the flash rules). The arcade's first full-field flash | Keep it until the owner has seen it on the panels; the other choice is the word turning white with no flash |
| Q77, Dodge | Dodge is off main: the suite with it reads 321 to 336 s against the loop's limit of 330 s. It is whole on c49d902 and returns by `git revert 16dbb91` | First a plan that makes room in the suite (the oracle's 20-seed reports cost 26 s a game); or the owner raises the limit |
| Q70 | The Dodge that was built is side steps under falling rocks, NOT the spec's jump and duck | Side steps: the body's x is the tracker's steadiest signal |
| Q78 | In Quick Draw a match in which more than one body sat in player 1's seat banks no best. A player who steps out past the grace and comes back (a new tracker id) banks none either | As built; the other choices are in decisions.md |
| The hand point | Cut from iteration 15: the spike's hand point (the mean of wrist, index and pinky) changes two existing asserts in `tests/arcade/test_pose_mediapipe.py` (wrist x 0.15 becomes 0.17; one fixture) | The owner's word, or a plan that names both asserts. Q73's default named the hand point as landing; it did not |
| Q67 | The arcade's runner does not count its governor's first frame against black; one assert (300 governor calls) would read 301 | Yes, in a safety slice; today's first frames are the dark lobby |
| Q23 | A duel's end card shows player 1's points. **Reads wrong**: a winner as player 2 sees "PONG 0" | Both scores, in the players' colours |
| Q68 | After a failed push a stop of the show takes up to 2 s to darken the wall. `deploy/README.md`'s "Stop" text still says two black frames and exit | The text is the owner's to change (the loop touches nothing under `deploy/`) |
| Q54 | `bright-on-field` is the default strip look; the three looks are drawn in evidence/it12 | The pick stays the owner's, on the panels |
| PR 1's README | The public repository's README for the LEDVision kit names a LAN address and the VM's MAC addresses | The owner decides whether they stay |
| The commit trailer | The loop's commits end with the Fable 5.1 line; three orchestrator commits of iteration 14 name Opus 5.5 | Left as they are |
| The push of 07:30 and the pull of 07:35 (iteration 14) | Someone pushed main and pulled PR 1's merge into the main checkout in the middle of a build; read as the owner's | Tell the operator if it was not |

## Decisions taken by default, for the owner to confirm or change (decisions.md)
| Q | Default taken |
|---|---|
| Q22 | The idle lobby shows the featured game's title, dim |
| Q24, Q25 | A hand raised during the end card does nothing; a hand already up must be lowered and raised again |
| Q26, Q27, Q28, Q31, Q38 | The feel budgets' numbers, the bots' win bands, the dim rule, the score's visibility, `response_px` at least 12 |
| Q29, Q30 | The evidence GIF's form; how the stripe rule is read |
| Q34, Q36, Q37, Q39 | Pong's sizes at 128x64; a good round need not reach 5 points; the lobby on 64 rows; the `index` pattern's seams |
| Q35, Q41 | A still player banks nothing; "BEST!" only for a new best above 0 (both built, C42 and C43) |
| Q40, Q46 | Pong's pace: the fast ball of iteration 8 was set aside for a body's pace in iteration 9 |
| Q43, Q45, Q47 | Pong by the body: a step towards the camera is up; the two hint lines; about 0.5 m in and 0.7 m back cover the wall |
| Q44, Q73 | The camera stays at 10 captures a second by default (`arcade.mac.toml` has 30 for a trial); the full model and 30 a second wait for the graces counted in seconds |
| Q48 | The body's size is held through a hip dropout (built in iteration 9) |
| Q51, Q52 | The Reduced tier's rows (16, the strip on row 16); the strip's text carries the year |
| Q59 | The governor's cost on the Pi 4 is measured there; a slower loop is stricter, never laxer |
| Q60, Q61 | On the 128x64 proof of concept the governor may hold fast typing; the attract strip alternates |
| Q62 | A press on a portrait with no entry is acknowledged and queues nothing |
| Q63, Q64 | The unit keeps `network-online.target`; no full `white` pattern without the panels' current figures |
| Q65, Q66 | After a failed push the wall holds, quiet (Q66 replaces Q65's default) |
| Q69 | The close keeps the counted frame before black (2 s at most, not 1) |
| Q71, Q72 | Quick Draw's WAIT is 2 to 5 s; its solo score is rounds won, a duel records nothing |
| Q74, Q75 | One learned torso for the reach box, the cursor and the raise line; `Depth` keeps the paddle where it is when a body is first measured |

## Owner items (roadmap.md, "Owner items")
- The second Pong live smoke (Pong by the body): `.venv/bin/python -m arcade run`; fill live-smoke.md. Each "n"
  or low score becomes a Carried fix.
- The first play of Quick Draw: the flash (Q76), whether `DRAW!` reads in the 0.67 s after it, whether the CPU's
  pace (it draws 0.25 to 0.80 s after the signal) can be beaten through the camera's lag.
- Q66's check on the real panels (the safety gate above).
- The 2 x 2 wiring check (`tools/wall_pattern.py index` at 128x64) and the hardware bring-up; results into
  evidence/hardware.md.
- The overnight soak of the show; its command is in `deploy/README.md`.
- GATE C: the five entries, the size tier, the Pi 4, Falcon Player.
- Whether real captures lose the hips and keep a hanging wrist (it loses Quick Draw 0-3 in a made input) needs
  the owner's recordings; the loop does not open them.
- Forty-seven merged agent worktrees under `.claude/worktrees/` can be cleared; the loop's guard does not let it
  delete a branch by force.

Evidence: docs/superpowers/workflow/evidence/it10/ to it15/, journal.md (iterations 10 to 15).
