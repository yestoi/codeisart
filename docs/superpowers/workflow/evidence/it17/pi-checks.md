The Pi 5's check of iteration 17, run by the operator inline at the code head 86f0607 (while the code review read the same commits), 2026-10-01 03:45:38 to 03:46:13 CDT.
One call: `git archive 86f0607` piped into one ssh call under `flock -w 300 /tmp/pi5.lock` (Q83, pi-lock.md); the lock was free; the tree was untarred into `/tmp/it17-operator`, used and removed in the same call. gcc (Debian 14.2.0-19) 14.2.0, aarch64. The script: the session scratchpad's `pi/pi_a17.sh`. If a review fix changes the strip, the pipeline or the curated test, the check is run again and this file says so.

## The show's tests on Linux
`pytest -q -rs -s tests/test_curated_entries.py tests/test_state.py tests/test_pipeline.py tests/test_sandbox.py tests/test_entries.py` with the Pi's venv: **147 passed, 0 skipped, 34.61 s** (the test that skips on the Mac for `unshare` runs here). It includes it17's new tests: the six of `tests/test_state.py` (`wrap_words`, the short strip's pieces) and the six of `tests/test_curated_entries.py` (`banners`, the star program that plays through, the four failed plays that are still caught).

| Entry | Real s | Peak lit | Final lit | it16 on the Pi (9e3b8f0) |
|---|---|---|---|---|
| sloane | 3.02 | 1795 | 1795 | 3.03, 1795, 1795 |
| imc | 2.86 | 1716 | 1716 | 2.86, 1716, 1716 |
| thadgavin | 3.03 | 1677 | 1656 | 3.04, 1677, 1656 |
| endoh1 | 2.80 | 1424 | 940 | 2.79, 1424, 940 |
| endoh3 | 2.83 | 812 | 812 | 2.81, 807 or 808 (its face depends on the second it starts in) |
| hello | 0.96 | 138 | 138 | 0.96, 138, 138 |

The entries play on the Pi as they did in it16: the banner check's change (`banners`, the pipeline's four texts) lets imc's fifth view through under gcc 14 on aarch64 and still passes every entry.

it16's checks (b) (the build lines' warnings) and (c) (endoh3's clock loop) were not run again: it17 changes no entry, no build line and nothing of the sandbox.
