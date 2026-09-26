# Wall Arcade Design

Date: 2026-09-26. Status: approved in conversation, awaiting written review.

A camera-and-microphone-driven arcade for the two-panel LED prototype, launched from a menu you
steer with your hand. Built on the Mac before hardware arrives, by agents that verify their own
work headlessly, then run unchanged on the Raspberry Pi 4 through the same display pipeline the
Code is Art show daemon uses.

This is a separate deliverable from the Code is Art installation
(`2026-09-22-code-is-art-design.md`). It shares the repo, the Pi, the Colorlight card, and the
DDP path, and it has no fixed deadline.

## 1. Goals

- A stranger walks up at a festival and is playing something within ten seconds, unprompted.
- Every game runs on the Mac against the laptop webcam and microphone, and on the Pi against the
  Raspberry Pi AI Camera and a USB microphone, with no game code that knows which it is on.
- Every game is verifiable without hardware: scripted inputs in, frames out, assertions on pixels,
  and PNG contact sheets an agent can look at.
- Twelve entries in the first version: the menu and the eleven games in section 8.

### Non-goals

- Sound output. The microphone is an input only. No speaker, no sound effects.
- Radar, time-of-flight, or button input. The Sensed record (section 4) can grow fields for them
  later without changing games.
- Name entry for high scores. There is no keyboard.
- Anything from the show daemon beyond the foundation modules named in section 3.

## 2. Hardware and layouts

- Two Wired Watts outdoor P5 modules, each 64 wide by 32 tall, on one chain of the Colorlight
  5A-75E, driven by Falcon Player over DDP from the Pi 4 (see the Code is Art spec, section 3.2).
- The panels are physically fixed in one arrangement per session: side by side (128 by 32) or
  stacked (64 by 64). The arcade reads width and height from config and every game adapts. The
  test suite runs every game at both sizes.
- Dev machine: Mac with built-in webcam and microphone. Pi: Raspberry Pi 4, AI Camera (IMX500,
  pose model runs on the sensor), USB microphone. A white floodlight on the play area at night.

## 3. Foundation from the show daemon plan

Before any arcade code, implement these tasks from `docs/superpowers/plans/2026-09-22-show-daemon.md`
exactly as written, with their tests: Task 1 (scaffold and config), Task 2 (font), Task 5
(display protocol, fake and SDL backends), and the DDP backend task. This gives one display
pipeline for both projects.

One amendment to Task 5: `make_display` reads the fields it needs (`width`, `height`, `backend`,
`sdl_scale`, `ddp_host`, `ddp_port`) off whatever config object it is given, rather than requiring
`show.config.Config`. The arcade passes its own config object with the same field names.

No other show daemon task is part of this work.

## 4. Architecture

One Python process, one fixed-tick loop at 30 Hz. Each tick the runner assembles one `Sensed`
record from the camera and audio sources, hands it with the elapsed time to the current game,
and pushes the game's canvas to the display.

```
camera source ─┐
               ├─> Sensed ─> runner ─> game.update / game.draw ─> Canvas ─> Display.push
audio source  ─┘                 │
                                 ├─ menu (a Game)
                                 ├─ exit gesture, idle attract, crash guard
                                 └─ injected clock and rng
```

### 4.1 Package layout

```
arcade/config.py                 ArcadeConfig, load_config(path)
arcade/sensed.py                 Sensed, Body, Keypoint, Blob, Audio dataclasses
arcade/sources/camera.py         CameraSource protocol, make_camera(cfg), BodyTracker
arcade/sources/pose_mediapipe.py Mac: OpenCV webcam + MediaPipe Pose Landmarker
arcade/sources/pose_imx500.py    Pi: picamera2 + on-sensor pose model
arcade/sources/blobs.py          bright-blob and motion-grid extraction from a frame
arcade/sources/audio.py          AudioSource protocol, sounddevice implementation, features
arcade/sources/replay.py         ReplayCamera and ReplayAudio from a scenario file
arcade/sources/actors.py         scripted synthetic bodies, blobs and audio for tests
arcade/sources/record.py         write a live session to a scenario file
arcade/canvas.py                 Canvas: pixel, line, rect, circle, fill, text (show.font)
arcade/game.py                   Game protocol, GameInfo
arcade/menu.py                   hover-and-dwell menu, itself a Game
arcade/runner.py                 tick loop, exit gesture, idle attract, crash guard
arcade/scores.py                 best-of-the-night persistence
arcade/main.py                   CLI
arcade/games/__init__.py         registry, menu order
arcade/games/<name>.py           one file per game (section 8)
arcade/look.py                   render modes for previews: plain, led (round dots, gap, glow, gamma), distance
tools/arcade_shot.py             headless run -> PNG contact sheet, any render mode
tools/arcade_play.py             step-verb REPL for agents: step N <actor>, state, shot
tools/fetch_models.py            downloads the MediaPipe model file (gitignored)
.claude/skills/                  project skills: arcade-verify, wall-look, arcade-game-authoring
tests/arcade/                    one test module per module and per game, helpers, conftest
```

### 4.2 Dependencies

- Everywhere: numpy, pygame (SDL preview, already in the daemon plan), opencv-python,
  sounddevice.
- `mac` extra: mediapipe.
- `pi` extra: picamera2.
- Tests need none of the hardware extras. Modules that import mediapipe or picamera2 do so
  inside the source class, never at package import time.

Agent tooling, installed on the dev machine, not code dependencies: the MediaPipe skill from
`damionrashford/media-os`; `game-feel`, `procedural-gen` and `performance-optimization` from
`gamedev-skills/awesome-gamedev-agent-skills`; `pixel-art-sprites` from
`absolutelyskilled/absolutelyskilled`; and the official `skill-creator` and `pyright-lsp`
plugins. Not `pygame-core`, which teaches variable timestep and sprite groups this project does
not use.

### 4.3 Config

`arcade.toml`, flat, keys are fields of `ArcadeConfig`, unknown keys rejected:

| Field | Default | Meaning |
|---|---|---|
| `width`, `height` | 64, 64 | wall size in pixels |
| `backend` | `sdl` | `sdl`, `fake`, `ddp` |
| `sdl_scale` | 8 | preview window scale |
| `ddp_host`, `ddp_port` | `127.0.0.1`, 4048 | Falcon Player |
| `camera` | `mediapipe` | `mediapipe`, `imx500`, `replay`, `none` |
| `camera_index` | 0 | OpenCV device index on the Mac |
| `audio` | `sounddevice` | `sounddevice`, `replay`, `none` |
| `scenario` | `""` | scenario file for the replay sources |
| `mirror` | true | flip x so the player's right is screen right |
| `brightness` | 0.4 | cap applied before push, never exceeded by a game |
| `gamma` | 2.2 | curve the previews model; set to 1.0 if the card applies gamma itself |
| `look` | `led` | preview render mode: `plain`, `led`, `distance` |
| `dwell_seconds` | 1.0 | menu hover time to select |
| `idle_seconds` | 60 | no presence before attract |
| `exit_seconds` | 1.5 | both wrists above head to leave a game |
| `data_dir` | `./data` | scores file location |

## 5. The Sensed record

The only input games see. Built once per tick by the runner from the latest source results.

```python
@dataclass(frozen=True)
class Keypoint:  x: float; y: float; conf: float        # normalized 0..1, already mirrored
@dataclass(frozen=True)
class Body:      id: int; box: tuple[float, float, float, float]; keypoints: tuple[Keypoint, ...]  # 17, COCO order
@dataclass(frozen=True)
class Blob:      x: float; y: float; size: float; color: tuple[int, int, int]
@dataclass(frozen=True)
class Audio:     level: float; peak: float; onset: bool; beat: bool; bpm: float | None
@dataclass(frozen=True)
class Sensed:
    t: float                     # seconds since runner start
    bodies: tuple[Body, ...]     # tracked, stable ids, most confident first
    blobs: tuple[Blob, ...]      # brightest first, at most 8
    motion: np.ndarray           # bool, shape (height, width), true where the scene changed
    audio: Audio
```

- COCO keypoint order: nose, eyes, ears, shoulders, elbows, wrists, hips, knees, ankles. Helper
  properties on `Body` for `nose`, `left_wrist`, `right_wrist`, `raised_wrist` (the higher wrist
  if above the nose, else None), and `center`.
- Mirroring is applied in the camera source, once, when `mirror` is true.
- `motion` is frame differencing thresholded and downsampled to wall resolution. It needs no
  model and works on any camera, so ambient modes and Life work even without pose.
- `BodyTracker` assigns ids by nearest centroid across consecutive frames, drops a body after
  ten frames unseen, and never reuses an id within a session.
- Audio features from a rolling 16 kHz mono buffer: `level` is RMS over the last 50 ms mapped
  to 0..1 with a slow automatic gain so a quiet field and a sound camp both give usable range;
  `peak` is the raw peak; `onset` is true on a tick where short-term energy exceeds three times
  the rolling median; `beat` and `bpm` come from the last eight onset intervals when they agree
  within 15 percent, else `beat` is false and `bpm` is None.

## 6. Sources

Every source runs its capture in a thread and exposes `latest()` without blocking. The runner
never waits on a sensor. A source that cannot open its device logs once, reports
`available = False`, and returns empty results forever; the menu shows this in its status glyph.

### 6.1 Camera

`CameraSource.latest() -> tuple[bodies, blobs, motion]`.

- **pose_mediapipe** (Mac): OpenCV capture at 640 by 480, MediaPipe Pose Landmarker in video
  mode with `num_poses = 2`. The 33 MediaPipe landmarks map to the 17 COCO points by index.
  Blobs and motion come from the same frame through `blobs.py`.
- **pose_imx500** (Pi): picamera2 with the IMX500 pose model from the Raspberry Pi model zoo.
  Keypoints arrive already in COCO order. A low-resolution stream from the same camera feeds
  `blobs.py`.
- **blobs.py**: convert to grayscale, threshold at the 99.5th percentile with a floor, connected
  components, keep the eight largest, average the color under each. Motion: absolute difference
  against the previous frame, threshold, box-downsample to wall size, boolean.
- **replay**: reads a scenario file and returns records in order at the runner's tick.
- **none**: always empty.

### 6.2 Audio

`AudioSource.latest() -> Audio`.

- **sounddevice**: default input device, 16 kHz mono, callback appends to a ring buffer of two
  seconds; features computed in `latest()`.
- **replay** and **none** as for the camera.

### 6.3 Scenario files

JSON lines, one Sensed record per tick at 30 Hz, `motion` stored as a packed bit string.
Produced by `record.py` from a live session (`arcade record --seconds 20 out.jsonl`) or by
actors. Recordings are for regression and for looking at real data; tests use actors.

### 6.4 Actors

Generators in `actors.py` that yield Sensed records for a given tick count, composable with
`combine(*actors)`. First set: `stand(x, y)`, `walk(x0, x1, seconds)`, `raise_hand(at, seconds)`,
`jump(at, height)`, `both_hands_up(at, seconds)`, `blob(path, color)`, `silence()`,
`claps(times)`, `tempo(bpm)`, `pose(named_pose)`. Deterministic: no randomness, no wall clock.

## 7. Runner, game interface, menu, canvas

### 7.1 Game

```python
@dataclass(frozen=True)
class GameInfo:
    name: str            # registry key, file name
    title: str           # scrolled in the menu
    icon: np.ndarray     # 8x8 bool
    needs: frozenset[str]   # subset of {"pose", "blobs", "motion", "audio"}

class Game(Protocol):
    info: GameInfo
    def reset(self, size: tuple[int, int], rng: random.Random) -> None: ...
    def update(self, sensed: Sensed, dt: float) -> None: ...
    def draw(self, canvas: Canvas) -> None: ...
    def done(self) -> bool: ...
    def debug_state(self) -> dict: ...
```

`debug_state` returns a small flat dictionary of the game's own truth (for Frogger: lane,
column, lives, crossings; for the menu: hovered tile, dwell fraction). Tests and the agent
tools assert on it before they look at pixels. Keys are stable per game and listed in the
game's docstring.

A fresh instance per launch. Games hold no state across plays except through `scores.py`.
Games never touch the display, the config, or the frame array directly.

### 7.2 Runner

- Tick at 30 Hz from an injected monotonic clock; `dt` is real elapsed time clamped to 100 ms.
- Order per tick: read sources, build Sensed, check exit gesture, check idle, `update`, `draw`,
  apply brightness cap, `push`.
- **Exit gesture**: both wrists above the nose on the most confident body for `exit_seconds`
  returns to the menu. Not active while the menu is showing.
- **Idle attract**: no bodies and no blobs for `idle_seconds` launches the `ambient` entry
  (section 8), which cycles its three modes. Any body or blob returns to the menu.
- **Crash guard**: an exception in `reset`, `update`, or `draw` logs the traceback, shows a
  one-second glitch frame, and returns to the menu. A game that raises three times in a session
  is hidden from the menu until restart. The runner itself never exits on a game error.
- `done()` true returns to the menu on the next tick.

### 7.3 Menu

- Tiles in a grid sized to the wall: 3 by 4 on 64 by 64, 6 by 2 on 128 by 32, each tile the
  game's 8 by 8 icon with a one-pixel border. Twelve slots, eleven games plus one spare that
  shows the arcade's title.
- Cursor: `raised_wrist` of the most confident body, else the largest blob, else that body's
  `center`, else no cursor. Drawn as a two-pixel cross.
- Dwell: while the cursor stays inside one tile, a ring around the tile fills over
  `dwell_seconds`; leaving the tile resets it. A full ring launches the game. Passing through a
  tile never launches.
- The hovered game's title scrolls on one text row. Games whose `needs` the current sources
  cannot provide are drawn dimmed and show "needs camera" or "needs mic" in the title row.
- Status glyph in a corner: two pixels, camera and mic, lit when available.

### 7.4 Canvas

Wraps a `(height, width, 3)` uint8 array. Methods: `clear`, `pixel`, `line`, `rect`,
`fill_rect`, `circle`, `fill_circle`, `text(x, y, s, color)` in the 5 by 7 font, `blit(sprite)`,
and `size`. All coordinates are integers in wall pixels; out-of-range drawing is clipped, never
raises. Games get the same canvas each tick, already cleared unless they ask to keep it
(light painting keeps it).

### 7.5 Scores

`scores.py` keeps `{game: {"best": float, "when": iso}}` in `data_dir/scores.json`, written
atomically on change. A game reports through `record(game, value)`, which returns whether it is
a new best.

## 8. Games

Build order. Each is one file in `arcade/games/`, tested at both layouts.

| # | Name | Reads | Behaviour |
|---|---|---|---|
| 1 | `menu` | wrist, blobs | section 7.3 |
| 2 | `paint` | blobs | each blob leaves a trail in its color; trail fades to black over 20 s; canvas kept between ticks; clears after 30 s with no blobs |
| 3 | `puppet` | bodies | up to two stick figures drawn from keypoints, scaled to the wall, one color each |
| 4 | `frogger` | body x, raised_wrist | lanes run vertically, cars move up and down, frog crosses left to right; body x sets the frog's column, a raised wrist hops one lane forward; hit by a car restarts the crossing; five crossings wins |
| 5 | `pong` | wrists or blobs | two paddles; player one is body id order or the brightest blob, player two the next; a missing second player gets a wall-bounce; first to 5 |
| 6 | `jump` | nose y | tracks the nose's peak height above its standing baseline; bar and number; best of the night |
| 7 | `holewall` | keypoints | shows one of eight target stick-figure poses, three-second countdown, scores by mean keypoint distance, three rounds |
| 8 | `life` | motion, body boxes | Conway's Life stepping at 8 Hz; motion cells and body boxes are stamped live each tick; dies out to empty and restarts from a random seed after 20 s empty |
| 9 | `ambient` | motion, wrists | three modes that cycle every 60 s: rain columns part around motion; fire intensity rises under motion; boids flee wrists. Also the attract cycle |
| 10 | `scream` | audio level | peak-hold bar with a two-second decay, number, best of the night |
| 11 | `flappy` | audio onset | one flap per onset; pipes; score; game over holds three seconds then `done` |
| 12 | `beat` | beat, bpm | shapes pulse on each beat, color cycles with tempo; falls back to pulsing on onsets when no tempo lock |

Row 9 is one registry entry, `ambient`, holding the three modes in one file each under
`arcade/games/ambient/`. Its menu tile launches rain and cycles to fire and boids every
60 seconds; the attract cycle uses the same entry. The registry therefore holds eleven playable
entries, which with the title tile fills the twelve-tile menu exactly. No paging.

## 9. Verification

- **Headless helper**: `run(game, sensed_iter, ticks, size) -> list[np.ndarray]` runs the real
  runner with an injected clock, the fake display, and a fixed rng seed.
- **Semantic assertions** per game, never golden images: the frog's column follows the actor's
  x; the paint trail exists after a blob passes and is black again within 20 s; the menu launches
  tile two after a dwell and does not launch on a pass-through; Life has live cells where a body
  stood; the exit gesture returns to the menu; a raising game hides after three crashes.
- **Both layouts**: a parametrized fixture runs every game test module at 128 by 32 and 64 by 64.
- **Generic soak**: every registered game runs 300 ticks against a random mix of actors and must
  raise nothing and produce at least one non-black frame.
- **Budget**: every game's `update` plus `draw` averages under 8 ms per tick at 64 by 64 on the
  dev machine, measured over 300 ticks, marked as a `perf` test.
- **State first, pixels second**: every game test asserts on `debug_state()` for behaviour
  and on pixels only for what state cannot express (a trail fading, a tile ring filling).
- **Contact sheets**: `tools/arcade_shot.py --game frogger --actors "walk(0.1,0.9,3);raise_hand(2,0.5)" --ticks 90 --every 10 --look led --out shots/frogger.png`
  writes a labeled grid of frames. Agents read the PNG to judge the look. Also accepts
  `--scenario file.jsonl`, `--size 128x32`, and `--look plain|led|distance`.
- **Render modes** (`arcade/look.py`), shared by the SDL preview and the contact sheets:
  `plain` is nearest-neighbour upscale; `led` draws each pixel as a round dot on black with a
  gap and a soft halo, after the configured gamma curve, so a preview looks like a P5 module
  and not a bitmap; `distance` applies the gamma, blurs and downsamples to what the wall
  resolves from about 15 feet, for legibility checks. Where gamma is really applied, on the
  card or in the DDP sender, is measured in prototype week and the config default follows it.
- **Agent REPL**: `tools/arcade_play.py --game frogger` reads verbs on stdin: `step N <actor>`
  holds an actor for N ticks, `state` prints `debug_state()`, `shot path.png` writes the
  current frame, `reset`. One verb per line, deterministic, no window. This is how an agent
  probes a game interactively rather than only through canned scenarios.
- **Live smoke** (manual): `python -m arcade --backend sdl --camera mediapipe` on the Mac, one
  minute per game. On the Pi: `--backend ddp --camera imx500`.
- **Foundation tests**: the daemon plan's tests for Tasks 1, 2, 5 and DDP run unchanged.

## 10. Failure handling

- Missing camera or microphone: logged once, empty Sensed fields, status glyph off, dependent
  games dimmed in the menu. Nothing exits.
- MediaPipe model file absent: `pose_mediapipe` reports unavailable and logs the fetch command.
- Camera thread dies: the source reports unavailable from that tick; the runner keeps going.
- Display push fails (DDP socket error): logged, retried next tick, never raised into a game.
- Brightness cap in config is the hard ceiling; a game cannot raise it.

## 11. Project skills

Written with the official `skill-creator` plugin after the foundation tasks and the first two
games exist, so they describe real commands and real files. They live in `.claude/skills/` and
are committed.

- **arcade-verify**: how to run a scenario, produce a contact sheet, use the REPL, and a
  per-game checklist of what a correct run looks like. Each check names one specific behaviour;
  the skill never asks the agent to "find bugs".
- **wall-look**: what a 64 by 32 P5 module can show. Minimum feature sizes (two-pixel lines
  for anything that must read at distance), no thin dark greys, the gamma curve, the 5 by 7
  font, colour choices that survive the brightness cap, and how to use the `distance` mode.
- **arcade-game-authoring**: the Game protocol, `debug_state` conventions, actor recipes, the
  test template, and the registry, so a new game is one file plus one test.

## 12. Open items

- The exact MediaPipe landmark to COCO index map and the IMX500 model choice (PoseNet versus
  HigherHRNet) are decided during implementation and recorded in `arcade/sources/README.md`.
- The dwell time of one second is a guess; the live smoke on the Mac tunes it.
