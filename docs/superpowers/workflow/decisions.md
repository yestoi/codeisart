# Decisions — wall arcade

Every question put to the owner, one block each. The loop appends a block when it asks, and
transcribes the owner's answer under it before acting on it. A block with an empty `answer:` line is
open. Loop-decidable questions are never asked here; they are journaled. At the deadline an
unanswered question takes its default and is marked `defaulted`; the owner can override it later.

Block format:

```
### Q<n>: <question>
asked: it<N>
default: <what the loop does if no answer by the deadline, or "none (blocks)">
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
