# Adversarial review, lens 2: attract mode and ambient visuals

Scope: spec sections 7.2, 7.3, 8 row 9, 9 and 11, and plan Tasks 5, 6, 8, 9, 15 and 20. No repo file was edited.

Figures marked "measured" come from prototypes next to this file:

- `bench_attract.py` runs 12 candidate modes in numpy.
- `flashguard2.py` holds the proposed flash limiter and an independent WCAG-style flash counter.
- `modeflash.py` measures flicker area and average picture level (APL) per mode.

Pi 4 estimates are M1 timings times 8. Confirm them on the Pi.

## Blockers

### 1. Raw blobs gate attract, so the piece rarely shows (spec 7.2, Tasks 8 and 15)

`present = bool(sensed.bodies or sensed.blobs)` gates both entry and exit. `find_blobs` reports any max-channel of 200 or more with 4 or more pixels. At night that is nearly always true. Headlamps, distant art, string lights and art cars all qualify. So does the play area's own floodlight, because auto-exposure pushes a floodlit patch and white shirts toward 255. The 60 idle seconds rarely accumulate, and the next headlamp ends any attract run.

Three bugs compound it:

- **Interruptions restart at rain.** Spec 7.1 makes a fresh instance per launch, so interruptions more often than every 60 s mean fire and boids never appear.
- **Launches repeat exactly.** `launch` passes `random.Random(self.seed)` every time, so each run is the same rain.
- **The audience triggers the exit.** A passer-by at 4 m is who attract exists for. Detecting them snaps the wall to eleven 8x8 blue icons, which read as dots from 5 m.

**Fix.** Use graded presence tiers in a director, described below. A blob counts only if it is inside a configurable play region, is moving, and is outside a learned background mask. A cell that has held a blob for more than 20 s is scenery. Seed each launch with `hash((seed, launch_count))`.

**Test.** A static bright blob in the top band plus a headlamp blob crossing every 20 s still reaches attract within `idle_seconds` and stays there.

### 2. Abandoned games never hand back (spec 7.2, Task 8)

The idle check runs only while the menu is current. When a player walks away mid-game, which is how festival games usually end, the game runs all night.

**Fix.** Add `abandon_seconds` to `GameInfo`, default 20. A game hands back to the lobby by dissolve after that long at the PASSING tier or below. `paint` opts out with `None`.

**Test.** Launch `spy` and feed 20 s of empty scene. The game should be the lobby, in attract.

### 3. No flash rule, and three specified behaviours exceed 3 flashes per second (spec 7.2, spec 8 rows 8, 11, 12)

WCAG 2.3.1 limits flashing to 25% of a 10-degree field, which is 19.6 deg².

| Distance | Either layout |
|---|---|
| 2 m | 83 deg² |
| 3 m | 37 deg² |
| 5 m | 13 deg² |

Players stand at 2 to 3 m, where a full-wall flash exceeds the limit. The limit was calibrated for lit rooms. A dark field with a source near 2000 cd/m² is worse, so treat it as a floor.

Offenders, measured as the fraction of wall flashing more than 3 times in any second:

- **Glitch frame (Task 8).** It is reseeded every tick, making 30 Hz noise for one second. Measured 0.57. One fixed mask that fades out measures 0.00.
- **`beat`.** The onset fallback can pulse at 10 Hz, and tempo lock allows 4 Hz. Halve the pulse rate above 150 bpm, and keep onset pulses to 25% of the wall or less.
- **`life` at 8 Hz.** Blinkers flash at 4 Hz. Measured 0.26 at 64x64. Step at 5 Hz or slower, fade cells over 2 ticks, and stamp after the step so body boxes do not drop out per step.
- **`flappy` game over.** It is unspecified, and a red flash is the genre default. Specify a hold and one slow fade.

**Fix.** Add `arcade/flash.py`, called in `Runner._push` after compositing. Per pixel it:

- linearises through `cfg.gamma`, takes Rec. 709 luminance, and counts saturated red double;
- tracks the last extreme and direction, with a 30-frame ring of transitions;
- allows a reversal of 0.1 linear or more only after fewer than 6 transitions in the last second, and otherwise holds the previous value.

That guarantees 3 flashes per second or fewer per pixel. Measured:

- It takes full-wall strobes at 4, 5, 10 and 15 Hz from 1.00 to 0.00.
- A moving sprite, a 2 Hz strobe and the fading glitch pass bit-exact.
- It costs 0.2 ms on the M1, about 1.6 ms on the Pi.

Expose `flash_held_ticks` in `runner.state()`.

**Tests.** Add these in `test_flash.py`:

1. Strobes through the limiter keep counter area at 0.25 or less.
2. Menu frames and a sprite pass bit-identical.
3. A 10 Hz strobe game passes through the real runner.
4. Task 20's soak asserts raw game output flashes on 0.10 of the wall or less, with a 10 Hz onset actor in the mix.

Item 4 catches real bugs. A naive level trace measured 0.57, and an undamped ripple measured 0.33 at 128x32.

## Serious

### 4. Brightness has no enforcement, no night curve and no clock (spec 4.3 and 10, Task 1 step 4)

After the amendment, `DDPDisplay.set_brightness` does nothing, so `brightness = 0.4` is ignored and Falcon Player's setting rules. Even if it were enforced, 0.4 is two to four times the sibling's night range of 0.10 to 0.20. Outdoor P5 modules are typically rated 4000 to 6000 cd/m², so 0.4 is about 2000 cd/m² at 2 m. Prototype fire averages an APL of 0.20 to 0.28. That much light also disturbs the camera's exposure, blobs and motion.

**Fix.**

- Set the card or Falcon Player once as the physical ceiling, recorded as `panel_brightness`.
- The DDP backend warns when asked for less than 1.0.
- The runner applies an APL limiter, scaling through a lookup table only when over cap and never below a 0.5 factor. That loses at most one bit.
- Default `apl_cap` is 0.12 until 01:00, then 0.06.
- Modes receive `energy` and dim by lighting fewer pixels.
- A Pi 4 has no real-time clock and a burn has no NTP. Add a DS3231 (about $5), or drive the schedule from darkness using picamera2's Lux metadata, which must be verified on the IMX500.

**Test.** A full-white frame comes out at or under the cap, and a frame already under it passes bit-exact.

### 5. One entry, a fixed 60 s cycle and hard cuts (spec 8 row 9)

Rain on 128x32 crosses the wall in one second, so it is learned in ten and repeats for fifty more. Fire has the highest APL of any mode. Boids flee wrists, but pose works only within about 5 m. Cuts are hard. No mode reacts to an approaching person, so the wall shows no sign it sees anyone. Replace this with the director and catalog below. The `ambient` tile becomes the director in showcase mode, keeping eleven entries.

### 6. The motion grid self-excites (Task 15)

Raw absolute difference at 25 fires across the whole grid whenever global light changes. Causes include the wall's own light, sweeping art-car lights, and auto-exposure steps. Fire then brightens under motion, which lights the scene, which reads as more motion.

**Fix.** Divide each frame by its median before differencing, and return an empty grid when more than 40% of cells fire.

**Test.** Adding 30 levels to a whole frame gives an empty grid, while an 8x8 moving square still registers.

### 7. Text is marginal at 5 m and the preview cannot tell (spec 9 and 11, Tasks 5, 6, 9)

A 5x7 glyph is 35 mm tall with 5 mm strokes.

| Distance | Glyph height |
|---|---|
| 2 m | 60 arcmin |
| 5 m | 24 arcmin |
| 10 m | 12 arcmin |

Signage wants about 20 arcmin, so it reads to about 5 m at best. At night, halation closes the 1-px counters in B, 8, e and M. This breaks the wall-look skill's own two-pixel rule. `distance` is a fixed blur with sigma about 0.46 px. It takes no distance and no brightness, and it skips the downsample spec 9 promises. It will pass near-white text that halates.

**Fix.**

- Add `scale` to `Canvas.text`. Scores use the font at 2x, 10x14 with 2 px strokes, which reads to about 10 m and fits five digits in 64 px.
- `jump` and `scream` show a bar first and the number second.
- Icons get 2 px strokes and a distinct colour per game.
- Text uses bytes of about 140 in one hue.
- `distance` takes metres and models a 1.5 arcmin blur plus a luminance-weighted halation Gaussian of about 1.5 px.

**Test.** Glyphs of menu titles rendered at 5 m match the correct atlas glyph by a correlation margin of 0.1.

### 8. The tick budget is a Mac number (Task 20)

8 ms on the M1 is about 60 ms on a Pi 4, which misses 30 Hz. The modes are not the problem, since all 12 prototypes measured 0.02 to 0.26 ms. Set `BUDGET_MS = 3.0` and add a `pi_perf` marker with a 12 ms budget.

## Minor

9. **Title scroll judders.** At 20 px/s it holds alternately 1 and 2 ticks. Use 15 or 30 px/s.
10. **Dark colours vanish.** `DIM_COLOR (40,40,60)` and the `(60,0,0)` status colour are about 1.7% light with card gamma. Strike through unavailable icons instead.
11. **The director should filter modes by `needs`.** Favour audio and no-input modes when the camera is down, and skip audio modes when the mic is down.
12. **Audio visuals need an envelope.** Add `level_smooth` to `Audio` with a 50 ms attack and 300 ms release, and drive visuals from it.
13. **Contact sheets hide flicker.** At `--every 10` they sample at 3 Hz. Add `arcade_shot --flash-report` to print worst flicker area and mean APL.

## Attract catalog

Each mode is one file in `arcade/attract/modes/`. It implements `attend(focus)` and reports `lit_fraction`, `apl` and `focus` in `debug_state`. Its test asserts state first, then flicker of 0.10 or less and APL under the cap, at both sizes. Costs are measured on the M1, with the Pi estimate after.

1. **Watcher.** A large eye, 56 px on 64x64 or two 28 px eyes on 128x32. It tracks the nearest body, then the motion centroid, then glances idly. It blinks every 4 to 8 s, and the pupil dilates as a body nears. Passers-by see the wall looking at them. Cost 0.09 to 0.16 ms, about 1.3 ms on the Pi. Effort S. Test: the pupil follows `walk(0.1,0.9)`.
2. **Echo.** Motion decays into an age-coloured afterimage, measured at an APL of 0.07. Motion only. Cost 0.05 ms, about 0.4 ms. Effort S. Test: the frame is black 3 s after motion stops.
3. **Rain, reworked.** Streaks with 3 to 4 px tails fall at 10 to 20 px/s and split around motion. Motion only. Cost 0.06 ms, about 0.5 ms. Effort S. Test: no drop head sits inside a motion block.
4. **Embers.** A low coal bed. Flames rise where people move, scaled by `level_smooth` and `energy`, with the palette capped at amber. Motion and audio. Cost 0.08 ms, about 0.6 ms. Effort S. Test: heat above a motion column is at least 2x elsewhere.
5. **Fireflies.** About 48 points phase-sync a 0.5 Hz blink with a Kuramoto model. People scatter them, and beats nudge the phase, capped at 2 Hz. Motion, bodies and audio. Cost 0.06 ms, about 0.5 ms, or 2.1 ms with flocking. Effort M. Test: the order parameter is above 0.8 when idle and below 0.5 after a walk.
6. **Ripple pond.** A wave equation where onsets drop pebbles and walkers leave wakes. Use 2 px bands with damping of 0.97 or less. Audio and motion. Cost 0.08 ms, about 0.6 ms. Effort S. Test: a clap makes a ring whose radius grows.
7. **Heartline.** A mirrored `level_smooth` trace scrolling at 10 px/s. Shouts spike it, which invites `scream`. Audio. Cost 0.03 ms, about 0.3 ms. Effort S. Test: two claps make two peaks.
8. **Warp.** 150 stars with 2 px streaks, sped up by audio when a mic exists. No input, audio optional. Cost 0.02 ms, about 0.2 ms. Effort S. Test: speed rises under `loud`.
9. **Contours.** 2 px isolines of warped sines on black, which is plasma without the glare. No input. Cost 0.10 ms, about 0.8 ms. Effort S. Test: lit fraction stays between 0.05 and 0.2.
10. **Aurora.** Swaying green and violet curtains at an APL of about 0.02, meant for after 02:00. No input. Cost 0.06 ms, about 0.5 ms. Effort S. Test: APL is below 0.03 at `energy=0.3`.
11. **Life drift.** Life at 4 Hz with cells fading over 4 ticks, seeded by motion. Motion only. Cost 0.06 ms, about 0.5 ms. Effort S. Test: flicker stays at 0.10 or less, which 8 Hz Life fails.
12. **Snowfall on you.** Flakes settle on a 2 px keypoint skeleton, piling on shoulders and falling when you move. Bodies. Not prototyped; estimate 0.3 ms, about 2.5 ms. Effort M. Test: flakes sit above the shoulders after 5 s of `stand`.

Coverage: five modes use audio (4 to 8), four use motion only (2, 3, 4, 11), and three need nothing (8, 9, 10).

## Attract director

`arcade/attract/director.py` replaces the runner's idle logic and becomes its lobby, so the runner has only LOBBY and GAME.

**Tiers, with hysteresis.**

- **EMPTY:** nothing for 3 s.
- **PASSING:** motion on 2% or more of cells after rejection, a body, or a qualifying blob.
- **NEAR:** a body with box height of 0.35 or more stable for 0.5 s, or a play-region blob moving for 1 s. Tune both live.
- **ENGAGED:** a raised wrist on a NEAR body for 0.4 s.

**Sub-states.**

- **ATTRACT** runs at EMPTY and PASSING. The mode uses the night `energy` and gets `attend(focus)` at PASSING.
- **INVITE** runs at NEAR. After 1.5 s, a 16 px hand-raise pictogram with 2 px strokes breathes at 1 Hz beside the person.
- **MENU** runs at ENGAGED. Tiles fade in over 0.5 s over the running mode, which drops to 30% energy. Tiles get a black keyline, and the hand becomes the mode's focus. Dwell starts after the fade, so the summoning raise never selects.
- **Return.** After 15 s at PASSING or below, tiles fade out over 1 s.

**Scheduling.** Modes declare `needs`, `calm` from 0 to 1, and `min_s` and `max_s`, defaulting to 40 and 150. The next mode is a weighted random choice:

- weight 0 if its needs are unavailable;
- times 0.2 if it is among the last three;
- times `1 - abs(calm - night_calm(hour))`;
- times 2 for audio modes while `bpm` is locked, and for reactive modes after recent passers-by.

Duration is uniform in the declared range. It extends while PASSING interaction continues and ends early on `settled()`.

**Transitions.** A 1.5 s linear-light crossfade with both modes running, about 3 ms on the Pi, or a noise dissolve over a frozen snapshot. Never a cut.

**Handback.** On `done()` or abandonment, show a 3 s big-digit score card. "NEW BEST" breathes at 1 Hz. The card dissolves to MENU at NEAR or above, else to ATTRACT. An occasional "TONIGHT'S BEST" card adds social proof.

**Energy.** Use `night_curve(hour)` times a tier boost that runs from 1.0 to 1.3, capped at 1. The APL limiter backstops it.

**`debug_state`.** `tier`, `sub`, `mode`, `mode_t`, `next_mode`, `energy`, `fade`, `focus`, `bg_blob_cells`.

**Tests.**

- No mode repeats back to back.
- No audio mode plays with `audio="none"`.
- `walk`, `stand`, `raise_hand` passes ATTRACT, INVITE and MENU in order.
- No frame-to-frame step in mean linear luminance exceeds 0.1 across a sub-state change.

## Checked and found OK

- **Mode compute:** 12 vectorised prototypes run 0.02 to 0.26 ms per frame at both sizes.
- **Flash limiter:** it costs 0.2 ms and passes legitimate motion untouched.
- **Flash area:** beyond 5 m the whole wall is under the threshold, so the limiter protects players.
- **Canvas clipping:** particles can safely leave the edge.
- **Clock and rng:** the dt clamp and injected rng suit physics modes, once seeds vary per launch.
- **Audio gain:** the slow running maximum gives usable range beside a sound camp.
- **Exit gesture:** it is harmless in attract.
