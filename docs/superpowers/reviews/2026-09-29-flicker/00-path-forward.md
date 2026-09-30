# The wall flickers while the card is fed data: findings and a path forward

2026-09-29. Five read-only research lanes; their full reports are beside this file (01 to 05).
Install date: 2026-11-11.

Labels: CONFIRMED (a primary source or our own measurement), LIKELY, SPECULATIVE.

## 1. What the flicker is

- CONFIRMED. It is a known fault of Colorlight "5A" firmware 13.x when a computer's network port feeds
  the card directly. Other people see it under LEDVision on bare-metal Windows, under Falcon Player after
  its firmware-13 patch, and under third-party senders. Falcon Player closed its issue unresolved
  (FPP #2242, 2026-06-22) and recommends a sender card. Firmware 11.04 and 11.09 do not flicker.
  One forum report is nearly our wall: 5A-75E, P5, 2 x 2, 128x64, LEDVision 8.8, "If I close the LEDVision
  program, the flickering stops".
- CONFIRMED. It is not our network port. The link never dropped, errors are 0, pause frames are off, and
  the port was silent (0 packets in 90 s) with the sender idle.
- LIKELY. It is not electrical. The wall is steady when the card holds a frame and steadiest at the
  highest packet rate; a coupling fault would do the opposite. Not excluded: the supply voltage was never
  measured.
- LIKELY. Each sync packet disturbs the card's scan once, so the flicker rate is the sender's frame rate.
  LEDVision sent 25.00 frames a second in the one capture available (someone else's); 25 Hz filmed at 30
  gives dips on a 6-frame grid, which is what our phone video shows.
- CONFIRMED (our measurement, the owner's eye, two A/B runs). 60 frames a second is the steadiest input.
  The only sender anyone reports clean on 13.x, Colorlight's S2 sender card, sends 60.32 frames a second.
- NOT KNOWN. Whether at 60 frames a second the disturbance is gone or only too fast to see. This is the
  first thing to measure.

## 2. What the written log got wrong

- The 20 / 30 / 60 series is confounded: the 30 run had the 1 ms pause before the sync, the 20 run did not.
- "960 Hz x16 = 60 x 16, so the card wants 60" is an inference. LEDVision's stream flickered at x1 too.
- The phone video with 8 % dips was taken at 360 Hz / x1 / 10.4 MHz, and the dips are about two a second on
  a 6-frame grid, not a regular 5 Hz.
- A second phone video (60 fps with the pause) was analysed and never reported: no 8 % dips, no rolling band.
- Every Linux run showed static bars, which hide lost rows. No packet capture of any of our streams exists.

## 3. The driver against the hardware

| Gap | The code today | The wall |
|---|---|---|
| Sync packets per frame | 1 | 2 worked; 1 not yet tried on its own |
| Brightness packet | every 3rd push | twice a frame worked; the need is unproven (the S2 sends none) |
| Pixel order | RGB | BGR (CONFIRMED) |
| Output rate | the content's: show 20, arcade 30 | only 60 measured steady |
| Sync timing | n/a | sync right behind the rows gives noise on the bottom rows |
| Close | two black frames, then the socket closes; the arcade sends none | the card needed about 1 s of black at 60 |
| Start | the wall is taken to be dark | the card keeps its last picture through a restart |
| A pulled cable | taken to raise an error | probably raises nothing on Linux (LIKELY) |

The bottom-row noise has a likely cause: the test sender puts the sync straight after the rows, and the
port's queue (byte limit 26298, exactly one frame) hands the whole burst over at once. Falcon Player,
LEDVision and the S2 all leave the idle time between the rows and the sync. Two other authors document
the same noise and cure it with a pause of 5 to 10 ms, not 1.

## 4. Three routes

| Route | For | Against |
|---|---|---|
| A. Software: fix the driver, send a steady 60 Hz | Our own measurement; no parts, no flashing; the driver needs most of this work anyway | Nobody else has reported it working; "steady" at 60 may mean "too fast to see" |
| B. Firmware: card down to 11.x | The fix most people used | Every success was a 5A-75B. One 5A-75E was bricked by 11.04. Our card's hardware revision is not recorded. Card 2 is the only good card. Whether 11.x knows the ICN2018/3018 decoder is not known |
| C. Hardware: a Colorlight sender card fed by HDMI | The vendor's own path; the one sender reported clean | A part to buy and ship; the raw-socket driver is replaced by an HDMI output; the 128x64 picture must sit in a video mode |

Recommendation: route A now, with route C ordered as insurance. Do not flash card 2.
Route B only on card 1, only after its hardware revision is read, and only if A fails.

## 5. Next session at the wall (no new code)

On the Omarchy box, `~/Work/codeisart-wall/cl_fpp_test.py`, run with sudo as before. Brightness stays at
the default 10 %. One variable per run.

Before anything: turn off IPv6 and avahi on `enp5s0`. Film with the phone in slow motion (240 fps),
exposure locked, and film the control first.

| # | Run | What it settles |
|---|---|---|
| 0 | Sender stopped, the card holding a picture; 240 fps clip | The control: what a steady wall looks like to this camera |
| 1 | `--fps 60`, 240 fps clip | Is the disturbance gone at 60, or only fast? |
| 2 | `--fps 20`, `--fps 30`, `--fps 60`, all without `--gap-ms`; then all three with `--gap-ms 1` | Undoes the confound in the log |
| 3 | `--fps 60 --gap-ms 12 --spin`, and without `--spin` | The reference layout (idle before the sync): bottom rows clean and steady? |
| 4 | at `--fps 60`: `--no-dup`; `--no-dup --sync-reps 2`; `--sync-reps 1` | Which doubling firmware 13.17 needs |
| 5 | `--fps 50`, `55`, `58`, `59`, `61`, `62`, `65`, `120` | How exact the rate must be |
| 6 | `--fps 60 --seconds 10 --tail-seconds 0`, watch 5 s, three times | Does the card hold the picture when the sender stops, with no blink? This is also Q66's safety check |
| 7 | `--fps 60 --tail-seconds 0.05`, `0.1`, `0.25`, `0.5` | The fewest black frames that land a black wall |

Also, while there:
- `tcpdump` on `enp5s0` during one run, to see the real timing on the wire.
- A multimeter on the 5 V rail at the card and at the far panel (the plug sits on pads marked "2.8V").
- Read the card's hardware revision from the board's silkscreen.
- Answer the three open questions: whole wall or parts; white only or colours too; does it change when
  the eyes move.

Needs a few lines of new code, lower priority:
- A moving picture in the test sender.
- Traffic the card ignores (a foreign EtherType, the same volume) while it holds a frame. Flicker here
  would mean an electrical cause after all.

Decision after the session:
- Run 1 clean and run 3 clean: build route A.
- Run 1 shows the disturbance at 60: route A still hides it from the eye, but cameras will see it.
  Decide then whether that is good enough, or route C.
- Nothing is steady: route C.

## 6. The driver work (route A), in order

A safety slice on its own branch; the driver is shared by the show and the arcade. `arcade/flash.py`
needs no change.

1. The output frame as one function, with the measured layout and counts as named constants; BGR on the
   wire. Check: `wall_pattern.py rgb` shows red, green, blue, white from the left.
2. A close that drains to black; the pattern tool paced by deadline; a dark start. Check: Ctrl-C lands
   black three times of three.
3. The steady sender: it repeats the last governed frame at the output rate; `push` copies and returns.
   Check: the show at 20 and the arcade at 30 are steady by eye and by slow-motion video.
4. Failure handling: errors carried back to the caller, the hold logic kept, a third display model, the
   iteration-14 sweeps rerun. Check: pull the cable for 5 s.

Safety points for that slice:
- The governor cannot see what the card does. The old picture flashing hard under the repo driver, and
  the flicker at 20 and 30, both happen after the governor has passed the frame. Nothing runs in front
  of people until the output is measured steady.
- With BGR unhandled the governor's saturated-red rule judges blue as red.
- The steady sender must originate no content of its own. The dark start is the one exception and needs
  the owner's word.
- Python timing on the Pi 5 under MediaPipe is not measured. Start with a thread; move the same core to a
  separate process or a small C helper if the sync intervals are rough.

## 7. Separate, small

- Blanking is saved as 3 (300 ns), below the row driver's 500 ns datasheet minimum; the factory value was
  11. It cannot explain flicker that stops with the sender. Try 6 and 11 in the card's RAM in the next
  LEDVision session. Every timing change there resets Brightness Level to 8 (81 %).
- The card's gamma is 2.8; the governor allows 1.0 to 2.2. SPECULATIVE until the gamma pattern is read
  on the wall.
- `hardware.md` needs the corrections of section 2.
