# Review 05: plan executability, game layer

Reviewer lens: if a fresh agent executes `docs/superpowers/plans/2026-09-26-wall-arcade-core.md` task by task, does the game layer come out consistent, and does it carry the nine games of the second plan without framework surgery?

## What I ran

- **Environment.** Python 3.12.13 (uv), numpy 2.x, pygame 2.6.1, opencv-python 5.0.0, Pillow, pytest, pyte, sdnotify. No mediapipe, picamera2 or sounddevice (Tasks 15 to 19 were read, not run). `SDL_VIDEODRIVER=dummy`.
- **Extraction.** A script pulled every `` `path`: `` code block from daemon plan Tasks 1, 2, 5 and 15 and from arcade plan Tasks 1 to 14 and 20 into a scratch repo. I then applied by hand the arcade Task 1 replacements (pyproject, duck-typed `make_display`, `FakeDisplay` with `last`/`count`, new `test_display.py`), the daemon amendments for Tasks 1 and 15 (extra `Config` fields, no `matrix_multiplexing`, DDP type `0x0B`, no scaling, renamed DDP test), and the two registry appends from Tasks 10 and 11. The font came from the real Adafruit `glcdfont.c` through the plan's extractor.
- **Result as written: 109 collected, 109 passed** in 3.4 s on the first run. Per file: daemon config 4, font 7, display 4, DDP 3; arcade config 9, sensed 6, actors 6, canvas 6, look 6, game 3, scores 2, runner 10, menu 12, paint 6, puppet 7, scenario 4, shot 4, play 4, all_games 6.
- **Result under different hash seeds: the Task 20 soak test fails in 10 of 12 runs** (`PYTHONHASHSEED=1..12`: 1 or 2 failures each, except seeds 3 and 9). See Blocker 1.
- **Probes.** I wrote 14 reviewer tests asserting what the spec requires; 11 failed against the plan's code. Every Blocker and Serious item below that says "demonstrated" is one of them.
- **Corrections verified.** I applied the corrected code given below to a copy. The full suite plus the probes give **124 passed, 1 failed**; the one failure is the brightness probe, which needs a decision rather than a code fix (Serious 6). The corrected soak test passes under 8 of 8 hash seeds at three sizes.
- **Timing.** I measured per-tick costs on the Mac (numbers in the budget section).

Plan test-count errors an agent will trip on: Task 10 says "5 passed" but its tests collect 6, because the two sized tests run twice. Every other task's expected count matched.

---

## Blockers

### B1. Task 20: the soak test is nondeterministic and fails most runs

`rng = random.Random(hash((game_cls.info.name, size)) & 0xFFFF)` uses `hash()` of a string, which Python salts per process. On top of that, `random_mix` draws `rng.randint(0, 2)` persons and blobs, so a third of the time puppet gets no body and paint gets no blob. Those games then correctly draw black, and the test fails with `AssertionError: game never drew anything`. I measured 10 failures in 12 seeds. An unattended agent at Task 20 will "fix" a game that is not broken, or it will loosen the assertion.

Corrected code (verified 8/8 seeds, also adds Review Focus 3's 96x48):

```python
import zlib

def random_mix(rng: random.Random, ticks: int, needs: frozenset = frozenset()):
    """Random actors, but always at least one of each input the game needs, so black means broken."""
    n_persons = rng.randint(1 if needs & {"pose", "motion"} else 0, 2)
    n_blobs = rng.randint(1 if "blobs" in needs else 0, 2)
    persons = [Person(rng.uniform(0.1, 0.9), 0.55, rng.uniform(0.4, 0.8), id=i)
               .walk(rng.uniform(0.1, 0.9), rng.uniform(1, 5))
               .raise_hand(at=rng.uniform(0, 5), seconds=1.0)
               .jump(at=rng.uniform(0, 8), height=0.2)
               for i in range(n_persons)]
    blobs = [moving_blob(rng.random(), rng.random(), rng.random(), rng.random(), rng.uniform(1, 6),
                         start=rng.uniform(0, 2),
                         color=(rng.randint(64, 255), rng.randint(64, 255), rng.randint(64, 255)))
             for _ in range(n_blobs)]
    audio = rng.choice([claps([1.0, 2.5, 4.0]), tempo(120)] + ([] if "audio" in needs else [None]))
    return scene(persons=persons, blobs=blobs, audio=audio, ticks=ticks)

@pytest.mark.parametrize("size", [(128, 32), (64, 64), (96, 48)], ids=["128x32", "64x64", "96x48"])
@pytest.mark.parametrize("game_cls", all_games(), ids=lambda g: g.info.name)
def test_every_game_soaks_without_error(game_cls, size, font5x7):
    rng = random.Random(zlib.crc32(f"{game_cls.info.name}{size}".encode()))  # hash() is salted per process
    frames, game, runner = run(game_cls, random_mix(rng, 300, game_cls.info.needs), size, font5x7)
    ...
```

Also add `-p no:randomly`-style determinism guidance to Global Constraints: "Never seed from `hash()` of a str; use `zlib.crc32`."

### B2. Task 8: the crash guard does not cover `__init__`, `reset` or `done()` (spec 7.2). Demonstrated.

`launch()` constructs the game and calls `reset` outside any `try`. `tick()` calls `launch(choice)` after the guarded block, and it calls `self.current.done()` outside it too. A game that raises in `reset` when picked from the menu, or in `done()`, propagates out of `Runner.tick`, out of `loop`, and ends the process. The spec says "an exception in reset, update, or draw ... returns to the menu ... The runner itself never exits on a game error." Nine unwritten games will each get a `reset`, so this is the most likely crash at the festival.

Corrected `launch` and the guarded block (verified; all ten original runner tests still pass):

```python
def launch(self, name: str, attract: bool = False) -> None:
    cls = self.games[name]          # KeyError for an unknown name is the caller's bug
    self.current_name, self.in_attract, self._exit_held = name, attract, 0.0
    try:
        game = cls()
        game.reset(self.cfg.size, random.Random(self.seed))
    except Exception:
        self._crashed()
        return
    self.current = game

# in tick():
    try:
        self.current.update(sensed, dt)
        self.canvas.clear()
        self.current.draw(self.canvas)
        finished = self.current is not self.menu and self.current.done()
    except Exception:
        self._crashed()
        return
    ...
    elif finished:
        self.go_menu()
```

Add to the Task 8 tests: a game raising in `reset`, selected through `StubMenu.selected`, increments `crashes` and never raises out of `tick`. Do the same for `done()`.

---

## Serious

### S1. Task 8: a game left alone never times out, so the wall goes black. Demonstrated.

The idle check only launches attract when the menu is showing. If someone launches puppet or paint and walks away, the runner stays in that game forever. Puppet draws nothing with no body, and paint clears itself after 30 s. The wall is then black until someone walks up, which breaks the spec's "no bodies and no blobs for idle_seconds launches ambient". Separately, `arcade/main.py` (Task 18) never passes `attract=`. So even after the second plan adds `ambient`, the live arcade never enters attract unless someone edits `main.py`.

Fix (verified):

```python
        body = sensed.primary
        if self.current is not self.menu:
            ...exit gesture...
            elif self.in_attract and present:
                self.go_menu()
            elif not self.in_attract and self._idle >= self.cfg.idle_seconds:
                self._go_attract()
        elif self._idle >= self.cfg.idle_seconds:
            self._go_attract()

    def _go_attract(self) -> None:
        a = self.attract
        if a is not None and a in self.games and a not in self.hidden:
            if self.current_name != a:
                self.launch(a, attract=True)
        elif self.current is not self.menu:
            self.go_menu()          # no ambient registered yet: the menu is the attract screen
```

In Task 18, construct the runner as `Runner(cfg, display, font, Menu(games, cfg), games, attract="ambient", seed=args.seed)`. The runner already ignores a missing entry, so this is safe with two games. Add a sentence to Task 8: "When the registry lacks the attract entry, idle returns to the menu, and the menu is the attract screen."

### S2. Task 8/9: the exit gesture flows straight into an accidental launch. Demonstrated.

After 1.5 s of both hands up the runner returns to the menu. The player's hands are still up, so `cursor_of` takes the higher wrist, the cursor sits on a top-row tile, and after `dwell_seconds` that game launches. With `Person(0.62).both_hands_up(0, 4.0)` in puppet, the menu relaunched puppet at t = 2.5 s. People hold the exit pose until something visibly changes, so this will happen constantly.

Fix (verified). The runner hides bodies and blobs from the menu until both hands come down:

```python
            if self._exit_held >= self.cfg.exit_seconds:
                self.go_menu()
                self._menu_blocked = True       # hands still up: do not let them steer the menu yet
        ...
        if self.current is self.menu and self._menu_blocked:
            if body is None or not body.both_hands_up:
                self._menu_blocked = False
            else:
                sensed = dataclasses.replace(sensed, bodies=(), blobs=())
```

Add the test: launch a game, hold both hands up for 4 s, and assert no launch happens after the return to the menu.

### S3. Task 8 helper `run()` and `run_headless` hide crashes and return the wrong object. Demonstrated.

`run()` returns `runner.current`. If the game called `done()` or crashed, that is the `NullMenu`, and `game.debug_state()["lit"]` raises `KeyError: 'lit'`. A game exception is also swallowed by the crash guard. The TDD agent then sees a `KeyError` or a black-frame assertion instead of the traceback it needs. For agents writing nine games test-first, this is the most expensive debugging trap in the plan.

Fix (verified; all existing tests pass unchanged): add a `strict` mode that re-raises, default it on in the harness, and keep the launched instance.

```python
# Runner.__init__(..., strict: bool = False); in _crashed(), first line:
        if self.strict:
            raise
# headless.py
def run_headless(cfg, font, game_cls, sensed_iter, seed=0, strict=True):
    ...
    runner = Runner(cfg, display, font, NullMenu(), [game_cls], seed=seed, strict=strict)
    runner.launch(game_cls.info.name)
    runner.game = runner.current          # the launched instance, even after done() or a crash
# helpers.run(..., strict=True, **cfg_over) returns frames, runner.game, runner
```

Tests of the crash guard itself build a `Runner` directly, where the default is `strict=False`, so they are unaffected.

### S4. Task 5: Canvas raises on float coordinates and can hang. Demonstrated.

The canvas promises that drawing "clips, never raises". Every future game with motion keeps float positions: pong's ball, flappy's bird, frogger's cars, boids. Passing those floats breaks the promise:

| Call | Result |
|---|---|
| `pixel(3.5, 2, c)` | `IndexError` |
| `fill_rect`, `fill_circle`, `blit` with a float | `TypeError` |
| `pixel(1, 1, (300, 0, 0))` | `OverflowError` |
| `line(0, 0, 10.5, 0, c)` | **infinite loop**; the crash guard cannot catch a hang |
| `line(0, 0, 10**9, 0, c)` | walks a billion clipped pixels |

Fix (verified):

```python
_FAR = 1 << 20

def _i(v) -> int:
    """Games keep float positions; the canvas rounds. NaN or inf lands far off-canvas and clips."""
    try:
        return max(-_FAR, min(_FAR, int(round(v))))
    except (ValueError, OverflowError, TypeError):
        return -_FAR

def _c(color) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(v))) for v in color)
```

Call `_i` and `_c` at the top of `pixel`, `fill_rect`, `line`, `_disc` and `blit`. In `line`, after coercion, add `if max(abs(x0), abs(x1), abs(y0), abs(y1)) > 4 * (self.width + self.height): return`. Add a canvas test covering floats, NaN, huge values and out-of-range colours. Change the Task 5 interface line to: "Coordinates may be int or float and are rounded; colours are clamped to 0..255."

### S5. Task 8: `Runner.state()` lets game keys overwrite runner keys. Demonstrated.

`{"game":..., "idle":..., **self.current.debug_state()}` means paint's own `idle` silently replaces the runner's `idle` in every REPL reply today. A future game with a `t`, `game` or `hidden` key corrupts what agents read. State also omits crashes, so the REPL cannot show that a game died.

Fix (verified):

```python
    def state(self) -> dict:
        own = {"game": self.current_name, "t": round(self.t, 3), "idle": round(self._idle, 3),
               "attract": self.in_attract, "hidden": sorted(self.hidden), "crashes": dict(self.crashes),
               "glitch": self._glitch}
        game = {} if self._glitch else self.current.debug_state()
        return {**game, **own}      # runner keys win; games must not reuse them
```

Rename paint's key to `since_blob`. In Task 20 add `assert not set(game.debug_state()) & {"game","t","idle","attract","hidden","crashes","glitch"}`.

### S6. Global Constraints vs spec 4.3 and 10: the brightness cap is enforced nowhere. Demonstrated.

The runner calls `display.set_brightness(0.4)` once. `SDLDisplay` stores the value "on purpose" and ignores it. After the amendment, `DDPDisplay` stores it and sends unscaled bytes. Nothing talks to Falcon Player. So `brightness` in `arcade.toml` has no effect on any output, while the spec calls it "the hard ceiling". My probe pushing 255 through DDP at brightness 0.4 received 255. Pick one of these and write it into the plan:

- **(a)** The ceiling is Falcon Player's output brightness, set during prototype bring-up. `ArcadeConfig.brightness` is then documented as "preview only". The runner logs `brightness cap is FPP's; arcade value %s is advisory` at startup when `backend == "ddp"`, and the spec's rows in 4.3 and 10 change.
- **(b)** The arcade scales in software, for DDP only, with a LUT. That costs about 1.3 bits of depth at 0.4.

Either way, add a test that the chosen path is taken. I would pick (a), because the show daemon already decided it, and add a bring-up checklist line to verify FPP's brightness.

### S7. Task 7/8: games cannot reach `Scores`, so jump, scream and flappy cannot be written without changing the framework.

Spec 7.5 says "a game reports through `record(game, value)`". But games are constructed with no arguments, `reset(size, rng)` passes no context, and games "never touch the config". So a game has no way to find `data_dir/scores.json`, and tests have no way to redirect it. Add this now:

```python
# scores.py: Scores(path: Path | None); path None keeps scores in memory (tests, tools)
    def _write(self) -> None:
        if self.path is None:
            return
        ...
# game.py, Game protocol docstring: "scores: Scores is set by the runner before reset()."
# runner.py
    def __init__(..., scores: Scores | None = None, ...):
        self.scores = scores if scores is not None else Scores(cfg.data_dir / "scores.json")
    def launch(...):
        game = cls()
        game.scores = self.scores
        game.reset(...)
# headless.run_headless: Runner(..., scores=Scores(None))
```

Add a Task 7 test: a game launched by the runner has `game.scores`, and `run_headless` never writes to `data/`.

### S8. Task 7/8: holewall, jump and pong need to switch off the exit gesture.

Holding both wrists above the nose for 1.5 s is a natural move in three of the planned games. It is a likely target pose in holewall, whose three-second countdown is longer than 1.5 s. People throw both arms up in jump. And a pong player may reach high with both hands. Add `exit_gesture: bool = True` to `GameInfo` now. The runner reads it through `getattr(self.current.info, "exit_gesture", True)`, a line already in my verified runner patch. A game with it off must end through `done()` or idle (S1).

### S9. Task 14 and 13: the agent tools can return wrong but plausible results. Demonstrated.

- **Stale shot.** `launch puppet` followed by `shot x.png` writes paint's last frame, because `display.last` survives `launch`, `menu` and `reset`. Fix (verified): set `self.display.last = None` on those three verbs. `shot` then returns `error: no frame since the last launch/menu/reset; step 1 first`.
- **Silently parsed input.** `step 3 x=0.3 hand=rihgt` returns success with no hand raised. `blob=0.5,0.5,255` silently becomes white. Fix (verified): validate `hand` against `left|right|both|none` and require 2 or 5 blob parts. Also echo the parsed input in each `step` reply, for example `"input": {"bodies": 1, "hand": "right", "blobs": 0}`, so a dropped token is visible.
- **Crash invisible in the REPL.** A raising game shows `"game": "spy"` for 30 ticks, then `"game": "menu"`, with nothing saying it crashed. S5's `crashes` and `glitch` keys fix this. Also add a `log` verb that prints the last traceback kept by the runner (`self.last_error = traceback.format_exc()` in `_crashed`).
- **Beats in the REPL.** `beat=120` fires one beat on the first tick only. The beat and flappy games need `step 90 beat=120` to produce a beat every 15 ticks. Build the audio from `tempo(bpm, start=t0)` for the whole step.
- **Black or crashed contact sheet.** In `arcade_shot`, a crashed game gives 30 glitch-noise frames, then black NullMenu frames, and exit 0. An agent can read the noise as a "static" effect. With S3's `strict=True` default, `run_headless` raises instead (verified by probe). Also make the tool refuse an all-black run: `if not any(f.any() for f in frames): raise SystemExit("every frame is black; the game got no input it needs (needs=%s)" % sorted(cls.info.needs))`, with `--allow-black` to override. It should print a one-line summary: frames, non-black count, `runner.state()` at the end, and `ScenarioReader.skipped` when replaying.
- **Minor tool points.** The label `t30` is a tick index but reads like seconds, so use `#30 1.00s`. `--ticks` is silently ignored with `--scenario`. `--audio tempo`, missing the call, puts a function into `Sensed.audio`: check `isinstance(audio(0.0), Audio)` after evaluating.

### S10. Task 4: `tempo()` fires double beats at 128 bpm. Demonstrated.

`_on_tick` accepts any tick within half a tick of the event. When a beat lands on a half-tick boundary, two adjacent ticks both match. Over 60 s, 128 bpm gives 135 beats with one-tick gaps; 60, 90, 100, 140, 174 and 200 bpm are clean. 128 is the most common dance tempo and exactly what the beat game's tests will use. The same hazard applies to `claps`. Fix (verified: exactly one hit per event at every tempo tried):

```python
def _fires(t: float, when: float) -> bool:
    """Exactly one tick per event: the first tick at or after it."""
    return when - 1e-9 <= t < when + TICK - 1e-9

def claps(times):  ... hit = any(_fires(t, c) for c in times)

def tempo(bpm, start=0.0):
    period = 60.0 / bpm
    def script(t):
        n = math.floor((t - start) / period + 1e-9)
        hit = t >= start - 1e-9 and _fires(t, start + n * period)
        ...
```

Add `128` to the actors test: `len(beats in 60 s) == 128` and no gap under 14 ticks.

---

## Minor

- **Registry import failure (Task 7).** One game module that fails at import takes down `arcade.games` and the whole arcade. Wrap each registration in `try/except Exception: log.exception(...)` so the other ten games still show.
- **Menu drops extra games silently (Task 9).** `list(games)[:TITLE_SLOT]` drops a twelfth game with no warning. Log it, and have a Task 20 test assert `len(all_games()) <= 11`.
- **Menu at 64x32 (Task 9).** A single panel during bring-up is 64x32. Three columns by four rows needs 51 rows, so half the tiles fall off-screen. Six columns needs 65 px wide, one pixel too many. Either pick the layout by fit (try 6x2, 4x3, 3x4 and shrink `GAP` to 0 when needed) or have `load_config` reject sizes where the menu cannot fit. Add 64x32 to the layout test. Review Focus 3 sizes 96x48 and 128x64 pass as written.
- **Dim colour too dark (Task 9).** `DIM_COLOR = (40, 40, 60)` becomes about 16/255 at the 0.4 cap, invisible on the wall, and wall-look forbids dark greys. Use a checkerboard of the icon in `TILE_COLOR`, or a hue change, instead of darkness.
- **Menu labels (Task 9).** Tiles draw no one-pixel border, only a margin, although the spec says "with a one-pixel border". The cursor is a five-pixel plus. Both are fine, but the spec wording should match.
- **Menu crash loop (Task 8).** If the menu itself crashes, `_crashed` hides "menu", then `go_menu` crashes again, glitching forever. Special-case `name == "menu"` by falling back to a built-in title card or to attract.
- **`needs` is AND-only (Task 7).** Pong reads "wrists or blobs", which `needs` cannot say. It is harmless while every camera source provides pose and blobs together. Document it.
- **`draw()` right after `reset()` (Task 7).** The protocol should say whether `draw()` must work right after `reset()`, before any `update`. The runner never does that, but tools might. Say "must".
- **Spec drift to fix in the spec, not the plan.** Spec 7.4 "kept canvas" became a game-owned buffer in paint, so drop "unless they ask to keep it". Spec 9's `--actors "walk(...);raise_hand(...)"` became `--person "Person(...)..."`, and the skill written from the spec will teach a command that fails. Spec 6.4 `combine(...)` became `scene(...)`.
- **Two SDL libraries on the Mac (dev box).** opencv-python 5.0 bundles its own `libSDL2` on macOS, and so does the headless wheel. Importing it next to pygame prints 17 `objc: Class SDL... is implemented in both` warnings, which say this "may cause spurious casting failures and mysterious crashes". The live Mac preview runs both in one process. Add it to the Task 18 smoke checklist. If it bites, run the preview with `pygame-ce`, or move `cv2.blur` in `look.py` to numpy so only the camera source imports cv2.
- **Unnamespaced debug keys.** Paint's key `idle` differs from runner `idle` (see S5).

---

## Forward compatibility with the nine unplanned games

What each game needs that this plan does not provide. **Now** means add it in this plan, because the second plan would otherwise edit framework files the first plan's tests pin.

| Game | Missing | When |
|---|---|---|
| frogger | Rising-edge detector for "raised wrist hops once" (`arcade/input.py: Edge`, `Hold(seconds)`), shared with holewall and the menu | Now, small |
| frogger | Multi-colour sprites: `Canvas.blit_rgb(img, x, y)` using black as transparent, and `sprite_from_rows(rows, palette)` | Now |
| frogger, pong, flappy, ambient | Float coordinates accepted by Canvas (S4) | Now |
| pong | Continuous wrist height in actors: `Person.wrist(hand, y_from, y_to, seconds, at)`; today hands are only up or down | Now |
| pong | Two bodies in the REPL: `step N x=0.3,0.7` | Now |
| pong, holewall, jump | `GameInfo.exit_gesture` (S8) | Now |
| jump, scream, flappy | Scores reachable from a game (S7); `Canvas.text(..., scale=2)` for digits readable at 15 ft (wall-look's two-pixel rule) | Now |
| jump | Standing-baseline calibration is game-level. Needs `Person.jump` (exists) and a stable `Body.id` (exists) | Fine |
| holewall | A pose library `arcade/poses.py: POSES: dict[str, tuple[Keypoint, ...]]` in body-relative units, plus `Person.pose(name, at, seconds)` in actors and `pose=NAME` in the REPL. `pose(named)` is explicitly deferred, but it is an actors.py change | Now: mechanism plus two poses |
| holewall | Scale-invariant keypoint comparison helper: translate to hip centre, scale by shoulder-hip distance. Could live in the game | Second plan |
| life | An actor for raw motion: `scene(..., motion=Callable[[float], np.ndarray \| None])` or `motion_rect(x0, y0, x1, y1, start, seconds)`, and `motion=` in the REPL. Today the only motion in tests is the body-box fallback, so "motion cells are stamped" cannot be tested apart from body boxes | Now |
| life | 8 Hz sub-tick: accumulate `dt` in the game | Fine |
| ambient | `attract="ambient"` passed in `main.py` (S1); a package under `arcade/games/ambient/` registers like any game | Now (one line) |
| ambient | In attract, any body returns to the menu, so "boids flee wrists" is only ever seen when launched from the menu. Accept it, and say so in the spec | Spec note |
| scream | A level ramp actor, `level_ramp([(t, level), ...])`; `loud(level)` is constant | Now, small |
| flappy, beat | `tempo`/`claps` exactly one hit per event (S10); REPL `beat=` for the whole step (S9) | Now |
| beat | Beat phase between onsets: the game tracks time since the last `beat`. Spec-level `beat` is `onset and bpm is not None`, so there are no predicted beats; document that | Doc |
| all | Soak fed with the inputs each game needs (B1); `strict` harness (S3); `state()` namespacing (S5); guarded registry import | Now |
| all | "Game over holds N s, then done()" is repeated in frogger, pong, flappy and holewall. Put a recipe in the authoring skill, not framework code | Second plan |

`Sensed` itself is sufficient for all nine. `GameInfo` needs one field, `exit_gesture`. The `Game` protocol needs one attribute, `scores`. `Canvas` needs float coercion, `blit_rgb` and `text(scale=)`. `actors` needs `Person.wrist`, `Person.pose`, a motion script, `level_ramp` and exact event ticks. The runner needs S1, S2, S3, S5, S7 and S8.

---

## Frame budget

Measured on the Mac (Apple Silicon, Python 3.12), per tick at 64x64:

| Item | Mac ms |
|---|---|
| `Sensed` construction for 2 bodies + 1 blob | 0.055 |
| `with_motion`, rasterize 2 boxes | 0.005 |
| `canvas.clear` | 0.019 |
| `runner.sense` | 0.002 |
| DDP packetise, 9 packets | 0.004 |
| paint update+draw | 0.090 |
| puppet update+draw | 0.185 |
| menu update+draw | 0.066 |
| `runner.tick` whole, puppet | 0.14 |
| LED look render at scale 8 (Mac preview only) | 3.2 |
| `FrameFeatures.update` 640x480 (camera thread) | 10.7 |
| `FrameFeatures.update` 320x240 (camera thread) | 2.7 |

A Pi 4 (Cortex-A72 at 1.8 GHz) runs this kind of small-array numpy and interpreter-bound code about 7 to 10 times slower than the Mac. That estimate comes from single-core benchmark ratios; I did not measure a Pi. Estimated per-tick overhead on the Pi, outside the game:

- **Runner bookkeeping, Sensed and clear:** about 1 ms.
- **Audio `latest()` features:** about 0.3 ms. They are computed on the tick thread (Task 17).
- **DDP send:** 9 `sendto` calls at 12 KB, about 0.4 ms.
- **GIL contention and scheduling jitter:** 5 to 10 ms of margin. The camera thread runs `FrameFeatures` at 20 to 25 ms per frame even at 320x240. The default GIL switch interval is 5 ms.

That leaves roughly 20 ms of the 33 ms tick for `update` plus `draw` on the Pi. **The plan's 8 ms Mac budget allows a game that takes about 60 to 80 ms on the Pi**, which means 12 to 15 fps. Recommendation:

- Set `BUDGET_MS = float(os.environ.get("ARCADE_TICK_BUDGET_MS", "2.0"))`. 2 ms on the Mac maps to about 15 to 20 ms on the Pi. Run the same test on the Pi in prototype week with `ARCADE_TICK_BUDGET_MS=20`.
- Measure p95 as well as the mean: `assert sorted(samples)[int(0.95 * n)] < 2 * BUDGET_MS`. Life's 8 Hz step and holewall's scoring are periodic spikes a mean hides.
- Time `runner.tick` through `run_headless` with `RecordingDisplay(keep_all=False)`, not bare `update`/`draw`, so a game that is cheap to update but makes the runner copy or rasterize a lot is caught.
- Note for the sensing lens: at 640x480 the Mac camera thread already takes 10.7 ms per frame. On the Pi, `FrameFeatures` must run on the low-resolution stream at 320x240 or less. `frame_bgr[labels == i].mean` does eight full-frame mask passes per frame; replace it with `cv2.mean(frame, mask)` on the component's bounding box.

---

## Checked and found OK

- **Everything as written passes.** All 109 extracted tests pass when the soak's hash seed happens to be favourable. Foundation: `make_display` duck-typing with `SimpleNamespace`, `FakeDisplay.last/count`, DDP `0x0B` and no scaling, sequence cycling 1 to 15.
- **Signatures agree across tasks.** I checked `Game` and `GameInfo` against `SpyGame`, `StubMenu`, `NullMenu`, `Menu`, `Paint` and `Puppet`. `MenuLike` (`selected`, `set_unavailable`, `set_status`) is implemented identically by `Menu`, `StubMenu` and `NullMenu`. `run_headless(cfg, font, game_cls, sensed_iter, seed)` and `helpers.run` match every caller. `Runner` constructor arguments match Tasks 8, 14 and 18. `Canvas` method names and argument orders match the menu, paint, puppet and shot tool. `Body` helpers (`nose`, `left_wrist`, `right_wrist`, `raised_wrist`, `both_hands_up`, `center`, `height`, `confidence`) match their uses in the runner, menu, puppet and REPL. `Person`, `moving_blob`, `claps`, `tempo`, `loud` and `scene` signatures match their uses in Tasks 8, 9, 12, 13, 14 and 20. `ScenarioReader`/`Writer` match Tasks 13 and 18. No mismatches found.
- **Runner tick order against spec 7.2.** Sense, build, exit, idle, update, draw, push. `done()` returns to the menu; the last game frame is pushed on that tick and the menu shows on the next. The 30-tick glitch then menu works, hide-after-three works and `set_unavailable` propagates. `dt` is clamped to 0.1. The fake-clock loop keeps 30 Hz. A raising source gives empty `Sensed` with status off, and a push failure is logged.
- **Menu layout on 128x32.** Six 10x10 tiles (8x8 icon plus a one-pixel margin) with a one-pixel gap make a 65x21 grid. With the 8-row title band that is 29 of 32 rows. `y0 = 1`, and the grid spans x = 31..95, so the status glyph at (126, 0) and (127, 0) never overlaps a tile. On 64x64 the 3x4 grid is 32x43, plus 8 rows, in 51 of 64. Layout tests pass at 96x48 and 128x64, and my probes at 32x32, 48x16 and 8x8 laid out and drew without raising.
- **Menu behaviour.** Dimming for missing `needs` and hidden games, the title tile never selecting, pass-through never launching, and dwell selecting at about 1.03 s all pass. Twelve slots with only two registered games draws two icons, the title icon and nine empty slots, with no errors.
- **Review Focus items.** Focus 1 (NaN or out-of-range keypoints clamp with confidence 0) passes. Focus 4 (garbage scenario lines are skipped and counted) passes.
- **Budget test logic.** The perf test is correct for what it measures. Paint and puppet cost 0.09 and 0.19 ms on the Mac.
