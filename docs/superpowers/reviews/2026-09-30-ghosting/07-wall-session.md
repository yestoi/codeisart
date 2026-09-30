# The wall session of 2026-09-30, afternoon: the copy is the sender's, and the S2 format removes it

Written by the review's lead after the session, from the run logs on the Pi (`~/bench`), the owner's clips, and
the owner's words at the wall. The Pi drove the wall over `eth0`; the card's RAM held the saved settings (960,
x16, blanking 3, Level 3) after a power cycle before the first run. Nothing was written to the card. No repo
file changed; the bench scripts are in `bench/` beside this file and in `~/bench` on the Pi.

Labels: SEEN (the owner's eye at the wall), MEASURED (frames of a clip registered to the LED grid; the script
and the numbers are in the session's scratch folder), CONFIRMED (both, or a fact of the code).

## 1. Verdict in short

1. **The copy exists only while frames arrive.** CONFIRMED. The still picture (a white row at 255 with the
   reference patches, `ghost_map.py 8 --step 0 --row 18`) with the stream stopped for 8 s: the copy vanished
   within one video frame of the stop and returned within one frame of the restart (IMG_5100, 242 frames
   without it). The card holding a frame is clean.
2. **The copy's row is set by the sender's frame rate.** MEASURED at eight rates, our own sync format:

   | Frames a second | 57 | 57.7 | 57.8 | 57.9 | 58 | 58.18 | 59 | 59.5 | 60, 61, 62 |
   |---|---|---|---|---|---|---|---|---|---|
   | Copy, rows below its line | 5 | 2 | 1 | 1 | 1 | 1 | 4 | 3 | wall black |

   No straight line through these; no rate tried put the copy on its own line. At 58 to 58.2 the line is
   doubled (SEEN up close by the owner after the camera had said so).
3. **So it was never a card setting.** Every LEDVision trial of the morning was aimed at the panel; the panel
   is not making it.
4. **In our sync format the card shows nothing above 60 frames a second.** SEEN three times (60, 61, 62), and
   the "one sync a frame" variant is black at 59 too, as the record of 2026-09-29 said.
5. **The S2's format removes the copy.** The spike's imitation of Colorlight's sender card (`send.py --s2`:
   one 1036-byte sync a frame with source type 00, a frame counter, bytes 16 to 18 ff, byte 26 01, the
   declared rate 01 3c, byte 36 00; no brightness packet; row tail 00 00; rows right behind the sync) at
   60.32 frames a second: picture, **no copy on any row** (MEASURED, IMG_5106: the rows above and below the
   line symmetric in every frame), scrolling bars smooth with no flicker or judder (SEEN), the line clean up
   close (SEEN). The same format at 59 is black.
6. **Which parts matter.** Added one at a time to our own format at 60.32 (each 8 to 10 s, SEEN):

   | Added | Result |
   |---|---|
   | declared rate 01 3c | picture above 60 for the first time; copy present; brightness obeyed |
   | + rows right behind the sync | copy |
   | + one sync a frame | copy |
   | + no brightness packet | copy |
   | + row tail 00 00 (alone) | black |
   | + frame counter | copy |
   | + 1036-byte sync | copy |
   | + source type 00 | copy |
   | + byte 26 01 | copy |
   | + byte 36 00 | copy, and **bright**: the level no longer obeyed |
   | + bytes 16 to 18 ff | copy |

   No single element cures it; the whole format does. Two pairs (source type 00 with the row tail; the
   1036-byte sync with the row tail) ran and were not reported by the owner: not settled.
7. **Byte 36 is the brightness switch.** CONFIRMED. With the full S2 format the card ignored the sync's level
   (2 % and 30 % looked the same), ignored our 0x0A brightness packet (2 % and 40 % the same), and ignored
   bytes 16 to 18 (00 and ff the same). With byte 36 put back to 05 the level is obeyed: 2 %, 30 %, 2 % were
   plainly dim, bright, dim (SEEN), the picture still clean, the 0x0A packet not needed.

**The winning configuration**, in the spike sender's terms:

```
send.py --s2 --fps 60.32 --sync-level <brightness> --byte36 05
```

order sync-rows; one sync a frame, 1036 bytes, source type 0x00, counter on, bytes 16-18 ff ff ff, byte 26 01,
bytes 31-32 01 3c, the level byte at 35 from `--sync-level`, byte 36 05; no brightness packet; row tail 00 00.
The picture, the level and the rate are the only inputs.

## 2. The runs, in order

All from `cd ~/codeisart` on the Pi with `sudo .venv/bin/python`, brightness 0.1 unless said. `ghost_map.py`
and `ghost_knobs.py` run through `tools/wall_pattern.py`'s governed path; `send_line.py` (the spike sender
with a line picture) does not pass the governor and showed stills and a slow scroll only, at the owner's word
(`--level-field-proven` for a 255 line of 28 pixels).

| # | Run | The owner, or the clip |
|---|---|---|
| 1 | `ghost_map.py 8 --step 0 --row 18 --seconds 120` | IMG_5097: copy 4 rows below in all 132 frames, never 5; no once-a-second gap; the brightest patches copy 4 rows up (the wrap). By camera the copy matched patch 6 to 7 (15 to 25 %), a rough figure |
| 2 | the same, `--seconds 50 --stop-for 30`, then `--seconds 20 --stop-for 8` twice | IMG_5100: the copy gone for the whole stop, back at the restart. Finding 1 |
| 3 | `ghost_knobs.py --sync-reps 1` | wall black |
| 4 | `ghost_knobs.py --out-fps 60` | wall black |
| 5 | `ghost_map.py` unchanged (control) | picture as before |
| 6 | `ghost_knobs.py` with every knob at the driver's value, twice | picture as before: the wrapper is sound. On the Pi's loopback the bench child and the stock child put the same packets on the wire (`sniff_lo.py`) |
| 7 | sweep 57, 58, 60, 61, 62 (6 to 8 s each), twice | IMG_5101: 57 → +5, 58 → +1; 60, 61, 62 black (SEEN) |
| 8 | 58.1818 (the first rule's prediction of no copy), three times, the last 75 s | IMG_5103 and the owner up close: the line doubled, the brighter patches doubled: +1. The rule was wrong |
| 9 | sweep 59.5, 57.9, 57.8, 57.7, 57.6, 57.5 (5 s each) | IMG_5104 (the first four): 59.5 → +3, 57.9 → +1, 57.8 → +1, 57.7 → +2. 57.6 and 57.5 not reported |
| 10 | `send_line.py --s2 --fps 60.32 --sync-level 0.1 --picture line --pixel 255` (25 s, then 30 s) | IMG_5106: picture, no copy. The owner: brighter than the other runs |
| 11 | the same at `--fps 59` | wall black |
| 12 | the same at 60.32, `--picture scroll --pixel 128`, then the line for 45 s | scroll smooth, no jitter; the line clean up close; "we might've nailed it" |
| 13 | the S2 format, sync level 0.02, 0.3, then 0.1 with `--bright-reps 2` | 1 and 2 the same; 3 no copy, brightness not judged |
| 14 | the S2 format with our brightness packet at 0.02, 0.4, 0.02, 0.4 | all the same |
| 15 | the S2 format with bytes 16-18 at 00 and ff, alternating | all the same (a run with 05 05 05 was refused by the tool's rule: only values seen on a wire) |
| 16 | our format `--declared-rate 013c --fps 60.32` | picture, dim (level obeyed), copy |
| 17 | isolation batch 1: `--order sync-rows`, `--sync-reps 1`, `--bright-reps 0`, `--row-tail 0000`, each on run 16 | copy, copy, copy, black |
| 18 | isolation batch 2 (twice): `--counter on`, `--sync-len 1036`, `--source-type 00`, `--byte26 01`, `--byte36 00`, `--bytes16 ffffff` | copy/dim, copy/dim, copy/dim, copy/dim, copy/**bright**, copy/dim |
| 19 | `--s2 --sync-level 0.1 --byte36 05`; the same `--bright-reps 2`; `--source-type 00 --row-tail 0000`; `--sync-len 1036 --row-tail 0000` (the last two with the declared rate) | the first two, rerun at 15 s: **clean and dim**, and the same with the packet. The pairs not reported |
| 20 | `--s2 --byte36 05` at sync level 0.02, 0.3, 0.02 | dim, bright, dim |

## 3. What this says, and does not say

- The card, fed our 112-byte sync (source type 07, no declared rate), runs a mode that needs each frame to
  last longer than its own 1/60 s and, in that mode, shows a row's data again on another row of the same
  8-row group, the row chosen by how much longer the frame is. Fed the S2's sync it runs a mode that needs
  frames at least as fast as the declared 60 Hz and shows no copy. Which of the S2's bytes select the mode is
  not isolated (finding 6); the format as a whole is what was proven.
- The mechanism inside the card (lane 02's stray row token, or data put out again) was not seen and no longer
  needs to be: the fix does not depend on it. The one-row map (`ghost_map.py 1a`) and the by-eye strength
  match were never run; they are moot for the fix and still available if anyone wants the mechanism.
- Not checked in the S2 format: the held frame (Q66) and what the card shows when the stream stops; the
  close to black; a moving picture from the show or the arcade through the governor; the brightness at the
  cap (0.4); a video for flicker; more than 45 s at a stretch. All of these belong to the driver change.
- The morning's LEDVision trials, the blanking and the multiple, are explained: they never touched the cause.
  The card's RAM is at the saved settings; nothing about the card needs changing for this fault. The blanking
  at 300 ns against the row chip's 500 ns minimum (lane 02) is a separate, small matter.
- The 60.32 rate is the S2's own. Whether 60.0 or 61 also work in this format was not tried; 59 does not.
