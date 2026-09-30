# The wall session of 2026-09-30, evening: the driver's S2 format on the card, the burst tears, the paced rows

The branch `s2-format` (the driver in the S2 format at 60.32, plan `docs/superpowers/plans/2026-09-30-s2-format.md`)
on the wall from the Pi, the owner's eyes, the Pi driven over ssh. Nothing was written to the card. Bench scripts in
`bench/` beside this file (and `~/bench` on the Pi): `direct_play.py` (pictures straight into the driver, no governor),
`arcade_knobs.py` (the lobby through the arcade with the bench child), `ghost_child.py` (the driver's sender with
knobs: rate, spread, order, counter, sync reps), `ghost_knobs.py` (the line picture with the bench child).

Labels: SEEN (the owner's eye), MEASURED (a clip), CONFIRMED (both, or a fact of the code).

## 1. Verdict in short

1. **The copy is gone.** CONFIRMED: `rgb`, `border`, the line picture (`ghost_map.py 8 --step 0 --row 18`), the lobby, a
   video: no second picture on any of them, with the rows as a burst or paced. The S2 format at 60.32 does what the
   bench said.
2. **The burst tears.** In this mode the card shows rows as they land: a 1 ms burst of rows after the sync shows as
   flicker on natural motion (a video) and on the lobby's moving limbs, and not at all on stills or on whole-field
   translation (bars scrolling at 8 or 60 px/s at 24, 128 or 255; the lobby's still sliding). MEASURED (IMG_5110,
   a 120 fps clip of a bar jumping 32 px a push): 16 of about 170 jumps caught mid-change within one 8 ms frame, the
   old bar solid on the top panels and broken into row groups on the bottom panels with the new bar faint, which is a
   transition of about 1 ms, the burst's length. The same video through main's driver (our format at 59): smooth.
3. **Pacing the rows fixes it.** SEEN: the rows spread over 15.5 ms after the sync, ending about 1 ms before the next
   sync: the video "zero flicker, no weird artifacts, the best playing of the video yet"; the line picture: no copy.
   14 ms: some flicker, acceptable. 16.4 ms (the rows meeting the next sync; the sync 79 us late): worse, slight
   ghosting. The rows first and the sync after (a burst): bad flicker.
4. **60.00, not 60.32, with the paced rows.** SEEN, A/B on the lobby: 60.32 "an acceptable amount of flicker";
   60.00 "near perfect, one flicker in 30 s". The lobby ticks 30 a second, so 60.00 shows every frame twice with no
   3 s hitch, and the sweep stops drifting against the card. With a burst 60.00 and 60.32 were "hard to tell apart":
   the tear dominated.
5. **What did not help.** The sync counter frozen at 0: flicker unchanged. Two syncs a frame: a black wall. 59 in the
   S2 format with the driver: a picture (not black, as yesterday's still was) with shimmer and the copy back. The
   arcade's stack: the video flickered with no governor and no arcade, so it was never the arcade.
6. **A bright blink at a stream restart.** SEEN five times (`--stop-for 5`): the picture holds through the stop, and
   the first frame after the restart is bright for an instant, at the restart, never at the stop. "Not bright enough
   to be a safety concern"; banked. In production only a cable's return or a dead sender child restarts the stream.

**The configuration to build into the driver:** the S2 format as on the branch, `OUTPUT_FPS = 60.00`, the sync on
its deadline, the 64 row packets paced evenly across the 15.5 ms after it (one every 242 us), the last about 1.2 ms
before the next sync. The sender's timing held through every paced run: worst sync 15 to 66 us at real-time priority.

## 2. The runs, in order

All from the Pi (`cd ~/codeisart`, `sudo .venv/bin/python`), brightness 0.1, the branch `s2-format` at 948b2ee
except where main is named. "Sender" is the driver's stats line: frames, worst sync.

| # | Run | The owner, or the clip |
|---|---|---|
| 1 | `wall_pattern.py rgb` 15 s | clean, steady (907 frames, worst 9 us) |
| 2 | `border` 15 s | clean, steady (worst 5 us) |
| 3 | the line picture 20 s | clean, steady: no copy on row 18 (worst 9 us) |
| 4 | the line picture `--stop-for 5`, five runs | held through the stop; a bright blink at the restart every time |
| 5 | the lobby (`arcade_load.py --wall`) 40 s | "some flickering" (30 ticks a second held; worst 25 us) |
| 6 | the lobby at 60.00 (bench child) | flicker |
| 7 | the lobby at 59 | "wasn't great: shimmering and ghosting" (a picture, not black) |
| 8 | the lobby at 60.32, counter frozen | flicker (IMG_5109 at 30 fps: inconclusive, the phone hunting focus) |
| 9 | A/B the lobby 60.32 then 60.00 | "hard to tell a difference; if I had to pick, 60.32" |
| 10 | `direct_play.py video` (rick.mp4) 30 s, no governor | flicker |
| 11 | the video, two syncs a frame | black |
| 12 | `scroll` 128 at 8 px/s; at 255; at 60 px/s; `slide` (lobby.png 10 px/s); `scroll` at 24 | smooth, no flicker, all five |
| 13 | the video through **main's** driver (our format, 59) | "no flicker this time" |
| 14 | `vframe` (one video frame held) | no flicker |
| 15 | `noise` (every pixel random each push) | no flicker (uninformative) |
| 16 | `toggle` (a band at 128, the black going to 12 every push); the same through main | "only the background" flickers, both drivers (the 12 visible in both) |
| 17 | `jump` (a bar 32 px further every push) 15 s, IMG_5110 at 120 fps | finding 2: transitions of about 1 ms, split frames; an extra repeated push every 3.1 s (the 60.32/30 beat) |
| 18 | the video, rows spread over 14 ms | "some flicker, but an acceptable amount" |
| 19 | the video, rows first then the sync (a burst) | "bad flicker" |
| 20 | the video, rows spread over 15.5 ms | "zero flicker, no weird artifacts, the best playing of the video yet" |
| 21 | the lobby, 60.32, spread 15.5 | "flicker, but an acceptable amount" (worst 14 us) |
| 22 | the line picture, spread 15.5 | no copy |
| 23 | the lobby, 60.32, spread 16.4 | "slight ghosting, the flicker worse" (the sync 79 us late) |
| 24 | the lobby, 60.00, spread 15.5 | "near perfect, one flicker towards the end" |
| 25 | A/B the lobby 60.32 vs 60.00, both spread 15.5 | 60.00 the cleaner |

## 3. What this says, and what is open

- The S2 mode of the card is single-buffered as far as the wire can tell: rows show as they arrive. Colorlight's
  own S2 feeds the card from a scanning video input, so its rows arrive spread across the frame in scan order; a
  sender that bursts them must pace them itself. Our old format (source type 07) latched a whole frame on the sync,
  which is why the burst never mattered before and why the prime logic worked.
- The row pacing is a timing change only: the bytes of the branch stand. The sender can pace 64 sends over 15.5 ms
  inside its existing tick (a wait before each row, as `ghost_child.py` does) and still put the sync within its
  100 us; the paced runs' worst syncs were 14 to 66 us. The pacing's budget: the last row must land with margin
  before the next sync (16.4 ms of a 16.67 ms period was too close); 15.5 at 60.00 leaves 1.2 ms.
- Open: the lobby's last flicker in 30 s at 60.00 (a 240 fps clip at fixed exposure would place it); the restart's
  bright blink (whether the paced rows change it is untested); the show's 512-wide wall with two row packets a row
  (128 paced sends a frame, one every 121 us); levels 0.1 and 0.4; `wall_video.py`; the soaks; whether the prime
  (rows with no sync) should be paced too (it is now a burst before the first sync).
- Yesterday's "dip every 3 to 6 s at 60.32" (S8b) was most likely this tear on the scrolling bars' edges, or the
  60.32/30 beat; it is moot at 60.00 with paced rows.
