# Sender-card spike: what the S2 does that a computer does not, and what the card wants

2026-09-29. Phase 0 (the desk, 17:14 to 20:00) and phase 1 (the wall, 20:55 to 21:41) on one day. Owner: Trey,
at the wall, judging by eye. Brief: `docs/superpowers/specs/2026-09-29-sender-card-spike.md`. Phase 0's
findings, including the adversarial review and step 6's wire measurements, are in
`2026-09-29-sender-card-spike/00-phase0.md`; the run sheet in `01-run-sheet.md`; every run's output and the
owner's words as written down during the session in `2026-09-29-sender-card-spike/phase1/runs/`.

Labels: MEASURED (a number from the sender's logs or the port's clock), SEEN (the owner's verdict, quoted),
INFERENCE (my reading), UNKNOWN.

## 1. The answer

**A Linux sender can drive this card (Colorlight 5A-75E, firmware 13.17) without the flicker.** The S2 sender
card's special bytes are not what does it. Three things do, and our own packets serve:

1. **The order.** Send the sync first and the rows right behind it, so that the card has the whole frame
   period between the last row and the next sync. This alone turned the base from "bad" (flicker, noisy
   bottom rows) into "good, bottom row clean", at full brightness, with our header, two syncs and the
   brightness packets (N1 against N6; N7 against N8).
2. **The rate.** About 60 frames a second, and a little under rather than over. 59.00 was "our most stable
   presentation yet" and "super smooth" with a moving picture; 60.00 hitched or dipped a couple of times a
   half minute; 60.32 dipped every 3 to 6 s; 50 flickered and 55 once went black; 30 and 20 were "bad fast
   flickering" (N15b, N19, N11, S8b, N16 to N17, N9, N10).
3. **The timing.** The card follows the sync and notices when a frame is late by a quarter of a millisecond:
   jitter of 0.25 ms was "the slightest flicker, I can tell", 0.5 ms "I see jitter", 2 ms "bad" (N21, N20,
   N14). The sender used tonight held the sync to about 50 us at the port (MEASURED in step 6), and that
   was good enough.

**What kind of machine the card is:** it follows the sync, within limits. At 59 it waited for each frame
with no beat and no hitch; a card running on its own 60 Hz clock would have hitched once a second. It cannot
be driven faster than its own scan: at 60.32 it dropped a frame every 3 s or so (the drift between 60.32
and 60), at 60.00 now and then (the drift between two crystals). It will not hold a picture steady when
frames come much slower than its scan: 50 and below flicker, 30 and 20 badly. INFERENCE: the card scans at
its own 60 Hz and shows the newest frame it has; a frame that comes late, or not at all, means a scan of
the old one, which is what the flicker is. That fits every run of the night.

**The S2 imitated byte for byte** (sync first, one 1036-byte sync with the S2's header, no brightness packet,
the S2's row header, 60.32 frames a second, level 0xff) gave a picture the owner called "perfect", twice.
The same packets at 60.00 with our own level gave a picture too; next to our own packets in the same order
and at the same brightness they looked "about the same" (N7, N8). At 20 frames a second the S2's stream gave
**no picture at all**, four times of four, blind (P1, P2), where our own packets at 20 did. So the S2's bytes
are neither needed nor harmful at 60; at 20 the card refuses them. Which byte it refuses was not chased,
because the S2's bytes are not needed.

## 2. The field table, completed

| Field | S2 | Ours | On our card (this session) |
|---|---|---|---|
| Order | sync, rows, idle | rows, sync, idle | **The one that matters.** Sync first: clean bottom rows, most of the flicker gone (N6, N7). Rows first: noisy bottom rows and flicker at every rate (S1, N1, F1, L1b to L3b) |
| Rate | 60.32 | any | 59: steadiest. 60.00: a couple of dips a half minute. 60.32: a dip every 3 to 6 s. 55: once a picture, once black. 50: flicker. 30, 20: bad. With the S2's own bytes, 20: no picture |
| Syncs a frame | 1 | 2 | Either works in the sync-first order (N7 with two, N8 with one). In the rows-first order one was "even more jittery" than two (L3b against L2b) |
| Brightness packet (0x0A) | none | 2 a frame | Not needed: N8 and N4 had none and a picture. Whether it disturbs: not separated |
| Byte 13 (source type) | 0x00 | 0x07 | 0x00 alone in our layout: a picture, "stable, noise at the bottom" (L1b): no change |
| Byte 14 (counter), bytes 16 to 18, byte 26, bytes 31 and 32, byte 36 | the S2's | 0 | Together, in our layout and at level 0.1: a picture, "jittery" (L2b), worse than L1b. In the S2's layout at 60: as good as ours (N8) |
| Byte 35 and 38 to 40 (level) | 0xff | the level | 0xff (N4) and 25 (N5, N8) both give a picture in the S2's layout. Whether the card obeys the field: not compared for brightness (the owner was not asked in time) |
| Byte 37 | 1 every 4 s | 0 | Not sent |
| Length of the sync | 1036 | 112 | Both work (N8 against N7 has both changes at once with the rest of the S2's bytes; not separated) |
| Row header, bytes 19 and 20 | 00 00 | 08 88 | Both work; not separated from the other S2 bytes |
| The PC's queue | | | Sending past it: 0 reordered frames in every run. Through it, the old way at 20: 2 of 200 frames with the sync ahead of the last row, and the owner saw no difference (S2o) |

Not settled, and not needed for the driver: which single S2 byte the card refuses at 20 frames a second;
whether the brightness packet disturbs; which level field the card obeys; the S2's row header and sync length
on their own (H6, H7); H3 (the declared rate) and H5 (the counter).

## 3. The runs

Fifty runs, 20:55 to 21:41. Every run: the Omarchy box, port `enp5s0`, real-time priority 50, past the port's
queue, kernel stamps on the last row and the first sync of each frame, unless the table says otherwise.
"sd" and "worst" are the sync-to-sync interval as the driver took the packet, in microseconds, over the
run. "Order broken" (the sync leaving the driver before its last row) was 0 in every run but S2o (2 of
200). No run had a packet on the port that was not its own. The card was power-cycled before S1 and after
F1. The owner's words are as typed; a run that has "not reported" was overtaken by the next before a verdict
was asked for or given.

Runs P1 and P2 were played blind, four segments of 10 s in an order the box drew by lot, the owner told
only afterwards. The N runs were named to the owner before they played, at the owner's request.

| Run | Started | What it sent (all else the base) | Frames | sd, us | Worst, us | The owner's words |
|---|---|---|---|---|---|---|
| S1 | 20:55:15 | 60 fps; sync x2; bars, pixel 128 | 600 | 19 | 71 | picture; flicker slight/some; bottom rows noisy |
| S2 | 20:56:04 | 20 fps; sync x2; bars, pixel 128 | 200 | 99 | 753 | picture; flicker slight/some; bottom rows noisy |
| S2o | 20:57:12 | 20 fps; sync x2; bars, pixel 128; through the queue; plain priority; time.sleep | 200 | 71 | 387 | "looks the same" as S2; "hard to tell unless back to back" |
| P1_1 | 20:59:24 | 20 fps; sync x2; bars, pixel 25 | 200 | 15 | 58 | blind, order ABBA: two pictures seen, "stable with noise at the bottom", believed to be 1 and 4 |
| P1_2 | 20:59:35 | 20 fps; sync first; the S2's sync at level 25; sync x1; no 0x0A; row tail 00 00; bars, pixel 25 | 200 | 5 | 25 | nothing seen |
| P1_3 | 20:59:46 | 20 fps; sync first; the S2's sync at level 25; sync x1; no 0x0A; row tail 00 00; bars, pixel 25 | 200 | 8 | 51 | nothing seen |
| P1_4 | 20:59:57 | 20 fps; sync x2; bars, pixel 25 | 200 | 17 | 111 | a picture, as 1 |
| P2_1 | 21:04:52 | 20 fps; sync x2; bars, pixel 25 | 200 | 16 | 60 | blind, order ABAB: "1 good" |
| P2_2 | 21:05:03 | 20 fps; sync first; the S2's sync at level 25; sync x1; no 0x0A; row tail 00 00; bars, pixel 25 | 200 | 7 | 24 | "2 dark" |
| P2_3 | 21:05:14 | 20 fps; sync x2; bars, pixel 25 | 200 | 21 | 81 | "3 good" |
| P2_4 | 21:05:25 | 20 fps; sync first; the S2's sync at level 25; sync x1; no 0x0A; row tail 00 00; bars, pixel 25 | 200 | 7 | 42 | "4 dark" |
| S8 | 21:06:15 | 60.32 fps; sync first; the S2's sync (level 0xff); sync x1; no 0x0A; row tail 00 00; bars, pixel 25 | 603 | 20 | 345 | "The first one was perfect." |
| L1 | 21:06:26 | 60 fps; byte 13 = 00; sync x2; bars, pixel 25 | 600 | 11 | 80 | not reported ("I believe they did" show a picture) |
| L2 | 21:06:37 | 60 fps; the S2's sync at level 25; sync x2; bars, pixel 25 | 600 | 16 | 104 | not reported |
| L3 | 21:06:48 | 60 fps; the S2's sync at level 25; sync x1; bars, pixel 25 | 600 | 21 | 80 | not reported |
| S8b | 21:08:12 | 60.32 fps; sync first; the S2's sync (level 0xff); sync x1; no 0x0A; row tail 00 00; bars, pixel 25 | 1810 | 22 | 509 | "that might be a winner. There is still some flickering but it's on the very slight level where it happens across all panels simultaneously randomly every 3-6 seconds. Big improvement on before. No noise at the bottom. Full clear picture." |
| R1 | 21:10:36 | 60 fps; sync first; the S2's sync (level 0xff); sync x1; no 0x0A; row tail 00 00; bars, pixel 25 | 1200 | 36 | 878 | not reported (the owner was not counting) |
| R2 | 21:10:57 | 60.32 fps; sync first; the S2's sync (level 0xff); sync x1; no 0x0A; row tail 00 00; bars, pixel 25 | 1206 | 4 | 31 | not reported |
| R3 | 21:11:18 | 59 fps; sync first; the S2's sync (level 0xff); sync x1; no 0x0A; row tail 00 00; bars, pixel 25 | 1180 | 4 | 34 | not reported |
| L1b | 21:13:30 | 60 fps; byte 13 = 00; sync x2; bars, pixel 25 | 600 | 9 | 54 | "stable, noise at the bottom" |
| L2b | 21:13:41 | 60 fps; the S2's sync at level 25; sync x2; bars, pixel 25 | 600 | 24 | 293 | "jittery, noise at the bottom" |
| L3b | 21:13:52 | 60 fps; the S2's sync at level 25; sync x1; bars, pixel 25 | 600 | 21 | 95 | "even more jittery, noise at the bottom" |
| S1b | 21:14:46 | 60 fps; sync x2; bars, pixel 128 | 600 | 36 | 576 | not reported (a redo was asked for, one at a time) |
| B1 | 21:14:57 | 60 fps; sync first; sync x2; bars, pixel 128 | 600 | 5 | 45 | not reported |
| S7 | 21:15:08 | 60 fps; sync first; the S2's sync at level 25; sync x1; no 0x0A; row tail 00 00; bars, pixel 25 | 600 | 5 | 27 | not reported |
| N1 | 21:17:44 | 60 fps; sync x2; bars, pixel 128 | 600 | 13 | 98 | "bad" |
| N2 | 21:18:23 | 60 fps; sync first; sync x2; bars, pixel 128 | 600 | 5 | 34 | not reported ("next") |
| N3 | 21:19:04 | 60 fps; sync first; the S2's sync at level 25; sync x1; no 0x0A; row tail 00 00; bars, pixel 25 | 600 | 4 | 49 | not reported ("Do the next one") |
| N4 | 21:19:54 | 60.32 fps; sync first; the S2's sync (level 0xff); sync x1; no 0x0A; row tail 00 00; bars, pixel 25 | 603 | 5 | 26 | "That is the perfect one. No flickering, no noise." |
| N5 | 21:20:38 | 60 fps; sync first; the S2's sync at level 25; sync x1; no 0x0A; row tail 00 00; bars, pixel 25 | 600 | 4 | 19 | "it shown a picture" |
| N6 | 21:21:32 | 60 fps; sync first; sync x2; bars, pixel 128 | 600 | 4 | 23 | "It appears good. bottom row is clean." (N1 before it: bad) |
| N7 | 21:23:20 | 60 fps; sync first; sync x2; bars, pixel 128 | 600 | 3 | 15 | with N8, back to back: "Looks great. about the same." |
| N8 | 21:23:31 | 60 fps; sync first; the S2's sync at level 25; sync x1; no 0x0A; row tail 00 00; bars, pixel 128 | 600 | 3 | 15 | as N7 |
| N9 | 21:24:27 | 30 fps; sync first; sync x2; bars, pixel 128 | 300 | 6 | 39 | "both bad fast flickering" |
| N10 | 21:24:38 | 20 fps; sync first; sync x2; bars, pixel 128 | 200 | 7 | 27 | as N9 |
| N11 | 21:25:30 | 60 fps; sync first; sync x2; bars, pixel 128 | 1800 | 25 | 702 | dips: "a few, maybe a couple, but way better than before where it was every few seconds. Now it's very stable" |
| N12 | 21:27:36 | 60 fps; sync first; sync x2; scroll, pixel 128 | 1200 | 7 | 51 | "I did see slightly more jitterying there." "Lets have more movement." |
| N13 | 21:29:09 | 60 fps; sync first; sync x2; scroll at 32 px/s, pixel 128 | 1200 | 3 | 26 | "Do it again." |
| N13b | 21:30:22 | 60 fps; sync first; sync x2; scroll at 32 px/s, pixel 128 | 1200 | 26 | 611 | "Is it supposed to be smooth? I saw two transitions." |
| N14 | 21:31:56 | 60 fps; sync first; jitter to 2 ms; sync x2; bars, pixel 128 | 1200 | 800 | 1947 | "Bad jitter/flicker." |
| N15 | 21:33:10 | 59 fps; sync first; sync x2; bars, pixel 128 | 885 | 4 | 29 | "Do it again and for longer." |
| N15b | 21:33:57 | 59 fps; sync first; sync x2; bars, pixel 128 | 1770 | 26 | 746 | "I think this is our most stable presentation yet." |
| N16 | 21:35:02 | 55 fps; sync first; sync x2; bars, pixel 128 | 825 | 6 | 44 | with N17 back to back: "I saw flicker at 50. Do 55 again." |
| N17 | 21:35:18 | 50 fps; sync first; sync x2; bars, pixel 128 | 750 | 16 | 309 | flicker |
| N16b | 21:36:02 | 55 fps; sync first; sync x2; bars, pixel 128 | 1100 | 25 | 444 | "I actually saw just a black screen that time." |
| N18 | 21:38:00 | 60 fps; sync x2; bars, pixel 128 | 300 | 20 | 52 | "wall showed bars": the card answers |
| N19 | 21:38:46 | 59 fps; sync first; sync x2; scroll at 32 px/s, pixel 128 | 1180 | 4 | 37 | "Super smooth" |
| N20 | 21:39:07 | 59 fps; sync first; jitter to 0.5 ms; sync x2; bars, pixel 128 | 885 | 203 | 488 | "I see jitter." |
| N21 | 21:39:53 | 59 fps; sync first; jitter to 0.25 ms; sync x2; bars, pixel 128 | 885 | 102 | 241 | "Just the slightest flicker. I can tell." |
| F1 | 21:40:26 | 60 fps; sync x2; bars, pixel 128 | 600 | 19 | 84 | "yes": as S1 at the start |

## 4. What the runs say, run by run

- **The base is bad, and the same at 60 and 20** (S1, S2, N1, F1): "slight/some" flicker, noisy bottom rows,
  at 60 as at 20. The afternoon's "fast flicker" at 20 was not seen again tonight; the card had been
  power-cycled. The base looked the same whether sent our exact way or the old sender's way (S2o), so at this
  level the sender's roughness (sd 71 us, 2 reordered frames) does not show.
- **Dim hides the flicker** (P1, P2): the base at pixel 25 was "stable" where at pixel 128 it flickers. The
  eye cannot judge flicker at that level. Every flicker verdict below is at pixel 128, except where a
  picture-or-none question was all that was asked.
- **The S2's stream at 20: no picture, four of four, blind** (P1, P2). At 60.00 with our level: a picture
  (N3, N5). At 60.32 with its level: a picture (S8, N4). The rate is what the card refused, not the level.
- **The S2's stream at 60.32 is "perfect"** (S8, N4), with dips every 3 to 6 s over 30 s (S8b). With our own
  packets in the S2's order, at the same brightness, "about the same" (N7, N8): the bytes add nothing.
- **The order is the thing** (N1 "bad", then N6 "appears good, bottom row clean", the one change being the
  sync first). The rows-first order with the S2's header is worse, not better (L1b, L2b, L3b).
- **Rates** (N9, N10, N11, N15, N15b, N16, N16b, N17, S8b, N13b): 30 and 20 "bad fast flickering"; 50
  flicker; 55 a picture once and black once (see section 6); 59 "our most stable presentation yet"; 60.00 a
  couple of dips a half minute and two hitches in 20 s of movement; 60.32 a dip every 3 to 6 s.
- **Movement** (N12, N13, N13b, N19): at 60.00 the moving bars hitched twice in 20 s; at 59 they were "super
  smooth". The sender's timing was as good in both (worst 26 and 37 us in N13 and N19). The hitches are
  the card's dropped frames.
- **Jitter** (N14, N20, N21): 2 ms "bad", 0.5 ms "I see jitter", 0.25 ms "just the slightest flicker, I can
  tell". All at the steady rate 59, sync first. The card follows the sync closely enough that a quarter of
  a millisecond shows. The sender held the sync to 15 to 50 us in the good runs (MEASURED at the driver;
  at the port it was 52 us worst in step 6).
- **The card came back as it was** (N18 after the black run, F1 at the end): the base looked as at the start.

## 5. What the driver should do, and the runs that say so

For `show/display/colorlight.py`, the shared driver of the show and the arcade (route A of
`docs/superpowers/reviews/2026-09-29-flicker/00-path-forward.md`, section 6). Each change with the runs
that support it:

| Change | Runs |
|---|---|
| **Send the sync first, then the brightness packets, then the rows, then idle** until the next tick. The sync shows the rows sent one tick earlier. This is Falcon Player's order too | N1 against N6; N7 |
| **Send at a steady 59 frames a second**, whatever the content's rate, repeating the last frame. Not 60: our clock and the card's drift past each other and a frame is dropped every half minute or so. Not 60.32. Not 30 or 20: fast flicker. INFERENCE: the safe band is a little under the card's own 60; 58 was not tried; 55 flickered or blanked | N15b, N19 against N13b, N11, S8b, N9, N10, N16, N16b, N17 |
| **Hold the sync to 100 us or better**, by the port's clock. 250 us of jitter shows. The sender that did it tonight: real-time priority (`chrt -f 50`), a sleep to 2 ms before the tick then a busy-wait, absolute deadlines on `perf_counter_ns`, packets past the queue (`PACKET_QDISC_BYPASS`). `time.sleep` alone gives 60 us sd and single frames 0.6 to 2.4 ms late (step 6); a pure busy-wait at real-time priority stalled 37 ms once | N21, N20, N14; step 6's table in `00-phase0.md`, section 7 |
| **Keep our own packets**: type 0x07 sync of 112 bytes with the level in it, two syncs, two brightness packets, row header 08 88. The S2's bytes are not needed; the doubled sync is harmless in this order | N7 against N8; N4 against N5 |
| **BGR on the wire**, as measured on 2026-09-29 afternoon (unchanged by this session) | `hardware.md`, 15:40 |
| **Send past the port's queue.** Not because the queue caused what was seen (it did not show), but because it reorders one frame in a thousand the old way and the driver should not depend on the queue's mood | step 6; S2o |
| **Watch what the Pi can hold.** Every number above is from a 20-core desktop. The Pi 5 under MediaPipe has to hold the sync to about 100 us at 59 frames a second in Python, or in a helper process, or in a small C program. Measure it with `send.py --dry-run` and then with `--stamp` before building on it | (not tested) |

What the driver need not do: imitate the S2's header, send one sync, drop the brightness packet, or change the
row header. What it must not do: send 20 or 30 frames a second to this card, in any order.

## 6. Things to keep an eye on

- **55 frames a second went black once.** After N16 at 55 the owner's words were about the run beside it
  ("I saw flicker at 50. Do 55 again"), so 55 had shown something; N16b, the same command a minute later,
  gave a black wall for its whole 20 s, with every frame stamped out of the port and nothing else on the
  wire. The next run (N18, the plain base) showed bars, so the card had not locked. UNKNOWN why. It is one
  more reason to stay near 59 and to keep the black-tail-and-hold behaviour in the driver's close.
- **The dips at 60.00.** A couple in 30 s. INFERENCE: the drift between the sender's clock and the card's.
  At 59 none were reported. If the driver runs at 59 this is moot; if it must run at 60.00 for another
  reason, expect a hitch every 10 to 30 s.
- **The S2's stream refuses 20 frames a second** while ours does not. UNKNOWN which byte. Of no consequence
  unless someone builds on the S2's header.
- **The afternoon's "fast flicker" at 20 was not reproduced** (S2, S2o: "slight/some"). The card had been
  power-cycled; that afternoon it had come from LEDVision. Whatever state the card was in then, a power
  cycle clears it; the driver's dark start should follow one at the install.
- **The eye was the instrument.** One owner, mostly told what each run was (at his request, from N1 on), no
  camera. The blind rounds (P1, P2) and the back-to-back pairs (N7 and N8, N9 and N10, N16 and N17) are the
  firmest verdicts. The 240 fps clips of the run sheet were not made: whether "no flicker" at 59 is gone or
  too fast to see is still open, and a camera will still see it if it is only fast. For an audience it does
  not matter; for the flash governor's safety argument it may.

## 7. What was not done

- The run sheet's batches B (jitter below 0.25 ms, 61, 120), C (which brightness field), D's ladder above
  L3, E (the declared rate) and the 240 fps clips. The owner asked to prove the hypothesis before tuning;
  the hypothesis turned out to need one change of order, and the session went to what the driver needs
  instead (rate, jitter, movement).
- Byte 37 was never sent.
- Nothing was flashed, written or read on the card. The card was power-cycled before and after.

## 8. Stop condition

The brief's stop condition is met: the report is written after phase 1, the finding is not "out of a
sender's reach", it is "the order, the rate and the timing, all within a Linux sender's reach". Route A goes
ahead with the changes of section 5. Route C (a sender card) is not needed for the flicker. Phase 2 of the
spike (a sender card on the bench) is not needed.
