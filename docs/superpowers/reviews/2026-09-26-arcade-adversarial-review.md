# Adversarial review of the wall arcade spec and plan, 2026-09-26

Six independent reviewers attacked the arcade spec (`docs/superpowers/specs/2026-09-26-wall-arcade-design.md`)
and the core plan (`docs/superpowers/plans/2026-09-26-wall-arcade-core.md`) from six angles: game design
and fun, attract mode and ambient visuals, sensing reality, autonomous agent verification, plan
executability, and festival operations and safety. The attract and sensing reviewers benchmarked their
claims with numpy prototypes on the Mac; the verification reviewer checked the toolchain on this machine
and fetched every external skill; the plan reviewer extracted and ran the plan's code. Nothing below has
been applied. Spec-level decisions are the owner's; section 10 lists them.

The full per-lens reports, the attract and flash prototypes, and the plan reviewer's probe tests are in
`docs/superpowers/reviews/2026-09-26-arcade-review-lenses/` (`01-fun.md` through `06-ops.md`,
`bench_attract.py`, `flashguard2.py`, `modeflash.py`, `plan-probe-tests.py`).

## 1. Where the reviewers converged

Findings reached independently by three or more lenses. These carry the most weight.

1. **The play loop has no concept of a player, a session, or presence.** Control goes to "the most
   confident body" each tick, so it hops between strangers and spectators. Idle attract is checked only
   while the menu is showing, so six games that never call `done()` run all night after the player walks
   away. Presence is "any body or any blob anywhere in frame", and at a night burn a headlamp, art car or
   floodlit shirt is always in frame, so attract almost never starts, and the first passer-by exits it.
   The body-centre cursor fallback dwells on whatever tile sits under a person standing still and
   launches it after one second. (fun B1 to B3, ops B1 to B2, attract 1 to 2, sensing B3)
2. **The exit gesture is the victory pose.** Both wrists above the nose for 1.5 s is what people do when
   they win, jump, cheer, or copy holewall's own targets. (fun B4, ops S1, sensing B1)
3. **The walk-up flow cannot meet the ten-second goal.** Eleven 8x8 icons are 4 cm wide at 4 m; nothing
   says "raise a hand"; and because `raised_wrist` exists only above the nose and the cursor maps raw
   frame coordinates, a raised hand can only reach the top third of the wall. Half the menu is
   unreachable except by the accidental fallback. Three reviewers proposed nearly the same replacement:
   mirror first, one wordless hand-up prompt, play at once, menu opt-in. (fun B6, ops B4, attract director)
4. **Nothing limits flashing, and three specified behaviours strobe.** The crash glitch frame reseeds
   noise every tick: a 30 Hz full-white strobe over 57 percent of the wall (measured). Life at 8 Hz
   flashes 26 percent. `beat` on onsets can pulse at 10 Hz. Players stand at 2 to 3 m, where the whole
   wall exceeds the WCAG 2.3.1 area. A per-pixel limiter in the runner removed every strobe tested and
   costs 0.2 ms on the Mac. (ops B3, attract 3, fun minor, loop minor)
5. **The audio games measure the sound camp.** The auto-gain divides by a running maximum with a 4.6 s
   half-life, so every scream reads exactly 1.0 and the first yell pegs the night's best. Onsets fire on
   the camp's kick, so `flappy` flaps to the bass and `beat` locks to the camp. (fun B5, sensing B4)
6. **Brightness 0.4 is two to four times too bright at night, and it is not enforced.** After the daemon
   plan amendment the DDP backend's `set_brightness` does nothing; Falcon Player's setting rules. 0.4 of
   an outdoor P5 module is about 2000 cd/m² of white at 2 m against night billboard guidance near 300.
   (ops S5, attract 4)
7. **The 8 ms tick budget is a Mac number.** A Pi 4 runs this code 5 to 10 times slower, and the test
   measures a mean of `update` plus `draw` only. Expect 40 to 80 ms per tick on the Pi against a 33 ms
   tick. (attract 8, sensing S7, loop S1, plan)
8. **A hung sensor looks live.** Nothing timestamps camera or audio results, so a blocked capture serves
   the last frame forever: a frozen wrist relaunches one game every second and idle never fires. Repeated
   frames at a 30 Hz tick also break any per-tick velocity. (sensing B2, ops S7)
9. **About half the games are the right games.** Four are toys or visualisers (puppet, life, ambient,
   beat), two use inputs that fail at a festival (scream, flappy), and the two strongest (holewall, pong)
   need normalisation work to be fair. Consensus verdicts are in section 7.

## 2. Blockers

1. **Session structure and presence.** Add to spec 7.2: a calibrated play zone (camera-space rectangle
   plus a minimum body height, saved by an `arcade calibrate` step); `Sensed.player` and `player2`
   (in-zone bodies, largest scale first, locked by tracker id with 0.5 to 1 s hysteresis, re-acquired
   by nearest position); `Sensed.present` (in-zone body or moving in-zone blob for 1 s, off after 3 s).
   Idle, attract exit and every game read `player` and `present`, never `bodies[0]` or raw blobs. Idle
   applies inside games: 8 s with nobody in the zone ends the session with a 3 s score card. Add an
   engagement timeout (30 s with no input, "still playing? raise a hand", then end) and a session cap
   (180 s while someone else waits). Wire the attract in `main.py`; today `Runner` is built without it.
   Test: launch paint, feed 10 s of empty scene, assert attract is current; hold `stand()` in the menu
   for 10 s at both sizes, assert nothing launches; a crowd of six behind a standing player never steals
   the cursor.
2. **Exit gesture.** Walking away is the exit (blocker 1). Keep a deliberate exit no game asks for,
   forearms crossed in an X for 2 s or both hands for 3 s with a runner-drawn closing ring, and suppress
   it for games that declare `uses_hands_up`.
3. **Cursor and menu.** Map the cursor from a body-relative reach box (the wrist relative to the shoulder
   midpoint, normalised by shoulder width, the Kinect "physical interaction zone"), never from raw frame
   coordinates. Only a hand cursor can dwell-select; body-centre and blob fallbacks draw a ghost cursor
   that never fills a ring. Anchor "raised" on a line above the shoulder midpoint, not the nose, because
   goggles, masks and hoods are normal at a burn. Grow the hovered tile by 2 px and decay dwell over
   0.3 s instead of resetting it on one jittery tick. Smooth keypoints with a One Euro filter; the plan
   smooths nothing.
4. **Walk-up flow.** Replace spec 7.3's front door. Attract is a mirror: entering the zone shows the
   visitor's own stick figure within half a second over the running attract visual. After 1.5 s a 16 px
   hand-up pictogram breathes beside them. A raised hand starts play at once with a 2 s pictogram of the
   game's one action; the featured game rotates. The menu is opt-in from the score card: three big tiles
   (COPY, DODGE, FLAP style verbs), selected by standing under one, 1.2 to 1.5 s dwell. A player who does
   nothing for 5 s gets the featured game after a countdown. The end card reads "HAND UP = AGAIN" and
   "NEXT: RAISE A HAND", then the mirror returns.
5. **Flash governor.** New spec 7.6, runner-level after `draw` and not bypassable: per pixel, linearise
   through `gamma`, take Rec. 709 luminance with saturated red counted double, and hold a reversal of
   0.1 or more when the pixel has already transitioned six times in the last second. Replace the glitch
   frame with one static dim icon fading over 0.5 s. `beat` changes hue, not luminance, on onsets and
   pulses only on a locked tempo at or below 180 bpm. Life steps at 5 Hz or slower with two-tick cell
   fades. Expose `flash_held_ticks` in `runner.state()`. Tests: a 15 Hz white strobe is held to 3 per
   second; menu frames and a moving sprite pass bit-identical; every game's soak includes `claps` at
   12 Hz, `tempo(180)` and an alternating motion grid and must flash at most 10 percent of the wall.
   Add the flashing-light warning to the approach sign.
6. **Audio.** Hardware: a cardioid dynamic mic on a gooseneck at mouth height, gain locked, windscreen;
   a shout at 5 to 20 cm sits 25 to 35 dB over the camp. Features: keep broadband `level` for ambient and
   add `voice_db` (absolute dBFS, 300 Hz to 3.4 kHz, no automatic gain), `floor_db` (rolling 30 s 90th
   percentile), `voice` (dB over floor scaled to 0..1), and `clap` (2 to 6 kHz spectral-flux onset with
   crest factor above 4, 12 dB over floor). `scream` scores dB over the floor and a new best needs 10 dB
   more. Test: a 125 bpm kick plus pink noise yields zero claps in 20 s; claps 12 dB over the floor are
   caught 90 percent of the time.
7. **Pose dropouts and staleness.** The IMX500 source publishes a tensor-less frame as "no bodies", and
   the sensor defaults to 30 fps while HigherHRNet runs at 10, so bodies blink. Set `FrameRate` to 10;
   return `None` from `step()` when there is no output so the last result holds; the tracker coasts a
   missed track for 300 ms and emits `seen_ago`; dwell and exit get a 250 ms grace. `ThreadedCamera` and
   the audio source store a capture timestamp and go `EMPTY` and unavailable past 1.0 s (camera) or
   0.5 s (audio). `Sensed` gains `camera_t`, `camera_fresh`, `camera_seq`; `Body` gains `vx, vy` per
   second computed in the tracker. Games never difference keypoints across ticks.
8. **The Pi camera will not start as planned.** picamera2's HigherHRNet postprocess imports `munkres`
   at module level and the plan's apt line omits `python3-munkres`; the import failure is swallowed as
   "unavailable". Its pure-Python matching runs 16 times per frame on an n by n matrix: measured on the
   Mac and scaled, six people cost about 10 ms per frame on the Pi, fifteen cost 190 to 300 ms, thirty
   cost over a second, all while holding the GIL. Add the apt package, shim the matcher with scipy's
   `linear_sum_assignment`, and truncate each output tensor to the top 8 candidates per joint.
9. **The toolchain breaks on the first command.** This Mac has Python 3.14.5 and uv, no `python3.12`.
   mediapipe is now 1.0.1 with wheels for any Python 3; its unbounded pin pulls in
   `opencv-contrib-python`, which clashes with the plan's `opencv-python`. `MediaPipeCamera` swallows
   every setup error, so a run with no pose at all exits 0. Add a Task 0 environment spike (`uv venv`,
   install, build a `PoseLandmarker` on one JPEG, pin with upper bounds, pick one OpenCV distribution),
   `python -m arcade doctor --require camera,mic,pose` that exits non-zero, and a headless pose test that
   runs a five-second video clip through `MediaPipeCamera`.
10. **The generic tests pass for a game that ignores its input.** Soak, budget, both-layout, and contact
    sheet checks all pass for a screensaver. The soak seeds from Python's `hash()`, which changes every
    process (three runs: three seeds). The contact sheet test asserts `max() > 0` on an image whose
    labels are always non-black. Add a counterfactual input test: for each input event in a game's
    canonical scenario, run with and without it under the same seed and require the frames to diverge
    within `LATENCY_TICKS`. Seed soaks from `zlib.crc32` over a fixed seed list and print the seed on
    failure. Make the sheet test compare each frame region to `render(frame)`, refuse all-black sheets,
    and stamp every sheet with git sha, dirty flag, game, size, look, seed and scenario.

## 3. Serious

11. **Brightness enforcement and a night curve.** Set the card or Falcon Player once as the physical
    ceiling and record it as `panel_brightness`; the DDP backend warns when asked for less than 1.0. Add a
    runner-level average-picture-level limiter (scale through a lookup table only when over cap, never
    below 0.5) and a `night_brightness` around 0.06 to 0.12 driven by the IMX500 lux metadata with a
    clock fallback. The Pi has no real-time clock; add a DS3231 or rely on darkness.
12. **Tick budget.** Set the Mac budget to 3 ms mean and 5 ms p95 over the whole `Runner.tick` with a
    documented `CPU_SCALE = 6`, plus a `pi_perf` marker at 12 to 20 ms. Run `pytest -m perf` on the Pi on
    day one and commit the numbers to `docs/superpowers/workflow/evidence/pi-perf.md`.
13. **Blobs at night.** The 99.5th percentile floor means 0.5 percent of the frame always passes, and
    under the floodlight that is faces and white shirts, so paint paints faces pink. Keep pixels with
    V >= 220 whose 3 px halo is saturated (>= 0.5); take hue from the halo; reject components over 0.5
    percent of the frame; mask a blob that is still for 5 s; keep only in-zone blobs; drop the blob cursor
    while a body is present. Use the `lores` stream: `find_blobs` measured 10.3 ms at 640x480 on the Mac
    (about 60 ms on the Pi) and 0.8 ms at 160x120.
14. **Motion grid self-excites.** Raw differencing at threshold 25 fires on sensor noise (sigma 12 lit
    83 percent of cells in a static dark scene), one-pixel shake, auto-exposure steps, 120 Hz floodlight
    flicker, wind, and the wall's own light. Lock exposure and white balance after a 3 s warm-up and
    re-converge only after 30 s without presence; blur 5x5 and raise fill to 0.2; divide by the frame
    median before differencing; emit an empty grid when more than 35 percent of cells fire; crop the zone
    at the wall's aspect before downsampling; mount the camera on the wall frame, not a pole.
15. **Left and right are different hands on the Mac and the Pi.** MediaPipe runs on the flipped frame
    and labels the mirrored figure; the IMX500 path mirrors after inference. Run MediaPipe unflipped and
    mirror x in one shared `mirror_keypoints()` that never swaps labels. Test: one raised-right-hand
    fixture through both parsers returns `RIGHT_WRIST` at x > 0.5.
16. **BodyTracker fails on real crossings.** The box centre jumps when ankles drop out at night, past
    `max_dist`; matching is greedy with no motion model; the timeout is in frames (1 s on the Pi, 0.33 s
    on the Mac); Review Focus 2 tests two tracks at different heights, which people on one floor never
    are. Anchor on the shoulder midpoint, predict with constant velocity, assign globally with a scale
    term, time out at 0.5 s, and replace the test with two same-height bodies crossing over 2 s with the
    rear one hidden for five frames.
17. **Geometry and calibration.** The AI Camera sees about 1.3Z by 1.0Z at distance Z. A 64 cm wall
    draws people to 1 to 2 m, where the camera sees head to hips. Jump height and holewall distance
    scale with standing distance (2 m scores roughly double 4 m). Add `arcade calibrate` (aim, stand at
    the mat's edges to set the zone, stand still for baseline scale, clear the frame to capture the
    static-light mask and audio floor, lock exposure) saving `data_dir/calibration.json`. Add
    `Body.scale` (smoothed nose to mid-hip) and `Body.in_zone`. Jump height is nose rise over scale times
    0.65 m; holewall centres on the hips, scales by torso, and scores limb angles weighted by confidence.
    Placement: wall bottom edge at about 2.1 m, camera on the frame just below and angled down, a lit
    2 by 2 m mat at 2 to 3 m, floodlight at 2.5 m or higher and 30 to 45 degrees off axis behind the
    camera plane, mic at chest height facing the mat.
18. **No session structure per game.** No game has a length, end card or replay; flappy exits to the menu
    on every death. Every game ends in 45 to 90 s or on a clear result, shows a 4 s end card with score,
    "BEST!" on a record, and "HAND UP = AGAIN".
19. **Non-uniform keypoint scale.** Task 11 maps x and y independently, so a 4:3 frame stretches figures
    three times wide on 128x32 and squashes them on 64x64; holewall targets and live figures will not
    match. Add a shared `to_wall(body, rect)` that scales uniformly by body height; on 128x32 give each
    player a 64x32 half. Pong assigns sides by x, not id order.
20. **Text is marginal at 5 m and the preview cannot tell.** A 5x7 glyph is 35 mm tall with 5 mm
    strokes: 24 arcmin at 5 m, and halation closes the one-pixel counters. Add `scale` to `Canvas.text`;
    scores use 2x (10x14, 2 px strokes, reads to about 10 m); bars before numbers for jump and scream;
    icons get 2 px strokes and one colour per game. Make `distance` take metres and model a 1.5 arcmin
    blur plus a luminance-weighted halation Gaussian.
21. **Operations.** No systemd unit, watchdog or status output; failed sources never retry; errors log 30
    times a second. Add `Restart=always`, `StartLimitIntervalSec=0`, `WatchdogSec=10` pinged only while
    ticks advance and a push succeeded; retry unavailable sources every 30 s and exit non-zero after 5
    minutes of camera failure; log repeats once per minute; write `/run/arcade/status.json` every 10 s
    (game, fps, temperature, throttling, sources, crashes, governor count, detections per minute) served
    read-only on the site LAN; SoC temperature and `vcgencmd get_throttled` every 10 s with 15 fps above
    75 °C and a static frame above 82 °C; read-only root, volatile journald, `data_dir` on its own
    writable partition; a GPIO3 shutdown button and a laminated card in the lid; a dusk restart timer.
    Prefer a second Pi over sharing the Code is Art Pi.
22. **Privacy.** Nothing identifying is written today, but no rule keeps it so and agents reach for
    `cv2.imwrite` when debugging. New spec 6.5: no camera frame or audio sample leaves its source thread;
    nothing is written, logged or sent except Sensed records, scores and status. Enforce with a test that
    fails if `arcade/` references `imwrite`, `imencode`, `np.save`, `Image.save`, `VideoWriter` or
    `wave`. `arcade record` needs `--i-have-consent`, shows 3-2-1 then a red REC counter on the wall, and
    drops `motion` unless asked. Signs at the approach and the camera: "This camera sees you as 17 dots.
    Nothing is recorded or saved. Stand outside the square and it ignores you." Declare the camera on
    the placement form.
23. **Verification honesty.** The implementer writes its own acceptance tests, so the cheapest fix for a
    red test is the expected number. The second plan must contain each game's test module in full; the
    reviewer lists every removed or changed `assert` in `tests/` and blocks unless the commit justifies
    it; the journal records the collected test count and skip count each iteration and a drop is a gate;
    feel budgets live in a toml the loop may tighten but never loosen. `debug_state` is the game's own
    claim: adopt the `_xy` convention (a key ending in `_xy` holds wall pixels of a visible entity) and
    one generic test that the pixel at each `_xy` is lit. Add a collection hook that fails unless every
    game's test module carries at least three `128x32` items.
24. **Open-loop actors cannot play a game with randomness.** Add `arcade/bots.py`: a closed-loop policy
    `(debug_state, t) -> actor` with reaction ticks and noise. Each game ships a `good` and a `lazy` bot,
    and difficulty becomes a measured win-rate band over 20 seeds. Add `degrade(scene, fps=10,
    latency=0.15, keypoint_dropout=0.15, jitter=0.01)` and festival actors `crowd`, `headlamps`,
    `camp_kick`, `wind`, `shake`; the soak also runs under `degrade` with a `hostile_mix`.
25. **Recordings cannot re-run the pipeline.** `record.py` stores post-tracker Sensed at 30 Hz. Add
    `--raw` (per camera frame: capture time, raw detections, a 160x120 frame, 16 kHz WAV) and replay
    sources that run the real `FrameFeatures`, `BodyTracker` and `AudioFeatures` on it, so the tracker,
    blobs, motion and audio can be re-tuned from one backyard-night recording.
26. **Registry as a merge hotspot.** Every game appends an import to `arcade/games/__init__.py`, so
    parallel implementers conflict and menu order becomes merge order. Hold a fixed `MENU_ORDER` of all
    names from spec section 8, discover modules with `importlib`, skip missing ones, and assert the order
    matches the spec.
27. **External skills.** `pixel-art-sprites` is gone upstream (the repo is now `maddhruv/absolute`) and
    its dark shading ramps vanish at 40 percent brightness with gamma 2.2, so skip it. Installing
    `media-os` or the gamedev marketplace whole adds 96 and 73 skills including the `pygame-core` the
    spec rejects; vendor only `cv-mediapipe` and `game-feel` as single SKILL.md files pinned by commit
    sha. `procedural-gen` and `performance-optimization` add nothing here. Write `arcade-verify` and
    `arcade-game-authoring` right after Task 20 and before the second plan's first game; the feel rules
    must exist as tests before any second-plan game.
28. **The model reads a downscaled sheet.** Default `--scale 6 --cols 6` makes a 128x32 sheet about
    4,600 px wide; the viewer downsamples it 3x and erases LED dots. Cap sheets at 1,536 px wide and emit
    two per scenario, `plain` for content and `led` for look. Add `--flash-report` printing worst flicker
    area and mean picture level, because a sheet sampled every 10 ticks hides flicker.

## 4. Minor

- Best of the night never resets; roll over at 16:00 and keep last night's best for attract.
- Every launch uses `random.Random(self.seed)`, so every run of a game is identical; seed per launch
  with `(seed, launch_count)` or declare a "course of the night".
- Frogger lets both body x and a raised wrist move the frog; walking makes hopping pointless.
- Steering with a raised hand tires people in about 20 s; use the hand to confirm, the body to aim.
- Title scroll at 20 px/s judders at 30 Hz; use 15 or 30. `DIM_COLOR (40,40,60)` is about 1.7 percent
  light after gamma; strike through unavailable icons instead.
- Audio visuals need `level_smooth` with 50 ms attack and 300 ms release. `AudioFeatures.latest()`
  advances history per call, so gain decay depends on tick rate; define windows in seconds.
- picamera2 boxes are (y0, x0, y1, x1); pass `img_size=(288, 384)` and never use its boxes.
  `MediaPipeCamera.close()` releases the capture while a `read()` may be in flight; `IMX500Camera` never
  calls `picam2.close()`. A denied macOS mic permission delivers exact zeros; warn after 2 s.
- Jump: keypoint jitter reads as a jump; require a 0.1 scale rise over two frames and freeze the
  baseline while airborne. Frogger: re-arm the hop after the wrist has been down 300 ms.
- The REPL leaves no trace; add `--log` and a `repl_to_test.py` so probes become regression tests.
- Soak's final check is vacuous after `done()`; keep a reference to the launched instance and assert
  the declared phases were reached.
- Scenario motion is stored at the recording's wall size; record on a fixed 128x64 grid and resample.
- Puppet draws one-pixel lines against the wall-look two-pixel rule.
- A session log (`data_dir/sessions.jsonl`: game, duration, players, score, end reason) and `arcade
  stats` are the only way to learn which games worked after night one. Effort S.
- Camera behind a downward-angled acrylic window with a hood and silica gel; wipe nightly; run dusk to
  dawn only.
- Add a six-person actor scene to every soak; the Mac caps MediaPipe at two poses while the IMX500
  returns many.

## 5. Attract mode

The single `ambient` entry with a fixed 60 s cycle of rain, fire and boids is replaced by a director and
a catalog. The director becomes the runner's lobby (LOBBY and GAME are the only runner states), with
presence tiers and hysteresis: EMPTY (nothing 3 s), PASSING (motion, a body, or a qualifying blob), NEAR
(a body of box height 0.35 or more stable 0.5 s, or a moving in-zone blob 1 s), ENGAGED (a raised wrist
on a NEAR body 0.4 s). ATTRACT runs at EMPTY and PASSING and gets `attend(focus)` so a mode reacts to a
passer-by. INVITE at NEAR shows the hand-up pictogram. MENU at ENGAGED fades tiles in over the running
mode, which drops to 30 percent energy; dwell starts after the fade. Modes declare `needs`, `calm`, and a
duration range; the next mode is a weighted random choice (zero if needs are unavailable, 0.2x if among
the last three, matched to a night calm curve, 2x for audio modes under a tempo lock). Transitions are a
1.5 s linear-light crossfade or a noise dissolve, never a cut. Handback from a game is a 3 s big-digit
score card, then MENU at NEAR or ATTRACT otherwise. All twelve prototypes below measured 0.02 to 0.26 ms
per frame on the Mac at both sizes.

| Mode | Reacts to | Pi 4 estimate | Effort | Test |
|---|---|---|---|---|
| Watcher (a large eye that tracks the nearest body, blinks, dilates as one nears) | bodies, motion | 1.3 ms | S | pupil follows `walk(0.1,0.9)` |
| Echo (motion decays into an age-coloured afterimage) | motion | 0.4 ms | S | black 3 s after motion stops |
| Rain, reworked (3 to 4 px tails, splits around motion) | motion | 0.5 ms | S | no drop inside a motion block |
| Embers (coal bed, flames rise under motion, scaled by audio) | motion, audio | 0.6 ms | S | heat over a motion column is 2x |
| Fireflies (48 points phase-sync at 0.5 Hz, scatter from people, nudged by beats) | motion, bodies, audio | 0.5 to 2.1 ms | M | order parameter above 0.8 idle, below 0.5 after a walk |
| Ripple pond (wave equation; onsets drop pebbles, walkers leave wakes) | audio, motion | 0.6 ms | S | a clap makes a growing ring |
| Heartline (mirrored `level_smooth` trace scrolling at 10 px/s) | audio | 0.3 ms | S | two claps, two peaks |
| Warp (150 stars with 2 px streaks, faster under audio) | nothing, audio optional | 0.2 ms | S | speed rises under `loud` |
| Contours (2 px isolines of warped sines) | nothing | 0.8 ms | S | lit fraction 0.05 to 0.2 |
| Aurora (green and violet curtains, picture level 0.02, for after 02:00) | nothing | 0.5 ms | S | picture level below 0.03 |
| Life drift (Life at 4 Hz, cells fade over four ticks, seeded by motion) | motion | 0.5 ms | S | flicker at most 0.10 |
| Snowfall on you (flakes pile on a 2 px skeleton's shoulders, fall when you move) | bodies | about 2.5 ms | M | flakes above shoulders after 5 s of `stand` |

Attract also shows tonight's best per game with the holder's frozen stick figure, and every 20 s a 5 s
demo replayed from a recorded scenario. Two lenses recommend moving `life` and `beat` into this catalog.

## 6. Verification and the autonomous loop

What an agent can measure headlessly, proposed as `arcade/feel.py` with per-game budgets in
`arcade/feel_budgets.toml`. Every game declares `SCENARIOS` including `canonical`, `idle_body`, `nobody`,
`fail` and `win`; tests, sheets, GIFs and metrics all read that one source.

| Metric | Computed as | Default budget |
|---|---|---|
| Response latency | counterfactual diff: ticks from an input event to the first frame differing by 12 px or more | at most 2 ticks (control), 1 (toys) |
| Response magnitude | pixels changed by one event in the `distance` render | at least 12 px or 0.5 percent |
| Control fidelity | Pearson r between actor x and the controlled `_xy` over a sweep | at least 0.9, monotonic |
| Reachable range | playfield covered when the actor sweeps 0.25 to 0.75 of the frame | at least 90 percent |
| Liveliness | median fraction of pixels changed per tick | 0.5 to 40 percent |
| Lit fraction | median lit after gamma and brightness | 3 to 60 percent |
| Dim pixels | lit pixels with max channel below 48 outside declared fades | at most 10 percent |
| Flashes | full-field swings per second | at most 3 |
| Distinct states | 8x8 mean-hash frames per session, and `phase` values reached | every declared phase; 6 hashes |
| Score visible and legible | template-match the project font against `debug_state()["score"]`, then after the `distance` blur | matches every tick; no digit pair below threshold |
| Fail vs win | hue histogram and transient duration after each event | differ; 6 to 60 ticks |
| Hint | in `idle_body`, a prompt appears | within 90 ticks |
| Round length | `good` bot until `done()` | 20 to 120 s |
| Difficulty | win rate over 20 seeds: `good`, `lazy`, none | 40 to 90, below 30, 0 percent |

What stays human: whether a stranger gets it in ten seconds, whether the motion feels good or
embarrassing, total latency with the real camera, colour taste, night glare. The metrics find dull and
broken games cheaply; they cannot find the good ones.

**Real-input fixtures the owner records once** (about five minutes on the Mac, five of them again on the
Pi): `empty-room`, `walk-in-stand-leave`, `menu-point`, `wrist-sweep`, `exit-gesture`, `jumps-squats`,
`poses-8`, `torch-paint`, `idle-still`, `claps-tempo-voice`, `music-speaker`, and optionally
`two-people-cross`. `arcade record --script NAME` shows timed cues in the SDL window and writes the cue
times into the scenario header, so the script is the ground truth. Each yields cue assertions, a replay
through each consuming game, and fitted `REAL_NOISE` constants.

**Evidence package** per iteration, written by one command to `docs/superpowers/workflow/evidence/itNN/`:
`README.md` whose first line is the decision with a default and a deadline, then the feel table, the
reviewer verdict, test and skip counts against the last iteration, and every image inline; per changed
game `<game>-<size>-led.png`, `-distance.png`, `-canonical.gif` (at most 6 s, 300 KB), `-trace.jsonl`;
`feel.json`; `review.md`. Owner answers go in `docs/superpowers/workflow/decisions.md`, one line each,
read by the loop every iteration.

**Gate table**

| Decision | Who |
|---|---|
| Keep or cut a game | Human |
| Difficulty numbers, colour palettes, menu order, icons, dependency pins, skill edits | Loop, journaled |
| Dwell time | Loop proposes from fixtures, human confirms once live |
| Brightness ceiling, where gamma is applied | Human |
| Feels good on the live webcam | Human, via a `live-smoke.md` filled in on a phone |
| Move to the Pi | Human |
| Write the second plan | Loop, after the owner's first live smoke |
| Loosen a feel budget or change a plan-literal test | Human; tightening is the loop's |
| Delete or re-record fixtures | Human |
| Publish evidence outside the machine | Human, once |

## 7. Game verdicts

Consensus of the fun, sensing and ops lenses. "Realistic input" is the sensing lens's verdict on the
input as designed.

| Entry | Verdict | Realistic input | Reason |
|---|---|---|---|
| menu | REWORK | needs change | eleven tiny icons, cursor reaches the top third, body-centre launches by accident |
| paint | KEEP, fix | needs change | burners carry lights; draw segments not stamps, take hue from the halo, in-zone blobs only, 5 s gallery freeze |
| puppet | REWORK | OK | the strongest "it sees me" moment but nothing to do; becomes the attract's mirror layer |
| frogger | CUT | needs change | body x and wrist hop conflict, nothing at stake; Dodge replaces it |
| pong | KEEP, fix | needs change | proven camera game, great to watch; sides by x, body-relative height, CPU paddle for solo |
| jump | REWORK, merge | needs change | three-second novelty, score depends on distance; merge into a Strongman high striker |
| holewall | KEEP, hero | needs change | copying needs no words, failures are funny, crowd reads it; needs uniform scale and torso-normalised scoring |
| life | CUT to attract | OK after motion gate | players cannot see cause and effect; belongs in the catalog as Life drift |
| ambient | REWORK | OK | becomes the director; not a tile |
| scream | REWORK, merge | unrealistic | meter always maxes; becomes "3, 2, 1, ROAR" in Strongman with the near-field mic |
| flappy | REWORK | unrealistic | kick drums flap it; switch to arm flapping on wrist `vy` |
| beat | CUT to attract | unrealistic as a game | no player agency; its music look belongs in attract |

**Hero: holewall as "Copy Me".** Live figure in the player's colour, target as a cyan outline growing
toward them over 3 s, each limb turning green when its angle is within tolerance, flash and score pop at
zero, the round's best frame frozen 1.5 s. Pose relay (the winner strikes a pose that becomes a future
target), two players head to head on 128x32, and a pose ladder from easy to silly.

**Proposed additions** (fun lens; effort S to M): Flap (both wrists sweep down within 0.4 s), Dodge (the
Chrome dinosaur with your body: jump low, duck high), Swat (Fruit Ninja with hand paths), Quick Draw
(two players, first hand up after "DRAW!", false starts lose), Freeze (freeze dance to the sound camp,
movers topple), Tug (the crowd game: whichever half of the camera moves more pulls the knot; needs no
pose, so it survives costumes and ten people). Strongman merges jump and scream. Suggested ship order:
Copy Me, Pong, Quick Draw, Dodge, Tug, Flap, Swat, Paint, Strongman, Freeze. Keep at least two pose-free
games (Tug, Paint) for costumes and EL wire.

**Shared juice toolkit** (`arcade/juice.py`, runner-owned, deterministic, budget under 0.5 ms):
`shake`, `flash` (at most 3 per second), `burst` (particle pool capped at 96), `pop`, `banner`, `freeze`
(hit-stop), `celebrate`, `echo` (a glyph over the player's marker on the tick a gesture is recognised, so
acknowledgement adds no latency on top of the camera's 150 to 200 ms), with `fx_*` keys merged into
`runner.state()` so tests can assert on them. A 2 px marker in the player's colour stays on the bottom
row under them in every game.

## 8. Plan executability

The plan reviewer extracted every code block from daemon Tasks 1, 2, 5 and 15 (amendments applied) and
arcade Tasks 1 to 14 and 20 into a scratch repo on Python 3.12 (uv, numpy 2, pygame 2.6.1,
opencv-python 5.0, no mediapipe or picamera2) and ran it. Tasks 15 to 19 were read, not run. The
14 probe tests are `plan-probe-tests.py` in the lenses directory; the corrected code blocks are in
`05-plan.md` there.

**As written: 109 collected, 109 passed** on the first run. Under twelve different `PYTHONHASHSEED`
values the Task 20 soak failed in ten of them. Of 14 probes asserting what the spec requires, 11 failed
against the plan's code. With the corrections below applied, 124 pass and one fails (the brightness cap,
which needs a decision, item 6 in this section). Every signature was checked across the tasks that define
and use it (`Game`, `GameInfo`, `MenuLike`, `Canvas`, `Body` helpers, actors, `run_headless`, `Runner`,
scenario reader and writer) and no mismatches were found. Runner tick order matches spec 7.2; the menu
lays out on 128x32 (29 of 32 rows), 64x64, 96x48 and 128x64; Review Focus 1 and 4 pass.

Blockers and serious items in the plan's code, each demonstrated by a probe and each with a verified fix
in the reviewer's report:

1. **Soak nondeterminism (Task 20).** Besides the salted `hash()` seed, `random_mix` draws zero to two
   persons and blobs, so a third of the time puppet gets no body and paint no blob, and a correct game
   draws black. Seed with `zlib.crc32`, always supply the inputs the game's `needs` declares, and add
   96x48 to the size list. Add to Global Constraints: never seed from `hash()` of a string.
2. **The crash guard misses `__init__`, `reset` and `done()` (Task 8).** `launch()` constructs and
   resets outside any `try`, and `done()` is called outside the guarded block. A game that raises in
   `reset` when picked from the menu ends the process. Nine unwritten games will each get a `reset`, so
   this is the most likely festival crash. Wrap both; add tests for a game raising in each.
3. **Abandoned games never time out, and `main.py` never passes `attract`** (Task 8, Task 18).
   Confirms convergence item 1 at code level. Fix: idle applies from any game; when the registry lacks
   the attract entry the menu is the attract screen; construct the runner with `attract="ambient"`.
4. **The exit gesture flows straight into a relaunch (Tasks 8 and 9).** After the return to the menu
   the player's hands are still up, the cursor sits on a top-row tile, and the game relaunches after
   `dwell_seconds`; demonstrated at t = 2.5 s. Hide bodies and blobs from the menu until both hands come
   down. Test: hold both hands up 4 s through an exit, assert no launch.
5. **The test harness hides crashes and returns the wrong object (Task 8).** `run()` returns
   `runner.current`, which after `done()` or a crash is the `NullMenu`, so the TDD agent sees
   `KeyError: 'lit'` instead of the traceback. Add `strict=True` to the harness (re-raise in `_crashed`)
   and keep the launched instance as `runner.game`. This is the most expensive debugging trap in the plan
   for an unattended loop.
6. **Brightness is enforced nowhere.** `SDLDisplay` ignores it on purpose and `DDPDisplay` sends
   unscaled bytes after the amendment; a probe pushing 255 at brightness 0.4 received 255. Decide: (a)
   the ceiling is Falcon Player's setting, `brightness` is documented as preview-only and the runner logs
   that at startup on the `ddp` backend, or (b) scale in software for DDP with a lookup table at a cost
   of about 1.3 bits at 0.4. The reviewer recommends (a) with a bring-up checklist line; the attract lens
   adds the average-picture-level limiter (item 11) on top either way.
7. **Canvas raises on floats and `line` can hang (Task 5).** `pixel(3.5, 2)` raises `IndexError`,
   a colour of 300 raises `OverflowError`, `line(0, 0, 10.5, 0)` loops forever, and `line(0, 0, 1e9, 0)`
   walks a billion clipped pixels. Every moving game keeps float positions. Add integer and colour
   coercion with NaN and infinity landing far off-canvas, and an early return when endpoints exceed four
   times the canvas extent.
8. **`Runner.state()` lets game keys overwrite runner keys (Task 8).** Paint's `idle` replaces the
   runner's `idle` in every REPL reply today. Runner keys win; add `crashes`, `glitch`, `t`, `attract`;
   rename paint's key; assert in the soak that no game reuses a runner key.
9. **Games cannot reach `Scores` (Tasks 7 and 8).** Games take no constructor arguments and never touch
   config, so jump, scream and flappy cannot record a best. The runner sets `game.scores` before
   `reset()`; `Scores(None)` keeps scores in memory for tests and tools.
10. **`tempo()` fires double beats at 128 bpm (Task 4).** A beat on a half-tick boundary matches two
    adjacent ticks: 135 beats in 60 s. Fire exactly one tick per event, the first at or after it; same
    for `claps`. Add 128 to the actors test.
11. **The agent tools return wrong but plausible results (Tasks 13 and 14).** `launch` then `shot`
    writes the previous game's frame; `hand=rihgt` parses as no hand; `blob=0.5,0.5,255` becomes white;
    a crashed game shows 30 glitch frames then black with exit 0; `beat=120` fires once per step. Clear
    `display.last` on launch, menu and reset; validate verbs and echo the parsed input; refuse an
    all-black run without `--allow-black`; add a `log` verb printing the last traceback; build audio from
    `tempo(bpm, start)` for the whole step.

**Framework additions this plan must make now** so the second plan never edits files the first plan's
tests pin: `GameInfo.exit_gesture` (holewall, jump, pong turn the exit off); `game.scores`; canvas float
coercion, `blit_rgb` with black transparent and `sprite_from_rows(rows, palette)`, and `text(scale=2)`;
actors `Person.wrist(hand, y_from, y_to, seconds, at)` for continuous hand height, `Person.pose(name)`
with a shared `arcade/poses.py` table (mechanism plus two poses), a raw motion script for Life,
`level_ramp`, and exact event ticks; REPL support for multiple bodies (`x=0.3,0.7`), `pose=`, `motion=`,
and beats held for the whole step; an `arcade/input.py` with `Edge` and `Hold(seconds)` shared by
frogger, holewall and the menu; guarded registry imports so one broken module does not take down the
arcade; a strict harness. `Sensed` itself is sufficient for all nine games as specified (the sensing and
fun lenses add fields for other reasons).

**Frame budget, measured on the Mac at 64x64:** runner bookkeeping, Sensed construction and clear cost
under 0.1 ms per tick; paint 0.09 ms, puppet 0.19 ms, menu 0.07 ms; the LED-look preview render 3.2 ms
(Mac only); `FrameFeatures` on the camera thread 10.7 ms at 640x480 and 2.7 ms at 320x240. Scaled 7 to
10x for a Pi 4 and allowing 5 to 10 ms for GIL contention with the camera thread, about 20 ms of the
33 ms tick remains for `update` plus `draw`. The plan's 8 ms Mac budget admits a game that runs at 12 to
15 fps on the Pi. Set `BUDGET_MS` from an environment variable defaulting to 2.0, assert p95 under twice
the budget, time the whole `runner.tick` through the harness, and rerun on the Pi with 20 ms in
prototype week. Blobs must run on the low-resolution stream and use `cv2.mean` over each component's
bounding box instead of eight full-frame mask passes.

**Minor, plan:** a registry import failure takes down every game; the menu silently drops a twelfth
game and cannot fit on a single 64x32 panel (pick the layout by fit or reject the size); `DIM_COLOR` is
invisible after gamma; a crashing menu glitches forever (fall back to a title card); `needs` is
AND-only and cannot express pong's "wrists or blobs"; the protocol should say `draw()` must work right
after `reset()`; spec drift to fix in the spec (7.4 "kept canvas", 9's `--actors` syntax that became
`--person`, 6.4's `combine` that became `scene`); opencv-python 5.0 and pygame both bundle SDL2 on macOS
and the live preview imports both in one process, which prints casting warnings and may crash, so move
`cv2.blur` in `look.py` to numpy or run the preview with `pygame-ce` if it bites.

## 9. Descoping ladder

If the loop falls behind or the Pi is late, in this order:

1. Ship 128x32 as the design layout; 64x64 only has to run and stay legible.
2. Drop audio games entirely; keep the mic for attract only.
3. Ship Copy Me, Pong, Paint and Tug with the attract director and the new walk-up flow.
4. Drop the menu; the featured game rotates and a hand starts it.

Minimum viable arcade: attract director with four modes and the mirror, the new walk-up flow, the flash
governor, Copy Me and Pong, session log, systemd unit and status file.

## 10. Decisions for the owner

- Accept the consensus game list changes in section 7 (cut frogger, life, beat as games; merge jump and
  scream; rework flappy to arm flapping; add Quick Draw, Dodge, Tug, and which of Flap, Swat, Freeze).
- Accept the new walk-up flow (mirror, hand-up prompt, play at once, opt-in three-tile menu) in place of
  spec 7.3's twelve-tile grid.
- 128x32 as the design layout.
- Buy: a cardioid dynamic mic plus USB interface and gooseneck; a DS3231 clock or rely on lux; a second
  Pi 4 rather than sharing the show daemon's.
- Brightness: accept a night default near 0.08 and measure with a lux meter in prototype week.
- Camera consent: accept spec 6.5 and the sign text, and declare the camera on the placement form.
- Fold the accepted items into spec revision 2 and amend the core plan (Task 0 environment spike,
  presence and player fields, flash governor, timestamps, budget, seeds, sheet provenance,
  counterfactual test, `MENU_ORDER`, munkres) before the operator starts.

## 10a. Owner decisions so far

- **2026-09-26, layouts.** 128x32 is the design layout, chosen for two-player side-by-side play. 64x64 is
  not a mere constraint: the two panels will often sit stacked on a bar where a 128x32 banner takes too
  much room, so 64x64 is a first-class configuration for single-player games and for visuals that suit a
  square. Consequences for spec revision 3: `GameInfo` declares which layouts a game is designed for
  (`layouts: frozenset[str]`, both by default); the menu and the attract director show only entries
  designed for the current layout; per-layout tuning tables where a game needs them (lane counts, paddle
  travel, figure scale); feel budgets apply in full on every layout a game declares and the
  run-and-legible constraint applies on the rest; the owner's live smoke covers both layouts. A game
  designed for both is the goal where it costs little (Copy Me single-player on 64x64, head-to-head on
  128x32), never a requirement.
- **2026-09-26, games.** The section 7 verdicts are accepted: cut frogger; life and beat move to the
  attract catalog; jump and scream merge into Strongman; flappy becomes arm flapping; puppet becomes the
  attract's mirror layer; holewall is the hero as Copy Me; pong and paint stay with their fixes. The
  additions Quick Draw, Dodge, Tug, Flap, Swat and Freeze are accepted, in the ship order of section 7.
- **2026-09-26, walk-up flow.** Blocker 4's flow replaces spec 7.3: mirror, hand-up pictogram, play at
  once, opt-in three-door menu, end by leaving.
- **2026-09-26, operator.** The operator design (`2026-09-26-arcade-operator-design.md`) is approved as
  written. Bootstrap follows spec revision 3.

## 11. Checked and found OK

- Fixed 30 Hz tick with clamped `dt`, injected clock and injected rng; the counterfactual test depends
  on exactly this determinism.
- `debug_state`-first testing, which extends cleanly to `fx_*` and `_xy` keys.
- Stable, never-reused tracker ids, which make a player lock simple.
- Pass-through never launches; unavailable games dim with a reason; the dwell ring shows progress.
- Mirroring once at the source; a brightness cap no game can raise (mechanism right, value wrong).
- The crash guard is tested end to end including hiding after three crashes; the runner never exits
  on a game error; sources never block the tick; hardware imports are lazy; one lock per source, never
  nested.
- Headless SDL in conftest; the REPL is deterministic, one JSON line per verb; one `look.render` for
  preview and sheets.
- IMX500 output is in COCO order, `(x, y, score)` layout, `img_size` is (H, W), `RGB888` is BGR in
  memory, the binned 2028x1520 mode keeps the full field of view. MediaPipe timestamps increase strictly
  and out-of-range landmarks are cleaned (Review Focus 1).
- All twelve attract prototypes run in 0.02 to 0.26 ms per frame on the Mac; the flash limiter costs
  0.2 ms and passes legitimate motion untouched; beyond 5 m the whole wall is under the flash area
  threshold.
- No raw frame or audio sample is persisted anywhere in the plan today; no sound output, so no
  quiet-hours problem.
- The slow running-maximum audio gain gives usable range for ambient visuals beside a sound camp (it is
  wrong only as a score).
