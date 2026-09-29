# Lane 03: panel chips, scan settings, power and grounding

Date: 2026-09-29. Read-only research; nothing was sent to the wall and no repo file was changed.
Labels: CONFIRMED (primary source or our own measurement), LIKELY, SPECULATIVE. "Not confirmed" means I
looked and could not settle it.

## 0. Verdict in short

| Cause | My estimate | Why |
|---|---|---|
| Data timing (when and how often frames and the sync packet reach the card) | about 85 % | The flicker follows the sender's frame rate (20 fps bad, 30 fps some, 60 fps steady) and stops when the sender stops. Nothing electrical changes between those cases. |
| Panel scan settings on their own | about 10 % | The settings are inside what the chips can do. One value is out of the row driver's datasheet range (blanking 300 ns against a 500 ns minimum), but the wall is steady with those same settings when the card holds a frame. The settings do decide HOW the card reacts to a slow sender (960 Hz x16 means a 60 Hz frame), so they are part of the fix, not the root cause. |
| Electrical (supply sag, ground noise, ribbon signal integrity, Ethernet ground loop) | about 5 % | Four separate measurements argue against it (section 3.1). Not zero, because supply voltage, supply model and ribbon lengths were never recorded. |

The percentages are my judgement, not a calculation.

## 1. The chips

### 1.1 What the photos show (CONFIRMED from the photos unless noted)

Files: `/Users/trey/dev/codeisart-ledvision/docs/superpowers/workflow/evidence/hardware/14-panel-back.jpg`,
`.../27-panel-back-power-row-drivers.jpg`.

- Silkscreen `P5-1921-64X32-8S-H3.3`, pink sticker `YP5-5125HG505-Y2076`.
- Column drivers: 24-pin narrow packages, designators UR / UG / UB numbered to 15 at least. No top marking is
  legible in either photo. I could not read any chip marking.
- Row drivers T2 (above POWER1) and T3 (below POWER1): small SOP parts with blank tops. The log says 10 pins;
  at the photo's resolution I count 4 to 5 leads a side and cannot confirm 10 against 8. A third part of the
  same size sits further down in photo 14 (label looks like "T1", not confirmed).
- Bulk capacitors: several 220 uF 10 V electrolytics per panel (EC3, EC8, EC9, EC11 and more), plus small
  ceramics next to each driver. So the panel has the usual local decoupling.
- Power connector: 6-way footprint marked VCC, VCC, 2.8V, 2.8V, GND(-), GND(-). The 4-pin plug sits on
  2.8V, 2.8V, GND, GND. The VCC pads are empty. L1 and L2 beside them are fitted.
- HUB75 silkscreen: R1 G1 / B1 GND / R2 G2 / B2 N / A B / C N / CLK LAT / OE GND. Only A, B, C.
- Q6 and Q7 (16-pin footprints beside JOUT) are empty.

Open point from the photos (SPECULATIVE): the "2.8V" marking means this board design can run as an
"energy saving" panel with a lower LED rail. The DP5125 datasheet recommends a lower LED voltage so the
driver's output sits near 1 V (section 12 of the datasheet, URL below). On our panels the plug feeds the
pads marked 2.8V and L1/L2 probably join the two rails. The supply voltage was never recorded
(hardware.md line 251). This is a multimeter check (test E1), not a flicker theory: DP5125 needs 3.3 V or
more on VDD, and the panels light, so the rail is not at 2.8 V.

### 1.2 Row driver: ICN2018 / ICN3018 family

Source: Chipone ICND2018 datasheet V1.6 (May 2021),
https://downloads.olympianled.com/PDF/Driver%20ICs/ICND2018-datasheet-EN-2021-V1.6.pdf ; product pages
https://olympianled.com/product/chipone-icn2018-icnd2018-row-driver/ and
https://olympianled.com/product/chipone-icn3018-icnd3018-line-driver/

CONFIRMED from the datasheet:
- "ICND2018 is a 8-channel power switch for LED display. ICND2018 Integrated 74HC595 (8-bit serial-in,
  serial parallel-out shift register) and 8 Channel P-Channel Enhancement Mode MOSFET driver." It adds
  "Ghosting Reduction, Caterpillar Cancelling and LED Protection circuit".
- Pins: VDD, SDIN, DCLK (shift clock), RCLK (register input), OUT0 to OUT7, DOUT, GND. Packages SOP16 and
  QFN16. ICN3018 is the 16-channel part in SSOP24 / QFN24.
- There is no address decoding. Each rising edge of the row clock moves the lit row on by one: "The rising
  edge of DCLK is a line feed signal. After receiving the rising edge of DCLK, the data is shifted once, and
  the corresponding open channel is also shifted."
- The blanking is the row clock's pulse width: "The width of DCLK is the elimination time, so we need to do
  DCLK width and interface elimination parameter linkage." Minimum "Ghost reduction time, DCLK pulse width":
  **500 ns**. Setup 20 ns, hold 20 ns.
- The ghost-elimination level is set by the number of RCLK pulses sent while the row clock is low (8 to 23
  pulses, levels 2.0 V to 3.75 V, default 1101).
- Supply 3.0 to 5.5 V. Output propagation 48 ns / 220 ns, rise 46 ns, fall 180 ns (typical, 2 nF load).
- Note the name clash: "DCLK" in this datasheet is the ROW clock. LEDVision's "DCLK 15.6 MHz" is the pixel
  shift clock of the column drivers. They are different signals.

What follows for our panel:
- CONFIRMED (our measurement, hardware.md 14:00): LEDVision's "ICN2018/3018 Decoding" is the only setting
  of about 15 tried that lights one row.
- LIKELY: T2/T3 are not the Chipone SOP16 part itself but a compatible serial row driver in a smaller
  package. A 10-pin part fits exactly VDD, GND, SDIN, DCLK, RCLK, DOUT and 4 outputs, so two of them make the
  8 scan lines. I found no datasheet for such a part; the search for one returned nothing useful.
- Consequence: the three HUB75 lines A, B, C carry a clock, a latch/config line and serial data, not a
  binary address. A row driver of this kind keeps no absolute position. If it misses one clock edge, the
  picture sits one scan line off until the card feeds the next start bit (at most one scan cycle, about 1 ms
  at 960 Hz).

Third-party lists agree on the type: DMD_STM32's chip table lists ICN2018 as a "595" type multiplexer
(https://github.com/board707/DMD_STM32/wiki/Led_drivers). rpi-rgb-led-matrix has row address types 3 and 5
for "ABC-addressed panels" of this kind
(https://raw.githubusercontent.com/hzeller/rpi-rgb-led-matrix/master/README.md).

### 1.3 Column driver: DP5125 family (Depuw)

Source: Depuw DP5125E datasheet REV1.1 (2024-02), reached from Depuw's product list
http://www.depuw.com/cn/pro/193.html , entry "DP5125F/E", which redirects to
https://www.lipuxin.com/_120241227/1504598661.pdf . I did not find a datasheet titled DP5125D; this one's
section 12 drawings are labelled "DP5125D", so the family shares the document. Treat the numbers as the
family's, LIKELY valid for the D.

CONFIRMED from the datasheet (Chinese, my translation):
- "16-channel general-purpose constant-current driver". Block diagram: a 16-bit shift register, two 16-bit
  latches, 16 constant-current outputs, a "protocol parser (single/double latch adaptive)" and a
  "black-screen energy saving" block. **No PWM engine, no grey-scale memory, no GCLK pin.** Pins: SDI, CLK,
  LE, OE, SDO, REXT, OUT0 to OUT15, VDD, GND (QSOP24).
- Maximum clock ("maximum data transfer frequency") **30 MHz**. CLK to SDO delay 54 to 55 ns typical.
- OE to output delay 31 to 33 ns, output rise and fall 45 ns each, fastest output response 40 ns at 5 V.
- Supply 3.3 to 5.5 V; 2 to 40 mA a channel at 5 V.
- Supply current is specified at "refresh rate 960", white screen 4.91 mA, black screen 0.2 mA. The
  black-screen figure is the energy-saving mode: the chip powers its outputs down when its data is all zero.
- "General program: single latch, no blanking". The chip itself does no ghost removal in the generic mode;
  that is left to the row driver and the card.

Other sources say the same: "The driver DP5125 is a completely standard driver"
(https://rpi-rgb-led-matrix.discourse.group/t/support-for-dp5125b-chipset/1056); DMD_STM32 lists DP5125 as
a "standard" driver, fully tested (https://github.com/board707/DMD_STM32/wiki/Led_drivers). LEDVision
reads the card's chip setting as "Normal Chip" (photo `34-card2-params-read-back.png`).

Answer to the brief's question: **it is a plain constant-current shift register, the same class as ICN2037
and MBI5124. The card does all the grey-scale timing.** Every brightness level is made by the card
switching OE and re-shifting bit planes, so the card's refresh scheme and its reaction to frame timing
decide what the eye sees. With a PWM/memory chip the chip would keep refreshing on its own clock and hide
the sender's timing; here nothing hides it.

One side effect to keep in mind (SPECULATIVE, low weight): the black-screen energy saving means an
all-black frame puts the column drivers to sleep and the next lit frame wakes them. The wake-up time is not
in the datasheet. It cannot explain flicker on a static lit picture.

### 1.4 Sibling panels

- `P5-1921-64*32-8S-S2`: SM5166PF rows (138 type) and DP5125D columns; the report has no settings and no
  answer (https://github.com/mrcodetastic/ESP32-HUB75-MatrixPanel-DMA/issues/698).
- `P5(1921)64x32-8S`: ICN2037 columns and HX6016SP rows (138 type), needed a custom pixel map
  (https://rpi-rgb-led-matrix.discourse.group/t/p5-1921-64x32-8s/1161).
- A 64x64 with DP5125D + DP32020A (serial rows): "it flickered with some" driver types in the ESP32
  library; the MBI5124 type worked best
  (https://github.com/mrcodetastic/ESP32-HUB75-MatrixPanel-DMA/issues/645).
- I found **no report of the H3.3 revision** and no published receiver-card settings for this board. Not
  confirmed: whether Wired Watts' guide was written for it (their product page lists SMD 2121 and says the
  product is discontinued, https://wiredwatts.com/pnp5o ; our board says 1921).
- The closest field report to our symptom is on the Falcon forum: a Wired Watts P5 kit on a Colorlight card
  fed by FPP flickered on random rows, and "when the Pi is not running a sequence or in a pause ... the
  flickering goes away". A firmware downgrade (13.04 to 11.09) did not help; the thread has no resolution;
  one experienced user placed the problem "upstream with your source"
  (https://falconchristmas.com/forum/index.php?topic=16375.0). Same pattern as ours: steady when the sender
  is quiet.

## 2. Are the saved scan settings sensible?

Saved (CONFIRMED, photo `34-card2-params-read-back.png`): refresh 960, Multiple "Refresh x 16", grey 8192,
DCLK 15.6 MHz, **Blanking Value 3 "x100ns"**, Brightness Level 3, Brightness Percent 23 %, **Minimum OE
115.2 ns**, cabinet width 128 with the limit shown as "<=216".

### 2.1 The timing budget (my arithmetic)

- 960 Hz x 8 scan lines = 7680 row slots a second = 130 us a slot.
- Shifting one 128-bit line takes 128 / 15.6 MHz = 8.2 us (12.3 us at 10.4 MHz): 6 to 9 % of the slot.
- 15.6 MHz is half the DP5125's 30 MHz limit.
- The width limit "<=216" at these settings shows LEDVision itself sees headroom: we use 128.

So 960 Hz x16 at 15.6 MHz is **not past what the panel can do** (LIKELY; the chip limits are CONFIRMED,
the margin on our ribbons is not measured). It is an ordinary setting for generic chips:

- Linsn's troubleshooting page: conventional chips (ICN2037, FM6124, MBI5020 class) "can only flash to 960
  or 1920Hz"; pushed higher "it will flash and drag. When it's down to 960, it will display normally"
  (https://www.linsnled.com/troubles-of-led-display-configuration-how-to-locate-and-solve.html).
- Depuw specifies the DP5125's supply current at refresh 960.

### 2.2 What "Refresh x16" means, and why it matters here

Source: "The refresh multiplier determines how many times a single frame from the video source is refreshed
on the LED screen ... if a video source has a frame rate of 60Hz and the refresh multiplier is set to 32,
the effective refresh rate becomes 1920Hz (60Hz x 32)"
(https://www.colorlitled.com/performance-settings-led-receiver-card/).

So 960 Hz with x16 is a **60 Hz frame**: 16 refresh passes per incoming frame. INFERENCE (LIKELY): with a
plain shift-register chip and 8192 grey levels the card spreads the bit planes over those 16 passes, so one
complete grey-scale cycle lasts one frame period, 16.7 ms. If the sender's frame or sync does not arrive on
that 60 Hz beat, a cycle is cut short, stretched or restarted, and the light put out in that period
changes. That is a whole-wall, even brightness step with no shift and no missing rows, which is what the
phone video shows (observation 2), and it predicts "steady at 60 fps, worse as the rate drops", which is
what observation 5 shows. The card's own spec sheet says it adapts to "23.98/24/29.97/30/50/59.94/60Hz"
input (5A-75E Specification V8.2.2,
https://www.colorlitled.com/wp-content/download/colorlight/file/Colorlight%205A-75E%20Specification%20V8.2.2.pdf),
but that is written for Colorlight's own senders; how firmware 13.17 treats a raw-socket sender at 20 fps
is the protocol lane's question. Not confirmed by me.

### 2.3 Why Wired Watts says "DCLK as low as possible" and "x16 to x8"

CONFIRMED from the guide (https://www.wiredwatts.com/colorlight-setup-for-outdoor-p5-panels): both
sentences are about getting the cabinet size **in range**, not about flicker:

- "Check your cabinet setting, if anything is in red, adjust the multiple down from refresh x16 to refresh
  x8. That should make your matrix come in range if it was out."
- "If the matrix is still out of range, set the DCLK as low as possible and adjust the refresh rate until
  you are able to get the panel in range."

Their kits are many panels wide; a wide chain needs more shift time per row, so the multiple has to come
down. Our 128-wide cabinet is in range at x16 (limit 216). The guide gives no reason beyond that. The
general reason to prefer a low DCLK is signal margin: "an excessively high DCLK can cause data
transmission errors ... adjust the DCLK to a lower value that still meets the needs of the other
parameters" (https://www.colorlitled.com/performance-settings-led-receiver-card/).

### 2.4 The one value that is out of range: blanking

- CONFIRMED: LEDVision's Blanking Value is in units of 100 ns (the dialog prints "x100ns"). Saved value 3 =
  **300 ns**. The factory file had 11 = 1100 ns (hardware.md line 278). The first wizard run gave 0.
- CONFIRMED: the ICND2018 datasheet's minimum row-clock pulse width / ghost-reduction time is **500 ns**.
- LIKELY, not confirmed: that LEDVision's Blanking Value is what sets that pulse width when the decoder is
  "ICN2018/3018". The datasheet's sentence about "interface elimination parameter linkage" says the two must
  be tied together, and that is the only blanking parameter LEDVision shows.
- What too little blanking does, by the datasheet's mechanism: weak ghosting (a faint copy of a row on its
  neighbour) and, at worst, a marginal row clock. It does not explain flicker that stops when the sender
  stops, because the scan signals are the same in both cases. It is a fault to fix anyway.

### 2.5 Minimum OE 115 ns

The shortest light pulse is 115 ns. The DP5125's output needs about 30 ns delay plus 45 ns rise and 45 ns
fall, so the shortest pulse is mostly edges. That makes the darkest grey steps inexact and
temperature-dependent; it does not make flicker. LEDVision warned "Minimum OE is 0" at Level 1
(hardware.md line 155); Level 3 cleared it. Colorlit's page says minimum OE "should not be set below 8ns",
which is far below what this chip can form.

### 2.6 What I would change, in order

All of these need LEDVision and the owner's OK to save; every change of DCLK or Multiple silently resets
Brightness Level to 8 (hardware.md line 156), so check the level before every Send.

1. **Blanking 3 -> 6** (600 ns, above the datasheet minimum), and try 11 (the factory value) if ghosting is
   visible. Cost: a fraction of a percent of brightness. Confidence it helps the flicker: low. Confidence it
   is the right value for the row driver: medium.
2. **Keep 960 Hz / x16 only if the sender will hold a steady 60 fps.** If the installation must send 20 or
   30 fps, test a setting whose frame period matches the sender, in LEDVision, one step at a time (test S2
   below). I cannot say from documents which combination the card accepts.
3. **DCLK 15.6 -> 10.4 MHz** if LEDVision keeps the width limit at or above 128 without red. It did not
   change the flicker (observation 3), so this is margin for the second panel in each chain and for heat,
   not a fix.
4. Leave grey 8192, gamma 2.8 and Level 3 alone until the flicker is settled; change one thing at a time.

## 3. Electrical causes

### 3.1 The evidence already in hand (all CONFIRMED, our measurements)

| Observation | What an electrical cause would predict | What happened |
|---|---|---|
| Sender stopped, card holds the frame (obs. 1) | Same picture, same LED current, same scan signals: supply sag and ribbon faults would still show | Steady, std 0.34, no dips in 241 frames |
| Same bars at 20, 30, 60 fps (obs. 5) | More packets a second means more Ethernet activity: a coupling fault would be worst at 60 fps | The opposite: 60 fps is steady, 20 fps is worst |
| Brightness 10 % against 23 % at 20 fps (obs. 5) | LED current more than doubles: sag-driven flicker would grow | Same flicker |
| DCLK 15.6 -> 10.4 MHz (obs. 3) | A signal-integrity fault on the ribbons would change | "Same" |
| Two chains, four panels, short and long ribbon (hardware.md 13:00) | A cable or panel fault would sit on one chain or panel | Whole wall, even, "no shift, no missing rows" |

The second row is the strongest. I cannot construct an electrical mechanism that is bad at 20 packets-bursts
a second and clean at 60.

### 3.2 Supply sag or ground noise from the shared 5 V supply

- The card draws 3 W (0.6 A) at 3.8 to 5.5 V (5A-75E Specification V8.2.2, page 4). The panels draw amperes.
  My estimate, not measured: an outdoor P5 64x32 at full white is of the order of 8 to 15 A; at the card's
  23 % cap, 2 to 4 A a panel. Wired Watts lists the panel's current as "TBD" (https://wiredwatts.com/pnp5o).
- A sag needs a load change. With a static picture the load does not change when a frame arrives: the card
  re-shifts the same bits either way. So a static test picture cannot modulate the supply. Moving content
  can (a white flash is a load step of several amperes), and that is worth a test on the real show content,
  but it is a different symptom from the one reported.
- The card's working range reaches down to 3.8 V, so a card brown-out from the shared rail needs a sag of
  more than a volt. A reset would show as a black wall for a second or more, not an 8 % dip.
- Verdict: **unlikely** as the cause of the reported flicker (about 3 %). Still measure the rail (test E1):
  the supply model and the voltage at the panels were never recorded.

### 3.3 Ribbons, the second panel in each chain, 15.6 MHz on 5 V HUB75

- Bit errors on the data or clock lines give sparkle: wrong pixels, coloured dots, more on the second panel
  than the first, and the same whether the sender runs or not. None of that is reported.
- The noise on "the last row or two" at 60 fps (obs. 5) is NOT this. A 1 ms pause between the last row
  packet and the sync packet clears it, so it is the sync arriving before the last rows are stored: data
  timing. LIKELY.
- One electrical route to a picture that "shifts": a serial row driver that misses a row clock shows the
  picture one line off for up to a scan cycle (section 1.2). The camera found no shift (max 0.4 px,
  hardware.md line 153). Noted for completeness. SPECULATIVE.
- General advice that does apply: short ribbons ("Make sure to have as short as possible flat-cables",
  hzeller README), and the lowest DCLK that stays in range.
- Verdict: **unlikely** (about 1 %).

### 3.4 Ethernet cable shield and ground loops

- Every Ethernet port has isolation transformers (about 1500 V); the data pairs carry no DC path between
  the PC and the card. With unshielded cable there is no ground connection at all through the link:
  "UTP cables provide isolation between stations that might have unequal ground potentials"
  (https://industrialmonitordirect.com/blogs/knowledgebase/industrial-ethernet-shield-grounding-avoiding-ground-loops,
  https://e2e.ti.com/support/interface-group/interface/f/interface-forum/209010/ethernet-cable-shield-grounding).
- A shielded cable with metal plugs joins the PC's chassis to the card's jack shell. If the 5 V supply's
  negative is also earthed, that closes a loop. A loop carries hum at mains frequency and its harmonics; it
  would not know the sender's frame rate, and it would be there with the sender stopped and the cable
  still plugged in (obs. 1 was taken with the cable in).
- Which cable is in use (shielded or not) is not recorded.
- Verdict: **unlikely** (about 1 %). Use an unshielded Cat5e/Cat6 patch cable at the event; it removes the
  question.

### 3.5 Generator power (2 kW inverter generator)

Nothing here explains the bench flicker (the bench is on mains). Planning points:

- Capacity is not the problem: four panels at the 23 % cap are of the order of 50 to 80 W, plus the
  computer. Full white at 100 % could reach a few hundred watts. Estimates, not measured.
- **Eco / throttle mode**: the engine idles low and takes time to answer a load step, and the output dips
  meanwhile ("there is a lag between the increased demand/load and the generator increasing output";
  https://www.truckcamperadventure.com/solving-the-dreaded-inverter-and-generator-eco-mode-conflict/ ,
  https://www.powerequipmentforum.com/threads/question-s-about-eco-mode-on-a-champion-inverter-generator.28178/).
  A wall that jumps from dark to bright is a load step. A switching 5 V supply rides through short dips on
  its hold-up time; check the figure for the supply in use (for example Mean Well LRS-350,
  https://www.meanwell.com/Upload/PDF/LRS-350/LRS-350-SPEC.PDF). Plan: rehearse on the generator with eco
  mode on and off; if the wall dims on bright scenes with eco on, turn it off.
- **Other loads on the same generator** (sound, a compressor fridge, a kettle) make far larger steps than
  the wall. Give the wall and its computer their own generator or test with the neighbours' loads on.
- **Supply sizing and wiring**: size the 5 V supply for full white at the brightness cap with margin; feed
  each panel from the distribution point, not panel to panel; check 5 V at the far panel under white.
- **Earthing and wet ground**: portable inverter generators usually have a floating neutral. Use an RCD/GFCI
  on the feed and bond the wall's metal frame as the generator's manual says. This is a safety point, not a
  flicker point.
- The sender computer and the wall should share the same source, so there is one earth reference.

## 4. Discriminating tests

### 4.0 Two rules for every test

1. **Record the control first.** Card holding the frame, sender stopped, same camera position, exposure and
   focus locked. With 960 Hz x16 the bit planes are spread over a 16.7 ms cycle, so a 240 fps clip of a
   perfectly steady wall will itself show a repeating brightness pattern and rolling-shutter bands
   (INFERENCE from section 2.2). Only a difference from the control counts.
2. One variable a test. Use the same static picture for all of them: a mid-grey field with one bright
   single-pixel horizontal line and one vertical line (the lines show shift and ghosting, the field shows
   brightness dips).

The stimulus that flickers reliably is the FPP-order test sender at 20 fps; use it as the "bad" case.

### 4.1 Ordered list

Predictions are for three hypotheses: **T** = data timing, **E** = electrical, **S** = scan setting alone.

| # | Test (one variable) | Instrument | T predicts | E predicts | S predicts |
|---|---|---|---|---|---|
| 1 | **Slow-motion shape.** 240 fps clips of: control (held), 20 fps, 30 fps, 60 fps | Phone, exposure locked | Whole wall steps in brightness together, at the sender's rate or a beat of it; held and 60 fps look alike | Rolling band unrelated to the sender's rate, or sparkle, worse on the 2nd panel of a chain; present in the control too | Same artefact in every clip including the control |
| 2 | **Traffic the card ignores.** Card holding a frame; send bursts of frames with an EtherType the card does not use, same size and rate as a 20 fps stream | Eye + 30 fps clip | Steady | Flicker (the link is busy, the PHY and the cable carry the same energy) | Steady |
| 3 | **Rate sweep around 60.** Same picture at 50, 59, 60, 61, 120 fps | Eye + clip | 59 and 61 show a slow beat (about 1 Hz); 60 steady; 120 steady or a fixed pattern | No dependence on the exact rate | No dependence |
| 4 | **Load independence.** At 20 fps: all black with one line, then full white (at the 23 % cap) | Eye + clip | Relative flicker the same on both | Flicker grows with white (sag) | Same on both |
| 5 | **Rail voltage (E1).** DC volts at the card's power terminals and at the far panel's plug: black, then white; held, then 20 fps. Also the meter's AC mV range, and MIN/MAX if it has it | Multimeter | 4.8 to 5.2 V everywhere; held and streaming read the same | More than 0.2 V difference between points or between held and streaming; AC reading rises when streaming | As T |
| 6 | **Card on its own 5 V supply.** Separate small 5 V supply for the card; grounds stay joined through the ribbons; never join the two +5 V outputs | Eye | No change | Flicker goes or changes | No change |
| 7 | **Ethernet cable.** Short unshielded patch cable against a long or shielded one, at 20 fps and at 60 fps | Eye | No change | Changes with the cable | No change |
| 8 | **One chain, one panel.** Unplug J2; then also the second panel of J1 (ribbon and its power stay as they are, only the data ribbon) | Eye + clip | The remaining panel flickers the same | Flicker falls (less load, shorter chain) | Same |
| 9 | **Blanking (S1).** 3 -> 6 -> 11, Send (RAM only), at 20 fps and held | Eye, close up, dark room | Flicker unchanged; ghost rows may fade | Unchanged | Flicker or "fidget" changes with the value |
| 10 | **Frame period (S2).** In LEDVision try Multiple x8 and x1 with the refresh it then allows, Send (RAM only); then the 20 fps and 30 fps sender | Eye + clip | The flicker's rate and depth change with the Multiple; some setting may be clean at 30 fps | Unchanged | Flicker present even when held |
| 11 | **Oscilloscope, if there is one** (ask the owner; I do not assume it). Channel 1 on the 5 V rail at the far panel, AC coupled, 50 mV/div; channel 2 on OE at the panel's input. Compare held against 20 fps | Scope | Rail flat; OE shows gaps or restarts in step with the sender's frames | Rail shows dips or bursts in step with the flicker | OE pattern the same in both |
| 12 | **Generator rehearsal.** The whole wall on the event's generator, eco on then off, a dark-to-white step every few seconds | Eye + multimeter on the rail | Not about the bench flicker; pass if the rail holds and the wall does not dim on the step | | |

### 4.2 Reading the results

- Tests 1 to 4 need no hardware change and no LEDVision. If 2 is steady and 3 shows a beat at 59 and 61,
  the cause is data timing and the electrical tests 5 to 8 can be done once for the record rather than
  as a hunt.
- Test 2 is the cleanest split between "the link is busy" and "frames are arriving". It needs a sender
  change (another lane); packets with a foreign EtherType cannot alter the card's picture.
- If test 1's control clip already shows the artefact, the problem is in the scan settings or the camera,
  not in the stream: go to 9 and 10.
- Tests 9 and 10 change the card's RAM only. Do not save to flash until a combination is clean, and check
  the Brightness Level before each Send.
- A result that would change my verdict: flicker in test 2, or a rail difference above 0.2 V in test 5.

## 5. What I could not confirm

- The marking of any chip on our panels (blank or illegible in the photos). "DP5125D" rests on the sticker
  and a sibling panel; "ICN2018-compatible" rests on LEDVision's decoder setting working.
- The pin count and part number of T2/T3.
- A datasheet titled DP5125D (I used the DP5125E sheet, which names the D in its drawings).
- That LEDVision's Blanking Value sets the ICN2018 row-clock pulse width.
- How firmware 13.17 times its refresh cycle against the incoming sync packet (section 2.2 is inference).
- Which settings the phone video with the 5 Hz dips was taken at. The log's order suggests 360 Hz, x1,
  10.4 MHz (hardware.md lines 157 to 164), not 960 / x16; it does not say so.
- The 5 V supply's model, the voltage at the panels, the ribbon lengths, the Ethernet cable type.
- Any report of the H3.3 board revision.

## 6. Sources

Datasheets and specifications
- Chipone ICND2018 V1.6: https://downloads.olympianled.com/PDF/Driver%20ICs/ICND2018-datasheet-EN-2021-V1.6.pdf
- Chipone ICND3018 V1.1: https://downloads.olympianled.com/PDF/Driver%20ICs/ICND3018-datasheet-EN-2020-V1.1.pdf (linked from the product page; not opened)
- ICN2018 / ICN3018 product pages: https://olympianled.com/product/chipone-icn2018-icnd2018-row-driver/ , https://olympianled.com/product/chipone-icn3018-icnd3018-line-driver/
- Depuw DP5125E REV1.1: https://www.lipuxin.com/_120241227/1504598661.pdf (from http://www.depuw.com/cn/pro/193.html)
- Colorlight 5A-75E Specification V8.2.2: https://www.colorlitled.com/wp-content/download/colorlight/file/Colorlight%205A-75E%20Specification%20V8.2.2.pdf
- Mean Well LRS-350: https://www.meanwell.com/Upload/PDF/LRS-350/LRS-350-SPEC.PDF (named as an example; not opened)

Settings guides
- Wired Watts, Colorlight setup for outdoor P5: https://www.wiredwatts.com/colorlight-setup-for-outdoor-p5-panels
- Wired Watts outdoor P5 product page: https://wiredwatts.com/pnp5o
- Colorlit, receiver card performance settings: https://www.colorlitled.com/performance-settings-led-receiver-card/
- Linsn, configuration troubles: https://www.linsnled.com/troubles-of-led-display-configuration-how-to-locate-and-solve.html

Reports
- Falcon forum, "P5 panels flickering badly with colorlight card": https://falconchristmas.com/forum/index.php?topic=16375.0
- FPP issue 1849: https://github.com/FalconChristmas/fpp/issues/1849
- ESP32-HUB75-MatrixPanel-DMA issues 698 and 645: https://github.com/mrcodetastic/ESP32-HUB75-MatrixPanel-DMA/issues/698 , https://github.com/mrcodetastic/ESP32-HUB75-MatrixPanel-DMA/issues/645
- rpi-rgb-led-matrix forum: https://rpi-rgb-led-matrix.discourse.group/t/p5-1921-64x32-8s/1161 , https://rpi-rgb-led-matrix.discourse.group/t/support-for-dp5125b-chipset/1056
- DMD_STM32 chip table: https://github.com/board707/DMD_STM32/wiki/Led_drivers
- rpi-rgb-led-matrix README: https://raw.githubusercontent.com/hzeller/rpi-rgb-led-matrix/master/README.md

Electrical
- Ethernet shield grounding: https://industrialmonitordirect.com/blogs/knowledgebase/industrial-ethernet-shield-grounding-avoiding-ground-loops , https://e2e.ti.com/support/interface-group/interface/f/interface-forum/209010/ethernet-cable-shield-grounding
- Generator eco mode: https://www.truckcamperadventure.com/solving-the-dreaded-inverter-and-generator-eco-mode-conflict/ , https://www.powerequipmentforum.com/threads/question-s-about-eco-mode-on-a-champion-inverter-generator.28178/
- HUB75 power: https://github.com/rorosaurus/esp32-hub75-driver/blob/master/POWER.md

Our own record
- /Users/trey/dev/codeisart-ledvision/docs/superpowers/workflow/evidence/hardware.md
- /Users/trey/dev/codeisart-ledvision/docs/superpowers/workflow/evidence/hardware/14-panel-back.jpg
- /Users/trey/dev/codeisart-ledvision/docs/superpowers/workflow/evidence/hardware/27-panel-back-power-row-drivers.jpg
- /Users/trey/dev/codeisart-ledvision/docs/superpowers/workflow/evidence/hardware/34-card2-params-read-back.png
