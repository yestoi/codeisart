# Iteration 3 plan review (adversarial, operator step 2a)

Plan: `docs/superpowers/plans/2026-09-27-it03-carried-canvas-look.md` (uncommitted), reviewed 2026-09-27 against spec
revision 3 (sections 2, 4.3, 5, 6.4, 7.4, 7.6, 9.4), the core plan (lines 1-51, Tasks 5 and 6 with their per-task
amendments, "Spec drift already known"), 05-plan S4, the roadmap's C11-C16 with `evidence/it02/orchestrator-report.md`
and `reviewer-verdict.md`, the operator design's section 5 gate table, and HEAD `0fc31ca`.

## Verdict: BLOCKED

Two blocking findings, each a few lines of code plus one test:

- B1: the `distance` look adds light. It changes flat colours and brightness at every distance, 0 m included.
- B2: `blit_rgb` wraps colours instead of clamping them when the sprite is not uint8. Paint's float buffer will be
  such a sprite.

Everything else the plan claims held when I replayed it.

## What I ran

All of this ran in a scratch clone of `0fc31ca`, with the venv symlinked in. The working tree was never touched.

- **Replay.** I extracted every `path`: block from the plan's text and applied the blocks task by task, tests first.
  Every count and failure message matches the plan:
  - Task 1: `3 failed, 17 passed` with the two messages quoted in the plan, then `20` and `186`.
  - Task 2: `4 failed, 30 passed`, then `34` and `190`.
  - Tasks 3 and 4: each fails collection with `ModuleNotFoundError`, then `16`/`206` and `12`/`218`.
  - Per-module collection counts match verify step 2 exactly.
  - Verify step 3 prints only `-from arcade.sensed import MIN_CONF`.
  - Verify step 4 prints `[]`.
  - The suite passes under `-W error` and under `PYTHONHASHSEED` 1, 2 and 3.
- **Diffs against HEAD.** `arcade/sensed.py` and `arcade/sources/actors.py` differ only where the loop decisions say
  they do. The core tests the plan calls verbatim are verbatim: the five Task 5 functions, `tests/arcade/conftest.py`
  (byte-identical), and the six Task 6 functions. The one exception is `test_distance_blurs`, which gains
  `metres=5.0` as the amendment requires.
- **Forwarded C12 list.** I grepped the core plan for `Sensed(` and `Audio(`. The positional calls are exactly
  lines 2884, 3659, 3661, 4157 and 5267, so the list is complete. `Body(...)` and `Blob(...)` calls in the core plan
  are positional only in spec order.
- **Cached matrices against a direct blur.** I wrote my own direct implementation: nearest-neighbour upscale, then
  the plan's `_box` three times per axis on the big image, for the core and for the halo. I compared it with
  `render(..., "distance")` over:
  - frames 1x1, 4x8, 32x128, 64x64 and 3x200;
  - five patterns: random, white, gradient, sparse and near-black;
  - scales 1, 2, 3 and 8;
  - distances 0, 0.3, 2, 5, 10, 50, 300 and 1e5 m;
  - gamma 1.0 and 2.2.

  The worst difference is 1 byte. "Within one byte" is true across the value range.
- **Linear light.** `(v/255) ** (2.2/gamma)` is the light the `led` preview shows on a 2.2 monitor, and the output is
  re-encoded once with `1/2.2`. Gamma is applied exactly once in `distance`, once in `led`, and never in `plain`.
  `dim` works on the monitor-decoded light, so it is correct for every look. `PreviewDisplay` never modifies or
  aliases the wall frame: `_nearest` always copies.
- **Timing.**
  - Unloaded: `distance` at 128x32 scale 8 takes 7.1 ms median including `dim` (plain 2.1 ms, led 4.4 ms). A cold
    build takes 6.8 ms.
  - Under 16 busy processes on 8 cores: the median is 6.4 ms and the worst single render 34 ms. The perf test (median
    of 5 under 33 ms) passed three times out of three.
  - The worst hostile canvas call, `text(-10**6, 0, "X" * 10000)`, takes 0.8 ms unloaded and up to 24 ms under that
    load, against the 50 ms single-shot limit.
- **Mutations.** I ran 38 single mutations of my own (not the writer's list). 20 were caught and 18 survived. The
  survivors that matter feed B1 and notes N2 to N7:
  - HALATION x10 and x1/6
  - HALATION_SIGMAS 1.5
  - box edges padded with the edge value instead of dark
  - Kovesi widths all `lo`
  - `led` ignoring gamma
  - `blit` without the bool cast
  - line-skip threshold at 40x and 1000x
  - ring thickness
  - `_placed_by` ignoring `in_zone`, and ignoring `zone_y`

  The survivors that do not matter are equivalent or affect only speed: `_i` mapping +inf to +FAR, `_i` without its
  clamp, text without the y cull or the off-left skip, `rect` without its `w <= 0` guard, and
  `min(level, 1)` forwarded as the brightness.

  One more mutation, applying `_i` only to a line's start point, reintroduces 05-plan S4's infinite loop.
  `test_line_with_float_endpoint_terminates` then **hangs** (killed after 15 s) instead of failing (N1).
- **Pictures.** I ran the Iteration verify snippet and read all six PNGs. They match the plan's description:
  - `plain` is crisp. `led` shows round dots with dark gaps; red (255, 40, 40) reads pink there, which is the
    uncorrected wall correctly modelled.
  - `distance` at 5 m is soft, "CODE IS ART" and the scale-2 "88" are legible at both sizes, and the glow is widest
    around white and green, faint around blue.
  - At 64x64 the title is clipped to "CODE IS AR'", over the right border.
  - At 128x32 the white diagonal runs through the cyan provenance sha.

  I also rendered a 64x64 text card at 5 m and 10 m, and again with HALATION 3.0. At 3.0 the white "score 12" is a
  blown-out slab, and the plan's tests still pass (B1, N4).

## Blocking findings

### B1. Task 4, loop decision 9: the halation glow adds light, so `distance` shifts every flat colour at every distance

- **What.** `_distance` computes `core + HALATION * halo`, where `core` already carries all of each pixel's light and
  `halo` is that same light times its luminance, blurred wider. Nothing is taken out of the core, so light is created.
  For a uniform field (interior pixel of a 32x128 frame, scale 8, gamma 2.2), against the `led` look's light
  (`gamma_lut`):

  | Colour | led | distance 5 m | distance 0 m |
  |---|---|---|---|
  | (128, 128, 128) | 186 | 199 | 199 |
  | (255, 200, 0) | 255, 228, 0 | 255, **251**, 0 | 255, 251, 0 |
  | (255, 40, 40) | 255, 110, 110 | 255, 115, 115 | 255, 115, 115 |
  | (60, 60, 60) | 132 | 136 | 136 |

  Mid grey gets 15% more light. The arcade's amber (255, 200, 0) turns lemon yellow. This happens at 0 m, where the
  plan's own test says "nothing spreads past the LED".
- **Why it blocks.**
  - `distance` is the instrument spec 9.4 names for judging the wall at 5 m, and its docstring promises "the led
    look's light as seen from metres away". Instead it misstates colour and brightness everywhere, and the owner will
    judge from these PNGs (loop decision 9: "the owner can retune it by eye").
  - No value of HALATION removes the bias. Any value above 0 shifts flat colours; retuning trades glow radius against
    colour error.
  - The tests are built around the defect. The halation test deliberately measures a ratio that "does not depend on
    it", and HALATION 3.0 passes the whole suite while filling the 1 px gap between two white strokes completely at
    5 m (gap byte 255, stroke 255).
  - Core Task 13 (the forwarded `-distance.png`) and the wall-look work inherit this.
- **Fix.**
  1. Make the halo redistribute light rather than add it: a share of each pixel's light scatters into the wide
     Gaussian, and the rest stays in the narrow one. I verified this replacement passes all 12 plan tests unchanged
     (far glow green 25, blue 9, white 29), and flat fields then equal `gamma_lut` exactly at 0, 5 and 10 m:

     ```python
         scattered = HALATION * light * (light @ LUMA)[..., None]      # this share of each pixel's light glows
         core = _gauss(light - scattered, scale, sigma)
         halo = _gauss(scattered, scale, HALATION_SIGMAS * sigma)
         shown = np.clip(core + halo, 0.0, 1.0) ** (1.0 / MONITOR_GAMMA)
     ```

  2. Change the `HALATION` comment to "the share of a white pixel's light scattered into the glow; under 1".
  3. Reword loop decision 9 to match.
  4. Add a test that pins conservation and bounds HALATION by the spec's own legibility claims. With the fix and
     HALATION 0.3, the gap-to-stroke ratios are 0.73 (1 px strokes and gap at 5 m) and 0.72 (2 px strokes and gap at
     10 m; spec 7.4 says scale 2 "reads to about 10 m"). With the fix, this test fails on the plan's code (flat
     grey is 13 bytes off) and passes on the fixed code together with the 12 plan tests. HALATION 0.5 still passes
     (0.81, 0.80) and 0.6 fails (0.86, 0.84), so the owner keeps room to retune by eye without an assert change.

     ```python
     def test_distance_conserves_light_and_keeps_strokes_apart():
         for color in ((128, 128, 128), (255, 200, 0), (60, 60, 60)):
             flat = np.full((32, 128, 3), color, np.uint8)
             for metres in (0.0, 5.0, 10.0):
                 inner = render(flat, "distance", scale=8, gamma=2.2, metres=metres)[128, 512]
                 assert np.abs(inner.astype(int) - gamma_lut(2.2)[list(color)]).max() <= 1, (color, metres)
         one = np.zeros((9, 16, 3), np.uint8); one[:, 6] = one[:, 8] = 255        # 1 px strokes, 1 px gap
         two = np.zeros((9, 20, 3), np.uint8); two[:, 6:8] = two[:, 10:12] = 255  # scale 2: 2 px strokes and gap
         near = render(one, "distance", scale=8, gamma=2.2, metres=5.0)[36, :, 0]
         far = render(two, "distance", scale=8, gamma=2.2, metres=10.0)[36, :, 0]
         assert near[60] < 0.85 * near[52] and far[72] < 0.85 * far[56]           # the gap stays darker
     ```

  5. Test step 4's count becomes 13 and the suite 219. Update verify steps 1 and 2 to match.

### B2. Task 3: `blit_rgb` wraps colours instead of clamping them when the sprite is not uint8

- **What.** `self.frame[dst][lit] = sub[lit]` casts silently, with numpy's unsafe casting. I probed on HEAD plus the
  plan:
  - A float32 sprite with (300, 127.9, 0.4), NaN, -5 and 255.6 draws (44, 127, 0), 0 (with a `RuntimeWarning: invalid
    value encountered in cast`), 251 and 255.
  - An int64 sprite with 300 and -1 draws 44 and 255.
- **Why it blocks.**
  - Spec 7.4 says "colours are clamped to 0..255", and so does the plan's Canvas docstring. The plan's own Review
    Focus 1 is "a colour computed as 300 or NaN ... must round, clamp and clip".
  - Spec 7.4 also says a game that keeps its own buffer "(paint) blits it", and core Task 10's Paint keeps
    `self.trail` as float32. Paint and every later sprite-computing game inherit wrap-around: -5 becomes near-white,
    and 300 becomes dark.
  - The Interfaces line says "(h, w, 3) uint8", but nothing enforces it, and the 25 hostile calls never pass a
    non-uint8 sprite.
- **Fix.**
  1. At the top of `blit_rgb`, convert first. Rounding half up matches `_channel`, and black is judged after
     conversion, so 0.4 is transparent:

     ```python
             sprite = np.asarray(sprite)
             if sprite.dtype != np.uint8:
                 v = np.floor(np.nan_to_num(sprite.astype(np.float64), nan=0.0, posinf=255.0, neginf=0.0) + 0.5)
                 sprite = np.clip(v, 0, 255).astype(np.uint8)
     ```

  2. Extend the docstring: "a sprite that is not uint8 (a game's float buffer) is rounded half up and clamped to
     0..255 first, NaN to 0".
  3. Add to `test_colours_clamped`, under `warnings.simplefilter("error")`:
     `c.blit_rgb(np.array([[[300.0, 127.6, 0.4], [np.nan, 0, 0], [-5, 0, 0], [np.inf, 0, 0]]], np.float32), 0, 5)`
     gives row 5 as `(255, 128, 0), (0, 0, 0), (0, 0, 0), (255, 0, 0)`, and an int64 `[[[300, 0, 0]]]` gives
     `(255, 0, 0)`.

  I verified this passes all 16 canvas tests under `-W error`, and the probe then gives exactly those values.

## Notes (non-blocking)

The writer asked five questions; my answers are first.

- **Timing tests (flag 2).** These tests are not flaky on this machine, but they are the wrong shape. The perf test
  (median of 5, 6 to 7 ms against 33) is robust even at 2x CPU oversubscription.

  The canvas's single-shot 50 ms asserts had only about 2x headroom under that load: 24 ms for the 10,000-character
  off-left string. That headroom is thin when several agents run suites at once.

  The real weakness is **N1**: a regression that reintroduces S4's infinite loop hangs the suite rather than failing
  it, which I demonstrated above. The 50 ms asserts only catch calls that are slow but finish.
- **`distance` deviation (flag 3).**
  - Linear light is correct, and "within 1 byte" is true (see What I ran).
  - Cached separable matrices are an exact refactor of the box blurs the amendment asks for, so they conform to the
    spec.
  - "HALATION untested" is the problem, and B1 fixes it.
- **C12 and C14 forwards (flag 4).** The C12 list is complete. C14's `scale = 0.0` is safe until core Task 16,
  because actors always have hips and `_noisy` keeps the clean scale. See N11 for the part C14 misses.
- **`scene()` (flag 5).** Nothing breaks and nothing is consumed twice. Every caller in the core plan (Tasks 8, 9,
  12, 13, 14, 20 and `degrade(scene(...))`) iterates the result once. `persons`, `blobs` and `motion` are listed
  once, before validation. Motion-shape errors are still raised lazily inside `_frames`, which the committed
  `pytest.raises(...): list(scene(...))` expects. The only visible change is that a duplicate-id error now surfaces
  at the call.
- **Owner questions (flag 1).** Q8 and Q9 are correctly the owner's: Q9 changes the expected outcome of a committed,
  plan-literal assert. With the plan as written, `degrade(shake(...)(custom_scene), calibration=custom)` now raises,
  so the `shake` fallback can no longer slip silently through `degrade`. That makes waiting for Q9 cheap.

Other notes, each with a fix:

- **N1. Tests.** Make "never hangs" fail rather than hang. Add a `deadline(seconds)` context manager to
  `test_canvas.py` using `signal.setitimer(signal.ITIMER_REAL, s)` with a SIGALRM handler that raises
  `TimeoutError`. That works on macOS and Linux in pytest's main thread, and interrupts pure-Python loops. Wrap
  `test_nan_inf_and_huge_never_raise_or_hang`'s loop and `test_line_with_float_endpoint_terminates` in
  `with deadline(1.0)`.

  Also make `text` skip whole off-left glyphs arithmetically:
  `first = max(0, (-x) // cell_w)` and `for i in range(first, len(s))`. The 10,000-character case then costs only
  what shows, as loop decision 8 already claims.
- **N2. `led` ignoring gamma survives.** Every `led` test uses `gamma=1.0`. This is the default look, and "where gamma
  is applied" is a named hazard. Add `assert render(frame_with_dot(), "led", scale=8, gamma=2.2)[12, 20, 0] ==
  gamma_lut(2.2)[128]` to a new plan test (not to the verbatim core test).
- **N3. Blur size and edges are untested.**
  - The Kovesi widths can all shrink to `lo` and the dark-edge padding can become edge-replicating, and both
    mutations survive. Add a test that, with `monkeypatch.setattr(look, "HALATION", 0.0)`, measures the realised
    spread of one lit wall pixel. For one axis, the variance is `sigma**2 + (scale**2 - 1) / 12` within 10 percent,
    at 5 and 10 m and scale 8. The same test can check that a white frame's corner is darker than its centre.
  - The box approximation is coarse at small scales: at scale 1 and 5 m the core blur has radii `[0, 0, 0]`, which
    is no blur. Say so in `distance_sigma`'s docstring, since core Task 13 shrinks the scale to fit 1,536 px.
- **N4. HALATION is unbounded by the tests.** B1's second assert covers this. Keep HALATION under 1, which the
  energy-conserving form needs.
- **N5. C13's check is half tested.** `_placed_by` ignoring `in_zone`, or ignoring `zone_y`, survives. A scene built
  with `Calibration(min_height=0.3)` and `Person(0.5, height=0.4)` differs from the default only in `in_zone`, and
  the real code does raise on it (probed). Add that case to `test_degrade_needs_the_scene_calibration`.
- **N6. `blit`'s bool cast is untested.** That cast is a listed addition, and dropping it survives. Without it, an
  int mask becomes fancy indexing and paints the wrong rows. Add
  `c.blit(np.array([[1, 0], [0, 1]], np.uint8), 3, 0, RED)` and assert the diagonal.
- **N7. The spec's "four times the canvas extent" is not pinned.** The skip threshold survives at 40x and 1000x. Add
  `c.line(0, 0, 4 * (w + h), 0, RED)` draws and `c.line(0, 0, 4 * (w + h) + 1, 0, RED)` does not.
- **N8. Cached arrays are writable and shared.** `gamma_lut` is public and returns an `lru_cache`d array. The
  brightness limiter and flash governor (spec 7.6) are likely LUT users, and an in-place edit there would corrupt
  every later preview. Set `flags.writeable = False` on the arrays returned by `gamma_lut`, `_led_kernel`,
  `_light_lut` and `_spread`.
- **N9. `render` rejects numpy integer scales.** `isinstance(scale, int)` is False for `np.int64(8)`. Core Task 13
  computes a smaller scale to fit 1,536 px. Use `operator.index(scale)` inside a try block (bool still rejected).
- **N10. Infinite sizes behave inconsistently (per 05-plan S4, which maps inf to -FAR).**
  - `fill_circle(5, 5, inf)` draws one pixel, but `fill_circle(5, 5, 1e300)` fills the canvas.
  - `fill_rect(0, 0, inf, 2)` draws nothing, but a width of 1e300 fills.

  This is harmless and arguably flash-safe. Document it in `_i`'s docstring rather than change it.
- **N11. C14 spec drift and a near-zero torso.**
  - Spec 5 says the nose is used "only when both shoulders are missing". Loop decision 4 changes that rule for the
    degenerate case. Add it to the core plan's "Spec drift already known" for the next spec revision.
  - `torso > 0.0` catches only an exact zero. With shoulders 0.02 apart (side-on) and no hips, the torso is 0.025 and
    the line sits 0.008 above the shoulders, so a wrist at shoulder height counts as raised. Spec 2's bar layout
    (64x64, hips hidden by the counter) makes this likely. Carry a torso floor to core Task 8 or 16, for example the
    nose line when the torso is under 0.1 of the box height.
- **N12. Headlamps now park on the edge.** A clamped headlamp that has left the frame stays on the edge column rather
  than disappearing. It is out of the zone, and real sources cannot produce such a blob, so this only needs a
  sentence in `headlamps`' docstring.
- **N13. The `distance` docstring is inaccurate.** It says "the led look's light", but the model starts from
  full-fill squares at the `led` look's gamma, not from the dot pattern. At 5 m the eye's 2.2 mm blur against the
  5 mm pitch leaves the real dot grid visible, so text looks slightly smoother in the preview than on the wall. Say
  so.
- **N14. The verify snippet's composition hides what it checks.**
  - At 64x64, draw "CODE IS" and "ART" on two lines, so the evidence shows legible text at the square layout. The
    right-edge clip is already tested.
  - At 128x32, the diagonal crosses the sha, the provenance text. Draw the line from `(0, 20)` to `(w - 1, 11)`, or
    move the sha to y 2 on the right.
- **N15. The perf test times less than the tick pays.** Time `PreviewDisplay(FakeDisplay(), "distance", 8,
  2.2).push(f)` with the level at 0.4, rather than `render` alone. With `dim` it takes 7.1 ms.
- **N16. The perf test's seed is not in its message.** The Global Constraint says to print the seed in the assertion
  message: add `seed={zlib.crc32(b'distance-perf')}` to it.
- **N17. Forwarded items need to outlive the plan.** When C12 to C16 close, copy "Forwarded to later amendments" into
  the roadmap as carried items: C12's positional calls, Task 12's `place()` and calibration, Task 13's
  `-distance.png`, Task 18's `build_display`, and Task 16's scale smoothing. Iteration 2's forwarded note was
  mis-addressed once already.
- **N18. `dim` assumes the brightness packet scales light linearly.** The Colorlight brightness packet scaling light
  linearly (PWM) is firmware-dependent. Add "confirm the brightness packet scales light linearly" to the GATE B
  firmware check, next to C4's `rgb` pattern.

## Owner decisions

None new. Q8 (C11) and Q9 (`shake` and `test_festival.py:180`) are already with the owner, and this plan needs
neither. The C14 wording change to spec 5 (N11) should be journaled as spec drift for the next spec revision; it is
not a gate.

## Round 2

### Verdict: APPROVED

B1 and B2 are closed. Q9 is applied as the owner answered it, and the Q9 line is the only committed assert that
changed. The revised plan replays exactly as written. No blocking defect remains in the plan's code. The notes below
are test gaps over correct code: six added asserts close them, and the plan's own rules allow adding asserts at any
time. One sentence of the plan's "Declined" paragraph is wrong and needs correcting (R2-N1).

### What I ran

- **Replay.** I cloned `83b6945` fresh into the scratchpad and replayed Tasks 1 to 4 from the plan text, tests
  before code and one commit per task. Every step matched the plan:
  - Task 1: `3 failed, 17 passed`, then `186 passed`.
  - Task 2: `5 failed, 29 passed` (the five named tests; two fail with `ZeroDivisionError`, three with
    `DID NOT RAISE`), then `190 passed`.
  - Tasks 3 and 4: `ModuleNotFoundError` for `arcade.canvas` and `arcade.look`, then `19` and `209 passed`, then
    `15` and `224 passed`.
  - `--collect-only`: `224 tests collected`. The per-module counts match verify step 2 exactly.
  - `-W error`: `224 passed`.
  - `git diff 83b6945 -- tests/ | grep '^-[^-]'` prints exactly the two lines named in verify step 3: the import and
    line 180.
- **Q9.** The new line 180 is `pytest.raises(ValueError, match="calibration")` around the same `shake(0.5, 1.0)`
  call. That matches the owner's answer in `decisions.md` ("Yes, raise"), and Task 2's commit body cites Q9.
- **B1 is closed.** I rendered flat fields in `distance`: grey 128, amber (255, 200, 0), grey 60, blue, white and
  (1, 1, 1), at 0, 5, 10 and 20 m and scales 1, 4 and 8. The centre pixel is exactly `gamma_lut(2.2)` of the colour
  (0 bytes off) in every case.
  - Only at 50 m does the centre lose 3 to 11 bytes. There the 3-sigma glow (13 wall px) reaches the frame's edges
    and some light falls into the dark air beside the wall, which is physically right.
  - The round-1 additive glow fails the new test, HALATION 0.6 fails, and 0.5 passes.
  - The regenerated PNGs show yellow as yellow, not lemon.
- **B2 is closed.** `blit_rgb` of float `[300, 127.5, 0.49]`, NaN, -5, `[inf, -inf]` and `1e300` gives (255, 128, 0),
  black, black, (255, 0, 0) and (255, 1, 0). An int64 sprite of `[2**62, -2**62, 1]` gives (255, 0, 1). All of this
  runs under `warnings.simplefilter("error")`.
- **Mutations.** I wrote 75: my 39 from round 1, re-aimed at the revised code where a pattern moved, and 36 new
  ones for this round's changes. 3 round-1 patterns no longer apply to the rewritten `_light_lut` and re-encode,
  so 72 ran: 57 were caught and 15 survived. The survivors are judged in R2-N1 and R2-N4.
  - The S4 start-point-only `_i` mutation now fails within the 1 s `deadline` instead of hanging.
  - Newly caught: the additive glow, HALATION 0.6, unweighted or max-channel scatter, flat or swapped `LUMA`, a
    no-op `_frozen` or any one cache left writable, `int(scale)`, `dim`'s exponent, every `blit_rgb` conversion
    step except the rounding mode, the line skip at `>=`, `4 * max(w, h)` or the start point only, off-left skip +1,
    `shake` unchecked, `shake` checking the jittered bodies, and `_placed_by` without `zone_x`.
- **`deadline`.**
  - After a normal exit and after an expired one, the SIGALRM handler is the original and `getitimer` is (0, 0).
  - A pure-Python `while True` is interrupted at 0.20 s by `deadline(0.2)`.
  - From a thread it raises `ValueError: signal only works in main thread`.
  - It cancels any `ITIMER_REAL` timer set outside it.
  - `pyproject.toml` has neither pytest-xdist nor pytest-timeout.
- **Timing.**
  - Idle: `PreviewDisplay.push` in `distance` at scale 8 takes a median 9.4 ms; `render` alone takes 7.2 ms.
  - Under 16 busy processes on 8 cores: the push median is 10 to 26 ms across three runs (max 55 to 70 ms), and
    `test_look.py` plus `test_canvas.py` passed three runs out of three.
- **PNGs.** I ran the verify snippet and read all six images.
  - Sizes are 1024x256 and 512x512, and the `git` text chunk is present.
  - 64x64 shows "CODE IS" over "ART". The diagonal touches no text, no disc and no sha. The sha is top right at
    128x32 and bottom left at 64x64.
  - `distance` at 5 m: every letter, both 8s and the sha are readable. Yellow and red match `led` (the red is pink in
    both, since `led` at gamma 2.2 shows 40 as 110). The glow is barely visible.

### Blocking findings

None.

### Notes (non-blocking)

- **R2-N1. Four of the seven "equivalent" survivors are observable, and this round's new code adds three more
  survivors.**
  - The plan's "Declined" paragraph says seven survivors "change no behaviour a test can observe short of timing".
    That holds for three: `text` without its y cull, `text` without the off-left skip (the `continue` still
    culls), and `_spread` without `lru_cache`.
  - It is false for four:
    - `_i` without its clamp: `fill_circle(5, 5, 1e200, c)` raises `OverflowError` because `(r + 0.5) ** 2`
      overflows a float. That breaks spec 7.4's "never raises". The hostile list's radii stop at `10**9`.
    - `_i` sending +inf to +FAR: `fill_rect(0, 0, inf, 4, c)` lights 64 pixels instead of the 0 that `_i`'s new
      docstring promises.
    - `rect` without its `w <= 0` guard: `rect(3, 0, 0, 4, c)` draws two columns. A game's health bar at width 0 would
      show this.
    - Forwarding `min(level, 1)`: the inner display gets 1.0 instead of 1.5, against loop decision 11's "forwards it
      unchanged".
  - Three survivors are new with this round's code:
    - `range(max(0, -(x // cell_w)), ...)`, a one-character slip in the new arithmetic skip: `text(-1, 0, "B")`
      draws nothing instead of B's four visible columns, so text scrolling in from the left edge loses its first
      glyph.
    - `_require_placed` checking only the first body: in a two-person custom-zone scene whose first person stands
      outside both zones, `degrade` and `shake` pass silently. All the C13 tests use one person.
    - `blit_rgb` using `np.round` (half to even): 0.5 becomes 0 (transparent) and 126.5 becomes 126, against loop
      decision 7's half up. The test's values have no exact .5.
  - **Fix.** Add these asserts. Each passes on the plan's code and fails under its mutation; I checked all seven, and
    the test file is kept in the scratchpad as `r2_extra_tests.py`.
    - Hostile list: `lambda: c.fill_circle(5, 5, 1e200, RED)` (it fills the canvas).
    - `test_rects_and_clear`: `rect(3, 0, 0, 4)`, `rect(10, 0, -3, 4)` and `fill_rect(0, 0, math.inf, 4)` light
      nothing.
    - `test_text_uses_font_and_clips`: after `text(-1, 0, "B")` against `text(5, 0, "B")`, `frame[:, 0:4]` equals
      `frame[:, 6:10]` and is lit.
    - `test_colours_clamped`: `blit_rgb([[[0.5, 126.5, 2.5]]] float32)` gives (1, 127, 3).
    - `test_preview_models_brightness`: `set_brightness(1.5)` leaves `inner.brightness == 1.5`.
    - `test_degrade_needs_the_scene_calibration`: `persons=[Person(0.1, id=1), Person(0.85, id=2)]` under
      `zone=(0.5, 0.2, 1.0, 0.8)`, and both `degrade` and `shake(0.0, 1.0)` raise `match="body 2"`.
  - That makes 3 more canvas asserts in existing tests, 1 in `test_look.py` and 1 in `test_festival.py`; the counts
    do not change. Then reword the "Declined" sentence to name only the three truly equivalent survivors.
- **R2-N2. `_i`'s new docstring is wrong about radius.** "An infinite radius or width draws nothing" is not what
  happens: `_disc` clamps `r` to 0, so `fill_circle(8, 4, inf)` and any negative radius draw the centre pixel. Fix
  the docstring to "an infinite width draws nothing and an infinite radius draws only the centre pixel". Changing the
  behaviour is not needed.
- **R2-N3. `deadline` is sound for this repo, with known limits.**
  - It is Unix-only (no `SIGALRM` or `setitimer` on Windows) and works only in the main thread.
  - It cancels any outer `ITIMER_REAL` timer, so it would silently disarm pytest-timeout's `signal` method.
  - None of these applies today:
    - The suite runs on the Mac (core plan line 730).
    - The Pi and the Omarchy box are Linux.
    - pytest runs tests in the main thread.
    - Neither xdist nor pytest-timeout is installed.
    - xdist 3.6 and later runs tests in the worker's main thread in any case.
  - It does not leak:
    - I verified the handler is restored and the timer disarmed on both exits.
    - The one window, an alarm landing between the block's end and `setitimer(0)`, leaves the `expired` handler
      installed with no timer armed. That is harmless, and the 50 ms assert has already failed by then.
  - Optional hardening: when `threading.current_thread() is not threading.main_thread()` or `signal` lacks
    `setitimer`, just `yield`. Say in the docstring that it replaces any outer SIGALRM timer.
- **R2-N4. The declined lower bound on HALATION: I agree.**
  - Spec 9.4 and the Task 6 amendment say only "a luminance-weighted halation Gaussian" of three times the sigma, with
    no amount. HALATION 0.05 and 0.01 both survive.
  - What is pinned: the glow's presence (`blue > 0`), its luminance ordering, its 3-sigma width (HALATION_SIGMAS
    2.7 fails; 3.1 survives within the 10% variance tolerance, which is fine) and its upper bound (0.5 passes, 0.6
    fails).
  - Any floor would be a number nobody specified, and verify step 5's "faint glow widest around white and green"
    is where a vanished glow shows.
  - Two other survivors are truly equivalent: `render` keeping the numpy scale unconverted, and allowing
    `np.bool_` (numpy 2's `np.True_` has no `__index__`, so it is rejected anyway).
- **R2-N5. The perf test has less headroom under load than round 1 measured.** The push median rose to 26 ms in one
  of three loaded runs, against 33 ms, though it never failed. Keep the test as it is; `-m "not perf"` is the
  documented escape for a slow box. If it ever flakes, time the median of 30 pushes instead of 20 rather than
  raising the budget.

### Owner decisions

None. Q8 and Q9 are applied exactly as answered. The C14 refinement of spec 5 is forwarded as spec drift for the
journal, and the torso floor goes to core Task 8 or 16. Neither is a gate.
