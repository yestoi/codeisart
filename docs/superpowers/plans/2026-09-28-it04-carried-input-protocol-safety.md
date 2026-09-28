# Iteration 4: Carried Preview Fixes, Input Helpers, Game Protocol and Frame Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close iteration 3's carried fixes C18-C20. Then build the first slice of M3, the pure modules the runner will consume:
- the input helpers, with carried C10 folded in;
- core Task 7, the game protocol, registry and scores;
- the brightness limiter and the flash governor, spec 7.6's two hard ceilings on every frame, as the owner's answers to Q11-Q13 and Q15 amend it.

**Architecture:** Task 1 changes four existing files:
- `circle` draws its centre pixel at the radii where `fill_circle` does, and a huge Python int clamps like a huge float.
- `apply_gamma` always returns a new array.
- `look.check_settings` validates the render settings with `ValueError`. `render` and `PreviewDisplay` use it at construction.
- `look.light_lut(gamma)` is the looks' light table made public and checked, so the governor and the limiter share it.
- `config` refuses `look = "distance"` below `sdl_scale` 4.

Tasks 2 to 4 are new modules, each pure and testable alone:
- `arcade/input.py` (`Edge`, `Hold`, `Cursor`, `OneEuro`) takes graces in seconds, and `capture_grace(camera_fps)` sizes them in camera captures (C10).
- `arcade/game.py` holds a validated `GameInfo`, the `Game` protocol, the runner's reserved keys and `icon_from_rows`.
- `arcade/games/__init__.py` discovers games in `MENU_ORDER` with guarded imports.
- `arcade/scores.py` keeps tonight's and last night's bests and appends the sessions log. Neither ever raises into a game over a file, and numpy numbers are numbers.
- `arcade/brightness.py` scales a frame's average picture level down to the day or night cap through a lookup table, never below half. Its factor falls at once and rises slowly. Night is the clock's window or lux night (Q12).
- `arcade/flash.py` holds a pixel's transition when the 30 frames before already hold 6, measuring light three ways (luminance, saturated red doubled, red excess), unless the flash is a small area (Q13). Over-budget flips on 12.5% of the wall are held however small (Q15), and a square backstop holds any 32 px square whose mean light would flash past the budget (B7). It runs last, after the limiter (Q11).

Nothing here is wired into a runner yet. That is the next slice.

**Tech Stack:** Python 3.12 from uv, numpy and pytest, with the venv from iteration 1. Nothing is installed.

**Spec:** `docs/superpowers/specs/2026-09-26-wall-arcade-design.md`, revision 3, with the owner's answers Q11-Q13 and Q15 (`docs/superpowers/workflow/decisions.md`), which amend it until revision 4:
- sections 4.3 and 9.4 for Task 1;
- 4.1, 5 and 6.4 for Task 2;
- 7.1, 7.2 (runner keys) and 7.5 for Task 3;
- 4.3 (`apl_cap_*`, `night_*`, `gamma`) and 7.6 for Task 4.

**Sources merged here (this plan overrides them where they differ):**
- the roadmap's "Carried fixes" C10 and C18-C20 (`docs/superpowers/workflow/roadmap.md`);
- core plan `docs/superpowers/plans/2026-09-26-wall-arcade-core.md` Task 7 (line 2144), with its revision-3 amendment (lines 484-500);
- the parts of the Task 8 amendment (lines 501-545) that name `arcade/input.py`, `arcade/flash.py`, `arcade/brightness.py` and their tests;
- the review prototype `docs/superpowers/reviews/2026-09-26-arcade-review-lenses/flashguard2.py` (`FlashLimiter`);
- plan review rounds 1 and 2, `docs/superpowers/workflow/evidence/it04/plan-review.md` (see "Plan review round 1: what changed" and "Plan review round 2: what changed");
- the Global Constraints below.

Every file below is final code, given whole. An implementer needs nothing else.

## M3 slicing

M3 is "game protocol with `SCENARIOS`, `_xy`, `MENU_ORDER`, and `GameInfo.layouts`; runner with session rules, flash governor, brightness limiter; attract director with four modes and the mirror". It splits into three iterations, in dependency order:

| Iteration | Tasks | What lands |
|---|---|---|
| **it04 (this plan)** | 4 | The carried fixes C18-C20, then the pure modules the runner consumes: input helpers (with C10), game protocol, registry and scores (core Task 7), and the brightness limiter and flash governor. Nothing here depends on the runner, and the runner depends on all of it. |
| **it05** | 3 | 1. `arcade/juice.py`. 2. The runner: `PlayerLock`, `Presence`, session rules, crash guard, `state()`, `sense()` with the new `latest()` shapes and C21's keyword `Sensed`, and the tick order limiter, governor, push (Q11). 3. `run_headless`, `helpers.run` and `NullLobby`. It also takes C22 (the torso floor) and C10's runner half, the exit `Hold` with `capture_grace(cfg.camera_fps)`. |
| **it06** | 2 or 3 | The attract director (tiers, sub-states, doors with dwell decaying over 0.3 s, cards), the mirror with `draw_figure` and `to_wall`, and the four modes: watcher, echo, warp and contours. |

M3 is done when it06 lands. C11 and C17 stay with core Task 15. C23 stays with core Tasks 13 and 18.

## Global Constraints

Carried from the core plan ("Global Constraints" as replaced by "Global Constraints, revised"):

- Frames are numpy arrays of shape `(height, width, 3)`, dtype uint8, RGB, row-major.
- Every game declares `layouts`, and its tests are parametrized over the declared layouts (spec 9.1). 128x32 is the default and design layout. This iteration has no games; the `size` fixture covers 128x32 and 64x64.
- Brightness:
  - The runner calls `display.set_brightness(cfg.brightness)` once.
  - The Colorlight backend enforces it at the panel with the card's brightness packet.
  - The fake and SDL displays store the level. The SDL window itself shows full brightness, and `PreviewDisplay` models the level in the preview it renders.
  - DDP logs once that brightness is Falcon Player's setting.
  - Pixels pushed to hardware are never scaled for `brightness`. The brightness limiter (Task 4) is a separate, spec 7.6 picture-level cap and does scale frames.
- Tick rate 30 Hz. `dt` handed to games is clamped to 100 ms. Clocks and random sources are injected.
- Never seed from `hash()` of a str. Use `zlib.crc32` and print the seed in the assertion message.
- Modules that import `mediapipe`, `picamera2`, `cv2.VideoCapture` devices or `sounddevice` do so inside the class constructor, probe function or thread, never at module import. Tests never need hardware extras.
- Tests run headless: `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy` are set in `tests/conftest.py` before pygame is imported.
- No `print` in library code. Use `logging.getLogger("arcade")` in `arcade/` and `logging.getLogger(__name__)` in `show/`. CLI entry points and `tools/` may print.
- Python 3.12 through uv on the Mac, with one OpenCV distribution, `opencv-contrib-python`.
- Commit after every task with the exact message and `git add` list given in the task.

Operator rules for this loop:

- Test modules are copied from this plan verbatim. Any difference, however small, is a Deviation and must be reported as one.
- Never remove or weaken an existing assert; only add or tighten. If an existing assert must change, the task and its commit message say why. This iteration changes no existing test line.
- `arcade/games/__init__.py`: after Task 3 creates it, the only permitted edit is adding a name to `MENU_ORDER` in its spec position.
- Never push. Never run `git push` or `gh pr create`.
- Use `.venv/bin/python` (Python 3.12 from uv). Never use the system `python3` (3.14), never `pip`, and never activate the venv in a way later commands depend on.
- Install with `uv pip install --python .venv/bin/python ...`. This iteration installs nothing.
- Run tests from the repo root with `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`. Append a path to run one module.

## Loop decisions taken by this plan (journal each one)

1. **M3 is sliced as above.** it04 builds the runner's inputs, it05 the runner, and it06 the lobby. Each slice ends with the whole suite green and nothing half-wired.
2. **C18: a ring at a radius that rounds to 0 is its centre pixel, as the disc is.** `_disc` applies the ring mask only when `r > 0`. So radii 0, 0.25 and 0.49, and negative, infinite, NaN and `None` radii (which land at `-_FAR`), draw the centre pixel in `circle` exactly as in `fill_circle`. `circle(8, 8, 0.5)` rounds half up to radius 1 and draws the eight neighbours, as before.

   `_i` clamps a Python `int` directly before trying the float path. So `10**400`, which has no float, lands at `_FAR` like `1e300`, instead of at `-_FAR` through `OverflowError`.

   `_i`'s docstring now states all of this.
3. **C19: `apply_gamma` always returns a new array.** At gamma 1.0 that is `frame.copy()`, so a caller that writes into the result, like core Task 11, never edits the caller's frame. It costs one 12 KB copy per `led` preview frame.
4. **C20: preview settings are checked where they are given.**
   - `look.check_settings(mode, scale, gamma, metres=5.0) -> int` holds `render`'s checks and returns the scale as an `int`. `render` calls it first, then checks the frame.
   - `PreviewDisplay.__init__` calls it, so a bad setting raises at construction, not on the first push, and `PreviewDisplay.scale` is always an `int`.
   - `look.is_real(v)` is `numbers.Real` and not a bool (`np.True_` included). `check_settings`, `dim` and `PreviewDisplay.set_brightness` use it, so `None`, a string or a bool raises `ValueError`, not `TypeError`. A numpy number passes. Tasks 2 to 4 use the same check for every number they take (B5).
   - NaN and levels of 0 or less still give black in `dim`, as iteration 3 decided.
   - `set_brightness` checks before storing or forwarding, so a bad level leaves both the preview and the inner display as they were.
   - The roadmap offered "require scale >= 4 for `look = "distance"` at config load, or document the floor". This plan requires it: `config.DISTANCE_MIN_SCALE = 4`, and `load_config` raises `ValueError` naming `sdl_scale`. `render` itself still accepts any scale, because core Task 13 renders contact-sheet cells at scales it computes.
5. **C10: every grace is given in seconds and sized in camera captures.** The camera captures at `camera_fps` (10), and a `Sensed` body holds for three 30 Hz ticks. `capture_grace(camera_fps, captures=CAPTURE_GRACE)` returns `(captures + 0.5) / camera_fps`, which is 0.55 s at 10 fps with `CAPTURE_GRACE = 5` (Q10, answered). The half capture keeps a run of exactly `captures` misses from tripping on a rounding error.

   Measured over 6000 s of `degrade(REAL_NOISE)` captures of 300 ids, both hands up reads false on 28.1% of captures, in runs:

   | Consecutive missed captures | Number of runs | How often |
   |---|---|---|
   | 1 | 8451 | |
   | 2 | 2745 | |
   | 3 | 665 | 3 or more: about every 7 s of holding |
   | 4 | 165 | |
   | 5 | 16 | 5 or more: about every 5 minutes |
   | 6 | 4 | about every 25 minutes |
   | 7 or more | 0 | never |

   Over 40 ids:
   - With the amendment's 0.25 s grace, only 30 of 40 three-second exit holds completed.
   - With `capture_grace(10)`, all 40 fire, between 3.17 and 3.77 s, and each resets between 5.5 and 5.7 s after the hands drop at 5 s. Over 400 ids, two fire later, at 3.97 and 4.27 s, so the test's bound is `fired < 4.4` (N5).
   - `Edge` without a grace fires a second time during 35 of 40 raises. With `capture_grace(10)` it fires exactly once per raise on all 40.

   The helpers keep the amendment's default `grace=0.25`, which the named core tests pin (`test_hold_tolerates_200ms_dropout_resets_after_300ms`). The lobby and the runner pass `capture_grace(cfg.camera_fps)`; a game chooses its own grace, and the module docstring says so (N7). The runner's exit hold is it05.

   The costs of 5 captures (N7): a real release registers 0.55 s later rather than 0.25 s; a new `Edge` press needs more than 0.55 s of hands down, so raises faster than about 1.5 a second merge into one press; and a `Cursor` freezes for up to 0.55 s through a dropout instead of jumping to the hanging hand. Flap and Swat use velocity and paths, not `Edge`, so nothing planned breaks.
6. **C10: `Cursor` adds hand hysteresis to `Body.cursor`.** `Body.cursor` is stateless and jumps to the hanging wrist whenever the raised one misses a capture: 314 jumps over 60 ids, against 0 for `Cursor`.
   - `Cursor` keeps the hand it chose.
   - While that wrist is missing, it holds the last position for up to `grace`.
   - It changes hands only when the other wrist's reach is more than `switch = 1.25` times the current one's.
   - It measures reach exactly as `Body.cursor` does: from the wrist's own hip when that hip is confident, else from the confident hips, else from the shoulders. So its first choice is `Body.cursor`'s.
7. **`OneEuro` is the paper's filter, timed by capture time.** It uses Casiez, Roussel and Vogel, CHI 2012, with the amendment's defaults `min_cutoff=1.0, beta=0.007, d_cutoff=1.0`.
   - A sample at a time no later than the last one returns the last output. That covers the same capture held over three ticks.
   - A NaN or infinite sample or time is ignored.
   - `beta = 0.007` is the paper's value for pixel units and barely adapts in the arcade's 0..1 units. The measured lag on a 0.3/s ramp is 0.159 s. Tuning it is forwarded to the tracker (core Task 16).
8. **`GameInfo` is validated in `__post_init__` and is `frozen=True, eq=False`.** A dataclass `__eq__` would compare the numpy icons and raise on the ambiguous truth value, so identity equality it is.
   - The icon is kept as a read-only bool copy.
   - `needs` and `layouts` accept a set, frozenset, tuple or list, never a bare string, and are stored as frozensets.
   - `players` is the int 1 or 2, not a bool. `exit_gesture` is a bool. `kind` is one of `KINDS`.
   - `abandon_seconds` is `None` or a finite real number over 0, numpy numbers included (B5).
   - `name` is a lowercase identifier, because it is the module name.
   - Every failure is a `ValueError`, so a broken game is skipped at discovery rather than launched.
   - `Game.SCENARIOS` is a read-only `MappingProxyType({})`, so a subclass that writes into the shared default raises `TypeError` instead of adding scenarios to every game (N12).
9. **Discovery tells "not written yet" from "broken".**
   - `all_games()` imports `arcade.games.<name>` for each name in `MENU_ORDER`.
   - A `ModuleNotFoundError` for that module itself is silent, because seven of the ten games do not exist for several iterations. One for any other name, a sibling helper such as `arcade.games.strongman_audio` included, is a broken game.
   - A missing dependency inside the module, or any other exception, is logged with its traceback and skipped.
   - A `GAME` that is not a class, has an `info` that is not a `GameInfo`, or has an `info.name` that is not the module's name is logged and skipped.
   - `get_game(name)` raises `KeyError`.
   - The tests fake every module, the empty package included, so no test line depends on which games exist (B6). The real package is checked in this iteration's verify step 5.
10. **Scores.**
    - A night runs from 16:00 local time to 16:00 the next day (`night_of`).
    - `record` returns True for the first finite value of the night, or for a value strictly above tonight's best and at least `margin` above it. A tie is not a new best.
    - A numpy number is a number (B5). A value that is NaN, infinite, `None`, a bool or not a number is logged and never a best.
    - A negative, NaN or infinite margin is a caller bug: `ValueError`.
    - When the first record of a new night replaces an older entry, the old one is kept under `"previous"`, so `last_night()` can show the night before tonight after a restart. Later records that night keep it.
    - The file is written to `scores.json.tmp`, flushed, fsynced, then `os.replace`d.
    - A missing, unreadable or malformed file starts empty (or drops the malformed entries) with a warning. A failed write logs and keeps the scores in memory.
    - `SessionLog` validates the end reason and start time, which are runner bugs, and writes non-finite numbers as `null`.
11. **The flash governor counts a transition as the prototype does, and holds when the previous second already holds 6 (N1).** Per pixel and per signal:
    - The governor keeps the lowest and highest value since the last transition, and that transition's direction.
    - A rise of `THRESHOLD = 0.1` or more over the lowest (unless already rising), or a fall of 0.1 or more from the highest (unless already falling), is a transition, and both extremes restart there. Before the first transition either way counts, so a slow fall from the first frame counts as a slow rise does (N3).
    - A transition is over budget when the pixel's previous `fps` frames already hold `BUDGET = 6`. That is the prototype's window and spec 7.6's "already transitioned six times in the last second", so any `fps + 1` frames show at most 6. It leaves one frame of margin for a late tick: an exact 3 Hz strobe still shows every flash, each 7th transition a frame late.
    - An over-budget transition is held, and the pixel keeps its previous output, unless the flash is a small area (decisions 16 and 18).
    - Then the square backstop (B7): a 32 px square whose mean light would make a transition while its previous `fps` frames already hold `BUDGET` is held whole, every pixel at its previous output, whatever the pixels' own budgets. The governor re-measures and repeats until no such square flips. The loop ends: the held set only grows, a bad square always has a pixel not yet held (a square held whole shows its previous mean, which cannot flip), and showing the previous frame everywhere flips nothing. The review saw at most 4 passes, and this plan's attacks at most 3.
    - **The backstop is bounded (operator decision, round 2).** A wall governor must never hang, so the loop runs at most `BACKSTOP_PASSES = 8` passes. If a square still flips after that, which no search has reached (the most seen is 4), every pixel is held: the wall shows the previous output, which flips nothing, so the bound still holds and is strictly tighter. The fallback is logged once per governor with `logging.getLogger("arcade")`. `test_the_backstop_gives_up_by_holding_the_whole_frame` forces it with a square tracker whose first square always flips, and asserts 8 passes, the previous output, `held_ticks` rising each frame, one log record, and trackers advanced on what was shown with nothing counted (N25). `test_pixels_taking_turns_are_held_by_the_square` asserts the fallback never fires on the review's attacks.
    - A held pixel is measured as shown: its three signals are those of the colour it keeps, so a pixel held on one signal cannot run past the budget on another (B1). The pixel and square trackers both advance on the shown signals.
    - The first frame passes.
    - `apply` returns the input array itself when nothing is held, and a new array otherwise. It keeps its own copy of what it showed, so the runner may redraw into one canvas array every tick.
    - The window, budget and threshold are the `fps`, `budget` and `threshold` keywords. The runner passes `fps=cfg.fps`, so the window is always one second (B4). `threshold` must be over 0 and finite; `inf` would turn the governor off.
    - Its cost at 128x32 on this Mac is 0.16 ms median on a static frame and 0.21 ms on random frames, where the held path runs every tick (spec 7.6 measured 0.2 ms for the prototype; the budget is the tick's, spec 9's `ARCADE_TICK_BUDGET_MS`; the test allows 0.5 ms; re-timed on the Pi 5 at GATE B).
12. **Light is the previews' light, measured three ways (B1).** `look.light_lut(gamma)` checks gamma and returns the looks' own read-only table, `(v / 255) ** (2.2 / gamma)`, so the governor, the limiter and the `led` and `distance` looks agree (N9). `signals(frame, gamma)` gives each pixel three values, a swing in any of which is a transition:
    - Rec. 709 luminance of that light;
    - the same, doubled when red is at least `RED_SHARE = 0.8` of the light (`R / (R + G + B)`, spec 7.6); black is 0 either way;
    - red excess, `max(0, R - G - B)` in light, which moves when saturated red trades against another colour of about the same luminance: the red/blue strobe the review found passing at 12-15 Hz.

    Doubling alone hid flashes: red against green moves luminance by 0.21 but the doubled values by less than the threshold. Tracking plain luminance as well restores them. Each of the three catches a swing the other two miss, and the tests show one pair for each.
13. **The brightness limiter falls at once and rises slowly (B2).**
    - APL is the mean light of every channel of every pixel after gamma, which is what the review's APL figures measured and roughly what the LEDs draw.
    - The frame needs `1.0` when its APL is at or under the cap, else `max(MIN_FACTOR, cap / APL)` with `MIN_FACTOR = 0.5`.
    - The factor falls to what the frame needs at once, and rises by at most `RELEASE = THRESHOLD / 10 = 0.01` a tick, never past what the frame needs. So a level that comes and goes, or a cap that changes, moves a pixel's light by at most a tenth of a transition a tick.
    - While the factor is below 1.0, the frame goes through one lookup table, `floor(v * factor ** (gamma / 2.2) + 0.5)`. At gamma 2.2 the light scales by `factor`, and white at the floor becomes 128. At 1.0 the frame is returned as is (the same array).
    - Because an `ArcadeConfig` built in code skips `load_config`, the limiter validates the fields it uses.
14. **Night is the clock's window or lux night; lux only adds night (Q12, replacing this decision's round-1 text).**
    - The clock's night is `night_start <= now < night_end`, spanning midnight when the start is later. Equal times mean never.
    - Lux night starts at a reading under `night_lux`. It ends once no reading has been under `LUX_RELEASE = 1.5` times `night_lux` for `LUX_HOLD_S = 10` seconds of the limiter's clock. So a reading flapping between 4.9 and 5.1, or anywhere under 7.5, keeps the night cap, and the cap changes at most once in 10 s.
    - A clock set back keeps lux night until 10 s past the last dark reading.
    - `None`, NaN, an infinity, a non-number and an exception from `lux()` are no reading. The exception is logged once (N10).
    - The clock is local time, injected. The runner passes a local clock, never its monotonic one (B4).
    - The values 1.5 and 10 s are loop proposals; the tests pin them.
15. **The measures count as the governor does.** Each takes `gamma`, `fps`, `threshold` and, where it applies, `budget`:
    - `flash_area(frames)`: the largest share of the wall with more than `budget` transitions in any `fps + 1` consecutive frames. Spec 7.6's "a game's raw output may flash at most 10 percent of the wall" is `flash_area(raw) <= 0.1`. Governed output of any flash that is not a small area gives 0.0.
    - `concurrent_area(frames)`: the largest share of any 32x32 square whose over-budget transitions went the same way in one frame, as the governor measures a flash's area. Governed output is always under `SMALL_AREA`.
    - `square_flashes(frames)`: the most transitions the mean light of any 32x32 square made in `fps + 1` consecutive frames. Governed output is always at most `budget` (B7).
16. **Small flashing areas are not held (Q13), and every square's mean light is governed (B7).** An over-budget transition is held only when the flash is not small. The flash is small, and no pixel is held for its own budget, while all three:
    - **Concurrent area:** the over-budget pixels whose signals all rise or all fall in this frame fill under `SMALL_AREA = 0.1` of every `WINDOW = 32` pixel square. A rise and a fall are counted apart, because text scrolling past turns some pixels on and others off.
    - **Field area (Q15, decision 18):** the over-budget pixels flipping in this frame, rises and falls together, fill under `FIELD_AREA = 0.125` of the whole wall.
    - **Area over time:** no 32x32 square's mean light (its mean of each signal) has itself made `budget` transitions in the previous `fps` frames.

    **The square backstop (B7).** Whatever the pixel rule decides, a square whose mean light would make a transition while its previous `fps` frames already hold `budget` is held whole (decision 11). The pixel rule only ever holds a pixel that is over its own budget. Without the backstop, a flash whose pixels take turns reached the wall at full rate: interleaved dithers flashing one after another keep every pixel within its budget, while every square's mean, and the wall's, flashes at up to 15 Hz with nothing held (the review's B7 table). With the backstop, on what the wall shows:
    - every pixel makes at most `budget` transitions in any `fps + 1` frames, unless it is part of a small flash;
    - every 32x32 square's mean light always does, however its pixels take turns.

    `test_pixels_taking_turns_are_held_by_the_square` pins the review's two attacks on both layouts: 5 dithers (the mean swings 0.2 at 15 Hz) and 2 dithers (it swings 0.5), each asserting `square_flashes(frames) >= 12`, `held_ticks > 0` and `square_flashes(out) <= BUDGET`. `test_a_flash_spread_over_frames_is_held` pins the ramp attack at `square_flashes(out) <= BUDGET`.

    **The square flag is global (N20).** One square whose mean is over budget anywhere lets over-budget pixels be held anywhere on the wall in that frame, so a scrolling title can smear while an unrelated corner is being governed. It is conservative (it only ever holds more), and the backstop, not the flag, is what bounds each square's mean. So the flag stays global.

    **Windowed, not contiguous.** WCAG counts "the combined area of flashes occurring concurrently" in any 10 degree field, and BT.1702 and Ofcom count the combined area on the screen. A connected-region measure would pass a field of dots or a checkerboard, each region tiny. Summing every transition inside any square holds them: dots at a quarter of the wall and a checkerboard reversal are both held in the tests.

    **Why 32 pixels and 10%:**
    - A 32 px square is 16 cm of P5 wall: a 10 degree field, WCAG's unit, seen from 92 cm.
    - The guidance limits a flash to 25% of the screen (ITU-R BT.1702, Ofcom) or of any 10 degree field (WCAG 2.2, 0.006 sr). The real margin against 25% is about 1.25x, not the 2.5x that 10% suggests (N15). The concurrent rule counts rises and falls apart, so up to about 2 x 9.9% of a square can flash at once in opposite phase, and the guidance's "combined area of flashes occurring concurrently" does not split by direction. The field cap (decision 18) bounds the two directions together at 12.5% of the wall, and the backstop bounds every square's mean.
    - 10% of the square is 102 px, 25.5 cm². That is WCAG's 0.006 sr for a viewer 65 cm from the wall, closer than a player stands.
    - 10% equals `THRESHOLD`. A full-swing flash on under 10% of a square moves the square's mean light by under one transition's worth, so the mean-light rule and the area rule agree.
    - A full-field flash is 100% of every square, and a flash over a large area is over 10% of the squares inside it, so neither can pass. A flash spread over frames or taken in turns moves the squares' means, and the backstop holds it. Red counts on the area measure through its signals, as everywhere else.

    **Measured (at 128x32 and 64x64, the ten titles in the 5x7 font):** text scrolling at 20-30 px/s flashes 5-29% of the wall pixel by pixel. Its concurrent area is at most 0.080 at scale 2 and 0.074 at scale 1, its over-budget flips cover at most 9.9% of the wall in a frame (scale 1 at 30 px/s on 128x32), and its squares' means make at most 2 transitions a second, so nothing is held. At 60 px/s (a 2 px jump a frame) it is held. A 16 px square would put the same text at 0.16-0.18, over the fraction, which is why the square is 32. The margins are thin (N21): the stroke-heavy "MMMM WWWW HHHH MMMM" reaches a concurrent area of 0.090 at scale 2 and flips 13.1% of the 128x32 wall at scale 2 and 30 px/s, so the field cap holds it for 6 frames. The constraints for door titles are forwarded to it06.

    **The residual accepted:** a fine twinkle or sparse grating whose over-budget pixels stay under 10% of every square going one way and under 12.5% of the wall in every frame, and whose squares' means stay within budget, passes. That is sparkle, not a flash of an area. Regular patterns below that area are a content rule: the game guide and the soak's `pattern` check (Q15, forwarded).
17. **The tick order is limiter, then governor, then push (Q11).** The governor runs last, so what it bounds is what the wall shows: no level change of the limiter can strobe a static frame after it. On the pushed frames every 32x32 square's mean light makes at most `budget` transitions in any `fps + 1` frames, and every pixel does unless it is part of a small flash (decision 16). The cost is that a held pixel can sit above the cap for up to a second, by at most the light of the frame the governor keeps. `test_limiter_then_governor_never_strobes` composes the two in this order against the review's attacks: out-of-phase blocks, lux flapping between 4.9 and 5.1, and a random search. Release alone already keeps the first two steady after the limiter (`flash_area` 0, and a constant frame under the flapping reading). The random search runs 30 trials of 60 frames of blocks switching at random under a flapping, failing sensor. In every trial something is held (`g.held_ticks > 0`, asserted, N22), the pushed frames' `concurrent_area` stays under `SMALL_AREA`, and `square_flashes(pushed) <= BUDGET`. Without the backstop, 5 of the 30 trials push a square's mean past the budget (worst 8 transitions), and the test fails. Measured without release, the limited frames of the first case flash 3.1% of the wall.
18. **The field cap (Q15).** Over-budget flips on `FIELD_AREA = 0.125` of the whole wall or more in one frame, rises and falls together, are held even when every square's share is small (decision 16).
    - **Why:** ITU-R BT.1702-3 Guideline 2 treats "more than five light and dark pairs of clearly discernible stripes" that reverse, oscillate or flash over more than 25% of the screen as potentially harmful (N14). A grating of 1 px lines every 11 px, reversing every frame (12 pairs across 128 px, the whole wall, 15 Hz), flips 18.75% of the wall over budget in each frame, while no square has 10% going one way and every square's mean is constant. Q13's rule passed it untouched (`flash_area(pushed)` 0.188). The cap holds it to 0.
    - **Why 12.5%:** Q13's wording is "below a fraction of the field". Measured maxima for text scrolling at 20-30 px/s are 0.099 for the ten titles at 1x and 30 px/s on 128x32, 0.084 at 2x, and 0.072 on 64x64, so titles pass.
    - **The boundary:** a grating every 16 px (8 pairs) flips exactly 12.5% and is held; with one pixel less it passes untouched.
    - **What it cannot do:** no cheap governor rule separates a grating from ordinary motion below 12.5% of the wall. So regular patterns are also a content rule: the game guide's pattern rule and a soak `pattern` check (forwarded).
    - **Tests:** `test_a_reversing_grating_is_held_by_the_field_cap` and `test_titles_scrolling_pass_under_the_field_cap` (both layouts). 0.125 is a loop value, journaled here.

## Owner questions

All answered (2026-09-28, `docs/superpowers/workflow/decisions.md`):

- **Q10: How many missed camera captures should a hold, an edge and the cursor ride out (C10)?** Answered: `CAPTURE_GRACE = 5`, 0.55 s at 10 fps (loop decision 5). `test_capture_grace_is_sized_in_captures` pins it.
- **Q11: Tick order.** Answered: governor last. Limiter, then governor, then push (loop decision 17). This departs from spec 4, 7.2 and 8.1, and is recorded for spec revision 4.
- **Q12: May lux cancel the clock's night?** Answered: lux only adds night, with hysteresis (loop decision 14).
- **Q13: Scrolling titles against the per-pixel flash rule.** Answered: exempt small areas, with a conservative fraction from broadcast guidance, journaled (loop decision 16). Recorded for spec revision 4.
- **Q14: The plan review is blocked after two rounds on B7 with a verified fix. Apply it?** Answered: apply B7 exactly as the reviewer specified, then a confirm-only third round (loop decisions 11, 16 and 17; "Plan review round 2: what changed").
- **Q15: Regular patterns.** Answered: a game-guide content rule (no reversing or oscillating stripes with more than 5 pairs over more than 25% of the wall, BT.1702-3 Guideline 2), a soak `pattern` check, and the governor's 12.5% field cap (loop decision 18; the first two are forwarded).
- **Q16: An absolute flash threshold.** Answered: keep `THRESHOLD = 0.1`; in prototype week measure the wall's white at `brightness` 0.4 (L cd/m²) and set `THRESHOLD = min(0.1, 20 / L)` at GATE B (forwarded).

Dwell time, session timeouts and presence thresholds are not touched in this iteration; their spec defaults stand in `arcade/config.py`.

## Plan review round 1: what changed

Verdict BLOCKED on B1-B6 (`docs/superpowers/workflow/evidence/it04/plan-review.md`). Each finding and what this revision does:

- **B1, red flashes missed and luminance flashes masked.** Three signals per pixel (loop decision 12), a transition on any of them, and held pixels measured as shown (decision 11). Tests: `test_red_traded_against_another_colour_is_a_flash` (the four review pairs at 15 and 12 Hz, plus one pair that only each signal catches) and `test_held_pixels_are_measured_as_shown`.
- **B2, the limiter strobing after the governor.** Fast attack and slow release, `RELEASE = 0.01` (decision 13), and the owner's order, governor last (Q11, decision 17). Tests: `test_factor_falls_at_once_and_rises_slowly` and `test_limiter_then_governor_never_strobes`. `test_white_frame_scaled_not_below_half` no longer checks a jump back to 1.0 after black; the ramp is checked instead. That test is new in this iteration, so no committed assert changes.
- **B3, lux cancelling the night.** Q12: lux only adds night, with hysteresis (decision 14). `test_lux_overrides_clock` is replaced by `test_lux_only_adds_night` (at 02:00 a reading of 300 keeps the night), with `test_lux_night_ends_after_10_bright_seconds` for the flapping reading.
- **B4, the runner wiring.** Forwarded: `FlashGovernor(cfg.height, cfg.width, cfg.gamma, fps=cfg.fps)` and a separate injected local clock for the limiter. `test_window_and_budget_follow_the_keywords` covers `fps=60` (2 Hz passes and 4 Hz is held, for the governor and `flash_area`), `budget` and `threshold`. `test_governor_rejects_bad_input` rejects `threshold` inf and NaN.
- **B5, numpy numbers.** `scores._finite`, `GameInfo.abandon_seconds` and every number `arcade/input.py` takes use `look.is_real`, and are stored as `float`. Tests: `test_scores_take_numpy_numbers`, the numpy margin in `test_scores_margin`, and numpy asserts in the input and game tests.
- **B6, the discovery test.** It starts with `fake_modules(monkeypatch, {})`.
- **N1:** the prototype's window, adopted (decision 11). **N3:** both extremes tracked from the first frame. **N4:** see the mutation results in "Environment facts". **N5:** bound widened to `< 4.4`. **N7:** docstring and costs (decision 5). **N8:** "Resolved conflicts". **N9:** `look.light_lut`. **N10:** a failing `lux()` is no reading, logged once. **N11:** forwarded to it05's Juice. **N12:** `MappingProxyType`. **N13:** timings re-measured (decision 11).
- **N2 and N6** are notes for spec revision 4 and change no code: the red-share cliff (keep the doubled track until the spec gives a continuous red weight), and the scrolling-title conflict, which Q13 answered.

## Plan review round 2: what changed

Verdict BLOCKED on B7, with notes N14-N24 (`plan-review.md`, "Round 2"). The owner answered Q14 (apply B7 as the reviewer specified, then a confirm-only third round) and Q15 (a guide rule, a soak check and a field cap). Each item and what this revision does:

- **B7, pixels that take turns.** The square backstop in `FlashGovernor.apply`, as the reviewer's diff gives it (loop decisions 11 and 16), with Q15's field clause added to the same condition.
  - Residual (2) is deleted from decision 16. Decisions 16 and 17 now say that every pixel makes at most `budget` transitions in any `fps + 1` frames unless it is part of a small flash, and that every 32x32 square's mean always does.
  - New: `test_pixels_taking_turns_are_held_by_the_square`, with the 5-dither 15 Hz attack and the 2-dither 0.5-swing attack on both layouts. Each asserts `square_flashes(frames) >= 12`, `held_ticks > 0` and `square_flashes(out) <= BUDGET`.
  - `test_a_flash_spread_over_frames_is_held` is tightened from `square_flashes(out) <= BUDGET + 1` to `<= BUDGET`. That test is new in this iteration, so no committed assert changes.
  - `test_limiter_then_governor_never_strobes` asserts `square_flashes(pushed) <= BUDGET` in every trial.
  - Forwarded to core Task 20's soak: `square_flashes(pushed) <= BUDGET`.
- **Q15 and N14, regular patterns.** `FIELD_AREA = 0.125` (loop decision 18).
  - New: `test_a_reversing_grating_is_held_by_the_field_cap` (both layouts). The review's grating (1 px lines every 11 px, 12 pairs across 128 px, the whole wall, reversing every frame) has `flash_area` 0.1875 raw and 0.0 governed. A grating every 16 px, exactly 12.5%, is held, and with one pixel less it passes untouched.
  - New: `test_titles_scrolling_pass_under_the_field_cap` (both layouts). The ten titles at 1x and 2x, 20-30 px/s, pass untouched (`held_ticks == 0`).
  - Forwarded to the game guide: the pattern rule (BT.1702-3 Guideline 2) and N22's note on cumulative risk. Forwarded to core Task 20: the soak's `pattern` check.
- **N15.** Decision 16 states the real margin, about 1.25x against 25%. The field cap addresses it.
- **N16, N19 and N24** confirm the plan; nothing changes. The lint facts in "Environment facts" were checked again for this revision.
- **N17 and Q16.** `THRESHOLD` stays 0.1, to be re-derived as `min(0.1, 20 / L)` at GATE B (forwarded).
- **N18.** One assert for each of the three surviving mutants:
  - `concurrent_area(two, budget=2) == 1.0` in `test_window_and_budget_follow_the_keywords`;
  - `square_flashes(one, window=8) == 30` in `test_many_small_flashes_add_up_and_are_held`;
  - a single held pixel on a 3x3 wall, counted in `held_ticks`, in `test_a_flash_just_over_the_small_area_is_held`.
- **N20.** The square flag stays global, documented in decision 16.
- **N21.** Forwarded to it06: the constraints on door titles.
- **N22.** `test_limiter_then_governor_never_strobes` asserts `g.held_ticks > 0` in every trial of the random search, where decision 17 claims it. `limited_then_governed` takes an optional `governor` for that; its return value is unchanged. The note on cumulative risk goes to the game guide.
- **The backstop is bounded (operator decision on this revision's open issue).** A wall governor must never hang: at most `BACKSTOP_PASSES = 8` passes, then every pixel is held (the previous output, which flips nothing), logged once with `logging.getLogger("arcade")` (loop decision 11). New: `test_the_backstop_gives_up_by_holding_the_whole_frame` forces the cap. `test_pixels_taking_turns_are_held_by_the_square` also asserts that the fallback never fires, and that a full-field flash is held whole (each frame shows the input or the previous output).
- **N23.** Decision 11 and "Environment facts" now read "spec 7.6 measured 0.2 ms for the prototype; the budget is the tick's". The 0.5 ms test is kept. Forwarded to it05: a holding-path scenario in the tick-budget test, and the governor's share of the tick. Forwarded to GATE B: timing on the Pi 5.

Task 4 gains 7 tests (three new functions on both layouts, and the backstop's fallback): 41 in the task and 334 in the suite.

## Plan review round 3: what changed

Verdict APPROVED (`plan-review.md`, "Round 3"), with notes N25-N28. All four are folded in:

- **N25.** `test_the_backstop_gives_up_by_holding_the_whole_frame` also asserts that after the fallback the trackers hold what was shown, `signals(out, 2.2)`, and no square window counts past the budget. This kills the two fallback mutants that survived. "Environment facts" set (5) now names the mutant it ran (a fallback that asks the tracker again), and set (6) lists the two survivors.
- **N26.** `test_held_pixels_are_measured_as_shown` adds `assert len(changes(out, 0, 127)) < 140` on a line of its own beside the existing `> 120`, so the square flag of decision 16 is tested again (without it 155 of the blinker's 179 changes pass; with it 131).
- **N27.** Decision 11 now says the fallback is reached by no search so far (the most seen is 4), not "only a bug".
- **N28.** Forwarded with the core Task 20 soak: `flash_area(pushed)` can exceed 0.125 because the field cap is per frame; the soak asserts `flash_area(raw)`.

Test counts are unchanged: 41 in Task 4, 334 in the suite.

## Forwarded to later amendments

- **it05, runner (core Task 8):**
  - C21: every `Sensed` and `Audio` built in `sense()` uses keywords.
  - C22: the torso floor.
  - C10's runner half: the exit gesture is `Hold(cfg.exit_seconds, grace=capture_grace(cfg.camera_fps))`, with a ring drawn from `progress`. The lobby's hand-up and door selection use `Edge` and `Cursor` with the same grace.
  - **The tick order is limiter, then governor, then push (Q11).** `test_push_path_order` asserts it: a frame the limiter changes reaches the governor, and what the governor returns is what is pushed.
  - The runner builds `BrightnessLimiter(cfg, clock=local_clock, lux=lux)` and `FlashGovernor(cfg.height, cfg.width, cfg.gamma, fps=cfg.fps)` once, and reports `flash_held_ticks` as `governor.held_ticks`.
  - `local_clock: Callable[[], datetime]` is a separate injected local clock, never the runner's monotonic `clock`. `run_headless` and `helpers.run` fix it to a constant local time (21:00 on 2026-11-11, the opening night), so headless evidence never depends on the time of day (B4).
  - A late tick: the core loop runs the next tick at once when one is late, so two pushes can land close together. The governor's window leaves one frame of margin for that (N1); a loop that could fall several ticks behind should skip ticks rather than push a burst.
  - Spec 7.6's "logged once per minute with the game name" is the runner's.
  - Neither `apply` promises a new array, so the runner must not keep a reference to a pushed frame across ticks.
  - **Tick budget (N23):** the runner's tick-budget test (spec 9, `ARCADE_TICK_BUDGET_MS`) must include a scenario that keeps the governor on its holding path, such as `claps` at 12 Hz or a strobe, not only static attract frames. It reports the governor's share of the tick.
  - **Juice (spec 8.1):** `Juice.flash` must stay under the governor's budget by itself ("additive and rate-limited"). Add `flash_area(raw) == 0` tests for `shake` and `burst` on a high-contrast frame (N11): a shake whose sign alternates every tick toggles every edge at 15 Hz, and dense burst particles over one spot do the same.
- **it05, IMX500 lux (core Task 19):** `lux` is a callable returning the latest lux metadata or `None`. Until Task 19 the runner passes `None`, and the clock decides.
- **it06, director (core Task 9 superseded):**
  - `to_wall(body, rect)` goes to `arcade/input.py` and `draw_figure(canvas, body, rect, color, stroke=2)` to `arcade/game.py`. They are not here, because their tests are the director's and the mirror's, and the camera aspect they depend on is set by the mirror.
  - Door titles (N21): the 5x7 font at 2x at most, scrolling at 30 px/s at most. Assert `concurrent_area < 0.09` and the governor's `held_ticks == 0` on the real door frames at both layouts. The margins are thin: stroke-heavy text reaches 0.090 concurrent at 2x, and "MMMM WWWW HHHH MMMM" at 2x and 30 px/s flips 13.1% of the 128x32 wall, so the field cap (loop decision 18) holds it for 6 frames.
  - Door dwell decays over 0.3 s.
- **Core Task 13 (`--flash-report`):** print `flash_area(raw_frames, cfg.gamma, fps=cfg.fps)`, `concurrent_area`, `square_flashes`, and the mean of `brightness.apl(frame, cfg.gamma)`.
- **Core Task 16 (tracker):** tune `OneEuro`'s `beta` for 0..1 units against the recorded fixtures (loop decision 7), and smooth `scale` (iteration 3).
- **Core Task 20 (soak):**
  - Assert `flash_area(raw) <= 0.1` under `claps` at 12 Hz, `tempo(180)` and the alternating motion grid (spec 9.2), `concurrent_area(pushed) < SMALL_AREA`, and `square_flashes(pushed) <= BUDGET` (B7).
  - `flash_area(pushed)` can exceed 0.125 (0.19 in the round-3 search), because the field cap is per frame and different pixels spend their over-budget flip in different frames; the soak asserts `flash_area(raw)`, and no bound on `flash_area(pushed)` is claimed (N28).
  - A `pattern` check (Q15): no reversing or oscillating stripes with more than 5 light-dark pairs over more than 25% of the wall, in raw or pushed frames.
- **Game guide (docs, core Task 21 or later; no planned task writes it yet, so the operator places it in the roadmap):**
  - Choose colours with low channels at 0 (iteration 3's verdict).
  - A game's own flash stays under 10% of any 32x32 square, or is held.
  - No reversing or oscillating stripes with more than 5 light-dark pairs over more than 25% of the wall (Q15, BT.1702-3 Guideline 2). Stripes that flow smoothly across, into or out of the wall in one direction are allowed.
  - More than 5 s of flashing near the threshold may be a cumulative risk (BT.1702-3, N22), even under the budget. Keep near-threshold flashing short.
- **GATE B (prototype week):**
  - Time `FlashGovernor.apply` and `BrightnessLimiter.apply` on the Pi 5 at both layouts, on the holding path, and record them against the 20 ms tick (N23).
  - Q16: `THRESHOLD` is 0.1 until then. Measure the wall's white at `brightness` 0.4 (L cd/m²) and re-derive `THRESHOLD = min(0.1, 20 / L)` (N17).
- **Spec revision 4:** Q11's order, Q12's night rule, Q13's small-area rule, Q15's field cap and pattern rule, and B7's square backstop; spec 7.6's "Measured cost 0.2 ms" is the prototype's, and the budget is the tick's (N23); spec 8's "Ship order is the table order" against Q2 (N8); a continuous red weight instead of the 0.8 cliff (N2).
- **Unchanged from the roadmap:** C11 and C17 go with core Task 15. C23 goes with core Tasks 13 and 18.
- **Operator:** when this iteration closes C10 and C18-C20, copy the items above into the roadmap's carried fixes.

## Resolved conflicts

- **The prototype's window.** `FlashLimiter` in `flashguard2.py` holds when the 30 frames before the current one already hold 6. Round 1 of this plan counted the current frame in instead, to let an exact 3 Hz strobe through untouched. The review showed a late tick can then show 7 transitions in under a second (N1), so the prototype's window is adopted: the 3 Hz strobe keeps every flash, one frame late per second. `test_3_flashes_a_second_pass_and_4_do_not` pins it.
- **The prototype's light and red.**
  - The prototype linearises with `(v / 255) ** 2.2`, which is config gamma 1.0. Here the light follows `cfg.gamma` (loop decision 12).
  - The prototype's red test is `r > 0.3 and r > 2.5 (g + b)`. Spec 7.6's rule, red at least 0.8 of `R + G + B` in light with no floor, wins, alongside plain luminance and red excess (B1).
- **Spec 4.3 against spec 7.6 on night.** Spec 4.3 says night begins "at `night_start` or when lux falls below `night_lux`". Spec 7.6 says "decided by IMX500 lux metadata when available, else by the clock". The owner chose 4.3 (Q12): lux only adds night.
- **Spec 4, 7.2 and 8.1 on the tick order.** They put the limiter after the governor. The owner chose governor last (Q11).
- **Spec 7.6's per-pixel rule against Q13.** Spec 7.6 governs every pixel. Q13 exempts small areas, with the fraction in loop decision 16.
- **Spec 7.6's per-pixel rule against B7.** Spec 7.6 holds only a pixel over its own budget, so pixels that take turns can flash an area at full rate. The square backstop also holds pixels within their own budgets when their square's mean would flash past it. It only tightens the spec, so it is the loop's (Q14 applied it); recorded for spec revision 4.
- **Spec 7.6 has no pattern rule (Q15).** BT.1702-3 Guideline 2 has one. The owner chose a content rule (the game guide and a soak `pattern` check) plus the governor's 12.5% field cap (loop decision 18); recorded for spec revision 4.
- **`MENU_ORDER` against Q2's ship order (N8).** `MENU_ORDER` is copyme, pong, paint, quickdraw, dodge, tug, flap, swat, strongman, freeze: spec 8's table, spec 9.7, 04-loop S5 and the core amendment (line 494). Q2's answer orders the builds (Copy Me, Pong, Quick Draw, Dodge, Tug, Flap, Swat, Paint, Strongman, Freeze), and the roadmap holds that. Menu order is the loop's to decide (journaled, never asked), so the menu follows spec 8's table and the builds follow Q2. Spec 8's sentence "Ship order is the table order" is drift for revision 4.
- **Core Task 7, revision 2 against its amendment.** The amendment's interface replaces revision 2's:
  - `GameInfo(name, title, icon, needs)` with 8x8 icons;
  - `GAMES: list`;
  - `Scores(path)` with `best(name)`.

  The amendment says to replace `test_registry_lookup`; `test_discovery_skips_missing_modules` covers `get_game` instead. The `data/` entry the core task adds to `.gitignore` is already there (`/data/`), so `.gitignore` is not touched.
- **Spec 7.1 against 7.2 on runner keys.** Spec 7.1's list lacks `player` and `present`, while spec 7.2 and the amendment include them. `RUNNER_KEYS` has all ten.
- **Spec 7.1 types `scores` as `Scores`.** The amendment gives games a per-game view. `GameScores` has `record(value, margin=0.0)`, `best()` and `last_night()`, so a game's `self.scores.record(value)` works as the spec writes it.
- **The amendment's `Hold(seconds, grace=0.25)`** keeps its default. C10's per-capture grace is what callers pass (loop decision 5).

## Additions beyond the source plans (reviewer: check these on purpose)

- **Task 1:**
  - `look.is_real`, `look.check_settings` and `look.light_lut`;
  - `config.DISTANCE_MIN_SCALE`;
  - six tests appended to `test_canvas.py`, `test_look.py` and `test_config.py`.
- **Task 2:**
  - `capture_grace` and `CAPTURE_GRACE`;
  - the `Cursor` class;
  - `Hold.reset()`, `Hold.fired`, and `Hold.progress` of 1.0 at zero seconds;
  - `Edge.on`, `OneEuro.reset()` and `OneEuro.value`;
  - `EPSILON`, so a 3.0 s hold timed by summed ticks fires at tick 90, not 91, and a dropout of exactly the grace, summed, holds;
  - nine tests beyond the three named ones.
- **Task 3:**
  - `game.KINDS`, `INPUTS`, `LAYOUTS`, `ICON_SIZE`, `reserved(key)`, `NAME` and `LAYOUT`;
  - `scores.night_of`, `ROLLOVER_HOUR` and `REASONS`;
  - the `"previous"` entry in `scores.json`;
  - `GameScores`;
  - `SessionLog.records` for the in-memory log;
  - the tests beyond the amendment's list: frozen, defaults, reserved keys, protocol defaults, record and persist, fsync then rename, corrupt file, last night after a restart, numpy numbers, non-finite values and unwritable files.
- **Task 4:**
  - `flash.FPS`, `THRESHOLD`, `BUDGET`, `RED_SHARE`, `REC709`, `WINDOW`, `SMALL_AREA`, `FIELD_AREA`, `BACKSTOP_PASSES`, `signals`, `largest_share`, `square_means`, `concurrent_area` and `square_flashes`;
  - `FlashGovernor`'s `fps`, `threshold` and `budget` keywords;
  - the governor's square backstop (plan review B7), bounded at `BACKSTOP_PASSES` with a whole-frame fallback, and field cap (Q15);
  - `brightness.apl`, `MIN_FACTOR`, `RELEASE`, `LUX_RELEASE`, `LUX_HOLD_S`, `BrightnessLimiter.factor` and `scaled_ticks`;
  - the tests beyond the amendment's list.

## Review Focus

1. **The runner draws into one canvas array every tick and pushes what the governor returns.**
   - Expected: the governor keeps its own copy of what it showed, so a reused buffer is governed exactly like fresh frames. The governor and the limiter may return the input itself.
   - Tests (Task 4): `test_governor_copes_with_a_reused_buffer`, and the `is` asserts in `test_static_and_moving_sprite_pass_bit_identical`, `test_3_flashes_a_second_pass_and_4_do_not` and `test_frame_under_cap_passes_identical`.
2. **Ordinary motion meets the flash rule:** door titles scrolling, a ball, a fade to black, a game-over hold.
   - Expected: none of these is touched, fine text scrolling at up to 30 px/s included (Q13).
   - Expected: a flicker made of sub-threshold steps, riding the top of a fade, spread over frames, taken in turns by pixels each within budget, made of many small flashes together, or a reversing grating over 12.5% of the wall, is still caught.
   - Tests (Task 4): `test_static_and_moving_sprite_pass_bit_identical` (both layouts), `test_fine_text_scrolling_fast_is_a_small_area_and_passes` and `test_titles_scrolling_pass_under_the_field_cap` (both layouts), `test_transitions_follow_extremes_not_steps`, `test_many_small_flashes_add_up_and_are_held`, `test_a_flash_spread_over_frames_is_held`, `test_pixels_taking_turns_are_held_by_the_square` and `test_a_reversing_grating_is_held_by_the_field_cap` (both layouts).
3. **A festival `data_dir`:** a hand-edited or truncated `scores.json`, a file from a later version, a read-only root or a full disk.
   - Expected: scores never raise into a game.
   - Expected: malformed entries are dropped with one warning, and a failed write keeps the scores in memory.
   - Expected: last night's best survives a restart and a second record tonight.
   - Tests (Task 3): `test_scores_survive_corrupt_file`, `test_scores_ignore_non_finite_values_and_unwritable_files`, `test_scores_last_night_survives_a_restart` and `test_scores_roll_over_at_1600`.
4. **A player holding both hands up, or pointing, under real camera noise (15% keypoint dropout).**
   - Expected: the exit hold completes once, near 3 s.
   - Expected: a raise is one press.
   - Expected: the cursor never jumps to the hanging hand.
   - Tests (Task 2): `test_exit_hold_survives_spec_noise_with_the_capture_grace`, `test_edge_fires_once_per_raise_under_spec_noise` and `test_cursor_keeps_its_hand_through_dropouts`, each over 40 noise seeds.
5. **Settings built in code or read from hand-edited TOML, and numbers computed with numpy:** `None`, a string, a bool, NaN, a list or an out-of-range value for gamma, a cap, `night_lux`, a night time, a preview scale or a brightness level; a numpy score, margin, grace or `abandon_seconds`.
   - Expected: `ValueError` at construction, naming the setting. Never a `TypeError` later, and never a silently wrong picture. A numpy number is a number.
   - Tests: Task 1's `test_settings_that_are_not_numbers_raise_value_error_at_construction`, `test_light_lut_is_the_looks_table_checked` and `test_distance_look_needs_sdl_scale_4`; Task 3's `test_scores_take_numpy_numbers`; Task 4's `test_limiter_rejects_bad_config_and_frames` and `test_governor_rejects_bad_input`.

## Environment facts verified 2026-09-28

- HEAD is `5cf9943`. Since `f07afea` only `docs/superpowers/workflow/` files have changed. The working tree differs only in `docs/superpowers/workflow/` files (`decisions.md`, `roadmap.md`, `state.md` and `evidence/it04/plan-review.md`) and this plan.
- The suite is 224 collected, 224 passed, 0 skipped.
- `.venv` is Python 3.12.13 with numpy 2.5.3, pytest 9.1.1 and pygame 2.6.1.
- `arcade/input.py`, `arcade/game.py`, `arcade/games/`, `arcade/scores.py`, `arcade/flash.py` and `arcade/brightness.py` do not exist.
- `.gitignore` already has `/data/`.
- `pyproject.toml` declares the `perf` marker.
- `arcade.look._light_lut(gamma)` is `lru_cache`d and read-only, and the committed `test_look.py` reads it, so it stays; `look.light_lut` is the checked public name.
- `arcade.config.HHMM` is the `HH:MM` pattern `load_config` uses.
- `ArcadeConfig` is a plain (mutable) dataclass, so `dataclasses.replace` builds test configs.
- `arcade.sensed.MIN_CONF` is 0.3.
- `Body.cursor` measures reach from the wrist's own confident hip, else `hip_mid`, else `shoulder_mid`.
- `arcade.sources.actors` exports `REAL_NOISE`, `TICK`, `Person`, `degrade` and `scene`. `Person(x, id=...)` has `raise_hand(at, seconds=0.5, hand="right")` and `both_hands_up(at, seconds)`.
- Summing `1/30` ninety times gives `2.999999999999999`, and three summed ticks from tick 13 come to `0.10000000000000003`, which is why `EPSILON` exists.
- The C10 numbers in loop decision 5 were measured with `degrade(scene(...), **REAL_NOISE)` on this HEAD.
- Timings on this Mac, idle (spec 7.6 measured 0.2 ms for the prototype; the budget is the tick's, `ARCADE_TICK_BUDGET_MS`, 2.0 ms on the Mac):
  - `FlashGovernor.apply` at 128x32: 0.16 ms median on a static frame and 0.21 ms on random frames (the held path every tick, p95 0.28 ms); at 64x64, 0.17 ms and 0.22-0.23 ms;
  - `BrightnessLimiter.apply`: 0.04 ms;
  - `test_input.py` 2 s, `test_flash.py` 9 s, and the whole suite about 14 s.
- `ruff check --select F` passes on every file this plan writes. `--select E501 --line-length 120` flags only `tests/arcade/test_config.py:95` among them, a committed line this plan copies unchanged (checked again for round 2).
- The whole plan's code was replayed from this file's text in a fresh clone of `5cf9943`, task by task (tests first, then code, then the commit), and every failure and count below was observed.
- Mutations were run with `PYTHONDONTWRITEBYTECODE=1`, each against its task's tests: six sets, 385 mutants in all. (1) The round-1 set, re-run on this revision: of its 168, 36 no longer apply (the code they mutated was rewritten), and all 132 that apply fail. (2) A new set of 141 aimed at this revision's code (Task 1 4, Task 2 9, Task 3 7, Task 4 121: the three signals, the extremes and direction, the window, the squares, both area rules and their boundaries, re-measuring held pixels, the fps, budget and threshold keywords, the measures, release, lux hysteresis, the failing sensor, `is_real` and `MappingProxyType`), including the reviewer's survivors 0-5, 15, 23, 24 and 32. On the first run 17 survived; 15 were observable and now each has an assert (a summed dropout of exactly the grace for `Edge` and `Hold`, which the round-1 test missed by one tick; `float` storage of numpy numbers; a missing parent module; a rise before the first fall; a swing of exactly the threshold; a flash of exactly a tenth of a square; a 7th transition with 6 before it; a mean over a cut square; a small flash beside a large one-time change; square means counted as shown; release never past what the frame needs). (3) An independent agent that had not seen these wrote 54 more against the final code: 24 failed at once, 24 more after the asserts it proposed were added (the red-excess formula, Rec. 709 blue, a red flash spread over frames, the exact-3 Hz spread flash, rounding half up, a cap of 1.0, `HH:MM` matched whole, `captures=0`, progress clamped, `switch=1.0`, a hip at exactly `MIN_CONF`, a name starting with `_`, list rows in an icon, `fx` without the underscore, a non-string `when`, an integer best read back as `float`, `previous` never nested, and a float32 gamma worked in float64). Eight survive, and each is equivalent, with no observable effect: `need <= factor` for `need < factor` and `factor >= 1.0` for `factor == 1.0` (the factor never exceeds 1.0 and equal values give the same result); `level < cap` for `level <= cap` (at equality `cap / level` is 1.0 anyway); `start <= end` for `start < end` (equal times give an empty window either way); the bool check on `fps` (True is 1, under 2, and rejected anyway); `is_real`'s `np.bool_` check (`np.bool_` is not a `numbers.Real`); `_Transitions` not copying its first frame (no array is changed in place); and the governor's first-frame `_shown` (nothing can be held on the second frame, whose end overwrites it). (4) Round 2: 14 mutants against the square backstop, the field cap and the three measures' keywords (N18). 13 fail. Two of those first failed by never finishing: advancing the trackers on the input instead of the shown signals, and a dilation that misses a bad square's edge, each left the backstop's loop unable to end. Re-run on the bounded loop, the set's 13 governor mutants give the same verdicts and none hangs: the first now fails at once and the dilation fails the turn-taking test's whole-frame assert. One survives and is equivalent: skipping the backstop's `np.where` when nothing is held. (5) The bound: 5 mutants (one pass instead of 8, `BACKSTOP_PASSES = 3`, a fallback that holds nothing, a fallback that asks the square tracker for its flips again, a log on every fallback), and all 5 fail. (6) Round 3: the reviewer's 3 survivors (N25, N26): a fallback that keeps the last pass's square flips, a fallback that advances the trackers on the input's signals instead of what was shown, and a small-flash condition without the square flag. All 3 passed the 41 tests before the round-3 asserts, and each fails now.

## File map

```
arcade/canvas.py                Task 1  C18: _i clamps Python ints; circle draws its centre at tiny radii; docstring
arcade/look.py                  Task 1  C19 apply_gamma copies; C20 is_real, check_settings, dim raises; light_lut
arcade/preview.py               Task 1  C20 settings checked at construction, set_brightness checks its level
arcade/config.py                Task 1  C20 DISTANCE_MIN_SCALE; distance look needs sdl_scale 4
tests/arcade/test_canvas.py     Task 1  two tests appended
tests/arcade/test_look.py       Task 1  three tests appended
tests/arcade/test_config.py     Task 1  one test appended
arcade/input.py                 Task 2  new: capture_grace, Edge, Hold, Cursor, OneEuro
tests/arcade/test_input.py      Task 2  new
arcade/game.py                  Task 3  new: GameInfo, Game, RUNNER_KEYS, reserved, icon_from_rows
arcade/games/__init__.py        Task 3  new: MENU_ORDER, all_games, get_game
arcade/scores.py                Task 3  new: night_of, Scores, GameScores, SessionLog
tests/arcade/test_game.py       Task 3  new
tests/arcade/test_scores.py     Task 3  new
arcade/flash.py                 Task 4  new: signals, squares, FlashGovernor (square backstop, field cap), flash_area, concurrent_area, square_flashes
arcade/brightness.py            Task 4  new: apl, BrightnessLimiter
tests/arcade/test_flash.py      Task 4  new
tests/arcade/test_brightness.py Task 4  new
```

---

### Task 1: Carried preview and canvas fixes (C18, C19, C20)

**Files:**
- Modify: `arcade/canvas.py`, `arcade/look.py`, `arcade/preview.py`, `arcade/config.py` (whole files below)
- Test: `tests/arcade/test_canvas.py`, `tests/arcade/test_look.py`, `tests/arcade/test_config.py` (whole files below)

**Interfaces:**
- Consumes: iteration 3's `Canvas`, `render`, `dim`, `apply_gamma`, `PreviewDisplay` and `load_config`.
- Produces:
  - `look.is_real(v) -> bool`.
  - `look.check_settings(mode: str, scale: int, gamma: float, metres: float = 5.0) -> int`, which raises `ValueError`.
  - `look.dim(image, level)` raises `ValueError` when `level` is not a real number.
  - `look.apply_gamma(frame, gamma)` always returns a new array.
  - `look.light_lut(gamma) -> np.ndarray`, the looks' read-only (256,) float32 light table, the same object as `look._light_lut(float(gamma))`. A gamma that is not a finite real number over 0 raises `ValueError`.
  - `PreviewDisplay(inner, mode, scale, gamma, metres=5.0)` raises `ValueError` at construction for bad settings, and its `scale` is an `int`. `PreviewDisplay.set_brightness(level)` raises `ValueError` for a non-number and neither stores nor forwards it.
  - `config.DISTANCE_MIN_SCALE = 4`. `load_config` raises `ValueError` (message names `sdl_scale`) for `look = "distance"` with `sdl_scale` under 4.
  - `Canvas.circle` at a radius that rounds to 0 or lands at `-_FAR` draws the centre pixel. `_i(10**400) == _FAR`.

  No name or signature is removed.

Changes to existing test lines: none. Six tests are appended at the ends of the three modules. The new look tests reach `look.check_settings`, `look.dim` and `look.light_lut` through the module (`import arcade.look as look` is already imported), so the import lines are unchanged and each new test fails on its own rather than at collection.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_canvas.py`:

```python
import contextlib
import math
import signal
import threading
import time
import warnings

import numpy as np
import pytest

from arcade.canvas import Canvas, sprite_from_rows

RED = (255, 0, 0)


def lit(c: Canvas) -> int:
    return int((c.frame.max(axis=2) > 0).sum())


@contextlib.contextmanager
def deadline(seconds: float):
    """Fails a block that runs past seconds instead of hanging the suite (05-plan S4's infinite line).

    It replaces any outer SIGALRM timer while it runs. Off the main thread, or where there is no setitimer
    (Windows), it just runs the block."""
    if threading.current_thread() is not threading.main_thread() or not hasattr(signal, "setitimer"):
        yield
        return
    def expired(signum, frame):
        raise TimeoutError(f"still running after {seconds} s")
    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def test_new_canvas_is_black_and_sized(font5x7, size):
    c = Canvas(*size, font5x7)
    assert c.frame.shape == (size[1], size[0], 3) and c.frame.dtype == np.uint8
    assert c.size == size and lit(c) == 0


def test_pixel_and_clipping(font5x7):
    c = Canvas(16, 8, font5x7)
    c.pixel(3, 2, RED)
    c.pixel(-1, 0, RED)
    c.pixel(16, 8, RED)
    assert lit(c) == 1 and tuple(c.frame[2, 3]) == RED


def test_rects_and_clear(font5x7):
    c = Canvas(16, 8, font5x7)
    c.fill_rect(2, 1, 4, 3, RED)
    assert lit(c) == 12
    c.clear()
    c.rect(0, 0, 16, 8, RED)
    assert lit(c) == 2 * 16 + 2 * 6
    c.fill_rect(10, 4, 100, 100, RED)
    assert lit(c) == 2 * 16 + 2 * 6 + (6 * 4 - 6 - 3)


def test_line_and_circles(font5x7):
    c = Canvas(16, 16, font5x7)
    c.line(0, 0, 15, 15, RED)
    assert lit(c) == 16 and tuple(c.frame[7, 7]) == RED
    c.clear()
    c.fill_circle(8, 8, 3, RED)
    n_fill = lit(c)
    assert 25 <= n_fill <= 37 and tuple(c.frame[8, 8]) == RED
    c.clear()
    c.circle(8, 8, 3, RED)
    assert 12 <= lit(c) < n_fill and tuple(c.frame[8, 8]) == (0, 0, 0)
    c.circle(0, 0, 40, RED)


def test_text_uses_font_and_clips(font5x7):
    c = Canvas(32, 8, font5x7)
    assert c.text_width("AB") == 12
    w = c.text(0, 0, "A", RED)
    assert w == 6 and lit(c) > 5
    a = c.frame.copy()
    c.clear()
    c.text(30, 0, "A", RED)
    assert lit(c) < lit_of(a)
    c.clear()
    c.text(0, 0, "☃", RED)
    assert lit(c) > 0


def lit_of(frame: np.ndarray) -> int:
    return int((frame.max(axis=2) > 0).sum())


def test_float_coordinates_round(font5x7):
    c = Canvas(16, 8, font5x7)
    c.pixel(2.5, 0.5, RED)                          # half rounds up: a 0.5 px step moves every tick
    c.pixel(np.float32(5.4), np.int64(3), RED)
    assert tuple(c.frame[1, 3]) == RED and tuple(c.frame[3, 5]) == RED and lit(c) == 2
    c.clear()
    c.fill_rect(1.2, 1.2, 2.6, 2.6, RED)            # x 1, y 1, 3 by 3
    assert lit(c) == 9 and c.frame[1:4, 1:4, 0].all()
    c.clear()
    c.fill_circle(8.4, 4.4, 1.6, RED)               # centre (8, 4), radius 2
    assert tuple(c.frame[4, 8]) == RED and tuple(c.frame[4, 10]) == RED and tuple(c.frame[4, 11]) == (0, 0, 0)
    c.clear()
    c.blit(np.ones((2, 2), bool), 0.6, 0.4, RED)    # at (1, 0)
    c.text(9.5, 0.2, "I", RED)                      # at (10, 0)
    assert c.frame[0:2, 1:3, 0].all() and not c.frame[:, 0].any() and c.frame[:, 10:16].any()
    c.clear()
    c.text(0, 0.5, "I", RED)                        # at (0, 1): text rounds as pixel does
    one = Canvas(16, 8, font5x7)
    one.text(0, 1, "I", RED)
    assert np.array_equal(c.frame, one.frame)
    c.clear()
    c.text(-1, 0, "B", RED)                         # scrolling in from the left: B's four visible columns
    b = Canvas(16, 8, font5x7)
    b.text(5, 0, "B", RED)
    assert c.frame[:, 0:4].any() and np.array_equal(c.frame[:, 0:4], b.frame[:, 6:10])


def test_nan_inf_and_huge_never_raise_or_hang(font5x7):
    c = Canvas(64, 32, font5x7)
    nan, inf = math.nan, math.inf
    sprite = np.full((4, 4, 3), 200, np.uint8)
    c.text(0, 0, "A", RED)                          # build the font atlas before timing
    calls = [
        lambda: c.pixel(nan, 3, RED), lambda: c.pixel(inf, -inf, RED), lambda: c.pixel(10**12, 5, RED),
        lambda: c.pixel(None, "x", RED), lambda: c.pixel(10**400, 0, RED),
        lambda: c.line(0, 0, nan, 5, RED), lambda: c.line(0, 0, 10**9, 0, RED),
        lambda: c.line(-inf, 0, inf, 0, RED), lambda: c.line(0, 0, 1e300, -1e300, RED),
        lambda: c.fill_rect(nan, 0, 5, 5, RED), lambda: c.fill_rect(0, 0, 10**9, 10**9, RED),
        lambda: c.rect(nan, nan, nan, nan, RED), lambda: c.rect(-10**9, -10**9, 2 * 10**9, 2 * 10**9, RED),
        lambda: c.circle(5, 5, 10**9, RED), lambda: c.fill_circle(nan, nan, 3, RED),
        lambda: c.fill_circle(5, 5, inf, RED), lambda: c.fill_circle(10**9, 10**9, 10**9, RED),
        lambda: c.fill_circle(5, 5, 1e200, RED),       # (r + 0.5) ** 2 overflows a float unless _i clamps
        lambda: c.blit(np.ones((3, 3), bool), nan, 0, RED), lambda: c.blit_rgb(sprite, inf, 0),
        lambda: c.blit_rgb(sprite, -10**9, 10**9),
        lambda: c.text(nan, 0, "HI", RED), lambda: c.text(0, 0, "HI", RED, scale=10**9),
        lambda: c.text(0, 0, "X" * 10000, RED, scale=2), lambda: c.text(-10**6, 0, "X" * 10000, RED),
        lambda: c.text(0, inf, "HI", RED, scale=nan),
    ]
    for i, call in enumerate(calls):
        start = time.perf_counter()
        with deadline(1.0):
            call()
        assert time.perf_counter() - start < 0.05, f"call {i} took too long"
    assert c.frame.shape == (32, 64, 3) and c.frame.dtype == np.uint8
    e = Canvas(16, 8, font5x7)
    e.rect(3, 0, 0, 4, RED)                         # a health bar at width 0 draws nothing
    e.rect(10, 0, -3, 4, RED)
    e.fill_rect(0, 0, inf, 4, RED)                  # an infinite width lands at -_FAR: nothing
    assert lit(e) == 0


def test_colours_clamped(font5x7):
    c = Canvas(16, 8, font5x7)
    c.pixel(0, 0, (300, -5, 127.6))
    assert tuple(c.frame[0, 0]) == (255, 0, 128)
    c.fill_rect(1, 0, 1, 1, (math.nan, math.inf, -math.inf))
    assert tuple(c.frame[0, 1]) == (0, 255, 0)
    c.line(0, 2, 3, 2, (np.int64(999), np.float32(-1), 7))
    assert tuple(c.frame[2, 3]) == (255, 0, 7)
    c.text(0, 3, "I", (999, 0, 0))
    assert c.frame[3:8, :, 0].max() == 255
    c.clear((256, 256, 256))
    assert (c.frame == 255).all()
    c.clear()
    with warnings.catch_warnings():
        warnings.simplefilter("error")              # a NaN never reaches a byte cast
        c.blit_rgb(np.array([[[300.0, 127.6, 0.4], [np.nan, 0, 0], [-5, 0, 0], [np.inf, 0, 0]]], np.float32), 0, 5)
        c.blit_rgb(np.array([[[300, 0, 0], [-1, 0, 0]]], np.int64), 0, 6)
        c.blit_rgb(np.array([[[0.5, 126.5, 2.5]]], np.float32), 0, 7)
    assert [tuple(p) for p in c.frame[5, :4]] == [(255, 128, 0), (0, 0, 0), (0, 0, 0), (255, 0, 0)]
    assert [tuple(p) for p in c.frame[6, :2]] == [(255, 0, 0), (0, 0, 0)]   # a paint buffer clamps, never wraps
    assert tuple(c.frame[7, 0]) == (1, 127, 3)                               # half up, as coordinates round


def test_line_with_float_endpoint_terminates(font5x7):
    c = Canvas(16, 8, font5x7)
    start = time.perf_counter()
    with deadline(1.0):
        c.line(0, 0, 10.5, 0, RED)                  # used to step past 10.5 forever
    assert time.perf_counter() - start < 0.05
    assert lit(c) == 12 and c.frame[0, :12, 0].all()
    c.clear()
    c.line(0.4, 0.6, 7.6, 3.4, RED)                 # (0, 1) to (8, 3)
    assert tuple(c.frame[1, 0]) == RED and tuple(c.frame[3, 8]) == RED and lit(c) == 9


def test_text_scale_two(font5x7):
    c = Canvas(32, 16, font5x7)
    assert c.text_width("8", scale=2) == 12 and c.text_width("88", scale=2) == 24
    one = Canvas(32, 16, font5x7)
    one.text(0, 0, "8", RED)
    assert c.text(0, 0, "8", RED, scale=2) == 12
    assert lit(c) == 4 * lit(one)
    big, small = c.frame[:16, :12, 0] > 0, one.frame[:8, :6, 0] > 0
    assert np.array_equal(big, small.repeat(2, axis=0).repeat(2, axis=1))    # 2 px strokes
    rows, cols = np.nonzero(c.frame[:, :, 0])
    assert rows.max() - rows.min() + 1 == 14 and cols.max() - cols.min() + 1 == 10   # the 5x7 glyph at 10x14
    num = Canvas(32, 16, font5x7)
    assert num.text(0, 0, 8, RED, scale=2) == 12 and np.array_equal(num.frame, c.frame)   # numbers are drawn as str


def test_blit_rgb_black_is_transparent(font5x7):
    c = Canvas(8, 8, font5x7)
    c.clear((0, 0, 255))
    sprite = np.array([[[255, 0, 0], [0, 0, 0]], [[0, 0, 0], [0, 255, 0]]], np.uint8)
    c.blit_rgb(sprite, 1, 1)
    assert tuple(c.frame[1, 1]) == (255, 0, 0) and tuple(c.frame[2, 2]) == (0, 255, 0)
    assert tuple(c.frame[1, 2]) == (0, 0, 255) and tuple(c.frame[2, 1]) == (0, 0, 255)   # black showed through
    c.clear()
    c.blit_rgb(sprite, -1, 6.6)                     # at (-1, 7): only the black top-right cell is on-canvas
    c.blit_rgb(sprite, 6.5, -1)                     # at (7, -1): only the black bottom-left cell is on-canvas
    assert lit(c) == 0
    c.blit_rgb(sprite, 7, 7)
    assert lit(c) == 1 and tuple(c.frame[7, 7]) == (255, 0, 0)


def test_sprite_from_rows_palette():
    s = sprite_from_rows(["R.", ".G"], {"R": (255, 0, 0), "G": (0, 300, 0)})
    assert s.shape == (2, 2, 3) and s.dtype == np.uint8
    assert tuple(s[0, 0]) == (255, 0, 0) and tuple(s[1, 1]) == (0, 255, 0)            # clamped
    assert tuple(s[0, 1]) == (0, 0, 0) and tuple(s[1, 0]) == (0, 0, 0)
    assert sprite_from_rows([".R"], {".": (9, 9, 9), "R": RED})[0, 0].sum() == 0       # "." is always black
    with pytest.raises(ValueError, match="'X'"):
        sprite_from_rows(["RX"], {"R": RED})
    with pytest.raises(ValueError, match="length"):
        sprite_from_rows(["RR", "R"], {"R": RED})
    assert np.array_equal(Canvas.sprite_from_rows(["R"], {"R": RED}), sprite_from_rows(["R"], {"R": RED}))


def test_circle_is_the_one_pixel_rim_of_fill_circle(font5x7):
    for r in (1, 3, 6):
        ring, inner, disc = (Canvas(16, 16, font5x7) for _ in range(3))
        ring.circle(8, 8, r, RED)
        inner.fill_circle(8, 8, r - 1, RED)
        disc.fill_circle(8, 8, r, RED)
        rim, core, whole = (c.frame[:, :, 0] > 0 for c in (ring, inner, disc))
        assert not (rim & core).any() and np.array_equal(rim | core, whole), r


def test_blit_takes_any_mask_as_bool(font5x7):
    c = Canvas(8, 4, font5x7)
    c.blit(np.array([[1, 0], [0, 1]], np.uint8), 3, 0, RED)   # an int mask is a mask, not row indices
    assert lit(c) == 2 and tuple(c.frame[0, 3]) == RED and tuple(c.frame[1, 4]) == RED


def test_line_skip_starts_past_four_times_the_extent(font5x7):
    # Spec 7.4: a line whose endpoints exceed four times the canvas extent is skipped.
    c = Canvas(16, 8, font5x7)
    reach = 4 * (16 + 8)
    c.line(0, 0, reach, 0, RED)
    assert c.frame[0, :, 0].all()
    c.clear()
    c.line(0, 0, reach + 1, 0, RED)
    c.line(0, -reach - 1, 0, 7, RED)
    assert lit(c) == 0


@pytest.mark.parametrize("w,h", [(64, 32), (96, 48), (128, 64)])
def test_other_wall_sizes_draw_and_clip(font5x7, w, h):
    # Core Review Focus 3: a single panel at bring-up (64x32), or a wall of another size from config.
    c = Canvas(w, h, font5x7)
    c.text(w - 10, h - 8, "88", RED, scale=2)
    c.fill_circle(w - 1, h - 1, 5, RED)
    c.line(-5, h // 2, w + 5, h // 2, RED)
    c.rect(-1, -1, w + 2, h + 2, RED)
    c.blit_rgb(np.full((5, 5, 3), 90, np.uint8), w - 2, -2)
    assert c.frame.shape == (h, w, 3) and c.frame[h // 2, :, 0].all()
    assert c.text_width("88", scale=2) == 24 and lit(c) > w


def test_tiny_negative_and_non_finite_radii_draw_the_centre_as_fill_circle_does(font5x7):
    # C18: a ring whose radius rounds to 0 or lands at -_FAR (negative, infinite, NaN, not a number) is its
    # centre pixel, as the disc is; it used to draw nothing while fill_circle drew the centre.
    for r in (0, 0.25, 0.49, -2, -math.inf, math.inf, math.nan, None):
        ring, disc = Canvas(16, 16, font5x7), Canvas(16, 16, font5x7)
        ring.circle(8, 8, r, RED)
        disc.fill_circle(8, 8, r, RED)
        assert lit(ring) == 1 and tuple(ring.frame[8, 8]) == RED, r
        assert np.array_equal(ring.frame, disc.frame), r
    c = Canvas(16, 16, font5x7)
    c.circle(8, 8, 0.5, RED)                        # rounds half up to 1: the eight neighbours, not the centre
    assert lit(c) == 8 and not c.frame[8, 8].any()


def test_huge_python_ints_clamp_like_huge_floats(font5x7):
    # C18: 10**400 has no float, so it used to land at -_FAR: a radius drew 1 px where 1e300 fills.
    draws = [lambda c, v: c.fill_circle(5, 5, v, RED), lambda c, v: c.fill_rect(0, 0, v, 4, RED),
             lambda c, v: c.text(0, 0, "H", RED, scale=v), lambda c, v: c.pixel(v, 0, RED),
             lambda c, v: c.pixel(-v, 0, RED), lambda c, v: c.circle(5, 5, v, RED)]
    lights = []
    for draw in draws:
        huge, big = Canvas(16, 8, font5x7), Canvas(16, 8, font5x7)
        with deadline(1.0):
            draw(huge, 10**400)
            draw(big, 1e300)
        assert np.array_equal(huge.frame, big.frame)
        lights.append(lit(huge))
    assert lights == [128, 64, 128, 0, 0, 0]       # a disc and a rect fill, one glyph pixel fills, a ring is off
```

`tests/arcade/test_look.py`:

```python
import math
import statistics
import subprocess
import sys
import time
import warnings
import zlib
from pathlib import Path

import numpy as np
import pytest

import arcade.look as look
from arcade.config import LOOKS
from arcade.look import MODES, apply_gamma, distance_sigma, gamma_lut, render
from arcade.preview import PreviewDisplay
from show.display.fake import FakeDisplay

ROOT = Path(__file__).resolve().parents[2]


def frame_with_dot(w=8, h=4):
    f = np.zeros((h, w, 3), np.uint8)
    f[1, 2] = (128, 0, 0)
    return f


def test_gamma_lut_brightens_midtones_and_identity_at_one():
    lut = gamma_lut(2.2)
    assert lut[0] == 0 and lut[255] == 255 and lut[128] > 128
    assert np.array_equal(gamma_lut(1.0), np.arange(256, dtype=np.uint8))
    f = frame_with_dot()
    assert apply_gamma(f, 2.2)[1, 2, 0] == lut[128]


def test_plain_is_nearest_neighbour():
    out = render(frame_with_dot(), "plain", scale=4, gamma=2.2)
    assert out.shape == (16, 32, 3)
    assert (out[4:8, 8:12, 0] == 128).all() and out[0, 0].sum() == 0


def test_led_draws_round_dots_with_dark_gaps():
    out = render(frame_with_dot(), "led", scale=8, gamma=1.0)
    cell = out[8:16, 16:24, 0]
    assert cell[4, 4] == 128
    assert cell[0, 0] == 0 and cell[0, 7] == 0
    assert 0 < (cell > 0).sum() < 64
    assert out[0:8, 0:8].sum() == 0


def test_distance_blurs():
    out = render(frame_with_dot(), "distance", scale=8, gamma=1.0, metres=5.0)
    assert out.shape == (32, 64, 3)
    assert out[12, 20, 0] > 0 and out[12, 20, 0] < 128
    assert out[9, 13, 0] > 0


def test_unknown_mode_rejected():
    with pytest.raises(ValueError):
        render(frame_with_dot(), "crt")


def test_preview_display_renders_before_push():
    inner = FakeDisplay()
    d = PreviewDisplay(inner, "plain", scale=2, gamma=1.0)
    d.push(frame_with_dot())
    assert inner.last.shape == (8, 16, 3)
    d.set_brightness(0.3)
    assert inner.brightness == 0.3
    d.close()
    assert inner.closed


def spread(out: np.ndarray) -> float:
    """Root-mean-square distance of the red light from its centre, in preview pixels."""
    light = (out[:, :, 0] / 255.0) ** 2.2
    yy, xx = np.mgrid[0:out.shape[0], 0:out.shape[1]]
    cy, cx = (light * yy).sum() / light.sum(), (light * xx).sum() / light.sum()
    return math.sqrt((light * ((yy - cy) ** 2 + (xx - cx) ** 2)).sum() / light.sum())


def test_distance_blur_grows_with_metres():
    f = np.zeros((9, 16, 3), np.uint8)
    f[4, 8] = (255, 0, 0)
    near, mid, far = (spread(render(f, "distance", scale=8, gamma=2.2, metres=m)) for m in (2.0, 5.0, 10.0))
    assert near < mid < far and far > 1.5 * near
    assert distance_sigma(5.0) == pytest.approx(5.0 * math.tan(math.radians(1.5 / 60)) / 0.005)
    assert distance_sigma(5.0) == pytest.approx(0.436, abs=1e-3)   # 1.5 arcmin at 5 m is under half a P5 pixel
    sharp = render(f, "distance", scale=8, gamma=2.2, metres=0.0)
    assert (sharp[:, :, 0] > 0).sum() == 64                          # at 0 m nothing spreads past the LED
    start = time.perf_counter()
    assert render(f, "distance", scale=8, gamma=2.2, metres=1e300).max() == 0   # too far to see: no overflow
    assert time.perf_counter() - start < 0.5                                     # and no giant blur buffers


def test_distance_halation_follows_luminance():
    # 16 preview px (2 wall px) from a lit pixel the 5 m blur has died out; only the halation glow is left,
    # and it follows luminance: a green pixel glows further than an equally bright blue one.
    def far_glow(color, channel):
        f = np.zeros((5, 16, 3), np.uint8)
        f[2, 2] = color
        return int(render(f, "distance", scale=8, gamma=2.2, metres=5.0)[20, 36, channel])

    green, blue, white = far_glow((0, 255, 0), 1), far_glow((0, 0, 255), 2), far_glow((255, 255, 255), 0)
    assert blue > 0 and green > 2 * blue and white >= green
    f = np.zeros((5, 16, 3), np.uint8)
    f[2, 2] = (0, 255, 0)
    assert render(f, "distance", scale=8, gamma=2.2, metres=5.0)[20, 60].sum() == 0   # 5 wall px: dark
    assert render(np.zeros((32, 128, 3), np.uint8), "distance").sum() == 0



def test_distance_conserves_light_and_keeps_strokes_apart():
    # The glow redistributes light, never adds it: a flat field keeps the led look's level at any distance.
    for color in ((128, 128, 128), (255, 200, 0), (60, 60, 60)):
        flat = np.full((32, 128, 3), color, np.uint8)
        for metres in (0.0, 5.0, 10.0):
            inner = render(flat, "distance", scale=8, gamma=2.2, metres=metres)[128, 512]
            assert np.abs(inner.astype(int) - gamma_lut(2.2)[list(color)]).max() <= 1, (color, metres)
    # Spec 7.4: 1 px strokes read at 5 m and scale-2 text (2 px strokes) to about 10 m, so the gap between
    # two strokes stays darker than the strokes. This bounds HALATION (0.5 passes, 0.6 fails).
    one = np.zeros((9, 16, 3), np.uint8)
    one[:, 6] = one[:, 8] = 255                                      # 1 px strokes, 1 px gap
    two = np.zeros((9, 20, 3), np.uint8)
    two[:, 6:8] = two[:, 10:12] = 255                                # 2 px strokes and gap
    near = render(one, "distance", scale=8, gamma=2.2, metres=5.0)[36, :, 0]
    far = render(two, "distance", scale=8, gamma=2.2, metres=10.0)[36, :, 0]
    assert near[60] < 0.85 * near[52] and far[72] < 0.85 * far[56]   # the gap stays darker


def test_distance_blur_has_its_width_and_dark_edges(monkeypatch):
    # One lit white wall pixel spreads as a Gaussian convolved with the 8 px square: per axis, variance
    # sigma**2 + (scale**2 - 1) / 12 in preview pixels. With no glow that sigma is the eye's blur; with
    # all of white's light scattered it is the glow's, three times wider (the amendment's 3 sigma).
    for halation, widths in ((0.0, 1.0), (1.0, 3.0)):
        monkeypatch.setattr(look, "HALATION", halation)
        for metres in (5.0, 10.0):
            f = np.zeros((9, 71, 3), np.uint8)
            f[4, 35] = 255
            light = (render(f, "distance", scale=8, gamma=2.2, metres=metres)[:, :, 0] / 255.0) ** 2.2
            col, x = light.sum(axis=0), np.arange(71 * 8)
            centre = (col * x).sum() / col.sum()
            variance = (col * (x - centre) ** 2).sum() / col.sum()
            expected = (widths * distance_sigma(metres) * 8) ** 2 + (8 ** 2 - 1) / 12
            assert variance == pytest.approx(expected, rel=0.1), (halation, metres)
    monkeypatch.setattr(look, "HALATION", 0.0)
    white = render(np.full((32, 128, 3), 255, np.uint8), "distance", scale=8, gamma=2.2, metres=5.0)
    assert white[0, 0, 0] < white[0, 512, 0] < white[128, 512, 0] == 255   # the air beside the wall is dark


def test_led_honours_gamma_and_cached_tables_are_read_only():
    assert render(frame_with_dot(), "led", scale=8, gamma=2.2)[12, 20, 0] == gamma_lut(2.2)[128]
    lut = gamma_lut(2.2)
    assert not lut.flags.writeable
    with pytest.raises(ValueError):
        lut[128] = 0                                                 # would corrupt every later preview
    render(frame_with_dot(), "distance", scale=8)
    assert not any(a.flags.writeable for a in (look._led_kernel(8), look._light_lut(2.2), look._spread(4, 8, 3.5)))


@pytest.mark.perf
def test_distance_keeps_up_with_the_preview():
    # look = "distance" renders every tick of an SDL run, and the preview dims it: a 128x32 wall at scale 8
    # must fit in a 30 Hz tick.
    seed = zlib.crc32(b"distance-perf")
    f = np.random.default_rng(seed).integers(0, 256, (32, 128, 3), dtype=np.uint8)
    d = PreviewDisplay(FakeDisplay(), "distance", scale=8, gamma=2.2)
    d.set_brightness(0.4)
    d.push(f)                                                        # builds the cached blur matrices
    times = []
    for _ in range(5):
        start = time.perf_counter()
        d.push(f)
        times.append(time.perf_counter() - start)
    assert statistics.median(times) < 1 / 30, f"median {statistics.median(times) * 1000:.1f} ms, seed={seed}"


def test_render_rejects_bad_input():
    good = frame_with_dot()
    bad = [
        dict(frame=good.astype(np.float32)), dict(frame=good[:, :, 0]), dict(frame=good[:, :, :2]),
        dict(scale=0), dict(scale=2.5), dict(scale=True), dict(scale=np.float64(2.0)), dict(scale=np.int64(0)),
        dict(gamma=0.0), dict(gamma=math.nan),
        dict(gamma=math.inf), dict(metres=-1.0), dict(metres=math.nan), dict(metres=math.inf),
    ]
    for case in bad:
        args = dict(frame=good, mode="distance", scale=2, gamma=2.2, metres=5.0) | case
        with pytest.raises(ValueError):
            render(**args)
    assert MODES == LOOKS                                            # every configurable look renders
    for mode in MODES:                                               # a computed numpy scale is an int
        assert render(good, mode, scale=np.int64(2)).shape == (8, 16, 3)


def test_look_never_imports_cv2():
    code = "import sys, arcade.look, arcade.preview; print(sorted({'cv2', 'pygame'} & set(sys.modules)))"
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "[]"


def test_preview_models_brightness():
    inner = FakeDisplay()
    d = PreviewDisplay(inner, "plain", scale=1, gamma=1.0)
    wall = np.full((4, 8, 3), 255, np.uint8)
    d.push(wall)
    assert (inner.last == 255).all()                                 # full brightness until told otherwise
    d.set_brightness(0.25)
    d.push(wall)
    assert inner.brightness == 0.25 and (wall == 255).all()          # the wall frame itself is never scaled
    assert (inner.last == round(255 * 0.25 ** (1 / 2.2))).all()      # 136: the monitor shows a quarter of the light
    assert np.allclose((inner.last / 255.0) ** 2.2, 0.25, atol=0.01)
    with warnings.catch_warnings():
        warnings.simplefilter("error")                               # a NaN level never reaches the byte cast
        for level, expect in ((0.0, 0), (-1.0, 0), (math.nan, 0), (1.0, 255), (1.5, 255)):
            d.set_brightness(level)
            d.push(wall)
            assert (inner.last == expect).all(), level
    assert inner.brightness == 1.5                                   # forwarded unchanged, even above 1
    far = PreviewDisplay(FakeDisplay(), "distance", scale=4, gamma=2.2, metres=10.0)
    far.push(frame_with_dot())
    assert np.array_equal(far.inner.last, render(frame_with_dot(), "distance", scale=4, gamma=2.2, metres=10.0))


def test_apply_gamma_at_one_returns_a_copy():
    # C19: the led look and later callers (core Task 11) may write into the result.
    f = frame_with_dot()
    for gamma in (1.0, 2.2):
        out = apply_gamma(f, gamma)
        assert out is not f and not np.shares_memory(out, f) and out.dtype == np.uint8, gamma
        out[1, 2] = 0
        assert f[1, 2, 0] == 128, gamma                              # the caller's frame is untouched
    assert np.array_equal(apply_gamma(f, 1.0), f)


def test_settings_that_are_not_numbers_raise_value_error_at_construction():
    # C20: None, a string or a bool is a ValueError like any other bad setting, and PreviewDisplay checks its
    # settings when it is built, not on the first push.
    good = frame_with_dot()
    for case in (dict(gamma=None), dict(metres=None), dict(gamma="2.2"), dict(metres="5"), dict(gamma=True)):
        args = dict(mode="distance", scale=4, gamma=2.2, metres=5.0) | case
        with pytest.raises(ValueError):
            render(good, **args)
        with pytest.raises(ValueError):
            PreviewDisplay(FakeDisplay(), **args)
    for case in (dict(mode="crt"), dict(scale=0), dict(scale=2.0), dict(gamma=0.0), dict(metres=-1.0)):
        with pytest.raises(ValueError):
            PreviewDisplay(FakeDisplay(), **(dict(mode="led", scale=4, gamma=2.2, metres=5.0) | case))
    assert look.check_settings("led", np.int64(3), np.float64(2.2), 0) == 3
    assert type(look.check_settings("led", np.int64(3), 1.0)) is int
    assert type(PreviewDisplay(FakeDisplay(), "plain", np.int64(2), 1.0).scale) is int
    image = np.full((2, 2, 3), 200, np.uint8)
    for level in (None, "0.5", True):
        with pytest.raises(ValueError):
            look.dim(image, level)
    assert look.dim(image, math.nan).sum() == 0 and look.dim(image, 0).sum() == 0   # NaN and 0 are still black
    inner = FakeDisplay()
    d = PreviewDisplay(inner, "plain", scale=1, gamma=1.0)
    d.set_brightness(0.5)
    with pytest.raises(ValueError):
        d.set_brightness(None)
    assert d.level == 0.5 and inner.brightness == 0.5                         # neither kept nor forwarded


def test_light_lut_is_the_looks_table_checked():
    # The flash governor and the brightness limiter read the looks' own light table through this public name.
    assert look.light_lut(2.2) is look._light_lut(2.2) and look.light_lut(np.float32(1.0)) is look._light_lut(1.0)
    assert look.light_lut(2)[255] == 1.0 and not look.light_lut(1.8).flags.writeable
    gamma = np.float32(1.7)                                          # worked in float64, as the float it equals
    v = np.arange(256) / 255.0
    assert np.array_equal(look.light_lut(gamma), (v ** (look.MONITOR_GAMMA / float(gamma))).astype(np.float32))
    for bad in (0.0, -1.0, math.nan, math.inf, None, True, "2.2"):
        with pytest.raises(ValueError):
            look.light_lut(bad)
```

`tests/arcade/test_config.py`:

```python
import dataclasses
import tomllib
from pathlib import Path

import pytest

from arcade.config import ArcadeConfig, load_config

REPO_TOML = Path(__file__).resolve().parents[2] / "arcade.toml"


def write(tmp_path, text):
    p = tmp_path / "arcade.toml"
    p.write_text(text + "\n")
    return p


def test_defaults_when_file_missing(tmp_path):
    cfg = load_config(tmp_path / "nope.toml")
    assert cfg.size == (128, 32)
    assert cfg.backend == "sdl" and cfg.sdl_scale == 8 and cfg.iface == "eth0"
    assert (cfg.ddp_host, cfg.ddp_port) == ("127.0.0.1", 4048)
    assert cfg.camera == "mediapipe" and cfg.camera_index == 0 and cfg.camera_fps == 10
    assert cfg.audio == "sounddevice" and cfg.audio_device == "" and cfg.scenario == ""
    assert cfg.mirror is True and cfg.brightness == 0.4 and cfg.gamma == 2.2 and cfg.look == "led"
    assert (cfg.apl_cap_day, cfg.apl_cap_night, cfg.night_lux) == (0.12, 0.06, 5.0)
    assert (cfg.night_start, cfg.night_end) == ("01:00", "06:00")
    assert cfg.dwell_seconds == 1.2
    assert (cfg.present_on_seconds, cfg.present_off_seconds, cfg.player_lost_seconds) == (1.0, 3.0, 0.5)
    assert (cfg.leave_seconds, cfg.inactive_seconds, cfg.max_session_seconds) == (8.0, 30.0, 180.0)
    assert cfg.exit_seconds == 3.0 and cfg.allow_record is False
    assert cfg.data_dir == Path("data") and cfg.font_path == Path("fonts/5x7.bin") and cfg.fps == 30
    assert not hasattr(cfg, "idle_seconds")


def test_values_from_file(tmp_path):
    cfg = load_config(write(tmp_path, 'width = 64\nheight = 64\nbackend = "colorlight"\niface = "eth1"\n'
                                      'camera = "replay"\nscenario = "s.jsonl"\ndata_dir = "d"\nleave_seconds = 10'))
    assert cfg.size == (64, 64) and cfg.layout == "64x64"
    assert cfg.backend == "colorlight" and cfg.iface == "eth1"
    assert cfg.camera == "replay" and cfg.scenario == "s.jsonl"
    assert cfg.data_dir == Path("d")
    assert cfg.leave_seconds == 10.0 and isinstance(cfg.leave_seconds, float)


@pytest.mark.parametrize("line,field", [('backend = "hologram"', "backend"), ('audio = "tape"', "audio"),
                                        ("brightness = 1.5", "brightness"), ("brightness = 0", "brightness"),
                                        ("brightnes = 0.2", "brightnes"), ("width = 4", "width")])
def test_bad_values_rejected(tmp_path, line, field):
    with pytest.raises(ValueError, match=field):
        load_config(write(tmp_path, line))


@pytest.mark.parametrize("line,field", [('backend = "matrix"', "backend"), ('camera = "kinect"', "camera"),
                                        ('look = "crt"', "look")])
def test_rejects_bad_enum_values(tmp_path, line, field):
    with pytest.raises(ValueError, match=field):
        load_config(write(tmp_path, line))


@pytest.mark.parametrize("line", ['night_start = "25:00"', 'night_end = "6pm"', 'night_start = "12:60"'])
def test_rejects_bad_night_time(tmp_path, line):
    with pytest.raises(ValueError, match="HH:MM"):
        load_config(write(tmp_path, line))


@pytest.mark.parametrize("line,field", [('brightness = "0.4"', "brightness"), ("width = 12.5", "width"),
                                        ('mirror = "yes"', "mirror"), ("width = true", "width")])
def test_wrong_type_rejected(tmp_path, line, field):
    with pytest.raises(ValueError, match=field):
        load_config(write(tmp_path, line))


@pytest.mark.parametrize("line,field", [("apl_cap_day = 0", "apl_cap_day"), ("apl_cap_day = 5", "apl_cap_day"),
                                        ("apl_cap_night = -0.1", "apl_cap_night"),
                                        ("apl_cap_night = nan", "apl_cap_night"), ("fps = 0", "fps"),
                                        ("fps = -3", "fps"), ("camera_fps = 0", "camera_fps"), ("gamma = 0", "gamma"),
                                        ("gamma = nan", "gamma"), ("gamma = inf", "gamma"),
                                        ("sdl_scale = 0", "sdl_scale"),
                                        ("night_lux = -1", "night_lux"), ("dwell_seconds = nan", "dwell_seconds")])
def test_rejects_out_of_range_values(tmp_path, line, field):
    with pytest.raises(ValueError, match=field):
        load_config(write(tmp_path, line))


@pytest.mark.parametrize("field", [f.name for f in dataclasses.fields(ArcadeConfig) if f.name.endswith("_seconds")])
def test_every_seconds_field_rejects_negative(tmp_path, field):
    with pytest.raises(ValueError, match=field):
        load_config(write(tmp_path, f"{field} = -1.0"))


def test_range_edges_accepted(tmp_path):
    cfg = load_config(write(tmp_path, "apl_cap_day = 1.0\napl_cap_night = 1\ndwell_seconds = 0\nsdl_scale = 1\n"
                                      "night_lux = 0"))
    assert (cfg.apl_cap_day, cfg.apl_cap_night, cfg.dwell_seconds, cfg.sdl_scale, cfg.night_lux) == (1.0, 1.0, 0.0, 1, 0.0)


def test_layout_name():
    assert ArcadeConfig().layout == "128x32"
    assert ArcadeConfig(width=64, height=64).layout == "64x64"


def test_default_file_in_repo_lists_every_field_with_its_default():
    keys = set(tomllib.loads(REPO_TOML.read_text()))
    assert keys == {f.name for f in dataclasses.fields(ArcadeConfig)}
    assert load_config(REPO_TOML) == ArcadeConfig()


def test_distance_look_needs_sdl_scale_4(tmp_path):
    # C20: at sdl_scale under 4 the distance look's eye blur rounds away (look.distance_sigma), so the preview
    # would look sharper than the wall seen from 5 m.
    for scale in (1, 3):
        with pytest.raises(ValueError, match="sdl_scale"):
            load_config(write(tmp_path, f'look = "distance"\nsdl_scale = {scale}'))
    assert load_config(write(tmp_path, 'look = "distance"\nsdl_scale = 4')).sdl_scale == 4
    assert load_config(write(tmp_path, 'look = "plain"\nsdl_scale = 1')).sdl_scale == 1
```

- [ ] **Step 2: Run them to verify they fail**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_canvas.py tests/arcade/test_look.py tests/arcade/test_config.py`

Expected: `6 failed, 76 passed`. The six failures are:
- `test_tiny_negative_and_non_finite_radii_draw_the_centre_as_fill_circle_does`, with `AssertionError: 0` (the ring draws nothing);
- `test_huge_python_ints_clamp_like_huge_floats`, with `assert False` (10**400 differs from 1e300);
- `test_apply_gamma_at_one_returns_a_copy`, with `AssertionError: 1.0`;
- `test_settings_that_are_not_numbers_raise_value_error_at_construction`, with `TypeError`;
- `test_distance_look_needs_sdl_scale_4`, with `Failed: DID NOT RAISE ValueError`;
- `test_light_lut_is_the_looks_table_checked`, with `AttributeError: module 'arcade.look' has no attribute 'light_lut'`.

- [ ] **Step 3: Implement**

`arcade/canvas.py`:

```python
"""Canvas (spec 7.4): drawing over a (height, width, 3) uint8 frame. Everything clips; nothing raises or hangs."""
from __future__ import annotations

import math

import numpy as np

from show.font import CELL_H, CELL_W, Font

Color = tuple[int, int, int]

_FAR = 1 << 20   # coordinates are clamped to plus or minus this; NaN, infinity and garbage land at -_FAR


def _i(v) -> int:
    """A coordinate as an int: rounded half up (so 0.5 px steps are even), clamped to plus or minus _FAR.

    A huge number clamps to its end, a Python int too (10**400 is past any float but lands at _FAR like
    1e300). NaN, infinity and anything that is not a number land at -_FAR (05-plan S4). So a huge width
    or radius fills, an infinite width draws nothing, and an infinite, NaN, negative or sub-half-pixel
    radius draws only the centre pixel, for circle as for fill_circle: harmless either way, and nothing
    hangs."""
    if isinstance(v, int):
        return max(-_FAR, min(_FAR, v))
    try:
        return max(-_FAR, min(_FAR, math.floor(v + 0.5)))
    except (ValueError, OverflowError, TypeError):
        return -_FAR


def _channel(v) -> int:
    try:
        return max(0, min(255, math.floor(v + 0.5)))
    except OverflowError:
        return 255 if v > 0 else 0
    except (ValueError, TypeError):
        return 0


def _c(color) -> Color:
    """A colour as three ints clamped to 0..255; NaN is 0."""
    r, g, b = color
    return (_channel(r), _channel(g), _channel(b))


def sprite_from_rows(rows: list[str], palette: dict[str, Color]) -> np.ndarray:
    """An (h, w, 3) uint8 sprite from equal-length rows of palette characters; "." is always black."""
    lut = {**{k: _c(v) for k, v in palette.items()}, ".": (0, 0, 0)}
    widths = {len(r) for r in rows}
    if len(widths) > 1:
        raise ValueError(f"sprite rows differ in length: {sorted(widths)}")
    out = np.zeros((len(rows), widths.pop() if widths else 0, 3), np.uint8)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch not in lut:
                raise ValueError(f"sprite character {ch!r} at row {y}, column {x} is not in the palette")
            out[y, x] = lut[ch]
    return out


class Canvas:
    """Drawing over an (h, w, 3) uint8 frame. Coordinates may be int or float and are rounded; colours are
    clamped to 0..255. Out-of-range drawing clips, never raises, never hangs."""

    sprite_from_rows = staticmethod(sprite_from_rows)

    def __init__(self, width: int, height: int, font: Font):
        self.width, self.height = width, height
        self.font = font
        self.frame = np.zeros((height, width, 3), dtype=np.uint8)

    @property
    def size(self) -> tuple[int, int]:
        return (self.width, self.height)

    def clear(self, color: Color = (0, 0, 0)) -> None:
        self.frame[:] = _c(color)

    def pixel(self, x, y, color: Color) -> None:
        x, y = _i(x), _i(y)
        if 0 <= x < self.width and 0 <= y < self.height:
            self.frame[y, x] = _c(color)

    def fill_rect(self, x, y, w, h, color: Color) -> None:
        x, y, w, h = _i(x), _i(y), _i(w), _i(h)
        x0, y0 = max(x, 0), max(y, 0)
        x1, y1 = min(x + w, self.width), min(y + h, self.height)
        if x0 < x1 and y0 < y1:
            self.frame[y0:y1, x0:x1] = _c(color)

    def rect(self, x, y, w, h, color: Color) -> None:
        x, y, w, h = _i(x), _i(y), _i(w), _i(h)
        if w <= 0 or h <= 0:
            return
        self.fill_rect(x, y, w, 1, color)
        self.fill_rect(x, y + h - 1, w, 1, color)
        self.fill_rect(x, y, 1, h, color)
        self.fill_rect(x + w - 1, y, 1, h, color)

    def line(self, x0, y0, x1, y1, color: Color) -> None:
        """Bresenham. A line with an endpoint beyond four times the canvas extent is skipped (spec 7.4)."""
        x0, y0, x1, y1 = _i(x0), _i(y0), _i(x1), _i(y1)
        if max(abs(x0), abs(y0), abs(x1), abs(y1)) > 4 * (self.width + self.height):
            return
        color = _c(color)
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            if 0 <= x0 < self.width and 0 <= y0 < self.height:
                self.frame[y0, x0] = color
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def _disc(self, cx, cy, r, color: Color, ring: bool) -> None:
        cx, cy, r = _i(cx), _i(cy), max(_i(r), 0)
        x0, y0 = max(cx - r, 0), max(cy - r, 0)
        x1, y1 = min(cx + r + 1, self.width), min(cy + r + 1, self.height)
        if x0 >= x1 or y0 >= y1:
            return
        yy, xx = np.ogrid[y0:y1, x0:x1]
        d2 = (xx - cx) ** 2 + (yy - cy) ** 2
        mask = d2 <= (r + 0.5) ** 2
        if ring and r > 0:                  # a ring of radius 0 is its centre pixel, as the disc is
            mask &= d2 >= (r - 0.5) ** 2
        self.frame[y0:y1, x0:x1][mask] = _c(color)

    def fill_circle(self, cx, cy, r, color: Color) -> None:
        self._disc(cx, cy, r, color, ring=False)

    def circle(self, cx, cy, r, color: Color) -> None:
        self._disc(cx, cy, r, color, ring=True)

    def _window(self, h: int, w: int, x: int, y: int):
        """The on-canvas part of an h by w sprite at (x, y), as (frame slices, sprite slices), or None."""
        x0, y0 = max(x, 0), max(y, 0)
        x1, y1 = min(x + w, self.width), min(y + h, self.height)
        if x0 >= x1 or y0 >= y1:
            return None
        return (slice(y0, y1), slice(x0, x1)), (slice(y0 - y, y1 - y), slice(x0 - x, x1 - x))

    def blit(self, mask: np.ndarray, x, y, color: Color) -> None:
        """Lights the True cells of a bool mask in one colour."""
        mask = np.asarray(mask, bool)
        win = self._window(*mask.shape, _i(x), _i(y))
        if win is not None:
            dst, src = win
            self.frame[dst][mask[src]] = _c(color)

    def blit_rgb(self, sprite: np.ndarray, x, y) -> None:
        """Copies an (h, w, 3) sprite; black pixels are transparent. A sprite that is not uint8 (a game's
        float buffer) is rounded half up and clamped to 0..255 first, NaN to 0, so black is judged after."""
        sprite = np.asarray(sprite)
        if sprite.dtype != np.uint8:
            v = np.floor(np.nan_to_num(sprite.astype(np.float64), nan=0.0, posinf=255.0, neginf=0.0) + 0.5)
            sprite = np.clip(v, 0, 255).astype(np.uint8)
        win = self._window(*sprite.shape[:2], _i(x), _i(y))
        if win is not None:
            dst, src = win
            sub = sprite[src]
            lit = sub.any(axis=2)
            self.frame[dst][lit] = sub[lit]

    def _scale(self, scale) -> int:
        """Text scale as an int from 1 to the canvas's larger side (a bigger glyph cannot show)."""
        return max(1, min(_i(scale), max(self.width, self.height)))

    def text_width(self, s, scale=1) -> int:
        return CELL_W * self._scale(scale) * len(str(s))

    def text(self, x, y, s, color: Color, scale=1) -> int:
        """Draws s in the 5x7 font, each glyph pixel scale by scale (2 gives 10 by 14 with 2 px strokes);
        returns the width drawn, text_width(s, scale). Characters past 255 draw as "?"."""
        s, k = str(s), self._scale(scale)
        x, y, color = _i(x), _i(y), _c(color)
        cell_w = CELL_W * k
        if y >= self.height or y + CELL_H * k <= 0:
            return self.text_width(s, k)
        atlas = self.font.atlas()
        for i in range(max(0, -x // cell_w), len(s)):        # glyphs wholly off the left edge are skipped
            cx, ch = x + i * cell_w, s[i]
            if cx >= self.width:
                break
            if cx + cell_w <= 0:
                continue
            glyph = atlas[ord(ch) if ord(ch) < 256 else ord("?")]
            if k > 1:
                glyph = glyph.repeat(k, axis=0).repeat(k, axis=1)
            self.blit(glyph, cx, y, color)
        return self.text_width(s, k)
```

`arcade/look.py`:

```python
"""Preview render modes (spec 9.4): how a wall frame looks as flat pixels, as LED dots, and from a distance.

Pure numpy: this module never imports cv2, so the SDL preview never loads OpenCV's own SDL next to pygame's.
"""
from __future__ import annotations

import math
import numbers
import operator
from functools import lru_cache

import numpy as np

MODES = ("plain", "led", "distance")

MONITOR_GAMMA = 2.2        # a preview's bytes are decoded by an sRGB monitor
PITCH_M = 0.005            # P5 modules: 5 mm between LEDs
BLUR_ARCMIN = 1.5          # what the eye resolves at night (spec 9.4)
HALATION_SIGMAS = 3.0      # the glow around bright pixels spreads three times as far as the blur
HALATION = 0.3             # the share of a white pixel's light scattered into the glow (times luminance); under 1
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)   # Rec. 709 weights on linear light


def _frozen(a: np.ndarray) -> np.ndarray:
    """A cached array is shared by every caller, so it is read-only: an in-place edit raises."""
    a.flags.writeable = False
    return a


@lru_cache(maxsize=8)
def gamma_lut(gamma: float) -> np.ndarray:
    v = np.arange(256, dtype=np.float64) / 255.0
    return _frozen(np.clip(np.round(255.0 * v ** (1.0 / gamma)), 0, 255).astype(np.uint8))


def apply_gamma(frame: np.ndarray, gamma: float) -> np.ndarray:
    """frame through gamma_lut(gamma), always a new array: at 1.0 a copy, so a caller may write into it."""
    if gamma == 1.0:
        return frame.copy()
    return gamma_lut(gamma)[frame]


@lru_cache(maxsize=8)
def _led_kernel(scale: int) -> np.ndarray:
    c = (scale - 1) / 2
    yy, xx = np.mgrid[0:scale, 0:scale]
    d = np.hypot(xx - c, yy - c) / scale
    return _frozen(np.where(d <= 0.36, 1.0, np.where(d <= 0.5, 0.3, 0.0)).astype(np.float32))


def _nearest(frame: np.ndarray, scale: int) -> np.ndarray:
    return np.repeat(np.repeat(frame, scale, axis=0), scale, axis=1)


def distance_sigma(metres: float) -> float:
    """The eye's blur at this distance, in wall pixels: 1.5 arcmin across the 5 mm pitch (0.436 at 5 m).

    The preview blurs sigma * scale preview pixels with three box blurs, which cannot go below one pixel:
    at scale 1 and 5 m the boxes have radius 0 and the core is not blurred at all (the glow still is), so
    judge distance at scale 4 or more."""
    return metres * math.tan(math.radians(BLUR_ARCMIN / 60.0)) / PITCH_M


@lru_cache(maxsize=8)
def _light_lut(gamma: float) -> np.ndarray:
    """Byte to the light the preview shows, 0..1: the led look's bytes as a monitor decodes them."""
    v = np.arange(256, dtype=np.float64) / 255.0
    return _frozen((v ** (MONITOR_GAMMA / gamma)).astype(np.float32))


def light_lut(gamma: float) -> np.ndarray:
    """Byte to the light the wall emits, 0..1 of full: the led and distance looks' own read-only table, shared
    with the flash governor and the brightness limiter so all of them agree. With gamma 2.2 the card sends bytes
    as they are and the light is linear in the byte; with 1.0 the card applies gamma and the light is
    (byte / 255) ** 2.2. A gamma that is not a finite number over 0 raises ValueError."""
    if not (is_real(gamma) and 0.0 < gamma < math.inf):
        raise ValueError(f"gamma must be over 0 and finite, got {gamma!r}")
    return _light_lut(float(gamma))


def _box_radii(sigma: float, n: int = 3) -> list[int]:
    """Radii of n box blurs whose sum approximates a Gaussian of this sigma (Kovesi's widths)."""
    sigma = min(sigma, 1e6)               # wider than any preview already; keeps the squares finite
    ideal = math.sqrt(12.0 * sigma * sigma / n + 1.0)
    lo = int(ideal)
    lo -= 1 - lo % 2                      # the largest odd width at or under the ideal
    m = round((12.0 * sigma * sigma - n * lo * lo - 4 * n * lo - 3 * n) / (-4 * lo - 4))
    return [(lo if i < m else lo + 2) // 2 for i in range(n)]


def _box(a: np.ndarray, r: int, axis: int) -> np.ndarray:
    """Mean over 2r + 1 cells along axis; cells past the edge are dark, as the air beside the wall is."""
    if r <= 0:
        return a
    if r >= a.shape[axis]:                  # every window holds the whole line: one mean, and no huge pads
        return np.broadcast_to(a.sum(axis=axis, keepdims=True) / (2 * r + 1), a.shape).copy()
    a = np.moveaxis(a, axis, 0)
    pad = np.zeros((r + 1,) + a.shape[1:], a.dtype), a, np.zeros((r,) + a.shape[1:], a.dtype)
    c = np.cumsum(np.concatenate(pad), axis=0)
    out = (c[2 * r + 1:] - c[:-2 * r - 1]) / (2 * r + 1)
    return np.moveaxis(out, 0, axis)


@lru_cache(maxsize=16)
def _spread(n: int, scale: int, sigma: float) -> np.ndarray:
    """(n * scale, n): how one wall pixel's light lands on a preview line after the nearest-neighbour
    upscale and three box blurs. The blur is linear and separable, so it is built once per size."""
    m = np.repeat(np.eye(n, dtype=np.float32), scale, axis=0)
    for r in _box_radii(sigma):
        m = _box(m, r, 0)
    return _frozen(np.ascontiguousarray(m))


def _gauss(light: np.ndarray, scale: int, sigma: float) -> np.ndarray:
    """light (h, w, 3) at wall resolution, upscaled by scale and blurred by a Gaussian of sigma preview px."""
    h, w, _ = light.shape
    rows = (_spread(h, scale, sigma) @ light.reshape(h, w * 3)).reshape(h * scale, w, 3)
    return np.einsum("Ywc,Xw->YXc", rows, _spread(w, scale, sigma), optimize=True)


def _distance(frame: np.ndarray, scale: int, gamma: float, metres: float) -> np.ndarray:
    """Light is conserved: a luminance-weighted share of each pixel's light scatters into the wide glow and
    the rest stays in the eye's blur, so a flat field keeps the led look's level at every distance."""
    light = _light_lut(gamma)[frame]
    sigma = distance_sigma(metres) * scale
    scattered = HALATION * light * (light @ LUMA)[..., None]
    core = _gauss(light - scattered, scale, sigma)
    halo = _gauss(scattered, scale, HALATION_SIGMAS * sigma)
    shown = np.clip(core + halo, 0.0, 1.0) ** (1.0 / MONITOR_GAMMA)
    return np.round(shown * 255.0).astype(np.uint8)


def is_real(v) -> bool:
    """A real number (NaN and infinities included), not a bool, None or a string."""
    return isinstance(v, numbers.Real) and not isinstance(v, (bool, np.bool_))


def check_settings(mode: str, scale: int, gamma: float, metres: float = 5.0) -> int:
    """Raises ValueError unless these render settings are valid; returns scale as an int.

    mode is one of MODES; scale is any integer type of at least 1 (a numpy integer from a computed fit,
    never a float or a bool); gamma is over 0 and finite; metres is 0 or more and finite. None, a string
    or a bool for gamma or metres raises ValueError too, not TypeError."""
    if mode not in MODES:
        raise ValueError(f"look must be one of {MODES}, got {mode!r}")
    try:
        size = operator.index(scale)                   # an int or a numpy integer; never a float
    except TypeError:
        size = 0
    if isinstance(scale, (bool, np.bool_)) or size < 1:
        raise ValueError(f"scale must be an int of at least 1, got {scale!r}")
    if not (is_real(gamma) and 0.0 < gamma < math.inf):
        raise ValueError(f"gamma must be over 0 and finite, got {gamma!r}")
    if not (is_real(metres) and 0.0 <= metres < math.inf):
        raise ValueError(f"metres must be 0 or more and finite, got {metres!r}")
    return size


def render(frame: np.ndarray, mode: str, scale: int = 8, gamma: float = 2.2, metres: float = 5.0) -> np.ndarray:
    """frame (h, w, 3) uint8 drawn at scale for a monitor.

    plain: nearest-neighbour, the bytes as they are. led: round dots with dark gaps, after gamma (with
    gamma 2.2 the preview shows the light of an uncorrected wall; with 1.0, the bytes as the card
    applies gamma). distance: each pixel as a full square of the led look's light (not its dot), seen
    from metres away: blurred by 1.5 arcmin, with a luminance-weighted share scattered into a glow three
    times wider, for legibility checks (spec 9.4). At 5 m the real eye still resolves the 5 mm dot grid,
    so text reads slightly smoother in this preview than on the wall. Settings are checked by
    check_settings; scale may be any integer type.
    """
    scale = check_settings(mode, scale, gamma, metres)
    if frame.ndim != 3 or frame.shape[2] != 3 or frame.dtype != np.uint8:
        raise ValueError(f"frame must be (height, width, 3) uint8, got {frame.shape} {frame.dtype}")
    if mode == "plain":
        return _nearest(frame, scale)
    if mode == "distance":
        return _distance(frame, scale, gamma, metres)
    f = apply_gamma(frame, gamma)
    h, w = f.shape[:2]
    k = _led_kernel(scale)
    out = f[:, None, :, None, :].astype(np.float32) * k[None, :, None, :, None]
    return out.reshape(h * scale, w * scale, 3).astype(np.uint8)


def dim(image: np.ndarray, level: float) -> np.ndarray:
    """A preview image showing level (0..1) of its light: a monitor decodes bytes with MONITOR_GAMMA, so
    the bytes scale by level ** (1 / MONITOR_GAMMA). NaN or a level not over 0 gives black; None, a
    string or a bool is not a level and raises ValueError."""
    if not is_real(level):
        raise ValueError(f"level must be a number, got {level!r}")
    if not level > 0.0:
        return np.zeros_like(image)
    if level >= 1.0:
        return image
    factor = level ** (1.0 / MONITOR_GAMMA)
    return np.round(image.astype(np.float32) * factor).astype(np.uint8)
```

`arcade/preview.py`:

```python
from __future__ import annotations

import numpy as np

from arcade.look import check_settings, dim, is_real, render
from show.display import Display


class PreviewDisplay:
    """Renders a wall frame in a look mode before handing it to a real (usually SDL) display.

    Brightness is modelled here: set_brightness forwards the level to the inner display (which stores it; the
    SDL window never dims) and scales the rendered preview so the monitor shows that fraction of the light.
    The wall frame itself is never scaled (Global Constraints: pixels pushed to hardware are never scaled).
    The settings are checked here, at construction, with look.check_settings (ValueError), not on the first push;
    a level that is not a number raises ValueError in set_brightness and is neither kept nor forwarded.
    """

    def __init__(self, inner: Display, mode: str, scale: int, gamma: float, metres: float = 5.0):
        scale = check_settings(mode, scale, gamma, metres)
        self.inner, self.mode, self.scale, self.gamma, self.metres = inner, mode, scale, gamma, metres
        self.level = 1.0

    def push(self, frame: np.ndarray) -> None:
        image = render(frame, self.mode, self.scale, self.gamma, self.metres)
        self.inner.push(dim(image, self.level))

    def set_brightness(self, level: float) -> None:
        if not is_real(level):
            raise ValueError(f"brightness must be a number, got {level!r}")
        self.level = level
        self.inner.set_brightness(level)

    def close(self) -> None:
        self.inner.close()
```

`arcade/config.py`:

```python
"""ArcadeConfig: the flat arcade.toml (spec 4.3). Calibration lives in arcade/calibration.py."""
from __future__ import annotations

import dataclasses
import math
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

BACKENDS = ("sdl", "fake", "colorlight", "ddp")
CAMERAS = ("mediapipe", "imx500", "replay", "none")
AUDIOS = ("sounddevice", "replay", "none")
LOOKS = ("plain", "led", "distance")
DISTANCE_MIN_SCALE = 4   # below this the distance look's eye blur rounds away (look.distance_sigma)
HHMM = re.compile(r"([01]\d|2[0-3]):[0-5]\d")


@dataclass
class ArcadeConfig:
    width: int = 128
    height: int = 32
    backend: str = "sdl"
    sdl_scale: int = 8
    iface: str = "eth0"
    ddp_host: str = "127.0.0.1"
    ddp_port: int = 4048
    camera: str = "mediapipe"
    camera_index: int = 0
    camera_fps: int = 10
    audio: str = "sounddevice"
    audio_device: str = ""
    scenario: str = ""
    mirror: bool = True
    brightness: float = 0.4
    apl_cap_day: float = 0.12
    apl_cap_night: float = 0.06
    night_start: str = "01:00"
    night_end: str = "06:00"
    night_lux: float = 5.0
    gamma: float = 2.2
    look: str = "led"
    dwell_seconds: float = 1.2
    present_on_seconds: float = 1.0
    present_off_seconds: float = 3.0
    player_lost_seconds: float = 0.5
    leave_seconds: float = 8.0
    inactive_seconds: float = 30.0
    max_session_seconds: float = 180.0
    exit_seconds: float = 3.0
    allow_record: bool = False
    data_dir: Path = Path("data")
    font_path: Path = Path("fonts/5x7.bin")
    fps: int = 30

    @property
    def size(self) -> tuple[int, int]:
        return (self.width, self.height)

    @property
    def layout(self) -> str:
        return f"{self.width}x{self.height}"


def _coerce(name: str, value, default):
    """A TOML value as the field's type. Ints are accepted for float fields; true/false only for bools."""
    if isinstance(default, Path):
        if isinstance(value, str):
            return Path(value)
    elif isinstance(default, bool):
        if isinstance(value, bool):
            return value
    elif isinstance(value, bool):
        pass
    elif isinstance(default, float) and isinstance(value, (int, float)):
        return float(value)
    elif isinstance(value, type(default)):
        return value
    kind = "a path string" if isinstance(default, Path) else type(default).__name__
    raise ValueError(f"{name} must be {kind}, got {value!r}")


def load_config(path: Path | str) -> ArcadeConfig:
    path = Path(path)
    raw = tomllib.loads(path.read_text()) if path.exists() else {}
    defaults = ArcadeConfig()
    names = {f.name for f in dataclasses.fields(ArcadeConfig)}
    unknown = sorted(set(raw) - names)
    if unknown:
        raise ValueError(f"unknown config keys: {unknown}")
    cfg = ArcadeConfig(**{k: _coerce(k, v, getattr(defaults, k)) for k, v in raw.items()})
    for name, allowed in (("backend", BACKENDS), ("camera", CAMERAS), ("audio", AUDIOS), ("look", LOOKS)):
        if getattr(cfg, name) not in allowed:
            raise ValueError(f"{name} must be one of {allowed}, got {getattr(cfg, name)!r}")
    for name in ("night_start", "night_end"):
        if not HHMM.fullmatch(getattr(cfg, name)):
            raise ValueError(f"{name} must be HH:MM (00:00 to 23:59), got {getattr(cfg, name)!r}")
    for name in ("brightness", "apl_cap_day", "apl_cap_night"):
        if not 0 < getattr(cfg, name) <= 1:   # NaN fails too
            raise ValueError(f"{name} must be in (0, 1], got {getattr(cfg, name)}")
    for name in ("fps", "camera_fps", "gamma"):
        if not getattr(cfg, name) > 0:
            raise ValueError(f"{name} must be greater than 0, got {getattr(cfg, name)}")
    if not math.isfinite(cfg.gamma):
        raise ValueError(f"gamma must be finite, got {cfg.gamma}")
    if cfg.sdl_scale < 1:
        raise ValueError(f"sdl_scale must be at least 1, got {cfg.sdl_scale}")
    if cfg.look == "distance" and cfg.sdl_scale < DISTANCE_MIN_SCALE:
        raise ValueError(f'look = "distance" needs sdl_scale {DISTANCE_MIN_SCALE} or more (its eye blur rounds '
                         f"away below that), got {cfg.sdl_scale}")
    for name in [f.name for f in dataclasses.fields(ArcadeConfig) if f.name.endswith("_seconds")] + ["night_lux"]:
        if not getattr(cfg, name) >= 0:
            raise ValueError(f"{name} must be 0 or more, got {getattr(cfg, name)}")
    if cfg.width < 8 or cfg.height < 8:
        raise ValueError(f"width and height must be at least 8, got {cfg.layout}")
    return cfg
```

- [ ] **Step 4: Run the tests**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_canvas.py tests/arcade/test_look.py tests/arcade/test_config.py`

Expected: `82 passed` (canvas 21, look 18, config 43).

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`

Expected: `230 passed`, no skips.

- [ ] **Step 5: Commit**

```bash
git add arcade/canvas.py arcade/look.py arcade/preview.py arcade/config.py tests/arcade/test_canvas.py tests/arcade/test_look.py tests/arcade/test_config.py
git commit -m "fix(arcade): circle draws its centre at tiny radii, huge ints clamp, apply_gamma copies, preview settings checked at construction (it03 C18, C19, C20)" -m "No existing test line changed; six tests appended. look = \"distance\" now needs sdl_scale 4 or more at config load. look.light_lut is the looks' light table, public and checked, for the flash governor and the brightness limiter." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Input helpers with graces sized in captures (core Task 8 part, carried C10)

**Files:**
- Create: `arcade/input.py`
- Test: `tests/arcade/test_input.py`

**Interfaces:**
- Consumes: Task 1's `look.is_real`, `arcade.sensed` (`Body`, `Keypoint`, `LEFT_WRIST`, `RIGHT_WRIST`, `LEFT_HIP`, `RIGHT_HIP`, `MIN_CONF`, `Body.reach`, `Body.hip_mid`, `Body.shoulder_mid`, `Body.cursor`), and, in the tests, `arcade.sources.actors` (`REAL_NOISE`, `TICK`, `Person`, `degrade`, `scene`).
- Produces:
  - `CAPTURE_GRACE = 5`.
  - `capture_grace(camera_fps: float, captures: int = CAPTURE_GRACE) -> float`.
  - `Edge(grace=0.25)`, with `.on` and `update(value: bool, t: float) -> bool`.
  - `Hold(seconds, grace=0.25)`, with `.start`, `.fired`, `.progress` (0..1), `reset()` and `update(value: bool, t: float) -> bool`.
  - `Cursor(grace=0.25, switch=1.25)`, with `.hand` (`"left"`, `"right"` or `None`) and `update(body: Body | None, t: float) -> tuple[float, float] | None`.
  - `OneEuro(min_cutoff=1.0, beta=0.007, d_cutoff=1.0)`, with `.value`, `reset()` and `__call__(x: float, t: float) -> float`.
  - Every constructor raises `ValueError` for a bad parameter, and takes numpy numbers, stored as `float`.

- [ ] **Step 1: Write the failing tests**

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
```

- [ ] **Step 2: Run them to verify they fail**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_input.py`

Expected: `1 error` during collection, with `ModuleNotFoundError: No module named 'arcade.input'`.

- [ ] **Step 3: Implement**

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
"""
from __future__ import annotations

import math

from arcade.look import is_real
from arcade.sensed import LEFT_HIP, LEFT_WRIST, MIN_CONF, RIGHT_HIP, RIGHT_WRIST, Body

CAPTURE_GRACE = 5        # missed captures in a row that a hold, an edge or the cursor rides out
EPSILON = 1e-9           # tick times are sums of 1/30: a 3.0 s hold must not miss by a rounding error


def _check(name: str, value: float) -> float:
    if not is_real(value) or not 0.0 <= value < math.inf:
        raise ValueError(f"{name} must be a finite number of seconds, 0 or more, got {value!r}")
    return float(value)


def capture_grace(camera_fps: float, captures: int = CAPTURE_GRACE) -> float:
    """Seconds that cover this many missed captures in a row, plus half a capture so a run of exactly that
    many never trips on a rounding error: 0.55 s at 10 fps. A run one capture longer ends the hold."""
    if not is_real(camera_fps) or not 0.0 < camera_fps < math.inf:
        raise ValueError(f"camera_fps must be over 0 and finite, got {camera_fps!r}")
    if isinstance(captures, bool) or not isinstance(captures, int) or captures < 0:
        raise ValueError(f"captures must be an int, 0 or more, got {captures!r}")
    return (captures + 0.5) / float(camera_fps)


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
    last output unchanged, and so does a sample that is not finite. beta = 0.007 is the paper's value for
    pixel units; in the 0..1 camera units the arcade uses it barely adapts, so the tracker (core Task 16)
    passes its own when it is tuned against the real fixtures."""

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.007, d_cutoff: float = 1.0):
        for name, v in (("min_cutoff", min_cutoff), ("d_cutoff", d_cutoff)):
            if not is_real(v) or not 0.0 < v < math.inf:
                raise ValueError(f"{name} must be over 0 and finite, got {v!r}")
        if not is_real(beta) or not 0.0 <= beta < math.inf:
            raise ValueError(f"beta must be 0 or more and finite, got {beta!r}")
        self.min_cutoff, self.beta, self.d_cutoff = min_cutoff, beta, d_cutoff
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
        if not (math.isfinite(x) and math.isfinite(t)):
            return x if self.value is None else self.value
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

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_input.py`

Expected: `12 passed`, in about 2 s.

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`

Expected: `242 passed`, no skips.

- [ ] **Step 5: Commit**

```bash
git add arcade/input.py tests/arcade/test_input.py
git commit -m "feat(arcade): Edge, Hold, Cursor and One Euro input helpers with graces sized in camera captures (core Task 8 part, it02 C10)" -m "capture_grace(10) is 0.55 s: the 3 s exit hold completes under spec 6.4 noise for 40 of 40 seeds, where 0.25 s loses a quarter. CAPTURE_GRACE = 5 is owner question Q10." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Game protocol, registry and scores (core Task 7)

**Files:**
- Create: `arcade/game.py`, `arcade/games/__init__.py`, `arcade/scores.py`
- Test: `tests/arcade/test_game.py`, `tests/arcade/test_scores.py`

**Interfaces:**
- Consumes: Task 1's `look.is_real`, and `Canvas` (iteration 3) and `Sensed`, for type hints only.
- Produces:
  - In `arcade/game.py`:
    - `INPUTS`, `KINDS`, `LAYOUTS`, `ICON_SIZE = 16`, `RUNNER_KEYS` (10 keys), `FX_PREFIX = "fx_"` and `reserved(key) -> bool`.
    - `GameInfo(name, title, verb, icon, needs, layouts=LAYOUTS, players=1, exit_gesture=True, kind="control", abandon_seconds=None)`, frozen and validated.
    - The `Game` protocol, with class attributes `info`, `SCENARIOS = MappingProxyType({})` (read-only; a game assigns its own dict), `CAPTION_KEYS = ()` and `PHASES = ("play",)`, the attribute `scores: GameScores`, and `reset(size, rng, fx)`, `update(sensed, dt)`, `draw(canvas)`, `done()` and `debug_state()`.
    - `icon_from_rows(rows: list[str]) -> np.ndarray`, a (16, 16) read-only bool array.
  - In `arcade/games/__init__.py`: `MENU_ORDER` (ten names), `all_games() -> list[type]` in `MENU_ORDER` order, and `get_game(name) -> type`, which raises `KeyError`.
  - In `arcade/scores.py`:
    - `ROLLOVER_HOUR = 16`, `REASONS` (six) and `night_of(datetime) -> date`.
    - `Scores(path | None, clock=datetime.now)`, with `for_game(name, layout) -> GameScores`, `best(name, layout)`, `last_night(name, layout)` and `record(name, layout, value, margin=0.0) -> bool`.
    - `GameScores`, with `record(value, margin=0.0)`, `best()` and `last_night()`.
    - `SessionLog(path | None)`, with `.records` and `append(game, layout, start: datetime, duration, players, score, reason) -> dict`.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_game.py`:

```python
import importlib
import logging
import math
import types

import numpy as np
import pytest

import arcade.games as games
from arcade.game import FX_PREFIX, INPUTS, KINDS, LAYOUTS, RUNNER_KEYS, Game, GameInfo, icon_from_rows, reserved
from arcade.games import MENU_ORDER, all_games, get_game

BLANK = ["." * 16] * 16


def info(**over):
    return GameInfo(**(dict(name="dodge", title="Dodge", verb="DODGE", icon=icon_from_rows(BLANK),
                            needs=frozenset({"pose"})) | over))


def test_icon_from_rows():
    rows = ["#" + "." * 14 + "#"] + ["." * 16] * 14 + ["#" + "." * 14 + "#"]
    icon = icon_from_rows(rows)
    assert icon.shape == (16, 16) and icon.dtype == bool and not icon.flags.writeable
    assert icon[0, 0] and icon[15, 15] and not icon[7, 7] and icon.sum() == 4
    for bad in (["#"], ["." * 16] * 15, ["." * 16] * 15 + ["." * 15], ["." * 16] * 15 + ["." * 15 + "x"],
                [["."] * 16] * 16):
        with pytest.raises(ValueError):
            icon_from_rows(bad)


def test_game_info_is_frozen():
    i = info()
    with pytest.raises(Exception):
        i.name = "y"  # type: ignore[misc]
    with pytest.raises(ValueError):
        i.icon[0, 0] = True                                          # the icon is a read-only copy


def test_game_info_defaults_follow_the_spec():
    i = info()
    assert i.layouts == LAYOUTS == frozenset({"128x32", "64x64"})
    assert (i.players, i.exit_gesture, i.kind, i.abandon_seconds) == (1, True, "control", None)
    assert INPUTS == frozenset({"pose", "blobs", "motion", "audio"}) and KINDS == ("control", "toy", "score")
    rows = ["#" * 16] + ["." * 16] * 15
    source = np.array([[ch == "#" for ch in r] for r in rows])
    i = info(icon=source, needs={"blobs", "audio"}, layouts=["64x32"], players=2, exit_gesture=False, kind="toy",
             abandon_seconds=45)
    source[0, 0] = False                                             # the caller's array is copied
    assert i.icon[0, 0] and i.needs == frozenset({"blobs", "audio"}) and i.layouts == frozenset({"64x32"})
    assert isinstance(i.needs, frozenset) and isinstance(i.layouts, frozenset)
    assert info(needs=frozenset()).needs == frozenset()             # a no-input toy is allowed
    assert info(abandon_seconds=np.float32(30)).abandon_seconds == 30  # a numpy number is a number


@pytest.mark.parametrize("over", [
    dict(icon=np.zeros((8, 8), bool)), dict(icon=np.zeros((16, 16), np.uint8)), dict(icon=None),
    dict(kind="arcade"), dict(layouts=frozenset({"128 x 32"})), dict(layouts=frozenset()), dict(layouts="128x32"),
    dict(layouts=frozenset({"0x32"})), dict(needs=frozenset({"pose", "sonar"})), dict(needs="pose"), dict(needs=""),
    dict(name="Dodge"), dict(name="3d"), dict(name=""), dict(name="_x"), dict(title=""), dict(verb="  "),
    dict(verb=None),
    dict(players=0), dict(players=3), dict(players=True), dict(players=1.0), dict(exit_gesture=1),
    dict(abandon_seconds=0), dict(abandon_seconds=-5.0), dict(abandon_seconds=math.inf),
    dict(abandon_seconds=math.nan), dict(abandon_seconds=True), dict(abandon_seconds="45"),
    dict(abandon_seconds=np.True_), dict(abandon_seconds=np.float32(0)),
])
def test_game_info_validates(over):
    with pytest.raises(ValueError):
        info(**over)


def test_reserved_keys_are_the_runners():
    assert RUNNER_KEYS == {"game", "t", "idle", "attract", "hidden", "crashes", "glitch", "flash_held_ticks", "player",
                           "present"}
    assert FX_PREFIX == "fx_" and reserved("fx_shake") and reserved("t") and reserved("present")
    assert not reserved("score") and not reserved("phase") and not reserved("ball_xy") and not reserved("tx")
    assert not reserved("fxlevel") and not reserved("fx")                  # the prefix is fx_, underscore and all


def test_game_protocol_defaults():
    class Toy(Game):
        info = info(name="paint")

    assert Toy.PHASES == ("play",) and Toy.CAPTION_KEYS == () and Toy.SCENARIOS == {}
    with pytest.raises(TypeError):
        Toy.SCENARIOS["serve"] = lambda: None                        # one default shared by every game: read-only


def test_menu_order_lists_the_ten_spec_games():
    assert MENU_ORDER == ("copyme", "pong", "paint", "quickdraw", "dodge", "tug", "flap", "swat", "strongman",
                          "freeze")
    assert len(set(MENU_ORDER)) == 10


def fake_modules(monkeypatch, modules):
    """import_module that serves these fake arcade.games.<name> modules; anything else is missing."""
    real = importlib.import_module

    def import_module(name, package=None):
        short = name.rpartition(".")[2]
        if name.startswith("arcade.games.") and short in modules:
            found = modules[short]
            if isinstance(found, BaseException):
                raise found
            return found
        if name.startswith("arcade.games."):
            raise ModuleNotFoundError(f"No module named {name!r}", name=name)
        return real(name, package)

    monkeypatch.setattr(games.importlib, "import_module", import_module)


def module_with(game):
    m = types.ModuleType("fake")
    m.GAME = game
    return m


def game_class(name):
    return type(name.title(), (), {"info": info(name=name)})


def test_discovery_skips_missing_modules(monkeypatch, caplog):
    fake_modules(monkeypatch, {})
    assert all_games() == []                                         # no game module at all
    pong, dodge = game_class("pong"), game_class("dodge")
    fake_modules(monkeypatch, {"dodge": module_with(dodge), "pong": module_with(pong)})
    with caplog.at_level(logging.DEBUG, logger="arcade"):
        assert all_games() == [pong, dodge]                          # MENU_ORDER, not the order found
    assert caplog.records == []                                      # a game not written yet is not an error
    assert get_game("dodge") is dodge
    for name in ("copyme", "nope"):
        with pytest.raises(KeyError):
            get_game(name)


def test_broken_module_is_logged_and_skipped(monkeypatch, caplog):
    tug = game_class("tug")
    missing_dep = ModuleNotFoundError("No module named 'scipy'", name="scipy")
    missing_helper = ModuleNotFoundError("No module named 'arcade.games.strongman_audio'",
                                         name="arcade.games.strongman_audio")   # the game is there, its helper not
    missing_parent = ModuleNotFoundError("No module named 'arcade.games'", name="arcade.games")
    fake_modules(monkeypatch, {
        "copyme": RuntimeError("bad import"), "pong": SyntaxError("bad syntax"), "paint": missing_dep,
        "strongman": missing_helper, "freeze": missing_parent,
        "quickdraw": module_with(game_class("dodge")),               # GAME named after another game
        "dodge": types.ModuleType("fake"),                           # no GAME
        "flap": module_with(game_class("flap")()),                   # GAME is an instance, not the class
        "swat": module_with(type("Swat", (), {"info": "swat"})),     # info is not a GameInfo
        "tug": module_with(tug),
    })
    with caplog.at_level(logging.ERROR, logger="arcade"):
        assert all_games() == [tug]
    skipped = sorted(r.getMessage().split()[1] for r in caplog.records)
    assert skipped == ["copyme", "dodge", "flap", "freeze", "paint", "pong", "quickdraw", "strongman", "swat"]
    assert all(r.name == "arcade" for r in caplog.records)
    tracebacks = [r for r in caplog.records if r.exc_info]
    assert sorted(r.getMessage().split()[1] for r in tracebacks) == ["copyme", "freeze", "paint", "pong", "strongman"]
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
```

- [ ] **Step 2: Run them to verify they fail**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_game.py tests/arcade/test_scores.py`

Expected: `2 errors` during collection, with `ModuleNotFoundError: No module named 'arcade.games'` for `test_game.py` and `ModuleNotFoundError: No module named 'arcade.scores'` for `test_scores.py`.

- [ ] **Step 3: Implement**

`arcade/scores.py`:

```python
"""Best-of-the-night scores and the sessions log (spec 7.5). Neither ever raises into a game for a bad file."""
from __future__ import annotations

import json
import logging
import math
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
    value = float(value)
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
                previous = _entry(value.get("previous"))
                if previous is not None:
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

    SessionLog(None) keeps the records in memory (records) and never writes. A reason outside REASONS raises
    ValueError (a runner bug); a write that fails logs a warning. A duration or score that is not a finite
    number is written as null.
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
        record = {"game": game, "layout": layout, "start": start.isoformat(), "duration": _finite(duration),
                  "players": players, "score": _finite(score), "reason": reason}
        if self.path is None:
            self.records.append(record)
            return record
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a") as f:
                f.write(json.dumps(record) + "\n")
                f.flush()
                os.fsync(f.fileno())
        except OSError as e:
            log.warning("could not append to sessions log %s: %s", self.path, e)
        return record
```

`arcade/game.py`:

```python
"""The game interface (spec 7.1): GameInfo, the Game protocol, the runner's reserved state keys and icons."""
from __future__ import annotations

import math
import random
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, ClassVar, Protocol

import numpy as np

from arcade.canvas import Canvas
from arcade.look import is_real
from arcade.scores import GameScores
from arcade.sensed import Sensed

INPUTS = frozenset({"pose", "blobs", "motion", "audio"})
KINDS = ("control", "toy", "score")               # selects the feel budget set (spec 9.3)
LAYOUTS = frozenset({"128x32", "64x64"})
ICON_SIZE = 16
RUNNER_KEYS = frozenset({"game", "t", "idle", "attract", "hidden", "crashes", "glitch", "flash_held_ticks", "player",
                         "present"})
FX_PREFIX = "fx_"                                 # the effects' keys in state(); runner keys, too
NAME = re.compile(r"[a-z][a-z0-9_]*")             # a registry key is the game's module name
LAYOUT = re.compile(r"[1-9][0-9]*x[1-9][0-9]*")


def reserved(key: str) -> bool:
    """True for a debug_state key a game must not use: the runner's own (it wins in state()) and fx_*."""
    return key in RUNNER_KEYS or key.startswith(FX_PREFIX)


def _text(name: str, value) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"GameInfo.{name} must be a non-empty string, got {value!r}")


@dataclass(frozen=True, eq=False)
class GameInfo:
    """What the lobby, the runner and the tests know about a game before launching it (spec 7.1).

    Validated when built: name a lowercase identifier (the module name), title and verb non-empty, icon
    16x16 bool (kept as a read-only copy), needs a subset of INPUTS, layouts a non-empty set of "WxH" names,
    players 1 or 2, exit_gesture a bool, kind one of KINDS, abandon_seconds None or a finite number over 0.
    A bad value raises ValueError, so a broken game module is skipped at discovery, not launched.
    """

    name: str
    title: str
    verb: str
    icon: np.ndarray
    needs: frozenset[str]
    layouts: frozenset[str] = LAYOUTS
    players: int = 1
    exit_gesture: bool = True
    kind: str = "control"
    abandon_seconds: float | None = None

    def __post_init__(self):
        if not isinstance(self.name, str) or not NAME.fullmatch(self.name):
            raise ValueError(f"GameInfo.name must be a lowercase identifier, got {self.name!r}")
        _text("title", self.title)
        _text("verb", self.verb)
        icon = np.array(self.icon)
        if icon.shape != (ICON_SIZE, ICON_SIZE) or icon.dtype != bool:
            raise ValueError(f"GameInfo.icon must be a {ICON_SIZE}x{ICON_SIZE} bool array, got {icon.shape} "
                             f"{icon.dtype}")
        icon.flags.writeable = False
        object.__setattr__(self, "icon", icon)
        for name in ("needs", "layouts"):
            value = getattr(self, name)
            if isinstance(value, str) or not isinstance(value, (set, frozenset, tuple, list)):
                raise ValueError(f"GameInfo.{name} must be a set of strings, got {value!r}")
            object.__setattr__(self, name, frozenset(value))
        if not self.needs <= INPUTS:
            raise ValueError(f"GameInfo.needs must be a subset of {sorted(INPUTS)}, got "
                             f"{sorted(map(str, self.needs))}")
        if not self.layouts or not all(isinstance(v, str) and LAYOUT.fullmatch(v) for v in self.layouts):
            raise ValueError(f"GameInfo.layouts must be non-empty WxH names, got {sorted(map(str, self.layouts))}")
        if isinstance(self.players, bool) or not isinstance(self.players, int) or self.players not in (1, 2):
            raise ValueError(f"GameInfo.players must be 1 or 2, got {self.players!r}")
        if not isinstance(self.exit_gesture, bool):
            raise ValueError(f"GameInfo.exit_gesture must be a bool, got {self.exit_gesture!r}")
        if self.kind not in KINDS:
            raise ValueError(f"GameInfo.kind must be one of {KINDS}, got {self.kind!r}")
        a = self.abandon_seconds
        if a is not None and (not is_real(a) or not 0.0 < a < math.inf):
            raise ValueError(f"GameInfo.abandon_seconds must be None or a finite number over 0, got {a!r}")


class Game(Protocol):
    """A game (spec 7.1). A fresh instance per launch; state across plays only through scores.

    The runner sets scores (the per-game view Scores.for_game(name, layout)) before reset(). draw() must
    work right after reset(). debug_state() is a small flat dict: a phase key with values from PHASES, score
    when there is one, active on any tick with meaningful input, *_xy for wall coordinates of a visible
    entity, and never a reserved() key. fx is the launch's effects object (arcade/juice.py, core Task 8).
    A game may subclass Game to inherit PHASES, SCENARIOS and CAPTION_KEYS defaults.
    """

    info: ClassVar[GameInfo]
    scores: GameScores
    SCENARIOS: ClassVar[Mapping[str, Callable]] = MappingProxyType({})     # shared by every subclass: read-only
    CAPTION_KEYS: ClassVar[tuple[str, ...]] = ()
    PHASES: ClassVar[tuple[str, ...]] = ("play",)

    def reset(self, size: tuple[int, int], rng: random.Random, fx: Any) -> None: ...
    def update(self, sensed: Sensed, dt: float) -> None: ...
    def draw(self, canvas: Canvas) -> None: ...
    def done(self) -> bool: ...
    def debug_state(self) -> dict: ...


def icon_from_rows(rows: list[str]) -> np.ndarray:
    """A read-only 16x16 bool icon from 16 rows of 16 characters, "#" on and "." off (2 px strokes)."""
    if len(rows) != ICON_SIZE or any(not isinstance(r, str) or len(r) != ICON_SIZE for r in rows):
        raise ValueError(f"an icon is {ICON_SIZE} rows of {ICON_SIZE} characters")
    bad = {ch for row in rows for ch in row} - {"#", "."}
    if bad:
        raise ValueError(f"icon rows use only '#' and '.', got {sorted(bad)}")
    icon = np.array([[ch == "#" for ch in row] for row in rows], dtype=bool)
    icon.flags.writeable = False
    return icon
```

`arcade/games/__init__.py`:

```python
"""The game registry (spec 4.1): MENU_ORDER and guarded discovery.

A game is the module arcade/games/<name>.py with a GAME attribute, the game class, whose info.name is <name>.
Nothing else registers a game: adding one means creating its module and, if it is new to the spec, adding its
name to MENU_ORDER in its place. This file changes in no other way.
"""
from __future__ import annotations

import importlib
import logging

from arcade.game import GameInfo

log = logging.getLogger("arcade")

MENU_ORDER = ("copyme", "pong", "paint", "quickdraw", "dodge", "tug", "flap", "swat", "strongman", "freeze")


def _load(name: str) -> type | None:
    """arcade.games.<name>'s GAME, or None: silently when the module does not exist yet, with a log line when
    it fails to import (any exception, a missing dependency included) or its GAME is not a game called name."""
    module_name = f"{__name__}.{name}"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        if e.name == module_name:
            return None
        log.exception("game %s skipped: its module failed to import", name)
        return None
    except Exception:
        log.exception("game %s skipped: its module failed to import", name)
        return None
    game = getattr(module, "GAME", None)
    info = getattr(game, "info", None)
    if not isinstance(game, type) or not isinstance(info, GameInfo) or info.name != name:
        log.error("game %s skipped: GAME must be a class whose info is a GameInfo named %r", name, name)
        return None
    return game


def all_games() -> list[type]:
    """Every game that imports cleanly, in MENU_ORDER."""
    return [game for game in map(_load, MENU_ORDER) if game is not None]


def get_game(name: str) -> type:
    """The game called name; KeyError if it is not in MENU_ORDER or did not load."""
    for game in all_games():
        if game.info.name == name:
            return game
    raise KeyError(name)
```

- [ ] **Step 4: Run the tests**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_game.py tests/arcade/test_scores.py`

Expected: `51 passed` (game 39, of which 31 are `test_game_info_validates` cases, and scores 12).

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`

Expected: `293 passed`, no skips.

- [ ] **Step 5: Commit**

```bash
git add arcade/game.py arcade/games/__init__.py arcade/scores.py tests/arcade/test_game.py tests/arcade/test_scores.py
git commit -m "feat(arcade): GameInfo and the Game protocol, guarded registry in MENU_ORDER, nightly scores and the sessions log (core Task 7)" -m "A game module not written yet is skipped silently; a broken one is logged and skipped. Scores never raise into a game over a bad or unwritable file, and numpy numbers are numbers." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Flash governor and brightness limiter (core Task 8 part, spec 7.6)

**Files:**
- Create: `arcade/flash.py`, `arcade/brightness.py`
- Test: `tests/arcade/test_flash.py`, `tests/arcade/test_brightness.py`

**Interfaces:**
- Consumes:
  - Task 1's `look.is_real` and `look.light_lut`, and iteration 3's `look.gamma_lut` and `look.MONITOR_GAMMA` (`gamma_lut` in tests);
  - `config.ArcadeConfig` and `config.HHMM`;
  - `Canvas` and the `font5x7` and `size` fixtures, in tests.
- Produces:
  - In `arcade/flash.py`:
    - `FPS = 30`, `THRESHOLD = 0.1`, `BUDGET = 6`, `RED_SHARE = 0.8`, `REC709`, `WINDOW = 32`, `SMALL_AREA = 0.1`, `FIELD_AREA = 0.125` and `BACKSTOP_PASSES = 8`.
    - `signals(frame, gamma) -> np.ndarray`, of shape (3, h, w): luminance, red-doubled luminance and red excess, in light.
    - `largest_share(mask, window=WINDOW) -> float` and `square_means(s, window=WINDOW) -> np.ndarray` (every square, cut to the wall).
    - `FlashGovernor(height, width, gamma=2.2, fps=FPS, threshold=THRESHOLD, budget=BUDGET)`, with `.held_ticks`, `.fps` and `apply(frame) -> np.ndarray`.
    - `flash_area(frames, gamma=2.2, fps=FPS, threshold=THRESHOLD, budget=BUDGET) -> float`.
    - `concurrent_area(frames, gamma=2.2, fps=FPS, threshold=THRESHOLD, budget=BUDGET, window=WINDOW) -> float`.
    - `square_flashes(frames, gamma=2.2, fps=FPS, threshold=THRESHOLD, window=WINDOW) -> int`.
    - On governed output, `square_flashes(out) <= budget` always (the square backstop), and every pixel makes at most `budget` transitions in any `fps + 1` frames unless it is part of a small flash.
  - In `arcade/brightness.py`:
    - `MIN_FACTOR = 0.5`, `RELEASE = THRESHOLD / 10`, `LUX_RELEASE = 1.5`, `LUX_HOLD_S = 10.0` and `apl(frame, gamma) -> float`.
    - `BrightnessLimiter(cfg, clock=datetime.now, lux=None)`, with `.factor`, `.scaled_ticks`, `is_night() -> bool`, `cap() -> float` and `apply(frame) -> np.ndarray`. `clock` returns local time; the runner passes a local clock, never its monotonic one.
  - The runner (it05) calls the limiter, then the governor, then pushes (Q11).
  - Both `apply` methods raise `ValueError` for a frame of the wrong shape or dtype.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_flash.py`:

```python
import logging
import math
import statistics
import time
import zlib

import numpy as np
import pytest

from arcade.canvas import Canvas
from arcade.flash import (BACKSTOP_PASSES, BUDGET, FIELD_AREA, FPS, RED_SHARE, SMALL_AREA, THRESHOLD, WINDOW,
                          FlashGovernor, concurrent_area, flash_area, largest_share, signals, square_flashes,
                          square_means)
from arcade.look import gamma_lut, light_lut


def strobe(hz, w, h, n=90, color=(255, 255, 255), cols=None, off=(0, 0, 0), fps=FPS):
    """A strobe of hz flashes a second at fps: color for the first half of each period and off for the
    second (the review prototype), over the first cols columns (all of them by default)."""
    frames = []
    for i in range(n):
        f = np.zeros((h, w, 3), np.uint8)
        f[:, :cols] = color if int(i * 2 * hz / fps) % 2 == 0 else off
        frames.append(f)
    return frames


def govern(frames, gamma=2.2, **kwargs):
    h, w = frames[0].shape[:2]
    g = FlashGovernor(h, w, gamma, **kwargs)
    return [g.apply(f) for f in frames], g


def changes(frames, y, x):
    """The frames at which one pixel's value changes (from the frame before)."""
    v = [int(f[y, x].sum()) for f in frames]
    return [i for i in range(1, len(v)) if v[i] != v[i - 1]]


def most_changes_in_a_second(frames, y, x, n=FPS):
    """The most changes of one pixel's value in any n consecutive frames."""
    c = changes(frames, y, x)
    return max(sum(1 for i in c if start <= i < start + n) for start in range(len(frames)))


def test_15hz_white_strobe_held_to_3_per_second(size):
    w, h = size
    raw = strobe(15, w, h)
    out, g = govern(raw)
    assert flash_area(raw) == 1.0 and flash_area(out) == 0.0
    assert most_changes_in_a_second(raw, 0, 0) == 30                  # the strobe changes every frame
    assert most_changes_in_a_second(out, 0, 0) == 6 == BUDGET        # 3 flashes a second get through, no more
    assert most_changes_in_a_second(out, h - 1, w - 1, FPS + 1) == 6  # the window is the 30 frames before
    assert g.held_ticks > 0 and g.held_ticks == sum(not np.array_equal(a, b) for a, b in zip(raw, out))
    assert all(set(np.unique(f)) <= {0, 255} for f in out)          # held pixels keep a previous frame's value


def test_3_flashes_a_second_pass_and_4_do_not():
    w, h = 16, 8
    for hz in (1, 2, 2.9):
        raw = strobe(hz, w, h)
        out, g = govern(raw)
        assert g.held_ticks == 0 and all(a is b for a, b in zip(raw, out)), hz
        assert flash_area(raw) == 0.0, hz
    # Exactly 3 a second is the limit: every flash gets through, but a transition waits a frame when the 30
    # frames before already hold 6 (one frame of margin for a late tick, loop decision 11).
    raw = strobe(3, w, h, n=150)
    out, g = govern(raw)
    assert flash_area(raw) == 0.0 and g.held_ticks > 0
    assert len(changes(out, 3, 3)) == len(changes(raw, 3, 3)) and most_changes_in_a_second(out, 3, 3, FPS + 1) == 6
    raw = strobe(4, w, h)
    out, g = govern(raw)
    assert g.held_ticks > 0 and flash_area(raw) == 1.0 and flash_area(out) == 0.0
    assert most_changes_in_a_second(out, 3, 3) == 6
    seventh = grey([255, 0] * 4 + [0] * 5)                           # a 7th transition with 6 in the frames before
    out, g = govern(seventh)
    assert concurrent_area(seventh) == 1.0 and flash_area(seventh) == 1.0 and g.held_ticks == 6   # white to the end
    assert concurrent_area(out) == 0.0 and flash_area(out) == 0.0


def test_window_and_budget_follow_the_keywords():
    # The runner ticks at cfg.fps: at 60 fps a second is 60 frames, so 2 flashes a second pass and 4 do not.
    for hz, flashing in ((2, False), (4, True)):
        raw = strobe(hz, 16, 8, n=180, fps=60)
        out, g = govern(raw, fps=60)
        assert (g.held_ticks > 0) is flashing and flash_area(raw, fps=60) == float(flashing), hz
        assert flash_area(out, fps=60) == 0.0 and most_changes_in_a_second(out, 3, 3, 61) <= 6, hz
    five = strobe(5, 16, 8, n=180, fps=60)                          # 5 a second at 60 fps: 10 changes in 60 frames
    assert flash_area(five, fps=30) == 0.0 and flash_area(five, fps=60) == 1.0   # a 30-frame window misses it
    assert govern(five, fps=30)[1].held_ticks == 0 and govern(five, fps=60)[1].held_ticks > 0
    two = strobe(2, 16, 8)                                          # 4 transitions a second
    out, g = govern(two, budget=2)
    assert flash_area(two) == 0.0 and flash_area(two, budget=2) == 1.0
    assert concurrent_area(two) == 0.0 and concurrent_area(two, budget=2) == 1.0
    assert g.held_ticks > 0 and flash_area(out, budget=2) == 0.0 and most_changes_in_a_second(out, 0, 0) == 2
    grey = strobe(15, 16, 8, color=(60, 60, 60))                   # a swing of 0.235 of light
    assert flash_area(grey) == 1.0 and flash_area(grey, threshold=0.3) == 0.0
    assert govern(grey, threshold=0.3)[1].held_ticks == 0 and govern(grey)[1].held_ticks > 0


TITLES = "COPY ME  PONG  PAINT  QUICKDRAW  DODGE  TUG  FLAP  SWAT  STRONGMAN  FREEZE"


def scrolling(font, w, h, scale, speed, text=TITLES):
    """Static text, a 4x4 ball at 60 px a second and text scrolling right to left at speed px a second
    until it has gone by."""
    frames = []
    for i in range(int((w + len(text) * 6 * scale) * FPS / speed)):
        c = Canvas(w, h, font)
        c.text(2, 1, "SCORE 12", (255, 200, 0))                      # static
        c.fill_rect((i * 2) % (w - 4), 10, 4, 4, (255, 255, 255))    # the ball
        c.text(w - int(i * speed / FPS), h - 15, text, (0, 255, 255), scale=scale)
        frames.append(c.frame.copy())
    return frames


def test_static_and_moving_sprite_pass_bit_identical(font5x7, size):
    # The door titles scroll at scale 2: at 10 px a second no pixel of any title changes more than 6 times
    # in a second, so the governor never touches them.
    w, h = size
    frames = scrolling(font5x7, w, h, scale=2, speed=10)
    out, g = govern(frames)
    assert g.held_ticks == 0 and all(a is b for a, b in zip(frames, out))
    assert flash_area(frames) == 0.0


def test_fine_text_scrolling_fast_is_a_small_area_and_passes(font5x7, size):
    # At 20 to 30 px a second the strokes of 1x and 2x text turn pixels on and off more than 3 times a second
    # (5 to 29% of the wall, pixel by pixel), but a square never has 10% of its pixels going the same way
    # at once and its mean light hardly moves: the flash is small (Q13) and nothing is held.
    w, h = size
    for scale, speed in ((1, 20), (1, 30), (2, 20), (2, 25), (2, 30)):
        frames = scrolling(font5x7, w, h, scale, speed, text="COPY ME  QUICKDRAW")
        out, g = govern(frames)
        assert g.held_ticks == 0 and all(a is b for a, b in zip(frames, out)), (scale, speed)
        assert flash_area(frames) > 0.05 and concurrent_area(frames) < 0.09, (scale, speed)   # measured 0.08
        assert square_flashes(frames) <= 2, (scale, speed)
    frames = scrolling(font5x7, w, h, 2, 60, text="COPY ME  QUICKDRAW")    # twice as fast: a 2 px jump a frame
    out, g = govern(frames)
    assert concurrent_area(frames) > SMALL_AREA and g.held_ticks > 0 and concurrent_area(out) < SMALL_AREA


def test_a_flash_just_over_the_small_area_is_held():
    assert WINDOW == 32 and SMALL_AREA == 0.1                        # 102 pixels of a 32 x 32 square are under
    tenth = grey([128, 0] * 45, h=10, w=10)
    for f in tenth:
        f[1:] = 0                                                    # a row of a 10 x 10 wall: exactly a tenth
    out, g = govern(tenth)
    assert concurrent_area(tenth) == pytest.approx(0.1) and g.held_ticks > 0 and flash_area(out) == 0.0
    blink = strobe(15, 128, 32, cols=1)
    for f in blink:
        f[1:] = 0
    for f in blink[60:]:
        f[:, 64:] = 255                                              # half the wall lights once as the pixel does
    out, g = govern(blink)
    assert g.held_ticks == 0 and concurrent_area(blink) == pytest.approx(1 / 1024)   # only flashing pixels count
    for color, off in (((255, 255, 255), (0, 0, 0)), ((87, 0, 0), (0, 0, 255))):   # red against blue counts too
        for n, held in ((102, False), (103, True)):
            frames = strobe(15, 64, 32, color=color, off=off)
            for f in frames:
                f[:] = 0
            for f, src in zip(frames, strobe(15, 1, n, color=color, off=off)):
                f[:10, :10] = src[:100, 0].reshape(10, 10, 3)
                f[10, :n - 100] = src[100:, 0]
            out, g = govern(frames)
            assert (g.held_ticks > 0) is held, (color, n)
            assert flash_area(frames) == pytest.approx(n / 2048) and concurrent_area(frames) == pytest.approx(n / 1024)
            assert flash_area(out) == (0.0 if held else n / 2048), (color, n)
    one = strobe(15, 3, 3, cols=1, color=(128, 128, 128))
    for f in one:
        f[1:] = 0                                                    # one pixel of 9, held alone: the mean moves 0.056
    out, g = govern(one)
    assert g.held_ticks > 0 and g.held_ticks == sum(not np.array_equal(a, b) for a, b in zip(one, out))


def test_many_small_flashes_add_up_and_are_held():
    one = strobe(15, 128, 32)
    for f in one:
        f[:, 2:] = 0                                                 # a 32 x 2 strip: 6% of its square
    out, g = govern(one)
    assert g.held_ticks == 0 and flash_area(out) == pytest.approx(64 / 4096)
    assert square_flashes(one) == 0 and square_flashes(one, window=8) == 30   # a quarter of an 8 x 8 square
    dots = strobe(15, 128, 32)
    for f in dots:
        f[(np.arange(32) % 4 >= 2)] = 0
        f[:, (np.arange(128) % 4 >= 2)] = 0                          # 2 x 2 dots every 4 px: a quarter of the wall
    out, g = govern(dots)
    assert concurrent_area(dots) == 0.25 and g.held_ticks > 0 and flash_area(out) == 0.0
    board = np.indices((32, 128)).sum(axis=0) % 2 == 0
    reversal = [np.where(board ^ (i % 2 == 1), 255, 0).astype(np.uint8)[..., None].repeat(3, axis=2)
                for i in range(90)]                                  # a checkerboard reversing: mean light constant
    out, g = govern(reversal)
    assert concurrent_area(reversal) == 0.5 and g.held_ticks > 0 and flash_area(out) == 0.0
    assert square_flashes(reversal) == 0                             # held on the pixels going the same way


def test_a_flash_spread_over_frames_is_held():
    # Three sets of columns, each 9% of a square, light one frame after another and go out the same way: no
    # frame turns 10% of a square one way, but each square's mean light swings 0.27 five times a second.
    x = np.arange(128)
    frames = []
    for i in range(150):
        p = i % 6
        f = np.zeros((32, 128, 3), np.uint8)
        for k in (range(p) if p <= 3 else range(p - 3, 3)):
            f[:, x % 11 == k] = 255
        frames.append(f)
    out, g = govern(frames)
    assert concurrent_area(frames) < SMALL_AREA and square_flashes(frames) == 10 and g.held_ticks > 0
    assert square_flashes(out) <= BUDGET              # the square backstop holds the mean too (B7)
    red = [np.where(f > 0, np.array([255, 0, 0], np.uint8), f) for f in frames]
    assert govern(red)[1].held_ticks > 0                            # red means swing 0.06 of luminance, 0.12 doubled
    # At exactly 3 a second each square's mean makes its 7th transition with 6 in the frames before: held.
    three = []
    for i in range(90):
        f = np.zeros((32, 128, 3), np.uint8)
        for k in range(3):
            if k + 1 <= i % 10 < k + 6:
                f[:, x % 11 == k] = 255
        three.append(f)
    assert concurrent_area(three) < SMALL_AREA and govern(three)[1].held_ticks > 0


def turns(groups, w, h, n=150, period=31, burst=6):
    """groups interleaved dithers take turns: each flashes 3 times in burst frames, then rests while the next
    takes its turn. Every pixel stays within its budget, while every square's mean light flashes."""
    y, x = np.indices((h, w))
    group = (x + 2 * y) % groups
    frames = []
    for i in range(n):
        f = np.zeros((h, w, 3), np.uint8)
        k, j = divmod(i % period, burst)
        if k < groups and j % 2 == 0:
            f[group == k] = 255
        frames.append(f)
    return frames


def test_pixels_taking_turns_are_held_by_the_square(size, caplog):
    # 5 dithers flash the whole wall's mean light 0.2 at 15 Hz, 2 dithers swing it 0.5 six times a second, and no
    # pixel is over its own budget. The square backstop (B7) holds whole squares until no square's mean flashes
    # past its budget: here every square flashes, so every frame shows the input or the previous output whole.
    w, h = size
    for groups in (5, 2):
        frames = turns(groups, w, h)
        with caplog.at_level(logging.WARNING, logger="arcade"):
            out, g = govern(frames)
        assert flash_area(frames) == 0.0 and concurrent_area(frames) == 0.0, groups
        assert square_flashes(frames) >= 12 and g.held_ticks > 0 and square_flashes(out) <= BUDGET, groups
        assert all(np.array_equal(o, f) or np.array_equal(o, p) for o, f, p in zip(out[1:], frames[1:], out)), groups
    assert not caplog.records                                        # the backstop ends by itself, never capped


def grating(w, h, every, n=150):
    """1 px lines every `every` px over the whole wall, reversing every frame (15 Hz)."""
    x = np.arange(w)
    frames = [np.zeros((h, w, 3), np.uint8) for _ in range(n)]
    for i, f in enumerate(frames):
        f[:, x % every == (0 if i % 2 else every // 2)] = 255
    return frames


def test_a_reversing_grating_is_held_by_the_field_cap(size):
    # 1 px lines every 11 px reversing: 12 pairs across 128 px, and 18.75% of the wall flips over budget in each
    # frame, though no square has 10% going one way and every square's mean is constant. Over-budget flips on
    # FIELD_AREA of the wall or more are held (Q15; BT.1702-3 Guideline 2 counts more than 5 pairs).
    assert FIELD_AREA == 0.125
    w, h = size
    frames = grating(w, h, 11)
    out, g = govern(frames)
    assert concurrent_area(frames) < SMALL_AREA and square_flashes(frames) == 0 and flash_area(frames) == 0.1875
    assert g.held_ticks > 0 and flash_area(out) == 0.0
    frames = grating(w, h, 16)                                       # 8 pairs: exactly 12.5% of the wall
    out, g = govern(frames)
    assert flash_area(frames) == FIELD_AREA and g.held_ticks > 0 and flash_area(out) == 0.0
    for f in frames:
        f[0, 0] = 0                                                  # one pixel less: under the cap, not held
    out, g = govern(frames)
    assert g.held_ticks == 0 and all(a is b for a, b in zip(frames, out))


def test_titles_scrolling_pass_under_the_field_cap(font5x7, size):
    # The ten titles at 1x and 2x, 20 to 30 px a second: over-budget pixels flip on at most 9.9% of the wall in
    # a frame (1x at 30 px a second on 128x32), under FIELD_AREA, so nothing is held.
    w, h = size
    for scale, speed in ((1, 20), (1, 30), (2, 20), (2, 25), (2, 30)):
        frames = scrolling(font5x7, w, h, scale, speed)
        out, g = govern(frames)
        assert g.held_ticks == 0 and all(a is b for a, b in zip(frames, out)), (scale, speed)


def test_the_backstop_gives_up_by_holding_the_whole_frame(monkeypatch, caplog):
    # A wall governor never hangs: when a square still flashes after BACKSTOP_PASSES passes (here a square
    # tracker whose first square always flips), every pixel of the wall keeps the previous output, which flips
    # nothing, and it is logged once.
    assert BACKSTOP_PASSES == 8
    g = FlashGovernor(32, 64)
    g.apply(np.zeros((32, 64, 3), np.uint8))
    calls = []

    def always(v):
        calls.append(1)
        flip = np.zeros(v.shape, bool)
        flip[:, 0, 0] = True                                         # the left square, never the right half
        return flip, flip

    monkeypatch.setattr(g._squares, "flips", always)
    out = None
    with caplog.at_level(logging.WARNING, logger="arcade"):
        for i in range(12):
            f = np.full((32, 64, 3), 20 * (i + 1), np.uint8)
            prev, held, calls[:] = out, g.held_ticks, []
            out = g.apply(f)
            if i >= BUDGET:                                          # the squares' windows are over budget
                assert len(calls) == BACKSTOP_PASSES and np.array_equal(out, prev) and g.held_ticks == held + 1, i
    assert not np.array_equal(out, f)
    assert len(caplog.records) == 1 and "backstop" in caplog.records[0].getMessage()
    assert np.array_equal(g._shown, signals(out, 2.2)) and g._square_window.count.max() == BUDGET   # nothing counted


def test_governor_copes_with_a_reused_buffer():
    # The runner draws every tick into the same canvas array: the governor keeps its own copy of what it showed.
    raw = strobe(15, 16, 8)
    expected = [f.copy() for f in govern(raw)[0]]
    g, buf, out = FlashGovernor(8, 16), np.zeros((8, 16, 3), np.uint8), []
    for f in raw:
        buf[:] = f
        out.append(g.apply(buf).copy())
    assert all(np.array_equal(a, b) for a, b in zip(out, expected)) and flash_area(out) == 0.0


def test_saturated_red_counts_double():
    assert RED_SHARE == 0.8 and THRESHOLD == 0.1
    px = np.array([[[255, 0, 0], [255, 63, 0], [255, 64, 0], [0, 255, 0], [0, 0, 0], [128, 32, 0], [0, 0, 255]]],
                  np.uint8)
    plain, red, excess = signals(px, 2.2)[:, 0]
    assert plain[0] == pytest.approx(0.2126, rel=1e-5) and red[0] == pytest.approx(2 * 0.2126, rel=1e-5)
    assert red[1] == pytest.approx(2 * (0.2126 + 0.7152 * 63 / 255), rel=1e-5)     # red is 80.2% of the light
    assert red[2] == pytest.approx(0.2126 + 0.7152 * 64 / 255, rel=1e-5)           # 79.9%: counted once
    assert red[3] == plain[3] == pytest.approx(0.7152, rel=1e-5) and red[4] == 0.0
    assert red[5] == pytest.approx(2 * (0.2126 * 128 + 0.7152 * 32) / 255, rel=1e-5)   # exactly 80%: counts
    assert excess[0] == pytest.approx(1.0) and excess[1] == pytest.approx(192 / 255) and excess[3] == 0.0
    assert plain[6] == red[6] == pytest.approx(0.0722, rel=1e-6) and excess[6] == 0.0   # Rec. 709 blue
    # A dim red strobe swings 0.075 of light: under the threshold as luminance, over it counted double.
    dim_red = strobe(15, 8, 4, color=(90, 0, 0))
    out, g = govern(dim_red)
    assert flash_area(dim_red) == 1.0 and g.held_ticks > 0 and flash_area(out) == 0.0
    blue = strobe(15, 8, 4, color=(0, 0, 255))                       # 0.072 of light, not red: never a flash
    out, g = govern(blue)
    assert flash_area(blue) == 0.0 and g.held_ticks == 0


RED_PAIRS = (((87, 0, 0), (0, 0, 255)),        # the Pokemon strobe: luminance and doubled luminance barely move
             ((255, 0, 0), (0, 152, 0)),       # doubling red lifts it onto the green: luminance moves 0.21
             ((189, 0, 0), (255, 66, 0)),
             ((255, 0, 0), (255, 60, 60)))


def test_red_traded_against_another_colour_is_a_flash():
    for color, off in RED_PAIRS:
        for hz in (15, 12):
            raw = strobe(hz, 128, 32, color=color, off=off)
            out, g = govern(raw)
            assert flash_area(raw) == 1.0 and g.held_ticks > 0 and flash_area(out) == 0.0, (color, off, hz)
    # Each measure catches a swing the other two miss.
    for a, b, which in (((51, 10, 0), (89, 38, 26), 0), ((128, 13, 13), (128, 0, 33), 1), ((87, 0, 0), (0, 0, 255), 2),
                        ((200, 0, 0), (200, 0, 40), 2)):                # blue alone takes red's excess away
        swing = np.abs(np.subtract(*signals(np.array([[a, b]], np.uint8), 2.2)[:, 0].T))
        assert [bool(s >= THRESHOLD) for s in swing] == [k == which for k in range(3)], (a, b)
        raw = strobe(15, 8, 4, color=a, off=b)
        out, g = govern(raw)
        assert flash_area(raw) == 1.0 and g.held_ticks > 0 and flash_area(out) == 0.0, (a, b)


def test_held_pixels_are_measured_as_shown():
    # A pixel held on one signal keeps its other signals' extremes where the shown colour put them, not where the
    # input went: random colours on four large blocks never get past the budget on any signal.
    seed = zlib.crc32(b"flash-held")
    rng = np.random.default_rng(seed)
    palette = np.array([(0, 0, 0), (255, 255, 255), (255, 0, 0), (0, 152, 0), (0, 0, 255), (87, 0, 0), (255, 66, 0)],
                       np.uint8)
    for trial in range(20):
        frames = [palette[rng.integers(0, len(palette), (2, 2))].repeat(4, axis=0).repeat(8, axis=1) for _ in range(60)]
        out, g = govern(frames)
        assert g.held_ticks > 0 and flash_area(out) == 0.0, (trial, seed)
    # The squares count what is shown too: a half-wall strobe brought down to the budget no longer holds a
    # one-pixel blinker elsewhere (measured: 131 of its 179 changes pass; counting the input, 50 would; without
    # the square flag, 155 would).
    frames = strobe(3.5, 128, 32, n=180, cols=64)
    for i, f in enumerate(frames):
        f[0, 127] = 255 * (i % 2 == 0)
    out, g = govern(frames)
    assert g.held_ticks > 0 and len(changes(out, 0, 127)) > 120 and flash_area(out) == pytest.approx(1 / 4096)
    assert len(changes(out, 0, 127)) < 140                          # the square flag still holds the blinker (N26)


def grey(values, h=4, w=8):
    return [np.full((h, w, 3), v, np.uint8) for v in values]


def test_transitions_follow_extremes_not_steps():
    # A fade is one transition however many frames it takes: white to black in 8 steps of 0.125 and back,
    # about 2 fades a second, passes untouched.
    fade = [255 - 32 * i for i in range(8)] + [32 * i for i in range(8)]
    frames = grey((fade * 6)[:90])
    out, g = govern(frames)
    assert g.held_ticks == 0 and all(a is b for a, b in zip(frames, out)) and flash_area(frames) == 0.0
    # Steps under the threshold still add up: 0 to 0.3 of light and back in steps of 0.075 is a 3.75 Hz flash.
    tri = [0, 19, 38, 57, 76, 57, 38, 19]
    frames = grey((tri * 12)[:90])
    out, g = govern(frames)
    assert flash_area(frames) == 1.0 and g.held_ticks > 0 and flash_area(out) == 0.0
    # A flicker at the top of a fade swings from the fade's peak, not from where the fade began.
    frames = grey([32 * i for i in range(8)] + [255, 200] * 41)
    out, g = govern(frames)
    assert flash_area(frames) == 1.0 and g.held_ticks > 0 and flash_area(out) == 0.0
    # The first swing counts either way: a slow fall from the first frame, then a rise, is two transitions.
    fall = grey([128 - 8 * i for i in range(16)] + [128])
    assert flash_area(fall, budget=1) == 1.0 and flash_area(fall[::-1], budget=1) == 1.0
    rise = grey([8 * i for i in range(17)] + [0])                    # and a slow rise from the first frame, then a fall
    assert flash_area(rise, budget=1) == 1.0
    # A swing of exactly the threshold is a transition, up or down: red (51, 0, 0) is its own excess.
    exact = strobe(15, 8, 4, color=(51, 0, 0))
    th = float(light_lut(2.2)[51])
    assert flash_area(exact, threshold=th) == 1.0 and govern(exact, threshold=th)[1].held_ticks > 0
    assert flash_area(exact, threshold=th * 1.001) == 0.0


def test_governor_follows_gamma():
    # The same bytes are less light when the card applies gamma (gamma 1.0): a grey swing of 0 to 60 is 0.235
    # of light on an uncorrected wall and 0.043 on a gamma-correcting one.
    grey = strobe(15, 8, 4, color=(60, 60, 60))
    assert flash_area(grey, gamma=2.2) == 1.0 and flash_area(grey, gamma=1.0) == 0.0
    assert govern(grey, gamma=1.0)[1].held_ticks == 0 and govern(grey, gamma=2.2)[1].held_ticks > 0


def test_only_the_flashing_part_is_held(font5x7):
    w, h = 32, 16
    frames = []
    for i in range(60):
        f = np.zeros((h, w, 3), np.uint8)
        if i % 2 == 0:
            f[:, :8] = 255                                           # a strobing strip on the left
        f[8:12, 12 + i % 16: 16 + i % 16] = (0, 255, 0)              # a sprite moving on the right
        frames.append(f)
    out, g = govern(frames)
    assert g.held_ticks > 0
    assert all(np.array_equal(a[:, 8:], b[:, 8:]) for a, b in zip(frames, out))
    assert flash_area(out) == 0.0 and flash_area(frames) == pytest.approx(8 / 32)


def test_squares_are_every_square():
    mask = np.zeros((32, 128), bool)
    mask[5:15, 100:110] = True
    assert largest_share(mask) == 100 / 1024 and largest_share(mask, 10) == 1.0 and largest_share(mask, 20) == 0.25
    assert largest_share(mask[:8, :16] | True, 32) == 1.0                   # a small wall: the square is cut to it
    assert largest_share(np.zeros((8, 8), bool)) == 0.0
    s = np.zeros((3, 64, 64), np.float32)
    s[1, 40:50, 3:13] = 1.0
    means = square_means(s)
    assert means.shape == (3, 33, 33) and means[0].max() == 0.0 and means[1].max() == pytest.approx(100 / 1024)
    assert means[1, 32, 0] == pytest.approx(100 / 1024) and means[1, 0, 0] == 0.0 and means[1, 18, 13] == 0.0
    assert square_means(s[:, :8, :16]).shape == (3, 1, 1) and square_means(s, 8).shape == (3, 57, 57)
    assert np.allclose(square_means(np.ones((3, 8, 16), np.float32)), 1.0)   # a cut square's mean is over its area


def test_light_lut_matches_the_led_preview():
    for gamma in (1.0, 2.2, 1.8):
        lut = light_lut(gamma)
        shown = (gamma_lut(gamma).astype(np.float64) / 255) ** 2.2   # what the led look's monitor emits
        assert np.abs(lut - shown).max() < 0.01 and not lut.flags.writeable, gamma
    assert light_lut(2.2)[128] == pytest.approx(128 / 255) and light_lut(1.0)[128] == pytest.approx((128 / 255) ** 2.2)


def test_governor_rejects_bad_input():
    g = FlashGovernor(4, 8)
    for bad in (np.zeros((8, 4, 3), np.uint8), np.zeros((4, 8, 3), np.float32), np.zeros((4, 8), np.uint8)):
        with pytest.raises(ValueError):
            g.apply(bad)
    for kwargs in (dict(gamma=0.0), dict(gamma=float("nan")), dict(gamma=None), dict(gamma=[2.2]), dict(fps=1),
                   dict(budget=0), dict(threshold=0.0), dict(threshold=None), dict(threshold=math.inf),
                   dict(threshold=math.nan), dict(fps=30.0), dict(budget=True)):
        with pytest.raises(ValueError):
            FlashGovernor(4, 8, **kwargs)
    FlashGovernor(4, 8, fps=2, budget=1, threshold=np.float32(0.5))
    first = np.full((4, 8, 3), 200, np.uint8)
    assert g.apply(first) is first and g.held_ticks == 0             # the first frame passes


@pytest.mark.perf
def test_governor_under_half_ms_at_128x32():
    seed = zlib.crc32(b"flash-perf")
    rng = np.random.default_rng(seed)
    frames = [rng.integers(0, 256, (32, 128, 3), dtype=np.uint8) for _ in range(40)]
    g = FlashGovernor(32, 128)
    for f in frames[:10]:
        g.apply(f)
    times = []
    for f in frames[10:]:
        start = time.perf_counter()
        g.apply(f)
        times.append(time.perf_counter() - start)
    assert g.held_ticks > 0                                          # the held path is the one timed
    assert statistics.median(times) < 0.0005, f"median {statistics.median(times) * 1000:.3f} ms, seed={seed}"
```

`tests/arcade/test_brightness.py`:

```python
import dataclasses
import logging
import math
import zlib
from datetime import datetime, timedelta

import numpy as np
import pytest

from arcade.brightness import LUX_HOLD_S, LUX_RELEASE, MIN_FACTOR, RELEASE, BrightnessLimiter, apl
from arcade.config import ArcadeConfig
from arcade.flash import BUDGET, SMALL_AREA, FlashGovernor, concurrent_area, flash_area, square_flashes


class Clock:
    """A settable local clock."""

    def __init__(self, when: str = "2026-11-11T21:00"):
        self.set(when)

    def __call__(self) -> datetime:
        return self.now

    def set(self, when: str) -> None:
        self.now = datetime.fromisoformat(when)

    def tick(self, seconds: float = 1 / 30) -> None:
        self.now += timedelta(seconds=seconds)


def limiter(clock=None, lux=None, **over):
    return BrightnessLimiter(dataclasses.replace(ArcadeConfig(), **over), clock or Clock(), lux)


def frame(value, h=32, w=128):
    return np.full((h, w, 3), value, np.uint8)


def test_apl_is_the_mean_light_after_gamma():
    assert apl(frame(0), 2.2) == 0.0 and apl(frame(255), 2.2) == pytest.approx(1.0)
    assert apl(frame(128), 2.2) == pytest.approx(128 / 255, rel=1e-6)        # the card sends bytes as they are
    assert apl(frame(128), 1.0) == pytest.approx((128 / 255) ** 2.2, rel=1e-5)  # the card applies gamma
    half = frame(0)
    half[:, :64, 0] = 255                                                   # red on half the wall: 1/6 of the light
    assert apl(half, 2.2) == pytest.approx(1 / 6, rel=1e-6)


def test_frame_under_cap_passes_identical():
    lim = limiter()
    dim = frame(0)
    dim[:, :, 1] = 30                                                       # APL 0.039, under the day cap 0.12
    assert lim.apply(dim) is dim and lim.factor == 1.0 and lim.scaled_ticks == 0
    at_cap = frame(0)
    at_cap[:4, :, :] = 255
    at_cap[4:5, :32, :] = 255                                               # 544 of 4096 pixels white: APL 0.1328
    lim = limiter(apl_cap_day=544 / 4096)
    assert lim.apply(at_cap) is at_cap and lim.scaled_ticks == 0            # exactly at the cap is not over it


def test_white_frame_scaled_not_below_half():
    lim = limiter()
    out = lim.apply(frame(255))
    assert MIN_FACTOR == 0.5 and lim.factor == 0.5 and lim.scaled_ticks == 1
    assert out.dtype == np.uint8 and np.all(out == 128)                     # 255 * 0.5 rounds to 128
    assert apl(out, 2.2) == pytest.approx(128 / 255, rel=1e-6)             # over the cap: the floor wins
    f = frame(255)
    f[0, 0] = 5
    assert limiter().apply(f)[0, 0, 0] == 3                                 # 2.5 rounds half up, not to even


def test_factor_falls_at_once_and_rises_slowly():
    assert RELEASE == pytest.approx(0.01)                                  # a tenth of a flash's swing a tick
    lim = limiter()
    lim.apply(frame(255))
    black = frame(0)
    factors = []
    for _ in range(50):
        out = lim.apply(black)
        factors.append(lim.factor)
        assert np.all(out == 0)
    assert factors[0] == pytest.approx(0.51) and factors[-2] == pytest.approx(0.99) and factors[-1] == 1.0
    assert lim.scaled_ticks == 50 and lim.apply(black) is black             # back to 1.0: the frame as it is
    f = frame(0)
    f[:6, :, :] = 200                                                       # needs 0.816: falls there at once
    lim.apply(f)
    assert lim.factor == pytest.approx(0.12 / apl(f, 2.2))
    lim.apply(frame(255))
    assert lim.factor == 0.5
    lim.apply(f)
    assert lim.factor == pytest.approx(0.51)                                # needs more: rises by RELEASE
    lim.apply(frame(255))
    lim.apply(frame(61))                                                    # needs 0.502: rises to it, not past
    assert lim.factor == pytest.approx(0.12 / apl(frame(61), 2.2)) and lim.factor < 0.505


def test_frame_over_cap_lands_on_the_cap():
    f = frame(0)
    f[:6, :, :] = 200                                                       # APL 0.1471 against a cap of 0.12
    lim = limiter()
    out = lim.apply(f)
    assert lim.factor == pytest.approx(0.12 / apl(f, 2.2))
    assert abs(apl(out, 2.2) - 0.12) < 1 / 255 and np.all(out[6:] == 0)     # black stays black
    assert np.all(out[:6] == math.floor(200 * lim.factor + 0.5))            # one lookup table for every channel
    assert f[0, 0, 0] == 200                                                # the input is not changed


def test_scaling_follows_gamma():
    # Grey 128 is 0.502 of the light on an uncorrected wall but 0.2195 when the card applies gamma (1.0).
    lim = limiter(gamma=1.0)
    out = lim.apply(frame(128))
    assert lim.factor == pytest.approx(0.12 / (128 / 255) ** 2.2, rel=1e-5)
    assert np.all(out == 97) and abs(apl(out, 1.0) - 0.12) < 0.002         # 128 * 0.547 ** (1 / 2.2) = 97.3
    lim = limiter(gamma=2.2)
    assert np.all(lim.apply(frame(128)) == 64) and lim.factor == 0.5        # 0.239 would be under the floor


def test_night_by_clock_spans_midnight():
    clock = Clock()
    lim = limiter(clock)                                                    # the defaults: 01:00 to 06:00
    for when, night in (("2026-11-11T21:00", False), ("2026-11-12T00:59", False), ("2026-11-12T01:00", True),
                        ("2026-11-12T05:59", True), ("2026-11-12T06:00", False)):
        clock.set(when)
        assert lim.is_night() is night and lim.cap() == (0.06 if night else 0.12), when
    lim = limiter(clock, night_start="22:00", night_end="06:00")
    for when, night in (("2026-11-11T21:59", False), ("2026-11-11T22:00", True), ("2026-11-12T00:00", True),
                        ("2026-11-12T05:59", True), ("2026-11-12T06:00", False), ("2026-11-12T12:00", False)):
        clock.set(when)
        assert lim.is_night() is night, when
    lim = limiter(clock, night_start="03:00", night_end="03:00")            # equal times: never night
    for when in ("2026-11-12T02:59", "2026-11-12T03:00", "2026-11-12T03:01"):
        clock.set(when)
        assert lim.is_night() is False, when
    clock.set("2026-11-12T02:00")
    assert np.all(limiter(clock).apply(frame(40)) == 20)                    # APL 0.157, night cap 0.06: the floor
    clock.set("2026-11-12T12:00")
    assert np.all(limiter(clock).apply(frame(40)) == 31)                    # day cap 0.12: 40 * 0.765


def test_lux_only_adds_night():
    clock = Clock("2026-11-12T02:00")                                       # night by the clock
    reading = [300.0]
    lim = limiter(clock, lux=lambda: reading[0])
    assert lim.is_night() and lim.cap() == 0.06                             # a bright sensor never ends it
    clock.set("2026-11-11T21:00")                                           # day by the clock
    for value, night in ((5.0, False), (np.float64(900.0), False), (None, False), (math.nan, False),
                         (-math.inf, False), (True, False), ("2", False), (4.99, True)):
        reading[0] = value
        assert lim.is_night() is night, value                               # no reading: the clock decides
    for value in (np.float32(1.0), -1.0, 0):
        lim = limiter(clock, lux=lambda: value)
        assert lim.is_night() is True and lim.cap() == 0.06, value         # dark by the sensor
    assert limiter(clock, lux=lambda: 0.0, night_lux=0).is_night() is False  # night_lux 0: lux never adds night


def test_lux_night_ends_after_10_bright_seconds():
    assert LUX_RELEASE == 1.5 and LUX_HOLD_S == 10.0
    clock = Clock("2026-11-11T21:00")
    reading = [4.9]
    lim = limiter(clock, lux=lambda: reading[0])
    for i in range(600):                                                    # 20 s of a reading flapping at 5
        reading[0] = (4.9, 5.1)[i % 2]
        assert lim.cap() == 0.06, i
        clock.tick()
    for value in (7.49, 7.0, 5.0):                                          # under 1.5 x night_lux: still dark
        reading[0] = value
        clock.tick(9.0)
        assert lim.is_night(), value
    reading[0] = 7.5
    lim.is_night()
    clock.tick(9.9)
    assert lim.is_night()
    clock.tick(0.1)
    assert not lim.is_night()                                               # 10 s since the last dark reading
    reading[0] = 5.1
    assert not lim.is_night()                                               # day again: 5.1 is not dark
    reading[0] = 4.0
    assert lim.is_night()
    reading[0] = None                                                       # the sensor goes away
    clock.tick(9.9)
    assert lim.is_night()
    clock.tick(0.1)
    assert not lim.is_night()                                               # then the clock decides
    reading[0] = 4.0
    lim.is_night()
    clock.set("2026-11-11T20:00")                                           # a clock set back keeps the night
    reading[0] = 900.0
    assert lim.is_night()


def test_a_failing_lux_sensor_is_no_reading(caplog):
    clock = Clock("2026-11-11T21:00")

    def broken():
        raise OSError("no metadata")

    lim = limiter(clock, lux=broken)
    with caplog.at_level(logging.ERROR, logger="arcade.brightness"):
        assert [lim.is_night() for _ in range(3)] == [False] * 3
        clock.set("2026-11-12T02:00")
        assert lim.is_night() and lim.cap() == 0.06
    assert len(caplog.records) == 1 and "lux" in caplog.records[0].getMessage()


def limited_then_governed(frames, lux=None, clock=None, governor=None):
    """The runner's order (Q11): limiter, then governor, then push. Returns what the limiter made and what is
    pushed."""
    lim = limiter(clock, lux=lux)
    g = governor or FlashGovernor(*frames[0].shape[:2])
    limited = [lim.apply(f) for f in frames]
    return limited, [g.apply(f) for f in limited]


def test_limiter_then_governor_never_strobes():
    # A static score strip, with the left and right halves each flashing 2.5 times a second out of phase: a
    # limiter that followed each frame's level at once would strobe the strip between 255 and 128.
    frames = []
    for i in range(120):
        f = frame(0)
        f[:4, :32] = 255
        if i % 12 < 3:
            f[4:, :64] = 255
        elif 6 <= i % 12 < 9:
            f[4:, 64:] = 255
        frames.append(f)
    limited, pushed = limited_then_governed(frames)
    assert flash_area(frames) == 0.0 and flash_area(limited) == 0.0 and flash_area(pushed) == 0.0
    assert len({int(f[0, 0, 0]) for f in limited}) > 1                     # the strip does dim and recover
    # A static frame under a lux reading flapping across night_lux: the cap holds, the picture does not move.
    reading = iter([4.9, 5.1] * 60)
    limited, pushed = limited_then_governed([frame(40)] * 120, lux=lambda: next(reading))
    assert all(np.array_equal(f, limited[0]) for f in limited) and np.all(limited[0] == 20)
    # Random blocks switching at random under a flapping, failing sensor: the pushed frames keep the bound, on
    # every pixel outside a small flash and on every square's mean light.
    seed = zlib.crc32(b"limiter-then-governor")
    rng = np.random.default_rng(seed)
    for trial in range(30):
        blocks = [(rng.integers(0, 32), rng.integers(0, 128), rng.integers(2, 20), rng.integers(2, 64),
                   rng.integers(0, 256, 3)) for _ in range(8)]
        on = rng.random(8) < 0.5
        frames = []
        for _ in range(60):
            on ^= rng.random(8) < 0.3
            f = frame(0)
            for (y, x, h, w, c), lit in zip(blocks, on):
                if lit:
                    f[y:y + h, x:x + w] = c
            frames.append(f)
        values = iter(rng.choice([4.9, 5.1, np.nan], 60))
        g = FlashGovernor(32, 128)
        limited, pushed = limited_then_governed(frames, lux=lambda: next(values), governor=g)
        assert g.held_ticks > 0 and concurrent_area(pushed) < SMALL_AREA, (trial, seed)
        assert square_flashes(pushed) <= BUDGET, (trial, seed)


def test_limiter_rejects_bad_config_and_frames():
    for over in (dict(apl_cap_day=0.0), dict(apl_cap_night=1.5), dict(apl_cap_day=math.nan),
                 dict(apl_cap_night=None), dict(apl_cap_day=True), dict(night_lux=-1.0), dict(night_lux=math.nan),
                 dict(night_lux="5"), dict(night_start="1:00"), dict(night_end="24:00"), dict(night_start="01:000"),
                 dict(night_start=None), dict(gamma=0.0), dict(gamma=math.inf), dict(gamma="2.2")):
        with pytest.raises(ValueError):
            limiter(**over)
    limiter(apl_cap_day=np.float64(0.2), night_lux=0, night_start="23:59", night_end="00:00")
    limiter(apl_cap_day=1.0, apl_cap_night=1.0)                             # a cap of all the light is allowed
    lim = limiter()
    for bad in (np.zeros((4, 8, 3), np.float32), np.zeros((4, 8), np.uint8), np.zeros((4, 8, 4), np.uint8)):
        with pytest.raises(ValueError):
            lim.apply(bad)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_flash.py tests/arcade/test_brightness.py`

Expected: `2 errors` during collection, with `ModuleNotFoundError: No module named 'arcade.flash'` for `test_flash.py` and `ModuleNotFoundError: No module named 'arcade.brightness'` for `test_brightness.py`.

- [ ] **Step 3: Implement**

`arcade/flash.py`:

```python
"""The flash governor (spec 7.6 as amended by Q13 and Q15): no area of the wall flashes more than 3 times a second.

Runner-level and last before push (Q11: limiter, then governor, then push), so the bound holds on what the wall
shows; no game or mode can bypass it. After the review prototype FlashLimiter
(docs/superpowers/reviews/2026-09-26-arcade-review-lenses/flashguard2.py), with spec 7.6's saturated-red rule,
the light model of the previews, Q13's small-area exemption, Q15's field cap and a square backstop (plan review B7).
"""
from __future__ import annotations

import logging
import math
from functools import lru_cache

import numpy as np

from arcade.look import is_real, light_lut

log = logging.getLogger("arcade")

FPS = 30                 # the runner's default tick rate: one second of frames
THRESHOLD = 0.1          # a swing of this much light (0..1) from the last extreme is a transition
BUDGET = 6               # transitions per pixel in any second: two per flash, so 3 flashes a second
RED_SHARE = 0.8          # a pixel whose red is this share of its light or more is saturated red
REC709 = np.array([0.2126, 0.7152, 0.0722], np.float32)
WINDOW = 32              # the area rule's square: 16 cm of P5 wall, a 10 degree field seen from 92 cm
SMALL_AREA = 0.1         # a flash on under this share of every WINDOW square is not held (Q13, decision 16)
FIELD_AREA = 0.125       # over-budget flips on this share of the wall, either way, are held however small (Q15)
BACKSTOP_PASSES = 8      # the square backstop's passes before it holds the whole frame (the review saw 4 at most)


def signals(frame: np.ndarray, gamma: float) -> np.ndarray:
    """(3, h, w) float32, each pixel's light measured three ways, a swing in any of which is a transition:
    Rec. 709 luminance; the same doubled for saturated red (red at least RED_SHARE of the light, spec 7.6);
    and red excess, red's light less green's and blue's (0 at least), which moves when red trades against
    another colour of the same luminance."""
    light = light_lut(gamma)[frame]
    y = light @ REC709
    red = light[..., 0]
    doubled = np.where(red >= RED_SHARE * light.sum(axis=2), 2.0 * y, y)      # black: 0 either way
    excess = np.maximum(red - light[..., 1] - light[..., 2], 0.0)
    return np.stack((y, doubled, excess))


class _Transitions:
    """Per value: the lowest and highest since the last transition, and that transition's direction. A rise of
    threshold or more over the lowest (unless already rising) or a fall of threshold or more from the highest
    (unless already falling) is a transition, and both restart there. Before the first, either way counts."""

    def __init__(self, v: np.ndarray, threshold: float):
        self.threshold = threshold
        self.lo, self.hi = v.copy(), v.copy()
        self.direction = np.zeros(v.shape, np.int8)

    def flips(self, v: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        up = (v - self.lo >= self.threshold) & (self.direction <= 0)
        down = (self.hi - v >= self.threshold) & (self.direction >= 0)
        return up | down, up

    def advance(self, v: np.ndarray, flip: np.ndarray, up: np.ndarray) -> None:
        self.direction[flip] = np.where(up[flip], 1, -1)
        self.lo = np.where(flip, v, np.minimum(self.lo, v))
        self.hi = np.where(flip, v, np.maximum(self.hi, v))


@lru_cache(maxsize=16)
def _band(n: int, k: int) -> np.ndarray:
    """(n - k + 1, n) float32: row i is 1 over columns i to i + k - 1, so band @ v sums every run of k."""
    i, j = np.arange(n - k + 1)[:, None], np.arange(n)[None, :]
    band = ((j >= i) & (j < i + k)).astype(np.float32)
    band.flags.writeable = False
    return band


def _square_sums(a: np.ndarray, window: int) -> tuple[np.ndarray, int]:
    """a (..., h, w) summed over every window x window square (cut to the wall), and the square's area."""
    h, w = a.shape[-2:]
    wh, ww = min(window, h), min(window, w)
    return _band(h, wh) @ a @ _band(w, ww).T, wh * ww


def largest_share(mask: np.ndarray, window: int = WINDOW) -> float:
    """The largest share of any window x window square of mask (h, w) that is True, 0..1; on a wall smaller
    than the window the square is cut to the wall."""
    sums, area = _square_sums(mask.astype(np.float32), window)
    return float(sums.max()) / area


def square_means(s: np.ndarray, window: int = WINDOW) -> np.ndarray:
    """(3, h, w) signals to (3, h', w'): their mean over every window x window square (cut to the wall)."""
    sums, area = _square_sums(s, window)
    return sums / area


def _concurrent(flip: np.ndarray, up: np.ndarray, over: np.ndarray, window: int) -> float:
    """The largest share of any square whose over-budget pixels transition the same way in this frame (any of
    the three signals rising, or any falling): the area of a flash, as the guidance counts "flashes occurring
    concurrently". Text scrolling past turns some pixels on and others off, never most of a square one way."""
    ups, downs = (flip & up).any(axis=0) & over, (flip & ~up).any(axis=0) & over
    return max(largest_share(ups, window), largest_share(downs, window))


class _Window:
    """Per position: how many transitions the last n frames hold."""

    def __init__(self, n: int, shape: tuple[int, ...]):
        self.ring = np.zeros((n,) + shape, bool)
        self.count = np.zeros(shape, np.int16)
        self.i = 0

    def push(self, shown: np.ndarray) -> None:
        self.count -= self.ring[self.i]
        self.ring[self.i] = shown
        self.count += shown
        self.i = (self.i + 1) % len(self.ring)


class FlashGovernor:
    """apply(frame) returns the frame with every over-budget transition held at the pixel's previous output,
    unless the flash is a small area, and with every square whose mean light would flash past budget held whole.

    A transition is over budget when the pixel's previous fps frames already hold budget of them (spec 7.6's
    "already transitioned six times in the last second"), so any fps + 1 frames show at most budget. A flash
    is a small area (Q13), and nothing is held, while all three: the over-budget transitions of this frame
    going the same way fill under SMALL_AREA of every WINDOW square; those going either way fill under
    FIELD_AREA of the wall (Q15); and no square's mean light has made budget transitions in the last fps
    frames (one such square anywhere lets over-budget pixels be held anywhere). Then the square backstop: a
    square whose mean light would make a transition while its last fps frames already hold budget is held
    whole, whatever its pixels' own budgets, until no such square flips. After BACKSTOP_PASSES passes it holds
    the whole frame instead, logged once, so apply never hangs. So every square's mean shows at most budget
    transitions in any fps + 1 frames, however its pixels take turns. Fine text scrolling past passes: it
    turns a few pixels of a square on and others off, and the square's mean hardly moves. A strobe, a pattern
    reversal, a reversing grating, many small flashes together, and a flash spread over a few frames or taken
    in turns are all held. Held pixels are measured as shown: what the wall showed is what is counted.

    The first frame passes, and a frame with nothing held is returned as it is (the same array). held_ticks
    counts the frames in which anything was held (the runner's flash_held_ticks). fps is the runner's tick rate
    (cfg.fps). A frame of another shape or dtype raises ValueError.
    """

    def __init__(self, height: int, width: int, gamma: float = 2.2, fps: int = FPS, threshold: float = THRESHOLD,
                 budget: int = BUDGET):
        light_lut(gamma)                                             # checks gamma
        if isinstance(fps, bool) or not isinstance(fps, int) or fps < 2:
            raise ValueError(f"fps must be an int of at least 2, got {fps!r}")
        if isinstance(budget, bool) or not isinstance(budget, int) or budget < 1:
            raise ValueError(f"budget must be an int of at least 1, got {budget!r}")
        if not is_real(threshold) or not 0.0 < threshold < math.inf:
            raise ValueError(f"threshold must be over 0 and finite, got {threshold!r}")
        self.shape, self.gamma, self.budget, self.fps = (height, width, 3), gamma, budget, fps
        self.threshold = threshold
        self.held_ticks = 0
        self._prev: np.ndarray | None = None                        # a copy of the last output
        self._shown: np.ndarray | None = None                       # and its signals
        self._pixels: _Transitions | None = None
        self._squares: _Transitions | None = None
        self._pixel_window = self._square_window = None
        self._gave_up = False                                       # the backstop's fallback is logged once

    def apply(self, frame: np.ndarray) -> np.ndarray:
        if frame.shape != self.shape or frame.dtype != np.uint8:
            raise ValueError(f"frame must be {self.shape} uint8, got {frame.shape} {frame.dtype}")
        s = signals(frame, self.gamma)
        if self._pixels is None:                             # nothing is held before a transition: no _prev yet
            means = square_means(s)
            self._pixels, self._squares = _Transitions(s, self.threshold), _Transitions(means, self.threshold)
            self._pixel_window = _Window(self.fps, s.shape[1:])
            self._square_window = _Window(self.fps, means.shape[1:])
            self._shown = s
            return frame
        flip, up = self._pixels.flips(s)
        over = self._pixel_window.count >= self.budget
        hold = flip.any(axis=0) & over
        square_over = self._square_window.count >= self.budget
        if not (hold.any() and (square_over.any() or hold.mean() >= FIELD_AREA
                                or _concurrent(flip, up, over, WINDOW) >= SMALL_AREA)):
            hold[:] = False                                  # a small flash (Q13): nothing is held
        # Square backstop: a square whose mean would make an over-budget transition is held whole, whatever
        # its pixels' own budgets; repeat until no over-budget square flips (all held flips nothing).
        h, w = hold.shape
        bh, bw = _band(h, min(WINDOW, h)), _band(w, min(WINDOW, w))
        for _ in range(BACKSTOP_PASSES):
            shown = np.where(hold, self._shown, s)           # measure what is shown: a held pixel does not flip
            means = square_means(shown)
            square_flip, square_up = self._squares.flips(means)
            bad = square_flip.any(axis=0) & square_over
            if not bad.any():
                break
            hold |= (bh.T @ bad.astype(np.float32) @ bw) > 0
        else:                                                # never measured: hold the whole frame, which flips nothing
            if not self._gave_up:
                log.warning("flash governor: the square backstop took %d passes; holding the whole frame",
                            BACKSTOP_PASSES)
                self._gave_up = True
            hold[:] = True
            shown, means = self._shown, square_means(self._shown)
            square_flip = square_up = np.zeros(means.shape, bool)
        out = frame
        if hold.any():
            self.held_ticks += 1
            out = np.where(hold[..., None], self._prev, frame)
        s = shown
        flip, up = self._pixels.flips(s)
        self._pixels.advance(s, flip, up)
        self._pixel_window.push(flip.any(axis=0))
        self._squares.advance(means, square_flip, square_up)
        self._square_window.push(square_flip.any(axis=0))
        self._prev, self._shown = out.copy(), s
        return out


def _counted(frames, gamma: float, fps: int, threshold: float, squares: int | None = None):
    """For each frame after the first: its flips and rises (3, h, w) and the window of the fps frames before
    it, counted as the governor counts; of the square means of the given size instead, when given."""
    track, window = None, None
    for frame in frames:
        s = signals(np.asarray(frame), gamma)
        if squares is not None:
            s = square_means(s, squares)
        if track is None:
            track, window = _Transitions(s, threshold), _Window(fps, s.shape[1:])
            continue
        flip, up = track.flips(s)
        yield flip, up, window
        track.advance(s, flip, up)
        window.push(flip.any(axis=0))


def flash_area(frames, gamma: float = 2.2, fps: int = FPS, threshold: float = THRESHOLD,
               budget: int = BUDGET) -> float:
    """The largest share of the wall that flashed more than budget / 2 times in a second (more than budget
    transitions in fps consecutive frames), counted as the governor counts. For tests and tools: spec 7.6's
    "a game's raw output may flash at most 10 percent of the wall", and 0.0 for governed output of any flash
    that is not a small area."""
    worst = 0.0
    for flip, up, window in _counted(frames, gamma, fps, threshold):
        last_second = window.count - window.ring[window.i] + flip.any(axis=0)
        worst = max(worst, float((last_second > budget).mean()))
    return worst


def concurrent_area(frames, gamma: float = 2.2, fps: int = FPS, threshold: float = THRESHOLD,
                    budget: int = BUDGET, window: int = WINDOW) -> float:
    """The largest share of any window x window square whose over-budget transitions went the same way in one
    frame, as the governor measures a flash's area (Q13): governed output is always under SMALL_AREA."""
    worst = 0.0
    for flip, up, counts in _counted(frames, gamma, fps, threshold):
        worst = max(worst, _concurrent(flip, up, counts.count >= budget, window))
    return worst


def square_flashes(frames, gamma: float = 2.2, fps: int = FPS, threshold: float = THRESHOLD,
                   window: int = WINDOW) -> int:
    """The most transitions the mean light of any window x window square made in fps consecutive frames: a
    flash of an area, however its pixels take turns."""
    worst = 0
    for flip, up, counts in _counted(frames, gamma, fps, threshold, squares=window):
        worst = max(worst, int((counts.count - counts.ring[counts.i] + flip.any(axis=0)).max()))
    return worst
```

`arcade/brightness.py`:

```python
"""The brightness limiter (spec 7.6): caps the wall's average picture level, lower at night.

Runner-level, before the flash governor (Q11: limiter, then governor, then push). Unlike the display brightness
(a hard ceiling the card applies, never pixel scaling), this is a picture-level cap that does scale frames.
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, time
from typing import Callable

import numpy as np

from arcade.config import HHMM, ArcadeConfig
from arcade.flash import THRESHOLD
from arcade.look import MONITOR_GAMMA, is_real, light_lut

log = logging.getLogger(__name__)

MIN_FACTOR = 0.5         # the limiter never takes more than half the light: at most one bit lost
RELEASE = THRESHOLD / 10  # the factor rises at most this much a tick: 10 ticks to brighten a pixel by a flash
LUX_RELEASE = 1.5        # lux night ends only once no reading has been under 1.5 x night_lux ...
LUX_HOLD_S = 10.0        # ... for 10 seconds (Q12, loop decision 14)


def apl(frame: np.ndarray, gamma: float) -> float:
    """Average picture level: the mean light of every channel of every pixel, 0..1, after gamma (the
    light_lut model). Mean channel light is what the LEDs draw and what the review's APL figures measured."""
    return float(light_lut(gamma)[frame].mean())


def _hhmm(name: str, value) -> time:
    if not isinstance(value, str) or not HHMM.fullmatch(value):
        raise ValueError(f"{name} must be HH:MM (00:00 to 23:59), got {value!r}")
    return time(int(value[:2]), int(value[3:]))


class BrightnessLimiter:
    """apply(frame) scales frames down to cap() through a lookup table, never below MIN_FACTOR of their light.

    The factor falls at once to what the frame needs (cap / APL, at least MIN_FACTOR) and rises back by at
    most RELEASE a tick, so a level that comes and goes, or a cap that changes, never strobes the picture.
    A frame is returned as it is (the same array) while the factor is 1.0.

    cap() is apl_cap_night at night and apl_cap_day otherwise. is_night() is the clock's night OR lux night
    (Q12: lux only adds night). The clock's night is night_start <= now < night_end, spanning midnight when
    night_start is later than night_end; equal times mean never. Lux night starts at a reading under night_lux
    (lux() is the IMX500's lux metadata) and ends once no reading has been under LUX_RELEASE x night_lux for
    LUX_HOLD_S. None, NaN, an infinity, a reading that is not a number and an exception from lux() are no
    reading (an exception is logged once). clock returns local time: the runner passes a local clock, never
    its monotonic one. factor is the last scale applied and scaled_ticks counts the frames scaled. The config
    is checked here, since an ArcadeConfig built in code skips load_config: ValueError on a bad value, and on
    a frame that is not (h, w, 3) uint8.
    """

    def __init__(self, cfg: ArcadeConfig, clock: Callable[[], datetime] = datetime.now,
                 lux: Callable[[], float | None] | None = None):
        for name in ("apl_cap_day", "apl_cap_night"):
            v = getattr(cfg, name)
            if not is_real(v) or not 0.0 < v <= 1.0:
                raise ValueError(f"{name} must be in (0, 1], got {v!r}")
        if not is_real(cfg.night_lux) or not cfg.night_lux >= 0:
            raise ValueError(f"night_lux must be 0 or more, got {cfg.night_lux!r}")
        self.start, self.end = _hhmm("night_start", cfg.night_start), _hhmm("night_end", cfg.night_end)
        light_lut(cfg.gamma)                                         # checks gamma
        self.cfg, self.clock, self.lux = cfg, clock, lux
        self.factor, self.scaled_ticks = 1.0, 0
        self._dim_at: datetime | None = None                         # the last dark reading while lux night
        self._lux_failed = False

    def _reading(self) -> float | None:
        if self.lux is None:
            return None
        try:
            v = self.lux()
        except Exception:
            if not self._lux_failed:
                log.exception("lux reading failed: the clock decides the night")
                self._lux_failed = True
            return None
        return float(v) if is_real(v) and math.isfinite(v) else None

    def is_night(self) -> bool:
        now = self.clock()
        reading = self._reading()
        dark = self.cfg.night_lux * (1.0 if self._dim_at is None else LUX_RELEASE)
        if reading is not None and reading < dark:
            self._dim_at = now
        elif self._dim_at is not None and (now - self._dim_at).total_seconds() >= LUX_HOLD_S:
            self._dim_at = None
        t = now.time()
        if self.start < self.end:
            clock_night = self.start <= t < self.end
        else:
            clock_night = self.start > self.end and (t >= self.start or t < self.end)
        return clock_night or self._dim_at is not None

    def cap(self) -> float:
        return self.cfg.apl_cap_night if self.is_night() else self.cfg.apl_cap_day

    def apply(self, frame: np.ndarray) -> np.ndarray:
        if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError(f"frame must be (h, w, 3) uint8, got {frame.shape} {frame.dtype}")
        level, cap = apl(frame, self.cfg.gamma), self.cap()
        need = 1.0 if level <= cap else max(MIN_FACTOR, cap / level)
        self.factor = need if need < self.factor else min(need, self.factor + RELEASE)
        if self.factor == 1.0:
            return frame
        self.scaled_ticks += 1
        # light is (v / 255) ** (MONITOR_GAMMA / gamma): scaled by factor, v scales by factor ** (gamma / MONITOR_GAMMA)
        scale = self.factor ** (self.cfg.gamma / MONITOR_GAMMA)
        lut = np.floor(np.arange(256) * scale + 0.5).astype(np.uint8)      # scale <= 1: 255 at most
        return lut[frame]
```

- [ ] **Step 4: Run the tests**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_flash.py tests/arcade/test_brightness.py`

Expected: `41 passed` (flash 29, brightness 12), in about 10 s.

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`

Expected: `334 passed`, no skips.

- [ ] **Step 5: Commit**

```bash
git add arcade/flash.py arcade/brightness.py tests/arcade/test_flash.py tests/arcade/test_brightness.py
git commit -m "feat(arcade): flash governor holds flashes past 3 a second unless small, brightness limiter caps the picture level by night and day (core Task 8 part)" -m "Both use the looks' light through cfg.gamma. Transitions count on luminance, saturated red doubled and red excess; a flash under 10% of every 32 px square passes (Q13), unless its over-budget pixels cover 12.5% of the wall (Q15), and a square whose mean light would flash past the budget is held whole (plan review B7), in at most 8 passes before the whole frame is held. The limiter falls at once, rises 0.01 a tick and never takes more than half the light; lux only adds night (Q12). The runner order is limiter, governor, push (Q11)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Iteration verify

The operator runs these inline after Task 4, from the repo root.

1. `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest --collect-only -q | tail -1` prints `334 tests collected`. There were 224 before this iteration, and the count rises at every task: 230, 242, 293, 334.
2. `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs` prints `334 passed` with **0 skipped**. Per module:

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
   | `tests/arcade/test_input.py` | 12 |
   | `tests/arcade/test_look.py` | 18 |
   | `tests/arcade/test_mirror.py` | 2 |
   | `tests/arcade/test_scores.py` | 12 |
   | `tests/arcade/test_sensed.py` | 20 |
   | `tests/test_colorlight.py` | 29 |
   | `tests/test_config.py` | 5 |
   | `tests/test_ddp.py` | 8 |
   | `tests/test_display.py` | 4 |
   | `tests/test_font.py` | 7 |
   | `tests/test_gitignore.py` | 6 |

   `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest --collect-only -q | grep '::' | sed 's/::.*//' | sort | uniq -c` lists the same counts.
3. No existing assert weakened: `git diff 5cf9943 -- tests/ | grep '^-[^-]'` prints nothing, because no test line was removed or changed. Anything it prints is a Deviation.
4. `.venv/bin/python -c "import sys, arcade.input, arcade.game, arcade.games, arcade.scores, arcade.flash, arcade.brightness; print(sorted({'cv2', 'mediapipe', 'sounddevice', 'pygame'} & set(sys.modules)))"` prints `[]`.
5. `.venv/bin/python -c "from arcade.games import all_games; print(all_games())"` prints `[]`: no game module exists yet, and nothing is logged. The tests fake the package (B6); this is the real one.
6. Nothing visual lands in this iteration. The canvas and look changes affect only degenerate inputs: sub-half-pixel radii, `10**400`, and bad settings that now raise. The governor and limiter are not wired to any display until it05. So there is no PNG snippet. it05's verify will render governed and limited frames once the runner pushes them.
7. `git log --oneline -4` shows the four commit messages above, in order. `git status --short` is clean apart from `docs/superpowers/workflow/` files.
