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

### Q48: Is the body's size held when the hips leave the camera's view, inside iteration 9?
asked: it9
default: yes, as one more task of iteration 9 (S3, the plan's amendment). The owner's hand-read spike (branch `spike/hand-read`, docs/superpowers/reviews/2026-09-28-hand-read-spike.md) measured that without hips the size falls back to 1.25 shoulder widths, which read 0.16 against 0.26 measured on the owner. Pong by the body reads that size: a hip dropout would throw the paddle to the far end, and stepping in is when the hips leave the frame. The tracker learns each person's size per shoulder width while the hips are seen and uses it when they are not. The spike's other findings (the full model, 30 captures a second, duplicate poses, the hand point, the cursor's hand switch) wait for the arcade's return (C45 to C47 in the roadmap)
deadline: the second live smoke
answer:
status: defaulted (standing instruction)

### Q49: After iteration 9, does the loop stop at a gate?
asked: it9
default: by Q42 the loop gates after iteration 9 and waits for the owner before the show daemon
deadline: none
answer: the owner, 2026-09-28 23:10 CDT, before the gate was written: "I finished the spike. I will do the new pong smoke test in the morning. Lets continue onto the show daemon and other iterations until you need me next." The loop does not gate after iteration 9. It goes on to the show daemon's foundation tasks (Q33) and keeps iterating; it stops only for what config.md's rule 8 names (a destructive or irreversible action, a change of scope or end goal, the iteration cap). `iterations-per-run` is 6
status: answered

### Q50: Does the show daemon limit flashing on the wall?
asked: it10
default: yes, from D3 on. An entry's output is arbitrary: a program can flip the whole 80x23 terminal between reverse and normal video several times a second, on a 512x192 wall at night. The show spec (revision 2) has no rule for it. The show's main loop passes each frame through the arcade's flash governor (`arcade/flash.py`, at most 3 full-field flashes a second) before the push; the curation rules (GATE C) also reject entries that flash. D1 and D2 build no display path, so nothing changes before D3. Adding the governor to the show's loop is a safety slice (a plan review, one round)
deadline: the plan of D3
answer: the owner, 2026-09-28 23:17 CDT: "yes to Q50, use the flash governor." The show's main loop passes every frame through the arcade's flash governor before the push, from D3 on; adding it is a safety slice
status: answered

### Q51: How do the rows split on the Reduced tier (512x128)?
asked: it10
default: `rows = 16`: 80x15 for programs plus the strip on row 16, as the show spec's table in 3.1 says. `cfg.rows` counts the strip on every tier (Full: 24, the terminal 80x23). Nothing in D1 changes for it; the owner sets `height` and `rows` in show.toml when the size tier is chosen
deadline: GATE C (the size tier)
answer:
status: defaulted (standing instruction)

### Q52: What does the strip show before D3, and does it carry the year?
asked: it10
default: the renderer draws the text it is given and cuts it at 80 columns. The sheets use the spec's strings (4.4) with the year added, "NOW: <title> by <author>, <year>, Not A.I. | NEXT: ...", matching the plaque (spec 3.5 revision 2: "Created by <author>, <year>, Not A.I."; the core plan's older text has no year). D3's `strip()` builds the real text
deadline: the plan of D3
answer:
status: defaulted (standing instruction)

### Q53: Which wall do the show's LED sheets show, and what can the 128x64 prototype show?
asked: it10
default: the sheets render the full 512x192 wall: 128x64 cannot hold 80 columns of 6 px. The prototype shows a 128x64 window of the wall, 21 columns by 8 rows, in the sheets by `--crop` and on the panels by D4's test pattern. No scaled-down terminal mode is built
deadline: GATE C
answer: relayed 2026-09-29 00:32 CDT by the owner's other session (codeisart-5d), not said to the operator: "yes, add the ink mode for the PoC". The 2 x 2 128x64 panels are the proof of concept only; the full 80x23 wall stays the goal. This replaces the default's "No scaled-down terminal mode is built": the ink view (`Config.view = "ink"`, show.poc.toml) was built by that session on branch `show-ink-view` (5211a49) and merged by the operator (c28c027). The terminal stays 80x23; each cell is one dot lit by its glyph's ink. The sheets of the full wall stay 512x192. Confirmed by the owner to the operator, 2026-09-29 00:46 CDT: "yes to Q53, the ink mode merge is confirmed"
status: answered

### Q54: Is the attribution strip legible in reverse video on LEDs?
asked: it10
default: the spec's reverse video stays through D1 and D2. The sheets of iteration 10 (evidence/it10/it10-prototype-window.png at the led look, it10-cc-distance.png at 10 m) show the strip's dark letters closing up inside the lit field, while normal text reads well. The strip carries the attribution ("the year is the proof"), so it must read from 15 to 40 feet. D3's plan draws three variants in sheets (reverse at 70 % as now; reverse on a field at about 35 %; bright letters on a field at about 25 %), makes the choice a key in show.toml, and takes the one that reads best at the led and distance looks as the default. The owner judges on the real panels (the 128x64 prototype can show the strip's window: `--crop 16,128,128,64`)
deadline: the plan of D3; the panels at GATE C
answer: the owner, 2026-09-29 00:52 CDT: "For Q54, draw the three strip variants in D3". D3's plan draws the three variants in sheets (reverse at 70 % as now; reverse on a field at about 35 %; bright letters on a field at about 25 %) at the led and distance looks, on the full wall and on the 128x64 proof of concept, and makes the strip's look a key in show.toml. Which variant becomes the default is still the owner's to pick, from the sheets and on the panels; until then the loop takes the one that reads best in the sheets
the loop's reading (it12, 2026-09-29 04:02 CDT, from evidence/it12/it12-strips-led.png, it12-strips-distance.png, it12-strips-row-distance.png, it12-strips-poc.png, it12-strips-poc-distance.png): `bright-on-field` reads best at 10 m on the full wall and on 128x64; `reverse` (the present look) reads at the led look and badly at 10 m; `dim-reverse` lies between. show.toml still says `reverse`: an older test asserts that show.toml equals the code's defaults, so the default changes in the code and in show.toml together, in iteration 13
status: answered (the variants are drawn in D3; the pick is open)

### Q58: What does the strip show on the 128x64 proof of concept?
asked: it11 (raised by the owner's other session, codeisart-5d, 2026-09-29)
default: on 128x64 only 21 characters fit on the strip's text row, so "NOW: hello by Trey, 2026, Not A.I." shows as "NOW: hello by Trey, 2" and the attribution's "Not A.I." is lost. Until the owner decides, D3's `strip()` builds a short form when fewer than 40 characters fit: it alternates every 3 s between "<author>, <year>" and "Not A.I.", each cut to the width (no marquee: scrolling text on a strip that is already hard to read in reverse video, Q54, reads worse). D1 and D2 change nothing: the renderer cuts the text it is given. The full wall's strip is not changed by this
deadline: the plan of D3
answer: the owner, 2026-09-29 00:49 CDT: "For Q58, i'll take your suggestion." When fewer than 40 characters fit on the strip (the 128x64 proof of concept: 21), D3's `strip()` alternates every 3 s between "<author>, <year>" and "Not A.I.", each cut to the width; no marquee. The full wall's strip is not changed
status: answered

### Q55: How are the portrait lightboxes wired, and do they dim?
asked: it11
default: 12 V through a MOSFET each, on the PWM pins [17, 22, 23, 24, 27] (`lightbox_pins`, a new key in show.toml; no pin shared with the buttons or the rings, none on I2C, SPI or UART). Level 0.4 when idle or queued, 1.0 while that station plays. The button rings stay on `light_pins`. show.toml changes when the owner's boards are built
deadline: GATE C (the hardware)
answer: the owner, 2026-09-29 01:33 CDT: "yes to Q55, Q56 and Q57". The default stands: 12 V through a MOSFET each on the PWM pins [17, 22, 23, 24, 27] (`lightbox_pins`), 0.4 when idle or queued, 1.0 while that station plays; show.toml changes when the boards are built
status: answered

### Q56: Does `entries/hello` play on the festival wall?
asked: it11
default: no. It stays in `entries/` for tests, demos and the sheets (station 6, no portrait). Once any entry on stations 1 to 5 is loaded, D3's attract mode and autoplay leave out stations above 5
deadline: the plan of D3
answer: the owner, 2026-09-29 01:33 CDT: "yes to Q55, Q56 and Q57". The default stands: `entries/hello` is not on the festival wall (station 6, no portrait); once an entry on stations 1 to 5 is loaded, D3's attract mode and autoplay leave out stations above 5
status: answered

### Q57: What does the wall print around an entry?
asked: it11
default: the spec (4.3) names the phases, not the words. A shell transcript: the title, the plaque, a blank line, `$ cat <source>` and the source typed, `$ <build>` and the compiler's real output, `$ <run>` and the program. On a failure `*** <reason> ***`, then `$ <run>   (recording)` over the replay of the fallback
deadline: the owner's first look at `python -m show` (D3)
answer: the owner, 2026-09-29 01:33 CDT: "yes to Q55, Q56 and Q57". The default stands: the shell transcript around an entry, as the sheets of iteration 11 show it (evidence/it11/it11-hello-plain.png, it11-hello-fallback-plain.png)
status: answered

### Q59: Is the flash governor fast enough for the full wall on the Pi 4?
asked: it12 (the plan writer's probe)
default: the governor costs 4 to 6 ms a 512x192 frame on the Mac (M1; the worst frame 13 ms), about 0.4 ms at 128x64. On the Pi 4 it may pass the 50 ms of a frame at 20 a second. The loop runs at the rate it reaches: the governor's window is counted in frames, so a slower loop is stricter in seconds, never laxer. D4 measures it on the Pi; a faster governor would be its own safety slice, with a plan review
deadline: D4 (the measure on the Pi); GATE C
answer:
the loop's measure (it13, 2026-09-29, the plan writer's probe on the Mac): 5.06 ms median, 8.62 ms p95, 12.80 ms worst a 512x192 frame on a strobe (4.36 ms median static); 0.36 ms at 128x64. The measure on the Pi 4, and pyte's feed time there, move from D4 to GATE C (the Pi is not in the loop's hands); D4's soak tool reports the governor's cost wherever it runs
status: defaulted (standing instruction)

### Q60: May the governor hold fast typing on the 128x64 ink view?
asked: it12 (the plan writer's probe)
default: accepted on the proof of concept. In the ink view a cell is a dot, so typing at 400 characters a second changes a large share of the picture: the governor holds something on 21 % of the frames, up to 15 % of the pixels in one frame (on the full wall at most 2 %). Attract at 3 lines a second, hello's band, the cursor and the strip's alternation are not held in either view. The governor is not loosened for it
deadline: the owner's first look at the proof of concept on the panels
answer:
status: defaulted (standing instruction)

### Q61: Does the attract strip alternate on the 128x64 proof of concept?
asked: it12
default: yes. `PRESS A BUTTON ON ANY PORTRAIT` is 30 characters and 21 fit, so on 128x64 the attract strip alternates every 3 s between `PRESS A BUTTON` and `ON ANY PORTRAIT`, as the playing strip does by Q58. The full wall's strip is unchanged
deadline: the owner's first look at `python -m show --config show.poc.toml`
answer:
status: defaulted (standing instruction)

### Q62: What does a press on a portrait with no entry do?
asked: it12
default: the press is acknowledged: the keypress cue plays and the button's ring flashes; nothing is written on the strip and nothing is queued (spec 4.5: every press is acknowledged)
deadline: GATE C (all five stations have entries by then)
answer:
status: defaulted (standing instruction)

### Q63: May the show's unit order itself after `network.target` instead of `network-online.target`?
asked: it13 (the plan writer; the it12 review's note)
default: the unit is unchanged. With no carrier the start waits for wait-online's timeout and then runs; `deploy/README.md` says so. Spec 4.6 wants the loop up, and the Colorlight path needs the link, not the network; but the change edits the asserts at `tests/test_deploy.py:17-18`, which the loop does not change without the owner's word
deadline: GATE C
answer:
status: defaulted (standing instruction)

### Q64: Should the pattern tool have a full `white` pattern (the core plan's dead-pixel hunt)?
asked: it13 (the plan writer)
default: not built. `tools/wall_pattern.py` keeps its rule that no pattern lights half the wall, and the repository has no figures for the panels' current at full white against the power supplies. With those figures from the owner the loop adds `white`, capped at brightness 0.1, with its own refusal and test. Until then `grid`, `rgb`, `index` and `panels` find dead pixels only where they light
deadline: the full wall's bring-up
answer:
status: defaulted (standing instruction)

### Q65: What should the wall do after repeated failed pushes (a torn frame the governor never saw)?
asked: it13 (the review; evidence/it13/review-probes/p2_torn_base.txt)
default: the wall holds. After a failed push the wall sends the last governed frame again and takes no new frame until one second has passed without a failed push; the governor goes on counting from the frame it holds. The wall does not go dark by itself (spec 4.6: the wall is never blank), and the failures are logged and counted as today. Why: the Colorlight push sends the frame packet and then the rows, so a send that fails between the rows leaves a mix of two frames on the card for a tick; with a failure on every second or third push a 32x32 square made 7 transitions against the budget of 6. A pulled cable fails at the first packet and shows nothing of this. The other choice is a dark wall after N failures in a row. Built in iteration 14's safety slice (C51), with a plan review. The loop's measure (it14's plan, evidence/it14/plan-probes/p4_single.txt): this default closes the repeated tears (at most 3 transitions) but not one tear on the budget's last change, which still reads 7; the hold that is built is Q66's
deadline: the first run of the show on the real panels with people in front of it
answer:
status: defaulted (standing instruction); replaced by Q66's default in iteration 14

### Q66: After a failed push, may the wall stand still for three seconds (a quiet hold) and not send every tick?
asked: it14 (the plan writer; evidence/it14/plan-probes/)
default: yes, quiet. After a failed send nothing is sent for 1 s; then the last governed frame is sent; 1 s later it is sent again; 1 s later new frames start. Any failed send starts the hold again. The wall is frozen for 3 s or more after each failure, and a dead link is sent to once a second. The close is never held. Why: a torn frame (new rows over old rows) makes a 32x32 square that straddles the tear overshoot, and the return from the overshoot is a transition the governor never counted; Q65's resend on every tick puts that return right behind the tear (7 transitions against the budget of 6 for one tear on the budget's last change); the quiet hold puts a second between every change (at most 6 in every case the probes tried, in both display models). It needs the Colorlight card to keep its last picture through a second without packets. The owner's check on the real panels: stop the sender for 3 s; the picture must stay, not go black. This check is a safety gate, not a nicety (it14's plan review, evidence/it14/plan-review-probes/r6_blank_close_dark.txt): on a card that blanks without packets the hold itself breaks the budget, 7 to 8 transitions in a second with flash area 0.5 on a reversal (0.281 on a block strobe), for a card that blanks after 0.1 s, 0.5 s or 0.9 s. If the card blanks, tell the loop before the show runs in front of people: the hold then needs another form. Q65's resend is no safe fallback either (7 for one tear on the budget's last change); until the hold has its other form, a wall with a blanking card and failing pushes must be stopped by hand. The plan review also found that the hold must reset the governor at its end (B1: re-initialised in place and primed with the counted frame, not sent), or the second after the hold reads 7; that is in the plan that is built
deadline: the first run of the show on the real panels with people in front of it
answer:
status: defaulted (standing instruction)

### Q67: May the arcade's runner count its governor's first frame against black (C52 for the arcade)?
asked: it14 (the plan writer)
default: not changed. Priming the runner's governor with one black frame at birth makes `tests/arcade/test_headless.py:227` read 301 governor calls where it asserts 300 (six cases); the loop changes no assert of the arcade without the owner's word. The arcade starts on the dark lobby, so its first frames do not flash today. The show's half of C52 is built in iteration 14 (`from_dark=True`, passed by every caller). With the owner's yes the loop primes the runner and changes that one number
deadline: the arcade's first night in front of people
answer:
status: defaulted (standing instruction)

### Q70: May Dodge ship as side steps under falling rocks, not as the spec's jump and duck?
asked: it15 (the arcade's plan writer; docs/superpowers/plans/2026-09-29-it15-arcade-pose-games.md)
default: yes, side steps only in iteration 15. This is NOT the spec's Dodge (spec 8, game 5: "the dinosaur game with your body: jump low obstacles, duck high ones", a run of at most 90 s). The game built: rocks fall, the player steps left and right (the body's x in the zone, the tracker's steadiest signal), the speed ramps, a run ends on the first hit or at 45 s, and every third rock is aimed at the player so that a still body is hit. Why: jump and duck need the shoulders' height against a baseline, which the bots' `Move` cannot drive and which wants a level camera (not measured by the spike). With the owner's no, the game is renamed or remade; with a yes, jump and duck can be added later as a second control
deadline: the owner's first play of Dodge (a live smoke)
answer:
status: defaulted (standing instruction)

### Q71: May Quick Draw's WAIT be 2 to 5 s (the spec says 2 to 6 s)?
asked: it15 (the arcade's plan writer; docs/superpowers/plans/2026-09-29-it15-arcade-pose-games.md)
default: yes, 2 to 5 s, for pace and for the suite's time (every bot play waits it out)
deadline: the owner's first play of Quick Draw
answer:
status: defaulted (standing instruction)

### Q72: What is Quick Draw's solo score and best?
asked: it15 (the arcade's plan writer; docs/superpowers/plans/2026-09-29-it15-arcade-pose-games.md)
default: rounds won (0 to 3). The spec's solo "chases the night's fastest" draw needs a best where lower is better, which `Scores` does not have; the fastest draw is shown in the round's result only. A duel records nothing (Q23)
deadline: the owner's first play of Quick Draw
answer:
status: defaulted (standing instruction)

### Q73: When does the arcade move to the full pose model and 30 captures a second (the spike's settings)?
asked: it15 (the arcade's plan writer; docs/superpowers/plans/2026-09-29-it15-arcade-pose-games.md)
default: not in iteration 15. The full model, `camera_fps` 30 and the graces counted in seconds (Q44) go together, in a later iteration: the graces need `arcade/runner.py`, which iteration 15 does not edit. Only the spike's hand point lands now (the wrist is the mean of the wrist, pinky and index landmarks)
deadline: the arcade's next engine iteration
answer:
status: defaulted (standing instruction)

### Q74: May the learned torso also move the raise line when the hips are not seen?
asked: it15 (the arcade's plan writer; docs/superpowers/plans/2026-09-29-it15-arcade-pose-games.md)
default: yes, one torso for all. `Body.torso` without hips uses the person's learned torso per shoulder width, and the reach box, the cursor and the raise line follow from it: the raise line sits about 0.03 of the frame higher on the owner than with the fixed 1.25
deadline: the owner's next live smoke
answer:
status: defaulted (standing instruction)

### Q75: When a body is first measured, does `Depth` keep the paddle where it is or recentre it?
asked: it15 (the arcade's plan writer; docs/superpowers/plans/2026-09-29-it15-arcade-pose-games.md)
default: it keeps the paddle where it is: the new centre is taken so that the reading does not jump (C47), and the jump is neither travel nor activity
deadline: the owner's next live smoke
answer:
status: defaulted (standing instruction)

### Q68: May a stop within 3 s of a failed push take up to 2 s to darken the wall?
asked: it15 (the close's plan writer; docs/superpowers/plans/2026-09-29-it15-close-in-a-hold.md)
default: yes. While the wall holds after a failed push, the close waits until the hold's next send is due (at most 1 s, nothing sent), sends the counted frame if the hold has not sent it yet and waits 1 s more, makes the governor again from the counted frame, and then sends two governed black frames; the display is closed in every case. Without a failed push the stop is as fast as before (about 0.06 s). This replaces Q66's line "The close is never held". Why (C53): a close right behind a torn push read 7 to 8 square transitions against the budget of 6. The service's stop limit is systemd's default of 90 s. `deploy/README.md`'s "Stop" text (two black frames, then exit) is not changed by the loop: the owner's. Ctrl-C during the wait ends the close at once: the display is closed and the wall stays as the tear left it
deadline: the first run of the show on the real panels with people in front of it
answer:
status: defaulted (standing instruction)

### Q69: May the close go black after the first quiet second, without the counted frame (1 s at most, not 2)?
asked: it15 (the close's plan writer; docs/superpowers/plans/2026-09-29-it15-close-in-a-hold.md)
default: no, the counted frame stays: the quiet second, the counted frame, a quiet second, black. Going straight to black also read at most 6 and flash area 0.000 in the plan writer's probes, and is 1 s faster, but it changes an existing assert (`tests/test_wall_close.py:69`, the loop's close after a failed push sends the counted frame first), which the loop does not change without the owner's word
deadline: the first run of the show on the real panels with people in front of it
answer:
status: defaulted (standing instruction)

### Q76: Does Quick Draw keep its full-wall white flash on the signal?
asked: it15 (the operator, from the sheets; measured by the arcade's reviewer, evidence/it15/reviewer-arcade.md, point 5b)
default: yes, as built, until the owner has seen it on the wall. On DRAW the game asks `fx.flash` for white, 0.15 s: the raw frame is the whole wall white for 5 ticks; the limiter pushes it at level 0.502 (its floor of 0.5; every channel 128), which is 4.2 times the day's cap on average light and 8.4 times the night's, for 0.17 s. It is inside the flash rules: at most one such flash in any 4.5 s, the governor holds nothing, square transitions 4 of 6, flash area 0.000. It is the arcade's first full-field flash. Its cost: the limiter lets the light back slowly, so `DRAW!` and the bars stand at 51 to 71 percent light for the first 0.67 s after the signal, which is the time the player reacts in. The other choice: no flash, the word `DRAW!` turning white is the signal (a change to the game and its tests, for a plan)
deadline: the owner's first play of Quick Draw on the panels
answer:
status: defaulted (standing instruction)

### Q77: May Dodge return to main if the suite with it reads under its limit on an idle machine?
asked: it15 (the operator; the orchestrator cut Dodge by the plan's cut order when a suite run read 334.84 s against 330 s under load)
default: yes. The limit is the loop's own number and is not raised. The run that cut Dodge was made at a load of 2.4 to 4.3 with other sessions on the machine; the run before it, with Dodge, read 321.11 s. The operator times the suite with Dodge on the idle machine; under 330 s Dodge returns by a revert of 16dbb91, else it stays cut and whole on commit c49d902. The arcade's review found nothing else that blocks it. The outcome (2026-09-29 11:16): the operator's run with Dodge, no agent beside it, read 335.87 s (1364 passed; load 1.7 at the start, 6.1 at the end from the desktop's own processes). Three runs with Dodge now read 321.11, 334.84 and 335.87 s: the suite with Dodge stands at its limit, so Dodge stays cut. It returns by a revert of 16dbb91 once the suite has room: Dodge costs about 45 s, 26 s of it the oracle's 20-seed feel report; a plan that shares or marks the oracle's reports comes first (roadmap.md, the it07 note), or the owner raises the limit
deadline: iteration 15's report
answer:
status: defaulted (standing instruction)

### Q78: In Quick Draw, when player 1 leaves and a body with another id takes their seat, is a best banked?
asked: it15 (the arcade's reviewer, round 2, finding N1: evidence/it15/reviewer-arcade-round2.md; reproduced 3 seeds of 3 through the real runner)
default: no. A match in which more than one body id sat in seat a banks no best, as a duel banks none (Q23). The rounds stay with the seat and the play goes on. The tracker gives a player who is back after the grace a new id too, so the game cannot tell them from the next person in the queue: a player who steps out for longer than the grace and comes back plays on with their rounds and banks no best for that match. A player back inside the grace banks as before. The other choices: the seat's rounds go to 0 for a new id (a player who is back loses their rounds); or the match ends when player 1 is gone longer than the grace (the runner's leave rule does that after 8 s with nobody in view, but a newcomer's presence keeps the session alive)
deadline: the owner's first play of Quick Draw on the panels
answer:
status: defaulted (standing instruction)

### Q79: On the Pi 5, is the flash governor made faster, or is its 0.5 ms budget set for the Pi?
asked: the owner's session on the Pi 5, 2026-09-30 (the Pi's first full suite: six failures, all the governor's 0.5 ms; docs/superpowers/reviews/2026-09-29-route-a/00-bench.md, section 3)
default: none taken; the owner answered in the session
deadline: none
answer: "yes", to: the budget is set for the Pi. The two tests read the governor's budget from `ARCADE_GOVERNOR_BUDGET_MS`, 0.5 when it is not set (the Mac's, unchanged), 2 on the Pi 5, where the governor's median is 0.95 to 1.05 ms at 128x64; the Pi's numbers are in evidence/pi-perf.md. The owner asked first whether this brings the flicker back, and it was tested at the wall: a bar sweeping through the governor and the driver with 0, 20 and 40 ms added to every push. The sender's sync held in all three (it is another process, at real-time priority); the owner saw no flicker in any, and the pushes lost at 40 ms as motion. The governor is not made faster: it would have to be some twenty times slower before the arcade's loop loses a push at 30 a second.
status: answered (owner, 2026-09-30)

### Q80: What does the run after iteration 15 build, and with what leave?
asked: the owner's session, 2026-09-30 evening (the display driver is done and proven on the wall, the Pi 5 drives it; the camera arrives tonight; the owner is building promptviz in another session)
default: none taken; the owner chose in the session
deadline: none
answer: the show's entries. "Show entries": GATE C's Task 19 on the operator, as the D5 line in roadmap.md (the five researched picks fetched, built, configured, governed, sheeted and recorded, a wall check left for the owner's morning). "Yes" to fetching the sources from github.com/ioccc-src/winner over the network (CC BY-SA 4.0; the sources land under entries/ with their licence and attribution). "Yes, no wall output" to the Pi 5 over ssh (trey@codeisart.local, ~/codeisart on main, gcc 14.2, unshare 2.41) for Linux-only checks: builds and the sandbox tests run there; the sender is never started and the wall stays as the owner left it. The arcade waits (the owner's live smokes of Pong and Quick Draw come first, on the camera). The run is iterations 16 to 19 (config.md iterations-per-run: 4); every plan of the run gets one adversarial review round (the owner's ask of 2026-09-30, docs/superpowers/plans/2026-09-30-paced-rows.md's precedent), not only safety slices.
status: answered (owner, 2026-09-30)

### Q81: In the run of Q80, what is the suite's limit, what do iterations 18 and 19 do if D5 is done early, and are the entries sheeted at the Reduced tier?
asked: the owner's session before the launch, 2026-09-30 night (the pre-flight at 4ec98e4: the suite reads 1762 passed, 3 skipped in 319.03 s on the idle Mac against it15's limit of 330 s, the owner's driver work having added about 450 tests and two skips; the roadmap sends the loop to M7a once the D lines need the owner while Q80 says the arcade waits; D5's evidence names the full tier and 128x64 only)
default: none taken; the owner answered in the session
deadline: none
answer: "I'll take the recommendation", to all three. (1) The suite's limit for this run is 420 s on an idle machine. No entry is reverted or left out for the suite's time under that limit; the curated entries' tests stay short (one build an entry, runs cut by the fake clock). The baseline of 1762 passed and 3 skipped is the one the verify checklist counts from (the two new skips are the driver's `/proc` tests on the Mac). (2) If D5 is done before iteration 19, the iterations left are D5's slack first (a replaced entry, the review's fixes, the Reduced-tier sheets), then only the suite's time (the roadmap's note "it15 (every plan)") with Dodge's return by `git revert 16dbb91` (Q77); no new game and no other arcade work, which waits for the owner's live smokes. With none of that left the loop gates. (3) Each entry is also sheeted at the Reduced tier (512x128, 15 program rows and the strip): the spec's criterion 3 for the size tier (3.1), so that the owner can decide the tier from the sheets. The sheets report; an entry that does not survive at 15 rows is not changed or dropped for it.
status: answered (owner, 2026-09-30); its (3), the Reduced tier's sheets, is withdrawn by Q82

### Q82: Which wall does the run of Q80 build and judge for?
asked: the owner, 2026-09-30 night, on reading Q81's record before the launch
default: none taken; the owner said it
deadline: none
answer: "420 is fine. We are developing against our 2x2 panel wall for tonight. Do not make code for a bigger panel we do not have." The run's wall is the 2 x 2 wall in hand, 128x64 (`show.poc.toml`, the ink view): the sheets, the governor's numbers and every judgement of an entry are made there. No code, config, test or tuning is made for a wall the owner does not have: Q81's Reduced-tier sheets are withdrawn, the full tier's sheets are not made in this run (the probe's stand, evidence/probe-entries-2026-09-30/), and a finding that shows only at a bigger size is one line in the journal, not a fix (a safety gap is carried under Loop rule 5 as always). The terminal is not the wall: it stays 80 columns by 23 rows and the strip, the size the entries were written for, and D5's `rows` key stays (the donut's tear is the pty's, whatever the view). Tests that exist at the default `Config()` are left as they are. Q81's (1), the 420 s, and (2), the iterations left, stand.
status: answered (owner, 2026-09-30)

### Q83: In the run of Q80, how does the operator share the Pi 5 and the Mac with the owner's other sessions?
asked: the owner, 2026-10-01 00:13 CDT, while iteration 16's plan was being written (the Pi 5 is shared tonight with promptviz's corpus screen; another session also works on the Mac)
default: none taken; the owner said it
deadline: none
answer: "The Pi is shared tonight with promptviz's corpus screen. Wrap every Pi command in `flock -w 300 /tmp/pi5.lock` inside the ssh call; if the lock is not free in 5 minutes, do Mac work and retry. Do not rely on files left in /tmp on the Pi. Another session is also working on the Mac: re-read a suite time over the limit or a timing failure once before deciding anything on it." (1) Every Pi command is `ssh trey@codeisart.local 'flock -w 300 /tmp/pi5.lock <command>'`: the lock is taken on the Pi, inside the ssh call. When flock gives up after 300 s the operator goes on with the Mac's work and tries the Pi command again later; a Pi check that never got the lock is journaled as not run, never as passed. (2) Nothing is kept on the Pi between two ssh calls: a command that needs the tree or an entry brings it in the same call (a `git archive` piped over ssh into a `mktemp -d`), uses it and removes it. (3) On the Mac a suite time over the limit (420 s) or a timing failure is measured once more before anything is decided on it (a cut, a revert, a finding, a carried fix); the journal gives both readings. One ssh call of the operator at 00:08 CDT ran before this answer without the lock: read-only (`git log`, `git status`, `gcc --version`, `unshare --version`, `pgrep`, `uptime`), it left nothing on the Pi.
status: answered (owner, 2026-10-01)

### Q84: In the run of Q80, how far does the loop go before it needs the owner?
asked: the owner, 2026-10-01 00:19 CDT, while iteration 16's plan was in its review
default: none taken; the owner said it
deadline: none
answer: "For tonights run, do as much work as possible before I am needed at the wall." The loop's reading: everything of D5 that does not need the owner's eyes on the panels is done in this run without a stop: the entries built, tested, reviewed, sheeted at 128x64, recorded, checked on the Pi 5 under Q83's lock; the review's fixes and a replaced entry in the iterations left (Q81); then the suite's time with Dodge's return (Q81). No question stops the loop (rule 8: the default is taken and listed). What needs the wall is not done by the loop and is made ready for the owner instead: one sheet for the wall session, docs/superpowers/workflow/evidence/itNN/wall-session.md, with the commands in order, what to look at for each entry (the strip, the donut's 24 rows, the plasma's light under the governor, the clock's width), the sheets' numbers to compare against, and the open questions each look answers. The rule 9a limits stand (no `python -m show` with a wall backend, no sender, no systemctl on the Pi by the loop).
status: answered (owner, 2026-10-01)

### Q85: Which of endoh3's two programs does the wall build, the plain clock or the archive's Unicode variant?
asked: it16 (the plan writer; plan docs/superpowers/plans/2026-10-01-it16-five-entries.md, E-endoh3). The roadmap says the wall builds each entry's `.alt.c`; the probe built `prog.alt.c` and saw an 89-character line
default: `prog.c`, the plain ASCII clock, with `rows = 24`; `prog.alt.c` is not copied. `prog.alt.c` prints 23 lines of 85 columns, seven of them with one three-byte Unicode letter (the 89 was a byte count): on 80 columns the lines wrap and the wall draws those letters as `?`. `prog.c` prints 23 lines of at most 79 columns, ASCII, and stays so over three generations on the Mac and on the Pi (evidence/it16/pi-probe-early.md). The research ran the 79-column clock too. The other choice: leave the entry out and take an alternate from the research notes
deadline: the owner's look at the entries on the wall (GATE C)
answer:
status: defaulted (standing instruction)

### Q86: Does imc's tour keep its last two views, which look nearly alike?
asked: it16 (the plan writer; E-imc). The tour is six views at 78x22, 6 s each: the probe's 16-shade Mandelbrot, then the five of the archive's try.sh; the last two (`-limit 256`, `-limit 1024`) light 469 and 471 cells and look nearly the same, and the fourth (`-centre 1 2`) lights only 10 rows
default: kept, all six, in the archive's order. The other choice: drop one of the last two and hold the others longer
deadline: the owner's look at the entries on the wall (GATE C)
answer:
status: defaulted (standing instruction)

### Q87: Does the plasma (thadgavin) run at the archive's speed even if the governor holds it often?
asked: it16 (the plan writer; E-thadgavin). The entry is built with the alt's `-DZ=30 -DZS=0`; its whole-screen redraw is the flash question, and the governor's numbers at 128x64 come with the sheets
default: kept at Z=30; the numbers (held, area, squares) go to the owner with the sheets and the wall decides. Nothing is tuned for the governor before the owner has seen it. The other choice: a slower Z
deadline: the owner's look at the entries on the wall (GATE C)
answer:
status: defaulted (standing instruction)

### Q88: Is a fallback recording over 5 MB committed?
asked: it16 (the plan writer; the operator's fallback step). `fallback.cast` lives in the entry directory and is tracked (spec 4.3)
default: no: a cast over 5 MB is not committed and the journal says so. The plan review measured the five casts at about 0.02 to 1.5 MB, so the rule should not bite
deadline: none
answer:
status: defaulted (standing instruction)

### Q89: In the run of Q80, what does the operator tell the owner while he sleeps?
asked: the owner, 2026-10-01 01:13 CDT, as the build of iteration 16 ran
default: none taken; the owner said it
deadline: none
answer: "I don't need updates anymore unless important sendmessages you can send me for outcome changing decisions or important findings. Going to sleep and setting up remoteconnect." No routine progress goes to the owner: progress is state.md and the journal. A push notification goes out only for a decision that changes the outcome (an entry cut or replaced, a safety gap, a gate, a run that cannot go on) or an important finding, and for something the owner must do before the wall session. The milestone report at an iteration's end is the journal entry and one or two lines in the session, without a push unless it holds one of those.
status: answered (owner, 2026-10-01)

### Q90: At the wall session, does the show reach the card as a plain user with two capabilities, or as root?
asked: it16 (the operator, writing evidence/it16/wall-session.md). Every wall run so far was `sudo .venv/bin/python <tool>` (the pattern tool, the arcade, the bench). The show builds and runs the entries, so under `sudo` the five IOCCC programs would run as root on the Pi; `deploy/show.service` runs the show as a plain user with `AmbientCapabilities=CAP_NET_RAW CAP_SYS_NICE`. The show daemon has never driven this wall (the wall-session sheet's "step one")
default: the wall session plays the entries through `sudo systemd-run --pty --collect --uid=trey -p AmbientCapabilities='CAP_NET_RAW CAP_SYS_NICE' -p WorkingDirectory=/home/trey/codeisart ... -m show --config show.poc.toml --backend colorlight --play <name>`, the unit's settings by hand; not `sudo python`. The form is unproven as a whole (the sender's real-time child under a unit as user trey was proven dry on 2026-09-30). The loop runs neither (rule 9a). The other choice: `sudo python` as the tools did, the entries as root
deadline: the wall session (GATE C)
answer:
status: defaulted (standing instruction)

### Q91: Is the short strip's cut attribution fixed by wrapping it over more alternations?
asked: it16 (the operator's read of the sheets, the reviewer's note). At 128x64 the strip holds 21 characters and shows `f"{author}, {year}"[:21]` and `Not A.I.` in turn (Q58); thadgavin's reads `Gavin Buttimore and T`: the second author and the year never reach the wall. The other four fit
default: iteration 17 (D5's slack) wraps a long attribution at word boundaries into pieces of at most the strip's width and shows them in turn before `Not A.I.` (`Gavin Buttimore and`, `Thaddaeus Frogley,`, `2000`, `Not A.I.`), three seconds each as today; an attribution that fits is shown as today. A carried fix under rule 5a (C54). The other choices: a shorter `author` in the entry's `entry.toml` (it changes the credit), or a scrolling strip (motion on the strip, more light changing)
deadline: iteration 17's plan
answer:
status: defaulted (standing instruction)

### Q92: Does imc's tour keep its third view, which at this size is one lit block?
asked: it16 (the operator's read of the final sheets, evidence/it16/it16-imc-p1.png, 20 s to 25 s). The tour's third view (`-limit 1024 -julia 2 -2.5`, the archive's try.sh's) prints `*` in every one of its 78 x 22 cells: on the wall it is a lit rectangle for six seconds with nothing to read. The first view is a field of shades (the set is the bright body), the second and fourth are clear, the fifth and sixth are the same picture (Q86). It is the program's own output for the archive's arguments, not a fault of the build (the recording's text was read)
default: kept, all six, as Q86 stands; the owner sees it at the wall. Nothing is curated away before the owner has seen it. The other choice: a tour of four views (the first, second, fourth and fifth) of nine seconds each, a change to `entries/imc/tour.sh` and its README section only
deadline: the owner's look at the entries on the wall (GATE C)
answer:
status: defaulted (standing instruction)

### Q93: Is the donut (sloane) clear enough in the ink view, where its body is as bright as the floor under it?
asked: it16 (the operator's read of the final sheets, evidence/it16/it16-sloane-p1.png and -p2.png). "Homer's favorite" draws the donut over a checkered floor of `.` and `#`, and a banner in ASCII letters scrolls along the top row. In the ink view a character is only its light: the donut's shades (`,-+=#$@`) lie between the floor's two levels, so on the sheet the hole and the floor's squares read and the donut's body hardly stands out from them. On a still sheet the turning does not show; at the wall the motion may carry it
default: kept as it is; the wall decides (GATE C: keep, change or replace). No view or brightness rule is changed for one entry. The other choices: none cheap (the program has no switch for the floor; a patched source would no longer be the entry as published)
deadline: the owner's look at the entries on the wall (GATE C)
answer:
status: defaulted (standing instruction)

### Q94: Does the curated test's banner check hold the pipeline's four failure texts itself, or does `show/pipeline.py` export them?
asked: it17 (the plan writer; T-stars). `tests/test_curated_entries.py:195` refused any screen row starting `***`, including a program's own stars (imc's views 5 and 6 and its default view start 8 of 22 rows so). The plan matches only the banner `_fail` writes, `*** <reason> ***`, for the four reasons of its call sites today (`show/pipeline.py:170, 172, 198, 274`), as a pattern kept in the test. A new test plays a real failure of each reason, and another plays imc's fifth view
default: the pattern lives in the test. A fifth reason added to `_fail` later would not match it, but `player.failure is None`, the strongest of the three asserts, still stops it. The other choice: `show/pipeline.py` gets a `banner(reason)` helper or pattern that `_fail` and the test share (a change to the pipeline, outside this slice)
deadline: it17's code review
answer:
status: defaulted (standing instruction)

### Q95: Does iteration 17 also correct the README's strip line?
asked: it17 (the plan writer; O2). The slice names `entries/README.md:29` (thadgavin polls the terminal: `nodelay` and `getch()` each frame, and the show never writes to the pty). Line 33 says the strip shows "<author>, <year>", which C54 makes incomplete for thadgavin's three pieces
default: O2 corrects both lines in one docs commit. The other choice: line 29 only, line 33 left as it is
deadline: O2
answer:
status: defaulted (standing instruction)

### Q96: Does thadgavin's year stay alone on the strip for three seconds?
asked: it17 (the operator's read of the sheets, evidence/it17/it17-thadgavin-p1.png; the code review's note on Q58). Q91's wrap is greedy: at 21 characters `Gavin Buttimore and Thaddaeus Frogley, 2000` becomes `Gavin Buttimore and`, `Thaddaeus Frogley,`, `2000`, then `Not A.I.`. The year is on the wall now (it16 showed `Gavin Buttimore and T`), but for three seconds the strip reads a bare `2000`. Q58 (each text cut to the width) was the owner's answer; for an attribution longer than the strip it is replaced by Q91's default, not by an owner's answer
default: kept, the greedy wrap as built (86f0607); the owner sees it at the wall. The other choices: the year joined to the last name by filling the pieces from the end (`Gavin Buttimore`, `and Thaddaeus`, `Frogley, 2000`), a change to `wrap_words` and its tests; or a shorter `author` in `entries/thadgavin/entry.toml` (it changes the credit)
deadline: the owner's look at the entries on the wall (GATE C)
answer:
status: defaulted (standing instruction)

### Q97: May the suite start 4 worker processes for the oracle's bot plays?
asked: it18 (the plan writer; T-pool, plan 2026-10-01-it18-suite-time-dodge.md). The oracle's 20-seed reports are 95% bot plays (pong about 60 s, quickdraw 24 s, dodge 33 s, one after another). The plan makes them first in plain `python -m tests.arcade.pooled` subprocesses, dealt round robin, and stores them where the reports already look (`tests.arcade.helpers.PLAYS`); no seed, assert or band changes and nothing under `arcade/` changes. The plan writer's probe on the shared Mac: the 180 plays of the three games in 32.5 s with 4 workers, 40.8 s with 3, about 125 s in one process. For about 30 s of each suite run four cores are busy: on the Mac beside the other session, and on the Pi 5 (4 cores) when the suite runs there
default: 4 workers (`PLAY_WORKERS = 4`, capped by the core count), the suite about 60 s shorter (about 270 s, about 300 s with Dodge, against 326 s and 371 s). The other choices: 3 workers (about 8 s slower); every core; or no workers and 5 seeds in the suite with 20 in the evidence tool, which changes what the suite asserts (spec 9.3's count)
deadline: it18's code review
answer:
status: defaulted (standing instruction)

### Q98: Are the loop's evidence images published with the repository?
asked: the owner, 2026-10-01, at the push after the gate of iteration 18: the public repository had grown to 115 MB, 104 MB of it the loop's evidence (85 MB already pushed; the 55 unpushed commits would add 32 MB, 27 MB of it the sheets of iterations 16 to 18). The operator's scan found no key, token, `.env` or recording in the files or the history. The operator offered three choices: make the repository private and push as is (its lean); stay public and push as is; stay public and stop publishing evidence
default: none taken (the owner asked)
deadline: none
answer: "3": the repository stays public and evidence images are no longer published. The operator rewrote the 20 unpushed commits from dc4629c on without the 48 PNGs and the GIF of iterations 16 to 18 (evidence/sha-map-2026-10-01.md has every id before and after; the old commits stay on the Mac under `refs/backup/main-before-evidence-trim-2026-10-01`), and `.gitignore` now leaves PNG, GIF and JPG under evidence/ out of git (config.md, "Evidence images are not committed"). What was already pushed (the images of iterations 1 to 15 and evidence/hardware/) stays as it is; removing it would need a rewrite of the public history and a forced push, which the owner did not ask for
status: answered (owner, 2026-10-01)

### Q99: Do the microphone games and the motion-grid game stay on the arcade's list?
asked: the owner, 2026-10-01, in a session after the gate of iteration 18, on reading what is left to build (M7b: Paint, Tug, Strongman)
default: none taken (the owner decided)
deadline: none
answer: "I do have a microphone, but we are not going to do a yelling thing or clapping thing. I don't have a motion grid. So lets remove those games out." The session told the owner that the motion grid is not hardware (it is computed from the camera's frames) and that spec 13's step 3 has a jump-only Strongman with no microphone. The owner then: "Lets keep tug and rename Strongman to Jump then." So: Tug stays as the spec has it (M7b, with Paint). Strongman becomes Jump (`jump`, title JUMP): the jump phase alone (nose rise over body scale, the bar first, the number at 2x, the best of the night), no roar, no `voice`; it reads pose only and moves to M7a's open games. The list stays ten: Copy Me, Pong, Quick Draw, Dodge, Tug, Flap, Swat, Paint, Jump, Freeze. Neither game was started, so no code changes. What follows from it, the session's reading and the owner's to change: no game reads `voice` or `clap`, so M5's audio source is not built until an attract mode needs it; `Sensed`'s audio fields, the actors and the soak's claps stay as they are (the engine is not changed)
status: answered (owner, 2026-10-01)
