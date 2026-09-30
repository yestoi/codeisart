# Route A: the steady sender on the bench, and at the wall

The driver of `show/display/colorlight.py` after the spec of `docs/superpowers/specs/2026-09-29-route-a-steady-sender-design.md`
and the plan of `docs/superpowers/plans/2026-09-29-route-a-steady-sender.md`. Labels as the spike's: MEASURED, SEEN, OPEN.

## 1. The bench: the Omarchy box, no card (2026-09-29, late evening)

`tools/wall_pattern.py grid --dry-run --seconds 30`: the driver with a socket that keeps nothing, the child process
running the sender, the tool pushing at `--fps`. Ordinary priority (`ulimit -r` is 0 for the user; SCHED_FIFO needs the
sudo hour or CAP_SYS_NICE). Python 3.12.14, kernel 7.2.3-arch1-3, 20 cores. MEASURED by the sender's own stats
(`ColorlightDisplay.stats()`: the sync's time by `perf_counter_ns` as the child handed the packet over, not the port's
clock).

| Pushes a second | Frames in 30 s | Late (over 1 ms) | Worst, us | Sync to sync sd, us | Slips |
|---|---|---|---|---|---|
| 20 | 1770 | 0 | 207 | 7 | 0 |
| 30 | 1770 | 1 | 2092 | 50 | 0 |

1770 frames in 30 s is 59.00 a second in both runs, whatever the push rate. The second run's one frame 2.1 ms late is the
"ordinary priority is a gamble" of the spike's step 6 (0.2 to 0.8 ms late once in a while there).

Under sudo (2026-09-30, about 04:20; the child took SCHED_FIFO 50 itself, `real-time yes`), MEASURED the same way:

| Pushes a second | Seconds | Frames | Late (over 1 ms) | Worst, us | Sync to sync sd, us | Slips |
|---|---|---|---|---|---|---|
| 20 | 30 | 1770 | 0 | 222 | 7 | 0 |
| 30 | 60 | 3540 | 0 | 297 | 10 | 0 |

The sd matches the spike's sender at real-time priority (3 to 5 us there, by the port's clock). The worst, a single
sync 200 to 300 us late in a run, is above the spec's 100 us; the spike's own runs had the same outliers (N15b, judged
"our most stable presentation yet", had a worst of 746 us; N11 702, N13b 611) and were judged steady, and 0.25 ms of
jitter on *every* frame (N21) is what showed. INFERENCE: the sleep waking past its 2 ms margin now and then; a wider
spin margin would absorb it at more CPU. To watch on the Pi, not tuned here.

The driver's tests pass on the box (119 of the driver's, the tool's and the soak's), the child a real subprocess there.

### The lone late sync, chased (2026-09-30, about 04:40 to 05:00)

At the wall (section 2) the owner noticed the one sync 849 us late in a 60 s run of `grid`. MEASURED on the box, dry
runs of 60 s at real-time priority, the sender's stats and a new one, how late the sleep woke:

| The child | Worst, us | sd, us | The sleep woke at worst, us late |
|---|---|---|---|
| unpinned, spin 2 ms | 365 | 10 | 445 |
| unpinned, spin 4 ms | 274 | 8 | 332 |
| pinned to core 19 by taskset (the parent too) | 36 | 2 | 563 |
| pinned itself to core 19 (the parent free), run 1 | 259 | 6 | 723 |
| pinned itself, run 2 | 32 | 2 | 979 |
| both by taskset, run 2 | 714 | 18 | 187 |
| pinned itself, run 3 | 194 | 7 | 491 |
| both by taskset, run 3 | 254 | 6 | 370 |

The sleep is not it: it never woke later than its 2 ms margin. The stall is inside the busy-wait, at SCHED_FIFO 50,
a few hundred microseconds about once a minute, and pinning does not remove it reliably (INFERENCE: a machine-level
event, an SMI or an interrupt on that core; `/sys/kernel/debug/x86/smi_count` is not readable here). The spike's own
good runs had the same outliers (N15b 746 us, N13b 611 us) and the same "a couple of dips" verdicts. The child now
pins itself to the highest core it may use (`sender_cpu`), which is harmless and was decisive in two runs of four.
OPEN: the same measurement on the Pi 5, whose stalls will be its own.

## 2. At the wall (2026-09-30, about 04:25 to 05:20)

The owner at the wall, the LEDVision VM off (`vm.py status`: shut off), the port up at 1000 Mb/s, sudo for the hour.
Every run `tools/wall_pattern.py` on the Omarchy box, `--iface enp5s0 --brightness 0.1`, the child at SCHED_FIFO 50
(`real-time yes` in every stats line), the tool pushing at its default 20 unless said. The owner's words as typed.

| Run | What | Frames | Worst, us | sd, us | The owner's words |
|---|---|---|---|---|---|
| 1 | `rgb`, 20 s | 1180 | 121 | 5 | "Nice and steady. Full picture. Rgbw" |
| 2 | `grid`, 60 s, pushes at 20 | 3540 | 849 | 21 | with run 3: "I didn't notice a difference between the two. I think I did notice the outlier" |
| 3 | `grid`, 60 s, pushes at 30 | 3540 | 333 | 8 | as run 2 |
| 4 | `grid --stop-for 5`, 20 s (Q66) | 885 | 24 | 3 | "Do it again, I'll count this time" |
| 5 | the same | 885 | 24 | 2 | "Yes [the picture holds], just the slightest blink at stop and restart" |
| 6 | `grid`, 60 s, the cable pulled at ~39 s | 2321 | 116 | 5 | `send` raised errno 105 (No buffer space available) at once; the tool quit, by design. "Image kept stable. Maybe a little blink on disconnect, but I'd have to do it again to confirm" |
| 7 | the same, the cable pulled at ~16 s | 919 | 22 | 2 | errno 105 again. "Held steady. The slight stuttering I saw was me moving the Ethernet plug as I was disconnecting. So I'm blaming the cheap Ethernet port" |

What the session settled:

- **The rgb check** (plan Task 11, step 1): red, green, blue, white from the left: the BGR swap is right, the governor
  judges the colours the wall shows. SEEN.
- **Steady by eye at 20 and 30 pushes** (step 2): no flicker, no noise, no difference between the show's and the
  arcade's rate. SEEN. The one sync 849 us late in run 2 was noticed ("I think"): the lone late sync is worth its
  chase (section 1) and the Pi's own measurement.
- **Q66 at 59** (step 3): the card keeps its picture through a stopped stream, steady, with "just the slightest blink"
  at the stop and at the restart. SEEN, twice. The blink is the card's reaction to its stream stopping and starting,
  not the driver's (a dead link stops the stream the same way), so the paused hold stands as decided; a hold costs
  two slight blinks a second apart, and holds come from a dead link.
- **The cable pulled** (step 4): `send` raises at once with the link down (errno 105 through `PACKET_QDISC_BYPASS`),
  so the hold logic sees a dead link and no carrier watch is needed (spec section 4's follow-up is closed). The card
  held its picture steady with the cable out. What happens when the cable returns was not seen: the tool quits at
  the first failure by design; the show's loop holds and carries on (a `--hold` for the tool would show it). OPEN.
- **The 240 fps clip** (step 5): not made tonight. OPEN.

## 3. The Pi 5 (2026-09-30, about 08:15 to 08:36)

The show's target: a Raspberry Pi 5 Model B Rev 1.1, 8 GB, 4 cores, Raspberry Pi OS Lite 64-bit (Trixie, the
2026-09-15 image), kernel 6.18.50+rpt-rpi-2712 (PREEMPT, `CONFIG_HZ=250`, `CONFIG_RT_GROUP_SCHED` not set), Python
3.13.5, main at 8a54a91. The card on the Pi's own port, `eth0`, up at 1000 Mb/s; SSH over Wi-Fi.

### Dry runs, no card

`tools/sender_spike/send.py --dry-run --fps 59 --order sync-rows --seconds 30`, ordinary priority, the Pi idle: 1769
frames, every one within 20 us of its tick; the sync after its tick mean 0.3 us, worst 1.4 us. MEASURED.

`tools/wall_pattern.py grid --dry-run`, MEASURED by the sender's stats as in section 1. "Busy" is four shell loops
spinning, one a core: a stand-in for load, not the arcade.

| The Pi | Priority | Pushes a second | Seconds | Frames | Late (over 1 ms) | Worst, us | sd, us | The sleep woke at worst, us late |
|---|---|---|---|---|---|---|---|---|
| idle | ordinary | 20 | 30 | 1770 | 0 | 5 | 0 | 74 |
| idle | real-time (sudo) | 30 | 60 | 3540 | 0 | 5 | 0 | 10 |
| busy | ordinary | 30 | 60 | 3540 | 834 | 4001 | 1160 | 4992 |
| busy | real-time (sudo) | 30 | 60 | 3542 | 0 | 3 | 0 | 8 |

Idle, the Pi is steadier than the Omarchy box (a worst of 5 us against the box's 200 to 300), and no lone late sync
came in these runs; they are 30 to 60 s each and the box's came about once a minute, so longer runs would say more.
Real-time priority is not optional on the Pi: with the cores busy and ordinary priority a quarter of the frames were
late. With it the load does not show. About 61 C after two minutes of the four busy cores, `vcgencmd get_throttled`
0x0.

The driver's and the wall tool's tests pass on the Pi (302 passed, 119 s). The full suite on the Pi, run beside the
wall runs below: 1735 passed, 2 skipped, 6 failed, 766 s (321 s on the Mac). All six are the flash governor's 0.5 ms
budget (`tests/arcade/test_flash.py::test_governor_under_half_ms_at_128x32` and five of
`tests/arcade/test_headless.py::test_tick_budget_with_the_governors_share`), not the driver. Run again on the idle Pi,
five of the six still fail. MEASURED there, the governor's median a tick:

| Wall | static, ms | strobe, ms | The whole tick, mean, ms |
|---|---|---|---|
| 128x32 | 0.455 | 0.500 | 0.9 to 1.0 |
| 64x64 | 0.519 | 0.585 | 1.0 to 1.1 |
| 128x64 | 0.948 | 1.043 | 1.5 to 1.6 |

The whole tick is inside its 2 ms budget at every size. The governor alone is about twice its 0.5 ms at the arcade's
128x64. The owner's to settle: the budget was met on the Mac; on the Pi 5 either the governor gets faster or the
budget is set for the Pi. Settled the same morning, after the test below (Q79): the budget is set for the Pi,
`ARCADE_GOVERNOR_BUDGET_MS=2` there, 0.5 where it is not set; the Pi's numbers are in
`docs/superpowers/workflow/evidence/pi-perf.md`.

### A slower governor, tested (08:46 to 08:50)

The owner's question: would a budget set for the Pi bring the flicker back? A bench script (not kept in the repo)
ran `wall_pattern.py`'s own loop, governor, driver and close with a moving picture, a 3 pixel bar sweeping 30 pixels
a second inside the border, and after every push busy-waited some milliseconds more: a governor that much slower.
15 s a run, 30 pushes a second asked, real-time priority. MEASURED, dry and then on the wall at brightness 0.1:

| Added a push, ms | Where | Pushes a second | Frames | Late (over 1 ms) | Worst, us | sd, us | Governor median, ms |
|---|---|---|---|---|---|---|---|
| 0 | dry | 30.0 | 887 | 0 | 7 | 1 | 1.42 |
| 1 | dry | 30.0 | 887 | 0 | 4 | 0 | 1.42 |
| 5 | dry | 30.0 | 887 | 0 | 5 | 1 | 1.34 |
| 20 | dry | 30.0 | 887 | 0 | 6 | 0 | 0.97 |
| 40 | dry | 24.4 | 885 | 0 | 12 | 1 | 0.97 |
| 0 | the wall | 30.0 | 887 | 0 | 18 | 1 | 1.45 |
| 20 | the wall | 30.0 | 887 | 0 | 7 | 1 | 1.00 |
| 40 | the wall | 24.4 | 886 | 0 | 7 | 0 | 0.98 |

The sender does not see the governor: it is another process, at real-time priority, and its sync held in every run,
the 40 ms ones with them. What a slow governor costs is pushes, and only once the whole tick passes the 33 ms of a
frame: at 40 ms added the loop made 24.4 pushes a second. Asked whether the picture was steady in each run and
whether the bar moved differently in the third, the owner: "yes to both". SEEN: no flicker at any of the three, and
the lost pushes show as motion, not as flicker. In a paced loop the governor costs about 1.4 ms a frame on the Pi
(1.0 when the core is kept busy), so it would have to be some twenty times slower before a push is lost.

### At the wall, from the Pi (08:28 to 08:36)

The owner at the wall. `sudo .venv/bin/python tools/wall_pattern.py <pattern> --iface eth0 --fps 30`, brightness 0.1,
`real-time yes` in every stats line, no send errors, no slips. The full test suite was running on the Pi beside all
three runs. The owner's words as typed.

| Run | What | Frames | Worst, us | sd, us | The owner's words |
|---|---|---|---|---|---|
| 1 | `grid`, 60 s | 3542 | 9 | 1 | "Looks good. However, if there is supposed to be a line around all edges, that wasn't the case" |
| 2 | `grid`, 20 s, photographed | 1182 | 8 | 1 | "There is no line at the bottom and right sides" |
| 3 | `border`, 30 s | 1772 | 9 | 1 | "Looked great" |

`grid` starts its lines at pixel 0, so its last row and column are dark by design; the photograph shows 16 cells by
8, the top and the left edge lit, the lines unbroken across the seams. `border` (new that morning) lights all four
edges, the last row and column with them. SEEN.

### In the unit, under the arcade, and long (09:05 to 09:34)

Dry runs, no card. Each ran in a transient systemd unit with `deploy/show.service`'s settings (`systemd-run` with
`User=trey`, `ProtectSystem=strict`, `ReadWritePaths=` the entries, `PrivateTmp=yes`, `AmbientCapabilities=CAP_NET_RAW
CAP_SYS_NICE`, the groups audio and gpio): the ordinary user, no sudo inside. `real-time yes` in every stats line:
the unit's ambient capability is enough, as the kernel's `CONFIG_RT_GROUP_SCHED` not set promised. MEASURED.

"The arcade" is a bench script (`~/bench/arcade_load.py` on the Pi, not kept in the repo) that builds what
`arcade.main.run` builds: the lobby, every game, the runner's loop at 30 ticks a second, the governor, and the real
`MediaPipeCamera` with the lite pose model in its thread. The Pi has no camera yet, so the camera's frames are one
still photograph of a person (640x480, 30 a second); `mediapipe` 1.0.1 was installed into the Pi's venv by hand and
the model copied to `models/`, neither is in `.[pi]` or the README. The display is the driver on a socket that
discards.

| Run | Seconds | Ticks a second | Late ticks | A tick, ms (median, p95, max) | Pose a second | An inference, ms (median, p95, max) | Frames | Late (over 1 ms) | Worst, us | sd, us |
|---|---|---|---|---|---|---|---|---|---|---|
| the arcade, pose asked at 10 a second | 600 | 30.00 | 0 | 2.3, 3.3, 10.8 | 10.0 | 56.0, 66.9, 80.8 | 35400 | 0 | 36 | 4 |
| the arcade, pose asked at 30 a second | 120 | 30.00 | 0 | 2.5, 3.5, 5.1 | 17.3 | 56.2, 63.9, 85.8 | 7080 | 0 | 30 | 4 |
| `wall_pattern.py grid --dry-run`, idle | 600 | (30 pushes) | | | | | 35400 | 0 | 10 | 0 |

What they say:

- **The lone late sync did not come.** Ten minutes idle: a worst of 10 us. The Omarchy box's came about once a
  minute at 200 to 800 us; the Pi showed none in 35400 frames, twice.
- **Under the arcade the sync holds.** A worst of 36 us in ten minutes, against the 100 us the spike asked for, with
  the pose model taking two thirds of a core beside the loop (the process 65 % of one core; 106 % when asked for 30).
- **The loop holds 30 ticks a second** beside the pose thread; no tick was late.
- **The lite pose model takes 56 ms an inference on the Pi 5**, so 10 a second holds and 30 does not: asked for 30
  it made 17.3. Whatever wants the camera faster than about 17 a second on this Pi needs another model or another
  path.
- **Limits of the run:** the photograph stands still, so the arcade stayed in its lobby (`invite` at the end) and no
  game was played; the games' own cost is the tick budget's (about 1.5 ms, `evidence/pi-perf.md`). No camera was
  read: a USB camera's capture and decode are not in these numbers. 51 C at the end, not throttled.

**What the Pi sends the card besides the driver's packets** (09:31, three minutes, `tcpdump -Q out` on `eth0`, no
sender running): 24 frames, all the Pi's own housekeeping. 7 DHCP requests, 6 IPv6 router solicitations, 6
multicast listener reports, 4 mDNS announcements over IPv6, 1 neighbour solicitation; the card answered nothing. At
1000 Mb/s the longest (329 bytes) holds the wire under 3 us, so a sync that leaves behind one is late by that at
most, and every wall run above was steady with them going on. Left as it is: DHCP on `eth0` is the way in if Wi-Fi
fails. MEASURED; whether the card minds these frames is SEEN only as the steady wall.

### At the wall again, from the Pi (09:36 to 09:42)

The owner at the wall, brightness 0.1, real-time priority in every run, no send errors, no slips.

| Run | What | Frames | Late | Worst, us | sd, us | The owner's words |
|---|---|---|---|---|---|---|
| 1 | `send.py --iface eth0 --qdisc-bypass --stamp --fps 59 --order sync-rows`, 20 s, under `chrt -f 50` | 1180 | 0 | (below) | | steady: "yes" |
| 2 | `grid`, 60 s, pushes at 20 | 3540 | 0 | 8 | 1 | steady: "yes" |
| 3 | `grid --stop-for 5`, 20 s (Q66) | 885 | 0 | 11 | 1 | the picture stayed: "yes, did not see a blink (but would need to see again to confirm)" |
| 4 | the arcade (`arcade_load.py --wall`), 60 s | 3540 | 0 | 39 | 5 | a video, from the replay |
| 5 | the same, 90 s, filmed | 5310 | 0 | 42 | 5 | the video, 3.5 s |

- **The kernel's stamps** (run 1, MEASURED): sync to sync at the driver 16.949 ms, sd 1 us, every interval 16.933 to
  16.957 ms; the sync 0.3 us after its tick (worst 0.5); the port sent 84252 packets during the run, all the
  sender's, and its queue held none. The spike asked for the sync within 100 us: the Pi holds it within 20.
- **20 pushes and Q66 from the Pi:** as from the Omarchy box. SEEN. On the box the owner saw "the slightest blink"
  at the stop and the restart; from the Pi none, to be seen once more.
- **The arcade on the card:** 30 ticks a second, none late, the pose model at 10 a second beside it, the sync worst
  at 39 and 42 us.
- **A faint second picture on the wall** (the video, SEEN in its frames): beside the lobby's orange figure a dimmer,
  redder copy of its arms and legs, a few rows lower, the same in every frame of the video. It is not in what the
  Pi sends: of the last 150 frames the arcade pushed in a dry run, every lit pixel was lit in all of them and the
  figure is drawn once. So it is made at the panel. INFERENCE: the row ghosting that
  `docs/superpowers/reviews/2026-09-29-flicker/03-panel-electrical.md` section 2.4 expects from the card's saved
  Blanking Value of 3 (300 ns, under the ICND2018's 500 ns), and its first change in section 2.6: blanking 3 to 6,
  then 11. A card setting, through LEDVision; not the driver's and not the Pi's. The owner: "I see it by eye."

### The second picture chased in LEDVision, and a video from both machines (09:50 to 10:11)

The card's cable on the Omarchy box, LEDVision's grid of single white rows 16 apart, paused, at the card's saved
Level 3 (23%). The owner sees the fainter copy under each line there too, at the saved settings: so it is not the
Pi's and not the Linux sender's. Four settings of the row driver, each sent to the card's RAM only, changed
nothing to the owner's eye: Blanking Value 3 to 6 ("looks the same, may be weaker") and to 11 ("still the same"),
the ICN2018/3018 page's Blanking Enhancement on ("still the same"), its Blanking Voltage 3.25 V to 2.0 V ("still
the same"); 3.75 V was sent and not judged. The inference above is therefore wrong as to the cure: blanking is not
it. The owner stopped the trial ("I don't think we're getting anywhere"; LEDVision's own stream is hard to tune
by). The settings were put back and sent, nothing was saved to the card's flash, the VM shut off. The record, and
an untested reading of the copy's place (the row lit next, if the panel scans 0, 4, 1, 5, 2, 6, 3, 7), is in
`hardware.md` on the branch `ledvision-card1`.

Then the same video (`rick.mp4`, 640x360 at 25 frames a second) by `tools/wall_video.py`, 60 s, brightness 0.1,
pushes at 30: first from the Omarchy box by the owner (its numbers not kept), then from the Pi (10:10): 1798 frames
shown, 206 ticks held by the governor, the sender 3541 frames, 0 late, worst 15 us, sd 4 us, real-time yes. The
owner: "looks the same on both". SEEN: the Pi shows what the Omarchy box shows.

### The second picture without the arcade (10:16)

The owner's question: earlier animations were smooth with no second picture, so is it the arcade's? Four pictures
from the Pi with no arcade behind them, by `wall_pattern.py`'s own run (a bench script, `~/bench/ghost_test.py`),
20 s each, brightness 0.1, each numbered on the wall; the sender clean in all four (worst 4 to 11 us).

| Picture | What | The owner, and his photographs |
|---|---|---|
| 1 | the lobby's frame as the arcade pushed it, standing still | the second picture is there (photographed) |
| 2 | the same frame sliding sideways, 10 pixels a second | there |
| 3 | a white bar sweeping inside the border, pixel value 128 | "smooth, no ghosting" |
| 4 | two-row lines at pixel values 64, 128 and 255, orange above and white below | photographed: none under the 64s, a trace under the 128s, a plain copy under the 255s, 4 rows down |

SEEN: it is the picture, not the arcade. The copy grows with the pixel's value, and steeply: nothing at 64, little
at 128, plain at 255. The lobby draws its figure at (255, 120, 0), so its red channel is at the top and the copy is
red; `wall_pattern.py`'s patterns are drawn at 128 and a video sits mostly in the middle values, which is why they
looked clean. INFERENCE, not tested: a copy that comes only with the high values fits the card's grey-scale
timing (the longest light pulses of a row still on when the next row is lit) better than a fixed leak, and points
at the refresh rate, its multiple and the grey mode, not at the blanking. The same photograph shows (255, 120, 0)
as red, not orange: the card's gamma of 2.8 is applied to bytes the arcade sends as if none were (`arcade.toml`
`gamma = 2.2`), which is the `gamma` wall check, still the owner's.

OPEN on the Pi:

- Q66 seen once more from the Pi, for the blink.
- A game played through a real camera: the Pi has none attached.

CLOSED the same afternoon, and not the wall's: the fainter second picture is the card's response to our sync
format. The wide review and the wall session of 2026-09-30 are in `docs/superpowers/reviews/2026-09-30-ghosting/`
(`00-path-forward.md`, `07-wall-session.md`). In short: the copy exists only while frames arrive (the card holding
a frame is clean), its row is set by the sender's rate (57 fps: 5 rows below; 58: 1; 59: 4; 59.5: 3; 60 and
above: our format shows nothing), and the S2 sender card's sync format at 60.32 fps with byte 36 at 05 shows a
clean, smooth, dimmable picture. The driver change that follows is a safety slice; the "grows with the pixel's
value" reading above was the card's gamma 2.8, not a property of the copy. Nothing on the card needs changing.
