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

OPEN on the Pi:

- `send.py --stamp` on the link (the kernel's stamps): not run, the wall runs came first.
- Runs longer than 60 s, for the lone late sync.
- The driver under the arcade itself, not a stand-in load.
- Real time under the systemd unit: the kernel allows it; `real-time yes` in the unit's log is not yet seen.
- The 20 pushes run and Q66 (`--stop-for`) from the Pi.
- NetworkManager asks `eth0` for DHCP every 45 s and its packets reach the card. Left alone: DHCP on `eth0` is the
  way in if Wi-Fi fails.
