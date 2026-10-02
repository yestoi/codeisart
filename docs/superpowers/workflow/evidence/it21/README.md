Decision: iteration 21 done. Jump's words stand in one line under the figure and no word covers the player (C56 closed; 17 feel metrics, every budget met, no override); a camera source says what it provides (C35); M5's second lane is on main: the blobs and the motion grid wired into the MediaPipe source, `record` with its scripts and `--raw`, `calibrate`, the reader's range check, raw replay, `stats`, `run --replay` and `run --require`. Plan review: two rounds, the second's one finding fixed in the plan with the reviewer's text; code review APPROVED in round 1. One fix is carried: C57, Jump's hint leads the second and third windows. The suite was not run again in verify (the Mac was out of memory); the run after the last code merge stands: 2323 passed, 3 skipped, 454.57 s.

# Evidence, iteration 21 (C56, C35, M5's wiring, record, calibrate, raw replay, stats)

Code head d2f1b63 (the reviewed range is 42f2d40..d2f1b63). Jump's sheets are stamped `2fb3a04`, HEAD when they
were made; 2fb3a04 changes only `docs/` after d2f1b63. Made with
`.venv/bin/python tools/arcade_evidence.py --iteration 21 --games jump` on a clean tree. The record and calibrate
sheets were made with `python -m tools.arcade_shot` by the plan's I2 a minute later and are stamped `2fb3a04+dirty`:
the evidence tool's own text files were untracked beside them, no code differed.
Nothing here was run on the Pi or on the card. The images (`*-led.png`, `*-plain.png`, `*-distance.png`,
`*-canonical.gif`) are on the Mac beside this file and are not committed (Q98); what they show is said in words
below.

## Feel (games.md, feel.json; 128x64, 20 report seeds)

| metric | Jump | iteration 20 | budget |
|---|---|---|---|
| win_good / win_lazy / win_none | 1.0 / 0.45 / 0.0 | 1.0 / 0.45 / 0.0 | at least 0.7 / 0.1 to 0.7 / at most 0.05 |
| range | 0.685 | 0.685 | at least 0.6 |
| round_seconds | 30.0 | 30.0 | 20 to 120 |
| phases_reached | 1.0 | 1.0 | 1.0 |
| response_ticks / response_px | 1.0 / 216.0 | 1.0 / 197.5 | at most 2 / at least 12 |
| fidelity | 0.9991 | 0.9991 | at least 0.8 |
| lit_fraction / dim_fraction | 0.099 / 0.0 | 0.111 / 0.0 | 0.01 to 0.5 / at most 0.1 |
| liveliness | 0.0190 | 0.0181 | at least 0.001 |
| flash_area_raw | 0.0037 | 0.0024 | under 0.1 |
| square_flashes | 4.0 | 4.0 | at most 6 |
| score_visible / score_legible | 0.978 / 1.0 | 0.978 / 1.0 | at least 0.8 / 0.9 |

No failure. The game is iteration 20's; only the drawing moved (a 50-row figure, the words in a band).

## What the sheets show (read by the operator with the Read tool)

- `jump-128x64-led.png` (the canonical, 20 frames over 28.5 s; the player walks from the middle to the mat's left
  end, to its right end and back): the lobby's amber "JUMP", the mirror figure, the raised hand with the green
  launch icon. In the game: the cyan striker at the left with the yellow bell mark, the figure 50 rows tall, and
  every word in one amber line under the figure's feet: "JUMP!", "RING THE BELL!", "GET SET". No word touches the
  figure in any frame. The white score at 2x at the top right from the first tick ("0", then "42"), the white peak
  line on the bar, the result's amber "42" right of the bar.
- `jump-128x64-distance.png`: the band's 1x words, the "42"s and the bar's line read at viewing distance.
- The bell and `over` (the operator's sheets in the scratchpad, the same code): "DING!" pops beside the bar at the
  bell's height on a dimmed frame, clear of the band; `over` shows "BELL RUNG!" in the band under the engine's
  "NEW BEST". `idle_body`: "GET SET", "RING THE BELL!", an amber "0"; never two words at once.
- `jump-128x64-canonical.gif`: the Read tool gives its first frame only.
- What is not right yet (C57, carried; no budget fails): in the second and the third window the band shows "RING
  THE BELL!" from the window's first frame and "JUMP!" only after the jump, because the hint's idle clock is not
  reset when a window opens (`arcade/games/jump.py`, `_update_hint`). Beside it, a note: at the mat's left end the
  result's number is drawn over the figure's arm and legs.
- `record-led.png` (`door-point`, every 18 ticks, 12 s): a white "3", "2", "1" at 2x on a black wall; then a red
  "REC" at the top left with the seconds beside it on every frame; the cue in white across the middle ("STAND IN
  THE MIDDLE", "POINT AT DOOR 1", "HOLD", "HAND DOWN"); the performer's amber figure behind the words; the bottom
  rows dark.
- `calibrate-led.png` (every 45 ticks, 28.5 s): the step's words in white at the top ("AIM: HANDS UP", "STAND FAR
  LEFT", "STAND FAR RIGHT", "STAND AT THE FRONT", "STAND STILL", "CLEAR THE FRAME 10" counting down, "SAVED"); the
  body as green keypoint dots; the zone so far as a yellow outline; a lamp as a magenta dot that stays while a
  second light wanders through the clear step. The camera frame's own edge is not drawn (Q157).

## The suite (final-durations.txt)

| run | collected | passed | skipped | time | the pool |
|---|---|---|---|---|---|
| before the slice (6e8adf1's code, iteration 20's verify) | 2236 | 2233 | 3 | 457.24 s | 480 plays, 136.4 s |
| after the last code merge (4895b1f, the orchestrator) | 2326 | 2323 | 3 | 454.57 s | 480 plays, 135.6 s, waited 11.0 s |
| d2f1b63 (an import-order commit): the seven import-sensitive files | - | 131 | 0 | - | - |
| d2f1b63: the code reviewer's run of the iteration's 12 files | - | 333 | 0 | - | - |

The limit is 540 s (Q102). Verify did not run the full suite again: at 08:30 the owner reported the Mac out of
memory (8 GB, the swap nearly full), the full run is five Python processes for about eight minutes, and the only
code after the orchestrator's run is d2f1b63, which reorders imports in one file and was covered by the 131 and the
333 passed above; the reviewer's `--collect-only` at d2f1b63 reads 2326. The three skips are the base's (Linux
only). No timing test failed.

## Reviews

- Plan: `plan-review.md`. Round 1 BLOCKED on B1 to B7, fixed in the plan. Round 2 BLOCKED on one finding (R2-B1,
  wording the reviewer's own round 1 asked for) with three notes; the operator applied the reviewer's fix text and
  the notes and asked for no third round (a loop decision, journaled).
- Code: `code-review.md`. APPROVED in round 1, no blocking finding, 19 mutants (three survived, each harmless),
  the privacy rule read against spec 6.5. Five notes: calibrate can save with an empty static mask when the camera
  dies in the clear step's first seconds; the bell's `fx.flash` lights rows 60 to 63 through `fx.render`, as before
  this iteration; the privacy rule misses a bare `save` imported from numpy; a camera that dies during a recording
  leaves "REC" counting; "STAND FAR LEFT / RIGHT" where the spec says the far corners.

## Doctor

`.venv/bin/python -m arcade doctor` at 2fb3a04 on the Mac: camera ok (device 0, 1280x720), mic ok (540 samples),
pose ok (mediapipe, the landmarker ran in 17 ms).
