# The wall session of 2026-09-30, night: the wall in its frame, the proven runs again

The owner had moved the wall into its frame. The Pi drove the wall over ssh on main at 7ffb4b6, the paced
driver of session 09. Everything committed after 7ffb4b6 is docs, tooling config and the operator's hook test,
so the driver was the one session 09 proved. The Pi was rebooted about 22:29 for the move, and the card was
power-cycled with it. The card's link came up at 22:33:43. Same card and same cable as session 09 (the owner).
Nothing was written to the card. The card is set up for 128 x 64.

Labels: SEEN (the owner's eye), MEASURED (the sender's own line at the close, or a probe), CONFIRMED (both).

## 1. Verdict in short

1. **The wall in its frame passes.** CONFIRMED: rgb and border good, the video "perfect", the lobby stable three
   times, the line picture with no copy and no shimmer, level 0.4 good, and the five-minute lobby soak "clean
   the whole five minutes". Every sender line sat in session 09's band: worst sync 2 to 15 us, 0 rows off their
   slot in every run.
2. **One run shimmered and never came back.** SEEN: the first lobby after the reboot, at 22:39:39, about nine
   minutes after boot. It was the boot's first arcade run and came straight after the video. "Everything lit
   flickers", "fast shimmer, by eye", "from the start, steady", no copy. MEASURED: the sender was clean in that
   run (2399 frames, worst sync 13 us, 0 rows off their slot). Three lobbies after it were clean, one of them in
   the same order (the video, 25 s of dark, the lobby), and so was the soak.
3. **What the evidence rules out.** The Pi's software: the same code, script, config, level and no knobs as the
   clean afternoon soak. The picture: a dry probe showed the level set once, the brightest byte 255 in every
   frame, the lit pixels steady, and only the lobby's own breathing. Greys on the card: the steps and gamma
   stills were clean. The arcade process against its picture: the still lobby picture, with no arcade, was
   clean. The Pi's load: a burst load on cores 0 to 2 beside the still changed nothing. The DHCP retries on the
   card's link: none fell inside the shimmering run. The kernel logged nothing and the Pi never throttled.
4. **The owner's reading: a first-boot quirk of the Pi that goes away after about 10 minutes of runtime.** It
   rests on one sighting. The runbook (`docs/runbooks/wall-shimmer.md`) records the uptime every time, so the
   next sighting confirms or refutes it. Still open beside it: how the card picked up that one stream start
   (no copy was seen, so the card's old mode is less likely), and an intermittent fault in the frame's wiring.

## 2. The runs, in order

All from the Pi, level 0.1 unless named, a 5 s dark lead on the owner's "go". "Sender" is the driver's line at
the close: frames, worst sync, rows off their slot (worst row). `direct_play.py` prints no sender line.

| Time | Run | Sender | The owner |
|---|---|---|---|
| 22:36:02 | dry: `wall_pattern.py rgb --dry-run`, 5 s | 299, 8 us, 0 (4 us) | |
| 22:37:53 | `rgb`, 10 s | 602, 3 us, 0 (13 us) | "good" |
| 22:38:07 | `border`, 10 s | 602, 3 us, 0 (34 us) | "good" |
| 22:38:37 | the video, `direct_play.py video`, 30 s | 900 pushed in 31.0 s | "Great. perfect" |
| 22:39:39 | the lobby, `arcade_load.py --wall`, 40 s | 2399, 13 us, 0 (67 us) | "flickering", "everything lit", "fast shimmer, by eye", "from the start, steady" |
| 22:41:43 | dry: the lobby, 20 s | 1199, 12 us, 0 (51 us); 600 ticks, 0 late | |
| 22:45:45 | dry: the lobby probe, 20 s (below) | 1199, 11 us, 0 (92 us) | |
| 22:47:37 | `steps`, 10 s | 602, 4 us, 0 (26 us) | "No flicker" |
| 22:47:51 | `gamma`, 10 s | 602, 4 us, 0 (30 us) | "No flicker" |
| 22:49:57 | the lobby, 20 s | 1199, 8 us, 0 (61 us); 600 ticks, 0 late | "good" |
| 22:50:22 | the still lobby picture (`direct_play.py slide --speed 0.001`), 20 s | 600 pushed | "good" |
| 22:50:47 | the same still, 25 s, with `burst_load.py` 22:50:55 to 22:51:05 | 750 pushed | "good too" |
| 22:53:17 | the lobby, 40 s | 2399, 13 us, 0 (65 us); 1200 ticks, 0 late | "clean" |
| 22:54:45 | the video, 30 s, then 25 s dark | 900 pushed | |
| 22:55:41 | the lobby, 40 s | 2399, 11 us, 0 (89 us); 1200 ticks, 0 late | "stable this time" |
| 22:57:19 | the line picture (`ghost_map.py 8 --step 0 --row 18`), 54 s | 3242, 3 us, 0 (20 us) | "no copy, no shimmer" |
| 22:58:37 | `rgb --brightness 0.4`, 10 s | 602, 2 us, 0 (32 us) | not flagged |
| 22:58:51 | the lobby at 0.4, 20 s | 1199, 15 us, 0 (74 us); 600 ticks, 0 late | "blinked a few times, within acceptable levels, not a shimmering" |
| 23:00:30 | the soak's first start | none: the operator's command ran the lobby from the wrong folder, so nothing went to the card | "I'm not seeing anything" |
| 23:02:42 | the lobby, 300 s | 17999, 14 us, 0 (156 us); 9000 ticks, 0 late; 3013 inferences, 10 a second; 65 % of one core | "clean the whole five minutes" |

The Pi's temperature: 38 °C before the first run, 60 to 66 °C through the soak. `get_throttled` read 0x0
throughout.

The lobby probe at 22:45:45 measured 600 frames. The card's level was set once, to 0.1. The brightest byte was
255 in every frame with no change. 551 pixels were lit, with one change as the figure appeared. The mean light
rose and fell between 7.50 and 7.87 of 255 once a second: the lobby's breathing, present in the clean soaks too.

## 3. What this says, and what is open

- The frame did not move the picture: the stills, the video, the line picture and the soak match session 09.
  Every wall-proven setting stands.
- The one shimmer is the open item. The sender's line was healthy during it, so the stream left the Pi clean.
  The fault was past the Pi or in how that one stream started. The owner's reading is a first-boot quirk.
  `docs/runbooks/wall-shimmer.md` is the play for the next sighting, with `bench/wall_triage.sh` (`~/wall_triage`
  on the Pi) running every step.
- The lobby's few blinks at level 0.4 are accepted, like the one blink in 40 s of session 09.
- Found on the way: the Pi's clock came up at 18:25 at boot, the time of its last shutdown, and jumped to 22:30
  when NTP synced. The Pi 5's clock keeps time through a power-off only with an RTC battery. Without one, at a
  site with no network, the clock is wrong after every power cycle. The arcade's night brightness cap and the
  show's quiet hours both read the local clock.
- Not causes, recorded so they are not chased again: NetworkManager retries DHCP on `eth0` every 45 s, four at a
  time, then rests for 5 minutes (left alone since 2026-09-30, it is the way in if Wi-Fi fails). A `systemd`
  process at 56 % CPU in `ps` was the measuring ssh session's own user manager, seconds old.

## 4. Bench added this session

In `bench/`: `wall_triage.sh` (the runbook's steps: `state`, `probe`, `sweep`, `video-lobby`, `soak`, `checks`;
`DRY=1` sends every step nowhere), `lobby_probe.py` (the lobby dry, every frame measured), `burst_load.py` (a
bursty load on cores 0 to 2, never the sender's core 3), and `arcade_load.py` (the lobby under the arcade on the
Pi; until now only in `~/bench` on the Pi). The media stay on the Pi in `~/bench`.
