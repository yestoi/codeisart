## Completed
- I0 (orchestrator, main checkout): `tests/test_config.py:20` now asserts `bright-on-field`, and `test_the_default_strip_look_is_the_loop_s_reading_everywhere` was added. Test first: both failed (2 failed, 7 passed), then passed after `show/config.py:28` and `show.toml:7` were changed. `show.poc.toml` and `show/renderer.py` are unchanged. Commit 258d8d1 is BASE for group 1.
- GROUP 1 (one message, worktrees, from 258d8d1):
  - T-wall (opus), 8cc8d22: `GovernedDisplay.unsent`, `.failed`, `.last` (a read-only view), and `close`, which resends the counted frame when the last send did not complete, then sends two governed black frames. Also `tools/flash_meter.py` `FlashMeter`. The 4 EXACT tests in `tests/test_wall_close.py` are as given. `show/wall.py` still has one `.push(` and two `._send(`.
  - T-main (opus), 6729d76: `Sigterm`, `sigterm_raises()`, `FALLBACK_FPS`, `DISPLAY_KEYS`, `config_from` fallback (`_fallback`), the `closing` log, lights `all_off` + `tick` in `_close`, the fps fallback and the `runs at` log.
    - The review note is in: brightness and brightness_cap are range-checked (a real number from 0 to 1, not bool or nan) before the min with the default.
    - `tests/test_main_stop.py` has 9 tests. The stop test's child keeps the real AudioCues and is killed in a `finally`.
  - T-deploy (sonnet), 1ec7c25, plus the follow-up f4ec916: `deploy/README.md` (the watchdog every second, SIGTERM, black, the broken show.toml, network-online Q63, the soaks, NRestarts, vcgencmd, the pattern tool) and 2 tests in `tests/test_deploy.py`.
- Merged T-wall (d8ad84d). The full suite was green, 220.22 s. Then merged T-deploy (2d68d5e) and T-main (3ee1431), each checked with its named test files plus `tests/test_wall.py tests/test_main.py tests/test_config.py`.
- GROUP 2 (one message, worktrees, all three from 3ee1431, which has T-wall and T-main merged):
  - T-pattern (opus), 2f20c5a: `tools/wall_pattern.py` goes only through `GovernedDisplay(display, ...)`. Adds `governor_fps`, `MAX_FPS`, `grid`, `panels`, no `white`, the fps and gamma refusals, `--config`, and refusals before `make_display`. The 3 EXACT tests in `tests/test_wall_pattern_governed.py` are as given (checked against the plan text).
  - T-shot (sonnet), b9a4997: `pages`, `PAGE_MAX_H`, `COLS_MAX_WIDTH`, `--cols` honoured or refused with exit 2, `-p<k>` page names, the FlashMeter on `display.last` after the governor, the area/sq labels, and the `held/area/squares` line for `--session`.
  - T-soak (sonnet), 2f7e496: `tools/show_soak.py` `soak`, `failures`, `main`. A real ShowLoop with fakes, run inside `sigterm_raises()`. It never names `make_display` and has no `.push(`. 11 tests.
- Merged T-pattern (6dfde3c), T-shot (5bd6c7e), T-soak (de46e3f) and the T-deploy follow-up (418ef74). Each merge's named test files plus the three shared files were green, and the final full suite was green.
- I1 checks (all at HEAD 418ef74):
  - `git diff 245cb57 --` on `arcade/flash.py`, `arcade/brightness.py`, `show/display/colorlight.py`, `tests/test_wall.py`, `tests/test_main.py` and `tests/test_wall_pattern.py` is empty. `show.poc.toml`, `deploy/show.service` and `show/renderer.py` are also unchanged.
  - `tests/test_config.py` differs from 245cb57 only at line 20 and the new test.
  - No added line is over 120 characters. The only lines over 120 in changed files are six in `tools/show_shot.py` (lengths 171, 170, 121, 121, 122, 122), all present at 245cb57, just moved down.
  - Every commit 258d8d1..418ef74, merges included, carries `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` (read with `git log`).
  - `pgrep -fl python`: nothing left after the final suite.
  - I2 was not run (the operator's).

## Deviations
- **I0 suite over the limit:** the full suite after I0 took 283.43 s, over 245 s (1064 passed, 1 skipped). The later runs on the same machine took 220.22 s (after T-wall) and 225.05 s (final), so the 283 s looks like machine load, not the change.
- **Group 2 timing and base:** all of group 1 had returned before T-wall's full suite finished. So I merged T-deploy and T-main (named test files only) and spawned T-pattern, T-shot and T-soak together in ONE message from 3ee1431, not T-pattern and T-shot from a T-wall-only HEAD. The full suite ran after T-wall's merge, as asked, and again after the last merge. At most three implementers ran at once.
- **T-wall missed its time bound:** the new tests take 1.46 s against the plan's 1 s. `test_governed_frames_meter_inside_the_budget` (strobe(100) at 192x512, governor about 0.43 s plus meter about 0.36 s) takes 0.91 s alone. The bound was not loosened and the test was not changed.
- **T-wall readings:**
  - A failed resend in `close` is also logged (`log.exception`, a new module logger in `show/wall.py`) as well as swallowed.
  - "Both sizes" in the meter test are 64x128 and 16x24; 192x512 alone took 1.39 s.
  - Two extra tests: a close with nothing pushed, and a KeyboardInterrupt during the close's resend.
  - The T-wall agent ran one profiling command that began with `cd` into its worktree. It was not a git command and did not touch the main checkout.
- **T-main readings and gaps:**
  - Two extra tests: the thread warning, and the count logged after the close.
  - The in-process SIGTERM test runs `loop.run()` inside `sigterm_raises()`, not through `main()`.
  - `Sigterm.seen` counts every SIGTERM, the first included. The count is logged only when it is over 0.
  - A previous handler of None is restored as SIG_DFL.
  - `test_lights_tick_on_every_step` passed at BASE: the loop already ticked every step. Only the tick in `_close` is new.
  - Gaps not handled (the plan is silent):
    - A first SIGTERM that arrives while `_close` is already running (after `--play` ends) could cut the black short.
    - A SIGTERM before `run`'s `try` gives a KeyboardInterrupt, not exit 0.
    - `load_config` does not type-check `backend`, so the `backend = 3` test adds `fps = 0` to force the fallback.
- **T-deploy:**
  - The first README line `tools/wall_pattern.py --config show.toml` had no pattern, and the pattern is a required positional (found by T-pattern). I sent T-deploy back once, and f4ec916 made it `... --config show.toml panels` plus a line on `grid`. I checked it: the command parses and writes a PNG (exit 0, output in the scratchpad).
  - The test strings are the smallest reading: `python -m tools.show_soak` and `wall_pattern.py --config show.toml`.
- **T-pattern readings:**
  - A new `--gamma` flag (default 2.2), so `main`'s "gamma 22.0: 2" can be given; `load_config` rejects 22.0.
  - A config that fails to load returns 2 with a message. A `--config` path that does not exist silently gives `Config()` (load_config's behavior); no check was added.
  - The backend check (`fake`) comes after `--png` and before the display.
  - The config's `brightness`, `fps` and `sdl_scale` are not taken; the tool keeps 0.1, 20 and 8.
  - `build_parser(defaults=False)` uses argparse.SUPPRESS to tell which flags were given.
  - If `wall.close()` raises in `run`'s finally, the error propagates, but the display is still closed by `GovernedDisplay.close`'s own finally.
  - `panels` draws labels only, no outlines.
- **T-shot readings:**
  - `test_a_long_command_writes_numbered_pages` uses `--command "seq 1 50; sleep 1" --cols 1 --seconds 0.3`, not the plan's `"seq 1 50" --seconds 0.5`. Plain seq ends at once and gives about 2 frames, so it never reaches a second page.
  - `test_the_strobe_session_labels_its_flash_numbers` uses `seconds=0.9, every_ms=100`, not 1.5, to stay under 3 s. It does not reach the strobe: the build plus about 1.1 s of black comes first. It asserts the labels, that the meter saw frames, and `squares_max <= BUDGET`. The flash property stays with `tests/test_show_shot.py:248` and `tests/test_flash_meter.py`, as the review note allows.
  - `main` builds the session meter from `cfg.fps` and `cfg.gamma`. When `meter` is None, `frames_from_session` builds it from the governor.
  - The `--cols` fit uses the smaller of the fit at `--scale` and at the distance sheet's `max(4, scale)`.
  - Titles carry "page k/n" even on a single page.
  - `sheet()` gained a `cap` argument (default as before).
- **T-soak readings:**
  - The first press is at t0.
  - `test_main_writes_the_report` uses `--minutes 0.005 --window-s 0.1`, not 0.02, and a fake EntryPlayer.
  - `rss_kb` is `ru_maxrss` (peak), reported first and last.
  - `plays_started` counts player-factory calls. `plays_ended` counts each player's first stop, snapshot at the last step.
  - `main` returns 2 for a non-positive `--minutes`, `--press-every` or `--window-s` and for an unreadable config, and writes nothing then. A SIGTERM or Ctrl-C counts in `run_ended_early`, so the exit is 1.
  - Nested report keys are the implementer's own: `governor.held_ticks`, `meter`, `windows` rows, `failures`.
- **Left in place:** all seven it13 worktree branches (worktree-agent-af9e292eb5c21db20, -a9771bb813529372d, -a042094ad8be1650b, -a82a5820ad76069e6, -a5c777fc4624875fa, -ad436948c27d37ae6), all merged, none failed. `docs/superpowers/workflow/state.md` shows as modified (the operator's) and was not touched. `reports/` and `research_notes/` were not touched.
- No EXACT test failed. `it13-failing/` is empty. No merge was reverted.

## Test status (command + counts)
- Command, from `/Users/trey/dev/codeisart`: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs --durations=0`
- Final at 418ef74: 1140 collected, 1139 passed, 1 skipped (`tests/test_sandbox.py:153`), 225.05 s, under the 245 s limit.
- Earlier full runs: I0 at 258d8d1, 1065 collected, 1064 passed, 1 skipped, 283.43 s (over the limit, see Deviations). After T-wall at d8ad84d, 1076 collected, 1075 passed, 1 skipped, 220.22 s.
- New test files, from the final run's `--durations=0`:

| File | Seconds | Budget |
|---|---|---|
| test_wall_close + test_flash_meter (T-wall) | 1.46 | 1 (missed) |
| test_main_stop (T-main) | 0.38 | 2.5 |
| test_deploy new tests (T-deploy) | under 0.005 each | 0.2 |
| test_wall_pattern_governed (T-pattern) | 0.32 | 1 |
| test_show_shot_pages (T-shot) | 2.68 | 3 |
| test_show_soak (T-soak) | 1.31 | 2 |

  About 6.2 s in all, against the 10 s allowed.
- `pgrep -fl python` after the final suite: none.

## Commits (sha + subject)
- 258d8d1 chore(show): bright-on-field is the strip's default (Q54; it13 I0)
- 8cc8d22 feat(show): the close path after a failed push, and a flash meter (it13 T-wall)
- 6729d76 feat(show): systemctl stop, the fallback's display, lights.tick, fps (it13 T-main)
- 1ec7c25 docs(deploy): what stop and the watchdog do, the soak and the pattern tool (it13 T-deploy)
- d8ad84d Merge T-wall: the close path after a failed push, and a flash meter (it13)
- 2d68d5e Merge T-deploy: what stop and the watchdog do, the soak and the pattern tool (it13)
- 3ee1431 Merge T-main: systemctl stop, the fallback's display, lights.tick, fps (it13)
- 2f20c5a feat(tools): the test pattern through the governor, grid and panels, --config (it13 T-pattern)
- b9a4997 feat(tools): show_shot pages, --cols honoured, the session metered (it13 T-shot)
- 2f7e496 feat(tools): the soak, a real ShowLoop with fakes and a flash meter (it13 T-soak)
- f4ec916 docs(deploy): the pattern tool's line names its pattern (it13 T-deploy)
- 6dfde3c Merge T-pattern: the test pattern through the governor, grid and panels, --config (it13)
- 5bd6c7e Merge T-shot: show_shot pages, --cols honoured, the session metered (it13)
- de46e3f Merge T-soak: the soak, a real ShowLoop with fakes and a flash meter (it13)
- 418ef74 Merge T-deploy follow-up: the pattern tool's line names its pattern (it13)

## Minutes (serial lane, parallel tasks, integration)
- Start 04:59:44, end 05:38 (from `date`): about 38 minutes in all.
- Serial lane (I0, 04:59:44 to 05:04:50): about 5 minutes, of which the suite took 4:43.
- Parallel tasks:
  - Group 1, 05:05 to 05:16: about 10.5 minutes wall. T-wall 8.0, T-main 10.5, T-deploy 1.7.
  - Group 2, 05:22 to 05:32: about 9.5 minutes wall. T-pattern 9.5, T-shot 6.5, T-soak 6.7.
  - The T-deploy follow-up, about 1 minute, ran during the merges.
- Integration: about 13 minutes.
  - Group 1 merges with the full suite after T-wall: 05:16 to 05:22.
  - Group 2 merges: 05:32 to 05:33:40.
  - Final suite: 05:33:42 to 05:37:28.
  - I1: to 05:38.
