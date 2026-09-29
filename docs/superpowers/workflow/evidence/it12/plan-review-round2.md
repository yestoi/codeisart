## Verdict: BLOCKED

B1 to B5 are lifted (below). The fix itself opened two holes, B6 and B7. Both come from the new `_send` and fallback design, and each needs a line or two.

## Blocking findings (plan line, what is wrong, the evidence, the smallest fix)

**B6. Plan lines 131, 135-137, against the AST test at 216-218. A frame can reach the wall through `_send` without the governor.**
- What is wrong:
  - wall.py's single `.push` call now sits in `_send`, and `_send` has three callers (`push`, `repush`, `close`).
  - An ungoverned frame given to `_send` passes the test. Two examples: `close()` sending a raw black, or main.py calling `self.wall._send(frame)`.
  - main.py's check looks only at `.push` attributes.
- The evidence: probe_r2_ast.txt runs the plan's lines 207-220 as written.
  - "wall.close sends a raw black via _send": the plan's test passes.
  - "main.py calls self.wall._send(raw frame)": the plan's test passes.
  - The two asserts below reject both, and the good sample still passes.
- The smallest fix:
  - Add this rule at line 137: "`close` calls `self.push(black)` twice. `_send` is called only by `push` (apply's output) and `repush` (the last governed frame)."
  - Add these asserts after line 218:
```python
    assert "_send" not in (ROOT / "show" / "main.py").read_text()
    assert len([n for n in ast.walk(wall) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "_send"]) == 2               # push's (apply's output), repush's (the last governed)
```

**B7. Plan lines 129 and 155-156, against the AST assert at line 212. The fallback and the exact test contradict each other, so the implementers need a ruling.**
- What is wrong:
  - The fallback `GovernedDisplay(display, h, w)` needs the display that the first `GovernedDisplay(...)` raised on. So does "display closed" on line 156.
  - If `make_display` is written inline, as line 212 requires, the display is lost when the constructor raises.
  - If the display is kept in a local first, which is the natural code, line 212 fails.
  - Only a walrus inside the call satisfies both.
- The evidence (probe_r2_ast.txt):
  - The hoisted sample (the display kept in a local, then wrapped) fails the plan's test.
  - The inline sample passes, but it has no display to fall back on.
  - The walrus sample passes.
- The smallest fix, one line in Setup (line 155): "`self.wall = GovernedDisplay((raw := display if display is not None else make_display(cfg, on_key=...)), h, w, cfg.fps, cfg.gamma)`. The fallback and the close use `raw`. `GovernedDisplay.__init__` never closes the display it is given."

**The first round's findings, B1 to B5:**
- **B1, lifted.**
  - Lines 189 and 195: both feeds start with `\x1b[?25l`. Line 244: the strobe test renders with the cursor hidden. Lines 259-260: `STROBE_C` prints `\033[?25l` first.
  - The plan's lines 189-195, run through Terminal, Renderer (1 Hz blink) and the real governor: raw area 0.898, pushed 0.00000, square_flashes 6, held 35.
  - A `STROBE_C` written from T-shot's description, run in real time through the pump, 3 trials: pushed 0.00000, concurrent 0.0000, square_flashes 6, held 39 to 40.
- **B2, lifted.**
  - Lines 35-37: I0 checks `1.0 <= gamma <= 2.2`. Lines 42-43: the tests cover gamma 0.22 and 22.0.
  - Line 133: GovernedDisplay raises on the same bound. Line 167: the prose test checks that 0.22 and 22.0 raise.
- **B3, lifted for all the round-1 samples.**
  - Lines 213-218 now have the asserts. The alias, bound-method and wall `display.push` samples all fail the test now.
  - Lines 167-170 add the behavioural test `test_the_loop_s_own_display_is_governed`.
  - The new holes are B6 and B7.
- **B4, lifted.** Line 159: a render raise sends the last frame again and calls `show.abort(now)`. Line 247 renames the test to match. Lines 288-289 cover push failures.
- **B5, lifted.** Lines 280-282: the operator sets `strip_look` from the led and distance looks, as Q54's answer.

## Notes (not blocking, one line each)
- Q2: `FlashGovernor` stores `gamma` and `fps`, with defaults 2.2 and 30. `Config(gamma=-1.0)` builds after I0: the dataclass does not check the field, and today it raises TypeError.
- Q2: fps 30 on a 20 fps loop is stricter: 10 Hz strobe, pushed area 0.000, 6 square flashes. The test is not vacuous: it pins the fallback's parameters, a lit static frame, and count == governed.
- Line 234: add `not inner.closed`. A closed FakeDisplay still counts pushes, so the test cannot tell that the fallback reused a live display.
- Lines 155-156: the fallback at fps 30 is laxer only on a loop above 30 fps. It carries a static frame, so it is safe; one clause would say so.
- Line 37: I0 accepts fps 1, but FlashGovernor needs at least 2. Use `cfg.fps < 2` so a bad fps shows its config error rather than the governor's.
- Line 150: `config_from` falls back to `Config()`, whose backend is "sdl". The unit's ExecStart (line 118) passes no `--backend`, so on the Pi a bad show.toml leaves the wall dark (round-1 N3); the README should say so.
- Line 170: patching `show.wall.FlashGovernor` needs wall.py to import it by name (`from arcade.flash import FlashGovernor`).
- Line 137: `test_a_clean_close_pushes_two_governed_black_frames` would also prove B6 if, after `strobe(40)`, the two blacks must equal a reference governor's `apply(black)` twice.
- Q4: the typing bounds are not flaky: a fake clock, a fixed input, and `arcade/flash.py`, which I1 checks no task edits. My probe matches the writer's.
- Q4: headroom: 1600 cps at 0.065 against 0.08; ink at 0.102 against 0.15; flood at 0.012 against 0.02.
- Q4: the 400 cps bound of 0.03 sits over a probe of 0.000, so it is wide. That is acceptable for legibility; `held_ticks <= 5` there (probe 0) would pin it.
- Q5: no file is under two tasks; the plan is 298 lines, none over 120. Lines 56 and 157 agree that `lights.tick` belongs to the loop.

## Probes (file, what it shows, the numbers)
All under /private/tmp/claude-502/-Users-trey-dev-codeisart/d1e01db2-fed8-414f-9a38-325b95bc9c3a/scratchpad/, with each output beside its script as .txt.
- **it12-plan-review/probe_r2_strobe.py**
  - (a) The plan's FILL and StrobePlayer (lines 189-195), through Terminal, Renderer and the real FlashGovernor: raw area 0.898, pushed 0.00000, square_flashes 6, held 35.
  - FlashGovernor's defaults are gamma 2.2 and fps 30; Config has no gamma field before I0. The default governor on a real 20 fps loop with a 10 Hz strobe: area 0.000, square_flashes 6.
  - (b) A STROBE_C written from T-shot's description, in real time through the pump, 3 trials of 80 frames: raw 0.898, pushed 0.00000, concurrent 0.0000, square_flashes 6, held 39, 40, 40.
- **it12-plan-review/probe_r2_ast.py** runs the plan's lines 207-220 against sample trees.
  - Walrus main: passes. Inline main: passes. Hoisted main: fails (B7).
  - wall.close sending a raw black through `_send`: passes. main.py calling `self.wall._send`: passes (B6).
  - With B6's asserts, the good sample passes and both bypasses fail.
  - The round-1 samples (alias, bound method, wall `display.push`): all fail now.
- **it12-plan/probe_fixed_text.py** (the writer's), with my it12-plan-review/probe_legibility.txt: with `arcade/flash.py` as the text, 400 cps 0.000, 1600 cps 0.065, ink 400 cps 0.102.
