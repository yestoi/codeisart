# Iteration 5 plan review (adversarial, operator step 2a), round 1

Plan: `docs/superpowers/plans/2026-09-28-it05-juice-runner-headless.md` (uncommitted, 4726 lines), reviewed 2026-09-28.

It was measured against:
- spec revision 3, as amended by decisions Q1 to Q19 and the roadmap's "Spec revision 4 notes";
- the core plan's Task 8 and 9 bodies and the juice and runner amendments (lines ~502-534);
- the roadmap's carried fixes (C10 runner half, C21, C22, C25-C29);
- the it04 plan's "Forwarded" list (line 293 on) and it04 plan-review B4 and N23;
- HEAD `ee6780b`.

## Verdict: BLOCKED

Two blocking findings. Both are small to fix.
- **B1.** A game that reports `"active": np.True_` is never active. The runner tests `self._state.get("active") is True`, so a player who is playing is shown "STILL PLAYING?" and ended as `inactive` after 35 s. This is it04 B5's class of bug (numpy values silently not counted), in the rule that ends sessions.
- **B2.** The new tick-budget test times wall-clock ticks with `perf_counter` and asserts the p95 against 4 ms. Under the CPU load that the loop itself creates (parallel agents), it failed in 7 of 33 loaded full-suite runs. The plan's "one unexplained failure" (line 357) is almost certainly the same kind: the existing `test_governor_under_half_ms_at_128x32` failed in 8 of the same 33. Timing the tests on the thread's CPU clock removes it: 0 failures in 10 runs under 16 hogs, against 2 in 10 for the plan's version.

The rest holds. The replay matches the plan exactly, every frame path goes limiter, governor, push, and the exit, crash guard and presence logic do what the plan says. The notes below are mostly tests that would pin wiring the plan already gets right.

## What I ran

Everything ran in scratch clones of `ee6780b` under the session scratchpad (`it05rev/`). The working tree was never touched; this file is the only edit.

- **Replay.** I extracted all 15 `path`: blocks from the plan's text and applied them task by task, tests first, committing each task. Every count matches the plan:
  - Task 1: `4 failed, 44 passed` (the plan's four), then `48` and `338`.
  - Task 2: collection fails with `ModuleNotFoundError: arcade.juice`, then `22` and `360`.
  - Task 3: `ModuleNotFoundError: arcade.headless`, then `47` (2.6 s) and `407`.
  - Task 4: `ImportError: NullLobby`, then `11` and `418`.
  - Per-module counts match verify step 2. `git diff ee6780b -- tests/ | grep '^-[^-]'` prints nothing. The import check prints `[]`.
  - Verify step 6 prints what the plan says: raw 1.0, pushed 0.006, held 58, scaled 90, night False, crash red 96, crashes `{'spy': 1}`, at both layouts.
  - `ruff check --select F` passes on every file the plan writes, and `--select E501 --line-length 120` passes on the new modules and tests.
- **Hash seeds and warnings.** With my hogs stopped (load average about 13 from other agents), the full suite passes under `-W error` with `PYTHONHASHSEED` 1, 2 and 3: 418 passed each, about 18 s. Under the hogs, seeds 1 and 2 each had one failure, which is B2's timing.
- **Flakiness.** 63 full-suite runs with three suites at once, under seeds 1, 2, 3 and random: all passed. 33 more with 8 busy-loop hogs added: 14 runs failed, all on timing tests (B2). I found no dependence on hash order, wall-clock time or test order in the new tests: every clock is injected (`local_clock`, `FakeClock`), sets are compared as sets, and `hidden` is sorted.
- **Mutations.** 40 runner and harness mutations (`mutate.py`: tick order T1-T12, exit E1-E10, crash guard C1-C15, session rules S1-S3) and 10 juice mutations (`mutate_juice.py`), each run against the task's tests. 13 runner mutations survive; none of them is a bug in the plan's code, but each is wiring nothing pins (N2, N3, N6, B1).
- **Probes.** `probe_*.py` in the scratchpad: numpy `active`, juice effects at one spot, the crash icon's `score`, lamps and jitter against the moving-blob rule, and in-zone crowds under `REAL_NOISE`.

## Blocking findings

### B1 (Task 3, `runner._game_tick`, plan line 4012; loop decision 14, line 146): a numpy `active` is never active

```python
        if self._state.get("active") is True:
            s["active"] = self.t
```

- Spec 7.1 asks for "an `active` boolean". `np.True_` is a numpy boolean, and it is what `np.any(motion > x)` or `speed > threshold` on a numpy float returns. The game guide (line 233) tells authors to "report `active` on any tick with meaningful input", and says nothing about the type.
- **Probe.** A SpyGame reporting `{"active": np.True_}` every tick, with `inactive_seconds` 2: the prompt shows at 2 s and the session ends as `inactive` at 7 s while the game reports active every tick. With the defaults a playing player is thrown out at 35 s.
- Nothing fails: every test uses Python `True` (lines 3309-3389). Mutation S3 (`if self._state.get("active"):`) also survives, so the plan's choice of `is True` over truthiness is not pinned either.
- **Why it blocks.** It is silent and it ends a real session, which is the class it04 blocked as B5 (numpy scores). The plan fixed that class for `score` and `players` (C25) and missed it here.

**Fix.**
- Count `v is True or (isinstance(v, np.bool_) and bool(v))`, or `v is not False and isinstance(v, (bool, np.bool_)) and bool(v)`.
- Add a test: `spy(extra={"active": np.True_})` keeps the session past `inactive_seconds + PROMPT_SECONDS`; `1`, `"yes"` and `np.int64(1)` do not count (this pins S3).
- In the game guide forward (line 233), say `active` is a bool and numpy bools count.

### B2 (Task 4, `test_tick_budget_with_the_governors_share`, plan lines 4483-4521; loop decision 25, lines 190-194; "Environment facts", line 357): the budget test fails under the loop's own load

The test stamps each tick with `time.perf_counter()` and asserts `mean < 2 ms`, `p95 < 4 ms` and the governor's median under 0.5 ms.

- **Under load it fails.** With 8 `yes` hogs and three suites at once (this Mac's 10 cores busy, as when agents run in parallel), 14 of 33 full-suite runs failed:

  | Test | Failing runs | What failed |
  |---|---|---|
  | `test_flash.py::test_governor_under_half_ms_at_128x32` (existing) | 8 | median 0.543-0.551 ms |
  | `test_headless.py::test_tick_budget_with_the_governors_share` (new) | 7 | `[static-128x32]` 2, `[static-64x64]` 3, `[strobe-128x32]` 2; p95 4.04-5.23 ms, governor mean 0.41-0.85 ms |
  | `test_look.py::test_distance_keeps_up_with_the_preview` (existing) | 1 | |

  On a quiet machine the same test reports about 0.33-0.37 ms a tick (static 128x32 0.334 ms mean, 0.343 ms p95; strobe 64x64 0.371 ms mean, 0.405 ms p95, governor 54% of the tick). The code is well inside the budget; the test measures the scheduler.
- **Why.** `perf_counter` counts time the thread spends preempted. On Apple Silicon a preempted Python thread is often moved to an efficiency core, which roughly triples its timings, and a p95 over 300 ticks is exactly the statistic that catches that.
- **The unexplained failure is almost certainly this.** Line 357 records one failure in about 40 drafting runs, under `PYTHONHASHSEED=3`, name not captured. I found no hash-order dependence anywhere in the new tests, and the timing tests fail at about that rate under load. "The perf tests alone 25 times" passed because running them alone is running them on a quiet machine.
- **Controlled comparison.** Under 16 hogs, 10 runs each: the plan's test failed in 2 of 10 runs (4 test failures). The same test timing ticks and the governor with `time.thread_time()` failed in 0 of 10.
- **Why it blocks.** The iteration verify needs the full suite green, and the loop runs agents in parallel. As written the implementer or verifier will meet a red suite that is not a regression, and the plan tells them only to record it.

**Fix.**
- Time ticks and the governor with `time.thread_time()` (the thread's CPU clock, 42 ns resolution on this Mac). It measures the code's cost, which is what spec 9.2's budget is for; say so in a comment. Keep the printed report.
- The governor-median assert duplicates `test_flash.py`'s. Keep it on `thread_time` or drop it.
- Do the same in `test_juice.py`'s render timing (line 2443), which is `perf_counter` too; it did not fail in my runs, but it is the same pattern.
- For `test_flash.py:500` (existing, 2x margin): switch it to `thread_time` in Task 1 with a stated reason, which is a changed test line and needs the plan to say so; or forward it with C29 as a known flake. My default is the switch, since changing the clock does not loosen the bound.
- Rewrite line 357: the likely cause is a timing test under load; when a full-suite failure is a `perf` test, rerun `-m perf` alone on a quiet machine and record both results before calling it a regression.

## Notes (non-blocking)

**N1. "Each effect keeps the flash rule by itself" is true against the governor's 6, not the plan's 4, and not for all effects (lines 18, 118-124, 206, 234, 2464, 2769).**
- Bursts at one fixed spot, called every tick over black, make exactly 6 changes a second at the burst's centre: `flash_area(frames, budget=4)` is 0.0071, and at `budget=6` it is 0. The plan says "no pixel changes state more than 4 times a second from it alone".
- The plan's burst test moves the origin every tick (`(i * 1.5) % w`, line 2283), so it never re-bursts at one spot, and `BURST_GAP` is unpinned: the mutation `BURST_GAP = 0.3` survives, and at one spot it flashes (0.0061).
- The banner and pops are not rate-limited: a banner whose text changes every tick flashes 0.117 of the wall at 128x32 (0.122 at 64x64), and a pop every tick flashes 0.0073 at 64x64. Combinations can too: burst plus flash 0.0015, burst, flash and shake together 0.0027.
- Safety holds, because the governor sits after all of it. The claim is what is wrong: "the governor never has to hold a game for its juice" is false for games that call these every tick.
- Fix: add a fixed-spot burst case over black to `test_effects_keep_the_flash_rule_by_themselves`; either raise `BURST_GAP` to 0.5 (then 4 is true) or say 6. Reword line 18, decision 7, the module docstring, the Task 2 commit message and the game-guide forward: shake, flash and bursts each keep the rule alone; banner text, pops and combinations are the game's to pace, and the governor catches the rest.

**N2. Safety wiring the plan gets right but no test pins (surviving mutations).**
- T4: `FlashGovernor(..., fps=cfg.fps)` dropped to the default 30 survives. This is exactly it04 B4. Add a test with `cfg.fps=60` that a strobe is held to 6 a second, or at least `runner.governor.fps == cfg.fps`.
- T6: `lux=None` passed to the limiter survives. Assert the runner's limiter sees the lux callable.
- T7, T8: the game's draw after `fx.render`, and overlays before `fx.render` (the exit ring shaken), both survive. A test with a shaking fx and the ring at a known pixel pins both.
- T11: skipping the lobby's `dt`-0 tick after a rule ends a session (line 4017) survives, so the "never a blank frame" of decision 14 is untested. Assert the lobby's pixel on the ending tick.
- C6, C15: `CRASH_SECONDS` and `CRASH_RED` are only used through their names. Pin `== 0.5` and `== (96, 0, 0)`.
- C7: a crash in `draw` keeps the half-drawn frame when `canvas.clear()` is removed; nothing checks that only the icon shows.
- `debug_state` is guarded in code (C1 is killed), but `SpyGame`'s `raise_in` does not list it and the crash parametrize does not include it. Add `"debug_state"`.

**N3. The exit's person and hand rules are unpinned (E5, E6, E8, E9, E10 survive).**
- E9: exiting on any body's both hands, not the player's. E10: exiting on one raised wrist. E8: the exit hold updated only in games. E5: the block ending the moment hands drop, without the grace. E6: the block releasing on `both_hands_up` false while one hand is still up, so the lobby sees a raised hand and spec 7.3's "a raised hand starts play at once" relaunches.
- Suggested tests: a bystander with both hands up for 4 s does not exit; the player holding one hand up for 4 s does not exit; after an exit, lowering one hand then the other keeps the block until both are down for the grace; the block under `REAL_NOISE`.

**N4. Decision 24's "except `score`" is false (line 189; `_crashed`, line 3933).**
- `_crashed` filters `_state` to `score`, then calls `end_session("crash")`, whose `_to_lobby` sets `_state = {}`. A probe shows `glitch` True with no `score` key. The filtering line does nothing.
- On a crash during `launch`, `_state` is still the lobby's, so the filter would keep a lobby `score` if it had one.
- Fix the code (keep the score through the icon) or the wording. The session log's `score` is right either way: it is read before the reset.

**N5. The moving-blob rule is fragile for real lamps (decision 13, lines 139-143; `moving_blob`, line 3792).**
- A lamp the blob source misses on every 5th capture "appears" on the next and counts: the session never leaves. Missing every 20th capture, the session is still open at 12 s with `leave_seconds` 2.
- Centroid jitter of ±0.001 frame widths at 30 captures a second counts as moving: `BLOB_SPEED` 0.05 fw/s is 0.27 px a capture at the 160 px lores width.
- The leave timer resets on a single tick of evidence. The test models only a perfect lamp, and `degrade` never jitters or drops blobs.
- Forward to Task 15 and GATE A: judge displacement over a window (for example ≥0.02 fw from where the blob was about 0.5 s ago) or require sustained motion, and add jittered and flickering lamp tests. The source's 5 s scenery mask is the backstop meanwhile. Dropping a still player who shows only as light is consistent with spec 7.2.

**N6. S1 survives:** leave following only in-zone bodies, ignoring moving blobs, passes every test. Add one where a moving in-zone blob with no body holds the session past `leave_seconds`.

**N7. Smaller edges in `sense()` and `launch()`.**
- `sense()` builds `Sensed.t` and `camera_t` from the runner's `t` before `tick` increments it, so live games see the previous tick's `t` while headless ones see the scenario's. Harmless now; say which is meant.
- A malformed `latest()` shape raises out of `sense()` and the loop, not through the crash guard.
- `CAMERA_INPUTS` claims pose, blobs and motion whenever the camera is ok. M5 will need per-input availability, and the status-set test will change then.
- An unhashable lobby request, or a public `launch()` during the crash icon, are untested.

**N8. Player lock and exit under in-zone crowds hold up.** The crowd test uses only out-of-zone bodies. My probes of in-zone cases under `REAL_NOISE` (two equal players, a friend 1.25x larger, a body at the zone edge, a bystander cheering both hands up for 8 s, a smaller walker crossing) showed no lock switches and no exits.

**N9. The exit ring and markers under noise** make a `flash_area` of 0.001 at 128x32 with nothing held: small-area exempt (Q13), as intended.

## Confirmed as claimed

- **Every frame path goes limiter, governor, push** (Q11): the lobby, the title card, the crash icon, games, and the tick a session ends. T1, T2, T3, T9, T10 and T12 are killed. The governor is built with `fps=cfg.fps` and the limiter with the injected local clock (T5 killed), closing it04 B4.
- **The exit** is `Hold(cfg.exit_seconds, grace=capture_grace(cfg.camera_fps))`, updated every tick in the lobby too and reset on launch (C27; E1-E4, E7 killed).
- **The crash guard** covers `__init__`, `reset`, `update`, `draw`, `done` and `debug_state`; it logs, keeps `last_error`, logs a `crash` session, hides after 3 (Q17), and a raising lobby becomes the title card and is never called again (C1-C5, C8-C14 killed).
- **Session rules** fire in the stated order; the cap needs a non-`play` phase and more bodies than players (S2 killed).
- **Presence** counts in-zone bodies and moving in-zone blobs only, as decision 13 says; a parked lamp holds nothing in the plan's own test.
- **Carried fixes.** C22's torso floor, C25's `SessionLog` (numpy players cast, bad values raise before any write, a failed write is logged and never raises), C26's two pinned deviations and C27's caller rule all have tests that fail first for the stated reason. C29's touched items are in.
- **Hygiene.** No hardware imports in the new modules; no removed or changed existing test line; displays copy what they are pushed synchronously; `run_headless` fixes local time at `OPENING_NIGHT`; no sleeps or wall-clock reads in the new tests other than B2's timing.

## Owner decisions

None of the findings needs the owner; both blocking fixes are the loop's. For the check-in:
1. **Q17-Q19 as defaulted** (hide after 3 crashes until restart; jump shake at most every 0.25 s; bursts near a recent one dropped). Acceptable. If N1 is fixed by raising `BURST_GAP` to 0.5, Q19's default number changes with it; proposed default: the loop picks, and the check-in lists it.
2. **The moving-blob rule** (N5) is a presence rule the spec leaves to the loop, but it decides whether a lamp can hold the wall. Proposed default: forward to Task 15 and GATE A, refit on captured lamps, no owner question unless the refit changes spec 7.2's wording.

## Round 2

Revised plan (5161 lines, uncommitted) reviewed 2026-09-28 against HEAD `ee6780b`. It folds in B1, B2 and N1-N7, and records the operator's two decisions (the clock-only switch in `test_flash.py` and `test_look.py`, and `BURST_GAP` 0.5) and a new defaulted owner item, Q20 (the flash is a hold). I did not reopen the operator's decisions or the ruling on `test_governor_under_half_ms_at_128x32`.

### Verdict: APPROVED

No blocking findings.
- **B1 is fixed.** `_is_true(v)` counts `True` and `np.True_` only. The new parametrized test covers seven values, and both the truthy mutation (S3) and the old `is True` (S4) fail it.
- **B2 is fixed.** Every `perf` test times on `time.thread_time()`. Under 8 hogs and one suite at a time, the new budget test and the Juice render timing passed 15 of 15 `-m perf` runs and 6 of 6 full suites.
- **N1-N7 are folded in as claimed.** Every round-1 mutant but one now fails. The survivor, E8 (the exit hold updated only in games), is equivalent while the launch reset is there, as the plan says.
- **The new code holds up.** That covers the flash as a hold, the `latest()` shape guard, `launch` emptying `_state`, a launch ending the crash icon, and the non-string request. Three edges remain, as notes: a capture time in the future defeats the staleness rule, a public `launch` mid-session drops that session, and the lobby's `request` is read outside the guard.

### What I ran (round 2)

Everything ran in fresh scratch clones of `ee6780b` (`it05rev/s1` for the replay, `m2` for mutations). The working tree was never touched; this file is the only edit.

- **Replay.** I extracted all 15 file blocks again and applied them task by task, tests first, with Task 1's clock script run exactly as written. Every count matches the plan's table:
  - Task 1: `4 failed, 44 passed`. The clock script prints `2 files changed, 4 insertions(+), 4 deletions(-)`. Then `48` and `338`.
  - Task 2: `ModuleNotFoundError: arcade.juice`, then `26` and `364`.
  - Task 3: `ModuleNotFoundError: arcade.headless`, then `70` and `434`.
  - Task 4: `ImportError: NullLobby`, then `11` and `445`.
- **Iteration verify.**
  - Step 2: the per-module counts match the table, all 23 modules.
  - Step 3: `git diff ee6780b -- tests/ | grep '^-[^-]'` prints exactly the four `time.perf_counter()` lines.
  - Step 4 prints `[]`.
  - Step 5 prints four lines on the CPU clock, for example `strobe 64x64: tick mean 0.395 ms, p95 0.449 ms, governor 0.212 ms (54%), held 200` and `static 128x32: 0.342 / 0.352 / 0.167 ms (49%), held 0`.
  - Step 6 prints what the plan says at both layouts: raw 1.0, pushed 0.006, held 58, scaled 90, night False, crash red 96, crashes `{'spy': 1}`.
- **Warnings, hash seeds and lint.** `-W error` under `PYTHONHASHSEED` 1, 2 and 3 gives 445 passed each (about 20 s). `ruff check --select F arcade tests` passes. `--select E501 --line-length 120` passes on the new modules and tests.
- **Load, one suite at a time** (the operator's condition). I started 8 `yes` hogs, which the script's trap removed afterwards:
  - `-m perf` on `test_headless.py` and `test_juice.py`, 15 runs: 15 green (5 passed each).
  - Full suites under `-W error`, seeds 1-6: 5 green. One failed on the existing `test_governor_under_half_ms_at_128x32` alone.

  The new budget test and the Juice timing never failed. The one existing-test failure is the case the operator has ruled on. But note it happened at one suite, where the plan's "Environment facts" record 12 of 12 green. The rerun rule covers it.
- **Mutations.** 51 runner and harness mutants (`mutate2.py`) and 15 Juice mutants (`mutate_juice2.py`), each run against the task's tests:
  - my round-1 set;
  - B1 both ways;
  - ten against the new round-2 code: the launch's empty state, the icon ended by a launch, the str check, the camera, motion, audio and `Body` shape checks, `t`, `camera_t`, and the once-per-run failure log;
  - six new Juice mutants: the fade restored, the gap counted from the flash's start, `FLASH_GAP` 0.25, a flash one tick longer, `BURST_GAP` 0.45, and `BURST_NEAR` 16.

  All fail except E8.
- **Probes.** `probe_flash2.py`, `probe_flash3.py`, `probe_sense2.py` and `probe_r2.py` are in `s1`.

### Blocking findings (round 2)

None.

### Checked against round 1

| Round 1 | Claimed | Found |
|---|---|---|
| B1 numpy `active` | `_is_true`; 7-value test; guide forward | Yes. S3 and S4 killed. |
| B2 timing under load | `thread_time` in every `perf` test; Environment facts rewritten; rerun rule | Yes. Four existing lines change, clock only, thresholds kept. The new timing is green under load at one suite. |
| N1 Juice claims | `BURST_GAP` 0.5; `burst-spot` and `flash-red` cases at both layouts; wording | Yes. The gap is pinned at 14 and 15 ticks (J2, J14 killed). The wording now says 6 at most for bursts, 4 for the shake and the flash, and that banner text, pops and combinations are the game's to pace. |
| N2 wiring | tests for T4, T6, T7, T8, T11, C6, C7, C15, `debug_state` | Yes. All killed. The fps test runs a strobe at 60 ticks a second through the runner and checks `flash_area(fps=60)` is 0. |
| N3 exit rules | bystander, one hand, block under noise | Yes. E5, E6, E9 and E10 killed; E8 equivalent. |
| N4 decision 24 | `launch` empties `_state`; wording; test | Yes. The dead filter is gone; N1 mutant killed. |
| N5 lamps | forwarded to Task 15 and GATE A | Yes, in "Forwarded" with the numbers and the to-do. |
| N6 moving light holds a session | test | Yes. S1 killed. |
| N7 edges | one clock for games, shape guard, str check, icon ended by a launch, per-input forwarded to M5 | Yes. N2-N10 mutants killed. |

### Notes (round 2, non-blocking)

**R2-N1. The flash as a hold keeps the rule through the whole runner path (Q20's default is sound).**
- I ran a game calling `fx.flash` every tick through `run_headless`, the limiter and the governor. The sweep covered four colours (white, saturated red, blue and dark red (128, 0, 0)), `seconds` of 0.03, 0.2 and 1.0, and four pictures (black, grey 60, a 4 px checker, a score line). Each ran 300 ticks at both layouts.
- Every case gives a raw `flash_area` of 0 at the governor's budget, and 0 at a budget of 4. None was held.
- The flashes do show. A one-tick red flash recurs every 16 ticks (1 on, 15 of `FLASH_GAP`). A 0.2 s white flash is 6 on and 15 off.
- Flash, shake and red bursts all called every tick are held at 64x64: 179 of 300 ticks over black, 57 over the checker. At 128x32 nothing is held. That is the "together they are the game's to pace" case the docstring now names, and the governor catches it.

**R2-N2. A capture time in the future, or `inf`, defeats the staleness rule (`sense()`; `_camera_result` accepts any real `capture_t`).**
- `is_real` accepts infinities, and `sense()` checks only `now - capture_t <= CAMERA_STALE`.
- A camera whose `latest()` keeps returning one result with `capture_t` of `inf`, or an hour ahead, stays `camera_ok` with its bodies for 10 s of ticks, and presence stays true. A game sees `camera_t` of `inf` in the first case.
- The audio check has the same one-sided test.
- It matters in Task 15. A source that stamps captures on another clock, or in another unit, would freeze the last body on the wall and hold a session open forever. picamera2's sensor timestamps are nanoseconds since boot, for example.
- Fix, cheap: treat a non-finite `capture_t`, or one more than a small tolerance ahead of `now`, as malformed, the way the guard treats other shapes. Add it to the 12-shape test. Otherwise forward it to Task 15 with the source's clock contract.

**R2-N3. A public `launch()` during a running session drops that session.**
- I launched `a`, ran 1 s, then called `launch("b")`. The lobby was told nothing, the session log has no record for `a`, and `b` runs.
- If `b`'s `reset` raises instead, only `b`'s crash is logged.
- Today only `run_headless` (from the lobby) and tests call `launch`. The lobby path cannot reach this, since requests are read in the lobby tick.
- Fix: `launch` refuses, with a warning, unless the runner is in the lobby or showing the crash icon. Or it ends the running session first, with a reason the log accepts. Otherwise forward it to whichever tool first calls `launch` directly.

**R2-N4. The lobby's `request` is read and cleared outside `_lobby_call` (`_lobby_tick`).**
- A lobby whose `request` is a read-only property raises `AttributeError` out of `tick()`. A getter that raises something other than `AttributeError` is caught only because `debug_state` read it first.
- The it06 director is the only real lobby, so this is cheap to close now: do the read and the clear inside `_lobby_call`.

**R2-N5. `test_governor_under_half_ms_at_128x32` can fail at one suite under 8 hogs** (1 of 6 here). The plan records 12 of 12 green for that setup. This is inside the operator's ruling and the rerun rule. The plan's figure should just not read as "never at one suite".

**R2-N6. Earlier round-1 notes stand as forwarded:** N5 (lamps), per-input availability for M5, and N8/N9 (confirmed). The `inf` camera case (R2-N2) belongs with N5's Task 15 items if it is not fixed now.

### Owner decisions (round 2)

None needed.
1. **Q20, the flash as a hold** (defaulted). Proposed default: accept. It keeps the rule for every colour and duration I tried through the whole path. The cost is a blink instead of a glow, and the fade alternative (at most one flash a second, `seconds` capped) stays open for the check-in.
2. **Q17-Q19** as defaulted, with `BURST_GAP` now 0.5 under Q19: accept.
