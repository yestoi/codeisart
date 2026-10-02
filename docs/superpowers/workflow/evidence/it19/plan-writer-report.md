# it19 plan writer's report (2026-10-01)
Plan: `docs/superpowers/plans/2026-10-01-it19-four-pose-games.md`. Not committed. No code run but greps and reads.

## Read
config.md Loop rules 1 to 10 and the Orchestrator prompt; the it15 plan (form); spec 5, 7.6, 8 (rows copyme, flap,
swat, freeze), 8.1, 9.2, 9.3; roadmap M7a, Spec revision 4 notes, the it18, it08, it07, C24, it15 and it09 notes; the
game guide (all 330 lines); `arcade/bots.py` (whole), `arcade/poses.py`, `arcade/figure.py`, `arcade/input.py`
(Edge, Hold, Cursor, Glide), `arcade/sensed.py` (Body, reach, SKELETON, constants), `arcade/sources/actors.py`
(Person, degrade, _noisy), `arcade/feel.py` (_canonical, measure, judge), `arcade/feel_budgets.toml`, `arcade/game.py`
(players), `arcade/juice.py` (API, ECHOES), `arcade/flash.py` (concurrent_area, square_flashes),
`arcade/attract/lobby.py:45-52,175-190,240-256`, `arcade/games/__init__.py`, `arcade/games/dodge.py:1-130`, the
test names of `test_dodge.py`, `test_oracle.py:22-117`, `test_all_games.py:30-180`, `tests/arcade/helpers.py` names.

## Findings the plan had to settle (check these first in the adversarial review)
1. No bot could play Copy Me or Flap. `bots.Move` (`arcade/bots.py:40`) is one body with ONE wrist's height;
   `Person.wrist` (`actors.py:119`) moves a wrist vertically only (its x stays at the stand offset: reach u is 0.75
   for the right hand, 0.25 for the left, always). So a bot can neither flap with both arms nor strike a pose. The
   plan adds I0, the orchestrator's (rule 6: `arcade/bots.py` is a shared file, not an engine file): `Move.pose`
   (defaulted None, via `Person.pose`) and `hand="both"`. Two new tests in `tests/arcade/test_bots.py`; no existing
   assert moves (no test inspects `Move`'s fields; `_sensed` is called only in bots.py and test_quickdraw.py:365,440
   with today's Moves).
2. Every `score` game needs fidelity >= 0.8 and range >= 0.6 (`feel_budgets.toml`, `feel.py:344-352`) on one of
   cursor_x, cursor_y, zone_x, near, far, inside canonical's first 20 s (`FEEL_SECONDS`). Flap's flap has no axis:
   the plan gives Flap a wing gauge (hand height, Cursor then Glide) as its measured control. Copy Me's and Freeze's
   figures follow `zone_x` through `figure_rect` (the lobby's mirror), so they measure on zone_x and need the column
   backlash (it08 note). Swat's blade is zone_x plus the hand's reach (u, v): a bot's u is fixed, so the body's step
   is what moves a bot's blade across.
3. `GameInfo.players` is 1 or 2 (`arcade/game.py:89`): Freeze's "1 to many" is 1 or 2.
4. `exit_seconds` is 3.0 (`arcade/config.py:50`): a Freeze player frozen with both hands up for a 2.5 to 4 s red would
   end the session, so Freeze declares `exit_gesture=False` (as Copy Me must).
5. Spec 5 says games never difference keypoints; Flap ("wrist vertical velocity") and Freeze ("keypoint speed") are
   planned as crossings within a window and travel spans per capture, not per-tick differences.
6. The pose relay writes to `data_dir`; a game never saves or reads the config (guide 2): cut (Q104).
7. A standing body must match no Copy Me target, so only the limbs a target moves away from `stand` are judged.
8. The bots' noise is an independent draw per tick on x and wrist_y; Freeze's thresholds must sit above it, so its
   bots carry small noise (0.005 good, 0.02 lazy). The implementer tunes inside the bands.
9. Swat at 60 s (spec) is the costliest game (both bots play the whole round): about 38 s of suite; first to cut.
10. Canonical scripts cannot read the rng's draws (Copy Me's targets, Freeze's lights): the scripts cycle a rung's
    poses and alternate dance and hold, so the sheets show matches and outs on some rounds, not all.
11. Real bodies on 45-degree poses read about 8 degrees off the bots' (Person makes x offsets in frame-width units,
    the camera is 4:3); inside the 30-degree tolerance. For the owner's first play.

## Not settled by the plan
- Whether a still body under `degrade(**REAL_NOISE)` stays under Freeze's `MOVE_TRAVEL = 0.25` and Swat's
  `CUT_MIN_PX = 3`: estimated from `_noisy` (uniform +-0.01 per keypoint; reach u span up to about 0.1, v up to about
  0.15 at height 0.6). The plan lets each rise (Freeze to 0.3, Swat to 4), never fall.
- Copy Me's round_seconds (about 26 s) is near the 20 s floor, like Quick Draw's 20.98.
- The suite estimate (about 440 s) is from Dodge's 31 s per pose game, scaled by round length.

## Questions for the owner (the operator records them as Q104 and up; each default taken)
- Q104: Copy Me's pose relay (the round winner's pose saved to `data_dir` as a future target) is cut from it19: a game
  never saves or reads the config; it needs a runner-owned store. Default: cut, a later iteration.
- Q105: Copy Me takes 1 or 2; two copy the same target at once, each scored; bests for solo only. Default: yes.
- Q106: Freeze takes 1 or 2 (the protocol's limit), not "many". Solo survives 6 reds; a red scores only after a dance
  in the green before it (C41); an out ends a solo game. Default: yes.
- Q107: Freeze reads keypoint travel by body (wrists in the reach box, the hips' zone_x); no music, no motion grid
  (Q99, M5 unbuilt); the red light is a 1 px border and the word FREEZE (red area at most 0.12 of the wall), never a
  full-field colour. Default: yes.
- Q108: Flap needs both wrists, as the spec says; a one-armed flap does not count. Default: both.
- Q109: Flap shows a wing gauge (the hand's height and the two lines a flap crosses) at the left edge; a flap during
  `over` restarts, at most 3 runs a session. Default: yes.
- Q110: Swat's blade is the body's place on the mat plus the hand's reach, so a player steps to reach the far side.
  Default: yes.
- Q111: Swat keeps the spec's 60 s round (about 38 s of suite time); two players share one score and record nothing.
  Default: yes.
- Q112: `bots.Move` gains `pose` and `hand="both"` (orchestrator's I0 in a shared file). Default: yes.
- Q113: Copy Me judges only the limbs a target moves away from standing, so standing still matches nothing; legs only
  when seen. Default: yes.
