Decision: iteration 1 done. M1 complete; continue to iteration 2 (carried fixes plus M2's first slice). No owner decision needed.

# Evidence, iteration 1 (M1: environment spike, show foundation, arcade config)

- HEAD at verify: 040ff3f (recorded by hand in head.txt; no PNGs exist before M4, so the freshness check is this sha against `git rev-parse --short HEAD`, which matched)
- Plan: docs/superpowers/plans/2026-09-27-it01-environment-foundation.md
- Review: APPROVED, round 1 (reviewer-verdict.md)

| Check | Result | File |
|---|---|---|
| Collected | 66 tests collected | collect.txt |
| Test command | 66 passed, 0 skipped | pytest.txt |
| env_check | PoseLandmarker VIDEO mode ran, 12.1 ms/frame; 17 SDL duplicate warnings, no crash; README rewrite differed only in timing, restored | env_check.txt |
| doctor --require pose | ok, exit 0 | doctor-pose.txt |
| doctor --require camera,mic,pose | camera 1920x1080 ok, mic ok, pose ok, exit 0 (terminal already has camera and mic permission) | doctor-all.txt |
| One OpenCV | opencv-contrib-python 5.0.0.93 only | opencv.txt |

No games exist yet, so there are no sheets, GIFs or feel metrics to judge this iteration.
