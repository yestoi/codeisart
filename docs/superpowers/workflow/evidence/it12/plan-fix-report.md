## Plan (path, line count, lines over 120)
/Users/trey/dev/codeisart/docs/superpowers/plans/2026-09-29-it12-show-runs.md: 298 lines, none over 120. I edited it
in place and did not commit it. `git status` also shows `roadmap.md` and `state.md` as modified; those edits are the
operator's, not mine. I left `reports/` and `research_notes/` alone.

## Blocking findings: what changed for each (plan lines)
- B1 (strobe inputs hide the cursor):
  - Line 189: `FILL` now starts with `\x1b[?25l`. Line 195: StrobePlayer's black feed also starts with `\x1b[?25l`.
  - Line 244: `test_strobes_over_3_hz_are_held_and_under_are_not` renders `FILL` with the cursor hidden (N7).
  - Lines 259-260: T-shot's `STROBE_C` prints `\033[?25l` first, as hello.c does.
- B2 (`gamma` bounded to `1.0 <= gamma <= 2.2`):
  - Lines 33-38: I0's check uses the review's exact message; `import math` is gone (NaN fails the comparison).
  - Lines 40-41: the show.toml comment gives the range.
  - Lines 42-44: `test_strip_look_gamma_and_fps_are_checked`: gamma 0, -1.0, 0.22 and 22.0 raise; 1.0 loads.
  - Line 133: `GovernedDisplay` raises the same `ValueError`, because a Config built in code skips `load_config`.
  - Line 167: the governed-frame test in prose also checks that 0.22 and 22.0 raise.
- B3 (the AST test and a behavioural test):
  - Lines 207-220: the AST test has the review's asserts:
    - no alias of `make_display`;
    - every `.push` attribute in main.py is on `self.wall`;
    - exactly one `.push` call in wall.py;
    - `tools/show_shot.py` is among the files that may not name `make_display`.
  - The show_shot assert agrees with the tool. show_shot.py does not import or call `make_display` today; I checked
    with grep. T-shot's sessions use `ShowLoop(cfg, display=FakeDisplay())`, so the frames go through the loop's
    `GovernedDisplay`. Line 255 tells T-shot never to name `make_display`.
  - N4 and N20 would have added `.push` calls to wall.py. Line 131 routes them through one private `_send`: `repush`
    sends the last governed frame again, and `close` sends two blacks through apply and then `_send`. That keeps
    wall.py at one `.push` call.
  - Lines 166-169: `test_the_loop_s_own_display_is_governed`, in prose as the review gives it: `monkeypatch`
    `show.display.fake.FakeDisplay` with `Made(Recorder)`, no display, the strobing steps, then one `Made` with 100
    governed frames, `flash_area == 0.0` and at most `BUDGET` square flashes.
- B4 (a render raise aborts to attract):
  - Line 159, the step: a raise pushes the last frame again and calls `show.abort(now)`.
  - Line 247: the test is renamed `test_a_render_that_raises_repushes_the_last_frame_and_returns_to_attract`.
  - Line 288, Decisions: a push failure does not abort; the lights rule (10 s, all off, relight) is how spec 4.6
    applies to a push.
- B5 (the operator sets the strip look): lines 280-282. I2 ends with the operator setting `strip_look` in show.toml
  to the look that reads best at the led and distance looks. That is a commit of its own and names the pick as Q54's
  answer. Config's default stays `reverse`.

## Notes taken in, notes left out (and why)
- N2, a governor that can't be built:
  - Lines 153-156: if the config's governor fails, `GovernedDisplay(display, h, w)` is built with the module's
    defaults (gamma 2.2, fps 30). It carries only the static error frame naming the cause, with no show.
  - Only if that also fails is the display closed and `wall` None. `wall is None` counts as a push failure for the
    lights (line 161).
  - Lines 229-235: the test is renamed `test_a_gamma_the_governor_refuses_shows_its_error_governed`, with an exact
    body: gamma -1.0 in a Config built in code; no show; an error names gamma; the governor runs at gamma 2.2 and fps
    30; 20 identical lit frames are pushed.
  - Line 170: `test_when_no_governor_can_be_built_the_wall_stays_dark` keeps the dark case, with `FlashGovernor`
    patched to raise. It also appears in Decisions (line 286).
- N3:
  - Line 150: `config_from(args)` returns `Config()` with `--backend` if given, plus the error. The loop then has
    `config_error`: no show, and the static governed frame names the error.
  - Line 245: `test_a_bad_config_falls_back_with_its_error`.
  - Lines 37-38: I0 checks `fps` is an int of at least 1; the config test covers 20.0 and 0.
- N4: line 160, after a failed push, `self.wall.repush()` first, then the new frame. Test:
  `test_after_a_failed_push_the_last_governed_frame_goes_again`.
- N5: line 162, `run` steps at least `1 / fps` apart with no catch-up, and T-shot does the same (line 257). Test:
  `test_run_never_steps_faster_than_fps`.
- N6: line 237, the typed and scrolled text is `arcade/flash.py`, which no task edits. I probed it again in
  `it12-plan/probe_fixed_text.py`; the numbers match the review's probe.

  | Test | Probe | Bound |
  |---|---|---|
  | Attract, 3 lines/s, both views | held 0 | held 0 |
  | Typing, text view, 400 cps | 0.000 | 0.03 |
  | Typing, text view, 1600 cps | 0.065 | 0.08 |
  | Ink view, 400 cps | 0.102 | 0.15 |

  Q60 now gives the range of both texts.
- N7: with B1.
- N9: line 78, `set_entries`: unchanged stations and slugs change nothing; a change rebuilds attract and keeps the idle
  clock; queued entries are compared by station. Test: `test_an_unchanged_rescan_keeps_the_idle_clock`.
- N10: lines 56 and 157. Lights calls are guarded apart from the show and never abort it; `lights.tick` belongs to the
  loop, in its own `try`. Test: `test_a_lights_error_never_aborts_the_show`.
- N11: line 163, `run`'s `finally` guards each close, and closes lights only if they have `close`. Test:
  `test_run_s_finally_survives_a_raising_close`.
- N12: line 154, `AudioCues(cfg.audio_dir, cfg.volume, cfg.quiet_hours)`.
- N13: lines 55-56, the player protocol is `done`, `crowd`, `start(now, crowd)`, `tick(now) -> cues`, `stop()`.
- N1: line 128, a WARNING on the ddp backend names the level Falcon Player must hold. Line 122, README: Falcon Player's
  brightness equals show.toml's, never over `brightness_cap`.
- N14-N18, lines 117-122:
  - `Environment=LG_WD=/tmp` (N14).
  - README: edit `User=` and the paths, since Bookworm has no `pi` user (N15).
  - `CAP_NET_RAW` is for the colorlight backend only (N16).
  - The LEDVision settings record (N17).
  - No `KillMode` (N18).
  - I dropped "drop CAP_NET_RAW on DDP" and "USB gigabit adapter" from the README list to save lines; the core
    plan's steps still cover the adapter.
- N20: line 137, `close` sends two governed black frames. Test: `test_a_clean_close_pushes_two_governed_black_frames`.
- N23: line 3 now reads "I0's commit on the HEAD at the spawn". I1 still diffs against 0dae849 for the safety files.
- N24: line 10, T-main gets 15 s and new tests 25 s in all; the suite limit is 235 s.
- Left out, as you said: N21 and N22, which go to the roadmap. N8, N19, N25 and N26 needed no change; they confirm the
  plan as it was.

## What was cut or moved
- Nothing moved to it13. T-deploy keeps `deploy/`. The fallback in Decisions (line 290) still says `deploy/` moves
  first if the iteration runs long.
- No safety test was cut or loosened.
- To fit in 298 lines:
  - Short lines of the exact code were joined. The plan allows reformatting, and no assert changed.
  - T-deploy's unit list uses `D` for `/home/pi/codeisart`.
  - Prose was shortened: T-state's test notes, T-term, legibility, loop tests, T-shot, I2 (its expected output is
    now one line per sheet) and Decisions.
  - One test name was shortened: `test_an_empty_strip_is_lit_in_every_look`.
- No harness refusals.

## Minutes
Started at 02:30 CDT and finished at 02:37, about 7 minutes. One read-only probe:
`it12-plan/probe_fixed_text.py`.
