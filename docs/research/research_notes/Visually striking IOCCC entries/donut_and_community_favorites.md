# donut.c provenance and the IOCCC entries the community rates most visually impressive

Research date: 2026-09-28. Local test results come from compiling and running the code myself. The runs used gcc 14.4.0 in the official `gcc:14` Docker image and Apple clang 17 on an M1 Mac. The IOCCC sources come from a fresh clone of github.com/ioccc-src/winner at commit 31bd35c8 (2026-09-28).

## 1. Who wrote donut.c, when, and is it an IOCCC winner?

### Takeaway
Andy Sloane (a1k0n) wrote donut.c and posted it on his blog on 15 Sep 2006. That program, the famous one with donut-shaped source and a donut alone on screen, was never an IOCCC winner. Sloane did win the IOCCC once. His winner is **2006/sloane, "Homer's favorite"**, an embellished version of the donut ("Donut Mark II") that he posted on 20 Sep 2006. It shows the shaded donut spinning over a scrolling infinite checkerboard, with a scrolling "IOCCC 2006" logo. So "the IOCCC donut" is half right. The IOCCC donut exists, but it isn't the widely shared donut.c.

### Cited Findings
- The original donut.c post is "Have a donut.", dated **Sep 15, 2006**. It says "compile with `gcc -o donut donut.c -lm`, and it needs ANSI- or VT100-like emulation". The post never mentions the IOCCC. Sloane calls it "my first attempt at obfuscated C and I feel it's pretty amateurish; see Donut Mark II for a more impressive demo -- though this one is simple and elegant in comparison." — [a1k0n.net 2006-09-15](https://www.a1k0n.net/2006/09/15/obfuscated-c-donut.html)
- "Embellishing the donut: an old-school CG cliche", dated **Sep 20, 2006**, shows the donut-over-checkerboard program and says: "A version of this (the scroll text says 'IOCCC 2006' instead) was featured in the 2006 International Obfuscated C Code Contest." — [a1k0n.net 2006-09-20](https://www.a1k0n.net/2006/09/20/obfuscated-c-donut-2.html)
- "Donut math: how donut.c works" is dated **Jul 20, 2011**. It opens: "There has been a sudden resurgence of interest in my 'donut' code from 2006". It does not claim the IOCCC for donut.c. — [a1k0n.net 2011-07-20](https://www.a1k0n.net/2011/07/20/donut-math.html)
- ioccc.org lists **2006/sloane – "Homer's favorite" – *Animated donut*** among the 2006 (19th IOCCC) winners. — [ioccc.org years.html#2006](https://www.ioccc.org/years.html#2006); [2006/sloane entry page](https://www.ioccc.org/2006/sloane/index.html)
- The IOCCC author record for Andy Sloane (`author/Andy_Sloane.json`) lists exactly one win, `"winning_entry_set": [{"entry_id": "2006_sloane"}]`, with location US. — [ioccc.org authors](https://www.ioccc.org/authors.html); [winner repo author JSON](https://github.com/ioccc-src/winner/blob/master/author/Andy_Sloane.json)
- The entry's own remarks describe "a little animation of a shaded donut rotating over an infinite checkerboard". They also say that "the entire source code is shaped into a work of art, without being prefixed by any `#define` hacks, or even `#includes`". The judges' comment: "Looks almost good enough to eat, dunnit? I suppose you could argue that, at first blush, this looks like a self-reproducing program." — [ioccc.org 2006/sloane](https://www.ioccc.org/2006/sloane/index.html)
- Sloane on Hacker News (user a1k0n), 2011-07-09: "I'm most proud of my IOCCC 2006 winner (the IOCCC organizers announced the winners, but not the actual entries, then disappeared from the planet): http://a1k0n.net/2006/09/20/obfuscated-c-donut-2.html". In the same thread he says of donut.c: "I don't get why this particular one attracts so much attention, as it was my first one and is pretty amateurish compared to this one". — [HN 2745084](https://news.ycombinator.com/item?id=2745084); [HN 2746451](https://news.ycombinator.com/item?id=2746451)
- In 2014 Sloane wrote on HN: "Clarity and simplicity was the opposite of the goal here, it was an IOCCC entry." This could blur the distinction. — [HN 7109366](https://news.ycombinator.com/item?id=7109366)
- Timeline detail: the "2006" contest (19th IOCCC) had an entry window of **31-Dec-2006 23:59 UTC to 28-Feb-2007 23:59 UTC**. Both blog posts predate the window, and the entry was submitted in early 2007 under the "2006" contest label. — [2006/rules.txt in winner repo](https://github.com/ioccc-src/winner/blob/master/2006/rules.txt)
- Folklore example: Hackaday's IOCCC tag page files a 2020 post ("Mmm… Obfuscated Shell Donuts") under IOCCC. That post describes "a rotating ASCII art donut, formatted as donut-shaped C code" by Andy Sloane from 2006, which merges donut.c and the IOCCC entry. — [Hackaday IOCCC tag](https://hackaday.com/tag/ioccc/)
- Wikipedia's IOCCC article does not mention donut.c or Andy Sloane. — [Wikipedia: IOCCC](https://en.wikipedia.org/wiki/International_Obfuscated_C_Code_Contest)

### Inferences
- The accurate statement is: "donut.c (2006) is not an IOCCC winner. Its direct descendant by the same author, 2006/sloane, won the 19th IOCCC." Calling donut.c "the IOCCC donut" is a common conflation. The entry shares donut.c's torus math (same angle steps 0.07 and 0.02, the same `N=8*((f*e-c*d*g)*m-...)` luminance, z-buffer, and `\x1b[H` redraw), so the confusion is understandable.
- For an installation whose premise is "IOCCC entries", **2006/sloane is the right donut**. It is literally the IOCCC donut, by the same author in the same year. It also looks more impressive on screen (checkerboard plus scrolling logo) and keeps the spinning shaded torus the user wants.

### Gaps
- I found no statement from Sloane explaining why he submitted Mark II instead of the original.
- I found no primary record of the exact date the 2006 winners were announced or published. Sloane's HN comment says entries were not published for a long time after the announcement.

## 2. Closest IOCCC winner to donut.c, and honest plaque wording

### Takeaway
The closest IOCCC winner is 2006/sloane itself: the same torus renderer, same author, same year. Other IOCCC winners that animate 3D shapes in the terminal are 1996/eldby (flying ASCII spheres), 2011/eastman (bouncing ANSI ball), 2013/endoh4 (rotating ASCII solids), 2024/endoh2 (rigid-body spinning top) and 2024/tmarrec (3D tornado). None of them is a torus.

### Cited Findings
- 2006/sloane: "Homer's favorite – Animated donut". It is the donut rotating over an infinite checkerboard with a scrolling "IOCCC 2006" logo (the author's remarks list three parts: "the donut, the checkerboard, and the ASCII logo"). — [ioccc.org 2006/sloane](https://www.ioccc.org/2006/sloane/index.html)
- 1996/eldby: "Best output – Flying 3D spheres in an ASCII display". Judges: "We were impressed by the author's ability to render spheres in 3D in a very small chunk of code." The alt version adds `usleep(35000)` "to not flash too quickly". — [ioccc.org 1996/eldby](https://www.ioccc.org/1996/eldby/index.html)
- 2013/endoh4: "Most solid – ASCII solid rotation". It reads a solid description (for example `cube.txt` or a truncated icosahedron), and the source is formatted as the net of a tetrahedron. — [ioccc.org 2013/endoh4](https://www.ioccc.org/2013/endoh4/index.html)
- 2011/eastman: "Best ball – Bouncing Ball in ANSI Graphics". It needs "a terminal capable of displaying coloured ANSI characters" and sizes itself to the terminal. — [ioccc.org 2011/eastman](https://www.ioccc.org/2011/eastman/index.html)
- 2024/endoh2 is a rotating rigid-body simulation with a 120x24 default screen. 2024/tmarrec is a 3D tornado; the original flickered and the judges added a `\033[H` fix. — [ioccc.org 2024/endoh2](https://www.ioccc.org/2024/endoh2/index.html); [ioccc.org 2024/tmarrec](https://www.ioccc.org/2024/tmarrec/index.html)
- 1998/chaos: "Rotates and zooms an object using ASCII graphics" (curses, `halfdelay()`). — [ioccc.org 1998/chaos](https://www.ioccc.org/1998/chaos/index.html)

### Inferences
Plaque options, all honest:
- **Option A, recommended: use 2006/sloane.** "Created by Andy Sloane, 2006, Not A.I." Every word is accurate: he wrote it in 2006 and it won the "2006" (19th) IOCCC. The installation can also say "IOCCC 2006 winner, 'Homer's favorite'".
- **Option B: use the original donut.c.** "Created by Andy Sloane, 2006, Not A.I." is still accurate, but don't call it an IOCCC winner anywhere nearby. If the other four portraits are labeled as IOCCC winners, add a qualifier such as "donut.c, first published at a1k0n.net, 2006". Another option is "donut.c (2006), the precursor of his IOCCC 2006 winner".
- **Option C: pair them.** Show donut.c's classic donut-shaped source on the print and run 2006/sloane on the wall, or the other way round. This needs careful wording because the printed source would not be the program that runs.
- On a 23-row wall, 1996/eldby, 2013/endoh4 and 2011/eastman fit donut-like expectations but lose to 2006/sloane on source-shape art and name recognition. 2011/eastman also relies on ANSI colour, which a single-phosphor wall cannot show.

### Gaps
- I did not run eldby, endoh4, eastman, endoh2 or tmarrec, so I have not checked their exact row counts or flash behaviour on an 80x23 screen.

## 3. Run characteristics on the wall (80x23, one phosphor colour, no input)

### Takeaway
Both donut programs are pure ANSI terminal programs. They clear the screen once and then home the cursor every frame, draw 79-column rows, loop forever, need no input, and use only characters from a small ASCII luminance ramp. Neither has a frame delay in its original form. On modern gcc (14+) neither compiles without flags. Each writes one newline too many for a 23-row screen. Neither fits a 15-row tier without changing constants.

### Cited Findings
- **donut.c (2006) source facts:** `printf("\x1b[2J")` once, then an infinite `for(;;)` loop. Each frame does `printf("\x1b[H")` and `for(k=0;1761>k;k++)putchar(k%80?b[k]:10)`. The buffer is `z[1760]`/`b[1760]` (80x22), plotting is gated by `22>y&&y>0&&x>0&&80>x`, the ramp is `".,-~:;=!*#$@"`, and each frame does `A+=0.04;B+=0.02` with no sleep. — [a1k0n.net 2006-09-15](https://www.a1k0n.net/2006/09/15/obfuscated-c-donut.html); [Donut math](https://www.a1k0n.net/2011/07/20/donut-math.html)
- **Local test, donut.c output geometry:** each frame is `ESC[H`, one leading blank line, 22 lines of exactly 79 chars, and a trailing newline, so 23 newlines per frame. The torus spans about 20 rows (roughly rows 2 to 21) and about 40 columns, centred near column 40 and row 12. — local test, with the source from [a1k0n.net 2006-09-15](https://www.a1k0n.net/2006/09/15/obfuscated-c-donut.html)
- **Local test, 2006/sloane output geometry:** `puts("\x1b[2J")` once. Each frame is `\x1b[H` followed by 23 lines of 79 chars plus 23 newlines (`for(k=1;1841>k;k++)putchar(k%80?b[k]:10)`, buffer 1840 = 80x23). The checkerboard fills every row, so the whole 79x23 area changes every frame. The ramp is `" ..,,-++=#$@"` for the donut and `".#"` for the checker, with `/ \ | _` for the logo. — local test; [2006/sloane source](https://github.com/ioccc-src/winner/blob/master/2006/sloane/sloane.c)
- **Frame rate:** the original donut.c ran at about 164 frames/s at -O0 and about 1,400 frames/s at -O2 on an Apple M1. 2006/sloane ran at about 1,750 frames/s at -O2. Rotation is a fixed amount per frame, so speed scales with CPU speed and output bandwidth. — local test
- The IOCCC's 2006/sloane page adds a **`sloane.alt.c` with `usleep(S)` (default 75000 µs, about 13 fps)** and warns: "if you are easily overstimulated with fast movement or have photosensitivity please be careful running this version". It says the alt version is recommended "to not flash too quickly, which can be problematic for some people". The alt is otherwise identical: `diff` shows only `usleep(S);` inserted before the draw loop. — [ioccc.org 2006/sloane](https://www.ioccc.org/2006/sloane/index.html); local diff
- Sloane's 2021 version builds in `usleep(15000)` (about 66 fps cap) and needs no `-lm`. — [a1k0n.net 2021-01-13](https://www.a1k0n.net/2021/01/13/optimizing-donut.html)
- **Compile, gcc 14.4.0 (local test):**
  - donut.c with no flags FAILS with 5 errors, the first being `type defaults to 'int' in declaration of 'k' [-Wimplicit-int]`.
  - donut.c with `-std=gnu89 -Wall` compiles with 8 warnings: implicit int ×2 ("data definition has no type or storage class", "type defaults to 'int' in declaration of 'k'"), "return type defaults to 'int'", and implicit declaration of `printf`, `memset` and `putchar` plus two "incompatible implicit declaration of built-in function" warnings.
  - donut.c with `-std=gnu17 -fpermissive` compiles.
  - donut.c with `-std=c23` FAILS ("too many arguments to function 'sin'"), because `double sin(),cos();` means "no parameters" in C23.
  - sloane.c with no flags FAILS with 19 errors. With `-std=gnu89 -Wall` it compiles with 23 warnings, including implicit `sin`/`cos`/`printf`/`puts`, `-Wsequence-point`, and `-Wparentheses`. It also compiles with `-fpermissive`, and even with `-std=c23 -fpermissive`.
  - Apple clang 17 with default flags turns the implicit-int and implicit-function warnings into errors. — local test
- The IOCCC Makefile for 2006/sloane builds with `-std=gnu99 -include math.h -include stdio.h -O3 -lm` plus a long `-Wno-…` list, and the author says: "You will almost certainly get a compiler warning because I declared a bunch of global `int`s without types... There's a chance that my failure to include `math.h` or declare `sin(3)` or `cos(3)` will make the donut not render properly". With gcc 14 and `-std=gnu89` and no includes, it rendered correctly because gcc substitutes its built-in `sin`/`cos`. — [2006/sloane README/Makefile](https://github.com/ioccc-src/winner/tree/master/2006/sloane); local test
- The installation spec says the target computer is a Raspberry Pi 4 running real gcc. — `/Users/trey/dev/codeisart/docs/superpowers/specs/2026-09-22-code-is-art-design.md` (lines 39, 62, 64)

### Inferences
- **The extra newline:** each frame ends with a newline after row 23 relative to home. donut.c prints a leading blank row, 22 content rows and a final newline; sloane.c prints 23 content rows and a final newline. On an exactly 23-row terminal this scrolls the screen up one line every frame. The steady state is the image shifted up one row, and there may be a visible scroll/redraw jitter if the wall samples mid-frame. On a 24-row terminal there is no scroll. It's worth testing on the wall's pty. Fixes include running the pty at 24 rows and cropping, or noting it as a known wart.
- **15-row tier:** donut.c's torus spans about 20 rows and sloane's checkerboard fills 23, so both would clip. Both hard-code 80-column stride and row centre 12.
- **Flashing:** donut.c has no full-screen inversions or strobing. The shading changes gradually and the background stays blank, so it should pass a flash governor easily once it is throttled. 2006/sloane has a high-contrast `.`/`#` checkerboard sweeping toward the viewer across the whole screen, which is a larger luminance-change area. Run it throttled (the IOCCC alt at 75 ms, or slower) and check it against the show's flash governor.
- **Compile on the Pi:** the "real gcc compile with its warnings" moment will show a screenful of implicit-int and implicit-declaration warnings under `-std=gnu89 -Wall`, which is arguably part of the charm. With gcc ≥14 and no `-std`/`-fpermissive` flag, the compile will fail. Which gcc Raspberry Pi OS ships (Bookworm vs Trixie) decides whether that matters; I did not verify this.

### Gaps
- I did not measure frame rate on a Raspberry Pi 4. The M1 numbers only show that a delay is mandatory.
- I did not emulate the 23-row scroll behaviour in a terminal emulator. The finding comes from byte counts.

## 4. Later versions and which has the best donut-shaped source for a printed portrait

### Takeaway
There are four donut versions worth knowing. The 2006 original donut.c is the canonical donut-shaped source and the best portrait of a donut. 2006/sloane is the IOCCC winner, with a blockier checkerboard-and-ring shape. The 2021 no-math-library version is "a little misshapen", in Sloane's words. The 2023/2024 shifts-and-adds variant was written for a chip, not for looks.

### Cited Findings
- **2006 original donut.c:** 22 lines, about 40 columns wide, formatted as a torus. The lower half of the ring is filled with a comment of luminance characters (`/*#****!!-*/`, `/*****####*******!!=;:~ ~::==!!!**********!!!==::- .,~~;;;========;;;:~-. ..,--------,*/`) that completes the shaded-donut picture. — [a1k0n.net 2006-09-15](https://www.a1k0n.net/2006/09/15/obfuscated-c-donut.html) (verbatim from the page's `<pre>` block)
- **2006/sloane (IOCCC):** 32 lines, 56 columns max, 1,707 bytes. The author says "The shape of the source gives a hint about its output". In practice it is a block pattern (checkerboard) around a ring. The IOCCC keeps `sloane.orig.c` (the as-submitted version, which differs only in `main(k,Z)` vs `main(k,Z)char**Z;`) and `sloane.alt.c` (usleep). — [ioccc.org 2006/sloane](https://www.ioccc.org/2006/sloane/index.html); [winner repo](https://github.com/ioccc-src/winner/tree/master/2006/sloane)
- **Donut Mark II blog version (2006-09-20):** almost the same layout as the IOCCC entry, but the logo scroller says something other than "IOCCC 2006". — [a1k0n.net 2006-09-20](https://www.a1k0n.net/2006/09/20/obfuscated-c-donut-2.html)
- **2011:** "Donut math" is an explanation, not a new version. It reprints the 2006 code. — [a1k0n.net 2011-07-20](https://www.a1k0n.net/2011/07/20/donut-math.html)
- **2021 "donut.c without a math library":** no `sin`/`cos`, uses a rotation macro `R(t,x,y)`, `usleep(15000)`, and ends with the comment `/*no math lib needed .@a1k0n 2021.*/`. Sloane: "It's a little misshapen and still has comments at the bottom... there's slightly less code than filled pixels". He also notes donut.c "has been making the rounds again, after being featured in a couple YouTube videos (e.g., Lex Fridman and Joma Tech)". — [a1k0n.net 2021-01-13](https://www.a1k0n.net/2021/01/13/optimizing-donut.html)
- **2023 to 2025:** "donut.c with only shifts and adds" ([a1k0n.net/code/donutbitops.c.html](https://www.a1k0n.net/code/donutbitops.c.html)) and the Tiny Tapeout ASIC port ("From ASCII to ASIC", Jan 10, 2025, updated Dec 19, 2025 saying the chip works). — [a1k0n.net 2025-01-10](https://www.a1k0n.net/2025/01/10/tiny-tapeout-donut.html)

### Inferences
- For a printed portrait that reads instantly as "a donut", **the 2006 original donut.c** is the strongest image. If the running program must be the IOCCC winner, print **2006/sloane**, whose source is the IOCCC artefact. Its layout suggests the checkerboard scene more than a donut, but it is the real entry and the pairing is honest.

### Gaps
- I did not fetch the full text of donutbitops.c, so I have not checked its shape.

## 5. License and permission to display and print

### Takeaway
2006/sloane is clearly licensed: IOCCC content is CC BY-SA 4.0, which allows public display and printing with attribution. The IOCCC FAQ also politely asks users to contact the judges first. donut.c has no licence statement anywhere I checked. It is under default copyright to Andy Sloane, so ask him for permission. That is easy, and it makes a nice story.

### Cited Findings
- IOCCC FAQ Q10.1: "While IOCCC judges look favorably on most requests to use IOCCC material, we request that you ask the IOCCC judges first. Of course, if you're the winner of the entry you can make use of it as you want". It also says "The Copyright and CC BY-SA 4.0 License applies to all IOCCC content." — [ioccc.org FAQ](https://www.ioccc.org/faq.html#ioccc_copyright); [ioccc.org license highlights](https://www.ioccc.org/license.html)
- The 2006/sloane README footer reads "Copyright © … by Landon Curt Noll. All Rights Reserved. You are free to share and adapt this file under the terms of … CC BY-SA 4.0". — [2006/sloane README](https://github.com/ioccc-src/winner/blob/master/2006/sloane/README.md)
- The 2006 contest rules (rule 7) said: "All submitted programs are thereby put in the public domain. All explicitly copyrighted programs will be rejected." — [2006/rules.txt](https://github.com/ioccc-src/winner/blob/master/2006/rules.txt)
- The donut.c posts (2006, 2011, 2021) contain no licence statement. — [2006 post](https://www.a1k0n.net/2006/09/15/obfuscated-c-donut.html); [2011 post](https://www.a1k0n.net/2011/07/20/donut-math.html)
- Sloane's GitHub donut-related repos carry licences, but for different code: `donut-raymarch` (MIT; files `raymarch.c`, `di2.c`; created 2023-10-24) and `tt08-vga-donut` and `tt08-donut-uart` (Apache-2.0). There is no `a1k0n/donut` repo (404). — [GitHub a1k0n](https://github.com/a1k0n) (queried via GitHub API)

### Inferences
- For 2006/sloane: credit "Andy Sloane, IOCCC 2006" with a CC BY-SA 4.0 note and link, for example in small type on the plaque or in a QR code. Emailing the IOCCC judges is the courteous step their FAQ asks for.
- For donut.c: email Sloane. He publicly enjoys the attention (chip port, HN replies), so permission seems likely, but it isn't guaranteed. This is not legal advice.

### Gaps
- I did not find an explicit licence for donut.c or any public statement from Sloane waiving rights.

## 6. IOCCC entries the community treats as most visually impressive

### Takeaway
Across ioccc.org, Wikipedia, Hacker News (about 1,500 comments and the top stories), Hackaday and blogs, the recurring visual favourites are:
- 1988/westley (pi circle source)
- 1998/banks (flight simulator, X11)
- 2012/endoh1 (ASCII fluid)
- 2013/cable3 (8086 PC emulator, SDL/X11 for graphics)
- 2001/herrmann2 (magic-eye source)
- 2013/birken (Tetris painting)
- 2011/akari (anime-girl source, image output)
- the donut family

The donut family is the single most up-voted visual subject on HN, but mostly for the non-IOCCC donut.c. 2006/toledo2, 2006/sykes2, 2018/mills and 2020/carlini get high HN scores for cleverness rather than visuals.

### Cited Findings

**Method:** Author names are checked against the IOCCC winner-repo `author/*.json` files. I queried HN through the Algolia API for comments matching "ioccc", "obfuscated c", "donut.c" and "a1k0n" for 2007 to 2026, giving 1,511 unique comments. I counted explicit `YYYY/name` entry references and keyword mentions co-occurring with "ioccc"/"obfuscated". I also ranked HN stories by points. Reddit's API blocked scripted access and site-restricted web search returned no Reddit threads, so Reddit coverage is missing (see Gaps).

**Frequency-weighted list** (✓T = terminal text output, fits an 80-column terminal; G = needs X11/SDL/graphics or image files):

1. **Donut family: donut.c (2006, not IOCCC) and 2006/sloane "Homer's favorite" (IOCCC).** ✓T.
   - HN stories about donut.c: "Donut math" 237 pts (2011), 204 (2012), 196 (2023), 121 (2014); "donut.c without a math library" 135 (2021); "From ASCII to ASIC" 162 (2025); "ASCII animated donut in obfuscated C" 81 (2011). No single IOCCC entry has that many front-page appearances. — [HN 2787227](https://news.ycombinator.com/item?id=2787227), [HN 4595920](https://news.ycombinator.com/item?id=4595920), [HN 37548599](https://news.ycombinator.com/item?id=37548599), [HN 25787545](https://news.ycombinator.com/item?id=25787545), [HN 42675208](https://news.ycombinator.com/item?id=42675208), [HN 2746132](https://news.ycombinator.com/item?id=2746132)
   - YouTube coverage (Lex Fridman, Joma Tech) is per Sloane. — [a1k0n.net 2021](https://www.a1k0n.net/2021/01/13/optimizing-donut.html)
   - Only 2 HN comments reference `2006/sloane` explicitly. — local HN corpus count
2. **1998/banks, flight simulator (Best of Show), by Carl Banks.** G (X11/Xlib).
   - Highlighted by Wikipedia ("a flight simulator using X Windows, the winner of the 1998 IOCCC"). — [Wikipedia](https://en.wikipedia.org/wiki/International_Obfuscated_C_Code_Contest)
   - HN stories 251 pts (2017) and 165 (2024); HN "My favorite is … 1998/banks.c a flight simulator!" — [HN 15058723](https://news.ycombinator.com/item?id=15058723), [HN 41903399](https://news.ycombinator.com/item?id=41903399), [HN 18348956](https://news.ycombinator.com/item?id=18348956)
   - It is flown with the keyboard (arrow keys), which is a problem for a wall with no input. The source layout is commonly described as airplane-shaped, but I did not verify the full silhouette. — [ioccc.org 1998/banks](https://www.ioccc.org/1998/banks/index.html)
3. **1988/westley, "Best layout", prints 3.141 using a circle made of `_-_-`, by Brian Westley.** ✓T (output is a number; the visual is the circular source).
   - Wikipedia example: "a 1988 entry which calculates Pi by looking at its own area". — [Wikipedia](https://en.wikipedia.org/wiki/International_Obfuscated_C_Code_Contest)
   - 24 HN comments in 22 threads mention it with IOCCC; 7 explicit links. — local HN corpus count; e.g. [HN 2747316](https://news.ycombinator.com/item?id=2747316)
   - Westley's other layouts (1990, 1992, 1994) are also frequently linked. — [ioccc.org years](https://www.ioccc.org/years.html)
4. **2012/endoh1, "Most complex ASCII fluid", by Yusuke Endoh.** ✓T (ANSI; reads its own source and "melts" it as fluid).
   - HN story 89 pts; 24 comment mentions and 13 explicit links; Hackaday 2015 "Animated ASCII Fluid Dynamics Simulator Is Retro Cool". — [HN 20074185](https://news.ycombinator.com/item?id=20074185), [Hackaday IOCCC tag](https://hackaday.com/tag/ioccc/)
   - The author says "make your terminal window larger than 80 x 25", which is too tall for an 80x23 wall without changes. — [ioccc.org 2012/endoh1](https://www.ioccc.org/2012/endoh1/index.html)
5. **2013/cable3, IBM PC 8086 emulator in 4,043 bytes, by Adrian Cable.** G (SDL/X11 for the graphics mode; can boot DOS and run old apps).
   - HN 196 pts (2014) and 126 pts (2018); 8 explicit links; Hackaday 2014. — [HN 7012385](https://news.ycombinator.com/item?id=7012385), [HN 18198374](https://news.ycombinator.com/item?id=18198374), [ioccc.org 2013/cable3](https://www.ioccc.org/2013/cable3/index.html)
6. **2001/herrmann2, "Most eye-crossing": SIRDS/magic-eye generator whose source is itself a stereogram, by Immanuel Herrmann.** ✓T.
   - 5 explicit HN links ("This obfuscated 'magic eye' C program also produces a magical feeling!"). — [HN 22568552](https://news.ycombinator.com/item?id=22568552), [ioccc.org 2001/herrmann2](https://www.ioccc.org/2001/herrmann2/index.html)
7. **2013/birken, "Best painting tool": paints pictures with Tetris pieces, by Michael Birken.** ✓T (ANSI, animated; also GIF output).
   - HN "Code or art?"; Hackaday 2014 roundup. — [HN 12789723](https://news.ycombinator.com/item?id=12789723), [ioccc.org 2013/birken](https://www.ioccc.org/2013/birken/index.html)
8. **2011/akari, Best of Show: downsampler whose source is ASCII art of Akari (YuruYuri), by Don Yang.** G for real use (PGM/PPM), but the source is famous as art.
   - Wikipedia example. — [Wikipedia](https://en.wikipedia.org/wiki/International_Obfuscated_C_Code_Contest), [HN 3898770](https://news.ycombinator.com/item?id=3898770)
9. **2006/toledo2, Best of Show: Intel 8080 emulator (runs CP/M), by Oscar Toledo G.** ✓T (curses/ANSI).
   - HN 256 pts (2024); Hackaday 2024. Toledo's nanochess is a Wikipedia example. Impressive, but the display isn't the attraction. — [HN 39758667](https://news.ycombinator.com/item?id=39758667), [ioccc.org 2006/toledo2](https://www.ioccc.org/2006/toledo2/index.html)
10. **2006/sykes2, "Best one liner": a clock in one line (prints large ASCII digits), by Stephen Sykes.** ✓T.
    - HN 227 pts for the StackOverflow "Please explain sykes2.c". — [HN 5524002](https://news.ycombinator.com/item?id=5524002), [ioccc.org 2006/sykes2](https://www.ioccc.org/2006/sykes2/index.html)
11. **2020/carlini, Best of Show: tic-tac-toe in a single `printf` call.** ✓T.
    - HN 361 pts; 7 explicit links; Hackaday 2020. Clever rather than visual. — [HN 25690319](https://news.ycombinator.com/item?id=25690319)
12. **2018/mills, Best of Show: PDP-7/PDP-11 emulator (runs early Unix).** ✓T. HN 157 pts. — [HN 18848062](https://news.ycombinator.com/item?id=18848062)
13. **Also frequently linked but not visual:**
    - 2012/tromp (lambda calculus). It has the most explicit HN links (50), but 45 of them were posted by user "tromp", the author. — local HN corpus count; [HN 4666562](https://news.ycombinator.com/item?id=4666562)
    - 1994/smr (smallest quine). — [HN 5762285](https://news.ycombinator.com/item?id=5762285)
    - 1984/mullender (VAX machine code as `short main[]`, first winner; HN 150 pts deep-dive). — [HN 24321403](https://news.ycombinator.com/item?id=24321403)
    - Bellard's OTCC (2001/bellard; HN 381 pts for the OTCC page). — [HN 26141124](https://news.ycombinator.com/item?id=26141124)

**Terminal 3D/animation entries that rarely come up in community lists but fit the wall:** 1996/eldby (flying spheres), 2013/endoh4 (rotating solids), 2011/zucker ("Most shiny – Text raytracing"), 2024/endoh2 (spinning top), 2024/tmarrec (tornado). — [ioccc.org years](https://www.ioccc.org/years.html)

**Judges' and organizers' own highlights:** the IOCCC runs YouTube award presentations (for example "IOCCC29 Winning Entries | IOCCC Awards Presentation and Source Code Reveal", June 2026) and Patreon commentary on the IOCCC28 winners. — [YouTube MoWCwZx1Swc](https://www.youtube.com/watch?v=MoWCwZx1Swc), [Patreon](https://www.patreon.com/posts/commentary-on-of-135753694)

### Inferences
- The donut dominates popular attention. It is the most famous obfuscated-C program in general, largely thanks to YouTube and repeated HN front pages. So the user's instinct is right; only the label needs care.
- For an 80x23 monochrome terminal wall, the favourites that actually fit are:
  - 2006/sloane (animated; fits 80x23 exactly, give or take the trailing newline)
  - 2006/sykes2 (clock)
  - 2001/herrmann2 (stereogram)
  - 2013/birken (animated; check colour dependence)
  - 1988/westley (static output; the source is the art)
  - 2012/endoh1 (animated, but needs about 25 rows and would need a size change)
- 1998/banks, 2013/cable3 and 2011/akari need graphics.

### Gaps
- **Reddit:** reddit.com blocked scripted JSON access, and `site:reddit.com` searches returned no IOCCC threads, so I could not measure r/programming or r/C_Programming frequency. A manual Reddit search is needed if that matters.
- **YouTube:** I did not enumerate compilation videos or their view counts beyond the ones cited.
- The HN counts are lower bounds. Algolia returns at most 1,000 hits per query (queries were sliced by year to stay under that), keyword matching is approximate, and link rot makes old `ioccc.org/1998/banks.c`-style URLs countable only by pattern.
- I found no dedicated "top 10 IOCCC entries" blog listicle from a reputable source. The aggregate picture rests on Wikipedia's chosen examples, HN votes and comments, and Hackaday coverage.
