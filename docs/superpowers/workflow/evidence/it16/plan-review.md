# it16 plan review: the five entries (one adversarial round)

Plan: `docs/superpowers/plans/2026-10-01-it16-five-entries.md` at 2b8ee74 (303 lines). Reviewer: a fresh-context agent, 2026-10-01 00:17 to 00:45 CDT.
Line numbers below are the plan's at 2b8ee74. Probes and their outputs are in `/private/tmp/it16-plan-review/` (named in each finding and listed at the end). The sources are the operator's fetch at cb48eb9 (the session scratchpad's `ioccc/`), read only.

Verdict: **BLOCKED**, on six findings. Four are mine and two (B5, B6) are the operator's or Q83's. Most of the plan holds: every code citation but one, every sha256, the authors, the five builds and their warning kinds on the Mac, the widths and ASCII of all five runs, the suite's time, and the lanes' independence.

## Blocking findings

### B1. endoh1's run line feeds a leaky container: the wall shows two bars, not fluid (plan :211, :216)
- The plan: `run = "./prog < endoh1.alt.c"`, justified as "the archive's way (`try.alt.sh:65`)".
- What happens: endoh1.alt.c is not a closed vessel; source lines 4 to 29 have no right wall, so the fluid runs out of the field within about 2 s. Here are the frames in the repo's own Terminal (80x23, real time, the plan's build):
  - From about 3 s to 39 s the screen holds **40 lit cells**: two `||` bars at the left, on 20 rows (`probe_pty_endoh1.out`).
  - From a pipe, frame 0 has about 1000 lit cells and frame 34 (about 2 s) has 52.
  - The same binary fed `endoh1.c` holds **1008 to 1138 lit cells** through 36 s, widest column 78, ASCII only (`probe_pty_endoh1_orig_input.out`).
- `try.alt.sh:65` runs `./endoh1_color.alt < endoh1_color.alt.c`, which is the colour variant with its own source. It is not this file.
- The archive's README says: "Use `endoh1.alt` … as you would `endoh1`"; the author's synopsis is `./endoh1 < endoh1.c` (README.md:181).
- Why it blocks: for 34 of its 36 s the entry shows a near-empty screen on the wall. The plan's acceptance test passes it anyway: final lit 40 is over FINAL_LIT_MIN 10 (see B3).
- Smallest fix: `run = "./prog < endoh1.c"`. endoh1.c is already in the directory and is the unmodified published file. Keep the build, -DA=40 and run_seconds 36. The emulated curated play then gives a witness peak of 1424 and a final of 1245 (`probe_curated_endoh1_fixed.out`).

### B2. T-rows hides the line being typed under the strip during SOURCE (plan :69-71)
- The plan claims: "No other change: `start` (:103) … already reset the terminal to `self.rows` … so a 24-row pty under a shown strip loses only row 24, where the cursor parks."
- What happens: `start` resets the terminal to 24 rows before SOURCE (`show/pipeline.py:103`). Once the typed source fills the screen, the line being typed sits on row 24. At 128x64 that row is under the strip, and the renderer draws only `min(23, 24)` rows (`show/renderer.py:73-80`).
- At the show's 20 fps, the player was ticked through SOURCE at 24 rows and at today's 23 rows, and both frames were rendered with show.poc.toml's renderer (`probe_rows_source.out`):
  - sloane: in **28 of 85** SOURCE ticks the line being typed is on row 24 with text on it, and 35 of the 85 frames differ from today's.
  - endoh3: 14 of 83 such ticks, and 15 frames that differ.
- The viewer sees the source scroll up while the letters arrive out of sight. The same applies to BUILD's last line.
- Why it blocks: the claim the task rests on is false for SOURCE and BUILD, and following it puts a wrong picture on the wall for both 24-row entries.
- Smallest fix:
  - `start` and SOURCE/BUILD keep today's rows (`cfg.rows - 1`, or `cfg.rows` when full_screen).
  - `_start_run` grows the screen to `self.rows` (`self.term.rows = self.rows; self.term.screen.resize(self.rows, self.term.columns)`) before the CastWriter at :171 and before `term.run`, which sets TIOCSWINSZ from `term.rows` (`show/terminal.py:72`). The fallback's reset at :202 stays at `self.rows`.
  - pyte's resize from 23 to 24 keeps the content and the cursor (checked).
  - Add a test: a `rows = 24` entry has `term.rows == 23` in SOURCE and BUILD and 24 from RUN.
  - `_fail`'s `\n*** … ***\n` stays visible at 24 rows (it ends on a fresh line), so ERROR_HOLD needs nothing.

### B3. T-curated counts lit cells on the leftover source screen, so a run that prints nothing passes (plan :105-108)
- The plan: PEAK and FINAL are counted on `player.term.screen.display[:cfg.rows - 1]`, with PEAK_LIT_MIN 100 and FINAL_LIT_MIN 10, plus "the phases are SOURCE, BUILD, RUN, DWELL, DONE" and `failure is None`.
- What happens: at RUN's start that screen still holds the typed source and the build line. A run that exits at once with any status is a normal end (`show/pipeline.py:181-187` fails only on a signal), so it goes RUN → DWELL with `failure is None`.
- Three broken copies passed every check of the test as planned (`probe_curated_broken.out`):

  | Copy | Run line | peak / final as planned |
  |---|---|---|
  | imc | `sh nosuch.sh` | 547 / 541 |
  | endoh1 | `exit 1` | 986 / 993 |
  | sloane | `./prog_missing` | 716 / 879 |

- This is exactly the failure the Pi check (a) exists to catch. On the Pi it runs on a `git archive` tree, so if O1's `.gitignore` lines were wrong, `tour.sh` or `clock.sh` would be missing and the entry would still pass.
- The test also passes B1's endoh1 (final 40) and the Pi's REP-damaged plasma (B5: 1232 lit).
- Why it blocks: a named acceptance test passes a wrong implementation on the point that matters, namely that the entry's program runs and draws.
- Smallest fix:
  1. Attach the witness when RUN begins: a fresh pyte Screen at `player.rows`, after `_start_run` fed `$ <run>`.
  2. Count PEAK and FINAL on the witness, with FINAL_LIT_MIN 100.
  3. For each CURATED slug (not hello, which exits by itself), assert that RUN ended at the pipeline's cut: the fake time from RUN to DWELL is at least `player.run_timeout()`.
- Measured on the witness:
  - Good entries' finals: hello 138, endoh3 804, endoh1 (fixed) 1245, thadgavin 1614, imc 1716, sloane 1790 (`probe_curated_witness.out`). All five curated were cut by run_seconds in fake time (RUN to DWELL 36 to 40 fake s).
  - Broken runs: witness peak 0 and RUN lasted 0.2 fake s.
  - Assert (3) does not depend on the length of the shell's error message. Bash on the Mac printed the temp path and lit 265 cells for `./prog_missing`.

### B4. The T-shot test asserts a title that the 128x64 strip never shows (plan :125-127)
- The plan: `test_governed_entry_session_runs_the_entry_through_the_governor` asserts, "at show.poc.toml, … a strip text names the entry's title".
- What happens: at 128x64 the strip holds `strip_chars(cfg)` = 128 // 6 = 21 characters. That is under SHORT_BELOW 40, so `strip()` gives the short form ("<author>, <year>" alternating with "Not A.I.", plus notices) and never the title.
- A session at show.poc.toml with a `write_entry` HELLO_C entry pressed at 1 s showed only these strip texts: `{'PRESS A BUTTON': 4, 'PLAYING': 9, 'Test Author, 2026': 3, 'Not A.I.': 8}`. No strip named the title (`probe_tshot_strip.out`).
- Why it blocks: a named test cannot pass on a right implementation.
- Smallest fix: assert that a strip text is `"<author>, <year>"` of the written entry ("Test Author, 2026"). A strip of "PLAYING" alone would not prove the entry played.

### B5. thadgavin's `TERM=xterm` draws with REP on the Pi, which pyte drops (plan :194). This is the operator's finding, carried here.
- `evidence/it16/pi-probe-early.md` (1470646), after the plan was written: the Pi's ncurses 6.5 under TERM=xterm sends `CSI n b`. **22 of 23 rows are wrong** (1232 lit against 1676). TERM=vt100, xterm-r6 and linux are clean.
- Confirmed here: `'b' in pyte.Stream.csi` is False, and `#\x1b[5b` leaves a single `#` on a pyte screen. The Mac's xterm and vt100 terminfo have no `rep`, so no Mac test or sheet can see this.
- Why it blocks: a wrong picture on the wall, and B3's test as planned passes it.
- Fix (the operator's): `run = "TERM=vt100 ./prog"`, and the curated test refuses a REP escape in a run's bytes. Add it to B3's witness listener: refuse `ESC [ <digits> b` in the RUN bytes.

### B6. Pi check (a) leaves pytest's temp tree on the Pi (plan :268-271; Q83 (2))
- The plan: "every call … keeps nothing on the Pi between calls". Check (a) runs pytest on the untarred tree with `-p no:cacheprovider` but no `--basetemp`.
- What happens: pytest's tmp_path root defaults to `/tmp/pytest-of-<user>/pytest-<n>`, outside the call's scratch directory, and pytest keeps the last three. Each play copies an entry there and builds `prog` (and endoh3's `clock`).
- Why it blocks: it breaches Q83 (2) as decisions.md records it: "Nothing is kept on the Pi between two ssh calls".
- Smallest fix: `--basetemp=<scratch>/pt` inside the directory the call removes. The operator's literal `/tmp/it16-operator` (the guard refuses `$` and short /tmp paths) gives `--basetemp=/tmp/it16-operator/pt`.

## Noted, not blocking
- O1's check (:53): `git check-ignore -v` prints all four paths, because -v also reports the `!` matches. Without -v it prints only `entries/endoh3/clock.c` and `entries/x/prog`. The rules themselves are right (scratch repo `gi/`):
  - tour.sh, clock.sh and LICENSE.md are not ignored.
  - clock.c, clock, prog and fallback.cast.part are ignored.
  - entries/README.md is not ignored.
- The Risks line (:301) cites `show/pipeline.py:27` for "RLIMIT_AS 256 MB". :27 is BUILD_MEMORY 512 MB; the run's 256 MB is :28.
- The same line says "the Pi step proves" endoh3's in-run gcc under the limits. Neither check (a) nor (b) exercises it:
  - Under the fake clock a play ends in about 3.5 real s, before clock.sh's `sleep 5`.
  - Check (b) builds without limits.
  - pi-probe-early.md already shows the compile passing under `ulimit -v 262144` and `unshare -rn`. That is enough evidence, but the plan's sentence is wrong.
- Check (b)'s script is quoted inside `sh -c "<script>"`. Taken literally, the inner `sh -c "$b"` closes the outer quote, and `$b`, `$$` and `$?` are expanded by the remote login shell. So `$b` is empty and every build would report "0 warnings, exit 0".
  - Check (a) still builds every entry under gcc 14, so this is a false warning count, not a false pass on the build.
  - "The build's exit status printed beside it" cannot come from `… | grep -c` under dash. Use `sh -c "$b" >log 2>&1; echo $?; grep -c warning: log`.
- Fallback replays compress gaps over 2 s (CastPlayer). imc's 6 s views and endoh3's 5 s generations replay at 2 s each. That is acceptable, but the sheets will not show it.
- Cast sizes are all under 5 MB: thadgavin about 0.7 MB, endoh1 about 1.5 MB, sloane under 1 MB, endoh3 about 0.02 MB. Each `--play --capture` takes about 55 s.
- A broken run line is recorded as a kept cast: `_stop_capture(keep=sig is None)` keeps an exit-127 capture. Step 2's "exists and its size" would commit a junk fallback. B3's fixed test, run before step 2, is the guard.
- The governed sheet's held/area/squares cover SOURCE typing and attract as well as the RUN, so they are not the program's numbers alone.
- Attract's header line for thadgavin (`---- Plasma -- Created by Gavin Buttimore and Thaddaeus Frogley, 2000, Not A.I. ----`) is 84 characters and wraps.
- The plan's "79-character strip" remark applies only at 512 wide, not at 128x64.
- Cutting endoh3 during its in-run compile can leave `cc*` files in /tmp (PrivateTmp under the unit) or a truncated `clock`. The next play rewrites both.
- imc's view 4 (`-centre 1 2`) lights only 10 rows and 249 cells. Views 5 and 6 light 469 and 471 (the plan's Q-b).
- gcc 14: clang 17 already turns implicit declarations and int-conversion into errors, and the plan's lines pass it. pi-probe-early.md shows four builds clean under gcc 14 and thadgavin clean after libncurses-dev. No residual risk is seen.
- endoh3 is built from prog.c, not prog.alt.c, against the roadmap's "the .alt.c, the one the wall builds". The plan raises this as Q-a, so it is not a finding.
- The tests that read the real `entries/` touch only hello. No existing test reads attract or autoplay from it, so Q56's stations 1 to 5 leaving hello out of autoplay changes no existing assert.

## Verified as the plan states
- Code citations hold: `show/pipeline.py:84-86, :103, :171, :181-187, :202`; `show/renderer.py:73-80, :91`; `show/terminal.py:37-39`; `show/sandbox.py:32-33, :56-59`; `show/entries.py:18-33, :74`; `show/config.py:23-24`; `tools/show_shot.py:236-250, :320-326, :329-390, :539`; `tests/test_entries.py:94-105`; `tests/test_pipeline.py:433`; `tests/test_show_shot.py:153`.
- Every sha256 the plan gives matches SHA256SUMS. The authors, years and awards match `.entry.json`.
- The five builds pass on the Mac with the plan's exact lines (`build.out`). Warnings: sloane 8, imc 2, thadgavin 2 (one `-Wdeprecated-non-prototype`), endoh1 0, endoh3 0.
- Runs in the repo's Terminal (real time):
  - sloane at 24 rows uses 23 rows with the cursor parked on 24, and does not scroll.
  - imc's tour: six views at 6 s each; it exits 0 at 36.6 s.
  - thadgavin on the Mac: about 1600 lit cells.
  - endoh3 regenerates every 5.4 s.
  - Every width is at most 80 (at most 79 for all but thadgavin), and everything is ASCII.
- The curated emulation (`probe_curated.py`, the plan's constants):
  - Each play takes 3.3 to 4 real s.
  - Builds stay well inside the fake build timeout.
  - No witness cell is at x >= 80.
- Suite time: T-curated about 20 s (six plays), T-rows about 5 s, T-shot about 5 s. That gives about 350 s against the 420 s limit.
- The lanes share no files, and the merge order works. Nothing under deploy/ is touched. The unit's `ReadWritePaths=/home/pi/codeisart/entries` and `PrivateTmp` allow endoh3's in-run cc.

## Probes (all under /private/tmp/it16-plan-review/)
- `build.sh` → `build.out`, `build/<name>.build.log`: the five builds with the plan's lines.
- `entries/`: the plan's five entry directories (entry.toml, tour.sh, clock.sh) plus a copy of hello. `entries_broken/` holds three broken copies, `entries_fixed/endoh1` holds the endoh1.c input.
- `probe_curated.py` → `probe_curated.out`, `probe_curated_witness.out`, `probe_curated_broken.out`, `probe_curated_endoh1_fixed.out`, `probe_curated_endoh1_v.out`: emulates `test_entry_plays_through` with T-rows as planned.
- `probe_pty.py` → `probe_pty_{sloane,imc,thadgavin,endoh3,endoh1,endoh1_orig_input}.out`, with raw bytes in `endoh1.raw`, `thadgavin.raw` and `endoh3.raw`: real-time runs in the repo's Terminal, wrap and run_command.
- `probe_endoh1_frames.py`: lit cells per frame from a pipe.
- `probe_rows_source.py` → `probe_rows_source.out`: SOURCE at 24 rows against 23, rendered at show.poc.toml.
- `probe_tshot_strip.py` → `probe_tshot_strip.out`: the strip texts of a session at show.poc.toml.
- `gi/`: a scratch git repository for the O1 check-ignore check.
