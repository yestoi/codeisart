# Wall Arcade Design

Date: 2026-09-26. Revision 3. Status: approved. Folds in the accepted findings of the six-lens
adversarial review (`docs/superpowers/reviews/2026-09-26-arcade-adversarial-review.md`) and the owner's
decisions recorded in its sections 10 and 10a. Revision history is in section 14.

A camera-and-microphone-driven arcade for two P5 LED panels, launched by stepping up and raising a
hand. Built on the Mac before hardware arrives, by agents that verify their own work headlessly, then
run unchanged on a Raspberry Pi 5 through the same display code the Code is Art show daemon uses.

This is a separate deliverable from the Code is Art installation
(`2026-09-22-code-is-art-design.md`). It shares the repo, the display code and the spare Colorlight
card. It has its own Pi, its own panels and no fixed deadline.

## 1. Goals

- A stranger walks up at a festival at night and is playing something within ten seconds, unprompted,
  with no words on the wall they have to read first.
- Every game runs on the Mac against the laptop webcam and microphone, and on the Pi 5 against the
  Raspberry Pi AI Camera and a USB microphone, with no game code that knows which it is on.
- Every game is verifiable without hardware: scripted inputs in, frames out, assertions on the game's
  own state first and on pixels second, feel metrics with budgets, and PNG contact sheets an agent can
  look at. Fun itself is judged by a human from evidence the tools produce.
- Two layouts. 128x32 (side by side) is the design layout, chosen for two-player play in front of a
  crowd. 64x64 (stacked) is first-class, not a fallback: the panels often sit stacked on a bar where a
  banner takes too much room. Each game declares which layouts it is designed for.
- Nothing flashes in the seizure band, nothing identifying is ever recorded, and the wall never goes
  dark because someone walked away.

### Non-goals

- Sound output. The microphone is an input only.
- Radar, time-of-flight, or button input. `Sensed` (section 5) can grow fields later without changing
  games.
- Name entry for high scores.
- Anything from the show daemon beyond the foundation modules in section 3.

## 2. Hardware, placement and layouts

- Two Wired Watts outdoor P5 modules, each 64 wide by 32 tall, on one chain of the spare Colorlight
  5A-75E. The arcade's Raspberry Pi 5 drives the card directly over its wired Ethernet port with the raw
  Colorlight protocol (show daemon plan Task 16 with its amendments). No Falcon Player in the arcade path.
  SSH is over Wi-Fi. The show daemon's Pi 4 is never touched by the arcade.
- The panels are physically fixed in one arrangement per session: side by side (128x32) or stacked
  (64x64). The arcade reads width and height from config and every game adapts to the layouts it declares.
  A single panel (64x32) must run the attract director and the mirror for bring-up; no game is designed
  for it.
- Dev machine: Mac with built-in webcam and microphone. Pi: Raspberry Pi 5 with active cooler, 5 V 5 A
  supply, the AI Camera (IMX500, pose model on the sensor), a cardioid dynamic vocal microphone on a
  gooseneck through a USB audio interface with gain locked, and the Pi 5's real-time clock with its
  battery. A warm, diffuse, DC-powered floodlight on the play area at night.
- Placement rules (also in the operations checklist, section 10):
  - The camera mounts on the wall frame above the panels, tilted down, never on a pole in the play area.
    Framing is set so a one-metre child at the mat's near edge is fully in view.
  - A flat marked play mat, about 2 by 2 m, starting 1.5 to 2 m from the wall, with a one-metre clear
    margin. No stakes, cables or guy lines cross it or the approach. Bike paths stay out of frame.
  - The floodlight sits at 2.5 m or higher, 30 to 45 degrees off the camera axis, visored so its face is
    hidden from eye height on the mat, dimmed to the lowest level at which detection holds.
  - The microphone stands at mouth height beside the mat, facing the player, away from the sound camp
    and the generator, in a windscreen.
  - On a bar (64x64), the same rules apply at bar scale: camera on the panel frame, a marked standing
    spot, the mic on the bar.

## 3. Foundation from the show daemon plan

Before any arcade code, implement these tasks from `docs/superpowers/plans/2026-09-22-show-daemon.md`
exactly as written with their amendments and tests: Task 1 (scaffold and config), Task 2 (font), Task 5
(display protocol, fake and SDL backends), Task 16 (raw Colorlight backend) and Task 15 (DDP backend,
kept so a Falcon Player path remains possible). This gives one display pipeline for both projects.

Amendments for the arcade:

- `make_display` reads the fields it needs (`width`, `height`, `backend`, `sdl_scale`, `ddp_host`,
  `ddp_port`, `iface`) off whatever config object it is given.
- `FakeDisplay` keeps only the last frame and a count.
- The Colorlight backend exposes `set_brightness(level)` by sending the card's brightness packet, and
  it is the only backend on which `brightness` is enforced at the panel. The SDL and fake backends model
  it in the preview. The DDP backend logs once at startup that brightness is Falcon Player's setting.
- On the Pi the process needs `CAP_NET_RAW` (`AmbientCapabilities=CAP_NET_RAW` in the unit), and the
  wired interface is dedicated to the card.

No other show daemon task is part of this work.

## 4. Architecture

One Python process, one fixed-tick loop at 30 Hz. Each tick the runner assembles one `Sensed` record
from the camera and audio sources, derives the player and presence fields, hands the record with the
elapsed time to the current game, renders the game's canvas plus the shared effects, passes the frame
through the flash governor and the brightness limiter, and pushes it to the display.

```
camera source ─┐
               ├─> Sensed ─> runner ─> game.update / game.draw ─> Juice ─> flash governor ─> APL limiter ─> Display.push
audio source  ─┘               │
                               ├─ lobby (attract director: mirror, invite, doors)
                               ├─ session rules (player lock, leave, inactivity, cap, deliberate exit)
                               ├─ crash guard, strict mode for tests
                               └─ injected clock and rng
```

### 4.1 Package layout

```
arcade/config.py                 ArcadeConfig, load_config(path)
arcade/sensed.py                 Sensed, Body, Keypoint, Blob, Audio dataclasses, COCO constants
arcade/calibration.py            Calibration (zone, baseline scale, static-light mask, audio floor), load/save
arcade/sources/camera.py         CameraSource protocol, make_camera(cfg), ThreadedCamera, BodyTracker
arcade/sources/pose_mediapipe.py Mac: OpenCV webcam + MediaPipe Pose Landmarker (unflipped)
arcade/sources/pose_imx500.py    Pi: picamera2 + on-sensor pose model, pluggable parser
arcade/sources/mirror.py         mirror_keypoints(): the one place x is flipped, labels never swapped
arcade/sources/blobs.py          light-source blobs and gated motion grid from a low-resolution frame
arcade/sources/audio.py          AudioSource protocol, sounddevice implementation, FFT features
arcade/sources/replay.py         ReplayCamera and ReplayAudio from a scenario file (Sensed or raw)
arcade/sources/actors.py         scripted bodies, blobs, motion and audio for tests; degrade(); festival scenes
arcade/sources/record.py         write a live session to a scenario file, with --script cues and --raw
arcade/canvas.py                 Canvas: pixel, line, rect, circle, fill, text(scale), blit, blit_rgb
arcade/look.py                   preview render modes: plain, led, distance(metres)
arcade/game.py                   Game protocol, GameInfo, icon and sprite helpers
arcade/input.py                  Edge, Hold(seconds), OneEuro filter helpers shared by games and the lobby
arcade/juice.py                  shared effects: shake, flash, burst, pop, banner, freeze, celebrate, echo
arcade/flash.py                  the flash governor
arcade/brightness.py             average-picture-level limiter and the night schedule
arcade/poses.py                  named poses in body-relative units (Copy Me targets, actors, REPL)
arcade/bots.py                   closed-loop test players: Bot protocol, per-game good and lazy bots
arcade/feel.py                   feel metrics computed from frames and debug_state traces
arcade/feel_budgets.toml         per-game-kind budgets; the loop may tighten, only a human loosens
arcade/attract/director.py       the lobby: presence tiers, mode scheduling, invite, doors, score card
arcade/attract/modes/<name>.py   one attract mode per file (section 7.7)
arcade/runner.py                 tick loop, session rules, crash guard, state()
arcade/scores.py                 best-of-the-night persistence; sessions log
arcade/main.py                   CLI: run, doctor, calibrate, record, stats
arcade/games/__init__.py         MENU_ORDER, discovery by importlib, guarded imports
arcade/games/<name>.py           one file per game (section 8)
tools/arcade_shot.py             headless run -> contact sheet, provenance header, black refusal
tools/arcade_play.py             step-verb REPL for agents, with --log
tools/arcade_evidence.py         the per-iteration evidence package (section 9.6)
tools/arcade_feel.py             prints the feel table for a game
tools/latency_probe.py           camera-to-wall latency measurement with a mirror
tools/fetch_models.py            downloads the MediaPipe model file (gitignored)
.claude/skills/                  project skills: arcade-verify, wall-look, arcade-game-authoring; vendored cv-mediapipe, game-feel
tests/arcade/                    one test module per module and per game, helpers, conftest, fixtures/real/
```

### 4.2 Dependencies

- Everywhere: numpy, pygame (SDL preview), one OpenCV distribution (`opencv-contrib-python`, because
  current mediapipe requires it; never both `opencv-python` and the contrib build), sounddevice, Pillow.
- `mac` extra: mediapipe 1.x, pinned with an upper bound recorded by the environment spike.
- Pi: picamera2, `python3-munkres` and `python3-scipy` from apt.
- Python 3.12 through uv (`uv venv --python 3.12 .venv`). The Mac's system Python is 3.14 and is not
  used. Working versions are recorded in `arcade/sources/README.md` by the environment spike and pinned.
- Tests need none of the hardware extras. Modules that import mediapipe, picamera2, `cv2.VideoCapture`
  devices or sounddevice do so inside the source class, never at package import time.

Agent tooling, vendored into `.claude/skills/vendor/` as single SKILL.md files pinned by commit sha, not
installed as whole marketplaces: `cv-mediapipe` from `damionrashford/media-os` and `game-feel` from
`gamedev-skills/awesome-gamedev-agent-skills`. Also the official `skill-creator` and `pyright-lsp`
plugins. Not `pygame-core`, `procedural-gen`, `performance-optimization` or `pixel-art-sprites`.

### 4.3 Config

`arcade.toml`, flat, keys are fields of `ArcadeConfig`, unknown keys rejected. Calibration results
(section 6.6) live in `data_dir/calibration.json`, not here.

| Field | Default | Meaning |
|---|---|---|
| `width`, `height` | 128, 32 | wall size in pixels; the layout name is `f"{width}x{height}"` |
| `backend` | `sdl` | `sdl`, `fake`, `colorlight`, `ddp` |
| `sdl_scale` | 8 | preview window scale |
| `iface` | `eth0` | wired interface for the Colorlight backend |
| `ddp_host`, `ddp_port` | `127.0.0.1`, 4048 | Falcon Player, if that path is ever used |
| `camera` | `mediapipe` | `mediapipe`, `imx500`, `replay`, `none` |
| `camera_index` | 0 | OpenCV device index on the Mac |
| `camera_fps` | 10 | requested frame rate of the pose source; raised only while the tensor-less frame count stays zero |
| `audio` | `sounddevice` | `sounddevice`, `replay`, `none` |
| `audio_device` | `""` | input device matched by name; empty means default |
| `scenario` | `""` | scenario file for the replay sources |
| `mirror` | true | flip x so the player's right is screen right, applied once in `mirror_keypoints` |
| `brightness` | 0.4 | hard ceiling sent to the card on the `colorlight` backend, modelled by previews, advisory on `ddp`; never raised by a game |
| `apl_cap_day`, `apl_cap_night` | 0.12, 0.06 | average-picture-level caps applied by the limiter; night begins at `night_start` or when lux falls below `night_lux` |
| `night_start`, `night_end` | `"01:00"`, `"06:00"` | clock fallback for the night cap |
| `night_lux` | 5.0 | IMX500 lux below which night applies, when the metadata is available |
| `gamma` | 2.2 | curve the previews and the governor model; 1.0 if the card applies gamma itself |
| `look` | `led` | preview render mode: `plain`, `led`, `distance` |
| `dwell_seconds` | 1.2 | how long a hand must hold on a door to select it |
| `present_on_seconds`, `present_off_seconds` | 1.0, 3.0 | hysteresis for `Sensed.present` |
| `player_lost_seconds` | 0.5 | how long the player slot survives without its body |
| `leave_seconds` | 8 | nobody in the zone this long ends the session |
| `inactive_seconds` | 30 | no input this long shows the still-playing prompt, which lasts 5 s before ending |
| `max_session_seconds` | 180 | session cap, applied only while another body waits in the zone |
| `exit_seconds` | 3.0 | the deliberate exit hold |
| `allow_record` | false | must be true on the `colorlight` backend before `arcade record` will run |
| `data_dir` | `./data` | scores, sessions log, calibration |

## 5. The Sensed record

The only input games see. Built once per tick by the runner from the latest source results, then
enriched with the derived fields.

```python
@dataclass(frozen=True)
class Keypoint:  x: float; y: float; conf: float        # normalized 0..1 in the camera frame, already mirrored, smoothed
@dataclass(frozen=True)
class Body:
    id: int
    box: tuple[float, float, float, float]
    keypoints: tuple[Keypoint, ...]                     # 17, COCO order
    vx: float; vy: float                                # body-anchor velocity, per second, from capture timestamps
    scale: float                                        # smoothed nose-to-mid-hip length in frame units
    in_zone: bool
    zone_x: float; zone_y: float                        # body anchor mapped into the calibrated zone, 0..1 across the mat
    seen_ago: float                                     # seconds since the tracker last saw this body (0 when fresh)
@dataclass(frozen=True)
class Blob:      x: float; y: float; size: float; color: tuple[int, int, int]; in_zone: bool
@dataclass(frozen=True)
class Audio:
    level: float          # broadband RMS with slow gain, 0..1, for ambient visuals only
    level_smooth: float   # level with 50 ms attack and 300 ms release
    peak: float
    voice_db: float       # absolute dBFS in the 300 Hz to 3.4 kHz band, no automatic gain
    floor_db: float       # rolling 30 s 90th percentile of voice_db
    voice: float          # (voice_db - floor_db) / 30, clamped 0..1
    clap: bool            # 2 to 6 kHz spectral-flux onset, crest factor above 4, 12 dB over the floor
    onset: bool           # broadband onset, kept for ambient visuals
    beat: bool; bpm: float | None
@dataclass(frozen=True)
class Sensed:
    t: float                       # seconds since runner start
    camera_t: float                # capture time of the newest camera frame, on the runner clock
    camera_fresh: bool             # true on the tick a new camera frame arrived
    camera_seq: int
    bodies: tuple[Body, ...]       # tracked, stable ids, largest scale first
    player: Body | None            # the locked player (section 7.2); replaces any notion of "primary"
    player2: Body | None           # the second in-zone body by scale, for two-player games
    present: bool                  # someone is in the zone, with hysteresis
    blobs: tuple[Blob, ...]        # light sources, brightest first, at most 8
    motion: np.ndarray             # bool, shape (height, width); empty when the grid is judged global
    audio: Audio
```

- COCO keypoint order: nose, eyes, ears, shoulders, elbows, wrists, hips, knees, ankles. Helper
  properties on `Body`: `nose`, `left_wrist`, `right_wrist`, `shoulder_mid`, `hip_mid`, `center`,
  `height`, `confidence`, `raised_wrist` (the higher wrist if above the raise line, else None),
  `both_hands_up`, `reach(kp) -> (u, v)` (a keypoint in the body-relative reach box, section 7.3).
- The raise line is 0.3 torso lengths above the shoulder midpoint; the nose is used only when both
  shoulders are missing, because goggles, masks and hoods are normal at a burn.
- Keypoints outside 0..1 or NaN are clamped with confidence 0. Keypoints are smoothed by a One Euro
  filter in the tracker; games never smooth or difference keypoints themselves.
- Mirroring happens once, in `mirror_keypoints`, after inference on both platforms, and never swaps
  left and right labels. The same raised-right-hand fixture through both parsers yields `RIGHT_WRIST`
  at x > 0.5.
- `motion` is frame differencing after a 5x5 blur and median normalisation, thresholded, downsampled to
  wall resolution over the zone crop at the wall's aspect. When more than 35 percent of cells fire the
  grid is returned empty and a shake is counted. It needs no model and works on any camera.
- `BodyTracker` anchors on the shoulder midpoint (then nose, then hips), predicts with constant
  velocity, assigns globally with a distance plus scale-difference cost, coasts a missed track for
  300 ms (emitting `seen_ago`), drops it after 0.5 s, and never reuses an id within a session.
- Audio features come from a 512-point FFT per block on a rolling 16 kHz mono buffer, with windows
  defined in seconds and updated per block, never per tick. `beat` and `bpm` come from the last eight
  onset intervals when they agree within 15 percent.

## 6. Sources

Every source runs its capture in a thread and exposes `latest()` without blocking. The runner never
waits on a sensor. A source that cannot open its device logs once, reports `available = False`, retries
every 30 s, and returns empty results meanwhile. Every result carries its capture timestamp; a result
older than 1.0 s (camera) or 0.5 s (audio) is treated as empty and the source as unavailable until a
fresh one arrives. Repeated errors are logged once per minute with a count.

### 6.1 Camera

`CameraSource.latest() -> (capture_t, bodies, blobs, motion) | None`.

- **pose_mediapipe** (Mac): OpenCV capture at 640 by 480, MediaPipe Pose Landmarker in video mode with
  `num_poses = 2`, run on the unflipped frame. The 33 landmarks map to the 17 COCO points by index. A
  denied macOS microphone or camera permission is detected (exact zeros, or no frames) and reported.
- **pose_imx500** (Pi): picamera2 with a pose model from the model zoo through a pluggable parser.
  HigherHRNet is the default; YOLO11n-pose is tried on the first Pi day (section 12). `FrameRate` is
  `camera_fps`. A frame with no output tensor returns `None` so the last result holds. The matcher is
  scipy's `linear_sum_assignment`, and each output tensor is truncated to the top 8 candidates per joint.
  Coordinates are normalised by the model input size, never by picamera2's boxes. Exposure and white
  balance are locked after a 3 s warm-up and re-converged only after 30 s without presence.
- **blobs.py** runs on a low-resolution stream (about 160 by 120): a light source is a pixel region with
  value at or above 220 whose 3 px halo is saturated (0.5 or more); hue comes from the halo; components
  over 0.5 percent of the frame are rejected; a blob still for 5 s is masked as scenery until it moves;
  only in-zone blobs are reported to games. Blob colour is sampled with `cv2.mean` over the bounding box.
- **replay**: reads a scenario file. A Sensed-level file replays records at the runner's tick. A raw
  file (section 6.3) runs the real feature extraction and tracker so they can be re-tuned.
- **none**: always empty.

### 6.2 Audio

`AudioSource.latest() -> (capture_t, Audio)`.

- **sounddevice**: the configured input device, 16 kHz mono, callback appends to a two-second ring
  buffer and stamps the time; features computed per block. Callback overflows are logged.
- **replay** and **none** as for the camera.

### 6.3 Scenario files

JSON lines, gzip-compressed (`.jsonl.gz`), with a header record. Two kinds:

- **Sensed recordings**: one Sensed record per tick at 30 Hz, `motion` stored as a packed bit string on
  a fixed 128 by 64 grid and resampled on replay. Produced by `arcade record` or by actors.
- **Raw recordings** (`arcade record --raw`): one record per camera frame with the capture time, raw
  detections, a 160 by 120 frame, plus a 16 kHz WAV. About 10 MB per minute. Used to re-tune the
  tracker, blobs, motion and audio features. Raw recordings are made only by the owner, under the
  privacy rules of section 6.5.

`arcade record --script NAME` shows timed cues in the preview window ("RAISE RIGHT HAND", "HOLD",
"SWEEP LEFT") and writes the cue times into the header, so the script is the ground truth for cue
assertions. The fixture scripts are listed in section 9.5.

### 6.4 Actors

Generators in `actors.py` that yield Sensed records for a given tick count, composed with
`scene(persons=, blobs=, motion=, audio=, ticks=)`. `Person(x, y, height, id)` with chained scripts
`walk`, `raise_hand`, `both_hands_up`, `jump`, `wrist(hand, y_from, y_to, seconds, at)` for continuous
hand height, and `pose(name, at, seconds)` from `arcade/poses.py`. `moving_blob(...)`,
`motion_rect(x0, y0, x1, y1, start, seconds)`, `silence()`, `claps(times)`, `tempo(bpm, start)`,
`loud(level)`, `level_ramp([(t, level), ...])`. Events fire on exactly one tick, the first at or after
the event time. Festival scenes: `crowd(n)` behind the player, `headlamps`, `camp_kick(bpm)`, `wind`,
`shake`. `degrade(scene, fps=10, latency=0.15, keypoint_dropout=0.15, jitter=0.01)` turns perfect
30 fps keypoints into what the Pi produces; game tests run their canonical scenarios under `degrade`
with `REAL_NOISE` constants fitted from the real fixtures. Deterministic: no randomness, no wall clock.

### 6.5 Privacy

- No camera frame or audio sample leaves its source thread. Nothing is written, logged or sent except
  Sensed records, scores, the sessions log and the status file. A test fails if `arcade/` references
  `imwrite`, `imencode`, `np.save`, `Image.save`, `VideoWriter` or `wave`, and another asserts a
  scenario line holds no field outside the Sensed schema.
- No preview or stream server is ever started on the Pi.
- `arcade record` requires `--i-have-consent`, and on the `colorlight` backend `allow_record = true`.
  The wall shows 3, 2, 1, then a red REC glyph and a seconds counter for the whole recording. Event
  recordings drop `motion` unless `--with-motion`. `--raw` is refused on the `colorlight` backend.
- Signs at the approach and at the camera: "This camera sees you as 17 dots. Nothing is recorded or
  saved. Stand outside the square and it ignores you. Flashing lights." The camera is declared on the
  placement form. The mirror in the attract is the strongest disclosure: each visitor sees exactly what
  the camera sees of them.

### 6.6 Calibration

`arcade calibrate` runs once per setup and writes `data_dir/calibration.json`, read at startup:

1. The wall shows the camera's view while the operator aims the camera.
2. The operator stands at the mat's two far corners and its near edge; this sets the zone rectangle in
   camera space and the minimum body height that counts as in-zone.
3. The operator stands still on the mat; this sets the baseline scale.
4. The operator clears the frame for 10 s; this captures the static-light mask and the audio floor.
5. Exposure and white balance are locked.

Keypoints stay in the camera frame; `Body.zone_x` and `zone_y` map the body anchor into the zone
(0..1 across the mat), and games that steer by position read those, so body x maps to the playfield the
same way at 2 m and 4 m. `Body.reach` (section 7.3) is already body-relative. Without a calibration file the zone is the central 60 percent
of the frame and the minimum height 0.45; the status glyph shows "uncalibrated".

## 7. Runner, game interface, lobby, canvas

### 7.1 Game

```python
@dataclass(frozen=True)
class GameInfo:
    name: str                       # registry key, file name
    title: str                      # one word or two, shown at 2x on a door
    verb: str                       # the one action, shown on the opening pictogram: "COPY", "DODGE", "FLAP"
    icon: np.ndarray                # 16x16 bool, 2 px strokes
    needs: frozenset[str]           # subset of {"pose", "blobs", "motion", "audio"}
    layouts: frozenset[str] = frozenset({"128x32", "64x64"})   # layouts this game is designed for
    players: int = 1                # 1 or 2
    exit_gesture: bool = True       # False for games whose play involves both hands up
    kind: str = "control"           # "control", "toy" or "score", selects the feel budget set
    abandon_seconds: float | None = None   # overrides leave_seconds; None uses config; paint sets a longer one

class Game(Protocol):
    info: GameInfo
    scores: Scores                  # set by the runner before reset()
    SCENARIOS: dict[str, Callable]  # named actor or bot scripts: canonical, idle_body, nobody, fail, win at least
    CAPTION_KEYS: tuple[str, ...]   # debug_state keys printed under each contact sheet cell
    def reset(self, size: tuple[int, int], rng: random.Random, fx: Juice) -> None: ...
    def update(self, sensed: Sensed, dt: float) -> None: ...
    def draw(self, canvas: Canvas) -> None: ...   # must work immediately after reset()
    def done(self) -> bool: ...
    def debug_state(self) -> dict: ...
```

`debug_state` returns a small flat dictionary of the game's own truth. Conventions: a `phase` key
(`intro`, `play`, `over`, `card`), a `score` key when the game has one, an `active` boolean that is true
on any tick the game received meaningful input, and keys ending in `_xy` holding wall pixel coordinates
of a visible entity, which a generic test checks are lit. Keys are stable per game and listed in the
game's docstring. Games must not use the runner's keys (`game`, `t`, `idle`, `attract`, `hidden`,
`crashes`, `glitch`, `fx_*`, `flash_held_ticks`).

A fresh instance per launch. Games hold no state across plays except through `scores`. Games never
touch the display, the config or the frame array directly. Coordinates may be floats; the canvas
rounds and clips.

### 7.2 Runner and session rules

Two states: LOBBY (the attract director, section 7.7) and GAME.

- Tick at 30 Hz from an injected monotonic clock; `dt` is real elapsed time clamped to 100 ms.
- Order per tick: read sources, build Sensed, derive `player`, `player2` and `present`, apply session
  rules, `update`, `draw`, render effects, flash governor, brightness limiter, `push`.
- **Player lock.** `player` is the in-zone body with the largest scale. Once set it stays until its body
  has been absent for `player_lost_seconds`, or another in-zone body has been 1.3 times larger for one
  second. A body re-acquired by nearest position within that window keeps the slot. `player2` is the
  next in-zone body by scale. Games read `player` and `player2`, never `bodies[0]`.
- **Presence.** `present` turns true after an in-zone body, or a moving in-zone blob, has lasted
  `present_on_seconds`, and false after `present_off_seconds` without one. Out-of-zone bodies and blobs
  never count. Idle and attract read only `present`.
- **Leaving.** In a game, no presence for `leave_seconds` (or the game's `abandon_seconds`) ends the
  session: a 3 s score card, then the lobby. This is the normal way a session ends.
- **Inactivity.** `inactive_seconds` without `active` shows "STILL PLAYING? HAND UP" for 5 s, then ends
  the session.
- **Session cap.** With another body waiting in the zone, `max_session_seconds` ends the session after
  the current round with an end card that says "NEXT: RAISE A HAND".
- **Deliberate exit.** Both hands held above the raise line for `exit_seconds` with a runner-drawn
  closing ring, only when the game's `exit_gesture` is true. After any exit the lobby ignores bodies
  until both hands are down, so the same hands cannot select a door.
- **Crash guard.** An exception in `__init__`, `reset`, `update`, `draw` or `done` logs the traceback,
  keeps it as `last_error`, shows a static dim red icon that fades over 0.5 s, and returns to the lobby.
  A game that raises three times in a session is hidden until the dusk restart. The lobby itself is
  never hidden; if it raises, a built-in title card runs until restart. In `strict` mode (the test
  harness default) the exception is re-raised instead.
- `done()` true shows the game's card, then the lobby.
- `state()` merges the game's `debug_state` under the runner's keys (runner keys win) and adds `player`
  id, `present`, `crashes`, `glitch`, `flash_held_ticks`, and the effects' `fx_*` keys.

### 7.3 Walk-up flow, cursor and doors

The ten-second path, replacing the twelve-tile grid of revision 2.

1. **Attract, nobody near.** A mode from the catalog runs (section 7.7). Every 20 s the director may
   show a 5 s demo replayed from a recorded scenario, or tonight's best with the holder's frozen figure.
2. **Someone steps onto the mat.** Their mirror figure appears over the running mode within half a
   second, in their colour with 2 px strokes. This is the moment that stops people.
3. **After 1.5 s near**, a 16 px hand-up pictogram breathes at 1 Hz beside the figure. No words.
4. **A raised hand starts play at once.** The featured game opens with a 2 s pictogram of its one action
   and its verb at 2x, then plays. The featured game rotates every 15 minutes among games that need no
   teaching and fit the layout and the available sources.
5. **The doors are opt-in.** From any end card, holding the hand up shows three doors. On 128x32 they
   are three 42 by 32 panels side by side, each a 16 by 16 icon over the title at 2x, and the player
   selects by standing under one. On 64x64 they are three 21 px columns with the icon, and the hovered
   door's title scrolls at 2x in the bottom 14 rows; the player selects by standing under a column.
   A door fills over `dwell_seconds` while the hand stays up; leaving the door decays the fill over
   0.3 s rather than resetting it. Unselected doors rotate every 5 s through the rest of the list.
6. **The ten-second guarantee.** A player who is near for 5 s and does nothing gets the featured game
   after a 3, 2, 1.
7. **End.** A game's card shows the score, "BEST!" on a record, "HAND UP = AGAIN" and, when someone
   waits, "NEXT: RAISE A HAND". A hand replays, a hold opens the doors, and walking away returns to
   attract.

**Cursor.** Wherever a hand position is needed, it is the wrist in the body-relative reach box: the
wrist further from its hip, relative to the shoulder midpoint, normalised by shoulder width, with a box
1.5 shoulder widths each side and from hip height to a forearm above the head mapping to the whole
wall. This works at any distance, seated, and for children. Raw frame coordinates are never used for a
cursor. Blobs never steer selection while a body is present. Body centre never selects anything.

**Status.** Two pixels in a corner for camera and microphone availability, and an "uncalibrated" mark.
Games whose `needs` the current sources cannot provide, or whose `layouts` exclude the current layout,
are never offered.

### 7.4 Canvas

Wraps a `(height, width, 3)` uint8 array. Methods: `clear`, `pixel`, `line`, `rect`, `fill_rect`,
`circle`, `fill_circle`, `text(x, y, s, color, scale=1)` in the 5 by 7 font (scores use `scale=2`,
10 by 14 with 2 px strokes, which reads to about 10 m), `blit(mask, x, y, color)`,
`blit_rgb(sprite, x, y)` with black transparent, `sprite_from_rows(rows, palette)`, and `size`.
Coordinates may be int or float and are rounded; NaN and infinity land far off-canvas and clip;
colours are clamped to 0..255; a line whose endpoints exceed four times the canvas extent is skipped.
Out-of-range drawing is clipped, never raises, never hangs. Games get the same canvas each tick,
already cleared; a game that keeps its own buffer (paint) blits it.

### 7.5 Scores and the sessions log

`scores.py` keeps `{game: {layout: {"best": float, "when": iso}}}` in `data_dir/scores.json`, written
with fsync then rename. `Scores(None)` keeps scores in memory for tests and tools. A game reports
through `self.scores.record(value)`, which returns whether it is a new best; a new best on Strongman's
roar needs at least 10 dB more. Bests roll over at 16:00 local time; the previous night's best is kept
for the attract's "LAST NIGHT" card.

Every session appends one JSON line to `data_dir/sessions.jsonl`: game, layout, start time, duration,
players, score, end reason (`done`, `left`, `inactive`, `capped`, `exit`, `crash`). `arcade stats`
summarises it. This is how the owner learns which games worked after night one.

### 7.6 Flash governor and brightness limiter

Runner-level, after effects, not bypassable by any game or mode.

- **Flash governor** (`arcade/flash.py`): per pixel, linearise through `gamma`, take Rec. 709 luminance
  with saturated red (R over R+G+B at or above 0.8) counted double, track the last extreme and
  direction with a 30-frame ring of transitions, and hold a reversal of 0.1 or more when the pixel has
  already transitioned six times in the last second. This bounds every pixel to 3 flashes per second.
  Interventions are counted in `state()` as `flash_held_ticks` and logged once per minute with the game
  name. Measured cost 0.2 ms on the Mac.
- **Brightness limiter** (`arcade/brightness.py`): computes the frame's average picture level after
  gamma and, when it exceeds the active cap (`apl_cap_day` or `apl_cap_night`), scales the frame through
  a lookup table, never below a factor of 0.5. Night is decided by IMX500 lux metadata when available,
  else by the clock (the Pi 5 has a real-time clock). Modes and games also receive `energy` (0..1) from
  the director and are expected to light fewer pixels late at night rather than rely on the limiter.
- **Rules for games and modes:** no full-field luminance flash faster than 3 per second; game-over is a
  hold and one slow fade, never a red strobe; `beat`-driven visuals change hue or shape on onsets and
  pulse luminance only on a locked tempo at or below 180 bpm; Life steps at 5 Hz or slower with two-tick
  cell fades. Every soak runs with `claps` at 12 Hz, `tempo(180)` and an alternating motion grid, and a
  game's raw output may flash at most 10 percent of the wall.

### 7.7 Attract director

`arcade/attract/director.py` is the lobby. It owns the mirror, the invite, the doors, the cards, and
the attract modes.

- **Presence tiers** with hysteresis: EMPTY (nothing for 3 s), PASSING (motion on 2 percent of cells,
  or an out-of-zone body, or a qualifying blob), NEAR (an in-zone body stable 0.5 s, or a moving in-zone
  blob for 1 s), ENGAGED (a raised wrist on the NEAR body for 0.4 s).
- **Sub-states:** ATTRACT at EMPTY and PASSING, with the mode's `attend(focus)` called at PASSING so a
  passer-by sees the wall react; INVITE at NEAR (mirror plus pictogram); PLAY at ENGAGED (featured game
  or doors); CARD after a game. After 15 s at PASSING or below, anything overlaid fades out over 1 s.
- **Mode scheduling.** Each mode declares `needs`, `calm` (0..1), `layouts`, and a duration range
  (default 40 to 150 s). The next mode is a weighted random choice: zero weight if its needs are
  unavailable or the layout is not declared; 0.2x if among the last three; scaled by closeness to the
  night calm curve; 2x for audio modes while a tempo is locked and for reactive modes after recent
  passers-by. Duration extends while PASSING interaction continues and ends early on `settled()`.
- **Transitions** are a 1.5 s linear-light crossfade with both modes running, or a noise dissolve over a
  frozen snapshot. Never a cut. The mirror and doors fade in over the running mode, which drops to
  30 percent energy.
- **Catalog**, one file each under `arcade/attract/modes/`, each implementing `attend(focus)` and
  reporting `lit_fraction`, `apl` and `focus` in `debug_state`, tested at both layouts for state first,
  then flicker at most 0.10 and picture level under the cap. Ship order: Watcher, Echo, Rain, Embers,
  Fireflies, Ripple pond, Heartline, Warp, Contours, Aurora, Life drift, Snowfall on you, then Beat
  (the music look from revision 2's `beat` game). Descriptions and measured costs are in the review,
  section 5. At least four ship with the core plan: Watcher, Echo, Warp and Contours, which between
  them cover bodies, motion and no input at all.
- With the camera down the director favours audio and no-input modes and shows a "camera resting"
  icon; with both down, a slow dim mode. Attract must never depend on a sensor.
- `debug_state`: `tier`, `sub`, `mode`, `mode_t`, `next_mode`, `energy`, `fade`, `focus`,
  `featured`, `door`, `dwell`.

## 8. Games

Ten games plus the lobby. Each is one file in `arcade/games/`, tested on every layout it declares with
full feel budgets, and required to run and stay legible on the other. Ship order is the table order.
Effort is the fun lens's estimate.

| # | Name | Title | Layouts | Players | Reads | Behaviour | Effort |
|---|---|---|---|---|---|---|---|
| 1 | `copyme` | COPY ME | both | 1 on 64x64, 1 or 2 on 128x32 | keypoints | The hero. The player's live figure in their colour; a target pose as a cyan outline that grows toward them over 3 s; each limb turns green when its angle is within tolerance; at zero, flash, score pop, and the round's best frame frozen 1.5 s. Scoring translates to the hip centre, scales by torso length, compares limb angles weighted by confidence, upper body only when legs are cropped. A pose ladder from easy to silly so round one succeeds. Pose relay: the round winner strikes a pose that is saved to `data_dir` as a future target. Three rounds. `exit_gesture = False`. | M |
| 2 | `pong` | PONG | 128x32 | 1 or 2 | hand height | Paddles follow hand height in the reach box; sides by body x; a solo player gets a beatable CPU paddle; a second body stepping in joins live; the ball starts slow and speeds up; first to 5. | S |
| 3 | `paint` | PAINT | both | any | blobs, wrist | Each in-zone light source leaves a trail in its halo colour, drawn as segments between tracked positions; a raised wrist paints when nobody has a light; trails fade over 20 s; `abandon_seconds = 45`; ends with a 5 s gallery freeze. | S |
| 4 | `quickdraw` | DRAW! | 128x32 | 2 (solo chases the night's fastest) | raised hand per player | Both keep hands low; "WAIT" for 2 to 6 s, then "DRAW!"; first hand up wins; an early hand loses; best of five at about 10 s a round. | S |
| 5 | `dodge` | DODGE | both | 1 | shoulder height vs baseline, body x | The dinosaur game with your body: jump low obstacles, duck high ones; hitboxes forgive 2 px; speed ramps; a run ends on the first hit or at 90 s. | M |
| 6 | `tug` | TUG | 128x32 | crowd | motion grid halves | Whichever half of the camera view moves more pulls the knot toward its side; needs no pose, so it survives costumes, darkness and ten people; the spectators are the players. | S |
| 7 | `flap` | FLAP | both | 1 | wrist vertical velocity | Both wrists sweeping from above to below the shoulders within 0.4 s is one flap; wide gaps, gentle gravity; restart by flapping again; a death holds and fades, never flashes. | S |
| 8 | `swat` | SWAT | both | 1 or 2 | wrist paths | Bright 5 px fruit arc in; a hand's path between two ticks cuts them; bombs are red; 60 s rounds; two players cooperate. The showcase for the effects toolkit. | M |
| 9 | `strongman` | STRONGMAN | both | 1 | nose rise over scale; `voice` | A high striker in two phases: a jump measured as nose rise over body scale in metres, then "3, 2, 1, ROAR" scored in dB over the floor with the bell and overshoot; a bar first, the number second at 2x. Best of the night for each. `exit_gesture = False`. | S |
| 10 | `freeze` | FREEZE | both | 1 to many | keypoint speed by body, or motion by region | Freeze dance to whatever music is around; on red, anyone moving after a 0.5 s grace is out and their figure topples; last one standing. | S to M |

Removed from revision 2: `frogger`, `life`, `beat`, `jump`, `scream`, `flappy`, `holewall`, `puppet`
and the `ambient` tile. Life and Beat live on as attract modes, the puppet as the lobby's mirror, jump
and scream inside Strongman, flappy as Flap, holewall as Copy Me.

Every game ends in 45 to 90 s or on a clear result and shows its card (section 7.3). Every game
randomises its content (poses, obstacles, spawns) from the injected rng so second plays differ and tests
stay deterministic. Every game has a `good` and a `lazy` bot (section 9.3). No game a stranger meets
first depends on the microphone.

### 8.1 Effects toolkit

`arcade/juice.py`, one instance per launch, runner-owned, seeded, passed to `reset`. `shake(px,
seconds)` as an integer frame offset that decays; `flash(color, seconds)` additive and rate-limited;
`burst(x, y, color, n)` from a particle pool capped at 96; `pop(text, x, y, color)` rising 6 px over
0.8 s; `banner(text, seconds)` for "3", "2", "1", "GO!", "BEST!"; `freeze(seconds)` hit-stop that skips
update and keeps drawing; `celebrate(color)`; `echo(player, kind)` drawing a glyph over the player's
marker on the tick a gesture is recognised, so acknowledgement adds no latency on top of the camera's.
The runner renders effects after `draw`, applies shake as a slice copy, then the governor and limiter.
A 2 px marker in the player's colour stays on the bottom row under them in every game. `fx_*` keys
merge into `runner.state()` so tests assert on them. Budget under 0.5 ms at 64x64 with a full pool.

## 9. Verification

### 9.1 Harness and determinism

- `run(game, sensed_iter, ticks, size, strict=True) -> (frames, game, runner)` runs the real runner
  with an injected clock, the fake display, a fixed rng and `Scores(None)`, returning the launched
  instance even after `done()` or a crash. `strict` re-raises game exceptions.
- Every game test module is parametrized over the layouts the game declares; a collection hook fails
  unless each declared layout has at least three items. The other layout gets the run-and-legible tests.
- Seeds come from `zlib.crc32` over a fixed list of five per game and are printed on failure; never
  from `hash()` of a string.
- Debug keys are the game's claim; the `_xy` test and the counterfactual test (9.2) are the check.

### 9.2 Generic tests for every registered game

- **Soak**: 300 ticks against a random mix that always supplies every input the game's `needs`
  declares, at every declared layout plus 96x48, under `degrade`, with a `hostile_mix` (five bodies,
  eight blobs, keypoints at 0 and 1, confidence-0 limbs, flickering presence, short both-hands-up),
  raising nothing and producing at least one non-black frame, reaching every declared `phase`.
- **Counterfactual input**: for each input event in `SCENARIOS["canonical"]`, run with and without it
  under the same seed; the frames must diverge by at least `RESPONSE_PX` within `LATENCY_TICKS`. A game
  that ignores its input cannot pass.
- **`_xy` lit**: on every tick of every scenario, the pixel at each `_xy` key is lit.
- **Flash**: raw output flashes at most 10 percent of the wall under the strobe inputs of section 7.6.
- **Budget**: the whole `runner.tick` averages under `ARCADE_TICK_BUDGET_MS` (default 2.0 on the Mac)
  with p95 under twice that, over 300 ticks; on the Pi 5 the same test runs with 20 ms in prototype week
  and the numbers are committed to `docs/superpowers/workflow/evidence/pi-perf.md`.
- **Namespacing**: no `debug_state` key collides with a runner key.

### 9.3 Feel metrics and bots

`arcade/feel.py` computes, per game and layout, from the scenarios: response latency and magnitude
(from the counterfactual runs), control fidelity (Pearson r between the actor's x and the controlled
`_xy`), reachable range, liveliness, lit fraction, dim-pixel fraction, flashes per second, distinct
states and phases reached, score visibility (template-matching the project's own font against
`debug_state()["score"]`) and legibility after the `distance` blur, fail-versus-win transient
difference, hint appearance in `idle_body`, round length with the `good` bot, and difficulty as win
rate over 20 seeds for `good`, `lazy` and no input. Budgets live in `arcade/feel_budgets.toml` per
`kind`; a game may override a budget only with a comment. `pytest -m feel` asserts them and
`tools/arcade_feel.py` prints the table.

`arcade/bots.py`: a `Bot` is a closed-loop policy `(debug_state, t) -> actor spec` with
`reaction_ticks` and position noise. Every game ships `good` and `lazy`. Difficulty tuning within the
win-rate bands is the loop's; loosening a band is the owner's.

What stays human: whether a stranger gets it in ten seconds, whether the motion feels good or
embarrassing, total latency with the real camera, colour taste, night glare. The metrics find dull and
broken games cheaply; they cannot find the good ones.

### 9.4 Tools

- **Contact sheets**: `tools/arcade_shot.py --game copyme --scenario canonical --size 128x32 --look led
  --out shots/copyme.png` (also `--person`, `--blob`, `--audio`, `--scenario file`). Every sheet carries
  a header with git sha, dirty flag, game, size, look, seed and scenario, and a caption per cell from
  `CAPTION_KEYS` with the tick and time. The tool refuses an all-black run without `--allow-black`,
  prints frames, non-black count and the final `runner.state()`, caps sheets at 1,536 px wide, and
  `--flash-report` prints the worst flicker area and mean picture level. Two sheets per scenario,
  `plain` for content and `led` for look.
- **Render modes** (`arcade/look.py`): `plain` is nearest-neighbour; `led` draws round dots on black
  with a gap and halo after gamma; `distance` takes metres and models a 1.5 arcmin blur plus a
  luminance-weighted halation Gaussian, for legibility checks at 5 m.
- **REPL**: `tools/arcade_play.py --game pong --log probe.jsonl` reads verbs on stdin: `step N
  x=0.3,0.7 hand=right pose=NAME motion=... beat=120`, `state`, `shot path.png`, `reset`, `log` (last
  traceback). Verbs are validated (an unknown `hand=` is an error, never silence), each `step` echoes
  the parsed input, `shot` refuses a frame from before the last launch, and beats fire for the whole
  step. `tools/repl_to_test.py` turns a log into a pytest case.
- **Doctor**: `python -m arcade doctor --require camera,mic,pose` exits non-zero if a required source
  is unavailable after five seconds. The loop and the pre-flight run it.
- **Latency probe**: the wall flashes a square that a mirror shows the camera; the tool counts pushes
  until the blob appears.
- **Live smoke** (owner): `python -m arcade --backend sdl --camera mediapipe` on the Mac, one minute per
  game per layout, recorded in `docs/superpowers/workflow/live-smoke.md`. On the Pi:
  `--backend colorlight --camera imx500`.

### 9.5 Real-input fixtures

Recorded once by the owner with `arcade record --script NAME` (about five minutes on the Mac, five of
them again on the Pi camera and mic), stored in `tests/arcade/fixtures/real/` as `.jsonl.gz`:
`empty-room` (30 s, room lamp toggled at 15 s), `walk-in-stand-leave` (20 s), `door-point` (30 s, three
doors held 2 s each, then a sweep through without stopping), `wrist-sweep` (20 s, slow, fast, leaning),
`exit-gesture` (15 s, one 3 s hold, three false starts), `jumps-squats` (20 s), `poses-8` (40 s),
`torch-paint` (30 s, phone torch, dark room), `idle-still` (20 s), `claps-tempo-voice` (30 s),
`music-speaker` (30 s, dance track near 125 bpm), and optionally `two-people-cross` (30 s). Each yields
cue assertions (three selections in `door-point`, none in its sweep; one exit on the hold), a replay
through each consuming game with looser bands, and the fitted `REAL_NOISE` constants. A backyard-night
raw recording before the event (floodlight, techno 30 m off, three people, a glow stick, a headlamp) is
committed as the tracker's regression fixture.

### 9.6 Evidence package

`python tools/arcade_evidence.py --iteration N --games changed` writes
`docs/superpowers/workflow/evidence/itNN/`: `README.md` whose first line is the decision with a default
and a deadline, then the feel table for changed games, the reviewer's verdict, test and skip counts
against the last iteration, and every image inline; per changed game `<game>-<layout>-led.png`,
`-plain.png`, `-distance.png`, `-canonical.gif` (at most 6 s, 300 KB), `-trace.jsonl` and a ten-line
phase timeline; `feel.json`; `review.md`. Only changed games are regenerated. The package is what the
owner judges on a phone; the operator design (`2026-09-26-arcade-operator-design.md`) says how.

### 9.7 Rules for the autonomous loop

Game test modules are written into the plan in full and copied verbatim; any difference is a deviation
the reviewer must see. The reviewer lists every removed or changed `assert` under `tests/` and blocks
unless the commit justifies it. The journal records collected and skipped test counts each iteration;
a drop or a rise is a gate. Feel budgets and plan-literal tests are loosened only by the owner.
`MENU_ORDER` in `arcade/games/__init__.py` lists every game name from section 8 from the start;
discovery uses `importlib`, skips modules that do not exist yet, and guards each import so one broken
game cannot take down the arcade. Adding a game never edits the registry.

## 10. Failure handling and operations

- Missing camera or microphone: logged once, empty Sensed fields, status glyph off, dependent games not
  offered, attract falls back to modes that need nothing. Nothing exits. Unavailable sources retry every
  30 s; after five minutes of camera failure the process exits non-zero for a clean restart.
- A stale source (no fresh result within its timeout) is unavailable from that tick, so a hung camera
  cannot hold a hand on a door or freeze a game.
- MediaPipe model file absent: `pose_mediapipe` reports unavailable and logs the fetch command.
- Display push fails: logged once per minute, retried next tick, never raised into a game. After 10 s
  of failures the process keeps ticking and the status file says so.
- The flash governor and brightness limiter are the hard ceilings; no game or mode can bypass them.
- **Service.** A systemd unit with `Restart=always`, `StartLimitIntervalSec=0`, `WatchdogSec=10`
  (pinged only while ticks advance and a push succeeded in the last 5 s), `AmbientCapabilities=CAP_NET_RAW`,
  `ProtectSystem=strict` with `ReadWritePaths=` for `data_dir`. A dusk restart timer clears hidden games
  and starts the night's scores. Read-only root overlay, journald `Storage=volatile`, `data_dir` on its
  own writable partition. A labelled weatherproof button on GPIO3 with `dtoverlay=gpio-shutdown`, and a
  laminated card in the lid: "Dark wall: check power; press the button, wait for dark, press again, wait
  90 s; still dark, find Trey at camp."
- **Thermal.** SoC temperature and `vcgencmd get_throttled` every 10 s; above 75 °C the tick drops to
  15 fps; above 82 °C a static dim frame; undervoltage is logged because on generator power it predicts
  SD corruption.
- **Status.** `/run/arcade/status.json` every 10 s: game, layout, fps, temperature, throttling, sources,
  calibration state, crashes, hidden games, governor and limiter counts, detections per minute, mean
  keypoint confidence, last session. Served read-only on the site LAN or a Pi access point with a
  password-protected restart button, so the owner can check from camp on a phone. A 1 Hz heartbeat pixel
  in the status corner shows a volunteer it is alive.
- **Morning checklist.** Read status for crashes, hidden games, throttling and governor counts; wipe the
  camera window; check the housing for dew; sweep the mat; check floodlight aim, cables and signs;
  walk-up test (enter, hand up, play, walk away, attract returns); cover the wall and box for the day.
  Run dusk to dawn only. Camera behind a downward-angled acrylic window under a hood with silica gel.

## 11. Project skills

Written with the official `skill-creator` plugin right after the core plan's last task and before the
first second-plan game, so they describe real commands and real files, and so the feel rules exist as
tests before any game relies on prose. They live in `.claude/skills/` and are committed.

- **arcade-verify**: how to run a scenario, produce a contact sheet, read `feel.json`, use the REPL and
  the doctor, and a per-game checklist of what a correct run looks like. Each check names one specific
  behaviour; the skill never asks the agent to "find bugs".
- **wall-look**: what a P5 module shows at 2 to 10 m. Two-pixel strokes for anything that must read at
  distance, text at 2x for scores, no dark greys (nothing under about 140 in a channel after the cap),
  the gamma curve, one colour per game, how to use `distance` at 5 m, and the flash rules.
- **arcade-game-authoring**: the Game protocol, `GameInfo` fields, `debug_state` conventions (`phase`,
  `score`, `active`, `_xy`), `SCENARIOS` and `CAPTION_KEYS`, bots, actor recipes, the effects toolkit,
  the feel budget kinds, the test template, the "card then done()" recipe, and `MENU_ORDER`, so a new
  game is one file plus one test module. Feel guidance: no sound, so every event needs a visible
  response within two ticks and at least 12 lit pixels; camera latency is already 100 to 200 ms, so use
  hysteresis and never smoothing that costs a tick; map the middle half of the reach box to the full
  playfield; hint within three seconds of a still body; rounds of 20 to 120 s; failure and success differ
  in hue and motion.

## 12. Open items

Decided during implementation and recorded in `arcade/sources/README.md` or the workflow journal:

- The IMX500 model: HigherHRNet from the model zoo versus a YOLO11n-pose export, tried on the first Pi
  day with the parser kept pluggable.
- Dwell, presence, player-lock and leave timings above are starting values; the real fixtures tune them
  and the owner confirms once live.
- Where gamma is applied (card or software) and the night brightness cap, measured with a lux meter at
  2 m in prototype week.
- The raw Colorlight constants, diffed against chubby75 and Falcon Player before the first panel test.
- Pi 5 tick times, committed to `evidence/pi-perf.md`.

## 13. Descoping ladder

If the loop falls behind or the Pi is late, in this order:

1. Ship 128x32 fully; 64x64 games beyond Copy Me, Paint and Dodge wait.
2. Drop Freeze and Swat.
3. Drop the microphone from games; keep it for attract only (Strongman becomes jump only).
4. Ship four attract modes, not thirteen.
5. Drop the doors; the featured game rotates and a hand starts it.

Minimum viable arcade: the attract director with four modes and the mirror, the walk-up flow, the flash
governor and limiter, Copy Me and Pong, the sessions log, the systemd unit and the status file.

## 14. Revision history

- Revision 1 (2026-09-26): approved in conversation; eleven games and a twelve-tile menu.
- Revision 2 (2026-09-26): `debug_state`, LED-look previews, the agent REPL, project skills.
- Revision 3 (2026-09-26): six-lens review folded in. New: layouts as a first-class property, the
  arcade's own Pi 5 with the raw Colorlight backend, player lock and presence, session rules, the
  walk-up flow with doors, flash governor and brightness limiter, timestamps and velocity in Sensed,
  near-field audio features, light-source blobs and gated motion, calibration, privacy rules, the
  attract director and catalog, the effects toolkit, feel metrics and bots, the counterfactual test,
  evidence packages, operations. The game list changed as section 8 records.
