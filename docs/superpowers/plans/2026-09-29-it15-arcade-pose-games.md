# Iteration 15 (arcade lane): the tracker's two faults, the duplicate pose, Quick Draw and Dodge
BASE: HEAD at the spawn. Carried fixes C45, C46, C47; M7a's first games. Thin plan. Not a safety slice.
"Spec" = `docs/superpowers/specs/2026-09-26-wall-arcade-design.md`, not edited. The run's last iteration: what
ships is whole; a game half built is dropped (see "Cut order"), never merged. `arcade/flash.py`,
`arcade/brightness.py`, `show/display/colorlight.py`, `arcade/runner.py` and the order limiter, governor, push are
untouched. Nothing under `show/`, `tools/show_*`, `deploy/`, no `tests/test_wall*.py`: that is the show lane's.

## Global Constraints
- Test command, from the checkout's (or worktree's) root: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
  /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs`. At the base: 1231 collected, 1 skip, about 235 s.
- Touch only your task's files. Never `cd`: absolute paths and `git -C` (in a worktree: plain git from its root).
  No command over 10 minutes. Test-first (superpowers:test-driven-development). No removed or weakened assert; no
  band in `arcade/feel_budgets.toml` or a `*_feel.toml` loosened. An assert this plan does not name that would
  have to change: stop and report it.
- The frozen protocol (`game-protocol-v1`) is unchanged: `test_protocol_members_are_the_frozen_set` is not edited
  and passes; `SessionResult` is not touched. `Body` gains two defaulted fields (E1); `Sensed` does not change.
- Every call that builds `Sensed` or `Audio` uses keywords. Colours saturated, low channels at 0, no dark greys.
  Seeds from `zlib.crc32`, printed in messages. CPU timing with `time.thread_time`. No game pushes or saves.
- Flash (C24, the game guide section 6): each game keeps the governor's held ticks at 0 and `flash_area_raw`
  (raw `concurrent_area`) under 0.1 on its own frames; no reversing stripes over a quarter of the wall; a loss holds
  and fades, never strobes. The generic tests in `tests/arcade/test_all_games.py` assert it; nothing skips them.
- C46: a game that points with a hand reads `arcade.input.Cursor` then a `Glide`, never `Body.cursor`. This
  binds Quick Draw (G1). Dodge (G2) reads `zone_x` through a `Glide`, never raw.
- A still body scores nothing and banks no best (C41, C42): each game's rule below says what counts as movement.
- Pong's `response_px` is exactly 12.0 on its floor. E1 must leave every number of Pong's row in
  `evidence/it09/games.md` equal (see E1's check). No change to `Glide`, `DEPTH_SPAN`, Pong's scripts or timing.
- Suite time: at most 330 s after this iteration. Shares: I0 0 s, E1 +3 s, E2 +1 s, G1 +42 s, G2 +47 s (each
  game: its oracle report about 25 to 34 s, the soak 12 s, its own tests at most 6 s). Say in your report what
  yours added (`--durations=15` on your files alone).
- A finding outside your task goes in your final message, not in code.

## Lanes and merge order
1. I0, orchestrator, main checkout: `tests/arcade/helpers.py`, `tests/arcade/test_oracle.py`. Committed first.
2. SERIAL, main checkout, `model: opus`, one at a time, each committed before the next: E1, then E2. No game task
   is in flight while they run (engine files, Loop rule 6). E2 runs in the main checkout (the pose model's files
   are not in git), though none of its tests loads the model.
3. PARALLEL, `isolation: "worktree"` from the local HEAD after E2, launched in ONE message, `model: sonnet`:
   G1 (Quick Draw), G2 (Dodge). Neither imports what the other builds. Neither needs the camera or the model.
4. Merge G1, then G2, the suite after each; then I1. I2 is the operator's, in verify.

Files by task (no file under two tasks):
- I0: `tests/arcade/helpers.py`, `tests/arcade/test_oracle.py`.
- E1: `arcade/sensed.py`, `arcade/sources/camera.py`, `arcade/input.py`, `tests/arcade/test_sensed.py`,
  `tests/arcade/test_camera.py`, `tests/arcade/test_input.py`, `tests/arcade/test_pong.py` (one test added).
- E2: `arcade/sources/pose_mediapipe.py`, `tests/arcade/test_pose_mediapipe.py`.
- G1: `arcade/games/quickdraw.py`, `quickdraw_bots.py`, `quickdraw_feel.toml`, `tests/arcade/test_quickdraw.py`.
- G2: `arcade/games/dodge.py`, `dodge_bots.py`, `dodge_feel.toml`, `tests/arcade/test_dodge.py`.
- I1: `.claude/skills/arcade-game-authoring/SKILL.md` (one line on `Body.measured`); the merges and the suite.

Shared files not edited by anyone: `arcade/games/__init__.py` (`quickdraw` and `dodge` are already in
`MENU_ORDER`), `arcade/bots.py`, `arcade/feel_budgets.toml`, `arcade/config.py`, `arcade.toml`, `tests/conftest.py`.

## I0: the oracle judges every game (orchestrator)
- `tests/arcade/helpers.py` gains, moved from `test_oracle.py` unchanged: `PLAYS: dict[tuple[str, str, int, str],
  bots.Play]`, `play_key(game_cls, bot_name, seed, layout=None)`, and `played(game_cls, bot_name, seed) -> Play`
  (the plain play from `PLAYS`, else `bots.play` with the game's own bot, stored). `test_oracle.py` imports
  `PLAYS` and `play_key` from helpers under the same names, so `test_pong.py`'s `oracle.PLAYS` reads the same dict,
  and its `shared_plays` memo stores there. Plays are then shared whichever test file sorts first
  (`test_dodge` sorts before `test_oracle`).
- `test_oracle.py` gains, for every game of `all_games()` but Pong (Pong's three tests stay as they are):
  `test_feel_meets_its_budgets[<name>]` (marked `feel`: `report(...)["failures"] == []`, seeds printed) and
  `test_bots_rank[<name>]` (`win_good > win_lazy > win_none`, `phases_reached == 1.0`), one 20-seed report per
  game per module (a module-level dict). With no game but Pong registered, both collect nothing.
- Acceptance: the suite passes with the same count plus 0; `test_pong.py` alone and after `test_oracle.py` passes.

## E1: the tracker says "measured" and holds the torso (C47, C46) (opus, main checkout)
Measured (probe, the spike's proportions, a still body born without hips, hips from 1 s): the tracker's scale
goes 0.24, 0.335, 0.370, 0.383, 0.387 (the SCALE_TAU ramp over four captures); Depth's value jumps 0.777 and
Pong's paddle travels 24.0 px (the 14.4 that counts).
- `arcade/sensed.py`, `Body` gains two fields, both after `seen_ago`, both defaulted so every actor, bot and
  scripted body reads exactly as today:
  - `measured: bool = True`: the scale is this person's measure. The tracker passes False while a track has
    never been seen with its nose and a hip (its scale is the shoulder fallback). A body built elsewhere is True.
  - `torso_per_width: float = 0.0`: this person's torso per shoulder width, learned by the tracker; a value that
    is not finite or not over 0 reads as 0.0 (as keypoints are cleaned, nothing raises).
  - `Body.torso` without hips: `(torso_per_width or TORSO_PER_SHOULDER_WIDTH) * shoulder_width`. `reach()`'s
    width fallback divides by the same ratio. `raise_line`, `reach` and `cursor` follow from `torso` (Q74).
- `arcade/sources/camera.py`:
  - `_Track.torso_per_width: float = 0.0`, learned in `_learn` from a measured capture with both shoulders as
    `raw.torso / raw.shoulder_width`: the first at once, then smoothed by `RATIO_TAU`, as `per_width` is.
  - `_refresh`: on the capture a track is first measured (`tr.measured` False before, `_measured(raw)` now), the
    scale takes the measured reading at once, not through `SCALE_TAU`: the jump is one capture, not four.
  - `_body` passes `measured=tr.measured` and `torso_per_width=tr.torso_per_width`.
- `arcade/input.py`, `Depth`: remembers whether the capture its centre came from was measured. On the first
  capture after `reset()` whose body is `measured` when the earlier ones were not, it takes a new centre:
  `scale0` moves so this capture reads the value the last capture read (`self.raw`), and the pinned clock
  restarts. So that jump is no travel and no `active`. Once per `reset()`; a body always measured never takes it.
  No new constant. Docstring says so (C47).
- Acceptance tests (one line each on what they assert):
  - `test_sensed.py::test_body_defaults_are_measured_with_the_default_torso`: `Body(...)` has `measured` True,
    `torso_per_width` 0.0, and `torso`, `reach`, `raise_line` equal to today's on the file's existing bodies.
  - `test_sensed.py::test_torso_without_hips_uses_the_learned_ratio`: ratio 2.03 and width 0.128 give torso 0.26
    (the spike's measure); a raised wrist 0.2 above the shoulders reads v over 0.05, not 0.
  - `test_sensed.py::test_a_bad_torso_ratio_reads_the_default`: NaN, -1, inf read as 0.0.
  - `test_camera.py::test_a_track_born_without_hips_is_measured_once_its_hips_are_seen`: False on the captures
    without hips, True from the first with them, still True through a later hip dropout.
  - `test_camera.py::test_the_first_measure_is_taken_at_once`: that capture's scale is the measure within 1
    percent; `test_tracker_scale_follows_a_step_within_three_captures` passes unchanged (a measured track smooths).
  - `test_camera.py::test_the_tracker_learns_the_torso_per_width`: `spike_det()` gives the ratio of its torso to
    its width within 2 percent; a never-measured track passes 0.0.
  - `test_camera.py::test_a_raised_hand_stays_in_the_reach_box_through_a_hip_dropout`: spike proportions, wrist
    0.2 above the shoulders, 1 s with hips then 1 s without: `Cursor` v never 0 and moves under 0.05.
  - `test_camera.py::test_depth_reads_steady_when_a_track_born_without_hips_is_measured`: the probe above through
    the tracker and a `Depth`: every value after the hips arrive within 0.05 of the value before.
  - `test_input.py::test_depth_takes_a_new_centre_when_its_body_is_first_measured`: unmeasured bodies at scale
    s, then measured at 1.6 s: the value stays within 0.01; a step after it still moves the value as before.
  - `test_input.py::test_depth_takes_the_new_centre_once_per_reset`: measured, unmeasured, measured again at a
    new scale moves the value (a real step); after `reset()` the rule arms again.
  - `test_pong.py::test_a_still_body_born_without_hips_banks_nothing`: tracker bodies (spike proportions, hips
    from 1 s) as Pong's player, 30 s: travel under `travel_px`, no point for the human, no best stored.
- Check for Pong (the implementer runs both, in the report): `pytest tests/arcade/test_oracle.py tests/arcade/
  test_pong.py -p no:cacheprovider`, and `feel.report(Pong, "128x64", seeds=bots.seeds(Pong, "128x64", 20))`
  printed: response_ticks 1.0, response_px 12.0, fidelity 0.9947, range 0.6287, win_good 1.0, win_lazy 0.25,
  win_none 0.0, round_seconds 66.0667 (evidence/it09/games.md). Actor bodies take no new path, so these are
  equal, not merely in band; any difference is a defect to find, not a band to read.

## E2: one person, one pose; the hand point (C45, the spike's hand) (opus, main checkout)
- `arcade/sources/pose_mediapipe.py`:
  - `DUP_DISTANCE = 0.04`: frame units. The spike's duplicates put the noses 0.01 to 0.02 apart; two people
    shoulder to shoulder put them one shoulder width apart, 0.13 at 2 m (the spike's) and about 0.09 at 3 m.
  - `merge_duplicates(detections: list[tuple[Box, tuple[Keypoint, ...]]], near: float = DUP_DISTANCE) ->
    list[...]`: two poses are one person when the nose and both shoulders are confident (`MIN_CONF`) in both and
    each pair lies within `near`. Of the two, keep the one whose hips have the higher mean confidence (a tie keeps
    the earlier). A pose without a confident nose or both shoulders is never merged. Order otherwise kept.
  - `step()` calls it between building the detections and `tracker.update`.
  - The hand point: `HAND_LANDMARKS = {9: (15, 17, 19), 10: (16, 18, 20)}` (COCO wrist index: MediaPipe wrist,
    pinky, index). `landmarks_to_keypoints` puts each wrist at the mean x, y of its three landmarks; the
    confidence stays the wrist's visibility. The spike: spikes 6 to 1 percent at 2 m.
- Not changed: `NUM_POSES` (2), `CAPTURE_SIZE`, the thresholds, `arcade/main.py`'s `MODEL_PATH` (Q73), any config.
- Acceptance tests (`tests/arcade/test_pose_mediapipe.py`, a fake landmarker, no model):
  - `test_duplicate_poses_are_merged_keeping_the_more_confident_hips`: two copies 0.015 apart, hips 0.9 and 0.2:
    one detection out, the 0.9 one.
  - `test_two_people_shoulder_to_shoulder_are_never_merged`: two actors' keypoints side by side, shoulders
    touching, at the zone's smallest body (3 m) and at 2 m: two detections out.
  - `test_a_child_in_front_of_an_adult_is_never_merged`: noses 0.03 apart in x, shoulders 0.1 apart in y: two.
  - `test_a_pose_without_a_nose_or_a_shoulder_is_never_merged`: two copies, one shoulder under `MIN_CONF`: two.
  - `test_step_gives_one_body_for_a_doubled_pose`: `MediaPipeCamera` with a fake landmarker returning the same
    person twice 0.01 apart for 20 captures: every result has one body, one id.
  - `test_the_wrist_is_the_mean_of_wrist_pinky_and_index`: the keypoint's x, y are the mean; its conf the wrist's.

## G1: Quick Draw (`quickdraw`, spec 8 game 4) (sonnet, worktree)
Rules: hands low; "WAIT" for a random 2 to 5 s (Q71); then "DRAW!"; the first hand up wins the round; a hand up
during WAIT loses it ("TOO SOON"). First to 3 rounds (best of five). Solo plays a CPU gunslinger (green, in seat
b); a second body joins at the next round's `ready` and takes seat b with its rounds (Pong's seat rule). At 2 to
3 m the player sees one bar per seat, their hand's height; the draw is the bar crossing the line.
- `GameInfo(name="quickdraw", title="DRAW!", verb="DRAW", needs={"pose"}, layouts={"128x64"}, players=2,
  kind="score")`, icon a 16x16 hand and line, 2 px strokes. `PHASES = ("ready", "play", "result", "over")`:
  `ready` waits until every human bar is below the line (text "HANDS DOWN" at 1x); `play` holds WAIT then DRAW
  (key `signal`: "wait" or "draw"); `result` shows the round; `over` holds the match.
  `CAPTION_KEYS = ("phase", "signal", "left", "right")`.
- Control: each human seat has `Cursor(grace=capture_grace(CAMERA_FPS))` then `Glide`; the bar's y maps the reach
  box's v from `V_TOP = 0.25` to `V_BOTTOM = 0.75` onto `BAR_TOP = 16` to `BAR_BOTTOM = 56` (clamped). The line
  is at v `DRAW_V = 0.45` (a hand at shoulder height, v 0.51, is below it): `line_y = 32`.
- Constants: `WIN_ROUNDS = 3`, `WAIT_SECONDS = (2.0, 5.0)` (rng.uniform), `READY_SECONDS = 1.0` (least),
  `DRAW_TIMEOUT = 1.5` (nobody drew: the CPU's round in solo, a void round in a duel), `CPU_DRAW = (0.40, 0.70)` s
  (rng.uniform per round), `RESULT_SECONDS = 1.5`, `OVER_SECONDS = 2.5`, `ARM_PX = 6` (a bar counts as drawn
  only after it sat at least this far below the line during this round's `play`), `ACTIVE_PX = 3`,
  `HINT_IDLE_SECONDS = 2.0`, `CAMERA_FPS = 10`, `BAR_W = 12`, `BAR_H = 3`, `SCORE_SCALE = 2`.
- Drawn: seat a's bar centred at x = w/8, seat b's at 7w/8, in the player's colour (`PLAYER_COLORS`) or
  `CPU_COLOR = (0, 200, 0)`; the line: two 4 px ticks either side of each bar at `line_y`, `LINE_COLOR = (255,
  120, 0)`. Rounds won at 2x, top row y 1, centred on w/4 and 3w/4. Centre text at 2x: "WAIT" (255, 120, 0),
  "DRAW!" (255, 255, 255) with one `fx.flash((255, 255, 255), 0.15)` (check its return), the winner's time
  ("0.31") at 1x under it in `result`. A win: `fx.burst` on the winner's bar and `fx.echo`; "TOO SOON" at 1x in
  (255, 0, 0) over the loser's half. `over`: the result held, `fx.celebrate` for a solo win, no strobe. The
  bottom rows 60 to 63 stay free (the runner's marker). Hint (key `hint`): "HAND UP ON DRAW!" at 1x, faded in
  0.3 s, when a human's bar has not moved `ACTIVE_PX` for `HINT_IDLE_SECONDS`.
- Movement and scores (C41): a draw is a crossing after `ARM_PX` below, so a still hand never draws; a still
  body loses every round to the CPU's draw. `active` is True on a tick a human bar moved `ACTIVE_PX` from its
  anchor (Pong's rule). `score` is player 1's rounds won. Solo only: `scores.record(rounds)` once, at `over`, when
  player 1 won a round by a draw (Q72); a game that ever had a human in seat b records nothing (Q23).
- Leaving: a human missing longer than the grace gives the seat to the CPU at the next `ready` (rounds kept);
  player 1 leaving ends the session by the runner's rule. `update` may stop at any tick.
- debug_state: `phase, signal, round, score, left, right, cpu ("left"/"right"/None), humans, active, hint, hand_xy`
  (player 1's bar centre), `left_xy`, `right_xy` (bars), `wait_left` (s until DRAW, for bots only while
  `signal == "draw"` is False, rounded to 0.1), `react` (the last winner's time, s, or None).
- Scenarios: `canonical` (2 s empty, walk-up, `raise_hand`, lower, then five rounds: the wrist swept from hip
  to top and back once in `ready` so fidelity and range see the whole bar travel, and drawn 0.3 s after each
  DRAW by the script's own timing, about 60 s); `idle_body` (60 s, hand down); `nobody` (30 s); `duel` (two
  Persons, one each side, both drawing, 50 s); `early` (a hand up in WAIT, 20 s).
- `quickdraw_feel.toml`: `[fidelity] input = "cursor_y"`, `xy = "hand_xy"`, `axis = 1`. No budget override.
- Bots (`quickdraw_bots.py`, `wrist_y` 1.0 is hands down, 0.1 is drawn): `good`: `reaction_ticks = 6`,
  `noise = 0.02`, draws when `signal == "draw"`, lowers in `ready`. `lazy`: `reaction_ticks = 14`, `noise =
  0.05`, and on rounds with `round % 4 == 2` draws early (when `wait_left` is under 0.5). `won(state)`:
  `phase == "over"` and player 1's rounds (`score`) exceed the other seat's. Starting values: tune the game's
  `CPU_DRAW` and the bots inside the bands, never a band.
- Acceptance tests (`tests/arcade/test_quickdraw.py`, Pong's template; bots through `helpers.played`):
  - `test_registered_and_declared`: info, `PHASES`, `CAPTION_KEYS`, `GAME`, in `MENU_ORDER`.
  - `test_bar_follows_hand_height`: the wrist from hip to top moves the bar from `BAR_BOTTOM` to `BAR_TOP`.
  - `test_first_draw_after_the_signal_wins_the_round`: a draw 0.3 s after DRAW beats a CPU at 0.4 s or more.
  - `test_a_hand_up_during_wait_loses_the_round`: "TOO SOON", the other seat's round.
  - `test_ready_waits_for_hands_down`: a hand up at launch holds `ready`; lowered, `play` starts.
  - `test_first_to_three_ends_the_match_and_done_after_the_hold`: `over`, `score` kept through `OVER_SECONDS`.
  - `test_idle_body_scores_nothing`: `idle_body`: score 0, `scores.best` None, `hint` within 3 s.
  - `test_a_still_body_under_real_noise_never_draws`: `degrade(**REAL_NOISE)`, 5 seeds: no draw, no best.
  - `test_duel_first_hand_wins_and_records_nothing`: `duel` reaches `over`; `scores.best` stays None.
  - `test_a_second_player_takes_the_cpu_seat_at_the_next_round`: rounds kept, `cpu` None after.
  - `test_a_player_who_leaves_gives_the_seat_to_the_cpu`: player 2 leaves mid-match; the CPU draws for seat b.
  - `test_debug_state_is_clean`: no reserved key, `active` a bool, every `_xy` lit, inside the wall.
  - `test_required_scenarios_start_with_an_empty_wall`, `test_canonical_drives_the_lobby_to_quickdraw`,
    `test_bots_module_is_found`, `test_good_beats_lazy_beats_nobody` (5 seeds, from `played`),
    `test_good_round_length_in_band`, `test_feel_file_overrides_have_reasons`, `test_seeded_runs_repeat`.
- Expected: good plays about 24 s (3 to 4 rounds of about 6.4 s and the hold), the oracle about 25 s.

## G2: Dodge (`dodge`, spec 8 game 5, side steps only: Q70) (sonnet, worktree)
Rules: rocks fall; step left and right to stay out from under them; the speed ramps; a run ends on the first hit
or survives `RUN_SECONDS`. At 2 to 3 m the player sees their block on the bottom band and the rocks above it;
the whole body is the control, so it reads in any light the tracker reads the shoulders in.
- `GameInfo(name="dodge", title="DODGE", verb="DODGE", needs={"pose"}, layouts={"128x64"}, players=1,
  kind="score")`, icon a block under two falling blocks. `PHASES = ("ready", "play", "hit", "over")`:
  `ready` 2 s "STEP SIDE TO SIDE" at 1x (two lines); `play`; `hit` the hit-stop and the fade; `over` holds.
  `CAPTION_KEYS = ("phase", "score", "speed")`.
- Control: `zone_x` through a `Glide` (by `sensed.camera_t`), mapped from `ZONE_LO = 0.15` .. `ZONE_HI = 0.85`
  to x 0 .. w - `PLAYER_W`, clamped (the middle of the mat reaches both walls).
- Constants: `RUN_SECONDS = 45.0`, `PLAYER_W = 6`, `PLAYER_H = 8` (rows 50 to 57; a 1 px step changes 16 px),
  `ROCK_W = 6`, `ROCK_H = 4`, `ROCK_SPEED = (20.0, 48.0)` px/s (linear over the run), `SPAWN_EVERY = (1.2,
  0.5)` s (linear), `AIM_EVERY = 3` (every third rock falls at the player's x at its spawn), `HIT_SLACK = 2` (each
  box shrunk 2 px before the overlap test), `DODGE_TRAVEL_PX = 12` (a rock that passes counts only if the
  player's x span since its spawn was at least this), `ACTIVE_PX = 3`, `HIT_SECONDS = 0.6` (`fx.freeze(0.2)`,
  `fx.shake(3, 0.3)`), `OVER_SECONDS = 2.5`, `HINT_IDLE_SECONDS = 2.0`, `SCORE_SCALE = 2`.
- Drawn: the player's block in `PLAYER_COLORS[0]`; rocks in `ROCK_COLOR = (0, 200, 255)`; score (rocks dodged)
  at 2x top right, y 1; a thin run bar on row 0 shrinking as time passes, (255, 120, 0). A hit: the block turns
  (255, 0, 0) and fades over `HIT_SECONDS`, no blink; surviving: `fx.celebrate((0, 200, 0))`, "SAFE!" at 2x.
  Rows 60 to 63 free. Hint "STEP!" at 1x over the player when it has not moved `ACTIVE_PX` for 2 s.
- Movement and scores (C41): with `AIM_EVERY` a still body is hit within about 4 s, and a passed rock counts
  only with `DODGE_TRAVEL_PX` of travel, so `idle_body` scores 0 and stores no best. `score` is rocks dodged.
  `scores.record(score)` once at `over`, only when the run counted a dodge. `active`: the block moved `ACTIVE_PX`.
- Leaving: nobody in view holds the rocks' fall for the grace, then the run goes on (the runner ends the session
  on its leave rule); `update` may stop at any tick.
- debug_state: `phase, score, active, hint, speed, survived, player_xy` (block centre), `threat_xy` (the
  lowest rock whose columns overlap the block's widened by 4 px, else None), `t_left`.
- Scenarios: `canonical` (2 s empty, walk-up, raise, then about 50 s stepping: a sweep across the whole mat
  first, so fidelity and range see it, then steps out from under the aimed rocks by script timing); `idle_body`
  (60 s); `nobody` (30 s); `solo` (a scripted run to a hit).
- `dodge_feel.toml`: `[fidelity] input = "zone_x"`, `xy = "player_xy"`, `axis = 0`. No budget override.
- Bots (`dodge_bots.py`): `good`: `reaction_ticks = 5`, `noise = 0.02`; when `threat_xy` is within 10 px of the
  block and above row 44, steps 0.25 of the zone to the side with more room. `lazy`: `reaction_ticks = 12`,
  `noise = 0.06`, steps only 0.12 and only when the threat is above row 38. `won(state)`: `state["survived"]`.
- Acceptance tests (`tests/arcade/test_dodge.py`):
  - `test_registered_and_declared`; `test_block_follows_zone_x` (0.15 to 0.85 spans the wall, clamped past).
  - `test_a_rock_on_the_block_ends_the_run` (with `HIT_SLACK`: a 2 px graze is no hit; 3 px is).
  - `test_an_aimed_rock_falls_at_the_player` (every third spawn, at the block's x then).
  - `test_speed_and_spawns_ramp` (start and end values at 0 s and 45 s).
  - `test_surviving_the_run_wins_and_done_after_the_hold`; `test_score_counts_dodges_with_travel`.
  - `test_idle_body_scores_nothing` (score 0, best None, hint within 3 s);
    `test_a_still_body_under_real_noise_scores_nothing` (5 seeds).
  - `test_a_player_who_leaves_ends_nothing_by_itself` (the game keeps state; no exception; `done()` False).
  - `test_debug_state_is_clean`, `test_required_scenarios_start_with_an_empty_wall`,
    `test_canonical_drives_the_lobby_to_dodge`, `test_bots_module_is_found`, `test_good_beats_lazy_beats_nobody`
    (5 seeds, from `played`), `test_good_round_length_in_band`, `test_feel_file_overrides_have_reasons`,
    `test_seeded_runs_repeat`.
- Expected: good plays about 49 s, lazy about 25 s, the oracle about 32 s.

## Existing asserts that change
None. E1's fields default to today's behaviour; the snap touches only a track born without hips and later
measured, which no existing test builds. The variant that changes Pong's travel rule (subtracting the jump) is
not taken: it would change `test_pong.py`'s travel asserts.

## Decisions taken
- Two games, Quick Draw and Dodge. Copy Me waits (figure_rect's column slack, the pose ladder, M effort).
- C47: the tracker says `measured` on `Body`; `Depth` keeps its output across the first measure (Q75).
- C46: a learned torso per shoulder width on `Body` (the spike's "last measured torso", following steps).
- C45: nose and both shoulders within 0.04, the more confident hips kept; no model in the tests.
- The hand point (spike) lands with E2; the model stays lite and `camera_fps` stays 10 (Q44 needs `runner.py`).

## Questions for the owner (the loop takes each default at once)
- Q70: Dodge ships with side steps under falling rocks (body x); the spec's jump and duck wait for a bot `Move`
  with a body's height and a level-camera baseline. Default: yes, side steps only in it15.
- Q71: Quick Draw's WAIT is 2 to 5 s (spec: 2 to 6), for pace and the suite's time. Default: yes.
- Q72: Quick Draw's solo score and best are rounds won (0 to 3); the fastest draw shows in `result` only.
  "Chases the night's fastest" needs a lower-is-better best, which `Scores` does not have. Default: yes.
- Q73: The pose model moves from lite to full (the spike: 0.3 px still jitter against 1.3) with `camera_fps`
  30 and the graces in seconds, together, in a later iteration. Default: not in it15.
- Q74: The learned torso also moves the raise line without hips (0.3 torso above the shoulders: about 0.03 of
  the frame higher on the owner). Default: yes, one torso for all.
- Q75: At the first measure `Depth` keeps the paddle where it is (no jump) rather than recentring to 0.5.
  Default: keep it where it is.

## Cut order (if the orchestrator runs out of time, or I1's suite is over 330 s)
1. G2, Dodge (not merged; its worktree kept for the next run).
2. G1, Quick Draw.
3. E2's hand point (the mean of three landmarks); C45's merge stays.
4. E2 whole (C45). E1 (C47, C46) is cut last.

## I1 (orchestrator, after the merges)
- The full suite once with `--durations=25`: passes, 1 skip; the time at most 330 s (expected about 330: 235 +
  E1 3 + E2 1 + G1 42 + G2 47). Over it: the cut order's step 1.
- One line in the game guide's Controls: `Body.measured` and that `Depth` takes the first measure without a jump.

## I2 (the operator's, in verify)
- `.venv/bin/python -m tools.arcade_evidence --iteration 15 --games quickdraw,dodge,pong --seeds 20`: must write
  `feel.json`, `games.md`, and per game the plain, led and distance PNGs, the canonical GIF, trace and timeline.
  `games.md`: every budget "yes" for quickdraw and dodge, no override; Pong's row not worse than it09's
  (response_ticks 1.0, response_px 12.0, fidelity 0.9947, range 0.6287, lit 0.039, dim 0.1147, liveliness
  0.0035, flash_area_raw 0.0, square_flashes 0.0, score_visible 1.0, score_legible 1.0, win_good 1.0,
  win_lazy 0.25, win_none 0.0, round_seconds 66.07, phases_reached 1.0).
- `.venv/bin/python -m tools.arcade_shot quickdraw --lobby small --scenario canonical --raw-vs-pushed`, and the
  same for `dodge`: the bars, the line, the rocks and the 2x scores read in the led and distance sheets.
- `.venv/bin/python -m arcade doctor`: as `evidence/it09/doctor.txt`, no new failure.
- The suite: the count, 1 skip, the time (at most 330 s).
