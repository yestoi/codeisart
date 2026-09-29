Decision: iteration 12 done. D3 landed: the show runs by itself (attract, presses, the queue, the strip's texts and three looks, the static error frame, the watchdog), and every frame passes the flash governor before the push (Q50); review APPROVED in 1 round with no blocking finding after a plan review that fixed seven; a strobing entry is held to the budget (rendered flash area 0.898, pushed 0.000); suite green, 1064 collected, 1 skip.

# Evidence, iteration 12 (the show runs; a safety slice)

Code head 245cb57; the sheets are stamped 245cb57, clean. They were made from a clean detached checkout of 245cb57,
because untracked folders of the owner's stand in the main checkout and the stamp counts untracked files as dirty.

| file | what it shows |
|---|---|
| it12-presses-{led,plain}.png | the show itself on the full wall for 40 s, a frame a second: attract, a press (`PLAYING`), a second press (`QUEUED #1`), the real build with its warning, the band with `NEXT: hello-2 (1 queued)`, the queued entry starting by itself, the dwell, attract again; `held 0` throughout. One column, 32076 px tall |
| it12-presses-distance-4s-to-6s.png | three frames of the same at the 10 m look, cut by the operator from the 13 MB sheet (not committed): the body text reads, the `reverse` strip reads badly |
| it12-presses-poc.png, it12-presses-poc-distance.png | the same session on the 128x64 proof of concept (ink view): the short strip alternates, the notices fill it; the governor holds parts of the ink view while source scrolls (held 21 by the end; Q60) |
| it12-strips-{led,plain,distance}.png | the three looks of the strip on the full wall (Q54): `reverse`, `dim-reverse`, `bright-on-field` |
| it12-strips-row.png, it12-strips-row-distance.png | the strip's row alone, the three looks one above the other |
| it12-strips-poc.png, it12-strips-poc-distance.png | the three looks on 128x64, both halves of the alternating strip |
| it12-strobe.png | the strobe session, a frame every 100 ms. The sampling falls on the strobe's own period, so the sheet shows no flicker either way; read strobe-measure.txt |
| strobe-measure.txt, strobe-measure.py.txt | the operator's measure of the strobe session, every step kept: rendered flash area 0.898 (15 square flashes), pushed 0.000 (6, the budget); on 128x64 0.765 (14) and 0.000 (6) |
| show-shot.txt | the six commands, the strip's text and the held ticks of every frame, the exits |
| pytest.txt, collect.txt, head.txt | the suite at 245cb57: 1064 collected, 1063 passed, 1 skipped, 231.39 s |
| orchestrator-report.md | the implement phase: seven tasks, the merges, the deviations |
| reviewer.md, review-probes/ | APPROVED; the repush path under failing displays (p3), the fallbacks and raising `apply` (p5), C49 (p11), the default look byte-identical (p13), the sheet tool's tests five times (p14) |
| plan-review.md, plan-review-round2.md, plan-review-probes/ | the plan review: BLOCKED on B1 to B5, then B6 and B7; all fixed in the plan |
| plan-report.md, plan-fix-report.md | the plan writer's reports |

Not done in this iteration: show.toml's `strip_look` still says `reverse` (see the journal, "Loop decisions"); the
loop's reading is `bright-on-field`, and iteration 13 makes it the default.
