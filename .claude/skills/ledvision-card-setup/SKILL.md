---
name: ledvision-card-setup
description: Use when configuring the Colorlight 5A-75E receiver card for the LED wall through the ledvision Windows VM, or when driving that VM (screenshots, clicks, LEDVision, the Intelligent Setting wizard)
---

# Setting up the Colorlight card through the ledvision VM

The card needs a one-time setup in LEDVision 8.8 (Windows). It runs in the VM `ledvision` on the Omarchy host,
which owns the host's port `enp5s0` wired straight to the card. You drive the VM with `tools/ledvision/vm.py`
and see the wall with `tools/ledvision/wall_cam.py`. Setup, commands and screen coordinates:
`tools/ledvision/README.md`. What is known about the hardware: `docs/superpowers/workflow/evidence/hardware.md`.

**Start by reading `hardware.md`'s Status section.** It says where the last session stopped, and what the
VM, LEDVision and the card are doing right now. Take a `vm shot` and a `wall_cam` photo before any click.

## Where to work

This work runs in the worktree `/Users/trey/dev/codeisart-ledvision`, on the branch `ledvision-card1`, not in
the main checkout. The arcade operator runs in `/Users/trey/dev/codeisart` on `main`. It checks that its
evidence carries HEAD's sha, so a commit on `main` in the middle of an iteration breaks that check. Commit here;
the owner merges the branch when the operator is between runs. The worktree has no `.venv`: run everything from
the worktree's root with the main checkout's interpreter, `/Users/trey/dev/codeisart/.venv/bin/python`.
Never start this session with `OPERATOR=1`: that turns the operator's hooks on.

## Rules

1. **Nothing lights the wall above 40%.** Set LEDVision's brightness to 40% (or lower) and hold the output
   black (Test > Gray Test, value 0, Hide Gray Value, window left open) *before* the Net Card is in use.
   LEDVision's 40% only scales its video. The wizard and the test patterns ignore it and run at the **card's**
   Brightness Level (Receiver Parameters > Performance Setting, 1 to 8; the factory setting is 8, 81%). Set it
   to **1 (10%)** and **Send** before opening the wizard. A card power cycle forgets it, and so does loading a
   preset: send it again after either. No full white at 100%, no fast flashing: untick "Automatic changes" on
   every wizard page at once.
2. **Save to Receivers writes the card's flash: only with the owner's explicit OK**, after they have seen the
   result. Use **Send** (lost on a card power cycle) to try settings. The factory settings of card 1 are in
   `docs/superpowers/workflow/evidence/hardware/card1-factory-before.rcvbp` (Load > Browse restores them).
3. **Look before every click**: `vm shot` (crop to read small text), then click. After a click that changes
   the wall, take `wall_cam` and look at it before answering the wizard.
4. **If a step fails twice, stop and tell the owner** what you saw and what you think it means. No guessing
   loops. The owner is at the wall and can describe what the camera cannot resolve.
5. Close LEDVision (and `vm stop`) before anything on Linux talks to the card: they share the port.
6. The repo has an autonomous loop. Change only `hardware.md`, its `hardware/` evidence files, and this kit;
   stage files by path, never `git add -A`; never touch `docs/superpowers/workflow/state.md`; commit only on
   `ledvision-card1` (see "Where to work").

## The loop

From the worktree's root (in zsh a variable holding `python -m ...` does not split into words, so use the
full command, or a two-line wrapper script in the scratchpad):

```
P=/Users/trey/dev/codeisart/.venv/bin/python
LEDVISION_HOST=trey@192.168.12.127 $P -m tools.ledvision.vm shot --out shots/vm.png --scale 0.75
                                                   -> read it (coordinates / 0.75); --crop X,Y,W,H to read text
LEDVISION_HOST=... $P -m tools.ledvision.vm click X Y  |  type '...'  |  keys KEY_...
$P -m tools.ledvision.wall_cam --size 1280x720 --out shots/wall-<step>.png
$P -m tools.ledvision.wall_cam --size 1280x720 --flash 4 --panel L,T,R,B --out shots/g8-p001.png
```

Name wall photos after the step (`shots/wall-g8-p003.png`); the pairs are the evidence. From the camera the
wall is seen from the FRONT: left in the photo is left for a viewer, and LEDVision's "Look From Front" agrees.

The camera:
- The laptop's webcam gives 1280x720 frames. Its index moves between 0 and 1 from one run to the next (an
  iPhone Continuity Camera comes and goes at 1920x1080 and gives black frames), so always pass `--size 1280x720`.
- In daylight every unlit LED package reflects as a white dot, and a lit single LED does not stand out. The
  owner dims the room (a blanket over the wall and the laptop worked). Bright lit lines elsewhere on the wall
  also set the exposure and drown a single LED.
- The wizard's Guide 8 point **blinks**. A still photo misses it; `--flash 4` records 4 s and keeps only
  what changed, and prints where it blinked. `--panel L,T,R,B` (the top-right panel's outer edges in the photo,
  measured on a dark photo each time the laptop moves) turns that into the panel's row and column.

## Procedure for a card

1. `vm start`; `vm status` shows ssh up and `enp5s0` at 1000Mb/s Full (the card will not link at 100). The
   Mac's key (`~/.ssh/id_rsa.pub`) is already trusted by the guest (2026-09-29).
2. `vm ledvision`. On "first time… check this computer?" answer No (it did not ask on 2026-09-29).
3. Test > Gray Test: it opens at **Red 255**; at once click the value, Ctrl+A, type 0, Tab. Hide Gray Value
   ticked. Drag the window aside and leave it open.
4. Control > LED Screen Settings (password 168) > Sending Device: Net Card, adapter "…Connection **#2**
   (Speed:1G)", Use Net Card, Detect Receivers. Expect one row: `5A 13.17` for card 1. Record the version.
5. Close it; Control > Brightness Adjustment: slider to 40%. Control > Screen Size and Count: 128 x 64 at 0,0.
6. LED Screen Settings again (**re-select #2 and Detect**), Receiver Parameters: **Read** and **Save…** the
   card's current settings to a file first (`cardN-factory-before.rcvbp`), then `vm get` it into
   `docs/superpowers/workflow/evidence/hardware/`. For card 1 compare the sha256 with the one in `hardware.md`.
7. **The quick way (card 2 is done; use this for a replacement card):** Load > Browse
   `hardware/colorlight-outdoor-p5-2x2.rcvbp`, set Brightness Level 1, **Send**; then Receiver Mapping: Col 1,
   Row 1, click the cell, receiver 1 = **128 x 64**, **Send**. Check the Grid test (below), then with the owner's OK
   **Save to Receivers** and, on Receiver Mapping, **Save to Devices**; Read both back and power-cycle to prove
   it. The long way (new panels): Load > Preset Parameters > General Parameters (Fullcolor) > **14- full-color
   eight scan**, Normal 32 groups, cabinet 128 x 64 From Right to Left, Intelligent Module Setting 64 x 32 (the
   Modify buttons open lists; map: J1 = top row, 1-1 top right; J2 = bottom row), Brightness Level 1, Send
   (Yes to "Minimum OE is 0"), then the wizard (step 8).
8. Intelligent Setting wizard, watching the **top-right** panel (first on J1). Answers found on 2026-09-29 with
   card 2 (card 1 is faulty) and confirmed by a correct picture:
   - G1 Single Type Module. G2 module width **64** (it opens at 32), **Decoding Chip "ICN2018/3018 Decoding"**
     (the list may open scrolled: look before clicking), Normal 32 groups, output J1. **Not 138**: the panels'
     row drivers (T2/T3, 10-pin, next to the power plug) are serial; with 138 every address lit rows in pairs
     (G7 showed rows 1-2, 5-6, 9-10, 13-14) and the picture came out multiplied. Of 16 decoders tried only
     ICN2018/3018 gave one line at G7.
   - G3 "1 display black and 2 display white". G4 "1 darker than 2".
   - G5 colours are rotated (the panels, not the card): State1 = **Green**, State2 = **Blue**, State3 =
     **Red**, State4 Black.
   - G6 **16**. G7 **2** (it shows one line; "1" makes G8 blink whole rows).
   - G8: **Import alignment table** > `hardware/icn2018-guide8-route.csv` (also in the VM's Documents) and
     skip the clicking. By hand: point 1 blinks at row 9 on the top-right panel's first column; the points go
     row 9, row 1 in each column, columns 1 to 64; then the rows: the owner reads each lit pair (2/10, 3/11 ...
     8/16) and you click rows 10 to 16 of column 1. The table is the plain 1/8 layout.
   - After Finish the Brightness Level is back to 8: set it before any Send. **Changing DCLK, Multiple or the
     refresh rate also resets the level to 8 (and the refresh rate)**: check the level before every Send.
9. Check: Test > Screen Test > Grid, horizontal lines, gap 16 = four single rows 16 apart across all panels.
   Receiver Mapping must say 128 x 64 (a card from elsewhere may hold another layout, e.g. 6 x 128x512, and then
   shows no picture at all). With the owner's OK: **Save to Receivers**, **Save to Devices**, Read both back,
   **Save…** the read-back as a `.rcvbp`, `vm get` it, power-cycle the wall and check the picture comes back.
   LED Screen Settings is modal: close it to use the main window (programs, Screen Test is separate).
   Saved on card 2: Level 3 (23% at 960 Hz / x16 / 15.6 MHz).
10. Close LEDVision, `vm stop`, and on the host run the four `tools/wall_pattern.py` checks (`rgb`, `index`,
    `steps --brightness 0.4`, `gamma`; they need CAP_NET_RAW, so the owner runs them with sudo). Photograph
    each with the webcam and write what the wall shows into `hardware.md`.
11. A flicker while LEDVision streams (whole-wall dips of ~8% at ~5 Hz) is its stream from the VM: with "Use
    Net Card" unticked the card holds the frame steadily. Judge flicker only with the Linux sender.
