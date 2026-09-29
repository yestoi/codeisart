# Iteration 9, amendment: the scale survives a hip dropout (S3)

Added by the operator 2026-09-28 22:40 CDT, after the owner's hand-read spike reported (branch `spike/hand-read`,
ed7c80c, docs/superpowers/reviews/2026-09-28-hand-read-spike.md). Decision Q48 (defaulted). The plan
docs/superpowers/plans/2026-09-28-it09-pong-by-the-body.md listed "the scale's fallback when the hips leave the
frame" under Left out; this amendment takes it in, because Pong's paddle now reads `Body.scale`.

## The fault (measured by the spike on recordings of the owner)
`Body._measured_scale` (`arcade/sensed.py:92`) is the nose-to-mid-hip length. Without hips it is
`NOSE_TO_HIP_PER_TORSO` x `TORSO_PER_SHOULDER_WIDTH` x shoulder width. On a real person in a 640x480 frame the
shoulder width reads short (normalized x, and landmarks inside the shoulder's edge): torso 0.16 by the fallback
against 0.26 measured, a ratio of 0.62. `input.Depth` reads ln(0.62) / 0.6 = -0.8: the paddle goes to the far
end on a hip dropout. A laptop on a low table puts the hips at the frame's bottom edge, and a step towards the
camera pushes them out.

## Task S3 (opus; its own worktree from main's HEAD; test-first)
Files: `arcade/sources/camera.py`, `tests/arcade/test_camera.py`. Nothing else. `arcade/sensed.py` is not
changed (the protocol is frozen; a body nobody has measured keeps today's fallback).

Interfaces:
- `RATIO_TAU = 1.0` (s): the time constant of the learned ratio's smoothing.
- `_Track.per_width: float = 0.0`: this person's measured scale per shoulder width, 0.0 until learned.
- A capture's scale is **measured** when the raw body's nose is confident and `hip_mid` is not None.
  - Measured: the reading is `raw.scale`; when `raw.shoulder_width > 0` the track learns
    `raw.scale / raw.shoulder_width` into `per_width` (the first value at once, then smoothed by `RATIO_TAU`).
  - Not measured, `per_width > 0` and `raw.shoulder_width > 0`: the reading is `per_width * raw.shoulder_width`.
  - Not measured otherwise, and the track has a scale: no reading; the track's scale is held.
  - A new track that was never measured: `raw.scale`, the fallback, as today.
- The reading goes through the `SCALE_TAU` smoothing as today. `_match`'s scale cost uses the same reading
  rule, so a hip dropout does not raise a track's cost against its own body.

Acceptance tests (tests/arcade/test_camera.py), each seen failing first where it can fail:
- `test_tracker_scale_holds_when_the_hips_drop_out`: a body with nose-to-hip 0.39 and shoulder width 0.128
  (the fallback reads 0.24); 10 captures with hips, then 10 with both hips under MIN_CONF: every emitted scale
  is within 3 percent of 0.39, and the id does not change.
- `test_tracker_scale_follows_a_step_in_without_hips`: hips out; the nose and shoulders grow 1.3 times about
  the anchor in one capture: the emitted scale is within 5 percent of 1.3 times by the third capture after.
- `test_tracker_scale_returns_to_the_measure_when_the_hips_come_back`: after a dropout the hips return with
  nose-to-hip 0.39: within 3 percent at once and after.
- `test_tracker_scale_of_a_body_never_measured_uses_the_fallback`: a new track without hips reads
  1.5 x 1.25 x its shoulder width (today's behaviour).
- `test_tracker_scale_is_held_without_hips_and_shoulders`: measured once, then only the nose and one shoulder
  are confident: the scale stays, within 1 percent.
- `test_depth_reads_steady_through_a_hip_dropout`: the tracker's bodies fed to `arcade.input.Depth` at 10
  captures a second and 30 ticks: across a 1 s hip dropout on a still body the value moves less than 0.05.

Constraints: the plan's constraints hold. No existing assert is changed; `test_tracker_scale_and_placement`
and `test_tracker_scale_follows_a_step_within_three_captures` pass unchanged. No `cd`, no stash. Run
`tests/arcade/test_camera.py`, `test_input.py`, `test_sensed.py`, `test_runner.py`, `test_pose_mediapipe.py`
and `test_festival.py` before the commit; the operator runs the whole suite at the merge.

## Left out (roadmap, for the arcade's return)
The full pose model and 30 captures a second, merging duplicate poses, the hand point as the mean of wrist,
index and pinky, `input.Cursor` in place of `Body.cursor` where a game still points, the camera's index by
name. The nose's dropout uses the same rule here (not measured by the spike).
