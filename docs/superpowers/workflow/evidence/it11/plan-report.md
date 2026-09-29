# it11 plan report (D2, one entry end to end)

## Plan (path, line count)
/Users/trey/dev/codeisart/docs/superpowers/plans/2026-09-29-it11-show-one-entry-end-to-end.md
- 294 lines (`wc -l`). `awk 'length > 120'` prints nothing.
- Revised against c28c027, the merged ink view. I read `git diff ebd367c..c28c027`.
- Not committed. The modified decisions.md, roadmap.md and state.md in the main checkout are the operator's; I did not touch them.
- BASE: HEAD at the spawn, after I0 commits the plan on c28c027.
- SAFETY SLICE: no. D2 pushes no frame to any display.

## Tasks and lanes
- I0 (orchestrator, main checkout, before any spawn): adds one config key, `lightbox_pins = [17, 22, 23, 24, 27]`.
  - Why: amendment Task 13 has the lights drive the lightboxes as well as the rings, and `Config` has only `light_pins`.
  - The edits are to the merged files, where c28c027 put `view` after `glow`. The exact text for all three is in the plan:
    - `show/config.py`;
    - `show.toml`;
    - one assert in `tests/test_config.py::test_defaults_when_file_missing`.
  - `show.poc.toml` gets no key; it takes the defaults.
  - The edit is committed with the plan; that commit is BASE.
- GROUP 1: four worktrees in one message. Merge order: T-pipe, T-hello, T-attract, T-io, with the suite after each.
  - T-pipe (opus): `show/terminal.py`, `tests/test_terminal.py`, `show/pipeline.py`, `tests/test_pipeline.py`.
    - The terminal is committed first: C48, plus note 2's drain (`DRAIN_MAX` 2 s, a new keyword on `finished_or_orphaned`).
    - Then the pipeline, with 21 named tests.
    - C48 is not a serial lane. The pipeline is the first caller of `run`, `kill` and `finished_or_orphaned`.
  - T-hello (sonnet): `entries/hello/hello.c`, `entries/hello/entry.toml`, `tests/test_entries.py` (tests added only).
    - One `-Wall` warning, on purpose.
    - About 3 s of large motion; station 6.
    - No fallback is committed.
  - T-attract (sonnet): `show/attract.py`, `tests/test_attract.py`.
  - T-io (sonnet): `show/input.py`, `show/lights.py`, `show/audio.py`, `tools/make_cues.py`, `audio/*.wav`, `tests/test_io.py`, `tests/test_make_cues.py`.
    - Cues play through `pygame.mixer`, with the mixer injected in tests.
    - GPIO is tested through a fake `gpiozero`.
- GROUP 2: one worktree from the merged HEAD. T-shot (sonnet) owns `tools/show_shot.py` and `tests/test_show_shot.py`.
  - New modes and options: `--entry DIR` (the real pipeline on a temp copy), `--build CMD`, `--capture-first`, `--attract DIR`.
  - Both modes honour the merged `--config`.
  - Both render through the merged `_renderer(cfg, font)`, that is `Renderer(font, width, height, columns, rows, phosphor, glow=False, view="text")` called with `cfg.glow` and `cfg.view`.
  - `test_attract_mode_scrolls` also runs with `Config(width=128, height=64, view="ink")`.
- I1: merges and readings.
- I2: four operator commands, from a clean checkout.
  - hello, text view.
  - hello with `-Werror`: the build fails and the captured fallback plays.
  - Attract mode.
  - New: `--config show.poc.toml --entry entries/hello --every-ms 1500 --look led`. It should show a cell as a dot, a moving stripe for the band, no cursor, and the strip cut to `NOW: hello by Trey, 2`, which is Q58's cut.
  - The `--crop 16,128,128,64` sheet is **dropped**. It showed the text view's 21x8 corner, which the proof of concept no longer uses.
- Suite limit: 212 s (it was 192 s).
  - Base: 176 s, the ink branch's own run (175.9 s). The suite at c28c027 ran 901 collected, 900 passed, 1 skipped, in 169.4 s.
  - Shares: T-pipe 15 s, T-attract 1 s, T-io 1 s, T-hello 4 s, T-shot 7 s. That gives about 204 s, plus 8 s for the spread.
- Every file is owned by exactly one task. Shared files are I0's only.

## Owner questions (with defaults)
- Q55: How are the lightboxes wired, and can they dim?
  - Default: 12 V through a MOSFET, on the PWM pins [17, 22, 23, 24, 27].
  - Level 0.4 when idle or queued, 1.0 while that station plays.
  - The rings stay on `light_pins`.
- Q56: Does `entries/hello` play on the festival wall?
  - Default: no. It is for tests and demos (station 6).
  - Once a station 1 to 5 entry is loaded, D3's attract and autoplay leave out stations above 5.
- Q57: What does the wall print around an entry?
  - Default: a shell transcript: title, plaque, `$ cat <source>`, `$ <build>`, `$ <run>`.
  - On failure: `*** <reason> ***`, then `$ <run>   (recording)` over the replay.
- Q58 is the operator's (the 128x64 strip cuts "Not A.I."). The plan lists it under D3 and plans no fix.

## Mismatches found (core plan against amendments, spec and code)
1. **Crowd mode.** The amendment reads it only at the start; spec 4.5 makes it follow the queue. The plan makes it a flag read every tick.
2. **`signal_of`.** The draft also counts return codes above 128 as signals; the amendment counts only codes below 0. `exec ` is prepended per the amendment.
3. **Pipeline draft.** It lacks:
   - `sandbox.wrap`;
   - `min_build_seconds`;
   - `LC_ALL=C`;
   - the `.part`-then-rename capture;
   - pump exception handling.
4. **Lights and audio.**
   - Lights: `Config` has no lightbox pins (hence I0), and the draft has no pulse speeds, `flash` or `all_off`.
   - Audio: the error cue is a square wave, and cues play through unreaped `aplay`/`afplay` children with no volume or quiet hours.
5. **Attract draft.**
   - The year is printed twice.
   - There is no 40-line banner and no `idle_seconds`.
   - There is no row reset after a full-screen entry.
   - A late tick is not capped.
6. **`entries/hello` draft.**
   - Station 1, and no `-Wall`.
   - No motion.
   - A plaque without the year.
   - It imports `from helpers`.
7. **`make_cues`** runs by path; the loop runs tools as modules.
8. **Core Task 14 is stale** (`status_line()`, `matrix` in the deploy README). That is D3's to fix.
9. **`fast_cfg`** keeps `min_build_seconds` at 1.5. `show_shot`'s `PLAY_STRIP` is hard-coded to hello; T-shot replaces it with `play_strip(entry)`.
10. **The ink view (c28c027) against the team lead's list.**
    - D2's `pipeline.py` and `attract.py` feed a `Terminal` and build no `Renderer`. The only renderers in D2 are T-shot's, through `_renderer`, which already passes `cfg.view`.
    - `main`'s renderer is D3's, and the plan's Decisions say it must pass `cfg.view`.
    - In the ink view the terminal stays 80x23, so `EntryPlayer`, `Attract` and the `full_screen` rows need no change.

## Risks for the orchestrator
- **The terminal change reaches every `Terminal` user.** All 24 existing terminal tests must stay green unchanged. `run()` no longer kills the previous group, so a caller that ends a run without `finished_or_orphaned`/`kill` would leave orphans.
- **Real-time tests** (min build, crowd, flood median, drain_max) can flake while four worktree suites run at once. Rerun one alone before calling it failed, and never loosen a bound.
- **Suite time.** The spread is 169.4 s to 175.9 s on the same code. Over 212 s is a reading to report, not a bound to raise.
- **Linux.** The drain's 64 KB tail, dash without a controlling tty, and `unshare` are unchecked. They are for GATE C on the Omarchy box.
- **Audio.**
  - `pygame.mixer` has never been started on the Pi.
  - `test_committed_cues_match_the_generator` needs identical bytes across platforms. If they differ, T-io reports it rather than loosening the test silently.
- **The poc sheet.** In the ink view, `_program_black` counts any lit pixel above the strip's row. hello's frames are lit from SOURCE on, so the sheet should not trip it. If it does, look at the first frame before using `--allow-black`.
- **Operator time.** `--entry` runs at show.toml's timings (dwell 4 s, error_hold 3 s): about 15 to 20 s per I2 command.
- **Branches.** T-hello builds only in temp copies. It merges second, so T-shot's worktree has it.

## Minutes (from `date`)
- First pass: 00:21 to 00:35 CDT, about 14 minutes.
- Revision for c28c027: 00:36 to 00:40, about 4 minutes.
- About 18 minutes in all.
