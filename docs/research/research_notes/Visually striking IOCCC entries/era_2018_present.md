# Visually striking IOCCC winners, 2018 to present (25th to 29th IOCCC)

Scope and method. Primary source is the official winner repository (`github.com/ioccc-src/winner`, cloned 2026-09-28, last commit 2026-09-28), which is the source of ioccc.org. Every entry page follows the pattern `https://www.ioccc.org/<year>/<dir>/index.html`. On top of reading the READMEs, I compiled and ran the main candidates myself on 64-bit ARM Linux: Docker `gcc:12` (gcc 12.5.0, aarch64) with `-std=gnu17 -Wall -O2`. I ran each one inside a real pty sized with `stty rows 23 cols 80` and replayed the captured output through a terminal emulator (pyte) to get 80x23 snapshots. I also compile-checked the top candidates on `gcc:14` (14.4.0) under `-std=gnu17` and `-std=gnu23`. These are "local tests" below. Caveat: the container ran on an Apple-silicon Mac, which is much faster than a Raspberry Pi 4, so run times and frame rates for CPU-heavy entries are not representative of the Pi. Link text for local tests points to each entry's official page.

Contest numbering (verified from each year's index page): 2018 = 25th, 2019 = 26th, 2020 = 27th, 2024 = 28th, 2025 = 29th ([2018](https://www.ioccc.org/2018/index.html), [2019](https://www.ioccc.org/2019/index.html), [2020](https://www.ioccc.org/2020/index.html), [2024](https://www.ioccc.org/2024/index.html), [2025](https://www.ioccc.org/2025/index.html)). No contests were held for 2021-2023.

## Which 2018+ winners are most famous for visual output or source shape?

### Takeaway
Yusuke Endoh is the most prolific visual author of this era, with three of the four standout 80-column terminal pieces: the 2020 Star Wars crawl, the 2020 mirror-clock quine and the 2024 spinning-top simulator. The 29th IOCCC (2025, announced June 2026) drew the most press for shaped source: the GameBoy-shaped GameBoy emulator (ncw1), the TARDIS-shaped Doctor Who titles (jingp49), Quine Pong (uellenberg), the lightning-bolt Lichtenberg generator (endoh2) and the punch-card black hole (cesmoak). Several of the most photogenic shaped sources need color, big windows, X11/SDL or keyboard input, so they suit a portrait but not the wall.

### Cited Findings
**Most-publicized visual entries**
- Slashdot's June 7, 2026 story on the IOCCC29 winners singled out the GameBoy emulator "formatted to resemble a GameBoy", Quine Pong, the Doctor Who entry with "formatted source code in the shape of a Tardis" showing ASCII animations of the 1963 opening, the black-hole punch-card simulator, and the Casio MG-880 invaders game — [Slashdot](https://developers.slashdot.org/story/26/06/07/1730236/winners-announced-in-2026s-international-obfuscated-c-code-competition)
- Hackaday (Maya Posch, June 9, 2026) highlighted Endoh's "Most likely to shock", which "generates a Lichtenberg figure in ASCII in the terminal", and the GameBoy emulator ("just do not expect ... fancy terminal-based graphics") — [Hackaday](https://hackaday.com/2026/06/09/the-winners-of-the-2025-obfuscated-c-code-contest/)
- On the Hacker News thread for the 29th IOCCC, a commenter called the GameBoy emulator their favorite: "The GameBoy emulator's code also looks like the GameBoy. Slow clap this is insane." — [HN](https://news.ycombinator.com/item?id=48432199)
- The judges' own "notable and remarkable" list for IOCCC29 includes cable (Subleq), cesmoak (black-hole punch-card Fortran), endoh3, jhshrvdp (rogue-like), jingp49 (Dr. WHO), ncw1 (GameBoy), tompng (ocean sound), uellenberg (Quine Pong) and yang2 (Zoltraak) — [IOCCC 2025 page](https://www.ioccc.org/2025/index.html)
- IOCCC29 had "a Hat trick of Hat-tricks": three wins each for Yusuke Endoh, Nick Craig-Wood and Don Yang — [IOCCC 2025 page](https://www.ioccc.org/2025/index.html)

**Visual-output entries, 2018-2020 (from the READMEs)**
- 2020/endoh2 "Best perspective" (Yusuke Endoh, JP): a Star Wars opening-crawl renderer; `./prog` or `./prog file.txt` (yoda.txt, bear.txt, hello.txt). The judges point to an obfuscation directory showing "how some winning authors create / edit programs into ASCII shapes" — [2020/endoh2](https://www.ioccc.org/2020/endoh2/index.html)
- 2020/endoh3 "Most head-turning" (Endoh): an ASCII clock. "Prepare a mirror!" The clock is mirrored and the program must be recompiled on each run (`run_clock.sh` loops compile, run and `tee clock.c`) — [2020/endoh3](https://www.ioccc.org/2020/endoh3/index.html)
- 2018/endoh2 "Best use of python" (Endoh): a "Monty-Pythonesque animated quine". The source shape is an "Undead Parrot", and the program cycles Party Parrot frames by recompiling its own output — [2018/endoh2](https://www.ioccc.org/2018/endoh2/index.html)
- 2018/poikola "Most stellar" (Timo Poikola, FI): an Ursa Major ASCII animation that needs "24 bit color, has black background, and size at least 125x38" — [2018/poikola](https://www.ioccc.org/2018/poikola/index.html)
- 2018/giles "Most unstable" (Edward Giles, AU): an SDL falling-sand simulation. "The code is laid out graphically as a bucket pouring sand" — [2018/giles](https://www.ioccc.org/2018/giles/index.html)
- 2018/endoh1 (Endoh) turns text into an animated GIF, so its output is a file — [2018/endoh1](https://www.ioccc.org/2018/endoh1/index.html)
- 2019/dogon "Best use of space and time" (Gil Dogon): an X11 Golly Game of Life. The judges wrote that it "likely concludes the IOCCC category 'Cellular automata simulators'" — [2019/dogon](https://www.ioccc.org/2019/dogon/index.html)
- 2020/carlini "Best of Show - abuse of libc" (Nicholas Carlini): tic-tac-toe built from a single `printf` in a loop. "A clue to what is happening ... is encoded in the ASCII art of the program source" — [2020/carlini](https://www.ioccc.org/2020/carlini/index.html)
- 2020/tsoj (Asteroids, keyboard-driven, "make your terminal as large as possible") and 2020/ferguson1 (Snake, arrow keys) are visual terminal games, but both need live input — [2020/tsoj](https://www.ioccc.org/2020/tsoj/index.html), [2020/ferguson1](https://www.ioccc.org/2020/ferguson1/index.html)

**Visual-output entries, 2024 (28th) and 2025 (29th)**
- 2024/endoh1 "patient pointillism": a ray tracer written in the C preprocessor that renders one pixel per compile into image files, with sample PNGs at 8 to 512 px. A 512x512 render is slow, and the judges estimate that the largest possible image would take "169 billion years" — [2024/endoh1](https://www.ioccc.org/2024/endoh1/index.html)
- 2024/endoh2 "solid body physics": a rotating rigid-body (spinning top) simulator. Width and height are compile-time parameters (defaults 120x24), and it ships body files such as top.txt, tippe-top.txt and vase.txt; "even `prog.c`" works as a shape file — [2024/endoh2](https://www.ioccc.org/2024/endoh2/index.html)
- 2024/codemeow "tray planting" (Codemeow, KG): a bonsai generator "inspired by `cbonsai`" that "does not use ncurses" — [2024/codemeow](https://www.ioccc.org/2024/codemeow/index.html)
- 2024/tmarrec "cyclonic coding" (Tristan Marrec, CA): a 3D fluid tornado with a semi-Lagrangian solver and ray-marched rendering — [2024/tmarrec](https://www.ioccc.org/2024/tmarrec/index.html)
- 2024/tompng "quasi bijection" (tompng, JP): a "visual vortex encryptor/decryptor ... You can visually see how this program stirs the text" — [2024/tompng](https://www.ioccc.org/2024/tompng/index.html)
- 2024/kurdyukov1 "phased periodicity" (Ilya Kurdyukov, RU): "draws the current moon phase to the console" — [2024/kurdyukov1](https://www.ioccc.org/2024/kurdyukov1/index.html)
- 2024/weaver "Sur prize" (Vince Weaver): a Rickroll that "requires a terminal emulator that supports 24-bit ANSI colors" and pipes sound to `aplay` — [2024/weaver](https://www.ioccc.org/2024/weaver/index.html)
- 2024/kurdyukov3: a Doom-capable VM that renders through X11, with an SDL2 alternative — [2024/kurdyukov3](https://www.ioccc.org/2024/kurdyukov3/index.html)
- 2025/jingp49 "Who won award" (jingp49, Taiwan, "a new location"): "an ASCII animation resembling the 1963 Doctor Who title sequence", run as `./prog width height` — [2025/jingp49](https://www.ioccc.org/2025/jingp49/index.html)
- 2025/endoh2 "Most likely to shock": Lichtenberg discharge. "Take a look at the source code -- it is shaped like a lightning bolt itself." Current intensity is shown with "terminal escape sequence brightness" — [2025/endoh2](https://www.ioccc.org/2025/endoh2/index.html)
- 2025/endoh1 "Most likely to dazzle": a Nixie-tube text illuminator for 256-color terminals. Its try.sh wants a 336x34 terminal — [2025/endoh1](https://www.ioccc.org/2025/endoh1/index.html)
- 2025/uellenberg "Ping pong prize" (Jonah Uellenberg): "Running the program produces the source code to generate the next frame, formatted to display the current frame" — [2025/uellenberg](https://www.ioccc.org/2025/uellenberg/index.html)
- 2025/ncw1 "Best real emulator" (Nick Craig-Wood, GB): a terminal GameBoy emulator that needs UTF-8 block elements, xterm-256color and "a terminal window set to at minimum 160x73" — [2025/ncw1](https://www.ioccc.org/2025/ncw1/index.html)
- 2025/ncw2 "Best fractional emulator": a C64 emulation in FRACTRAN that runs the `10 PRINT` maze. It wants UTF-8, 24-bit color and a 40x25 window — [2025/ncw2](https://www.ioccc.org/2025/ncw2/index.html)
- 2025/cesmoak "Retro space award" (Chris Smoak): a black-hole render through a punch-card Fortran pipeline that outputs PGM images. `try.sh` "might take 9 - 18 hours" — [2025/cesmoak](https://www.ioccc.org/2025/cesmoak/index.html)
- 2025/yang2: "Code layout is based on Fern from 'Sousou no Frieren'" — [2025/yang2](https://www.ioccc.org/2025/yang2/index.html)

**Source-as-art silhouettes I confirmed by viewing prog.c (links to source)**
- 2020/endoh3: a 79x23 round clock face with numerals 1-12 in comments and ASCII hands — [prog.c](https://github.com/ioccc-src/winner/blob/master/2020/endoh3/prog.c)
- 2020/endoh2: a 78-column code block with the slanted block letters "IOCCC" over "2020" carved out as whitespace (Star Wars-logo style), plus Yoda, Vader and C-3PO quotes in comments — [prog.c](https://github.com/ioccc-src/winner/blob/master/2020/endoh2/prog.c)
- 2024/codemeow: a bonsai tree in a pot, 43 lines x 80 columns — [prog.c](https://github.com/ioccc-src/winner/blob/master/2024/codemeow/prog.c)
- 2024/endoh2: a code block with a spinning-top-shaped hole standing on a blank "floor" band — [prog.c](https://github.com/ioccc-src/winner/blob/master/2024/endoh2/prog.c)
- 2024/tompng: a round swirling vortex or galaxy of scattered characters around a code core — [prog.c](https://github.com/ioccc-src/winner/blob/master/2024/tompng/prog.c)
- 2024/kurdyukov1: a small round moon of about 13 lines — [prog.c](https://github.com/ioccc-src/winner/blob/master/2024/kurdyukov1/prog.c)
- 2024/tmarrec: a tab-indented tornado funnel — [prog.c](https://github.com/ioccc-src/winner/blob/master/2024/tmarrec/prog.c)
- 2025/jingp49: a police box (TARDIS) with "POLICE PUBLIC BOX", "TELEPHONE", "FREE FOR USE OF PUBLIC" and "PULL TO OPEN" in its comments — [prog.c](https://github.com/ioccc-src/winner/blob/master/2025/jingp49/prog.c)
- 2025/endoh2: a lightning bolt — [prog.c](https://github.com/ioccc-src/winner/blob/master/2025/endoh2/prog.c)
- 2025/endoh1: a Nixie tube with a "MMXXV" cap and pins — [prog.c](https://github.com/ioccc-src/winner/blob/master/2025/endoh1/prog.c)
- 2025/ncw1: a GameBoy with screen, D-pad and buttons — [prog.c](https://github.com/ioccc-src/winner/blob/master/2025/ncw1/prog.c)
- 2018/endoh2: a parrot 142 columns wide — [prog.c](https://github.com/ioccc-src/winner/blob/master/2018/endoh2/prog.c)
- 2025/uellenberg: the code is a Pong frame, with the field carved as whitespace. Lines are very long, up to 1684 characters — [prog.c](https://github.com/ioccc-src/winner/blob/master/2025/uellenberg/prog.c)
- 2020/carlini: the printf format string drawn as a large ASCII-art figure — [prog.c](https://github.com/ioccc-src/winner/blob/master/2020/carlini/prog.c)
- 2025/cesmoak: 280 lines of 80 columns, i.e. a punch-card deck — [prog.c](https://github.com/ioccc-src/winner/blob/master/2025/cesmoak/prog.c)
- 2024/cable2 "murky waters": a salmon recipe hidden in invisible Unicode tag characters inside `U"..."` literals, so the visible source looks almost empty — [2024/cable2](https://www.ioccc.org/2024/cable2/index.html)

### Inferences
- For "code is the art" in both senses, the strongest 2018+ pieces are 2020/endoh3 (the output is the source, redrawn as the current time), 2025/jingp49 (TARDIS source, Doctor Who output), 2024/endoh2 (a top-shaped source that can spin its own shape) and 2020/endoh2.
- The most famous shaped source of the era is probably 2025/ncw1 (the GameBoy). It cannot run on the wall, so it is a portrait-only candidate.

### Gaps
- I could not measure fame quantitatively (view counts, stars). Rankings rest on judge "notable" lists, press coverage and my judgment.
- I found no press coverage specific to the 2018-2020 visual entries beyond ioccc.org itself. Search returned only ioccc.org pages and unrelated deobfuscation repos.

## What did the 28th IOCCC (2024 contest, results 2025) award, and which are visual? (plus the 29th, 2025 contest, results 2026)

### Takeaway
The 28th IOCCC ("40th Anniversary") announced 23 winners on 2025-08-02. The visual ones are endoh1 (ray tracer, image files), endoh2 (spinning top, terminal), codemeow (bonsai, terminal), tmarrec (tornado, terminal with 256 colors, 64 rows), tompng (vortex, terminal), kurdyukov1 (moon, terminal), weaver (Rickroll, 24-bit color plus audio) and kurdyukov3 (Doom, X11/SDL). The 29th IOCCC announced 22 winners on 2026-06-06. Its visual ones are jingp49, endoh2, endoh1, uellenberg, ncw1, ncw2, cesmoak and howe/jhshrvdp (interactive games). IOCCC30 enters its pending state on 2026-11-07 (tentative), so there will be no newer winners before the install.

### Cited Findings
- IOCCC28 winners were released 2025-08-02 and presented live on the "Our Favorite Universe" YouTube channel. The news post calls it "The 40th Anniversary International Obfuscated C Code Contest" — [IOCCC news](https://www.ioccc.org/news.html)
- Full IOCCC28 list: burton (wordle solver), cable1 (LLM inference engine "ChatIOCCC"), cable2 (salmon recipe), carlini (Intel 4004 emulation), codemeow (bonsai), endoh1 (ray tracer in CPP), endoh2 (rigid body), ferguson1 (Oregon Trail), ferguson2 (Navajo code talker), howe (mini vi), kramer (natural-language calculator), kurdyukov1 (moon phase), kurdyukov2 (JPEG artifact removal), kurdyukov3 (gaming VM and Doom), kurdyukov4 (encode without literals), macke (OpenRISC CPU and Linux), maffiodo (Jav\*script interpreter), mills (Infocom v3 interpreter), stedolan (icon from MD5, best one-liner), straadt (layered music generator), tmarrec (3D tornado), tompng (vortex encryptor), weaver (Rickroll) — [IOCCC news](https://www.ioccc.org/news.html), [2024 index](https://www.ioccc.org/2024/index.html)
- IOCCC29 ran from 2025-12-03 to 2026-03-13. Winners were announced live on 2026-06-06 and released to GitHub the same day — [IOCCC news](https://www.ioccc.org/news.html)
- Full IOCCC29 list (dir 2025): ayu (pass-the-traps game), cable (Subleq computer), cesmoak (black hole punch-card Fortran), diels-grabsch (compress one-liner), dogon (prints e), endoh1 (Nixie tube), endoh2 (Lichtenberg), endoh3 (patch/diff quine), ferguson (antipodes map on PPM), howe (Casio MG-880 invaders), jhshrvdp (rogue-like), jingp49 (Dr. WHO), kurdyukov (number puzzles), mattpep (base64), ncw1 (GameBoy), ncw2 (C64 FRACTRAN), ncw3 (FORTH in Unicode), tompng (synthetic seashore, audio), uellenberg (Quine Pong), yang1/2/3 — [IOCCC 2025 page](https://www.ioccc.org/2025/index.html)
- IOCCC30 is tentatively scheduled to enter PENDING on 2026-11-07, OPEN on 2026-12-08 and JUDGING on 2027-04-02 — [IOCCC news, 2026-09-16](https://www.ioccc.org/news.html)
- 2024/stedolan (best one-liner) emits an 80x80 PBM icon — [2024/stedolan](https://www.ioccc.org/2024/stedolan/index.html)
- 2024/macke emulates an OpenRISC system that boots Linux with a UART "connected to the Terminal" — [2024/macke](https://www.ioccc.org/2024/macke/index.html)
- 2025/tompng is an ocean-and-music audio generator. Its visual trick is in the source ("Once you do [open your eyes], you'll see something you can't unsee") — [2025/tompng](https://www.ioccc.org/2025/tompng/index.html)
- 2025/howe needs TAB and ENTER to play. 2025/jhshrvdp needs WASD — [2025/howe](https://www.ioccc.org/2025/howe/index.html), [2025/jhshrvdp](https://www.ioccc.org/2025/jhshrvdp/index.html)

### Inferences
- If the plaque year follows the IOCCC directory convention, 29th-contest entries read "2025" even though they were announced in June 2026. The site titles that directory "2025 - The 29th IOCCC".

### Gaps
- I did not watch the YouTube award presentations, so the judges' spoken commentary is not captured here.

## Which produce terminal-only output that fits 80x23 and build on 64-bit ARM gcc? (ranked shortlist)

### Takeaway
Five entries build cleanly on aarch64 gcc 12 and 14 and produce strong monochrome text visuals at 80x23 (or configurable to it): 2020/endoh2, 2020/endoh3, 2025/jingp49, 2024/endoh2 and 2024/codemeow. One critical ARM bug turned up: 2024/codemeow's bonsai renders as garbage on ARM because `char` is unsigned there. `-fsigned-char` fixes it. Several color-dependent favorites turn blank or lose their effect in one phosphor color: 2018/endoh2's parrot, 2024/weaver, 2025/endoh1 and 2018/poikola.

### Cited Findings
Method: the local tests described at the top (gcc 12.5 aarch64 with `-std=gnu17 -Wall -O2`, run in an 80x23 pty and rendered with pyte; compile-check on gcc 14.4 with gnu17 and gnu23). "Warnings" means `-Wall` warnings; none of these are errors unless stated.

**Ranked shortlist (wall and portrait)**

1. **2020/endoh3, "Most head-turning", Yusuke Endoh, 2020 (27th)**: mirror-image ASCII clock quine — [page](https://www.ioccc.org/2020/endoh3/index.html)
   - What it does: prints its own source redrawn as an analog clock showing the compile time, mirrored. The official loop recompiles the output each cycle ([run_clock.sh](https://github.com/ioccc-src/winner/blob/master/2020/endoh3/run_clock.sh)).
   - Source as art 5/5 (the source is a clock face). Output as art 4/5 (the output is the source with hands and hour letters redrawn).
   - Wall: local test output was exactly 79 columns x 23 lines, with no color and no input. It builds with 0 warnings on gcc 12 and gcc 14 (gnu17 and gnu23). It needs gcc at runtime for the recompile loop, which the wall already has. The clock changes only when recompiled, so it is slow-moving and flash-safe. It does not fit a 15-row Reduced tier.
2. **2020/endoh2, "Best perspective", Yusuke Endoh, 2020**: Star Wars opening crawl — [page](https://www.ioccc.org/2020/endoh2/index.html)
   - Source 4/5 ("IOCCC / 2020" carved in whitespace plus movie quotes). Output 5/5 (perspective-scaled text receding into the distance).
   - Wall: local test used 79 columns, no color and no input. It clears the screen once, then homes the cursor each frame, so there is no full-screen strobe. It runs about 30 s by default (it was still running at the 20 s cut and finished in the 32 s run), a good fit for 40 s. Custom text works via `./prog file.txt`. Caveat: frames are 24 lines plus a trailing newline, so on 23 rows the top 1-2 (mostly empty sky) rows scroll off each frame. The buffer is hard-coded to 1920 = 80x24. 0 warnings on gcc 12 and 14.
3. **2025/jingp49, "Who won award", jingp49 (Taiwan), 2025 (29th)**: 1963 Doctor Who title sequence — [page](https://www.ioccc.org/2025/jingp49/index.html)
   - Source 5/5 (TARDIS police box). Output 5/5 (howlround texture in `, : ; ! ? { $ % # @` resolving into "DOCTOR WHO" in `@` letters, confirmed in local snapshots).
   - Wall: `./prog 80 22` ran about 26 s (280 frames at 90 ms) in the local test, a good fit. It takes width and height as args, so it fits 80x23 and the 15-row Reduced tier. Pure ASCII, no color, no input, 1 warning. Flash note: the whole screen of noise texture changes about 11 times per second. Its average brightness is fairly steady, but the flash governor should be checked.
4. **2024/endoh2, "Prize in solid body physics", Yusuke Endoh, 2024 (28th)**: spinning top and tippe-top rigid-body sim — [page](https://www.ioccc.org/2024/endoh2/index.html)
   - Source 4/5 (spinning-top silhouette cut out of the code). Output 4/5 (a shaded `@`/`:` body that spins, precesses and flips, with an rpm readout).
   - Wall: build with `-DW=80 -DH=22` (plus the Makefile's dt/e/u/rpm/tilt defines). The local test produced 79 columns with no color or input, homing each frame at a high frame rate, 0 warnings on gcc 12 and 14. It loops forever (fine, gets cut off). H is adjustable for the Reduced tier. A nice touch: `./prog < prog.c` spins the program's own shape.
5. **2024/codemeow, "Prize in tray planting", Codemeow (Kyrgyzstan), 2024**: growing bonsai — [page](https://www.ioccc.org/2024/codemeow/index.html)
   - Source 5/5 (bonsai in a pot). Output 4/5 (the tree grows branch by branch over about 14 s, then stops).
   - Wall: sizes itself from `TIOCGWINSZ`. Uses basic ANSI colors and bold, which are lost in mono, but the shape carries.
   - **ARM bug found in local test**: with default aarch64 unsigned `char`, the growth offsets went to column 293 and beyond and the screen filled with garbage. With `-fsigned-char` the tree rendered correctly within about 66x21. The code reads bytes out of a `double` array through `char*`, so it depends on signedness.
   - It also fails to compile under `-std=gnu23` on gcc 14 ("too many arguments to function 'write'"), so pin `-std=gnu17`. It needs `-include sys/ioctl.h` per its Makefile. 2 warnings (misleading indentation).
6. **2025/endoh2, "Most likely to shock", Yusuke Endoh, 2025**: Lichtenberg discharge figure — [page](https://www.ioccc.org/2025/endoh2/index.html)
   - Source 5/5 (lightning bolt). Output 3/5 in mono (a random spanning tree of `/ \ | _`).
   - Wall: size set at compile time (`-Dw=80 -Dh=23`, so Reduced is fine). 0 warnings on gcc 12 and 14. It drew the whole figure almost instantly (about 0.03 s), so a slot means re-running it every few seconds for new patterns. It uses SGR bold/dim brightness plus yellow (33) to show current intensity: 1,782 color and 1,518 bold/dim codes in one frame. If the wall ignores intensity, the "hot path" emphasis is lost and it becomes a plain branching tree.
7. **2024/tompng, "Prize in quasi bijection", tompng (JP), 2024**: visual vortex text encryptor — [page](https://www.ioccc.org/2024/tompng/index.html)
   - Source 5/5 (swirling vortex). Output 3/5 (text visibly stirred into a whirlpool and back).
   - Wall: the animation goes to stderr (fine on a pty). The SIZE argument sets the area: `./prog 11 < sample.txt` used 76 columns x 17 rows in the local test. No color. 2 warnings. Caveat: one pass lasts only about 2.3 s (fixed `usleep` steps), so the slot needs a loop (encrypt, then decrypt, repeat). Input must be a small text file.
8. **2024/kurdyukov1, "Prize in phased periodicity", Ilya Kurdyukov (RU), 2024**: current moon phase — [page](https://www.ioccc.org/2024/kurdyukov1/index.html)
   - Source 4/5 (a tiny round moon). Output 3/5 (a static `#`/`.` moon, 22 rows by about 40 columns in the local test).
   - Wall: fits 80x23, but it is a single instant static frame and fixed at 22-23 rows, so it fails the Reduced tier.
   - Build: 7 warnings on gcc 12. **Fails on gcc 14** with default gnu17 (implicit-int errors). It builds on gcc 14 with `-std=gnu89` or `-fpermissive` (local test).
9. **2025/uellenberg, "Ping pong prize", Jonah Uellenberg, 2025**: Quine Pong — [page](https://www.ioccc.org/2025/uellenberg/index.html)
   - Source 5/5 (the source is the Pong frame). Output 4/5 conceptually (each frame is the next source file).
   - Wall: in the local test the frame was about 36 rows with lines wrapping at 80 columns, too tall for 23 rows. It needs a gcc compile per frame (`try.sh` loop), which will be a few frames per second at best on a Pi. The right paddle takes `w`/`e` as arguments. Whether it plays itself without input is untested. 5-6 warnings. Better as a portrait, or as a wall piece only with a scroll/crop plan.
10. **2025/ncw2, "Best fractional emulator", Nick Craig-Wood, 2025**: C64 `10 PRINT` maze via FRACTRAN — [page](https://www.ioccc.org/2025/ncw2/index.html)
    - Source 2/5 (a table of fractions). Output 4/5 (C64 boot banner, then the diagonal maze).
    - Wall: the local test shows the C64 banner and maze at 80 columns (40x25 is the recommended window). It prints Unicode `╱╲` and uses 24-bit color for the C64 blue, which is lost. The 5x7 font needs `╱ ╲` glyphs or a `/ \` mapping. Deliberately slow printing. 0 warnings.
11. **2020/carlini, "Best of Show - abuse of libc", Nicholas Carlini, 2020**: printf tic-tac-toe — [page](https://www.ioccc.org/2020/carlini/index.html)
    - Source 4/5 (ASCII-art format string). Output 1/5 (a tiny 5-line board).
    - Wall: canned input `echo 1 2 3 4 5 6 7 | ./prog` works (local test ended "P1 WINS"). 0 warnings on gcc 12 and 14. Between boards it prints bursts of non-ASCII padding bytes (0xFF) before each `ESC[2J`, 8 clears in the demo, which could flash or garble on the wall. Portrait-first.
12. **2018/anderson, "Most able to divine code gaps", Derek Anderson, 2018 (25th)**: typographic-river visualizer — [page](https://www.ioccc.org/2018/anderson/index.html)
    - Output 2/5 (static squiggles, about 39x14 for `prog.c`). Source 3/5 (a small 16-line block).
    - Wall: fits and builds with 0 warnings on gcc 12 and 14, but it is static and modest.

**Fails the wall; still candidates for a portrait-only role**
- 2025/ncw1 GameBoy emulator (GameBoy-shaped source, 5/5): needs 160x73, 256 colors, a ROM and a keypad — [page](https://www.ioccc.org/2025/ncw1/index.html)
- 2018/endoh2 dancing parrot quine (parrot source, 142 columns wide): in the local test the text was a plain 79x24 rectangle ending "I'm dead!" / "Bereft of life, I rest in peace!". The parrot figure lives in the ANSI colors (1,026 color codes per run), so it is invisible in one phosphor color — [page](https://www.ioccc.org/2018/endoh2/index.html)
- 2025/endoh1 Nixie tube (Nixie-shaped source): the digit is drawn by coloring source characters with 256 colors. In mono only the digit characters show (local test: a "5" traced in 5s over about 30 rows). The clock needs 336x34 — [page](https://www.ioccc.org/2025/endoh1/index.html)
- 2024/tmarrec tornado (funnel-shaped source): needs its Makefile's `-DQ='fputs("\033[H",stdout);' -ffast-math -include stdio.h`, or it fails to compile (2 errors in the local test). Output is 79x64 rows with 256-color codes on every cell: 43 MB of output in 30 s locally, which is heavy for the wall and 64 rows too tall. The fluid sim will be much slower on a Pi — [page](https://www.ioccc.org/2024/tmarrec/index.html)
- 2024/weaver Rickroll: pure 24-bit background-color blocks, so mono is blank (confirmed locally), plus audio — [page](https://www.ioccc.org/2024/weaver/index.html)
- 2018/poikola Ursa Major: 24-bit color, 125x38. In the local test only a few star names were visible at 80x23 — [page](https://www.ioccc.org/2018/poikola/index.html)
- 2018/giles falling sand (bucket-pouring-sand source): SDL2 — [page](https://www.ioccc.org/2018/giles/index.html)
- 2019/dogon Game of Life: X11 plus keyboard — [page](https://www.ioccc.org/2019/dogon/index.html)
- 2024/endoh1 CPP ray tracer: image output and extremely slow — [page](https://www.ioccc.org/2024/endoh1/index.html)
- 2025/cesmoak punch-card black hole (punch-card-deck source): PGM output taking hours — [page](https://www.ioccc.org/2025/cesmoak/index.html)
- 2024/kurdyukov3 Doom VM: X11/SDL2 plus keyboard — [page](https://www.ioccc.org/2024/kurdyukov3/index.html)
- 2025/yang2 (Fern-from-Frieren-shaped source): the output is generated C code, not a visual — [page](https://www.ioccc.org/2025/yang2/index.html)
- 2024/stedolan one-liner: PBM output of 80 columns x 82 rows of 0/1 (local test) — [page](https://www.ioccc.org/2024/stedolan/index.html)
- 2025/ncw3 FORTH (fullwidth-Unicode source): needs 120x40 and 24-bit color — [page](https://www.ioccc.org/2025/ncw3/index.html)
- Interactive, input-dependent entries: 2020/tsoj Asteroids, 2020/ferguson1 Snake, 2020/endoh1 Minesweeper (mouse clicks), 2019/duble collaborative drawing, 2025/howe invaders (with no keys the local run just showed a one-line status bar), 2025/jhshrvdp rogue-like — [2020/tsoj](https://www.ioccc.org/2020/tsoj/index.html), [2020/endoh1](https://www.ioccc.org/2020/endoh1/index.html), [2019/duble](https://www.ioccc.org/2019/duble/index.html), [2025/howe](https://www.ioccc.org/2025/howe/index.html)
- 2019/karns BFS-on-text: segfaulted on aarch64 in the local test (`./prog < maze`, `-O0`, with or without `-fsigned-char`). Its bugs entry says "Segfaults happen sometimes" (status INABIAF, "please DO NOT fix") — [bugs](https://www.ioccc.org/bugs.html#2019_karns)
- 2024/macke Linux-on-OpenRISC emulator: printed nothing in 60-90 s in the aarch64 container, and nothing natively on macOS arm64 in 25 s. Not diagnosed; not recommended for a 40 s slot — [page](https://www.ioccc.org/2024/macke/index.html)

### Inferences
- A good five-portrait set from this era: 2020/endoh3 (clock), 2020/endoh2 (Star Wars), 2025/jingp49 (TARDIS), 2024/endoh2 (top), and 2024/codemeow (bonsai, with `-fsigned-char`) or 2025/endoh2 (lightning, if the wall renders bold/dim). The first four need no source edits and no color.
- Build policy for the wall: always pass `-std=gnu17` (gcc 15 and later default to gnu23, which breaks codemeow) and consider `-fsigned-char` globally, since many IOCCC entries assume x86 signed `char`. Per-entry Makefile defines (tmarrec, endoh2, codemeow) must be copied into the wall's build recipe.
- Pi OS versions: Bookworm ships gcc 12 and Trixie ships gcc 14 (general knowledge, not verified here). kurdyukov1 is the one shortlisted entry that needs a flag change on gcc 14.

### Gaps
- None of this was run on actual Raspberry Pi 4 hardware. The frame rates and CPU-heavy entries (tmarrec, the endoh2 physics, compile-per-frame quines) need a Pi test.
- I could not test how the wall's 5x7 font renders non-ASCII glyphs (ncw2's `╱╲`, howe's emoji) or whether it honors SGR bold/dim.
- 2025/uellenberg's behavior with no key input (does the right paddle idle, or does the game end?) is untested.
- 2024/macke's boot time is unknown. It may simply need more than 90 s, or it may have an aarch64 issue.

## Did recent IOCCC contests make rules or statements about AI-generated submissions?

### Takeaway
Yes, and the answer cuts against a "Not A.I." reading. Since the 28th contest the IOCCC rules and FAQ explicitly **allow** AI/LLM tools and only encourage disclosure in `remarks.md`. At least two 29th-contest winners disclose AI help. Entries from 2018-2020 predate practical LLM coding tools, which makes them the safest picks for a "Not A.I." plaque.

### Cited Findings
- 2024 (IOCCC28) rules: "you are _allowed_ to use tools to develop and test your submission. These tools may include ... machine learning tools, natural language models, code copilot tools, so-called AI services, large language models (LLMs), etc. If you do make use of such tools or services, then we **ENCOURAGE you to describe what tools and how you used those tools**" — [2024 rules](https://www.ioccc.org/2024/rules.html)
- The 2024 guidelines have near-identical wording — [2024 guidelines](https://www.ioccc.org/2024/guidelines.html)
- The 2025 (IOCCC29) guidelines for Rule 7 (Original Work) list LLMs, "Code copilot tools" and "So called 'AI services'" as allowed. The rule reads "you created it, you own it, its an original work" — [2025 guidelines](https://www.ioccc.org/2025/guidelines.html)
- The tentative IOCCC30 Rule 7 says: "You are permitted to use tools (including LLM tools) to write your code." — [next rules](https://www.ioccc.org/next/rules.html)
- FAQ Q1.6: "You are free to use whatever tools you wish to write your code. This includes tools that are AI based, LLM ... The IOCCC judges do not discriminate on the basis of the tools used to write obfuscated C code so long as you are the ultimate author of the code you submit ... PLEASE mention in your remarks.md which tools you used" — [FAQ](https://www.ioccc.org/faq.html#ai)
- AI disclosed by 29th-contest winners:
  - 2025/ncw1 thanks "Gemini 3 Pro, for its ruthless code golfing suggestions", and its test ROM was "written by The Author and Gemini Pro 3" — [2025/ncw1](https://www.ioccc.org/2025/ncw1/index.html)
  - 2025/cesmoak: "AI coding agents were used to help make these tools", meaning its helper tools, not necessarily prog.c — [2025/cesmoak](https://www.ioccc.org/2025/cesmoak/index.html)
- Explicitly "no AI":
  - The 2025/dogon author: "no AI chatbot was abused, and its an entirely original work"
  - The judges' remarks on the same entry open with "A little poem, no AI - just free" — [2025/dogon](https://www.ioccc.org/2025/dogon/index.html)
- 2024/cable1 "Prize in bot talk" is itself an LLM: "ChatIOCCC is the world's smallest LLM (large language model) inference engine - a 'generative AI chatbot'" in under 1800 bytes of C. The author adds that it is "absolutely totally impossible" according to ChatGPT — [2024/cable1](https://www.ioccc.org/2024/cable1/index.html)
- Press summary (secondary; I could fetch only a search snippet, not the article text): The New Stack reported that the judges, including founder Landon Curt Noll, experimented with LLMs to analyze code with mixed results, did not use them in final judging, and emphasized that humans can still produce code far beyond current AI capabilities — [The New Stack](https://thenewstack.io/the-obfuscated-c-code-contest-confronts-the-age-of-ai/)
- HN commenters on IOCCC29 argued that LLMs remain "terrible at obfuscation" — [HN](https://news.ycombinator.com/item?id=48432199)

### Inferences
- For honest "Not A.I." plaques:
  - 2018-2020 winners are unimpeachable on timing (all submitted before ChatGPT's release in late 2022, a general-knowledge date).
  - For 2024/2025 winners, the absence of a disclosure is not proof, because disclosure is only encouraged. Among the shortlisted 2024/2025 entries (endoh2 2024, codemeow, tompng, kurdyukov1, jingp49, endoh2 2025, uellenberg, ncw2), I found no AI mention in any README (grep for AI/LLM/ChatGPT/Copilot/Gemini/Claude). Avoid ncw1 (GameBoy) for a "Not A.I." plaque, since it credits Gemini.
- 2024/cable1 (ChatIOCCC) could be an ironic companion piece, but it needs a downloaded LLaMA-2 model and live typed input, so it does not fit the wall.

### Gaps
- The New Stack article text could not be fetched (the page returned navigation only), so the judges' quotes above are unverified paraphrase from search snippets.
- I did not check the remarks of every 2024/2025 winner in full, only a keyword grep of all READMEs.
