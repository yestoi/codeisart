# it19 code review: bb9fd70..e356f3a (13 commits)

References: the plan `docs/superpowers/plans/2026-10-01-it19-four-pose-games.md`, the spec
`docs/superpowers/specs/2026-09-26-wall-arcade-design.md`, `plan-review.md`, the orchestrator's and G1 to G4's
reports. Read: `arcade/bots.py`, `arcade/poses.py`, the four games and their bots modules, the feel tomls, the five
changed test files, and the runner, juice and figure code they lean on. Probes were run from a scratch directory outside
the repository, straight through each game or through `run_headless`; their numbers are below. Nothing in the tree was
changed but this file.

## Verdict: BLOCKED

One plan requirement is not met in two games: "Rows 60 to 63 stay free (the runner's marker)" (plan, Global
Constraints, line 15). Freeze's topple and Flap's hint and floor-crash wings draw there. Each fix is a line or two.
Everything else holds: no assert is removed or weakened, the collected count only rose, no skip was added, every flash
probe passes at full length, and B1 to B8 and N1 are closed in the code.

## Blocking findings

### 1. Freeze: an out player's topple lights rows 60 to 63

- Where: `arcade/games/freeze.py:427-449` (`_draw_fall`). The file's own constant claims the opposite, at
  `freeze.py:61` (`BORDER_ROWS = 60  # ... rows 60 to 63 stay free`).
- Input: `Freeze.SCENARIOS["canonical"]` driven through the game with the test's `make`/`drive`.
- What happens: seat a goes out at t 8.27 s. On each of the next 52 ticks (1.7 s, the whole topple and fade), the
  game's own frame lights rows 60, 61, 62 and 63, starting at columns 38 to 39. In `duo`, seat b goes out at 8.13 s:
  52 ticks, rows 60 to 63, starting at columns 83 to 84. Through `run_headless`, every lazy-bot seed that slips lights
  52 ticks per out, and the canonical through the lobby lights 156 ticks.
- Why: `_draw_fall` turns the skeleton 90 degrees about its feet, which lays it along the feet row. The 2 px thick line
  and the head circle then reach below that row, and nothing clips them at row 59.
- Why it blocks:
  - It breaks a stated Global Constraint.
  - The topple is drawn in `PLAYER_COLORS[i]`, the same colour as the runner's marker (row 63, `juice.py:249`) and
    echo (rows 59 to 61, `juice.py:253`).
  - `_out` fires `fx.echo(i + 1, "hit")` (`freeze.py:284`) on the same tick. So the out's only acknowledgement, the
    "hit" glyph, and the marker merge into one block of the same colour.
  - Every out in every Freeze game does this.
- Fix: clip the topple's points to row 59 or above, or lay the body down above its feet row.

### 2. Flap: the hint text and the floor-crash wings light rows 60 and 61

- Where, the hint: `arcade/games/flap.py:349`. `HINT_TEXT` is drawn at y = round(64 * 0.7) + 7 + 3 = 55, and a 7-row
  glyph covers rows 55 to 61. It is drawn in `TEXT_COLOR` (255, 120, 0), which is player 1's marker and echo colour.
- Input for the hint: any still body in `ready` for `HINT_IDLE_SECONDS`, for example `Flap.SCENARIOS["idle_body"]`.
- What happens with the hint:
  - At 4 s, `hint` is True and rows 60 and 61 are lit.
  - Through `run_headless`, the game's own drawing lights rows 60 and 61 on 990 ticks of `idle_body`, 180 of `nobody`
    and 76 of `one_arm`, all from the hint.
  - Drawn alone, the hint text lights rows 55 to 61.
- Where, the wings: `arcade/games/flap.py:371`. The wings-down rectangle is drawn at `top + BIRD_H`.
- Input for the wings: one flap at 1.3 s, then both hands down.
- What happens with the wings: the bird crashes on the floor at `bird_y` 57.53, so top is 56. Rows 60 and 61 at
  columns 26 and 27 then stay lit for 37 ticks, the whole crash fade (play at 4.13 s through over at 5.33 s). This
  happens on 6 of 6 seeds.
- Why it blocks: it breaks the same Global Constraint. The hint shares rows 59 to 61 with the echo glyph and has the
  same colour as player 1's echo. A hesitant player's first seconds in `ready` are exactly when the hint shows.
- Fix:
  - Draw the hint at y 53 or above (rows 53 to 59). In `ready`, `READY_TEXT` stays on rows 45 to 51.
  - Keep the wings at row 58 or above when the bird is on the floor.

Copy Me and Swat never light rows 60 to 63: probes of every scenario and every bot seed found 0 ticks.

## Noted, not carried

- `tests/arcade/test_copyme.py:543` skips the lit-pixel check for rows 0 to 15 at columns 0 to 48 or 80 to 127. In
  `duo`, every head falls in that region, so the check never runs: 0 checks ran and 1396 were skipped, though all 1396
  points were in fact lit. Without the skip, the canonical's `player_xy` is lit on 676 of 676 ticks. The test is weak;
  the code is right.
- `tests/arcade/test_flap.py:410-411` skips `gap_xy` entirely, including its bounds check.
- Swat's tests use shortened windows: the flash rule 40 s (`test_swat.py:523`), the still body under noise 25 s
  (`:409`), idle 20 s. Full-length probes hide nothing:
  - the 70 s `canonical` and `duo` on 4 seeds: `flash_area` at most 0.006, held 0, `square_flashes` 2 of 6;
  - the still body under `REAL_NOISE` to `over` (66 s), 5 seeds at 2 heights: score 0, cut 0, never `active`, best
    None.
- Freeze's still-body test (`test_freeze.py:194`) does not assert that the seat joined, but the probe shows it is real
  on all 5 seeds: the seat joined at 3.0 s, all 6 reds were judged, and the largest travel in a red was 0.079 to 0.089
  against `MOVE_TRAVEL` 0.25.
- Flap banks a best in `done()` 3 s after a non-final crash, so a player who walks away still banks it (leave is 8 s).
  A best is lost only if the 180 s cap lands in the first 3 s of an `over`.
- Freeze joins a seat only when its body is seen on the green's first tick (`freeze.py:256`). A real camera that misses
  that one tick delays the join by one green. `REAL_NOISE` drops whole bodies only in its first 0.15 s, so no test
  meets this.
- Freeze binds a seat to its tracker id for good (`freeze.py:196-201`). If a solo player's id changes after more than
  the grace, the player is out without a topple and the game ends.
- Swat can fire a combo flash on the same tick as a bomb hit. The flash rule held in every probe.
- Every game's own test file runs 13 to 23 s, against the plan's 6 s. The suite runs 484 s, inside Q102's 540 s.

## Removed or changed asserts (`git diff bb9fd70..HEAD -- tests/`)

None. The diff is 2287 lines added and 3 removed. All 3 removed lines are in `tests/arcade/test_bots.py`, and none is
an assert:

- an import line, widened from `RIGHT_WRIST` to `LEFT_HIP, RIGHT_HIP, RIGHT_WRIST`;
- `def probe(noise, move, seed, font)`, which became `def probe(noise, move, seed, font, game=Probe)`;
- `play(Probe, ...)`, which became `play(game, ...)` with the same arguments.

No `skip`, `xfail` or `importorskip` line is added or removed.

## Counts

- Collected: `pytest --collect-only -q` at e356f3a gives 2086, against 1881 at the baseline (+205). It did not drop.
- Skipped: no skip marker is added. The orchestrator's full run gives 2083 passed and 3 skipped in 484.03 s, the base's
  three. I did not rerun the whole suite while the evidence tool was running.

## Declared deviations

### G1 Copy Me

| Deviation | Judgement |
|---|---|
| The canonical walks one way, 0.15 to 0.85 | Free choice: a fixture; the plan's walk measured range 0.59 |
| Poses cycle only in the last `SCORE_WINDOW`, ±0.25 s | Free choice: a fixture |
| The torso axis needs both hips and both shoulders, then the shoulder line's normal, then vertical (`copyme.py:124-134`) | Free choice with a measured reason: `hip_mid` let one hip tilt the axis by about 20 degrees under noise. No band or assert moved, and the still-body test passes on every `LADDER` pose |
| `active` is sampled only when every judged limb is seen | Free choice: the plan defines what `active` is, not when it is sampled. The still-body test shows it never fires |
| "MATCH!" shows for either seat | Free choice: the plan does not name a seat |
| The fresh-pose rule (`copyme.py:448`) | Meets the plan: a share under `FRESH_SHARE` in `show` or `play`, applied per seat (the plan names player 1). A held `t_pose` scores 0 |
| A refused flash becomes a burst | Free choice; it meets the rule that every `fx.flash` return is checked |
| A score is recorded only when the total is over 0 | Free choice: the plan's "when a round counted" |
| The target's name shows only in `show`; `LADDER` lives in `copyme.py`; the outline test measures arm span | Free choices |
| The lazy bot copies only `LADDER[2][0]` in round 3 | A named lever (bot numbers) |

### G2 Flap

| Deviation | Judgement |
|---|---|
| Lazy `reaction_ticks` 9 to 10 | A named lever |
| The window test's reading; `bird_vy` = `FLAP_VY` on the flap's tick; a restart waits for the crash fade; the canonical runs 60 s | Free choices |
| The best run is recorded at the last run's end or in `done()` | Free choice: the same as the plan's "once, at the last `over`" except at the cap edge noted above |

### G3 Swat

| Deviation | Judgement |
|---|---|
| `GOAL` 25 to 30, `SPAWN_EVERY` (1.4, 0.8), `BOMB_SHARE` 0.2, and the bots' numbers | Named levers (plan line 217). Result: good 0.95, lazy 0.35 |
| `test_debug_state_is_clean` skips a blade under the score box (`test_swat.py:449`) | Free choice, and justified: in `duo` over 25 s, 2122 checks ran and 88 were skipped, every one of them dark (under the black box the plan draws last). None was skipped though lit |
| The canonical sweep takes 1.5 s; the bomb is a fat plus; `swipe` and `spawn` are public | Free choices |
| The flash, lobby and idle tests run 20 to 40 s windows | Free choice. The full-length probes above pass |

### G4 Freeze

| Deviation | Judgement |
|---|---|
| `COUNT_LAG` 0.3 (`freeze.py:57`, `:259`) | Free choice: it only waits for captures stamped inside the red (latency 0.15 plus one 0.1 s capture). Judging still goes by capture time, and `GRACE` is untouched |
| A duo survivor counts the red it stood through (`freeze.py:289-292`) | Free choice: `_count` still requires the green's dance (`:267`), so C41 holds |
| The canonical has no side steps; `idle_body` asserts score 0 and best None (it ends "inactive" at about 35 s); the over words | Free choices |

### Orchestrator

| Deviation | Judgement |
|---|---|
| Items 1 to 3, 5 and 6 | Free choices. The timing failure in item 3 is one of the three named load tests |
| Item 4, every game's own test file over 6 s | A plan budget missed, inside the suite cap. Noted |

No deviation breaks a rule: no assert or band moved, no `*_feel.toml` override was added, and every `needs` is
`{"pose"}`.

## plan-review.md B1 to B8 and N1 against the code

| Item | In the code |
|---|---|
| B1 | Closed: Freeze's lazy bot (`LAZY_GREEN` 4.5, a 1 s slip) wins 0.4 |
| B2 | Closed: Copy Me's lazy bot copies round 3 only on `LADDER[2][0]` and wins 0.4 |
| B3 / N1 | Closed: a flap before `READY_SECONDS` arms the run (`flap.py:182`, `:241-244`) |
| B4 | Closed: a cut needs the unglided Cursor v under `CUT_V_MAX` 0.85 (`swat.py:209`). The still-body probe above confirms it |
| B5 | Closed: `SPAWN_Y` is 57, and a falling fruit is removed at `SPAWN_Y` (`swat.py:274`). The test asserts y + R ≤ 59 |
| B6 | Closed by tuning: Flap good 1.0, lazy 0.6 |
| B7 | Closed: `exit_gesture=False` (`flap.py:118`) |
| B8 | Closed: `test_copyme.py:480` runs every `LADDER` pose and a whole game under `REAL_NOISE` |

## Round 2

Scope: the two fix commits, nothing else.

- 1acbe6e touches `arcade/games/freeze.py` and `tests/arcade/test_freeze.py`.
- d81599e touches `arcade/games/flap.py` and `tests/arcade/test_flap.py`.
- HEAD is d81599e.

The round 1 probes were run again on main. The parent, f2d24ba, was extracted with `git archive` into a scratch
directory outside the repository and run with `python -P`, so that the old code, not main's, was imported.

### Verdict: APPROVED

Both blocking findings are fixed. The new tests fail on the old code. No assert was removed or changed. Neither fix
opens anything new.

### 1. Freeze

The fix, at `freeze.py:427-456`:

- `_draw_fall` lifts the rotated points by however far the lowest lit row would pass row 59.
- For a non-steep line, that lowest row is the second row of the 2 px stroke. For the head, it is the nose plus the
  disc's radius.
- The calculation matches `_thick_line` (`STROKE` 2, offsets 0 and +1) and `Canvas._disc` (rows cy - r to cy + r).

Rows 60 to 63 in the game's own frames, on main:

| Run | Ticks lit |
|---|---|
| `canonical`, straight through the game | 0 (round 1: 52) |
| `duo`, straight through the game | 0 (round 1: 52) |
| `canonical`, `idle_body`, `nobody` and `duo` through `run_headless` | 0 each |
| Good bot, 4 seeds | 0 each |
| Lazy bot, 8 seeds | 0 each |

On the lazy bot's 8 seeds, 5 slip, each drawing the topple on 91 ticks, and 3 win with 6, the same 3 of 8 as before.

The topple still shows, and more of it does. These are the pixels the topple adds to the game's own composited frame,
with the word's black box and the scores drawn over it:

| Scenario | Main: mean (min) | Parent: mean (min) | Fall ticks | Ticks with nothing visible |
|---|---|---|---|---|
| `canonical` | 297 (260) | 220 (126) | 60 | 0 |
| `duo` | 204 (136) | 137 (48) | 60 | 0 |

On main, the topple lights rows 0 to 59 only.

### 2. Flap

The fixes:

- The hint is drawn at y = round(64 * 0.7) - `CELL_H` = 37, so it covers rows 37 to 43.
- `READY_TEXT` stays on rows 45 to 51, with row 44 left blank between them.
- The wings-down block is drawn no lower than `FLOOR_Y - 1` = 58.
- The bird's body cannot reach row 60: `MAX_FALL` 30 px/s is 1 px a tick, so `bird_y` stays under 58 at a floor
  crash, and the body's top stays at row 56 or above.
- The removed `GLYPH_H` was not imported anywhere; Dodge, Pong and Copy Me keep their own.

Rows 60 to 63 in the game's own frames, on main:

| Run | Ticks lit |
|---|---|
| `canonical`, `idle_body`, `nobody` and `one_arm` through `run_headless` | 0 each (round 1: 990 on `idle_body`, 180 on `nobody`, 76 on `one_arm`) |
| Good bot, 4 seeds | 0 each |
| Lazy bot, 4 seeds | 0 each |
| Floor crash (one flap at 1.3 s, then both hands down), 6 seeds | 0 each, crash at `bird_y` 57.53 (round 1: 37 ticks) |

The hint against everything else, straight through the game, with i = 2:

| Scenario | Hint ticks, main | Something else lit inside the hint's box, main | The same, parent (rows 55 to 61) |
|---|---|---|---|
| `idle_body` | 1741 | 0 | 1741 (the floor) |
| `nobody` | 841 | 0 | 841 |
| `one_arm` | 76 | 0 | 76 |
| `canonical` | 76 | 0 | 76 |

On main the hint covers rows 37 to 43, in `ready` only. It no longer sits on `READY_TEXT` or anything else.

### 3. The new tests fail on the old code, and no assert is touched

On the parent's code with main's two test files, `-k keeps_rows_60_to_63` gives 6 failed:

| Test | Lit ticks on the parent |
|---|---|
| Freeze `canonical` | 52, from 8.27 s |
| Freeze `duo` | 52, from 8.13 s |
| Flap `idle_body` | 1741 |
| Flap `nobody` | 841 |
| Flap `one_arm` | 76 |
| Flap `floor_crash` | 37, from 4.13 s |

The Freeze test also asserts that a topple happened, so it cannot pass vacuously. The Flap test asserts that the hint
showed, or for the floor crash that the bird reached the floor.

Other test checks:

- `git diff f2d24ba..d81599e -- tests/`: 43 lines added and 0 removed. No assert was removed or changed.
- Collected: 2092 (2086 + the 6 new tests).
- `tests/arcade/test_freeze.py` and `tests/arcade/test_flap.py` on main: 80 passed in 41.00 s.

### 4. Nothing new opened

The flash rule through `run_headless`, seed 5, on main (parent in brackets):

| Run | `flash_area` | Held ticks | `square_flashes` |
|---|---|---|---|
| Freeze `canonical` | 0.0238 (0.0269) | 0 | 5 of 6 (5) |
| Freeze `duo` | 0.0045 (0.0042) | 0 | 2 of 6 (2) |
| Flap `canonical` | 0.0 | 0 | 1 of 6 (1) |
| Flap `idle_body` | 0.0 | 0 | 1 of 6 (1) |
| Flap `one_arm` | 0.0 | 0 | 0 of 6 (0) |

The win rates cannot have moved. Both fixes change only drawing (`_draw_fall`, the hint's y, the wings' y), and no
`debug_state` key, game rule or bot reads any of it. The lazy probe's 3 wins in 8 matches the 0.4 the oracle measured
before the fix. I did not run the oracle or the suite, because the orchestrator was running both.

### Noted, not carried

- On the floor, the wings-down block now sits on rows 58 and 59, inside the bird's own body (rows 56 to 59). The wings
  merge into the body for the crash fade.
