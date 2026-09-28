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

## Round 2

Revised plan (4160 lines, uncommitted) reviewed 2026-09-28 against HEAD `5cf9943`, which records owner answers Q11 (governor last), Q12 (lux only adds night) and Q13 (small flashing areas exempt).

### Verdict: BLOCKED

One blocking finding, and it is the one the team lead asked me to judge first.
- Residual (2) is not a 7-against-6 rounding matter. The square rule never holds a pixel that is under its own budget. So any flash spread across pixels that take turns reaches the wall at full rate, over the whole field.
- Worst case: a full-field flash at 15 Hz with a swing of 0.2 in light, or at 5 Hz with a swing of 0.6. Nothing is held, and every measure the plan forwards (`flash_area`, `concurrent_area`) reads 0.
- It also shows up without an adversary. In the plan's own composed test, random blocks under the flapping sensor, 28 of 100 longer trials push square means over budget, on up to 63% of the wall's square positions.
- The fix is prototyped and small. It passes all 327 tests unchanged, and it makes the bound hold by construction.

Everything else from round 1 is fixed and verified. The Q13 geometry and guidance figures check out. The 8 claimed-equivalent survivors are equivalent.

### What I ran (round 2)

All of it ran in scratch clones of `5cf9943` (`r5` for the plan, `r5fix` for the fix). The working tree was never touched.

- **Replay.** Every file block, applied task by task with the tests first. The counts match the plan exactly:

  | Task | Failing first | Task tests | Full suite |
  |---|---|---|---|
  | 1 | `6 failed, 76 passed` | 82 | 230 |
  | 2 | collection error | 12 | 242 |
  | 3 | 2 collection errors | 51 | 293 |
  | 4 | 2 collection errors | 34 | 327 |

  - Clean under `-W error` and PYTHONHASHSEED 1, 2 and 3.
  - `git diff 5cf9943 -- tests/ | grep '^-[^-]'` prints nothing.
  - Verify steps 4 and 5 print `[]`.
  - No `hash()`, sleeps or wall-clock reads in the new tests.
- **Round-1 attacks, re-run.**
  - B1: the four red pairs and the per-signal pairs are in the tests and held.
  - B2: the out-of-phase strip after the limiter ramps 128 to 135 and back. That is under a transition, and `flash_area` is 0. The static frame under lux flapping 4.9/5.1 stays at 128.
  - B3: at 02:00 a reading of 7 keeps the night cap.
  - B4: at `fps=60` the window follows.
  - B5: `record(np.int64(7))`, `record(np.float32(8.5), margin=np.float32(0.1))`, `capture_grace(np.int64(10))` and `Cursor(switch=np.float32(1.25))` are all accepted.
  - B6: `fake_modules`.
- **New probes.** In the session scratchpad:
  - `r2_turns.py`: turn-taking attacks;
  - `r2_search.py` and `r2_compose.py`: random searches;
  - `r2_pattern.py`: gratings;
  - `r2_text.py`, `r2_ca.py`, `r2_field.py`: text measures;
  - `r2_straddle.py`: block offsets;
  - `r2_perf.py`, `r2_iter.py`: timing and loop count;
  - `mut_r2.py`: 38 mutants.

### Blocking findings (round 2)

#### B7 (Task 4, `FlashGovernor.apply`, loop decisions 16 and 17): a flash whose pixels take turns reaches the wall at full rate, and the "by construction" bound does not hold

**What.** `hold = flip.any(axis=0) & over` only ever holds a pixel that is over its own budget. The square rule (`self._square_window.count >= self.budget`) only decides *whether* those pixels are held. When every pixel stays within 6 transitions in 31 frames, nothing can be held however fast the area flashes.

The attack:
- Split the wall into G interleaved dithers.
- Each dither flashes 3 times in 6 frames, then rests while the next takes its turn.
- Every pixel stays within budget. Every 32x32 square's mean light, and the wall's, flashes at the frame rate.

Measured on the plan's code (128x32; 64x64 is the same):

| Attack | Mean swing of every square | Square-mean transitions a second (raw → pushed) | Held ticks | `flash_area` pushed | `concurrent_area` pushed |
|---|---|---|---|---|---|
| 5 dithers, 6-frame turns | 0.2 (15 Hz) | 30 → **30** | 0 | 0.0 | 0.0 |
| 3 dithers | 0.33 | 18 → **18** | 0 | 0.0 | 0.0 |
| 2 dithers | 0.5 | 12 → **12** | 0 | 0.0 | 0.0 |
| 5 dithers, 3 on 3 off (5 Hz) | 0.6 | 10 → **10** | 49 (changes nothing) | 0.0 | 0.0 |
| The plan's own ramp attack (`test_a_flash_spread_over_frames_is_held`) | 0.10 | 10 → **7** | 88 | 0.094 | 0.094 |

**How big and where (the team lead's question 1).**
- **The plan's residual (2) covers the whole field.** The columns repeat every 11 px across the wall. In one second, the governed wall mean runs 0.09, 0.19, 0.19, 0.19, 0.09, 0.09, 0.09, 0.19 and so on: a swing of 0.10 at 5 Hz for about 18 frames of every 30.
- **It goes past the success criterion** ("no full-field luminance flash faster than 3 per second", spec 7.6; "nothing flashes in the seizure band", spec section 1). It is also only the mildest member of the family: the turn-taking attack gives 15 Hz at twice the swing.
- **Plain content hits it too.** I ran the plan's `test_limiter_then_governor_never_strobes` random search for 100 trials of 90 frames instead of 30 of 60, and added `square_flashes(pushed)`:
  - 28 trials push a square mean past 6 transitions in 30 frames, with a worst of 9;
  - in the worst trial, 63% of the square positions on the wall are over budget.
- **This was already true of the round-1 plan and of spec 7.6's per-pixel rule. I missed it in round 1.**
- **It now blocks because the revision claims the opposite.**
  - Decision 16: "a flash over a large area is over 10% of the squares inside it, so neither can pass"; "a flash spread over a few frames [is] held".
  - Decision 17: "the flash bound holds on what the wall shows by construction".
  - The owner chose Q11 on that claim.
  - The soak assertions forwarded to core Task 20 (`flash_area(raw) <= 0.1`, `concurrent_area(pushed) < SMALL_AREA`) read 0 on every row above, so no later test would catch it.

**Fix (prototyped in `r5fix`).** Add a square backstop, a strict tightening that the loop can decide:
- **Hold whole squares.** After the pixel rule, find every square whose mean would make a transition while its window already holds `budget`. Hold every pixel of that square at its previous output, whatever the pixels' own budgets.
- **Re-measure and repeat** until no over-budget square flips.
  - The loop ends: the held set only grows, and showing the previous frame everywhere flips nothing, because the trackers were advanced on exactly that frame.
  - In practice it takes at most 4 `square_means` calls per tick over 100 random trials.
- **Advance** the pixel and square trackers on the shown signals, as now.

The whole change:

```diff
         hold = flip.any(axis=0) & over
+        if not (hold.any() and ((self._square_window.count >= self.budget).any()
+                                or _concurrent(flip, up, over, WINDOW) >= SMALL_AREA)):
+            hold[:] = False
+        # Square backstop: a square whose mean would make an over-budget transition is held whole, whatever
+        # its pixels' own budgets; repeat until no over-budget square flips (all held flips nothing).
+        square_over = self._square_window.count >= self.budget
+        h, w = hold.shape
+        bh, bw = _band(h, min(WINDOW, h)), _band(w, min(WINDOW, w))
+        while True:
+            shown = np.where(hold, self._shown, s)
+            means = square_means(shown)
+            square_flip, square_up = self._squares.flips(means)
+            bad = square_flip.any(axis=0) & square_over
+            if not bad.any():
+                break
+            hold |= (bh.T @ bad.astype(np.float32) @ bw) > 0
         out = frame
-        if hold.any() and (...):
+        if hold.any():
             self.held_ticks += 1
             out = np.where(hold[..., None], self._prev, frame)
-            s = np.where(hold, self._shown, s)
-            flip, up = self._pixels.flips(s)
+        s = shown
+        flip, up = self._pixels.flips(s)
         self._pixels.advance(s, flip, up)
         self._pixel_window.push(flip.any(axis=0))
-        means = square_means(s)
-        square_flip, square_up = self._squares.flips(means)
         self._squares.advance(means, square_flip, square_up)
```

**Results with the fix.**
- **Tests:** all 327 pass unchanged. Every text case still has `held_ticks == 0` and returns the same array.
- **Attacks:** every attack above gives `square_flashes(pushed) <= 6`.
  - 200 random turn-taking trials: worst 6 (the plan: 24).
  - 100 composed limiter-then-governor trials: 0 over budget (the plan: 28).
- **`concurrent_area(pushed)`** stays under 0.1.
- **Cost:** medians of 0.16 to 0.24 ms at 128x32 and 64x64, and 0.41 ms at worst, against the plan's 0.13 to 0.26 ms. That is inside the test's 0.5 ms.

**Tests to add:**
- **Turn-taking attacks.** The 5-dither 15 Hz one and the 2-dither 0.5-swing one, asserting `square_flashes(frames) >= 12`, `held_ticks > 0` and `square_flashes(out) <= BUDGET`.
- **Tighten the ramp test.** `test_a_flash_spread_over_frames_is_held`'s `square_flashes(out) <= BUDGET + 1` becomes `<= BUDGET`. That test is new in this iteration, so changing it is allowed.
- **Composed test.** `test_limiter_then_governor_never_strobes` asserts `square_flashes(pushed) <= BUDGET` in every trial.
- **Forward to core Task 20's soak:** `square_flashes(pushed) <= BUDGET`.
- **Plan text.**
  - Delete residual (2) from decision 16.
  - Reword decisions 16 and 17: every pixel holds at most `budget` transitions in any `fps + 1` frames unless it is part of a small flash, and every 32x32 square's mean always does.

### Notes (round 2, non-blocking)

**N14. Residual (1) is a named hazard, not sparkle.** It belongs with the owner (see owner decision 5 below). ITU-R BT.1702-3, Guideline 2 and its Attachment 1, says:

> "more than five light and dark pairs of clearly discernible stripes ... [that] change direction, oscillate, flash, or reverse in contrast and the pattern occupies more than 25% of the displayed screen area"

is potentially harmful. The same Attachment exempts patterns that "flow smoothly across, into, or out of the screen in one direction", which covers scrolling titles.

A counterphase grating passes the plan's governor untouched, and the fix too: 1 px lines every 11 px, 12 pairs across 128 px, over the whole wall, reversing every frame (15 Hz).
- Held ticks: 0.
- `flash_area(pushed)`: 0.188.
- `concurrent_area`: 0.094.
- Square means: constant.

With 2 px lines (18% one way) it is held.

The spec cannot catch this at all, only at a lower rate. Spec 7.6's per-pixel rule already lets a 50% grating reverse at 3 Hz, and pixels taking turns can move a sparse grating around at 15 Hz under any per-pixel budget. A rule that counted every flipping pixel, whatever its budget, would have to sit above the 6-12% of the wall that scrolling titles already flip each frame (measured). Moving figures in the mirror, which I did not measure, will be in the same range. So no cheap governor rule separates the grating from ordinary motion.

Recommended loop-level tightening, optional:
- Cap the over-budget flipping pixels of *both* directions at `FIELD_AREA = 0.125` of the whole wall per frame. That matches Q13's wording, "below a fraction of the field".
- Measured maxima for text: 0.099 for 1x titles at 30 px/s on 128x32, 0.084 for 2x, and 0.072 on 64x64. Text passes.
- The 12-line grating (0.188) would be held.

**N15. "10% is 2.5 times stricter" overstates the margin.**
- The concurrent rule counts rises and falls apart, so up to about 2 x 9.9% of a square can be flashing at once, in opposite phase.
- BT.1702's "combined area of flashes occurring concurrently" does not split by direction.
- Against 25% the real margin is about 1.25x, not 2.5x. Say so in decision 16, or adopt N14's field cap.

**N16. The geometry and the guidance figures check out.**

Geometry:
- 32 px at P5 (5 mm) is 16 cm, which is a 10-degree field at 2 x 0.915 x tan(5°) = 16.0 cm, so 92 cm.
- 102 px is 25.5 cm², which is 0.006 sr at 65 cm.
- WCAG 2.2's 0.006 sr is 25% of a 10-degree field.
- BT.1702-3 says 25% of the displayed screen area and more than 3 flashes (6 changes) in a second. I read the PDF.
- At the spec's distances the rule is stricter still:
  - The mat starts 1.5-2 m out. At 1.5 m a 32 px square is 6 degrees.
  - At 3.7 m and beyond, the whole 64 x 16 cm wall sits inside one 10-degree field, and at most about 10% of it can flash one way.

Windows:
- The squares sit at every offset (`_band` has n - k + 1 rows), so nothing straddles a boundary: a 110 px block was held at all 105 offsets tried on both layouts.
- Small flashes in separate squares can add up to at most about 10% of the wall per direction, about 400 px. A dither can reach 9.4% of every square, which is the N15 margin.

**N17. The spec's threshold is relative, and the guidance's is absolute.**
- BT.1702-3 (SDR included) and Ofcom call a flash potentially harmful at a change of 20 cd/m² when the darker image is below 160 cd/m². Separately: "irrespective of luminance, a transition to or from a saturated red".
- Spec 7.6 uses 0.1 of relative light. On a panel whose white at `brightness` 0.4 is L cd/m², the broadcast threshold is 20/L of light.
- Outdoor P5 modules are rated in the thousands of cd/m², so 0.1 is likely several times laxer than BT.1702.
- Measure L in prototype week, where the lux-meter step already is. Then set `THRESHOLD = min(0.1, 20 / L)`. That is a spec value, so it is an owner item (below).

**N18. Three of my 38 mutants survive, all observable but minor.** The other 35 were killed, including every square, band, concurrent, release and lux-hysteresis mutant. The survivors:
- `concurrent_area`'s `budget` keyword hard-wired to `BUDGET`;
- `square_flashes`'s `window` keyword hard-wired to `WINDOW`;
- `held_ticks` counted only when more than one pixel is held.

Add one assert each.

**N19. The writer's 8 surviving mutants are equivalent. I checked each against the code.**
- `need <= factor`: equal values give `min(need, factor + RELEASE) == need`.
- `factor >= 1.0`: the factor is never above `need <= 1.0`.
- `level < cap`: at equality `cap / level` is exactly 1.0.
- `start <= end`: equal times give an empty window in either branch.
- The bool check on `fps`: True is 1, under 2.
- `np.bool_`: `isinstance(np.bool_(True), numbers.Real)` is False.
- `_Transitions` not copying: no array it keeps is changed in place. It is fragile, though; keep the copy.
- The first-frame `_shown`: on frame 2 every pixel window is 0, so `hold` is empty and `_shown` is never read.

The mutation claim is accurate.

**N20. The square flag is global.** One square over budget anywhere lets over-budget pixels be held anywhere, so a scrolling title smears while an unrelated corner is being governed. It is conservative. With B7's backstop the flag can become local (`square_over` dilated to pixels), or stay global and be documented in decision 16.

**N21. Text margins are thin.**
- Worst `concurrent_area` over the ten titles, "TUG" and a stroke-heavy "MMMM WWWW HHHH MMMM", at 20-30 px/s: 0.090 at 2x and 0.074 at 1x, against 0.1.
- A heavier font or 3x text would be held. Forward to it06: door titles stay in the 5x7 font at 2x and at most 30 px/s, with `concurrent_area < 0.09` asserted on the real door frames.

**N22. Two small things.**
- Decision 17 says "every trial is held somewhere", but the test does not assert it. Add `assert g.held_ticks > 0` or drop the sentence.
- BT.1702's note that more than 5 s of near-threshold flashing may be a cumulative risk is not addressed. Put it in the game guide beside the pattern rule.

### Owner decisions (round 2)

5. **Regular patterns (N14).**
   - BT.1702 treats stripes that reverse or oscillate as potentially harmful, when there are more than 5 light-dark pairs over more than 25% of the screen. Spec 7.6 has no pattern rule.
   - The governor cannot enforce one cheaply without also holding moving figures. Q13 lets sparse gratings reverse at 15 Hz.
   - Proposed default:
     - make it a content rule: the game guide, plus a `pattern` check in core Task 20's soak (no reversing or oscillating stripes with more than 5 pairs over more than 25% of the wall);
     - the loop adds N14's 12.5% field cap to the governor.
   - Deadline: before the first attract mode or game lands (it05 or M4).
6. **Absolute flash threshold (N17).**
   - Spec 7.6's 0.1 of relative light against BT.1702's 20 cd/m².
   - Proposed default: measure the wall's white at `brightness` 0.4 in prototype week, then set `THRESHOLD = min(0.1, 20 / L)`.
   - Deadline: GATE B.

Sources checked: [ITU-R BT.1702-3 (11/2023)](https://www.itu.int/dms_pubrec/itu-r/rec/bt/R-REC-BT.1702-3-202311-I!!PDF-E.pdf), Guidelines 1 and 2 and Attachment 1, read in full; [International Guidelines for Photosensitive Epilepsy: Gap Analysis (PMC11872230)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11872230/) for WCAG's 0.006 sr / 10-degree / 25% and Ofcom's 25%; [Wilkins, Emmett and Harding 2005, Epilepsia](https://onlinelibrary.wiley.com/doi/10.1111/j.1528-1167.2005.01405.x) for the stripe-pair limits. The [Ofcom guidance note PDF](https://www.ofcom.org.uk/__data/assets/pdf_file/0021/16248/gn_flash.pdf) returned 403; its figures here are as quoted by the sources above.

### Round 2 addendum: governor timing and the lint note

**N23. The governor at 0.24 ms is acceptable. Deferring the check to GATE B is sound, and nothing here blocks.**

*The 0.2 ms figure is a measurement, not a budget.*
- Spec 7.6 says "Measured cost 0.2 ms on the Mac": that is what the review prototype took. The plan's "spec 7.6 budgets 0.2 ms" (decision 11) misreads it.
- The budgets the spec does set are for the whole tick, in section 9's Budget item: `runner.tick` must average under `ARCADE_TICK_BUDGET_MS`, which is 2.0 ms on the Mac, with p95 under twice that, over 300 ticks. On the Pi 5 the same test runs with 20 ms in prototype week.
- The effects module (Juice) has its own figure: under 0.5 ms at 64x64 with a full particle pool.

*My measurements on this Mac, holding path, random frames:*

| Code | Median | p95 | Worst |
|---|---|---|---|
| The plan's governor | 0.24-0.26 ms | 0.31-0.33 ms | 0.53 ms |
| With B7's backstop | 0.23-0.24 ms | about 0.30 ms | 0.41 ms |
| The limiter | 0.04 ms | | |

Together the governor and limiter are about 15% of the Mac's 2 ms tick.

*On the Pi 5.* At these array sizes numpy is dominated by per-call overhead, so a slowdown of a few times is plausible. That is an estimate, not a measurement: about 0.5-1.2 ms, against a 20 ms tick budget and a 33 ms period. The margin runs the wrong way, but it is an order of magnitude wide.

*A cheaper held path would not help.* The held path is two `np.where` calls and a second `flips` on 3x32x128 floats. Shaving it saves microseconds that no budget asks for.

*Fixes (non-blocking):*
- In decision 11 and the "Environment facts", reword "spec 7.6 budgets 0.2 ms" to "spec 7.6 measured 0.2 ms for the prototype; the budget is the tick's".
- Keep the 0.5 ms test.
- Forward to it05: the runner's tick-budget test must include a scenario that keeps the governor on its holding path (for example `claps` at 12 Hz, or a strobe), not only static attract frames. It must also report the governor's share of the tick.
- At GATE B, time `FlashGovernor.apply` and `BrightnessLimiter.apply` on the Pi 5 at both layouts. Record the result against the 20 ms tick.

**N24. The lint note is accurate and touches no new test code.**
- `ruff check --select F` passes on all 18 files the plan writes.
- `--select E501 --line-length 120` flags exactly one line: `tests/arcade/test_config.py:95` (123 characters).
- That line is identical at HEAD `5cf9943` (the same line 95, 123 characters). The plan's diff to that file is 10 inserted lines and no changed ones.
- No new or changed line in any test or source file is over 120 characters.

## Round 3 (confirm-only)

The revised plan (4363 lines, uncommitted) was reviewed on 2026-09-28 against HEAD `5cf9943`, under owner decision Q14 (apply B7, confirm only) and Q15 (guide rule, soak check and field cap). Settled questions were not reopened.

### Verdict: APPROVED

- B7 is applied as specified. With the field cap turned off, the plan's governor gives the same output as my round-2 fix, frame for frame, on 286 inputs.
- Residual (2) is gone. Decisions 16 and 17 are reworded as asked. Every test and assert I asked for is present and passes.
- The `BACKSTOP_PASSES = 8` bound cannot flip anything, cannot hang, and only tightens the bound.
- Q15's cap holds the 12-pair grating, and the titles pass untouched. Content hovering at 12.5% does not strobe.
- Every count in the plan replays exactly.

Nothing blocks. Three small test gaps and one overstated sentence are below as notes.

### What I ran (round 3)

All of it ran in a scratch clone of `5cf9943`. The working tree was never touched.

- **Replay.** Every file block, applied task by task with the tests first, and committed in the clone. The counts match the plan:

  | Task | Failing first | Task tests | Full suite |
  |---|---|---|---|
  | 1 | `6 failed, 76 passed` | 82 | 230 |
  | 2 | collection error | 12 | 242 |
  | 3 | 2 collection errors | 51 | 293 |
  | 4 | 2 collection errors | 41 | 334 |

  - `-W error` and PYTHONHASHSEED 1, 2 and 3 each give `334 passed`.
  - The per-module collect counts match verify step 2's table.
  - `git diff 5cf9943 -- tests/ | grep '^-[^-]'` prints nothing.
  - Verify steps 4 and 5 both print `[]`.
  - `ruff --select F` is clean on the 18 files. E501 at 120 flags only the committed `tests/arcade/test_config.py:95`, as before.
  - The new tests have no `hash()`, sleeps or wall-clock reads.
- **B7 as specified.** I loaded my round-2 `r5fix` governor beside the plan's and turned the plan's field cap off (`FIELD_AREA = 2.0`). Outputs and `held_ticks` were identical on all 286 inputs:
  - the 5-, 3- and 2-dither attacks;
  - 120 random block trials and 120 random turn-taking trials, on both layouts;
  - 40 noise runs.

  The code diff against `r5fix` is only the field clause, the `for`/`else` bound and comments.
- **Decision 17's claim.** On the test's own seed, the round-2 governor without the backstop pushes a square's mean past budget in 5 of the 30 trials (worst 8). The plan's governor pushes at most 6, and every trial holds something. The claim is accurate.
- **The bound.**
  - By reading the code:
    - The fallback shows `_prev` whole.
    - It advances the pixel tracker on `_shown`. Re-applying the value a tracker was advanced on can never flip it: a rise needs `direction <= 0` and a fall needs `direction >= 0`, and a swing that big would have flipped on the frame before.
    - It advances the square tracker on `square_means(_shown)` with explicit zero flips, and both windows push zeros.
    - So it flips nothing, and the loop is a `range`, so it cannot hang.
  - Timed with a forced fallback (a square tracker that always flips): median 0.41 ms at 128x32 and 0.47 ms at 64x64, worst 0.50 ms.
  - Pass counts, measured as `square_means` calls per `apply`:
    - at most 3 over all 286 inputs above;
    - at most 2 in 100 composed trials and in 200 random turn-taking trials;
    - 4 at most from a hill-climb with passes unbounded, searching frame sequences after a prologue that puts every square over budget with no pixel over its own.

    Nothing reached 8, and the fallback never fired.
- **Q15.**
  - The review's grating is held on both layouts. `flash_area` is 0.1875 raw and 0.0 governed.
  - Over-budget flips peak per frame at:
    - 0.0994 for the ten titles at 1x and 30 px/s on 128x32;
    - 0.0845 at 2x;
    - 0.0718 on 64x64.

    These are the plan's figures, and nothing is held.
  - "MMMM WWWW HHHH MMMM" at 2x and 30 px/s reaches 0.131 and is held for 6 frames, as decision 16 says.
  - The boundary test is sound. On both layouts, 16 px lines flip exactly 512/4096 of the wall, and `>=` holds that. Removing (0, 0) in the lit phase leaves 511 flips, with square means constant and one-way concurrency at 6.25%. The `>` mutant fails the test.
  - Hovering results are in N28.
- **Round-2 attacks, re-run** (`r3rev/p4_attacks.py`, all on the plan as written):

  | Attack | Result |
  |---|---|
  | Composed limiter-then-governor, 30 trials x 60 frames (the test's seed) | Square flashes pushed: worst 6, 0 trials over budget, every trial held something, concurrent under 0.1 |
  | Composed, 100 trials x 90 frames | Square flashes pushed: worst 6, 0 trials over budget, every trial held something, worst concurrent 0.0996 |
  | 200 random turn-taking trials (2-7 dithers, bursts of 2/4/6, 4 group shapes, random colours, both layouts) | Square flashes pushed: worst 6 |
  | Text: titles, "TUG" and "MMMM WWWW HHHH MMMM" at 1x/2x, 20-30 px/s, both layouts | Only the MMMM case above is held. Square flashes pushed: at most 1 |
  | Timing on random frames (held path) | Median 0.236 ms at 128x32 and 0.247 ms at 64x64, worst 0.30 ms |
  | Timing on turn-taking | Median 0.18-0.23 ms |

  All timings are under the test's 0.5 ms.
- **Mutants** (`r3rev/mut.py`): 19 aimed at this revision, run against Task 4's tests. 16 fail:
  - N18's three;
  - the field cap at `>`, removed, at 0.1 and 0.2, and counting every flip rather than over-budget ones;
  - the backstop removed;
  - the fallback holding nothing, logging every time, or looping 2, 3 or 9 passes;
  - a dilation that misses the edge;
  - trackers advanced on the input.

  3 survive (N25, N26).
- **Round-2 notes folded in:**
  - N15: decision 16 gives the 1.25x margin.
  - N18: the three asserts are present, and each kills its mutant.
  - N20: the global flag is documented in decision 16.
  - N21: forwarded to it06.
  - N22: `held_ticks > 0` is asserted in the random search, and the cumulative-risk note is in the game guide.
  - N23: decision 11 and "Environment facts" are reworded. The it05 holding-path scenario and GATE B timing are forwarded.
  - Q16: `THRESHOLD = min(0.1, 20 / L)` is under GATE B.

  All present as claimed.

### Blocking findings (round 3)

None.

### Notes (round 3, non-blocking)

**N25. The fallback's tracker invariants are not pinned.** `test_the_backstop_gives_up_by_holding_the_whole_frame` checks the output, the pass count, `held_ticks` and the log, but not what the trackers were advanced on. Two mutants survive all 41 tests:
- Dropping `square_flip = square_up = np.zeros(...)`, which keeps the last pass's square flips. This looks like the plan's own mutant (5), "a fallback that keeps the trackers' flips", which the plan says fails.
- Replacing `shown, means = self._shown, square_means(self._shown)` with `means = square_means(shown)`. The pixel tracker then advances on signals the wall never showed.

The code as written is right, and the path is unreached, but it is the safety path. After the loop in that test, add:

```python
    assert np.array_equal(g._shown, signals(out, 2.2)) and g._square_window.count.max() == BUDGET   # nothing counted
```

Verified: the test passes on the plan, and the line kills both mutants.

**N26. The square flag is no longer tested.** With the backstop in place, removing `square_over.any()` from the small-flash condition passes all 41 tests. The effect is observable: in `test_held_pixels_are_measured_as_shown`'s blinker case, 155 of the 179 changes pass instead of 131. Decision 16 names the flag as one of the three conditions, so pin it with `assert len(changes(out, 0, 127)) < 140` beside the existing `> 120`. Verified: it passes on the plan and kills the mutant.

**N27. "Which only a bug could cause" (decision 11) is too strong.** The termination argument bounds the passes by the number of squares, not by 8. I could not reach 8: random content gave 3 at most, and a hill-climb gave 4. But I have no proof that crafted square histories cannot chain further. Either way the fallback is safe. It only tightens, freezes for at most the second in which squares are over budget, and costs at most 0.5 ms. Suggested wording: "which no search has reached (the most seen is 4)". The `BACKSTOP_PASSES` comment ("the review saw 4 at most") is already accurate.

**N28. The field cap does not strobe on its own.** I ran content hovering at 12.5% on both layouts:
- 16 px gratings with one pixel dropped on alternate frames, on every third frame, or by half-seconds;
- 11 px gratings with random rows cut, flipping 11-14%;
- random dots reversing at 12.1-12.9%.

The cap holds and releases in turn. It only removes transitions: on the dropped-pixel gratings, the per-pixel maximum falls from 31 to 17-23 a second, and frames flipping 10% of the wall fall from 30 to 16-22 a second. Square means stay constant.

A 300-trial random search compared the cap on against the cap off and against the raw frames. The worst differences:

| Measure | Cap on minus cap off | Cap on minus raw |
|---|---|---|
| `flash_area` | +0.017 | never above raw |
| Per-pixel transitions in any 31 frames | +2 | +1 |
| Frames a second flipping 10% of the wall | +1 | +1 |

Square flashes stayed at 6 at most, and the per-frame over-budget flip share at 0.1248. These are timing shifts of a few pixels, not a flash of an area.

`flash_area(pushed)` can exceed 12.5% (0.19 in the search), because the cap is per frame and different pixels spend their over-budget flip in different frames. The plan claims no bound on it, and the soak asserts `flash_area(raw)`, so nothing is wrong. It is worth knowing when reading soak output.

Scripts: `r3rev/` in this session's scratchpad:
- `replay.sh`;
- `p1_equiv.py` (B7 equivalence);
- `p2*_passes.py` (the pass searches);
- `p3*_field.py` (the cap hovering);
- `p4*_attacks.py`, `p5.py`, `p6.py`, `p7.py`;
- `mut.py`.
