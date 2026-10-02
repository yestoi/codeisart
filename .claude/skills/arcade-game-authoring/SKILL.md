---
name: arcade-game-authoring
description: Use when writing or changing a game under arcade/games/
---

# Authoring a wall arcade game

A game is small: four files and a name in a tuple. The rest (the runner, the lobby, the flash governor, the
oracle that judges feel) is not yours to change from a game task. Read `arcade/games/pong.py` and
`tests/arcade/test_pong.py` first; Pong is the worked example for everything below.

Sources: spec `docs/superpowers/specs/2026-09-26-wall-arcade-design.md` sections 7.1, 8.1, 9.1 to 9.3 and 11;
the it07 plan `docs/superpowers/plans/2026-09-28-it07-oracle-for-games.md`.

## 1. What a game is

Four files, all named after the game (`<name>` is a lowercase identifier, the module name):

| File | Holds |
|---|---|
| `arcade/games/<name>.py` | the class, `GAME = <Class>`, the scenario scripts |
| `arcade/games/<name>_bots.py` | `BOTS = {"good": ..., "lazy": ...}` and `won(state)` |
| `arcade/games/<name>_feel.toml` | budget overrides, each with a `reason`, and `[fidelity]` |
| `tests/arcade/test_<name>.py` | the game's tests, modelled on Pong's |

Plus the name in `MENU_ORDER` in `arcade/games/__init__.py` (ten names, in ship order; a game the spec lists is
already there, so usually you add nothing). Discovery imports only `MENU_ORDER` names, so `pong_bots` is never
taken for a game. `GAME.info.name` must equal the module name, or the game is skipped with a log line. A module
that fails to import is skipped, not fatal: read the log.

Never edit `arcade/game.py`, `runner.py`, `juice.py`, `flash.py`, `brightness.py`, `headless.py`, `bots.py`,
`feel.py`, `pattern.py`, `feel_budgets.toml` or the lobby for a game. A need that only they can meet goes in your
report, not in code.

## 2. The protocol (frozen at `game-protocol-v1`)

`arcade/game.py` at the tag: `GameInfo`'s ten fields and their validation; `Game`'s `info`, `scores`,
`SCENARIOS`, `CAPTION_KEYS`, `PHASES`, `reset(size, rng, fx)`, `update(sensed, dt)`, `draw(canvas)`, `done()`,
`debug_state()`; `REQUIRED_SCENARIOS`, `INPUTS`, `KINDS`, `LAYOUTS` (a data value, `{"128x64"}` since Q33), `RUNNER_KEYS`, `reserved()`,
`icon_from_rows`. A canary test (`test_protocol_members_are_the_frozen_set` in `tests/arcade/test_game.py`) holds
the list; a game never needs it changed. Known later changes, each with a journaled reason: M5's `Blob.id`, `vx`,
`vy` and per-input availability (C35) in `Sensed`.

`GameInfo(name, title, verb, icon, needs, layouts, players, exit_gesture, kind, abandon_seconds)`:

- `title`: one or two words, shown at 2x on a door. `verb`: the one action ("COPY", "BLOCK"), shown at 2x on the
  opening pictogram. `icon`: `icon_from_rows([...])`, 16 rows of 16 characters, `#` on and `.` off, 2 px strokes.
- `needs`: a subset of `INPUTS` = `pose`, `blobs`, `motion`, `audio`. Declare what the game reads, no more: a game
  whose needs the sources cannot give is never offered. No game a stranger meets first depends on `audio`.
- `layouts`: a subset of `LAYOUTS` = `{"128x64"}` (the default), the design layout: four 64x32 panels, 2 x 2
  (Q32, Q33). A game declares it and still runs at any size (the soak adds 96x48, only run and checked for
  legibility). Every declared layout gets full feel budgets; `feel.measure` raises `ValueError` for a layout the
  game does not declare.
- `players`: 1 or 2. `exit_gesture`: False only when play itself needs both hands up.
- `kind`: `control`, `toy` or `score` (one of `KINDS`). It picks the feel budget set (section 7).
- `abandon_seconds`: None (use the config's `leave_seconds`) or a finite number over 0.
- A bad value raises `ValueError` at import, so the game is skipped at discovery.

### What the runner passes

- `scores` (the per-game view, `Scores.for_game(name, layout)`) is set before `reset`.
- `reset((w, h), random.Random, Juice)` on a fresh instance per launch. Two ints, the launch's seeded rng, the
  launch's effects object. State across plays goes through `scores` only. Take every random choice from that rng,
  never from `random` or `time`, so second plays differ and tests repeat.
- `update(Sensed, TICK)` every tick (30 Hz, `dt` clamped to 100 ms) with the runner's `player` and `player2`
  set. Read `player` and `player2`, never `bodies[0]`. Blobs arrive already filtered to the zone. While
  `fx.freeze` holds, `update` is skipped and `draw` still runs.
- `draw(canvas)` on a cleared `Canvas`. It must work right after `reset()`, before any `update`.
- The runner then renders the effects over your frame, applies shake, then the flash governor, then the
  brightness limiter, then pushes.

The lobby passes nothing but the launch. A game never pushes a frame, never saves an image (`.save` appears only
under `tools/`), never reads the config, never knows which machine it runs on. An exception in `__init__`,
`reset`, `update`, `draw` or `done` sends the session to the lobby; three in a runner start hide the game until
the dusk restart. In tests `strict` (the default) re-raises instead.

Every call that builds `Sensed` or `Audio` in a test uses keywords (`Sensed(t, camera_t=..., bodies=...)`).

## 3. `debug_state()`

A small flat dict of the game's own truth, stable keys, listed in the game's docstring. It is the game's claim;
the generic tests and the bots check it.

- `phase`: a value from the class's `PHASES` (default `("play",)`; typically `intro`, `play`, `over`, `card`).
  **Leave `play` between rounds** (a serve, a point, the end): the session cap only ends a session outside
  `play`, so a game that never leaves it is never capped. The soak asserts every traced phase is declared;
  the `good` bot's plays must reach every phase in `PHASES`, so do not declare one the game cannot reach.
- `score`: when the game has one. The end card and the sessions log read it (a finite number, else None).
- `active`: `True` or a numpy bool on any tick the game got meaningful input. `1`, `"yes"` and numpy ints do not
  count. Without it the runner shows "STILL PLAYING? HAND UP" and then ends the session. Use `bool(...)`.
- `*_xy`: the wall pixel coordinates of a visible entity, as a pair (`ball_xy`, `left_xy`). A generic test
  checks the pixel at each `_xy` is lit. Keep them inside the wall (Pong clamps to `w - 0.01`).
- No reserved keys: never `arcade.game.reserved(key)`: `game, t, idle, attract, hidden, crashes, glitch,
  flash_held_ticks, player, present`, and anything starting `fx_`.
- `CAPTION_KEYS`: the `debug_state` keys printed under each contact-sheet cell (Pong: `phase`, `left`,
  `right`). Every one must be a key you return.

## 4. Scenarios, bots and the oracle

`SCENARIOS` is a read-only mapping of scripts built with `arcade/sources/actors.py` (`Person`, `scene`,
`moving_blob`, `motion_rect`, `claps`, `tempo`, `crowd`). Give it a `MappingProxyType`. Every game has at least
`REQUIRED_SCENARIOS = ("canonical", "idle_body", "nobody")`:

- `canonical`: **2 s of an empty wall** (attract shows, feel and the evidence GIF start from here), a walk-up
  (`Person(x, id=1)` arrives), the raised hand that launches the game from the lobby (`raise_hand`), then play
  as a player would. Its input events are what response latency and fidelity are measured on. About 100 s.
  `feel.measure` launches it through `run_headless(..., lobby=Lobby([game_cls], cfg))`, the small lobby, so
  without the walk-up and the raised hand nothing launches, and the game's name must be in
  `arcade.attract.lobby.MENU_ORDER` (the list in `arcade.games`) or `measure` raises `ValueError` ("<name>
  never launched from the lobby").
- `idle_body`: one `Person` standing in the zone without moving (about 60 s). The game must score nothing, store no
  best (`scores.best(name, "128x64")` stays None) and hint within three seconds. C41: points need movement in the
  round, and a best needs movement in the game; an idle body earns neither.
- `nobody`: an empty wall (about 30 s).
- Other scripts (Pong's `solo` and `duel`) are yours. Winning and losing are not scripts: bots judge them.

`arcade/bots.py` plays a game closed-loop through the real runner. Your `<name>_bots.py` gives it:

```python
BOTS = {"good": Good, "lazy": Lazy}     # zero-argument factories of a Bot
def won(state: dict) -> bool: ...        # from the last debug_state(): the human side won
```

A bot has `reaction_ticks`, `noise`, and `__call__(state, t) -> Move | None`. It sees `debug_state()` that many
ticks late (`{}` before), so keep everything it needs in `debug_state`. `Move(x=0.5, hand="right",
wrist_y=None, near=None, pose=None)`: `x` is in **zone coordinates**, 0 to 1 across the play zone (not wall pixels); `wrist_y` is the
wrist in the reach box, 0 top to 1 hip height, None for hand down; None instead of a Move is nobody in view.
`hand="both"` moves both wrists to `wrist_y` with one noise draw (a two-arm gesture: Flap's bot flaps with it).
`pose="<name>"` holds `arcade.poses.POSES[name]` on the tick (an unknown name raises `ValueError`; Copy Me's bot
copies the target with it); a `wrist_y` then moves the hand's wrists over the pose. A pose takes no noise (only `x`,
`wrist_y` and `near` do), so a pose bot's wins hang on the game's rng, not on the bot's.
`arcade.bots.Nobody` is the no-input bot. `play(game_cls, bot, seed, layout)` adds the reaction delay and
seeded noise (clamped to 0..1) and stops on `done()`, or when the session ends otherwise (a game whose
`done()` never fires ends at the leave or inactive rule, or at `MAX_PLAY_SECONDS` = 180).
`play` and `win_rate` default the layout to the game's one declared layout. `bots.seeds(game_cls, layout, n)` gives `zlib.crc32(f"{name}:{layout}:{i}".encode())`.

Difficulty bands (win rate over 20 seeds, per `score` kind): `good` at least 0.7; `lazy` 0.1 to 0.7 and fewer
than `good`; no input at most 0.05. Round length under `good`: a median of 20 to 120 s. Tune the game's own
speeds and bot skill to sit inside the bands. Never loosen a band: that is the owner's.

## 5. Budgets (`arcade/feel_budgets.toml`, `<name>_feel.toml`)

`arcade/feel.py` (`measure`, `judge`, `report`) computes the metrics through `run_headless`; `budgets(game_cls,
layout)` layers the kind's defaults, then the kind's layout table, then your file's `[budgets."<WxH>"]`.

Default metrics: `response_ticks` (max 2; latency: the first tick after a probe on which any pixel differs),
`response_px` (min 12; magnitude: the pixels that differ `LATENCY_TICKS` = 2 ticks after the probe; a clamped
control is no probe), `fidelity` (min 0.8), `range` (min 0.6), `lit_fraction` (0.01 to 0.5),
`dim_fraction` (max 0.1), `liveliness` (min 0.001), `flash_area_raw` (max 0.1), `square_flashes` (max 6),
`phases_reached` (1.0), `round_seconds` (20 to 120); `score` also `win_good`, `win_lazy`, `win_none`. `toy` is the
control set without `round_seconds`, `fidelity` and `range`.

`<name>_feel.toml`:

```toml
[fidelity]                      # what to correlate: the actor's input against the controlled _xy axis
input = "cursor_y"              # "cursor_x" | "cursor_y" | "zone_x" | "near" | "far", from sensed.player
xy = "left_xy"                  # a *_xy key of your debug_state
axis = 1                        # 0 = x, 1 = y

[budgets."128x64"]              # per-layout overrides; Pong's file (arcade/games/pong_feel.toml, P3) is the
dim_fraction = ...              # model for the exact shape, and arcade/feel.py's `budgets` docstring is its law
```

A gesture has no axis, yet a `score` game is judged on `fidelity` and `range`. Give the gesture a gauge: a small
marker that follows the hand's height (`Cursor`, then a `Glide`), with short ticks at the lines the gesture must
cross, and point `[fidelity]` at it (`input = "cursor_y"`, `xy` the marker's `_xy`, `axis = 1`). It is the measured
control and it teaches the gesture; the canonical sweeps the hand slowly over the gauge's span inside the first 20 s.
Flap is the worked example (`wing_xy`, its ticks at `V_ABOVE` and `V_BELOW`).

An override needs a non-empty `reason` or `budgets()` raises `ValueError` naming the metric. An override is for
something the game does on purpose (Pong's dashed net is dim), never to make a failing number pass: fix the game
first, and never loosen a win band. Report every override with its metric and reason.

`pytest -m feel` asserts the budgets (`tests/arcade/test_oracle.py`, Pong in it07).

## 6. The flash rule

The runner's governor holds what goes over (per pixel, six transitions in a second), and holds are counted in
`flash_held_ticks`. Your job is to never need it: raw output flashes at most 10 percent of the wall, and pushed
frames pass `square_flashes <= 6`.

- Shake, flash and bursts each keep the rule alone, by construction (`arcade/juice.py`): shake jumps at most every
  0.25 s (max 8 px); `flash` is a hold, one rise and one fall, and returns **False** (doing nothing) while one shows
  or within 0.5 s after; a burst within 32 px of one accepted in the last 0.5 s is dropped. Use them freely,
  and check the return value where it matters (do not assume the flash happened).
- Banner text, pops and combinations are the game's to pace: a banner whose text changes every tick, a pop every
  tick, or a burst over a flash can flash a small part of the wall. Change banner text at most a few times a
  second.
- Your own drawing keeps it: no blinking a large area, no full-field luminance change faster than 3 a second.
  Game over is a hold and one slow fade, never a red strobe. Saturated red counts double.
- A player's figure (`figure_rect`, `draw_figure`) placed from raw `zone_x` jitters a column under real noise, and
  the whole outline flips with it: 0.1006 raw in the it08 note, over the rule. Give its column the lobby's backlash
  (`COLUMN_SLACK = 1`, `arcade/attract/lobby.py:49,181`): for the same person the column moves only past the slack
  of the one held; a new id takes its column at once. Keep the two lines in the game's own file (Copy Me and Freeze
  do), and no `Glide` on a figure: it follows `zone_x`, so fidelity and range are measured on it.
- No reversing stripes over a quarter of the wall: more than five light-dark band pairs of equal width that
  reverse, oscillate or move (`arcade/pattern.py`, `PATTERN_AREA = 0.25`; static stripes count 0). A dashed net is
  fine; a scrolling grating over the field is not.
- Beat-driven visuals change hue or shape on onsets and pulse luminance only on a locked tempo at or below
  180 bpm. The soak runs `claps` at 12 Hz, `tempo(180)` and an alternating motion grid: the game must stay under
  10 percent raw.

## 7. Feel guidance (spec 11)

- No sound, so every event needs a visible response within two ticks and at least 12 pixels changed
  (`response_ticks` <= 2 is latency, `response_px` >= 12 is magnitude, `RESPONSE_PX` = 12). Acknowledge a gesture on the tick it is recognised
  (`fx.echo(player, kind)`).
- Camera latency is already 100 to 200 ms: use hysteresis, and never smoothing that costs a tick.
- Map the middle half of the reach box to the full playfield (`fidelity` and `range` measure this).
  The wrist in the reach box comes through `Cursor` and `Glide`, the body's depth through `Depth` (Controls);
  raw frame coordinates are never a cursor.
- Hint within three seconds of a still body (`idle_body`).
- Rounds of 20 to 120 s; a game ends in 45 to 90 s or on a clear result.
- Failure and success differ in hue and motion, not just in text.
- Legible from 2 to 10 m: 2 px strokes for anything that must read at distance, text at 2x for scores (spec 7.4; `feel.SCORE_SCALES` is `(1, 2)` today and becomes `(2,)` after Pong's 2x
  lands, so the oracle then finds only 2x scores), no dark
  greys (a lit pixel with every channel under 140 is dim, and `dim_fraction` counts it). Colours saturated with
  the low channels at 0 (`(255, 120, 0)`, `(0, 200, 0)`, `(255, 255, 255)`): gamma is unknown. One colour per
  game apart from players (`PLAYER_COLORS`: amber, then blue). Light fewer pixels late at night.
- The runner draws a 2 px marker in the player's colour on the bottom row under them in every game, and the
  echoes: keep that row and the glyph area free of anything the player must read.
- Coordinates may be floats: the canvas rounds and clips.

## Controls (C44)

A game reads its control from `sensed.player`, through one of the helpers in `arcade/input.py`. Pick the control
the game needs; do not invent a fourth.

- **Depth** (the whole body, one axis): `Depth(grace=capture_grace(CAMERA_FPS))`, then `depth.update(body, t,
  sensed.camera_t)` every tick gives 0 to 1, 1 nearest the camera, or None for a dropout. It reads from where the
  player started: the first capture after `reset()` is 0.5, and the span is `DEPTH_SPAN` (0.6, ln of the size ratio
  across the whole range; `Depth.ratio(value)` inverts it). A player pinned at an end for `RECENTRE_SECONDS` drags
  the centre inward, so nobody is stuck at an end. Call `reset()` when another body takes the seat. Pong is the
  worked example: a step in raises the paddle, a step back lowers it.
- `Body.measured` is False while the tracker has never seen the track's nose and a hip (its scale is the shoulder
  fallback); `Depth` takes the first measured capture without a jump (C47), so a game does nothing about it.
- **The hand, pointing**: `Cursor.update(body, t)` gives the wrist in the reach box; pass its value through a `Glide`
  (`glide.update(value, t, sensed.camera_t)`) so the control moves on every tick and not ten times a second (the
  camera captures at `camera_fps`, 10 by default; a raw capture holds for three ticks). The Glide interpolates and
  never extrapolates; it adds at most one capture period of lag.
- **Side to side**: `zone_x`, the hips across the play zone, 0 to 1.
- Never read `body.cursor` raw for a control: it steps at the capture rate. `Cursor` and `Glide`, or `Depth`.
- Declare the control in `<name>_feel.toml` `[fidelity] input`: `cursor_x`, `cursor_y`, `zone_x`, `near` or `far`.
  `near` is ln(scale) (rises as the player steps in), `far` is -ln(scale) (rises as the player steps back). Pick the
  one whose sign matches the `_xy` axis you correlate against (Pong: `far`, with y down the wall).
- Bots: `Move(x=..., wrist_y=..., near=...)`. `near` is a Depth value, 0 far to 1 near, None for the start size; the
  bot's body steps at a body's pace (`BODY_RANGE_SECONDS` = 0.8 s for the whole range), so a bot cannot teleport a
  paddle. A hand game's bot drives `wrist_y`. Scripts use `Person.scale_to(ratio, seconds)`.
- A still body scores nothing. A point counts when the control TRAVELLED over the rally, its max minus its min at
  least a share of the control's range (C42, Pong's `TRAVEL_SHARE`), a threshold above what `degrade(**REAL_NOISE)`
  makes a still body jitter (a still body's Depth wanders several pixels of a 48 px travel). Judging a 1 px tick of
  movement lets noise score. A best is stored only when the player travelled in the game (C41, C42).

## 8. The effects toolkit (`fx`, spec 8.1)

`fx.shake(px, seconds)`, `fx.flash(color, seconds)`, `fx.burst(x, y, color, n)`, `fx.pop(text, x, y, color)`
(rises 6 px over 0.8 s), `fx.banner(text, seconds)` ("3", "2", "1", "GO!", "BEST!"), `fx.freeze(seconds)`
(hit-stop), `fx.celebrate(color)`, `fx.echo(player, kind)`; `fx.frozen`. Call them from `update`, not `draw`. The
runner renders them after your `draw`. Bad numbers (NaN, negative, not a number) make a call do nothing; nothing
raises into a game. Particle pool 96.

## 9. The card, then `done()`

The runner ends the session on `done()` (reason `done`); the lobby then draws the end card: the result from your
`debug_state()["score"]`, "BEST!" on a record, "HAND UP = AGAIN", and "NEXT: RAISE A HAND" when someone waits.
So a game does not draw the card itself. It makes the result readable, then gets out of the way:

1. On the deciding event, record the score once: `self.scores.record(value)` (solo play; a duel records
   nothing, and a duel's card shows player 1's points, bests for solo only). `scores.best()` and
   `last_night()` are there for "BEST!" logic.
2. Enter a final phase (Pong's `over`) that holds the result on the wall: the final score, a `fx.celebrate` or a
   slow fade, no strobe. `phase` leaves `play`.
3. `done()` returns True only after that hold (`phase == "over" and phase_t >= OVER_SECONDS`), never on the tick
   the result appears.
4. `score` in `debug_state()` stays the final value through the hold.

Whoever is played, walking away ends the session earlier ("left"): a game must tolerate `update` stopping at any
tick.

## 10. The test template (Pong's module)

`tests/arcade/test_pong.py` is the template: copy its shape.

```python
def seed(layout, i): return zlib.crc32(f"<name>:{layout}:{i}".encode())   # never hash() of a str
def make(size=WALL, i=0):     # a game reset the way the runner resets it, for tests that poke state
    game = Game(); game.scores = Scores(None, lambda: OPENING_NIGHT).for_game("<name>", layout)
    game.reset(size, random.Random(seed(layout, i)), Juice(random.Random(1), size)); return game
```

- `from tests.arcade.helpers import make_cfg, run`: `run(GameCls, sensed_iter, size, font5x7, ticks=...,
  seed=...)` returns `(frames, game, runner)` through the real runner (strict). The `font5x7` fixture is in
  `tests/arcade/conftest.py`.
- Helpers to write: `step` (one tick with `player`/`player2` set as the runner sets them, via
  `dataclasses.replace(frame, player=..., player2=...)`), `drive` and `advance(game, frames, phase)`.
- Parametrize over the layouts the game declares, and take seeds from
  `zlib.crc32`, printed in assertion messages. Time CPU with `time.thread_time`, never wall time.
- Cover: registration and declared `info`, `PHASES` and `CAPTION_KEYS`; the input moves the thing it should; each
  phase transition; the score and `done()` after the hold; `debug_state` has no reserved key, `active` is a
  bool, every `_xy` pixel is lit; `test_required_scenarios_start_with_an_empty_wall`;
  `test_canonical_drives_the_lobby_to_pong` (`lobby=Lobby([Game], cfg)`: `game == "<name>"` within a tick of the
  raise); `test_idle_body_scores_nothing`; `test_bots_module_is_found`; `test_good_beats_lazy_beats_nobody`
  (5 seeds); `test_good_round_length_in_band`; `test_feel_file_overrides_have_reasons`.
- `tests/arcade/test_all_games.py` runs the soak, the flash rule, the tick budget (mean under
  `ARCADE_TICK_BUDGET_MS`, 2.0; p95 twice that), the required scenarios and the `good`/`lazy` bots for every
  registered game with no work from you. It fails your game when the game breaks the rule; do not skip it.

## 11. Run, then show the evidence

Test command, from the checkout or worktree root, one at a time, no command over 10 minutes:

```
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs
```

Say what your game adds to the suite time (a task adds at most 20 s of CPU). The feel table for one game:
`arcade.feel.report(GameCls, "128x64", seeds=arcade.bots.seeds(GameCls, "128x64", 20))` gives
`{"metrics", "budgets", "failures"}`.

The evidence package, from the repo root (the operator runs it in verify; writes `feel.json`, `games.md`, and per
game and layout the plain, led and distance PNGs, a canonical GIF, a trace and a timeline):

```
.venv/bin/python -m tools.arcade_evidence --iteration N --games changed|NAME[,NAME] [--since REV] [--out DIR] \
    [--seeds 20] [--allow-dirty]
```

To look at a run by hand: `python -m tools.arcade_shot <game> [--lobby small] [--scenario NAME]
[--raw-vs-pushed] [--out STEM]`. An all-black run is refused without `--allow-black`, naming the games'
`needs`. Every file carries the git sha; a mismatch with HEAD is a tooling defect, fixed before judging.

What stays human: whether a stranger gets it in ten seconds, whether it feels good or embarrassing, total latency
with the real camera, colour taste, night glare. The metrics find dull and broken games; they cannot find good
ones.

## Checklist before you say done

- The four files exist; `GAME` is set; `info.name` equals the module name; the name is in `MENU_ORDER`.
- `SCENARIOS` has `canonical` (2 s empty first), `idle_body`, `nobody`.
- `debug_state`: `phase` in `PHASES`, leaves `play` between rounds, `active` a real bool, `_xy` inside the wall
  and lit, no reserved key; `CAPTION_KEYS` all present.
- `<name>_bots.py` has `good`, `lazy` and `won`; bands met without loosening; overrides each carry a reason.
- No push, no save, no config read; colours saturated; every random choice from the injected rng.
- The full suite passes; you say what it added in time.
