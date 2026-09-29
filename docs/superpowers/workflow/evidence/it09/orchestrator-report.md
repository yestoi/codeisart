# it09 orchestrator report: Pong by the body (M4c)

Base 8ae1aea. Plan: docs/superpowers/plans/2026-09-28-it09-pong-by-the-body.md. Main checkout, no push, no deploy.
Task reports (scratchpad): it09-S1-report.md, it09-S2-report.md, it09-P1-report.md, it09-P2-report.md, it09-P3-report.md.

## Completed
- S1 (opus, serial, f82eda9): `Glide` and `Depth` with the plan's constants in arcade/input.py; SCALE_TAU 0.3 -> 0.1;
  `SessionResult.new_best` from the best read at launch. Every named test written test-first; the still-body test
  was held back (bound missed) and went in with the operator's d738df1 at 0.18.
- S2 (opus, serial, de01b4a): `Person.scale_to` / `height_at`; `_noisy(rescale=...)`; `Move.near`, BODY_HEIGHT,
  BODY_RANGE_SECONDS; feel INPUTS `near` / `far`. The stop point passed: the depth-follower stub reads fidelity
  0.986, range 0.766, response_ticks 1.0, response_px 12.0 (exactly the floor). No GLIDE_BETA retry was needed.
  degrade's rescale=True was held back (it broke an unnamed assert) and went in with the operator's d738df1.
- P1 (opus, worktree, 8770f89 + d6fcf12, merged 5fc0b7c): Pong's paddle follows `Depth` (NEAR_IS_UP), the hand does
  not move it; travel judged per rally (C42); a best needs travel in the game; the "STEP IN = UP / STEP BACK = DOWN"
  hint; ball and CPU retuned for a body; `pong_bots` drive `Move.near`; scripts step in depth. All named tests pass;
  every Pong feel budget passes at 128x64 over 20 seeds, none loosened.
- P2 (opus, worktree, f7efc01, merged a448ff9): "BEST!" only when `r.new_best` and the score is above 0; the three
  named tests gain `new_best=True`; three new tests.
- P3 (sonnet, worktree, d228c35, merged 887c144): the guide's "Controls (C44)" (27 lines; guide 328 lines);
  live-smoke.md's second smoke with both commands and a report table; arcade.mac.toml (`camera_fps = 30`).
  `python -m arcade run --seconds 2 --script walkup --config arcade.mac.toml` exits 0 on main (checked by me).
- I1: P1, P2 and P3 were merged in that order, with the full suite green after each. P1 went back once for suite time, and its two perf commits merged at 8181012 and e42b02e. Final: 762 passed in 169.2 s at e42b02e.
- The owner's smoke commands: `.venv/bin/python -m arcade run -v` and `.venv/bin/python -m arcade run -v --config arcade.mac.toml`.

## Deviations
1. S1's `test_depth_still_body_under_real_noise_stays_within_0_15` missed its bound with the plan's constants
   (0.163, 0.159, 0.102 on its seeds; worst 0.168 over 10 seeds x 60 s; the plan's probe of 5.8 px did not
   reproduce, raw matched at 9.5 px). Reported to the operator, who committed it at 0.18 on 10 seeds in d738df1.
2. S2: `degrade(rescale=True)` broke `test_festival.py::test_festival_guard_rails` (asserted the degraded scale
   equals the truth's), an assert the plan did not name. Held and reported; the operator applied the patch and
   changed that assert in d738df1 (drops scale from the tuple).
3. S2: the depth-follower stub maps the paddle over the full height, (1 - v) * (h - 1), not Pong's 48 px travel
   (with Pong's map the plan's canonical gives range 0.583 < 0.6). Finding: feel's `range` divides by h - 1, so a
   paddle game's range is capped at (h - paddle_h) / (h - 1), 0.76 at 128x64.
4. P1: TRAVEL_SHARE 0.3 (14.4 px), not the plan's 0.25, per the operator's ruling sent to P1 directly.
5. P1: CPU_SPEED 0.3, not 0.35 (lazy's win band: 0.20 at 0.35, 0.25 at 0.3).
6. P1: the good bot aims off-centre (AIM_OFFSET 0.6, a new constant in pong_bots); flat returns drew 0-0.
7. P1: the step scripts hold 0.4 s at each end (the step itself 0.8 s, ratios 0.78 and 1.28 as planned); this is
   what brings range to 0.6287 (a 0.6 s hold gives response_px 9).
8. P1: asserts changed that the plan's list does not name: test_pong's feel-file check reads fidelity input "far"
   (the plan's own feel change); test_cpu_is_beatable's ball vy 90 -> 70; test_first_playable's duel test now asserts
   each paddle follows its own player's depth (r > 0.95, measured 0.995), not the other's (|r| < 0.5, measured
   0.107 and -0.083), span >= 32 px, in place of "left follows the cursor, right does not move" (cannot hold once
   player 2 steps). The duel's player 2 steps a quarter cycle behind player 1.
9. P1: Pong's `active` fires on a 14.4 px travel from an anchor, not on any 1 px move: under the scale jitter a still
   body counted as playing and the runner never asked "STILL PLAYING?".
10. P1: `idle_body` gained optional `body_id` and `seconds` parameters (scenario unchanged).
11. Suite time: 193.6 s after P1's first merge. I sent P1 back once, and it fixed this in eb71d04 and 50d6b29, which change no asserts, seeds, marks, budgets or constants.
    - test_oracle memoises plain `bots.play` results for its module, through a module-scoped monkeypatch.
    - test_pong's `bot_play` reads `tests.arcade.test_oracle.PLAYS` when the oracle has already measured those seeds.
    - Pong draws its net, hint and scores from masks cached per canvas. P1 checked that the frames are bit-identical: the sha256 over two seeds of good and lazy plays did not change.
    - Final time: 169.2 s.
    - A finding for the review: test_pong imports test_oracle. Their shared state speeds up the full suite only because test_oracle sorts first. Run alone, test_pong plays the games itself, so the tests stay correct either way.
15. Every assert any task changed, beyond the plan's named changes:
    - tests/arcade/test_festival.py `test_festival_guard_rails`, in the operator's d738df1:
      old: `assert (b.box, b.scale, b.vx, b.vy) == (truth.box, truth.scale, truth.vx, truth.vy)`
      new: `assert (b.box, b.vx, b.vy) == (truth.box, truth.vx, truth.vy)` plus
      `assert b.scale == dataclasses.replace(b, scale=0.0).scale`.
    - tests/arcade/test_input.py: S1's still-body test went in as `..._stays_within_0_18`, with the bound 0.18 in place of the plan's 0.15, in d738df1 (the operator's ruling).
    - tests/arcade/test_first_playable.py `test_two_players_walk_up_play_pong_and_see_the_card`, in P1's 8770f89:
      old: `left.max() - left.min() >= WALL[1] / 2`; `np.corrcoef(cursor, left)[0, 1] > 0.95`; `len(right) == 1`.
      new, for each paddle against its own player's `far`: span `>= WALL[1] / 2`; `np.corrcoef(far, paddle)[0, 1] > 0.95`; `abs(np.corrcoef(not_mine, paddle)[0, 1]) < 0.5`.
      P1 asked me for this ruling, but the message reached me only after P1 had committed. I have not ruled on it; it goes to the reviewer.
    - tests/arcade/test_pong.py `test_feel_file_overrides_have_reasons`, in 8770f89:
      old: `data["fidelity"] == {"input": "cursor_y", ...}`
      new: `"far"`. The plan's feel-file line implies this change.
    - tests/arcade/test_pong.py `test_cpu_is_beatable`: the ball's setup vy went from 90 to 70, with the asserts unchanged.
    - The plan's named changes, as listed: `CAPTION_KEYS` gains "near"; the hand-height test becomes `test_paddle_follows_depth`; the still-paddle and moving-player tests judge travel.
    - P1's time fix touched no assert.
16. Messages reached me late. The lead's rulings of 21:38, 21:44 and 22:04, and the implementers' questions, arrived only after the parallel tasks had finished. The operator therefore made the serial commit d738df1 and gave P1 its rulings directly. I did not add the still-body test myself, because d738df1 holds it.
12. The governor timing test `test_headless.py::test_tick_budget_with_the_governors_share[strobe|static-128x64]`
    failed in several task runs under a load average of 5 to 8 from other sessions, and at the base too. It passed
    in all three integration runs (load 1.3 to 3.6).
13. S1 and S2 committed while that load-flaky test failed (every other test green). S2 ran one command containing
    `cd /dev/null` (it failed at once, changed nothing). S1 used `git stash` twice on the main checkout for base
    timing, carrying the operator's uncommitted state.md through unchanged.
14. The operator's amendment 441564e (task S3, Q48: the scale holds through a hip dropout) and S3 itself (94045c6,
    merged 6ec798e) belong to the operator. I did not dispatch or merge S3. My final suite run covers it.

## Test status (command + counts)
Command, from /Users/trey/dev/codeisart: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
/Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs`
| point | HEAD | result | wall | load |
|---|---|---|---|---|
| base (S1's run) | 8ae1aea | 723 passed | 139.97 s | quiet |
| after P1 merge | 5fc0b7c | 750 passed | 193.63 s | 1.3 to 1.9 |
| after P2 merge | a448ff9 | 755 passed | 197.63 s | 1.6 to 3.6 (P1's time fix running) |
| after P3 merge | 887c144 | 755 passed | 223.03 s | 3.3 (P1's time fix running) |
| after P1's time fix (eb71d04), with S3 (6ec798e) | 8181012 | 762 passed | 165.28 s | 2.0 |
| **final, after P1's second perf commit (50d6b29)** | **e42b02e** | **762 passed, 0 skipped, 0 failed** | **169.23 s** | 1.5 to 2.0 |
The final time is under the 175 s limit: it is 29 s over the 140 s base, against a share of 35 s. 762 = 723 + 32 (it09's
tasks) + 7 (S3's). The governor timing test passed in every integration run.
Slowest in the final run: test_oracle setup 61.9 s, pong soaks 5.9 and 5.4 s, test_first_playable_keeps_the_flash_rule 3.8 s,
test_evidence_package_for_pong 3.3 s. test_good_beats_lazy_beats_nobody now reuses the oracle's plays (under 1 s).
P1's profile of what remains: the flash governor's `apply` in arcade/flash.py takes 40 of the 87 s of the oracle's plays. That file is outside every game task, so the time is left as a finding.
Slowest after the first P1 merge: test_oracle setup (test_feel_pong_meets_its_budgets) 66.1 s (39.1 s at base), test_good_beats_lazy_beats_nobody
16.1 s (8.8 s), test_evidence_package_for_pong 9.8 s, pong soaks 6.2 and 5.7 s.

## Pong's feel at 128x64 (every metric, value, budget; failures)
From P1, `bots.seeds(Pong, "128x64", 20)`, final constants. No failures; no band loosened.
| metric | value | budget |
|---|---|---|
| response_ticks | 1.0 | max 2 |
| response_px | 12.0 | min 12 (margin 0; per probe 6, 12, 4, 6, 12, 18, 18, 12) |
| fidelity | 0.9947 | min 0.8 |
| range | 0.6287 | min 0.6 |
| lit_fraction | 0.039 | 0.01 to 0.5 |
| dim_fraction | 0.1147 | max 0.3 (existing override, the dashed net) |
| liveliness | 0.0035 | min 0.001 |
| flash_area_raw | 0.0 | max 0.1 |
| square_flashes | 0.0 | max 6 |
| score_visible | 1.0 | min 0.8 |
| score_legible | 1.0 | min 0.9 |
| phases_reached | 1.0 | min 1.0 |
| round_seconds | 66.05 | 20 to 120 |
| win_good | 1.0 | min 0.7 |
| win_lazy | 0.25 | 0.1 to 0.7 |
| win_none | 0.0 | max 0.05 |
Good bot rounds (s): 92.0, 57.3, 80.2, 74.1, 62.9, 60.0, 86.3, 82.7, 53.1, 63.5, 64.6, 63.8, 55.0, 52.2, 67.5, 73.5,
92.0, 80.4, 42.7, 68.7; median 66.05. 18 of 20 end by points (5-0); 2 at the 92 s cap (4-0, still won).
Final constants: BALL_START 55, BALL_GAIN 1.08, BALL_MAX 95, MAX_ANGLE 50, CPU_SPEED 0.3, PADDLE_W 3,
PADDLE_SHARE 0.25 (16 px), TRAVEL_SHARE 0.3 (14.4 px), NEAR_IS_UP True, HINT_IDLE_SECONDS 5, HINT_FADE 0.3.

## Lag and jitter (P1's measures)
Lag from a body's step (ratio 1.0 to 1.28 at once, and as a 0.5 s ramp; paddle travel 19.7 px) to Pong's paddle,
one tick = 1/30 s, no dropout:
| camera | latency | step | first pixel | 90 percent of the travel |
|---|---|---|---|---|
| 10 a second | 0 (clean) | instant | 3 ticks, 0.100 s | 8 ticks, 0.267 s |
| 10 a second | 0 | 0.5 s ramp | 3 ticks, 0.100 s | 17 ticks, 0.567 s (0.117 s after the body's own 90 percent) |
| 10 a second | 0.15 s (REAL_NOISE) | instant | 8 ticks, 0.267 s | 13 ticks, 0.433 s |
| 10 a second | 0.15 s | 0.5 s ramp | 8 ticks, 0.267 s | 22 ticks, 0.733 s |
| 30 a second | 0 | instant | 1 tick, 0.033 s | 3 ticks, 0.100 s |
| 30 a second | 0 | 0.5 s ramp | 2 ticks, 0.067 s | 15 ticks, 0.500 s (0.050 s after the body's) |
| 30 a second | 0.15 s | instant | 6 ticks, 0.200 s | 8 ticks, 0.267 s |
| 30 a second | 0.15 s | 0.5 s ramp | 7 ticks, 0.233 s | 20 ticks, 0.667 s |
The Glide adds about 0.1 to 0.25 s past the camera's own latency at 10 a second, under 0.07 s at 30.

Jitter, a still body under REAL_NOISE with the scale jitter (d738df1), 10 seeds x 60 s:
| measure | value |
|---|---|
| paddle y range, worst 6 s window | 9.14 px (per-seed medians 4.2 to 6.4 px) |
| paddle y range, worst 60 s | 9.57 px |
| tick-to-tick SD | 0.37 to 0.42 px |
| steps or glide | glides: y changes on every tick; about 9 drawn 1 px moves a second (a third on capture ticks) |
| worst rally travel | 7.6 to 8.3 px against the 14.4 px threshold: no point banks (10 of 10 seeds) |
Finding (not in code): a 1 px hysteresis on the drawn y would cut the shimmer to about 200 moves a minute; the plan
fixes the paddle formula, so it is the owner's call after the smoke.
S1's Depth-level numbers: a still body's Depth range up to 0.168 (8.1 px of 48); tracker scale at SCALE_TAU 0.1 reaches
0.63, 0.86, 0.95 of a x1.3 step on captures 1, 2, 3.

## Commits (sha + subject)
8ae1aea to e42b02e (main), oldest first:
- f82eda9 feat(arcade): it09 S1, Glide and Depth controls, tracker scale, SessionResult.new_best
- de01b4a feat(arcade): it09 S2, bodies that step in depth for actors, bots and feel
- d228c35 docs(arcade): it09 P3, the guide's Controls section, the second live smoke, arcade.mac.toml
- f7efc01 feat(arcade): it09 P2, the end card says BEST! only for a new best above 0 (C43, Q41)
- d738df1 feat(arcade): it09 serial: degrade jitters the scale; the still-body bound is 0.18 (the operator)
- 8770f89 feat(arcade): it09 P1, Pong by the body: Depth paddle, travel (C42), the step hint
- d6fcf12 Merge main (d738df1: degrade jitters the scale) into it09 P1
- 5fc0b7c Merge it09 P1: Pong by the body (Depth paddle, travel C42, step hint)
- a448ff9 Merge it09 P2: the end card's BEST! only for a new best above 0 (C43, Q41)
- 441564e docs(plan): it09 amendment, the scale survives a hip dropout (S3, Q48), from the owner's hand-read spike (the operator)
- 887c144 Merge it09 P3: the guide's Controls, the second live smoke, arcade.mac.toml
- 94045c6 feat(arcade): it09 S3, the tracker's scale survives a hip dropout (Q48) (the operator's task)
- 6ec798e Merge it09 S3: the tracker's scale survives a hip dropout (Q48) (the operator)
- eb71d04 perf(arcade): it09 P1 suite time: the oracle's bot plays are shared, Pong draws from cached masks
- 8181012 Merge it09 P1's suite-time fix: shared oracle plays, Pong's cached masks
- 50d6b29 perf(arcade): it09 P1, Pong's net and hint masks as indices; frames bit-identical
- e42b02e Merge it09 P1's second suite-time commit: Pong's masks as indices
Branches left in place (not deleted): worktree-agent-aa74db8c55411b189 (P1), worktree-agent-aef8e523bc9b0245f (P2),
worktree-agent-ad27493d47c927fd6 (P3), all merged. Nothing pushed. The operator's uncommitted docs/superpowers/workflow/state.md
is untouched.

## Minutes (serial lane, parallel tasks, integration)
| phase | start to end (CDT) | minutes |
|---|---|---|
| serial: S1 | 21:05 to 21:42 | 37 (it ran the full suite several times under load 5 to 8) |
| serial: S2 | 21:42 to 22:01 | 19 |
| parallel: P1 / P2 / P3 | 22:02 to 22:36 | 34 (P1 34, P2 11, P3 7) |
| integration: merges, suites, P1 sent back once (22:40 to 22:50), report | 22:36 to 23:00 | 24 |
| total | 21:05 to 23:00 | about 115, against the 60 planned |
