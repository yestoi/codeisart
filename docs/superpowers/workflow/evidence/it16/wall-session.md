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
