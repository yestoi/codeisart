# Iteration 3 orchestrator report

Plan: `docs/superpowers/plans/2026-09-27-it03-carried-canvas-look.md`. Range: ac0a05a..e6e31f5, on main, not pushed.

## Completed

- Task 1, `Sensed` guard rails (C12, C14, C16 blobs): done, task review clean. RED was `3 failed, 17 passed`, as the plan says. Suite at that commit: 186 passed, 0 skipped.
- Task 2, actor guard rails (C13 for `degrade` and `shake`, C15, C16): done, task review clean. RED was `5 failed, 29 passed`, as the plan says. 190 passed, 0 skipped. The commit body cites owner decision Q9.
- Task 3, canvas (core Task 5): done, task review clean. RED was the planned `ModuleNotFoundError: No module named 'arcade.canvas'`. 209 passed, 0 skipped.
- Task 4, looks and `PreviewDisplay` (core Task 6): done, task review clean. RED was the planned `ModuleNotFoundError: No module named 'arcade.look'`. 224 passed, 0 skipped.
- All 11 production and test files match the plan's code blocks byte for byte. I extracted the blocks mechanically before dispatch, the implementers copied them into place, and I ran `cmp` after each task. The final reviewer extracted all 11 blocks again independently and got the same result.
- Implementers and task reviewers were sonnet, one fresh implementer per task. The final whole-branch review was opus. No fix rounds were needed.
- I ran Iteration verify steps 1-4 and 6 myself. All pass:
  1. `pytest --collect-only -q | tail -1` prints `224 tests collected`.
  2. `pytest -q -rs` prints `224 passed`, 0 skipped. Every per-module count matches the plan (table below).
  3. `git diff 83b6945 -- tests/ | grep '^-[^-]'` prints exactly the two expected lines, both in `tests/arcade/test_festival.py`: `-from arcade.sensed import MIN_CONF` and the old line-180 `assert not list(shake(0.5, 1.0)(iter(source)))[30].bodies[0].in_zone` (owner decision Q9).
  4. Importing `arcade.canvas`, `arcade.look` and `arcade.preview` loads none of cv2, mediapipe, sounddevice or pygame (`[]`).
  6. `git log --oneline -4` shows the four commit messages in order. `git status --short` shows only ` M docs/superpowers/workflow/state.md`, which I never staged.
- I did not run step 5 (the PNG snippet). The operator runs it at verify time.
- `arcade/games/__init__.py` does not exist. Nothing was pushed or deployed. The only file I wrote under `docs/superpowers/workflow/` is this report, and it is not committed.
- The final whole-branch review (opus) found no implementation deviations and nothing Critical or Important. Its verdict was "Ready to merge: Yes". It raised 4 Minor findings, all plan defects (see Deviations). I reproduced findings 1-3 myself.

### Rulings I made

1. **Implementers copied the extracted plan blocks instead of retyping them.** They copied each block into place with `cp`, then ran `cmp`. Why: the plan requires a verbatim copy, and a mechanical copy removes transcription risk. Cost if wrong: none beyond an extraction bug, which `cmp` against the brief and the reviewers would catch.
2. **I ran no fix wave for the final review's findings.** All four are plan defects, and your rules say plan defects go to the operator; only implementation bugs get fixed. Cost if wrong: `circle` at radius 0 and the `apply_gamma(..., 1.0)` aliasing ship one iteration later. No current caller hits either.
3. **I kept the SDD workspace** (`.superpowers/sdd/2026-09-27-it03-carried-canvas-look/`, git-ignored) instead of deleting it. Why: iteration 2's workspace was kept too, and it holds the briefs, reports and review packages. Cost if wrong: scratch files the operator can delete.
4. **I skipped finishing-a-development-branch's merge and push options.** Why: the work is on main by your instruction, and pushing is forbidden. Cost if wrong: none.

## Deviations

### Implementation deviations

None.

### Plan defect, Minor

**1. A NaN blob becomes an in-zone light at the frame corner.**
- Where: `arcade/sensed.py`, `Blob.__post_init__` (C16).
- `Blob.__post_init__` maps NaN and None to 0.0, the way keypoint cleaning does. But a cleaned keypoint also gets confidence 0 and so drops out. A `Blob` has no confidence field, so it stays a full light.
- Before C16, a NaN blob compared False in `_in()` and so was out of zone. Now, with any zone that touches the frame edge, it is an in-zone light at (0, 0). `Calibration.from_dict` accepts `[0, 0, 1, 1]`.
- The `headlamps` docstring says the clamped crossing lamp "is out of the zone" on the edge column. That is only true because the default zone starts at 0.2.
- Evidence (I reproduced it): `place_blob(Blob(nan, nan, 0.02, (255,255,255)), Calibration(zone=(0,0,1,1)))` returns `Blob(x=0.0, y=0.0, ..., in_zone=True)`.
- Suggested fix: forward to core Task 15. Either the blob source drops non-finite centroids, or `place_blob` sets `in_zone=False` for a blob whose raw coordinate was non-finite or outside 0..1.

**2. `circle` at radius 0, below 0.5, negative or infinite draws nothing, and `_i`'s docstring says otherwise.**
- Where: `arcade/canvas.py`, the `_disc` ring mask `d2 >= (r - 0.5)**2`, and `_i`'s docstring.
- The ring mask leaves out the centre pixel at these radii. `fill_circle` at the same radii draws the centre pixel.
- `_i`'s docstring says "an infinite (or negative) radius draws only the centre pixel". That holds only for `fill_circle`.
- Why it matters: a ripple animated up from r=0 loses its first frames.
- Evidence (I reproduced it): on a 16x16 canvas, `circle(8, 8, r)` lights 0 pixels and `fill_circle` lights 1, for r in {0, 0.25, -2, inf}.
- A related wording nit: `_i(10**400)`, a huge finite int, lands at `-(1 << 20)`, so `fill_circle(5, 5, 10**400)` draws only the centre while `1e300` fills. The docstring should say "a huge float".
- Suggested fix: in `_disc`, when drawing a ring with r under 0.5, draw the centre pixel. Add r=0 to `test_circle_is_the_one_pixel_rim_of_fill_circle` and reword the docstring.

**3. `apply_gamma(frame, 1.0)` returns the caller's own array.**
- Where: `arcade/look.py`, `apply_gamma`.
- At every other gamma it returns a new array. Loop decision 10 made the caches read-only so that a later in-place edit (a brightness limiter, spec 7.6) cannot corrupt anything. At gamma 1.0, the "card applies gamma" setting, the same edit would write into the wall frame.
- Evidence (I reproduced it): `g = apply_gamma(f, 1.0)` gives `g is f` True.
- Suggested fix: return `frame.copy()`, or document the aliasing. Forward to core Task 11 if the limiter reuses `apply_gamma`.

**4. Forwarding gap: `distance` at `sdl_scale` under 4 is only forwarded for core Task 13.**
- Core Task 18's `build_display` passes `cfg.sdl_scale` to `PreviewDisplay`, and config accepts `sdl_scale >= 1`.
- At scale 1 and 5 m, the distance look has no eye blur. Only `distance_sigma`'s docstring says so.
- Suggested fix: add to the Task 18 forwarded item that `build_display` should log a warning when `look == "distance"` and `sdl_scale < 4`.

Recommendation from the final review: add findings 1, 3 and 4 to the forwarded list (core Tasks 15, 11 and 18), next to the C14 torso-floor and GATE B items. Fix finding 2 the next time the canvas is touched.

## Test status (command + counts)

Command, from the repo root: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`

| After | Planned | Observed |
|---|---|---|
| Baseline (ac0a05a) | 183 | 183 passed, 0 skipped |
| Task 1 (6b973ad) | 186 | 186 passed, 0 skipped |
| Task 2 (c765e55) | 190 | 190 passed, 0 skipped |
| Task 3 (02ae229) | 209 | 209 passed, 0 skipped |
| Task 4 (e6e31f5) | 224 | 224 passed, 0 skipped (224 collected) |

Per-module counts at HEAD, all matching the plan:

| Module | Tests |
|---|---|
| tests/arcade/test_actors.py | 17 |
| tests/arcade/test_calibration.py | 23 |
| tests/arcade/test_canvas.py | 19 |
| tests/arcade/test_config.py | 42 |
| tests/arcade/test_doctor.py | 10 |
| tests/arcade/test_festival.py | 17 |
| tests/arcade/test_look.py | 15 |
| tests/arcade/test_mirror.py | 2 |
| tests/arcade/test_sensed.py | 20 |
| tests/test_colorlight.py | 29 |
| tests/test_config.py | 5 |
| tests/test_ddp.py | 8 |
| tests/test_display.py | 4 |
| tests/test_font.py | 7 |
| tests/test_gitignore.py | 6 |

Extra checks by the final reviewer:
- Each intermediate commit, checked out in its own scratch worktree, passes at the planned count.
- `tests/arcade` passes under `-W error`.

## Commits (sha + subject)

- 6b973ad fix(arcade): Sensed and Audio fields are keywords after t, nose raise line without a torso, blobs clamped (it02 C12, C14, C16)
- c765e55 fix(arcade): degrade and shake check the scene calibration, unique scene ids with a crowd id_base, tempo needs a positive bpm (it02 C13, C15, C16)
- 02ae229 feat(arcade): canvas drawing primitives with float coordinates, clamped colours, scaled text, blit_rgb and sprite_from_rows (core Task 5)
- e6e31f5 feat(arcade): plain, LED and metre-aware distance looks in numpy, PreviewDisplay models brightness (core Task 6)

Each commit carries the plan's exact subject and body plus the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, and stages exactly the plan's `git add` list.
