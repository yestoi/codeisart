## Verdict: BLOCKED

## Blocking findings (plan line, what is wrong, the evidence, the smallest fix)

B1. Lines 186-194 and 208 (and 259-260, 266, 281, which use the same input). The exact test `test_the_loop_holds_a_strobing_entry` cannot pass on the real, correct governor.
- What is wrong: the loop blinks the cursor at 1 Hz (`cursor_on = int(now * 2 * BLINK_HZ) % 2 == 0`). The feeds leave the cursor visible, so the cursor cell at (0, 0) flashes over budget. That is a Q13 small-area flash (one cell is 4.7 % of a 32x32 square, under SMALL_AREA 0.1). The governor passes such flashes by design, and `flash_area` counts them.
- The evidence: probe_loop_strobe.txt, with the exact inputs, Terminal and Renderer, strip notice and blink. Pushed `flash_area` is 0.00049: 48 px, rows 0-7, cols 16-21, cell (0, 0). `square_flashes` is 6 and `held_ticks` is 45. With the cursor steady on or off, the result is 0.00000. T-shot's `STROBE_C` (`test_strobe_session_is_held`, pushed `flash_area == 0.0`) and I2's "pushed flash_area 0.0" fail the same way unless the program hides the cursor.
- The smallest fix: both StrobePlayer feeds start with `\x1b[?25l`: `FILL = b"\x1b[?25l\x1b[H\x1b[7m" + ...` and `b"\x1b[?25l\x1b[H\x1b[2J"`. Add "`STROBE_C` prints `\033[?25l` first, as hello.c does" to T-shot. probe_loop_strobe_fix.txt confirms the fix: pushed area 0.00000, concurrent 0.0000, square_flashes 6.

B2. Lines 35-38 and 42 (I0), 136-137 (GovernedDisplay). The `gamma` key allows any value over 0 and finite. A config value can turn off the governor for the show's own content.
- The evidence: probe_safety.txt section 4. A full-screen 10 Hz strobe of normal text (35,178,35) against black is exactly the StrobePlayer's `FILL`.
  - With gamma 0.1 or 0.22, nothing is held: shown flash_area is 1.000 and square_flashes is 20. 0.22 is a one-character typo of 2.2.
  - A bold/normal strobe with gamma 22 or 1000: held 0, area 1.000, 20 square flashes.
  - With gamma from 0.5 to 5 everything is held (area 0.000, 6).
  - The physically meaningful values are 1.0 (the card applies gamma) and 2.2 (bytes as they are). For any pair of levels, a value between them is at least as strict as one of those two.
- The smallest fix:
  - I0's check becomes `... or not 1.0 <= cfg.gamma <= 2.2: raise ValueError(f"{path}: gamma must be 1.0 (the card applies gamma) to 2.2 (bytes as they are)")`.
  - `test_strip_look_and_gamma_are_checked` adds `0.22` and `22.0` among the values that raise, and `1.0` among those that load.
  - GovernedDisplay's comment becomes: "raises ValueError unless 1.0 <= gamma <= 2.2 (a Config built in code skips load_config), else what FlashGovernor raises".
  - Change the show.toml comment to match.

B3. Lines 132-133 and 210-218. `test_every_display_is_wrapped_by_the_governor_at_birth` passes on code that makes or pushes frames outside the governor. Also, the production path (`display=None`, where ShowLoop calls `make_display` itself) has no behavioral safety test: every safety test passes `display=inner`.
- The evidence: probe_ast.txt runs the plan's test on sample sources. It passes (True) on:
  - (a) `from show.display import make_display as md` and a raw display made through `md`;
  - (b) `p = self.raw.push; p(frame)`;
  - (c) a wall.py whose `close()` pushes a black frame with `self.display.push`. The test reads only main.py.
  - The asserts below reject all three and still pass the good sample.
- The smallest fix, exact lines in that test:
```python
    tree = ast.parse((ROOT / "show" / "main.py").read_text())
    pushes = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr == "push"]
    assert pushes and all(ast.unparse(n.value) == "self.wall" for n in pushes)
    assert not [a for a in ast.walk(tree) if isinstance(a, ast.alias) and a.name == "make_display" and a.asname]
    wall = ast.parse((ROOT / "show" / "wall.py").read_text())
    assert len([n for n in ast.walk(wall) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "push"]) == 1                  # GovernedDisplay.push's own, after apply
    for path in [*(ROOT / "show").glob("*.py"), ROOT / "tools" / "show_shot.py"]:
```
  Add one test in prose: `test_the_loop_s_own_display_is_governed(tmp_path, monkeypatch)`.
  - `monkeypatch.setattr("show.display.fake.FakeDisplay", Made)`, where `Made(Recorder)` appends itself to a list in `__init__`. `make_display` imports FakeDisplay when called, so the patch takes effect.
  - Build `ShowLoop(loop_cfg(tmp_path), player_factory=StrobePlayer, notify=lambda s: None)` with no display, then run the strobe steps of the loop test.
  - Assert: one `Made`, with `count == loop.wall.governed == 100`, `flash_area(pushed, fps=20) == 0.0` and `square_flashes(pushed, fps=20) <= BUDGET`.

B4. Lines 158-159 go against spec 4.6: "Any exception in press handling, tick, render or push is logged and the show returns to attract".
- What is wrong: a render that raises only re-pushes the last frame. A raise that repeats (one caused by the entry's screen or strip) then freezes the wall for as long as the entry plays, while the watchdog is still petted.
- The smallest fix:
  - Step: "(a raise: the last frame again and `show.abort(now)` in its own `try`)".
  - Add a line to Decisions: "a push failure does not abort: the amendment's lights rule (10 s, all off, relight) is how spec 4.6 applies to push".
  - `test_a_render_that_raises_repushes_the_last_frame` also asserts that the show is back in attract.

B5. Lines 34 and 280-283 go against the owner's Q54 answer (decisions.md:415): "until then the loop takes the one that reads best in the sheets".
- What is wrong: the plan keeps "reverse" and says "the owner picks". The it10 sheets showed reverse reads worst.
- The smallest fix: add to I2: "Then the operator sets `strip_look` in show.toml to the look that reads best at the led and distance looks. It is a commit of its own, and Q54 names the pick. Config's default stays `reverse`."

To stay under 300 lines, the writer can join short lines of the exact code. The plan already allows reformatting.

## Notes (not blocking, one line each)
- N1 Brightness on DDP, the spec's primary path: nothing in software applies `brightness` or `brightness_cap`. `DDPDisplay.set_brightness` only logs at info (show/display/ddp.py:42-46). The wall runs at Falcon Player's setting. The README should say "set Falcon Player's output brightness to show.toml's brightness, never over brightness_cap 0.40", and ShowLoop should log a WARNING with the level on the ddp backend. Colorlight applies it on the card (make_display starts at effective_brightness). SDL is a monitor preview.
- N2 Governor cannot be built, wall dark. Safety rightly wins over spec 1's "never blank", but the conflict can be avoided:
  - A fallback `FlashGovernor(h, w)` with the module defaults (gamma 2.2, fps 30; stricter at 20 fps) could carry the static error frame. The wall would then show the cause, meeting both Q50 and spec 4.6.
  - As planned, the owner learns only from the journal, and the unit stays "active".
  - The rings stay lit over a dark wall: `wall is None` should count as push failure for the 10 s lights-off rule.
- N3 The plan does not say what happens when `load_config` raises (bad show.toml, a bad strip_look or gamma after I0). `main` returns 2 only for `--play`, so the implementer must choose a cfg. Rule on it. The Config() default backend is "sdl", which leaves the wall dark on the Pi. `fps` is not validated: `fps = 20.0` gives a governor that cannot be built, so the wall is dark.
- N4 "A failed push adds no transition" (lines 163-164) holds only for all-or-nothing failures. A torn Colorlight push, where some rows are sent before the raise, or rows silently dropped by the NIC, is a frame the governor never saw. Probe: on a 10 Hz strobe with 30 % torn pushes, the wall showed square_flashes 7 against 6 and flash_area 0.135. With whole failures it stayed at 0.0 and 6. Suggest: after a failed push, the next step re-pushes the last governed frame, with no new `apply`, before a new frame.
- N5 The governor's `fps` above the loop's real rate is stricter (probe: 40 at 20, 6). Below the real rate it is laxer (probe: 10 at 20 gives 12 square flashes a second, area 1.0). Pin that `run` never steps faster than cfg.fps (no catch-up after a stall), and that T-shot's sessions do the same.
- N6 The typing bounds depend on which text is typed, and the plan names none. `show/pipeline.py` (the writer's probe) is edited by T-term. `arcade/flash.py` at 1600 cps gives 0.065 in the text view (bound 0.06) and 0.29 in ink. Name a fixed text and re-probe it (probe_legibility.txt).
- N7 `test_strobes_over_3_hz_are_held_and_under_are_not` must render with the cursor hidden or steady, for the reason in B1. The 60-frame strobe probes match the plan: 10, 5 and 3.3 Hz governed to area 0.0 and square_flashes 6; 2.5 Hz is held 0, in both views.
- N8 Every "0" bound checks out exactly: hello's band and the blink with strip alternation give held_ticks 0 and max share 0.0 in both views (probe_legibility.txt).
- N9 About `set_entries` on the rescan every 30 s:
  - If it rebuilds and restarts Attract when nothing changed, `Attract.idle_seconds` resets and the 5-minute autoplay never fires in the real loop.
  - Say "unchanged entries change nothing; a rebuild keeps the idle clock".
  - Compare queued entries by station or slug: `Entry` is a frozen dataclass, and a captured `fallback.cast` changes its value.
- N10 `Show.tick` calls `lights.tick` (core plan line 2418). A GpioLights write that raises would abort to attract on every frame. Guard lights apart from the show. Presses also relight rings while the wall is dark after `all_off`.
- N11 `FakeLights` has no `close()`: `run`'s `finally` must guard `lights.close` or check for it, or `--play` ends in an AttributeError.
- N12 Setup should name `AudioCues(cfg.audio_dir, cfg.volume, cfg.quiet_hours)` (amendment Task 13). No test checks that quiet hours or volume reach it.
- N13 State the player protocol `Show` may use: `done`, `crowd`, `start(now, crowd)`, `tick(now)`, `stop()`. StrobePlayer and FakePlayer have no `phase` or `failure`.
- N14 In deploy, lgpio (the `pi` extra) writes its notification files into the working directory. That directory is read-only under `ProtectSystem=strict`, which likely leaves the buttons unavailable. Add `Environment=LG_WD=/tmp` (PrivateTmp). Medium confidence: check on the Pi.
- N15 In deploy, Raspberry Pi OS Bookworm has no default `pi` user. The README should say to edit `User=` and the paths.
- N16 In deploy, `AmbientCapabilities=CAP_NET_RAW` is inherited by gcc and every entry; `unshare -rn` isolates only the run's network. It is needed only for the colorlight backend, not the DDP primary path.
- N17 In deploy, the README list leaves out the "LEDVision settings record" (amendment Task 14, spec 3.2).
- N18 In deploy, no SIGTERM handler means `run`'s `finally` does not run on `systemctl stop`. The default `KillMode=control-group` still kills entries in their own sessions: keep it, and never set `KillMode=process`.
- N19 In deploy, `WatchdogSec=15` is fine. Startup compiles nothing. Under `Type=notify` the watchdog starts after READY=1, and the longest in-step block is `Terminal.kill`'s 1 s.
- N20 A clean exit (Ctrl-C, the end of `--play`) leaves the card showing the last frame, lit. Consider two governed black pushes on close, as tools/wall_pattern.py does.
- N21 `tools/wall_pattern.py:214` makes and pushes displays ungoverned. Its patterns are static, and `steps` changes brightness every 2 s. It is a bench tool outside the show. D4's show test pattern should go through `GovernedDisplay`.
- N22 The same unbounded `gamma` is in arcade/config.py:101-105 and arcade.toml. Carry B2's bound to the arcade as its own safety slice.
- N23 Line 3 says the implementers' BASE is "I0's commit on 0dae849", but HEAD is 03c9555 (the plan's commit). I1's `git diff 0dae849` still works.
- N24 T-main's 10 s is tight. The governor takes 4-6 ms a 512x192 frame, and the legibility tests alone are about 1,000 frames, plus render.
- N25 Lanes check out: no file is under two tasks. T-state needs only its own `strip_chars` and `Attract`, T-strip needs only I0, and T-main and T-shot wait for their groups. The merge order is safe. I0's text can be applied as written, apart from B2.
- N26 Q60 and legibility check out: typing in the text view is held on at most 2-5 % of pixels for a frame. Crowd mode (1600 cps) is 4.7 % with the writer's text. The ink view at 15-22 % is the accepted Q60 cost.

## Probes (file, what it shows, the numbers)
Folder: /private/tmp/claude-502/-Users-trey-dev-codeisart/d1e01db2-fed8-414f-9a38-325b95bc9c3a/scratchpad/it12-plan-review/. Each script has its output beside it as .txt.
- probe_safety.py, the plan's exact inputs against the real governor:
  - The 10 Hz strobe test: raw area 1.000, pushed 0.0000, square_flashes 6, held 35. A do-nothing governor gives 1.000 and 20, so the test is not vacuous.
  - StrobePlayer through the real Terminal and Renderer: raw 0.898, pushed 0.0005 (see B1), strip row lit in every frame.
  - Strobes at 10, 5, 3.3 and 2.5 Hz: as in N7.
  - The gamma sweep: as in B2.
  - Failed and torn pushes: as in N4.
  - Governor fps against the real rate: as in N5.
- probe_loop_strobe.py: the failing 48 px are the cursor cell (0, 0) with the 1 Hz blink. With the cursor steady off or on, the result is 0.00000.
- probe_loop_strobe_fix.py: with `ESC[?25l` first, pushed area is 0.00000, concurrent 0.0000 and square_flashes 6. Unfixed, concurrent is 0.0469, under SMALL_AREA.
- probe_ast.py: the plan's AST test passes on three ungoverned samples (an alias, a bound method, a wall.py `close()` pushing black). B3's asserts reject all three and pass the good sample.
- probe_legibility.py:
  - hello's band and the cursor with strip alternation: held 0 and max share 0.0 in both views.
  - Typing max share by text, text view at 400 and 1600 cps: pipeline.py 0.021 and 0.047; flash.py 0.000 and 0.065; terminal.py 0.000 and 0.037; hello.c 0.000 and 0.000.
  - The ink view at 400 cps: 0.149, 0.102, 0.034 and 0.043 for the same texts.
