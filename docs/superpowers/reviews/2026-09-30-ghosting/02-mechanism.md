# Lane 02: the mechanism, at the panel

Date: 2026-09-30. Read-only: nothing was sent to the wall or the card, no repo file was changed except this
report. Datasheets, crops and the numbers quoted below are in
`/private/tmp/claude-502/-Users-trey-dev-codeisart/489bd663-dd66-40f0-8952-22058687bf7d/scratchpad/02-mechanism/`.

Labels: CONFIRMED (a primary source, cited, or a measurement with its method), LIKELY, SPECULATIVE. SEEN means
I looked at an enlarged photograph and did not measure. "Not settled" means I looked and could not decide.

## 0. Verdict in short

1. **The copy is not a fixed number of rows from its source. It is a fixed time behind it.** CONFIRMED as
   two measurements of the owner's pictures (section 4.4), and by lane 01 on frames registered to the LED
   grid: at Refresh x16 the copy of rows 16-17 is on rows 20-21 (+4 rows; lane 01 finds +5 in about a third
   of the video frames); at Refresh x4 the same picture has two copies, on rows 17-18 and 21-22 (+1 and +5
   rows). Four row slots at x16 and one row slot at x4 are the same 0.52 ms (1/1920 s); five slots at x4 are
   2.6 ms, which at x16 is twenty slots, +4 rows again. INFERENCE from two multiples: the row lit about
   0.52 ms after the source row, and the row lit about 2.6 ms after it, show the source's data. It predicts
   a copy 2 (at times 3) rows away at Refresh x8, which nobody has looked for.
2. **So none of the textbook ghosts is this artefact.** LIKELY. Upper ghost, lower ghost, slow row switches
   and late OE all land one scan step from the source at every refresh rate, and each is a small fixed
   charge, of the order of 0.01 to 1 % of a full pixel (section 4.2). This copy moves with the refresh
   multiple and reaches some 2 to 15 % of the source at x16 and more at x4 (lane 01). That is also why
   blanking 3 to 11, Blanking Enhancement and Blanking Voltage did nothing: they act on the upper ghost only.
3. **Both geometric readings in the brief fail as hardware facts.** At x16 the picture does have the geometry
   of reading (b) most of the time: lines 0 to 3 copy 4 rows down and lines 4 to 7 copy 4 rows up, inside
   their own group of 8 rows (lane 01, CONFIRMED). But at x4 the offsets are +1 and +5, which no fixed
   pairing of rows k and k+4 and no fixed scan order gives. The premise of (b) also falls: T2 and T3 are not
   10-pin parts with four outputs (at least 7 leads a side in photo 14, CONFIRMED by a brightness profile),
   and "138 decoding lit rows in pairs four apart" is what any 8-stage serial row driver does when clocked
   by A with C as data (section 3.1). It is not evidence of a link between rows k and k+4.
4. **Where the cause sits** (my weights, judgement not calculation; section 5): the card's row signalling to
   the serial row drivers, a token too many in the chain, about 60 %; the card putting a row's data out
   again, about 10 %; a time-dependent behaviour of the DP5125 column drivers, about 5 %; every electrical
   cause at the panel together, under 10 % for this artefact; unknown, about 15 %. Lane 01's finding that
   the first 8 rows of each panel take no upward copy is what puts the row tokens ahead of the data: it is
   what a stray token does in row chips chained output to input, and nothing on the data side makes one
   group of rows differ from the next (section 4.5, INFERENCE).
5. **Two real electrical weaknesses exist beside it and may add small ghosts of their own.** The DP5125's
   column pre-charge is off under a generic single-latch program (CONFIRMED in its datasheet: "通用程序：
   单锁存（无消影）"), so a faint lower ghost one row below is to be expected. The saved Blanking Value of
   300 ns is under the 500 ns that every candidate row driver asks for (CONFIRMED in three datasheets), so a
   faint upper ghost one row above is possible; the "1-row copy just above" in the enlarged arm may be that.
   Neither is the second picture the owner sees.
6. **Cheapest observations that would move all this** (section 7): the card holding a frame with the sender
   stopped (a stray token left when a frame arrives predicts no copy); the sender's rate stepped from 57 to
   61 frames a second (it predicts the copy walks row by row); the same level lines at Refresh x8 (+2 or +3
   rows); one row at a time in each of the four row groups of a panel (the first group: copies downward
   only). Film them (video or a long exposure): a still with a short exposure catches a slice of the frame
   cycle, which is why the x4 lobby photograph looked clean (lane 01, CONFIRMED).

## 1. What I read, looked at and measured

- The brief; `hardware.md` on `ledvision-card1` (all, with the 2026-09-30 sections); route A's `00-bench.md`
  section 3; yesterday's `03-panel-electrical.md`; `ghost_test.py` and `lobby.png`.
- Both panel-back photographs at full resolution, with crops of T2, T3, the power pads and the sticker.
- The owner's pictures: `a4192b69` (level lines, x16), `9a8f1211` (lobby, x16), `50ed57ea-IMG_5091.mov`
  (level lines, x4), `c2636b4a` (lobby, x4), `fba75423` (level lines, x4, a still).
- Datasheets downloaded and read as text and as page images: Chipone ICND2018 V1.6; Depuw DP5125E REV1.1,
  DP32020A REV2.3 and REV3.1, DP32020C, DP32021 REV1.4, DP32019B REV2.1, DP32030B, DP3246B REV1.1; Macroblock
  MBI5153 Application Note V1.02 and MBI5124; TI TLC59283 (SBVS199C), LP5891 (SLDS269A), SBVA057; Sunmoon
  SM5166P. A Chipone article on row drivers ("行驱动的六大挑战", mirrored). URLs in section 9.
- `show/display/colorlight.py`: `--brightness` goes to the card as a level byte (`level_byte(brightness)`),
  the pixel bytes are not scaled. CONFIRMED in the code; lane 05 has the full audit.

How I measured the pictures: a column-averaged brightness profile down the image through one lit block, the
LED pitch taken from the peaks of the unlit LEDs (which show as grey dots), rows counted from the wall's top
edge (the first dot row is row 0), so the row numbers below are wall rows and not guesses from the source.
Ratios are in camera units above the unlit-dot level. They are not linear light and a saturated source makes
them too high; read them as "a tenth" or "a half", no finer.

## 2. The taxonomy: kinds of ghosting and coupling in scanned LED displays

Each scan step, one row switch (a P-MOSFET to the LED rail) is on and the column drivers sink current in the
lit columns. The row lines and the column lines have capacitance; the faults below are what that stored
charge, or a switch that is on at the wrong time, does.

### 2.1 Upper ghost (上鬼影; charge on the row line)

- Mechanism. CONFIRMED (Chipone article): "Row(n)打开时，行寄生电容Cr充电到VCC电位。切换到Row(n+1)时，
  Cr与OUT之间形成电位差，电荷通过灯珠进行泄放，产生LED隐亮" (row n's line stays charged to VCC; when row
  n+1 is lit and a column turns on, the charge leaves through row n's LED in that column). TI says the same of
  the common line: "the common lines are not discharged quickly due to parasitic capacitance and this causes
  the LED to briefly turn on" (SBVA057).
- Where it lands. CONFIRMED (Macroblock AN section 9): "The phenomenon of unexpected LED in last scan line
  slightly turns on called 'upper ghost problem'". The row lit BEFORE shows the data of the row lit now: the
  copy is one scan step above its source.
- Strength. A fixed charge per row change, Cr x dV, shared among the columns that turn on. So (INFERENCE from
  the mechanism): it does not grow with how long the source pixel is lit; per pixel it FALLS as more pixels in
  the source row are lit; per second it grows with the number of row changes (the refresh rate); it shrinks
  with a longer discharge time (blanking) and a lower discharge level.
- Colour. Red LEDs light from a lower voltage, so they take the charge first. CONFIRMED (Chipone): "经测试
  红色灯珠1.4V即能使之点亮", green and blue 2.4 to 3.4 V nominal, green lit from about 1.8 V.
- Cure. Discharge the row line at each row change. In the row driver: "下拉电位即消隐电压VH设置的越低...
  通常VH<VCC－1V即可消除上鬼影" (Chipone). With discrete parts: "a resistor cascaded with a zener diode. The
  resistance is about 390Ω~1kΩ, and the zener diode is about 3.0~3.3V" (Macroblock).

### 2.2 Lower ghost (下鬼影; charge on the column line)

- Mechanism. CONFIRMED (TI TLC59283 datasheet 7.3.3.1): "One cause of this phenomenon is the parasitic
  capacitance charging current of the constant-current outputs (OUTn) and PCB wiring connected to OUTn through
  the LED ... When SWPMOS1 turns on, the OUT0 voltage is pulled up from the ground voltage to VLED – VF. The
  charge current (ICHRG) flows to the parasitic capacitor (C0) through LED1-0, causing the LED to briefly turn
  on". TI adds that pulling the old row down drags the column down with it through the LED's own capacitance,
  so a row driver that discharges its rows makes the column side worse unless the columns are pre-charged.
- Where it lands. CONFIRMED (Macroblock): "unexpected LED in next scan line slightly turns on called 'lower
  ghost problem'". The row lit NEXT shows the data of the row lit before: one scan step below the source.
- Strength. A fixed charge per row change per column, Cc x dV. Independent of how many pixels are lit; does
  not grow with the source's on-time; needs only that the column was on near the end of the slot; grows with
  refresh rate; NOT reached by the row driver's blanking level.
- Colour. As 2.1: red leans ahead.
- Cure. Pre-charge in the column driver: "When a small delay after PWM control for a single common line
  completes, the FET pulls OUTn up to VCC" (TI); "MBI5124 integrates the pre-charge circuit which can relieve
  the ghosting" (Macroblock); in the MBI5153 "the duration between the falling edge of 513th GCLK and scan
  line switched determines the running time of lower ghost elimination". TI's caution: "depending on the LED
  anode voltage ... and the TLC59283 VCC supply voltage, there may not be a great enough ghost-canceling
  effect". A lower LED rail reduces the swing.

### 2.3 A row switch that turns off slowly; rows overlapping; late OE

- Mechanism. The old row's P-MOSFET is still conducting when the new one turns on, or the columns are still
  sinking when the row changes. Datasheet figures: ICND2018 output fall 180 ns and turn-off delay 220 ns at
  2 nF; DP32020A fall 400 ns. CONFIRMED (the datasheets).
- Where it lands: the adjacent scan step, above or below by which edge overlaps. Strength is the overlap
  over the slot, in proportion to the source. Cure: a blanking time longer than the switch; that is why the
  serial row drivers make the row clock's high time the blanking time, 500 ns minimum.

### 2.4 Caterpillar from a shorted LED, cross from an open LED (毛毛虫, 十字架)

- CONFIRMED (Chipone, TI LP5891 7.3.5). A shorted LED ties its column to its row: "会出现一列长亮现象 ...
  只要屏幕处于扫描状态，不管LED灯珠是否显示图像，都会显现" (a column lit whenever the panel scans, whatever
  the picture). An open LED lets its column fall to 0.5 V when addressed, and the other rows' LEDs in that
  column conduct from the discharge level: "causing all LEDs which connect to the channel OUT1, light
  unwanted" (TI).
- Where: at the defect's column or row only. It does not follow the picture. Cure: the discharge level
  (higher against shorts, VH > VCC - 1.4 V; lower against opens), or detection in the driver.

### 2.5 Discharge level too high for the LED (VF 偏大列亮)

- CONFIRMED (Chipone): with a column on at VOUT = VLED - VF, the other rows of that column sit at the
  discharge level VH and see VH - VLED + VF; above about 1.8 V they light: "VH>VCC－1.6V便不利于解决灯珠VF值
  偏大引起的列常亮问题".
- Where: every other row of the block, in the lit column, for as long as the column is on (so in proportion
  to the source). A smear down the column, not one copy.

### 2.6 High-contrast coupling (高对比耦合, image coupling)

- CONFIRMED. Macroblock section 10: "Due to the loading effect, the image with low gray scale will be affected
  by the high gray scale image". Chipone: "低亮画面与高亮画面同行的区域出现偏色、偏暗现象 ... 为列通道通过
  行管相互干扰造成".
- Where: a dim area in the same rows as a bright one turns darker or off-colour. A tint, not a copy.
  Cure: a stiffer or lower discharge level (Macroblock: zener, N-MOSFET and 0.1 uF), at the price of 2.4.

### 2.7 First line dark (第一扫偏暗)

- Named by Chipone ("第一扫偏暗") and TI ("dim at the first scan line", LP5891, which has a `FIRST_LINE_DIM`
  setting). The first line scanned after the pause between frames is dimmer at low grey, because the column
  lines have drifted during the pause and the first short pulses go into charging them. I found no primary
  text that sets the mechanism out further; LIKELY as stated.
- Where: scan line 0. A dim row, not a copy.

### 2.8 Summary

| Kind | The copy lands on | Follows source on-time | More lit pixels in the row | Higher refresh | Longer blanking | Cure |
|---|---|---|---|---|---|---|
| Upper ghost | row lit before (1 step up) | no | weaker per pixel | stronger | weaker | row discharge, time and level |
| Lower ghost | row lit next (1 step down) | no | same | stronger | same | column pre-charge, lower rail |
| Slow switch, late OE | adjacent step | yes | same | stronger | weaker | blanking time |
| Short / open LED | the defect's column or row | no | | | | discharge level, detection |
| Level too high | all other rows of the column | yes | same | same | same | lower level |
| Coupling | same rows, dim areas | | stronger | | | stiffer discharge |
| First line dark | scan line 0, dimmer | | | | | compensation |
| What the wall shows | 0.52 ms and 2.6 ms later: +4 (at times +5) rows at x16, +1 and +5 at x4 | not settled (4.4) | not tested | offset moves, share grows as it falls | no change seen | not known |

No row of the table above the last one moves its copy when the refresh multiple changes.

## 3. This panel

### 3.1 The row drivers T2 and T3

**What the photographs show.** Photo 27 shows five leads a side because the frame's rib covers the rest of
each package. Photo 14, taken from another angle, shows T2's lower side clear of the rib: a brightness
profile along the leads has seven peaks at an even 8.3 px pitch (35, 66, 112, 169, 183, 194, 174 in camera
units, the first in shadow), and the enlarged crop shows seven leads with room for an eighth in the shadow.
CONFIRMED: at least 7 leads a side. LIKELY: SOP16, 1.27 mm pitch (in photo 27 the lead pitch is twice that of
the 0.635 mm QSOP24 column driver beside it). The "10-pin" in the log is a miscount from photo 27. The tops
are blank at this resolution; the marking is not read. Whether there are T1 and T4 elsewhere on the board is
not settled (photo 14 may show one more).

**Which parts fit.** I found no 8-pin or 10-pin serial row driver with four outputs from Chipone, Depuw or
Sunmoon; not settled for other makers, and no longer needed. The SOP16 serial row drivers with 8 P-MOSFET
outputs that I could read:

| Part | Maker | Protocol | Notes (all CONFIRMED from the datasheet) |
|---|---|---|---|
| ICND2018 | Chipone | 1 row clock per line, token on SDIN, 8 stages | 2.5 A, 100 mΩ, 3.0 to 5.5 V; level set by COUNTING RCLK pulses |
| DP32020A, DP32020C | Depuw | the same line protocol | "防止 3 个及以上通道同时开启": refuses three or more outputs on at once; level set by 8 RCK clocks carrying 4 bits |
| DP32021 | Depuw | the same | no such guard in its sheet; 4 A, 73 mΩ; works from 2.8 V; default level 2.75 V |
| DP32019B | Depuw | 138-style binary address | SOP16; not serial |
| SM5166P | Sunmoon | 138-style | SOP16; not serial |

The pinouts agree (VDD 1, DIN 2, DCK 3, RCK 4, OUT4-7 on 5-8, GND 9, DOUT 10, OUT3-0 on 13-16), so these
parts are drop-in for one another on a board. Depuw's sheets give the HUB75 mapping: "DIN 对应 3-8 译码的 C
信号, DCK 对应 3-8 译码的 A 信号, RCK 对应 3-8 译码的 B 信号". The DP5125E's own application drawing names
"DP7268, DP32020, DP32019" as the line drive unit, so a Depuw row driver beside Depuw column drivers is the
natural guess; LEDVision's "DP32020 Decoding" lit nothing on this panel, which speaks against it. Not
settled. The marking would settle it (check E1).

**What "138 decoding lit rows in pairs four apart" means.** With 138 signalling the card counts a binary
address on A, B, C. A serial driver takes A as its row clock and C as its data. A rises at addresses 1, 3, 5
and 7; C is 0, 0, 1, 1 at those edges. The 8-stage register therefore fills with 1,1,0,0,1,1,0,0: stages 0,
1, 4 and 5 on during address 0. That is rows 1-2 and 5-6, and with the partner rows 9-10 and 13-14: exactly
what the owner read at Guide 7 (hardware.md line 128). INFERENCE, and it reproduces the observation to the
row. Three things follow:

- It is ordinary behaviour for a serial row driver. It says nothing about a link between rows k and k+4.
- The log's reading "the panels follow address line B" (hardware.md line 131, taken up by lane 04) is not
  needed: the set of rows with B = 0 and the set 1,1,0,0,1,1,0,0 are the same set.
- Four outputs were on at once, so the chips have no guard against three or more. LIKELY not DP32020A or C;
  ICND2018 and DP32021 both fit.

**The ghost-elimination section of these chips, and what the controller must send.** CONFIRMED (datasheets):

- The blanking time is the row clock's high time. ICND2018: "The width of DCLK is the elimination time, so we
  need to do DCLK width and interface elimination parameter linkage", "Ghost reduction time, DCLK pulse width"
  500 ns minimum. DP32020A and DP32021: "消影时间等于 DCK 高电平宽度", 500 ns minimum. The saved Blanking
  Value is 3 (300 ns) if LEDVision's value is that width, which is LIKELY and not confirmed.
- The discharge level. ICND2018: the number of RCLK rising edges while DCLK is low, 8 to 23, gives
  `Reg[3:0] = RCLK - 8`: three bits of level, 2.0 to 3.75 V in 0.25 V steps, and a fourth bit "Model", whose
  meaning the sheet does not give. Default 1101: Model 1, 3.25 V. LEDVision's page has the same 2.0 to 3.75 V
  list and a "Blanking Enhancement" tick, LIKELY that fourth bit.
- Depuw's chips are configured differently: "当 DCK 为低的时候，对 RCK 发送的 8 个 clock (4 个 dummy clocks
  +4 个寄存器配置 clocks)", the four bits being clocked in as data, with levels as fractions of VDD (1.75 to
  3.5 V at 5 V).

**If the card speaks ICN2018's protocol to a Depuw chip.** INFERENCE from the two sheets, not tested: the
line protocol is the same, so the picture is right. The level is not set: a burst of 13 or 21 plain pulses
reads as the bits 0000 (1.75 V at 5 V, the lowest), and LEDVision's Blanking Voltage would do nothing. That
would square with "3.25 V to 2.0 V: still the same", but so does the plain fact that the artefact is not an
upper ghost. A level of 1.75 V is lower than Chipone's article advises for LED life (not under VCC - 2 V).
Worth knowing once the marking is read; it does not explain the copy.

### 3.2 The sticker `YP5-5125HG505-Y2076`

Not settled. "P5" and "5125" (the DP5125 family) are plain. I found no part, lamp or maker that "HG505"
names, in English or Chinese sources; no row driver is called that. SPECULATIVE: a lamp or lot code.

### 3.3 The column drivers: DP5125

CONFIRMED (DP5125E REV1.1; the family's only public sheet, its drawings labelled for the family):

- Overview: "芯片上电智能识别工作模式，向下兼容并扩展市场现有的普通单锁存恒流芯片和双锁存恒流列下消影
  芯片" (at power-up the chip recognises its working mode; it is compatible with plain single-latch chips and
  with double-latch chips that have column lower-ghost removal).
- Features: "控制系统自适应技术：通用程序：单锁存无消影，不会造成灯珠反压" (generic program: single
  latch, no ghost removal). The block diagram has a box "通用程序：单锁存（无消影）" beside a "协议解析
  （单双锁自适应）" parser and two 16-bit latches.
- Depuw's row-driver sheets say what the pair is meant to do: "搭配内建有预先充电功能的恒流驱动芯片 DP5125，
  如此即可能够完整地消除此上、下拖影现象" (with the DP5125's built-in pre-charge, upper and lower ghosting
  are both removed).
- Black-screen energy saving: supply current 0.2 mA against 4.91 mA "黑屏" (when its data are black). The
  sheet gives no entry or wake-up time.

So the chip has a pre-charge, and it is switched by the protocol the controller speaks, not by a pin. The E
sheet does not print the double-latch protocol. A sibling does (DP3246B, "高级双锁存"): commands are the
number of CLK edges while LE is high (3 latches data, 11 and 12 write two registers), and register 2 has
`DISSHD_EN`, "0：不启用消影功能" by default, with a level `VS_DISSHD`. INFERENCE: the DP5125's pre-charge
comes on when the card uses a double-latch driver type, LIKELY with a register write; which entry in
LEDVision's "Select Driver IC" list does that for this chip is not settled. "Normal Chip" is the generic
single-latch program: the pre-charge is off. LIKELY (CONFIRMED that the generic program has none; LIKELY that
"Normal Chip" is that program, the panel being lit correctly by it).

What that means here: the wall has no defence against the lower ghost (2.2), so a faint one, one row below
any bright pixel, is to be expected. It is not the second picture (it cannot sit 4 rows away at x16).

### 3.4 The power pads

CONFIRMED from the photos: the plug is on the pads marked "2.8V"; the "VCC" pads are empty; L1 and L2 beside
them are fitted. LIKELY: one 5 V rail feeds both nets. DP32021 and DP32030B are specified from 2.8 V and
2.6 V, which shows this board family is also built for low LED rails. The supply voltage at the panel has
never been measured.

## 4. The scan

### 4.1 Timing under the saved settings (my arithmetic)

- 960 Hz x 8 scan lines: a row slot is 130.2 us. Refresh x16 of a 60 Hz frame: 16 passes a frame, each
  1.042 ms. At x8 (480 Hz) a slot is 260.4 us; at x4 (240 Hz), 520.8 us, which is 1/1920 s.
- Shifting one 128-bit line at 15.6 MHz takes 8.2 us. The row change costs the blanking, 0.3 us.
- The light: LEDVision showed Brightness Percent 23 %, 25 %, 26 % with Minimum OE 115.2, 129.0, 133.6 ns at
  x16, x8, x4 (hardware.md lines 333 to 335). 8191 x (Minimum OE / 2) over a line's share of a frame (2083 us)
  gives 22.6 %, 25.4 %, 26.3 %. INFERENCE: the grey unit is half the Minimum OE (about 58 ns), the last bit
  being made in time; a full-white pixel is on for about 472 us a frame, 29.5 us per slot at x16 and 118 us
  at x4.
- "Gray-level First" with 8192 levels: how the card spreads the 13 bit planes over the 16 passes is not
  documented. If the high planes are split evenly, a slot at x16 holds the top plane for about 15 us and the
  next for 7 us; at x4 those are 60 and 30 us and the third plane is 15 us. Illustration only.
- With gamma 2.8 the card turns pixel 64 into 171 units of 8191, 128 into 1187, 199 into 4091, 255 into 8191.
  The top bit plane is lit from pixel 200 up; 128 has its highest bit at plane 10.

### 4.2 How big the textbook ghosts can be here (estimate, capacitances assumed)

- A full pixel at x16: 15 mA for 29.5 us is about 440 nC per slot.
- Lower ghost: a column line of 50 to 300 pF stepping 0.5 to 1.5 V is 0.03 to 0.45 nC: 0.01 to 0.1 % of a
  full pixel.
- Upper ghost: a row line with 384 LED junctions, 4 to 20 nF, stepping 0.5 to 1.5 V: 2 to 30 nC, shared
  among the pixels lit in the next row. One pixel lit: up to a few per cent. Thirty-four lit: 0.01 to 0.2 %.
- So these show as a faint glow beside dim content and at low brightness levels, and cannot make a copy a
  twentieth or more as bright as a 34-pixel line. SPECULATIVE as numbers, LIKELY as orders of magnitude.

### 4.3 The two readings, and what hardware each would need

**Reading (a): the rows are lit in the order 0, 4, 1, 5, 2, 6, 3, 7 and the copy is on the row lit next.**
A serial row driver can only pass its token along the chain, and the guided setup saw the chain's order as
the plain order of rows (rows 2/10, 3/11 ... 8/16, step by step). CONFIRMED (hardware.md line 176). For the
order (a) the card would have to clock the row driver four or five times between lit rows and re-enter
tokens at odd places; possible, but I found nothing that says a Colorlight card does it. With a 138 decoder
an order like that is free; with a serial driver it is not. And (a) predicts the same offsets at any
multiple: +4 for lines 0 to 3 and -3 for lines 4 to 7. The x4 video shows +1 and +5. Against.

**Reading (b): scan lines k and k+4 are partly on together.** What would do it in hardware: two row chips
with four outputs each whose tokens run in step (chained through DOUT, which delays by 8, or fed in
parallel); a second token entered 4 clocks after the first; two row traces bridged. Each of those holds rows
k and k+4 on together ALL the time, which gives two equal lines, the "138" picture, not a fainter copy; the
chips are 8-output parts; and under ICN2018 decoding the grid showed single clean lines. A partial form
(the two rows together for a fraction of the time) needs a cause in the signalling, and then the fixed
"+4" is no longer hardware. (b) also predicts the same offsets at any multiple. Against, as a hardware fact.

**What a one-row-at-a-time picture shows under each** (source on scan line s of 0..7; rows r and r+8 share a
line but have separate column outputs, so a copy made at the row switches stays inside its own block of 8):

| Cause | Copy of line s lands on | At x4 instead of x16 |
|---|---|---|
| Lower ghost, plain order | s+1 (line 7 to line 0) | the same rows, weaker |
| Upper ghost, plain order | s-1 (line 0 to line 7) | the same rows, weaker |
| Reading (a), next-lit | 0>4, 4>1, 1>5, 5>2, 2>6, 6>3, 3>7, 7>0 | the same rows |
| Reading (b) | s+4 for 0..3, s-4 for 4..7 | the same rows |
| Level too high (2.5) | all seven other lines, faint | the same |
| Short or open LED | fixed places, whatever is lit | the same |
| Shown about 0.52 ms and 2.6 ms later (4.4, 4.5) | (s+4) mod 8, at times (s+5); first group downward only | (s+1) mod 8 and (s+5) mod 8 |

A copy that crossed from row 6 to row 10 (into the other column group) would mean the data, not the rows.

### 4.4 What the owner's pictures say

**x16, level lines from the Pi (`a4192b69`).** LED pitch 7.7 px, row 0 at y 55. Orange 255: the source
peaks at y 179 and 186 (rows 16 and 17), the copy at 209 and 215 (rows 20 and 21): +4 rows, two rows
thick, nothing between. White 255: the same, +3.9 rows by the pitch. Copy over source, above the unlit
level: 0.46 (orange, red channel), 0.33 to 0.37 (white). Under the 128 lines the rows at +4 are at the
unlit level in my profile (lane 01 finds a copy there of about 1 % of the line). CONFIRMED (my measurement).

**x4, the same picture (`50ed57ea-IMG_5091.mov`, frame 10; frames 0, 30, 60, 90, 110 agree).** LED pitch
7.0 px, row 0 at y 740 of the frame, sixteen unlit rows counted down to the source. Orange 255, green
channel (nothing saturates there and the flare is nil): rows 16 and 17 at 189 and 188 (the source), row 18
at 178, rows 19 and 20 at 149 and 146 (the unlit level is 150), rows 21 and 22 at 178 and 182, row 23 at
150. The red channel has the same five rows lit, nearer saturation. White 255 has the same shape. So rows
16-17 appear on rows 17-18 and again on rows 21-22: copies at **+1 and +5**, each 0.7 to 0.8 of the source
in camera units. Under 128 the same two copies, 0.6 to 0.7. Under 64: row 18 at 0.5, rows 21-22 barely
there. CONFIRMED (my measurement; lane 01 has the same rows in all 111 frames). The last session's "34 to
35 px below (about 4 rows)" is 5 rows at this pitch.

**x16, the lobby (`9a8f1211`, and lane 01's registration of the video IMG_5083).** In the enlarged crop the
diagonal leg has dim fragments on both sides, the horizontal part of the right leg has a copy below it, and
the top of the vertical leg has dim dots above it. Lane 01 measured it on all 105 frames: every scan line
copies, to line k+4 in 58 frames and to line k+5 in 38, the whole wall changing together; the copy wraps
inside its own group of 8 rows and never leaves it. CONFIRMED (lane 01). The dashes I saw are the two
directions of the wrap, not missing lines, and the green figure (0, 199, 0) does copy (lane 01: 0.2 to 0.4
of the recorded green); I had read both wrongly by eye.

**x4, the lobby (`c2636b4a`, a still).** A few isolated two-pixel fragments up-left of the left leg, 8 rows
apart, and a dot above the right leg's corner. Lane 01 places them: line 7's +1 copy wrapping to line 0 of
its group, 7 rows up; every other line's +1 copy lies against its own stroke and only thickens it (the arms
are 5 to 6 rows thick in that still). CONFIRMED (lane 01). A still is a slice of a few milliseconds of the
frame cycle; that, and the +1 copy hiding against the strokes, is why this photograph looked clean.

**The law.** 4 slots x 130.2 us = 1 slot x 520.8 us = 0.52 ms. 5 slots x 520.8 us = 2.60 ms = 20 slots at
x16 = two passes and 4 slots: +4 again, on top of the first. INFERENCE: the row lit about 0.52 ms after the
source row, and the row lit about 2.60 ms after it, show the source's data. 0.52 ms is exactly the edge
between 4 and 5 slots at x16, which fits the copy being on +4 in most frames and on +5 in the rest: a delay
that wanders a few tens of microseconds either side of that edge. At x4 the same delay is the edge between
1 and 2 slots; lane 01 sees +1 in every frame there.

**How strong.** No ratio from these pictures is sound: lane 01 shows every lit LED at the sensor's ceiling.
Its comparison inside one picture puts the copy of a 255 line at x16 between about 2 % and 15 % of its
source, the copy of a 128 line at about 1 %, and at x4 roughly 10 to 15 % or more. LIKELY. My camera ratios
above are upper bounds. One stray visit in 16 passes is 6 %, two are 12 %; one in 4 is 25 %.

**Is it in proportion to the source?** Not settled. At x16 the copy from 128 is weaker against its line
than the copy from 255 (lane 01: "grows somewhat faster than the light"), and at x4 the two copies of the 64
line differ from each other. SPECULATIVE: the passes that are copied carry some bit planes and not others.
My first draft inferred a step between pixel 199 and 200 from the green figure showing no copy; lane 01
finds the green copy, so that inference is withdrawn. A fine value ladder would settle it.

**Two ways to make it.** (i) The later row is switched on early: a second token runs in the row driver
ahead of the right one (by 4 or 5 stages at x16, by 1 and by 5 at x4). (ii) The columns put the earlier
row's data out again during the later row's slot. A serial row driver holds no address: whatever the card
clocks into it stays until it has been clocked out, so a card whose sequencer was written for 138 panels can
leave a token behind without any sign of it on a 138 panel. LIKELY that the origin is the card's signalling
and not the panel's electricity: nothing on the panel has a clock that could count 0.52 ms.

### 4.5 The first 8 rows of each panel, and what they say about the row chips

Lane 01's fact (CONFIRMED there): at x16 the second, third and fourth groups of 8 rows in a panel all take
copies, down and up; the first group (wall rows 0-7 and 32-39) takes no upward copy (rows 5-7 and 37-39 put
nothing on rows 1-3 and 33-35). Whether rows 0-3 copy down onto 4-7 could not be read.

INFERENCE: this is what a stray token does if the panel has four row chips, one per group of 8 rows, chained
output to input (DOUT of one to DIN of the next), the first taking its token from the HUB75 input. In steady
scanning each chip holds one token at the same stage, so the chain and a parallel feed look alike. Put one
token too many into the first chip, p stages ahead of the right one:

- in the first chip it lights row n+p while line n's data is out, for n up to 7-p: copies DOWNWARD only.
  When it reaches the end it leaves the chip; nothing brings it back to the first chip's low rows.
- it enters the second chip p slots early and lights rows n+p-8 there during lines 8-p to 7: the UPWARD
  wrap, in the second group. A pass later it makes the downward copies there, then moves to the third chip,
  and so on down the chain.

So every group but the first gets copies both ways, and the first gets them downward only: lane 01's
pattern. Option (ii), data put out again, treats every group alike and cannot make the first one differ.
This is the one observation that separates (i) from (ii) without an instrument, and it says (i). LIKELY. It
also says the chips are chained, that there are four of them (T1 to T4), and it predicts that rows 0-3 of a
panel DO copy down onto rows 4-7, which lane 05's one-row picture will show.

Where the stray token comes from is not settled. The simplest source (SPECULATIVE): the card starts its scan
afresh when a frame arrives and enters a new token while the old one is still in the chain. Then the offset
is the time the old pass had run, in slots: about 0.52 ms here. After such a restart the chips further down
the chain have only old tokens until the new one reaches them, so their rows are lit out of step for a pass
or more (light moved, not doubled). This is the same family as yesterday's flicker: the card disturbing its
scan when a frame arrives. It predicts no copy while the card holds a frame with the sender stopped, and an
offset that follows the sender's frame period (one row per 0.13 ms at x16, which is about half a frame a
second near 59). The second copy at x4 (+5, 2.08 ms behind the first) is not explained by one restart.
Lane 01's moment "without the copy" in each second of video fits an event that fills only part of the
frame cycle.

**Predictions, none yet tested.** Refresh x8 (slot 260.4 us): both delays fall on +2 rows, at times +3.
Refresh 1920 (slot 65 us): the first delay is 8 slots, a whole pass, so the copy falls on its own source or
one row below it; I no longer expect a clean "none". One row at a time: the last line of the table in 4.3,
with the first group of each panel copying downward only.

## 5. The candidate causes, ranked

The observations to meet: (O1) blanking 3 to 11, Blanking Enhancement and Blanking Voltage changed nothing
by eye; (O2) the multiple changed the look in two directions; (O3) the copy is seen only from high values;
(O4) it shows under LEDVision's own grid; (O5) the offsets in 4.4 and 4.5; (O6) the copy is some 2 to 15 % of
the source at x16 and more at x4; (O7) the same from the Pi, the Omarchy box and LEDVision.

| Cause | Fits | Speaks against | Weight | What would move it |
|---|---|---|---|---|
| A1. The card's row signalling: a token too many in the chained serial row drivers (LIKELY left when the card restarts its scan on a frame's arrival) | O1 (not a blanking matter); O2 (+4 becomes +1 and +5); O4, O7 (any sender); O5, with lane 01's wrap inside the group and the first group taking no upward copy (4.5); O6; a moment of the frame cycle without the copy | No direct sight of the signals. The second copy at x4 is not explained. The x16 rhythm (k+4, k+4, k+5) is not explained. The chain of four chips is inferred, not seen | 60 % | Up: no copy while the card holds a frame; the copy walks with the sender's rate; rows 0-3 of a panel copy down and rows 4-7 do not copy up. Down: the copy unchanged on hold and at any rate |
| A2. The card putting a row's data out again, a fixed time later | O1, O2, O4, O5, O6, O7 | Treats every group of rows alike: does not give the first group's exception | 10 % | Up: the first group found to copy like the others |
| B. The DP5125's black-screen energy saving or mode parser doing something a fixed time after lit data | Offsets that follow time; seen against black | The chip has two latches and cannot hold data across the many latches of 0.52 ms; two delays; the first group's exception; no primary text on its timing | 5 % | Up: the copy goes when the lines stand on a dim field. Down: it stays |
| C. Lower ghost, the columns not pre-charged (3.3) | Real on this wall; untouched by O1; red leans | Lands at +1 at every multiple; too weak for O6; O5 | 3 % as this artefact; LIKELY present beside it | A faint row directly under a single lit row at x16, stronger at low brightness |
| D. Upper ghost, blanking under 500 ns or the level not reaching the chip (3.1) | The "1-row copy just above" the arm | O1; lands at -1 at every multiple; O5, O6 | 2 % as this artefact; possible beside it | A faint row directly above a single row, which fades with Blanking Value 6 or 11 |
| E. Rows k and k+4 tied in hardware (reading b), or a scan order with a +4 step (reading a) | The x16 geometry | The x4 offsets; 8-output chips; the single clean lines under ICN2018 decoding; "138 pairs" explained otherwise | 3 % | The one-row map at x4 showing +4 after all |
| F. Discharge level too high, short or open LEDs, coupling (2.4 to 2.6) | Red leans | A copy, not a smear or a fixed mark; all four panels alike | 1 % | One panel differing from the others |
| G. Supply at the panel (low rail, sag) | Never measured | Would not move the copy with the multiple; all panels alike | 1 % | A rail under 4.5 V at the pads |
| Unknown | | | 15 % | |

On the observations that speak against my favourite: nobody has seen the card's row signals, so "a token
too many" is an explanation that fits, not a finding. The chain of row chips rests on one pattern in one
video (the first group's missing upward copies); if lane 05's one-row picture shows the first group copying
upward after all, A1 loses its best support and A2 rises. (O3), "only from high values", is met by any of
these once the card's gamma is counted, and does not choose between them. If the one-row map at x4 came
back with +4, the time law would be wrong and E would come back.

## 6. Electrical checks at the panel, in order of value

None of these is expected to find the cause of the copy if sections 4.4 and 4.5 hold. They close questions that
have been open since the first day, and E1 decides what the card should be told.

- **E1. Read the marking on T2 and T3, and find T1 and T4.** A loupe or a phone's macro lens, light from the
  side. Count the leads (expect 8 a side). If a meter is at hand, power off: continuity from pin 10 (DOUT)
  of one row chip to pin 2 (DIN) of the next settles the chain of section 4.5. A Chipone mark means the
  card's ICN2018 setting and its Blanking
  Voltage reach the chip; a Depuw mark (DP32021, DP32020) means the level setting LIKELY does not (3.1) and
  the DP32020 decoder entry deserves a second look.
- **E2. Panel by panel.** With one lit row (lane 05's picture 1), is the copy the same on all four panels
  and in both halves of each? The same everywhere: it is made upstream, as 4.4 says. One panel differing: that
  panel's row driver or LEDs, and causes E and F rise.
- **E3. One panel alone.** J2 unplugged and the second panel's ribbon off, a single panel on J1 by the short
  ribbon. Card-made: no change.
- **E4. The supply at the panel.** DC volts across the "2.8V" and GND pads of the far panel, wall black and
  wall lit; the same at the card. Expect 4.8 to 5.2 V and under 0.2 V between the two states. With the
  power off, continuity between a "VCC" pad and a "2.8V" pad tells whether the board has one rail (3.4).
- **E5. Swap a ribbon; move the short one.** A change with the ribbon would mean the row clock or data line
  (A, C) is being misread on the cable. Card-made: no change.
- **E6. If there is a logic analyser or a scope** (I do not assume one): A, B, C, OE and LAT at the first
  panel's input. Count the clock edges on A at which C is high in one frame: 16 at x16 if the card is right;
  more, and where, would show cause A (i) directly. This is the one check that separates (i) from (ii).

## 7. The discriminating tests

All from the sender or by LEDVision "Send" (the card's RAM only; a power cycle restores the flash). Nothing
here is a fix and nothing is to be saved to the card. **Every change of Multiple, refresh, DCLK or Blanking
Value in LEDVision sets Brightness Level back to 8: set it to 3 before every Send.** One variable at a time.
Film every picture (video, or an exposure of 1/30 s or longer), with lane 05's row ruler in the frame.
Lane 05's `ghost_map.py` has the pictures; its numbers are given where they fit.

| Pair of causes | The cheapest observation | One says | The other says |
|---|---|---|---|
| A fixed time (A, B) against a fixed row relation (E) | Level lines or one row at **Refresh x8** | one copy at +2 rows | +4 rows, as at x16 |
| The same | One row at a time, at x16 and at x4 (picture 1) | x16: (s+4) mod 8 for all s; x4: s+1 and s+5 | the same rows at both |
| A stray token left at a frame's arrival (A1) against the card's own scan | The card **holding** the frame, sender stopped | no copy | the copy stays: it is in the card's scan with or without a sender |
| The same | The sender stepped from 57 to 61 frames a second in steps of a quarter | the copy walks a row at a time, about one row per half frame a second at x16 | no change |
| Row tokens (A1) against data put out again (A2) | One row at a time through the FIRST 8 rows of a panel (picture 1a, 1c) | rows 0-3 copy down; rows 4-7 put nothing on rows 0-3 | the first group copies both ways like the others |
| The same | **Refresh 1920**, if LEDVision accepts it at this width | the copy on its own source or one row below | not distinguishing; record it |
| Card (A1, A2) against column driver (B) | The level lines on a **dim field** (pixel 24 to 32 everywhere) instead of black; and picture 6 | copy unchanged | copy gone or plainly weaker. Caution: most bit planes of a dim field are still zero, so "unchanged" is weak evidence |
| Bit planes against a fixed share | A value ladder on one row in steps of 8 from 128 to 255 (picture 3 is coarser) | steps where a high bit plane comes in (160, 200) | smooth growth |
| Rows switched early (A1) against data shown again (A2), directly | E6 | extra tokens on C | tokens right; OE low with old data |
| Lower ghost beside it (C) | One lit row at x16, brightness 0.1 against 0.4, close up | a faint row at +1, weaker at 0.4 relative to the source | nothing at +1 |
| Upper ghost beside it (D) | The same row, Blanking Value 3 against 11 | a faint row at -1 that fades at 11 | nothing at -1, or no change |
| Parasitic against made-by-sequencing, in general | Picture 2: the row lit over 1, 4, 16, 64, 128 pixels | upper ghost: weaker per pixel as the row fills; lower: unchanged but faint | unchanged and strong |

Two trials that belong to other lanes but follow from section 3: a double-latch driver type in LEDVision's
"Select Driver IC" list would switch on the DP5125's pre-charge (it would cure cause C, not the copy; a
wrong type garbles the picture until the saved settings are sent again); and the decoder entries not yet
tried (ICND2019, TC7261, GM5018, TA6018 and the rest of the list in screenshot 26) once E1 has named the
chip.

## 8. What I could not settle

- The marking, the maker and the exact pin count of T2 and T3; whether T1 and T4 exist.
- What "HG505" and "Y2076" on the sticker stand for.
- Whether LEDVision's Blanking Value is the row clock's high time in ICN2018 mode.
- What the ICND2018's "Model" bit does.
- The DP5125's double-latch protocol and register map (the E sheet prints neither), and the timing of its
  black-screen mode.
- How the card orders its bit planes, and what it does to its scan when a frame arrives.
- Whether the copy is doubled light or moved light (whether the source row is dimmer for it).
- Why the x16 copy switches between +4 and +5 on a three-frame rhythm (lane 01), and where the second copy
  at x4 comes from.
- Whether the row chips are chained output to input, and whether there are four (section 4.5 infers both).
- Whether the first group of each panel copies downward.
- The offsets under LEDVision's own stream; the owner saw the copy there but no picture was measured.
- A first-hand text for "first line dark".
- The supply voltage at the panels.

## 9. Sources

Datasheets and application notes

- Chipone ICND2018 V1.6 (May 2021): https://downloads.olympianled.com/PDF/Driver%20ICs/ICND2018-datasheet-EN-2021-V1.6.pdf
- Depuw DP5125E REV1.1: https://www.lipuxin.com/_120241227/1504598661.pdf (from http://www.depuw.com/cn/pro/193.html)
- Depuw DP32020A REV3.1: https://www.lipuxin.com/_120250318/1616173923.pdf ; REV2.3: https://cognigraph.com/6502/datasheet-DP32020A-chinese.pdf
- Depuw DP32020C REV1.0: https://www.lipuxin.com/_120241227/1525055356.pdf
- Depuw DP32021 REV1.4: https://www.lipuxin.com/_120250605/1706444719.pdf
- Depuw DP32019B REV2.1: https://www.lipuxin.com/_120241227/1524067223.pdf
- Depuw DP32030B REV2.0: https://www.lipuxin.com/_120250327/0936299940.pdf
- Depuw DP3246B REV1.1: https://www.lipuxin.com/_120241227/1505147262.pdf
- Depuw's row-driver list: http://www.depuw.com/cn/pro/230.html
- Macroblock MBI5153 Application Note V1.02: https://led.limehouselabs.org/datasheets/MBI5153%20Application%20Note%20V1.02-EN.pdf
- Macroblock MBI5124 preliminary datasheet V1.01: https://www.mblock.com.tw/upload/Datasheet/LED%20Driver%20IC/MBI5124/MBI5124%20Preliminary%20Datasheet_V1.01_EN.pdf
- TI TLC59283 (SBVS199C), section 7.3.3.1: https://www.ti.com/lit/ds/symlink/tlc59283.pdf
- TI SBVA057, "Use TLC59283 for LED Indication ...": https://www.ti.com/lit/pdf/sbva057
- TI LP5891 (SLDS269A): https://www.ti.com/lit/ds/symlink/lp5891.pdf
- Sunmoon SM5166P: https://www.waveshare.com/w/upload/8/8b/Sm5166p.pdf

Articles

- "一文读懂LED显示屏行驱动的六大挑战" (Chipone's article on row drivers, mirrored):
  http://m.szledscreen.com/h-nd-160.html ; also https://zhuanlan.zhihu.com/p/658491428 (not opened)
- DOIT VISION, an English rendering of the same material: https://www.doitvision.com/led-display-ghosting-dead-pixel-crosses/
- Colorlit, receiver card performance settings: https://www.colorlitled.com/performance-settings-led-receiver-card/
- ESP32-HUB75-MatrixPanel-DMA issue 645 (DP5125D with DP32020A, a serial row driver on A, B, C):
  https://github.com/mrcodetastic/ESP32-HUB75-MatrixPanel-DMA/issues/645

Our own record

- `/Users/trey/dev/codeisart-ledvision/docs/superpowers/workflow/evidence/hardware.md`
- `/Users/trey/dev/codeisart-ledvision/docs/superpowers/workflow/evidence/hardware/14-panel-back.jpg`,
  `27-panel-back-power-row-drivers.jpg`, `26-guide2-decoding-chip-list.png`
- `/Users/trey/dev/codeisart/docs/superpowers/reviews/2026-09-29-route-a/00-bench.md`, section 3
- `/Users/trey/dev/codeisart/docs/superpowers/reviews/2026-09-29-flicker/03-panel-electrical.md`
- The owner's pictures in the session's `scratchpad/evidence/`: `a4192b69-image.jpg`, `9a8f1211-image.jpg`,
  `50ed57ea-IMG_5091.mov`, `c2636b4a-image.jpg`, `fba75423-image.jpg`
