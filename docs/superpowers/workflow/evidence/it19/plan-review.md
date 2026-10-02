# it19 plan review (adversarial, fresh context)
Plan: `docs/superpowers/plans/2026-10-01-it19-four-pose-games.md` at 7f71798. Read-only review: probes in the
scratchpad with `.venv/bin/python`, no suite run, no commit.

## Verdict: BLOCKED

Eight blocking findings. Four are about the bots' win rates: three games fail `[score.win_*]` or
`test_oracle.py:115` as specified. Two are cases where a still body under REAL_NOISE scores. One contradicts a named
test, and one contradicts the guide. Each fix is a few lines of the plan. None changes the plan's structure, I0, the
file ownership or the parallel order.

## Blocking findings

**B1. Freeze's lazy bot can never win, so `win_lazy` = 0.**
- Why it fails: `feel_budgets.toml` `[score.win_lazy] min = 0.1` and `test_oracle.py:115` (`win_good > win_lazy >
  win_none`, here 0 > 0).
- How:
  - Plan 266-267: lazy "on every third red keeps dancing 1 s", which is past `GRACE = 0.5`, so it is out on red 3
    every game.
  - An out ends a solo game (plan 255, Q106), and `won` needs `out` False and `score >= WIN_SCORE = 4` (plan 267-268).
    Reds 1 and 2 give at most 2.
  - Its noise would also lose most games without the deliberate mistake. Probe: the x noise 0.02 alone moves the
    anchored body past `MOVE_TRAVEL = 0.25` on 38.6 % of reds (travel is the span over the red, divided by
    `STEP_SCALE` 0.4), so it survives 6 reds with p = 0.053. Noise 0.015 gives 0.7 % of reds out; 0.005 to 0.01
    gives 0.
- Smallest fix (plan 266-267):
  - Make lazy's mistake depend on the seed and happen once. For example: lazy keeps dancing 1 s into a red only when
    the green before it lasted over 4.5 s (about p 0.5 per red from `GREEN_SECONDS` (3, 6)); or into red 1 only, on
    half the seeds.
  - Set lazy's noise to 0.01 at most. Target win_lazy is about 0.2 to 0.5.

**B2. Copy Me's lazy bot wins every seed, so `win_lazy` = 1.0.**
- Why it fails: `[score.win_lazy] max = 0.7` and `win_good > win_lazy` (1.0 > 1.0).
- How:
  - Plan 121-122: lazy strikes the target "from 2.4 s into `play`". Even counted from when it sees `play`
    (`reaction_ticks` 14 + 1 late), that is 2.9 s, inside the scoring window 2.0 to 3.0 s (`GROW_SECONDS` 3.0,
    `SCORE_WINDOW` 1.0).
  - The bot's pose carries no noise (`bots.play` noises only x, wrist_y and near, `bots.py:182-187`; I0 adds `pose`
    unnoised), so rounds 1 and 3 have share 1.0. Round 2 misses (wrong rung).
  - So `matches` = 2 = `WIN_MATCHES` and the bot wins. Nothing in it depends on the seed.
- Smallest fix: tie lazy's result to the rng's draw. For example, in round 3 lazy copies only when the target is the
  rung's first pose and stands otherwise (win about 1/3 with a three-pose rung). Or strike at 2.9 s from `play`'s
  first seen tick, so the hold lands on the window's last ticks only when reaction jitter allows. The first is
  deterministic per seed and easy to check.

**B3. Flap's bots never leave `ready` on many seeds.**
- How:
  - Plan 146-147: `ready` holds the bird level until the first flap.
  - Plan 176-178: both bots flap only "whenever `bird_xy`'s y is under `gap_xy`'s by 3 px or more" (lazy: 7 px).
  - In `ready` the bird does not fall. If `gap_xy` is None (no pipe yet, plan 169) or the first gap's centre is at or
    below the bird plus 3 (or 7) px, the bot never flaps. The session then ends on the runner's inactive rule (30 s
    plus the 5 s prompt, `config.py:48`, `runner.py:47`) with `survived` False.
  - The plan never says the bird's ready y. With `GAP_Y` (14, 44) uniform and a mid-wall bird, about half the seeds
    deadlock. That fails win_good >= 0.7 by itself.
- Smallest fix:
  - Both bots flap once in `ready`, and whenever `gap_xy` is None.
  - The plan states the bird's ready y (for example row 30).
  - Make "the first pipe is placed before `ready` ends" or "`gap_xy` is the first gap from `ready`" explicit.

**B4. Swat: a still body under REAL_NOISE swipes, and cuts fruit at the spawn row.**
- How:
  - Blade x = `zone_x` map + `(u - 0.5) * ARM_PX` (plan 194-196), with u from `Cursor`.
  - `Cursor` switches hands whenever the other wrist reads 1.25x further from its reference (`input.py:151`). With
    one hip dropped (about 15 % of captures under REAL_NOISE), a hanging wrist's reference becomes the far hip and
    the switch fires.
  - Probe (still `Person(0.5, height=0.6)`, `degrade(**REAL_NOISE)`, 60 s, 5 ids, the plan's Cursor, Glide and
    mapping):
    - 98 to 106 hand switches per 60 s (50 to 60 through a `KeypointHold`). Each one flips u 0.75 to 0.25: a 24 px
      blade jump, which the Glide spreads over a few ticks.
    - The blade moves 3 px or more on 270 to 300 ticks and 4 px or more on 240 to 285. The largest segment is 6.8 px.
    - All of it is at row 57 (v clamped at `V_BOTTOM`). Fruit spawn at `SPAWN_Y = 58`, so a horizontal 3 to 7 px
      segment at row 57 passes within `FRUIT_R + 1` = 3 px of every new fruit under it.
  - So `test_a_still_body_under_real_noise_scores_nothing` fails, and C41 with it. The plan's remedy, raising
    `CUT_MIN_PX` to 4 (plan 211), does not help: 240 or more ticks still qualify.
- Smallest fix, any one of:
  - A cut needs the cursor's raw v under `V_BOTTOM` minus a margin. A still hanging hand reads v 0.951 or more in
    every probe capture, so `v < 0.85` excludes it.
  - Or drop u from the blade (x from `zone_x` only, `ARM_PX` 0).
  - Or pin each seat's hand (no `Cursor` switch) for the blade.
  - Keep the real-noise test, and run it at `height=0.6` and 0.45.

**B5. Swat's constants contradict its named test.**
- How:
  - From `SPAWN_Y = 58` with `GRAVITY = 30`:
    - `LAUNCH_VY = -40` peaks at row 31.3 (30.7 to 32.0 depending on the integrator).
    - `LAUNCH_VY = -52` peaks at row 12.9 (12.1 to 13.8).
  - `test_fruit_arcs_up_and_falls_out` asserts apexes rows 8 to 30 (plan 201, 228). The slow end fails every time
    it is drawn.
  - `FRUIT_R = 2` centred at row 58 lights rows 56 to 60. The same test forbids rows 60 to 63 unless the draw clips.
- Smallest fix: `LAUNCH_VY = (-54.0, -42.0)` (apexes 9.4 to 28.6), or the test's band 12 to 32. Also either
  `SPAWN_Y = 57` or "fruit are clipped at row 59" in the plan.

**B6. Flap's numbers: the good bot cannot reach `win_good >= 0.7` as specified.**
- Probe: a model of the plan's physics.
  - Physics: `GRAVITY 24`, `FLAP_VY -22` set, `MAX_FALL 30`, `GAP_H` 30 to 24, `GAP_Y` uniform (14, 44) per pipe,
    `PIPE_EVERY 3`, `SCROLL 20`, `FLOOR_Y 59`.
  - The bot sees the state `reaction_ticks + 1` late (`bots.py:153-205`). The flap fires on the sweep's down
    capture (camera at 10 fps).
  - Result: good 0/200 and lazy 0/200 survive 45 s. Almost all crashes are into the bottom or the gap's lower lip.
  - Why: a flap is +10 px of climb (v^2 / 2g), and the bot reacts on a view about 0.35 to 0.45 s old. It flaps when
    3 px under the gap and is still flapping-eligible when the first flap's climb begins, so it double-flaps and
    overshoots, then falls 10 px or more past the gap before the next decision lands.
- Variants:
  - A bot that flaps only while falling (vy > 0) and 0 to 2 px under the gap: 0.32 and 0.27.
  - Adding a bounded step (next gap centre within ±12 px of the last): 0.52.
  - ±8 px and `GAP_H (32, 28)` with the falling-only bot: good 0.96. But lazy at 12 to 13 ticks stays about 0, which
    still fails `win_lazy >= 0.1`.
  - This is a model, not the game, but the margins are not close.
- Smallest fix:
  - The plan names these as starting values to tune inside the budget bands, and names the levers: a bounded gap
    step, wider gaps, a good bot that flaps only while falling, and a lazy reaction nearer good's (8 ticks) with a
    larger threshold.
  - Acceptance adds the win rates (the oracle already checks them), so the implementer tunes before the review.

**B7. Flap keeps the runner's exit gesture, and flapping trips it.**
- How:
  - Plan 145: `GameInfo` for flap has no `exit_gesture`, so it is True (`game.py`).
  - A flap starts with both wrists over the shoulders. The runner's exit is both hands up held `exit_seconds = 3.0`
    (`config.py:50`) by a `Hold` whose grace (`capture_grace(10)` = 0.55 s) bridges short down-strokes.
  - Probe with the runner's Hold: flapping every 0.30 s or 0.50 s ends the session at 3.0 s, every 0.63 s at
    3.17 s, and every 0.80 s or slower never.
  - A climbing player flaps about every 0.5 s, and so does the good bot when it double-flaps (B6).
  - The guide says it outright: "`exit_gesture`: False only when play itself needs both hands up"
    (`.claude/skills/arcade-game-authoring/SKILL.md:54`). Flap's play does.
- Smallest fix: `exit_gesture=False` on plan 145, and `test_exit_gesture_is_off` (fast flaps for 5 s: session on).

**B8. Copy Me: a still body under REAL_NOISE scores on poses whose judged limb sits 30 to about 49 degrees from
stand.**
- How:
  - Judged = target angle more than `LIMB_TOLERANCE_DEG` (30) from stand's (plan 91-92), and matched = within 30 of
    the target.
  - Probe (still Person, `degrade(**REAL_NOISE)`, 60 s, 5 ids, angles as the plan defines them):
    - A still body's segment angles wander from stand's by up to 18.8 degrees on forearms and 14.5 to 15.4 on upper
      arms.
    - Forearm error is over 5 degrees on 72 % of captures, over 10 on 31 % and over 15 on 10 %.
  - So any judged segment 30 to about 49 degrees from stand is matched by a still body on many captures. Airplane's
    down-out forearm (35 to 43 degrees from stand in the probe) is one, giving share about 1/3.
  - `points = round(100 * share)` is above 0. The `FRESH_SHARE` rule does not protect: a still body's share is
    always under 0.5, so every round counts as fresh.
  - That breaks C41. `test_a_still_body_under_real_noise_scores_nothing` uses 5 random seeds, which draw airplane
    only about 87 % of the time: the test is flaky as well as failing.
- Smallest fix:
  - Judge only segments more than `2 * LIMB_TOLERANCE_DEG` (60) from stand's. Every listed target still judges 2 or
    more limbs: arms_up differs by 141 and 175 degrees per arm, t_pose by 70 and 80.
  - Run the real-noise test over every `LADDER` pose as the target, not random draws.

## Notes
- Paths:
  - The plan writes `actors.py` (59, 62, 91); the file is `arcade/sources/actors.py`.
  - G1 is given `model: opus` (plan 44, 73) where config.md Loop rule 2 gives games to sonnet. That is the
    operator's call, so it should be said.
- I0 is sound:
  - Built in scratch: `hand="both"` puts both wrists' reach v exactly at `wrist_y` (0.1, 0.4, 0.62, 0.95), and
    `pose=t_pose` reproduces `Person.pose`'s keypoints exactly (error 0.0). Both wrists at 0.1 read
    `both_hands_up` True.
  - No positional `Move(...)` exists in the repo, and `_sensed` callers are bots.py and `test_quickdraw.py:365,440`
    only.
- The oracle needs no edit: `REPORT_PLAYS` comes from `all_games()` (`test_oracle.py:22-26`). New game modules that
  sort after `test_oracle` (quickdraw, swat) put all their plays in the pool.
- Suite:
  - Measured CPU per tick is about 0.6 ms (Pong 0.56 to 0.61, Quick Draw 0.65 to 0.68, Dodge 0.58 to 0.59,
    Nobody 0.45).
  - My shares: Swat 42 s, Freeze 29, Flap 29, Copy Me 24. The plan's 440 s total is believable.
  - The pool's CPU roughly doubles (about 107 s to about 215 s, about 66 s of wall time on 4 workers) against
    `WORKER_TIMEOUT_S = 120` (`pooled.py:34`): the margin halves. A pool timeout falls back to the memo, so it is not
    a failure, but watch it on the Pi.
- Freeze:
  - A still body is safe under the repo's noise. The worst 3.5 s travel is 0.086 to 0.095 against 0.25, with 0
    windows over, because `degrade`'s crc noise never drops both shoulders together. Real cameras do. With both
    shoulders gone, `reach` falls back to the box and v jumps from about 1.0 to 0.51: an out for a frozen player. A
    later iteration's concern, or hold travel per keypoint at `MIN_CONF`.
  - The topple cannot use `draw_figure`: `to_wall` scales the box height to the rect, so a rotated body is not
    drawable. The plan should say the topple is the game's own drawing.
  - The topple moves `player_xy` while `zone_x` stays put: watch fidelity on zone_x.
  - The red area estimate (1 px border plus FREEZE at 1x) is about 0.094, under the plan's 0.12 and the flash cap.
- Flap:
  - A still body never flaps: the minimum hanging v is 0.951, and the box fallback is about 0.51, never under 0.40.
  - `test_gravity_is_gentle` sits on its boundary: exactly 12.0 px after 1 s analytically, 12.40 with
    semi-implicit Euler (fails), 11.60 with explicit. Say the integrator, or set the bound to 13.
  - Canonical's flaps every 1.2 s each climb about 9.1 px net (the level period is 1.83 s), so the bird pins to the
    top. It reaches `over` by crashing, so `phases_reached` holds, but "so the bird passes gaps" (173) is not what
    happens.
- Copy Me:
  - `star`'s legs (about 13 degrees from stand) are never judged, so `test_legs_cropped_scores_the_upper_body`
    tests nothing about cropping.
  - The `cropped` Person at y 0.85, h 0.6 has its knees at 0.98, not clamped. Pick a pose with judged legs and a
    lower person.
  - `active` (judged-angle error changing 10 degrees within 1 s, plan 110) will read a still noisy body as active,
    because forearm noise reaches 18.8 degrees. Harmless for the hint; it matters only if `active` feeds a check.
  - The round is about 24 s, inside 20 to 120.
- Swat:
  - The bots' u is fixed at 0.75 (`Person.wrist` moves only vertically), so the bot's blade sits 12 px right of its
    zone map. Columns 0 to 11 are unreachable unless `zone_x` maps below 0. Fruit drift there.
  - Lazy's noise of 0.05 on x is about a 9 px blade SD against a 3 px cut radius. Lazy may land under 0.1: tuning.
  - On a slow sweep, `response_px` (at least 12) may be borderline: check canonical early.
  - A COMBO flash on top of a 3x3 blade, a trail and bursts may near the 0.1 concurrent area. The plan checks it
    (139): keep that.
  - Two-handed swipes above the head can reach the 3 s exit hold. Rare in play; the default is fine.
- Global says the figures follow `zone_x` "through a Glide", but the lobby maps raw `zone_x` with its column
  backlash and no Glide (`arcade/attract/lobby.py:40-56,170-195`). Either works; say which, so the sheets match the
  lobby.
- File ownership is clean: each game owns its module, test, feel toml and sheets, and I0 owns `bots.py` and
  `test_bots.py`. POSES readers check `set(POSES) >= {...}` (`test_actors.py:117`), so they still hold.
- Flash: Copy Me's match flash and Swat's COMBO flash use `fx.flash`, whose 0.5 s gap (`FLASH_GAP`) and the
  `square_flashes <= 6` budget hold for the rates planned. Freeze's red is never a field colour (Q107).

## What was checked and how
- Read:
  - The plan in full, the plan writer's report, and spec section 8 (the rows at 551, 557, 558, 560), 8.1, 5, 7.6,
    9.2 and 9.3.
  - config.md Loop rules 1, 2, 5 and 6, and the guide (`SKILL.md`).
  - Code: `arcade/bots.py`, `arcade/sources/actors.py` (Person, `_keypoints_at`, degrade, `REAL_NOISE`),
    `arcade/poses.py`, `arcade/figure.py`, `arcade/input.py` (Cursor, Glide, Hold, `capture_grace`),
    `arcade/sensed.py` (reach), `arcade/juice.py`, `arcade/flash.py`, `arcade/game.py`, `arcade/feel.py`,
    `arcade/feel_budgets.toml`, `arcade/games/__init__.py`, the lobby's 40-56 and 170-195, and the runner's 380-560.
  - Tests: `tests/arcade/test_oracle.py`, `test_all_games.py`, `pooled.py`, `helpers.py`.
- Probes (scratchpad, `.venv/bin/python`, each under 2 minutes):
  - `probe_i0.py`: I0 built on a copy of `Move` and `_sensed`. Covers both-hand reach v, pose keypoints and
    `both_hands_up`.
  - `probe_still.py`: a still Person under `degrade(**REAL_NOISE)`, 60 s, 5 ids, with and without `KeypointHold`.
    Measures Freeze travel windows, Swat blade segments, `Cursor` hand switches and Flap's hanging v (B4 and the
    notes).
  - `probe_drop.py`: per-joint drop rates and which pairs drop together (shoulders never, hips never, wrists
    about 2.2 %).
  - `probe_angles.py`: segment angles of stand, arms_up, t_pose and the ladder poses, and a still body's angle error
    from stand per capture (B8).
  - `probe_freeze.py`: the lazy bot's noise against `MOVE_TRAVEL` per red at 0.005 to 0.02 (B1).
  - `probe_phys.py`: Swat apexes per integrator (B5), and Flap's gravity after 1 s and canonical's climb (notes).
  - `probe_flap.py` and `probe_flap2.py`: Flap's play model, 200 seeds per variant (B3, B6), and the runner's exit
    `Hold` under repeated flaps (B7).
  - `probe_cost.py`: CPU per tick of the existing games' plays, and the suite and pool estimates.
