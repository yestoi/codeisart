# Iteration 20 (arcade): the suite's room, Jump, C55, Blob ids, M5's blobs and scenario files
BASE: HEAD after R, the rename, I0 and E0 are committed (the orchestrator gives the sha). Thin plan. Not a safety
slice. "Spec" = `docs/superpowers/specs/2026-09-26-wall-arcade-design.md`, not edited. "Core plan" =
`docs/superpowers/plans/2026-09-26-wall-arcade-core.md`: its code is a draft to test, not text to paste.
No engine file but `arcade/sensed.py` (E0); no safety file (`arcade/flash.py`, `brightness.py`,
`show/display/colorlight.py`), no change to the runner's order. The writer's report:
`docs/superpowers/workflow/evidence/it20/plan-writer-report.md`.
## Global Constraints
- Test command, from the checkout's (or worktree's) root: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
  /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs`. Baseline at d81599e's tree: 2092 collected, 2089
  passed, 3 skipped, 476.51 to 505.09 s on the shared Mac. Worktrees show a 4th skip (no `models/` there). One command
  per Bash call; tools as modules (`python -m tools.arcade_shot`); no `cd`.
- The orchestrator runs the FULL suite at two points only: after R (the gate, below) and once after the last merge.
  After each other merge: the merged task's test files plus `tests/arcade/test_all_games.py`,
  `tests/arcade/test_oracle.py` and `tests/arcade/test_game.py`. Implementers run their own files and the generic
  ones (`test_all_games.py -k <name>`, `test_oracle.py -k <name>`, `test_game.py`), never the whole suite.
- Touch only your task's files. Test-first. No removed or weakened assert; no band in `arcade/feel_budgets.toml` or a
  `*_feel.toml` loosened; no `*_feel.toml` override without a game-made reason (guide 5). The only changed asserts are
  the rename's three in `tests/arcade/test_game.py` (lines 171, 236, 239; Q99, the name only) and F1's colour value
  in `tests/arcade/test_copyme.py:178` (`(0, 200, 255)` becomes `(255, 0, 255)`, `MATCH_COLOR` unchanged; Q117). An
  assert this plan does not name that would have to change: stop and report.
- 128x64 only (Q32, Q33, Q82): every game declares `layouts={"128x64"}`; no code, test or tuning for another size
  (the generic soak at 96x48 is the engine's and stays as it is). Rows 60 to 63 stay free (the runner's marker).
- The frozen protocol is unchanged; `test_protocol_members_are_the_frozen_set` is not edited. `GameInfo.players` is 1
  or 2 (`arcade/game.py:89`): a game reads `sensed.player` and `sensed.player2`, never `bodies[0]`.
- No game reads the microphone or the motion grid (Q99): every `needs` is `{"pose"}`. Nothing is fetched.
- Flash (C24, guide 6): each game's own frames keep governor held ticks 0 and raw `concurrent_area` under 0.1; no
  reversing stripes; a loss or a miss holds and fades, never blinks; saturated red counts double. Every `fx.flash`
  return is checked.
- C41, C42: a still body (and Nobody) scores nothing and banks no best; Jump says what counts below. Bots rank
  `win_good > win_lazy > win_none`, `phases_reached == 1.0`, every budget met (`tests/arcade/test_oracle.py:101-117`).
  Bot numbers and the named levers are starting values: tune them until `win_good >= 0.7` and `0.1 <= win_lazy <=
  0.7` hold on the 20 report seeds (`pytest tests/arcade/test_oracle.py -k jump`); no other rule moves.
- C46: a figure maps raw `zone_x` with a column backlash of `COLUMN_SLACK = 1` in the game's own file (the lobby's two
  lines, `arcade/attract/lobby.py:49,181`), no Glide; graces `capture_grace(CAMERA_FPS)`, `CAMERA_FPS = 10`.
- Colours saturated, low channels 0, no channel set under 140 alone (`feel.DIM_LEVEL`); scores at 2x (`SCORE_SCALES =
  (2,)`), drawn last over a black box 1 px wider than the text, from the game's first tick (`score_visible` >= 0.8).
- `Sensed`/`Audio`/`Blob`'s new fields by keywords (C21); seeds `zlib.crc32`, printed; `time.thread_time`; no push,
  save or config read.
- The canonical's first 20 s are measured (`feel.FEEL_SECONDS`): 2 s empty, the walk-up, the raise, then the sweep
  that fidelity and range need, inside those 20 s; then play that gets past the first attempt.
- Suite: at most 540 s (Q102); nothing is reverted or left out for its time. Shares: R -95 s, the rename 0, I0 +0.5 s,
  E0 +0.5 s, G5 +30 s, F1 +2 s, S1 +4 s, S2 +2 s: expected about 410 s after R (505.09 s load) and about 445 s after
  the last merge. Report what your files add (`--durations=15`).
- Template tests in every game's file (`test_flap.py`'s shape): `test_debug_state_is_clean`,
  `test_required_scenarios_start_with_an_empty_wall`, `test_canonical_drives_the_lobby_to_<name>`,
  `test_bots_module_is_found`, `test_good_beats_lazy_beats_nobody` (5 seeds via `helpers.played`),
  `test_good_round_length_in_band`, `test_feel_file_overrides_have_reasons`, `test_seeded_runs_repeat`.
- Under load three timing asserts fail and pass on a rerun (the it15 note:
  `tests/arcade/test_headless.py::test_tick_budget_with_the_governors_share`, its asserts at :236-237, and
  `tests/test_show_shot.py::test_strobe_session_is_held`): rerun them alone before a revert.
## Lanes and merge order
1. SERIAL, the orchestrator in the main checkout, each committed and checked before the next: R, the gate (one full
   run), the rename, I0; then E0 (one implementer, `model: opus`, main checkout). BASE is E0's commit.
2. PARALLEL, `isolation: "worktree"`, ONE message: G5 Jump (`model: sonnet`), F1 C55 (`model: sonnet`), S1 blobs
   (`model: opus`), S2 scenario files (`model: opus`). Each checks `git rev-parse --short HEAD` equals BASE first.
   No cross-imports: S2 does not import S1's module.
3. Merge G5, F1, S1, S2 with `git -C /Users/trey/dev/codeisart merge --no-ff`, the subset above after each; a merge
   that breaks it is undone with `git revert -m 1` and sent back once. Then the full suite once, then I1.
Files by task (no file under two tasks):
- R: `tests/arcade/pooled.py`, `tests/conftest.py`, `tests/arcade/test_oracle.py` (fixture and new tests only).
- Rename: `arcade/games/__init__.py`, `tests/arcade/test_game.py`.
- I0: `arcade/bots.py`, `tests/arcade/test_bots.py`.
- E0: `arcade/sensed.py`, `tests/arcade/test_sensed.py`.
- G5: `arcade/games/jump.py`, `jump_bots.py`, `jump_feel.toml`, `tests/arcade/test_jump.py`.
- F1: `arcade/games/copyme.py`, `tests/arcade/test_copyme.py`, `tests/arcade/test_swat.py`.
- S1: `arcade/sources/blobs.py`, `tests/arcade/test_blobs.py` (both new).
- S2: `arcade/sources/scenario.py`, `arcade/sources/replay.py`, `tests/arcade/test_scenario.py` (all new).
- I1: `.claude/skills/arcade-game-authoring/SKILL.md`.
Not edited: `arcade/sources/__init__.py` (no export in it20: the sources are wired in it21), `camera.py`,
`pose_mediapipe.py`, `tests/arcade/helpers.py`, `tests/arcade/conftest.py`, `feel_budgets.toml`, `main.py`,
`config.py`, `arcade.toml`, `pyproject.toml`, `.gitignore`, `arcade/figure.py`, `arcade/attract/lobby.py`.
## R: the pool runs beside the soaks and fills before the games' own files (orchestrator)
Why (orient, evidence/it20/orient-durations.txt): the pool's 89.9 s setup blocks the session at `test_oracle.py`, and
Copy Me's, Dodge's, Flap's and Freeze's own 5-seed tests (34.3 s) make in process plays the pool also needs: their
files sort before `test_oracle.py`, Pong's, Quick Draw's and Swat's after it. The games' 5 seeds are the first 5 of
the report's 20 (`bots.seeds` is `crc32(f"{name}:{layout}:{i}")` for `i < n`; the same `play_key`). In run order,
`tests/arcade/test_all_games.py` (the soaks, 88.8 s) is the second file; nothing in it but
`test_every_game_fits_the_tick_budget` (perf, `thread_time`) is timed.
Both candidates, as one: (B) the pool starts when collection ends and runs beside the soaks; (A) it is joined before
the first test that is not a soak, so every game's own tests and the reports read `PLAYS`. Plain subprocesses, as
it18 (no `multiprocessing`). Not C: the estimate is under 420 s without it (the report has the sum).
- `pooled.py`: `fill`'s body splits into `start` and `Pool.join`; `fill(reports, plays=PLAYS, workers=PLAY_WORKERS)`
  stays and is `start(...).join()` with today's warnings, so its two failure tests hold unchanged.
  - `class Pool`: fields `keys: frozenset[Key]` (asked), `before: frozenset[Key]` (report keys already in `plays` at
    the start), `started: float` (monotonic), `elapsed: float | None`, `waited: float | None` (the join's own wait).
    `join() -> set[Key]`: waits to the deadline, kills and reaps the rest, stores the plays it read, removes its
    temporary directory; a second call returns the same set at once. `stop() -> None`: kills, reaps, removes; no
    play stored. Neither leaves a child on any path.
  - `start(reports, plays=PLAYS, workers=PLAY_WORKERS) -> Pool` (a pool of no worker when `fill` would start none;
    its join returns `set()` with `fill`'s core-count warning). `RUNNING: Pool | None = None`, the session's pool.
  - `WORKER_TIMEOUT_S = 180.0` (was 120): from the first worker's start; eight games' 480 plays take about 105 s alone
    and about 120 to 140 s beside the soaks. A failed share is replayed in process (about 100 s) and fails
    `test_the_pool_made_every_missing_play`: about 410 + 60 + 100 s, under 10 minutes; four hung shares were over 10
    minutes at 120 s as well. The gate and I1 record the pool's `elapsed`; over 150 s is flagged for it21's plan.
  - `BESIDE_THE_POOL = ("tests/arcade/test_actors.py", "tests/arcade/test_all_games.py")`; `beside_the_pool(nodeid:
    str, perf: bool) -> bool`: the node's file is in it and it is not marked `perf`.
  - `rows_for(items, report_plays) -> list` (the rows the selected tests read): an item that needs `pooled_plays`
    with a `game_cls` param asks for that game's row; one that needs `pong_report`, Pong's; any other (the pool's own
    test) every row. Rows keep `REPORT_PLAYS`' order. So `-k jump` pools Jump's 60 plays, not 480.
- `tests/conftest.py` (all hooks no-ops when no pool runs):
  - `pytest_collection_finish(session)`: unless `--collect-only`, when a selected item needs `pooled_plays`,
    `pooled.RUNNING = pooled.start(pooled.rows_for(session.items, item.module.REPORT_PLAYS))`.
  - `pytest_runtest_setup(item)`: a running pool not joined is joined before any item for which
    `beside_the_pool(item.nodeid, item.get_closest_marker("perf") is not None)` is False. So no worker runs beside
    the three timing asserts (Global): `test_headless.py` runs after the join in any selection, and
    `test_strobe_session_is_held` and `tests/test_show_soak.py` (no child left) are outside `tests/arcade`.
  - `pytest_sessionfinish`: `stop()` a pool not joined (`-x`, Ctrl-C, an error). `pytest_terminal_summary`: one line,
    `pooled: <n> plays, <k> workers, <elapsed> s, the join waited <waited> s`.
- `test_oracle.py`: `pooled_plays` returns `(RUNNING.before, RUNNING.join())` when the session started a pool (its
  rows are the selection's), else today's `(before, pooled.fill(REPORT_PLAYS))`. No assert changes.
- Acceptance: every test in `test_oracle.py` passes unchanged; new there: `test_stop_kills_a_running_pool_and_leaves_
  no_child` (the `Popen` that `pooled.start` calls patched to start `sys.executable -c "import time;
  time.sleep(60)"`, `subprocess.run` left real: after `stop`, `children_of_this_process() == 0`, the temporary
  directory gone, nothing stored); `test_join_twice_waits_once` (a cannot-start pool: two joins return `set()`, the
  first join's warnings and none from the second, the second's `waited` 0);
  `test_the_pool_runs_beside_the_soaks_only` (soak and actors nodes True; a perf soak node, `test_bots`,
  `test_headless`, `tests/test_show_shot.py` False); `test_the_rows_follow_the_selected_tests` (stand-in items:
  `game_cls` Flap gives Flap's row, `pong_report` Pong's, the pool's test all rows).
- The gate (one full run, `--durations=40`, saved as `evidence/it20/r-durations.txt`): passes with 3 skips; the
  pool line printed; a `--collect-only -q` run prints no `pooled:` line (no pool started). Expected about
  410 s at 505.09 s's load: the 89.9 s and 34.3 s leave the path, about 15 s of join wait and 10 s of slower soaks
  come in. R saves under 60 s against the same load's reading of BASE: R stays (it is not slower), the slice
  lands, the report says so, and C (the soaks in workers) is it21's first task. R fails a test: one fix round; still
  failing, `git revert` R but keep `WORKER_TIMEOUT_S = 180.0` alone, land the rest, and report the time.
## The rename (orchestrator)
- `MENU_ORDER`'s `"strongman"` becomes `"jump"` (Q99). `test_game.py:171`'s tuple changes with it. In
  `test_broken_module_is_logged_and_skipped`, the fake's key at :226 becomes `"jump"` and the name in the lists at
  :236 and :239 becomes `"jump"`, sorted (the test keys its fakes by `MENU_ORDER`; Q121); the helper's free text at
  :221-222 (`strongman_audio`) and `test_scores.py:158` stay. Before G5 merges, `all_games()` skips the missing
  module as it skips every unbuilt one.
## I0: a bot can jump (orchestrator)
Why: `Move` (`arcade/bots.py:40`) has no whole-body rise; `Person.jump` exists but a bot's `Person` lives one tick.
- `Move` gains `lift: float = 0.0`, last field: the hips (and every keypoint) raised by that share of the frame
  height on the tick. `_sensed` builds the `Person` with `y = Person's 0.55 - lift`. `lift` carries no noise draw, so
  no existing play's rng sequence changes. Docstring says so.
- Acceptance (`tests/arcade/test_bots.py`): `test_move_lift_raises_the_whole_body` (every keypoint 0.1 higher in the
  camera frame with `Move(lift=0.1)` than with `Move()`, before `place`, within 1e-6);
  `test_move_without_lift_is_todays_body` (`Move()` and `Move(lift=0.0)` give equal `bodies`, every keypoint,
  `in_zone`, `zone_x`, `zone_y`, and the same rng draws; `Sensed` is `eq=False`). The rest unchanged.
## E0: Blob ids and velocities (one implementer, opus, main checkout)
- `Blob` (`arcade/sensed.py:270`) gains, after `in_zone`, keyword-only (`_: dataclasses.KW_ONLY`): `id: int = -1`
  (-1 untracked), `vx: float = 0.0`, `vy: float = 0.0` (fw/s, the source's; C11, C17, Q8). `__post_init__` unchanged.
- Guards (unchanged, all pass): `tests/arcade/test_sensed.py` (`test_place_blob`, `test_blob_coordinates_are_clamped`,
  whose :273 equality holds with defaults), `test_actors.py::test_blob_and_audio_scripts`,
  `test_runner.py::test_games_get_only_in_zone_blobs`, `test_lobby.py`, `test_festival.py`. No existing assert
  changes: every caller passes four or five positional fields.
- New (`test_sensed.py`): `test_blob_ids_and_velocities_default_untracked_and_still`;
  `test_blob_new_fields_are_keyword_only` (a sixth positional raises `TypeError`);
  `test_place_blob_keeps_id_and_velocity`.
## G5: Jump (`jump`, spec 8 row 9 as Q99 changed it) (sonnet, worktree)
Rules: a high striker. Stand still ("GET SET"), then "JUMP!": for 5 s the bar shoots up with your nose's rise, and
you may jump as often as you like; the best peak of the window stays as a line; past the bell line the bell rings.
Three windows; the best is the night's. A stranger reads it from the bar and the bell.
- `GameInfo(name="jump", title="JUMP", verb="JUMP", needs={"pose"}, layouts={"128x64"}, players=1,
  exit_gesture=False, kind="score")`, icon a striker column with a bell on top, 2 px strokes.
  `PHASES = ("ready", "play", "result", "over")`, an attempt is `ready`, `play`, `result`, three times, then `over`:
  `ready` (before EVERY attempt, a new baseline each time) until player 1 is seen and still for `SETTLE_SECONDS`
  ("GET SET" at 1x); `play` "JUMP!" at 2x for the whole `JUMP_WINDOW` (it never ends early; the window's best peak
  holds as a line and banks at the window's end); `result` the attempt's peak held `RESULT_SECONDS`; `over` the best
  held. The good bot's round is about 3 x (1.5 + 5 + 2.5) + 3 = 30 s (`round_seconds` 20 to 120).
  `CAPTION_KEYS = ("phase", "attempt", "peak_cm", "best_cm")`.
- The measure: `torso` = hip_mid to shoulder_mid in camera y (keypoints at `MIN_CONF` or more); the baseline = the
  medians of the nose's and the hip_mid's y over `ready`'s last `SETTLE_SECONDS` (at least 5 captures). Still: the
  nose's and the hip_mid's camera y each within `STILL = 0.1` torso of their medians (x is free). `rise` =
  (baseline nose y - nose y) / torso, per capture. A jump counts only while the hip_mid rose by at least `HIP_SHARE`
  of the nose's rise (a nod or a head tilt never counts) and `rise >= MIN_RISE`. `cm = round(rise * TORSO_CM)`.
  `measure_rise(body, base_nose_y, base_hip_y, torso) -> float | None`, a module-level pure function (None: not
  counted). The docstring says: a body whose shoulders leave the zone's top is dropped by the runner, so the zone
  caps the rise (about 47 cm at a body height of 0.6 of the frame, 33 cm at 0.7, 23 cm at 0.8).
- Constants: `ATTEMPTS = 3`, `SETTLE_SECONDS = 1.5`, `JUMP_WINDOW = 5.0`, `RESULT_SECONDS = 2.5`,
  `OVER_SECONDS = 3.0`, `MIN_RISE = 0.15` (torsos), `HIP_SHARE = 0.5`, `STILL = 0.1`, `ACTIVE_RISE = 0.25`,
  `TORSO_CM = 50.0`, `BELL_CM = (28.0, 40.0)` (the bell's height, drawn once per game by the rng),
  `BAR_TOP_CM = 60.0`, `BAR_X, BAR_W = 6, 10`, `BAR_TOP, BAR_BOTTOM = 6, 57`, `FIGURE_H = 56`,
  `HINT_IDLE_SECONDS = 2.0`, `CAMERA_FPS = 10`, `COLUMN_SLACK = 1`, `BAR_COLOR = (255, 160, 0)` (red share 0.61,
  under `flash.RED_SHARE`), `BELL_COLOR = (255, 200, 0)`, `FRAME_COLOR = (0, 200, 255)`.
- Drawn, in this order: the player's figure on its own column across the wall via
  `KeypointHold(capture_grace(CAMERA_FPS))`, `draw_figure` in `PLAYER_COLORS[0]`, `figure_rect(held, (w,
  FIGURE_H))` with the column backlash (it may pass the striker; the striker is drawn over it); the striker (a 1 px
  frame in `FRAME_COLOR`, `BAR_X..BAR_X + BAR_W`, rows `BAR_TOP..BAR_BOTTOM`), the bar filled from the bottom to
  `cm / BAR_TOP_CM` live in `play`, the window's peak held as a 1 px line; the bell a 5x4 block on the bell line;
  in `result` the attempt's `"<cm>"` at 2x right of the bar; last the score, `best_cm` at 2x top right over its
  black box from the game's first tick (0 before an attempt counts). Rows 60 to 63 dark.
- Effects: a bell: `fx.flash((255, 255, 255), 0.15)` (checked) and `fx.pop("DING!", x, y, BELL_COLOR)` at the bell,
  once per attempt; a miss: the number only. `over`: `scores.record(best_cm)` once, when an attempt counted; a new
  best: `fx.banner("NEW BEST")`.
- Movement and scores (C41): a still body never reaches `MIN_RISE` with its hips (real noise moves a nose about 0.06
  torsos), so it banks nothing and records nothing; a window without a jump banks 0. `active`: `rise` changed by
  `ACTIVE_RISE` or more within 1 s, or a counted jump this tick (a still body under real noise is never `active`).
  Hint "JUMP!" again at 1x after `HINT_IDLE_SECONDS` not `active` in `play`.
- debug_state: `phase, attempt, score` (the number drawn: `best_cm`, an int, 0 before a counted attempt), `rise,
  peak_cm, best_cm, bell_cm, rang, heights` (banked cm), `active, hint, player_xy` (head disc centre, None when not
  drawn), `bar_xy` (the bar top's centre).
- Scenarios: `canonical` (2 s empty, walk-up, raise; a walk across the mat in zone x, 0.15 to 0.85 then back to 0.5,
  Copy Me's `SWEEP` (`copyme.py:539-540`), at most 0.1 zone a second (the flash rule's area), the far end inside the
  measured 20 s: range about 0.69; a `Person.jump(at, height=0.15, seconds=0.6)` in each window at the time the
  game opens it (launch + 1.5 s + 9 s x k; a walk is still), body height 0.6), `idle_body` (60 s), `nobody`.
- `jump_feel.toml`: `[fidelity] input = "zone_x"`, `xy = "player_xy"`, `axis = 0`. No budget override.
- Bots (`Move(x=0.5, lift=...)`, I0; the default body, height 0.6): stand in `ready`; in `play`, one arc per window,
  `lift = peak * 4u(1 - u)` over 0.6 s. `good`: `reaction_ticks = 4`, `noise = 0.01`, `peak` reaching
  `BELL_CM[1] + 4` cm (about 0.16 of the frame, the most that stays in the zone; the implementer measures
  `Person()`'s torso first). `lazy`: `reaction_ticks = 10`, `noise = 0.03`, `peak` reaching the middle of `BELL_CM`
  (about 0.12): it wins when the rng's bell is low, about half the seeds. `won(state)`: `phase == "over"` and
  `rang`. Levers: the bots' peaks, `BELL_CM`. Not levers: `ATTEMPTS`, `MIN_RISE`, `HIP_SHARE`.
- Acceptance (`tests/arcade/test_jump.py`, its own tests about 6 s beyond the template's plays):
  - `test_registered_and_declared`; `test_rise_is_nose_over_torso` (a body raised half a torso: rise 0.5, 25 cm);
  - `test_rise_ignores_size_and_place` (`measure_rise` called directly, not through the runner: heights 0.4 and
    0.8, x 0.3 and 0.7 give the same cm within 1);
  - `test_a_nod_never_counts` (the nose up 0.6 torsos, the hips still: nothing banked);
  - `test_a_window_banks_its_best_peak_at_its_end` (two jumps in one window: the higher banks, `play` lasts the
    whole window); `test_the_bar_follows_the_rise_live` (`bar_xy` rows track `rise`);
  - `test_ready_takes_a_new_baseline_before_each_attempt`; `test_the_score_shows_from_the_first_tick` (`score` 0);
  - `test_no_jump_in_the_window_banks_zero`; `test_the_bell_rings_once_and_checks_the_flash` (held 0);
  - `test_three_attempts_then_over_and_done_after_the_hold`; `test_the_best_is_recorded_once`;
  - `test_exit_gesture_is_off` (both hands up 5 s: session on); `test_idle_body_scores_nothing`;
  - `test_a_still_body_under_real_noise_never_counts` (`degrade(**REAL_NOISE)`, 5 seeds: no attempt banked);
  - `test_own_drawing_keeps_the_flash_rule` (canonical: raw area under 0.1, held 0);
    `test_own_drawing_keeps_rows_60_to_63_dark` (as `test_flap.py:307`); the template tests.
- Share: about 30 s (its 60 plays in the pool beside the soaks, its soaks at two sizes, its own tests, its report).
## F1: C55, Copy Me's outline on player 2 (sonnet, worktree)
- `copyme.OUTLINE_COLOR` becomes `(255, 0, 255)` (Q117's default) for both seats: the outline and its head circle
  (`copyme.py:279-280`) and every other use of the constant (the small target in `show`); no other colour changes.
  Magenta's red share is 0.5, under `flash.RED_SHARE = 0.8` (not doubled). `MIN_COLOR_DISTANCE = 150.0`.
- Acceptance: `test_copyme.py::test_the_outline_differs_from_every_figure_colour` (the RGB Euclidean distance from
  `OUTLINE_COLOR` to each `juice.PLAYER_COLORS[seat]` and to `MATCH_COLOR` is at least `MIN_COLOR_DISTANCE`: 282,
  301, 413 today; and in a `duo` frame of `play` no outline pixel is drawn in seat b's colour);
  `test_copyme.py::test_own_drawing_keeps_rows_60_to_63_dark` and `test_swat.py::test_own_drawing_keeps_rows_60_to_
  63_dark` (canonical and duo, as `test_flap.py:307`). `test_copyme.py:178`'s pinned value becomes `(255, 0, 255)`
  (the one named changed assert of F1; `MATCH_COLOR` stays). The feel report for Copy Me meets every budget
  (`flash_area_raw` was 0.0111, `square_flashes` 4 of 6). The operator reads the `duo` sheet again (I2).
## S1: blobs and motion from camera frames (M5's first lane) (opus, worktree)
Core plan Task 15, body lines 4252 to 4396 (`arcade/sources/blobs.py`, `tests/arcade/test_blobs.py`), as its
amendment (lines 620 to 630), spec 5 and 6.1, and C11, C17 change it. Pure functions on numpy frames, tested with
synthetic frames: no camera, no model, so it runs in a worktree. Not wired into `camera.py` or
`pose_mediapipe.py` (iteration 21, with C35's per-input availability); C34's lamp rule waits for GATE A.
- The amendment's light source: value at or above `LIGHT_V = 220` whose 3 px halo (`HALO_PX = 3`) has saturation
  `HALO_S = 0.5` or more; hue from the halo; colour from `cv2.mean` over the component's bounding box with its mask;
  components over `MAX_AREA = 0.005` of the frame rejected. `STATIC_SECONDS = 5.0`: `StaticMask` hides a blob still
  that long (moved under `STATIC_MOVE = 0.01` fw) until it moves. `Blob.in_zone` via `place_blob`.
- C11, C17: `BlobTracker.update(blobs, t) -> tuple[Blob, ...]`: ids by nearest centroid within `MATCH_DIST = 0.1` fw
  between captures, new ids from 1 up, `vx`, `vy` = the matched step over dt; a component whose centroid is not
  finite is dropped before matching.
- `motion_grid(prev_gray, gray, zone, size) -> np.ndarray`: 5x5 blur, divide by the frame median, threshold
  `MOTION_T = 0.25`, cell fill `CELL_FILL = 0.2`; over `SHAKE_SHARE = 0.35` of cells lit returns an empty grid and
  counts a shake; the frame is flipped left to right first (the zone is in mirrored camera space, as the keypoints
  are), then cropped to the zone at the wall's aspect, then downsampled to `size`.
- `FrameFeatures(size=(160, 120), calibration=Calibration())`: `update(frame_bgr, t) -> tuple[tuple[Blob, ...],
  np.ndarray]` (blobs placed, mirrored as `mirror_keypoints` does, the grid); `shakes: int`. The first frame: no
  motion.
- Acceptance (`tests/arcade/test_blobs.py`): the amendment's `test_small_saturated_red_is_a_red_blob`,
  `test_large_lamp_rejected`, `test_white_core_without_saturated_halo_rejected`,
  `test_static_blob_masked_after_5s_unmasked_on_move`, `test_out_of_zone_blob_flagged`,
  `test_uniform_brightness_step_gives_no_motion`, `test_shake_returns_empty_and_counts`,
  `test_motion_zone_crop_maps_to_wall_cell`, perf `test_features_under_3ms_at_160x120` (`thread_time`, marked `perf`);
  the draft's `test_frame_features_first_frame_has_no_motion`, `test_blobs_sorted_by_size_and_capped`,
  `test_no_blobs_in_a_dim_frame`; new `test_blob_ids_persist_and_velocities_follow` (a disc moving 0.02 fw a
  capture keeps its id, vx about 0.02 / dt), `test_a_non_finite_centroid_is_dropped` (the components' centroids
  patched to NaN: no blob), `test_a_blob_lost_and_found_far_away_gets_a_new_id`.
## S2: scenario files and replay sources (opus, worktree; cut first)
Core plan Task 12, body lines 3524 to 3776 (`arcade/sources/scenario.py`, `arcade/sources/replay.py`,
`tests/arcade/test_scenario.py`), as its amendment (line 588), C21 and Review Focus 4 (line 773) change it. No CLI
(`record`, `calibrate`, the source factory are iteration 21); raw replay through `FrameFeatures` and `BodyTracker`
is iteration 21 (S2 does not import S1).
- `.jsonl.gz` (`gzip.open` in text mode), the header record first: `{"kind": "header", "version": 1, "type":
  "sensed" | "raw", "fps", "grid": [128, 64], "script", "cues", "created", "git"}`. Sensed records: `motion` as
  base64 `np.packbits` on the fixed 128x64 grid, resampled on replay; blobs with `id`, `vx`, `vy` (E0). Raw records:
  capture time, raw detections, a 160x120 grey frame as base64 bytes, a 16 kHz WAV with a `struct`-written RIFF
  header (no `wave` module in `arcade/`).
- `encode(s) -> str`, `decode(line, calibration=None) -> Sensed` (C21: keywords; the empty `(0, 0)` grid when none;
  `place()` on every body with the caller's calibration: the header holds none, so `decode(..., calibration)` and
  `open_replay(path, calibration=None)` take it); `ScenarioWriter(path, header)`, `ScenarioReader(path)` with
  `header` and `skipped: int` (a bad line is skipped with one warning, never raised); `ReplayStream`,
  `ReplayCamera.latest() -> CameraResult | None` (the 4-tuple of `camera.py:23`), `ReplayAudio.latest() ->
  tuple[float, Audio] | None` (the runner's shape, `runner.py:236`, stamped as `ScriptedCamera` stamps). The
  draft's tests are adapted to these shapes and to the empty `(0, 0)` grid (not `None`).
- Acceptance (`tests/arcade/test_scenario.py`): the draft's `test_round_trip`, `test_reader_skips_bad_lines`,
  `test_writer_and_open_replay`, `test_replay_of_empty_stream_yields_empty_sensed`; the amendment's
  `test_gz_round_trip_with_header`, `test_header_cues_readable`,
  `test_motion_packed_on_128x64_resampled_to_wall`, `test_raw_record_round_trip`,
  `test_sensed_line_has_only_schema_fields`; new `test_blob_ids_and_velocities_round_trip`,
  `test_decode_places_bodies_with_the_recordings_calibration`.
## Decisions taken
- R is A and B as one; C is not planned (estimate under 420 s). The pool's rows follow the selection, so four
  implementers' `-k` runs pool 60 plays each, not 480. The deadline rises to 180 s (reason in R).
- The rename changes three asserts of one test file, the names only (Q121). Jump's best is a height in cm (`TORSO_CM`
  scale) and its win is the bell (a rng height per game), so the lazy bot's win hangs on the rng as Copy Me's.
- Owner questions Q121 to Q125 (the writer's report), each defaulted. Reviewed: evidence/it20/plan-review.md (B1 to
  B4, N1 to N12 and round 2's three notes are in this text).
- A subset after each merge and the full suite after R and the last merge depart from config.md rule 6, for time
  (it19: 28 minutes of four serial full runs); a break the last run finds is bisected with the failing test alone.
- Cut order if time runs out: S2, then S1, then F1; R, the rename, I0, E0 and G5 are the slice's core. A cut task's
  worktree is kept.
## I1 (orchestrator, after the merges)
- The suite once with `--durations=25`: passes, 3 skips, at most 540 s (expected about 445); the pool line read.
- The guide gains: `Move(lift=...)` (section 4); a measured jump's baseline and the hip check (5).
## I2 (the operator's, in verify)
- `tools/arcade_evidence.py --iteration 20 --games jump,copyme`: `games.md` every budget "yes", no override. Sheets:
  Jump's invite, "GET SET", the bar rising, the bell, the number, the card; Copy Me's `duo` with the magenta outline.
  For the owner's live play: a near or tall player's rise is capped by the zone's top, under the bell's 28 cm.
