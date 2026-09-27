# Iteration 2 reviewer verdict

Range: `b93e767..HEAD` (`26f684f`, `13ca20a`, `62a4fe6`, `a6d957c`, `f84700f`, `3017693`).
Plan: `docs/superpowers/plans/2026-09-27-it02-carried-sensed-actors.md`. Reviewed 2026-09-27.

## Verdict: APPROVED

## Blocking findings (file:line — what — why it blocks)

None.

## Evidence

### Verbatim check against the plan

I extracted all 23 whole-file code blocks from the plan and diffed each one against the file at the commit that lands it and again at HEAD. Every file is byte-identical to the plan:

| Task | Commit | Files (all identical to the plan) |
|---|---|---|
| 1 | 26f684f | show/display/colorlight.py, show/display/\_\_init\_\_.py, show/display/ddp.py, tests/test_colorlight.py, tests/test_ddp.py, tests/test_display.py |
| 2 | 13ca20a | arcade/config.py, arcade/calibration.py, tests/arcade/test_config.py, tests/arcade/test_calibration.py |
| 3 | 62a4fe6 | .gitignore, arcade/main.py, tests/arcade/test_doctor.py, tests/test_gitignore.py |
| 4 | a6d957c | arcade/sensed.py, arcade/sources/mirror.py, tests/arcade/test_sensed.py, tests/arcade/test_mirror.py |
| 5 | f84700f | arcade/poses.py, arcade/sources/actors.py (the Task 5 version), tests/arcade/test_actors.py |
| 6 | 3017693 | arcade/sources/actors.py (the Task 6 version), tests/arcade/test_festival.py |

Each commit touches exactly the files in its task's `git add` list. The subject lines match the plan, and Task 1's commit carries the body the plan specifies.

### Removed or changed test lines

`git diff b93e767..HEAD -- tests/ | grep '^-[^-]'` and `git diff 7697d01..HEAD -- tests/ | grep '^-[^-]'` both print exactly the five lines the plan lists:

1. `tests/arcade/test_doctor.py`: `from arcade.main import doctor, main`. The import is widened to add `probe_pose` and `within`.
2. and 3. `tests/test_colorlight.py`: the two lines of the old `from show.display.colorlight import (...)` block. The import now adds `BRIGHTNESS_EVERY` and `SAFE_BRIGHTNESS`.
4. `tests/test_colorlight.py`: the old reference-encoder `@pytest.mark.parametrize(...)`. It now adds `(384, 4)`.
5. `tests/test_colorlight.py`: `Recorder.__init__`, which now accepts `**kwargs`.

None of the five is an assert. No assert was removed or changed. Task 1's commit body explains all four `test_colorlight.py` edits. The `test_doctor.py` import change is not an assert, so it needs no justification.

### Test counts

- `pytest --collect-only -q | tail -1` gives `183 tests collected`, as expected (iteration 1 ended at 66).
- `pytest -rs -q | grep -c SKIPPED` gives `0`. The full suite prints `183 passed`.
- I ran the suite at each intermediate commit from a `git archive` copy. The counts were 85, 123, 134, 153, 169 and 183, matching the plan's progression. Every run passed.
- Per-module counts match plan step 2: actors 16, calibration 23, arcade config 42, doctor 10, festival 14, mirror 2, sensed 17, colorlight 29, show config 5, ddp 8, display 4, font 7, gitignore 6.

### Iteration-verify steps 4 to 6

- `arcade doctor --require pose` prints `pose ok ... landmarker ran in 16 ms` and exits 0.
- `--timeout 0.01` prints `did not finish within 0.01 s` and exits 1.
- `--require ""` prints `names no source` and exits 2.
- `git check-ignore --no-index -v tests/arcade/fixtures/data/x.jsonl.gz` exits 1.
- Importing `arcade.sources.actors` and `arcade.sensed` loads none of cv2, mediapipe, sounddevice or pygame.

### Carried fixes, checked in the code

- **C1**
  - `ColorlightDisplay.__init__(..., brightness=SAFE_BRIGHTNESS)` (colorlight.py:99). Every push sends the frame packet at `self.brightness` (colorlight.py:124).
  - The 0x0A brightness packet is resent every `BRIGHTNESS_EVERY = 3` pushes, between the frame packet and the rows, and `set_brightness` resets the count (colorlight.py:116-128).
  - `_level` maps NaN and values of 0 or less to 0 (colorlight.py:52-55).
  - `make_display` passes `effective_brightness` (a `@property` in show/config.py:53), then `brightness`, then `SAFE_BRIGHTNESS` (show/display/\_\_init\_\_.py:45-46).
  - Fixed.
- **C2**
  - Colorlight checks shape, then dtype, before any byte is sent (colorlight.py:119-123).
  - DDP checks both (ddp.py:49-50).
  - Tests pin float64, int64, RGBA and grey frames, and check that nothing reaches the socket.
  - Fixed.
- **C3**
  - An empty or missing `iface` raises `ValueError` whether it comes from `iface` or `colorlight_iface` (\_\_init\_\_.py:39-42).
  - The `PermissionError` names CAP_NET_RAW, `AmbientCapabilities` and `setcap`. A failed bind closes the socket and names the interface (colorlight.py:135-146).
  - Fixed.
- **C5**
  - `brightness`, `apl_cap_day` and `apl_cap_night` must be in (0, 1]; `fps`, `camera_fps` and `gamma` must be over 0; `gamma` must be finite; `sdl_scale` must be at least 1.
  - Every `*_seconds` field (read from the dataclass fields) and `night_lux` must be 0 or more.
  - NaN fails every check (config.py:96-110).
  - Fixed.
- **C6**
  - `min_height` and `baseline_scale` must be in [0, 1]. Static-mask entries must be in 0..1 with a radius over 0. `audio_floor_db` must be in [-200, 0], which rejects NaN. `calibrated` must be a bool, and booleans are rejected as numbers.
  - A missing key takes its default. Unknown keys and missing keys each get a warning.
  - The directory is fsynced after `os.replace` (calibration.py:34-110).
  - Fixed.
- **C7**
  - `test_sdl_display_pushes_headless` now asserts the window size, pixels and key handling.
  - Fixed.
- **C8**
  - `row_packets` uses `_chunk_pixels`, the same equal split `push` uses (colorlight.py:63-78).
  - `(384, 4)` is in the reference test, and `test_row_packets_split_384_pixels_equally` pins the headers.
  - Fixed.
- **C9**
  - `.gitignore` anchors `/models/`, `/data/` and `/shots/`.
  - `doctor` returns 2 when `require` is empty (main.py:101-103).
  - `probe_pose` runs the landmarker through `within()` in a daemon thread. The `import mediapipe` stays untimed, which is documented.
  - `probe_camera` documents why it stays on the main thread.
  - Fixed, and confirmed on the CLI above.

### Conventions

- Library code has no `print`. Only arcade/main.py's CLI prints.
- No seed comes from `hash()` or `random`. Noise is keyed with `zlib.crc32`.
- Hardware modules are imported only inside probes.
- There are no unused imports.
- Tests run headless.

## Notes (non-blocking)

### Plan defects the orchestrator raised: all five confirmed

I confirmed each one with a probe against HEAD.

1. **Plan defect: `Sensed` and `Audio` accept positional arguments.**
   - `Sensed(0.0, (body,))` silently sets `camera_t` to the tuple and leaves `bodies == ()`.
   - `Audio(0.5, 0.9)` sets `level_smooth=0.9, peak=0.0`.
   - The core plan's runner, `docs/superpowers/plans/2026-09-26-wall-arcade-core.md:2884`, calls `Sensed(self.t, tuple(bodies), tuple(blobs), motion, a)`. That call would build a record with no bodies and raise no error.
   - Nothing in this iteration calls either class positionally beyond `t`, so this iteration is correct. Fix it before core Task 7 lands, and make it the first item of that amendment: `@dataclass(frozen=True, kw_only=True)` on `Audio`, and `t` as the only positional field of `Sensed` (a `kw_only` marker after it).
2. **Plan defect: `degrade` (and `shake`) fall back to the default calibration silently.**
   - A scene built with `Calibration(zone=(0.6, 0.2, 1.0, 0.8))` and a person at x 0.9 gives `in_zone=True, zone_x=0.75`.
   - Passing it through `degrade` without `calibration=` gives `in_zone=False, zone_x=1.0`.
   - Suggested fix: make `calibration` required, or have `scene` record the calibration it used, for example on the frames, so `degrade` and `shake` can reuse it.
3. **Plan defect: with one confident shoulder and no confident hip, `torso` is 0** (sensed.py:151-156).
   - `shoulder_width` needs both shoulders, so the fallback `1.25 * shoulder_width` is 0.
   - As a result the raise line collapses onto the shoulder line (0.42 in the probe), which is more permissive than spec 5's 0.3 torso above.
   - `reach` falls back to the body box.
   - With no nose-plus-hip pair, `scale` is 0.0, which sorts that body last in "largest scale first".
   - Nothing raises, so it is not a crash. It is a behaviour gap for side-on or half-occluded players, which core Task 8's tracker should decide.
4. **Plan defect: body ids can collide.**
   - `scene(persons=[Person(0.2), Person(0.5, id=0), *crowd(1), *crowd(1)])` gives ids `[0, 0, 100, 100]`.
   - `scene` uses the list index for an unnamed person, and `crowd` always starts at 100.
   - `degrade` keys its noise on `body.id`, so colliding bodies get identical dropout and jitter.
   - A future tracker test would see two bodies with one id.
   - Suggested fix: `scene` raises `ValueError` on duplicate ids, and `crowd` takes an `id_base` parameter.
5. **Plan defect: `Body.in_zone` defaults to True, and so does `Blob.in_zone`.**
   - A body or blob that never went through `place` or `place_blob` counts as in the zone.
   - `headlamps()` returns raw blobs with `in_zone=True` until `scene` places them.
   - A default of False would fail safe, so the runner could never treat an unplaced body as a player.

### Further observations: minor, none blocking

6. **Headlamp blob outside 0..1.** `headlamps()`'s crossing blob has x from -0.05 to 1.05, so `Sensed.blobs` can hold x outside 0..1.
   - It is out of the zone after placement, so a game that filters on `in_zone` never sees it.
   - A consumer that maps every blob to a pixel without clamping would index at -1, which numpy wraps.
   - Either clamp `Blob` the way `Body._clean` clamps keypoints, or document that blob x is unclamped.
7. **Stale boxes after jitter.** `_noisy` (actors.py:332-339), used by both `shake` and `degrade`, replaces the keypoints but keeps the original `box` and `scale`.
   - `Body.height`, and therefore `place`'s `min_height` test, use the clean box.
   - This is probably intended, since the box stands for a detector box, but it is not documented.
8. **No input validation for two degenerate cases.**
   - `tempo(0)` and `camp_kick(0)` raise `ZeroDivisionError`, and a negative bpm gives a negative period. Neither is validated.
   - `place` divides by the zone's width and height, so a hand-built `Calibration(zone=(0.5, 0.2, 0.5, 0.8))` raises `ZeroDivisionError`. `load_calibration` already rejects such a zone, so only code that constructs one directly can hit this.
9. **`wind` docstring.** It says "an onset at each gust peak", but the gusts (every 2.7 s) are not aligned with the level swell (period 3.5 s). This is cosmetic.
10. **Uneven commit bodies.** `62a4fe6` widens a test import but has no commit body. The plan's commit command for Task 3 has none either, and the line is not an assert, so this is not a finding. The plan's commit bodies are just uneven.
11. **Working tree.** It has `docs/superpowers/workflow/state.md` modified and `docs/superpowers/workflow/evidence/it02/orchestrator-report.md` untracked. Both are workflow files, which plan verify step 7 allows.
