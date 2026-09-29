# Iteration 9: Pong by the body (M4c), and C42, C43, C44
Base 353359f. Roadmap M4c (owner decision Q42: "yes, do it now as iteration 9"). Carried C42, C43, C44. Owner
decisions applied: Q35 (by travel, C42), Q40 (the fast ball goes back toward Q34's numbers), Q41 (C43), Q42.
Thin plan (Loop rule 1). "Spec" = `docs/superpowers/specs/2026-09-26-wall-arcade-design.md`, not edited.
SAFETY SLICE: no. `arcade/flash.py`, `arcade/brightness.py`, `show/display/colorlight.py` and the runner's order
(limiter, governor, push) are untouched. The runner gains one field on `SessionResult` and one read of the scores.

## Global Constraints
- Test command, from the checkout's (or worktree's) root: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
  /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs`. At 353359f: 723 collected; it08's run 140 s.
- Touch only your task's files. Never `cd`: absolute paths and `git -C` (in a worktree: plain git from its root,
  one command per call). No command over 10 minutes. Test-first (superpowers:test-driven-development); write the
  code yourself. No removed or weakened asserts. The only changed asserts are those under "Changed asserts";
  any other: stop and report it.
- Every call that builds `Sensed` or `Audio` uses keywords (C21). Every frame reaches the display only through the
  runner; no game, lobby, bot or metric pushes or saves images.
- Colours saturated, low channels at 0. No game or lobby code knows which machine it runs on. Timing tests time
  CPU (`time.thread_time`). Seeds from `zlib.crc32`, printed in assertion messages.
- `debug_state` keys are never `arcade.game.reserved()`. The frozen protocol (`game-protocol-v1`) is unchanged:
  the canary `test_protocol_members_are_the_frozen_set` is not edited and passes.
- 128x64 is the only layout a game declares; the engine's tests at 128x32, 64x64 and 96x48 stay. No code under
  `arcade/` names 128 or 64 as the wall's size except `arcade/config.py`'s defaults, `GameInfo.layouts`, bots.
- No budget in `arcade/feel_budgets.toml` or `pong_feel.toml` is loosened. A budget Pong cannot meet is reported
  to the orchestrator, who asks the owner; it is never widened in this iteration.
- Suite time: at most 175 s after this iteration (+35 s). Shares: S1 +3 s, S2 +5 s, P1 +25 s, P2 +2 s, P3 0.
  Say in your report what yours added. (P1's share is large: a slower ball lengthens the oracle's 40 bot plays;
  it08 measured 178 s with rounds to the cap and 141 s with rounds that end by points.)
- A finding or idea outside your task goes in your final message, not in code.

## Lanes
- SERIAL, main checkout, opus, one at a time, each committed before the next: S1, then S2. No game task is in
  flight while S1 or S2 runs.
- PARALLEL, `isolation: "worktree"` from the local HEAD after S2, launched in ONE message: P1 (opus), P2 (opus),
  P3 (sonnet). A task imports nothing another parallel task builds. No task needs the camera or the pose model.
- INTEGRATION, orchestrator, main checkout: merge P1, P2, P3 in that order, the suite after each; then I1.
  I2 is the operator's, in verify, after the review.
- Shared files: S2 is given `arcade/bots.py` by name. No other shared file is edited (`arcade.toml`,
  `arcade/config.py`, `arcade/main.py`, `feel_budgets.toml` and `tests/arcade/helpers.py` do not change).
- Changed asserts (each named, none weakened):
  - P1 `test_pong.py`: `test_registered_and_declared` CAPTION_KEYS gains `"near"`; `test_paddle_follows_hand_height`
    is replaced by `test_paddle_follows_depth` (Q42: the hand no longer moves the paddle); `test_a_still_paddle_
    banks_no_point` and `test_a_moving_player_still_scores` judge travel, not a 1 px tick (C42), same outcomes;
    `test_cpu_is_beatable` and `stander` drive depth instead of a wrist, same asserts; `_sweeps` becomes `_steps`.
  - P2 `test_lobby.py`: `test_end_card_says_best_on_a_record`, `test_card_fits_64_rows_with_best` and
    `test_card_falls_back_to_1x_when_2x_does_not_fit` pass `new_best=True` with their record; asserts unchanged.

## S1 (opus, serial): the controls in the engine (C44), the tracker's scale, `SessionResult.new_best` (C43)
Files: `arcade/input.py`, `arcade/sources/camera.py`, `arcade/runner.py`, `tests/arcade/test_input.py`,
`tests/arcade/test_camera.py`, `tests/arcade/test_runner.py`.
```
DEPTH_SPAN = 0.6          # ln(scale / scale0) across the whole 0..1: 0 at a ratio of 0.741 (about 0.7 m back from
                          # 2 m), 1 at 1.350 (about 0.5 m nearer); 0.5 where the body was first seen
PIN = 0.02                # an unclamped value within this of 0 or 1 is pinned at that end
RECENTRE_SECONDS = 2.0    # pinned this long, the centre starts to follow the body
RECENTRE_RATE = 0.25      # value units a second the reading moves inward while it follows,
RECENTRE_TO = 0.15        # until the body reads this far inside the end
GLIDE_MIN_CUTOFF = 1.0    # Hz: One Euro on the value, by capture time
GLIDE_BETA = 2.0          # per (value unit per second): a moving body is barely smoothed
GLIDE_PERIOD = (1 / 60, 0.25)   # s: the measured capture period is clamped to this

class Glide:
    """A value captured at the camera's rate, given on every tick: One Euro filtered by capture time, then
    moved linearly from the last output to the newest filtered value over one measured capture period."""
    def __init__(self, grace: float = capture_grace(10), min_cutoff: float = GLIDE_MIN_CUTOFF,
                 beta: float = GLIDE_BETA)
    value: float | None
    def reset(self) -> None
    def update(self, value: float | None, t: float, camera_t: float) -> float | None
        # a new capture when camera_t is later than the last; value None or not finite: hold the output for
        # grace seconds (by t), then None and reset(); the next value starts fresh, with no glide from the old

class Depth:
    """Body.scale as a 0..1 control, 1 nearest the camera: 0.5 + ln(scale / scale0) / span, clamped, through a
    Glide. scale0 is the scale of the first capture after reset(); pinned at an end for RECENTRE_SECONDS the
    centre follows as the constants say. A body that is None or has no scale is a dropout."""
    def __init__(self, span: float = DEPTH_SPAN, grace: float = capture_grace(10))
    raw: float | None        # the newest capture's value before the Glide, unclamped
    def reset(self) -> None
    def update(self, body: Body | None, t: float, camera_t: float) -> float | None
    @staticmethod
    def ratio(value: float, span: float = DEPTH_SPAN) -> float    # scale / scale0 that reads value: exp(...)

SCALE_TAU = 0.1           # arcade/sources/camera.py, from 0.3: Depth's Glide smooths; the tracker's lag was 0.3 s
@dataclass(frozen=True) class SessionResult: ... ; new_best: bool = False    # arcade/runner.py, the last field
```
- The working signature `update(body, t)` gains `camera_t` (from `Sensed.camera_t`): the filter runs on capture
  times and a held capture (three ticks at 10 fps) must not count as three samples.
- The lag accepted (C44): Glide adds at most one capture period (0.1 s at 10 fps, one tick on a 30 fps scene) plus
  One Euro's time constant 1/(2 pi fc): 0.16 s for a still body's first move, about 0.06 s at a range a second.
  Worst case 0.26 s from a capture's arrival to the paddle. Why: a person's step takes about half a second, and a
  still body under REAL_NOISE must read under Pong's travel threshold (probe, still `Person(height=0.7)`, 60 s:
  raw value range over 6 s at most 9.5 px of a 48 px travel; filtered at 1.0 Hz, beta 1 to 2, at most 5.8 px).
  Interpolation, not extrapolation: a paddle that overshoots on a reversal feels worse than one 0.1 s late.
- `SessionResult.new_best`: the runner reads `scores.best(name, layout)` at launch; at the end it is True when
  tonight's best after the session is not None and (there was none before or it rose). No game changes.
Tests:
- `test_glide_moves_on_every_tick_between_captures`: a ramp captured at 10 fps, ticked at 30 Hz: the output changes
  on every tick of the ramp and never passes the newest filtered value.
- `test_glide_lag_is_bounded`: a step at 10 fps reaches 90 percent within 0.35 s of its capture; on a ramp of one
  range a second the output is at most 0.25 behind.
- `test_glide_holds_through_grace_then_lets_go`: None for up to grace keeps the value, longer gives None; the next
  value is output as is.
- `test_depth_starts_at_half_and_reads_the_log_ratio`: first body 0.5; scale x1.35 reads 1.0, x0.741 reads 0.0,
  x1.16 reads 0.75 (within 0.01, settled); x2 and x0.5 clamp; nearer is always larger.
- `test_depth_ratio_inverts_the_map`: for v in 0, 0.25, 0.5, 0.9, 1 a body at `Depth.ratio(v)` reads v within 0.01.
- `test_depth_recentres_after_two_seconds_pinned`: a body parked at ratio 0.6 reads 0 for 2 s, then rises at
  RECENTRE_RATE to RECENTRE_TO and stays; pinned for 1.9 s then back inside: no recentre.
- `test_depth_still_body_under_real_noise_stays_within_0_15`: a still Person(height=0.7) under `degrade(REAL_NOISE)`,
  each body's scale measured again from its noisy keypoints in the test (S2 moves that into `degrade`): range <= 0.15.
- `test_depth_rejects_a_bad_span`: 0, negative, NaN, inf raise ValueError.
- `test_camera.py::test_tracker_scale_follows_a_step_within_three_captures`: detections at 10 fps whose scale
  steps x1.3 reach 90 percent of the step by the third capture.
- `test_runner.py::test_session_result_says_new_best_only_when_the_best_rose`: spy sessions recording 3, then 3,
  then 4, then none: new_best True, False, True, False; `best` as before.

## S2 (opus, serial): the actors, the bots and the feel probes move a body in depth
Files: `arcade/sources/actors.py`, `arcade/bots.py`, `arcade/feel.py`, `tests/arcade/test_actors.py`,
`tests/arcade/test_bots.py`, `tests/arcade/test_feel.py`.
```
class Person:
    def scale_to(self, ratio: float, seconds: float, at: float | None = None) -> "Person"
        # the body's size from its ratio at `at` (1 at the start) to ratio times its height, linearly; keypoints,
        # box and so the measured scale grow about the hip centre (y stays); ratio > 1 is nearer the camera
    def height_at(self, t: float) -> float
def _noisy(body, tick, tag, dropout, jitter, rescale: bool = False) -> Body   # rescale: scale measured again
                                                                             # from the noisy keypoints
degrade(...)    # passes rescale=True: the scale jitters as a raw capture's (the tracker smooths more: worst case)
                # shake() keeps rescale=False: its 0.03 jitter would move the runner's player lock (SWITCH_RATIO)

@dataclass(frozen=True) class Move:            # arcade/bots.py; x, hand, wrist_y unchanged
    near: float | None = None   # the Depth value the body stands at (0 far, 1 near, 0.5 its start); None: start size
BODY_HEIGHT = 0.7               # a bot's body at near 0.5; near 0 is 0.52 tall (in the zone), near 1 is 0.95
BODY_RANGE_SECONDS = 0.8        # a bot's near moves at most 1 / this a second: a brisk step, not a teleport
INPUTS["near"] = ln(p.scale); INPUTS["far"] = -ln(p.scale)     # arcade/feel.py: None when scale <= 0
```
- How a game declares its control (no protocol change): the `[fidelity]` table's `input` in its feel file, as
  Pong's `cursor_y` does today. The probes, `fidelity` and `range` already read `control()`'s input; they gain the
  two names. "far" exists because Pong's paddle y grows downward while nearer is up (Q43's default). A test that
  finds degrade's new scale jitter breaks it (the runner's 1.4x switch, `test_runner.py:352`): stop and report.
- `bots.play`: noise (SD `bot.noise`) is added to `near` as to `wrist_y`, clamped 0..1, then rate-limited; the
  body is `Person(cx, height=BODY_HEIGHT * Depth.ratio(near))`. With `near` None nothing changes.
Tests:
- `test_actors.py::test_scale_to_grows_the_body_about_the_hips`: the measured `Body.scale` is ratio times the start
  within 1e-6, the hip y is unchanged, the box grows; halfway through the move the ratio is halfway.
- `test_actors.py::test_degrade_puts_real_jitter_on_the_scale`: a still Person under REAL_NOISE: ln(scale) varies
  between captures with SD between 0.01 and 0.05; the clean scene's scale is constant; `shake` keeps it.
- `test_bots.py::test_move_near_sizes_the_body`: a bot holding near v feeds a body that a fresh `Depth` reads as v
  within 0.02 once settled (the bot's first tick at near 0.5 is the centre).
- `test_bots.py::test_near_moves_at_a_bodys_pace`: a bot asking 0 then 1 takes at least 0.8 s of ticks to get there.
- `test_feel.py::test_near_and_far_read_the_log_scale`: `INPUTS["near"](p) == -INPUTS["far"](p) == ln(p.scale)`.
- `test_feel.py::test_depth_follower_passes_fidelity_and_response`: a stub whose 3 px wide paddle follows a
  `Depth` (paddle y from 1 - value), `[fidelity] input = "far"`, and a canonical that steps between ratios 0.78
  and 1.28, 0.8 s each way: `fidelity` >= 0.8, `range` >= 0.6, `response_ticks` <= 2, `response_px` >= 12.
  If `response_px` misses 12, stop and report it before P1 starts: the orchestrator asks the owner (probe:
  One Euro at beta 2 leaves a 2-tick difference of about 1.7 px at this pace, so 3 px of width is the margin).
- Existing wrist and cursor tests keep their asserts.

## P1 (opus, worktree): Pong by the body, its ball for a body, travel (C42), the hint
Files: `arcade/games/pong.py`, `arcade/games/pong_bots.py`, `arcade/games/pong_feel.toml`,
`tests/arcade/test_pong.py`, `tests/arcade/test_oracle.py`, `tests/arcade/test_first_playable.py`.
```
BALL_START = 55.0       # px/s (100): 2.3 s a crossing; a body needs its step
BALL_GAIN = 1.08        # (1.2)
BALL_MAX = 95.0         # px/s (170): 1.35 s a crossing at the fastest
MAX_ANGLE = 50          # degrees (60): vertical speed at most 73 px/s
CPU_SPEED = 0.35        # wall heights a second, kept as the starting value
PADDLE_W = 3            # px (2): a smoothed control's 2-tick answer must show 12 px
PADDLE_SHARE = 0.25     # of the height (16 px); tuning may grow it to 0.3125 (20 px)
TRAVEL_SHARE = 0.25     # C42: a rally counts when the paddle's travel (max y - min y) is at least this share of
                        # its range (h - paddle_h): 12 px at 128x64; a still body travels at most 6 px, a slow
                        # player 17 px
NEAR_IS_UP = True       # Q43, defaulted: stepping towards the camera raises the paddle
HINT_LINES = ("STEP IN = UP", "STEP BACK = DOWN")   # 1x: 71 and 95 px wide
HINT_COLOR = (255, 160, 0)
HINT_IDLE_SECONDS = 5.0 # in play with the rally's travel under TRAVEL_SHARE this long: the hint again
HINT_FADE = 0.3         # s in and out: never a blink
class Seat: + depth: Depth; lo: float; hi: float (the rally's paddle y); travelled: bool (in the game)
            - moved, moved_ever
debug_state: + "near" (player 1's Depth value, 2 places, or None), + "hint" (bool)
CAPTION_KEYS = ("phase", "left", "right", "near")
```
- The paddle: a human seat's y is `paddle_h / 2 + (1 - v) * (h - paddle_h)` from its `Depth` (v when NEAR_IS_UP,
  else 1 - v): the whole control range is the paddle's travel, no dead ends. None holds the paddle. The seat's
  `Depth` is reset when a body takes the seat, so the centre is where the player stood at the start.
  `body.cursor` is no longer read. `Depth(grace=self.grace)` (capture_grace(CAMERA_FPS), as now).
- C42: `lo`, `hi` reset at each launch; a human's goal banks only when `hi - lo >= TRAVEL_SHARE * (h - paddle_h)`;
  `travelled` is set by such a rally; `_finish` records a best only when the solo player `travelled`.
- Ball and CPU are tuned against S2's bots (a body's pace): over `bots.seeds(Pong, "128x64", 20)` every budget
  passes, none loosened. Report the good bot's round lengths and how many end by points (Q40's note).
- The hint: at the first serve and when HINT_IDLE_SECONDS pass in play without a counted travel; gone once the
  travel counts. Two centred 1x lines around three quarters of the height, drawn before the ball (the ball is never
  hidden) and after the net; fades per HINT_FADE; the drawing keeps the flash rule.
- Scripts: `_steps(person, start, end)` steps between ratios 0.78 and 1.28, 0.8 s each way; canonical, solo and
  duel use it (duel's player 2 steps on its own phase, so its points bank). `idle_body` is a still body, hands
  down. SCENARIOS' names are unchanged. `pong_bots`: `Good` and `Lazy` give `Move(x=HUMAN_X, near=...)` from the
  paddle y they want, by the paddle formula above; `WALL_W`, `WALL_H` stay.
- `pong_feel.toml`: `[fidelity] input = "far"` (xy `left_xy`, axis 1, as now); budgets unchanged.
Tests (in `test_pong.py` unless named):
- `test_paddle_follows_depth` (named, replaces the hand's): a body at ratio 1.3 puts `left_xy` y <= 12; at 0.77,
  >= 52.
- `test_the_hand_does_not_move_the_paddle`: a still body sweeping its wrist 0 to 1: `left_xy` y does not change.
- `test_a_still_body_under_real_noise_banks_nothing`: `degrade(idle_body(), **REAL_NOISE)` over
  `bots.seeds(Pong, "128x64", 10)`: the human side 0 and `score` 0 on 10 seeds of 10; `scores.best` None.
- `test_a_slow_player_keeps_the_point`: the paddle travels 17 px over 3 s in a rally and the ball passes the CPU:
  one point; the same at 10 px: none (`test_a_still_paddle_banks_no_point`, rewritten).
- `test_a_duel_with_both_bodies_still_scores_nothing`: two still bodies under REAL_NOISE: 0-0, over at
  MAX_SECONDS, no best.
- `test_duel_script_banks_every_point`: in the duel scenario the `point` phases entered equal left + right at the
  end (C42's unbanked player 2).
- `test_best_needs_travel_in_the_game`: solo stores a best; a still body (above) stores none.
- `test_hint_at_first_serve_and_after_idle`: `hint` True at the first serve, False after a counted travel, True
  again after HINT_IDLE_SECONDS without; the ball's pixels show over the hint.
- `test_hint_fits_and_keeps_the_flash_rule`: both lines inside 128 px; Pong's own drawing with the hint fading keeps
  `concurrent_area` under the flash module's limit, as `test_own_drawing_keeps_the_flash_rule` does.
- Existing tests keep their asserts, with the named changes; `test_ball_speeds_up_on_each_hit_up_to_the_max` reads
  the new constants. `test_oracle.py` and `test_first_playable.py`: unchanged asserts over the new scripts; the
  canonical round runs attract to card.

## P2 (opus, worktree): the end card's "BEST!" only for a new best above 0 (C43, Q41)
Files: `arcade/attract/lobby.py`, `tests/arcade/test_lobby.py`.
- `_draw_card`: "BEST!" when `r.new_best` and `r.score is not None and r.score > 0`. Nothing else on the card moves.
Tests:
- `test_end_card_says_best_only_for_a_new_best`: `new_best` False with score equal to best: no BEST!; `new_best`
  True with score 0: none; with score 3: BEST!.
- `test_best_shows_once_for_a_repeated_score`: a spy that scores 3 in two sessions through `run_headless` with a
  real `Scores`: the first card says BEST!, the second does not (it08's walk-up, sessions 1 to 3).
- `test_a_zero_score_never_says_best`: a spy scoring 0 as the night's first: no BEST!.
- The three named tests gain `new_best=True`; the strobe tests at 128x64 pass unchanged.

## P3 (sonnet, worktree): the game guide's controls, and the second live smoke
Files: `.claude/skills/arcade-game-authoring/SKILL.md`, `docs/superpowers/workflow/live-smoke.md`.
- The guide gains "Controls" (at most 40 lines; the guide under 400): `Depth` (one axis, the whole body, reads
  from where the player started; Pong), the hand through `Cursor` plus `Glide` (pointing), `zone_x` (side to side);
  never read `body.cursor` raw (C44); declare the control in `[fidelity] input` (`near`, `far`, `cursor_x`,
  `cursor_y`, `zone_x`); bots drive `Move.near` or `wrist_y`; a still body scores nothing, judged by travel over a
  threshold above REAL_NOISE's jitter (C42), and a best needs travel in the game.
- `live-smoke.md`: Pong's row becomes the second smoke: `.venv/bin/python -m arcade run -v`; stand about 2 to
  2.5 m away with the hips in view; raise a hand to start; step in for up, back for down; report the lag, the
  jitter when still, whether both ends are reachable, whether the hint read, and the ball's pace.
- P3 also owns the new file `arcade.mac.toml` (the operator's addition, Q44): `camera_fps = 30` alone, with a comment
  that it is the owner's trial on the Mac and that every grace shrinks with it. live-smoke.md gives both commands
  (the second with `--config arcade.mac.toml`). Check that it loads: `arcade run --seconds 2 --script walkup`.
- No tests: check every name, constant and command against S2's commit and this plan.

## I1 (orchestrator): merges and the report
- Merge P1, P2, P3 with the suite after each. Report: Pong's feel table at 128x64 (every metric, value, budget),
  the good bot's round lengths, the suite's count and time against 175 s, and the owner's smoke command.

## I2 (the operator, in verify, after the review): evidence, from the repo root
```
.venv/bin/python -m tools.arcade_evidence --iteration 9 --games pong --out docs/superpowers/workflow/evidence/it09
.venv/bin/python -m tools.arcade_shot pong --lobby small --scenario duel --raw-vs-pushed --flash-report \
    --out <scratch>/it09-strobe > <scratch>/strobe-check.txt
.venv/bin/python -m tools.arcade_shot pong --lobby small --scenario canonical --look both --out <scratch>/it09-walkup
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m arcade run --seconds 5 --script walkup \
    > <scratch>/run-default.txt 2>&1
```
Copied into evidence/it09/ with the tree clean, plus collect.txt, pytest.txt, head.txt. The depth shows on Pong's
sheets through the caption (`near` in CAPTION_KEYS) and the paddle following the steps. The lobby's mirror figure
does NOT grow as the actor steps: `figure.to_wall` fills the rect with the body's box height (Q37); see Left out.

## C44: can the Mac's camera run faster than 10 a second? Not in this iteration
Inference (MediaPipe's lite landmarker, 11 ms on the M1 by `arcade doctor`, evidence/it08/doctor.txt) runs in
`ThreadedCamera`'s daemon thread, not in the tick; the 2.0 ms tick budget (game code, `thread_time`) is not touched,
and 20 a second is about a fifth of a core. It is not made the default now because: `arcade.toml` must equal
`ArcadeConfig`'s defaults (`test_default_file_in_repo_lists_every_field_with_its_default`), so a Mac-only value
needs a config seam or moves the Pi's default too; every grace is sized in captures (Q10), so at 20 the lobby's
and the runner's graces halve in seconds against C10's statistics measured at 10; REAL_NOISE, the budgets and
Pong's tuning are at 10; and whether MediaPipe's `detect` releases the GIL (an 11 ms hold, twice in three ticks)
is unmeasured. Glide removes the 10-steps-a-second jerk at 10. Owner question Q44 (default: stay at 10).

## Left out (named)
- The hand's read quality (GATE A, the owner's recordings); M7a's games and their still-hand rule; panels; Q23.
- The lobby's mirror growing with depth (a change to Q37's full-height figure); a depth gauge in the lobby.
- camera_fps above 10 (Q44). `Body.scale`'s fallback when the hips leave the frame (1.5 torso, the torso from
  1.25 shoulder widths) is kept, not retuned: a player too near the camera may jump; the smoke's advice covers it.

## Decisions
- Pong's control is `Depth` on `Body.scale`; the raised hand only launches (the lobby's rule unchanged); the
  frozen protocol is unchanged: the control is declared in the feel file's `[fidelity] input`.
- The log map is symmetric (DEPTH_SPAN 0.6: ratios 0.741 to 1.350), centred at first sight, recentred only after
  2 s pinned; the paddle's whole travel is the control's whole range.
- The tracker's SCALE_TAU drops to 0.1 s: two smoothers in a row were 0.3 s of lag on a ramp.
- `degrade` measures the scale from its noisy keypoints (worse than the live tracker: the tests are the worst case);
  `shake` keeps the scale.
- Travel threshold 0.25 of the paddle's range (12 px): between a still body's 6 px (9.5 raw) and a slow player's 17.
- `PADDLE_W` 3 so a smoothed control's 2-tick answer can reach spec 11's 12 px; S2's stub checks this first.
- C43: the runner knows whether tonight's best rose (`SessionResult.new_best`, a defaulted field outside the
  freeze); the card needs it and a score above 0.

## Owner questions (defaulted)
- Q43 Direction: stepping towards the camera moves the paddle up (`NEAR_IS_UP = True`).
- Q44 Camera rate on the Mac: the default stays 10; `arcade.mac.toml` lets the owner try 30 in the second smoke.
- Q45 The hint: two 1x lines "STEP IN = UP" / "STEP BACK = DOWN", amber, at the first serve and after 5 s in
  play without travel, fading in and out, under the ball.
- Q46 Pong for a body: ball 55 to 95 px/s (gain 1.08, angle 50), paddle 3 x 16 px, the CPU at 0.35 heights a
  second, before tuning; the owner's second smoke judges the pace (Q40's fast ball is set aside).
- Q47 The depth range: about 0.5 m nearer to 0.7 m back from where you raised your hand covers the wall; after 2 s
  at an end the middle follows you.
