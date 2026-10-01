# Plan review: iteration 17, the strip's wrap (C54) and D5's slack

Plan: `docs/superpowers/plans/2026-10-01-it17-strip-wrap.md` at b60c4e2 (code head 9e3b8f0). One adversarial round,
fresh context. Every claim below was probed against the real code: a scratch copy of the tree (`git archive
b60c4e2`) with the plan's rule written into `show/state.py` from the plan's words alone, the plan's tests written
from its one-line descriptions, run on this Mac and in an arm64 Linux container with gcc 14.4 and dash.

Verdict: **APPROVED**

## Blocking findings

None. Every value the plan states came out of the rule as written, every test it calls green stayed green with the
rule applied, every new test passed and can fail, and the two changed asserts stop at least what they stopped.

## Noted, not blocking

1. **Line 195 cannot catch a pipeline failure, before or after the change.** It runs only after line 194's
   `player.failure is None` has passed, so `_fail` never ran in that play and no banner of its own can be on the
   screen. Today the line can fail only on a program's or a source's stars; after the change it can fail only if a
   program prints a banner's exact text. The plan's "it stops every failure it stops today" is true, but only
   trivially so. The four-case test is what shows `banners` reads each banner. The journal can say this plainly;
   Q94's default stands.
2. **The strip at 128x64, through the real renderer and governor (FPS 20, as `tests/test_wall.py`).** The rate is
   unchanged: one change every 3 s, with held_ticks 0, flash_area 0 and square_flashes 0 for today's cycle, the
   plan's cycle and sloane's. One transition can change a few more cells than today: `Gavin Buttimore and` ->
   `Thaddaeus Frogley,` changes 254 pixels, against today's worst of 229 (`Gavin Buttimore and T` <-> `Not A.I.`).
   Fewer pixels rise, though: 177 at most, against 190 today. "Never wider than today's text" holds. Under rule 4
   this is not a safety slice, and nothing here argues for one.
3. **A full-screen entry would show the pieces out of order.** No entry is full-screen today (README: "used by
   none"). `strip_visible`'s 2 s in every 10 s, set against a 12 s cycle, would show pieces 0, 3, 2, 1 and so on.
   Not for it17 (Q82). At most one line in the journal.
4. **`test_short_strip_keeps_a_fitting_attribution_in_two_texts`.** The plan writes the expected text as
   `<author>, <year>`. Literal strings (`Andy Sloane, 2006`, `Ian Collier, 1992`, `Yusuke Endoh, 2012`, `Yusuke
   Endoh, 2020`, `Trey, 2026`) would keep the test from restating the code's f-string. Either form fails a cycle of
   three or four texts.
5. **The crash case's margin is ample.** The crash is seen at the first RUN tick: 0.2 of the 5.0 fake seconds
   before the cut, 15 of 15 runs. The default `run_seconds=5.0` needs no change.
6. **Time.** T-stars took 2.1 s on the Mac and 1.7 s in the Linux container, so the plan's 6 s is generous.
   T-strip: all of `tests/test_state.py` ran in 0.23 s.
7. **The sheets drift.** In it16's sheet the cell times drift: the 40th cell is at 41.0 s. Past the first 13 s,
   read thadgavin's pieces as `(t - press) // 3 % 4`, not by the plan's whole seconds. The plan already says
   "about", and it lists times only up to 13 s.
8. **`wrap_words` at width 0** returns empty pieces. That width cannot occur on the wall (`strip_chars` is 21), and
   the plan states `width >= 1`.
9. **Commit trailer.** The plan's `Co-Authored-By: Claude Fable 5.1` does not match it16's implementer commits
   (`Claude Opus 5.5`) and leaves out the `Claude-Session` line. This is attribution, not correctness.

## Verified as the plan states

- **The wrap rule is complete and unambiguous.** Only one function can be written from it. Cutting a word before
  the join test gives the same result as cutting it after, since a word longer than the width never joins. Every
  stated value was reproduced:
  - thadgavin at 21: `Gavin Buttimore and` (19), `Thaddaeus Frogley,` (18), `2000`.
  - `Test Author, 2026` at 21 and at 17 gives one text; at 10 it gives `Test`, `Author,`, `2026`.
  - `a  b` at 4 is kept as it is.
  - `ab cd ef` at 5 gives `ab cd`, `ef`.
  - `Supercalifragilistic Smith, 1999` at 10 gives `Supercalif`, `Smith,`, `1999`.
  - `Ab Supercalifragilistic` at 10 gives `Ab`, `Supercalif`.
  - Property test: for all six real attributions at widths 1 to 45, every piece has 1 to `width` characters, and
    the words are kept wherever none is longer than the width.
  - Lengths: sloane 17, imc 17, endoh1 18, endoh3 18, hello 10. None of these entries is full-screen.
- **`Show`.**
  - `_begin` sets `_started` for a start from the queue too, and clears the notice.
  - A notice lasts `0 <= now - t < 2.0`.
  - `ink(fast_cfg)` gives 21 strip characters.
  - Every time/text pair of `test_short_strip_wraps_a_long_attribution` holds, float edges included: t0+2.9,
    t0+11.9, `QUEUED #1` to t0+14.9, and `Thaddaeus Frogley,` at t0+15.
  - So does `..._keeps_a_fitting_...` (3.0 and 7.0 the attribution, 4.0 and 10.0 `Not A.I.`).
  - So does the changed line 450 (3.0 `Test`, 4.0 `Author,`, 7.0 `2026`, 10.0 `Not A.I.`, 13.0 `Test`). It fails on
    today's code, and pins every text where the old line pinned two.
- **Stays green with the rule applied (scratch copy).**
  - `tests/test_state.py`: 35 passed, counting the 6 new tests and the changed line.
  - `tests/test_show_shot.py`, `tests/test_show_shot_governed.py`, `tests/test_show_shot_pages.py`,
    `tests/test_wall.py` and `tests/test_main.py`: 62 passed.
- **No caller is missed.**
  - `show/main.py:294` and `tools/show_shot.py:395` pass the text through.
  - `playing_strips` (`tools/show_shot.py:422-431`) plays hello (10 characters), so its two halves stay true.
  - `tools/show_soak.py` never reads the strip.
  - `tests/test_wall.py:200` has texts of its own.
  - The renderer has no cache keyed on the strip's text.
- **T-stars: `_fail` and the banner.**
  - `_fail` (`show/pipeline.py:254-258`) is the only writer of `***` in `show/` and `tools/`.
  - The call sites (:170, :172, :198, :274) write exactly the four texts.
  - A negative build code matches `-?\d+`, and `type(exc).__name__` matches `\w+`.
  - LNM puts the banner at column 0. Insert mode keeps it there.
  - pyte's UTF-8 stream ignores charset designations (`ESC ( 0`, SO), so the banner's letters are never
    translated. `.match` finds it in every case `startswith("***")` does.
- **The six T-stars tests, written from the plan, pass.**
  - On the Mac they take 2.1 s. In the arm64 Linux container (gcc 14.4, `/bin/sh` is dash) they take 1.7 s.
  - The phases, reasons and banners are as stated. The terminal-error case fails at BUILD's first pump.
  - The build-timeout case leaves no `sleep 30` behind.
- **imc's fifth view starts 8 of its rows with `***`.** This held on the Mac (clang, `-ffp-contract` on, off and
  fast, all giving the same bytes) and with gcc 14.4 on aarch64 Linux, whose output is byte-identical (sha1
  bb9c2830...). It held 20 of 20 plays on each.
- **`unshare -rn` and the crash case.** `unshare -rn sh -c 'kill -s KILL $$'` exits 137. unshare execs sh in place
  (pid 9, ppid 1), so the pty process gets the signal, as the plan's operator step 3 says.
- **Line 195 changed.** With the change, `tests/test_curated_entries.py` gives 19 passed.
- **Counts.** 6 + 6 = 12 new tests, giving 1806 passed, 3 skipped, 1809 collected. The lanes share no file and
  need no shared helper.
- **O2.** The facts the new README text rests on are true:
  - `entries/README.md` has lines 29-30 and 33 as the plan quotes them.
  - In `thadgavin.alt.c` the curses branch is the `#else`. `nodelay(stdscr,1)` is at :59, `getch()=='q'` at :60
    (`endwin(); exit(0)`), and `E()` is called at :97.
  - In `show/` nothing writes to the pty master (no `os.write`); `terminal.py` only reads it.
  - endoh1 reads `< endoh1.c`. No other curated source reads the terminal.
- **Owner's questions.** Q91 (the wrap), Q94 (the pattern kept in the test) and Q95 (the README's strip line) are
  in decisions.md. The cut of an over-long word is roadmap note (3). The plan decides nothing else that is the
  owner's.

## Probes

All under `/private/tmp/it17-plan-review/`. The checkout's `git status --porcelain` showed only
`docs/superpowers/workflow/state.md`, which this review did not touch.

- `repo/`: `git archive b60c4e2`, with the rule in `show/state.py`, the plan's T-strip tests and the line-450
  change in `tests/test_state.py`, and line 195 changed in `tests/test_curated_entries.py`. It was run with
  `python -P` and `PYTHONPATH=repo`; `show.state.__file__` was checked to be the scratch copy. `base/` is the
  untouched export.
- `repo/tests/test_it17_stars_probe.py`: the six T-stars tests as the plan words them.
- `repo/tests/test_it17_imc_repeat_probe.py`: imc's fifth view, 20 plays.
- `repo/tests/test_it17_crash_margin_probe.py`: the crash case, 15 plays.
- `probes/strip_governor.py`: today's, the plan's and sloane's strip cycles through `renderer_for` and
  `GovernedDisplay` at 128x64 ink, FPS 20, measuring held_ticks, `flash_area`, `square_flashes`, and the pixels
  changed and rising at each transition.
- `imc/`: `imc.c` built with clang at three `-ffp-contract` settings, and with `docker run gcc:14`
  (aarch64, `--network none`).
- `linux-site/`: the venv's pure-Python packages (pytest, pyte, wcwidth). The stars probes were run in `gcc:14`
  with `--noconftest`.
- `docker run --privileged debian:trixie`: `unshare -rn` self-kill gives exit 137, with `$$` being the exec'd sh.
