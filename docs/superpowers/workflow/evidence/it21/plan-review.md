# Iteration 21: plan review

Plan: `docs/superpowers/plans/2026-10-02-it21-m5-wiring-record-calibrate.md` (299 lines, none over 118 characters),
against HEAD d166402. Reviewer: the adversarial plan reviewer. I changed no file but this one, ran no full suite, and
ran probes only from the scratchpad (`.../scratchpad/it21-plan-review/`: `shrink_probe.py`, `zone_probe.py`,
`tick_cost.py`, `feat_cost.py`, `ast_probe.py`).

## Verdict: BLOCKED

Seven blockers. Three of them make a built feature fail for the owner while every planned test passes (B2, B3, B5).
One breaks an assert that the plan does not name (B1). The fixes are mostly a phrase each. The plan stays under 300
lines if "Decisions taken" drops the three bullets that repeat its own sections (see Line budget).

## Blockers

### B1. W's shrink breaks an assert the plan does not name (`tests/arcade/test_blobs.py:99-100`)
- Where: plan lines 116-118 ("`update` first shrinks a frame wider than `work[0]` to `work`") and lines 19-21 ("The
  only changed asserts are the three named below ... An assert this plan does not name that would have to change:
  stop and report").
- What is wrong: `test_blob_ids_persist_and_velocities_follow` (`test_blobs.py:87-100`) builds `FrameFeatures()` and
  feeds it `dark_frame(200, 150)`, a frame wider than 160. W shrinks that frame to 160x120 first. A 4 px step at 200
  px becomes 3.2 px at 160, and INTER_AREA rounds the centroid unevenly. `:99`
  `b.x - prev.x == pytest.approx(0.02, abs=1e-9)` and `:100` `b.vx == pytest.approx(0.02 / dt, rel=1e-6)` fail.
- Evidence (`shrink_probe.py`: the test's frames through `cv2.resize(..., (160, 120), INTER_AREA)` and today's
  `FrameFeatures`): dx = 0.020391, 0.019097, 0.019097, 0.020391; vx = 0.2039, 0.1910, 0.1910, 0.2039. None is within
  1e-9 of 0.02 or within 1e-6 relative of 0.2. No other `FrameFeatures` test uses a frame wider than 160 (`:81`,
  `:119`, `:136`, `:153`, `:174`, `:198`, `:224` use 160x120 or the small grids).
- Smallest fix (W, after line 131, +1 line): "Changed setup (named, no assert changes): `test_blobs.py:89`
  `FrameFeatures()` becomes `FrameFeatures(work=(200, 150))`, so its 200 px frame is not shrunk and :99-100 hold."

### B2. Calibrate's zone (Q144) is too thin in y: after a calibrate, Jump's bell almost never rings
- Where: plan lines 204-206 ("Zone: the stands' anchors, min to max, widened by `MARGIN`") and the acceptance at
  lines 214-215 ("the file's zone holds the three anchors within `MARGIN`").
- What is wrong: the anchor is the shoulders (`sensed.py:311-321`), and all three stands are taken standing, so the
  anchors' y spread is small. A jump lifts the anchor above the zone's top. The runner then drops the body: it keeps
  only `in_zone` bodies (`runner.py:111`, `:474`), and `jump.py:15-16` and `:100` say so ("the zone caps the rise").
  The default zone (y 0.2 to 0.8) caps the rise at about 47 cm for a body 0.6 of the frame tall. The calibrated zone
  caps it far lower.
- Evidence (`zone_probe.py`, actors with hips at 0.55, far stands at x 0.3 and 0.7 with height 0.5, near stand at x
  0.5 with height 0.7): zone = (0.25, 0.29, 0.75, 0.45). A standing anchor's y is 0.400 at height 0.5, 0.370 at 0.6
  and 0.340 at 0.7. Jump's canonical 0.15 jump takes the body out of this zone for 9, 13 and 15 ticks (heights 0.5,
  0.6, 0.7). The rise that still counts, (anchor y - 0.29) / torso x `TORSO_CM` 50, is 37 cm at height 0.5, 22 cm at
  0.6 and 12 cm at 0.7. The bell is drawn from 28 to 40 cm (`BELL_CM`, `jump.py:51`). From height 0.6 up, the bell
  can never ring, and at 0.5 the top of its range is out of reach. The squat side is thin too: y1 0.45 leaves a
  0.08 frame dip at height 0.6. The planned test pins exactly this zone, so it passes.
- Smallest fix (C, lines 204-206 and 214-215, line-neutral): "Zone: x from the stands' anchors, min to max, widened
  by `MARGIN`; y from `min(0.2, top - MARGIN)` to `max(0.8, bottom + MARGIN)`, never thinner than the default's (a
  jump lifts the anchor: `jump.py:15`)". In the acceptance: "the zone's x holds the three anchors within `MARGIN`, its
  y spans at least 0.2 to 0.8; a 0.15 jump at each stand's height stays in the zone". Q144's text changes to match,
  so the owner sees it.

### B3. The static-light mask can never be captured from a real camera: `StaticMask` hides the lamp first
- Where: plan lines 201-202 (`clear`: "`static_mask` = the blobs seen in at least `STATIC_SHARE` of the captures")
  with W's lines 116-124 (the camera's blobs come from `FrameFeatures`), and the acceptance at lines 213-216.
- What is wrong: `FrameFeatures.update` passes every blob through `StaticMask` (`blobs.py:233`), and `StaticMask`
  hides any tracked blob that has stayed still for `STATIC_SECONDS = 5.0` (`blobs.py:24`, `:177-199`). Calibrate's
  `clear` step starts at least 11 s into the run (aim 2 s, three stands of at least 2 s, baseline 3 s), and in
  practice much later. A lamp lit since the start has been hidden for at least 6 s when `clear` begins, so it is seen
  in 0 percent of the clear's captures. A lamp switched on at the start of `clear` is seen for 5 of its 10 s, which
  is 50 percent, under `STATIC_SHARE` 0.8. So `static_mask` is always empty on the real camera, and W's drop (line
  120-121) never acts. The actors test (line 215, "a still lamp blob") feeds blobs straight into Sensed and never
  passes `FrameFeatures`, so it passes.
- Smallest fix (W line 116 and C line 210, about +1 line): W: "`FrameFeatures(..., hide_still: bool = True)`, an
  attribute: False skips `StaticMask` (for calibrate)"; W's acceptance adds `test_hide_still_off_keeps_a_still_lamp`
  (a lamp still for 12 s is shown on every frame). C: "`main` sets `camera.features.hide_still = False` when the
  camera has `features` (`getattr`, no import of W)". W merges before C, so the subset after C runs both.

### B4. A scene that raises hangs `record` and `calibrate` forever
- Where: plan line 168 (`runner.loop(camera, audio, until=scene.done)`) and lines 211-212 (`loop(..., until=
  cal.done)`; "0 when saved, 1 when failed; sources and display closed on every path").
- What is wrong: `Runner` defaults to `strict=False` (`runner.py:285`). Every lobby call goes through `_lobby_call`
  (`runner.py:404-416`). On a raise it logs, then replaces the lobby with `_TitleCard`, whose `done()` is always
  False. So `scene.done` never turns True again, `loop` has no `max_ticks` in `record`'s or calibrate's `main`, and
  the command runs forever on a title card. The writer is never closed (a truncated `.gz`), no exit code comes back,
  and "closed on every path" does not hold. A test that drives `record()` or `main` to a raising scene with a
  `FakeClock` hangs the suite, not just that test.
- Smallest fix (R line 168 and C line 211, line-neutral): both build their `Runner(..., strict=True)`, so a raising
  scene ends the loop with the exception. "R's `main`, like C's, closes the writer, sources and display in a
  `finally`."

### B5. Raw files hold the 3 s countdown and the frames after the end: the cues are off by `COUNTDOWN`
- Where: plan lines 167-168 ("Raw: `camera.tap = writer.write` and the scene writes nothing; the runner's loop
  ends, then `camera.close()`") against lines 161-162 (a sensed file starts at "rec", "the cue times' base").
- What is wrong: the tap is set before the loop, so the camera thread writes from the first capture. The raw file
  starts 3 s before "rec", the countdown, and it keeps capturing after `done()` until `close()` joins the thread
  (`ThreadedCamera.close` waits up to 2 s). RP's raw replay rebases on the first record (plan line 234: `t - t0`).
  So every cue in a raw file is about 3 s early against its frames, and spec 9.5's cue assertions on raw fixtures
  ("three selections in `door-point`, none in its sweep") read the wrong windows. The owner records these once, at
  the camera. Also, if `close()` times out, a tap after `writer.close()` writes into a closed file.
- Smallest fix (R lines 158 and 167, +1 line): `RecordScene(..., camera=None)`; "Raw: the scene sets `camera.tap =
  writer.write` when "rec" starts and `None` at `done()`, so the file holds rec's captures only". The test at lines
  180-181 adds "none from the countdown or after `done()`".

### B6. REC's figures light rows 60 to 63, and nothing in R's acceptance checks the rows
- Where: plan lines 149-150 ("the bodies seen as figures (`figure_rect`, `draw_figure`, ...) under the text. Rows 60
  to 63 dark.") and R's acceptance (lines 173-183), which has no rows-60-to-63 test. C has one (line 219), and so
  does Jump (`test_jump.py:461`, `:475`).
- What is wrong: `figure_rect(body, (w, h))` is an h-by-h square from row 0 (`figure.py`), and `to_wall` scales the
  box to fill rows 0 to h - 1. With the wall's (128, 64), a standing body's feet are drawn on rows 60 to 63. Jump
  avoids this only by blacking those rows after the figure (plan line 101). it20's B1 was exactly this: a figure
  lighting rows 60 to 63 (`test_jump.py:476-477`). The figures can also touch "REC" at (1, 1) and the cue at rows 28
  to 35. `feel.find_text` needs a 1 px dark gutter, so `test_rec_glyph_on_every_recorded_tick` would fail or pass
  depending on where the actor stands.
- Smallest fix (R lines 149-150 and 182, line-neutral): "the bodies as figures (...), then rows 60 to 63 black, then
  each text over a black box"; rename `test_rec_frames_keep_the_flash_rule` to `test_rec_frames_keep_the_flash_
  rule_and_rows_60_to_63_dark` (a body in view on every tick: `raw_frames[:, 60:]` all 0).

### B7. The raw refusal contradicts "refuse before any source opens"
- Where: plan lines 156-157 (`refusal(cfg, *, consent, raw, camera=None)`: "`raw` with a camera that has no `tap`")
  against line 171 ("a refusal prints the reason and returns 2 before any source or display opens").
- What is wrong: before the sources open there is no camera, so `main` calls `refusal(..., camera=None)`. One
  reading ("None has no `tap`") refuses every `--raw`, so the owner can never record raw. The other skips the check,
  and a scripted or none camera gets through with no tap, writing an empty raw file. The plan does not say which.
- Smallest fix (line 157, shorter): "`raw` unless `cfg.camera == "mediapipe"`", with `camera=None` dropped from the
  signature.

### Line budget
B1, B3 and B5 add about 3 lines. Pay for them by deleting the first three bullets of "Decisions taken" (lines
282-286, 5 lines). They repeat lines 74-79 and 143-145 (lobby scenes, `provides`), lines 90-98 (G6's band, Q136,
Q137) and lines 184-186 (`test_privacy.py`, `wave`), and the writer's report keeps the reasons. W's lines 132-133 can
go too (2 lines): they repeat I2's owner line (298-299).

## Notes (not blocking)
1. S, line 256: the reason "leave" is not a session reason. `scores.REASONS` is ("done", "left", "inactive",
   "capped", "exit", "crash") (`scores.py:18`), and `SessionLog.append` raises on any other (`:193-194`). Write
   "left" in the test and its expected dict, or the fixture holds a line the runner never writes.
2. `test_privacy.py` (lines 184-186) bans the spec's list. It does not catch `ndarray.tofile`, `pickle.dump` or
   `open(..., "wb")` of a frame. The spec does not ask for them; adding `tofile` costs nothing. `ast_probe.py`: the
   planned rule passes on today's `arcade/` (no hit; `freeze.py:504`'s `wave` is a function name, not an import).
3. The raw header has no `mirror`. W's tap stores the unflipped frame, and RP's `RawReplayCamera` builds
   `FrameFeatures(MOTION_GRID, calibration)` with today's default `mirror=True`. A raw file recorded with `cfg.mirror
   = false` would replay its motion mirrored against its detections. A header key `mirror`, read by RP, closes it.
4. Raw replay pacing (line 234: `t - t0` at most `clock() - opened`): at exactly +0.1 s the float difference can be
   0.09999999999999998, so `test_raw_replay_paces_by_capture_time`'s "at +0.1 s the second" can miss by one ulp. Use
   the runner's `EPSILON` in the comparison.
5. Replaying a sensed file that holds audio makes `ReplayAudio` available, so the status inputs include the audio
   inputs while no audio source exists (Q99). No game needs audio, so nothing breaks; it is a status-line oddity.
6. Suite share: C's actors test runs about 60 s of scene ticks through `run_headless`. `tick_cost.py` puts a lobby
   tick at about 1 ms headless, plus the actors, so about 5 to 6 s, against the planned +3 s. The total stays near
   475 s, well under 540.
7. `motion_grid` crops to `calibration.zone` (`blobs.py:102`). With B2's fix the calibrated grid keeps at least the
   default's height; with the plan's zone it would be a strip about 0.25 of the frame tall.
8. With B4's `strict=True`, a game raise would also propagate, but `record` and `calibrate` run no games, so nothing
   else changes.

## What I checked and found right
- Form: 299 lines, none over 118 characters; test-first acceptance in every task; each task's files listed once, no
  file under two parallel tasks; E1 serial on the main checkout; batch 1 has four worktrees and batch 2 two; the
  orchestrator-only files (`main.py`, `sources/__init__.py`, `scripted.py`, README) sit in I1.
- The three named changed asserts are real and as described: `test_jump.py:130` pins `FIGURE_H` 56;
  `test_pose_mediapipe.py:149` pins `blobs == () and motion is None` (the fake's 48x64 blue frame at 200 is under
  `LIGHT_V`; 64 px is not shrunk; the first frame has no motion, so the new assert is strict); `test_scenario.py:
  212-218` is the whole raw-refusal test.
- E1: no fake camera in the suite has `provides`, so the default keeps today's inputs. `test_runner.py:694`, `:697`
  and `:711` are unchanged. All built games declare `needs = {"pose"}`, and the lobby filters with `needs <= inputs`
  (`lobby.py:145`), so walkup's pose-only claim (I1) hides no built game. `loop(until=)` fits `runner.py:610-627`.
- G6's geometry, computed: at zone x 0.15, 0.5 and 0.85 the 50-row rects span columns -6 to 43, 39 to 88 and 83 to
  132, rows 0 to 49. The band (columns 18 to 127, rows 50 to 59) never meets them. The text widths at 1x are 41
  ("GET SET"), 29 ("JUMP!"), 83 ("RING THE BELL!"), 59 ("BELL RUNG!") and 53 ("NICE TRY!"), all inside the band's
  110 columns, with gutters for `find_text`. `_row(28) = 34` and `_row(40) = 24`, so the "DING!" pop stays at rows 37
  and above and the banner at rows 23 to 40, both clear of row 50. The score box (rows 0 to 17) and the 2x result number are untouched.
- W: the shrink of a 640x480 frame costs 0.39 ms (`feat_cost.py`), inside the 3 ms perf test. `cv2` stays out of
  `import arcade.main`: `blobs` is imported only by `pose_mediapipe` (lazily, from `make_sources`) and by the raw
  replay path, and I1's exports leave `blobs` out.
- RP: the range bounds reject no existing fixture. Boxes are clamped by `actors.body_box` and
  `pose_mediapipe.box_of`, `Body` clamps keypoints, and `raw_sample()` is in range. `check_header` ignores unknown
  keys today, so R can write `inputs` before RP lands. `test_scenario.py:115`'s full-header pin holds when `inputs`
  is written only on request.
- R and C as lobby scenes: every frame they draw passes `_push`'s limiter and governor (`runner.py:548-553`), with
  no path around them. R's cue width (21 characters: 125 px) fits 128. C's `VIEW` (rows 10 to 59) stays above
  row 60.
- Privacy (spec 6.5): the writers named (Sensed and raw records, scores, sessions, `calibration.json`) are the only
  writes the plan adds. Raw frames leave only through the tap on the source thread via `encode_raw` (base64 and
  `struct`). No new INFO line in `run`. `make_sources` already takes `calibration=` and has a default clock, so C's
  call works.
- Standing limits: nothing goes to the card or the Pi, nothing is fetched, no audio source is built (Q99 kept: `NoAudio`
  in raw replay, no samples in the tap), and the size work is 128x64 only.

## What I did not check
- The core plan's amendment line numbers (588, 620, 640, 690) and Task 18's span (5085 to 5392).
- Spec 9.5's twelve scripts against R's names and seconds, and the cue texts (Q142 leaves them to the owner).
- Spec 4.1, 4.3 and 10 line by line; the whole of `attract/lobby.py`.
- G6's real `flash_area` and `square_flashes` after the change (not simulated; the band is static 1x text, so I
  expect no change).
- No test file was run; every claim above comes from reading the code at HEAD or from the probes named.
