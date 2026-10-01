The Pi 5's checks of iteration 16, run by the operator inline at 27a10bd (before the code review's verdict), 2026-10-01 02:05 to 02:07 CDT.
Each call: `git archive 27a10bd` piped into one ssh call under `flock -w 300 /tmp/pi5.lock` (Q83, pi-lock.md); the lock was free both times; the tree was untarred into `/tmp/it16-operator`, used and removed in the same call. gcc (Debian 14.2.0-19) 14.2.0, aarch64. The scripts: the session scratchpad's `pi/pi_a.sh`, `pi_b.sh`, `pi_c.sh`. If a review fix changes an entry, the pipeline or the curated test, the checks are run again and this file says so.

## (a) The show's tests on Linux
`pytest -q -rs -s tests/test_curated_entries.py tests/test_entries.py tests/test_sandbox.py tests/test_pipeline.py` with the Pi's venv: **106 passed, 0 skipped, 33.16 s** (the three tests that skip on the Mac for `unshare` and `/proc` run here).

| Entry | Real s | Peak lit | Final lit | On the Mac (orchestrator, 511fab8) |
|---|---|---|---|---|
| sloane | 3.03 | 1795 | 1795 | 3.62, 1795, 1795 |
| imc | 2.86 | 1716 | 1716 | 3.39, 1716, 1716 |
| thadgavin | 3.04 | 1677 | 1656 | 3.10, 1677, 1634 |
| endoh1 | 2.79 | 1424 | 940 | 3.40, 1424, 1206 |
| endoh3 | 2.81 | 808 | 808 | 3.37, 807, 807 |
| hello | 0.96 | 138 | 138 | 1.16, 138, 138 |

The plasma (thadgavin) passes the curated test's REP refusal on the Pi: under `TERM=vt100` ncurses 6.5 sends no `CSI n b`, and the peak (1677 of 1840 cells) is the full picture of the early probe (pi-probe-early.md).

## (b) Each entry's build line under gcc 14
Every build exits 0, with `-Wall` and `-fsigned-char`, no error.

| Entry | Warnings | What |
|---|---|---|
| sloane | 6 | 2 return-type, 1 data definition has no type, 1 sequence-point, 2 parentheses |
| imc | 12 | 3 builtin-declaration-mismatch (exit, free, malloc), 1 infinite-recursion, 1 return-type, 7 unused-value |
| thadgavin | 7 | 6 sequence-point on `n`, 1 misleading-indentation |
| endoh1 | 0 | |
| endoh3 | 0 | |

The warnings scroll past on the wall in BUILD: they are part of the show (the spec's `-Wall`, never `-w`).

## (c) endoh3's clock loop in real time
`sh clock.sh` for 15 s under `unshare -rn` with the address space capped at 256 MB (`ulimit -v 262144`): the loop was still ticking at 15 s (timeout's status 124); 3 generations (the first, then two compiled from the program's own output at 5 s and 10 s); each prints 23 lines, widest 79, no non-ASCII or control byte. The loop's compile (`cc -std=c11 -Wall -Wextra -pedantic -fsigned-char -O3`) works inside the sandbox's limits on the Pi: the cut rule does not fire.
