# it10 plan report (D1, the terminal on the wall)

Plan: /Users/trey/dev/codeisart/docs/superpowers/plans/2026-09-28-it10-show-terminal-on-the-wall.md
It has 299 lines, and no line is over 120 characters. It is not committed.

## Tasks (id, model, files)
- T3, opus: show/renderer.py, tests/test_renderer.py (draft: core lines 546-760)
- T4, opus: show/terminal.py, tests/test_terminal.py (draft: 763-981)
- T6, sonnet: show/entries.py, tests/show_helpers.py, tests/test_entries.py (draft: 1157-1385; entries/hello is left to D2)
- T9, opus: show/sandbox.py, tests/test_sandbox.py (draft: 1648-1743)
- T7, sonnet: show/queue.py, tests/test_queue.py (draft: 1388-1484)
- T8, sonnet: show/recording.py, tests/test_recording.py (draft: 1487-1645)
- T-shot, sonnet: tools/show_shot.py, tests/test_show_shot.py
- I1, orchestrator: merges only. No shared file is edited: pyproject.toml, conftest.py, .gitignore, show.toml and config.py are all untouched.
- I2, operator: six show_shot commands plus the suite, with outputs to a scratch folder and the tree clean.

## Launch groups and merge order
- Group 1 (4 worktrees, one message): T3, T4, T6, T9. Merge in the order T3, T4, T6, T9, with the suite after each.
- Group 2 (worktrees from the merged HEAD): T7, T8, T-shot. Merge in the order T7, T8, T-shot. T-shot runs after T3 and T4 are merged, so it builds against the real code.

## Decisions taken
- Geometry: `cfg.rows` (24) counts the strip. A normal entry gets Terminal(80, rows-1) = 80x23 and a full_screen entry gets 80x24. The renderer takes the wall's rows. Config and show.toml do not change.
- full_screen entries use `Terminal.reset(24)`. The renderer overlays the strip only when `strip_visible` is true.
- The renderer cuts the strip at 80 columns (fitting it is D3's job). It also holds the dirty-only render cache from spec 4.2 and returns the cached frame read-only.
- The pump reads in 1024-byte chunks so that budget_ms actually binds. pyte took about 3 ms to feed 4096 bytes on the Mac; that number is from a scratch run.
- The plaque carries the year (spec 3.5 revision 2 wins over the core plan).
- `rescan` never raises.
- The network test runs against the host's own loopback, so it needs no internet.
- The show's test helper lives in tests/show_helpers.py and is imported as `tests.show_helpers`, because tests/ is a package.
- The LED sheets use gamma 2.2 until the hardware notes give the card's gamma.
- Suite limit is 192 s (173 now). Shares: T3 2 s, T4 6 s, T6 1 s, T7 0.5 s, T8 0.5 s, T9 3 s, T-shot 4 s.
- If an implementer cannot meet a bound, it never loosens it. It commits what passes, saves the failing test in its scratchpad and reports the readings.

## Owner questions (defaulted)
- Q51, Reduced tier rows: `rows = 16` (80x15 plus the strip), as in the spec 3.1 table.
- Q52, strip text before D3 and the year: the renderer draws whatever text it is given. The sheets use spec 4.4's strings with the year added, to match the plaque. D3's `strip()` will build the real text.
- Q53, which wall the LED sheets show: the full 512x192 wall. The 128x64 prototype can show only a window of 21 columns by 8 rows (`--crop 0,0,128,64` in the sheets, and D4's pattern on the panels). No scaled-down mode is built.

## Safety slice
No.

## Tests at HEAD 40e8226
762 collected. The expected count after the slice is about 837. The expected new skips are +1 on the Mac: the unshare loopback test, with its reason given.

## Mismatches found
1. The core plan's Global Constraints and Task 3 describe an 80x24 terminal with an optional status row. Spec revision 2 and the amendment make it 80x23 plus a permanent strip. The draft test `test_child_sees_window_size` expects "24 80" when it should now expect "23 80".
2. Plaque text: the core plan (Global Constraints and Task 6) has "Created by <author>, Not A.I." while spec 3.5 has "Created by <author>, <year>, Not A.I.". Spec 4.4's strip wording has no year (Q52).
3. Core Task 6 creates entries/hello and tests/helpers.py and imports with `from helpers import`. tests/ is a package, so that import fails. The roadmap also puts entries/hello in D2.
4. Amendment Task 19 gives hello `station = 6`, but Global Constraints say stations are 1 to 5. The loader accepts 6 and up.
5. The draft's `draw_text` and strip use `min(ord(c), 255)`, so non-Latin-1 characters become chr(255) instead of "?".
6. The draft CastWriter decodes each chunk on its own, so a UTF-8 character split across two pty reads becomes two U+FFFD.
7. The draft `Terminal.kill` kills only while the shell is running, so orphans after `sh` exits survive. The draft pump reads 64 KiB with no time bound, and its default max_bytes is 262144 against the amendment's 4096.
8. pyte's `Screen.reset()` keeps 132 columns after ESC[?3h (checked on this install), so `reset` needs `resize`, as the amendment says.
9. Spec 4.2 gives the renderer dirty-only rendering and entries "rescan while running". The core plan has neither.
10. The draft sandbox test runs "python3" instead of sys.executable, and RLIMIT_AS works only on Linux.
11. The core File Structure still lists show/display/matrix.py, which the amendments removed. The core Task 12 `status_line()` becomes `strip()` in D3.

## Risks for the orchestrator
- The pump timing tests use wall-clock time with a 20 ms median. They can be flaky when four worktrees run suites at once. The bound must not be loosened; rerun the test alone before calling it a failure.
- The child-process tests (pty, killpg, orphan grace) behave differently on macOS and Linux (EOF against EIO, reaping). They were written for the Mac and have not been run on Linux until GATE C.
- `unshare -rn` is blocked by AppArmor on Ubuntu 23.10 and later (unprivileged user namespaces). Raspberry Pi OS and Arch allow it. On a blocked host the probe falls back and logs a warning, and the loopback test skips.
- On the Pi, pyte's feed is the bottleneck (a guess of about 25 ms per 4 KiB). The 1024-byte chunk keeps the pump inside 8 ms, but throughput on a flooding entry will be low. That is fine for the wall, but check it at D4.
- T-shot imports tools.arcade_shot, which imports the arcade runner and headless modules. The import is slow, but it is reuse, not copying.
- The render cache returns a read-only array. Any backend that writes into the frame in place would raise. The current backends were not checked for this beyond FakeDisplay, which copies.

## Minutes
About 8 minutes by the shell clock: from 1790655233 to 23:21 CDT.
