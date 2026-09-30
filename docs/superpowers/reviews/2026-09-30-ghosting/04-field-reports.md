# Lane 04: what other people saw

Date: 2026-09-30. Read-only research; nothing was sent to the wall or the card and no repo file was changed
except this report. Labels: CONFIRMED (a primary source, cited, or read from code at a named commit), LIKELY,
SPECULATIVE. "Not settled" means I looked and could not decide it.

All web sources were read on 2026-09-30. Code was read from shallow clones at these commits:
rpi-rgb-led-matrix `51d3231` (2026-09-07), ESP32-HUB75-MatrixPanel-DMA `cf09801` (2026-08-16), DMD_STM32
`398ec1d` (2026-08-29), PxMatrix `ea8dc95` (2021-03-08), Adafruit_Protomatter `3fc002d` (2026-02-13), FPP
`65860b2` (2026-09-30).

## 0. Verdict in short

Revised the same day after lane 02's measurements (`02-mechanism.md` section 4.4): the copy is not a fixed
number of rows away. It is +4 rows at Refresh x16 and +1 and +5 rows at x4, which is the same two delays,
0.52 ms and 2.6 ms. Points 2 and 6 below were rewritten for that; the search itself was framed on "a fixed
number of rows", as the brief had it.

1. **I found no report that matches our symptom and names a cure.** No one on a 1/8-scan outdoor panel with
   serial row drivers and generic column drivers describes a dim copy a fixed 3 or 4 rows away, on any
   controller, and says what ended it. Nor does any report I read describe a copy that moves with the
   refresh setting or comes a fixed time after its source. That is a finding: the wall's fault is not a
   known, named one with a known setting. CONFIRMED as a search result (section 1 lists what was searched).
2. Three reports have a copy a fixed several rows away. All three are unresolved (section 2). The only class
   of fixed-offset copy that was ever cured is a **row-select fault**: two row groups on at once because a
   select line floats or is mistimed (copy 16 rows away on a 1/24-scan panel; cured by driving the pin).
   CONFIRMED for those panels. **It does not fit ours**: a select fault puts the copy at the same distance
   whatever the refresh multiple, and lane 02 measured the distance changing (LIKELY ruled out).
3. Ordinary ghosting in these communities is on the **row lit next** (the adjacent row), and its cures are
   well documented: keep the output off around the latch and the row change; make the shortest light pulse
   longer; change rows less often; slow the signals; lower the panel supply; ground or drive every select
   line (section 3). With a serial row driver the row lit next is the physically adjacent row, so these
   reports describe a different geometry from ours unless the one-row-at-a-time map says otherwise.
4. The chip makers' own papers say what this chip pairing needs (section 5), all CONFIRMED from datasheets:
   - the serial row chip wants its row clock high for at least 500 ns (that width is the blanking time);
   - Depuw states that upper and lower ghosting are removed by the row chip's discharge **together with a
     column driver that pre-charges**, and names the DP5125 for it;
   - the DP5125E sheet says its generic mode is "single latch, no ghost elimination". The card's "Normal
     Chip" setting is that generic mode, so the column drivers' ghost circuit is LIKELY off on our wall.
5. Cures that can be reached on a 5A-75E (section 6): a driver-chip setting that turns on the DP5125's
   double-latch mode; a longer minimum OE (fewer grey levels or a lower refresh multiple); the Blanking
   Phase page; an untried serial decoder entry; the panel supply voltage (a hardware trial); and, from our
   own sender, a cap on the brightest values next to black. None is proven for our geometry.
6. The field evidence that bears on lane 02's reading (a second token in the row chips, or a bit plane shown
   again, put there by the card's sequencing) is the record of serial row drivers being near-compatible
   and not interchangeable: drivers written for one serial chip light the right row on another and are
   still wrong in their timing (ESP32-HUB75 issues 805, 806, 815; rpi-rgb-led-matrix issue 1774), and
   Depuw builds a guard into the DP32020A against "3 or more channels on at once", which says extra tokens
   in the register are an expected condition (section 5.1). CONFIRMED as reports and datasheet text; that
   this is our fault is lane 02's to argue.
   (An earlier draft of this point read our log's "rows with B = 0" as the row chips gating on line B. Lane
   02 shows that a plain 8-stage serial register fed 138 addresses lights those same rows with no gate: A
   clocks at addresses 1, 3, 5, 7 and C is 0, 0, 1, 1 there. The reading is withdrawn.)

## 1. What was searched

Issue trackers, through the GitHub API (`gh search issues` and full issue text with comments), for:
ghost, ghosting, shadow, faint, "rows below", "4 rows", "dim copy", "double image", bleed, ICN2018, ICND2018,
DP32020, SM5368, SM5158, RUL5158, TC7558, TC7559, DP5125, and the board markings.

- hzeller/rpi-rgb-led-matrix (issues 92, 311, 328, 691, 703, 823, 970, 1209, 1725, 1744, 1774 read in full)
  and its Discourse group (the group's search for ghosting, ghost, shadow, faint, "rows below", DP5125,
  DP32020, ICN2018, SM5368; topics 137, 950, 1056, 1161, 1226 read).
- mrcodetastic/ESP32-HUB75-MatrixPanel-DMA (issues 64, 204, 545, 643, 645, 654, 671, 698, 702, 709, 733, 759,
  781, 804, 805, 806, 815, 838, 845, 861, 885, 920, 929, 949 read, the long ones around every ghost mention).
- board707/DMD_STM32 (issues 9, 10, 38, 104, 118, 134, 142, 161, 168, 201 and the wiki page Led_drivers),
  2dom/PxMatrix (issues 26, 28, 38, 158, 175, 290), Adafruit_Protomatter and pixelmatix/SmartMatrix (no
  issue matched; Protomatter's core read for its row handling).
- FalconChristmas/fpp (source and issues), the Falcon forum, AusChristmasLighting, doityourselfchristmas,
  the Light-O-Rama forum, through web search and direct page reads.
- Chinese-language sources for 上鬼影, 下鬼影, 消影, 拖影, 行管, 串行译码, 5958, ICN2018, DP32020, "隔4行":
  Chipone's article on row drivers, Depuw's datasheets.
- NovaStar's NovaLCT manual for the names and meanings of the ghost settings.
- The board family: `P5-1921-64X32-8S`, `-S1`, `-S2`, `-S3`, `H3.3`, `YP5-5125`.

Not reached: Facebook groups (the Wired Watts and "P5 and P10" groups are closed to a reader without a
login), the Falcon forum's own search (login), the Parallax forum thread on DP5125D panels (the server
refused the read), Zhihu (403; the same article was read from a mirror). Images in six issues were
downloaded and looked at; videos were not watched except four frames of issue 885.

## 2. Reports with a copy a fixed several rows away

This is the geometry that matters. There are few, and none is solved.

| # | Report | Hardware | In the reporter's words | Tried | Ended by |
|---|---|---|---|---|---|
| M1 | ESP32-HUB75 issue 885, 2025-12-24, open. https://github.com/mrcodetastic/ESP32-HUB75-MatrixPanel-DMA/issues/885 | 1/4-scan HUB75 panel, chips not given, ESP32-S3 | "Issue persists only on the 4th scanned line and continue to 5 th line when actual scan is happening on 2nd line and so on." | clkphase both ways, clock 8 to 16 MHz, every line decoder, five driver types, latch_blanking 0 to 4, lower refresh | Nothing. No answer beyond the maintainer asking for the panel size |
| M2 | ESP32-HUB75 issue 861, 2025-11-09, open. https://github.com/mrcodetastic/ESP32-HUB75-MatrixPanel-DMA/issues/861 | 128x64, FM6124 columns, 7258 rows (138 type), ESP32 | "Some rows (0,8,16,....) will draw up 3 rows below it as well." "it does not override the color previously lit up, it just turn up the brightness if it's the same color" | clkphase: "It does not" help | Nothing. The panel was sent back |
| M3 | rpi-rgb-led-matrix issue 970, 2020-01-24. https://github.com/hzeller/rpi-rgb-led-matrix/issues/970 | P6 outdoor 32x32, 1/8 scan, Pi 3B+, `--led-multiplexing=1 --led-slowdown-gpio=4`; chips not given | "Even after --led-pwm-lsb-nanoseconds=1000 I'm seeing some ghosting which the camera could not capture." | LSB 130 (default), 500, 1000 ns | Mostly gone at 1000 ns by the photographs; no reply; closed in the 2025 mass clean-up |
| M4 | ESP32-HUB75 issue 838, 2025-09-17. https://github.com/mrcodetastic/ESP32-HUB75-MatrixPanel-DMA/issues/838 | 96x48, 1/24 scan, ICN2037 columns, SM5166 rows, ESP32-S3 | "the content of row 16 to 23 overwrite rows 0 to 7 (additively not replacement). This repeats on the bottom half" | pin assignments, board definitions | **Driving the E line** (it had been left unconnected) |
| M5 | PxMatrix issue 38, 2018-10-06. https://github.com/2dom/PxMatrix/issues/38 | 64x32, 1/16 scan, ESP32 | "ghost lines below the drawn line"; later "every character is being printed twice ... shifted down one pixel" | panel ground, fast update, an older library | **A sound ground wire, and the E pin driven or grounded** |

Notes on these, so they are not over-read:

- M1 and M2 describe whole lines, and neither says the copy is dim. M1's offset is 3 scan steps on a panel
  whose scan lines are not in physical row order, so it cannot be turned into rows without the panel's map.
  M2's copies fall only under every eighth row. Neither is our picture exactly. LIKELY different faults.
- M3, my own reading of the first photograph (not the reporter's words): a faint trace in the column
  straight above the letter "h", and faint dots some 25 rows above the text. At 1000 ns the photograph shows
  neither. SPECULATIVE that the far dots are a row copy; the panel's multiplex map may have been wrong too.
- M4 and M5 are the one cured class: **two row groups selected at once**. The copy is at the distance
  between the groups (16 rows in M4), and it is strong, not faint, because the second group is fully on. The
  cure was electrical (drive the select line), not a timing setting.
- Our own record has rows 4 apart on together once: under "138" decoding the wall lit rows 1-2, 5-6, 9-10
  and 13-14 (hardware.md lines 128 to 134). CONFIRMED observation. The log read it as "the rows with B = 0";
  lane 02 shows it is what an 8-stage serial register does when it is fed 138 addresses (two tokens, four
  stages apart), with no gating by B. So it shows that these row chips will hold and show more than one
  token at once, and nothing about a select line.

A design in the field where sibling row chips all hold the same shifted bit and only a select line separates
them is documented: the SM5266 panels ("8 SM5266 shifters ... DE is used to select the active shifter",
rpi-rgb-led-matrix `lib/framebuffer.cc` lines 113 to 122). On such a board a weak or late select gives a copy
exactly one chip's worth of rows away. I raised it as a possible parallel for our two row chips. It does not
hold: lane 02 counts at least 7 leads a side on T2 and T3 (SOP16, 8 outputs each, not the 10-pin parts the
log supposed), and a copy that moves from +4 to +1 and +5 rows with the refresh multiple is not a fixed
pairing of rows. Kept here so the idea is not raised again.

## 3. Ghosting reports on the same class of hardware, with what ended them

These are adjacent-row or same-row artefacts. They are the common kind and LIKELY a different fault from
ours; they are kept because their cures say what these chips are sensitive to.

| # | Report | Hardware | Symptom, in the reporter's words | What ended it |
|---|---|---|---|---|
| A1 | ESP32-HUB75 issue 64, 2021-01. https://github.com/mrcodetastic/ESP32-HUB75-MatrixPanel-DMA/issues/64 | 64x64 1/32; ICND2012 or RUC7258 rows, ICND2038S or ICN2037BP columns | "A ghost pixel appears when a pixel is set to a brightness level of RGB888(192) or above"; "193 ... no ghost, 194 ... ghost"; "All ghost pixels have always the same brightness level of about 64"; "in the same column, one row beneath"; row 31 ghosts onto row 0 of the same half | The library's dev branch, which blanks OE for some clocks before and after the latch (later `setLatBlanking`). A later user: `clkphase = false` |
| A2 | ESP32-HUB75 issue 733, 2025-01. https://github.com/mrcodetastic/ESP32-HUB75-MatrixPanel-DMA/issues/733 | P5 32x64 1/8 Qiangli; **RUL5158C serial rows**, SM16208 columns | "When I connect the second panel, there is a ghost shadow problem" (a sideways smear by the photograph) | Shortening the latch from three clocks to two: "several cycles continue latch signal creates ghosting" |
| A3 | ESP32-HUB75 issue 545, 2023-12. https://github.com/mrcodetastic/ESP32-HUB75-MatrixPanel-DMA/issues/545 | 64x64 Waveshare; SM5166PS rows, SM16208SJ columns | ghosting "on vertical edges like the checkerboard or text", bottom half | `latch_blanking: 4`, clock 8 MHz, `clock_phase: false` |
| A4 | ESP32-HUB75 issues 845 and 920, 2025 to 2026. https://github.com/mrcodetastic/ESP32-HUB75-MatrixPanel-DMA/issues/920 | 32x16 1/8; 74HC138 rows, JXI5020 columns | a dim copy down the whole half column; "Lower values [of colour depth] makes ghost pixels more intense"; "only visible on black pixels" | Not the latch blanking, clock, level shifters, resistors or supply. A slower library (CircuitPython rgbmatrix) was "fairly good". Maintainer: "some panels have issue with the precise/fast timings ... between data, latch and output enable" |
| A5 | rpi-rgb-led-matrix issue 1725, 2024 to 2025. https://github.com/hzeller/rpi-rgb-led-matrix/issues/1725 | P5 outdoor 8S 64x32 with SM16208 columns, two reporters (`HRL-P5-8S-LED1922-64x32-v2.0`; the second reporter's panel has ICN2012 rows, 138 type) | second reporter: "looks almost perfect, but there is some ghosting going on"; board707 put it down to contacts, not the mapping; left open | first reporter: `--led-slowdown-gpio=6` on a Pi 4 (the limit patched to 10), "to remove flicker and ghosting" |
| A6 | rpi-rgb-led-matrix issue 1774, 2025. https://github.com/hzeller/rpi-rgb-led-matrix/issues/1774 | 128x64 ABC panels; **SM5368 and DP32020A serial rows**, SM16208 columns | rows garbled unless the GPIO was slowed four to eight times | A row setter that sends one clock per row (`--led-row-addr-type=5`) instead of re-shifting the register |
| A7 | PxMatrix issue 290, 2021-11. https://github.com/2dom/PxMatrix/issues/290 | two `P4-1921-64X32-8S-S1` outdoor 1/8 panels (a sibling silkscreen), ESP32 | "a lot of ghosting (4 leds in a row) and a strange offset behaviour" with two panels; one panel was fine | SPI clock just under 20 MHz and `setMuxDelay(1,1,1,1,1)` (1 us after each address change) |
| A8 | Falcon forum, "Bad P5 panels?", post 14, 2020-11-23, dkulp (FPP's lead developer). https://falconchristmas.com/forum/index.php?topic=13473.0 | outdoor panels on a BeagleBone cape | "My outdoor panels for my TuneTo sign ghost really bad at 5V. To get them to stop ghosting, I had to drop the voltage to less than 4.6 volts" | **Panel supply at 4.5 V**, the controller on its own 5 V supply. "Last year I ran at 4.8V ... but did have minor ghosting" |
| A9 | rpi-rgb-led-matrix Discourse topic 137, 2021-02. https://rpi-rgb-led-matrix.discourse.group/t/rpi-3b-outdoor-p2-5-128x64-adjacent-pixels-light-up/137 | outdoor P2.5 128x64 1/16, Pi 3B+ | "adjacent pixels are also highlighted" | "With a value of 1000, 2000 [ns LSB], the shadows disappeared, but the image began to blink". Unresolved |
| A10 | rpi-rgb-led-matrix issue 92, 2015. https://github.com/hzeller/rpi-rgb-led-matrix/issues/92 | 16x32, Pi 2 | faint pixels under text | hzeller: "The shadow pixels are not sent to the panel, it is the hardware of the panel not cleanly shutting off pixels ... It typically shows with very high contrast situations" |
| A11 | Arduino forum, 2019. https://forum.arduino.cc/t/ghosting-on-rgb-led-matrix-panel/589978 | NovaeLED P4 32x64 on a Mega; another maker's panel of the same size was clean | "The line below has an image of the line above it. It will wrap around from the 16th row to the first row as well." | Unresolved |

What these say together (LIKELY):

- The fault is in the panel, and it shows on bright content against black. Several maintainers say so in
  nearly the same words (A4, A10, and the README quoted in section 4).
- In A1 the copy switched on at one pixel value, because only the top bit plane's light ran up to the row
  change. That is a documented case where "nothing below a value, plain above it" came from grey-scale
  timing and not from a fixed fraction of the source's light. It is a precedent, not proof: A1's step was
  sharp (193 against 194), ours is soft (a trace at 128), and gamma 2.8 alone can give a soft one.
- In A4 fewer bit planes made the copy stronger, and a slower library made it weaker. Both point at the
  number and shortness of the light pulses, not at the picture.
- A8 is the only cure by hardware, and it is on outdoor panels. The DP5125E datasheet gives a reason in its
  section 12: it recommends an output voltage near 1 V and says to use "as low a VLED supply as possible"
  (section 5.2 below).
- The same chip pairing as ours can be clean: an 80x40 1/10-scan board with DP5125D columns and RUL5158C
  serial rows runs on DMD_STM32 with no ghost reported
  (https://github.com/board707/DMD_STM32/issues/104), and on rpi-rgb-led-matrix a batch with DP5125D was
  the clean one next to a batch with FM6124 that showed artefacts on black
  (https://rpi-rgb-led-matrix.discourse.group/t/artefacts-glitches-around-edges-of-displayed-objects-images-with-black-background/950).
  Both run far slower than our card (a few hundred Hz, 4 to 7 bit planes). CONFIRMED as reports.

Reports on the exact board family, none with ghosting and none with serial rows:
`P5-1921-64*32-8S-S2` (SM5166PF + DP5125D, issue 698), `P5(1921)64x32-8S` (HX6016SP + ICN2037, Discourse
1161), `P5-08S-1921` (SM5166 + MBI5124, https://github.com/mrcodetastic/ESP32-HUB75-MatrixPanel-DMA/issues/949),
`P5-1921-3264-8S-S3` (https://community.home-assistant.io/t/esphome-hub75-with-p5-matrix-help-needed/986665),
`YS-P5-320X160-8S-1921(PRO)-V1` (74HC138 + SM16169SH, https://github.com/hzeller/rpi-rgb-led-matrix/issues/1744).
**No report of the `H3.3` revision, of a `YP5-5125` sticker, or of what row chip those boards carry.**
A GitHub search for the markings returned nothing. CONFIRMED as a search result.

## 4. What the open-source drivers do for serial row drivers

All CONFIRMED by reading the code at the commits named at the top.

### 4.1 How the row is stepped

| Driver | Where | What goes on the wire for one row change |
|---|---|---|
| rpi-rgb-led-matrix, type 3 | `lib/framebuffer.cc` 246 to 278, `ABCShiftRegisterRowAddressSetter` | The whole register is re-shifted: `double_rows_` clocks on A with C high only at the wanted row's place, then one more A pulse. B is not touched. It runs for every bit plane (no early return), so the lit bit walks through every other row each time |
| rpi-rgb-led-matrix, type 5 | `lib/framebuffer.cc` 173 to 207, `B707ShiftRegisterRowAddressSetter` | B high; C high only when the row is 0; A high (written twice, "Longer clock time; tested with Pi3"); A low; B low. One clock per row, and only when the row changes |
| DMD_STM32 | `DMD_Multiplexer.cpp` 140 to 186, `DMD_Mux595::set_mux` | The same order as type 5 (type 5 is this code, contributed by its author). On the RP2040: "Add extra delay to avoid flickering": a wait after setting the data and A held high for twice that wait (lines 163 to 181) |
| ESP32-HUB75, `SM5368` (= `TYPE595`) | `src/ESP32-HUB75-MatrixPanel-I2S-DMA.cpp` 635 to 642 | "A is row clk, B is BK and C is row data". In the last two pixel clocks of a row: C (row 0 only) and B, then C, A and B. So **A is high for one pixel clock**, 50 to 125 ns at 20 to 8 MHz |
| PxMatrix, `SHIFTREG_ABC` | `PxMatrix.h` 1135 to 1151 | C high for row 0 only, A high, A low. B is "/Enable" (line 114) and is left alone |
| FPP, Protomatter, SmartMatrix | | No serial row support found; address lines only |

Two things stand out:

- The drivers disagree about B. DMD_STM32 and type 5 treat it as a latch held high around the clock; the
  ESP32 library calls it "BK"; PxMatrix calls it "/Enable" and never moves it; type 3 ignores it. Depuw's
  datasheet says B is the clock of the blanking-level register and nothing else (section 5.1). The drivers
  were written by trial on panels, and they work on some serial chips and not others: issue 815 records a
  panel with **ICN2018 rows and MBI5124 columns** that stayed dark, then ran "although not quite stably",
  under the ESP32 library's serial setting (https://github.com/mrcodetastic/ESP32-HUB75-MatrixPanel-DMA/issues/815),
  and issue 1774 has the type 3 setter failing on SM5368 and DP32020A until the GPIO was slowed four to eight
  times. LIKELY: "serial row driver" is a family of near-compatible parts, and a protocol that lights the
  right row on one of them can still be wrong in its timing for another.
- None of them meets the 500 ns row-clock width of the datasheets by design. The ESP32 library's 50 to
  125 ns is four to ten times too short; the others get there by accident of a slow processor. Where the
  pulse was lengthened, the comment gives flicker or stability as the reason, never ghosting.

### 4.2 The order of output enable, row change and latch

- rpi-rgb-led-matrix, `lib/framebuffer.cc` 981 to 1004: clock the next plane in while the last one still
  shows; "OE of the previous row-data must be finished before strobe"; "Setting address and strobing needs
  to happen in dark time"; set the row; pulse the latch; switch the output on. So the row changes with the
  output off and the old data still in the column latches, and the new data is latched after it.
- The same file, 981 to 982: "Rows can't be switched very quickly without ghosting, so we do the full PWM of
  one row before switching rows." DMD_STM32 carries the older Adafruit note to the same effect
  (`DMD_RGB.cpp` 326 to 332): interleaving the planes across rows "causes a green 'ghosting' effect on black
  pixels, a much worse artifact". **Both libraries change rows once per row per frame, on purpose.**
- ESP32-HUB75, `...I2S-DMA.cpp` 665 to 676: "need to disable OE before/after latch to hide row transition.
  Should be one clock or more before latch, otherwise can get ghosting"; `latch_blanking` 1 to 4 clocks
  (default 2, header lines 121 to 125). Its README: "Latch blanking controls for how many clock pulses
  matrix output is disabled via EO signal before/after toggling LAT signal. It hides row bits
  transitioning and different panels may require longer times".
- PxMatrix, `PxMatrix.h` 1244 to 1291 and 1177 to 1200: output off; set the row; shift the data; latch;
  output on for the show time. `setMuxDelay` adds microseconds after each address line change (1053 to
  1100); it is not applied in the serial branch.
- Protomatter, `src/core.c` 56 to 60 and 521 to 560: "Time (in microseconds) to pause following any change in
  address lines ... Some matrices respond slowly there": **8 us**, with the output off.
- FPP, `src/pru/FalconMatrixByRow.asm` 83 to 111 and 128 to 168: the "output by row" mode shows all planes of
  a row, then changes the row with the display off. With `OUTPUTBLANKROW` it first clocks a full row of
  zeros into the column drivers and latches it: "Some panels need a fully blank row to prevent some
  ghosting". Also `FalconMatrixCommon.asm` 92 to 96 ("LATCH HI NEEDS to be completely independent of all
  other GPIO calls or ghosting occurs") and `src/channeloutput/BBBMatrix.cpp` 151 to 156 and 180 to 183
  ("if max is too low, the low bit time is too short and extra ghosting occurs"; "low value cannot be less
  than 20 or ghosting").
- rpi-rgb-led-matrix README, on `--led-pwm-lsb-nanoseconds` (default 130): "some panels have trouble with
  sharp contrasts and short pulses that results in ghosting. It is particularly apparent in situations such
  as bright text on black background. In these cases increase the value until you don't see this ghosting
  anymore."

So the open-source answer to ghosting on plain shift-register column drivers has four parts: dark time
around the row change (microseconds, not hundreds of nanoseconds); a shortest light pulse of several
hundred nanoseconds or more; one row change per row per frame; and, in FPP, zeros in the column latches
before the row moves.

Our card, for comparison (CONFIRMED from the saved settings in the brief and yesterday's lane 03): 960 Hz
times 8 lines is 7680 row changes a second, 16 passes a frame; Blanking Value 3 is 300 ns; Minimum OE is
115 ns. Every one of the four is on the unfavourable side of what these libraries settled on.

## 5. What the chip and card makers say

### 5.1 The serial row driver (Depuw DP32020A, REV2.3, 2024-05-29)

https://cognigraph.com/6502/datasheet-DP32020A-chinese.pdf . CONFIRMED, my translation:

- Page 7: "because the parasitic capacitance of the LED anodes makes a discharge path at the moment the scan
  switches, the screen shows smearing; the user can use the DP32020A, which has a discharge circuit, ... and
  pair it with a constant-current driver with built-in pre-charge, the DP5125; this removes the upper and
  lower smearing completely" (搭配内建有预先充电功能的恒流驱动芯片 DP5125，如此即可能够完整地消除此上、下拖影现象).
- Page 11: "each row change is fixed at one DCK"; blanking time "equals the width of DCK high", **minimum
  500 ns**; set-up and hold 60 ns.
- Page 12: the blanking level is a 4-bit register, default 3.25 V, written by "8 clocks on RCK while DCK is
  low (4 dummy + 4 data)", at least 100 ns after the row change. Pin map: "DIN is the 138's C signal, DCK
  the 138's A signal, RCK the 138's B signal".
- Pages 1 and 5: 8 outputs, SOP16 or QFN16.
- Page 1: "integrates a serial decoding circuit that prevents several channels being on together; it
  prevents 3 or more channels turning on at once, which would burn the chip" (集成防止多通道同时开启的串行译码电路，
  可以防止 3 个及以上通道同时开启). The maker expects stray tokens in the register often enough to guard
  against them. Lane 02 notes our wall showed four outputs on at once under 138 decoding, so our chips have
  no such guard.

The Chipone ICND2018 sheet says the same things about its chip (yesterday's lane 03, section 1.2: 500 ns
minimum, level set by 8 to 23 RCLK pulses). LEDVision's "Blanking Voltage 2.0 to 3.75 V, default 3.25 V" is
this register. So the four RAM-only trials of this morning changed the row chip's clock width and its
discharge level, on the assumption that T2 and T3 obey this protocol.

### 5.2 The column driver (Depuw DP5125E, REV1.1, 2024-02-20)

https://www.lipuxin.com/_120241227/1504598661.pdf . CONFIRMED, my translation:

- Page 1: "on power-up the chip recognises its working mode; it is backward compatible with, and extends,
  the ordinary single-latch constant-current chips and the double-latch constant-current chips with column
  lower-ghost elimination" (普通单锁存恒流芯片和双锁存恒流列下消影芯片).
- Page 1, features, and the block diagram on page 6: "generic program: single latch, no ghost elimination,
  will not cause reverse voltage on the LEDs" (通用程序：单锁存无消影，不会造成灯珠反压); the diagram has a
  "protocol parser (single/double latch adaptive)".
- Page 18, section 12: best output voltage about 1 V; at VLED = 5 V the output voltage may be too high; "use
  as low a VLED supply as possible", or a series resistor or a Zener.

The sheet is the E part's; our sticker says only "5125" and no chip marking has been read. Its section 12
drawings are labelled DP5125D, so the family shares the text (LIKELY valid for ours, as lane 03 judged on
2026-09-29).

What follows (LIKELY): the DP5125's circuit against the lower ghost exists, and it is switched on by a
double-latch protocol, not by the generic one. LEDVision reads our card as "Normal Chip". I did not find
which LEDVision entry sends the double-latch protocol, nor a description of that protocol for the DP5125.
Not settled; it is lane 03's page.

### 5.3 Chipone on row drivers, and the names of the two ghosts

"一文读懂LED显示屏行驱动的六大挑战" (Chipone's article, read from the mirror
http://m.szledscreen.com/h-nd-160.html ; original https://zhuanlan.zhihu.com/p/658491428). CONFIRMED:

- Upper ghost (上鬼影): "when Row(n) is on, the row's parasitic capacitance charges to VCC. On the switch to
  Row(n+1) ... the charge drains through the LEDs and they glow faintly." Cure: the row chip pulls the line
  down to a blanking voltage; "usually VH < VCC - 1 V removes the upper ghost".
- The blanking voltage cannot simply be lowered: reverse voltage on the LEDs wants it above VCC - 2 V, a
  shorted LED wants it above VCC - 1.4 V, "so 3 V to 3.4 V (VCC = 5 V) is a reasonable choice".
- "Red LEDs have a forward voltage of 1.6 to 2.4 V, green and blue 2.4 to 3.4 V. By test a red LED lights at
  1.4 V." A row line that sits a little too high lights red first. That fits "the copy looks redder than the
  orange source" for any cause that leaves a small forward voltage on the victim row (LIKELY; it does not
  tell the causes apart).
- The article's table lists ICN2018 as the "8-channel, serial decoding, SOP16" part.

In this trade both classic ghosts fall on the row **next to the lit one in scan order**: the upper ghost
from the row line's charge, the lower ghost from the column line's, cured by the row chip's discharge and the
column chip's pre-charge. I found no trade source that describes a ghost at a larger fixed distance.

### 5.4 What the card makers call the settings (NovaStar, as a dictionary for LEDVision)

NovaLCT user manual V5.3.0, pages 32 to 36,
https://oss.novastar.tech/uploads/2020/04/NovaLCT-LED-Configuration-Tool-for-Synchronous-Control-System-User-Manual-V5.3.02.pdf .
CONFIRMED quotes:

- "Row Blanking Time: Used to adjust the ghost problem of the scanning type display. If the ghost problem is
  serious, increase the parameter value."
- "Line Changing Time: Works with row blanking time to adjust the ghost of the scanning type display."
- "Ghost Control Ending Time: Works with row blanking time and line changing time to adjust the ghost".
- "Blanking Time Height: Used to eliminate the lower ghost".
- "Delay Time of ABCDE Signals: Fix the problem that the afterglow cannot be eliminated because the decoding
  signals are not synchronized."
- "Isolated Pixel Afterglow: Eliminate the afterglow problem of isolated pixels."

LEDVision's untested Blanking Phase page (Line Switch Time 25, 4051 Enable Time 14, 4051 Disable Time 124)
is LIKELY the same set under other names. That mapping is my inference, not a source.

## 6. The cures, by kind, and whether a 5A-75E can reach them

"Evidence" is for the reports in sections 2 and 3, which are mostly the adjacent-row kind. None of these is
shown to cure a 4-row offset.

| Kind | The cure in the field | Evidence | On our wall |
|---|---|---|---|
| Controller setting: dark time at the row change | OE off for more clocks around the latch (A1, A3); microseconds after an address change (A7, Protomatter) | CONFIRMED cures for adjacent-row ghosts | LEDVision Blanking Value, already tried 3, 6, 11 (0.3 to 1.1 us) with no change by eye. The Blanking Phase page is untried. Reachable |
| Controller setting: longer shortest pulse | `--led-pwm-lsb-nanoseconds` from 130 up to 500 or 1000 ns (M3, A9, the README); FPP's floor on the low bit | CONFIRMED in those reports; A9 paid for it with flicker | Our Minimum OE is 115 ns. It rises with fewer grey levels, a lower refresh multiple or a higher Brightness Level. x16 to x4 moved it only to 134 ns, so that trial did not test this. Reachable |
| Controller setting: fewer row changes | One row change per row per frame (hzeller, DMD_STM32 by design); FPP "output by row" | CONFIRMED as design statements | Refresh multiple x16, x8, x4 tried with a mixed result. x1 untried. Reachable |
| Controller setting: slower signals | GPIO slowdown (A5, A6), lower pixel clock (A3, A7) | CONFIRMED for those panels | DCLK 15.6 to 10.4 MHz is available (lane 03 of 2026-09-29 judged it margin, not a fix). Reachable |
| Column-driver protocol | The driver type in the ESP32 library; for DP5125, the double-latch mode that turns on its lower-ghost circuit (5.2) | The datasheet is CONFIRMED; no field report of anyone switching it on | LEDVision's driver-chip setting, now "Normal Chip". Which entry to choose is not settled. Reachable in principle |
| Row-driver protocol or decoder choice | One clock per row instead of re-shifting (A6); separating the row-chip setting from the column-chip setting (issue 815) | CONFIRMED for SM5368, DP32020A, ICN2018 panels | LEDVision's decoder list has about 30 entries; about 15 were tried, and "ICN2018/3018" was the only one that lit one row. Serial entries never tried: 5953/5958, VOD5958, ICND2019, GM5018, TA6018, TC6960, D7266, MBI5981, MBI5988, LS97xx (hardware.md 135 to 157). Reachable |
| Clearing the column data before the row change | FPP's blank row (`OUTPUTBLANKROW`) | CONFIRMED in code; no thread found that names the panels it helped | Not reachable: the card owns the scan. A chip setting with "blanking" of its own is the nearest thing |
| Select lines | Drive or ground every select pin (M4, M5); a sound ground (M5, PxMatrix README) | CONFIRMED cures, and the only ones for a fixed-offset copy | Does not apply: our copy's distance changes with the refresh multiple (lane 02), and the card drives A, B and C |
| Hardware: supply voltage | Panel supply below 4.6 V (A8); the DP5125E sheet's "as low a VLED as possible" | One CONFIRMED field report, from a reliable source, on unnamed outdoor panels | The supply's trim pot, if it has one. The card works from 3.8 V (its specification, lane 03 of 2026-09-29). A hardware change: the owner's word first |
| Software workaround | Lower brightness (the ESP32 library's example `4_OtherShiftDriverPanel.ino`, line 64: "If you experience ghosting, you will need to reduce the brightness level"); more bit depth (A4); never pure black next to bright (A4: "only visible on black pixels") | CONFIRMED as workarounds, none a cure | Fully reachable in our sender: cap the value of thin bright content on black at the level where the copy is invisible (observation 3: nothing under 64, a trace under 128), or thicken it. Costs contrast |

## 7. What would tell the readings apart

From this lane only. The mechanism itself belongs to lane 02.

| If the fault is | It predicts | Existing or cheap observation |
|---|---|---|
| A classic upper or lower ghost (row-line or column-line charge), the kind in section 3 | The copy is on the scan-adjacent row: 1 row above or below, and row 8 wraps to row 1 of the same half. It scales with the number of row changes. It is redder than the source | The one-row-at-a-time map over 16 positions. The arm's "1-row copy just above" may be this; the copy 4 below cannot be, because a serial driver steps in physical order (the wizard saw rows 1 to 8 in order, hardware.md 161 to 176) |
| Two rows selected together by a fixed pairing (the class of M4 and M5) | The copy is at the same distance at every refresh multiple; it carries the source's full column pattern | Already answered by lane 02's measurement: +4 at x16, +1 and +5 at x4. Does not fit |
| Grey-scale timing at the card (short pulses of the top planes running into the row change), as in A1 | A threshold in pixel value that moves with Brightness Level and grey depth; the copy on the adjacent row | Level lines at the same pixel values but a different Brightness Level or grey depth. The row distance does not fit on its own |
| The card's sequencing with a serial row driver (lane 02: a second token, or a plane shown again, a fixed 0.52 ms and 2.6 ms after the source) | The copy's distance in rows follows the row slot: +2 at x8; on its own source, so gone, at refresh 1920. It carries whole bit planes, so a step at one pixel value (as in A1). Blanking and discharge settings do nothing, as this morning's four trials found. A different decoder entry or driver protocol could change it; supply voltage and pre-charge would not | Lane 02's two predictions (x8, refresh 1920), both RAM-only. From this lane: the untried serial decoder entries |

Before lane 02's measurement I wrote that the one-row-at-a-time map came first. It is still worth having, but
the x8 and refresh-1920 trials now separate the readings faster. If they come out as lane 02 predicts, the
ordinary-ghosting cures of section 3 (dark time, longer pulse, supply voltage, pre-charge) are aimed at a
different fault, and the field experience that applies is section 4.1's: serial row chips that are driven
by a protocol written for a near relative.

Reversible trials this lane's reading supports, one variable at a time, all by **Send** (RAM only). **Every
LEDVision timing change silently sets Brightness Level back to 8: set it to 3 again before every Send.** A
decoder or chip-type change may do the same; check it. Nothing is to be saved to the receiver.

Order revised after lane 02's measurement: its own x8 and refresh-1920 trials come before any of these.

1. The untried serial decoder entries, beginning with 5953/5958. Do it at Brightness Level 1 as the log did:
   a wrong decoder can light many rows at once. Tests whether another protocol lights one row and leaves no
   copy. This is the trial the field record of near-compatible serial chips points to.
2. The driver-chip entry that LEDVision offers for double-latch or "with blanking" general chips, if lane 03
   can name one. Tests 5.2, and changes what the card puts on the latch line. A wrong chip type can give a
   wrong picture; it does not write flash.
3. Grey level 8192 down one or two steps, to raise Minimum OE (read the figure LEDVision prints). Tests the
   "longer shortest pulse" cure; only worth doing if the copy turns out to be ordinary ghosting after all.
4. The panel supply at 4.5 to 4.6 V, measured at a panel, with the owner's agreement. A hardware trial; it
   is undone by turning the pot back. Tests A8; the same condition as trial 3.

## 8. What I could not settle

- Whether any of the cures in section 6 touches our copy. No source covers a copy several rows away, and
  none covers one that comes a fixed time after its source.
- Whether anyone has seen a Colorlight card leave a second token in a serial row driver. I did not search
  under that description (lane 02's measurement came after the search); nothing I read suggests it.
- What T2 and T3 are. Lane 02 counts them as SOP16 parts; no marking has been read.
- Which LEDVision driver-chip entry sends the DP5125's double-latch protocol, and what that protocol is.
- What the Parallax forum thread says about DP5125D panels bought from a Christmas-light vendor (the forum
  pages could not be read). The driver that came out of it was read (CONFIRMED, commit `84a1236`): version
  3.0.1 of 2024-01-15 "Add support for panels using DP5125D chips"; its chip table gives them ABC addressing,
  1/8 scan, no init sequence, and the latch style "Offset + Overlap" ("latch position overlaps last clock"),
  the same as its FM6126A entry (`DOCs/ChipCharacteristicsMatrix.md` lines 341 to 360 and 763 to 767,
  `driver/isp_hub75_hwEnums.spin2` lines 77 to 82). It says nothing about ghosting or the row chip. If those
  were Wired Watts panels, that thread is the nearest report to our board.
- The Facebook groups where most Colorlight and P5 questions now go.
- Whether issue 970's far dots are a row copy (section 2, M3).
- The rows of M1 and M2 in physical terms.

## 9. Sources

Reports
- ESP32-HUB75-MatrixPanel-DMA issues 64, 545, 698, 733, 805, 815, 838, 845, 861, 885, 920, 949:
  https://github.com/mrcodetastic/ESP32-HUB75-MatrixPanel-DMA/issues/ (number)
- rpi-rgb-led-matrix issues 92, 970, 1725, 1744, 1774: https://github.com/hzeller/rpi-rgb-led-matrix/issues/ (number)
- rpi-rgb-led-matrix Discourse topics 137, 950, 1056, 1161, 1226: https://rpi-rgb-led-matrix.discourse.group/t/ (number)
- PxMatrix issues 38, 290: https://github.com/2dom/PxMatrix/issues/ (number)
- DMD_STM32 issues 104, 134, 168 and the chip table: https://github.com/board707/DMD_STM32/issues/ (number),
  https://github.com/board707/DMD_STM32/wiki/Led_drivers
- Falcon forum, "Bad P5 panels?": https://falconchristmas.com/forum/index.php?topic=13473.0
- Arduino forum: https://forum.arduino.cc/t/ghosting-on-rgb-led-matrix-panel/589978
- Read and found to hold nothing on ghosting: https://falconchristmas.com/forum/index.php?topic=16300.0 ,
  https://falconchristmas.com/forum/index.php?topic=14281.0 ,
  https://auschristmaslighting.com/threads/problems-with-ray-wu-p5-panels-colorlight-card.12585/ ,
  https://auschristmaslighting.com/threads/help-with-setting-up-64-32-1-8-scan-p5-e-top-panels-in-ledvision.12846/ ,
  https://auschristmaslighting.com/threads/p10-display-issues.12667/ , https://esphome.io/components/display/hub75/ ,
  https://kno.wled.ge/advanced/HUB75/

Code (paths as in section 4)
- https://github.com/hzeller/rpi-rgb-led-matrix (`lib/framebuffer.cc`, `README.md`)
- https://github.com/mrcodetastic/ESP32-HUB75-MatrixPanel-DMA (`src/ESP32-HUB75-MatrixPanel-I2S-DMA.cpp`, `.h`, `README.md`)
- https://github.com/board707/DMD_STM32 (`DMD_Multiplexer.cpp`, `DMD_RGB.cpp`)
- https://github.com/2dom/PxMatrix (`PxMatrix.h`, `README.md`)
- https://github.com/adafruit/Adafruit_Protomatter (`src/core.c`)
- https://github.com/FalconChristmas/fpp (`src/pru/FalconMatrixByRow.asm`, `src/pru/FalconMatrixCommon.asm`,
  `src/channeloutput/BBBMatrix.cpp`)
- https://github.com/ironsheep/P2-HUB75-LED-Matrix-Driver (`ChangeLog.md`, `DOCs/ChipCharacteristicsMatrix.md`,
  `driver/isp_hub75_hwEnums.spin2`)

Datasheets and manuals
- Depuw DP32020A REV2.3: https://cognigraph.com/6502/datasheet-DP32020A-chinese.pdf
- Depuw DP5125E REV1.1: https://www.lipuxin.com/_120241227/1504598661.pdf
- Macroblock MBI5124 ("integrates the pre-charge circuit which can relieve the ghosting"):
  https://www.mblock.com.tw/upload/Datasheet/LED%20Driver%20IC/MBI5124/MBI5124%20Preliminary%20Datasheet_V1.01_EN.pdf
- Chipone, row drivers: http://m.szledscreen.com/h-nd-160.html (mirror of https://zhuanlan.zhihu.com/p/658491428)
- NovaLCT manual V5.3.0: https://oss.novastar.tech/uploads/2020/04/NovaLCT-LED-Configuration-Tool-for-Synchronous-Control-System-User-Manual-V5.3.02.pdf
- Utility model CN203721164U (row-line charge and a discharge circuit): https://patents.google.com/patent/CN203721164U/zh

Our own record
- /Users/trey/dev/codeisart-ledvision/docs/superpowers/workflow/evidence/hardware.md (lines 128 to 183, 295 to 349)
- /Users/trey/dev/codeisart/docs/superpowers/reviews/2026-09-29-flicker/03-panel-electrical.md
- Scratch (issue texts, images, PDFs): /private/tmp/claude-502/-Users-trey-dev-codeisart/489bd663-dd66-40f0-8952-22058687bf7d/scratchpad/lane04/
