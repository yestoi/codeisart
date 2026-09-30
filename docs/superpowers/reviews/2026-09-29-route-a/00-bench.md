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

## 3. The Pi 5 (OPEN)

The show's target. Set up tomorrow (the owner, 2026-09-30). `tools/sender_spike/send.py --dry-run` there, then
`--stamp` on a link, then `wall_pattern.py --dry-run` under the arcade's load.
