Decision: iteration 14 done. The flash governor's three gaps are closed for the show: after a failed push the wall holds still and then starts its governor again from the counted frame (C51), every wall starts counted against a dark wall (C52, the show's half), and the arcade refuses a gamma outside 1.0 to 2.2 (C50); review APPROVED in 1 round with no blocking finding after a plan review that fixed two; one gap was widened and is carried (C53, a stop within 0.7 s of a torn push); the owner's check of the card without packets is a safety gate (Q66); suite green, 1231 collected, 1 skip.

# Evidence, iteration 14 (the governor's three gaps; a safety slice)

Code head da20a3a; the sheets are stamped da20a3a, clean. They were made from a clean detached checkout of da20a3a
(verify-script.py.txt), because untracked folders of the owner's stand in the main checkout. With fakes no push
fails, so the hold shows on no sheet: its evidence is the tests and the two reviews' sweeps.

| file | what it shows |
|---|---|
| it14-strobe.png | the strobe session on the full wall, a frame every 150 ms: black, one lit frame at 4.3 s, five black cells while held rises to 8, two lit, three black. Area 0.0000, square flashes at most 6 (the budget), held 13 |
| it14-presses-{led,plain}-p1..p9.png | the show on the full wall for 40 s, a frame a second, nine pages: held 0, area at most 0.0272, square flashes at most 4, as in it13 |
| it14-presses-poc-{led,plain,distance}-p1/p2.png | the same on 128x64 (ink view): held 24 in this run, area at most 0.0560, square flashes at most 3 |
| presses-poc-idle.txt | the 128x64 session again on an idle machine, before the slice (b83045d: held 21, 18) and after it (da20a3a: held 20, 21): the number moves from run to run, the slice did not move it |
| it14-panels.png | `wall_pattern.py panels --config show.toml`: 48 labels, as in it13 |
| show-shot.txt | the six commands with their output and exits, the arcade's config load and the gamma bound (0.22 and 22.0 refused, 1.0 and 2.2 taken) among them |
| stop.txt | `python -m show --backend fake`, SIGTERM after 5 s: exit 0, 0.06 s after the signal |
| soak.txt, it14-soak/, it14-soak-poc/ | two soaks of 2 minutes and their JSON reports: 2199 and 2201 steps, 0 push failures, 0 errors, square flashes at most 4 and 3, held 0 and 7 |
| pytest-idle.txt, pytest.txt | the suite at da20a3a: 1231 collected, 1230 passed, 1 skipped; 234.60 s on the idle machine, 298.35 s beside the reviewer's sweeps |
| orchestrator-report.md | the implement phase: I0, T-wall, the merge, the deviations (the owner's PR 1 pulled in the middle of the run) |
| reviewer.md, review-probes/ | APPROVED; the tear sweep on the real wall at fps 20 and 30 (r1_sweep), repeated tears (p1), the re-init (p2), from dark and the gamma (p4), the close before and after the slice (p5, p5b, p5c), the `#` band with no tear (p6) |
| plan-review.md, plan-review-round2.md, plan-review-probes/ | the plan review: BLOCKED on B1 (the hold's end) and B2 (tests that ended before the hold), both fixed in the plan, confirmed; r6 is the card that blanks and the close |
| plan-report.md, plan-fix-report.md, plan-probes/ | the plan writer's reports and probes: why a torn push reads 7, why a resend every tick does not close it |
| verify-script.py.txt, verify-idle-script.py.txt | the operator's verify commands |

Open after this iteration: C53 and the arcade's half of C52 (roadmap.md, "Carried fixes"), Q66's check on the real
panels and Q67 (decisions.md), and the notes tagged "it14" in roadmap.md.
