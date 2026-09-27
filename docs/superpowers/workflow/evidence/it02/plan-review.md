# Iteration 2 plan review (adversarial, operator step 2a)

Plan: `docs/superpowers/plans/2026-09-27-it02-carried-sensed-actors.md` (uncommitted), reviewed 2026-09-27 against
spec revision 3, the core plan (lines 1-51, Task 3 and 4 bodies, per-task amendments, spec drift), 05-plan, the
roadmap's carried fixes with `evidence/it01/reviewer-verdict.md`, the operator design section 5 gate table, and HEAD
`7697d01`.

## Verdict: BLOCKED

Four blocking findings. Three are one- or two-line fixes: the C1 resend interval, NaN brightness, and `degrade`
input alignment. The fourth, the one-shoulder centre, is a small semantic change to `Body`, and it must land before
the plan's tests pin it.

## What I ran

- **Replay.** I cloned HEAD into a scratch directory and extracted every `path`: code block from the plan's text, task
  by task. Every observed count matches the plan:
  - Task 1: the DDP and display tests give `4 failed, 8 passed` before the fix; colorlight gives the `BRIGHTNESS_EVERY`
    ImportError; after the fix, `37 passed` and `81 passed`.
  - Task 2: `33 failed, 29 passed` before, then `62` and `116`.
  - Task 3: gitignore `3 failed, 3 passed` before, then `16` and `127`.
  - Task 4: `17` and `144`. Task 5: `15` and `159`. Task 6: `170 passed`, 0 skipped. The whole suite takes 1.5 s; the
    slowest test takes 0.29 s.
- **Iteration verify.**
  - Step 3: `git diff 7697d01 -- tests/ | grep '^-[^-]'` prints exactly the four lines named. Each replacement is a
    superset, so no assert is removed.
  - Step 5: `check-ignore` exits 1 for the nested fixture path.
  - Step 6: the import leaves `[]` hardware modules loaded.
  - `doctor --require ""` exits 2.
  - `doctor --require pose` gives `ok  ... landmarker ran in 20 ms`, exit 0; with `--timeout 0.01` it is
    `UNAVAILABLE ... did not finish within 0.01 s`, exit 1, in 1.1 s wall time.
- **Falcon Player.** I checked the plan's Falcon Player claims against the `ColorLight-5a-75.cpp` fetched into the
  scratchpad, and they hold:
  - `m_msgs[0]` is the 0x0A packet, with a second copy for firmware 13 and later, and all of `m_msgs` goes out from
    `PrepData()` every frame.
  - The sync packet goes out from `SendData()`, twice on firmware 13 and later.
  - Our byte layout matches theirs: data[0..2] = b and data[3] = 0xFF for 0x0A; data[22], data[23] = 5 and
    data[25..27] for 0x01.
  - The same file also says: "Brightness may only work on newer firmware. Doesn't seem to work on v2.x and v3.x".
- **Revision 2 tests.**
  - Carried verbatim: `test_body_requires_17_keypoints`, `test_body_cleans_bad_keypoints`,
    `test_skeleton_indices_valid`, and five of the six actor tests.
  - Changed as the amendment says: `test_scene_assigns_ids_and_ticks`.
  - Dropped as the amendment says: `test_raised_wrist_and_both_hands`, `test_sensed_defaults_and_primary` and
    `test_with_motion_rasterizes_boxes_and_keeps_existing`. Their surviving asserts (center, height, nose, a faint
    wrist, the `given` motion identity, 2x2 resampling) reappear in the replacements.
- **Mutations.** I applied ten single mutations to the plan's code (list under N6). Five were caught and five
  survived.
- **Probes.** I probed edge cases in `_clean`, `_level`, `place`, `reach`, `Person.wrist`, `shake` and `degrade`, and
  measured the cursor and `zone_x` spread under `REAL_NOISE`.

## Blocking findings

### B1. Task 1 / Loop decision 1 (C1): the brightness resend every 30 pushes rests on a false premise

- **What.** `BRIGHTNESS_EVERY = 30`. The plan justifies 30 by saying that resending more often would change three
  plan-literal tests, and that "at push 30 no existing test reaches it".
- **Why it blocks.** The premise is true for every frame and for every 2nd push, but false for 30 as a minimum. I ran
  the three plan-literal tests plus `test_starts_at_the_safe_brightness_until_told` at each interval:
  - `BRIGHTNESS_EVERY = 1` gives 5 failures.
  - `= 2` gives 4 failures (the reference encoder pushes twice).
  - `= 3` passes all 7.
  - The whole suite at 3 passes except the plan's own new test, which pins 30.

  So the loop can cut the window after a card brownout from 1 s to 0.1 s without touching any plan-literal test. C1 is
  a must-land-before-GATE-B safety fix whose stated goal is "a card brownout must not come back at full brightness".
  Choosing a 10x longer exposure than the tests force, and justifying it with a constraint that doesn't hold, leaves
  C1 only partly fixed.
- **Is the gap acceptable?** On firmware that honours the 0x01 packet's level, the gap is moot, because that packet
  carries the level on every push. On firmware that honours only 0x0A, the gap is up to 1 s at the card's power-on
  level, which is a visible glare flash at night. Nothing is gained by accepting it.
- **Fix.**
  - Set `BRIGHTNESS_EVERY = 3`: the smallest value no plan-literal test reaches, 100 ms at 30 Hz, and 77 bytes per
    100 ms.
  - Rename and rewrite the new test to push twice (no 0x0A), then push a third time and assert
    `[frame, brightness, rows...]`.
  - Keep the reset on `set_brightness`.
  - Change the docstring's "within a second" to "within 0.1 s".
  - Rewrite Loop decision 1's reason: 3 is the floor set by the two pushes in `test_push_matches_reference_encoder`.
    Every frame (Falcon Player parity) and the doubled packets for firmware 13 and later stay with GATE B's firmware
    record.
- **Is every frame "tightening"?** The team lead asked whether resending every frame would count as tightening.
  Adapting `sock.sent[1:] == expected` to `sent[1] == brightness_packet(..)` and `sent[2:] == expected` asserts
  strictly more, but it changes the pinned packet stream. The operator table puts "change a plan-literal test" with
  the owner. Using 3 avoids the question.

### B2. Task 1 (C1): `_level(NaN)` is 255, so a NaN brightness fails open to full

- **What.** In `show/display/colorlight.py`, `_level(level) = int(max(0.0, min(1.0, level)) * 255)`. `min(1.0, nan)`
  returns 1.0, so NaN becomes 255. Observed:
  - `_level(nan) == 255`.
  - `ColorlightDisplay(..., brightness=nan).push(...)` sends frame byte 255.
  - `set_brightness(nan)` sends a 0x0A packet with 255.
- **Why it blocks.** This is the one function that enforces the hardware ceiling, in a file this task rewrites for
  brightness safety.
  - NaN reaches it through the plan's new unvalidated `brightness=` keyword.
  - It also reaches it through the daemon: `show/config.py` validates only `brightness_cap`, and
    `effective_brightness()` is `min(nan, 0.4)`, which is `nan`. So `brightness = nan` in `show.toml` lights the wall
    at 255.
  - It also reaches it through any future computed level, such as night dimming from a NaN lux reading.
- **Fix.** `if not level > 0.0: return 0` (NaN or non-positive gives dark), then `int(min(1.0, level) * 255)`. Add
  `assert brightness_packet(math.nan)[13] == 0 and frame_packet(math.nan)[35] == 0` to a new test, and optionally make
  `set_brightness` and the constructor raise `ValueError` for NaN. I verified that the change keeps every existing
  assert, including `brightness_packet(1.7)[13] == 255` and `brightness_packet(-1.0)[13] == 0`, with the suite green
  apart from B1's test.

### B3. Task 6, `degrade`: a stream that does not start at t = 0 silently gets zero latency

- **What.** `degrade` keys `seen` by the enumeration index `i`, and computes `src = min(floor(k / fps / TICK), i)`. For
  frames whose `t` is not `i * TICK`, `src` is clamped to `i`, so every capture comes from the current frame.
  - `degrade(iter(scene(...)[90:]), dropout 0, jitter 0)` gives camera ages `{0.0, 0.033, 0.067}` instead of
    `{0.167, 0.2, 0.233}`.
  - The first tick is fresh with `camera_seq` 31.
  - Nothing raises.
- **Why it blocks.** It breaks the plan's own docstring ("capture k is taken at k/fps from the scene frame at or
  before that time"), and it does so silently. `degrade` is the shared noise model that "game tests run their
  canonical scenarios under" (spec 6.4). Any later caller that slices, offsets or chains a stream would test against
  a perfect-latency camera without knowing it: a REPL step starting at t0, a bot loop resumed mid-run, a replayed
  segment.
- **Fix.** At the top of the loop, raise
  `ValueError("degrade needs a 30 Hz scene that starts at t=0; frame {i} has t={s.t}")` when
  `abs(s.t - i * TICK) > 1e-6`. Alternatively, key by `round(s.t / TICK)` and document that frames before the first
  are unavailable. Add a test asserting that `list(degrade(iter(source[30:])))` raises.

### B4. Task 4 / Loop decisions 2 and 5: one confident shoulder moves the cursor 0.17 of the wall and `zone_x` 0.12, on 31% of `REAL_NOISE` captures

- **What.** `shoulder_mid` with one confident shoulder returns that shoulder, so its x is off the body centre by half
  a shoulder width. `anchor`, `place` (and so `zone_x`) and `reach` (and so `cursor`) all centre on it.
  - On the actor figure with the right arm up, the right shoulder's confidence going from 0.31 to 0.29 moves `cursor`
    from (0.708, 0.024) to (0.848, 0.061) and the anchor x from 0.500 to 0.428.
  - Under `degrade(**REAL_NOISE)`, a still player with the right hand up gives these values, counted only on
    captures where the raised wrist is confident:

    | | Both shoulders confident | One shoulder confident (31% of captures) |
    |---|---|---|
    | Raised-wrist `u` | 0.706, sd 0.021 | clusters at 0.51-0.58 and 0.82-0.94 |
    | `zone_x` | 0.502, sd 0.004 | 0.36-0.39 and 0.60-0.63 |

    One-shoulder captures are 93 of 299, which matches `2 * 0.15 * 0.85` plus jitter.
- **Why it blocks.**
  - Doors are selected by `zone_x`, and a door is a third of the wall. The cursor drives Pong's paddle and every
    pointing game.
  - The tracker (Task 16) anchors on the same point.
  - Feel budgets and bot win rates computed under `degrade` would be tuned against this artefact.
  - The plan's test pins the jumpy semantics (`one.shoulder_mid == Keypoint(0.4, 0.4)`). Once committed, fixing it
    means changing a plan-literal assert, which the gate table gives to the owner.

  Spec 5 only says the nose is used for the raise line when both shoulders are missing. It does not require the
  horizontal centre to jump.
- **Fix.** With exactly one confident shoulder, keep its y (the raise line is unchanged) but take the centre's x from
  `hip_mid` if seen, else from a confident nose, else from the shoulder.
  - I prototyped this by overriding `shoulder_mid`. On the one-shoulder captures, `u` became 0.719 (sd 0.069) and
    `zone_x` 0.497 (sd 0.049), against 0.706 and 0.502 with both shoulders.
  - Update `test_nose_fallback_only_without_shoulders`'s `one` asserts to the new x.
  - Add `test_one_shoulder_does_not_move_the_centre`: on the actor figure, `|anchor.x|`, `cursor[0]` and `zone_x`
    each change by under 0.03 when one shoulder crosses `MIN_CONF`.
  - Record it as a loop decision.

## Notes (non-blocking)

N1. **`test_real_noise_matches_degrade_defaults` turns a routine refit into an owner gate** (Task 6). It asserts that
`REAL_NOISE` equals `degrade`'s defaults. Spec 6.4 fixes those defaults, and REAL_NOISE is meant to be refit from the
real fixtures (the plan's own comment; spec 9.5). After GATE A the loop would have two options, both bad: drift the
spec defaults, or change a plan-literal test (owner). Fix now: assert that the key set is
`{fps, latency, keypoint_dropout, jitter}` and that `degrade(scene(ticks=1), **REAL_NOISE)` runs. Pin the spec
defaults against literals in a separate assert.

N2. **`Person.wrist` crashes for a body partly out of frame** (Task 5). `_keypoints_at` builds a `Body`, whose
`_clean` zeroes out-of-frame keypoints, then reads `frame.shoulder_mid.y` and `frame.hip_mid.y`. Observed:
`AttributeError: 'NoneType' object has no attribute 'y'` for
`Person(y=0.3, height=0.6).jump(at=0, height=0.2).wrist(...)` and for `Person(y=1.05).wrist(...)`. Task 20's
`hostile_mix` ("keypoints at 0 and 1") is built from actors. Fix: compute `top` and hip y from the unclamped pose
offsets (`cy + (shoulder_dy - REACH_TOP_TORSOS * torso_dy) * h`) and use `REACH_TOP_TORSOS`, not a literal 1.05.

N3. **`shake` ignores the scene's calibration** (Task 6). It re-places bodies with `Calibration()`. A
`scene(..., calibration=cal)` body that was in the zone is out of the zone inside the shake window (observed). Add
`calibration=None` as `degrade` has, or keep each body's `in_zone` and only re-map it.

N4. **`Sensed.motion` is shared and mutable.** `degrade` hands the same array to up to three ticks, and
`with_motion` returns `self` when the shape already matches. A consumer that writes into `sensed.motion` corrupts
later ticks. Fix: in `Sensed.__post_init__`, set `motion.flags.writeable = False`, a one-line guard that costs
nothing.

N5. **The cursor flips to the hanging wrist when the raised wrist drops out.** This happens on 15% of `REAL_NOISE`
captures (the `u` range of a still player is 0.08-0.92 with both effects). `Body.cursor` is stateless by design, so
every cursor consumer needs grace or hysteresis. Say so in the Task 8 `input.py` and Task 9 director amendments
(`Hold(grace=0.25)` covers dwell, but not a paddle).

N6. **Claimed behaviours with no test.** Each of these mutations survived the plan's tests:
- the bind failure no longer closes the socket;
- `_number` accepts booleans (`"min_height": true` loads as 1.0);
- no warning for unknown calibration keys;
- `_clean` stops clamping confidence to 0..1 (a confidence of 5 stays 5);
- `vx` from a forward difference (non-causal).

Add:
- a `socket.bind` monkeypatch that asserts `closed`;
- a `("min_height", True)` case;
- an unknown-key caplog test;
- a new test (not the verbatim revision 2 one) for confidence NaN, 5 and -1, and x = inf;
- `Person(0.1).walk(0.9, 2.0).body_at(0.0, 0).vx == 0` and `body_at(2.0, 0).vx == approx(0.4)`.

Caught: C1 start level, C2 dtype, C5 NaN, degrade start, the end of the shake window.

N7. **Thread leak** (Task 3). `test_within_gives_up_at_the_timeout` and `test_within_raises_what_the_function_raised`
each leave a daemon thread sleeping 3 s. This is harmless but avoidable: use a `threading.Event`
(`stop.wait(3)`, then `stop.set()` after the assert).

N8. **`tests/test_gitignore.py` reads the user's global excludes.** On this Mac `.superpowers/` is ignored globally. A
machine whose global file ignores `data/` would fail the nested-path test. Use
`git -c core.excludesFile=/dev/null check-ignore ...`.

N9. **The start level is the approved default, not a new ceiling, but it is a second copy.** `SAFE_BRIGHTNESS = 0.4`
equals spec 4.3's approved `brightness` and `show.toml`'s `brightness_cap`, so no owner decision is taken. However,
`make_display` does not pass the configured level, so an owner who lowers `arcade.toml`'s `brightness`, or the
daemon's 0.15 operating level, still gets 0.4 until `set_brightness`. The runner calls that first, so the window is
tiny. Optional: pass `brightness=getattr(cfg, "brightness", SAFE_BRIGHTNESS)` from `make_display`. That needs
`Recorder.__init__` in `tests/test_colorlight.py` to accept `**kwargs`, a helper edit with no assert change; journal
it.

N10. **Coordinate spaces are undocumented, and M5 will build on them.**
- `Calibration.zone` says "camera space", but keypoints are already mirrored. If `mirror` changes after
  `arcade calibrate`, the zone is flipped.
- `place_blob` compares blob x to the zone, but spec 5 mirrors only in `mirror_keypoints`. Blobs from `blobs.py` will
  be unmirrored unless Task 15 flips them.
- `motion_rect`'s rectangle is in "normalized" units on the 128x64 grid, while the real grid is the zone crop at the
  wall's aspect (spec 5). So motion_rect x is a wall or zone fraction, not the camera x that `Person(x)` uses.

State all three in docstrings now (zone and blobs in the mirrored display space; motion in zone or wall fractions).

N11. **Forward gap for M3 and M4: `Blob` has no identity or velocity.** Spec 7.2 presence counts "a moving in-zone
blob", 7.7 NEAR needs a moving blob for 1 s, and Paint (Task 10) draws "each tracked blob ... from its last position".
None of these can be computed from spec 5's `Blob`. This is a spec gap, not plan drift. Decide in M3 (runner-side
matching, or a `Blob.id` added by `blobs.py`); `Sensed` may grow fields.

N12. **Small robustness items.**
- `gamma = inf` and `*_seconds = inf` load; reject non-finite `gamma`.
- A `bind` failure on a missing interface raises a bare `OSError` without the iface name.
- The Global Constraints line "SDL and fake model it in the preview" is not true of `SDLDisplay`, which "shows full
  brightness on purpose". Modelling arrives with `PreviewDisplay` in the look task, so reword.
- `Sensed.blobs` says "brightest first", which actors cannot honour because `Blob` has no brightness.

N13. **Verified and fine.**
- A NaN box does not raise in `place` or `reach` (not in the zone, `zone_x` 0.0).
- `reach` never divides by zero: `bottom - top >= 0.05 * torso` for any hip position.
- `_resample` keeps lit cells both ways.
- `_fires`, `tempo` and `wind` fire exactly once per event (tempo at 8 bpm values; claps at 300 offsets).
- `degrade` at fps 7 and 60 behaves.
- Mirroring happens nowhere in this iteration's data path, so it cannot be applied twice, and the actors' right hand
  lands at x > 0.5, as spec 5 requires after mirroring.
- No `print` in library code; no `hash()` or `random`; hardware imports are inside probes and constructors.

## Owner decisions

None is needed for this plan to proceed once B1-B4 are fixed. Loop decisions 2-10 are all within the loop's remit:
- none sets a brightness ceiling, night level, gamma placement, dwell time, presence threshold or feel budget;
- none changes a plan-literal assert (the three drops and one change are the amendment's).

With B1's fix, C1 needs no owner call. Queue two items for GATE B with C4's firmware record; they are not decisions
for this iteration:

1. Falcon Player's source says card brightness "may only work on newer firmware; doesn't seem to work on v2.x and
   v3.x". If the 5A-75E ignores both the 0x0A packet and the 0x01 packet's level, then under "pixels are never scaled
   for brightness" nothing caps the wall. Measure it with the `rgb` pattern at 0.1 and 1.0. If the card ignores it,
   where brightness is applied (in software or on the card) is the owner's decision (gate table: "Brightness ceiling,
   night level, where gamma is applied").
2. Resending on every frame, and doubling the 0x0A and 0x01 packets on firmware 13 and later, changes the packet
   stream that plan-literal tests pin. That is the owner's call when the firmware is known.

## Round 2

Revised plan re-reviewed on 2026-09-27. I made fresh scratch clones of `7697d01` and applied the plan's code blocks
from its text; the working tree is untouched apart from this file.

### Verdict: BLOCKED

B1, B2 and B3 are closed. B4 is only partly closed: the fix routes the centre through `hip_mid`, and `hip_mid` jumps
the same way when one hip drops out. The new statistical test sets its tolerance just above that leftover jump and
runs on `REAL_NOISE`, so a modest refit (dropout 0.20) would fail a plan-literal tolerance and hand the owner the
same lock-in that B4 and N1 were about. The fix is two lines of code plus one tightened test, and I have verified it
(R2-B1).

### What I ran

- **Per-task replay** (`advrev/r2u`: tests first, then source, task by task). Every count the plan states was
  observed:
  - Task 1: colorlight collection error, then `4 failed, 8 passed`, then `40 passed` and `84 passed`.
  - Task 2: `36 failed, 29 passed`, then `65` and `122`.
  - Task 3: `within` ImportError and gitignore `3 failed, 3 passed`, then `16` and `133`.
  - Task 4: 2 collection errors, then `19` and `152`.
  - Task 5: collection error, then `16` and `168`.
  - Task 6: collection error, then `30` and `182`.
  - The whole suite is `182 passed` in 1.7 s; the slowest test takes 0.28 s.
- **Round-1 failing cases, re-run.**
  - `_level` of (NaN, -1, 0, 0.4, 1.7, inf, -inf) gives (0, 0, 0, 102, 255, 255, 0).
  - `degrade` raises `ValueError` for `src[90:]`, for `iter(src[90:])` and for a stream with a dropped frame.
  - `shake` followed by `degrade`, and a 30-minute scene (54000 ticks), go through `degrade` without error.
  - The 0.31/0.29 shoulder figure now moves the anchor, cursor and `zone_x` by less than 0.03.
- **Mutations** (`advrev/mut2.py`, on the revised code). 19 of 20 are caught:
  - Caught: the interval back to 30; no reset after a resend; the old `_level`; `level <= 0` (NaN passes); the C1
    start level; the C2 dtype check; bind closes the socket; the daemon's uncapped start level; bool rejected;
    unknown keys warned; the conf clamp; motion read-only; B4's old centre; a half-way centre; no nose fallback; no
    timing check in `degrade`; velocity one tick ahead; the end of the shake window; `shake` ignoring the
    calibration.
  - Survived: "`set_brightness` does not reset the count" (R2-N1).
  - All five of round 1's survivors are now caught.
- **Assert audit.** I diffed every file between the round-1 and round-2 replays.
  - The only changed asserts are the `one` asserts in `test_nose_fallback_only_without_shoulders`. They are this
    plan's own text: the core plan names the test but gives no body, and none of it has been committed. So no
    plan-literal or committed assert changed.
  - Every other test change adds cases or asserts. `test_real_noise_matches_degrade_defaults` became
    `test_real_noise_is_a_degrade_setting`, which still pins the spec 6.4 defaults, now against literals (N1 as
    asked).
  - No `print` in library code (`arcade/main.py`'s prints are the CLI), no `hash()` and no `random`.
- **Owner decisions.** No new ones. Loop decision 1 leaves every-frame resend with GATE B; no ceiling, night level,
  gamma or feel budget moved.

### B1-B4 status

- **B1: closed.**
  - `BRIGHTNESS_EVERY = 3`. `test_brightness_packet_resent_every_3_pushes` pins the order: frame, brightness, rows.
  - The docstring says 0.1 s, and loop decision 1's reason is now correct.
  - `make_display` passes the configured start level, the daemon's `effective_brightness` included (it is a property,
    checked).
- **B2: closed.** `if not level > 0.0: return 0`. `test_nan_or_negative_brightness_fails_dark` covers both packets,
  the constructor and `set_brightness`. A NaN `show.toml` brightness now fails dark through `effective_brightness`.
- **B3: closed.** The check is `abs(s.t - i * TICK) > 1e-6`, tested for a sliced stream and a gapped one.
  `scene` builds `t = i * TICK` exactly, so a long scene never trips it.
- **B4: partly closed. See R2-B1.**

### Blocking findings

**R2-B1. Task 4 `Body.shoulder_mid` and Task 6's statistical test: the one-shoulder centre still jumps through a
single hip, and the test is tuned to that leftover jump on refit-able noise.**

- **What.** With one confident shoulder, the plan takes x from `hip_mid`. `hip_mid` is itself a single hip whenever
  one hip is under `MIN_CONF`, and that is half a hip width off centre.
  - I broke down the plan's own still-player run (`REAL_NOISE`, 299 captures). Every one of the 29 `zone_x`
    outliers (9.7%) is a capture with one shoulder and one hip, and the nose was confident in all 29.
  - Those captures move `zone_x` by up to 0.099 (a door is 0.33). Captures with one shoulder and both hips (64)
    move it by at most 0.005.
- **The test.** `test_still_player_keeps_cursor_and_zone_steady_under_real_noise` runs on `REAL_NOISE`, with
  tolerances of 12% (cursor) and 15% (`zone_x`) against measured values of 6.7% and 9.7%.
  - At dropout 0.20 and jitter 0.01 it fails (`zone_x` 15.4%). At 0.25 both asserts fail (20% and 27%).
  - Loop decision 11 says `REAL_NOISE` is refit from the GATE A fixtures, and a Pi camera at night dropping 20%
    of keypoints is plausible.
  - A failing refit would then force either a code change under time pressure or loosening a plan-literal tolerance,
    and the gate table gives loosening to the owner.
- **Why it blocks.**
  - This is B4's defect class at two-thirds of the size. The tracker (Task 16) and door selection build on the
    anchor and `zone_x`.
  - It also brings back, through a new test, the refit lock-in that N1 removed from
    `test_real_noise_matches_degrade_defaults`.
- **Fix (verified).**
  1. In `shoulder_mid`, use the hip midpoint only when both hips are confident, else a confident nose, else
     whatever hip is seen, else the shoulder:
     ```python
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
     ```
     Update the docstring and loop decision 2 to match ("x from both hips, else the nose, else one hip, else the
     shoulder").
  2. In `test_nose_fallback_only_without_shoulders`, after the `no_hips` assert, add:
     ```python
         one_hip = {RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0), RIGHT_HIP: Keypoint(0.55, 0.7, 0.0)}
         assert figure(one_hip).shoulder_mid == Keypoint(0.5, 0.4)    # one hip is off centre too: the nose
     ```
  3. In the statistical test:
     - Run `degrade(source, fps=10, latency=0.15, keypoint_dropout=0.15, jitter=0.01)`, the spec 6.4 values as
       literals, not `**REAL_NOISE`, so a refit never touches it. Rename it to `..._under_spec_noise`.
     - Tighten both tolerances to `<= 0.02`.
     - Fix the comment and the Environment-facts line.
- **Evidence for the fix.**
  - The whole suite is `182 passed`.
  - The still player measures 0.0% cursor and 0.0% `zone_x` outliers at spec noise, and stays under 0.02 up to
    dropout 0.25 (at 0.30 it is 4.8% and 8.0%).
  - The tightened tests catch every regression tried: the old centre (3 tests fail), the round-2 order with a single
    hip first (2 tests), a half-way centre (3) and a 75%-of-the-way centre (3). With the plan's tolerances, the 75%
    variant passed the statistical test (3.5% and 5.0%).
  - The test is deterministic: the noise is keyed by `zlib.crc32` of (tag, tick, body id, joint) over a fixed scene,
    and `test_degrade_is_deterministic` checks it across `PYTHONHASHSEED` values.

### Notes (non-blocking)

**R2-N1. The reset on `set_brightness` is untested.** The mutation "no reset on `set_brightness`" survives. The test
calls `set_brightness` right after a resend, when the count is already 0. Fix: push twice, call `set_brightness(0.2)`,
clear the socket, push twice, and assert there is no 0x0A packet; then push once more and assert exactly one
`brightness_packet(0.2)`. I verified that this passes on the plan's code and catches the mutation.

**R2-N2. `Sensed.__post_init__` freezes the caller's array, not only the record's.**
`self.motion.flags.writeable = False` acts on the array that was passed in. After `Sensed(0.0, motion=grid)`, the
producer's own `grid[0, 0] = True` raises "assignment destination is read-only" (observed). A camera or blob source
(core Tasks 14-15, `camera.latest()`) that reuses one grid buffer would crash on its next frame. `Sensed(motion=None)`
(the revision-2 scenario `decode` still builds one) raises `AttributeError: 'NoneType' object has no attribute
'flags'`. Fix:
```python
    motion = np.asarray(self.motion, bool).view()
    motion.flags.writeable = False
    object.__setattr__(self, "motion", motion)
```
Add `assert grid.flags.writeable` to `test_sensed_defaults`. Name the decode path in the core Task 7 amendment (use
the empty grid, not `None`). Producers still must not mutate a grid after handing it over; say so in the docstring.

**R2-N3. Loop decisions are numbered 1-8, 11, 9, 10.** Renumber 11 to come after 10, so the journal entries and their
references (for example "Loop decision 11" in round-2 text) are unambiguous.

**R2-N4. Carried from round 1, unchanged.** N11 (`Blob` identity and velocity) is deferred to M3 by the operator,
which is acceptable. N5 is carried in the `cursor` docstring and loop decision 5; the Task 8 and Task 9 amendments
must pick it up when those plans are written.

### Owner decisions

None for this plan. The two GATE B items from round 1 stand unchanged: whether the card honours brightness on this
firmware, and every-frame resend with doubled packets on firmware 13 and later. R2-B1's fix is what keeps a later
`REAL_NOISE` refit from becoming an owner decision.

## Round 3 (confirm)

Confirm-only pass on 2026-09-27, after the owner approved applying the R2-B1 fix (decisions.md Q7). I made a fresh
scratch clone of HEAD `07c96b1` (`advrev/r3`) and applied the plan's code blocks from its text, task by task; the
working tree is untouched apart from this file.

### Verdict: APPROVED

Every round-2 item is applied correctly. Both deviations from R2-N2 are right, and I found no regression.

### What I ran

- **Per-task replay.** Every count the plan states was observed:
  - Task 1: collection error, then `4 failed, 8 passed`, then `41` and `85`.
  - Task 2: `36 failed, 29 passed`, then `65` and `123`.
  - Task 3: ImportError and `3 failed, 3 passed`, then `16` and `134`.
  - Task 4: 2 collection errors, then `19` and `153`.
  - Task 5: collection error, then `16` and `169`.
  - Task 6: collection error, then `30` and `183`.
  - Whole suite: `183 passed`, 0 skipped, 1.7 s.
- **Round-2 against round-3 replay diff.** Only the files these items name changed: `arcade/sensed.py`,
  `tests/arcade/test_sensed.py`, `tests/arcade/test_festival.py` and `tests/test_colorlight.py`.
- **Mutations** (`advrev/mut4.py`). 19 of 19 are caught, including the one that survived round 2 ("no reset on
  `set_brightness`") and two new ones: freezing the caller's array, and `None` not mapping to the empty grid.
- **B4 regression mutations** (`advrev/mut3.py`). 4 of 4 are caught: the old centre, the round-2 order (a single hip
  first), a half-way centre and a 75%-of-the-way centre.
- **Still player at spec 6.4 noise.** 0.0% cursor outliers and 0.0% `zone_x` outliers, and still 0.0% at dropout
  0.25.

### Items

- **R2-B1: applied as written.**
  - `shoulder_mid` follows the order: both hips, else the nose, else one hip, else the shoulder. The docstring and
    loop decision 2 match.
  - `one_hip` gives `Keypoint(0.5, 0.4)`.
  - The still-player test runs on the spec 6.4 literals, is renamed `..._under_spec_noise`, and allows at most 0.02
    for both measures.
  - Loop decision 11 and the Environment facts are updated.
- **R2-N1: applied.** `test_set_brightness_restarts_the_resend_count` is the scenario I proposed, and it catches the
  mutation.
- **R2-N2: applied, and both deviations are accepted.**
  - `motion=None` becomes the empty `(0, 0)` grid. That is correct: my suggested `np.asarray(None, bool)` gives a 0-d
    `array(False)`, so the writer's version is the right one.
  - `... .motion is given` became `with_motion(...) is held and np.shares_memory(held.motion, given)`. A record that
    holds a read-only view can no longer satisfy `is given`. The new assert still pins "no copy, no resample" and
    adds that `with_motion` returns the same record, so it is not weaker. The test is this plan's own and not
    committed.
  - `assert grid.flags.writeable` pins that the caller's array stays writeable.
  - A non-bool input (for example uint8) is converted to a bool copy. That is harmless, and spec 5's motion is bool.
- **R2-N3: applied.** Loop decisions run 1-11 in order.
- **R2-N4: applied.** "Forwarded to later amendments" carries the cursor hysteresis (Tasks 8 and 9) and the
  scenario `decode` empty-grid rule (Task 7). The roadmap carries C10 and C11 (`07c96b1`).

### Blocking findings

None.

### Notes

- **R3-N1 (cosmetic, optional).** The `Body.cursor` docstring (plan line 2167) still says "15 percent of captures
  under REAL_NOISE", while loop decision 5 now says "at the spec 6.4 dropout". Align the wording if the file is
  touched again; no test depends on it.
