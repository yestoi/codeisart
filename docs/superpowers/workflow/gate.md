# Gate: the run of Q80 is done, after iteration 18 (2026-10-01)

Question: the run that Q80 started (iterations 16 to 19) has nothing left that Q81 allows: D5 is built (it16),
its slack is done (it17), the suite has room and Dodge is back (it18), and no new game may be started. The loop
has stopped before iteration 19. Does the operator start a new run, and with what?

Default: none is taken; the loop waits for the owner (Loop rule 8: the iteration cap, and Q81's "with none of
that left the loop gates"). The operator's lean: first the owner's wall session for the five entries (about 20
minutes, the sheet below), then the live smokes on the camera; after them a run on M7a's next games (Copy Me,
Flap, Swat, Freeze) and whatever the wall session asks of the entries.
Deadline: none (nothing is in flight; no agent runs)

## Where the work stands
- Code head 708a42e; main is at the gate's commit, 55 commits ahead of origin/main (d7d0051). The loop does not
  push. The suite: 1869 collected, 1866 passed, 3 skipped (macOS), 301.58 s on the quieter Mac and 308 to 312 s
  beside promptviz's session, under Q81's 420 s.
- Iteration 16 (9e3b8f0; evidence/it16/): D5, the five IOCCC entries on stations 1 to 5 (sloane, imc, thadgavin,
  endoh1, endoh3), each built and played through the pipeline and the governor at 128x64, with fallback
  recordings. The Pi 5 builds and runs all five under the lock (gcc 14, `unshare -rn`).
- Iteration 17 (86f0607; evidence/it17/): C54 closed. The 128x64 strip shows a long attribution in whole pieces
  (`Gavin Buttimore and`, `Thaddaeus Frogley,`, `2000`, `Not A.I.`), where it16 cut it at `Gavin Buttimore and T`.
- Iteration 18 (708a42e; evidence/it18/): the oracle's bot plays are made by 4 worker processes (the suite
  325.84 s to 270.35 s, no seed, assert or band changed), and Dodge is back on main, equal to it15's build and
  evidence. Nobody has played Dodge on the camera.
- Nothing was sent to the card, nothing under `deploy/` was touched, nothing was pushed. The Pi was used only
  under the lock (Q83); `pi-lock.md` still stands and only the owner deletes it.
- Carried: only C52's arcade half, which waits on Q67.

## What the owner does first (before anything at the wall)
1. Push main: `git -C /Users/trey/dev/codeisart push` (55 commits).
2. The wall session for D5: `docs/superpowers/workflow/evidence/it16/wall-session.md`. It starts with "Before
   the session" (the pull on the Pi under the lock, promptviz off the Pi or the lock kept), then run 0 dry,
   hello on the card, the five entries, attract. The show daemon has never put a picture on this wall.

## What needs the owner's ruling
| Item | What happens today | Operator's lean |
|---|---|---|
| The next run | The loop is stopped | M7a's next games after the live smokes; or the entries' changes from the wall session first |
| The suite's limit after this run | Q81's 420 s was given for this run; before it the limit was 330 s (Q77). The suite is 302 to 312 s with Dodge | Keep 420 s: three of the four open pose games fit at about 30 s each, the fourth is tight |
| Q90 | At the wall the show reaches the card as user trey with two capabilities (`systemd-run`), not as root under `sudo`; nobody has run this form yet | This form: the five programs must not run as root |
| Q87, the plasma (thadgavin) | Built at the archive's speed; the governor holds about 400 ticks of the play, blocky patches for moments | The owner's eye at the wall: still a plasma, the light comfortable? |
| Q92, imc's third view | One lit block with nothing to read (the program's own output at this size) | Kept; the other choice drops the view |
| Q86, imc's views 5 and 6 | Nearly alike | Kept |
| Q93, the donut (sloane) | In the ink view the donut's body hardly stands out from the floor under it | Kept until seen on the panels |
| Q96, thadgavin's year | `2000` stands alone on the strip for three seconds | Kept; the other choice fills the pieces from the end (`Frogley, 2000`) |
| endoh1's field | 26 lines in a 23-row terminal: the top rows are never seen, a tear may show | The owner's eye at the wall |
| Q97 | The suite starts 4 worker processes for the oracle's bot plays | Kept (3 workers are about 8 s slower) |
| Q70, Dodge's form | Side steps under falling blocks, not the spec's jump and duck | Side steps; the first live play decides |
| Q66, a SAFETY GATE | After a failed push the wall sends nothing for 1 s; if the card blanks without packets the hold itself breaks the flash budget | Before the show runs in front of people: on the panels, stop the sender for 3 s; the picture must stay. Result into evidence/hardware.md |

## Decisions taken by default in this run, for the owner to confirm or change (decisions.md)
| Q | Default taken |
|---|---|
| Q85 | endoh3 builds the plain clock `prog.c`, not the archive's Unicode variant |
| Q86, Q92 | imc's tour keeps all six views |
| Q87 | The plasma runs at the archive's speed (`-DZ=30`) under the governor |
| Q88 | No fallback recording over 5 MB is committed |
| Q90 | The show reaches the card as a plain user with two capabilities |
| Q91, Q96 | The short strip shows a long attribution in pieces; the year may stand alone |
| Q93 | The donut stays in the ink view |
| Q94, Q95 | The banner check holds the pipeline's four failure texts itself; the README's strip line was corrected |
| Q97 | 4 worker processes for the oracle's plays |

Earlier defaults still unconfirmed: Q22 to Q31, Q34 to Q41, Q43 to Q48, Q51, Q52, Q59 to Q78 (the list with
each default is in the last gate's record: `git show ab5276b:docs/superpowers/workflow/gate.md`).

## Owner items (roadmap.md, "Owner items")
- The wall session for D5 (above), with the Pi's own fallback recordings once the five are kept.
- The live smokes on the camera: Pong by the body (the second), the first play of Quick Draw (Q76's flash), the
  first play of Dodge. `.venv/bin/python -m arcade run`; fill `live-smoke.md`.
- Q66's check on the panels (the safety gate above).
- GATE C's rest: the size tier, the courtesy mail to the IOCCC judges.
- `spike/hand-read` (ed7c80c, the worktree /Users/trey/dev/codeisart-spike) is unmerged: merge or drop.
  `ledvision-card1` stays off main.
- Ten merged implementer worktrees and branches of it16 to it18 under `.claude/worktrees/` can be cleared; the
  loop's guard does not let it delete a branch by force.
- `pi-lock.md`: delete it when the Pi is no longer shared.

Evidence: docs/superpowers/workflow/evidence/it16/ to it18/ (each README's first line is the decision),
journal.md (iterations 16 to 18).
