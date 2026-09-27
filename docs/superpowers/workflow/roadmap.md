# Roadmap — wall arcade
**End goal:** A camera-and-microphone arcade for the two-panel LED wall that a stranger at a festival is playing within ten seconds of walking up, unprompted: the attract director shows a mirror of them, a wordless hand-up pictogram invites them, a game starts at once, the three-door menu is opt-in, and the session ends when they leave. Every game is verifiable headlessly on the Mac from scripted and recorded inputs, producing contact sheets, GIFs and feel metrics an agent can judge, with no game code that knows which machine it runs on. 128x32 is the design layout, chosen for two-player side-by-side play, and 64x64 is first-class for single-player games and square visuals. The arcade runs on its own Raspberry Pi 5 driving the spare Colorlight 5A-75E with the raw Colorlight backend, leaving the show Pi 4 untouched. The game list is the one the owner accepted from the review: Copy Me as the hero, Pong, Quick Draw, Dodge, Tug, Flap, Swat, Paint, Strongman and Freeze, with life, beat and the puppet mirror in the attract catalog.

Source documents: the arcade spec as amended by spec revision 3, the core plan with its amendments, and docs/superpowers/reviews/2026-09-26-arcade-adversarial-review.md (sections 6, 7, 10a).

## Milestones
- [x] M0 (owner, before launch): spec revision 3 (44d860a) and plan amendments (0c0bd8e) landed 2026-09-26; pre-flight checklist (operator design section 10) is the owner's remaining part.
- [x] M1 (it01, 040ff3f): Task 0 environment spike (uv, Python 3.12, pins, one OpenCV, `doctor`); foundation Tasks 1 and 2 as renumbered by spec revision 3 (the raw Colorlight backend task per the hardware decision).
- [ ] M2: Sensed with timestamps, velocity, `player`, `present`, zone; actors with `degrade` and festival scenes; canvas with text scale; look with the metre-aware `distance`.
- [ ] M3: game protocol with `SCENARIOS`, `_xy`, `MENU_ORDER`, and `GameInfo.layouts`; runner with session rules, flash governor, brightness limiter; attract director with four modes and the mirror.
- [ ] M4: the new walk-up flow and opt-in three-door menu; paint; contact sheet with provenance and black refusal; REPL with `--log`; `tools/arcade_evidence.py`; feel metrics and budgets (per layout); bots; counterfactual and `_xy` tests.
- [ ] M5: sources (blobs on lores, gated motion grid, MediaPipe unflipped with shared mirroring, audio with voice band and clap), record with `--script` and `--raw`, calibrate.
- [ ] GATE A (human): record the real-input fixture set, first live smoke on both layouts (live-smoke.md), confirm dwell and presence thresholds, approve game order for the second plan.
- [ ] M6: project skills (`arcade-verify`, `wall-look`, `arcade-game-authoring`) and the vendored `cv-mediapipe` and `game-feel` skills.
- [ ] M7: second plan, games in the approved order (default: Copy Me, Pong, Quick Draw, Dodge, Tug, Flap, Swat, Strongman, Freeze), two per iteration; an iteration's evidence is a gate only when a keep-or-cut question arises.
- [ ] GATE B (human): Pi 5 in hand; Pi config, `pi_perf` budget on the Pi 5, IMX500 source with munkres and scipy, plan Task 24 (systemd unit, status file, thermal policy); record the Colorlight 5A-75E firmware version with the `rgb` pattern check (brightness and sync behaviour depend on it; C4 from it01).

## Carried fixes
From iteration 1's review (evidence/it01/reviewer-verdict.md). C1-C4 must land before GATE B.
- C1 (it01) Colorlight brightness safety: `ColorlightDisplay` starts at brightness 1.0 and sends the 0x0A brightness packet only from `set_brightness`. Start at a safe level or refuse to push until brightness is set, and resend the brightness packet periodically (Falcon Player resends; a card brownout must not come back at full brightness).
- C2 (it01) Frame dtype and shape: `ColorlightDisplay.push` checks shape but not dtype (floats go out as zeros, int64 300 wraps to 44); `DDPDisplay.push` checks neither. Raise `ValueError` on a non-uint8 or wrong-shape frame in both.
- C3 (it01) `make_display` colorlight branch raises `AttributeError` for an ArcadeConfig with `iface=""`; raise a clear `ValueError` instead. Add a CAP_NET_RAW hint to the raw-socket PermissionError.
- C4 (it01) done in it01's report: GATE B text now records the card firmware version.
- C5 (it01) `ArcadeConfig` range checks: `apl_cap_day/night` in (0, 1], `fps > 0`, `gamma > 0`, `sdl_scale >= 1`, every `*_seconds >= 0`.
- C6 (it01) Calibration validation: reject negative `min_height`/`baseline_scale`, out-of-range static-mask lights, NaN `audio_floor_db`, a non-bool `calibrated`; a missing key takes that key's default instead of discarding the file; fsync the directory after `os.replace`.
- C7 (it01) `test_sdl_display_pushes_headless` asserts nothing; add asserts (tightening a plan-literal test is the loop's call).
- C8 (it01) `row_packets` uses fixed 256-pixel chunks while `push` splits rows equally; make `row_packets` split equally and add width 384 to the reference test.
- C9 (it01) Small tooling: anchor `.gitignore`'s `/models/`, `/data/`, `/shots/`; `arcade doctor --require ""` should exit 2; `probe_pose` should honour its timeout or document why not.
- C10 (it02 plan review N5) The body cursor is stateless and flips hands when the raised wrist drops out (about 15% of noisy captures). The M3 runner and director (core Tasks 8 and 9) must give cursor consumers a grace period or hysteresis. Fold into the M3 iteration plan.
- C11 (it02 plan review N11, spec gap) `Blob` has no id or velocity, which M3's presence and NEAR logic and Paint need. Resolve in the M3 plan: add them per the spec's intent, or raise a spec question if the intent is unclear.
