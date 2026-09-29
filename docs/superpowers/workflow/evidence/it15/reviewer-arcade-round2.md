## Verdict: BLOCKED

B1 is lifted: c99d463 does what the operator's rulings (1) to (4) ask, and every run below confirms it.

It is BLOCKED on one new finding, N1. When player 1 leaves, a different body can step into seat a and take over player 1's rounds, and the game then records a best that holds rounds the new body never played. This is the same kind of wrong result as B1, reached by another input. The fix did not cause it (it happens at 01bfd95 too), and it sits next to ruling (3). If the operator accepts it as the price of ruling (3), N1 can be carried and the verdict becomes APPROVED.

## B1 (lifted or not, the runs)

**Lifted.** Every run was on c99d463, through the real runner unless it says otherwise. Probes are in `.../scratchpad/it15-review-arcade/`.

| check | input | result |
|---|---|---|
| B1's probe, extended to 10 seeds (`probe_r2_leave.py`) | good bot, 2 rounds won, leaves in `result`, never back | 10/10 end by the leave rule at 2-1. best None, `left` never rises while gone, `cpu` "right" |
| leave in `ready`, 5 seeds | same | 5/5 at 2-1, best None, `left` never rises |
| leave in WAIT, 5 seeds | same | 5/5 at 2-1, best None |
| leave right at the signal, 5 seeds | same | 5/5 at 2-2 (the CPU in seat b wins the round in play), best None, `left` never rises |
| leave in `over` after winning 3, 3 seeds | same | 3/3: best 3.0, earned while present |
| back inside the grace (0.15 s), 5 seeds | 1 round, leaves in `result` | 5/5 at 3-0, best 3.0 (all rounds played) |
| back after the grace (3 s), 5 seeds | same | 5/5 at 3-1: the CPU in seat b won one round, `left` never rose while gone. best 3.0, all three won by the player while present |
| leave in WAIT, back after 3 s, 3 seeds | 1 round | 3-0 or 3-1, best 3.0, `left` never rose while gone |
| launch with nobody in view (`probe_r2_nobody.py`) | `nobody()` | seat a is empty. The CPU in seat b wins round 1 (0-1). The runner ends the session at 7.97 s (the leave rule). 1 flash, best None |
| duel, player 1 leaves at 8 s, 3 seeds (`probe_r2_duel.py`, game driven directly) | two bodies drawing 0.30 s and 0.40 s after DRAW | 1-3: player 2 wins in seat b, `left` never rises while player 1 is gone, best None |
| duel, player 2 leaves at 8 s, 3 seeds | same | 3-0: seat b goes to the CPU (`cpu` "right") as before, best None |
| duel, nobody leaves | same | 3-0, best None |

**Nothing broke:**
- 16 selected tests in `test_quickdraw.py` pass. They cover the 3 new tests, the still body under noise, `idle_body`, TOO SOON, the hint, the leave and second-player tests, the duel, the void round, the first draw, `good_beats_lazy_beats_nobody` and the round length.
- The orchestrator's feel row matches the one before the fix. Pre-fix: win_good 1.0, win_lazy 0.45, round_seconds 20.98, fidelity 0.989, range 0.635, square_flashes 2.0, flash_area_raw 0.0. Post-fix: failures [], win_good 1.0, win_lazy 0.45, win_none 0.0, fidelity 0.9891, range 0.6349, square_flashes 2.0, flash_area_raw 0.0, round_seconds 20.98, phases_reached 1.0.

**Flash spacing:**
- The shortest gap in all runs above is 4.77 s.
- An empty seat a cannot make rounds end sooner:
  - The CPU in seat b still draws at 0.25 s or later.
  - A void by DRAW_TIMEOUT still takes 1.5 s, then READY 1.0 s, then WAIT 2.0 s.
  - A TOO SOON against an empty seat a is a void with no flash.
- The floor stays at 4.5 s: at most one full-field flash in any 4.5 s. The governor held 0 ticks.

**The three new tests:**
- On 01bfd95's `quickdraw.py`, loaded in memory by `run_new_tests_on_old.py`, all 3 fail:
  - (a) `(1057892440, (3.0, 3.0, 3, 0))`: `3 == 2`.
  - (b) `left` 2 at 8.1 s: `2 == 1`.
  - (c) hint pixels `(227, 107, 0)` in the time's rows.
- On c99d463 all 3 pass.
- `git diff 01bfd95..c99d463 -- tests/` removes only import lines. No assert was removed or changed.

**The hint in `result`** (`probe_r2_hint.py`, `idle_body`, 40 s, the hint's rows drawn every tick):

| phase | ticks | with hint pixels |
|---|---|---|
| ready | 89 | 60 |
| play | 292 | 262 |
| result | 135 | 0 |
| over | 76 | 0 |

## New findings (or "none")

**N1. Another body that steps into seat a takes over player 1's rounds, and the game banks them as its best.**
- Where: `quickdraw.py` `_assign`, which gives the empty seat a to any unseated `sensed.player`. The seat keeps its `rounds`. Then `_finish` records `a.rounds`, because `_drew` is still set from player 1.
- Input: player 1 (id 1) wins 2 rounds, then leaves during `result`. Two seconds later the next person in the queue (id 7) steps into the same spot and plays like the good bot. `probe_r2_stranger.py`, through the real runner, 3 seeds:

| seed | id 7 seated in a at (s, left) | end | final | best | SessionResult |
|---|---|---|---|---|---|
| 1057892440 | 18.07, 2 | 25.77 (done) | 3-1 | **3.0** | score 3.0, players 1 |
| 1208555726 | 17.07, 2 | 25.43 (done) | 3-1 | **3.0** | score 3.0, players 1 |
| 3506456948 | 22.90, 2 | 31.57 (done) | 3-1 | **3.0** | score 3.0, players 1 |

- Result: the stored best is 3, but the body that finished the match won only 1 round. The newcomer's presence keeps the session alive, so the runner's leave rule never ends it.
- Why it blocks: a reproduced wrong result, 3 seeds of 3, from an input a queue at the wall will produce. It is the same kind of fault as B1: the best holds rounds the player in the seat did not win.
- Why the operator decides: the tracker gives a returning player a new id too (the fix's own test (b) uses id 3), so the game cannot tell "back after the grace" from "someone else". Ruling (3) keeps the rounds for a player who returns, and that is exactly what hands them to a stranger.
- A fix that keeps rulings (1) to (3): record nothing, as `_duel` already does, for a match in which more than one body id sat in seat a. A player who returns still plays on with their rounds but banks no best.
- This behaviour also exists at 01bfd95, so c99d463 did not introduce it. I missed it in round 1.

## Notes (not blocking)

- The hint disappears in one tick at the start of `result`, instead of fading. It is 1x text on about 3 percent of the wall, so the flash rule holds (held 0).
- An empty seat a is drawn in player 1's amber, at the bottom, with its rounds, so the wall shows a "ghost" seat until the leave rule ends the session. This is harmless.
- A returning player (or a newcomer) regains seat a only at a `_to_ready`. After a void round they wait one round more (`_to_ready_void` skips `_assign`, my round-1 note, not fixed under ruling 5), and meanwhile the CPU in seat b can take a round.
- In a duel where player 1 is gone but the seat is not yet released (the same round), player 2's TOO SOON gives seat a the round. `a.rounds` rises while player 1 is absent. A duel records no best, so only the session's score is off, by at most 1 round.
- My round-1 notes (`_flashed`, `_winner`, the dropout that arms the bar, the hanging hand without hips, the DRAW flash's pushed APL 0.502) stand, as ruling 5 says.
- `git status` is the same as at the start. The run on old code loaded 01bfd95's file from my scratch folder, in memory only, with `-B`.

## Minutes

10:52 to 10:56 by `date`, about 5 minutes. The probes and their `.txt` outputs are:
- `probe_r2_leave.py`
- `probe_r2_duel.py`
- `probe_r2_nobody.py`
- `probe_r2_hint.py`
- `probe_r2_stranger.py`
- `run_new_tests_on_old.py` (with `quickdraw_01bfd95.py`)
