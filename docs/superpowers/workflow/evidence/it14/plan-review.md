## Verdict: BLOCKED

## Blocking findings (plan line, what is wrong, the evidence, the smallest fix)

**B1. Plan lines 52-58 and 64-65: the quiet hold does not keep the budget once it ends. The wall shows 7 transitions in one second, in both display models, at fps 20 and 30.**
- What goes wrong. The torn frame overshoots in a square that straddles the tear, then returns. That leaves the square's transition tracker on the wall (its direction, lo and hi) opposite to the governor's. The governor never saw the torn frame. So its next move "in the same direction" is free for the governor, but on the wall it is a new transition. The governor then allows its full 6 in the same second. The two counts stay apart until that extra transition. This is the answer to question 2: yes, the count and the wall come apart.
- Evidence, trace (`r2_trace.txt`). Picture: a reversal, top first, 10 Hz at fps 20. One tear at call 6, split 33. Card model: the square at rows 6-37 flips at slots 26 (torn) and 46 (return). After the hold it flips at slots 68, 82, 83, 84, 85, 86 and 87. That is 7 in the 20 slots from 68 to 87. The probe model reads the same, with slots 67 and 81-86.
- Evidence, sweep (`r1_sweep_20.txt`, `r1_sweep_30.txt`). The planned wall (the writer's scratch copy, the same file as the plan's text) reads 7 in 8 of 19 pictures, for each model and each fps. All of them have flash area 0.000.

| picture | fps 20 (call, split) | fps 30 |
|---|---|---|
| reversal, boundary row 32, top first, 10 Hz | 7 (6, 33) | 7 (8, 33) |
| reversal, boundary row 48, top first, 10 Hz | 7 (6, 56) | 7 (8, 56) |
| reversal, boundary 32 or 24, top first, 5 Hz | 7 (11, 33 / 20) | 7 (15, 33 / 20) |
| 32x32 checks, offset 0 or 16, 10 Hz and 5 Hz | 7 | 7 |
| rows boundary 16, bottom first; columns; partial strobe; scrolls; # band | 6 or less | 6 or less |

- The fix (`r3_fix.txt`, `reset_inplace.py`). When the hold ends, re-initialise the governor in place and apply the counted frame to it once. The 16 cases that read 7 then read 6 (4 pictures x 2 models x 2 fps). The existing show-side tests with the fix and the plan's loop: 121 pass. The one failure is the named replaced test (`r7_existing_on_fix.txt`).
- Smallest change. Add this after plan line 58: "When the hold ends, before this push governs its frame: `self.governor.__init__(h, w, gamma, fps=fps)` in place (`held_ticks` carried), then `governor.apply(self.last)` once, not sent. Every tracker's direction is unknown again, so the next move counts whichever way the torn frame and its return left the wall. The empty window is true: the wall's last change was a second back." Change line 64 to: "The governor during the hold: not called; re-initialised at its end (above)." Doing it in place keeps the soak's `timed_apply` wrapper and the test spies.

**B2. Plan lines 168-183: the exact torn-push tests never reach the end of the hold. So they cannot see B1, and they pass on an unsafe wall.**
- What goes wrong. The hold lasts 3 s or more after a tear. `test_torn_pushes...` drives `3 * fps` frames. `test_one_torn_push...` drives 50 frames, 2.5 s. No first new frame after a hold is ever measured.
- Evidence (`r5_tests_long.txt`). A wrong wall that re-initialises the governor at the end of the hold without priming it passes all 77 of the plan's wall tests. With that wall, the next frame is the governor's first frame and the window is empty. The one failure is the AST test, which reads the unchanged repository.
- With the amended test (below), the planned wall fails 4 cases: lead 0, split 24 and 33, card and probe. The wrong wall fails the same 4. The fixed wall passes.
- Smallest change, in the plan's test text:
  - Line 175: add `@pytest.mark.parametrize("split", [24, 33])` and the parameter `split`.
  - Line 177: `reversal(10, 20, 120, top_first=True)`.
  - Line 180: `split=split`.
  - Line 170: `pattern(hz, fps, 4 * fps)`, so that "call 5" reaches its end.
  - Line 221, for B1's priming: `assert applied == [k / 16 for k in [*range(17), 64, 64, 65, 113, *range(113, 160)]] and wall.governed == len(applied) - 4`.
  - Line 10: set the new-test time to what is measured. The whole file took 10.4 s with `6 * fps` and 120 frames. With `4 * fps` it should be about 6-7 s, which is still over the plan's 4 s for T-wall.

## The questions (1 to 11, one short answer each, with numbers)
1. The writer's account of the seventh transition is right for the tear itself: the overshoot and its return. It misses the lasting direction mismatch (B1): after the hold the wall reads 7 in 8 of 19 pictures, in both models, at fps 20 and 30. Pictures that do not straddle that way read 6 or less: scrolls read 2-3, the partial strobe and the column reversal read 6. Two tears (n and n+1 to n+4, which covers a tear on a counted send and on the first new frame) read no worse than one tear. The writer's residual in the probe model stays. I did not build it separately: on the card order the torn frame shows 1 s after the tear. I did not run the 512x192 wall (time).
2. At the end of the hold the wall does show `wall.last` in both models. On the card, counted send 2's frame packet shows counted send 1's rows (N). When the first new frame is sent, its packet shows N again. But the trackers differ (B1). One extra transition follows (r2), then they agree again.
3. Only `_push` uses `push`'s return value. The soak meters `wall.last` when `governed` changes, and the sheet tool meters `display.count` and `last`. A held step does not raise `governed` and sends nothing. `_push_failed` is used only in `show/main.py`. The soak's rules and "governed = steps" are unchanged with fakes. `r9`: 121 of 122 existing tests pass; the failure is the named test.
4. `_now` is set before every push (`start` pushes nothing). `_close` never waits. A monotonic clock cannot go back. A stalled fake clock would hold for ever with the lights never going dark, but fakes never fail, so it is not reachable. No path pushes with a stale `_now`.
5. No contradiction. The wall is frozen, not blank, if the card keeps its picture. Q65 is replaced by Q66. The owner sees an ERROR with a traceback at each failure (after a good counted send the count resets, so each failure logs), and an INFO "works again". The lights go dark after 10 s of failing and held steps and relight at the first counted send that arrives (`test_plan_loop.py`, 3 of 3 pass). With a failure every few seconds the wall never moves. Only the log shows it.
6. No. The wall is not safe whichever way the card behaves. A card that blanks without packets (r6) makes the planned hold read 7 with flash area 0.500 (blanks after 0.5 s and 0.9 s), and the fix reads 8. That is more than "a blink once a second". Q66's check is a safety gate.
7. Yes, `from_dark` fixes a bright first frame (r6). A 99.9 % lit frame at level 128, then a strobe: 7 and area 1.000 without it, 6 and 0.000 with it. The error border reads area 0.046 either way; that is Q13's small-area rule. A normal start is counted against black: one transition. A restart after a crash comes with `RestartSec=2`, so the window really is empty; a wrong black guess can add the B1-style +1 once, which is harmless for attract. Q67 (the arcade's half) is the right call under the assert rule. I did not verify the lobby's first frames myself.
8. Five wrong walls, all tried in memory:

| wrong wall | caught by |
|---|---|
| hold measured from the first failure | the timing test |
| hold without the last second | the timing test |
| governor still advanced during the hold | the timing test |
| priming without `apply` | the from-dark test |
| a second `display.push` | the AST test in `test_main.py` (static) |
| governor re-initialised without priming at the end of the hold | passes (B2) |

   The time comparisons are exact binary fractions (k/16, 0.5 steps). `in_time` gives k = 1 on the planned wall and is sound. The AST test accepts `clock=None` and misses an alias or a subclass; `**kw` fails closed. The names `FailingPushes`, `playing_loop`, `flash_area`, `square_flashes`, `BUDGET`, `last`, `failed`, `governed` and `holding` all exist.
9. The new test keeps the old safety properties: the counted frame goes again (`pushed[2]`, `pushed[3]`), one push a step afterwards, and the governed count. It drops the old `pushed[3] == loop.rendered`. No other test changes: `test_main.py:303-318`, `test_wall_close.py:35` (no clock, no hold), `test_main_stop`, soak, shot and pattern tests are all green (r9).
10. No. Through `load_config` the tests pass only 0, nan and inf, which are still refused with "gamma" in the message. `arcade.toml` has 2.2, and `arcade.mac.toml` uses the default. The other way in is an `ArcadeConfig` built in code (tests only). There is no `dataclasses.replace` of gamma and no arcade gamma flag. The sheet tool's `--gamma` is on the show side and bounded by the wall. That is a note.
11. The files hold: the B1 fix is inside `show/wall.py`. `tools/show_soak.py` and `tools/show_shot.py` need no edit. `deploy/README.md` says nothing about failed pushes. I0 is exact ("after line 105" is the finite check).

## Notes (not blocking, one line each)
- Close 1 tick after a tear reads 8 on a reversal at budget (card and probe; r6). That is it13's close, unchanged by the plan, and rare (a stop within 1 s of a tear).
- Q66's text should say that a blanking card breaks the budget (7-8, area 0.5), not only that the wall blinks. Q65's resend is not in the budget either (7).
- In the AST test, use `kw.get("clock") not in (None, "None")`.
- A scrolling fine `#` band reads flash area 0.063 at every tear case. That is Q13's small-area exemption, not the hold.
- The plan should say that `SETTLE_SENDS` restarts when a counted send fails (the scratch wall does this).
- The replacement test could assert that the frame sent at 3.5 is the governed rendered frame.
- A failure every few seconds freezes the show; no counter of held steps exists, only the log.

## Probes (file, what it shows, the numbers) and minutes
All are in `/private/tmp/claude-502/-Users-trey-dev-codeisart/d1e01db2-fed8-414f-9a38-325b95bc9c3a/scratchpad/it14-plan-review/`.

| file | what it shows |
|---|---|
| `rlib.py` | the torn display (probe, card, card that blanks) and the real-time sequence |
| `r1_sweep.py`, `r1_sweep_20.txt`, `r1_sweep_30.txt` | 19 pictures x 120 tear cases x 2 models; the planned wall reads 7 in 8 pictures (249 s at fps 20) |
| `r2_trace.py`, `.txt` | the slots of the 7: 68 and 82-87 (card) |
| `r3_fix.py`, `.txt`; `reset_inplace.py` | 7 becomes 6 in 16 of 16 cases with the in-place re-init |
| `r4_amended_tests.txt`, `r5_tests_long.txt`, `wrong_reinit.py`, `test_*_on_*.py` | the exact tests as written pass the wrong re-init wall (77 of 78; the AST test fails because the repository is unchanged); the amended ones fail it and the planned wall (4 cases) and pass the fix (81 of 82; the same AST test) |
| `r6_blank_close_dark.py`, `.txt` | blanking card 7-8 (area 0.5); close after a tear 8; from dark: lit first frame 7 and area 1.0 become 6 and 0.0 |
| `plan_plugin.py`, `plan_plugin2.py`, `test_plan_loop.py`, `r9_existing_tests.txt`, `r7_existing_on_fix.txt` | the plan's loop in memory: 121 of 122 existing tests pass (the named test fails), with the plan's wall and with the fix; loop test, lights and log 3 of 3 |

The repository is unchanged. No process is left running. Start 06:47, end 07:10 CDT: 23 minutes.
