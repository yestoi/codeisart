## Plan (path, line count)
/Users/trey/dev/codeisart/docs/superpowers/plans/2026-09-29-it13-pattern-and-soak.md: 299 lines. `awk 'length > 120'` prints nothing, and line 2 is 117 characters. It is not committed; the operator commits it. I changed only this file and this report. The working tree shows just the plan (untracked) beside the state.md edit, `reports/` and `research_notes/` that were already there. I did not open those two folders.

## Tasks and lanes
- I0 (orchestrator, main checkout, first; the exact text is in the plan). Q54: `bright-on-field` becomes the default in `Config` (`show/config.py:28`) and `show.toml:7` together, test first. `tests/test_config.py:20` changes, and one new test pins `Config()`, show.toml and show.poc.toml. One commit, which becomes BASE.
- GROUP 1 (worktrees, one message):
  - T-wall (opus): `show/wall.py`, `tools/flash_meter.py`, `tests/test_wall_close.py`, `tests/test_flash_meter.py`.
  - T-main (opus): `show/main.py`, `tests/test_main_stop.py`. Covers the SIGTERM handler, the fallback keeping the display keys, `lights.tick` at close, and the pace falling back to 20.
  - T-deploy (sonnet): `deploy/README.md`, `tests/test_deploy.py`.
- GROUP 2 (from the HEAD with T-wall merged; at most four tasks at once):
  - T-pattern (opus): `tools/wall_pattern.py`, `tests/test_wall_pattern_governed.py`.
  - T-shot (sonnet): `tools/show_shot.py`, `tests/test_show_shot_pages.py`.
  - T-soak (sonnet, when a slot frees): `tools/show_soak.py`, `tests/test_show_soak.py`.
- Merge order: T-wall, T-deploy, T-main, T-pattern, T-shot, T-soak. The full suite runs after T-wall and after the last merge.
- Nobody edits `show.poc.toml`, `deploy/show.service`, `show/renderer.py`, or the three NOT-edited files. `tests/test_wall.py`, `tests/test_main.py` and `tests/test_wall_pattern.py` are also not edited: new tests go in new files.
- Budget: new tests about 9.2 s in total (T-wall 1, T-main 3, T-pattern 1, T-shot 2, T-soak 2, T-deploy 0.2). Suite limit 245 s against it12's 231 s.

## The governed path (what the pattern tool and the close path do today, what changes, the probes' numbers)
**The pattern tool today.** `tools/wall_pattern.run` pushes straight to the display with no governor. Its protection is the 0.4 cap and the "under half the wall" refusal (`tests/test_wall_pattern.py:46-51`). `steps` changes the device brightness every 2 s.

**The pattern tool after this iteration.**
- `run` wraps the display in `GovernedDisplay(display, h, w, governor_fps(fps), gamma)`, where `governor_fps = max(2, ceil(fps))`. That keeps the governor's window from ever being shorter than a real second.
- It refuses a bad fps (not finite, or outside (0, 60]) and a bad gamma with exit 2, before touching the display.
- It reaches the display only through `wall.set_brightness`, `wall.push` and `wall.close`. An AST test pins this, and pins exactly one `GovernedDisplay(display, ...)`.
- An OSError from a push returns 1 after the close.
- `--config` supplies the backend, size, interface, ddp, gamma and cap (`min(CAP, brightness_cap)`), and a flag on the command line wins.
- New patterns: `grid` and `panels`. There is no `white` (Q64).
- The device brightness in `steps` still bypasses the governor. It is bounded to 0.5 changes a second, at or under the brightness, and a test pins that.

**The close path today.**
- `GovernedDisplay.close` pushes two governed black frames and then closes the display in a `finally`.
- If the last `_send` raised, the frame the governor counted was never shown. If the loop stops before its repush, close sends black straight after the last frame the governor saw, which is not the frame the wall last showed.

**The close path after this iteration.**
- `_send` tracks `unsent` (True from the start until `display.push` returns) and `failed` (a running count of raises). A read-only `last` property is added.
- `close` calls `repush()` first when `unsent` is True (a raise there is swallowed), then sends the two governed black frames as before.
- A clean close is unchanged: 42 pushes at `tests/test_main.py:406-416`.
- The AST counts stay the same: one `.push(`, two `._send(`.

**SIGTERM.** `main()` alone installs a handler that raises KeyboardInterrupt once, so `run`'s `finally` darkens the wall and the lights. Nothing is installed at import.

**Probes** (Mac, patches in memory only, no file edited):
- Look: default patched, 6 test files: 143 passed and 2 failed, the expected two (`test_config.py:20` and `:48`). `:48` passes again once show.toml changes with the default.
- Governed pattern plus the new close: `test_wall_pattern`, `test_wall` and `test_main`, all unchanged: 74 passed in 14.6 s.
- rgb, index, steps, gamma and grid through the governor, at 512x192 and 128x64, 200 frames each: frames unchanged, held 0, the last two frames black. Means: rgb 0.251, index 0.026, steps 0.244, gamma 0.412, grid 0.118.
- Governor cost per frame (Q59, Mac):

  | Frame | Median | p95 | Worst |
  |---|---|---|---|
  | 512x192 strobe | 5.06 ms | 8.62 ms | 12.80 ms |
  | 512x192 static | 4.36 ms | 5.06 ms | 7.10 ms |
  | 128x64 strobe | 0.36 ms | 0.37 ms | 0.40 ms |
  | 128x64 static | 0.33 ms | | |

- Streaming flash meter: its maxima equal `flash_area` and `square_flashes` (1.0 and 20, both sizes). Cost: 4.34 ms median and 6.46 ms p95 at 512x192; 0.32 ms at 128x64.
- The plan's exact safety tests, 7 in all: every one passes against the patches. They must fail on BASE by construction, since the attributes and the governed `run` do not exist there, but I did not run them on BASE. The strobe pattern run gave 101 pushes (99 frames plus 2 black), raw flash_area 1.0, governed flash_area 0.0, and square_flashes 6 (BUDGET 6).

## Existing asserts the plan touches or depends on (file:line, what each needs)
- `tests/test_config.py:20`: the default look is `reverse`. It changes to `bright-on-field` in I0. This is the only assert changed.
- `tests/test_config.py:48`: `load_config(show.toml) == Config()`. It needs show.toml and `Config` changed in the same commit.
- `tests/test_main.py:94-101`: the AST check (one `.push(` and two `._send(` in wall.py; `.push` in main.py only on `self.wall`; `make_display` only in main.py and wall.py). T-wall and T-main keep it. The new tools must not name `make_display`: show_soak.py and wall_pattern.py are not in the checked set, but the plan forbids it anyway, and T-soak has its own AST test.
- `tests/test_main.py:406-416`: a clean close is 42 pushes. It needs `close` to add nothing when `unsent` is False.
- `tests/test_main.py:443-476`: the failed-push counts (count 2). They need the loop's repush path unchanged.
- `tests/test_main.py:189-203`: the fallback's `cfg` equality. It still holds, because those files are not TOML or carry no display keys. T-main must check this.
- `tests/test_wall.py:149-203`: legibility under the default look. These passed in the probe with the new default.
- `tests/test_show_shot.py:47`, `:57-58` and `:176`: the strip is lit over 0.5. These passed with the new default.
- `tests/test_show_shot.py`, the file names at `:34`, `:69`, `:111`, `:202` and `:264`: need one page to keep today's names. The widths at `:90-91` need `--cols` to default to None, which is today's behaviour. `:243` (`label.count("held") == 1`) needs the new label text to add "area" and "sq", not a second "held". `:238` and `:250` need `frames_from_session` to keep its 3-tuple. `:153` is the git-status check: commit before the suite when `entries/` is edited.
- `tests/test_wall_pattern.py`:
  - `:46-51`: under half the wall, for every pattern. This rules out `white`; `grid` and `panels` must pass it.
  - `:100-103`, `:122-147`, `:150-157`, `:160-171`, `:183-191`, `:194-207`: run and main at fps 1 and 2, the parser defaults and the refusals. They need `governor_fps` of at least 2, the defaults unchanged without `--config`, and `_refusal` taking a defaulted `cap`.
- `tests/test_deploy.py:17-18`: `After`/`Wants=network-online.target`. The unit is unchanged (Q63).
- `tests/test_deploy.py:42-46`: the README checks. T-deploy only adds text.
- `tests/test_renderer.py:409-495` passes explicit looks, and `tests/test_state.py:454` does not depend on the default. Both are unaffected, and both passed in the probe.

## Decisions taken
- Q54: `bright-on-field` is the default in `Config` and show.toml in one commit. show.poc.toml inherits it. The renderer's own default stays `reverse`. The owner's pick stays open.
- One pattern tool: `tools/wall_pattern.py` grows. Task 18's separate `test_pattern.py` is not built. Its labelled `index` becomes `panels`, and `grid` is added.
- The pattern tool's governor fps is `max(2, ceil(fps))`, never under the real push rate.
- The close resends the counted frame when the last send did not complete, and black still goes if that resend fails. After a strobe, the close may be held rather than black: the governor wins.
- SIGTERM raises once, and only inside `main()`. `KillMode` and `TimeoutStopSec` stay at systemd's defaults.
- A broken show.toml keeps its display keys (the right type, not bool) and never its brightness, cap, gamma or fps.
- An fps under 2 in a `Config` built in code runs at `FALLBACK_FPS` 20, and nothing divides by it.
- The soak runs in process with fakes, drives the real `loop.run()`, and stops with a KeyboardInterrupt subclass. It writes JSON under the gitignored `data/soak`. `--real-devices` and the Pi's Q59 numbers belong to GATE C.
- `tools/flash_meter.py` reads arcade.flash's internals (`_Transitions`, `_Window`, `signals`, `square_means`) without editing that file.

## Questions for the owner (each with a default the loop takes at once; the next free number is Q63)
- Q63: May the unit order itself after `network.target` instead of `network-online.target`? Default: unchanged. The README says that a start with no carrier waits for wait-online's timeout and then runs. A change would edit `tests/test_deploy.py:17-18`, which only the owner may allow. Deadline: GATE C.
- Q64: Should there be a full `white` pattern (the core plan's week 4 dead-pixel hunt)? Default: not built. It would break "under half the wall", and the repository has no figures for the panels' current against the supplies. Given those figures from the owner, the loop would add it, capped at 0.1, with its own refusal and test. Deadline: the full wall's bring-up.

## What was cut or moved
- `white` moved to Q64.
- The unit's network-target change moved to Q63.
- A "push black until the wall is dark" close was cut. It would change the exact count at `tests/test_main.py:415`. Noted for later.
- The Pi 4 governor measurement and the `--real-devices` soak moved to GATE C. The overnight soak is the owner's run, and the README documents it.
- Task 18's separate `test_pattern.py` tool is not built.
- To get under 300 lines, I compacted the prose. The test lists for T-main, T-pattern and T-soak are now names with short notes, not full descriptions. The exact safety test bodies (4 in `test_wall_close.py`, 3 in `test_wall_pattern_governed.py`), the interfaces, the lanes and the owners are kept in full.
- No command was refused by the harness. I did not run the full suite, did not replay the plan, and did not run the exact tests against BASE.

## Minutes (start and end from `date`)
Start 04:13:25 CDT. End 04:33:45 CDT (2026-09-29), about 20 minutes. This spans a context compaction.
