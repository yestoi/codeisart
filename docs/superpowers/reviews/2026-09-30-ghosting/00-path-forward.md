# The wall's second picture: findings and a path forward

2026-09-30. Five read-only lanes (01 to 05) and a fresh-context adversarial review of the first synthesis
(06), then a session at the wall the same afternoon (07) that settled the question. This file was rewritten
after the session; the first version's run sheet is superseded by section 4. Install date: 2026-11-11.

Labels: CONFIRMED (a primary source or a measurement, cited), LIKELY, SPECULATIVE.

## 1. What the second picture is

- **It is made by the receiver card while frames arrive, and only then.** CONFIRMED at the wall (07, finding
  1): the card holding a frame with the stream stopped shows no copy; the copy returns with the first frame.
- **Its row is set by the sender's frame rate.** CONFIRMED (07, finding 2): 57 frames a second put it 5 rows
  below its line, 58 to 58.2 one row, 59 four, 59.5 three; above 60 the card shows nothing at all in our
  format. This is why the morning's blanking trials and the refresh multiple did nothing that made sense:
  the panel is not making it. Lane 01's measurement that the copy stays in the same column and 8-row group,
  wrapping inside it, and lane 02's that its offset moved between x16 and x4, were both right; the reason
  is that the card's timing, not the panel's wiring, places it.
- **It is not one of the textbook ghosts.** LIKELY (lanes 02, 03, 04 agree, and the wall bears it out).
  Charge-leak ghosts land one scan step away at any setting and are small; this copy moves with timing and
  reaches a tenth or more of its source (lane 01's bound: 2 to 15 % at x16, more at x4).
- **The sender changes no pixel.** CONFIRMED (lanes 01 and 05, code and a run on a list). The card's gamma
  2.8 acts on the bytes as drawn (64 is 2 % of full light, 128 is 15 %, 255 is 100 %).

## 2. The fix, as proven on the bench

**Send frames the way Colorlight's own S2 sender card does, at 60.32 a second, with byte 36 of the sync at
05.** CONFIRMED on stills and a scrolling pattern (07, findings 5 and 7): a clean picture on every row, smooth
motion, no flicker seen, and the brightness level obeyed (2 % against 30 % plainly different).

In the spike sender's terms: `tools/sender_spike/send.py --s2 --fps 60.32 --sync-level <level> --byte36 05`,
that is: rows right behind the sync; one sync a frame of 1036 bytes with source type 0x00, a frame counter,
bytes 16 to 18 ff ff ff, byte 26 01, the declared rate 01 3c at bytes 31 and 32, the level byte at 35, byte
36 05; no 0x0A brightness packet; row packets with the tail 00 00.

What is known about the parts (07, finding 6): the declared rate alone lets the card accept frames above 60;
byte 36 alone decides whether the level is obeyed; no other single element removes the copy, and the whole
format does. The same format at 59 frames a second shows nothing. Which subset is the smallest that works was
not isolated and does not need to be.

Not yet checked in the new format, and part of the driver work: the held frame and the close to black (Q66),
the show at 20 and the arcade at 30 pushed through the steady sender, the level at the 0.4 cap, a
slow-motion video for flicker, a soak.

## 3. What the review got wrong on the way, kept for the record

- The first synthesis read lane 01's "no copy once a second" frames as the copy depending on the moment in
  the sender's frame cycle. The adversarial review (06, I1) showed the 10 Hz rhythm is the beat of the card's
  7680 row slots against 59 frames a second. Either way the copy was the sender's; the wall settled it.
- The first synthesis put the "first 8 rows of a panel take no copy" observation on the data side; lane 02's
  chained-row-chip reading was the better one (06, I2). Moot now.
- Two straight-line rules for the copy's row against the rate were proposed during the session and both
  failed on the next measurement (07, run 8). The mapping is not linear; it did not matter.
- Lane 02's "refresh 1920 gives no copy" and "a step at pixel 199/200" were withdrawn by lane 02 itself.
- Several labels in the first synthesis were stronger than the lanes' (06, I9): the redder copy being the
  camera is LIKELY, not CONFIRMED (lane 01); the blanking 300 ns against 500 ns is CONFIRMED from datasheets
  but that LEDVision's field is that width is LIKELY (lane 03); lane 02's weights were its judgement.
- The first run sheet used the script's default row 2, inside the group lane 01 found exempt from upward
  copies (06, C1). Every wall run used row 18.

## 4. The path forward

1. **The driver.** A safety slice on its own branch, with a plan and an adversarial plan review, as route A
   was: `show/display/colorlight_packets.py` and `colorlight_sender.py` take the S2 sync layout (1036 bytes,
   the fields above, the counter kept per frame), one sync a frame, no 0x0A packet, the row tail 00 00, rows
   behind the sync, `OUTPUT_FPS` 60.32; the level byte stays at offset 35 with byte 36 at 05; `CLOSE_FRAMES`
   follows the rate. `tests/test_colorlight*.py` change with it. The steady sender's hold, restart and close
   logic is untouched. Check on the wall, in this order: `wall_pattern.py rgb` and `border`; the line picture
   (`ghost_map.py 8 --step 0 --row 18`) clean; `--stop-for 5` three times (Q66: the picture stays, no blink,
   and now also no copy); the arcade's lobby and Pong; `wall_video.py`; a 240 fps clip of each; the level at
   0.1 and 0.4; `tools/show_soak.py` for the two-minute and five-minute runs. Then the Pi's overnight soak.
2. **What is closed by it.** The morning's LEDVision trials: nothing on the card needs changing for this
   fault; the RAM is at the saved settings. The software workarounds of lane 05 (a cap, a palette, a dim
   field): not needed. Route C (a sender card): not needed; the driver now speaks the S2's format itself.
3. **Separate, small, still open.**
   - The flash governor's light model against the card's gamma 2.8 (lane 05, section 1.3; LIKELY by
     arithmetic): a swing from 231 to 255 is 24 % of full light on this card and is not counted. The `gamma`
     wall check is the owner's; it is a safety matter apart from the ghost.
   - Blanking Value 3 is 300 ns, under the 500 ns the row chip's datasheet asks for (lane 02, 3.1). A RAM
     trial of 6 in LEDVision some day, judged from the Pi; not urgent.
   - The DP5125's column pre-charge is LIKELY off under "Normal Chip" (lanes 02 and 04); ordinary
     one-row ghosting may exist beside the fault that is now gone. Look for it once the driver is in.
   - The panel supply voltage was never measured; the row chips' marking is unread (lane 02, E1, E4).
   - `hardware.md` on `ledvision-card1` needs the corrections in 07 and in section 3 here; its 10:25 section
     is uncommitted.
4. **The evidence.** The owner's clips of the day are in this session's uploads; the measured frames and the
   scripts are in the session's scratch folder (`v97`, `v100`, `v101`, `v103`, `v104`, `v106`); the bench
   scripts are in `bench/` beside this file and in `~/bench` on the Pi. Nothing here is committed.
