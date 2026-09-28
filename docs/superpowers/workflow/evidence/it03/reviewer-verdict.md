# Iteration 3 reviewer verdict

Range: ac0a05a..e6e31f5 (4 commits, on main). Plan: `docs/superpowers/plans/2026-09-27-it03-carried-canvas-look.md`.

## Verdict: APPROVED

## Blocking findings (file:line — what — why it blocks)

None.

## Notes (non-blocking)

### Evidence gathered

- **Verbatim match.** I extracted the 11 plan code blocks myself (plan lines 153, 438, 826, 1015, 1267, 1739, 1765, 2051, 2280, 2513, 2683) and ran `cmp` against each target. All 11 match byte for byte: `arcade/sensed.py`, `arcade/sources/actors.py`, `arcade/canvas.py`, `arcade/look.py`, `arcade/preview.py`, `tests/arcade/{conftest,test_sensed,test_actors,test_festival,test_canvas,test_look}.py`. No implementation deviation.
- **Commits.** Each commit's subject and body match the plan's `git commit -m ... -m ...` exactly. Each commit stages exactly the plan's `git add` list (`git show --stat`). All four carry the Co-Authored-By trailer. The working tree holds only the uncommitted `state.md` and `orchestrator-report.md`.
- **Test counts.** `pytest --collect-only -q | tail -1` prints `224 tests collected`. `pytest -rs -q | grep -c SKIPPED` prints `0`. Full run: `224 passed`, and `224 passed` again under `-W error`. The previous iteration ended at 183 collected, 0 skipped, so nothing was dropped or skipped. The perf test passed on 3 reruns.
- **Removed or changed test lines.** `git diff ac0a05a..HEAD -- tests/ | grep '^-[^-]'` prints exactly 2 lines, both in `tests/arcade/test_festival.py`:
  1. `-from arcade.sensed import MIN_CONF`: an import, widened to `MIN_CONF, Sensed, place`. The c765e55 body justifies it ("test_festival's import line gains Sensed and place").
  2. `-    assert not list(shake(0.5, 1.0)(iter(source)))[30].bodies[0].in_zone`: this is the only removed `assert`. It becomes `with pytest.raises(ValueError, match="calibration")`. The c765e55 body cites it: "owner decision Q9: shake raises ValueError ... so test_festival.py:180 changes ...". It is justified.
- **Carried fixes, checked in the code:**
  - C12: `Sensed` has `_: dataclasses.KW_ONLY` after `t` (sensed.py:320). `Audio` is `@dataclass(frozen=True, kw_only=True)`. A grep of `arcade/ show/ tools/ tests/` finds no positional call beyond `t`.
  - C13: `_require_placed` runs on each fresh capture in `degrade` (actors.py:429) and on each windowed frame in `shake` (actors.py:387). The test covers each single-field calibration mismatch, an unplaced body, and a second body (`match="body 2"`). I also checked that a NaN-box body places to finite `zone_x`/`zone_y`, so the exact-equality check in `_placed_by` cannot raise spuriously on NaN.
  - C14: `raise_line` uses the shoulders only when `torso > 0.0`, then a confident nose, then `None`.
  - C15: `scene` validates duplicate ids eagerly and returns `_frames(...)`. `crowd(..., id_base=100)` is in place.
  - C16: `Blob.__post_init__` clamps x and y (NaN and None become 0.0). `tempo` raises on a bpm outside (0, inf), NaN included. `_noisy` has its docstring, and `test_festival_guard_rails` pins the kept box, scale and velocity.
- **No cv2 in `look.py`.** Its only "cv2" is the docstring saying it never imports it. Importing `arcade.look`, `arcade.canvas` and `arcade.preview` loads none of cv2, mediapipe, sounddevice, pygame or picamera2 (`[]`).
- **Brightness rule holds.** `PreviewDisplay.push` renders into a new array and dims only that image (`dim(render(...))`). `render` never returns the input frame: `_nearest`, `_distance` and the `led` float product all allocate. `test_preview_models_brightness` asserts `(wall == 255).all()` after a dimmed push. `set_brightness` forwards the level unchanged, 1.5 included. This range changes nothing under `show/`. `ColorlightDisplay.push` copies the frame unscaled and applies brightness only through the 0x01/0x0A packets. DDP sends frames unscaled. SDL stores the level and shows full brightness.
- No `print` in the new or changed library code. The `perf` marker is registered in `pyproject.toml`.

### Plan defects raised by the orchestrator (all four confirmed, none blocking)

1. **Confirmed, plan defect: a NaN blob becomes an in-zone light at the corner.** `place_blob(Blob(nan, nan, 0.02, (255,255,255)), Calibration(zone=(0,0,1,1)))` gives `Blob(x=0.0, y=0.0, ..., in_zone=True)`. With the default zone (x0 = 0.2) it is `in_zone=False`, so it matters only for zones that touch the frame edge. `test_blob_coordinates_are_clamped` pins NaN to 0.0 but never places a NaN blob in an edge zone. No task in this iteration builds on it (no blob source until core Task 15). Forward it to Task 15 as the report suggests.
2. **Confirmed, plan defect: `circle` draws nothing at small radii, which contradicts `_i`'s docstring.** On 16x16, `circle(8, 8, r)` lights 0 pixels and `fill_circle` lights 1 for r in {0, 0.25, 0.49, -2, inf}. From r=0.5 upward (rounded half up to 1) it lights 8. The cause is the ring mask `d2 >= (r - 0.5)**2` (canvas.py:128). `_i`'s docstring (canvas.py:18-20) says "an infinite (or negative) radius draws only the centre pixel", which is true only of `fill_circle`. The huge-int wording nit also reproduces: `fill_circle(5, 5, 10**400)` lights 1 pixel and `1e300` lights 256. No task in this iteration builds on `circle`. Fix it the next time the canvas is touched.
3. **Confirmed, plan defect: `apply_gamma(frame, 1.0)` aliases.** It returns `frame` itself (`is` is True). At 2.2 it returns a new, writable array. No current caller writes into the result: the `led` path immediately does `.astype(np.float32)`. It is a hazard only for a later in-place brightness limiter (core Task 11). Forward it.
4. **Confirmed, plan defect: `distance` at `sdl_scale` under 4 is forwarded only for Task 13.** `_box_radii(distance_sigma(5) * s)` gives `[0,0,0]` at s=1, `[0,0,1]` at s=2, `[1,1,1]` at s=3 and `[1,1,2]` at s=4. `config.py:105` accepts `sdl_scale >= 1`. The plan's Task 18 forwarded item says nothing about it; only `distance_sigma`'s docstring does. The default `sdl_scale = 8` is fine. Add the warning to the Task 18 forwarded item.

### Additional notes (mine, minor, none blocking)

5. `PreviewDisplay` does not validate `mode`, `scale`, `gamma` or `metres` at construction. A bad value surfaces as `ValueError` from `render` on the first `push`. Core Task 18 passes `cfg.look`, which config already validates against `LOOKS`, so nothing hits this today. If Task 18 wants errors at startup, it could call `render` once on a 1x1 frame.
6. `render` and `dim` raise `TypeError` rather than `ValueError` for `gamma=None`, `metres=None` or `level=None`. The plan's validation covers numeric garbage only. No current caller passes None, and config types these fields.
7. `test_distance_keeps_up_with_the_preview` holds a hard 33 ms median. Here it runs in about 7 ms, so there is wide margin, but on the Pi 5 (GATE B) it should be re-timed rather than assumed.
