# Sender-card spike, phase 1: the run sheet

Written 2026-09-29 in phase 0. For one session at the wall, about an hour, the owner present.
Brief: `docs/superpowers/specs/2026-09-29-sender-card-spike.md`. Findings so far: `00-phase0.md`.

About 35 runs of 10 s. The runs that say most come first: if the hour ends early, stop anywhere after
batch B and the spike still has its main answer.

## Three things that need the owner's word before the session

1. **The S2's sync carries level 0xff.** The brief's safety rule 3 lets an S2-style sync go out with pixels of
   25 or less, and says in the same paragraph "never a level above 0.4". Both cannot hold for batch D. The
   sender reads it this way: 0xff only in a sync with the S2's source type (0x00), and then the pixels are
   dim and nothing lifts that; every other level is capped at 0.4. If the owner reads the rule the other
   way, batch D runs with `--sync-level 0.4` on every command and is no longer the S2's sync byte for byte.
2. **The sync before the rows.** One source (menull, firmware 13.39, a 5A-75B) lists "`0x0101` before pixels
   (init-style): brief flash, then card stops responding", in the table whose next line became the brief's
   safety rule 2. B1, L7, D1 to D4 and batch E send the sync first. What speaks for them: the S2, LEDVision
   and Falcon Player all put the sync first on the wire, and the brief's H4 asks for it. What our own record
   says: the repo driver sends its sync first, once; the owner ran it for 30 s on 2026-09-29 at 16:06; the
   wall showed no picture; the card was not power-cycled (the link did not drop between 14:56 and 16:27);
   and at 16:12 the test sender put bars on the wall. So a sync-first stream has not locked this card.
   If the card does stop answering: power-cycle, run A2, go on without the sync-first runs.
3. **Flicker on purpose**, as the brief's rule 4 says: the owner's word before each batch.

## Before the session

1. **Gate: step 6 of the brief has been run** (`00-phase0.md`, section 7) and its first row,
   `hybrid-fifo50-qdisc-stamp-sw`, shows stamps. That row is the `run` command below. Until then the stamps
   have never met a kernel. If `--stamp` fails at the wall, take it out of `run` and `plain`: the loop's
   own clock is still printed.
2. Route A's runs (`docs/superpowers/reviews/2026-09-29-flicker/00-path-forward.md`, section 5) come first if
   both happen on one evening. Where a run here repeats one of them it says so.
3. From the Mac, copy the tools:

   ```
   rsync -a --exclude __pycache__ /Users/trey/dev/codeisart-sender-spike/tools/sender_spike/ \
       omarchy:Work/codeisart-wall/tools/sender_spike/
   ```

4. On the Omarchy box:

   ```
   cd ~/Work/codeisart-wall && mkdir -p runs
   .venv/bin/python -m tools.ledvision.vm status                  # the VM is off
   sudo sysctl -w net.ipv6.conf.enp5s0.disable_ipv6=1             # nothing else sends on the port
   sudo systemctl stop avahi-daemon.socket avahi-daemon.service
   run()   { n=$1; shift; sudo chrt -f 50 .venv/bin/python tools/sender_spike/send.py --iface enp5s0 \
             --stamp --log runs/$n.csv "$@" 2>&1 | tee -i runs/$n.txt; }
   plain() { n=$1; shift; sudo .venv/bin/python tools/sender_spike/send.py --iface enp5s0 \
             --stamp --log runs/$n.csv "$@" 2>&1 | tee -i runs/$n.txt; }
   say()   { echo "$(date +%T) $*" | tee -a runs/verdicts.txt; }
   ```

   `run` is the sender at real-time priority; `plain` is without. `tee -i` stays alive through Ctrl-C, so a
   run that is stopped still prints its report. The sender also writes `runs/<name>.csv` (a line a frame)
   and `runs/<name>.report.txt` before it prints anything.
   Every run prints "N not ours": packets the port sent that were not the run's. It should be 0. If it is
   not, NetworkManager is the next thing to quiet: `nmcli device set enp5s0 managed no`.

5. The phone on a stand, slow motion at 240 fps, exposure and focus locked, the same framing all evening.
6. The room dim. Nobody but the owner in front of the wall.

Afterwards: `sudo sysctl -w net.ipv6.conf.enp5s0.disable_ipv6=0`,
`sudo systemctl start avahi-daemon.socket avahi-daemon.service`, and `nmcli device set enp5s0 managed yes`
if it was changed.

## Rules during the session

- The owner's word before each batch. One variable a run. 10 s a run.
- A run ends in 1 s of black when it ends by itself or by one Ctrl-C. It does not when the socket fails or
  Ctrl-C is pressed twice: the card then holds the last frame. Any next run ends in black again.
- Flicker is made on purpose here. Look away or stop the run with one Ctrl-C when it is unpleasant.
- If the wall shows something that was not sent, or goes dark and stays dark: stop, power-cycle the card,
  run A2 again before anything else.
- Runs marked DIM send pixels of 25 or less. A run is dim when a packet of it holds anything the base's
  does not, or when it sends no brightness packet: nobody knows what the fields mean, so nobody knows what
  the card then does with the brightness (safety rule 3). The sender enforces it.
- A dim run is compared with a dim run (A3), never with a bright one. Low grey levels are made of fewer and
  shorter pulses and may flicker in their own way.
- No run sends anything but sync, row and brightness packets. A field takes only values seen on the wire
  (and 0x1e for H3). There is no flag for byte 37.

## After each run the owner answers

1. **A picture, or none?**
2. **Flicker: none, slight, some, or fast?**
3. **Bottom rows: clean, or noisy?**

Where the sheet asks for it, a fourth: **brighter, the same, or dimmer than the run named?**

`say B3 picture, slight, clean, a slow beat about once a second` writes it down with the time.
A clip at 240 fps for every run that gets "none" for flicker, to tell gone from too fast to see.
Where a verdict is close, play the pair again back to back under new names: `run B1x --order sync-rows`,
then `run A2x`.

## Batch A: the control and the base (5 runs)

| Run | Command | What it settles |
|---|---|---|
| A0 | `run A0 --seconds 5 --tail-seconds 0`, then film the wall for 10 s while nothing is sent | The control: what a held picture looks like to this camera. Also: does the card hold the picture when the sender stops? (Route A's run 6; skip if done) |
| A1 | `plain A1 --wait sleep` | The old test sender's way, but at a true 60.000 (the old one ran 59.7). Is it still steady? |
| A1b | `plain A1b` | The exact wait, plain scheduling. Against A1: does the jitter of `time.sleep` (about 60 us) show? |
| A2 | `run A2` | The base of the evening: the exact wait at real-time priority. Against A1b: does the scheduling show? |
| A3 | `run A3 --pixel 25` | DIM. The base for every dim run. Fourth question: can flicker be judged at this level at all? |

If flicker cannot be judged in A3 (with the card's gamma of 2.8, pixel 25 at level 0.1 is about a hundredth
of the base's light): `run A3b --pixel 25 --brightness 0.4` is the dim base instead, four times brighter and
within the cap. If that is still too dim, the dim runs are judged by the phone's clips, and "a picture or
none" is asked with the room dark.

## Batch B: what kind of machine the card is (8 to 14 runs)

H4, H9 and H1 of the brief. This is the spike's main question.

| Run | Command | What it settles |
|---|---|---|
| B1 | `run B1 --order sync-rows` | H4: the sync first, the rows right behind it, as the S2, LEDVision and Falcon Player. A picture? Bottom rows clean? Steadier than A2? See "the sync before the rows" above |
| B2 | `run B2 --gap-ms 12` | H4's other form: the base's order with 12 ms between rows and sync. (Route A's run 3; skip if done) |

Now choose the layout for the rest of the batch: the steadier of A2, B1 and B2; where they tie, B1, because
its sync sits on the tick. Write its flags where `LAYOUT` stands below (for B1: `--order sync-rows`).

| Run | Command | What it settles |
|---|---|---|
| B3 | `run B3 LAYOUT --fps 59` | H9. A slow beat, once a second, that 60 does not have: the card free-runs at its own 60 |
| B4 | `run B4 LAYOUT --fps 61` | H9, the other side. The same beat: confirmed |
| B5 | `run B5 LAYOUT --fps 60.32` | The S2's rate. Any difference from 60? |
| B6 | `run B6 LAYOUT --jitter-ms 2` | H1, the largest jitter first. No change from the layout's own run: the card does not care when the sync comes, skip B7 to B9 |
| B7 | `run B7 LAYOUT --jitter-ms 1` | H1 |
| B8 | `run B8 LAYOUT --jitter-ms 0.25` | H1 |
| B9 | `run B9a LAYOUT --jitter-ms 0.5`, `run B9b LAYOUT --jitter-ms 0.1`, `run B9c LAYOUT --jitter-ms 0.05` | Only those between the last value that showed and the first that did not: the budget |
| B10 | `run B10 LAYOUT --fps 50`, `run B11 LAYOUT --fps 120` | H9's far points, if time allows. (Route A's run 5 has them with the old sender.) With `--gap-ms 12` as the layout 120 does not fit: the sender refuses it |
| B12 | `run B12 LAYOUT --picture scroll` | Still bars hide lost rows. Does a moving picture tear or stutter? |

Reading the batch:

| B3, B4 | B6 to B8 | The card |
|---|---|---|
| a beat | no change with jitter | free-runs at its own rate: the sender must match the rate, its jitter matters little |
| no beat | flicker grows with jitter | follows the sync: the rate is free, the jitter is the budget |
| a beat | flicker grows with jitter | both: a lock with a narrow range |
| no beat | no change | neither: the cause is elsewhere, batch D matters more |

## Batch C: which brightness field the card obeys (4 runs)

C1, C1b and C2 are compared with A3, whose two levels are both 0.1.

| Run | Command | What it settles |
|---|---|---|
| C1 | `run C1 --pixel 25 --sync-level 0.4` | Fourth question against A3. Brighter: the card obeys the sync's level (PC-style header) |
| C1b | `run C1b --pixel 25 --bright-level 0.4` | Fourth question against A3. Brighter: the card obeys the brightness packet's level |
| C2 | `run C2 --bright-reps 0` | DIM. H8, and the fourth question. The same brightness and a picture: the brightness packet is not needed. Steadier: it disturbs |
| C3 | `run C3 --bright-reps 1` | H8's middle: one brightness packet a frame. Against A2 |

## Batch D: the S2 (10 to 13 runs)

All DIM until D2 says otherwise. The owner's word on the first of the three things above comes first.

| Run | Command | What it settles |
|---|---|---|
| D1 | `run D1 --s2 --fps 60.32` | The whole imitation. A picture? (mjunek got none; how he sent it is not recorded.) Flicker? Fourth question against A3 |
| D2 | `run D2 --s2 --fps 60.32 --sync-level 0.1` | Fourth question against D1. Dimmer: the card obeys the level of an S2-style sync |

If D2 was dimmer than D1, and the owner says so: the rest of the batch may add
`--sync-level 0.1 --pixel 128 --level-field-proven` to every command, and is then compared with A2, not A3.
If D2 was not dimmer, the batch stays dim.

Then the ladder. Each rung adds one thing to the rung below it.

| Rung | Command | Adds | Hypothesis |
|---|---|---|---|
| L0 | A3 (done) | the base, dim | |
| L1 | `run L1 --source-type 00` | byte 13 | H2 |
| L2 | `run L2 --s2-header` | the rest of the header: counter, bytes 16 to 18, byte 26, bytes 31 and 32, level 0xff, byte 36 | H2 |
| L3 | `run L3 --s2-header --sync-reps 1` | one sync a frame | H10 |
| L4 | `run L4 --s2-header --sync-reps 1 --bright-reps 0` | no brightness packet | H8 |
| L5 | `run L5 --s2-header --sync-reps 1 --bright-reps 0 --row-tail 0000` | the S2's row header | H7 |
| L6 | `run L6 --s2-header --sync-reps 1 --bright-reps 0 --row-tail 0000 --sync-len 1036` | the S2's sync length | H6 |
| L7 | `run L7 --s2` | the S2's order: sync first | H4 |
| L8 | D1 (done) | the S2's rate | H9 |

- **D1 gave a picture and was steadier than A3:** walk down from L7 until the flicker is back. The rung
  above that one holds what matters.
- **D1 gave no picture:** walk up from L1 until the picture goes. That rung holds what the card refuses.
- **D1 gave a picture and the same flicker as A3:** walk up L1, L3, L7 only. No byte helps; batch B has the
  answer.

More, where D1 gave a picture:

| Run | Command | What it settles |
|---|---|---|
| D3 | `run D3 --s2 --fps 60.32 --counter off` | H5: does the card need the counter to count? |
| D4 | `run D4 --s2 --fps 60.32 --sync-reps 2` | H10 from the other side: the S2's sync, doubled. Flicker back? |

And on the base, whatever D1 gave:

| Run | Command | What it settles |
|---|---|---|
| D5 | `run D5 --sync-reps 1` | A PC-style sync once: a picture? (Route A's run 4; skip if done) |
| D6 | `run D6 --row-tail 0000` | DIM. H7's fourth corner: the S2's row header under the PC's sync. A picture? |

## Batch E: the declared rate (3 runs, only if D1 gave a picture)

H3. All DIM unless D2 lifted the cap.

| Run | Command | What it settles |
|---|---|---|
| E0 | `run E0 --pixel 25 --fps 30` | The base at the arcade's rate, for comparison |
| E1 | `run E1 --s2 --fps 30` | The S2's sync declaring 60 (0x3c), sent at 30 |
| E2 | `run E2 --s2 --fps 30 --declared-rate 011e` | Declaring 30 (0x1e), sent at 30. Steady where E1 is not: the arcade needs no 60 Hz repeat. 0x1e was never seen on the wire: it is the brief's guess |

## Batch F: back to the base (1 run)

| Run | Command | What it settles |
|---|---|---|
| F1 | `run F1` | As A2? If not, the S2-style packets left something in the card: power-cycle, run it again, write down both |

## What goes into the report

`docs/superpowers/reviews/<date>-sender-card-spike.md`, written after the session whatever it found.
For each run: the first line of `runs/<name>.report.txt` (it names every variable of the run), the lines
"sync to sync" by the loop and by the driver, "late", "slips" and "not ours", the owner's words from
`runs/verdicts.txt`, and the clip's numbers where there is one.
