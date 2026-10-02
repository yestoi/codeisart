# it19 G1: Copy Me (`copyme`), the implementer's report

Branch `worktree-agent-aeb6d66f99fe9c79f`, from BASE `a5dbf29`. Plan: `docs/superpowers/plans/2026-10-01-it19-four-pose-games.md`,
section G1. The work was done test first: every test failed before its code existed.

## Files

- `arcade/poses.py`: seven new poses for the ladder: `right_up`, `left_up`, `y_pose`, `flex`, `airplane`, `disco`,
  `teapot`. All use the same `_pose` helper and `_LEGS`. `stand`, `arms_up` and `t_pose` are unchanged.
- `arcade/games/copyme.py` (new): the game, `LADDER`, the pure `score_pose`, and the four scenarios.
- `arcade/games/copyme_bots.py` (new): `good`, `lazy`, `won`.
- `arcade/games/copyme_feel.toml` (new): `[fidelity] input = "zone_x"`, `xy = "player_xy"`, `axis = 0`. No budget
  override.
- `tests/arcade/test_copyme.py` (new): 39 tests. These are the plan's acceptance list, the template tests, and
  `test_seat_bs_match_alone_flashes_and_says_match`.
- This report.

No engine, safety, shared or "not edited" file was touched. No existing assert changed.

## Tests and times

| Run | Result | Time |
|---|---|---|
| `tests/arcade/test_copyme.py` | 39 passed | 13.1 s (7.05 s is the template's 15 bot plays) |
| `tests/arcade/test_oracle.py -k copyme` | 3 passed | 47.2 s (43.3 s is the pool setup, which fills every game's report plays) |
| `tests/arcade/test_all_games.py -k copyme` | 8 passed | 10.8 s |
| Suite part 1 (`tests --ignore=tests/arcade`) | 1109 passed, 3 skipped | 125.8 s |
| Suite part 2 (`tests/arcade`, no oracle and no soak) | 771 passed, 1 skipped | 141.4 s |
| Suite part 3 (oracle and soak, `--durations=15`) | 49 passed | 104.6 s |

**Collected tests:** 1933. That is BASE's 1883 plus 50 new ones: 39 in my file, 8 Copy Me cases in
`test_all_games`, and 3 in the oracle. Collected did not drop.

**Skips:** 4, against 3 at BASE. The fourth is `tests/arcade/test_pose_mediapipe.py:303`
(`test_real_landmarker_runs_on_a_blank_frame`). It reports "no model at
`<worktree>/models/pose_landmarker_lite.task`": `/models/` is gitignored, so a worktree has no model, and the test
runs in the main checkout. The test does not read `POSES`. The `POSES` reader in that file (line 259, `stand`) ran
and passed.

None of the three known flaky timing tests failed.

### What my files add to suite time

All times are from `--durations` and probes.

- **Part 2:** `test_copyme.py` adds 13.1 s.
  - `test_good_beats_lazy_beats_nobody` takes 7.05 s. These are the template's 5 seeds x 3 bots, each good play
    24 s long. The same template costs Dodge 7.06 s.
  - The rest takes 6.0 s:
    - `test_own_drawing_keeps_the_flash_rule`: duo 1.06 s, canonical 0.86 s
    - `test_canonical_drives_the_lobby`: 0.74 s
    - `test_idle_body_scores_nothing`: 0.63 s
    - `test_seeded_runs_repeat`: 0.52 s
    - `test_debug_state_is_clean`: 0.52 s
    - the three real-noise tests: 0.23 s each
- **Part 3:** about 22 s.
  - The soak takes 5.05 s at 128x64 and 4.44 s at 96x48. For comparison, Pong takes 5.99 and 5.51 s, Quick Draw
    4.41 and 3.60 s, and Dodge 3.56 and 3.00 s.
  - The tick-budget and soak-flash tests take about 1.3 s.
  - The feel report call takes 3.19 s.
  - The pool spends 8.5 s on Copy Me's 60 report plays, measured alone with 4 workers, worker start included.
- **Total:** about 35 s, against the planned +25 s.
  - In a one-process suite, `test_copyme.py`'s 15 plays are already in `PLAYS` when the pool runs, so the pool
    plays 45 rather than 60.
  - About 0.6 ms of each tick's 0.9 ms is the runner, the governor and the bot feed. A cache of the drawn figure was
    tried and measured: it made a play only 3% faster, so it was reverted. The plan fixes the 24 s game.

## Bots and win rates (the 20 report seeds)

Bots:

- **good:** `reaction_ticks = 6`, `noise = 0.01`. It returns `Move(x=0.5, pose=state["target"])` in show and play,
  and `Move(x=0.5)` before.
- **lazy:** `reaction_ticks = 14`, `noise = 0.03`. It copies round 1, stands through round 2, and in round 3
  copies only `LADDER[2][0]` (`disco`).

| Metric | Value | Band |
|---|---|---|
| `win_good` | 1.0 | >= 0.7 |
| `win_lazy` | 0.4 (the 8 seeds that draw `disco`) | 0.1 to 0.7 |
| `win_none` | 0.0 | <= 0.05 |
| `round_seconds` | 24.0 | 20 to 120 |
| `phases_reached` | 1.0 | 1.0 |

No lever was tuned: every constant is the plan's starting value. Those values are:

- `ROUNDS = 3`
- `READY_SECONDS = 1.5`, `SHOW_SECONDS = 1.5`, `GROW_SECONDS = 3.0`, `GROW_FROM = 0.3`, `SCORE_WINDOW = 1.0`,
  `RESULT_SECONDS = 2.0`, `FREEZE_SECONDS = 1.5`, `OVER_SECONDS = 3.0`
- `LIMB_TOLERANCE_DEG = 30`, `JUDGE_MIN_DEG = 60`, `ACTIVE_DEG = 30` (over `ACTIVE_SECONDS = 1.0`)
- `MATCH_SHARE = 0.75`, `FRESH_SHARE = 0.5`, `WIN_MATCHES = 2`
- `FIGURE_H = 60`, `HINT_IDLE_SECONDS = 2.0`, `COLUMN_SLACK = 1`, `CAMERA_FPS = 10`
- `LADDER`: `(arms_up, t_pose, right_up, left_up)`, `(y_pose, flex, airplane)`, `(disco, teapot)`

## Feel metrics against their budgets (kind "score", 128x64)

| Metric | Value | Budget |
|---|---|---|
| response_ticks | 1.0 | max 2 |
| response_px | 280 | min 12 |
| fidelity | 0.9996 | min 0.8 |
| range | 0.701 | min 0.6 |
| lit_fraction | 0.108 | 0.01 to 0.5 |
| dim_fraction | 0.0 | max 0.1 |
| liveliness | 0.0177 | min 0.001 |
| flash_area_raw | 0.0111 | max 0.1 |
| square_flashes | 4 | max 6 |
| score_visible | 0.978 | min 0.8 |
| score_legible | 1.0 | min 0.9 |

`failures: []`. The game's own flash results: canonical and duo give raw `concurrent_area` under 0.1 with governor
held ticks 0. The soak passes at 128x64 and 96x48, including the tick budget.

## Deviations, each with its reason

1. **The canonical's walk.** The plan has a sweep from 0.2 to 0.8 to 0.5. Mine walks one way, from 0.15 to 0.85, at
   0.1 zone per second, in three legs between the rounds' pose cycles. The legs run at 5.0 to 8.25 s, 12.1 to 14.75 s
   and 18.6 to 19.85 s, all inside the measured 20 s. The player arrives at 0.15. There are two reasons:
   - **Range.** With the lobby's column backlash, 0.2 to 0.8 measures about 0.59, under the 0.6 budget.
   - **Flash.** A figure drawn in 2 px lines that walks trips the area rule. Measured raw `concurrent_area`, walking
     with no poses:

     | Speed (zone per second) | Raw `concurrent_area` | Governor held ticks |
     |---|---|---|
     | 0.1 | 0.049 to 0.054 | 0 |
     | 0.15 | 0.065 to 0.101 | 0 to 10 |
     | 0.2 | 0.105 to 0.129 | 5 to 15 |
     | 0.3 | 0.159 | 18 to 28 |

     Walking while the poses cycle measured 0.648. So the walk never comes within a second of a cycle (the
     rule's counting window) and never runs during a frozen frame, where the figure does not follow the body.

   The scenario test pins this: the endpoints, a span of at least 0.65, and no step faster than `WALK_SPEED`.
2. **The pose cycle covers only play's last `SCORE_WINDOW`, plus 0.25 s either side** for the launch's lag. It does
   not run through all of play. The score window is what counts, and the rest of play is left free for the walk.
3. **The torso axis.** The plan says hip_mid to shoulder_mid. Mine runs from both hips' centre to both shoulders'
   centre; with no hips it uses the shoulder line's normal, and with neither, the vertical. `Body.hip_mid` lets one
   hip stand in for two, which tilted the axis by up to about 20 degrees on a still body under real noise.
4. **`active` is sampled only on ticks when every judged segment is seen.** A dropout then cannot fake movement.
   Its window clears at each show, because the target changes.
5. **The target's name shows in show only.** The plan says "show: the target small with its name". In play nothing is
   drawn over the growing outline. The outline test measures `t_pose`'s arm span, not its height. The arm span scales
   by the same factor, and the hint, name and MISS lines (rows 41 to 58) may cover the outline's feet.
6. **"MATCH!" shows when any seat matched.** This is when the flash fires: in a duo it fires for either seat. Each
   seat's "+N" pop (green on a match, else its own colour) says whose match it was. The plan words it as player 1's
   share only.
7. **A refused flash becomes a burst.** When `fx.flash` returns False (`FLASH_GAP`), a `fx.burst` goes at the
   figure. The plan says "checked" but not what to do on a refusal.
8. **A score is recorded only when the total is over 0.** That is the plan's "when a round counted". A pose that was
   not fresh scores 0 and shows MISS.
9. **`LADDER` lives in `copyme.py`.** `poses.py`'s docstring points to it.

## Owner questions

1. **Player 2's colour against the outline.** Player 2's blue `(0, 160, 255)` is close to `OUTLINE_COLOR`
   `(0, 200, 255)`, so in a duo seat b's figure and the cyan outline are hard to tell apart. Should the outline take
   another colour, such as magenta? The plan fixes it, so it is unchanged.
2. **Walking makes the figure stutter.** In Copy Me, a real player crossing the mat at an ordinary pace (0.2 zone
   per second or more) makes the governor hold frames. The wall stays safe, but the figure stutters while they walk.
   Options:
   - accept it;
   - draw a heavier figure;
   - slow the figure's column. C46 says no Glide for a figure.
3. **Time over budget.**
   - G1's suite share is about 35 s against +25 s.
   - The file takes 13.1 s against the 6 s budget for my own tests. 7.05 s of that is the template's 15 bot plays;
     the rest is 6.0 s.
   - The engine's tick cost and the plan's 24 s game set most of it. The whole three-part suite took 372 s, against
     the 540 s cap.
4. **The text lines cover the figure's lower legs.** The name, the hint, MISS and MATCH! cover rows 41 to 58 of the
   figure. No ladder pose judges a leg. Is that acceptable?
