# Iteration 5: Juice, the Runner and run_headless Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the second slice of M3: the runner every game runs inside. That is:
- the effects toolkit, `arcade/juice.py`;
- the runner, `arcade/runner.py`, with the player lock, presence, the session rules, the crash guard, `state()`, `sense()` and the tick order limiter, then governor, then push (Q11);
- the headless harness, `run_headless`, `NullLobby` and `helpers.run`, that every game test and agent tool will use.

It first closes the carried fixes that the runner depends on: C22, C25, C26, the C27 caller rule and the C29 minors in the files it touches.

**Architecture:** Task 1 changes three existing modules:
- `sensed.py`: a torso under `TORSO_FLOOR` of the box height is not measured, so the nose line stands in (C22).
- `scores.py`: `SessionLog.append` casts a numpy `players`, checks its names, and never raises on a failed write (C25). A malformed `"previous"` counts in the warning (C29).
- `input.py`: `OneEuro` casts its samples (C29), the two ruled it04 deviations are pinned by tests (C26), and the module docstring states the caller rule (C27).
- Two existing timing tests, in `test_flash.py` and `test_look.py`, time on the thread's CPU clock instead of the wall clock. Their thresholds are unchanged (plan review B2).

Tasks 2 to 4 are new modules:
- `arcade/juice.py`: `Juice(rng, size)` is one per launch, runner-owned and seeded. Shake, flash and bursts each keep the flash rule by themselves, saturated red included:
  - the shake jumps at most 4 times a second;
  - the flash holds its colour and stops, and the next one waits 0.5 s after it ends;
  - bursts fly at one speed and are spaced, so a pixel sees at most two a second.

  Banner text, pops and effects used together are the game's to pace. The governor catches the rest.
- `arcade/runner.py`: `Runner` ticks the lobby or a game:
  - `PlayerLock` and `Presence` derive `player`, `player2` and `present`;
  - the session rules are leave, inactivity, the cap and the deliberate exit, with C10's per-capture grace;
  - a crash guard covers `__init__`, `reset`, `update`, `draw`, `done` and `debug_state`, and a lobby that raises falls back to a title card;
  - every frame goes through `BrightnessLimiter.apply`, then `FlashGovernor.apply`, then `display.push`;
  - `sense()` reads the sources' `latest()` shapes and builds `Sensed` with keywords (C21).
- `arcade/headless.py`:
  - Task 3 adds `RecordingDisplay` and `OPENING_NIGHT`.
  - Task 4 adds `NullLobby` and `run_headless`, and `tests/arcade/helpers.py` gains spec 9.1's `run`.

The lobby itself, the attract director, is it06. Until then the runner is driven by a stub lobby in tests and by `NullLobby` in `run_headless`. `main.py` is not wired to the runner in this iteration.

**Tech Stack:** Python 3.12 from uv, numpy and pytest, with the venv from iteration 1. Nothing is installed.

**Spec:** `docs/superpowers/specs/2026-09-26-wall-arcade-design.md`, revision 3, with the owner's answers Q10-Q16 (`docs/superpowers/workflow/decisions.md`), which amend it until revision 4. The sections, by task:
- 5 and 7.5 for Task 1;
- 7.6 and 8.1 for Task 2;
- 4.3, 5, 6.4, 7.1, 7.2, 7.6 and 10 for Task 3;
- 9.1 and 9.2 (the budget) for Task 4.

**Sources merged here (this plan overrides them where they differ):**
- the roadmap's "Carried fixes" C10 (the runner half), C21 (Task 8's part), C22 and C25-C29 (`docs/superpowers/workflow/roadmap.md`);
- core plan `docs/superpowers/plans/2026-09-26-wall-arcade-core.md`: the Task 8 amendment (lines 502-534) and the revision-2 Task 8 body (lines 2346-2920), for the parts that name the runner, Juice, `run_headless` and `helpers.run`;
- the it04 plan's "Forwarded to later amendments" and "Resolved conflicts" (`docs/superpowers/plans/2026-09-28-it04-carried-input-protocol-safety.md`);
- the Global Constraints below.

Every file below is final code, given whole. The one exception is Task 1's clock change in two existing timing tests, which is given as a script together with the exact lines it produces. An implementer needs nothing else.

## Plan review round 1: what changed

Round 1 (`docs/superpowers/workflow/evidence/it05/plan-review.md`) was BLOCKED on B1 and B2. The plan now folds in both, notes N1-N7, and the operator's two decisions: `BURST_GAP` is 0.5, and the existing timing tests switch clock. Everything was replayed again in a fresh clone of `ee6780b`. The counts below are the new ones.

- **B1, a numpy `active` (Task 3).**
  - `_session_rule`'s activity check is now `_is_true(v)`, which is `v is True or (isinstance(v, np.bool_) and bool(v))`.
  - `test_active_is_a_bool_and_numpy_bools_count` covers seven values. `True` and `np.True_` keep a session past `inactive_seconds + PROMPT_SECONDS`. `False`, `np.False_`, `1`, `"yes"` and `np.int64(1)` end it as `inactive`.
  - The game-guide forward says that `active` is a bool and that numpy bools count.
- **B2, timing tests under load (Tasks 1, 2 and 4).**
  - Every `perf`-marked test now times with `time.thread_time()`, the thread's CPU clock, which counts the code's own cost:
    - Task 1 changes `test_flash.py`'s `test_governor_under_half_ms_at_128x32` (lines 500 and 502) and `test_look.py`'s `test_distance_keeps_up_with_the_preview` (lines 172 and 174). Both used `perf_counter`. Only the clock changes; the thresholds stay. On an idle machine the distance look measured 8.36 ms on `thread_time` against 8.22 ms on `perf_counter`, so its blur runs on the calling thread, and the CPU clock misses no work done elsewhere.
    - Task 2's `test_full_pool_under_half_ms` and Task 4's budget test are new, and use `thread_time` from the start.
  - The budget test keeps its governor-median assert, on `thread_time`. It is not a duplicate of `test_flash.py`'s: it times the governor inside the runner, on a strobe that keeps it on the holding path, at both layouts.
  - "Environment facts" now names the cause of the one failure seen while drafting, and says what to do before calling such a failure a regression.
  - The load test is recorded there too. With 8 busy-loop hogs and one suite at a time, 12 of 12 full-suite runs were green here, but the reviewer saw the existing governor test fail once in 6 such runs (round 2). With three suites at once as well, the new timing tests never failed, but the existing governor test still failed in 7 of 36 runs, on the slower efficiency cores: an open issue for the operator.
  - The hang checks in `test_canvas.py` (0.05 s) and `test_look.py` line 91 (0.5 s) are not perf tests and keep `perf_counter`. They stayed green in all 60 loaded runs.
- **N1, what Juice keeps by itself (Task 2).**
  - `BURST_GAP` is 0.5 (Q19).
  - `test_effects_keep_the_flash_rule_by_themselves` gains two cases. `burst-spot` is a saturated red burst at one fixed spot every tick, over black. `flash-red` is a 0.2 s red flash every 8 ticks.
  - Each case runs 150 ticks at both layouts. The asserts:
    - `flash_area` is 0 at the governor's budget for every case;
    - it is also 0 at a budget of 4 for the shake and both flashes;
    - with the effect's limit patched away, every case flashes.
  - `test_burst_near_a_recent_one_is_dropped` pins 0.5 exactly: refused after 14 ticks, accepted on the 15th.
  - **Found while doing this: the fading flash broke the rule.** A saturated red flash that fades over several frames makes up to three transitions on the way down, one for each of the governor's three signals, on different frames.
    - So `flash((255, 0, 0), 0.2)` called every tick flashed the whole wall at the governor's own budget: `flash_area` 1.0 at both layouts. The governor would have held the whole frame.
    - The flash is now a hold. It adds its colour for `seconds`, then stops: one rise and one fall on the same frame, whatever the colour.
    - `FLASH_GAP` now runs from the end of one flash to the start of the next. A fall is then always followed by at least 0.5 s dark, so no pixel changes more than 4 times in any second.
    - This is Q20, defaulted. The mutation that restores the fade is killed.
  - **"4 a second" for bursts is true for most pixels, not all.** At `BURST_GAP` 0.5, bursts at one spot for 300 ticks give 0 at the governor's budget. At a budget of 4 they give 0.001 to 0.003. A few pixels next to the origin see 5 or 6 changes in a second, because a diagonal particle can sit on one pixel for two frames. The same holds at every gap up to 0.7.
    - The wording now says: at most two bursts a second at any pixel, which is 4 changes for most pixels and the governor's 6 at most.
    - The test asserts the governor's budget for bursts, and 4 for the shake and the flash.
  - Line 18 above, loop decision 7, the module docstring, the Task 2 commit message and the game-guide forward now say it the reviewer's way: shake, flash and bursts each keep the rule alone; banner text, pops and combinations are the game's to pace; the governor catches the rest.
- **N2, wiring pinned (Task 3).** Each item has a test, and each named mutation now fails:
  - `test_governor_and_limiter_are_built_from_the_runners_settings`: at `cfg.fps=60` the governor's `fps` is 60, and a whole-wall strobe fed at 60 ticks a second gives `flash_area(frames, fps=60)` 0. The limiter's `lux` is the callable given (T4, T6).
  - `test_the_game_shakes_and_the_overlays_do_not`: a shaking fx moves the game's pixel by `fx_shake`, and the exit ring matches an unshaken reference circle (T7, T8).
  - `test_the_lobby_draws_on_the_tick_a_rule_ends_the_session` (T11).
  - `CRASH_SECONDS == 0.5` and `CRASH_RED == (96, 0, 0)` (C6, C15).
  - `test_crash_shows_static_dim_icon_then_lobby` runs twice: a crash in `update`, and `Smear`, which paints the whole wall and then raises in `draw`. Only the icon shows (C7).
  - `SpyGame.raise_in` takes `"debug_state"`, and the crash parametrize includes it.
- **N3, the exit's person and hand rules (Task 3).**
  - `test_exit_needs_the_players_own_two_hands`: a bystander's two hands, or the player's one hand, held for 6 s never exit and never show the ring (E9, E10).
  - `test_exit_block_holds_until_both_hands_are_down_for_the_grace`: after the exit, one hand stays up until 7 s. The lobby sees nobody until then and through the grace, and sees the player again within 0.2 s of that. It runs clean and under `REAL_NOISE` with four body ids (E5, E6).
  - E8, updating the exit hold only in games, still survives. It is equivalent while the reset on launch is there, as "Environment facts" says.
- **N4, decision 24.**
  - The code now matches the wording, with the smallest change. `launch` empties `_state` before it constructs the game, so a crash at launch never reports a key of the lobby's as the session's `score`. The filter in `_crashed`, which did nothing, is gone.
  - Decision 24 now says that during the icon none of the game's keys show, `score` included. The lobby's result and the session log carry the last score the game reported.
  - `test_crash_icon_has_no_game_keys_and_the_log_keeps_the_last_score` pins both.
- **N5, lamps and the moving-blob rule.** Forwarded to core Task 15 and GATE A as the reviewer wrote it (see "Forwarded"). No code change now.
- **N6.** `test_a_moving_light_holds_the_session`: a light carried across the zone, with no body, holds the session past `leave_seconds`, and leave runs once the light is gone (S1).
- **N7, `sense()` and `launch()` edges (Task 3).**
  - **Which `t`.** The `Sensed` that the lobby and games see now carries the runner's `t` for the tick, and `camera_t` moves by the same amount. A game therefore sees one clock, live and headless, wherever a scenario starts. `sense()` still stamps the runner's `t` before the tick's `dt`, and `tick()` moves both. `test_games_see_the_runners_clock` pins this.
  - **A malformed `latest()`.** Chosen route: it goes the way of a source that raises. The result is checked:
    - camera: `(capture_t, bodies, blobs, motion)`, with `Body` and `Blob` items and `motion` either `None` or a 2-D array;
    - audio: `(capture_t, Audio)`.

    Anything else makes that source unavailable for the tick, logged once per run of failures. Neither `sense()` nor `loop()` raises. The crash guard is for games, and a source is not one. `test_sense_treats_a_malformed_result_as_a_failed_source` covers 12 shapes and the loop.
  - **A lobby request that is not a str** is refused and logged as unknown. It used to raise `TypeError` for an unhashable one.
  - **A public `launch()` during the crash icon** ends the icon. Before, the icon would have sent the new game to the lobby without a session end.
  - `test_launch_refuses_an_unhashable_name_and_ends_a_crash_icon` covers both.
  - **Per-input availability** (`CAMERA_INPUTS` claims pose, blobs and motion whenever the camera is fresh) is forwarded to M5.

## Plan review round 2: what changed

Round 2 APPROVED the plan with notes R2-N1 to R2-N6. The operator asked for R2-N2 to R2-N5 to be folded in before commit. Everything was replayed again in a fresh clone of `ee6780b`, and the counts in this plan are the new ones: `test_runner.py` 73, Task 3's suite 437, and the iteration 448.

- **R2-N2, a capture stamped off the runner's clock (Task 3), fixed now.**
  - New constant `CLOCK_SLACK = 0.1` (seconds). `_stamped(capture_t, now)` accepts a capture time only if it is finite and at most `CLOCK_SLACK` past `now`. `_camera_result` and `_audio_result` check it, so an `inf`, `-inf` or `nan` stamp, or one more than 0.1 s ahead, is malformed, and that source counts as failed for the tick (logged once per run of failures), for camera and audio alike.
  - Why 0.1 s (loop decision 27): sources stamp on the runner's monotonic clock, in seconds, so a capture is never later than the moment `latest()` returns, microseconds after `sense()` reads `now`. 0.1 s leaves room for a slow thread handoff and is at most 3 camera frames. A stamp on another clock or in another unit (picamera2's nanoseconds since boot, or the wall clock's epoch) is off by hours or more.
  - `test_sense_treats_a_malformed_result_as_a_failed_source` gains `inf`, `nan` and an hour ahead, for camera and audio: 18 shapes now.
  - New `test_a_body_stamped_ahead_of_the_runners_clock_holds_nothing`:
    - a live camera stamping 0.05 s ahead counts, and presence comes on;
    - one stamping 0.2 s ahead does not;
    - a `-inf` stamp is logged as a failed source, not merely stale;
    - a frozen body stamped an hour ahead, repeated for 6 s, ends the session as `left` at `leave_seconds` and lets presence go.
  - Forwarded to core Task 15: sources stamp captures on the runner's monotonic clock, in seconds.
- **R2-N3, a public `launch()` mid-session (Task 3).**
  - `launch` returns False and logs `not launching 'paint': spy is running` unless the runner is in the lobby or showing the crash icon. So no session is ever dropped without its log line and end card.
  - New `test_launch_is_refused_while_a_game_runs`: the running game keeps running, no session is logged, and after its session ends the launch works.
- **R2-N4, the lobby's `request` (Task 3).**
  - `_take_request(lobby)` reads the request and sets it to None, and the runner calls it inside `_lobby_call`. A request that cannot be read or cleared is a lobby that raised: the title card replaces it, and `tick()` never raises for it.
  - New `test_a_request_that_cannot_be_cleared_is_a_lobby_that_raised`, with a lobby whose `request` is a read-only property. Before the fix, `tick()` raised `AttributeError`.
- **R2-N5, the load figure.** "Environment facts", loop decision 26 and the round-1 section now say the existing governor test can fail at one suite under 8 hogs too: 0 of 12 here, 1 of 6 in the reviewer's runs. The rerun rule stands.
- **Failing first.** Against the round-1 runner, the four changed or new tests fail and the other 69 pass: the shape test on the `inf` camera, the stamp test (the frozen body is kept), the launch test (`launch('paint')` is True), and the stuck-lobby test (`AttributeError` out of `tick()`).
- **Mutations, 11 more**, all killed: the finite check, the future check, `CLOCK_SLACK` at 0, 0.3 and 3600, the camera and the audio check each dropped, the launch guard dropped, the guard also refusing during the crash icon, the request read outside the guard, and the request not cleared.
- R2-N1 (the flash as a hold holds through the whole path) and R2-N6 need no change.

## M3 slicing

M3 is "game protocol with `SCENARIOS`, `_xy`, `MENU_ORDER`, and `GameInfo.layouts`; runner with session rules, flash governor, brightness limiter; attract director with four modes and the mirror". It splits into three iterations, in dependency order:

| Iteration | Tasks | What lands |
|---|---|---|
| it04 (9e48c24) | 4 | C18-C20; input helpers (with C10's helper half); game protocol, registry and scores (core Task 7); flash governor and brightness limiter. |
| **it05 (this plan)** | 4 | 1. Carried fixes C22, C25, C26, the C27 caller rule and C29 in touched files. 2. `arcade/juice.py`. 3. The runner (with C10's runner half and C21's Task 8 part) and `RecordingDisplay`. 4. `run_headless`, `NullLobby`, `helpers.run` and the tick budget on the governor's holding path (N23, C27). |
| **it06** | 2 or 3 | The attract director (tiers, sub-states, doors with dwell decaying over 0.3 s, cards), the mirror with `draw_figure` and `to_wall`, and the four modes: watcher, echo, warp and contours. C28 goes with it, because the director is the first caller of the game list. |

M3 is done when it06 lands. C11 and C17 stay with core Task 15. C23 stays with core Tasks 13 and 18. C24 stays with core Task 20 and M6.

## Global Constraints

Carried from the core plan ("Global Constraints" as replaced by "Global Constraints, revised"):

- Frames are numpy arrays of shape `(height, width, 3)`, dtype uint8, RGB, row-major.
- Every game declares `layouts`, and its tests are parametrized over the declared layouts (spec 9.1). 128x32 is the default and design layout. This iteration has no games. The runner and Juice tests that depend on the layout run at 128x32 and 64x64.
- Brightness:
  - The runner calls `display.set_brightness(cfg.brightness)` once.
  - The Colorlight backend enforces it at the panel with the card's brightness packet.
  - The fake and SDL displays store the level. The SDL window itself shows full brightness, and `PreviewDisplay` models the level in the preview it renders.
  - DDP logs once that brightness is Falcon Player's setting.
  - Pixels pushed to hardware are never scaled for `brightness`. The brightness limiter is a separate picture-level cap (spec 7.6), and it does scale frames.
- Tick rate 30 Hz. `dt` handed to games is clamped to 100 ms. Clocks and random sources are injected.
- Never seed from `hash()` of a str. Use `zlib.crc32` and print the seed in the assertion message.
- Modules that import `mediapipe`, `picamera2`, `cv2.VideoCapture` devices or `sounddevice` do so inside the class constructor, probe function or thread, never at module import. Tests never need hardware extras.
- Tests run headless: `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy` are set in `tests/conftest.py` before pygame is imported.
- No `print` in library code. Use `logging.getLogger("arcade")` in `arcade/` and `logging.getLogger(__name__)` in `show/`. CLI entry points and `tools/` may print. A test may print a measurement (Task 4's budget test does, through `capsys.disabled()`).
- Python 3.12 through uv on the Mac, with one OpenCV distribution, `opencv-contrib-python`.
- Commit after every task with the exact message and `git add` list given in the task.

Operator rules for this loop:

- Test modules are copied from this plan verbatim. Any difference, however small, is a Deviation and must be reported as one.
- Never remove or weaken an existing assert; only add or tighten. If an existing assert must change, the task and its commit message say why.
  - This iteration changes four existing test lines, and only their clock (plan review B2, operator decision). Task 1 times `test_flash.py`'s `test_governor_under_half_ms_at_128x32` (lines 500 and 502) and `test_look.py`'s `test_distance_keeps_up_with_the_preview` (lines 172 and 174) with `time.thread_time()` instead of `time.perf_counter()`.
  - Both thresholds stay. The CPU clock counts the code's cost and not the time the thread waits preempted, so the assert still bounds the code and no longer fails on a machine loaded by parallel agents.
  - Task 1 also appends four tests. Every other test module is new.
- `arcade/games/__init__.py` is not touched in this iteration.
- Never push. Never run `git push` or `gh pr create`.
- Use `.venv/bin/python` (Python 3.12 from uv). Never use the system `python3` (3.14), never `pip`, and never activate the venv in a way later commands depend on.
- Install with `uv pip install --python .venv/bin/python ...`. This iteration installs nothing.
- Run tests from the repo root with `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`. Append a path to run one module.

## Loop decisions taken by this plan (journal each one)

1. **This iteration has four tasks, not the three in it04's slicing table.** The carried fixes the runner depends on come first, as Task 1: the torso floor changes what a raised hand is, and the sessions log must not raise on the runner's crash path. C28 moves to it06, because the runner never calls `all_games` (decision 22).
2. **C22: a torso under `TORSO_FLOOR = 0.1` of the box height is not measured.**
   - `raise_line` then falls back to the nose, as it already does when the torso is 0.
   - Side-on at a bar, the shoulders overlap and the counter hides the hips. The torso estimated from the shoulder width is then a few hundredths, and a line 0.3 torsos above the shoulders sits a hair above them. A wrist at the collarbone would count as raised.
   - A full torso is unchanged.
   - A small far body still passes: a 0.35 box has a floor of 0.035.
   - Spec 5's wording ("the nose only when both shoulders are missing") is already listed for spec revision 4.
3. **C25: `SessionLog.append` never raises on the file path for a value the runner can hand it.**
   - `players` must be an integral number, not a bool, 0 or more. A numpy int is cast to `int`.
   - `game` and `layout` must be strings.
   - Anything else raises `ValueError`, because it is a runner bug, and that raise happens before any write.
   - `json.dumps` moved inside the `try`, which now catches `OSError`, `TypeError` and `ValueError`: a record that cannot be written is logged and kept in the return value.
   - The runner's crash path therefore cannot crash the runner.
4. **C26 pins it04's two ruled deviations with tests.**
   - `OneEuro` stores floats (B5).
   - A huge int in `scores.json` is a malformed entry: it is dropped with the warning, and `record(10**400)` returns `False` (decision 10).
5. **C29 in the files this iteration touches:**
   - `OneEuro.__call__` casts `x` and `t`. A sample that is not a real number, or an int too big for a float, is not a sample: it returns the last output, or NaN before the first.
   - `OneEuro` and `capture_grace` share one range check, `_positive`, instead of repeating `_check`'s.
   - `Hold(10**400)` now raises `ValueError`. Before, `_check` let it through and `float()` overflowed.
   - A malformed `"previous"` entry counts in the load warning, and its entry is kept without last night.
   - The other C29 minors are in files this iteration does not touch, and are forwarded (see "Forwarded").
6. **C27: the caller rule is in `arcade/input.py`'s docstring.** The runner follows it:
   - it updates its exit `Hold` on every tick, the lobby's included;
   - it resets the hold on every launch, so hands held up in the lobby never end the next game at once.

   `test_exit_hold_is_reset_on_launch` pins the reset. Updating in the lobby is not observable while the reset is there (see "Environment facts"), and it is kept so the rule holds as written.
7. **Shake, flash and bursts each keep the flash rule by themselves (spec 8.1 "additive and rate-limited", it04 N11), whatever the colour.** Saturated red counts too, which the governor counts three ways. Each effect alone stays under the governor's 6 changes a second, and the shake and the flash under 4:
   - **The shake is jumps, not a smooth wobble.** The offset changes at most once every `SHAKE_STEP = 0.25` s: to the other side, smaller each time, along one axis the rng picks, reaching 0 at the end. A jump moves each pixel once whatever the picture. A smooth sinusoid over a 4 px checker was measured at 4 transitions per pixel per period, over budget at any useful rate. See owner question Q18.
   - **The flash is a hold, not a fade.**
     - It adds its colour for `seconds`, then stops: one rise and one fall, each on one frame for all three of the governor's signals.
     - A new flash starts only `FLASH_GAP = 0.5` s after the last one ended; while one shows, or before then, `flash` returns `False`.
     - A fade would make up to three falls from one saturated red flash, one per signal on different frames. At 2 flashes a second that flashed the whole wall at the governor's own budget (plan review round 1). See Q20.
   - **Bursts.**
     - Every particle flies at `BURST_SPEED = 30` px/s for `BURST_LIFE = 0.5` s, so a particle passes a pixel once.
     - A burst within `BURST_NEAR = 32` px of one accepted in the last `BURST_GAP = 0.5` s is dropped, and `burst` returns `False`. See Q19.
     - So at most two bursts a second reach any pixel. That is 4 changes for most pixels. A few next to an origin, which a diagonal particle takes two frames to cross, reach 5 or 6, measured over 300 ticks. That is never over the governor's 6.

   `test_effects_keep_the_flash_rule_by_themselves` runs each effect as fast as a game can call it, at both layouts: the shake over a 4 px checker; bursts moving, and saturated red bursts at one spot, over black; a white flash and a red one, over black. It checks:
   - `flash_area` is 0 at the governor's budget for every case;
   - `flash_area` is 0 at a budget of 4 for the shake and both flashes;
   - with the effect's limit patched away, `flash_area` is over 0, so the test has teeth.

   Banner text, pops and effects used together are the game's to pace. Measured `flash_area` over 150 ticks at both layouts:
   - a banner whose text changes every tick: 0.03 with one digit, and 0.12 with the review's longer text;
   - a pop at one place every 10 ticks: about 0.02;
   - a burst, a flash and a shake called together every tick: 0.017.

   The governor runs after all of it and holds what goes over (forwarded to the game guide).
8. **Juice draws the players' markers.** Spec 8.1: "A 2 px marker in the player's colour stays on the bottom row under them in every game."
   - `render(canvas, player, player2)` draws 2 px at `marker_x(body, width)` on the bottom row, in `PLAYER_COLORS`: amber (255, 120, 0) for player 1 and blue (0, 160, 255) for player 2.
   - The markers and `echo` glyphs (3x3, over the marker, for `ECHO_SECONDS = 0.25`) are drawn after the shake, so they never shake.
   - it06's mirror uses the same `PLAYER_COLORS` (forwarded).
9. **Juice takes a game's numbers as they come.** A NaN, an infinity, a negative duration, a non-number or an unknown colour makes that call do nothing, returning `False` where it returns a bool. Nothing in Juice raises into a game, as with scores.
10. **Juice has a second argument, `size`.** `celebrate` needs the wall's width and height: it bursts at `x` in `range(16, width, 32)` across the middle, now and again after `CELEBRATE_GAP = 0.5` s. The amendment's `Juice(rng)` keeps working, with 128x32 as the default. Pops rise `POP_RISE = 6` px over `POP_SECONDS = 0.8` s, and the newest `MAX_POPS = 8` are kept. The banner draws at 2x when it fits, on a black box.
11. **The lobby gets no Juice.** `runner.fx` is `None` in the lobby, and the lobby's `state()` has no `fx_*` keys. The director (it06) keeps its own effects, if any, under the same flash rule.
12. **Player lock (spec 7.2):**
    - `player` is the in-zone body with the largest scale.
    - A rival must be more than `SWITCH_RATIO = 1.3` times larger, the same rival, for `SWITCH_SECONDS = 1.0`.
    - While the locked body is missing, `player` is `None` and the slot is kept for `player_lost_seconds`.
    - Re-acquired by nearest position: in that window, a body whose id was not present at the last sighting, within `REACQUIRE_DISTANCE = 0.25` zone units of the player's last place, takes the slot. The tracker never reuses an id, so a re-detected player is a new id, while a body that stood there all along is somebody else.
    - After the window, the largest in-zone body takes the lock.
13. **Presence evidence is an in-zone body, or a moving in-zone blob (spec 7.2).**
    - A blob is moving when, between two camera captures, it moved at least `BLOB_SPEED = 0.05` frame widths a second away from every blob of the capture before, timed by `camera_t`.
    - It is judged on `camera_fresh` ticks and held between them. A light that appears counts on its first capture; a parked lamp never does.
    - The leave rule uses the same evidence, so a lamp in the zone cannot hold a session open.
    - The blob source's own 5 s scenery mask (spec 6.1, core Task 15) is separate and still lands there.
14. **Session rules, in this order on each game tick:** exit, leave, inactivity, cap. The first that fires ends the session, and the lobby ticks at once with `dt` 0, so the wall is never a blank frame.
    - **Leave:** no evidence for `abandon_seconds` if the game sets it, else `leave_seconds`.
    - **Inactivity:** after `inactive_seconds` without the game's `active` key true, "STILL PLAYING? HAND UP" shows for `PROMPT_SECONDS = 5` s. A raised wrist on the player, or `active`, cancels it. Otherwise the session ends as `inactive`.
      - `active` is spec 7.1's boolean. Python `True` and numpy `True` (`np.True_`, which a numpy comparison gives) count.
      - `1`, `"yes"`, a numpy int or anything else is not a boolean and never counts (plan review B1).
    - **Cap:** only after `max_session_seconds`, only while more in-zone bodies stand than the game's `players`, and only on a tick whose `phase` is not `play`. A game without a `phase` key counts as mid-round and is never capped. Every game declares its phases (spec 7.1), and the game guide says to leave `play` between rounds (forwarded).
15. **Deliberate exit (C10's runner half):**
    - The exit is `Hold(cfg.exit_seconds, grace=capture_grace(cfg.camera_fps))` on `player.both_hands_up`: 3 s through the 15% keypoint dropout, measured over eight noise seeds.
    - The ring is grey (160, 160, 160). It is drawn at the player's `zone_x` while the hold fills, closing from half the wall to 1 px, and only when `info.exit_gesture`.
    - After an `exit` end, the lobby gets no bodies, blobs or players until no in-zone body has shown a raised wrist for longer than the grace. Other ends do not block: nobody's hands are up on purpose.
16. **Players and waiting in `SessionResult`:**
    - `players` is the most in-zone bodies seen at once during the session, capped at the game's `players`.
    - `waiting` is true when more in-zone bodies than the game's `players` stand at the end. The lobby's card uses it for "NEXT: RAISE A HAND" (it06).
    - `score` is the game's last `score` key. On a crash it is the last score the game reported.
17. **Crash guard:**
    - What it guards: `__init__`, `reset`, `update`, `draw`, `done` and `debug_state`. A crash in `__init__` or `reset` makes `launch` return `False`.
    - What it records: the traceback is logged and kept as `last_error`, the session is logged with reason `crash`, and the lobby's `end_session` is told.
    - What the wall shows: only the game's own 16x16 icon, static, in dim red (96, 0, 0), fading linearly to black over 0.5 s. A crash in `draw` clears what the game drew first. The lobby draws on the tick the icon ends.
    - A public `launch()` while the icon shows ends the icon.
    - A lobby request that is not a str is refused and logged as unknown, like an unknown name.
    - Hiding: a game that has crashed 3 times since the runner started is hidden until the restart (Q17).
    - The lobby: if it raises, it is replaced by a built-in "ARCADE" title card until restart and never called again. The lobby itself is never hidden.
    - `strict` re-raises, the lobby's exceptions included.
18. **The frame path is limiter, then governor, then push (Q11).**
    - The runner draws into one canvas every tick. It never keeps a reference to a pushed frame. `RecordingDisplay` copies.
    - A push that raises is logged at most once a minute, and the next tick carries on.
    - A governor hold is logged at most once a minute with the game's name (spec 7.6). `flash_held_ticks` is `governor.held_ticks`.
19. **`sense(camera, audio)` reads spec 5's `latest()` shapes:** `(capture_t, bodies, blobs, motion) | None` and `(capture_t, Audio)`, with capture times on the runner's injected clock.
    - A result older than `CAMERA_STALE = 1.0` s or `AUDIO_STALE = 0.5` s is empty, and its source is unavailable (spec 6 and 10).
    - A source whose `latest()` raises is unavailable. The failure is logged once per run of failures.
    - So is one whose result has another shape (plan review N7). The camera's must be `(capture_t, bodies, blobs, motion)`, with `Body` and `Blob` items and `motion` either `None` or a 2-D array; the audio's must be `(capture_t, Audio)`. A source is not a game, so this is not the crash guard: `sense()` and `loop()` never raise for it.
    - `camera_t` is placed on the runner's `t`. `camera_seq` counts new captures, and `camera_fresh` is true on the tick one arrives.
    - The lobby gets `set_status(camera_ok, mic_ok, inputs, calibrated)` every tick. `inputs` is the subset of `pose`, `blobs`, `motion` and `audio` whose source is fresh.
    - `Sensed` and `Audio` are built with keywords (C21).
20. **Time.**
    - The runner's `t` is the sum of its clamped `dt`s. It never takes its time from `sensed.t`, so scenario files and actors can start anywhere.
    - The `Sensed` that the lobby and games see carries the runner's `t` for the tick, with `camera_t` moved by the same amount. A game sees one clock, live and headless (plan review N7).
    - `sense()` builds `t` and `camera_t` on the runner's `t` before the tick's `dt`, and `tick()` moves both.
    - `loop()` runs a late tick at once and restarts its schedule from it, with no burst of catch-up ticks (it04 N1).
    - `local_clock` is local time for the limiter's night and the scores' night of, never the monotonic clock (B4).
    - `run_headless` and `helpers.run` fix `local_clock` at `OPENING_NIGHT`, 21:00 on 2026-11-11, so headless evidence never depends on the time of day. That is day, so the limiter caps at `apl_cap_day`.
21. **Seeds.**
    - The lobby's rng is `crc32(f"{seed}:lobby")`.
    - A launch's rng is `crc32(f"{seed}:{name}:{n}")`, where `n` counts launches.
    - Its Juice rng is the same string plus `":fx"`.
    - Two runners with one seed replay the same launches, and a second launch of a game is a different run.
22. **The runner keys `games` by `info.name` once, at construction, and never calls `all_games`.** `main` (core Task 11) will pass `all_games()` once at startup. C28, `get_game` re-importing on every call, is forwarded to it06, where the director is the first caller.
23. **Scores and sessions default to in-memory ones.** `main` passes the files in `data_dir`, and `run_headless` always uses in-memory ones. The runner gives a game `game.scores = scores.for_game(name, layout)` before `reset`, so a game can read tonight's best in `reset`.
24. **`state()` merges in order: the game's (or lobby's) `debug_state`, then the `fx_*` keys, then the runner's ten keys, which win.**
    - `t` and `idle` are rounded to milliseconds.
    - `idle` is 0 while present, else the time since the last evidence.
    - `attract` is true in the lobby while nobody is present.
    - During the crash icon, `glitch` is true and none of the game's keys show, `score` included. The lobby's `SessionResult` and the session log carry the last score the game reported (decision 16).
    - A launch starts from an empty state, so a crash in `__init__` or `reset` reports no score, never a key of the lobby's (plan review N4).
25. **The tick-budget test** (spec 9.2, `ARCADE_TICK_BUDGET_MS`, default 2.0) runs through `run_headless` with `RecordingDisplay(keep_all=False)`, over 300 ticks after a second of warm-up, at both layouts. It covers:
    - a full-wall strobe with a burst every second, which keeps the governor on its holding path (N23);
    - a static high-contrast picture, which it never holds.

    It asserts the mean is under the budget, the p95 under twice it, and the governor's median under 0.5 ms. It prints the governor's share of the tick (C27, N23).

    It times with `time.thread_time()`, the thread's CPU clock, which is the code's cost and what the budget is for (plan review B2). The governor-median assert stays, on the same clock. It is not a duplicate of `test_flash.py`'s: it times the governor inside the runner, on the holding path, at both layouts.
26. **Every `perf` test times on the thread's CPU clock (plan review B2).**
    - `perf_counter` also counts the time a thread waits preempted. On Apple Silicon a preempted thread often moves to an efficiency core. Under the load of parallel agents, the budget test and `test_flash.py`'s governor timing failed in 7 and 8 of 33 loaded runs.
    - The four `perf` tests use `time.thread_time()`:
      - Task 1 switches `test_flash.py:500,502` and `test_look.py:172,174`, changing only the clock;
      - Tasks 2 and 4 are new.
    - The thresholds stay.
    - The CPU clock removes the waits, not a slower core: under load, even one suite beside 8 hogs, the existing governor test can still fail on an efficiency core (see "Environment facts"). The rerun rule there applies.
    - The GATE B timing on the Pi 5 still stands (it04 reviewer's note), and prints the same report.
27. **The runner guards its own edges (plan review round 2).**
    - A capture stamp must be on the runner's clock: finite, and at most `CLOCK_SLACK = 0.1` s past `now`, or the source is malformed for the tick (R2-N2).
      - On the right clock a capture is never later than `latest()` returning, microseconds after `now` is read. 0.1 s leaves room for a slow thread and is 3 camera frames at most.
      - A wrong clock or unit is off by hours or more.
      - Without this, a source repeating a capture stamped ahead stays fresh, and holds a frozen body and its session.
    - `launch()` is refused, with a warning, unless the runner is in the lobby or showing the crash icon (R2-N3). The alternative, ending the running session first, would need a reason that `scores.REASONS` (`done`, `left`, `inactive`, `capped`, `exit`, `crash`) does not have.
    - The lobby's `request` is read and cleared inside `_lobby_call` (R2-N4).

## Owner questions

All four are defaulted under the owner's standing instruction of 2026-09-28: the loop takes its conservative default at once and lists each for the iteration-6 check-in. None changes a spec rule the owner has answered.

- **Q17: How many crashes hide a game?** (defaulted)
  - Spec 7.2 says "a game that raises three times in a session is hidden until the dusk restart". But a crash ends its session, so a game can raise only once in a session.
  - Default: three crashes since the runner started hide it until the restart. `MAX_CRASHES = 3`, per game, over the night.
  - `test_crash_hides_after_three` pins it.
  - Alternative: three crashes in a row, with a clean session resetting the count.
- **Q18: The shake is a few jumps, not a smooth wobble.** (defaulted)
  - Default: the frame jumps to alternate sides, shrinking, at most 4 times a second (loop decision 7). This is the design that keeps the flash rule by itself over fine detail.
  - The cost is that a shake reads as a few knocks, not a rumble.
  - Alternative: a smooth shake, with the governor holding it over busy pictures, which the owner would see as a stutter.
- **Q19: Bursts close together.** (defaulted)
  - Default: a burst within 32 px of one accepted in the last 0.5 s is dropped (loop decision 7). The gap was 0.4 s until the operator raised it to 0.5 in plan review round 1, so that at most two bursts a second reach a pixel. A fast rally that bursts on every hit shows every other burst or so.
  - Alternative: merge the new burst into the old one's remaining particles, which spends more of the pool.
- **Q20: The flash is a hold, not a fade.** (defaulted, new in plan review round 1)
  - Default: `flash(color, seconds)` adds its colour at full for `seconds`, then stops. The next flash waits 0.5 s after it ends (loop decision 7).
  - Why: a saturated red flash fading over several frames counts up to three falls under the governor's red rule, so red flashes on every point would make the governor hold the whole wall.
  - The cost is that a flash reads as a blink, not a glow that dies away.
  - Alternative: keep the fade and allow at most one flash a second, with `seconds` capped below that.

Dwell time, session timeouts and presence thresholds keep their spec defaults in `arcade/config.py`. GATE A confirms them live.

## Forwarded to later amendments

- **it06, director (core Task 9 superseded):**
  - Everything it04 forwarded to it06 stands: `to_wall` and `draw_figure`, door titles at 2x at most and 30 px/s at most with the `concurrent_area < 0.09` and `held_ticks == 0` checks, and door dwell decaying over 0.3 s.
  - C28: compute the game list once at startup (`main` passes `all_games()` to the runner and the director). `get_game` stops calling `all_games()` per call, or goes.
  - The director implements `LobbyLike`: `request`, `set_available`, `set_status` and `end_session(SessionResult)`.
    - Its end card shows `SessionResult` for 3 s (spec 7.2's "3 s score card") and "NEXT: RAISE A HAND" when `waiting`.
    - Its hand-up and door selection use `Edge` and `Cursor` with `capture_grace(cfg.camera_fps)`, updated every tick (C27).
    - Its NEAR tier's "moving in-zone blob for 1 s" uses `runner.moving_blob`.
  - The mirror draws a player in `juice.PLAYER_COLORS`, the markers' colours.
- **Core Task 11 (`main`):** build the runner with `all_games()` once, `Scores(data_dir / "scores.json", datetime.now)`, `SessionLog(data_dir / "sessions.jsonl")`, the loaded calibration, `local_clock=datetime.now` and `lux=None` until Task 19. Call `runner.loop(camera, audio)`.
- **Core Task 12 (scenario files), Task 14 and Task 18 (`record`):** C21's remaining parts, unchanged: keyword `Sensed` and `Audio`, `decode`'s empty `(0, 0)` motion grid, `place()` on every body, and the recording's calibration passed to anything that re-places.
- **Core Task 13 (`--flash-report`):** unchanged from it04.
- **Core Task 15 (sources' clock, plan review R2-N2):** every source stamps its captures on the runner's monotonic clock (`time.monotonic`, the runner's `clock`), in seconds. picamera2's sensor timestamps (nanoseconds since boot) and wall-clock times must be converted at the source. The runner treats a stamp that is not finite, or over `CLOCK_SLACK` (0.1 s) ahead of its clock, as a failed source (loop decision 27).
- **Core Task 15 (blob source):** C11 and C17 unchanged. `Blob.vx` and `vy` (C11) may replace the runner's capture-to-capture speed in `moving_blob` when they land.
- **Core Task 15 and GATE A, the moving-blob rule (plan review N5, as the reviewer wrote it):**
  - The rule is fragile for real lamps. A lamp that the blob source misses on every 5th capture "appears" on the next and counts, so the session never leaves. Missing every 20th capture, the session is still open at 12 s with `leave_seconds` 2.
  - Centroid jitter of ±0.001 frame widths at 30 captures a second counts as moving: `BLOB_SPEED` 0.05 fw/s is 0.27 px a capture at the 160 px lores width.
  - The leave timer resets on a single tick of evidence. The test models only a perfect lamp, and `degrade` never jitters or drops blobs.
  - To do: judge displacement over a window (for example at least 0.02 fw from where the blob was about 0.5 s ago), or require sustained motion. Add jittered and flickering lamp tests, and refit on captured lamps at GATE A.
  - The source's 5 s scenery mask is the backstop meanwhile. Dropping a still player who shows only as light is consistent with spec 7.2.
  - No owner question, unless the refit changes spec 7.2's wording.
- **M5 (inputs):** per-input availability. `sense()` claims `pose`, `blobs` and `motion` together whenever the camera result is fresh (`CAMERA_INPUTS`). M5 needs each input's own availability, and `test_sense_survives_raising_source_and_reports_status`'s status set will change then (plan review N7).
- **Core Task 19 (IMX500 lux):** `lux` is a callable returning the latest lux metadata or `None`. Until then `main` passes `None`, and the clock decides.
- **Core Task 20 (soak):** C24 unchanged, plus `test_every_game_fits_the_tick_budget` through `run_headless`, as Task 4's budget test does here.
- **Game guide (M6 `arcade-game-authoring`, C24):**
  - Report `phase` values from `PHASES`, and leave `play` between rounds, or the session cap never applies (loop decision 14).
  - Report `active` on any tick with meaningful input, or the inactivity prompt shows. `active` is a bool: `True`, or a numpy bool such as `np.any(...)` gives, counts. `1`, `"yes"` and numpy ints do not (plan review B1).
  - Juice: shake, flash and bursts each keep the flash rule alone, at any rate a game calls them.
  - Banner text, pops and combinations are the game's to pace. A banner whose text changes every tick, a pop at one place more often than about once a second, or a burst, a flash and a shake together every tick each flash a small part of the wall. The governor catches the rest (loop decision 7).
  - A game's own drawing must keep the rule too.
  - `flash` is a hold, not a fade (Q20), and returns `False` while one shows or within 0.5 s after it.
- **C29, files not touched here:** `FlashGovernor` does not validate `height` and `width`; the flash metrics do not check shape or dtype; a huge-int lux reading raises `OverflowError` (`brightness.py:82`); `GameInfo(needs=[["pose"]])` raises `TypeError`, not `ValueError`; `brightness.py` logs to `"arcade.brightness"` (change code and the verbatim test together). These go with the next iteration that touches `flash.py`, `brightness.py` or `game.py`.
- **GATE B (prototype week):** time the whole tick on the Pi 5 at both layouts with Task 4's budget test and `ARCADE_TICK_BUDGET_MS=20`. Record the governor's share, printed by the test, in `docs/superpowers/workflow/evidence/pi-perf.md` (N23). The test reports CPU time (`thread_time`, loop decision 26). Also re-time `test_flash.py`'s governor median there (it04 reviewer's note).
- **Spec revision 4:**
  - spec 7.2's "three times in a session" (Q17);
  - the cap's `phase` rule for a game without `phase`;
  - spec 8.1's "shake as an integer frame offset that decays" as jumps (Q18);
  - spec 8.1's flash as a hold (Q20);
  - `Juice(rng, size)`;
  - spec 7.2's tick order, already listed (Q11).
- **Operator:** when this iteration closes C22, C25, C26, C27 and the touched part of C29, and C10's and C21's Task 8 halves, copy the items above into the roadmap's carried fixes.

## Resolved conflicts

- **The amendment's tick order** puts `FlashGovernor.apply` before `BrightnessLimiter.apply`. The owner chose governor last (Q11). `test_push_path_order` pins limiter, then governor, then push.
- **The amendment's `Hold(exit_seconds, grace=0.25)`** misses under spec noise (C10). The exit uses `capture_grace(cfg.camera_fps)`, 0.55 s at 10 fps (Q10). `test_exit_hold_rides_out_camera_noise` covers eight noise seeds.
- **The amendment's `Runner(...)` signature** gains `local_clock` and `lux` (it04 B4). `run_headless` gains `display`, so the budget test can pass `RecordingDisplay(keep_all=False)`.
- **The amendment lists `test_fx_keys_in_runner_state` under `test_juice.py`.** It needs the runner, so it is in `test_runner.py`. `test_juice.py` has `test_fx_keys_are_namespaced` for Juice's own keys.
- **The amendment lists `test_run_headless_returns_launched_instance_after_done` under `test_runner.py`.** It is in `test_headless.py`, with the rest of the harness tests, because `run_headless` is Task 4's.
- **Spec 7.2 against 7.2 on crashes.** "Three times in a session" against a crash ending the session: Q17's default.
- **Spec 7.2's "a 3 s score card, then the lobby"** is the lobby's card (spec 7.3). The runner hands `SessionResult` to `lobby.end_session` and returns to the lobby at once. The director draws the card for 3 s (it06).
- **The revision-2 Task 8 body** draws a 30-tick noise glitch on a crash, tracks `attract` itself, and has `MenuLike`. The amendment replaced all three (a static dim icon, the lobby as the attract, `LobbyLike`), and this plan follows the amendment.
- **The it04 forward "The lobby's hand-up and door selection use `Edge` and `Cursor` with the same grace"** is the director's, so it moves to it06.

## Additions beyond the source plans (reviewer: check these on purpose)

- **Task 1:**
  - `sensed.TORSO_FLOOR`;
  - `input._float` and `input._positive`;
  - `SessionLog`'s checks on `game`, `layout` and `players`;
  - four tests appended to `test_sensed.py`, `test_scores.py` and `test_input.py`;
  - the clock change in `test_flash.py` and `test_look.py` (loop decision 26).
- **Task 2:**
  - `Juice`'s `size` argument, and the constants `SHAKE_STEP`, `SHAKE_MAX`, `FLASH_GAP`, `BURST_*`, `POP_*`, `MAX_POPS`, `ECHO_SECONDS`, `ECHOES`, `PLAYER_COLORS` and `CELEBRATE_GAP`;
  - `marker_x`;
  - the `frozen` property;
  - `flash` and `burst` returning `bool`;
  - the flash as a hold, with `FLASH_GAP` from its end (Q20);
  - the `fx_banner`, `fx_pops` and `fx_echoes` keys;
  - Juice uses `canvas._c`, the canvas's own colour check, so a colour means the same in both;
  - 10 test functions beyond the amendment's five for Juice, and the `burst-spot` and `flash-red` cases of the flash-rule test.
- **Task 3:**
  - `SessionResult`;
  - `Presence`'s `last_seen`;
  - `moving_blob` and `BLOB_SPEED` (loop decision 13);
  - `REACQUIRE_DISTANCE`;
  - `Runner.available()`, `launch()`, `end_session()`, `games`, `grace`, `current`, `current_name`, `fx`, `trace`, `raw_frames` and `running`;
  - the crash icon from `info.icon`;
  - `debug_state` guarded;
  - `_is_true` for `active` (B1);
  - `_camera_result` and `_audio_result`, which check a source's result shape (N7);
  - `Sensed.t` and `camera_t` moved to the runner's `t` in `tick` (N7);
  - `launch` refusing a name that is not a str, emptying the state first, and ending a crash icon (N4, N7);
  - `RecordingDisplay` and `OPENING_NIGHT` in `arcade/headless.py`;
  - the test helpers `SpyGame` (with `"debug_state"` in `raise_in`), `spy`, `StubLobby` and `FakeClock`;
  - the tests beyond the amendment's list:
    - scores given before `reset`;
    - crash hiding;
    - freeze;
    - inactivity cancelled;
    - the exit under noise and on launch;
    - the source checks;
    - the log rate limits;
    - the loop;
    - `dt` clamping;
    - blobs for games;
    - the round-1 tests: `active` values (B1), the governor's `fps` and the limiter's `lux`, the draw/render/overlay order, the lobby on the ending tick, a crash in `draw`, the crash state and score, the exit's hands and block, a moving light holding a session, the runner's clock, malformed source results, and `launch` edges.
- **Task 4:**
  - `NullLobby.results`;
  - `run_headless`'s `display`;
  - the harness tests;
  - the budget test's strobe scenario and the governor's share (N23);
  - its CPU clock (loop decision 26).

## Review Focus

1. **A game that crashes, draws garbage or never ends, on a festival night.**
   - Expected: the wall never goes dark for more than the 0.5 s icon.
   - Expected: the runner never raises in non-strict mode, the sessions log never raises (C25), and the game is hidden after three crashes.
   - Expected: a lobby that raises, or whose request cannot be cleared, is replaced for good.
   - Expected: a camera or mic whose captures are stamped off the runner's clock counts as failed, and never freezes a body on the wall.
   - Tests (Task 3): `test_init_reset_and_done_raises_are_guarded` (all six places), `test_crash_shows_static_dim_icon_then_lobby` (a crash in `update`, and one in `draw` after painting the wall), `test_crash_hides_after_three`, `test_crash_icon_has_no_game_keys_and_the_log_keeps_the_last_score`, `test_lobby_crash_falls_back_to_title_card`, `test_the_lobby_draws_on_the_tick_a_rule_ends_the_session`, `test_launch_refuses_an_unhashable_name_and_ends_a_crash_icon`, `test_launch_is_refused_while_a_game_runs`, `test_a_request_that_cannot_be_cleared_is_a_lobby_that_raised`, `test_a_body_stamped_ahead_of_the_runners_clock_holds_nothing` and `test_session_logged_with_reason`. Task 1's `test_sessions_log_casts_numpy_players_and_checks_names` covers the log itself.
2. **A crowd at the wall: people walking behind the player, a taller friend stepping in, the player ducking out of frame for a moment.**
   - Expected: the player keeps the slot through the crowd and through a short loss.
   - Expected: the slot passes to a rival only one clearly larger for a second, and never to someone who was already standing there.
   - Tests (Task 3): `test_crowd_of_six_never_steals_the_player` (under `REAL_NOISE`), `test_player_switches_after_1_3x_for_one_second` and `test_player_reacquired_by_position_keeps_slot`.
3. **Both hands up under real camera noise, and hands still up after the exit.**
   - Expected: one exit near 3 s.
   - Expected: the lobby does not take the same hands as a door selection.
   - Expected: hands held up in the lobby do not end the next game at once (C27).
   - Expected: only the player's own two hands exit; a bystander's two, or the player's one, never do.
   - Tests (Task 3): `test_exit_hold_rides_out_camera_noise` (eight seeds), `test_exit_then_hands_still_up_reaches_lobby_as_no_bodies`, `test_exit_block_holds_until_both_hands_are_down_for_the_grace` (clean and four noise seeds), `test_exit_needs_the_players_own_two_hands` and `test_exit_hold_is_reset_on_launch`.
4. **Lights at a burn: a parked lamp in the zone, a headlamp carried across it, a glowstick outside it.**
   - Expected: a parked lamp never makes anyone present and never holds a session open.
   - Expected: a light carried across the zone does count, at 30 and at 10 captures a second.
   - Expected: games get only in-zone blobs.
   - Tests (Task 3): `test_presence_hysteresis_ignores_out_of_zone`, `test_leave_ends_session_with_card`, `test_a_moving_light_holds_the_session` and `test_games_get_only_in_zone_blobs`. Lamps the blob source drops or jitters are forwarded to core Task 15 and GATE A (N5).
5. **Juice used hard: a shake on every hit, bursts on every catch, flashes on every point, and effects with bad numbers.**
   - Expected: the effects alone never flash past the governor's budget.
   - Expected: bad numbers do nothing, and nothing raises into the game.
   - Expected: the wall keeps its frame budget with a full particle pool.
   - Tests (Task 2): `test_effects_keep_the_flash_rule_by_themselves` (each effect, saturated red bursts at one spot and red flashes included, both layouts, with and without its limit), `test_bad_numbers_do_nothing` and `test_full_pool_under_half_ms`. Task 4's `test_tick_budget_with_the_governors_share` covers the whole tick.

## Environment facts verified 2026-09-28

- HEAD is `ee6780b`. The working tree differs only in `docs/superpowers/workflow/` files and this plan.
- The suite is 334 collected, 334 passed, 0 skipped.
- `.venv` is Python 3.12.13 with numpy 2.5.3, pytest 9.1.1 and pygame 2.6.1.
- `arcade/juice.py`, `arcade/runner.py`, `arcade/headless.py`, `tests/arcade/helpers.py`, `tests/arcade/test_juice.py`, `tests/arcade/test_runner.py` and `tests/arcade/test_headless.py` do not exist.
- `tests/__init__.py` and `tests/arcade/__init__.py` exist, and `pyproject.toml` sets `pythonpath = ["."]`, so `from tests.arcade.helpers import ...` works. The `perf` marker is declared.
- `font5x7` is a session fixture in `tests/arcade/conftest.py`.
- `arcade.canvas` has `_c(color)`, `Canvas.fill_rect`, `circle`, `blit(mask, x, y, color)`, `text(x, y, s, color, scale=1)` and `text_width(s, scale=1)`. `show.font.CELL_H` is the line height.
- `arcade.game.RUNNER_KEYS` has the ten keys, and `GameInfo` has `players`, `exit_gesture`, `abandon_seconds` and `icon`.
- `ArcadeConfig` defaults:
  - `fps` 30 and `camera_fps` 10;
  - `present_on_seconds` 1.0 and `present_off_seconds` 3.0;
  - `player_lost_seconds` 0.5, `leave_seconds` 8.0 and `inactive_seconds` 30.0;
  - `max_session_seconds` 180.0 and `exit_seconds` 3.0;
  - `brightness` 0.4 and `apl_cap_day` 0.12.
- Actors under the default calibration (zone (0.2, 0.2, 0.8, 0.8), `min_height` 0.45):
  - `Person(height=h)` has scale about 0.45 h (0.225 at 0.5, 0.315 at 0.7), so 0.7 against 0.5 is 1.4 times and 0.6 against 0.5 is 1.2 times.
  - Every `Person` height from 0.45 to 0.8 at `x=0.5` is in the zone.
  - `crowd(n)` bodies are out of the zone.
  - `Person.present(t)` is `t >= arrive and t < leave`, and `scene` frame `i` is at `t = i / 30`.
- Timings on this Mac, idle, on the thread's CPU clock:
  - `Juice.render` with a full pool, shake, flash, pop and banner at 64x64: 0.10 ms median.
  - A whole runner tick through `run_headless`: 0.33-0.37 ms mean and 0.34-0.40 ms p95 at both layouts. The governor is about half of it (48-54%): 0.19-0.20 ms on the strobe's holding path and 0.16-0.18 ms on the static picture.
  - `test_distance_keeps_up_with_the_preview`: 8.4 ms median on `thread_time`, 8.2 ms on `perf_counter`.
  - The whole suite: about 20 s.
- `ruff check --select F` passes on every file this plan writes, and `--select E501 --line-length 120` does too.
- The whole plan's code was replayed from this file's text in a fresh clone of `ee6780b`, task by task (tests first, then code, then the commit). Every failure and count below was observed there.
- The replay also checked:
  - the full suite under `-W error` and under `PYTHONHASHSEED` 1, 2 and 3;
  - that `git diff ee6780b -- tests/ | grep '^-[^-]'` prints exactly the four `perf_counter` lines of loop decision 26, and nothing else;
  - that importing `arcade.juice`, `arcade.runner` and `arcade.headless` loads none of `cv2`, `mediapipe`, `sounddevice` and `pygame`.
- **Timing under parallel agent load.** In about 40 full-suite runs while drafting round 0, one run under `PYTHONHASHSEED=3` failed one test, and its name was not captured. The cause was timing under the load of parallel agents. The round-1 review reproduced it: with 8 busy-loop hogs, 14 of 33 full-suite runs failed, every one on a `perf` test timed with `perf_counter` (`test_flash.py`'s governor median, the new budget test, and once `test_look.py`'s distance look). No hash-order dependence was found.
  - Loop decision 26 moves every `perf` test to `thread_time`.
  - The load test, on this Mac (4 performance and 4 efficiency cores), in the replay clone, with other agents also running (load average 24 to 81):
    - **8 busy-loop hogs, one suite at a time:** 12 of 12 full-suite runs green under `-W error`, seeds 1, 2, 3 and random, about 39 s each. The round-2 reviewer's same setup gave 5 of 6: one run failed on the existing `test_governor_under_half_ms_at_128x32` alone. So that test can fail at one suite too; the new budget test and the Juice timing did not fail in any run.
    - **8 hogs and three suites at once** (the review's setup): 29 of 36 runs green. All 7 failures are the existing `test_governor_under_half_ms_at_128x32`, with medians of 0.51-0.60 ms against its 0.5 ms. The new budget test, the Juice render timing and the distance look never failed.
    - **Same setup, clocks side by side,** rounds interleaved: `thread_time` failed 1 of 12 runs (the governor test), `perf_counter` 7 of 12 (the budget test 6 times, the distance look once).
    - **Why the governor test can still fail.** The governor takes 0.21 ms of CPU a frame on a performance core, and about 0.55 ms on an efficiency core. When the scheduler keeps the test's thread on an efficiency core for most of its 30 frames, the median is over 0.5 ms on any clock. `thread_time` removes the waits, not the slower core. A thread QoS of user-interactive did not keep it on a performance core. The Pi 5's four cores are all the same, so this is a Mac test-machine effect, not a product one. This plan keeps the operator's clock-only change and does not touch the test further. If it fails in a full-suite run, the rule below applies: rerun `-m perf` alone on a quiet machine.
    - The hang checks in `test_canvas.py` and `test_look.py` line 91 (which keep `perf_counter`) never failed in any of these 60 runs.
  - If a full-suite run still fails on a `perf` test, rerun `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs -m perf` alone on a quiet machine, and record both results and the load average, before calling the failure a regression.
- Mutations were run with `PYTHONDONTWRITEBYTECODE=1` against the task's tests. There were 97 in all:
  - **Runner and harness, 30.** The constants, the session rules, the cap's phase and players rules, `waiting`, the exit block, `state()`'s order, the logging rate limits, the scores-before-reset order, the source checks, the crash fade and hiding, the title-card lobby, `run_headless`'s clock, strict and raw, and `helpers.run`'s ticks. On the first run 4 survived, and each now has an assert: `PROMPT_SECONDS`, the players cap, `MAX_DT`, and the broken lobby being called again. All 30 fail now.
  - **Tick path and lock, 8.** The tick order, the exit reset on launch, the exit grace, the frozen skip, blobs for games, the re-acquire's "new id" rule (it survived until the body-beside-the-player case was added), and updating the exit hold only outside the lobby. The last survives and is equivalent while the launch reset is there.
  - **Moving blobs, 5.** Any in-zone blob as evidence, `BLOB_SPEED` 0.5, the leave rule on any blob, a fixed 1/30 s between captures, and no zone check. On the first run 2 survived; the slow-drift and outside-the-zone cases now kill them.
  - **Juice, 20.** The pool, shake step, flash gap, burst gap (0.1, 0.3, 0.4 and 0.6), the flash gap counted from the start instead of the end, the flash fading, a smaller shake overriding, a shake's fill, the pop rise, the banner box, celebrate's second wave, echo's player check, freeze extension, `MAX_POPS`, `n` capped before the ring, and `dt` checked. On the first run 2 survived (`MAX_POPS` and the cap on `n`), and each now has an assert. All 20 fail now.
  - **Plan review round 2, 11.** The finite check, the future check, `CLOCK_SLACK` at 0, 0.3 and 3600, the camera and the audio stamp checks each dropped, the launch guard dropped, the guard also refusing during the crash icon, the request read outside the lobby guard, and the request not cleared. All 11 fail.
  - **Plan review round 1, 23.** B1 (truthy `active`, and `is True`), T4, T6, T7, T8, T11, C6, C7, C15, `debug_state` unguarded, E5, E6, E9, E10, S1, and the N4 and N7 changes (the launch's empty state, the icon ended by a launch, the str check, `t` and `camera_t` not moved, the shape check, the motion check). All 23 fail.

## File map

```
arcade/sensed.py                Task 1  C22 TORSO_FLOOR; raise_line falls back to the nose under it
arcade/scores.py                Task 1  C25 SessionLog.append casts players, checks names, never raises on write; C29 bad "previous" counted
arcade/input.py                 Task 1  C27 caller rule docstring; C29 _float, _positive, OneEuro casts its samples
tests/arcade/test_sensed.py     Task 1  one test appended
tests/arcade/test_scores.py     Task 1  two tests appended
tests/arcade/test_input.py      Task 1  one test appended
tests/arcade/test_flash.py      Task 1  lines 500, 502: perf_counter -> thread_time (clock only)
tests/arcade/test_look.py       Task 1  lines 172, 174: perf_counter -> thread_time (clock only)
arcade/juice.py                 Task 2  new: Juice, marker_x, PLAYER_COLORS
tests/arcade/test_juice.py      Task 2  new
arcade/runner.py                Task 3  new: SessionResult, LobbyLike, PlayerLock, Presence, moving_blob, Runner
arcade/headless.py              Task 3  new: OPENING_NIGHT, RecordingDisplay; Task 4 adds NullLobby, run_headless
tests/arcade/helpers.py         Task 3  new: make_cfg, SpyGame, spy, StubLobby, FakeClock; Task 4 adds run
tests/arcade/test_runner.py     Task 3  new
tests/arcade/test_headless.py   Task 4  new
```

---

### Task 1: Carried fixes the runner depends on (C22, C25, C26, C27 docstring, C29 part)

**Files:**
- Modify: `arcade/sensed.py`, `arcade/scores.py`, `arcade/input.py` (whole files below)
- Test: `tests/arcade/test_sensed.py`, `tests/arcade/test_scores.py`, `tests/arcade/test_input.py` (whole files below)
- Modify (clock only): `tests/arcade/test_flash.py:500,502` and `tests/arcade/test_look.py:172,174` (the script in Step 1)

**Interfaces:**
- Consumes: iteration 4's `arcade.input`, `arcade.scores` and `arcade.sensed`, and `look.is_real`.
- Produces:
  - `sensed.TORSO_FLOOR = 0.1`. `Body.raise_line` uses the shoulders only when `torso >= TORSO_FLOOR * height`.
  - `SessionLog.append(game: str, layout: str, start: datetime, duration, players: int, score, reason) -> dict`:
    - it raises `ValueError` for a non-string `game` or `layout`, or for `players` that is a bool, not integral, or negative;
    - it stores `int(players)`;
    - it never raises for a write that fails, whether the failure is `OSError`, `TypeError` or `ValueError`.
  - `OneEuro.__call__(x, t) -> float` always returns a float. A non-real or overflowing sample returns the last value, or NaN before the first.
  - `capture_grace`, `Hold`, `Edge`, `Cursor` and `OneEuro` raise `ValueError` for a huge int, where they used to raise `OverflowError` or pass it.

  No name or signature is removed.

Changes to existing test lines: four, all clock-only, and nothing else. Four tests are appended at the ends of the three modules. The sensed test imports `TORSO_FLOOR` inside the function, so the module's import lines are unchanged and the new test fails on its own rather than at collection.

The four changed lines are the timing lines of the two existing `perf` tests, `test_governor_under_half_ms_at_128x32` (`test_flash.py:500,502`) and `test_distance_keeps_up_with_the_preview` (`test_look.py:172,174`). Each `time.perf_counter()` becomes `time.thread_time()`. The thresholds (0.5 ms and 1/30 s), the medians, the seeds and every assert stay as they are. Why (plan review B2, operator decision, loop decision 26):
- `perf_counter` is wall time, so it counts the time the test thread waits for a CPU. Under parallel agent load, 8 busy-loop hogs made 14 of 33 full-suite runs fail, all on these timings.
- `thread_time` is this thread's CPU time: what the code costs, not what the machine is doing. The code measured runs in the calling thread (numpy's 128x32 work does not go to other threads: the distance look reads 8.4 ms on `thread_time` and 8.2 ms on `perf_counter` on a quiet machine), so the CPU clock sees all of it.
- The limit a test asserts is unchanged, so no assert is weakened; only the clock that feeds it changes.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_sensed.py`:

```python
import dataclasses
import math

import numpy as np
import pytest

from arcade.calibration import Calibration
from arcade.sensed import (LEFT_ANKLE, LEFT_EAR, LEFT_ELBOW, LEFT_EYE, LEFT_HIP, LEFT_KNEE,
                           LEFT_SHOULDER, LEFT_WRIST, NOSE, RIGHT_ANKLE, RIGHT_EAR, RIGHT_ELBOW,
                           RIGHT_EYE, RIGHT_HIP, RIGHT_KNEE, RIGHT_SHOULDER, RIGHT_WRIST, SKELETON,
                           Audio, Blob, Body, Keypoint, Sensed, place, place_blob)


def kps(**over):
    pts = [Keypoint(0.5, 0.2 + i * 0.04) for i in range(17)]
    for idx, kp in over.items():
        pts[int(idx)] = kp
    return tuple(pts)


# A standing figure: shoulders at y 0.4, 0.2 apart; hips at y 0.7, so the torso is 0.3 and the raise
# line is at 0.4 - 0.3 * 0.3 = 0.31. The nose (0.22) is above it, the wrists hang at hip height.
FIGURE = {
    NOSE: Keypoint(0.5, 0.22), LEFT_EYE: Keypoint(0.48, 0.2), RIGHT_EYE: Keypoint(0.52, 0.2),
    LEFT_EAR: Keypoint(0.46, 0.21), RIGHT_EAR: Keypoint(0.54, 0.21),
    LEFT_SHOULDER: Keypoint(0.4, 0.4), RIGHT_SHOULDER: Keypoint(0.6, 0.4),
    LEFT_ELBOW: Keypoint(0.37, 0.55), RIGHT_ELBOW: Keypoint(0.63, 0.55),
    LEFT_WRIST: Keypoint(0.35, 0.7), RIGHT_WRIST: Keypoint(0.65, 0.7),
    LEFT_HIP: Keypoint(0.45, 0.7), RIGHT_HIP: Keypoint(0.55, 0.7),
    LEFT_KNEE: Keypoint(0.45, 0.85), RIGHT_KNEE: Keypoint(0.55, 0.85),
    LEFT_ANKLE: Keypoint(0.45, 0.95), RIGHT_ANKLE: Keypoint(0.55, 0.95),
}
BOX = (0.3, 0.2, 0.7, 1.0)


def figure(over=None, box=BOX, **fields):
    pts = dict(FIGURE)
    pts.update(over or {})
    return Body(1, box, tuple(pts[i] for i in range(17)), **fields)


def test_body_requires_17_keypoints():
    with pytest.raises(ValueError):
        Body(1, (0, 0, 1, 1), tuple(Keypoint(0, 0) for _ in range(5)))


def test_body_cleans_bad_keypoints():
    pts = kps(**{str(LEFT_WRIST): Keypoint(1.7, -0.2, 0.9), str(RIGHT_WRIST): Keypoint(math.nan, 0.5, 0.9)})
    b = Body(1, (0, 0, 1, 1), pts)
    assert b.left_wrist == Keypoint(1.0, 0.0, 0.0)
    assert b.right_wrist.conf == 0.0 and b.right_wrist.x == 0.0


def test_clean_clamps_confidence_and_rejects_non_finite():
    pts = kps(**{str(NOSE): Keypoint(0.5, 0.2, 5.0), str(LEFT_EYE): Keypoint(0.5, 0.2, -1.0),
                 str(RIGHT_EYE): Keypoint(0.5, 0.2, math.nan), str(LEFT_EAR): Keypoint(math.inf, 0.2, 0.9),
                 str(RIGHT_EAR): Keypoint(0.5, -math.inf, 0.9)})
    b = Body(1, (0, 0, 1, 1), pts)
    assert b.keypoints[NOSE] == Keypoint(0.5, 0.2, 1.0)
    assert b.keypoints[LEFT_EYE] == Keypoint(0.5, 0.2, 0.0)
    assert b.keypoints[RIGHT_EYE] == Keypoint(0.0, 0.0, 0.0)
    assert b.keypoints[LEFT_EAR] == Keypoint(1.0, 0.2, 0.0)
    assert b.keypoints[RIGHT_EAR] == Keypoint(0.5, 0.0, 0.0)


def test_body_defaults_and_measured_scale():
    b = figure()
    assert (b.vx, b.vy, b.in_zone, b.zone_x, b.zone_y, b.seen_ago) == (0.0, 0.0, True, 0.5, 0.5, 0.0)
    assert b.scale == pytest.approx(0.48)            # nose to mid-hip
    assert figure(scale=0.7).scale == 0.7            # a given scale is kept
    assert b.shoulder_mid == Keypoint(0.5, 0.4) and b.hip_mid == Keypoint(0.5, 0.7)
    assert b.shoulder_width == pytest.approx(0.2) and b.torso == pytest.approx(0.3)
    assert b.center == (0.5, 0.6) and b.height == pytest.approx(0.8)
    assert b.nose == b.keypoints[NOSE] and b.confidence == 1.0
    assert Body(1, (0, 0, 1, 1), kps()).scale == pytest.approx(0.46)


def test_raise_line_is_above_shoulders():
    b = figure()
    assert b.raise_line == pytest.approx(0.31)
    assert b.raised_wrist is None and not b.both_hands_up
    low = 0.4 - 0.1 * 0.3                             # 0.1 torso above the shoulders: not raised
    assert figure({RIGHT_WRIST: Keypoint(0.65, low)}).raised_wrist is None
    high = 0.4 - 0.4 * 0.3                            # 0.4 torso above: raised
    up = figure({RIGHT_WRIST: Keypoint(0.65, high)})
    assert up.raised_wrist == Keypoint(0.65, high) and not up.both_hands_up
    assert figure({RIGHT_WRIST: Keypoint(0.65, 0.3)}).raised_wrist is not None   # below the nose, still raised
    both = figure({LEFT_WRIST: Keypoint(0.35, 0.1), RIGHT_WRIST: Keypoint(0.65, high)})
    assert both.both_hands_up and both.raised_wrist == Keypoint(0.35, 0.1)      # the higher one
    faint = figure({RIGHT_WRIST: Keypoint(0.65, 0.1, 0.1)})
    assert faint.raised_wrist is None


def test_nose_fallback_only_without_shoulders():
    hidden = {LEFT_SHOULDER: Keypoint(0.4, 0.4, 0.0), RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0)}
    b = figure(hidden)
    assert b.shoulder_mid is None and b.raise_line == pytest.approx(0.22)
    assert figure({**hidden, RIGHT_WRIST: Keypoint(0.65, 0.25)}).raised_wrist is None
    assert figure({**hidden, RIGHT_WRIST: Keypoint(0.65, 0.18)}).raised_wrist is not None
    one = figure({RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0)})    # one shoulder still sets the line
    assert one.shoulder_mid == Keypoint(0.5, 0.4)                 # its y; x from the hips
    assert one.raise_line == pytest.approx(0.31)
    no_hips = {RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0), LEFT_HIP: Keypoint(0.45, 0.7, 0.0),
               RIGHT_HIP: Keypoint(0.55, 0.7, 0.0)}
    assert figure(no_hips).shoulder_mid == Keypoint(0.5, 0.4)    # x from the nose
    alone = {**no_hips, NOSE: Keypoint(0.5, 0.22, 0.0)}
    assert figure(alone).shoulder_mid == Keypoint(0.4, 0.4)      # nothing else: the shoulder itself
    one_hip = {RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0), RIGHT_HIP: Keypoint(0.55, 0.7, 0.0)}
    assert figure(one_hip).shoulder_mid == Keypoint(0.5, 0.4)    # one hip is off centre too: the nose


def test_one_shoulder_does_not_move_the_centre():
    # Shoulders 0.24 apart for the 0.3 torso: the 1.25 ratio TORSO_PER_SHOULDER_WIDTH assumes, as actors use.
    up = {LEFT_SHOULDER: Keypoint(0.38, 0.4), RIGHT_WRIST: Keypoint(0.7, 0.1)}
    seen = figure({**up, RIGHT_SHOULDER: Keypoint(0.62, 0.4, 0.31)})
    lost = figure({**up, RIGHT_SHOULDER: Keypoint(0.62, 0.4, 0.29)})    # crosses MIN_CONF
    assert abs(seen.anchor.x - lost.anchor.x) < 0.03
    assert abs(seen.cursor[0] - lost.cursor[0]) < 0.03
    assert abs(seen.cursor[1] - lost.cursor[1]) < 0.03
    cal = Calibration()
    assert abs(place(seen, cal).zone_x - place(lost, cal).zone_x) < 0.03


def test_hooded_body_still_raises():
    hood = {NOSE: Keypoint(0.5, 0.22, 0.0), LEFT_EYE: Keypoint(0.48, 0.2, 0.0),
            RIGHT_EYE: Keypoint(0.52, 0.2, 0.0)}
    b = figure({**hood, RIGHT_WRIST: Keypoint(0.65, 0.2)})
    assert b.raise_line == pytest.approx(0.31)
    assert b.raised_wrist == Keypoint(0.65, 0.2)
    assert b.scale == pytest.approx(0.3 * 1.5)        # no nose: 1.5 torso lengths


def test_body_with_nothing_confident_never_raises_or_fails():
    blank = Body(1, BOX, tuple(Keypoint(0.5, 0.5, 0.0) for _ in range(17)))
    assert blank.raise_line is None and blank.raised_wrist is None and not blank.both_hands_up
    assert blank.cursor is None and blank.anchor is None and blank.scale == 0.0
    assert blank.reach(Keypoint(0.5, 0.6)) == pytest.approx((0.5, 0.5))
    placed = place(blank, Calibration())
    assert placed.in_zone and (placed.zone_x, placed.zone_y) == pytest.approx((0.5, 2 / 3))


def test_sensed_defaults():
    s = Sensed(t=1.0)
    assert s.bodies == () and s.blobs == () and s.audio == Audio()
    assert s.motion.shape == (0, 0) and s.motion.dtype == bool
    grid = np.zeros((4, 8), bool)
    held = Sensed(0.0, motion=grid)
    with pytest.raises(ValueError, match="read-only"):
        held.motion[0, 0] = True                     # one grid is shared by the ticks that hold it
    assert not held.with_motion((4, 2)).motion.flags.writeable
    assert grid.flags.writeable                      # the record holds a read-only view, not the caller's array
    assert Sensed(0.0, motion=None).motion.shape == (0, 0)
    assert (s.camera_t, s.camera_fresh, s.camera_seq) == (0.0, False, 0)
    assert s.player is None and s.player2 is None and not s.present
    assert not hasattr(s, "primary")
    a = Audio()
    assert (a.level, a.level_smooth, a.peak, a.voice, a.voice_db, a.floor_db) == (0, 0, 0, 0, -90.0, -90.0)
    assert not (a.clap or a.onset or a.beat) and a.bpm is None


def test_with_motion_resamples_never_rasterizes():
    b = figure()
    s = Sensed(0.0, bodies=(b,)).with_motion((8, 4))
    assert s.motion.shape == (4, 8) and s.motion.dtype == bool and not s.motion.any()
    given = np.ones((4, 8), bool)
    held = Sensed(0.0, motion=given)
    assert held.with_motion((8, 4)) is held and np.shares_memory(held.motion, given)
    small = np.array([[True, False], [False, True]])
    up = Sensed(0.0, motion=small).with_motion((8, 4)).motion
    assert up.shape == (4, 8)
    assert up[:2, :4].all() and up[2:, 4:].all() and not up[:2, 4:].any() and not up[2:, :4].any()
    grid = np.zeros((64, 128), bool)
    grid[33, 101] = True
    down = Sensed(0.0, motion=grid).with_motion((64, 32)).motion
    assert down.shape == (32, 64) and down.sum() == 1 and down[16, 50]    # one lit cell survives shrinking


def test_reach_box_corners():
    b = figure()     # shoulder mid (0.5, 0.4), shoulders 0.2 apart, torso 0.3, hips at 0.7
    top = 0.4 - 1.05 * 0.3
    assert b.reach(Keypoint(0.2, top)) == pytest.approx((0.0, 0.0))
    assert b.reach(Keypoint(0.8, 0.7)) == pytest.approx((1.0, 1.0))
    assert b.reach(Keypoint(0.5, (top + 0.7) / 2)) == pytest.approx((0.5, 0.5))
    assert b.reach(Keypoint(0.0, 1.0)) == (0.0, 1.0)                        # clamped
    half = {i: Keypoint(0.5 + (k.x - 0.5) / 2, 0.5 + (k.y - 0.5) / 2) for i, k in FIGURE.items()}
    small = figure(half, box=(0.4, 0.35, 0.6, 0.75))
    wrist = Keypoint(0.7, 0.3)
    assert small.reach(Keypoint(0.5 + (wrist.x - 0.5) / 2, 0.5 + (wrist.y - 0.5) / 2)) == pytest.approx(b.reach(wrist))
    no_shoulders = figure({LEFT_SHOULDER: Keypoint(0.4, 0.4, 0.0), RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0)})
    assert no_shoulders.reach(Keypoint(0.5, 0.6)) == pytest.approx((0.5, 0.5))   # the body box


def test_cursor_is_wrist_further_from_hip():
    right = figure({RIGHT_WRIST: Keypoint(0.8, 0.3), LEFT_WRIST: Keypoint(0.4, 0.65)})
    assert right.cursor == right.reach(right.right_wrist)
    assert right.cursor == pytest.approx((1.0, (0.3 - 0.085) / 0.615))
    left = figure({LEFT_WRIST: Keypoint(0.25, 0.2), RIGHT_WRIST: Keypoint(0.6, 0.72)})
    assert left.cursor == left.reach(left.left_wrist)
    only = figure({RIGHT_WRIST: Keypoint(0.8, 0.3, 0.0), LEFT_WRIST: Keypoint(0.4, 0.65)})
    assert only.cursor == only.reach(only.left_wrist)
    none = figure({RIGHT_WRIST: Keypoint(0.8, 0.3, 0.0), LEFT_WRIST: Keypoint(0.4, 0.65, 0.1)})
    assert none.cursor is None


def test_anchor_order():
    assert figure().anchor == Keypoint(0.5, 0.4)
    hidden = {LEFT_SHOULDER: Keypoint(0.4, 0.4, 0.0), RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0)}
    assert figure(hidden).anchor == Keypoint(0.5, 0.22)
    assert figure({**hidden, NOSE: Keypoint(0.5, 0.22, 0.0)}).anchor == Keypoint(0.5, 0.7)


def test_place_uses_calibration_zone():
    b = figure()
    placed = place(b, Calibration())                  # zone (0.2, 0.2, 0.8, 0.8), min_height 0.45
    assert placed.in_zone
    assert (placed.zone_x, placed.zone_y) == pytest.approx((0.5, (0.4 - 0.2) / 0.6))
    assert placed.keypoints == b.keypoints and placed.scale == b.scale and b.zone_y == 0.5
    right = place(b, Calibration(zone=(0.6, 0.0, 1.0, 1.0)))
    assert not right.in_zone and right.zone_x == 0.0                       # clamped to the zone edge
    short = place(figure(box=(0.3, 0.2, 0.7, 0.6)), Calibration())         # 0.4 tall, under min_height
    assert not short.in_zone
    tall_enough = place(figure(box=(0.3, 0.2, 0.7, 0.65)), Calibration())
    assert tall_enough.in_zone


def test_place_blob():
    assert place_blob(Blob(0.5, 0.5, 0.03, (255, 255, 255)), Calibration()).in_zone
    assert not place_blob(Blob(0.05, 0.1, 0.03, (255, 255, 255)), Calibration()).in_zone
    assert Blob(0.1, 0.2, 0.05, (255, 0, 0)).in_zone


def test_skeleton_indices_valid():
    assert all(0 <= a < 17 and 0 <= b < 17 for a, b in SKELETON)
    assert Blob(0.1, 0.2, 0.05, (255, 0, 0)).color == (255, 0, 0)


def test_sensed_and_audio_take_keywords_after_t():
    # C12: revision 2 called Sensed(t, bodies, blobs, motion, audio); in spec 5's field order that binds
    # the bodies to camera_t without an error. Audio(0.8, 1.0) would put 1.0 in level_smooth.
    with pytest.raises(TypeError):
        Sensed(1.0, (figure(),))
    with pytest.raises(TypeError):
        Audio(0.8, 1.0)
    assert [f.name for f in dataclasses.fields(Sensed) if not f.kw_only] == ["t"]
    assert all(f.kw_only for f in dataclasses.fields(Audio))
    s = Sensed(1.0, bodies=(figure(),), audio=Audio(level=0.8, level_smooth=1.0))
    assert s.bodies[0].id == 1 and s.camera_t == 0.0 and s.audio.level_smooth == 1.0


def test_one_shoulder_without_hips_uses_the_nose_line():
    # C14: one shoulder and no hip give no torso, so a line from the shoulders would sit on the shoulder.
    no_hips = {RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0), LEFT_HIP: Keypoint(0.45, 0.7, 0.0),
               RIGHT_HIP: Keypoint(0.55, 0.7, 0.0)}
    b = figure(no_hips)
    assert b.shoulder_mid is not None and b.torso == 0.0
    assert b.raise_line == pytest.approx(0.22)                                           # the nose
    assert figure({**no_hips, RIGHT_WRIST: Keypoint(0.65, 0.395)}).raised_wrist is None   # a hair over the shoulder
    assert figure({**no_hips, RIGHT_WRIST: Keypoint(0.65, 0.25)}).raised_wrist is None    # under the nose
    assert figure({**no_hips, RIGHT_WRIST: Keypoint(0.65, 0.18)}).raised_wrist == Keypoint(0.65, 0.18)
    assert figure({**no_hips, LEFT_WRIST: Keypoint(0.35, 0.1), RIGHT_WRIST: Keypoint(0.65, 0.18)}).both_hands_up
    blind = figure({**no_hips, NOSE: Keypoint(0.5, 0.22, 0.0), RIGHT_WRIST: Keypoint(0.65, 0.1),
                    LEFT_WRIST: Keypoint(0.35, 0.1)})
    assert blind.raise_line is None and blind.raised_wrist is None and not blind.both_hands_up


def test_blob_coordinates_are_clamped():
    # C16: headlamps() crosses from x -0.05 to 1.05; a consumer mapping x to a pixel would index at -1.
    b = Blob(-0.05, 1.2, 0.02, (255, 250, 235))
    assert (b.x, b.y) == (0.0, 1.0)
    assert Blob(math.nan, 0.5, 0.02, (255, 0, 0)).x == 0.0 and Blob(0.3, math.inf, 0.02, (255, 0, 0)).y == 1.0
    assert Blob(None, 0.5, 0.02, (255, 0, 0)).x == 0.0                                  # as a keypoint's None
    assert place_blob(b, Calibration()).x == 0.0
    assert Blob(0.25, 0.75, 0.02, (255, 0, 0)) == Blob(0.25, 0.75, 0.02, (255, 0, 0), True)   # in range: kept


def test_raise_line_needs_a_torso_over_the_floor():
    # C22: side-on at the bar the shoulders overlap (0.03 apart) and the counter hides the hips. The torso from
    # the shoulder width is 0.0375, under 0.1 of the 0.8 box, and a line from it would sit a hair (0.011) above
    # the shoulders, so a wrist at the collarbone would count as raised.
    from arcade.sensed import TORSO_FLOOR
    side = {LEFT_SHOULDER: Keypoint(0.485, 0.4), RIGHT_SHOULDER: Keypoint(0.515, 0.4),
            LEFT_HIP: Keypoint(0.45, 0.7, 0.0), RIGHT_HIP: Keypoint(0.55, 0.7, 0.0)}
    b = figure(side)
    assert TORSO_FLOOR == 0.1
    assert b.torso == pytest.approx(0.0375) and b.torso < TORSO_FLOOR * b.height
    assert b.raise_line == pytest.approx(0.22)                                           # the nose
    assert figure({**side, RIGHT_WRIST: Keypoint(0.65, 0.38)}).raised_wrist is None      # at the collarbone
    assert figure({**side, RIGHT_WRIST: Keypoint(0.65, 0.18)}).raised_wrist == Keypoint(0.65, 0.18)
    assert figure({**side, NOSE: Keypoint(0.5, 0.22, 0.0)}).raise_line is None           # no nose either: None
    near = figure(side, box=(0.3, 0.6, 0.7, 0.95))              # a 0.35 box: the floor is 0.035, the torso passes
    assert near.raise_line == pytest.approx(0.4 - 0.3 * 0.0375)
    assert figure().raise_line == pytest.approx(0.31)                                     # a full torso is unchanged
```

`tests/arcade/test_scores.py`:

```python
import json
import logging
import math
from datetime import datetime

import numpy as np
import pytest

import arcade.scores as scores_module
from arcade.scores import REASONS, GameScores, Scores, SessionLog, night_of


class Clock:
    """A settable local clock."""

    def __init__(self, when: str):
        self.now = datetime.fromisoformat(when)

    def __call__(self) -> datetime:
        return self.now

    def set(self, when: str) -> None:
        self.now = datetime.fromisoformat(when)


def test_scores_record_and_persist(tmp_path):
    p = tmp_path / "d" / "scores.json"
    clock = Clock("2026-11-11T21:00")
    s = Scores(p, clock)
    assert s.best("dodge", "128x32") is None
    assert s.record("dodge", "128x32", 0.4) is True
    assert s.record("dodge", "128x32", 0.3) is False
    assert s.record("dodge", "128x32", 0.4) is False                 # a tie is not a new best
    assert s.record("dodge", "128x32", 0.5) is True
    assert s.best("dodge", "128x32") == 0.5
    assert Scores(p, clock).best("dodge", "128x32") == 0.5
    assert json.loads(p.read_text()) == {"dodge": {"128x32": {"best": 0.5, "when": "2026-11-11T21:00:00"}}}
    assert not (tmp_path / "d" / "scores.json.tmp").exists()


def test_scores_write_fsyncs_then_renames(tmp_path, monkeypatch):
    calls = []
    real_fsync, real_replace = scores_module.os.fsync, scores_module.os.replace
    p = tmp_path / "scores.json"

    def fsync(fd):
        calls.append(("fsync", (tmp_path / "scores.json.tmp").read_text()))
        real_fsync(fd)

    def replace(src, dst):
        calls.append(("replace", str(src), str(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(scores_module.os, "fsync", fsync)
    monkeypatch.setattr(scores_module.os, "replace", replace)
    Scores(p, Clock("2026-11-11T21:00")).record("pong", "64x64", 7)
    assert [c[0] for c in calls] == ["fsync", "replace"]
    assert json.loads(calls[0][1])["pong"]["64x64"]["best"] == 7.0   # the whole file was on disk before the rename
    assert calls[1][1:] == (str(tmp_path / "scores.json.tmp"), str(p))
    calls.clear()
    monkeypatch.setattr(scores_module.os, "fsync", lambda fd: calls.append(("fsync", log.read_text())))
    log = tmp_path / "sessions.jsonl"
    SessionLog(log).append("pong", "64x64", datetime(2026, 11, 11, 21), 30.0, 1, 7, "done")
    assert len(calls) == 1 and json.loads(calls[0][1])["score"] == 7.0  # the line was written before the fsync


def test_scores_survive_corrupt_file(tmp_path, caplog):
    p = tmp_path / "scores.json"
    clock = Clock("2026-11-11T21:00")
    for text in ("{not json", "[1, 2]", '{"x": 5}'):
        p.write_text(text)
        with caplog.at_level(logging.WARNING, logger="arcade"):
            s = Scores(p, clock)
        assert s.best("x", "128x32") is None and caplog.records, text
        caplog.clear()
    good = {"best": 3.0, "when": "2026-11-11T20:00:00"}
    p.write_text(json.dumps({"x": {"128x32": good, "64x64": {"best": "high", "when": "x"}},
                             "y": {"128x32": {"best": math.inf, "when": "2026-11-11T20:00:00"},
                                   "64x64": {"best": 2.0, "when": "last night"}}},
                            allow_nan=True))
    with caplog.at_level(logging.WARNING, logger="arcade"):
        s = Scores(p, clock)
    assert [r.getMessage().split()[1] for r in caplog.records] == ["3"]   # "ignoring 3 malformed entries"
    assert s.best("x", "128x32") == 3.0 and s.best("x", "64x64") is None and s.best("y", "128x32") is None
    assert s.best("y", "64x64") is None and s.last_night("y", "64x64") is None
    assert s.record("x", "64x64", 1.0)
    p.write_text(json.dumps({"x": {"128x32": {"best": 3, "when": "2026-11-11T20:00:00"},
                                   "64x64": {"best": 1.0, "when": 5}}}))
    with caplog.at_level(logging.WARNING, logger="arcade"):
        s = Scores(p, clock)                                         # a "when" that is not a string is dropped
    assert s.best("x", "64x64") is None and type(s.best("x", "128x32")) is float


def test_scores_in_memory_never_writes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def refuse(*args, **kwargs):
        raise AssertionError("Scores(None) and SessionLog(None) must not touch the disk")

    monkeypatch.setattr(scores_module.os, "replace", refuse)
    monkeypatch.setattr(scores_module.os, "fsync", refuse)
    s = Scores(None, Clock("2026-11-11T21:00"))
    assert s.record("tug", "128x32", 12) and s.best("tug", "128x32") == 12.0
    log = SessionLog(None)
    log.append("tug", "128x32", datetime(2026, 11, 11, 21), 60.0, 2, 12, "done")
    assert log.records[0]["reason"] == "done"
    assert list(tmp_path.iterdir()) == []


def test_scores_per_layout():
    s = Scores(None, Clock("2026-11-11T21:00"))
    assert s.record("flap", "128x32", 10)
    assert s.record("flap", "64x64", 4)                              # the other layout has its own best
    assert s.best("flap", "128x32") == 10.0 and s.best("flap", "64x64") == 4.0 and s.best("pong", "64x64") is None
    view = s.for_game("flap", "64x64")
    assert isinstance(view, GameScores) and view.best() == 4.0
    assert view.record(5) and not view.record(3) and s.best("flap", "64x64") == 5.0
    assert s.best("flap", "128x32") == 10.0


def test_scores_roll_over_at_1600():
    clock = Clock("2026-11-11T22:00")
    s = Scores(None, clock)
    view = s.for_game("swat", "128x32")
    assert view.record(50)
    clock.set("2026-11-12T03:00")                                    # the same night, after midnight
    assert view.best() == 50.0 and not view.record(40) and view.last_night() is None
    clock.set("2026-11-12T15:59:59")
    assert view.best() == 50.0
    clock.set("2026-11-12T16:00")                                    # a new night
    assert view.best() is None and view.last_night() == 50.0
    assert view.record(20) and view.best() == 20.0 and view.last_night() == 50.0
    assert view.record(30) and view.last_night() == 50.0             # a second best tonight keeps last night
    clock.set("2026-11-13T17:00")                                    # two nights on: last night is the 12th's
    assert view.best() is None and view.last_night() == 30.0
    clock.set("2026-11-15T17:00")                                    # nights without a record: none
    assert view.last_night() is None
    assert night_of(datetime(2026, 11, 12, 1)) == night_of(datetime(2026, 11, 11, 16)) == datetime(2026, 11, 11).date()
    assert night_of(datetime(2026, 11, 11, 15, 59)) == datetime(2026, 11, 10).date()


def test_scores_last_night_survives_a_restart(tmp_path):
    p = tmp_path / "scores.json"
    clock = Clock("2026-11-11T23:00")
    Scores(p, clock).record("tug", "128x32", 9)
    clock.set("2026-11-12T20:00")
    Scores(p, clock).record("tug", "128x32", 4)
    s = Scores(p, clock)
    assert s.best("tug", "128x32") == 4.0 and s.last_night("tug", "128x32") == 9.0
    clock.set("2026-11-13T20:00")
    Scores(p, clock).record("tug", "128x32", 5)
    entry = json.loads(p.read_text())["tug"]["128x32"]
    assert entry["previous"] == {"best": 4.0, "when": "2026-11-12T20:00:00"}   # one night back, never nested


def test_scores_margin():
    s = Scores(None, Clock("2026-11-11T21:00"))
    roar = s.for_game("strongman", "128x32")
    assert roar.record(-30.0, margin=10.0)                           # the first of the night needs no margin
    assert not roar.record(-21.0, margin=10.0) and roar.best() == -30.0
    assert roar.record(-20.0, margin=10.0) and roar.best() == -20.0  # exactly 10 dB more is enough
    for bad in (-1.0, math.nan, math.inf, None, np.True_):
        with pytest.raises(ValueError):
            roar.record(0.0, margin=bad)
    assert roar.record(np.float32(-5.0), margin=np.float32(10.0)) and roar.best() == -5.0


def test_scores_take_numpy_numbers(tmp_path):
    # Games compute scores with numpy: Copy Me's match, Strongman's dB, a Tug tally from np.sum.
    p = tmp_path / "scores.json"
    s = Scores(p, Clock("2026-11-11T21:00"))
    assert s.record("tug", "128x32", np.int64(7)) and s.record("copyme", "64x64", np.float32(0.8))
    assert not s.record("tug", "128x32", np.int64(7)) and s.record("tug", "128x32", np.int64(8))
    assert s.best("tug", "128x32") == 8.0 and type(s.best("tug", "128x32")) is float
    assert s.best("copyme", "64x64") == pytest.approx(0.8)
    assert json.loads(p.read_text())["tug"]["128x32"]["best"] == 8.0
    assert not s.record("tug", "128x32", np.float64(np.nan)) and not s.record("tug", "128x32", np.True_)
    log = SessionLog(tmp_path / "sessions.jsonl")
    record = log.append("tug", "128x32", datetime(2026, 11, 11, 21), np.float32(45.5), 2, np.int64(12), "done")
    assert record["duration"] == 45.5 and record["score"] == 12.0
    assert json.loads((tmp_path / "sessions.jsonl").read_text()) == record


def test_scores_ignore_non_finite_values_and_unwritable_files(tmp_path, caplog):
    s = Scores(None, Clock("2026-11-11T21:00"))
    with caplog.at_level(logging.WARNING, logger="arcade"):
        for bad in (math.nan, math.inf, None, True, "12"):
            assert s.record("pong", "128x32", bad) is False
    assert s.best("pong", "128x32") is None and len(caplog.records) == 5
    blocker = tmp_path / "data"
    blocker.write_text("a file where the data directory should be")
    s = Scores(blocker / "scores.json", Clock("2026-11-11T21:00"))
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="arcade"):
        assert s.record("pong", "128x32", 3) is True                 # a failed write never reaches the game
    assert s.best("pong", "128x32") == 3.0 and caplog.records
    log = SessionLog(blocker / "sessions.jsonl")
    log.append("pong", "128x32", datetime(2026, 11, 11, 21), 30.0, 1, 3, "left")


def test_sessions_log_appends_json_line(tmp_path):
    p = tmp_path / "d" / "sessions.jsonl"
    log = SessionLog(p)
    log.append("paint", "64x64", datetime(2026, 11, 11, 21, 5), 45.5, 1, None, "left")
    log.append("pong", "128x32", datetime(2026, 11, 11, 21, 7), math.nan, 2, math.inf, "done")
    lines = p.read_text().splitlines()
    assert [json.loads(line) for line in lines] == [
        {"game": "paint", "layout": "64x64", "start": "2026-11-11T21:05:00", "duration": 45.5, "players": 1,
         "score": None, "reason": "left"},
        {"game": "pong", "layout": "128x32", "start": "2026-11-11T21:07:00", "duration": None, "players": 2,
         "score": None, "reason": "done"},
    ]
    assert log.records == []                                         # kept in memory only without a path
    assert REASONS == ("done", "left", "inactive", "capped", "exit", "crash")


def test_sessions_log_rejects_unknown_reason(tmp_path):
    p = tmp_path / "sessions.jsonl"
    log = SessionLog(p)
    for reason in ("quit", "", None, "DONE"):
        with pytest.raises(ValueError):
            log.append("pong", "128x32", datetime(2026, 11, 11, 21), 10.0, 1, 3, reason)
    with pytest.raises(ValueError):
        log.append("pong", "128x32", "21:00", 10.0, 1, 3, "done")
    assert not p.exists()
    for reason in REASONS:
        log.append("pong", "128x32", datetime(2026, 11, 11, 21), 10.0, 1, 3, reason)
    assert [json.loads(line)["reason"] for line in p.read_text().splitlines()] == list(REASONS)


def test_sessions_log_casts_numpy_players_and_checks_names(tmp_path, caplog, monkeypatch):
    # C25: the runner counts players with numpy. json.dumps(np.int64(2)) raised TypeError outside the OSError try,
    # so a game crash, logged on the runner's "crash" path, would have become a runner crash.
    p = tmp_path / "sessions.jsonl"
    log = SessionLog(p)
    when = datetime(2026, 11, 11, 21)
    record = log.append("tug", "128x32", when, 30.0, np.int64(2), np.int64(5), "crash")
    assert record["players"] == 2 and type(record["players"]) is int
    assert json.loads(p.read_text()) == record
    memory = SessionLog(None).append("tug", "64x64", when, 30.0, np.uint8(1), None, "done")
    assert type(memory["players"]) is int
    for game, layout, players in ((None, "128x32", 1), ("tug", 64, 1), (b"tug", "128x32", 1), ("tug", "128x32", 1.5),
                                  ("tug", "128x32", True), ("tug", "128x32", "2"), ("tug", "128x32", -1),
                                  ("tug", "128x32", None)):
        with pytest.raises(ValueError):
            log.append(game, layout, when, 30.0, players, 5, "done")
    assert len(p.read_text().splitlines()) == 1

    def refuse(*args, **kwargs):
        raise TypeError("not serializable")

    monkeypatch.setattr(scores_module.json, "dumps", refuse)
    with caplog.at_level(logging.WARNING, logger="arcade"):
        assert log.append("tug", "128x32", when, 30.0, 1, 5, "crash")["reason"] == "crash"   # logged, never raised
    assert caplog.records and len(p.read_text().splitlines()) == 1


def test_scores_drop_huge_ints_and_count_a_bad_previous(tmp_path, caplog):
    # C26 pins it04's ruled deviation (decision 10): _finite catches OverflowError, so a huge int in the file is a
    # malformed entry and record(10**400) is not a best. C29: a malformed "previous" is counted in the warning.
    p = tmp_path / "scores.json"
    clock = Clock("2026-11-11T21:00")
    p.write_text('{"x": {"128x32": {"best": ' + "9" * 400 + ', "when": "2026-11-11T20:00:00"}, '
                 '"64x64": {"best": 2.0, "when": "2026-11-11T20:00:00"}}}')
    with caplog.at_level(logging.WARNING, logger="arcade"):
        s = Scores(p, clock)
    assert [r.getMessage().split()[1] for r in caplog.records] == ["1"]
    assert s.best("x", "128x32") is None and s.best("x", "64x64") == 2.0
    assert s.record("x", "128x32", 10**400) is False and s.best("x", "128x32") is None
    assert s.record("x", "128x32", -10**400) is False
    caplog.clear()
    p.write_text(json.dumps({"x": {"128x32": {"best": 3.0, "when": "2026-11-12T20:00:00",
                                              "previous": {"best": "low", "when": "2026-11-11T20:00:00"}},
                                   "64x64": {"best": 2.0, "when": "2026-11-12T20:00:00",
                                             "previous": {"best": 1.0, "when": "2026-11-11T20:00:00"}}}}))
    clock.set("2026-11-12T21:00")
    with caplog.at_level(logging.WARNING, logger="arcade"):
        s = Scores(p, clock)
    assert [r.getMessage().split()[1] for r in caplog.records] == ["1"]    # the bad "previous"; its entry is kept
    assert s.best("x", "128x32") == 3.0 and s.last_night("x", "128x32") is None
    assert s.best("x", "64x64") == 2.0 and s.last_night("x", "64x64") == 1.0
```

`tests/arcade/test_input.py`:

```python
import math
import zlib

import numpy as np
import pytest

from arcade.input import CAPTURE_GRACE, Cursor, Edge, Hold, OneEuro, capture_grace
from arcade.sensed import LEFT_HIP, LEFT_WRIST, MIN_CONF, RIGHT_HIP, RIGHT_WRIST, Body, Keypoint
from arcade.sources.actors import REAL_NOISE, TICK, Person, degrade, scene

IDS = range(40)          # body ids key degrade's noise (zlib.crc32 of tick, id, joint): 40 different captures


def ticks(values, start=0.0):
    """(value, t) pairs at 30 Hz."""
    return [(v, start + i * TICK) for i, v in enumerate(values)]


def summed(values):
    """(value, t) pairs at 30 Hz with t summed tick by tick, as the runner adds dt: 3 ticks from tick 13 to
    tick 16 come to 0.10000000000000003 s."""
    t, out = 0.0, []
    for v in values:
        out.append((v, t))
        t += TICK
    return out


def test_edge_fires_once():
    e = Edge(grace=0.25)
    fired = [e.update(v, t) for v, t in ticks([False] * 3 + [True] * 10 + [False] * 2 + [True] * 5)]
    assert fired.count(True) == 1 and fired[3]                       # a 67 ms blink is the same press
    e = Edge(grace=0.25)
    fired = [e.update(v, t) for v, t in ticks([True] * 3 + [False] * 7 + [True] * 3 + [False] * 9 + [True])]
    assert [i for i, f in enumerate(fired) if f] == [0, 22]          # 233 ms is a blink, 300 ms a new press
    assert Edge().grace == 0.25 and not Edge().on
    assert Edge(np.float64(0.1)).grace == 0.1 and Hold(np.int64(3), np.float32(0.5)).seconds == 3.0
    assert type(Hold(np.int64(3)).seconds) is float and type(Edge(np.float32(0.5)).grace) is float
    e = Edge(grace=0.1)
    assert [e.update(v, t) for v, t in ((True, 0.0), (False, 0.1), (True, 0.2))] == [True, False, False]
    assert e.on                                                       # false for exactly grace is not more than it
    e = Edge(grace=0.1)
    fired = [e.update(v, t) for v, t in summed([True] * 14 + [False] * 3 + [True])]
    assert [i for i, f in enumerate(fired) if f] == [0]               # false for the grace, summed: not re-armed


def test_hold_tolerates_200ms_dropout_resets_after_300ms():
    h = Hold(1.0, grace=0.25)
    run = ticks([True] * 15 + [False] * 6 + [True] * 20)             # 0.5 s, a 200 ms dropout, then on
    fired = [h.update(v, t) for v, t in run]
    assert [i for i, f in enumerate(fired) if f] == [30]              # 1.0 s after the hold began, not later
    assert h.progress == 1.0 and h.fired
    h = Hold(1.0, grace=0.25)
    run = ticks([True] * 15 + [False] * 9 + [True] * 31)             # a 300 ms dropout ends the hold
    fired, progress = [], []
    for v, t in run:
        fired.append(h.update(v, t))
        progress.append(h.progress)
    assert progress[14] == pytest.approx(14 / 30) and progress[23] == 0.0 and h.start == pytest.approx(24 * TICK)
    assert [i for i, f in enumerate(fired) if f] == [54]              # a whole second after the new hold
    assert Hold(2.0).grace == 0.25
    h, t, fired = Hold(3.0), 0.0, []
    for _ in range(100):
        fired.append(h.update(True, t))
        t += TICK                                                     # the runner adds dt: 90 ticks sum to 2.999...
    assert [i for i, f in enumerate(fired) if f] == [90]
    h = Hold(1.0, grace=0.1)
    fired = [h.update(v, t) for v, t in summed([True] * 14 + [False] * 3 + [True] * 20)]
    assert [i for i, f in enumerate(fired) if f] == [30]              # a dropout of the grace, summed, holds
    h = Hold(1.0)
    h.update(True, 5.0)
    h.update(True, 4.0)
    assert h.progress == 0.0                                          # progress never leaves 0..1


def test_hold_fires_once_per_hold_and_at_zero_seconds():
    h = Hold(0.5, grace=0.0)
    fired = [h.update(v, t) for v, t in ticks([True] * 30 + [False] + [True] * 16)]
    assert [i for i, f in enumerate(fired) if f] == [15, 46]          # held on: once; released: again
    z = Hold(0.0)
    assert z.progress == 0.0 and z.update(True, 5.0) and z.progress == 1.0 and not z.update(True, 5.1)
    assert not z.update(False, 5.2) and z.progress == 1.0            # within the grace the hold stands
    h.reset()
    assert h.start is None and h.progress == 0.0 and not h.fired


def test_capture_grace_is_sized_in_captures():
    assert CAPTURE_GRACE == 5
    assert capture_grace(10) == pytest.approx(0.55) and capture_grace(30) == pytest.approx(5.5 / 30)
    assert capture_grace(10, captures=2) == pytest.approx(0.25)       # the amendment's 0.25 s is two captures
    assert capture_grace(10, captures=0) == pytest.approx(0.05)       # no missed capture: half a capture
    assert capture_grace(np.int64(10)) == pytest.approx(0.55)          # a numpy number is a number
    for bad in (0, -1, math.nan, math.inf, None, True, np.True_):
        with pytest.raises(ValueError):
            capture_grace(bad)
    for bad in (-1, 2.0, True):
        with pytest.raises(ValueError):
            capture_grace(10, captures=bad)
    for make in (lambda v: Edge(v), lambda v: Hold(1.0, v), lambda v: Hold(v), lambda v: Cursor(v)):
        for bad in (-0.1, math.nan, math.inf, None, True, np.True_, "1"):
            with pytest.raises(ValueError):
                make(bad)


def test_exit_hold_survives_spec_noise_with_the_capture_grace():
    # C10: both hands up is seen on about 72 percent of captures at the spec 6.4 noise, and runs of 3 or more
    # misses (0.3 s) end a hold with the amendment's 0.25 s grace. Sized in captures, the 3 s exit holds.
    short = 0
    for body_id in IDS:
        person = Person(0.5, id=body_id).both_hands_up(0.0, 5.0)
        frames = list(degrade(scene(persons=[person], ticks=210), **REAL_NOISE))
        hold, amended = Hold(3.0, grace=capture_grace(10)), Hold(3.0, grace=0.25)
        fired, progress = [], {}
        for s in frames:
            up = bool(s.bodies) and s.bodies[0].both_hands_up
            if hold.update(up, s.t):
                fired.append(s.t)
            short += amended.update(up, s.t) and s.t < 5.0
            progress[round(s.t, 3)] = hold.progress
        assert len(fired) == 1 and 3.15 <= fired[0] < 4.4, (body_id, fired)   # 2 ids in 400 fire after 3.8
        assert progress[5.8] == 0.0, body_id                          # hands down at 5 s: reset within 0.8 s
    assert short < 0.8 * len(IDS), short                              # the 0.25 s grace loses over a fifth


def test_edge_fires_once_per_raise_under_spec_noise():
    # A raised wrist drops out of 15 percent of captures: without a grace, a blink mid-raise is a new press.
    bare = 0
    for body_id in IDS:
        person = Person(0.5, id=body_id).raise_hand(0.5, 1.0).raise_hand(2.5, 1.0)
        edge, raw, count, raw_count = Edge(grace=capture_grace(10)), Edge(grace=0.0), 0, 0
        for s in degrade(scene(persons=[person], ticks=120), **REAL_NOISE):
            up = bool(s.bodies) and s.bodies[0].raised_wrist is not None
            count += edge.update(up, s.t)
            raw_count += raw.update(up, s.t)
        assert count == 2, (body_id, count)
        bare += raw_count > 2
    assert bare > len(IDS) // 2, bare


def test_cursor_keeps_its_hand_through_dropouts():
    # C10: Body.cursor jumps to the hanging wrist whenever the raised one drops out of a capture.
    raw_jumps = 0
    for body_id in IDS:
        person = Person(0.5, id=body_id).raise_hand(0.5, 3.0, "right")
        cursor, last, last_raw = Cursor(grace=capture_grace(10)), None, None
        for s in degrade(scene(persons=[person], ticks=110), **REAL_NOISE):
            body = s.bodies[0] if s.bodies else None
            point = cursor.update(body, s.t)
            if 1.0 <= s.t <= 3.5:
                raw = body.cursor
                assert point is not None and cursor.hand == "right", (body_id, s.t)
                assert last is None or abs(point[0] - last[0]) < 0.1, (body_id, s.t, point, last)
                raw_jumps += last_raw is not None and raw is not None and abs(raw[0] - last_raw[0]) > 0.2
                last, last_raw = point, raw
    assert raw_jumps > len(IDS), raw_jumps                            # the stateless cursor jumps, often


def test_cursor_holds_for_grace_then_lets_go_and_switches_with_hysteresis():
    body = Person(0.5).raise_hand(0.0, 5.0, "right").body_at(1.0, 1)
    c = Cursor(grace=0.25)
    point = c.update(body, 1.0)
    assert c.hand == "right" and point == body.cursor
    assert c.update(None, 1.2) == point and c.update(None, 1.25) == point   # held through the grace
    assert c.update(None, 1.3) is None and c.hand is None
    both = Person(0.5).both_hands_up(0.0, 5.0).body_at(1.0, 1)
    c = Cursor()
    c.update(both, 0.0)
    first = c.hand
    kps = list(both.keypoints)
    other = RIGHT_WRIST if first == "left" else LEFT_WRIST
    kps[other] = Keypoint(kps[other].x, kps[other].y - 0.02)          # a little further: not enough to switch
    c.update(Body(1, both.box, tuple(kps)), 0.1)
    assert c.hand == first
    kps[other] = Keypoint(kps[other].x, 0.0)                          # much further: switch
    c.update(Body(1, both.box, tuple(kps)), 0.2)
    assert c.hand != first and c.hand is not None
    for bad in (0.9, math.inf, None, "2"):
        with pytest.raises(ValueError):
            Cursor(switch=bad)
    assert (Cursor().grace, Cursor().switch) == (0.25, 1.25)
    assert Cursor(switch=np.float32(1.25)).switch == 1.25 and type(Cursor(switch=np.float32(1.25)).switch) is float
    kps = list(both.keypoints)
    kps[LEFT_WRIST], kps[RIGHT_WRIST] = Keypoint(0.25, 0.25), Keypoint(0.75, 0.25)
    kps[LEFT_HIP] = kps[RIGHT_HIP] = Keypoint(0.5, 0.75)
    level = Body(1, both.box, tuple(kps))                             # both wrists exactly as far out
    c = Cursor(switch=1.0)
    c.update(level, 0.0)
    first = c.hand
    c.update(level, 0.1)
    assert c.hand == first                                            # switch 1.0: only a longer reach switches
    c = Cursor(grace=0.1)
    seen = [c.update(body if v else None, t) for v, t in summed([True] * 14 + [False] * 3)]
    assert seen[16] == seen[13] == body.cursor                        # gone for the grace, summed: still held


def test_cursor_measures_reach_as_body_cursor_does():
    # Cursor's first choice of hand is Body.cursor's: an unconfident wrist is not a hand, and a wrist's reach is
    # measured from its own hip only when that hip is confident, else from the hips seen, else the shoulders.
    both = Person(0.5).both_hands_up(0.0, 5.0).body_at(1.0, 1)
    one = Person(0.5).raise_hand(0.0, 5.0, "right").body_at(1.0, 1)
    kps = list(both.keypoints)
    kps[RIGHT_WRIST] = Keypoint(0.99, 0.0, 0.1)                       # far out, but not seen
    unseen = Body(1, both.box, tuple(kps))
    kps = list(one.keypoints)
    kps[LEFT_HIP] = Keypoint(0.0, 0.0, 0.1)                           # a stray, unconfident left hip
    stray = Body(1, one.box, tuple(kps))
    for body, hand in ((unseen, "left"), (stray, "right"), (one, "right")):
        c = Cursor()
        assert c.update(body, 0.0) == body.cursor and c.hand == hand, hand
    kps = list(one.keypoints)
    kps[LEFT_HIP] = Keypoint(0.0, 0.0, MIN_CONF)                      # just confident enough: the reach is from it
    edge = Body(1, one.box, tuple(kps))
    wrist = edge.keypoints[LEFT_WRIST]
    assert Cursor._reach(edge, "left") == math.hypot(wrist.x, wrist.y)


def test_one_euro_cuts_jitter_and_lags_under_200ms():
    seed = zlib.crc32(b"one-euro")
    rng = np.random.default_rng(seed)
    times = np.arange(0.0, 10.0, 0.1)                                 # captures at 10 fps
    noisy = 0.5 + rng.uniform(-0.01, 0.01, times.size)               # a still wrist with the spec's jitter
    f = OneEuro()
    out = np.array([f(x, t) for x, t in zip(noisy, times)])
    assert out[20:].std() < 0.5 * noisy[20:].std(), f"seed={seed}"
    speed = 0.3                                                       # a wrist crossing the frame in 3 s
    f = OneEuro()
    ramp = [f(speed * t, t) for t in times[:30]]
    lag = (speed * times[29] - ramp[-1]) / speed
    assert 0.1 < lag < 0.2, lag
    fast, slow = OneEuro(beta=5.0), OneEuro(beta=0.0)                 # beta is the adaptive part: speed cuts lag
    for t in times[:30]:
        a, b = fast(speed * t, t), slow(speed * t, t)
    assert a > b + 0.01


def test_one_euro_holds_repeated_captures_and_ignores_non_finite():
    f = OneEuro()
    assert f(0.2, 1.0) == 0.2 and f.value == 0.2                      # the first sample passes through
    v = f(0.8, 1.1)
    assert 0.2 < v < 0.8
    assert f(0.9, 1.1) == v and f(0.9, 1.05) == v                     # the same capture again, or an older one
    assert f(math.nan, 1.2) == v and f(0.5, math.inf) == v and f.value == v
    f.reset()
    assert f.value is None and f(0.4, 0.0) == 0.4
    assert math.isnan(OneEuro()(math.nan, 0.0))
    for kwargs in (dict(min_cutoff=0.0), dict(d_cutoff=math.inf), dict(beta=-1.0), dict(min_cutoff=math.nan),
                   dict(beta=None), dict(d_cutoff=True), dict(min_cutoff="1")):
        with pytest.raises(ValueError):
            OneEuro(**kwargs)
    f = OneEuro()
    assert (f.min_cutoff, f.beta, f.d_cutoff) == (1.0, 0.007, 1.0)      # the paper's defaults


def test_one_euro_matches_the_paper():
    # Casiez et al. 2012, as written there: alpha = 1 / (1 + tau / Te), tau = 1 / (2 pi fc); the derivative is
    # low-passed at d_cutoff before it sets the cutoff.
    def alpha(cutoff, te):
        return 1.0 / (1.0 + 1.0 / (2.0 * math.pi * cutoff * te))

    seed = zlib.crc32(b"one-euro-paper")
    rng = np.random.default_rng(seed)
    times = np.cumsum(rng.uniform(0.05, 0.15, 60))
    xs = np.sin(times * 3.0) * 0.4 + 0.5 + rng.normal(0.0, 0.01, times.size)
    f = OneEuro(min_cutoff=0.8, beta=2.0, d_cutoff=1.5)
    x_hat, dx_hat, last = xs[0], 0.0, times[0]
    assert f(xs[0], times[0]) == x_hat
    for x, t in zip(xs[1:], times[1:]):
        te = t - last
        dx_hat += alpha(1.5, te) * ((x - x_hat) / te - dx_hat)
        x_hat += alpha(0.8 + 2.0 * abs(dx_hat), te) * (x - x_hat)
        last = t
        assert f(x, t) == pytest.approx(x_hat, abs=1e-12), f"seed={seed}"


def test_one_euro_casts_its_samples():
    # C26 pins it04's ruled deviation B5: the filter stores floats. C29: a numpy sample comes out as a float, and a
    # sample that is not a real number, or too big for a float, is not a sample.
    assert type(OneEuro(np.float32(1)).min_cutoff) is float and type(OneEuro(beta=np.int64(0)).beta) is float
    f = OneEuro()
    first = f(np.float32(0.25), np.float64(1.0))
    assert type(first) is float and type(f.value) is float and first == 0.25
    v = f(np.float32(0.75), np.int64(2))
    assert type(v) is float and 0.25 < v < 0.75
    for x, t in ((None, 3.0), ("0.9", 3.0), (0.9, None), (np.True_, 3.0), (10**400, 3.0), (0.9, 10**400)):
        assert f(x, t) == v and f.value == v
    assert math.isnan(OneEuro()(None, 0.0))                          # nothing yet: NaN, as for a NaN sample
    for kwargs in (dict(min_cutoff=10**400), dict(beta=-10**400), dict(d_cutoff=np.float64(np.inf))):
        with pytest.raises(ValueError):
            OneEuro(**kwargs)
    with pytest.raises(ValueError):
        capture_grace(10**400)
    with pytest.raises(ValueError):
        Hold(10**400)
```

Then switch the two existing timing tests to the CPU clock. The script checks each line before it changes it, so it fails loudly on a tree that differs from `ee6780b`:

```bash
.venv/bin/python - <<'EOF'
from pathlib import Path
for path, lines in [("tests/arcade/test_flash.py", (500, 502)), ("tests/arcade/test_look.py", (172, 174))]:
    p = Path(path)
    text = p.read_text().split("\n")
    for n in lines:
        assert text[n - 1].count("time.perf_counter()") == 1, (path, n, text[n - 1])
        text[n - 1] = text[n - 1].replace("time.perf_counter()", "time.thread_time()")
    p.write_text("\n".join(text))
EOF
git diff --stat tests/arcade/test_flash.py tests/arcade/test_look.py
```

It prints `2 files changed, 4 insertions(+), 4 deletions(-)`. The four lines now read:

```python
        start = time.thread_time()                                   # test_flash.py:500 and test_look.py:172
        times.append(time.thread_time() - start)                     # test_flash.py:502 and test_look.py:174
```

(The comments above are for this plan only; the files keep their own indentation and no comment is added.)

- [ ] **Step 2: Run them to verify they fail**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_sensed.py tests/arcade/test_scores.py tests/arcade/test_input.py`

Expected: `4 failed, 44 passed`. The four failures are:
- `test_raise_line_needs_a_torso_over_the_floor`, with `ImportError: cannot import name 'TORSO_FLOOR' from 'arcade.sensed'`;
- `test_sessions_log_casts_numpy_players_and_checks_names`, with `TypeError: Object of type int64 is not JSON serializable`, the C25 crash itself;
- `test_scores_drop_huge_ints_and_count_a_bad_previous`, with `AssertionError: assert [] == ['1']` (the bad `"previous"` is not counted);
- `test_one_euro_casts_its_samples`, with `AssertionError: assert (<class 'numpy.float32'> is float)`.

- [ ] **Step 3: Implement**

`arcade/sensed.py`:

```python
"""The Sensed record (spec 5): the only input games see, built once per tick by the runner."""
from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from arcade.calibration import Calibration

(NOSE, LEFT_EYE, RIGHT_EYE, LEFT_EAR, RIGHT_EAR, LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_ELBOW,
 RIGHT_ELBOW, LEFT_WRIST, RIGHT_WRIST, LEFT_HIP, RIGHT_HIP, LEFT_KNEE, RIGHT_KNEE, LEFT_ANKLE,
 RIGHT_ANKLE) = range(17)

KEYPOINT_NAMES = ("nose", "left_eye", "right_eye", "left_ear", "right_ear", "left_shoulder",
                  "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist",
                  "left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle")

SKELETON = ((LEFT_SHOULDER, LEFT_ELBOW), (LEFT_ELBOW, LEFT_WRIST), (RIGHT_SHOULDER, RIGHT_ELBOW),
            (RIGHT_ELBOW, RIGHT_WRIST), (LEFT_SHOULDER, RIGHT_SHOULDER), (LEFT_SHOULDER, LEFT_HIP),
            (RIGHT_SHOULDER, RIGHT_HIP), (LEFT_HIP, RIGHT_HIP), (LEFT_HIP, LEFT_KNEE),
            (LEFT_KNEE, LEFT_ANKLE), (RIGHT_HIP, RIGHT_KNEE), (RIGHT_KNEE, RIGHT_ANKLE),
            (NOSE, LEFT_SHOULDER), (NOSE, RIGHT_SHOULDER))

MIN_CONF = 0.3
RAISE_TORSOS = 0.3               # the raise line sits this many torso lengths above the shoulder midpoint
REACH_WIDTHS = 1.5               # the reach box spans this many shoulder widths each side of the shoulder midpoint,
REACH_TOP_TORSOS = 1.05          # and from this many torso lengths above it (head plus a forearm) down to the hips
TORSO_PER_SHOULDER_WIDTH = 1.25  # torso length estimated from shoulder width when no hip is seen
NOSE_TO_HIP_PER_TORSO = 1.5      # scale estimated from the torso when the nose is not seen
TORSO_FLOOR = 0.1                # a torso shorter than this share of the box height is not measured (C22)
MOTION_GRID = (128, 64)          # (width, height) of the fixed grid scenario files and actors store motion on


@dataclass(frozen=True)
class Keypoint:
    x: float
    y: float
    conf: float = 1.0


def _clean(kp: Keypoint) -> Keypoint:
    x, y, conf = kp.x, kp.y, kp.conf
    bad = any(v is None or math.isnan(v) for v in (x, y, conf))
    if bad:
        return Keypoint(0.0, 0.0, 0.0)
    return Keypoint(min(1.0, max(0.0, x)), min(1.0, max(0.0, y)),
                    0.0 if not 0.0 <= x <= 1.0 or not 0.0 <= y <= 1.0 else min(1.0, max(0.0, conf)))


def _clamp01(v: float) -> float:
    return min(1.0, max(0.0, v))


def _mid(a: Keypoint, b: Keypoint) -> Keypoint | None:
    """The midpoint of the confident ones of a and b; one alone stands in for the pair."""
    seen = [k for k in (a, b) if k.conf >= MIN_CONF]
    if not seen:
        return None
    return Keypoint(sum(k.x for k in seen) / len(seen), sum(k.y for k in seen) / len(seen),
                    min(k.conf for k in seen))


@dataclass(frozen=True)
class Body:
    """One tracked person. Keypoints are normalized camera coordinates, already mirrored and smoothed.

    scale 0.0 means "measure it": the nose-to-mid-hip length, or 1.5 torso lengths without a nose.
    """

    id: int
    box: tuple[float, float, float, float]
    keypoints: tuple[Keypoint, ...]
    vx: float = 0.0
    vy: float = 0.0
    scale: float = 0.0
    in_zone: bool = True
    zone_x: float = 0.5
    zone_y: float = 0.5
    seen_ago: float = 0.0

    def __post_init__(self):
        if len(self.keypoints) != 17:
            raise ValueError(f"a body has 17 keypoints, got {len(self.keypoints)}")
        object.__setattr__(self, "keypoints", tuple(_clean(k) for k in self.keypoints))
        if self.scale == 0.0:
            object.__setattr__(self, "scale", self._measured_scale())

    def _measured_scale(self) -> float:
        hip = self.hip_mid
        if self.nose.conf >= MIN_CONF and hip is not None:
            return math.hypot(self.nose.x - hip.x, self.nose.y - hip.y)
        return NOSE_TO_HIP_PER_TORSO * self.torso

    @property
    def nose(self) -> Keypoint:
        return self.keypoints[NOSE]

    @property
    def left_wrist(self) -> Keypoint:
        return self.keypoints[LEFT_WRIST]

    @property
    def right_wrist(self) -> Keypoint:
        return self.keypoints[RIGHT_WRIST]

    @property
    def shoulder_mid(self) -> Keypoint | None:
        """The midpoint of the confident shoulders, None without one.

        With one shoulder, its y stands in for the pair, but x comes from both hips, else a confident
        nose, else the one hip seen, else that shoulder: the centre (and so anchor, zone_x and the reach
        box) does not jump half a shoulder or hip width when one shoulder and one hip drop out.
        """
        left, right = self.keypoints[LEFT_SHOULDER], self.keypoints[RIGHT_SHOULDER]
        seen = [k for k in (left, right) if k.conf >= MIN_CONF]
        if len(seen) != 1:
            return _mid(left, right)
        one = seen[0]
        hips = (self.keypoints[LEFT_HIP], self.keypoints[RIGHT_HIP])
        if all(h.conf >= MIN_CONF for h in hips):
            x = (hips[0].x + hips[1].x) / 2
        elif self.nose.conf >= MIN_CONF:
            x = self.nose.x
        else:
            hip = self.hip_mid
            x = hip.x if hip is not None else one.x
        return Keypoint(x, one.y, one.conf)

    @property
    def hip_mid(self) -> Keypoint | None:
        return _mid(self.keypoints[LEFT_HIP], self.keypoints[RIGHT_HIP])

    @property
    def shoulder_width(self) -> float:
        """Distance between the shoulders, 0.0 unless both are confident."""
        a, b = self.keypoints[LEFT_SHOULDER], self.keypoints[RIGHT_SHOULDER]
        if a.conf < MIN_CONF or b.conf < MIN_CONF:
            return 0.0
        return math.hypot(a.x - b.x, a.y - b.y)

    @property
    def torso(self) -> float:
        """Shoulder midpoint to hip midpoint; from the shoulder width without hips; 0.0 when unknown."""
        s, h = self.shoulder_mid, self.hip_mid
        if s is not None and h is not None:
            return math.hypot(s.x - h.x, s.y - h.y)
        return TORSO_PER_SHOULDER_WIDTH * self.shoulder_width

    @property
    def anchor(self) -> Keypoint | None:
        """What the tracker and place() follow: the shoulder midpoint, then the nose, then the hips."""
        s = self.shoulder_mid
        if s is not None:
            return s
        if self.nose.conf >= MIN_CONF:
            return self.nose
        return self.hip_mid

    @property
    def raise_line(self) -> float | None:
        """A wrist above this y is raised: 0.3 torso above the shoulders.

        The nose stands in without shoulders, and when the torso cannot be measured (one shoulder and no
        hip) or is under TORSO_FLOOR of the box height (side-on shoulders with the hips hidden, C22),
        because a line a hair above the shoulders would count a wrist at the collarbone; with neither,
        None, and nothing is raised.
        """
        s, torso = self.shoulder_mid, self.torso
        if s is not None and torso > 0.0 and torso >= TORSO_FLOOR * self.height:
            return s.y - RAISE_TORSOS * torso
        if self.nose.conf >= MIN_CONF:
            return self.nose.y
        return None

    @property
    def raised_wrist(self) -> Keypoint | None:
        """The higher confident wrist above the raise line, else None."""
        line = self.raise_line
        if line is None:
            return None
        best = None
        for w in (self.left_wrist, self.right_wrist):
            if w.conf >= MIN_CONF and w.y < line and (best is None or w.y < best.y):
                best = w
        return best

    @property
    def both_hands_up(self) -> bool:
        line = self.raise_line
        return line is not None and all(w.conf >= MIN_CONF and w.y < line
                                        for w in (self.left_wrist, self.right_wrist))

    def reach(self, kp: Keypoint) -> tuple[float, float]:
        """kp in the body-relative reach box (spec 7.3), (u, v) each clamped to 0..1.

        u runs across 1.5 shoulder widths each side of the shoulder midpoint; v runs from 1.05 torso
        above the shoulder midpoint (head plus a forearm) down to hip height. Without shoulders the
        body box is the frame of reference.
        """
        s, torso = self.shoulder_mid, self.torso
        width = self.shoulder_width or torso / TORSO_PER_SHOULDER_WIDTH
        if s is None or torso <= 0.0 or width <= 0.0:
            x0, y0, x1, y1 = self.box
            u = (kp.x - x0) / (x1 - x0) if x1 > x0 else 0.5
            v = (kp.y - y0) / (y1 - y0) if y1 > y0 else 0.5
        else:
            hip = self.hip_mid
            top = s.y - REACH_TOP_TORSOS * torso
            bottom = hip.y if hip is not None else s.y + torso
            u = (kp.x - (s.x - REACH_WIDTHS * width)) / (2 * REACH_WIDTHS * width)
            v = (kp.y - top) / (bottom - top)
        return (_clamp01(u), _clamp01(v))

    @property
    def cursor(self) -> tuple[float, float] | None:
        """The confident wrist further from its hip, through reach(); None without a confident wrist.

        Stateless: when the pointing wrist drops out for a frame the cursor jumps to the other wrist
        (15 percent of captures at the spec 6.4 dropout), so every consumer needs a grace period or hysteresis.
        """
        best, far = None, -1.0
        for wrist, hip_index in ((self.left_wrist, LEFT_HIP), (self.right_wrist, RIGHT_HIP)):
            if wrist.conf < MIN_CONF:
                continue
            own = self.keypoints[hip_index]
            ref = next((k for k in (own if own.conf >= MIN_CONF else None, self.hip_mid, self.shoulder_mid)
                        if k is not None), wrist)
            d = math.hypot(wrist.x - ref.x, wrist.y - ref.y)
            if d > far:
                best, far = wrist, d
        return None if best is None else self.reach(best)

    @property
    def center(self) -> tuple[float, float]:
        x0, y0, x1, y1 = self.box
        return ((x0 + x1) / 2, (y0 + y1) / 2)

    @property
    def height(self) -> float:
        return self.box[3] - self.box[1]

    @property
    def confidence(self) -> float:
        return sum(k.conf for k in self.keypoints) / 17


@dataclass(frozen=True)
class Blob:
    """A light source. x and y are clamped to 0..1 (NaN and None to 0), as keypoints are, so a blob that leaves the
    frame (a headlamp crossing it) never maps outside the wall."""

    x: float
    y: float
    size: float
    color: tuple[int, int, int]
    in_zone: bool = True

    def __post_init__(self):
        for name in ("x", "y"):
            v = getattr(self, name)
            object.__setattr__(self, name, 0.0 if v is None or math.isnan(v) else _clamp01(v))


@dataclass(frozen=True, kw_only=True)
class Audio:
    """Every field is a keyword: Audio(0.8, 1.0) would silently put 1.0 in level_smooth."""

    level: float = 0.0            # broadband RMS with slow gain, 0..1, for ambient visuals only
    level_smooth: float = 0.0     # level with 50 ms attack and 300 ms release
    peak: float = 0.0
    voice_db: float = -90.0       # absolute dBFS in the 300 Hz to 3.4 kHz band
    floor_db: float = -90.0       # rolling 30 s 90th percentile of voice_db
    voice: float = 0.0            # (voice_db - floor_db) / 30, clamped 0..1
    clap: bool = False
    onset: bool = False
    beat: bool = False
    bpm: float | None = None


def _in(zone: tuple[float, float, float, float], x: float, y: float) -> bool:
    x0, y0, x1, y1 = zone
    return x0 <= x <= x1 and y0 <= y <= y1


def place(body: Body, calibration: Calibration) -> Body:
    """body with in_zone, zone_x and zone_y from the calibration (spec 6.6). Actors and the tracker call it.

    The anchor (shoulders, then nose, then hips; the box centre without any) maps into the zone, 0..1
    across the mat and clamped. In the zone means the anchor inside it and the body at least min_height tall.
    """
    x0, y0, x1, y1 = calibration.zone
    a = body.anchor
    ax, ay = (a.x, a.y) if a is not None else body.center
    inside = _in(calibration.zone, ax, ay) and body.height >= calibration.min_height
    return dataclasses.replace(body, in_zone=inside, zone_x=_clamp01((ax - x0) / (x1 - x0)),
                               zone_y=_clamp01((ay - y0) / (y1 - y0)))


def place_blob(blob: Blob, calibration: Calibration) -> Blob:
    """blob with in_zone from the calibration zone. The blob must be in the zone's space, the mirrored
    display space of the keypoints: a blob source mirrors x as mirror_keypoints does."""
    return dataclasses.replace(blob, in_zone=_in(calibration.zone, blob.x, blob.y))


def _resample(motion: np.ndarray, width: int, height: int) -> np.ndarray:
    """Nearest-cell resample that keeps every lit cell: a shrinking axis ORs the source cells it covers."""
    rows = (np.arange(height) * motion.shape[0]) // height
    cols = (np.arange(width) * motion.shape[1]) // width
    grid = np.logical_or.reduceat(motion.astype(bool), rows, axis=0)
    return np.logical_or.reduceat(grid, cols, axis=1)


@dataclass(frozen=True, eq=False)
class Sensed:
    """Every field after t is a keyword: Sensed(t, bodies) would silently put the bodies in camera_t."""

    t: float                                     # seconds since runner start
    _: dataclasses.KW_ONLY
    camera_t: float = 0.0                        # capture time of the newest camera frame, on the runner clock
    camera_fresh: bool = False                   # true on the tick a new camera frame arrived
    camera_seq: int = 0
    bodies: tuple[Body, ...] = ()                # tracked, stable ids, largest scale first
    player: Body | None = None                   # the locked player (spec 7.2), set by the runner
    player2: Body | None = None
    present: bool = False                        # someone is in the zone, with hysteresis, set by the runner
    blobs: tuple[Blob, ...] = ()                 # light sources, brightest first, at most 8
    motion: np.ndarray = field(default_factory=lambda: np.zeros((0, 0), bool))   # bool (height, width)
    audio: Audio = field(default_factory=Audio)

    def __post_init__(self):
        # One grid is shared by every tick that holds it (degrade, with_motion), so the record keeps a
        # read-only view; the producer's own array stays writeable, but must not change after hand-over.
        # None (an old scenario record) means the empty grid.
        motion = np.zeros((0, 0), bool) if self.motion is None else np.asarray(self.motion, bool)
        motion = motion.view()
        motion.flags.writeable = False
        object.__setattr__(self, "motion", motion)

    def with_motion(self, size: tuple[int, int]) -> "Sensed":
        """This record with motion as a (height, width) grid for size (width, height).

        An empty grid becomes all False; a grid of another shape is resampled. Bodies are never
        rasterized into it.
        """
        w, h = size
        if self.motion.shape == (h, w):
            return self
        if self.motion.size == 0:
            return dataclasses.replace(self, motion=np.zeros((h, w), bool))
        return dataclasses.replace(self, motion=_resample(self.motion, w, h))
```

`arcade/scores.py`:

```python
"""Best-of-the-night scores and the sessions log (spec 7.5). Neither ever raises into a game for a bad file."""
from __future__ import annotations

import json
import logging
import math
import numbers
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable

from arcade.look import is_real

log = logging.getLogger("arcade")

ROLLOVER_HOUR = 16       # a night runs from 16:00 local time to 16:00 the next day
REASONS = ("done", "left", "inactive", "capped", "exit", "crash")


def night_of(when: datetime) -> date:
    """The night a moment belongs to, named by the date of its evening: 01:00 on the 12th is the 11th's."""
    return (when - timedelta(hours=ROLLOVER_HOUR)).date()


def _finite(value) -> float | None:
    """value as a finite float, else None (NaN, infinity, None, a bool or anything that is not a number). A
    numpy number is a number: games compute scores with numpy."""
    if not is_real(value):
        return None
    try:
        value = float(value)
    except (OverflowError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _entry(raw) -> dict | None:
    """A {"best", "when"} record from the file, or None if it is malformed."""
    if not isinstance(raw, dict) or _finite(raw.get("best")) is None or not isinstance(raw.get("when"), str):
        return None
    try:
        datetime.fromisoformat(raw["when"])
    except ValueError:
        return None
    return {"best": float(raw["best"]), "when": raw["when"]}


def _write_atomic(path: Path, text: str) -> None:
    """Write through a temporary file in the same directory: flush, fsync, then rename over the old file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


class Scores:
    """{game: {layout: {"best", "when"}}} in one JSON file (spec 7.5); higher is better.

    Scores(None) keeps everything in memory and never writes, for tests and tools. Tonight's best rolls over
    at 16:00 local time. An entry replaced by the first record of a new night keeps the old one under
    "previous", so last_night() can show the night before tonight. A missing, unreadable or malformed file
    starts empty with a warning; a write that fails (a read-only or full disk) logs a warning and keeps the
    scores in memory. clock returns local time (datetime.now).
    """

    def __init__(self, path: Path | str | None, clock: Callable[[], datetime] = datetime.now):
        self.path = None if path is None else Path(path)
        self.clock = clock
        self._data: dict[str, dict[str, dict]] = {}
        if self.path is not None:
            self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text())
        except FileNotFoundError:
            return
        except (ValueError, OSError) as e:
            log.warning("ignoring unreadable scores file %s: %s", self.path, e)
            return
        if not isinstance(raw, dict):
            log.warning("ignoring scores file %s: not an object", self.path)
            return
        dropped = 0
        for game, layouts in raw.items():
            for layout, value in (layouts.items() if isinstance(layouts, dict) else ()):
                entry = _entry(value)
                if entry is None:
                    dropped += 1
                    continue
                if "previous" in value:
                    previous = _entry(value["previous"])
                    if previous is None:
                        dropped += 1                                # the entry stays, without last night
                    else:
                        entry["previous"] = previous
                self._data.setdefault(game, {})[layout] = entry
            dropped += not isinstance(layouts, dict)
        if dropped:
            log.warning("ignoring %d malformed entries in scores file %s", dropped, self.path)

    def for_game(self, name: str, layout: str) -> GameScores:
        """The view a game gets as self.scores."""
        return GameScores(self, name, layout)

    def _tonight(self, entry: dict | None, night: date) -> float | None:
        if entry is None or night_of(datetime.fromisoformat(entry["when"])) != night:
            return None
        return entry["best"]

    def best(self, name: str, layout: str) -> float | None:
        """Tonight's best for this game on this layout, or None."""
        return self._tonight(self._data.get(name, {}).get(layout), night_of(self.clock()))

    def last_night(self, name: str, layout: str) -> float | None:
        """The best of the night before tonight, or None (also when that night had no record)."""
        entry = self._data.get(name, {}).get(layout)
        yesterday = night_of(self.clock()) - timedelta(days=1)
        for candidate in (entry, (entry or {}).get("previous")):
            best = self._tonight(candidate, yesterday)
            if best is not None:
                return best
        return None

    def record(self, name: str, layout: str, value: float, margin: float = 0.0) -> bool:
        """True if value is tonight's new best: the first of the night, or above the best by margin or more
        (strictly above at margin 0). A value that is not a finite number is never a best."""
        if _finite(margin) is None or margin < 0.0:
            raise ValueError(f"margin must be a finite number, 0 or more, got {margin!r}")
        v = _finite(value)
        if v is None:
            log.warning("ignoring score %r for %s %s: not a finite number", value, name, layout)
            return False
        now = self.clock()
        night = night_of(now)
        entry = self._data.get(name, {}).get(layout)
        best = self._tonight(entry, night)
        if best is not None and not (v > best and v >= best + margin):
            return False
        new = {"best": v, "when": now.isoformat()}
        if best is None and entry is not None:
            new["previous"] = {"best": entry["best"], "when": entry["when"]}    # the last night that had one
        elif entry is not None and "previous" in entry:
            new["previous"] = entry["previous"]
        self._data.setdefault(name, {})[layout] = new
        self._save()
        return True

    def _save(self) -> None:
        if self.path is None:
            return
        try:
            _write_atomic(self.path, json.dumps(self._data, indent=1))
        except OSError as e:
            log.warning("could not write scores file %s, keeping scores in memory: %s", self.path, e)


class GameScores:
    """One game's scores on one layout: what a game sees as self.scores (spec 7.1)."""

    def __init__(self, scores: Scores, name: str, layout: str):
        self.scores, self.name, self.layout = scores, name, layout

    def record(self, value: float, margin: float = 0.0) -> bool:
        return self.scores.record(self.name, self.layout, value, margin)

    def best(self) -> float | None:
        return self.scores.best(self.name, self.layout)

    def last_night(self) -> float | None:
        return self.scores.last_night(self.name, self.layout)


class SessionLog:
    """One JSON line per session in data_dir/sessions.jsonl (spec 7.5), appended and fsynced.

    SessionLog(None) keeps the records in memory (records) and never writes. A reason outside REASONS, a game
    or layout that is not a string, or a players count that is not an int of 0 or more raises ValueError (a
    runner bug); a numpy int is an int (C25). A write that fails logs a warning. A duration or score that is not
    a finite number is written as null.
    """

    def __init__(self, path: Path | str | None):
        self.path = None if path is None else Path(path)
        self.records: list[dict] = []

    def append(self, game: str, layout: str, start: datetime, duration: float, players: int, score: float | None,
               reason: str) -> dict:
        if reason not in REASONS:
            raise ValueError(f"session end reason must be one of {REASONS}, got {reason!r}")
        if not isinstance(start, datetime):
            raise ValueError(f"session start must be a datetime, got {start!r}")
        if not isinstance(game, str) or not isinstance(layout, str):
            raise ValueError(f"session game and layout must be strings, got {game!r} and {layout!r}")
        if isinstance(players, bool) or not isinstance(players, numbers.Integral) or players < 0:
            raise ValueError(f"session players must be an int, 0 or more, got {players!r}")
        record = {"game": game, "layout": layout, "start": start.isoformat(), "duration": _finite(duration),
                  "players": int(players), "score": _finite(score), "reason": reason}
        if self.path is None:
            self.records.append(record)
            return record
        try:
            line = json.dumps(record) + "\n"
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a") as f:
                f.write(line)
                f.flush()
                os.fsync(f.fileno())
        except (OSError, TypeError, ValueError) as e:
            log.warning("could not append to sessions log %s: %s", self.path, e)
        return record
```

`arcade/input.py`:

```python
"""Input helpers shared by games, the lobby and the runner (spec 4.1): Edge, Hold, Cursor and the One Euro filter.

The camera captures at camera_fps (10) while the runner ticks at 30 Hz, so a Sensed body holds for three ticks
and a keypoint that drops out of one capture is missing for a tenth of a second. At the spec 6.4 dropout (15
percent per keypoint) one wrist is missing from 15 percent of captures and both hands up reads false on 28
percent, in runs (C10, measured over 6000 s of degrade(REAL_NOISE) captures): 3 or more captures in a row about
every 7 s of holding, 5 or more about every 5 minutes, 6 about every 25 minutes, 7 or more never. Every helper
here takes a grace in seconds. The lobby and the runner give theirs capture_grace(cfg.camera_fps), which is
sized in captures (Q10); a game chooses its own, and a grace delays a release by that long.

The caller rule (C27): call update on a Hold, an Edge or a Cursor every tick, with the value false when there is
nothing to see, or reset() it when it comes back into use (the runner resets its exit hold on every launch). A
helper not updated for a while still holds its last state, so a Hold could fire at once on the first tick after
the gap.
"""
from __future__ import annotations

import math

from arcade.look import is_real
from arcade.sensed import LEFT_HIP, LEFT_WRIST, MIN_CONF, RIGHT_HIP, RIGHT_WRIST, Body

CAPTURE_GRACE = 5        # missed captures in a row that a hold, an edge or the cursor rides out
EPSILON = 1e-9           # tick times are sums of 1/30: a 3.0 s hold must not miss by a rounding error


def _float(value) -> float:
    """value as a float: NaN if it is not a real number, an infinity if it is an int too big for a float."""
    if not is_real(value):
        return math.nan
    try:
        return float(value)
    except OverflowError:
        return math.inf if value > 0 else -math.inf


def _check(name: str, value: float) -> float:
    v = _float(value)
    if not 0.0 <= v < math.inf:
        raise ValueError(f"{name} must be a finite number of seconds, 0 or more, got {value!r}")
    return v


def _positive(name: str, value: float, zero: bool = False) -> float:
    """value as a float if it is finite and over 0 (or 0 itself, with zero), else ValueError."""
    v = _float(value)
    if not (0.0 <= v if zero else 0.0 < v) or not v < math.inf:
        raise ValueError(f"{name} must be {'0 or more' if zero else 'over 0'} and finite, got {value!r}")
    return v


def capture_grace(camera_fps: float, captures: int = CAPTURE_GRACE) -> float:
    """Seconds that cover this many missed captures in a row, plus half a capture so a run of exactly that
    many never trips on a rounding error: 0.55 s at 10 fps. A run one capture longer ends the hold."""
    fps = _positive("camera_fps", camera_fps)
    if isinstance(captures, bool) or not isinstance(captures, int) or captures < 0:
        raise ValueError(f"captures must be an int, 0 or more, got {captures!r}")
    return (captures + 0.5) / fps


class Edge:
    """A rising edge that fires once per press. update(value, t) is True on the first true value after the
    value has been false for more than grace seconds (or ever). A blink no longer than grace, a wrist missing
    from a capture or two, neither fires again nor re-arms."""

    def __init__(self, grace: float = 0.25):
        self.grace = _check("grace", grace)
        self.on = False
        self._last = -math.inf

    def update(self, value: bool, t: float) -> bool:
        if value:
            fire = not self.on
            self.on, self._last = True, t
            return fire
        if self.on and t - self._last > self.grace + EPSILON:
            self.on = False
        return False


class Hold:
    """update(value, t) is True once, on the first tick with value true that is seconds or more after the hold
    began. Dropouts of up to grace seconds keep the hold; a longer one ends it (progress back to 0), and it
    fires again only after a new hold. progress runs 0..1 for a ring drawn round the hands."""

    def __init__(self, seconds: float, grace: float = 0.25):
        self.seconds, self.grace = _check("seconds", seconds), _check("grace", grace)
        self.reset()

    def reset(self) -> None:
        self.start: float | None = None
        self.fired = False
        self._last = self._now = -math.inf

    @property
    def progress(self) -> float:
        if self.start is None:
            return 0.0
        if self.seconds == 0.0:
            return 1.0
        return min(1.0, max(0.0, (self._now - self.start) / self.seconds))

    def update(self, value: bool, t: float) -> bool:
        self._now = t
        if value:
            if self.start is None:
                self.start = t
            self._last = t
        elif self.start is not None and t - self._last > self.grace + EPSILON:
            self.reset()
            return False
        if not value or self.fired or self.start is None or t - self.start < self.seconds - EPSILON:
            return False
        self.fired = True
        return True


class Cursor:
    """Body.cursor with hand hysteresis (C10). The stateless cursor jumps to the other wrist whenever the
    pointing one drops out of a capture; this one keeps the hand it chose and holds its last position for
    up to grace seconds while that wrist is missing, and changes hands only when the other wrist reaches
    switch times further from its hip. update(body, t) returns (u, v) in the reach box, or None."""

    def __init__(self, grace: float = 0.25, switch: float = 1.25):
        self.grace = _check("grace", grace)
        if not is_real(switch) or not 1.0 <= switch < math.inf:
            raise ValueError(f"switch must be 1 or more and finite, got {switch!r}")
        self.switch = float(switch)
        self.hand: str | None = None
        self._last: tuple[float, float] | None = None
        self._seen = -math.inf

    @staticmethod
    def _reach(body: Body, hand: str) -> float | None:
        """How far this hand's confident wrist is from its hip (as Body.cursor measures it), else None."""
        wrist, hip = (body.keypoints[LEFT_WRIST], body.keypoints[LEFT_HIP]) if hand == "left" else \
            (body.keypoints[RIGHT_WRIST], body.keypoints[RIGHT_HIP])
        if wrist.conf < MIN_CONF:
            return None
        ref = next((k for k in (hip if hip.conf >= MIN_CONF else None, body.hip_mid, body.shoulder_mid)
                    if k is not None), wrist)
        return math.hypot(wrist.x - ref.x, wrist.y - ref.y)

    def update(self, body: Body | None, t: float) -> tuple[float, float] | None:
        reach = {} if body is None else {h: d for h in ("left", "right") if (d := self._reach(body, h)) is not None}
        if self.hand not in reach:
            if self._last is not None and t - self._seen <= self.grace + EPSILON:
                return self._last                            # the pointing wrist is missing: hold it
            self.hand = max(reach, key=reach.get) if reach else None
        else:
            other = "left" if self.hand == "right" else "right"
            if other in reach and reach[other] > self.switch * reach[self.hand]:
                self.hand = other
        if self.hand is None:
            return None
        wrist = body.keypoints[LEFT_WRIST if self.hand == "left" else RIGHT_WRIST]
        self._last, self._seen = body.reach(wrist), t
        return self._last


class OneEuro:
    """The One Euro filter (Casiez, Roussel and Vogel, CHI 2012) for one coordinate, timed by capture time.

    A sample at a time no later than the last one (the same capture held over several ticks) returns the
    last output unchanged, and so does a sample that is not a finite real number (NaN before the first). A
    numpy sample is taken as a float, and the output is always a float. beta = 0.007 is the paper's value for
    pixel units; in the 0..1 camera units the arcade uses it barely adapts, so the tracker (core Task 16)
    passes its own when it is tuned against the real fixtures."""

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.007, d_cutoff: float = 1.0):
        self.min_cutoff, self.d_cutoff = _positive("min_cutoff", min_cutoff), _positive("d_cutoff", d_cutoff)
        self.beta = _positive("beta", beta, zero=True)
        self.reset()

    def reset(self) -> None:
        self.value: float | None = None
        self._dx = 0.0
        self._t = -math.inf

    @staticmethod
    def _alpha(dt: float, cutoff: float) -> float:
        r = 2.0 * math.pi * cutoff * dt
        return r / (r + 1.0)

    def __call__(self, x: float, t: float) -> float:
        x, t = _float(x), _float(t)
        if not (math.isfinite(x) and math.isfinite(t)):
            return math.nan if self.value is None else self.value
        if self.value is None:
            self.value, self._t = x, t
            return x
        dt = t - self._t
        if dt <= 0.0:
            return self.value
        self._dx += self._alpha(dt, self.d_cutoff) * ((x - self.value) / dt - self._dx)
        cutoff = self.min_cutoff + self.beta * abs(self._dx)
        self.value += self._alpha(dt, cutoff) * (x - self.value)
        self._t = t
        return self.value
```

- [ ] **Step 4: Run the tests**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_sensed.py tests/arcade/test_scores.py tests/arcade/test_input.py`

Expected: `48 passed` (sensed 21, scores 14, input 13).

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`

Expected: `338 passed`, no skips.

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs -m perf tests/arcade/test_flash.py tests/arcade/test_look.py`

Expected: `2 passed, 45 deselected`.

- [ ] **Step 5: Commit**

```bash
git add arcade/sensed.py arcade/scores.py arcade/input.py tests/arcade/test_sensed.py tests/arcade/test_scores.py tests/arcade/test_input.py tests/arcade/test_flash.py tests/arcade/test_look.py
git commit -m "fix(arcade): torso floor for the raise line, sessions log casts numpy players and never raises on write, OneEuro casts its samples; perf tests time CPU, not wall (it03 C22, it04 C25, C26, C27, C29 part, it05 plan review B2)" -m "Four tests appended. Four existing lines changed, clock only: the governor and distance-look perf tests time with time.thread_time() instead of time.perf_counter(). Wall time counts the waits of a loaded machine, and under parallel agent load these tests failed on timing alone; the thread's CPU time is the code's cost. The 0.5 ms and 1/30 s limits are unchanged, so no assert is weakened. A torso under 0.1 of the box height falls back to the nose line. SessionLog.append raises ValueError for a bad game, layout or players before any write and logs a failed write, so the runner's crash path cannot crash the runner. The two ruled it04 deviations are pinned, and input.py states the caller rule for Hold, Edge and Cursor." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: The effects toolkit (core Task 8 part, spec 8.1, it04 N11)

**Files:**
- Create: `arcade/juice.py`
- Test: `tests/arcade/test_juice.py`

**Interfaces:**
- Consumes: `arcade.canvas` (`Canvas`, `_c`), `look.is_real`, `arcade.sensed.Body` (`zone_x`), `show.font.CELL_H`, and, in the tests, `arcade.flash.flash_area`, `arcade.sensed.place`, `arcade.calibration.Calibration` and `arcade.sources.actors` (`TICK`, `Person`).
- Produces:
  - `Juice(rng: random.Random, size: tuple[int, int] = (128, 32))`, with:
    - `shake(px, seconds)`, `flash(color, seconds=0.2) -> bool` (a hold: the color is added for `seconds`, then stops; refused while one shows or under `FLASH_GAP` after it ended), `burst(x, y, color, n=12) -> bool` (refused within `BURST_NEAR` of a burst from the last `BURST_GAP` = 0.5 s), `pop(text, x, y, color)`, `banner(text, seconds=1.0)`, `freeze(seconds)`, `celebrate(color)` and `echo(player: 1 | 2, kind: "up" | "down" | "hit" | "ok")`;
    - the `frozen` property;
    - `update(dt)`, `render(canvas, player=None, player2=None)` and `debug_state() -> dict`, whose keys are `fx_shake`, `fx_particles`, `fx_frozen`, `fx_flash`, `fx_banner`, `fx_pops` and `fx_echoes`.
  - `marker_x(body, width) -> int`.
  - The constants `MAX_PARTICLES = 96`, `SHAKE_STEP`, `SHAKE_MAX`, `FLASH_GAP`, `BURST_SPEED`, `BURST_LIFE`, `BURST_GAP`, `BURST_NEAR`, `BURST_N`, `POP_RISE`, `POP_SECONDS`, `MAX_POPS`, `ECHO_SECONDS`, `ECHOES`, `PLAYER_COLORS` and `CELEBRATE_GAP`.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_juice.py`:

```python
import math
import random
import statistics
import time
import zlib

import numpy as np
import pytest

import arcade.juice as juice
from arcade.calibration import Calibration
from arcade.canvas import Canvas
from arcade.flash import flash_area
from arcade.juice import (BURST_LIFE, BURST_NEAR, ECHO_SECONDS, FLASH_GAP, MAX_PARTICLES, PLAYER_COLORS, POP_RISE,
                          SHAKE_STEP, Juice, marker_x)
from arcade.sensed import place
from arcade.sources.actors import TICK, Person

WHITE = (255, 255, 255)


def checker(size, block=4):
    """A high-contrast frame: white and black squares of block pixels, edges everywhere on both axes."""
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w]
    return np.where((((xx // block) + (yy // block)) % 2 == 0)[..., None], np.uint8(255), np.uint8(0)).repeat(3, 2)


def run(fx, canvas, ticks, each=None, base=None, **render):
    """Render ticks frames over base (black by default), calling each(fx, i) before each; returns the frames."""
    frames = []
    for i in range(ticks):
        if each is not None:
            each(fx, i)
        canvas.frame[:] = 0 if base is None else base
        fx.render(canvas, **render)
        frames.append(canvas.frame.copy())
        fx.update(TICK)
    return frames


def test_particle_pool_capped_at_96():
    fx = Juice(random.Random(1), (640, 64))
    for i in range(10):                                              # ten bursts of 12, far enough apart
        assert fx.burst(20 + i * 60, 30, WHITE)
    assert fx.debug_state()["fx_particles"] == MAX_PARTICLES == 96
    assert fx._pos[fx._alive()][:, 0].min() >= 20 + 2 * 60           # the oldest two bursts were replaced
    fx.update(BURST_LIFE)
    assert fx.debug_state()["fx_particles"] == 0
    assert fx.burst(20, 30, WHITE, n=500) and fx.debug_state()["fx_particles"] == 96
    angles = np.sort(np.arctan2(fx._vel[:, 1], fx._vel[:, 0]))
    gaps = np.diff(np.concatenate([angles, angles[:1] + 2 * math.pi]))
    assert gaps.max() == pytest.approx(2 * math.pi / 96)             # n is capped first: still a whole ring
    fx.update(BURST_LIFE)
    assert fx.burst(100, 30, WHITE, n=np.int64(5)) and fx.debug_state()["fx_particles"] == 5


def test_shake_decays_to_zero(font5x7):
    fx = Juice(random.Random(3), (128, 32))
    canvas = Canvas(128, 32, font5x7)
    offsets = []
    fx.shake(4, 1.0)
    for i in range(45):
        canvas.frame[:] = 0
        canvas.frame[16, 64] = WHITE
        fx.render(canvas)
        offsets.append(tuple(fx.debug_state()["fx_shake"]))
        ys, xs = np.nonzero(canvas.frame.any(axis=2))
        assert (xs.tolist(), ys.tolist()) == ([64 + offsets[-1][0]], [16 + offsets[-1][1]])   # the frame moved
        fx.update(TICK)
    axis = 0 if any(o[0] for o in offsets) else 1
    assert all(o[1 - axis] == 0 for o in offsets)                    # one axis only
    values = [o[axis] for o in offsets]
    changes = [i for i in range(1, 45) if values[i] != values[i - 1]]
    assert abs(values[0]) == 4 and changes                           # at once, at full size
    assert all(b - a >= SHAKE_STEP / TICK - 1e-6 for a, b in zip([0] + changes, changes))   # 4 moves a second
    sizes = [abs(values[i]) for i in [0] + changes]
    assert sizes == sorted(sizes, reverse=True) and sizes[-1] == 0   # decaying, then still
    signs = [values[i] > 0 for i in [0] + changes[:-1]]
    assert all(a != b for a, b in zip(signs, signs[1:]))             # side to side
    for i in [0] + changes:
        assert abs(values[i]) <= 4 * max(0.0, 1.0 - i * TICK) + 0.5  # under the decaying envelope
    assert values[36:] == [0] * 9 and fx.debug_state()["fx_shake"] == [0, 0]
    fx.shake(100, 0.5)                                               # capped at SHAKE_MAX
    run(fx, canvas, 3)
    assert max(abs(v) for v in fx.debug_state()["fx_shake"]) == juice.SHAKE_MAX
    fx.shake(1, 0.1)                                                 # smaller than the one running: ignored
    assert fx._amp == juice.SHAKE_MAX


def test_shake_slice_copy_fills_black(font5x7):
    fx = Juice(random.Random(0), (64, 64))
    canvas = Canvas(64, 64, font5x7)
    fx.shake(3, 2.0)
    for _ in range(3):
        fx.update(TICK)
    canvas.frame[:] = WHITE
    fx.render(canvas)
    dx, dy = fx.debug_state()["fx_shake"]
    assert (dx, dy) != (0, 0)
    lit = canvas.frame.any(axis=2)
    assert lit.sum() == (64 - abs(dx)) * (64 - abs(dy))              # the uncovered strip is black, not wrapped


def test_freeze_skips_update_keeps_drawing(font5x7):
    # Juice's half: frozen is true for the freeze's seconds and drawing goes on; the runner skips the game's
    # update while it is (test_runner.py, test_freeze_skips_the_games_update).
    fx = Juice(random.Random(0), (64, 64))
    canvas = Canvas(64, 64, font5x7)
    fx.freeze(0.2)
    fx.freeze(0.1)                                                   # a shorter freeze never cuts one short
    fx.burst(32, 32, WHITE)
    frozen = []
    for _ in range(9):
        canvas.frame[:] = 0
        fx.render(canvas)
        frozen.append(fx.frozen)
        assert canvas.frame.any()                                    # still drawn while frozen
        fx.update(TICK)
    assert frozen == [True] * 6 + [False] * 3
    assert fx.debug_state()["fx_frozen"] is False
    for bad in (math.nan, -1.0, None, "1"):
        fx.freeze(bad)
    assert not fx.frozen


def test_flash_rate_limited(font5x7):
    fx = Juice(random.Random(0), (64, 64))
    canvas = Canvas(64, 64, font5x7)
    assert fx.flash((200, 0, 0), 0.3)
    assert not fx.flash(WHITE, 0.3)                                  # one is showing: refused
    canvas.frame[:] = (0, 100, 0)
    fx.render(canvas)
    assert canvas.frame[0, 0].tolist() == [200, 100, 0]              # additive
    levels = [fx.debug_state()["fx_flash"]]
    for _ in range(23):
        fx.update(TICK)
        levels.append(fx.debug_state()["fx_flash"])
        assert not fx.flash(WHITE)                                   # refused until FLASH_GAP after it ended
    assert levels == [1.0] * 9 + [0.0] * 15                          # on for 0.3 s, then off: one rise, one fall
    fx.update(TICK)
    assert fx.t == pytest.approx(0.3 + FLASH_GAP) and fx.flash(WHITE, 0.1)
    canvas.frame[:] = (100, 100, 100)
    fx.render(canvas)
    assert canvas.frame[5, 5].tolist() == [255, 255, 255]            # clamped, never wrapped
    for bad in ((WHITE, 0.0), (WHITE, math.nan), (WHITE, -1), (None, 0.2)):
        fx.update(0.1 + FLASH_GAP)
        assert not fx.flash(*bad)


@pytest.mark.parametrize("effect", ["shake", "burst", "burst-spot", "flash", "flash-red"])
def test_effects_keep_the_flash_rule_by_themselves(font5x7, size, effect, monkeypatch):
    # it04 N11: an effect called as often as a game can, over a high-contrast frame (the shake) or black, must not
    # flash any of the wall past the governor's budget, saturated red included (the governor counts it three
    # ways, so a fading red flash would count three falls). The shake and the flash stay at 4 changes a second.
    # A shake whose sign alternated every tick would toggle every edge at 15 Hz; bursts at one spot every tick, or
    # flashes every few ticks, would flash too. With the effect's own limit taken away the same calls do flash,
    # so the limit is what keeps it.
    w, h = size
    red = (255, 0, 0)
    calls = {
        "shake": lambda fx, i: fx.shake(4, 0.5),
        "burst": lambda fx, i: fx.burst((i * 1.5) % w, h / 2 + (i % 5), WHITE),
        "burst-spot": lambda fx, i: fx.burst(w / 2, h / 2, red),
        "flash": lambda fx, i: i % 2 == 0 and fx.flash(WHITE, 0.03),
        "flash-red": lambda fx, i: i % 8 == 0 and fx.flash(red, 0.2),
    }
    base = checker(size) if effect == "shake" else None
    canvas = Canvas(w, h, font5x7)
    frames = run(Juice(random.Random(7), size), canvas, 150, calls[effect], base)
    assert flash_area(frames) == 0.0
    if effect in ("shake", "flash", "flash-red"):
        assert flash_area(frames, budget=4) == 0.0
    assert any(not np.array_equal(f, frames[0]) for f in frames)    # the effect did show
    limit = {"shake": "SHAKE_STEP", "flash": "FLASH_GAP", "flash-red": "FLASH_GAP"}.get(effect, "BURST_GAP")
    monkeypatch.setattr(juice, limit, 0.0)
    frames = run(Juice(random.Random(7), size), canvas, 150, calls[effect], base)
    assert flash_area(frames) > 0.0


def test_burst_near_a_recent_one_is_dropped():
    fx = Juice(random.Random(0), (128, 32))
    assert fx.burst(20, 16, WHITE)
    assert not fx.burst(20 + BURST_NEAR - 1, 16, WHITE)              # too near, too soon
    assert fx.burst(20 + BURST_NEAR, 16, WHITE)                      # far enough
    for _ in range(14):
        fx.update(TICK)
    assert not fx.burst(20, 16, WHITE)                               # 0.467 s: still too soon
    fx.update(TICK)                                                  # 0.5 s: BURST_GAP
    assert fx.burst(20, 16, WHITE)
    for bad in ((math.nan, 5, WHITE), (5, math.inf, WHITE), (5, 5, None), (5, 5, WHITE, True), (5, 5, WHITE, 2.5),
                ("5", 5, WHITE)):
        assert not fx.burst(*bad)


def test_particles_fly_at_one_speed_and_fade(font5x7):
    fx = Juice(random.Random(0), (64, 64))
    canvas = Canvas(64, 64, font5x7)
    fx.burst(32, 32, (0, 0, 240), n=8)
    for _ in range(6):
        fx.update(TICK)                                              # 0.2 s: 6 px out
    fx.render(canvas)
    ys, xs = np.nonzero(canvas.frame.any(axis=2))
    d = np.hypot(xs - 32, ys - 32)
    assert len(xs) >= 6 and np.all(np.abs(d - 6) <= 1.0)
    assert canvas.frame[ys, xs, 2].max() == 144 and canvas.frame[..., :2].max() == 0   # 240 x (1 - 0.2 / 0.5)


def test_pop_rises_six_pixels_then_goes(font5x7):
    fx = Juice(random.Random(0), (128, 32))
    canvas = Canvas(128, 32, font5x7)
    fx.pop("+1", 64, 20, (0, 255, 0))
    tops = []
    for _ in range(25):
        canvas.frame[:] = 0
        fx.render(canvas)
        ys, xs = np.nonzero(canvas.frame.any(axis=2))
        tops.append(int(ys.min()) if len(ys) else None)
        fx.update(TICK)
    assert tops[0] - tops[23] == POP_RISE and tops[24] is None
    assert tops[:24] == sorted(tops[:24], reverse=True)              # rising all the way
    assert fx.debug_state()["fx_pops"] == 0
    for i in range(12):
        fx.pop(str(i), 64, 20, (0, 255, 0))
    assert fx.debug_state()["fx_pops"] == juice.MAX_POPS == 8


def test_banner_is_boxed_and_ends(font5x7, size):
    w, h = size
    fx = Juice(random.Random(0), size)
    canvas = Canvas(w, h, font5x7)
    fx.banner("GO!", 0.5)
    canvas.frame[:] = (0, 0, 255)
    fx.render(canvas)
    white = np.all(canvas.frame == 255, axis=2)
    ys, xs = np.nonzero(white)
    assert ys.max() - ys.min() >= 12                                  # 2x glyphs, 14 px tall
    assert np.all(canvas.frame[ys.min() - 1, xs.min():xs.max() + 1] == 0)   # the black box
    assert fx.debug_state()["fx_banner"] == "GO!"
    fx.banner("A LONG BANNER HERE", 0.5)                              # too wide at 2x on either layout: 1x
    canvas.frame[:] = 0
    fx.render(canvas)
    ys, _ = np.nonzero(canvas.frame.any(axis=2))
    assert ys.max() - ys.min() <= 8
    for _ in range(15):
        fx.update(TICK)
    assert fx.debug_state()["fx_banner"] is None


def test_celebrate_bursts_across_the_wall_twice(font5x7):
    fx = Juice(random.Random(0), (128, 32))
    fx.celebrate((255, 200, 0))
    assert fx.debug_state()["fx_particles"] == 4 * juice.BURST_N    # four origins 32 px apart
    for _ in range(15):
        fx.update(TICK)
    assert fx.debug_state()["fx_particles"] == 4 * juice.BURST_N    # the second wave, 0.5 s on
    fx.update(BURST_LIFE)
    assert fx.debug_state()["fx_particles"] == 0


def test_markers_stay_on_the_bottom_row_and_echo_over_them(font5x7, size):
    w, h = size
    cal = Calibration()
    one = place(Person(x=0.3).body_at(0.0, 1), cal)
    two = place(Person(x=0.75).body_at(0.0, 2), cal)
    fx = Juice(random.Random(0), size)
    canvas = Canvas(w, h, font5x7)
    fx.shake(4, 1.0)
    fx.echo(1, "up")
    fx.echo(3, "up")                                                 # not a player: nothing
    fx.echo(2, "wave")                                               # not a kind: nothing
    assert fx.debug_state()["fx_echoes"] == 1
    for i in range(12):
        canvas.frame[:] = 0
        fx.render(canvas, player=one, player2=two)
        for body, color in ((one, PLAYER_COLORS[0]), (two, PLAYER_COLORS[1])):
            x = marker_x(body, w)
            assert canvas.frame[h - 1, x:x + 2].tolist() == [list(color)] * 2   # never shaken
        x = marker_x(one, w)
        echo = canvas.frame[h - 5:h - 2, x:x + 3]
        assert bool(np.all(echo[1] == PLAYER_COLORS[0])) == (i * TICK < ECHO_SECONDS - 1e-9), i
        fx.update(TICK)
    assert marker_x(one, w) < marker_x(two, w)
    edge = place(Person(x=0.95).body_at(0.0, 3), cal)
    assert marker_x(edge, w) == w - 2 and edge.zone_x == 1.0


def test_fx_keys_are_namespaced():
    fx = Juice(random.Random(0))
    state = fx.debug_state()
    assert set(state) == {"fx_shake", "fx_particles", "fx_frozen", "fx_flash", "fx_banner", "fx_pops", "fx_echoes"}
    assert state == {"fx_shake": [0, 0], "fx_particles": 0, "fx_frozen": False, "fx_flash": 0.0, "fx_banner": None,
                     "fx_pops": 0, "fx_echoes": 0}


def test_bad_numbers_do_nothing(font5x7):
    fx = Juice(random.Random(0), (64, 64))
    for px, seconds in ((math.nan, 1.0), (4, math.inf), (-4, 1.0), (None, 1.0), (4, "1"), (10**400, 1.0)):
        fx.shake(px, seconds)
    fx.pop("x", math.nan, 5, WHITE)
    fx.pop("x", 5, 5, None)
    fx.banner("x", math.nan)
    fx.update(math.nan)
    assert fx.t == 0.0
    assert fx.debug_state() == Juice(random.Random(0)).debug_state()
    canvas = Canvas(64, 64, font5x7)
    fx.render(canvas)
    assert not canvas.frame.any()


@pytest.mark.perf
def test_full_pool_under_half_ms(font5x7):
    seed = zlib.crc32(b"juice-perf")
    rng = random.Random(seed)
    fx = Juice(rng, (64, 64))
    canvas = Canvas(64, 64, font5x7)
    fx._bursts = []
    for i in range(8):
        fx.burst(8 + (i % 2) * 40, 8 + (i // 2) * 16, WHITE)
        fx._bursts = []                                              # fill the pool from nearby origins
    assert fx.debug_state()["fx_particles"] == MAX_PARTICLES
    fx.shake(3, 5.0)
    fx.flash((40, 40, 40), 5.0)
    fx.pop("+10", 32, 40, WHITE)
    fx.banner("GO!", 5.0)
    times = []
    for _ in range(200):
        canvas.frame[:] = 30
        t0 = time.thread_time()                                      # CPU time: the cost, not the load
        fx.render(canvas)
        times.append(time.thread_time() - t0)
    assert statistics.median(times) < 0.0005, f"seed={seed} median={statistics.median(times) * 1e3:.3f} ms"
```

- [ ] **Step 2: Run them to verify they fail**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_juice.py`

Expected: `1 error` at collection, with `ModuleNotFoundError: No module named 'arcade.juice'`.

- [ ] **Step 3: Implement**

`arcade/juice.py`:

```python
"""The effects toolkit (spec 8.1): one Juice per launch, runner-owned, seeded, passed to the game's reset().

A game calls shake, flash, burst, pop, banner, freeze, celebrate and echo from update(); the runner draws the
effects after the game's draw (render), advances them once a tick (update) and skips the game's update while
frozen. Shake, flash and bursts each keep the governor's flash rule by themselves (spec 7.6, it04 N11), whatever
the colour, saturated red included, which the governor counts three ways:

- shake jumps the frame from side to side along one axis, and the offset changes at most once every SHAKE_STEP
  (0.25 s). A jump changes each pixel once whatever the picture, so no pixel changes more than 4 times a second
  under a shake, under the 6 of the governor's budget. (A smooth shake would sweep fine detail across a pixel
  many times a cycle.)
- flash adds its colour for its seconds and stops: one rise and one fall. The next starts FLASH_GAP (0.5 s) after
  one ends, so no pixel changes more than 4 times a second. (A red flash fading over several frames counts up to
  three falls, one per way, and at 2 a second the governor would hold the whole wall.)
- burst particles all fly at BURST_SPEED for BURST_LIFE, so each passes a pixel once; a burst whose origin is
  within BURST_NEAR of one accepted in the last BURST_GAP (0.5 s) is dropped, so no pixel sees more than two
  bursts a second. That is 4 changes for most pixels; a few by the origin, which one particle takes two frames
  to cross or two cross in turn, reach the governor's 6 and no more.

Banner text, pops and effects together are the game's to pace: a banner whose text changes every tick, a pop
every tick, or bursts over a flash can flash a small part of the wall. The governor runs after all of it and
holds what goes over.

Numbers from a game are taken as they come: a NaN, an infinity, a negative duration or anything that is not a
number makes that call do nothing (and return False where it returns a bool). Nothing here raises into a game.
"""
from __future__ import annotations

import math
import random

import numpy as np

from arcade.canvas import Canvas, _c
from arcade.look import is_real
from arcade.sensed import Body
from show.font import CELL_H

MAX_PARTICLES = 96
SHAKE_STEP = 0.25        # seconds between two changes of the shake's offset: 4 a second at most
SHAKE_MAX = 8            # pixels
FLASH_GAP = 0.5          # seconds from the end of one flash to the start of the next
BURST_SPEED = 30.0       # px/s, every particle
BURST_LIFE = 0.5         # seconds: a burst reaches BURST_SPEED * BURST_LIFE = 15 px
BURST_GAP = 0.5          # seconds before another burst may start near an accepted one
BURST_NEAR = 32          # px: two particle discs of 15 px whose origins are this far apart never meet
BURST_N = 12             # particles in a burst by default
POP_RISE = 6             # px over POP_SECONDS
POP_SECONDS = 0.8
MAX_POPS = 8
ECHO_SECONDS = 0.25
ECHOES = {               # 3x3 glyphs drawn over a player's marker
    "up": (".#.", "###", "..."),
    "down": ("...", "###", ".#."),
    "hit": ("#.#", ".#.", "#.#"),
    "ok": (".#.", "###", ".#."),
}
PLAYER_COLORS = ((255, 120, 0), (0, 160, 255))    # player 1 amber, player 2 blue: low channels at 0 or near
CELEBRATE_GAP = 0.5      # seconds between celebrate's two waves


def _number(v) -> float | None:
    """v as a finite float, else None."""
    if not is_real(v):
        return None
    try:
        v = float(v)
    except OverflowError:
        return None
    return v if math.isfinite(v) else None


def _seconds(v) -> float | None:
    v = _number(v)
    return v if v is not None and v >= 0.0 else None


def marker_x(body: Body, width: int) -> int:
    """The left column of a player's 2 px marker on the bottom row: zone_x across the wall."""
    return max(0, min(width - 2, math.floor(body.zone_x * (width - 2) + 0.5)))


class Juice:
    """Effects for one launch, timed by update(dt). rng is the launch's random.Random (the shake's axis and the
    bursts' angles); size is the wall's (width, height), for celebrate. debug_state() gives the fx_* keys the
    runner merges into state()."""

    def __init__(self, rng: random.Random, size: tuple[int, int] = (128, 32)):
        self.rng, self.size = rng, size
        self.t = 0.0
        # shake: jumps of alternating sign whose size decays linearly from amp over [start, start + length)
        self._axis, self._sign = 0, 1
        self._amp, self._start, self._length = 0.0, 0.0, 0.0
        self._offset = (0, 0)
        self._moved = -math.inf                                      # when the offset last changed
        self._flash_color = (0, 0, 0)
        self._flash_start, self._flash_seconds = -math.inf, 0.0
        self._flash_end = -math.inf
        self._pos = np.zeros((MAX_PARTICLES, 2))
        self._vel = np.zeros((MAX_PARTICLES, 2))
        self._rgb = np.zeros((MAX_PARTICLES, 3))
        self._born = np.full(MAX_PARTICLES, -math.inf)
        self._next = 0
        self._bursts: list[tuple[float, float, float]] = []         # (t, x, y) of accepted bursts
        self._pops: list[tuple[float, str, float, float, tuple]] = []
        self._banner: tuple[str, float] | None = None               # (text, until)
        self._freeze_until = -math.inf
        self._waves: list[tuple[float, tuple]] = []                  # celebrate's second waves: (at, colour)
        self._echoes: dict[int, tuple[str, float]] = {}              # player -> (kind, until)

    # ----- what a game calls -----

    def shake(self, px, seconds) -> None:
        """Shake the frame by up to px pixels (at most SHAKE_MAX), decaying to 0 over seconds: the frame jumps to
        alternate sides at most every SHAKE_STEP. A shake while one runs restarts it if it is at least as big."""
        px, seconds = _seconds(px), _seconds(seconds)
        if px is None or seconds is None or px == 0.0 or seconds == 0.0:
            return
        px = min(px, float(SHAKE_MAX))
        if self._amplitude() == 0.0 and self._offset == (0, 0):
            self._axis, self._sign = self.rng.randrange(2), self.rng.choice((-1, 1))
        elif px < self._amplitude():
            return
        self._amp, self._start, self._length = px, self.t, seconds

    def flash(self, color, seconds=0.2) -> bool:
        """Add color to the whole frame for seconds, then stop: one rise and one fall. False (and nothing) while a
        flash shows or under FLASH_GAP after one ended."""
        seconds = _seconds(seconds)
        if seconds is None or seconds == 0.0 or self.t - self._flash_end < FLASH_GAP - 1e-9:
            return False
        try:
            self._flash_color = _c(color)
        except (TypeError, ValueError):
            return False
        self._flash_start, self._flash_seconds, self._flash_end = self.t, seconds, self.t + seconds
        return True

    def burst(self, x, y, color, n=BURST_N) -> bool:
        """n particles (1 to MAX_PARTICLES) from (x, y) in wall pixels, evenly spread round the circle, fading over
        BURST_LIFE. The pool keeps the newest MAX_PARTICLES. False (and nothing) for a burst within BURST_NEAR of
        one accepted in the last BURST_GAP."""
        x, y = _number(x), _number(y)
        if x is None or y is None or isinstance(n, bool) or not isinstance(n, (int, np.integer)):
            return False
        try:
            rgb = _c(color)
        except (TypeError, ValueError):
            return False
        n = max(1, min(MAX_PARTICLES, int(n)))
        self._bursts = [b for b in self._bursts if self.t - b[0] < BURST_GAP - 1e-9]
        if any(math.hypot(x - bx, y - by) < BURST_NEAR for _, bx, by in self._bursts):
            return False
        self._bursts.append((self.t, x, y))
        start = self.rng.random() * 2.0 * math.pi / n
        for i in range(n):
            a = start + 2.0 * math.pi * i / n
            k = self._next % MAX_PARTICLES
            self._pos[k] = (x, y)
            self._vel[k] = (BURST_SPEED * math.cos(a), BURST_SPEED * math.sin(a))
            self._rgb[k] = rgb
            self._born[k] = self.t
            self._next += 1
        return True

    def pop(self, text, x, y, color) -> None:
        """text centred on (x, y), rising POP_RISE pixels over POP_SECONDS; the newest MAX_POPS are kept."""
        x, y = _number(x), _number(y)
        if x is None or y is None:
            return
        try:
            rgb = _c(color)
        except (TypeError, ValueError):
            return
        self._pops = (self._pops + [(self.t, str(text), x, y, rgb)])[-MAX_POPS:]

    def banner(self, text, seconds=1.0) -> None:
        """text across the middle of the wall on a black box for seconds, at 2x when it fits; replaces a banner."""
        seconds = _seconds(seconds)
        if seconds is None:
            return
        self._banner = (str(text), self.t + seconds)

    def freeze(self, seconds) -> None:
        """Hit-stop: the runner skips the game's update for seconds and keeps drawing."""
        seconds = _seconds(seconds)
        if seconds is not None:
            self._freeze_until = max(self._freeze_until, self.t + seconds)

    def celebrate(self, color) -> None:
        """Bursts across the middle of the wall now and again after CELEBRATE_GAP."""
        self._wave(color)
        self._waves.append((self.t + CELEBRATE_GAP, color))

    def echo(self, player, kind) -> None:
        """Acknowledge a recognised gesture at once: kind's glyph over player 1's or 2's marker for ECHO_SECONDS."""
        if player in (1, 2) and not isinstance(player, bool) and kind in ECHOES:
            self._echoes[player] = (kind, self.t + ECHO_SECONDS)

    @property
    def frozen(self) -> bool:
        return self.t < self._freeze_until - 1e-9

    # ----- what the runner calls -----

    def update(self, dt: float) -> None:
        """Advance every effect by dt seconds (the runner's clamped tick)."""
        dt = _seconds(dt) or 0.0
        self.t += dt
        for at, color in [w for w in self._waves if w[0] <= self.t + 1e-9]:
            self._waves.remove((at, color))
            self._wave(color)
        self._pops = [p for p in self._pops if self.t - p[0] < POP_SECONDS - 1e-9]
        if self._banner is not None and self.t >= self._banner[1] - 1e-9:
            self._banner = None
        self._echoes = {p: e for p, e in self._echoes.items() if self.t < e[1] - 1e-9}

    def render(self, canvas: Canvas, player: Body | None = None, player2: Body | None = None) -> None:
        """Draw the effects over the game's frame: particles, pops, the banner and the flash, then the shake as a
        slice copy (black fills the gap), then the players' markers and echoes, which never shake."""
        frame = canvas.frame
        h, w = frame.shape[:2]
        self._draw_particles(frame)
        for at, text, x, y, rgb in self._pops:
            rise = POP_RISE * min(1.0, (self.t - at) / POP_SECONDS)
            canvas.text(x - canvas.text_width(text) / 2, y - CELL_H / 2 - rise, text, rgb)
        if self._banner is not None:
            text = self._banner[0]
            scale = 2 if canvas.text_width(text, 2) <= w - 2 and 2 * CELL_H <= h - 2 else 1
            tw, th = canvas.text_width(text, scale), CELL_H * scale
            x, y = (w - tw) // 2, (h - th) // 2
            canvas.fill_rect(x - 1, y - 1, tw + 2, th + 2, (0, 0, 0))
            canvas.text(x, y, text, (255, 255, 255), scale)
        level = self._flash_level()
        if level > 0.0:
            add = np.array(self._flash_color, np.float64) * level
            frame[:] = np.minimum(frame + np.floor(add + 0.5).astype(np.uint16), 255).astype(np.uint8)
        self._shake_step()
        dx, dy = self._offset
        if dx or dy:
            shifted = np.zeros_like(frame)
            shifted[max(dy, 0):h + min(dy, 0), max(dx, 0):w + min(dx, 0)] = \
                frame[max(-dy, 0):h + min(-dy, 0), max(-dx, 0):w + min(-dx, 0)]
            frame[:] = shifted
        for number, body in ((1, player), (2, player2)):
            if body is None:
                continue
            x, color = marker_x(body, w), PLAYER_COLORS[number - 1]
            canvas.fill_rect(x, h - 1, 2, 1, color)
            echo = self._echoes.get(number)
            if echo is not None:
                glyph = np.array([[ch == "#" for ch in row] for row in ECHOES[echo[0]]])
                canvas.blit(glyph, min(x, w - 3), h - 5, color)

    def debug_state(self) -> dict:
        return {"fx_shake": list(self._offset), "fx_particles": int(self._alive().sum()), "fx_frozen": self.frozen,
                "fx_flash": round(self._flash_level(), 3), "fx_banner": None if self._banner is None else
                self._banner[0], "fx_pops": len(self._pops), "fx_echoes": len(self._echoes)}

    # ----- inside -----

    def _wave(self, color) -> None:
        w, h = self.size
        for x in range(BURST_NEAR // 2, w, BURST_NEAR):
            self.burst(x, h / 2, color)

    def _alive(self) -> np.ndarray:
        return self.t - self._born < BURST_LIFE - 1e-9

    def _draw_particles(self, frame: np.ndarray) -> None:
        alive = self._alive()
        if not alive.any():
            return
        age = (self.t - self._born[alive])[:, None]
        pos = np.floor(self._pos[alive] + self._vel[alive] * age + 0.5).astype(np.int64)
        rgb = np.floor(self._rgb[alive] * (1.0 - age / BURST_LIFE) + 0.5).astype(np.uint8)
        h, w = frame.shape[:2]
        inside = (pos[:, 0] >= 0) & (pos[:, 0] < w) & (pos[:, 1] >= 0) & (pos[:, 1] < h)
        frame[pos[inside, 1], pos[inside, 0]] = rgb[inside]

    def _flash_level(self) -> float:
        age = self.t - self._flash_start
        return 1.0 if 0.0 <= age < self._flash_seconds - 1e-9 else 0.0

    def _amplitude(self) -> float:
        if self._length <= 0.0:
            return 0.0
        return max(0.0, self._amp * (1.0 - (self.t - self._start) / self._length))

    def _shake_step(self) -> None:
        """Move the offset to the other side at the envelope's size, at most once every SHAKE_STEP."""
        if self.t - self._moved < SHAKE_STEP - 1e-9:
            return
        v = self._sign * math.floor(self._amplitude() + 0.5)
        offset = (v, 0) if self._axis == 0 else (0, v)
        if offset != self._offset:
            self._offset, self._moved, self._sign = offset, self.t, -self._sign
```

- [ ] **Step 4: Run the tests**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_juice.py`

Expected: `26 passed`.

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`

Expected: `364 passed`, no skips.

- [ ] **Step 5: Commit**

```bash
git add arcade/juice.py tests/arcade/test_juice.py
git commit -m "feat(arcade): Juice effects that keep the flash rule by themselves: jump shake, held flash, spaced bursts at one speed, pops, banner, freeze, celebrate, echo and markers (core Task 8 part)" -m "Shake, flash and bursts each keep the rule alone; banner text, pops and combinations are the game's to pace, and the governor catches the rest. The shake jumps at most every 0.25 s (Q18 defaulted) and a flash is a hold, one rise and one fall, with 0.5 s from its end to the next (Q20 defaulted): at most 4 changes a second each, saturated red included. A burst near one from the last 0.5 s is dropped (Q19): most pixels see at most 4 changes a second, a few by the origin reach the governor's 6 and no more. Bad numbers make a call do nothing. The 2 px player markers and echo glyphs sit on the bottom row and never shake." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: The runner (core Task 8 part, it02 C10 runner half, it03 C21 Task 8 part)

**Files:**
- Create: `arcade/runner.py`, `arcade/headless.py` (this task's version: `OPENING_NIGHT` and `RecordingDisplay`), `tests/arcade/helpers.py` (this task's version, without `run`)
- Test: `tests/arcade/test_runner.py`

**Interfaces:**
- Consumes:
  - Task 1's `SessionLog` and `TORSO_FLOOR`, and Task 2's `Juice`;
  - it04's `BrightnessLimiter(cfg, clock=, lux=)`, `FlashGovernor(h, w, gamma, fps=)`, `Hold`, `capture_grace`, `EPSILON`, `Game`, `GameInfo`, `RUNNER_KEYS`, `icon_from_rows`, `Scores(path, clock)` with `for_game` and `best`;
  - `Calibration`, `Canvas`, `ArcadeConfig`, `Sensed.with_motion` and `show.font.CELL_H`.
- Produces:
  - `arcade.runner`:
    - `MAX_DT`, `CAMERA_STALE`, `AUDIO_STALE`, `CLOCK_SLACK`, `MAX_CRASHES`, `CRASH_SECONDS`, `CRASH_RED`, `PROMPT_SECONDS`, `PROMPT`, `SWITCH_RATIO`, `SWITCH_SECONDS`, `REACQUIRE_DISTANCE`, `BLOB_SPEED`, `LOG_EVERY`, `LOBBY` and `RING`;
    - `SessionResult(game, layout, reason, score, duration, players, best, waiting)`, frozen;
    - `LobbyLike`, a `Protocol`: a `Game` plus `request` (read and set to None inside the lobby guard), `set_available(names)`, `set_status(camera_ok, mic_ok, inputs, calibrated)` and `end_session(result)`;
    - `PlayerLock(lost_seconds)`, with `update(bodies, t) -> (player, player2)` and `reset()`;
    - `Presence(on_seconds, off_seconds, grace)`, with `update(evidence, t) -> bool`, `present` and `last_seen`;
    - `moving_blob(before, now, seconds) -> bool`.
  - `Runner(cfg, display, font, lobby, games, seed=0, clock=time.monotonic, sleep=time.sleep, log=None, scores=None, sessions=None, calibration=None, strict=False, local_clock=datetime.now, lux=None)`:
    - methods `tick(sensed, dt)` (the game sees `sensed` with `t` set to the runner's own clock `runner.t`, and `camera_t` moved by the same amount), `sense(camera, audio) -> Sensed` (a `latest()` of the wrong shape, or stamped with a non-finite time or one over `CLOCK_SLACK` past the clock, counts as a failed source), `loop(camera, audio, max_ticks=None)`, `state() -> dict`, `launch(name) -> bool` (False while a game runs, and for a non-string, unknown or hidden name; allowed in the lobby and during the crash icon, which it ends), `end_session(reason) -> SessionResult` and `available() -> set[str]`;
    - attributes `game` (the last launched instance), `current`, `current_name`, `fx`, `t`, `crashes`, `hidden`, `last_error`, `player`, `player2`, `limiter`, `governor`, `grace`, `lock`, `presence`, `scores`, `sessions`, `trace`, `raw_frames` and `running`.
  - `arcade.headless`:
    - `OPENING_NIGHT = datetime(2026, 11, 11, 21, 0)`;
    - `RecordingDisplay(keep_all=True)`, with `frames`, `last`, `count`, `brightness`, `closed`, `push`, `set_brightness` and `close`.
  - `tests.arcade.helpers`:
    - `make_cfg(size, **over)`, `spy_info(name="spy", **over)`, `spy(name="spy", info=None, **attrs) -> type`;
    - `SpyGame`, configured by `raise_in` (any of `init`, `reset`, `update`, `draw`, `done`, `debug_state`), `finish_after` and `extra`;
    - `StubLobby(raise_in=frozenset())`, `FakeClock(now=100.0)`, `BLANK_ICON` and `CROSS_ICON`.

Task 4 replaces `arcade/headless.py` and `tests/arcade/helpers.py` with versions that add to these and change none of them.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/helpers.py` (this task's version):

```python
"""Test helpers: configs, a spy game, a stub lobby and a fake clock."""
from __future__ import annotations

import random
from dataclasses import replace

from arcade.canvas import Canvas
from arcade.config import ArcadeConfig
from arcade.game import Game, GameInfo, icon_from_rows
from arcade.sensed import Sensed

BLANK_ICON = icon_from_rows(["." * 16] * 16)
CROSS_ICON = icon_from_rows(["#" * 16] * 2 + ["##" + "." * 12 + "##"] * 12 + ["#" * 16] * 2)


def make_cfg(size: tuple[int, int], **over) -> ArcadeConfig:
    return replace(ArcadeConfig(width=size[0], height=size[1], backend="fake", camera="none", audio="none"), **over)


def spy_info(name: str = "spy", **over) -> GameInfo:
    return GameInfo(**(dict(name=name, title=name.title(), verb="SPY", icon=CROSS_ICON, needs=frozenset({"pose"}))
                       | over))


class SpyGame(Game):
    """Records calls. Class attributes configure it: raise_in names the methods that raise ("init", "reset",
    "update", "draw", "done", "debug_state"), finish_after ends the game after that many updates, extra adds to
    debug_state."""

    info = spy_info()
    raise_in: frozenset[str] = frozenset()
    finish_after: int | None = None
    extra: dict = {}

    def __init__(self):
        if "init" in self.raise_in:
            raise RuntimeError("boom in init")
        self.updates = self.draws = 0
        self.size = self.rng = self.fx = self.scores_at_reset = None
        self.seen: list[Sensed] = []

    def reset(self, size, rng: random.Random, fx) -> None:
        self.scores_at_reset = getattr(self, "scores", None)
        if "reset" in self.raise_in:
            raise RuntimeError("boom in reset")
        self.size, self.rng, self.fx = size, rng, fx

    def update(self, sensed: Sensed, dt: float) -> None:
        self.updates += 1
        self.seen.append(sensed)
        if "update" in self.raise_in:
            raise RuntimeError("boom in update")

    def draw(self, canvas: Canvas) -> None:
        self.draws += 1
        if "draw" in self.raise_in:
            raise RuntimeError("boom in draw")
        canvas.pixel(0, 0, (255, 255, 255))

    def done(self) -> bool:
        if "done" in self.raise_in:
            raise RuntimeError("boom in done")
        return self.finish_after is not None and self.updates >= self.finish_after

    def debug_state(self) -> dict:
        if "debug_state" in self.raise_in:
            raise RuntimeError("boom in debug_state")
        return {"updates": self.updates, **self.extra}


def spy(name: str = "spy", info: dict | None = None, **attrs) -> type:
    """A SpyGame subclass called name, with GameInfo fields info and class attributes attrs."""
    return type(name.title(), (SpyGame,), {"info": spy_info(name, **(info or {})), **attrs})


class StubLobby:
    """A lobby that records what the runner tells it. Set request to launch a game on the next tick."""

    info = None

    def __init__(self, raise_in: frozenset[str] = frozenset()):
        self.raise_in = raise_in
        self.request: str | None = None
        self.available: set[str] | None = None
        self.status = None
        self.results: list = []
        self.resets = self.updates = 0
        self.seen: list[Sensed] = []

    def reset(self, size, rng, fx=None) -> None:
        self.resets += 1

    def update(self, sensed: Sensed, dt: float) -> None:
        self.updates += 1
        self.seen.append(sensed)
        if "update" in self.raise_in:
            raise RuntimeError("lobby boom")

    def draw(self, canvas: Canvas) -> None:
        canvas.pixel(1, 0, (0, 255, 0))

    def done(self) -> bool:
        return False

    def debug_state(self) -> dict:
        return {"request": self.request}

    def set_available(self, names: set[str]) -> None:
        self.available = set(names)

    def set_status(self, camera_ok: bool, mic_ok: bool, inputs: set[str], calibrated: bool) -> None:
        self.status = (camera_ok, mic_ok, set(inputs), calibrated)

    def end_session(self, result) -> None:
        self.results.append(result)


class FakeClock:
    def __init__(self, now: float = 100.0):
        self.now = now

    def __call__(self) -> float:
        return self.now

    def sleep(self, s: float) -> None:
        self.now += s
```

`tests/arcade/test_runner.py`:

```python
import logging
import json
import math
import random
import zlib
from datetime import datetime

import numpy as np
import pytest

from arcade.calibration import Calibration
from arcade.canvas import Canvas
from arcade.flash import flash_area
from arcade.game import RUNNER_KEYS
from arcade.headless import OPENING_NIGHT, RecordingDisplay
from arcade.input import capture_grace
from arcade.juice import Juice
from arcade.runner import CLOCK_SLACK, CRASH_RED, CRASH_SECONDS, MAX_DT, PROMPT_SECONDS, RING, Runner, SessionResult
from arcade.scores import GameScores, SessionLog
from arcade.sensed import Audio, Blob, Sensed, place_blob
from arcade.sources.actors import REAL_NOISE, TICK, Person, crowd, degrade, moving_blob, scene
from tests.arcade.helpers import CROSS_ICON, FakeClock, SpyGame, StubLobby, make_cfg, spy

SIZE = (64, 64)
WHITE = (255, 255, 255)
LAMP = lambda t: Blob(0.5, 0.5, 0.02, (255, 200, 0))             # parked in the zone


def make_runner(font, games=(SpyGame,), lobby=None, display=None, cfg=None, **kw):
    cfg = cfg or make_cfg(SIZE)
    display = display or RecordingDisplay()
    lobby = lobby or StubLobby()
    kw = {"seed": 1, "local_clock": lambda: OPENING_NIGHT} | kw
    return Runner(cfg, display, font, lobby, list(games), **kw), display, lobby


def feed(runner, frames, dt=TICK):
    for s in frames:
        runner.tick(s, dt)


def ticks(seconds):
    return round(seconds / TICK)


def stand(**kw):
    """One person standing in the zone for the whole scene."""
    return scene(persons=[Person(id=1)], **kw)


class Strobe(SpyGame):
    """The whole wall white and black on alternate ticks."""

    info = spy("strobe").info

    def draw(self, canvas):
        canvas.clear(WHITE if self.draws % 2 else (0, 0, 0))
        self.draws += 1


class Smear(SpyGame):
    """Paints the whole wall, then raises: a crash in draw must leave only the icon."""

    def draw(self, canvas):
        canvas.clear(WHITE)
        raise RuntimeError("boom in draw")


def test_starts_in_lobby_and_sets_brightness(font5x7):
    runner, display, lobby = make_runner(font5x7, cfg=make_cfg(SIZE, brightness=0.25))
    assert runner.current is lobby and display.brightness == 0.25 and lobby.resets == 1
    assert lobby.available == {"spy"} and runner.game is None
    feed(runner, scene(ticks=2))
    assert display.count == 2 and lobby.updates == 2
    state = runner.state()
    assert state["game"] == "lobby" and state["request"] is None and state["attract"] is True
    assert display.last[0, 1].tolist() == [0, 255, 0]                 # the lobby drew


def test_lobby_request_launches_next_tick(font5x7, caplog):
    runner, display, lobby = make_runner(font5x7)
    lobby.request = "spy"
    feed(runner, scene(ticks=1))
    assert runner.current_name == "spy" and isinstance(runner.game, SpyGame) and lobby.request is None
    assert runner.game.size == SIZE and runner.game.updates == 0
    feed(runner, scene(ticks=1))
    assert runner.game.updates == 1 and runner.state()["updates"] == 1 and runner.state()["game"] == "spy"
    runner.end_session("exit")
    lobby.request = "nope"
    with caplog.at_level(logging.WARNING, logger="arcade"):
        feed(runner, scene(ticks=1))
    assert runner.current_name == "lobby" and "nope" in caplog.text


def test_scores_view_and_fx_given_before_reset(font5x7):
    runner, _, _ = make_runner(font5x7)
    assert runner.launch("spy")
    game = runner.game
    assert isinstance(game.scores_at_reset, GameScores)
    assert (game.scores.name, game.scores.layout) == ("spy", "64x64") and isinstance(game.fx, Juice)
    first = game.rng.random()
    again, _, _ = make_runner(font5x7)
    again.launch("spy")
    assert again.game.rng.random() == first                          # seeded: the same seed, the same launch
    again.launch("spy")
    assert again.game.rng.random() != first                          # a second launch is another run
    assert first == pytest.approx(random.Random(zlib.crc32(b"1:spy:1")).random())


def test_done_returns_to_lobby_with_result(font5x7):
    sessions = SessionLog(None)
    done = spy(finish_after=3, extra={"score": np.int64(7)})
    runner, display, lobby = make_runner(font5x7, games=(done,), sessions=sessions)
    runner.launch("spy")
    feed(runner, stand(ticks=2))
    assert runner.current_name == "spy"
    feed(runner, stand(ticks=1))
    assert runner.current is lobby and runner.game.updates == 3      # the launched instance is kept
    (result,) = lobby.results
    assert isinstance(result, SessionResult)
    assert (result.game, result.layout, result.reason, result.score, result.players) == ("spy", "64x64", "done", 7,
                                                                                         1)
    assert result.duration == pytest.approx(3 * TICK) and result.best is None and result.waiting is False
    record = sessions.records[0]
    assert record["reason"] == "done" and record["score"] == 7.0 and record["start"] == "2026-11-11T21:00:00"


@pytest.mark.parametrize("where", ["init", "reset", "update", "draw", "done", "debug_state"])
def test_init_reset_and_done_raises_are_guarded(font5x7, where, caplog):
    sessions = SessionLog(None)
    runner, display, lobby = make_runner(font5x7, games=(spy(raise_in=frozenset({where})),), sessions=sessions)
    with caplog.at_level(logging.ERROR, logger="arcade"):
        started = runner.launch("spy")
        feed(runner, stand(ticks=1))
    assert started is (where not in ("init", "reset"))
    assert runner.crashes == {"spy": 1} and f"boom in {where}" in runner.last_error
    assert "game spy crashed" in caplog.text and sessions.records[-1]["reason"] == "crash"
    assert lobby.results[-1].reason == "crash"
    feed(runner, stand(ticks=ticks(CRASH_SECONDS) + 1))
    assert runner.current is lobby and runner.state()["glitch"] is False


@pytest.mark.parametrize("game", [spy(raise_in=frozenset({"update"})), Smear], ids=["update", "draw"])
def test_crash_shows_static_dim_icon_then_lobby(font5x7, game):
    assert CRASH_SECONDS == 0.5 and CRASH_RED == (96, 0, 0)            # loop decision 17
    runner, display, lobby = make_runner(font5x7, games=(game,))
    runner.launch("spy")
    feed(runner, stand(ticks=1))
    assert runner.state()["glitch"] is True and runner.state()["game"] == "spy"
    frames = [display.last]
    while runner.state()["glitch"]:
        feed(runner, stand(ticks=1))
        frames.append(display.last)
    assert len(frames) == ticks(CRASH_SECONDS) + 1
    lit = frames[0].any(axis=2)
    assert lit.sum() == CROSS_ICON.sum() and frames[0][..., 1:].max() == 0   # only the icon, never half a frame
    assert frames[0][lit, 0].max() == CRASH_RED[0]                     # dim: 96 at most
    reds = [int(f[..., 0].max()) for f in frames[:-1]]
    assert reds == sorted(reds, reverse=True) and reds[-1] < 40        # one slow fade, never a strobe
    assert all(np.array_equal(f.any(axis=2), lit) for f in frames[:-1] if f.any())   # static: the same pixels
    assert frames[-1][0, 1].tolist() == [0, 255, 0]                    # then the lobby


def test_crash_hides_after_three(font5x7):
    runner, display, lobby = make_runner(font5x7, games=(spy(raise_in=frozenset({"draw"})), spy("paint")))
    for n in range(1, 4):
        lobby.request = "spy"
        feed(runner, stand(ticks=2 + ticks(CRASH_SECONDS)))
        assert runner.crashes["spy"] == n and runner.current is lobby
    assert runner.hidden == {"spy"} and lobby.available == {"paint"} and runner.state()["hidden"] == ["spy"]
    lobby.request = "spy"
    feed(runner, stand(ticks=2))
    assert runner.current is lobby and runner.crashes["spy"] == 3
    lobby.request = "paint"
    feed(runner, stand(ticks=1))
    assert runner.current_name == "paint"


def test_crash_icon_has_no_game_keys_and_the_log_keeps_the_last_score(font5x7):
    # Loop decisions 16 and 24: the lobby's result and the session log carry the last score the game reported,
    # and state() during the icon has none of the game's keys. A crash at launch reports no score, never a key
    # of the lobby's.
    class Late(SpyGame):
        extra = {"score": 5}

        def update(self, sensed, dt):
            super().update(sensed, dt)
            if self.updates == 3:
                raise RuntimeError("late")

    sessions = SessionLog(None)
    broken = spy("broken", raise_in=frozenset({"reset"}))
    runner, _, lobby = make_runner(font5x7, games=(Late, broken), sessions=sessions)
    runner.launch("spy")
    feed(runner, stand(ticks=3))
    state = runner.state()
    assert state["glitch"] is True and "score" not in state and "updates" not in state
    assert lobby.results[-1].score == 5 and sessions.records[-1]["score"] == 5.0
    feed(runner, stand(ticks=ticks(CRASH_SECONDS) + 1))
    lobby.debug_state = lambda: {"request": None, "score": 99}
    feed(runner, stand(ticks=1))
    assert runner.state()["score"] == 99                               # the lobby's own key
    assert not runner.launch("broken")
    assert lobby.results[-1].score is None and sessions.records[-1]["score"] is None


def test_strict_reraises(font5x7):
    runner, _, _ = make_runner(font5x7, games=(spy(raise_in=frozenset({"update"})),), strict=True)
    runner.launch("spy")
    with pytest.raises(RuntimeError, match="boom in update"):
        feed(runner, stand(ticks=1))
    runner, _, _ = make_runner(font5x7, games=(spy(raise_in=frozenset({"init"})),), strict=True)
    with pytest.raises(RuntimeError, match="boom in init"):
        runner.launch("spy")
    runner, _, _ = make_runner(font5x7, lobby=StubLobby(raise_in=frozenset({"update"})), strict=True)
    with pytest.raises(RuntimeError, match="lobby boom"):
        feed(runner, scene(ticks=1))


def test_last_error_holds_traceback(font5x7):
    runner, _, _ = make_runner(font5x7, games=(spy(raise_in=frozenset({"draw"})),))
    assert runner.last_error is None
    runner.launch("spy")
    feed(runner, stand(ticks=1))
    assert runner.last_error.startswith("Traceback (most recent call last)")
    assert "RuntimeError: boom in draw" in runner.last_error and "def draw" not in runner.last_error


def test_lobby_crash_falls_back_to_title_card(font5x7, caplog):
    lobby = StubLobby(raise_in=frozenset({"update"}))
    runner, display, _ = make_runner(font5x7, lobby=lobby)
    with caplog.at_level(logging.ERROR, logger="arcade"):
        feed(runner, scene(ticks=3))
    assert lobby.updates == 1 and "lobby boom" in runner.last_error and "title card" in caplog.text
    assert runner.state()["title_card"] is True and runner.state()["game"] == "lobby"
    assert display.last.any() and display.last[0, 1].tolist() == [0, 0, 0]   # the card, not the lobby
    runner.launch("spy")
    feed(runner, stand(ticks=2))
    runner.end_session("exit")
    feed(runner, scene(ticks=1))
    assert runner.state()["title_card"] is True and runner.hidden == set()   # the lobby is never hidden
    assert lobby.updates == 1 and lobby.results == []                  # the broken lobby is never called again


def test_state_runner_keys_win(font5x7):
    greedy = spy(extra={"t": "mine", "present": "mine", "fx_shake": "mine", "phase": "play", "crashes": "mine"})
    runner, _, _ = make_runner(font5x7, games=(greedy,))
    runner.launch("spy")
    feed(runner, stand(ticks=40))
    state = runner.state()
    assert set(RUNNER_KEYS) <= set(state)
    assert state["t"] == pytest.approx(40 * TICK, abs=1e-3) and state["present"] is True and state["crashes"] == {}
    assert state["fx_shake"] == [0, 0] and state["phase"] == "play" and state["updates"] == 40
    assert state["player"] == 1 and state["glitch"] is False and state["flash_held_ticks"] == 0
    assert state["attract"] is False and state["idle"] == 0.0 and state["game"] == "spy"


def test_fx_keys_in_runner_state(font5x7):
    class Bursting(SpyGame):
        def update(self, sensed, dt):
            super().update(sensed, dt)
            if self.updates == 1:
                self.fx.burst(32, 32, WHITE)

    runner, display, lobby = make_runner(font5x7, games=(Bursting,))
    feed(runner, scene(ticks=1))
    assert not any(k.startswith("fx_") for k in runner.state())       # the lobby has no effects
    runner.launch("spy")
    feed(runner, stand(ticks=1))
    state = runner.state()
    assert state["fx_particles"] == 12 and {"fx_shake", "fx_frozen", "fx_flash", "fx_banner"} <= set(state)
    assert display.last.any(axis=2).sum() > 1                          # the particles reached the wall


def test_freeze_skips_the_games_update(font5x7):
    class Freezing(SpyGame):
        def update(self, sensed, dt):
            super().update(sensed, dt)
            if self.updates == 1:
                self.fx.freeze(0.2)

    runner, _, _ = make_runner(font5x7, games=(Freezing,))
    runner.launch("spy")
    counts = []
    for s in stand(ticks=10):
        runner.tick(s, TICK)
        counts.append((runner.game.updates, runner.game.draws, runner.state()["fx_frozen"]))
    assert [c[0] for c in counts] == [1, 1, 1, 1, 1, 1, 2, 3, 4, 5]    # six ticks frozen: no update
    assert [c[1] for c in counts] == list(range(1, 11))               # drawn every tick
    assert counts[0][2] is True and counts[-1][2] is False


def test_the_game_shakes_and_the_overlays_do_not(font5x7):
    # The tick order: the game draws, Juice renders (its shake moves the game's picture), then the overlays, so
    # the exit ring is drawn where the player is and never shakes.
    class Shaken(SpyGame):
        def update(self, sensed, dt):
            super().update(sensed, dt)
            if self.updates == 1:
                self.fx.shake(8, 6.0)

        def draw(self, canvas):
            canvas.pixel(32, 20, WHITE)

    runner, display, _ = make_runner(font5x7, games=(Shaken,))
    runner.launch("spy")
    checked = 0
    for s in scene(persons=[Person(id=1).both_hands_up(at=0.0, seconds=2.5)], ticks=ticks(2.5)):
        runner.tick(s, TICK)
        dx, dy = runner.state()["fx_shake"]
        progress = runner._exit.progress
        if not (dx or dy) or progress == 0.0:
            continue
        ring = Canvas(*SIZE, font5x7)
        ring.circle(runner.player.zone_x * (SIZE[0] - 1), SIZE[1] / 2,
                    (1.0 - progress) * (min(SIZE) / 2 - 2) + 1, RING)
        drawn = ring.frame.any(axis=2)
        assert np.array_equal(np.all(display.last == RING, axis=2), drawn)          # the ring, unshaken
        if not drawn[20 + dy, 32 + dx]:
            assert np.argwhere(np.all(display.last == WHITE, axis=2)).tolist() == [[20 + dy, 32 + dx]]   # shaken
            checked += 1
    assert checked > ticks(1.0)


def test_governor_and_limiter_are_built_from_the_runners_settings(font5x7):
    # it04 B4: the governor counts a second at cfg.fps, so at 60 ticks a second a strobe still shows at most 3
    # flashes a second; the limiter reads the lux callable the runner was given.
    lux = lambda: 500.0
    runner, display, _ = make_runner(font5x7, games=(Strobe,), cfg=make_cfg(SIZE, fps=60), lux=lux)
    assert runner.governor.fps == 60 and runner.limiter.lux is lux
    runner.launch("strobe")
    feed(runner, stand(ticks=120), dt=1 / 60)
    assert flash_area(display.frames, fps=60) == 0.0 and runner.governor.held_ticks > 0


def test_crowd_of_six_never_steals_the_player(font5x7):
    runner, _, _ = make_runner(font5x7)
    runner.launch("spy")
    frames = degrade(scene(persons=[Person(x=0.5, id=1)] + crowd(6), ticks=ticks(6.0)), **REAL_NOISE)
    ids = []
    for s in frames:
        runner.tick(s, TICK)
        ids.append(runner.state()["player"])
    assert set(ids[ticks(0.2):]) == {1}                               # after the camera's first capture
    assert runner.player2 is None                                     # the crowd is out of the zone


def test_player_switches_after_1_3x_for_one_second(font5x7):
    runner, _, _ = make_runner(font5x7)
    small = Person(x=0.35, height=0.5, id=1)
    big = Person(x=0.65, height=0.7, id=2).arrive(1.0)                # 1.4 times the scale
    ids = []
    for s in scene(persons=[small, big], ticks=ticks(3.0)):
        runner.tick(s, TICK)
        ids.append((runner.player.id, None if runner.player2 is None else runner.player2.id))
    switch = ids.index((2, 1))
    assert set(ids[:ticks(1.0)]) == {(1, None)} and set(ids[ticks(1.0):switch]) == {(1, 2)}
    assert switch == ticks(2.0) and set(ids[switch:]) == {(2, 1)}      # one second after the rival came
    runner, _, _ = make_runner(font5x7)
    close = Person(x=0.65, height=0.6, id=2).arrive(1.0)              # 1.2 times: never switches
    feed(runner, scene(persons=[Person(x=0.35, height=0.5, id=1), close], ticks=ticks(4.0)))
    assert runner.player.id == 1 and runner.player2.id == 2


def test_player_reacquired_by_position_keeps_slot(font5x7):
    runner, _, _ = make_runner(font5x7)
    lost = Person(x=0.4, height=0.7, id=1).leave(1.0)
    other = Person(x=0.75, height=0.5, id=3)                          # in the zone all along, smaller
    far = Person(x=0.2, height=0.7, id=8).arrive(1.05)                # new, but a third of the zone away
    back = Person(x=0.42, height=0.7, id=7).arrive(1.25)              # re-detected: a new id, nearby
    seen = []
    for s in scene(persons=[lost, other, far, back], ticks=ticks(2.0)):
        runner.tick(s, TICK)
        seen.append((None if runner.player is None else runner.player.id,
                     None if runner.player2 is None else runner.player2.id))
    assert seen[ticks(1.0) - 1] == (1, 3)
    assert {p for p, _ in seen[ticks(1.0):ticks(1.25)]} == {None}     # the slot is kept, empty
    assert {p2 for _, p2 in seen[ticks(1.1):ticks(1.25)]} == {8}      # the far one is only the second body
    assert {p for p, _ in seen[ticks(1.25):]} == {7}                  # the new id by the old place keeps it
    runner, _, _ = make_runner(font5x7)
    beside = Person(x=0.45, height=0.5, id=3)                         # there all along, next to the player
    ids = []
    for s in scene(persons=[Person(x=0.35, height=0.7, id=1).leave(1.0), beside], ticks=ticks(1.6)):
        runner.tick(s, TICK)
        ids.append(None if runner.player is None else runner.player.id)
    assert set(ids[ticks(1.0):ticks(1.45)]) == {None}                 # a body that was there is not the player back
    assert set(ids[ticks(1.55):]) == {3}                              # nobody came back: the lock moves on


def test_presence_hysteresis_ignores_out_of_zone(font5x7):
    runner, _, _ = make_runner(font5x7)
    feed(runner, scene(persons=crowd(6), ticks=ticks(3.0)))
    assert runner.state()["present"] is False                         # out of the zone: never present
    runner, _, _ = make_runner(font5x7)
    present = []
    for s in scene(persons=[Person(id=1).leave(3.0)], ticks=ticks(7.0)):
        runner.tick(s, TICK)
        present.append(runner.state()["present"])
    on, off = present.index(True), present.index(False, present.index(True))
    assert on == ticks(1.0) and off == ticks(6.0) - 1                 # on after 1 s, off 3 s after leaving
    assert runner.state()["idle"] == pytest.approx(4.0, abs=0.05)                  # since the last sighting
    runner, _, _ = make_runner(font5x7)
    feed(runner, scene(blobs=[LAMP], ticks=ticks(3.0)))
    assert runner.state()["present"] is False                         # a parked light is a lamp, not a person
    carried = moving_blob(0.25, 0.5, 0.75, 0.5, 3.0)                  # a sixth of the frame a second
    for frames in (scene(blobs=[carried], ticks=ticks(1.5)),
                   degrade(scene(blobs=[carried], ticks=ticks(1.5)), **REAL_NOISE)):
        runner, _, _ = make_runner(font5x7)
        feed(runner, frames)
        assert runner.state()["present"] is True                      # at 30 and at 10 captures a second
    runner, _, _ = make_runner(font5x7)
    feed(runner, scene(blobs=[moving_blob(0.1, 0.25, 0.1, 0.75, 3.0)], ticks=ticks(2.0)))
    assert runner.state()["present"] is False                         # moving, but left of the zone
    runner, _, _ = make_runner(font5x7)
    feed(runner, degrade(scene(blobs=[moving_blob(0.4, 0.5, 0.49, 0.5, 3.0)], ticks=ticks(2.0)), **REAL_NOISE))
    assert runner.state()["present"] is False                         # drifting 0.03 a second, timed by camera_t


def ended(runner, lobby, frames):
    """Feed frames and return (the reason the first session ended, the runner time it ended) or None."""
    for s in frames:
        runner.tick(s, TICK)
        if lobby.results:
            return lobby.results[0].reason, runner.t
    return None


def test_leave_ends_session_with_card(font5x7):
    runner, _, lobby = make_runner(font5x7, cfg=make_cfg(SIZE, leave_seconds=2.0))
    runner.launch("spy")
    reason, t = ended(runner, lobby, scene(persons=[Person(id=1).leave(1.0)], blobs=[LAMP], ticks=ticks(5.0)))
    assert reason == "left" and t == pytest.approx(1.0 + 2.0, abs=TICK + 1e-9)   # a parked lamp holds nothing
    assert lobby.results[0].players == 1 and runner.current is lobby


def test_abandon_seconds_overrides_leave(font5x7):
    paint = spy(info={"abandon_seconds": 4.0})
    runner, _, lobby = make_runner(font5x7, games=(paint,), cfg=make_cfg(SIZE, leave_seconds=2.0))
    runner.launch("spy")
    reason, t = ended(runner, lobby, scene(persons=[Person(id=1).leave(1.0)], ticks=ticks(8.0)))
    assert reason == "left" and t == pytest.approx(1.0 + 4.0, abs=TICK + 1e-9)


def test_a_moving_light_holds_the_session(font5x7):
    # spec 7.2: presence evidence is an in-zone body or a moving in-zone blob, and leave follows the evidence. A
    # light carried across the zone with nobody detected keeps the session; once it is gone, leave runs.
    runner, _, lobby = make_runner(font5x7, games=(spy(extra={"active": True}),),
                                   cfg=make_cfg(SIZE, leave_seconds=1.0))
    runner.launch("spy")
    carried = moving_blob(0.25, 0.5, 0.75, 0.5, 4.0)
    reason, t = ended(runner, lobby, scene(blobs=[carried], ticks=ticks(7.0)))
    assert reason == "left" and t == pytest.approx(4.0 + 1.0, abs=2 * TICK)


def test_the_lobby_draws_on_the_tick_a_rule_ends_the_session(font5x7):
    # Loop decision 14: the tick a rule ends the session, the lobby ticks with dt 0 and draws, so the wall never
    # shows a blank frame.
    runner, display, lobby = make_runner(font5x7, cfg=make_cfg(SIZE, leave_seconds=1.0))
    runner.launch("spy")
    reason, _ = ended(runner, lobby, scene(persons=[Person(id=1).leave(0.5)], ticks=ticks(3.0)))
    assert reason == "left" and lobby.updates == 1 and display.last[0, 1].tolist() == [0, 255, 0]


def test_inactivity_prompt_then_end(font5x7):
    runner, display, lobby = make_runner(font5x7, cfg=make_cfg(SIZE, inactive_seconds=2.0))
    runner.launch("spy")
    reason, t = ended(runner, lobby, stand(ticks=ticks(10.0)))
    assert PROMPT_SECONDS == 5.0                                       # spec 7.2
    assert reason == "inactive" and t == pytest.approx(2.0 + PROMPT_SECONDS, abs=TICK + 1e-9)
    runner, display, lobby = make_runner(font5x7, cfg=make_cfg(SIZE, inactive_seconds=2.0))
    runner.launch("spy")
    feed(runner, stand(ticks=ticks(2.5)))
    white = np.all(display.last == 255, axis=2)
    assert white.sum() > 40 and white[:, :2].sum() + white[:, -2:].sum() <= 2   # "STILL PLAYING? HAND UP", wrapped
    assert runner.current_name == "spy"


def test_inactivity_prompt_cancelled_by_a_raised_hand_or_activity(font5x7):
    runner, _, lobby = make_runner(font5x7, cfg=make_cfg(SIZE, inactive_seconds=2.0))
    runner.launch("spy")
    hand = Person(id=1).raise_hand(at=3.0, seconds=0.5)
    reason, t = ended(runner, lobby, scene(persons=[hand], ticks=ticks(12.0)))
    assert reason == "inactive" and t > 3.0 + 2.0 + PROMPT_SECONDS - TICK   # the prompt restarted after the hand
    busy = spy(extra={"active": True})
    runner, _, lobby = make_runner(font5x7, games=(busy,), cfg=make_cfg(SIZE, inactive_seconds=2.0))
    runner.launch("spy")
    assert ended(runner, lobby, stand(ticks=ticks(10.0))) is None


@pytest.mark.parametrize("active, counts", [(True, True), (np.True_, True), (False, False), (np.False_, False),
                                            (1, False), ("yes", False), (np.int64(1), False)])
def test_active_is_a_bool_and_numpy_bools_count(font5x7, active, counts):
    # Plan review B1: spec 7.1's active boolean. np.True_ is what a numpy comparison gives a game, and it counts;
    # a number or a string is not a boolean and never does.
    runner, _, lobby = make_runner(font5x7, games=(spy(extra={"active": active}),),
                                   cfg=make_cfg(SIZE, inactive_seconds=2.0))
    runner.launch("spy")
    result = ended(runner, lobby, stand(ticks=ticks(2.0 + PROMPT_SECONDS + 1.0)))
    assert (result is None) if counts else (result[0] == "inactive"), f"active={active!r}"


def test_cap_only_when_someone_waits(font5x7):
    cfg = make_cfg(SIZE, max_session_seconds=2.0)
    runner, _, lobby = make_runner(font5x7, games=(spy(extra={"phase": "over", "active": True}),), cfg=cfg)
    runner.launch("spy")
    assert ended(runner, lobby, stand(ticks=ticks(4.0))) is None      # nobody waits: no cap
    two = [Person(x=0.35, id=1), Person(x=0.65, height=0.5, id=2)]
    runner, _, lobby = make_runner(font5x7, games=(spy(extra={"phase": "play", "active": True}),), cfg=cfg)
    runner.launch("spy")
    assert ended(runner, lobby, scene(persons=two, ticks=ticks(3.0))) is None   # mid-round: never
    runner.game.extra = {"phase": "over", "active": True}
    reason, t = ended(runner, lobby, scene(persons=two, ticks=ticks(1.0)))
    assert reason == "capped" and lobby.results[0].waiting is True and lobby.results[0].players == 1
    pair = spy(info={"players": 2}, extra={"phase": "over", "active": True})
    runner, _, lobby = make_runner(font5x7, games=(pair,), cfg=cfg)
    runner.launch("spy")
    assert ended(runner, lobby, scene(persons=two, ticks=ticks(4.0))) is None   # two players: nobody waits


def test_exit_gesture_disabled_by_info(font5x7):
    arms = spy(info={"exit_gesture": False}, extra={"active": True})
    runner, display, lobby = make_runner(font5x7, games=(arms,))
    runner.launch("spy")
    assert ended(runner, lobby, scene(persons=[Person(id=1).both_hands_up(at=0.0, seconds=6.0)],
                                      ticks=ticks(6.0))) is None
    assert not np.any(np.all(display.last == RING, axis=2))          # and no ring


@pytest.mark.parametrize("body_id", range(8))
def test_exit_hold_rides_out_camera_noise(font5x7, body_id):
    # C10's runner half: the exit is Hold(exit_seconds, grace=capture_grace(camera_fps)), so the 15% keypoint
    # dropout of spec 6.4 does not break a 3 s hold, and a closing ring shows while it fills.
    runner, display, lobby = make_runner(font5x7, games=(spy(extra={"active": True}),))
    assert runner.grace == capture_grace(10) == pytest.approx(0.55)
    runner.launch("spy")
    person = Person(id=body_id).both_hands_up(at=0.5, seconds=6.0)
    rings = []
    for s in degrade(scene(persons=[person], ticks=ticks(6.0)), **REAL_NOISE):
        runner.tick(s, TICK)
        rings.append(bool(np.any(np.all(display.last == RING, axis=2))))
        if lobby.results:
            break
    assert lobby.results[0].reason == "exit", f"body_id={body_id}"
    assert 0.5 + 3.0 < runner.t < 0.5 + 4.4, f"body_id={body_id} t={runner.t}"
    assert sum(rings) > ticks(2.0)


def test_exit_then_hands_still_up_reaches_lobby_as_no_bodies(font5x7):
    runner, _, lobby = make_runner(font5x7, games=(spy(extra={"active": True}),))
    runner.launch("spy")
    person = Person(id=1).both_hands_up(at=0.0, seconds=5.0)
    reason, t = ended(runner, lobby, scene(persons=[person], ticks=ticks(4.0)))
    assert reason == "exit" and t == pytest.approx(3.0, abs=2 * TICK)
    lobby.seen.clear()
    feed(runner, (s for s in scene(persons=[person], ticks=ticks(8.0)) if s.t > t))
    blocked = [s.bodies == () and s.player is None and s.blobs == () for s in lobby.seen]
    down = ticks(5.0 - t)                                             # lobby ticks until the hands come down
    assert all(blocked[:down]) and not any(blocked[down + ticks(capture_grace(10)) + 1:])
    assert lobby.request is None and runner.current is lobby


def test_exit_hold_is_reset_on_launch(font5x7):
    # C27's caller rule: the runner updates its exit hold every tick and resets it on launch, so hands held up in
    # the lobby do not end the next game at once.
    runner, _, lobby = make_runner(font5x7, games=(spy(extra={"active": True}),))
    person = Person(id=1).both_hands_up(at=0.0, seconds=9.0)
    frames = scene(persons=[person], ticks=ticks(9.0))
    feed(runner, (next(frames) for _ in range(ticks(4.0))))           # 4 s of hands up in the lobby
    runner.launch("spy")
    reason, t = ended(runner, lobby, frames)
    assert reason == "exit" and t == pytest.approx(4.0 + 3.0, abs=2 * TICK)


def test_exit_needs_the_players_own_two_hands(font5x7):
    # C10: the exit is the player's both hands. A bystander's two hands, or the player's one, never end the game.
    bystander = [Person(x=0.35, height=0.7, id=1), Person(x=0.65, height=0.5, id=2).both_hands_up(at=0.0, seconds=6.0)]
    one_hand = [Person(id=1).raise_hand(at=0.0, seconds=6.0)]
    for persons in (bystander, one_hand):
        runner, display, lobby = make_runner(font5x7, games=(spy(extra={"active": True}),))
        runner.launch("spy")
        assert ended(runner, lobby, scene(persons=persons, ticks=ticks(6.0))) is None
        assert runner.player.id == 1 and not np.any(np.all(display.last == RING, axis=2))


@pytest.mark.parametrize("body_id", [None, 0, 1, 2, 3])
def test_exit_block_holds_until_both_hands_are_down_for_the_grace(font5x7, body_id):
    # After an exit the lobby sees nobody while any in-zone body shows a raised wrist, and for the grace after:
    # lowering one hand is not enough, nor is a keypoint dropout (body_id: REAL_NOISE seeds), so spec 7.3's "a
    # raised hand starts play at once" cannot relaunch the game.
    runner, _, lobby = make_runner(font5x7, games=(spy(extra={"active": True}),))
    runner.launch("spy")
    person = Person(id=body_id or 1).both_hands_up(at=0.0, seconds=5.0).raise_hand(at=5.0, seconds=2.0)
    frames = scene(persons=[person], ticks=ticks(10.0))
    if body_id is not None:
        frames = degrade(frames, **REAL_NOISE)
    reason, t = ended(runner, lobby, frames)
    assert reason == "exit" and t < 5.0
    lobby.seen.clear()
    feed(runner, frames)
    blocked = [s.bodies == () and s.player is None for s in lobby.seen]
    down, grace = ticks(7.0 - t), ticks(capture_grace(10))            # the last hand comes down at 7 s
    assert all(blocked[:down + grace - 1]), f"body_id={body_id}"
    assert not any(blocked[down + grace + ticks(0.2):]), f"body_id={body_id}"
    assert runner.current is lobby and lobby.request is None


def test_session_logged_with_reason(font5x7, tmp_path):
    sessions = SessionLog(tmp_path / "sessions.jsonl")
    pair = spy(info={"players": 2}, extra={"score": np.float32(12.5), "active": True})
    runner, _, lobby = make_runner(font5x7, games=(pair,), sessions=sessions,
                                   cfg=make_cfg(SIZE, leave_seconds=1.0))
    runner.launch("spy")
    two = [Person(x=0.35, id=1).leave(2.0), Person(x=0.65, height=0.5, id=2).leave(2.0)]
    feed(runner, scene(persons=two, ticks=ticks(4.0)))
    (line,) = [json.loads(x) for x in (tmp_path / "sessions.jsonl").read_text().splitlines()]
    assert line == {"game": "spy", "layout": "64x64", "start": "2026-11-11T21:00:00",
                    "duration": pytest.approx(3.0, abs=2 * TICK), "players": 2, "score": 12.5, "reason": "left"}


def test_push_path_order(font5x7):
    # Q11: limiter, then governor, then push. A frame the limiter changes reaches the governor, and what the
    # governor returns is what is pushed.
    class White(SpyGame):
        def draw(self, canvas):
            canvas.clear(WHITE)

    calls = []
    runner, display, _ = make_runner(font5x7, games=(White,), local_clock=lambda: datetime(2026, 11, 12, 2, 0))
    limiter, governor = runner.limiter.apply, runner.governor.apply

    def limit(frame):
        calls.append(("limiter", frame is runner.canvas.frame, int(frame.max())))
        out = limiter(frame)
        calls.append(("limited", out))
        return out

    def govern(frame):
        calls.append(("governor", frame is calls[-1][1]))
        out = governor(frame)
        calls.append(("governed", out))
        return out

    runner.limiter.apply, runner.governor.apply = limit, govern
    runner.launch("spy")
    feed(runner, stand(ticks=1))
    assert [c[0] for c in calls] == ["limiter", "limited", "governor", "governed"]
    assert calls[0][1:] == (True, 255) and calls[2][1] is True
    assert np.array_equal(display.last, calls[3][1]) and display.last.max() == 128   # 02:00 is night: scaled
    runner, display, _ = make_runner(font5x7, games=(White,))
    runner.launch("spy")
    feed(runner, stand(ticks=1))
    assert display.last.max() == 128 and runner.limiter.is_night() is False          # 21:00: the day cap
    assert runner.limiter.cap() == runner.cfg.apl_cap_day


class Camera:
    """latest() gives what result says; available as set."""

    def __init__(self, result=None, available=True):
        self.result, self.available = result, available

    def latest(self):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_stale_camera_is_unavailable(font5x7):
    clock = FakeClock()
    runner, _, lobby = make_runner(font5x7, clock=clock)
    body = next(stand(ticks=1)).bodies[0]
    audio = Camera((clock.now, Audio()))
    s = runner.sense(Camera((clock.now - 1.5, (body,), (), None)), audio)
    assert s.bodies == () and not s.camera_fresh and lobby.status[0] is False
    camera = Camera((clock.now - 0.2, (body,), (), None))
    s = runner.sense(camera, audio)
    assert s.bodies == (body,) and s.camera_fresh and s.camera_seq == 1 and lobby.status[0] is True
    assert s.camera_t == pytest.approx(runner.t - 0.2)
    s = runner.sense(camera, audio)
    assert not s.camera_fresh and s.camera_seq == 1                   # the same capture again
    clock.now += 0.9
    s = runner.sense(camera, audio)
    assert s.bodies == () and lobby.status[:3] == (False, False, set())   # both stale now
    assert runner.sense(Camera(None), Camera((clock.now, Audio()))).bodies == ()


def test_sense_survives_raising_source_and_reports_status(font5x7, caplog):
    clock = FakeClock()
    runner, _, lobby = make_runner(font5x7, clock=clock, calibration=Calibration(calibrated=True))
    with caplog.at_level(logging.ERROR, logger="arcade"):
        for _ in range(5):
            s = runner.sense(Camera(OSError("camera gone")), Camera(OSError("mic gone")))
    assert s.bodies == () and s.motion.shape == (64, 64) and lobby.status == (False, False, set(), True)
    assert len(caplog.records) == 2                                   # each failing source logged once
    s = runner.sense(Camera((clock.now, (), (), None)), Camera((clock.now - 0.1, Audio(level=0.5)), available=False))
    assert lobby.status == (True, False, {"pose", "blobs", "motion"}, True) and s.audio.level == 0.5


def test_sense_builds_keyword_sensed(font5x7):
    # C21: Sensed and Audio take keywords after t, so sense() can never bind the bodies to camera_t.
    clock = FakeClock()
    runner, _, lobby = make_runner(font5x7, clock=clock)
    feed(runner, scene(ticks=3))
    body = next(stand(ticks=1)).bodies[0]
    grid = np.zeros((64, 128), bool)
    grid[:32, :64] = True
    s = runner.sense(Camera((clock.now, (body,), (), grid)), Camera((clock.now, Audio(voice=0.4))))
    assert s.t == runner.t and s.bodies == (body,) and s.audio.voice == 0.4 and s.motion.shape == (64, 64)
    assert s.motion[:32, :32].all() and not s.motion[32:].any()
    assert lobby.status == (True, True, {"pose", "blobs", "motion", "audio"}, False)


def test_games_see_the_runners_clock(font5x7):
    # Sensed.t is the runner's t for the tick, and camera_t moves with it, so a game sees one clock live and
    # headless, wherever a scenario starts.
    runner, _, _ = make_runner(font5x7)
    runner.launch("spy")
    feed(runner, [Sensed(50.0 + i * TICK, camera_t=49.9 + i * TICK, camera_fresh=True) for i in range(3)])
    s = runner.game.seen[-1]
    assert s.t == runner.t == pytest.approx(3 * TICK) and s.camera_t == pytest.approx(runner.t - 0.1)
    clock = FakeClock()
    runner, _, lobby = make_runner(font5x7, clock=clock)
    feed(runner, scene(ticks=3))
    s = runner.sense(Camera((clock.now - 0.05, (), (), None)), Camera((clock.now, Audio())))
    runner.tick(s, TICK)
    assert lobby.seen[-1].t == runner.t and lobby.seen[-1].camera_t == pytest.approx(runner.t - 0.05)


def test_sense_treats_a_malformed_result_as_a_failed_source(font5x7, caplog):
    # A latest() of another shape goes the way of one that raises: the source is unavailable, logged once per run
    # of failures, and neither sense() nor the loop raises.
    clock = FakeClock()
    runner, _, lobby = make_runner(font5x7, clock=clock, sleep=clock.sleep)
    body = next(stand(ticks=1)).bodies[0]
    cameras = [(clock.now, (body,), ()), (clock.now,), 5, (clock.now, ("body",), (), None),
               (clock.now, (), ("blob",), None), (clock.now, (), (), "grid"), (clock.now, (), (), np.zeros(4, bool)),
               ("now", (), (), None)]
    cameras += [(t, (body,), (), None) for t in (math.inf, math.nan, clock.now + 3600)]   # not the runner's clock
    audios = [(clock.now, 0.5), (clock.now,), "loud", ("now", Audio())]
    audios += [(t, Audio(level=0.5)) for t in (math.inf, math.nan, clock.now + 3600)]
    with caplog.at_level(logging.ERROR, logger="arcade"):
        for got in cameras:
            s = runner.sense(Camera(got), Camera((clock.now, Audio())))
            assert s.bodies == () and lobby.status[:2] == (False, True), f"{got!r}"
        for got in audios:
            s = runner.sense(Camera((clock.now, (body,), (), None)), Camera(got))
            assert s.bodies == (body,) and lobby.status[:2] == (True, False), f"{got!r}"
        runner.loop(Camera(5), Camera("loud"), max_ticks=3)
    messages = [r.getMessage() for r in caplog.records]
    assert messages.count("camera source failed") == 2 and messages.count("audio source failed") == 1


def test_launch_refuses_an_unhashable_name_and_ends_a_crash_icon(font5x7, caplog):
    runner, _, lobby = make_runner(font5x7, games=(spy(raise_in=frozenset({"update"})), spy("paint")))
    lobby.request = ["spy"]                                           # a lobby bug: a list, not a name
    with caplog.at_level(logging.WARNING, logger="arcade"):
        feed(runner, stand(ticks=1))
    assert runner.current is lobby and "not launching ['spy']: unknown" in caplog.text
    runner.launch("spy")
    feed(runner, stand(ticks=1))
    assert runner.state()["glitch"] is True
    assert runner.launch("paint")
    feed(runner, stand(ticks=1))
    assert runner.current_name == "paint" and runner.game.updates == 1 and runner.state()["glitch"] is False
    feed(runner, stand(ticks=ticks(CRASH_SECONDS) + 1))
    assert runner.current_name == "paint"                             # the old icon never sends it to the lobby


class Live:
    """A camera whose latest() stamps each capture on clock, plus ahead seconds."""

    def __init__(self, clock, bodies, ahead=0.0):
        self.clock, self.bodies, self.ahead = clock, bodies, ahead

    def latest(self):
        return self.clock.now + self.ahead, self.bodies, (), None


def test_a_body_stamped_ahead_of_the_runners_clock_holds_nothing(font5x7, caplog):
    # R2-N2: a source on another clock or unit (picamera2 stamps nanoseconds since boot) repeats its last capture
    # with a time far ahead. It is malformed, so the frozen body holds neither presence nor the session. A stamp
    # within CLOCK_SLACK is a capture that landed as sense() read the clock, and counts.
    assert CLOCK_SLACK == 0.1
    clock = FakeClock()
    runner, _, lobby = make_runner(font5x7, clock=clock, sleep=clock.sleep, cfg=make_cfg(SIZE, leave_seconds=2.0))
    body = next(stand(ticks=1)).bodies[0]
    runner.loop(Live(clock, (body,), ahead=CLOCK_SLACK / 2), Camera(None), max_ticks=ticks(2.0))
    assert runner.presence.present and lobby.status[0] is True
    assert runner.sense(Live(clock, (body,), ahead=2 * CLOCK_SLACK), Camera(None)).bodies == ()
    runner.sense(Live(clock, (body,)), Camera(None))
    caplog.clear()
    with caplog.at_level(logging.ERROR, logger="arcade"):
        assert runner.sense(Camera((-math.inf, (body,), (), None)), Camera(None)).bodies == ()
    assert "camera source failed" in caplog.text                      # malformed, not merely stale
    assert runner.launch("spy")
    runner.loop(Camera((clock.now + 3600, (body,), (), None)), Camera(None), max_ticks=ticks(6.0))
    assert [r.reason for r in lobby.results] == ["left"] and runner.current is lobby
    assert not runner.presence.present and lobby.status[0] is False


def test_launch_is_refused_while_a_game_runs(font5x7, caplog):
    # R2-N3: a launch comes from the lobby or during the crash icon. Mid-session it would drop the session with no
    # log line and no end card, so it is refused.
    runner, _, lobby = make_runner(font5x7, games=(SpyGame, spy("paint")))
    assert runner.launch("spy")
    feed(runner, stand(ticks=ticks(1.0)))
    first = runner.game
    with caplog.at_level(logging.WARNING, logger="arcade"):
        assert runner.launch("paint") is False
    assert "not launching 'paint': spy is running" in caplog.text
    feed(runner, stand(ticks=1))
    assert runner.current is first and first.updates == ticks(1.0) + 1 and lobby.results == []
    runner.end_session("exit")
    assert [r.game for r in lobby.results] == ["spy"] and runner.launch("paint")


class StuckLobby(StubLobby):
    """A lobby whose request is a read-only property: the runner can read it, never clear it."""

    request = property(lambda self: "spy")

    def __init__(self):
        vars(self).update(raise_in=frozenset(), available=None, status=None, results=[], resets=0, updates=0,
                          seen=[])


def test_a_request_that_cannot_be_cleared_is_a_lobby_that_raised(font5x7, caplog):
    # R2-N4: the runner reads and clears the request inside the lobby guard, so tick() never raises for it and the
    # game is not launched again on every lobby tick.
    runner, _, lobby = make_runner(font5x7, lobby=StuckLobby())
    with caplog.at_level(logging.ERROR, logger="arcade"):
        feed(runner, stand(ticks=3))
    assert runner.state()["title_card"] is True and runner.current_name == "lobby" and runner.game is None
    assert "AttributeError" in runner.last_error and "title card" in caplog.text


def test_push_failure_is_logged_once_a_minute(font5x7, caplog):
    class BadDisplay(RecordingDisplay):
        def push(self, frame):
            raise OSError("socket")

    runner, _, _ = make_runner(font5x7, display=BadDisplay())
    with caplog.at_level(logging.ERROR, logger="arcade"):
        feed(runner, scene(ticks=90))
        assert len(caplog.records) == 1
        feed(runner, scene(ticks=ticks(60.0)))
    assert len(caplog.records) == 2 and "display push failed" in caplog.records[0].getMessage()


def test_governor_interventions_logged_once_a_minute_with_the_game(font5x7, caplog):
    runner, display, _ = make_runner(font5x7, games=(Strobe,))
    runner.launch("strobe")
    with caplog.at_level(logging.INFO, logger="arcade"):
        feed(runner, stand(ticks=90))
    held = [r for r in caplog.records if "flash governor" in r.getMessage()]
    assert len(held) == 1 and "strobe" in held[0].getMessage()
    assert runner.state()["flash_held_ticks"] == runner.governor.held_ticks > 0


def test_loop_runs_max_ticks_with_fake_clock(font5x7):
    clock = FakeClock()
    runner, display, _ = make_runner(font5x7, clock=clock, sleep=clock.sleep)
    runner.loop(Camera((clock.now, (), (), None)), Camera((clock.now, Audio())), max_ticks=10)
    assert display.count == 10 and clock.now == pytest.approx(100.0 + 10 / runner.cfg.fps, abs=0.05)


def test_dt_is_clamped(font5x7):
    runner, _, _ = make_runner(font5x7)
    runner.launch("spy")
    runner.tick(Sensed(0.0), dt=5.0)
    assert runner.t == pytest.approx(MAX_DT) and MAX_DT == 0.1           # spec 7.2: 100 ms
    for bad in (math.nan, -1.0, math.inf, None):
        runner.tick(Sensed(0.0), dt=bad)
    assert runner.t == pytest.approx(MAX_DT)


def test_games_get_only_in_zone_blobs(font5x7):
    cal = Calibration()
    inside, outside = place_blob(Blob(0.5, 0.5, 0.02, WHITE), cal), place_blob(Blob(0.05, 0.5, 0.02, WHITE), cal)
    runner, _, lobby = make_runner(font5x7)
    feed(runner, [Sensed(0.0, blobs=(inside, outside))])
    assert lobby.seen[-1].blobs == (inside, outside)                  # the lobby sees them all
    runner.launch("spy")
    feed(runner, [Sensed(TICK, blobs=(inside, outside))])
    assert runner.game.seen[-1].blobs == (inside,)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_runner.py`

Expected: `1 error` at collection, with `ModuleNotFoundError: No module named 'arcade.headless'`.

- [ ] **Step 3: Implement**

`arcade/headless.py` (this task's version):

```python
"""Headless pieces shared by the tests and the agent tools: a recording display and the fixed local time of
headless runs."""
from __future__ import annotations

from datetime import datetime

import numpy as np


OPENING_NIGHT = datetime(2026, 11, 11, 21, 0)    # headless local time: evidence never depends on the time of day


class RecordingDisplay:
    """A display that keeps copies of what it was pushed: every frame (keep_all) or only the last."""

    def __init__(self, keep_all: bool = True):
        self.keep_all = keep_all
        self.frames: list[np.ndarray] = []
        self.last: np.ndarray | None = None
        self.count = 0
        self.brightness = 1.0
        self.closed = False

    def push(self, frame: np.ndarray) -> None:
        copy = frame.copy()
        if self.keep_all:
            self.frames.append(copy)
        self.last = copy
        self.count += 1

    def set_brightness(self, level: float) -> None:
        self.brightness = level

    def close(self) -> None:
        self.closed = True

```

`arcade/runner.py`:

```python
"""The runner (spec 7.2): a fixed tick from sources to Sensed to the lobby or a game to the wall.

It owns what every game gets for free: the player lock, presence, the session rules (leave, inactivity, the cap
and the deliberate exit), the crash guard, the effects, and the two hard ceilings on every frame. One tick:

    read sources -> Sensed -> player, player2, present -> session rules -> update (skipped while fx.frozen)
    -> draw -> Juice.render -> overlays -> BrightnessLimiter.apply -> FlashGovernor.apply -> push

The governor runs last (owner Q11), so what it bounds is what the wall shows.
"""
from __future__ import annotations

import dataclasses
import logging
import math
import random
import time
import traceback
import zlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Protocol

import numpy as np

from arcade.brightness import BrightnessLimiter
from arcade.calibration import Calibration
from arcade.canvas import Canvas
from arcade.config import ArcadeConfig
from arcade.flash import FlashGovernor
from arcade.game import Game
from arcade.input import EPSILON, Hold, capture_grace
from arcade.juice import Juice
from arcade.look import is_real
from arcade.scores import Scores, SessionLog
from arcade.sensed import Audio, Blob, Body, Sensed
from show.display import Display
from show.font import CELL_H, Font

MAX_DT = 0.1                 # seconds: a tick's dt is clamped to this (spec 7.2)
CAMERA_STALE = 1.0           # seconds: an older camera result is empty and the camera unavailable (spec 10)
AUDIO_STALE = 0.5            # seconds: the same for audio
CLOCK_SLACK = 0.1            # seconds: a capture stamped further past the runner's clock is on another clock
MAX_CRASHES = 3              # a game that raises this many times is hidden until the dusk restart
CRASH_SECONDS = 0.5          # the crash icon fades over this, then the lobby
CRASH_RED = (96, 0, 0)       # the crash icon's colour: static and dim
PROMPT_SECONDS = 5.0         # "STILL PLAYING? HAND UP" shows this long before the session ends
PROMPT = "STILL PLAYING? HAND UP"
SWITCH_RATIO = 1.3           # a rival this much larger than the player ...
SWITCH_SECONDS = 1.0         # ... for this long takes the lock
REACQUIRE_DISTANCE = 0.25    # zone units: a new body this near the lost player's last place keeps the slot
BLOB_SPEED = 0.05            # frame widths a second: a slower in-zone light is a lamp, not a person (spec 7.2)
LOG_EVERY = 60.0             # seconds between two log lines about one failing thing
CAMERA_INPUTS = frozenset({"pose", "blobs", "motion"})
AUDIO_INPUTS = frozenset({"audio"})
LOBBY = "lobby"
RING = (160, 160, 160)       # the exit ring


@dataclass(frozen=True)
class SessionResult:
    """What the lobby's end card shows (spec 7.3): the session just ended and why."""

    game: str
    layout: str
    reason: str                  # one of scores.REASONS
    score: float | None
    duration: float
    players: int
    best: float | None           # tonight's best after this session
    waiting: bool                # someone beyond the game's players stands in the zone


class LobbyLike(Game, Protocol):
    """The lobby (the attract director, core Task 9): a Game plus a request the runner launches and three
    notices from the runner. The runner reads request after the lobby's tick and sets it to None; a request that
    cannot be read or set is a lobby that raised."""

    request: str | None

    def set_available(self, names: set[str]) -> None: ...
    def set_status(self, camera_ok: bool, mic_ok: bool, inputs: set[str], calibrated: bool) -> None: ...
    def end_session(self, result: SessionResult) -> None: ...


class PlayerLock:
    """spec 7.2's player lock. update(bodies, t) returns (player, player2).

    player is the in-zone body with the largest scale. Once locked it stays until its body has been absent for
    more than lost_seconds, or another in-zone body has been SWITCH_RATIO times larger for SWITCH_SECONDS.
    While the locked body is absent, player is None and the slot is kept; a body with an id that was not there
    when it went missing, in the zone within REACQUIRE_DISTANCE of its last place, takes the slot (the tracker
    never reuses an id, so a re-detected player is a new id). player2 is the next in-zone body by scale.
    """

    def __init__(self, lost_seconds: float):
        self.lost_seconds = lost_seconds
        self.id: int | None = None
        self._seen = -math.inf
        self._place = (0.5, 0.5)
        self._known: set[int] = set()                 # ids present when the player went missing
        self._rival: int | None = None
        self._rival_since = -math.inf

    def reset(self) -> None:
        self.__init__(self.lost_seconds)

    def update(self, bodies: tuple[Body, ...], t: float) -> tuple[Body | None, Body | None]:
        inside = sorted((b for b in bodies if b.in_zone), key=lambda b: -b.scale)
        by_id = {b.id: b for b in inside}
        if self.id is not None and self.id not in by_id:
            if t - self._seen > self.lost_seconds + EPSILON:
                self.id = None
            else:
                new = [b for b in inside if b.id not in self._known and
                       math.hypot(b.zone_x - self._place[0], b.zone_y - self._place[1]) <= REACQUIRE_DISTANCE]
                if new:
                    self.id = min(new, key=lambda b: math.hypot(b.zone_x - self._place[0],
                                                                b.zone_y - self._place[1])).id
        if self.id is None and inside:
            self.id, self._rival = inside[0].id, None
        player = by_id.get(self.id)
        if player is not None:
            rival = next((b for b in inside if b.id != player.id and b.scale > SWITCH_RATIO * player.scale), None)
            if rival is None:
                self._rival = None
            elif rival.id != self._rival:
                self._rival, self._rival_since = rival.id, t
            elif t - self._rival_since >= SWITCH_SECONDS - EPSILON:
                self.id, player, self._rival = rival.id, rival, None
            self._seen, self._place = t, (player.zone_x, player.zone_y)
            self._known = {b.id for b in bodies}
        player2 = next((b for b in inside if b.id != self.id), None)
        return player, player2


class Presence:
    """spec 7.2's presence. update(evidence, t) returns present: true once evidence (an in-zone body or a moving
    in-zone blob) has lasted on_seconds, riding out dropouts of up to grace; false after off_seconds without any.
    last_seen is the time of the last evidence."""

    def __init__(self, on_seconds: float, off_seconds: float, grace: float):
        self.off_seconds = off_seconds
        self._on = Hold(on_seconds, grace=grace)
        self.present = False
        self.last_seen = -math.inf

    def update(self, evidence: bool, t: float) -> bool:
        if evidence:
            self.last_seen = t
        if self._on.update(evidence, t):
            self.present = True
        if self.present and t - self.last_seen >= self.off_seconds - EPSILON:
            self.present = False
            self._on.reset()
        return self.present


class _TitleCard:
    """The lobby after the real one raised: a built-in title card until the restart (spec 7.2)."""

    info = None
    request: str | None = None

    def reset(self, size, rng, fx=None) -> None:
        pass

    def update(self, sensed: Sensed, dt: float) -> None:
        pass

    def draw(self, canvas: Canvas) -> None:
        text = "ARCADE"
        canvas.text((canvas.width - canvas.text_width(text)) // 2, (canvas.height - CELL_H) // 2, text,
                    (120, 60, 0))

    def done(self) -> bool:
        return False

    def debug_state(self) -> dict:
        return {"title_card": True}

    def set_available(self, names) -> None:
        pass

    def set_status(self, camera_ok, mic_ok, inputs, calibrated) -> None:
        pass

    def end_session(self, result) -> None:
        pass


def moving_blob(before: tuple[Blob, ...], now: tuple[Blob, ...], seconds: float) -> bool:
    """True when a blob in now is in the zone and at least BLOB_SPEED from every blob in before, seconds earlier:
    spec 7.2's "moving in-zone blob". A light that appears counts on its first capture; a parked one never."""
    seconds = max(seconds, EPSILON)
    return any(b.in_zone and all(math.hypot(b.x - p.x, b.y - p.y) / seconds >= BLOB_SPEED for p in before)
               for b in now)


def _is_true(v) -> bool:
    """spec 7.1's active boolean: True or a numpy True. 1, "yes" and numpy ints are not booleans (plan review B1)."""
    return v is True or (isinstance(v, np.bool_) and bool(v))


def _stamped(capture_t, now: float) -> bool:
    """Whether capture_t is a time on the runner's clock: finite, and at most CLOCK_SLACK past now.

    Sources stamp captures on the runner's monotonic clock, in seconds. On it a capture is never later than the
    moment latest() returns, a few microseconds after sense() reads now; 0.1 s leaves room for a slow thread and is
    3 camera frames at most. A capture stamped on another clock or in another unit (nanoseconds since boot, the
    wall clock's epoch) is off by hours or more, and would otherwise count as fresh for as long as it is repeated,
    holding a frozen body and a session (plan review R2-N2)."""
    return is_real(capture_t) and math.isfinite(capture_t) and capture_t <= now + CLOCK_SLACK


def _camera_result(got, now: float) -> tuple[float, tuple[Body, ...], tuple[Blob, ...], np.ndarray | None] | None:
    """A camera latest() result checked: None, or (capture_t, bodies, blobs, motion) with capture_t _stamped,
    Body and Blob items and motion None or a 2-D grid. Anything else raises, and sense() treats the source as
    failed."""
    if got is None:
        return None
    capture_t, bodies, blobs, motion = got
    bodies, blobs = tuple(bodies), tuple(blobs)
    if not (_stamped(capture_t, now) and all(isinstance(b, Body) for b in bodies)
            and all(isinstance(b, Blob) for b in blobs)
            and (motion is None or (isinstance(motion, np.ndarray) and motion.ndim == 2))):
        raise TypeError(f"camera latest() gave a malformed result: {got!r:.200}")
    return float(capture_t), bodies, blobs, motion


def _audio_result(got, now: float) -> tuple[float, Audio] | None:
    """An audio latest() result checked: None, or (capture_t, Audio) with capture_t _stamped. Anything else
    raises."""
    if got is None:
        return None
    capture_t, sound = got
    if not (_stamped(capture_t, now) and isinstance(sound, Audio)):
        raise TypeError(f"audio latest() gave a malformed result: {got!r:.200}")
    return float(capture_t), sound


def _take_request(lobby) -> str | None:
    """Read the lobby's request and clear it, so it launches once; the runner calls this inside _lobby_call, so
    a request that cannot be read or cleared is a lobby that raised (plan review R2-N4)."""
    request = getattr(lobby, "request", None)
    if request is not None:
        lobby.request = None
    return request


def _wrap(text: str, width: int, canvas: Canvas) -> list[str]:
    """text in lines that fit width at 1x, split between words."""
    lines: list[str] = []
    for word in text.split():
        if lines and canvas.text_width(lines[-1] + " " + word) <= width:
            lines[-1] += " " + word
        else:
            lines.append(word)
    return lines


class Runner:
    """spec 7.2. tick(sensed, dt) runs one tick; loop(camera, audio) ticks at cfg.fps from the injected clock.

    games are the game classes the lobby may launch, keyed by info.name once here (the runner never calls
    all_games). scores and sessions default to in-memory ones; main passes the files in data_dir. local_clock
    is local time for the brightness limiter's night, never the monotonic clock; lux is the IMX500's lux
    callable or None. strict re-raises a game's exception instead of guarding it (the test harness default).
    runner.game is the last launched instance, kept after its session ends. raw_frames, when a list, gets a
    copy of every frame before the limiter; trace, when a list, gets state() after every tick. The Sensed that
    the lobby and games see has t set to the runner's t for the tick and camera_t moved by the same amount, so a
    game sees one clock live and headless, wherever a scenario starts. clock is the monotonic clock the sources
    stamp their captures on, in seconds.
    """

    def __init__(self, cfg: ArcadeConfig, display: Display, font: Font, lobby: LobbyLike, games: list[type],
                 seed: int = 0, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep, log: logging.Logger | None = None,
                 scores: Scores | None = None, sessions: SessionLog | None = None,
                 calibration: Calibration | None = None, strict: bool = False,
                 local_clock: Callable[[], datetime] = datetime.now, lux: Callable[[], Any] | None = None):
        self.cfg, self.display, self.lobby, self.seed = cfg, display, lobby, seed
        self.games: dict[str, type] = {g.info.name: g for g in games}
        self.clock, self.sleep, self.local_clock, self.strict = clock, sleep, local_clock, strict
        self.log = log or logging.getLogger("arcade")
        self.scores = scores if scores is not None else Scores(None, local_clock)
        self.sessions = sessions if sessions is not None else SessionLog(None)
        self.calibration = calibration or Calibration()
        self.canvas = Canvas(cfg.width, cfg.height, font)
        self.limiter = BrightnessLimiter(cfg, clock=local_clock, lux=lux)
        self.governor = FlashGovernor(cfg.height, cfg.width, cfg.gamma, fps=cfg.fps)
        self.grace = capture_grace(cfg.camera_fps)
        self.lock = PlayerLock(cfg.player_lost_seconds)
        self.presence = Presence(cfg.present_on_seconds, cfg.present_off_seconds, self.grace)
        self.t = 0.0
        self.running = True
        self.crashes: dict[str, int] = {}
        self.hidden: set[str] = set()
        self.last_error: str | None = None
        self.game: Game | None = None
        self.current: Any = lobby
        self.current_name = LOBBY
        self.fx: Juice | None = None
        self.raw_frames: list[np.ndarray] | None = None
        self.trace: list[dict] | None = None
        self.player: Body | None = None
        self.player2: Body | None = None
        self._state: dict = {}
        self._bodies: tuple[Body, ...] = ()
        self._blobs_before: tuple[float, tuple[Blob, ...]] | None = None  # (camera_t, blobs) of the last capture
        self._blob_moving = False
        self._evidence = False
        self._launches = 0
        self._exit = Hold(cfg.exit_seconds, grace=self.grace)
        self._blocked = False                         # after an exit, until the hands are down
        self._hands_seen = -math.inf
        self._crash: tuple[np.ndarray, float] | None = None  # (icon, since) while the crash icon shows
        self._session: dict = {}
        self._push_logged = self._governor_logged = -math.inf
        self._held_before = 0
        self._camera_seq, self._camera_capture = 0, None
        self._source_failed: dict[str, bool] = {}
        self.display.set_brightness(cfg.brightness)
        self._lobby_call(lambda: self.lobby.reset(cfg.size, random.Random(zlib.crc32(f"{seed}:lobby".encode()))))
        self._lobby_call(lambda: self.lobby.set_available(self.available()))

    # ----- the lobby and games -----

    def available(self) -> set[str]:
        """The games the lobby may offer: every game not hidden."""
        return set(self.games) - self.hidden

    def launch(self, name: str) -> bool:
        """Start a fresh instance of the game called name; False if it is unknown, hidden or crashed at start, or if
        a game is running: a launch comes from the lobby or during the crash icon, which it ends, so no session is
        dropped unlogged (plan review R2-N3)."""
        if self.current_name != LOBBY and self._crash is None:
            self.log.warning("not launching %r: %s is running", name, self.current_name)
            return False
        if not isinstance(name, str) or name not in self.games or name in self.hidden:
            hidden = isinstance(name, str) and name in self.hidden
            self.log.warning("not launching %r: %s", name, "hidden" if hidden else "unknown")
            return False
        self._launches += 1
        rng = random.Random(zlib.crc32(f"{self.seed}:{name}:{self._launches}".encode()))
        fx = Juice(random.Random(zlib.crc32(f"{self.seed}:{name}:{self._launches}:fx".encode())), self.cfg.size)
        self.current_name, self.fx, self._state, self._crash = name, fx, {}, None
        self._session = {"start": self.t, "local": self.local_clock(), "seen": self.t, "active": self.t,
                         "prompt": None, "players": 0}
        try:
            game = self.games[name]()
            self.game = game
            game.scores = self.scores.for_game(name, self.cfg.layout)
            game.reset(self.cfg.size, rng, fx)
        except Exception:
            self._crashed()
            return False
        self.current, self._state = game, {}
        self._exit.reset()                            # the caller rule (C27): a stale hold never fires at once
        return True

    def end_session(self, reason: str) -> SessionResult:
        """Log the session, tell the lobby, and return to it."""
        name, info = self.current_name, self.games[self.current_name].info
        s, state = self._session, self._state
        bodies = sum(b.in_zone for b in self._bodies)
        result = SessionResult(game=name, layout=self.cfg.layout, reason=reason, score=state.get("score"),
                               duration=self.t - s["start"], players=s["players"],
                               best=self.scores.best(name, self.cfg.layout), waiting=bodies > info.players)
        self.sessions.append(name, self.cfg.layout, s["local"], result.duration, result.players, result.score,
                             reason)
        self._lobby_call(lambda: self.lobby.end_session(result))
        self._to_lobby()
        if reason == "exit":
            self._blocked, self._hands_seen = True, self.t
        return result

    def _to_lobby(self) -> None:
        self.current, self.current_name, self.fx, self._crash = self.lobby, LOBBY, None, None
        self._state = {}

    def _crashed(self) -> None:
        """The crash guard (spec 7.2): log and keep the traceback, count, hide at MAX_CRASHES, show the icon."""
        if self.strict:
            raise
        name = self.current_name
        self.last_error = traceback.format_exc()
        self.log.exception("game %s crashed", name)
        self.crashes[name] = self.crashes.get(name, 0) + 1
        if self.crashes[name] >= MAX_CRASHES and name not in self.hidden:
            self.hidden.add(name)
            self._lobby_call(lambda: self.lobby.set_available(self.available()))
        result_icon = self.games[name].info.icon
        self.end_session("crash")
        self.current_name, self._crash = name, (result_icon, self.t)

    def _lobby_call(self, fn: Callable[[], Any]) -> Any:
        """Call into the lobby; if it raises, a built-in title card replaces it until restart."""
        try:
            return fn()
        except Exception:
            if self.strict:
                raise
            self.last_error = traceback.format_exc()
            self.log.exception("the lobby raised: showing the title card until restart")
            if self.current is self.lobby:
                self.current = _TitleCard()
            self.lobby = _TitleCard()
            return None

    # ----- one tick -----

    def tick(self, sensed: Sensed, dt: float) -> None:
        dt = min(MAX_DT, max(0.0, float(dt))) if is_real(dt) and math.isfinite(dt) else 0.0
        self.t += dt
        sensed = sensed.with_motion(self.cfg.size)
        self._bodies = sensed.bodies
        self.player, self.player2 = self.lock.update(sensed.bodies, self.t)
        self._evidence = any(b.in_zone for b in sensed.bodies) or self._moving(sensed)
        present = self.presence.update(self._evidence, self.t)
        sensed = dataclasses.replace(sensed, t=self.t, camera_t=sensed.camera_t + (self.t - sensed.t),
                                     player=self.player, player2=self.player2, present=present)
        hands_up = self.player is not None and self.player.both_hands_up
        exit_fired = self._exit.update(hands_up, self.t)             # every tick (C27), in the lobby too
        self.canvas.clear()
        if self._crash is not None and self._draw_crash():
            pass
        elif self.current_name == LOBBY:                              # also the tick the crash icon ends
            self._lobby_tick(sensed, dt)
        else:
            self._game_tick(sensed, dt, exit_fired)
        self._push()
        if self.trace is not None:
            self.trace.append(self.state())

    def _moving(self, sensed: Sensed) -> bool:
        """Whether a moving in-zone blob was in the last camera capture, judged on the tick it arrives (camera_fresh)
        against the capture before; seconds apart from camera_t, or one camera frame when that does not advance."""
        if sensed.camera_fresh:
            if self._blobs_before is None:
                self._blob_moving = any(b.in_zone for b in sensed.blobs)
            else:
                t0, before = self._blobs_before
                seconds = sensed.camera_t - t0 if sensed.camera_t > t0 else 1.0 / self.cfg.camera_fps
                self._blob_moving = moving_blob(before, sensed.blobs, seconds)
            self._blobs_before = (sensed.camera_t, sensed.blobs)
        return self._blob_moving

    def _lobby_tick(self, sensed: Sensed, dt: float) -> None:
        if self._blocked:
            if any(b.in_zone and b.raised_wrist is not None for b in sensed.bodies):
                self._hands_seen = self.t
            if self.t - self._hands_seen > self.grace + EPSILON:
                self._blocked = False
            else:
                sensed = dataclasses.replace(sensed, bodies=(), blobs=(), player=None, player2=None)
        lobby = self.current
        self._lobby_call(lambda: lobby.update(sensed, dt))
        self._lobby_call(lambda: self.current.draw(self.canvas))
        self._state = self._lobby_call(lambda: dict(self.current.debug_state())) or {}
        request = self._lobby_call(lambda: _take_request(self.current))
        if request is not None:
            self.launch(request)

    def _game_tick(self, sensed: Sensed, dt: float, exit_fired: bool) -> None:
        game, info, fx, s = self.current, self.games[self.current_name].info, self.fx, self._session
        inside = [b for b in sensed.bodies if b.in_zone]
        s["players"] = max(s["players"], min(len(inside), info.players))
        if self._evidence:                                          # the presence evidence: leave follows it
            s["seen"] = self.t
        if _is_true(self._state.get("active")):
            s["active"] = self.t
        reason = self._session_rule(sensed, info, exit_fired, len(inside))
        if reason is not None:
            self.end_session(reason)
            self._lobby_tick(sensed, 0.0)
            return
        game_sensed = dataclasses.replace(sensed, blobs=tuple(b for b in sensed.blobs if b.in_zone))
        try:
            if not fx.frozen:
                game.update(game_sensed, dt)
            game.draw(self.canvas)
            fx.render(self.canvas, self.player, self.player2)
            self._draw_overlays(info)
            fx.update(dt)
            self._state = dict(game.debug_state())
            if game.done():
                self.end_session("done")
        except Exception:
            self._crashed()
            self.canvas.clear()
            self._draw_crash()

    def _session_rule(self, sensed: Sensed, info, exit_fired: bool, inside: int) -> str | None:
        """The reason the session ends on this tick, from the rules of spec 7.2, or None."""
        s, cfg = self._session, self.cfg
        if exit_fired and info.exit_gesture:
            return "exit"
        leave = info.abandon_seconds if info.abandon_seconds is not None else cfg.leave_seconds
        if self.t - s["seen"] >= leave - EPSILON:
            return "left"
        if s["prompt"] is not None:
            if (self.player is not None and self.player.raised_wrist is not None) or s["active"] > s["prompt"]:
                s["prompt"], s["active"] = None, self.t
            elif self.t - s["prompt"] >= PROMPT_SECONDS - EPSILON:
                return "inactive"
        elif self.t - s["active"] >= cfg.inactive_seconds - EPSILON:
            s["prompt"] = self.t
        if (self.t - s["start"] >= cfg.max_session_seconds - EPSILON and inside > info.players
                and self._state.get("phase", "play") != "play"):
            return "capped"
        return None

    def _draw_overlays(self, info) -> None:
        c = self.canvas
        progress = self._exit.progress
        if info.exit_gesture and progress > 0.0 and self.player is not None:
            r = (1.0 - progress) * (min(c.width, c.height) / 2 - 2) + 1
            c.circle(self.player.zone_x * (c.width - 1), c.height / 2, r, RING)
        if self._session["prompt"] is not None:
            lines = _wrap(PROMPT, c.width - 2, c)
            top = (c.height - CELL_H * len(lines)) // 2
            c.fill_rect(0, top - 1, c.width, CELL_H * len(lines) + 1, (0, 0, 0))
            for i, line in enumerate(lines):
                c.text((c.width - c.text_width(line)) // 2, top + i * CELL_H, line, (255, 255, 255))

    def _draw_crash(self) -> bool:
        """Draw the fading crash icon; False once it has faded (and the runner is back in the lobby)."""
        icon, since = self._crash
        u = (self.t - since) / CRASH_SECONDS
        if u >= 1.0 - EPSILON:
            self._crash = None
            self._to_lobby()
            return False
        color = tuple(math.floor(v * (1.0 - u) + 0.5) for v in CRASH_RED)
        self.canvas.blit(icon, (self.canvas.width - icon.shape[1]) // 2, (self.canvas.height - icon.shape[0]) // 2,
                         color)
        return True

    def _push(self) -> None:
        if self.raw_frames is not None:
            self.raw_frames.append(self.canvas.frame.copy())
        try:
            out = self.governor.apply(self.limiter.apply(self.canvas.frame))
            self.display.push(out)
        except Exception:
            if self.t - self._push_logged >= LOG_EVERY:
                self._push_logged = self.t
                self.log.exception("display push failed (logged once a minute)")
        held = self.governor.held_ticks
        if held > self._held_before and self.t - self._governor_logged >= LOG_EVERY:
            self._governor_logged = self.t
            self.log.info("flash governor held frames of %s (%d ticks so far)", self.current_name, held)
        self._held_before = held

    # ----- sources and the loop -----

    def _source(self, name: str, source, check: Callable[[Any], Any]) -> tuple[Any, bool]:
        try:
            got, ok = check(source.latest()), bool(getattr(source, "available", True))
        except Exception:
            if not self._source_failed.get(name):
                self.log.exception("%s source failed", name)
            self._source_failed[name] = True
            return None, False
        self._source_failed[name] = False
        return got, ok

    def sense(self, camera, audio) -> Sensed:
        """A Sensed from the sources' latest() results (spec 5, 6): camera (capture_t, bodies, blobs, motion) or
        None, audio (capture_t, Audio), capture times on the injected clock in seconds. A result older than
        CAMERA_STALE or AUDIO_STALE is empty and its source unavailable (spec 10), as is a source whose latest()
        raises, gives another shape, or stamps a time that is not finite or is over CLOCK_SLACK ahead (logged once
        per run of failures). t and camera_t are on the runner's t before this tick's
        dt; tick() moves both to the tick's t. Tells the lobby the status."""
        now = self.clock()
        got, camera_ok = self._source("camera", camera, lambda got: _camera_result(got, now))
        bodies, blobs, motion, camera_t, fresh = (), (), None, 0.0, False
        if got is not None:
            capture_t, *rest = got
            if now - capture_t <= CAMERA_STALE:
                bodies, blobs, motion = rest
                camera_t = self.t - (now - capture_t)
                fresh = capture_t != self._camera_capture
                if fresh:
                    self._camera_capture, self._camera_seq = capture_t, self._camera_seq + 1
            else:
                camera_ok = False
        else:
            camera_ok = False
        heard, mic_ok = self._source("audio", audio, lambda got: _audio_result(got, now))
        sound = Audio()
        if heard is not None and now - heard[0] <= AUDIO_STALE:
            sound = heard[1]
        else:
            mic_ok = False
        inputs = (CAMERA_INPUTS if camera_ok else frozenset()) | (AUDIO_INPUTS if mic_ok else frozenset())
        self._lobby_call(lambda: self.lobby.set_status(camera_ok, mic_ok, set(inputs), self.calibration.calibrated))
        return Sensed(self.t, camera_t=camera_t, camera_fresh=fresh, camera_seq=self._camera_seq,
                      bodies=tuple(bodies), blobs=tuple(blobs), motion=motion, audio=sound).with_motion(self.cfg.size)

    def loop(self, camera, audio, max_ticks: int | None = None) -> None:
        """Tick at cfg.fps. A late tick runs at once and the schedule restarts from it: no burst of catch-up
        ticks (it04 forwarded: the governor's window leaves one frame of margin for one late tick)."""
        period = 1.0 / self.cfg.fps
        last = self.clock()
        deadline = last + period
        ticks = 0
        while self.running and (max_ticks is None or ticks < max_ticks):
            now = self.clock()
            dt, last = now - last, now
            self.tick(self.sense(camera, audio), dt)
            ticks += 1
            delay = deadline - self.clock()
            if delay > 0:
                self.sleep(delay)
                deadline += period
            else:
                deadline = self.clock() + period

    def state(self) -> dict:
        """The game's (or lobby's) debug_state, then the fx_* keys, then the runner's keys, which win (spec 7.2)."""
        crashed = self._crash is not None
        out = dict(self._state)
        if self.fx is not None and not crashed:
            out.update(self.fx.debug_state())
        out.update({"game": self.current_name, "t": round(self.t, 3),
                    "idle": 0.0 if self.presence.present else round(min(self.t, self.t - self.presence.last_seen), 3),
                    "attract": self.current_name == LOBBY and not self.presence.present,
                    "hidden": sorted(self.hidden), "crashes": dict(self.crashes), "glitch": crashed,
                    "flash_held_ticks": self.governor.held_ticks,
                    "player": None if self.player is None else self.player.id, "present": self.presence.present})
        return out
```

- [ ] **Step 4: Run the tests**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_runner.py`

Expected: `73 passed`, in about 4 s.

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`

Expected: `437 passed`, no skips.

- [ ] **Step 5: Commit**

```bash
git add arcade/runner.py arcade/headless.py tests/arcade/helpers.py tests/arcade/test_runner.py
git commit -m "feat(arcade): runner with player lock, presence, session rules, crash guard, state() and sense(); every frame goes limiter, governor, push (core Task 8 part, it02 C10, it03 C21)" -m "The exit is Hold(exit_seconds, grace=capture_grace(camera_fps)), updated every tick and reset on launch (C27); after an exit the lobby sees no bodies until the hands are down. Only the player's own two hands exit. A session stays while the game's debug_state() says active is True (a numpy bool counts; 1 or \"yes\" do not). Presence and leave count in-zone bodies and moving in-zone blobs, so a parked lamp holds nothing. Games see Sensed.t on the runner's clock. A crash shows the game's icon in fading dim red for 0.5 s, logs a crash session, and hides the game after three (Q17 defaulted); a raising lobby becomes a title card. sense() reads the new latest() shapes, treats a malformed, stale or off-clock result (a capture stamped non-finite or over CLOCK_SLACK 0.1 s ahead) as unavailable and builds Sensed with keywords. launch() is refused while a game runs, and the lobby's request is read and cleared inside the lobby guard." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: run_headless, NullLobby and helpers.run, with the tick budget (core Task 8 part, spec 9.1, 9.2, it04 N23, C27)

**Files:**
- Modify: `arcade/headless.py`, `tests/arcade/helpers.py` (whole files below; each adds to Task 3's version and changes nothing in it)
- Test: `tests/arcade/test_headless.py`

**Interfaces:**
- Consumes: Task 3's `Runner`, `RecordingDisplay`, `OPENING_NIGHT` and the helpers, `Scores`, `SessionLog`, `FlashGovernor.apply` (patched in the budget test to time it) and `actors.TICK`.
- Produces:
  - `arcade.headless.NullLobby()`: a lobby that draws nothing, never requests, and records `results`.
  - `run_headless(cfg, font, game_cls, sensed_iter, seed=0, strict=True, trace=False, raw=False, display=None) -> (frames, runner)`:
    - one tick of `TICK` per `Sensed`;
    - `runner.game` is the launched instance, kept after `done()` or a crash;
    - `frames` is the `RecordingDisplay`'s list, or `[]` for another display;
    - in-memory scores and sessions, and `local_clock` fixed at `OPENING_NIGHT`.
  - `tests.arcade.helpers.run(game_cls, sensed_iter, size, font, ticks=None, seed=0, strict=True, **cfg_over) -> (frames, runner.game, runner)`: spec 9.1's `run`. `ticks` takes the first `ticks` records of `sensed_iter`, which may be endless.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/helpers.py`:

```python
"""Test helpers: configs, a spy game, a stub lobby, a fake clock and spec 9.1's run()."""
from __future__ import annotations

import itertools
import random
from dataclasses import replace
from typing import Iterable

from arcade.canvas import Canvas
from arcade.config import ArcadeConfig
from arcade.game import Game, GameInfo, icon_from_rows
from arcade.sensed import Sensed
from show.font import Font

BLANK_ICON = icon_from_rows(["." * 16] * 16)
CROSS_ICON = icon_from_rows(["#" * 16] * 2 + ["##" + "." * 12 + "##"] * 12 + ["#" * 16] * 2)


def make_cfg(size: tuple[int, int], **over) -> ArcadeConfig:
    return replace(ArcadeConfig(width=size[0], height=size[1], backend="fake", camera="none", audio="none"), **over)


def run(game_cls: type, sensed_iter: Iterable[Sensed], size: tuple[int, int], font: Font, ticks: int | None = None,
        seed: int = 0, strict: bool = True, **cfg_over):
    """spec 9.1: the real runner on sensed_iter (its first ticks records when ticks is given), returning
    (frames, the launched game, runner)."""
    from arcade.headless import run_headless

    cfg = make_cfg(size, **cfg_over)
    feed = sensed_iter if ticks is None else itertools.islice(sensed_iter, ticks)
    frames, runner = run_headless(cfg, font, game_cls, feed, seed=seed, strict=strict)
    return frames, runner.game, runner


def spy_info(name: str = "spy", **over) -> GameInfo:
    return GameInfo(**(dict(name=name, title=name.title(), verb="SPY", icon=CROSS_ICON, needs=frozenset({"pose"}))
                       | over))


class SpyGame(Game):
    """Records calls. Class attributes configure it: raise_in names the methods that raise ("init", "reset",
    "update", "draw", "done", "debug_state"), finish_after ends the game after that many updates, extra adds to
    debug_state."""

    info = spy_info()
    raise_in: frozenset[str] = frozenset()
    finish_after: int | None = None
    extra: dict = {}

    def __init__(self):
        if "init" in self.raise_in:
            raise RuntimeError("boom in init")
        self.updates = self.draws = 0
        self.size = self.rng = self.fx = self.scores_at_reset = None
        self.seen: list[Sensed] = []

    def reset(self, size, rng: random.Random, fx) -> None:
        self.scores_at_reset = getattr(self, "scores", None)
        if "reset" in self.raise_in:
            raise RuntimeError("boom in reset")
        self.size, self.rng, self.fx = size, rng, fx

    def update(self, sensed: Sensed, dt: float) -> None:
        self.updates += 1
        self.seen.append(sensed)
        if "update" in self.raise_in:
            raise RuntimeError("boom in update")

    def draw(self, canvas: Canvas) -> None:
        self.draws += 1
        if "draw" in self.raise_in:
            raise RuntimeError("boom in draw")
        canvas.pixel(0, 0, (255, 255, 255))

    def done(self) -> bool:
        if "done" in self.raise_in:
            raise RuntimeError("boom in done")
        return self.finish_after is not None and self.updates >= self.finish_after

    def debug_state(self) -> dict:
        if "debug_state" in self.raise_in:
            raise RuntimeError("boom in debug_state")
        return {"updates": self.updates, **self.extra}


def spy(name: str = "spy", info: dict | None = None, **attrs) -> type:
    """A SpyGame subclass called name, with GameInfo fields info and class attributes attrs."""
    return type(name.title(), (SpyGame,), {"info": spy_info(name, **(info or {})), **attrs})


class StubLobby:
    """A lobby that records what the runner tells it. Set request to launch a game on the next tick."""

    info = None

    def __init__(self, raise_in: frozenset[str] = frozenset()):
        self.raise_in = raise_in
        self.request: str | None = None
        self.available: set[str] | None = None
        self.status = None
        self.results: list = []
        self.resets = self.updates = 0
        self.seen: list[Sensed] = []

    def reset(self, size, rng, fx=None) -> None:
        self.resets += 1

    def update(self, sensed: Sensed, dt: float) -> None:
        self.updates += 1
        self.seen.append(sensed)
        if "update" in self.raise_in:
            raise RuntimeError("lobby boom")

    def draw(self, canvas: Canvas) -> None:
        canvas.pixel(1, 0, (0, 255, 0))

    def done(self) -> bool:
        return False

    def debug_state(self) -> dict:
        return {"request": self.request}

    def set_available(self, names: set[str]) -> None:
        self.available = set(names)

    def set_status(self, camera_ok: bool, mic_ok: bool, inputs: set[str], calibrated: bool) -> None:
        self.status = (camera_ok, mic_ok, set(inputs), calibrated)

    def end_session(self, result) -> None:
        self.results.append(result)


class FakeClock:
    def __init__(self, now: float = 100.0):
        self.now = now

    def __call__(self) -> float:
        return self.now

    def sleep(self, s: float) -> None:
        self.now += s
```

`tests/arcade/test_headless.py`:

```python
import itertools
import os
import statistics
import time

import numpy as np
import pytest

from arcade.flash import FlashGovernor
from arcade.game import RUNNER_KEYS
from arcade.headless import OPENING_NIGHT, NullLobby, RecordingDisplay, run_headless
from arcade.sources.actors import Person, scene
from tests.arcade.helpers import SpyGame, make_cfg, run, spy

BUDGET_MS = float(os.environ.get("ARCADE_TICK_BUDGET_MS", "2.0"))
SIZES = [(128, 32), (64, 64)]
WHITE = (255, 255, 255)


def stand(ticks):
    return scene(persons=[Person(id=1)], ticks=ticks)


class Speckle(SpyGame):
    """Draws a pixel its rng picks: frames that depend on the seed."""

    info = spy("speckle").info

    def draw(self, canvas):
        super().draw(canvas)
        canvas.pixel(self.rng.randrange(canvas.width), self.rng.randrange(canvas.height), WHITE)


class Strobe(SpyGame):
    """The whole wall white and black on alternate ticks, with a burst every second: the governor holds it."""

    info = spy("strobe").info

    def draw(self, canvas):
        super().draw(canvas)
        canvas.clear(WHITE if self.draws % 2 else (0, 0, 0))
        if self.draws % 30 == 0:
            self.fx.burst(canvas.width // 2, canvas.height // 2, (255, 120, 0))


class Static(SpyGame):
    """A fixed high-contrast picture: the governor passes it."""

    info = spy("static").info

    def draw(self, canvas):
        super().draw(canvas)
        for x in range(0, canvas.width, 8):
            canvas.fill_rect(x, 0, 4, canvas.height, WHITE)


def test_run_headless_returns_launched_instance_after_done(font5x7):
    frames, runner = run_headless(make_cfg((64, 64)), font5x7, spy(finish_after=5), stand(12))
    assert len(frames) == 12 and all(f.shape == (64, 64, 3) and f.dtype == np.uint8 for f in frames)
    game = runner.game
    assert isinstance(game, SpyGame) and game.updates == 5 and runner.current_name == "lobby"
    assert isinstance(runner.lobby, NullLobby) and [r.reason for r in runner.lobby.results] == ["done"]
    assert frames[4][0, 0].any() and not frames[5].any()             # then the null lobby draws nothing
    assert runner.lobby.request is None and runner.game is game


def test_run_headless_keeps_the_crashed_instance_when_not_strict(font5x7):
    boom = spy(raise_in=frozenset({"update"}))
    frames, runner = run_headless(make_cfg((64, 64)), font5x7, boom, stand(30), strict=False)
    assert len(frames) == 30 and isinstance(runner.game, boom) and runner.game.updates == 1
    assert runner.crashes == {"spy": 1} and "boom in update" in runner.last_error
    with pytest.raises(RuntimeError, match="boom in update"):
        run_headless(make_cfg((64, 64)), font5x7, boom, stand(30))  # strict is the default


def test_trace_and_raw_frames(font5x7):
    class White(SpyGame):
        def draw(self, canvas):
            canvas.clear(WHITE)

    cfg = make_cfg((64, 64))
    frames, runner = run_headless(cfg, font5x7, White, stand(10), trace=True, raw=True)
    assert len(runner.trace) == len(runner.raw_frames) == 10
    assert all(set(RUNNER_KEYS) <= set(s) for s in runner.trace) and runner.trace[-1]["updates"] == 10
    assert runner.raw_frames[-1][:-1].min() == 255                    # before the limiter (the marker row aside)
    assert frames[-1].max() < 255 and runner.limiter.scaled_ticks > 0  # after it: the day cap
    frames, runner = run_headless(cfg, font5x7, White, stand(10))
    assert runner.trace is None and runner.raw_frames is None


def test_local_time_is_fixed_to_opening_night(font5x7):
    frames, runner = run_headless(make_cfg((64, 64), leave_seconds=0.5), font5x7, SpyGame,
                                  scene(persons=[Person(id=1).leave(0.5)], ticks=40))
    assert runner.local_clock() == OPENING_NIGHT == runner.limiter.clock()
    assert runner.limiter.is_night() is False and runner.limiter.cap() == runner.cfg.apl_cap_day
    (record,) = runner.sessions.records
    assert record["start"] == "2026-11-11T21:00:00" and record["reason"] == "left"
    assert runner.sessions.path is None and runner.scores.path is None   # nothing written


def test_seeded_runs_repeat(font5x7):
    cfg = make_cfg((64, 64))
    a, _ = run_headless(cfg, font5x7, Speckle, stand(20), seed=3)
    b, _ = run_headless(cfg, font5x7, Speckle, stand(20), seed=3)
    c, _ = run_headless(cfg, font5x7, Speckle, stand(20), seed=4)
    assert all(np.array_equal(x, y) for x, y in zip(a, b))
    assert not all(np.array_equal(x, y) for x, y in zip(a, c))


def test_another_display_gets_the_frames(font5x7):
    display = RecordingDisplay(keep_all=False)
    frames, runner = run_headless(make_cfg((128, 32)), font5x7, SpyGame, stand(7), display=display)
    assert frames == [] and display.count == 7 and display.last.shape == (32, 128, 3)
    assert runner.display is display


def test_helpers_run_takes_ticks_and_config(font5x7):
    endless = itertools.cycle(list(stand(3)))
    frames, game, runner = run(SpyGame, endless, (128, 32), font5x7, ticks=10, brightness=0.3)
    assert len(frames) == 10 and game.updates == 10 and game is runner.game
    assert runner.cfg.brightness == 0.3 == runner.display.brightness and runner.cfg.size == (128, 32)
    assert runner.strict is True
    frames, game, runner = run(spy(raise_in=frozenset({"draw"})), stand(5), (64, 64), font5x7, strict=False)
    assert len(frames) == 5 and runner.crashes == {"spy": 1}


def timed(frames, stamps):
    for s in frames:
        stamps.append(time.thread_time())
        yield s
    stamps.append(time.thread_time())


@pytest.mark.perf
@pytest.mark.parametrize("size", SIZES, ids=lambda s: f"{s[0]}x{s[1]}")
@pytest.mark.parametrize("game_cls", [Strobe, Static], ids=lambda g: g.info.name)
def test_tick_budget_with_the_governors_share(game_cls, size, font5x7, monkeypatch, capsys):
    # spec 9.2's budget, with a scenario on the governor's holding path (it04 N23, C27) and the governor's share.
    # Timed on the thread's CPU clock, which is the code's cost, what the budget is for. perf_counter also counts
    # the time the thread waits preempted, and under parallel agent load that failed this test (plan review B2).
    spent = []
    apply = FlashGovernor.apply

    def timed_apply(self, frame):
        start = time.thread_time()
        out = apply(self, frame)
        spent.append(time.thread_time() - start)
        return out

    monkeypatch.setattr(FlashGovernor, "apply", timed_apply)
    frames = list(stand(330))
    stamps = []
    _, runner = run_headless(make_cfg(size), font5x7, game_cls, timed(frames, stamps),
                             display=RecordingDisplay(keep_all=False))
    ticks = np.diff(stamps)[30:] * 1000                               # the first second warms up
    governor = np.array(spent[30:]) * 1000
    assert len(ticks) == len(governor) == 300
    held = runner.governor.held_ticks
    assert (held > 0) is (game_cls is Strobe)                          # the strobe is held, the static never
    mean, p95, share = ticks.mean(), float(np.percentile(ticks, 95)), governor.sum() / ticks.sum()
    report = (f"{game_cls.info.name} {size[0]}x{size[1]}: tick mean {mean:.3f} ms, p95 {p95:.3f} ms, governor "
              f"{governor.mean():.3f} ms ({share:.0%} of the tick), held {held} ticks")
    with capsys.disabled():
        print(f"\n{report}")
    assert mean < BUDGET_MS and p95 < 2 * BUDGET_MS, report
    assert statistics.median(governor) < 0.5, report
```

- [ ] **Step 2: Run them to verify they fail**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_headless.py`

Expected: `1 error` at collection, with `ImportError: cannot import name 'NullLobby' from 'arcade.headless'`.

`helpers.run` imports `run_headless` inside the function, so `test_runner.py` still collects and passes with Task 3's `arcade/headless.py`. Check it: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_runner.py` prints `73 passed`.

- [ ] **Step 3: Implement**

`arcade/headless.py`:

```python
"""Headless pieces shared by the tests and the agent tools: a recording display, a lobby that never requests, and
run_headless, which runs one game through the real runner (spec 9.1)."""
from __future__ import annotations

import random
from datetime import datetime
from typing import Iterable

import numpy as np

from arcade.config import ArcadeConfig
from arcade.scores import Scores, SessionLog
from arcade.sensed import Sensed
from arcade.sources.actors import TICK
from show.font import Font

OPENING_NIGHT = datetime(2026, 11, 11, 21, 0)    # headless local time: evidence never depends on the time of day


class RecordingDisplay:
    """A display that keeps copies of what it was pushed: every frame (keep_all) or only the last."""

    def __init__(self, keep_all: bool = True):
        self.keep_all = keep_all
        self.frames: list[np.ndarray] = []
        self.last: np.ndarray | None = None
        self.count = 0
        self.brightness = 1.0
        self.closed = False

    def push(self, frame: np.ndarray) -> None:
        copy = frame.copy()
        if self.keep_all:
            self.frames.append(copy)
        self.last = copy
        self.count += 1

    def set_brightness(self, level: float) -> None:
        self.brightness = level

    def close(self) -> None:
        self.closed = True


class NullLobby:
    """A lobby that draws nothing and never requests a game: for tools and tests that launch a game directly."""

    info = None

    def __init__(self):
        self.request: str | None = None
        self.results: list = []

    def reset(self, size, rng: random.Random, fx=None) -> None:
        pass

    def update(self, sensed: Sensed, dt: float) -> None:
        pass

    def draw(self, canvas) -> None:
        pass

    def done(self) -> bool:
        return False

    def debug_state(self) -> dict:
        return {}

    def set_available(self, names: set[str]) -> None:
        pass

    def set_status(self, camera_ok: bool, mic_ok: bool, inputs: set[str], calibrated: bool) -> None:
        pass

    def end_session(self, result) -> None:
        self.results.append(result)


def run_headless(cfg: ArcadeConfig, font: Font, game_cls: type, sensed_iter: Iterable[Sensed], seed: int = 0,
                 strict: bool = True, trace: bool = False, raw: bool = False, display=None):
    """Run game_cls through the real runner, one tick of TICK per Sensed, and return (frames, runner).

    The runner has in-memory scores and sessions, a NullLobby, and a local clock fixed at OPENING_NIGHT (the
    brightness limiter's day cap). runner.game is the launched instance, kept after done() or a crash; with trace
    runner.trace holds state() after every tick, and with raw runner.raw_frames every frame before the limiter.
    display defaults to a RecordingDisplay keeping every frame; frames is its list (empty for another display).
    """
    from arcade.runner import Runner

    display = RecordingDisplay() if display is None else display
    runner = Runner(cfg, display, font, NullLobby(), [game_cls], seed=seed, strict=strict,
                    scores=Scores(None, lambda: OPENING_NIGHT), sessions=SessionLog(None),
                    local_clock=lambda: OPENING_NIGHT)
    runner.trace = [] if trace else None
    runner.raw_frames = [] if raw else None
    runner.launch(game_cls.info.name)
    for sensed in sensed_iter:
        runner.tick(sensed, TICK)
    return getattr(display, "frames", []), runner
```

- [ ] **Step 4: Run the tests**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_headless.py`

Expected: `11 passed`. The budget test times on the thread's CPU clock (`time.thread_time`, loop decision 26) and prints one line per game and layout, such as `strobe 128x32: tick mean 0.348 ms, p95 0.376 ms, governor 0.187 ms (54% of the tick), held 200 ticks`. Copy the four lines into the report: they are the governor's share of the tick (N23).

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`

Expected: `448 passed`, no skips.

- [ ] **Step 5: Commit**

```bash
git add arcade/headless.py tests/arcade/helpers.py tests/arcade/test_headless.py
git commit -m "feat(arcade): run_headless, NullLobby and helpers.run, with the tick budget on the governor's holding path (core Task 8 part, it04 N23, C27)" -m "run_headless runs one game through the real runner with in-memory scores and sessions and local time fixed at 21:00 on the opening night, keeping the launched instance after done or a crash, per-tick state() and pre-limiter frames on request. The budget test runs a full-wall strobe the governor holds and a static picture at both layouts, asserts mean and p95 against ARCADE_TICK_BUDGET_MS on the thread's CPU clock (a loaded machine does not fail it), and prints the governor's share of the tick." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Iteration verify

The operator runs these inline after Task 4, from the repo root.

1. `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest --collect-only -q | tail -1` prints `448 tests collected`. There were 334 before this iteration, and the count rises at every task: 338, 364, 437, 448.
2. `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs` prints `448 passed` with **0 skipped**. Per module:

   | Module | Tests |
   |---|---|
   | `tests/arcade/test_actors.py` | 17 |
   | `tests/arcade/test_brightness.py` | 12 |
   | `tests/arcade/test_calibration.py` | 23 |
   | `tests/arcade/test_canvas.py` | 21 |
   | `tests/arcade/test_config.py` | 43 |
   | `tests/arcade/test_doctor.py` | 10 |
   | `tests/arcade/test_festival.py` | 17 |
   | `tests/arcade/test_flash.py` | 29 |
   | `tests/arcade/test_game.py` | 39 |
   | `tests/arcade/test_headless.py` | 11 |
   | `tests/arcade/test_input.py` | 13 |
   | `tests/arcade/test_juice.py` | 26 |
   | `tests/arcade/test_look.py` | 18 |
   | `tests/arcade/test_mirror.py` | 2 |
   | `tests/arcade/test_runner.py` | 73 |
   | `tests/arcade/test_scores.py` | 14 |
   | `tests/arcade/test_sensed.py` | 21 |
   | `tests/test_colorlight.py` | 29 |
   | `tests/test_config.py` | 5 |
   | `tests/test_ddp.py` | 8 |
   | `tests/test_display.py` | 4 |
   | `tests/test_font.py` | 7 |
   | `tests/test_gitignore.py` | 6 |

   `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest --collect-only -q | grep '::' | sed 's/::.*//' | sort | uniq -c` lists the same counts.
3. No existing assert weakened: `git diff ee6780b -- tests/ | grep '^-[^-]'` prints exactly four lines, the `time.perf_counter()` lines of Task 1's clock switch (twice `start = time.perf_counter()` and twice `times.append(time.perf_counter() - start)`), each replaced by the same line on `time.thread_time()`. Anything else it prints is a Deviation.
4. `.venv/bin/python -c "import sys, arcade.juice, arcade.runner, arcade.headless; print(sorted({'cv2', 'mediapipe', 'sounddevice', 'pygame'} & set(sys.modules)))"` prints `[]`.
5. The governor's share of the tick: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs -m perf tests/arcade/test_headless.py` prints four lines, `strobe` and `static` at 128x32 and 64x64, timed on the thread's CPU clock. The strobe is held (`held` over 0) and the static picture never is (`held 0 ticks`). Record the four lines in `docs/superpowers/workflow/evidence/it05/tick-budget.txt` (create the directory with `mkdir -p docs/superpowers/workflow/evidence/it05`), with `git rev-parse HEAD` above them.
6. Frames through the whole path, for the verdict. This one-off script prints no PNG. It records, at both layouts:
   - a strobe game's raw and pushed `flash_area`;
   - the limiter's scaled ticks at `OPENING_NIGHT`;
   - the crash icon's peak red.

   ```bash
   SDL_VIDEODRIVER=dummy .venv/bin/python - <<'EOF' | tee docs/superpowers/workflow/evidence/it05/runner-path.txt
   import subprocess
   from tests.arcade.helpers import SpyGame, make_cfg, spy
   from tests.arcade.test_headless import Strobe, stand
   from arcade.headless import run_headless
   from arcade.flash import flash_area
   from show.font import Font
   font = Font.load("fonts/5x7.bin")
   print(subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip())
   for size in [(128, 32), (64, 64)]:
       frames, r = run_headless(make_cfg(size), font, Strobe, stand(90), raw=True)
       print(size, "raw flash_area", round(flash_area(r.raw_frames), 3), "pushed", round(flash_area(frames), 3),
             "held", r.governor.held_ticks, "scaled", r.limiter.scaled_ticks, "night", r.limiter.is_night())
       frames, r = run_headless(make_cfg(size), font, spy(raise_in=frozenset({"update"})), stand(30), strict=False)
       print(size, "crash red peak", max(int(f[..., 0].max()) for f in frames), "crashes", r.crashes)
   EOF
   ```

   Expected, at each layout (measured in the replay):
   - raw `flash_area` 1.0 and pushed 0.006;
   - `held` 58 and `scaled` 90;
   - `night False`;
   - a crash red peak of 96;
   - `crashes {'spy': 1}`.

   The pushed 0.006 is the strobe game's bursts: their particles are a small flash, which the governor lets through (Q13). Without the bursts the pushed `flash_area` is 0.0. The whole-wall strobe itself flashes nowhere after the governor, and the crash icon never exceeds dim red. The script logs the crash's traceback on stderr; that is expected.
7. `git log --oneline -5` shows the four commit messages above, in order. `git status --short` is clean apart from `docs/superpowers/workflow/` files.
