# Decisions — wall arcade

Every question for the owner, one block each. Since 2026-09-28 the loop does not ask and wait: it
appends the block, takes the default, and the owner answers at a check-in or whenever they like; the loop
then transcribes the answer under the question and follows it from there. A block with an empty `answer:`
line is open. Loop-decidable questions are never asked here; they are journaled. Every
question takes its default at once and is marked `defaulted` (standing instruction below); the owner can
override it later.

## Standing instruction (2026-09-28, made permanent the same day)

First the owner said: "I will take your leans for decisions tonight. I will review our work after iteration 6."
After the retrospective of 2026-09-28 the owner made it the rule for every run (config.md, Loop rule 8).

A new owner question gets its block here as usual, then takes its default at once, marked
`status: defaulted (standing instruction)`, and is listed at the next check-in. It is not asked, and the
loop does not wait. A plan review that blocks gets the fix and one confirming look (config.md, Loop rule 4).
The loop writes gate.md only for a destructive or irreversible action, a change to the roadmap's scope or
end goal, or the iteration cap. A step only the owner can do goes to the roadmap's "Owner items" and the
loop takes the next milestone that does not need it.

The "review after iteration 6" happened early, on 2026-09-28 before iteration 6 (journal, owner
intervention). The owner confirmed Q17 to Q20 there. The next gate is after iteration 7 (Q21).

Block format:

```
### Q<n>: <question>
asked: it<N>
default: <what the loop does at once; every question has one>
deadline: it<N>
answer: <owner's answer, transcribed; empty while open>
status: open|answered|defaulted
```

Q1 to Q5 were decided in the adversarial review before the loop started (review section 10a).

### Q1: Which layout is the design layout?
asked: it0
default: none (blocks)
deadline: it0
answer: 128x32 is the design layout, chosen for two-player side-by-side play. 64x64 is first-class for single-player games and square visuals (the panels often sit stacked on a bar). `GameInfo` declares `layouts` (both by default); the menu and attract director show only entries designed for the current layout; per-layout tuning tables where needed; feel budgets apply in full on declared layouts, run-and-legible on the rest; the live smoke covers both layouts. (2026-09-26)
status: answered

### Q2: Which games ship?
asked: it0
default: none (blocks)
deadline: it0
answer: Review section 7 verdicts accepted. Cut frogger; life and beat move to the attract catalog; jump and scream merge into Strongman; flappy becomes arm flapping (Flap); puppet becomes the attract's mirror layer; holewall is the hero as Copy Me; pong and paint stay with their fixes. Add Quick Draw, Dodge, Tug, Flap, Swat and Freeze. Ship order: Copy Me, Pong, Quick Draw, Dodge, Tug, Flap, Swat, Paint, Strongman, Freeze. (2026-09-26)
status: answered

### Q3: What is the walk-up flow?
asked: it0
default: none (blocks)
deadline: it0
answer: The review's replacement for the twelve-tile grid: mirror first, a wordless hand-up pictogram, play at once, an opt-in three-door menu, and the session ends when the player leaves. (2026-09-26)
status: answered

### Q4: Is the operator design approved?
asked: it0
default: none (blocks)
deadline: it0
answer: Approved as written (docs/superpowers/specs/2026-09-26-arcade-operator-design.md). Bootstrap follows spec revision 3. (2026-09-26)
status: answered

### Q5: What hardware does the arcade run on?
asked: it0
default: none (blocks)
deadline: it0
answer: Its own Raspberry Pi 5 (ordered) with the spare Colorlight 5A-75E and its own power; the show Pi 4 stays untouched. The raw Colorlight backend from the show daemon plan drives the card, not DDP through Falcon Player; its brightness command enforces the arcade's brightness. The Pi's wired port is dedicated to the card; SSH over Wi-Fi. The Pi 5's built-in real-time clock replaces the DS3231. Gate B and the `pi_perf` budget target the Pi 5. Mic: a cardioid dynamic vocal mic on a gooseneck through a USB interface (Trey ordering). (2026-09-26)
status: answered

### Q6: Should iteration plans get an adversarial review before implementation?
asked: it2
default: none (owner asked)
deadline: it2
answer: Yes. "Lets make that happen to ensure quality as we go along." One opus plan reviewer between Plan and Implement, blocking findings back to the plan writer, re-review once, gate after two blocked rounds (operator design step 2a). Applies from iteration 2's plan onward. (2026-09-27)
status: answered

### Q7: The it02 plan review is blocked after two rounds on one finding with a verified fix (R2-B1). Apply it and continue?
asked: it2
default: apply R2-B1 and R2-N1 to N4 as the reviewer specified, confirm-only third review round, then implement
deadline: it2
answer: "Apply fix, confirm." The plan writer applies R2-B1 and R2-N1 to N4 exactly as the reviewer specified; the reviewer does a confirm-only third round; then commit and implement. The step 2a rule (gate after two blocked rounds) stays as is. (2026-09-27)
status: answered

### Q8: Should Blob gain an id and velocity (carried fix C11, a spec gap)?
asked: it3
default: yes, `Blob.id = -1` (untracked) plus `vx`, `vy`, set by the blob source when core Task 15 is planned; nothing before then needs them
deadline: the iteration that plans core Task 15 (M5)
answer: "Yes, at Task 15." Add `Blob.id` (-1 = untracked), `vx`, `vy`; the blob source sets them when core Task 15 is planned. (2026-09-27)
status: answered

### Q9: shake() silently falls back to the default calibration, and committed test_festival.py:180 pins that. Change the test to expect ValueError (as degrade now does)?
asked: it3
default: yes, change it in the next iteration that touches actors; the change makes a silent wrong-zone result an error
deadline: it4
answer: "Yes, raise." shake raises ValueError like degrade; test_festival.py:180 changes to pytest.raises(ValueError). Applied in iteration 3, which already touches actors. (2026-09-27)
status: answered

### Q10: How many missed camera captures should holds, edges and the cursor ride out (CAPTURE_GRACE)?
asked: it4
default: 5 captures (0.55 s at 10 fps). Under spec noise the 3 s exit hold completes 40 of 40 times at 5, 30 of 40 at the old 0.25 s grace; a release registers after 0.55 s instead of 0.25 s. The real fixtures at GATE A refit it.
deadline: it4
answer: "5 captures." CAPTURE_GRACE = 5 (0.55 s at 10 fps); GATE A's real fixtures refit it. (2026-09-28)
status: answered

### Q11: Tick order: run the flash governor last (after the brightness limiter), against spec 4, 7.2 and 8.1?
asked: it4
default: governor last (flash bound holds by construction; with the limiter after it, the limiter's level changes can themselves strobe a static frame, evidence/it04/plan-review.md B2)
deadline: it5 (the runner)
answer: "Governor last." Tick order is limiter, then governor, then push; the flash bound holds by construction. Departs from spec 4, 7.2 and 8.1; recorded for spec revision 4. (2026-09-28)
status: answered

### Q12: Night rule: may a bright lux reading cancel the clock's night (spec 7.6), or may lux only add night (spec 4.3)?
asked: it4
default: lux only adds night (night = clock window OR lux below night_lux), with hysteresis; the camera sees the wall's own light, and a flapping reading strobes the picture (plan-review.md B3)
deadline: it4
answer: "Lux only adds night." Night = the clock window OR lux below night_lux, with hysteresis; lux never makes the picture brighter than the clock allows. (2026-09-28)
status: answered

### Q13: Scrolling titles against the per-pixel flash rule: fine text scrolling at 10-30 px/s gets held and smeared, and 2x titles do not fit 42 px doors (plan-review.md N6). Which way?
asked: it4
default: (b) spec 7.6 exempts small flashing areas below a field fraction, matching the success criterion's "full-field flashes"; the director (it06) is where it bites
deadline: it6 (the director)
answer: "Exempt small areas." Amend spec 7.6: flashing regions below a fraction of the field are not held, matching the success criterion's "full-field flashes". The loop proposes the fraction conservatively from broadcast guidance and journals it; recorded for spec revision 4. (2026-09-28)
status: answered

### Q14: The it04 plan review is blocked after two rounds on one finding with a verified fix (B7: pixels that take turns flash the whole wall, so the flash bound does not hold by construction). Apply it and continue?
asked: it4
default: apply B7 (a square backstop: after the pixel rule, hold any 32 px square whose mean would make an over-budget transition, repeated until none flips; only tightens; 327/327 tests pass unchanged; square flashes <= 6 on every attack), delete residual (2), reword decisions 16-17, add the turn-taking tests and the <= BUDGET asserts; confirm-only third review round, then implement
deadline: it4
answer: "Apply fix, confirm." The writer applies B7 exactly as the reviewer specified (square backstop, residual (2) deleted, decisions 16-17 reworded, turn-taking tests and <= BUDGET asserts); confirm-only third round; then commit and implement. (2026-09-28)
status: answered

### Q15: Regular patterns (plan-review.md N14): a reversing stripe grating (12 pairs, 15 Hz, whole wall) passes the flash governor, and spec 7.6 has no pattern rule. How should it be covered?
asked: it4
default: a content rule in the game guide (no reversing or oscillating stripes with more than 5 pairs over more than 25% of the wall, per BT.1702-3 Guideline 2) plus a soak `pattern` check; the loop also caps over-budget flipping pixels at 12.5% of the wall per frame (text peaks at 0.099, the grating at 0.188)
deadline: before the first attract mode or game (it06)
answer: "Guide rule + soak + cap." Game-guide content rule (no reversing or oscillating stripes with more than 5 pairs over more than 25% of the wall, BT.1702-3 Guideline 2), a soak `pattern` check, and the governor caps over-budget flipping pixels at 12.5% of the wall per frame; the cap goes into the it04 plan with B7. (2026-09-28)
status: answered

### Q16: Absolute flash threshold (plan-review.md N17): spec 7.6's 0.1 is relative; BT.1702 and Ofcom use 20 cd/m² absolute, so a bright outdoor P5 panel may be several times laxer. Change it?
asked: it4
default: measure the wall's white at brightness 0.4 in prototype week, then set THRESHOLD = min(0.1, 20/L); keep 0.1 until then
deadline: GATE B
answer: "Measure at prototype." Keep THRESHOLD 0.1; in prototype week measure the white at brightness 0.4 and set THRESHOLD = min(0.1, 20/L); added to GATE B. (2026-09-28)
status: answered

### Q17: Spec 7.2 hides a game that raises "three times in a session", but a crash ends its session. How many crashes hide a game?
asked: it5
default: three crashes since the runner started hide the game until the restart (`MAX_CRASHES = 3` per game over the night); alternative: three in a row, a clean session resetting the count
deadline: it5
answer: confirmed by the owner 2026-09-28: three crashes since the runner started hide the game until the restart. Nothing restarts the arcade nightly yet; plan Task 24 (the service) must, or a hidden game stays hidden.
status: answered

### Q18: Juice shake: a few shrinking jumps (at most 4 a second) so the shake keeps the flash rule by itself, instead of a smooth wobble the governor would hold as a stutter over busy pictures?
asked: it5
default: jumps; a shake reads as a few knocks, not a rumble
deadline: it5
answer: confirmed by the owner 2026-09-28: jumps. To be judged on the panel at the first live play test (does one knock read as an impact or as a glitch).
status: answered

### Q19: Juice bursts close together: drop a burst within 32 px of one accepted in the last 0.4 s, or merge it into the old one?
asked: it5
default: drop it (a fast rally that bursts on every hit shows about every other burst); merging spends more of the particle pool. The gap was 0.4 s at asking; the loop raised it to 0.5 s after it05 plan review N1, so a burst alone changes a pixel at most about 4 times a second
deadline: it5
answer: confirmed by the owner 2026-09-28: drop it, with the gap at 0.5 s as built. To be judged in two-player play: 32 px is the wall's full height at 128x32, so one player's burst can swallow the other's.
status: answered

### Q20: Juice flash: a hold (full colour for `seconds`, then off; the next waits 0.5 s after it ends) instead of a fade?
asked: it5
default: a hold. A fading saturated red flash crosses the governor's red rule up to three times and got the whole wall held (flash_area 1.0, it05 plan review round 1). The cost is a blink instead of a glow. Alternative: keep the fade, at most one flash a second.
deadline: it5
answer: confirmed by the owner 2026-09-28: a hold. To be judged on the panel at night at the first live play test, before many games tune their flash values; the safety measurements favour neither a hold nor a fade at one a second.
status: answered

### Q21: The show daemon has the install date (2026-11-11) and only its foundation tasks are built. When does the operator move to it?
asked: it6 (owner check-in 2026-09-28, before iteration 6)
default: stay on the arcade
deadline: it6
answer: two arcade iterations (6 and 7: the first playable, headless and on the camera), then the operator moves to the show daemon. `iterations-per-run` is 2. At the gate after iteration 7 the loop stops; the daemon's roadmap and workflow files are written then, with the owner. The arcade resumes after the daemon, if there is time before the event.
status: answered

### Q22: What does the small lobby show when nobody is near, before M8's attract modes exist?
asked: it6
default: the featured game's title at 1x, centred, static and dim (`TITLE_COLOR = (120, 60, 0)`); nothing when no game fits. M8's director replaces it
deadline: it6
answer:
status: defaulted (standing instruction)

### Q23: Which score does the end card show after a two-player Pong, and which games record a best?
asked: it6
default: the card shows player 1's points; Pong records a best for solo games only (a duel's points depend on the other player)
deadline: it6
answer:
status: defaulted (standing instruction)

### Q24: Does a raised hand during the 3 s end card start the next game at once?
asked: it6
default: no. Hands do nothing while the card shows; after it a raise starts the game. The result stays readable for its 3 s
deadline: it6
answer:
status: defaulted (standing instruction)

### Q25: A player walks in with a hand already up. Does the game start?
asked: it6
default: no. The hand must be lowered and raised again (the lobby's edge is primed when a new player locks and after the end card), so a hand left up, or someone waving while passing, starts nothing by accident. To be judged at the first live smoke: it costs a stranger who arrives waving about a second
deadline: it6
answer:
status: defaulted (standing instruction)

Seen on it06's sheet (operator, 2026-09-28): under Q23's default the card after a duel that player 2 wins 5-0 reads "PONG 0", so the winner reads a zero. The operator's lean for the gate: both scores in the players' colours.

### Q26: What are the feel budgets' numbers? (Spec 9.3 names the metrics and gives no numbers.)
asked: it7
default: for `control` and `score` games: `response_ticks` at most 2, `fidelity` at least 0.8, `range` at least 0.6, `lit_fraction` 0.01 to 0.5, `dim_fraction` at most 0.1, `liveliness` at least 0.001, `flash_area_raw` at most 0.1, `square_flashes` at most 6, `phases_reached` 1.0, `round_seconds` 20 to 120 (2 ticks and rounds of 20 to 120 s are spec 11's). Toys: the same without `round_seconds`, `fidelity`, `range`. A game may override one in its own file, with a reason; a band is never loosened to make a game pass
deadline: it7
answer:
status: defaulted (standing instruction)

### Q27: How often must each bot win for a game's difficulty to pass?
asked: it7
default: the `good` bot wins at least 0.7 of its plays, the `lazy` bot 0.1 to 0.7, no input at most 0.05, over 20 seeded plays
deadline: it7
answer:
status: defaulted (standing instruction)

### Q28: When is a lit pixel "dim"?
asked: it7
default: when every channel is under 140 (spec 11's wall-look line), measured on the game's own drawing before the limiter. At most 10% of lit pixels may be dim; Pong's net is dim on purpose and is an override with a reason
deadline: it7
answer:
status: defaulted (standing instruction)

### Q29: What does a game's evidence GIF show?
asked: it7
default: 6 s from 1 s before the game launches, every third tick at 10 frames a second, the plain look at scale 2 (scale 1 if over 300 KB)
deadline: it7
answer:
status: defaulted (standing instruction)

### Q30: How is the stripe rule (Q15, BT.1702-3 Guideline 2) read by the soak's `pattern` check?
asked: it7
default: stripes are more than 5 light-dark pairs of equal width (within 1 px) in a row or column, the light bands at least the flash threshold above the dark ones; they count only where they change between two frames (reversing, oscillating or moving; static stripes count 0); the limit is 25% of the wall. It is a check in the tests, not part of the governor
deadline: it7
answer:
status: defaulted (standing instruction)

### Q31: What are the budgets for the score's visibility and legibility, and is there one for the idle hint?
asked: it7
default: `score_visible` at least 0.8 (the share of play ticks on which the game's score is found on the wall by font matching) and `score_legible` at least 0.9 (the same digits still read after the 5 m `distance` look), for `control` and `score` games. No budget for the idle hint: the measure built in it07 showed only that the wall answers a present body (Pong passed it at 0.0 s with no hint at all, by the seat's colour), so the review blocked it; it stays in the report as `presence_answer_seconds` without a budget until a measure of a real hint exists (spec 9.3, spec 11's 3 s)
deadline: it7
answer:
status: defaulted (standing instruction)

### Q32: The prototype has four 64x32 panels, not two. Which arrangement does the arcade build for, and when?
asked: it7 (raised by the owner, 2026-09-28 18:00 CDT, while it07's review was open)
default: none taken; the owner answered at once
deadline: it7
answer: "2x2, put 128x64 at the top of the roadmap". 128x64 is the third first-class layout, beside 128x32 and 64x64. Milestone M4b, the first unchecked line after M4a, before the games of M7a. Iteration 7 is not changed by it: Pong stays at 128x32 in it07, and the freeze tag `game-protocol-v1` is set as planned (a layout is a data value of `GameInfo`, not a member of the protocol). Q21's gate after iteration 7 stands until the owner says otherwise
status: answered (owner, 2026-09-28)

### Q33: Is 128x64 the only layout games are built for, and what comes after the gate: the show daemon or M4b?
asked: it7, at the gate (gate.md, 358b7ca), 2026-09-28
default: Q21 stands, the show daemon; 128x64 a third layout beside 128x32 and 64x64
deadline: none
answer: "yes, make 128x64 the only layout and do M4b first". Games are designed, tuned and judged at 128x64 alone; the engine stays free of any size and every game still runs at a size it does not declare. Iteration 8 is M4b; the loop gates after it and the operator then moves to the show daemon. Pong's 128x32 declaration stays only if it passes without extra work
status: answered (owner, 2026-09-28)

### Q34: What are Pong's numbers at 128x64?
asked: it8
default: the paddle a quarter of the wall's height (16 px) and 2 px wide; the ball 2 px; ball speeds in px/s as at 128x32 (start 60, gain 1.08, max 110) before tuning; the CPU at 0.75 wall heights a second (48 px/s) before tuning; both scores at 2x at the top, centred over each half. Pong's 128x32 declaration is dropped (it would need its own tuning and a second 20-seed report); Pong still runs at sizes it does not declare
deadline: it8
answer:
status: defaulted (standing instruction)

### Q35: Does a player who stands still bank points in Pong (C41)?
asked: it8
default: no. A human's point counts only if they moved the paddle 1 px or more in the rally that ended in it; otherwise nobody scores and the next serve follows. A best is stored only when the solo player moved during the game
deadline: it8
answer:
status: defaulted (standing instruction)

### Q36: Must a good player's round of Pong reach 5 points before the 90 s cap?
asked: it8
default: no. The round band (20 to 120 s) holds; the owner's live smoke judges the pace
deadline: it8
answer:
status: defaulted (standing instruction)

### Q37: How is the small lobby laid out on 64 rows?
asked: it8
default: the attract title, the card's title-and-score line and "BEST!" at 2x on a wall of 48 rows or more where they fit, the prompt line at 1x; the mirror figure the wall's full height (64 px) with 2 px strokes; the hand-up pictogram 16 px, level with the shoulders. The card's content stays Q23's
deadline: it8
answer:
status: defaulted (standing instruction)

### Q38: How large must a game's answer to an input be (the response budget, C38)?
asked: it8
default: `response_px` at least 12 pixels changed two ticks after the input moves, for control, score and toy games (spec 11's "within two ticks and at least 12 lit pixels"). `response_ticks` stays the latency alone, at most 2
deadline: it8
answer:
status: defaulted (standing instruction)

### Q39: What does the wall test pattern show for the 2 x 2 wall?
asked: it8
default: `wall_pattern index` defaults to 128x64 and draws a seam at every 64 columns and every 32 rows, so a panel in the wrong place shows
deadline: it8
answer:
status: defaulted (standing instruction)

### Q40: Is the faster Pong kept? (It was retuned during it08 to end rounds by points, which also cut the suite's time.)
asked: it8
default: yes, until the owner has played it. At 128x64: `CPU_SPEED` 0.35 wall heights a second (Q34's starting value was 0.75), `BALL_START` 100 px/s (60), `BALL_GAIN` 1.2 a paddle hit (1.08), `BALL_MAX` 170 px/s (110). With it all 20 good-bot rounds end by points in 34 to 73 s (median 46.6 s; before, every round ran to the 90 s cap), the lazy bot wins 0.55 (before 0.10, the floor of its band), and the suite takes 141 s (before 178 s). The ball crosses the wall in 0.75 to 1.3 s: whether a person can follow it is judged in the live smoke, and the numbers go back toward Q34's if not
deadline: the first live smoke
answer:
status: defaulted (standing instruction)

### Q41: When does the end card say "BEST!"?
asked: it8 (verify)
default: only when this session set tonight's new best, and only for a score above 0. Today the card says it whenever the score is equal to or above tonight's best after the session, so a round lost 0 to 5 says "BEST!", and so does every later round that ends on the same score (evidence/it08/pong-128x64-plain.png). The change is C43 and goes through the next arcade plan; nothing was changed in it08
deadline: the next arcade iteration
answer:
status: defaulted (standing instruction)

### Q42: What controls Pong's paddle: the hand's height, or the body's distance from the camera?
asked: 2026-09-28, by the owner after the first live smoke ("it could be funner moving your whole body back and forth towards the camera to be the paddle control")
default: none taken; the loop is gated and the owner is in the session. The operator's lean: the body's distance, read from `Body.scale` (nose to hip in the frame, already in `Sensed`), smoothed, with the raised hand kept only to start the game; the ball slowed to a body's speed. The hand path's faults (C44) are fixed in the engine either way, because other games point with a hand
deadline: the arcade's next iteration
answer: "yes, do it now as iteration 9. I was jerky and laggy. Didn't appear to have a good read on my hand." The body's distance from the camera moves Pong's paddle; it is built now, as iteration 9, before the show daemon (this changes Q33's order by one iteration; after iteration 9 the loop gates again). The hand path's faults (C44: jerky, laggy, a poor read of the hand) are fixed in the engine
status: answered (owner, 2026-09-28 20:50 CDT)

### Q43: In Pong by the body, which way does the paddle go?
asked: it9
default: stepping towards the camera moves the paddle up (`NEAR_IS_UP = True`)
deadline: the second live smoke
answer:
status: defaulted (standing instruction)

### Q44: Does the Mac's camera capture faster than 10 a second?
asked: it9
default: the default stays 10 in this iteration: `arcade.toml` must equal the defaults, every grace is sized in captures, and the noise and Pong's tuning were measured at 10. `Glide` moves the paddle on every tick between captures. For the owner's trial the file `arcade.mac.toml` sets `camera_fps = 30` (`arcade run --config arcade.mac.toml`); inference runs in the camera's own thread at about 11 ms a frame
deadline: the second live smoke
answer:
status: defaulted (standing instruction)

### Q45: How does Pong tell a player to move their body?
asked: it9
default: two lines at 1x in amber, "STEP IN = UP" and "STEP BACK = DOWN", at the first serve and again after 5 s in play without travel, fading in and out, drawn under the ball
deadline: the second live smoke
answer:
status: defaulted (standing instruction)

### Q46: What is Pong's pace for a body?
asked: it9
default: before tuning: the ball 55 to 95 px/s (gain 1.08, angle at most 50 degrees), the paddle 3 by 16 px, the CPU at 0.35 wall heights a second. This sets Q40's fast ball aside: it was tuned for a hand. No budget is loosened
deadline: the second live smoke
answer:
status: defaulted (standing instruction)

### Q47: How far must a player step?
asked: it9
default: about 0.5 m nearer to 0.7 m back from where they raised their hand covers the wall's height (`DEPTH_SPAN` 0.6); after 2 s at an end the middle follows the player. A still player scores nothing: a rally counts when the paddle travelled 12 px or more (C42, Q35)
deadline: the second live smoke
answer:
status: defaulted (standing instruction)
