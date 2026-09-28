# Orchestrator report, iteration 6

`it06-orchestrator` (opus), 2026-09-28 15:18 to 16:03, BASE ab40231. Transcribed by the operator from the orchestrator's report.

## Completed
- S1 (C30a/b/c, C31, `arcade/runner.py`): 9 new test cases. `test_a_numpy_str_phase_still_caps` and both `test_a_raising_limiter_or_governor_pushes_nothing` cases passed before the change; they guard behaviour that already worked. `_push`, the limiter, the governor, `flash.py` and `brightness.py` were not touched.
- S2 (`run_headless(..., lobby=...)`, `game_cls` a class or a sequence): 4 tests.
- P1, the small lobby and `arcade/figure.py`: all planned tests, plus `test_end_card_says_best_on_a_record`.
- P2, Pong: all 14 planned tests, plus a tie at 90 s and humans per scenario.
- P3, `tools/arcade_shot.py`: the 8 planned tests plus a `git_sha` test.
- Merges into main in plan order, no conflicts, the suite green after each.
- I1, `tests/arcade/test_first_playable.py`: 3 tests. Duel: Pong launches on the tick of the raise; 5-0 in 23.3 s, `reason done`, `players 2`, `score 5.0`; the card shows that score for 90 ticks; the left paddle's correlation with player 1's sweep is above 0.95. Solo: `cpu == "right"`, `players 1`, a best recorded.
- Stretch X1, `MediaPipeCamera`, `BodyTracker`, `assign`, One Euro: 39 tests.
- Stretch X2, `make_sources`, `ScriptedCamera` with `SCRIPTS["walkup"]`, `build_display`, `run` as the default command, `main` builds the runner with the small lobby and the games once: 8 tests.
- Done-when: `python -m arcade run --seconds 5 --script walkup --config <scratch>` exits 0 under the SDL dummy driver; `python -m arcade doctor --require camera,pose` exits 0.

## Deviations
- I1's flash assert is narrower than the plan: pushed `flash_area` is 0.000244 over the whole run (one pixel of the mirror's arm, after the first card). Asserted: 0.0 up to the end of the first card, pushed at most raw over the run; the other three flash asserts as planned. The reviewer ruled it Q13's exemption.
- I1 adds a 1 s empty lead-in before Pong's scenarios, so attract is seen.
- P1: `test_implements_lobbylike` checks `LobbyLike.__protocol_attrs__` minus the members from `Game`; the hidden case hides the game with 3 real crashes; the card draws text only; the `Hold` resets in `end_session`; nothing is available before the first `set_available`.
- P2: a second body present at launch joins at once; points belong to seats; `cpu` is None when both seats are CPU; both scenarios are 3000 ticks.
- P3: `contact_sheet` takes `gamma=2.2`; `TITLE_H`, `CAP_H`, `PAD` exposed; `raw_vs_pushed` lays out 4 pairs a row; the timelines print the whole run; the tests use the shared `font` fixture.
- X1: the model path is resolved in the constructor; spec 6's 30 s camera reopen retry is not built; scipy is not in the venv, so `assign` uses the exhaustive search; a recency cost of 0.1 per second breaks ties at a crossing; a coasting body keeps its last keypoints.
- X2: `make_sources` takes `calibration=None`; `run` has `--config`; `--script` ignores `cfg.camera`; the walkup script reaches Pong at 3.2 s.
- Process slips: P1 and X1 each ran one command with `cd`, both read-only.
- The three worktree branches are merged; their worktrees are left under `.claude/worktrees/`. No shared file was edited.

## Findings passed to the review
1. The Mac camera reports 1280x720 (ruled harmless: the arcade captures 640x480).
2. Nothing had run `MediaPipeCamera` end to end (the reviewer did, 6 s).
3. On the tick a game ends on `done()`, the trace holds only the runner's keys.
4. Each 100 s Pong scenario starts 3 or more sessions; `runner.game` after a run is the last.
5. In solo the scripted player loses 0-5; only `test_cpu_is_beatable` shows the CPU beaten.
6. `arcade_shot` stamps `+dirty` whenever `git status` lists anything.
7. A bare `python -m arcade` opens the real camera.
8. `run` does not check that `data_dir` exists (harmless: `Scores` and `SessionLog` create it).
9. `helpers.run` has no `raw` passthrough.
10. The lobby primes its Edge at the end of the card, which is redundant.

## Test status
`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs`

| Step | Passed |
|---|---|
| Base | 478 |
| After S1 | 487 |
| After S2 | 491 |
| After merging P1 | 517 |
| After merging P2 | 537 |
| After merging P3 | 546 |
| After I1 | 549 |
| After X1 | 588 |
| After X2 (b6cede1) | 596 collected, 596 passed, 0 skipped |

## Commits
- 82de50f fix(runner): C30 and C31
- c5d5d6f feat(headless): S2, run_headless takes a lobby and a sequence of games
- 85e58fe feat(figure): to_wall, figure_rect and draw_figure
- dce9810 feat(lobby): the small lobby
- 238b5e6 feat(games): Pong
- 5d48393 feat(tools): P3, arcade_shot
- fb6300a Merge P1, e26bdc2 Merge P2, 1b1eb36 Merge P3
- b5700d2 test(first-playable): M3b done-when
- 68f9592 feat(camera): MediaPipe pose camera, threaded base and body tracker (X1)
- b6cede1 feat(arcade): make_sources, scripted walk-up camera and `python -m arcade run` (X2)

## Minutes
Serial lane 5, parallel tasks 12 (P1 11.7, P2 6.3, P3 2.0), integration 10, stretch 17 (X1 9.5, X2 3.8). Total 44.
