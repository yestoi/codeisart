# it21 code review (42f2d40..00c5e74, code head d2f1b63)

Reviewer: the it21 code reviewer. I judged the code against the plan
`docs/superpowers/plans/2026-10-02-it21-m5-wiring-record-calibrate.md` and the spec
`docs/superpowers/specs/2026-09-26-wall-arcade-design.md`. The commits after d2f1b63 change docs only. The probes
are in the session scratchpad,
`/private/tmp/claude-502/-Users-trey-dev-codeisart/3d4c1cbf-546d-4e23-a6ab-f6f8456f0239/scratchpad/it21-code-review/`.
The mutants ran in a clean `git archive d2f1b63` export there (`tree/`). After the last probe I checked that export
against d2f1b63 again, and it matches. The only change I made to the repository is this file. Nothing touched the Pi,
the LED card or the network.

## Verdict: APPROVED

I found no blocking finding. The safety path, the privacy boundary, the standing rules, the assert diff and the test
counts all hold. Every probe that could have shown a defect came back clean, except the one in note 1. That one is a
real defect but rare and mild, so I leave it as a note.

## Blocking findings

None.

## Noted, not carried

1. **calibrate saves when the camera died during `clear`** (`arcade/calibrate.py:254-263`, also `:236-237`).
   - `_clear` counts time while no body is in view. An unavailable camera also gives no body.
   - Captures count only when `camera_fresh`, and `set_status` keeps only `mic_ok`.
   - Probe `p_calibrate_camera_dies.py`: the test's operator and lamp, a strict Runner as `main` builds it, and a
     ScriptedCamera whose frames end. The clear starts at 13.9 s.
     - **Camera dies at 14.0 s**, with the operator still in view: 0 clear captures. It saves `calibrated True`,
       `static_mask ()` at 23.97 s, and the wall shows SAVED. `main` would return 0.
     - **Camera dies at 16.0 s**: 54 captures, and the lamp is kept.
     - **Camera never dies**: 300 captures, and the lamp is kept.
   - Why it is not carried: the input is narrow. The camera's thread has to die, or stall past `CAMERA_STALE`,
     within the first seconds of the clear while a body is still in view. The harm is also small. The zone and the
     baseline are already right, and in `run` the StaticMask hides a still lamp within 5 s (`calibrate.py:301`).
   - A fix if wanted: keep `camera_ok` in `set_status`, and restart the clear on a tick without it, as a body does.
2. **The bell lights rows 60 to 63** (`arcade/games/jump.py:240`). `fx.flash` does it on about 12 ticks per ring,
   from `fx.render`, never from `game.draw`. This predates it21 (42f2d40 `jump.py:234`). What Jump draws itself
   keeps the rows dark.
3. **The privacy rule misses a bare `save`** (`tests/arcade/test_privacy.py:37`).
   - `from numpy import save` followed by `save(path, frame)` passes the rule (probe below). The plan names only
     the attribute `.save`.
   - The rule's reach is right. A new file anywhere under `arcade/` is parsed: `arcade/newdir/leak.py` with
     `cv2.imwrite` fails `test_no_forbidden_calls`.
4. **A camera that dies during rec** (`arcade/sources/record.py:124-148`).
   - REC keeps counting, with no figure on the wall.
   - A Sensed file goes on writing records with no bodies: `camera_fresh False` and `camera_t` rebased from 0.0.
     `ReplayStream` holds the last capture until it goes stale, which matches what happened live.
   - A raw file simply stops, because the tap is no longer called.
   - Probe `p_record_camera_dies.py`: 60 records written, 30 of them with bodies. REC shows on every rec tick, and
     rows 60 to 63 stay dark. Nothing in the file is wrong, and the operator can see the problem.
5. **Calibrate's words "STAND FAR LEFT" and "STAND FAR RIGHT"** (spec 6.6 step 2).
   - These are the plan's words for the spec's "far corners".
   - The zone's x is the far corners' anchors plus the near one. With perspective, a player at a near corner can
     stand outside that x.
   - This is how the spec designs the step, not something the code adds.

## The standing rules

- **The wall is 128x64.** Every test and probe here uses `make_cfg((128, 64))`. Nothing for other sizes was added.
- **Rows 60 to 63 stay dark.**
  - Jump, `p_jump_noise.py`: `game.draw` under `degrade(**REAL_NOISE)` at zone x 0.15, 0.5 and 0.85, ids 1, 3, 8,
    12, 24 and 37, with three 0.15 jumps each. It never lit rows 60 to 63. The only light there came from
    `fx.render` (note 2).
  - REC: `test_record.py:315`, plus the camera-dies probe.
  - Calibrate: `test_calibrate.py:213`, plus `p_calibrate_noise.py` (ids 1, 2, 5, 9, 17 and 33 under REAL_NOISE).
  - Killing `record.py`'s fill makes the test fail (M8).
- **The flash rule.**
  - Jump, `p_jump_flash.py`: run through the Runner and Lobby under REAL_NOISE, on the canonical scenario and on
    0.15 jumps at x 0.15, 0.5 and 0.85, with three seeds each. `flash_held_ticks` stayed 0 on every tick. The raw
    concurrent flash area over Jump's frames was at most 0.0145, against the 0.1 limit.
  - REC: `test_record.py:322-323` (held 0, area under `SMALL_AREA`).
  - Calibrate: `test_calibrate.py:218-226`.
- **Safety path.**
  - `RecordScene` and `Calibrator` are lobbies, and they have no display of their own. `record()` and
    `calibrate.main` hand the display only to `Runner`.
  - `Runner._push` sends every frame through `BrightnessLimiter` and then `FlashGovernor` (`runner.py:556-561`).
  - Neither command pushes a frame any other way.
- **`import arcade.main` loads no cv2, mediapipe or sounddevice.** `p_imports.py` loaded none of the three for
  `import arcade.main`, `build_parser()`, `arcade.sources.record`, `arcade.calibrate`, `arcade.stats` or
  `arcade.sources`.
- **No feel band was loosened, and the frozen game protocol is unchanged.**
  - `arcade/game.py`, `feel.py`, `flash.py`, `limiter.py`, `juice.py` and `tests/arcade/test_feel.py` are not in
    the diff.
  - The only changed feel number is `test_jump.py:130` (56 to 50, `FIGURE_H`), which is on the allowed list.
- **Nothing talks to the Pi, the LED card or the network.** The diff's only subprocess is `git rev-parse --short
  HEAD` in `record.git_sha`. It adds no socket, http or ssh. The colorlight display opens only through the
  existing `build_display`, when a command runs on the wall.

## Privacy (spec 6.5)

- **Where the tap is set.** It is set only in `record.py:135`, on the tick rec starts. It is cleared at
  `record.py:142`, when rec ends, and again in `record()`'s `finally` (`:252`) before `camera.close()` and then
  `writer.close()`.
- **Who can record raw.** `refusal()` asks for consent on every recording. It refuses raw on colorlight and raw
  from any camera except mediapipe. It does all of this before any source or display opens
  (`test_a_refusal_opens_nothing`).
- **Where the frame goes.**
  - `MediaPipeCamera.step` builds the `RawRecord` and calls the tap on the camera's own thread
    (`pose_mediapipe.py:208-210`). The record holds the working frame in grey, at `FRAME_SHAPE`.
  - `features.gray` is read nowhere else in `arcade/` (grep).
  - In raw mode the main thread writes nothing (`RecordScene.update`, `raw_camera` set).
- **What the mutants show.**
  - Setting the tap before the loop puts the countdown's captures in the file, and the tests catch it: M6, 151
    records against 60.
  - Leaving the tap set at rec's end is shadowed by the `finally`, so it changes nothing on disk (M7, survived).
- **The rule's reach.** See note 3.

## Removed or changed asserts (`git diff 42f2d40..00c5e74 -- tests/`)

Only the allowed ones changed:

- `tests/arcade/test_jump.py:130`: 56 to 50 (`FIGURE_H`).
- `tests/arcade/test_pose_mediapipe.py:149`: `motion.shape == (64, 128) and not motion.any()`.
- `tests/arcade/test_scenario.py:212-218`: `test_raw_file_is_not_replayed_yet` was removed.
- `tests/arcade/test_blobs.py:89`: the setup is now `FrameFeatures(work=(200, 150))`.

The other removed lines are imports and the FakeCapture and camera helper setup. None of them is an assert.

## Collect and skip counts

- `--collect-only -q` collects 2326 tests, up from 2236 at the base. This matches the orchestrator.
- The diff adds no skip or xfail marker. I did not run the full suite, so the skip count of 3 is the
  orchestrator's figure.
- The 12 iteration test files, run together: 333 passed in 35.23 s (`subset.txt`).

## Mutation probes (`mutants.py`, `mutants.txt`)

Killed (the tests fail):

- M1: the zone's y taken from the anchors alone. `test_a_jump_stays_in_the_calibrated_zone` fails at (0.3, 0.5).
- M2: `hide_still` left on in calibrate.
- M3: `FrameFeatures` ignoring `hide_still`.
- M4: record's runner not strict. GuardClock reports "record ran past 1000 ticks": the raising scene would hang
  record, and the test catches it.
- M5: calibrate's runner not strict.
- M6: the tap set before the loop.
- M8: rows 60 to 63 not blacked in REC.
- M9: the countdown writing records.
- M10: the static mask not applied.
- M11: no shrink to the working size.
- M12: motion always mirrored.
- M13: the box range not checked.
- M14: `provides` ignored in `sense()`.
- M15: the header's `mirror` ignored in the raw replay.
- M16: no `DUE_SLACK`.
- M19: `until` ignored. The test hangs and is killed at 90 s.

Survived:

- M7: the tap not cleared at rec's end. The `finally` clears it anyway, so nothing on disk changes.
- M17: Jump's band black box removed. No figure pixel reaches the band in the scenarios the tests use, and the code
  draws the box today.
- M18: the clear restarted only by in-zone bodies. The code restarts on any body, as the plan says.

## Also checked and found right

- **E1.**
  - A camera whose `provides` raises, or is not a set, fails the camera.
  - Names outside `CAMERA_INPUTS` are cut (a declared deviation).
  - `loop(until=)` stops after the tick on which `until()` is True.
  - `ScriptedCamera.provides` is a class attribute (a declared deviation).
- **G6.** The prompt band is rows 50 to 59, columns 18 to 127. Under REAL_NOISE the band's word is always found
  there at 1x, the band holds only `TEXT_COLOR`, the pop ends above row 50, and the bell rings (`p_jump_noise.py`).
- **W.**
  - `FrameFeatures` shrinks to `WORK_SIZE` with INTER_AREA and mirrors motion by `mirror`.
  - It drops static-mask blobs in working-frame units.
  - The runtime mask applies only with `hide_still`.
  - `MediaPipeCamera.provides = CAMERA_INPUTS`.
- **R.**
  - The countdown runs 3, 2, 1 and writes nothing.
  - REC and the seconds show on every recorded tick, and cues show whole at rows 28 to 35.
  - Motion is dropped unless `--with-motion`.
  - The header holds `inputs` (raw: motion and pose, plus `mirror`).
  - The writer is closed on every path, also when the scene raises, raw or not.
- **C.**
  - The steps and constants match the plan.
  - The zone's y is never thinner than (0.2, 0.8).
  - `_from_json` runs before `save_calibration`, and a zone that would not load fails as NOT SAVED.
  - "NO ONE CAME" comes after `STEP_TIMEOUT`, and no file is written.
  - Under REAL_NOISE every probe run saved zone (0.251, 0.2, 0.751, 0.8), `min_height` 0.4 and one mask light.
    A 0.15 jump from every stand stays in that zone.
- **RP.**
  - The reader's range checks are `BOX_RANGE`, `KEYPOINT_RANGE`, `CONF_RANGE` and `MAX_ABS`.
  - `RawReplayCamera` is paced by capture time plus `DUE_SLACK`.
  - It provides pose and motion, follows the header's `mirror`, and ends unavailable.
- **S and I1.**
  - stats is read-only.
  - `calibrate`, `record` and `stats` are dispatched lazily.
  - `run --replay` builds sources through `make_sources(replay=)`.
  - `run --require` runs the doctor before any source opens and returns the doctor's code (a declared deviation).
  - `record --script` is required (a declared deviation).
- **The declared deviations** in `orchestrator-report.md` are all acceptable:
  - C imports `_from_json`.
  - C draws blob dots.
  - The words "NOT SAVED".
  - REC's end tick shows figures only.

## Not checked

- The full suite. It was not allowed, so the skip count of 3 comes from the orchestrator.
- A live camera, MediaPipe or sounddevice, and anything on the Pi: timing, `record --raw` throughput and file size.
  The same goes for the colorlight display.
- The race between `record()`'s `writer.close()` and a tap call still in flight. This can only happen when
  `camera.close()`'s 2 s join times out. I read it but did not probe it.
- A raw replay of a hand-edited record. For example, a detection without 17 keypoints makes `RawReplayCamera` raise
  on every later call, but nothing in the code writes such a record.
- `stats` against a real sessions log from the wall.
- I2, the sheet. It is the operator's, in verify.
