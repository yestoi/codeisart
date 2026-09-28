# Iteration 4 plan review (adversarial, operator step 2a), round 1

Plan: `docs/superpowers/plans/2026-09-28-it04-carried-input-protocol-safety.md` (uncommitted), reviewed 2026-09-27.

It was measured against:
- spec revision 3, sections 4.3, 7 (7.1 to 7.6) and 8;
- the core plan's lines 1-51, Tasks 7 and 8 with their amendments (lines 484-545), the File Structure and the runner loop (lines 2886-2901);
- 05-plan and the adversarial review, sections 7 and 10a;
- decisions Q1 to Q10 (Q10 was answered "5 captures" in `cec3db2` while this review ran);
- the roadmap's C10 and C18-C20;
- the operator design's section 5 gate table;
- HEAD `cec3db2`, whose only change from `f07afea` is to the workflow docs.

## Verdict: BLOCKED

Six blocking findings. Four are in the safety modules, which this iteration's success criterion names.
- **B1.** The flash governor passes a full-field saturated red/blue strobe at 12-15 Hz untouched. It also passes a red/green strobe that has a real luminance swing of twice the threshold. Doubling red luminance *hides* that flash.
- **B2.** The brightness limiter runs after the governor and creates flashes of its own. A static score strip strobes at 6 Hz after it. A completely static frame strobes at 5 Hz when the lux reading hovers at `night_lux`.
- **B3.** Letting a lux reading cancel the clock's night is a night-level decision, which the gate table reserves for the owner. It is also the less safe reading of a spec conflict, and there is no hysteresis.
- **B4.** The forwarded runner wiring leaves two traps.
  - `FlashGovernor(cfg.height, cfg.width, cfg.gamma)` fixes a 30-frame window, but the runner ticks at `cfg.fps`. At 60 fps, 6 flashes a second pass.
  - `BrightnessLimiter(cfg, clock, lux)` would receive the runner's monotonic clock.
- **B5.** `Scores.record` rejects numpy numbers (`np.int64`, `np.float32`) as "not a finite number". A game's score computed with numpy is never a best, and the sessions log writes it as null.
- **B6.** `test_discovery_skips_missing_modules` asserts `all_games() == []` against the real package. The day the first game module lands, a plan-literal assert must change, which is a human gate.

The rest holds. The replay matches the plan exactly. The hold logic is sound for the plan's own luminance: an independent checker found no over-budget pixel in 1,200 random trials. No committed assert changes. The night schedule across midnight, the linear-light APL and the input helpers are right.

## What I ran

Everything ran in scratch clones of `cec3db2` under the session scratchpad. The working tree was never touched.

- **Replay.** I extracted every `path`: block from the plan's text and applied the blocks task by task, tests first. Every count matches the plan:
  - Task 1: `5 failed, 76 passed`, then `81` and `229`.
  - Tasks 2 to 4: each fails collection with `ModuleNotFoundError`, then `12`/`241`, `47`/`288` and `22`/`310`.
  - Per-module counts match verify step 2.
  - The suite passes under `-W error` and `PYTHONHASHSEED` 1, 2 and 3.
  - Verify step 4 prints `[]`, and step 5 prints `[]`.
- **Committed asserts.** `diff` of the three modified test modules against HEAD shows no removed or changed line; every change is appended. The plan's "no existing test line changed" is true.
- **Probes and mutations.** The probe scripts (`probe_it04.py`, `probe_lim*.py`, `probe_slew.py`, `probe_indep*.py`, `probe_union.py`, `scroll.py`, `perf.py`, `mut_it04.py`) are in the session scratchpad. The numbers below come from them.

## Blocking findings

### B1 (Task 4, `flash.luminance` and `_Transitions`): the flash definition misses red flashes and masks real luminance flashes

Spec 7.6's single scalar ("Rec. 709 luminance with saturated red counted double") can be matched by a non-red colour. Whatever doubled red equals, the governor sees no swing. The table shows full-field frames, 90 frames at 128x32, through the plan's governor.

| Alternation | Doubled Y (governor) | Plain Y | R−G−B in light | Held ticks | `flash_area(raw)` |
|---|---|---|---|---|---|
| red (87,0,0) / blue (0,0,255), 15 Hz and 12 Hz | 0.145 / 0.072 | 0.073 / 0.072 | 0.34 / 0 | **0** | **0.00** |
| red (255,0,0) / green (0,152,0), 15 Hz and 10 Hz | 0.425 / 0.426 | **0.213 / 0.426** | 1.0 / 0 | **0** | **0.00** |
| dark red (189,0,0) / orange (255,66,0), 15 Hz | 0.315 / 0.398 | **0.158 / 0.398** | 0.74 / 0.74 | **0** | **0.00** |
| red (255,0,0) / (255,60,60), 15 Hz | 0.425 / 0.398 | 0.213 / 0.398 | 1.0 / 0.53 | **0** | **0.00** |
| white / black, 15 Hz (control) | 1 / 0 | 1 / 0 | 0 / 0 | 36 | 1.00 |

- **Row 1 is the Pokémon pattern.** It is a saturated red/blue full-field strobe at about 12 Hz, and WCAG's red-flash rule counts it (the change in (R−G−B)·320 is about 109, above 20). The plan passes it untouched.
- **Rows 2 and 3 are worse than having no red rule at all.** A plain-luminance governor would hold them: the swings are 0.21 and 0.24, over twice the 0.1 threshold. Doubling red lifts the red state's value onto the other colour's.
- **This breaks the success criterion.** "The flash governor ... hold[s] on every game and attract mode" fails on these inputs, so the plan cannot ship as written. Nothing in it tests a red/non-red alternation at matched values.

**Fix.** It is strictly tighter than spec 7.6, so it is loop-decidable ("tightening is the loop's").
- **Three signals per pixel.** Track three signals in light, each with its own `_Transitions` at `THRESHOLD`:
  - plain Rec. 709 luminance;
  - the spec's red-doubled luminance;
  - red excess `max(0, R − G − B)`.
- **A pixel transitions** when any of the three flips. `hold`, the ring and `flash_area` count that union.
- **Held pixels must advance on what was shown.** Advance every track with the *shown* output's signals (`signals(out)` where `hold`), with held flips cleared, as the prototype re-measures.
  - The plan's shortcut ("a held pixel's y is past its extreme, so the extreme stays") is valid only for the track that flipped.
  - I measured the difference. Advancing the non-flipping tracks with the input's signals lets 345 pixels reach 8 transitions in 30 frames (600 random trials). Re-measuring gives 0 over budget, worst 6.

I prototyped exactly this:
- The plan's 14 flash tests pass unchanged.
- Every row above is held and governed to `flash_area == 0`.
- The cost is 0.16 ms median at 128x32 when nothing is held and 0.26 ms on random frames, under the test's 0.5 ms.

Add a test with the four red rows at 15 Hz and 12 Hz, asserting `flash_area(raw) == 1.0`, `held_ticks > 0` and `flash_area(out) == 0.0`.

### B2 (Task 4, `BrightnessLimiter.apply`, and the tick order forwarded to it05): the limiter creates flashes after the governor

The factor follows each frame's APL instantly, and the limiter runs after the governor (spec 4, 7.2, 8.1; forwarded to it05). Any factor change is a light change on every lit pixel that the governor never sees.

- **Out-of-phase blocks.**
  - Setup: a 32x4 white score strip is static. The left and right halves each flash 3 times a second, within budget and out of phase.
  - Before the limiter, raw and governed `flash_area` are 0.0.
  - After the limiter the strip reads `128, 128, 255, 255, 255, 128, 128, 255, ...`. That is 12 transitions a second, 6 flashes, and `flash_area` is 0.031.
- **Lux at the threshold.**
  - Setup: a completely static frame at APL 0.156, with the lux reading alternating 4.9 and 5.1 per capture.
  - The cap flips between 0.06 and 0.12, so the frame strobes 128 and 196 at 5 Hz. `flash_area` of the pushed frames is 0.156.
- **Random search.** 150 trials of blocks switching at random, governed first and then limited. Up to 46% of the wall exceeds the budget in the pushed frames.

Fast attack with slow release fixes both hand-made cases: the factor drops at once and rises at most 0.01 of light per tick, so a recovery of `THRESHOLD` takes 10 ticks. In the random search, though, it still leaves 9.4% of the wall over budget under the spec's order. Putting the governor last (limiter, then governor, then push) gives 0 by construction. The cost is that held pixels can sit above the cap: up to 0.33 over it on that adversarial content.

**Fix.**
1. In it04, give `BrightnessLimiter` fast attack and slow release, with a documented `RELEASE` constant: at most `THRESHOLD / 10` of light per tick. Add tests: the out-of-phase strip, and the static frame under a flapping lux reading, both with `flash_area(out) == 0.0`. `test_white_frame_scaled_not_below_half`'s `factor == 1.0` after a black frame changes to the release ramp. It is a new test, so that is allowed.
2. Take the order to the owner (below). The strict bound needs the governor last, and that contradicts spec 4, 7.2, 7.6 and 8.1. Forward the answer to it05's tick order and to `test_push_path_order`.

### B3 (loop decision 14, "Resolved conflicts": spec 4.3 against 7.6): lux cancelling the night is an owner decision, and the less safe one

The plan resolves 4.3 ("night begins at `night_start` **or** when lux falls below `night_lux`") in favour of 7.6, so a bright reading at 02:00 gives the day cap. Three problems:
- **Owner decision.** The gate table puts "brightness ceiling, night level" with the human, and this decides when the night level applies.
- **The IMX500 sees the wall's own light.** It sits at the wall and looks at people lit by it.
  - By my estimate (two P5 panels, about 0.1 m², at brightness 0.4 and APL 0.12), the wall alone puts a few lux on a player at 1.5 m. That is the same order as `night_lux = 5`.
  - Festival lighting nearby adds to it. With lux deciding both ways, the night cap may never apply.
  - The 4.3 reading can only add night, so it fails safe.
- **No hysteresis.** A reading straddling 5.0 flips the cap every capture, which B2 shows is a strobe.

**Fix.**
- **Default to 4.3's reading:** `night = clock_night or (reading below night_lux)`.
- **Add lux hysteresis:** for example, leave lux-night only above 1.5 × `night_lux` for 10 s. Journal the values as loop proposals.
- **Update `test_lux_overrides_clock`:** at 02:00 a reading of 300 keeps night.
- **Add a flapping test:** a reading alternating 4.9 and 5.1 does not flip `cap()`.
- **Ask the owner** whether lux may cancel the clock's night, with this default.

### B4 ("Forwarded to later amendments", it05 runner; Task 4 keyword tests): the runner wiring the plan forwards is wrong twice

1. **Window in frames, runner in `cfg.fps`.**
   - The core runner loop ticks at `period = 1.0 / self.cfg.fps` (core plan line 2887), and `load_config` accepts any `fps > 0`.
   - The forwarded `FlashGovernor(cfg.height, cfg.width, cfg.gamma)` keeps `fps=FPS=30`. Its window is then 0.5 s at 60 fps, and a 6 Hz full-field strobe at 60 fps passes with `held_ticks 0`: 12 changes in one second.
   - The `fps`, `budget` and `threshold` keywords that would fix it are untested. My mutants that hard-wire `FPS`, `BUDGET` or `THRESHOLD` in the governor or in `flash_area` all survive (mutants 0-5 below).
   - **Fix:** forward `FlashGovernor(cfg.height, cfg.width, cfg.gamma, fps=cfg.fps)` (or have `load_config` require `fps == 30`). Add a test that at `fps=60` a 3 Hz strobe passes and a 4 Hz one is held, for the governor and for `flash_area`. Add one test of `budget` and `threshold` behaviour, and reject `threshold=inf`: it is accepted today and turns the governor off (mutant 15).
2. **Which clock the limiter gets.**
   - The runner's `clock` is `time.monotonic` (core Task 8), which returns a float. `BrightnessLimiter` calls `self.clock().time()`.
   - Passed literally, it05 raises `AttributeError`. Falling back to the default `datetime.now` makes headless frames depend on the time of day: the night cap below 06:00 changes the evidence.
   - **Fix:** forward a separate injected local clock (`local_clock: Callable[[], datetime]`), fixed in `run_headless` and `helpers.run` (for example the scenario's start, or 21:00), and state it in loop decision 14's interface.

### B5 (Task 3, `scores._finite`): numpy scores are silently not scores

`_finite` accepts only `int` and `float`, and `np.int64` and `np.float32` are neither. In the replay, a game's `self.scores.record(value)` behaves like this:
- `record(np.int64(7))` returns False and logs "ignoring score ... not a finite number". So does `record(np.float32(0.8))`.
- Only `np.float64` works, because it subclasses `float`.
- `SessionLog.append` writes numpy durations and scores as `null`.
- `record(..., margin=np.float32(10))` raises `ValueError`.

Games compute scores from numpy arrays: Copy Me's limb-angle match, Strongman's dB from the float32 audio features, a Tug tally from `np.sum`. The first "BEST!" would never show, and the sessions log (the owner's post-night-one data) would lose its scores.

**Fix:** `_finite` uses `look.is_real` (`numbers.Real`, not a bool) before `float()`. Add asserts that `record(np.int64(7))`, `record(np.float32(0.8))` and the log's numpy duration and score are kept. The same applies to `input._number`, which rejects `Cursor(switch=np.float32(1.25))` and `capture_grace(np.int64(10))`. That one is a note, since callers pass config ints.

### B6 (Task 3, `test_discovery_skips_missing_modules`, first line): a plan-literal assert with an expiry date

`assert all_games() == []  # no game module exists yet` reads the real `arcade/games/` package. It fails the moment M4's paint (or any game) lands. That iteration must then change a committed, plan-literal assert, and the gate table makes that a human gate ("change a plan-literal test | Human | Gate").

**Fix:** make the empty case a fake: `fake_modules(monkeypatch, {})`, then `assert all_games() == []`. The real-package check stays where it belongs, in this iteration's verify step 5.

## Notes (non-blocking)

- **N1. The 30-frame window has no margin.**
  - The plan's reading ("current plus the 29 before") lets a steady 3 Hz strobe through exactly. That is allowed.
  - The core loop doesn't sleep after a late tick (`delay <= 0` sets the next deadline and runs the next tick at once), so two pushes can land milliseconds apart. A steady 3 Hz strobe can then show 7 transitions in less than a real second.
  - The prototype's reading (hold when the previous 30 frames already hold 6) matches spec 7.6's "already transitioned six times in the last second". It gives one frame of margin at the cost of one held frame a second on an exact 3 Hz strobe.
  - Either adopt it, or forward to it05 that the loop must never push two frames within less than a period.
- **N2. The red-share cut is a cliff (spec drift for the next revision).**
  - (255,63,0) and (255,64,0) look identical, yet alternating them is a full-field flash: governor values 0.78 and 0.39, `flash_area(raw) = 1.0`, 36 ticks held.
  - A pixel at exactly 80% flips class on float rounding: (236,22,37) counts double in float64 and single in the plan's float32.
  - Fire and ember palettes with 1-LSB flicker will freeze pixels and fail the soak's `flash_area(raw) <= 0.1`.
  - Keep the spec's doubled track (B1) for now. Propose a continuous red weight for spec revision 4.
- **N3. The first swing is detected only one way.**
  - While `direction == 0`, `_Transitions.advance` tracks only the minimum. So a slow fall from the first frame is never counted as the "first swing" the docstring promises.
  - That is at most one uncounted transition per pixel per process: harmless.
  - Track both extremes until the first flip, or reword the docstring.
- **N4. The "168 of 168 killed" claim does not hold.**
  - I wrote 35 mutants of my own, and 16 survive. About six are equivalent or boundary-only:
    - `SyntaxError` is already an `Exception`;
    - clipping a LUT whose scale is at most 1;
    - `>` against `>=` at a float threshold;
    - `>=` on the hand switch;
    - lux `isnan` against `isfinite`, which differs only at ±inf;
    - removing the Edge `EPSILON`.
  - The observable survivors are:
    - 0-5: the governor's and `flash_area`'s `fps`, `budget` and `threshold` are hard-wirable (B4);
    - 15: `threshold=inf` is accepted;
    - 23 and 24: removing `EPSILON` from `Hold`'s reset and from `Cursor`'s grace;
    - 32: `e.name == module_name` loosened to a prefix, so a missing sibling helper module would be skipped silently instead of logged.
  - Each needs an assert, or the claim should be reworded.
- **N5. The noise tests are fragile.** Over 400 other body ids, `test_exit_hold_survives_spec_noise_with_the_capture_grace`'s window `3.15 <= fired < 3.8` fails for ids 138 and 259, which fire at 3.97 s and 4.27 s. If `degrade`'s noise keys ever change (the actors change again at M5, with C11 and C17), roughly one run in five fails a plan-literal test for no real reason. Bound it now at `fired < 4.4`, or allow one late fire in 40. It is a new test, so that is allowed.
- **N6. Scrolling text: forwarding a speed limit is wrong. It is a spec conflict for the owner (below).**
  - One pass of STRONGMAN at scale 2 and 10 px/s takes 17 s on 64x64 and 24 s on 128x32. Spec 7.3 has a 1.2 s dwell and doors that rotate every 5 s.
  - Held share of lit title pixels (128x32):

    | Speed | Held share | Most pixels held in one frame |
    |---|---|---|
    | 15 px/s | 4.4% | 26 |
    | 20 px/s | 15.5% | 92 |
    | 30 px/s | 36.5% | 216 |

  - A 128x32 door is 42 px wide and a 2x title is 12 px a character. "PONG" (48 px) and "COPY ME" (84 px) cannot sit still under the icon as spec 7.3 draws them, so they scroll there too.
  - The governor is right to hold, because the per-pixel rule is the spec's. The loop cannot choose between the rule and 7.3's doors.
- **N7. Q10 (answered: 5) is sensible, but its costs were understated.**
  - The question named release latency (0.55 s). It did not say that a new `Edge` press needs more than 0.55 s of hands down, so repeated raises under about 1.5 Hz merge into one press. Flap and Swat use velocity and paths, not `Edge`, so nothing shipped breaks.
  - With the grace, a Pong paddle driven by `Cursor` freezes for up to 0.55 s through a dropout instead of jumping to the hanging hand. That is the right trade.
  - The module docstring's "Every helper here ... should be given `capture_grace`" should say "the lobby's and the runner's"; games choose their own.
- **N8. MENU_ORDER against Q2.**
  - The Q2 answer gives the ship order Copy Me, Pong, Quick Draw, Dodge, Tug, Flap, Swat, **Paint**, Strongman, Freeze.
  - `MENU_ORDER` puts paint third. That follows spec 8's table, spec 9.7, 04-loop S5 and the core amendment (line 494), and spec 8 itself says "Ship order is the table order".
  - The gate table makes menu order the loop's ("journaled, never asked"), and build order lives in the roadmap (M4 paint, M7 the rest in Q2's order). So the plan's tuple is defensible.
  - But it is frozen once created, and the plan does not mention the conflict. Add a "Resolved conflicts" entry: MENU_ORDER is the menu order from spec 8's table, and Q2's ship order is the build order. Journal it, and list spec 8's sentence as drift for revision 4.
- **N9. `flash.py` imports the private `look._light_lut`.**
  - Sharing one table is right: the governor, the limiter and the looks must agree.
  - Rename it to a public `look.light_lut` (unvalidated; `flash.light_lut` stays the validating wrapper), or journal the private import.
- **N10.** `BrightnessLimiter.is_night` lets an exception from `lux()` propagate into the tick. Treat it as no reading and log once: spec 7.7 says attract never depends on a sensor.
- **N11. Forward to it05's Juice.**
  - Spec 8.1's shake is an integer offset. If its sign alternates every tick, every high-contrast edge toggles at 15 Hz, and the governor freezes ghost edges for up to a second. Dense `burst` particles over one spot do the same.
  - Add `flash_area(raw) == 0` tests for shake and burst on a high-contrast frame, next to the planned `Juice.flash` rule.
- **N12.** `Game.SCENARIOS = {}` is a mutable class default shared by every subclass that does not override it. Use `types.MappingProxyType({})`.
- **N13. Performance.** The plan's governor runs at 0.12 ms median (p99 0.14) at 128x32 and 64x64. The B1 fix runs at 0.16 ms, and 0.26 ms on random frames where the held path runs every frame. That is well inside the test's 0.5 ms and a 33 ms tick. Re-time on the Pi 5 at GATE B as planned.

## Confirmed as claimed

- **Holding cannot create a flash** under the plan's own luminance. An independent pure-Python extreme tracker ran over the governed output of 1,200 random trials (random, stepped, palette and red strobes). No pixel exceeded 6 transitions in 30 frames.
- **Per-pixel, not whole-field**, as spec 7.6 requires. Partial fields, large areas and slow ramps that cross the threshold are counted as the spec says.
- **The limiter** measures APL in linear light through the looks' table, and its lookup table scales light, not bytes. The clock schedule is right across midnight, and equal times mean never.
- **Input helpers.** `Cursor`'s reach is `Body.cursor`'s, ties included. `OneEuro` matches the paper. `Edge` and `Hold` behave as documented.
- **Registry.** `GameInfo.layouts` defaults to both layouts per Q1. Discovery tells a missing module from a broken one, and imports are guarded.
- **Hygiene.** No hardware imports, no `hash()` seeds, no sleeps or wall-clock reads in tests. Every clock is injected and every rng is `zlib.crc32`-seeded.
- **M3 slicing.** The dependency order holds: it04's modules depend on nothing new, the it05 runner consumes all of them, and the it06 director consumes the runner's lobby interface. Moving `draw_figure` and `to_wall` to it06 is listed and harmless. it05 must absorb B2's order answer and B4's wiring.

## Owner decisions

1. **Tick order: governor last?**
   - Spec 4, 7.2, 7.6 and 8.1 put the limiter after the governor, and then the 3-flashes-a-second bound fails on pushed frames (B2).
   - Slow release fixes the limiter's own strobes, but random content still leaves 9.4% of the wall over budget.
   - Governor last holds the bound by construction. Held pixels may then exceed the APL cap for up to a second.
   - Proposed default: governor last. Deadline: it05, which wires the order.
2. **May a lux reading cancel the clock's night (spec 7.6), or only add night (spec 4.3)?** This is a night-level decision under the gate table, and the camera sees the wall's own light (B3). Proposed default: only add night, with hysteresis. Deadline: it05, or prototype week at the latest.
3. **Scrolling titles against the per-pixel flash rule (N6).** The options:
   - (a) accept the governor's smear at 20-30 px/s (15-36% of title pixels held for a few frames);
   - (b) revise spec 7.6 to exempt small areas, as WCAG does;
   - (c) no scrolling titles: 1x or abbreviated.

   The plan's forwarded 10 px/s limit makes a 64x64 door title take 17 s a pass against a 1.2 s dwell. Proposed default: forward nothing as settled; it06 asks before building doors.
4. **For spec revision 4 (no answer needed now):**
   - a continuous red weight (N2);
   - spec 8's "ship order is the table order" against Q2 (N8);
   - spec 7.3's 2x titles on 42 px doors (N6).
