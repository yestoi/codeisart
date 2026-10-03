# Route A: the steady sender for the Colorlight 5A-75E

> **2026-09-30:** the rate and the packets in this spec (59 frames a second; the 112-byte sync twice, the 0x0A
> brightness packet twice, the row tail 08 88) are superseded: the driver sends the S2 sender card's format at
> 60.32 (one 1036-byte sync with a frame counter, byte 36 = 05, no brightness packet, the row tail 00 00),
> which removes the second picture the old format made the card draw. See
> `docs/superpowers/reviews/2026-09-30-ghosting/00-path-forward.md` section 2 and
> `docs/superpowers/plans/2026-09-30-s2-format.md`. The slot, the hold, the restart, the drain and the close stand.

2026-09-29. The driver in `show/display/colorlight.py`, shared by the show, the arcade and the pattern tool,
made to drive the card (firmware 13.17) without the flicker. What it must do was measured at the wall the same
day: `docs/superpowers/reviews/2026-09-29-sender-card-spike.md`, section 5 (each change with its runs), within
the order and the safety points of `docs/superpowers/reviews/2026-09-29-flicker/00-path-forward.md`, section
6. The design questions were worked through in `2026-09-29-flicker/04-code-audit.md`, section 2; this spec
settles them.

Labels: MEASURED (the spike's numbers), DECIDED (the owner's word, 2026-09-29 evening), OPEN (comes before
the work is called done).

## 1. What the wire must carry

One output frame, in this order, then nothing until the next tick (MEASURED: N1 against N6, N7):

1. The sync, twice: packet type 0x01, EtherType 0x0107, 112 bytes, the level at bytes 35 and 38 to 40, byte 36
   = 0x05. The sync shows the rows sent one tick earlier.
2. The brightness packet, twice: type 0x0A, 77 bytes, the level at bytes 13 to 15, byte 16 = 0xFF.
3. The rows, top to bottom: type 0x55, row header `row, offset (2), count (2), 08 88`, then the pixels **BGR**
   (MEASURED, `hardware.md` 15:40). A row wider than 256 pixels is split into equal packets, as today.

The packet builders of today (`frame_packet`, `brightness_packet`, `row_packets`) already make these bytes; the
tests pin them byte for byte against the spike's builders in `tools/sender_spike/send.py` (`sync_packet` with
the default `SyncSpec`, `brightness_packet`, `row_packets`), which are the working test sender's. What changes
is the order, the count and the pixel order; not a byte inside a packet.

**The rate**: 59.00 frames a second, a module constant (`OUTPUT_FPS = 59.0`), not a config key. Not 60.00,
not 60.32, never the content's 20 or 30, not 55 or below (MEASURED: N15b, N19, N11, S8b, N9, N10, N16b, N17).

**The timing**: the first sync within 100 us of its deadline (MEASURED: 0.25 ms of jitter shows, N21). The
recipe that held about 50 us at the port (step 6): real-time priority SCHED_FIFO 50, absolute deadlines on
`perf_counter_ns`, a sleep to 2 ms before the tick then a busy-wait, `PACKET_QDISC_BYPASS` on the socket.
Never a pure busy-wait (it stalled 37 ms once); never `time.sleep` alone (0.6 to 2.4 ms late). Superseded for the rows on 2026-09-30: with the rows paced across the frame (docs/superpowers/plans/2026-09-30-paced-rows.md) the sender spins between rows and from the last row to the sync, pinned to a core, as the bench child did when the wall was clean; the 37 ms stall was unpinned.

## 2. Where the sender runs: a separate process (DECIDED)

A thread cannot hold 100 us in this program: a busy-waiting thread holds the GIL, and a sleeping one has to
win the GIL back from the main thread, which keeps it up to the switch interval (5 ms) while rendering, and
for longer inside numpy and MediaPipe calls. So the sender is a child process from the start (the audit's
option E), with the C helper (option F) in reserve under the same process model if the Pi 5 measurement says
Python cannot do it (OPEN, section 9).

The parts, all in `show/display/colorlight.py` unless a file grows past reason:

**The packets** (as today): the three builders, the constants of the layout, `SYNC_REPS = 2`,
`BRIGHTNESS_REPS = 2`.

**The slot**: one frame in a file-backed mmap (`/dev/shm` where there is one; the file named for the parent's
pid, and the files of parents that are gone swept at the next create) with a header of int64 fields, and one
lock: a flock on the file itself, one per opening, released by the kernel if its holder dies. (A
`multiprocessing` lock or process would start Python's resource tracker, a child that lives as long as the show
and that the soak counts as a child left behind.) The parent writes a frame under the lock and bumps a counter.
The sender, at each tick, tries the lock without waiting: if it gets it and the counter moved, it copies the
frame out; if not, it keeps the frame it has. The lock is held for microseconds by either side, and the
sender never blocks on it, so the parent cannot make it late. Header fields: the frame counter, the level (a
byte), the stop flag, the pause flag, the sender's heartbeat (ticks so far), the error (errno and a count), the
real-time flag (whether the priority was granted), and the stats of section 6.

**The core** (`Sender`): a plain object with `tick()` and `run()`, given the slot, a `send` callable, a clock
and a sleep. No time in it that a test cannot fake. Each tick: read the stop and pause flags; take a new frame
if there is one; write the pixels (BGR) into the prebuilt row packets *before* the wait, so the sync leaves on
the deadline and the rows right behind it; wait for the deadline (sleep to `SPIN_NS` before it, then spin);
send sync, sync, brightness, brightness, the rows; record the sync's lateness; set the next deadline. The first
burst after a start or a pause is a *prime*: brightness and rows, no sync, so that the sync that follows shows a
whole frame and never the rows a torn burst left. Absolute deadlines from a start time; a tick that is a period
or more behind moves the whole grid and is counted a slip, never followed by a catch-up burst (as the spike's
loop and `arcade/runner.py`); the interval across a slip is not counted in the stats. `send` is `sock.send`,
one packet a call, as the measured sender did. The loop allocates nothing a frame: the swap writes into the
packets in place.

**The child** (`sender_main`, run as `python -m show.display.colorlight_sender`): attaches the slot, asks for
SCHED_FIFO 50 (a refusal sets the real-time flag off and the sender runs at ordinary priority; the parent logs a
warning once per display: the show goes on, roughly), turns garbage collection off, ignores SIGINT and SIGTERM
(both reach the whole process group, from Ctrl-C and from a systemd stop; the parent's close must drain black
first, and stops the child by the flag, or by SIGKILL past `JOIN_S`), runs the core until the stop flag, then
exits. It is a plain subprocess of the same interpreter, not a fork (the arcade makes its camera, and
MediaPipe's threads, before the display) and not `multiprocessing` (its resource tracker, section 2's slot).
The socket is opened in the *parent* (its errors raise from the constructor as today, naming CAP_NET_RAW and
the interface) with `PACKET_QDISC_BYPASS` set before the bind, and inherited by the child as a descriptor; the
parent keeps its own, for a restart. A socket with no descriptor (`DiscardSocket`) is a dry run: the child
sends to nowhere.

**The facade** (`ColorlightDisplay`): the unchanged `Display` protocol.

- `push(frame)`: shape and dtype checked as today, then the error check of section 4, then the frame written
  to the slot and the pause flag cleared. It returns before anything is on the wire. It sends nothing itself.
- `set_brightness(level)`: the level into the header; from the next tick every packet carries it. The
  every-third-push resend of today goes: the level is on the wire 59 times a second.
- `close()`: section 5.
- `stats()`: section 6.
- The constructor starts the child and waits for its first heartbeat (bounded, 2 s), so a child that cannot
  start is an error at open, not later. The wall is black from the first tick (section 3).

The steady sender repeats the last frame it was given. It originates no content of its own but the dark start
and the black of the close (section 3), and black if its parent dies (section 4).

## 3. Start dark, close to black

**The dark start** (DECIDED: the owner's word, the one permitted content). The child's first frame, before any
push, is black, sent at 59 from the moment the display opens. The card keeps its last picture through a
restart (`hardware.md`); the old picture would otherwise stand until the first governed frame, uncounted.
`GovernedDisplay(from_dark=True)` already counts the first frame against a dark wall, which is now true.

**The close** (DECIDED: "close by draining to black and holding"). `close()` writes black to the slot, clears
the pause, and lets the sender run it for `CLOSE_HOLD_S = 1.0` s (59 frames, the value that landed a black
wall, `hardware.md` and the spike's 1 s tail), then sets the stop flag; the sender stops after a whole burst,
never inside one; the parent joins the child (bounded, 3 s, then terminated), closes the socket and unlinks
the slot. `GovernedDisplay.close` still pushes its two governed black frames first; the arcade, which pushes
no black, gets the driver's. A close while the sender is paused (in a hold) restarts it on black.

## 4. Failure: carried back, the hold kept, the sender paused

**A failed send** (an `OSError` from `sock.send` in the child): the sender ends the burst there, sends no
more of it (no sync follows a torn frame), records the errno and bumps the error count, sets the pause flag and
sends nothing more until the pause is cleared. The next `push` in the parent sees the count moved, raises
`OSError(errno, ...)` and does *not* take the frame. `GovernedDisplay` then does what it does today: `failed`
counts, the hold starts from that push, the counted frame is the one that raised (`show/wall.py`). The repush
that ends the hold's silence writes the counted frame and clears the pause: the stream restarts on it, at 59,
from a fresh deadline grid, and runs it for the rest of the hold. The second repush changes nothing on the wire.
`close()` in a hold works the same way. Nothing in `show/wall.py` changes.

Why paused and not running (DECIDED): during the hold nothing changes on the wall, which is the second of
quiet Q66 measured; a running sender would repair a torn picture 17 ms after the tear with a change the governor
never counted (Q65's shape). The card keeps its picture through a stopped stream. What a stop and a restart
look like at 59 is the owner's Q66 check (OPEN, section 9): the picture stays, steady, no blink at either end.
If a blink shows, "keep the last whole frame running" is one flag in the core.

**A dead sender** (the child gone, or its heartbeat still for `DEAD_S = 1.0` s): `push` raises `OSError`
("the sender is not running") and does not take the frame; the driver restarts the child at the first push
`RESTART_S = 1.0` s or more after it died, on the same socket and slot, and the new child resumes on the slot's
last frame (a governed one: a black of the driver's own between two content frames would be a change the
governor never counted). The show daemon's push failures, its lights-off after 10 s and the soak's counters
all see this, as they see a failed send. A `close` that finds the child dead starts one to drain the black.

**A dead parent**: the child watches its parent (`os.getppid()`, once a tick); when the parent is gone it runs
black for `CLOSE_HOLD_S` (taking no frame meanwhile) and exits, so a crashed show leaves a dark wall, not a
frozen picture, until systemd starts it again 2 s later. Black on a parent's death is under the same word as
the dark start. The child ignores SIGINT, SIGTERM and SIGABRT (Ctrl-C, `systemctl stop` and the watchdog's
signal all go to the whole process group or cgroup), so in each case it outlives the parent long enough to do
this; SIGKILL to the cgroup (systemd's final resort, after the stop timeout) leaves the wall on its last
picture, as before route A. The child holds the slot by descriptor, not by path: logind's `RemoveIPC` deletes
a user's `/dev/shm` files when their last login ends, and a restart must still find the slot.

**A pulled cable**: whether `send` raises on this port with the link down is not known (the audit's G11). It
is measured at the wall (section 9); if it raises nothing, a carrier watch (`/sys/class/net/<iface>/carrier`
read once a second in the child, a lost carrier counted as a failed send) is the follow-up, not part of this
slice.

## 5. What the callers see

Nothing new to call. `show/main.py`, `arcade/main.py` and `tools/wall_pattern.py` reach the driver through
`make_display` as before, at their own rates. Two small changes beside the driver:

- `tools/wall_pattern.py` is paced by absolute deadlines (the audit's G14): the next push is due `1/fps` after
  the last was *due*, not after it returned; a late tick runs at once and the grid restarts from it. At its end
  it prints the sender's stats (section 6).
- `arcade/main.py` and `show/main.py` log the sender's stats at the close, when the display has them.

The governor is untouched (`arcade/flash.py` frozen, `show/wall.py` unchanged). Its safety argument, restated
for the steady sender (the audit's 2.2): the wall shows only frames the governor passed; a content frame may
be skipped when two fall in one output period, never invented; display time is quantised but transitions are
not added; the driver originates black only, at the start, at the close and at a parent's death.

## 6. Measuring on the target

The sender keeps, in the slot's header, over its life: ticks, slips, late ticks (the sync more than
`LATE_NS = 1 ms` after its deadline), the worst lateness, and the sum and sum of squares of the sync-to-sync
interval, from which `stats()` gives `frames, late, slips, worst_us, mean_us, sd_us, errors, restarts, rt`.
The pattern tool prints them at its end; the loops log them at the close. The suite asserts none of these:
rates are measured on the target, not in tests. The spike's `send.py --dry-run` and `--stamp` stay the way to
measure a machine before trusting it (section 9).

## 7. Scheduling and the unit

`deploy/show.service` gains `CAP_SYS_NICE` beside `CAP_NET_RAW` in `AmbientCapabilities` (SCHED_FIFO needs
it), and `deploy/README.md` says so; its "Pi 4" heading becomes the Pi 5 when the owner confirms the target
(DECIDED for the unit; the heading waits on the Pi). `tests/test_deploy.py` pins the new value. Under `sudo`
(the bench) nothing is needed. Without either, the sender says so once and runs at ordinary priority.

The child is not pinned to a core in this slice (`SENDER_CPU = None`); the Pi measurement decides whether it
should be.

## 8. Tests

Test first; the old tests that pin the old order (frame packet then rows per push, the brightness packet every
third push) are replaced, not kept. The layers, following the audit's 2.6:

1. **Packets**: byte for byte the spike's (`tests/sender_spike` style); the BGR of a red pixel; the level in
   all four packets of a frame; NaN and negative levels dark.
2. **One burst, no time**: `Sender.tick()` with a fake socket and a fake clock sends exactly sync, sync,
   brightness, brightness, the rows, from one frame only (a fake `send` that pushes another frame at row 20
   changes nothing in this burst and the whole of the next); black before any push; the same rows again
   when nothing new was pushed; a `send` that raises at packet k sends nothing after k, sets the pause and the
   error, and sends nothing on later ticks until the pause is cleared.
3. **Pacing on a fake clock**: deadlines at start + k/59 exactly, no drift over 10 000 ticks; the sleep is asked
   for the time to `SPIN_NS` before the deadline and the spin covers the rest; a stall of 100 ms moves the grid
   once with no catch-up.
4. **The slot**: a frame written is read whole; the lock held by the other side means the last frame again,
   not a wait; the counter tells a new frame from an old one.
5. **The facade**, with a test launcher that runs the core in the test's own hands (no child): push copies
   (the caller's array changed after the push does not change the wire); a raised send comes back from the next
   push, which stores nothing; the push after that restarts the stream; a dead sender raises and is restarted
   after `RESTART_S`; `close` drains 59 black bursts and stops after a whole one; the socket is closed.
6. **The child, liveness only**: start on a stream socketpair, push, see the third sync on the other end, close,
   joined, socket closed. One test, bounded by a timeout, asserting no rate.
7. **The hold**: a third display model beside `TornDisplay`'s two in `tests/test_wall_hold.py` ("rows then
   sync, a torn burst sends no sync, the stream pauses") and the sweeps of `test_wall_hold.py` and
   `test_wall_close_hold.py` run against it.
8. **The tool and the unit**: the pattern tool's deadline pacing; `test_deploy.py`'s capabilities.

## 9. Open before it is called done

1. **The Pi 5** (the show's target): can Python hold the sync to 100 us there, alone and under MediaPipe?
   Measured with `tools/sender_spike/send.py --dry-run` on the Pi, then `--stamp` on a real link, then the
   driver's own stats under the arcade. The Pi is set up tomorrow (the owner); tonight's bench is the Omarchy
   box. If Python cannot: the C helper, same process model.
2. **Gone or too fast to see**: a 240 fps phone clip of the driver at 59 against a held-frame control, at the
   wall. For the audience it does not matter; for the governor's argument it may.
3. **Q66 at 59**: stop the stream, the picture stays and stays steady, no blink at the stop or the restart.
4. **The cable pulled for 5 s** during `wall_pattern.py grid`: does `send` raise; what the wall shows; what
   happens when it returns.
5. **The rgb check**: `wall_pattern.py rgb` shows red, green, blue, white from the left; Ctrl-C lands black
   three times of three; the show at 20 and the arcade at 30 steady by eye.

## 10. Not in this slice

The S2's bytes, one sync a frame, no brightness packet, the row header 00 00 (all measured unnecessary). A
discovery-packet health check (the audit's G11). The carrier watch. Pinning a core. Any change to
`arcade/flash.py`, `show/wall.py` or the governor's inputs. The 512x192 wall's budget.

## 11. Amendment (2026-10-03): the hand-off keeps the picture

Scope: only the swap between the wall's own processes under promptviz's conductor (the party wall to a guest, the
arcade's `run --game --leave-after/--once` or the show's `--play`, and back). Everything else closes as section 3
decided.

Why: measured on the Pi's journal for the FREEZE pick at 16:20:53, the wall was dark for about 4.5 s between the
pick and the guest's card: 1.1 s of the close's black hold, 0.5 s of process start, 2.6 s of the doctor's second
camera open, the rest the guest's own open. A guest sees a black wall and does not know the pick took.

What changes. `ColorlightDisplay.close(keep_picture=True)` writes no black and holds nothing: it sets the stop
flag, joins the child (bounded, as before), closes the socket and unlinks the slot. The card keeps the last
picture, as `hardware.md` says it does through a restart. The sender child is still stopped and joined, never
left to die, because a child whose parent has gone drains black on its own (section 4) and would undo this.
`GovernedDisplay.close(keep_picture=True)` pushes no black frames and passes the flag down. The three callers
pass it only when the run ended by its own rule: the party wall on a pick (its exit code set), the arcade when
`until()` ended the loop, the show when `--play`'s entry ended. A KeyboardInterrupt (the unit's SIGINT, the
conductor's limit) and `--seconds` close to black as before, so `systemctl stop` never leaves a frozen frame lit.

Why the dark start still holds (C52). The next process's sender starts on a black frame and the open waits for
its first beat (section 3), so the first governed frame is still counted against a black wall. The one
uncounted pair, the kept picture to black to the first card, happens once inside about half a second: one
flash, under the 3 a second rule.

Also: `arcade run --require camera` with `camera = "imx500"` no longer runs the doctor's probe (a second open of
the same camera); the one open in `make_sources(strict=True)` is the check and a failure returns 1 with the
doctor's line. A script or a replay opens no camera, so the doctor still probes then. The probe's wait for the
network upload is lost on this path; under the conductor the party wall streams the same source for minutes
before any pick, so an upload completes there.
