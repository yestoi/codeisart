# Iteration 4 orchestrator report (it04-impl, opus; subagent-driven-development with sonnet implementers)

## Completed
- All 4 tasks landed on main from BASE e9b23ec, one commit each. Each task had a task review: sonnet for Tasks 1-3, opus for Task 4. An opus review of the whole branch ran last.
- 16 of 18 plan files are byte-identical to the plan. The 2 that differ are the ruled deviations below. All test modules are verbatim.
- Plan verify steps 1-5 and 7 pass: 334 collected, 334 passed, 0 skipped, per-module counts as planned, no removed test lines, heavy imports `[]`, `all_games()` `[]`. Step 6 has no visual output this iteration.

## Deviations
1. `arcade/input.py:152`: `OneEuro.__init__` stores `float(min_cutoff)`, `float(beta)` and `float(d_cutoff)`, per the plan's interface text and B5. It was amended into the Task 2 commit, and no test changed.
2. `arcade/scores.py` `_finite` catches `(OverflowError, ValueError)` from `float(value)` and returns None, per decision 10. It was squashed into Task 3 with a local, non-interactive `rebase --autosquash`, which rewrote the Task 3 and Task 4 SHAs. Nothing had been pushed, and no test changed.
3. The Task 1 commit had a "Claude Sonnet 5" trailer and was amended to the plan's exact message: a331590 became 257d30e.
4. Parked minors and the it05 caller rule. They are in reviewer-verdict.md and the roadmap (C25-C29).
5. The operator guard hook blocked the recursive delete of the git-ignored `.superpowers/sdd/2026-09-28-it04-carried-input-protocol-safety/`, so that directory is left in place.

## Test status
Command: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`

Full suite after each task, all with 0 skipped:

| After | Passed |
|---|---|
| Task 1 | 230 |
| Task 2 | 242 |
| Task 3 | 293 |
| Task 4 | 334 |

## Commits
- 257d30e fix(arcade): circle draws its centre at tiny radii, huge ints clamp, apply_gamma copies, preview settings checked at construction (it03 C18, C19, C20)
- 8d2a2e9 feat(arcade): Edge, Hold, Cursor and One Euro input helpers with graces sized in camera captures (core Task 8 part, it02 C10)
- 1ea6069 feat(arcade): GameInfo and the Game protocol, guarded registry in MENU_ORDER, nightly scores and the sessions log (core Task 7)
- 9e48c24 feat(arcade): flash governor holds flashes past 3 a second unless small, brightness limiter caps the picture level by night and day (core Task 8 part)
