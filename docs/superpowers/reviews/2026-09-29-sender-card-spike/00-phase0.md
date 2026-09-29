# Sender-card spike, phase 0: what the desk work found

2026-09-29, 17:14 to 17:49 CDT. Brief: `docs/superpowers/specs/2026-09-29-sender-card-spike.md`.
No packet was sent to the card. The run sheet for the wall is beside this file (`01-run-sheet.md`).

Labels: MEASURED (on a capture or on our machine, by a tool in `tools/sender_spike/`), SOURCE (someone else
says so), INFERENCE (my reading), UNKNOWN.

## 1. The short version

1. The S2's stream is fully described now. Beyond the brief's table there is one more thing in it: byte 37 of
   the sync is 1 in one sync about every 4.0 s. Everything else in the 13.5 s is constant. (MEASURED)
2. The capture cannot show a start of stream or a handshake. It begins in mid-stream, and all three captures
   of issue 1849 begin and end on a sync packet, which chance does not explain: they were trimmed. (MEASURED,
   INFERENCE)
3. INFERENCE: no receiver card was in the S2 capture. The PC stood where the receiver stands ("capture an
   incoming from the sender card"). So the capture shows what an S2 sends with nothing answering it, and it
   cannot answer "was the receiver on firmware 13".
4. Two of the brief's hypotheses have been tried by others, on a 5A-75B. Source type 0x00 with byte 36 = 0x00
   gave a picture on 13.13 and no change in flicker that the tester reported (cpinkham). The S2's exact
   packets from a computer gave no picture (mjunek), but that was sent in Falcon Player's old layout, one
   sync, everything in one burst, which gives no picture on 13.x with any header. So the failed replay says
   little about the header.
5. A new hypothesis, H10: **the doubled sync is the disturbance.** A PC-style sender needs two syncs on 13.x;
   the S2 sends one. If an S2-style sync is accepted once, the second sync is what a computer adds and a
   sender card does not.
6. The spike sender is built and tested (229 tests). With no flags its packets are the test sender's byte for
   byte; `--s2` sends the capture's sync byte for byte except the counter.
7. On the Omarchy box the loop's own clock holds the sync to 2 us (sd) with a sleep followed by a 2 ms
   busy-wait, against 57 us with `time.sleep` alone. What the queue and the driver add is not measured yet:
   that needs root and a link (section 7).

## 2. The field table, completed

Offsets count from the start of the Ethernet frame. "Ours" is the test sender, which is also `send.py` with no
flags. The last column is empty until phase 1: nothing here is measured on our card.

| Field | S2 (MEASURED on the capture) | PC, ours | What is known of its meaning | On our card |
|---|---|---|---|---|
| Length of the sync | 1036 | 112 | UNKNOWN. No source mentions the length | |
| Byte 13 | 0x00 | 0x07 | SOURCE (Falcon Player's header): "0x00 sent from S2 sender, 0x07 sent from PC/netcard". SOURCE (cpinkham, 13.13): "the 13.x receiver works both ways" | |
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
| Frame period | 16.579 ms (sd 0.22 ms as captured) | 16.667 | the sd is the capturing PC's, not the S2's | |
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
sync with no rows behind it. The two LEDVision captures also begin and end on a sync. A capture stopped at a
random moment ends in the idle time, behind a last row; three of three ending on a sync means the files were
cut to that shape by hand. Nothing can be read from the first or last packet.

**What is not in it.** Only types 0x01 and 0x55, 53,106 packets, none cut short. No detect, no reply, no
brightness packet, no packet from any other address.

## 4. What the two issues say about replaying the S2

Read in full: Falcon Player issues 1849 (37 comments) and 2242 (6), with 1911, 2420 and chubby75 94.

- **mjunek's replay** (1849): "Replicating the exact data in the Sender Card packet did not produce an
  output, it's likely packet timing related however." How is not recorded, but the date is: it was before
  the firmware-13 patch, when Falcon Player sent sync, brightness and rows in one `sendmmsg`, the sync first,
  once. That layout gives no picture on 13.x with the PC's own header either (the issue's first report, and
  our repo driver on our wall). INFERENCE: the replay failed for the layout, and the header was never tested
  in a layout that works.
- **cpinkham's test** (1849): "My current code also allows me to test with 0x01 packets with the next byte
  being 0x00 and byte offset 23 being 0x00 as sent by the S2 sender [...]. The 13.x receiver works both ways,
  so I don't think this is a PC vs S2 issue, I think it is something to do with the 0x01 packet timing."
  That is byte 13 and byte 36, in a 112-byte sync, sent twice, on 13.13, with 32x16 P10 panels. He did not
  test the counter, bytes 16 to 18, byte 26, bytes 31 and 32, the length, the row tail, or one sync alone.
  He saw no flicker on his panels with either header, so his test cannot say whether the header changes it.
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
| `tools/sender_spike/timing_matrix.py` | Step 6 as one command: 14 runs, one table |
| `tools/sender_spike/pcap_detail.py` | Section 3 of this file |
| `tests/sender_spike/` | 229 tests; no socket, no wall clock. They also hold every command of the run sheet |

What the tests hold:

- With no flags the sync, the brightness packet and the rows are `cl_fpp_test.py`'s, byte for byte.
- `--s2` is the capture's sync, byte for byte except the counter. The test reads the capture file itself where
  it exists (815 syncs compared) and a copy of its first 41 bytes elsewhere.
- Each flag changes the bytes it names and no others; each flag changes one variable of the plan.
- The safety rules of the brief, in the code:
  - Rule 1: every packet passes a guard that lets through types 0x01, 0x55 and 0x0A to the card's address,
    and nothing else. There is no code that builds any other packet.
  - Rule 2: every sync has its 64 rows. `--sync-reps` is 1 to 3.
  - Rule 3: when a plan leaves the fields by which the base sets the brightness (source type, byte 36, a
    sync level above the cap, no brightness packet), the pixels hold 25 or less. `--level-field-proven`
    lifts that, and only while every level byte is within 0.4; with the S2's own 0xff nothing lifts it.
  - Rule 4: a run is at most 60 s; rates are 15 to 240; the pictures are still bars or bars moving 8 pixels
    a second. Every run ends in black, after Ctrl-C too.
- Eight faults put into the code on purpose (the pixel cap, the guard, the level cap, the black tail, the
  tick grid, a sync byte, the jitter, the plan check) each made tests fail.

What the tests do not hold: the transmit stamps (`--stamp`, `--stamp-hw`) have run against a stand-in for the
socket only. The first run with a real socket is step 6, with the card out of the way.

Decisions taken while building, each open to the owner's veto:

- The default wait is a sleep followed by a busy-wait of the last 2 ms (`--wait hybrid`), not a busy-wait of
  the whole idle time (`--wait spin`), which holds a core at real-time priority and is throttled on a stock
  kernel such as the Pi's. `--wait sleep` is the old test sender's way.
- `--gap-ms` means what it means in `cl_fpp_test.py`: a pause after the last row. The layout with exact
  timing is `--order sync-rows`, where the sync sits on the tick.
- Runs that leave the base's brightness fields are dim (pixel 25). Their comparison is the base at
  `--pixel 25`, not the base.

## 7. Timing: what is measured and what is not

MEASURED on the Omarchy box at 17:43, the loop's own clock, no socket, plain scheduling, 60 frames a second,
600 frames each (`timing_matrix.py --dry-run`):

| Wait | sd of sync to sync | The interval furthest from 16.667 ms |
|---|---|---|
| `time.sleep` | 57 us | 164 us |
| sleep, then busy-wait 2 ms | 2 us | 22 us |
| busy-wait | 1 us | 17 us |

An earlier run of 10 s each gave 76, 1 and 10 us; the busy-wait lost one slice of 186 us to another task.

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
sudo .venv/bin/python tools/sender_spike/timing_matrix.py --iface enp5s0 --out timing-$(date +%F-%H%M)
```

## 8. The Omarchy box as found (read, not changed)

- `enp5s0`: up, 1000 Mb/s, driver e1000e, queue fq_codel. It sent 0 packets in 20 s while idle.
- Its address is `52:54:00:4c:ed:02`, not the port's own (`68:05:ca:c5:a7:2b`). INFERENCE: left from the VM's
  use of the port. It does not matter to the sender, which writes the source address itself.
- IPv6 is on for the port (a link-local address) and avahi is active. NetworkManager is active. The brief
  asks for IPv6 and avahi to be off for the port before a run; the run sheet has the commands. Every run of
  `send.py` prints how many packets the port sent that were not its own.
- The VM `ledvision` is shut off.
- `sched_rt_runtime_us` is 1000000: real-time tasks are not throttled on this box. The CPU governor is
  powersave. No core is isolated.
- `tcpdump` is not installed. The stamps replace it for timing. A capture of our own stream, for the record,
  would still need it or a listener.

## 9. Open after phase 0

- Step 6 of the brief, beyond the loop's clock (section 7).
- Whether the S2 sends anything that a PC's port does not deliver to a capture (frames with a bad checksum,
  idle patterns). Thacher's "saturates the link" hints at it. Only a sender card on the bench can say
  (phase 2).
- What byte 37 asks for.
