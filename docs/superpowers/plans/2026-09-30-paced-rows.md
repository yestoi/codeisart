# The paced row send at 60.00, implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** the steady sender (`show/display/colorlight_sender.py`) sends what the bench child sent when the wall was "near perfect" on the evening of 2026-09-30: the S2 format as on the branch, `OUTPUT_FPS = 60.00`, the sync on its deadline, then the row packets paced evenly across the 15.5 ms after it, the last about 1.2 ms before the next sync.

**Architecture:** a timing change only. The card in the S2 mode shows rows as they land, so a 1 ms burst of rows tears on motion; spread across the frame they do not (`08-wall-session-evening.md`, verdicts 2 to 4). Each row packet gets a slot on the sync's own grid: row k goes out at `deadline + ROW_SPREAD_NS * (k + 1) // n` for n row packets (64 on the 128-wide wall, one every 242 us; 128 on a 512-wide wall of 64 rows, one every 121 us; 384 at the show's 512 x 192, one every 40 us), the last at `deadline + 15.5 ms`, 1.17 ms before the next sync. Between rows the sender spins (a slot is far inside `time.sleep`'s lateness), so in a steady stream it never sleeps: the frame is the rows and then the 1.17 ms spin to the next sync, which stays inside its 100 us. A row that goes out after the next row's slot began is counted in the header as one that missed its slot, with the worst lateness beside it; the stats and the log line carry both. The tick now starts right after the last row, 1.17 ms before the sync, so the frame's BGR swap (800 us for a 512 x 192 frame on the Pi 5) leaves that gap and rides in the row loop, one packet at a time inside that packet's own slot (3.5 us); the frame copy from the slot stays in the gap (13 to 50 us). The prime (the rows alone, before the first sync after a start or a pause) stays a burst and swaps the whole frame, which also repairs the mixed rows a torn burst leaves. The bytes, the prime, the hold, the pause after a failed send, the restart, the parent-death drain and the close are untouched.

**Tech Stack:** Python 3.11+, numpy, pytest. The fakes in `tests/colorlight_fakes.py` (`FakeSocket` with its `hook`, `FakeClock` with a 10 us step per read).

**Spec:** `docs/superpowers/reviews/2026-09-30-ghosting/08-wall-session-evening.md` sections 1 and 3 (the verdict and the configuration to build), and the bench child that produced it, `docs/superpowers/reviews/2026-09-30-ghosting/bench/ghost_child.py` (its `GHOST_SPREAD_MS` knob: a wait before each row, `t0` at the sync). The sender's own design: `docs/superpowers/specs/2026-09-29-route-a-steady-sender-design.md` (the rate superseded here and in `2026-09-30-s2-format.md`; the hold, restart and close are not).

## Global Constraints

- **Nothing goes to the card.** No run against `eth0`, `enp5s0` or any interface with the card on it. Dry runs (`--dry-run`, a `DiscardSocket`) and the fake socket only. The owner runs the wall checks from the Pi at his word.
- **The bytes do not change.** No edit to `show/display/colorlight_packets.py`. `tests/test_colorlight_sender.py::test_a_frame_on_the_wire_is_the_winning_spike_runs_frame` (the whole frame against the spike's builders, counter and all) passes as it is, unedited.
- `OUTPUT_FPS = 60.00`, a module constant, never a config key. `PERIOD_NS = round(1e9 / OUTPUT_FPS) == 16_666_667`, `CLOSE_FRAMES = round(CLOSE_HOLD_S * OUTPUT_FPS) == 60`. Why 60.00 and not 60.32: verdict 4 of the spec (A/B on the lobby, both paced: 60.32 "an acceptable amount of flicker", 60.00 "near perfect, one flicker in 30 s"; the lobby ticks 30 a second, so 60.00 shows every frame twice with no 3 s beat). 59 in this format: shimmer and the copy back (verdict 5).
- `ROW_SPREAD_NS = 15_500_000`, a module constant. Why: verdict 3 (15.5 ms "zero flicker, no weird artifacts"; 14 "some flicker, acceptable"; 16.4, the rows meeting the next sync, "worse, slight ghosting" with the sync 79 us late). The margin `PERIOD_NS - ROW_SPREAD_NS = 1_166_667` ns is what keeps the last row off the next sync.
- The slots are on the sync's grid (`self.deadline`), not on the sync's actual send time: a sync that goes out late does not push the last row toward the next sync; the first rows whose slots have passed go at once instead.
- A row missed its slot when its wait ended more than one slot (`row_spread_ns // n`) after the slot began. With a spread of 0 (the bench's burst) there are no slots: nothing is counted and no worst is kept.
- The sync's 100 us budget still holds: `wait_until` and the sync's send are not edited. `SPIN_NS` (2 ms) is larger than the margin, so the sync's wait is a spin in a steady stream; the sender sleeps only on the tick after a prime (a start, a pause). A slip moves the deadline to now and never sleeps.
- Untouched, by name: `Sender.run`, the `STOP` and `PAUSE` branches of `tick`, the slip logic, the `except OSError` branch (the pause after a failed send) except one added line, `self._primed = False`, so the restart primes even when the pause is cleared before a paused tick has run (Task 2), the counter, the level, the prime's burst, `Slot` (except the header's length), `sender_main`, `main`, everything in `colorlight.py` except `stats_line` and its docstring's rate words.
- **The take and the swap sit in the gap now.** Before this plan the frame copy (`slot.take`) and the BGR swap ran at the tick's top inside 15 ms of idle; now the tick starts right after the last row, 1.17 ms before the sync. Measured on the Pi 5 (2026-09-30, numpy only, no socket, 300 tries): the take 1 to 4 us at 128 x 64 and 13 to 50 us at 512 x 192; the whole-frame swap 67 to 83 us at 128 x 64 and 789 to 809 us at 512 x 192. So the swap moves into the row loop, one packet at a time before that packet's spin (2.3 to 2.7 us a packet at 128 x 64, in a 242 us slot; 3.5 to 3.6 us at 512 x 192, 384 packets in 40 us slots); the take stays in the gap. The prime still swaps the whole frame: a burst has no slots, and that repairs the mixed rows a torn burst leaves in the packets (every torn burst pauses, every pause primes). The packets hold one whole frame at every tick's end, as before; the parent-death drain zeroes the packets and takes nothing, as before.
- **The spin and the kernel.** The sender pinned to its core at SCHED_FIFO 50 now spins the whole frame. On the Pi (read 2026-09-30, `trey@codeisart.local`: kernel `6.18.50+rpt-rpi-2712`, 4 cores, `sched_rt_runtime_us` 950000, `NO_RT_RUNTIME_SHARE`, the fair server on cpu3 at 50 ms runtime per 1 s period) a spinning real-time task is not throttled on a schedule; a fair thread that lands on that core gets the core for as long as its own work lasts, up to 50 ms a second. The bench child spun the same way at the wall (its spread wait never slept at a 242 us step) over 30 to 40 s runs with worst syncs of 14 to 66 us. Read from the Pi's `/proc/config.gz` the same day: `CONFIG_RT_GROUP_SCHED` not set (no per-cgroup real-time throttle), `CONFIG_PREEMPT=y`, `CONFIG_HZ=250`. The repo's own record against a spin: `wait_until`'s docstring and the design spec's rule "never a pure busy-wait (it stalled 37 ms once)", from the spike of 2026-09-29, unpinned; 37 ms fits the fair server's lump. The evening's paced runs, pinned, are the later evidence and the wall's, and the owner's instruction is the paced rows: the rule yields, Task 1 rewrites the docstring and adds a sentence to the spec's rule. The soaks are the proof. What the soak reads for: a stall of tens of ms about once a second (the fair server handing the core to a fair thread; the parent is not pinned off the sender's core, a follow-up if it shows, and the core's own kernel threads, `kworker/3` and `ksoftirqd/3`, no pinning moves); heat, since one core now runs at 100% for the whole show (`vcgencmd get_throttled` in the soak's status; a throttled clock shrinks the 40 us slots of the show's wall).
- Work in `/Users/trey/dev/codeisart-s2-format` on branch `s2-format` (at 035b0d6); commit after each task; never push and never merge.
- Run tests from the worktree with the main checkout's venv: `cd /Users/trey/dev/codeisart-s2-format && /Users/trey/dev/codeisart/.venv/bin/python -m pytest <paths> -q`. The colorlight suite is `tests/test_colorlight_packets.py tests/test_colorlight_sender.py tests/test_colorlight.py tests/test_colorlight_slot.py tests/test_colorlight_child.py tests/test_wall_pattern.py tests/test_deploy.py tests/sender_spike`; the baseline before this plan is 466 passed, 2 skipped in 2.95 s without `test_deploy.py`. The fake clock steps 10 us a read, so a paced tick is about 1 600 reads where a burst was about 200; the suite's time is measured in Task 5.
- Comment and docstring style as the repo's: plain sentences, the measurement or the date that a number rests on named beside it.

## Review Focus

Inputs the spec implies that no task's tests would otherwise exercise; each has its test in the task that owns the code:

1. A stall inside the rows longer than the margin (3.3 ms after row 60): every row still goes out, at once, the next sync is late and counted (`LATE`), no slip, nothing dropped, and the first rows of the frame behind the late sync are counted as missed too, since the grid does not move (Task 2, `test_a_stall_past_the_margin_sends_every_row_and_makes_the_next_sync_late`).
2. A stall inside the rows shorter than the margin (1 ms after row 19): the rows whose slots passed are counted as missed, the worst lateness recorded, and the next sync lands on its deadline (Task 2, `test_rows_that_miss_their_slot_are_counted_and_the_next_sync_holds`).
3. A 512-wide wall: 128 row packets a frame at 64 rows (121 us slots) and 384 at the show's own 512 x 192 (`show/config.py`; 40 us slots), every one in its own slot, in scan order (row 0 offset 0, row 0 offset 256, row 1 offset 0), the last still at 15.5 ms (Task 2, `test_a_wide_wall_paces_every_row_packet_in_its_own_slot`). The send's own cost inside a 40 us slot (about 15 us, from the bench's 1 ms burst of 64) cannot be measured without the card: wall check 4 at 512 x 192 reads the rows-off-their-slot count as its gate.
4. A spread of 0 (the bench's burst) sends the rows back to back with no row counted late; a spread of a period or more is refused at construction (Task 2, `test_a_spread_of_zero_is_a_burst_with_no_row_counted_late`).
5. The restart after a pause: its prime is still a burst, the frame after it is paced (Task 2, `test_the_prime_and_a_restarts_prime_stay_a_burst`), and a burst torn by a failed send half-way through the per-packet swap leaves no mixed frame at that prime (Task 2, `test_a_torn_burst_leaves_no_mixed_frame_at_the_restarts_prime`); the counter's continuity across it is already pinned by `test_the_counter_counts_syncs_from_zero_wraps_at_a_byte_and_carries_on_through_a_pause`.

---

### Task 1: The rate, the spread and the spin between rows

**Files:**
- Modify: `show/display/colorlight_sender.py` (the module docstring, lines 1 to 22; the constants at 42 to 57; `wait_until`'s docstring, lines 202 to 204; a `spin_until` after `wait_until`, line 212)
- Modify: `docs/superpowers/specs/2026-09-29-route-a-steady-sender-design.md` (the busy-wait rule, line 41)
- Test: `tests/test_colorlight_sender.py`

**Interfaces:**
- Produces: `OUTPUT_FPS = 60.00`, `PERIOD_NS = 16_666_667`, `ROW_SPREAD_NS = 15_500_000`, `CLOSE_FRAMES = 60`; header indices `ROWS_LATE = 16`, `ROW_WORST = 17`, `HEADER_LEN = 18`; `spin_until(target_ns: int, clock: Callable[[], int]) -> int` (how late the wait ended, ns).

- [ ] **Step 1: Write the failing tests**

In `tests/test_colorlight_sender.py` change the import block (lines 8 to 11) to:

```python
from show.display.colorlight_packets import COUNTER_OFFSET, row_packets, sync_bytes
from show.display.colorlight_sender import (BEATS, CLOSE_FRAMES, CLOSE_HOLD_S, DEV_N, ERRNO, ERRORS, FRAMES, LEVEL,
                                            LATE, OUTPUT_FPS, PAUSE, PERIOD_NS, ROW_SPREAD_NS, ROW_WORST, ROWS_LATE,
                                            SLIPS, STOP, Sender, Slot)
from tests.colorlight_fakes import BRIGHTNESS, ROW, SYNC, Cranked, FakeClock, FakeSocket, bursts, kinds, row_pixels
```

Replace `test_the_rate_and_the_close_follow_the_winning_run` (lines 106 to 109) with:

```python
def test_the_rate_the_spread_and_the_close_follow_the_evening_at_the_wall():
    # 08-wall-session-evening.md: 60.00 with the rows paced over 15.5 ms "near perfect"; 60.32 an acceptable
    # flicker; 14 ms some flicker; 16.4 ms (the rows meeting the next sync) worse.
    assert OUTPUT_FPS == 60.00 and PERIOD_NS == round(1e9 / 60.0) == 16_666_667
    assert ROW_SPREAD_NS == 15_500_000
    assert PERIOD_NS - ROW_SPREAD_NS >= 1_100_000                              # the last row 1.17 ms before the next sync
    assert CLOSE_FRAMES == round(CLOSE_HOLD_S * OUTPUT_FPS) == 60
    assert round(CLOSE_HOLD_S * Cranked(FakeSocket(), FakeClock()).fps) >= CLOSE_FRAMES   # a close's sleep cranks a second
```

Change the pacing section's import (line 176) to:

```python
from show.display.colorlight_sender import LATE_NS, SPIN_NS, spin_until, stats_of, wait_until  # noqa: E402
```

and add after `test_the_wait_sleeps_to_spin_ns_before_the_deadline_then_spins` (after line 206):

```python
def test_the_spin_between_rows_never_sleeps_and_returns_its_lateness():
    clock = FakeClock(step_ns=10_000)
    target = clock.t + 242_000                                                # one row's slot at 64 rows
    assert 0 <= spin_until(target, clock.now) < clock.step
    assert target <= clock.t < target + clock.step and clock.slept == []
    clock.t += 500_000                                                        # the target 500 us in the past
    assert 500_000 <= spin_until(target, clock.now) <= 500_000 + 2 * clock.step   # at once, the lateness handed back
```

In `test_stats_read_the_header` (line 229) change `np.zeros(16, np.int64)` to `np.zeros(18, np.int64)` and the expected dict to:

```python
    assert stats_of(np.zeros(18, np.int64)) == {"frames": 0, "late": 0, "slips": 0, "worst_us": 0.0, "mean_us": 0.0,
                                                "sd_us": 0.0, "errors": 0, "rt": False, "wake_worst_us": 0.0,
                                                "rows_late": 0, "row_worst_us": 0.0}
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `cd /Users/trey/dev/codeisart-s2-format && /Users/trey/dev/codeisart/.venv/bin/python -m pytest tests/test_colorlight_sender.py -q 2>&1 | tail -5`
Expected: an ImportError on `ROW_SPREAD_NS` (the whole module fails to collect).

- [ ] **Step 3: The constants, the header and the spin**

In `show/display/colorlight_sender.py` replace the module docstring's first line and its first paragraph (lines 1 to 8) with:

```python
"""The steady sender of the Colorlight driver: 60.00 frames a second to the card, whatever the caller's rate.

The spec: docs/superpowers/specs/2026-09-29-route-a-steady-sender-design.md, its rate and packets superseded by
docs/superpowers/reviews/2026-09-30-ghosting/00-path-forward.md section 2 and 08-wall-session-evening.md
section 1. What the card wants was measured on 2026-09-29 (the sync first, within 100 us of its deadline; pixels
BGR), on 2026-09-30 (the S2 sender card's format: one 1036-byte sync a frame with a frame counter, no 0x0A
brightness packet; in that format 59 shows shimmer and the copy, and in our old format anything under 60 drew a
second picture) and on the evening of 2026-09-30 (in the S2 mode the card shows rows as they land: a 1 ms burst
of rows after the sync tears on motion, the rows paced evenly across the 15.5 ms after the sync do not, and
60.00 beat 60.32 on the lobby, which ticks 30 a second).

A frame on the wire: the sync on its deadline, then row packet k in its own slot ROW_SPREAD_NS * (k + 1) // n
after that deadline (64 slots of 242 us on the 128-wide wall; 128 of 121 us on a 512-wide one), the last 1.17 ms
before the next sync. Between rows the sender spins (a slot is far inside time.sleep's lateness), so in a steady
stream it never sleeps: the frame is the rows, then the spin to the next sync. A row whose wait ended after the
next row's slot began is counted as one that missed its slot, the worst lateness beside it. A new frame is
swapped to BGR into the packets one packet at a time, inside that packet's slot (the whole 512 x 192 frame at
once is 800 us on the Pi 5, and the tick's top now sits in the 1.17 ms before the sync). The prime (the rows
before the first sync after a start or a pause) is still a burst, and swaps the whole frame: that leaves the
packets whole after a burst torn by a failed send.
"""
```

(The paragraph about the Slot, lines 10 to 14, stays as it is.) In the Sender paragraph (lines 16 to 21) change `a sleep to SPIN_NS before each deadline and then a busy-wait` to `a sleep to SPIN_NS before a deadline further off than that (only the one after a prime: in a steady stream the wait is a spin from the last row) and then a busy-wait`.

Replace `wait_until`'s docstring (lines 202 to 204) with:

```python
    """Sleep to spin_ns before the target, then busy-wait to it. time.sleep alone wakes 0.6 to 2.4 ms late; a
    pure busy-wait at real-time priority once stalled 37 ms (the spike's step 6, unpinned). With the rows paced
    the sync's wait in a steady stream is the spin alone (the last row lands 1.17 ms before the deadline, under
    spin_ns), which the bench child did at the wall, pinned, and was clean (2026-09-30 evening). Returns how late
    the sleep woke, ns (0 when it did not sleep): past spin_ns, the spin cannot hold the deadline."""
```

In `docs/superpowers/specs/2026-09-29-route-a-steady-sender-design.md` line 41 (`Never a pure busy-wait (it stalled 37 ms once); never \`time.sleep\` alone (0.6 to 2.4 ms late).`) append the sentence: `Superseded for the rows on 2026-09-30: with the rows paced across the frame (docs/superpowers/plans/2026-09-30-paced-rows.md) the sender spins between rows and from the last row to the sync, pinned to a core, as the bench child did when the wall was clean; the 37 ms stall was unpinned.`

Replace the constants block (lines 42 to 57) with:

```python
OUTPUT_FPS = 60.00                      # with the rows paced: A/B on the lobby, 2026-09-30 evening, 60.32 "an acceptable
                                        # amount of flicker", 60.00 "near perfect, one flicker in 30 s" (the lobby ticks
                                        # 30 a second: 60.00 shows every frame twice); 59 in this format: shimmer, the copy
PERIOD_NS = round(1e9 / OUTPUT_FPS)     # 16 666 667
ROW_SPREAD_NS = 15_500_000              # the rows paced across this after the sync: 15.5 ms "zero flicker" on the
                                        # video, 14 some, 16.4 (the rows meeting the next sync) worse; the last row
                                        # lands PERIOD_NS - ROW_SPREAD_NS = 1.17 ms before the next sync
SPIN_NS = 2_000_000                     # sleep to this before the deadline, then busy-wait
LATE_NS = 1_000_000                     # a sync this long after its deadline is counted late
PAUSE_POLL_S = 0.005                    # while paused: nothing sent, the flags read this often
CLOSE_HOLD_S = 1.0                      # black runs this long at the close, and when the parent dies
CLOSE_FRAMES = round(CLOSE_HOLD_S * OUTPUT_FPS)
RT_PRIORITY = 50
SENDER_CPU = None                       # a core to pin the child to; None: the highest it may use (sender_cpu)

# The header's int64 fields. Both sides read and write single fields without the lock: a field is one aligned
# 64-bit store, and no reading depends on two fields changing together.
(FRAME, LEVEL, STOP, PAUSE, BEATS, FRAMES, ERRNO, ERRORS, RT, SLIPS, LATE, WORST, DEV_N, DEV_SUM,
 DEV_SUMSQ, WAKE_WORST, ROWS_LATE, ROW_WORST) = range(18)
HEADER_LEN = 18                         # int64s; 144 bytes before the frame
```

After `wait_until` (after line 212) add:

```python
def spin_until(target_ns: int, clock: Callable[[], int]) -> int:
    """Busy-wait to the target, never a sleep: a row's slot is 242 us at 64 rows, far inside time.sleep's
    lateness (0.6 to 2.4 ms, the spike). Returns how late the wait ended, ns: about 0 when it waited, more when
    the target had passed."""
    now = clock()
    while now < target_ns:
        now = clock()
    return now - target_ns
```

And in `stats_of` (line 317) add the two keys to the dict:

```python
    return {"frames": int(h[FRAMES]), "late": int(h[LATE]), "slips": int(h[SLIPS]), "worst_us": h[WORST] / 1e3,
            "mean_us": mean / 1e3, "sd_us": math.sqrt(max(var, 0.0)) / 1e3, "errors": int(h[ERRORS]),
            "rt": bool(h[RT]), "wake_worst_us": h[WAKE_WORST] / 1e3,
            "rows_late": int(h[ROWS_LATE]), "row_worst_us": h[ROW_WORST] / 1e3}
```

with its docstring's list extended: "..., the spread of the sync-to-sync interval, in microseconds, the rows that missed their slot and the worst row lateness."

- [ ] **Step 4: Run the sender's tests**

Run: `cd /Users/trey/dev/codeisart-s2-format && /Users/trey/dev/codeisart/.venv/bin/python -m pytest tests/test_colorlight_sender.py tests/test_colorlight_slot.py -q 2>&1 | tail -5`
Expected: all pass except `test_the_worst_wake_past_the_spin_margin_is_recorded`, which may still pass here (the rows are not paced yet) and is reworked in Task 2. `test_colorlight_slot.py` passes: `len(slot.h) == HEADER_LEN` follows the constant.

- [ ] **Step 5: Commit**

```bash
cd /Users/trey/dev/codeisart-s2-format
git add show/display/colorlight_sender.py tests/test_colorlight_sender.py docs/superpowers/specs/2026-09-29-route-a-steady-sender-design.md
git commit -m "feat(colorlight): 60.00 frames a second, the row spread constant, the spin between rows and the two header fields for a row that missed its slot"
```

---

### Task 2: The rows paced on the sync's grid, the missed slots counted

**Files:**
- Modify: `show/display/colorlight_sender.py` (`Sender.__init__` at lines 218 to 235; the send block of `tick` at 268 to 280; the class docstring at 216)
- Test: `tests/test_colorlight_sender.py`

**Interfaces:**
- Consumes: `spin_until`, `ROW_SPREAD_NS`, `ROWS_LATE`, `ROW_WORST` (Task 1).
- Produces: `Sender(slot, send, *, clock, sleep, period_ns, spin_ns, row_spread_ns=ROW_SPREAD_NS, parent_alive)`; `sender._row_due: list[int]` (each row packet's offset from the sync's deadline, ns) and `sender._row_step: int` (one slot, ns); `sender._bgr_rows` (the packets' pixels as (packets, chunk, 3), a view of `sender.packets`) and `sender._frame_rows` (the taken frame cut the same way, a view of `sender.frame`); a `ValueError` for a `row_spread_ns` outside `0 <= x < period_ns`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_colorlight_sender.py`, after `test_the_worst_wake_past_the_spin_margin_is_recorded`'s section and before the `# --- the whole burst against the spike sender's` section (before line 309), and rework that wake test as shown:

```python
# --- the rows paced across the frame (2026-09-30 evening: the card shows rows as they land; a burst tears)

def stamped(slot, **kw):
    """A sender whose socket stamps every send with the fake clock's reading: stamps of (packet, ns)."""
    sock, clock, stamps = FakeSocket(), FakeClock(), []
    sock.hook = lambda n, p: stamps.append((p, clock.t))
    sender = Sender(slot, sock.send, clock=clock.now, sleep=clock.sleep, **kw)
    return sender, sock, clock, stamps


def test_the_rows_are_paced_across_the_frame_on_the_syncs_grid(slot):
    sender, sock, clock, stamps = stamped(slot)
    for _ in range(4):                                                        # the prime, then three frames
        sender.tick()
    syncs = [i for i, (p, _) in enumerate(stamps) if p[12] == SYNC]
    assert len(syncs) == 3
    for i, j in zip(syncs, syncs[1:] + [len(stamps)]):
        t0, rows = stamps[i][1], stamps[i + 1 : j]
        assert kinds([p for p, _ in rows]) == [ROW] * H
        for k, (p, t) in enumerate(rows):                                     # one every 242 us, on the grid
            assert abs(t - (t0 + ROW_SPREAD_NS * (k + 1) // H)) <= 3 * clock.step, k
        if j < len(stamps):                                                   # then 1.17 ms of quiet to the next sync
            assert abs((stamps[j][1] - rows[-1][1]) - (PERIOD_NS - ROW_SPREAD_NS)) <= 3 * clock.step
    assert slot.h[ROWS_LATE] == 0 and slot.h[ROW_WORST] < 2 * clock.step
    assert len(clock.slept) == 1                                              # only before the first sync: after that the
    assert 0 < clock.slept[0] <= PERIOD_NS / 1e9                              # frame is the rows and a spin under SPIN_NS


@pytest.mark.parametrize("width,height,sends", [(512, 64, 128), (512, 192, 384), (384, 4, 8)])
def test_a_wide_wall_paces_every_row_packet_in_its_own_slot(width, height, sends):
    s = Slot.create(width, height)
    try:
        sender, sock, clock, stamps = stamped(s)
        sender.tick()
        sender.tick()
        i = next(k for k, (p, _) in enumerate(stamps) if p[12] == SYNC)
        t0, rows = stamps[i][1], stamps[i + 1 :]
        assert len(rows) == sends == len(sender.rows)
        for k, (p, t) in enumerate(rows):                                     # 121 us apart at 128 sends, 40 at 384
            assert abs(t - (t0 + ROW_SPREAD_NS * (k + 1) // sends)) <= 3 * clock.step, k
        assert rows[-1][1] - t0 <= ROW_SPREAD_NS + 3 * clock.step             # the last still at 15.5 ms
        chunk = width * height // sends
        assert [(p[14], int.from_bytes(p[15:17], "big")) for p, _ in rows[:3]] == [(0, 0), (0, chunk), (1, 0)]
    finally:
        s.close()


def test_the_prime_and_a_restarts_prime_stay_a_burst(slot):
    sender, sock, clock, stamps = stamped(slot)
    sender.tick()                                                             # the start's prime
    assert kinds([p for p, _ in stamps]) == [ROW] * H
    assert stamps[-1][1] - stamps[0][1] <= 2 * clock.step                     # back to back: no wait between rows
    sender.tick()
    slot.h[PAUSE] = 1
    sender.tick()
    slot.h[PAUSE] = 0
    n = len(stamps)
    sender.tick()                                                             # the restart's prime
    again = stamps[n:]
    assert kinds([p for p, _ in again]) == [ROW] * H and again[-1][1] - again[0][1] <= 2 * clock.step
    sender.tick()                                                             # and the frame after it is paced
    rows = stamps[n + H + 1 :]
    assert stamps[n + H][0][12] == SYNC and len(rows) == H
    assert rows[-1][1] - stamps[n + H][1] >= ROW_SPREAD_NS - 3 * clock.step


def test_rows_that_miss_their_slot_are_counted_and_the_next_sync_holds(slot):
    sender, sock, clock, stamps = stamped(slot)

    def stall(n, p):
        stamps.append((p, clock.t))
        if p[12] == ROW and p[14] == 19 and slot.h[FRAMES] == 1:              # the second frame, right after row 19
            clock.t += 1_000_000                                              # the sender loses 1 ms: inside the margin
    sock.hook = stall
    for _ in range(4):
        sender.tick()
    step = ROW_SPREAD_NS // H
    expected = sum(1 for k in range(20, H) if 1_000_000 - (k - 19) * step > step)      # rows 20 to 22; row 23 by 32 us
    assert slot.h[ROWS_LATE] == expected == 3
    assert 1_000_000 - step <= slot.h[ROW_WORST] <= 1_000_000 - step + 3 * clock.step   # row 20, a slot into the ms
    syncs = [t for p, t in stamps if p[12] == SYNC]
    assert abs((syncs[2] - syncs[1]) - PERIOD_NS) <= 3 * clock.step           # the next sync on its deadline
    assert slot.h[FRAMES] == 3 and slot.h[LATE] == 0 and slot.h[SLIPS] == 0
    s = stats_of(slot.h)
    assert s["rows_late"] == 3 and 1000 - step / 1e3 <= s["row_worst_us"] <= 1000 - step / 1e3 + 30


def test_a_stall_past_the_margin_sends_every_row_and_makes_the_next_sync_late(slot):
    sender, sock, clock, stamps = stamped(slot)

    def stall(n, p):
        stamps.append((p, clock.t))
        if p[12] == ROW and p[14] == 60 and slot.h[FRAMES] == 1:              # the second frame, after row 60
            clock.t += 3_300_000                                              # 3.3 ms lost: past the 1.17 ms margin
    sock.hook = stall
    for _ in range(4):
        sender.tick()
    frames = bursts([p for p, _ in stamps])
    assert [kinds(f) for f in frames[1:]] == [[SYNC] + [ROW] * H] * 3        # every row of every frame went out
    # Rows 61 to 63 go at once; the next sync is about 1.46 ms late on a grid that does not move, so rows 0 to 4
    # of that frame find their slots (242 to 1 211 us) gone too, and row 5 (1 453 us) is back in its slot.
    assert slot.h[ROWS_LATE] == 3 + 5
    worst = 3_300_000 - (ROW_SPREAD_NS * 62 // H - ROW_SPREAD_NS * 61 // H)   # row 61: the stall less one slot
    assert worst <= slot.h[ROW_WORST] <= worst + 3 * clock.step
    syncs = [t for p, t in stamps if p[12] == SYNC]
    late = 3_300_000 - (PERIOD_NS - ROW_SPREAD_NS * 61 // H)                  # the stall less what was left of the frame
    measured = (syncs[2] - syncs[1]) - PERIOD_NS
    assert late <= measured <= late + 10 * clock.step                         # plus the reads on the way to the sync
    assert slot.h[LATE] == 1 and slot.h[SLIPS] == 0 and slot.h[FRAMES] == 3  # late (over 1 ms), no slip: the grid holds


def test_a_fresh_frame_reaches_the_paced_rows_a_packet_at_a_time(slot):
    sender, sock, _ = make(slot)
    sender.tick()
    sender.tick()                                                             # the prime, then a black frame
    other = np.random.default_rng(7).integers(0, 256, (H, W, 3), dtype=np.uint8)
    slot.write(other)
    sock.sent.clear()
    sender.tick()                                                             # the paced frame that takes it
    rows = [p for p in sock.sent if p[12] == ROW]
    assert rows == [p for y in range(H) for p in row_packets(y, other[y, :, ::-1])]      # every packet, BGR
    sock.sent.clear()
    sender.tick()                                                             # no push: the same rows again
    assert [p for p in sock.sent if p[12] == ROW] == rows


def test_a_torn_burst_leaves_no_mixed_frame_at_the_restarts_prime(slot):
    blue = np.zeros((H, W, 3), np.uint8)
    blue[..., 2] = 200
    sock = FakeSocket(fail={PRIME + 1 + 27: OSError(errno.EIO, "io")})      # frame 2, row 26: the swap half done
    sender, sock, _ = make(slot, sock)
    slot.write(red())
    sender.tick()                                                             # the prime: red
    slot.write(blue)
    sender.tick()                                                             # blue into the packets a row at a time, torn at 26
    assert slot.h[PAUSE] == 1
    slot.h[PAUSE] = 0                                                         # the pause cleared with no new push
    sock.sent.clear()
    sender.tick()                                                             # the restart's prime: one whole frame
    rows = [p for p in sock.sent if p[12] == ROW]
    assert len(rows) == H and all((row_pixels(p, W) == (200, 0, 0)).all() for p in rows)   # blue, BGR, every row
    assert kinds(sock.sent) == [ROW] * H                                      # a prime: no sync in front of it


def test_a_spread_of_zero_is_a_burst_with_no_row_counted_late(slot):
    sender, sock, clock, stamps = stamped(slot, row_spread_ns=0)
    for _ in range(3):
        sender.tick()
    syncs = [i for i, (p, _) in enumerate(stamps) if p[12] == SYNC]
    rows = stamps[syncs[0] + 1 : syncs[1]]
    assert len(rows) == H and rows[-1][1] - rows[0][1] <= H * clock.step      # one clock read a row, no wait
    assert slot.h[ROWS_LATE] == 0 and slot.h[ROW_WORST] == 0                  # a burst has no slots to miss
    with pytest.raises(ValueError):
        Sender(slot, sock.send, clock=clock.now, sleep=clock.sleep, row_spread_ns=PERIOD_NS)
    with pytest.raises(ValueError):
        Sender(slot, sock.send, clock=clock.now, sleep=clock.sleep, row_spread_ns=-1)
```

Rework `test_the_worst_wake_past_the_spin_margin_is_recorded` (lines 270 to 282): the paced sender sleeps only before the first sync, so the oversleep goes on the first sleep, not the fourth:

```python
def test_the_worst_wake_past_the_spin_margin_is_recorded(slot):
    clock = FakeClock()
    real_sleep = clock.sleep

    def oversleeps(seconds):
        real_sleep(seconds + (0.0025 if not clock.slept else 0.0))     # the first sleep (before the first sync) wakes 2.5 ms late
    clock.sleep = oversleeps
    sender, sock, _ = make(slot, clock=clock)
    for _ in range(8):
        sender.tick()
    s = stats_of(slot.h)
    assert 2400 < s["wake_worst_us"] < 2600                       # how late the sleep returned, at worst
    assert 400 < s["worst_us"] < 600                               # and so the sync, past the 2 ms spin
```

In `test_the_bgr_swap_writes_into_the_packets_without_a_copy` (lines 258 to 265) add after the existing assertion:

```python
        assert np.shares_memory(sender._bgr_rows, sender.packets) and np.shares_memory(sender._frame_rows, sender.frame)
        assert len(sender._bgr_rows) == len(sender._frame_rows) == len(sender.rows) == len(sender._row_due)
```

And in `test_syncs_sit_on_an_absolute_grid_with_no_drift` (line 194) replace the last assertion with:

```python
    assert len(clock.slept) == 1 and 0 < clock.slept[0] <= PERIOD_NS / 1e9   # one sleep, before the first sync; then never
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `cd /Users/trey/dev/codeisart-s2-format && /Users/trey/dev/codeisart/.venv/bin/python -m pytest tests/test_colorlight_sender.py -q 2>&1 | tail -15`
Expected: the paced tests fail (the rows still go out as a burst) and the spread-0 test raises `TypeError` on the `row_spread_ns` keyword; the grid test's sleep count fails (2 000 sleeps); the shares-memory test fails on `_bgr_rows`; the torn-burst test fails at its last line (the current code sends the restart's frame behind a sync when the pause was cleared before a paused tick). Pass on the current code: the reworked wake test (the current sender also sleeps before the first sync) and the fresh-frame test (the whole-frame swap keeps the packets whole); they pin what the new structure must keep. The rest pass.

- [ ] **Step 3: The paced rows**

In `show/display/colorlight_sender.py` change `Sender.__init__`'s signature and body (lines 218 to 235) to:

```python
    def __init__(self, slot: Slot, send: Callable[[bytes], int], *, clock: Callable[[], int] = time.perf_counter_ns,
                 sleep: Callable[[float], None] = time.sleep, period_ns: int = PERIOD_NS, spin_ns: int = SPIN_NS,
                 row_spread_ns: int = ROW_SPREAD_NS, parent_alive: Callable[[], bool] = lambda: True):
        self.slot, self.send, self.clock, self.sleep = slot, send, clock, sleep
        self.period, self.spin, self.parent_alive = period_ns, spin_ns, parent_alive
        if not 0 <= row_spread_ns < period_ns:
            raise ValueError(f"row_spread_ns {row_spread_ns} is not 0 to under the period {period_ns}")
        self.packets, self.pixels = row_buffers(slot.width, slot.height)
        self.rows = self.packets.reshape(-1, self.packets.shape[-1])
        n = len(self.rows)
        self._row_due = [row_spread_ns * (k + 1) // n for k in range(n)]      # each row's slot, ns after the deadline
        self._row_step = row_spread_ns // n if n else 0                       # one slot; 0: a burst, no row late
        chunks, chunk = self.pixels.shape[1], self.pixels.shape[2] // 3
        self.bgr = self.pixels.reshape(slot.height, chunks, chunk, 3)      # the same bytes, a pixel at a time
        self._shape = (slot.height, chunks, chunk, 3)                       # a frame, as the packets cut it
        self.frame = np.zeros((slot.height, slot.width, 3), np.uint8)      # black: the dark start
        self._bgr_rows = self.bgr.reshape(-1, chunk, 3)                     # the packets' pixels, a packet a row
        self._frame_rows = self.frame.reshape(-1, chunk, 3)                 # the taken frame, cut the same way
        self._dark = False                                                  # the parent-death drain: black only
        self._level = -1
        self._sync = bytearray(sync_bytes(0, 0))                            # the level's sync; the counter goes in
        self._counter = 0                                                   # the next sync's byte 14, wrapping
        self.deadline: int | None = None
        self._last_sync: int | None = None
        self._primed = False                                                 # a sync goes only after a whole frame
```

(Both reshapes are views: the packets' pixel bytes have a row stride that is the chunk count times the packet stride, so the two axes merge without a copy; checked for 128, 384, 512 and 512 x 192 on 2026-09-30, and pinned by the shares-memory test.)

Change the class docstring (line 216) to:

```python
    """One output frame a tick: the sync on its deadline, the rows paced across ROW_SPREAD_NS after it. Testable
    with a fake socket and a fake clock; the child runs it for real."""
```

Replace the take (lines 254 to 255):

```python
        if not self._dark and self.slot.take(self.frame):
            self.bgr[...] = self.frame.reshape(self._shape)[..., ::-1]       # BGR, in place, before the wait
```

with:

```python
        fresh = not self._dark and self.slot.take(self.frame)                # swapped into the packets below, a
                                                                             # packet a slot: the whole frame is
                                                                             # 800 us at 512 x 192, the gap 1.17 ms
```

Replace the send block of `tick` (lines 268 to 280, from `at = self.clock()` to `return True` of the `except`) with:

```python
        at = self.clock()
        bgr, src = self._bgr_rows, self._frame_rows
        try:
            if self._primed:
                self._sync[COUNTER_OFFSET] = self._counter
                self.send(bytes(self._sync))
                self._counter = (self._counter + 1) & 0xFF
                for i, (off, row) in enumerate(zip(self._row_due, self.rows)):   # each row in its slot on the grid
                    if fresh:
                        bgr[i] = src[i, :, ::-1]                             # this packet's pixels, BGR, in its slot
                    late = spin_until(self.deadline + off, self.clock)
                    self.send(row.data)
                    if self._row_step:                                       # 0 is a burst (the bench): not counted
                        if late > self._row_step:                            # past the next slot's start: missed
                            h[ROWS_LATE] += 1
                        if late > h[ROW_WORST]:
                            h[ROW_WORST] = late
            else:
                if not self._dark:                                           # the prime: the whole frame swapped
                    self.bgr[...] = self.frame.reshape(self._shape)[..., ::-1]   # (whole again after a torn burst)
                for row in self.rows:                                        # then a burst, no sync before it
                    self.send(row.data)
        except OSError as e:
            h[ERRNO] = e.errno or 0
            h[ERRORS] += 1
            h[PAUSE] = 1                                                     # nothing more until a push
            self._primed = False                                             # and then a prime, whole again
            return True
```

(The one added line in that branch: `self._primed = False`. Before it, de-priming happened only in the `PAUSE` branch of a later tick; a pause cleared before that tick ran would send the next frame behind a sync, and with the per-packet swap a burst torn half-way leaves mixed rows in the packets until a prime swaps the whole frame. In production `push` writes a frame before it clears the pause, so the take would have refreshed the packets anyway; the line makes the prime not depend on that ordering.)

Also update the `tick` docstring (line 244): `"""One frame on its deadline (the sync, then the rows in their slots), or a paused poll. False once the stop flag is set (nothing sent)."""`

- [ ] **Step 4: Run the sender's tests**

Run: `cd /Users/trey/dev/codeisart-s2-format && /Users/trey/dev/codeisart/.venv/bin/python -m pytest tests/test_colorlight_sender.py -q 2>&1 | tail -5`
Expected: all pass, `test_a_frame_on_the_wire_is_the_winning_spike_runs_frame` among them, unedited.

- [ ] **Step 5: The rest of the colorlight suite**

Run: `cd /Users/trey/dev/codeisart-s2-format && /Users/trey/dev/codeisart/.venv/bin/python -m pytest tests/test_colorlight_packets.py tests/test_colorlight_sender.py tests/test_colorlight.py tests/test_colorlight_slot.py tests/test_colorlight_child.py tests/test_wall_hold.py tests/sender_spike -q 2>&1 | tail -5`
Expected: all pass. `test_colorlight_child.py` runs the real child on a socketpair (a frame now takes 16.7 ms of real time, as before); `test_wall_hold.py` models the sender at `OUTPUT_FPS`.

- [ ] **Step 6: Commit**

```bash
cd /Users/trey/dev/codeisart-s2-format
git add show/display/colorlight_sender.py tests/test_colorlight_sender.py
git commit -m "feat(colorlight): the rows paced across 15.5 ms on the sync's grid, one a slot, the BGR swap a packet at a time inside it; a row past the next slot counted, the worst kept; the prime still a burst"
```

---

### Task 3: The log line, and the words in the facade, the tools and the deploy README

**Files:**
- Modify: `show/display/colorlight.py` (the docstring, lines 1 to 3; `stats_line`, lines 264 to 267)
- Modify: `tools/wall_pattern.py:18-19`, `tools/wall_video.py:10`, `deploy/README.md:86-87`
- Test: `tests/test_colorlight.py:245-256`, `tests/test_wall_pattern.py:258-262`, `tests/test_deploy.py:62-64`

**Interfaces:**
- Consumes: `stats_of`'s `rows_late` and `row_worst_us` (Task 1).
- Produces: the log line `colorlight sender: %d frames, %d late (over 1 ms), worst %.0f us, sync to sync sd %.0f us, %d rows off their slot, worst row %.0f us late, %d slips, %d send errors, %d restarts, real-time %s, the sleep woke at worst %.0f us late`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_colorlight.py::test_stats_and_the_line_for_the_log` (line 253) change the assertion to:

```python
    assert "5 frames" in line and "0 rows off their slot" in line and "real-time no" in line
```

In `tests/test_wall_pattern.py::test_run_prints_the_senders_stats_at_the_end` (lines 261 to 262) change the stub to:

```python
            return {"frames": 5, "late": 0, "slips": 0, "worst_us": 30.0, "mean_us": 0.0, "sd_us": 4.0,
                    "errors": 0, "restarts": 0, "rt": True, "wake_worst_us": 0.0, "rows_late": 0, "row_worst_us": 12.0}
```

In `tests/test_deploy.py::test_readme_says_the_sender_needs_cap_sys_nice` (line 64):

```python
    assert "CAP_SYS_NICE" in text and "60.00 frames" in text and "60.32 frames" not in text and "59 frames" not in text
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `cd /Users/trey/dev/codeisart-s2-format && /Users/trey/dev/codeisart/.venv/bin/python -m pytest tests/test_colorlight.py::test_stats_and_the_line_for_the_log tests/test_deploy.py::test_readme_says_the_sender_needs_cap_sys_nice tests/test_wall_pattern.py::test_run_prints_the_senders_stats_at_the_end -q 2>&1 | tail -8`
Expected: the first two fail (no "rows off their slot"; the README says 60.32); the third passes (the stub only gained keys) and is here to keep passing after `stats_line` reads them.

- [ ] **Step 3: The line and the words**

In `show/display/colorlight.py` replace `stats_line`'s return (lines 264 to 267) with:

```python
    return ("colorlight sender: %d frames, %d late (over 1 ms), worst %.0f us, sync to sync sd %.0f us, %d rows off "
            "their slot, worst row %.0f us late, %d slips, %d send errors, %d restarts, real-time %s, the sleep woke "
            "at worst %.0f us late"
            % (s["frames"], s["late"], s["worst_us"], s["sd_us"], s["rows_late"], s["row_worst_us"], s["slips"],
               s["errors"], s["restarts"], "yes" if s["rt"] else "no", s.get("wake_worst_us", 0.0)))
```

and its docstring (lines 1 to 3) to:

```python
"""Raw Ethernet driver for the Colorlight 5A-75B/E receiving card (Linux only, needs CAP_NET_RAW), as a steady
sender: whatever rate the caller pushes at, the card gets OUTPUT_FPS (60.00) frames a second from a child process,
the sync first (the S2 sender card's format) within 100 us of its deadline, then the rows paced across the 15.5 ms
after it (the card shows rows as they land; a burst tears), the pixels BGR
(show/display/colorlight_sender.py). The spec: docs/superpowers/specs/2026-09-29-route-a-steady-sender-design.md;
```

(the rest of that docstring stays.)

In `tools/wall_pattern.py` (lines 18 to 19): `On the colorlight backend the driver sends 60.00` / `frames a second from a child process whatever --fps is, the rows paced across each frame (--fps paces the pushes only), and prints the sender's` (keep the rest of the sentence). In `tools/wall_video.py` (line 10): `the colorlight driver sends 60.00 a second whatever --fps is, the rows paced across each frame.`

In `deploy/README.md` (lines 86 to 87) replace the sentence from `(SCHED_FIFO 50), 60.32 frames a second` through `00-path-forward.md).` with:

```
(SCHED_FIFO 50), 60.00 frames a second whatever the show's `fps`, in the S2 sender card's format with
the rows paced across each frame, which the card draws clean
(docs/superpowers/reviews/2026-09-30-ghosting/08-wall-session-evening.md). The child spins its core for
the whole frame, pinned to the highest core it may use; the show's threads keep the others.
```

- [ ] **Step 4: Run the tests**

Run: `cd /Users/trey/dev/codeisart-s2-format && /Users/trey/dev/codeisart/.venv/bin/python -m pytest tests/test_colorlight.py tests/test_wall_pattern.py tests/test_deploy.py tests/test_wall_video.py -q 2>&1 | tail -5`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/trey/dev/codeisart-s2-format
git add show/display/colorlight.py tools/wall_pattern.py tools/wall_video.py deploy/README.md tests/test_colorlight.py tests/test_wall_pattern.py tests/test_deploy.py
git commit -m "feat(colorlight): the log line counts the rows off their slot and the worst row; the facade's, the tools' and the deploy README's words follow 60.00 and the paced rows"
```

---

### Task 4: The bench child's spread knob becomes the driver's own

**Files:**
- Modify: `docs/superpowers/reviews/2026-09-30-ghosting/bench/ghost_child.py` (whole file), `bench/ghost_knobs.py:49-50`, `bench/direct_play.py:60,63,91-93`, `bench/arcade_knobs.py:42-43`

**Interfaces:**
- Consumes: `Sender(..., row_spread_ns=)` (Task 2), `cs.ROW_SPREAD_NS`, `cs.PERIOD_NS`.
- Produces: `GHOST_SPREAD_MS` unset is the driver's 15.5; `0` is a burst; the rows-sync order knob kept without its own pacing.

The bench child paced the rows itself by wrapping `send`; with the driver pacing, that wrapper would pace twice. It now hands the spread to the driver. No test file covers the bench (it is not part of the repo's code); the check is a construction by hand in step 2.

- [ ] **Step 1: Rewrite `ghost_child.py`**

```python
"""Bench (2026-09-30, not part of the repo): the colorlight sender's child with one knob from the environment,
for the ghosting review's sender-side trials. Everything else is show.display.colorlight_sender as it stands.

    GHOST_FPS          output frames a second (the driver's 60.00)
    GHOST_SPREAD_MS    the rows spread over this many ms after the sync, handed to the driver's own pacing (the
                       driver's 15.5, the evening's answer at 60.00); 0: a burst
    GHOST_ORDER        sync-rows (the driver's) or rows-sync (the sync held until the last row has gone)
    GHOST_COUNTER      on (the driver's) or off: byte 14 frozen at 0
    GHOST_SYNC_REPS    syncs a frame (the driver's 1); 2 in the S2 format is a black wall

Started only by ghost_knobs.py, in place of `python -m show.display.colorlight_sender`, with the same arguments.
"""
import os
import sys

from show.display import colorlight_sender as cs

FPS = float(os.environ.get("GHOST_FPS", cs.OUTPUT_FPS))
COUNTER_OFF = os.environ.get("GHOST_COUNTER", "on") == "off"
SYNC_REPS = int(os.environ.get("GHOST_SYNC_REPS", "1"))
SPREAD_MS = os.environ.get("GHOST_SPREAD_MS")                 # None: the driver's own spread
ORDER = os.environ.get("GHOST_ORDER", "sync-rows")            # or rows-sync: the rows first, the sync after the last
if ORDER not in ("sync-rows", "rows-sync"):
    raise SystemExit("ghost_child: GHOST_ORDER is sync-rows or rows-sync")
if not 1 <= SYNC_REPS <= 3:
    raise SystemExit("ghost_child: GHOST_SYNC_REPS is 1 to 3")
if not 50.0 <= FPS <= 65.0:
    raise SystemExit("ghost_child: GHOST_FPS out of range (50..65)")
cs.OUTPUT_FPS = FPS
cs.PERIOD_NS = round(1e9 / FPS)
cs.CLOSE_FRAMES = round(cs.CLOSE_HOLD_S * FPS)
SPREAD_NS = cs.ROW_SPREAD_NS if SPREAD_MS is None else round(float(SPREAD_MS) * 1e6)
if not 0 <= SPREAD_NS < cs.PERIOD_NS:
    raise SystemExit("ghost_child: GHOST_SPREAD_MS is 0 to under the period (%.2f ms); over 64.5 frames a second the "
                     "driver's 15.5 is not, so set it" % (cs.PERIOD_NS / 1e6))


class Sender(cs.Sender):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("period_ns", cs.PERIOD_NS)       # the class's defaults were bound at the driver's rate
        kwargs.setdefault("row_spread_ns", SPREAD_NS)
        super().__init__(*args, **kwargs)
        if ORDER == "rows-sync":                           # the sync held back until the last row has gone
            inner, n_rows = self.send, len(self.rows)
            state = {"held": None, "k": 0}

            def rows_then_sync(packet):
                if packet[12] == 0x01:
                    state["held"], state["k"] = packet, 0
                    return len(packet)
                n = inner(packet)
                state["k"] += 1
                if state["k"] >= n_rows and state["held"] is not None:
                    inner(state["held"])
                    state["held"] = None
                return n
            self.send = rows_then_sync
        if SYNC_REPS > 1:                                  # every sync goes out SYNC_REPS times, back to back
            inner = self.send

            def send_reps(packet):
                n = inner(packet)
                if packet[12] == 0x01:
                    for _ in range(SYNC_REPS - 1):
                        inner(packet)
                return n
            self.send = send_reps

    def tick(self):                                        # GHOST_COUNTER=off: byte 14 stays 0 (bench, 2026-09-30 evening)
        ok = super().tick()
        if COUNTER_OFF:
            self._counter = 0
        return ok


cs.Sender = Sender
sys.exit(cs.main(sys.argv[1:]))
```

In `ghost_knobs.py` (lines 49 to 50) the defaults printed become `"60.00"` and `"15.5"`. In `direct_play.py`: line 60's help `"the sender's rate (bench child): 60.00 unless set"`, line 63's help `"rows spread over this many ms after the sync (bench child); 15.5 unless set; 0 is a burst"`, and the print at 91 to 93 defaults `'60.00'` and `'15.5'`. In `arcade_knobs.py` (line 43) the default printed becomes `"60.00"`.

- [ ] **Step 2: Check the child by hand (no card, no socket)**

Run:

```bash
cd /Users/trey/dev/codeisart-s2-format && GHOST_SPREAD_MS=14 /Users/trey/dev/codeisart/.venv/bin/python - <<'EOF'
import runpy, sys
sys.argv = ["ghost_child.py"]
try:
    runpy.run_path("docs/superpowers/reviews/2026-09-30-ghosting/bench/ghost_child.py", run_name="__main__")
except IndexError:
    pass                                   # the sender's main with no arguments: the module loaded and its knobs parsed
from show.display import colorlight_sender as cs
from tests.colorlight_fakes import FakeSocket, FakeClock
s = cs.Slot.create(128, 64); sock = FakeSocket(); c = FakeClock()
snd = cs.Sender(s, sock.send, clock=c.now, sleep=c.sleep)
print(type(snd).__module__, snd._row_due[-1], snd._row_step, cs.OUTPUT_FPS, cs.PERIOD_NS)
s.close()
EOF
```

Expected: `__main__ 14000000 218750 60.0 16666667` (the bench's subclass, run as a main module; the last slot at 14 ms, a slot of 218.75 us, the driver's rate).

Then `cd /Users/trey/dev/codeisart-s2-format && GHOST_SPREAD_MS=17 /Users/trey/dev/codeisart/.venv/bin/python docs/superpowers/reviews/2026-09-30-ghosting/bench/ghost_child.py; echo "exit $?"` — expected: `ghost_child: GHOST_SPREAD_MS is 0 to under the period (16.67 ms); over 64.5 frames a second the driver's 15.5 is not, so set it` and `exit 1`.

- [ ] **Step 3: Commit**

```bash
cd /Users/trey/dev/codeisart-s2-format
git add docs/superpowers/reviews/2026-09-30-ghosting/bench/
git commit -m "docs(ghosting): the bench child hands its spread to the driver's own pacing; the bench's words at 60.00 and 15.5"
```

---

### Task 5: Verification: the whole suite, a dry run, the timing by hand, and the record

**Files:**
- Modify: `docs/superpowers/plans/2026-09-30-paced-rows.md` (a "Done" section at the end)

- [ ] **Step 1: The whole suite, timed**

Run: `cd /Users/trey/dev/codeisart-s2-format && /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -x 2>&1 | tail -5`
Expected: everything passes. Then the colorlight suite alone with its time: `... -m pytest tests/test_colorlight_packets.py tests/test_colorlight_sender.py tests/test_colorlight.py tests/test_colorlight_slot.py tests/test_colorlight_child.py tests/test_wall_pattern.py tests/test_deploy.py tests/sender_spike -q --durations=3 2>&1 | tail -8`. Expected: passes; the three slowest tests named (the 2001-tick grid test is the one to watch; under 3 s is fine).

- [ ] **Step 2: A dry run of the driver on this machine (no card, no root)**

Run: `cd /Users/trey/dev/codeisart-s2-format && /Users/trey/dev/codeisart/.venv/bin/python tools/wall_pattern.py rgb --dry-run --seconds 10 2>&1 | tail -3`
Expected: the sender's stats line with frames about 600 (60.00 x 10, the start's prime not counted), errors 0, slips 0, and the new fields `N rows off their slot, worst row M us late`. The late count, the worst and the rows are this machine's (a Mac without real-time priority, the child unpinned) and are not judged; they are recorded.

- [ ] **Step 3: The timing on a fake wire, by hand**

Run:

```bash
cd /Users/trey/dev/codeisart-s2-format && /Users/trey/dev/codeisart/.venv/bin/python - <<'EOF'
from tests.colorlight_fakes import FakeSocket, FakeClock
from show.display.colorlight_sender import Sender, Slot, ROWS_LATE, ROW_WORST
s = Slot.create(128, 64); sock = FakeSocket(); c = FakeClock(); stamps = []
sock.hook = lambda n, p: stamps.append((p[12], p[14], c.t))
snd = Sender(s, sock.send, clock=c.now, sleep=c.sleep)
for _ in range(3): snd.tick()
syncs = [i for i, (k, _, _) in enumerate(stamps) if k == 1]
t0 = stamps[syncs[0]][2]
rows = stamps[syncs[0] + 1 : syncs[1]]
print(len(rows), [(r, (t - t0) // 1000) for k, r, t in rows[:3]], (rows[-1][2] - t0) // 1000, (stamps[syncs[1]][2] - rows[-1][2]) // 1000)
print(int(s.h[ROWS_LATE]), int(s.h[ROW_WORST]), len(c.slept))
s.close()
EOF
```

Expected: `64 [(0, 240), (1, 480), (2, 720)] 15490 1180` (the first three rows at 242, 484 and 726 us after the sync's deadline, the last at 15.5 ms, then 1.17 ms to the next sync; the sync's own stamp is 10 to 20 us past its deadline and the division floors, so the row numbers read up to 20 us under and the gap up to 20 us over) and `0 N 1` with N under 10000 (no row off its slot, a worst under one clock step, one sleep in three ticks).

- [ ] **Step 4: Write the record and commit**

Append to this plan a `## Done` section with: the suite's count and time, the three slowest tests, the stats line of the dry run, the numbers of step 3, the adversarial review's findings and what was done with each, and the wall checks owed. The owed checks, the owner's, from the Pi (`trey@codeisart.local`, `~/codeisart` on `s2-format`, after `git fetch` and `git reset --hard origin/s2-format` or a pull, sudo for the runs), in his order:

1. The video (`direct_play.py video` or `wall_video.py`) and the lobby (`arcade_load.py --wall`): the driver alone now, no bench child, no knobs. Expected: the video "zero flicker" as run 20, the lobby as run 24. The stats line at the end: worst sync under 100 us, `0 rows off their slot` (or a handful with a worst row under a slot or two: a few tens of us).
2. The line picture (`ghost_map.py 8 --step 0 --row 18`): no copy.
3. Levels 0.1 and 0.4 (`wall_pattern.py rgb --brightness 0.4`, the lobby at 0.4): the same picture, brighter; no copy at 0.4.
4. The show's own wall size (`wall_pattern.py rgb --width 512 --height 192` and `border`; then `--width 512 --height 64`): 384 row packets a frame in 40 us slots, then 128 in 121 us slots; neither on the card before in this format. Expected: clean; the stats line's rows off their slot at 0 or near it and the worst row under a slot. This is the gate for the send's own cost inside a 40 us slot, which no dry run can measure (a dry run's send is `len`).
5. The restart blink (the line picture `--stop-for 5`, three times): the picture holds through the stop; whether the bright first frame at the restart is still there with the paced rows (the report banked it as not a safety concern; this tells whether the pacing changed it). One thing the wall has not seen: the bench child paced its prime too (`t0` at the first row), the driver bursts it as instructed, so a burst prime followed by paced frames is new here, and this check is where it would show.
6. Then the soaks: `tools/show_soak.py` two and five minutes, then the overnight. What to read: slips (a stall of tens of ms once a second would be the fair server handing the core to a fair thread; the fix would be pinning the parent off the sender's core), rows off their slot, the worst row.

Open from the report and not settled by this slice: the lobby's last flicker in 30 s at 60.00 (a 240 fps clip at fixed exposure would place it); the prime as a burst (kept; a paced prime is a knob away if the restart's first frame looks wrong).

Then:

```bash
cd /Users/trey/dev/codeisart-s2-format
git add docs/superpowers/plans/2026-09-30-paced-rows.md
git commit -m "docs(paced-rows): the plan's record: suite, dry run, the timing by hand, the review's findings, the owed wall checks"
```

Do not push. Do not merge. Nothing to the card.

## Done (2026-09-30, on branch `s2-format`, not merged, not pushed)

Built in `/Users/trey/dev/codeisart-s2-format` from 035b0d6 (the S2-format branch with the evening's report), executed
inline task by task with TDD after a fresh-context adversarial review of the plan; a fresh-context review of the whole
branch at the end and one fix pass. Nothing went to the card. Commits: df9dd49 (Task 1), d792082 (Task 2), 3db8e7d
(Task 3), 8461b54 (Task 4), 7bd94d5 (the fix pass), then this record.

**The suite.** Whole suite after Task 4: 1759 passed, 4 skipped in 315.85 s (0:05:15); after the fix pass:
1761 passed, 4 skipped in 307.86s (0:05:07). The colorlight suite (`test_colorlight*.py`, `test_wall_pattern.py`, `test_deploy.py`,
`sender_spike`) after Task 4: 484 passed, 2 skipped in 3.53 s; the three slowest: the 2001-tick grid test 0.35 s, the
child's process-leak test 0.29 s, the child's socketpair test 0.22 s (the paced tick's 1 600 fake-clock reads cost
nothing that shows).

**The dry run** (`tools/wall_pattern.py rgb --dry-run --seconds 10` on the Mac, no card, no root, the child unpinned
and without real-time priority, the whole suite running beside it): `599 frames, 1 late (over 1 ms), worst 1667 us,
sync to sync sd 68 us, 31 rows off their slot, worst row 2669 us late, 0 slips, 0 send errors, 0 restarts, real-time
no, the sleep woke at worst 3664 us late`. The frame count is the rate (60.0 a second); the sync-to-sync spread of
68 us is a tenth of the previous plan's Mac number (680 us), the never-sleeping spin holding the grid; the late rows
and the worst are this machine's and are not judged. Running from a worktree: `tools/wall_pattern.py` puts its own
root on the path, so the dry run is the branch's; a bench script run by its path resolves `show` to the main checkout
through the venv's editable install (main's 59) unless `PYTHONPATH` names the worktree, which `ghost_knobs.py` does
for its child and Task 4's check now does too.

**The timing by hand** (Task 5 step 3), exactly as expected: `64 [(0, 240), (1, 480), (2, 720)] 15490 1180` and
`0 9896 1`: 64 rows, the first three 242, 484 and 726 us after the sync's deadline (the sync's own stamp 10 to 20 us
past it, the division flooring), the last at 15.5 ms, then 1.17 ms of quiet to the next sync; no row off its slot, a
worst under one clock step, one sleep in three ticks.

**The measurements the plan rests on** (the Pi 5, `trey@codeisart.local`, 2026-09-30, numpy only, no socket): the
frame copy 1 to 4 us at 128 x 64 and 13 to 50 us at 512 x 192; the whole-frame BGR swap 67 to 83 us at 128 x 64 and
789 to 809 us at 512 x 192; the per-packet swap 2.3 to 2.7 us a packet at 128 x 64 (64 packets, 242 us slots) and 3.5
to 3.6 us at 512 x 192 (384 packets, 40 us slots). The kernel: `6.18.50+rpt-rpi-2712`, 4 cores, `CONFIG_RT_GROUP_SCHED`
not set, `CONFIG_PREEMPT=y`, `CONFIG_HZ=250`, `sched_rt_runtime_us` 950000, `NO_RT_RUNTIME_SHARE`, the fair server on
cpu3 at 50 ms per 1 s.

**The adversarial plan review** (before execution; 4 Important, 5 Minor) and what was done:
- I1 a pause cleared before a paused tick has run would send the next frame behind a sync, and with the per-packet
  swap a burst torn half-way leaves mixed rows until a prime: `self._primed = False` added to the `except OSError`
  branch (the one line in a branch the instruction called untouched; the restart primes either way, now without
  depending on the push's ordering); `test_a_torn_burst_leaves_no_mixed_frame_at_the_restarts_prime` asserts the
  prime.
- I2 the stall-past-the-margin test's count: 8 rows, not 3 (the rows behind the late sync miss their slots too, the
  grid not moving); the stall 3.3 ms so the boundary row clears its slot by 84 us.
- I3 the show's wall is 512 x 192 (`show/config.py`): 384 packets in 40 us slots, the send's own cost inside a slot
  unmeasurable without the card; `(512, 192, 384)` in the wide-wall test; wall check 4 at that size is the gate.
- I4 the repo's rule "never a pure busy-wait (it stalled 37 ms once)" named in the constraints, `wait_until`'s
  docstring and the spec's line 41 (the spike's stall was unpinned; the evening's paced child spun pinned and was
  clean; the owner's instruction is the paced rows); the kernel config read from `/proc/config.gz`; the per-CPU
  kernel threads and heat named as what the soak reads for.
- M5 to M9: the expected failures of Task 2 step 2, the by-hand numbers (20 us under, the division flooring), "a slip
  never sleeps", no worst kept at a spread of 0, the README's line numbers and the bench child's message.
- The review also confirmed: the plan's timing is the bench child's within the sync's lateness; the last row lands
  at 15.49 ms in a steady stream, after a late sync, after a slip, in the drain and at the close.
- Mid-plan, before the review: the tick's top (the frame copy and the BGR swap) now sits in the 1.17 ms gap before
  the sync instead of 15 ms of idle; the Pi's numbers above made the whole-frame swap a threat to the sync's 100 us
  on the show's wall, so the swap moved into the row loop, a packet a slot; the prime swaps the whole frame.

**The branch review** (after execution; no Critical, 2 Important, 5 Minor; "ready for the owner's wall checks as it
stands"):
- Fixed: the per-packet swap's pixels were pinned only at 128 wide (one packet a row); the fresh-frame test now runs
  at (128, 64), (512, 4) and (384, 4), and was proved by a mutation (the frame cut chunk-major: the two wide cases
  failed, the narrow one passed). Fixed: the deploy README's "the show's threads keep the others", which nothing
  enforces; now "nothing yet keeps the show's threads off it", pinned by `test_deploy.py`.
- Deferred (minor): a 203-character docstring line in the sender and long ones in the two tools; `late` reused for
  the row's and the sync's lateness; the stall test's comment gives the fake clock's arithmetic (five rows) where a
  real clock gives four; stale "burst" wording where it now means a frame; the module docstring could name the 384
  slots of 40 us.
- Rulings on what the reviewer set aside: the wall-proven settings stand (the owner's rule); the core's spin, heat
  and the fair server are the soak's to prove; the prime as a burst is the instruction (wall check 5); a stall between
  the margin and a period puts a partial burst behind the late sync on purpose (the fixed grid keeps the last row's
  margin, the rows are counted); the row-late count measures the wait's end, not the departure (wall check 4's
  gate); `colorlight_packets.py:12`'s "at 60.32" wording is a follow-up (the file was not to be edited); the drain's
  first tick after a primed stream sends a sync of black (pre-existing).
- The reviewer's own probes: the paced path's pixels against `row_packets` at 512 x 192, 512 x 64 and 384 x 4,
  identical; torn at row 26 then a push before the restart gives a whole prime of the pushed frame; torn then parent
  death gives 61 black bursts; a 20 ms stall inside the rows: no slip, one late sync, 80 rows counted, the next sync
  back on the grid; nothing in the repo hardcodes the header's old 128 bytes.

**Rulings made in execution:** `tests/test_colorlight_child.py` (outside the plan's file list) waits for
`FRAMES >= 3` with its existing deadline instead of asserting it the instant the third sync is read: a frame counts
after its last row, now up to 15.5 ms behind its sync, and the old assertion raced the rows (the sender is right).
Task 4's second check runs with `PYTHONPATH` set to the worktree (see the dry run above).

**Owed at the wall, the owner's, from the Pi** (`trey@codeisart.local`, `~/codeisart` on `s2-format`: `git fetch`
and `git reset --hard origin/s2-format` once the branch is pushed, or the commits carried over; `sudo` for the runs),
in his order:
1. The video (`direct_play.py video` or `wall_video.py`) and the lobby (`arcade_load.py --wall`): the driver alone
   now, no bench child, no knobs. Expected: the video as run 20 ("zero flicker"), the lobby as run 24. The stats
   line at the end: worst sync under 100 us, `0 rows off their slot` (or a handful, the worst row under a slot or
   two, a few tens of us).
2. The line picture (`ghost_map.py 8 --step 0 --row 18`): no copy.
3. Levels 0.1 and 0.4 (`wall_pattern.py rgb --brightness 0.4`, the lobby at 0.4): the same picture, brighter; no copy
   at 0.4.
4. The show's own wall size (`wall_pattern.py rgb --width 512 --height 192` and `border`; then `--width 512
   --height 64`): 384 packets a frame in 40 us slots, then 128 in 121 us slots; neither on the card before in this
   format. Expected: clean; rows off their slot at 0 or near it, the worst row under a slot. This is the gate for the
   send's own cost inside a 40 us slot, which no dry run can measure.
5. The restart blink (the line picture `--stop-for 5`, three times): the picture holds through the stop; whether the
   bright first frame at the restart is still there with the paced rows. The bench child paced its prime too; the
   driver bursts it as instructed, so a burst prime before paced frames is new here.
6. Then the soaks: `tools/show_soak.py` two and five minutes, then the overnight. Read for: slips or a worst sync of
   tens of ms about once a second (the fair server handing the sender's core to a fair thread: the fix would be
   pinning the show's threads off that core); rows off their slot and the worst row; `vcgencmd get_throttled` (one
   core at 100% for the whole show).

Open from the report and not settled here: the lobby's last flicker in 30 s at 60.00 (a 240 fps clip at fixed
exposure would place it); the prime as a burst (a paced prime is a knob away if check 5 looks wrong).
