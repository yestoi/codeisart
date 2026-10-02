# Iteration 19 (arcade): Copy Me, Flap, Swat, Freeze (M7a)
BASE: HEAD after I0 is committed (the orchestrator gives the sha). Thin plan. Not a safety slice. "Spec" =
`docs/superpowers/specs/2026-09-26-wall-arcade-design.md`, not edited. Jump (Strongman without its roar, Q99) is it20.
No engine file (`arcade/runner.py`, `headless.py`, `game.py`, `sensed.py`, `canvas.py`, `juice.py`, `input.py`), no
safety file (`arcade/flash.py`, `brightness.py`, `show/display/colorlight.py`). No existing assert changes (I0, G1).
Reviewed: `docs/superpowers/workflow/evidence/it19/plan-review.md` (B1 to B8 and its notes are fixed in this text).
## Global Constraints
- Test command, from the checkout's (or worktree's) root: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
  /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs`. At 820349b: 1881 collected, 1878 passed, 3 skipped,
  312.10 s on a shared Mac. One command per Bash call; tools as modules (`python -m tools.arcade_shot`); no `cd`.
- Touch only your task's files. Test-first. No removed or weakened assert; no band in `arcade/feel_budgets.toml` or a
  `*_feel.toml` loosened; no `*_feel.toml` override without a game-made reason (guide 5). An assert this plan does
  not name that would have to change: stop and report.
- 128x64 only (Q32, Q33, Q82): every game declares `layouts={"128x64"}`; no code, test or tuning for another size
  (the generic soak at 96x48 is the engine's and stays as it is). Rows 60 to 63 stay free (the runner's marker).
- The frozen protocol is unchanged; `test_protocol_members_are_the_frozen_set` is not edited. `GameInfo.players` is 1
  or 2 (`arcade/game.py:89`): a game reads `sensed.player` and `sensed.player2`, never `bodies[0]`.
- No game reads the microphone or the motion grid (Q99; M5 is not built): every `needs` is `{"pose"}`.
- Flash (C24, guide 6): each game's own frames keep governor held ticks 0 and raw `concurrent_area` under 0.1; no
  reversing stripes; a loss, a crash or an out holds and fades, never blinks; saturated red counts double. Every
  `fx.flash` return is checked.
- C41, C42: a still body (and Nobody) scores nothing and banks no best; each game says what counts below. Bots rank
  `win_good > win_lazy > win_none`, `phases_reached == 1.0`, every budget met (`tests/arcade/test_oracle.py:101-117`).
  Bot numbers and each section's named levers are starting values: tune them until `win_good >= 0.7` and `0.1 <=
  win_lazy <= 0.7` hold on the 20 report seeds (`pytest tests/arcade/test_oracle.py -k <name>`); no other rule moves.
- C46: a pointing hand goes `Cursor` (`input.py:129`) then `Glide` (`input.py:214`), never `Body.cursor`; a control
  on `zone_x` goes through a `Glide`; a figure maps raw `zone_x` with a column backlash of `COLUMN_SLACK = 1` in the
  game's own file (the lobby's two lines, `arcade/attract/lobby.py:49,181`; the it08 note: 0.1006 raw without it), no
  Glide; graces `capture_grace(CAMERA_FPS)`, `CAMERA_FPS = 10`.
- Colours saturated, low channels 0, no channel set under 140 alone (`feel.DIM_LEVEL`); scores at 2x (`SCORE_SCALES =
  (2,)`), drawn last over a black box 1 px wider than the text, from the game's first tick (`score_visible` >= 0.8).
- `Sensed`/`Audio` by keywords; seeds `zlib.crc32`, printed; `time.thread_time`; no push, save or config read.
- The canonical's first 20 s are measured (`feel.FEEL_SECONDS`): 2 s empty, the walk-up, the raise, then the sweep
  that fidelity and range need, inside those 20 s; then play that gets past the first round (it18's Dodge note).
- Suite: at most 540 s (Q102). Shares: I0 +1 s, G1 +25 s, G2 +30 s, G3 +38 s, G4 +32 s; expected about 440 s (good
  plays: Copy Me 26 s, Flap 48 s, Swat 66 s, Freeze 52 s). Each game's 60 report plays reach the pool by themselves
  (`REPORT_PLAYS`, `test_oracle.py:22-26`); its own tests at most 6 s. Report what your files add (`--durations=15`).
- Template tests in every game's file (`test_dodge.py`'s shape): `test_debug_state_is_clean`,
  `test_required_scenarios_start_with_an_empty_wall`, `test_canonical_drives_the_lobby_to_<name>`,
  `test_bots_module_is_found`, `test_good_beats_lazy_beats_nobody` (5 seeds via `helpers.played`),
  `test_good_round_length_in_band`, `test_feel_file_overrides_have_reasons`, `test_seeded_runs_repeat`.
- Under load three timing tests fail and pass on a rerun (the it15 note): rerun them alone before a revert.
## Lanes and merge order
1. I0, orchestrator, main checkout, committed before the spawn (its sha is BASE).
2. PARALLEL, `isolation: "worktree"`, ONE message: G1 Copy Me (`model: opus`: the hero, roadmap M7a), G2 Flap, G3
   Swat, G4 Freeze (`model: sonnet`). Each checks `git rev-parse --short HEAD` equals BASE first. No cross-imports.
3. Merge G1, G2, G3, G4 with `git -C /Users/trey/dev/codeisart merge --no-ff`, the full suite after each; a merge
   that breaks it is undone with `git revert -m 1` and sent back once. Then I1. I2 is the operator's.
Files by task (no file under two tasks):
- I0: `arcade/bots.py`, `tests/arcade/test_bots.py`.
- G1: `arcade/games/copyme.py`, `copyme_bots.py`, `copyme_feel.toml`, `tests/arcade/test_copyme.py`, `arcade/poses.py`.
- G2, G3, G4, with `<name>` = `flap`, `swat`, `freeze`: `arcade/games/<name>.py`, `<name>_bots.py`,
  `<name>_feel.toml`, `tests/arcade/test_<name>.py`.
- I1: `.claude/skills/arcade-game-authoring/SKILL.md`.
Shared: `arcade/bots.py` (I0). Not edited: `arcade/games/__init__.py` (`MENU_ORDER` has the four names),
`feel_budgets.toml`, `main.py`, `config.py`, `arcade.toml`, `pyproject.toml`, `.gitignore`, `tests/arcade/helpers.py`,
`tests/conftest.py`, `test_oracle.py`, `arcade/figure.py`, `arcade/attract/lobby.py`. `arcade/poses.py` (G1) keeps
`stand`, `arms_up`, `t_pose`: its readers (`sources/actors.py`, `test_actors.py:117`, `test_pose_mediapipe.py`) hold.
## I0: a bot can move both hands and strike a pose (orchestrator)
Why: `Move` (`arcade/bots.py:40`) is one body with one wrist's height (`Person.wrist`, `sources/actors.py:119`, moves a
wrist up and down only), so no bot can flap with both arms (G2) or strike a target pose (G1).
- `Move` gains `pose: str | None = None`, last field. `hand` also takes `"both"`. Docstring says both.
- `_sensed` (`bots.py:124`): with `pose`, the `Person` holds `POSES[pose]` on the tick (`person.pose(move.pose,
  at=t - TICK, seconds=2 * TICK)`); with `wrist_y`, `hand == "both"` moves both wrists to it (one noise draw, as
  today), else the one hand. An unknown pose raises `ValueError` (`Person.pose` does). Nothing else changes: `play`'s
  noise, pacing and stop rule as they are.
- Acceptance (`tests/arcade/test_bots.py`): `test_move_both_hands_moves_both_wrists` (both wrists' reach v equal
  `wrist_y` within 0.02); `test_move_pose_holds_the_named_pose` (`Move(pose="t_pose")`: the body's keypoints are
  `t_pose`'s offsets at its hip centre within 1e-6). Every existing test in the file passes unchanged.
## G1: Copy Me (`copyme`, spec 8 row 1, the hero) (opus, worktree)
Rules: a target pose is a cyan outline in the player's figure rect that grows over `GROW_SECONDS`; each judged limb
within tolerance turns green; at zero a flash, a pop and the round's best frame held. Three rounds, easy to silly.
- `GameInfo(name="copyme", title="COPY ME", verb="COPY", needs={"pose"}, layouts={"128x64"}, players=2,
  exit_gesture=False, kind="score")`, icon a figure inside a dashed outline, 2 px strokes.
  `PHASES = ("ready", "show", "play", "result", "over")`: `ready` until player 1 is in view and `READY_SECONDS`
  passed ("COPY THE SHAPE" at 1x); `show` the target small with its name at 1x; `play` the grow; `result` the frozen
  best frame and the points; `over` holds. `CAPTION_KEYS = ("phase", "round", "target", "score")`.
- Poses (`arcade/poses.py`, same `_pose` helper, legs `_LEGS` unless named): `right_up`, `left_up` (one arm straight
  up, the other as `stand`), `y_pose` (arms up and out at 45 degrees), `flex` (upper arms horizontal, forearms up),
  `airplane` (one arm up-out 45, the other down-out 45), `disco` (right arm up-out 45, left hand on the hip),
  `teapot` (left hand on the hip, right arm out with the forearm up), `star` (`y_pose` arms, feet apart 0.16 each).
  `LADDER = (("arms_up", "t_pose", "right_up", "left_up"), ("y_pose", "flex", "airplane"), ("disco", "teapot",
  "star"))`: round k draws `rng.choice(LADDER[k - 1])`.
- Scoring: segments `LIMBS` = the eight arm and leg segments of `SKELETON` (`sensed.py:22`). An angle is the
  segment's direction with x times `figure.FRAME_ASPECT`, measured from the torso axis (hip_mid to shoulder_mid;
  the frame's vertical without hips), so position, size and a lean do not matter. The target's angles come from its
  POSES offsets placed as `Person` places them (`sources/actors.py:24`). Judged segments: those whose target angle
  differs from `stand`'s by more than `JUDGE_MIN_DEG` (real noise moves a still limb up to 19 degrees); a leg segment
  is judged only when both its keypoints are at `MIN_CONF` or more (legs cropped: upper body only; no ladder pose
  judges a leg today). `score_pose(body, offsets) -> (share, judged, matched)`, a module-level pure function: `share`
  = sum of `min(conf_a, conf_b)` over judged segments within `LIMB_TOLERANCE_DEG`, over the same sum over all judged
  (0 with none seen). Round points `round(100 * share)`, the best share in the last `SCORE_WINDOW` of `play`; that
  tick's held body is the frozen frame.
- Constants: `ROUNDS = 3`, `READY_SECONDS = 1.5`, `SHOW_SECONDS = 1.5`, `GROW_SECONDS = 3.0`, `GROW_FROM = 0.3`,
  `SCORE_WINDOW = 1.0`, `RESULT_SECONDS = 2.0`, `FREEZE_SECONDS = 1.5`, `OVER_SECONDS = 3.0`, `LIMB_TOLERANCE_DEG =
  30.0`, `JUDGE_MIN_DEG = 60.0`, `ACTIVE_DEG = 25.0`, `MATCH_SHARE = 0.75`, `FRESH_SHARE = 0.5`, `WIN_MATCHES = 2`,
  `FIGURE_H = 60`, `HINT_IDLE_SECONDS = 2.0`, `OUTLINE_COLOR = (0, 200, 255)`, `MATCH_COLOR = (0, 200, 0)`.
- Drawn: each seat's figure via its own `KeypointHold(capture_grace(CAMERA_FPS))` and `draw_figure` in
  `PLAYER_COLORS[seat]`, rect `figure_rect(held, (w, FIGURE_H))` with the column backlash; judged segments within
  tolerance redrawn 2 px in `MATCH_COLOR`; the outline 1 px, the target's segments scaled about the rect's hip point
  from `GROW_FROM` to 1. At zero: `fx.flash((255, 255, 255), 0.15)` (checked), `fx.pop(f"+{points}", ...)`, "MATCH!"
  at 2x in `MATCH_COLOR` when share >= `MATCH_SHARE`, else "MISS" at 1x (255, 120, 0) and no flash. Score at 2x top
  left (seat b's top right). `over`: `fx.celebrate(MATCH_COLOR)` on a solo win, else the totals held.
- Movement and scores (C41): a standing body matches no target (every target judges 2 segments or more, none in
  `stand`'s place). A round's points count only if player 1's share was under `FRESH_SHARE` at some tick of that
  round's `show` or `play` (the pose was struck in the round, not held from before). `score` is player 1's total
  (0 to 300). Solo only: `scores.record(score)` once at `over` when a round counted; a game that had a seat b
  records nothing (Q23). `active`: player 1's mean judged-angle error changed by `ACTIVE_DEG` or more within 1 s.
- Seats: both copy the same target in their own rects; a second body takes seat b at the next `show`, a seat b gone
  past the grace leaves at the next. Hint: "STRIKE THE SHAPE" at 1x after `HINT_IDLE_SECONDS` not `active`.
- debug_state: `phase, round, target, score, other` (seat b's total or None), `share, matches, judged, active, hint,
  humans, player_xy` (player 1's head-disc centre, None when not drawn), `player2_xy`.
- Scenarios: `canonical` (2 s empty, walk-up, `raise_hand`; then a walk across the mat 0.2 to 0.8 to 0.5 inside the
  measured 20 s; then each round's `play` cycles every pose of its rung with `Person.pose`, so every round shows green
  limbs, a frozen frame and a pop), `idle_body` (60 s), `nobody` (30 s), `duo` (two Persons cycling the rungs).
- `copyme_feel.toml`: `[fidelity] input = "zone_x"`, `xy = "player_xy"`, `axis = 0`. No budget override.
- Bots: `good`: `reaction_ticks = 6`, `noise = 0.01`, `Move(x=0.5, pose=state["target"])` from `show`, `stand`
  before. `lazy`: `reaction_ticks = 14`, `noise = 0.03`; round 1 it copies, round 2 it stands (a miss), round 3 it
  copies only when the target is `LADDER[2][0]`, else stands: a bot's pose carries no noise, so its win hangs on the
  rng's draw (about 1 seed in 3). `won(state)`: `phase == "over"` and `matches >= WIN_MATCHES`.
- Acceptance (`tests/arcade/test_copyme.py`):
  - `test_registered_and_declared`; `test_new_poses_keep_the_old_three` (17 offsets; the three unchanged; LADDER in).
  - `test_every_target_judges_two_limbs_and_stand_matches_none`: per `LADDER` pose, judged >= 2; stand's share 0.
  - `test_a_body_in_the_target_pose_shares_one`: `Person.pose(name)` at x 0.3 and 0.7, height 0.4 and 0.8: 1.0.
  - `test_a_lean_keeps_the_share`: the target rotated 10 degrees about the hip centre: 1.0.
  - `test_limbs_within_tolerance_turn_green`: a forearm 20 degrees off is drawn in `MATCH_COLOR`, 40 is not.
  - `test_legs_cropped_scores_the_upper_body`: `score_pose` on a test-made target with one leg 70 degrees out and
    the body in it: 1.0; the body's legs standing: under 1; knees and ankles at confidence 0: legs unjudged, 1.0.
  - `test_share_is_weighted_by_confidence`: one judged forearm off at conf 0.4: the share is the weighted value.
  - `test_the_outline_grows_over_three_seconds`: its height `GROW_FROM` of full at `play`'s start, full at 3.0 s.
  - `test_round_k_draws_from_rung_k`: 20 seeds, every round's target in its rung.
  - `test_points_need_a_fresh_pose`: `t_pose` held from `ready` scores 0 on a `t_pose` round; struck from `stand`, 100.
  - `test_the_best_frame_is_frozen_in_result`: `result`'s frames equal for `FREEZE_SECONDS` while the body moves.
  - `test_three_rounds_then_over_and_done_after_the_hold`; `test_exit_gesture_is_off` (`arms_up` 5 s: session on).
  - `test_a_second_player_joins_at_the_next_show_and_the_game_records_nothing`; `test_a_seat_b_who_leaves_is_dropped`.
  - `test_the_figure_column_holds_within_the_slack`: a 1-column jitter keeps `player_xy`'s x; a 2-column step moves it.
  - `test_idle_body_scores_nothing` (score 0, best None, hint within 3 s); `test_a_still_body_under_real_noise_
    scores_nothing` (`degrade(**REAL_NOISE)`, 3 ids, 60 s: `score_pose` against every `LADDER` pose matches no limb
    on any capture; a whole game scores 0 and is never `active`); `test_own_drawing_keeps_the_flash_rule` (canonical,
    duo: raw `concurrent_area` under 0.1, held 0); the template tests (Global Constraints).
## G2: Flap (`flap`, spec 8 row 7) (sonnet, worktree)
Rules: both wrists sweeping from above to below the shoulders within `FLAP_WINDOW` is one flap; the bird rises,
gravity is gentle, gaps are wide; pass gaps; a crash holds and fades. The run survives `RUN_SECONDS` or ends on a crash.
- `GameInfo(name="flap", title="FLAP", verb="FLAP", needs={"pose"}, layouts={"128x64"}, players=1,
  exit_gesture=False, kind="score")` (fast flaps would hold the runner's 3 s exit; guide line 54), icon a bird with
  raised wings. `PHASES = ("ready", "play", "over")`: `ready` holds the bird level at row `READY_Y` until the first
  flap ("FLAP TO FLY" at 1x, least `READY_SECONDS`), the first pipe already standing at the right edge, so `gap_xy`
  is the first gap from tick 1; `over` holds a crash's fade or "SAFE!". `CAPTION_KEYS = ("phase", "score", "runs")`.
- The flap: each wrist read as `body.reach(wrist)`'s v (`sensed.py:215`) when at `MIN_CONF` or more, its last value
  held for `capture_grace(CAMERA_FPS)`; a flap fires on the capture where both wrists are under-line (v over
  `V_BELOW`) and both were over-line (v under `V_ABOVE`) within the last `FLAP_WINDOW` by `camera_t`. One wrist alone
  never flaps. `fx.echo(1, "down")` on the tick.
- The wing gauge: `Cursor` then a `Glide` gives v; a `GAUGE_W` by 2 px marker at the left edge, v `V_TOP .. V_BOTTOM`
  onto rows `GAUGE_TOP .. GAUGE_BOTTOM`, with 3 px ticks at the `V_ABOVE` and `V_BELOW` rows: the player sees the
  lines a flap crosses. The bird's wings are drawn up when the gauge is over `V_ABOVE`.
- Constants: `RUN_SECONDS = 45.0`, `READY_SECONDS = 1.0`, `READY_Y = 30`, `FLAP_WINDOW = 0.4`, `V_ABOVE = 0.40`,
  `V_BELOW = 0.62`, `BIRD_X = 28`, `BIRD_W = 5`, `BIRD_H = 4`, `GRAVITY = 24.0` px/s2, `FLAP_VY = -22.0` px/s (set,
  not added), `MAX_FALL = 30.0` px/s, `PIPE_W = 6`, `GAP_H = (32, 28)` px (linear over the run), `PIPE_EVERY = 3.0`
  s, `SCROLL = 20.0` px/s, `GAP_Y = (14, 44)` (gap centres, rng), `GAP_STEP = 8` px (a gap's centre lies within this
  of the one before), `FLOOR_Y = 59` (touching it crashes; the top clamps), `CRASH_SECONDS = 1.2` (`fx.freeze(0.2)`,
  `fx.shake(2, 0.3)`, the bird red (255, 0, 0) fading to black), `MAX_RUNS = 3`, `OVER_SECONDS = 3.0`, `GAUGE_W = 8`,
  `V_TOP, V_BOTTOM = 0.15, 0.85`, `GAUGE_TOP, GAUGE_BOTTOM = 4, 56`, `HINT_IDLE_SECONDS = 2.0`, `CAMERA_FPS = 10`,
  `SCORE_SCALE = 2`, `BIRD_COLOR = PLAYER_COLORS[0]`, `PIPE_COLOR = (0, 200, 0)`.
- Levers (Global; the review's model: the first draft's good bot won 0 of 200 seeds, lazy 0): `GAP_STEP`, `GAP_H`,
  `GRAVITY`, `FLAP_VY`, `PIPE_EVERY`, the bots' numbers. Not levers: `FLAP_WINDOW`, both wrists, `RUN_SECONDS`.
- Restart (spec): a flap in `over` after a crash starts a new run while `runs < MAX_RUNS`; the best run is recorded.
- Movement and scores (C41): a hanging wrist never reaches `V_ABOVE`, so a still body never flaps: the bird stays
  in `ready` (the runner's inactive rule ends the session). `score` = gaps passed in the run; `scores.record(best
  run)` once, at the last `over`, when a gap was passed. `active`: a flap on this tick or the gauge moved 3 px within
  1 s. `survived`: a run lasted `RUN_SECONDS`.
- debug_state: `phase, score, runs, active, hint, survived, crashed, arms` ("up" while both wrists over-line within
  the window, else "down"), `bird_xy` (the bird's centre), `bird_vy` (px/s, down positive), `gap_xy` (the next
  gap's centre, None past the last), `wing_xy` (the gauge marker's centre), `t_left`.
- Scenarios: `canonical` (2 s empty, walk-up, raise; three slow full sweeps of both wrists 0.1 to 0.95 inside the
  measured 20 s for the gauge; then a flap about every 1.8 s, the level period: the bird hovers past pipes until it
  crashes), `idle_body` (60 s), `nobody` (30 s), `one_arm` (one wrist flapping, 20 s: never flies).
- `flap_feel.toml`: `[fidelity] input = "cursor_y"`, `xy = "wing_xy"`, `axis = 1`. No budget override.
- Bots (`Move(hand="both", wrist_y=...)`, I0): a sweep is both wrists to 0.1, then to 0.95 over 0.25 s. Both sweep
  once in `ready` and whenever `gap_xy` is None, and do nothing in `over`. `good`: `reaction_ticks = 5`, `noise =
  0.02`; in `play` sweeps only while the bird falls (`bird_vy > 0`) and is level with `gap_xy`'s y or under it, one
  sweep at a time. `lazy`: `reaction_ticks = 8`, `noise = 0.05`, only when 5 px under. `won(state)`: `survived`.
- Acceptance (`tests/arcade/test_flap.py`):
  - `test_registered_and_declared`; `test_both_wrists_down_within_the_window_flap` (0.3 s flaps; 0.5 s does not);
  - `test_one_wrist_never_flaps` (`one_arm`); `test_a_flap_sets_the_bird_rising` (vy `FLAP_VY` on the tick, echo);
  - `test_gravity_is_gentle` (from rest: 13 px or less fallen after 1 s); `test_the_gauge_follows_hand_height`;
  - `test_exit_gesture_is_off` (a flap every 0.3 s for 5 s: session on); `test_gap_centres_step_at_most_gap_step`;
  - `test_ready_holds_the_bird_until_the_first_flap`; `test_passing_a_gap_scores_one`;
    `test_a_pipe_or_the_floor_crashes_and_the_top_clamps`;
  - `test_a_crash_holds_and_fades` (`over`; the bird's light only falls over `CRASH_SECONDS`; held 0; raw area < 0.1);
  - `test_a_flap_in_over_restarts_up_to_max_runs`; `test_surviving_the_run_wins_and_done_after_the_hold`;
  - `test_idle_body_scores_nothing`; `test_a_still_body_under_real_noise_never_flaps` (5 seeds); the template tests.
## G3: Swat (`swat`, spec 8 row 8, the effects showcase) (sonnet, worktree)
Rules: 5 px fruit arc up and fall back; a hand's path between ticks cuts them; red bombs cost; 60 s; two cooperate.
- `GameInfo(name="swat", title="SWAT", verb="SWAT", needs={"pose"}, layouts={"128x64"}, players=2, kind="score")`,
  icon a fruit cut by a slash. `PHASES = ("ready", "play", "over")`: `ready` `fx.banner` "3", "2", "1", "GO!" over
  `READY_SECONDS`; `over` holds the total. `CAPTION_KEYS = ("phase", "score", "t_left")`.
- The blade, per seat: `Cursor` then two `Glide`s give (u, v), a `Glide` gives `zone_x`; x = `zone_x` from
  `ZONE_LO..ZONE_HI` onto `-ARM_PX / 4 .. w - 1 + ARM_PX / 4` (either hand reaches both edges), plus `(u - 0.5) *
  ARM_PX`, clamped to the wall; y = v from `V_TOP..V_BOTTOM` onto rows `BLADE_TOP..BLADE_BOTTOM`.
- A cut: the segment from the blade's last tick to this one, at least `CUT_MIN_PX` long, passes within `FRUIT_R + 1`
  px of a fruit's centre (a fast swipe cuts what it crosses even when neither end is on it), while the seat's
  `Cursor` v (not glided) is under `CUT_V_MAX`: a hanging hand (0.95 or more) never cuts, whatever `Cursor`'s u does.
- Constants: `ROUND_SECONDS = 60.0`, `READY_SECONDS = 3.0`, `OVER_SECONDS = 3.0`, `FRUIT_R = 2`, `SPAWN_EVERY = (1.1,
  0.6)` s (linear over the round), `BOMB_SHARE = 0.15`, `LAUNCH_VY = (-53.0, -42.0)` px/s, `DRIFT_VX = (-18.0, 18.0)`,
  `GRAVITY = 30.0` px/s2 (apexes rows 10 to 28), `SPAWN_Y = 57` (a fruit lights rows 55 to 59 there), `BOMB_COST =
  3`, `GOAL = 25`, `CUT_MIN_PX = 3`, `CUT_V_MAX = 0.85`, `ARM_PX = 48`, `ZONE_LO, ZONE_HI = 0.15, 0.85`, `V_TOP,
  V_BOTTOM = 0.15, 0.85`, `BLADE_TOP, BLADE_BOTTOM = 2, 57`, `TRAIL = 4` ticks, `COMBO = 3`, `HINT_IDLE_SECONDS = 2.0`,
  `CAMERA_FPS = 10`, `SCORE_SCALE = 2`, `FRUIT_COLORS = ((0, 200, 0), (255, 200, 0), (0, 200, 255), (255, 0, 255))`,
  `BOMB_COLOR = (255, 0, 0)`.
- Effects (every one keeps the rule alone; the game paces the rest): a cut: `fx.burst` in the fruit's colour (a
  dropped burst is fine) and `fx.pop("+1")`; `COMBO` cuts in one swipe: `fx.pop("COMBO")` and `fx.flash((255, 255,
  255), 0.15)` (checked; no burst on a flash's tick); a bomb: `fx.freeze(0.15)`, `fx.shake(3, 0.3)`, `fx.echo(seat,
  "hit")`, the score drops by `BOMB_COST` (not under 0), never a flash; reaching `GOAL`: `fx.banner("GOAL!")`; `over`:
  `fx.celebrate((0, 200, 0))` when `score >= GOAL`. The blade: a 3x3 block in the seat's colour and a 1 px trail of
  `TRAIL` ticks. Score at 2x top right; a 1 px run bar on row 0 (255, 120, 0).
- Movement and scores (C41): a cut needs a raised hand (`CUT_V_MAX`) swiping `CUT_MIN_PX` a tick; both may only
  tighten. Levers: `GOAL`, `SPAWN_EVERY`, `BOMB_SHARE`, the bots' numbers. `score` = fruit cut minus bomb costs, shared
  by both seats. Solo only: `scores.record(score)` once at `over` when a fruit was cut; with a seat b ever, nothing
  (Q23). `active`: a blade moved `CUT_MIN_PX` this tick with its v under `CUT_V_MAX`. Player 2's blade shows once
  `player2` is seen; a missing seat's fades over its grace.
- debug_state: `phase, score, cut, bombs_hit, active, hint, t_left, blade_xy` (seat a's), `blade2_xy` (or None),
  `target_xy` (the uncut fruit nearest seat a's blade, else None), `bomb_xy` (the nearest bomb, else None).
- Scenarios: `canonical` (2 s empty, walk-up, raise; one slow wrist sweep top to hip and a walk across inside the
  measured 20 s; then fast swipes 0.2 to 0.8 every 0.4 s at the centre for the rest of the round), `idle_body`,
  `nobody`, `duo` (two Persons swiping).
- `swat_feel.toml`: `[fidelity] input = "cursor_y"`, `xy = "blade_xy"`, `axis = 1`. No budget override.
- Bots (`Move(x, wrist_y)`): `good`: `reaction_ticks = 5`, `noise = 0.02`; steps `x` so `blade_xy`'s x meets
  `target_xy`'s and swipes `wrist_y` 0.15 either side of the target's height every 3 ticks; away from `bomb_xy` when
  it is within 8 px. `lazy`: `reaction_ticks = 12`, `noise = 0.05`, swipes every 8 ticks, ignores bombs. `won(state)`:
  `phase == "over"` and `score >= GOAL`.
- Acceptance (`tests/arcade/test_swat.py`):
  - `test_registered_and_declared`; `test_blade_follows_body_and_hand` (zone_x spans the wall; v spans the rows);
  - `test_a_swipe_through_a_fruit_cuts_it` (both ends off the fruit); `test_a_slow_hand_cuts_nothing`;
  - `test_fruit_arcs_up_and_falls_out` (apex rows 8 to 30, gone below row 59, never into rows 60 to 63);
  - `test_a_bomb_costs_shakes_and_never_flashes` (score down 3, floor 0; `fx_` keys show shake and freeze, no flash);
  - `test_a_combo_flashes_once_and_checks_the_return`; `test_each_effect_fires_on_its_event` (runner `fx_` keys);
  - `test_the_round_ends_at_sixty_seconds_and_done_after_the_hold`; `test_two_share_one_score_and_record_nothing`;
  - `test_idle_body_scores_nothing`; `test_a_still_body_under_real_noise_scores_nothing` (5 ids, heights 0.6 and
    0.45: no cut, never `active`); `test_a_hanging_hand_never_cuts` (a 24 px blade jump at v 0.95 over a fruit);
  - `test_own_drawing_keeps_the_flash_rule` (canonical and duo: raw area under 0.1, held 0); the template tests.
## G4: Freeze (`freeze`, spec 8 row 10, pose only) (sonnet, worktree)
Rules: on green everyone dances; on red, anyone still moving after `GRACE` is out and their figure topples; last one
standing. Solo: survive the reds. Keypoint travel by body, no music, no motion grid (Q99).
- `GameInfo(name="freeze", title="FREEZE", verb="FREEZE", needs={"pose"}, layouts={"128x64"}, players=2,
  exit_gesture=False, kind="score")` (a hands-up freeze must not exit), icon a figure and a lamp. `PHASES = ("ready",
  "play", "over")`: `ready` "DANCE ON GREEN" / "FREEZE ON RED" at 1x; `CAPTION_KEYS = ("phase", "light", "score")`.
- Movement by body, per capture (`camera_t` newer): the reach-box (u, v) of each confident wrist and the `zone_x`.
  Travel since an anchor time = the largest of each wrist's u span and v span, and the `zone_x` span over
  `STEP_SCALE`. Moving = travel over `MOVE_TRAVEL` (a span, not a per-tick difference: the tracker smooths, spec 5).
- The light: green for `GREEN_SECONDS` (rng), red for `RED_SECONDS` (rng), `REDS` reds. On red the anchors reset at
  red + `GRACE`; a body whose travel passes `MOVE_TRAVEL` before green is out: `fx.echo(seat, "hit")`, its figure
  topples (the game's own drawing: the held skeleton's segments rotated 90 degrees about its feet over
  `TOPPLE_SECONDS`, `draw_figure` cannot rotate; `player_xy` keeps its last upright place) and fades. A red counts
  for a seat that is still in and danced in the green before it (its travel over that green reached `DANCE_TRAVEL`).
- Shown: a 1 px border (rows 0 and 59, columns 0 and w - 1) in the light's colour, `(0, 200, 0)` or `(255, 0, 0)`,
  and the word, "DANCE" or "FREEZE", at 2x centred on rows 44 to 57 over a black box: red lit area at most
  `RED_AREA = 0.12` of the wall; the light changes once per phase, never blinks; no full-field colour.
  Figures as Copy Me's (`KeypointHold`, `draw_figure`, `figure_rect(held, (w, FIGURE_H))`, `COLUMN_SLACK`).
- Constants: `REDS = 6`, `GREEN_SECONDS = (3.0, 6.0)`, `RED_SECONDS = (2.5, 4.0)`, `GRACE = 0.5`, `MOVE_TRAVEL = 0.25`,
  `DANCE_TRAVEL = 0.5`, `STEP_SCALE = 0.4`, `READY_SECONDS = 3.0`, `TOPPLE_SECONDS = 1.0`, `OVER_SECONDS = 3.0`,
  `WIN_SCORE = 4`, `FIGURE_H = 60`, `HINT_IDLE_SECONDS = 2.0`. `MOVE_TRAVEL` may rise to 0.3, never fall. Levers: the
  bots' numbers, `LAZY_GREEN`, `GREEN_SECONDS`, `RED_SECONDS`. Not levers: `GRACE`, `REDS`.
- Players: solo plays to `REDS` or out; two play to the last one standing or `REDS`. `score` = player 1's counted
  reds; `other` seat b's. Solo only: `scores.record(score)` once at `over` when a red counted; with a seat b, nothing.
  A second body joins on the next green. Leaving: a seat missing past the grace is out without a topple.
- C41: a still body never dances, so no red counts and nothing is stored. `active`: travel over `MOVE_TRAVEL` in 1 s.
- debug_state: `phase, light, score, other, out, out2, danced, reds_left, in_grace, active, hint, player_xy` (the head
  disc's centre, None when not drawn), `player2_xy`.
- Scenarios: `canonical` (2 s empty, walk-up, raise; a walk across the mat inside the measured 20 s; then arm waves
  and steps; a script cannot read the rng's lights, so it dances 2 s and holds 3 s in turn and some reds catch it
  moving: the sheet shows an out), `idle_body`, `nobody`, `duo` (one dancer who freezes, one who keeps dancing).
- `freeze_feel.toml`: `[fidelity] input = "zone_x"`, `xy = "player_xy"`, `axis = 0`. No budget override.
- Bots (`Move(x, wrist_y)`): `good`: `reaction_ticks = 6`, `noise = 0.005`; on green sways `x` 0.1 and swings
  `wrist_y` 0.2 to 0.8 every 0.3 s; on red holds `x` and drops the hand (`wrist_y=None`). `lazy`: `reaction_ticks =
  10`, `noise = 0.01` (0.02 alone is out on 39 percent of reds), the same dance; its one mistake hangs on the rng: it
  dances 1 s into the first red only when the first green lasted over `LAZY_GREEN = 4.5` s (it counts the green's
  ticks: about half the seeds). `won(state)`: `phase == "over"`, `out` False and `score >= WIN_SCORE`.
- Acceptance (`tests/arcade/test_freeze.py`):
  - `test_registered_and_declared`; `test_the_lights_follow_the_rng_plan` (each span in its range; `REDS` reds);
  - `test_moving_after_the_grace_is_out`; `test_moving_inside_the_grace_is_not_out`;
  - `test_a_still_body_under_real_noise_is_never_out` (5 seeds, through every red);
  - `test_a_red_counts_only_after_a_dance`; `test_an_out_figure_topples_and_fades` (held 0, raw area < 0.1);
  - `test_the_red_light_keeps_its_area` (red lit share <= `RED_AREA`; one change per light);
  - `test_last_one_standing_with_two_and_nothing_recorded`; `test_a_solo_who_survives_wins_and_done_after_the_hold`;
  - `test_exit_gesture_is_off` (both hands up 5 s: session on); `test_idle_body_scores_nothing`; the template tests.
## Decisions taken
- No engine or `arcade/figure.py` change: the column backlash stays in each game; moving it into `figure.py` is a
  later one-owner task. Copy Me's figure follows `zone_x` (the lobby's mirror), so fidelity and range are measured.
- Copy Me, Swat, Freeze take 1 or 2 (`GameInfo.players` allows no more); Flap 1; bests for solo only. Flap's gauge is
  its measured control; Freeze's light is a border and a word; "keypoint speed" is a travel span per capture.
- Owner questions Q104 to Q113 (the writer's report) and Q114 to Q116 (the review's fixes), each defaulted.
- Cut order (a game that cannot pass is not merged; its worktree is kept): G3 Swat, G4 Freeze, G2 Flap, G1 last.
## I1 (orchestrator, after the merges)
- The suite once with `--durations=25`: passes, 3 skips, at most 540 s (expected about 440); over it, the cut order.
- The guide gains: `Move(hand="both")`, `Move(pose=...)` (section 4); the column backlash (6); a gesture's gauge (5).
## I2 (the operator's, in verify)
- `tools/arcade_evidence.py --iteration 19 --games changed`: `games.md` every budget "yes", no override. Sheets:
  each invite and ready; Copy Me's outline growing over the figure, green limbs, a frozen frame, "+N"; Flap's gauge,
  flight, a crash fading; Swat's arcs, a cut's burst, a bomb, the trail; Freeze's two borders and a topple; the cards.
