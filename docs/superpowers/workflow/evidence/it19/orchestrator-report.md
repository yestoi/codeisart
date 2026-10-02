# it19 orchestrator report: Copy Me, Flap, Swat, Freeze (M7a)

Plan: `docs/superpowers/plans/2026-10-01-it19-four-pose-games.md`. Main was at bb9fd70 with a clean tree at the start.
BASE (after I0) is a5dbf29. The task reports are `G1-report.md` to `G4-report.md` in this folder.

## Completed

- **I0** (serial lane, main checkout, test-first). `arcade/bots.py`: `Move` gains `pose: str | None = None` as its last
  field, and `hand` takes `"both"`. In `_sensed`, a pose is held on the tick through `Person.pose`; `"both"` moves both
  wrists to `wrist_y` with one noise draw. An unknown pose raises `ValueError`.
  - New tests in `tests/arcade/test_bots.py`: `test_move_both_hands_moves_both_wrists` and
    `test_move_pose_holds_the_named_pose`. Both failed first (`hand must be 'left' or 'right'`, `unexpected keyword
    argument 'pose'`).
  - No existing test changed. The `probe` helper gained a `game=Probe` keyword so the new tests can reuse it.
  - Committed as a5dbf29.
- **G1 to G4**. Four implementers were spawned in one message, each with `isolation: "worktree"`: G1 on opus, G2 to G4
  on sonnet. Each checked BASE first. Each branch touches only its plan files plus its report.
- **Merges**. The four branches were merged into main with `--no-ff` in plan order (G1, G2, G3, G4), with the full
  suite after each. No merge was reverted, no task was sent back and nothing was cut.
- **I1**. The suite was run with `--durations=25`: it passes with 3 skips in 484.03 s, under the 540 s cap. The guide
  `.claude/skills/arcade-game-authoring/SKILL.md` gained three additions:
  - section 4: `Move(hand="both")` and `Move(pose=...)`;
  - section 5: a gesture's gauge for fidelity and range, with Flap's `wing_xy` as the worked example;
  - section 6: a figure's column backlash, `COLUMN_SLACK = 1` in the game's own file.
- The worktrees and branches are left in place.
- No review agents were run, as instructed. Nothing was pushed or deployed, and nothing was sent to the Pi or the card.

### Each game's final win rates and lever values (20 report seeds, 128x64)

| Game | win_good | win_lazy | win_none | round_seconds | Levers and bot numbers moved from the plan |
|---|---|---|---|---|---|
| G1 Copy Me | 1.0 | 0.4 | 0.0 | 24.0 | none: every constant and bot number is the plan's |
| G2 Flap | 1.0 | 0.6 | 0.0 | 49.0 | lazy `reaction_ticks` 9 to 10 (9 gave 0.75, over the band) |
| G3 Swat | 0.95 | 0.35 | 0.0 | 66.2 | `GOAL` 25 to 30; `SPAWN_EVERY` (1.1, 0.6) to (1.4, 0.8); `BOMB_SHARE` 0.15 to 0.2; the bots below |
| G4 Freeze | 1.0 | 0.4 | 0.0 | 52.9 | none (`MOVE_TRAVEL` stays 0.25) |

`phases_reached` is 1.0 for all four. Every feel budget is met, and no game has a budget override.

- **G1 Copy Me.**
  - Constants as the plan: `ROUNDS` 3, `READY_SECONDS` 1.5, `SHOW_SECONDS` 1.5, `GROW_SECONDS` 3.0, `GROW_FROM` 0.3,
    `SCORE_WINDOW` 1.0, `RESULT_SECONDS` 2.0, `FREEZE_SECONDS` 1.5, `OVER_SECONDS` 3.0.
  - Judging: `LIMB_TOLERANCE_DEG` 30, `JUDGE_MIN_DEG` 60, `ACTIVE_DEG` 30, `MATCH_SHARE` 0.75, `FRESH_SHARE` 0.5,
    `WIN_MATCHES` 2.
  - Bots: good 6 ticks, noise 0.01; lazy 14 ticks, noise 0.03. The lazy bot copies round 1, stands in round 2, and in
    round 3 copies only `disco`.
  - Feel: fidelity 0.9996, range 0.701, flash_area_raw 0.011, square_flashes 4 of 6, score_visible 0.978.
- **G2 Flap.**
  - All game constants as the plan: `GRAVITY` 24, `FLAP_VY` -22, `GAP_H` (34, 30), `GAP_STEP` 6, `PIPE_EVERY` 3,
    `RUN_SECONDS` 45.
  - Bots: good 5 ticks, noise 0.02; lazy 10 ticks, noise 0.05.
  - Lazy's rate falls off a cliff with its reaction ticks: 9 gives 0.75, 10 gives 0.60, 11 gives 0.55, 12 gives 0.05.
  - Feel: fidelity 0.990, range 0.825, flash_area_raw 0.0, square_flashes 0.
- **G3 Swat.**
  - With the plan's numbers both bots won every seed, because a bot cuts about 55 of 56 fruit.
  - Bots: good 5 ticks, noise 0.02, swipes every 3 ticks, 0.15 either side of the target, avoids a bomb within 8 px,
    and leads the fruit's drift by 6 ticks. Lazy 12 ticks, noise 0.05, swipes every 8 ticks, 0.07 either side, no
    lead, ignores bombs.
  - Feel: fidelity 0.954, range 0.873, flash_area_raw 0.003, square_flashes 2.
- **G4 Freeze.**
  - Constants as the plan: `GREEN_SECONDS` (3, 6), `RED_SECONDS` (2.5, 4), `LAZY_GREEN` 4.5, `GRACE` 0.5, `REDS` 6,
    `MOVE_TRAVEL` 0.25.
  - Bots: good 6 ticks, noise 0.005; lazy 10 ticks, noise 0.01.
  - Feel: fidelity 0.99987, range 0.921, flash_area_raw 0.0186, square_flashes 5 of 6, the closest to its budget of
    the four.

## Deviations

### Mine

1. **The post-G4 run is also I1's run.** The full-suite run after the G4 merge was run with `--durations=25` and is
   I1's suite run too. I1's only change is the guide, and no test reads it (checked with `grep -rl SKILL.md tests`).
2. **The full suite in three parts.** Implementers ran it as three commands: `tests --ignore=tests/arcade`, then
   `tests/arcade` without the oracle and the soak, then those two. Four suites running at once on an 8-core, 8 GB Mac
   could pass the 10-minute command limit. The sum is the same suite.
3. **A timing failure on the G1 merge.** `tests/test_show_shot.py::test_strobe_session_is_held`, one of the three
   named load-timing tests, failed. It passed alone (1 passed, 3.65 s), so the merge was not reverted.
4. **Every game's own test file is over the plan's 6 s.** G1 13.1 s, G2 15.8 s, G3 about 10 to 12 s plus its 5-seed
   bot tests, G4 about 23 s. Most of it is the template's `test_good_beats_lazy_beats_nobody`: 5 seeds of 3 bots,
   which Dodge also pays 7 s for. The shares measured merge to merge on the shared Mac are G1 +30 s, G2 +54 s,
   G3 +27 s and G4 +62 s, against the planned 25, 30, 38 and 32. The whole suite is 484 s against the plan's
   expected 440 s, inside Q102's 540 s, so nothing was cut.
5. **The extra skip in the worktrees.** Every worktree showed 4 skips: `tests/arcade/test_pose_mediapipe.py:303`
   skips because `/models/` is not in git. The main checkout shows the base's 3 skips after every merge.
6. **`state.md` left alone.** `docs/superpowers/workflow/state.md` was modified in the main checkout by someone else
   during the run. It is the operator's file: I neither edited nor committed it, so the tree is clean except for that
   file.

### The implementers' (details in their reports)

- **G1 Copy Me.**
  - The canonical walks one way, 0.15 to 0.85 at 0.1 zone/s, instead of 0.2 to 0.8 to 0.5. The plan's walk measured
    range 0.59, and a faster walk breaks the flash area rule.
  - Poses cycle only in play's last `SCORE_WINDOW`, plus 0.25 s either side.
  - The torso axis runs from both hips' centre to both shoulders' centre. `Body.hip_mid` lets one hip stand in, which
    tilted the axis up to about 20 degrees under noise.
  - `active` is sampled only on ticks when every judged limb is seen.
  - The target's name shows in `show` only.
  - "MATCH!" shows when either seat matches.
  - A refused flash becomes a burst.
  - A score is recorded only when the total is over 0.
  - `LADDER` lives in `copyme.py`.
  - The outline test measures arm span, not height.
- **G2 Flap.**
  - The window test is read as the two wrists' drops staggered by 0.3 s (flaps) or 0.5 s (does not).
  - `bird_vy` equals `FLAP_VY` on the flap's tick.
  - Restart in `over` waits for the crash fade.
  - The best run is recorded at the last run's end or in `done()`; a session left after a non-final crash banks
    nothing.
  - The canonical is 60 s.
- **G3 Swat.**
  - The canonical sweep is 1.5 s, not slow: a 4 s sweep gave `response_px` 5.5, under the budget of 12.
  - A bomb is drawn as a fat plus.
  - `test_debug_state_is_clean` skips the lit-pixel check for a blade under the score's black box.
  - The flash, lobby and idle tests run 20 to 25 s windows.
  - `swipe` and `spawn` are public methods.
- **G4 Freeze.**
  - A red counts 0.3 s after it ends (`COUNT_LAG`).
  - The canonical has no side steps: they and faster waves pushed the governor to hold frames.
  - A duo survivor counts the red it stood through.
  - `idle_body` ends "inactive" at about 35 s, so its test asserts score 0 and best None, not phase over.
  - Over words are OUT, SAFE!, P1 WIN, P2 WIN and DRAW.

### Owner questions raised by the implementers (none blocking)

- **G1**
  1. Player 2's blue (0, 160, 255) is close to the outline's cyan (0, 200, 255).
  2. A real player crossing the mat at 0.2 zone/s or faster makes the governor hold frames: safe, but the figure
     stutters.
  3. The time overrun.
  4. The text rows 41 to 58 cover the figure's lower legs; no pose judges a leg.
- **G3**: is `GOAL` 30 right for human players, whom the oracle does not measure?
- **G2**: the lazy bot's rate falls off a cliff with its reaction ticks; a later physics change may need it retuned.

## Test status (command + counts)

Command, from `/Users/trey/dev/codeisart`:
`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs`

| When | Collected | Passed | Skipped | Failed | Time |
|---|---|---|---|---|---|
| Baseline at 820349b (given) | 1881 | 1878 | 3 | 0 | 312.10 s |
| After I0 (a5dbf29) | 1883 | 1880 | 3 | 0 | 311.17 s |
| After the G1 merge (96bf4c5) | 1933 | 1929 | 3 | 1, timing; passed alone | 341.46 s |
| After the G2 merge (051bd7e) | 1980 | 1977 | 3 | 0 | 395.25 s |
| After the G3 merge (4241bb0) | 2037 | 2034 | 3 | 0 | 422.30 s |
| After the G4 merge (0cbd396), with `--durations=25` (also I1's run) | 2086 | 2083 | 3 | 0 | 484.03 s |

Collected never dropped and the skips stayed at 3: the base's three, all Linux-only. The load average was 3 to 4.5
during the merge runs.

The last `--durations=25` table:

```
91.61s setup    tests/arcade/test_oracle.py::test_feel_pong_meets_its_budgets
9.89s call     tests/arcade/test_freeze.py::test_good_beats_lazy_beats_nobody
9.52s call     tests/arcade/test_flap.py::test_good_beats_lazy_beats_nobody
7.18s call     tests/arcade/test_dodge.py::test_good_beats_lazy_beats_nobody
7.03s call     tests/arcade/test_copyme.py::test_good_beats_lazy_beats_nobody
6.09s call     tests/test_show_shot_governed.py::test_governed_entry_session_runs_the_entry_through_the_governor
5.93s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[pong-128x64]
5.75s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[freeze-128x64]
5.35s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[pong-96x48]
5.18s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[copyme-128x64]
4.56s call     tests/test_show_shot.py::test_entry_mode_plays_the_sample_entry_through_the_pipeline
4.37s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[quickdraw-128x64]
4.35s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[copyme-96x48]
4.06s call     tests/test_entries.py::test_sample_entry_band_leaves_no_trail
3.84s call     tests/test_curated_entries.py::test_entry_plays_through[sloane]
3.82s call     tests/arcade/test_oracle.py::test_evidence_package_for_pong
3.81s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[flap-128x64]
3.80s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[swat-128x64]
3.65s call     tests/arcade/test_first_playable.py::test_first_playable_keeps_the_flash_rule
3.65s call     tests/arcade/test_oracle.py::test_feel_meets_its_budgets[copyme]
3.60s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[dodge-128x64]
3.58s call     tests/test_show_shot.py::test_strobe_session_is_held
3.55s call     tests/test_curated_entries.py::test_entry_plays_through[imc]
3.52s call     tests/test_curated_entries.py::test_entry_plays_through[endoh1]
3.50s call     tests/test_entries.py::test_sample_entry_runs_with_large_motion
2083 passed, 3 skipped in 484.03s (0:08:04)
```

The oracle's pool setup, 91.61 s, plays every registered game's 60 report plays: seven games now, the three before
it19 and the four of this iteration.

## Commits (sha + subject)

| sha | subject |
|---|---|
| a5dbf29 | feat(arcade): it19 I0, a bot's Move strikes a pose and moves both hands |
| 83a0e83 | feat(arcade): it19 G1, Copy Me (copyme): a target pose grows over the figure; judged limbs turn green |
| 5ceece1 | docs(it19): G1 report, Copy Me: tests, times, win rates, feel metrics, deviations, owner questions |
| a5758c3 | feat(arcade): it19 G2, Flap: both wrists sweep down to flap, wing gauge, bots tuned |
| d180829 | feat(arcade): it19 G3, Swat (fruit, blade, bombs, combos; two share one score) |
| 5f8aa0a | feat(arcade): it19 G4, Freeze (red light, green light on the pose camera), bots, feel file, tests, report |
| 96bf4c5 | merge: it19 G1, Copy Me (copyme) |
| 051bd7e | merge: it19 G2, Flap (flap) |
| 4241bb0 | merge: it19 G3, Swat (swat) |
| 0cbd396 | merge: it19 G4, Freeze (freeze) |
| 23756c7 | docs(guide): it19 I1, Move(hand="both") and Move(pose=...), a gesture's gauge, the figure's column backlash |
| (this file) | docs(it19): the orchestrator's report |

The branches are kept, as are their worktrees under `.claude/worktrees/`:

| Task | Branch | Worktree |
|---|---|---|
| G1 | `worktree-agent-aeb6d66f99fe9c79f` | `agent-aeb6d66f99fe9c79f` |
| G2 | `worktree-agent-a8e141a00b4957966` | `agent-a8e141a00b4957966` |
| G3 | `worktree-agent-a43fac7edc5096b91` | `agent-a43fac7edc5096b91` |
| G4 | `worktree-agent-ac6231002623807cf` | `agent-ac6231002623807cf` |

## Minutes (serial lane, parallel tasks, integration)

- **Serial lane (I0):** about 9 min, from about 00:25 to the commit at 00:33. That includes the 5 min 11 s full
  suite.
- **Parallel tasks:** about 72 min of wall time, from the spawn at about 00:36 to 01:48, bound by G1.
  - G1: 72.4 min (opus).
  - G2: 21.1 min.
  - G3: 30.5 min.
  - G4: 30.8 min.
- **Integration:** about 35 min, from 01:48 to about 02:23. That covers four merges, each with its full suite (5.7,
  6.6, 7.1 and 8.1 min), the strobe rerun, the guide additions and this report.

## Fix round (the code review's two findings)

The code review (`code-review.md`, "Blocking findings") found two breaks of the Global Constraint "Rows 60 to 63 stay
free (the runner's marker)". Both were fixed test-first in the main checkout, from f2d24ba, one commit per game. Only
the four named files changed. No existing assert was removed or weakened, and no lever moved.

### Freeze

- **Fix** (`arcade/games/freeze.py`, `_draw_fall`): the rotated skeleton is lifted by as much as its lowest lit row
  would pass row 59 (`BORDER_ROWS - 1`). The lowest lit row is a thick line's lower row (`STROKE` 2: one row under its
  points) or the head disc's radius. So the out player lies down above rows 60 to 63, and the topple and fade still
  show.
- **Test added** (`tests/arcade/test_freeze.py`): `test_own_drawing_keeps_rows_60_to_63_dark[canonical, duo]`. It
  drives each scenario through the game with the file's `make`/`drive` until `done()`. It asserts that a seat toppled,
  and that rows 60 to 63 of the game's own frame are dark on every tick.
  - Before the fix: 52 lit ticks in `canonical` from t 8.27 and in `duo` from t 8.13, as the review found.
  - After the fix: none.
- `test_an_out_figure_topples_and_fades` is unchanged and passes.

### Flap

- **Fix** (`arcade/games/flap.py`):
  - **The hint.** `HINT_TEXT` moves from y 55, rows 55 to 61, to y 37, rows 37 to 43. The row is not a named
    constant: the expression `round(h * 0.7) + GLYPH_H + 3` became `round(h * 0.7) - CELL_H`. That is one line pitch
    over `READY_TEXT` (rows 45 to 51), with a blank row between, clear of the bird (rows 26 to 33 in `ready`) and the
    gauge ticks. I chose y 37 over the review's y 53 because y 53's bottom glyph row would sit on the floor line, row
    59. `GLYPH_H`, the expression's only user, is dropped.
  - **The wings.** The wings-down block is drawn at `min(top + BIRD_H, FLOOR_Y - 1)`, so a bird on the floor keeps
    its wings on rows 58 and 59.
- **Test added** (`tests/arcade/test_flap.py`): `test_own_drawing_keeps_rows_60_to_63_dark[idle_body, nobody,
  one_arm, floor_crash]`. `floor_crash` is one flap at 1.3 s, then both hands down; its new helper is `floor_crash()`.
  Each case asserts that the hint showed, or for the crash that the bird crashed on the floor, and that rows 60 to 63
  are dark on every tick.
  - Before the fix: 1741, 841, 76 and 37 lit ticks. The floor crash ran from t 4.13, as the review found.
  - After the fix: none.

### Tests after both fixes

- `tests/arcade/test_flap.py tests/arcade/test_freeze.py`: 80 passed, 40.85 s.
- `tests/arcade/test_oracle.py -k "flap or freeze"`: 6 passed, 96.91 s.
- `arcade.feel.report` on the 20 report seeds: `failures` is empty for both games.

| Metric | Flap | Freeze | Budget |
|---|---|---|---|
| win_good | 1.0 | 1.0 | min 0.7 |
| win_lazy | 0.6 | 0.4 | 0.1 to 0.7 |
| win_none | 0.0 | 0.0 | max 0.05 |
| response_ticks | 1.5 | 1.0 | max 2 |
| response_px | 16 | 396 | min 12 |
| fidelity | 0.9903 | 0.9999 | min 0.8 |
| range | 0.8254 | 0.9213 | min 0.6 |
| lit_fraction | 0.0564 | 0.0992 | 0.01 to 0.5 |
| dim_fraction | 0.0 | 0.0274 | max 0.1 |
| liveliness | 0.0014 | 0.0197 | min 0.001 |
| flash_area_raw | 0.0 | 0.0186 | max 0.1 |
| square_flashes | 0 | 5 | max 6 |
| score_visible, score_legible | 1.0, 1.0 | 1.0, 1.0 | min 0.8, 0.9 |
| round_seconds | 49.0 | 52.87 | 20 to 120 |
| phases_reached | 1.0 | 1.0 | 1.0 |

The win rates did not move. Freeze's `dim_fraction` rose from 0.0157 to 0.0274, because the lifted topple fades in
view.

- **Full suite** (the test command, at d81599e): 2092 collected, 2089 passed, 3 skipped (the base's three), no
  failure, 484.37 s, under the 540 s cap. The load average was about 4.

### Commits

| sha | subject |
|---|---|
| 1acbe6e | fix(arcade): it19 review, Freeze's topple lies down above rows 60 to 63 |
| d81599e | fix(arcade): it19 review, Flap's hint and floor-crash wings stay above rows 60 to 63 |
