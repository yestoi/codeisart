# Iteration 22: the plan writer's report

Plan: `docs/superpowers/plans/2026-10-02-it22-suite-room-paint-tug.md`, 298 lines, the longest 118 characters
(line 24). Written by reading only: no test was run, nothing committed, no Pi, no network.

## What I read

- `tests/arcade/pooled.py` whole (PLAY_WORKERS 4 at :38, WORKER_TIMEOUT_S 180.0 at :39, BESIDE_THE_POOL at :42,
  `RUNNING` :181, `start` :184, `n = min(...)` :198, `beside_the_pool` :229, `rows_for` :234, `main` :253).
- `tests/conftest.py` (the hooks: `pytest_collection_finish` :21, `pytest_runtest_setup` :33,
  `pytest_sessionfinish` :43, `pytest_terminal_summary` :50; no `pytest_collection_modifyitems` anywhere in
  `tests/`, and `pyproject.toml` loads no ordering plugin).
- `tests/arcade/test_all_games.py` (`soak` :156-170, lru_cached; the strobe run :198-202), `test_oracle.py`
  (`test_bots_rank` :118-124, `test_the_pool_runs_beside_the_soaks_only` :237-246, `_Item` :249,
  `test_the_rows_follow_the_selected_tests` :258), `helpers.py` (`PLAYS` :40), `test_sensed.py` (:289-290),
  `test_scenario.py` (:159-162), `test_jump.py` (:417-418, :500-502, the rows test :463-473), `test_flap.py`
  (:306-307, :469, :506-511), `test_pong.py` (its own `bot_play` reading `oracle.PLAYS`, :645-664).
- `arcade/sensed.py` (`Blob` :271-289, `place` :313-324, `place_blob` :327-330, the grid :333-365),
  `arcade/bots.py` (`Move` :40-55, `_sensed` :131-154, the noise :184-199), `arcade/games/jump.py` (constants
  :42-80, `_begin` :157-166, `_update_hint` :277-282, `_view` :289-294, the result's number :306-311, the bell's
  `fx.flash` :240), `arcade/juice.py` (`PLAYER_COLORS` :58, the flash :234-237), `arcade/runner.py` (presence
  :434, `_moving` :451-459: in-zone moving blobs only), `arcade/sources/blobs.py` (`motion_grid` :91-110: mirrored,
  cropped to the zone), `arcade/sources/actors.py` (`wrist` :119, `moving_blob` :199, `shake` :400, `degrade` :419,
  `REAL_NOISE` :466), `arcade/sources/scripted.py`, `arcade/feel.py` (`DIM_LEVEL` :42), `arcade/games/__init__.py`
  (`MENU_ORDER` :16 already holds "paint" and "tug").
- The spec (Paint's row :553, Tug's :556, `abandon_seconds` :376, a game's own buffer :477), `roadmap.md` (C57 at
  :129), `decisions.md` (Q32, Q33, Q82, Q97, Q102, Q131, Q158), `journal.md`, the it20 and it21 plans,
  `evidence/it21/final-durations.txt`.

## What I measured by reading

- it21's final run: 2323 passed, 3 skipped, 454.57 s; `pooled: 480 plays, 4 workers, 135.6 s, the join waited
  11.0 s` (the 11.00 s setup of `test_every_game_fits_the_tick_budget[copyme-128x64]` is that wait).
- The 16 soak tests (8 games x 2 layouts) in the slowest 25 sum to 117.15 s: 160 soak runs (8 x 2 x 5 seeds x 2
  mixes), about 0.73 s each, all in the main process beside the workers. The workers spent about 542
  worker-seconds on 480 plays (1.13 s a play).
- Every one of the 26 files R puts beside the pool (18 named plus the 8 built games) imports no `time`,
  `subprocess`, `multiprocessing`, `threading`, `signal`, `concurrent` or `tools.show_soak` and marks nothing
  `perf` today (grep of each file). In those files only `test_good_beats_lazy_beats_nobody` and
  `test_good_round_length_in_band` call `played`/`bot_play` or name `PLAYS`.
- Bot wave arithmetic (the grid is 128 x 64, each cell one wall pixel; the grid is the zone's crop, so `Move.x` is
  its column share): `wave = 0.1` at x 0.25 lights column centres in 0.2..0.3, columns 26 to 37 (12) without noise,
  12.8 on average with noise; rows with centres in 0.2..0.9 are 13 to 57 (45). The left half's lit share is
  12.8 x 45 / 4096 = 0.14; at `PULL_SPEED = 0.25` the knot moves 0.035 a second: a goal of 0.6 to 1.0 in 17 to
  29 s. `wave = 0.04`: 5.1 columns, 0.056, 0.014 a second, about 0.83 in 60 s: past the goal in about 58% of
  seeds (11 of 20). So good about 20 of 20, lazy about 11, none 0.

## Estimates

- After R (the subset R's check runs and the full suite would show): the pool does 542 + 117 = 659
  worker-seconds over 4 workers, about 165 s. The main process runs the beside set (about 120 s, today's after-join
  time of those files) and waits about 45 s at the join; after the join about 205 s (today's 314 s less the beside
  files, plus the soak tests now reading stored soaks). Total about 370 s (345 to 400).
- After Paint and Tug: 120 more plays (135 worker-s) and 40 more soaks (29 worker-s): the pool about 206 s
  (205 to 225); the beside set grows by the two game files (about 60 s), the join wait shrinks to about 25 s;
  after the join about 225 s. Total about 430 s (395 to 470).
- Without R: 454.57 + 29 s of soaks + 60 s of game files + about 20 s of generic tests, about 545 s: over Q102's
  540. So R lands first, and a reverted R cuts Tug.
- Wall time: R 45 min plus its check 5; E2 20 and I0 15 (C57 runs meanwhile); C57's merge and subset 8; batch 2
  about 60; two merges and subsets 16; I1 10. About 2 h 50 min to 3 h: OVER the two hours. The cut order (the
  plan's Decisions): Tug, then C57's number (the hint stays), then Paint. R, E2, I0 and C57's hint are the core.

## Choices

- R is the two halves together: the soaks become pool jobs (C) and the safe test files run in the main process
  while the workers play (B). Either alone barely helps: C alone leaves the main process idle at the join, B alone
  leaves 117 s of soaks in the main process.
- Ordering is a `trylast` `pytest_collection_modifyitems` stable partition, so `-k`/`-m` selection happens first
  and a file's own tests keep their order. The two pool readers and every perf item stay after the join.
- A static guard (`test_the_beside_files_start_no_process_and_read_no_clock`) instead of trusting the list.
- `ARCADE_POOL_WORKERS=1` lets implementers run their own files with no worker processes, so two worktree
  tasks plus the orchestrator's subset never run two pools.
- `soak_job` returns None on an error so an exception never crosses the process boundary; the main process
  remakes that soak and its test shows the real traceback.
- E2 puts the zone position on `Blob` (compare=False) instead of having Paint redo `place`'s arithmetic: one
  owner of the zone mapping, and decoded scenario blobs stay equal.
- I0 extends `Move` with a light and a wave, drawing no noise, so every existing seeded play repeats exactly.
- C57 resets `_idle` in `_begin("play")`; `_update_hint` stays as it is.
- Paint keeps its own paper (spec :477) and fades linearly to a floor, then off in one step: no blinking, and no
  lit channel under 140.
- Tug's echo holds each cell 0.5 s, so a cell turns on and off at most once per 0.5 s: under the flash rule by
  construction, even for a whole-grid strobe.

## Questions (defaulted; the owner's to change)

- Q161. Pool workers: 4 (Q97), with `ARCADE_POOL_WORKERS=1` for implementers. Why: the memory rule; the main
  process plus 4 workers is today's process count, the soaks only move between them.
- Q162. `WORKER_TIMEOUT_S` 180 -> 270, the pool's elapsed flagged over 230 s. Why: the pool grows to about 206
  s; 270 keeps today's third of headroom; a hung worker is now killed after 4.5 minutes, not 3.
- Q163. Paint's `needs = {"pose", "blobs"}` (the spec says "blobs, wrist"). Why: the wrist fallback needs a body,
  and a pose-only camera would otherwise offer a game with no light.
- Q164. The wrist paints when its cursor v is under 0.8 (`PEN_V`), across the zone x plus half an arm span
  (`ARM_SPAN = 0.5`). Why: a resting arm at the hip lifts the brush; the body's place moves the brush across the
  wall.
- Q165. Strokes fade linearly to 56% (`FADE_FLOOR`) over 20 s, then go off in one step. Why: the spec's 20 s
  fade, kept above the dim floor of 140 and without a slow flicker.
- Q166. The brush is 2 or 3 px, drawn once per game by the rng. Why: variety; the bots' wins then vary by seed as
  Jump's bell (it20).
- Q167. Paint `players = 2`, `exit_gesture = False` (the spec says "any" players). Why: two seats have colours
  (`PLAYER_COLORS`); both hands up is a natural painting pose, so it must not end the session.
- Q168. A light's colour is clamped and saturated (white under saturation 0.25); an untracked light (id -1) paints
  dots only; a new id within 12 px of a stroke lost under 0.3 s ago continues it. Why: halo colours from the
  camera are washed out; untracked blobs have no history to join.
- Q169. Paint is "won" at the gallery with at least 20% of the paper painted; the gallery is a 1 px white frame
  for 5 s. Why: the bots need a measurable win; a frame marks the end without a flash.
- Q170. Tug's pull is the left share minus the right, dead under 0.02, the knot moving 0.25 x pull a second. Why:
  a room-sized difference (about 0.14) crosses a goal in 17 to 29 s; sensor speckle stays in the dead zone.
- Q171. The goal is drawn per game from 0.6 to 1.0; at the 60 s cap a lean of 0.1 or more wins, else a draw. Why:
  rounds vary; a draw is honest when the room is even.
- Q172. Tug's words "WAVE!", "LEFT WINS", "RIGHT WINS", "DRAW" at 2x; the halves in `PLAYER_COLORS` (amber left,
  blue right). Why: short words that fit 128 px at 2x; the colours the arcade already uses for seats.
- Q173. Tug `abandon_seconds = 70`, `exit_gesture = False`, `players = 1`. Why: motion is no presence evidence
  (`runner.py:434`), so a 67 s round must outlast a room the pose model cannot see; a crowd's waving must not end it.
- Q174. The echo holds each cell 0.5 s. Why: under the flash rule by construction; long enough to read as a trail.
- Q175. Jump's result number moves right of the figure (or left of it when that overflows) when the figure would
  cover it, its x fixed on result's first tick. Why: the number is the player's score and must be read; a fixed x
  never jitters.
- Q176. `Blob.zone_x`/`zone_y` are compare=False. Why: they follow from x, y and the calibration; equality and
  scenario round trips stay as they are.
- Q177. The beside-the-pool reorder runs the safe files first, before the pool's readers and everything timed. Why:
  it is what saves the time; the guard test and the stable partition keep it safe.
- Q178. Paint and Tug are both `kind = "toy"` with no score drawn. Why: neither has a number to beat; toy budgets
  have no fidelity, win or score bands, and `test_bots_rank` still ranks the bots.
- Q179. Jump's bell flash (`fx.flash` at `jump.py:240`, applied to the whole frame at `juice.py:234-237`) lights
  rows 60 to 63 for 0.15 s; Jump's rows test (`test_jump.py:463-473`) draws without `fx.render`, so it does not
  see it. Default: not changed in it22 (an engine file, outside the slice); a later slice can confine the flash to
  rows 0 to h - 5. Why: the lead's rows rule is for the new games' own drawing; changing the flash belongs to a
  safety-reviewed engine task.

## Risks an adversarial reviewer will attack

1. Ordering dependence. A beside test may rely on state an earlier non-beside test set (a module-level cache, a
   monkeypatch left behind). The stable partition keeps each file's order but changes the order between files.
2. Hidden clocks. The guard reads imports and marks only; a beside test can still time something through the
   code under test (a runner with a real clock, a `time.monotonic` default argument). Under 4 busy workers such a
   test could flake. `test_runner.py` and `test_first_playable.py` are the likeliest; neither imports a clock
   today.
3. The deadline. 270 s against an expected 206 s is a 31% margin; a slow Mac morning (it21 saw out of memory)
   could cross it. A crossed deadline kills the workers and the main process remakes the missing plays: slow,
   not wrong.
4. Memory during batch 1. R's check runs a pool (main plus 4 workers) while C57's implementer runs its one
   process: 6 Python processes. During batch 2 the orchestrator's subsets wait for merges, so at most 2 + 5.
5. The bot cliffs. The lazy Tug bot's win share hinges on the goal draw (58% expected); a 20-seed sample can land
   from about 8 to 15. `win_good > win_lazy` holds unless lazy reaches 20; the lever is `wave`. Paint's lazy
   wrist bot must paint under 20% in most seeds; the mapping from `wrist_y` to cursor v is not measured here.
6. Response for Tug. Tug reads no body; its response probes come from the cursor, and only the canonical's sliding
   motion band makes the frame change within 2 ticks. That passes because the held run freezes the whole Sensed,
   motion included; a reviewer may call it coincidence. The band is the act Tug responds to.
7. Response for Paint. A probe with the wrist below `PEN_V` paints nothing; the canonical keeps v in 0.1..0.7
   from 6 s, so probes land while painting, and the ring moves with the brush.
8. Tug's presence. If the pose model loses everyone, the session lives on motion alone only by
   `abandon_seconds = 70` against a 67 s round: a 3 s margin.
9. Paint's wrist mapping puts a body at the zone's edge painting off the paper's side half the time (clamped).
10. The C57 number's fixed x: a figure that walks during `result` can still cross it; the tests use a still body.
11. Time. About 2 h 50 min to 3 h, over the two hours; the subset after each merge is nearly the pool's full
    work (about 4 minutes each), so it is not cheap.
12. The beside list names `test_paint.py` and `test_tug.py` through `MENU_ORDER` before they exist; the guard
    reads only existing files (26 now, 28 after batch 2).

## Not checked (open points for the reviewer)

- The beside set's 120 s: estimated from the it21 run's shape (only the slowest 25 durations are on file), not
  summed per file.
- `feel.py`'s response probe for Tug and Paint (risks 6 and 7): reasoned from the held-Sensed rule, not traced.
- The mapping from `Move.wrist_y` to the cursor's v for Paint's lazy bot (risk 5).
- Indirect clock reads in the 26 beside files (risk 2): only imports and marks were grepped.
- A worker's memory with soaks added: not measured; the process count is today's.
- C57's 15.0 s and 24.0 s: taken from `roadmap.md:129`, not re-measured.

## The plan's numbers

298 lines, the longest 118 characters (line 24). No line over 118.
