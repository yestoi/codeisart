# Iteration 3: Carried Fixes, Canvas and Look Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close iteration 2's carried fixes C12-C16 (C11 is decided for core Task 15, owner decision Q8), then build core Task 5, the canvas every game draws on, and core Task 6, the preview looks (`plain`, `led`, metre-aware `distance`) with `PreviewDisplay` modelling brightness.

**Architecture:** Tasks 1 and 2 harden `arcade/sensed.py` and `arcade/sources/actors.py`: `Sensed` and `Audio` fields become keyword-only, the raise line falls back to the nose when the torso cannot be measured, blob coordinates are clamped, `degrade` and `shake` refuse a calibration that does not reproduce the scene's placement, and scene ids are unique. The one committed assert that changes is `test_festival.py:180`, by owner decision Q9. `arcade/canvas.py` wraps the `(h, w, 3)` uint8 frame with rounding, clamping, clipping drawing primitives and scaled text in the 5x7 font. `arcade/look.py` renders a frame for a monitor in pure numpy (it never imports cv2); `distance` blurs in linear light: a luminance-weighted share of each pixel's light scatters into a wide halation glow and the rest stays in a Gaussian of 1.5 arcmin at the given distance, so light is conserved; both blurs are built from box blurs and applied as cached, read-only separable matrices. `arcade/preview.py` wraps a real display, renders each frame in a look and dims the rendered preview (never the wall frame) to the brightness level.

**Tech Stack:** Python 3.12 from uv, numpy, pytest; Pillow (a declared dependency) only in the Iteration verify snippet; the venv from iteration 1.

**Spec:** `docs/superpowers/specs/2026-09-26-wall-arcade-design.md`, revision 3 (sections 5 and 6.4 for Tasks 1 and 2; 7.4 for Task 3; 4.3 and 9.4 for Task 4).

**Sources merged here (this plan overrides them where they differ):** the roadmap's "Carried fixes" C11-C16 (`docs/superpowers/workflow/roadmap.md`); owner decisions Q8 and Q9 (`docs/superpowers/workflow/decisions.md`); the round-1 plan review (`docs/superpowers/workflow/evidence/it03/plan-review.md`: B1, B2 and notes N1-N18, applied as listed under "Plan review round 1"); core plan `docs/superpowers/plans/2026-09-26-wall-arcade-core.md` Task 5 and Task 6 with their per-task amendments (lines 466-483) and "Global Constraints, revised"; `docs/superpowers/reviews/2026-09-26-arcade-review-lenses/05-plan.md` S4. Every file below is final, amendment-applied code, given whole; an implementer needs nothing else.

## Global Constraints

Carried from the core plan ("Global Constraints" as replaced by "Global Constraints, revised"):

- Frames are numpy arrays of shape `(height, width, 3)`, dtype uint8, RGB, row-major.
- Every game declares `layouts`; its tests are parametrized over the declared layouts (spec 9.1). 128x32 is the default and design layout. (No games in this iteration; the canvas fixtures `size` cover 128x32 and 64x64.)
- Brightness: the runner calls `display.set_brightness(cfg.brightness)` once. The Colorlight backend enforces it at the panel with the card's brightness packet; the fake and SDL displays store the level, the SDL window itself shows full brightness, and `PreviewDisplay` (Task 4) models the level in the preview it renders; DDP logs once that it is Falcon Player's setting. Pixels pushed to hardware are never scaled for `brightness`. (Iteration 2 said the SDL window shows full brightness "until core Task 6's `PreviewDisplay` models it"; this is that task.)
- Tick rate 30 Hz; `dt` handed to games is clamped to 100 ms; clocks and random sources are injected.
- Never seed from `hash()` of a str; use `zlib.crc32` and print the seed in the assertion message.
- Modules that import `mediapipe`, `picamera2`, `cv2.VideoCapture` devices, or `sounddevice` do so inside the class constructor, probe function or thread, never at module import. Tests never need hardware extras.
- Tests run headless: `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy` are set in `tests/conftest.py` before pygame is imported.
- No `print` in library code; use `logging.getLogger("arcade")` in `arcade/` and `logging.getLogger(__name__)` in `show/`. CLI entry points and `tools/` may print.
- Python 3.12 through uv on the Mac; one OpenCV distribution, `opencv-contrib-python`.
- Commit after every task with the exact message and `git add` list given in the task.

Operator rules for this loop:

- Test modules are copied from this plan verbatim. Any difference, however small, is a Deviation and must be reported as one.
- Never remove or weaken an existing assert; only add or tighten. If an existing assert must change, the task and its commit message say why. (Task 2 changes one, `tests/arcade/test_festival.py:180`, by owner decision Q9; the only other changed test line is an import, also in Task 2.)
- Never push. Never run `git push` or `gh pr create`.
- Use `.venv/bin/python` (Python 3.12 from uv). Never use the system `python3` (3.14), never `pip`, never activate the venv in a way later commands depend on.
- Install with `uv pip install --python .venv/bin/python ...`. (This iteration installs nothing.)
- Run tests from the repo root with `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs` (append a path to run one module).

## Loop decisions taken by this plan (journal each one)

1. **C11 (blob id and velocity) is decided and not built here.** Owner decision Q8: `Blob` gains `id` (-1 = untracked), `vx` and `vy` when core Task 15 is planned, set by the blob source. Nothing in this iteration reads a blob's identity or speed, so `Blob`'s fields are unchanged.
2. **C12: every `Sensed` field after `t`, and every `Audio` field, is keyword-only.** `Sensed` uses a `dataclasses.KW_ONLY` sentinel after `t`; `Audio` is `@dataclass(frozen=True, kw_only=True)`. `Sensed(t, bodies)` and `Audio(0.8, 1.0)` now raise `TypeError`. Every existing call in `arcade/` and `tests/` already used keywords (the suite passes after Task 1 with no other change). The core plan's positional calls are forwarded (below).
3. **C13: `degrade` and `shake` verify the calibration (owner decision Q9 for `shake`).** Before re-placing noisy bodies, both check with `_require_placed` that `place(body, calibration)` reproduces each clean body's `in_zone`, `zone_x` and `zone_y`; if not (a scene built with another zone or `min_height`, or a body never placed), they raise `ValueError` naming the body and time instead of moving the zone silently. `degrade` checks every fresh capture, `shake` every frame in its window. That is the roadmap's "require it explicitly" without a new required parameter, so every call that passes the scene's calibration (or uses the default for a default scene) keeps working. The committed assert `tests/arcade/test_festival.py:180`, `assert not list(shake(0.5, 1.0)(iter(source)))[30].bodies[0].in_zone`, pinned `shake`'s silent fallback; by owner decision Q9 it becomes `with pytest.raises(ValueError, match="calibration"): list(shake(0.5, 1.0)(iter(source)))`. That is an owner-approved change of an expected outcome, not a tightening. The test gives one calibration per placement field (`min_height` changes only `in_zone`, a wider zone only `zone_x`, a taller one only `zone_y`) and checks both functions catch each.
4. **C14: with one shoulder and no hip, the raise line is the nose line.** `raise_line` uses the shoulders only when `torso > 0`; otherwise a confident nose; otherwise `None` (nothing is raised: fail safe). A line on the shoulder itself would have counted a wrist a hair above the shoulder as raised. `scale` stays 0.0 ("measure") in that case and `reach` keeps its box fallback (iteration 2's loop decision 4): the tracker (core Task 16) smooths scale over captures, and the reach box already works without shoulders. This refines spec 5's "the nose only when both shoulders are missing" for the degenerate case (journal as spec drift); a torso that is tiny but not zero is forwarded (below).
5. **C15: `scene` refuses duplicate ids before the first frame; `crowd(n, start=0.0, id_base=100)`.** A person without an id gets its index in `persons`, as before. `scene` now validates eagerly and returns a generator (`_frames`), so `scene(...)` raises at the call, not at the first `next()`. The default `id_base=100` keeps every existing crowd id.
6. **C16 guard rails.** `Blob.__post_init__` clamps `x` and `y` to 0..1, NaN and None to 0.0, as `Keypoint` cleaning does, so `headlamps()` (which crosses x -0.05 to 1.05) never maps off the wall; its docstring says the crossing lamp now sits on the edge column, out of the zone, for its first and last 0.27 s. `tempo` raises `ValueError` for a bpm that is not in (0, inf), so `camp_kick(0)` does too. `_noisy`'s docstring now says why `box`, `scale`, `vx` and `vy` are kept clean (the box stands for the detector's box; scale and velocity come from the tracker, which smooths them), and `test_festival_guard_rails` pins that.
7. **Canvas rounding is half up** (`math.floor(v + 0.5)`), not Python's `round`, which rounds half to even: a sprite moving 0.5 px a tick would step 0, 2, 2, 4 with `round` and 1, 2, 3, 4 here. Colours round half up and clamp to 0..255; NaN is 0 and an infinity clamps to its end. As 05-plan S4 maps NaN and infinity to `-(1 << 20)`, an infinite radius or width draws nothing while a huge finite one fills; `_i`'s docstring says so.
8. **Canvas text scale** is rounded and clamped to 1..max(width, height) (a larger glyph cannot show, and `scale=10**9` must not allocate a giant glyph); `text` and `text_width` draw `str(s)`, so a score passed as an int draws. Glyphs wholly off the left edge are skipped arithmetically (`range(max(0, -x // cell_w), len(s))`) and the loop stops at the right edge, so a 10000-character string costs only what shows.
9. **`distance` works in linear light and conserves it.** Each byte becomes the light the `led` look's gamma gives on an sRGB monitor, `(v / 255) ** (MONITOR_GAMMA / gamma)` with `MONITOR_GAMMA = 2.2`, spread over the whole pixel square (not the `led` dot; at 5 m the eye still resolves the 5 mm dot grid, so text reads slightly smoother in this preview than on the wall, as the docstring says). A share of each pixel's light, `HALATION * light * Y` with `Y` its Rec. 709 luminance, scatters into a glow blurred at `HALATION_SIGMAS = 3` times the eye's sigma; the rest stays in the eye's blur, a Gaussian of `distance_sigma(metres) * scale` preview pixels (`metres * tan(1.5 arcmin) / 0.005` wall pixels, 0.436 at 5 m). Both come from three zero-padded box blurs per axis (Kovesi's widths); the sum is clipped and re-encoded with `1 / MONITOR_GAMMA`. Because light moves rather than being added, a flat field keeps the `led` look's level at every distance, 0 m included (round 1 added the glow on top and turned mid grey 15% brighter and amber lemon; plan review B1). `HALATION = 0.3` is a starting value: `test_distance_conserves_light_and_keeps_strokes_apart` bounds it from above with spec 7.4's legibility claims (1 px strokes stay apart at 5 m, 2 px strokes at 10 m; 0.5 passes, 0.6 fails), `test_distance_halation_follows_luminance` needs it over 0, and `test_distance_blur_has_its_width_and_dark_edges` pins the eye's sigma and the glow's 3 sigma. The owner can retune it by eye from the Iteration verify PNGs anywhere in (0, 0.5] without an assert change. At scale 1 and 5 m the core boxes have radius 0 (no core blur); `distance_sigma`'s docstring says to judge distance at scale 4 or more.
10. **The blur is applied as cached, read-only separable matrices.** Box blurs are linear and separable, so the nearest-neighbour upscale plus three boxes along each axis is one `(n * scale, n)` matrix per axis, built once per (size, scale, sigma) with the same `_box` and applied with two matrix products. The result equals blurring the upscaled image directly to within one byte (checked on four frame sizes, each at five scale and distance pairs; the round-1 review confirmed it over 5 sizes, 5 patterns, 4 scales, 8 distances and both gammas), and `PreviewDisplay.push` in `distance` costs about 7 ms per 128x32 frame at scale 8 instead of 76 ms, so `look = "distance"` fits a 30 Hz tick (`test_distance_keeps_up_with_the_preview`, marked `perf`, times the push at brightness 0.4). A box wider than the line takes the whole line's mean without padding, and sigma is capped at 1e6 pixels, so an absurd distance neither overflows nor allocates giant pads. Every cached array (`gamma_lut`, `_led_kernel`, `_light_lut`, `_spread`) is read-only, so an in-place edit by a later caller (a brightness limiter, spec 7.6) raises instead of corrupting every later preview.
11. **Preview brightness.** `PreviewDisplay.set_brightness(level)` stores the level and forwards it unchanged to the inner display; `push` renders the look and then multiplies the preview's bytes by `level ** (1 / MONITOR_GAMMA)`, so the monitor shows `level` of the light whatever `gamma` the look used (at 0.25 a white preview byte is 136). NaN or a level not over 0 gives black, above 1 gives full, and the level starts at 1.0. The wall frame handed to `push` is never modified. This models a brightness packet that scales light linearly, which GATE B must confirm (forwarded).
12. **`blit_rgb` converts a sprite that is not uint8** (plan review B2): `nan_to_num` (NaN to 0, infinities to 0 or 255), round half up, clip to 0..255, then judge black as transparent. Paint's float32 trail (core Task 10) is such a sprite; round 1 let numpy wrap 300 to 44 and -5 to 251.
13. **`render` takes any integer scale** through `operator.index`, so a numpy integer (core Task 13 computes a scale to fit 1,536 px) works; a float, a bool or anything under 1 raises `ValueError`.

## Owner questions

None open. Q8 (C11: `Blob.id`, `vx`, `vy` at core Task 15) and Q9 (`shake` raises; `test_festival.py:180` changes) are answered in `docs/superpowers/workflow/decisions.md` and applied in loop decisions 1 and 3.

## Plan review round 1 (`evidence/it03/plan-review.md`): what changed

- **B1** (distance adds light): fixed as the review specifies (loop decision 9); the review's `test_distance_conserves_light_and_keeps_strokes_apart` is added, split onto separate lines.
- **B2** (`blit_rgb` wraps): fixed as the review specifies (loop decision 12); `test_colours_clamped` gains the float32 and int64 cases under `warnings.simplefilter("error")`.
- **N1**: `deadline(seconds)` (SIGALRM through `setitimer`) wraps the 26 hostile calls and the float-endpoint line, so an S4-style infinite loop fails in 1 s instead of hanging (the start-point-only `_i` mutation now fails); off-left glyphs are skipped arithmetically.
- **N2**: `test_led_honours_gamma_and_cached_tables_are_read_only` checks `led` at gamma 2.2. **N3**: `test_distance_blur_has_its_width_and_dark_edges` measures the realised variance of one white pixel with the glow off (the eye's sigma) and with all of white's light scattered (3 sigma), at 5 and 10 m, and a white frame's dark edges; `distance_sigma`'s docstring notes the scale-1 limit. **N4**: covered by B1's test. **N5**: the calibration cases above, for `degrade` and `shake`. **N6**: `test_blit_takes_any_mask_as_bool`. **N7**: `test_line_skip_starts_past_four_times_the_extent`. **N8**: read-only caches (loop decision 10). **N9**: loop decision 13. **N10**: `_i`'s docstring. **N11**: journal note in loop decision 4; torso floor forwarded. **N12**: `headlamps` docstring. **N13**: `render`'s docstring. **N14**: the snippet draws "CODE IS" / "ART" on two lines at 64x64 and keeps the diagonal clear of the sha. **N15** and **N16**: the perf test times `PreviewDisplay.push` at brightness 0.4 and prints its seed. **N17** and **N18**: forwarded (below).
- **Round 2 (APPROVED; notes applied).** R2-N1: six asserts added to plan-owned tests, none to the six verbatim core tests, so the counts are unchanged: `fill_circle(5, 5, 1e200)` joins the hostile list (without `_i`'s clamp it raised `OverflowError`); `rect` at width 0 or -3 and `fill_rect` of infinite width draw nothing (end of `test_nan_inf_and_huge_never_raise_or_hang`); `text(-1, 0, "B")` keeps B's four visible columns (`test_float_coordinates_round`); `blit_rgb` of 0.5, 126.5, 2.5 gives (1, 127, 3) (`test_colours_clamped`); `set_brightness(1.5)` reaches the inner display as 1.5 (`test_preview_models_brightness`); a two-person scene whose second body only the scene's zone places raises `match="body 2"` in `degrade` and `shake` (`test_degrade_needs_the_scene_calibration`). R2-N2: `_i`'s docstring now says an infinite width draws nothing and an infinite or negative radius draws only the centre pixel. R2-N3: `deadline` just runs the block off the main thread or without `setitimer`, and its docstring says it replaces any outer SIGALRM timer. R2-N5: the perf test is unchanged.
- **Also from the review's survivor list:** `test_circle_is_the_one_pixel_rim_of_fill_circle` pins ring thickness (the core test only bounds it).
- **Declined:** a lower bound on `HALATION` (its x1/6 mutation survives). The spec gives no minimum glow, so any bound would be a number of mine that the owner would have to own; the glow's presence (`blue > 0`), luminance weighting, width and upper bound are pinned. Three survivors are truly equivalent (`text` without its y cull, `text` without its off-left skip, whose `continue` still culls, and `_spread` without `lru_cache`): they change nothing a test can observe short of timing, so no test is added for them.

## Forwarded to later amendments

- **C12 positional calls in the core plan.** Task 8 `sense()` (core plan line 2884), Task 12 `decode` (lines 3659 and 3661), Task 14 (line 4157) and Task 18 `record` (line 5267) build `Sensed` or `Audio` positionally in revision 2's field order; with Task 1 they raise `TypeError`. Their amendments must use keywords. Task 12's `decode` (the roadmap corrects iteration 2's note, which said Task 7) must also build the empty `(0, 0)` motion grid and call `place()` on every body, because `in_zone` defaults to True, and must pass the recording's calibration to anything that re-places (`degrade` and `shake` now raise otherwise).
- **C10** is unchanged: cursor grace or hysteresis and a per-capture exit grace, for core Tasks 8 and 9.
- **C11** (owner decision Q8): core Task 15 adds `Blob.id` (-1 = untracked), `vx`, `vy`, set by the blob source; core Tasks 9 and 10 consume them.
- **C14 torso floor** (review N11): `torso > 0.0` catches only an exact zero. Side-on shoulders 0.02 apart with no hips give a torso of 0.025 and a raise line 0.008 above the shoulders, which spec 2's bar layout (hips hidden by the counter) makes likely. Core Task 8 or 16: use the nose line when the torso is under a floor (for example 0.1 of the box height), with a test. Journal the spec 5 wording ("the nose only when both shoulders are missing") as spec drift for the next revision.
- **Core Task 13** (`tools/arcade_shot.py`): render `-distance.png` with `render(frame, "distance", scale, gamma, metres=5.0)` at scale 4 or more (loop decision 9); save PNGs from `tools/` only (core Task 20's privacy test forbids `.save` in `arcade/`); the Iteration verify snippet below shows the PNG text chunk for the git sha.
- **Core Task 16** (tracker): smooth `scale` over captures, since loop decision 4 leaves `scale = 0.0` when one shoulder and no hip are seen.
- **Core Task 18** (`build_display`): keep the inner `SDLDisplay(cfg.width * cfg.sdl_scale, cfg.height * cfg.sdl_scale, 1)` and `PreviewDisplay(inner, cfg.look, cfg.sdl_scale, cfg.gamma)`; `metres` defaults to 5.0 (spec 9.4's legibility distance), and the runner's `set_brightness(cfg.brightness)` now dims the preview.
- **GATE B firmware check** (review N18): confirm the Colorlight brightness packet scales light linearly, next to C4's `rgb` pattern; `dim` assumes it.
- **Operator** (review N17): when this iteration closes C12-C16, copy the items above into the roadmap's carried fixes, so they outlive this plan.

## Resolved conflicts (the arcade amendments win)

- **Core Task 5 interface.** "All coordinates are integer wall pixels" becomes the amendment's line: "Coordinates may be int or float and are rounded; colours are clamped to 0..255." `text(x, y, s, color, scale=1)` and `text_width(s, scale=1)` replace the scale-less forms.
- **05-plan S4's `_i` and `_c`.** S4 uses `int(round(v))` and `int(v)`. `round` is banker's rounding (loop decision 7) and `int(v)` truncates 127.6 to 127 and raises on NaN; here both round half up, and `_c` maps NaN to 0 and an infinity to 0 or 255. S4's catch list for `_i` (`ValueError`, `OverflowError`, `TypeError` to `-(1 << 20)`) is kept.
- **Core Task 5 test file.** The six core items (`test_new_canvas_is_black_and_sized` twice through `size`, `test_pixel_and_clipping`, `test_rects_and_clear`, `test_line_and_circles`, `test_text_uses_font_and_clips`) are verbatim; the import line grows to `from arcade.canvas import Canvas, sprite_from_rows`. Step 4's count is 19, not the amendment's 13: the amendment's seven tests, `test_other_wall_sizes_draw_and_clip` over three sizes (core Review Focus 3), and three from the plan review (ring, mask cast, line-skip threshold).
- **Core Task 6 `look.py`.** Revision 2 imported cv2 and blurred gamma-encoded bytes with a box of `scale // 2`; the amendment's `distance` (loop decisions 9 and 10) replaces it, and `render` gains `metres=5.0`. The six core tests are verbatim except `test_distance_blurs`, which passes `metres=5.0` as the amendment says; its thresholds are unchanged and pass. The import lines become `import arcade.look as look` and `from arcade.look import MODES, apply_gamma, distance_sigma, gamma_lut, render`. Step 4's count is 15, not 6.
- **`PreviewDisplay(inner, mode, scale, gamma)`** gains `metres: float = 5.0`, so core Task 18's four-argument call is unchanged.
- **Roadmap C13** says "carry the calibration on the scene or require it explicitly"; loop decision 3 requires it by verification in `degrade` and `shake`.

## Additions beyond the source plans (reviewer: check these on purpose)

- Sensed: docstrings on `Blob`, `Audio` and `Sensed` saying why their fields are what they are; `Blob.__post_init__` (loop decision 6).
- Actors: `_frames` (the generator `scene` returns after validating), `_placed_by(body, calibration)` and `_require_placed(bodies, calibration, who, t)`; `tempo` validation (so `camp_kick` validates); `crowd`'s `id_base`; the `headlamps` docstring; three new festival tests and one new actors test.
- Canvas: `sprite_from_rows` is a module function and also `Canvas.sprite_from_rows` (spec 7.4 lists it among the canvas's methods); `blit` casts its mask to bool; `blit_rgb` converts non-uint8 sprites; `text` draws `str(s)`, clamps `scale` and skips off-left glyphs arithmetically; `test_other_wall_sizes_draw_and_clip`, `test_circle_is_the_one_pixel_rim_of_fill_circle`, `test_blit_takes_any_mask_as_bool`, `test_line_skip_starts_past_four_times_the_extent` and the test helper `deadline`; `tests/arcade/conftest.py` is core Task 5's, verbatim.
- Look: constants `MONITOR_GAMMA`, `PITCH_M`, `BLUR_ARCMIN`, `HALATION_SIGMAS`, `HALATION`, `LUMA`; `distance_sigma(metres)`; `dim(image, level)`; `_frozen`; `render` validates mode, frame (`(h, w, 3)` uint8), scale (any integer of at least 1, not a bool), gamma (over 0, finite) and metres (0 or more, finite) with `ValueError`; `test_distance_halation_follows_luminance`, `test_render_rejects_bad_input` (with `MODES == arcade.config.LOOKS`), `test_distance_conserves_light_and_keeps_strokes_apart`, `test_distance_blur_has_its_width_and_dark_edges`, `test_led_honours_gamma_and_cached_tables_are_read_only` and the `perf`-marked `test_distance_keeps_up_with_the_preview`.
- Preview: `PreviewDisplay.level` and the `metres` keyword.

## Review Focus

1. A game keeps float positions and colours (pong's ball at x 63.5, a colour computed as 300 or NaN, Paint's float32 trail blitted with `blit_rgb`). The canvas must round, clamp and clip and never raise, wrap or hang. Test: Task 3, `test_float_coordinates_round`, `test_nan_inf_and_huge_never_raise_or_hang` (each of 26 hostile calls within 50 ms, under a 1 s `deadline`; empty and infinite-width rects draw nothing), `test_colours_clamped` (float32 and int64 sprites, half up at 0.5 and 126.5), `test_line_with_float_endpoint_terminates`.
2. A wall that is not 128x32: one 64x32 panel at bring-up, or another size from config. Drawing, text and clipping must work at any size. Test: Task 3, `test_other_wall_sizes_draw_and_clip` (64x32, 96x48, 128x64) plus the `size` fixture (128x32, 64x64); Task 4's look tests run on frames from 8x4 to 128x32.
3. The owner judging the wall from a `distance` render: colours and levels must be the wall's, and strokes that the spec says read at 5 or 10 m must stay apart. Test: Task 4, `test_distance_conserves_light_and_keeps_strokes_apart`, `test_distance_blur_has_its_width_and_dark_edges`.
4. A night level or a computed brightness that is NaN, 0, negative or above 1 reaching the preview, and an SDL run with `look = "distance"` rendering every tick. The preview must go dark on NaN and non-positive, full above 1, never emit a cast warning, never touch the wall frame, and fit a 30 Hz tick. Test: Task 4, `test_preview_models_brightness`, `test_distance_keeps_up_with_the_preview`.
5. A producer written from the revision-2 core plan passing `Sensed(t, bodies, ...)` positionally, which used to put the bodies in `camera_t` silently; or a scene with a custom zone run through `degrade` or `shake` without its calibration. Both must raise. Test: Task 1, `test_sensed_and_audio_take_keywords_after_t`; Task 2, `test_degrade_needs_the_scene_calibration`, `test_shake_places_against_the_scene_calibration`.

## Environment facts verified 2026-09-27

- HEAD is `83b6945`; only `docs/superpowers/workflow/` files changed since `0fc31ca`. The suite is 183 collected, 183 passed, 0 skipped. `.venv` is Python 3.12.13 with numpy 2.5.3, pygame 2.6.1, pytest 9.1.1, Pillow 12.3.0 (`Pillow>=10,<13` is a declared dependency in `pyproject.toml`). `arcade/canvas.py`, `arcade/look.py`, `arcade/preview.py` and `tests/arcade/conftest.py` do not exist.
- `show/font.py`: `CELL_W = 6`, `CELL_H = 8`, `Font.load(path)`, `Font.atlas()` is `(256, 8, 6)` bool. `arcade/config.py`: `LOOKS = ("plain", "led", "distance")`. `show/display/fake.py`'s `FakeDisplay` keeps `last`, `count`, `brightness` (starts 1.0) and `closed`.
- `dataclasses.KW_ONLY` works under `from __future__ import annotations` in `arcade/sensed.py`, and `kw_only=True` on a frozen dataclass: positional calls raise `TypeError`, `dataclasses.fields()` reports `kw_only`.
- Casting a NaN float array to uint8 gives 0 with a `RuntimeWarning` on this Mac, so a NaN that reached a cast would look dark; the brightness and colour tests turn warnings into errors so they catch that path. The whole suite passes under `-W error`.
- `signal.setitimer(signal.ITIMER_REAL, s)` with a SIGALRM handler interrupts a pure-Python loop in pytest's main thread on macOS.
- With the conserving glow, a flat field in `distance` equals `gamma_lut(2.2)` of its colour within one byte at 0, 5 and 10 m; the realised variance of one white pixel is 0.96 to 1.00 of `sigma**2 + (scale**2 - 1) / 12` for the eye's sigma and for 3 sigma, at 5 and 10 m.
- The distance blur as cached matrices matches the direct box blur of the upscaled image to within one byte over frames 1x1, 4x8, 32x128 and 64x64 at scales 1 to 8 and 0 to 300 m.
- The editable install's finder comes after `PathFinder`, so in a clone with the venv symlinked the clone's own `arcade/` is imported.
- The whole plan's code was replayed from this file's text in a fresh clone of `83b6945`, task by task (tests first, then code, then the commit): every failure and count below was observed.
- Mutations, run with `PYTHONDONTWRITEBYTECODE=1` (a file restored within the same second at the same size once left a stale `.pyc`): 68 hand-made mutations of this plan's code, each run against its task's tests: 64 fail. They are 41 of mine (Tasks 1 to 4), the round-1 review's 18 survivors plus the S4 start-point-only `_i`, five for round 2's fixes (the round-1 additive glow, `blit_rgb` without its conversion or with truncation, writable caches, numpy scales rejected) and the round-2 review's three new survivors (off-left skip as `-(x // cell_w)`, `_require_placed` checking the first body only, `blit_rgb` rounding half to even). The start-point-only `_i` hung the suite before `deadline`; it now fails in about 1 s. Four survive: `HALATION = 0.05` (declined above: no lower bound is specified), and three that change nothing observable short of speed (no `lru_cache` on `_spread`; `text` without its y cull or its off-left skip).

## File map

```
arcade/sensed.py                Task 1  C12 keyword-only fields, C14 nose raise line, C16 blob clamp
tests/arcade/test_sensed.py     Task 1  three tests added
arcade/sources/actors.py        Task 2  C13 placement check in degrade and shake, C15 unique ids and crowd id_base, C16 tempo check, docstrings
tests/arcade/test_actors.py     Task 2  one test added
tests/arcade/test_festival.py   Task 2  three tests added; line 180 changed (owner decision Q9); import line gains Sensed and place
tests/arcade/conftest.py        Task 3  new (core Task 5's): font5x7 and size fixtures
arcade/canvas.py                Task 3  new: Canvas, sprite_from_rows
tests/arcade/test_canvas.py     Task 3  new
arcade/look.py                  Task 4  new: gamma_lut, apply_gamma, distance_sigma, render, dim
arcade/preview.py               Task 4  new: PreviewDisplay
tests/arcade/test_look.py       Task 4  new
```

---

### Task 1: Sensed guard rails (carried C12, C14, C16 blobs)

**Files:**
- Modify: `arcade/sensed.py` (whole file below)
- Test: `tests/arcade/test_sensed.py` (whole file below)

**Interfaces:**
- Consumes: iteration 2's `arcade/sensed.py` (`Keypoint`, `Body`, `Blob`, `Audio`, `Sensed`, `place`, `place_blob`, `MIN_CONF`, `_clamp01`).
- Produces: `Sensed(t, *, camera_t=..., ...)`: every field after `t` is keyword-only; `Audio(*, level=..., ...)`: every field keyword-only; `Body.raise_line` is the nose's y when `torso == 0.0` (one shoulder, no hip) and the nose is confident, else `None`; `Blob(x, y, size, color, in_zone=True)` stores `x` and `y` clamped to 0..1 with NaN and None as 0.0. No name or signature is removed.

Changes to existing test lines: `tests/arcade/test_sensed.py` gains `import dataclasses` as its first line and three tests at the end. No existing line is changed or removed.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_sensed.py`:

```python
import dataclasses
import math

import numpy as np
import pytest

from arcade.calibration import Calibration
from arcade.sensed import (LEFT_ANKLE, LEFT_EAR, LEFT_ELBOW, LEFT_EYE, LEFT_HIP, LEFT_KNEE,
                           LEFT_SHOULDER, LEFT_WRIST, NOSE, RIGHT_ANKLE, RIGHT_EAR, RIGHT_ELBOW,
                           RIGHT_EYE, RIGHT_HIP, RIGHT_KNEE, RIGHT_SHOULDER, RIGHT_WRIST, SKELETON,
                           Audio, Blob, Body, Keypoint, Sensed, place, place_blob)


def kps(**over):
    pts = [Keypoint(0.5, 0.2 + i * 0.04) for i in range(17)]
    for idx, kp in over.items():
        pts[int(idx)] = kp
    return tuple(pts)


# A standing figure: shoulders at y 0.4, 0.2 apart; hips at y 0.7, so the torso is 0.3 and the raise
# line is at 0.4 - 0.3 * 0.3 = 0.31. The nose (0.22) is above it, the wrists hang at hip height.
FIGURE = {
    NOSE: Keypoint(0.5, 0.22), LEFT_EYE: Keypoint(0.48, 0.2), RIGHT_EYE: Keypoint(0.52, 0.2),
    LEFT_EAR: Keypoint(0.46, 0.21), RIGHT_EAR: Keypoint(0.54, 0.21),
    LEFT_SHOULDER: Keypoint(0.4, 0.4), RIGHT_SHOULDER: Keypoint(0.6, 0.4),
    LEFT_ELBOW: Keypoint(0.37, 0.55), RIGHT_ELBOW: Keypoint(0.63, 0.55),
    LEFT_WRIST: Keypoint(0.35, 0.7), RIGHT_WRIST: Keypoint(0.65, 0.7),
    LEFT_HIP: Keypoint(0.45, 0.7), RIGHT_HIP: Keypoint(0.55, 0.7),
    LEFT_KNEE: Keypoint(0.45, 0.85), RIGHT_KNEE: Keypoint(0.55, 0.85),
    LEFT_ANKLE: Keypoint(0.45, 0.95), RIGHT_ANKLE: Keypoint(0.55, 0.95),
}
BOX = (0.3, 0.2, 0.7, 1.0)


def figure(over=None, box=BOX, **fields):
    pts = dict(FIGURE)
    pts.update(over or {})
    return Body(1, box, tuple(pts[i] for i in range(17)), **fields)


def test_body_requires_17_keypoints():
    with pytest.raises(ValueError):
        Body(1, (0, 0, 1, 1), tuple(Keypoint(0, 0) for _ in range(5)))


def test_body_cleans_bad_keypoints():
    pts = kps(**{str(LEFT_WRIST): Keypoint(1.7, -0.2, 0.9), str(RIGHT_WRIST): Keypoint(math.nan, 0.5, 0.9)})
    b = Body(1, (0, 0, 1, 1), pts)
    assert b.left_wrist == Keypoint(1.0, 0.0, 0.0)
    assert b.right_wrist.conf == 0.0 and b.right_wrist.x == 0.0


def test_clean_clamps_confidence_and_rejects_non_finite():
    pts = kps(**{str(NOSE): Keypoint(0.5, 0.2, 5.0), str(LEFT_EYE): Keypoint(0.5, 0.2, -1.0),
                 str(RIGHT_EYE): Keypoint(0.5, 0.2, math.nan), str(LEFT_EAR): Keypoint(math.inf, 0.2, 0.9),
                 str(RIGHT_EAR): Keypoint(0.5, -math.inf, 0.9)})
    b = Body(1, (0, 0, 1, 1), pts)
    assert b.keypoints[NOSE] == Keypoint(0.5, 0.2, 1.0)
    assert b.keypoints[LEFT_EYE] == Keypoint(0.5, 0.2, 0.0)
    assert b.keypoints[RIGHT_EYE] == Keypoint(0.0, 0.0, 0.0)
    assert b.keypoints[LEFT_EAR] == Keypoint(1.0, 0.2, 0.0)
    assert b.keypoints[RIGHT_EAR] == Keypoint(0.5, 0.0, 0.0)


def test_body_defaults_and_measured_scale():
    b = figure()
    assert (b.vx, b.vy, b.in_zone, b.zone_x, b.zone_y, b.seen_ago) == (0.0, 0.0, True, 0.5, 0.5, 0.0)
    assert b.scale == pytest.approx(0.48)            # nose to mid-hip
    assert figure(scale=0.7).scale == 0.7            # a given scale is kept
    assert b.shoulder_mid == Keypoint(0.5, 0.4) and b.hip_mid == Keypoint(0.5, 0.7)
    assert b.shoulder_width == pytest.approx(0.2) and b.torso == pytest.approx(0.3)
    assert b.center == (0.5, 0.6) and b.height == pytest.approx(0.8)
    assert b.nose == b.keypoints[NOSE] and b.confidence == 1.0
    assert Body(1, (0, 0, 1, 1), kps()).scale == pytest.approx(0.46)


def test_raise_line_is_above_shoulders():
    b = figure()
    assert b.raise_line == pytest.approx(0.31)
    assert b.raised_wrist is None and not b.both_hands_up
    low = 0.4 - 0.1 * 0.3                             # 0.1 torso above the shoulders: not raised
    assert figure({RIGHT_WRIST: Keypoint(0.65, low)}).raised_wrist is None
    high = 0.4 - 0.4 * 0.3                            # 0.4 torso above: raised
    up = figure({RIGHT_WRIST: Keypoint(0.65, high)})
    assert up.raised_wrist == Keypoint(0.65, high) and not up.both_hands_up
    assert figure({RIGHT_WRIST: Keypoint(0.65, 0.3)}).raised_wrist is not None   # below the nose, still raised
    both = figure({LEFT_WRIST: Keypoint(0.35, 0.1), RIGHT_WRIST: Keypoint(0.65, high)})
    assert both.both_hands_up and both.raised_wrist == Keypoint(0.35, 0.1)      # the higher one
    faint = figure({RIGHT_WRIST: Keypoint(0.65, 0.1, 0.1)})
    assert faint.raised_wrist is None


def test_nose_fallback_only_without_shoulders():
    hidden = {LEFT_SHOULDER: Keypoint(0.4, 0.4, 0.0), RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0)}
    b = figure(hidden)
    assert b.shoulder_mid is None and b.raise_line == pytest.approx(0.22)
    assert figure({**hidden, RIGHT_WRIST: Keypoint(0.65, 0.25)}).raised_wrist is None
    assert figure({**hidden, RIGHT_WRIST: Keypoint(0.65, 0.18)}).raised_wrist is not None
    one = figure({RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0)})    # one shoulder still sets the line
    assert one.shoulder_mid == Keypoint(0.5, 0.4)                 # its y; x from the hips
    assert one.raise_line == pytest.approx(0.31)
    no_hips = {RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0), LEFT_HIP: Keypoint(0.45, 0.7, 0.0),
               RIGHT_HIP: Keypoint(0.55, 0.7, 0.0)}
    assert figure(no_hips).shoulder_mid == Keypoint(0.5, 0.4)    # x from the nose
    alone = {**no_hips, NOSE: Keypoint(0.5, 0.22, 0.0)}
    assert figure(alone).shoulder_mid == Keypoint(0.4, 0.4)      # nothing else: the shoulder itself
    one_hip = {RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0), RIGHT_HIP: Keypoint(0.55, 0.7, 0.0)}
    assert figure(one_hip).shoulder_mid == Keypoint(0.5, 0.4)    # one hip is off centre too: the nose


def test_one_shoulder_does_not_move_the_centre():
    # Shoulders 0.24 apart for the 0.3 torso: the 1.25 ratio TORSO_PER_SHOULDER_WIDTH assumes, as actors use.
    up = {LEFT_SHOULDER: Keypoint(0.38, 0.4), RIGHT_WRIST: Keypoint(0.7, 0.1)}
    seen = figure({**up, RIGHT_SHOULDER: Keypoint(0.62, 0.4, 0.31)})
    lost = figure({**up, RIGHT_SHOULDER: Keypoint(0.62, 0.4, 0.29)})    # crosses MIN_CONF
    assert abs(seen.anchor.x - lost.anchor.x) < 0.03
    assert abs(seen.cursor[0] - lost.cursor[0]) < 0.03
    assert abs(seen.cursor[1] - lost.cursor[1]) < 0.03
    cal = Calibration()
    assert abs(place(seen, cal).zone_x - place(lost, cal).zone_x) < 0.03


def test_hooded_body_still_raises():
    hood = {NOSE: Keypoint(0.5, 0.22, 0.0), LEFT_EYE: Keypoint(0.48, 0.2, 0.0),
            RIGHT_EYE: Keypoint(0.52, 0.2, 0.0)}
    b = figure({**hood, RIGHT_WRIST: Keypoint(0.65, 0.2)})
    assert b.raise_line == pytest.approx(0.31)
    assert b.raised_wrist == Keypoint(0.65, 0.2)
    assert b.scale == pytest.approx(0.3 * 1.5)        # no nose: 1.5 torso lengths


def test_body_with_nothing_confident_never_raises_or_fails():
    blank = Body(1, BOX, tuple(Keypoint(0.5, 0.5, 0.0) for _ in range(17)))
    assert blank.raise_line is None and blank.raised_wrist is None and not blank.both_hands_up
    assert blank.cursor is None and blank.anchor is None and blank.scale == 0.0
    assert blank.reach(Keypoint(0.5, 0.6)) == pytest.approx((0.5, 0.5))
    placed = place(blank, Calibration())
    assert placed.in_zone and (placed.zone_x, placed.zone_y) == pytest.approx((0.5, 2 / 3))


def test_sensed_defaults():
    s = Sensed(t=1.0)
    assert s.bodies == () and s.blobs == () and s.audio == Audio()
    assert s.motion.shape == (0, 0) and s.motion.dtype == bool
    grid = np.zeros((4, 8), bool)
    held = Sensed(0.0, motion=grid)
    with pytest.raises(ValueError, match="read-only"):
        held.motion[0, 0] = True                     # one grid is shared by the ticks that hold it
    assert not held.with_motion((4, 2)).motion.flags.writeable
    assert grid.flags.writeable                      # the record holds a read-only view, not the caller's array
    assert Sensed(0.0, motion=None).motion.shape == (0, 0)
    assert (s.camera_t, s.camera_fresh, s.camera_seq) == (0.0, False, 0)
    assert s.player is None and s.player2 is None and not s.present
    assert not hasattr(s, "primary")
    a = Audio()
    assert (a.level, a.level_smooth, a.peak, a.voice, a.voice_db, a.floor_db) == (0, 0, 0, 0, -90.0, -90.0)
    assert not (a.clap or a.onset or a.beat) and a.bpm is None


def test_with_motion_resamples_never_rasterizes():
    b = figure()
    s = Sensed(0.0, bodies=(b,)).with_motion((8, 4))
    assert s.motion.shape == (4, 8) and s.motion.dtype == bool and not s.motion.any()
    given = np.ones((4, 8), bool)
    held = Sensed(0.0, motion=given)
    assert held.with_motion((8, 4)) is held and np.shares_memory(held.motion, given)
    small = np.array([[True, False], [False, True]])
    up = Sensed(0.0, motion=small).with_motion((8, 4)).motion
    assert up.shape == (4, 8)
    assert up[:2, :4].all() and up[2:, 4:].all() and not up[:2, 4:].any() and not up[2:, :4].any()
    grid = np.zeros((64, 128), bool)
    grid[33, 101] = True
    down = Sensed(0.0, motion=grid).with_motion((64, 32)).motion
    assert down.shape == (32, 64) and down.sum() == 1 and down[16, 50]    # one lit cell survives shrinking


def test_reach_box_corners():
    b = figure()     # shoulder mid (0.5, 0.4), shoulders 0.2 apart, torso 0.3, hips at 0.7
    top = 0.4 - 1.05 * 0.3
    assert b.reach(Keypoint(0.2, top)) == pytest.approx((0.0, 0.0))
    assert b.reach(Keypoint(0.8, 0.7)) == pytest.approx((1.0, 1.0))
    assert b.reach(Keypoint(0.5, (top + 0.7) / 2)) == pytest.approx((0.5, 0.5))
    assert b.reach(Keypoint(0.0, 1.0)) == (0.0, 1.0)                        # clamped
    half = {i: Keypoint(0.5 + (k.x - 0.5) / 2, 0.5 + (k.y - 0.5) / 2) for i, k in FIGURE.items()}
    small = figure(half, box=(0.4, 0.35, 0.6, 0.75))
    wrist = Keypoint(0.7, 0.3)
    assert small.reach(Keypoint(0.5 + (wrist.x - 0.5) / 2, 0.5 + (wrist.y - 0.5) / 2)) == pytest.approx(b.reach(wrist))
    no_shoulders = figure({LEFT_SHOULDER: Keypoint(0.4, 0.4, 0.0), RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0)})
    assert no_shoulders.reach(Keypoint(0.5, 0.6)) == pytest.approx((0.5, 0.5))   # the body box


def test_cursor_is_wrist_further_from_hip():
    right = figure({RIGHT_WRIST: Keypoint(0.8, 0.3), LEFT_WRIST: Keypoint(0.4, 0.65)})
    assert right.cursor == right.reach(right.right_wrist)
    assert right.cursor == pytest.approx((1.0, (0.3 - 0.085) / 0.615))
    left = figure({LEFT_WRIST: Keypoint(0.25, 0.2), RIGHT_WRIST: Keypoint(0.6, 0.72)})
    assert left.cursor == left.reach(left.left_wrist)
    only = figure({RIGHT_WRIST: Keypoint(0.8, 0.3, 0.0), LEFT_WRIST: Keypoint(0.4, 0.65)})
    assert only.cursor == only.reach(only.left_wrist)
    none = figure({RIGHT_WRIST: Keypoint(0.8, 0.3, 0.0), LEFT_WRIST: Keypoint(0.4, 0.65, 0.1)})
    assert none.cursor is None


def test_anchor_order():
    assert figure().anchor == Keypoint(0.5, 0.4)
    hidden = {LEFT_SHOULDER: Keypoint(0.4, 0.4, 0.0), RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0)}
    assert figure(hidden).anchor == Keypoint(0.5, 0.22)
    assert figure({**hidden, NOSE: Keypoint(0.5, 0.22, 0.0)}).anchor == Keypoint(0.5, 0.7)


def test_place_uses_calibration_zone():
    b = figure()
    placed = place(b, Calibration())                  # zone (0.2, 0.2, 0.8, 0.8), min_height 0.45
    assert placed.in_zone
    assert (placed.zone_x, placed.zone_y) == pytest.approx((0.5, (0.4 - 0.2) / 0.6))
    assert placed.keypoints == b.keypoints and placed.scale == b.scale and b.zone_y == 0.5
    right = place(b, Calibration(zone=(0.6, 0.0, 1.0, 1.0)))
    assert not right.in_zone and right.zone_x == 0.0                       # clamped to the zone edge
    short = place(figure(box=(0.3, 0.2, 0.7, 0.6)), Calibration())         # 0.4 tall, under min_height
    assert not short.in_zone
    tall_enough = place(figure(box=(0.3, 0.2, 0.7, 0.65)), Calibration())
    assert tall_enough.in_zone


def test_place_blob():
    assert place_blob(Blob(0.5, 0.5, 0.03, (255, 255, 255)), Calibration()).in_zone
    assert not place_blob(Blob(0.05, 0.1, 0.03, (255, 255, 255)), Calibration()).in_zone
    assert Blob(0.1, 0.2, 0.05, (255, 0, 0)).in_zone


def test_skeleton_indices_valid():
    assert all(0 <= a < 17 and 0 <= b < 17 for a, b in SKELETON)
    assert Blob(0.1, 0.2, 0.05, (255, 0, 0)).color == (255, 0, 0)


def test_sensed_and_audio_take_keywords_after_t():
    # C12: revision 2 called Sensed(t, bodies, blobs, motion, audio); in spec 5's field order that binds
    # the bodies to camera_t without an error. Audio(0.8, 1.0) would put 1.0 in level_smooth.
    with pytest.raises(TypeError):
        Sensed(1.0, (figure(),))
    with pytest.raises(TypeError):
        Audio(0.8, 1.0)
    assert [f.name for f in dataclasses.fields(Sensed) if not f.kw_only] == ["t"]
    assert all(f.kw_only for f in dataclasses.fields(Audio))
    s = Sensed(1.0, bodies=(figure(),), audio=Audio(level=0.8, level_smooth=1.0))
    assert s.bodies[0].id == 1 and s.camera_t == 0.0 and s.audio.level_smooth == 1.0


def test_one_shoulder_without_hips_uses_the_nose_line():
    # C14: one shoulder and no hip give no torso, so a line from the shoulders would sit on the shoulder.
    no_hips = {RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0), LEFT_HIP: Keypoint(0.45, 0.7, 0.0),
               RIGHT_HIP: Keypoint(0.55, 0.7, 0.0)}
    b = figure(no_hips)
    assert b.shoulder_mid is not None and b.torso == 0.0
    assert b.raise_line == pytest.approx(0.22)                                           # the nose
    assert figure({**no_hips, RIGHT_WRIST: Keypoint(0.65, 0.395)}).raised_wrist is None   # a hair over the shoulder
    assert figure({**no_hips, RIGHT_WRIST: Keypoint(0.65, 0.25)}).raised_wrist is None    # under the nose
    assert figure({**no_hips, RIGHT_WRIST: Keypoint(0.65, 0.18)}).raised_wrist == Keypoint(0.65, 0.18)
    assert figure({**no_hips, LEFT_WRIST: Keypoint(0.35, 0.1), RIGHT_WRIST: Keypoint(0.65, 0.18)}).both_hands_up
    blind = figure({**no_hips, NOSE: Keypoint(0.5, 0.22, 0.0), RIGHT_WRIST: Keypoint(0.65, 0.1),
                    LEFT_WRIST: Keypoint(0.35, 0.1)})
    assert blind.raise_line is None and blind.raised_wrist is None and not blind.both_hands_up


def test_blob_coordinates_are_clamped():
    # C16: headlamps() crosses from x -0.05 to 1.05; a consumer mapping x to a pixel would index at -1.
    b = Blob(-0.05, 1.2, 0.02, (255, 250, 235))
    assert (b.x, b.y) == (0.0, 1.0)
    assert Blob(math.nan, 0.5, 0.02, (255, 0, 0)).x == 0.0 and Blob(0.3, math.inf, 0.02, (255, 0, 0)).y == 1.0
    assert Blob(None, 0.5, 0.02, (255, 0, 0)).x == 0.0                                  # as a keypoint's None
    assert place_blob(b, Calibration()).x == 0.0
    assert Blob(0.25, 0.75, 0.02, (255, 0, 0)) == Blob(0.25, 0.75, 0.02, (255, 0, 0), True)   # in range: kept
```

- [ ] **Step 2: Run them to verify they fail**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_sensed.py`
Expected: `3 failed, 17 passed`: `test_sensed_and_audio_take_keywords_after_t` (`Failed: DID NOT RAISE TypeError`), `test_one_shoulder_without_hips_uses_the_nose_line` (`assert 0.4 == 0.22 ± 2.2e-07`, the line on the shoulder) and `test_blob_coordinates_are_clamped` (`assert (-0.05, 1.2) == (0.0, 1.0)`).

- [ ] **Step 3: Implement**

`arcade/sensed.py`:

```python
"""The Sensed record (spec 5): the only input games see, built once per tick by the runner."""
from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from arcade.calibration import Calibration

(NOSE, LEFT_EYE, RIGHT_EYE, LEFT_EAR, RIGHT_EAR, LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_ELBOW,
 RIGHT_ELBOW, LEFT_WRIST, RIGHT_WRIST, LEFT_HIP, RIGHT_HIP, LEFT_KNEE, RIGHT_KNEE, LEFT_ANKLE,
 RIGHT_ANKLE) = range(17)

KEYPOINT_NAMES = ("nose", "left_eye", "right_eye", "left_ear", "right_ear", "left_shoulder",
                  "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist",
                  "left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle")

SKELETON = ((LEFT_SHOULDER, LEFT_ELBOW), (LEFT_ELBOW, LEFT_WRIST), (RIGHT_SHOULDER, RIGHT_ELBOW),
            (RIGHT_ELBOW, RIGHT_WRIST), (LEFT_SHOULDER, RIGHT_SHOULDER), (LEFT_SHOULDER, LEFT_HIP),
            (RIGHT_SHOULDER, RIGHT_HIP), (LEFT_HIP, RIGHT_HIP), (LEFT_HIP, LEFT_KNEE),
            (LEFT_KNEE, LEFT_ANKLE), (RIGHT_HIP, RIGHT_KNEE), (RIGHT_KNEE, RIGHT_ANKLE),
            (NOSE, LEFT_SHOULDER), (NOSE, RIGHT_SHOULDER))

MIN_CONF = 0.3
RAISE_TORSOS = 0.3               # the raise line sits this many torso lengths above the shoulder midpoint
REACH_WIDTHS = 1.5               # the reach box spans this many shoulder widths each side of the shoulder midpoint,
REACH_TOP_TORSOS = 1.05          # and from this many torso lengths above it (head plus a forearm) down to the hips
TORSO_PER_SHOULDER_WIDTH = 1.25  # torso length estimated from shoulder width when no hip is seen
NOSE_TO_HIP_PER_TORSO = 1.5      # scale estimated from the torso when the nose is not seen
MOTION_GRID = (128, 64)          # (width, height) of the fixed grid scenario files and actors store motion on


@dataclass(frozen=True)
class Keypoint:
    x: float
    y: float
    conf: float = 1.0


def _clean(kp: Keypoint) -> Keypoint:
    x, y, conf = kp.x, kp.y, kp.conf
    bad = any(v is None or math.isnan(v) for v in (x, y, conf))
    if bad:
        return Keypoint(0.0, 0.0, 0.0)
    return Keypoint(min(1.0, max(0.0, x)), min(1.0, max(0.0, y)),
                    0.0 if not 0.0 <= x <= 1.0 or not 0.0 <= y <= 1.0 else min(1.0, max(0.0, conf)))


def _clamp01(v: float) -> float:
    return min(1.0, max(0.0, v))


def _mid(a: Keypoint, b: Keypoint) -> Keypoint | None:
    """The midpoint of the confident ones of a and b; one alone stands in for the pair."""
    seen = [k for k in (a, b) if k.conf >= MIN_CONF]
    if not seen:
        return None
    return Keypoint(sum(k.x for k in seen) / len(seen), sum(k.y for k in seen) / len(seen),
                    min(k.conf for k in seen))


@dataclass(frozen=True)
class Body:
    """One tracked person. Keypoints are normalized camera coordinates, already mirrored and smoothed.

    scale 0.0 means "measure it": the nose-to-mid-hip length, or 1.5 torso lengths without a nose.
    """

    id: int
    box: tuple[float, float, float, float]
    keypoints: tuple[Keypoint, ...]
    vx: float = 0.0
    vy: float = 0.0
    scale: float = 0.0
    in_zone: bool = True
    zone_x: float = 0.5
    zone_y: float = 0.5
    seen_ago: float = 0.0

    def __post_init__(self):
        if len(self.keypoints) != 17:
            raise ValueError(f"a body has 17 keypoints, got {len(self.keypoints)}")
        object.__setattr__(self, "keypoints", tuple(_clean(k) for k in self.keypoints))
        if self.scale == 0.0:
            object.__setattr__(self, "scale", self._measured_scale())

    def _measured_scale(self) -> float:
        hip = self.hip_mid
        if self.nose.conf >= MIN_CONF and hip is not None:
            return math.hypot(self.nose.x - hip.x, self.nose.y - hip.y)
        return NOSE_TO_HIP_PER_TORSO * self.torso

    @property
    def nose(self) -> Keypoint:
        return self.keypoints[NOSE]

    @property
    def left_wrist(self) -> Keypoint:
        return self.keypoints[LEFT_WRIST]

    @property
    def right_wrist(self) -> Keypoint:
        return self.keypoints[RIGHT_WRIST]

    @property
    def shoulder_mid(self) -> Keypoint | None:
        """The midpoint of the confident shoulders, None without one.

        With one shoulder, its y stands in for the pair, but x comes from both hips, else a confident
        nose, else the one hip seen, else that shoulder: the centre (and so anchor, zone_x and the reach
        box) does not jump half a shoulder or hip width when one shoulder and one hip drop out.
        """
        left, right = self.keypoints[LEFT_SHOULDER], self.keypoints[RIGHT_SHOULDER]
        seen = [k for k in (left, right) if k.conf >= MIN_CONF]
        if len(seen) != 1:
            return _mid(left, right)
        one = seen[0]
        hips = (self.keypoints[LEFT_HIP], self.keypoints[RIGHT_HIP])
        if all(h.conf >= MIN_CONF for h in hips):
            x = (hips[0].x + hips[1].x) / 2
        elif self.nose.conf >= MIN_CONF:
            x = self.nose.x
        else:
            hip = self.hip_mid
            x = hip.x if hip is not None else one.x
        return Keypoint(x, one.y, one.conf)

    @property
    def hip_mid(self) -> Keypoint | None:
        return _mid(self.keypoints[LEFT_HIP], self.keypoints[RIGHT_HIP])

    @property
    def shoulder_width(self) -> float:
        """Distance between the shoulders, 0.0 unless both are confident."""
        a, b = self.keypoints[LEFT_SHOULDER], self.keypoints[RIGHT_SHOULDER]
        if a.conf < MIN_CONF or b.conf < MIN_CONF:
            return 0.0
        return math.hypot(a.x - b.x, a.y - b.y)

    @property
    def torso(self) -> float:
        """Shoulder midpoint to hip midpoint; from the shoulder width without hips; 0.0 when unknown."""
        s, h = self.shoulder_mid, self.hip_mid
        if s is not None and h is not None:
            return math.hypot(s.x - h.x, s.y - h.y)
        return TORSO_PER_SHOULDER_WIDTH * self.shoulder_width

    @property
    def anchor(self) -> Keypoint | None:
        """What the tracker and place() follow: the shoulder midpoint, then the nose, then the hips."""
        s = self.shoulder_mid
        if s is not None:
            return s
        if self.nose.conf >= MIN_CONF:
            return self.nose
        return self.hip_mid

    @property
    def raise_line(self) -> float | None:
        """A wrist above this y is raised: 0.3 torso above the shoulders.

        The nose stands in without shoulders, and when the torso cannot be measured (one shoulder and no
        hip), because a line on the shoulder itself would count a wrist a hair above it; with neither,
        None, and nothing is raised.
        """
        s, torso = self.shoulder_mid, self.torso
        if s is not None and torso > 0.0:
            return s.y - RAISE_TORSOS * torso
        if self.nose.conf >= MIN_CONF:
            return self.nose.y
        return None

    @property
    def raised_wrist(self) -> Keypoint | None:
        """The higher confident wrist above the raise line, else None."""
        line = self.raise_line
        if line is None:
            return None
        best = None
        for w in (self.left_wrist, self.right_wrist):
            if w.conf >= MIN_CONF and w.y < line and (best is None or w.y < best.y):
                best = w
        return best

    @property
    def both_hands_up(self) -> bool:
        line = self.raise_line
        return line is not None and all(w.conf >= MIN_CONF and w.y < line
                                        for w in (self.left_wrist, self.right_wrist))

    def reach(self, kp: Keypoint) -> tuple[float, float]:
        """kp in the body-relative reach box (spec 7.3), (u, v) each clamped to 0..1.

        u runs across 1.5 shoulder widths each side of the shoulder midpoint; v runs from 1.05 torso
        above the shoulder midpoint (head plus a forearm) down to hip height. Without shoulders the
        body box is the frame of reference.
        """
        s, torso = self.shoulder_mid, self.torso
        width = self.shoulder_width or torso / TORSO_PER_SHOULDER_WIDTH
        if s is None or torso <= 0.0 or width <= 0.0:
            x0, y0, x1, y1 = self.box
            u = (kp.x - x0) / (x1 - x0) if x1 > x0 else 0.5
            v = (kp.y - y0) / (y1 - y0) if y1 > y0 else 0.5
        else:
            hip = self.hip_mid
            top = s.y - REACH_TOP_TORSOS * torso
            bottom = hip.y if hip is not None else s.y + torso
            u = (kp.x - (s.x - REACH_WIDTHS * width)) / (2 * REACH_WIDTHS * width)
            v = (kp.y - top) / (bottom - top)
        return (_clamp01(u), _clamp01(v))

    @property
    def cursor(self) -> tuple[float, float] | None:
        """The confident wrist further from its hip, through reach(); None without a confident wrist.

        Stateless: when the pointing wrist drops out for a frame the cursor jumps to the other wrist
        (15 percent of captures at the spec 6.4 dropout), so every consumer needs a grace period or hysteresis.
        """
        best, far = None, -1.0
        for wrist, hip_index in ((self.left_wrist, LEFT_HIP), (self.right_wrist, RIGHT_HIP)):
            if wrist.conf < MIN_CONF:
                continue
            own = self.keypoints[hip_index]
            ref = next((k for k in (own if own.conf >= MIN_CONF else None, self.hip_mid, self.shoulder_mid)
                        if k is not None), wrist)
            d = math.hypot(wrist.x - ref.x, wrist.y - ref.y)
            if d > far:
                best, far = wrist, d
        return None if best is None else self.reach(best)

    @property
    def center(self) -> tuple[float, float]:
        x0, y0, x1, y1 = self.box
        return ((x0 + x1) / 2, (y0 + y1) / 2)

    @property
    def height(self) -> float:
        return self.box[3] - self.box[1]

    @property
    def confidence(self) -> float:
        return sum(k.conf for k in self.keypoints) / 17


@dataclass(frozen=True)
class Blob:
    """A light source. x and y are clamped to 0..1 (NaN and None to 0), as keypoints are, so a blob that leaves the
    frame (a headlamp crossing it) never maps outside the wall."""

    x: float
    y: float
    size: float
    color: tuple[int, int, int]
    in_zone: bool = True

    def __post_init__(self):
        for name in ("x", "y"):
            v = getattr(self, name)
            object.__setattr__(self, name, 0.0 if v is None or math.isnan(v) else _clamp01(v))


@dataclass(frozen=True, kw_only=True)
class Audio:
    """Every field is a keyword: Audio(0.8, 1.0) would silently put 1.0 in level_smooth."""

    level: float = 0.0            # broadband RMS with slow gain, 0..1, for ambient visuals only
    level_smooth: float = 0.0     # level with 50 ms attack and 300 ms release
    peak: float = 0.0
    voice_db: float = -90.0       # absolute dBFS in the 300 Hz to 3.4 kHz band
    floor_db: float = -90.0       # rolling 30 s 90th percentile of voice_db
    voice: float = 0.0            # (voice_db - floor_db) / 30, clamped 0..1
    clap: bool = False
    onset: bool = False
    beat: bool = False
    bpm: float | None = None


def _in(zone: tuple[float, float, float, float], x: float, y: float) -> bool:
    x0, y0, x1, y1 = zone
    return x0 <= x <= x1 and y0 <= y <= y1


def place(body: Body, calibration: Calibration) -> Body:
    """body with in_zone, zone_x and zone_y from the calibration (spec 6.6). Actors and the tracker call it.

    The anchor (shoulders, then nose, then hips; the box centre without any) maps into the zone, 0..1
    across the mat and clamped. In the zone means the anchor inside it and the body at least min_height tall.
    """
    x0, y0, x1, y1 = calibration.zone
    a = body.anchor
    ax, ay = (a.x, a.y) if a is not None else body.center
    inside = _in(calibration.zone, ax, ay) and body.height >= calibration.min_height
    return dataclasses.replace(body, in_zone=inside, zone_x=_clamp01((ax - x0) / (x1 - x0)),
                               zone_y=_clamp01((ay - y0) / (y1 - y0)))


def place_blob(blob: Blob, calibration: Calibration) -> Blob:
    """blob with in_zone from the calibration zone. The blob must be in the zone's space, the mirrored
    display space of the keypoints: a blob source mirrors x as mirror_keypoints does."""
    return dataclasses.replace(blob, in_zone=_in(calibration.zone, blob.x, blob.y))


def _resample(motion: np.ndarray, width: int, height: int) -> np.ndarray:
    """Nearest-cell resample that keeps every lit cell: a shrinking axis ORs the source cells it covers."""
    rows = (np.arange(height) * motion.shape[0]) // height
    cols = (np.arange(width) * motion.shape[1]) // width
    grid = np.logical_or.reduceat(motion.astype(bool), rows, axis=0)
    return np.logical_or.reduceat(grid, cols, axis=1)


@dataclass(frozen=True, eq=False)
class Sensed:
    """Every field after t is a keyword: Sensed(t, bodies) would silently put the bodies in camera_t."""

    t: float                                     # seconds since runner start
    _: dataclasses.KW_ONLY
    camera_t: float = 0.0                        # capture time of the newest camera frame, on the runner clock
    camera_fresh: bool = False                   # true on the tick a new camera frame arrived
    camera_seq: int = 0
    bodies: tuple[Body, ...] = ()                # tracked, stable ids, largest scale first
    player: Body | None = None                   # the locked player (spec 7.2), set by the runner
    player2: Body | None = None
    present: bool = False                        # someone is in the zone, with hysteresis, set by the runner
    blobs: tuple[Blob, ...] = ()                 # light sources, brightest first, at most 8
    motion: np.ndarray = field(default_factory=lambda: np.zeros((0, 0), bool))   # bool (height, width)
    audio: Audio = field(default_factory=Audio)

    def __post_init__(self):
        # One grid is shared by every tick that holds it (degrade, with_motion), so the record keeps a
        # read-only view; the producer's own array stays writeable, but must not change after hand-over.
        # None (an old scenario record) means the empty grid.
        motion = np.zeros((0, 0), bool) if self.motion is None else np.asarray(self.motion, bool)
        motion = motion.view()
        motion.flags.writeable = False
        object.__setattr__(self, "motion", motion)

    def with_motion(self, size: tuple[int, int]) -> "Sensed":
        """This record with motion as a (height, width) grid for size (width, height).

        An empty grid becomes all False; a grid of another shape is resampled. Bodies are never
        rasterized into it.
        """
        w, h = size
        if self.motion.shape == (h, w):
            return self
        if self.motion.size == 0:
            return dataclasses.replace(self, motion=np.zeros((h, w), bool))
        return dataclasses.replace(self, motion=_resample(self.motion, w, h))
```

- [ ] **Step 4: Run the tests**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_sensed.py`
Expected: `20 passed`.

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`
Expected: `186 passed`, no skips.

- [ ] **Step 5: Commit**

```bash
git add arcade/sensed.py tests/arcade/test_sensed.py
git commit -m "fix(arcade): Sensed and Audio fields are keywords after t, nose raise line without a torso, blobs clamped (it02 C12, C14, C16)" -m "No existing assert changed; test_sensed gains import dataclasses and three tests. Every existing Sensed and Audio call already used keywords."
```

---

### Task 2: Actor guard rails (carried C13 for degrade and shake, C15, C16)

**Files:**
- Modify: `arcade/sources/actors.py` (whole file below)
- Test: `tests/arcade/test_actors.py`, `tests/arcade/test_festival.py` (whole files below)

**Interfaces:**
- Consumes: Task 1's `Sensed` (keyword-only after `t`) and clamped `Blob`; iteration 2's `place`, `Calibration`, `Person`, `scene`, `degrade`, `crowd`, `tempo`, `camp_kick`, `headlamps`.
- Produces: `scene(...)` raises `ValueError("duplicate body id N in scene: ...")` at the call, before any frame, and returns an iterator; `crowd(n: int, start: float = 0.0, id_base: int = 100) -> list[Person]` with ids `id_base + i`; `degrade(...)` and, inside its window, `shake(...)` raise `ValueError` naming the function, the body, the time, `calibration=` and `place()` when a clean body's placement is not reproduced by their calibration (owner decision Q9 for `shake`); `tempo(bpm, start=0.0)` raises `ValueError` for a bpm not in (0, inf).

Changes to existing test lines, both in `tests/arcade/test_festival.py`: the line `from arcade.sensed import MIN_CONF` becomes `from arcade.sensed import MIN_CONF, Sensed, place`; and, by owner decision Q9, line 180 `    assert not list(shake(0.5, 1.0)(iter(source)))[30].bodies[0].in_zone     # the default zone ends at 0.8` becomes the two lines `    with pytest.raises(ValueError, match="calibration"):                    # owner decision Q9: no silent default zone` and `        list(shake(0.5, 1.0)(iter(source)))`. Both modules gain tests at the end. No other line is changed or removed.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_actors.py`:

```python
import math

import numpy as np
import pytest

from arcade.poses import POSES
from arcade.sensed import LEFT_WRIST, NOSE, RIGHT_WRIST, Keypoint
from arcade.sources.actors import (TICK, Person, claps, level_ramp, loud, make_keypoints, motion_rect,
                                   moving_blob, scene, silence, tempo)


def test_make_keypoints_is_a_standing_figure():
    kps = make_keypoints(0.5, 0.5, 0.6)
    assert len(kps) == 17
    assert kps[NOSE].y < kps[LEFT_WRIST].y
    up = make_keypoints(0.5, 0.5, 0.6, right_up=True)
    assert up[RIGHT_WRIST].y < up[NOSE].y and up[LEFT_WRIST].y > up[NOSE].y


def test_person_walks_and_holds_position():
    p = Person(0.1).walk(0.9, seconds=2.0)
    assert p.body_at(0.0, 0).center[0] == pytest.approx(0.1, abs=0.02)
    assert p.body_at(1.0, 0).center[0] == pytest.approx(0.5, abs=0.02)
    assert p.body_at(5.0, 0).center[0] == pytest.approx(0.9, abs=0.02)


def test_person_chained_walks_start_where_the_last_ended():
    p = Person(0.2).walk(0.6, 1.0).walk(0.2, 1.0)
    assert p.body_at(1.0, 0).center[0] == pytest.approx(0.6, abs=0.02)
    assert p.body_at(2.0, 0).center[0] == pytest.approx(0.2, abs=0.02)


def test_hands_and_jump_and_presence():
    p = Person().raise_hand(at=1.0, seconds=0.5).both_hands_up(at=3.0, seconds=1.0).jump(at=5.0, height=0.2)
    assert p.body_at(0.5, 0).raised_wrist is None
    assert p.body_at(1.2, 0).raised_wrist is not None and not p.body_at(1.2, 0).both_hands_up
    assert p.body_at(3.5, 0).both_hands_up
    standing = p.body_at(4.0, 0).nose.y
    assert p.body_at(5.3, 0).nose.y < standing - 0.1
    q = Person().leave(at=2.0)
    assert q.present(1.9) and not q.present(2.1)
    r = Person().arrive(at=2.0)
    assert not r.present(1.9) and r.present(2.1)


def test_scene_assigns_ids_and_ticks():
    frames = list(scene(persons=[Person(0.2), Person(0.8)], ticks=3))
    assert len(frames) == 3
    assert [b.id for b in frames[0].bodies] == [0, 1]
    assert frames[1].t == pytest.approx(TICK)
    assert frames[0].motion.shape == (64, 128) and not frames[0].motion.any()


def test_blob_and_audio_scripts():
    b = moving_blob(0.0, 0.5, 1.0, 0.5, seconds=2.0, color=(255, 0, 0))
    assert b(-0.1) is None and b(2.1) is None
    assert b(1.0).x == pytest.approx(0.5) and b(1.0).color == (255, 0, 0)
    assert silence()(3.0).level == 0.0
    c = claps([1.0, 2.0])
    hits = [i for i in range(90) if c(i * TICK).onset]
    assert len(hits) == 2
    t = tempo(120)
    beats = [i for i in range(90) if t(i * TICK).beat]
    assert beats == [0, 15, 30, 45, 60, 75]
    assert t(0.1).bpm == 120
    assert loud(0.9)(0.0).level == 0.9
    frames = list(scene(blobs=[b], audio=c, ticks=60))
    assert frames[30].blobs[0].x == pytest.approx(0.5, abs=0.01)
    assert frames[30].audio.onset


def test_tempo_128_exactly_one_beat_per_period():
    for bpm in (60, 90, 100, 120, 128, 140, 174, 200):
        script = tempo(bpm)
        beats = [i for i in range(1800) if script(i * TICK).beat]
        assert len(beats) == bpm, f"{bpm} bpm gave {len(beats)} beats in 60 s"
        gaps = np.diff(beats)
        assert gaps.min() >= math.floor(1800 / bpm), f"{bpm} bpm has a gap of {gaps.min()} ticks"
    late = tempo(128, start=2.0)
    first = next(i for i in range(1800) if late(i * TICK).beat)
    assert first == 60


def test_claps_fire_exactly_once():
    for k in range(300):
        when = k * 0.0123
        script = claps([when])
        hits = [i for i in range(120) if script(i * TICK).clap]
        assert hits == [math.ceil(when / TICK - 1e-6)], f"clap at {when} fired on ticks {hits}"
        assert all(script(i * TICK).onset == (i in hits) for i in range(120))


def test_wrist_ramp_in_reach_units():
    p = Person().wrist("right", 0.9, 0.1, seconds=2.0, at=1.0).wrist("right", 0.1, 0.5, seconds=1.0)
    assert p.body_at(0.5, 0).right_wrist == make_keypoints(0.5, 0.55, 0.6)[RIGHT_WRIST]   # hanging before
    for t, v in ((1.0, 0.9), (2.0, 0.5), (2.9, 0.14), (3.5, 0.3)):
        body = p.body_at(t, 0)
        assert body.reach(body.right_wrist)[1] == pytest.approx(v, abs=1e-9), f"t={t}"
        assert body.left_wrist == make_keypoints(0.5, 0.55, 0.6)[LEFT_WRIST]
    assert p.body_at(2.9, 0).raised_wrist is not None and p.body_at(1.0, 0).raised_wrist is None
    assert p.body_at(4.0, 0).right_wrist == make_keypoints(0.5, 0.55, 0.6)[RIGHT_WRIST]   # hanging after
    with pytest.raises(ValueError, match="hand"):
        Person().wrist("middle", 0.0, 1.0, 1.0)


def test_wrist_works_for_a_body_partly_out_of_frame():
    low = Person(y=1.05).wrist("right", 0.5, 0.5, seconds=1.0).body_at(0.5, 0)       # hips below the frame
    assert low.hip_mid is None and low.right_wrist.conf == 1.0
    high = Person(y=0.3, height=0.6).jump(at=0.0, height=0.2).wrist("left", 0.0, 0.0, seconds=1.0)
    assert high.body_at(0.3, 0).left_wrist.conf == 0.0                               # above the frame: clamped
    inside = Person().wrist("right", 0.3, 0.3, seconds=1.0).body_at(0.5, 0)
    assert inside.reach(inside.right_wrist)[1] == pytest.approx(0.3, abs=1e-9)


def test_pose_from_table():
    assert set(POSES) >= {"stand", "t_pose", "arms_up"}
    assert all(len(offsets) == 17 for offsets in POSES.values())
    stand = tuple(Keypoint(0.5 + dx * 0.6, 0.55 + dy * 0.6) for dx, dy in POSES["stand"])
    assert make_keypoints(0.5, 0.55, 0.6) == stand
    p = Person(x=0.5, y=0.55, height=0.6).pose("t_pose", at=1.0, seconds=2.0)
    held = p.body_at(1.5, 0)
    for i, (dx, dy) in enumerate(POSES["t_pose"]):
        assert (held.keypoints[i].x, held.keypoints[i].y) == pytest.approx((0.5 + dx * 0.6, 0.55 + dy * 0.6))
    assert p.body_at(0.5, 0).keypoints == make_keypoints(0.5, 0.55, 0.6)
    assert p.body_at(3.0, 0).keypoints == make_keypoints(0.5, 0.55, 0.6)
    assert Person().pose("arms_up", at=0.0, seconds=1.0).body_at(0.5, 0).both_hands_up


def test_unknown_pose_raises():
    with pytest.raises(ValueError, match="unknown pose 'dab'"):
        Person().pose("dab", at=0.0, seconds=1.0)


def test_motion_rect_grid():
    m = motion_rect(0.25, 0.5, 0.5, 1.0, start=1.0, seconds=1.0)
    assert m(0.9) is None and m(2.0) is None
    grid = m(1.5)
    assert grid.shape == (64, 128) and grid.dtype == bool
    assert grid[32:, 32:64].all() and grid.sum() == 32 * 32
    tiny = motion_rect(0.5, 0.5, 0.5, 0.5, start=0.0, seconds=1.0)(0.0)
    assert tiny.sum() == 1 and tiny[32, 64]
    frames = list(scene(motion=[m, motion_rect(0.0, 0.0, 0.1, 0.1, start=0.0, seconds=0.5)], ticks=60))
    assert frames[0].motion[:7, :13].all() and not frames[0].motion[32:, 32:64].any()
    assert frames[45].motion[32:, 32:64].all() and not frames[45].motion[:7, :13].any()
    assert not frames[20].motion.any()
    with pytest.raises(ValueError, match="shape"):
        list(scene(motion=[lambda t: np.zeros((4, 4), bool)], ticks=1))


def test_level_ramp_interpolates():
    ramp = level_ramp([(1.0, 0.0), (3.0, 1.0), (4.0, 0.5)])
    assert ramp(0.0).level == 0.0 and ramp(2.0).level == pytest.approx(0.5)
    assert ramp(3.5).level == pytest.approx(0.75) and ramp(9.0).level == 0.5
    assert ramp(2.0).level_smooth == ramp(2.0).peak == ramp(2.0).level
    with pytest.raises(ValueError):
        level_ramp([(2.0, 0.0), (1.0, 1.0)])
    with pytest.raises(ValueError):
        level_ramp([])


def test_scene_stamps_camera_and_places_bodies():
    big, small = Person(0.5, height=0.6), Person(0.1, height=0.3)
    frames = list(scene(persons=[small, big], blobs=[moving_blob(0.5, 0.5, 0.5, 0.5, 9.0)] * 10, ticks=3))
    f = frames[2]
    assert (f.camera_t, f.camera_fresh, f.camera_seq) == (f.t, True, 3)
    assert [b.id for b in f.bodies] == [1, 0]                   # largest scale first
    assert f.bodies[0].in_zone and not f.bodies[1].in_zone     # the small one is short and off to the side
    assert len(f.blobs) == 8 and all(b.in_zone for b in f.blobs)


def test_person_velocity():
    p = Person(0.1).walk(0.9, seconds=2.0).jump(at=3.0, height=0.2)
    assert p.body_at(1.0, 0).vx == pytest.approx(0.4)
    assert p.body_at(0.0, 0).vx == 0.0                          # causal: not yet moving at the start
    assert p.body_at(2.0, 0).vx == pytest.approx(0.4)           # the last tick of the walk still moved
    assert p.body_at(2.5, 0).vx == 0.0 and p.body_at(2.5, 0).vy == 0.0
    assert p.body_at(3.1, 0).vy < 0                             # rising


def test_tempo_needs_a_positive_bpm():
    # C16: tempo(0) divided by zero; a negative bpm gave a negative period.
    for bad in (0, -120, math.nan, math.inf):
        with pytest.raises(ValueError, match="bpm"):
            tempo(bad)
```

`tests/arcade/test_festival.py`:

```python
import inspect
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from arcade.calibration import Calibration
from arcade.sensed import MIN_CONF, Sensed, place
from arcade.sources.actors import (REAL_NOISE, TICK, Person, camp_kick, claps, crowd, degrade, headlamps,
                                   motion_rect, scene, shake, wind)

ROOT = Path(__file__).resolve().parents[2]

DIGEST = """
import hashlib
from arcade.sources.actors import Person, crowd, degrade, scene
frames = degrade(scene(persons=[Person(0.3).walk(0.7, 2.0).raise_hand(at=1.0), *crowd(3)], ticks=90))
h = hashlib.sha256()
for f in frames:
    h.update(repr((f.camera_seq, f.camera_fresh, [(b.id, b.keypoints, b.in_zone) for b in f.bodies])).encode())
digest = h.hexdigest()
"""


def walker():
    return Person(0.2).walk(0.8, 3.0)


def test_degrade_samples_holds_and_delays():
    source = list(scene(persons=[walker()], audio=claps([0.2]), ticks=90))
    frames = list(degrade(iter(source)))
    assert len(frames) == 90
    fresh = [i for i, f in enumerate(frames) if f.camera_fresh]
    assert fresh == list(range(5, 90, 3)) and len(fresh) == 29        # 10 fps, first visible at 0.15 s
    for f in frames[:5]:
        assert f.bodies == () and f.camera_seq == 0 and f.motion.size == 0
    for i, f in enumerate(frames[5:], start=5):
        assert f.t == source[i].t
        assert 0.15 - 1e-9 <= f.t - f.camera_t < 0.25, f"tick {i}: camera_t {f.camera_t}"
        assert f.camera_seq == (i - 5) // 3 + 1
    assert frames[6].bodies == frames[5].bodies and frames[7].bodies == frames[5].bodies
    assert frames[8].bodies != frames[5].bodies
    assert frames[6].audio.clap and not frames[6].camera_fresh     # audio is not delayed
    clean = list(degrade(iter(source), keypoint_dropout=0.0, jitter=0.0))
    assert clean[8].bodies == source[3].bodies                       # capture 1 is the scene at 0.1 s


def test_degrade_without_noise_is_the_scene():
    source = list(scene(persons=[walker()], motion=[motion_rect(0.0, 0.0, 0.5, 0.5, 0.0, 1.0)], ticks=40))
    frames = list(degrade(iter(source), fps=30, latency=0.0, keypoint_dropout=0.0, jitter=0.0))
    for i, (f, s) in enumerate(zip(frames, source)):
        assert f.bodies == s.bodies and f.camera_fresh and f.camera_seq == i + 1
        assert f.camera_t == s.t and np.array_equal(f.motion, s.motion)


def test_degrade_drops_and_jitters_at_the_given_rates():
    source = list(scene(persons=[walker(), Person(0.7, id=7)], ticks=300))
    frames = [f for f in degrade(iter(source), latency=0.0) if f.camera_fresh]
    dropped = total = 0
    for f in frames:
        truth = source[round(f.camera_t / TICK)]
        for b, t in zip(f.bodies, truth.bodies):
            for k, kt in zip(b.keypoints, t.keypoints):
                total += 1
                dropped += k.conf == 0.0
                assert abs(k.x - kt.x) <= 0.01 + 1e-9 and abs(k.y - kt.y) <= 0.01 + 1e-9
    assert total == 100 * 2 * 17
    assert 0.10 <= dropped / total <= 0.20, f"dropped {dropped} of {total}"


def test_degrade_rejects_bad_parameters():
    for bad in ({"fps": 0}, {"latency": -0.1}, {"keypoint_dropout": 1.5}, {"jitter": -0.01},
                {"fps": float("nan")}):
        with pytest.raises(ValueError, match="degrade needs"):
            list(degrade(scene(ticks=1), **bad))


def test_degrade_refuses_a_stream_that_does_not_start_at_zero():
    source = list(scene(persons=[walker()], ticks=60))
    with pytest.raises(ValueError, match="starts at t=0; frame 0 has t=1.0"):
        list(degrade(iter(source[30:])))
    with pytest.raises(ValueError, match="frame 2"):
        list(degrade(iter(source[:2] + source[3:])))


def test_still_player_keeps_cursor_and_zone_steady_under_spec_noise():
    source = scene(persons=[Person().raise_hand(at=0.0, seconds=99.0)], ticks=900)
    noise = degrade(source, fps=10, latency=0.15, keypoint_dropout=0.15, jitter=0.01)   # spec 6.4 literals
    captures = [f.bodies[0] for f in noise if f.camera_fresh]
    assert len(captures) == 299
    u = np.array([b.cursor[0] for b in captures if b.right_wrist.conf >= MIN_CONF])
    zone_x = np.array([b.zone_x for b in captures])
    assert np.median(u) == pytest.approx(0.71, abs=0.02) and np.median(zone_x) == pytest.approx(0.5, abs=0.01)
    # A dropped shoulder, or a dropped shoulder and hip, once moved the centre half a width (u by 0.15).
    assert np.mean(np.abs(u - np.median(u)) > 0.1) <= 0.02
    assert np.mean(np.abs(zone_x - np.median(zone_x)) > 0.05) <= 0.02


def test_degrade_is_deterministic():
    runs = []
    for _ in range(2):
        ns: dict = {}
        exec(DIGEST, ns)
        runs.append(ns["digest"])
    for seed in ("0", "12345"):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        out = subprocess.run([sys.executable, "-c", DIGEST + "print(digest)"], cwd=ROOT, env=env,
                             capture_output=True, text=True, check=True)
        runs.append(out.stdout.strip())
    assert len(set(runs)) == 1, runs


def test_real_noise_is_a_degrade_setting():
    assert set(REAL_NOISE) == {"fps", "latency", "keypoint_dropout", "jitter"}     # values are refit (spec 9.5)
    assert len(list(degrade(scene(persons=[walker()], ticks=30), **REAL_NOISE))) == 30
    names = ("fps", "latency", "keypoint_dropout", "jitter")
    defaults = {n: inspect.signature(degrade).parameters[n].default for n in names}
    assert defaults == {"fps": 10, "latency": 0.15, "keypoint_dropout": 0.15, "jitter": 0.01}   # spec 6.4


def test_crowd_is_out_of_zone():
    people = crowd(6)
    assert len(people) == 6 and len({p.id for p in people}) == 6
    raised = 0
    for f in scene(persons=[Person(0.5), *people], ticks=300):
        assert len(f.bodies) == 7
        assert [b.in_zone for b in f.bodies] == [True] + [False] * 6
        assert f.bodies[0].id == 0                                    # the player is the largest
        raised += sum(b.raised_wrist is not None for b in f.bodies[1:])
    assert raised > 0                                                 # the crowd waves


def test_camp_kick_has_onsets_but_no_claps():
    kick = camp_kick(125)
    frames = [kick(i * TICK) for i in range(1800)]
    assert sum(a.onset for a in frames) == 125 and sum(a.beat for a in frames) == 125
    assert not any(a.clap for a in frames)
    assert all(a.voice == 0.0 and a.voice_db == a.floor_db and a.bpm == 125 for a in frames)


def test_wind_never_claps():
    frames = [wind()(i * TICK) for i in range(1800)]
    assert not any(a.clap or a.beat for a in frames)
    assert 20 <= sum(a.onset for a in frames) <= 25
    assert all(a.voice < 0.1 for a in frames) and max(a.level for a in frames) > 0.45


def test_headlamps_are_out_of_zone():
    frames = list(scene(blobs=headlamps(), ticks=1800))
    assert all(f.blobs and not any(b.in_zone for b in f.blobs) for f in frames)
    crossing = [i for i, f in enumerate(frames) if len(f.blobs) == 2]
    assert crossing and crossing[0] == 0 and 600 in crossing and 300 not in crossing


def test_shake_empties_motion_and_jitters():
    source = list(scene(persons=[walker()], motion=[motion_rect(0.0, 0.0, 1.0, 1.0, 0.0, 9.0)], ticks=90))
    shaken = list(shake(1.0, 1.0)(iter(source)))
    assert len(shaken) == 90
    for i, (f, s) in enumerate(zip(shaken, source)):
        if 30 <= i < 60:
            assert f.motion.size == 0
            for k, ks in zip(f.bodies[0].keypoints, s.bodies[0].keypoints):
                assert abs(k.x - ks.x) <= 0.03 + 1e-9 and abs(k.y - ks.y) <= 0.03 + 1e-9 and k.conf == ks.conf
            assert f.bodies[0].keypoints != s.bodies[0].keypoints
        else:
            assert f is s
    first = list(shake(1.0, 1.0)(iter(source)))
    assert all(a.bodies == b.bodies for a, b in zip(first, shaken))


def test_shake_places_against_the_scene_calibration():
    right = Calibration(zone=(0.5, 0.2, 1.0, 0.8))
    source = list(scene(persons=[Person(0.85)], ticks=60, calibration=right))
    assert all(f.bodies[0].in_zone for f in source)
    shaken = list(shake(0.5, 1.0, calibration=right)(iter(source)))
    assert all(f.bodies[0].in_zone for f in shaken)
    with pytest.raises(ValueError, match="calibration"):                    # owner decision Q9: no silent default zone
        list(shake(0.5, 1.0)(iter(source)))


def test_degrade_needs_the_scene_calibration():
    # C13: degrade (and shake, owner decision Q9) placed noisy bodies against the default zone whatever
    # the scene used.
    right = Calibration(zone=(0.5, 0.2, 1.0, 0.8))
    source = list(scene(persons=[Person(0.85)], ticks=60, calibration=right))
    with pytest.raises(ValueError, match="calibration"):
        list(degrade(iter(source)))
    kept = list(degrade(iter(source), keypoint_dropout=0.0, jitter=0.0, calibration=right))
    assert all(f.bodies[0].in_zone for f in kept[5:]) and kept[8].bodies == source[3].bodies
    noisy = list(degrade(iter(source), calibration=right))
    assert sum(f.bodies[0].in_zone for f in noisy[5:]) >= 0.9 * 55
    unplaced = [Sensed(t=i * TICK, bodies=(Person().body_at(i * TICK, 0),)) for i in range(6)]
    with pytest.raises(ValueError, match="place"):
        list(degrade(iter(unplaced)))
    # Calibrations that differ from the default in one placement field each: min_height moves in_zone
    # alone, a wider zone zone_x alone, a taller one zone_y alone. degrade and shake catch every one.
    for cal, x in ((Calibration(min_height=0.3), 0.5), (Calibration(zone=(0.1, 0.2, 0.9, 0.8)), 0.4),
                   (Calibration(zone=(0.2, 0.1, 0.8, 0.9)), 0.5)):
        source = list(scene(persons=[Person(x, height=0.4)], ticks=12, calibration=cal))
        b, default = source[0].bodies[0], place(source[0].bodies[0], Calibration())
        differs = (b.in_zone != default.in_zone, b.zone_x != default.zone_x, b.zone_y != default.zone_y)
        assert sum(differs) == 1, (cal, differs)
        with pytest.raises(ValueError, match="calibration"):
            list(degrade(iter(source)))
        with pytest.raises(ValueError, match="calibration"):
            list(shake(0.0, 1.0)(iter(source)))
        assert len(list(degrade(iter(source), calibration=cal))) == 12
        assert len(list(shake(0.0, 1.0, calibration=cal)(iter(source)))) == 12
    # Every body is checked, not just the first: body 1 stands outside both zones, body 2 only in the scene's.
    source = list(scene(persons=[Person(0.1, id=1), Person(0.85, id=2)], ticks=12, calibration=right))
    with pytest.raises(ValueError, match="body 2"):
        list(degrade(iter(source)))
    with pytest.raises(ValueError, match="body 2"):
        list(shake(0.0, 1.0)(iter(source)))


def test_scene_refuses_duplicate_ids_and_crowd_takes_an_id_base():
    # C15: crowd always started at 100 and scene used the list index, so ids could collide.
    with pytest.raises(ValueError, match="duplicate body id 100"):
        scene(persons=[Person(), *crowd(2), *crowd(2)])
    with pytest.raises(ValueError, match="duplicate body id 0"):
        scene(persons=[Person(0.2), Person(0.5, id=0)])
    assert [p.id for p in crowd(3, id_base=200)] == [200, 201, 202]
    frames = list(scene(persons=[Person(), *crowd(2), *crowd(2, id_base=200)], ticks=1))
    assert sorted(b.id for b in frames[0].bodies) == [0, 100, 101, 200, 201]


def test_festival_guard_rails():
    # C16: headlamp blobs stay on the wall; camp_kick(0) is a ValueError; degrade keeps the detector box.
    assert all(0.0 <= b.x <= 1.0 for f in scene(blobs=headlamps(), ticks=600) for b in f.blobs)
    with pytest.raises(ValueError, match="bpm"):
        camp_kick(0)
    source = list(scene(persons=[walker()], ticks=30))
    for f in degrade(iter(source)):
        for b in f.bodies:
            truth = source[round(f.camera_t / TICK)].bodies[0]
            assert (b.box, b.scale, b.vx, b.vy) == (truth.box, truth.scale, truth.vx, truth.vy)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_actors.py tests/arcade/test_festival.py`
Expected: `5 failed, 29 passed`: `test_tempo_needs_a_positive_bpm` and `test_festival_guard_rails` (`ZeroDivisionError: float division by zero`), `test_shake_places_against_the_scene_calibration` (the changed line 180), `test_degrade_needs_the_scene_calibration` and `test_scene_refuses_duplicate_ids_and_crowd_takes_an_id_base` (`Failed: DID NOT RAISE ValueError`).

- [ ] **Step 3: Implement**

`arcade/sources/actors.py`:

```python
"""Scripted synthetic input for tests and tools (spec 6.4). Deterministic: no randomness, no wall clock."""
from __future__ import annotations

import dataclasses
import math
import zlib
from typing import Callable, Iterable, Iterator

import numpy as np

from arcade.calibration import Calibration
from arcade.poses import POSES
from arcade.sensed import (LEFT_ELBOW, LEFT_HIP, LEFT_SHOULDER, LEFT_WRIST, MOTION_GRID, REACH_TOP_TORSOS,
                           RIGHT_ELBOW, RIGHT_HIP, RIGHT_SHOULDER, RIGHT_WRIST, Audio, Blob, Body, Keypoint,
                           Sensed, place, place_blob)

TICK = 1 / 30
MAX_BLOBS = 8
_ARMS = {"left": (LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST), "right": (RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST)}

Offsets = tuple[tuple[float, float], ...]


def _points(cx: float, cy: float, h: float, offsets: Offsets, conf: float = 1.0) -> list[Keypoint]:
    return [Keypoint(cx + dx * h, cy + dy * h, conf) for dx, dy in offsets]


def make_keypoints(cx: float, cy: float, h: float, left_up: bool = False, right_up: bool = False,
                   conf: float = 1.0) -> tuple[Keypoint, ...]:
    """A standing figure with its hip centre at (cx, cy) and total height h, coordinates normalized."""
    offsets = list(POSES["stand"])
    for hand, up in (("left", left_up), ("right", right_up)):
        if up:
            for i in _ARMS[hand][1:]:
                offsets[i] = POSES["arms_up"][i]
    return tuple(_points(cx, cy, h, tuple(offsets), conf))


def body_box(keypoints: Iterable[Keypoint]) -> tuple[float, float, float, float]:
    xs = [k.x for k in keypoints]
    ys = [k.y for k in keypoints]
    clamp = lambda v: min(1.0, max(0.0, v))
    return (clamp(min(xs) - 0.02), clamp(min(ys) - 0.02), clamp(max(xs) + 0.02), clamp(max(ys) + 0.02))


def _check_hand(hand: str) -> None:
    if hand not in _ARMS:
        raise ValueError(f"hand must be 'left' or 'right', got {hand!r}")


class Person:
    """A scripted body. Every method returns self so scripts chain. y is the hip height."""

    def __init__(self, x: float = 0.5, y: float = 0.55, height: float = 0.6, id: int | None = None):
        self.x0, self.y0, self.h, self.id = x, y, height, id
        self._moves: list[tuple[float, float, float, float]] = []
        self._hands: list[tuple[float, float, str]] = []
        self._wrists: list[tuple[float, float, str, float, float]] = []
        self._poses: list[tuple[float, float, str]] = []
        self._jumps: list[tuple[float, float, float]] = []
        self._arrive = 0.0
        self._leave: float | None = None

    def _x_at(self, t: float) -> float:
        x = self.x0
        for t0, t1, xa, xb in self._moves:
            if t >= t1:
                x = xb
            elif t0 <= t < t1:
                x = xa + (xb - xa) * (t - t0) / (t1 - t0)
        return x

    def _lift_at(self, t: float) -> float:
        lift = 0.0
        for at, seconds, height in self._jumps:
            if at <= t < at + seconds:
                u = (t - at) / seconds
                lift = max(lift, height * 4 * u * (1 - u))
        return lift

    def walk(self, x_to: float, seconds: float, at: float | None = None) -> "Person":
        t0 = (self._moves[-1][1] if self._moves else 0.0) if at is None else at
        self._moves.append((t0, t0 + seconds, self._x_at(t0), x_to))
        return self

    def raise_hand(self, at: float, seconds: float = 0.5, hand: str = "right") -> "Person":
        _check_hand(hand)
        self._hands.append((at, at + seconds, hand))
        return self

    def both_hands_up(self, at: float, seconds: float) -> "Person":
        self._hands.append((at, at + seconds, "both"))
        return self

    def wrist(self, hand: str, y_from: float, y_to: float, seconds: float, at: float | None = None) -> "Person":
        """Move one wrist from y_from to y_to in reach-box v units (0 top, 1 hip height) over seconds.

        The wrist follows the script during [at, at + seconds) and hangs at the side outside it. With at
        None it starts where this hand's last wrist script ended, or at 0.
        """
        _check_hand(hand)
        if at is None:
            ends = [t1 for _, t1, h, _, _ in self._wrists if h == hand]
            at = ends[-1] if ends else 0.0
        self._wrists.append((at, at + seconds, hand, y_from, y_to))
        return self

    def pose(self, name: str, at: float, seconds: float) -> "Person":
        """Hold POSES[name] during [at, at + seconds)."""
        if name not in POSES:
            raise ValueError(f"unknown pose {name!r}; known: {', '.join(sorted(POSES))}")
        self._poses.append((at, at + seconds, name))
        return self

    def jump(self, at: float, height: float = 0.15, seconds: float = 0.6) -> "Person":
        self._jumps.append((at, seconds, height))
        return self

    def leave(self, at: float) -> "Person":
        self._leave = at
        return self

    def arrive(self, at: float) -> "Person":
        self._arrive = at
        return self

    def present(self, t: float) -> bool:
        return t >= self._arrive and (self._leave is None or t < self._leave)

    def _offsets_at(self, t: float) -> list[tuple[float, float]]:
        offsets = list(POSES["stand"])
        for t0, t1, name in self._poses:
            if t0 <= t < t1:
                offsets = list(POSES[name])
        for t0, t1, hand in self._hands:
            if t0 <= t < t1:
                for side in ("left", "right") if hand == "both" else (hand,):
                    for i in _ARMS[side][1:]:
                        offsets[i] = POSES["arms_up"][i]
        return offsets

    def _keypoints_at(self, t: float) -> list[Keypoint]:
        cx, cy = self._x_at(t), self.y0 - self._lift_at(t)
        offsets = self._offsets_at(t)
        pts = _points(cx, cy, self.h, tuple(offsets))
        for t0, t1, hand, y_from, y_to in self._wrists:
            if t0 <= t < t1:
                v = y_from + (y_to - y_from) * (t - t0) / (t1 - t0)
                shoulder, elbow, wrist = _ARMS[hand]
                # The reach box of sensed.Body.reach, from the pose offsets rather than the keypoints, so a
                # body partly out of frame (keypoints clamped with confidence 0) still has one.
                sx, sy = [(a + b) / 2 for a, b in zip(offsets[LEFT_SHOULDER], offsets[RIGHT_SHOULDER])]
                hx, hy = [(a + b) / 2 for a, b in zip(offsets[LEFT_HIP], offsets[RIGHT_HIP])]
                top = cy + (sy - REACH_TOP_TORSOS * math.hypot(sx - hx, sy - hy)) * self.h
                y = top + v * (cy + hy * self.h - top)
                pts[wrist] = Keypoint(pts[wrist].x, y)
                pts[elbow] = Keypoint((pts[shoulder].x + pts[wrist].x) / 2, (pts[shoulder].y + y) / 2)
        return pts

    def _anchor_at(self, t: float) -> tuple[float, float]:
        return self._x_at(t), self.y0 - self._lift_at(t)

    def body_at(self, t: float, id: int) -> Body:
        kps = tuple(self._keypoints_at(t))
        (x1, y1), (x0, y0) = self._anchor_at(t), self._anchor_at(t - TICK)
        return Body(self.id if self.id is not None else id, body_box(kps), kps,
                    vx=(x1 - x0) / TICK, vy=(y1 - y0) / TICK)


BlobScript = Callable[[float], Blob | None]
MotionScript = Callable[[float], np.ndarray | None]
AudioScript = Callable[[float], Audio]


def moving_blob(x0: float, y0: float, x1: float, y1: float, seconds: float,
                color: tuple[int, int, int] = (255, 255, 255), size: float = 0.03,
                start: float = 0.0) -> BlobScript:
    def script(t: float) -> Blob | None:
        if t < start or t > start + seconds:
            return None
        u = (t - start) / seconds if seconds > 0 else 1.0
        return Blob(x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, size, color)
    return script


def motion_rect(x0: float, y0: float, x1: float, y1: float, start: float, seconds: float) -> MotionScript:
    """Motion cells lit over a rectangle during [start, start + seconds), on the 128x64 grid.

    The rectangle is in fractions of the motion grid, which covers the calibrated zone at the wall's
    aspect (spec 5), not in the camera coordinates Person(x) uses: x 0.5 is the middle of the zone.
    """
    w, h = MOTION_GRID
    c0, r0 = int(x0 * w), int(y0 * h)
    c1, r1 = max(c0 + 1, math.ceil(x1 * w)), max(r0 + 1, math.ceil(y1 * h))
    grid = np.zeros((h, w), bool)
    grid[max(r0, 0):min(r1, h), max(c0, 0):min(c1, w)] = True

    def script(t: float) -> np.ndarray | None:
        return grid.copy() if start <= t < start + seconds else None
    return script


def silence() -> AudioScript:
    return lambda t: Audio()


def loud(level: float) -> AudioScript:
    return lambda t: Audio(level=level, level_smooth=level, peak=level)


def level_ramp(points: list[tuple[float, float]]) -> AudioScript:
    """level (and level_smooth and peak) interpolated linearly between (t, level) points, ends held."""
    if not points or any(b[0] < a[0] for a, b in zip(points, points[1:])):
        raise ValueError(f"level_ramp needs (t, level) points in time order, got {points!r}")

    def script(t: float) -> Audio:
        level = points[0][1] if t <= points[0][0] else points[-1][1]
        for (ta, la), (tb, lb) in zip(points, points[1:]):
            if ta <= t < tb:
                level = la + (lb - la) * (t - ta) / (tb - ta)
                break
        return Audio(level=level, level_smooth=level, peak=level)
    return script


def _fires(t: float, when: float) -> bool:
    """Exactly one tick per event: the first tick at or after it."""
    return when - 1e-9 <= t < when + TICK - 1e-9


def claps(times: list[float]) -> AudioScript:
    def script(t: float) -> Audio:
        hit = any(_fires(t, c) for c in times)
        return Audio(level=0.8 if hit else 0.05, level_smooth=0.8 if hit else 0.05,
                     peak=1.0 if hit else 0.05, clap=hit, onset=hit)
    return script


def tempo(bpm: float, start: float = 0.0) -> AudioScript:
    if not 0.0 < bpm < math.inf:
        raise ValueError(f"tempo needs a bpm over 0, got {bpm!r}")
    period = 60.0 / bpm

    def script(t: float) -> Audio:
        n = math.floor((t - start) / period + 1e-9)
        hit = t >= start - 1e-9 and _fires(t, start + n * period)
        return Audio(level=0.6 if hit else 0.3, level_smooth=0.6 if hit else 0.3, peak=0.9 if hit else 0.3,
                     onset=hit, beat=hit, bpm=bpm)
    return script


def scene(persons: Iterable[Person] = (), blobs: Iterable[BlobScript] = (), motion: Iterable[MotionScript] = (),
          audio: AudioScript | None = None, ticks: int = 90,
          calibration: Calibration | None = None) -> Iterator[Sensed]:
    """Sensed records at 30 Hz with a fresh camera frame every tick, as a perfect 30 fps camera gives.

    A person without an id gets its index in persons; two persons with one id raise ValueError here,
    before the first frame, because the tracker never gives two bodies one id and degrade keys its noise
    on it. Bodies are placed against the calibration (the default one when None) and sorted largest
    scale first; blobs are placed, kept in script order (a Blob has no brightness to sort by) and capped
    at 8; motion scripts are ORed on the 128x64 grid.
    """
    persons, blobs, motion = list(persons), list(blobs), list(motion)
    ids = [p.id if p.id is not None else idx for idx, p in enumerate(persons)]
    for body_id in ids:
        if ids.count(body_id) > 1:
            raise ValueError(f"duplicate body id {body_id} in scene: give crowd() an id_base or Person an id")
    return _frames(persons, ids, blobs, motion, audio or silence(), ticks, calibration or Calibration())


def _frames(persons: list[Person], ids: list[int], blobs: list[BlobScript], motion: list[MotionScript],
            audio: AudioScript, ticks: int, cal: Calibration) -> Iterator[Sensed]:
    w, h = MOTION_GRID
    for i in range(ticks):
        t = i * TICK
        bodies = [place(p.body_at(t, body_id), cal) for p, body_id in zip(persons, ids) if p.present(t)]
        bodies.sort(key=lambda b: -b.scale)
        lights = tuple(place_blob(b, cal) for b in (s(t) for s in blobs) if b is not None)[:MAX_BLOBS]
        grid = np.zeros((h, w), bool)
        for script in motion:
            cells = script(t)
            if cells is not None:
                if cells.shape != (h, w):
                    raise ValueError(f"a motion script returned shape {cells.shape}, not {(h, w)}")
                grid |= cells
        yield Sensed(t=t, camera_t=t, camera_fresh=True, camera_seq=i + 1, bodies=tuple(bodies),
                     blobs=lights, motion=grid, audio=audio(t))


# Festival scenes (spec 6.4, 9.3): what a burn puts in front of the camera and microphone.

def crowd(n: int, start: float = 0.0, id_base: int = 100) -> list[Person]:
    """n small people behind the player: 0.3 tall, so under the zone's min_height, drifting and waving.

    Their ids are id_base, id_base + 1, ...; a second crowd in one scene needs another id_base."""
    people = []
    for i in range(n):
        x = (i + 0.5) / n
        p = Person(x, y=0.35, height=0.3, id=id_base + i)
        p.walk(min(1.0, x + 0.04), 3.0, at=start + 0.4 * i).walk(x, 3.0)
        p.raise_hand(at=start + 1.0 + 0.7 * i, seconds=0.8, hand="left" if i % 2 else "right")
        people.append(p)
    return people


def headlamps(period: float = 20.0, cross_seconds: float = 6.0) -> tuple[BlobScript, BlobScript]:
    """A headlamp parked at the top left, and one crossing the top of the frame every period seconds.

    Both stay above the default zone (y under 0.2), so games never see them. Blob clamps x to 0..1, so the
    crossing lamp sits on the edge column for its first and last 0.27 s instead of leaving the frame; it is
    out of the zone there, and a real blob source never reports a light outside the frame."""
    parked = lambda t: Blob(0.05, 0.15, 0.02, (255, 244, 214))

    def crossing(t: float) -> Blob | None:
        u = (t % period) / cross_seconds
        return Blob(-0.05 + 1.1 * u, 0.1, 0.02, (255, 250, 235)) if u < 1.0 else None
    return parked, crossing


def camp_kick(bpm: float = 125.0, start: float = 0.0) -> AudioScript:
    """A neighbouring camp's kick drum: broadband onsets on the beat, no claps, voice at the floor."""
    beat = tempo(bpm, start)

    def script(t: float) -> Audio:
        hit = beat(t).beat
        level = 0.7 if hit else 0.45
        return Audio(level=level, level_smooth=0.55, peak=0.95 if hit else 0.5, voice_db=-42.0,
                     floor_db=-42.0, voice=0.0, clap=False, onset=hit, beat=hit, bpm=bpm)
    return script


def wind(gust_every: float = 2.7) -> AudioScript:
    """Wind on the microphone: a slow swell with an onset at each gust peak, never a clap or a voice."""
    def script(t: float) -> Audio:
        level = 0.3 + 0.2 * math.sin(2 * math.pi * t / 7.0) ** 2
        gust = _fires(t, gust_every * math.floor(t / gust_every + 1e-9))
        return Audio(level=level, level_smooth=level, peak=min(1.0, level + (0.3 if gust else 0.05)),
                     voice_db=-58.0, floor_db=-60.0, voice=2.0 / 30, onset=gust)
    return script


def _unit(tag: str, tick: int, body_id: int, joint: int) -> float:
    """A fixed pseudo-random number in [0, 1) for this tag, tick, body and joint (never hash() or random)."""
    return zlib.crc32(f"{tag}:{tick}:{body_id}:{joint}".encode()) / 2**32


def _noisy(body: Body, tick: int, tag: str, dropout: float, jitter: float) -> Body:
    """body with its keypoints dropped and jittered. box, scale, vx and vy are kept: the box stands for the
    detector's box, which does not lose a joint, and scale and velocity come from the tracker (core
    Task 16), which smooths them over captures. Re-placing is the caller's job."""
    pts = []
    for j, k in enumerate(body.keypoints):
        x = k.x + (2 * _unit(tag + "x", tick, body.id, j) - 1) * jitter
        y = k.y + (2 * _unit(tag + "y", tick, body.id, j) - 1) * jitter
        conf = 0.0 if _unit(tag + "drop", tick, body.id, j) < dropout else k.conf
        pts.append(Keypoint(x, y, conf))
    return dataclasses.replace(body, keypoints=tuple(pts))


def _placed_by(body: Body, cal: Calibration) -> bool:
    """Whether body's in_zone, zone_x and zone_y are what place(body, cal) gives."""
    again = place(body, cal)
    return (again.in_zone, again.zone_x, again.zone_y) == (body.in_zone, body.zone_x, body.zone_y)


def _require_placed(bodies: Iterable[Body], cal: Calibration, who: str, t: float) -> None:
    """Raises ValueError unless cal reproduces every body's placement: re-placing noisy bodies against
    another calibration would move the zone silently (C13)."""
    for b in bodies:
        if not _placed_by(b, cal):
            raise ValueError(f"{who}: body {b.id} at t={t:.3f} was not placed against this calibration; "
                             f"pass the scene's calibration= (and place() every body)")


def shake(start: float, seconds: float, jitter: float = 0.03,
          calibration: Calibration | None = None) -> Callable[[Iterable[Sensed]], Iterator[Sensed]]:
    """What the gated camera source yields while the wall or pole shakes: an empty motion grid and
    keypoints jittered by up to 0.03, during [start, start + seconds). Wraps a scene.

    Jittered bodies are placed again against calibration (the default one when None), which must be the
    scene's: a body in the window whose placement it does not reproduce raises ValueError (owner
    decision Q9), as in degrade."""
    def wrap(frames: Iterable[Sensed]) -> Iterator[Sensed]:
        cal = calibration or Calibration()
        for i, s in enumerate(frames):
            if start - 1e-9 <= s.t < start + seconds - 1e-9:
                _require_placed(s.bodies, cal, "shake", s.t)
                bodies = tuple(place(_noisy(b, i, "shake", 0.0, jitter), cal) for b in s.bodies)
                s = dataclasses.replace(s, bodies=bodies, motion=np.zeros((0, 0), bool))
            yield s
    return wrap


def degrade(frames: Iterable[Sensed], fps: float = 10, latency: float = 0.15, keypoint_dropout: float = 0.15,
            jitter: float = 0.01, calibration: Calibration | None = None) -> Iterator[Sensed]:
    """Perfect 30 Hz input turned into what the Pi camera gives (spec 6.4).

    The camera captures at fps; capture k is taken at k / fps from the scene's frame at or before that
    time and becomes visible latency seconds later, then holds until the next one. Each keypoint of a
    capture is dropped (confidence 0) with probability keypoint_dropout and moved by up to jitter,
    keyed by zlib.crc32 of (tick, body id, joint). Audio and t stay on the current tick.

    Noisy bodies are placed again against calibration (the default one when None), which must be the
    one the input was placed with: a captured body whose placement that calibration does not reproduce
    (a scene built with another zone, or a body never placed) raises ValueError rather than moving the
    zone silently.
    """
    if not fps > 0 or not latency >= 0 or not 0 <= keypoint_dropout <= 1 or not jitter >= 0:
        raise ValueError(f"degrade needs fps > 0, latency >= 0, dropout in [0, 1], jitter >= 0; got "
                         f"{fps}, {latency}, {keypoint_dropout}, {jitter}")
    cal = calibration or Calibration()
    seen: dict[int, Sensed] = {}             # scene frames not yet captured, by tick
    held: tuple[int, Sensed] | None = None
    for i, s in enumerate(frames):
        if abs(s.t - i * TICK) > 1e-6:   # a sliced or offset stream would silently lose its latency
            raise ValueError(f"degrade needs a 30 Hz scene that starts at t=0; frame {i} has t={s.t}")
        seen[i] = s
        k = math.floor((s.t - latency) * fps + 1e-9)
        if k < 0:
            yield dataclasses.replace(s, camera_t=0.0, camera_fresh=False, camera_seq=0, bodies=(), blobs=(),
                                      motion=np.zeros((0, 0), bool))
            continue
        fresh = held is None or held[0] != k
        if fresh:
            src = min(math.floor(k / fps / TICK + 1e-9), i)
            shot = seen[src]
            for old in [j for j in seen if j < src]:
                del seen[old]
            _require_placed(shot.bodies, cal, "degrade", shot.t)
            bodies = tuple(place(_noisy(b, src, "degrade", keypoint_dropout, jitter), cal) for b in shot.bodies)
            held = (k, dataclasses.replace(shot, bodies=bodies))
        shot = held[1]
        yield dataclasses.replace(s, camera_t=shot.t, camera_fresh=fresh, camera_seq=k + 1, bodies=shot.bodies,
                                  blobs=shot.blobs, motion=shot.motion)


REAL_NOISE = {"fps": 10, "latency": 0.15, "keypoint_dropout": 0.15, "jitter": 0.01}   # refit from the real fixtures (spec 9.5)
```

- [ ] **Step 4: Run the tests**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_actors.py tests/arcade/test_festival.py`
Expected: `34 passed` (17, 17).

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`
Expected: `190 passed`, no skips.

- [ ] **Step 5: Commit**

```bash
git add arcade/sources/actors.py tests/arcade/test_actors.py tests/arcade/test_festival.py
git commit -m "fix(arcade): degrade and shake check the scene calibration, unique scene ids with a crowd id_base, tempo needs a positive bpm (it02 C13, C15, C16)" -m "owner decision Q9: shake raises ValueError on a missing or mismatched calibration, so test_festival.py:180 changes from asserting the silent default-zone fallback to pytest.raises(ValueError). No other existing assert changed; test_festival's import line gains Sensed and place."
```

---

### Task 3: Canvas (core plan Task 5 with its amendment)

**Files:**
- Create: `arcade/canvas.py`
- Test: `tests/arcade/conftest.py`, `tests/arcade/test_canvas.py`

**Interfaces:**
- Consumes: `Font`, `CELL_W`, `CELL_H` from `show.font`.
- Produces: `Canvas(width, height, font)` with `.frame` (the `(h, w, 3)` uint8 array), `.width`, `.height`, `.font`, `.size -> (width, height)`, `clear(color=(0, 0, 0))`, `pixel(x, y, color)`, `line(x0, y0, x1, y1, color)`, `rect(x, y, w, h, color)`, `fill_rect(x, y, w, h, color)`, `circle(cx, cy, r, color)`, `fill_circle(cx, cy, r, color)`, `blit(mask, x, y, color)`, `blit_rgb(sprite, x, y)` (black is transparent), `text(x, y, s, color, scale=1) -> int` (the width, `text_width(s, scale)`), `text_width(s, scale=1) -> int`, and `Canvas.sprite_from_rows`; module function `sprite_from_rows(rows: list[str], palette: dict[str, Color]) -> np.ndarray` `(h, w, 3)` uint8 (`.` is black; an unknown character or unequal rows raise `ValueError`). Coordinates may be int or float and are rounded; colours are clamped to 0..255. Out-of-range drawing clips, never raises, never hangs.
- Test fixtures (`tests/arcade/conftest.py`): `font5x7` (session, the real font) and `size` (parametrized `(128, 32)` and `(64, 64)`).

- [ ] **Step 1: Write the fixtures and the failing tests**

`tests/arcade/conftest.py`:

```python
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from show.font import Font

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def font5x7() -> Font:
    return Font.load(ROOT / "fonts" / "5x7.bin")


@pytest.fixture(params=[(128, 32), (64, 64)], ids=["128x32", "64x64"])
def size(request) -> tuple[int, int]:
    return request.param
```

`tests/arcade/test_canvas.py`:

```python
import contextlib
import math
import signal
import threading
import time
import warnings

import numpy as np
import pytest

from arcade.canvas import Canvas, sprite_from_rows

RED = (255, 0, 0)


def lit(c: Canvas) -> int:
    return int((c.frame.max(axis=2) > 0).sum())


@contextlib.contextmanager
def deadline(seconds: float):
    """Fails a block that runs past seconds instead of hanging the suite (05-plan S4's infinite line).

    It replaces any outer SIGALRM timer while it runs. Off the main thread, or where there is no setitimer
    (Windows), it just runs the block."""
    if threading.current_thread() is not threading.main_thread() or not hasattr(signal, "setitimer"):
        yield
        return
    def expired(signum, frame):
        raise TimeoutError(f"still running after {seconds} s")
    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def test_new_canvas_is_black_and_sized(font5x7, size):
    c = Canvas(*size, font5x7)
    assert c.frame.shape == (size[1], size[0], 3) and c.frame.dtype == np.uint8
    assert c.size == size and lit(c) == 0


def test_pixel_and_clipping(font5x7):
    c = Canvas(16, 8, font5x7)
    c.pixel(3, 2, RED)
    c.pixel(-1, 0, RED)
    c.pixel(16, 8, RED)
    assert lit(c) == 1 and tuple(c.frame[2, 3]) == RED


def test_rects_and_clear(font5x7):
    c = Canvas(16, 8, font5x7)
    c.fill_rect(2, 1, 4, 3, RED)
    assert lit(c) == 12
    c.clear()
    c.rect(0, 0, 16, 8, RED)
    assert lit(c) == 2 * 16 + 2 * 6
    c.fill_rect(10, 4, 100, 100, RED)
    assert lit(c) == 2 * 16 + 2 * 6 + (6 * 4 - 6 - 3)


def test_line_and_circles(font5x7):
    c = Canvas(16, 16, font5x7)
    c.line(0, 0, 15, 15, RED)
    assert lit(c) == 16 and tuple(c.frame[7, 7]) == RED
    c.clear()
    c.fill_circle(8, 8, 3, RED)
    n_fill = lit(c)
    assert 25 <= n_fill <= 37 and tuple(c.frame[8, 8]) == RED
    c.clear()
    c.circle(8, 8, 3, RED)
    assert 12 <= lit(c) < n_fill and tuple(c.frame[8, 8]) == (0, 0, 0)
    c.circle(0, 0, 40, RED)


def test_text_uses_font_and_clips(font5x7):
    c = Canvas(32, 8, font5x7)
    assert c.text_width("AB") == 12
    w = c.text(0, 0, "A", RED)
    assert w == 6 and lit(c) > 5
    a = c.frame.copy()
    c.clear()
    c.text(30, 0, "A", RED)
    assert lit(c) < lit_of(a)
    c.clear()
    c.text(0, 0, "☃", RED)
    assert lit(c) > 0


def lit_of(frame: np.ndarray) -> int:
    return int((frame.max(axis=2) > 0).sum())


def test_float_coordinates_round(font5x7):
    c = Canvas(16, 8, font5x7)
    c.pixel(2.5, 0.5, RED)                          # half rounds up: a 0.5 px step moves every tick
    c.pixel(np.float32(5.4), np.int64(3), RED)
    assert tuple(c.frame[1, 3]) == RED and tuple(c.frame[3, 5]) == RED and lit(c) == 2
    c.clear()
    c.fill_rect(1.2, 1.2, 2.6, 2.6, RED)            # x 1, y 1, 3 by 3
    assert lit(c) == 9 and c.frame[1:4, 1:4, 0].all()
    c.clear()
    c.fill_circle(8.4, 4.4, 1.6, RED)               # centre (8, 4), radius 2
    assert tuple(c.frame[4, 8]) == RED and tuple(c.frame[4, 10]) == RED and tuple(c.frame[4, 11]) == (0, 0, 0)
    c.clear()
    c.blit(np.ones((2, 2), bool), 0.6, 0.4, RED)    # at (1, 0)
    c.text(9.5, 0.2, "I", RED)                      # at (10, 0)
    assert c.frame[0:2, 1:3, 0].all() and not c.frame[:, 0].any() and c.frame[:, 10:16].any()
    c.clear()
    c.text(0, 0.5, "I", RED)                        # at (0, 1): text rounds as pixel does
    one = Canvas(16, 8, font5x7)
    one.text(0, 1, "I", RED)
    assert np.array_equal(c.frame, one.frame)
    c.clear()
    c.text(-1, 0, "B", RED)                         # scrolling in from the left: B's four visible columns
    b = Canvas(16, 8, font5x7)
    b.text(5, 0, "B", RED)
    assert c.frame[:, 0:4].any() and np.array_equal(c.frame[:, 0:4], b.frame[:, 6:10])


def test_nan_inf_and_huge_never_raise_or_hang(font5x7):
    c = Canvas(64, 32, font5x7)
    nan, inf = math.nan, math.inf
    sprite = np.full((4, 4, 3), 200, np.uint8)
    c.text(0, 0, "A", RED)                          # build the font atlas before timing
    calls = [
        lambda: c.pixel(nan, 3, RED), lambda: c.pixel(inf, -inf, RED), lambda: c.pixel(10**12, 5, RED),
        lambda: c.pixel(None, "x", RED), lambda: c.pixel(10**400, 0, RED),
        lambda: c.line(0, 0, nan, 5, RED), lambda: c.line(0, 0, 10**9, 0, RED),
        lambda: c.line(-inf, 0, inf, 0, RED), lambda: c.line(0, 0, 1e300, -1e300, RED),
        lambda: c.fill_rect(nan, 0, 5, 5, RED), lambda: c.fill_rect(0, 0, 10**9, 10**9, RED),
        lambda: c.rect(nan, nan, nan, nan, RED), lambda: c.rect(-10**9, -10**9, 2 * 10**9, 2 * 10**9, RED),
        lambda: c.circle(5, 5, 10**9, RED), lambda: c.fill_circle(nan, nan, 3, RED),
        lambda: c.fill_circle(5, 5, inf, RED), lambda: c.fill_circle(10**9, 10**9, 10**9, RED),
        lambda: c.fill_circle(5, 5, 1e200, RED),       # (r + 0.5) ** 2 overflows a float unless _i clamps
        lambda: c.blit(np.ones((3, 3), bool), nan, 0, RED), lambda: c.blit_rgb(sprite, inf, 0),
        lambda: c.blit_rgb(sprite, -10**9, 10**9),
        lambda: c.text(nan, 0, "HI", RED), lambda: c.text(0, 0, "HI", RED, scale=10**9),
        lambda: c.text(0, 0, "X" * 10000, RED, scale=2), lambda: c.text(-10**6, 0, "X" * 10000, RED),
        lambda: c.text(0, inf, "HI", RED, scale=nan),
    ]
    for i, call in enumerate(calls):
        start = time.perf_counter()
        with deadline(1.0):
            call()
        assert time.perf_counter() - start < 0.05, f"call {i} took too long"
    assert c.frame.shape == (32, 64, 3) and c.frame.dtype == np.uint8
    e = Canvas(16, 8, font5x7)
    e.rect(3, 0, 0, 4, RED)                         # a health bar at width 0 draws nothing
    e.rect(10, 0, -3, 4, RED)
    e.fill_rect(0, 0, inf, 4, RED)                  # an infinite width lands at -_FAR: nothing
    assert lit(e) == 0


def test_colours_clamped(font5x7):
    c = Canvas(16, 8, font5x7)
    c.pixel(0, 0, (300, -5, 127.6))
    assert tuple(c.frame[0, 0]) == (255, 0, 128)
    c.fill_rect(1, 0, 1, 1, (math.nan, math.inf, -math.inf))
    assert tuple(c.frame[0, 1]) == (0, 255, 0)
    c.line(0, 2, 3, 2, (np.int64(999), np.float32(-1), 7))
    assert tuple(c.frame[2, 3]) == (255, 0, 7)
    c.text(0, 3, "I", (999, 0, 0))
    assert c.frame[3:8, :, 0].max() == 255
    c.clear((256, 256, 256))
    assert (c.frame == 255).all()
    c.clear()
    with warnings.catch_warnings():
        warnings.simplefilter("error")              # a NaN never reaches a byte cast
        c.blit_rgb(np.array([[[300.0, 127.6, 0.4], [np.nan, 0, 0], [-5, 0, 0], [np.inf, 0, 0]]], np.float32), 0, 5)
        c.blit_rgb(np.array([[[300, 0, 0], [-1, 0, 0]]], np.int64), 0, 6)
        c.blit_rgb(np.array([[[0.5, 126.5, 2.5]]], np.float32), 0, 7)
    assert [tuple(p) for p in c.frame[5, :4]] == [(255, 128, 0), (0, 0, 0), (0, 0, 0), (255, 0, 0)]
    assert [tuple(p) for p in c.frame[6, :2]] == [(255, 0, 0), (0, 0, 0)]   # a paint buffer clamps, never wraps
    assert tuple(c.frame[7, 0]) == (1, 127, 3)                               # half up, as coordinates round


def test_line_with_float_endpoint_terminates(font5x7):
    c = Canvas(16, 8, font5x7)
    start = time.perf_counter()
    with deadline(1.0):
        c.line(0, 0, 10.5, 0, RED)                  # used to step past 10.5 forever
    assert time.perf_counter() - start < 0.05
    assert lit(c) == 12 and c.frame[0, :12, 0].all()
    c.clear()
    c.line(0.4, 0.6, 7.6, 3.4, RED)                 # (0, 1) to (8, 3)
    assert tuple(c.frame[1, 0]) == RED and tuple(c.frame[3, 8]) == RED and lit(c) == 9


def test_text_scale_two(font5x7):
    c = Canvas(32, 16, font5x7)
    assert c.text_width("8", scale=2) == 12 and c.text_width("88", scale=2) == 24
    one = Canvas(32, 16, font5x7)
    one.text(0, 0, "8", RED)
    assert c.text(0, 0, "8", RED, scale=2) == 12
    assert lit(c) == 4 * lit(one)
    big, small = c.frame[:16, :12, 0] > 0, one.frame[:8, :6, 0] > 0
    assert np.array_equal(big, small.repeat(2, axis=0).repeat(2, axis=1))    # 2 px strokes
    rows, cols = np.nonzero(c.frame[:, :, 0])
    assert rows.max() - rows.min() + 1 == 14 and cols.max() - cols.min() + 1 == 10   # the 5x7 glyph at 10x14
    num = Canvas(32, 16, font5x7)
    assert num.text(0, 0, 8, RED, scale=2) == 12 and np.array_equal(num.frame, c.frame)   # numbers are drawn as str


def test_blit_rgb_black_is_transparent(font5x7):
    c = Canvas(8, 8, font5x7)
    c.clear((0, 0, 255))
    sprite = np.array([[[255, 0, 0], [0, 0, 0]], [[0, 0, 0], [0, 255, 0]]], np.uint8)
    c.blit_rgb(sprite, 1, 1)
    assert tuple(c.frame[1, 1]) == (255, 0, 0) and tuple(c.frame[2, 2]) == (0, 255, 0)
    assert tuple(c.frame[1, 2]) == (0, 0, 255) and tuple(c.frame[2, 1]) == (0, 0, 255)   # black showed through
    c.clear()
    c.blit_rgb(sprite, -1, 6.6)                     # at (-1, 7): only the black top-right cell is on-canvas
    c.blit_rgb(sprite, 6.5, -1)                     # at (7, -1): only the black bottom-left cell is on-canvas
    assert lit(c) == 0
    c.blit_rgb(sprite, 7, 7)
    assert lit(c) == 1 and tuple(c.frame[7, 7]) == (255, 0, 0)


def test_sprite_from_rows_palette():
    s = sprite_from_rows(["R.", ".G"], {"R": (255, 0, 0), "G": (0, 300, 0)})
    assert s.shape == (2, 2, 3) and s.dtype == np.uint8
    assert tuple(s[0, 0]) == (255, 0, 0) and tuple(s[1, 1]) == (0, 255, 0)            # clamped
    assert tuple(s[0, 1]) == (0, 0, 0) and tuple(s[1, 0]) == (0, 0, 0)
    assert sprite_from_rows([".R"], {".": (9, 9, 9), "R": RED})[0, 0].sum() == 0       # "." is always black
    with pytest.raises(ValueError, match="'X'"):
        sprite_from_rows(["RX"], {"R": RED})
    with pytest.raises(ValueError, match="length"):
        sprite_from_rows(["RR", "R"], {"R": RED})
    assert np.array_equal(Canvas.sprite_from_rows(["R"], {"R": RED}), sprite_from_rows(["R"], {"R": RED}))


def test_circle_is_the_one_pixel_rim_of_fill_circle(font5x7):
    for r in (1, 3, 6):
        ring, inner, disc = (Canvas(16, 16, font5x7) for _ in range(3))
        ring.circle(8, 8, r, RED)
        inner.fill_circle(8, 8, r - 1, RED)
        disc.fill_circle(8, 8, r, RED)
        rim, core, whole = (c.frame[:, :, 0] > 0 for c in (ring, inner, disc))
        assert not (rim & core).any() and np.array_equal(rim | core, whole), r


def test_blit_takes_any_mask_as_bool(font5x7):
    c = Canvas(8, 4, font5x7)
    c.blit(np.array([[1, 0], [0, 1]], np.uint8), 3, 0, RED)   # an int mask is a mask, not row indices
    assert lit(c) == 2 and tuple(c.frame[0, 3]) == RED and tuple(c.frame[1, 4]) == RED


def test_line_skip_starts_past_four_times_the_extent(font5x7):
    # Spec 7.4: a line whose endpoints exceed four times the canvas extent is skipped.
    c = Canvas(16, 8, font5x7)
    reach = 4 * (16 + 8)
    c.line(0, 0, reach, 0, RED)
    assert c.frame[0, :, 0].all()
    c.clear()
    c.line(0, 0, reach + 1, 0, RED)
    c.line(0, -reach - 1, 0, 7, RED)
    assert lit(c) == 0


@pytest.mark.parametrize("w,h", [(64, 32), (96, 48), (128, 64)])
def test_other_wall_sizes_draw_and_clip(font5x7, w, h):
    # Core Review Focus 3: a single panel at bring-up (64x32), or a wall of another size from config.
    c = Canvas(w, h, font5x7)
    c.text(w - 10, h - 8, "88", RED, scale=2)
    c.fill_circle(w - 1, h - 1, 5, RED)
    c.line(-5, h // 2, w + 5, h // 2, RED)
    c.rect(-1, -1, w + 2, h + 2, RED)
    c.blit_rgb(np.full((5, 5, 3), 90, np.uint8), w - 2, -2)
    assert c.frame.shape == (h, w, 3) and c.frame[h // 2, :, 0].all()
    assert c.text_width("88", scale=2) == 24 and lit(c) > w
```

- [ ] **Step 2: Run them to verify they fail**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_canvas.py`
Expected: collection error, `ModuleNotFoundError: No module named 'arcade.canvas'`.

- [ ] **Step 3: Implement**

`arcade/canvas.py`:

```python
"""Canvas (spec 7.4): drawing over a (height, width, 3) uint8 frame. Everything clips; nothing raises or hangs."""
from __future__ import annotations

import math

import numpy as np

from show.font import CELL_H, CELL_W, Font

Color = tuple[int, int, int]

_FAR = 1 << 20   # coordinates are clamped to plus or minus this; NaN, infinity and garbage land at -_FAR


def _i(v) -> int:
    """A coordinate as an int: rounded half up (so 0.5 px steps are even), clamped to plus or minus _FAR.

    NaN, infinity and anything that is not a number land at -_FAR (05-plan S4), so an infinite width draws
    nothing and an infinite (or negative) radius draws only the centre pixel, while a huge finite one fills:
    harmless either way, and nothing hangs."""
    try:
        return max(-_FAR, min(_FAR, math.floor(v + 0.5)))
    except (ValueError, OverflowError, TypeError):
        return -_FAR


def _channel(v) -> int:
    try:
        return max(0, min(255, math.floor(v + 0.5)))
    except OverflowError:
        return 255 if v > 0 else 0
    except (ValueError, TypeError):
        return 0


def _c(color) -> Color:
    """A colour as three ints clamped to 0..255; NaN is 0."""
    r, g, b = color
    return (_channel(r), _channel(g), _channel(b))


def sprite_from_rows(rows: list[str], palette: dict[str, Color]) -> np.ndarray:
    """An (h, w, 3) uint8 sprite from equal-length rows of palette characters; "." is always black."""
    lut = {**{k: _c(v) for k, v in palette.items()}, ".": (0, 0, 0)}
    widths = {len(r) for r in rows}
    if len(widths) > 1:
        raise ValueError(f"sprite rows differ in length: {sorted(widths)}")
    out = np.zeros((len(rows), widths.pop() if widths else 0, 3), np.uint8)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch not in lut:
                raise ValueError(f"sprite character {ch!r} at row {y}, column {x} is not in the palette")
            out[y, x] = lut[ch]
    return out


class Canvas:
    """Drawing over an (h, w, 3) uint8 frame. Coordinates may be int or float and are rounded; colours are
    clamped to 0..255. Out-of-range drawing clips, never raises, never hangs."""

    sprite_from_rows = staticmethod(sprite_from_rows)

    def __init__(self, width: int, height: int, font: Font):
        self.width, self.height = width, height
        self.font = font
        self.frame = np.zeros((height, width, 3), dtype=np.uint8)

    @property
    def size(self) -> tuple[int, int]:
        return (self.width, self.height)

    def clear(self, color: Color = (0, 0, 0)) -> None:
        self.frame[:] = _c(color)

    def pixel(self, x, y, color: Color) -> None:
        x, y = _i(x), _i(y)
        if 0 <= x < self.width and 0 <= y < self.height:
            self.frame[y, x] = _c(color)

    def fill_rect(self, x, y, w, h, color: Color) -> None:
        x, y, w, h = _i(x), _i(y), _i(w), _i(h)
        x0, y0 = max(x, 0), max(y, 0)
        x1, y1 = min(x + w, self.width), min(y + h, self.height)
        if x0 < x1 and y0 < y1:
            self.frame[y0:y1, x0:x1] = _c(color)

    def rect(self, x, y, w, h, color: Color) -> None:
        x, y, w, h = _i(x), _i(y), _i(w), _i(h)
        if w <= 0 or h <= 0:
            return
        self.fill_rect(x, y, w, 1, color)
        self.fill_rect(x, y + h - 1, w, 1, color)
        self.fill_rect(x, y, 1, h, color)
        self.fill_rect(x + w - 1, y, 1, h, color)

    def line(self, x0, y0, x1, y1, color: Color) -> None:
        """Bresenham. A line with an endpoint beyond four times the canvas extent is skipped (spec 7.4)."""
        x0, y0, x1, y1 = _i(x0), _i(y0), _i(x1), _i(y1)
        if max(abs(x0), abs(y0), abs(x1), abs(y1)) > 4 * (self.width + self.height):
            return
        color = _c(color)
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            if 0 <= x0 < self.width and 0 <= y0 < self.height:
                self.frame[y0, x0] = color
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def _disc(self, cx, cy, r, color: Color, ring: bool) -> None:
        cx, cy, r = _i(cx), _i(cy), max(_i(r), 0)
        x0, y0 = max(cx - r, 0), max(cy - r, 0)
        x1, y1 = min(cx + r + 1, self.width), min(cy + r + 1, self.height)
        if x0 >= x1 or y0 >= y1:
            return
        yy, xx = np.ogrid[y0:y1, x0:x1]
        d2 = (xx - cx) ** 2 + (yy - cy) ** 2
        mask = d2 <= (r + 0.5) ** 2
        if ring:
            mask &= d2 >= (r - 0.5) ** 2
        self.frame[y0:y1, x0:x1][mask] = _c(color)

    def fill_circle(self, cx, cy, r, color: Color) -> None:
        self._disc(cx, cy, r, color, ring=False)

    def circle(self, cx, cy, r, color: Color) -> None:
        self._disc(cx, cy, r, color, ring=True)

    def _window(self, h: int, w: int, x: int, y: int):
        """The on-canvas part of an h by w sprite at (x, y), as (frame slices, sprite slices), or None."""
        x0, y0 = max(x, 0), max(y, 0)
        x1, y1 = min(x + w, self.width), min(y + h, self.height)
        if x0 >= x1 or y0 >= y1:
            return None
        return (slice(y0, y1), slice(x0, x1)), (slice(y0 - y, y1 - y), slice(x0 - x, x1 - x))

    def blit(self, mask: np.ndarray, x, y, color: Color) -> None:
        """Lights the True cells of a bool mask in one colour."""
        mask = np.asarray(mask, bool)
        win = self._window(*mask.shape, _i(x), _i(y))
        if win is not None:
            dst, src = win
            self.frame[dst][mask[src]] = _c(color)

    def blit_rgb(self, sprite: np.ndarray, x, y) -> None:
        """Copies an (h, w, 3) sprite; black pixels are transparent. A sprite that is not uint8 (a game's
        float buffer) is rounded half up and clamped to 0..255 first, NaN to 0, so black is judged after."""
        sprite = np.asarray(sprite)
        if sprite.dtype != np.uint8:
            v = np.floor(np.nan_to_num(sprite.astype(np.float64), nan=0.0, posinf=255.0, neginf=0.0) + 0.5)
            sprite = np.clip(v, 0, 255).astype(np.uint8)
        win = self._window(*sprite.shape[:2], _i(x), _i(y))
        if win is not None:
            dst, src = win
            sub = sprite[src]
            lit = sub.any(axis=2)
            self.frame[dst][lit] = sub[lit]

    def _scale(self, scale) -> int:
        """Text scale as an int from 1 to the canvas's larger side (a bigger glyph cannot show)."""
        return max(1, min(_i(scale), max(self.width, self.height)))

    def text_width(self, s, scale=1) -> int:
        return CELL_W * self._scale(scale) * len(str(s))

    def text(self, x, y, s, color: Color, scale=1) -> int:
        """Draws s in the 5x7 font, each glyph pixel scale by scale (2 gives 10 by 14 with 2 px strokes);
        returns the width drawn, text_width(s, scale). Characters past 255 draw as "?"."""
        s, k = str(s), self._scale(scale)
        x, y, color = _i(x), _i(y), _c(color)
        cell_w = CELL_W * k
        if y >= self.height or y + CELL_H * k <= 0:
            return self.text_width(s, k)
        atlas = self.font.atlas()
        for i in range(max(0, -x // cell_w), len(s)):        # glyphs wholly off the left edge are skipped
            cx, ch = x + i * cell_w, s[i]
            if cx >= self.width:
                break
            if cx + cell_w <= 0:
                continue
            glyph = atlas[ord(ch) if ord(ch) < 256 else ord("?")]
            if k > 1:
                glyph = glyph.repeat(k, axis=0).repeat(k, axis=1)
            self.blit(glyph, cx, y, color)
        return self.text_width(s, k)
```

- [ ] **Step 4: Run the tests**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_canvas.py`
Expected: `19 passed`.

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`
Expected: `209 passed`, no skips.

- [ ] **Step 5: Commit**

```bash
git add arcade/canvas.py tests/arcade/conftest.py tests/arcade/test_canvas.py
git commit -m "feat(arcade): canvas drawing primitives with float coordinates, clamped colours, scaled text, blit_rgb and sprite_from_rows (core Task 5)" -m "blit_rgb rounds and clamps a sprite that is not uint8 before judging black (plan review B2)."
```

---

### Task 4: Look, the preview render modes (core plan Task 6 with its amendment)

**Files:**
- Create: `arcade/look.py`, `arcade/preview.py`
- Test: `tests/arcade/test_look.py`

**Interfaces:**
- Consumes: `Display` from `show.display`; `FakeDisplay` from `show.display.fake` (tests); `LOOKS` from `arcade.config` (tests).
- Produces: `MODES = ("plain", "led", "distance")`; `MONITOR_GAMMA = 2.2`; `gamma_lut(gamma: float) -> np.ndarray` `(256,)` uint8; `apply_gamma(frame, gamma) -> np.ndarray`; `distance_sigma(metres: float) -> float` (wall pixels); `render(frame, mode: str, scale: int = 8, gamma: float = 2.2, metres: float = 5.0) -> np.ndarray` of shape `(h * scale, w * scale, 3)` uint8, raising `ValueError` for an unknown mode, a frame that is not `(h, w, 3)` uint8, a scale that is not an integer (Python or numpy) of at least 1 or is a bool, a gamma not over 0 and finite, or metres not 0 or more and finite; `dim(image, level: float) -> np.ndarray`; `PreviewDisplay(inner: Display, mode, scale, gamma, metres=5.0)` implementing the `Display` protocol, with `.level` (starts 1.0). Arrays `gamma_lut` returns are cached and read-only: copy before editing. `look.py` imports only `math`, `functools`, `operator` and numpy.

Gamma direction (core plan): an uncorrected LED wall drives light output proportional to the byte value, so mid greys look brighter on the wall than the same bytes look on a monitor. To show that, the `led` preview maps `v -> 255 * (v/255) ** (1/gamma)`. With `gamma = 1.0` the preview shows the bytes as they are, which is right when the Colorlight card applies gamma itself. `distance` starts from the light that `led` preview shows (loop decision 9).

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_look.py`:

```python
import math
import statistics
import subprocess
import sys
import time
import warnings
import zlib
from pathlib import Path

import numpy as np
import pytest

import arcade.look as look
from arcade.config import LOOKS
from arcade.look import MODES, apply_gamma, distance_sigma, gamma_lut, render
from arcade.preview import PreviewDisplay
from show.display.fake import FakeDisplay

ROOT = Path(__file__).resolve().parents[2]


def frame_with_dot(w=8, h=4):
    f = np.zeros((h, w, 3), np.uint8)
    f[1, 2] = (128, 0, 0)
    return f


def test_gamma_lut_brightens_midtones_and_identity_at_one():
    lut = gamma_lut(2.2)
    assert lut[0] == 0 and lut[255] == 255 and lut[128] > 128
    assert np.array_equal(gamma_lut(1.0), np.arange(256, dtype=np.uint8))
    f = frame_with_dot()
    assert apply_gamma(f, 2.2)[1, 2, 0] == lut[128]


def test_plain_is_nearest_neighbour():
    out = render(frame_with_dot(), "plain", scale=4, gamma=2.2)
    assert out.shape == (16, 32, 3)
    assert (out[4:8, 8:12, 0] == 128).all() and out[0, 0].sum() == 0


def test_led_draws_round_dots_with_dark_gaps():
    out = render(frame_with_dot(), "led", scale=8, gamma=1.0)
    cell = out[8:16, 16:24, 0]
    assert cell[4, 4] == 128
    assert cell[0, 0] == 0 and cell[0, 7] == 0
    assert 0 < (cell > 0).sum() < 64
    assert out[0:8, 0:8].sum() == 0


def test_distance_blurs():
    out = render(frame_with_dot(), "distance", scale=8, gamma=1.0, metres=5.0)
    assert out.shape == (32, 64, 3)
    assert out[12, 20, 0] > 0 and out[12, 20, 0] < 128
    assert out[9, 13, 0] > 0


def test_unknown_mode_rejected():
    with pytest.raises(ValueError):
        render(frame_with_dot(), "crt")


def test_preview_display_renders_before_push():
    inner = FakeDisplay()
    d = PreviewDisplay(inner, "plain", scale=2, gamma=1.0)
    d.push(frame_with_dot())
    assert inner.last.shape == (8, 16, 3)
    d.set_brightness(0.3)
    assert inner.brightness == 0.3
    d.close()
    assert inner.closed


def spread(out: np.ndarray) -> float:
    """Root-mean-square distance of the red light from its centre, in preview pixels."""
    light = (out[:, :, 0] / 255.0) ** 2.2
    yy, xx = np.mgrid[0:out.shape[0], 0:out.shape[1]]
    cy, cx = (light * yy).sum() / light.sum(), (light * xx).sum() / light.sum()
    return math.sqrt((light * ((yy - cy) ** 2 + (xx - cx) ** 2)).sum() / light.sum())


def test_distance_blur_grows_with_metres():
    f = np.zeros((9, 16, 3), np.uint8)
    f[4, 8] = (255, 0, 0)
    near, mid, far = (spread(render(f, "distance", scale=8, gamma=2.2, metres=m)) for m in (2.0, 5.0, 10.0))
    assert near < mid < far and far > 1.5 * near
    assert distance_sigma(5.0) == pytest.approx(5.0 * math.tan(math.radians(1.5 / 60)) / 0.005)
    assert distance_sigma(5.0) == pytest.approx(0.436, abs=1e-3)   # 1.5 arcmin at 5 m is under half a P5 pixel
    sharp = render(f, "distance", scale=8, gamma=2.2, metres=0.0)
    assert (sharp[:, :, 0] > 0).sum() == 64                          # at 0 m nothing spreads past the LED
    start = time.perf_counter()
    assert render(f, "distance", scale=8, gamma=2.2, metres=1e300).max() == 0   # too far to see: no overflow
    assert time.perf_counter() - start < 0.5                                     # and no giant blur buffers


def test_distance_halation_follows_luminance():
    # 16 preview px (2 wall px) from a lit pixel the 5 m blur has died out; only the halation glow is left,
    # and it follows luminance: a green pixel glows further than an equally bright blue one.
    def far_glow(color, channel):
        f = np.zeros((5, 16, 3), np.uint8)
        f[2, 2] = color
        return int(render(f, "distance", scale=8, gamma=2.2, metres=5.0)[20, 36, channel])

    green, blue, white = far_glow((0, 255, 0), 1), far_glow((0, 0, 255), 2), far_glow((255, 255, 255), 0)
    assert blue > 0 and green > 2 * blue and white >= green
    f = np.zeros((5, 16, 3), np.uint8)
    f[2, 2] = (0, 255, 0)
    assert render(f, "distance", scale=8, gamma=2.2, metres=5.0)[20, 60].sum() == 0   # 5 wall px: dark
    assert render(np.zeros((32, 128, 3), np.uint8), "distance").sum() == 0



def test_distance_conserves_light_and_keeps_strokes_apart():
    # The glow redistributes light, never adds it: a flat field keeps the led look's level at any distance.
    for color in ((128, 128, 128), (255, 200, 0), (60, 60, 60)):
        flat = np.full((32, 128, 3), color, np.uint8)
        for metres in (0.0, 5.0, 10.0):
            inner = render(flat, "distance", scale=8, gamma=2.2, metres=metres)[128, 512]
            assert np.abs(inner.astype(int) - gamma_lut(2.2)[list(color)]).max() <= 1, (color, metres)
    # Spec 7.4: 1 px strokes read at 5 m and scale-2 text (2 px strokes) to about 10 m, so the gap between
    # two strokes stays darker than the strokes. This bounds HALATION (0.5 passes, 0.6 fails).
    one = np.zeros((9, 16, 3), np.uint8)
    one[:, 6] = one[:, 8] = 255                                      # 1 px strokes, 1 px gap
    two = np.zeros((9, 20, 3), np.uint8)
    two[:, 6:8] = two[:, 10:12] = 255                                # 2 px strokes and gap
    near = render(one, "distance", scale=8, gamma=2.2, metres=5.0)[36, :, 0]
    far = render(two, "distance", scale=8, gamma=2.2, metres=10.0)[36, :, 0]
    assert near[60] < 0.85 * near[52] and far[72] < 0.85 * far[56]   # the gap stays darker


def test_distance_blur_has_its_width_and_dark_edges(monkeypatch):
    # One lit white wall pixel spreads as a Gaussian convolved with the 8 px square: per axis, variance
    # sigma**2 + (scale**2 - 1) / 12 in preview pixels. With no glow that sigma is the eye's blur; with
    # all of white's light scattered it is the glow's, three times wider (the amendment's 3 sigma).
    for halation, widths in ((0.0, 1.0), (1.0, 3.0)):
        monkeypatch.setattr(look, "HALATION", halation)
        for metres in (5.0, 10.0):
            f = np.zeros((9, 71, 3), np.uint8)
            f[4, 35] = 255
            light = (render(f, "distance", scale=8, gamma=2.2, metres=metres)[:, :, 0] / 255.0) ** 2.2
            col, x = light.sum(axis=0), np.arange(71 * 8)
            centre = (col * x).sum() / col.sum()
            variance = (col * (x - centre) ** 2).sum() / col.sum()
            expected = (widths * distance_sigma(metres) * 8) ** 2 + (8 ** 2 - 1) / 12
            assert variance == pytest.approx(expected, rel=0.1), (halation, metres)
    monkeypatch.setattr(look, "HALATION", 0.0)
    white = render(np.full((32, 128, 3), 255, np.uint8), "distance", scale=8, gamma=2.2, metres=5.0)
    assert white[0, 0, 0] < white[0, 512, 0] < white[128, 512, 0] == 255   # the air beside the wall is dark


def test_led_honours_gamma_and_cached_tables_are_read_only():
    assert render(frame_with_dot(), "led", scale=8, gamma=2.2)[12, 20, 0] == gamma_lut(2.2)[128]
    lut = gamma_lut(2.2)
    assert not lut.flags.writeable
    with pytest.raises(ValueError):
        lut[128] = 0                                                 # would corrupt every later preview
    render(frame_with_dot(), "distance", scale=8)
    assert not any(a.flags.writeable for a in (look._led_kernel(8), look._light_lut(2.2), look._spread(4, 8, 3.5)))


@pytest.mark.perf
def test_distance_keeps_up_with_the_preview():
    # look = "distance" renders every tick of an SDL run, and the preview dims it: a 128x32 wall at scale 8
    # must fit in a 30 Hz tick.
    seed = zlib.crc32(b"distance-perf")
    f = np.random.default_rng(seed).integers(0, 256, (32, 128, 3), dtype=np.uint8)
    d = PreviewDisplay(FakeDisplay(), "distance", scale=8, gamma=2.2)
    d.set_brightness(0.4)
    d.push(f)                                                        # builds the cached blur matrices
    times = []
    for _ in range(5):
        start = time.perf_counter()
        d.push(f)
        times.append(time.perf_counter() - start)
    assert statistics.median(times) < 1 / 30, f"median {statistics.median(times) * 1000:.1f} ms, seed={seed}"


def test_render_rejects_bad_input():
    good = frame_with_dot()
    bad = [
        dict(frame=good.astype(np.float32)), dict(frame=good[:, :, 0]), dict(frame=good[:, :, :2]),
        dict(scale=0), dict(scale=2.5), dict(scale=True), dict(scale=np.float64(2.0)), dict(scale=np.int64(0)),
        dict(gamma=0.0), dict(gamma=math.nan),
        dict(gamma=math.inf), dict(metres=-1.0), dict(metres=math.nan), dict(metres=math.inf),
    ]
    for case in bad:
        args = dict(frame=good, mode="distance", scale=2, gamma=2.2, metres=5.0) | case
        with pytest.raises(ValueError):
            render(**args)
    assert MODES == LOOKS                                            # every configurable look renders
    for mode in MODES:                                               # a computed numpy scale is an int
        assert render(good, mode, scale=np.int64(2)).shape == (8, 16, 3)


def test_look_never_imports_cv2():
    code = "import sys, arcade.look, arcade.preview; print(sorted({'cv2', 'pygame'} & set(sys.modules)))"
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "[]"


def test_preview_models_brightness():
    inner = FakeDisplay()
    d = PreviewDisplay(inner, "plain", scale=1, gamma=1.0)
    wall = np.full((4, 8, 3), 255, np.uint8)
    d.push(wall)
    assert (inner.last == 255).all()                                 # full brightness until told otherwise
    d.set_brightness(0.25)
    d.push(wall)
    assert inner.brightness == 0.25 and (wall == 255).all()          # the wall frame itself is never scaled
    assert (inner.last == round(255 * 0.25 ** (1 / 2.2))).all()      # 136: the monitor shows a quarter of the light
    assert np.allclose((inner.last / 255.0) ** 2.2, 0.25, atol=0.01)
    with warnings.catch_warnings():
        warnings.simplefilter("error")                               # a NaN level never reaches the byte cast
        for level, expect in ((0.0, 0), (-1.0, 0), (math.nan, 0), (1.0, 255), (1.5, 255)):
            d.set_brightness(level)
            d.push(wall)
            assert (inner.last == expect).all(), level
    assert inner.brightness == 1.5                                   # forwarded unchanged, even above 1
    far = PreviewDisplay(FakeDisplay(), "distance", scale=4, gamma=2.2, metres=10.0)
    far.push(frame_with_dot())
    assert np.array_equal(far.inner.last, render(frame_with_dot(), "distance", scale=4, gamma=2.2, metres=10.0))
```

- [ ] **Step 2: Run them to verify they fail**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_look.py`
Expected: collection error, `ModuleNotFoundError: No module named 'arcade.look'`.

- [ ] **Step 3: Implement**

`arcade/look.py`:

```python
"""Preview render modes (spec 9.4): how a wall frame looks as flat pixels, as LED dots, and from a distance.

Pure numpy: this module never imports cv2, so the SDL preview never loads OpenCV's own SDL next to pygame's.
"""
from __future__ import annotations

import math
import operator
from functools import lru_cache

import numpy as np

MODES = ("plain", "led", "distance")

MONITOR_GAMMA = 2.2        # a preview's bytes are decoded by an sRGB monitor
PITCH_M = 0.005            # P5 modules: 5 mm between LEDs
BLUR_ARCMIN = 1.5          # what the eye resolves at night (spec 9.4)
HALATION_SIGMAS = 3.0      # the glow around bright pixels spreads three times as far as the blur
HALATION = 0.3             # the share of a white pixel's light scattered into the glow (times luminance); under 1
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)   # Rec. 709 weights on linear light


def _frozen(a: np.ndarray) -> np.ndarray:
    """A cached array is shared by every caller, so it is read-only: an in-place edit raises."""
    a.flags.writeable = False
    return a


@lru_cache(maxsize=8)
def gamma_lut(gamma: float) -> np.ndarray:
    v = np.arange(256, dtype=np.float64) / 255.0
    return _frozen(np.clip(np.round(255.0 * v ** (1.0 / gamma)), 0, 255).astype(np.uint8))


def apply_gamma(frame: np.ndarray, gamma: float) -> np.ndarray:
    if gamma == 1.0:
        return frame
    return gamma_lut(gamma)[frame]


@lru_cache(maxsize=8)
def _led_kernel(scale: int) -> np.ndarray:
    c = (scale - 1) / 2
    yy, xx = np.mgrid[0:scale, 0:scale]
    d = np.hypot(xx - c, yy - c) / scale
    return _frozen(np.where(d <= 0.36, 1.0, np.where(d <= 0.5, 0.3, 0.0)).astype(np.float32))


def _nearest(frame: np.ndarray, scale: int) -> np.ndarray:
    return np.repeat(np.repeat(frame, scale, axis=0), scale, axis=1)


def distance_sigma(metres: float) -> float:
    """The eye's blur at this distance, in wall pixels: 1.5 arcmin across the 5 mm pitch (0.436 at 5 m).

    The preview blurs sigma * scale preview pixels with three box blurs, which cannot go below one pixel:
    at scale 1 and 5 m the boxes have radius 0 and the core is not blurred at all (the glow still is), so
    judge distance at scale 4 or more."""
    return metres * math.tan(math.radians(BLUR_ARCMIN / 60.0)) / PITCH_M


@lru_cache(maxsize=8)
def _light_lut(gamma: float) -> np.ndarray:
    """Byte to the light the preview shows, 0..1: the led look's bytes as a monitor decodes them."""
    v = np.arange(256, dtype=np.float64) / 255.0
    return _frozen((v ** (MONITOR_GAMMA / gamma)).astype(np.float32))


def _box_radii(sigma: float, n: int = 3) -> list[int]:
    """Radii of n box blurs whose sum approximates a Gaussian of this sigma (Kovesi's widths)."""
    sigma = min(sigma, 1e6)               # wider than any preview already; keeps the squares finite
    ideal = math.sqrt(12.0 * sigma * sigma / n + 1.0)
    lo = int(ideal)
    lo -= 1 - lo % 2                      # the largest odd width at or under the ideal
    m = round((12.0 * sigma * sigma - n * lo * lo - 4 * n * lo - 3 * n) / (-4 * lo - 4))
    return [(lo if i < m else lo + 2) // 2 for i in range(n)]


def _box(a: np.ndarray, r: int, axis: int) -> np.ndarray:
    """Mean over 2r + 1 cells along axis; cells past the edge are dark, as the air beside the wall is."""
    if r <= 0:
        return a
    if r >= a.shape[axis]:                  # every window holds the whole line: one mean, and no huge pads
        return np.broadcast_to(a.sum(axis=axis, keepdims=True) / (2 * r + 1), a.shape).copy()
    a = np.moveaxis(a, axis, 0)
    pad = np.zeros((r + 1,) + a.shape[1:], a.dtype), a, np.zeros((r,) + a.shape[1:], a.dtype)
    c = np.cumsum(np.concatenate(pad), axis=0)
    out = (c[2 * r + 1:] - c[:-2 * r - 1]) / (2 * r + 1)
    return np.moveaxis(out, 0, axis)


@lru_cache(maxsize=16)
def _spread(n: int, scale: int, sigma: float) -> np.ndarray:
    """(n * scale, n): how one wall pixel's light lands on a preview line after the nearest-neighbour
    upscale and three box blurs. The blur is linear and separable, so it is built once per size."""
    m = np.repeat(np.eye(n, dtype=np.float32), scale, axis=0)
    for r in _box_radii(sigma):
        m = _box(m, r, 0)
    return _frozen(np.ascontiguousarray(m))


def _gauss(light: np.ndarray, scale: int, sigma: float) -> np.ndarray:
    """light (h, w, 3) at wall resolution, upscaled by scale and blurred by a Gaussian of sigma preview px."""
    h, w, _ = light.shape
    rows = (_spread(h, scale, sigma) @ light.reshape(h, w * 3)).reshape(h * scale, w, 3)
    return np.einsum("Ywc,Xw->YXc", rows, _spread(w, scale, sigma), optimize=True)


def _distance(frame: np.ndarray, scale: int, gamma: float, metres: float) -> np.ndarray:
    """Light is conserved: a luminance-weighted share of each pixel's light scatters into the wide glow and
    the rest stays in the eye's blur, so a flat field keeps the led look's level at every distance."""
    light = _light_lut(gamma)[frame]
    sigma = distance_sigma(metres) * scale
    scattered = HALATION * light * (light @ LUMA)[..., None]
    core = _gauss(light - scattered, scale, sigma)
    halo = _gauss(scattered, scale, HALATION_SIGMAS * sigma)
    shown = np.clip(core + halo, 0.0, 1.0) ** (1.0 / MONITOR_GAMMA)
    return np.round(shown * 255.0).astype(np.uint8)


def render(frame: np.ndarray, mode: str, scale: int = 8, gamma: float = 2.2, metres: float = 5.0) -> np.ndarray:
    """frame (h, w, 3) uint8 drawn at scale for a monitor.

    plain: nearest-neighbour, the bytes as they are. led: round dots with dark gaps, after gamma (with
    gamma 2.2 the preview shows the light of an uncorrected wall; with 1.0, the bytes as the card
    applies gamma). distance: each pixel as a full square of the led look's light (not its dot), seen
    from metres away: blurred by 1.5 arcmin, with a luminance-weighted share scattered into a glow three
    times wider, for legibility checks (spec 9.4). At 5 m the real eye still resolves the 5 mm dot grid,
    so text reads slightly smoother in this preview than on the wall. scale may be any integer type.
    """
    if mode not in MODES:
        raise ValueError(f"look must be one of {MODES}, got {mode!r}")
    if frame.ndim != 3 or frame.shape[2] != 3 or frame.dtype != np.uint8:
        raise ValueError(f"frame must be (height, width, 3) uint8, got {frame.shape} {frame.dtype}")
    try:
        size = operator.index(scale)                   # an int or a numpy integer; never a float
    except TypeError:
        size = 0
    if isinstance(scale, (bool, np.bool_)) or size < 1:
        raise ValueError(f"scale must be an int of at least 1, got {scale!r}")
    scale = size
    if not 0.0 < gamma < math.inf:
        raise ValueError(f"gamma must be over 0 and finite, got {gamma!r}")
    if not 0.0 <= metres < math.inf:
        raise ValueError(f"metres must be 0 or more and finite, got {metres!r}")
    if mode == "plain":
        return _nearest(frame, scale)
    if mode == "distance":
        return _distance(frame, scale, gamma, metres)
    f = apply_gamma(frame, gamma)
    h, w = f.shape[:2]
    k = _led_kernel(scale)
    out = f[:, None, :, None, :].astype(np.float32) * k[None, :, None, :, None]
    return out.reshape(h * scale, w * scale, 3).astype(np.uint8)


def dim(image: np.ndarray, level: float) -> np.ndarray:
    """A preview image showing level (0..1) of its light: a monitor decodes bytes with MONITOR_GAMMA, so
    the bytes scale by level ** (1 / MONITOR_GAMMA). NaN or a level not over 0 gives black."""
    if not level > 0.0:
        return np.zeros_like(image)
    if level >= 1.0:
        return image
    factor = level ** (1.0 / MONITOR_GAMMA)
    return np.round(image.astype(np.float32) * factor).astype(np.uint8)
```

`arcade/preview.py`:

```python
from __future__ import annotations

import numpy as np

from arcade.look import dim, render
from show.display import Display


class PreviewDisplay:
    """Renders a wall frame in a look mode before handing it to a real (usually SDL) display.

    Brightness is modelled here: set_brightness forwards the level to the inner display (which stores it; the
    SDL window never dims) and scales the rendered preview so the monitor shows that fraction of the light.
    The wall frame itself is never scaled (Global Constraints: pixels pushed to hardware are never scaled).
    """

    def __init__(self, inner: Display, mode: str, scale: int, gamma: float, metres: float = 5.0):
        self.inner, self.mode, self.scale, self.gamma, self.metres = inner, mode, scale, gamma, metres
        self.level = 1.0

    def push(self, frame: np.ndarray) -> None:
        image = render(frame, self.mode, self.scale, self.gamma, self.metres)
        self.inner.push(dim(image, self.level))

    def set_brightness(self, level: float) -> None:
        self.level = level
        self.inner.set_brightness(level)

    def close(self) -> None:
        self.inner.close()
```

- [ ] **Step 4: Run the tests**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_look.py`
Expected: `15 passed`.

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`
Expected: `224 passed`, no skips.

- [ ] **Step 5: Commit**

```bash
git add arcade/look.py arcade/preview.py tests/arcade/test_look.py
git commit -m "feat(arcade): plain, LED and metre-aware distance looks in numpy, PreviewDisplay models brightness (core Task 6)" -m "distance moves a share of the light into the glow instead of adding it, so levels and colours stay the wall's (plan review B1)."
```

---

## Iteration verify

Run inline by the operator after Task 4, from the repo root.

1. `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest --collect-only -q | tail -1` prints `224 tests collected` (183 before this iteration; the count rises at every task: 186, 190, 209, 224).
2. `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs` prints `224 passed` with **0 skipped**. Per module: `tests/arcade/test_actors.py` 17, `tests/arcade/test_calibration.py` 23, `tests/arcade/test_canvas.py` 19, `tests/arcade/test_config.py` 42, `tests/arcade/test_doctor.py` 10, `tests/arcade/test_festival.py` 17, `tests/arcade/test_look.py` 15, `tests/arcade/test_mirror.py` 2, `tests/arcade/test_sensed.py` 20, `tests/test_colorlight.py` 29, `tests/test_config.py` 5, `tests/test_ddp.py` 8, `tests/test_display.py` 4, `tests/test_font.py` 7, `tests/test_gitignore.py` 6.
3. No existing assert weakened: `git diff 83b6945 -- tests/ | grep '^-[^-]'` prints exactly two lines, both in `tests/arcade/test_festival.py`: `-from arcade.sensed import MIN_CONF` (replaced by `from arcade.sensed import MIN_CONF, Sensed, place`; not an assert) and `-    assert not list(shake(0.5, 1.0)(iter(source)))[30].bodies[0].in_zone     # the default zone ends at 0.8` (owner decision Q9: replaced by `pytest.raises(ValueError, match="calibration")` around the same call). Anything else is a Deviation.
4. `.venv/bin/python -c "import sys, arcade.canvas, arcade.look, arcade.preview; print(sorted({'cv2', 'mediapipe', 'sounddevice', 'pygame'} & set(sys.modules)))"` prints `[]`.
5. Look at the wall. The snippet writes six PNGs, plain, led and distance renderings (scale 8, gamma 2.2, 5 m) of one canvas at 128x32 and 64x64, into a directory the operator names in `OUT` (tools/arcade_shot.py is core Task 13, so this is verify-only). Each PNG carries the git sha in a `git` text chunk and on the canvas. Expected: the six paths with sizes `1024x256` and `512x512`; in the images, inside a blue border, the title in yellow ("CODE IS ART" on one line at 128x32; "CODE IS" over "ART" at 64x64), a red "88" at scale 2 with 2 px strokes, a white diagonal that touches neither text nor disc, a green disc in the bottom-right corner, and the sha in cyan (top right at 128x32, bottom left at 64x64); `led` shows round dots with dark gaps; `distance` is soft, with every letter and both 8s readable, the same colours and levels as `led` (yellow stays yellow, not lemon), and a faint glow that is widest around white and green and barely visible around blue.

```bash
OUT=docs/superpowers/workflow/evidence/it03    # or any directory the operator names
mkdir -p "$OUT" && OUT="$OUT" SHA="$(git describe --always --dirty --abbrev=7)" .venv/bin/python - <<'EOF'
import os
from pathlib import Path

from PIL import Image, PngImagePlugin

from arcade.canvas import Canvas
from arcade.look import render
from show.font import Font

out, sha = Path(os.environ["OUT"]), os.environ["SHA"]
font = Font.load(Path("fonts/5x7.bin"))
info = PngImagePlugin.PngInfo()
info.add_text("git", sha)
for w, h in ((128, 32), (64, 64)):
    wide = w > h                                                # 128x32: one title line; 64x64: two
    c = Canvas(w, h, font)
    c.rect(0, 0, w, h, (0, 0, 180))
    c.text(2, 2, "CODE IS ART" if wide else "CODE IS", (255, 200, 0))
    if not wide:
        c.text(2, 11, "ART", (255, 200, 0))
    c.text(2, 11 if wide else 20, "88", (255, 40, 40), scale=2)  # a score at scale 2: 10x14, 2 px strokes
    c.fill_circle(w - 8, h - 8, 5, (0, 255, 0))
    c.line(w // 2 - 2, h - 14, w - 1, 11, (255, 255, 255))      # clear of the text and the sha
    c.text(w - 44 if wide else 2, 2 if wide else h - 9, sha[:7], (0, 255, 255))
    for look in ("plain", "led", "distance"):
        image = render(c.frame, look, scale=8, gamma=2.2, metres=5.0)
        assert image.shape == (h * 8, w * 8, 3), image.shape
        path = out / f"it03-{w}x{h}-{look}.png"
        Image.fromarray(image).save(path, pnginfo=info)
        print(path, f"{w * 8}x{h * 8}")
EOF
```

6. `git log --oneline -4` shows the four commit messages above, in order, and `git status --short` is clean apart from `docs/superpowers/workflow/` files (and `$OUT` if it is under the repo).
