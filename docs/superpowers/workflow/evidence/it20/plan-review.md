# it20 plan review, round 1
Plan: `docs/superpowers/plans/2026-10-02-it20-suite-room-jump-m5.md` (272 lines) at b685e63. Fresh context, checked
against the code; probes under the session scratchpad's `it20-review/` (P1 to P3).

## Verdict: BLOCKED
Four findings, all in G5 and F1. Each one has a one-line fix to the plan's text. R, the rename, I0, E0, S1 and S2
hold as written, apart from the notes.

## Blocking findings

### B1. F1 changes an assert that the Global Constraints say must not change
- Plan: lines 18-20 say "The only changed asserts are the rename's three in `tests/arcade/test_game.py`... An assert
  this plan does not name that would have to change: stop and report." Line 203 sets `copyme.OUTLINE_COLOR` to
  `(255, 0, 255)`.
- Code: `tests/arcade/test_copyme.py:178` (in `test_registered_and_declared`) reads
  `assert (OUTLINE_COLOR, MATCH_COLOR) == ((0, 200, 255), (0, 200, 0))`.
- What happens: F1 cannot pass without editing that assert, and the Global rule then tells the implementer to stop
  and report. The task stalls, or the implementer breaks a rule the plan states twice.
- Fix (lines 19-20): "The only changed asserts are the rename's three in `tests/arcade/test_game.py` (lines 171,
  236, 239; Q99, the name only) and F1's colour value in `tests/arcade/test_copyme.py:178` (`(0, 200, 255)` becomes
  `(255, 0, 255)`, `MATCH_COLOR` unchanged)." Add the same sentence to F1's acceptance (line 206).

### B2. Jump has no `score` key, so `score_visible` and `score_legible` are None and fail
- Plan: the debug_state list at lines 179-180 has no `score` key. Line 173 draws the number "from `result` on".
  Line 36 (Global) says scores are drawn "from the game's first tick (`score_visible` >= 0.8)".
- Code: `arcade/feel.py:228-244`. `_score` counts only ticks whose `debug_state()["score"]` is an int. When no tick
  counts, both metrics are None. `feel_budgets.toml` `[score.score_visible]` min 0.8 and `[score.score_legible]`
  min 0.9 then fail with "None misses". Every other score game has the key: dodge.py:280, copyme.py:528,
  freeze.py:483, flap.py:383.
- What happens: `test_feel_meets_its_budgets[jump]` fails on two budgets. If the implementer adds `score` but follows
  line 173, the number appears only at the first `result`. The canonical spends its measured 20 s (`FEEL_SECONDS`,
  feel.py:40) on 2 s empty, the walk-up, the raise and the sweep (line 39-40: "then play that gets past the first
  attempt"). Its first result can therefore land after the window, and no tick counts again. Lines 36 and 173
  contradict each other, so the implementer has to guess.
- Fix:
  - Line 179: add "`score` (the number drawn: `best_cm`, an int, 0 before a counted attempt)".
  - Line 173: replace "from `result` on (the bar first, the number second)" with "from the game's first tick
    (`best_cm`, 0 before an attempt counts; drawn after the bar)".
  - C41 still holds, because showing 0 banks nothing.

### B3. The good bot's round is about 14 to 17 s, under the 20 s minimum
- Plan: lines 153-154 say "`play` ... for at most `JUMP_WINDOW`". Line 160 says "banks on landing ... or at the
  window's end". Lines 163-164 set ATTEMPTS 3, SETTLE 1.5, JUMP_WINDOW 5.0, RESULT 2.5 and OVER 3.0. Line 189 lists
  `ATTEMPTS` as a lever. Line 196 is `test_three_attempts_then_over_and_done_after_the_hold`, and line 150 says
  "Three attempts".
- Code: `feel_budgets.toml` `[score.round_seconds]` is min 20, max 120. `arcade/feel.py:375-380` takes the median of
  the good plays that ended done. The template's `test_good_round_length_in_band` (`test_flap.py:510-514`) asserts
  `20 <= median <= 120`.
- What happens: "at most" reads as "play ends on landing". The good bot's arc is 0.6 s plus 4 reaction ticks, so play
  lasts about 0.75 s.
  - With one `ready`: 1.5 + 3 × (0.75 + 2.5) + 3.0 = 14.3 s.
  - With a `ready` before each attempt (the plan does not say which applies): 3 × (1.5 + 0.75 + 2.5) + 3.0 = 17.3 s.

  Both fail the feel budget and the template test. The only lever that reaches 20 s is ATTEMPTS: 6 or more with
  one ready, 5 or more with three. That contradicts "Three attempts" and the test's name. For comparison, Copy Me
  measured 24.0 s, exactly its phase sum.
- Fix:
  - Line 154: replace "`play` "JUMP!" at 2x for at most `JUMP_WINDOW`" with "`play` "JUMP!" at 2x for the whole
    `JUMP_WINDOW` (the peak banks on landing and its line holds to the window's end)".
  - Say whether `ready` (and its baseline) comes back before each attempt. That gives about 27 s with one ready and
    about 30 s with three.
  - Drop `ATTEMPTS` from the levers on line 189.

### B4. The canonical sweep gives range 0.598, under 0.6, and "at the right" contradicts the full-width rect
- Plan: line 181 has the canonical walking "0.2 to 0.8 to 0.5". Line 171 places "the player's figure at the right"
  and line 172 uses `figure_rect(held, (w, FIGURE_H))` with the column backlash.
- Code: `arcade/figure.py`. `figure_rect` centres the figure on column `round(zone_x × (w - 1))` across the full
  width. `feel_budgets.toml` `[score.range]` min 0.6 is (max - min of `player_xy` x) / (w - 1). Copy Me's sweep is in
  zone units (`copyme.py:539-540`, `SWEEP = (0.15, 0.85)` walked through `cam_x`, `WALK_SPEED = 0.1` zone/s).
- What happens:
  - P3: zone x 0.2 to 0.8 at 0.1 zone/s, with backlash 1, puts the head at columns 25 to 101. 76/127 = 0.598
    fails `test_feel_meets_its_budgets[jump]`. The sweep is not a named lever.
  - If "at the right" is honoured, the figure is confined to a right-hand strip and range falls further.
  - Read as camera x, 0.2 to 0.8 is the zone's own edges (zone_x 0 to 1). The anchor would then sit on the edge of
    the zone, and the walk is 15 s at 0.1 zone/s.
  - So the plan's three readings either fail or contradict each other.
- Fix:
  - Line 181: "a walk across the mat in zone x, 0.15 to 0.85 then back to 0.5 (Copy Me's `SWEEP`), at most 0.1 zone
    a second (Copy Me's `WALK_SPEED`: the flash rule's area), the far end inside the measured 20 s". P3 gives
    0.693 for this.
  - Line 171: replace "at the right" with "on its own column across the wall (it may pass in front of the striker;
    the bar and the number are drawn over it)".

## Notes
- N1, S2 (line 252):
  - `ReplayAudio.latest() -> Audio` contradicts the runner, which takes `(capture_t, Audio)` (`arcade/runner.py:236`),
    and the amendment's "Replay returns the new `latest()` shapes" (core plan about line 592). Suggested wording:
    "`ReplayAudio.latest() -> tuple[float, Audio] | None`, stamped with the clock as `ScriptedCamera` does."
  - The draft tests' 3-tuple `cam.latest()`, bare `Audio()` and `decode(...).motion is None` asserts must be adapted
    to `CameraResult` (4-tuple, `camera.py:23`) and the empty grid. Say so.
  - `decode`'s "recording's calibration" has no header field. Say whether it is `decode(..., calibration)` from the
    caller or a header key.
- N2, the zone top caps a jump:
  - A lifted body's anchor (shoulder_mid) leaves the zone top (y 0.2), and the runner drops the player
    (`runner.py:111`, in-zone only).
  - P1, with Person h 0.6: shoulders 0.37 still, so a rise of about 0.94 torsos (47 cm) can be measured. The good bot's
    0.16 lift stays in the zone by 0.01.
  - At h 0.7 the cap is about 33 cm, and at h 0.8 about 23 cm (under `BELL_CM[0]` 28). A near or tall player can then
    never ring the bell.
  - Put this in the docstring and an I2 wall check, and keep the good bot at h 0.6 (`near` None).
- N3, `active` and "still" under noise (lines 153, 177):
  - "`rise` changed by 0.1 within 1 s" is under real noise's peak-to-peak (jitter ±0.01 per axis, about ±0.056
    torsos on the nose). A still body under `degrade` then reads `active` forever, and the hint and the inactivity
    prompt never come.
  - "still" in `ready` is undefined; if it means "not active", `ready` may never end under noise.
  - Suggest 0.25 torsos, and "still: nose and hip_mid each within 0.1 torso of their medians over `SETTLE_SECONDS`".
- N4, `test_rise_ignores_size_and_place` (line 192): make it call `measure_rise` directly.
  - Through the runner, h 0.4 is never in the zone (height 0.408 < `min_height` 0.45, P1).
  - h 0.8 raised half a torso leaves the zone (N2).
- N5, `test_join_twice_waits_once` (line 114): with `Popen` raising and workers=2, `fill` warns once per failed
  worker, which gives two warnings. Suggested wording: "the first join's warnings, none from the second" (or a
  one-worker pool).
- N6, `test_stop_kills_a_running_pool_and_leaves_no_child` (line 112): patch `Popen` in `pooled.start` only.
  `children_of_this_process` uses `subprocess.run`, which must stay real.
- N7, R's acceptance (lines 116-119):
  - `test_the_rows_follow_the_selected_tests` names Jump, but R runs before G5 and `REPORT_PLAYS` (test_oracle.py:25)
    has no Jump row then. Use any non-Pong game (Flap).
  - "`pgrep -P` of the pytest process" cannot be read after `--collect-only` exits. Suggested check: no `pooled:`
    summary line, or `pooled.RUNNING is None` in a `pytester` run.
- N8, the deadline margin (line 91):
  - After Jump the pool is 540 plays beside the soaks, about 140 s against 180 s, a margin of about 1.3x. it21's Paint
    and Tug will exceed it.
  - A failed share is replayed in process. A whole worker share (about 135 plays) costs about 100 s, not 70 s.
  - Have the gate and I1 record the pool's elapsed and flag it over 150 s.
- N9, rule 6 (lines 13-16): the subset after each merge departs from config.md rule 6 (the full suite after each
  merge). Record it under "Decisions taken" with its reason (time, the shared Mac), so the departure is deliberate.
- N10, I0 (line 137): `Sensed` is `eq=False`, so "equal records" never holds by `==`. Suggested wording: "equal
  `bodies` (every keypoint, `in_zone`, `zone_x`, `zone_y`) and the same rng draws".
- N11, S1 (line 226): say whether the motion grid is mirrored, as the keypoints are, before the zone crop. The zone
  is in mirrored camera space, so an unmirrored crop takes the wrong side.
- N12, small items:
  - Jump's bell flash, bar, line and number all change in one second. Copy Me's report already reads 4 of the 6
    `square_flashes`, so keep the bell to one flash per attempt (as written).
  - `fx.pop("DING!")` needs `x, y, color` (`juice.py`).
  - The striker frame's colour is not given.
  - "Review Focus 4 (line 772)" is line 773.

## What I checked and probed
- R:
  - Read: `pooled.py`, `test_oracle.py`, `helpers.py`, both conftests, `test_all_games.py`, and pytest 9.1.1's hook
    order (collection_finish after `-k`/`--lf`; runtest_setup before fixtures; sessionfinish on `-x`/Ctrl-C).
  - The join comes before every item that is not a soak, in default order, under `-k` and with a single file. No
    worker runs beside `test_headless.py`'s timing asserts, `test_show_shot.py`'s strobe test or `test_show_soak.py`'s
    child count.
  - `helpers.played` keys match the pool's (`play_key`, layout "128x64"). The existing pool tests hold unchanged. The
    410 s estimate is plausible.
- The rename: the asserts at `test_game.py:171`, :226, :236 and :239 are as stated. `all_games()` skips the missing
  module. `test_scores.py:158` is free text.
- I0: `Move` has no field pins in `test_bots.py`. A lift of 0.0 is exact, so plays stay bit-identical.
- E0: `KW_ONLY` on `Blob` (frozen, no slots, Python 3.12.13). Every `Blob(` caller passes 4 or 5 positional fields;
  no `astuple` or `fields(Blob)`. `asdict` in `tools/arcade_evidence.py:135` is harmless.
- G5 and F1:
  - Read `feel.py`'s `_score`, `_bot_plays` and range, `feel_budgets.toml` `[score.*]`, `figure.py`,
    `copyme.py:68,279-280,539-600`, `test_copyme.py:178,281`, `juice.py`, `runner.py:111,236,498`, `bots.py`, and
    `actors.py` (`Person`, `degrade`, `REAL_NOISE`).
  - Magenta's distances (282, 301, 412) and red share 0.5, and BAR's red share of 0.614, are correct.
- Probes:
  - P1 (`p1_body.py`), Person geometry and the zone: h 0.6 has torso 0.18 and shoulders 0.37; h 0.4 is out of the
    zone; at h 0.6, lifts up to 0.16 stay in the zone and 0.20 leaves it.
  - P2 (`p2_rows.py`): Copy Me's and Swat's canonical and duo drawings never light rows 60 to 63 today.
  - P3 (`p3_range.py`): the figure's head column for zone x 0.2 to 0.8 to 0.5 at 0.1 zone/s with backlash 1 spans
    25 to 101, range 0.598. Copy Me's 0.15 to 0.85 gives 0.693.
- S1 and S2: the new file names do not collide with existing files. No privacy test or module scan exists, and cv2
  is 5.0.0. Checked the core plan's Task 12 (3524-3776, amendment 588) and Task 15 (4252-4396, amendment 620-630)
  against `camera.py:23` and `runner.py:236`.
- Not run: the full suite (by the brief).
