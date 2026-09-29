# Iteration 8 review, round 1 (range 167d513..2e016e5)

Reviewer: it08-reviewer. Plan: docs/superpowers/plans/2026-09-28-it08-four-panel-wall-128x64.md. No repository file changed, no commit.

Suite, run once from the repo root with the plan's command: **723 passed, 0 skipped, 0 xfailed, 141.43 s**, exit 0.
`pytest --collect-only -q | tail -1`: **723 tests collected** (675 at the base: no drop). Skips: 0 (0 at the base).
Output: scratchpad/it08-probe-suite.txt. Probes: scratchpad/it08-probe-*.py.

## Verdict: APPROVED

## Blocking findings (file:line, the input, what happens, why it blocks)

None.

The strongest candidate is C41's rule (ruling 3). It does not block: the code does what the plan's rule says, and C41's own case (an idle body with its hands down) holds on clean input and under REAL_NOISE. The rule itself needs the owner's ruling (see ruling 3 and "Noted").

## Rulings on the twelve points (each REPRODUCED or READ)

**1. Pong's ball at 100 to 170 px/s, at 128x64: REPRODUCED. No pass-through, the ball never leaves the field, it never sticks.**
- Direct physics (it08-probe-ball.py) ran 1,041,120 cases:
  - speeds 100, 120, 144 and 170 (BALL_MAX, 5.67 px a tick);
  - angles -60 to 60 degrees in 0.5-degree steps;
  - 10 start rows including 1 and 63, and 6 sub-tick phases to the plane;
  - paddle offsets of up to +/-8.99 px from the continuous path's crossing (drawn rows overlapping, clamped as the game clamps);
  - dt at TICK and at the runner's MAX_DT of 0.1 s.
- Result: 0 pass-throughs and 0 steps with the ball outside rows 1..63.
- Why: the swept plane test (`pong.py:269-278`) catches any crossing; interpolating y after a wall reflection errs only within about 5 px of a wall, where the clamped paddle (centre 8..56) covers the ball anyway.
- Seeded plays through the real runner (it08-probe-plays.py) used an instrumented Pong that flags any plane crossing without a bounce while the paddle was within 9 px of the continuous path, on either side, and any ball outside rows 1..63.
  - Good bot, `bots.seeds(Pong, "128x64", 200)`: 200 of 200 won, 199 ended by points, median 48.6 s, **0 events**.
  - A further 280 plays of slower bot variants: 0 events.
- Stuck: impossible. |vx| >= speed x cos 60 degrees = 50 px/s, and every play ended.

**2. Is the retuned Pong humanly playable? REPRODUCED. A ruling for the owner, not blocking.**
- Arithmetic:
  - A flat ball at BALL_MAX crosses between the paddle planes (122 px) in 0.72 s, 21.5 ticks.
  - The paddle centre is clamped to 8..56. From one end, the paddle must travel about 46 px to meet a ball at the far rows.
  - With no reaction time: 2.1 px a tick (64 px/s, about one reach-box height a second).
  - With a 0.25 s human reaction plus REAL_NOISE's 0.15 s camera latency, 9.5 ticks remain: **4.8 px a tick (145 px/s, 2.3 reach-box heights a second)**.
  - This is the worst case. At 60 degrees the same ball takes 1.44 s.
- The Good bot (`pong_bots.py:31`) has a 3-tick reaction (0.1 s), noise 0.02 (1.3 px), a perfect 30 fps camera with no latency, exact bounce prediction, and a paddle that teleports.
- The 20 of 20 does not depend on that. Measured, with Good's aim but a human-like hand (40 seeds each):
  - reaction 6, 8 or 10 ticks: 40 of 40 won;
  - reaction 10 ticks (0.33 s) with the hand limited to 0.03 of the reach a tick (1.9 px a tick): 40 of 40 won, the CPU scoring 0.18 points a play;
  - the same with 0.02 a tick (1.26 px a tick): 39 of 40 won, the CPU scoring 1.8 a play.
- So a player moving at about 60 px/s with a third of a second of delay beats the CPU. The CPU (0.35 wall heights a second, 22 px/s) is what the tuning made weak. Good never concedes a point (5-0 in 40 of 40).
- For the owner's live smoke: the ball is fast by eye, and the CPU is easy.

**3. C41 (Q35): REPRODUCED. Per the plan's rule, but the rule sits at the camera's noise level.**
Source: it08-probe-c41.py, plus a 10-seed rerun. Every run went through `run_headless` at 128x64 with no lobby. A logging subclass records each goal: banked or not, whether the scorer returned the ball, and the px the scorer's paddle moved in the rally.
- **Idle body, hands down:** 0 points and no best on 10 of 10 seeds under `degrade(REAL_NOISE)`, as on clean input. C41's own case holds. The down wrist's cursor clamps at the bottom, so it never moves 1 px.
- **A well-placed paddle that never moves (clean input):** the scorer returned the ball, the CPU missed, and the point was not banked (seed 516029113, t 10.9). This is the plan's intended rule.
- **A slow tracker (clean input):** wrist 0.4 to 0.6 of the reach every 1.5 s, which is 0.14 px a tick. The paddle moved **16.8 px** (seed 2278075139, t 5.67) and **19.6 px** (seed 516029113, t 11.4) in the rally. The player returned the ball, the CPU missed, and the point was **not banked**, because no single tick reached 1 px.
  - This meets the plan's "(1 px or more on some tick)". It misses Q35's own wording, "moved the paddle 1 px or more in the rally".
  - Under REAL_NOISE the same player lost nothing in 3 seeds, because jitter trips the rule.
- **The same rule counts jitter as movement:**
  - A still raised hand under REAL_NOISE moves the paddle by a median 1.84 px per capture, and 1 px or more on 267 of 388 captures. When the wrist drops out, the cursor jumps to the other wrist, with steps of up to 33.7 px.
  - A player who stands perfectly still with a hand up therefore **banked points on 7 of 10 seeds** (12 points in all, one a 5-point win) and **stored a best on 10 of 10** (0.0 to 5.0).
  - Q35's question is "Does a player who stands still bank points?", and its default answer is "no". On the live camera, the 1-px rule cannot tell a still raised hand from a moving one.
- **What follows an unbanked goal:** the `point` phase runs its 1 s with no "+1" and no shake, the serve goes toward the side that conceded, and then `_assign` and a normal serve follow (`pong.py:300-312`).
- **Duel:**
  - Both hands still on clean input: neither side ever scores (25 to 28 unbanked goals a game). The round ends at MAX_SECONDS, 0-0 (92.0 to 92.7 s, phase over), with no best. It does not hang.
  - The duel script, where player 2 holds mid-height: every point player 2 wins goes unbanked (7 of 12, 1 of 6 and 16 of 21 human goals). Several of them followed player 2's own return.
- My recommendation for the next Pong task, if the owner agrees: judge movement by the paddle's range over the rally against a threshold above the jitter. Details under "Noted".

**4. C38: REPRODUCED.**
- On Pong at 128x64 with seed `bots.seeds(Pong, "128x64", 20)[0]` (3347246262), `feel._canonical` gives **response_ticks 1.0 and response_px 28.0 at PROBES 4, 8 and 16 alike** (probes [149, 315, 454, 589], 8 probes and 16 probes respectively).
- The launch goes through the lobby. The trace shows attract, mirror and invite before the launch. The launch is at trace tick 135, the same as canonical's raise at 4.5 s (record 135).
- The metrics count [first, stop): the raised hand's session only (`feel.py:321-329`). Pong's session runs to the end of the 20 s window.
- S2's deviation hides nothing:
  - The launch tick's raw frame is the lobby's (454 lit px, no Pong net). The game's first frame is tick 136 (the net is drawn).
  - Counting from the launch tick gives flash_area_raw 0.0, square_flashes 2 (budget max 6) and the same lit_fraction 0.0257.
  - The pushed flash_area over the lobby-to-game switch is 0.0, with 0 held ticks.
  - Starting one tick later is correct, and no budget would fail with or without the launch tick.

**5. C39: REPRODUCED.**
- Pong's scores are drawn at 2x at 128x64, for every pair from 0..5 x 0..5. Every one was found by `find_text` at SCORE_SCALES (2,) with legibility at 5 m of 0.9 or more.
- The oracle's canonical (seed as above): score_visible 0.974 and score_legible 1.0.
- The scores are not clear of the ball's path: they sit in rows 1-14, and the ball uses rows 1-63. The ball and the shake hide them on 2.6 % of ticks, within the 0.8 floor.
- They do not overlap the paddles (columns 0-1 and 126-127) or the net (column 64).
- A stub with `pong.SCORE_SCALE = 1` gives **score_visible 0.0 and score_legible None**, and `judge` names both. The oracle now refuses a 1x score.

**6. I1's stub edit (`tests/arcade/test_feel.py:184-196`): REPRODUCED (the suite) and READ.**
- The only change: `Scorer.draw` draws at `scale=2` always (it drew at 1x before 2 s), and the docstring says so.
- `test_score_visibility_counts_the_ticks_it_is_shown` keeps every assert: `score_visible == approx(0.75)`, legible over the floor, and the one failure "score_visible 0.75 < min 0.8".
- The test still tests what its name says. The score is hidden on the first second of every 4 (`t % 4 < 1`), which gives exactly 0.75. The 1x frames were a leftover of the (1, 2) scales, and `test_a_1x_score_is_not_visible` now covers 1x.

**7. The lobby at 128x64: REPRODUCED.** Source: it08-probe-lobby.py.
- Raw `concurrent_area` of the lobby's own drawing under `degrade(REAL_NOISE)`, 20 s each, stays under 0.1 with 0 held ticks:

  | Scene | concurrent_area |
  |---|---|
  | standing | 0.0615 |
  | walking 0.2 to 0.8 and back | 0.0361 |
  | slow walk | 0.0635 |
  | two players | 0.0664 |
  | two players crossing | 0.0615 |

- A walk-up to card run with Pong under REAL_NOISE went attract, mirror, invite, pong, card, with **0 held ticks**.
- COLUMN_SLACK:
  - The drawn column never differs from `figure_rect`'s by more than 1, on clean input or under noise, walking or standing.
  - A walker's figure does trail by exactly 1 column for most of a walk (194 of 240 ticks).
  - When the slot's person changes (id 1 leaves, id 2 takes the slot), the drawn x equals `figure_rect`'s on the first tick: no lag and no carried offset.
- The card and the title:
  - Cards covered titles "PONG", "COPY ME" and "PONG CHAMPIONSHIP"; scores 3, 5 with best 5, 12345 with best 100, and none; waiting on and off; at 128x64, 128x32 and 64x64.
  - Every card is drawn whole: its lit pixels equal the lines' own pixels, and the block fits the rows.
  - The attract titles are whole and centred. At 128x64: "PONG" at 2x (rows 24-37), "PONG CHAMPIONSHIP" at 1x. At 128x32: 1x. At 64x64: "PONG" at 2x, and the long title wrapped into 3 lines at 1x.

**8. S2's finding: REPRODUCED. Real, not a requirement missed.**
- Pong's canonical through `Lobby([Pong])` at 128x64 relaunches Pong after every card. Launches at ticks 135, 714, 1326, 1974 and 2946; cards begin at 597, 1224, 1876 and 2832.
- Each relaunch comes 3.3 to 3.9 s after its card begins, which is 0.3 to 0.9 s after the 3 s card ends: the sweep's top is a raised wrist.
- The duel script relaunches once (card at 2126, launch at 2238).
- Q24 and Q25 hold at 128x64 (a spy game, `lobby.py:165-191`):
  - A hand raised during the card does nothing.
  - A hand up across the card's end (4.6 to 5.6 s) launches nothing until it is raised again (launch at 6.53 s).
  - A hand held up from 2.5 s and never lowered launches nothing after the card.
- A sweeping player goes back into the game because the card says "HAND UP = AGAIN". Whether the top of a sweep should count as a hand up is the owner's call (Noted).

**9. The engine at undeclared sizes: REPRODUCED.**
- Pong's solo and duel scripts (seed 7) finish (`done()`) with no crash:

  | Size | Solo: score_visible, score_legible | Duel: score_visible, score_legible |
  |---|---|---|
  | 128x32 | 0.912, 1.0 | 0.763, 1.0 |
  | 64x64 | 1.000, 1.0 | 0.995, 1.0 |
  | 96x48 | 0.960, 1.0 | 0.959, 1.0 |
  | 128x64 (for reference) | 0.994, 1.0 | 0.997, 1.0 |

- Every 2x score pair is found and legible at all four sizes. The suite's soak also passes at 128x64 and 96x48.
- 128x32's duel at 0.763 is below the declared-layout floor, but 128x32 is undeclared and the scores stay legible (Noted).
- `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m arcade run --seconds 3 --script walkup` exits **0** and logs `INFO arcade.main: wall 128x64, backend sdl` (scratchpad/it08-probe-run.txt). `test_run_opens_a_128x64_wall_by_default` spies `build_display` at (128, 64).

**10. The tools: REPRODUCED.**
- `python -m tools.wall_pattern index --png <scratchpad>/it08-probe-index.png` saved a 1024x512 PNG (128x64 at 8x).
- Column seam: column 63 is cyan and column 64 yellow over every row off the row seam. Row seam: row 31 cyan, row 32 yellow, full width.
- The four corners are marked: red top left, green top right, blue bottom left, white bottom right, 2x2 each.
- Lit share 0.051, max byte 128.
- The CAP (0.4) and `--brightness` lines are context lines only in the diff, so they are unchanged.
- `arcade_evidence._feel_table` on Pong's real budget table prints `| presence_answer_seconds | 0.0 | - | - |`, `yes` for budgeted metrics that pass, and `no` for a missing value under a budget.

**11. The tick budget at 128x64: REPRODUCED.**
- This run: strobe mean 0.531 ms (p95 0.570, governor 0.345, held 200 ticks) and static mean 0.495 ms (p95 0.511, governor 0.306), against **2.0 ms**.
- `BUDGET_MS` (`tests/arcade/test_headless.py:15`) is unchanged. The diff only adds `WALL` to the parametrize.

**12. Safety files: REPRODUCED.**
- `git diff 167d513..2e016e5 --stat -- arcade/flash.py arcade/brightness.py show/display/colorlight.py arcade/runner.py` prints nothing: none of them changed.
- Protocol: since `game-protocol-v1`, `arcade/game.py` changes only in the `LAYOUTS` line and the GameInfo docstring. S1's commit carries "Q33: LAYOUTS is a data value; the protocol's members are unchanged".
  - `runner.py`, `headless.py`, `sensed.py` and `canvas.py` are unchanged, so what the runner passes a game is unchanged.
  - `juice.py` changes only its constructor's fallback size (named in S1).
  - The canary `test_protocol_members_are_the_frozen_set` is not edited and passes.

## Removed or changed asserts

Every `-` assert line in `git diff 167d513..2e016e5 -- tests/`:

| # | File: assert (old) | Ruling |
|---|---|---|
| 1 | test_config.py:20 `cfg.size == (128, 32)` becomes `(128, 64)` | replaced, named (S1) |
| 2 | test_config.py:99 `ArcadeConfig().layout == "128x32"` becomes `"128x64"` | replaced, named (S1) |
| 3-7 | test_feel.py:497-503, the five `find_text(...)` asserts in `test_find_text_locates_the_score_at_either_scale` | equal: the same asserts with `scales=BOTH` (1, 2) passed explicitly, as the plan names (S2) |
| 8-9 | test_feel.py:511-514, the two `legibility(frame, *find_text(...))` asserts | equal: the same thresholds; only `find_text` gets `scales=BOTH` so the 1x digits are still found after SCORE_SCALES (2,) (same reason as 3-7; not named separately) |
| 10-15 | test_figure.py, `test_figure_rect_follows_zone_x_and_fills_the_height` (2) and `test_mirror_draws_2px_figure_in_player_colour` (4) | extended: the same asserts, moved from a loop over (128, 32), (64, 64) to the module's `size` fixture, which adds (128, 64) |
| 16 | test_game.py:56 `LAYOUTS == {"128x32", "64x64"}` becomes `{"128x64"}` | replaced, named (S1) |
| 17 | test_pong.py:77 layouts `{"128x32"}` becomes `{"128x64"}` | replaced, named (P1) |
| 18 | test_pong.py:390 the walk-up assert: only the message's `seed("128x32", 3)` becomes `seed("128x64", 3)` | equal |
| 19 | test_arcade_shot.py:177 `run_shot(...) == 0` gains `"--size", "128x32"` | equal: it pins the size whose name the same test checks in the header (the old default); not in the plan's list; the orchestrator's deviation 7 reported it; not weakened |
| 20 | test_wall_pattern.py:225 `im.size == (128 * 8, 32 * 8)` becomes `(128 * 8, 64 * 8)` | replaced, named (P3) |

Changes that are not asserts:
- `test_wall_pattern.py:71` keeps the same two layouts in its own list, and 128x64's seams are asserted by the new test (equal).
- `test_lobby.py`'s mirror test drops its own parametrize and runs on the three-size override (extended).
- The `test_feel.py` stubs now run an 8 s canonical instead of 21 s, with the same asserts.
- `test_pong.py::test_cpu_is_beatable` changed its input (ball from x 96, vy 90) with the assert unchanged. I ran the old input (x 64, vy 43) at HEAD and it passes too, so the test is no weaker.

**None weakened.**

## Noted, not carried (one line each)

- C41/Q35, for the owner: the 1-px-on-a-tick rule counts camera jitter. A still raised hand under REAL_NOISE banked points on 7 of 10 seeds and stored a best on 10 of 10. On clean input a slow tracker who moved 17-20 px in the rally lost earned points. Suggest the paddle's y range over the rally at or above a threshold above the jitter (a still hand's median capture step is 1.84 px, and a dropout jumps it up to 34 px, so the range needs dropout-robust input, such as the cursor held through `capture_grace`).
- The plan's "(1 px or more on some tick)" narrows Q35's "1 px or more in the rally". The code follows the plan.
- Pong's balance, for the live smoke: Good concedes 0 points in 40 of 40 plays. A bot with a 0.33 s delay and a 1.9 px-a-tick hand still wins 40 of 40. The CPU at 22 px/s may be too easy, while the ball (up to 170 px/s) looks fast.
- The sweep's top counts as a raised hand in the lobby, so canonical and duel players relaunch Pong 0.3-0.9 s after each card. Q24 and Q25 hold; whether a sweep counts as "hand up" is the owner's call.
- A walking figure trails the body by 1 column for most of a walk (COLUMN_SLACK's backlash), never by more. Copy Me and the attract director use `figure_rect` without the slack (P2's finding).
- Pong at 128x32 (undeclared): the 2x scores fill 14 of 32 rows and the duel's score_visible is 0.763; the scores stay legible. The CPU at 128x32 is 11 px/s.
- `test_cpu_is_beatable`'s comment says "reaching the far side of the field in 0.5 s"; the ball reaches the CPU's plane in 0.2 s.
- Pong's canonical under the lobby relaunches after the first card. The I2 GIF of canonical will show several sessions (the new first-playable test stops at the first card).
