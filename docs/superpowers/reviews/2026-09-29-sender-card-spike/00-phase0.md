# Sender-card spike, phase 0: what the desk work found

2026-09-29, 17:14 to 19:11 CDT. Brief: `docs/superpowers/specs/2026-09-29-sender-card-spike.md`.
No packet was sent to the card. The run sheet for the wall is beside this file (`01-run-sheet.md`).

Labels: MEASURED (on a capture or on our machine, by a tool in `tools/sender_spike/`), SOURCE (someone else
says so), INFERENCE (my reading), UNKNOWN.

## 1. The short version

1. The S2's stream is fully described now. Beyond the brief's table there is one more thing in it: byte 37 of
   the sync is 1 in one sync about every 4.0 s. Everything else in the 13.5 s is constant. (MEASURED)
2. The capture cannot show a start of stream or a handshake: it begins in mid-stream (MEASURED). The files
   are whole: each holds every packet its port delivered while the capture ran (MEASURED; an earlier version
   of this document said they had been trimmed, which was wrong, section 3).
3. INFERENCE: no receiver card was in the S2 capture. The PC stood where the receiver stands (its maker:
   "it's the first time I tried to capture an incoming form the sender card"). So the capture shows what an
   S2 sends with nothing answering it, and it cannot answer "was the receiver on firmware 13".
4. Two of the brief's hypotheses have been tried by others, on a 5A-75B. Source type 0x00 with byte 36 = 0x00
   gave a picture on 13.13 (cpinkham, SOURCE). The S2's exact packets from a computer gave no picture
   (mjunek, SOURCE); how they were sent is not recorded, so the failed replay cannot be laid on the header
   or on the layout (section 4).
5. A new hypothesis, H10: **the doubled sync is the disturbance.** A PC-style sender needs two syncs on 13.x
   (cpinkham, menull); the S2 sends one (MEASURED). If an S2-style sync is accepted once, the second sync is
   what a computer adds and a sender card does not.
6. The spike sender is built and tested (320 tests). With no flags its packets are the test sender's byte for
   byte; `--s2` sends the capture's sync byte for byte except the counter.
7. On the Omarchy box the loop's own clock holds the sync to 2 us or better (sd) with a sleep followed by a
   2 ms busy-wait, against about 60 us with `time.sleep` alone. What the queue and the driver add is not
   measured yet: that needs root and a link (section 7).
8. A fresh review of the branch found no critical fault and six important ones; all are dealt with
   (section 10). Three questions are the owner's (section 9).
9. An adversarial review by three readers, asked for by the owner, found three things that would have made
   the end result false without anyone noticing, and corrected two statements of this document. All are
   dealt with (section 11). The weightiest: **this PC's queue can let the sync overtake the last rows of a
   frame**, which may be the "noise on the bottom rows" of 2026-09-29. Phase 1 now sends past the queue and
   tests the queue by itself.

## 2. The field table, completed

Offsets count from the start of the Ethernet frame. "Ours" is the test sender, which is also `send.py` with no
flags. The last column is empty until phase 1: nothing here is measured on our card.

| Field | S2 (MEASURED on the capture) | PC, ours | What is known of its meaning | On our card |
|---|---|---|---|---|
| Length of the sync | 1036 | 112 | UNKNOWN. No source mentions the length | |
| Byte 13 | 0x00 | 0x07 | SOURCE (Falcon Player's header, in my words): 0x00 is sent by the S2, 0x07 by a PC's network card. SOURCE (cpinkham, 13.13): "The 13.x receiver works both ways" | |
| Byte 14 | counts 0 to 255, +1 a frame, 817 steps of +1 in 817 | 0 | SOURCE (cpinkham): "what appears to be a 8-bit frame counter" | |
| Bytes 16 to 18 | ff ff ff | 0 | UNKNOWN | |
| Byte 19 | 0 | 0 | SOURCE (PanelPlayer, counting from byte 13: "offset 6"): "appears to be incremented by the receiving card". INFERENCE: a hop count along a chain of cards | |
| Byte 26 | 0x01 | 0 | UNKNOWN | |
| Bytes 31, 32 | 0x01 0x3c | 0 | UNKNOWN. 0x3c is 60; the brief's H3 | |
| Byte 35 | 0xff | the level | SOURCE (Kubota, Falcon Player, PanelPlayer): brightness, linear. SOURCE (Thacher, older firmware): "(Not used)" | |
| Byte 36 | 0x00 | 0x05 | SOURCE (Thacher): "Enables brightness settings? (Unstable if not set)". SOURCE (Kubota): "no idea what this is, but it's always 5" | |
| Byte 37 | 0, and 1 in 3 syncs of 818 | 0 | UNKNOWN. See section 3 | |
| Bytes 38 to 40 | ff ff ff | the level | SOURCE: the level of each colour. The order is not settled (Falcon Player's dissector: B, G, R; Kubota, PanelPlayer: R, G, B) | |
| Bytes 41 to the end | 0 | 0 | | |
| Brightness packet (0x0A) | none | 2 a frame | SOURCE (cpinkham, PanelPlayer): not needed. SOURCE (Thacher): it is what sets the brightness. Its scale is LEDVision's `255 * p^0.405`, not linear | |
| Row packet, bytes 12 to 18 | as ours | | type, row, offset, count | |
| Row packet, bytes 19, 20 | 00 00 | 08 88 | UNKNOWN. SOURCE (mjunek): 13.x needed 0x88 where older firmware took 0x80 | |
| Row packet, length and pixels | 405, 128 pixels | 405, 128 | | |
| Rows a frame, their order | 64, row 0 to 63, each once | the same | | |
| Source and destination | 22:22:33:44:55:66 to 11:22:33:44:55:66 | the same | | |
| Syncs a frame | 1 | 2 | SOURCE (cpinkham on 13.13, menull on 13.39): one is not enough from a computer | |
| Order | sync, rows, idle | brightness, rows, sync, idle | | |
| Frame period | 16.579 ms (sd 0.22 ms as captured) | 16.667 | The sd is the capturing PC's, not the S2's: it stamps a whole burst at once, up to 0.6 ms after the sync came. The S2's clock is steady over many frames; its jitter from frame to frame, below about 0.3 ms, cannot be read from this capture. So H1's premise, that a sender card's jitter is microseconds, is an assumption | |
| Other packet types | none | none | | |

## 3. The capture, in detail

Tool: `tools/sender_spike/pcap_detail.py`, run on the three captures of Falcon Player issue 1849.

**Byte 37.** It is 1 in the syncs of frames 101, 342 and 584 (counter values 34, 19 and 5) and 0 in the other
815. The marked syncs are 241 and 242 frames apart, 3.996 s and 4.012 s. 4 s is 241.3 frames, so this is a
timer of 4 s running beside the frame clock, not a count of frames. Nothing else changes with it: the picture
is the same, the rows are the same, the period before and after is ordinary. INFERENCE: a periodic request
or heartbeat from the sender, of the kind a receiver may answer. That puts it near the brief's safety rule 1
(nothing that reads the card), so `send.py` has no flag for it. The builder can make it
(`SyncSpec.mark37_every`), which is how the test compares against the capture.

**The rows.** Bytes 12 to 18 are what we send. Bytes 19 and 20 are 00 00. The addresses are ours. 64 rows a
frame, in rising order, each once. No difference beyond bytes 19 and 20.

**The picture** is one still picture for all 817 frames, pixel bytes from 133 to 214 (a piece of a desktop
background). So the capture says nothing about how the S2 behaves when the picture changes.

**Start and end.** The first packet is a sync with counter 189: the stream was running. The last packet is a
sync with no rows behind it. The two LEDVision captures also begin and end on a sync. CORRECTED after the
adversarial review: the files were not trimmed. Each ends with the capture program's statistics block:
packets received 53,106, 31,425 and 36,313, the numbers of packets in the files; dropped 0. Each capture
began 9.8, 5.3 and 2.4 ms before its first packet, less than a frame's period (MEASURED, by a reader of my
own and by the reviewer's). The line is idle 99 % of the time, so a capture nearly always begins in the idle
time and its first packet is a sync. SOURCE (the reviewer, from dumpcap's source): on Windows the capture
program looks for the stop after each packet, so a stop asked for in the idle time ends the file on the next
packet to come, a sync.

**What is not in it.** Only types 0x01 and 0x55, 53,106 packets, none cut short. No detect, no reply, no
brightness packet, no packet from any other address. Since the file is whole, this holds for everything
the port delivered in those 13.5 s. The PC sent nothing in that time. Byte 19 is 0, so no receiver stood
between the S2 and the PC; one beside it cannot be excluded.

**The pixels.** Each colour's values in the picture are neighbours (13, 14 and 19 values in a row), so the
S2 did not pass them through a table that spreads them, as a gamma table would (the reviewer's analysis).
The order of the colours cannot be read from the capture.

## 4. What the two issues say about replaying the S2

Read in full: Falcon Player issues 1849 (37 comments) and 2242 (6), with 1911, 2420 and chubby75 94.

- **mjunek's replay** (1849): "Replicating the exact data in the Sender Card packet did not produce an
  output, it's likely packet timing related however." How it was sent is not recorded. In the same comment he
  says his build with doubled packets gave a picture ("When testing with this from FPP, I could get an
  output, although insanely lagged"), so he had a layout that worked; whether the replay used it is not
  said. It was before the firmware-13 patch, when Falcon Player's own layout was sync, brightness and rows
  in one `sendmmsg`, the sync first, once: a layout that gives no picture on 13.x with the PC's header
  either (the issue's first report; our repo driver on our wall). INFERENCE, and no more than that: a
  replay that was exact also sent one sync a frame, and one sync from a computer is what cpinkham and menull
  found not to be enough. The replay does not tell the header from the count or from the layout.
- **cpinkham's test** (1849): "My current code also allows me to test with 0x01 packets with the next byte
  being 0x00 and byte offset 23 being 0x00 as sent by the S2 sender [...]. The 13.x receiver works both ways,
  so I don't think this is a PC vs S2 issue, I think it is something to do with the 0x01 packet timing."
  That is byte 13 and byte 36, in a 112-byte sync, sent twice, on 13.13, with 32x16 P10 panels. He did not
  test the counter, bytes 16 to 18, byte 26, bytes 31 and 32, the length, the row tail, or one sync alone.
  Of his patched build he says "I do not see flicker when driving newer 13.x firmware". INFERENCE: with no
  flicker to change, his test cannot say whether the header changes it.
- **cpinkham on the doubled sync**: "the old firmware flickers some when sending the two 0x01 packets", and
  "I'm also wondering whether the flicker with 13.x firmware is related to this double-0x01 packet and the
  timing." Nobody followed that up. It is H10.
- **Thacher** (the README of LED_Matrix-1), on PWM firmware: the S2 was clean where his Linux sender was
  not; "A slightly different protocol was used and some of these changes were evaluated. However the result
  still remains. It is believe this is due to some kind of timing property which user space Linux is not
  able to achieve." He also says the S2 "fully saturates the 1G link", which our capture does not show: its
  bursts last 0.22 ms of each 16.6 ms. His S2 may have been set for a larger screen. His answer was to
  build a hardware sender of his own. This is the strongest evidence for H1 and against a fix by bytes.
- **2242** adds nothing on the protocol. It is where 13.17 with a 64x32 P5 panel is reported to flicker
  under the patched Falcon Player, and LEDVision 8.6 too.
- **menull's warning about the sync before the rows** (his protocol notes, 13.39, a 5A-75B): his table of
  sequences that do not work has "`0x0101` before pixels (init-style) | Brief flash, then card stops
  responding", one line above the one that became the brief's safety rule 2. CORRECTED after the
  adversarial review: what "init-style" was is in his code (`menull-colorlight.py`, `enable_display`):
  fifty packets of type 0x0101, their payload all zero, 10 ms apart, with no rows between them. That is a
  stream of syncs without rows, the hazard of the brief's rule 2, which `send.py` cannot produce. It is not
  the S2's order, in which every sync is followed by its rows. MEASURED in our own record
  (`05-session-history.md`): the repo driver, which sends its sync first and once, ran on our card on
  2026-09-29 at 16:06; no picture; no power cycle followed (the link did not drop between 14:56 and 16:27);
  at 16:12 the test sender put bars on the wall. A sync-first stream has not locked our card. The run
  sheet asks for the owner's word before its first sync-first run all the same.

## 5. Hypotheses after phase 0

The brief's nine stand. Changes:

| # | Change |
|---|---|
| H2 | Byte 13 alone should give a picture (cpinkham). The open part is whether it changes the flicker, and what the rest of the header does |
| H5, H6, H7 | No source has tested any of them |
| H10 (new) | **Sync count.** One S2-style sync a frame against two; one PC-style sync against two. If the S2's header makes one sync enough and the wall is steadier with one, the doubled sync is the disturbance |
| Byte 37 | Not a hypothesis of the brief. Not to be sent without the owner's word |

## 6. What was built

| File | What it is |
|---|---|
| `tools/sender_spike/send.py` | The sender. `--help` lists the flags; one flag, one variable |
| `tools/sender_spike/timing_matrix.py` | Step 6 as one command: 16 runs, one table |
| `tools/sender_spike/pcap_detail.py` | Section 3 of this file |
| `tests/sender_spike/` | 320 tests; no socket, no wall clock. They also hold every command of the run sheet |

What the tests hold:

- With no flags the sync, the brightness packet and the rows are `cl_fpp_test.py`'s, byte for byte.
- `--s2` is the capture's sync, byte for byte except the counter. The test reads the capture file itself where
  it exists (all 818 syncs compared, the three with byte 37 set among them) and a copy of its first 41 bytes
  elsewhere.
- Each flag changes the bytes it names and no others; each flag changes one variable of the plan.
- The safety rules of the brief, in the code:
  - Rule 1: everything the loop is going to send passes a guard before the first packet goes: types 0x01,
    0x55 and 0x0A to the card's address, and nothing else. There is no code that builds any other packet.
    A field of a packet takes the values seen on the wire, and 0x011e for H3, and no other.
  - Rule 2: every sync has its 64 rows. `--sync-reps` is 1 to 3.
  - Rule 3: when a packet holds anything the base's does not (any field of the sync, its length, the row
    header), or no brightness packet is sent, the pixels hold 25 or less. `--level-field-proven` lifts that,
    and only while every level byte is within 0.4. A level above 0.4 goes out only in a sync with the S2's
    source type, and then nothing lifts the pixel cap.
  - Rule 4: a run is at most 60 s; rates are 15 to 240; the pictures are still bars or bars moving 8 pixels
    a second. A run that ends by itself or by one Ctrl-C ends in black. A run that ends by an error of the
    socket, a second Ctrl-C or a hangup does not: the card then holds the last frame.
- After a stall the frames do not come in a burst: a frame that is a period late moves the grid, and the
  report counts it ("slips").
- The log and the report are written to files before anything is printed, so a run stopped by Ctrl-C keeps
  its data when the pipe's reader is gone.
- Jitter holds the whole frame back, in either order, and opens no pause between the rows and the sync.
- The last row and the first sync of each frame are stamped, and the report counts the frames in which the
  sync left the driver before the last row. Each run reads the counters of the port's queue before and
  after, and says whether the queue held packets.
- Byte 37 is refused by the check itself, not only left without a flag.
- The run sheet's own helper text runs in bash, and a blind pair keeps its names and tells nothing.
- Twenty-one faults put into the code on purpose each made tests fail; four more (a guard taken away in one of
  several places) did not, which is why the guard is now one pass in one place.

What the tests do not hold: everything that needs a kernel. The raw socket, `PACKET_QDISC_BYPASS`, the
transmit stamps (`--stamp`, `--stamp-hw`) and the port's time stamp setting have run against a stand-in
only, and their constants and layouts were checked by reading, from memory of the Linux headers, by the
author and by the reviewer. The first run with a real socket is step 6, with the card out of the way; its
first row is the run sheet's own command.

Decisions taken while building, each open to the owner's veto:

- The default wait is a sleep followed by a busy-wait of the last 2 ms (`--wait hybrid`), not a busy-wait of
  the whole idle time (`--wait spin`), which holds a core at real-time priority and is throttled on a stock
  kernel such as the Pi's. `--wait sleep` is the old test sender's way.
- `--gap-ms` means what it means in `cl_fpp_test.py`: a pause after the last row. The layout with exact
  timing is `--order sync-rows`, where the sync sits on the tick.
- Runs whose packets hold anything the base's do not are dim (pixel 25). Their comparison is the base at
  `--pixel 25`, not the base.
- `--brightness` does not reach an S2-style sync, which carries its own level; `--sync-level` does.

## 7. Timing: what is measured and what is not

MEASURED on the Omarchy box, the loop's own clock, no socket, plain scheduling, 60 frames a second, 600
frames each (`timing_matrix.py --dry-run`). sd of sync to sync, and the interval furthest from 16.667 ms,
in microseconds:

| Wait | 17:30 | 17:43 | 18:19 (raw output kept in `timing-dry/`) |
|---|---|---|---|
| `time.sleep` | 76, 180 | 57, 164 | 56, 286 |
| sleep, then busy-wait 2 ms | 1, 17 | 2, 22 | 0, 1 |
| busy-wait | 10, 186 | 1, 17 | 15, 253 |

The busy-wait lost a slice of about 0.2 ms to another task in two runs of three; the sleep followed by a
busy-wait did not. The first two runs' raw output was not kept.

This is the clock the sender reads before it hands the packet over. It is not the wire. NOT MEASURED: the
same under `chrt -f 50`, what the port's queue (fq_codel) and the driver add, and what bypassing the queue
changes. The port (e1000e) can stamp packets with its own clock as they leave, which is as close to the
wire as this machine gets.

The rest of step 6 needs two things from the owner:

1. **Root** for the raw socket and for `chrt`: sudo for the session, or the owner runs the one command.
2. **A link without the card.** The brief says "the cable unplugged from the card or the card off". With no
   link the kernel drops the packets before the driver: there is then nothing to measure but the loop, and
   the runs that bypass the queue fail. So the wall's cable goes into another gigabit port for the
   measurement: a switch, or a laptop.

Then, on the Omarchy box, about 3 minutes:

```
cd ~/Work/codeisart-wall
sudo .venv/bin/python tools/sender_spike/timing_matrix.py --iface enp5s0 --card-unplugged \
    --out timing-$(date +%F-%H%M)
```

`--card-unplugged` is the owner's word that the cable is not in the card: twelve of the sixteen runs send
the sync before the rows, which the card has not seen yet. Without the flag the matrix does not start.

What the table has to say before phase 1 (the run sheet's gate): that the stamps and the bypass work
(first row); whether this port's queue lets the sync overtake the rows (the columns "order broken" and
"queue held" of the rows through the queue); and the port's worst interval, which decides which jitter
runs count. Where the busy-wait runs at real-time priority, stamps of the port may be missing: the driver
reads them in a task of ordinary priority, which the busy-wait holds off (the reviewer's reading of
e1000e; not measured).

## 8. The Omarchy box as found (read, not changed)

- `enp5s0`: up, 1000 Mb/s, driver e1000e, queue fq_codel. It sent 0 packets in 20 s while idle.
- Its address is `52:54:00:4c:ed:02`, not the port's own (`68:05:ca:c5:a7:2b`). INFERENCE: left from the VM's
  use of the port. It does not matter to the sender, which writes the source address itself.
- IPv6 is on for the port (a link-local address) and avahi is active. NetworkManager is active. The brief
  asks for IPv6 and avahi to be off for the port before a run; the run sheet has the commands. Every run of
  `send.py` prints how many packets the port sent that were not its own.
- The VM `ledvision` is shut off.
- The port's byte queue limit is 26298, one frame of the test sender to the byte. Its queue (fq_codel) has
  counted 123 requeues and 120 new flows, with a largest packet of 405 bytes, a row packet (read at 19:02).
  So this queue has held row packets. When, and in whose stream, the counters do not say.
- `sched_rt_runtime_us` is 1000000: real-time tasks are not throttled on this box. The CPU governor is
  powersave. No core is isolated.
- `tcpdump` is not installed. The stamps replace it for timing. A capture of our own stream, for the record,
  would still need it or a listener.

## 9. Questions that are the owner's

1. **Rule 3 against itself.** The brief lets an S2-style sync go out, which carries level 0xff, and says
   "never a level above 0.4". The sender allows 0xff only in a sync with the S2's source type, with dim
   pixels. Is that the rule?
2. **The sync before the rows** (section 4): the owner's word before B1. The one warning against it turned
   out to be about a stream of syncs without rows, which the sender cannot produce.
3. **Step 6:** root, and the wall's cable in another gigabit port (section 7).

Open after phase 0:

- Step 6 of the brief, beyond the loop's clock (section 7).
- Whether the S2 sends anything that a PC's port does not deliver to a capture (frames with a bad checksum,
  idle patterns). Thacher's "saturates the link" hints at it. Only a sender card on the bench can say
  (phase 2).
- What byte 37 asks for.

## 10. The review of the branch

A reviewer with no part in the work read the branch (9a0f5ef to f5d7dcb) against the brief. No critical
finding. What it found and what was done:

| Finding | Done |
|---|---|
| Ctrl-C can take `tee` with it; the report and the log were then lost | The files are written first; a broken pipe is survived; the run sheet uses `tee -i` |
| The stamps have never met a kernel, and the run sheet read as if they had | The sheet has a gate; the timing matrix starts with the sheet's own command |
| menull's warning about the sync before the rows was in neither document | Section 4 here; the owner's word in the run sheet; our own record added |
| mjunek's replay was read as fact | Section 4 rewritten; labelled |
| The dim base may be too dim to judge | A brighter dim base (A3b) in the run sheet |
| The cap on the sync's level could not fire, and C1 sent 1.0 against the letter of rule 3 | 0xff only with the S2's source type; C1 sends 0.4; question 1 above |
| Hex flags took values never seen on the wire | They take the values seen, and H3's |
| Unknown fields (bytes 16 to 18 and others) did not dim the picture | Anything the base's packets do not hold dims it |
| After a stall the frames came in a burst | The grid moves; "slips" are counted |
| `--gap-ms nan` passed the check | Refused |
| The guard inside the loop was held by no test | One pass in one place; a test; a fault put in on purpose is caught |
| The capture test read 300 syncs of 815 | It reads all 818 |
| "Every run ends in black" said too much; quotes not exact | Corrected |
| The run sheet: one name for three runs, H7's and H8's missing corners, A1 against A2 two variables | B9a to B9c, D6, C3, A1b |
| The timing numbers had no raw output | `timing-dry/` |

Left as they are, by decision:

- A tail of one frame in the sync-first order would not show black (the last rows get no sync). The tail is
  1 s, 60 frames.
- "N ours" in the line about the port's other traffic counts whole frames; after Ctrl-C it is off by the
  broken frame's packets.
- No test holds the Linux constants: a test that repeats a number proves nothing. Step 6 does.

## 11. The adversarial review

Asked for by the owner on 2026-09-29: three readers with no part in the work, each told to find what would
make the end result false, void or lost, or harm the card, and to leave the direction alone. Each finding
below was checked by the author before anything was changed.

**What would have made the end result false:**

| Finding | Checked how | Done |
|---|---|---|
| **The port's queue can let the sync overtake the last rows.** fq_codel sorts packets into flows by a hash that takes in bytes 12 and 13, so brightness, rows and sync are three flows. When the port's byte limit stops the queue in the middle of a frame, the rows wait; the syncs come as a new flow and are served after 4 more rows and before the rest. It touches every run in the base's order. It fits the "noise on the bottom rows at 60, gone with a pause of 1 ms" of 2026-09-29; that it is the cause is a suspicion | The mechanism: the reviewer read the kernel's source; the author went through the same path from memory of it, without the source at hand, and found no fault (the packet socket takes the protocol from the header; the hash starts at the protocol; new flows are served first; one quantum is 1514 bytes). On the box: the byte limit is one frame, the queue has counted 123 requeues and 120 new flows (section 8). How often it happens in our runs: not measured | Phase 1 sends past the queue (`--qdisc-bypass` in the helpers). One pair, A2 against A2q, tests the queue itself. Every run reports what the queue held and counts the frames whose sync left before their last row. Step 6 measures both without the card |
| **The jitter runs measured a pause.** In the base's order `--jitter-ms` held back the sync alone, which opened a random pause between rows and sync: 8 to 2000 us, mean 1094, at 2 ms. A pause of 1 ms there is on record as changing the flicker | Run by the author | The jitter holds the whole frame back in either order. A test holds the spacing of rows and sync equal with and without jitter |
| **The S2 batch could end in a false "no byte helps".** At 60 the base may already look steady, so nothing can look steadier. No run showed that flicker can be seen at the dim level at all. The S2-style runs carried level 255 against the dim base's 25, so "steadier" could have been "brighter" | By reading, and with `plan_from` | Two runs that are known to flicker (A4, A5). The comparison is made at a rate where the base flickers (`RATE`). Every rung has the dim base's light; the S2's own level is the last rung, read for brightness only |

**What would have weakened it:**

| Finding | Done |
|---|---|
| The gate before phase 1 asked that stamps appear, not what they say | The gate has three numbers; jitter runs below three times the port's worst are struck |
| No run was repeated; comparisons were from memory; the owner knew each variable | A control beside every batch; A2 repeated unannounced; the verdict before the variable; a helper for blind pairs |
| One check for what the card keeps, as the last run. The run without a brightness packet followed the run that set it to 0.4 | The base comes back after the first S2-style runs and around the guessed value; the run without a brightness packet follows a power cycle; the card is power-cycled after the session |
| H3's 0x011e is a guess sent to the only good card | Kept, fenced by the base before and after. INFERENCE: a field the S2 sends 60 times a second is not written to flash |
| Step 6 could have run with the card on the cable: twelve of its runs send the sync first | The matrix does not start without `--card-unplugged` |
| The check accepted byte 37 in a plan made without the command line | Refused |

**What this document had wrong:** the captures were not trimmed (section 3); menull's warning is about a
stream of syncs without rows (section 4); the S2's jitter is a bound, not a measurement (section 2).

**What held** under readers who tried to break it:

- Every byte and every timing figure of sections 2 and 3, re-derived with a reader written from the format's
  specification: the project's reader gave the same packets, bytes and stamps on all three files. The S2's
  rate is 60.3157 frames a second, within 13 parts in a million of VESA 800x600.
- The imitation: D1's stream against the capture, packet for packet, all equal but byte 37. The base
  against `cl_fpp_test.py`, all 68 packets of a frame.
- The quotes of section 4, word for word.
- The safety rules: 60,000 random flag combinations and 95 hostile plans, no violation through the command
  line.
- The unknown fields: no source reports a lock or a lasting change from any field of a sync packet;
  settings travel in other packet types, which the sender cannot build.
- EtherType 0x0100 at 1036 bytes: nothing in Linux's transmit path or in e1000e treats a frame by its
  length field; the port's own counter proves that the frames left.
- The socket path, by reading: every constant and layout; a full error queue drops stamps and never stops
  the sending.
- The rate runs: a card that free-runs gives 10 beats in 10 s at 59 and 61; the four cells of the table
  hold. The ladder: one variable a rung.
