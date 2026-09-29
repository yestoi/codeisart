## Fixed (B1, B2: the plan's new lines, quoted)
**B1, the fallback's brightness: the lower value wins.**
- The `config_from` interface (T-main):
  ```
      # the file when it parses as TOML and the value has the default's type (not bool); `brightness` and
      # `brightness_cap`: each the lower of the file's (a real number 0 to 1, not bool) and Config()'s; a value not
      # such a number: Config()'s, the only level then known; never gamma, fps. Then --backend, --capture, as now.
  ```
- The test `test_a_broken_show_toml_keeps_its_display_keys`:
  ```
  (colorlight, `enp3s0`, 128x64 kept beside `fps = 0`: fps 20; brightness `0.9`: 0.15; brightness `0.05` with
  `brightness_cap = 0.1`: 0.05, 0.1; brightness `true` or `"dim"`: 0.15; not TOML: `Config()`; `backend = 3`: sdl)
  ```
- The README (T-deploy): "a broken show.toml: the error frame on the file's own display at the lower of the file's brightness and the default".

**B2, the pattern tool's AST test.** It now checks every `ast.Attribute` node, not only calls, and forbids `_send` and `display` attributes anywhere in the tool:
```python
    attrs = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute)]  # every use, not only calls (no aliases)
    for name in ("push", "set_brightness", "close"):
        used = [n for n in attrs if n.attr == name]
        assert used and all(ast.unparse(n.value) == "wall" for n in used), name
    assert not [n for n in attrs if n.attr in ("_send", "display")]
```
The `GovernedDisplay(display, ...)` wrap check is unchanged.

**Checked with a probe** (`scratchpad/it13-plan/probe_ast_fix.py`, in memory only):
- It passes on a governed `run` that takes `display` as a parameter, together with `main` as planned: `--config` read through `load_config` and `cfg.*`, `save_png` (PIL `.resize`/`.save`), refusals before `make_display`, and `make_display` in `main` handing the display to `run`.
- It fails on today's file (three `display.push`).
- It also fails if `main` ever calls `display.close()`. So the plan now says: "Every refusal (brightness, fps, gamma) comes before make_display; main never touches the display, run does, through wall."
- `test_main_refuses_before_making_the_display` is added to T-pattern's test list.

## Notes folded in (by number) and notes left out (by number, why)
1. **Folded in.** `test_systemctl_stop_is_a_clean_exit` runs the child as `python -m show --backend fake` under `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy`, keeps the real `AudioCues` (SDL's mixer swallows SIGTERM on BASE), and kills the child in a `finally`.
2. **Folded in.** `Sigterm` only counts later signals and never logs itself; `main` logs the count after the close. `unsent` is False at first. `close` runs the repush inside the `try` whose `finally` closes the display: an Exception there is swallowed and black still goes, while a KeyboardInterrupt goes on to the `finally`.
3. **Folded in.** The in-process test asserts `isinstance(signal.getsignal(SIGTERM), Sigterm)` before `os.kill`.
4. **Left out, as the lead's instruction allows.** `tests/test_main.py:126` pins `loop.wall.governor.fps == 30` for the refused-gamma fallback, and that file is not edited. The plan now says: "The fallback governor keeps fps 30 (`tests/test_main.py:126` pins it; a static frame only)." For a bad fps, the pace of 20 is already under 30. The only gap is a refused gamma with `cfg.fps` over 30, and then only the static error frame is shown.
5. **Folded in.** The `FlashMeter` is built from `wall.governor`'s fps and gamma, both in `show_shot.frames_from_session` and in the soak. The soak keeps the meter's time out of `step_ms`.
6. **Folded in.**
   - The strobing soak test asserts on the Recorder's pushed frames (`flash_area == 0.0`, `square_flashes <= BUDGET`).
   - New test `test_the_wrappers_change_no_frame`: for one seed, the pushed frames are identical with and without the soak's wrappers.
   - Decided: T-soak starts from the HEAD with T-main merged too, and `show_soak.main` runs inside `show.main`'s `sigterm_raises()`. The GROUP 2 lane line says so. The merge order (T-main before T-soak) already fits. This also removes the review's "clock that never runs out" concern.
7. **Folded in.** `_refusal` checks brightness in (0, min(cap, CAP)]. `main` refuses brightness, fps and gamma before `make_display` (see B2).
8. **Folded in.** The strobe session test is "as `tests/test_show_shot.py:248` but `seconds=1.5`". New shares: T-wall 1, T-main 2.5, T-pattern 1, T-shot 3, T-soak 2, T-deploy 0.2, about 9.7 s.
9. **Folded in.** The README check also asserts "every few seconds" is gone. The README says the overnight and GATE C soaks run with the unit stopped.
10. **Folded in.** Under Decisions: "On the Pi at GATE C: `--real-devices`, pyte's feed time and the governor's cost (Q59); the operator writes that deadline into Q59 in decisions.md."

**Also done:**
- Cut both "Probe: ..." sentences (T-wall's meter numbers and T-pattern's governed-pattern numbers); they are in the first report. Cut I0's probe sentence and the Q54 decision line (I0 states it).
- T-pattern now says `run`'s loop reads `clock()` once a frame, as today (`tests/test_wall_pattern.py:122-137`).
- Compacted the soak's text, I1, I2's expectations and the Q63/Q64 wording to stay under 300 lines. The exact test bodies, the interfaces, the lanes and the owners are unchanged, apart from B2's lines.
- Not folded in: the review's optional "`unsent = True` at `push`'s start, before `apply`". The review showed that skipping a counted frame never adds transitions, and the lead did not list it.
- No command was refused by the harness. `git status` shows `decisions.md` modified; that edit is not mine.

## Plan (line count, the `awk 'length > 120'` result)
/Users/trey/dev/codeisart/docs/superpowers/plans/2026-09-29-it13-pattern-and-soak.md: 299 lines. `awk 'length > 120'` prints nothing. Not committed.

## Minutes (start and end from `date`)
Start 04:52:30 CDT, end 04:56:24 CDT, 2026-09-29 (about 4 minutes).
