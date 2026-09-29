# Iteration 14 plan report: the flash governor's three gaps

## Plan (path, line count)
- `/Users/trey/dev/codeisart/docs/superpowers/plans/2026-09-29-it14-governor-gaps.md`, 298 lines. No line is over 120 characters. It is not committed.
- Line 2 is as asked. It holds the exact test bodies (the wall's file, and the one loop test it replaces), plus I0, the lanes, I2, the decisions and the questions.
- Probes and their outputs are in `/private/tmp/claude-502/-Users-trey-dev-codeisart/d1e01db2-fed8-414f-9a38-325b95bc9c3a/scratchpad/it14-plan/`:
  - `p1_why_seven` (.py, .txt)
  - `p2_hold`, `p3_variants`, `p4_single` (with `tornlib.py`)
  - `c52_wall_tests.txt`, `c52_runner_tests.txt`, `c52_runner2_tests.txt`
  - `c51_tests_quiet.txt`, `c51_tests_repush.txt`
  - `exact_tests_vs_wrong.txt`
  - `impl/wall14.py`: a scratch copy of the planned wall, with the wrong modes
  - `plug/`: the pytest plugins that applied the changes in memory
- The repository is unchanged apart from the plan file. `git status` also shows `docs/superpowers/workflow/state.md` as modified. I did not touch it.

## Tasks and lanes
| Step | Who | Model | Files | Runs |
|---|---|---|---|---|
| I0 (C50) | orchestrator | - | `arcade/config.py`, `tests/arcade/test_config.py` (`arcade.toml` is read only) | first, in the main checkout, test first, then the suite |
| T-wall (C51, C52 show half) | task | opus | `show/wall.py`, `show/main.py`, `tools/wall_pattern.py`, `tests/test_wall_hold.py` (new), `tests/test_main.py` (lines 289-300 only) | worktree from I0's commit |

- There is only one task, so nothing runs in parallel. Merge order: I0, then T-wall.
- After the merge, run T-wall's files first. Then run `tests/test_wall.py`, `tests/test_wall_close.py`, `tests/test_main.py`, `tests/test_wall_pattern_governed.py` and `tests/test_show_soak.py`. Then run the full suite.
- `arcade/runner.py` has no task, because the arcade half of C52 went to Q67.
- The new tests take 3.1 s in scratch. The limit for new tests is 8 s.
- For the orchestrator: in a worktree, `tests/arcade/test_pose_mediapipe.py:223` is skipped as well (the pose model is not in git). The plan says so.

## The three gaps

### C51: torn pushes
**Why the probe reads 7 (p1).**
- A single pixel never changes more often than the governor counted: the flash area is 0.000 in every case.
- The seventh transition belongs to a 32x32 square that straddles the tear line. Example: rows 5 to 36 at 10 Hz, fps 20, a tear every 2nd call.
- The torn frame is new top rows over old bottom rows. Its square mean lies outside the range between the two governed frames. In the example it goes 0.121, then 0.772 (torn), then 0.652, then 0.000 (torn), then 0.121.
- Each tear therefore overshoots, and coming back from the overshoot is a transition in the other direction. After the last governed change, that return is the seventh transition, at tick 7.
- The operator's guess is half right. The tear does delay half of a change by one push. But it does not move a transition into the window: it creates a new one, the overshoot and its return.
- The list having two entries per tick does not cause the 7. Counted in real time (ticks) it still reads 7, in 8 of 8 cases. Counted by list entries it reads 7 in 7 of 8 cases: at 5 Hz, fps 30, every 2nd, the list says 6 but real time says 7.
- Colorlight's real order (`colorlight.py:126`: the frame packet first shows the rows the previous push left) shows the same torn frame, one send later.

**Does Q65's default close it?**
It closes the repeated tears, but not a single tear. The tables below are in real time, with the governor primed from dark and the wall measured from dark. "Probe" is the probe's display, "card" is colorlight's order.

Repeated tears (p3; 2 patterns x 4 rates x 5 tear cases x 2 models):

| Wall | Worst square transitions | Flash area |
|---|---|---|
| today (the loop resends, then pushes) | 7 (reversal, 5 Hz, fps 30, every 3rd, both models); 6 elsewhere | 0.000 |
| Q65 default (resend every tick for 1 s) | 6 (every 2nd: 1-2; every 3rd: 1-3) | 0.000 |
| quiet hold (planned) | 6 (every 2nd: 1-2; every 3rd: 1-2) | 0.000 |

One tear at call 1 to 20, split rows 8/24/32/40/56, 10 Hz at fps 20, reversal and strobe, with 0 or 1 leading frame (p4):

| Wall | Probe model | Card model |
|---|---|---|
| today | 8 (reversal top first, call 2-3, split 24) | 8 |
| Q65 default | 7 (call 6-7, split 24) | 7 |
| still 1 s, one resend, then new frames | 7 | 7 |
| quiet hold (planned) | 6 | 6 |

- Without priming (p2), Q65's default reads 7 for one tear at call 7, split 32, reversal 10 Hz, fps 20. That is the tear on the budget's last change.
- So Q65's default does not close C51. The plan uses the quiet hold, which is Q66 below:
  1. Nothing is sent for 1 s after a failed send.
  2. The counted frame is sent.
  3. Nothing is sent for 1 s, then the counted frame again.
  4. After 1 s more, new frames start.
  5. Any failed send starts the hold again.
- Why the quiet hold works: with colorlight's order, the torn frame and the return to the counted frame are each at least 1 s from any other change.
- One residual is left, in the probe's model only. There the torn rows show at the moment of the tear, which no wall can move. A picture built for it could still read 7. No picture in the probes did.

**Where the hold lives and what it does:**
- It lives in `GovernedDisplay`.
- It is on when a `clock` is given. The loop passes its step time, set in `start` and `step`.
- The pattern tool passes no clock. It stops and closes at its first OSError, so it never holds.
- `close` is never held: the counted frame goes if it was unsent, then two governed black frames, with no wait.
- During the hold, `governor.apply` is not called and the new frame is dropped. The governor's window counts frames, so the frames it never sees keep its window longer. After the hold it is therefore stricter in seconds, never laxer.
- What `push` returns:
  - `None` when it sent nothing.
  - A copy of the counted frame when it sent that.
  - The governed frame otherwise.
- A failed send raises, as it does today.
- The loop treats `None` as a failing step: it counts toward the lights going dark at 10 s, and nothing is logged. A counted send that arrives is a good push.

### C52: the governor's first frame
**Today, from dark** (it13's p2_close_faults, and this iteration's exact test on the unprimed wall): 7 transitions. The flash area is 1.000 for the strobe and 0.500 for the reversal. All 8 from-dark cases fail on it.

**Fix planned: `from_dark=True`.** It does one `apply` of black at birth and sends nothing.
- It is opt-in, and every caller passes it: the two calls in `show/main.py` and the one in `tools/wall_pattern.py`. An AST test holds this.
- With it, the 8 cases (10 Hz and 5 Hz, strobe and reversal, fps 20 and 30) read at most 6 transitions and area 0.0 on what was sent, with the dark wall counted as the first frame.

**Arcade half.** `arcade/runner.py` priming at line 296 is not planned (Q67). It changes an existing assert, and the one variant I tried changes more.

### C50: the arcade's gamma
- `arcade/config.py` gets a bound of 1.0 to 2.2, inclusive.
- New tests: 0.22, 22.0, 0.5 and 2.3 are refused; 1.0 and 2.2 are taken; the shipped configs are inside the bound.
- `arcade.toml` has 2.2. `arcade.mac.toml` sets no gamma, so it gets the default 2.2.
- The only gammas that tests pass through `load_config` are 0, nan and inf. They are still refused, and the messages still name "gamma".
- `test_brightness.py:109,113,259` build `ArcadeConfig` in code (1.0, 2.2, 0.0, inf, "2.2") and do not go through `load_config`.

### Wrong implementations tried against the exact tests
Each was a mode of `impl/wall14.py` (78 tests in the file). The planned wall passes 77 of 78. The one it fails is the AST caller test, which reads the unchanged `show/main.py` and `tools/wall_pattern.py`.

| Wrong wall | Exact tests that fail |
|---|---|
| Q65 resend every tick | hold timing; one tear (4) |
| one resend, then new frames | hold timing; one tear (3) |
| quiet hold, but the governor applies the held frame | hold timing |
| no hold (today) | hold timing; torn pushes (2) |
| `from_dark` ignored (today's first frame) | from dark (8); torn (4); one tear (4) |
| priming by sending governed black at birth | from dark (8, it sends at birth); hold timing; one tear (4) |
| priming with the first frame | from dark (8); torn (4); one tear (4); hold timing |

The loop's replacement test passes with the quiet hold. It fails with Q65's resend (at t=1.0, count 3 against 2) and with today's code.

## Existing tests touched by the priming
| Test | Assert | Changes? |
|---|---|---|
| `tests/test_wall.py:59` `test_the_display_gets_exactly_the_governed_frame` | `np.array_equal(out, want)`, `held_ticks == reference.held_ticks` (unprimed reference) | yes, if priming is the default |
| `tests/test_wall_close.py:19` `test_close_after_a_failed_push_sends_the_counted_frame_before_black` | the last 3 pushed equal an unprimed reference | yes, if priming is the default |
| `tests/test_main.py:406` `test_a_clean_close_pushes_two_governed_black_frames` | black frames equal an unprimed reference | yes, if priming is the default |
| every other show-side test (164 of 167 across test_wall*, test_main*, test_wall_pattern*, test_show_soak, test_show_shot*) | - | no |
| `tests/arcade/test_headless.py:227` `test_tick_budget_with_the_governors_share` (6 cases) | `len(ticks) == len(governor) == 300`: the priming apply makes it 301 | yes, with the runner primed |
| the other 370 arcade tests (runner, oracle, feel, headless, lobby, game, brightness, flash, first_playable, pong, all_games, figure, pattern, sources, main, arcade_shot, arcade_evidence, display) | - | no; no feel band moved |
| variant "the runner's first push is governed black" | test_runner (push order, crash icon x2, the push-failure log count, raising limiter or governor x2), test_headless lobby start, test_arcade_shot non-black | 8 fail, so worse |

- The plan makes priming opt-in, so none of the show-side asserts above change.
- The hold (a probe, not the priming) changes `tests/test_main.py:289-300`, which asserts a new frame 0.05 s after a failure. Any hold changes it. The plan names it as the one replaced test.
- The hold would also change `tests/test_wall_close.py:35` if it were on without a clock. It is not, so that test is unchanged.

## Decisions taken
- The hold is quiet (Q66), lives in `GovernedDisplay`, and is on when a clock is given. The loop gives its step time.
- `close` is never held.
- The governor is not called during the hold.
- `push` returns `None` when it sent nothing.
- `_send(` keeps two call sites, through a private `_govern`, and `display.push` keeps one.
- `from_dark` is opt-in, passed by every caller and checked by the AST test.
- `tests/test_main.py:289-300` is the one named replacement. Its new exact body is in the plan.
- The arcade's priming is left out (Q67).
- `arcade.toml` is not edited: it is already at 2.2.

## Questions for the owner
- **Q66:** The hold after a failed push is quiet, not Q65's resend every tick:
  1. Nothing is sent for 1 s.
  2. The counted frame is sent, then nothing for 1 s.
  3. The counted frame is sent again, then nothing for 1 s.
  4. New frames start.

  The wall is frozen for 3 s or more per failure, and a dead link is sent to once a second. **Default: yes, quiet.**

  The quiet hold needs the Colorlight card to keep its last frame through 1 s with no packets. Check this on the real panels: stop the sender for 3 s and the picture must stay. If the card blanks, fall back to Q65's resend.
- **Q67:** May `arcade/runner.py` prime its governor with black at birth (C52 for the arcade)? It changes `tests/arcade/test_headless.py:227` (300 becomes 301, in six cases). **Default: not changed.** The arcade starts on the dark lobby.

## What was cut or moved
- The ride-along note task is not planned. It covered point (3), a missing `--config` refused by the pattern tool, the soak, the sheet tool and `python -m show`; point (2), `load_config` type and sign checks; and point (5), the soak judging `errors_at_setup`. The reasons:
  - `tools/wall_pattern.py` and `show/main.py` belong to T-wall this iteration.
  - My planning time was over.
  - Point (3) for `python -m show` needs care with spec 4.6, because the default `show.toml` path is always "given".

  These stay notes for the next task in `show/config.py` and `tools/`.
- The arcade half of C52 moved to Q67.
- `p2_hold` took 9.7 min, close to the 10-minute limit. Later probes were made smaller.

## Minutes
- Start: Tue Sep 29 06:02:59 CDT 2026
- End: Tue Sep 29 06:45:10 CDT 2026 (42 minutes, over the 30-minute guide; mostly the C51 probes)
