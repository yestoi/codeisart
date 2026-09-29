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
7. Load > Preset Parameters > General Parameters (Fullcolor) > **14- full-color eight scan**. Data Group
   **Normal 32 groups**. Cabinet **128 x 64**, cascade From Right to Left. Intelligent Module Setting: module
   width **64**, height **32** (the boxes are read-only: each Modify button opens a list); its map must show
   J1 = top row (1-1 top right, 1-2 top left) and J2 = the bottom row. If the card can only be mapped as one
   chain of 256x32, stop and tell the owner. Then **Brightness Level 1** and **Send** (Yes to "Minimum OE is 0":
   it costs the darkest grey step, not the mapping).
8. Intelligent Setting wizard, watching the **top-right** panel (first on J1). Answers, checked on the wall
   on 2026-09-28 and again on 2026-09-29 (they are still not gospel):
   - G1 Single Type Module. G2 module width **64** (it opens at 32), 138 decoding, Normal 32 groups, output J1.
     G2 lights rows 1 to 16 of both top panels.
   - G3 "1 display black and 2 display white". G4 "1 darker than 2".
   - G5 colours are rotated: set State1 = **Green**, State2 = **Blue**, State3 = **Red**, State4 Black
     (what the wall shows for each). This is where the card's pixel order becomes RGB.
   - G6 **16** (the lit band is rows 1 to 16, measured on the photo at 5.7 px a row).
   - G7 **2**: four lines light, rows 1-2, 5-6, 9-10 and 13-14, each **two rows thick**. The question is how
     many rows one line covers, not how many lines there are ("4" left G8 dark on 2026-09-28).
   - G8 at the start: the top-left panel keeps G7's four lines lit, and the point on the top-right panel blinks.
     **Where point 1 is, is not settled.** The 2026-09-28 notes say row 9, column 1, then row 1, column 1, then
     column 2 and so on to column 64. On 2026-09-29 the owner saw point 1 on the far-right column of the
     top-right panel. Find it with `--flash` and ask the owner to confirm the first two points before clicking;
     then click where each point is, checking with `--flash` every 8 to 16 points.
   - G8 rows: **not solved yet.** After the 128 points each step lit four rows 4 apart (3/7/11/15, then
     2-3/6-7/10-11/14-15, then 4/8/12/16 twice); clicking the topmost lit row stalled it. Those may have been
     lines like G7's, not single rows. Plan: after the 128 points, click rows 10, 11, 12, 13, 14, 15, 16 in
     column 1 (Wired Watts' order), Finish; then Send and check with Test > Grid Test through the camera. Rows
     out of order: repeat mapping by what the camera shows, one step at a time, and stop at the second failure.
9. When the wall looks right to the owner: close the wizard, **Send**, then with the owner's OK **Save to
   Receivers**; **Save…** as `colorlight-outdoor-p5-2x2.rcvbp`; `vm get` it into the evidence folder. Put the
   Brightness Level the show needs back before Save to Receivers, and ask the owner which that is.
10. Close LEDVision, `vm stop`, and on the host run the four `tools/wall_pattern.py` checks (`rgb`, `index`,
    `steps --brightness 0.4`, `gamma`; they need CAP_NET_RAW, so the owner runs them with sudo). Photograph
    each with the webcam and write what the wall shows into `hardware.md`.
11. Card 2 (spare): swap the card (same cable), steps 1 to 6, then Load > Browse the saved `.rcvbp`, Send,
    check, Save to Receivers with the owner's OK, Read back and compare.
