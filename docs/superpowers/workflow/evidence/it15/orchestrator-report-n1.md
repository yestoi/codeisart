## Completed
N1 fix (arcade review round 2), under the operator's rulings of 10:58, from BASE 44a9dd2 (checked):
- 77c11d4 (opus, serial in the main checkout): Quick Draw banks no best when seat a went to a body id other than the first one it held in the match.
  - `reset` adds `_first_a`, the first id seat a held, and the flag `_swapped`.
  - `_assign` records `_first_a` on seat a's first take and sets `_swapped` when a later take is another id.
  - `_finish` records only when `not self._duel and not self._swapped and self._drew`.
  - The rounds stay with the seat and play goes on. The module docstring gains one sentence.
  - Files: `arcade/games/quickdraw.py` and `tests/arcade/test_quickdraw.py` only.
- New tests:
  - `test_another_body_in_seat_a_after_the_grace_banks_no_best`: the probe's input through the real runner, on seeds 1057892440, 1208555726 and 3506456948. Seat a held ids [1, 7]; the stored best is None; the SessionResult has best None and new_best False. On 44a9dd2 it failed: `(1057892440, ([1, 7], 'over', 3, 1, 3.0, 3.0, ...)) assert 3.0 is None`.
  - `test_a_player_back_inside_the_grace_still_banks_their_best`: the same seeds, with player 1 out of view for 0.15 s (the grace is 0.55 s) and back as id 1. Seat a held [1]; left 3; best 3; new_best True. It is a guard that passes on 44a9dd2 by design (see Deviations).
- The probe after the fix: all three seeds end 3-1, reason done, players 1, stored best None, SessionResult score 3.0, best None, new_best False.
- Feel report for quickdraw (20 seeds): failures [].
  - The row is equal to the one before: win_good 1.0, win_lazy 0.45, win_none 0.0, fidelity 0.9891, range 0.6349, square_flashes 2.0, flash_area_raw 0.0, round_seconds 20.98, phases_reached 1.0.
  - The rest of the row: response_ticks 1.0, response_px 72.0, lit 0.0794, dim 0.0119, liveliness 0.0122, score_visible 0.9784, score_legible 1.0.
  - No band touched; Pong not touched.
- `git diff 0dae849 -- arcade/flash.py arcade/brightness.py show/display/colorlight.py arcade/runner.py` is empty.

## Deviations
- Changed asserts: none. The c99d463 test for a player back after the grace already ends with no best asserted, so it needed no change. The only removed test line is the `from arcade.games.quickdraw import (...)` line, re-added with `CAMERA_FPS`, plus a new import of `capture_grace`.
- The inside-the-grace test cannot fail on 44a9dd2, because ruling 2 keeps that behaviour. The implementer showed that it catches a wrong fix: a mutant, patched in memory only, that sets the flag on any tick player 1 is missing failed it with `(1057892440, ([1], 'over', 3, 0, None, False))`. The mutant script is scratchpad `n1_mutant.py`.
- Smallest readings:
  - "One new flag" also needs the first id stored, so `_first_a` sits beside `_swapped`.
  - The same id 1 retaking seat a after the grace still banks ("an id other than the first").
  - `_finish` still celebrates a solo win by whoever sits in seat a, a stranger included; the rulings are silent, so it is unchanged.
- The implementer's feel-report command began with a `cd` into the repo, against the no-`cd` rule. It only set the working directory and wrote nothing.
- The round 2 notes (the ghost seat, the wait after a void round, the duel's TOO SOON with player 1 gone) are not fixed, per ruling 5.
- The operator's working-tree files under `docs/superpowers/workflow/` (modified, and untracked evidence) were left alone and are not in the commit.

## Test status (command + counts)
- `tests/arcade/test_oracle.py -k quickdraw`: 2 passed, 3 deselected, 24.38 s.
- `tests/arcade/test_all_games.py -k quickdraw`: 8 passed, 8 deselected, 11.45 s.
- `tests/arcade/test_quickdraw.py` alone: 39 passed, 15.77 s. The two new tests add about 2.7 s (1.50 s and 1.20 s).
- Full suite, the implementer's run on 77c11d4: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs -p no:cacheprovider /Users/trey/dev/codeisart` gave 1312 passed, 1 skipped in 281.71 s. Load average was 1.77 2.17 2.52 before and 2.33 2.48 2.58 after. The skip is `tests/test_sandbox.py:153` (no unshare on macOS). This is under 330 s.

## Commits (sha + subject)
- 77c11d4 fix(arcade): Quick Draw banks no best when another body sat in seat a (it15 review N1)

HEAD is 77c11d4, on top of the operator's 44a9dd2. Nothing is pushed or deployed.

## Minutes (serial lane, parallel tasks, integration)
- The N1 fix, serial in the main checkout: 10:58 to 11:06, about 8 minutes, including the feel report, the `-k quickdraw` runs and the full suite.
- Verification by me (the commit, the diff, the frozen files, the removed lines): 11:06 to 11:07.
- No parallel tasks and no merges.
