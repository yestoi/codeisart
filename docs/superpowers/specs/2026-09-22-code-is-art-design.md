# Code is Art, A.I. is not — Design Spec

Date: 2026-09-22
Event install date: 2026-11-11
Status: draft for review

## 1. Purpose

An interactive outdoor art installation for a regional burn. Five portraits
display International Obfuscated C Code Contest (IOCCC) entries as visual
art, each with a plaque reading "Created by <author>, Not A.I." Each portrait
has a button. Pressing it plays that entry on one large shared display: the
source scrolls past, the code is compiled live, and the program runs.

The shared display is a DIY LED matrix wall built from outdoor sign modules,
rendered as a real 80x24 monochrome terminal. The look is deliberately old
school: glowing dot-matrix text on black.

### Success criteria

- A stranger walks up at night, presses a button, and within 2 seconds sees
  that entry's source on the wall, followed by a real gcc compile and the
  program running.
- The wall is readable from 30 feet and legible as text from 100 feet.
- The piece survives a night of rain and a week of dust with no intervention.
- Power draw at night stays near 150 W so it can run on a battery station.
- Nothing ever leaves the wall blank or frozen. Every failure path returns
  to an attract loop.

### Non-goals for the MVP

- Game stepping controls or other interactive input beyond the five buttons.
- Daytime visibility. The piece is a night piece; daytime is a bonus.
- Video or graphics output beyond what a VT100-class terminal can show.

## 2. Constraints and decisions already made

- No projection. Rejected for ambient-light washout, throw space, and dust.
- No purchased or rented large screens. Outdoor TVs and LED wall rentals
  cost as much as the entire build.
- Display is a HUB75 RGB LED wall using outdoor (IP65 face) modules, run
  in a single phosphor color for the terminal look. RGB is kept because
  the drive chain is proven; monochrome sign modules were rejected for
  their thin driver ecosystem.
- Size tier is "Big": a true 80x24 terminal at roughly 8 to 10 feet wide.
- Buttons and portraits are wired, not wireless.
- Everything the show does is real: real pty, real gcc, real execution.
  Recordings exist only as fallbacks.

## 3. Hardware

### 3.1 LED wall

| Item | Value |
|---|---|
| Module | P5 outdoor, 64x32 px, 320x160 mm, IP65 face, 1/8 scan, HUB75 |
| Grid | 8 wide x 6 tall = 48 modules, plus 6 spares |
| Resolution | 512 x 192 px |
| Active area | 2.56 m x 0.96 m (8.4 ft x 3.15 ft) |
| Terminal | 85 x 24 cells with a 6x8 font; software uses 80x24 centered |
| Character size | 30 mm x 40 mm |

P6 outdoor modules (384x192 mm, same pixel count) are preferred if a US
stock seller can deliver within one week of ordering. Same driver, same
count, wall grows to 3.07 m wide and dots become slightly more visible.
Do not wait on overseas P6 shipping; P5 is the default.

### 3.2 Drive chain

Primary: one Colorlight 5A-75E receiving card (16 HUB75 ports). Six chains
of 8 modules, one chain per row, so a chain fault takes out one row rather
than the wall. A Raspberry Pi 4 (4 GB) streams frames to the card over a
direct Ethernet cable using the reverse-engineered Colorlight L2 protocol,
either through a standalone sender or through Falcon Player's native
Colorlight output fed by DDP.

Backup: the same Pi 4 with an Active-3 HUB75 adapter running the
rpi-rgb-led-matrix library directly, three parallel chains of 16 with the
U-mapper. Lower refresh rate and 1/8 scan multiplexing may need mapper
tuning. Raspberry Pi 5 is not supported by that library and is not used.

The two-module prototype in week 2 decides which path is primary.

### 3.3 Power

- Six 5 V, 300 W, rain-rated LED supplies, one per row, mounted inside the
  cabinet adjacent to their row. Each row branch fused at 40 A.
- Software brightness cap: 40% of full. Full white at the cap stays under
  the supply rating with margin.
- Night operating brightness: 10 to 20%.
- One 12 V supply for portrait lightboxes, button LEDs, and the amp.
- One 5 V supply for the Pi and Colorlight card, separate from the wall
  branches so a wall fault cannot brown out the controller.

| Load | Watts |
|---|---|
| Wall, night, dimmed text | 100 to 150 |
| Wall, worst case at 40% cap | ~800 |
| Pi, Colorlight, amp, 5 lightboxes | 40 to 60 |

Source of AC power (event supply, generator, or a 1 kWh class battery
station) is an open question, see section 8. A 1 kWh station covers one
night of realistic load.

### 3.4 Cabinet and structure

- Frame: welded steel angle or 40x40 aluminum extrusion, outer size about
  2.65 m x 1.05 m, modules bolted to the front face on their factory
  mounting points.
- Back: 12 mm exterior plywood, painted, silicone sealed to the frame.
- Roof: 30 cm drip edge along the top, sloped to the rear.
- Bottom: screened vents so PSUs breathe and any water that gets in drains.
- Supplies and power distribution live inside the cabinet. The Pi,
  Colorlight card, button interface, and amp live in a separate IP65
  enclosure at ground level.
- Mounting: ground supported on two posts, strapped to trees for stability.
  The trees do not carry the load. Estimated all-up weight 35 to 45 kg.

### 3.5 Portraits and buttons

Five stations. Each is a slim outdoor LED lightbox snap frame on a stake
holding a backlit print of the entry's source and the plaque. Each has an
IP65 illuminated arcade button.

Wiring: one 4-conductor outdoor landscape cable per station from the
central box. Two conductors carry 12 V for the lightbox and button LED,
two carry the button contact closure. Cables are staked or buried. Button
LEDs are switched from the Pi through a MOSFET so a queued portrait can
pulse.

Button inputs reach Pi GPIO through optoisolators with pull-ups and
hardware debounce.

### 3.6 Audio

A small 12 V amp in the central box driving one outdoor horn speaker
mounted under the wall. Sound cues for keypress, compile, run, and error.

## 4. Software

### 4.1 Architecture

One Python daemon, `show`, on the Pi, run under systemd with the hardware
watchdog enabled. It is a state machine with three states:

- ATTRACT: slowly scrolls the source of each entry, cycles the phosphor
  cursor, and pulses portrait lights.
- PLAYING(entry): runs the entry pipeline (section 4.3).
- Queue: a FIFO of pending entries. A press during PLAYING appends, lights
  that portrait's button, and the wall shows an "up next" line.

The wall is a real terminal. The show holds one pseudo-terminal sized
80x24 and a pyte screen tracking its state. Every frame the renderer
rasterizes the pyte cell grid to a 512x192 RGB framebuffer and hands it
to a display backend.

### 4.2 Components

| Component | Responsibility | Depends on |
|---|---|---|
| `input` | Reads GPIO buttons, debounces, emits press events | RPi.GPIO or gpiozero |
| `queue` | Ordered pending entries, dedupe, "up next" | none |
| `state` | ATTRACT / PLAYING transitions, timeouts | queue, pipeline, renderer |
| `pipeline` | Runs one entry: show source, compile, run, fallback | pty, sandbox, recordings |
| `terminal` | pty + pyte, 80x24, feeds bytes in, yields cell grid | pyte |
| `renderer` | Cell grid + font + palette to framebuffer; glow, cursor blink | font assets |
| `display` | Backend interface `push(frame)` with implementations | see below |
| `lights` | Portrait LED and lightbox control | GPIO |
| `audio` | Plays cue sounds | any simple player |
| `entries` | Loads entry directories, validates them at startup | filesystem |

Display backends, all behind the same interface:

- `SDLDisplay`: preview window for development on a laptop. Also used to
  render the fallback recordings.
- `ColorlightDisplay`: raw L2 Ethernet frames to the 5A-75E.
- `DDPDisplay`: DDP packets to Falcon Player, which drives the card.
- `MatrixDisplay`: rpi-rgb-led-matrix Python binding, backup path.

The backend is chosen by config. Nothing above the display layer knows
which one is in use.

### 4.3 Entry pipeline

Each entry is a directory:

```
entries/<slug>/
  entry.toml      # author, year, title, build cmd, run cmd, timeouts, notes
  <source>.c      # the code as submitted, unmodified
  fallback.cast   # asciinema-style recording of a known-good run
```

Playing an entry:

1. Light the portrait, play the keypress cue.
2. Typewriter-scroll the source into the terminal (`cat` with paced output).
3. Run the build command in the pty. Real gcc output, warnings and all.
4. Run the program in the pty inside a sandbox: separate user, CPU and
   memory limits, no network, wall-clock timeout from `entry.toml`.
5. Hold the final frame for a configured dwell, then return to ATTRACT or
   pop the next queued entry.

Error handling:

- Build failure or run crash: play the error cue, show the real error
  output for a few seconds, then replay `fallback.cast` through the same
  terminal and renderer so it looks identical to a live run.
- Timeout: kill the process group, same fallback path.
- Any exception in the pipeline: logged, state returns to ATTRACT. The
  daemon never exits on an entry error.
- Daemon crash: systemd restarts it within 2 seconds. Hardware watchdog
  reboots the Pi if the daemon stops petting it.
- Display backend failure: logged and retried; the show keeps running so a
  cable reseat recovers it without a restart.

### 4.4 Terminal look

- Single phosphor palette, configurable: P1 green or P3 amber.
- 6x8 bitmap font drawn from DEC or IBM character shapes, not a generic
  pixel font.
- Blinking block cursor.
- Optional faint glow: neighboring pixels lit at a low fraction to mimic
  phosphor bloom. Off by default until seen on real modules.
- Output pacing on the source scroll and compile output so it reads as a
  machine working, not a dump.

### 4.5 Testing

- Unit tests: renderer (cell grid to pixels, font metrics), queue
  semantics, entry loading and validation, state transitions with a fake
  clock.
- Pipeline tests against the SDL backend using a trivial "hello" entry and
  a deliberately failing entry, asserting the fallback path runs.
- Hardware bring-up: two-module prototype in week 2 with both drive paths.
- Full-wall soak test in week 5: 8 hours overnight, buttons pressed on a
  timer, memory and temperature logged.
- Weather test in week 6: hose on the cabinet for 15 minutes while
  running.

## 5. Bill of materials

| Item | Qty | Est. cost |
|---|---|---|
| P5 outdoor 64x32 HUB75 modules (48 + 6 spare) | 54 | $1,300 to $1,600 |
| Colorlight 5A-75E receiving card (+1 spare 5A-75B) | 2 | $80 |
| Raspberry Pi 4, 4 GB, SD card, case | 1 | $80 |
| Active-3 HUB75 adapter (backup path) | 1 | $30 |
| 5 V 300 W rain-rated LED PSU | 6 | $180 |
| 12 V and 5 V accessory PSUs, fuses, distribution | 1 | $80 |
| HUB75 ribbon cables, power harnesses | lot | $60 |
| Frame material, plywood, paint, sealant, hardware | lot | $300 to $400 |
| IP65 enclosure for controller | 1 | $60 |
| Outdoor LED lightbox frames with stakes | 5 | $400 to $600 |
| Backlit prints and plaques | 5 | $100 to $150 |
| IP65 illuminated arcade buttons | 6 | $60 |
| Optoisolator input board, MOSFET board | 1 | $30 |
| 4-conductor outdoor landscape cable, 200 ft | 1 | $80 |
| 12 V amp and outdoor horn speaker | 1 | $70 |
| Total, excluding power source | | $2,900 to $3,500 |

Two modules are also ordered from a fast-shipping seller in week 1 for the
prototype, so the software and drive chain can be proven before the bulk
order lands.

## 6. Schedule

| Week | Dates | Milestone |
|---|---|---|
| 1 | Sep 22 to 28 | All orders placed. 5 entries curated and confirmed to build on modern gcc. Repo scaffolded. |
| 2 | Sep 29 to Oct 5 | `show` running on laptop with SDL preview: terminal, renderer, queue, attract. Two modules lit on both drive paths; primary path chosen. |
| 3 | Oct 6 to 12 | Frame and cabinet built. Portrait prints ordered. Button and cable harness assembled. |
| 4 | Oct 13 to 19 | All modules tested on arrival and mounted. Power distribution done. Wall lit end to end. |
| 5 | Oct 20 to 26 | Buttons, lights, audio integrated. Fallback recordings captured. Overnight soak test. |
| 6 | Oct 27 to Nov 2 | Hose test. Spares packed. Transport rig built. |
| 7 | Nov 3 to 10 | Buffer. Pack. |
| | Nov 11 | Install. |

Critical path: module delivery. Order from a US stock seller in week 1 even
at a 30% premium over overseas pricing.

## 7. Risks

| Risk | Mitigation |
|---|---|
| Modules arrive late | US stock seller; week 7 is buffer; software is built against SDL so nothing waits on hardware |
| Dead pixels or dead modules | 6 spares; test every module on arrival |
| Colorlight sender does not work with this card revision | Backup path with rpi-rgb-led-matrix is bought up front and tested in week 2 |
| 1/8 scan multiplexing wrong on the backup path | Mapper options in the library; prototype in week 2 exposes this early |
| Entry hangs or crashes on the wall | Sandbox timeouts and fallback recordings; the daemon never exits on entry error |
| Rain reaches the module backs | Sealed cabinet, drip roof, hose test in week 6 |
| Wall too bright at night | Brightness cap and a config knob; set on site |
| Power source unknown | Load designed to fit a 1 kWh battery station; decide by week 3 |

## 8. Open questions

1. Power on site: event supply, generator, or battery station.
2. P6 availability from a US stock seller. Decides wall width; does not
   change anything else.
3. Final list of five entries. Must produce terminal output that fits
   80x24 and build on a current gcc, possibly with flags recorded in
   `entry.toml`.
4. Phosphor color, green or amber. Config only.
