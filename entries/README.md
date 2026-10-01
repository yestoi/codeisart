# The entries

One directory a station. Each holds `entry.toml`, the published source byte for byte, a run script where
one is needed, `LICENSE.md` (credit, the archive's commit, the licence, the sums) and, once the operator
records it, `fallback.cast`. Everything else in a directory (the build's `prog`, endoh3's `clock` and
`clock.c`) is a build product and stays out of git (`.gitignore`). `tests/test_curated_entries.py` checks
every directory: it loads, keeps `-Wall`, carries its licence and sums, and plays through by a fake clock
with its program inside the wall's 80 columns, ASCII only.

The five curated entries come from the IOCCC archive, ioccc-src/winner at
`cb48eb9572c2735a6f12ec56790e014311674a96`, under CC BY-SA 4.0; `entry.toml` and the run scripts are this
installation's adaptation under the same licence. Warnings are counted under `LC_ALL=C`: the Mac's
Apple clang 17 at it16, the Pi 5's gcc 14.2 from the early probe (`docs/superpowers/workflow/evidence/it16/`).

## Curation rules

- The source is the published file, byte for byte: never edited, reformatted or re-encoded (tabs and line
  ends kept). Where the archive has an `.alt.c` (its version for modern systems), the wall builds it;
  endoh3 is the exception (below).
- Builds keep `-Wall` and never `-w`, `-Werror` or `-fpermissive`. Every curated build has `-fsigned-char`:
  `char` is unsigned on the Pi's ARM Linux, and these programs were written where it is signed. The `-Wno-...` flags are
  the archive's own silencers (its Makefile's `CSILENCE`), the `-std` and `-include` its `CSTD` and
  `CINCLUDE`, the defines its `CDEFINE`.
- A run draws inside 80 columns and 23 rows (the strip has the 24th), ASCII only (the renderer draws a code
  point of 256 or more as `?`). A typed source line may be longer: the typing wraps it, the run never does.
- No `make`, `less`, `read`, `clear`, `/dev/tty`, `setsid`, `nohup`, background `&` or `daemon` in a run;
  run scripts are POSIX `sh` (dash on the Pi), run as `sh <script>`. A run that ends by a signal reads as a
  crash, so a run ends by the pipeline's cut (`run_seconds`) or by a normal exit.
- No entry waits on the terminal, needs raw modes or X11, or animates at character scale; large motion is
  preferred (core plan, Task 19). thadgavin (curses) polls it: `nodelay(stdscr,1)` and a `getch()` each frame
  (`thadgavin.alt.c:59-60`, called at :97), which ends the program on `q`; the show never writes to a run's
  terminal (`show/terminal.py` only reads the pty), so the poll finds nothing and the run goes on to the
  pipeline's cut. endoh1 reads stdin from a file of its own directory, never the terminal.
- `rows` (it16) gives the program a 24-row pty from RUN on, for a program whose frame ends in a newline on
  its 23rd line; the typing and the build stay at 23 rows. `full_screen` is used by none.
- The wall is 128x64 (`show.poc.toml`): the strip shows "<author>, <year>". An attribution longer than the
  strip's 21 characters is shown in pieces cut at spaces, each three seconds, before `Not A.I.` (thadgavin's
  three; C54, Q91).

## 1: sloane, "Homer's favorite"

Andy Sloane, IOCCC 2006 (`2006/sloane`). A spinning, shaded donut.

- Files: `sloane.c` (as judged), `sloane.alt.c` (built: the archive's version that sleeps between frames).
- Build: `-std=gnu99`, the silencers `-Wno-implicit-function-declaration -Wno-implicit-int`, `-include
  math.h -include stdio.h`, `-DS=75000` (the `usleep` between frames in microseconds, the archive's
  default), `-fsigned-char -O2`, `-lm`.
- Run: `./prog`, until the cut at 40 s.
- `rows = 24`: a frame is a cursor-home and 23 lines each ending in a newline; on 23 rows the last newline
  scrolls the screen and the frame tears.
- Warnings: Mac 8 (4 `-Wdeprecated-non-prototype`, 2 `-Wreturn-type`, 1 `-Wshift-op-parentheses`,
  1 `-Wunsequenced`); Pi 6.

## 2: imc, "Best output"

Ian Collier, IOCCC 1992 (`1992/imc`). The Mandelbrot set and Julia sets in characters.

- Files: `imc.c` (no `.alt.c` exists), `tour.sh` (ours).
- Build: `-std=gnu90`, the silencers `-Wno-implicit-function-declaration -Wno-format`, `-fsigned-char -O2`.
- Run: `sh tour.sh`, the archive's `try.sh` without its build, key waits and pager: four views at 78x22, nine
  seconds each, cleared by `ESC[H ESC[2J`: the 16-shade view `-mask 15 -limit 15`, then three of try.sh's
  five (`-limit 256 -julia 0.5 -0.5`; `-limit 1024 -centre 1 2 -julia 2 -2.5`; `-limit 256`). It exits 0
  after 36 s, under the 40 s cut; crowd mode's 10 s shows the first view and the start of the second.
  stderr is dropped: imc writes a progress dot a row there, which shares the pty and would shift every row
  by one.
- `rows`: not set (23). A view is a blank line, 22 rows of 78 columns and a newline.
- Warnings: Mac 2 (`-Wimplicit-int`, `-Wdeprecated-non-prototype`); Pi 12.
- Known: the third view (try.sh's `-limit 1024 -centre 1 2 -julia 2 -2.5`) lights only 10 rows. Dropped by
  the owner at the wall on 2026-10-01 (Q86, Q92): `-limit 1024 -julia 2 -2.5`, one lit block at 128x64, and
  `-limit 1024`, nearly alike to `-limit 256` (471 and 469 lit cells). The owner found the entry hard to read
  on the 2 x 2 wall and put it down to the wall's size.

## 3: thadgavin, "Most portable output"

Gavin Buttimore and Thaddaeus Frogley, IOCCC 2000 (`2000/thadgavin`). A full-screen plasma in curses.

- Files: `thadgavin.c` (as judged), `thadgavin.alt.c` (built).
- Build: `-std=gnu99`, the silencers `-Wno-empty-body -Wno-implicit-int -Wno-unsequenced`, `-include
  unistd.h -include stdlib.h`, `-DZ=30` (the curses mode's sleep between frames in microseconds, the
  archive's default) and `-DZS=0` (the SDL mode's, unused here), `-fsigned-char -O2`, `-lncurses -lm`.
- Run: `TERM=vt100 ./prog`, until the cut at 40 s. Curses reads the pty's size (80x23). `TERM=vt100`
  because under `xterm` the Pi's ncurses 6.5 sends REP (`CSI n b`), which pyte drops (22 of 23 rows
  wrong); the Mac's terminfo has no REP, so only the Pi shows it.
- `rows`: not set (23).
- Warnings: Mac 2 (1 `-Wdeprecated-non-prototype`, 1 linker note on the alignment of `__DATA,__common`);
  Pi 7 (with `libncurses-dev`).
- Known: line 85 of `thadgavin.alt.c` is 81 columns: the typing wraps it. Every frame redraws the whole
  screen, so the plasma is the flash question: kept at the archive's speed, the governor's held, area and
  squares at 128x64 go to the owner with the sheets (Q87).

## 4: endoh1, "Most complex ASCII fluid - Honorable mention"

Yusuke Endoh, IOCCC 2012 (`2012/endoh1`). Fluid dynamics in characters: the input text collapses and
flows under gravity.

- Files: `endoh1.c` (as judged, and the run's input), `endoh1.alt.c` (built: the archive's version with
  an alarm).
- Build: `-std=gnu11`, the silencers `-Wno-absolute-value -Wno-strict-prototypes
  -Wno-misleading-indentation`, `-DG=1 -DP=4 -DV=8` (gravity, pressure and viscosity, the archive's
  values), `-DA=40` (the alt's `alarm`, in seconds), `-fsigned-char -O2`, `-lm`.
- Run: `./prog < endoh1.c`, the author's synopsis: the program's own source poured as fluid. stdin is a
  file of the directory, never the terminal. `run_seconds = 36` puts the pipeline's cut before the alarm:
  SIGALRM at 40 s would end the run by a signal, which reads as a crash; the alarm stays the backstop.
- `rows`: not set (23).
- Warnings: Mac 0; Pi 0.
- Known: a frame is `ESC[1;1H` and 26 lines of at most 79 columns (an 80x25 field). On the 23-row pty
  each frame scrolls by four rows, so the field's top four rows are never seen and a render between two
  chunks can tear; `rows` cannot reach 26, and the sheet judges it. Line 42 of `endoh1.alt.c` is 81
  columns: the typing wraps it.

## 5: endoh3, "Most head-turning"

Yusuke Endoh, IOCCC 2020 (`2020/endoh3`). A clock whose source is a mirrored clock face: every five
seconds it prints its own next source, which is compiled and run.

- Files: `prog.c` (built), `clock.sh` (ours). `prog.alt.c` is left out (Q85): its lines are 85 columns
  and seven carry a three-byte UTF-8 letter, which the wall would wrap and draw as `?`. `prog.c` prints 23
  lines of at most 79 columns, ASCII, and stays so over three generations (Mac and Pi).
- Build: `-std=gnu17`, the silencer `-Wno-strict-prototypes`, `-fsigned-char -O2`.
- Run: `sh clock.sh`, the archive's `run_clock.sh` loop in POSIX sh: `ESC[H ESC[2J`, `./prog | tee
  clock.c`, `sleep 5`; then forever `cc -std=c11 -Wall -Wextra -pedantic -fsigned-char -O3 -o clock
  clock.c` (its warnings discarded, a failed compile ends the run with exit 1), the clear, `./clock | tee
  clock.c`, `sleep 5`. It writes `clock.c` and `clock` in its own directory (the run's cwd), which stays
  writable; both are ignored by git. Until the cut at 40 s.
- `rows = 24`: a clock is 23 lines and a final newline.
- Warnings: the build 0 (Mac and Pi); the loop's compile 2 a generation on the Mac (`-Wstrict-prototypes`),
  never shown.
- Known: the loop runs `cc` under the run's limits (256 MB address space, no network); the fake-clock play
  ends before the first `sleep 5`, so no test proves the loop: the early Pi probe (three generations) and
  the operator's real-time check do.

## 6: hello

The pipeline's own test entry (Trey, 2026): not curated, no licence file, `cc -Wall`. It stays on
station 6.
