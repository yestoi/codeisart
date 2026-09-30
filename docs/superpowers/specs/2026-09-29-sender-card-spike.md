# Spike: what does the sender card do that our Linux sender does not?

Written 2026-09-29 as the brief for a separate session. Branch `spike/sender-card`, worktree
`/Users/trey/dev/codeisart-sender-spike`. Owner: Trey.

To start the session:

```
cd /Users/trey/dev/codeisart-sender-spike && claude
> Read docs/superpowers/specs/2026-09-29-sender-card-spike.md and start the spike at phase 0.
```

## 1. The question

Our wall (four P5 panels, 128x64, one Colorlight 5A-75E on firmware 13.17) flickers while a computer's network
port feeds the card, and is steady when the card holds a frame. This is a known fault of firmware 13.x; Falcon
Player closed its issue unresolved and tells people to buy a sender card. Colorlight's own S2 sender card is the
one sender reported to drive a 13.x card without flicker.

**What does the sender card put on the wire that a computer does not, and can a Linux sender do the same?**

Nobody has published an answer. Two things make it worth a spike:

- A capture of an S2's output exists, for a 128x64 wall, our geometry.
- Our own measurement (60 frames a second was the one run the owner called steady) is a lead nobody else reports.

This is a spike: the product is knowledge and a recommendation, not driver code. The driver's repair ("route A")
goes ahead without waiting for it. Read `docs/superpowers/reviews/2026-09-29-flicker/00-path-forward.md` first,
then `01-protocol-refs.md` beside it; `hardware.md` (`docs/superpowers/workflow/evidence/`) is the record of the
wall, with a Corrections section at its top.

## 2. What is known (checked against the raw captures on 2026-09-29)

The captures are attachments of Falcon Player issue #1849, made by someone else on other hardware (a 5A-75B).
They are outside git, in `/Users/trey/dev/codeisart-sender-spike-refs/pcaps/`. The tools that read them are in
`tools/sender_spike/` (`pcap_summary.py`, `pcap_frames.py`, `pcap_seq.py`, `pcap_sync.py`); run them with
`/Users/trey/dev/codeisart/.venv/bin/python`.

Offsets count from the start of the Ethernet frame; the packet type is byte 12.

| | S2 sender card | LEDVision (PC) | our test sender | the repo driver |
|---|---|---|---|---|
| Frame rate | 60.32 (period 16.579 ms, sd 0.22) | 25.00 (sd 0.8 ms) | 20, 30, 60 tried | the content's: 20 or 30 |
| Cycle | sync, rows, idle 16.4 ms | sync, brightness, rows, idle | brightness x2, rows, sync x2, idle | sync, brightness every 3rd, rows, idle |
| Burst length | 0.22 ms (wire speed) | 0.37 ms | not measured | not measured |
| Sync packet length | **1036** | 112 | 112 | 112 |
| Byte 13 (source type) | **0x00** | 0x07 | 0x07 | 0x07 |
| Byte 14 | **a frame counter**, +1 each frame, 0 to 255 | 0 | 0 | 0 |
| Bytes 16 to 18 | **ff ff ff** | 0 | 0 | 0 |
| Byte 26 | **0x01** | 0 | 0 | 0 |
| Bytes 31, 32 | **0x01, 0x3c** | 0 | 0 | 0 |
| Byte 35 (brightness) | 0xff | 0xff | the level | the level |
| Byte 36 | **0x00** | 0x05 | 0x05 | 0x05 |
| Byte 37 | **takes two values** over the capture | 0 | 0 | 0 |
| Bytes 38 to 40 | ff ff ff | ff ff ff | the level | the level |
| Rest of the sync | zeros | zeros | zeros | zeros |
| Brightness packet (0x0A) | **none** | one a frame | two a frame | one every 3rd frame |
| Row packet | 405 bytes, 128 pixels | 213 bytes, 64 pixels | 405, 128 | 405, 128 |
| Row header, bytes 19 and 20 | **00 00** | 08 88 | 08 88 | 08 88 |
| Other packet types | none in 13.5 s | none | none | none |

Notes:

- The "every packet twice" seen in the LEDVision capture is probably how the capture was made (the PC's own DHCP
  packets are doubled in it, with the same IP ID), not what LEDVision sent. Falcon Player's author still found by
  experiment that firmware 13.13 needs two sync packets from a PC-style sender.
- The S2 capture was taken at the receiving end, so packets within one burst share time stamps. Only the frame
  period is good in it.
- 60.317 Hz is the refresh rate of VESA 800x600 at "60 Hz". INFERENCE: the S2 passes its HDMI source's frame
  timing through, so its sync is the source's vertical sync, made by an FPGA.
- Our wall shows raw pixels as BGR. The card's saved timing: refresh 960 Hz, "Refresh x16", DCLK 15.6 MHz,
  blanking 3, Brightness Level 3.

Counter-evidence to keep in mind:

- Falcon Player's mjunek replayed the sender card's exact packets from a computer and got **no output** ("it's
  likely packet timing related"). How it was replayed is not recorded. So a plain imitation may show nothing.
- Whether the receiver in the S2 capture ran firmware 13 was asked in the issue and never answered.
- One other project says a frame-rate change did not help on 13.x; it gives no numbers.
- Whether our wall at 60 frames a second is free of the disturbance, or only too fast for the eye, is not known.

## 3. Hypotheses, each with its test

Ranked by what the evidence supports. Each is one variable changed from **the base: the test sender that works**
(`docs/superpowers/workflow/evidence/hardware/cl_fpp_test.py`, 60 fps), which always gives a picture, so a run
that shows nothing is a result and not a dead end.

| # | Hypothesis | Test | If true |
|---|---|---|---|
| H1 | **Jitter.** The card locks its scan to the sync's arrival; the flicker is the phase error. An FPGA's jitter is microseconds, a sleeping Python's is a tenth of a millisecond or more | At 60 fps, busy-wait timing under `chrt -f`, add a known random delay to each sync: 0, 0.05, 0.1, 0.25, 0.5, 1, 2 ms | Flicker grows with the jitter. Gives the driver its budget, and says whether Python on a Pi can meet it |
| H2 | **Source type.** Byte 13 = 0x00 puts the card in its sender-card mode, where its scan follows the sync; 0x07 is a net-card mode that firmware 13 handles badly | The base with the S2's sync header, first byte 13 alone, then the whole header | A picture, and steadier, also at 30 and 20 fps |
| H3 | **Declared rate.** Bytes 31, 32 (0x01, 0x3c; 0x3c is 60) tell the card the frame rate | S2-style sync with 0x3c at 60 fps; with 0x1e at 30 fps; with 0x3c at 30 fps | 30 fps is steady when 30 is declared: the arcade needs no 60 Hz repeat. SPECULATIVE: 0x013c is also 316 |
| H4 | **Sync phase.** The sync belongs one idle period after the rows, as in every reference sender | The base with the sync moved: `--gap-ms 12` (exists), then sync first and rows right behind it | Bottom rows clean and steady together |
| H5 | **Frame counter.** The card uses byte 14 to tell a new frame from a repeat | Counting against constant, within the S2-style sync | A difference only when H2 holds |
| H6 | **Sync length.** 1036 bytes (8 microseconds on the wire) give the card time before the first row | 112 against 1036, same content | A difference in the top rows or in steadiness |
| H7 | **Row header.** 00 00 goes with source type 0x00, 08 88 with 0x07 | The four combinations | Some combinations show no picture: that maps the pairing |
| H8 | **The brightness packet disturbs the scan** | The base with no 0x0A at all, with one, with two | Steadier without. Watch the brightness: see the safety rules |
| H9 | **The rate band.** Any rate the card's timing divides evenly works, not only 60 | 50, 59, 60, 60.32, 61, 120 | A beat at 59 and 61 that is gone at 60: the card does not follow the sender, it free-runs |

H1 and H9 together say what kind of machine the card is: one that follows the sync (then jitter matters and the
rate is free), or one that free-runs at its own 60 Hz (then the rate must match and a beat appears when it does
not). That answer is worth more than any single byte.

## 4. Phases

### Phase 0: at the desk, no wall (one session)

1. Read the path forward, the protocol report, `hardware.md`'s Corrections and "15:40".
2. Finish the capture analysis: when byte 37 changes and to what; whether the S2's rows differ from ours beyond
   bytes 19 and 20; the S2's start of stream (is the capture's first packet the stream's first?); what the
   sources in `codeisart-sender-spike-refs/` say about each sync field (Falcon Player's Wireshark dissector
   `fpp-ColorLight_Wireshark.lua`, Kubota, `menull-COLORLIGHT_5A75B_PROTOCOL.md`).
3. Read Falcon Player issues #1849 and #2242 in full for how mjunek replayed the capture and what cpinkham
   tried with the 0x0100 sync (`fpp-issue-1849.txt`, `fpp-issue-2242.txt`; `gh issue view` for the rest).
4. Build `tools/sender_spike/send.py`: the test sender's loop with every row of section 3 as a flag, one
   variable a flag; busy-wait timing on `time.perf_counter_ns`; the jitter it adds logged; the interval between
   syncs measured and printed as a histogram at the end. It must build its packets through functions that a
   test can call without a socket.
5. Tests, without the wall and without the wall clock: each flag changes exactly the bytes it names; the
   S2-style sync is byte for byte the capture's except the counter; the default is byte for byte the test
   sender's.
6. Measure, on the Omarchy box with the cable unplugged from the card or the card off, what timing Linux really
   gives: sync-to-sync jitter with `time.sleep`, with busy-wait, with `chrt -f 50`, with the port's queue
   bypassed (`PACKET_QDISC_BYPASS`). This needs a raw socket: see section 6.
7. Write the run sheet for phase 1: the runs in order, the exact command of each, the three questions the owner
   answers after each. Put the runs that can tell most first; the owner's time at the wall is the scarce thing.

### Phase 1: at the wall, with the owner (one session, about an hour)

- Route A's runs come first (`00-path-forward.md`, section 5): they use the old test sender and settle
  questions this spike builds on. If both happen on one evening, the spike follows them.
- Film the control first: the card holding a picture, the phone at 240 fps with exposure locked.
- One variable a run, 10 s a run, A/B pairs played back to back where the verdict is close. After each run the
  owner says: a picture or none; flicker none, slight, some or fast; bottom rows clean or noisy.
- A phone video for every run that the owner calls steady, to tell "gone" from "too fast to see".
- Write each run into the report as it happens: the command, the frames sent, the measured jitter, the owner's
  words.

### Phase 2: only if a sender card is bought

The owner may order one as insurance (route C). If it comes:

- Capture its output with its port plugged straight into the Omarchy box: from power-on, with our wall's
  128x64 layout, at more than one source rate. This shows the handshake, if there is one, that the borrowed
  capture cannot.
- Put it on our wall. The claim that the S2 is clean on firmware 13 is one person's word about another card:
  check it on ours, with the same camera, before anything is built on it.

## 5. Safety rules

1. **Card 2 is the only good card.** Send only packet types 0x01, 0x55 and 0x0A. Nothing that reads or writes
   the card's settings, nothing from LEDVision's or LEDUpgrade's traffic, no firmware. A detect packet only in
   Falcon Player's exact form, only with the owner's word, and first on card 1 (which has a fault and holds
   factory settings): one source says a detect left its card dead until a power cycle.
2. **No stream of sync packets without rows.** One source says it locks the card until a power cycle.
3. **Brightness.** The S2's sync carries 0xff and no 0x0A packet follows it. Until a run has shown which field
   the card obeys, every picture sent with an S2-style sync uses pixel values of 25 or less, so that the wall is
   dim whatever the card does with the field. The old cap stays: never a level above 0.4.
4. **Flicker is what is being made on purpose.** Runs are 10 s, at low brightness, with the owner's word before
   each batch, and nobody else in front of the wall. No run strobes the picture itself: the pictures are
   static bars or a slow-moving one.
5. If the wall shows something that was not sent, or goes dark and stays dark, stop, tell the owner, and
   power-cycle before the next run.

## 6. Ground rules for the session

- Spike code lives in `tools/sender_spike/` and its tests in `tests/sender_spike/`. Do not change
  `show/`, `arcade/`, `tools/wall_pattern.py` or `cl_fpp_test.py`: the driver's repair is a separate, reviewed
  piece of work.
- Commit on `spike/sender-card` only. Never push. Never commit on `main` or `ledvision-card1`.
- No `cd` in a Bash call; use absolute paths and `git -C`.
- This worktree has no `.venv`: use `/Users/trey/dev/codeisart/.venv/bin/python` on the Mac.
- The wall hangs on the Omarchy box: `ssh omarchy`, port `enp5s0`, test tree `~/Work/codeisart-wall` with its
  own venv. Copy the spike's tools there with `rsync`; do not edit there.
- A raw socket needs root or CAP_NET_RAW. The session has neither: the owner runs the commands with sudo, or
  grants sudo for the session, or sets the capability on the venv's real python binary. Ask; do not work
  around it.
- `tcpdump` is not installed on the Omarchy box. Ask the owner to install it, or capture with a small
  AF_PACKET listener (also root).
- Before any run: the VM is off (`tools/ledvision/vm.py`), and nothing else sends on `enp5s0`. The host's IPv6
  and avahi were live on that port on 2026-09-29; ask the owner to turn them off for it.
- The captures and the copied sources in `codeisart-sender-spike-refs/` are other people's work: do not commit
  them. The repository is public.
- Write times from `date`, never from memory. Separate what was measured from what is inferred.

## 7. What the spike delivers

`docs/superpowers/reviews/<date>-sender-card-spike.md`:

- The field table of section 2, completed, each field marked measured on our card, from a source, or unknown.
- One row per run: the command, the measured jitter, the owner's verdict, the video's numbers.
- The answer to "what kind of machine is the card": follows the sync, or free-runs.
- A recommendation for the driver, as a list of changes each with the run that supports it, and the timing
  budget a sender has to meet. If the answer is "a Linux sender cannot do it", say so, with the evidence, and
  say what the sender card route costs the design.

Stop conditions: the report is written after phase 1 whatever it found. If no variable changes the flicker and
the jitter test shows no slope, the finding is that the cause is out of a sender's reach; that is a result.
