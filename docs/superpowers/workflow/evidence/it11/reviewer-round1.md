## Verdict: BLOCKED

## Blocking findings (file:line, the input, what happens, why it blocks)

1. `entries/hello/hello.c:27-37`. **Input:** the show's own environment, `LINES=23 COLUMNS=80`. **What happens:** each frame homes the cursor (`ESC[H`) and prints `col` spaces and then 6 `#`. It never clears the rest of the row (no `ESC[K` or trailing spaces). While the wave moves the band left, the `#` from the earlier frames stay to its right. The probe (`it11-review/p4_hello_trail.py`: hello built in the scratchpad, its output fed to pyte 80x23) counts the `#` on each row:
   - frame 30: 6 to 14
   - frame 45: 22 to 44 (row 0 is a solid block of 22 from column 58 to the edge)
   - frame 58 (the last frame): 48 to 70

   The second half of the animation is a wedge filling to the right edge, not a band. **Why it blocks:** T-hello's plan says "a band of `#` on every row, its column on a wave". I2's evidence is read against that for all four sheets: "the band moving", "the replayed band", and "the band a moving stripe" on the PoC. `test_sample_entry_runs_with_large_motion` passes anyway, because it measures motion, not the band's width. The fix is one line: `printf("\033[K")` after the band, or pad the row to `cols`. The committed hello has no fallback cast, so nothing else goes stale.

## Noted, not carried (one line each)

**Range checks**

- **Tests, per file.** `git diff ebd367c..08cc0fa -- tests/` has 1294 insertions and 0 deletions. No `assert` is removed or changed, and no test name is duplicated (so none is shadowed).
  - tests/test_terminal.py: only additions (`import signal` and new tests).
  - tests/test_renderer.py: only additions.
  - tests/test_config.py: one assert added to `test_defaults_when_file_missing` (`lightbox_pins`, as the plan says), plus new tests.
  - tests/test_show_shot.py: only additions.
- **Collected count.** 965 collected (888 at ebd367c). The only new skip markers are `skipif(no cc)`, and cc is present. I did not run the full suite, as instructed. test_attract, test_io and test_config pass (34), and test_make_cues passes (3).
- **Safety files.** `arcade/flash.py`, `arcade/brightness.py` and `show/display/colorlight.py` are unchanged in the range (`git diff --quiet`). Probes left no child behind (`pgrep`).

**The ten points**

- **P1 C48: fine.** Every path forgets the group: ESRCH, a SIGKILL after the leader is reaped, the end of `kill()`, and `run()` resetting `_pgid` without signalling. Three residuals remain, none a practical risk:
  - The first signal after a reap can still name a pgid whose group is already empty. That is the Linux drain path, 0.5 to 2 s after `poll()` reaped the leader. A hit needs a pid wrap within that window and the new process to lead a group.
  - EPERM after a reap keeps the pgid, but the group still exists then, so its ID cannot be reused.
  - If `kill()` raises in its pump (see P4), `_pgid` stays set. No code in the range calls `kill()` again on that terminal.
- **P2 drain: fine.**
  - On the finished path nothing is lost: EOF comes after the last byte.
  - On the orphan path, `kill()` sends SIGKILL, then one 4 KB/8 ms pump, then closes. The only loss is more than 4 KB written within the last tick (orphans), or a writer past `drain_max`, which the plan accepts.
  - The drain never blocks: each call returns at once. On that path `kill()` does not wait, because the leader is already reaped. The drain is also cut by `build_seconds` and `run_timeout()`.
  - By reading the code (Linux only; on macOS the leader's exit gives EOF at once, confirmed by `p5b.py`): a crash within `drain_max` of `run_timeout()`, while the pty still delivers data, takes the timeout branch at `show/pipeline.py:186-189`. The crash then reads as a normal end, and the capture is kept.
- **P3 `start()` may raise: noted.** The plan marks only `tick()` "never raises" and gives `start()` no such clause. Spec 4.6 puts the catch in D3's loop. If `start()` raises on `read_bytes`, the phase stays DONE. D3 must guard it.
- **P4 `stop()` can raise: noted, reachable.** Input (`it11-review/p2_stop_raises.py`): `ESCAPE_C` (`printf("\033[?3A"); sleep(30)`) reaches RUN, sleeps 0.3 s with no tick, then `stop()`. The result: `TypeError` out of `stop()`, phase DONE, the child SIGKILLed (rc -9), `master_fd` left open and `_pgid` kept. The fd is closed at the next `run()` on that terminal, so this is not a leak per entry while D3 reuses one Terminal.
  - D3 must guard `stop()`.
  - Suggested fix: `kill()` closes the master and forgets the group in a `finally`. That also closes the same hole in `_on_exception`, where `kill()` raising is caught but likewise leaves the fd open.
- **P5: fine.** No child exists in ERROR_HOLD, FALLBACK or DWELL: every exit from BUILD or RUN goes through `finished_or_orphaned()`, `_kill()` or the exception path's `_kill()`. The capture is always closed or dropped on leaving RUN, including a failure in `_start_run` while still in BUILD.
- **P6: fine.** The limit covers the longest timeout crowd mode can switch to, plus 5 CPU seconds. One caveat: RLIMIT_CPU sums a process's threads. A 4-thread spinner hits SIGXCPU at about 11 s wall and reads as "crashed (signal 24)", then plays the fallback. That is rare for IOCCC entries.
- **P7: fine.** `wrap()` is applied to every run line (`show/pipeline.py:172`). `run_command` only decides the `exec` prefix, so no allowed line runs outside `unshare` or the rlimits. The lines left alone lose only the crash-as-signal reading, which the plan accepts for shell syntax.
- **P8: fine.** The test's bound is the plan's: under 5 % of samples within 1 % of the peak, and a peak of at most half scale. Measured: 0.05 % and 0.330. Two fresh runs and the committed WAVs share the same sha1 for all four cues. Across machines, a 1-ulp libm difference could in theory flip one int16 rounding, but the odds are negligible.
- **P9: fine.** With the default `view = "text"`, `render` skips the ink branch. `x0`/`y0 = max(0, …)` do nothing because the fit check still runs, and `_ink`/`dot` are only computed in `__init__`. `it11-review/p3_text_view_same.py` compares the ebd367c renderer with HEAD on 320 frames (random screens, glow on and off, full_screen, cursor, strip on and off): byte-identical.
- **P10: fine.** It is a comment only, and tomllib ignores it. `lightbox_pins [17,22,23,24,27]` share no pin with the buttons or rings and avoid I2C (2,3), SPI (7-11) and UART (14,15). `test_repo_show_toml_matches_defaults` covers the pair.

**Other**

- `show/attract.py:55-58`: if a source line holds a raw escape that pyte rejects, `_i` is not advanced. Attract then re-feeds that line on every tick, logging an exception each time, and the screen stays up but stuck. Only a source with raw ESC bytes triggers it, which is curation's concern.
