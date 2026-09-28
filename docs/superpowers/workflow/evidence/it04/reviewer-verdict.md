# Iteration 4 implementation review (it04-review, opus), round 1

Commits e9b23ec..9e48c24 against docs/superpowers/plans/2026-09-28-it04-carried-input-protocol-safety.md.

## Verdict: APPROVED

## Blocking findings
None.

## Notes (non-blocking)

**Plan fidelity.**
- All 18 plan files match HEAD byte for byte, except the two ruled lines below. All 7 test modules are verbatim.
- All four commit messages and their file lists match each task's Step 5.
- The suite gives 334 passed, 0 skipped. No test line was removed or changed. The import check prints `[]`, and `all_games()` returns `[]`.

**Ruled deviation 1: `arcade/input.py:152` casts OneEuro's settings to float. Accepted.**
- Plan decision B5 says every number `arcade/input.py` takes is stored as float, and the cast honours it.
- A side effect: `OneEuro(min_cutoff=10**400)` now raises OverflowError at construction, as `Edge(grace=10**400)` already does.
- No test pins the cast; carried as C26.

**Ruled deviation 2: `arcade/scores.py:30-33`, `_finite` catches OverflowError and ValueError. Accepted.**
- Without it, a hand-edited scores.json with a huge int raises out of `Scores.__init__`, which breaks decision 10.
- Probed:
  - the file loads, drops the entry and warns;
  - `record(10**400)` returns False;
  - `record(1, margin=10**400)` raises ValueError;
  - `SessionLog.append(duration=10**400)` writes null.
- No test pins it; carried as C26.

**Parked minors, all confirmed by probe; none blocks:**
- `SessionLog.append` with a numpy int `players` (`scores.py:193,200`) raises TypeError on the file-write path, outside the OSError try. If the runner's crash end-of-session path raised, a game crash would become a runner crash. Carried with priority for it05 (C25).
- `OneEuro.__call__` does not cast `x` or `t`: a float32 sample keeps float32 state, and None raises TypeError (C29).
- A huge-int lux reading raises OverflowError (`brightness.py:82`). This is theoretical, because IMX500 lux is a float (C29).
- `FlashGovernor(0, -3)` constructs, and every `apply` then raises. It fails loudly (C29).
- The flash metrics do not check a frame's shape or dtype. They are used only by tests and tools (C29).
- A malformed `"previous"` entry is dropped but not counted in the warning (C29).
- The logger is named `"arcade.brightness"` (`brightness.py:19`) against the Global Constraint, and a verbatim test pins it. Records still reach `"arcade"` handlers. it05 tests must not match `record.name == "arcade"` for limiter logs (C29).

**Other observations:**
- `game.py:74-76`: `GameInfo(needs=[["pose"]])` raises TypeError, not ValueError. It is harmless, because discovery catches any Exception (C29).
- `games/__init__.py:46-50`: `get_game` re-imports and re-logs broken modules on every call. Cache `all_games()` at startup in it05 (C28).
- `flash.py:163-169`: `_prev` stays None after the first frame. The reviewer traced it: nothing can be held before frame 2, so it is correct but implicit.
- `test_flash.py:504`: the 0.5 ms median may be flaky on a loaded machine. Re-time it on the Pi 5 at GATE B, as the roadmap already says.
