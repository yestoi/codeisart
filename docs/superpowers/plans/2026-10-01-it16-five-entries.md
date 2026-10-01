# Iteration 16: the five entries (D5)
BASE: O1's commit (code head at the plan: 1ec0505). Roadmap D5 (Q80, Q81, Q82; notes "D5" x3, it10 4, it10 GATE C,
it11 `tests/test_show_shot.py:153`, it13 3). Thin plan. NOT a safety slice: `arcade/flash.py`, `arcade/brightness.py`,
`show/display/colorlight.py`, `show/wall.py`, `deploy/` are not edited. Core plan: Amendments line 67 and Task 19
(`docs/superpowers/plans/2026-09-22-show-daemon.md:3625-3676`); spec 4.3 (`...specs/2026-09-22-code-is-art-design.md:
227`: an entry directory holds `entry.toml`, the unmodified source and `fallback.cast`, all three tracked by
`.gitignore:21-25`). Iteration 17 is D5's slack.

SRC = `/private/tmp/claude-502/-Users-trey-dev-codeisart/55e7f702-6acd-44cf-b418-6da2919b2552/scratchpad/ioccc`: the
operator's fetch of ioccc-src/winner at `cb48eb9572c2735a6f12ec56790e014311674a96`. No agent fetches; `cp` copies.

## Global Constraints
- Test command, from the root (a worktree's root in a worktree): `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
  <root>/.venv/bin/python -m pytest -q -rs` (a worktree uses the main checkout's venv by its absolute path). At
  4ec98e4: 1762 passed, 3 skipped, 319 s on the idle Mac; limit 420 s (config.md "Suite time"). A worktree's extra
  skip `tests/arcade/test_pose_mediapipe.py:223` (model not in git) is expected. New test time, `--durations=0`:
  T-rows 3 s, T-curated 45 s for six directories (each play 8 s at most), T-shot 6 s.
- Test-first; only your files; never `cd` (absolute paths, `git -C`; in a worktree plain git, one command a call);
  `git add` by name; no stash, push, or command over 10 minutes; `tmp_path`; children killed (`player.stop()` in a
  `finally`); `skipif(shutil.which("cc") is None)` on every test that builds. An entry task commits its directory
  BEFORE its full-suite run (`tests/test_show_shot.py:153` asserts `git status --porcelain entries` is empty).
  Trailer `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. No rulings: a gap is reported, not decided.
- No existing assert is removed or weakened. A missed bound is reported, never loosened.
- The wall of this run is 128x64 (`show.poc.toml`, ink view; Q82). A NEW test that renders or governs frames does it
  at `load_config(ROOT / "show.poc.toml")`; no code, config, test or sheet for 512x192 or 512x128. The terminal stays
  80 columns by 23 rows plus the strip (`Config.columns = 80`, `Config.rows = 24`, `show/config.py:23-24`).
- Sources byte for byte from SRC; a published `.c` is never edited, reformatted or re-encoded (no CRLF, no tabs
  expanded: `imc.c` has 166 tabs). Builds: `-Wall` always, `-w` never, `-fsigned-char` in every curated build, the
  probe's `-Wno-...` (all from the archive's Makefile `CSILENCE`) kept, no `-Werror`, no `-fpermissive`.
- Every curated run: no program row past 80 columns, ASCII only (`show/renderer.py:91` draws a code point >= 256 as
  `?`), no `make`, `less`, `read`, `clear`, `/dev/tty`, `setsid`, `nohup`, background `&`, `daemon` (it10 GATE C), POSIX
  `sh` only (dash on the Pi). A run that ends by a signal reads as a crash (`show/pipeline.py:181-187`).

## Lanes
- O1 (orchestrator, main checkout, first): the `.gitignore` lines below, one commit: BASE.
- GROUP 1, together after O1: T-rows (opus) in the main checkout (the serial lane); T-curated (opus) and T-shot
  (sonnet) in worktrees from BASE. The three share no file.
- GROUP E, from the HEAD with T-rows and T-curated merged, `isolation: "worktree"`, four at most at once:
  E-sloane (sonnet), E-imc (opus), E-thadgavin (sonnet), E-endoh3 (opus) first; E-endoh1 (sonnet) when one ends.
- Merge order: T-curated, T-shot, then E-sloane, E-imc, E-thadgavin, E-endoh1, E-endoh3 (station order). After each
  entry merge: `tests/test_curated_entries.py tests/test_entries.py tests/test_show_shot.py`; the full suite after
  T-shot's merge and after the last merge. O2 (orchestrator) writes `entries/README.md` last.
- Owners. O1: `.gitignore`. T-rows: `show/entries.py`, `show/pipeline.py`, `tests/test_entries.py`,
  `tests/test_pipeline.py`, `tests/show_helpers.py`, `tests/test_renderer.py`. T-curated:
  `tests/test_curated_entries.py`. T-shot: `tools/show_shot.py`, `tests/test_show_shot_governed.py`. E-<name>:
  `entries/<name>/` only. O2: `entries/README.md`. Nobody: `entries/hello/`, `show/renderer.py`, `show/terminal.py`,
  `show/sandbox.py`, `show.toml`, `show.poc.toml`, `deploy/`, the safety files.

## O1 (orchestrator): what git tracks under entries/
`.gitignore:22-25` ignores `entries/*/*` save `*.c`, `entry.toml`, `fallback.cast`: a run script or a `LICENSE.md`
would be ignored, and endoh3's run writes `clock.c` (tracked by `!entries/*/*.c`) into its directory. Append after
line 25, in this order (the last match wins): `!entries/*/*.sh`, `!entries/*/LICENSE.md`, `entries/endoh3/clock.c`.
Check (no `-v`): `git -C <root> check-ignore entries/x/a.sh entries/x/LICENSE.md entries/endoh3/clock.c entries/x/prog`
prints only the last two. Commit `chore(entries): track run scripts and licences, ignore endoh3's clock.c (it16 O1)`.

## T-rows (opus): `rows`, the entry's pty rows from RUN on
```
@dataclass(frozen=True)
class Entry:                     # show/entries.py:18-33; one field after full_screen
    rows: int | None = None      # the pty's rows in RUN and FALLBACK; None: as today
def load_entry(dir: Path) -> Entry   # `rows` optional; when present an int (not a bool) >= 1, else EntryError
                                     # f"{toml_path}: rows must be an integer >= 1"; read beside full_screen (:74)
class EntryPlayer:               # show/pipeline.py:84-86
    @property
    def typing_rows(self) -> int # SOURCE and BUILD, today's rule: cfg.rows when full_screen, else cfg.rows - 1
    @property
    def rows(self) -> int        # RUN and FALLBACK: min(entry.rows, cfg.rows) when set, else typing_rows
def write_entry(..., rows: int | None = None) -> Path   # tests/show_helpers.py: writes `rows = N` when given
```
`start` (:103) resets to `typing_rows`: the typed line and the build's last line never sit on row 24 under the strip
(B2). `_start_run` (:168) sets `term.rows = self.rows` and resizes `term.screen` to it before the CastWriter (:171) and
`term.run` (TIOCSWINSZ from `term.rows`, `show/terminal.py:72`); pyte keeps content and cursor. The fallback's reset
(:202) stays at `self.rows`. The renderer draws `min(program_rows, screen.lines)` (`show/renderer.py:73-80`).
Tests: two in `tests/test_entries.py` (`:94-105`), four in `tests/test_pipeline.py` (`:433`), one in `test_renderer.py`.
- `test_rows_defaults_none_and_reads_an_integer`: no key gives None; `rows = 24` gives 24; `rows = 1` gives 1.
- `test_rows_must_be_an_integer_of_at_least_one` (bad: `0`, `-1`, `true`, `23.5`, `"24"`): EntryError naming rows.
- `test_player_rows_follow_the_entry_then_the_config`: no pty, `cfg.rows = 24`; (rows, full_screen) -> (rows,
  typing_rows): (None, F) 23, 23; (None, T) 24, 24; (24, F) 24, 23; (12, F) 12, 23; (30, F) 24, 23; (12, T) 12, 24.
- `test_an_entry_with_rows_gets_that_pty_size`: `run="stty size"`, `build="true"`: rows 24, 30: `24 80`; 12: `12 80`.
- `test_a_24_row_entry_types_and_builds_at_23_rows_and_runs_at_24`: `term.rows` and `term.screen.lines` are 23 at
  every SOURCE and BUILD tick and 24 from the first RUN tick on.
- `test_the_fallback_replays_at_the_entry_rows` (needs cc): a `rows = 24` crash entry with a cast: 24 in FALLBACK.
- `test_a_24_row_screen_renders_its_first_23_rows_under_the_strip`: at `renderer_for(load_config(show.poc.toml))`, a
  pyte Screen(80, 24) with a different letter on every row renders the same frame as a Screen(80, 23) holding its
  first 23 rows, the strip "NOW" on both.

## T-curated (opus): `tests/test_curated_entries.py`, proven on hello
Constants: `ENTRIES = ROOT / "entries"`; `DIRS` = its subdirectories, sorted, ids = the slug (so `-k <slug>` runs
one); `CURATED` = the DIRS holding a `LICENSE.md`; `COMMIT = "cb48eb9572c2735a6f12ec56790e014311674a96"`;
`FAKE_STEP = 0.2` (fake seconds a tick); `TICK = 0.01` (real sleep a tick); `PLAY_DEADLINE = 8.0` (real seconds a
play); `WITNESS_COLUMNS = 160`; `WALL_COLUMNS = 80`; `PEAK_LIT_MIN = 100`; `FINAL_LIT_MIN = 100`;
`REP = re.compile(rb"\x1b\[\d*b")` (REP, "repeat the last character", which pyte drops: review B5). The play's config:
`replace(load_config(ROOT / "show.poc.toml"), min_build_seconds=0.0, dwell=0.0, capture=False)` (no frame is rendered).
The play: `shutil.copytree` of the directory into `tmp_path` (nothing lands in the checkout),
`EntryPlayer(load_entry(copy), Terminal(cfg.columns, cfg.rows - 1), cfg)`, ticked with `now` advancing FAKE_STEP a tick
(the SOURCE, the build's timeout and the RUN's cut are by the fake clock: RUN ends at `run_timeout()` fake seconds,
about 2 to 4 real seconds) until DONE or PLAY_DEADLINE. When RUN begins (after `$ <run>` is fed), a witness joins
`player.term.listeners`: a fresh `pyte.Screen(WITNESS_COLUMNS, player.rows)` with LNM and a `pyte.ByteStream`, which
also keeps the RUN's bytes (a chunk can split an escape): the program's cells alone, a line past 80 unwrapped.
- `test_the_entries_directory_loads_whole`: `load_entries(ENTRIES)` holds every directory in DIRS (none skipped for
  an error or a duplicate station).
- `test_every_entry_but_hello_has_a_licence`: the DIRS without `LICENSE.md` are exactly `{"hello"}`.
- `test_entry_build_keeps_its_warnings[slug]`: `-Wall` is a word of `build`, `-w` is not; CURATED also `-fsigned-char`.
- `test_curated_sources_match_the_licence_sums[slug]` (CURATED): every line of LICENSE.md matching
  `^[0-9a-f]{64}  \S+$` names a file of the directory whose sha256 is that value; the entry's `source` is one of them;
  LICENSE.md contains COMMIT and `CC BY-SA 4.0`.
- `test_entry_plays_through[slug]` (needs cc): the phases are SOURCE, BUILD, RUN, DWELL, DONE in order (so the build
  exited 0); `player.failure is None`; no screen line starts `***`; for a CURATED slug, RUN ended at the pipeline's
  cut (fake time from RUN to DWELL >= `player.run_timeout()`; hello exits by itself); on the witness's first
  `cfg.rows - 1` rows, at least PEAK_LIT_MIN non-space cells at some RUN tick and FINAL_LIT_MIN as DWELL begins; after
  every RUN tick no witness cell at x >= WALL_COLUMNS and no character >= 128; no `REP` match in the RUN's bytes.
  Prints the slug, real seconds, peak and final lit counts.
Proof on hello at BASE: the others pass; the sums test's empty parameter set is one skip until the first entry merges
(journaled). The review's emulation, witness finals: hello 138, endoh3 804, endoh1 1245, thadgavin 1614, imc 1716,
sloane 1790; a run line that fails at once (missing script, `exit 1`, missing binary) ends RUN at 0.2 fake s.

## T-shot (sonnet): the governor's numbers for one entry
`--entry` plays through the renderer only (`tools/show_shot.py:236-250`); held, area and squares come only from
`--session` (`:329-390`), which plays hello (`:320`). Add:
```
def frames_from_session(name, cfg, seconds=SESSION_SECONDS, every_ms=500, presses=None, meter=None,
                        entry_dir: Path | None = None)   # name "entry": entry_dir's copy alone, at station 1
SESSIONS = ("presses", "strobe", "entry"); PRESSES["entry"] = [(1.0, 1)]
--governed   # CLI, with --entry only: frames_from_session("entry", cfg, seconds, every_ms, meter=FlashMeter(cfg.fps,
             # cfg.gamma), entry_dir=args.entry); prints `held <n> area <a> squares <s>` as --session does (:539)
```
`_session_entries("entry", cfg, dest, entry_dir)` copies the directory to `dest / <slug>` and rewrites its `station`
line to 1, as hello's copy is rewritten (`:321-326`). `--governed` without `--entry` is an argparse error.
- `test_governed_entry_session_runs_the_entry_through_the_governor`: at show.poc.toml, a `write_entry` HELLO_C entry
  at station 4: frames are labelled `<t>s held <n> area <a> sq <s>`; a strip text equals "Test Author, 2026" (the
  21-character strip at 128x64 shows "<author>, <year>", never the title); the checkout's `entries/` is untouched.
- `test_governed_needs_an_entry`: `main(["--governed", "--session", "presses", "--out", ...])` exits by argparse.

## The entries (E-<name>), common to all five
Each task creates `entries/<name>/` holding: the published files below by `cp` from `SRC/<name>/`; `entry.toml` as
given, plus `build_seconds = 60` and, unless given, `run_seconds = 40` (a line-end `\` is this plan's wrap: one line
in the file, joined by a space); a run script where given; `LICENSE.md`: `# <year>/<name>: <award>`, the authors as
`.entry.json`'s `author_set` gives them (handles, `_` read as a space), the archive's URL
`https://github.com/ioccc-src/winner/tree/<COMMIT>/<year>/<name>`, the commit, "Creative Commons Attribution-
ShareAlike 4.0 International (CC BY-SA 4.0), https://creativecommons.org/licenses/by-sa/4.0/", a fenced block of
`<sha256>  <file>` lines (the values below, the archive's SHA256SUMS), and a "Changes" line: the `.c` files are
unmodified; `entry.toml` and any run script are this installation's adaptation under the same licence. Then:
`tests/test_curated_entries.py -k <name>` green, commit `feat(entries): <year>/<name> on station <n> (it16)`, the full
suite. Report the warnings (count, kinds, `LC_ALL=C`), the play's printed line and the first screen in a sentence.
Typing wraps the 81-column line of thadgavin.alt.c and of endoh1.alt.c: the source as published, not a run row.

### E-sloane (sonnet), station 1
Files: `sloane.c` 3cc9c41a70a424825f7fa6baa1b0c5cee69c9e7ce25198a5d5caf4256e269fd8, `sloane.alt.c`
7c01b5ebb938b4742832906b96807f28cc759b230eb329131c6dc46c533c3afd. Award "Homer's favorite"; author `Andy_Sloane`.
```toml
title = "Homer's favorite"
author = "Andy Sloane"
year = 2006
station = 1
source = "sloane.alt.c"
build = "cc -std=gnu99 -Wall -Wno-implicit-function-declaration -Wno-implicit-int -include math.h \
-include stdio.h -DS=75000 -fsigned-char -O2 -o prog sloane.alt.c -lm"
run = "./prog"
rows = 24
```
`rows = 24`: a frame is a cursor-home and 23 lines each ending in a newline (research "Sloane's IOCCC winner"); on 23
rows the last newline scrolls (the probe's tear). Plan writer's Mac check: 8 warnings (4 deprecated-non-prototype,
2 return-type, 1 shift-op-parentheses, 1 unsequenced).

### E-imc (opus), station 2
Files: `imc.c` a3b267045240a8cf854c87658b5c737a7dea0a0861c82c5f207c67094ace90fa (no `.alt.c` exists: the wall builds
`imc.c`), `tour.sh` (ours). Award "Best output"; author `Ian_Collier`.
```toml
title = "Mandelbrot"
author = "Ian Collier"
year = 1992
station = 2
source = "imc.c"
build = "cc -std=gnu90 -Wall -Wno-implicit-function-declaration -Wno-format -fsigned-char -O2 -o prog imc.c"
run = "sh tour.sh"
```
`tour.sh`, POSIX sh, from the archive's `try.sh` (its `make`, `read` and `less` dropped): six views, each `printf
'\033[H\033[2J'`, then `./prog -text -size 78 22 <view> 2>/dev/null`, then `sleep 6`; exits 0 after the last (36 s,
under the 40 s cap; crowd mode's 10 s shows the first two). Views in order: `-mask 15 -limit 15` (the probe's, 16
shades); then try.sh's five at 78x22: `-limit 256 -julia 0.5 -0.5`; `-limit 1024 -julia 2 -2.5`; `-limit 1024 -centre 1
2 -julia 2 -2.5`; `-limit 256`; `-limit 1024`. Why `2>/dev/null`: imc writes a progress dot a row to stderr (README
"Options"), which shares the pty and shifts each row by one. Mac check: each view prints a blank line, 22 rows of 78
columns and a newline, ASCII, in under 0.01 s; 2 warnings.

### E-thadgavin (sonnet), station 3
Files: `thadgavin.c` 3d46f69fc3e0743a4120fbef778f0030edddff8b69f34c12236245e1eefd48e1, `thadgavin.alt.c`
3dfaa1bf754bbc50da4af5c1132a2fe3bc9fe04d7a856b9dc6091db32e7d8836. Award "Most portable output"; authors
`Gavin_Buttimore`, `Thaddaeus_Frogley`.
```toml
title = "Plasma"
author = "Gavin Buttimore and Thaddaeus Frogley"
year = 2000
station = 3
source = "thadgavin.alt.c"
build = "cc -std=gnu99 -Wall -Wno-empty-body -Wno-implicit-int -Wno-unsequenced -include unistd.h \
-include stdlib.h -DZ=30 -DZS=0 -fsigned-char -O2 -o prog thadgavin.alt.c -lncurses -lm"
run = "TERM=vt100 ./prog"
```
The curses mode reads `LINES` and `COLS` (80x23 here). `TERM=vt100` (review B5): under `xterm` the Pi's ncurses 6.5
sends REP (`CSI n b`), which pyte drops (22 of 23 rows wrong, `evidence/it16/pi-probe-early.md`); vt100 is clean on
both machines. The Mac cannot show this (its terminfo has no `rep`): the Pi's check (a) is where it bites.

### E-endoh1 (sonnet), station 4
Files: `endoh1.c` de593a8af39ec73e120bacecae2a09bc9858da6457894840f2f816513cc18fb4, `endoh1.alt.c`
a7e469298d33cff380aa6eb7c13fc009c92d0557fee468b541c97cde347e5919. Award "Most complex ASCII fluid - Honorable
mention"; author `Yusuke_Endoh`.
```toml
title = "ASCII fluid"
author = "Yusuke Endoh"
year = 2012
station = 4
source = "endoh1.alt.c"
build = "cc -std=gnu11 -Wall -Wno-absolute-value -Wno-strict-prototypes -Wno-misleading-indentation \
-DG=1 -DP=4 -DV=8 -DA=40 -fsigned-char -O2 -o prog endoh1.alt.c -lm"
run = "./prog < endoh1.c"
run_seconds = 36
```
`-DA=40` is `alarm(A)` (endoh1.alt.c:34): SIGALRM at 40 s, and a pty process dead by a signal is a crash
(`show/pipeline.py:181-187`; `sh -c` may exec the lone command). `run_seconds = 36` puts the pipeline's cut first (idle
cap 40); -DA=40 stays the backstop. The input is `endoh1.c`, the author's synopsis (SRC/endoh1/README.md:181); the
typed source stays `endoh1.alt.c`. Mac check: 0 warnings; a frame is `ESC[1;1H` and 26 lines of at most 79 columns.

### E-endoh3 (opus), station 5, with a cut rule
Files: `prog.c` 569720b75cabccd1db57dec1d7218e34e8b17f17f498711b19f95d3035913e2f, `clock.sh` (ours). `prog.alt.c`
is NOT copied. Award "Most head-turning"; author `Yusuke_Endoh`.
The 89 characters (Apple clang 17): the probe built `prog.alt.c`, whose row stride is 86 (`i%86`, `k/2*86`, `r<44`): 23
lines of 85 columns, seven with one three-byte UTF-8 letter (the archive's "Unicode letters"), 89 bytes at most, which
the wall would wrap and draw as `?`. `prog.c` prints 23 lines of at most 79 columns, ASCII, and a final newline (so
`rows = 24`); its output compiled again (the loop's flags, 3 pedantic warnings) prints 79 columns again.
```toml
title = "Mirror clock"
author = "Yusuke Endoh"
year = 2020
station = 5
source = "prog.c"
build = "cc -std=gnu17 -Wall -Wno-strict-prototypes -fsigned-char -O2 -o prog prog.c"
run = "sh clock.sh"
rows = 24
```
`clock.sh`, POSIX sh, the archive's `run_clock.sh` loop: first `printf '\033[H\033[2J'`, `./prog | tee clock.c`,
`sleep 5` (the first clock at once); then forever: `cc -std=c11 -Wall -Wextra -pedantic -fsigned-char -O3 -o clock
clock.c >/dev/null 2>&1 || exit 1`, `printf '\033[H\033[2J'`, `./clock | tee clock.c`, `sleep 5`. The escape replaces
`clear` (no terminfo lookup); the compile's warnings are discarded (they would flash between ticks); a failed compile
ends the run with exit 1, a normal end. Files are written in the entry's directory (the run's cwd), which systemd
keeps writable (spec 4.3 step 4); `clock.c` is ignored by O1.
CUT RULE: keep the entry only when (1) `test_entry_plays_through[endoh3]` passes and (2) a three-generation check in
a scratch directory (prog, then cc and run of each output twice) prints, each time, 23 lines of at most 80 columns,
ASCII only. Otherwise commit nothing under `entries/endoh3/`, report the widths and the generation that failed, and
stop: the entry is out of it16; an alternate is iteration 17's decision, not the task's.

## O2 (orchestrator, after the merges): `entries/README.md`
An entry a section, station order: credit, award, files, the build's flags and why (`-fsigned-char`: ARM's unsigned
char; the archive's silencers; the defines), the run and its timing, `rows`, the warnings, the known items (typed
lines over 80, endoh1's scrolling frame, thadgavin's flash, endoh3's alt left out). hello on 6. The curation rules
(core plan line 67, Global Constraints). Commit `docs(entries): curation notes (it16 O2)`.

## Operator, after the review (inline, not implementers); E = `docs/superpowers/workflow/evidence/it16`
1. Sheets, 128x64 only, on the Mac, each entry: `.venv/bin/python -m tools.show_shot --entry entries/<name> --governed
   --config show.poc.toml --seconds 70 --every-ms 1000 --look led --out E/it16-<name>`; record the printed `held area
   squares` per entry in E/README.md as the whole play's (typing, build, run and attract), not the program's alone.
2. Fallbacks on the Mac, in place (spec 4.3), once the five `test_entry_plays_through` are green (a broken run line
   would be kept as a junk cast), about 55 s each: `.venv/bin/python -m show --backend fake --capture --config
   show.poc.toml --play <name>`; note each cast's size; `git status --porcelain entries` shows only the five; commit
   `chore(entries): fallback recordings (it16)`; a cast over 5 MB is not committed (journaled).
3. The Pi 5, read-only on its checkout (rule 9a), shared (Q83), nothing kept between calls: one call a check, each a
   script file `<c>.sh` (no nested quoting); T is the literal `/tmp/it16-operator` (the guard refuses an rm of a `$`
   path or a short /tmp one): `git -C /Users/trey/dev/codeisart archive --format=tar --add-file=<c>.sh HEAD | ssh
   trey@codeisart.local "flock -w 300 /tmp/pi5.lock sh -c 'rm -rf /tmp/it16-operator; mkdir /tmp/it16-operator && tar
   -x -f - -C /tmp/it16-operator && sh /tmp/it16-operator/<c>.sh; rm -rf /tmp/it16-operator'"`. If flock gives up after
   300 s: the Mac's work, then the call again; a check that never got the lock is journaled as not run.
   (a) `gcc --version | head -1; env -C T SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy ~/codeisart/.venv/bin/python -m
   pytest -q -rs -p no:cacheprovider --basetemp=T/pt tests/test_curated_entries.py tests/test_entries.py
   tests/test_sandbox.py tests/test_pipeline.py` (plays under `unshare -rn`, `show/sandbox.py:56-59`, and RLIMIT_AS).
   (b) Per entry, in `T/entries/<name>`: its `build` (the venv's `tomllib`) run under `LC_ALL=C` into a log; print the
   name, exit status and the log's `grep -c warning:`. A gcc 14 error gets the Makefile's own `-Wno-<x>`, never `-w`.
   (c) endoh3 in real time: build as (b), then `timeout 15 unshare -rn sh -c 'ulimit -v 262144; sh clock.sh' > log`;
   print timeout's status (124: still ticking) and the generations shown (the log's `ESC[H ESC[2J`s, 5 s a tick).

## Decisions taken
- The sums: in each LICENSE.md, checked for good by `test_curated_sources_match_the_licence_sums`; values in this plan.
- endoh3 builds `prog.c` with `rows = 24`, not `prog.alt.c` (85 columns, non-ASCII letters); the research ran it too.
- endoh1 reads `endoh1.c` (the author's synopsis); `run_seconds = 36` under `-DA=40`: the alarm never ends a run.
- imc's tour: the probe's 16-shade view first, then try.sh's five views at 78x22, six seconds each, stderr dropped.
- The curated test plays every directory, hello too, by a fake clock; a witness made at RUN counts the program alone.
- T-shot is added: `--entry` gives no governor numbers today, and D5's evidence needs them per entry at 128x64.
- Run scripts end in `.sh` and are run by `sh <script>` (no executable bit needed; `run_command` adds `exec`).

## Questions for the owner (decisions.md Q85 to Q88, defaulted)
Q-a endoh3's `prog.c`; Q-b imc's six views kept; Q-c thadgavin at Z=30; Q-d no fallback cast over 5 MB.

## Risks
- gcc 14.2 on the Pi (the early probe): all five build; warnings sloane 6, imc 12, thadgavin 7 (with the owner's
  libncurses-dev), endoh1 0, endoh3 0. Check (b) counts them again on the merged entries.
- endoh1's 26-line frame scrolls the pty by four rows each frame: a render between two 1 KB chunks can tear, and the
  top four rows of its 80x25 field are never seen. `rows` cannot reach 26; the sheet judges it.
- endoh3 runs cc under the run's limits (256 MB RLIMIT_AS, `show/pipeline.py:28`; `unshare -rn`); the fake-clock play
  ends before the first `sleep 5`, so no test proves it: the early probe (three generations, exit 0) and check (c) do.
- Four parallel full suites slow each other on the Mac, and another session works there (Q83): a suite over 420 s
  or a timing failure is measured once more before anything is decided on it.
