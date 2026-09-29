## Verdict: APPROVED

## Blocking findings (file:line, the input, what happens, why it blocks)
None. No path reaches a display without `FlashGovernor.apply`. No level goes above the config's. No EXACT safety test was changed. The only changed assert is the allowed one.

## The safety points (1 to 10, one short answer each, with numbers)
1. **Every path to a display.** Only two callers make a display: `show/main.py:187` (`_open_wall`) and `tools/wall_pattern.py:296`.
   - Each wraps its display in `GovernedDisplay` at once.
   - `show_soak` and `show_shot` never make a display. They pass a fake or nothing to `ShowLoop`.
   - The only raw `.push(`, `.set_brightness(` and `.close(` calls on a display are in `show/wall.py:60`, `:76` and `:81`.
   - In `_open_wall`, the raw display is only closed when no governor can be built (`main.py:203`). Nothing is pushed to it there.
   - Nothing reads `.display` except the wall itself and one test.
   - I found no alias, `getattr`, lambda or kept bound method that reaches the raw display. `build_parser(defaults=False)` only parses flags.
   - The soak's `timed_apply` calls the real `apply` and returns what it returns. Its `step` wrapper calls the real step.
   - The plan's AST test passes, and the tool has no `.display`.
2. **The close path** (p2_close_faults, p2_torn_base; 3 s strobes at 10 Hz and 5 Hz, fps 20 and 30, then close; measured on the modelled screen):
   - These cases all measure area 0.000 and at most 6 square transitions (budget 6):
     - clean;
     - a failed push just before the close;
     - a failed resend inside the close;
     - every 2nd or every 3rd push failing;
     - one torn push;
     - a KeyboardInterrupt in a push;
     - a KeyboardInterrupt in the close's resend.
   - Repeated torn pushes (every 2nd or 3rd) of a within-budget top/bottom reversal: area 0.000, but **7** square transitions in 7 of 8 cases.
     - The same 7s come from 386d607's `show/wall.py`, and the loop's `_push` is unchanged. So this is **pre-existing, not made by it13** (see Noted).
   - `log.exception` with a normal handler cannot raise. A handler that raises, or a KeyboardInterrupt during the log call, skips the black. The display still closes, and the wall keeps the last governed frame, static.
   - `close` before any push: 2 black frames, then closed.
   - `close` twice: 5 calls. Harmless, and nothing calls it twice.
3. **SIGTERM** (p3_close_sigterm, p3_child_sigterm):
   - A first SIGTERM during the first black of `_close`, after a Ctrl-C: 10 frames, no black. The wall keeps the last governed frame, static. Display closed, lights off.
   - The same during the second black: one black, the wall black.
   - The same during `lights.all_off`: the wall is not closed and the lights are not closed, but the modes are off. The picture is static.
   - None of these is a flash. The governor has only counted frames the wall never got.
   - Under systemd it cannot happen: `run` only ends through the first SIGTERM, and later ones are counted. It needs an interactive Ctrl-C, the end of `--play`, or closing the window. **A note.**
   - A SIGTERM before `run`'s `try`: a KeyboardInterrupt comes out of `main`. No display has been opened (`start` opens it inside the `try`), so the wall is untouched. **A note.**
   - Real child `python -m show --backend fake`: "the show runs" after 0.14 s. SIGTERM 1 s later gives **exit 0 in 0.08 s**.
     - The last log lines: `the show runs at 20 fps`, `closing: the wall goes black, the lights off`, `stopped by SIGTERM, seen 1 times`.
     - `git status` was the same before and after.
4. **The broken show.toml fallback** (p4_fallback; every file also has `fps = 0` to force the fallback):

| brightness | cap | effective |
|---|---|---|
| 0.9 | missing | 0.15 |
| 0.05 | missing | 0.05 |
| 0 | missing | 0 |
| -0.1, 1.5, nan, inf, true, "dim" | missing | 0.15 |
| 0.05 | 0.1 | 0.05 |
| 0.9 | 0.1 | 0.1 |
| 0.05 or 0.9 | 0.0 | 0.0 |
| 0.9 | 1.0 or true | 0.15 |

   - The level is never above the file's valid values or above 0.15 and 0.40. B1 holds in the code.
   - A display key is kept only when its type matches exactly:
     - a width of 128.0 or "128" gives 512;
     - `backend = 3` gives sdl;
     - `ddp_port = 70000` is kept.
   - A width of -64 makes every push raise, and `close` fails at `np.zeros` before its `try`, so the display is not closed. A colorlight display would refuse that size, and nothing is lit. Pre-existing (`load_config` does not check sizes). A note.
   - `backend = 3` in an otherwise valid file: `load_config` accepts it, and `make_display` raises "unknown display backend 3", retried forever. No wall, nothing lit, and no error frame either. Pre-existing. A note.
5. **The fps fallback** (p5_fps; a Config built in code):
   - fps 0, -1, 1, 2.5 and True: pace 20, governor at 30, static frame only.
   - fps 2, 20, 31 and 60: pace equals the governor's fps.
   - The loop never steps faster than its governor.
   - One pre-existing path (p5_retry, `_open_wall` unchanged): a show built before a retried display shows the entry behind the fallback governor, not only the static frame. Pace 20 against a governor at 30. Measured area 0.0 and 6 square transitions, inside the budget. A note.
6. **The pattern tool** (p6_pattern):
   - Every refusal comes before `make_display`: fps 0, nan, 61; gamma 0.5, 3; brightness 0, nan, 0.5. Each exits 2 with no display made.
   - With a config's `brightness_cap = 0.2`: `--brightness 0.25` exits 2. With `brightness_cap = 0.9`: `--brightness 0.41` exits 2. With `brightness_cap = 0`: every level is refused.
   - A config's `backend = "fake"` exits 2.
   - `governor_fps`: 0.5→2, 7.5→8, 59.9→60, never under the push rate.
   - No flag or config gives a level over 0.4 or over the config's cap.
   - A mistyped `--config` path gives `Config()` silently:
     - With `--backend colorlight`, the tool opens colorlight at **512x192**, eth0, level 0.1, cap 0.4.
     - Without `--backend`, it takes `Config()`'s backend, `sdl`.
     - On the 128x64 bench wall that is the wrong size, but the level stays at or under 0.4. `show.poc.toml`'s cap is also 0.40. A note.
   - `steps` changes the device level at 0, 2.05, 4.1, 6.1 and 8.1 s: 0.05, 0.1, 0.2, 0.4, 0.05. The highest level equals `--brightness`, and it changes less than once every 2 s.
   - Share of pixels lit:

| pattern | 512x192 | 128x64 |
|---|---|---|
| grid | 23.4% | 23.4% |
| panels | 1.7% | 1.7% |
| rgb (LEVEL 128, pre-existing) | 99.9% | 99.1% |
| gamma (pre-existing) | 65% | 65% |

     None of the patterns flashes raw.
7. **The soak** (p7_soak, p7_soak_cli, p7_setup_error):
   - The wrapper test compares one session: seed 7 in both runs, clocks within 3e-15 s, the strobe played, 60 of 60 frames identical. Seed 8 gives only 12 of 60 identical, so the test is not vacuous.
   - The wrappers live on a local loop whose display is closed when `soak()` returns.
   - A failing display (22 push failures), a display that fails every 2nd push (20), and a torn push every 2nd push (80) all fail the soak on `push_failures` and `errors_logged`.
   - I found no session that reports clear with pushed frames over the budget: every display fault the code can produce raises.
   - The CLI run (0.5 min, press every 5, cwd the repository, `--out` my scratch folder):
     - exit 0 in 30.2 s;
     - 552 steps, governed 554 (the close's 2 black frames);
     - failures, errors and children all 0;
     - 6 presses, 0 plays (seed 0 never picked station 6);
     - squares_max 2, area 0.0;
     - step_ms median 6.3, p95 10.8;
     - governor_ms median 5.7;
     - fds 4 → 4;
     - peak rss 36.6 → 130.9 MB.
   - `git status` was the same before and after.
8. **The flash meter** (p8_meter_long): 40 sequences.
   - Sources: 10 Hz and 5 Hz strobes, noise, a scroll, and a ramp then a strobe.
   - At fps 20 and 30, for 3 s and 10 s, raw and governed.
   - `area_max` equals `flash_area` and `squares_max` equals `square_flashes` in all 40, with 0 disagreements. Prefixes across the one-window boundary agree too.
9. **The sheets** (p9_pages):
   - Frames and meter numbers come from `display.last` after a step whose count grew, so after the governor.
   - `pages()` loses no cell and keeps the order.
   - A page goes over 4000 px only when one row alone is taller: 40x192 at scale 30. The plan allows that.
   - `--cols 3 --scale 1` gives 3 columns. `--cols 6` exits 2 ("4 columns fit"), with no file.
   - One page keeps `o.png` and `o-distance.png`.
   - `git diff 386d607..418ef74 -- tests/test_show_shot.py` is empty.
10. **The safety files.** `git diff 245cb57..418ef74` is empty for:
    - `arcade/flash.py`, `arcade/brightness.py`, `show/display/colorlight.py`;
    - `tests/test_wall.py`, `tests/test_main.py`, `tests/test_wall_pattern.py`;
    - `show.poc.toml`, `deploy/show.service`, `show/renderer.py`.

    `git diff 386d607..418ef74 --stat -- arcade/` is empty too.

**EXACT tests.**
- `tests/test_wall_close.py` has the 4 T-wall tests. Only the formatting differs: the one-line loops are split. Every assert, input and number is the plan's.
- `tests/test_wall_pattern_governed.py` has the 3 T-pattern tests and the `strobe` helper, character for character except the docstrings.

**Counts.** 1140 collected (`--collect-only`; before: 1064). I did not run the full suite, so I have not seen the skip count myself. The four timing files had no skip.

## Removed or changed asserts
- One only: `tests/test_config.py:20`, `cfg.strip_look == "reverse"` changed to `"bright-on-field"` (Q54, allowed).
- Every other line the diff removes under `tests/` is none: no other `-` line.
- The new test `test_the_default_strip_look_is_the_loop_s_reading_everywhere` is as the plan gives it.

## Noted, not carried (one line each)
- **Pre-existing, the safety owner should see it.** Repeated torn colorlight pushes let a 32x32 square make 7 transitions (budget 6).
  - Why: colorlight's `push` sends the frame packet first, then the rows. So a send that fails mid-rows shows a mix of two frames for one tick, which the governor never counted.
  - The numbers are the same at 386d607 (p2_torn_base).
  - It needs a failure partway through the rows on every 2nd or 3rd push. A cable pull fails at the first packet instead.
  - Candidate for an owner question: govern on what the card may show, or darken after N failures.
- **Pre-existing, in the frozen `arcade/flash.py`.** The governor's first frame passes. From a dark wall, a strobe's first second measures 7 transitions (p2 "from dark" column).
- A first SIGTERM during `_close` (after a Ctrl-C or `--play`) can skip the black or leave the lights unclosed. The picture is static, and systemd cannot trigger it.
- A SIGTERM before `run`'s `try` raises out of `main`, not exit 0. No display is open yet.
- A mistyped `--config` path in `wall_pattern.py` gives `Config()` silently: 512x192, sdl, or colorlight when `--backend colorlight` is given. The level is at most 0.4.
- `backend = 3` in a valid file: no wall and no error frame, retried forever. `load_config` does not check the type. Pre-existing.
- A width of -64 in a config: `GovernedDisplay.close` raises before its `try` and the display stays unclosed. Pre-existing, and nothing is lit.
- `_open_wall`'s retry path can show a show behind the fallback governor, not only the static frame. Inside the budget. Pre-existing.
- The soak reports clear when the show never sets up: `errors_at_setup` is not must-be-zero, as the plan lists.
- The soak's `governed` counts the close's 2 black frames. I2's "governed = steps" will read steps + 2.
- The README's GATE C soak (`--real-devices`) keeps `--backend fake`, so the colorlight push is not soaked. The plan gave that command. The line "need the wall to themselves" suggests more.
- T-shot's strobe session test at 0.9 s never reaches the strobe (held == 0). The plan review showed 1.5 s did not reach it either, so nothing pinned is lost. The session meter during a real strobe is left to I2's `--session strobe --seconds 6`.
- `test_lights_tick_on_every_step` is not vacuous. It fails if a step stops ticking with no show, with a failing push, or with a raising `show.tick`: the three loops, 40 ticks in order.
- I0: `Config()`, `show.toml` and `show.poc.toml` give `bright-on-field`. The rendered strip is a field at green 63 with letters at 255, at 512x192 (text) and 128x64 (ink). No reverse video (p11_strip).
- README commands parse:
  - the soak line;
  - `wall_pattern.py --config show.toml panels` and `grid` write PNGs, exit 0;
  - "every second" matches `WATCHDOG_EVERY_S` 1.0;
  - the stop and broken-config text match the code (p13_readme).
- Timing: every file passed 3 of 3 runs. `test_show_shot_pages.py` ran 2.77 to 2.83 s against its 3 s budget, while another agent's soak ran.

| file | tests | seconds, runs 1 to 3 | budget |
|---|---|---|---|
| test_main_stop | 9 | 0.48, 0.56, 0.54 | 2.5 |
| test_show_soak | 11 | 1.26, 1.22, 1.28 | 2 |
| test_show_shot_pages | 4 | 2.83, 2.79, 2.77 | 3 |
| test_wall_pattern_governed | 32 | 0.38, 0.38, 0.38 | 1 |

  No python process of mine was left afterwards.

## Probes (file names) and minutes (start and end from `date`)
Folder `/private/tmp/claude-502/-Users-trey-dev-codeisart/d1e01db2-fed8-414f-9a38-325b95bc9c3a/scratchpad/it13-review/`. Each probe's output is beside it as a `.txt`:
- p2_close_faults.py, p2_torn_base.py, p2_base_wall.py
- p3_close_sigterm.py, p3_child_sigterm.py
- p4_fallback.py
- p5_fps.py, p5_retry.py
- p6_pattern.py
- p7_soak.py, p7_soak_cli.py, p7_setup_error.py (and the soak's JSON in soak-out/)
- p8_meter_long.py
- p9_pages.py
- p11_strip.py
- p13_readme.py
- p15_timing.txt

The repository's `git status --short` was unchanged throughout. Start 05:40:35, end 05:53:51 (from `date`): about 13 minutes.
