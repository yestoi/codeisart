## Verdict: APPROVED

## Blocking findings (file:line, the input, what happens, why it blocks)
None.

Checked: the code at e42b02e (HEAD 36a67ed differs only in state.md). `pytest --collect-only -q`: 762 collected (723 at the base), so no drop. The touched files (test_input, test_camera, test_festival, test_actors, test_lobby, test_pong, test_first_playable, test_bots) ran alone: 195 passed, 0 skipped, 61 s. Safety: flash.py, brightness.py, show/, headless.py, config.py and arcade.toml are untouched. The runner changes only `SessionResult.new_best` and one `scores.best` read, so the order limiter, governor, push is unchanged. Pong's cached masks write into the game's own canvas, which the runner pushes as before. arcade.mac.toml sets only `camera_fps = 30`.

Every removed or changed `assert` in `git diff 8ae1aea..e42b02e -- tests/`:
- test_festival.py `test_festival_guard_rails`, d738df1: `(b.box, b.scale, b.vx, b.vy) == truth's` became `(b.box, b.vx, b.vy) == truth's` plus `b.scale == dataclasses.replace(b, scale=0.0).scale`.
- test_first_playable.py `test_two_players_walk_up_play_pong_and_see_the_card`: the left span >= 32, the cursor r > 0.95 and `len(right) == 1` became, for each paddle, span >= 32, r(own far) > 0.95 and |r(other's far)| < 0.5.
- test_pong.py: `CAPTION_KEYS` gains "near" (named). `test_paddle_follows_hand_height`'s `y <= 8` / `y >= 23` became `test_paddle_follows_depth`'s `y <= 12` / `y >= 52` plus a `near` check (named, and the plan's own numbers). `test_feel_file_overrides_have_reasons` reads "far" instead of "cursor_y".
- Changed setup under unchanged asserts: `test_cpu_is_beatable` vy 90 to 70, and the ball is held 3 s while the body steps. The still and moving rally tests use travel 10 and 20 px, with the same outcomes (named).
- Only additions elsewhere. The new still-body Depth test went in at 0.18, not the plan's 0.15.

Rulings on the seven deviations:
1. d738df1: acceptable, not a weakening that hides a fault.
   - The new assert fails if degrade keeps the truth's scale, because the noisy keypoints then measure differently. Box, vx and vy stay pinned to the truth. test_actors' `test_degrade_puts_real_jitter_on_the_scale` bounds the jitter: SD of ln(scale) between 0.01 and 0.05, shake keeps the scale.
   - The 0.18 bound: 8.6 px of 48 px, under the 14.4 px threshold. Pong's own still-body tests hold C42 on 10 of 10 seeds, worst rally 8.3 px.
2. P1's constants: acceptable. No budget, seed count or probe changed to pass.
   - feel_budgets.toml is unchanged. pong_feel.toml changes only `input`. feel.py adds only INPUTS near and far. SEEDS stays 20.
   - `response_px` is honest. `_probes` spreads 8 probes evenly over the ticks where the control moves, and the pixel count comes in steps of 6 (3 px width x 2 edges per px of travel). 12.0 is the median of [6, 12, 4, 6, 12, 18, 18, 12], i.e. 2 px in 2 ticks.
   - STEP_HOLD 0.4 was picked for `range`: holds of 0.3, 0.4, 0.5 and 0.8 all give 12, and 0.6 gives 9. That is a scenario choice (a person holding at the end of a step), not a probe change.
   - CPU_SPEED is tuning the plan allows. AIM_OFFSET is bot strategy (angled returns), not a budget.
3. The unnamed changed asserts: acceptable.
   - The duel asserts cannot hold once player 2 steps, which the plan requires. The replacement checks both paddles and would catch swapped seats: the players are a quarter cycle apart, so a swapped paddle fails r > 0.95.
   - vy 90 is not a ball the game can make any more: BALL_MAX 95 x sin(MAX_ANGLE 50) = 72.8. vy 70 is.
   - "far" follows from the plan's feel-file line.
4. `active` on 14.4 px from an anchor: acceptable. A real slow player is not thrown out.
   - `_bounce` still sets `active` on every human hit, and the anchor resets at every serve (`_synced` False).
   - To reach the prompt a player must go 30 s without a hit and without 14.4 px of travel from a serve's position. A player who misses everything loses 5-0 in about 22 to 25 s: serve 1 s, a 2.3 s crossing and 1 s point, per point. The game ends "done" before 30 s.
   - In the 5 s prompt, a hit, 14.4 px of travel or a raised hand clears it.
5. The memo and the mask cache: acceptable.
   - A play depends on game, bot class, seed, layout, `won` and seconds. The last two are in the "plain" test, and both callers pass the project font.
   - No test in test_pong patches Pong or bots before `bot_play`. Run alone, test_pong plays the games itself.
   - The mask key is (canvas w, h, id(font), game w, h). The score masks are keyed by text, the colour and the hint's fade are applied at draw, and Canvas has no offset state that the direct frame writes could bypass.
6. S3's born-without-hips case: not worse than before S3. See the first note below.
   - The extra `_Track.measured` field is acceptable: it is needed to tell "never measured" (read the fallback) from "measured, no shoulder ratio" (hold).
7. The recentre plus jitter: possible, but rare. Noted below, not blocking.

## Noted, not carried (one line each)
- Q6 (probe it09-review-q6-born-without-hips.py, the spike's proportions): a still body whose track is born without hips, whose hips appear at 1 s, moves the paddle 32 to 8 px. That is 24 px of travel, over 14.4, so it counts as C42 travel and as `active`: one point or a best can bank for a person who never moved. The paddle is then pinned at the top for 2 s and recentred to 0.85 (y 15.2). After that the bottom needs a scale ratio of 0.60, about 1.3 m back from 2 m. This follows the amendment's own rule ("never measured: raw.scale, as today") and happened before S3 too. S3 makes it once per track, where every hip flicker used to swing it. Owner and next iteration: recentre Depth when a track is first measured; watch for it in the second smoke.
- Q7 (probe it09-review-q7-recentre.py; still body stepped to ratio 0.64, REAL_NOISE, ball held, one 6.8 s rally over the pin and the recentre): worst travel 14.74 px on 1 of 250 noise seeds (body id 9202), next 14.03, median 9.6. The snap reads a noisy capture, so the recentred mean lands near 0.2, not 0.15. It banks only if that rally also ends past the CPU, and the player had already stepped to the end. The margin under 14.4 is about 2 px, not the 6 px the numbers suggest.
- `response_px` has zero margin: 12.0 against min 12, per probe [6, 12, 4, 6, 12, 18, 18, 12]. Any Glide, script or probe-timing change can tip it (P1's own finding).
- feel's `range` divides by h - 1, which caps a 16 px paddle game at 0.762 against the 0.6 floor. Pong reads 0.6287 (S2's finding, for the budgets' comment).
- `new_best` compares `scores.best` at launch and at the end. A session that spans the 16:00 rollover after a higher previous-night best says no BEST! for tonight's first best. This is rare, and harmless.
- Process: two of my probe commands used `cd` (a git diff redirected to the scratchpad, and git status plus `pytest --collect-only -p no:cacheprovider`). Nothing was written in the repository. `git status` shows only the operator's modified docs and the untracked evidence/it09.
