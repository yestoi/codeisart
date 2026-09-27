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
