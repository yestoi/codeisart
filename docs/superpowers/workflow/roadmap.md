# Roadmap — wall arcade
**End goal:** A camera-and-microphone arcade for the two-panel LED wall that a stranger at a festival is playing within ten seconds of walking up, unprompted: the attract director shows a mirror of them, a wordless hand-up pictogram invites them, a game starts at once, the three-door menu is opt-in, and the session ends when they leave. Every game is verifiable headlessly on the Mac from scripted and recorded inputs, producing contact sheets, GIFs and feel metrics an agent can judge, with no game code that knows which machine it runs on. 128x32 is the design layout, chosen for two-player side-by-side play, and 64x64 is first-class for single-player games and square visuals. The arcade runs on its own Raspberry Pi 5 driving the spare Colorlight 5A-75E with the raw Colorlight backend, leaving the show Pi 4 untouched. The game list is the one the owner accepted from the review: Copy Me as the hero, Pong, Quick Draw, Dodge, Tug, Flap, Swat, Paint, Strongman and Freeze, with life, beat and the puppet mirror in the attract catalog.

Source documents: the arcade spec as amended by spec revision 3, the core plan with its amendments, and docs/superpowers/reviews/2026-09-26-arcade-adversarial-review.md (sections 6, 7, 10a).

## Milestones
- [x] M0 (owner, before launch): spec revision 3 (44d860a) and plan amendments (0c0bd8e) landed 2026-09-26; pre-flight checklist (operator design section 10) is the owner's remaining part.
- [x] M1 (it01, 040ff3f): Task 0 environment spike (uv, Python 3.12, pins, one OpenCV, `doctor`); foundation Tasks 1 and 2 as renumbered by spec revision 3 (the raw Colorlight backend task per the hardware decision).
- [x] M2 (it02 3017693, it03 e6e31f5): Sensed with timestamps, velocity, `player`, `present`, zone; actors with `degrade` and festival scenes; canvas with text scale; look with the metre-aware `distance`.
- [ ] M3: game protocol with `SCENARIOS`, `_xy`, `MENU_ORDER`, and `GameInfo.layouts`; runner with session rules, flash governor, brightness limiter; attract director with four modes and the mirror.
- [ ] M4: the new walk-up flow and opt-in three-door menu; paint; contact sheet with provenance and black refusal; REPL with `--log`; `tools/arcade_evidence.py`; feel metrics and budgets (per layout); bots; counterfactual and `_xy` tests.
- [ ] M5: sources (blobs on lores, gated motion grid, MediaPipe unflipped with shared mirroring, audio with voice band and clap), record with `--script` and `--raw`, calibrate.
- [ ] GATE A (human): record the real-input fixture set, first live smoke on both layouts (live-smoke.md), confirm dwell and presence thresholds, approve game order for the second plan.
- [ ] M6: project skills (`arcade-verify`, `wall-look`, `arcade-game-authoring`) and the vendored `cv-mediapipe` and `game-feel` skills.
- [ ] M7: second plan, games in the approved order (default: Copy Me, Pong, Quick Draw, Dodge, Tug, Flap, Swat, Strongman, Freeze), two per iteration; an iteration's evidence is a gate only when a keep-or-cut question arises.
- [ ] GATE B (human): Pi 5 in hand; Pi config, `pi_perf` budget on the Pi 5, IMX500 source with munkres and scipy, plan Task 24 (systemd unit, status file, thermal policy); record the Colorlight 5A-75E firmware version with the `rgb` pattern check (brightness and sync behaviour depend on it; C4 from it01); confirm the card honours the brightness packet on that firmware (Falcon Player notes v2.x/v3.x may not) and that it scales light linearly (`dim` assumes it); decide whether to resend brightness every frame, doubled on firmware 13+ (it02 plan review); re-time the look perf test and the tick budget on the Pi 5.

## Carried fixes
Closed: C1-C3, C5-C9 (it02); C4 (it01 report); C12-C16 (it03, e6e31f5).
- C10 (it02; for core Tasks 8 and 9, M3) Cursor and hold robustness: the body cursor is stateless and flips hands when the raised wrist drops out (about 15% of captures at spec 6.4 noise), so consumers need grace or hysteresis. `both_hands_up` holds on only 71% of captures under spec noise, with runs of 3+ missed captures longer than `Hold(grace=0.25)`: size the exit grace per capture and test it under `degrade`.
- C11 (owner Q8; for core Task 15, M5) Add `Blob.id` (-1 = untracked), `vx`, `vy`, set by the blob source; core Tasks 9 and 10 consume them. With it, C17.
- C17 (it03; for core Task 15) A NaN blob becomes an in-zone light at (0, 0) when the zone starts at 0 (`Blob.__post_init__` maps NaN to 0.0 and a Blob has no confidence). Drop non-finite centroids, or have `place_blob` mark them out of zone.
- C18 (it03; next iteration) `circle` draws nothing for radius under 0.5, negative or infinite, while `fill_circle` draws the centre pixel; `_i`'s docstring is wrong for `circle`, and a radius of `10**400` draws 1 px while `1e300` fills. Make `circle` match `fill_circle` at tiny radii and fix the docstring.
- C19 (it03; next iteration) `apply_gamma` at gamma 1.0 returns the caller's own array; return a copy (core Task 11 will write into it).
- C20 (it03; next iteration) Preview guard rails: the `distance` look at `sdl_scale` under 4 has no eye blur (config accepts 1), so require scale >= 4 for `look = "distance"` at config load or document the floor; `PreviewDisplay` validates its settings at construction, not on first push; `render` and `dim` raise ValueError on None.
- C21 (it03 forwarded; core Tasks 8, 12, 14, 18) Every core-plan call that builds `Sensed` or `Audio` uses keywords (Task 8 `sense()` line 2884, Task 12 `decode` 3659/3661, Task 14 line 4157, Task 18 `record` line 5267). Task 12's `decode` builds the empty `(0, 0)` motion grid, calls `place()` on every body, and passes the recording's calibration to anything that re-places.
- C22 (it03 forwarded; core Task 8 or 16) Torso floor: `torso > 0.0` catches only an exact zero; side-on shoulders with hips hidden by the bar counter give a raise line a hair above the shoulders. Use the nose line under a floor (e.g. 0.1 of box height), with a test. The tracker (Task 16) smooths `scale`, which stays 0 with one shoulder and no hip. Spec 5's wording ("the nose only when both shoulders are missing") is spec drift for the next revision.
- C23 (it03 forwarded; core Tasks 13 and 18) `tools/arcade_shot.py` renders `-distance.png` with `render(frame, "distance", scale, gamma, metres=5.0)` at scale 4 or more and saves PNGs only from `tools/` (Task 20's privacy test forbids `.save` in `arcade/`), with the git sha in a PNG text chunk. `build_display` keeps the inner `SDLDisplay(w*scale, h*scale, 1)` wrapped by `PreviewDisplay(inner, look, scale, gamma)`; the runner's `set_brightness` dims the preview.

## Spec revision 4 notes (owner-approved or found drift; fold in at the next spec revision)
- Tick order: limiter, then flash governor, then push (owner Q11; spec 4, 7.2, 8.1 say otherwise).
- Night: clock window OR lux below night_lux, with hysteresis (owner Q12; spec 7.6 lets lux cancel night).
- Flash rule exempts small flashing areas below a field fraction (owner Q13; spec 7.6 is per-pixel).
- Red weighting: a continuous red weight instead of the 0.8 red-share cliff (it04 plan review N2).
- Spec 8's "ship order is the table order" conflicts with owner Q2's ship order; MENU_ORDER follows spec 8's table (it04 N8).
- 2x titles do not fit 42 px doors (it04 N6).
- Spec 5 raise-line wording ("the nose only when both shoulders are missing") vs the torso floor (C22).

## Owner items for the next check-in
- Gamma location (prototype-week decision): with gamma 2.2 modelled, a channel at 40 previews as visible light, so red (255, 40, 40) reads salmon (evidence/it03/it03-128x32-led.png). If the card applies gamma, config `gamma` becomes 1.0 and the preview changes.
- stop.py counts turns spent waiting on agents against the run's cap (journal it01, it02); proposed fix: skip blocking and counting while state.md `in_flight` names an agent.
