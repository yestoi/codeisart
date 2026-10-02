# it20 code review (24e2aee..56ba6c9)

Reviewer: the it20 code reviewer, fresh context. Judged against the plan
`docs/superpowers/plans/2026-10-02-it20-suite-room-jump-m5.md` and the spec
`docs/superpowers/specs/2026-09-26-wall-arcade-design.md`. Probes are in the session scratchpad,
`/private/tmp/claude-502/-Users-trey-dev-codeisart/3d4c1cbf-546d-4e23-a6ab-f6f8456f0239/scratchpad/it20-code-review/`.
Nothing in the repo was changed except this file.

## Verdict: BLOCKED

Five blocking findings, each shown by a probe. Two are in how Jump behaves: its figure lights the marker rows during
a jump under real noise, and a player who takes over mid-window is measured against the previous player's baseline.
One is in S2: a hostile line raises out of the reader, or gets through and crashes the game. The last two are plan
text the code does not meet: F1's named test does not test its second clause, and Jump drops `fx.flash`'s return.
Each fix is small.

R, the rename, I0, E0 and S1 hold. No assert was removed or weakened beyond the four the plan names. The collected
count rose from 2092 to 2188, and no skip was added.

## Blocking findings

### B1. Jump's figure lights rows 60 to 63 during a jump under real noise

- Where: `arcade/games/jump.py:285` draws the held body (`self._hold.update`, `:169`) in the rect from `_view`
  (`:275-280`, rows 0 to 55). `draw_figure` (`arcade/figure.py:94`) maps every keypoint by the body's current box (`to_wall`, `:30`).
  `KeypointHold` puts a dropped keypoint back where it last saw it, up to `capture_grace(10)` = 0.55 s earlier. In a
  jump the box has risen since then, so a held ankle maps below the rect.
- Input: a standing `Person` that jumps 0.15 in each window, through `degrade(**REAL_NOISE)` (the repo's fit of the
  Pi camera, used by every game's still-body test), driven and drawn as `test_own_drawing_keeps_rows_60_to_63_dark`
  drives it. Body ids 1 to 40 vary which keypoints drop. Probes: `probe_rows.py`, `probe_rows_detail.py`.
- What happens:
  ```
  id 10: lowest lit row 63; hits [(3.2, 'play', 63), (3.23, 'play', 63), (3.27, 'play', 63)]
  ...
  runs with rows 60-63 lit: 22 of 40
  t 3.20 phase play: lit px in rows 60-63 = 8, colours [(255, 120, 0)] (PLAYER_COLOR (255, 120, 0)); box y 0.126..0.718;
  dropped this capture ['l_hip', 'l_ank']; held (keypoint, held y - capture y) [('l_hip', 0.119), ('l_ank', 0.119)]
  ```
  The clean `canonical`, `idle_body` and `nobody` (the test's inputs) light nothing, so the test passes.
- Why it blocks: the plan says "Rows 60 to 63 stay free (the runner's marker)" (Global Constraints) and "Rows 60 to
  63 dark" (G5). The standing rule says the same for every player position the game can meet, and a jump is this
  game's whole input. The real source is worse than the probe. `pose_mediapipe.box_of` (`:73`) boxes only the
  confident keypoints, so a dropped ankle also shrinks the box, and the held ankle maps further down.
- Fix hint (not prescribed): keep Jump's own drawing out of rows 60 to 63 after the figure is drawn (for example a
  black fill of rows 60 to 63 before the striker and the texts), or drop held keypoints that fall outside the current
  box. Add a degraded jumper to the rows test.

### B2. A player who takes over mid-window is measured against the previous player's baseline

- Where: on a new player id, `arcade/games/jump.py:166-168` clears only `ready`'s samples. `_measure` (`:218-219`)
  keeps using `self._base`, which `_sample` set from the previous body (`:213`). Nothing resets or guards it in
  `play`.
- Input: run through the real runner (`tests.arcade.helpers.run`, so the `PlayerLock` is live), seed 12345.
  Person A (the default body, id 1) stands still, and the window opens on A's baseline. A steps out at 2.2 s. B
  (id 2) steps into the same place and stands still: a taller person a step further back (height 0.72, hips 0.08
  higher, feet 0.026 higher in the frame). The lock hands the slot to B at once: B is a new id near the player's
  last place (REACQUIRE). Probe: `probe_swap.py`.
- What happens:
  ```
  swap, clean: heights [37, 0, 0], best_cm 37, rang True, bell_cm 29.46, recorded best 37.0, phase over
  swap, degrade(REAL_NOISE): heights [40, 0, 0], best_cm 40, rang True, bell_cm 29.46, recorded best 40.0, phase over
  B alone, clean: heights [0, 0, 0], best_cm 0, rang False, bell_cm 29.46, recorded best None, phase over
  ```
  B never jumps. B banks 37 cm, rings the bell (flash and "DING!") and records 37 as the night's best.
- Why it blocks: C41 and the plan say "a still body (and Nobody) scores nothing and banks no best". G5 adds that a
  still body "banks nothing and records nothing". This is a correctness bug with an input the wall will meet: people
  swap at the wall. With real proportions (hips at about 0.53 of stature, the nose at about 0.93), a taller successor
  on the same floor raises the hip_mid by about 0.57 of the nose's rise. That passes `HIP_SHARE = 0.5`. So the hip
  check does not catch it.
- Fix hint: on a new player id in `play`, stop measuring for the rest of the window, or take a new baseline. The
  tracker never reuses an id, so a re-detected player also arrives with a new id. Pick the behaviour with that in
  mind.

### B3. S2: a hostile line raises out of the reader, or gets through and crashes the game

- Where: `arcade/sources/scenario.py:44`. `BAD_LINE` has no `RecursionError`, which `json.loads` (`:188`) raises on
  deep nesting. Also `:192-196`: only `t` and `camera_t` are checked finite. `json.loads` accepts the tokens `NaN`
  and `Infinity` (and `1e999` reads as inf), and `_box` (`:116`) passes any float through.
- Input (1): a sensed file holding a good line, then `"[" * 200000 + "]" * 200000`, then two good lines. Probe:
  `probe_scenario.py`.
  ```
  (1) ScenarioReader over: good, a nested line, good, good
    RAISED RecursionError: maximum recursion depth exceeded while decoding a JSON array from a unicode string after records [0.0]; skipped 0
  (1b) the same file through open_replay: ReplayCamera.latest() once a tick, as the runner calls it
    tick 0: latest() gave capture_t 0.0, finished False
    tick 1: latest() RAISED RecursionError: maximum recursion depth exceeded while decoding a JSON array from a un
    tick 2: latest() gave capture_t 0.0, finished True
  ```
  The line is not skipped. The error reaches the runner's camera call (`runner._source` logs it as a camera failure),
  and the generator is dead, so every record after the line is lost.
- Input (2): a line whose body has `"box": [0, 0, Infinity, Infinity]` and a standing body's keypoints. Probes:
  `probe_scenario.py`, `probe_scenario_runner.py` (3 s of such lines, then good ones, through the runner with
  `strict=False`).
  ```
  read: 1 record(s), skipped 0; body box (0.0, 0.0, inf, inf), in_zone True, zone_x 0.500
  draw_figure RAISED ValueError: cannot convert float NaN to integer
  read 360 lines, skipped 0; runner: crashes {'jump': 1}, hidden [], game now lobby
  ```
  The line is accepted. The body is in the zone and becomes the player, and Jump's draw raises inside the runner's
  tick. The crash guard ends the game, and three such crashes hide it until dusk.
- Why it blocks: the plan's S2 says "a bad line is skipped with one warning, never raised". The core plan's Review
  Focus 4 says "Replay skips the line with a warning and never raises into the runner". The standing rule covers
  corrupt, cut-off and hostile lines.
- Fix hint: catch `RecursionError` per line (or every `Exception` from `_parse`). Reject non-finite numbers in
  every float field: the box, `vx`, `vy`, `scale`, `seen_ago`, `torso_per_width`, a blob's size and velocity, the
  audio. Covering the box alone is not enough.

### B4. F1's colour test does not test the plan's second clause

- Where: `tests/arcade/test_copyme.py:633-643`. The second half asserts that both colours appear somewhere in a
  `duo` frame of `play` (`:642`) and that the two constants differ (`:643`).
- Input: a mutant of `copyme.draw_view` that draws seat b's outline in seat b's own colour (the C55 fault itself),
  then the test function run against it. Probe: `probe_outline_mutant.py`.
  ```
  mutant, the first duo frame of play: 43 outline strokes drawn in seat b's colour (0, 160, 255)
  test_the_outline_differs_from_every_figure_colour: PASSES on the mutant
  ```
- Why it blocks: the plan's F1 acceptance names this test with the clause "in a `duo` frame of `play` no outline
  pixel is drawn in seat b's colour". The test passes while outline pixels are drawn in seat b's colour, so the clause
  is not tested. The production code does meet the clause. In `probe_outline.py`, over 270 `duo` frames of `play`,
  0 of 57,775 outline pixels show seat b's colour:
  ```
  duo play frames 270; outline pixels drawn in total 57775; worst frame: outline pixels shown in seat b's colour = 0 ...
  ```
  So the fix is in the test only. For example: mask the pixels the outline strokes draw, and assert none of them is
  seat b's colour in the drawn frame.

### B5. Jump drops `fx.flash`'s return

- Where: `arcade/games/jump.py:227`, `self.fx.flash(FLASH, 0.15)` as a bare statement.
- Probe: `probe_flash_return.py`, an AST scan of every game's `fx.flash` call:
  ```
  copyme.py:415 self.fx.flash(FLASH_COLOR, FLASH_SECONDS): return used
  jump.py:227 self.fx.flash(FLASH, 0.15): return DROPPED
  quickdraw.py:268 self.fx.flash(DRAW_COLOR, 0.15): return used
  swat.py:233 self.fx.flash((255, 255, 255), 0.15): return used
  ```
- Why it blocks: the plan says it twice. The Global Constraints: "Every `fx.flash` return is checked." G5: "a bell:
  `fx.flash((255, 255, 255), 0.15)` (checked)". It19's review read the same rule as the game using the return (Copy
  Me's refused flash becomes a burst). Today it changes nothing you can see. The bell is Jump's only flash, it rings
  at most once per 9 s attempt, and each launch gets a fresh `Juice`, so a refusal cannot happen inside Jump. That is
  why this is the smallest finding: the fix is one line, Copy Me's pattern of a burst at the bell when the flash is
  refused.

## The integrator's three flags

1. `jump.py:227`, the dropped `fx.flash` return: a plan requirement not met. Blocking, as B5.
2. `Blob.vy`'s unit: neither. `arcade/sensed.py:281` comments `vx` only ("frame widths per second"), and that is
   right for `vx`. `vy` (`:282`) has no comment. `arcade/sources/blobs.py:170` computes `vy` in frame heights per
   second and says so (`:141-142`), the same as `Body.vy` (`arcade/sources/camera.py:274`) and `Blob.y`. So `y + vy * dt` predicts
   correctly. The plan reads both ways: E0 says "fw/s", while S1 says "the matched step over dt", and the step's y
   is in frame heights. Nothing reads `Blob.vy` yet (grep of `arcade/`), so no wrong result can be shown. Noted below.
3. `test_the_outline_differs_from_every_figure_colour`: its second half does not test what the plan asks. Blocking,
   as B4.

## The standing rules for a game, and for S2 and R

- Rows 60 to 63 dark: fails under real noise in a jump (B1). The striker (rows 6 to 57), the bell, the texts
  (rows 20 to 47) and the score (rows 0 to 15) stay above row 60.
- Every body value is guarded:
  - `measure_rise` (`:101`), `_torso` (`:112`) and `_sample` (`:200`) guard a nose, hip or shoulder under
    `MIN_CONF` or absent, and a torso of 1e-3 or less.
  - `Body` cleans every keypoint to finite (`sensed._clean`).
  - A player lost mid-window holds the bar for the grace, then reads 0, and the window still banks its peak.
  - With two players, Jump reads `sensed.player` only.
  - The gap is a different player mid-window (B2).
- The score is drawn last: `jump.py:299-302` come after the figure, the striker and the phase texts. The runner's
  effects render after the game's `draw`, which is the runner's job.
- S2, corrupt, cut-off and hostile lines: a cut-off gzip ends with one warning (`:349-351`, as tested), and a
  malformed JSON object or a wrong type is skipped. A deeply nested line raises, and a non-finite box gets through to
  the game (B3).
- R, fallback and no orphan worker:
  - A share that cannot start, exits non-zero, runs past `WORKER_TIMEOUT_S` or returns a short or foreign file gives
    one `RuntimeWarning` and stores nothing (`pooled.py:157-168`).
  - The memo (`test_oracle.py:42-57`) then makes those plays in process, so every report keeps its full 20 seeds.
    `test_the_pool_made_every_missing_play` fails loudly in that case; nothing is silent.
  - `join` and `stop` kill and reap in `finally` (`:173-177`, `:131-135`), and `start` stops a pool whose launch
    raises (`:217-219`).
  - `pytest_sessionfinish` stops a pool that was never joined (`-x`, Ctrl-C, an error).
  - The join runs `tryfirst` in `pytest_runtest_setup`, before the fixtures of the first item that is not beside the
    pool, so every perf test and `test_headless.py` run after it.
  - `--collect-only` starts no pool and prints no `pooled:` line (checked below).
  - No finding.

## Removed or changed asserts (`git diff 24e2aee..56ba6c9 -- tests/`)

| File:line (new) | Before -> after | Judgement |
| --- | --- | --- |
| `tests/arcade/test_copyme.py:178` | `(OUTLINE_COLOR, MATCH_COLOR) == ((0, 200, 255), (0, 200, 0))` -> `((255, 0, 255), (0, 200, 0))` | Named by the plan (F1, Q117). The pinned value changes, `MATCH_COLOR` is kept, and the assert is no weaker |
| `tests/arcade/test_game.py:171` | `MENU_ORDER` tuple: `"strongman"` -> `"jump"` | Named (the rename, Q99). The name only |
| `tests/arcade/test_game.py:236` | the `skipped` list: `"strongman"` -> `"jump"`, re-sorted | Named (Q121). The name only |
| `tests/arcade/test_game.py:239` | the traceback list: `"strongman"` -> `"jump"`, re-sorted | Named (Q121). The name only |

`test_game.py:226`, the fake's dict key, also changes from `"strongman"` to `"jump"`. It is not an assert, and the
plan names it. Every other removed line under `tests/` is code or a docstring: `pooled.py`'s `fill` body split into
`start`/`Pool.join`, the `pooled_plays` docstring, `test_bots.py`'s import line and `test_copyme.py`'s module
docstring. No other assert is removed, changed or weakened.

## Collect and skip counts

- Base 24e2aee: `2092 tests collected`. I measured this on a `git archive` of 24e2aee in the scratchpad, run with
  the repo's venv.
- Head 56ba6c9: `2188 tests collected in 0.67s` (`pytest --collect-only -q | tail -1`). No `pooled:` line was
  printed.
- +96 = R 4, I0 2, E0 3, G5 50, F1 5, S1 16, S2 16. No drop.
- Skipped: 3 in the final run (`final-durations.txt`: `2185 passed, 3 skipped`), the base's 3. No `skip`, `xfail` or
  `importorskip` was added in the diff. I did not rerun the full suite (the rules).
- Run here, as a check: `tests/arcade/test_jump.py tests/arcade/test_scenario.py
  tests/arcade/test_copyme.py::test_the_outline_differs_from_every_figure_colour` gave `56 passed in 16.16s`. The
  tests pass, and the faults above are outside what they check.

## Notes (not carried)

- Jump's idle hint shows at 0.0 s into windows 2 and 3, and 0.5 s into window 1, for a still body (`probe_hint.py`:
  `{1: 0.5, 2: 0.0, 3: 0.0}`). `_idle` keeps counting through `result` and `ready` (`jump.py:264`). The plan's "after
  `HINT_IDLE_SECONDS` not active in play" can be read either way, and spec 11's "hint within three seconds of a still
  body" is met. G5's report ("idle 2 s" in play) is accurate for window 1 only.
- `Blob.vy` is in frame heights per second (flag 2). A comment on `sensed.py:282` would settle it when E0's file is
  next touched (S1's Q3 default).
- Jump measures the held body (`jump.py:181`). In the B1 probe, a hip held from before the jump read 0.119 lower than
  the capture, which halves that capture's hip rise. Held values are real past positions, so this can only
  under-count a capture. No changed result was shown.
- B1's cause is in shared code: `draw_figure` maps keypoints by the current box, and `KeypointHold` re-adds old ones.
  Copy Me (`FIGURE_H = 60`) has less margin than Jump. Its exposure is mostly in the real source, where `box_of`
  drops the low-confidence keypoints from the box. That is outside this range's rule for Jump. Worth a look in it21.
- A deeply nested header line makes `ScenarioReader()` raise `RecursionError` at open, not the documented
  `ValueError`. That happens at open, not in the runner.
- The G5 owner questions (a hint in `ready`; `player_xy` under the striker or a text) are design questions, not
  findings.
- Implementers' claims I checked and found true:
  - F1's 282, 301 and 413 are magenta's distances.
  - The rename's line numbers are right.
  - `HIP_Y - 0.0` leaves every existing bot play unchanged (`test_move_without_lift_is_todays_body`).
  - S1's non-finite centroids are dropped before matching.
  - S2's D1 stamping matches its test.
