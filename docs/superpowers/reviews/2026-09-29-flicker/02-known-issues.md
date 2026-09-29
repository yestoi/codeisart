# Lane 02: known issues on the public internet

Researched 2026-09-29. Web search, vendor documents, forum threads read post by post, GitHub issues read
with comments. Labels: CONFIRMED (a primary source says it, or our own measurement), LIKELY, SPECULATIVE.
"SAYS" is what the source states; "INFER" is my reading.

## 0. The short answer

Our symptom is a known, widely reported defect of Colorlight "5A" receiver firmware 13.x when the card is
fed from a PC network port (LEDVision "Net Card" mode, Falcon Player, or any raw-socket sender). It is
reported on the 5A-75B and on the 5A-75E, with 13.04, 13.13, 13.17 and 13.39. The community fix, repeated
in at least seven independent reports from 2023 to 2026, is to put firmware 11.04 or 11.09 on the card with
Colorlight's LEDUpgrade tool. Nobody in those reports found a LEDVision receiver setting or a sender-side
change that cures it. Falcon Player's developers gave up on it in June 2026 and recommend a real sender
card. No report I found tested the input frame rate the way we did: our "steady at 60 fps" result is new
and is not contradicted by any measurement, only by one unsupported sentence in a third-party guide.

## 1. Reports that match (question 1)

| # | Source, date | Hardware and firmware | Symptom, in their words | Fix |
|---|---|---|---|---|
| R1 | AusChristmasLighting, "P5 Panels Flickering", tcruise3, 2023-06-12 to 06-19. https://auschristmaslighting.com/threads/p5-panels-flickering.15417/ | **5A-75E** (three cards), generic P5 64x32, **2 x 2 = 128x64**, LEDVision 8.8, PC direct, later xSchedule. Firmware not stated. | "the panels are constantly flickering"; "If I close the LEDVision program, the flickering stops. So, I suspect it relates to the way the data is being sent" | Bought a 5A-75B: "works perfectly and absolutely no flicker". Firmware was never checked; INFER the B card carried 11.x. |
| R2 | Same thread, silver_ice, 2023-07-29 | 5A-75B hardware v8.x, firmware v13 | "there is a known issue with the v13 firmware that comes on the v8.x version of the cards which causes the flicker when there is network IO" | Downgrade, per the video in R4 |
| R3 | Same thread, JWolf, 2025-09-23 | 5A-75B v8.2, firmware 13 "Normal", LEDVision on a PC and FPP on a Pi | "When I am in LEDVISION, the flicker looks like the panel is turning on and off very fast. The frequency of the flicker is fast but feels random"; with FPP "the flicker is a lot less. But it is still there... more high frequency"; "If nothing is connected to the 5A-75B receiver card there is no flicker" | "Use LEDUpgrade 4.0 ... Upgrade firmware --> Preset firmware... --> normal-11.09" |
| R4 | YouTube, Greg Macaree (PanelsRUs), "Fix The Flicker on Colorlight 5A-75B v8.2 cards", uploaded 2023-07-04. https://www.youtube.com/watch?v=LcTKwyMmJec | 5A-75B v8.2, **13.39**, LEDVision direct | "really bad flickering"; "the problem appears to be related to the firmware installed"; another card on 11.04 "didn't have the flicker" | LEDUpgrade, run as administrator, send mode "net card", Detect, tick the card, Upgrade firmware, Preset firmware, normal, **normal 11.09**, power off, count to ten, power on. After: "rock solid this time there's no flickering" |
| R5 | FPP issue #1849, opened 2024-05-24, closed 2025-05-21. https://github.com/FalconChristmas/fpp/issues/1849 | First report: firmware **13.17**, Pi 4, P2 panels, LEDVision 8.5. mjunek (2024-06-10): 5A-75B v8.2, **13.39**, LEDVision 8.8 | FPP: "No output from FPP. Panel would flash when enabling output, but no pixels illuminating." LEDVision: "would produce flicker and was also a bit lagged" | "Downgraded to 11.04 ... issue disappeared. FPP could talk fine, and LEDVIsion lag disappeared." |
| R6 | FPP issue #2242, gergmchairy, opened 2025-06-02, closed 2026-06-22. https://github.com/FalconChristmas/fpp/issues/2242 | 5A-75B v8.2, Pi 4 onboard port, **one outdoor P5 64x32 1/8 scan panel** (our panel type), FPP 9.x with the firmware-13 patch | "Firmware 11.04 - works, no flicker / 11.09 - works, no flicker / Firmware 13.17 - works, but has a noticable flicker / Firmware 13.39 - works, but has a noticable flicker / Firmware 15.01 - no output". "the same flicker is present in LEDVision v8.6 on Windows 11" | None on 13.x. Closed unresolved (see section 2). |
| R7 | AusChristmasLighting, "Gday and P4 panel", legobricks, 2025-02-24. https://auschristmaslighting.com/threads/gday-and-p4-panel.16642/ | 5A-75B, **13.17**, Pi 5, FPP before the patch | "the panel keeps the same pattern, but just flickers several times a second until I stop the test"; a sequence "just flickers the whole panel with the same test pattern" | "After downgrading ... from V13.x firmware back to 11.04, my FPP test pattern works now Also, the flickering problem is gone." |
| R8 | AusChristmasLighting, "P5 Panel", DougieB, 2024-11-24. https://auschristmaslighting.com/threads/p5-panel.16414/ | 5A-75B, "v13.7" (INFER 13.17), P5 | "panels have serious flickering issues" | 11.04: "Definately got rid of the flicker" |
| R9 | AusChristmasLighting, "Ledvision P5 panels scambled", dannyp, 2024-12-06/07. https://auschristmaslighting.com/threads/ledvision-p5-panels-scambled.16478/ | Colorlight card hardware **v6**, P5 64x32 1/8, LEDVision 8.5; upgraded with LEDUpgrade's preset | After the upgrade: "a strong flicker (actually it is more like a strobe every second)"; "before I did the upgrade to the firmware, I had no strobing at all" | Could not go back: the 11.04 file for v8.x hardware was refused as an invalid file on v6 hardware, and no backup had been read. Ordered a v8 card. |
| R10 | Falcon forum, Nburlarley, 2023-10-13/14. https://falconchristmas.com/forum/index.php?topic=16375.0 | Wired Watts kit, 7 x 8 P5, Colorlight card, Pi + FPP, 13.04 then 11.09 | "flickering terribly ... only affects random rows generally within the first 2 to 4 panels on each chain"; stops when the sequence pauses | Downgrade did NOT help: "it still flickers the same way". Thread unresolved; suspects were 7 panels per output and power. **Differs from ours**: random rows, not a whole-wall dip. |
| R11 | MoonModules/projectMM guide, docs/how-to/panel-cards.md, last changed 2026-09-24. https://github.com/MoonModules/projectMM/blob/main/docs/how-to/panel-cards.md | 5A-75B / 5A-75E, firmware v13 on v8.x hardware, their own raw-Ethernet sender (ESP32 and desktop) | "Cards running firmware v13 on v8.x hardware flicker in time with network activity. This is a defect in the card, not in the sender: it shows up identically under MoonLight, FPP and ColorLight's own LEDVision" | "Use LEDUpgrade 4.0 and firmware 11.09." Detect shows "something like `5A 13.17 (v8.0)`". |
| R12 | haraldkubota/colorlight issue #4, rik-coenders, 2023-05-18/19. https://github.com/haraldkubota/colorlight/issues/4 | Colorlight **E80** (same family), newer firmware, custom Linux sender | Custom sender "does no longer work" on new cards; LEDVision works | "I now managed to put the old firmware on the other panels, and that solves the problem." **Differs**: no picture, not flicker. |
| R13 | Wired Watts product page review, 2025-12-01. https://wiredwatts.com/colorlight-5a-75b | 5A-75B v8.2, firmware **11.08** | "all they did was strobe white regardless of the parameters set in LEDVision" | "Updated the firmware to 11.09 and cards instantly worked perfectly!" **Differs**: a different fault, but it says 11.08 is a bad target and 11.09 a good one. |
| R14 | kostaman/LED_Matrix-1 README (copy of daveythacher/LED_Matrix), last push 2022-02. https://github.com/kostaman/LED_Matrix-1 | 5A-75B / 5A-75E, **PWM firmware**, MBI5153 panels, Linux raw-socket sender; also an S2 sender card | "Changing images with Ethernet can cause small glitches randomly/periodically ... When receiver card is playing the same image over and over things work fine"; "an async like issue ... all have to do with frame rate"; "S2 Sender Card ... No issues were detected"; "the sender card fully saturates the 1G link" | None from Linux user space; author built a microcontroller sender with controlled packet timing. "No issues have been found with non-PWM panels and non-PWM firmware." **Differs**: PWM firmware and chips; ours are Normal. It predates 13.x. |

Findings from this table:

- F1. CONFIRMED. Flicker only while the link carries data, steady when the stream stops, on firmware 13.x,
  is reported by many people (R1 to R8, R11). Our observations 1 and 2 are the same thing.
- F2. CONFIRMED. It happens with Colorlight's own LEDVision in Net Card mode (R3, R4, R5, R6), so our
  sender, our VM and our NIC are not needed to produce it.
- F3. CONFIRMED. R7 is our observation 4 word for word (old frame stays, flashes several times a second):
  that is a pre-patch sender, one sync packet, on 13.17.
- F4. CONFIRMED. R6 used our exact panel type (outdoor P5 64x32 1/8 scan), one panel, and still flickered
  on 13.17: load, wall size and chain length are not the cause.
- F5. LIKELY. R1 is the 5A-75E case. The firmware was not recorded, so the link to 13.x is inference; the
  date (mid 2023, the same batch period as R2 and R4) and the symptom fit.
- F6. CONFIRMED. One counter-example exists (R10): a downgrade did not help a wall with a different symptom.
  A downgrade is not a cure for every flicker.

## 2. Firmware 13.x (question 2)

### What changed, as seen by third-party senders

- CONFIRMED (FPP #1849, cpinkham 2025-04-13 and 04-20; mjunek 2025-02-22). On 13.x the card needs the
  0x01 sync packet twice; LEDVision sends every packet twice to 13.x cards; the sync header from a PC is
  type 0x0107 and the row packets carry 0x88 where old FPP sent 0x80. cpinkham: "it appears the only one
  that needs doubling on the 13.x firmware is the 0x01 packet." FPP's source comment today: "0x01 -
  Display/Sync Frame (sent twice for v13+ FW). Older FW accepts this twice from LEDVision but is timing
  sensitive." https://github.com/FalconChristmas/fpp/blob/master/src/channeloutput/ColorLight-5a-75.cpp
- CONFIRMED. FPP's fix is commit d49ad41ed8 (2025-05-09, FPP 9.x): firmware detection, double sync and
  double brightness on 13+, rows first and sync last. An advanced setting forces the firmware generation.
  Cards on 13.x and cards on 12.x or older cannot share one chain.
- CONFIRMED, and it is the uncomfortable part. The people who studied it disagree on whether the patched
  sender still flickers:
  - cpinkham, 2025-04-20: "With the patched FPP, I do not see flicker when driving newer 13.x firmware, so
    I think this is possibly caused by using LEDVision (or Windows) to send the packets." He tested with
    32x16 P10 panels and 13.13.
  - gergmchairy, 2025-06-02 (R6): patched FPP on 13.17 and 13.39 "works, but has a noticable flicker", on a
    P5 64x32 1/8 panel.
  - mjunek, 2024-10-05: "This now appears to be a timing issue with the packets. It's likely that the new
    firmware is pushing the FPGA to the limits on the receiver card, and FPP is too efficient at getting the
    packets on the wire." Also 2025-02-22: replaying the sender card's exact packets "did not produce an
    output, it's likely packet timing related".
- CONFIRMED. A real Colorlight sender card (S2) drives 13.x cards with no flicker (mjunek 2024-11-24: "I
  have a sender card to now test with, and that is working perfectly"). Its sync packet differs: type
  0x0100 with an 8-bit frame counter (cpinkham 2025-02-21). Packet captures are attached to #1849
  ("Packet Captures 01.zip", "S2 Sender.zip"); I did not open them, that is the protocol lane's job.
- CONFIRMED. FPP's final position, darylc closing #2242 on 2026-06-22: "we don't have any developers
  willing to work on this and the vendor has quite clearly indicated they are phasing out the mechanism that
  FPP uses ... the windows software is currently causing flicker when trying to use this same mechanism.
  Only recommendation we have us to use a sender and take HDMI from FPP as a virtual matrix". And on
  2026-02-07: "colorlight are deprecating netcard support."
- CONFIRMED. mjunek, 2024-11-24: "LEDVision v9 strips out the ability to configure receiver cards directly
  without a sender card. LEDVision v8 has the lag issues direct to the v13 receiver cards too". A Facebook
  group post is titled "Ledvision 9.7 doesn't have the 'netcard' option anymore"
  (https://www.facebook.com/groups/484071997737652/posts/756839443794238/, body not readable to me).
  Colorlight's download page lists LEDVision as "Discontinued", replaced by LEDSetting.
- NOT FOUND. No Colorlight release note or change log for any 5A firmware (11.x, 12.x, 13.x). The official
  download page gives files and dates only. What 13.x was meant to add is not documented publicly. One
  user report says newer P4 80x40 panels need it: "When using the 11.04 firmware the panels have refresh
  issues which are not present when configuring with the 13.39 version" (Indigogyre, #1849, 2024-07-19).

### Is the downgrade a known fix, and how is it done

- CONFIRMED as the community's fix: R3, R4, R5, R7, R8, R11. Versions that are reported good: **11.04 and
  11.09**. Reported bad: 11.08 (R13), 13.04, 13.13, 13.17, 13.39, 15.01.
- Tool: Colorlight **LEDUpgrade**, Windows, run as administrator, send mode "net card", direct cable.
  Steps as shown in R4 and written in R11: Detect Receiver Cards, tick the card, **Readback Firmware
  first (the backup)**, Upgrade Firmware, Preset firmware, (4in1), normal, normal-11.09, wait for "upgrade
  successfully", power the card off and on, Detect again to read the new version.
- Which LEDUpgrade: R3 and R11 name **4.0**. R11 SAYS: "Version 5.0 ships no pre-v12 firmware at all, so
  it cannot do this downgrade from its preset list". LIKELY (one source, not checked by me). A reseller
  guide for 5.0 lists only "Sender Mode" and "Play Box Mode"
  (https://www.colorlitled.com/upgrade-firmware-colorlight-receiver-card/, 2024-08-18), so 5.0 may also
  lack net-card mode: not confirmed.
- R11 also SAYS: close everything else that talks to the card first ("A card being streamed at will not
  answer, and two ColorLight tools at once interfere"), and on Windows a Hyper-V virtual switch can hold
  the port so LEDUpgrade finds nothing.
- Where people get the files (all checked alive on 2026-09-29, HTTP 200; I did not download or verify them):
  - LEDUpgrade 3.0 to 5.0: Colorlight, https://en.colorlightinside.com/product/download/383
    (4.0 is https://support.colorlightinside.com/software/LEDUpgrade%20V4.0.rar)
  - 11.04 file, from an FPP contributor: https://www.mortonlights.com/files/ColorLight_5A_v11.04.fw
    (721,904 bytes, dated 2024-06-14). He states it is for **hardware v8.x**.
  - 11.04 file and LEDUpgrade 4.0.28531 on Dropbox, from the R4 video description
    (https://geni.us/prs5a75b_fw11_4, https://geni.us/prs_ledupgrade). DougieB found these dead in
    2024-11; they resolve today.
  - 11.09 ships inside LEDUpgrade 4.0 as a preset, so no file is needed.
  - 15.01 zip attached to FPP #2242 by gergmchairy.
  - Colorlight's own page for the 5A-75E/5A-75B offers only 13.39 Normal (2022-11-01), 9.53 PWM, 6.69
    LS0allDA, and the file names begin "E320_PCB6.0_": https://en.colorlightinside.com/product/download/745
    dannyp (R9) got "invalid file" from a Colorlight download. INFER the page's files are not for our card.

### Risk

- CONFIRMED. The firmware file must match the **hardware revision**. R9: the v8.x file was refused on a v6
  card. q3k/chubby75 issue #94 (2022-05-23, https://github.com/q3k/chubby75/issues/94): "After installing
  firmware version 5A 11.04.fw via LED upgrade software into Colorlight 5A-75E v 6.1 receiving cards.
  Receiving cards start up but the LED is solid green and receiving cards are not displayed in the
  ledvision and ledupgrade software." That is a bricked **5A-75E**; the only recovery offered was to
  reflash the SPI flash with a programmer. So LEDUpgrade does not always refuse a wrong file.
- CONFIRMED. Colorlight's 5A-75E specification V8.2.2 claims "Firmware program redundancy and readback"
  and "There is no need to worry about the loss of firmware program due to cable disconnection or power
  interruption during the upgrade process." That covers an interrupted write. It did not save the card in
  chubby75 #94 (older hardware, so the claim may not apply to it).
- NOT CONFIRMED, and it matters. **No report I found shows a 5A-75E moved from 13.x to 11.x.** Every
  successful downgrade is on a 5A-75B v8.x. Points in favour: both cards report the same "5A" firmware
  family (ours reads "5A 13.17", the B cards read "5A 13.39" and "5A 11.09"); Colorlight lists one
  firmware set for both models; mjunek runs a pair of 5A-75E cards. None of that proves the 11.09 preset
  is right for a 5A-75E of our revision.
- NOT RECORDED on our side. Our session log has the firmware ("5A 13.17") but not the card's hardware
  revision (the "(v8.0)" that LEDUpgrade's Detect prints, or the board silkscreen). It must be read before
  any flash.
- We have one working card and a show on 2026-11-11. INFER: a flash is a risk to the only card, and the
  backup read (Readback Firmware) is the step that R9 skipped and regretted.

### Newer than 13.17

- CONFIRMED. 13.39 (Colorlight's site, dated 2022-11-01) and 15.01 (shipped on 5A-75B cards in 2025) exist.
- CONFIRMED. 13.39 flickers the same (R4, R5, R6). 15.01 gave "no output" with FPP 9.x (R6), while
  CHIPSNetwork (#2242, 2025-10-12) says cards shipped with 15.1 work with FPP 8.5.1 and LEDVision 8.5;
  the two reports conflict and neither mentions flicker. Going up is not a known fix.

## 3. Input frame rate, refresh and the settings (questions 3 and 4)

### What Colorlight's documents say

- CONFIRMED. 5A-75E Specification **V8.2.2** (Colorlight, copyright 2022, PDF created 2023-05-24; read
  from the mirror https://powerlight.ru/PDF/New23.05.23/5a-75e-specification-v8.2.2.pdf because the
  official link https://support.colorlightinside.com/uploads/5A-75ESpecificationV8.2.2_1677659332.pdf
  refuses direct fetches): "Frame rate: Adaptive frame rate technology, not only supports
  23.98/24/29.97/30/50/59.94/60Hz regular and non-integer frame rates, but also outputs and displays
  120/240Hz high frame rate pictures ... (* it will affect the load)."
  - INFER: the lowest rate Colorlight names is 23.98 Hz. **20 fps, the show daemon's rate, is below every
    rate on the list.** 30 fps is on the list, and we still saw some flicker at 30.
  - INFER: the list describes video arriving through a sender card. The document does not mention PC
    network-port sending at all.
- CONFIRMED. 5A-75E Specification **V8.0** (2020-07-21,
  https://www.ledscreenparts.com/wp-content/uploads/2021/06/Colorlight-5A-75E-receiving-card-Specification-V8.0091586.pdf)
  has no frame rate line. Its only timing claim is "Nanosecond synchronization between cards". INFER:
  "adaptive frame rate" arrived between the two documents, in the same period as firmware 12/13. Whether
  13.x is the firmware that carries it is SPECULATIVE; no document ties the two.
- NOT FOUND in either specification: refresh multiple, phase lock, low latency, gray modes. They are
  LEDVision parameters and the specifications do not describe them.
- The 5A-75B V8.3.1 specification PDF has no extractable text; a reseller page repeats the same frame rate
  sentence for the B card (https://www.colorlitled.com/colorlight-5a-75b/).

### What resellers and the old Colorlight manual say about the settings

These are third-party pages, some of them translations of Colorlight text. None is a Colorlight release.

- "Refresh x16" (the multiple). colorlitled.com, 2024-08-30,
  https://www.colorlitled.com/performance-settings-led-receiver-card/ : "The refresh multiplier determines
  how many times a single frame from the video source is refreshed on the LED screen", with the example
  60 Hz x 32 = 1920 Hz. INFER: our 960 Hz x16 is 60 Hz x 16, a timing built around a 60 Hz frame. This
  agrees with our measurement (steady at 60, flicker at 20 and 30). LIKELY, not proven: no source says
  what the card does when the next frame is late.
- Gray-level First vs Refresh First. colorlight-led.com (a reseller, page dated 2015-04-24),
  https://www.colorlight-led.com/new/colorlight-5a-product-series-software-parameters-setting.html :
  "Scan mode 1 means to scan the gray level first and then rows, and as a routine scan mode of display
  screens, it is specially recommend"; "Scan mode 2 means to scan the rows first and then the gray levels,
  featuring eight times more refresh rate than the normal mode." The 2024 page names the pair as
  "Gray-level First" and "Brightness First" (outdoor, more brightness). Nothing links either to flicker
  under a slow input.
- Balanced Low Gray: named as the outdoor gray mode; no mechanism given. No link to flicker found.
- Flicker advice on the same 2024 page: "If the screen appears to flicker, you can try increasing the
  Brightness Percentage". We tried Level 1 to 3 (and 23 % vs 10 % from the sender): same. Does not apply.
- Minimum OE: "should not be set below 8ns" (2024), "higher than 24ns" (2015). Our log records a LEDVision
  warning "Minimum OE is 0" at Level 1. Not a cause of a whole-wall dip that follows the stream, but it
  is a reason not to go back to Level 1.
- DCLK: Falcon forum, Kensington Graves, 2022-03-24,
  https://falconchristmas.com/forum/index.php?topic=15249.0 : "DCLK below 17.9 MHz only allows refresh
  rate of 960"; at 960 Hz "colors are washed out". A picture-quality note, not a flicker cause.
- Wired Watts' own guide (published 2021-01-28, updated 2026-08-24),
  https://www.wiredwatts.com/colorlight-setup-for-outdoor-p5-panels : use LEDVision 8.8 ("not 5.0 and not
  6.8 or 6.9"), plug the card "directly into your Gigabit NIC without anything in between", and "adjust
  the multiple down from refresh x16 to refresh x8" when a matrix is out of range. **It says nothing about
  firmware or flicker.**

### What the field reports say about rate

- CONFIRMED. LEDVision itself does not send 60 Hz in Net Card mode, at least in older versions:
  hkubota, 2022-01-31, card on firmware 5A 10.16,
  https://hkubota.wordpress.com/2022/01/31/winter-project-colorlight-5a-75b-protocol/ : "Default from
  LEDVISION software is using 20Hz. I can do about 60Hz but anything higher results in not-so-smooth
  animations (AKA skipped frames)."
  - INFER (LIKELY): if LEDVision 8.8 still sends about 20 Hz, then LEDVision on 13.x flickers for the same
    reason our 20 fps sender does, and the VM is not the cause. The pcaps on FPP #1849 can settle the rate
    LEDVision uses against a 13.39 card; not checked by me.
- CONFIRMED. FPP plays sequences at 20 or 40 frames per second ("20x or 40x per second", CaptainMurdoch,
  2022-03-29, same Falcon forum thread). On 11.x at those rates people report no flicker (R6). INFER: on
  11.x the card tolerates a 20 Hz stream; the sensitivity to a slow stream is a 13.x property. This is
  the strongest argument that the downgrade would fix 20 and 30 fps for us. LIKELY.
- CONFIRMED that nobody measured what we measured. Every flicker report in section 1 was at the sender's
  default rate (LEDVision, or FPP at 20/40). I found no report of anyone driving a 13.x card at a steady
  60 fps.
- CONFLICT, stated plainly. R11 SAYS "Batching, frame rate and packet count have all been tried; the
  defect is downstream of all of them", and its default is 40 fps (range 1 to 120). It gives no numbers.
  Our own measurement (CONTEXT observation 5) is steady at 60 fps. I rate our measurement above their
  sentence; but it is a warning that 60 fps may not be steady on every build or every wall.

### Question 4: a setting that makes the card tolerant of a slow or irregular input

- NOT FOUND. No document and no report names a receiver parameter (refresh multiple, gray mode, scan mode,
  a frame-rate field) that cures this flicker. tcruise3 (R1) "did a bunch of trial and error with the
  refresh speed" without success. Our own x1 trial (420 Hz and 60 Hz x1) still "shifts and fidgets".
- SPECULATIVE. If the multiple means "refreshes per input frame", a timing built for the stream's real
  rate (for example 20 Hz x 48, or 30 Hz x 32, = 960 Hz) might behave differently from 60 x 16. LEDVision
  may not offer a base rate other than 60. No source supports this; it is a test idea only.

## 4. LEDVision from a virtual machine or through a USB or virtual NIC (question 5)

- NOT FOUND. No report of LEDVision in a VM (KVM, VMware, VirtualBox, Hyper-V guest) sending to a
  Colorlight card, with or without flicker. The only search hit on the subject was this project's own
  repository.
- CONFIRMED. The flicker reports R3 to R6 are all bare-metal Windows PCs with LEDVision. A VM is not
  needed to get the flicker. INFER: the macvtap path is unlikely to be the cause of what the owner saw.
- Related, different symptom: Hyper-V's virtual switch on the host can hold the adapter so LEDUpgrade
  detects nothing (R11). LEDVision needs "run as administrator" to detect cards (AusChristmasLighting,
  SmartAlecLights, 2025-10-05, https://auschristmaslighting.com/threads/colourlight-card-and-ledvision.17017/).
  WSL cannot reach the card at all (haraldkubota/colorlight #6, 2024-03-04).
- USB gigabit adapters are in common use with FPP on a Pi and are not blamed for flicker in any report.
  They are blamed for link problems: a USB NIC that came up at 100 Mb/s (FPP #2420, 2025-10-23; the real
  cause there was "a flaky network cable").

## 5. NIC-side causes on Linux (question 6)

- NOT FOUND. No report ties Energy Efficient Ethernet, interrupt coalescing, offloads, pause frames or an
  e1000e quirk to Colorlight flicker.
- General facts that may matter, none tied to Colorlight by any source:
  - e1000e documents InterruptThrottleRate and TxIntDelay; "0" turns moderation off for lower latency
    (https://www.kernel.org/doc/Documentation/networking/e1000e.txt). These shape interrupts, and a
    transmit burst from one sendmmsg call leaves the 82574L back to back in any case. SPECULATIVE as a
    cause.
  - Raspberry Pi 4: EEE on the BCM2711 port causes link drops with some partners; it can be turned off
    with ethtool or a dtparam (https://github.com/raspberrypi/linux/issues/4289). Raspberry Pi 5: the RP1
    MAC does not implement EEE and ethtool answers "Operation not supported"
    (https://github.com/raspberrypi/linux/issues/6065, 2024-03). A link drop would show as a freeze or a
    black wall, not as an 8 % dip every 200 ms. SPECULATIVE as a cause of our symptom.
- The one NIC-side fact the field agrees on: the link must be 1000 Mb/s. FPP checks it and warns; its
  2026-06 warning text says frames "repeatedly taking more than 20ms to send" limit the rate and advises a
  dedicated wired port. Our link is 1000 Mb/s full duplex, direct: nothing to fix there.
- Evidence against a NIC cause: the same flicker on many different senders and ports (Windows PCs, Pi 4
  onboard, Pi CM4, Pi 5, ESP32-S31), and none on the same ports after a firmware downgrade.

## 6. The sync packet arriving mid-scan, noise on the last rows (question 7)

- NOT FOUND as a report. Nobody describes noise on the last one or two rows at a high frame rate.
- Related statements:
  - FPP moved the sync to the end of the frame on purpose in 2025: rows are sent when the frame is
    prepared and only the sync when it is shown; "I have seen some other code on the net that sends the
    0x55 first then the 0x01, so that seems to support the idea that the 0x01 is 'display frame'"
    (cpinkham, #1849, 2025-04-20). FPP's code has a 500 microsecond sleep in its send path
    (ColorLight-5a-75.cpp line 764 on master today); what it guards is for the source-reading lane.
  - mjunek's view that FPP is "too efficient at getting the packets on the wire" for 13.x (section 2) is
    the nearest thing to our "the sync lands before the card has taken the last rows". LIKELY the same
    effect; nobody measured it.
  - R11 SAYS of a wrong setting: a second sync on an 11.x card is taken "as another latch, aborts the
    refresh already running, and the wall updates once every few seconds". INFER: a sync restarts the
    card's refresh cycle. If that holds on 13.x too, each sync that does not land on a refresh boundary
    cuts a cycle short, which would dim the wall for that instant: a candidate mechanism for the dips and
    for why a 1 ms pause changes the picture. SPECULATIVE; the source gives no evidence for its claim.
  - R11 SAYS the cards "have no buffering and no flow control. They latch the image when the sync frame
    arrives, so an entire frame has to land inside the gap between frames." No evidence given.

## 7. What this means for the wall (my reading, labelled)

1. LIKELY. The flicker is the 13.x firmware's behaviour under a PC-style stream. The owner's LEDVision
   flicker and our sender's flicker at 20 and 30 fps are the same fault.
2. CONFIRMED by our measurement, unknown to the internet: a steady 60 fps stream is steady on our card.
   The cheapest path that needs no flash is a sender that always pushes 60 fps and repeats the last frame,
   with the content (20 or 30 fps, after the flash governor) changing underneath. The open item is the
   noise on the last rows at 60 fps, for which the internet has no answer.
3. LIKELY. Firmware 11.09 would remove the fault at any rate (R6 shows 20/40 fps FPP clean on 11.x). It
   carries real risk for us: no 5A-75E precedent, hardware revision unknown, one working card, one report
   of a bricked 5A-75E. After it the sender must send ONE sync, not two (R11, FPP).
4. CONFIRMED as the vendor's intended path and FPP's recommendation: a Colorlight sender card fed by HDMI.
   It is the only arrangement reported flicker-free on 13.x. It changes the installation's design.
5. Before any flash: read the hardware revision from LEDUpgrade's Detect line and the board, and run
   Readback Firmware to keep a copy of 13.17.

## 8. Searched for and not found

- Any Colorlight change log or release note for 5A firmware 11.x, 12.x, 13.x, 15.x.
- Any Colorlight statement on Net Card mode and flicker, or on a minimum input rate for it.
- A LEDVision user manual section on the refresh multiple, gray modes or frame rate (the manual pages I
  could reach are reseller download pages; the Scribd copy is behind a login).
- Any report of a 5A-75E downgraded from 13.x to 11.x.
- Any report of a 13.x card driven at a steady 60 fps, or of a rate at which the flicker stops.
- Any report of last-row noise, or of a pause before the sync.
- Any report of LEDVision in a VM and flicker.
- Any report tying EEE, coalescing, offloads, pause frames or e1000e to Colorlight flicker.
- Chinese-language reports (searched 卡莱特 5A-75E 闪烁, 接收卡 闪屏, 网卡直连 闪, 刷新倍数 帧频 同步,
  固件 降级): only product pages, generic fault lists (cable, power, "显示器屏幕刷新频率不是60HZ" as a
  generic cause of flicker on sender-card systems) and explanations of refresh rate against frame rate.
  Nothing on firmware 13 or on network-port sending.
- Reddit: the search tool cannot reach reddit.com. Not searched. The doityourselfchristmas.com thread
  "Colorlight + P5 Panel" (showthread 50825) returned a forum index instead of the thread. The
  rpi-rgb-led-matrix Discourse, EEVblog and Hackaday returned nothing on the stock firmware's flicker;
  their Colorlight material is about replacing the firmware with open gateware (q3k/chubby75).
- The Facebook "Colorlight Technical Support" group has posts on the subject (titles: "Ledvision 9.7
  doesn't have the 'netcard' option anymore", "Firmware for Colorlight 5a-75b?"); bodies not readable.

## 9. Source list

- https://github.com/FalconChristmas/fpp/issues/1849
- https://github.com/FalconChristmas/fpp/issues/2242
- https://github.com/FalconChristmas/fpp/issues/2420
- https://github.com/FalconChristmas/fpp/commit/d49ad41ed8 and /commit/306f0f6065cd25a32441ee4492576ace61ab799d
- https://github.com/FalconChristmas/fpp/blob/master/src/channeloutput/ColorLight-5a-75.cpp
- https://auschristmaslighting.com/threads/p5-panels-flickering.15417/
- https://auschristmaslighting.com/threads/gday-and-p4-panel.16642/
- https://auschristmaslighting.com/threads/p5-panel.16414/
- https://auschristmaslighting.com/threads/ledvision-p5-panels-scambled.16478/
- https://auschristmaslighting.com/threads/colourlight-card-and-ledvision.17017/
- https://falconchristmas.com/forum/index.php?topic=16375.0
- https://falconchristmas.com/forum/index.php?topic=15249.0
- https://falconchristmas.com/forum/index.php?topic=16742.0 (defective panels, not our case)
- https://www.youtube.com/watch?v=LcTKwyMmJec
- https://github.com/MoonModules/projectMM/blob/main/docs/how-to/panel-cards.md
- https://github.com/kostaman/LED_Matrix-1
- https://github.com/haraldkubota/colorlight/issues/4 and /issues/6
- https://github.com/q3k/chubby75/issues/94 and /issues/73
- https://hkubota.wordpress.com/2022/01/31/winter-project-colorlight-5a-75b-protocol/
- https://www.wiredwatts.com/colorlight-setup-for-outdoor-p5-panels
- https://wiredwatts.com/colorlight-5a-75b
- https://en.colorlightinside.com/product/download/745 , /product/download/383 , /service/download/?cat=959
- https://powerlight.ru/PDF/New23.05.23/5a-75e-specification-v8.2.2.pdf
- https://www.ledscreenparts.com/wp-content/uploads/2021/06/Colorlight-5A-75E-receiving-card-Specification-V8.0091586.pdf
- https://www.colorlitled.com/performance-settings-led-receiver-card/
- https://www.colorlitled.com/upgrade-firmware-colorlight-receiver-card/
- https://www.colorlitled.com/screen-flickering-troubleshooting/
- https://www.colorlight-led.com/new/colorlight-5a-product-series-software-parameters-setting.html
- https://www.colorlight-led.com/colorlight-problem-frequently-asked-questions/
- https://www.kernel.org/doc/Documentation/networking/e1000e.txt
- https://github.com/raspberrypi/linux/issues/4289 and /issues/6065
