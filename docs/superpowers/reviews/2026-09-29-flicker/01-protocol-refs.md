# Lane 01: protocol reference implementations (Colorlight 5A-75, firmware 13.x)

Date: 2026-09-29. Read-only research. No packets were sent, no repo was changed.

Labels: **CONFIRMED** = primary source read by me, or a measurement I made on a primary artefact;
**LIKELY** = inference from confirmed facts; **SPECULATIVE** = a model that fits, not tested.
"SAYS" marks what a source states; "INFER" marks my reading.

Local copies of every source quoted are in
`/private/tmp/claude-502/-Users-trey-dev-codeisart/c21e091e-0747-4ded-93ce-703d319b2710/scratchpad/flicker/refs/`
(FPP files, issue text, the three packet captures, the other senders, my pcap tools in `refs/tools/`).

---

## 0. The short version

1. **The flicker is a known, unresolved property of firmware 13.x when a PC-style ("netcard") sender
   drives the card, LEDVision included.** FPP issue #2242 reports it on firmware **13.17** with a
   **64x32 1/8-scan outdoor P5** panel, after FPP's firmware-13 patch; 11.04 and 11.09 did not flicker
   on the same rig. FPP closed the issue as not fixable. A forum thread reports the same on a
   **5A-75E with a 2 x 2 P5 wall of 128x64**, which is our wall. (CONFIRMED that the reports exist;
   the cause is not established by anyone.)
2. **No open-source sender paces to 60 Hz on purpose, but the one hardware sender we have a capture
   of (Colorlight S2) sends 60.3 frames a second, one sync per frame, and is the only sender reported
   flicker-free on firmware 13.** LEDVision sent 25.00 fps in the one capture available. Our own
   measurement (steady at 60, flicker at 20 and 30) fits. (CONFIRMED rates; LIKELY link.)
3. **Every reference that works puts the idle time between the last row and the sync packet, not
   after the sync.** FPP, LEDVision and the S2 all send `sync, [brightness], rows, idle`. Our test
   sender sends `brightness, rows, sync, idle`, so its sync lands microseconds after the last row.
   Two independent authors document the bottom-row noise this causes and fix it with a delay
   (1 to 2 ms, and 5 to 10 ms). (CONFIRMED)
4. **The "LEDVision doubles every packet" finding, which FPP's firmware-13 code is built on, is at
   least partly a capture artefact.** In the capture attached to FPP #1849, Windows' own DHCP packets
   are doubled too, byte for byte, 13 to 24 microseconds apart. (CONFIRMED by my analysis.) FPP's
   author still found by experiment that 13.x needs the 0x01 packet twice.

---

## 1. Sources

| # | Source | Firmware it targets | Kind |
|---|--------|--------------------|------|
| S1 | FPP `src/channeloutput/ColorLight-5a-75.cpp` and `.h`, master, file last changed in `a1c10998ac` (2026-08-20). https://github.com/FalconChristmas/fpp/blob/master/src/channeloutput/ColorLight-5a-75.cpp | 2.x to 13.x, tested by author on 2.0, 3.60, 13.13 (5A-75B v6.x, v8.x) | C++ sender |
| S2 | FPP commit `d49ad41ed8` (2025-05-09) "ColorLight changes to support v13.x firmware"; `6b4377cdbe` (2025-05-12) forced-version setting; `5b9201737d` (2025-08-10) per-matrix setting | 13.x | history |
| S3 | FPP issue #1849 https://github.com/FalconChristmas/fpp/issues/1849 (2024-05-24 to 2025-05-21) | 13.17, 13.39 | discussion + 3 pcaps |
| S4 | FPP issue #2242 https://github.com/FalconChristmas/fpp/issues/2242 (2025-06-02, closed 2026-06-22) | 11.04, 11.09, 13.17, 13.39, 15.01 | test report |
| S5 | Packet captures attached to #1849: `5A75B 13v39.pcapng`, `5A75B 11v09.pcapng` (LEDVision on Windows 11), `S2 Sender.pcapng` (Colorlight S2 sender card) | 11.09, 13.39; S2 receiver firmware not stated | primary data |
| S6 | H. Kubota, protocol post https://hkubota.wordpress.com/2022/01/31/winter-project-colorlight-5a-75b-protocol/ and code https://github.com/haraldkubota/colorlight (`7ed37abc6c`) | **10.16** (5A-75B) | notes + Dart/Deno/Node senders |
| S7 | ZoidTechnology/PanelPlayer https://github.com/ZoidTechnology/PanelPlayer (`bba53f2f7e`, 2024-10-05) | not stated (5A-75B) | C sender + protocol notes |
| S8 | kostaman/LED_Matrix-1 (code by David Thacher) https://github.com/kostaman/LED_Matrix-1 (`4dc0ea3166`, 2022-02-26) | normal 11.09, PWM 8.75; 5A-75B **and 5A-75E** | C++ sender + notes |
| S9 | menull/colorlight-5a75b-protocol https://github.com/menull/colorlight-5a75b-protocol (`ac70486972`) | **13.39** (`04.0D.27`), 5A-75B | notes + Python sender |
| S10 | itoledo/ColorlightDemo https://github.com/itoledo/ColorlightDemo (`0a360b3d7e`, 2026-05-25) | not stated (5A-75B) | C# sender (Npcap) |
| S11 | mtlevine0/colorlightpy https://github.com/mtlevine0/colorlightpy (`ee8cc74709`) | not stated | Python sender (scapy) |
| S12 | asamonik/colorlight.rs https://github.com/asamonik/colorlight.rs (`ca388cb0b3`) | not stated | Rust library |
| S13 | mirisu/colorlight https://github.com/mirisu/colorlight (`22e9f4f55a`) | has a "v13 compat" flag copied from FPP | Rust sender |
| S14 | AusChristmasLighting thread "P5 Panels Flickering" https://auschristmaslighting.com/threads/p5-panels-flickering.15417/ | 13.x on 5A-75B v8.x; 5A-75E unstated | user reports |
| S15 | q3k/chubby75 issue #94 https://github.com/q3k/chubby75/issues/94 | 5A-75E v6.1 + 11.04 | user report |

Weight of the sources. S1 to S5 are the strongest: code in wide use, its author's test notes, and raw
captures. S6, S7 and S8 are careful individual work on older firmware. S9 is the only source that
claims to describe firmware 13 specifically, but it is a single commit with no stars, and one of its
claims contradicts FPP's behaviour (section 6.3); treat it as one person's bench notes. S13 copies FPP.
chubby75 itself documents the card's hardware and replacement gateware, not this protocol.

Not found: any OBS or GStreamer plugin, any Home Assistant or WLED project, that sends this protocol.
GitHub code search was rate-limited during the session, so the repository search (by name and
description) is what the list rests on. A sender that does not say "colorlight" in its name or
description would have been missed.

---

## 2. Question a: packet order per frame in FPP, and how FPP learns the firmware

### 2.1 What FPP sends (CONFIRMED, S1)

FPP builds two packet lists at `Init` and sends them from two different calls.

`m_msgs`, sent by `PrepData()` (S1 line 830, `SendMessages(m_msgs);`):

| firmware | contents, in order |
|---|---|
| below 13 | 0x0A brightness x1, then every 0x55 row packet |
| 13 and later | 0x0A brightness **x2**, then every 0x55 row packet (each row once) |

`m_syncMsgs`, sent by `SendData()` (S1 line 859, `SendMessages(m_syncMsgs);`):

| firmware | contents |
|---|---|
| below 13 | 0x01 sync x1 |
| 13 and later | 0x01 sync **x2** (same buffer twice) |

The code, S1 lines 513 to 515 and 543 to 550:

```cpp
if (m_highestFirmwareVersion >= 13) {
    packetCount += 1; // 0x0A brightness sent twice
}
...
if (m_highestFirmwareVersion >= 13) {
    // Send duplicate brightness packet
```

and S1 lines 629 to 635:

```cpp
if (m_highestFirmwareVersion >= 13) {
    m_syncMsgs.resize(2);
    m_synciovecs.resize(2);
} else {
    m_syncMsgs.resize(1);
```

Row doubling exists in the source but is compiled out (S1 lines 599 to 610, `#if 0`, comment
"LEDVision sends data rows duplicated as well, but doesn't seem necessary").

### 2.2 The order in time (CONFIRMED, S1 plus FPP's output thread)

`PrepData` and `SendData` are not called back to back. FPP's output loop
(`src/channeloutput/channeloutputthread.cpp`, lines 160 to 282) does, once per frame period:

1. `sequence->SendSequenceData()` -> `SendChannelData()` -> `SendData()`: **the sync for the frame
   prepared last time round** (line 188; `Sequence.cpp` line 937).
2. `sequence->ReadSequenceData()`: read the next frame (line 198).
3. `sequence->ProcessSequenceData()` -> `PrepareChannelData()` -> `PrepData()`: **brightness and rows
   of the next frame** (line 208; `Sequence.cpp` line 888).
4. Sleep for the rest of the period (lines 275 to 281, `outputThreadCond.wait_for`).

So on the wire FPP's cycle is:

```
sync(N) x2 | short gap (read + process) | brightness x2, rows(N+1) | idle to the end of the period | sync(N+1) x2 ...
```

The idle time sits between the rows and the sync. At FPP's default 20 fps that is close to 50 ms; at
40 fps close to 25 ms. The card gets the whole frame period to take in the rows before it is told to
show them. The author describes this design in S3: "Ideally we will send the 0x55 when we prep the
next frame of output in PrepData() and when it is time to display we only need to send the 0x01
packet to display the frame data we previously sent."

### 2.3 Before the firmware-13 patch (CONFIRMED, S2, parent of `d49ad41ed8`)

One list, one `sendmmsg` from `SendData`: `0x0101` (all-zero payload), `0x0AFF`, rows. Row header
ended `0x08 0x80`. This is the order that failed on 13.x in #1849 ("No output from FPP. Panel would
flash when enabling output, but no pixels illuminating", mjunek, 13.39).

INFER: our repo driver's order (sync, brightness, rows, once each) is this pre-patch order with the
newer bytes (0x0107, 0x05, 0x88). Its symptom on our wall ("the old frame stayed up and flashed
hard") matches the #1849 symptom. LIKELY the same failure.

### 2.4 How FPP learns the firmware (CONFIRMED, S1)

Both. Default is detection; a setting can force it.

- Global setting, S1 line 413: `m_highestFirmwareVersion = getSettingInt("ColorlightFirmwareVersion");`
- Per-matrix override, S1 lines 420 to 422: `config["firmwareVersion"]`.
- UI options (`www/co-ledPanels.php` lines 3835 to 3839): `Auto Detect` (0), `v2.x - v12.x` (2),
  `v13.x+` (13).
- If the value is 0, `GetReceiverInfo()` runs (S1 lines 482 to 489, 909 to 1057): it sends a 284-byte
  0x07 packet with the receiver index in byte 16, waits up to 300 ms for a broadcast 0x08 reply of more
  than 1000 bytes whose source MAC is 11:22:33:44:55:66, and reads `data[2]` (major) and `data[3]`
  (minor), data counted from byte 13. The highest major version seen decides the mode.
- FPP sends no acknowledgement after the reply. Kubota's notes (S6) and colorlight.rs (S12) send a
  third packet (0x07 with `data[2] = controller + 1`), which is what LEDVision does.
- Commit `6b4377cdbe` explains the forced setting: "to handle cases where the discovery does not work
  for some reason, for istance if the receivers are powered off when fppd is restarted."

Our senders do not detect and do not need to: one card, known firmware.

---

## 3. Question b: timing

### 3.1 FPP (CONFIRMED, S1)

- One `sendmmsg` per list, non-blocking. S1 line 849: `return sendmmsg(m_fd, msgs, msgCount, MSG_DONTWAIT);`
- No pacing between packets, no sleep between the brightness packet and the rows, no sleep between
  rows. The only sleep is a retry when the socket buffer is full, S1 lines 762 to 764:

```cpp
if (totalTime < 22) {
    // we'll keep trying for up to 22ms, but give the network stack some time to flush some buffers
    std::this_thread::sleep_for(std::chrono::microseconds(500));
```

- The gap between rows and sync is not a sleep in this file. It comes from the output thread calling
  `PrepData` early and `SendData` at the next tick (section 2.2).
- The output thread asks for real-time priority (`channeloutputthread.cpp` line 120,
  `SetThreadRealtimePriority(10)`), with the comment "Frame timing must stay consistent under load".
- FPP does not pace to 60 Hz. Its rate is the sequence's rate (`RefreshRate`, default 20;
  `channeloutputthread.cpp` lines 40 to 43, 319 to 323).

### 3.2 The bottom-row noise: two authors document it (CONFIRMED)

Kubota, firmware 10.16, 128x64, `colorlight.dart` lines 130 to 137 (S6):

```dart
// Without the following delay the end of the bottom row module flickers in the last line
if (wait) await Future.delayed(Duration(milliseconds: 1));
// Display frame
n = l2.send(src_mac, dest_mac, 0x0107, frameData0107, frame0107DataLength, flags);
```

`loadimg.dart` line 186 uses 2 ms. The Deno and Node libraries keep `await delay(1)`.

PanelPlayer, `protocol/readme.md` (S7): "Display the stored image. Sending frames faster than around
50 Hz results in stuttering. This packet should be delayed at least 5 ms after sending the last row
of image data." The code enforces 10 ms (`source/main.c`, `#define UPDATE_DELAY 10`, added in commit
`27e7cfd8` "Improve frame timing"):

```c
if (next - get_time() < UPDATE_DELAY)
{
    next = get_time() + UPDATE_DELAY;
}
await(next);
colorlight_send_update(colorlight, brightness, brightness, brightness);
```

INFER: this is our "noise on the last row or two at 60 fps, cleared by 1 ms". It is not new to
firmware 13 and not special to our card: the card needs time after the last row before the sync.
CONFIRMED as a documented behaviour; the mechanism inside the card is not documented anywhere.

Nobody reports that the delay "brings back a slight flicker", which is what we saw. Not confirmed by
any source. Note that PanelPlayer and FPP give the card far more than 1 ms (10 ms; the rest of the
period), and that our 1 ms test still placed the sync right after the rows rather than just before the
next frame's rows.

### 3.3 What the captures show (CONFIRMED, S5, my analysis with `refs/tools/frames.py`)

| capture | frame rate | packets per frame | order | idle gap, last row to next sync |
|---|---|---|---|---|
| LEDVision -> 13.39 | **25.00 fps** (period 40.000 ms mean, sd 0.81) | as captured: 0x01 x2, 0x0A x2, 32 rows x2 | sync, brightness, rows | 39.6 ms mean |
| LEDVision -> 11.09 | **25.00 fps** (39.997 ms, sd 0.74) | identical to the above | sync, brightness, rows | 39.6 ms mean |
| S2 sender card | **60.32 fps** (16.579 ms, sd 0.22) | 0x01 x1, 64 rows x1, **no 0x0A** | sync, rows | 16.4 ms mean |

All three bursts are short: the whole frame leaves in 0.2 to 0.4 ms, then the line is idle.
LEDVision's stream is byte-for-byte the same for 11.09 and 13.39: **LEDVision does not change its
protocol for firmware 13.**

The S2 capture was taken on the receiving side, so packets inside one burst share timestamps
(interrupt coalescing); only the frame period is reliable there.

### 3.4 Other senders (CONFIRMED by reading each)

| sender | order | gap before sync | pacing |
|---|---|---|---|
| Kubota (S6) | brightness x1, rows, sync x1 | 1 ms (2 ms in loadimg) | sleep; 50 fps in Dart, `delay(15)` in Deno |
| PanelPlayer (S7) | rows, sync x1; no 0x0A | at least 10 ms | sleeps to the source's frame time |
| Thacher (S8) | rows, then sync x1 and brightness x1 in one `sendmmsg` | none | 60 fps poll (`const int FPS = 60`), sends on change |
| menull (S9) | brightness x2, rows, sync x2 | none | `time.sleep(0.05)`, 20 fps |
| itoledo (S10) | brightness x2, rows x2, sync x3 | none (Npcap SendQueue) | sleeps to target fps |
| colorlightpy (S11) | brightness x1, rows, sync x1; at open: brightness, sync, brightness, sync | none | drift-compensated sleep, default 30 fps |
| colorlight.rs example (S12) | rows, sync x1 | none | `thread::sleep(Duration::from_millis(10))`, comment "sleep to avoid flickering" |
| mirisu (S13) | brightness, rows, sync; x2 for control packets with the v13 flag | none | sleep to fps |

Nobody uses kernel packet pacing (SO_MAX_PACING_RATE, tc) or SO_TXTIME. Only FPP and Thacher use
`sendmmsg`.

---

## 4. Question c: frame rate

### 4.1 What sources say

- Kubota (S6), firmware 10.16: "Default from LEDVISION software is using 20Hz. I can do about 60Hz but
  anything higher results in not-so-smooth animations (AKA skipped frames)." Deno code: "Less than 14ms
  won't be smooth".
- PanelPlayer (S7): "Sending frames faster than around 50 Hz results in stuttering."
- Thacher (S8), on PWM firmware with MBI5153 panels: "Changing images with Ethernet can cause small
  glitches randomly/periodically. LED panel current is very steady when Ethernet is not connected to
  receiver card. When receiver card is playing the same image over and over things work fine. [...]
  Further testing has shown this to be an async like issue. There are a few things which appear to be
  able to cause a glitch all have to do with frame rate. [...] S2 Sender Card was tested with MBI5153
  based panels using the same receiver card and configuration. No issues were detected with the sender
  card. [...] It is believe this is due to some kind of timing property which user space Linux is not
  able to achieve." He adds: "No issues have been found with non-PWM panels and non-PWM firmware"
  (that was 11.09).
- cpinkham (FPP author), S3, before his patch: "This could be why you see flicker, because FPP isn't
  sending this packet so the receiver has to time out before flushing the data to the outputs."
- menull (S9), firmware 13.39: "continuous sending of the full frame sequence causes visible
  brightness flickering because each 0x0101 swap produces a brief visual glitch." His fix for static
  content is to resend rows without a sync and to sync only when the picture changes.
- A reseller page on LEDVision's settings (secondary, not Colorlight's own):
  "The refresh multiplier determines how many times a single frame from the video source is refreshed
  on the LED screen", with the example 60 Hz x 32 = 1920 Hz.
  https://www.colorlitled.com/performance-settings-led-receiver-card/

### 4.2 What no source says

**Not confirmed:** that the card requires 50 or 60 Hz input. **Not confirmed:** what the card does
between frames when input is slower than its refresh. No source documents either. No open-source
sender resends the last frame to hold a 60 Hz cadence.

### 4.3 What the evidence supports (INFER)

- LIKELY: on firmware 13 each sync packet causes a short brightness disturbance, so the flicker
  frequency is the sender's frame rate. Supporting facts:
  - Our wall: flicker at 20 fps, some at 30, steady at 60 (CONTEXT, item 5).
  - Our phone video of LEDVision's stream: dips every 6 frames of a 30 fps video, 5 Hz. A 25 Hz event
    sampled at 30 Hz aliases to exactly 5 Hz, and 25.00 fps is LEDVision's rate in S5. A 20 Hz event
    would repeat every 3 frames, not 6. **This is the strongest single link between our measurement
    and a reference source.** It rests on LEDVision sending 25 fps in our VM too, which is not
    confirmed: nobody captured our LEDVision stream.
  - menull's statement above (13.39).
  - JWolf in S14 (13.x, 5A-75B v8.2): "When I am in LEDVISION, the flicker looks like the panel is
    turning on and off very fast [...] When I connect the 5A-75B receiver card to a Raspberry Pi
    running Falcon Player (FPP) the flicker is a lot less. But it is still there and noticeable. This
    feels like a more high frequency flicker." FPP at 40 fps against LEDVision at 25 would look like
    that.
- LIKELY: the S2 works because it sends 60 fps. mjunek, S3: "I have a sender card to now test with,
  and that is working perfectly." Whether that receiver ran 13.x is implied by the thread, not stated.
- SPECULATIVE: at 60 fps the disturbance is still there and is above the flicker-fusion rate, rather
  than absent. A camera test at 60 fps input would tell the two apart. This matters: if it is only
  hidden, a high-speed or rolling-shutter camera at the event will still see it.
- SPECULATIVE: the saved card timing (refresh 960 Hz, "Refresh x16") is 16 passes per 60 Hz input
  frame, and the card restarts or waits at each sync. The hardware log already proposes this. No source
  confirms it.

### 4.4 The firmware reports (CONFIRMED that they say this)

S4, gergmchairy, 5A-75B v8.2, Pi 4, **one outdoor P5 64x32 1/8 scan panel**, FPP 9.x master after the
patch:

- "Firmware 11.04 - works, no flicker"
- "11.09 - works, no flicker"
- "Firmware 13.17 - works, but has a noticable flicker"
- "Firmware 13.39 - works, but has a noticable flicker"
- "Firmware 15.01 - no output"
- "Yes, the same flicker is present in LEDVision v8.6 on Windows 11"

FPP's closing comment (darylc, 2026): "we don't have any developers willing to work on this and the
vendor has quite clearly indicated they are phasing out the mechanism that FPP uses. Additionally
numerous people have tried to work on this already in other issues and the windows software is
currently causing flicker when trying to use this same mechanism. Only recommendation we have us to
use a sender and take HDMI from FPP as a virtual matrix and plug the receivers into the sender."

cpinkham in the same issue: "I think I saw some flicker from v13.x firmware when sending the same
packets as the Colorlight software running on Windows, but don't recall it being present with the
current code in FPP." His panels were 32x16 P10.

S14:

- tcruise3 (2023-06-12), **5A-75E, 2 x 2 P5 panels, 128x64, LEDVision 8.8**: "the panels are
  constantly flickering [...] If I close the LEDVision program, the flickering stops." Three 5A-75E
  cards behaved the same; a 5A-75B did not flicker. Firmware versions not given.
- silver_ice (2023-07-29): "there is a known issue with the v13 firmware that comes on the v8.x
  version of the cards which causes the flicker when there is network IO."
- JWolf (2025-09-23): fixed by LEDUpgrade 4.0, "Preset firmware... --> normal-11.09" on a 5A-75B v8.2.

S3, mjunek: "LEDVision pie graph setup output would produce flicker and was also a bit lagged.
Downgraded to 11.04 firmware [...] issue disappeared."

**Caution on downgrading a 5A-75E.** Every downgrade report above is a 5A-75B. S15 reports a
5A-75E v6.1 that stopped being detected after `5A 11.04.fw` was installed ("the LED is solid green and
receiving cards are not displayed in the ledvision and ledupgrade software"). Thacher's repo (S8)
ships `normal-11.09.fw` and says it covers the 5A-75B and 5A-75E, without saying which board revision.
**Not confirmed:** that 11.04 or 11.09 is safe on our 5A-75E, or that it supports the ICN2018/3018
row decoder our panels need. We have one working card and one faulty one.

---

## 5. Question d: brightness

### 5.1 Fields (CONFIRMED in code; meaning from the sources named)

Offsets below are `data[n]` counted from byte 13 (FPP's convention). Kubota counts from byte 14, so
his numbers are one lower.

0x01 sync packet, 112 bytes:

| data[n] | PC / netcard | S2 sender (S5) | meaning |
|---|---|---|---|
| 0 | 0x07 | 0x00 | source type (FPP comment, S1 lines 31 to 32) |
| 1 | 0 | frame counter, 0 to 255 | cpinkham, S3; confirmed in S5 |
| 3..5 | 0 | ff ff ff | unknown |
| 13 | 0 | 0x01 | unknown |
| 18..19 | 0 | 0x01 0x3c | unknown |
| 22 | brightness | 0xff | overall brightness, **linear** (Kubota's table: 0x1a = 10 %, 0x40 = 25 %, 0x80 = 50 %) |
| 23 | 0x05 | 0x00 | Thacher: "Enables brightness settings? (Unstable if not set)" |
| 25..27 | brightness | ff ff ff | per-colour levels for colour temperature (Kubota: 2000 K at 100 % is ff 76 06). FPP's Wireshark dissector names them B, G, R; Kubota and PanelPlayer name them R, G, B. **Order not settled.** |

The S2's sync packet is 1036 bytes long, not 112.

0x0A brightness packet, 77 bytes: `data[0..2]` levels, `data[3]` 0xFF. FPP writes the same value to
all three. Kubota, Thacher and colorlightpy write two and then 0xFF in the third place (they count
from byte 14, where the first level byte is the second half of the EtherType), which is the same
bytes on the wire. Our senders match.

### 5.2 The two packets use different scales (CONFIRMED in two sources)

- Kubota (S6), 0x0A values "based on LEDVISION software": "1%=0x28, 2%=0x35, 5%=0x4d, 25%=0x92,
  50%=0xc1, 75%=0xe3, 100%=0xff".
- Thacher (S8), `Linux_NetCard.cpp` lines 98 to 102:

```cpp
b_raw = round(b / 100.0 * 255.0);                  // goes in the 0x01 packet
brightness = round(pow(b / 100.0, 0.405) * 255.0); // goes in the 0x0A packet
```

`255 * p^0.405` reproduces Kubota's table to within 1 (I computed: 1 % 0x27, 2 % 0x34, 5 % 0x4c,
25 % 0x91, 50 % 0xc1, 75 % 0xe3). So LEDVision sends a **linear** level in 0x01 and a
**gamma-encoded** level in 0x0A.

**FPP and both of our senders put the same linear byte in both packets.** At our 10 % that is 0x19 in
0x0A, which LEDVision's scale reads as about 0.3 %, against 0x64 (100) that LEDVision would send.
PanelPlayer notes the same thing: "Brightness values are non-linear."

### 5.3 Do they interact, and does 0x0A blink?

- cpinkham, S3: "The 0x0A brightness packet doesn't seem to be needed since brightness control appears
  to work fine with new/old firmware when set in the 0x01 packet." He tested "with/without the 0x0A
  brightness packet as well as doubling the 0x0A packet [...] it appears the only one that needs
  doubling on the 13.x firmware is the 0x01 packet."
- PanelPlayer: "This packet doesn't appear to be required." It never sends 0x0A.
- The S2 sender never sends 0x0A (S5, CONFIRMED).
- Thacher says the opposite for his firmware: the 0x01 level is "(Not used)" and 0x0A sets brightness.
- mjunek, S3: "By manipulating this value from 0x0A00 to 0xAFF you can adjust the brightness of the
  panel".
- FPP's header comment (S1 line 153): "Brightness may only work on newer firmware. Doesn't seem to
  work on v2.x and v3.x ColorLight FW."
- FPP developers advise setting brightness in the card with LEDVision, not from the sender (issue
  #1911, dkulp: "you REALLY want to set the brightness in LEDVision").

**Not confirmed:** which packet firmware 13.17 obeys, whether the two fight when they disagree, and
whether a 0x0A packet mid-stream causes a visible blink. No source reports a blink from 0x0A. Our own
test (23 % against 10 %, same flicker) says the level does not change the flicker; it does not say
which packet set the level.

SPECULATIVE: if 13.17 applies both, a sender that sends 0x0A = 0x19 and then 0x01 = 0x19 changes the
wall's brightness twice a frame. This cannot be the cause of LEDVision's flicker, because LEDVision's
two values agree with each other. It could add to ours.

---

## 6. Questions e and f, and the doubling question

### 6.1 Pixel order (question e)

- FPP sends what its configuration says: `m_colorOrder` defaults to RGB (S1 line 244), read from
  `config["colorOrder"]` (line 306) and per panel (lines 347 to 353). The byte order on the wire is
  the sender's choice. FPP's header says "RGB order pixel data" (line 150).
- Kubota: "Pixel format: BGR (for my panel)". PanelPlayer: "Image data in BGR order". menull, itoledo,
  colorlight.rs: BGR. colorlightpy sends RGB.
- CONFIRMED: most independent senders found BGR on a card LEDVision had configured. INFER: the card's
  configuration maps wire bytes to colour outputs (LEDVision's colour-exchange step), so both sides
  take part: the card config fixes the mapping, the sender must match it. LEDVision itself shows the
  right colours either way because it knows the mapping it wrote.
- Our measurement (R, G, B, W bars showed B, G, R, W) agrees with the majority. For our card: BGR.

### 6.2 Row packet size (question f)

- FPP: `#define CL_MAX_PIXL_PER_PACKET 497` (S1 header line 27). Rows wider than that are split with
  the pixel-offset field; the last packet of a row may be shorter (S1 lines 576 to 582). PanelPlayer
  and menull: 497. colorlightpy: 493.
- LEDVision sends one packet per row at the panel widths captured: 64 pixels (S5), and 256 pixels in
  itoledo's capture ("pixel=789" bytes). The S2 sends 128 pixels per packet for a 128x64 wall (S5),
  which is our geometry.
- No source gives a preferred size, and no source says splitting matters on firmware 13.
  **Not confirmed** either way.
- For us this is moot: at width 128 the repo driver (`CHUNK_PIXELS = 256`) and the test sender both
  send one 128-pixel packet per row, 405 bytes, the same as the S2.
- One difference in the S2's rows: the two header bytes after the pixel count are `00 00`, not
  `08 88` (S5, CONFIRMED). mjunek, S3: "On v13 firmware, the 0x0107 type packet was one thing that
  was needed to get it working, along with the 0x88 frame". Our senders use 0x88.

### 6.3 Is the doubling real? (CONFIRMED artefact in S5; the need for 2 x sync stands on experiment)

In `5A75B 13v39.pcapng` every Colorlight packet appears twice, which is where "LEDVision doubles
packets on firmware 13" comes from (mjunek and cpinkham, S3 and S4; FPP header lines 27 to 29, 133,
140). My analysis of the same file (`refs/tools`, output in my session):

- All 15,708 consecutive pairs are byte-identical, and the same is true of all 18,156 pairs in the
  **11.09** capture. LEDVision is not doing something different for firmware 13.
- The capturing PC's own packets are doubled as well: one DHCPv6 packet and three DHCP discovers, each
  present twice, byte-identical, **with the same IP identification** (0x2a57, 0x2a58, 0x2a59), 13 to
  24 microseconds apart. Windows does not send a DHCP discover twice with one IP ID.
- The S2 capture, taken on the receive path of the same PC, has no doubles.

INFER (LIKELY): the capture recorded each outgoing frame twice (a filter driver or virtual switch
under Npcap is the usual cause), and LEDVision sent each packet once. Not proven: a driver that really
transmits twice would look the same in the file.

itoledo's notes from a different capture say "3×Sync → 2×Brightness → 256 rows × 2 each". An odd count
cannot come from doubling alone, so LEDVision may send more than one sync. **Not confirmed**; I have
not seen that capture.

What stands regardless: cpinkham's bench result on 13.13 that one 0x01 per frame was not enough with
FPP's timing and two were, and menull's on 13.39 ("Single 0x0101 per frame instead of 2x: Flickering").
cpinkham also saw the cost on old firmware: "the old firmware flickers some when sending the two 0x01
packets", and suspected timing: "I'm also wondering whether the flicker with 13.x firmware is related
to this double-0x01 packet and the timing." Our own log has "sync x1 vs x2 not settled".

The S2 sends one sync per frame and no brightness packet, and is the sender reported to work.

### 6.4 Claims in S9 to treat with care

- "Sending a discover request puts the card in a state where it stops responding to pixel data. A
  power cycle is required". FPP sends a discover at every start on 13.x and then streams (S4's logs
  show detection followed by a picture). Contradicted for FPP's form of the packet. menull also sends
  the acknowledgement packet, FPP does not; that may be the difference. Not confirmed.
- "Continuous 0x0101 without pixel data: Card locks up, requires power cycle." Single source. Worth
  knowing before anyone tests sync-only keepalives.
- The double-buffer model (rows go to a back buffer, sync swaps). His own test contradicts the simple
  form of it: he sent green and a sync and saw the red from the previous test. What is supported is
  that **the card shows a frame one step late and needs a continuing stream to bring the last frame
  up**. That matches our observation that 3 black frames at 20 fps left a stale picture, and itoledo's
  habit of sending each frame twice "so both card buffers have the same data".

---

## 7. Question g: the diff table

Repo driver: `/Users/trey/dev/codeisart/show/display/colorlight.py`.
Test sender: `/Users/trey/dev/codeisart-ledvision/docs/superpowers/workflow/evidence/hardware/cl_fpp_test.py`.

| behaviour | FPP master (firmware 13 mode) | our repo driver | our working test sender |
|---|---|---|---|
| packet bytes | 0x01 with 0x07, 0x05; 0x0A; 0x55 with 08 88 | same, byte for byte (`colorlight.py:81-95`) | same (`cl_fpp_test.py:22-42`) |
| order on the wire, one cycle | `sync x2`, brightness x2, rows, **idle**, `sync x2` | `sync x1`, brightness (every 3rd push), rows, **idle** (`colorlight.py:126-133`) | brightness x2, rows, `sync x2`, **idle** (`cl_fpp_test.py:83-92`) |
| sync count per frame | 2 | 1 | 2 (1 with `--no-dup`, n with `--sync-reps`) |
| 0x0A count | 2, every frame | 1, every 3rd push (`BRIGHTNESS_EVERY = 3`, line 45) and on `set_brightness` | 2, every frame |
| gap, last row to sync | rest of the frame period (about 50 ms at 20 fps) | rest of the frame period, set by the caller | none; 1 ms with `--gap-ms 1` |
| gap, sync to first row | read + process time, short | none | rest of the frame period |
| frame a sync shows | the rows sent one period earlier | the rows sent by the previous push | the rows just sent |
| send call | `sendmmsg`, `MSG_DONTWAIT`, 500 us retry up to 22 ms | `socket.send` per packet, blocking | `socket.send` per packet, blocking |
| frame rate | sequence rate, default 20 fps; no 60 Hz pacing | caller's: show 20, arcade 30 | `--fps`, default 20; tested 20, 30, 60 |
| thread priority | real time (priority 10) | none | none; `--spin` busy-waits |
| firmware detection | 0x07 / 0x08, or a setting | none | none |
| brightness scale | same linear byte in 0x01 and 0x0A | same | same |
| pixel order | configurable, default RGB | RGB (docstring line 13) | raw bytes; the wall showed them as BGR |
| max pixels per row packet | 497 | 256 (`CHUNK_PIXELS`, line 40), equal chunks only | whole row, 128 |
| rows per packet at width 128 | 1 packet, 128 px | 1 packet, 128 px | 1 packet, 128 px |
| row doubling | no (compiled out) | no | no |
| end of stream | sends blanking data through the same path | caller sends black twice | 1 s of black at the stream rate |

For reference, the two vendor senders in S5:

| behaviour | LEDVision 8.x (PC) | S2 sender card |
|---|---|---|
| order | sync, brightness, rows, idle | sync, rows, idle |
| sync per frame | 1 LIKELY (2 in the file, see 6.3) | 1 |
| 0x0A | every frame | never |
| rate | 25.00 fps | 60.32 fps |
| sync packet | 112 bytes, 0x07, 0x05 | 1036 bytes, 0x00, frame counter |
| row header tail | 08 88 | 00 00 |

### Where our senders differ from what works

1. **Repo driver against FPP: the sync count and the brightness cadence, not the order.** Its cycle
   order is the same as FPP's and LEDVision's (sync first, idle after the rows). It sends one sync
   where FPP's firmware-13 mode sends two, and 0x0A every third push where FPP sends two every frame.
   It failed on the wall. LIKELY the single sync, on cpinkham's and menull's evidence. The repo
   driver's docstring claim that it matches FPP's loop is true of the order and no longer true of the
   counts.
2. **Test sender against FPP: the phase.** It has FPP's counts and puts the sync straight after the
   rows. That is the documented cause of bottom-row noise (section 3.2), and it is Kubota's layout,
   not FPP's. FPP, LEDVision and the S2 all leave the idle time before the sync.
3. **Both against the S2: the rate.** Neither holds 60 fps by itself; the show pushes 20 and the
   arcade 30.
4. **Both against LEDVision: the 0x0A scale.** Linear where LEDVision sends `255 * p^0.405`.

---

## 8. The three findings most likely to explain the flicker

1. **Firmware 13.x flickers with any sender that is not a 60 Hz sender card; the event rate is the
   sender's frame rate.** Reported on 13.17 with our panel type after FPP's patch (S4), with LEDVision
   itself (S3, S4, S14), and on a 5A-75E with a 128x64 P5 wall (S14). The S2 at 60.3 fps is the
   reference that works. Our 5 Hz camera beat fits LEDVision's 25 fps. Evidence: CONFIRMED reports,
   LIKELY mechanism. The references' two ways out are firmware 11.04 / 11.09 (5A-75B only in every
   report; unproven and risky on a 5A-75E) or a sender that holds 60 fps.
2. **Our test sender's sync is in the wrong place in the cycle.** Moving it to the start of the next
   tick (sync for frame N, then brightness and rows for N+1, then idle) matches FPP, LEDVision and the
   S2, gives the card about 16 ms after the rows at 60 fps, and should remove the bottom-row noise
   without the 1 ms pause that brought flicker back. CONFIRMED difference; the outcome on our card is
   untested.
3. **The sync count and the brightness packet are both unsettled on 13.17, and the references
   disagree.** FPP sends 2 syncs and 2 brightness packets; the S2 sends 1 sync and no brightness
   packet; LEDVision LIKELY sends 1 of each. Our 0x0A value is on the wrong scale if the card reads it
   the way LEDVision writes it. Candidates for one-variable tests at 60 fps in the FPP phase: sync x1
   against x2; 0x0A dropped; 0x0A sent as `round(255 * level ** 0.405)`.

---

## 9. What I could not confirm

- What the card does between frames when input is slower than its refresh. No source.
- That the card needs 50 or 60 Hz input. No source states it; the evidence is circumstantial.
- Whether the flicker is absent at 60 fps or only too fast to see.
- What LEDVision really puts on the wire per frame (1 or 2 of each packet), and its frame rate in our
  VM. A capture on the Omarchy host of the macvtap port would settle both. None exists.
- Whether the S2 capture's receiver ran firmware 13 (cpinkham asked in S3; no answer).
- Which brightness packet firmware 13.17 obeys, and whether 0x0A blinks the wall.
- The colour order of the three per-colour bytes in 0x01 and 0x0A (sources disagree).
- Whether splitting rows matters on firmware 13.
- Any source for the 5A-75E on 13.17 specifically, other than the forum report with no firmware
  version. Every FPP test was a 5A-75B.
- Whether firmware 11.x exists for our 5A-75E revision, keeps the ICN2018/3018 decoder setting, or
  can be installed without bricking the only good card.
- The PanelsRus video "Fix The Flicker on Colorlight 5A-75B v8.2 cards"
  (https://www.youtube.com/watch?v=LcTKwyMmJec): cited by three sources as the downgrade procedure; I
  did not watch it.
- The original mplayer-colorlight source (mylifesucks.de): the page holds only archives; not read.
- GitHub code search was rate-limited, so senders not named "colorlight" may have been missed.
