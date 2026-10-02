# Iteration 20, the plan writer's report

Plan: `docs/superpowers/plans/2026-10-02-it20-suite-room-jump-m5.md` (272 lines, none over 118 characters). About
36 minutes, over the 30-minute budget by a few; I cut detail rather than tasks: S2 stays in, in its thin form.

## What I read
- The brief; config.md "Loop rules" 1, 2, 5, 6, 10; the roadmap's M7a, M5 and M7b lines, "Carried:" (C55), and the notes
  tagged it19 (the suite's room), it19 (the next task in the four games' files), C11/C17, C21, C34, C35, it15 (the
  orchestrator's brief) and the Q99 spec note; decisions.md Q99.
- it19's plan (form and Global Constraints, carried over in its words where they still hold), `tests/arcade/pooled.py`,
  `tests/arcade/test_oracle.py`, `tests/arcade/helpers.py`, both conftests, `tests/arcade/test_all_games.py` (its timed
  test), `tests/arcade/test_game.py:166-240`, `arcade/sensed.py` (`Blob`, `place_blob`), `arcade/bots.py` (`Move`,
  `_sensed`, `seeds`), `arcade/sources/actors.py` (`Person`, `jump`, `_lift_at`), `arcade/games/copyme.py`'s colours,
  `arcade/juice.py:58`, `arcade/flash.py:23-40`, and the core plan's Task 12 (3524-3776, amendment 588) and Task 15
  (4252-4396, amendment 620-630) signatures.
- I did not read it18's plan in full or the authoring skill (time); it19's plan carries their rules.

## What I measured
- `orient-durations.txt` summed by file in run order (collected with `--collect-only`, 84 files): the soaks
  (`test_all_games.py`) are the second file and take 88.8 s; Copy Me's file starts about 92 s into the run, the
  oracle at about 207 s (116.5 s with its 89.9 s pool setup); `test_headless.py` (the two timing asserts) at about
  193 s; `tests/test_show_shot.py` (the strobe test) at about 410 s.
- The games' 5 seeds are the first 5 of the report's 20 (`bots.seeds` = `crc32(f"{name}:{layout}:{i}")` for
  `i < n`) under the same `play_key`, so a pooled play serves `helpers.played` as is.
- The Mac: `hw.ncpu` 8 (4 performance, 4 efficiency), load 3.8 to 4.7 while I worked. cv2 5.0.0 in the venv (S1).
- Every test name the plan cites as existing was grepped: each found (`test_own_drawing_keeps_rows_60_to_63_dark` in
  Flap's and Freeze's files only, as the roadmap says).

## Decisions, with reasons
1. **R is A and B in one design.** The pool starts when collection ends (`pytest_collection_finish` in
   `tests/conftest.py`) and runs beside the soaks; a `pytest_runtest_setup` hook joins it before the first test that is
   not a soak (`BESIDE_THE_POOL` = the actors and soak files, minus the `perf` tick-budget test, which reads
   `thread_time` and would pay for an efficiency core). So every game's own 5-seed tests and the reports read `PLAYS`.
   The join in the setup hook, not in `helpers.played`, keeps `helpers.py` unchanged and holds in any `-k` or file
   order: the three timing asserts and `test_show_soak.py`'s child check can never run beside a worker.
   Estimate: today 89.9 s (setup) + 34.3 s (four games' in-process plays) on the path; after R, about 15 s of join
   wait (420 plays at today's rate take about 105 s, plus contention, against about 100 s of soaks) and about 10 s of
   slower soaks: about 410 s at 505.09 s's load (about 385 s at the quieter 476 s). Jump adds about 30 s: about
   445 s after the slice. C (soaks in workers) is not planned; it is it21's first candidate if R saves under 60 s.
2. **The pool's rows follow the selection** (`rows_for`): `-k jump` pools Jump's 60 plays, not all 480. Four
   worktree implementers each running `test_oracle.py -k <name>` on the shared 8-core Mac would otherwise start 16
   workers for 1920 plays. The pool's own test asks every row, so `test_the_pool_made_every_missing_play` is unchanged.
3. **`WORKER_TIMEOUT_S` 120 to 180 s.** Eight games' 480 plays take about 105 s alone, about 120 s beside the soaks:
   120 would fail on a busy afternoon. 180 is 1.5 times the estimate; one failed share then costs about 80 s of wait
   and 70 s of in-process replay, about 560 s, under 10 minutes. (Four hung shares passed 10 minutes at 120 s too.)
   The terminal summary line prints the pool's time, so it21 sees how close it runs (Paint and Tug add 120 plays).
4. **`--collect-only` starts no pool**; `pytest_sessionfinish` stops a pool not joined (`-x`, Ctrl-C).
5. **The rename touches more asserts than the brief said** (Q121). `test_broken_module_is_logged_and_skipped` keys its
   fake modules by `MENU_ORDER` names (`fake_modules`, `test_game.py:176-189`): with `"jump"` in `MENU_ORDER`, the
   `"strongman"` fake at :226 is never imported, so the lists at :236 and :239 lose `"strongman"`. The key and the two
   lists change to `"jump"` (sorted), the name only; :221-222's `strongman_audio` text and `test_scores.py:158` stay.
6. **I0 is needed.** `Move` has no whole-body rise and a bot's `Person` lives one tick, so `Person.jump` cannot be used.
   `Move.lift` (no noise draw, so no existing play changes) lifts the whole body; the bot draws its own arc.
7. **E0**: `id`, `vx`, `vy` keyword-only after `in_zone` (`dataclasses.KW_ONLY`): every existing caller passes four
   or five positional fields and `test_sensed.py:273`'s equality holds with the defaults. No assert changes.
8. **Jump**: a high striker with a bell line drawn per game from the rng (28 to 40 cm); three attempts; the height in
   cm from `TORSO_CM = 50` (Q122); the hips must rise with the nose (`HIP_SHARE`, Q125), so a nod, a lean or a
   still body under noise never counts (C41). The figure follows `zone_x` (Copy Me's fidelity, the canonical's walk).
   Win = the bell rang (Q123): the lazy bot's fixed peak at the band's middle wins about half the seeds by the rng's
   bell, as Copy Me's lazy hangs on its rng. The bar is orange (255, 160, 0): red share 0.61, never doubled.
9. **F1**: magenta's distances to amber, blue and green are 282, 301, 413 (RGB Euclidean); the test's floor is 150.
   Magenta's red share is 0.5, under `RED_SHARE = 0.8`. `OUTLINE_COLOR` is used only at `copyme.py:279-280`.
10. **S1 and S2 export nothing** from `arcade/sources/__init__.py` (a shared file): wiring is it21's, so no shared
    edit. S2 does not import S1; raw replay through `FrameFeatures` is it21's.

## Owner questions (none blocks; each default is in the plan)
- **Q121** The `strongman` to `jump` rename changes `test_game.py:236` and `:239` (and the fake's key at :226), not
  only :171: the test keys its fakes by `MENU_ORDER`. Default: the name changes in those three places, nothing else.
- **Q122** Jump's number: centimetres from the torso (`TORSO_CM = 50`), the spec's "metres" shown as cm (a 2x "42"
  reads better than "0.42"). Default: cm.
- **Q123** What Jump's win is: ringing a bell whose height the rng draws once per game (28 to 40 cm). Default: so.
- **Q124** The pool's deadline rises from 120 s to 180 s (decision 3). Default: 180 s.
- **Q125** A jump counts only when the hips rise too (`HIP_SHARE = 0.5`): a player whose hips the camera crops cannot
  score. Default: hips required (the invite's "stand back" covers it); the owner may relax it to the shoulders.

## For the orchestrator
- R first, then one full run (the gate); the pool's summary line and `--durations=40` saved as
  `evidence/it20/r-durations.txt`. Compare against a reading of BASE at a similar load if the load differs.
- The core plan's `test_features_under_3ms_at_160x120` is a timing test: it uses `thread_time` and is marked `perf`.
