# Sender-card spike, phase 1: the run sheet

Written 2026-09-29 in phase 0, rewritten the same evening after an adversarial review (`00-phase0.md`,
section 11). For one session at the wall, about an hour, the owner present.
Brief: `docs/superpowers/specs/2026-09-29-sender-card-spike.md`. Findings so far: `00-phase0.md`.

Runs marked **core** are the spine, 25 of them: about 40 minutes with the verdicts. The others are taken
where a core run calls for them or time allows. If the hour ends early, stop anywhere after batch B: the
spike then has its main answer, and the S2 batch unreached is an honest "unknown".

## How this sheet guards the result

| What could make the result false | The guard |
|---|---|
| The port's queue lets the sync overtake the last rows: measured, 2 of 2400 frames the old sender's way (`00-phase0.md`, section 7) | Every run goes past the queue. One pair (A2, A2q) tests the queue itself. Every run counts what the queue held and which left first |
| A flicker that is not there cannot be seen to go | Two runs that are known to flicker (A4, A5). Comparisons are made at a rate where the base flickers (`RATE`) |
| Brighter looks steadier | Runs that are compared have the same light: the same pixel value and the same levels. The S2's own level is a rung of its own |
| The eye sees what it expects; memory fades in 20 runs | A control is repeated beside every batch that is compared with it; close calls are played blind (`ab`) |
| The card keeps something from an earlier run | The base comes back after the first S2-style runs, after the guessed value, and at the end |
| The sender's own jitter is as large as the jitter under test | Step 6's numbers decide which jitter runs count |

## The owner's word

1. **The S2's sync carries level 0xff.** The brief's safety rule 3 lets an S2-style sync go out with pixels of
   25 or less, and says in the same paragraph "never a level above 0.4". The sender reads it this way: 0xff
   only in a sync with the S2's source type (0x00), and then the pixels are dim and nothing lifts that;
   every other level is capped at 0.4. Only D1, L8 and S8 send 0xff.
   **Answered 2026-09-29:** "Whatever is easiest. It's in a controlled environment and wont harm anyone."
   The sender's reading stands.
2. **The sync before the rows.** B1, D1, D2, L7, L8 and batch E send the sync first, as the S2, LEDVision and
   Falcon Player do. The one warning against it (menull, 13.39) turns out to be about something else: his
   "init-style" is fifty syncs in a row with no rows between them, which is the brief's safety rule 2 and
   which this sender cannot produce. Our own record: the repo driver sends its sync first; it ran on this
   card on 2026-09-29 at 16:06, showed no picture, and the card answered the next sender at 16:12 without a
   power cycle. If the card does stop answering: power-cycle, run A2, go on without the sync-first runs.
3. **Flicker on purpose**, as the brief's rule 4 says: the owner's word before each batch. A4 and A5 are
   meant to flicker (20 frames a second, as on 2026-09-29 at 16:12).

## The short form: prove the hypothesis first

The owner, 2026-09-29: "Lets prove out the hypothesis before tuning." So the first thing at the wall is not
the whole sheet but these nine runs, about 12 minutes: does sending as the S2 sends take the flicker away,
yes or no? Which field does it, how much jitter the card bears and the rest of the sheet are tuning, and
come after a yes. The helpers and the rules below apply.

| Run | Command | What the owner is asked | What it settles |
|---|---|---|---|
| S1 | `run S1` | the three questions | The base: a picture, as steady as on record? |
| S2 | `run S2 --fps 20` | the three questions | A run known to flicker. It must flicker tonight |
| S3 | `run S3 --pixel 25 --fps 20` | the three questions | DIM. The same, dim: can its flicker be seen? This is what S4 is compared with |
| S4 | `run S4 --s2 --sync-level 0.1 --fps 20` | the three questions; against S3 | DIM. **The test by eye:** the S2's packets, order and single sync at S3's rate and light. A picture? Less flicker than S3? |
| S5 | `run S5 --pixel 25 --fps 20` | the three questions; as S3? | S3 again: the control, and whether S4 left something in the card |
| S6 | `run S6 --pixel 25` | the three questions; a clip | DIM. The base at 60, for the camera |
| S7 | `run S7 --s2 --sync-level 0.1` | the three questions; a clip | DIM. **The test by camera:** the S2's way at 60, against S6's clip |
| S8 | `run S8 --s2 --fps 60.32` | a picture? brighter than S7? | DIM. The capture byte for byte, its rate and its level 0xff. Brighter than S7: the card obeys the level of an S2-style sync |
| S9 | `run S9` | as S1? | The base again. Not as S1: power-cycle, run it again, write down both |

Where S3 cannot be seen to flicker, S3 to S5 are run again with `--brightness 0.4` (and `--sync-level 0.4`
in S4), under the names S3b, S4b, S5b.

Reading it:

| S4 against S3 (by eye, at 20) | S7 against S6 (by camera, at 60) | What it says | Next |
|---|---|---|---|
| less flicker | steadier, or both steady | Sending as the S2 sends helps: a Linux sender can do what the sender card does | The ladder of batch D: which of its fields it is |
| the same | steadier | The S2's way helps only at its own rate | Batch B (rate and jitter), then the ladder at 60 by camera |
| the same | the same | No field of the S2 helps; what is left is timing | Batch B. If that shows nothing either, the finding is that the cause is out of a sender's reach |
| no picture in S4 or S7 | | The card refuses something of the S2's | The ladder of batch D from its bottom: which rung loses the picture |

At 20 frames a second the S2's header still says 60 (bytes 31, 32). If S4 is no steadier than S3 and S7 is
steadier than S6, that field is the first suspect: batch E.

## Before the session

1. **Gate: step 6 of the brief.** Passed on 2026-09-29, 19:47 to 20:00, the cable in a Raspberry Pi
   (`00-phase0.md`, section 7):

   | Row of the table | What it had to show | What it showed |
   |---|---|---|
   | `hybrid-fifo50-bypass-stamp-sw` (the `run` command below) | driver stamps 600/600; "order broken" 0/600 | 600/600 and 0/600, twice |
   | the rows through the queue in the base's order | does this port's queue reorder? | yes: 2 of 2400 frames the old sender's way; 0 of 2400 with the exact wait |
   | `hybrid-fifo50-bypass`, and `-rows-sync` | the port's worst, in microseconds: **W** | **W = 52** (sd 5); 29 to 43 with the sync first |

   Jitter below 3 x W = 0.16 ms cannot be told from none: the runs at 0.1 and 0.05 ms are struck.
   If the box was restarted or its kernel changed since, run the matrix again before the session.
2. Route A's runs (`docs/superpowers/reviews/2026-09-29-flicker/00-path-forward.md`, section 5) come first if
   both happen on one evening. Where a run here repeats one of them it says so. On an evening without them,
   run the old sender once first, as it was: `sudo .venv/bin/python cl_fpp_test.py --seconds 10 --fps 60`.
3. From the Mac, copy the tools:

   ```
   rsync -a --exclude __pycache__ /Users/trey/dev/codeisart-sender-spike/tools/sender_spike/ \
       omarchy:Work/codeisart-wall/tools/sender_spike/
   ```

4. On the Omarchy box (bash):

   ```
   cd ~/Work/codeisart-wall && mkdir -p runs
   .venv/bin/python -m tools.ledvision.vm status                  # the VM is off
   sudo sysctl -w net.ipv6.conf.enp5s0.disable_ipv6=1             # nothing else sends on the port
   sudo systemctl stop avahi-daemon.socket avahi-daemon.service
   run()    { local n=$1; shift; sudo chrt -f 50 .venv/bin/python tools/sender_spike/send.py --iface enp5s0 \
              --qdisc-bypass --stamp --log runs/$n.csv "$@" 2>&1 | tee -i runs/$n.txt; }
   queued() { local n=$1; shift; sudo chrt -f 50 .venv/bin/python tools/sender_spike/send.py --iface enp5s0 \
              --stamp --log runs/$n.csv "$@" 2>&1 | tee -i runs/$n.txt; }
   plain()  { local n=$1; shift; sudo .venv/bin/python tools/sender_spike/send.py --iface enp5s0 \
              --qdisc-bypass --stamp --log runs/$n.csv "$@" 2>&1 | tee -i runs/$n.txt; }
   old()    { local n=$1; shift; sudo .venv/bin/python tools/sender_spike/send.py --iface enp5s0 \
              --stamp --log runs/$n.csv "$@" 2>&1 | tee -i runs/$n.txt; }
   ab()     { local p=$1 x=$2 y=$3; if (( RANDOM % 2 )); then x=$3; y=$2; fi
              echo "1: $x | 2: $y" > runs/$p.order
              eval "run ${p}_1 $x" > /dev/null; eval "run ${p}_2 $y" > /dev/null
              echo "$p: the first or the second steadier, or the same? Then: cat runs/$p.order"; }
   say()    { echo "$(date +%T) $*" | tee -a runs/verdicts.txt; }
   ```

   - `run`: real-time priority, past the port's queue. `queued`: the same through the queue. `plain`:
     ordinary priority, past the queue. `old`: ordinary priority, through the queue, as on 2026-09-29.
   - `ab NAME "FLAGS" "FLAGS"` plays two runs in an order it does not tell, and keeps the order in a file.
   - `tee -i` stays alive through Ctrl-C. The sender also writes `runs/<name>.csv` and
     `runs/<name>.report.txt` before it prints anything.
   - Every run prints three lines to look at: "N not ours" (other traffic on the port: should be 0; if not,
     `nmcli device set enp5s0 managed no`), "the port's queue held ..." (should be "no packet" past the
     queue), and "the sync left before the last row of its frame in N of M frames" (should be 0).

5. The phone on a stand, slow motion at 240 fps, the same framing all evening. Two exposure locks: one on
   the bright base (A2), one on the dim base (A3). A clip is compared only with a control of its own lock.
6. The room dim. Nobody but the owner in front of the wall.

Afterwards: `sudo sysctl -w net.ipv6.conf.enp5s0.disable_ipv6=0`,
`sudo systemctl start avahi-daemon.socket avahi-daemon.service`, `nmcli device set enp5s0 managed yes` if it
was changed, and **power-cycle the card**, whatever the last run showed.

## Rules during the session

- The owner's word before each batch. One variable a run. 10 s a run.
- **The verdict first, the variable after.** The owner answers before hearing what the run changed. Where
  the agent types the commands, it names the run by its letter only.
- A run ends in 1 s of black when it ends by itself or by one Ctrl-C. It does not when the socket fails or
  Ctrl-C is pressed twice: the card then holds the last frame. Any next run ends in black again.
- Flicker is made on purpose here. Look away or stop the run with one Ctrl-C when it is unpleasant.
- If the wall shows something that was not sent, or goes dark and stays dark: stop, power-cycle the card,
  run A2 again before anything else.
- Runs marked DIM send pixels of 25 or less. A run is dim when a packet of it holds anything the base's
  does not, or when it sends no brightness packet: nobody knows what the fields mean, so nobody knows what
  the card then does with the brightness (safety rule 3). The sender enforces it.
- A dim run is compared with a dim run of the same levels, never with a bright one.
- No run sends anything but sync, row and brightness packets. A field takes only values seen on the wire
  (and 0x1e for H3). Byte 37 is not sent.

## After each run the owner answers

1. **A picture, or none?**
2. **Flicker: none, slight, some, or fast?**
3. **Bottom rows: clean, or noisy?**

Where the sheet asks for it, a fourth: **brighter, the same, or dimmer than the run named?**

`say B3 picture, slight, clean, a slow beat about once a second` writes it down with the time.
A clip at 240 fps for every run that gets "none" for flicker, to tell gone from too fast to see.

## Batch A: the controls and the base (10 runs, 8 core)

| Run | Core | Command | What it settles |
|---|---|---|---|
| A0 | core | `run A0 --seconds 5 --tail-seconds 0`, then film the wall for 10 s while nothing is sent | The bright control: what a held picture looks like to this camera. Also: does the card hold the picture when the sender stops? (Route A's run 6) |
| A1 | core | `old A1 --wait sleep` | The old test sender's way: ordinary priority, `time.sleep`, through the queue; but at a true 60.000 (the old one ran 59.7). On the wire its sync wanders by 0.6 ms (sd 61 us), against A2's 52 us (sd 5): A1 against A2 is a jitter run in itself |
| A2 | core | `run A2` | The base of the evening: real-time priority, the exact wait, past the queue |
| A2q | core | `queued A2q` | The queue alone against A2. Bottom rows noisy here and clean in A2, with "the sync left before the last row" above 0: the noise of 2026-09-29 was this PC's queue, not the card's |
| A2r | core | `run A2r`, unannounced, somewhere in batch B | A2 again: how far two verdicts on one and the same run lie apart. A difference smaller than that is no difference |
| A1b | | `plain A1b` | Ordinary priority against A2's real-time priority |
| A4 | core | `run A4 --fps 20` | A run that is known to flicker ("Bars, flashing", 16:12). It must flicker tonight too, or the evening does not stand on the record |
| A5 | core | `run A5 --pixel 25 --fps 20` | DIM, and meant to flicker. Seen to flicker: flicker can be judged at the dim level. Not seen: see below |
| A3 | core | `run A3 --pixel 25` | DIM. The dim base at 60. Then film it held: `run A3h --pixel 25 --seconds 5 --tail-seconds 0`, the dim control, with the dim exposure lock |
| A3b | | `run A3b --pixel 25 --brightness 0.4` | Only where A5 was too dim to judge: the dim base four times brighter, within the cap |

After the batch, two things are written at the top of the sheet:

- **`DIMLEVEL`.** A5 was seen to flicker: nothing. A5 was not, and `run A5b --pixel 25 --brightness 0.4 --fps 20`
  was: every dim command below gets `--brightness 0.4`, and every `--sync-level 0.1` becomes
  `--sync-level 0.4`. Neither was: flicker cannot be judged by eye at the dim level; batches C, D and E
  report "a picture or none" and "brighter or dimmer", and their flicker is read from clips alone.
- **`RATE`.** A3 flickers (slight or more): `RATE` is nothing, and the S2 batch is compared at 60. A3 got
  "none": `RATE` is `--fps 20`, and the S2 batch is compared with A5, where there is a flicker to lose.

## Batch B: what kind of machine the card is (6 core runs, up to 7 more)

H4, H9 and H1 of the brief. This is the spike's main question.

| Run | Core | Command | What it settles |
|---|---|---|---|
| B1 | core | `run B1 --order sync-rows` | H4: the sync first, the rows right behind it. A picture? Bottom rows clean? Steadier than A2? |
| B2 | | `run B2 --gap-ms 12` | H4's other form: the base's order with 12 ms between rows and sync. (Route A's run 3; skip if done) |

Now choose the layout for the rest of the batch: the steadier of A2, B1 and B2. Where the call is close, play
it blind: `ab B1x "--order sync-rows" ""`. Where they tie, B1. Write its flags where `LAYOUT` stands below
(for B1: `--order sync-rows`; for A2: nothing).

| Run | Core | Command | What it settles |
|---|---|---|---|
| B3 | core | `run B3 LAYOUT --fps 59` | H9. Anything that 60 does not have: a beat of once a second (the card free-runs at its own 60), or another |
| B4 | core | `run B4 LAYOUT --fps 61` | H9, the other side. The same: confirmed |
| B5 | | `run B5 LAYOUT --fps 60.32` | The S2's rate. Any difference from 60? |
| B0 | core | `run B0 LAYOUT` | The layout's own run again, right before the jitter: the control for B6 to B9 |
| B6 | core | `run B6 LAYOUT --jitter-ms 2` | H1, the largest jitter first. The same as B0: the card does not care when the frame comes; skip B7 to B9 |
| B7 | core | `run B7 LAYOUT --jitter-ms 1` | H1 |
| B8 | | `run B8 LAYOUT --jitter-ms 0.25` | H1 |
| B9 | | `run B9a LAYOUT --jitter-ms 0.5` | Only where B7 showed and B8 did not: the budget lies between 0.25 and 1 ms. Below 0.16 ms (3 x W) the sender's own jitter is as large as the one under test: no run |
| B10 | | `run B10 LAYOUT --fps 50`, `run B11 LAYOUT --fps 120` | H9's far points. (Route A's run 5.) With `--gap-ms 12` as the layout 120 does not fit: the sender refuses it |
| B12 | | `run B12 LAYOUT --picture scroll` | Still bars hide lost rows. Does a moving picture tear or stutter? |

The jitter holds the whole frame back, its rows and its sync together, in either layout. It opens no pause
between the rows and the sync: a pause there changes the flicker by itself (2026-09-29, "A steadier" twice),
and that is B2's variable, not this one.

Reading the batch:

| B3, B4 | B6, B7 | The card |
|---|---|---|
| a beat | as B0 | free-runs at its own rate: the sender must match the rate, its jitter matters little |
| as 60 | flicker grows with jitter | follows the sync: the rate is free, the jitter is the budget |
| a beat | flicker grows with jitter | both: a lock with a narrow range |
| as 60 | as B0 | neither: the cause is elsewhere, batch D matters more |

Each cell stands only if A2r came out as A2 did.

## Batch C: which brightness field the card obeys (6 runs, 2 core)

All with pixel 25, all compared with C0.

| Run | Core | Command | What it settles |
|---|---|---|---|
| C0 | core | `run C0 --pixel 25` | The dim base again, both levels 0.1: the control of this batch |
| C1 | core | `run C1 --pixel 25 --sync-level 0.4` | Fourth question against C0. Brighter: the card obeys the sync's level (PC-style header) |
| C1b | | `run C1b --pixel 25 --bright-level 0.4` | Fourth question against C0. Brighter: the card obeys the brightness packet's level |
| C3 | | `run C3 --bright-reps 1` | H8's middle: one brightness packet a frame. Against A2 |
| C2 | | **power-cycle the card first**, then `run C2 --bright-reps 0` | DIM. H8. A card remembers the last brightness packet, so only a card fresh from power can say what no packet means. A picture as bright as C0: the packet is not needed. Steadier than C0: it disturbs. Then `run C2b --pixel 25`, and C0's brightness must be back |

## Batch D: the S2 (8 core runs, up to 8 more)

All DIM. The owner's word on the first of the three things above comes first.
`RATE` is what batch A found: nothing, or `--fps 20`. `DIMLEVEL` applies.

| Run | Core | Command | What it settles |
|---|---|---|---|
| D0 | core | `run D0 --pixel 25 RATE` | The dim base, right before: the control of this batch |
| D2 | core | `run D2 --s2 --sync-level 0.1 RATE` | The whole imitation at the base's light. A picture? (mjunek got none; how he sent it is not recorded.) **Flicker against D0: this is the S2 question** |
| D0b | core | `run D0b --pixel 25 RATE` | The base again. As D0: the S2-style packets left nothing behind. Not as D0: power-cycle, write it down, and every later run is read with that in mind |
| D1 | core | `run D1 --s2 --fps 60.32` | The S2's own rate and its own level, 0xff: the capture byte for byte. A picture? Fourth question against D2: brighter means the card obeys the level of an S2-style sync. Its flicker is not compared with D0's: the light differs |

If D1 was brighter than D2, and the owner says so: the rungs below may add `--pixel 128 --level-field-proven`
(not L8, whose level is 0xff), and are then compared with `run D0c RATE`, the bright base at that rate.

Then the ladder. Each rung adds one thing to the rung below it; all but the last have the dim base's light.

| Rung | Core | Command | Adds | Hypothesis |
|---|---|---|---|---|
| L0 | | D0 (done) | the base, dim | |
| L1 | core | `run L1 --source-type 00 RATE` | byte 13 | H2 |
| L2 | core | `run L2 --s2-header --sync-level 0.1 RATE` | the rest of the header: counter, bytes 16 to 18, byte 26, bytes 31 and 32, byte 36 | H2 |
| L3 | core | `run L3 --s2-header --sync-level 0.1 --sync-reps 1 RATE` | one sync a frame | H10 |
| L4 | | `run L4 --s2-header --sync-level 0.1 --sync-reps 1 --bright-reps 0 RATE` | no brightness packet | H8 |
| L5 | | `run L5 --s2-header --sync-level 0.1 --sync-reps 1 --bright-reps 0 --row-tail 0000 RATE` | the S2's row header | H7 |
| L6 | | `run L6 --s2-header --sync-level 0.1 --sync-reps 1 --bright-reps 0 --row-tail 0000 --sync-len 1036 RATE` | the S2's sync length | H6 |
| L7 | core | `run L7 --s2 --sync-level 0.1 RATE` | the S2's order: sync first. (It is D2 again: a second verdict on one run) | H4 |
| L8 | | `run L8 --s2 RATE` | the S2's level, 0xff. Brightness only; its flicker is not compared | |

- **D2 gave a picture and was steadier than D0:** walk down from L6 until the flicker is back. The rung
  above that one holds what matters. Then run the rungs not yet run: two fields may work only together.
- **D2 gave no picture:** walk up from L1 until the picture goes. That rung holds what the card refuses.
- **D2 gave a picture and the same flicker as D0:** the core rungs only. If `RATE` is `--fps 20`, this is a
  real "no byte helps". If `RATE` is nothing and D0 got "none", it is a tie at the top and says nothing.

More, where D2 gave a picture:

| Run | Core | Command | What it settles |
|---|---|---|---|
| D3 | | `run D3 --s2 --sync-level 0.1 --counter off RATE` | H5: does the card need the counter to count? |
| D4 | | `run D4 --s2 --sync-level 0.1 --sync-reps 2 RATE` | H10 from the other side: the S2's sync, doubled. Flicker back? |

And on the base, whatever D2 gave:

| Run | Core | Command | What it settles |
|---|---|---|---|
| D5 | | `run D5 --sync-reps 1` | A PC-style sync once: a picture? (Route A's run 4; skip if done) |
| D6 | | `run D6 --row-tail 0000 RATE` | DIM. H7's fourth corner: the S2's row header under the PC's sync. A picture? |

## Batch E: the declared rate (5 runs, only if D2 gave a picture)

H3. All DIM, all at 30 frames a second, the arcade's rate.

| Run | Command | What it settles |
|---|---|---|
| E0 | `run E0 --pixel 25 --fps 30` | The base at 30: the control of this batch |
| E1 | `run E1 --s2 --sync-level 0.1 --fps 30` | The S2's sync declaring 60 (0x3c), sent at 30 |
| E0b | `run E0b --pixel 25 --fps 30` | The base again, before a value that nobody has seen on a wire |
| E2 | `run E2 --s2 --sync-level 0.1 --fps 30 --declared-rate 011e` | Declaring 30 (0x1e), sent at 30. Steady where E1 is not: the arcade needs no 60 Hz repeat. 0x1e is the brief's guess |
| E0c | `run E0c --pixel 25 --fps 30` | The base again. Not as E0b: the guess left something behind; power-cycle and write it down |

## Batch F: back to the base (1 core run)

| Run | Command | What it settles |
|---|---|---|
| F1 | `run F1` | As A2? If not, something stayed in the card: power-cycle, run it again, write down both. F1 is run whatever the clock says |

## What goes into the report

`docs/superpowers/reviews/<date>-sender-card-spike.md`, written after the session whatever it found.
For each run: the first line of `runs/<name>.report.txt` (it names every variable of the run); the lines
"sync to sync" by the loop and by the driver, "late", "slips", "not ours", "the port's queue held" and
"left before"; the owner's words from `runs/verdicts.txt`; the order file of a blind pair; and the clip's
numbers where there is one, with the lock it was filmed under.
