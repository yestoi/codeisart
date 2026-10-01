## Completed
- BASE checked: the main checkout was at 311e796 and clean. I read the plan (216 lines) and both plan reviews.
- O1: nothing to build. The orient files (`orient-durations.txt`, `orient-durations-dodge.txt`) are the "before" measurement.
- T-pool (opus, worktree branch `worktree-agent-ac8fa39ef100296a1`, commit 32df14c):
  - The new `tests/arcade/pooled.py` has the plan's interface. It runs 4 plain `python -m tests.arcade.pooled` workers with `cwd=ROOT`, has a 120 s deadline, kills and waits for the workers in a `finally`, and checks that the workers imported this checkout's `arcade`.
  - `tests/arcade/test_oracle.py` gains `REPORT_PLAYS`, `pooled_plays`, a `shared_plays` that yields `real`, and the six new items, placed after `test_evidence_package_for_pong`.
  - Every existing test and assert is unchanged word for word. I checked this in the diff: only fixture signatures, the docstring and `game_report`'s source for layout and seeds changed.
- Merge: 23c57d0 (`--no-ff`). The full suite with `--durations=20` gave 1812 passed, 3 skipped, 270.35 s, under the 380 s gate on the first run. Written to `durations-after-pool.txt`.
- O2 (Dodge returns), in the main checkout: I reverted 16dbb91 with no commit, then committed 708a42e.
  - The commit has the plan's subject, a line giving the reason with the measured 270.35 s, and the two trailers as its last paragraph.
  - The plan's checks hold: `show --stat HEAD` lists exactly the four files, with 991 insertions and none removed. The diff of the four files against 83fe13a is empty (0 bytes).
- After O2: the full suite with `--durations=20` gave 1866 passed, 3 skipped, 301.58 s, under 420 s. Written to `durations-after-dodge.txt`.
  - `test_oracle.py` collects 14 items, including `test_pooled_plays_are_the_in_process_plays[dodge]`.
  - The setup of `test_feel_pong_meets_its_budgets` takes 33.91 s: the fill of 165 plays plus Pong's canonical run.
  - `[quickdraw]` and `[dodge]` are no longer in the top 20 (each is under 3.22 s; they were 24.95 s and 25.07 s).

## Deviations
- I left the evidence files `durations-after-pool.txt` and `durations-after-dodge.txt` uncommitted, like this report. The operator commits evidence, as in it17.
- The implementer reported these deviations from the plan's wording. None of them changes an interface, an assert or a count:
  - `pooled.py` has two private helpers: `_read` (step 5's checks; any error while unpickling counts as step 6's "missing or short file") and `_tail` (the last 20 lines of stderr).
  - The deadline is set just before the first `Popen` call. The plan says "from the first start".
  - `test_oracle.py` has a module helper, `report_keys()`, used by `pooled_plays` and the pool test.
  - The comparison test compares each field of `bots.Play` on its own, but reports every field that differs in one assert that names the game, layout and seed. The plan reads as one assert per field.
  - The comparison test is parametrized over `REPORT_PLAYS` rows, with the game names as ids.
  - `pytest.warns(RuntimeWarning)` has no `match`, as the plan writes it.
  - 32df14c's commit message quotes the implementer's first full run, which had one flake. That flake was `tests/test_show_shot.py::test_strobe_session_is_held`, which the it15 note lists as failing under load. It passed on a rerun of its module, and on the implementer's second full run of the committed head: 1811 passed and 4 skipped in the worktree.
- No other deviation. No merge was reverted, no task was sent back, and no suite was rerun, because both runs were under their limits on the first try.

## Test status (command + counts)
- Command, from /Users/trey/dev/codeisart: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs --durations=20`

| Run | Head | Collected | Passed | Skipped | Time | Load averages (before to after) |
| --- | --- | --- | --- | --- | --- | --- |
| After T-pool | 23c57d0 | 1815 | 1812 | 3 | 270.35 s | 2.08 to 1.43 |
| After O2 | 708a42e | 1869 | 1866 | 3 | 301.58 s | 1.95 to 1.59 |

- Plan expectations: after T-pool, 1815 / 1812 / 3 / about 270 s; after O2, 1869 / 1866 / 3 / about 300 s. Both runs match.
- Skips are the same three in both runs: two `/proc` descriptor tests and the `unshare` test, all because this is macOS.
- Implementer, in the worktree at 32df14c: 1815 collected, 1811 passed, 4 skipped (the pose test, since there is no model in git), 270.25 s. `test_oracle.py` alone took 33.33 s.

## Commits (sha + subject)
- 32df14c test(arcade): the oracle's plain plays made by worker processes before its reports (it18 T-pool)
- 23c57d0 Merge T-pool: the oracle's plays in worker processes (it18)
- 708a42e feat(arcade): Dodge returns (it18 O2; reverts 16dbb91)

## Minutes (serial lane, parallel tasks, integration)
- Serial lane: 0 (O1 builds nothing; reading the plan and its reviews took under 1 minute).
- Parallel tasks: 17.4 (T-pool, from 04:48 to 05:05).
- Integration: 10.7 (the merge, the suite after T-pool, O2's revert, commit and checks, and the suite after O2, from 05:05 to 05:16).
- Total: 28.3.
