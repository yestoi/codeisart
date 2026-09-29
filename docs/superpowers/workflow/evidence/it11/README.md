Decision: iteration 11 done. D2 landed: one entry plays end to end on the wall (source, real `cc -Wall`, real run, error hold, fallback recording, dwell), attract mode scrolls the sources, input, lights and audio have fakes; the sheets show it on the full wall and on the 128x64 ink view; review APPROVED after 2 rounds (one blocking finding, the sample entry's trail, fixed in 89e9259); suite green, 966 collected, 1 skip.

# Evidence, iteration 11 (one entry end to end)

Code head 14728d4; the sheets are stamped 14728d4, clean. They were made from a clean detached checkout of 14728d4,
because untracked folders of the owner's stand in the main checkout and the stamp counts untracked files as dirty.

| file | what it shows |
|---|---|
| it11-hello-{plain,led,distance}.png | `entries/hello` for real: title, plaque, `$ cat hello.c`, `$ cc -Wall` with the compiler's warning, `$ ./hello`, the band both ways, `hello, world` |
| it11-hello-fallback-{plain,led,distance}.png | the build made to fail with `-Werror`: the error, `*** build failed (exit 1) ***` held, `$ ./hello   (recording)`, the recorded band replayed |
| it11-attract-{plain,led,distance}.png | attract mode for 20 s: the banner, hello's header and source scrolling, the banner again after 40 lines |
| it11-hello-poc.png, it11-hello-poc-distance.png | the same entry on the 128x64 proof of concept (`show.poc.toml`, ink view): a cell a dot, no cursor, the strip cut to 21 characters |
| before-fix-it11-hello-{led,poc}.png, before-fix-show-shot.txt | the same at 72f0654, before the fix: the band leaves a wedge behind on its way back (the review's blocking finding) |
| show-shot.txt | the four commands, their phase times and exits |
| pytest.txt, collect.txt, head.txt | the suite at 14728d4: 966 collected, 965 passed, 1 skipped, 202.18 s |
| orchestrator-report.md, orchestrator-fix-report.md | the implement phase and the fix round |
| reviewer-round1.md, reviewer-round2.md | BLOCKED on one finding, then APPROVED |
| probe-p4_hello_trail.py.txt | the reviewer's probe of the trail |
| probe-p2_stop_raises.py.txt | the reviewer's probe for C49 (`Terminal.kill()` raising out of `EntryPlayer.stop()`) |
| plan-report.md | the plan writer's report |
