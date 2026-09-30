# The wall session of 2026-09-30, late: the paced rows in the driver, on the card

The branch `s2-format` at 47f3f9a (the paced row send: `docs/superpowers/plans/2026-09-30-paced-rows.md`) on the
wall from the Pi, the owner's eyes, the Pi driven over ssh, the driver alone (no bench child, no knobs) except
where a run says otherwise. Nothing was written to the card. The card is set up for 128 x 64, as all evening.

Labels: SEEN (the owner's eye), MEASURED (the sender's own line at the close), CONFIRMED (both, or a fact of the code).

## 1. Verdict in short

1. **The paced driver is what the bench child was.** CONFIRMED: the video "perfect"; the lobby "perfect, one blink
   in 40 s as before"; the line picture no copy; both at level 0.4 "looks great"; the five-minute lobby soak clean
   at the sender (17 999 frames, worst sync 10 us, 0 rows off their slot). Every wall-proven setting stands.
2. **The sync's budget holds with the spin.** MEASURED, every run: worst sync 3 to 12 us, sync-to-sync spread 0 to
   1 us, 0 slips, real-time yes; the paced child never sleeps and nothing stalled it in 8 minutes on the wall.
3. **The show's size on this card, 512 x 192 (384 packets a frame, 40 us slots): the slots hold, the picture
   flickers.** MEASURED: 0 to 4 rows off their slot in 10 s, the worst row 73 us. SEEN: "clean, one flicker" on
   the rgb bands, "clean, more flicker" on the border, at most one at 512 x 64. Two readings, not settled: the
   send's own cost inside a 40 us slot (the border segment had the late rows and the most flicker), or the card
   being handed rows and columns it is not set up for (which the real show wall will not do). The 128 x 64 wall,
   the arcade's, was clean in every run.
4. **The restart's blink is two things, and the copy in it was the prime.** SEEN with the driver (rows first, no
   sync, then the sync a frame later): "very minimal", "big blink with copy", "same". SEEN with a bench child that
   sends the sync first at the restart (no prime): "one little blink/jitter", "a blink", "no blink or the most
   minimal of them all": no copy in any of the three. The copy at the restart is the card's response to rows
   with no S2 sync in front, which is what a prime is. The blink itself is the card's own reaction to a stream
   resuming after 5 s of silence, smaller without the prime, not gone. **Banked by the owner**: "unless it
   becomes a problem later on; don't want to micro-optimize for a rare event" (a restart happens only on a
   cable's return or a dead sender child). The driver keeps its prime; the sync-first restart is a knob in the
   bench child (`GHOST_PRIME=off`) and a one-line change if it is ever wanted.
5. **The show's own soak tool does not fit this card.** `tools/show_soak.py` builds the show at its 512 x 192
   (an 80 x 24 terminal does not fit 128 x 64), so a soak with a 128 x 64 config pushed 2 400 dark frames and
   logged six setup errors; the wall was dark for two minutes. The five-minute soak was the lobby through the
   arcade (`~/bench/arcade_load.py --wall --seconds 300`) instead.

## 2. The runs, in order

All from the Pi (`cd ~/codeisart`, `sudo .venv/bin/python`), level 0.1 unless named, a 5 s dark lead on the owner's
"go". "Sender" is the driver's line at the close: frames, worst sync, rows off their slot (worst row).

| # | Run | Sender | The owner |
|---|---|---|---|
| dry | `wall_pattern.py rgb --dry-run` 10 s, 128 x 64 (no card) | 602, 3 us, 0 (30 us) | |
| dry | the same at 512 x 192 | 628, 11 us, 8 (81 us) | |
| 1 | the video (`bench/direct_play.py video`, rick.mp4, 30 s, no governor) | (the player prints no line) | "It was perfect!" |
| 2 | the lobby (`arcade_load.py --wall`) 40 s | 2399, 8 us, 0 (98 us); 1200 ticks at 30/s | "Perfect! one blink like last time, don't focus on it" |
| 3 | the line picture (`ghost_map.py 8 --step 0 --row 18`), 54 s | 3240, 4 us, 0 (37 us) | "Looks good" (no copy) |
| 4a | `rgb --brightness 0.4` 10 s | 602, 3 us, 0 (35 us) | "Looks great" |
| 4b | the lobby at 0.4, 20 s | 1199, 5 us, 0 (108 us) | "Looks great" |
| 5a | `rgb --width 512 --height 192` 10 s | 608, 7 us, 0 (36 us) | "clean. One flicker" |
| 5b | `border` at 512 x 192, 10 s | 604, 12 us, 4 (73 us) | "clean, more flicker" |
| 5c | `rgb` at 512 x 64, 10 s | 603, 10 us, 0 (29 us) | "clean, no flicker or one I missed" |
| 6.1-3 | the line picture `--seconds 15 --stop-for 5`, three runs | 598 each, 3-4 us, 0 (30-77 us) | "very minimal", "big blink with copy", "same" |
| 7.1-3 | the same through `bench/ghost_knobs.py` with `GHOST_PRIME=off` (the sync first at the restart) | 600 each, 4-5 us, 0 (4-51 us) | "one little blink/jitter", "a blink", "no blink or the most minimal of them all"; no copy |
| 8 | `tools/show_soak.py --config show.soak.toml --backend colorlight --minutes 2` (128 x 64) | no picture: the show does not build at 128 x 64 | a dark wall |
| 9 | the lobby, 300 s | 17999, 10 us, 0 (116 us); 9000 ticks at 30/s, none late; 52 to 64 °C, not throttled | "Looked great. soak went well." |

The Pi's temperature across the session: 51.6 °C idle before, 56 to 62 °C during runs, 64.2 °C at the end of the
five minutes, `get_throttled` 0x0 throughout.

## 3. What this says, and what is open

- The driver's paced send is the evening's bench configuration, on the card, with the same picture and the
  sender's own line proving the timing: the sync within 12 us in every run, no row off its slot at 128 x 64 in
  about 1.5 million packets over the session. The sender spinning its whole frame at real-time priority did not
  stall once in 8 minutes on the wall; the fair server's 50 ms lump did not show. The overnight soak is still the
  proof for hours.
- Open: the flicker at 512 x 192 on a 128 x 64 card (finding 3), to be read again when a card is set up for the
  show's size; the lobby's one blink in 40 s (the owner: not to be chased); the restart's blink (banked).
- The show's soak needs a card at the show's size, or a soak that drives the arcade's wall; tonight's five
  minutes were the latter by hand.
- Bench: `bench/ghost_child.py` gained `GHOST_PRIME` (on: the driver's prime; off: the sync first from the first
  frame); the Pi's `~/bench` copies of `ghost_child.py` and `ghost_knobs.py` are the repo's now (the old
  `~/bench/ghost_knobs.py` had a mangled print line); `show.soak.toml` on the Pi is `show.toml` plus
  `width = 128`, `height = 64`, untracked.
