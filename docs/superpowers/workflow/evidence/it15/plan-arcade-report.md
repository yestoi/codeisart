## Plan (path, line count)
/Users/trey/dev/codeisart/docs/superpowers/plans/2026-09-29-it15-arcade-pose-games.md: 299 lines, no line over 120
characters. Line 2 is the required BASE line. Not committed. Probes and their outputs are in
/private/tmp/claude-502/-Users-trey-dev-codeisart/d1e01db2-fed8-414f-9a38-325b95bc9c3a/scratchpad/it15-plan-arcade/.
The plan is the only file I changed. `docs/superpowers/workflow/state.md` shows as modified in `git status`. I did
not touch it; someone else changed it during my run.

## Tasks and lanes (task, model, where it runs, its files)
| Task | Model | Where | Files |
|---|---|---|---|
| I0 | orchestrator | main checkout, first | `tests/arcade/helpers.py`, `tests/arcade/test_oracle.py` |
| E1 (C47, C46) | opus | main checkout, serial | `arcade/sensed.py`, `arcade/sources/camera.py`, `arcade/input.py`, `tests/arcade/test_sensed.py`, `tests/arcade/test_camera.py`, `tests/arcade/test_input.py`, `tests/arcade/test_pong.py` (one test added) |
| E2 (C45, hand point) | opus | main checkout, serial, after E1 | `arcade/sources/pose_mediapipe.py`, `tests/arcade/test_pose_mediapipe.py` |
| G1 Quick Draw | sonnet | worktree, parallel | `arcade/games/quickdraw.py`, `quickdraw_bots.py`, `quickdraw_feel.toml`, `tests/arcade/test_quickdraw.py` |
| G2 Dodge | sonnet | worktree, parallel | `arcade/games/dodge.py`, `dodge_bots.py`, `dodge_feel.toml`, `tests/arcade/test_dodge.py` |
| I1 | orchestrator | main checkout | `.claude/skills/arcade-game-authoring/SKILL.md` (one line) |

Order: I0, E1, E2, then G1 and G2 in parallel. Merge G1, then G2, then I1. No file is listed under two tasks.
C47 and C46 are one task because both change `sensed.py` and `camera.py`. Nobody edits `arcade/games/__init__.py`,
`arcade/bots.py`, `feel_budgets.toml`, `config.py`, `arcade.toml` or `tests/conftest.py`. `quickdraw` and `dodge`
are already in `MENU_ORDER`.

## The fixes (C47, C46, C45: what is planned, what was measured)
- **C47.** Probe `probe_c47.py`: a still body with the spike's proportions, born without hips, with the hips
  arriving at 1 s. The tracker's scale goes 0.24, 0.335, 0.370, 0.383, 0.387 (the SCALE_TAU ramp spreads the
  jump over four captures). The Depth value jumps 0.777, and Pong's paddle travels 24.0 px, against the 14.4 px
  that counts. The plan:
  - `Body` gets `measured: bool = True`. The tracker passes False until a track has been seen with its nose and a hip.
  - On a track's first measured capture, the tracker takes the measured scale at once, so the jump is one capture.
  - `Depth` takes a new centre on that capture, once per `reset()`. Its output stays where it was, so the jump is
    neither travel nor `active`.
  - Actor and bot bodies default to True and take no new path, so every number in Pong's it09 row must come out
    equal. The implementer checks with `test_oracle.py`, `test_pong.py` and a printed `feel.report`.
- **C46.**
  - `Body` gets `torso_per_width: float = 0.0`, which the tracker learns from measured captures.
  - Without hips, `Body.torso` = that ratio (default 1.25) × the shoulder width. This follows a step, where a
    frozen torso would not. It matches the spike's measure: 0.26 at a width of 0.128.
  - The reach box and the raise line follow from it (Q74).
  - As a constraint: Quick Draw points with `Cursor` + `Glide`, never `Body.cursor`. Dodge reads `zone_x`
    through a `Glide`.
- **C45.**
  - `merge_duplicates` goes before the tracker. Two poses are one person only when the nose and both shoulders
    are confident in both and each pair is within 0.04 of the frame. The pose with the more confident hips is kept.
  - Why 0.04: the spike's duplicate noses were 0.01 to 0.02 apart. Two people shoulder to shoulder are about
    0.09 (3 m) to 0.13 (2 m) apart.
  - Tests: side by side at 2 m and at 3 m, a child in front of an adult, and a pose with a missing shoulder. None
    of them is merged. No test loads the model; E2 still runs in the main checkout.
- **Spike settings.** Only the hand point lands: each wrist becomes the mean of the wrist, pinky and index
  landmarks, keeping the wrist's confidence. These stay as they are: `camera_fps` 10, the arcade.toml camera
  settings, the lite model (Q73). The graces in seconds (Q44) need `arcade/runner.py`, which is frozen in this
  iteration, so they wait.

## The games chosen and why
| Game | Why | What it asks at 128x64 from 2 to 3 m |
|---|---|---|
| Quick Draw (G1) | Small in the spec. It needs C46 (a raised hand in the reach box without hips) and C45 (no phantom player 2 in a duel). The bots' `wrist_y` drives it with no change to `bots.py`. | Keep your hand low. On "DRAW!" (2x text), raise it. Your hand's height is a 12x3 bar near the wall's edge, and the draw is the bar crossing a line of ticks. First to 3 rounds. Solo plays a green CPU; a second body takes the CPU's seat. |
| Dodge (G2) | Body x (`zone_x`) is the tracker's steadiest signal. The bots' `Move.x` drives it directly. Two different controls make two different games. | Step left and right under falling 6x4 rocks, with your 6x8 block on the bottom band. The speed ramps from 20 to 48 px/s. A run ends on a hit or at 45 s. Every third rock aims at you, so a still body is hit. |
Not chosen:
- Copy Me: needs the column slack of `figure_rect`, a pose ladder, and is M effort.
- Flap: needs both wrists, but `Move` has one hand. Its impulse control would miss the fidelity and range bands.
- Swat: the body-relative reach box gives a bot no hand x.
- Freeze: a stillness game fights the rule that a still body scores nothing, and its threshold needs the real camera.
- Dodge's jump and duck: they need a body-height `Move` and a baseline. The plan ships side steps only (Q70).

## Existing asserts that change (or "none")
None. Both `Body` fields default to today's behaviour. The tracker's snap only touches a track born without hips
and later measured, and no existing test builds one (`test_tracker_scale_follows_a_step_within_three_captures`
is measured from its first capture). I did not take the variant that subtracts the jump in Pong's travel rule,
because it would change `test_pong.py`'s travel asserts.

## The suite's time (measured today, expected after)
Measured with each file alone and `--durations=15`:
| File | Time | Main cost |
|---|---|---|
| test_oracle.py | 62.1 s | the setup's 20-seed report, 58.8 s |
| test_pong.py | 33.3 s alone | `test_good_beats_lazy_beats_nobody` 14.3 s; it reuses the oracle's plays when the oracle runs first |
| test_feel.py | 17.0 s | not per game |
| test_all_games.py (Pong) | 12.2 s | the soak, 5.8 s + 5.4 s |
Probe `probe_cost.py`: a bot play costs 18.4 ms of CPU per simulated second.

| Share | Expected |
|---|---|
| base | about 235 s |
| I0 | 0 s |
| E1 | +3 s |
| E2 | +1 s |
| G1 Quick Draw | +42 s: oracle about 25 s (good plays about 24 s), soak 12 s, own tests at most 6 s |
| G2 Dodge | +47 s: oracle about 32 s (good about 49 s, lazy about 25 s), soak 12 s, own tests at most 6 s |
| after | about 330 s, right at the limit (range 320 to 340) |

How the games keep their share small:
- I0 moves the play memo into `helpers.py`, so plays are shared whichever file sorts first (`test_dodge` sorts
  before `test_oracle`).
- Rounds are short: Quick Draw's WAIT is 2 to 5 s (Q71) and first to 3 wins; a Dodge run is 45 s.
- Each game's tests use 5 seeds and read the shared plays.

If I1's suite goes over 330 s, Dodge is cut first. No single command exceeds 10 minutes; the longest file is
about 62 s today.

## Decisions taken
- Two games: Quick Draw and Dodge. Copy Me waits.
- One engine task for C47 and C46 (they share files), then E2. I0 comes first: the oracle judges every game but
  Pong through new parametrised tests, and Pong's three tests stay as they are.
- C47: `Body.measured`, the tracker snaps its scale on the first measure, and `Depth` takes a new centre with no
  jump (Q75).
- C46: a learned torso per shoulder width on `Body`.
- C45: nose and both shoulders within 0.04; the more confident hips are kept.
- From the spike, only the hand point. No camera or config change.
- Both games declare no budget override. Their `[fidelity]` is `cursor_y` against `hand_xy` (Quick Draw) and
  `zone_x` against `player_xy` (Dodge). Hints show after 2 s still, inside the 3 s rule.

## Questions for the owner (each with a default the loop takes at once; from Q70)
- Q70: Dodge ships with side steps only. Jump and duck wait. Default: yes.
- Q71: Quick Draw's WAIT is 2 to 5 s (the spec says 2 to 6). Default: yes.
- Q72: Quick Draw's solo score and best are rounds won; the fastest draw shows only in the round's result.
  `Scores` has no lower-is-better best. Default: yes.
- Q73: The move from the lite to the full model, `camera_fps` 30 and the graces in seconds go together, in a
  later iteration. Default: not in it15.
- Q74: The learned torso also moves the raise line without hips, by about 0.03 of the frame on the owner.
  Default: yes, one torso for all.
- Q75: At the first measure, `Depth` keeps the paddle where it is rather than recentring to 0.5. Default: keep it.

## What was cut or moved
- Q44 (graces in seconds) and any `camera_fps` change are moved: they need `arcade/runner.py`, which is frozen in
  this iteration. `arcade.toml` is unchanged.
- The switch to the full pose model is moved (Q73).
- Moved to the next run: Copy Me, Flap, Swat, Freeze, and Dodge's jump and duck.
- The spike's "width with the frame's aspect" is not planned. The learned ratio absorbs it for a body facing the
  camera.
- The plan's cut order, if time runs out or the suite goes over 330 s: Dodge, then Quick Draw, then the hand
  point, then C45. E1 is cut last.
- No command was refused. The first background timing run failed at once because `timeout` is not installed on
  this Mac. I ran it again without `timeout`, and the longest file took 62 s.

## Minutes (start and end from `date`)
Start 08:22:16 CDT, end 08:33 CDT (2026-09-29): about 11 minutes.
