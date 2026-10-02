Decision: iteration 20 done. Jump is on main and reads as a game at 128x64 (17 feel metrics, every budget met, no override), so M7a's seven pose games are all built; Copy Me's outline is magenta and shows on player 2 (C55 closed); the suite has room again (505.09 s before, 457.24 s after with Jump and 144 more tests, limit 540 s); M5's first lane (blobs with ids, the gated motion grid, scenario files and replay) is on main, not yet wired into a camera source. Plan review approved in round 2 (four blockers fixed in the plan), code review APPROVED in round 2 (five blockers fixed: B1 to B5). One fix is carried: C56, Jump's words sit over the figure.

# Evidence, iteration 20 (the suite's room, Jump, C55, Blob ids, M5's blobs and scenario files)

Code head 6e8adf1 (the reviewed range is 24e2aee..6e8adf1). The sheets are stamped `14dd073`, HEAD when they were
made; 14dd073 changes only `docs/` after 6e8adf1. Made with
`.venv/bin/python tools/arcade_evidence.py --iteration 20 --games jump,copyme` on a clean tree.
Nothing here was run on the Pi or on the card. The images (`*-led.png`, `*-plain.png`, `*-distance.png`,
`*-canonical.gif`) are on the Mac beside this file and are not committed (Q98); what they show is said in words
below.

## Feel (games.md, feel.json; 128x64, 20 report seeds)

| metric | Jump | Copy Me | budget |
|---|---|---|---|
| win_good / win_lazy / win_none | 1.0 / 0.45 / 0.0 | 1.0 / 0.4 / 0.0 | at least 0.7 / 0.1 to 0.7 / at most 0.05 |
| range | 0.685 | 0.701 | at least 0.6 |
| round_seconds | 30.0 | 24.0 | 20 to 120 |
| phases_reached | 1.0 | 1.0 | 1.0 |
| response_ticks / response_px | 1.0 / 197.5 | 1.0 / 280.0 | at most 2 / at least 12 |
| fidelity | 0.9991 | 0.9996 | at least 0.8 |
| lit_fraction / dim_fraction | 0.111 / 0.0 | 0.108 / 0.0 | 0.01 to 0.5 / at most 0.1 |
| liveliness | 0.0181 | 0.0177 | at least 0.001 |
| flash_area_raw | 0.0024 | 0.0110 | under 0.1 |
| square_flashes | 4.0 | 4.0 | at most 6 |
| score_visible / score_legible | 0.978 / 1.0 | 0.978 / 1.0 | at least 0.8 / 0.9 |

No failure in either game. Jump's numbers are the same before and after the review's fixes (the fixer compared them
at full precision).

## What the sheets show (read by the operator with the Read tool)

- `jump-128x64-led.png` (the canonical, 20 frames over 30 s): the lobby's amber "JUMP", the mirror figure, the
  raised hand with the green launch icon. In the game: a cyan striker frame at the left with a yellow bell mark,
  "GET SET" in `ready`, a big amber "JUMP!" for the whole 5 s window, the white score at the top right at 2x from
  the first tick ("0", then "42"), a white line on the bar at the jump's peak, the result's big amber "42" beside
  the bar, three attempts, then `over`.
- A close sheet of the first two attempts (every 5 ticks, in the scratchpad): the bar fills amber to the bell mark
  as the body rises, one full-frame light grey flash frame when the bell rings (6.83 s and 15.83 s), then a dimmed
  frame with "DING!" for about 0.3 s.
- `jump-128x64-distance.png`: "JUMP!", "GET SET", the "42"s and the bar's line read at viewing distance.
- `idle_body` (scratchpad): a stander sees "GET SET", "JUMP!" with the hint, then an amber "0"; nothing is banked.
- `jump-128x64-canonical.gif`: the Read tool gives its first frame only (the lobby's figure and the launch icon).
- `copyme-128x64-led.png`: the game as in iteration 19 with the target's outline in magenta on the amber figure.
- Copy Me's `duo` sheet (scratchpad, 12 frames over 20 s): the magenta outline stands out on seat b's blue figure as
  on seat a's amber one, in `show`, `play` and `result`.
- What is wrong with Jump's picture (C56, carried; no budget fails): the words "GET SET" and "JUMP!" are drawn over
  the figure's torso for the whole window; the idle hint is a second, small "JUMP!"; "DING!" pops onto the big
  "JUMP!"; at the zone's left end the figure covers the striker and the result's number; `over` has no word.

## The suite (verify-suite.txt, final-durations.txt, r-durations.txt, orient-durations.txt)

| run | collected | passed | skipped | time | the pool |
|---|---|---|---|---|---|
| before the slice (24e2aee, orient) | 2092 | 2089 | 3 | 505.09 s | in the oracle's setup, 89.92 s |
| the gate after R (019d434) | 2096 | 2093 | 3 | 402.71 s | 420 plays, 109.2 s, the join waited 10.7 s |
| after the last merge (b3ff645) | 2188 | 2185 | 3 | 440.51 s | 480 plays, 130.2 s, waited 9.4 s |
| verify, after the review's fixes (14dd073) | 2236 | 2233 | 3 | 457.24 s | 480 plays, 136.4 s, waited 13.9 s |

The limit is 540 s (Q102). The verify run ran beside the re-review's probes (load 4.2 at its start, 6.5 at its end).
The pool's deadline is 180 s a share (Q124); its time is under the 150 s flag. The three skips are the base's
(Linux only). No timing test failed in any run.

## Reviews

- Plan: `plan-review.md`. Round 1 BLOCKED on B1 to B4 (an unnamed changed assert, a missing `score` key, a round
  under 20 s, a canonical range of 0.598), fixed in the plan; round 2 APPROVED.
- Code: `code-review.md`. Round 1 BLOCKED on five findings, each shown by a probe: B1 Jump's figure lit rows 60 to 63
  in a jump under real noise; B2 a player who took over mid-window was measured against the earlier player's
  baseline and banked a height without a jump; B3 a deeply nested line raised out of the scenario reader and a
  non-finite box reached a game and crashed it; B4 F1's colour test passed on the fault it names; B5 Jump dropped
  `fx.flash`'s return. Fixed in f2197ed, 1bb54c0 and 001d4d9 (`fix-report.md`). Round 2 APPROVED: the reviewer's
  probes read 0 of 40 ids, [0, 0, 0] for the swap, no raise and no crash for the two files, the test failing on the
  mutant, the return used. Four asserts changed in the range, all named by the plan; none removed or weakened.

## Doctor

`.venv/bin/python -m arcade doctor` at 14dd073 on the Mac: camera ok (device 0, 1280x720), mic ok, pose ok
(mediapipe, the landmarker ran in 30 ms).
