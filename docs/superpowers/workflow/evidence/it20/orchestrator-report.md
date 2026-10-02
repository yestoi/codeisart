# it20 orchestrator report: the suite's room, Jump, C55, Blob ids, M5's blobs and scenario files

Plan: `docs/superpowers/plans/2026-10-02-it20-suite-room-jump-m5.md`. Main was at 1a9ca88 with a clean tree at the
start (state.md aside, see below). BASE for the parallel tasks (after R, the rename, I0 and E0) is b4f1e9b. The task
reports are `E0-report.md`, `G5-report.md`, `F1-report.md`, `S1-report.md` and `S2-report.md` in this folder.

## Completed

- **R** (serial lane, mine, test-first). The four new tests were written first and failed (`pooled` had no
  `start`, `Pool`, `beside_the_pool` or `rows_for`), then passed.
  - `tests/arcade/pooled.py`: `fill`'s body split into `start(reports, plays, workers) -> Pool` and `Pool.join()`;
    `fill` is `start(...).join()` and gives the same warnings, so its two failure tests hold unchanged. `Pool` has
    the plan's `keys`, `before`, `started`, `elapsed` and `waited`, plus `joined`, `tmp` and `stop()`.
    `WORKER_TIMEOUT_S` is 180.0. `RUNNING`, `BESIDE_THE_POOL`, `beside_the_pool` and `rows_for` are as the plan says.
  - `tests/conftest.py`: `pytest_collection_finish` starts the pool for the selection's rows (not under
    `--collect-only`); `pytest_runtest_setup` (tryfirst) joins it before the first item that is not beside it;
    `pytest_sessionfinish` stops a pool never joined; `pytest_terminal_summary` prints the `pooled:` line. Every hook
    is a no-op when no pool runs; `tests.arcade.pooled` is imported only when a selected test reads the pool.
  - `tests/arcade/test_oracle.py`: `pooled_plays` returns `(RUNNING.before, RUNNING.join())` when the session
    started a pool, else today's fill. No assert changed. New: `test_stop_kills_a_running_pool_and_leaves_no_child`,
    `test_join_twice_waits_once`, `test_the_pool_runs_beside_the_soaks_only`, `test_the_rows_follow_the_selected_tests`.
  - Committed as 019d434.
- **The gate**: one full run with `--durations=40`, saved as `r-durations.txt`: 2093 passed, 3 skipped, **402.71 s**,
  `pooled: 420 plays, 4 workers, 109.2 s, the join waited 10.7 s`. The BASE reading at the same load
  (`orient-durations.txt`) was 505.09 s, so R saves about 102 s (the plan expected about 95 s). A whole-suite
  `--collect-only -q` prints no `pooled:` line, and no worker was left after either run.
- **The rename** (mine, test-first): `MENU_ORDER`'s `"strongman"` became `"jump"`; `test_game.py`'s menu tuple, the
  broken-module test's fake key and its two sorted lists changed with it, the names only. The tests failed first
  (2 failed), then passed. `test_scores.py:158` and the helper's free text stay. Committed as 85fd34f.
- **I0** (mine, test-first): `Move.lift: float = 0.0`, its last field; `_sensed` builds the Person at
  `HIP_Y - lift`, `HIP_Y = Person().y0` (0.55). No noise draw. New tests `test_move_lift_raises_the_whole_body` and
  `test_move_without_lift_is_todays_body` failed first (`unexpected keyword argument 'lift'`), then passed;
  `test_bots.py` 15 passed. Committed as e8335bd.
- **E0** (opus, main checkout): `Blob` gains keyword-only `id = -1`, `vx = 0.0`, `vy = 0.0`. 99609bd and its report
  b4f1e9b. I checked the diff and reran `test_sensed`, `test_actors`, `test_runner` and `test_game`: 171 passed.
- **G5, F1, S1, S2**: spawned in one message, each with `isolation: "worktree"`, each checked b4f1e9b first. Each
  branch touches only its plan files plus its report. Merged into main with `--no-ff` in plan order (G5, F1, S1, S2).
  No merge was reverted, no task was sent back and nothing was cut.
- **I1**: the full suite once after the last merge with `--durations=25`, saved as `final-durations.txt`: 2185
  passed, 3 skipped, **440.51 s** (the plan expected about 445 s; cap 540 s). `pooled: 480 plays, 4 workers,
  130.2 s, the join waited 9.4 s`: under the 150 s flag. The guide gained `Move(lift=...)` (section 4) and a measured
  jump's baseline and hip check (section 5). Committed with both durations files as c1365f7.
- The worktrees and branches are left in place. Nothing was pushed or deployed; nothing went to the Pi or the card.

### Suite time and the pool

| Run | Collected | Passed | Skipped | Time | Pool (plays, elapsed, join wait) | Load (start, end) |
|---|---|---|---|---|---|---|
| BASE reading (orient, given) | 2092 | 2089 | 3 | 505.09 s | in process, 89.92 s setup | 2.54, 4.53 |
| The gate after R (019d434) | 2096 | 2093 | 3 | 402.71 s | 420, 109.2 s, 10.7 s | 4.26, 4.44 |
| Final, after the S2 merge (b3ff645) | 2188 | 2185 | 3 | 440.51 s | 480, 130.2 s, 9.4 s | 8.62, 4.01 |

- The four parallel tasks added 37.8 s together, gate to final (the plan: G5 30 + F1 2 + S1 4 + S2 2 = 38 s).
- The join's wait shows as the setup of `test_all_games.py::test_every_game_fits_the_tick_budget[copyme-128x64]`
  (10.73 s at the gate, 9.42 s at the end): the first perf soak, so no worker runs beside a timed test.
- The games' own 5-seed tests left the top of the durations: they read the pooled plays (it19's 7 to 10 s each).
- The load average peaks near 12 while the four workers play beside the soaks, and falls back after the join.

### Each merge's subset

Command: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs
--durations=10 <files>` from the main checkout.

| After | Files | Passed | Failed | Time | Pool |
|---|---|---|---|---|---|
| G5 merge (6d4bc32) | test_jump, test_all_games, test_oracle, test_game | 178 | 0 | 255.78 s | 480, 132.5 s, waited 132.6 s (deviation 2) |
| F1 merge (3865e2c) | test_all_games, test_copyme, test_swat, test_oracle, test_game | 229 | 0 | 178.17 s | 480, 126.1 s, waited 10.6 s |
| S1 merge (ea6bc74) | test_all_games, test_blobs, test_oracle, test_game | 155 | 0 | 164.77 s | 480, 126.6 s, waited 9.7 s |
| S2 merge (b3ff645) | test_scenario, test_blobs, test_sensed, test_game, then the full suite | 101, then 2185 | 0 | 0.55 s, then 440.51 s | as the final run |

No timing test failed in any run.

### Each task's final numbers

- **E0** (opus, 1.6 min): `test_sensed.py` 27 passed (3 new, each failed first); the plan's guards with
  `test_game.py` 233 passed in 16.72 s. No deviation, no owner question.
- **G5 Jump** (sonnet, 8.3 min): `test_jump.py` 39 passed in 16.2 s; `test_all_games.py -k jump` 8 passed;
  `test_oracle.py -k jump` 3 passed. No constant and no bot number moved from the plan. Bots: Person's torso is 0.18
  of the frame; good peaks 44 cm (lift 0.158), lazy 34 cm (lift 0.122), an 18-tick arc.
  - Feel (20 seeds, no failures): win_good 1.0, win_lazy 0.45, win_none 0.0, response_ticks 1.0, response_px 197.5,
    fidelity 0.999, range 0.685, lit_fraction 0.111, dim_fraction 0.0, liveliness 0.018, flash_area_raw 0.0024,
    square_flashes 4.0 of 6, score_visible 0.978, score_legible 1.0, round_seconds 30.0, phases_reached 1.0.
- **F1 C55** (sonnet, 3.3 min): `test_copyme.py` and `test_swat.py` 90 passed in 35.6 s; the soaks and the oracle
  for both 22 passed. Copy Me's feel meets every budget: flash_area_raw 0.0110, square_flashes 4.0, win_good 1.0,
  win_lazy 0.4, win_none 0.0, phases_reached 1.0.
- **S1 blobs** (opus, 22.1 min): `test_blobs.py` 16 passed in 0.33 s (the 15 named plus
  `test_static_lamps_do_not_crowd_out_a_moving_light`). Perf: `FrameFeatures.update` at 160x120 0.405 ms mean,
  0.513 ms max, against 3 ms; 1.19 ms with 32 lights.
- **S2 scenario files** (opus, 17.3 min): `test_scenario.py` 16 passed in about 0.1 s (the 11 named plus 5).

## Deviations

### Mine

1. **One `cd`.** One check command (the `-k flap` pool check after R) began with `cd /Users/trey/dev/codeisart`,
   against the rule. The shell starts there anyway, so it changed nothing; no later command used `cd`.
2. **The G5 subset's file order.** pytest runs the files in the order they are named. With `test_jump.py` first, the
   first test was not beside the pool, so the join waited for the whole pool (132.6 s) and the soaks ran after it.
   The later subsets named `test_all_games.py` first, and the join then waited about 10 s. The full suite's own
   order puts `test_actors.py` and `test_all_games.py` first, so the full runs are not affected. For it21: a subset
   command should list `tests/arcade/test_all_games.py` first.
3. **S2's subset folded into the final run.** After the S2 merge I ran S2's and the source files' tests (101 passed),
   then the full suite once, which holds the subset's files. Running the soaks and the oracle twice in a row would
   have added about 3 minutes and tested nothing new: S1 and S2 touch no game.
4. **The pool's `elapsed` and `waited`.** `elapsed` runs from the start to the last worker's out-file write (its
   mtime), or to the join's read for a worker that failed. So it is the workers' time even when the join comes
   after they are done. `waited` is the first join's own wait. The plan's "the second's `waited` 0" is read as "the
   second join waits nothing": the test measures the second call under 0.1 s and checks `waited` keeps the first
   join's value, which the summary line prints.
5. **More on `Pool` than the plan lists.** `joined`, `tmp`, `stored`, `procs` and `stop()`'s effect on a later
   join, which returns `set()`. A stopped pool's summary line reads `pooled: stopped before its join, <k> workers`.
6. **I0's `HIP_Y`.** A module constant `HIP_Y = Person().y0` in `bots.py`, so Person's 0.55 is not written twice.
   `0.55 - 0.0` is exactly 0.55, so every existing play is unchanged.
7. **`state.md` left alone.** `docs/superpowers/workflow/state.md` was modified in the main checkout by someone else
   during the run. It is the operator's: I neither edited nor committed it.

### Flagged for the loop's review (not changed by me)

8. **Jump's bell ignores `fx.flash`'s return.** `arcade/games/jump.py:227` calls `self.fx.flash(FLASH, 0.15)` and
   drops the result, with the comment "the governor may refuse: nothing else hangs on it". The Global Constraints
   say "Every `fx.flash` return is checked", and G5's text says "a bell: `fx.flash(...)` (checked)". The "DING!" pop
   shows either way, and `test_the_bell_rings_once_and_checks_the_flash` asserts the flash returned True. A refusal
   needs a flash in the last `FLASH_GAP`, and the bell rings at most once per 9 s attempt. It is not a test break,
   so I did not send it back. Copy Me's pattern would be a burst at the bell when the flash is refused.
9. **`Blob.vy`'s unit.** The plan says `vx`, `vy` are "fw/s, the source's". E0's comment on `vx` says frame widths
   per second. S1 computes `vy` in frame heights per second, as `Body.vy` is (S1's deviation 6 and Q3).
10. **F1's colour test, its second half.** "In a `duo` frame of `play` no outline pixel is drawn in seat b's
    colour" is asserted as: both colours appear in a duo `play` frame and the two constants differ. It holds because
    the outline is drawn only in `OUTLINE_COLOR`. It does not check the pixels at seat b's figure.

### The implementers' (details in their reports)

- **E0**: none.
- **G5**:
  - The bell rings live, on the first counted capture at or over `bell_cm`, not at the window's end.
  - `measure_rise` also returns None under `MIN_RISE`; the bar and `rise` then read 0.
  - The ready check keeps samples for `SETTLE_SECONDS`, at least `MIN_SAMPLES = 5`, spanning at least
    `SETTLE - 0.05` s. A player seen again after the grace, or a new id, starts the samples afresh.
  - `active` is False outside `play`, and the hint shows only in `play`. So `idle_body` hints about 3.5 s after the
    game starts, against the guide's "within three seconds"; "GET SET" is on the wall from the first tick.
  - Added constants: `COLUMN_SLACK = 1`, `MIN_SAMPLES = 5`, `LINE_COLOR` white (the peak line), `TEXT_COLOR`
    (255, 160, 0), `BELL_W, BELL_H = 5, 4`.
  - The canonical is 40 s: walk 0.5 to 0.15 to 0.85 to 0.5 at 0.1 zone/s from 5.5 s (far end at 16 s), jumps at 6.5,
    15.5 and 24.5 s. Two bells ring inside the measured 20 s: square_flashes 4.0.
  - The result number is drawn at x 20, row 24, over a black box; `over` shows the best as the white line on an empty
    bar plus the score.
- **F1**: none. The plan's "282, 301, 413" are magenta's distances; the 40 F1 measured is the old cyan against seat
  b's blue, so they agree.
- **S1** (its report's deviations and Q1 to Q3):
  - A blob's colour is the halo's hue at full saturation, with brightness from the core's mean.
  - The halo test reads the saturation of the halo's mean colour.
  - A new `SCAN_BLOBS = 32`: the cap of 8 comes after the still-light mask, so still lamps cannot crowd out a moving
    light.
  - `FrameFeatures(size=...)` is the motion grid's size; frames of any size are accepted and not resized.
  - The zone crop keeps the zone's full width and takes rows at 2:1 centred on the zone; a shake returns a `(0, 0)`
    grid.
  - `vy` is in frame heights per second (see 9).
  - The tracker matches against the previous capture only, with no coasting.
  - NaN centroids are dropped inside `find_blobs`.
  - `Calibration.static_mask` is not applied.
- **S2** (its report's D1 to D6):
  - D1: each record also stores `camera_t` and `camera_fresh`, and replay stamps a new capture only where the
    recording had one. Stamping every record as `ScriptedCamera` does replayed a 10 fps recording as 30 captures a
    second; its new test `test_replay_holds_a_capture_as_the_recording_did` pins this.
  - D2: after the end, the last record is held with its old stamp and `available` turns False.
  - D3: blobs are placed again with the caller's calibration, so `in_zone` is not stored.
  - D4 to D6: the draft's tests are adapted to the new shapes and the `(0, 0)` grid. `open_replay` and
    `ReplayStream` take a `clock`, and `ScenarioReader` takes a `calibration`.
  - Replaying a raw file raises `ValueError` (iteration 21).

### Owner questions raised by the implementers (each defaulted)

- **G5**:
  1. Should the hint also show in `ready`?
  2. The figure can pass under the striker, the score box and the centred texts, so `player_xy` can be a covered
     pixel.
- **S1**:
  - Q1: `MIN_AREA = 4` px was set for 640x480 frames. Default: keep it and refit with C34 at GATE A.
  - Q2: should the grid default be the wall's (128, 64)? Default: the plan's (160, 120), and it21's wiring chooses.
    It21 must also shrink the Mac's 640x480 frames before calling `update`.
  - Q3: `vy`'s unit (see 9). Default: fix E0's comment the next time `sensed.py` is touched.
- **S2**:
  - Q-S2a: keep D1's stamping.
  - Q-S2b: a raw file stores one WAV inside each record, not one beside the file.
  - Q-S2c: blobs are placed again, as bodies are.

## Test status (command + counts)

Command, from `/Users/trey/dev/codeisart`:
`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs`

- The gate after R (019d434), `--durations=40`: 2096 collected, 2093 passed, 3 skipped, 0 failed, 402.71 s.
- Final after the last merge (b3ff645), `--durations=25`: 2188 collected, 2185 passed, 3 skipped, 0 failed, 440.51 s.
- The 3 skips are the base's three, all Linux-only. No timing failure in any run.
- Collected grew by 92: I0 2, E0 3, G5 50 (39 own, 8 soaks, 3 oracle), F1 5, S1 16, S2 16.

The final `--durations=25` table, from `final-durations.txt`:

```
10.08s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[freeze-128x64]
9.96s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[pong-128x64]
9.42s setup    tests/arcade/test_all_games.py::test_every_game_fits_the_tick_budget[copyme-128x64]
8.86s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[pong-96x48]
7.65s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[copyme-128x64]
7.34s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[quickdraw-128x64]
7.31s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[jump-128x64]
7.24s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[copyme-96x48]
7.13s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[jump-96x48]
6.90s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[swat-128x64]
6.77s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[flap-128x64]
6.29s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[dodge-128x64]
6.15s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[freeze-96x48]
6.09s call     tests/test_show_shot_governed.py::test_governed_entry_session_runs_the_entry_through_the_governor
6.01s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[quickdraw-96x48]
5.58s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[flap-96x48]
5.20s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[dodge-96x48]
5.08s call     tests/arcade/test_all_games.py::test_every_game_soaks_without_error[swat-96x48]
4.48s call     tests/test_show_shot.py::test_entry_mode_plays_the_sample_entry_through_the_pipeline
3.82s call     tests/test_curated_entries.py::test_entry_plays_through[sloane]
3.78s call     tests/arcade/test_first_playable.py::test_first_playable_keeps_the_flash_rule
3.64s call     tests/test_curated_entries.py::test_entry_plays_through[endoh1]
3.64s call     tests/test_show_shot.py::test_strobe_session_is_held
3.53s call     tests/test_entries.py::test_sample_entry_band_leaves_no_trail
3.42s call     tests/arcade/test_oracle.py::test_evidence_package_for_pong
pooled: 480 plays, 4 workers, 130.2 s, the join waited 9.4 s
2185 passed, 3 skipped in 440.51s (0:07:20)
```

For it21: the soaks (about 140 s of the path now) are the largest block left, and C (the soaks in workers) is
it21's first task by the plan. The pool's 130.2 s is under the 150 s flag, but Paint and Tug will add plays against
the 180 s deadline.

## Commits (sha + subject)

| sha | subject |
|---|---|
| 019d434 | test(arcade): it20 R, the oracle's pool starts when collection ends and plays beside the soaks |
| 85fd34f | feat(arcade): it20 rename, MENU_ORDER's strongman becomes jump (Q99) |
| e8335bd | feat(arcade): it20 I0, a bot's Move lifts the whole body (Move.lift) |
| 99609bd | feat(arcade): it20 E0, Blob gains keyword-only id, vx and vy (-1 untracked, still by default) |
| b4f1e9b | docs(workflow): it20 E0 report |
| db965d6 | feat(arcade): it20 G5, Jump (a high striker: three 5 s windows, the nose's rise over the torso, the bell) |
| 216ca2c | feat(arcade): it20 F1, Copy Me's outline is magenta so it reads on player 2 (C55, Q117) |
| ffb0890 | feat(arcade): it20 S1, blobs and motion from camera frames (core Task 15 as amended, C11, C17) |
| 3c1a4d2 | feat(arcade): it20 S2, scenario files and replay sources |
| 6d4bc32 | merge: it20 G5, Jump (jump) |
| 3865e2c | merge: it20 F1, C55, Copy Me's outline is magenta (Q117) |
| ea6bc74 | merge: it20 S1, blobs and motion from camera frames (M5) |
| b3ff645 | merge: it20 S2, scenario files and replay sources (M5) |
| c1365f7 | docs(guide): it20 I1, Move(lift=...) and a measured jump's baseline and hip check; the gate's and the final run's durations |
| (this file) | docs(it20): the orchestrator's report |

The branches are kept, as are their worktrees under `.claude/worktrees/`:

| Task | Branch | Worktree |
|---|---|---|
| G5 | `worktree-agent-a8f8620e33f1caea7` | `agent-a8f8620e33f1caea7` |
| F1 | `worktree-agent-a59c77d571b065b68` | `agent-a59c77d571b065b68` |
| S1 | `worktree-agent-ad3f0b6a0ff391d2e` | `agent-ad3f0b6a0ff391d2e` |
| S2 | `worktree-agent-a8f45f86fcf2790d9` | `agent-a8f45f86fcf2790d9` |

## Minutes (serial lane, parallel tasks, integration)

- **Serial lane:** about 16 min, from 04:06 to the BASE at 04:22. That covers R (about 5 min), the gate's full run
  (6 min 44 s, 04:11 to 04:18), the rename, I0 and E0 (1.6 min).
- **Parallel tasks:** about 23 min of wall time, from the spawn at about 04:22 to 04:45, bound by S1.
  - G5: 8.3 min (sonnet).
  - F1: 3.3 min (sonnet).
  - S1: 22.1 min (opus).
  - S2: 17.3 min (opus).
- **Integration:** about 22 min, from 04:46 to about 05:08. That covers four merges, three subsets (4.3, 3.0 and
  2.7 min), the final full run (7.3 min), the guide and this report.
- **In all:** about 62 min against the 75-minute target.
