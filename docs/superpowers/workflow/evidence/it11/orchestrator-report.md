## Completed
- I0 (serial lane, main checkout): `lightbox_pins` added to `show/config.py` (after `light_pins`), `show.toml` (after `light_pins`, the `light_pins` line commented `# button rings`), and one assert added to `tests/test_config.py::test_defaults_when_file_missing`. Full suite green: 900 passed, 1 skipped, 176.49 s. Committed as d7e1599, which is BASE for group 1.
- GROUP 1 (four worktrees from d7e1599, spawned in one message): T-pipe (opus), T-hello (sonnet), T-attract (sonnet) and T-io (sonnet) all finished green. Merged in the order T-pipe, T-hello, T-attract, T-io with `--no-ff`, and the full suite ran after each merge. Every run was green, so nothing was reverted.
- GROUP 2 (one worktree from the merged HEAD 67eac25): T-shot (sonnet) finished green. Merged, then the full suite ran with `--durations=25`: green, 198.51 s against the 212 s bound.
- Final checks:
  - `git log main..<branch>` is empty for all five task branches.
  - `pgrep -fl "sleep 30|yes |hello"` shows one process, pid 26445. It is an unrelated herdr `ssh ... ControlPersist=yes -T omarchy` bridge that only matches on the text "yes -T". It is not a test child, and it was there before the suites ran.
  - `git status --short --ignored entries audio` is empty, so there is no build product under `entries/`.
  - `git status --short` shows only the operator's `docs/superpowers/workflow/{decisions,roadmap,state}.md` as modified (not mine: not committed, not touched) and the owner's untracked `reports/` and `research_notes/`.
- I1:
  - BASE is d7e1599.
  - Collected after the last merge: 965 (901 + 64). The plan estimated about 976 (901 + 75).
  - Skips: 1 on the Mac, `tests/test_sandbox.py:153: needs a working unshare -rn (Linux with unprivileged user namespaces); macOS has no unshare`. There are no new skips with `cc`. In worktrees the expected extra skip, `tests/arcade/test_pose_mediapipe.py:223` (no pose model), also appeared.
  - Suite time against the 212 s bound after each step (collected / passed / skipped / seconds):

    | Step | Collected | Passed | Skipped | Seconds |
    |---|---|---|---|---|
    | I0 | 901 | 900 | 1 | 176.49 |
    | After T-pipe | 927 | 926 | 1 | 184.64 |
    | After T-hello | 930 | 929 | 1 | 186.15 |
    | After T-attract | 938 | 937 | 1 | 186.12 |
    | After T-io | 960 | 959 | 1 | 194.79 |
    | After T-shot | 965 | 964 | 1 | 198.51 |

  - Seconds each task's tests add (`--durations=0`), against the plan's budget:

    | Task | Added | Budget | Detail |
    |---|---|---|---|
    | T-pipe | about 13.4 s | 15 s | Terminal tests about 2.0 s (budget 3); `tests/test_pipeline.py` 11.4 s |
    | T-hello | about 3.9 s | 4 s | The run test 3.49 s; the build 0.41 s |
    | T-attract | 0.10 s | 1 s | |
    | T-io | about 0.4 s | 1 s | The two-tone test 0.30 s |
    | T-shot | about 10.2 s | 7 s | Over budget. The `entries/hello` play 4.41 to 4.55 s; stamped sheets 2.84 s; the broken build 1.72 s; attract 0.98 s |

  - Timing readings (printed by the tests, from the implementers' runs):

    | Test | Reading | Bound or target |
    |---|---|---|
    | Terminal drain | `END` on the screen before True; lines 1 to 8 all shown | Grace 0.3 s |
    | Terminal drain_max | True 1.001 s after the exit; the writer is gone | 1.0 to 3.0 s |
    | Min build, successful build | BUILD to RUN 0.505 s | At least 0.5 s |
    | Min build, failing build | BUILD to ERROR_HOLD 0.506 s | At least 0.5 s |
    | Build timeout | BUILD to ERROR_HOLD 0.503 to 0.504 s | 0.5 s |
    | Run timeout slack | RUN 1.002 s and 1.010 s | Within 1.0 to 1.5 s |
    | Idle cap | RUN 0.502 to 0.503 s | Cap 0.5 s |
    | Crowd, typing | SOURCE 0.254 s | 0.25 to 0.35 s |
    | Crowd, run | RUN 0.501 to 0.503 s | Cap 0.5 s |
    | Crowd, dwell | 0.009 to 0.010 s, against a 5 s dwell | Skipped |
    | Crowd set mid-run | Set 0.304 to 0.305 s in; RUN 0.503 s | Cap 0.5 s |
    | Flood | 95 to 97 RUN ticks; median 4.94 to 5.06 ms; max 9.66 to 10.35 ms | Median under 20 ms |

  - Other readings:
    - hello: 60 frames, the band over columns 0 to 74, run 3.43 s. One warning: `hello.c:21:9: warning: unused variable 'leftover' [-Wunused-variable]` (Apple clang 17).
    - Error cue: peaks at 330.5 Hz then 221.7 Hz (falling); 0.05 % of samples within 1 % of the peak (bound 5 %); peak 0.330 of full scale (bound 0.5).
    - T-shot phase lines, `entries/hello`: source 0.00, build 0.32, run 0.54, dwell 4.20, done 4.42.
    - T-shot phase lines, broken build with `--capture-first`: source 0.00, build 0.06, error_hold 0.28, fallback 0.50, dwell 0.77, done 0.99. The failure starts `build failed`.
  - I2 was not run: it is the operator's, in verify.

## Deviations
- I0: the plan's `show.toml` edit says "after `light_pins` (comment `# button rings`)". I read that as adding the `# button rings` comment to the existing `light_pins` line and adding the new `lightbox_pins` line after it. The test that compares `show.toml` with the defaults passes.
- T-shot's tests add about 10.2 s against the plan's 7 s estimate. The suite total stays within the bound (198.51 s against 212 s), so the task was not sent back. The cost is real-time play: `entries/hello`'s own 3 s of motion, plus rendering the sheets.
- T-shot's choices:
  - `--seconds` defaults to 10 with `--attract`; the plan names no default.
  - The phase list holds the phase's string value (for example `"source"`).
  - `--build` and `--capture-first` without `--entry` are a parser error.
  - The stamped-sheets test writes a fast `fast.toml` under `tmp_path` and uses `--look both` to get three PNGs.
- T-pipe's choices beyond the plan:
  - `stop()` and the exception path kill only in BUILD or RUN, so a finished player cannot kill a later entry's child on a shared terminal.
  - An exception in ERROR_HOLD, FALLBACK or DWELL goes straight to DONE.
  - A build timeout also holds `min_build_seconds`.
  - The run's CPU limit is `min(run_seconds, max(crowd_run_seconds, idle_run_seconds)) + CPU_MARGIN`, so a crowd flag cleared mid-run cannot trip SIGXCPU.
  - `run_command` also leaves alone a line that already starts with `exec `, or holds `#`, `!`, `{}`, `~` or a backslash.
  - The test pipeline config also sets `dwell=0.0`; the tests that time a dwell set their own.
- T-pipe's findings, left to D3 or the review:
  - `start()` can still raise, for example on an unreadable source; only `tick()` is guaranteed not to.
  - `Terminal.kill()` pumps while it waits, so a malformed escape arriving then could raise out of `kill()`. The pipeline guards its exception path but not `stop()`.
  - On the Mac the backgrounding entry ends through the finished path (the pty is revoked). The Linux grace path has not been run.
- T-io:
  - A bad `quiet_hours` and a missing cue file are logged at WARNING; a failed load is logged at ERROR.
  - The first error cue had 5.1 % of samples near the peak, against the 5 % bound. The generator was changed (an exponential decay on each tone); the bound was not.
  - `audio/` is not git-ignored, so the four WAVs are committed, together with the test that compares them.
- T-hello: none.
- T-attract: none.
- No shared-file edit was needed beyond I0.
- No task failed, no merge was reverted, and no test was saved as failing.

## Test status (command + counts)
`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs`, from /Users/trey/dev/codeisart at 08cc0fa: 965 collected, 964 passed, 1 skipped (`tests/test_sandbox.py:153`, macOS has no unshare), 198.51 s (bound 212 s).

## Commits (sha + subject)
- d7e1599 feat(show): lightbox_pins (it11 I0)
- 5ef04bd fix(show): the terminal forgets a finished group and drains after the exit (C48, it10 note 2)
- 78afb5c feat(show): the entry pipeline, one entry end to end (core Task 10, D2)
- c0955ba Merge T-pipe: C48, the drain, and the entry pipeline (it11)
- ccf35ab feat(show): sample entry entries/hello with one deliberate warning (it11 T-hello)
- 906301c Merge T-hello: the sample entry entries/hello (it11)
- b1decce feat(show): attract mode scrolls entry sources when idle (it11 T-attract)
- 5a86f5d Merge T-attract: attract mode (it11)
- b8cac6d feat(show): input, lights, audio cues and the cue generator (it11 T-io)
- 67eac25 Merge T-io: input, lights, audio cues (it11)
- 6a76791 feat(tools): show_shot --entry and --attract play the real pipeline and attract mode (it11 T-shot)
- 08cc0fa Merge T-shot: the real pipeline in the operator's sheets (it11)

Branches, all left in place:
- worktree-agent-a507b5ea275eefd24 (T-pipe)
- worktree-agent-a1204ae46efa8c7c2 (T-hello)
- worktree-agent-a165a589468c717b1 (T-attract)
- worktree-agent-ab42701bcfdb65231 (T-io)
- worktree-agent-a8ddcabe738bbfb95 (T-shot)

## Minutes (serial lane, parallel tasks, integration)
Times are from `date`, CDT, 2026-09-29.

| Phase | Clock | Minutes |
|---|---|---|
| Serial lane (I0: edit, suite, commit) | 00:41:25 to 00:44:52 | 3.5 |
| Group 1, in parallel (spawn to the last return) | 00:44:52 to 00:58:13 | 13.4 |
| Integration, group 1 (4 merges, 4 suites) | 00:58:13 to 01:11:08 | 12.9 |
| Group 2, T-shot | 01:11:11 to 01:17:52 | 6.7 |
| Integration, group 2 (merge, suite, final checks) | 01:17:52 to 01:21:17 | 3.4 |
| **Total** | 00:41:25 to 01:21:17 | **about 40** |

Group 1 task times: T-pipe 12.5, T-hello 4.3, T-attract 4.1, T-io 4.7. The parallel tasks together (group 1 plus group 2) took 20.1 minutes, and integration 16.3.
