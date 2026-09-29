## Verdict: CONFIRMED

## B1 (lifted or not, the evidence)
Lifted. Plan lines 115-118 now set `brightness` and `brightness_cap` each to the lower of the file's value (a real number 0 to 1, not bool) and `Config()`'s. Any other value takes `Config()`'s. gamma and fps never come from the file. The wall's level is `effective_brightness` = min(brightness, cap). Case by case:

| File's value | Result |
|---|---|
| Key missing | The default (0.15 and 0.40), which is never above the default |
| Bool (`true`) or string (`"dim"`) | The default. The file's valid cap still applies, e.g. `"dim"` with cap 0.1 gives min(0.15, 0.1) = 0.1 |
| Negative, over 1, nan, inf | Outside 0 to 1, so the default. The file's number is not a level |
| Cap below brightness (0.3 with cap 0.1) | min(0.3, 0.15) and min(0.1, 0.40): the wall gets 0.1, the file's own effective level |
| Brightness 0.05, cap 0.1 | 0.05 |
| 0 | 0, a dark wall as asked |

- In no case is the level above the file's valid brightness or cap, or above the default.
- The test at lines 132-134 covers 0.9, 0.05 with 0.1, `true` and `"dim"`.
- The README at line 142 says "at the lower of the file's brightness and the default".

## B2 (lifted or not, the evidence)
Lifted. Lines 193-202 are the review's replacement, word for word, with the wrap check kept.
- **Against the planned `main`.** Refusals come before `make_display`, and `main` never touches the display. The writer's probe `it13-plan/probe_ast_fix.py`, rerun by me, gives:
  - A governed `run` plus the planned `main` (`--config` via `load_config` and `cfg.*`, `save_png`, `make_display` handing the display to `run`): passes.
  - Today's file: fails on 3 `display.push`.
  - A `main` that calls `display.close()`: fails.
- **Legitimate code that could trip it.** Nothing the plan requires does.
  - `from show.display import make_display` is an ImportFrom, not an Attribute.
  - `cfg.*` names none of `display`, `_send`, `push`, `set_brightness` or `close`.
  - `wall.governor...` is allowed.
  - `wall.display` is forbidden, and nothing the plan requires needs it.

## New blocking findings from the fix pass (or "none")
None.
- **T-soak's start.** Waiting for T-main is a sound lane: T-main is in group 1, and the merge order already puts T-main before T-soak. No file has two owners.
- **Note 4 left out.** Leaving the fallback governor at fps 30 is right. `tests/test_main.py:126` asserts it, and the plan names that at line 125.
- **The compaction lost nothing.** The six exact test bodies and all owners' files are intact (lines 62-100, 170-203, 28-32).

## Notes for the implementation review (one line each, at most five)
- **The strobe session at 1.5 s never reaches the strobe, so `squares_max <= BUDGET` in `test_the_strobe_session_labels_its_flash_numbers` is vacuous there.** Probe `probe_strobe15`: 28 frames, held 0, square_flashes 1, in 1.64 s; at 3.4 s it is held 6 and square_flashes 6, in 3.66 s. The flash property stays pinned by `tests/test_show_shot.py:248` and `tests/test_flash_meter.py`. The label check still works. Ask for `dwell=0.1` and an assert of held > 0, or accept that this test is only a label test.
- **`test_a_broken_show_toml_keeps_its_display_keys` leaves out a negative level, a level over 1, and a cap below the brightness.** Check that `config_from` range-checks rather than taking min(), since min(-0.1, 0.15) would pass a negative level through.
- **The planned `run` must not reach `wall.display`.** For example, a printout of the display's name would trip B2's test. Only `wall.governor` is allowed.
- **`Sigterm.seen` is now an int.** Check that `main` logs the count after the close and never from the handler.
- **`test_the_wrappers_change_no_frame` needs the same seed and clock in both runs.** Otherwise it compares two different sessions.

## Minutes (start and end from `date`)
Start 04:57:16 CDT, end 04:58:07 CDT, 2026-09-29. No repository file changed. The one probe ran from scratchpad/it13-plan-review/ and left no child process. `decisions.md` and `state.md` show as modified in `git status`; those edits are not mine.
