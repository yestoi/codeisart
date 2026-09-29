# Iteration 13: the test pattern and the soak (D4)
BASE: HEAD at the spawn. Roadmap D4 (Q50, Q54, Q59; notes it10, it12 1-9, it12 plan review). Thin plan. SAFETY SLICE.
Implementers' BASE: I0's commit (code head at the plan: 245cb57). "Core plan" = `docs/superpowers/plans/2026-09-22-
show-daemon.md`: Amendments (line 65) over Task 18 (3457 to 3624) and the week 5 soak (3686); spec 4.1 to 4.7 (205
to 290) over both. NOT edited: `arcade/flash.py`, `arcade/brightness.py`, `show/display/colorlight.py`.

## Global Constraints
- Test command, from the root: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/
  python -m pytest -q -rs`. At 245cb57: 1064 collected, 1 skip (`tests/test_sandbox.py:153`), 231 s. A worktree's
  second skip, `tests/arcade/test_pose_mediapipe.py:223` (model not in git), is expected. Suite limit 245 s. New
  tests 10 s at most (`--durations=0`): T-wall 1, T-main 2.5, T-pattern 1, T-shot 3, T-soak 2, T-deploy 0.2.
- Test-first; only your files; never `cd` (absolute paths, `git -C`); `git add` by name; no stash, push or command
  over 10 min; `tmp_path`; children killed, `pgrep -P` reported; `skipif(shutil.which("cc") is None)`; no window,
  sound or GPIO (fakes). Nothing installed, enabled or deployed. No rulings: a gap is reported. Editing `entries/`:
  commit before the suite (`tests/test_show_shot.py:153`). Trailer `Co-Authored-By: Claude Fable 5.1
  <noreply@anthropic.com>`.
- No existing assert is removed or weakened, save `tests/test_config.py:20` (I0, Q54). A missed bound is reported,
  never loosened. `tests/test_wall.py`, `tests/test_main.py`, `tests/test_wall_pattern.py` are NOT edited.
- EXACT safety tests (Loop rule 4): reformat only, no assert changed. They pass on the writer's in-memory patches.

## Lanes
- I0 (orchestrator, main checkout, first): the strip's default below, the suite, one commit: BASE.
- GROUP 1, one message, `isolation: "worktree"`: T-wall (opus), T-main (opus), T-deploy (sonnet).
- GROUP 2, from the HEAD with T-wall merged (T-main, T-deploy may still run; four tasks at most at once): T-pattern
  (opus) and T-shot (sonnet); T-soak (sonnet) from the HEAD with T-main merged too (it uses `sigterm_raises()`).
- Merge order: T-wall, T-deploy, T-main, T-pattern, T-shot, T-soak. After each merge its test files and
  `tests/test_wall.py tests/test_main.py tests/test_config.py`; the full suite after T-wall (group 2's base) and last.
- Owners: I0 `show/config.py`, `show.toml`, `tests/test_config.py`. T-wall `show/wall.py`, `tools/flash_meter.py`,
  `tests/test_wall_close.py`, `tests/test_flash_meter.py`. T-main `show/main.py`, `tests/test_main_stop.py`. T-deploy
  `deploy/README.md`, `tests/test_deploy.py`. T-pattern `tools/wall_pattern.py`, `tests/test_wall_pattern_governed.
  py`. T-shot `tools/show_shot.py`, `tests/test_show_shot_pages.py`. T-soak `tools/show_soak.py`, `tests/test_show_
  soak.py`. Nobody: `show.poc.toml`, `deploy/show.service`, `show/renderer.py`.

## I0 (orchestrator): the strip's default look (Q54, the loop's reading), test first
1. `tests/test_config.py:20` becomes `    assert cfg.strip_look == "bright-on-field" and cfg.gamma == 2.2`; at the
   end: `def test_the_default_strip_look_is_the_loop_s_reading_everywhere():` / `assert Config().strip_look ==
   "bright-on-field"` / `for name in ("show.toml", "show.poc.toml"): assert load_config(ROOT / name).strip_look ==
   "bright-on-field", name`. Run `tests/test_config.py`: `:20` and the new test fail.
2. `show/config.py:28`: `    strip_look: str = "bright-on-field"   # the strip's look (Q54, the loop's reading)`.
   `show.toml:7`: `strip_look = "bright-on-field"   # reverse | dim-reverse | bright-on-field (Q54)`. `show.poc.toml`
   sets no `strip_look` and follows `Config`: unchanged. `show/renderer.py:29` keeps `reverse`. `tests/test_config.
   py` green, then the suite. Commit `chore(show): bright-on-field is the strip's default (Q54; it13 I0)`.

## T-wall (opus): the close path after a failed push (note it12 3), and a flash meter
```
class GovernedDisplay:   # show/wall.py; still ONE `.push(` call (in _send) and TWO `._send(` calls (push, repush)
    unsent: bool         # False at first; True from _send's start until display.push returns (a raise mid-send)
    failed: int          # sends that raised an Exception, all told (the soak's push failures)
    last: np.ndarray | None   # property: the last governed frame as a read-only view; None before any push
    def close(self) -> None   # in the try whose finally closes the display: when unsent, self.repush() first (an
        # Exception there is swallowed, black still goes; a KeyboardInterrupt goes on to the finally); then the two
        # governed black frames through the bound `push`, as now
class FlashMeter:        # tools/flash_meter.py: arcade.flash's counting a frame at a time (read-only use of signals,
                         # square_means, _Transitions, _Window, THRESHOLD, BUDGET, WINDOW)
    def __init__(self, fps: int, gamma=2.2, threshold=THRESHOLD, budget=BUDGET, window=WINDOW)
    frames: int; area_max: float; squares_max: int         # over every frame added
    def add(self, frame) -> tuple[float, int]   # this frame's flash area and square flashes (the first: 0.0, 0)
    def take(self) -> tuple[float, int]         # the maxima of add since the last take, then reset
```
A clean close is today's (`tests/test_main.py:406-416`, 42 pushes); the loop's repush (`show/main.py:270-271`) stays
and, once it succeeds, close adds nothing.
Safety tests, EXACT, `tests/test_wall_close.py` (docstring: "the plan's, as given"):
```python
# imports: numpy as np, pytest; FlashGovernor (arcade.flash); GovernedDisplay (show.wall); FailingPushes,
# no_devices (the autouse fixture, imported for it), playing_loop (tests.test_main); FPS, H, W, strobe (tests.test_wall)
LIT = np.full((H, W, 3), (51, 255, 51), np.uint8)
def test_close_after_a_failed_push_sends_the_counted_frame_before_black():
    inner, reference = FailingPushes({31}), FlashGovernor(H, W, 2.2, fps=FPS)
    wall, frames = GovernedDisplay(inner, H, W, fps=FPS), strobe(31)
    for f in frames[:30]: wall.push(f); reference.apply(f)
    with pytest.raises(OSError): wall.push(frames[30])           # governed and counted, never shown
    assert wall.unsent and wall.failed == 1 and wall.governed == 30
    black = np.zeros((H, W, 3), np.uint8)
    want = [reference.apply(frames[30]).copy(), reference.apply(black).copy(), reference.apply(black).copy()]
    wall.close()
    assert inner.count == 33 and inner.closed and not wall.unsent
    assert all(np.array_equal(got, w) for got, w in zip(inner.pushed[-3:], want))
def test_close_after_a_mended_failure_is_the_clean_close():
    inner = FailingPushes({6}); wall = GovernedDisplay(inner, H, W, fps=FPS)
    for _ in range(5): wall.push(LIT)
    with pytest.raises(OSError): wall.push(LIT)                  # call 6
    wall.repush(); wall.push(LIT)                                 # calls 7 and 8: the loop's next step mends it
    assert not wall.unsent and wall.failed == 1
    wall.close()                                                  # calls 9 and 10: black, nothing sent again
    assert inner.count == 9 and inner.closed
    assert not inner.pushed[-1].any() and not inner.pushed[-2].any() and inner.pushed[-3].any()
def test_close_when_the_repush_fails_still_darkens_and_closes():
    inner = FailingPushes({6, 7}); wall = GovernedDisplay(inner, H, W, fps=FPS)
    for _ in range(5): wall.push(LIT)
    with pytest.raises(OSError): wall.push(LIT)                  # call 6
    wall.close()                                                  # call 7, the repush, fails; 8 and 9 black
    assert inner.closed and inner.count == 7 and wall.failed == 2
    assert not inner.pushed[-1].any() and not inner.pushed[-2].any()
def test_the_loop_s_close_after_a_failed_push_sends_the_counted_frame_first(tmp_path):
    inner = FailingPushes({3}); loop = playing_loop(tmp_path, inner)         # call 1
    loop.step(0.10); loop.step(0.15)                              # call 2; call 3 fails: its frame was governed
    counted = loop.wall.last.copy()
    loop._close()                                                 # calls 4 (the counted frame), 5 and 6 (black)
    assert inner.count == 5 and inner.closed and np.array_equal(inner.pushed[2], counted)
```
Also `test_last_is_the_governed_frame_and_read_only` (None first; the last push; writing raises `ValueError`).
`tests/test_flash_meter.py`: `test_the_meter_agrees_with_flash_area_and_square_flashes` (strobe periods 1, 2, 3, 20
noise frames, both sizes); `test_take_gives_the_maxima_since_the_last_take`; `test_governed_frames_meter_inside_
the_budget` (`strobe(100)` governed: `squares_max <= BUDGET`, `area_max == 0.0`).

## T-main (opus): systemctl stop, the fallback's display, lights.tick, fps (notes it12 2, 4, 6, 7)
```
FALLBACK_FPS = 20          # show/main.py: run's pace when cfg.fps is not an int of at least 2 (Config's default)
DISPLAY_KEYS = ("backend", "width", "height", "colorlight_iface", "ddp_host", "ddp_port")
class Sigterm:             # SIGTERM's handler: KeyboardInterrupt the first time; later ones only counted (it never
    seen: int; def __call__(self, signum: int, frame) -> None   # logs itself); main logs the count after the close
@contextmanager
def sigterm_raises() -> Iterator[None]   # installs Sigterm(), restores the previous handler on exit; outside the
                                         # main thread (ValueError): a warning, nothing installed
def config_from(args) -> tuple[Config, str | None]   # load_config raises: Config() plus each DISPLAY_KEYS value of
    # the file when it parses as TOML and the value has the default's type (not bool); `brightness` and
    # `brightness_cap`: each the lower of the file's (a real number 0 to 1, not bool) and Config()'s; a value not
    # such a number: Config()'s, the only level then known; never gamma, fps. Then --backend, --capture, as now.
def main(argv=None) -> int   # `with sigterm_raises(): return ShowLoop(cfg, config_error=error).run(play=args.play)`
```
- Nothing at import. `_close` logs INFO `closing: the wall goes black, the lights off`; after the buttons,
  `lights.all_off()` then `lights.tick(self.clock())` in one guarded `try`, before `lights.close` (if any), then the
  wall. `run`: `pace = cfg.fps` when an int of at least 2 (not bool), else `FALLBACK_FPS` and an ERROR log; the
  wall's refusal names that fps on the static frame (`show/main.py:158-171`); after `start`, INFO `the show runs at
  <pace> fps`. The fallback governor keeps fps 30 (`tests/test_main.py:126` pins it; a static frame only).
Tests, `tests/test_main_stop.py` (helpers, autouse `no_devices` from `tests.test_main`): `test_sigterm_raises_once_
then_is_ignored`; `test_sigterm_in_a_running_loop_darkens_the_wall_and_the_lights` (the third fake step asserts
`isinstance(signal.getsignal(SIGTERM), Sigterm)`, then `os.kill(os.getpid(), SIGTERM)`: 0; the last two frames a
reference governor's two `apply(black)`; lights `"off"`; old handler back); `test_importing_show_main_installs_no_
handler` (child: `SIG_DFL`); `test_systemctl_stop_is_a_clean_exit` (child `python -m show --backend fake` under
`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy`, real `AudioCues` kept (SDL's mixer swallows SIGTERM on BASE): exit 0
in 10 s, `closing` logged; child killed in a `finally`); `test_a_broken_show_toml_keeps_its_display_keys` (colorlight,
`enp3s0`, 128x64 kept beside `fps = 0`: fps 20; brightness `0.9`: 0.15; brightness `0.05` with `brightness_cap =
0.1`: 0.05, 0.1; brightness `true` or `"dim"`: 0.15; not TOML: `Config()`; `backend = 3`: sdl);
`test_lights_tick_on_every_step` (40 steps, no show, a failing push, a raising `show.tick`: 40 ticks in order);
`test_an_fps_the_governor_refuses_never_divides_by_zero` (fps `0`, `-1`, `1`, `2.5`, `True`: 5 steps, 0, gaps `>= 1 /
FALLBACK_FPS`, fps in `errors`).

## T-deploy (sonnet, group 1): the notes (notes it12 4, 5, 8)
`deploy/README.md`: `WATCHDOG=1` every second, not "every few seconds"; `systemctl stop` sends SIGTERM: two governed
black frames, lights off, entries die with the cgroup (default `KillMode`); a broken show.toml: the error frame on
the file's own display at the lower of the file's brightness and the default (not TOML: `sdl`, read `journalctl -u
show`); no carrier: the start waits for wait-online's timeout, then runs (Q63); the overnight and GATE C soaks, with
the unit stopped (`--minutes 600 --press-every 180 --real-devices`), `systemctl show show -p NRestarts` (0), a
`vcgencmd measure_temp` loop; `wall_pattern.py --config show.toml`. `tests/test_deploy.py` adds `test_readme_says_
what_stop_and_the_watchdog_do` ("every second", "SIGTERM", "black", "network-online", "NRestarts"; "every few
seconds" gone) and `test_readme_names_the_soak_and_the_pattern_tool` (those two commands).

## T-pattern (opus, group 2): the test pattern through the governor (Task 18; it12 plan review N21)
```
MAX_FPS = 60.0                               # tools/wall_pattern.py
def governor_fps(fps: float) -> int          # max(2, ceil(fps)): the governor's window never under a real second
def grid(width, height, t) -> np.ndarray     # LEVEL white lines every 8 px, rows and columns (alignment, tearing)
def panels(width, height, t) -> np.ndarray   # each 64x32 panel's "r,c", LEVEL white, draw_text at (x + 2, y + 2)
PATTERNS, LOOK_FOR gain "grid" and "panels"; no "white" (Q64)
def _refusal(pattern, brightness, cap: float = CAP) -> str | None   # brightness in (0, min(cap, CAP)]
def run(pattern, display, width, height, brightness=0.1, seconds=0.0, fps=20.0, clock=time.monotonic,
        sleep=time.sleep, out=print, gamma: float = 2.2, cap: float = CAP) -> int
    # 2, display untouched: _refusal; fps not finite in (0, MAX_FPS]; gamma not in [GAMMA_MIN, GAMMA_MAX]
    # (show.wall). Then wall = GovernedDisplay(display, height, width, governor_fps(fps), gamma), and only
    # wall.set_brightness, wall.push, wall.close; an OSError from a push: a message, 1 after the finally's wall.close()
main: --config PATH: backend, width, height, colorlight_iface (as iface), ddp_host, ddp_port, gamma and cap =
    min(CAP, brightness_cap) from load_config; a flag on the line wins; --png takes the config's size; a backend the
    tool has no choice for (fake): a message, 2. Without --config: today's defaults, exactly. Every refusal
    (brightness, fps, gamma) comes before make_display; main never touches the display, run does, through wall.
```
`steps` sets the device brightness the governor does not see: bounded by `STEP_SECONDS` 2.0 (0.5 changes a second
against 3 flashes) and `level <= brightness <= cap <= CAP`; pinned below. `tests/test_wall_pattern.py:46-51` covers
`grid`, `panels`. `run`'s loop reads `clock()` once a frame, as today (`tests/test_wall_pattern.py:122-137`).
Safety tests, EXACT, `tests/test_wall_pattern_governed.py` (docstring: "the plan's, as given"):
```python
# imports: ast, Path, numpy as np; BUDGET, flash_area, square_flashes (arcade.flash); FailingPushes
# (tests.test_main); Recorder (tests.test_wall); wall_pattern as wp (tools); ROOT = Path(__file__).resolve().parents[1]
def strobe(width, height, t):                        # the whole wall lit and black by turns: 10 Hz at 20 fps
    lit = round(t * 20) % 2 == 0
    return np.full((height, width, 3), (0, wp.LEVEL, 0) if lit else (0, 0, 0), np.uint8)
def test_every_frame_the_pattern_tool_sends_is_governed(monkeypatch):
    monkeypatch.setitem(wp.PATTERNS, "strobe", strobe)
    monkeypatch.setitem(wp.LOOK_FOR, "strobe", "a strobe the governor holds")
    inner, clock = Recorder(), iter(np.arange(0.0, 100.0, 0.05))
    assert wp.run("strobe", inner, 128, 64, brightness=0.1, seconds=5.0, fps=20, clock=lambda: next(clock),
                  sleep=lambda s: None, out=[].append) == 0
    raw = [strobe(128, 64, k * 0.05) for k in range(1, len(inner.pushed) - 1)]
    assert len(inner.pushed) == 99 + 2 and flash_area(raw, fps=20) > 0.5
    assert flash_area(inner.pushed, fps=20) == 0.0 and square_flashes(inner.pushed, fps=20) <= BUDGET
    assert inner.closed
def test_a_failed_push_ends_with_the_counted_frame_then_governed_black():
    inner, clock = FailingPushes({3}), iter(np.arange(0.0, 100.0, 0.05))
    assert wp.run("rgb", inner, 128, 64, brightness=0.1, seconds=5.0, fps=20, clock=lambda: next(clock),
                  sleep=lambda s: None, out=[].append) == 1
    assert inner.closed and inner.count == 5 and np.array_equal(inner.pushed[2], wp.rgb(128, 64, 0.0))
    assert not inner.pushed[-1].any() and not inner.pushed[-2].any()
def test_the_pattern_tool_reaches_the_display_only_through_the_governor():
    tree = ast.parse((ROOT / "tools" / "wall_pattern.py").read_text())
    attrs = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute)]  # every use, not only calls (no aliases)
    for name in ("push", "set_brightness", "close"):
        used = [n for n in attrs if n.attr == name]
        assert used and all(ast.unparse(n.value) == "wall" for n in used), name
    assert not [n for n in attrs if n.attr in ("_send", "display")]
    wraps = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == "GovernedDisplay"]
    assert len(wraps) == 1 and ast.unparse(wraps[0].args[0]) == "display"
```
Also: `test_the_governor_fps_is_never_under_the_push_rate` (1, 2.0, 7.5, 20.0 to 2, 2, 8, 20); `test_run_refuses_a_
bad_fps_or_gamma_without_touching_the_display` (fps 0, -1, nan, inf, 61; gamma 0.22, 22.0); `test_steps_changes_the_
device_brightness_at_most_every_2_s`; `test_grid_lines_every_8_pixels`; `test_panels_labels_every_panel` (48, 4);
`test_config_sets_the_wall_and_a_flag_wins` (ddp, 512x192, gamma 1.0, cap 0.3; `--width 128` wins; `--brightness
0.35`: 2); `test_png_takes_the_config_size`; `test_main_refuses_before_making_the_display` (fps 0, gamma 22.0: 2).

## T-shot (sonnet, group 2): the operator's sheets (note it12 9)
```
PAGE_MAX_H = 4000                     # tools/show_shot.py: a written page is at most this tall, px
COLS_MAX_WIDTH = 4 * SHOW_MAX_WIDTH   # an explicit --cols is honoured up to this width (8320 px)
def pages(frames, look, scale, title, gamma, cols, cap=SHOW_MAX_WIDTH, max_height=PAGE_MAX_H) -> list[Image.Image]
    # sheet()'s cells in pages of whole rows (one row at least), each titled "<title> page <k>/<n>"
def frames_from_session(name, cfg, seconds=SESSION_SECONDS, every_ms=500, presses=None, meter=None)  # same 3-tuple
    # a FlashMeter(wall.governor.fps, .gamma) (made when None) gets every pushed frame (display.last after a step whose
    # display.count grew: AFTER the governor, as now); labels gain " area <a:.4f> sq <s>", take() since the last cell
```
- `--cols` default None: today's (2, fitted to `SHOW_MAX_WIDTH`); given: honoured up to `COLS_MAX_WIDTH`, else exit
  2 naming the columns that fit at that `--scale`, nothing written. One page keeps today's names; more add `-p<k>`
  before `.png`. `--session` prints `held <n> area <a> squares <s>` for the whole session.
- Tests, `tests/test_show_shot_pages.py`: `test_pages_keep_every_cell_under_the_height` (30 synthetic 512x192 frames,
  scale 4, cols 1: each page `<= PAGE_MAX_H`, all 30 in order); `test_a_long_command_writes_numbered_pages`
  (`--command "seq 1 50" --seconds 0.5 --every-ms 50 --look plain`: `out-p1.png`.., `out-distance-p1.png`..);
  `test_cols_is_honoured_or_refused` (`--cols 3 --scale 1`: 3 columns; `--cols 6 --scale 4`: 2, no file);
  `test_the_strobe_session_labels_its_flash_numbers` (skipif no cc; as `tests/test_show_shot.py:248` but
  `seconds=1.5`: `area` and `sq` on every label, `squares_max <= BUDGET`).

## T-soak (sonnet, group 2): the soak (spec 4.7, line 290; core line 3686)
```
PRESS_EVERY_S = 180.0   # tools/show_soak.py: the core plan's week 5, a press every 3 minutes
WINDOW_S = 60.0         # a report row this often: frames, meter maxima, held, fds, rss
STATIONS = (1, 2, 3, 4, 5, 6)   # 1 to 5 may be empty (Q62); 6 is hello; the rng repeats some (review focus 3)
def soak(cfg: Config, minutes: float, press_every: float = PRESS_EVERY_S, *, seed=0, stations=STATIONS,
         window_s=WINDOW_S, real_devices=False, display=None, player_factory=EntryPlayer, clock=time.monotonic,
         sleep=time.sleep, perf=time.perf_counter) -> dict                      # the report
def failures(report: dict) -> list[str]   # the must-be-zero counts that are not, by name
def main(argv=None) -> int   # 0 clear, 1 failures (printed), 2 bad arguments; the report written either way;
                             # the soak runs inside show.main's sigterm_raises() (SDL's mixer swallows SIGTERM)
CLI: --minutes (5; over 0) --press-every (180) --config (show.toml) --backend (fake | sdl | colorlight | ddp; fake)
     --real-devices --seed --window-s --out (data/soak, under the gitignored /data/) -> <out>/soak-<stamp>.json
```
- A real `ShowLoop(cfg, display=display, notify=...)`: the loop makes and governs the display; the soak never names
  `make_display`, has no `.push(`. Paths resolve against the repository root, as `show_shot`. No `--real-devices`:
  `loop._devices = True`, `FakeLights`, `FakeAudio`, no buttons (as `tools/show_shot.py:347-348`). A press is
  `loop.presses.put(rng.choice(stations))` every `press_every`: the queue GPIO fills.
- The real `loop.run()`: `loop.clock`, `loop.sleep` set, `loop.step` wrapped on the instance; at the end the wrapper
  raises a private `KeyboardInterrupt` subclass, so `run`'s `finally` closes as a stop does. `run` ending any other
  way counts in `run_ended_early` (in process it stands for restarts; the service's are `NRestarts`).
- The JSON: steps, governed, push_failures (`wall.failed`), held_ticks, presses, plays_started, plays_ended,
  returns_to_attract, errors_logged (ERROR and over, `show` logger, after `start`, first 20 kept), errors_at_setup,
  step_ms and governor_ms (median, p95, worst; `wall.governor.apply` wrapped; fixed 0.1 ms histograms to 1 s), a
  `FlashMeter(wall.governor.fps, wall.governor.gamma)` on each new `wall.last` (per window, overall; its time out of
  step_ms), fds, rss, children left (`pgrep -P`), sha, config, times. Must be zero: push_failures, errors_logged,
  children_left, run_ended_early, windows with `squares_max > BUDGET`. Reported only: fd and rss growth, times.
- Tests, `tests/test_show_soak.py` (fake clock, 128x64 ink config, fake players): `test_a_short_soak_counts_steps_
  presses_and_plays` (3 s at 20 fps: 60 steps, 6 presses, plays end and return; `failures == []`); `test_a_strobing_
  entry_soaks_inside_the_budget` (the Recorder's pushed frames: `flash_area == 0.0`, `square_flashes <= BUDGET`);
  `test_the_wrappers_change_no_frame` (one seed: the pushed frames with and without the soak's wrappers, identical);
  `test_a_failing_display_fails_the_soak`; `test_a_logged_error_fails_the_soak`; `test_children_left_are_counted`;
  `test_main_writes_the_report` (`--minutes 0.02`); `test_the_soak_never_names_the_display_path`;
  `test_minutes_must_be_over_0`.

## I1 (orchestrator): the report
Collected, skips, time vs 245 s, `--durations=0`, `pgrep`; `git diff 245cb57 --` the NOT-edited files and the three
test files: empty; `tests/test_config.py`: line 20 and the new test only; `awk 'length > 120'` on changed files: none.

## I2 (the operator, in verify, after the review): from a clean detached checkout of the head; no tracked file edited
```
.venv/bin/python -m tools.show_soak --minutes 5 --press-every 5 --out <s>/it13-soak
.venv/bin/python -m tools.show_soak --config show.poc.toml --minutes 2 --press-every 5 --out <s>/it13-soak-poc
.venv/bin/python -m tools.show_shot --session strobe --seconds 6 --every-ms 150 --look plain --scale 1 --cols 4 \
    --out <s>/it13-strobe
.venv/bin/python -m tools.show_shot --session presses --every-ms 1000 --look both --out <s>/it13-presses
.venv/bin/python -m tools.show_shot --script strip --cols 6 --out <s>/it13-cols          # refused: exit 2
.venv/bin/python tools/wall_pattern.py panels --config show.toml --png <s>/it13-panels.png
.venv/bin/python tools/wall_pattern.py grid --config show.poc.toml --png <s>/it13-grid-poc.png
SDL_VIDEODRIVER=dummy .venv/bin/python tools/wall_pattern.py grid --backend sdl --config show.toml --seconds 2
SDL_VIDEODRIVER=dummy .venv/bin/python -m show --backend fake & sleep 5; kill -TERM $!; wait $!; echo "exit $?"
```
Soak: exit 0; about 6000 steps (2400 poc), governed = steps; failures, errors, children 0; `squares_max <= 6` each
window; 60 presses (24); step p95 under 50 ms; governor median (Q59); fd, rss growth. Strobe: 150 ms is three 50 ms
halves, so neighbouring cells differ (it12's 100 ms did not); every label `area 0.0000`, `sq <= 6`. presses: pages
under 4000 px. cols 6: message, no file. panels: 48 labels. The last two: exit 0, `closing`. Into `evidence/it13/`.

## Decisions
- One pattern tool: `tools/wall_pattern.py` grows, cap and refusal kept; Task 18's `test_pattern.py` is not built;
  its labelled `index` is `panels`, its `grid` is added. No `white` (Q64): every pattern stays under half the wall.
- `close` resends the counted frame when the last send did not complete; black goes even if that fails. A close
  after a strobe may be held, not black: the governor wins. SIGTERM raises once, only inside `main()`.
- The unit is unchanged (Q63). The soak runs in process with fakes. On the Pi at GATE C: `--real-devices`, pyte's
  feed time and the governor's cost (Q59); the operator writes that deadline into Q59 in decisions.md.

## Questions for the owner (decisions.md; the loop takes the default at once)
- Q63: May the unit order itself after `network.target`, not `network-online.target`? Default: unchanged (README:
  no carrier waits for wait-online's timeout, then runs); a change edits `tests/test_deploy.py:17-18`. GATE C.
- Q64: A full `white` pattern (core week 4's dead-pixel hunt)? Default: not built; given the panels' full-white current
  and the supplies' ratings, the loop adds it capped at 0.1, with its own refusal and test. The full wall's bring-up.
