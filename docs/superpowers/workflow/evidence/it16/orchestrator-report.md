## Completed
- **O1:** `.gitignore` gained `!entries/*/*.sh`, `!entries/*/LICENSE.md` and `entries/endoh3/clock.c`. `check-ignore` printed only `entries/endoh3/clock.c` and `entries/x/prog`. Commit b8346cc is the BASE.
- **T-rows:** opus, main checkout. `Entry.rows`, `EntryPlayer.typing_rows` and `.rows`, `write_entry(rows=)`, and the plan's 7 tests (11 cases). Committed on main as 82ad36d.
- **T-curated:** opus, worktree. `tests/test_curated_entries.py`, proven on hello (`hello: 1.16 s real, peak 138, final 138`). Every assert was shown red on scratch entries. Merged as 8105d8b.
- **T-shot:** sonnet, worktree. `frames_from_session(..., entry_dir=)`, the "entry" session and `--governed`, with 2 tests. Merged as 6eda8df.
- **E-sloane** (station 1, merged 3d6e782): 8 Mac warnings (4 deprecated-non-prototype, 2 return-type, 1 shift-op-parentheses, 1 unsequenced).
- **E-imc** (station 2, merged d4d6dbc): 2 Mac warnings (implicit-int, deprecated-non-prototype). The six views each print 22 rows of 78 columns, ASCII. `tour.sh` exits 0 at 36.07 s and passes `dash -n`.
- **E-thadgavin** (station 3, merged 5809179): 2 Mac warnings (1 deprecated-non-prototype, 1 linker note on the alignment of `__DATA,__common`).
- **E-endoh1** (station 4, merged f8299af): 0 warnings. A frame is `ESC[1;1H` and 26 lines of at most 79 columns, ASCII.
- **E-endoh3** (station 5, merged 511fab8): KEPT. All three generations print 23 lines, 79 columns at most, ASCII. The entry's build gives 0 warnings; the loop's compile gives 2 `-Wstrict-prototypes` a generation.
- **Plays at 511fab8** (`-s`):

  | Entry | Real s | Peak | Final |
  |---|---|---|---|
  | sloane | 3.62 | 1795 | 1795 |
  | imc | 3.39 | 1716 | 1716 |
  | thadgavin | 3.10 | 1677 | 1634 |
  | endoh1 | 3.40 | 1424 | 1206 |
  | endoh3 | 3.37 | 807 | 807 |
  | hello | 1.16 | 138 | 138 |

- **O2:** `/Users/trey/dev/codeisart/entries/README.md` has the curation rules and one section per station, 1 to 6. Committed as 27a10bd before its test run.
- **Main is not pushed:** nothing is deployed and nothing of mine is running. The only uncommitted change is the operator's own `docs/superpowers/workflow/state.md`, which I left alone.
- **Worktrees:** seven implementer worktrees and their branches remain under `/Users/trey/dev/codeisart/.claude/worktrees/` (not removed).
- **Not done:** the operator's section ("after the review") was left out, as instructed.

## Deviations
1. **Commit trailers:** every commit carries the Opus 5.5 or Sonnet 5.5 line of its own session, not the plan's Fable 5.1 line (plan line 22), as the brief's rule says.
2. **E-endoh1's start:** the Agent tool is synchronous here, so the four agents of one message return together. E-endoh1 therefore started after all four had reported, not when the first one did.
3. **E-endoh1's first spawn was lost:**
   - The operator committed 5a8ec51 (its own docs and `scripts/operator/` only) on main at 01:28, between my merge and the spawn. The worktree was cut there, and the agent stopped on its base check.
   - Its unchanged worktree and branch were auto-removed when it ended. Resuming it by SendMessage moved its shell into the main checkout, so I sent it STOP.
   - It has now confirmed that it ran only read-only commands (`pwd`, `rev-parse`, `branch --show-current`, `ls`) and created, changed or started nothing. Main stayed clean.
   - A fresh E-endoh1 ran from 5809179, which already held sloane, imc and thadgavin, instead of the GROUP E base 6eda8df. About 4 minutes were lost.
4. **Background runs:** the merges of sloane, imc and thadgavin, each followed by the three files and set to stop at the first red, ran as a background script while E-endoh1 worked. The order and the checks were unchanged. The full suite after T-shot's merge also ran in the background, while the four E agents worked.
5. **Operator commits on main during the run:** 49aad79 and 5a8ec51. Neither touches it16's files.
6. **T-rows:**
   - The resize comes after `$ <run>` is fed and before the CastWriter and `term.run`, so the typed line stays at 23 rows.
   - GAP, not fixed: "pyte keeps content and cursor" holds only when the screen grows. When `rows` is below 23, pyte drops the top rows and leaves the cursor outside the screen. No it16 entry uses a value below 24; clamping the cursor is the owner's decision.
   - The renderer test uses the real font `fonts/5x7.bin`, because the conftest font draws only "A".
   - The 23-then-24 test types at 2000 characters a second so that SOURCE has ticks to check.
7. **T-curated:**
   - "No witness cell at x >= 80" is read as "no character drawn at x >= 80". pyte's erase lays blanks across all 160 columns, so a literal cell check fails hello. It is checked as text is drawn, which is stricter than once per tick.
   - Non-ASCII is checked the same way. The peak count includes the tick that ends RUN.
   - `player.failure is None` can never fail on its own: a failure goes through ERROR_HOLD, so the phases assert fails first.
   - Risk, not changed: hello does not exit by itself under the fake clock. It is cut at 10.2 fake seconds; on a Mac slow enough (about 60 ms a tick) it would finish and leave 11 lit cells, under the minimum of 100.
8. **The worktree's expected mediapipe skip** is at `tests/arcade/test_pose_mediapipe.py:303`, not `:223` (plan line 16).
9. **Test-first:** for sloane, `-k sloane` could not go red, because there is no sums parameter until `LICENSE.md` exists and the play was already green. thadgavin's red was `test_every_entry_but_hello_has_a_licence`. imc, endoh3 and endoh1 each had a real red run (missing `tour.sh`, `clock.sh` and `endoh1.c`).
10. **My brief's order was wrong:** I asked for "the three files green before the commit", but `tests/test_show_shot.py:153` and `:244` need `entries/` committed. The agents committed first and then ran them green, which is the plan's own order.
11. **Measured against the plan's numbers:**
    - endoh3's loop compile gives 2 warnings on the Mac, not the 3 pedantic ones the plan says.
    - imc's worst view took 0.0135 s on the loaded Mac, not under 0.01 s (best 0.004 to 0.008 s).
12. **Timing readings in the agents' worktree suites:** all on a loaded Mac, and the failing test each time was `test_tick_budget_with_the_governors_share[strobe-128x64]` (`tests/arcade/test_headless.py:237`).

    | Agent | Suite | Rerun alone |
    |---|---|---|
    | E-sloane | 472 s, the test failed | failed again |
    | E-thadgavin | 451 s, failed (median 0.61 against 0.5) | passed |
    | E-imc | 406 s, failed (0.512 ms against 0.5) | passed |
    | E-endoh3 | 421 s, failed (0.563 ms against 0.5) | passed |

    Measured once more with no agent of mine running (Q83): my final suite was clean at 327.7 s. Nothing was cut, reverted or skipped.
13. **My integration runs** used `-p no:cacheprovider`; the counts are unchanged.

## Test status (command + counts)
- After T-shot's merge, at 6eda8df, with four E agents running:
  - `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs -p no:cacheprovider`
  - 1779 passed, 4 skipped (the 4th is the sums test's empty set, as planned at that point), 407.22 s.
- After each entry merge, `tests/test_curated_entries.py tests/test_entries.py tests/test_show_shot.py`:

  | Merge | Passed | Seconds |
  |---|---|---|
  | sloane | 75 | 30.84 |
  | imc | 78 | 33.87 |
  | thadgavin | 81 | 36.92 |
  | endoh1 | 84 | 40.69 |
  | endoh3 | 87 | 43.30 |

- After the last merge, at 511fab8, with no agent running: the same full-suite command gave 1794 passed, 3 skipped, 327.73 s, exit 0. The count is 1762 + 11 (T-rows) + 2 (T-shot) + 19 (T-curated).
- After O2, at 27a10bd: `tests/test_curated_entries.py tests/test_show_shot.py` gave 39 passed, 36.47 s; `git status --porcelain entries` is empty.
- In the implementers' own worktrees, each full suite run once after its commit:

  | Task | Passed | Failed | Skipped | Seconds |
  |---|---|---|---|---|
  | T-rows | 1773 | 0 | 3 | 321.3 |
  | T-curated | 1765 | 0 | 5 | 320.3 |
  | T-shot | 1763 | 0 | 4 | 332 |
  | E-sloane | 1780 | 1 (timing) | 4 | 472 |
  | E-imc | 1780 | 1 (timing) | 4 | 406 |
  | E-thadgavin | 1780 | 1 (timing) | 4 | 451 |
  | E-endoh3 | 1780 | 1 (timing) | 4 | 421 |
  | E-endoh1 | 1790 | 0 | 4 | 335.6 |

## Commits (sha + subject)
- b8346cc chore(entries): track run scripts and licences, ignore endoh3's clock.c (it16 O1)
- 82ad36d feat(show): rows, an entry's pty rows from RUN on (it16 T-rows)
- 9673491 test(entries): the curated entries' checks, proven on hello (it16 T-curated)
- 8105d8b merge: it16 T-curated, the curated entries' checks
- 7cc294f feat(tools): show_shot --governed, the governor's numbers for one entry (it16 T-shot)
- 6eda8df merge: it16 T-shot, show_shot --governed
- 576a3d6 feat(entries): 2006/sloane on station 1 (it16)
- 3d6e782 merge: it16 E-sloane, 2006/sloane on station 1
- 17fc9b8 feat(entries): 1992/imc on station 2 (it16)
- d4d6dbc merge: it16 E-imc, 1992/imc on station 2
- a76b39e feat(entries): 2000/thadgavin on station 3 (it16)
- 5809179 merge: it16 E-thadgavin, 2000/thadgavin on station 3
- 1c213ca feat(entries): 2012/endoh1 on station 4 (it16)
- f8299af merge: it16 E-endoh1, 2012/endoh1 on station 4
- 95cf76d feat(entries): 2020/endoh3 on station 5 (it16)
- 511fab8 merge: it16 E-endoh3, 2020/endoh3 on station 5
- 27a10bd docs(entries): curation notes (it16 O2)
- The operator's own commits, also on main: 49aad79, 5a8ec51.

## Minutes (serial lane, parallel tasks, integration)
- **Wall clock:** 01:01 to 02:03, 62 minutes.
- **Serial lane:** O1 2 min (01:01 to 01:03); T-rows 10.7 min in the main checkout.
- **Parallel tasks:**

  | Group | Wall clock | Each task |
  |---|---|---|
  | GROUP 1 | 01:03 to 01:21, 18 min | T-curated 17.7, T-rows 10.7, T-shot 6.7 |
  | GROUP E | 01:25 to 01:39, 14 min | E-imc 13.6, E-endoh3 12.5, E-thadgavin 10.4, E-sloane 9.2 |
  | E-endoh1 | 01:46 to 01:54 | 7.4, after a lost first spawn (0.2 min plus about 4 min of recovery, 01:41 to 01:46) |

- **Integration, about 17 min of my own wall time:**
  - Merging T-curated and T-shot: 2 min. Their suite took 6.8 min in the background, overlapped with GROUP E.
  - Merging sloane, imc and thadgavin with their three-file runs: 2 min, overlapped with E-endoh1.
  - Merging endoh1 and endoh3 with their runs: 2.5 min.
  - The final full suite: 5.5 min.
  - O2: about 5 min (drafted during the waits, committed and tested 02:01 to 02:03).
