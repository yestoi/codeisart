# Hardware bring-up: Colorlight 5A-75E and the four P5 panels

**Status (2026-09-29, 12:05): in progress. Card 1's flash still holds the factory settings (nothing was
saved to it).** The Intelligent Setting wizard ran to the end (Guides 1 to 8, all 1024 points and rows) and its
result was **Sent** to the card's RAM. Since 13:00 (Receiver Mapping set to 128 x 64 and Sent) the picture
reaches all four panels in the right colours, but each grid line shows as 3 to 4 rows (see "13:00" below). The
`wall_pattern.py` checks have not run yet. How to continue: `.claude/skills/ledvision-card-setup/SKILL.md`,
from the worktree `/Users/trey/dev/codeisart-ledvision` (branch `ledvision-card1`). Screenshots: `hardware/`.

### Where the last session stopped (2026-09-29, 12:05)

- The VM is running; LEDVision is open with the Screen Test window on **Grid, paused** (white oblique lines,
  gap 16). LED Screen Settings is closed (re-select adapter #2 and Detect when it is reopened).
- The wizard's result is in the card's RAM (Send) at **Brightness Level 1 (8%)**, and saved as a file:
  `hardware/card1-wizard-20260929.rcvbp` (Load > Browse restores it without redoing the wizard). The Guide 8
  table is `hardware/card1-guide8-route.csv` (Import alignment table in Guide 8).
- **Open problem: the wall does not show LEDVision's picture.** Since Finish it shows a dim green pattern (2x2
  clusters about every 4 columns, two bands in the top ~8 rows of the top-left panel,
  `hardware/12-after-finish-green-pattern.png`) whatever LEDVision sends: Gray 0, Grid, Grid paused, with LED
  Screen Settings open or closed (`hardware/13-grid-test-not-on-wall.png`). The card answers Detect (5A 13.17)
  and took the Send (the pattern dimmed when Brightness Level went from 8 to 1). The pattern jitters by exactly
  one column at random (the owner saw it "moving back and forth"; the camera measures 0 or +6 px, frame to
  frame).
- What it probably means: (1) Guide 1 warns "Smart settings will reset the cabinet construction", so the
  Receiver Mapping tab (which region of the screen card 1 takes) was likely reset; the card then gets no video
  for its area and keeps the last frame, the wizard's own. Next: LED Screen Settings > Receiver Mapping, card 1
  = 128 x 64 at 0,0, Send. (2) The one-column jitter looks like a data timing fault: the wizard set DCLK 15.6 MHz,
  refresh 960, Refresh x16 (the factory had 10.4 MHz, 480). If it stays on the real picture, lower DCLK and Send.
- Web research (12:30), nothing describes these symptoms exactly:
  - Wired Watts' outdoor P5 guide (https://www.wiredwatts.com/colorlight-setup-for-outdoor-p5-panels) sets
    Receiver Mapping (width, height, col 1, row 1) and presses "Save to Devices" before the wizard. We never set
    Receiver Mapping. The guide also says "set the DCLK as low as possible" and to drop Refresh x16 to x8.
  - Its grid step is "drag across line nine, then line one", so on its panels the points walk along row 9 first.
    Ours alternate row 9 / row 1 per column: our panels are wired differently, and its row order (10 to 16) is
    not proof for ours.
  - Each point lighting two LEDs 4 rows apart fits a fault on address line C (HUB75 pin 11): a cable, the
    card's output, or the panel's row decoder (https://www.lcf-led.com/articledetail/2261.html: rows lit
    together in regular pairs means checking A/B/C/D for shorts or a bad 138). The chip count on the back
    (48 drivers, "8S") rules out a panel that is really 1/4 scan.
  - The 5A-75E's green LED blinks about once a second when normal, about 10 a second in "Cabinet: Sorting &
    Highlight" (5A-75E spec V8.0).
- 12:30: the owner powered the wall off (the card is back on its flash, the factory settings, when it comes
  up) and swapped a long ribbon cable for a short one to see whether the fault moves.

### 13:00: the picture reaches the wall; lines are multiplied on all four panels

- Setup at 12:55: the card → top-right ribbon replaced with a short one; a ribbon found unplugged on the top-left
  panel was plugged back in; the card power-cycled (flash: factory settings), then the wizard's parameters
  **Sent** at Brightness Level 1.
- Right after that Send, before any mapping change, the green pattern came back on the top-left panel
  (`hardware/15-green-pattern-after-send-fresh-boot.png`). So it is not left over from the wizard: it is what
  the card shows under these parameters when no picture arrives for its region.
- **Receiver Mapping was the "no picture" fault.** Read from the card: 6 receivers in a row, each 128 x 512
  (a previous installation's layout, `hardware/16-card1-stored-mapping-6x128x512.png`). LEDVision's own
  mapping had the receiver numbered 0 (not connected). Set: Col 1, Row 1, receiver 1 = 128 x 64, **Send**
  (not Save to Devices). The green pattern vanished (`hardware/17-mapping-sent-pattern-gone.png`) and Gray
  red/green/blue 128 fill all four panels evenly in the right colours (`hardware/18-red128-whole-wall.png`).
  The mapping is in the card's RAM only; the card's flash still has the 6 x 128x512 layout.
- **Pixel placement is wrong on all four panels alike.** Grid, horizontal lines, width 1, gap 16 (should be 4
  single rows): each line shows as a band of 3 to 4 lit rows over about 8 rows, at rows ~1, ~4-5, ~8 of each
  16-row half, the same on the top panels (J1, the new short cable) and the bottom panels (J2, the old
  cables) (`hardware/20-grid-horizontal-gap16.png`; the oblique grid, `hardware/19-grid-oblique-gap16.png`,
  is dense for the same reason). Four panels on two chains behaving the same points away from one cable or
  one panel: to the card's shared address outputs, or to a setting (decoding type, the Guide 8 row order).
- The one-column jitter is gone (120 frames, no horizontal shift). The owner sees a slight flicker; the camera
  measures a ~5% dip in one frame in 10 to 15 (static lines, 30 fps), which may also be the camera beating
  with the refresh.

### What the 2026-09-29 session found

- The wizard runs at the card's own Brightness Level, not at LEDVision's 40%. At level 8 (the factory
  setting) Guide 2's band was full white; the owner confirmed level 3 (31%) was dimmer. Level 1 is 10%, and
  LEDVision warns "Minimum OE is 0" (the darkest grey step is lost; the mapping is not affected).
- Guide 6: the band is rows 1 to 16 of the top panels (96 px on the photo at 5.7 px a row): 16.
- Guide 7: four lines, rows 1-2, 5-6, 9-10 and 13-14, each two rows thick: answer 2
  (`hardware/07-guide7-lines-rows-1-2-5-6-9-10-13-14.png`).
- Guide 8: at its start the top-left panel keeps Guide 7's four lines and the point on the top-right panel
  blinks (`hardware/08-guide8-start-daylight.png`: in daylight the camera cannot see it). Resolved at 11:40:
  point 1 is on the top-right panel's first column (at the joint), rows 9 and 13, as the 2026-09-28 notes say.
  The camera found it by splitting a 4 s recording into on and off frames; the glare off the lit lines hides a
  one-column difference, so the owner settled which side of the joint it was on.
- The camera's colour and brightness readings: Guide 3 state 1 black, state 2 white; Guide 4 state 1 dimmer
  (the camera saturates on both; state 2 more); Guide 5 as before (`hardware/10-guide5-states-1-4.png`).

## Hardware

| | |
|---|---|
| Panels | Wired Watts outdoor P5, 64x32, 1/8 scan, HUB75. Silkscreen `P5-1921-64X32-8S-H3.3` (SMD1921 LEDs; "8S" = 1/8 scan), sticker `YP5-5125HG505-Y2076` (`hardware/14-panel-back.jpg`). Wired Watts' own page lists SMD2121 and the product is discontinued, so these may not be the panels its setup guide was written for |
| HUB75 pinout (silkscreen) | R1 G1 / B1 GND / R2 G2 / B2 N / A B / C N / CLK LAT / OE GND: address lines A, B, C only (pins 8 and 12 unused), as a 1/8-scan panel should be |
| Power input | a 6-way footprint labelled VCC, VCC, 2.8V, 2.8V, GND(-), GND(-); the 4-pin plug sits on 2.8V, 2.8V, GND, GND and the VCC pads are empty (L1, L2 next to them look fitted). Supply voltage not recorded yet |
| Driver chip | 24-pin SSOP, designators per colour (UR, UG, UB) numbered to at least 15, so about 16 a colour and 48 in all: 128 channels a chain, which fits 1/8 scan and the 128 points the wizard found. Top marking not legible in the photo yet |
| Decoder chip | not read yet (16-pin SOPs near the power input); LEDVision's preset assumes 138 decoding. Two 16-pin footprints next to JOUT (Q6, Q7) are empty |
| Receiver card | Colorlight 5A-75E (card 1 of 2; the second is the spare) |
| Firmware | **5A 13.17** (LEDVision *Detect Receivers*; support chips "Normal Chip, Normal Serial"). Not upgraded. |
| Sender | Omarchy host port `enp5s0` (Intel 82574L), straight to the card, no switch, 1000Mb/s Full. LEDVision 8.8.41956 in a Windows 11 VM with that port as macvtap passthrough (`tools/ledvision/`) |

## Wiring

Four panels 2 x 2, 128x64. Two chains of two, one per row. Seen from the FRONT:

```
   J1 -> [1-1 top right] -> [1-2 top left]
   J2 -> [2-1 bottom right] -> [2-2 bottom left]
```

Output J1 drives the top row and J2 the bottom row; each chain enters at the right-hand panel (cascade "From
Right to Left"). The card's cable entering the top-right panel was confirmed on the wall: the wizard's test
points appeared on the top-right panel. `hardware/04-module-layout-2x2.png` is LEDVision's map. The card does
not need the 256x32 workaround.

## Card 1: factory settings (before any change)

Read from the card and saved as `hardware/card1-factory-before.rcvbp` (sha256
`8a799bac0502dc45a42613e5caa20315bedeb6f5344e255ba0205a0c06991513`); `hardware/03-card1-factory-params.png`.
Module 32Wx32H, 32 scan, Normal chip, 138 decoding, positive data phase, OE low valid; cabinet 128x512, From
Right to Left, 2 Split (Same Direction), Normal 32 groups; refresh 480, gray level 8192, DCLK 10.4 MHz,
blanking 11, Refresh x8, Balanced Low Gray, Gray-level First, brightness level 8 (81%); calibration disabled,
from receivers; no-signal action Keep the Last Frame; input 8 bit; gradual off; gamma 2.8.

## Configuration so far (entered, not saved to the card)

- Preset: General Parameters (Fullcolor) > "14- full-color eight scan" (module 32Wx8H, 8 scan).
- Data Group Normal 32 groups; cabinet 128x64; module 64x32; LEDVision brightness 40%.
- Intelligent Setting wizard, watching the top-right panel:
  - Guide 3: "1 display black and 2 display white". Guide 4: "1 darker than 2".
  - Guide 5, **pixel order**: the card's red showed green, green showed blue, blue showed red. Entered
    State1 Green, State2 Blue, State3 Red, State4 Black; that makes the card send RGB
    (`hardware/05-guide5-colour-order.png`). Not yet checked with `wall_pattern.py rgb`.
  - Guide 6: 16 rows lit. Guide 7: four lines were visible in the top half, but with "4" Guide 8 lit nothing;
    "2" (Wired Watts' answer) worked.
  - Guide 8, data order: the point alternates row 9, row 1 in each column, columns 1 to 64 left to right;
    confirmed on the wall across the whole width (2026-09-29: checked by camera at columns 1, 2, 9, 25, 35,
    49 and 64). Point 1 is on the **top-right** panel, its first column (next to the joint with the top-left
    panel), confirmed by the owner. Each point lights two LEDs four rows apart (rows 9 and 13, then 1 and 5),
    not one (`hardware/11-guide8-point1-on-off.png`); on the top-left panel Guide 7's lines stay lit.
  - Guide 8, row order: after the 128 points the rows were clicked in column 1 as 10, 11, 12, 13, 14, 15, 16
    (Wired Watts' order; the camera saw each step light four rows 4 apart, 3/7/11/15 first, as on 2026-09-28).
    The wizard took all seven and said "Finished" (the 2026-09-28 run, which clicked 11, 10, 12, stalled). The
    table (`hardware/card1-guide8-route.csv`, `hardware/09-guide8-mapping-complete.png`) is the plain 1/8
    layout: scan line k drives row k (even bits) and row k+8 (odd bits), 128 bits a line.
  - After Finish: module 64W x 16H, 8 scan, 138 decoding, cabinet 128 x 64, From Right to Left, Normal 32
    groups; refresh 960, Refresh x16, DCLK 15.6 MHz, blanking 0, Gray 8192, Balanced Low Gray, Gray-level
    First, gamma 2.8. Finish put Brightness Level back to 8; it was set to 1 before the Send.
- Scan type chosen: 1/8 ("eight scan" preset). Not yet seen working on a real picture.

## Still to record

- As saved: gamma, brightness, current gain, refresh, DCLK (the Receiver Parameters tab after Save to Receivers).
- The exported config: `hardware/colorlight-outdoor-p5-2x2.rcvbp`.
- `wall_pattern.py` on `enp5s0`, 128x64: `rgb`, `index`, `steps --brightness 0.4` (does the card honour the
  brightness packet on 5A 13.17, are the steps even), `gamma` (does the card apply gamma: sets `gamma` in
  `arcade.toml`).
- Card 2: firmware, and that it reads back the same settings.
