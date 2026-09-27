# Roadmap — wall arcade
**End goal:** A camera-and-microphone arcade for the two-panel LED wall that a stranger at a festival is playing within ten seconds of walking up, unprompted: the attract director shows a mirror of them, a wordless hand-up pictogram invites them, a game starts at once, the three-door menu is opt-in, and the session ends when they leave. Every game is verifiable headlessly on the Mac from scripted and recorded inputs, producing contact sheets, GIFs and feel metrics an agent can judge, with no game code that knows which machine it runs on. 128x32 is the design layout, chosen for two-player side-by-side play, and 64x64 is first-class for single-player games and square visuals. The arcade runs on its own Raspberry Pi 5 driving the spare Colorlight 5A-75E with the raw Colorlight backend, leaving the show Pi 4 untouched. The game list is the one the owner accepted from the review: Copy Me as the hero, Pong, Quick Draw, Dodge, Tug, Flap, Swat, Paint, Strongman and Freeze, with life, beat and the puppet mirror in the attract catalog.

Source documents: the arcade spec as amended by spec revision 3, the core plan with its amendments, and docs/superpowers/reviews/2026-09-26-arcade-adversarial-review.md (sections 6, 7, 10a).

## Milestones
- [x] M0 (owner, before launch): spec revision 3 (44d860a) and plan amendments (0c0bd8e) landed 2026-09-26; pre-flight checklist (operator design section 10) is the owner's remaining part.
- [ ] M1: Task 0 environment spike (uv, Python 3.12, pins, one OpenCV, `doctor`); foundation Tasks 1 and 2 as renumbered by spec revision 3 (the raw Colorlight backend task per the hardware decision).
- [ ] M2: Sensed with timestamps, velocity, `player`, `present`, zone; actors with `degrade` and festival scenes; canvas with text scale; look with the metre-aware `distance`.
- [ ] M3: game protocol with `SCENARIOS`, `_xy`, `MENU_ORDER`, and `GameInfo.layouts`; runner with session rules, flash governor, brightness limiter; attract director with four modes and the mirror.
- [ ] M4: the new walk-up flow and opt-in three-door menu; paint; contact sheet with provenance and black refusal; REPL with `--log`; `tools/arcade_evidence.py`; feel metrics and budgets (per layout); bots; counterfactual and `_xy` tests.
- [ ] M5: sources (blobs on lores, gated motion grid, MediaPipe unflipped with shared mirroring, audio with voice band and clap), record with `--script` and `--raw`, calibrate.
- [ ] GATE A (human): record the real-input fixture set, first live smoke on both layouts (live-smoke.md), confirm dwell and presence thresholds, approve game order for the second plan.
- [ ] M6: project skills (`arcade-verify`, `wall-look`, `arcade-game-authoring`) and the vendored `cv-mediapipe` and `game-feel` skills.
- [ ] M7: second plan, games in the approved order (default: Copy Me, Pong, Quick Draw, Dodge, Tug, Flap, Swat, Strongman, Freeze), two per iteration; an iteration's evidence is a gate only when a keep-or-cut question arises.
- [ ] GATE B (human): Pi 5 in hand; Pi config, `pi_perf` budget on the Pi 5, IMX500 source with munkres and scipy, plan Task 24 (systemd unit, status file, thermal policy).

## Carried fixes
(none)
