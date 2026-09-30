# 04: Code audit of the wall driver against the measured hardware

Lane 4 of 5. Read-only audit; nothing was edited, committed, run against the wall, or tested with the suite.

Roots used below:
- `R` = `/Users/trey/dev/codeisart` (main, head 0fd3f40). Paths without a prefix are under `R`.
- `L` = `/Users/trey/dev/codeisart-ledvision` (branch ledvision-card1). `hardware.md` means
  `L/docs/superpowers/workflow/evidence/hardware.md`; `cl_fpp_test.py` means
  `L/docs/superpowers/workflow/evidence/hardware/cl_fpp_test.py`.
- `refs/` = the scratchpad's `flicker/refs/` (another lane's downloads: Falcon Player source, issue 1849, captures).
- `show/display/colorlight.py`, `show/wall.py` and `tools/wall_pattern.py` are byte for byte the same in `R` and `L`
  (checked with `diff`).

Labels: CONFIRMED (our own measurement or a primary source read here), LIKELY, SPECULATIVE. "Not confirmed" means
no source was found; nothing is filled in.

---

## 0. The five findings that change the plan

1. **"Packet order" is not isolated by the measurements.** The sender that worked (`cl_fpp_test.py:81-92`) differs
   from the driver in three things at once: duplicates (brightness x2, sync x2), brightness on every frame, and where
   the idle time sits in the cycle. In a continuous stream the driver's order (sync, brightness, rows, idle) and the
   test sender's (brightness, rows, sync, idle) are the same cycle of packets; only the position of the pause
   differs. A reference capture of LEDVision itself driving firmware 13.39 shows the DRIVER's cycle, with every packet
   doubled: sync x2, brightness x2, each row x2, then ~39.6 ms idle, 25 fps (`refs/pcaps/pc/5A75B 13v39.pcapng`, read
   with `refs/tools/frames.py` and `seq.py`; CONFIRMED for that capture). Falcon Player's developer wrote that on 13.x
   "the only one that needs doubling ... is the 0x01 packet" and that the 0x0A packet "doesn't seem to be needed"
   (`refs/fpp-issue-1849.txt:292-294`; CONFIRMED as what the source says). So the most likely cause of "no picture"
   is the single sync packet, not the order (LIKELY). hardware.md itself records "sync x1 vs x2 not settled"
   (hardware.md:222-224). The existing script can settle it with its own flags (section 4, E2). Until then the only
   layout CONFIRMED to work on this card is the test sender's: B x2, rows, S x2 with no pause before the sync.
2. **The current driver is a flash hazard on this card, outside the governor's sight.** With it the old picture
   "stayed up and flashed hard" (hardware.md:207-208, CONFIRMED). At 20 and 30 fps even the working layout flickers
   (hardware.md:213-215, CONFIRMED). The governor bounds the frames that are sent; it assumes the wall shows each
   one steadily. Neither the show nor the arcade nor `wall_pattern.py` at its default 20 fps should run on the
   panels in front of people until the output is steady.
3. **A pump makes `close()` draining mandatory, and the driver's in-place packet buffer unsafe.** Two governed black
   frames pushed microseconds apart (show/wall.py:149-150) and then a socket close would reach the wall as nothing
   at all. And `push()` writing into the buffer the sender thread is reading (show/display/colorlight.py:131-133)
   would put mixed frames on the wire that the governor never passed.
4. **The hold's single sends are the pattern the card handled worst.** Q66's hold sends one frame, waits 1 s, sends
   one frame (show/wall.py:79-88). The card kept a stale or partial picture after 3 frames at 20 fps and needed 1 s
   at 60 fps to change (hardware.md:222-224, CONFIRMED). The hold's "quiet" half is supported by the log; its
   "one frame" half is not.
5. **Two assumptions of the safety design are contradicted by the card keeping its last frame:** `from_dark`
   (the wall is dark when the process starts) and "the arcade leaves the wall as it found it" (the arcade sends no
   black at exit). See G10 and G7.

---

## 1. Gap table

Columns: what the code assumes; what was measured; what the wall does; which tests pin today's behaviour.

### G1. Frame layout for firmware 13: duplicates and where the sync goes

| | |
|---|---|
| Assumption | One sync, then the rows, per push: show/display/colorlight.py:126 (`frame_packet` first, "shows the rows sent by the previous push"), :131-133 (rows). Docstring :16-18. One packet of each kind. |
| Measured | The driver put no picture on the wall; the old frame flashed hard (hardware.md:207-210, CONFIRMED). B x2, rows, S x2 put a picture up (hardware.md:211-213; `cl_fpp_test.py:83-90`, CONFIRMED). Which of the three differences is needed: not confirmed (finding 1). Falcon Player doubles sync and brightness for firmware >= 13 (`refs/fpp-ColorLight-5a-75.cpp:513-515, 543-550, 629-635, 661-666`, CONFIRMED) and sends brightness and rows in `PrepData` (:830) and the sync in `SendData` (:859). In its output thread the send comes first in a loop pass and the prepare after it (`refs/fpp-channeloutputthread.cpp:188, 208`), so on the wire Falcon Player's pause is between the rows and the sync, as in the driver (LIKELY: `Sequence::SendSequenceData` and `ProcessSequenceData` are not in `refs/`, the mapping to `SendChannelData` / `PrepareChannelData` at `refs/fpp-ChannelOutputSetup.cpp:615-648` is from memory). |
| On the wall | No picture; a held picture flashing hard. |
| Tests | tests/test_colorlight.py:76-85 (`test_push_sends_frame_packet_then_rows`: sync first, `1 + 4 * 2` packets): must change. :88-98 (`sock.sent[1:] == expected`): index and count change. :123-132 (`sock.sent[1] == frame_packet(0.4)`), :135-141 (`sock.sent[0] == frame_packet(0.4)`), :182-191 (`sock.sent[0][35] == 0`): all pin "the sync is the first packet of a push"; they change. tests/test_wall_pattern.py:183-191 (`sent[0]` brightness, `sent[1]` sync): changes. tests/test_wall_hold.py:17-39 (`TornDisplay(card=True)` models "the frame packet first shows the rows the last call left"): the model is wrong for the new layout; see section 2.3. Packet BYTES stay: tests/test_colorlight.py:61-73 do not change. |

### G2. Brightness packet cadence and count

| | |
|---|---|
| Assumption | One 0x0A packet on `set_brightness` (colorlight.py:116-119) and one every third push, between the sync and the rows (:45 `BRIGHTNESS_EVERY = 3`, :127-130). Docstring :22-25 reasons "back at the cap within 0.1 s at 30 Hz". |
| Measured | The working sender sent it twice on every frame (`cl_fpp_test.py:83-84`). Whether once a frame, or none, also works: not confirmed (`--no-dup` result is not in hardware.md). Falcon Player's developer: not needed, the sync packet carries the level (`refs/fpp-issue-1849.txt:292`). The earlier guess that a 0x0A every third push would show as a 10 Hz dip (hardware.md:198-201) was never tested, because the driver showed no picture at all. Brightness 10 % vs 23 %: same flicker (hardware.md:213). Whether the card honours the packet level on 13.17 is still owed (`steps`, hardware.md:311-313). |
| On the wall | Unknown in isolation. |
| Tests | tests/test_colorlight.py:144-164 (`test_brightness_packet_resent_every_3_pushes`, asserts `BRIGHTNESS_EVERY == 3` and the position "after the frame packet, before the rows") and :167-179 (`test_set_brightness_restarts_the_resend_count`): both are replaced. :123-128 (one packet on `set_brightness`) can stay. |

### G3. Pixel order

| | |
|---|---|
| Assumption | RGB: colorlight.py:13 ("pixels in RGB order (Falcon Player; Kubota's panel needed BGR)"), :72 (`row_packets` "(width, 3) RGB"), :131 (the frame copied as it is). |
| Measured | Sent R, G, B, W; the wall showed B, G, R, W, not mirrored: the card takes raw pixels as BGR (hardware.md:219-221, CONFIRMED). LEDVision's Guide 5 answers do not apply to the raw stream. |
| On the wall | Red and blue swapped. The show's green phosphor (51, 255, 51) looks the same; amber (255, 176, 0) turns blue-cyan; every arcade colour is wrong. It also matters for safety: the governor's saturated-red rule (arcade/flash.py:23, :39) would be judging blue pixels as red and red as blue. |
| Tests | tests/test_colorlight.py:40 and :43 (`payload[7:10] == bytes([255, 0, 0])` "RGB order, as Falcon Player", `[0, 0, 255]`): change. :53 uses green, which reads the same either way. :88-98 compares `push` to `row_packets`; it passes if both swap together, so it does NOT catch a missing swap: a new test must pin the bytes on the wire for a red pixel. |

### G4. Output rate tied to the content rate

| | |
|---|---|
| Assumption | One burst of packets per content frame, at the loop's rate. Show: show/main.py:364-391 paces steps at `cfg.fps`, 20 (show/config.py:43, show.toml:22), one push a step (:247, :309). Arcade: arcade/runner.py:610-627 ticks at `cfg.fps`, 30 (arcade/config.py:54, arcade.toml:36), one push a tick (:439, :553). Pattern tool: tools/wall_pattern.py:222-223, default 20 (:192, :255), refused over 60 (:50, :182-184). Nothing resends between content frames. Steps that push nothing: a render that failed with no last frame (show/main.py:306-307), no wall (:303-305), the hold (show/wall.py:81-82). |
| Measured | 20 fps: fast flicker. 30 fps: some flicker. 60 fps: steady (hardware.md:213-215, CONFIRMED, the owner judging by eye, one card timing: 960 Hz x16). Rates other than 20, 30, 60: not measured. Tolerance to jitter: not measured. |
| On the wall | The show flickers fast, the arcade flickers some, the pattern tool at its default flickers fast. |
| Tests | None pins "one burst per content frame" in the driver. The loops' pacing tests (tests/test_main_stop.py:242-264, tests/test_wall_pattern_governed.py:93-97 `MAX_FPS == 60.0`, :244-250 default `fps == 20.0`) stay as they are with a pump, because the content rate does not change. |

### G5. Bottom-row noise and the pause before the sync

| | |
|---|---|
| Assumption | The driver has no notion of a pause inside a frame; its pause is the whole content period, between the rows and the next push's sync. |
| Measured | With the sync right behind the last row (the test sender, 60 fps) the last row or two showed noise; 1 ms between the last row and the sync cleared the noise and brought back a slight flicker, with sleep and with busy-wait (hardware.md:216-218, CONFIRMED). No clean-and-steady setting yet. Not tried: the layout LEDVision and Falcon Player use, where the sync comes a whole idle period after the rows (`--gap-ms 12` at 60 fps does this with the existing script). |
| On the wall | Noise on rows 62-63, or slight flicker. |
| Tests | None. A fix adds a parameter (the delay from the last row to the sync) that needs its own tests. |

### G6. Ending a stream: how to land black

| | |
|---|---|
| Assumption | Two black frames are enough "the card shows a frame when the next one starts": show/wall.py:123, :149-150; tools/wall_pattern.py:196; deploy/README.md:24. The two go out back to back, microseconds apart, then the socket closes (:152). |
| Measured | 3 black frames at 20 fps left a stale picture ("top bars / all bars", so at least once a PARTLY updated picture). 1 s of black at 60 fps cleared it (hardware.md:222-224, CONFIRMED). The smallest number that lands: not measured. |
| On the wall | After `systemctl stop show`, Ctrl-C on the pattern tool, or the soak's end, the wall keeps a picture, possibly a torn one, until power off. The governor has counted black. |
| Tests | tests/test_wall_close.py:19-32 (`inner.count == 33`), :87-91 (`inner.count == 2`); tests/test_wall_close_hold.py:101, :124-128, :145, :175, :184 (`inner.calls == 6`, `== 3`); tests/test_main_stop.py:118-119 (`inner.count == 5`), :261 (`inner.count == 7`); tests/test_wall_pattern.py:146; tests/test_wall_pattern_governed.py:36 (`99 + 2`), :46. All of these count frames at the `Display.push` boundary. If the driver does the draining inside its own `close()` (resending the last pushed frame, which is the governed black), NONE of them changes. If `GovernedDisplay.close` is changed to push N black frames, all of them change. |

### G7. What `close()` and stop do today

| | |
|---|---|
| Driver | `ColorlightDisplay.close()` closes the socket, nothing else (colorlight.py:135-136). Pinned by tests/test_colorlight.py:131-132. |
| Show | `ShowLoop._close` (show/main.py:401-430) calls `GovernedDisplay.close` (show/wall.py:122-152): the counted frame if the last send failed, two governed black frames, display closed. In a hold it waits up to 2 s first (Q68). On this card: G6. |
| Arcade | arcade/main.py:161-164: `display.close()` only. No black at all, governed or not. Since the card keeps the last frame (CONTEXT "Keep the Last Frame"; hardware.md:162-164), the wall stays lit with the last game frame after the arcade exits or crashes (LIKELY: follows from two CONFIRMED facts, not itself observed). Pinned by tests/arcade/test_main.py:65 (`display.closed`). |
| Pattern tool | tools/wall_pattern.py:229-230: `wall.close()`, as the show. |
| SIGKILL, a crash, the watchdog | Nothing is sent. The wall keeps the last frame, possibly half of one. |

### G8. Docstring and document claims now known wrong

| Where | Claim | Status |
|---|---|---|
| colorlight.py:13 | "pixels in RGB order (Falcon Player; Kubota's panel needed BGR)" | Wrong for this card: BGR (G3). |
| colorlight.py:16-18 | "push() does the same, so the card shows a pushed frame when the next push starts" | On 13.17 the card showed no pushed frame (G1). |
| colorlight.py:22-25 | one brightness packet every 3 pushes brings a restarted card back to the cap "within 0.1 s at 30 Hz" | Untested; the working sender sends two a frame (G2). |
| colorlight.py:3-4 | "Constants diffed ... against Falcon Player's ... (master)" | True for the bytes (checked here against `refs/fpp-ColorLight-5a-75.cpp:531-534, 584-591, 648-655`). The doubling for firmware >= 13 in the same file was not taken over, though :23 mentions it. |
| colorlight.py:146-147 | "run under the arcade's systemd unit" | There is no arcade unit in the repository (`deploy/` holds only `show.service`). |
| show/wall.py:5-6, tools/wall_pattern.py:196, tests/test_wall_pattern.py:146 | two black frames darken the wall | G6. |
| deploy/README.md:24-25 | "sends two governed black frames ... then exits" | G6; also Q68 (gate.md:34). The file is the owner's. |
| deploy/README.md:1, :72-73 | "Pi 4", "a dedicated USB gigabit Ethernet adapter" | The steady 60 fps was measured on an Intel PCIe port (hardware.md:256). A USB adapter's timing is unmeasured. |
| deploy/README.md:77-85 | the LEDVision settings record, empty; "14 full color eight scan" following the Wired Watts guide | The real record is hardware.md:183-189; the decoder is ICN2018/3018, not the preset's 138. |
| Q65 (decisions.md:492) | "A pulled cable fails at the first packet" | Not confirmed, and doubtful on Linux: see G11. |

### G9. "Send nothing" is safe; one frame a second is enough (Q66, C51, C53)

| | |
|---|---|
| Assumption | After a failed send the wall sends nothing for `HOLD_S`, then the counted frame once, again 1 s later, then new frames (show/wall.py:32-33, :79-89). The card keeps the picture meanwhile, and a single frame changes it. |
| Measured | Keeps the picture with the sender stopped: yes, steady, for LEDVision's stream, about 8 s (241 frames at 30 fps) and 6 s (181 frames) on RAM settings (hardware.md:159-164, :177-178, CONFIRMED), and after the save to flash LEDVision's last frame stayed up from the VM's stop until the Linux tests (hardware.md:205-208, CONFIRMED that it stayed; its steadiness then is not stated). The no-signal action read back is "Keep the Last Frame". Q66's check as written (gate.md:26: after the last Save, stop the sender 3 s) has not been run with the Linux sender: LIKELY to pass. A single isolated frame changes the picture: contradicted (G6). What the wall does at the moment a stream stops or starts: not recorded. |
| On the wall | The quiet second is likely fine. The counted frame sent once may not appear, or appear in part; the governor then resumes from a frame the wall never showed. |
| Tests | tests/test_wall_hold.py:138-162, tests/test_main.py:289-300, tests/test_wall_close_hold.py (all). They test `GovernedDisplay` against fakes and stay valid if the hold keeps its form at that level and the driver turns "the counted frame" into a steady stream of it (section 2.3). |

### G10. `from_dark`: the wall is dark when the process starts (C52)

| | |
|---|---|
| Assumption | show/wall.py:57-58 primes the governor with black, unsent; show/main.py:188-190 and tools/wall_pattern.py:204 pass `from_dark=True`. |
| Measured | The card keeps its last frame without a sender, through minutes (G9). After a crash, a kill, a restart by systemd (`Restart=always`, `RestartSec=2`, deploy/show.service:12-13) or an arcade exit (G7), the wall is lit with the last picture when the next process starts. |
| On the wall | The first frame's change is counted against black, not against what is shown. One miscounted change per start; a crash loop repeats it every 2 s or more. |
| Tests | tests/test_wall_hold.py:165-189. They stay. The fix is in the driver's start (section 4, S2), which makes the assumption true. |

### G11. How a failure shows itself, and recovery

| | |
|---|---|
| Assumption | A broken link raises from `sock.send` inside `push`; the caller counts it (show/wall.py:154-161) and holds. |
| Doubt | On Linux an AF_PACKET send to an interface that is up but has no carrier is, as far as I know, dropped without an error; `ENETDOWN` comes only when the interface is down, `ENXIO` when it is gone (LIKELY, from the kernel's behaviour as I remember it; not confirmed here, and not in hardware.md). If so, a pulled cable or a card that lost power never starts the hold and never turns the lights off after `PUSH_DARK_S` (show/main.py:43, :330-340); the show believes the wall is fine. |
| Recovery | Neither loop reopens the display after failures. The show opens the wall only while `self.wall is None` (show/main.py:148, :242-244); the arcade never. A USB adapter that is unplugged and plugged back gets a new interface index; the old socket stays dead until the process restarts, and the watchdog is still petted (show/main.py:250), so systemd does not restart it (LIKELY). |
| Tests | tests/test_main.py:275-300 (`FailingPushes`), tests/test_wall_hold.py:215-234. They model the raise, not the silence. |

### G12. The governor's light model and the card's gamma

| | |
|---|---|
| Assumption | `gamma` is 1.0 ("the card applies gamma", light = (byte/255)^2.2) to 2.2 ("bytes as they are", light linear in the byte): arcade/look.py:71-78; checked at show/config.py:79-80, arcade/config.py:106-107, show/wall.py:31, :42-44, tools/wall_pattern.py:185-187. Both configs ship 2.2 (show.toml:8, arcade.toml:23). |
| Measured | The card's saved gamma is 2.8 (hardware.md:187). Whether it applies to the raw stream: not confirmed (the `gamma` pattern is still owed, hardware.md:311-313; Guide 5's colour answers do NOT apply to the raw stream, hardware.md:220-221, so other settings may not either). |
| Consequence | If the card applies 2.8, the model needs the exponent 2.8, which is `gamma = 2.2 / 2.8 = 0.79`, below the allowed 1.0. With the shipped 2.2 the governor misses real swings at the top of the range: byte 235 to 255 is 0.078 of full light in the linear model (under `THRESHOLD` 0.1, arcade/flash.py:21) and about 0.20 under gamma 2.8. `light_lut` itself accepts any gamma over 0, so arcade/flash.py need NOT change; the four range checks would. (SPECULATIVE until the `gamma` pattern is read on the wall.) |
| Tests | tests/test_config.py, tests/arcade/test_config.py (the range), tests/test_wall.py:70-72 (`gamma in (0.22, 22.0)` refused; 0.79 is between), tests/test_wall_pattern_governed.py:118-124. |

### G13. The brightness packet and the card's own level

| | |
|---|---|
| Assumption | The packet level is the power cap: 0.4 (colorlight.py:44, arcade.toml:17), 0.15 capped at 0.40 for the show (show.toml:3-4). |
| Measured | The card's saved Brightness Level is 3 (23 %) (hardware.md:187). How the packet level combines with it (replaces, multiplies): not confirmed. The test sender clamps to 0.4 and ran at 10 % and 23 % (`cl_fpp_test.py:71`, hardware.md:213). |
| Consequence | Unknown. If the packet replaces the card's level, the arcade's 0.4 is brighter than anything yet run on these supplies. `steps` answers it. |

### G14. The pattern tool's pacing

| | |
|---|---|
| Assumption | `sleep(1.0 / fps)` after each push (tools/wall_pattern.py:222-223): the period is 1/fps PLUS the render and the send. |
| Consequence | `--fps 60` gives less than 60 frames a second (the pattern is rebuilt every frame, the font file is loaded on every `rgb` and `panels` frame at :90, :152). The tool cannot produce the one rate measured steady. Default 20 fps flickers (G4). |
| Tests | tests/test_wall_pattern.py:140-157 and tests/test_wall_pattern_governed.py give `sleep=lambda s: None`; a deadline pace does not break them. |

### G15. The driver's shared packet buffer (a hazard for any pump, not a fault today)

`push` fills `self._pixels` in place and then sends from it (colorlight.py:104-109, :131-133). Today that is
one thread and correct. With a sender thread, a `push` in the middle of a burst changes rows that are not yet sent.
The arcade may also hand `push` its own canvas array: the governor returns "the same array" when nothing is held
(arcade/flash.py:135, :197), the runner clears that canvas on the next tick (arcade/runner.py:432). The pump must
take a private copy inside `push`.

---

## 2. The decoupling question: a 60 Hz pump

### 2.1 Where it lives

In `show/display/colorlight.py`, behind the unchanged `Display` protocol (show/display/__init__.py:24-27):

- `push(frame)`: check shape and dtype as today (:122-125), convert to the wire's pixel order, store a private copy
  as the pending frame, return. It sends nothing itself.
- The pump: every 1/`output_hz` it takes the pending frame (or keeps the last one) and sends one whole output
  frame in the layout section 4 settles.
- `set_brightness(level)`: stores the level; the pump puts it in every frame's packets.
- `close()`: drains (2.4), stops the pump, closes the socket.

Every caller reaches the driver through `make_display` (show/display/__init__.py:37-46): the show
(show/main.py:188), the arcade (arcade/main.py:141), the pattern tool (tools/wall_pattern.py:296), the soak
(tools/show_soak.py:147 through `ShowLoop`). So all four get the pump with no change of their own. `output_hz`
belongs next to `iface` as a display setting (default 60, matched to the card's refresh and multiple), not in the
loops' `fps`.

`arcade/flash.py` (FROZEN) needs NO change for the pump: the governor keeps running once per content frame, in the
caller's thread, with `fps` the content rate. The one place a change to the governor's inputs may be needed is
G12 (the gamma range), and that is in the config checks, not in flash.py.

### 2.2 The governor sees each content frame once; the wall shows only governed frames

Today's flow. Show: `GovernedDisplay._govern` (show/wall.py:106-112): `apply`, copy to `_last`, `_send`, count.
Arcade: arcade/runner.py:552-553: `governor.apply(limiter.apply(canvas))`, then `display.push`.

With the pump the flow above is unchanged. What the property rests on:

1. **The pump sends only what `push` was given.** Every `push` caller governs first (the show by construction,
   tests/test_wall_pattern_governed.py:50-60 pins it for the tool; the arcade at runner.py:552). Resending the same
   bytes changes no pixel's light, so it adds no transition. HOLDS.
2. **Whole frames only.** The pump must take its frame at the start of a burst and never look at the pending slot
   again until the burst is over. With the buffer of today it BREAKS (G15). With an immutable pending object
   swapped by one assignment (`self._pending = converted.tobytes()` is atomic under the GIL), or a sequence-locked
   double buffer across processes, it holds.
3. **A content frame may be skipped, never invented.** If two pushes fall inside one output period the pump shows
   only the second. The governor counted prev, A, B; the wall shows prev, B. A pixel's changes of direction in a
   subsequence are never more than in the whole sequence, so the wall makes at most the transitions the governor
   counted, in no less time. The same holds when the held pixels of B were copied from A (flash.py:200): B as the
   governor returned it is what goes out. HOLDS (by argument; worth a property test: drop random frames from a
   governed sequence and measure with `flash_area` and `square_flashes`).
4. **Display time is quantised.** A 30 fps frame shows for 1, 2 or 3 output periods depending on phase and
   jitter; a 20 fps frame for 2 to 4. The count of transitions is unchanged; the governor's second is counted in
   content frames (flash.py:121-122), which the pump does not touch. HOLDS.
5. **The driver must originate no content of its own.** Black at close and black at start are the two temptations.
   At close the driver should resend the LAST PUSHED frame (the caller's governed black), not make black itself:
   otherwise the arcade, which pushes no black (G7), would get an uncounted lit-to-black change. The dark start
   (S2) is the one exception, argued there.
6. **`unsent` loses its meaning.** `GovernedDisplay._send` (show/wall.py:154-161) sets `unsent` around
   `display.push`. With a pump `push` returns before anything is on the wire, so `unsent` is False while the frame
   is still pending. It is harmless only if the driver's `close()` drains.

Where it BREAKS if done naively: item 2 (shared buffer), item 5 (driver-made black), and the close: two black
pushes and an immediate socket close send nothing (finding 3).

### 2.3 What a failed push means, and what the hold becomes

Today a raise from `push` means "a burst stopped part way; the wall may show a mix". The hold exists because the
repair of that mix is a change the governor did not count (decisions.md:497-503, Q66).

With a pump the socket work is in another thread or process; `push` cannot raise for it. Three things follow.

**(a) The error must be carried back.** The pump records the first error of a burst; the next `push` raises it and
does NOT take the frame. `GovernedDisplay` then behaves as today: `failed` counts, the hold starts, the counted
frame is the one whose `push` raised (show/wall.py:90-93). Without this, `failed`, the hold, the lights going dark
after 10 s (show/main.py:330-340) and the soak's `push_failures` (tools/show_soak.py:235, :256) are all dead code
on the real wall.

**(b) A failed burst should send no sync.** If any row of a burst fails, the pump ends the burst without the sync
packets. Whether that keeps the mix off the wall depends on a card property that is NOT CONFIRMED: that rows do
not show until a sync arrives. For: the driver's rows, with a sync the card did not accept, never showed
(hardware.md:207-208). Against: a stream that ended left "top bars" (hardware.md:222-223), a partly updated
picture, and the bottom rows show noise when the sync is close behind them (hardware.md:216): the card's latch is
not clean in every case. So the hold stays; rule (b) only makes tears rarer.

**(c) "Quiet" has to be defined for a stream.** Two readings of Q66's second of silence:

| Reading | During the hold | For | Against |
|---|---|---|---|
| Paused pump | The pump stops after the failed burst and starts again when `GovernedDisplay` hands it the counted frame. | It is Q66 as it was probed (evidence/it14): at least a second between the tear and any change. The card keeps the picture (G9). | Stop and start of the stream are unmeasured on this card; if either shows as a blink, each hold adds two. |
| Running pump | The pump keeps resending the last frame it sent WHOLE (sync included), and takes nothing new. | The steady 60 Hz stream is the only state measured steady (hardware.md:214). | If the failed burst left a mix on the wall, the next burst repairs it 16 ms later: the change "right behind the tear" that made Q65 read 7 against the budget of 6 (decisions.md:492-494). If the link is down the resends fail too, which is the paused pump by another name. |

Recommendation: the PAUSED pump, because it is the form the safety probes measured, PROVIDED experiment E1 shows
the wall steady through a stop and a start. The hold's two single sends (show/wall.py:83-87) then become, with no
change to `GovernedDisplay`: the first `repush` restarts the stream ON the counted frame, which now runs at 60 Hz
for the rest of the hold; the second `repush` hands over the same frame and changes nothing on the wire. That
repairs G9's weak half (one frame is not enough) without touching the hold's timing or its tests. `close()` in a
hold (show/wall.py:133-143) works the same way.

What the owner's Q66 check must now cover (it is wider than "the picture stays for 3 s"): the picture stays, it
stays STEADY, there is no blink at the stop, and none at the restart. E1 in section 4.

**Failures the hold never sees** (G11): silent loss. With a pump this gets one new tool: the card answers a
discovery packet (0x07) with its uptime and a packet count (`refs/fpp-ColorLight-5a-75.cpp:70-88`). Polling it
once a second would tell a dead link and a card that restarted (uptime went back) from a healthy one. Not needed
for the flicker fix; a candidate for a later safety slice.

**The arcade has no hold at all.** A raise from `push` is logged and the next tick pushes a new governed frame
(arcade/runner.py:551-557, pinned by tests/arcade/test_runner.py:840-848, :941): new content straight behind a
possible tear, which is looser than Q65's resend that Q66 replaced as unsafe. With (a) in place the arcade would
at least see the errors. Whether the arcade gets `GovernedDisplay` is the owner's call (section 5, item 3).

### 2.4 The close

`close()` of the driver, with a pump: keep resending the last pushed frame for N output frames, then stop after a
whole burst (never mid-burst), then close the socket. N from experiment E5; 60 (1 s) is the only value measured
to work (hardware.md:223). This costs up to 1 s on every stop; Q68 already allows 2 s.

Because the draining is inside the driver, every frame-count assertion in G6 stays as it is.

### 2.5 Python timing on a Pi 5

Load: 128x64 is 64 row packets of 405 bytes, plus 2 brightness (77) and 2 sync (112): 68 packets and 26.3 kB a
frame; at 60 Hz 4080 packets and 1.6 MB a second. The link does not care. The full wall (512x192, show/config.py:
18-19) would be 384 row packets a frame, 23 000 packets a second; that is a different budget and likely several
cards.

What is known about the tolerance: the test sender, Python on an idle x86 desktop with an Intel PCIe port, paced
by `time.sleep` from each frame's start (`cl_fpp_test.py:82, :92`, so slightly UNDER 60.0 fps), was judged steady
(hardware.md:214). So the card does not need exactly 60.000 Hz. How much jitter or drift it takes: NOT MEASURED.
Every option below is judged without that number; E4 gets it.

| Option | Jitter to expect | Cost | Verdict |
|---|---|---|---|
| A. Thread, `time.sleep` to an absolute deadline, one `send` per packet | Each `send` releases the GIL and must take it back. While the main thread runs Python or small numpy work the wait is up to the switch interval (5 ms by default), per packet, 68 times a frame. In practice: late by about as long as the main loop's busy stretch (the show's render and pyte feed; the arcade's tick), some frames a second (LIKELY; not measured). | Smallest change. No new files. | Good enough to LEARN with; not to be trusted before it is measured under the real load. |
| B. Thread, the whole frame in one `sendmmsg` through `ctypes` | One GIL hand-back a frame, not 68. The wake itself still waits for the GIL, up to 5 ms; `sys.setswitchinterval(0.001)` trades that for main-loop speed. | `ctypes` structures for `mmsghdr`; Linux only (the fake socket path stays for tests). | Better than A; same kind of risk. |
| C. Busy-wait in a thread (`perf_counter` spin) | The spinning thread HOLDS the GIL; the main loop gets it only at forced switches. | Starves the show or the arcade. | NO. Spinning belongs in its own process. |
| D. `SCHED_FIFO` on the pump thread | Removes kernel scheduling delay, not the GIL wait (the holder is an ordinary thread; the kernel cannot lend it priority through a Python lock). | `CAP_SYS_NICE` or `LimitRTPRIO` in the unit. tests/test_deploy.py:37 pins `AmbientCapabilities == "CAP_NET_RAW"` exactly; `deploy/` is the owner's. | Useful only together with E or F. |
| E. A separate Python process, the frame in shared memory | Its own GIL: jitter is the kernel's, tens to a few hundred microseconds on an idle core; with `SCHED_FIFO`, a pinned core and a short spin before the deadline, under 100 us is realistic on a Pi 5 (LIKELY; to be measured). Garbage collection in the pump can be switched off (it allocates nothing per frame if written so). | A second process to start, watch and stop: a heartbeat both ways (the pump stops if the parent dies; `push` raises if the pump died, which feeds 2.3a). A sequence-locked frame slot. The systemd watchdog still sees only the main process (`NotifyAccess=main`, deploy/show.service:10). | The RECOMMENDED target if A or B measures too rough. |
| F. A small C helper (about 150 lines: `clock_nanosleep(TIMER_ABSTIME)`, `sendmmsg`) | The best: bounded by the kernel. | A build step on the Pi (`build-essential` is already in deploy/README.md:6); a second language inside the flash-safety review; a test seam (let it write to a Unix datagram socket or a capture file in tests). | The fallback if E is not steady enough. Same process model as E, so E's supervision code carries over. |
| G. Kernel pacing: `SO_TXTIME` and the `etf` qdisc | The kernel releases each packet at its stamped time; the sender only has to be early. Python's jitter stops mattering up to the lead time. | A qdisc set up as root at boot; one frame more latency; support on the Pi 5's port and on USB adapters not confirmed. | SPECULATIVE; listed for completeness. |

Two more points:

- **The network port.** The measured-steady sender used an Intel PCIe port. A USB adapter (deploy/README.md:73)
  batches packets; its effect on the row-to-sync timing (G5) is unknown. The Pi 5's own port should carry the
  card. To be checked on the real Pi, whichever option is built.
- **MediaPipe.** It runs in the camera's thread (arcade/sources/camera.py:281-299,
  arcade/sources/pose_mediapipe.py:119) and may use every core. That argues for E or F with a pinned core and a
  real-time priority on the arcade's Pi, more than on the show's.

Recommended path: build the pump's core so that it does not care where it runs (2.6), run it first as option A,
MEASURE the interval between sync packets on the Pi 5 under the real load (a histogram, as tools/show_soak.py
already keeps for the step), and move the same core to E only if the wall or the histogram says so.

### 2.6 Tests without the wall clock

The suite's habit is already right: loops take `clock` and `sleep` (arcade/runner.py:282-283, show/main.py:
119-120, show/wall.py:38-39, tools/wall_pattern.py:192-193). The pump follows it, in three layers:

1. **One output frame, no time at all.** `burst(sock, frame_bytes, level)`: a pure function of its arguments
   that sends one output frame. Tested with `FakeSocket` (tests/test_colorlight.py:15-27): the exact packet
   sequence, the counts, the BGR bytes of a red pixel, the level in every packet, and "a `send` that raises on
   packet k: no sync packet follows, the error is returned".
2. **The pacing, on a fake clock.** `run(next_frame, burst, clock, sleep, stop)`: tested with a clock that only
   `sleep` moves. Asserts: bursts start at k / 60 exactly; the deadline is absolute (no drift over 10 000 frames);
   after a stall of 100 ms one burst goes at once and the schedule restarts, with no catch-up run (as
   arcade/runner.py:611-627); the drain sends exactly N bursts of the last frame and ends after a whole burst.
3. **Interleaving, by hook, not by thread.** A fake socket whose `send` calls `display.push(other_frame)` when it
   sees row 20. Assert that all 64 rows of that burst are from one frame and that the next burst is the other
   frame, whole. This is the test that catches G15, and it is deterministic.
4. **The thread or process wrapper: liveness only.** Start, push, wait on a `threading.Event` that the fake socket
   sets at its third sync (timeout 5 s, a bound and not a measure), close, assert joined and the socket closed. No
   assertion on rates or intervals in the suite. Rates are measured by a tool on the target, not asserted in
   tests, which is what keeps them from failing under load.
5. **Error hand-back.** A fake socket that raises once: the next `push` raises that error and stores nothing; the
   pump is paused; a following `push` restarts it.
6. **Across processes (option E):** the sequence-locked slot is tested in one process by stopping a writer half
   way (a hook between its two counter writes) and asserting that the reader retries and never returns a mix.

The `GovernedDisplay` tests need a third display model beside `TornDisplay`'s two (tests/test_wall_hold.py:17-39):
"rows then sync, a torn burst sends no sync, the stream pauses". The sweep at tests/test_wall_hold.py:96-117 and
tests/test_wall_close_hold.py:55-67 should be run against it before the pump is trusted; that is a safety slice
with a plan review, like it14's.

---

## 3. The alternative: retune the card for 30 fps

The idea: the card is steady when its input rate matches what its refresh setting expects (960 Hz x16 is 60 x 16,
hardware.md:214-215). Choose a refresh rate and multiple whose quotient is 30 (for example 480 Hz x16), or
Refresh x1, and feed 30 fps.

**Evidence for** (all from hardware.md):
- :214-215: 60 fps steady at 960 x16, 20 and 30 not. One card timing, three rates. The reading "the card repeats
  each frame 16 times and waits for the next" is the session's INFERENCE, not a measurement (SPECULATIVE until a
  second timing is tried).
- :131-132: no flicker seen during the wizard runs at 420 Hz, x1, 17.9 MHz. But the wizard shows static test
  pictures, sent by LEDVision at an unknown rate.

**Evidence against:**
- :150-158: at 420 Hz x1 with a real picture from LEDVision the owner still saw it "shift and fidget"; DCLK 15.6
  to 10.4 MHz: "Same"; Brightness Level 1 to 3: "Same".
- :159-164: the 8 % dips about every 6 camera frames. The log does not name the card timing of that video; by the
  log's order it follows the state of 14:35, which was 360 Hz, x1 (:157). If so, x1 does not by itself make an
  irregular stream steady (LIKELY; LEDVision's rate and jitter from the VM are the unknowns in it).
- The Linux sender has been run against ONE card timing. There is no measurement of it at any other.
- `refs/fpp-issue-1849.txt:14, :214`: others report flicker and lag from LEDVision itself on 13.x. The card's
  firmware, not only its timing, is in question (another lane's subject).

**What a retune leaves unsolved, even if it works:**
1. The show runs at 20 fps. One card setting cannot match 20 and 30. (The show could be set to `fps = 30` in
   show.toml: the governor takes it, show/config.py:81; the cost is the render and pyte on a Pi 4.)
2. Irregular frame times. If the card waits for each sync, a frame that is 5 ms late is 5 ms of wrong light. Both
   loops restart their schedule after a late step (show/main.py:385-391, arcade/runner.py:622-627), the hold sends
   nothing for seconds (G9), setup retries and failed renders skip pushes (G4). A retune moves the sensitive rate;
   it does not remove the sensitivity.
3. The ending (G6), the layout (G1), BGR (G3), the bottom rows (G5): all remain.
4. A lower refresh rate is more visible to cameras (the piece will be filmed).
5. Every change of DCLK or multiple in LEDVision silently sets Brightness Level to 8, 81 % (hardware.md:155-156):
   each retune is a chance to run the wall at a level the supplies were not sized for, and ends with another Save
   to the card's flash. The saved, power-cycled, working setup (hardware.md:183-197) would be replaced.

**Verdict.** Not instead of the pump. As an EXPERIMENT it is worth one LEDVision session (E6), because its result
tells what the card is actually sensitive to, and a timing that is tolerant of 30 fps would widen the pump's
margin. The pump's rate should be a setting so that it can follow whatever timing the card ends up with.

---

## 4. Proposed order of work

The owner runs every hardware check on the Omarchy box (`enp5s0`, sudo). All checks at brightness 0.1. Until S3
lands, anything on the wall should run at 60 fps only (finding 2).

### First: experiments that need NO new code (the existing `cl_fpp_test.py`)

| | Command (after `sudo .venv/bin/python cl_fpp_test.py --iface enp5s0`) | Answers |
|---|---|---|
| E1 | `--fps 60 --seconds 10 --tail-seconds 0`, then watch 5 s; run it 3 times in a row | Q66's check with the Linux sender: the bars stay, steady; is there a blink at the stop, and at the next start? (2.3c) |
| E2 | at `--fps 60`: (a) `--no-dup`; (b) `--no-dup --sync-reps 2`; (c) `--sync-reps 1` | Which doubling the card needs: both single; sync doubled only; brightness doubled only. Settles G1 and G2. |
| E3 | `--fps 60 --gap-ms 12 --spin`, and the same without `--spin` | LEDVision's and Falcon Player's layout (the sync one idle period after the rows): is the bottom noise gone, and is it steady? Settles G5. |
| E4 | `--fps 50`, `55`, `58`, `59`, `61`, `62`, `65`, `120` | How exact the rate must be, and whether 120 (two bursts per card frame) is also steady. Gives the pump its tolerance. |
| E5 | `--fps 60 --tail-seconds 0.05`, `0.1`, `0.25`, `0.5`, three runs each | The fewest black frames that land black. Gives the drain its N. |
| E6 | One LEDVision session: a timing whose refresh / multiple is 30 (and x1); after each Send, check the level, then `--fps 30` and `--fps 60` from Linux. Do NOT save to the card. | Section 3. |

### Then: code, in small steps

| Step | Change | Certain? | Hardware check |
|---|---|---|---|
| S1 | The driver's output frame as one function: brightness, rows, sync, with the counts and the row-to-sync delay as named constants; the layout of `cl_fpp_test.py` until E2 and E3 say otherwise. BGR on the wire, as a named pixel order. `push` still sends at once (no pump yet). Docstring rewritten (G8). Tests: G1, G2, G3. | Layout: CONFIRMED to work as a whole. BGR: CONFIRMED. | `wall_pattern.py rgb --fps 60 --seconds 10`: bands red, green, blue, white from the left, letters readable. Some flicker is expected (G14). |
| S2 | `close()` drains (2.4); the pattern tool paces by deadline (G14). A dark start: on open, 1 s of black at the output rate before the first content frame, so that `from_dark` is true (G10). The dark start is content the driver makes itself; the case for allowing it: the wall's state at start is unknown to every governor, the change to black is one change, and a second of black follows it. It needs the owner's word as a safety decision. | Drain: CONFIRMED need; N from E5. | Ctrl-C on the pattern tool: the wall is black within 1 s, three times of three. Start the tool while an old picture is up: it goes black, then the pattern. |
| S3 | The pump, option A, with the core of 2.6; `push` copies and returns; `output_hz` setting. Tests: 2.6 layers 1 to 4. A tool on the target prints the histogram of sync-to-sync intervals. | NEEDS E4 for its tolerance. | `wall_pattern.py rgb --fps 20` and `--fps 30`: steady, by eye and by a phone's slow-motion video. Then the owed checks: `index`, `steps --brightness 0.4`, `gamma` (hardware.md:311-313). |
| S4 | Errors carried back, no sync after a failed row, the paused pump (2.3). The third display model and the sweeps against it. A safety slice with a plan review. | NEEDS E1. | Pull the cable for 5 s during `wall_pattern.py grid`: write down whether `send` raises at all (G11), what the wall shows, and what it does when the cable returns. |
| S5 | The same on the Pi 5, on its own port, with the real load: `python -m show --config show.poc.toml` and `python -m arcade run`. If the histogram or the wall is rough: the same core as option E (a process), then F. | NEEDS a measurement. | 10 minutes of each, filmed in slow motion; the histogram's worst interval. |
| S6 | The arcade's end and failures (section 5, items 2 and 3); the governor's gamma after the `gamma` pattern (G12); reopening the socket (G11). | Owner's decisions. | As each says. |

S1 and S2 are small and certain. S3 is where the flicker goes away. S4 is where the safety design is made whole
again; the show should not face people before it.

---

## 5. Anything else

1. **The governor's colour rule runs on swapped colours until BGR is fixed** (G3). Any earlier safety measurement
   that depended on saturated red (arcade/flash.py:39-40) was right for the frames and wrong for the wall.
2. **The arcade leaves its last frame on the wall** (G7) and **never counts the wall's first frame against what is
   shown** (C52's arcade half, roadmap.md:84, Q67). With a card that keeps its picture, both matter more than they
   did on paper. The arcade pushing governed black before `display.close()` is a change in arcade/main.py or the
   runner, with tests/arcade/test_main.py:65 beside it.
3. **The arcade does not use `GovernedDisplay`.** It has the governor (arcade/runner.py:296, :552) but not the
   hold, the counted frame, the dark start or the governed close. tests/test_wall_hold.py:178-181 asserts that
   only `show/main.py` and `tools/wall_pattern.py` build one. Moving the arcade onto it touches the runner's
   `governor` attribute, which tests reach for (tests/arcade/test_runner.py:630-644) and `state()` reports
   (arcade/runner.py:639). The owner's decision.
4. **No reopen after a lost interface** (G11). With `Restart=always` the cheapest repair is to let the show exit
   after N seconds of failed sends, so that systemd starts it again with a new socket; the dark start (S2) makes
   that restart safe.
5. **`set_brightness` sends a single 0x0A packet** (colorlight.py:116-119). If the card needs it doubled (E2c), the
   level set at open may not take; the sync packet carries the level too (:84-86), which probably covers it
   (LIKELY).
6. **`mediapipe` is only in the `mac` extra** (pyproject.toml:12-13); the `pi` extra has no pose library. The
   arcade on a Pi 5 has no declared way to get one. Nothing to do with flicker.
7. **The session log and the brief describe the same fault differently.** hardware.md:209-210 says the difference
   is "FPP's firmware-13 handling: per frame brightness packet (x2), the rows, then the sync". The capture and
   Falcon Player's loop say the ORDER is not the difference (finding 1). The log should get a line once E2 and E3
   are run, so that the next reader does not build on the order alone.
8. **The test of 15:40 made the wall flash hard** (hardware.md:207-208). Any later run of unproven sender code
   should start at the lowest brightness, with nobody sensitive in front of the wall, and for a second or two.
9. **The full wall.** At 512x192 the per-packet Python send is about 6 ms a frame on a Pi (LIKELY), a third of a
   60 Hz period; the pump's options B, E and F scale, A does not.
