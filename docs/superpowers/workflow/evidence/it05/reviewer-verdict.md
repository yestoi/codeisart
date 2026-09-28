# Iteration 5 implementation review (it05-review, opus), round 1

Commits 4971882..a1320bc against docs/superpowers/plans/2026-09-28-it05-juice-runner-headless.md.

## Verdict: APPROVED

## Blocking findings
None.

## Notes (non-blocking)

**Plan fidelity.**
- All 16 Python blocks are identical to their files at the commits that added them.
- The only edits to existing tests are the four `perf_counter` → `thread_time` lines in `test_flash.py:500,502` and `test_look.py:172,174`, as the plan allows.
- No `print` in library code; `arcade/games/` is untouched.
- The suite gives 448 passed, 0 skipped. A tick is about 0.34 ms, and the governor is about 54% of it.

**The wall-safety property holds: no ungoverned or unlimited frame ever reaches the display.**
- `display.push` is called only at `runner.py:545`, with `governor.apply(limiter.apply(canvas.frame))` built in the same `try`.
- If the limiter or governor raises, nothing is pushed. The governor's shape check raises before it changes any state.
- If `tick()` raises, in strict mode or not, `_push` is never reached and the wall keeps its last governed frame.
- All four backends and `RecordingDisplay` copy or send the frame before `push` returns.
- The reviewer's probe:
  - Wraps `governor.apply` and `display.push` over 900 ticks, strict and non-strict, at both layouts.
  - Game: strobes the whole wall, uses every Juice effect, and raises at random in update, draw, done and debug_state.
  - Lobby: strobes and raises partway through draw.
  - Every push was the governor's latest output, with one apply per push.
  - Governed output: `square_flashes` at most 6, `concurrent_area` at most 0.0996, `flash_area` at most 0.107.
- `run_headless` goes through the same `tick` and `_push`.

**Rulings on the parked minors: none blocks.**
- **Numpy-array `phase`** (`runner.py:509-510`): raises ValueError out of `tick()` in non-strict mode on every tick once the cap condition holds, so `loop()` dies. This is an availability bug, not a flash hazard. It is the most serious item: one game value can stop the arcade, which breaks the crash guard's promise. Fix it before main or a supervisor ships (C30).
- **Object-dtype motion grid in `sense()`** (`runner.py:600`): also escapes the loop, but the data comes from our own sources (C30).
- **Rival timer** (`runner.py:124-130`): keeps counting while the locked player is missing, so the lock can switch on the player's first tick back. A behaviour bug (C31).
- **The rest** (C32). Each raises into the crash guard or leaves the wall on its last governed frame:
  - `echo` on unhashable values;
  - the guard's scope over fx and overlays;
  - two stateless title cards;
  - `SessionResult.score`'s raw type (the log nulls it);
  - `freeze()` with no cap;
  - `echo` rate;
  - burst warnings;
  - launch-refusal log rate;
  - `helpers.run` against spec 9.1;
  - the unguarded public `end_session()`;
  - a partial lobby frame, which is still governed.

**Push failures.** If `display.push` raises after the governor ran, the governor has counted a frame the wall never showed. Under repeated display errors, the wall can show about one more transition a second than counted. The one-frame margin covers it. Note it when the Colorlight backend's error handling is reviewed (C30).

**Weak test.** No test makes the limiter or governor raise inside `_push` and asserts that nothing is pushed; only a raising display is tested (`test_runner.py:837`). Carry it (C30).
