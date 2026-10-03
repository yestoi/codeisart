# Plan review (integration lens): pose on the sensor

Plan: `docs/superpowers/plans/2026-10-02-pose-on-the-sensor.md`. Spec: `docs/superpowers/specs/2026-10-02-pose-on-the-sensor-design.md`.
Reviewed 2026-10-02 against both checkouts (main at 1a00b49; the worktree `/Users/trey/dev/codeisart-wall` on
`wall-bringup` at 97972ba). None of the files the plan edits differ between the two branches (checked file by file
with `git diff --quiet main wall-bringup -- <path>`), so the plan's line numbers hold in the worktree after Task 0.
Lens: tests, wiring, threading, the operational path (Tasks 0, 1, 4, 5, 6, 7, 8). The decoder is another
reviewer's.

## Critical (would break the build or the wall)

### C1. Task 4 breaks `test_make_sources_mediapipe_gets_the_config_clock_and_calibration`, and the plan says "all pass"

Plan, Task 4 Step 3, the mediapipe branch:

```python
camera = pose_mediapipe.PoseCamera(cfg, size, clock, calibration=cal)
```

and Task 4 Step 4: "Expected: all pass" for `tests/arcade/test_sources.py`.

What is wrong: the existing test at `tests/arcade/test_sources.py:85-98` monkeypatches the alias:

```python
monkeypatch.setattr(pm, "MediaPipeCamera", Spy)
```

Rebinding `pm.MediaPipeCamera` does not rebind `pm.PoseCamera` (they are two names on the module; Task 1 makes them
point at the same object, and `setattr` replaces one pointer). Once `make_sources` calls `pose_mediapipe.PoseCamera`,
the Spy is never used and the real `PoseCamera` is built with `camera="mediapipe"`, `capture="opencv"`,
`camera_index=0`:

- in the main checkout the model exists, so a real MediaPipe `Landmarker` and `cv2.VideoCapture(0)` (the Mac's
  camera) are opened from a unit test and the camera thread starts;
- in the worktree the model file is missing (see I2), so it logs "mediapipe camera unavailable" instead;
- either way `assert isinstance(cam, Spy)` fails.

The plan does not touch this test in any task. Task 1 Step 4 runs `test_sources.py` and passes (the branch still
calls `MediaPipeCamera` then); Task 4 Step 4 fails.

Fix (one of): change the existing test to `monkeypatch.setattr(pm, "PoseCamera", Spy)` in Task 4 Step 1 (its
`Spy.__init__` also needs `capture=None, detector=None` keywords only if the branch passes them, which it does not),
or keep the mediapipe branch calling `pose_mediapipe.MediaPipeCamera`. The first is right: the plan's own new test
already patches `pm.PoseCamera`.

## Important (wrong but survivable)

### I1. Task 8 runs the full suite on the Mac; the owner said on 2026-10-02 that full suites go to the Pi

Plan, Global Constraints: "The full suite runs once on the Mac at the end, under 540 s (Q102)". Task 8 Step 1 runs
it in the worktree on the Mac.

The owner's instruction of the same day (memory `run-tests-on-the-pi`, quoting him: "Can we run the test on the rpi
to confirm. We shouldn't be taxing my mac anymore if we can avoid it"): the full suite and heavy checks go to the
Pi 5 when it is reachable and no wall process runs there; unpushed code travels as a git bundle on stdin into a
scratch clone under the lock. The plan also says "nothing runs on the Pi in this plan", and promptviz holds the wall,
so the Pi has a wall process running: by the memory's own condition the Pi is not available either.

Fix: the plan must say which the owner wants, not assume the Mac. Either state "the owner allowed the Mac run for
this plan because promptviz holds the Pi" (ask him), or make Task 8 the bundle-on-stdin run on the Pi under the lock
after promptviz stops, before the wall session. Do not silently run a 540 s suite on the 8 GB Mac against his
instruction.

### I2. The worktree has no `models/` directory: `MODEL_PATH` does not exist there

```
$ ls /Users/trey/dev/codeisart-wall/models/
ls: /Users/trey/dev/codeisart-wall/models/: No such file or directory
$ cd /Users/trey/dev/codeisart-wall && .../python -c "import arcade.main; print(arcade.main.MODEL_PATH.exists())"
False
```

`models/` is gitignored (`/models/`), so the worktree never got it. Consequences for the plan as written:

- `tests/arcade/test_pose_mediapipe.py:382` (`test_landmarker_runs...`) skips in the worktree, so the suite's count
  is "4 skipped", not the "3 skipped (the Mac's)" Task 8 expects. The three Mac skips are `test_colorlight_slot`,
  `test_colorlight_child` and `test_sandbox`.
- The only test that exercises the real `Landmarker` never runs where the plan runs its tests, so nothing checks
  `MediaPipeDetector` against real MediaPipe at any point (the plan's `MediaPipeDetector` tests use the fake).

Fix: in Task 0 add `ln -s /Users/trey/dev/codeisart/models /Users/trey/dev/codeisart-wall/models` (the memory's
Pi recipe does the same with a symlink), and set Task 8's expectation to the measured skip count.

### I3. `run --require camera` with `camera = "imx500"` can hold the owner, and the Pi's lock, for 5 minutes with no way to shorten it

Plan, Task 5: `probe_imx500(timeout, index=0, upload_wait=UPLOAD_WAIT)` with `UPLOAD_WAIT = 300.0`; `doctor()` calls
`probes[name](timeout)` so `upload_wait` is always 300 s in real use, and `--timeout` only bounds the first 3 s. When
frames flow but no tensor comes for another reason (the wrong network loaded, a dropped `CnnOutputTensor` stream, a
`.rpk` the sensor rejected), the owner sees "uploading the network to the sensor, up to 4 minutes" and waits 300 s
for `imx500 posenet 30/s: N frames, no tensor in 300 s`. Under `flock -w 300 /tmp/pi5.lock` the run holds the lock
for that whole time, and with `--require camera,pose` the same probe runs twice (both names map to it), opening the
camera twice: a failing first start costs up to 10 minutes before the arcade even says no.

Fix: run the one probe once and reuse its result for both names (cache in `make_probes`), and let `--timeout` cap
`upload_wait` too or print the elapsed seconds while waiting so the owner can SIGINT with knowledge. At the least
the runbook should say "a second `imx500` line repeats the probe" and name `^C`.

### I4. The spec's wall-session doctor command does not exist; the plan's runbook command differs from the spec and neither notes it

Spec section 5 step 2: `doctor --require camera,pose --config arcade.pi.toml`. The `doctor` subparser has no
`--config` (`arcade/main.py:230-236`); the plan's runbook text (Task 7 Step 5) uses `--camera imx500 --capture
picamera2` instead, which is right for the code the plan builds. The hand-off in Task 8 Step 3 says "the doctor's
line" without the command. The owner reading the spec at the wall will type a flag that argparse rejects.

Fix: Task 7's runbook text is the one to follow; add a line to the plan's Task 8 report naming the exact doctor
command, and fix spec section 5 step 2 in the same commit (or say the spec's command is wrong).

## Minor

### M1. Task 0: "main is an ancestor of wall-bringup" is false, and main is two commits ahead, not one

```
$ git log --oneline wall-bringup..main
1a00b49 docs(plan): pose on the sensor ...
cd233b8 docs(spec): pose on the sensor ...
```

main is not an ancestor (it has these two commits wall-bringup lacks); the merge is a true merge, which
`git merge-tree --write-tree wall-bringup main` completes with no conflict (exit 0). Both the spec and the plan land
in the worktree. Harmless; fix the sentence.

### M2. Task 0: the fixture path is not ignored (checked), but the fallback reaches for the Pi

`git check-ignore -v tests/arcade/fixtures/posenet/sample1.npz` exits 1 in the main checkout: the only anchored
rules are `/models/`, `/data/`, `/shots/`. The scratchpad file exists and `s1`/`s4` are exactly float16-representable
(verified: all six arrays round-trip). The fallback sentence "ssh ... cat ~/imx500-spike/out/posenet_raw.npz" contradicts
"nothing runs on the Pi in this plan"; it will not be needed. Delete it or mark it as needing the owner's word.

### M3. Task 4: `arcade/sources/__init__.py` has no `log` and no `import logging`

The plan hedges ("check the module has ... add if not"). It does not have either (`arcade/sources/__init__.py:1-13`).
Say plainly: add `import logging` to the imports and `log = logging.getLogger("arcade")` after them.

### M4. Task 5: `probe_imx500(..., index)` builds `ArcadeConfig(camera_index=index)` but `open_imx500` never reads `cfg.camera_index`

`open_imx500` opens `Picamera2(imx.camera_num)`; the IMX500 object picks the camera. The probe's `index` argument and
`--camera-index` do nothing for imx500. Say so in the docstring, or drop the argument from the imx500 lambda.

### M5. Task 5: the upload notice prints to `sys.stdout`, the doctor prints to `out`

`doctor(require, probes, timeout, out=None)` writes its lines to `out`; the probe's `print(..., flush=True)` ignores
`out`. Every caller today passes no `out`, so it works, and the test uses capsys. Note it, or print to `sys.stdout`
explicitly with a comment.

### M6. Task 5: `label = f"imx500 {pose_imx500.describe(detector._imx)}"` reads a private attribute

Give `IMX500Pose` a public `imx` attribute (or a `describe()` method) so the doctor does not reach into it.

### M7. `record --raw` stays refused for `camera = "imx500"`

`arcade/sources/record.py:97-98` refuses `--raw` unless `cfg.camera == "mediapipe"`, with the message "the only
source with raw captures". After Task 1 the imx500 `PoseCamera` has the same tap. Not in the spec; a raw recording on
the Pi is now wrongly refused. Either widen the check to `cfg.camera in ("mediapipe", "imx500")` or note it as left
out in the README's "Not done" bullet.

### M8. Stale `MediaPipeCamera` prose

`arcade/sources/README.md:7-8`, `arcade/sources/record.py:8` and `tests/arcade/test_record.py:77` still say
`MediaPipeCamera`. The alias keeps them true; the README's new section (Task 7 Step 6) could say "`PoseCamera`,
formerly `MediaPipeCamera`" once.

### M9. Task 7: the gamma assertion is duplicated

`tests/arcade/test_config.py:154` on wall-bringup already asserts `cfg.gamma == 1.0` in its own test; the plan adds
gamma to the replaced test's tuple too. Fine, redundant.

### M10. Spec 3.4 says the doctor warns when `capture = "opencv"` sits beside `camera = "imx500"`; the plan does not build that

Not a failure; the plan's self-review claims 3.4 is covered by Tasks 4, 5, 7. Say it is left out.

## Checked and fine

- **Every `landmarker=` and `MediaPipeCamera(` construction** is in `tests/arcade/test_pose_mediapipe.py` (lines 92,
  217, 398, 416, plus 225 and 236 which pass neither) and `arcade/sources/__init__.py:51`; the plan updates all four
  `landmarker=` sites and the factory. No `tools/` file, `record.py` or `calibrate.py` constructs the camera or
  names the landmarker; `calibrate.py:299` only reads `camera.features`, which `PoseCamera` keeps. Identical in both
  checkouts.
- **Task 1's "`test_without_picamera2...` still finds `mediapipe camera unavailable`"**: `cfg.camera` defaults to
  `"mediapipe"` there, and the new warning uses `cfg.camera`. Correct.
- **Task 4's `_Unopened` with `start=False`**: `PoseCamera.__init__` with both injected does nothing in the `try`,
  skips `start()`; `ThreadedCamera.available` is `latest() is not None`, and `_latest` is `None`, so `available`
  is False and `latest()` None. `close()` tolerates `_thread is None` and calls `release()`, which calls
  `_Unopened.release()` and `.close()`. The warning text `imx500 camera unavailable: import of picamera2 halted;
  None in sys.modules` carries both substrings the test wants. The warning is logged once (the factory logs; the
  camera does not).
- **Task 5 argparse**: `CAMERAS = ("mediapipe", "imx500", "replay", "none")` exists in `arcade/config.py:12` and is
  not yet imported in `main.py` (the plan says to add it). `--camera` does not collide with `--camera-index`
  (exact match wins). `main()`'s positional `make_probes(camera_index, audio_device, model, capture, camera)`
  matches the new signature's order. `make_probes` looks `probe_imx500` up at call time, so the tests'
  monkeypatch of `arcade.main.probe_imx500` takes.
- **Task 5 upload test timing**: `UPLOAD_NOTICE_AFTER` is read at call time; with `timeout=0.1`, notice at 0.05 s,
  the deadline moves to `start + 0.3`; `TensorCapture.read` is instant so the loop spins hot and returns at 0.3 s
  with `why = "N frames, no tensor in 0 s"` (contains "no tensor"); `cap.reads > 2` holds; `release()` runs in
  `finally`. `test_probe_imx500_without_picamera2`: the `ImportError` message names picamera2.
- **Threading**: `make_probes` calls `probe_imx500` directly, not through `within()`, so picamera2 runs on the main
  thread as `probe_picamera2` does; `make_sources` is called on the main thread by `run`. `IMX500Pose.detect`
  reads `capture.metadata` on the camera thread right after that thread's `read()` set it.
- **Task 6 clocks**: sources stamp on the injected clock; `Runner.clock` is the same clock in production (both
  default `time.monotonic`) and in the test (`FakeClock` passed to both). `_push()` is called once per tick
  (`runner.py:447`). With `FakeClock` and `sleep=clock.sleep`, `loop` advances the clock by one period a tick, so
  `self.t` reaches 1.0 after `fps` ticks and 2.0 after `2 fps`; `max_ticks = 2 fps + 2` gives lines at t = 0,
  about 1.0 and about 2.0 (float accumulation may shift one by a tick, still inside the range): 3 lines, within
  `1 <= len <= 3`. The age is 0 ms (same clock reading in `sense` and `_push`), which still formats as
  "median 0 ms, max 0 ms (N pushes)". `caplog.at_level(DEBUG, logger="arcade")` sets that logger's level, so
  `self.log.isEnabledFor(logging.DEBUG)` is True; under `at_level(INFO)` it is False and nothing is appended.
  `loop` keeps no state between calls other than `self.t`, so the second call works. `logging` and `math` are
  imported in `runner.py` (lines 14, 15). `tests/arcade/test_headless.py` has no `caplog` and counts no log
  records. `scene`, `Person` are module imports of `test_runner.py` (line 22); `font5x7` is a conftest fixture.
- **Task 7**: the replaced test is at `tests/arcade/test_config.py:147-151` on wall-bringup, as the plan says; its
  current tuple ends `"mediapipe", 15`, so the expected failure text is right; `camera_fps = 30` loads as int and
  `gamma = 1.0` as float, both pass validation. The runbook sections the plan edits exist as described
  (`docs/runbooks/arcade-on-the-pi.md`: the model paragraph at 35-40, the doctor line at 46 with its explanation at
  50-51, the `--game` paragraph at 64). The README's "Measured facts and decisions (spec 12)." line is line 3.
- **Task 2**: the existing `fail_read=True` test raises `TimeoutError` from the camera and `capture_request` raises
  the same way in the new fake. picamera2's `capture_request(wait=)` and `IMX500.get_outputs(metadata,
  add_batch=False)` are the real signatures.
- **Task 8 hand-off**: the plan says pull "or a bundle over stdin when nothing is pushed". Nothing is pushed, so
  the bundle is the only way; that matches `pi-lock.md` (no scp; stdin carries what a command needs) and the
  memory's recipe. Nothing in Tasks 0 to 8 touches the card or the Pi apart from the fallback in M2.
- **The worktree's imports**: with the worktree as cwd, `python -m pytest` imports `arcade` and
  `tests.arcade.helpers` from the worktree (verified), as the Global Constraints claim.
