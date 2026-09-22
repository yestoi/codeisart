# Code is Art, A.I. is not — Design Spec

Date: 2026-09-22, revision 2 (folds in the adversarial review of the same day)
Event install date: 2026-11-11
Status: draft for review
Review record: `docs/superpowers/reviews/2026-09-22-adversarial-review.md`

## 0. Decisions taken in this revision

Each of these follows a review finding. All are reversible; say the word and it goes back.

- Wall size is decided after the four-panel prototype, not now. Both tiers are specified (3.1).
- Power is a 2 kW inverter generator with a mid-night refuel (3.3). Event mains, if offered, replaces it.
- The rpi-rgb-led-matrix backup drive path is dropped (3.2). Colorlight is the only wall driver.
- DDP through Falcon Player is the primary wall path; the raw Colorlight backend stays as a
  verified-on-hardware secondary.
- Row 24 of the wall is a permanent attribution and status strip; entries run in 80x23 (4.4).
- The sandbox keeps the original "separate user, no network" requirement via `unshare` (4.3).
- Entries build with `-Wall`, never `-w` (4.3).
- Crowd mode shortens entries when the queue is non-empty (4.5).
- Portrait lightboxes remain the goal, with printed signs as the documented fallback (3.5).
- Audio stays, with volume and quiet-hours controls (3.6).
- Plaques carry the year. A statement sign discloses that the wall software was built with an
  AI assistant; the code on the portraits was not (3.5).

## 1. Purpose

An interactive outdoor art installation for a regional burn. Five portraits display International
Obfuscated C Code Contest (IOCCC) entries as visual art, each with a plaque reading
"Created by <author>, <year>, Not A.I." Each portrait has a button. Pressing it plays that entry on
one large shared display: the source scrolls past, the code is compiled live, and the program runs.

The shared display is a DIY LED matrix wall built from outdoor sign modules, rendered as a real
monochrome terminal. The look is deliberately old school: glowing dot-matrix text on black.

### Success criteria

- A stranger presses a button at night and within 2 seconds sees that entry's source on the wall,
  followed by a real gcc compile with its warnings and the program running.
- The author's name and "Not A.I." are visible on the wall for the whole time their entry plays.
- The wall reads as text from 15 to 40 feet and is recognizable as a live terminal from 100 feet.
  (Character-level legibility at 100 feet was a false claim in revision 1.)
- A second press on any button, in any state, gets visible and audible acknowledgement.
- The piece survives a night of rain and a week of dust with no intervention.
- Nothing ever leaves the wall blank or frozen. Every failure path returns to an attract loop,
  including failures at boot.

### Non-goals for the MVP

- Game stepping controls or other input beyond the five buttons.
- Daytime visibility beyond the printed portraits themselves.
- Graphics beyond what a VT100-class terminal can show.

## 2. Constraints and decisions already made

- No projection. No purchased or rented large screens.
- Display is a HUB75 RGB LED wall of outdoor (IP65 face) modules run in one phosphor color.
- Modules are the Wired Watts outdoor P5 64x32 (SMD2525, 1/8 scan, M4 holes, rear gasket, ships
  from Alpharetta GA in 24 h). Four are on order for the prototype with one supply, one
  distribution board, and a Colorlight 5A-75E.
- Buttons and portraits are wired, not wireless.
- Everything the show does is real: real pty, real gcc, real execution. Recordings replay only
  after a failure.
- Target computer is a Raspberry Pi 4. Pi 5 is excluded (no longer matters with the matrix path
  dropped, kept for clarity).

## 3. Hardware

### 3.1 LED wall, two tiers

| | Full | Reduced |
|---|---|---|
| Grid | 8 wide x 6 tall, 48 modules + 6 spares | 8 wide x 4 tall, 32 modules + 4 spares |
| Resolution | 512 x 192 | 512 x 128 |
| Terminal | 80 x 23 plus status row | 80 x 15 plus status row |
| Active area | 2.56 m x 0.96 m | 2.56 m x 0.64 m |
| Supplies and distribution boards | 6 | 4 |
| Colorlight chains | 12 chains of 4 | 8 chains of 4 |
| Estimated all-up weight | 75 to 85 kg | 50 to 60 kg |

Decision criteria after the prototype (section 6, week 2):
1. Legibility of a 2x2 block at 30, 50 and 80 feet at night.
2. Measured draw per module at black, dimmed text and full white, times 32 and 48, against the
   generator and fuel plan.
3. Whether the five entries survive at 15 rows in the SDL preview (`rows = 15` in config).
4. Whether Wired Watts can supply 54 from one batch, or only 36. Mixed batches go in whole rows.
5. Hours available in weeks 3 and 4 (section 6).

Character size is 30 x 40 mm on either tier.

### 3.2 Drive chain

- Two Colorlight 5A-75E receiving cards, one installed and one spare pre-configured with the same
  settings. One card carries the whole wall (98k of 262k pixel capacity, 12 of 16 ports).
- Chains of four modules per port. Chains of eight sit at the vendor's per-port limit for 1/8 scan;
  chains of four double refresh and grey depth and halve the damage from a chain fault.
- Card configuration: LEDVision 8.8 on a Windows PC connected directly to the card over gigabit
  Ethernet, following the Wired Watts guide for these panels ("14 full color eight scan", save to
  receivers). No sender card. Record the final settings in `deploy/README.md`.
- Primary path: Raspberry Pi 4 running Falcon Player with the ColorLight 5A-75 channel output on
  a dedicated USB gigabit Ethernet adapter, fed by the show daemon over DDP on the same Pi.
- Secondary path: the daemon's raw Colorlight backend on the same adapter, used only once its
  packet constants are verified against the card on the prototype. Packets are prebuilt per row
  so the Pi can hold frame rate.
- Dropped: the rpi-rgb-led-matrix backup. Three parallel chains consume the GPIO the buttons and
  lights need, its snake mapping requires alternate rows mounted upside down (louvers up), and it
  may not support the modules' driver IC at all. A Panel Pi Hat is an optional bench toy only.
- Brightness is set on the card (or via Falcon Player's output brightness), never by scaling
  pixels in software, so low night levels keep full grey depth.

### 3.3 Power

Provisional figures from the Wired Watts listing (0.18 A idle, 6.19 A full white per module at
5 V). The prototype replaces them with measurements.

| Load, Full tier | Watts |
|---|---|
| 48 modules idle (logic only) | ~45 |
| Wall, night, dimmed green text | 100 to 150 DC |
| Wall, worst case at the 40% cap | ~600 DC |
| Wall, full white at 100% (must never happen) | ~1,500 DC |
| 12 V circuit: 5 lightboxes, button LEDs, amp | 60 to 100 |
| Pi, Colorlight, USB Ethernet | ~10 |
| Realistic night AC draw including supply losses | 200 to 300 |

Reduced tier is roughly two thirds of each line.

**Source: 2 kW inverter generator.** Honda EU2200i class or a Predator or WEN 2000 class unit.
Placed 30 to 50 feet behind the tree line, downwind of the audience, never enclosed, on a 12 AWG
outdoor cord. A plywood baffle open on two sides for noise. One 13-hour night is a little over one
tank, so plan one refuel around 2 a.m. or accept the wall going dark near dawn. Fuel 1.5 gal per
night in approved cans on a spill mat 20 feet from the piece, extinguisher at the generator. Check
the event's generator and quiet-hours rules now, and ask placement for art power, which is
cheaper than all of this. Optional: a 500 Wh to 1 kWh pass-through battery station between the
generator and the piece, so refuels and inrush never reach the Pi.

**5 V distribution.** Mean Well LRS-350-5 (5 V, 60 A) indoor supplies mounted inside the cabinet
on standoffs, one per row. Each supply feeds one Wired Watts Panel Power Distribution board (8
outputs, four 7 A fuses, 30 A total) over 10 AWG, and each board feeds its row through the
dual-head 14/18 AWG panel power wires. That gives a 7 A fuse per module pair, which is what
protects the 20 AWG pigtails. Supply outputs trimmed to 5.1 to 5.2 V to cover drop. One 6 AWG
star bus bonds every supply 0 V and the Colorlight card ground so ribbon grounds never carry
return current. The 40% software cap keeps a row under the board's 30 A rating; full white at
100% would be 50 A per row and is not allowed.

**AC side.** Inline GFCI at the generator. A labelled AC disconnect on the cabinet the event safety
team can throw. The steel frame bonded to protective earth. Supplies powered up in two stages
(two switched outlet strips) to limit inrush. Strain relief on every ribbon and power lead.

### 3.4 Cabinet and structure

- **Skin.** Modules seal by compressing their rear gasket against a flat surface and are screwed
  from behind on M4 at exact 320 x 160 mm pitch. The front of the cabinet is therefore a flat
  1.5 mm aluminium or punched steel skin, or a welded steel tube grid at module pitch. Not angle
  iron. Pitch error over 1 mm shows as a seam.
- **Enclosure.** A rain screen, not a sealed box. Hooded, screened louvers top and bottom so the
  supplies breathe and cold-night condensation on module backs can dry. Drip roof 30 cm deep,
  sloped to the rear. Exterior plywood back, painted and sealed, with a weatherproof access hatch
  and a wired keyboard port for debugging in the dark.
- **Structure.** Free standing on braced A-frame legs with guy lines to screw anchors and ballast.
  The trees are backdrop only and carry nothing. Design load: 650 N on the face at 40 mph, 1.5 kN
  at 60 mph, plus 75 to 85 kg dead load. Someone checks the overturning moment before build. A
  drop-in-wind plan (two people, five minutes) is written down. A low rope or bench 1 m in front
  keeps leaners and climbers off.
- **Electronics box.** The Pi, both cards (one installed), USB Ethernet, button interface and amp
  live in a separate IP65 enclosure at ground level.
- **Weather test.** Hose upward into the bottom vents with the wall running hot, for an hour, not
  a 15-minute front spray.

### 3.5 Portrait stations

Five stations plus a sixth statement sign.

- **Portrait.** Goal: slim outdoor LED lightbox frame holding a backlit print of the code and the
  plaque, switched from the daemon so the playing portrait glows from 60 feet. Fallback (descope
  step 3): printed aluminium or coroplast sign with a vinyl plaque and only the button ring lit.
  Frames are ordered first; prints are designed to the frame's live area and ordered once the
  frames are in hand.
- **Plaque text.** `Created by <author>, <year>, Not A.I.` The year is the proof.
- **Button.** 22 mm stainless industrial pushbutton with a 12 V LED ring, IP67, mounted at 36
  inches for wheelchair reach. Most "IP65 arcade buttons" are not.
- **Stakes.** Two stakes or a base plate per station; a single stake under a lightbox is a sail.
- **Cabling.** One run of 18 AWG UF-rated 4-conductor irrigation wire per station (12 V pair,
  contact pair) with IP67 SP13 or M12 connectors at both ends. Runs are trenched, or routed
  behind the portrait line and entered from the far side, and never cross the viewing area. Any
  surface run gets a cable ramp.
- **Inputs.** Optoisolated contact inputs with pull-ups and hardware debounce on the Pi. Descope
  step 4 replaces this with direct GPIO and software debounce.
- **Statement sign.** A sixth lightbox or sign: 150 words on what IOCCC is, what the buttons do,
  a QR to ioccc.org, a line that the wall software was built with an AI assistant while every
  entry on the portraits was written by a person before such tools existed, and a "if dark, find
  camp <name>" line. The layout in `vision.png`, portraits between viewer and wall, is kept so the
  plaques and wall are in one glance; a photo spot is marked where all five and the wall frame up.

### 3.6 Audio

A small 12 V amp and one outdoor horn speaker under the wall, aimed at the wall face, not the
audience. Cues for keypress, compile, run and error; the error cue is a soft tone, not a buzz.
Config has `volume` and `quiet_hours` (cues muted, wall unchanged). Descope step 2 removes audio.

## 4. Software

### 4.1 Architecture

One Python daemon, `show`, on the Pi, under systemd with the hardware watchdog. States:
ATTRACT, PLAYING(entry), and a queue. The wall is a real terminal: a pseudo-terminal sized
80x23 with a pyte screen; each frame the renderer rasterizes the cell grid with a 6x8 bitmap
font into the framebuffer and a display backend pushes it.

### 4.2 Components

| Component | Responsibility |
|---|---|
| `input` | Optoisolated buttons on GPIO, thread-safe press queue |
| `queue` | Ordered pending entries, dedupe, per-station position |
| `state` | Transitions, crowd mode, feedback on every press |
| `pipeline` | One entry: source, compile, run, fallback, dwell |
| `terminal` | pty plus pyte, bounded and time-budgeted pump, geometry restore |
| `renderer` | Cells to pixels, permanent row 24 strip, dirty-only rendering |
| `display` | `push(frame)` behind one interface: SDL preview, DDP, raw Colorlight, fake |
| `lights` | Portrait lightboxes and button rings: off, on, bright, pulse, flash |
| `audio` | Cue playback with volume and quiet hours |
| `entries` | Load and validate entry directories; rescan while running |

### 4.3 Entry pipeline

Each entry directory holds `entry.toml`, the unmodified source, and `fallback.cast`.

1. Light the portrait, cue keypress.
2. Typewriter the source at `typewriter_cps`.
3. Run the build command in the pty with `-Wall`. Real warnings are the point. BUILD shows for at
   least 1.5 s even when gcc is instant.
4. Run the program in the pty inside the sandbox: `unshare -rn` (unprivileged user namespace,
   no network), rlimits on CPU, core, file size and memory, wall-clock timeout, kill of the whole
   process group. The systemd unit uses `ProtectSystem=strict` with the entries directory in
   `ReadWritePaths`.
5. Hold the final frame for the dwell, then next queued entry or ATTRACT.

Failure means build exit non-zero, build timeout, or the program dying by signal (return code
below zero only; a non-zero exit is normal for IOCCC entries). A run timeout is a normal end. On
failure: show the reason, hold `error_hold`, replay `fallback.cast` if present. Capture writes
`fallback.cast` only on a clean run.

### 4.4 The wall layout

Row 24 is a permanent strip, reverse video, never overwritten by programs:
`NOW: <title> by <author>, Not A.I. | NEXT: <title> (<n> queued)` during play, and
`PRESS A BUTTON ON ANY PORTRAIT` in attract. Entries therefore run in 80x23 on the Full tier and
80x15 on the Reduced tier. This trades the "true 80x24" of revision 1 for attribution that is on
the wall the whole time an entry plays. Any entry that truly needs row 24 can set
`full_screen = true` in `entry.toml` to move the strip to a 2-second flash every 10 seconds.

Look: one phosphor color (P1 green or P3 amber, config), a classic 5x7 dot-matrix sign font in
6x8 cells (Adafruit glcdfont, BSD), blinking block cursor, paced output. Glow is off; it is too
slow on the Pi and banding makes it worse.

### 4.5 Interaction rules

- **Every press is acknowledged.** Cue plus a 300 ms flash of that button, and the strip shows
  `PLAYING` or `QUEUED #3` for 2 s, even when nothing changes.
- **Crowd mode.** With the queue non-empty: run capped at 10 s, no dwell, source scroll at 4x.
  With the queue empty: entries that animate forever get 40 s.
- **Attract.** Scrolls the sources with the banner re-inserted every 40 lines, and auto-plays a
  random entry every 5 idle minutes so the interaction demonstrates itself.
- **Lights.** Idle: all lightboxes on, rings pulsing slowly. Playing: that station bright, queued
  stations pulsing fast. After 10 s of display push failures: all lights off, so a dark wall does
  not invite pressing.

### 4.6 Robustness

- Startup never exits. Missing font, empty or invalid entries directory, no Ethernet carrier, or
  a GPIO library failure each log, show a static error frame if a display exists, and keep the
  loop, the watchdog and a 30-second rescan alive. `StartLimitIntervalSec=0` in the unit.
- Any exception in press handling, tick, render or push is logged and the show returns to
  attract; the process keeps running.
- Terminal pump reads at most 4 KB or 8 ms per frame. Render only when the screen is dirty or
  cursor or strip changed, otherwise re-push the cached frame. Default 20 fps.
- Process control: always kill the process group; "exited but no pty EOF within 0.5 s" counts as
  finished and triggers the kill, so backgrounded children never keep the pty open.
- Terminal reset restores geometry after an entry switches to 132 columns.
- Read-only overlay filesystem on the Pi so generator refuels never corrupt the SD card. A second
  Pi 4 with a cloned card travels with the piece.

### 4.7 Testing

- Unit tests for renderer, queue, entry loading, state transitions with a fake clock, and the
  pipeline against a hello entry, a broken build, a crashing entry, a non-zero exit, a forever
  entry, and a backgrounding entry.
- Prototype bring-up on four modules in week 2, DDP path first.
- Overnight soak in week 5 with buttons pressed by a timer. Weather test per 3.4 in week 6.

## 5. Bill of materials

Ordered (prototype): 2 x outdoor P5 2-packs, 1 x LRS-350-5, 1 x Panel Power Distribution, 30 inch
panel wires, AC cord, Colorlight 5A-75E, Raspberry Pi 4.

| Item | Full | Reduced | Est. cost |
|---|---|---|---|
| Wired Watts outdoor P5 2-packs, incl. prototype | 27 | 18 | $1,430 / $954 |
| Colorlight 5A-75E (one spare) | 2 | 2 | $90 |
| Mean Well LRS-350-5 | 6 | 4 | $177 / $118 |
| Panel Power Distribution boards | 6 | 4 | $87 / $58 |
| Mean Well LRS-350-12 | 1 | 1 | $30 |
| Panel wire, power wire spares, AC cords, 10 AWG, 6 AWG bus, lugs, fuse holders | | | $150 |
| USB gigabit Ethernet adapter, second Pi 4, SD cards, Pi supplies | | | $180 |
| Inline GFCI, AC disconnect, outlet strips, bonding hardware | | | $120 |
| Aluminium or steel skin, tube or angle frame, plywood, paint, sealant, louvers, hardware | | | $500 to $800 |
| A-frame legs, screw anchors, guy lines, ballast bags, ratchet straps | | | $200 |
| IP65 electronics enclosure, hatch hardware | | | $80 |
| Lightbox frames with bases (or signs, $150 total) | 6 | 6 | $500 to $750 |
| Backlit prints, plaques, statement sign | | | $200 |
| Industrial IP67 ring-LED buttons | 6 | 6 | $90 |
| UF irrigation wire 200 ft, SP13/M12 connectors, cable ramps | | | $200 |
| Opto input and MOSFET boards | | | $30 |
| 12 V amp, horn speaker | | | $70 |
| Tools and consumables (crimper, step bit, hole saw, silicone, fasteners) | | | $200 |
| Sales tax, freight | | | $400 |
| Truck rental, fuel | | | $250 |
| Subtotal before power | | | $4,900 to $5,700 (Full), $4,300 to $5,000 (Reduced) |
| Generator, cord, cans, spill mat, extinguisher | | | $700 to $1,500 |

## 6. Schedule to Nov 11

Realistic budget is 230 hours for the Full tier. Against 15 to 20 hours a week this only works
with a helper on cabinet and wiring weekends, or the Reduced tier, or both. The critical path is
cabinet fabrication and full-wall wiring, not delivery.

| Week | Dates | Milestone | Hours |
|---|---|---|---|
| 1 | Sep 22 to 28 | Prototype parts ordered (done). Curate the five entries and confirm they build with `-Wall` on current gcc. Confirm placement, power rules, generator rules and form deadlines with the event. Order six lightbox frames. Book helper and truck for Nov 10, 11 and teardown. Software Tasks 1 to 7. | 32 |
| 2 | Sep 29 to Oct 5 | Prototype bring-up on four modules, DDP path. Legibility walk, power measurements. Size decision; place the remaining panel order. Design prints to the frame live area. Cabinet skin drawing from the real hole pattern. Software Tasks 8 to 15. | 34 |
| 3 | Oct 6 to 12 | Cabinet skin and frame fabricated (helper weekend). Station cables and connectors. Order prints. Software Tasks 16 to 19. | 45 |
| 4 | Oct 13 to 19 | Modules tested on arrival at 0.1 brightness, mounted, chains and supplies wired (helper weekend). Wall lit end to end, chain order fixed in LEDVision. | 34 |
| 5 | Oct 20 to 26 | Buttons, lights, audio integrated. Fallback recordings. Overnight soak. Prints into frames. | 24 |
| 6 | Oct 27 to Nov 2 | Weather test. A-frame, anchors, drop-in-wind drill. Spares packed. Transport rig. | 18 |
| 7 | Nov 3 to 10 | Buffer. Night brightness set. Clone SD to the spare Pi. | 10 |
| | Nov 11 | On-site build with helper, 12 to 16 h. Teardown later, 6 h. | 22 |

### Descoping ladder, in order, if behind at the end of week 3

1. Drop the raw Colorlight backend and its verification; DDP only.
2. Drop audio.
3. Lightboxes become printed signs; only the button rings light.
4. Opto and MOSFET boards become direct GPIO and one fixed LED per station.
5. Steel skin becomes a 2x4 frame with a plywood face drilled at module pitch and a tarp roof.
6. Full tier becomes Reduced tier (if not already chosen).
7. Five stations become three.

Minimum viable piece: a lit wall of either size on the DDP path, attract loop and live compile
for at least three entries, three buttons, printed portraits with plaques, no audio, no queue.

## 7. Risks

| Risk | Mitigation |
|---|---|
| Panels beyond 36 unavailable from one batch | Reduced tier fits 36 from one order; mixed batches go in whole rows |
| Raw Colorlight constants wrong | DDP is primary; raw is verified on the prototype or dropped (ladder step 1) |
| Card needs LEDVision on Windows | Borrow a laptop for one afternoon; settings recorded in deploy notes; spare card pre-configured |
| Hours in weeks 3 and 4 | Helper weekends booked in week 1; ladder steps 5 and 6 |
| Wind | Engineered A-frame, anchors, ballast, written drop plan |
| Rain and condensation | Rain-screen venting, gasketed flat skin, upward hose test |
| Pigtail short | 7 A fuse per module pair on the distribution boards |
| Generator refuel or failure | Daemon auto-starts, read-only filesystem, optional pass-through battery |
| Entry hangs, crashes, backgrounds, floods | Sandbox, process-group kill, EOF grace, bounded pump, fallback recordings |
| Pi or SD failure | Second Pi with cloned card |
| Dead modules | Spares; every module tested on arrival |

## 8. Open questions

1. Size tier: Full or Reduced. Decided in week 2 by the criteria in 3.1.
2. Event placement confirmed, power and generator rules, which forms are due when.
3. The five entries and their build flags.
4. Who lifts and who drives on Nov 10, 11 and at teardown.
5. Lightboxes or printed signs, decided when frame lead times are known this week.
6. Phosphor color. Config only.
7. Whether event art power exists, which would remove the generator.
