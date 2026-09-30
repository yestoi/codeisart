The owner's session's probe of the five researched entries, 2026-09-30 evening, before the run that D5 starts (Q80).
Not the loop's evidence: made in the scratchpad at HEAD ab5276b with `tools/show_shot.py --entry <dir> --seconds 25
--every-ms 1000 --look led --allow-black` at the default config (512x192, 80x24, the strip on row 24), on the Mac
(Apple clang 17; no unshare). The entry.toml of each is the probe's (the build and run lines the operator starts from).

All five build with -Wall and no error on the Mac: sloane 8 warnings, imc 2, thadgavin 2, endoh1 0, endoh3 0.
- sloane (sloane.alt.c, -DS=75000): the donut spins over the checkerboard for the whole run. The rows tear as the
  research predicted (the 23-row pty scrolls on the frame's last newline): the picture wants a 24-row pty with the
  strip kept (`rows = 24` in entry.toml, D5).
- thadgavin (thadgavin.alt.c, -DZ=30 -DZS=0, `TERM=xterm ./prog`, -lncurses): the plasma fills all 23 rows and runs
  to the end. Its whole-screen redraw is the flash question for the governor's numbers.
- endoh1 (endoh1.alt.c, `./prog < endoh1.alt.c`): the source's block letters collapse into fluid. The run ends after
  10 s: the alt's `A` macro is the timer in seconds (10 default, 60 at most): build with -DA=40.
- imc (imc.c, `./prog -text -size 78 22 -mask 15 -limit 15`): a clean Mandelbrot in 0.2 s, then the dwell: the run
  must be a script that tours several views with pauses (the entry's try.sh has the views).
- endoh3 (prog.alt.c, `./prog`): prints its own source as a mirrored clock once; in the probe its longest output line
  read 89 characters, so the lines wrap and the screen scrolls (the sheet's dwell shows fragments). The run must be
  the recompile loop of the archive's run_clock.sh (print, tee to clock.c, cc, sleep 5) and the line width must be
  understood before the entry is kept (a wider terminal is not available: 80 columns is the wall).
