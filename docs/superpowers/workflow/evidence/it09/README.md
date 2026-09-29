Decision: iteration 9 done. M4c landed: Pong's paddle follows the body's distance from the camera (step in = up, step back = down), a rally counts by the paddle's travel, the card says "BEST!" only for a new best above 0, and the tracker's scale holds through a hip dropout (added from the owner's hand-read spike); Pong passes all 16 budgets at 128x64 with `response_px` at its floor; C42, C43 and C44 closed; C45, C46 and C47 carried. The loop gates here (Q42) and the operator moves to the show daemon.

# Evidence, iteration 9 (Pong by the body)

- **HEAD at verify:** 36a67ed (head.txt). The code's last commit is e42b02e; 36a67ed adds only the operator's state.md. `feel.json`, `games.md` and the stamped PNGs carry 36a67ed and were made from a clean tree (`git status --short` printed nothing before and after the sheets).
- **Plan:** docs/superpowers/plans/2026-09-28-it09-pong-by-the-body.md (8ae1aea), 299 lines, and its amendment docs/superpowers/plans/2026-09-28-it09-amendment-scale-hold.md (441564e, task S3, Q48). Not a safety slice, so no plan review.
- **Implementation review:** APPROVED in round 1, 0 blocking (reviewer-round1.md). The orchestrator's report, with its 16 deviations and every changed assert, is orchestrator-report.md.
- **Diff:** 8ae1aea..e42b02e, 27 files, 1440 lines added, 168 removed. `arcade/flash.py`, `arcade/brightness.py` and `show/display/colorlight.py` are unchanged; `arcade/runner.py` gains `SessionResult.new_best` and one read of the best at launch (9 lines), the order limiter, governor, push is unchanged.

| Check | Result | File |
|---|---|---|
| Collected | 762 (it08: 723) | collect.txt |
| Test command | 762 passed, 0 skipped, 172.8 s at load 2.0 (it08: 139.7 s; the plan's limit 175 s) | pytest.txt |
| Changed asserts in 8ae1aea..e42b02e | listed one by one by the review, none a weakening that hides a fault | reviewer-round1.md |
| `arcade doctor --require camera,pose` | camera ok (device 0, 1280x720), pose ok (landmarker 15 ms), exit 0 | doctor.txt |
| Evidence tool | exit 0, 8 files | games.md |
| Pong's feel at 128x64, 20 seeds | 16 budgets, `failures` empty | feel.json |
| Strobe check, lobby plus Pong duel, 3000 ticks | held 0; `flash_area` raw 0.002, pushed 0.002; `concurrent_area(pushed)` 0.010 of 0.1; `square_flashes(pushed)` 2 of 6; 3000 frames, none black; exit 0 | strobe-check.txt |
| Raw against pushed, 40 ticks at the largest raw change | the card to the mirror at t802, raw and pushed alike | it09-strobe-raw-vs-pushed.png |
| Canonical sheet, plain, LED look and at 5 m | title, mirror, raised hand, the hint at the first serve, the paddle over its whole travel, a round to 0-5 in 15 s, the card without "BEST!" | pong-128x64-plain.png, -led.png, -distance.png |
| Canonical GIF | 14.8 KB; first frame read, motion not judged by eye | pong-128x64-canonical.gif |
| Timeline and trace of the canonical run | attract 0.03, invite 3.53, launch 5.53, serves from 7.73, points from 13.07, lobby 22.50 | pong-128x64-timeline.txt, -trace.jsonl |
| Walk-up sheet, 100 s through the small lobby | one session, then the mirror and the pictogram for 75 s (the script steps, it does not raise a hand again) | it09-walkup-plain.png, -led.png, -distance.png |
| `arcade run` with no size given | logs "wall 128x64, backend sdl", exit 0 | run-default.txt |

## Pong's feel table (from feel.json)

| Metric | Value | Budget | Margin | it08 (the hand) |
|---|---|---|---|---|
| response_ticks | 1.0 | at most 2 | fair | 1.0 |
| response_px | 12.0 | at least 12 | **none**: per probe 6, 12, 4, 6, 12, 18, 18, 12 | 28.0 |
| fidelity | 0.995 | at least 0.8 | wide | 0.994 |
| range | 0.629 | at least 0.6 | thin (a 16 px paddle's ceiling is 0.762) | 0.762 |
| lit_fraction | 0.039 | 0.01 to 0.5 | fair | 0.026 |
| dim_fraction | 0.115 | at most 0.3 (Pong's own, the dim net) | fair | 0.153 |
| liveliness | 0.0035 | at least 0.001 | fair | 0.0026 |
| flash_area_raw | 0.0 | at most 0.1 | wide | 0.0 |
| square_flashes | 0 | at most 6 | wide | 0 |
| score_visible | 1.0 | at least 0.8 | wide | 0.974 |
| score_legible | 1.0 | at least 0.9 | wide | 1.0 |
| phases_reached | 1.0 | at least 1.0 | met | 1.0 |
| round_seconds | 66.1 | 20 to 120 | fair (2 of 20 good rounds end at the 92 s cap) | 46.6 |
| win_good | 1.0 | at least 0.7 | wide | 1.0 |
| win_lazy | 0.25 | 0.1 to 0.7 | fair | 0.55 |
| win_none | 0.0 | at most 0.05 | met | 0.0 |

`presence_answer_seconds` 0.0 is measured with no budget. No band in `arcade/feel_budgets.toml` or Pong's feel file was loosened; Pong's feel file changes only `[fidelity] input` to "far".

## The control, measured (simulated; the live lag is not measured)

| Measure | Value | From |
|---|---|---|
| A step to 90 percent of the paddle's travel, 10 captures a second, clean camera | 0.267 s (first pixel 0.100 s) | P1 |
| The same with 0.15 s of camera latency (REAL_NOISE) | 0.433 s (first pixel 0.267 s) | P1 |
| At 30 captures a second, clean; with 0.15 s latency | 0.100 s; 0.267 s | P1 |
| A still body's paddle under real noise, 10 seeds of 60 s | range at most 9.6 px; about 9 one-pixel moves a second | P1 |
| A still body's worst travel in a rally, against the 14.4 px that counts | 8.3 px; nothing banks on 10 seeds of 10 | P1 |
| A still body pinned at an end through the recentring | worst 14.74 px on 1 noise seed of 250 (the next 14.03, median 9.6) | the review's probe |
| The scale through a hip dropout, the spike's proportions | 0.39 on every capture (before S3: down to 0.24); `Depth` holds 0.5 | S3 |
| A track born without hips whose hips then appear | the paddle moves 24 px by itself, once (C47) | the review's probe |

## Not shown by this evidence
- A real body on the camera: lag, shimmer, whether both ends are reachable, whether the hint is understood. The owner's second live smoke (live-smoke.md) judges them.
- The Depth test through a hip dropout uses a body without noise; the spike's recordings were not replayed through the tracker.
