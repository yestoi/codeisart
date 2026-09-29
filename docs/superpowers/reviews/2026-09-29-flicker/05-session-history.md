# Lane 5: what our own session records say about the flicker

Mined 2026-09-29, 16:40 to 17:00 CDT. Read-only throughout: nothing was sent to the wall, no sudo, the VM was
not started, nothing was written in either repo or on the Omarchy box.

Labels: **CONFIRMED** (in a primary record or measured by us), **LIKELY**, **SPECULATIVE**.
Times: transcripts are in UTC (`Z`); `hardware.md` and the Omarchy journal are local (CDT = UTC - 5).
I give local time first and the transcript's UTC stamp in brackets.

## Sources read

| Source | What it is | Use |
|---|---|---|
| `~/.claude/projects/-Users-trey-dev-codeisart/446eb38e-...jsonl` (158 MB) | the card session, 2026-09-29 11:28 to 16:29 local | main source |
| `.../8d731703-...jsonl` (52 MB) | the morning card session, 07:35 to 11:26 local | no flicker remarks in it |
| `.../d1e01db2-...jsonl` (84 MB) | the arcade operator loop | its "flicker" hits are the software flash governor, not the wall |
| Omarchy: `~/.claude/projects/-home-trey-Work-windows-vm/340617f0-...jsonl` (42 MB) | VM build and the first wizard run, 2026-09-26 and 2026-09-28 evening | Windows adapter bindings, first power-up |
| Omarchy: `journalctl -b`, `ethtool`, `ip`, `tc`, `nmcli`, `virsh dumpxml` | the NIC and the VM as they are now | sections 6 and 7 |
| `git log -p ledvision-card1 -- .../hardware.md` | 4 commits, all 2026-09-29 | section 5 |

Other transcripts in the directory (177bc99d, 458616f0, 9fa65dce, b508d444, b5ce046f, d6d4645e, cb4b7812,
7be7b238 and the small ones) hold planning and software work only. No wall flicker in them.

Owner messages typed while the agent was working are stored as `queued_command` attachments, not as user
messages. Several of the owner's flicker remarks exist only there; a plain scan of user messages misses them.

Helper files (extracts of the transcripts, no images): `scratchpad/flicker/miner/`.

---

## 1. Timeline of every flicker-related experiment

All on 2026-09-29. "Owner" = the owner's eye at the wall.

### LEDVision in the VM

| # | Local (UTC) | Card, settings on the card | On the wall | Judge | Verdict |
|---|---|---|---|---|---|
| L0 | 11:56 (16:56:16Z) | card 1, wizard result: 138 decoding, 960 Hz, x16, DCLK 15.6 MHz, blanking 0, Level 1; no Receiver Mapping | the dim green pattern | owner | "Note the green grid is moving back and forth". Camera: a jump of exactly one column, 0 or +6 px |
| L1 | 12:58 (17:58:47Z) | card 1, same parameters, mapping now sent | Gray 128 fills, then Grid | owner | "It's slightly flickering fyi" |
| L1b | 13:01 (18:00:57Z) | same | static horizontal lines | laptop camera, 4 s, 120 frames | lit band 223, dips to 211 to 213 (about 5 %) in single frames; no horizontal shift in 120 frames |
| L2 | 13:18 (18:18:35Z) | card 2, same file sent | Grid, horizontal lines | owner | "Flickering still" |
| L3 | 13:54 (18:54:21Z) | card 2 after a power cycle, wizard from preset "14" (the agent recorded 420 Hz, x1, DCLK 17.9 MHz), decoders ICN2013 and 7258 being tried | the wizard's own test bands (Guide 3 to 7) | owner | "I'm noticing zero flickering this run." |
| L4 | 14:26 (19:26:57Z) | card 2, ICN2018, 960 Hz, x16, 15.6 MHz, blanking 3, Level 1 | Grid, then LEDVision's "LED1" program | owner | "There is some pretty bad flickering going on." |
| L5 | 14:28 (19:28:32Z) | refresh 420, x1, Level 1 (7 %). DCLK not stated for this step; L6 implies it was still 15.6 MHz | LED1 program | owner, 14:30 | "There is still flicker. You might need to record some video to see for yourself. The image shifts and fidges" |
| L5b | 14:32 (19:32:09Z) | same | LED1 program | laptop camera, 5 s, 150 frames | x shift max 0.11 px, y max 0.28 px (one LED is about 4 px); brightness 135.3 to 140.0, std 1.00 |
| L6 | 14:33 (19:33:38Z) | DCLK 15.6 -> 10.4 MHz; LEDVision moved refresh to 360; x1; Level put back to 1 | LED1 program | owner | "Same" |
| L7 | 14:34 (19:34:45Z) | Level 1 -> 3 (14 % at this timing, minimum OE 11.5 ns, the "Minimum OE is 0" warning gone) | LED1 program | owner, 14:35 | "Same" |
| L8 | 14:38 (19:38:35Z) | as L7: 360 Hz, x1, 10.4 MHz, Level 3 | LED1 program | owner's phone, IMG_5075.mov, 93 frames at 30 fps | whole wall 144 -> 132 (about 8 %) for one frame, at frames 0, 12, 18, 36, 42, 66 |
| L8b | 14:40 (19:40:46Z) | same | LED1 program | laptop camera, 8 s, 241 frames | median 144, 29 single-frame dips to about 140 (about 3 %), std 1.51 |
| L9 | 14:41 (19:41:24Z) | same; "Use Net Card" unticked, the card holds the last frame | LED1 frame, held | laptop camera 241 frames; owner | camera std 0.34, no dips. Owner, unprompted at 19:41:57Z: "Hey the image is stable now"; then answered "Gone" |
| L10 | 14:50 (19:50:28Z) | 960 Hz, x16, 15.6 MHz, blanking 3, Level 3 (23 %); stream stopped | Mandelbrot, held | laptop camera 181 frames; owner | std 0.45, no dips. Owner: "The screen moved a bit while we working on it, but everything is aligned and looks great." |

Notes on this table:

- **L3 is confounded (LIKELY).** The owner's "zero flickering" was seen on the wizard's test bands, not on a
  streamed picture. The agent put it down to the preset's timing. When the same timing family (420 Hz, x1) was
  used with a real picture (L5) the owner saw flicker again. So L3 fits "no flicker when no picture stream is
  being shown" at least as well as "no flicker at 420 / x1". Whether LEDVision sends its video stream during
  the wizard was never checked: not confirmed.
- **L8, the phone video that gives the "8 % dips", was taken at 360 Hz / x1 / 10.4 MHz / Level 3**, not at the
  saved 960 / x16 / 15.6. CONFIRMED by the order of events in the transcript (L6, L7, then the video).
- The flicker under LEDVision was reported at three different card timings (960/x16/15.6, 420/x1, 360/x1/10.4),
  at two brightness levels, and with both cards. CONFIRMED.
- No camera measurement exists of the streamed picture at the saved timing (960/x16). The only camera data at
  960/x16 while streaming is L1b (card 1, 138 decoding, blanking 0).

### The Linux senders (card 2, flash settings: 960 Hz, x16, 15.6 MHz, blanking 3, Level 3)

The exact commands are CONFIRMED twice: by the transcript and by the Omarchy journal's sudo lines.
No laptop camera was used in any of these runs (the laptop had been moved to its charger); one phone video.

| # | Local | Command (all `--iface enp5s0`) | Frames sent | Owner's verdict, in their words or the option they picked |
|---|---|---|---|---|
| S0 | 16:06:12 | `tools/wall_pattern.py rgb --seconds 60` (the repo driver; run by the owner) | not recorded | "The Mandelbrot stayed up and flashed pretty bad during the 30 secs." |
| S1 | 16:12:53 | `cl_fpp_test.py --seconds 10` (20 fps, brightness 25/255, brightness x2, sync x2, no gap) | 200 | "Bars, flashing" |
| S2 | 16:14:14 | `... --seconds 10 --brightness 0.23` (58/255, 20 fps) | 200 | "Same flashing"; kind: "Fast flicker" |
| S3 | 16:14:59 | `... --seconds 10 --fps 60` | 597 | "Steady now. However the last line or last two lines gives noise"; then "Rows"; where: "Bottom of the wall" |
| S4 | 16:16:02 | `... --seconds 10 --fps 60 --gap-ms 1` | 596 | noise: "Gone". Flicker was not asked for this run |
| S5 | 16:17:21 | `... --seconds 10 --fps 30 --gap-ms 1` | 300 | "Some flicker" |
| S6 | 16:18:08 | `... --seconds 20 --fps 60 --gap-ms 1` | 1192 | "Do it again, I'm going to send you a 3 sec video of the slight flickering I'm still seeing at 60fps" |
| S7 | 16:19:13 | `... --seconds 30 --fps 60 --gap-ms 1` | 1790 | phone video IMG_5080.mov; "Blue, green, red, white." After the run: "Top bars, bottom dark" |
| S8 | 16:22:54 | `... --seconds 10 --fps 60 --gap-ms 1 --sync-reps 1` | 596 | no verdict: "I need to compare the two to see if one is worse or not. I could've swore we got a stable image sometime during our testing just now and regressed since." After the run: "All color, blue, green, red, white" |
| S9 | 16:25:09, 16:25:24 | A: `--seconds 12 --fps 60 --tail-seconds 3`; B: `--seconds 12 --fps 60 --gap-ms 1 --tail-seconds 1` | 715, 716 | "Do it again" (both questions) |
| S10 | 16:25:59, 16:26:14 | A and B again, same commands | 716, 716 | "A steadier"; "Noise in A; black now" |
| S11 | 16:27:06, 16:27:21 | A as before; B: `... --gap-ms 1 --spin --tail-seconds 1` | 716, 720 | "A steadier"; "Clean; black now" |

Notes on this table:

- S7's phone video was analysed but the result was never told to the owner and is not in `hardware.md`.
  From the transcript's own per-frame list, frames 0 to 133 (the run itself): median 110, range 106 to 114,
  std 1.58; seven frames 3 to 4 below the median (frames 19, 37, 43, 48, 49, 57, 94), no rhythm I can see.
  No 8 % dips. The row-profile check found no rolling band (row deviation std 0.4 to 1.3). CONFIRMED from the
  recorded numbers; the phone's auto exposure is an uncontrolled factor.
- S3, the only run the owner called steady, was timed with `time.sleep` and ran at 59.7 fps (597 frames in
  10 s), not 60.0.
- The owner's "regressed" remark at 16:24 matches the record: the steady run was S3 (no gap) and every run
  from S4 to S8 had the 1 ms gap. CONFIRMED.

---

## 2. Send-loop variants: tried and not tried

The test sender changed four times during the session; only the last version is in the repo
(`hardware/cl_fpp_test.py`, sha256 `f12ad2bd...4462`, identical on the Omarchy box). No other variant of the
sender exists on the Omarchy box (`find ~ -name "cl_fpp*"` gives one file).

Versions: v1 (16:09) order brightness, rows, sync, all at once, frame period by `time.sleep`, ending with
3 black frames 50 ms apart. v2 (16:16) adds `--gap-ms`, a sleep between the last row and the sync.
v3 (16:22) adds `--sync-reps`. v4 (16:25) replaces the ending with `--tail-seconds` of black at `--fps`.
v5 (16:27) adds `--spin` (busy-wait) and moves to `perf_counter`.

### Tried

| Rate | Brightness pkts | Gap before sync | Sync pkts | Timing | Result |
|---|---|---|---|---|---|
| 20 fps | x2, 10 % | none | x2 | sleep | fast flicker |
| 20 fps | x2, 23 % | none | x2 | sleep | same fast flicker |
| 30 fps | x2 | 1 ms | x2 | sleep | some flicker |
| 60 fps (59.7) | x2 | none | x2 | sleep | steady; noise on the last 1 to 2 rows of the wall (reported twice: S3, S10; not asked in S11) |
| 60 fps | x2 | 1 ms | x2 | sleep | rows clean; "slight flickering"; less steady than no gap |
| 60.0 fps | x2 | 1 ms | x2 | busy-wait | rows clean; less steady than no gap |
| 60 fps | x2 | 1 ms | x1 | sleep | no verdict; stale bars left on the wall after the old ending |
| repo driver | every 3rd push, x1 | n/a | x1, sent first | driver's own | no picture; old frame flashed hard |

### Not tried (CONFIRMED absent from the transcript and from the journal's sudo lines)

- `--no-dup`: brightness x1 and sync x1. The flag exists and was never run.
- No brightness packet at all, or one brightness packet at the start only. The agent's own lead before the
  tests (19:57Z: "If 13.17 dips on brightness packets ... we'd see dips at that rhythm") was never tested.
- 30 fps without the gap, and 20 fps with the gap. The three rates were never compared on equal terms:
  20 had no gap, 30 had the gap, 60 had both.
- Any rate other than 20, 30, 60: nothing above 60, nothing between.
- Any gap other than 1 ms (0.1, 0.25, 0.5, 2 ms), a gap after the brightness packets, or rows spread evenly
  over the frame period instead of one burst.
- Busy-wait without a gap. In S11, A was sleep-timed at 59.7 fps and B was busy-wait at 60.0 fps with the gap:
  timing method, rate and gap all differ between the two.
- The driver's order (sync first, then rows) at 60 fps in the test sender. S0 and S1 differ in order,
  brightness cadence, rate, and the flash governor in front of the driver, all at once. Which of these made
  the driver fail is not known.
- A moving or changing picture. Every Linux run showed static bars. A static picture hides lost rows and
  half-updated frames; they only showed at the change to black (S7, S8).
- A different timing on the card (420 / x1, x8, another DCLK) with the Linux sender.
- A packet capture on `enp5s0`, of either sender. No `.pcap` exists on the Omarchy box.
- A camera measurement of S1 to S6 and S8 to S11.

---

## 3. The owner's words about the flicker

| Local (UTC) | Words | Context |
|---|---|---|
| 09-28 20:36 (01:36:45Z), Omarchy session | "There was a white flash on all panels when I plugged in." | first power-up of the wall |
| 11:56 (16:56:16Z) | "Note the green grid is moving back and forth" | L0 |
| 12:03 (17:03:44Z) | "Do a cycle of internet research to see what the problem might be. My own points to a hardware issue" | after L0 |
| 12:58 (17:58:47Z) | "It's slightly flickering fyi" | L1 |
| 13:07 (18:07:25Z) | "I do have a lot of otherthings plugged up in the extension block this wall is plugged into. I can put it on it's own extension block with nothing else if you think that could help?" | see section 4 |
| 13:18 (18:18:35Z) | "Flickering still" | L2 |
| 13:54 (18:54:21Z) | "I'm noticing zero flickering this run." | L3 |
| 13:58 (18:58:57Z) | "... using the option I mentioned that had no flickering during this run." | L3 |
| 14:26 (19:26:57Z) | "There is some pretty bad flickering going on." | L4 |
| 14:30 (19:30:41Z) | "There is still flicker. You might need to record some video to see for yourself. The image shifts and fidges" | L5 |
| 14:38 (19:38:35Z) | "Here's a short video you can process that captures the frames I'm talking about." | L8 |
| 14:41 (19:41:57Z) | "Hey the image is stable now" | L9, unprompted, about 30 s after the stream stopped |
| 14:56 (19:56:34Z) | "For the flickering, is this a symptom I will continue to have if I'm sending data to the color light card? Didn't we mention this is known defect in a particular firmware version" | |
| 16:07 (21:07:37Z) | "The Mandelbrot stayed up and flashed pretty bad during the 30 secs." | S0 |
| 16:14 (21:14:39Z) | picked "Fast flicker" (described as "Constant rapid flicker, like a bad fluorescent light") over "Irregular blinks", "Regular pulsing", "Parts flash" | S1, S2 |
| 16:15 (21:15:41Z) | "Steady now. However the last line or last two lines gives noise" | S3 |
| 16:19 (21:19:07Z) | "the slight flickering I'm still seeing at 60fps" | S6 |
| 16:24 (21:24:30Z) | "I could've swore we got a stable image sometime during our testing just now and regressed since." | S8 |

### Where the owner and the camera disagree

1. **Shift.** The owner: "The image shifts and fidges". The camera (L5b): no movement above 0.3 px in any
   panel or 16-row band, where one LED is about 4 px. The phone video (L8): whole-wall dimming, even across
   rows and columns (frame 12: every row band -3 to -17, every column band -7 to -14), no shift. CONFIRMED.
   The owner was never asked again whether "shifts" meant movement or a change in brightness.
2. **Kind of flicker.** Under LEDVision the cameras show separate single-frame dips, about 2 to 4 a second.
   Under the Linux sender at 20 fps the owner picked "Fast flicker", constant, and did not pick "Regular
   pulsing" or "Irregular blinks". These may be two different things. No camera data exists for the 20 fps runs.
3. **Size.** The phone saw 8 % dips, the laptop camera about 3 % for the same picture a few minutes apart.
   The owner called the 960/x16 case "pretty bad" and the first case "slightly". The cameras never measured a
   difference between those two.
4. Three questions put to the owner at 14:37 were never answered: whole wall or particular panels or rows;
   worse on white text or on colours; worse when the eyes move across the wall.

---

## 4. Noticed and dropped

| Item | What the record says | Status |
|---|---|---|
| Power strip | The owner offered to move the wall to its own strip (13:07). The agent: "Power might explain the slight flicker ... a good separate test later". Raised again at 13:19 and 14:37. | never tested |
| Card's green status LED | Agent asked twice (12:13, 12:44) for the blink rate: about 1 a second normal, about 10 a second in the wizard's test state (5A-75E spec V8.0). | never answered |
| Supply voltage and the "2.8V" silkscreen | Owner: "Power supply is 5v". The panel's plug sits on pads marked 2.8V with empty VCC pads. Agent: "treating that as low priority". | voltage at the panels never measured |
| Multimeter check of A, B, C | Owner: "I don't have time to pick up a multimeter" | not done; the decoder fix made it moot |
| Bench supply, heat | Nothing in any transcript about the supply's rating, its load, or temperature. | not recorded |
| Slow-motion video | Agent asked for 240 fps (14:37). The owner sent two normal 30 fps videos. | no high-speed video exists |
| LEDVision settings proposed and not tried | Refresh x8 (the vendor's advice), Display Mode "Refresh First" instead of "Gray-level First", a higher refresh rate at x1, more blanking; DCLK phase and duty ratio | not tried |
| "Minimum OE is 0" | LEDVision warns at Level 1. Gone at Level 3 at 360/x1 (minimum OE 11.5 ns). | whether Level 3 at the saved 960/x16 is clear of it was not recorded |
| Hidden resets | Any change of DCLK or Multiple resets Brightness Level to 8 and changes the refresh rate (x1 gave 60 Hz; 10.4 MHz gave 360 Hz). | recorded; caught each time before Send |
| Brightness percent moves with timing | Level 1 reads 10 %, 8 % and 7 %; Level 3 reads 31 %, 14 % and 23 %, depending on refresh and DCLK. | not explained |
| LEDVision forgets the adapter | Each time LED Screen Settings opens it falls back to the NAT adapter. At 14:50 the stream had already stopped for that reason before "Use Net Card" was unticked. | recorded in the README |
| 5A-75E flicker threads | Research at 12:11 found three 5A-75E cards flickering on P5 panels where a 5A-75B was clean (auschristmaslighting.com/threads/p5-panels-flickering.15417/), and v11 firmware "shifting" (threads/p4-panel-build.16141/page-2). Agent: "None of them looks like ours." | not followed up |
| Firmware | FPP issue 1849 and FPP's doubled brightness packet on firmware 13 and later. Agent: downgrade "stays a last resort". | not tried |
| "960 x16 = 60 x 16" | The agent's explanation of why 60 fps is steady. | inference; no source, no test |
| Stale picture at the end of a stream | 3 black frames 50 ms apart left "Top bars, bottom dark" (S7) and all bars (S8, sync x1). One second of black at 60 fps cleared it. | cause not found; "sync x1 vs x2 not settled" |
| One-column jitter | L0, card 1 only, before the mapping was sent. Gone once the mapping was sent (120 frames, no shift). | closed |
| The owner's terminal output from S0 | Asked for at 16:09, never given. | unknown |
| Card run time | LEDVision showed the card's run time: 0:42 at 13:44, 1:00 at 14:43, 1:08 at 14:51, all counting from the 13:43 power-on. | CONFIRMED: the card did not reboot during L3 to L10 |

---

## 5. Discrepancies between the records and `hardware.md` (and CONTEXT.md)

`git log -p` shows no flicker claim was ever rewritten: all of them were added in two commits the same day
(654c840 at 15:10, 4b36e13 at 16:28). The issues are compression, not revision.

1. **CONTEXT.md observation 2 joins two things.** "pretty bad flickering" was at 960/x16/15.6 (L4). The
   phone video with the 8 % dips was at 360/x1/10.4, Level 3 (L8). `hardware.md` has the order right but does
   not state the settings next to the video. CONFIRMED.
2. **"every 6 frames or a multiple of 6 (5 Hz at 30 fps)".** The dips are at frames 0, 12, 18, 36, 42, 66:
   six dips in 3.1 s, about 2 a second, all on a 6-frame grid. The agent later told the owner "a regular 5 Hz
   rhythm" and the skill says "~5 Hz". The grid is 0.2 s; the dips are not regular. CONFIRMED.
3. **"The laptop camera (8 s) sees the same rhythm smaller".** From the recorded list: 29 dips in 241 frames,
   gaps from 3 to 29 frames, 6 the most common (7 of 28). Same size of step, not the same rhythm. The laptop
   camera's frame timing was not checked. CONFIRMED.
4. **The three frame rates were not tested on equal terms.** `hardware.md` lists 20, 30 and 60 fps as one
   series. The 30 fps run had the 1 ms gap; the 20 fps runs did not. CONFIRMED.
5. **"60 fps: steady"** is the owner's verdict for one 10 s run at 59.7 fps (S3). For every later 60 fps run
   with the gap the owner reported slight flicker. `hardware.md` does say the gap "brought back a slight
   flicker". The A/B verdicts were "A steadier", not a statement that B flickers.
6. **"twice compared A/B".** Three A/B runs: the first got "Do it again", the next two "A steadier". The third
   changed the timing method and the rate as well as the gap.
7. **"(the saved timing, 960 Hz x16, is 60 x 16: the card repeats each frame 16 times and waits for the
   next)"** is written as fact in `hardware.md`, in the commit message and in the memory note. It is the
   agent's inference. Against it: LEDVision's stream flickered at 420/x1 and 360/x1 too.
8. **"The flicker is LEDVision's stream from the VM, not the card, panels or power."** What was shown: the
   card holds a frame steadily when no data arrives. That clears the panels' refresh and the supply at that
   load. It does not separate "the VM's stream is irregular" from "this card dims when packets arrive". The
   agent said so to the owner at 14:57 ("I can't tell which yet"); the log's heading is firmer than that.
9. **"The owner saw no flicker during these runs (preset timing ...)"**: see the note on L3. The observation
   is the owner's; the link to the timing is the agent's.
10. **S0 ran with `--seconds 60`** (journal); the owner wrote "during the 30 secs". Either the run was cut
    short or the time was estimated. Not confirmed which.
11. **S7's video analysis is missing from the log** (section 1).
12. **Status line of `hardware.md`** says the driver needs "a steady ~60 fps output". That rests on S1 to S6,
    with the limits in items 4, 5 and 7.

---

## 6. Other traffic on the wire

**No capture was ever taken, so what was on the wire during the tests is not confirmed.** What the records show:

1. **Host, now: silent (CONFIRMED).** Two readings of `ethtool -S enp5s0` 90 s apart (16:49:08 and 16:50:38),
   link up, no sender running: `tx_packets` 35391281 both times, `rx_packets` 164 both times.
2. **NetworkManager does not manage the port (CONFIRMED).** `/etc/NetworkManager/conf.d/90-ledvision-unmanaged.conf`:
   `unmanaged-devices=interface-name:enp5s0`; `nmcli`: `enp5s0:ethernet:unmanaged`. Before that file existed,
   NetworkManager ran DHCP on the port (journal, 2026-09-28 19:36:23 to 19:37:44). systemd-networkd, iwd and
   dhcpcd are inactive.
3. **The host's IPv6 stack is live on the port (CONFIRMED).** `ip addr`: `inet6 (the VM's link-local address, left out)/64`.
   That address is built from the VM's MAC ((the VM's MAC, left out)), which macvtap passthrough puts on the
   physical port while the VM runs; it stayed after the VM stopped. `sysctl`: `disable_ipv6 = 0`,
   `accept_ra = 1`, `router_solicitations = -1`. avahi-daemon is active and joined mDNS on the port
   (journal, 2026-09-28 19:40:55: "Joining mDNS multicast group on interface enp5s0.IPv6"; no later
   "Leaving"). So the host can put router solicitations, neighbour discovery, MLD and mDNS on the card's wire.
   From reading 1 the rate is low: none in 90 s. LIKELY a few packets at link-up and then long gaps.
4. **Windows in the VM had every protocol bound to the card's adapter (CONFIRMED for 2026-09-28 21:15).**
   `Get-NetAdapterBinding -Name LED-Card` in the Omarchy session: IPv4, IPv6, LLDP, Link-Layer Topology
   Discovery (both), Client for Microsoft Networks, File and Printer Sharing, QoS Packet Scheduler all
   `True`. No transcript holds a command that turns any of them off. So during every LEDVision test Windows
   could send DHCP, ARP, IPv6, LLMNR, NetBIOS, LLDP and the like to the card. How much: not confirmed.
5. **Counters (CONFIRMED).** Since boot (2026-09-28 19:05): `tx_packets` 35391281, of which `tx_multicast`
   35390646 and `tx_broadcast` 635; no unicast. The Colorlight address 11:22:33:44:55:66 has the group bit
   set, so picture packets count as multicast and cannot be told from other multicast. `rx_packets` 164, all
   broadcast, all counted as dropped by the host: the card does talk back (detection replies).
6. **The VM's macvtap is not attached now (CONFIRMED).** `virsh list --all`: `ledvision  shut off`;
   `ip -d link show type macvtap`: nothing. The domain still defines it:
   `<interface type='direct'> <source dev='enp5s0' mode='passthrough'/> <model type='e1000e'/>`.
   Journal: promiscuous mode entered 07:37:52, left 16:01:10; S0 began 16:06:12. LEDVision and the Linux
   sender never shared the port.

---

## 7. The NIC's state (Omarchy, read 16:44 to 16:51 local)

| Item | Value | Command |
|---|---|---|
| Kernel | 7.2.3-arch1-3 | `uname -r` |
| Driver | e1000e, version 7.2.3-arch1-3, firmware 1.8-0, bus 0000:05:00.0 | `ethtool -i enp5s0` |
| Link | 1000 Mb/s, full duplex, autonegotiation on; partner advertises 1000baseT/Full only, no pause | `ethtool enp5s0` |
| Flow control | RX off, TX off | `ethtool -a` |
| EEE | "Operation not supported" | `ethtool --show-eee` |
| Coalescing | rx-usecs 3; everything else n/a | `ethtool -c` |
| Rings | RX 256, TX 256 (max 4096) | `ethtool -g` |
| Offloads | TSO, GSO, GRO, checksums, scatter-gather all on | `ethtool -k` |
| Queue discipline | `fq_codel`, limit 10240p, flows 1024, quantum 1514; dropped 0, requeues 123, new_flow_count 120, maxpacket 405 | `tc -s -d qdisc show dev enp5s0` |
| Byte queue limit | limit 26298, inflight 0 | `/sys/class/net/enp5s0/queues/tx-0/byte_queue_limits/` |
| Errors | rx and tx errors 0, collisions 0, `tx_dropped` 10, `tx_timeout_count` 0, `tx_restart_queue` 0 | `ethtool -S` |
| Link changes | 28 since boot (14 up, 14 down) | `/sys/class/net/enp5s0/carrier_changes` |
| MAC | (the port's MAC, left out) (permanent); `addr_assign_type` 3 (it has been set by software) | `ethtool -P`, sysfs |
| Uptime | 21 h 39 min (boot 2026-09-28 19:05) | `uptime` |

`ethtool enp5s0` printed "netlink error: Operation not permitted" for one sub-query (it needs root) and gave
the rest. Nothing else needed root.

Findings:

1. **The link did not drop during any flicker test (CONFIRMED).** The journal has every "NIC Link is Down / Up".
   The last pair before the LEDVision flicker tests is 13:42:43 / 13:43:13; the next is 14:56:48 / 14:56:54,
   the owner's power-cycle test. Nothing between 14:56:54 and the end of the Linux tests at 16:27. Every link
   change matches a time the owner powered the wall off or on. The flicker is not link renegotiation.
2. **The byte queue limit is exactly one frame of the test sender (CONFIRMED arithmetic).**
   64 row packets x 405 bytes + 2 brightness x 77 + 2 sync x 112 = 25920 + 154 + 224 = 26298.
   LIKELY meaning: the whole frame, sync packets included, sat in the NIC's transmit queue at once, so the
   sender's packets leave back to back and the sync follows the last row by a few microseconds. That fits
   "noise on the last rows unless the sync is delayed". This is my inference from one number.
3. **Raw-socket packets pass through `fq_codel` (CONFIRMED that it is the root qdisc).** It sorts by flow, and
   the three packet kinds have different EtherTypes. If it ever held a backlog it could let a sync packet
   pass rows queued before it. The counters say a backlog was rare (120 new flows, 123 requeues in 35 million
   packets), so this cannot explain a steady fault. SPECULATIVE, low weight.
4. **The VM's card-side NIC is an emulated e1000e on macvtap, and its display is plain emulated VGA over VNC**
   (`virsh dumpxml`: `<model type='vga' vram='16384'>`, 4 vCPUs, no GPU). LEDVision captured a
   software-drawn screen and sent it through an emulated NIC. That supports uneven frame delivery from the
   VM as a cause of the LEDVision flicker. LIKELY, not measured.

---

## 8. Raw data that still exists (for re-analysis, no new test needed)

| File | What |
|---|---|
| `/Users/trey/.claude/uploads/446eb38e-8b4d-41f5-8566-409d1b269e36/e58aa0e9-IMG_5075.mov` | phone, LEDVision stream at 360/x1/10.4, Level 3 (L8) |
| `.../f3740607-IMG_5080.mov` | phone, Linux sender 60 fps with 1 ms gap, and the end of the run (S7) |
| `/Users/trey/dev/codeisart-ledvision/shots/vid-420x1.npy` | laptop camera, LEDVision at 420/x1 (L5b) |
| `.../shots/phone.npy`, `phone-al.npy`, `phone2.npy`, `phone2-al.npy` | the two phone videos as arrays, raw and aligned |
| `.../shots/rec-fpp.npz` | laptop camera, 90 s from 16:09:33; covers no test run |

`shots/` is git-ignored. The laptop recordings for L1b, L8b, L9 and L10 were not saved; only their per-frame
numbers are in the transcript.

---

## 9. What I could not confirm

- Whether LEDVision sends its picture stream while the wizard is open (bears on L3).
- LEDVision's frame rate and packet order on the wire. Never captured.
- The DCLK at L5 (the transcript gives refresh and multiple only).
- What `wall_pattern.py` printed in S0, its real frame rate, and whether the run lasted 30 or 60 s.
- The rating and load of the bench supply, and the voltage at the panels.
- The 2026-09-28 session has no flicker remark at all. The wizard's patterns were the only thing shown that
  evening, so this neither supports nor weakens anything.
