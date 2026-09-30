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
"ordinary priority is a gamble" of the spike's step 6 (0.2 to 0.8 ms late once in a while there); at real-time
priority the spike's sender held 3 to 5 us sd and 15 to 52 us worst. The real-time run of the driver is OPEN (needs sudo).

The driver's tests pass on the box (119 of the driver's, the tool's and the soak's), the child a real subprocess there.

## 2. At the wall (OPEN)

Waits on the owner, the LEDVision VM off, sudo granted: the plan's Task 11 (the rgb check, steady by eye at 20 and 30
pushes, Q66 at 59 by `wall_pattern.py grid --stop-for 5`, the cable pulled, the 240 fps clip). Before it, on the
box under sudo: `grid --dry-run --seconds 30` must say `real-time yes` and a worst under 100 us.

Also OPEN, on the Pi under the unit: the close's log line says `real-time yes` (the README's check); a kernel with
CONFIG_RT_GROUP_SCHED refuses SCHED_FIFO in a service's cgroup.

## 3. The Pi 5 (OPEN)

The show's target. Set up tomorrow (the owner, 2026-09-30). `tools/sender_spike/send.py --dry-run` there, then
`--stamp` on a link, then `wall_pattern.py --dry-run` under the arcade's load.
