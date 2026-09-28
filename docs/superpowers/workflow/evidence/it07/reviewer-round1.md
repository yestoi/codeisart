# it07 review: 6ddaf78..a2e6681 (the oracle for games, and C37)

Probes (all under the scratchpad, run with the venv and PYTHONPATH set to the repository root): probe_response.py,
probe_pong_rounds.py (+ probe_idle.txt), probe_stubs.py, probe_c37.py, with their .txt outputs beside them.

## Verdict: BLOCKED

## Blocking findings (file:line, the input, what happens, why it blocks)

**B1. `idle_hint_seconds` passes without an idle hint.** Files: arcade/feel.py:239-256 (`_idle_hint`) and
arcade/feel_budgets.toml (`idle_hint_seconds` max 3 for every kind).
- Input: Pong's own `idle_body` and `nobody` scenarios, seed 4107362358 (`bots.seeds(Pong, "128x32", 1)[0]`),
  through `feel._idle_hint`.
- What happens: it returns 0.0 s, and the oracle's `test_feel_pong_meets_its_budgets` passes it. Pong draws no
  hint at all: there is no hint code in arcade/games/pong.py.
  - From tick 0 to tick 179, the 53 differing pixels sit in columns 0-1, 21-22 and 29-33.
  - In `idle_body` those pixels are amber (255, 120, 0); in `nobody` they are CPU green (0, 200, 0).
  - So the difference is the seated body's paddle colour, its score digit and the player marker. It says nothing
    about a hint appearing for a body that stands still.
- Why it blocks: the metric names spec 9.3's "hint appearance in idle_body" and spec 11's "hint within three
  seconds of a still body". Any game that seats, colours or draws a present body scores about 0 on it, whether or
  not it ever hints. That is a metric passed without the property it names, in the oracle that is meant to judge
  every later game. The implementers flagged it themselves (report finding 4), but it still ships with a default
  budget for every kind.
- Smallest fix, either of:
  - Take `idle_hint_seconds` out of the default budgets and give the report key a name that says what it
    measures ("the wall answers a present body"), until a real hint measure exists.
  - Measure what spec 9.3 names: pixels in idle_body that were not lit on the body's first ticks and appear
    later, while the body stays still. Or compare idle_body against the same body moving, so what presence alone
    draws cancels out.

## Rulings (the ten points above, numbered)

1. **The Pong fix 35ae954: not blocking.** It is real code, but in real play it changes nothing a player meets, and
   it does not fake the property.
   - Through the lobby, Pong seats the walk-up on its first update both before and after the fix: (t 0.033,
     humans 1, cpu "right") for pre-fix (8f68d07) and post-fix alike.
   - The metric failed before because `feel.measure` launches the game directly and feeds it canonical's first
     4.5 s (the empty wall, the walk-up, the hand raise). Pre-fix Pong then left both seats to the CPU until the
     next serve after a point. Re-run: pre-fix response_ticks 10.0 and fidelity -0.2823, the same as I1 saw.
   - The fix makes Pong seat a body mid-rally when no human holds a seat. That matches spec 8's "a second body
     stepping in joins live" for a first body, and in the arcade it is reachable only after a seated player's
     seat was freed at a serve.
   - Does `response_ticks` measure spec 9.3/11's response? Partly: Pong really answers in 1 tick, and the value 2
     is an artifact of the measure.
     - The first differing tick is 1 at almost every probe.
     - The value 2 comes from a 2 px paddle moving about 1.7 px a tick against RESPONSE_PX 12: 8 px differ at
       tick 1 and 16 px at tick 2.
     - Probes at the clamp (paddle at the wall) give 6 to 10.
   - It holds at the plan's PROBES 8: 2.0 on all 5 seeds tried (4107362358, 2211860640, 450822426, 1842885004,
     4089226287). It does not hold at other probe counts on the seed measure() uses, 4107362358: PROBES 4 gives
     5.0 (per probe [1, 2, 8, 10]) and PROBES 16 gives 5.0.
   - So the pass sits on the probe placement, not on a margin. It is deterministic, so it is not flaky, but a
     small change to the sweep, the paddle or PROBES flips it. Carry it as a note on the metric (magnitude and
     latency are mixed for continuous control), not as a Pong defect.
2. **Pong cannot be finished by points against the good bot: not blocking.**
   - Over bots.seeds(Pong, "128x32", 20), every good play ends at the cap, 92.03 s (90 s plus the 2 s over).
     The human side's points are {1: 5, 2: 8, 3: 6, 4: 1}, the CPU scores 0 in all 20, and none reach
     WIN_POINTS 5.
   - Spec 8 game 2 says "first to 5", and Pong implements that rule. Spec 8 also says every game "ends in 45 to 90 s
     or on a clear result", and spec 11 and the round_seconds band ask for 20 to 120 s. The cap ending is
     within all of them.
   - No stated requirement is missed. Still, a 2-to-0 game at a 90 s cap is slow play, a tuning note for the
     owner's first live test.
3. **The four changed asserts.**
   - `test_registered_and_declared`: the equality now covers the five scenarios. Extended, not weakened.
   - `test_budget_file_parses_and_has_every_kind` and `test_measure_repeats_under_seeds`: the expected dicts and
     the key set gained the three X1 metrics. Extended (still equality), not weakened.
   - `test_idle_body_scores_nothing` is new (P3), so no existing assert was removed. It checks one seed and never
     asserts `score == 0`, so it does not test what its name (the plan's name) promises.
     - REPRODUCED through the real runner (`run_headless(cfg, font, Pong, idle_body(), seed=s)`) on 10 seeds: an
       idle body banks points on 3 of them. Seed 1842885004 ends 1-5, 4089226287 ends 2-5, 2366494866 ends 2-5.
     - Each session ends "done" with that score, and `Scores.record` stores it as the pong best (1.0 and 2.0).
     - Every idle run also records a best of 0.0.
     - The session is never ended "inactive": a ball bouncing off the still human paddle sets `active`
       (pong.py:290-291, which predates it07).
     - Neither spec 7.5 nor spec 8 forbids this, so it is not blocking. It is a gap between the test's name and
       what it checks: for an owner or operator call.
4. **Stub games against the oracle: the oracle catches both.** probe_stubs.py.
   - An input-blind bouncing dot (kind score, `[fidelity]` cursor_y against dot_xy) fails: `response_ticks 10 >
     max 2`, `fidelity 0.01434 < min 0.8`, plus phases, round and win failures. Without a feel file it also fails
     with `fidelity None` and `range None`.
   - Six reversing 5 px stripe pairs over the left 60 x 32 px fail the soak's pattern check. Reversing every 0.5 s,
     pushed pattern_area is 0.454 to 0.469 on all 10 soak runs, against 0.25, so `test_every_game_keeps_the_flash_rule_in_the_soak` fails. At 15 Hz swaps it is 0.469
     pushed, and raw flash_area 0.469 fails too.
   - Note: pattern_area is not a feel metric. Only the generic soak test catches stripes; the feel report of the
     stripe toy fails only on response and phases.
5. **pattern_area and stripes against Q15 and Q30: as required.**
   - A 12-pair grating over the whole wall scores 1.000, whether it reverses every tick or every 2 ticks. The same
     grating drifting 1 px a tick scores 0.992.
   - Pong's solo, duel and canonical score 0.0000 pushed and raw. The dim net, blue 96, is below THRESHOLD, so it is
     not a stripe.
   - The lobby's ticks in canonical score 0.0000 at 128x32 and 64x64.
6. **C37 (P6, `KeypointHold`): meets the plan; one plan-literal behaviour noted.**
   - On the reviewer-notes input, with real Pong in the lobby and with the test's spy, raw concurrent_area is:
     - 128x32: 0.0791, 0.0752, 0.0918, 0.0732, 0.0771.
     - 64x64: 0.0859, 0.0732, 0.0674, 0.0801, 0.0869.
   - Pushed is identical, and the governor held 0 ticks. The worst, 0.0918, is under SMALL_AREA 0.1, down from
     0.131 to 0.151 before the fix.
   - A wrist gone for good is last drawn 0.5 s after it drops (grace 0.55 s), then never again.
   - A held keypoint does draw a limb where the body no longer is. The hold keeps the keypoint's absolute
     camera place, and `to_wall` maps it through the current body's box.
     - A walker crossing 0.3 of the zone in 1 s with the right wrist dropped: the held wrist lands up to 9.0 px
       from the true wrist on the 32 px figure.
     - The same walk in 0.6 s: up to 15.0 px.
     - Both last for up to 0.5 s and never past the grace.
   - That is what the plan specifies ("takes its last confident place"), so it is not blocking. Holding the
     keypoint relative to the body's box would remove the stretch.
7. **S1's callable feed and `bots.play`: correct.**
   - `run_headless` calls the callable once, before the launch (headless.py:108-111). Every record goes through
     `runner.tick`, and every frame reaches the display only through `_push`, the limiter then the governor
     (runner.py:545-550). No bot or metric pushes.
   - With reaction_ticks r, the bot at tick i gets `states[i-1-r]` (bots.py:152-153). That is the state after tick
     i-1-r, r ticks behind the latest completed tick. The state of the tick being fed does not exist yet when the
     bot decides, so a bot never sees the present.
8. **Pong's 1x score: a stated requirement Pong misses, but not blocking here.**
   - Spec 7.4 says "scores use scale=2 (10 by 14 with 2 px strokes, which reads to about 10 m)". Pong draws both
     scores at scale 1 (pong.py:327-328), although a 14 px digit fits the 32 px wall.
   - X1's score_legible does not answer it. It looks at 1x and 2x (SCORE_SCALES) and judges at 5 m.
   - Measured legibility of a "3":
     - 1x: 0.984 at 5 m, 0.857 at 10 m (under the 0.9 min).
     - 2x: 1.000 at 5 m, 0.958 at 10 m.
   - Not blocking: it predates it07, and the plan's P3 says "Nothing else changes". Carry it: Pong's scores at 2x,
     or a score_legible at 10 m.
9. **`tools/arcade_evidence.py` CLI: works.**
   - `-m tools.arcade_evidence --iteration 7 --games pong --allow-dirty --seeds 5 --out <scratchpad>/it07-review-evidence`
     exits 0 in 14.75 s wall time and prints "a2e6681+dirty: 8 files".
   - The 8 files: feel.json, games.md, pong-128x32-{plain,led,distance}.png, -canonical.gif, -trace.jsonl and
     -timeline.txt (10 lines).
   - The GIF is 9,616 bytes and 256x64. Its 52 frames last 6,000 ms in total, because Pillow merges identical
     frames. Its comment is `a2e6681+dirty`.
   - The PNGs carry `git: a2e6681+dirty`, and so does games.md's header. The report has no failures.
10. **The freeze: matches the plan, and the canary works.**
   - The game.py diff holds only what the plan lists: REQUIRED_SCENARIOS, `fx: Juice` under TYPE_CHECKING, and the
     docstring (the `Any` import dropped). test_game.py:149 checks what the runner passes.
   - `test_protocol_members_are_the_frozen_set` (test_game.py:103) fails on each of four changes made to `Game`
     in memory, with the repository untouched: an added method, a renamed parameter (`update(self, sensed, delta)`),
     an added optional parameter, and an added annotation. It passes again once they are undone.
   - The canary checks the names of the other constants (`hasattr`), not their values.

## Checks (test counts and seconds, skipped, every removed or changed assert)
- The test command, run once from the repository root: 674 passed in 133.81 s, exit 0, 0 skipped (no "skip" in
  the -rs output).
- `--collect-only -q`: 674 tests collected, against 596 at the base: no drop.
- Removed or changed asserts in `git diff 6ddaf78..HEAD -- tests/`: the diff removes exactly one assert line.
  - tests/arcade/test_pong.py::test_registered_and_declared: `set(Pong.SCENARIOS) == {"solo", "duel"}` became
    `== {"solo", "duel", "canonical", "idle_body", "nobody"}`. Extended; still an equality.
- Changed within the range, in files new since 6ddaf78:
  - tests/arcade/test_bots.py::test_budget_file_parses_and_has_every_kind (X1): `idle_hint_seconds` added to
    METRICS, `score_visible` and `score_legible` to WINS. Extended.
  - tests/arcade/test_feel.py::test_measure_repeats_under_seeds (X1): the key set gained three names. Extended.
  - tests/arcade/test_all_games.py: the two `xfail(strict=True, reason="until P3")` marks were removed (4ede4a6).
    Strengthened: the tests now must pass.
  - tests/arcade/test_pong.py::test_idle_body_scores_nothing (P3, new): no `score == 0`. See ruling 3: weaker than
    its name, and no earlier assert was weakened.

## Noted, not carried (one line each, each starting REPRODUCED with its input and output, or READ)
- REPRODUCED: `feel._idle_hint(cfg, font, Pong, 4107362358)` gives 0.0. The differing pixels are the amber
  versus green seat colour, not a hint. This is B1.
- REPRODUCED: `response_ticks` for Pong on seed 4107362358 is 5.0 at PROBES 4 and at PROBES 16, and 2.0 at 8. The
  metric is at its max by probe placement (ruling 1).
- REPRODUCED: `bots.play(Pong, Good(), s)` over 20 seeds: every round ends at the 90 s cap, the human leading
  1 to 4 against 0, and 0 of 20 reach 5 (ruling 2).
- REPRODUCED: `run_headless(cfg, font, Pong, Pong.SCENARIOS["idle_body"](), seed=1842885004)`: the session ends
  "done" with score 1.0, and the pong best becomes 1.0 for a body that never moved (ruling 3).
- REPRODUCED: a KeypointHold walker (0.3 zone in 1 s, wrist dropped): the held wrist lands up to 9.0 px from the true one
  on the 128x32 figure for 0.5 s (ruling 6).
- READ: arcade/feel.py:294-307: `measure` feeds canonical straight to the game, lobby part included. game.py's
  docstring says that part "launch[es] the game from the lobby". Every game is therefore measured from an
  empty-wall launch the arcade never makes. That is why Pong needed 35ae954.
- READ: arcade/feel.py:39 `SCORE_SCALES = (1, 2)`: score_visible accepts 1x scores, so the oracle cannot flag spec
  7.4's 2x rule (ruling 8).
- READ: arcade/feel.py:220-236: score_visible's `find_text` takes the first match on the wall, so the other side's
  digit counts when it equals the score. Harmless for Pong, which draws both.
- READ: spec 9.2's "_xy lit" generic test is not in tests/arcade/test_all_games.py. The plan's P2 list omits it, so
  it is not a finding for it07.
- READ: arcade/bots.py:161 copies `debug_state()` shallowly. A future game that returns a list it mutates in place
  would show a delayed bot the present value. Pong returns tuples.
- READ: process slip by this reviewer: two of my commands began with a `cd` into the repository root, the directory
  the shell was already in (the evidence CLI run and one probe). Nothing in the repository was written.
