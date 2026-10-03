APPROVED: with `--game`, a locked player standing in the zone for 2 s starts the game; the default lobby is byte-identical.

# Iteration 23 (S4, the step-in start under --game; Q183, 2026-10-03)

- Code: 59c175a on main (arcade/attract/lobby.py, arcade/main.py, tests/arcade/test_lobby.py: +115, -15). Base 2e1585d.
- Plan: docs/superpowers/plans/2026-10-03-step-in-start.md (written outside the loop, reviewed 2026-10-03). Spec:
  docs/superpowers/specs/2026-10-03-step-in-start-design.md.
- Tests: 2386 collected at the base, 2395 after (+9, all in test_lobby.py). test_lobby.py 55 passed in 21 s; lobby and
  runner 144 passed in 26 to 29 s, no skips. The full suite ran in six parts (single runs stalled past 10 minutes at
  the first oracle test on this shared Mac, computing bot plays in-process); every part passed except two
  pre-existing governor tick-budget timing tests at 128x64 (strobe, static) that fail at the base too with the same
  medians (strobe 0.546 to 0.595 ms against 0.5; static at the 0.5 edge), and two tests/test_arcade_shot.py tests
  that fail only when pytest runs from outside the repo.
- Review (reviewer-it23, opus, 2e1585d..HEAD): APPROVED in one round. Probes outside the repo: the launch comes
  exactly 60 ticks after the first tick with a locked player; a re-lock under a new id restarts the count; the second
  launch comes 60 ticks after the card ends (mutants without the card-end reset, with an instant refire, with the
  raised hand as a second trigger, summing two bodies' time, or firing under 2 s each fail a named test); the default
  lobby gives identical raw frames and traces at the base and at HEAD on five scenes at three sizes; the limiter and
  governor path untouched; under REAL_NOISE in step-in mode the lobby's concurrent area stays at most 0.044 against
  0.1; no pictogram placed.
- Noted, not carried (the reviewer's): nothing pins the spec's "1.9 s does not start" (the 1.9 s scene covers 1.4 s of
  presence; the code fires at 2.0 s); the Review Focus 1 test passes without the new-id reset (the 1.0 s gap outlasts
  the grace; the code does reset); in step-in mode the card still reads "HAND UP = AGAIN" / "NEXT: RAISE A HAND",
  which contradicts the mode's reason (the spec kept the card as it is; an owner item for Night One); after an
  exit-gesture session a player who keeps standing gets the game again 2 s after the card.
- The commit's trailer names Claude Opus 5.5 (the orchestrator's session), the Claude-Session line as given.
