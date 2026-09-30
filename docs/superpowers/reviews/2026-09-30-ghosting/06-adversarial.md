# Lane 06: adversarial review of the path forward

2026-09-30. A fresh-context review of `00-path-forward.md` against the five lane reports, `ghost_map.py`,
the record and the owner's media. Read-only: nothing was sent to the wall, the card, the Pi or the Omarchy
box; no commit; no file changed but this one. The script was run only with `--png` and `--dry-run`. Scratch
work: `/private/tmp/claude-502/-Users-trey-dev-codeisart/489bd663-dd66-40f0-8952-22058687bf7d/scratchpad/adversary/`
(`rows.py` my row count, `beat.py`, the extracted frames, the rendered pictures).

Labels as in the lanes: CONFIRMED (a primary source, or my own measurement, with how), LIKELY, SPECULATIVE.
"The synthesis" is `00-path-forward.md`.

## 0. Verdict in short

- The two measurements everything rests on hold. By my own count of LED rows against the unlit lattice, the
  copy is 4 rows on at the saved settings and 1 and 5 rows on at Refresh x4. CONFIRMED (section 1).
- One Critical fault in the run sheet: five of the six runs of block 1, the held frame among them, put their
  source on wall row 2, inside the one row group that the synthesis itself says shows no copy. `--row 18`
  on those runs removes the doubt (C1).
- The synthesis reads the held frame and the switching wrongly in one respect that matters for the decision
  it is meant to make. Our 59 frames a second against the card's 7680 row slots a second leaves a beat of
  exactly 10 a second, which is the rhythm lane 01 found. If that is what switches the copy between 4 and 5
  lines, the sender's timing sets where the copy lands, and neither "the card's" (run 2) nor "the sender
  holds no lever" (run 1) follows (I1).
- Two lanes contradict each other in two places and the synthesis passed over both: what an exempt first
  group means (I2), and whether a pixel at 199 copies (I3). In the second, lane 01's measurement, which I
  reproduce, refutes the premise of the "step at 199/200" that run 4 is told to look for.
- Block 2: refresh 1920 is LIKELY not selectable at this cabinet width (I4); the driver-chip step can light
  the wall past the Brightness Level and its null result means nothing as written (I5); the rules leave out
  three items of the card-setup skill's rule 1 and every "put back" (I6).

## 1. The measurements, checked by my own method

Method: a strip 25 to 30 camera pixels wide, cut vertically through a lit block; the strip's mean luminance
down the image has one peak per LED row (the unlit LEDs are grey dots); rows are numbered from the panel's
first dot row. The anchor is checked by counting on to the seam between the panels: 32 rows each time.
Lit rows are those whose colour stands above the unlit rows'. No lane script was used for these counts.

| Picture | Rows counted top edge to seam | Sent | Lit on the wall |
|---|---|---|---|
| x16 screenshot `a4192b69`, strips at x 850 and x 950 | 32 (dot rows at y 53 to 288, then the seam) | orange 16, 17 | 16, 17 and **20, 21**; rows 18, 19 at the unlit level in green |
| the same | 32 in the bottom panel (y 298 to 534) | white 40, 41 | 40, 41 and **44, 45** |
| x4 video `IMG_5091`, frame 10, strips at x 800 and x 900 | 32 (y 740 to 957) | orange 16, 17 | 16, 17, **18** and **21, 22**; rows 19, 20, 23 red glow only |
| the same | 32 in the bottom panel (y 965 to 1180) | white 40, 41 | 40, 41, **42** and **45, 46** |
| x4 video, frames 3, 25, 47, 61, 77, 99, 108 | | orange 16, 17 | 16, 17, 18, 21, 22 in every one |
| x16 video `IMG_5083`, frames 48, 49, 50, a strip through the left arm | | arm, rows 9 to 12 | frame 48: copy on rows 14, 15 and none on row 8; frames 49, 50: copy on row 15 and on row 8 |

CONFIRMED: +4 at x16 (one instant, no arcade), +1 and +5 at x4 (eight frames), and the two states at x16
(4 lines on in frame 48, 5 lines on with the wrap to row 8 in frames 49 and 50). How sure: for the row
numbers, as sure as a count of 32 rows between two panel edges allows; the pitch is 7 to 8 camera pixels and
no peak is ambiguous except directly beside a clipped line (rows 39, 43, 47 in the white blocks merge with
the bloom, and are placed by the pitch).

The first group's exemption, checked on lane 01's per-LED array (its registration, my arithmetic; this one
is not independent of lane 01): the red excess on the copy's line is 0.49 to 0.66 for every source row of
rows 8 to 15 and 40 to 47, down and up alike, and -0.01 to 0.13 for sources 5, 6, 7 (to rows 1, 2, 3) and
36 to 39 (to rows 32 to 35). The upward wraps of the first group are absent. The downward copies of the
first group (rows 0 to 3 onto 4 to 7) cannot be read: every such place in the lobby touches a lit pixel.

The green figure, value 199: its feet on rows 16, 17 read 0.57, 0.58 on rows 20, 21 in the 4-state and 0.54,
0.52 on rows 21, 22 in the 5-state, against 0.36 unlit. It has a copy, and the copy follows the state.
CONFIRMED on lane 01's array. This matters in I3.

## 2. Critical

### C1. The held frame and four more runs stand on a row that may show no copy

At fault: block 1, runs 1, 2, 4, 5 and 6: `8 --step 0 --seconds 30 --stop-for 15`, `8 --step 0 --seconds 20`,
`8 --hold 10 --seconds 52`, `7 --seconds 20`, `2 --seconds 32`, `8 --channel ...`. None gives `--row`.

Evidence: `ghost_map.py` line 86 sets `row=2`; pictures 2 to 8 work on it. Rendered (`adversary/r1.png`):
the source on wall row 2, the patches on row 6. Row 2 is in rows 0 to 7, of which the synthesis says in
section 1, CONFIRMED: "The first 8 rows of each panel (wall rows 0 to 7 and 32 to 39) show no copy where
every other group does". Lane 01's own text is narrower (only the upward wraps were testable; "whether
rows 0-3 copy down onto rows 4-7 cannot be read in this picture"), and I find the same (section 1). So
whether row 2 has a copy at all is not known. If it has none, run 1 answers nothing, and its table invites
a wrong answer: "Copy gone or changed: A1, and the question moves to the sender". The map that would say
whether row 2 copies is run 3, after the runs that depend on it.

Correction: add `--row 18` to runs 1, 2, 4, 5 and 6. Row 18 is scan line 2 of rows 16 to 23, the group in
which the morning's lines on rows 16, 17 copied to 20, 21 at x16 and to 21, 22 at x4; the patches then sit
on row 22. Parsed and rendered (`adversary/fix1.png`, and `7`, `2` and `8 --channel r` with `--row 18`).
Correct section 1's bullet to what lane 01 measured: the first group shows no upward wrap; downward not
tested.

## 3. Important

### I1. What runs 1 and 2 can and cannot say: the sender's beat against the card's row clock

At fault: run 2, "Does the copy switch between 4 and 5 lines on with no arcade running? Yes: the card's. No:
the arcade run did it"; run 1, "Copy unchanged with no packets: A2, B or C, and the sender holds no lever";
section 3 item 5; section 6, "A sender card would not help if the held frame shows the copy".

Evidence, arithmetic (CONFIRMED as arithmetic): at 960 Hz and 8 lines the card steps 7680 row slots a
second. The sender's frame is 1/59 s (16.949 ms, sd 1 us on the Pi, `00-bench.md` line 232): 130.1695
slots. Each sync lands 0.1695 of a slot later than the one before, and the phase comes round 7680 mod 59
= 10 times a second. Lane 01's rhythm is "exactly 3 frames, that is 10.0 Hz". Neither lane 01 nor the
synthesis has this candidate; they name a cycle inside the card and the arcade's pose thread (also 10 a
second, so the video cannot choose between the beat and the thread).

Evidence, the video (lane 01's array, my reading, `beat.py` and the per-column map in my scratch): the
state is the same across the whole wall in all but about 18 of 105 frames. Those cluster at frames 21 to
26, 50 to 55 and 80 to 87. In them a strip one 8-column bin wide, with no copy or a mixed reading, walks
from the right of the wall to the left by about 16 columns a frame; in frames 23, 53 and 84 the wall is in
the 5-state on one side of the strip and in the 4-state on the other. The phone reads its columns in turn,
so the strip is a moment in time, and it recurs where the 59-against-30 beat brings the same moment of the
sender's frame into the readout. So the copy's line is set once per sender frame and changes at that
moment. LIKELY. This refines the synthesis's bullet ("frames 22, 52, 82 ... part of the wall shows no
copy"): it is a narrow strip over five or six frames each second, and lane 01's "frame 96, part of the
bottom" is another thing, a frame in which the copy is at about half strength over the whole wall.

What follows, my reading, SPECULATIVE until run 2 is filmed: the line the copy lands on depends on where in
a row slot the sync arrives. Then:

- Run 2 with no arcade will still switch, about 10 times a second. The synthesis would book that as "the
  card's". It would be the sender's timing against the card's clock, which is a lever (the rate, or the
  sync's phase).
- The held frame would show the copy fixed on one line. The synthesis would book that as "the sender holds
  no lever". A state left by the last sync that arrived is still the sender's doing.
- At x8 the same arithmetic gives 3840 mod 59 = 5 a second; at x4, 32 a second.

Correction: read run 1 three ways, not two: copy gone; copy as before, still switching; copy fixed on one
line. Run it three times and write the copy's row during each stop: a row that differs from stop to stop
is a state left by the last sync. Read run 2 as: "No: the arcade did it. Yes: the card's own cycle or the
beat; the held frame and the rhythm at x8 (5 a second, not 10) tell which". Drop "the sender holds no
lever" and the sender-card bullet unless the held copy also switches as it does while streaming.

### I2. An exempt first group: lane 02 reads it one way and the synthesis the opposite

At fault: section 3 item 3, "rows r and r + 8 share one row switch (the route table), so an extra row token
would copy both groups of a half alike. If the first group of each panel really is exempt, that speaks for
the data side"; section 4, cause B, "Both groups of a half copy alike".

Evidence: lane 02, verdict 4: the exemption "is what puts the row tokens ahead of the data: it is what a
stray token does in row chips chained output to input, and nothing on the data side makes one group of
rows differ from the next". The synthesis took the other side and did not say the lanes differ. (Lane 02
cites its "section 4.5" for this; its report has no section 4.5, so its argument is not written down
either.) The route table (lane 03, section 3.3) says which data is shown in which scan slot. It does not
say whether rows r and r + 8 hang on one switch or on two chips stepping together; the board's row chips
are not counted (lane 02: "whether T1 and T4 exist is not settled", and the parts are named T2 and T3).
On the data side rows r and r + 8 are alternate bits of one 128-bit chain with one latch and one OE:
nothing there can tell the first group from the second.

With four 8-output chips chained output to input, an old token left in the chain when a new one is entered
at the first chip gives the first chip copies downward only and every later chip copies both ways. That
is exactly what is measured (section 1: upward wraps absent in the first group, present in the others) and
it is lane 02's verdict 6 ("the first group: copies downward only").

Correction: strike the inference. Give run 3 its readings: first group copies down (rows 0 to 3 onto 4 to
7) and not up: chained row chips and a stray token, the row side. First group copies nothing: not explained
by either. First group as the others: lane 01's exemption was the picture. Add to the panel-back list:
count the T parts and see whether one's DOUT (pin 10) runs to the next one's DIN (pin 2).

### I3. "A step at 199/200" is already contradicted by lane 01, and run 4 is told to look for it

At fault: section 3 item 4, "Lane 02 reads the same pictures as bit planes shown again (the top plane is lit
from pixel value 200 up) and predicts a step between 199 and 200. Both are weak"; run 4, "A drop between 224
and 192: bit planes (lane 02's step at 199/200)".

Evidence: lane 02's premise is "none SEEN from green 199, which is 50 % of the light but has no top bit
plane". Lane 01, section 3.1, CONFIRMED: "The green figure (0,199,0) has a green copy". I reproduce lane 01
(section 1 above). A pixel at 199 copies, so the copy is not the top plane alone. The lanes also disagree
on 128 at x16: lane 02 "no copy", CONFIRMED by its measure; lane 01 a copy of 0.020 +- 0.006; the owner "a
trace". The synthesis quotes lane 01's number and does not say lane 02 measured none. Last, the step
assumes the sender's level (byte 25) shortens the light pulses; if the card scales the grey values by it,
at brightness 0.1 no pixel has a top plane at all (lane 01, section 6, raises this; not settled).

Correction: run 4's reading becomes "the same patch at every value: a fixed share; a lower patch as the
value falls: the share rises with the value". A sharp drop anywhere is worth writing down; 199/200 has no
standing. Picture 7 at `--brightness 0.2` draws the source at 199, on the disputed value; nothing to change,
but do not read that one point as a step.

### I4. Block 2, step 2: refresh 1920 is LIKELY out of range at width 128, and there is no branch for that

At fault: step 2, "Refresh Rate, at x16: 960, then 1920 ... The law predicts no copy ... Check the cabinet
width is still in range"; "Steps 1 and 2 are ten minutes and decide the most"; section 6, "the first
candidate cure".

Evidence: the record has the width limit at three slots: 350 at x4 (slot 521 us), 322 at x8 (260 us),
216 at x16 (130 us) (`hardware.md` lines 334, 335; lane 03 section 1). Halving the slot cost 28 columns,
then 106. At 1920 the slot halves again; even the last loss repeated gives 110, under the wall's 128, and
the trend is steeper. Only the list entry is on record; nobody has selected it. Lane 03 says "if it turns
red, do not Send" and no more. Also "predicts no copy" is firmer than lane 02 ("perhaps none"), and the
law as written leaves out the 5-state, which at 1920 would be 10 slots: 2 rows on.

Correction: write the expected outcome (the width shows red; do not Send) and the branch before the
session: Gray Level 8192 to 4096 judged first at 960 as its own step, then 1920 at 4096; or leave 1920 out.
x8 is then the one test of the law that is sure to run.

### I5. Block 2, step 7, the driver chip: what may light, and what a null means

At fault: step 7, "Driver IC, in the wizard, at Level 1: Normal Chip, then the DP5125 entry or the nearest
step 0 found ... A dark or scrambled wall means that entry is not the DP5125's; cancel and power-cycle".

Evidence: (a) "the nearest" is open. Lane 03 gave an order (a DP5125 entry, another Depuw general chip,
ICN2038S, FM6126A), all plain double-latch parts; the synthesis dropped it. An entry for a PWM chip makes
the card run OE as a grey-scale clock; plain shift-register outputs then light for as long as that clock
is low, whatever Brightness Level says. My inference, SPECULATIVE, but it is the one way a step here
lights the wall hard at "Level 1". (b) Lane 03, section 2.8: the generic mode "will not cause reverse
voltage" on the LEDs, which "implies the other mode can". Not in the synthesis. (c) The DP5125E sheet, as
lanes 02 and 04 both quote it: "on power-up the chip recognises its working mode". The card and the panels
share one 5 V supply (`hardware.md` line 108), so the chips chose their mode at power-up from the flash's
Normal Chip traffic. A Send afterwards may never be recognised: "no change" would then say nothing about
causes C and D. LIKELY, from the datasheet's wording; no lane raised it.

Correction: name the entries allowed (lane 03's four) and forbid any PWM-chip entry. Keep a hand on the
supply's switch at the first Next after the choice. Say in the table that a null is void unless the panels
are powered up while the card already holds the setting, which the shared supply does not allow without
pulling the panels' power plugs: the owner's call, and a reason to put this step last or leave it.

### I6. Block 2's rules are not enough on their own

At fault: "Rules, every step: ..." and step 0 and step 4.

Evidence and corrections:

- Step 0 opens the wizard as far as Guide 2 with no word on the level. Guide 2 lights a white band at the
  card's own level (`hardware.md` line 281). The skill's rule 1: "Set it to 1 (10%) and Send before opening
  the wizard". After the power cycle the level is the flash's 3. Add Level 1 to step 0.
- The skill's rule 1 also has: "untick 'Automatic changes' on every wizard page at once" (the pages
  otherwise alternate their states, a flashing band), and Gray Test opens at Red 255 and must be set to 0
  before the Net Card is used. Neither is in the synthesis; steps 0, 6 and 7 are wizard passes. Carry them
  into the rules, since the owner is told the rules are for "every step".
- "set it to 3 ... before every Send" is wrong for steps 3, 6 and 7 as written (Levels 1 and 5). Say "set
  it to the step's level".
- No "put back". Lane 03's table has one per step; the synthesis has "a power cycle undoes everything" and
  no instruction to do it. After step 0's Cancel the RAM may hold what the wizard sent (lane 03: "If the
  wizard sent anything, power-cycle"). Correction: power-cycle after step 0 and between steps.
- Step 4, "Expect flicker at 60; judge the copy". The governor cannot see the card's refresh. Bound it: a
  still picture with under 3 % of the wall lit (picture 8), Level 3 or less, a short look, and stop if the
  wall pulses a few times a second. Or go straight to the list's highest x1 rate.
- "A power cycle undoes everything": supported for the card's RAM (`hardware.md` lines 144, 235; the
  skill, "A card power cycle forgets it"). I found nothing against it.

### I7. Block 2 is judged with the wrong picture

At fault: "run `8 --step 0` (and `1a` where the row matters)".

Evidence: picture 8's patches sit 4 rows under the source. At x8 the law puts the copy 2 rows on, at x4 it
is 1 and 5: the patches are then not beside the copy, and with the default row the source is in the first
group (C1). The only picture with a measured reference at two multiples is the morning's
`~/bench/ghost_test.py 4` (rows 16, 17 and 40, 41), still on the Pi.

Correction: for steps 1, 2 and 4 film `ghost_test.py 4` (the same picture as the x16 and x4 references)
and `1b`; use `8 --row 18 --offset N` only once the copy's row at that setting is known.

### I8. "Draw the curtains" for every run throws away the row count

At fault: "Draw the curtains ... pull the exposure down until the lit LEDs are coloured dots".

Evidence: lane 05's run sheet says the opposite ("Room lights on ... the unlit LEDs then show as a grid and
rows can be counted"); the synthesis took lane 01's advice and did not say so. Every row number in this
review, lane 01's, lane 02's and mine, was counted against the lattice of unlit LEDs in daylight, and
lane 01 rates daylight photos "fully" trustworthy for geometry. In a dark room with the exposure pulled
down for a 255 line, the ruler's ticks (value 64, 2 % of that light) are the only row reference left, and
pictures 2 and `--no-ruler` have none.

Correction: the map (run 3) and every "which row" clip in room light, as this morning. Curtains for the
strength runs (4, 5), which are judged by eye against the patches and need no lattice.

### I9. Labels that are stronger in the synthesis than in the lane

- Section 1, first bullet, CONFIRMED: "the card's 2.8 acts on the bytes as drawn (64 is 2 % ...)". The 2.8
  is a saved setting; its effect on our frames has never been checked at the wall (`wall_pattern.py gamma`
  is still owed). Lane 01 writes "if the card's gamma is 2.8". LIKELY. Section 7's governor finding and
  picture 8's patch values inherit this.
- Section 1, CONFIRMED: "The 'redder' copy is the camera". Lane 01: "LIKELY the whole explanation", and
  it could not test whether the green at 120 copies less. If the share rises with the value, as section 3
  item 4 reports, the copy of (255, 120, 0) is truly redder than its source. The two statements conflict.
- Section 1, CONFIRMED: "It never crosses ... a panel". Lane 01: rows 31|32 "carry only vertical strokes, so
  the picture cannot test that one directly".
- Section 1: lane 02 "by a second method" confirmed the geometry. Lane 02 measured two lines on scan lines
  0 and 1; the wrap, the groups and the panels are lane 01's alone (and the wrap at x4 for lines 4 to 6 is
  nobody's).
- Section 2: "SOP16, 8-output parts". Lane 02: at least 7 leads a side CONFIRMED, SOP16 LIKELY.
- Section 7, CONFIRMED: "Blanking Value 3 is 300 ns, under the 500 ns every candidate row chip asks for".
  The 300 ns is CONFIRMED from bytes. That it is the row clock's high time, which is what the 500 ns is
  about, is LIKELY in lane 02 and "not settled" in lane 03.
- Section 1: the four blanking trials "changing nothing". Lane 01, contradiction 7: judged by eye on a
  flickering stream against a copy that switches rows; "weak evidence that the blanking settings do nothing".
- Section 4: "Lane 02's weights: A about 60 %, C about 10 %". Lane 02's verdict gives 60 % to extra row
  tokens alone, 10 % to data shown again, 5 % to the DP5125, 15 % unknown; its own table gives 60, 10 (the
  DP5125), 20. The two do not agree with each other, and lane 02's 60 % covers what the synthesis files
  under B as well as under A. The weights cannot be quoted against the synthesis's A1, A2, B split.

### I10. The cause table separates less than it claims

At fault: section 4.

- A1 against A2 rests on the held frame alone, with the gap of I1 (a state left by the last sync).
- A2's "moves to 2 lines on at x8" and B's "another serial decoder entry lights one row with no copy" are
  each predicted by the other as well (lane 03, section 5.4: another entry "runs other code").
- B's "both groups of a half copy alike": I2.
- C's test, lines on a dim field, is in no run: `ghost_map.py` has no dim-field picture, and picture 6,
  which lane 02 names beside it, is not in block 1. Lane 02's caution ("unchanged is weak evidence") was
  dropped. Cause C is untested by this session; say so.
- Not in the table: the beat of I1; a fault of this one card. Card 1 was called faulty from a comparison
  under the wrong decoder (`hardware.md` lines 114 to 117) and has never run ICN2018/3018. The same file
  sent to card 1's RAM and one picture from the Pi would say whether the copy is card 2's. The owner's
  call: card 1 showed a green pattern after a Send on 2026-09-29.
- I checked two causes the brief raised and found them excluded: the RAM holding x4 during a "saved
  settings" observation (the x16 video is from 09:40, before LEDVision was opened; the card had been
  power-cycled after the spike and nothing was sent in between), and the camera (the owner sees the copy by
  eye; only the 4/5 switching and the strip of I1 are camera-only).

## 4. Minor

- Run 6, "`8` with `--channel r`, `g`, `b`": no `--seconds` or `--hold`, so each runs until Ctrl-C at 6 s a
  step. Lane 05's line is `8 --hold 10 --seconds 52 --channel r`.
- `1a --seconds 100` shows r00 again for its last 4 s; `8 --hold 10 --seconds 52` shows s255 again for 2 s.
  Harmless; the label says which step it is.
- Run 2 in slo-mo: a 240 fps frame is at most 4 ms, four of the sixteen passes of a frame. A frame with no
  copy there is not the copy switching off. Read the rows, over many frames.
- Picture 8's patches are on the 4-lines-on row only. In the 5-state the copy is one row lower, so by eye
  the match is against about two thirds of the copy.
- Step 3 at Level 1 raises LEDVision's "Minimum OE is 0" prompt (answer Yes; the skill, step 7).
- Step 5, "3, then 30, then 80": lane 03 adds "if the box refuses, the largest it takes".
- Step 1, "one copy 2 lines on": lane 02 says "2 (at times 3)".
- The scp line needs the directory made on the Pi first; lane 05's sheet has both lines.

## 5. What is missing

Cheap observations nobody proposed:

1. **The originals behind the two screenshots.** `a4192b69` is a screenshot taken at 10:19:46 of something
   filmed or photographed during the 10:16 runs. If it is a video or a Live Photo of `ghost_test.py 4`, it
   is the x16 video with no arcade that lane 01 says does not exist, and it answers run 2 with no wall
   time. Ask the owner for the file.
2. **The wall during every cable move.** Between LEDVision's last frame and the Pi's first, the card holds
   LEDVision's grid with no packets. A look, or five seconds of film, at each RAM setting is a held frame
   for nothing. Lane 03's step 1 ("Use Net Card" unticked) is the same thing on purpose; the synthesis
   dropped it.
3. **The stop, three times** (I1).
4. **`wall_pattern.py gamma` and `steps --brightness 0.4`**, a minute each, owed since the card was set up.
   Pictures 7 and 8 and section 7 all assume gamma 2.8 and a linear level.
5. **A logic analyser or a scope on a free output of the card.** The 5A-75E has eight HUB75 outputs and the
   wall uses two; A, B, C, OE and LAT are there on the others with no panel to open. A is the row clock at
   7680 a second and C the token: any cheap analyser counts the tokens. It is the one observation that
   tells rows switched early from data shown again (lane 02, E6), shows whether the tokens change when a
   frame arrives (A1), and measures what Blanking Value stretches (lane 03). The synthesis says "Nobody has
   seen the card's row signals" and does not ask whether the owner has the tool.
6. **The rhythm at x8**: 5 a second if the beat of I1 is real, which no other candidate predicts.

In the lanes and not in the synthesis:

- Lane 03, step 1c: the card's flash read back 32, 32, 128 where the draft sent 16, 16, 64. Loading the
  draft file and Send is a free trial. The fixed-time unit is 1/1920 s, which is 60 x 32 on a card set to
  x16; lane 03 did not connect the two and neither can I, but a factor of two in both is a reason not to
  drop the trial silently.
- Lane 03, section 5.1: Send, then Read, to learn whether Read returns RAM or flash and whether a Send of a
  field took. Without it a null in block 2 cannot be told from a Send that did nothing.
- Lane 03, steps 5 to 7 and 10 (Blanking Phase, Gray Level, Display Mode) and lane 02's E2, E3, E5 (panel
  by panel, one panel alone, a ribbon swapped). Left out by choice, LIKELY rightly, but the synthesis should
  say they were left out.

Decisions section 6 does not cover:

- A multiple moves the copy and nothing removes it. Is a copy 1 or 2 rows from its line (a thicker line)
  better than one 4 rows away? The x4 video says the price: the copy is far stronger there.
- The held copy is fixed and the streamed one switches (I1). Then the sender's rate is a lever against a
  driver that was tuned to 59 for the flicker: two faults pulling on one setting.
- Nothing clears it. Section 6 goes straight to the software workaround. Before that stand: other
  firmware for the card (lane 03 found 13.39 and 11.04 named in FPP issue 1849; a flash write, the owner's
  word, and card 1 is the card to try it on); another make of receiver card; the panels driven without
  the card (lane 04, A6: DP32020A and SM5368 rows run under rpi-rgb-led-matrix's row type 5). Each has a
  delivery time, and the install is 2026-11-11. A date by which to choose belongs in section 6.
- 1920 out of range (I4), and the driver-chip null (I5).

## 6. Checked and found sound

- Every command of block 1 parses through `ghost_map.py` and `wall_pattern.py` (`--png`); flags, picture
  names, `--step 0`, `--hold 10`, `--channel`, brightness 0.1, 0.2, 0.4 (the cap is 0.4; picture 7 needs
  0.1 or more). `--seconds` covers the steps in each: 16 x 6 = 96 of 100; 5 x 10 = 50 of 52; 5 x 6 = 30
  of 32.
- `8 --step 0 --seconds 30 --stop-for 15 --dry-run` (a socket that discards): the stream stops at 5.0 s,
  restarts at 20 s, 885 frames sent, exit 0. `--stop-for` does not blank: `ColorlightDisplay.pause` sets a
  flag, the child sends nothing, the card keeps its last frame (No Signal Action, and seen from the Pi,
  `00-bench.md` line 228). The restart is a prime then a sync. One slight blink at stop and restart was
  seen once from the Omarchy box; nothing repeats. Run 1 also closes the Pi's open Q66 item.
- Nothing in block 1 blinks, sweeps or alternates; no picture lights over 12 % of the wall; each run opens
  from black and closes to black through the governor. No photosensitivity concern in block 1.
- The Pi's port is `eth0` (`00-bench.md` line 97).
- The order of block 1 for a short session, once C1 is fixed: the held frame, the switching, the map.
- The arithmetic quoted: 2 %, 15 %, 100 %; peak 155 at 0.4; 231 to 255 as 24 %; 0.52 ms and 2.6 ms;
  0.65 ms; Level 5 as 38 %.
- Section 2's corrections of the last session's record agree with the lanes and, where I measured, with me
  (the 5 rows at x4; the screenshots; the clipped ratios).

## 7. Limits of this review

- My row counts are my own. My readings of the strip, the beat and the first group use lane 01's per-LED
  array of the first video; I checked that array against my own strips in three frames only.
- I did not open the VM, so nothing about LEDVision's dialogs is first-hand; I4 is an extrapolation from
  three numbers in the log.
- I1's attribution of the rhythm to the beat is an argument from arithmetic and one video. The pose thread
  fits the same 10 a second. Run 2 with `--row 18` decides between them.
