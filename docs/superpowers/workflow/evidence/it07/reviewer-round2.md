# it07 review, round 2: the B1 fix 6ebbb6d (a2e6681..6ebbb6d)

HEAD is 6ebbb6d. The probe output is in probe_round2.txt, next to this file.

## Verdict: APPROVED

## Blocking findings
None. B1 is closed.

1. **B1 is closed.** I ran the checks below as well as reading the diff.
   - **Nothing in the repository claims an idle hint is measured or passed.** I grepped every file outside
     docs/superpowers/ with `git grep -i -E "idle_hint|idle.hint|IDLE_WINDOW|hint"`. It finds only these:
     - arcade/feel.py:244-245 and the header comment of arcade/feel_budgets.toml. Both say the metric is not
       spec 9.3's idle hint and has no budget.
     - .claude/skills/arcade-game-authoring/SKILL.md:106 and :188. Both are guidance to game authors ("hint
       within three seconds"). Neither says that a metric checks it.
     - The skill's list of default metrics never named idle_hint.
   - **`judge` ignores a metric with no budget.** It loops over the budgets, not over the metrics:
     - `feel.judge({"presence_answer_seconds": 99.0, "fidelity": 0.9}, {fidelity: min 0.8})` returns `[]`.
     - A budgeted miss is still reported: `fidelity 0.1` gives `['fidelity 0.1 < min 0.8']`.
     - The new test `test_presence_answer_has_no_default_budget` checks that no kind, including its layout
       tables, carries the metric. It also checks that the values None, 0, 6 and 1e9 never produce a failure.
   - **Pong's report at 128x32 still has no failures.** `feel.report(Pong, "128x32", seeds=bots.seeds(Pong,
     "128x32", 20))` took 49.3 s and gives `failures == []`.
     - presence_answer_seconds is 0.0 and is not among the budgets.
     - No `idle_hint_seconds` key is left in the metrics or the budgets.
     - The budgets are the 15 expected ones: the 12 from before X1 plus win_good, win_lazy and win_none,
       score_visible and score_legible.
2. **The changed asserts: none is weakened beyond what the fix requires.**
   - **Extended or equal:**
     - test_bots.py::test_budget_file_parses_and_has_every_kind: `idle_hint_seconds` left METRICS. The assert is
       still an exact equality over the whole file, so it now pins the budget's absence.
     - test_feel.py::test_measure_repeats_under_seeds: the key set has one name renamed. Equal.
   - **Replaced to match the fix:**
     - test_score_visibility_counts_the_ticks_it_is_shown: the value assert is kept under the new name.
       `"idle_hint_seconds 6 > max 3" in failures` became two asserts: the metric has no budget, and it produces
       no failure. The old line tested the budget that the fix removes.
     - test_idle_hint_times_the_first_answer_to_a_still_body was renamed
       test_presence_answer_times_the_first_answer_to_a_present_body. Every value assert is kept. The budget
       equality became `not in budgets`.
   - **Narrowed:** test_a_score_that_is_never_shown_misses_both's `liar` lost its idle_hint entry.
     - This drops the only check of the max-only form, `"<metric> None misses max N"`.
     - The same `judge` line is still covered in its min form and its min-and-max form (test_feel.py:259, :378).
       Not blocking.
   - **Removed tests:** none. One test was renamed and one was added (+1: 675).
3. **No other band changed.**
   - The fix's diff of arcade/feel_budgets.toml removes only the three `[<kind>.idle_hint_seconds] max = 3`
     tables and edits one comment line.
   - arcade/games/pong_feel.toml is untouched in a2e6681..6ebbb6d.
4. **The full test command, run once:** 675 passed in 135.71 s, exit 0, 0 skipped. `--collect-only`: 675
   collected, against 674 before the fix.

## Notes
- READ: .claude/skills/arcade-game-authoring/SKILL.md:105-106 says "The game must score nothing" in idle_body. Pong
  does not meet that on 3 of 10 seeds (REPRODUCED in round 1: seed 1842885004 banks 1 point and a best of 1.0).
  Nothing asserts it. Carried from round 1's ruling 3.
- READ: SKILL.md:106 and :188 ask for a hint within 3 s of a still body. No metric now checks it, so a later game's
  hint is judged only by a person. This matches the fix's choice, and fail-versus-win is in the same state.
