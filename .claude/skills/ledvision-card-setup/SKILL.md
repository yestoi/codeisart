---
name: ledvision-card-setup
description: Use when configuring the Colorlight 5A-75E receiver card for the LED wall through the ledvision Windows VM, or when driving that VM (screenshots, clicks, LEDVision, the Intelligent Setting wizard)
---

# Setting up the Colorlight card through the ledvision VM

The card needs a one-time setup in LEDVision 8.8 (Windows). It runs in the VM `ledvision` on the Omarchy host,
which owns the host's port `enp5s0` wired straight to the card. You drive the VM with `tools/ledvision/vm.py`
and see the wall with `tools/ledvision/wall_cam.py`. Setup, commands and screen coordinates:
`tools/ledvision/README.md`. What is known about the hardware: `docs/superpowers/workflow/evidence/hardware.md`.

## Rules

1. **Nothing lights the wall above 40%.** Set LEDVision's brightness to 40% (or lower) and hold the output
   black (Test > Gray Test, value 0, Hide Gray Value, window left open) *before* the Net Card is in use.
   No full white at 100%, no fast flashing: untick "Automatic changes" on every wizard page at once.
2. **Save to Receivers writes the card's flash: only with the owner's explicit OK**, after they have seen the
   result. Use **Send** (lost on a card power cycle) to try settings. The factory settings of card 1 are in
   `docs/superpowers/workflow/evidence/hardware/card1-factory-before.rcvbp` (Load > Browse restores them).
3. **Look before every click**: `vm shot` (crop to read small text), then click. After a click that changes
   the wall, take `wall_cam` and look at it before answering the wizard.
4. **If a step fails twice, stop and tell the owner** what you saw and what you think it means. No guessing
   loops. The owner is at the wall and can describe what the camera cannot resolve.
5. Close LEDVision (and `vm stop`) before anything on Linux talks to the card: they share the port.
6. The repo has an autonomous loop. Change only `hardware.md`, its `hardware/` evidence files, and this kit;
   stage files by path, never `git add -A`; never touch `docs/superpowers/workflow/state.md`.

## The loop

```
vm shot --out shots/vm.png --scale 0.75      -> read it (coordinates / 0.75)
vm click X Y  |  vm type '...'  |  vm keys KEY_...
wall_cam --out shots/wall-<step>.png          -> read it when the wall should have changed
```

Name wall photos after the step (`shots/wall-g8-p003.png`); the pairs are the evidence. From the camera the
wall is seen from the FRONT: left in the photo is left for a viewer, and LEDVision's "Look From Front" agrees.

## Procedure for a card

1. `vm start`; `vm status` shows ssh up and `enp5s0` at 1000Mb/s Full (the card will not link at 100).
2. `vm ledvision`. On "first time… check this computer?" answer No.
3. Test > Gray Test: value 0, Hide Gray Value. Drag the window aside and leave it open.
4. Control > LED Screen Settings (password 168) > Sending Device: Net Card, adapter "…Connection **#2**
   (Speed:1G)", Use Net Card, Detect Receivers. Expect one row: `5A 13.17` for card 1. Record the version.
5. Close it; Control > Brightness Adjustment: slider to 40%. Control > Screen Size and Count: 128 x 64 at 0,0.
6. LED Screen Settings again (**re-select #2 and Detect**), Receiver Parameters: **Read** and **Save…** the
   card's current settings to a file first (`cardN-factory-before.rcvbp`), then `vm get` it into
   `docs/superpowers/workflow/evidence/hardware/`.
7. Load > Preset Parameters > General Parameters (Fullcolor) > **14- full-color eight scan**. Data Group
   **Normal 32 groups**. Cabinet **128 x 64**, cascade From Right to Left. Intelligent Module Setting: module
   width **64**, height **32**; its map must show J1 = top row (1-1 top right, 1-2 top left) and J2 = the
   bottom row. If the card can only be mapped as one chain of 256x32, stop and tell the owner.
8. Intelligent Setting wizard, watching the **top-right** panel (first on J1). Answers found for these panels
   on 2026-09-28 (check each against the wall, they are not gospel):
   - G1 Single Type Module. G2 module width 64, 138 decoding, Normal 32 groups, output J1.
   - G3 "1 display black and 2 display white". G4 "1 darker than 2".
   - G5 colours are rotated: set State1 = **Green**, State2 = **Blue**, State3 = **Red**, State4 Black
     (what the wall shows for each). This is where the card's pixel order becomes RGB.
   - G6 **16**. G7 **2** (4 lines were visible, but with 4 G8 lit nothing; Wired Watts also uses 2).
   - G8 points: the lit point goes **row 9, then row 1** in each column, columns 1 to 64. Fill that, checking
     the wall every 8 to 16 columns.
   - G8 rows: **not solved yet.** After the 128 points each step lit four rows 4 apart (3/7/11/15, then
     2-3/6-7/10-11/14-15, then 4/8/12/16 twice); clicking the topmost lit row stalled it. Plan: Back to the
     128 points, click rows 10, 11, 12, 13, 14, 15, 16 in column 1 (Wired Watts' order), Finish; then Send and
     check with Test > Grid Test at 40% through the camera. Rows out of order: repeat mapping by what the
     camera shows, one step at a time, and stop at the second failure.
9. When the wall looks right to the owner: close the wizard, **Send**, then with the owner's OK **Save to
   Receivers**; **Save…** as `colorlight-outdoor-p5-2x2.rcvbp`; `vm get` it into the evidence folder.
10. Close LEDVision, `vm stop`, and on the host run the four `tools/wall_pattern.py` checks (`rgb`, `index`,
    `steps --brightness 0.4`, `gamma`; they need CAP_NET_RAW, so the owner runs them with sudo). Photograph
    each with the webcam and write what the wall shows into `hardware.md`.
11. Card 2 (spare): swap the card (same cable), steps 1 to 6, then Load > Browse the saved `.rcvbp`, Send,
    check, Save to Receivers with the owner's OK, Read back and compare.
