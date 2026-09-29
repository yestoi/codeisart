## Completed
- I0 (C50), main checkout, test first: `tests/arcade/test_config.py` got `test_gamma_outside_1_to_2_2_is_refused` (0.22, 22.0, 0.5, 2.3), `test_gamma_1_and_2_2_are_taken` and `test_the_shipped_arcade_configs_are_in_the_gamma_bound` (`arcade.toml`, `arcade.mac.toml`). The four refused cases failed first ("DID NOT RAISE ValueError"). `arcade/config.py` now raises `ValueError("gamma must be 1.0 (the card applies gamma) to 2.2 (bytes as they are), got ...")` after the finite check; lines 101-105 are unchanged. Config file: 49 passed in 0.05 s, every new case under 0.005 s. Full suite: 1145 passed, 1 skipped, in 237.90 s. Committed as 1c9b723, which is BASE.
- GROUP 1, T-wall (opus, worktree from 1c9b723, branch `worktree-agent-aedd1bec507ec1a6f`, commit 2038301). It touched its five owned files only: `show/wall.py`, `show/main.py`, `tools/wall_pattern.py`, `tests/test_wall_hold.py` (new, 69 tests), and `tests/test_main.py` (only the one test at 289-300 replaced).
  - What it built: `HOLD_S`/`SETTLE_SENDS`, `from_dark` priming, `clock`, `holding`, the quiet hold, and the in-place `self.governor.__init__(h, w, gamma, fps=fps)` at the hold's end with `held_ticks` carried and one `apply(self.last)` not sent (B1). There is one `_govern`. `_send(` has two call sites (lines 103, 110) and `display.push` one (line 133).
  - `show/main.py`: `_now` is set in `start` and `step`. Both `_open_wall` wraps pass `from_dark=True, clock=lambda: self._now`. `_push_failed` is gone. A held step calls `_failing(now)` without logging.
  - `tools/wall_pattern.py`: its wrap passes `from_dark=True` and no clock.
  - Red first: every new or changed test failed on today's code. The file first failed at import (`HOLD_S` missing). With the two constants added, the cases failed with a TypeError (no `from_dark`), the AST test failed on main.py's wrap, and the test_main replacement failed with an AttributeError (no `holding`). The implementer also ran mutation checks: without the B1 re-init 8 tests fail, and with the re-init but no priming apply 9 fail.
- I checked the exact tests against the plan myself. The plan's block at lines 81-238 matches `tests/test_wall_hold.py` line for line once blank lines are ignored; the only addition is the docstring the plan gives. The `tests/test_main.py` replacement is byte-identical to plan lines 243-259.
- Merged with `--no-ff` as da20a3a. After the merge:
  - T-wall's files plus `tests/test_wall.py tests/test_wall_close.py tests/test_main.py tests/test_wall_pattern_governed.py tests/test_show_soak.py`: 155 passed in 32.26 s.
  - The full suite: 1230 passed, 1 skipped, in 242.13 s.
- I1 checks, all at da20a3a:
  - Collected: 1231. Skips: 1 (`tests/test_sandbox.py:153`). Last suite time: 242.13 s, under the 250 s limit.
  - New tests' seconds: `tests/test_wall_hold.py` took 8.00 s in main (69 passed), under the 9.5 s allowance; the implementer measured 8.25 s in the worktree. The slowest cases are the eight `test_one_torn_push_at_any_call_...` cases at about 0.7 s each. I0's new tests take under 0.01 s in total.
  - `pgrep -fl python` and `pgrep -fl pytest`: nothing left running, in main and in the implementer's report.
  - `git diff 0dae849 -- arcade/flash.py arcade/brightness.py show/display/colorlight.py`: empty.
  - `git diff b83045d --stat -- arcade/runner.py deploy/`: empty.
  - Lines holding `assert` removed from `git diff b83045d -- tests/`: three, all in the one replaced test, `test_after_a_failed_push_the_last_governed_frame_goes_again` (tests/test_main.py):
    - `assert inner.count == 4 and governed == 2 and loop.wall.governed == 3`
    - `assert np.array_equal(inner.pushed[2], third) and np.array_equal(inner.pushed[3], loop.rendered)`
    - `assert inner.count == 5                                       # one push a step again`
  - I did not run I2; it is the operator's.

## Deviations
- A commit from outside this iteration landed mid-run. At 07:35:11 someone else fast-forward pulled the main checkout (reflog `pull: Fast-forward`) to 56b97dd, "Merge pull request #1 from yestoi/ledvision-vm-kit". GitHub made that merge at 07:33:37 with 1c9b723 (my I0 commit) as its first parent, so 1c9b723 reached origin by someone else's push. I did not push. The merge adds `tools/ledvision/**`, `docs/.../evidence/hardware/*` and `tests/test_ledvision_vm.py` (16 tests), which is why 1231 were collected rather than 1215 (1146 + 69). T-wall was merged on top of 56b97dd, and the full suite, including those 16 tests, is green. The AST test globs `tools/*.py` without recursion, so `tools/ledvision/` is outside its scan; no file there holds `GovernedDisplay(`.
- My commit trailers: I0 (1c9b723) and the merge (da20a3a) end in `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, the session's attribution for this model. The plan's Global Constraints name the Fable 5.1 trailer; T-wall's commit carries that one.
- In the worktree the full suite took 274.55 s, over the 250 s limit: 1213 passed, 2 skipped (the expected pose skip), with other agents possibly loading the machine. In main after the merge it took 242.13 s, within the limit.
- Where the plan was silent, T-wall took the smallest reading:
  1. Only a send that raised starts a hold (detected by `failed` rising in the push). A frame `apply` refuses does not.
  2. The next send is allowed at `now >= since + HOLD_S`, where `since` is the failure or the last counted send.
  3. A counted send that fails restarts the hold with `SETTLE_SENDS` counted from 0, and the exception goes on to the caller.
  4. Frames pushed during the hold are dropped without a shape check.
  5. The governor's constructor arguments are kept in `self._made` for the re-init. The only governor field read is the public `held_ticks`, besides `shape`, which was already read in `close`.
  6. `close()` in a hold does today's close: the counted frame, then two governed black frames. There is no re-init and no wait, so C53 stays open as planned.
  7. In `main.py` a counted send that arrives takes the success path: failures reset, the "works again" log, lights relit.
  8. The prose tests import `FailingPushes`, `no_devices` and `playing_loop` from `tests.test_main`, as `tests/test_wall_close.py` does.
  9. Blank lines were added in the exact block.
- No exact test failed on correct code; the scratchpad folder `it14-failing/` is empty. The implementer's scratch copy from the red and mutation runs is at `scratchpad/it14-twall-red/`, outside the repository.
- The merged branch `worktree-agent-aedd1bec507ec1a6f` and its worktree at `/Users/trey/dev/codeisart/.claude/worktrees/agent-aedd1bec507ec1a6f` are left in place, because the guard blocks deleting branches.
- Left untouched: `docs/superpowers/workflow/state.md` (modified, the operator's), `reports/` and `research_notes/`.

## Test status (command + counts)
`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs` from `/Users/trey/dev/codeisart`:
- After I0 (1c9b723): 1145 passed, 1 skipped, 1146 collected, 237.90 s.
- After T-wall's merge (da20a3a, with 56b97dd underneath): 1230 passed, 1 skipped (`tests/test_sandbox.py:153`), 1231 collected, 242.13 s.
- Named files after the merge: 155 passed in 32.26 s.
- `tests/test_wall_hold.py --durations=0`: 69 passed in 8.00 s.
- T-wall's worktree suite: 1213 passed, 2 skipped, 274.55 s.

## Commits (sha + subject)
- 1c9b723 fix(arcade): gamma is 1.0 to 2.2, as the show's (C50; it14 I0)
- 2038301 fix(show): the wall holds after a failed push and starts from dark (C51, C52; it14 T-wall)
- da20a3a Merge T-wall: the wall holds after a failed push and starts from dark (C51, C52; it14)
- (not this iteration's: 56b97dd Merge pull request #1 from yestoi/ledvision-vm-kit, pulled into main by someone else at 07:35)

## Minutes (serial lane, the task, integration)
- Serial lane, I0 (reading the plan, test first, full suite, commit): 07:24:56 to 07:29:27, about 4.5 min.
- The task, T-wall: 07:29:27 to 07:41:24, about 12 min (the agent ran 689 s).
- Integration (checks, merge, named files, full suite, I1): 07:41:24 to 07:47:30, about 6 min.
- Total: about 22.5 min.
