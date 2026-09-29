Decision: iteration 15 done, the run's last. The show's close after a failed push keeps the flash budget (C53 closed; review APPROVED in 1 round after a plan review that fixed two); the arcade's tracker faults are closed (C45, C46, C47) and Quick Draw, M7a's first game, is on main (review APPROVED after 3 rounds: two wrong bests found and fixed, B1 and N1); Dodge is built and reviewed but off main, because the suite with it stands at its limit of 330 s (Q77); the hand point was cut; suite green at 77c11d4, 1313 collected, 1 skip, 301.32 s.

# Evidence, iteration 15 (two lanes: the show's close, a safety task; the arcade's return)

Code head 77c11d4. The show's sheets and soaks are stamped 01bfd95, clean (nothing under `show/` changed after it);
the arcade's are stamped 77c11d4, clean. Each was made from a clean detached checkout (verify-script.py.txt,
verify-arcade-script.py.txt), because untracked folders of the owner's stand in the main checkout. With fakes no
push fails, so the close's wait shows on no sheet: its evidence is the 16 tests and the two reviews' sweeps.

| file | what it shows |
|---|---|
| arcade/games.md, arcade/feel.json | the feel table at 77c11d4: Quick Draw and Pong, every metric in its band, no failure; Pong's row equals it09's |
| arcade/quickdraw-128x64-{plain,led,distance}.png, -canonical.gif, -timeline.txt, -trace.jsonl | Quick Draw's canonical play: the lobby, WAIT, TOO SOON, DRAW! with the reaction time, the card |
| arcade/it15-quickdraw.png, arcade/it15-quickdraw-raw-vs-pushed.png | the play through the small lobby for 60 s, and ticks 835 to 874 raw beside pushed: the full-wall white flash on the signal (raw white, pushed mid grey, 5 ticks; Q76); held 0, flash area 0.000, square flashes 4 of 6 |
| arcade/pong-128x64-* | Pong at 77c11d4, as it09 |
| arcade.txt | the evidence commands with their output and exits; `python -m arcade doctor` from the main checkout exits 0 (camera, mic, pose ok) |
| dodge-83fe13a/ | Dodge while it was on main (83fe13a): its feel table (in band), sheets, GIF, the raw-vs-pushed sheet, the commands; for its return |
| it15-strobe.png | the strobe session on the full wall, a frame every 150 ms: area 0.0000, square flashes at most 6 (the budget), held 9 |
| it15-presses-{led,plain}-p1..p9.png | the show on the full wall for 40 s, a frame a second, nine pages: held 0, area at most 0.0209, square flashes at most 4 |
| it15-presses-poc-{led,plain,distance}-p1/p2.png | the same on 128x64 (ink view): held 22, area at most 0.0536, square flashes at most 3 |
| show-shot.txt | the sheet commands with their output and exits |
| stop.txt | `python -m show --backend fake`, SIGTERM after 5 s: exit 0, 0.06 s after the signal (no failed push, so the close does not wait) |
| soak.txt, it15-soak/, it15-soak-poc/ | two soaks of 2 minutes and their JSON reports: 2196 and 2203 steps, 0 push failures, 0 errors, square flashes at most 4 and 3, held 0 and 9 |
| pytest-idle.txt | the suite at 77c11d4 in the main checkout: 1312 passed, 1 skipped, 301.32 s (load 4.5 to 11.6 from the desktop; the orchestrator's run on the same tree: 281.71 s) |
| pytest-idle-with-dodge.txt | the suite with Dodge in a scratch worktree: 1364 passed, 2 skipped, 335.87 s, over the limit of 330 s |
| orchestrator-report.md, orchestrator-report-n1.md | the implement phase (I0, E1, E2, G1, G2, I1, T-close, the fix B1) and the fix N1, with the deviations |
| reviewer-close.md, review-close-probes/ | lane B, APPROVED: 178,236 closes on the real wall (s1 to s4), the real stop with real sleeps and signals (realclose), the exact tests against the plan (exact_compare), the wall before the fix (sanity_oldwall) |
| reviewer-arcade.md, reviewer-arcade-round2.md, reviewer-arcade-round3.md, review-arcade-probes/ | lane A: BLOCKED on B1, then on N1, then APPROVED; the DRAW flash measured (probe_5b_flash), the tracker (probe_engine), the leave (probe_qd_leave, probe_r2_leave), the stranger (probe_r2_stranger, probe_r3_stranger), the hanging hand without hips (probe_qd_hipless), Dodge (probe_dodge) |
| plan-review.md, plan-review-round2.md, plan-review-probes/ | lane B's plan review: BLOCKED on B1 (no re-init before the black: the wall ends lit) and B2 (a wait that reads the clock again hangs the stop), both fixed in the plan, confirmed |
| plan-close-report.md, plan-close-fix-report.md, plan-close-probes/, plan-arcade-report.md, plan-arcade-probes/ | the two plan writers' reports and probes |
| verify-script.py.txt, verify-arcade-script.py.txt, verify-suite-script.py.txt | the operator's verify commands |
| state-checks-after-44a9dd2.txt | the operator's checks from 10:54 to the gate (the earlier ones are in state.md at 44a9dd2) |

The full wall's 10 m pages (`it15-presses-distance-p*.png`, `it15-strobe-distance-p*.png`) are not committed, as in
it13 and it14; show-shot.txt's commands make them again.

Open after this iteration: the arcade's half of C52 (roadmap.md, "Carried fixes"), Dodge's return and the suite's
time, the hand point, Q66's check on the real panels (a safety gate), Q68 to Q78 (decisions.md), and the notes
tagged "it15" in roadmap.md.
