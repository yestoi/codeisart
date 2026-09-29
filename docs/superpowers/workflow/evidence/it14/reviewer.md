## Verdict: APPROVED

## Blocking findings (file:line, the input, what happens, why it blocks)
None.

One finding sits inside carried C53 and does not block. But C53's text is wrong about it, so the owner should see it. The slice made the close worse than it was at b83045d:
- `show/wall.py:115-128`. Take the reversal (top first, 10 Hz, fps 20). One tear at call 28 (split 33). Then `close()` 2 to 14 ticks (0.1 to 0.7 s) later.
- b83045d, driven by its own loop (a repush, then a governed push): the close reads 6.
- da20a3a: the close reads 7 in the probe model and up to 8 in the card model. Flash area is 0.000 in every case. There are 13 such cases per model (`p5c_close_shipped.txt`).
- With b83045d's start taken out (its governor primed with black by hand), a tear at call 6: old 6, new 8, for j 2 to 14 (`p5b_close_fair.txt`).
- Why: before the slice, the step after a tear resent the counted frame and went on governing, so only a close 1 tick after a tear read 8. Now a close anywhere in the hold's first ~0.7 s sends the counted frame and two blacks right behind the tear.
- C53 already carries "a close within a second of a tear reads 8", and the plan chose a close that is never held. Every case here is inside that second, so it is not new scope. But C53 says "it13's close, not changed by it14". That is false: the window where a close reads over 6 grew from 1 tick to about 14 ticks. C53's text should say so, and its fix should keep the priority it has.

## The safety points (1 to 9, one short answer each, with numbers)
1. **C51, the hold's end (B1). Holds.** I ran the plan review's `r1_sweep.py` unchanged against the REAL `show.wall.GovernedDisplay` (from_dark=True, the tick clock). That is 19 pictures x 120 tear cases (one tear at calls 1 to 22 with splits 8/20/33/56, and two tears n, n+j) x card and probe models, at fps 20 and fps 30.
   - Every picture reads at most 6 at both fps: 32 of 38 rows read 6, the scrolls 2 to 4, the hash band 0.
   - This covers all of the review's sevens: rows boundary 32/48 top first at 10 Hz, 32/24 at 5 Hz, checks at offset 0 and 16. The review read 7 on these with the planned wall; the real wall reads 6.
   - Flash area is 0.000 everywhere except the hash band: 0.063 at fps 20 and 0.094 at fps 30. It reads the same with no tear at all (`p6_hash_notear.txt`), so it is Q13's small-area exemption, not the hold.
   - Repeated tears (`p1_repeat.txt`): every 2nd, every 3rd, every call, and a run of four starting at calls 1 to 12, splits 8/33/56, 19 pictures, both models, fps 20 and 30. The worst is 6 with area 0.000, apart from the same hash band.
   - Run times: 331 s at fps 20, 443 s at fps 30, 343 s for the repeated tears.
2. **The re-init. Correct.** Probe: `p2_mechanics.txt`.
   - The governor is re-initialised in place. `wall.governor` is the same object after the hold, and a spy on `apply` saw all 142 applies.
   - The re-init runs exactly once per hold, with the wall's own arguments: `(64, 128, 1.0), fps=20` for a wall built with gamma 1.0 and fps 20.
   - `held_ticks` is carried and never falls (max 50).
   - The priming `apply(self.last)` happens at the same tick as the new frame's apply, and only one send happens at that tick. The primed frame is the counted frame.
   - `self.last` cannot be None in a hold: `_govern` sets `_last` before `_send`. With a failed first push, the counted first frame goes out at 1.0 and 2.0 s, and new frames start at 3.0 s.
   - If the first new frame after the hold fails, the hold restarts: sends at 1, 2, then 4, 5, 6, 6.05.
   - If a counted send fails, `SETTLE_SENDS` restarts from 0: sends at 2, 3, 4 when call 2 fails, and 1, 3, 4, 5 when call 3 fails.
   - The wall touches only `__init__`, `apply`, `held_ticks` and `shape` on the governor. No private field.
   - The only failed send that does not start a hold is inside `close()`, after which the display is closed. No outside `repush` caller is left (`_push_failed` is gone).
   - A bad-shape frame at the hold's end raises ValueError after the re-init. Nothing is sent and the next push governs. That is harmless.
3. **The loop's clock. Correct.**
   - `_now` is set in `start` (`show/main.py:139`) and first thing in `step` (`:239`). `step` is the only push path, and `_close` never reads the clock. No path pushes with a stale `_now`.
   - A held step calls `_failing(now)` and logs nothing (`:315-317`).
   - A counted send that arrives takes the success path: failures reset, lights relit. `test_a_held_loop_step_counts_toward_the_dark_lights` passes: lights go off at 10 s of held and failed steps and relight at the first counted send.
4. **C52, from dark. Correct.** Probe: `p4_dark_gamma.txt`.
   - Nothing is sent at birth (0 sends).
   - With from_dark=True: strobe lit first or dark first, reversal top first and bottom first, a white first frame then a strobe, 10 and 5 Hz, fps 20 and 30. All read 6 with area 0.000, the dark wall counted as the first frame.
   - With from_dark=False (control), the same pictures read 7 with area 1.000 (strobe) or 0.500 (reversal).
   - Only `show/main.py` (2 calls) and `tools/wall_pattern.py` (1 call) build `GovernedDisplay(` outside tests. All three pass the literal `from_dark=True`, and main's two pass `clock=lambda: self._now`.
   - The AST test checks the call nodes' keywords, not text, so it passes by meaning. `tools/ledvision/` is not scanned (non-recursive glob) and holds no `GovernedDisplay`.
5. **The close. Not held, as planned.** It does NOT keep b83045d's numbers: see the note under Blocking findings (C53's scope, 1 tick became about 0.7 s).
   - During a hold, `close()` sends the counted frame (when `unsent`), then two governed blacks, then closes the display. The prose test checks 6 calls, counted frame, black, black, closed.
   - The display is closed in every case (`finally`).
   - The plan review's own close case (tear at call 6, split 33, close 1 tick later) reads 8 on both commits.
6. **Every path to a display. Correct.** `_send(` has two call sites (`show/wall.py:103`, `:110`) and `display.push` one (`:133`). There is no alias, `getattr`, stored bound method or lambda. `close` now calls `_govern` directly, and the old `push = self.push` alias is gone. `set_brightness` and `close` are the only other uses of `self.display`.
7. **C50, the arcade's gamma. Correct.**
   - Taken: 1.0, 2.2, 1, 2, 1e0.
   - Refused: 0.999, 2.2000001, 0.22, 22.0, nan, inf, -inf, 0, true, false, "2.2".
   - `arcade.toml` and `arcade.mac.toml` load with 2.2.
   - The only other source of gamma for the arcade's governor is `ArcadeConfig()` built in code (`arcade/bots.py:169`, default 2.2). No flag or `replace` changes gamma.
8. **Frozen files. Correct.** `git diff 0dae849..da20a3a -- arcade/flash.py arcade/brightness.py show/display/colorlight.py` is empty. `git diff b83045d..da20a3a --stat -- arcade/ deploy/` shows only `arcade/config.py` (+2).
9. **The tools. No change in numbers or meaning.**
   - `wall_pattern.py`: `from_dark=True`, no clock, so it never holds. Its test file was not edited and passes.
   - The soak: `governed = steps` still holds, because neither the priming apply nor a counted send raises `governed`. With fakes nothing fails, so there is no hold. The `timed_apply` wrapper survives the in-place re-init.
   - `show_shot`: a counted send raises `display.count` and is metered as a repeat frame (no transition). Its held count can move only by a first frame that is now counted against black (the plan says so).

## Removed or changed asserts
- `git diff b83045d..da20a3a -- tests/` removes three assert lines, all in `tests/test_main.py`'s `test_after_a_failed_push_the_last_governed_frame_goes_again`, the one test the plan names:
  - `assert inner.count == 4 and governed == 2 and loop.wall.governed == 3`
  - `assert np.array_equal(inner.pushed[2], third) and np.array_equal(inner.pushed[3], loop.rendered)`
  - `assert inner.count == 5`
- The replacement is byte-identical to plan lines 243-259 (difflib). It keeps these safety properties:
  - the counted frame goes again (`pushed[2]`, `pushed[3]` == counted);
  - nothing new is governed during the hold (`governed == 2` at each step);
  - one push a step afterwards;
  - it adds `holding`.
- It swaps `pushed[3] == loop.rendered` for `pushed[4] == loop.wall.last`, the governed frame. That is the right object.
- `tests/test_wall_hold.py`'s exact block matches plan lines 81-238 line for line once blank lines are ignored. The only addition is the plan's docstring. No assert, input or number changed.
- The prose tests match the plan's prose.
- I0's config tests match the plan (0.22, 22.0, 0.5, 2.3; 1.0 and 2.2; the two shipped configs).
- Collected: 1231 (`--collect-only`). No new skip marker in any changed test file (the one `skipif` at `test_main.py:229` is older). I did not run the full suite.
- `test_wall_hold.py`, `tests/arcade/test_config.py`, `test_wall_pattern_governed.py` and `test_wall_close.py`: 157 passed in 17.4 s, on a loaded machine.

## Noted, not carried (one line each)
- C53's text ("it13's close, not changed by it14") should be corrected: a close 2 to 14 ticks after a tear read 6 at b83045d and reads 7 to 8 now.
- The LEDVision kit (PR 1) reaches the card outside the governor: its Test patterns, Brightness and "Send / Save to Receivers" drive the wall through the Windows VM. It is a setup tool run with the owner, with its own "no fast flashing, 40 %" rule. It changes no show or arcade code.
- The card's receiver parameters written by that kit (its behaviour without packets) decide Q66's safety gate. The hardware check should be done after the final Save to Receivers.
- After a crash restart, the card may still hold the old process's last frame while the governor is primed with black. That is a possible +1 once, no worse than the unprimed b83045d start (the plan review's Q7). Attract does not come near the budget then.
- `push`'s docstring says a frame of another shape raises. During a hold it is dropped silently instead (deviation 4). Nothing is sent, so this is harmless.
- `test_wall_hold.py` imports test_main's autouse `no_devices`, which makes it autouse there too (deviation 8). Harmless.
- Commit trailers: I0 and the merge carry Opus 5.5, not the plan's Fable 5.1 (process only).
- Deviations 1 to 9: I judge each one a sound reading of a silent plan. Only 6 (close as today) has a safety effect, and that effect is C53's.

## Probes (file names) and minutes
All are in `/private/tmp/claude-502/-Users-trey-dev-codeisart/d1e01db2-fed8-414f-9a38-325b95bc9c3a/scratchpad/it14-review/`, each with its `.txt` output.

| probe | what it runs |
|---|---|
| `rlib.py`, `r1pics.py` | the plan review's library and pictures, repointed to the real `show.wall` (it asserts the module path) |
| `r1_sweep.py` → `r1_sweep_20.txt`, `r1_sweep_30.txt` | the review's sweep, unchanged |
| `p1_repeat.py` | repeated tears |
| `p2_mechanics.py` | the re-init, failure orders, governor fields |
| `p4_dark_gamma.py` | from dark, and C50 |
| `p5_close.py`, `p5b_close_fair.py`, `p5c_close_shipped.py` | the close on b83045d (`wall_b83045d.py`, from `git show`) vs da20a3a |
| `p6_hash_notear.py` | the hash band's area with no tear |

Nothing was written to the repository (`git status` shows only the operator's `state.md` and `journal.md` and the owner's folders), and no probe process is left running. Start 07:49, end 08:07 CDT: 18 minutes.
