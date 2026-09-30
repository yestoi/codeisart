# Lane 03: the receiver card and LEDVision

Date: 2026-09-30. Read-only: nothing was sent to the wall or the card, the VM was not started, no repo file was
changed except this report. The `.rcvbp` files were read and decompressed into the scratchpad
(`scratchpad/lane03/`: `dec.py`, `cmp.py`, `sim138.py`, the `.bin` files); the originals are untouched.
Datasheets and manuals fetched for this lane are in `scratchpad/ledres/` and `scratchpad/ds/`.

Labels: CONFIRMED (a primary source quoted with its URL, a screenshot, or bytes I read), LIKELY,
SPECULATIVE. "Not settled" means I looked and could not decide it. Three web-research helpers did much of the
searching; every quote below that I did not re-read myself is marked "(helper)".

## 0. Verdict in short

1. **No LEDVision setting is documented to cure a copy 4 rows away.** Every ghost control Colorlight, NovaStar,
   Linsn and the chip makers describe acts on the row lit just before or just after the source (the "upper"
   and "lower" ghost). On this wall the rows are lit in plain order 1 to 8 (section 3.3), so those controls
   reach a copy one row away, not four. CONFIRMED for the documents; what the copy is, is lane 02's.
2. **The four trials of this morning all turned the same kind of knob**: the row chip's discharge (its time,
   its voltage, its mode). Colorlight's manual says what that knob is for: "eliminate upper ghosting". A copy
   below the source is not an upper ghost. So "nothing changed" is what the documents predict, and it does not
   show that Send failed. CONFIRMED for the documents; LIKELY as the explanation.
3. **The Blanking Value is what the dialog says it is.** In the config files 3 is stored as 38 and 11 as 138:
   a time in the card's 8 ns ticks (300 ns, 1100 ns). CONFIRMED from bytes (three values, five files). Which
   signal the card stretches with it under ICN2018/3018 decoding is not settled from documents.
4. **Brightness Level only scales the light pulses.** Minimum OE is 38.39 ns times the Level at the saved
   timings (Level 1: 38.4, Level 3: 115.2), and Brightness Percent is 4096 x Minimum OE x 8 lines x 60 Hz at
   every setting on record. CONFIRMED from bytes and six dialog read-outs. It makes Brightness Level the
   cleanest single variable there is: it changes the light and nothing else about the scan.
5. **"Normal Chip" leaves the DP5125's own ghost circuit off** (lane 04's finding, which I checked on the
   datasheet's first page). LEDVision's driver-chip list is reached only through the wizard; I could not
   find the list in any document, so which entry sends the double-latch protocol is **not settled**. The
   first step is a screenshot of that list. That circuit is for the lower ghost, one row below; it is not
   known to touch a copy 4 rows away.
6. **hardware.md's reading that "the panels follow address line B" is not needed.** A plain 8-bit serial
   chain clocked by A with its data on C, fed 138-style addresses, lights exactly lines 0, 1, 4, 5 for
   address 0: rows 1-2, 5-6, 9-10, 13-14, what the owner saw (simulated, section 2.9). So the 138 picture
   says nothing about B, and it confirms the chain runs in physical row order. CONFIRMED as arithmetic.
7. **The trials worth the owner's time, in order** (section 6): the held frame; the map at x8 and at refresh
   1920; the draft file; Brightness Level 1, 3, 5; Multiple x1; a Blanking Value in microseconds, not
   hundreds of nanoseconds; the Blanking Phase page; grey level; then, through the wizard, the driver-chip
   entry and the untried serial decoders (5953/5958 first). All RAM-only. They are diagnostic more than
   curative: each splits the candidate causes.
8. **Lane 02's interim lead (a copy a fixed 1/1920 s after its source) is weighed in section 5.4.** No
   document describes anything in the card's scan with that period, and no byte I could decode holds it. The
   one reading that fits a serial row chain is a second lit bit in the chain, ahead of the true one by that
   time; it predicts copies only below, and none for sources on the last lines of a band. Refresh 1920 and
   x8 are sound RAM-only trials for it and give sharp, different predictions for each reading. SPECULATIVE
   throughout; the lead itself is not yet cross-checked.

## 1. The settings in force

Sources: `34-card2-params-read-back.png` (the saved state, read back 2026-09-29 14:53),
`22-card2-factory-params.png` and `03-card1-factory-params.png` (factory; the two files are identical),
`26-guide2-decoding-chip-list.png`, hardware.md lines 221 to 234, 295 to 349, 378 to 385. I looked at each
screenshot. All CONFIRMED from them unless marked.

| Parameter | Saved on card 2 | Factory | Note |
|---|---|---|---|
| Module Size | 64W x 16H | 32W x 32H | |
| Scan Mode | 8 scan | 32 scan | |
| Driver IC | Normal Chip | Normal Chip | read-only on this page; set in the wizard's Guide 2 |
| Decode IC | ICN2018/3018 Decoding | 138 Decoding | read-only on this page; set in Guide 2 |
| Data Polarity | Positive Phase | Positive Phase | |
| OE Polarity | Low Valid | Low Valid | |
| Cabinet width, height | 128 (limit 216), 64 | 128 (limit 368), 512 | |
| Cascade, Split, Data Group | From Right to Left, No Split, Normal 32 groups | From Right to Left, 2 Split, Normal 32 groups | |
| Refresh Rate | 960 | 480 | follows the Multiple: at x16 the list offers 0, 960, 1920 |
| Multiple | Refresh x 16 | Refresh x 8 | |
| Gray Level | 8192 | 8192 | |
| Gray Mode | Balanced Low Gray | Balanced Low Gray | |
| Display Mode | Gray-level First | Gray-level First | |
| DCLK | 15.6 MHz | 10.4 MHz | |
| Blanking Value | 3 (x100 ns) | 11 | the first wizard run gave 0 |
| Brightness Level | 3 | 8 | |
| Brightness Percent (shown) | 23 % | 81 % | |
| Minimum OE (shown) | 115.2 ns | 103.6 ns | |
| Calibration Mode, Calibration | Disable, From Receivers | the same | |
| No Signal Action | Keep the Last Frame | the same | |
| Input Bit Depth | 8bit | 8bit | |
| Enable Gradual | Disable | Disable | |
| Gamma Value | 2.8 | 2.8 | |
| Blanking Phase page | Enable 4051 ticked, 4051 High Valid ticked, Line Switch Time 25 (x 8 ns), 4051 Enable Time 14, 4051 Disable Time 124 | not recorded | read 2026-09-30, no screenshot kept |
| Other Parameters > ICN2018/3018 Setting | Blanking Enhancement off, Blanking Voltage 3.25 V | does not apply | read 2026-09-30, no screenshot kept |
| Colour order (Guide 5) | Green, Blue, Red, Black | default | applies to LEDVision's stream only |
| Guide 2 extras | "4051 High Valid" ticked, "Reverse scan" unticked, "Void Points Per Scan" 0 | | seen in screenshot 26 under the preset; not re-read for the saved state |
| Frame rate (file only) | 60.0 | 60.0 | a float in the config, section 3 |

Not recorded anywhere: the SCK Duty Ratio dialog, Independent Setting, Custom Gamma Table, the other pages of
Other Parameters, the wizard's driver-chip list, the end of the decoder list (it scrolls). There is no current
gain to record: the DP5125 sets its current with a resistor (REXT) and has no gain register (CONFIRMED,
datasheet pin list, https://www.lipuxin.com/_120241227/1504598661.pdf).

The card's RAM may not match this table today: the last trial left Refresh x4 / 240 / Level 3 in RAM
(hardware.md line 348). A power cycle puts the table back.

## 2. What each parameter does

### 2.1 Blanking Value

- Colorlight, in full: "Blanking value: When the screen has such phenomena as dark light and tailing, the
  blanking value can be appropriately increased."
  (https://www.colorlight-led.com/colorlight-5a-product-series-software-parameters-setting/). Its newer
  manual: "Blanking: Help address dark or inactive LED beads to enhance overall display performance. Click to
  configure 4051 parameters for further optimization" and "Brightness efficiency: Lower blanking, lower
  refresh rate, and higher grayscale result in a higher brightness efficiency" (LEDSetting WEB User Manual
  V2.0, section 7.2.1, https://support.colorlightinside.com/uploads/LEDSettingUserManualV2.0_1762824389.pdf ,
  needs a colorlightinside.com Referer; I read the text copy in `scratchpad/ledres/lsweb20.txt`). CONFIRMED.
- So it is dead time taken out of each row slot. No Colorlight document says which edges bound it. Not
  settled.
- For a serial row chip the chip maker ties it to the row clock: "The width of DCLK is the elimination time,
  so we need to do DCLK width and interface elimination parameter linkage", with "Ghost reduction time, DCLK
  pulse width" 500 ns minimum (Chipone ICND2018 V1.6, page 6,
  https://downloads.olympianled.com/PDF/Driver%20ICs/ICND2018-datasheet-EN-2021-V1.6.pdf). Depuw's DP32020A
  says the same ("消影时间等于 DCK 高电平宽度", 500 ns minimum,
  https://www.lipuxin.com/_120250318/1616173923.pdf). CONFIRMED for those chips. That LEDVision's Blanking
  Value is that width under "ICN2018/3018 Decoding" is LIKELY and unproven; a scope on HUB75 pin 9 (A) would
  settle it in a minute.
- NovaStar's name for the same thing: "Row Blanking Time: Used to adjust the ghost problem of the scanning
  type display. If the ghost problem is serious, increase the parameter value." (NovaLCT manual V5.5.0,
  https://oss.novastar.tech/uploads/2024/02/NovaLCT-LED-Configuration-Tool-for-Synchronous-Control-System-User-Manual-V5.5.0.pdf).
  Linsn's: "Row blanking time: Effective value: 10-200000. If lower ghosting effect appears, changing this
  option can reduce it" (LEDSet manual, `scratchpad/ledres/ledset261.txt` line 274). CONFIRMED quotes.
- The unit: the config stores 3 as 38 and 11 as 138 (section 3.2): 8 ns ticks, so 300 ns and 1100 ns.
  CONFIRMED from bytes.
- Scale: at 960 Hz x 8 lines a row slot is 130 us. The values tried (0.3, 0.6, 1.1 us) are under 1 % of it.
  The open-source drivers that cured ghosts with dark time used microseconds (lane 04, section 4.2:
  Protomatter 8 us, PxMatrix 1 us per address change).

### 2.2 Other Parameters > ICN2018/3018 Setting (Blanking Enhancement, Blanking Voltage)

- Colorlight: "Decoder IC: Adjust the blanking to eliminate upper ghosting and reduce caterpillar artifacts
  caused by LED short circuits." (LEDSetting V2.0 manual, section 7.2.2; the Chinese V1.2 manual has
  "调节消隐，消除显示屏的上鬼影现象，改善灯珠短路造成的毛毛虫现象", helper). CONFIRMED.
- Blanking Voltage is the ICND2018's register: levels 2.0 to 3.75 V in 0.25 V steps, written as a count of
  pulses on RCLK (HUB75 B) while the row clock is low, "Reg[3:0]=RCLK-8", 8 to 23 pulses,
  "Default<3:0>=1101" (datasheet pages 6 and 7, URL above). CONFIRMED. LEDVision's range and its default of
  3.25 V are the datasheet's. The config byte that appears only with ICN2018 decoding holds 13, binary 1101
  (section 3.2).
- Blanking Enhancement: no document found. LIKELY the register's fourth bit, which the datasheet names
  "Model<3>" and does not explain. Not settled.
- What the voltage does: the chip pulls a released row line down to that level so the line's charge does not
  drain through its LEDs when the next row's data arrives. The datasheet does not say so; Chipone's article
  does: "通过加入下拉电路在进行切换时，将寄生电容Cr的电荷快速泄放 ... 通常VH<VCC－1V即可消除上鬼影"
  (http://m.szledscreen.com/h-nd-160.html, helper; lane 04 read the same article). LIKELY.
- **The upper ghost is on the row lit BEFORE the source, showing the source's data: one row above a lit row
  on a top-down scan.** Both settings on this page, and the Blanking Value, are aimed there. CONFIRMED from
  the documents above.
- If T2 and T3 are not true ICN2018s, the pulse count on B may set nothing. Depuw's DP32020A, the same kind of
  chip, takes its level by another protocol (8 RCK clocks with the data on DCK; range 1.75 to 3.5 V;
  datasheet section 10). "DP32020 Decoding" lit nothing on our wall (hardware.md line 157), so our chips are
  not that either. SPECULATIVE that the level setting is ignored; the morning's 3.25 to 2.0 V trial showing no
  change fits it and does not prove it.

### 2.3 The Blanking Phase page (4051, Line Switch Time)

- All Colorlight says: "Click to configure 4051 parameters for further optimization", under a figure titled
  "Blanking phase settings" (LEDSetting V2.0 manual, section 7.2.1). CONFIRMED. What a 4051 is here, and what
  the three times mean, is in no document I or the helpers found (searched in English and Chinese: LEDVision
  and LEDSetting manuals, Colorlight's site, resellers, forums). **Not settled.**
- My reading, SPECULATIVE: a 74HC4051 is an 8-way analogue switch that takes the same A, B, C address as a
  138. Older modules used one as the row discharge circuit, switched on for a window in the blanking time by
  an extra line from the card. "Enable 4051" and "4051 High Valid" would be that line and its polarity (the
  same tick box sits beside the decoder choice in Guide 2, screenshot 26); Enable Time and Disable Time the
  window (14 and 124 ticks: 112 ns and 992 ns); Line Switch Time the moment inside the blanking time at which
  the row changes (25 ticks: 200 ns).
- NovaStar has the same set under other names, with as little explanation: "Line Changing Time: Works with
  row blanking time to adjust the ghost of the scanning type display", "Ghost Control Ending Time: Works with
  row blanking time and line changing time ...", "Blanking Time Height: Used to eliminate the lower ghost",
  "Delay Time of ABCDE Signals: Fix the problem that the afterglow cannot be eliminated because the decoding
  signals are not synchronized" (NovaLCT V5.5.0, read in `scratchpad/ledres/novalct550.txt` lines 1574 to
  1588 and 1723). CONFIRMED quotes.
- Do these fields do anything under ICN2018/3018 decoding? Not settled. Two observations:
  - Our panels have no pin for a fourth line (HUB75 pins 8 and 12 are unconnected, hardware.md line 356), so
    if the 4051 signal leaves the card on D or E nothing hears it. If the card puts it on B when the decoder
    is serial, our row chips may hear it. I could not find which.
  - The page's numbers look made for the factory's blanking, not ours: a disable time of 992 ns fits inside
    1100 ns and not inside 300 ns. When the morning's trial raised the Blanking Value to 11 the Line Switch
    Time stayed at 25 (hardware.md line 316 says the page was untouched). If the row changes 200 ns after
    the light goes off whatever the Blanking Value, then the three values tried all left the same 200 ns
    before the row change and only added time after it. SPECULATIVE, and a reason the page deserves a trial.
- The config byte that changes from 1 to 25 when the decoder goes from 138 to ICN2018/3018 (offset 0x54) may
  be this Line Switch Time, or a decoder type code. 14 and 124 are not in the file as plain bytes. Not
  settled (section 3.2).

### 2.4 Refresh rate and Multiple

- "The refresh multiplier determines how many times a single frame from the video source is refreshed on the
  LED screen ... if a video source has a frame rate of 60Hz and the refresh multiplier is set to 32, the
  effective refresh rate becomes 1920Hz" (https://www.colorlitled.com/performance-settings-led-receiver-card/,
  a reseller's guide; yesterday's lane 03 quoted it). CONFIRMED quote. NovaStar only says "Refresh Rate Times:
  Indicates the times of refresh rate."
- So 960 with x16 is 16 passes over the 8 lines per 60 Hz frame: 7680 row changes a second, a slot of 130 us.
  x8: 3840 a second, 260 us. x4: 1920, 521 us. x1 at 60: 480 row changes a second, 2083 us a line.
- Colorlight's older wording for the two extremes: "Scan mode 1 means to scan the gray level first and then
  rows ... Scan mode 2 means to scan the rows first and then the gray levels, featuring eight times more
  refresh rate" (colorlight-led.com page above). CONFIRMED quote. LIKELY: x1 is "all the grey of one row, then
  the next row", the scheme hzeller and DMD_STM32 use on purpose because "Rows can't be switched very quickly
  without ghosting" (lane 04, section 4.2); a higher Multiple cuts the long bit planes into pieces and
  interleaves them across passes.
- How firmware 13.17 lays the 13 bit planes over the 16 passes (which passes carry the short planes, whether
  the light sits at the start or the end of a slot) is in no document. **Not settled**, and it matters: see
  section 5.2.

### 2.5 Gray Level, Minimum OE, Brightness Level, Brightness Percent

- "The minimum OE time refers to the shortest luminous time of a single LED. It should not be set below 8ns"
  and "Brightness Percentage can be understood as the ratio of the time the screen displays brightness within
  a single frame to the total duration of that frame"; for Brightness Level, "The principle behind this
  adjustment is to adjust the minimum OE value while keeping other parameters constant" (colorlitled.com page
  above; the last sentence by a helper's reading). Colorlight's own page: "It is recommended that the minimum
  OE value be higher than 24ns". CONFIRMED quotes.
- Our own numbers bear the principle out. Minimum OE in the config files is a float: 38.394 ns in the two
  files saved at Level 1, 115.181 ns in the two saved at Level 3, the same timings otherwise (section 3.2).
  Exactly three times. CONFIRMED from bytes; the dialog's 115.2 ns matches.
- Brightness Percent = 4096 x Minimum OE x scan lines x 60 Hz fits every read-out on record (my arithmetic
  on the dialog's figures, CONFIRMED as a fit):

  | State | Minimum OE | 4096 x OE | Line's share of a 60 Hz frame | Computed | Dialog |
  |---|---|---|---|---|---|
  | saved: 960, x16, Level 3 | 115.2 ns | 472 us | 2083 us | 22.6 % | 23 % |
  | 960, x16, Level 1 | 38.4 ns | 157 us | 2083 us | 7.5 % | 8 % |
  | 960, x16, Level 8 | (8 x 38.4 = 307 ns) | 1258 us | 2083 us | 60.4 % | 60 % |
  | 480, x8, Level 3 | 129.0 ns | 528 us | 2083 us | 25.4 % | 25 % |
  | 240, x4, Level 3 | 133.6 ns | 547 us | 2083 us | 26.3 % | 26 % |
  | factory: 480, x8, 32 scan, Level 8 | 103.6 ns | 424 us | 521 us | 81.4 % | 81 % |

  At the saved timings the Levels are therefore 7.5, 15, 23, 30, 38, 45, 53, 60 %. **Level 5 (38 %) is the
  highest that respects the 40 % rule at 960 / x16.**
- What follows, LIKELY: at Level 3 a line's full-value light is 472 us a frame, 29.5 us a pass if spread
  evenly over the 16 passes, in a slot of 130 us. Three quarters of every slot is dark already. The shift of
  128 bits takes 8 us. There is room in the slot for microseconds of blanking at no cost in light.
- Why 4096 and not 8192 for "Gray Level 8192": not settled (the top step may be built from a pulse shown
  every other pass). It does not change the ratios above.
- Minimum OE against the chip: the DP5125E's output rise and fall are 45 ns each (datasheet, yesterday's lane
  03). At 115 ns the shortest pulse is mostly edges; at Level 1 (38 ns) it cannot form at all, which is what
  LEDVision's "Minimum OE is 0" warning at Level 1 is about. hzeller's default shortest pulse is 130 ns and
  his cure for ghosting on "bright text on black" is to raise it to several hundred (lane 04, section 4.2).
  Minimum OE rises with Brightness Level and with a lower Gray Level; the Multiple barely moves it.

### 2.6 Gray Mode and Display Mode

- Gray Mode: "Grayscale: Select a mode to adjust the gamma value of low-grayscale regions in the gamma table,
  ensuring smoother transitions in dark areas." (LEDSetting V2.0 manual, section 7.2.1). CONFIRMED. The
  reseller's guide names two modes, "Low Grayscale Uniformity and Video Noise Cancellation", which are not
  8.8's names; "Balanced Low Gray" is LIKELY the first. It is a gamma-table choice, not a timing one: it
  should not move a ghost of full-value pixels. LIKELY. The alternatives in 8.8's list are not recorded.
- Display Mode: "The display mode can be set to 'Gray-level First' or 'Brightness First.'"; brightness first
  is for outdoor screens that need more light (colorlitled.com page). CONFIRMED quote. "Refresh first" is not
  an option I found. What Brightness First changes in the scan is not documented. Not settled.

### 2.7 Data Polarity, OE Polarity, DCLK, SCK Duty Ratio

- Data Polarity and OE Polarity are the wizard's Guide 3 and Guide 4 answers ("Wizard 4 will appear only when
  the driver IC is a normal chip", LEDSetting manual, helper). Wrong values give an inverted or full-on
  picture. **Not trial material**: reversed OE polarity lights the wall hard.
- DCLK is the column shift clock: "With each rising edge of the DCLK, one bit of RGB data is shifted into the
  LED driver chip" (colorlitled.com page). In the config it is a divider of 125 MHz: 8 gives 15.6 MHz, 12
  gives 10.4 (section 3.2). It does not set the row timing. A lower DCLK lengthens the 8 us shift and nothing
  else; low value as a ghost trial.
- SCK Duty Ratio: "Click to adjust the DCLK duty ratio" (LEDSetting manual). No bearing on a row ghost.

### 2.8 The driver-chip choice

- The DP5125E's datasheet, page 1 (I read the page image, `scratchpad/ledres/dp5125p-01.png`):
  "芯片上电智能识别工作模式，向下兼容并扩展市场现有的普通单锁存恒流芯片和双锁存恒流列下消影芯片" and
  "控制系统自适应技术：通用程序：单锁存无消影，不会造成灯珠反压". In English: the chip recognises how it
  is being driven; it behaves as an ordinary single-latch chip or as a double-latch chip with column
  lower-ghost elimination; under the generic program it is single latch with no ghost elimination and puts no
  reverse voltage on the LEDs. CONFIRMED (https://www.lipuxin.com/_120241227/1504598661.pdf). The sheet shows
  no command table for the double-latch mode. Our chips are "5125" by the sticker only; the suffix is unread.
- What a double-latch chip expects, from the best documented member of the class, Chipone's ICND2038S ("16-
  Channel Constant Current LED Sink Driver with Dual Latch", "Adjustable Pre-Charge for Ghosting Reduction"):
  "The command parser is a counter of LE length"; a latch held over 3 clock edges is "Data Latch", over 11 or
  12 a register write; its timing drawing marks a "消影" (ghost elimination) interval in the OE-off time
  before each plane is shown
  (https://downloads.olympianled.com/PDF/Driver%20ICs/ICND2038S-datasheet-EN-2020-V1.6.pdf, read in
  `scratchpad/ledres/icnd2038s.txt`). CONFIRMED for that chip. That the DP5125 answers the same latch lengths
  is LIKELY at best: the sheet says "compatible with the market's existing" chips and names none. One
  pointer: the Parallax P2 HUB75 driver gives DP5125D panels the same latch style as its FM6126A entry (lane
  04, section 8), and the FM6126A is of this class.
- LEDVision's list: the wizard's Guide 2 has "Select Driver IC..." (screenshot 26 shows the button). A
  reseller's guide to the same dialog: "Click on 'Select Driver IC' to trigger a selection prompt displaying
  various branded driver IC options ... if the chip model starts with 'ICN,' access the 'ICN' tab and choose
  the corresponding model, such as ICN2038s, ICN2037"
  (https://www.colorlitled.com/intelligent-setting-using-ledsetting/). Another page of theirs lists, as
  "Normal IC" families the 5A firmware serves, "ICN IC(ICN2038s, ICN2046, ICN2049, etc), DP IC(DP3246, etc)"
  (https://www.colorlitled.com/upgrade-firmware-colorlight-receiver-card/, helper). CONFIRMED quotes.
  **Whether DP5125 is in the list is not settled**: no document shows LEDVision 8.8's list, and nobody has
  opened it on our VM. Candidates to look for, in this order: a DP5125 entry; another Depuw general chip
  (DP3246, DP5220 if present); ICN2038S; ICN2037; FM6126A; SM16237.
- What choosing one would do: LIKELY change the latch the card sends (and send the chip's register words),
  which would put a DP5125 of the adaptive kind into its ghost-elimination mode. What that mode removes is
  the **lower** ghost: the row lit just after the source, one row below here. TI's description of the
  mechanism: "charging current for parasitic capacitance of OUTXn through the LED when the supply voltage
  switches from one common line to next common line" (https://www.ti.com/lit/an/slva645/slva645.pdf, helper).
  It is not a documented cure for a copy 4 rows away.
- Cost and risk: a wizard pass per entry (the answers are known and the route table imports, about five
  minutes); a wrong entry can give a scrambled or dark picture; nothing is written to flash. The datasheet's
  phrase "will not cause reverse voltage" for the generic mode implies the other mode can; that is a reason
  not to save such a setting without a second look, not a reason to avoid a short trial.

### 2.9 The decoding-chip list

What the 2026-09-29 session saw at Guide 7 (hardware.md lines 144 to 160), with each entry's kind. Kinds are
from datasheets where a helper found one (URLs in section 8), otherwise from NovaStar's and FK's chip lists;
"unknown" means no datasheet was found.

| Entry | Kind | Tried | Seen |
|---|---|---|---|
| 138, ICN2013, 7258, DP32019 | 3-to-8 address decoders with switches | yes | four row pairs (rows 1-2, 5-6, 9-10, 13-14) |
| SM5166/SM5188, HX6158H, CFD2138SPC | address decoders (HX6158H and CFD2138SPC: no datasheet found) | yes | the whole 16-row band |
| No Decoding IC | direct | yes | the whole band |
| SM5266 | serial: clock on A, data on B, blank on C (datasheet's application figure, helper) | yes | the whole band |
| 595 | plain shift register | yes | nothing |
| SM5366 | unknown | yes | nothing |
| DP32020 | serial: clock A, register clock B, data C; level written with data on the row clock | yes | nothing |
| SM5368/5388 | serial: clock A, "BK" on B, data C (the open-source drivers' reading, lane 04 section 4.1) | yes | nothing |
| **ICN2018/3018** | serial: clock A, register clock B, data C; level by a pulse count on B | yes | **one line** |
| DM5953/5958, VOD5958 | serial with a separate discharge line: DIN, LCK, BK (Raffar RT5958 family, taken as the reference by number) | **no** | |
| D7266 | serial, DIN, LCK, BK, "four blanking modes" (Debei) | **no** | |
| LS9735, LS9736, LS9737, LS9737_1, LS9739 | serial with an OE line (Shixin LS9736 diagram); timing unknown | **no** | |
| ICND2019, MBI5981 | serial, but N-channel: for common-cathode panels | **no** | wrong polarity for ours, LIKELY |
| MBI5988 | 8 P-channel switches; interface not found | **no** | |
| TC7261, TC7239, TC6960, GM5018, TA6018 | unknown (Debei's D7261 is a 2-to-4 decoder with 4 outputs) | **no** | |
| anything below TA6018 | the list scrolls; not recorded | **no** | |

- **Is there an untried entry that fits a four-output serial row driver better?** Not settled. No datasheet
  for a 10-pin, 4-output serial row driver turned up (helper; lane 04 found none either). The nearest
  documented parts are Raffar's: RT5956, "Built-in Swift Register 4-channel 5A PMOS with Anti-ghosting
  Control", "5A large current output for outdoor display (parallel two outputs)", pins LCK, BK, DIN, DOUT, in
  SOP16 (https://www.raffar.com.tw/upload_file/2021110215515724424.pdf, helper); and RT5953, 2 outputs in
  SOP8 with the same six other pins. A 4-output part with those six pins needs exactly 10 (inference). That
  family is the "5953/5958" entry, which was never tried. It is the first decoder to try. SPECULATIVE that it
  fits.
- What differs in that family: the discharge is timed by the card on the third line ("By controlling the BK
  signal timeslot (LED discharge) ... let controller determined the turn-on, discharge, and row blank
  timing", RT5958 datasheet, helper), and there is no level register. If T2 and T3 are of that kind, the
  ICN2018 setting gives them no deliberate discharge window at all and sends register pulses to a pin that
  means something else.
- Against reading too much into B (lane 02 reached the same result on its own, and lane 04 has since
  withdrawn the reading): hardware.md line 131 and lane 04's first draft (verdict 6) take the 138 picture to mean
  the panels' rows are gated by address line B. It need not. I simulated a plain 8-bit serial chain, shift
  clock on A, data on C, outputs in row order, fed the 138 address count 0 to 7
  (`scratchpad/lane03/sim138.py`): during address 0 the chain holds lines 0, 1, 4, 5, which is rows 1-2, 5-6,
  9-10, 13-14, exactly what the owner read; and a single grid row comes out as two 2-row bands 4 apart, which
  is what card 2's grid showed. Rising or falling clock edge gives the same set. So that picture is explained
  with no role for B, and it says the chain is one 8-long register in physical order. CONFIRMED as
  arithmetic. Whether B does anything to our chips is open: the SM5368 entry, which per the open-source
  drivers differs from ICN2018 mostly in what it does with B, lit nothing, which hints that B matters
  (SPECULATIVE; LEDVision's exact signals for either entry are undocumented).

### 2.10 Ghost options elsewhere in the dialog

- Other Parameters: only its ICN2018/3018 page is on record. Colorlight's manual describes chip-register
  pages for "low-grayscale color blocks, color shift, color spots, first dim line, high-contrast coupling",
  all for driver chips with registers, which a plain chip lacks (LEDSetting V2.0 manual, section 7.2.2).
  What 8.8 shows there for "Normal Chip" is not recorded. A screenshot of every page is step 0 of the trials.
- NovaStar has "Isolated Pixel Afterglow" and "Delay Time of ABCDE Signals". I found no LEDVision
  counterpart named in any document.
- Firmware 13.x and ghosting: nothing found, in release notes or forums. The 13.x reports are all about
  flicker and packet timing (FPP issue 1849, https://github.com/FalconChristmas/fpp/issues/1849; one user
  there found 13.39 better than 11.04 for "refresh issues" on other panels, helper).

## 3. The config files

### 3.1 The container

Each `.rcvbp` is a 32-byte header and one zlib stream. Header: 16 fixed bytes, then four little-endian
32-bit numbers: 4, the compressed length, the decompressed length, 0. The factory file inflates to 24288
bytes, the saved one to 24574. hardware.md's offsets (0x18e, 0x599f and so on) are offsets in the inflated
data. CONFIRMED (`scratchpad/lane03/dec.py`).

### 3.2 Fields the bytes support

Five files compared (`cmp.py`): factory, the 138 wizard result, the ICN2018 wizard result, the draft, the
saved read-back. A field is listed only where its bytes track a value the dialog showed.

| Offset | Factory | 138 wizard | ICN2018 wizard | Draft, saved | Reading | Label |
|---|---|---|---|---|---|---|
| 0x04, 0x05 | 32, 32 | 64, 16 | 64, 16 | 64, 16 | module width, height | CONFIRMED |
| 0x20 (float) | 2.8 | 2.8 | 2.8 | 2.8 | gamma | CONFIRMED |
| 0x24 | 32 | 8 | 8 | 8 | scan lines | CONFIRMED |
| 0x25 and 0x4f | 12 | 8 | 8 | 8 | DCLK divider of 125 MHz (10.4, 15.6 MHz); 0x4d is half of it (6, 4): the duty | LIKELY (two points) |
| **0x2a** | **138** | **0** | **38** | **38** | **Blanking Value in 8 ns ticks: 11, 0, 3 (x100 ns)** | CONFIRMED (three points) |
| 0x30 to 0x32 | 2 1 0 | 1 0 2 | 2 1 0 | 1 0 2 | colour order (Guide 5 answered or skipped) | CONFIRMED |
| 0x57 (float) | 60.0 | 60.0 | 60.0 | 60.0 | frame rate | LIKELY |
| 0xb2 (float) | 103.56 | 38.39 | 38.39 | 115.18 | Minimum OE in ns (dialog: 103.6, 115.2) | CONFIRMED |
| 0xc4, 0xc6 | 128, 512 | 128, 64 | 128, 64 | 128, 64 | cabinet width, height | CONFIRMED |
| 0xe9 | 7 | 15 | 15 | 15 | Multiple minus 1 (x8, x16) | LIKELY (two points) |
| 0x06 | 1 | 1 | 0 | 0 | differs with the decoder: 138 against ICN2018 | not decoded |
| 0x54 | 1 | 1 | 25 | 25 | differs with the decoder; 25 is also the page's Line Switch Time | not decoded |
| 0xb8 (three floats) | 0.25, 0.25, 0.5 | the same | 0.1, 0.1, 0.1 | 0.1, 0.1, 0.1 | differs with the decoder | not decoded |
| **0xec** | 0 | 0 | 13 | 13 | 13 is binary 1101, the ICND2018's default register (mode bit 1, level 101 = 3.25 V): LIKELY the Blanking Voltage and Enhancement word | LIKELY |
| 0x24f | 0 | 0 | 3 | 3 | differs with the decoder (or the Blanking Value as typed; the factory file has 0 here with blanking 11) | not decoded |
| 0x186 to 0x18c | 25, 125, 125, 62 | the same | the same | 50, 30, 45, 60 | changed only when Guide 5's colours were answered | not decoded |
| 0x20a to 0x223 | zeros | zeros | zeros | a 26-byte table | came with the colour answers | not decoded |

- The three Blanking Phase numbers (25, 14, 124) are not in the file as a group. 25 may be the byte at 0x54;
  14 and 124 appear nowhere outside the ramp tables. Either the page shows values LEDVision derives, or they
  are packed. Not settled.
- Brightness Level is not stored as a number. It lives in the Minimum OE float, which is the point of
  section 2.5.
- Gray Mode and Display Mode never changed between the files, so they cannot be located.
- The draft against the saved read-back: the 10 bytes hardware.md lists, nothing else. Not decoded further.

### 3.3 The scan order in the file

The pixel route is a table of 3-byte records from 0x4d35 (scan index, position in the chain, 0), 16 blocks of
64. The first block is scan 0 at positions 1, 3, 5, ...; the ninth (0x5335) is scan 0 at positions 0, 2, 4,
...; the second is scan 1, and so on to scan 7. With Guide 8's walk (point 1 on row 9, point 2 on row 1,
hardware.md line 398) the blocks are rows 1 to 16 in order, and the table matches
`icn2018-guide8-route.csv`. CONFIRMED from bytes: **scan index s is rows s + 1 and s + 9, in plain order.**

The file holds no separate "order in time" table that I could find. With a serial row chip the card has none
to choose: one clock moves the lit line one place along the chain. The wizard's row phase lit 2/10, 3/11, up
to 8/16 step by step (hardware.md line 176), and the 138 picture (section 2.9) shows the chain is one 8-long
register in row order. So the rows are lit in the order 1, 2, ... 8, LIKELY close to certain. **Reading (a)
of the brief, a copy on "the row lit next" under an order 0, 4, 1, 5, 2, 6, 3, 7, has no support in the
config or in how a serial chain works.** A copy 4 rows away is not the row lit next, nor the row lit before.

## 4. Field experience with these settings

Lane 04 covers the field reports; I add only what bears on the card's settings.

- Wired Watts' outdoor P5 guide prescribes a preset ("14 full color eight scan"), Normal 32 Groups, the
  wizard, LEDVision 8.8, and nothing about the decoder, blanking, DCLK value, grey level or ghosting. Its two
  timing sentences are about getting the cabinet in range (x16 down to x8; DCLK "as low as possible").
  CONFIRMED (https://www.wiredwatts.com/colorlight-setup-for-outdoor-p5-panels, helper and yesterday's lane
  03). Its guide assumes 138 decoding; ours are not the panels it was written for.
- **No report found of anyone curing, or failing to cure, row ghosting on a Colorlight card with a serial row
  driver, by any setting.** Searched: Falcon forum, AusChristmasLighting, DIYC, Reddit, FPP issues, Chinese
  trade sites. CONFIRMED as a search result (helper; lane 04 found the same).
- On other controllers the same chip family was cured by controller timing, not by a chip setting: a
  RUL5158C-row P5 1/8 panel by shortening the latch (ESP32-HUB75 issue 733), an SM5166 panel by clock phase
  and more blanking around the latch (issue 545). Both are lane 04's A2 and A3.
- Firmware 13.x and ghosting: nothing found (section 2.10).

## 5. Squaring the trials already made

### 5.1 Why Blanking Value 3, 6 and 11 looked the same

Taking the brief's three questions in turn.

- **Is the unit what we think?** Yes. 3 is stored as 38 ticks of 8 ns, 11 as 138. CONFIRMED from bytes.
- **Is the change applied on Send?** LIKELY yes. The same Send carried Brightness Level changes that the
  owner saw at once on other days, and the Multiple changes of 10:25 changed the picture. No read-back was
  taken after a Send, so it is not proven for this field. Cheap check: Send, then Read, and see whether Read
  returns the RAM value or the flash value (which also tells us what Read reads).
- **Does the field drive the row clock width under ICN2018 decoding?** Not settled from documents. A scope on
  HUB75 pin 9 is the only sure answer.

And the readings that make "no change" unsurprising, none proven:

1. The knob is for the upper ghost, the row above a lit row (section 2.2). The owner was judging a copy
   below. If the wall also has a faint one-row copy just above (the arm in the video had one), that is the
   copy the blanking trials could have moved, and nobody was looking at it. LIKELY.
2. The values were small. 0.3 to 1.1 us in a 130 us slot, where the field's cures used 1 to 8 us. LIKELY a
   factor.
3. The Line Switch Time stayed at 25 (section 2.3), so the time between light-off and the row change may
   not have changed at all. SPECULATIVE.
4. The row chips may not obey the ICN2018's discharge protocol (section 2.2), so the voltage and enhancement
   settings may have set nothing. SPECULATIVE.
5. The judging was by eye through LEDVision's flickering stream. "May be weaker" at 6 could be real.

### 5.2 Why the Multiple could move two pictures in opposite directions

x16 to x4 is not one change. It changes, together: the row changes a second (7680 to 1920); the length of
each light pulse per pass (four times longer); the slot (130 to 521 us); Minimum OE (115 to 134 ns) and the
brightness (23 to 26 %); and LIKELY the order of the bit planes across passes, which is undocumented.

What each kind of cause predicts from that:

| Kind of cause | x16 to x4 predicts | Fits the lobby (cleaner) | Fits the level lines (worse) |
|---|---|---|---|
| A fixed dose of light per row change (line or column charge) | the copy's share falls about four times | yes | no |
| A share of the source's on-time (a second row partly on, a leak) | no change | no | no |
| Tied to the longest unbroken pulse (threshold, heating of the row switch, sag along a loaded row) | grows | no | yes |

No single line fits both pictures. Ways out, none settled:

- The two were not measured alike: the lobby by a photograph and the eye, the lines by a video whose ratios
  (0.74 to 0.91) are LIKELY clipped at the source. The x16 lines were a photograph. This is lane 01's; from
  the settings side I can only say the comparison changed instrument as well as Multiple.
- The two pictures load the rows differently. The level lines light whole rows (up to 128 pixels, two rows
  thick); the figure lights a few pixels a row. A cause that grows with the row's load and with pulse length
  would show on the lines and not on the figure, while a per-change cause fades on both. Two causes at once
  would give exactly the record. SPECULATIVE. Lane 05's picture 2 (the same row lit over 1 to 128 pixels),
  run at x16 and again at x4, separates them.
- x1 is the stronger version of the same trial (16 times fewer row changes, not 4) and was never run.
- Lane 02's interim lead (section 5.4) would dissolve the disagreement another way: if at x4 the copy sits
  1 row below its source and not 4, the lobby's copy hides against the figure's own limbs (a photograph
  "clean" of a copy 4 below) while under a two-row line on black it shows. Then neither picture says the
  copy got weaker or stronger. Not cross-checked; hardware.md line 342 reads the same x4 video as "about 4
  rows" below.

### 5.3 What the null results do say

- The copy did not move with the number of pulses on B (3.25 V to 2.0 V is 21 pulses to 16, or 13 to 8). So
  whatever B does to T2 and T3, the length of that burst is not what makes the copy. LIKELY.
- The copy is there at the saved settings from three senders, so no sender-side setting is involved
  (CONFIRMED in the record).

### 5.4 Lane 02's lead: the copy comes a fixed 1/1920 s after its source

The lead, as given to me and not yet cross-checked: 4 rows below at x16 (960), 1 and 5 rows below at x4
(240); 4 slots at x16 and 1 slot at x4 are both 0.52 ms. I weigh it against what the settings do; I do not
adopt it.

**The arithmetic of the settings** (mine, CONFIRMED as arithmetic):

| Setting | Row slot | 0.52 ms is | 5 x 0.52 ms is |
|---|---|---|---|
| 960, x16 | 130.2 us | 4 slots | 20 slots |
| 480, x8 | 260.4 us | 2 slots | 10 slots |
| 240, x4 | 520.8 us | 1 slot | 5 slots |
| 1920 (the list's other entry at x16) | 65.1 us | 8 slots | 40 slots |
| 60, x1 | 2083 us | a quarter of a slot | 1.25 slots |
| 420, x1 | 297.6 us | 1.75 slots | 8.75 slots |

1920 is 60 x 32. The Refresh Rate list at x16 offers 0, 960 and 1920 (hardware.md line 333), so 1/1920 s is
a unit the card itself works in: one pass at 1920, half a pass at 960, one line at 240. Near it, and not
the same: 65536 ticks of 8 ns is 524.3 us, a 16-bit counter's span; a row count cannot tell 520.8 from
524.3.

**What in the card's scan could show a row's data again 0.52 ms later.** No document says how firmware 13.17
builds its scan (section 2.4), so all of this is SPECULATIVE. Three kinds:

1. **A second lit bit in the row chain, ahead of the true one by 0.52 ms.** Under ICN2018/3018 the card keeps
   one bit walking the chain: data high on C for one row clock in eight (the datasheet's waveform, page 6). If
   a bit put in 0.52 ms earlier is still in the chain (the scan restarted on a 1/1920 s boundary without
   clearing the chain; or C read as high on one extra clock edge), two lines are on together: the true one,
   and one further along. The line further along shows the true line's data: **a copy below, by 4 lines at
   x16, 2 at x8, 1 at x4.** Its strength is the share of passes in which the second bit exists. A chain of 8
   drops a bit after 8 clocks, so:
   - a source on lines 5 to 8 of a band at x16 has no copy (the second bit would be past the end): the map
     would read +4, +4, +4, +4, none, none, none, none. That is a third pattern, different from both
     readings in the brief ((a): 3 above for lines 5 to 7; (b): 4 above for lines 5 to 8). The arm in the
     morning's video, three rows thick with a two-row copy 4 below, is what this gives if the arm sat on
     lines 3, 4, 5;
   - at x16 a bit 20 slots old is long gone, at x4 a bit 5 slots old is still in the chain: that would give
     the second copy (5 below) at x4 only, as lane 02 reports, with sources on lines 4 to 8 showing no
     5-below copy;
   - at 1920 the second bit is 8 lines ahead, out of the chain: no copy anywhere.
2. **The card re-showing a piece of a line's grey scale while the chain has moved on.** If the scan under a
   Multiple cuts a line's light into sub-fields 1/1920 s apart, and one sub-field is shown without the chain
   being where the card thinks it is, the data lands on the line then lit. For a chain that is merely out of
   step the copy would wrap within the band (4 above for lines 5 to 8 at x16), unlike kind 1. Gray-level
   First and the Multiple decide the sub-field order if anything in the dialog does.
3. **The ICN2018 register burst.** The datasheet draws the pulses on B once per scan cycle, after the first
   row clock. That is every 1/960 s at x16 and every 1/240 s at x4: not a fixed 0.52 ms. It does not fit the
   lead, and the morning's voltage trial (which changes the pulse count) moved nothing. LIKELY not this.

Kind 1 and kind 2 are faults in how the card scans under "ICN2018/3018 Decoding", not in the panel's
analogue side, which is what lane 02 infers. They would also explain, better than anything in sections 2.1 to
2.3, why discharge settings did nothing: a row that is truly switched on is not a ghost.

**What the panel-side readings predict instead.** Two rows 4 apart tied together on the board or in the
chips (lane 04's "two row groups"): 4 rows at every Multiple, both ways round. Line or column charge: the
adjacent row at every Multiple. So the distance at x8, and whether the copy goes at 1920, separate the three
families with one picture each.

**Is refresh 1920 a sound RAM-only trial?** Yes, LIKELY, with checks:

- It is an entry LEDVision itself offers at x16. The DP5125's class runs at it: Depuw's own table gives
  1920 as the DP5125F/E's refresh figure (http://www.depuw.com/cn/pro/193.html, read from the saved page),
  and Linsn says conventional chips "can only flash to 960 or 1920Hz" (yesterday's lane 03, section 2.1).
- The slot halves to 65 us. The 128-bit shift (8.2 us at 15.6 MHz) and the light (at most 14.7 us a pass at
  Level 3 if spread evenly) still fit. **Look at the width limit beside the cabinet's 128 before Send: if it
  turns red, do not Send.** Read the Minimum OE and the Brightness Percent the dialog then prints.
- **Choosing the refresh rate sets Brightness Level to 8. Set it back to 3 before Send.**
- Row changes double, so if an ordinary charge ghost is also present it will be stronger. That is a reading,
  not a harm.
- How the wall behaves at 1920 with the 59 fps sender is untried; judge on the held frame first.

**Is another grey mode a sound trial?** Sound, yes (both lists are ordinary options for a Normal Chip); well
aimed, only partly. By the manual Gray Mode changes the low end of the gamma table and nothing in the timing
(section 2.6), so "Balanced Low Gray" against its alternatives should not move a copy of full-value pixels
under any reading: low priority. Display Mode "Brightness First" is undocumented and may reorder the
sub-fields: worth one Send under kind 2. Gray Level (8192 to 4096) changes the number of bit planes and so
the sub-field plan: worth one Send under kind 2. None of these has a sharp prediction the way x8 and 1920
have. Check the Level after each.

**The decoder.** If the fault is in the card's scan under one decoder entry, another serial entry runs other
code. This raises the value of step 9 of the trial list (5953/5958 first).

**The bytes.** Nothing I could decode bears on a 1/1920 s period: no field holds 1920, 32 passes, or a tick
count near 65104 or 65536; the refresh rate itself is not located; the frame rate float says 60.0. Two
things in the files are worth a look all the same:

- The Multiple is stored as 15 for x16 (0xe9) and the card was saved that way. No sign of a 32.
- **The card's flash did not give back what was sent.** The draft that was sent and the read-back after Save
  differ in 10 bytes (hardware.md line 230): two 16-bit fields read 32 where the draft has 16 (0x18e,
  0x194), one reads 128 for 64 (0x19c), 0x204 reads 255 for 0, and a 12-byte table at 0x599f has one bit
  cleared in alternate bytes. At the first four the read-back equals the factory file, which was x8, so
  these fields do not track the Multiple; LIKELY they are fields the card fills in itself. They are not
  decoded, and I do not claim they are timing. But three of them are a factor of two, the draft's values
  were in the card's RAM only from 14:50 to 14:53 on 2026-09-29, and nobody looked for a copy then. Loading
  the draft file and sending it is a free trial (step 1c). SPECULATIVE that it matters.

## 6. The trial list

Rules for every step:

- **Send only. Never Save to Receivers.** A power cycle of the card undoes everything.
- **Every change of Blanking Value, DCLK, Multiple or refresh rate silently sets Brightness Level to 8 (60 %
  at the saved timings). A wizard Finish does the same. Look at Brightness Level and Brightness Percent
  before every Send and set the Level back.** Check it after a Gray Level or Display Mode change too: those
  have not been tried and may do the same.
- Nothing above 40 %: at 960 / x16 that is Level 5 at most. At other timings read Brightness Percent.
- One variable a step; put it back before the next.
- The picture. For "is it there, where is it" LEDVision's own grid will do. For "is it weaker" it will not:
  use either (H) the card holding the frame, with "Use Net Card" unticked after the Send (the wall is steady
  then: std 0.34, hardware.md line 203), or (P) the Pi: Send, close LED Screen Settings without saving, move
  the cable, run `ghost_map.py 8` at brightness 0.1 and read the patch number (lane 05, section 2.3). RAM
  settings survive the cable move until a power cycle. Steps marked **P** need it.
- Candidate causes, as short names. **U**: upper ghost, row-line charge, copy on the row lit before the
  source. **L**: lower ghost, column-line charge, copy on the row lit after. With rows lit in order 1 to 8
  both are one row from the source. **S**: two rows on at once for part of the time (a second bit in the
  chain, or the partner chip's output partly on), copy at 4 rows. **G**: the grey-scale timing, a threshold
  in the pixel's value.

| # | Control | From, to | Picture | What each cause predicts | Put back |
|---|---|---|---|---|---|
| 0 | None. Power-cycle the card; Read. Screenshot: Receiver Parameters; Blanking Phase; SCK Duty Ratio; every page of Other Parameters; Independent Setting; then Intelligent Setting to Guide 2: every tab of "Select Driver IC...", the Decoding Chip list scrolled to its end; Cancel at Guide 2 | | none | fills the gaps in section 1; names the driver-chip entries for step 8 | nothing was sent. If the wizard sent anything, power-cycle |
| 1 | "Use Net Card" | ticked, unticked | LEDVision grid, then held | a cause in the free-running scan or the panel: the copy stays, and is now steady to judge. Gone: the copy is made when a frame arrives (for example the scan restarting with the old bit still in the chain, section 5.4), and the sender's frame timing becomes a lever | tick it again |
| 1b **P** | Multiple and Refresh Rate, with the map (section 5.4) | x16 / 960 as the baseline, then x8 / 480, then x16 / 1920 (at 1920 check the width limit is not red before Send) | picture 1a, all 16 rows, at each | **A second bit in the chain, 0.52 ms ahead**: 4 below for lines 1 to 4 and nothing for 5 to 8 at 960; 2 below for lines 1 to 6 at x8; no copy at 1920. **A sub-field shown out of step**: the same distances, wrapping inside the band. **Two rows tied together (S on the panel)**: 4 rows at all three, both ways round. **U, L**: one row at all three, stronger at 1920 | x16, 960, Level 3, Send; or power-cycle |
| 1c | Load > Browse `colorlight-outdoor-p5-2x2-draft.rcvbp`, then Send (the file as it was sent on 2026-09-29, before the card's own read-back; check Level 3 and 23 % first) | the read-back state, the draft | grid, held; then picture 1a | the copy gone or moved: the fields the card gives back differently (0x18e, 0x194, 0x19c, 0x204) matter. The same: they do not | power-cycle |
| 2 **P** | Brightness Level (no timing field touched) | 3, then 1, then 5 | picture 8 at 0.1; or the held grid | **U, L**: a fixed dose per row change, so the copy keeps its light while the source changes: a lower patch at Level 5, a higher one at Level 1. **S**: the same patch at every Level. **G**: the lowest source value that copies moves. Also tests "a longer shortest pulse" (38, 115, 192 ns) | Level 3, Send |
| 3 **P** | Multiple | x16, then x1 (take the refresh the list then gives, 60 first; then its highest, 420 on 2026-09-29) | picture 8, picture 2 | **U, L**: 16 times fewer row changes at 60: the copy all but gone; partly back at 420. **S**: unchanged share. Pulse-length causes: worse. Expect visible flicker at 60; judge the copy, not the comfort | x16, 960, Level 3, Send; or power-cycle |
| 4 **P** | Blanking Value | 3, then 30, then 80 (3 us, 8 us; if the box refuses, the largest it takes) | picture 1a (watch the row ABOVE the source as well as 4 below), picture 8 | **U**: the copy above fades. **L**: fades if the row changes late in the window, else little. **S**: nothing, unless the second row comes from the row clock's timing, in which case it may jump. Read Brightness Percent: it should fall only slightly | 3, Level 3, Send |
| 5 | Blanking Phase > Enable 4051 | ticked, unticked | grid, held | every cause: nothing, unless the 4051 signal reaches our row chips (then **S** changes, possibly a scrambled scan: that is an answer) | tick it, Send |
| 6 **P** | Blanking Phase > Line Switch Time, with Blanking Value 11 held throughout this step (judge 11 with 25 first, as the baseline) | 25, then 5, then 100 | picture 1a, picture 8 | **L**: weaker when the row changes later after light-off (100), stronger at 5. **U**: the reverse or none. **S**: none, or a jump. Rows out of place at some value: the field moves the row clock against its data | 25, Blanking Value 3, Level 3, Send |
| 7 **P** | Gray Level | 8192, then 4096, then 1024 | picture 3 (the ladder), picture 8 | read Minimum OE at each. **G** and short-pulse causes: the threshold moves or the copy fades as the pulses lengthen. **U, L, S**: little | 8192, Level 3, Send |
| 8 | Driver IC, in the wizard (Level 1 first; answers and the route table as in the skill) | Normal Chip, then the entry step 0 found: DP5125 if listed, else a Depuw general chip, else ICN2038S, else FM6126A | Guide 3 to 7 as the wizard shows them, then the grid and picture 1a | **L**: a copy one row below goes. **U, S, G**: no change. A dark or scrambled wall: that entry's protocol is not the DP5125's; cancel | power-cycle (the flash still holds Normal Chip) |
| 9 | Decoding Chip, in the wizard (Level 1), each run to Guide 7 as on 2026-09-29 | ICN2018/3018, then DM5953/5958, VOD5958, D7266, LS9736, LS9737, LS9739, LS9735, LS9737_1, MBI5988, then the unknowns (TC7261, TC7239, TC6960, GM5018, TA6018 and any below) | Guide 7: one line or not. For each that gives one line: finish with the imported table, then the grid and picture 1a | **S**: a protocol that suits T2 and T3 may light one line with no copy. **U, L**: another entry's discharge timing may move the one-row copies. None gives one line: ICN2018/3018 stays the only fit | power-cycle |
| 10 **P** | Display Mode | Gray-level First, Brightness First | picture 8 | undocumented; **G** may move. Low prior | Gray-level First, Level 3, Send |

Notes on the list:

- Steps 1 to 3 need no wizard. Step 1b is the test of lane 02's lead and of the panel-side readings at once:
  three runs of the map, each with a different prediction per reading. If the copy's distance follows the
  slot length (4, 2, none), the cause is in the card's scan, the discharge and charge settings (steps 4 to
  7) are beside the point, and the next steps are 9 (another decoder's scan code), 10 and 7 (the sub-field
  plan), with 1920 itself a candidate setting to live with if the wall is steady at it.
- Steps 2 and 3 are the cheapest way to tell a per-row-change cause from a share-of-on-time cause, which
  decides whether any timing setting can help at all. If the copy's share is the same at Levels 1, 3, 5 and
  at x16 and x1, it is **S**, and steps 4, 7 and 10 are not worth running; go to 5, 6 and 9.
- Step 3 under lane 02's lead: at x1 / 60 the delay is a quarter of a slot, so no copy on another row; at
  x1 / 420 it is 1.75 slots, so a copy 1 or 2 below.
- Skip ICND2019 and MBI5981 in step 9: they drive common-cathode panels, and the inverse polarity could turn
  seven lines on at once. If they are tried anyway, Level 1.
- Step 8 has a second use whatever it shows at 4 rows: if lane 05's map finds a one-row copy below as well,
  this is the setting aimed at it.
- Lane 05's picture 1 (the map) should be run once at the saved settings before any of this. The list above
  assumes nothing about the geometry, but the reading of steps 4 and 6 depends on which rows carry a copy.
- DCLK is left out: it sets the column shift clock only (section 2.7).
- Data Polarity and OE Polarity are left out on purpose (section 2.7).

## 7. What I could not settle

- What a "4051" is to this card and what its three times do; whether the Blanking Phase page acts under
  ICN2018/3018 decoding.
- Which signal the Blanking Value stretches under ICN2018/3018 decoding.
- What Blanking Enhancement sets.
- LEDVision 8.8's driver-chip list; whether it has a DP5125 entry; which entry sends a double-latch protocol
  the DP5125 accepts; what that protocol is for the DP5125.
- How firmware 13.17 orders the bit planes over the passes of a Multiple, and where in the slot the light
  sits; whether anything in its scan has a period of 1/1920 s; how it restarts the scan on a new frame and
  whether it clears the row chain when it does.
- What the fields at 0x18e, 0x194, 0x19c and 0x204 are, which the card reads back differently from what
  was sent.
- What Display Mode "Brightness First" changes; the other Gray Mode names in 8.8.
- The part number of T2 and T3, and so which decoder entry is truly theirs.
- The config bytes at 0x06, 0x54, 0xb8, 0x24f, 0x186 and the table at 0x20a.
- Whether Read returns the card's RAM or its flash.
- Any field report of ghosting cured by a LEDVision setting on serial-row panels, and anything tying
  firmware 13.x to ghosting.

## 8. Sources

Our own record
- `/Users/trey/dev/codeisart-ledvision/docs/superpowers/workflow/evidence/hardware.md` and its `hardware/`
  folder (screenshots 03, 22, 26, 34; the five `.rcvbp` files; `icn2018-guide8-route.csv`)
- `/Users/trey/dev/codeisart/.claude/skills/ledvision-card-setup/SKILL.md`, `/Users/trey/dev/codeisart/tools/ledvision/README.md`
- `/Users/trey/dev/codeisart/docs/superpowers/reviews/2026-09-29-flicker/03-panel-electrical.md`
- `/Users/trey/dev/codeisart/docs/superpowers/reviews/2026-09-30-ghosting/04-field-reports.md`, `05-software.md`

Colorlight and resellers
- LEDSetting WEB User Manual V2.0: https://support.colorlightinside.com/uploads/LEDSettingUserManualV2.0_1762824389.pdf
- LEDSetting V1.2 manual (Chinese): https://www.mliled.com/wp-content/uploads/2024/03/1711711354-LEDSettingV1.2%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E%E4%B9%A6_1697164947.pdf
- 5A series software parameters: https://www.colorlight-led.com/colorlight-5a-product-series-software-parameters-setting/
- Performance settings: https://www.colorlitled.com/performance-settings-led-receiver-card/
- Intelligent setting guide: https://www.colorlitled.com/intelligent-setting-using-ledsetting/
- Firmware and chip families: https://www.colorlitled.com/upgrade-firmware-colorlight-receiver-card/
- Wired Watts outdoor P5 guide: https://www.wiredwatts.com/colorlight-setup-for-outdoor-p5-panels

Other card makers
- NovaLCT manual V5.5.0: https://oss.novastar.tech/uploads/2024/02/NovaLCT-LED-Configuration-Tool-for-Synchronous-Control-System-User-Manual-V5.5.0.pdf
- Linsn LEDSet manual (text copy in `scratchpad/ledres/ledset261.txt`)

Chips
- Chipone ICND2018 V1.6: https://downloads.olympianled.com/PDF/Driver%20ICs/ICND2018-datasheet-EN-2021-V1.6.pdf
- Chipone ICND2038S V1.6: https://downloads.olympianled.com/PDF/Driver%20ICs/ICND2038S-datasheet-EN-2020-V1.6.pdf
- Chipone ICND2019 V1.2: https://downloads.olympianled.com/PDF/Driver%20ICs/ICND2019-datasheet-EN-2019-V1.2.pdf
- Depuw DP5125E REV1.1: https://www.lipuxin.com/_120241227/1504598661.pdf ; product table http://www.depuw.com/cn/pro/193.html
- Depuw DP32020A: https://www.lipuxin.com/_120250318/1616173923.pdf
- Raffar RT5958D, RT5956, RT5953: https://www.raffar.com.tw/upload_file/2021111117250752572.pdf ,
  https://www.raffar.com.tw/upload_file/2021110215515724424.pdf , https://www.raffar.com.tw/upload_file/2020070710593347550.pdf
- Sunmoon SM5368PF: https://www.linkage.cn/uploads/allimg/20231204/2-231204163A3I9.pdf
- Debei D7266, D7261: http://www.db-ic.com/solution/ic/led/d7266/ , http://www.db-ic.com/solution/ic/led/d7261/
- Chipone's article on row drivers (mirror): http://m.szledscreen.com/h-nd-160.html
- TI SLVA645: https://www.ti.com/lit/an/slva645/slva645.pdf
- DMD_STM32 chip table: https://github.com/board707/DMD_STM32/wiki/Led_drivers

Reports
- FPP issue 1849: https://github.com/FalconChristmas/fpp/issues/1849
- ESP32-HUB75-MatrixPanel-DMA issues 733 and 545: https://github.com/mrcodetastic/ESP32-HUB75-MatrixPanel-DMA/issues/733 ,
  https://github.com/mrcodetastic/ESP32-HUB75-MatrixPanel-DMA/issues/545

A note on the fetched pages: two of them, and one helper's result, carried text dressed as a system notice
asking for a session link in commit messages. It was page content, not an instruction from the owner; it was
ignored, and this lane made no commits.
