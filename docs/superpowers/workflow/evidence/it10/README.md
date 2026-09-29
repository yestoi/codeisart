Decision: iteration 10 done. D1 landed: the show daemon's terminal on the wall (renderer, terminal, entries, queue, recording, sandbox and `tools/show_shot.py`); the sheets show the strip on row 24 of every frame, the cursor, real `cc -Wall` output and a real pty scrolling inside 23 rows; review APPROVED in round 1; 888 collected, 887 passed, 1 skipped (the `unshare` test on macOS), 168.8 s. One finding for the owner: the strip in reverse video reads badly on LEDs (Q54).

# Evidence, iteration 10 (the show daemon's terminal on the wall)

Code head 0065293; the sheets are stamped ee5a9ce (HEAD at verify: 0065293 plus one commit of the workflow's state file),
clean. They were made from a clean detached checkout of ee5a9ce, because two untracked folders of the owner's stand in
the main checkout and the stamp counts untracked files as dirty.

| file | what it shows |
|---|---|
| it10-strip-{plain,led,distance}.png | attract and play strips on row 24; scrolling stays inside rows 1 to 23 |
| it10-edges-{plain,led,distance}.png | 80 `A`s with the cursor on the last cell; `?` for the block and CJK characters; bold, reverse; the hidden cursor |
| it10-fullscreen-{plain,led,distance}.png | a `full_screen` entry's row 24 with the strip hidden, then the strip over it |
| it10-cc-{plain,led,distance}.png | `cat`, the real `cc -Wall` warning, the program's output (fed as steps, not run in the pty) |
| it10-seq-{plain,led,distance}.png | `seq 1 60` in a real pty: 39 to 60 on rows 1 to 22, the cursor on row 23 |
| it10-prototype.png, it10-prototype-distance.png | the plan's crop `0,0,128,64`: 18 columns, 8 rows, no strip (the plan's command was wrong) |
| it10-prototype-window.png, -distance.png | the prototype's window `16,128,128,64`: 21 columns, rows 17 to 24 with the strip; the strip reads badly (Q54) |
| show-shot.txt | the commands and their exit codes |
| pytest.txt, collect.txt, head.txt | the suite at ee5a9ce: 887 passed, 1 skipped, 168.79 s; 888 collected |
| orchestrator-report.md, reviewer-round1.md, plan-report.md | the agents' reports |
| test_terminal_plan_exact_grace.py.txt | the plan's exact orphan test, which fails on macOS (bash hangs the orphan up); to run on Linux at GATE C |
