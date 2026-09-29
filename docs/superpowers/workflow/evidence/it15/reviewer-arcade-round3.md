## Verdict: APPROVED

N1 is fixed. A match in which seat a changes body banks no best, and nothing else changed.

## N1 (lifted or not, the runs)

**Lifted.** Every run is on 77c11d4, through the real runner unless it says otherwise.

| check | input | result |
|---|---|---|
| `probe_r2_stranger.py` / `probe_r3_stranger.py`, 3 seeds | player 1 (id 1) wins 2 rounds, leaves in `result`; id 7 steps in 2 s later | 3/3: final 3-1, `scores.best()` None, SessionResult `best None, new_best False` (score 3.0, reason done) |
| the same, id 7 steps in 0.15 s later | a new id inside the grace | 3/3: 3-0, best None, `new_best False`. Seat a changes id at the next `ready`, so no best |
| leave in `over` after winning 3 (`probe_r2_leave.py`), 3 seeds | same id | 3/3: best 3.0, still banks |
| back inside the grace (0.15 s), 5 seeds | same id 1 | 5/5: 3-0, best 3.0, still banks |
| back after the grace (3 s), 5 seeds | **the same id 1** | 5/5: 3-1, best 3.0, still banks |
| leave in WAIT, back after 3 s, 3 seeds | same id 1 | best 3.0, still banks |
| every "leave, never back" row of round 2 (result 10, ready 5, WAIT 5, signal 5) | same | 25/25: best None, `left` never rises while gone |

About point 2: my round-2 probe's return uses the **same id 1** (the bots' `_sensed` has only id 1). Under Q78's smallest reading ("the same id 1 retaking seat a after the grace still banks"), those rows still bank. That is correct by the ruling, but it is not the "banks nothing" point 2 expected. The price of the ruling shows when the returner has a new id, as a real tracker gives after its drop time. That case is the stranger rows above: no best, and the rounds stay (`left` 2 carried to 3-1 or 3-0).

**The new test:**
- `test_another_body_in_seat_a_after_the_grace_banks_no_best` **fails** on 44a9dd2's `quickdraw.py`, loaded in memory by `run_r3_tests_on_old.py`. The failure: `(1057892440, ([1, 7], 'over', 3, 1, 3.0, 3.0, ...))`, `3.0 is None`.
- It **passes** on 77c11d4.
- `test_a_player_back_inside_the_grace_still_banks_their_best` passes on both. It is a guard, as intended.
- `git diff 44a9dd2..77c11d4 -- tests/` removes only one import line, which gains `CAMERA_FPS`. No assert was removed or changed.

**Nothing broke:**
- 13 selected Quick Draw tests pass: both new tests, B1's tests, the duel, `idle_body`, the still body under noise, `good_beats_lazy_beats_nobody`, first to three, and a lost match.
- Duel (`probe_r2_duel.py`, 3 seeds): the same as round 2. Nobody leaves: 3-0. Player 1 leaves: 1-3. Player 2 leaves: 3-0 with `cpu` "right". Best None in every case.
- A launch with nobody in view: the same as round 2. The CPU in seat b wins 0-1, the runner ends the session at 7.97 s, 1 flash, best None, 0 held ticks.
- Flash spacing: unchanged. The shortest gap in all runs is 4.77 s, the floor is still 4.5 s, and the fix touches no timing.

## New findings (or "none")

None.

## Notes

- Point 5, `_finish` celebrating a stranger: a stranger who finishes a 3-1 match in seat a gets `fx.celebrate` and a SessionResult score of 3.0, though they won only 1 round. The wall shows the seat's score and a win. That follows from Q78's "the rounds stay with the seat", and nothing is banked (best None, `new_best False`). So it is a note, not a finding.
- The SessionResult `score` (3.0) is the seat's rounds, not the body's. The lobby's end card shows it, with no best.
- My earlier notes stand under ruling 5.
- `git status` is unchanged by me. The pre-fix module ran from my scratch folder, in memory only, with `-B`.

## Minutes

11:07 to 11:09 by `date`, about 3 minutes. The probes and their outputs are in `.../scratchpad/it15-review-arcade/`:
- `probe_r3_stranger.py` (`.txt`)
- `probe_r2_stranger.py`, `probe_r2_duel.py`, `probe_r2_nobody.py` (`r3_*.txt`)
- `probe_r2_leave.py` (`r3_probe_r2_leave.txt`)
- `run_r3_tests_on_old.py` (`.txt`), with `quickdraw_44a9dd2.py`
