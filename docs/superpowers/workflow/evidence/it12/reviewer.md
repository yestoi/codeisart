## Verdict: APPROVED

## Blocking findings (file:line, the input, what happens, why it blocks)

None. I found no safety gap, no reproduced wrong result, no missed stated requirement and no weakened assert.

## The safety points (1 to 10, one short answer each, with numbers)

1. **Every path to a display: all governed.**
   - `make_display` is called once, at `show/main.py:152`, inside `GovernedDisplay(...)` through the walrus `raw`.
   - The only `.push(` call in `show/` is `self.wall.push` (`main.py:272`), plus `self.display.push` in `_send` (`wall.py:57`).
   - `_send` is called only by `push` (after `apply`) and by `repush` (the stored `apply` output).
   - `raw` is used only for the fallback wrap (`main.py:163`) and for `raw.close()` (`main.py:168`).
   - `ShowLoop._display` is read only in `_open_wall`. `GovernedDisplay.display` is read only in wall.py (`set_brightness`, `close`, `_send`).
   - `tools/show_shot.py` builds `FakeDisplay()` and hands it to `ShowLoop`. It never names `make_display` and never calls `.push`.
   - Its session frames are `display.last` (`show_shot.py:369`), which is after the governor. Its `--strips` frames and its older modes are PNG renders, and no display receives them.
2. **The AST test is the plan's text.** `tests/test_main.py:87-103` equals plan lines 209-225 word for word.
   - The code passes it by meaning. `close` binds `push = self.push`, the governed method (`wall.py:49-52`). `test_a_clean_close_pushes_two_governed_black_frames` pins that the two blacks equal a reference governor's `apply(black)` twice.
   - Nothing else is hidden this way. A grep of `show/*.py` and `tools/show_shot.py` finds no alias, `getattr`, stored bound method or lambda that reaches a display's `push`.
   - The `getattr` at `main.py:367` is `lights.close`. The lambdas are `on_key` and the no-op notifier.
3. **The repush path cannot flash more than the governed sequence.** Probe `p3_repush.py`: the real `ShowLoop`, 512x192 at 20 fps, 120 steps, the plan's `StrobePlayer` (10 Hz and 5 Hz), a display that fails on a pattern.
   - Raw area was 0.8979 in every row. Every row, for both strobes, measured:

   | Measure | Result |
   |---|---|
   | Governed area | 0.0000 |
   | Received area | 0.0000 |
   | Wall-per-step area | 0.0000 |
   | square_flashes, every sequence | at most 6 (budget 6) |

   - Other numbers:

   | Pattern (10 Hz) | Display calls | Received | Governed | Held |
   |---|---|---|---|---|
   | none | 122 | 122 | 122 | 44 |
   | every 2nd fails before showing | 240 | 120 | 122 | 44 |
   | every 2nd fails after showing | 240 | 240 | 122 | 44 |
   | run of 3 in 7, before | 141 | 80 | 81 | 29 |
   | run of 5 in 9, after | 136 | 136 | 61 | 22 |
   | random 50 %, before / after / mixed | 151 / 161 / 145 | 74 / 161 / 111 | 76 / 86 / 74 | 21 / 27 / 23 |

   The 5 Hz rows are the same kind (squares 4 to 6).
   - Why it holds:
     - `_last` is set before `_send`.
     - After a failed push, the next step repushes that `_last` before it governs anything new.
     - If the repush fails too, the step governs nothing (`main.py:270-272`).
   - So every governed frame reaches the wall in order, and nothing else does; frames are only repeated. Repeats add no transitions. A late frame is followed at once by the next governed frame. So any real second holds at most the flips of fps + 1 consecutive governed frames, which the governor bounds to 6.
   - Governed and received disagree only at the close: after a failed push, `close` governs black without a repush first.
4. **A raising `apply` or renderer: the wall keeps its picture and the loop goes on** (probe `p5_fallback.py`, section 4).
   - Three raising `apply` calls (2 wrong shape, 1 wrong dtype) raise before the governor changes any state.
   - The next steps repush the last governed frame (5 pushes). The show keeps playing.
   - The governor's `_prev` equals the last frame shown, so the next frame is governed against the right frame.
   - A renderer that raised twice: 5 pushes, 5 governed (the last rendered frame again, governed again). The show went back to attract, and the last frame is lit.
5. **The fallback shows only the governed error frame** (probe `p5_fallback.py`, section 5; 121 steps, a press, then a step at 100 s).
   - Inputs: gamma 0.22, 22, NaN, True, -1, inf; fps 1, 0, 2.5, True, -5.
   - Every case: no show; the wall's governor is 2.2 / 30; 121 pushes, 121 governed; all pushes identical and lit; raw not closed; the error names the governor; the press changes nothing; no retry reopens anything.
   - If no governor can be built at all: `wall` None, 0 pushes, raw closed, lights all off. There is no retry (`_wall_retry` is False), so no later path pushes ungoverned.
   - (Noted only) With fps 0, `run()` raises ZeroDivisionError at `main.py:325`, before its `try`, with nothing opened yet. With fps -5 it steps without sleeping. Only a Config built in code can carry these values.
6. **The repo's configs load and are checked.**
   - `show.toml`: 512x192, text view, fps 20, gamma 2.2, look reverse, brightness 0.15, cap 0.4.
   - `show.poc.toml`: 128x64, ink view, fps 20, gamma 2.2.
   - `load_config` refuses gamma 0.22, 22.0, true, nan and inf, and fps 1, 2.5, true and 0. It loads gamma 1 and 2, and fps 2 and 1000.
   - `config_from` on a file with gamma 0.3 gives `Config()` plus the error. The loop on it shows a static, lit error frame, governed (41 of 41, governor 2.2 / 20) and no show.
7. **The loop cannot step faster than `cfg.fps`.**
   - `run()` sets `due = now + period` from the time taken just before the step, and sleeps until `due` (`main.py:339-346`). So steps are at least 1/fps apart, with no catch-up.
   - `repush` does not call `apply`. `close` adds two `apply` calls for black frames, which cannot flash.
   - So the governor's fps frames always span at least a second (at least fps periods for fps + 1 frames).
   - The only way to step faster is fps ≤ 0 in code (point 5).
8. **Close and stop: a note, not a gap.**
   - Neither the spec nor either plan asks for a SIGTERM handler. The plan's `finally` covers Ctrl-C, the window's close and `--play`'s end.
   - The plan says "no `KillMode`", and the unit sets none. The default `control-group` sends SIGTERM, then SIGKILL, to every process in the cgroup, so entries cannot outlive the daemon.
   - On `systemctl stop` the wall keeps the last governed frame, static, which is not a flash. The plan review's N18 made the same call.
   - A handler would give the two black frames on stop. Candidate for it13.
9. **The show's own drawing stays far from the threshold.**

   | Drawing | Transitions | Area |
   |---|---|---|
   | Cursor blink, 1 Hz | 2 per second | one 6x8 cell |
   | Short strip, every 3 s | 2 per 6 s | strip row: 1/24 of 512x192, 1/8 of 128x64 |
   | full_screen strip, 2 s in 10 | 2 per 10 s | strip row |
   | Notice | 2 per 2 s at most | strip row |
   | Error frame | none (static) | whole frame |

   Every rate is far under 6 per second. The test file `tests/test_wall.py` pins held 0 for the cursor blink, the strip alternation, attract and the hello band.
10. **The three safety files are unchanged.** `git diff 0dae849..245cb57 -- arcade/flash.py arcade/brightness.py show/display/colorlight.py` is empty (0 lines). `git diff --stat 02f3944..245cb57 -- arcade/` is empty.

The other points:
- **11. C49 can be closed.**
  - I copied the it11 probe (`p11_c49.py`) and ran it on HEAD. The real pyte TypeError now fires inside `kill()`'s pump; it is logged once and `stop()` returns.
  - After it: phase DONE, `master_fd` None, `_pgid` None, the child gone.
  - `test_a_pump_exception_leaves_no_open_master` patches `term.stream.feed`. That is the same call that raises in the real case (`Terminal.feed` then `stream.feed`, inside `kill()`'s pump). `test_kill_closes_the_master_when_the_pump_raises` and `test_stop_returns_when_the_pump_raises_in_kill` use the real `\033[?3A`.
- **12. `show/state.py` matches spec 4.5/4.6 and the plan.** Checked by reading:
  - Every press gives a cue and a flash.
  - `PLAYING` and `QUEUED #n` show for 2 s. `NEXT: <title> (<n> queued)` shows only when something is queued. The plan says title; the team lead's brief said slug.
  - The strip is cut to `strip_chars`. Below 40 characters it alternates every 3 s from the entry's start (attract too), and a notice fills the whole strip.
  - `eligible` leaves stations above 5 out of attract and autoplay, but a press plays them.
  - A press on an empty portrait gives the cue and flash only.
  - Every raise goes through `_recover`: the next queued entry or attract.
  - The strip row is always drawn, so the wall is never blank.
- **13. Byte-identical.** Probe `p13_reverse.py`: the default look `reverse` against `show/renderer.py` at 02f3944, over 300 frames (text 512x192, ink 128x64 and 512x192, every phosphor, glow on and off, bold, reverse, cursor, full-screen and wide strips). 0 frames differ.
- **14. `tests/test_show_shot.py` passes 5 of 5.**
  - Each run: 20 passed, 18.0 to 18.5 s (the operator's full suite was running at the same time).
  - `test_strobe_session_is_held`: 3.59 to 3.65 s.
  - Its `flash_area` 0.0 is taken from `display.last` after each step (`every_ms=1` keeps every step). Those are the frames the display received.
- **15. The deploy text matches the plan.** `WatchdogSec=15`, `Restart=always`, `RestartSec=2`, `StartLimitIntervalSec=0`, `User=pi` (the README says to edit it), `Type=notify`, `ProtectSystem=strict` with entries writable, no `KillMode`.
- **16. hello.c: comments only.** Lines 21, 29 and 35 changed in their comments only. `cc -Wall` gives exactly 1 warning (unused `leftover`, line 21). No line is over 80 characters.

## Removed or changed asserts
- `git diff 02f3944..245cb57 -- tests/` removes 0 lines at all, so no assert is removed.
- `test_config.py` only gains lines.
- New skip markers: 5, all `skipif(no cc)`, as the plan asks. With cc present there is no new skip.
- Collected: 1064 (before: 966).
- The core plan's `lights.ticks == 1` became `lights.levels == {}` in `tests/test_state.py:198-202`. This is not a weakening:
  - The it12 plan (line 56) moves `lights.tick` to the loop, so the new assert pins the new rule, that the show does not tick.
  - The scroll assert is kept.
  - No test in `test_main.py` pins that the loop calls `lights.tick` (the code does, at `main.py:231`). Noted below.
- EXACT safety tests, compared line by line with the plan: `test_a_10_hz_full_screen_strobe_is_held_to_the_budget`, `test_the_loop_holds_a_strobing_entry`, `test_every_display_is_wrapped_by_the_governor_at_birth`, `test_startup_failures_keep_the_loop_and_every_frame_goes_through_the_governor` and `test_a_gamma_the_governor_refuses_shows_its_error_governed`.
  - Their inputs, numbers and asserts equal the plan's.
  - Only the layout changed: one statement per line.
  - The prose ones (`test_the_display_gets_exactly_the_governed_frame`, `test_the_loop_s_own_display_is_governed`, `test_when_no_governor_can_be_built_the_wall_stays_dark`) hold what the prose says.

## Noted, not carried (one line each)
- Deviation 1 (T-shot tests 6.6 s against a 5 s budget): accepted; it is timing only.
- Deviation 2 (STROBE_C adds `2J`, full buffering, 1.1 s of black and a blank `shown.txt`): accepted. The plan's description still holds, the test is not an EXACT one, and no assert changed. The leftover it removes is Q13's small-area exemption, by design.
- Deviation 3 (session reaches into `loop._devices`, `presses=` override, `NOTICE_S` patched in tests): fine for a tool.
- Deviation 4 (`push = self.push` in `close`): governed, as B6 asked. Accepted.
- Deviation 5, readings: fine. "Repush fails: skip that step's push" is what keeps the received frames equal to the governed ones.
- Deviation 5, no SIGTERM handler: a note for it13 (safety point 8).
- Deviations 6 to 9: fine. Deviation 10 (commit trailers) is outside this review.
- Colorlight, torn push (colorlight.py is frozen, and the backend is secondary):
  - The card latches the rows of the previous push. So a push that fails partway leaves a mixed frame, and the repush's frame packet shows it for the time its rows take to go out (a few ms).
  - Each pixel still sees only governed values. A square's mean can move for those few ms. A D4 bench check with a failing NIC would settle it.
- `config_from`'s fallback `Config()` has backend "sdl". On the Pi, a broken show.toml leaves the wall dark (the plan review's N3), and `deploy/README.md` does not say so.
- `After=`/`Wants=network-online.target` (as the plan says) can delay the start while there is no carrier; spec 4.6 wants the loop up.
- No test pins that the loop calls `lights.tick` every step.
- fps 0 or below in a Config built in code: `run()` raises before its `try` (fps 0) or steps without pause (fps below 0). `load_config` refuses both.
- The README says the watchdog is pinged "every few seconds"; the code pets it every 1 s.
- Rule breaks on my side:
  - Two of my Bash commands began with a `cd` outside the repository (`cd /private/tmp`, `cd /dev/null`). No git command or edit was involved.
  - My probes imported repo modules without `PYTHONDONTWRITEBYTECODE`, so they may have refreshed the git-ignored `__pycache__/*.pyc` in `show/`, `show/display/` and `tests/` (other runs wrote those too).
  - No other file is in the repository from me, and no child process of mine is left.

## Probes (file names) and minutes
All are in `/private/tmp/claude-502/-Users-trey-dev-codeisart/d1e01db2-fed8-414f-9a38-325b95bc9c3a/scratchpad/it12-review/`, with each output beside it as `.txt`:
- `p3_repush.py`: repush under failing displays, 10 Hz and 5 Hz.
- `p5_fallback.py`: points 4, 5 and 6.
- `p11_c49.py`: the it11 probe, copied.
- `p13_reverse.py`, with `old_renderer.py` from 02f3944: point 13.
- `p14_show_shot_x5.txt`: five runs of `tests/test_show_shot.py`.

Minutes: about 25.
