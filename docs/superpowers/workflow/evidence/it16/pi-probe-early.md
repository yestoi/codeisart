The operator's early probe on the Pi 5, 2026-10-01 00:23 to 00:25 CDT, before any code of iteration 16 (the plan was in its review).
Not the iteration's Pi check: the published sources from the scratchpad fetch (ioccc-src/winner at cb48eb9) and the plan's build lines, built in a directory under /tmp that the same ssh call made and removed. Each call ran under `flock -w 300 /tmp/pi5.lock` inside the ssh call (Q83); the lock was free both times. The script: the session scratchpad's `ioccc/pi_probe.sh`.

gcc (Debian 14.2.0-19) 14.2.0. `unshare -rn` works (uid 0 inside).

| Entry | Build under gcc 14 | Warnings | What |
|---|---|---|---|
| sloane (`sloane.alt.c`) | exit 0 | 6 | 2 return-type, 1 "data definition has no type or storage class", 1 sequence-point, 2 parentheses |
| imc (`imc.c`) | exit 0 | 12 | 3 builtin-declaration-mismatch (exit, free, malloc), 1 infinite-recursion, 1 return-type, 7 unused-value |
| thadgavin (`thadgavin.alt.c`) | exit 1 | 0 | `fatal error: curses.h: No such file or directory`: the Pi has no `/usr/include/curses.h` or `ncurses.h` |
| endoh1 (`endoh1.alt.c`, `-DA=40`) | exit 0 | 0 | |
| endoh3 (`prog.c`) | exit 0 | 0 | |

- thadgavin cannot be built on the Pi until `libncurses-dev` is installed there: the owner's item (`sudo apt install libncurses-dev`; the loop writes nothing outside ~/codeisart and /tmp on the Pi, rule 9a).
- endoh3, three generations (prog's output compiled and run, twice more): each prints 23 lines, widest 79, no non-ASCII or control byte. The loop's compile (`cc -std=c11 -Wall -Wextra -pedantic -fsigned-char -O3`) exits 0 with 0 warnings each time inside `unshare -rn` with the address space capped at 256 MB (`ulimit -v 262144`, the run's RLIMIT_AS, `show/sandbox.py` DEFAULT_MEMORY). The compile's seconds were not measured (`/usr/bin/time` and `bc` are not on the Pi).
- sloane's first bytes: `ESC[2J`, a newline, `ESC[H`, then the frame. imc's first view: 23 lines, widest 78. endoh1's first bytes: `ESC[2J ESC[1;1H`, then the frame.
- The operator's guard (scripts/operator/guard_bash.py:61) refuses a recursive rm of a /tmp path of 12 characters or fewer (`/tmp/it16-op`) and of a path holding `$`: the Pi's scratch directory is the literal `/tmp/it16-operator`, made and removed in the one call, under the lock.
