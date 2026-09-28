# Reviewer verdict, iteration 6

Range ab40231..b6cede1, one round, `it06-reviewer` (opus), 2026-09-28 16:05 to 16:09. Transcribed by the operator from the reviewer's report; the full "Noted, not carried" list is reviewer-notes.md, written by the reviewer.

## Verdict: APPROVED

## Blocking findings
None.

## Rulings on the implementers' deviations
1. **The narrower flash assert in I1: not blocking.** It is Q13's small-area exemption working as decided. `flash_area` counts every pixel over budget, and its docstring says it is 0.0 on governed output only for flashes that are not a small area (`arcade/flash.py:228-233`). One pixel of 4096 is far under `SMALL_AREA`. The governed bounds hold on the pushed frames. The reviewer re-ran the strobe check on the duel: exit 0, held 0, `concurrent_area(pushed)` 0.001, `square_flashes(pushed)` 2.
2. **The mirror under real noise: not blocking, the flash rule holds on the wall.** Pushed frames through `run_headless` with `Lobby` under `degrade(REAL_NOISE)` for 20 s, 4 single placements and 2 people, both layouts, plus the degraded duel:
   - pushed `concurrent_area` 0.085 to 0.0977 at 128x32 and at most 0.0996 at 64x64; `square_flashes` at most 5 of 6;
   - raw at 64x64 `concurrent_area` 0.13 to 0.15, which the governor holds for 2 to 5 ticks per 20 s;
   - raw `flash_area` at most 0.089, under spec 7.6's 10 percent;
   - degraded duel: raw and pushed alike, `flash_area` 0.042, `concurrent_area` 0.058, `square_flashes` 2, held 0.
3. **`FRAME_ASPECT = 4/3` against a 1280x720 camera: not blocking, nothing goes wrong.** `open_capture` asks for 640x480 and the Mac camera honours it (frames are 480x640x3), as a centre crop of the sensor, not a squash (correlation 0.974 against 0.687). Only `doctor` reports 1280x720, because `probe_camera` sets no size. `zone_x` is normalised by the calibration zone; the cursor's `v` and `raised_wrist` use y only; the cursor's `u` compares x with the shoulder width, also in x.
4. **Pong's join at launch and points by seat: not blocking.** The join matches the plan's own I1 (`humans == 2`, `cpu is None` from the first tick). Points by seat keep each score with its player when the two swap sides.

## Checks
- 596 collected (base 478), 596 passed, 0 skipped.
- Removed or changed asserts in `git diff ab40231..HEAD -- tests/`: none. The one removed line is an import in `tests/arcade/test_headless.py`, replaced by a longer one.
- Every test the plan names exists, the X1 amendment list included.
- Push path: `.save` and `.push` appear in no game, lobby or figure code. Every frame goes through `Runner._push`; `build_display` only wraps the display.
- X2's done-when: `python -m arcade run --seconds 8 --script walkup` exits 0 under the SDL dummy driver; traced with `runner.loop`: attract 26 ticks, mirror 45, invite 25, Pong at tick 96 (3.2 s). `doctor --require camera,pose` passes.
- `MediaPipeCamera` on the real camera for 6 s: it opened; `latest()` gave 60 distinct results (10 fps), each `(capture_t, (), (), None)` with age 0.011 to 0.023 s; `available` True; nobody in view; `close()` clean.

## Noted, not carried
See reviewer-notes.md. The operator carried one of them, the 64x64 mirror under noise, as C37 (Loop rule 5a: a wrong output reproduced from a source in the repository).
