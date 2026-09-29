Decision: iteration 13 done. D4 landed: the test pattern goes through the flash governor, the soak tool runs the real show loop with buttons pressed by a timer (5 minutes on the full wall and 2 on 128x64, both clear), `systemctl stop` now stops the show with the wall black, and `bright-on-field` is the strip's default look (Q54); review APPROVED in 1 round with no blocking finding after a plan review that fixed two; two older safety gaps found and carried (C51 torn pushes, C52 the governor's first frame); suite green, 1140 collected, 1 skip.

# Evidence, iteration 13 (the test pattern and the soak; a safety slice)

Code head 418ef74; the sheets are stamped 418ef74, clean. They were made from a clean detached checkout of 418ef74
(verify-script.py.txt), because untracked folders of the owner's stand in the main checkout.

| file | what it shows |
|---|---|
| it13-strobe.png | the strobe session on the full wall, a frame every 150 ms, labels `held <n> area <a> sq <s>`: black, one lit frame at 4.2 s, five black cells while held rises to 10, then lit and still. Area 0.0000, square flashes at most 6 (the budget) |
| it13-presses-{led,plain}-p1..p9.png | the show itself on the full wall for 40 s, a frame a second, in nine pages: attract, the presses, the build with its warning, the band, the queued entry, the dwell, attract again. `held 0`, area at most 0.0214, square flashes at most 4. The strip is bright letters on a field |
| it13-presses-poc-p1/p2.png, it13-presses-poc-distance-p1/p2.png | the same on the 128x64 proof of concept (ink view): the short strip, held 20 by the end (Q60), area at most 0.0422, square flashes at most 3 |
| tiles/ | five tiles the operator cut and read: three of the full wall's 10 m pages (the strip reads), one of the strobe's 10 m page, `panels` at half size. The 10 m pages themselves (14 MB) are not committed; show-shot.txt's commands make them again |
| it13-panels.png | `wall_pattern.py panels --config show.toml`: 48 labels, `0,0` to `5,7`, one a panel |
| it13-grid-poc.png | `wall_pattern.py grid --config show.poc.toml`: a line every 8 pixels at 128x64 |
| show-shot.txt | the seven commands with their output and exits: the sessions' lines, `--cols 6` refused with exit 2, the two patterns, `grid` in the SDL preview for 2 s |
| stop.txt | `python -m show --backend fake`, SIGTERM after 5 s: exit 0, 0.06 s after the signal; the log's last lines |
| soak.txt, it13-soak/, it13-soak-poc/ | the two short soaks and their JSON reports: 5508 and 2246 steps, 0 push failures, 0 errors, 0 children left, square flashes at most 4 and 3, fds 4 to 4 |
| pytest.txt, collect.txt | the suite at 418ef74: 1140 collected, 1139 passed, 1 skipped, 230.68 s |
| orchestrator-report.md | the implement phase: I0, six tasks in two groups, the merges, the deviations |
| reviewer.md, review-probes/ | APPROVED; the close path under faults (p2), SIGTERM (p3), the broken show.toml (p4), fps (p5), the pattern tool (p6), the soak (p7), the meter (p8), the pages (p9), the strip (p11), the README's commands (p13), timing (p15) |
| plan-review.md, plan-review-round2.md, plan-review-probes/ | the plan review: BLOCKED on B1 and B2, both fixed in the plan, confirmed |
| plan-report.md, plan-fix-report.md | the plan writer's reports |

Open after this iteration: C51 and C52 (journal, "Carried forward"), Q63 to Q65 (decisions.md), and what waits for
the Pi and the panels (roadmap.md, "it13 (GATE C ...)").
