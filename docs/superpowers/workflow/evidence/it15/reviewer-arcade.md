## Verdict: BLOCKED

One blocking finding: in Quick Draw, a solo player who walks away mid-match can get a best they did not earn. The CPU takes player 1's seat (seat a) and wins a round in it, and the game records that round as player 1's. Everything else in lane A passes: the flash rule, the frozen files, the asserts and the count. Dodge (c49d902) has no blocker of its own; only the suite time kept it out.

## Blocking findings (file:line, the input, what happens, why it blocks)

**B1. Quick Draw gives player 1's seat to the CPU, and the CPU's rounds are recorded as player 1's best.**
- Where: `arcade/games/quickdraw.py:175` (`_release_stale()` runs on every `ready` tick, for seat a too). Then `:176` (`_hands_down()` is trivially True with no human). Then `:293-296` (`_finish` calls `scores.record(a.rounds)` when `_drew` is set, and `a.rounds` now holds the CPU's wins).
- Input: a solo player draws and wins 2 rounds, then leaves the camera's view during `result`. This is a player walking off, or the tracker losing them.
- What happens: at the next `ready`, seat a goes to the CPU, so both seats are CPUs. The CPUs play a round. If seat a's CPU wins before the runner's 8 s leave rule fires, `a.rounds` becomes 3, `_finish` records 3, and the SessionResult says `score=3.0, best=3.0, new_best=True`.
- Probe: `probe_qd_leave.py`, through the real runner with the good bot, 5 seeds (`zlib.crc32("quickdraw:128x64:i")`):

| seed | left at (s) | session ended (s) | final left-right | best stored | SessionResult |
|---|---|---|---|---|---|
| 1057892440 | 11.37 | 19.33 (left) | 3-0 | **3.0** | score 3.0, new_best True |
| 1208555726 | 9.47 | 17.43 (left) | 3-0 | **3.0** | score 3.0, new_best True |
| 3506456948 | 13.50 | 21.47 (left) | 2-1 | None | score 2.0 |
| 2785507810 | 12.73 | 20.70 (left) | 2-1 | None | score 2.0 |
| 946072641 | 9.73 | 17.70 (left) | 2-1 | None | score 2.0 |

- Why it blocks: this is a reproduced wrong result, 2 seeds of 5, from an input the code will meet. The score and the best (Q72: rounds won by player 1) include a round player 1 never played, while their body was not even in view. That breaks C41/C42 ("scores nothing and banks no best" without the player's movement). The same path credits CPU-won rounds to a player who is lost for longer than the grace and then comes back. Their seat's `rounds` are kept, plus whatever the CPU won in seat a.
- Fix (small): never hand seat a to the CPU. Player 1's leaving is the runner's to end. Or never count or record rounds won while seat a has no human.

## Lane A, the arcade: the seven points (one short answer each, with numbers)

1. **C47 (hips arriving late): passes.** Every case below is from `probe_engine.py`.
   - The plan's probe after E1: the paddle stays at 24.00 px before and after the hips arrive, with 0.000 px travel. `measured` goes False, then True.
   - The jump is neither travel nor `active`. `test_pong.py::test_a_still_body_born_without_hips_banks_nothing` passes.
   - Hips that flicker every capture: the value holds at 0.5000..0.5000 and the scale at 0.39, with no new centre. The tracker's `measured` stays True once set, and `Depth` arms only on its first capture after `reset()`.
   - A real step (x1.3) on the very capture the hips arrive is swallowed: the value stays at 0.500, where a body measured all along reads 0.928. The next step moves it as before (0.937). A real step spans several captures, so only one capture's share is lost. This is the design (Q75).
2. **C46 (torso without hips): passes, with one limit.**
   - Without hips, `torso`, the reach box's width fallback and `raise_line` use `torso_per_width or 1.25`.
   - NaN, inf and negative values read 0.0 (tests pass).
   - The ratio has no upper bound. A side-on first measured capture (shoulder width x0.15) teaches 13.54, where the truth is 2.03. After 0.5 s of frontal captures it is still 9.01, because it smooths with RATIO_TAU 1 s.
   - In my probe the hips then dropped. Q48's `per_width`, bad in the same way, broke the track first (a new id, ratio 0), so the big torso was never used. Not blocking.
3. **C45 (duplicate poses): passes.**
   - Two people shoulder to shoulder at 2 m (0.128) and at 3 m (0.087) stay two detections.
   - A child in front of an adult, and a pose without a nose or a shoulder, stay unmerged (tests pass).
   - One person directly behind another cannot meet all three points unless the rear face is hidden, and then its nose is not confident.
   - A doubled pose is merged only when both copies have a confident nose and both shoulders. Otherwise one person gives two bodies, as the plan's rule says.
   - A kept copy that alternates every capture (copies 0.015 apart): one id, shoulder x steps 0.0038 per capture, zone_x range 0.0064. That is about 1.1 px of Dodge travel, under ACTIVE_PX 3.
4. **Pong's numbers: equal, by the report and by code reading.** The orchestrator's E1 row matches the plan exactly: response_ticks 1.0, response_px 12.0, fidelity 0.9947, range 0.6287, win_good 1.0, win_lazy 0.25, win_none 0.0, round_seconds 66.0667, phases_reached 1.0. Actor bodies default to `measured=True` and `torso_per_width=0.0`, so every path they take is unchanged. I did not re-run the 20-seed report (about 63 s, over the 60 s cap).
5. **The games.**
   - Quick Draw passes everything below except B1.
   - Still body: `idle_body` and `degrade(**REAL_NOISE)` (5 seeds) score 0 with no best. These tests pass.
   - Pointing: `Cursor`, then `Glide`, then the bar.
   - Flash rule, generic tests (`-k quickdraw`, 8 passed): held 0 and raw `concurrent_area` 0.001.
   - No strobe: a win is `burst` plus `echo`, a loss is static "TOO SOON", and `over` holds.
   - Bands: none loosened, no override.
   - Bots: the good bot reads only `phase` and `signal`, and the lazy bot reads `wait_left` for its early draw only.
   - Two players: a second body takes seat b at the next round, and a duel records nothing (tests pass).
   - Dodge (c49d902), through the worktree: canonical has held 0, square_flashes 1 and flash_area 0. A still body under REAL_NOISE (2 seeds) scores 0 with no best and 0 active ticks. The good bot reads `rocks`, which the player can see. **Nothing blocks its return except the suite time** (334.84 s against the 330 s limit).
- **5b, the DRAW flash (a safety point): within the rules.** It goes through `fx.flash((255,255,255), 0.15)`; the game does not draw it itself. Measured through the real runner (`probe_5b_flash.py`):

| measure | raw | pushed |
|---|---|---|
| level during the 5 flash ticks (APL) | 1.000 | 0.502 (every channel 128; limiter factor 0.502, its 0.5 floor) |
| square_flashes (canonical, 60 s) | 4 | 4 |
| flash_area | 0.0002 | 0.0001 |
| concurrent_area | 0.0010 | 0.0010 |
| governor held ticks | n/a | 0 (canonical, early, duel) |
| after the flash | n/a | factor 0.51 -> 0.71 over 20 ticks, 1.0 after about 50 ticks (1.7 s) |

   - Shortest time between two signals: 4.9 s measured (canonical). From the code, the floor is 4.5 s: an instant win + RESULT 1.5 + READY 1.0 + WAIT 2.0, or a void by DRAW_TIMEOUT 1.5 + 1.0 + 2.0.
   - TOO SOON gives no flash. A new session needs at least OVER 2.5 + READY + WAIT, so 7 s or more. Two players share one signal.
   - `fx.flash`'s own gap alone forbids a second flash within 0.65 s.
   - So there is at most 1 full-field flash in any 4.5 s. Two in one second, or more than three, cannot happen.
   - If the governor held, it would hold each pixel's last extreme. It never holds here (0 ticks).
   - The return is stored in `_flashed` but never read (`quickdraw.py:244`). It cannot be False here, because no other flash comes within 4.5 s.
6. **Frozen protocol: untouched.** The range makes no change to `arcade/game.py`, `runner.py`, `flash.py`, `brightness.py`, `juice.py`, `bots.py`, `games/__init__.py`, `feel_budgets.toml`, `config.py`, `arcade.toml` or `tests/conftest.py`. It makes no change to `show/`, `deploy/` or `tests/test_wall*`. The canary test file is not in the diff.
7. **What was cut: nothing half built.**
   - E2's hand point: there is no `HAND_LANDMARKS` in the code and no skipped test for it. `landmarks_to_keypoints` is unchanged.
   - Only unused state is left in Quick Draw: `_flashed` (stored, never read) and `_winner` (assigned, never read). No constant, test or skip is left over.
   - The skip count is still 1.

## Removed or changed asserts
None. The only removed lines in `git diff f24cd3d..16dbb91 -- tests/` are:
- imports (`test_camera.py`, `test_pose_mediapipe.py`);
- `test_oracle.py`'s old docstring;
- `test_oracle.py`'s `PLAYS` and `play_key`, which moved unchanged to `tests/arcade/helpers.py` and are imported back under the same names.

Pong's three oracle tests are unchanged. Lane B's tests are untouched, since lane B has not started. The collected count is 1293 (`--collect-only`; before: 1231), and skips are still 1 (the orchestrator's final run: 1292 passed, 1 skipped).

## Noted, not carried (one line each)
- The DRAW flash puts the whole wall at pushed APL 0.502, day or night. That is 4.2x `apl_cap_day` (0.12) and 8.4x `apl_cap_night` (0.06), for 0.17 s every 4.5 s or more. The limiter's 0.5 floor lets it through, which is what spec 7.6 says. It is the arcade's first full-field flash, so it is worth the owner's eye on the wall.
- After each DRAW, the limiter's slow release (RELEASE a tick) shows the bars and "DRAW!" at 51 to 71 percent light for the first 0.67 s, which is the reaction window.
- The orchestrator's finding holds, and it does bite Quick Draw in one case (`probe_qd_hipless.py`): hips under MIN_CONF but both wrists confident. The Cursor keeps the hanging hand, so the bar stays at 56 and the player loses 0-3 on 3 of 3 seeds (with hips: 3-0 or 3-1). Whether real captures lose the hips but keep a hanging wrist needs the owner's recordings.
- A wrist that drops out for longer than the grace puts the bar at the bottom, which arms it (`quickdraw.py:205`). A hand held up then drops out, and comes back after DRAW, counts as a draw without moving. This is rare (a long dropout inside the CPU's 0.25 to 0.8 s).
- `_to_ready_void` (`quickdraw.py:268`) skips `_assign`, so after a void round in a duel a newcomer or a returning player waits one more round.
- `CPU_DRAW` (0.25, 0.80) is inside the plan's allowance. With camera latency and the Glide lag, a human's effective draw is about 0.45 s or more, so the owner's check of the pace is worth making.
- The `duel` scenario never reaches DRAW: every round ends TOO SOON. The two-human draw path is covered only by unit tests.
- `debug_state()["cpu"]` is None when both seats are CPUs (seen after B1's leave).
- The orchestrator's other deviations are sound: I0's `if OTHER_GAMES:` guard, E1's smallest readings, and Dodge's `rocks` key and bot rule (only what a player sees).

## Not covered
- Pong's 20-seed feel report was not re-run (about 63 s, over the 60 s cap). Its equality rests on the orchestrator's E1 run and on code reading.
- I did not run `test_oracle.py`, whole game test files, the full suite, or Dodge's own tests.
- The session-end-and-relaunch flash spacing, and the night clock, are worked from the code, not measured.
- Real-camera questions (hips lost while wrists stay seen, duplicate poses with a low shoulder) need the owner's recordings, which I did not open.

## Probes (file names) and minutes
Folder: `/private/tmp/claude-502/-Users-trey-dev-codeisart/d1e01db2-fed8-414f-9a38-325b95bc9c3a/scratchpad/it15-review-arcade/`. Each probe's output is saved beside it as `.txt`.
- `probe_5b_flash.py`: the DRAW flash through the real runner (canonical, duel, early).
- `probe_qd_leave.py`: B1, 5 seeds.
- `probe_engine.py`: C47, C46, C45.
- `probe_qd_hipless.py`: Quick Draw with hips under MIN_CONF.
- `probe_dodge.py`: Dodge from the read-only worktree (run with `-B`).

Tests run by keyword: E1 and E2 acceptance (21 passed), Pong's C47 test (1), Quick Draw's still/leave/duel tests (8), and `test_all_games.py -k quickdraw` (8). All passed.

`git status` is the same as at the start. Only gitignored `__pycache__` files may have been written by imports from the main checkout. I did not use `cd`, and nothing refused a command.

Minutes: 10:18 to 10:29 by `date`, about 11 minutes.
