# Iteration 17: orchestrator report

BASE f8bcc14 (checked before dispatch). Plan `docs/superpowers/plans/2026-10-01-it17-strip-wrap.md`. Head after
integration: 86f0607. Not pushed, not deployed. The Pi was not used.

## Completed
- T-strip (opus, worktree branch `worktree-agent-a83214534f36dbb85`, f99fad5), merged as 28a5036.
  - `show/state.py`: `wrap_words(text, width)` beside `strip_chars`, written to the plan's rules 1 and 2.
  - The short strip's playing branch now gives `wrap_words(f"{e.author}, {e.year}", w) + ["Not A.I."[:w]]`, indexed
    by `int((now - self._started) // ALTERNATE_S) % len(texts)`. It adds no constant and no `Show` attribute.
  - `tests/test_state.py` has the plan's six new tests:
    - `test_wrap_words_keeps_a_text_that_fits_whole`
    - `test_wrap_words_breaks_greedily_at_spaces`
    - `test_wrap_words_cuts_a_word_longer_than_the_width`
    - `test_wrap_words_pieces_fit_and_keep_the_words`
    - `test_short_strip_wraps_a_long_attribution`
    - `test_short_strip_keeps_a_fitting_attribution_in_two_texts`, with literal expected strings as review note 4
      asks (`Andy Sloane, 2006`, `Ian Collier, 1992`, `Yusuke Endoh, 2012`, `Yusuke Endoh, 2020`, `Trey, 2026`).
  - The old line 450 of `test_short_strip_cuts_each_part_to_the_width` now pins `Test` at 3.0, `Author,` at 4.0,
    `2026` at 7.0, `Not A.I.` at 10.0 and `Test` at 13.0 (two lines). Lines 444 to 449 and the test's name are
    unchanged.
  - Red first: the `wrap_words` tests failed on the missing function, the old line 450 on `'Test Autho'`, and
    thadgavin's test on `'Gavin Buttimore and T'`.
- T-stars (sonnet, worktree branch `worktree-agent-a299e61dc32093970`, 40018e3), merged as 7283d11.
  - `tests/test_curated_entries.py` has `BANNER` exactly as the plan writes it, and `banners(lines)` built on
    `.match`.
  - `test_entry_plays_through`'s old line 195 is now `assert banners(player.term.screen.display) == [], screen`.
    `player.failure is None` and `rec.phases == HAPPY` stay.
  - The new tests:
    - `test_banners_tell_the_pipeline_from_stars`
    - `test_a_program_that_draws_stars_plays_through` (`needs_cc`)
    - `test_a_failed_play_is_still_caught`, with cases `build-failed`, `build-timeout`, `crash` and
      `terminal-error`
  - The implementer confirmed the premise: imc's fifth view starts display rows with `***`. No `sleep 30` was left
    behind.
- O2 (orchestrator, main checkout), 86f0607.
  - `entries/README.md`, lines 29 to 30: "No entry waits on the terminal ...". thadgavin's poll is described there:
    `nodelay(stdscr,1)` and `getch()` at `thadgavin.alt.c:59-60`, called at :97, quitting on `q`. The show never
    writes to a run's terminal, so the poll finds nothing and the run goes on to the cut. The endoh1 sentence is
    kept.
  - Line 33 now adds the pieces sentence: an attribution over 21 characters is shown in pieces cut at spaces, three
    seconds each, before `Not A.I.` (thadgavin's three; C54, Q91).
  - Each fact was checked against the source before the edit:
    - `thadgavin.alt.c` lines 59, 60 and 97.
    - No `os.write` anywhere in `show/`; `show/terminal.py` only `os.read`s the pty.
    - endoh1 runs `./prog < endoh1.c`.
  - No test reads `entries/README.md`. The commit was made by name with the plan's subject.
- No review agent was run (rule 4). I read both branch diffs before merging. Each matches its section of the plan,
  and neither touches a file outside its owner list.

## Deviations
1. **Commit trailers.** The implementers' commits carry their own model's trailer plus the `Claude-Session:` line:
   `Claude Opus 5.5` on f99fad5 and `Claude Sonnet 5.5` on 40018e3. The merges and O2 carry `Claude Opus 5.5` and
   `Claude-Session:`. The plan's Global Constraints say `Co-Authored-By: Claude Fable 5.1`. This follows it16's
   implementer commits and the session's attribution instruction, as the plan review flagged (note 9). Attribution
   only.
2. **T-strip added `ROOT`.** It added `ROOT = Path(__file__).resolve().parents[1]` (and `from pathlib import Path`)
   to `tests/test_state.py`, which had no `ROOT`. The plan's tests use `ROOT / "entries" / ...`. It is the same line
   the other test files use, in an owned file.
3. **T-strip's checks beyond the plan.** In `test_wrap_words_pieces_fit_and_keep_the_words`, every result must be
   non-empty and at least six entries must load, so the test cannot pass on an empty list. This strengthens the
   test and changes no planned value.
4. **T-stars' new import.** It imports `HELLO_C, write_entry` from `tests.show_helpers`. The plan names that helper
   as "imported, not edited"; it was not edited.
5. **The worktree's extra skip.** It is reported at `tests/arcade/test_pose_mediapipe.py:303`, not the plan's
   `:223`. The reason is the same (the pose model is not in git). Each worktree's full suite read 1799 passed and
   4 skipped (1803 collected), which is the base's 1793 + 4 skipped in a worktree, plus 6. My dispatch note's
   "about 1800 passed" miscounted by one; the implementers' counts are right.
6. **How the first post-merge suite ran.** It ran from the main checkout's root with `--rootdir=/Users/trey/dev/codeisart`
   and the absolute `tests` path added to the plan's command. It collected the same 1803. The second (final) run used
   the plan's command exactly.
- Nothing was reverted, sent back, cut or skipped. No timing failure, and no suite over 420 s.

## Test status (command + counts)
The command, from `/Users/trey/dev/codeisart`:

`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs`

| Run | Result | Time |
|---|---|---|
| After the T-strip merge (28a5036) | 1800 passed, 3 skipped (1803) | 336.59 s |
| After the T-stars merge (7283d11) | **1806 passed, 3 skipped** | 327.50 s |
| `--collect-only` at 7283d11 | 1809 tests collected | |
| T-strip worktree, full suite | 1799 passed, 4 skipped | 349.98 s |
| T-stars worktree, full suite | 1799 passed, 4 skipped | 339.67 s |

- The 3 skips in the main checkout are the known ones: `tests/test_colorlight_child.py:142`,
  `tests/test_colorlight_slot.py:105` and `tests/test_sandbox.py:153`.
- After the T-stars merge the result matches the plan's expected 1806 passed, 3 skipped, 1809 collected, under the
  420 s limit.
- O2 changed only `entries/README.md`, which no test reads, so the suite was not run again after 86f0607.

## Commits (sha + subject)
| sha | subject |
|---|---|
| f99fad5 | feat(show): the short strip wraps a long attribution in pieces (it17 T-strip, C54) |
| 40018e3 | test(entries): the banner check reads the pipeline's banner, not a program's stars (it17 T-stars) |
| 28a5036 | merge: it17 T-strip, the short strip wraps a long attribution in pieces (C54) |
| 7283d11 | merge: it17 T-stars, the banner check reads the pipeline's banner, not a program's stars |
| 86f0607 | docs(entries): thadgavin polls the terminal; the strip's pieces (it17 O2) |

`docs/superpowers/workflow/state.md` is still modified and uncommitted (the operator's; not touched).

## Minutes (serial lane, parallel tasks, integration)
- Serial lane: 0 (none in this plan).
- Parallel tasks: 10.5 wall-clock minutes, both spawned in one message. T-strip took 9.8 min, T-stars 7.0 min.
- Integration: 12.0 min (two merges, two full suites of about 5.5 min each, O2, the report).
- Total: about 22.5 min, from dispatch at f8bcc14 to 86f0607.
