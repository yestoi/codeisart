## Plan (path, line count)
/Users/trey/dev/codeisart/docs/superpowers/plans/2026-09-29-it12-show-runs.md: 299 lines; `awk 'length > 120'` prints
nothing. Not committed (the operator commits). Line 1 is the title; line 2 is "BASE: HEAD at the spawn. Roadmap D3
(Q50, Q52, Q54, Q56, Q58). Carried: C49. Thin plan. SAFETY SLICE." The implementers' BASE is I0's commit on 0dae849.
No other file changed: `git status` shows only the untracked plan beside the operator's state.md edit and the owner's
`reports/` and `research_notes/`, which were not opened.

## Tasks and lanes
- I0 (orchestrator, exact text in the plan): `show/config.py` gets `STRIP_LOOKS`, `strip_look = "reverse"` and
  `gamma = 2.2` with checks in `load_config`. `show.toml` gets the two keys. `tests/test_config.py` gets one assert
  and one test. Then the suite and one commit.
- GROUP 1 (worktrees, one message): T-term (opus, C49: `show/terminal.py`, `show/pipeline.py` and their tests),
  T-state (opus: `show/state.py`, `show/attract.py`, `tests/test_state.py`, `tests/test_attract.py`), T-strip
  (sonnet: `show/renderer.py`, `tests/test_renderer.py`, the three looks and `renderer_for`) and T-deploy (sonnet:
  `entries/hello/hello.c`, `tests/test_entries.py`, `deploy/show.service`, `deploy/README.md`,
  `tests/test_deploy.py`). Merge order: T-term, T-strip, T-state, T-deploy, with the suite after each merge.
- GROUP 2: T-main (opus: `show/wall.py` `GovernedDisplay`, `show/main.py` `ShowLoop`, `show/__main__.py`,
  `tests/test_wall.py`, `tests/test_main.py`).
- GROUP 3: T-shot (sonnet: `tools/show_shot.py` `--session presses|strobe` and `--strips`, `tests/test_show_shot.py`).
- I1: the report, including an empty `git diff 0dae849` on the three safety files. I2: six show_shot commands for
  the operator's verify, plus the first playable by hand.
- Time: new tests aim at 15 s, 20 s at most (T-main 10, T-shot 5, the others 1 to 2). The suite limit is 230 s (it
  was about 200 s at 0dae849). The estimate is about 70 to 75 minutes of implementation, because the three groups
  are forced by the dependencies (main needs Show and renderer_for; show_shot needs main).

## The safety path (what you read in the governor, what it does to a terminal's frames, the probes' numbers)
- What the governor is. `arcade.flash.FlashGovernor(height, width, gamma=2.2, fps=30, threshold=0.1, budget=6)`.
  `.apply` takes any (h, w, 3) uint8 frame and raises ValueError on any other shape or type. The first frame passes,
  and a frame with nothing held comes back as the same object. `held_ticks` counts the frames in which anything was
  held. The window is `fps` frames, so a loop that runs slower than `cfg.fps` is stricter in seconds, never laxer.
  It raises ValueError for gamma of 0 or less, for NaN, and for a non-int fps.
- The path in the plan. Renderer, then the governor, then push. The show has no software brightness limiter:
  `BrightnessLimiter` is tied to `ArcadeConfig`, and the show's brightness is set on the device.
- How the path is enforced. `make_display` is called once, and only as an argument of `GovernedDisplay(...)`. Every
  `.push` in main.py goes to `self.wall`. The error frame, `--play` and the tests' displays all use this path.
- If the governor cannot be built (bad gamma or fps), the display is closed and the wall stays dark. There is no
  fallback that skips the governor.
- A failed push leaves the wall one governed frame behind, which adds no transition. No adapter is needed:
  512x192 and 128x64 work as they are.
- Exact safety test bodies in the plan: `test_a_10_hz_full_screen_strobe_is_held_to_the_budget`,
  `test_the_loop_holds_a_strobing_entry`, `test_every_display_is_wrapped_by_the_governor_at_birth` (an AST test),
  `test_startup_failures_keep_the_loop_and_every_frame_goes_through_the_governor` and
  `test_a_governor_that_cannot_be_built_leaves_the_wall_dark`. `test_the_display_gets_exactly_the_governed_frame` is
  specified in prose.
- Probe results. The probe (read-only) is `scratchpad/it12-plan/probe_governor.py`; it ran on the M1 at 20 fps.
  Held pixels are the most pixels held in any one frame, as a share of the frame.

  | Case | Text view (512x192) | Ink view (128x64) |
  |---|---|---|
  | Attract, 3 lines/s, 20 s | 0 held | 0 held |
  | Attract, 12 lines/s | held 1 frame, max 0.016 | held 286 of 400 frames, max 0.132 |
  | Typewriter, 400 cps | held 3 of 200 frames, max 0.021 | held 42 of 200 frames (21 %), max 0.149 |
  | Typewriter, 1600 cps | held 68 of 200 frames, max 0.047 | held 127 of 200 frames, max 0.218 |
  | Flood, 4 KB a frame | held 54 of 200 frames, max 0.0116 | about 0 |
  | Hello's band, cursor blink, strip alternation every 3 s | 0 | about 0 |
  | Apply time | median 3.8 to 6 ms, max 10.6 to 13 ms | about 0.4 ms |

- Full-screen strobes (text view; the ink view behaves the same):
  - 10 Hz: held 45 of 100 frames; raw flash area 0.898, governed 0.000; square flashes 20 cut to 6.
  - 5 Hz: square flashes 10 cut to 6.
  - 3.3 Hz: square flashes 7 cut to 6.
  - 2.5 Hz: nothing held.
- The legibility test bounds sit above these probe numbers: 0.03 and 0.06 for typing, 0.02 for the flood, 0.25 for
  the ink view.
- The risk: the governor's cost on a Pi 4 at 512x192 may pass the 50 ms frame budget (Q59).

## Decisions taken
- No software brightness limiter. `gamma` is a show.toml key (2.2), so hardware.md's answer can change it without
  code.
- The attract banner stays every 40 source lines. `tests/test_attract.py` (`test_banner_returns_every_40_source_lines`)
  pins it, and the spec asks for it.
- Attract fix: the index advances before the feed, so a line that pyte rejects is fed once. There is a new test.
- Attract and idle autoplay use stations 1 to 5 when any of them is loaded (Q56); a press still plays any loaded
  station. Hello is station 6 today, so the first playable uses key 6, and the show_shot sessions copy hello to
  stations 1 and 2.
- The strip:
  - Q52's text at 80 characters. There is no `NEXT` part with an empty queue.
  - Below 40 characters (Q58), it alternates every 3 s between `<author>, <year>` and `Not A.I.`, and in attract
    between two halves. A notice fills the whole strip.
  - `strip_chars` lives in state.py, so T-state does not wait on the renderer.
- Strip looks (Q54): reverse (0.70, 0), dim-reverse (0.35, 0), bright-on-field (0.25, 1.0). The default is the
  present look, byte-identical to today.
- Other: the cursor blinks at 1 Hz. The watchdog uses sdnotify and sends `WATCHDOG=1` at most once a second, even
  with no show or display.
- hello.c has three lines over 80 characters, not two: lines 21, 29 and 35 (line 35 came with the it11 fix). They are
  cut in comments only, and the `-Wall` warning stays on line 21. Commit before the suite, because
  `tests/test_show_shot.py:153` fails on an uncommitted edit under `entries/`.
- deploy/ is text tested with configparser, never installed.

## Questions for the owner (each with a default the loop takes at once; the next free number is Q59)
- Q59: The governor costs 4 to 6 ms a frame at 512x192 on the M1 (max 13 ms), and on a Pi 4 it may pass 50 ms.
  Default: the loop runs at the rate it reaches (slower is stricter); D4 measures it on the Pi; a faster governor
  would be its own safety slice.
- Q60: The ink view (128x64) holds 400 cps typing on 21 % of frames, up to 15 % of the pixels (the full wall: at most
  2 %). Default: accepted on the proof of concept.
- Q61: Should the attract strip on 128x64 alternate `PRESS A BUTTON` / `ON ANY PORTRAIT` every 3 s? Default: yes.
- Q62: A press on a portrait with no entry plays the cue and flashes its ring, with nothing on the strip. Default: yes.

## What was cut or moved
- If the iteration runs long, T-deploy moves to it13 first. The safety path, C49, the loop, the first playable and
  the strip sheets stay.
- Left out: D4 (test pattern, soak, the governor's cost on the Pi) and GATE C (entries, casts, Linux checks).
- To fit in 300 lines, `test_the_display_gets_exactly_the_governed_frame` is described in prose rather than given as
  exact text. Some exact test code uses one-line defs; the plan lets implementers reformat it without changing an
  assert.
- No harness refusals.

## Minutes
Started about 01:51 CDT; the plan was done at 02:10, and this report followed a minute or two later: about 21
minutes in all, inside the 30-minute limit. The first draft was 448 lines, trimmed to 299.
