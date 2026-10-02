# Iteration 22 (arcade): the suite's room (the soaks in the pool), C57 (Jump's hint), M7b's Paint and Tug
BASE: HEAD after R, E2, I0 and C57 are on main (the orchestrator gives the sha). Not a safety slice: no change to
`arcade/flash.py`, `brightness.py`, `show/display/colorlight.py`, or the order of limiter, governor, push. "Spec" =
`docs/superpowers/specs/2026-09-26-wall-arcade-design.md` (Paint 553, Tug 556, `abandon_seconds` 376, a game's own
buffer 477). Questions Q161 to Q179, defaulted: `docs/superpowers/workflow/evidence/it22/plan-writer-report.md`.
## Global Constraints
- Test command, from the checkout's (or worktree's) root: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
  /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs`. Baseline at 9387346's tree (code as d2f1b63): 2326
  collected, 2323 passed, 3 skipped, 454.57 s; the pool 480 plays in 135.6 s, the join waited 11.0 s. Worktrees show
  a 4th skip (no `models/` there). One command per Bash call; tools as modules; no `cd`; nothing fetched or pushed.
- Memory (the Mac has 8 GB): at most TWO worktree tasks at once. Implementers prefix every test command with
  `ARCADE_POOL_WORKERS=1` (R: no worker process; their plays and soaks run in their one process) and run only their
  own files and the generic ones (`test_all_games.py -k <name>`, `test_oracle.py -k <name>`, `test_game.py`), never
  the whole suite. The orchestrator runs R's check (below), after each merge a subset that names
  `tests/arcade/test_all_games.py` FIRST, then the merged task's test files, `tests/arcade/test_oracle.py` and
  `tests/arcade/test_game.py`, and the FULL suite ONCE, after the last merge (I1). No other full run.
- Touch only your task's files. Test-first. No removed or weakened assert; no seed changed; no band in
  `arcade/feel_budgets.toml` or a `*_feel.toml` loosened; no `*_feel.toml` override without a `reason` line and a
  question in the orchestrator's report. The only changed asserts: `tests/arcade/test_oracle.py:239` (R) and
  `tests/arcade/test_sensed.py:290` (E2). An assert this plan does not name that would have to change: stop, report.
- 128x64 only (Q32, Q33, Q82): `layouts={"128x64"}`; no code, test or tuning for another size. The generic soak at
  96x48 is the engine's: a game sizes its buffers from `reset`'s size and runs there without error.
- Rows 60 to 63 stay dark in everything a game draws, its effects through `fx.render(canvas)` included (Paint and
  Tug call no `fx.flash` and no shake). The frozen protocol is unchanged (`test_protocol_members_are_the_frozen_set`).
- Flash (C24, guide 6): each game's frames keep governor held ticks 0 and raw `concurrent_area` under 0.1; no
  blinking; saturated red counts double. Colours saturated, low channels 0, nothing drawn with every channel under
  140 (`feel.DIM_LEVEL`). Neither new game has a score: no number is drawn; their words are drawn last.
- C41, C42: a still body (and Nobody) paints and pulls nothing. `Sensed`/`Blob`/`Move` new fields by keyword (C21);
  seeds `zlib.crc32`; `time.thread_time` for perf. A file in `pooled.BESIDE_THE_POOL` (every
  `tests/arcade/test_<game>.py`, R) imports no `time`, `subprocess`, `multiprocessing`, `threading`, `signal`,
  `concurrent` or `tools.show_soak` and marks nothing `perf` (R's guard test reads them).
- Bots: `test_bots_rank` (`tests/arcade/test_oracle.py:118`) needs `win_good > win_lazy > win_none` and
  `phases_reached == 1.0` on the 20 report seeds, the template good >= 4 of 5, none 0, lazy < good, a good round's
  median 20 to 120 s. The named levers are starting values, tuned until those hold; no other rule moves.
- Template tests in each new game's file (`test_flap.py`'s shape): `test_debug_state_is_clean`,
  `test_required_scenarios_start_with_an_empty_wall`, `test_canonical_drives_the_lobby_to_<name>`,
  `test_bots_module_is_found`, `test_good_beats_lazy_beats_nobody`, `test_good_round_length_in_band` (both via
  `helpers.played`: they read the pool), `test_feel_file_overrides_have_reasons`, `test_seeded_runs_repeat`,
  `test_own_drawing_keeps_rows_60_to_63_dark` (as `test_flap.py:307`, with `game.fx.render(canvas)` after each
  draw). Each file about 30 s; each report plays through the pool (`REPORT_PLAYS` lists every built game).
- Under load `tests/arcade/test_headless.py::test_tick_budget_with_the_governors_share` (:236-237) and
  `tests/test_show_shot.py::test_strobe_session_is_held` fail and pass on a rerun: rerun them alone before a revert.
- Suite: at most 540 s (Q102). Before: 454.57 s. After R: about 370 s (345 to 400; R's check reads the pool's line,
  not a full run). After the two games (I1, the one full run): about 430 s (395 to 470). Without R the two games
  would read about 545 s, so R comes first and a reverted R cuts Tug (Decisions).
## Lanes and merge order
1. SERIAL, main checkout, the orchestrator (opus): R, committed (R0), then R's check.
2. Batch 1, one worktree task from R0 (`isolation: "worktree"`): C57 (`model: sonnet`), started when R0 is
   committed; it checks `git rev-parse --short HEAD` equals R0 first. It runs beside steps 1's check and 3.
3. SERIAL, main checkout: E2 (one implementer, `model: opus`), committed; then I0 (the orchestrator), committed.
4. Merge C57 with `git -C /Users/trey/dev/codeisart merge --no-ff`, the subset after it. BASE is that merge.
5. Batch 2, two worktree tasks from BASE, ONE message: Paint (`model: sonnet`), Tug (`model: sonnet`); each checks
   HEAD equals BASE first. No cross-imports. Merge Paint, then Tug, the subset after each; a merge that breaks it
   is undone with `git revert -m 1` and sent back once. Then I1 (the full suite once), then I2.
Files by task (no file under two tasks):
- R: `tests/arcade/pooled.py`, `tests/conftest.py`, `tests/arcade/helpers.py` (one line), `tests/arcade/
  test_all_games.py`, `tests/arcade/test_oracle.py`. E2: `arcade/sensed.py`, `tests/arcade/test_sensed.py`.
- I0: `arcade/bots.py`, `tests/arcade/test_bots.py`. C57: `arcade/games/jump.py`, `tests/arcade/test_jump.py`.
- Paint: `arcade/games/paint.py`, `paint_bots.py`, `paint_feel.toml`, `tests/arcade/test_paint.py` (all new).
- Tug: `arcade/games/tug.py`, `tug_bots.py`, `tug_feel.toml`, `tests/arcade/test_tug.py` (all new).
- I1: `.claude/skills/arcade-game-authoring/SKILL.md`.
Shared files, the orchestrator's alone: `tests/arcade/helpers.py` gains one line after `PLAYS` (:40), `SOAKS:
dict[tuple[str, str, int, str], object] = {}` with a one-line comment (R); `tests/conftest.py` R's hooks;
`arcade/bots.py` I0. Not edited: `arcade/games/__init__.py` (`"paint"`, `"tug"` are in `MENU_ORDER`, :16),
`feel_budgets.toml`, `arcade.toml`, `pyproject.toml`, `tests/arcade/conftest.py`, `runner.py`, `headless.py`,
`game.py`, `canvas.py`, `juice.py`, `input.py`, `jump_bots.py`, `jump_feel.toml`, every safety file.
## R: the soaks in the pool, the safe tests beside it (orchestrator, opus, main checkout)
Why (it21's final durations): the main process spends 117.2 s on the 160 soak runs while 4 workers play 480 plays
in 135.6 s, then about 314 s after the join. The soaks alone in the pool would leave the main process idle at the
join; so (C) the soaks become pool jobs and (B) the main process runs the safe tests meanwhile. Still four workers
(Q97); plain subprocesses, as it18.
- `pooled.py`:
  - `pool_workers(environ: Mapping[str, str]) -> int`: `ARCADE_POOL_WORKERS` as an int, 4 when absent; a value that
    is not an integer of 1 or more raises `ValueError` naming the variable. `PLAY_WORKERS = pool_workers(os.environ)`.
    With 1, `start` launches no worker and warns nothing (`n < 2`, `workers < 2`: today's no-worker pool).
  - `WORKER_TIMEOUT_S = 270.0` (was 180, Q162): the pool grows to about 165 s with the soaks, 205 to 225 s with
    Paint and Tug; 270 keeps today's third over the expected. A hang now costs about 11 minutes.
  - `SoakKey = tuple[str, str, int, str]` (game name, layout, seed index, mix): plain data across the boundary.
  - `soak_job(key: SoakKey, font) -> Soak | None`: `measure_soak(get_game(name), layout, i, mix, font)`, imported from
    `tests.arcade.test_all_games` inside the function; None when its `error` is not None (an exception does not
    cross the boundary: the main process makes that soak again and its test shows the traceback).
  - `start(reports, plays: dict = PLAYS, workers: int = PLAY_WORKERS, soaks: Sequence[SoakKey] = (), soaked: dict =
    SOAKS) -> Pool`: the plays not in `plays` and the soaks not in `soaked`, dealt round robin as one list (plays
    first); `n = min(workers, cores, len(todo))` as today. Worker k's `jobs-k.json` is `{"plays": [...], "soaks":
    [...]}`; its pickle `{"arcade": ..., "plays": [...], "soaks": [...]}`; `_read` checks both counts and the root.
  - `Pool` gains `soak_keys: frozenset[SoakKey]` (asked) and `soak_stored: set[SoakKey] | None`; `join()` stores
    each soak that is not None in `soaked` and still returns the play keys (`pooled_plays` is unchanged).
  - `main`: the plays, then the soaks with `Font.load(ROOT / "fonts" / "5x7.bin")` (the `font5x7` fixture's file).
  - `BESIDE_THE_POOL`: `tests/arcade/test_<n>.py` for n in actors, brightness, calibrate, calibration, config, feel,
    figure, first_playable, game, input, lobby, mirror, pattern, privacy, runner, scores, sensed, stats, and for every
    name in `MENU_ORDER`. Not `test_all_games`, `test_oracle`, `test_bots` (:246 stays), `test_headless`, nor
    any file with a process, a thread or a clock. `READS_THE_POOL = ("test_good_beats_lazy_beats_nobody",
    "test_good_round_length_in_band")`.
  - `beside_the_pool(nodeid: str, perf: bool) -> bool`: the file is in `BESIDE_THE_POOL`, not `perf`, and the test's
    name (the nodeid's after `::`, before `[`) is not in `READS_THE_POOL`.
  - `beside_first(items) -> list`: a stable partition, the beside items first, then the rest, each in its order.
  - `soaks_for(items, seeds: int, mixes: Sequence[str]) -> list[SoakKey]`: for each item that needs `pooled_soaks`,
    its `game_cls` and `layout` parameters, `i` in `range(seeds)`, each mix; no duplicate, first-seen order.
- `tests/conftest.py`:
  - `pytest_collection_modifyitems(session, config, items)`, `@pytest.hookimpl(trylast=True)` (after `-k` and
    `-m`): nothing under `--collect-only`; when an item needs `pooled_plays` or `pooled_soaks`,
    `items[:] = pooled.beside_first(items)`. So a game file's own tests run while the workers play, and its two
    readers, the soaks' tests, the reports and everything timed run after the join.
  - `pytest_collection_finish`: starts the pool when an item needs either fixture: rows from the first
    `pooled_plays` item's `REPORT_PLAYS` (else `[]`), soaks `soaks_for(items, m.SEEDS, m.MIXES)` of the first
    `pooled_soaks` item's module (else `()`). `pytest_runtest_setup` and `pytest_sessionfinish` unchanged.
  - The summary line: `pooled: <n> plays, <m> soaks, <k> workers, <elapsed> s, the join waited <w> s`.
- `test_all_games.py`: `MIXES = ("random_mix", "hostile_mix")` (`soaks()` iterates it, today's order);
  `measure_soak(game_cls, layout, i, mix, font) -> Soak` is today's `soak` body (:156-170) uncached; `soak(...)`
  (still `lru_cache`d) returns `SOAKS[(name, layout, i, mix)]` when there, else `measure_soak(...)`. Module fixture
  `pooled_soaks() -> set[SoakKey]`: joins `pooled.RUNNING` when one runs, returns its `soak_stored` (else `set()`).
  `test_every_game_soaks_without_error` and `test_every_game_keeps_the_flash_rule_in_the_soak` take it; their
  asserts and the strobe run (:198-202, in process, after the join) are unchanged.
- Acceptance. Changed: `test_oracle.py:239` becomes `assert not pooled.beside_the_pool(soak, perf=False)` (the soak
  test reads the pool now); :240 to :246 hold; every other test of `test_oracle.py` passes unchanged
  (`test_stop_kills_a_running_pool_and_leaves_no_child` and `test_join_twice_waits_once` among them). New there
  (its `_Item` stand-in gains `nodeid` and `get_closest_marker`):
  - `test_the_beside_files_start_no_process_and_read_no_clock` (`ast`: every existing file of `BESIDE_THE_POOL`
    imports none of the modules the Global Constraints name and has no `perf` mark; at least 26 files read);
  - `test_the_readers_of_the_pool_run_after_the_join` (every `test_*` function of a beside file that calls `played`
    or `bot_play` or names `PLAYS` or `SOAKS` is in `READS_THE_POOL`; `beside_the_pool` is False for
    `tests/arcade/test_jump.py::test_good_round_length_in_band`, True for `::test_debug_state_is_clean`);
  - `test_the_beside_items_run_first` (stand-ins: a perf item, a reader, a soak, two beside ones: the beside ones
    first in their order, the rest in theirs); `test_the_soaks_follow_the_selected_tests` (two parametrized
    stand-ins, `seeds=2`: 8 keys, no duplicate); `test_the_worker_count_reads_its_variable` (`{}` 4, `"1"` 1,
    `"0"` and `"x"` raise).
  New in `test_all_games.py`: `test_pooled_soaks_are_the_in_process_soaks` (each game at 128x64, `random_mix`,
  `i = SEEDS - 1`: the key is in `pooled_soaks`; every `Soak` field equals `measure_soak`'s; about +6 s);
  `test_the_pool_made_every_soak` (when the session started a pool: `soak_keys <= SOAKS.keys()`, every asked key
  not stored before is in `soak_stored`, `children_of_this_process() == 0`).
- R's check (no full run): one subset run, `--durations=25`, saved as `evidence/it22/r-subset.txt`:
  `tests/arcade/test_all_games.py tests/arcade/test_oracle.py tests/arcade/test_game.py` and every file of
  `BESIDE_THE_POOL`: passes; the line reads 480 plays, 160 soaks, 4 workers, about 165 s (flag over 200 s);
  `--collect-only -q` prints no `pooled:` line. R fails it: one fix round; still failing, `git revert` R, keep
  `WORKER_TIMEOUT_S = 270.0` and `pool_workers` alone, cut Tug, land the rest, report the time.
## E2: a blob's zone position (one implementer, opus, main checkout)
- `Blob` (`arcade/sensed.py:271-289`) gains, after `vy` (:284), keyword-only: `zone_x: float = field(default=0.5,
  compare=False)` and `zone_y` the same: the blob's place across and down the calibrated zone, 0..1, clamped, as
  `Body.zone_x`/`zone_y`. Not in equality or hash (they follow from x, y and the calibration; Q176).
- `place_blob` (:327-330) sets `in_zone`, `zone_x = clamp01((x - x0) / (x1 - x0))`, `zone_y` likewise, as `place`
  (:313-324) does for a body's anchor. Nothing else changes; `scenario.py` writes no zone field (it places on read).
- Changed: `tests/arcade/test_sensed.py:290` becomes `== ["id", "vx", "vy", "zone_x", "zone_y"]` (:289 holds).
  Unchanged: `test_place_blob`, `test_place_blob_keeps_id_and_velocity`, `tests/arcade/test_scenario.py:161` (decoded
  blobs are placed: equal by `compare=False`), `test_runner.py::test_games_get_only_in_zone_blobs`.
- New (`test_sensed.py`): `test_place_blob_sets_zone_x_and_zone_y` (the default zone (0.2, 0.2, 0.8, 0.8): a blob at
  (0.5, 0.5) gives 0.5, 0.5; at (0.35, 0.65) gives 0.25, 0.75; at (0.05, 0.9) gives 0.0, 1.0);
  `test_blob_zone_fields_do_not_change_equality` (two blobs differing only there are equal, same hash).
## I0: a bot can hold a light and wave (orchestrator, opus, main checkout)
- `Move` (`arcade/bots.py:40-55`) gains, last, `light: tuple[int, int, int] | None = None`, `wave: float = 0.0`.
- `_sensed` (:131-154): with `light`, one blob of `LIGHT_SIZE`, that colour and id 1 at the Move hand's wrist
  keypoint (the right one for `"both"`), after the pose and wrist are set, through `place_blob`; with `wave > 0`,
  the grid cells whose column centres lie within `wave / 2` of `move.x` (after noise; the grid is the zone's crop,
  `arcade/sources/blobs.py:103-106`) and whose row centres lie in `WAVE_ROWS` (shares of its height) are True.
  `LIGHT_SIZE = 0.03`, `WAVE_ROWS = (0.2, 0.9)`. Neither draws noise, so every existing play repeats.
- Acceptance (`tests/arcade/test_bots.py`): `test_move_light_is_a_placed_blob_at_the_wrist` (one blob, id 1, at
  the right wrist keypoint, `in_zone`, `zone_x`/`zone_y` from `place_blob`); `test_move_wave_lights_its_band`
  (`Move(x=0.25, wave=0.1)`: columns 26 to 37 lit on rows 13 to 57, nothing else);
  `test_move_without_light_or_wave_is_todays_record` (`Move()` and `Move(light=None, wave=0.0)`: equal bodies,
  `blobs == ()`, the grid all False, the same rng draws). Every existing test of `test_bots.py` passes unchanged.
## C57: Jump's hint waits in every window; the number clears the figure (sonnet, worktree, batch 1)
- `_begin` (`arcade/games/jump.py:157-166`): `"play"` sets `self._idle = 0.0` and `self._hint = False`, so the idle
  clock starts at each window's open (it ran through `result` and `ready`: the hint led windows 2 and 3, 15.0 s and
  24.0 s of the canonical). `_update_hint` (:277-282) is unchanged. The first task in Jump's files.
- With it (Q175), costing no band: the result's number (:306-311) takes its x on `result`'s first tick:
  `BAR_X + BAR_W + 4` when its box (x - 1 to x + width, rows 23 to 23 + 2 * CELL_H + 1) meets no column of the
  figure's rect (`self._view()[1]`, :289-294; no figure: that x), else the rect's right edge + `NUMBER_GAP = 2`
  when the box ends by column 127, else the rect's x - `NUMBER_GAP` - width (`peak_cm` is not capped: 3 digits fit).
- Unchanged and passing: `test_jump.py:418` (play opens at 1.5 s, the hint at 3.5 s, under 3.8), :502 (the number at
  2x is found), `test_the_hint_replaces_the_prompt` (the jump at 5.5 s is after the hint at 3.5 s),
  `test_the_pop_is_clear_of_the_prompt`, `test_the_prompt_never_meets_the_figure_rect`, the rows tests.
- New: `test_the_hint_waits_in_every_window` (canonical and `idle_body`: on each attempt's first `play` tick
  `hint` is False and the band reads `PLAY_TEXT`; in `idle_body` the hint first shows `HINT_IDLE_SECONDS` (within one
  tick) after each window opens); `test_the_result_number_never_meets_the_figure_rect` (zone x 0.0, 0.15, 0.5,
  0.85, a still body that jumps once: on `result`'s first and last tick the number is found at 2x and none of its
  pixels lies in the rect; at 0.85 its x is `BAR_X + BAR_W + 4`).
- `test_oracle.py -k jump` passes, every budget "yes", no band moved. The operator reads the sheet (I2).
## Paint (`paint`, spec line 553) (sonnet, worktree, batch 2)
Rules: lights paint. Each in-zone light leaves a stroke in its colour; a lifted wrist paints in its seat's colour
when nobody has a light; strokes fade over 20 s; after 60 s the picture freezes in a white frame for 5 s.
- `GameInfo(name="paint", title="PAINT", verb="PAINT", needs={"pose", "blobs"}, layouts={"128x64"}, players=2,
  exit_gesture=False, kind="toy", abandon_seconds=45.0)` (Q163, Q167); icon a wavy stroke, 2 px. `PHASES =
  ("paint", "gallery")`; `CAPTION_KEYS = ("phase", "painted", "lights")`. No score.
- The paper, its own buffer: `paper` (h - 4, w, 3) float at full colour and `painted_at` (h - 4, w) (NaN unpainted);
  `draw` blits the faded picture at (0, 0) (`canvas.blit_rgb`, black transparent), so the bottom 4 rows are never
  painted. A pixel `age` seconds old shows its colour x (1 - (1 - FADE_FLOOR) x age / FADE_SECONDS) while age <
  FADE_SECONDS, then black (Q165); painting it again sets colour and time.
- `stamp_segment(paper, painted_at, a, b, color, brush_px, t) -> int` (module level, pure): discs of diameter
  `brush_px` every pixel from a to b (wall px), clipped to the paper; returns the pixels set.
- Lights (Q168; the runner gives in-zone blobs only): at `(zone_x * (w - 1), zone_y * (h - 5))` (E2). A light with
  `id >= 0` draws a segment from its last point when the step is at most `MAX_SEGMENT_PX`, else starts a stroke; a
  stroke unseen for `LOST_SECONDS` ends; a new id first seen within `LINK_PX` of a stroke ended under
  `LOST_SECONDS` ago continues it. `id == -1` (untracked) stamps a dot per capture. Colour: each channel clamped to
  0..255 (Q158), scaled so the largest is 255; white when its saturation is under `WHITE_BELOW_S` or it is black.
- Wrists (Q164), only when no light was seen for `LIGHT_QUIET_SECONDS`: each seated body (`sensed.player`,
  `player2`) whose `cursor` v is under `PEN_V` paints in `PLAYER_COLORS[seat]` at x = clamp01(zone_x + `ARM_SPAN` x
  (u - 0.5)) x (w - 1), y = v / `PEN_V` x (h - 5); segments by seat as a light's. A resting wrist lifts the brush.
- Brushes move on fresh captures only (`sensed.camera_fresh`); a white 1 px ring of radius `RING_R` at each brush
  that painted on the last capture. `gallery` at `PAINT_SECONDS`: nothing paints, the fade stops, a 1 px
  `FRAME_COLOR` frame around the paper; `done()` after `GALLERY_SECONDS`.
- Constants: `PAINT_SECONDS = 60.0`, `GALLERY_SECONDS = 5.0`, `FADE_SECONDS = 20.0`, `FADE_FLOOR = 0.56` (255 x 0.56
  = 143: no channel set falls under 140), `FREE_ROWS = 4`, `BRUSH_PX = (2, 3)` (one drawn per game by the rng; Q166),
  `RING_R = 3`, `MAX_SEGMENT_PX = 32`, `LOST_SECONDS = 0.3`, `LINK_PX = 12`, `LIGHT_QUIET_SECONDS = 1.0`,
  `PEN_V = 0.8`, `ARM_SPAN = 0.5`, `WHITE_BELOW_S = 0.25`, `WIN_PAINTED = 0.2`, `FRAME_COLOR = (255, 255, 255)`.
- debug_state: `phase, painted` (share of paper pixels lit, 3 decimals), `strokes, lights, brush_xy` (player 1's
  wrist brush in wall px, None when it did not paint on the last capture), `light_xy` (the first light's, or
  None), `active` (a brush painted on this capture, or a light is seen), `brush_px`.
- Scenarios: `canonical` (2 s empty, walk-up, the raise at 4.5 s; from 6 s the right wrist sweeps v 0.1 to 0.7 and
  back about once a second (`Person.wrist`) while the body walks zone x 0.3 to 0.7 inside the measured 20 s; from
  13 s a light, `moving_blob` given `id=1`, crosses the zone; about 72 s), `idle_body` (60 s), `nobody`, `duo` (two
  bodies, both seats' wrists sweeping).
- `paint_feel.toml`: `[fidelity] input = "cursor_y"`, `xy = "brush_xy"`, `axis = 1` (probes where the brush moved;
  a toy has no fidelity budget). No budget override.
- Bots (I0's `Move`): `good`: a light `(0, 255, 0)`, x sweeping 0.1 to 0.9 and `wrist_y` 0.1 to 0.7 in a zigzag,
  `reaction_ticks = 4`, `noise = 0.01`; `lazy`: no light, `wrist_y` about 0.6, x drifting 0.1 around 0.5,
  `reaction_ticks = 10`, `noise = 0.03`. `won(state)`: `phase == "gallery"` and `painted >= WIN_PAINTED`. Levers:
  the bots' sweeps, `WIN_PAINTED` (Q169). Not levers: `FADE_SECONDS`, `PAINT_SECONDS`, `PEN_V`.
- Acceptance (`tests/arcade/test_paint.py`): `test_registered_and_declared`;
  `test_a_tracked_light_draws_segments_in_its_colour`; `test_a_step_over_max_segment_starts_a_new_stroke`;
  `test_a_new_id_near_a_lost_stroke_continues_it`; `test_an_untracked_light_paints_dots_only`;
  `test_a_light_colour_is_clamped_and_saturated` (1e308, -5, grey: no exception, a 255 channel, white);
  `test_a_lifted_wrist_paints_when_nobody_has_a_light`; `test_a_light_stops_the_wrists`;
  `test_two_seats_paint_in_their_colours`; `test_trails_fade_to_the_floor_then_go_off` (age 0 full, 19.9 s every
  lit channel 143 or more, 20 s black); `test_the_gallery_freezes_the_paper_then_done`;
  `test_idle_body_paints_nothing`; `test_exit_gesture_is_off` (both hands up 5 s: session on);
  `test_a_still_body_under_real_noise_paints_nothing` and `test_wrists_paint_under_real_noise` (both
  `degrade(**REAL_NOISE)` over body ids 1, 2 and 7: nothing painted; strokes in the seat's colour, rows dark);
  `test_a_degraded_light_draws_one_stroke` (degraded for blobs: `degrade(**REAL_NOISE)`, plus, seeded in the test,
  2 of every 10 captures without the light and a new id after each gap: one stroke, no break);
  `test_own_drawing_keeps_the_flash_rule` (canonical, `duo`: raw area under 0.1, held 0);
  `test_own_drawing_keeps_rows_60_to_63_dark` (canonical, `idle_body`, `duo`); the template tests.
## Tug (`tug`, spec line 556) (sonnet, worktree, batch 2)
Rules: the room is the rope. The camera's left and right halves pull a knot; whichever half moves more pulls it
toward its side; a knot past a goal line wins; no pose needed (only the launch's raised hand).
- `GameInfo(name="tug", title="TUG", verb="WAVE", needs={"motion"}, layouts={"128x64"}, players=1,
  exit_gesture=False, kind="toy", abandon_seconds=70.0)` (Q173: motion is no presence evidence, `runner.py:434`, so
  a round outlasts a room the pose model cannot see); icon a rope with a knot, 2 px. `PHASES = ("ready", "pull",
  "over")`; `CAPTION_KEYS = ("phase", "knot", "pull")`. No score.
- `ready`: `READY_SECONDS`, "WAVE!" at 2x. `pull`: `sl`, `sr` = the lit share of the grid's left and right halves
  (`sensed.motion`, all rows), each smoothed over `SMOOTH_SECONDS`; `pull = sl - sr` when `abs(sl - sr) >=
  DEAD_SHARE`, else 0; the knot (-1 left .. 1 right) moves by `-PULL_SPEED * pull * dt` (Q170). Past `-goal` or
  `goal` that side wins (`crossed`); at `ROUND_SECONDS` the side the knot leans to by `LEAN` or more wins, else a
  draw (Q171). `over`: `OVER_SECONDS` with "LEFT WINS", "RIGHT WINS" or "DRAW" at 2x (Q172); `done()` after it.
- Drawn in this order, rows 0 to h - 5 only: the echo, each grid cell lit for `ECHO_HOLD_SECONDS` after its last
  motion (Q174: a cell turns on and off at most once per 0.5 s), left half `PLAYER_COLORS[0]`, right half
  `PLAYER_COLORS[1]`; the rope, rows `ROPE_Y` and `ROPE_Y + 1` in white; the goal lines, 1 px columns at the knot's
  `-goal` and `goal` in the halves' colours; the knot, a `KNOT_PX` white square at x = 63.5 + knot x `KNOT_SPAN`;
  the words last, over a black box 1 px wider than the text.
- Constants: `READY_SECONDS = 3.0`, `ROUND_SECONDS = 60.0`, `OVER_SECONDS = 4.0`, `PULL_SPEED = 0.25`,
  `DEAD_SHARE = 0.02`, `SMOOTH_SECONDS = 0.5`, `GOAL = (0.6, 1.0)` (one drawn per game by the rng), `LEAN = 0.1`,
  `ECHO_HOLD_SECONDS = 0.5`, `ACTIVE_SHARE = 0.01`, `ROPE_Y = 29`, `KNOT_PX = 5`, `KNOT_SPAN = 60`, `FREE_ROWS = 4`.
- debug_state: `phase, knot` (3 decimals), `goal, left, right` (the smoothed shares), `pull, winner` ("left",
  "right", "draw" or None), `crossed, active` (the grid's lit share at least `ACTIVE_SHARE`), `knot_xy`.
- Degraded, for motion: `degrade(**REAL_NOISE)` (each capture's grid held 3 ticks, 0.15 s late); `shake(start,
  seconds)` (empty grids, all False in the game); a speckle seeded in the test (each cell lit with probability
  0.02 per capture, both halves).
- Scenarios: `canonical` (2 s empty, walk-up, the raise at 4.5 s; from the launch the right wrist sweeps (the
  cursor moves) and a 32-column band on grid rows 13 to 57 slides one column a tick between columns 0 and 63; the
  left wins; about 45 s), `idle_body` (60 s), `nobody`, `crowd` (both halves moving, the left more).
- `tug_feel.toml`: a comment only (no `[fidelity]`: Tug reads no body; no override).
- Bots (`Move(x, wave)`, I0): `good`: x 0.25, `wave = 0.1`, `reaction_ticks = 4`, `noise = 0.01` (about 12.8 of
  64 columns, the left half 0.14 lit: a goal in 17 to 29 s, a round about 30 s); `lazy`: x 0.25, `wave = 0.04`
  (about 5.1 columns, 0.056: the knot reaches about 0.83 in 60 s, past the goal in about 11 of 20 seeds),
  `reaction_ticks = 10`, `noise = 0.03`. `won(state)`:
  `phase == "over"`, `winner == "left"` and `crossed`. Levers: the bots' `wave`, `GOAL`. Not: `PULL_SPEED`, `LEAN`.
- Acceptance (`tests/arcade/test_tug.py`): `test_registered_and_declared`; `test_the_busier_half_pulls_the_knot`
  (left lit: the knot goes left; mirrored: right); `test_a_still_room_pulls_nothing` (equal halves, and a difference
  under `DEAD_SHARE`: the knot stays); `test_crossing_a_goal_ends_the_round_for_that_side`;
  `test_the_cap_ends_a_round_leaning_or_drawn`; `test_the_goal_is_drawn_once_per_game_by_the_rng`;
  `test_the_echo_holds_each_cell_half_a_second` (a one-tick cell lit `ECHO_HOLD_SECONDS`, then dark; a cell lit
  every other tick stays lit); `test_the_echo_takes_its_halfs_colour`; `test_idle_body_pulls_nothing` (a draw,
  `won` False); `test_no_pose_is_needed` (the launcher leaves at 6 s, the band moves on: the round reaches `over`);
  `test_exit_gesture_is_off`; `test_a_degraded_crowd_still_pulls` (`degrade(**REAL_NOISE)` on the canonical: the
  left wins); `test_a_shake_holds_the_knot` (a 2 s `shake`: the knot moves under 0.02, no exception);
  `test_speckle_alone_never_wins` (5 seeds: no crossing, `abs(knot) < LEAN` at the cap);
  `test_own_drawing_keeps_the_flash_rule` (canonical and a whole-grid strobe: raw area under 0.1, held 0);
  `test_own_drawing_keeps_rows_60_to_63_dark` (canonical, `idle_body`, `crowd`); the template tests.
## Decisions taken
- R is C and B as one: the soaks are pool jobs and the safe files run beside it. Four workers (Q97, Q161); an
  implementer's run starts none (`ARCADE_POOL_WORKERS=1`), so two worktree tasks and the orchestrator's subset never
  run more than one pool. The beside order is a stable partition: a file's own tests keep their order (Q177).
- No full run after R (the memory rule): R's check reads the pool's line on a subset; I1 is the one full run.
  `Blob.zone_x`/`zone_y` are E2's (an engine file, serial); `Move.light` and `Move.wave` are I0's (a shared file).
- Neither new game draws a score; both are `kind = "toy"` (Q178): no fidelity, win or score bands; `test_bots_rank`
  still ranks their bots, whose wins hang on the rng's brush and goal as Jump's on its bell (it20).
- Jump's bell flash lights rows 60 to 63 (`fx.flash` at `jump.py:240`, `juice.py:234-237`): not changed here (Q179).
- Cut order if time runs out (about 2 h 50 min of wall time, the report): Tug, then C57's number (the hint stays),
  then Paint. R, E2, I0 and C57's hint are the core. A cut task's worktree is kept.
## I1 (orchestrator, after the last merge)
- The suite once with `--durations=25`, saved as `evidence/it22/final-durations.txt`: passes, 3 skips, at most 540 s
  (expected about 430); the `pooled:` line reads 600 plays and 200 soaks; its elapsed over 230 s is flagged for
  it23's plan. A break is bisected with the failing test alone, never with another full run.
- The guide gains: `Move(light=..., wave=...)` (section 4); `Blob.zone_x`/`zone_y`; a game's test file runs beside
  the pool (no clock or process import; its readers run after the join); `ARCADE_POOL_WORKERS=1` for implementers.
## I2 (the operator's, in verify)
- `tools/arcade_evidence.py --iteration 22 --games paint,tug,jump`: `games.md` every budget "yes", no override.
  Sheets: Paint's strokes, a light's stroke, the fade, the gallery frame, `duo`; Tug's "WAVE!", the echo, the rope,
  the knot, the goal lines, "LEFT WINS"; Jump's windows 2 and 3 opening on "JUMP!" and the number clear of the
  figure at the mat's left end. C57 is closed when the sheet reads so.
