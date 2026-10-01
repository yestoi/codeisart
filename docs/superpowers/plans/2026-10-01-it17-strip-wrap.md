# Iteration 17: the strip's wrap (C54) and D5's slack
BASE: the operator's commit of this plan (code head at the plan: 9e3b8f0). Roadmap C54 (Q91) and the note "it17 (D5's
slack; from it16's review and sheets)" (1) to (5). Thin plan. NOT a safety slice (rule 4): `arcade/flash.py`,
`arcade/brightness.py`, `show/display/colorlight.py` and the runner's order of the limiter, the governor and the push
are not touched. The strip's text is drawn into the frame by the renderer and goes through the limiter and the
governor like every frame; it changes every `ALTERNATE_S` (3 s) as today, and a piece is never wider than today's text.

## Global Constraints
- Test command, from the root (a worktree's root in a worktree): `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
  /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs`. At 9e3b8f0: 1794 passed, 3 skipped, 1797 collected,
  327.61 s; limit 420 s (config.md "Suite time"). A worktree's extra skip `tests/arcade/test_pose_mediapipe.py:223`
  (model not in git) is expected. New items: T-strip 6 (under 1 s), T-stars 6 (about 6 s: one imc build and play,
  four failing plays); after both merges 1806 passed, 3 skipped, 1809 collected.
- Test-first; only your files; never `cd` (in a worktree plain git, one command a call); `git add` by name; no stash,
  push, or command over 10 minutes; `tmp_path`; children killed (`play()` stops the player in its `finally`);
  `skipif(shutil.which("cc") is None)` on a test that runs `cc`. Trailer `Co-Authored-By: Claude Fable 5.1
  <noreply@anthropic.com>`. No rulings: a gap is reported, not decided.
- No existing assert is removed or weakened. The two changes this plan makes to existing asserts are named below
  (`tests/test_state.py:450`, `tests/test_curated_entries.py:195`), with why each stops at least what it stopped.
- The wall is 128x64 (`show.poc.toml`, ink view, 21 strip characters; Q82). A new test that renders or governs frames
  does it at 128x64; no code, config, test or sheet for 512x192 or 512x128. Tests at the default `Config()` stay.

## Lanes
- GROUP 1, together from BASE, each `isolation: "worktree"`: T-strip (opus), T-stars (sonnet). They share no file.
- Merge order: T-strip, then T-stars; the full suite after each merge. Then O2 (orchestrator, main checkout).
- Owners. T-strip: `show/state.py`, `tests/test_state.py`. T-stars: `tests/test_curated_entries.py`. O2:
  `entries/README.md`. Nobody: `tools/show_shot.py`, `tests/test_show_shot.py`, `tests/test_show_shot_governed.py`,
  `tests/test_wall.py`, `tests/test_main.py`, `show/main.py`, `show/renderer.py`, `show/pipeline.py`,
  `tests/test_pipeline.py`, `tests/show_helpers.py` (imported, not edited), every `entries/<name>/`, `show.toml`,
  `show.poc.toml`, `deploy/`, the safety files.

## T-strip (opus): a long attribution in pieces (C54, Q91)
```
def wrap_words(text: str, width: int) -> list[str]   # show/state.py, beside strip_chars; pure; width >= 1
Show.strip(self, now: float) -> str                  # signature unchanged; only the short strip's playing
                                                     # branch (show/state.py:164-166) changes
```
No new constant and no new `Show` attribute: the pieces are made from `self._current` at each call.
The wrap rule, so two implementers write the same function:
1. `len(text) <= width`: `[text]`, the text as it is (its spaces kept).
2. Otherwise the words are `text.split()` (runs of whitespace separate words; no empty word). A word longer than
   `width` is cut to `word[:width]`; the rest of it is dropped, not carried on (roadmap note (3)). Greedy, in order:
   the first word opens a piece; each next word joins the open piece after one space when `len(piece) + 1 +
   len(word) <= width`, else the open piece is closed and the word opens the next. The last piece is closed. Every
   piece has 1 to `width` characters.
The short strip (`w < SHORT_BELOW`), an entry playing, no notice: the texts are `wrap_words(f"{e.author}, {e.year}",
w)` followed by `"Not A.I."[:w]`; the strip is `texts[int((now - self._started) // ALTERNATE_S) % len(texts)]`. An
attribution that fits gives two texts: today's strings at today's times. Unchanged: the notice (the whole strip, cut
to `w`), attract's short strip (`ATTRACT_SHORT`, counted from `_attract_t0`), the long strip (`w >= 40`),
`strip_visible`, `strip_chars`.

At 128x64 (w = 21), the six attributions of `entries/*/entry.toml` at 9e3b8f0 (the plan writer's probe):
- thadgavin, `Gavin Buttimore and Thaddaeus Frogley, 2000` (43): `Gavin Buttimore and` (19), `Thaddaeus Frogley,`
  (18), `2000`, then `Not A.I.`: a cycle of four texts, 12 s.
- sloane `Andy Sloane, 2006` (17), imc `Ian Collier, 1992` (17), endoh1 `Yusuke Endoh, 2012` (18), endoh3 `Yusuke
  Endoh, 2020` (18), hello `Trey, 2026` (10): one piece each, as today.

New tests, `tests/test_state.py`:
- `test_wrap_words_keeps_a_text_that_fits_whole`: `("Test Author, 2026", 21)` and `(..., 17)` give the one text;
  `("a  b", 4)` gives `["a  b"]` (a text that fits is not re-spaced).
- `test_wrap_words_breaks_greedily_at_spaces`: thadgavin's attribution at 21 gives the three pieces above; `("Test
  Author, 2026", 10)` gives `["Test", "Author,", "2026"]`; `("ab cd ef", 5)` gives `["ab cd", "ef"]` (a piece may
  fill the width exactly).
- `test_wrap_words_cuts_a_word_longer_than_the_width`: `("Supercalifragilistic Smith, 1999", 10)` gives
  `["Supercalif", "Smith,", "1999"]`; `("Ab Supercalifragilistic", 10)` gives `["Ab", "Supercalif"]`.
- `test_wrap_words_pieces_fit_and_keep_the_words`: for the six real attributions (`load_entry` of each `entries/`
  directory) at every width 1 to 45: each piece has 1 to `width` characters; where no word is longer than the width,
  `" ".join(pieces) == " ".join(text.split())`.
- `test_short_strip_wraps_a_long_attribution`: at `ink(fast_cfg)`, entries `{1: load(tmp_path, "a", 1), 3:
  load_entry(ROOT / "entries" / "thadgavin")}`; a plays, 3 is queued, a finishes at t0 = 10.0 and thadgavin starts
  from the queue (no notice). t0 and t0+2.9 `Gavin Buttimore and`; t0+3 `Thaddaeus Frogley,`; t0+6 `2000`; t0+9 and
  t0+11.9 `Not A.I.`; t0+12 `Gavin Buttimore and`; a press on station 1 at t0+13 shows `QUEUED #1` to t0+14.9, and
  t0+15 is `Thaddaeus Frogley,` (the cycle counts from the entry's start). Every text has at most 21 characters.
- `test_short_strip_keeps_a_fitting_attribution_in_two_texts` (one test, a loop): at `ink(fast_cfg)`, each of
  sloane, imc, endoh1, endoh3, hello (`load_entry` of the real directory) in its own `Show`, pressed at 1.0: 3.0 and
  7.0 `<author>, <year>`; 4.0 and 10.0 `Not A.I.` (a four-text cycle would give a piece at 7.0).
Changed existing assert:
- `test_short_strip_cuts_each_part_to_the_width` (`tests/test_state.py:443-450`): lines 444 to 449 stay (attract's
  halves are still cut: `PRESS A BU`, `ON ANY POR`; the notice `PLAYING`). Line 450, `show.strip(3.0) == "Test Autho"
  and show.strip(4.0) == "Not A.I."`, asserts the cut C54 removes: at 10 characters `Test Author, 2026` (17) now
  wraps. It becomes `strip(3.0) == "Test"`, `strip(4.0) == "Author,"`, `strip(7.0) == "2026"`, `strip(10.0) ==
  "Not A.I."`, `strip(13.0) == "Test"`: every text is pinned, more than before. The test keeps its name.
Stay green unchanged (every other strip assert, `Test Author, 2026` and `Trey, 2026` fit at 21): the rest of
`tests/test_state.py` (`test_short_strip_alternates_every_3_s` among them); in `tests/test_show_shot.py`
`test_strips_draw_three_looks` (both sizes); `tests/test_show_shot_governed.py`; `tests/test_wall.py` (its own texts);
`tests/test_main.py`. Callers: `show/main.py:294` (each frame) and `tools/show_shot.py:395` take the new texts as
they are; `playing_strips` (`tools/show_shot.py:422-431`, "first half"/"second half") plays hello, which fits at
every size, so its two halves stay true: no change to `tools/show_shot.py` or its tests.

## T-stars (sonnet): the banner check reads the pipeline's banner, not a program's stars
`_fail` (`show/pipeline.py:254-258`) is the only writer of the banner, `\n*** {reason} ***\n`, which starts its row
(LNM). Its reasons, from its four call sites: `build timed out` (:170), `build failed (exit <code>)` (:172; a build
killed by a signal gives a negative code), `crashed (signal <n>)` (:198), `terminal error (<exception class>)` (:274).
```
BANNER = re.compile(r"\*\*\* (build timed out|build failed \(exit -?\d+\)|crashed \(signal \d+\)"
                    r"|terminal error \(\w+\)) \*\*\*")
def banners(lines: list[str]) -> list[str]   # BANNER.match(line).group(0) for each line it matches, in order
```
`test_entry_plays_through`'s line 195 becomes `assert banners(player.term.screen.display) == [], screen`. `.match`,
not `fullmatch`: like `startswith`, it reads a row's start, so a banner over cells a program left on that row is
still found. Every banner today's check finds starts with one of the four texts, so it stops every failure it stops
today; it no longer refuses a program's, a source's or a build's row of stars, which is not a failure.
The three asserts: `player.failure is None` is the strongest (`_fail` sets it, only `start` clears it: no banner was
written). `rec.phases == HAPPY` proves the path (build exit 0, RUN ended without a crash, no ERROR_HOLD or FALLBACK).
The banner check is the visible side of the first; it sees only a failure without a fallback, whose `term.reset`
(`show/pipeline.py:213`) clears the screen. All three stay.
New tests, `tests/test_curated_entries.py`:
- `test_banners_tell_the_pipeline_from_stars` (no pty): `*** build timed out ***`, `*** build failed (exit 3) ***`,
  `*** build failed (exit -9) ***`, `*** crashed (signal 11) ***`, `*** terminal error (TypeError) ***`, and one of
  them followed by `  ** *`, are each found; imc's rows `"***      *** *  * *   ** *"`, `"*** *** *"`, `"*" * 78`,
  `"***"` and `"*** not a reason ***"` give `[]`.
- `test_a_program_that_draws_stars_plays_through` (needs cc): `entries/imc` copied to `tmp_path / "src" / "imc"`,
  its `run` line set to `./prog -text -size 78 22 -limit 256 2>/dev/null` (tour.sh's fifth view,
  `entries/imc/tour.sh:16`), played by `play()`: phases HAPPY, `failure is None`, some display line starts `***` (the
  premise: today's check refuses this play; 8 of the view's 22 rows start so on the Mac), and `banners(...) == []`.
- `test_a_failed_play_is_still_caught[case]`, four cases, each a `write_entry` (`tests/show_helpers.py`, `HELLO_C`)
  under `tmp_path / "src"` (`play()` copies into `tmp_path / <slug>`), played by `play()`, no fallback:
  `build-failed` build `exit 3` -> `build failed (exit 3)`; `build-timeout` build `sleep 30`, `build_seconds=1.0` ->
  `build timed out`; `crash` build `true`, run `kill -s KILL $$` -> `crashed (signal 9)`; `terminal-error` build
  `true`, `monkeypatch.setattr(Terminal, "pump", <raises RuntimeError>)` -> `terminal error (RuntimeError)` (BUILD's
  first pump). Each: `Phase.ERROR_HOLD in rec.phases`; `player.failure` is that reason; `banners(display) ==
  [f"*** {player.failure} ***"]`; some display line starts `***` (today's check catches it too). None runs `cc`.

## O2 (orchestrator, after both merges): `entries/README.md`
- Lines 29 to 30 ("No entry reads the terminal, ...") become: no entry waits on the terminal, needs raw modes or X11,
  or animates at character scale; large motion is preferred (core plan, Task 19). thadgavin (curses) polls it:
  `nodelay(stdscr,1)` and a `getch()` each frame (`thadgavin.alt.c:59-60`, called at :97), which ends the program on
  `q`; the show never writes to a run's terminal (`show/terminal.py` only reads the pty), so the poll finds nothing
  and the run goes on to the pipeline's cut. endoh1 reads stdin from a file of its own directory, never the terminal.
- Line 33 ("the strip shows "<author>, <year>"") adds: an attribution longer than the strip's 21 characters is shown
  in pieces cut at spaces, each three seconds, before `Not A.I.` (thadgavin's three; C54, Q91).
No source is touched. Commit `docs(entries): thadgavin polls the terminal; the strip's pieces (it17 O2)`.

## Operator, after the review (inline, not implementers); E = `docs/superpowers/workflow/evidence/it17`
1. Sheets at 128x64 only, on the Mac, from a clean detached checkout of the code head (it16's way,
   `evidence/it16/verify-script.py.txt`; `git status --porcelain` clean before and after): `python -m tools.show_shot
   --entry entries/<name> --governed --config show.poc.toml --seconds 70 --every-ms 1000 --look led --out
   E/it17-<name>` for thadgavin and sloane. thadgavin's printed strip column (press at 1.0 s): `PLAYING` to about 2.9 s,
   `Gavin Buttimore and` at 3 s, `Thaddaeus Frogley,` 4 to 6 s, `2000` 7 to 9 s, `Not A.I.` 10 to 12 s, `Gavin
   Buttimore and` again from 13 s; the sheet's strip rows show the same texts whole. sloane's: `PLAYING`, then `Andy
   Sloane, 2006` and `Not A.I.` in turn every 3 s, as in `evidence/it16/show-shot.txt`. Each `held area squares` line
   is written beside it16's for the same entry; a difference is reported, not judged here.
2. The full suite in the main checkout: 1806 passed, 3 skipped, 1809 collected expected, under 420 s.
3. The Pi 5, by the operator, it16's recipe (plan it16, "Operator" 3: the script file, the literal T
   `/tmp/it17-operator`, `flock -w 300 /tmp/pi5.lock`, nothing kept): `tests/test_curated_entries.py
   tests/test_state.py tests/test_pipeline.py tests/test_sandbox.py tests/test_entries.py`. New there: the crash case
   under `unshare -rn` (unshare execs `sh`, so the signal is the pty process's), imc's fifth view built by gcc 14.

## Decisions taken (the owner's questions go to decisions.md from Q94)
- Greedy wrap at spaces, an over-long word cut and its rest dropped, `Not A.I.` last, 3 s a text, counted from the
  entry's start (Q91, note (3)); `wrap_words` pure, nothing cached. `tests/test_state.py:450` changes (above).
- The banner check holds the four texts `_fail` writes today in the test, not in `show/pipeline.py` (Q94); a fifth
  reason added later is still stopped by `player.failure is None`. O2 also corrects the README's strip line (Q95).

## Risks
- imc's view 5 by gcc 14 on the Pi may shade the set's edge differently; its `***` rows lie in the set's body, and if
  none were left the premise assert fails loudly (the test never passes vacuously).
- Two parallel suites slow each other, and another session works on the Mac (Q83): a suite over 420 s or a timing
  failure is measured once more before anything is decided on it.
