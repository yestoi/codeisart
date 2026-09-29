# Hardware bring-up: Colorlight 5A-75E and the four P5 panels

**Status (2026-09-29, 11:20): in progress. Card 1's flash still holds the factory settings: read back at
08:53, its `.rcvbp` was byte for byte the factory file (same sha256).** Guides 1 to 7 of the wizard were
answered again and checked on the wall; Guide 8 has no point clicked yet. The `wall_pattern.py` checks have
not run yet. How to continue: `.claude/skills/ledvision-card-setup/SKILL.md`, from the worktree
`/Users/trey/dev/codeisart-ledvision` (branch `ledvision-card1`). Screenshots: `hardware/`.

### Where the last session stopped (2026-09-29, 11:20)

- The VM is running. LEDVision is open: the Gray Test window at value 0 with Hide Gray Value (parked at the
  bottom right), and LED Screen Settings on Receiver Parameters, adapter #2 selected, card 1 detected.
- Entered in LEDVision, not saved to the card: preset "14- full-color eight scan", Normal 32 groups, cabinet
  128 x 64, From Right to Left, module 64 x 32 (check the Intelligent Module Setting map again; the wizard was
  cancelled twice), **Brightness Level 1 (10%)**. That level was sent to the card after the owner reset the
  wall, so the card's RAM holds it; a power cycle sends the card back to its factory 81%.
- The wizard is closed. Next: rerun it from Guide 1 (answers in the skill), then Guide 8 in a dimmed room with
  `wall_cam --flash`. The laptop has to be put back facing the wall, and the owner asked for the lowest
  brightness for the mapping.

### What the 2026-09-29 session found

- The wizard runs at the card's own Brightness Level, not at LEDVision's 40%. At level 8 (the factory
  setting) Guide 2's band was full white; the owner confirmed level 3 (31%) was dimmer. Level 1 is 10%, and
  LEDVision warns "Minimum OE is 0" (the darkest grey step is lost; the mapping is not affected).
- Guide 6: the band is rows 1 to 16 of the top panels (96 px on the photo at 5.7 px a row): 16.
- Guide 7: four lines, rows 1-2, 5-6, 9-10 and 13-14, each two rows thick: answer 2
  (`hardware/07-guide7-lines-rows-1-2-5-6-9-10-13-14.png`).
- Guide 8: at its start the top-left panel keeps Guide 7's four lines and the point on the top-right panel
  blinks (`hardware/08-guide8-start-daylight.png`: in daylight the camera cannot see it). The owner saw point 1
  on the far-right column of the top-right panel, not at row 9, column 1 as the 2026-09-28 notes below say.
  Unresolved until the camera or the owner confirms it.

## Hardware

| | |
|---|---|
| Panels | Wired Watts outdoor P5, 64x32, SMD2525, 1/8 scan, HUB75. Board marking `YPS-5125HG505-Y2076` |
| Driver chip | not read yet (the small repeated ICs on the back) |
| Decoder chip | not read yet; LEDVision's preset assumes 138 decoding |
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
    confirmed on the wall across the whole width.
  - Guide 8, row order: **open.** Each step lit four rows 4 apart (3/7/11/15, 2-3/6-7/10-11/14-15, 4/8/12/16
    twice) and the wizard stalled after rows 3, 2, 4. Wired Watts clicks rows 10 to 16 in order here
    (`hardware/06-guide8-partial-mapping.png`). The wizard was cancelled.
- Scan type chosen: 1/8 ("eight scan" preset), pending the row order.

## Still to record

- As saved: gamma, brightness, current gain, refresh, DCLK (the Receiver Parameters tab after Save to Receivers).
- The exported config: `hardware/colorlight-outdoor-p5-2x2.rcvbp`.
- `wall_pattern.py` on `enp5s0`, 128x64: `rgb`, `index`, `steps --brightness 0.4` (does the card honour the
  brightness packet on 5A 13.17, are the steps even), `gamma` (does the card apply gamma: sets `gamma` in
  `arcade.toml`).
- Card 2: firmware, and that it reads back the same settings.
