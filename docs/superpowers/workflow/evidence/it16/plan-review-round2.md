# it16 plan review, round 2 (confirm)

This round checks the six findings of round 1 (`plan-review.md`) against the plan as fixed in 29765db (299 lines). The reviewer is the same agent as round 1, 2026-10-01 00:58 to 01:03 CDT. Probes are under `/private/tmp/it16-plan-review/`.

Verdict: **APPROVED**. All six findings are lifted, and the fix adds no new blocking finding.

## B1 to B6
- **B1 LIFTED.** The run line is now `./prog < endoh1.c` (:215). Under the fixed test, endoh1 passes with witness peak 1424 and final 1289. The old line fails it (final 40).
- **B2 LIFTED.** `typing_rows` covers SOURCE and BUILD; `rows` covers RUN and FALLBACK; `_start_run` resizes before the CastWriter and before `term.run`.
  - Emulated: sloane and endoh3 are 23x23 (`term.rows`, `screen.lines`) in every SOURCE and BUILD tick, and 24x24 from RUN through DONE (`probe_curated2.out`).
  - Nothing else reads the player's rows. The only readers are `show/pipeline.py:103` and `:202`.
  - The shared Terminal (`show/main.py:170`) is reset by `attract.start` to the attract's own 23 rows (`show/attract.py:46`; called at `show/state.py:206` and `:233`).
  - Every play gets a new player whose `start` resets to `typing_rows` (`show/state.py:255-256`).
  - `tools/show_shot.py:144-149` sizes its own terminal per step.
  - So DWELL stays at 24, which the renderer draws as 23 under the strip. Attract and the next entry do not inherit the 24-row screen.
- **B3 LIFTED.** I emulated the fixed `test_entry_plays_through` (witness from RUN, PEAK and FINAL 100 on it, the cut assert for curated slugs, the REP regex):
  - `exit 1`, `sh nosuch.sh` and `./prog_missing` fail it, each on the cut (0.2 fake s against 36 or 40) and on the peak (0). The first two also fail the final (27 and 34).
  - The old endoh1 fails on the final (40).
  - The five fixed entries and hello pass, with finals from 138 to 1790.
- **B4 LIFTED.** The test now asserts a strip text equal to "Test Author, 2026". Round 1's probe of a session at show.poc.toml saw exactly that text three times.
- **B5 LIFTED.** The run line is now `TERM=vt100 ./prog` (:197), and the test runs the REP regex over the RUN's bytes. A run that prints `#ESC[78b` lines fails it on `no_REP`. None of the six real entries matches the regex.
- **B6 LIFTED.** `--basetemp=T/pt` puts pytest's temp tree in the literal `/tmp/it16-operator`, which the call removes. Each check is a script file, so there is no nested quoting.
  - `git archive --add-file=<c>.sh HEAD` puts the script at the archive's root (git 2.50, listed).
  - I simulated the remote line under dash with a script that fails midway (`false; exit 3`): the script ran, and the directory was gone afterwards.
  - If flock times out, nothing is made.

## New blocking findings
None.

## Noted, not blocking
- Once the lock is taken, the call's exit status is the trailing `rm`'s (0), so each check's pass or fail comes only from its printed output. A flock timeout shows as exit 1 with no output.
- If ssh drops mid-check, `/tmp/it16-operator` stays until the next call's leading `rm -rf`.
- Check (c) puts only RLIMIT_AS (`ulimit -v`) and `unshare -rn` on clock.sh, not the run's CPU and file-size limits. That is enough for its question.
  - On SIGTERM, gcc's driver deletes its own temp files.
  - Prefixing `TMPDIR=/tmp/it16-operator` to check (c)'s `timeout` line would keep even a killed cc1's temp files inside T.
- On the Mac, the broken `./prog_missing` copy's bash error message lights 265 cells, which is over FINAL_LIT_MIN. The cut assert is what fails it, so keep that assert even if a later edit is tempted to drop it.

## Probes (round 2)
- `/private/tmp/it16-plan-review/probe_curated2.py` → `probe_curated2.out`: the fixed T-curated checks and the fixed T-rows, run on the five entries, hello, the three broken copies, the old endoh1 (`entries_r2/endoh1_old`) and a REP run (`entries_r2/rep_run`).
- `/private/tmp/it16-plan-review/c_probe.sh`, `c_fail.sh`: `git archive --add-file` placement, and the remote line under dash with a failing script (simulated under /private/tmp/it16-plan-review/pisim, removed by the line).
