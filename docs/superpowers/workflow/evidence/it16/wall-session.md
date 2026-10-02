# The wall session for D5: the five entries on the 128x64 wall (the owner's, GATE C)

Made ready by the operator (Q84). Nothing here was run on the card by the loop: the loop never runs `python -m show`
with a wall backend, never pushes, and touches nothing under `deploy/`. About 20 minutes at the wall.
The form is the wall-session protocol's: each run is announced, starts on your "go" with a lead-in, and asks one or
two words back.

## Before the session (5 minutes, no wall needed)
1. Push main (the loop does not push): `git -C /Users/trey/dev/codeisart push`.
2. On the Pi, pull: `ssh trey@codeisart.local 'flock -w 300 /tmp/pi5.lock git -C /home/trey/codeisart pull --ff-only'`.
3. Promptviz off the Pi for the session (the runbook's rule: nothing reconfigures or loads the Pi while the wall
   runs), or the session's runs take the lock like everything else while `pi-lock.md` stands.
4. `libncurses-dev` is on the Pi (done 2026-10-01): the plasma builds there.

## What has never been done, so it is step one
The show daemon has never put a picture on this wall: every wall run so far was `tools/wall_pattern.py`, the arcade
or the bench tools (the show's soak tool builds at 512x192 and left the wall dark on 2026-09-30). `show.poc.toml`
(128x64, the ink view) is the config that fits the wall in hand; it has only been seen on sheets.

- **Run 0, no card (a dry play on the Pi):**
  `.venv/bin/python -m show --config show.poc.toml --backend fake --play hello` in `~/codeisart`.
  It proves the show starts on the Pi at 128x64, builds with gcc 14 and plays under `unshare -rn`. It opens the
  Pi's GPIO for the lights and buttons (that is why the loop did not run it). Expect exit 0 in about 20 s and no
  `ERROR` line but the ones for missing lights, buttons or sound.
- **How the show reaches the card (your call, Q90):** the wall tools so far ran as `sudo .venv/bin/python ...`.
  The show builds and runs the entries, so under `sudo` the five programs would run as root. The service unit
  (`deploy/show.service`) runs as a plain user with two capabilities instead; the same by hand, for one play:
  `sudo systemd-run --pty --collect --uid=trey -p AmbientCapabilities='CAP_NET_RAW CAP_SYS_NICE' -p WorkingDirectory=/home/trey/codeisart /home/trey/codeisart/.venv/bin/python -m show --config show.poc.toml --backend colorlight --play hello`
  This form has not been run by anyone yet (the sender's real-time child under a unit as user trey was proven in a
  dry run on 2026-09-30). The default: this form, not `sudo python`.
- **Run 1, hello on the card** (the form above, `--play hello`, about 20 s): the first picture of the show on the
  wall. Look for: the typed source as dots, the strip on the bottom row (`Trey, 2026` and `Not A.I.` in turn), a
  steady picture, the wall black at the end. Words back: "steady" or "flicker", "strip yes/no".

## The five entries (about 55 s each: the source typed, the build with its warnings, the run, the dwell)
Same form, `--play <name>`. Brightness is the config's (`show.toml`'s level 0.15 is not in `show.poc.toml`: the
default 0.15, cap 0.40). One at a time; the wall goes black between plays.

| Run | `--play` | What to look for | Words back |
|---|---|---|---|
| 2 | `sloane` | The donut turning over a checkered floor, a banner scrolling along the top row (its 24th row sits under the strip by design: nothing of the picture is lost). On the sheet the floor and the donut's hole read, and the donut's body hardly stands out: in the ink view it is as bright as the floor (Q93). Does the turning carry it at the wall? The sheet read held 0. | "donut" or "only floor"; "smooth" or "jumpy" |
| 3 | `imc` | Six views, six seconds each, a clear between them. On the sheet: view 1 a field of shades, view 2 the clearest, view 3 one lit block with nothing to read (the program's own output, Q92), view 4 a patch in a dark field, views 5 and 6 alike (Q86). | "six" or "four" (drop views 3 and 6, nine seconds each); "reads" or "mush" |
| 4 | `thadgavin` | The plasma. The governor holds a large part of it (400 held ticks on the sheet, 350 of them between 16 s and 42 s, about two ticks of three there; blocky patches for a moment at a time): is it still a plasma, is the light comfortable? The strip (C54, fixed in iteration 17, 86f0607): `Gavin Buttimore and`, `Thaddaeus Frogley,`, `2000`, `Not A.I.` in turn, three seconds each. Does the bare `2000` read as the year of the two names (Q96)? | "plasma" or "broken"; "comfortable" or "too much"; "year reads" or "year lost" |
| 5 | `endoh1` | The word "Fluid" melts and sloshes in a tank for 36 s. Its frame is 26 lines in a 23-row terminal: the top rows of its field are never seen, and a tear may show. | "reads" or "torn" |
| 6 | `endoh3` | The mirror clock: a clock face that redraws every 5 s from a program compiled from its own output. Sparse (about 800 lit cells of 1840). The time shown is the Pi's clock. | "clock yes/no"; "ticks yes/no" |

After the five: run 7, the show itself without `--play` for two minutes (the same form without `--play ...`; Ctrl-C
ends it, the wall goes black): attract (`PRESS A BUTTON` / `ON ANY PORTRAIT`), and with no buttons wired the idle
autoplay picks an entry after `attract_autoplay_minutes`. Words back: "attract yes/no".

## What the session decides (GATE C's entries part)
- Each entry: keep, change (say what), or replace (the research report's next picks).
- The plasma's speed and light under the governor (Q87: built at `-DZ=30`).
- endoh1's cut field (26 lines in 23 rows): acceptable, or the entry needs another form.
- The Pi's own fallback recordings (`--capture` at the wall, once the five are kept): the casts in the repository
  were recorded on the Mac and show clang's warnings, not gcc's.
- Q85 to Q88, defaulted by the loop (decisions.md): endoh3's `prog.c`, imc's six views, the plasma at Z=30, no
  cast over 5 MB. Q92 (imc's third view, a lit block: kept) and Q93 (the donut against its floor: kept) come
  from the final sheets (README.md beside this file has the table).

## If something is wrong
- A dark wall: read the play's log first (the form above prints it to the terminal); `./wall_triage state` on the
  Pi; the runbook `docs/runbooks/wall-shimmer.md`.
- Nothing goes to the card without your word; a run is never started while another is on the wall.

## Results: the session of 2026-10-01, 08:58 to 09:10 CDT (the owner at the wall, a session on the Mac driving the Pi)

Before it: main pushed and the Pi pulled to fd4a09c; promptviz's run paused by the owner; the Pi's load 0.00,
48 C, never throttled, up 10.5 h; nothing held the card; the driver at the wall-proven set. Every run went under
the lock, on the owner's "go", after a dark lead of 5 or 10 s, at the config's level 0.15. The form was Q90's
default with `--pipe --wait --quiet` in place of `--pty` (the ssh call has no terminal):
`sudo systemd-run --pipe --wait --collect --quiet --uid=trey -p AmbientCapabilities='CAP_NET_RAW CAP_SYS_NICE' -p WorkingDirectory=/home/trey/codeisart /home/trey/codeisart/.venv/bin/python -m show --config show.poc.toml --backend colorlight --play <name>`.
Every play logged `audio unavailable, cues are muted` (no sound device; expected) and no other error.

| Run | Play | On the wall | Exit | The sender's line | The owner's words |
|---|---|---|---|---|---|
| 0 | `hello`, `--backend fake` (no card) | 12 s | not captured; the log shows the play and the close | none (no card) | not on the wall |
| 1 | `hello` | 12 s | 0 | 754 frames, 0 late, worst sync 5 us, 0 rows off their slot, real-time yes | "Looked good." |
| 2 | `sloane` | 50 s | 0 | 3030 frames, 0 late, worst 11 us, 0 rows off | "Looks great." |
| 3 | `imc` | 46 s | 0 | 2813 frames, 0 late, worst 7 us, 0 rows off | "four views. It was a bit difficult to understand what was going on, but I blame the 2x2 limitations on resolution." |
| 4 | `thadgavin` | 53 s | 0 | 3216 frames, 0 late, worst 6 us, 0 rows off | "This looked cool." |
| 5 | `endoh1` | 47 s | 0 | 2873 frames, 0 late, worst 5 us, 0 rows off | "Ok, that was actually really cool. The source code looked exactly like the starting animation." |
| 6 | `endoh3` | 50 s | 0 | 3011 frames, 0 late, worst 5 us, 0 rows off | clock yes, ticks yes ("yes to both") |
| 7 | the show without `--play`, 120 s | 120 s | 124 (the stop, below) | none: the close did not run | "attract yes, wall is black" |

Every sender's line also read sync to sync sd 0 us, 0 slips, 0 send errors, 0 restarts.

What the session decided:
- All five entries are kept.
- Q90: the show reaches the card as user trey with two capabilities; the form ran seven times, real-time yes.
- Q93: the donut stays in the ink view. Q87: the plasma stays at the archive's speed under the governor.
- Q86, Q92: imc's tour becomes four views (views 3 and 6 dropped, nine seconds each). The owner found imc
  hard to read at this size and put it down to the 2 x 2 wall's resolution, not to the entry.
- endoh1's cut field (26 lines in 23 rows): no tear was named; kept.
- Not answered: Q96 (the bare `2000` on thadgavin's strip; the owner did not name it, it stays as built). The
  owner did not name the strip in run 1 either ("Looked good.").

Run 7's stop, a finding. The session ended the show with `timeout -s INT 120` inside the unit. GNU timeout
signals its child and then its own process group, so the show got SIGINT twice; the second came as `_close`
began (`show/main.py:402`) and the show left by a traceback: no "closing: the wall goes black" line, the lights'
close skipped, no sender's line, exit 124. The wall went black all the same (the owner: "wall is black"): the
sender's own drain when its parent dies (`CLOSE_HOLD_S`, black for a second) did it. This is the roadmap's note
"it13 (the next task in `show/main.py`...)" (1), a signal while `_close` runs, seen for the first time on the
card. One Ctrl-C at a terminal or `systemctl stop` sends one signal and does not meet it.

Later the same morning (09:50 to 09:52, the Pi at ffb65a3): the strip off (Q100) and imc's four views, on the
wall in the same form. `imc`: 46 s, exit 0, 2813 frames, 0 late, worst sync 8 us, 0 rows off. `sloane`: 50 s,
exit 0, 3017 frames, 0 late, worst 6 us, 0 rows off. The owner: "Ok, looks good." (he did not name the view
count or the bottom edge).

Q66's check followed at 09:56: "held, no blink" (evidence/hardware.md).

The same night (22:58 to 23:04, the Pi pulled to 56e585d, at the owner's event): the five again in the same
form, at the owner's word ("Lets run the codeisart IOCCC entries"; he chose all five and that the session stops
`promptviz-party.service` for it). The unit closed cleanly (its sender: 20879 frames, 0 late). The Pi: up 50
minutes, 59.8 C, never throttled, load 1.57.

| Play | On the wall | Exit | The sender's line |
|---|---|---|---|
| `sloane` | 50 s | 0 | 3043 frames, 0 late, worst sync 8 us, 0 rows off their slot |
| `imc` | 46 s | not captured (the session cut that log); the close ran | 2820 frames, 0 late, worst 5 us, 0 rows off |
| `thadgavin` | 53 s | 0 | 3222 frames, 0 late, worst 6 us, 5 rows off their slot, worst row 1362 us late |
| `endoh1` | 47 s | 0 | 2868 frames, 0 late, worst 5 us, 0 rows off |
| `endoh3` | 50 s | 0 | 3019 frames, 0 late, worst 12 us, 4 rows off their slot, worst row 948 us late |

A finding, not looked into: two of the five plays had rows off their slot (5 and 4, about 1 ms late; no late
sync, no slip), where the morning's plays all read 0. The Pi was warmer and busier than in the morning (59.8 C
and load 1.57 against 48 C and 0.00). The owner wrote "stop" as the fifth play ended and did not say what he
saw. This session did not start `promptviz-party.service` again; the unit was active again at 23:19.

Still open from this sheet: the Pi's own fallback recordings (imc's cast still holds six views).
