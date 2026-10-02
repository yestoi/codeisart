# it21 RP: raw replay and the reader's range check (implementer's report)

Branch `worktree-agent-a02d14efeb9c96e2b`, from BASE2 4c23259 (checked). Commits:
- 2f374f5 `feat(arcade): it21 RP, the reader's range check and the header's inputs` (the cut-order's first: it stays)
- d7bf392 `feat(arcade): it21 RP, raw replay through FrameFeatures and BodyTracker`
- this report's commit

Test-first: each batch of acceptance tests was written and seen to fail for the missing feature (6 failures:
no `inputs` keyword, no `ScenarioReader.inputs`, no `MAX_ABS`, out-of-range lines read as good ones; then 3
failures: `open_replay` still refused a raw file), then the code.

## Files changed
- `arcade/sources/scenario.py`: constants `INPUTS = CAMERA_INPUTS | AUDIO_INPUTS`, `BOX_RANGE = (0.0, 1.0)`,
  `KEYPOINT_RANGE = (-1.0, 2.0)`, `CONF_RANGE = (0.0, 1.0)`, `MAX_ABS = 1e3`; `_within(v, bounds, what)` (finite and in
  bounds, else ValueError); `_box` (BOX_RANGE), `_keypoints` (x, y KEYPOINT_RANGE, conf CONF_RANGE), `_body`'s vx, vy,
  scale, seen_ago, torso_per_width, `_blob`'s x, y, size, vx, vy and `_audio`'s floats (bpm None still allowed) within
  MAX_ABS; t and camera_t (and a raw record's t) finite only. Raw detections go through the same `_box`/`_keypoints`.
  `make_header(..., inputs=None)`: key `inputs` (sorted list) only when given. `check_header`: `inputs` absent or a
  list of names from INPUTS; `mirror` absent or a bool. `ScenarioReader.inputs`: the header's as a frozenset, or
  CAMERA_INPUTS. Docstrings updated.
- `arcade/sources/replay.py`: `ReplayCamera(stream, provides=CAMERA_INPUTS)` (`provides & CAMERA_INPUTS`;
  `open_replay` passes `reader.inputs`). New `RAW_PROVIDES = {"pose", "motion"}`, `DUE_SLACK = 1e-9`,
  `RawReplayCamera(reader, calibration=None, clock=time.monotonic)` (FrameFeatures imported inside `__init__`),
  `NoAudio`. `open_replay` on a raw file returns `(RawReplayCamera, NoAudio)`.
- `tests/arcade/test_scenario.py`: `test_raw_file_is_not_replayed_yet` removed (the plan's named change, :212-218);
  9 acceptance tests added (below); imports added (`CAMERA_INPUTS`, `check_header`, `body_box`, `make_keypoints`, the
  `scenario` and `replay` modules as `scenario_mod`, `replay_mod`). No other assert changed.

## Tests
New: `test_a_box_out_of_range_is_skipped`, `test_a_keypoint_far_out_of_range_is_skipped`,
`test_a_float_over_max_abs_is_skipped`, `test_a_raw_detection_out_of_range_is_skipped`,
`test_header_inputs_round_trip_and_set_replay_provides`, `test_a_header_without_inputs_provides_every_camera_input`,
`test_raw_file_replays_through_features_and_tracker`, `test_raw_replay_paces_by_capture_time`,
`test_raw_replay_ends_unavailable`. No real clock anywhere (FakeClock).

Command (worktree root):
`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs --durations=15
tests/arcade/test_scenario.py tests/arcade/test_record.py tests/arcade/test_blobs.py tests/arcade/test_doctor.py
tests/arcade/test_privacy.py tests/arcade/test_sources.py tests/arcade/test_runner.py tests/arcade/test_pose_mediapipe.py`
-> **245 passed, 1 skipped in 7.36 s** (the skip: `test_pose_mediapipe.py:383`, no `models/` in a worktree, expected).
`tests/arcade/test_scenario.py` alone: 57 passed (was 49: +9 new, -1 removed).

Time: none of the new tests is in the top 15 (`--durations=15`'s slowest is 0.58 s, test_runner's). Their own call
times (`--durations=0`): `test_raw_file_replays_through_features_and_tracker` 0.06 s, the max_abs and raw-range tests
0.01 s each, the rest under 0.005 s: about **0.1 s** in all, under the +1.5 s share.

Checks: `arcade.__file__` resolves under the worktree; `import arcade.sources.replay, arcade.main` loads no `cv2`,
`mediapipe`, `sounddevice` or `arcade.sources.blobs` (so I1 can export `open_replay` from `sources/__init__.py`).
Mutation check: with `DUE_SLACK = 0` the pacing test fails at +0.1 s (100.0 for 100.1), so the `+ 1e-9` is
load-bearing (the plan review's note 4). No forbidden call (test_privacy passes).

## Readings taken (no deviation from the plan's text, where it was silent)
1. Pacing: "at +0.05 s the first capture" read as the first capture returned from offset 0 (it is t0, due at once)
   to just under +0.1, the second from +0.1. The test checks +0, +0.05, +0.1, +0.19 (still the second), and a late
   first call at +0.25 that runs the second and third in turn (motion lit between them proves the second ran).
2. `available` mirrors it20's D2 for ReplayCamera: the `latest()` that runs the last capture is still available,
   the next one, finding none left, turns it False and holds the last result. A raw file with no captures: the
   first `latest()` gives None and turns `available` False (before that call it reads True).
3. `RawReplayCamera` returns FrameFeatures' own blobs (always () on a grey frame; the test asserts it), and
   `provides` excludes "blobs" anyway, so the runner would drop any.
4. Both FrameFeatures and BodyTracker get the record's own `t` (relative steps are what they use); the result is
   stamped `opened + t - t0` on the runner's clock (at most `clock() + 1e-9`, inside the runner's CLOCK_SLACK).
5. The header's `inputs` and `mirror` are strict: present as `null` is refused, as is `mirror` 1 (a bool only).
   An empty `inputs` list is accepted (a recording of nothing from the camera: `provides` empty).
6. `CONF_RANGE` is a fourth named constant (the plan names three; conf's 0..1 needed a name). Boundaries inclusive:
   a box 0.0 or 1.0, a keypoint -1.0 or 2.0, a float of exactly 1e3 pass.
7. `opened` is read after the first record is peeked (so a slow gzip open never makes the first capture late).

## Questions for the owner (none blocked)
- Q-RP1: a blob's `color` is ints (`int(c)`), so a color of 1e308 still decodes to a huge int; the plan's range is
  for floats only. A game that puts a blob's colour into a uint8 frame would raise on it. Range-check `color` to
  0..255 in a later slice? (Not done: not in the plan.)
- Q-RP2: a record's `t` far in the future (finite, e.g. 1e300) in a raw file is never due: the replay then holds its
  last capture, available, until it goes stale in the runner. Acceptable (finite-only was the plan's rule for t).

Not touched: `arcade/sources/__init__.py` (I1 exports `open_replay` and wires `make_sources`).
