## Verdict: APPROVED

## Blocking findings (file:line, the input, what happens, why it blocks)
None.

What I checked, so the lead can see what "none" covers (all on this Mac, b4ff165..27a10bd; HEAD 0192f00 has the same code):
- Asserts: `git diff b4ff165..27a10bd -- tests/` removes one line, `tests/show_helpers.py` `year: int = 2026) -> Path:` (the signature gains `rows`). No `assert` is removed or changed.
- Counts: `pytest --collect-only -q | tail -1` gives 1765 at b4ff165 (a `git archive` copy) and 1797 at HEAD (+32: 6 entries, 4 pipeline, 1 renderer, 19 curated, 2 show_shot). Full suite at HEAD: `1794 passed, 3 skipped in 328.84s`, exit 0. The 3 skips are the baseline's (colorlight /proc x2, sandbox unshare).
- Sources: all 8 published `.c` files are byte-identical (`cmp`) to SRC. Their sha256 equal the LICENSE.md sums, SRC/SHA256SUMS and the committed blobs at 27a10bd. imc.c keeps its 166 tabs; there is no CR anywhere and no `.gitattributes`.
- Builds: every build has `-Wall` and `-fsigned-char`; none has `-w`, `-Werror` or `-fpermissive`. Mac warnings: sloane 8, imc 2, thadgavin 2, endoh1 0, endoh3 0. endoh3 builds `prog.c`; endoh1 builds `endoh1.alt.c -DA=40` and runs `./prog < endoh1.c`; thadgavin runs `TERM=vt100 ./prog`; imc runs `sh tour.sh`.
- T-rows: I played a `rows = 24` entry, then a plain one, then attract through `Show` on one shared Terminal at show.poc.toml (`/private/tmp/it16-review-scratch/next_after_24.py`). Each stage gave these `(term.rows, screen.lines)` and `stty size` values:
  - tall: SOURCE/BUILD (23,23); RUN/DWELL (24,24), "24 80".
  - plain: every phase (23,23), "23 80".
  - attract: (23,23).
  - Growing 23 to 24 keeps the content and the cursor (pyte `resize` only adds a row). The renderer draws `min(23, 24)` rows, so row 24 stays under the strip. `_fail`'s `\n*** ... ***\n` always ends at row 23 or above.
- Real-time plays: all five ran through `EntryPlayer` on the real clock at show.poc.toml (`realtime_play.py`).
  - Phases were SOURCE, BUILD, RUN, DWELL, DONE, with no failure.
  - No REP, no byte >= 128, no SO. thadgavin sends `ESC)0`, which pyte ignores in UTF-8 mode.
  - The process group was empty 0.3 s after `stop()`.
  - sloane's and endoh3's cursor parks on row 24 without scrolling. imc steps through its six views (1716, 1089, 1684, 249, 469, 471 lit).
- Run scripts under `/bin/dash`:
  - `tour.sh` exits 0 at 36.08 s.
  - `clock.sh` ran 3 generations in 13 s, widest line 79, ASCII; the group was empty after the SIGKILL.
- endoh3 cut rule over the clock face: 234 faked `__TIME__` values (`-U__TIME__ -D__TIME__=...`), three generations each, with the loop's flags. All 702 compiles succeeded; every output was 23 lines, at most 79 columns, ASCII.
- T-curated is falsifiable: I fed `test_entry_plays_through` broken copies, and an assert stopped each one:
  - missing script and `exit 1`: the cut assert (RUN ended at 0.2 fake s);
  - endoh1 fed `endoh1.alt.c`: final 40 < 100;
  - imc then clear: final 0;
  - an 81-column row: past_wall;
  - UTF-8 output: non_ascii;
  - `ESC[5b`: the REP assert.
  A fallback cannot pass, because the phases must equal HAPPY.
- Safety: the range does not touch the display path, the governor, the limiter or brightness. `--governed` runs `ShowLoop` on a `FakeDisplay` behind `GovernedDisplay`.
- `.gitignore`: `check-ignore` ignores `entries/endoh3/clock.c`, `clock`, `prog` and `fallback.cast.part`, but not `*.sh` or `LICENSE.md`. `git status --porcelain entries` is empty.

## Noted, not carried (one line each)
- `scripts/operator/guard_bash.py:143` checks only `rest[0]`, but ssh appends every later argument to the remote command. `ssh trey@codeisart.local 'flock -w 300 /tmp/pi5.lock true' '; reboot'` gets exit 0 from the guard (probe `/private/tmp/it16-review-scratch/guard_probe.py`), and `reboot` would run outside the lock.
- At 128x64, thadgavin's strip reads "Gavin Buttimore and T" (Q58 cuts it to 21 characters), so the second author and the year never reach the wall. The README's "the strip shows <author>, <year>" holds for the other four entries only.
- `tests/test_curated_entries.py:195` (no screen line starts `***`) also reads the program's own cells. imc's views 5 and 6 and its default view start rows with `***`. The fake-clock play reaches only view 1, so the entry passes today.
- thadgavin's `E()` calls `getch()` (non-blocking) every frame (`thadgavin.alt.c:60`), so `entries/README.md:29` "No entry reads the terminal" is not literally true. It is harmless, because nothing writes to the pty master.
- `--session entry` is now a valid choice (`tools/show_shot.py:281`). Without `--entry` it ends in the ValueError at `:313`, a traceback rather than an argparse error.
- A `rows` value below 23 leaves pyte's cursor outside the shrunk screen (the orchestrator's deviation 6). No entry uses one.
- The fake-clock play sees only about 3 real s of each run (imc's view 1, endoh3's first clock), and the REP refusal can only fire on the Pi. The rest is covered by the real-time checks above and by pi-checks.md.
