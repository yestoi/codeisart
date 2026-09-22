# Adversarial review of the spec and plan, 2026-09-22

Four independent reviewers attacked the spec (`docs/superpowers/specs/2026-09-22-code-is-art-design.md`)
and the plan (`docs/superpowers/plans/2026-09-22-show-daemon.md`) from four angles: hardware and
electrical, software, schedule and procurement, and on-site experience. The software reviewer
extracted every code block from the plan and ran the suite: all 87 tests pass as written on macOS.
Nothing below has been applied. Spec-level decisions are the artist's.

## Blockers

1. **Power budget is wrong by 2 to 3x.** 1/8-scan outdoor modules draw 3 to 5 W each at black for
   logic and driver quiescent. 48 modules is 150 to 240 W before one pixel lights, plus supply
   losses. Realistic night draw is 250 to 350 W AC, not 100 to 150. Mid-November dark is about 13
   hours, so one night is 3 to 4.5 kWh. The "1 kWh station covers one night" claim fails around
   midnight. Worst case at the 40% cap is nearer 1.1 kW AC. The 12 V budget also omits five
   lightboxes at 10 to 20 W each. Action: measure quiescent draw on the two prototype modules and
   republish the table; confirm event mains in writing this week or budget a 2 to 3 kWh station.

2. **Schedule is about 2x overcommitted.** Realistic total is about 230 hours over 7 weeks, 33 per
   week, against 15 to 20 available with a day job. Weeks 3 and 4 need 55 to 65 hours each. The
   cabinet alone is 25 to 35 hours. Entry curation is 10 to 20 hours and the spec puts it in week 1
   while the plan puts it in week 3. Missing entirely: event placement and power paperwork, site
   survey, print artwork design and proofing, plaque fabrication, a truck, a helper for lifting,
   12 to 16 hours of on-site build, 6 hours of teardown. The true critical path is cabinet
   fabrication and full-wall wiring, not module delivery.

3. **Structure and weight are underestimated by 2x.** Modules 24 kg, plywood 21 kg, steel frame
   20 kg, supplies 7 kg, hardware 5 kg: expect 75 to 85 kg, not 35 to 45. A 2.8 m² sail takes about
   650 N at 40 mph and 1.5 kN at 60 mph. "Strapped to trees, trees do not carry the load" is a
   contradiction. Two posts without footings will not hold it. Needs braced A-frame legs, guy lines
   to screw anchors, ballast, a drop-in-wind plan, and someone to check the overturning moment.
   Missing safety items: GFCI, a labelled AC disconnect for the safety team, PE bond of the frame,
   strain relief on ribbons, supplies not mounted on bare plywood, generator placement rule.

4. **5 V distribution as specified is a fire and brownout risk.** A 40 A row fuse does not protect
   20 AWG module pigtails on VH3.96 contacts rated about 7 A; a pigtail short cooks before the fuse
   opens. A row at the cap draws about 32 A; 2 m of 10 AWG round trip drops 8% and modules
   color-shift below 4.7 V. Nothing bonds the six supply negatives, so ribbon ground pins carry
   return current and corrupt data. Six switching supplies starting at once trip an inverter or
   small generator. Do instead: 10 A fuse per module pair at a distribution block, supply at row
   centre feeding two 8 AWG stubs, outputs trimmed to 5.1 to 5.2 V, one 6 AWG star bus for all 0 V
   and the card, staged power-up or inrush limiters.

5. **The rpi-rgb-led-matrix backup path cannot coexist with the rest of the design.** Three parallel
   chains consume every usable GPIO, leaving nowhere for five buttons and five PWM LEDs.
   `dtparam=audio=off` kills the 3.5 mm jack the cues need. U-mapper requires alternate rows mounted
   upside down, which points outdoor module louvers up (rain gutters) and makes the wall physically
   incompatible with the straight-row Colorlight layout. Modules with ICN2053, ICN2153 or MBI5153
   (S-PWM) drivers are unsupported by the mainline library, so the backup path may be dead on
   arrival; confirm the driver IC before ordering. The Active-3 ships from China in 2 to 4 weeks, so
   the week 2 three-path decision cannot happen in week 2. Recommendation from two reviewers: drop
   the backup path and Tasks 16 and 17, use an Adafruit bonnet (US stock) only for a two-module
   sanity test if desired.

6. **Boot failures leave the wall dark permanently.** An empty or invalid entries directory, a
   missing font, a raw-socket bind with no carrier, or a gpiozero error escapes `main` and crashes
   the process; with `Restart=always` systemd's default start limit (5 in 10 s) then stops
   restarting. Fix in plan: `StartLimitIntervalSec=0`, catch startup errors and keep the loop and
   watchdog alive with a static error frame, rescan entries every 30 s, move `press` and `render`
   inside the try.

7. **The default `pump(max_bytes=262144)` stalls the frame loop on a Pi.** Measured pyte throughput
   is about 1 MB/s on a laptop; a Pi 4 is about 10x slower, so one default pump is 2 to 3 s inside
   `show.tick`. Review Focus 2 is tested only with `max_bytes=100`. Fix in plan: default 4096 bytes
   plus a time budget (stop after 8 ms), and test the default with the flood entry.

## Serious

8. **Colorlight card configuration.** The reverse-engineered protocol sends pixels and brightness
   only. Scan mode, driver chip and port layout live in the card's flash and are set with LEDVision,
   which normally needs a Colorlight sender card (S2) and a Windows machine. Verify in week 2 whether
   the card can be configured over the Pi link; otherwise add the S2 and a laptop to the BOM.
   Chains of 8 at 1/8 scan sit at the vendor's per-port limit; with 16 ports use 12 chains of 4 for
   double the refresh and grey depth. Falcon Player's Colorlight output wants its own Ethernet
   interface, so a USB Ethernet adapter is missing from the BOM. DDP through FPP adds one to two
   frames of latency and duplicates or drops frames at 30 fps; the hardware reviewer wants raw
   Colorlight primary, the software reviewer measured that the raw path from Python misses 30 fps
   unless packets are prebuilt as a fixed uint8 array with one strided pixel fill per frame.

9. **Module mounting and moisture.** Outdoor modules seal by compressing a rear gasket against a
   flat skin, screwed from behind on inserts at exact 320x160 mm pitch. Angle iron gives no flat
   surface, no seal, and visible seams if pitch drifts 1 mm. Use a punched 1.5 mm steel or aluminium
   skin or a welded tube grid at module pitch. A sealed box holding 100 W of supplies condenses on
   module backs on a cold night; vent top and bottom with hooded screened louvers and treat it as a
   rain screen. The front-only hose test misses wind-driven rain into bottom vents and suction on
   cooling modules; spray upward into the vents with the wall hot, for an hour.

10. **Budget is $1,500 to $3,000 short.** Missing or low: sales tax (about $300), freight on 20 kg
    of modules, tools (crimper, hole saw, step bit, T-nuts or a welder), 8 AWG wire and lugs, fuse
    holders, IP67 station connectors ($150), sealant and paint ($80), ground anchors and straps
    ($100), truck rental ($150 to $250), spare Pi and SD cards ($80), 10% failed parts. Rain-rated
    5 V 300 W supplies at $30 do not exist in US stock; use Mean Well LRS-350-5 inside the cabinet.
    12 V outdoor lightboxes are a sign-trade special order. Replan at $4,500 to $6,000 before power.

11. **Experience: the interaction under load is unsatisfying.** Eight people mash five buttons at
    t=0: first entry plays to 31 s, second to 62 s, third to 93 s, fourth to 124 s; the group left at
    45 s. A press on the playing or already-queued station gives zero feedback (no cue, no light
    change), so people mash harder and decide it is broken. Changes: always cue and flash on any
    press and show "PLAYING" or "QUEUED #3" for 2 s; when the queue is non-empty cap the run at 10 s,
    skip dwell, and shorten the source scroll; auto-play a random entry every 5 idle minutes.

12. **Experience: the concept is under-served on the wall.** Task 19's build template uses `-w`,
    which suppresses every warning, so the live-compile beat prints nothing; spec 4.3 promises
    "warnings and all". Build with `-Wall` and give BUILD a visible minimum of 1 to 2 s. The author
    credit and "Not A.I." are on the wall for under 2 s, then scroll off; during the run there is no
    attribution anywhere. Proposal: dedicate row 24 permanently to "NOW: title by author, Not A.I. |
    NEXT: ..." and run entries in 80x23. That conflicts with the spec's "true 80x24". The status row
    as designed also clobbers row 24 of full-screen entries whenever anything is queued. The attract
    banner scrolls off after 8 s and never returns until the next play. Switch the lightbox itself,
    not only the button LED, so the playing portrait glows from 60 ft.

13. **Software correctness on Linux.** `signal_of` treats any exit code above 128 as a crash;
    IOCCC entries routinely return garbage from `main` (`exit 200` reports "crashed (signal 72)"), so a
    perfect run gets the error cue and a fallback replay. Treat only `rc < 0` as a crash and prepend
    `exec` for simple commands. `kill()` skips `killpg` once `sh` has exited, so an entry that
    backgrounds a child keeps the pty open, `finished` never turns true, and the orphan survives with
    only the CPU rlimit as backstop; macOS returns EOF earlier, which is why laptop tests pass. Always
    `killpg` and treat "exited but no EOF within 0.5 s" as finished. `reset()` does not restore
    geometry after DECCOLM (`ESC[?3h` resizes pyte to 132 columns); call `screen.resize`. The `pi`
    extra installs gpiozero with no PWM-capable pin factory in a venv on Bookworm, so `PWMLED` raises
    and the daemon crash-loops; add `lgpio` and fall back to `FakeLights` on error.

14. **Pi frame budget.** Measured per frame on a laptop: render 1.8 ms, glow 4.2 ms, Colorlight
    packet build 0.9 ms plus 385 sends, DDP 1.8 ms plus 205 sends. Scaled 8 to 12x for a Pi 4: DDP
    about 25 ms plus FPP's own load, marginal; raw Colorlight 30 to 40 ms, misses 30 fps; glow about
    40 ms, unusable. Render only when `screen.dirty` is non-empty or cursor/status changed, clear
    `dirty` after rendering, re-push the cached frame otherwise, default 20 fps.

15. **Spec drop: sandbox.** Spec 4.3 requires "separate user, no network". The plan's global
    constraints redefine the sandbox as rlimits; entries run as `pi` with write access to the repo,
    home directory, and network. Either amend the spec or wrap runs in `unshare -rn` and add
    `ProtectSystem=strict` with `ReadWritePaths=` for the entries directory to the unit.

16. **Brightness handling bands.** The plan scales pixels in software before sending; at 15% that
    leaves about 38 of 256 levels, so glow and cursor fades band. Send full-range pixels and set
    brightness on the card or through the library option.

17. **Portrait stations.** "4-conductor landscape cable" is not a product; use 18 AWG UF-rated
    irrigation wire and IP67 M12 or SP13 connectors, and bury or ramp every run. Most "IP65 arcade
    buttons" are not; use 22 mm stainless ring-LED industrial buttons. A slim lightbox on one stake is
    a 0.4 m² sail and will fall. Five cables run from the wall forward across the viewing area, where
    bikes at night will find them; trench them or route behind the portrait line. The plan's
    `ButtonInput` uses bare GPIO pull-ups, contradicting the spec's optoisolators. Button height is
    unspecified; 36 in for wheelchair reach. Print artwork has no design time and prints are ordered
    the same week as the frames whose live area they need; order frames now, design in week 2, print
    in week 3.

18. **Single points of failure.** One Pi and one SD image, one card, one person, one week of buffer
    already consumed by finding 2. Buy a second Pi 4, clone the SD after the soak test, enable the
    read-only overlay filesystem, add a weatherproof access hatch and a wired keyboard port.

19. **`FakeDisplay` stores every frame.** Task 19's capture recipe runs it at 30 fps for 40 s, over
    300 MB. Keep only the last frame and a count.

## Minor

20. `apply_glow` uses `np.roll`, so row 0 bleeds onto row 191 and column 0 onto 511; use padded
    slices. `run()` leaks both pty fds when `Popen` raises; close in an except block. DDP data type
    should be 0x0B (RGB 8-bit), not 0x01; FPP ignores it. FPP sends the 0x0107 Colorlight packet
    before the rows, not after; verify with the other constants. Pipeline, sandbox and main tests
    need `cc` and about 7 s; add `skipif`. Task 18's test inserts `"tools"` relative to cwd.
21. The glcdfont is exactly the "generic pixel font" spec 4.4 says not to use. Decide deliberately.
22. "Legible as text from 100 ft" is false; 40 mm characters read from 15 to 40 ft. "Recognizable
    as a text screen" is true and enough. Pick entries whose run has large motion.
23. Audio has no volume or quiet-hours config, the horn is loud and directional, and the error cue
    is a 350 ms square-wave buzz. Add both settings, aim at the wall, soften the error tone.
24. On sustained display push failure the daemon keeps pulsing button LEDs on a dark wall, which
    invites pressing and fiddling. Turn lights off after 10 s of failures; print a contact line.
25. No statement sign. Add a sixth lightbox with a 150-word statement, what IOCCC is, and a QR to
    ioccc.org. Mark a photo spot where the five portraits and the wall frame up.
26. "Not A.I." beside an AI-assisted build: the claim is about the code and it holds, since every
    entry predates LLMs. Add the year to the plaque as proof and disclose the AI-assisted daemon in
    the statement, which makes the distinction the point: the human code is the art, the plumbing
    is not.
27. Curation criteria should filter out entries that read stdin, use raw terminal modes, or need
    X11 before anything else. Entries that animate forever could run 40 s when the queue is empty.
28. Week 2 bring-up steps 6 and 7 need Tasks 16 and 17, which the milestones place in week 3.

## Descoping ladder (schedule reviewer), if behind at the end of week 3

1. Drop Tasks 16 and 17; DDP via Falcon Player is the only wall path.
2. Drop audio.
3. Drop the lightboxes; printed aluminium or coroplast signs on stakes with a vinyl plaque.
4. Drop the opto and MOSFET boards; buttons straight to GPIO, one fixed LED each.
5. Replace the steel or extrusion cabinet with a 2x4 frame, plywood box, tarp roof.
6. Reduce the wall to 8 wide by 4 tall (32 modules, 80x16, four supplies); re-verify entries fit.
7. Reduce to three stations.

Minimum viable piece for Nov 11: a lit wall of any size on the FPP path, attract loop and live
compile for at least three entries, three direct-GPIO buttons, printed portraits with plaques, no
audio, no queue, on event power.

## Must be answered this week

- Site power: event mains confirmed in writing, or a 2 to 3 kWh station purchase.
- Event placement accepted, and which safety, fire and power forms are due when.
- The five entries, since they gate prints, plaques, recordings, and the 80x24 assumption.
- Who lifts and who drives on Nov 10 and 11 and at teardown.
- Order within 48 hours regardless: two prototype modules, 5A-75E and spare card, USB Ethernet
  adapter, portrait frames, and the full module set from a seller with a US ship-from address.

## Checked and found OK

All 87 plan tests pass; expected counts are right; no task references a later task's file.
Renderer index math, glcd bit order, cursor clamp, hidden cursor, status row, reverse video, pygame
orientation. DDP header layout and packet count. Colorlight chunking under 1514 bytes. CastPlayer
gap compression. Station numbering 1-based end to end. sdnotify no-op without systemd. Missing gcc
yields the normal build-failed path. U-mapper arithmetic. 5A-75E pixel capacity (98k of about
131k). Pi 4 gigabit against 71 Mbps of frame data. 12 V drop over 40 ft of 18 AWG at 1.5 A.
Transformer isolation on the Pi-to-card link. Pi 5 exclusion.
