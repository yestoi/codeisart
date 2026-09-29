# Iteration 8 orchestrator report (M4b: the four-panel wall, 128x64 only)

Base 167d513, HEAD 2e016e5 (main). Nothing pushed, no tag, I2 not run.

## Completed
- S1 (opus, main checkout), 7ea99fa. `LAYOUTS = {"128x64"}`. `ArcadeConfig` and `arcade.toml` default to 128x64, with the comment "four 64x32 panels, 2 x 2 (Q32)". Juice falls back to (128, 64). `arcade run` logs `wall 128x64, backend B` at INFO. `helpers.SPY_LAYOUTS` exists. The tick-budget test gains a 128x64 case. The commit carries the Q33 sentence and the canary is untouched. No test_juice test moved (two rely on the default size, but not on its value).
- S2 (opus, main checkout), 2f9a261. C38:
  - `response_ticks` is latency (the first differing pixel after a probe).
  - `response_px` is new: magnitude, the pixels that differ `LATENCY_TICKS` = 2 ticks after the probe. Its budget is `min = 12` for control, score and toy.
  - A clamped control is not probed.
  - Canonical and the counterfactual reruns launch through a fresh `Lobby([game_cls], cfg)`.
  - `measure` raises ValueError for an undeclared layout.
  - `bots.play` and `win_rate` default to the game's one declared layout.
  - All the plan's tests are in, plus the strict xfail that I1 removed.
  - Pong at 128x32 at this commit: `response_ticks` 1.0, `response_px` 12.0. It passed, with no margin.
- P1 (sonnet, worktree), 6eff63a plus the time fix 789566b:
  - Pong declares only 128x64.
  - Scores draw at 2x, 10x14, at top row y 1, centred on w/4 and 3w/4.
  - `CPU_SPEED` is a share of the height per second.
  - C41: a human's point counts only if that player moved in the rally, and a best is stored only if the solo player moved in the game.
  - The feel file has `[budgets."128x64"]`.
  - The oracle's one module-scoped report is at 128x64.
  - `test_canonical_round_from_attract_to_the_card` is new, along with every other test the plan names.
  - Final tuning: CPU 0.35 wall heights/s, ball starting at 100 px/s, gain 1.2, max 170. 20 of 20 good rounds end by points before the cap (34 to 73 s, median 46.6 s).
- P2 (opus, worktree), 4cbf08f:
  - `BIG_ROWS` 48 and `BIG_SCALE` 2, with the `_lines(..., scale)` and `_centred(canvas, [(text, scale)], color)` signatures from the plan.
  - Attract's title and the card's head line and BEST! draw at 2x on tall walls where they fit, and fall back to 1x. The prompt stays at 1x.
  - `test_lobby.py` and `test_figure.py` override `size` with (128, 64), (128, 32) and (64, 64).
  - Every named test was added, plus `test_a_column_jitter_does_not_step_the_figure`.
  - `arcade/figure.py` is unchanged.
- P3 (sonnet, worktree), 5b964ea:
  - `arcade_shot --size` defaults to "128x64".
  - `wall_pattern` defaults to 128x64, with `PANEL_W, PANEL_H = 64, 32`. `index` draws a seam at every panel edge and the four corners as before.
  - C40: games.md prints `-` in the ok column for a metric with no budget.
  - The four named tests are in, and line 206's PNG is `(128 * 8, 64 * 8)`.
- P4 (sonnet, worktree), a055266:
  - The guide (299 lines) says 128x64 is the only design layout. It gives `[budgets."128x64"]` and `feel.report(GameCls, "128x64", ...)`, scores at 2x, C41, `response_ticks` against `response_px`, and the lobby launch (walk-up, raised hand, and the game listed in `MENU_ORDER`).
  - `live-smoke.md` has one row per game at 128x64 and names the 2 x 2 wall.
- Merges in plan order, each with `--no-ff` and the full suite after it: P1 21a4bdc, P2 62fef06, P3 3464e7e, P4 e418988. P1's time fix was merged last, as d5494f4.
- I1, 2e016e5: `SCORE_SCALES = (2,)`, and S2's xfail mark is removed. It also carries one stub fix in `test_feel.py` (see Deviations).
- X1 (stretch) was not run. See Minutes.

## Deviations
1. **Suite time after P1 (fixed in one round).**
   - After P1 merged, the suite took 178.4 s against the 175 s limit. Pong's four test files went from 86.4 s to 130.6 s standalone (+44 s against P1's +15 s share). The oracle's report alone went from 46.9 to 71.5 s, because every good round ran to the 90 s cap.
   - I sent P1 back once to its own worktree, within the operator's limits: 20 seeds, no weakened assert, no skip or slow mark, no loosened band.
   - P1 retuned `arcade/games/pong.py` only (789566b): CPU_SPEED 0.75 to 0.35, BALL_START 60 to 100, BALL_GAIN 1.08 to 1.2, BALL_MAX 110 to 170.
   - Pong's four files now take 95.6 s standalone, and the quiet full suite 140.9 s.
   - The round took about 14 minutes (19:22 to 19:36), against the operator's 10.
   - P1's note for the owner: the ball is now fast (100 to 170 px/s on a 128 px wall) and should be judged by eye in the live smoke. The plan's defaults (CPU 0.75 "before tuning", ball speeds as at 128x32) were changed by P1 under its tuning brief.
2. **I1 touched more than the xfail mark in `test_feel.py`.** S2's `Scorer` stub drew its points at 1x before t = 2 s, so with `SCORE_SCALES = (2,)` `test_score_visibility_counts_the_ticks_it_is_shown` got 0.508 instead of 0.75. S2 had checked its simulation of (2,) only against the xfail, legibility and find_text tests. I made the stub draw at 2x throughout (and fixed its docstring). The assert is unchanged. This was a stub edit in I1's file by the integrator, not by a fresh implementer.
3. **I1's suite run also covers the P1 time-fix merge.** I merged d5494f4 with I1's two edits already in the working tree, and one quiet suite run covered both before I committed I1.
4. **S2's other deviations:**
   - The feel stubs are added to `arcade.attract.lobby.MENU_ORDER` inside `test_feel.py`, because the lobby launches only games listed in `MENU_ORDER`.
   - A new ValueError, "<name> never launched from the lobby", with its own test.
   - Metrics count only the session the raised hand launched.
   - The frame metrics (lit, dim, liveliness, flash) start one tick after launch, because the launch tick still shows the lobby's frame.
   - The stubs' canonical is 8 s.
   - `test_legibility_...` passes `scales=(1, 2)` explicitly.
   - `test_a_1x_score_is_not_visible` uses `feel._score` on a 60-tick direct run instead of a full `measure`.
   - No assert was weakened (I checked the diff).
5. **P1's other deviations:**
   - C41 over seeds is a new test, `test_idle_body_scores_nothing_over_seeds`, beside the unchanged `test_idle_body_scores_nothing`.
   - `test_cpu_is_beatable` keeps its asserts but uses a moving player, with the ball starting at x 96 and vy 90.
   - `test_canonical_round_from_attract_to_the_card` stops the feed after the first card. The full canonical logs three sessions.
   - A `None` mode on the tick a game ends is ignored when reading the mode order.
6. **P2 fixed a real flicker at 128x64 in the lobby.**
   - The problem: at 128x64, `test_mirror_under_real_noise_keeps_the_area_rule` failed with raw `concurrent_area` 0.1006 against the 0.1 limit. Camera x-jitter stepped the whole figure one column and back.
   - The fix: the lobby keeps each figure's column with 1 px of play (`COLUMN_SLACK = 1`, reset when a new person takes the slot), which brought the area to about 0.068.
   - Test changes (no asserts changed):
     - The mirror test's own `parametrize("size")` is removed, so it runs on the module override.
     - Two figure tests that looped over hardcoded sizes now take the `size` fixture.
     - `test_a_column_jitter_does_not_step_the_figure` is added.
   - P2's finding: Copy Me and the attract director draw the same figure through `figure_rect`, so they probably need the same slack at 128x64 (a candidate for `figure.py`).
7. **P3's test changes** (no asserts changed):
   - The old `test_index_marks_the_four_corners_and_the_panel_seam` keeps its own list, [(128, 32), (64, 64)]. It probes row h // 2, which is the row seam at 128x64, and the new seam test covers 128x64.
   - `test_header_has_provenance` passes `--size 128x32` explicitly, since it relied on the old default.
   - `test_default_size_is_128x64` swaps `argparse.ArgumentParser.parse_args` by hand, restoring it in a `finally` (not monkeypatch).
8. **Findings outside the tasks** (not acted on):
   - S2: in the lobby, the sweep's top position counts as a raised wrist, so a player sweeping near the top relaunches the game from the card.
   - S1: `arcade/sensed.py:35` `MOTION_GRID = (128, 64)` is a motion grid, not the wall size, but a grep for the size finds it. The new `test_main` runs the real Runner against the repo's `arcade.toml` (`data_dir = "data"`); it wrote nothing.
   - P1 (first round): `win_lazy` sat at its 0.10 floor. After the retune it is 0.55.
9. The worktree suites show 1 skip (`test_pose_mediapipe.py`: the model file is absent in worktrees). There are no skips on main.
10. Every implementer commit ends with the `Claude Fable 5.1` Co-Authored-By line, as the lead instructed. The merge commits carry no trailer.
11. No failed branches. The four worktree branches are left in place: `worktree-agent-a0e3d1069ac98cb9e` (P1), `-a9024fc927936ddc4` (P2), `-a7ac68f13a8ba348d` (P3), `-abb2a32d4ad1a2afb` (P4).

## Test status (command + counts)
Command, from /Users/trey/dev/codeisart: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs`

| Point | sha | Result | Seconds |
|---|---|---|---|
| Base | 167d513 | 675 passed (it07) | 133.6 |
| After S1 | 7ea99fa | 678 passed | 133.1 |
| After S2 | 2f9a261 | 686 passed, 1 xfailed | 140.0 |
| P1 merged | 21a4bdc | 692 passed, 1 xfailed | 178.4 (quiet, over the limit) |
| P2 merged | 62fef06 | 712 passed, 1 xfailed | 205.3 (under load: P1's rework ran alongside) |
| P3 merged | 3464e7e | 722 passed, 1 xfailed | 205.5 (under load) |
| P4 merged | e418988 | 722 passed, 1 xfailed | 233.8 (under load) |
| P1 fix + I1 | d5494f4 / 2e016e5 | **723 passed, 0 skipped, 0 xfailed** | **140.88 (quiet)** |

- The final run is +7.3 s over it07's 133.6 s, under the 40 s allowance and the 175 s limit.
- Tick-budget test at 128x64: strobe tick mean 0.585 ms (p95 0.857, governor 0.377); static tick mean 0.510 ms (p95 0.535, governor 0.317). The budget is 2.0 ms, unchanged.
- Slowest tests in the final run:

| Seconds | Test |
|---|---|
| 38.68 | oracle report (setup) |
| 8.68 | test_good_beats_lazy_beats_nobody |
| 6.76 | test_evidence_package_for_pong |
| 3.58 | test_first_playable_keeps_the_flash_rule |
| 3.46 | soak pong-128x64 |
| 3.30 | test_scenarios_have_the_right_humans |
| 3.23 | test_own_drawing_keeps_the_flash_rule |
| 3.17 | mirror area rule [128x64] |
| 3.07 | response_ticks probe count [creeper] |
| 2.63 | soak pong-96x48 |

- Full output: /private/tmp/claude-502/-Users-trey-dev-codeisart/d1e01db2-fed8-414f-9a38-325b95bc9c3a/scratchpad/it08-suite-i1.txt
- Added time per task:

| Task | Added | Share |
|---|---|---|
| S1 | ~0 s | +5 s |
| S2 | +6.9 s | +10 s |
| P1 | ~+9 s after the fix (Pong's four files 86.4 to 95.6 s standalone) | +15 s |
| P2 | ~+4.7 s (per `--durations`) | +10 s |
| P3 | < 2 s | +2 s |
| P4 | 0 s | none |

## Pong's feel at 128x64 (every metric, value, budget; failures)
`feel.report(Pong, "128x64", seeds=bots.seeds(Pong, "128x64", 20))` at HEAD 2e016e5, with `SCORE_SCALES = (2,)`:

| Metric | Value | Budget |
|---|---|---|
| response_ticks | 1.0 | max 2 |
| response_px | 28.0 | min 12 |
| fidelity | 0.9937 | min 0.8 |
| range | 0.7619 | min 0.6 |
| lit_fraction | 0.0257 | 0.01 to 0.5 |
| dim_fraction | 0.1533 | max 0.3 (pong_feel.toml override, reason: the dashed net) |
| liveliness | 0.00265 | min 0.001 |
| flash_area_raw | 0.0 | max 0.1 |
| square_flashes | 0.0 | max 6 |
| score_visible | 0.9741 | min 0.8 |
| score_legible | 1.0 | min 0.9 |
| presence_answer_seconds | 0.0 | none (measured only) |
| win_good | 1.0 | min 0.7 |
| win_lazy | 0.55 | 0.1 to 0.7 |
| win_none | 0.0 | max 0.05 |
| round_seconds | 46.63 | 20 to 120 |
| phases_reached | 1.0 | min 1.0 |

Failures: none (`[]`). The oracle test passes in the suite. Good rounds ending by points before the cap: 20 of 20.

## Commits (sha + subject)

| sha | Subject |
|---|---|
| 7ea99fa | feat(arcade): it08 S1, the wall is 128x64 by default: LAYOUTS, config, tick budget at 8192 pixels |
| 2f9a261 | feat(arcade): it08 S2, C38: response latency and magnitude apart, feel launches through the lobby |
| 6eff63a | feat(arcade): it08 P1, Pong at 128x64 with 2x scores (C39); an idle body scores nothing (C41) |
| 4cbf08f | feat(arcade): it08 P2, the small lobby laid out for 64 rows |
| 5b964ea | feat(tools): it08 P3, the tools at 128x64: seams at every panel edge, a dash for a metric with no budget (C40) |
| a055266 | docs(arcade): it08 P4, the guide and the live smoke say 128x64 |
| 21a4bdc | Merge it08 P1: Pong at 128x64, 2x scores (C39), an idle body scores nothing (C41) |
| 62fef06 | Merge it08 P2: the small lobby laid out for 64 rows |
| 3464e7e | Merge it08 P3: the tools at 128x64, and C40 |
| e418988 | Merge it08 P4: the game guide and the live smoke say 128x64 |
| 789566b | perf(arcade): it08 P1, Pong's tuning ends good rounds by points: CPU 0.35, ball 100 to 170, gain 1.2 |
| d5494f4 | Merge it08 P1 time fix: Pong retuned so good rounds end by points (suite time) |
| 2e016e5 | feat(arcade): it08 I1, C39's last step: the oracle finds scores at 2x only |

## Minutes
Start 18:33, I1 committed 19:39: 66 minutes in all, against the 60-minute target.

| Stage | Time | Minutes | Notes |
|---|---|---|---|
| Serial lane | 18:33 to 19:00 | 27 | S1 about 4, S2 about 22 |
| Parallel tasks | 19:00 to 19:15 | 15 | wall time; the slowest was P1 at 13.5 minutes. P2 10.8, P3 6.4, P4 0.6 |
| Integration | 19:15 to 19:39 | 24 | four merges with a suite after each, the P1 time-fix round (19:22 to 19:36, running beside the P2 to P4 merges), then I1 with its stub fix and a quiet suite run |
| Stretch | none | 0 | see below |

- X1 was not run. The time condition was barely met: 66 minutes at I1's end, against fewer than 70. But one opus TDD task with at least two full suites at about 2.4 minutes each, plus a merge check, would likely overrun the 15-minute cap, and the whole run was already past its 60-minute target. In doubt, left out.
