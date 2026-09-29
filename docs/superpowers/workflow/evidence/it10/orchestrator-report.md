## Completed
All seven tasks were merged into main in the order the plan gives, and the suite was green after every merge. main is now 0065293. Base was 2eb5f3e.
- GROUP 1 (worktrees from 2eb5f3e), merged in the order T3, T4, T6, T9:
  - T3 renderer (opus): `show/renderer.py`, `tests/test_renderer.py`. 25 tests.
  - T4 terminal (opus): `show/terminal.py`, `tests/test_terminal.py`. 24 tests.
  - T6 entries (sonnet): `show/entries.py`, `tests/show_helpers.py`, `tests/test_entries.py`. 37 tests.
  - T9 sandbox (opus): `show/sandbox.py`, `tests/test_sandbox.py`. 10 passed, 1 skipped.
- GROUP 2 (worktrees from 3d5c553, the merged HEAD), merged in the order T7, T8, T-shot:
  - T7 queue (sonnet): `show/queue.py`, `tests/test_queue.py`. 5 tests.
  - T8 recording (sonnet): `show/recording.py`, `tests/test_recording.py`. 16 tests.
  - T-shot (sonnet): `tools/show_shot.py`, `tests/test_show_shot.py`. 8 tests.
- No task failed or was reverted. No task was sent back.
- No shared file was edited (`pyproject.toml`, `tests/conftest.py`, `.gitignore`, `show.toml`, `show/config.py`), and no task asked for one.
- No arcade engine file was touched.
- `git log main..<branch>` is empty for all seven branches. All seven branches are left in place.
- I1 readings (from the main checkout, after the last merge):
  - Collected: 888, which is 762 + 126. The plan estimated about +75; implementers added extra tests and parametrized cases.
  - Skips: 1, the expected one: `SKIPPED [1] tests/test_sandbox.py:153: needs a working unshare -rn (Linux with unprivileged user namespaces); macOS has no unshare`.
  - Suite time: 170.06 s, under the 192 s cap. The runs after each merge took 172.48, 177.55, 169.50, 168.61, 168.34, 168.90 and 170.06 s.
  - Seconds each module adds (its own run in the main checkout; the share is in brackets):
    - T3: 0.16 s [2 s]
    - T4: 1.71 s [6 s]
    - T6: 0.10 s [1 s]
    - T9: 1.16 s [3 s]
    - T7: 0.07 s [0.5 s]
    - T8: 0.02 s [0.5 s]
    - T-shot: 1.59 s [4 s]
    - Total: about 4.8 s.
  - `test_render_is_fast`, run alone after the last merge: median 1.06 ms, max 1.19 ms, min 1.06 ms over 50 renders (bound 5 ms). In T3's worktree: median 1.08 ms, and 1.44 ms (max 4.09 ms) under load.
  - `test_default_pump_is_bounded_by_bytes_and_time`, run alone after the last merge (bounds: at most 4096 bytes per pump, median under 20 ms):
    - Bytes per pump: [2048, 3072, 4096, 4096, 4096, 4096, 4096, 4096, 4096, 4096].
    - Times per pump in ms: [9.94, 8.41, 9.34, 8.29, 7.41, 6.47, 6.08, 5.75, 5.26, 5.03].
    - Median 6.94 ms. T4's earlier runs gave medians of 5.20 and 5.50 ms.
  - `test_pump_honours_a_small_budget`, run alone after the last merge: 1024 bytes in 3.90 ms (bound 20 ms). T4's runs gave 3.17, 2.22 and 2.73 ms.
- No `sleep 30` or `yes xxxxxxxx` child was left after the runs (`pgrep` found none).

## Deviations
- Orchestration: my first spawn of group 1 passed a `name` to each agent, and the harness refused it ("Teammates cannot spawn other teammates"). I spawned the same four prompts again without `name`, in one message. No work was lost.
- T4 (terminal):
  1. `test_background_child_counts_as_finished_after_grace` does not use `sh -c "sleep 30 & exit 0"`. On macOS, bash 3.2 as /bin/sh takes the pty as its controlling tty. When the shell exits, the orphan is hung up and EOF comes at once, so `finished` is True within about 16 ms and the plan's "`finished` stays False" fails. The committed test starts the orphan from a small Python session leader that takes no tty; every assert is unchanged. The plan's exact test is saved at `/private/tmp/claude-502/-Users-trey-dev-codeisart/d1e01db2-fed8-414f-9a38-325b95bc9c3a/scratchpad/test_terminal_plan_exact_grace.py`. It should pass under dash on the Pi; that is not checked.
  2. `kill()` also ignores `PermissionError`: on macOS, `killpg` raises EPERM when the group holds only the exited, not-yet-reaped shell.
  3. `finished_or_orphaned()` kills the group whenever it returns True, also after a clean EOF.
  4. `kill()` drains the pty while it waits, for at most `KILL_WAIT` = 1.0 s. Before this, killing a flood took 609 ms; after, 3 to 6 ms.
  5. `reset()` resizes before `screen.reset()`, so tab stops follow 80 columns after `ESC[?3h`.
  6. `test_kill_takes_the_process_group` adds `trap '' HUP` to the child, so that the test fails if the group kill is removed.
  7. `run()` kills the previous run's process group before it starts a new child.
  8. Seven tests were added beyond the plan's list.
- T3 (renderer):
  1. Every frame `render` returns is read-only, not only the cached one.
  2. The cache is tied to the screen object.
  3. The cursor clamps to the screen's last column.
  4. The strip is drawn at normal brightness (70 %), not bold.
  5. In the redraw test, the strips are "A" and "AA", because conftest's font draws only `A`.
  6. Tests were added beyond the plan's list.
- T6 (entries): these validations were added:
  - `year` must be an int.
  - The string keys must be non-empty strings.
  - `run_seconds` and `build_seconds` reject a bool or a string.
  - `rescan` catches any exception, not only `EntryError`, and logs it.
- T9 (sandbox):
  - The probe also returns False when running `unshare` raises `OSError`.
  - The warning is a `logging` warning on the `show.sandbox` logger.
  - One test was added: the probe is False when unshare fails or times out.
  - The loopback test has not run anywhere yet. It needs the Omarchy box or the Pi at GATE C.
- T8 (recording):
  - `CastError` is also raised for a missing or undecodable file, and for a header without width and height.
  - `close()` writes one U+FFFD event if a partial character is still pending.
  - `write()` after `close()` is ignored.
  - The implementer reports that it did not load the superpowers:test-driven-development skill. It says it wrote the tests first by hand and watched them fail before writing the code.
- T-shot (`tools/show_shot.py`):
  1. The `cc` script is not a live pty session. It runs `cc -Wall` and the program in a temp dir and feeds the captured output to the terminal as `Step`s, to fit `SCRIPTS: dict[str, Callable[[], list[Step]]]`. Its test and the I2 sheet still show the real warning and the real output.
  2. The black check counts text cells: black means no partly lit cell and at most one fully lit cell (the cursor). With glow on, black is judged by eye; `show.toml` has glow off.
  3. The extra flags `--scale` (default 4) and `--cols` (default 2) were added.
  4. The tool loads `show.toml` from the repo root.
  5. `--look both` writes `OUT-plain.png` and `OUT-led.png`; a single look writes `OUT.png`. `OUT-distance.png` is always written.
  6. A command run keeps one extra frame at the end.
  7. The implementer ran its first pytest call with `cd`, against the rules. That call only ran tests.
  8. Its hand-made sheets are in the scratchpad as `shot-{strip,edges,fullscreen,cc,seq}.png`, each with a `-distance.png`. The implementer looked only at `shot-cc.png`.
- Worktree suite runs show one more skip than main: `tests/arcade/test_pose_mediapipe.py:223`. The git-ignored `models/pose_landmarker_lite.task` is not in worktrees. It does not skip in the main checkout.
- Findings outside the tasks, reported by T4:
  1. Under dash on the Pi, children get no controlling tty, so an entry that opens `/dev/tty` fails there, while on the Mac bash takes one. The two differ. Setting a controlling tty on purpose when a child starts would make them match; that is not in D1.
  2. On macOS, pty output left unread after the shell exits can be lost within about 1 s. At 20 fps the pump reads every 50 ms, so the risk is small.
- Not mine and left alone in the main checkout: `docs/superpowers/workflow/state.md` (modified by the operator), and the untracked `reports/` and `research_notes/` directories (an IOCCC research report, not written by any test).

## Test status (command + counts)
`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs --durations=25`, run from /Users/trey/dev/codeisart at 0065293:
- 888 collected (`--collect-only`), 887 passed, 1 skipped, 0 failed, in 170.06 s (cap 192 s).
- The skip: `tests/test_sandbox.py:153: needs a working unshare -rn (Linux with unprivileged user namespaces); macOS has no unshare`.
- After each merge:

| After | Passed | Skipped | Seconds |
|---|---|---|---|
| T3 | 787 | 0 | 172.48 |
| T4 | 811 | 0 | 177.55 |
| T6 | 848 | 0 | 169.50 |
| T9 | 858 | 1 | 168.61 |
| T7 | 863 | 1 | 168.34 |
| T8 | 879 | 1 | 168.90 |
| T-shot | 887 | 1 | 170.06 |

- The largest item in the suite is still `tests/arcade/test_oracle.py::test_feel_pong_meets_its_budgets` setup, at 61.12 s. No new module is in the slowest 25.

## Commits (sha + subject)
- 6a08b06 feat(show): renderer, the strip on the last row, full_screen, dirty-only cache (it10 T3)
- 3b860c2 feat(show): the terminal, a pty and a pyte screen with a bounded pump and group kill (it10 T4)
- 7c4920a feat(show): entry loading with validation, full_screen, year plaque, rescan (D1 T6)
- 2aa0476 feat(show): sandbox rlimits and the cached unshare -rn probe (it10 T9)
- 86dd652 Merge it10 T3: the renderer
- 7013cc8 Merge it10 T4: the terminal
- a66da08 Merge it10 T6: entries
- 3d5c553 Merge it10 T9: the sandbox
- bab6d1a feat(show): the queue, with position and iteration (it10 T7)
- 1acd8e4 feat(show): asciinema v2 cast writer and gap-compressing player (it10 T8)
- 45aab6d feat(tools): show_shot, the operator's sheets of the terminal on the wall (it10 T-shot)
- 6c05694 Merge it10 T7: the queue
- 542f8d7 Merge it10 T8: recording
- 0065293 Merge it10 T-shot: tools/show_shot.py

## Minutes (serial lane, parallel tasks, integration)
Times are from `date`: start 23:26:07, end 00:08:31, about 42 min in all.
- Serial lane: 0 min (none in this iteration).
- Parallel tasks: about 21 min.
  - Group 1: 23:26:18 to 23:40:32, 14.2 min. Per agent: T4 11.7 min, T3 8.4, T9 6.4, T6 4.7.
  - Group 2: 23:52:30 to 23:59:22, 6.9 min. Per agent: T-shot 5.7 min, T8 3.8, T7 3.6.
- Integration: about 21 min, nearly all of it full-suite runs of about 2.9 min each.
  - Group 1 merges and suites: 23:40:32 to 23:52:26, 11.9 min.
  - Group 2 merges, suites and I1 readings: 23:59:22 to 00:08:31, 9.2 min.
