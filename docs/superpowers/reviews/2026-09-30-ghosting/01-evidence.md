# Lane 01: the evidence. What was observed, and the owner's photos and videos measured again

Date: 2026-09-30. Read-only: nothing was sent to the wall or the card, no repo file was changed but this one.
Labels: CONFIRMED (a primary source or my own measurement, with how), LIKELY, SPECULATIVE. "Recorded" means
as the camera recorded it, which for brightness is not the same as true (section 3.2).
Scratch folder, with every script and every picture named below:
`/private/tmp/claude-502/-Users-trey-dev-codeisart/489bd663-dd66-40f0-8952-22058687bf7d/scratchpad/01-evidence/`

Words used: a panel's 32 rows fall into four **groups** of 8 rows (wall rows 0-7, 8-15, 16-23, 24-31, then
32-39 and so on). Within a group, row r is on **scan line** k = r mod 8. "The copy is on line k+4" means: the
light meant for row r also shows in the same column, in the same group, on the row whose scan line is
(k + 4) mod 8. For k = 0..3 that is 4 rows below; for k = 4..7 it wraps and is 4 rows above.

## 0. Verdict in short

1. **Where the copy lands (saved settings, 960 Hz x16): on scan line k+4 or on scan line k+5 of the same
   8-row group, same column, and it switches between the two in time.** CONFIRMED, by registering all 105
   frames of the first video (IMG_5083) to the LED grid. In 58 frames every copy on the wall is on line k+4,
   in 38 frames every copy is on line k+5, 9 frames are mixed. It wraps inside the group and never leaves it:
   it does not cross a group, a 16-row half, or a panel. No sideways shift.
2. **Both readings in the brief are half right, because each was read off a different state.** Reading (b)
   (4 below for lines 0..3, 4 above for lines 4..7) is exactly the k+4 state. The "3 above" of reading (a) is
   the k+5 state's wrap (lines 3..7 land 3 above, lines 0..2 land 5 below); the enlarged frame the last
   session used (frame 50) is a k+5 frame. Reading (a) as written (4 below and 3 above in the same instant) is
   not what the wall does. CONFIRMED.
3. **The switching has a rhythm: three video frames (k+4, k+4, k+5, repeating), in step on all four panels.**
   CONFIRMED in IMG_5083 (the arcade run, x16). What sets the rhythm cannot be told from a 30 fps phone: a
   cycle of three of the card's frames, or the arcade's pose thread at 10 a second on the Pi, would both look
   like this. No x16 video without the arcade exists.
4. **At Refresh x4 the geometry is different: every lit row is copied to line k+1 AND to line k+5**, in every
   frame, with no switching. CONFIRMED (IMG_5091, all 111 frames, and the still fba75423). The last session's
   "34 to 35 px below (about 4 rows)" is 5 rows, plus a third bright row directly under each two-row line. So
   the offset is not fixed by the panel's wiring: it moves with a card timing setting.
5. **The first 8 rows of each panel (wall rows 0-7 and 32-39) show no copy** at x16, in either state, where
   the picture allows a clean test (the copies that would wrap upward into rows 1-3 and 33-35). CONFIRMED.
   Every other group copies alike, about equally in all four panels and along a line.
6. **No brightness ratio from these pictures can be trusted.** CONFIRMED: every lit LED's centre is at the
   sensor's ceiling, even the lines at pixel value 64, and an unlit LED's face in that daylight already reads
   80 % of the ceiling. The session's 0.74, 0.85, 0.91 are the ceiling, not the wall. The copy "looking
   redder" is the same effect (the source's red clips and turns orange in the camera; the copy clips less).
7. **"None at 64, a trace at 128, plain at 255" does not prove a steep, value-dependent cause, and does not
   prove a fixed fraction either.** At x16 the one picture with all three levels puts the copy at 128 at
   about 1 % of its line or less (if the card's gamma is 2.8); the copy at 255 is then 2 to 4 times stronger
   than a fixed fraction would make it, or more, but this rests on one tone-mapped screenshot. LIKELY: grows
   somewhat faster than the light; not settled.
8. **The x4 "contradiction" is not one.** The lobby "photographed clean" at x4 is a still photo: a slice of a
   few milliseconds (the same kind of photo of the lines shows a copy cut off mid-row). It does show the x4
   fault (arms smeared to 5 or 6 rows, wrapped dots). At x4 the copy is there at all three values, and at 64
   it is at least 4 to 6 times stronger against its line than at x16. CONFIRMED. x4 is worse, not better.
9. `--brightness 0.1` is a level byte (25) in the sync and brightness packets; the pixel bytes reach the card
   unscaled. CONFIRMED in the code (section 6). Pixel value 255 is 255 at the card.

## 1. The record: every observation of the second picture

Sources: `hardware.md` lines 295-349 (branch `ledvision-card1`, uncommitted), the route A bench report
`00-bench.md` lines 239-294, and the media's own time stamps (ffprobe, file metadata).

| # | Time | Sender | Picture | Card settings in force | Sender brightness | Judged by | Result as recorded |
|---|---|---|---|---|---|---|---|
| 1 | 09:36-09:42, video 09:40:51 | Pi 5, the arcade bench script | the lobby: figure (255,120,0), small figure (0,199,0) | flash: 960, x16, blanking 3, Level 3 (23 %) | 0.1 | video IMG_5083 (105 frames); the owner's eye ("I see it by eye") | "a dimmer, redder copy of its arms and legs, a few rows lower, the same in every frame" |
| 2 | 09:50-10:07 | LEDVision in the VM, from the Omarchy box | LEDVision's grid: white single rows, gap 16, paused | read back as saved: 960, x16, 15.6 MHz, blanking 3, Level 3 | LEDVision's own (not recorded) | eye only | "the fainter copy under each line here too" |
| 3 | same | same | same | Blanking Value 6 | | eye | "looks the same, may be weaker" |
| 4 | same | same | same | Blanking Value 11 | | eye | "still the same" |
| 5 | same | same | same | Blanking Enhancement on | | eye | "still the same" |
| 6 | same | same | same | Blanking Voltage 2.0 V | | eye | "still the same" |
| 7 | same | same | same | Blanking Voltage 3.75 V | | none | not judged; trial stopped |
| 8 | 10:16 | Pi 5, `ghost_test.py 1` | the lobby's frame, still, label 1 | RAM set back to the flash values at 10:07 | 0.1 | eye; "photographed" | "the second picture is there" |
| 9 | 10:16 | `ghost_test.py 2` | the same sliding 10 px a second | same | 0.1 | eye | "there" |
| 10 | 10:16 | `ghost_test.py 3` | white bar at 128 sweeping in a border | same | 0.1 | eye | "smooth, no ghosting" |
| 11 | 10:16, screenshot 10:19:46 | `ghost_test.py 4` | two-row lines at 64, 128, 255, orange rows 16-17, white rows 40-41 | same | 0.1 | the owner's photograph (a4192b69) | "none under the 64s, a trace under the 128s, a plain copy under the 255s, 4 rows down" |
| 12 | 10:25-10:40 | LEDVision | its grid | RAM: 480, x8, Level 3 (25 %) | | eye | no verdict ("try x4") |
| 13 | same | LEDVision | its grid | RAM: 240, x4, Level 3 (26 %) | | eye | "I think it is better. I will have to try it on the rpi" |
| 14 | about 10:34 | Pi 5, `ghost_test.py 1` | the lobby's frame, label 1 | RAM: x4 (no power cycle) | 0.1 | a still photo (c2636b4a) | "no second picture under the arms or along the legs" |
| 15 | 10:36:44 | Pi 5, `ghost_test.py 4` | the level lines | RAM: x4 | 0.1 | video IMG_5091 (111 frames), a still (fba75423) | "a second line under the 128 and the 255 lines ... 34 to 35 px below (about 4 rows) ... 0.74, 0.85, 0.91 of the line above" |
| 16 | 08:28-08:36 | Pi 5, `wall_pattern.py grid`, `border` | white at 128 | flash | 0.1 | eye, one photo (33cd9f46) | "Looks good", "Looked great": nothing said of a copy |

Observations and inferences, kept apart:

- OBSERVATIONS (rows above): 1, 2, 8, 9, 11, 15 are positive sightings; 10 and 16 are "clean" by eye at 128;
  3 to 6 are "no change by eye"; 14 is a still photo only, with no verdict by eye on record.
- INFERENCES of the last session, none tested: (i) row ghosting from Blanking Value 3 (bench line 242; its
  cure was tried and failed, rows 3-6); (ii) the copy is on "the row lit next" in an order 0,4,1,5,2,6,3,7
  (hardware.md line 318); (iii) the steep growth with value points at the grey-scale timing (bench line 281);
  (iv) x4 made one picture cleaner and the other worse (hardware.md line 345).
- What this lane finds of them: (ii) is wrong as stated (section 2); (iii) is not supported by the pictures
  either way (section 5); (iv) is a camera effect plus a real change of geometry (sections 2.4 and 3.2).

Contradictions and confounds in the record:

1. **Row 14 against row 15 (x4).** One is a still photo, the other a video; they are not comparable
   (section 3.2). CONFIRMED: the still of the lines (fba75423) shows the white 128 line's copy on row 45 only
   from column 64 rightwards and on row 46 only from column 59 rightwards: a time edge of the phone's rolling
   shutter, which in a portrait shot sweeps across the columns. A still says which LEDs were lit in a few
   milliseconds, not what the eye sees.
2. **"About 4 rows" at x4 (row 15) is 5 rows**, and the line itself is three rows thick at x4 (section 2.4).
   The last session measured the distance in pixels from the middle of three bright rows.
3. **The x16 "photographs" are phone screenshots.** CONFIRMED: `9a8f1211` and `a4192b69` are 1206 px wide,
   144 dpi, with the description "Screenshot" and the times 10:19:05 and 10:19:46. They are resampled 8-bit
   pictures of a picture. `9a8f1211` has no label 1 or 2 in its bottom right corner and the same cropping as
   IMG_5083: it is the arcade's lobby, not `ghost_test.py`'s picture 1. No photograph of picture 1 at x16
   is in the evidence folder.
4. **Exposure is unknown and was not locked.** The three full-size stills have no EXIF at all (stripped on
   the way). The videos are 30 fps HLG (Dolby Vision 8.4), portrait, with the phone's "ambient 314 lux" tag.
5. **Brightness Level.** Every change of Blanking Value, DCLK or Multiple sets it to 8; the log says it was
   set back to 3 before every Send. Level 3 is 23 % at x16, 25 % at x8, 26 % at x4, so the three multiples
   were not at quite the same light. Small.
6. **Two brightness controls at once.** From the Pi the card gets level byte 25 (section 6) on top of its own
   Level 3. LEDVision's grid ran at LEDVision's own brightness, which the log does not give. The eye
   judgments at LEDVision and from the Pi were made at different light.
7. **The LEDVision judgments (rows 2-7, 12-13) were by eye on a stream known to flicker**, against a copy that
   I find switching rows several times a second (section 2.3). "Looks the same" is weak evidence that the
   blanking settings do nothing, and "I think it is better" at x4 is contradicted by the video (row 15).
8. **Arcade or not.** The only x16 video (row 1) is the arcade run, with the pose model working at 10 a
   second on the Pi. The only video without the arcade (row 15) is at x4. The switching (section 2.3) is
   seen in the first and not in the second, so its cause is confounded between "x16" and "the arcade".
9. **Card RAM.** For rows 8-11 the RAM had been sent the flash values after the blanking trials (hardware.md
   line 324), not power cycled. For rows 14-15 it held x4. As the log says, it still holds x4 until a power
   cycle or a Send.
10. **Row 10 and row 16 (clean at 128) are by eye only.** The 08:31 photo of `grid` is too small (5 px an
    LED) to show a trace; I could not confirm or refute a copy in it.

## 2. Geometry

### 2.1 Method

The unlit LEDs show as a lattice of dots. For every frame I find the dots (about 18 000 a frame), grow a
lattice through them inside each panel, fit one homography per panel (median residual 0.2 to 0.3 px at 8 to
9 px an LED), and fix the absolute row and column from the panel's own edges (each panel has exactly 32 rows
and 64 columns of dots) and, for the x16 pictures, from the best match of the frame that was sent
(`lobby.png`, `ghost-4.png`). Both agree in every x16 picture used for a number here. At x4 they disagree
(the brightest rows are not the rows that were sent), so the x4 pictures are anchored by the panel edges
alone and checked by eye
(`frames/edge-fba75423-all.png`, `frames/lines-f10-TR-edge.png`). Then each of the 128 x 64 LEDs is read as
the mean of a small disc at its place. Scripts: `lattice.py`, `wallmap.py`, `run_lobby_all.py`,
`run_lines_all.py`, `photo.py`. CONFIRMED means measured this way.

The first video cuts off the wall's left 8 columns; nothing of the picture is there.

### 2.2 The saved settings (960 Hz, x16): the copy is on line k+4, or on line k+5

IMG_5083, 105 frames, the arcade's lobby. Each frame was classed by two clean places far apart (the left
arm in the top left panel, the right leg's steps in the bottom right). In 96 of 105 frames both agree.

Fit over all LEDs that are dark in the frame sent (about 5 400), with the camera's glow around lit LEDs
fitted alongside (`fit_states.py`). Level of a copy on scan line k+d of the same group, as a share of the
recorded source level, for rows 8-31 of each panel:

| State | d=1 | d=2 | d=3 | d=4 | d=5 | d=6 | d=7 |
|---|---|---|---|---|---|---|---|
| "k+4" (58 frames) | 0.00 | -0.02 | -0.04 | **0.49** | -0.01 | 0.00 | 0.01 |
| "k+5" (38 frames) | 0.01 | 0.00 | 0.00 | -0.02 | **0.47** | -0.01 | 0.00 |

Standard errors 0.005; the small negatives are the glow model's error. CONFIRMED: in each state the copy
is on one line only.

Per source row, the k+4 state (the averaged fit of `fit_lobby.py`; "up" means the copy wrapped above its
source). Every source row the picture offers outside the first 8 rows of a panel:

| Source row y | k | 16-row half | Copy row | Offset | Seen (clean pixels) |
|---|---|---|---|---|---|
| 8, 9, 10, 11 | 0, 1, 2, 3 | top panel, upper | 12, 13, 14, 15 | +4 | yes (10, 31, 52, 34) |
| 12 | 4 | top panel, upper | 8 | -4 | yes (6) |
| 16, 17 (green figure's feet) | 0, 1 | top panel, lower | 20, 21 | +4 | yes, in green |
| 40, 41, 42, 43 | 0, 1, 2, 3 | bottom panel, upper | 44, 45, 46, 47 | +4 | yes (10, 10, 7, 3) |
| 44, 45, 46, 47 | 4, 5, 6, 7 | bottom panel, upper | 40, 41, 42, 43 | -4 | yes (4, 5, 3, 2) |
| 48, 49, 50, 51 | 0, 1, 2, 3 | bottom panel, lower | 52, 53, 54, 55 | +4 | yes |
| 52, 53, 54, 55 | 4, 5, 6, 7 | bottom panel, lower | 48, 49, 50, 51 | -4 | yes |
| 56, 57, 58, 59 | 0, 1, 2, 3 | bottom panel, lower | 60, 61, 62, 63 | +4 | yes |
| 60, 61, 62, 63 | 4, 5, 6, 7 | bottom panel, lower | 56, 57, 58, 59 | -4 | yes |
| 5, 6, 7 (shoulder), 4, 5 (green head) | 4..7 | top panel, first 8 rows | 1, 2, 3 (0, 1) | would be -4 | **absent** |
| 37, 38, 39 (hip line) | 5, 6, 7 | bottom panel, first 8 rows | 33, 34, 35 | would be -4 | **absent** |

In the k+5 state the same rows copy one line later, still wrapping inside the group: 9, 10 go to 14, 15;
11 goes to 8 (three above); 12 goes to 9; 40..42 go to 45..47; 43..47 go to 40..44; and so on.

The brief's question, settled for the saved settings: **for source rows with k = 4..7 the copy is 4 rows
above in the k+4 state (reading b) and 3 rows above in the k+5 state; never both at once.** In the k+4
state a copy "3 above" fits at -0.015 +- 0.007 of the source: absent. The "one-row copy just above" the arm
in the last session's enlarged frame (`arm.png`, frame 50) is row 11's copy on row 8 in the k+5 state.

Also CONFIRMED:

- **No crossing.** A copy 4 below a k = 4..7 source (which would cross into the next group, or the next
  half at rows 15|16 and 47|48) fits at 0.02 +- 0.005; 4 above a k = 0..3 source at 0.01; 8 above or below
  (the other row of the same scan line) at 0.01. All nil. Rows 31|32 (the panel boundary) carry only
  vertical strokes, so the picture cannot test that one directly.
- **No sideways shift.** One column left or right of the copy: -0.05 and -0.03 (nil).
- **Vertical strokes.** Their copies fall in the same column, so on the stroke itself; nothing separate can
  be seen along a vertical stroke. At a stroke's end the copy shows: the right leg starts at row 44, and
  rows 40 and 41 above it are lit in its columns (87, 88).
- **The first 8 rows of each panel do not copy** (rows 0-7 and 32-39). Fitted level there 0.00 to 0.04 at
  every offset, in both states. The clean cases are the upward wraps in the table; whether rows 0-3 copy
  down onto rows 4-7 cannot be read in this picture (the head fills those rows). The second, third and
  fourth groups of a panel all copy. I have no explanation; it is a fact for the other lanes.
- Pictures: `lobby-x16-f48-arm-state-k4.png`, `lobby-x16-f50-arm-state-k5.png` (the same arm two frames
  apart), `lobby-x16-f48-leg-state-k4.png`, `lobby-x16-f50-leg-state-k5.png`, `lobby-x16-f48-hip-state-k4.png`
  (the hip line at rows 37-39 with nothing above it, the steps at rows 40-43 with their copies below),
  `lobby-x16-map-state4.png` and `lobby-x16-map-state5.png` (the whole wall as measured: grey is the frame
  sent, red the light that is not in it, the lines mark the 8-row groups).

The level lines at x16 (the screenshot a4192b69, one instant, `ghost_test.py 4`, no arcade): the orange 255
line (rows 16, 17) has its copy on rows 20, 21, the white 255 line (rows 40, 41) on rows 44, 45: the k+4
state. The label "4" copies the same way, wrapping: its row 59 on row 63, its row 55 on row 51. CONFIRMED
(`lines-x16-shot-orange255.png`, `lines-x16-shot-white255-and-label.png`). The lines are two rows thick,
as sent.

### 2.3 The switching

State of each of the 105 frames of IMG_5083, read at the left arm (4 = k+4, 5 = k+5):

```
445445445445445445455445445545445445445445445455455445454445445444445445445455445445555545454454545545445
```

- CONFIRMED: a three-frame rhythm (strongest period exactly 3 frames, that is 10.0 Hz as a 30 fps camera
  samples it; autocorrelation +0.4 to +0.5 at lags 3, 6, 9 ...), 61 frames k+4 and 44 frames k+5 at that
  place, with a slip about once a second. The four panels change together (both chains, both ends of each chain).
- CONFIRMED: in frames 22, 52 and 82 (exactly 30 frames apart) part of the right-hand side shows **no copy
  at all**, and in frame 96 part of the bottom (`lobby-x16-f22-whole-wall.png`). Thirty frames is one second,
  which is the beat between the phone's 30 fps and the sender's 59 fps: the phone then catches the same
  short moment of the sender's frame each time. So there is a moment in the card's frame cycle without the
  copy. What moment, the phone cannot say.
- What the rhythm is: a 30 fps camera cannot tell 10 Hz from 20, 40, 50 Hz and so on. Two candidates fit and
  the media cannot tell them apart: a cycle of three frames inside the card (SPECULATIVE), or something the
  arcade run does ten times a second on the Pi, which is the rate its pose model was asked for (bench report,
  line 237) (SPECULATIVE). LIKELY: a state lasts at least as long as the phone takes to read one frame (the
  state is the same across the whole width in 96 of 105 frames), so this is not a per-refresh (960 Hz)
  alternation.
- The eye averages the two states: two faint rows under a line, the nearer one stronger. That is what the
  time-averaged fit shows (k+4 at 0.39, k+5 at 0.13 to 0.16 of the recorded source).

### 2.4 Refresh x4 (240 Hz): lines k+1 and k+5 together

IMG_5091 (111 frames, `ghost_test.py 4`, no arcade) and the still fba75423. CONFIRMED:

| Sent | Lit on the wall |
|---|---|
| orange line, rows 16, 17 (k = 0, 1) | rows 16, 17, **18**, and rows **21, 22** |
| white line, rows 40, 41 (k = 0, 1) | rows 40, 41, **42**, and rows **45, 46** |
| label "4", row 55 col 124 (k = 7) | also row 48 (k+1, wrapped) and row 52 (k+5, wrapped) |
| label "4", row 59 cols 121-125 (k = 3) | also row 60 (k+1) and row 56 (k+5, wrapped) |
| label "4", rows 56, 57, 58 | also rows 57, 58, 59 (k+1) and rows 61, 62, 63 (k+5) |

Every extra LED of the label is accounted for by "line k+1 and line k+5, wrapping inside the 8-row group",
and none by k+4 (`lines-x4-f10-white255-and-label.png`, `lines-x4-f10-orange255.png`). All 111 frames are
alike: no switching at x4 (only a small dip once a second, the same 59-against-30 beat).

The still of the lobby at x4 (c2636b4a), which the record calls clean: its arms are 5 to 6 rows thick (rows
8 to 13 lit where rows 9 to 12 were sent), and it has lone lit dots that are wraps: (row 40, cols 50-51) and
(row 40, cols 87-88) from row 47; (rows 48-49, cols 41-42) from row 55; (rows 56-57, cols 30-32) from rows
62-63; (row 48, col 124) from the label's row 55. That is lines k+1 and k+2 in that instant, and no k+5.
CONFIRMED as to which LEDs are lit; a still is a time slice (section 3.2), so it does not show the average.

**So the copy's offset depends on the refresh multiple: k+4 (or k+5) at x16, k+1 and k+5 at x4.** A copy
made by the panel's wiring alone (two row chips mirroring each other, a fixed scan order) would not move
when a card timing setting changes. CONFIRMED as an observation; what it means is the other lanes' work.
Not known: x8 (no picture was taken), and whether the first 8 rows are exempt at x4 too.

## 3. Strength

### 3.1 What can be said

- **Rank only.** At x16 the copy reads less than its source in every frame and place: in either state, a
  copy LED reads about 0.65 to 0.75 of a source LED in the disc mean (0.47 to 0.49 after the glow of
  neighbours is fitted out). Both are clipped at the centre (peak code values: unlit LED 0.96, copy 1.05,
  source 1.10 to 1.19, where the sensor's ceiling is about 1.0 for white and up to 1.2 for saturated red).
  **The ratio is unusable**; the true ratio is lower, by an unknown factor. CONFIRMED.
- **Each colour copies.** The white 255 line's copy is white: red, green and blue excess 0.64, 0.67 and 0.72
  of the source's in the x16 screenshot. The green figure (0,199,0) has a green copy. CONFIRMED.
- **The redder copy.** The source (255,120,0) is, in light, red plus 12 % of full green (0.47 ^ 2.8 = 0.12).
  In the camera its red clips (code 1.10 to 1.19) and the green does not, which turns it orange-yellow; the
  copy clips less and keeps its hue. LIKELY the whole explanation. I could not test whether the green
  channel (value 120) copies less than the red (255) would predict: in this camera's colour space added red
  light LOWERS the green and blue readings (a copy LED reads green 0.29 where an unlit LED reads 0.34), so
  the green of a red-lit LED cannot be measured. A white-and-colour test picture would settle it (section 7).
- **x16 against x4, same picture, same method** (disc means above the local background, the orange line's
  red and the white line's green; "clip" marks readings whose LED centres are at the ceiling):

| Line | x16 source | x16 copy (rows +4) | x4 source | x4 row k+1 | x4 copy (rows +5) |
|---|---|---|---|---|---|
| orange 64 | 0.25 | 0.00 +- 0.01 | 0.36-0.43 | 0.16 | 0.11 |
| white 64 | 0.23 (clip in green) | 0.006 +- 0.006 | 0.43-0.45 (clip) | 0.09 | 0.08 |
| orange 128 | 0.44 (clip) | 0.01 +- 0.01 | 0.65-0.83 (clip) | 0.50-0.52 (clip) | 0.38-0.46 (clip) |
| white 128 | 0.23-0.36 (clip) | 0.020 +- 0.006 | 0.42-0.48 (clip) | 0.24-0.29 (clip) | 0.24-0.29 (clip) |
| orange 255 | 0.52 (clip) | 0.36 (clip) | 1.0-1.2 (clip) | 0.89 (clip) | 0.81-0.86 (clip) |
| white 255 | 0.26-0.42 (clip) | 0.17-0.27 (clip) | 0.49 (clip) | 0.38 (clip) | 0.41-0.44 (clip) |

  The x16 column is an 8-bit phone screenshot, linearised as sRGB; the x4 column is the 10-bit HLG video,
  linearised by the HLG curve. The two columns are different cameras' worth of processing and their numbers
  are not to be compared with each other in absolute terms; within a column they are.
- What the table does settle: at 64, x16 has no copy (under 0.04 of the line's reading) and x4 has one at
  0.17 to 0.27 of the line's reading, so **at 64 the x4 copy is at least 4 to 6 times stronger against its
  line than the x16 copy**. CONFIRMED. At x4 the copy is there at all three values.
- At x4 the orange 64 line's copy is not orange: its green reads as much as its red (0.125 against 0.107),
  where the source's red is 2.3 to 2.7 times its green. It looks yellow-green in the frame
  (`lines-x4-f10-orange64.png`). LIKELY real (the green channel at value 32 copying as strongly as the red
  at 64), which would mean the x4 copy does not scale with the value at the low end; but the colour of a
  single small LED in 4:2:0 video is not reliable, so not CONFIRMED.

### 3.2 How far a phone photo can be trusted

- **For geometry: fully**, if the LED dots are resolved (5 px an LED is too few, 8 px is enough) and the
  anchoring is by the panel edges. A lit LED in a photo was lit.
- **For brightness: not at all, in these.** The room is in daylight; an unlit LED's white face reads 0.32 to
  0.44 of full scale in the disc mean and 0.80 at its peak. There is one fifth of the range left above it,
  and every lit LED fills it. The white lines at 64, 128 and 255 read the same peak (1.015, 1.03, 1.03);
  their true light is 1 : 7 : 48.
- **A still is a time slice.** The panel is lit one scan line at a time and the phone's exposure in that
  light is short; its rolling shutter runs across the columns in a portrait shot. A still can show a row lit
  over half its length, or miss a copy that is there.
- **The 30 fps video is steady frame to frame** (2 to 4 % spread on a row's level at x4), so each frame does
  integrate over several refreshes. It samples the card at 30 a second, so anything periodic in the card is
  aliased (section 2.3).
- **Colour of single LEDs is unreliable**: chroma is stored at half resolution, and the HLG/BT.2020 matrix
  gives negative green and blue for a saturated red LED.
- The x16 "photos" are screenshots, tone-mapped for the phone's screen.

## 4. Does the copy vary along a line, between panels, between halves?

All at x16, in recorded (clipped) units, so differences under about 15 % mean nothing.

- **Along a line:** the copy of the left arm (row 14, columns 37 to 49) reads 0.43 to 0.52 of the source,
  rising by about 0.04 from left to right; flat. No step at the joint between the panels (the arm's copy
  runs across columns 63|64 unbroken). CONFIRMED flat within the camera's error.
- **Input side against far side of a chain:** by panel, the k+4 copy is 0.34 (top left, far end of J1), 0.37
  (top right, input), 0.44 (bottom left, far end of J2), 0.37 (bottom right, input) of the recorded source.
  At x4 the 128 lines read about 10 % stronger on the left (far) side of the joint. No consistent trend.
  CONFIRMED: no large difference; a small one cannot be excluded.
- **Top and bottom panel rows:** the same within error (0.34 to 0.37 against 0.37 to 0.44).
- **By scan line:** destination lines 0 to 7 read 0.36, 0.37, 0.43, 0.40, 0.38, 0.39, 0.39, 0.37. Flat. The
  copy above its source and the copy below it are equally strong (0.34 and 0.34 in rows 8-15).
- **By group within a panel:** rows 8-15: 0.34; rows 16-23: 0.35 to 0.40; rows 24-31: 0.43 (few pixels, next
  to vertical strokes, so weak); **rows 0-7: none** (section 2.2). This is the one large difference.
- The still of the lines at x4 shows the 128 line's copy only on the right of the wall. That is the rolling
  shutter's time edge (the edge is at column 64 on one row and column 59 on the next), not the panel joint.
  CONFIRMED by the video, where the copy is on both sides in every frame.

## 5. Fit: is "none at 64, a trace at 128, plain at 255" a fixed fraction?

With gamma 2.8 at the card, pixel values 64, 128 and 255 give 2.1 %, 14.5 % and 100 % of full light (ratios
1 : 6.96 : 47.9). A copy that is a fixed fraction of its source would follow the same ratios, so it would
also read "nothing, a trace, plain". The last session's inference from steepness alone does not hold. The
brief's caution is right.

The test the pictures allow (x16 screenshot, red channel, where the 64 line is the only source below the
ceiling: peak 227 to 240 against 243 to 254 for the 128 and 255 lines):

- Copy of the white 128 line: 0.020 +- 0.006. The white 64 line reads 0.224, so the 128 line's true light is
  at least 6.96 x 0.224 = 1.56 in the same units: **the copy at 128 is at most about 1.3 % of its line**
  (0.9 to 1.8 % with the noise). For orange, 0.0125 +- 0.01 against 6.96 x 0.246: at most about 0.7 %.
  "At most", because the 64 line may itself be compressed. LIKELY, conditional on gamma 2.8 holding at the
  card for these values and on the screenshot's tone curve being near sRGB in that range.
- A fixed fraction then predicts the copy at 255 to read 6.89 times the copy at 128: 0.14 (white), 0.09
  (orange). It reads 0.27 and 0.36, with its LED centres at or near the ceiling, so its true value is that
  or more. **The copy at 255 is at least 2 times (white) to 4 times (orange) what a fixed fraction of the
  128 copy allows.** LIKELY, weakly: one screenshot, one instant, a copy at 128 that is two to three times
  its own noise.
- At 64 a fixed fraction predicts 0.003, under the noise: "none at 64" says nothing either way.
- The fraction range the pictures allow at x16, if one fraction is forced on them: about 0.5 to 2 % at 128;
  at 255 at least about 2.5 % if the 64 line is in range, unbounded above. So either the fraction rises with
  the value between 128 and 255 (by 2 or more), or the screenshot's 128 copy is under-read.
- A cross-check that needs no ratio, only rank, inside one picture: at x16 the copy of the 255 line reads
  brighter than the real 64 line beside it (0.36 against 0.25 orange, 0.27 against 0.23 white) and below
  the real 128 line. The 64 and 128 lines are 2.1 % and 14.5 % of the 255 line's light, so **the copy of a
  255 line is between about 2 % and 15 % of its source** while it is on that row. LIKELY (gamma 2.8 assumed;
  readings near the ceiling). At x4 the same comparison puts the copy of the 128 line about level with the
  real 64 line, and the copy of the 255 line about level with the real 128 line: roughly 10 to 15 % or more.
- At x4 the 64 lines have a copy at 0.17 to 0.27 of the recorded line. A fixed fraction of 1 % cannot give
  that, so the x4 copy is a different size of thing from the x16 copy, by more than an order.

Verdict: the three-level observation is CONSISTENT with a fixed fraction of about 1 % up to 128 and does
not fit one up to 255 by a factor of 2 to 4, on thin evidence. It does not select between "a fixed leak"
and "grey-scale timing". The numbers that would (a ladder of values, read by matching, section 7) have not
been taken.

## 6. How `--brightness 0.1` reaches the card

CONFIRMED by reading the code; the pixel bytes are never scaled.

- `tools/wall_pattern.py:236` takes `level = brightness` and `:240` calls `wall.set_brightness(level)`. Its
  docstring (`:20`): "Brightness is the card's brightness packet".
- `show/wall.py:119-120` passes it to the display; the module says "No software brightness: the device holds
  the level" (`:6`). The flash governor (`arcade/flash.py:197-208`) returns the frame or, for held pixels,
  the previous frame's pixels; it never scales a value.
- `show/display/colorlight.py:213-215` stores `level_byte(level)` in the shared slot.
- `show/display/colorlight_packets.py:39-43`: `level_byte` is `int(min(1.0, level) * 255)`, so 0.1 is **25**.
  `:80-86` puts that byte in the sync packet (payload bytes 21 and 24 to 26, frame offsets 35 and 38 to 40);
  `:89-94` puts it in the 0x0A brightness packet (payload bytes 0 and 1, and the EtherType's low byte).
- `show/display/colorlight_sender.py:255` copies the pushed frame to the row packets with only the channel
  order reversed (BGR); `:271-276` sends, every tick at 59 a second (`:40`), the sync twice, the brightness
  packet twice, then the 64 rows.

So at the card, pixel value 255 is 255, and the card has two brightness terms to apply itself: its own
Level 3 and the packet's 25/255. What the card does with them (scale the grey values before its gamma
table, or shorten the light pulses) is not in the repo and I could not tell from the pictures. It matters:
if the card scales the grey value, "255 at 10 %" uses a low slice of its 13-bit grey range, and a copy that
depends on the grey value's bits would change with the brightness setting. Not tested: any other brightness.

`ghost_test.py` (scratch copy, lines 55-58) draws the orange lines as (level, level // 2, 0), so 64, 128,
255 orange are (64,32,0), (128,64,0), (255,127,0); the lobby's figure is (255,120,0) (`arcade/juice.py:58`).

## 7. What the evidence settles, what it cannot, and what to photograph

Settled (CONFIRMED by measurement):

1. The copy is in the same column, inside the same 8-row group, on a later scan line, wrapping within the
   group. At the saved settings that line is k+4 or k+5, one at a time, switching on a three-frame rhythm
   in the arcade video. At x4 it is k+1 and k+5 together.
2. The offset changes with the refresh multiple.
3. The first 8 rows of each panel do not show the upward-wrapped copies that every other group shows (x16).
4. No sideways shift; no crossing of groups, halves or panels; all four panels and both chains alike; no
   trend along a line.
5. Every colour copies; white copies white.
6. At x4 the copy is much stronger at low values than at x16, and is there in every frame.
7. The pixel bytes are unscaled; brightness 0.1 is a level byte of 25.
8. The camera numbers in the record (0.74 to 0.91) are clipping.

Not settled, and why:

1. **The true strength of the copy** at any value: every source is clipped. Best estimate, about 1 % at 128
   at x16, is conditional (section 5).
2. **Whether the copy is a fixed share of the light.** Leans "rises with the value above 128", weakly.
3. **What drives the k+4 / k+5 switching**, and its true rate: no x16 video without the arcade.
4. **Whether the copy is there while the card holds a frame** (the sender stopped). No picture. The frames
   with no copy once a second (section 2.3) say the copy is tied to a moment of the frame cycle, which makes
   this the most telling picture not yet taken.
5. **Per scan line and per group at full detail**, above all the first 8 rows: the lobby has only three
   rows there that test it, all wrapping upward.
6. **Per colour channel strength**, **other brightness levels**, **x8**, and whether rows 0-7 are exempt at x4.
7. **The 08:31 `grid` and 10:16 bar (value 128) were clean by eye**; at about 1 % a copy of a 128 line is
   0.15 % of full light, which may simply be under what the eye sees in daylight. Not tested by camera.

The pictures that would settle the rest. None of these needs a card setting changed; all are at the saved
settings first. (If a refresh-multiple trial is repeated in LEDVision: Send goes to RAM only, and every
change of Multiple, DCLK or Blanking Value silently sets Brightness Level to 8, so set it back to 3 before
each Send; one variable at a time.)

Camera, for all of them:

- Curtains drawn or evening: the unlit LEDs must photograph near black. This alone gives back most of the
  range.
- Phone on a stand, **landscape**, about 0.6 m from the wall so the wall fills the frame (12 px an LED or
  more), square on.
- Focus and exposure **locked** (hold a finger on the wall until "AE/AF lock"), then exposure pulled down
  (the sun slider, about -2 to -3) until the lit LEDs of the 255 line are coloured dots, not white blobs.
  Check by zooming into the shot: a white centre means still clipped.
- Video, not stills: 3 to 5 seconds, and once in **slo-mo (240 fps)** for the switching. Send the original
  files (AirDrop or the Files app), not screenshots, so the exposure data survives.

Pictures on the wall (each needs a small bench script in the manner of `ghost_test.py`; none exists yet):

1. **One row at a time.** A single row lit over columns 8 to 55 of each panel at 255 white, stepping through
   all 32 rows of a panel, two seconds a row, the row number shown small in a corner. Read off: the copy's
   row for every source row, the first 8 rows included, both directions. Settles geometry per line fully.
2. **The same picture while the card holds it.** Picture 4 (the level lines) with `--stop-for 5`: film
   through the stop and the restart. Is the copy there in the held frame, and does it stay on one line?
3. **Picture 4 at x16 without the arcade, in slo-mo.** Does the copy still switch between rows 20-21 and
   21-22, and how often? Then the same with the arcade bench running. Separates the card from the arcade.
4. **A ladder by matching, which needs no trust in the camera.** One two-row line at 255 on rows 16-17,
   columns 8 to 120; on rows 20-21 nothing (the copy lands there); on rows 24-25, in eight segments, real
   lines at values 12, 16, 24, 32, 40, 50, 64, 80 (0.02 %, 0.04 %, 0.13 %, 0.30 %, 0.56 %, 1.0 %, 2.1 %,
   3.9 % of the 255 line's light at gamma 2.8). The copy is as strong as the segment it matches, by eye or
   by camera. Repeat with the top line at 224, 192, 160, 128, 96: that is the value curve, and the answer to
   "fixed fraction or not".
5. **Per channel.** Picture 4 three times: red only, green only, blue only (values 64, 128, 255). And one
   line of (255,120,0) beside one of (255,0,0) and one of (0,120,0): does the green at 120 copy at all.
6. **How many pixels in the row.** Row 16 lit over 4, 16, 64 and 128 columns at 255: does the copy's
   strength change with the length.
7. **Brightness.** Picture 4 at `--brightness` 0.05, 0.1, 0.2, 0.4 (the cap): does the copy's share change.

## 8. Notes on method and its limits

- Registration is per frame and per panel; the row anchoring was checked by eye on labelled crops for every
  picture used, because at x4 the match to the sent frame picks the wrong rows (the copy outshines nothing,
  but there are more lit rows than were sent).
- The "share of the recorded source" figures come from a least-squares fit in which the camera's glow
  around a lit LED (about 10 to 15 % of a neighbour's reading one LED away, 1 to 3 % two away) is fitted
  together with the copies. The glow of clipped sources is not the glow of unclipped copies, so the shares
  carry an error of a few hundredths beyond the standard errors quoted.
- I did not read the other lanes' reports, and I did not try to explain any of this.
- A laptop-camera photo of LEDVision's grid from 2026-09-29 (`hardware/30-icn2018-grid-horizontal-gap16.png`)
  was checked for a copy under the lines: the lines' glare covers the place. Nothing to be learnt from it.
