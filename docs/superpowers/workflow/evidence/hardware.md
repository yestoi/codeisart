# Hardware bring-up: Colorlight 5A-75E and the four P5 panels

**Status (2026-09-29, 15:10): card 2 (the spare) is set up and saved to its flash, and survives a power
cycle; use card 2.** The fix was the row decoder: **ICN2018/3018** (the panels have serial row drivers), not
138 (see "14:00" to "14:53" below). Final settings: `hardware/colorlight-outdoor-p5-2x2.rcvbp`. Card 1 has a
hardware fault of its own and still holds its factory settings (see "13:20"). **The Linux driver
(`show/display/colorlight.py`) does not yet work with this card** (firmware 13.17): it needs the frame layout
of the test sender that worked (which part of that layout matters is not yet isolated), BGR pixel order, and a
fix for noise on the bottom rows (see "15:40"); the `wall_pattern.py` checks `index`, `steps`, `gamma` wait for
that. **The flicker while the card is fed data is a known fault of firmware 13.x**, seen by others under
LEDVision on bare-metal Windows and under Falcon Player; 60 fps is the only input rate judged steady here, on
one run. The review, the next runs at the wall and the routes:
`docs/superpowers/reviews/2026-09-29-flicker/00-path-forward.md`. How to continue the card setup:
`.claude/skills/ledvision-card-setup/SKILL.md`, from the worktree
`/Users/trey/dev/codeisart-ledvision` (branch `ledvision-card1`). Screenshots: `hardware/`.

### Corrections (2026-09-29, evening, from the review of the session records)

The sections below were written during the sessions. A review of the transcript and of the Omarchy box's journal
(`docs/superpowers/reviews/2026-09-29-flicker/05-session-history.md`) found these claims firmer or tidier than
the record. The text below is corrected in place; this list says what changed.

1. **"The flicker is LEDVision's stream from the VM"** (14:25) was not shown. What was shown: the card holds a
   frame steadily when no data arrives. That does not separate "the VM's stream is irregular" from "this card
   dims when packets arrive". Other people see the same flicker with LEDVision on bare-metal Windows.
2. **"every 6 frames (5 Hz)"** (14:25): the phone video's dips are at frames 0, 12, 18, 36, 42 and 66, six in
   3.1 s, about two a second, all on a 6-frame grid but not regular. The laptop camera's 29 dips have gaps from
   3 to 29 frames: the same size of step, not the same rhythm.
3. The phone video with the 8 % dips was taken at **360 Hz / x1 / 10.4 MHz / Level 3**, not at 960 / x16.
4. **The 20 / 30 / 60 fps runs were not on equal terms** (15:40): the 30 fps run had the 1 ms pause before the
   sync, the 20 fps runs did not.
5. **"60 fps: steady"** (15:40) is the owner's verdict on one 10 s run, timed by `time.sleep`, which really ran
   at 59.7 fps. Every later 60 fps run had the pause and got "slight flicker" or "A steadier" (A being the run
   without the pause).
6. **"960 Hz x16 is 60 x 16: the card repeats each frame 16 times and waits for the next"** (15:40) is an
   inference, not a measurement. Against it: LEDVision's stream flickered at 420 / x1 and 360 / x1 too.
7. **"twice compared A/B"** (15:40): three A/B pairs. The first got "Do it again", the next two "A steadier".
   The third changed the timing method (busy-wait) as well as the pause.
8. **"The owner saw no flicker during these runs"** (14:00) was seen on the wizard's test bands, not on a
   streamed picture. The link to the preset timing is an inference.
9. **A measurement was left out** (15:40): the phone video of the 60 fps run with the pause was analysed and
   not reported. It is now in that section.
10. Not tried at all, and so still open: 30 fps without the pause, 20 fps with it, any rate other than 20, 30
    and 60, any pause other than 1 ms, a moving picture (static bars hide lost rows), a packet capture of any
    of our streams.

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

### 13:20: card 2 (the spare) behaves differently from card 1

- The card is powered from the same 5 V supply as the panels (common ground). Card 2 swapped in on the same
  cables and panels. Detect: **5A 13.17** (`hardware/21-detect-receivers-card2.png`). Its settings, read and
  saved as `hardware/card2-factory-before.rcvbp`, are byte for byte card 1's factory file (same sha256;
  `hardware/22-card2-factory-params.png`).
- Sent to its RAM only: `card1-wizard-20260929.rcvbp` at Brightness Level 1, and the 128 x 64 mapping. Unlike
  card 1, it showed no green pattern after the parameter Send.
- Same grid (horizontal, gap 16): each line shows as **2 rows, 4 apart**, the same on all four panels; card 1
  gave 3 to 4 rows spread over ~8 (`hardware/23-card2-grid-horizontal-gap16.png`,
  `hardware/24-card1-vs-card2-same-settings.png`). Same settings, cables and panels, different result: **card 1
  has a hardware fault** on top of whatever remains. The remaining x2 (rows 4 apart) may be the wizard's
  answers, which were all decided while card 1 was fitted (Guide 7's "2", Guide 8's row order).
- The owner still sees the flicker with card 2, so it is not card 1's fault: next suspects are the wizard's
  timing (DCLK 15.6 MHz, Refresh x16, blanking 0) and then the power strip.
- 13:25, wizard rerun on card 2 from the preset (Level 1, 128 x 64, Normal 32 groups, module 64 x 32, map
  checked): Guide 3 and 4 as before; **Guide 5 the same colour rotation** (the card's red shows green, green
  blue, blue red: a panel property, not card 1); Guide 6 16; **Guide 7 again four lines 4 rows apart in the
  top 16 rows** (`shots` only). So the four lines are not card 1's fault either. One address lighting rows k,
  k+4, k+8, k+12 instead of k, k+8 is what address line C being ignored looks like, and card 2's grid (each
  line twice, 4 rows apart) fits the same. What both cards, both chains and all four panels share: the panel
  design, the power supply, the settings. Stopped at Guide 7 to ask the owner.
- The owner, at the wall: Guide 7 lights **rows 1-2, 5-6, 9-10, 13-14** (pairs of rows, 2 dark between;
  the glare makes each pair look solid to the camera, `hardware/25-card2-guide7-rows-1-2-5-6-9-10-13-14.png`).
  That is 8 rows of 16 for one address, where a 1/8-scan panel lights 2 (rows 1 and 9, what Wired Watts'
  guide expects). The lit rows are exactly those whose row address (0 to 7) has **B = 0**, whatever A and C:
  the panels follow address line B (HUB75 pin 10) and not A (pin 9) or C (pin 11). It also explains the
  rest: each Guide 8 "point" was 4 LEDs (rows 9-10 and 13-14; the camera merged neighbours), card 2's grid
  shows each line as 2 rows twice, and floating address inputs flicker.
- Guide 2's Decoding Chip list has ~30 types (`hardware/26-guide2-decoding-chip-list.png`: 138, No Decoding,
  595, 5953/5958, SM5266, SM5366, ICN2013, ICN2018/3018, 7258, LS97xx, TC7261/7239, HX6158H, MBI5981,
  ICND2019, DP32019/20, SM5368/5388, D7266, VOD5958, GM5018, TC6960, MBI5988, SM5166/5188, CFD2138SPC,
  TA6018, ...). Not tried blind: needs the row chip's marking or a measurement first.
- Left at 13:35: wizard cancelled, card 2 RAM holds the preset "14" at Level 1 with 128 x 64 / Normal 32
  groups and the 128 x 64 mapping; Screen Test Gray 0; wall black.
- 13:40, the panel's power corner (`hardware/27-panel-back-power-row-drivers.jpg`): the row drivers are **T2 and
  T3, 10-pin SOP**, blank tops, beside POWER1; not the 16-pin 74HC138/SM5166 that "138 Decoding" assumes.
  (Whether there are more T parts elsewhere on the board is not yet known.)
- 13:45, **"595 Decoding"** tried in Guide 2 (card 2, Level 1, wall powered off and on first, Level 1 and the
  mapping re-sent): Guide 3's state 2 lit **nothing**, where 138 lit the 16-row band. So these panels are not
  595-type (shift register). Wizard cancelled, the 138 preset re-sent.
- Web: a sibling panel, `P5-1921-64*32-8S-S2`, uses row driver **SM5166PF** and column driver **DP5125D**
  (https://github.com/mrcodetastic/ESP32-HUB75-MatrixPanel-DMA/issues/698). Our sticker, `YP5-5125HG505`,
  suggests DP5125D columns too. SM5166 is a 138-type decoder, but in SOP-16. Another P5(1921)64x32-8S
  (https://rpi-rgb-led-matrix.discourse.group/t/p5-1921-64x32-8s/1161) used ICN2037 + HX6016SP (138 type)
  and needed custom pixel mapping. So 138 is the likely right family; what the 10-pin T2/T3 are is still open.

### 14:00: the decoder is ICN2018/3018 (serial row driver)

- Guide 2's Decoding Chip tried one by one on card 2 (Level 1), each run to Guide 7 and photographed:
  four row-pairs (the old fault) with 138, ICN2013, 7258, DP32019; the whole 16-row band solid with SM5166,
  No Decoding IC, HX6158H, SM5266, CFD2138SPC; nothing lit with 595, SM5366, DP32020, SM5368/5388; **one line
  at the top with ICN2018/3018** (`hardware/28-icn2018-guide7-one-line.png`; the owner: "a single line, one
  at the top"). The 10-pin T2/T3 are serial (shift-register) row drivers; fed 138-style addresses they lit
  rows in pairs.
- ICN2018 at Guide 6: still the 16-row band (16). Guide 7 answered "1" (what was seen): Guide 8 then blinked a
  whole row (row 16) from the top-left panel's left edge to the middle of the top-right, with a steady top row
  over the same span; no single point. Answered "2" (1/8 scan, the board's "8S"): the top-left panel shows
  rows 1 and 9, then 8 and 16 (the owner: two blinking rows at 8 and 16), the healthy k / k+8 pair of a 1/8
  panel; nothing blinks on the top-right panel, so Guide 8 still gives no clickable point.
- The owner saw **no flicker** during these runs (preset timing: refresh 420, Refresh x1, DCLK 17.9 MHz); the
  flicker earlier was with the old wizard result (960, x16, 15.6 MHz). These runs showed the wizard's test
  bands, not a streamed picture, so this says nothing yet about the timing: at 420 / x1 a streamed picture
  flickered (see "14:25").

### 14:25: the wall shows a correct picture (card 2, RAM only)

- Guide 8 with ICN2018 and Guide 7 = 2: the owner saw the single point blink at row 9 on the top-right panel
  (the camera had it at the joint, row 8-9, column 1-2). Points walked row 9 / row 1 per column over all 64
  columns (camera checks at columns 1, 9, 25, 35, 49, 64); in the row phase the owner read each lit pair:
  2/10, 3/11, 4/12, 5/13, 6/14, 7/15, 8/16, clicked as rows 10 to 16 of column 1; "Finished". The exported table,
  `hardware/icn2018-guide8-route.csv`, is byte for byte `card1-guide8-route.csv`: the pixel order was right all
  along, the decoder was the fault (`hardware/29-icn2018-guide8-complete.png`).
- After Finish: module 64W x 16H, 8 scan, **Decode IC ICN2018/3018**, Normal chip, cabinet 128 x 64, From Right
  to Left, Normal 32 groups; refresh 960, Refresh x16, DCLK 15.6 MHz, blanking 3; Brightness Level 8, set back
  to 1 and Sent. Saved as `hardware/icn2018-wizard-20260929.rcvbp` (this wizard run skipped Guide 5's colour
  answers).
- Grid, horizontal, gap 16: **four clean single lines** 16 rows apart across all four panels
  (`hardware/30-icn2018-grid-horizontal-gap16.png`). LEDVision's own "LED1" program, text and colour wheels,
  shows correctly placed on all four panels (`hardware/31-icn2018-led1-program-on-wall.png`); colours rotated
  (desktop blue shows red, red green, green blue): Guide 5's answers are still to be put back.
- The owner: "pretty bad flickering" at 960 / x16 / 15.6 MHz. Changing Multiple to x1 reset refresh to 60 and
  the level to 8 (not sent); set refresh 420, x1, Level 1 and Sent (14:28).
- Flicker, still open. The owner: "the image shifts and fidgets" at 420 / x1. A 5 s camera video (30 fps) sees
  no shift in any panel or 16-row band (max 0.4 camera px; one LED is ~4 px) and brightness steady within 1%:
  whatever it is, it is faster than 30 fps. Tried, one at a time, owner's verdict "Same" for both: DCLK 15.6 ->
  10.4 MHz (refresh went to 360); Brightness Level 1 -> 3 (14%, clears LEDVision's "Minimum OE is 0" warning).
  Every change of DCLK or Multiple silently resets Brightness Level to 8 (and the refresh rate): check the
  level before every Send. State at 14:35 (RAM only): ICN2018/3018, DCLK 10.4 MHz, refresh 360, Refresh x1,
  blanking 3, Level 3.
- **The flicker appears only while the card is fed data; the card holding a frame is steady.** (This heading
  first read "The flicker is LEDVision's stream from the VM, not the card, panels or power": see
  "Corrections", 1.) The owner's phone video (3 s, 30 fps), taken at 360 Hz / x1 / 10.4 MHz / Level 3: the
  whole wall dips ~8% darker for single frames, at frames 0, 12, 18, 36, 42 and 66, about two a second, all on
  a 6-frame grid but not regular; evenly over the whole wall, no shift, no missing rows. The laptop camera
  (8 s) sees steps of the same kind, smaller (~3%, std 1.51), 29 of them with gaps from 3 to 29 frames: not the
  same rhythm. With "Use Net Card" unticked (LEDVision stops sending; the card holds the last frame, No Signal
  Action "Keep the Last Frame"): the camera sees a steady wall (std 0.34, no dips in 241 frames) and the owner:
  "the image is stable now". This clears the panels' refresh and the supply at that load. It does not say
  whether the VM's delivery or the card's handling of arriving packets is at fault; the later review found the
  same flicker reported for firmware 13.x with LEDVision on bare-metal Windows, which points at the card.

### 14:50: colours fixed, a test image on the wall (card 2, RAM only)

- Wizard rerun with ICN2018/3018: Guide 5 again showed the rotation (state 1 green, 2 blue, 3 red), answered
  Green / Blue / Red / Black; Guide 6 16, Guide 7 2; Guide 8 by **Import alignment table**
  (`icn2018-guide8-route.csv`), no clicking. After Finish: refresh 960, Refresh x16, DCLK 15.6 MHz, blanking 3;
  Level set to 3 (23% at these timings) and Sent. Saved as `hardware/colorlight-outdoor-p5-2x2-draft.rcvbp`
  (not yet on the card's flash).
- LEDVision program: Normal Page > File Window, full screen 128 x 64 > a 128 x 64 Mandelbrot PNG (effects None).
  On the wall in the right colours, placed and scaled right (`hardware/32-mandelbrot-colours-fixed.png`).
  Reopening LED Screen Settings put the adapter back on the NAT NIC; "Use Net Card" then unticked: the card
  holds the image, camera steady (std 0.45, no dips in 181 frames). The owner: "everything is aligned and
  looks great".

### 14:53: card 2 saved (owner's OK)

- With the owner's explicit OK: Receiver Parameters > **Save to Receivers** ("Save parameters to receivers
  complete!") and Receiver Mapping > **Save to Devices** ("Save mapping to devices successfully!").
- Read back from the card: mapping 1 x 1, receiver 1 = 128 x 64 (`hardware/33-card2-mapping-read-back.png`;
  it was 6 x 128x512); parameters 64W x 16H, 8 scan, Normal chip, ICN2018/3018, 128 x 64, From Right to Left,
  Normal 32 groups, refresh 960, Refresh x16, DCLK 15.6 MHz, blanking 3, Level 3 (23%), gamma 2.8
  (`hardware/34-card2-params-read-back.png`). Saved from the read-back as
  **`hardware/colorlight-outdoor-p5-2x2.rcvbp`** (sha256 `98c3c490…35bd`).
- It differs from the draft file sent (`colorlight-outdoor-p5-2x2-draft.rcvbp`) in 10 bytes: three fields read
  32/32/128 where the draft has 16/16/64 (0x18e, 0x194, 0x19c; the factory file also has 32/32/128), 0x204
  255 vs 0, and a six-byte table at 0x599f with bit 6 cleared in every other byte. Not decoded; no setting the
  dialog shows differs. The power-cycle test settles whether the flash holds a working setup.
- Card 1 is left on its factory settings; it has a hardware fault (see "13:20").
- **Power-cycle test passed (~14:57):** after the owner's power reset the card (run time 0:12:28 at 15:09, so
  booted after the save) showed LEDVision's Mandelbrot correctly: colours, rows, position
  (`hardware/35-after-power-cycle.png`). The flash holds a working setup.
- Flicker while streaming: FPP issue #1849 (https://github.com/FalconChristmas/fpp/issues/1849) had FPP 7.5 fail
  on firmware 13.17 (symptoms not given; fixed by going back to 11.04), and FPP sends its 0x0A brightness
  packet twice on firmware 13+. `show/display/colorlight.py` sends 0x0A every 3 pushes (10 Hz at 30 Hz): if
  the Linux sender's picture dips at that rhythm, send it less often before thinking of firmware.

### 15:40: the Linux sender (card 2, flash settings, from the Omarchy box)

- LEDVision closed, `vm stop`; the code copied to `~/Work/codeisart-wall` on the Omarchy box with its own uv
  venv (numpy, Pillow, pyte). The owner enabled passwordless sudo for an hour so the agent could run tests.
- **`wall_pattern.py rgb` (show/display/colorlight.py) did not reach the wall**: LEDVision's last frame (the
  Mandelbrot) stayed up and flashed hard. The driver's packets are byte for byte FPP's; the difference is
  FPP's firmware-13 handling: per frame brightness packet (x2 on firmware >= 13), the rows, then the sync
  (show-frame) packet; the driver sends sync, brightness (every 3rd push), rows, once each.
- A throwaway sender with FPP's order (`hardware/cl_fpp_test.py`, packets checked identical to the driver's)
  put R/G/B/W bars on the wall. One variable at a time, 10 % brightness, the owner judging:
  - 20 fps, no pause before the sync: bars, fast flicker. Brightness 23 % (the card's own level) instead of
    10 %: same flicker.
  - **60 fps, no pause: steady**, one 10 s run, timed by `time.sleep`, really 59.7 fps (597 frames). Why 60
    is not known: that the saved timing (960 Hz x16) is 60 x 16 is a guess (see "Corrections", 6).
  - 30 fps (the arcade's rate) **with the 1 ms pause**: some flicker. Not comparable with the 20 fps run,
    which had no pause; 30 fps without the pause and 20 fps with it were not tried. The show pushes 20 fps,
    the arcade 30.
  - At 60 fps the **last row or two of the wall showed noise**; a 1 ms pause between the last row and the
    sync cleared it but brought back a slight flicker. Three A/B pairs (A without the pause, B with): "Do it
    again", "A steadier", "A steadier"; the third pair's B also used busy-wait timing, exactly 60.0 fps. No
    clean-and-steady combination yet.
  - The owner's phone video of a 60 fps run with the pause (IMG_5080.mov, frames 0 to 133): median 110, range
    106 to 114, std 1.58; seven frames 3 to 4 below the median, no rhythm; no 8 % dips, no rolling band. The
    phone's auto exposure was not locked. (Analysed during the session, left out of the log until the review.)
  - **Pixel order: sent R, G, B, W left to right, the wall showed Blue, Green, Red, White** (not a mirror):
    the card takes raw pixels as **BGR** (as in Kubota's notes). LEDVision's picture was right because its
    Guide 5 answers apply to its own stream only (`hardware/36-linux-bars-bgr-order.png`).
  - Sync twice vs once: with the old ending (3 black frames at 20 fps) the wall kept a stale picture (top
    bars / all bars); ending with 1 s of black at 60 fps clears it. The card seems to need a steady stream to
    change picture; sync x1 vs x2 not settled.
- For the driver (shared show/arcade code, not changed here): the test sender's frame layout (brightness x2,
  rows, sync x2), of which the needed part is not isolated; BGR order (measured); the bottom-row noise; and,
  if the next runs at the wall bear out the one steady run, a 60 Hz output independent of the content rate
  (resend the last frame). `index`, `steps`, `gamma` wait for that. The runs that settle these, and the order
  of the driver work: `docs/superpowers/reviews/2026-09-29-flicker/00-path-forward.md`.

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
