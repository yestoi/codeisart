# Wall arcade review: festival operations, human factors, safety

Lens: the arcade surviving a regional-burn night with drunk strangers, kids, costumes, dust, a sound camp next door, and one owner asleep in a tent. Read: arcade spec (all); plan header, Global Constraints, Tasks 8, 9, 16 (thread base), 18, 19, Done-when; sibling spec and its prior review (not re-raised).

## Blockers

### B1. A player who walks away leaves the wall stuck; attract almost never runs (spec 7.2, 8, 10; plan Tasks 8, 18)

- **Idle is only checked from the menu.** In `Runner.tick` the idle branch is the `elif` of `if self.current is not self.menu`. Inside a game only `done()` or the exit gesture leaves, and `paint`, `puppet`, `life`, `ambient`, `beat`, `scream` never finish. Someone plays paint and walks off; the wall shows black until reboot.
- **Attract is not wired.** `arcade/main.py` constructs `Runner(...)` without `attract=`, so idle attract never fires on the real CLI.
- **Presence is any body or blob anywhere in frame.** Under the floodlight, white shirts and faces become blobs, and `find_blobs` thresholds at a percentile, so a lantern, glowstick or distant fire is always "present"; passers-by at 8 m reset the 60 s timer. The attract, the only recruiter, rarely shows.

**Fix (spec 7.2, new "session end" rule):**
1. `presence` = a body whose box height exceeds a configured fraction of the frame (closer than about 4 m) with its centre inside a configured camera-space `zone` rectangle calibrated to a ground mat. Blobs count only inside the zone and only for games that need blobs.
2. Idle applies everywhere: no presence for `leave_seconds` (8) in a game ends the session (3 s score card, then attract). `idle_seconds` in the menu drops to 20.
3. Engagement timeout: each game reports `active` in `debug_state()`; 30 s inactive shows "still playing? raise a hand" for 5 s, then ends.
4. `max_session_seconds` (180) applies while another body waits in the zone.
5. `main.py` passes the attract; a test runs `main` for 60 simulated idle seconds and asserts attract is current.

### B2. Standing still in front of the menu launches a random game (spec 7.3; plan Task 9 `cursor_of`)

With no raised wrist the cursor falls back to body centre, and `update` dwells wherever the cursor is. A person standing centred and talking sits near (0.5, 0.5): pixel (32, 32) on 64x64 is inside tile 7, and (64, 16) on 128x32 is inside tile 9. One second later that game launches unasked and, per B1, never ends. A static glowstick or headlamp does the same through the blob fallback.

**Fix:** only a hand cursor can dwell-select. Body-centre and blob fallbacks draw a dim ghost cursor that never fills a ring. Test: `stand()` held 10 s in the menu never selects, at both sizes. Also fix the mismatch: spec says "largest blob", code takes `blobs[0]`, the brightest.

### B3. Photosensitive seizure risk, starting with the crash screen (spec 7.2 crash guard, 8, 10)

- **The glitch frame is a 30 Hz strobe.** `_draw_glitch` seeds noise with `self._glitch`, which decrements each tick, so for a second every frame is a fresh random 15% of pixels at full white. An agent-written game that throws strobes whoever is watching.
- **`beat` falls back to onsets.** Beside a sound camp, hi-hats and snares give 4 to 16 onsets per second, inside the 3 to 30 Hz hazard band.
- **Motion games follow strobes.** An art-car strobe at 8 to 12 Hz lighting the zone makes the frame-difference `motion` grid flip all-true on alternate frames; `ambient` fire and `life` then flash the whole wall in sync. Auto-exposure jumps from headlights do the same.
- **Area:** at 2 m a 10-degree field is about 35 cm across; the 64x16 cm wall exceeds the WCAG 2.3.1 area threshold (25% of that field) on its own.

**Fix (new spec 7.6 "flash governor", runner-level, after `draw`, not bypassable):**
1. Per frame, compute mean linearized luminance (apply `gamma`, Rec. 709 weights) for the wall and each quadrant, and the saturated-red area (pixels with R/(R+G+B) >= 0.8).
2. Over a sliding 1 s window, a flash is a pair of opposing changes of at least 10% of full-scale luminance, or a saturated-red area change above 25% of the wall.
3. If this frame would be the fourth flash in any window, blend it toward the last pushed frame until the change is under 10%. Log interventions once per minute with the game name; count them in `state()`.
4. Replace the glitch with one static dim red icon fading over 0.5 s.
5. `beat` pulses luminance only on a locked tempo at or below 180 bpm; on onsets it changes hue or shape at constant luminance.
6. Tests: every game's soak with `claps` at 12 Hz, `tempo(180)` and a motion grid alternating every tick must cause zero interventions; separately, the governor holds a raw 15 Hz white strobe to 3 flashes per second.
7. A flashing-light warning on the approach sign (most art forms ask for it).

### B4. The walk-up flow cannot meet the ten-second goal (spec 1, 7.3)

| Step | Current design | Realistic, drunk stranger at night |
|---|---|---|
| Notice it is interactive | Ambient rain on a 64x16 cm panel reads as a screensaver | 5 to 30 s, often never |
| Menu appears | On first body | under 1 s |
| Understand the menu | 11 icons of 4 cm, a scrolling title, no instruction | 3 to 10 s |
| Discover "wrist above nose" | Nothing says so; B2 launches a game first | usually never |
| Aim and dwell on a 10x10 tile | Raw frame coordinates with pose jitter | 3 to 8 s |
| Understand the game | No instructions (frogger's hop is invisible) | 5 to 20 s |

**Half the menu is unreachable by a raised hand.** `raised_wrist` exists only above the nose, and `cursor_of` maps raw frame y to wall y. For any framing that shows a standing adult the nose is at y 0.1 to 0.3, so the raised-hand cursor lives in the top 10 to 30% of the wall. On 128x32 the second tile row spans y 0.38 to 0.68 (tiles 6 to 10); on 64x64 rows three and four span 0.44 to 0.75. Those games are reachable only through the accidental fallback of B2.

**Fix (spec 7.3):** map the cursor from a body-relative reach box: either wrist (the one further from its hip) relative to the shoulder midpoint, normalized by shoulder width, a box about 1.5 shoulder widths each side and from hip to a forearm above the head mapping to the whole wall. This is the Kinect "physical interaction zone"; it works at any distance, seated, and for kids. Flow in section 6.

## Serious

### S1. The exit gesture fires on celebration and game poses (spec 7.2, 8)

Both wrists up for 1.5 s is what people do after a frogger crossing, a pong point or a big jump, and what a cheering group does, and it is read from "the most confident body", often a spectator. `holewall` will likely hold a hands-up target through a 3 s countdown and exit itself. It shows no progress and excludes one-armed players. **Fix:** walking away (B1) is the exit. Keep a deliberate exit of both hands for 3 s with a runner-drawn closing ring, suppressed for games whose `GameInfo` sets `uses_hands_up` (holewall, jump).

### S2. No player lock, so control jumps between people (spec 5 BodyTracker, 7.2, 8)

Every rule reads "most confident body", which favours the largest, closest, most frontal person: the kid running through, the friend leaning in, the face 30 cm from the lens. Frogger's frog teleports; pong assigns paddles by id order, so an early spectator at the back becomes player two. The tracker drops an id after ten unseen frames and never reuses it, so a third-of-a-second occlusion loses the player. **Fix (spec 7.2):** the runner owns `sensed.player` and `player2`: the body whose hand launched the game, re-acquired as the body nearest the last position within 2 s before the seat empties. Pong seats by zone half, not id. Games read `player`, never `bodies[0]`. Mark each player's colour in a corner so everyone sees who is in control.

### S3. No visible turn-taking (spec 7.2)

A second person cannot tell when it is their turn. **Fix:** the session-end card reads "NEXT: RAISE A HAND"; the next zone body to raise a hand gets the seat. During a session a corner pip per waiting body shows the queue and arms the session cap. Pong and puppet invite the waiting person in as player two.

### S4. Camera consent: true today, but unstated and unenforced (spec 6, 10; plan Tasks 15, 18)

Scenario files hold only Sensed records and audio is features only, so nothing identifying is written today. But no rule keeps it so, agents reach for `cv2.imwrite` when debugging, and `arcade record` captures anyone in view with no signal. The 64x64 motion bitmap at 30 Hz is a silhouette video some people will object to.

**Fix, spec (new 6.5 "Privacy"):**
1. "No camera frame or audio sample leaves its source thread. Nothing is written, logged or sent except Sensed records, scores and the status file." Enforced by a test that fails if `arcade/` references `imwrite`, `imencode`, `np.save`, `Image.save`, `VideoWriter` or `wave`, and one that a scenario line holds no field outside the Sensed schema.
2. No preview or stream server is ever started.
3. `arcade record` requires `--i-have-consent` and, on the `ddp` backend, `allow_record = true` (default false). The wall shows 3-2-1, then a red REC and seconds counter throughout. Event recordings drop `motion` unless `--with-motion`.

**Fix, physical:** signs at the approach and at the camera: "This camera sees you as 17 dots. No photos, video or sound recorded, nothing saved. Stand outside the square and it ignores you." Mark the zone so opting out is a place, and aim the camera at the zone, not the walkway. Showing each player their own stick figure is the strongest disclosure. Declare the camera on the art and placement form. A sign alone is not enough: the first complaint will be "you recorded us", and the answer must be verifiable.

### S5. Brightness 0.4 is far too bright at night (spec 4.3, 10)

Outdoor P5 modules are rated around 4,000 to 5,500 cd/m², so 0.4 is about 2,000 cd/m² of white at 1 to 3 m for dark-adapted eyes, where night billboard guidance is near 300. Players leave with night vision gone and cannot see the ground. **Fix:** keep `brightness` as the ceiling and add `night_brightness` (0.08) from dusk to dawn, driven by the IMX500's lux metadata with a clock fallback; set the value in prototype week with a lux meter at 2 m and the `distance` preview.

### S6. Floodlight, camera mount and play-area placement (spec 2, new "Placement" section)

- **Floodlight:** it faces the players, so it shines in their eyes. Mount it at least 2.5 m up, aimed 45 degrees or more down, visored so the lamp face is hidden from eye height in the zone; warm, diffuse, dimmed to the lowest level where detection holds (measure detection rate against lux). Check whether the AI Camera has an IR-cut filter before considering IR.
- **No pole in the play area.** Poles get leaned on, climbed and hit by flailing arms. Mount the camera on the wall frame above the panels, 2.2 m or higher, tilted down; this also ends the face-in-lens case.
- **Cables** never cross the zone or approach. Keep Code is Art guy lines and station cables out of it.
- **Zone:** flat, soft, 2 by 2 m, starting 1.5 m from the wall, with 1 m clear margin for jumping and arm swings. Mark it with a taped flat mat or a lit circle, not rope light. No stakes nearby; cap any that exist. Keep bike paths out of frame. Do not feature `jump` on uneven ground.
- **Mic** at chest height by the zone, facing the player, away from sound camp and generator, in a furry windscreen, or wind gusts will flap `flappy` on their own.

### S7. Nothing restarts it, nobody can see its state, sources never recover (spec 10; plan Tasks 16, 18)

- No systemd unit, watchdog or status output in the plan.
- A source that fails, or whose thread dies, stays dead until restart; a USB mic re-enumerating after a generator dip is gone for the night.
- A blocked `capture_request` leaves `latest()` returning a stale result with `available` true; a frozen raised wrist on a tile relaunches that game forever.
- `sense()` and `_push` log a traceback every tick while a source raises or FPP is down: 30 per second all night, wearing the SD card.
- With the camera down, ten of eleven games dim and the wall shows a dead grid; the status glyph is one dark-red pixel.
- If it shares the Code is Art Pi, it competes with a daemon already judged marginal and can take the main piece down.

**Fix (spec 10 additions):**
1. systemd `Restart=always`, `StartLimitIntervalSec=0`, `WatchdogSec=10`, pinged only while ticks advance and a push succeeded in the last 5 s. Prefer a separate Pi; otherwise `Nice=5` and `CPUQuota`.
2. Source results carry timestamps; older than 1 s means empty and unavailable. Unavailable sources retry every 30 s; after 5 minutes of camera failure the process exits non-zero for a fresh start.
3. Repeated errors are logged once per minute with a count.
4. Camera down: an audio-reactive ambient mode with a "camera resting" icon. Both down: slow dim ambient.
5. Every 10 s read SoC temperature and `vcgencmd get_throttled`; above 75 °C drop to 15 fps, above 82 °C a static dim frame; log undervoltage, which on generator power predicts SD corruption.
6. Write `/run/arcade/status.json` every 10 s (game, fps, temperature, throttling, sources, crashes, hidden games, governor count, detections per minute, mean keypoint confidence). Serve it read-only on the site LAN or a Pi access point, with a password-protected restart button, so the owner can check from camp by phone. A 1 Hz heartbeat pixel lets a volunteer see it is alive.
7. Read-only overlay root, journald `Storage=volatile`, `data_dir` on a separate writable partition, scores written with fsync then rename.
8. A labelled weatherproof button on GPIO3 with `dtoverlay=gpio-shutdown` (press to halt, press to boot) and a laminated card in the lid: "Dark wall: check generator; press, wait for dark, press again, wait 90 s; still dark, find Trey at camp X."
9. A daily dusk restart timer clears hidden games and starts the night's scores.

**Morning checklist (append to spec 10):** read status for crashes, hidden games, throttling and governor hits; wipe the camera window; check the housing for dew; sweep the zone for glass and debris; check floodlight aim, cables, ramps and sign; walk-up test (enter, hand up, play, walk away, attract returns); cover the wall and box for the day.

## Minor

- **M1.** Best of the night never resets (spec 7.5). Reset at 16:00; keep last night's best for the attract.
- **M2.** Every launch uses `random.Random(self.seed)`, so every frogger run is identical. Either seed per launch or choose a "course of the night" seed for fair scores, and say which.
- **M3.** Frame the camera so a 1 m child is fully in view at the zone's near edge. Nothing essential should require both hands or jumping.
- **M4.** Dust and dew: camera behind a downward-angled acrylic window under a hood, silica gel in the housing, mean confidence in status so dust loss shows before failure.
- **M5.** Costumes and mirror suits break pose; a mirror suit under the flood becomes eight jittering blobs. After B1 and B2 these degrade to "not detected"; show blob-only people as paint trails in the attract so they still get a response.
- **M6.** Run dusk to dawn only; a black panel and sealed Pi box in sun overheat.
- **M7.** The Mac caps MediaPipe at two poses while the IMX500 returns many. Add a six-person actor scene to every soak.

## 6. The walk-up flow I would ship

1. **Attract is a mirror.** Entering the zone shows your own stick figure within half a second over the ambient background; between visitors a demo figure raises its hand, alternating with "TONIGHT'S BEST".
2. **One wordless prompt:** a large animated hand-up pictogram beside the figure.
3. **Hand up starts a game at once, no menu.** The featured game rotates every 15 minutes among those that need no teaching (paint, scream, pong, puppet). Each opens with a 2 s pictogram of its single action.
4. **The menu is opt-in:** from the score card, a three-tile carousel with 16x16 icons, body-relative cursor, 1.5 s dwell.
5. **End by leaving:** game over or 8 s absent shows the score and "NEXT: RAISE A HAND" for 3 s, then the mirror.

Expected: noticed from the path because it moves with passers-by, figure in 1 s, hand up by 5 s, playing by 6 s.

## 7. The social loop

- **Best of the night in the attract**, per game with time set ("HIGHEST JUMP 41 at 1:12"). A new best triggers a slow, non-flashing colour wave and "NEW BEST TONIGHT". With no names, the surrounding crowd is the audience, which is what drags friends over.
- **A crowd game:** "hands up together" fills a bar per zone body with both hands raised; at five, something big (governor-compliant) happens. It turns the cheering group from an exit-gesture bug into the best moment of the night. Crowd `scream` ("LOUDEST CROWD TONIGHT") works the same way.
- **Two-player invitation:** pong and puppet show "2P: STAND ON THE RIGHT" whenever a second body is in the zone.
- **Photo moment:** friends will photograph players in front of the wall; the sign says "photos of people by consent".
- **Return reasons:** a game unlocked only after midnight, and a featured-game schedule on the sign.

## Checked and found OK

- The runner never exits on a game error, sources never block the tick, and repeat crashers are hidden.
- Brightness is a hard ceiling via `set_brightness` that no game can raise (value wrong at night, S5; mechanism right).
- No raw frame or audio sample is persisted anywhere in the plan today.
- No sound output, so no noise or quiet-hours problem.
- The dwell ring shows progress, and pass-through does not launch.
- `dt` is clamped; mirroring is on by default and applied once.
- Missing hardware degrades rather than exits (S7 covers the missing recovery).
