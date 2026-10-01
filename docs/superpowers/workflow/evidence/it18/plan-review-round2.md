# it18 plan review, round 2 (confirm only)

Read: `git diff 0c45b44 d5906bd -- docs/superpowers/plans/`, plus the whole plan at d5906bd (216 lines) to look for
stale references. I ran no new probes; round 1's probes cover the edits.

## Verdict: APPROVED

## Blocking findings

None. Finding 1 is closed:
- **O2:** O2 now runs `revert --no-commit 16dbb91`, then `git commit` with a written subject
  (`feat(arcade): Dodge returns (it18 O2; reverts 16dbb91)`), one line on why, and the two Global Constraints trailers
  as the last paragraph.
- **The fallback:** it is done the same way, and its message gives the two suite times.
- **The checks after the commit:** they still hold. The commit's tree change is the same as the `--no-edit` revert's,
  so `show --stat HEAD` still gives 4 files and 991 insertions, and the diff against 83fe13a is still empty.
- **No stale wording:** "git's own message" and `--no-edit` no longer appear anywhere except in the line that cites
  the finding.

## Notes

None of the five edits breaks anything the plan relied on.

- **`WORKER_TIMEOUT_S = 120.0`:** the 180 plays took 32.7 s at load 3.3 (round 1), so the margin is about 3.6x, and
  after O2 the fill makes 165 plays, not 180.
  - **The new risk:** under extreme load a pool past 120 s would now be killed. Its plays would fall back to the
    parent, and `test_the_pool_made_every_missing_play` would fail as a timing failure.
  - **The cover:** the plan's Risks line and Q83 (measure once more) already handle that case.
  - **The Pi:** by my estimate it would be nearer 80 s, but the Pi does not run the oracle.
- **The `n < 2` warning:** on the Mac (8 cores) and the Pi 5 (4 cores) it never fires.
  - **The two failure tests:** with `workers=2`, one seed (3 jobs) and 8 cores, n = 2. Both workers start and fail,
    so each test still warns through its own path, as round 1's probe showed.
  - **The defaults:** with `workers=4` and 120 or 165 jobs, n = 4.
  - **The cases it skips, correctly:** an explicit `workers=1` and `len(todo) < 2` do not warn, because the core count
    is not what made n < 2.
  - **One side effect:** on a 1-core host, the two failure tests would now pass on the core-count warning without
    exercising the failure path. They do not test anything on that host only.
  - **What it fixed:** on such a host, `test_the_pool_made_every_missing_play` still fails, but it now prints the
    warning's text, which was the aim.
- **`Path(arcade.__file__).resolve().parents[1] == ROOT`:** `<root>/arcade/__init__.py` has the checkout as
  `parents[1]`. `arcade` is a regular package, so `__file__` is never None. Both sides are resolved paths, and round
  1's probe showed the worker's path is the physical `getcwd()` path. In the main checkout, this rejects a worktree's
  `arcade`, as intended.
- **`revert --no-commit`:** it takes in anything already staged in the main checkout's index. If the orchestrator has
  something staged, it lands in O2's commit, and the "exactly the four files" check catches that. Nothing to change.
- **The wording:** "step 5's dict (its two keys)" and "every existing test, five functions at BASE" are now right.
  One line (101) runs past the plan's width, which is cosmetic only. The plan is 216 lines, under rule 1's 300.
