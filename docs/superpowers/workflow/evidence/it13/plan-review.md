## Verdict: BLOCKED

## Blocking findings (plan line, what is wrong, the evidence, the smallest fix)

**B1. The broken show.toml fallback lights the real wall brighter than the file asks (plan lines 118-120, 133-134, 140-141).**
- **What is wrong.** Today `config_from` falls back to the whole `Config()`, whose backend is `sdl` (`show/main.py:404-406`), so a broken file never reaches the LED wall on the Pi. The plan keeps the file's `backend`, `width`, `height` and `colorlight_iface`, which newly opens the colorlight wall on that path. It also says "never brightness, cap", so the wall runs at `Config().effective_brightness` = min(0.15, 0.40) = 0.15 (`show/config.py:20-21`).
- **Evidence.** Take a file with `brightness = 0.05` for a dark night, or `brightness_cap = 0.1` for a smaller supply, and a typo anywhere else. The wall then lights at 0.15: 3 times the asked level, and over the file's own cap. `make_display` starts colorlight at `effective_brightness` (`show/display/__init__.py:43-45`), and `_open_wall` sets it again (`show/main.py:172-177`). DDP ignores the level either way (`ddp.py:42-46`).
- **Which choice is safe.** "Never its brightness, cap" is the unsafe choice once the display keys are kept. The safe one is "the lower wins": never brighter than the file and never brighter than the default. This is a path to the display that skips the brightness the config asks for.
- **Smallest fix.**
  - Lines 118-119: "... (not bool); `brightness` and `brightness_cap`: the lower of the file's (a real number 0 to 1, not bool) and `Config()`'s; never gamma, fps."
  - Line 134, in the test: "`brightness = 0.9`: 0.15; `brightness = 0.05`, `brightness_cap = 0.1` beside `fps = 0`: 0.05 and 0.1".
  - Line 141 (README): "at the lower of the file's brightness and the default".

**B2. The pattern tool's AST safety test passes on code that reaches the display without the governor (plan lines 192-200).**
- **What is wrong.** The test inspects only `ast.Call` nodes whose func is an Attribute. Two bypasses slip through: `wall._send(frame)`, and an alias such as `send = display.push; send(frame)` (the idiom `show/wall.py:49` itself uses for `push`). Put either in one branch (say `steps`), with `wall.push` kept for the other patterns, and all three exact tests pass. `test_every_frame_...` drives only the `strobe` pattern. The it12 precedent already checks every Attribute node, not only calls (`tests/test_main.py:93-94`).
- **Evidence.** probe_ast.txt: the plan's AST passes on `wall._send` (True) and on the alias (True). The fixed form below passes on a governed `run` (True) and fails on all three bypasses. It also fails on today's file, as a new safety test must.
- **Smallest fix.** Replace lines 194-197 with the following (+1 line):
```python
    attrs = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute)]
    for name in ("push", "set_brightness", "close"):
        used = [n for n in attrs if n.attr == name]
        assert used and all(ast.unparse(n.value) == "wall" for n in used), name
    assert not [n for n in attrs if n.attr in ("_send", "display")]
```
- **Room.** B1 and B2 add about 3 lines. Cut the "Probe: the meter's maxima ..." sentence at lines 63-64 (it is in the writer's report) and the "Probe: rgb, index, ..." sentence at lines 167-168 to stay under 300.

## Notes (not blocking, one line each)
- **Q1, the close path.** It is sound in every case asked, and the it12 AST (one `.push(`, two `._send(`) stays satisfiable, because `close` calls `self.repush()` and the bound `push`.
  - Raise before any byte, or a torn push (a KeyboardInterrupt inside `display.push` included): `unsent` → repush N → governed black. That is the governor's own order.
  - Closed twice, or closed before any push: harmless.
- **SIGTERM between `apply` and `_send`.** `unsent` stays False and the counted N is skipped. Skipping a counted frame never adds transitions.
  - probe_interrupt_sweep: a KeyboardInterrupt midway through either `_Window.push` (count decremented, ring not written), strobes of periods 1 to 4, frames 25 to 44, then close: worst square_flashes 6, flash_area 0.0.
  - Optionally set `unsent = True` at `push`'s start, before `apply`.
- **Which raise `close` swallows.** Say it: the repush goes inside the `try` whose `finally` closes the display. An `Exception` is swallowed; a KeyboardInterrupt (a second Ctrl-C, or the sdl backend's QUIT at `sdl.py:24`) goes on to the `finally`. Say also that `unsent` starts False.
- **SDL swallows SIGTERM today (new fact).** `pygame.mixer.init()` in `AudioCues` (`show/audio.py:55`) installs SDL's handler.
  - A real `python -m show` was still running 20 s after SIGTERM, and a child with only the mixer was still running 4 s after (probe_sdl_sigterm). So today `systemctl stop` waits `TimeoutStopSec` (90 s), then SIGKILL.
  - The plan's Python handler wins whether it is installed before or after `mixer.init`: exit 0 in 0.06 s.
  - The it12 note (2) ("kills the loop outside its finally") understates this. `test_systemctl_stop_is_a_clean_exit` must keep the real `AudioCues` in the child (the `no_devices` fixture does not reach it) and kill the child in a `finally`: on BASE it hangs to the timeout.
- **The soak's own SIGTERM.** `show_soak.main` with real audio swallows SIGTERM the same way. Wrap it in `sigterm_raises()` too.
- **Logging from the handler.** `Sigterm`'s "logged" on a later signal writes to the log from a signal handler. That can raise `RuntimeError` (a reentrant call into the buffered stream) inside whatever `_close` is doing. Count it and log after the close.
- **The in-process SIGTERM test.** `test_sigterm_in_a_running_loop_...` should assert `isinstance(signal.getsignal(SIGTERM), Sigterm)` before `os.kill(os.getpid(), SIGTERM)`. With a broken handler, SIG_DFL kills the whole pytest run.
- **SIGTERM during setup or `_close`.** In setup, the KeyboardInterrupt passes `start`'s `except Exception` to `run`'s `finally`. A later SIGTERM during `_close` is ignored; the close then takes about `KILL_WAIT` of 1 s plus 3 pushes, far under 90 s.
  - Entries: on the Pi the cgroup kills them. By hand on the Mac, `_close`'s `abort` makes `terminal.kill` send `killpg` SIGKILL. A KeyboardInterrupt inside `terminal.run`'s Popen can orphan one child (a tiny window, and only by hand).
- **Q6, the fallback pace.** `FALLBACK_FPS` 20 is paced under the fallback governor's 30 (`show/main.py:163`), so the governor is stricter. The rule holds for a bad fps.
  - It does not hold at BASE for a refused gamma with `cfg.fps` over 30: the governor is at 30 and the pace is `cfg.fps`. Only the static error frame is shown, so no flash is possible.
  - One line fixes it: build the fallback `GovernedDisplay` with `fps=pace`.
- **Q3, the governor's fps in the pattern tool.** `max(2, ceil(fps))` is never laxer. `run` sleeps `1/fps` after every push, so the real rate is at most fps. At fps 1 the governor's 2-frame window spans 2 s; at 60 on a slow display, 60 frames span over 1 s. Both are stricter in seconds.
- **`steps` by the governor's own light measure.** LEVEL gives 0.502, and the four levels are 0.063, 0.125, 0.251 and 0.502. Only the 0.25-to-0.5 step and the wrap are transitions: 2 in an 8 s cycle (probe_steps: 5 in 24 s) against 6 a second. The plan's bound and test are enough.
- **`--config` and the cap.** `cap = min(CAP, brightness_cap)` cannot raise the level. Still, clamp inside `_refusal` as well (`brightness in (0, min(cap, CAP)]`), since `run(cap=...)` is public.
  - Refuse fps and gamma in `main` before `make_display`. Otherwise `run` returns 2 and leaves the display open. Nothing is sent: `ColorlightDisplay.__init__` sends nothing.
- **Q3, "under half the wall".** `grid` is 15/64 of the pixels at LEVEL: a mean of 0.1176 at 512x192 and at 128x64 (the writer measured 0.118). `panels` is 48 or 4 labels of 3 glyphs, a few % at most. Leaving `white` out (Q64) is right: the tool's own rule and the supply figures are the owner's.
- **Q2, the exact tests.** Every import exists: `FailingPushes`, `no_devices`, `playing_loop` in `test_main.py`; `FPS`, `H`, `W`, `strobe`, `Recorder` in `test_wall.py`; `BUDGET`, `flash_area`, `square_flashes`; `wp.PATTERNS`, `LOOK_FOR`, `LEVEL`, `rgb`.
  - `FailingPushes.calls` counts attempts. `count` and `pushed` count successes. The plan's arithmetic (33, 9, 7, 5, 101, 5) checks out.
  - Test 1 is not vacuous against a raw-black close: governed black after the strobe is held lit (mean 119), so a raw-black close fails it (probe_close). A close without the repush fails tests 1, 3 (`failed == 2`) and 4.
  - Importing the helpers collects no test twice.
- **The pattern test's clock.** `test_every_frame_...` needs today's loop, which reads `clock()` once a frame. The existing `tests/test_wall_pattern.py:122-137` pins that already. Keep the plan saying the loop is today's.
- **Q7, `FlashMeter`.** Build it from `wall.governor.fps` and `.gamma`, not from `cfg`.
  - The meter's tracker runs across report windows (`take` resets only the maxima), so no window alignment can fail a correct governor.
  - A reopened wall (a fresh governor whose first frame passes) or skipped failed frames can make the meter differ from the governor.
- **The soak's instrumentation cost.** The meter costs 4.3 ms a frame at 512x192 on the Mac (writer's number), probably about 10 times that on the Pi. Keep it out of `step_ms`, or the GATE C soak measures the meter along with the loop.
- **Pin the soak's wrappers.** In `test_a_strobing_entry_soaks_inside_the_budget`, assert on the Recorder's pushed frames (`flash_area == 0`, `square_flashes <= BUDGET`). Add: for one seed, the pushed frames are identical with and without the soak's wrappers.
- **The meter's coupling to `arcade/flash.py`.** C50's fix is in `arcade/config.py` (roadmap line 79), not in `flash.py`. Any later change to the private `_Transitions` or `_Window` is caught by `test_the_meter_agrees_with_flash_area_and_square_flashes`.
- **Must-be-zero counts on the Mac.** An empty station 1 to 5 logs no ERROR (Q62; only the cue and the flash), and hello's compile warning is output, not a log. Missing audio or cue files log at setup, which the plan counts as `errors_at_setup`. So a clean Mac run should report 0.
- **The overnight soak.** It runs the loop in process with the unit stopped, so the watchdog and `NRestarts` are not exercised by it. The README should say the unit is stopped for the soak.
- **Q9, time.** The plan's handler stop took 0.16 to 0.28 s in total (probe_stop), and importing `show.main` in a child takes 0.07 s, so T-main's 3 s share is believable.
  - T-shot's 2 s is not: a strobe session "as `:248`" is 3.4 s of real time alone. New tests are more likely about 13 s against the 10 s budget, and the suite about 244 s against 245. Shorten that session (for example 1.5 s) or expect a reported miss.
- **Q10, the it10 read-only frame.** Moot: `_send` pushes the wall's own writable copy, and no backend writes in place (`colorlight.py:121-133`, `ddp.py:48-53`, `sdl.py:21-29`).
- **Q10, pyte's feed time on the Pi.** It is not named anywhere. Say it is GATE C's, alongside Q59.
- **Q59's deadline.** It reads "D4 (the measure on the Pi)", and the plan moves the Pi number to GATE C. Write that into Q59 in `decisions.md`.
- **T-deploy's README check.** `test_readme_says_what_stop_and_the_watchdog_do` asserts "every second", which passes with "every few seconds" still at `deploy/README.md:18`. Also assert "every few seconds" is gone.
- **Q8, lanes.** No file has two owners, and the group 2 tasks correctly wait for T-wall.
  - T-soak may start before T-main merges. Its tests then see T-main's `_close` (`lights.tick(self.clock())`) only after the merge, so it needs a callable clock that never runs out.
  - I0's text applies as written. No other test file asserts on the strip's look or a lit strip (grep; the writer's probe: 143 passed, the 2 named failures).
  - No step edits a tracked file outside a task.

## Probes (file, what it shows, the numbers)
All files are under `scratchpad/it13-plan-review/`: patches in memory, no file in the repository edited, no child left (`pgrep`).
- **probe_close.py / .txt.** Test 1 of `test_wall_close`:
  - The plan's close passes.
  - A raw-black close through an alias fails (the governed black is held lit: means 119, 119, 119).
  - A close without the repush fails.
  - it12's clean-close test also fails a raw-black close.
  - A KeyboardInterrupt mid `_Window.push`, or after the pixels' `advance`, at frames 60 to 63, then close: square_flashes 6 (BUDGET 6), flash_area 0.0.
- **probe_interrupt_sweep.py / .txt.** The same interrupt in the pixel or the square window, strobe periods 1 to 4, frames 25 to 44: worst square_flashes 6, worst flash_area 0.0.
- **probe_ast.py / .txt.**

  | Variant | Plan's AST | Fixed AST |
  |---|---|---|
  | Safe governed `run` | True | True |
  | `wall._send` | True | False |
  | `send = display.push` | True | False |
  | `raw = wall.display` | False | False |
  | Today's file | – | False |

- **probe_sdl_sigterm.py / .txt.** Each case is a child sent SIGTERM:

  | Child | Result |
  |---|---|
  | No pygame | Exit -15, at once |
  | `mixer.init`, no handler | Still running 4 s after SIGTERM |
  | Real `AudioCues`, no handler | Still running 4 s after SIGTERM |
  | Handler before `mixer.init` | Exit 0 in 0.06 s |
  | Handler after `mixer.init` | Exit 0 in 0.06 s |

- **probe_stop.py / .txt.** A real `python -m show` (fake backend, hello):
  - Today's code: still running 20 s after SIGTERM (killed by the probe).
  - The plan's handler patched in: "the show runs" at 0.10 to 0.20 s, exit 0 0.06 to 0.08 s after SIGTERM, "closing" logged, 0.16 to 0.28 s in total.
- **probe_steps.py / .txt.** The `steps` walk through `_Transitions`: light of LEVEL 0.502, levels 0.063, 0.125, 0.251, 0.502; 5 transitions in 24 s.
- **Import timing.** `python -c "import show.main"`: `getsignal(SIGTERM) == SIG_DFL`, 0.07 s real.
- **Reused the writer's evidence:** probe_governed.txt (grid 0.118, governed patterns unchanged) and probe_look.txt (143 passed, 2 failed).

## Minutes (start and end from `date`)
Start 04:35:41 CDT, end 04:49:57 CDT, 2026-09-29 (about 14 minutes). No repository file changed. `docs/superpowers/workflow/decisions.md` shows as modified in `git status`; that edit is not mine. I broke the no-`cd` rule twice, both read-only: a grep prefixed with `cd /Users/trey/dev/codeisart` and a timing loop prefixed with `cd /tmp`. Nothing was written, and I reran both without `cd`.
