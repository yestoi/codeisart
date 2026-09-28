# Iteration journal — wall arcade
(append-only; newest entry last; format defined in SKILL.md, plus test count, skip count and evidence dir per the operator design)

## Iteration 1 — 2026-09-27
- Plan: docs/superpowers/plans/2026-09-27-it01-environment-foundation.md
- Shipped: M1. uv Python 3.12 venv with bounded pins and one OpenCV, `arcade doctor`, `tools/env_check.py`; show foundation (config, 5x7 font, display protocol with fake/SDL, raw Colorlight backend, DDP 0x0B unscaled); `ArcadeConfig` per spec 4.3 and `arcade/calibration.py`. 7 commits e36dba4..040ff3f.
- Review: APPROVED after 1 round (0 blocking; 12 plan-defect notes, carried)
- Deploy: none (phase 1)
- Verify: 6/6 checklist items applicable passed (freshness: evidence sha 040ff3f = HEAD; items 6-7 have no sheets or GIFs before games exist). Evidence: docs/superpowers/workflow/evidence/it01/
- Tests: 66 collected, 66 passed, 0 skipped (first entry; baseline)
- Verdict: the environment works end to end on this Mac, pose included, and camera and mic permissions are already granted, so the pre-flight doctor item is done. No success criterion is scorable yet; none regressed.
- Loop decisions (journaled, not asked): mediapipe pinned `>=1.0,!=1.0.1,<2` (1.0.1 aborts on PoseLandmarker open on macOS arm64); Colorlight brightness packet corrected to Falcon Player's layout (EtherType 0x0A<b>) and pixel order RGB, both to confirm with the `rgb` pattern at GATE B; default calibration zone (0.2, 0.2, 0.8, 0.8); frame packet sent before rows (Falcon Player order, one push of latency).
- Operator tooling finding (owner item, raised at the iteration-2 gate): `stop.py` counts every blocked stop, including turns that end while an agent is in flight, so `iterations-per-run: 2` was used up waiting for the plan writer in iteration 1, not by iterations. The loop enforces the iteration cap itself at step 8. Proposed fix: do not block or count when state.md `in_flight` names an agent.
- Carried forward: C1-C4 (Colorlight and display hardening, must land before GATE B), C5-C9 (config and calibration validation, test and tooling tightening); see roadmap Carried fixes.
- Status: done

Owner intervention, 2026-09-27, during iteration 2's plan phase: the owner asked whether iteration plans get adversarial reviews (they did not; iteration 1's 12 plan defects surfaced only after implementation) and approved adding one (decisions.md Q6, operator design step 2a, config "Plan review: required"). Applies from iteration 2's plan.

## Iteration 2 — 2026-09-27
- Plan: docs/superpowers/plans/2026-09-27-it02-carried-sensed-actors.md
- Shipped: carried fixes C1-C3, C5-C9 (Colorlight safe start and 0.1 s brightness resend, NaN fails dark, uint8/shape checks, clear iface errors, config range checks, per-key calibration validation, anchored ignores, doctor fixes); core Task 3 Sensed with raise line, reach box, place() and mirroring; core Task 4 actors, poses, degrade, REAL_NOISE, festival scenes. 6 commits 26f684f..3017693.
- Plan review (new step 2a, owner decision Q6): BLOCKED round 1 on B1-B4 (brightness resend every 30 pushes on a false premise; NaN brightness drove the wall at full; degrade gave zero latency to streams not starting at t=0; one-shoulder centre jump moved zone_x by a door-third on 31% of noisy captures); BLOCKED round 2 on R2-B1 (single-hip residue of B4); gated as Q7, owner said apply the verified fix; APPROVED round 3 (confirm). All caught before any code was written.
- Review: APPROVED after 1 round (0 blocking; plan defects carried)
- Deploy: none (phase 1)
- Verify: 6/6 applicable items passed (freshness: evidence sha 3017693 = HEAD). Evidence: docs/superpowers/workflow/evidence/it02/
- Tests: 183 collected, 183 passed, 0 skipped (it01: 66/66/0); 5 removed test lines since 7697d01, none an assert
- Verdict: the Sensed record and actors are in and deterministic; the wall path now fails dark on bad brightness input. No success criterion is scorable yet; none regressed.
- Owner changes seen: `iterations-per-run` raised from 2 to 6 in config.md (uncommitted edit found during the plan phase, honoured, committed in 71c5762). Next check-in gate after iteration 6.
- Operator tooling finding, still open: stop.py spent all six of this run's blocks on turns waiting for agents. Proposed fix unchanged (skip blocking and counting while state.md `in_flight` names an agent).
- Carried forward: C12-C16 (see roadmap); C10 extended with the exit-hold grace finding.
- Status: done

## Iteration 3 — 2026-09-27
- Plan: docs/superpowers/plans/2026-09-27-it03-carried-canvas-look.md
- Shipped: carried C12-C16 (keyword-only Sensed/Audio, nose raise line without a torso, blobs clamped, degrade and shake check the calibration (owner Q9), unique scene ids, tempo needs bpm > 0); core Task 5 canvas (float coordinates, clamped colours, scaled text, blit_rgb, sprite_from_rows); core Task 6 plain/LED/distance looks in numpy with light-conserving glow, PreviewDisplay models brightness. 4 commits 6b973ad..e6e31f5. M2 complete.
- Plan review: BLOCKED round 1 (B1 distance look added light, turning amber lemon; B2 blit_rgb wrapped float/int64 colours), APPROVED round 2; round-2 notes (six mutation-killing asserts, docstring, deadline hardening) folded in before commit.
- Review: APPROVED after 1 round (0 blocking; plan defects carried)
- Deploy: none (phase 1)
- Verify: 7/7 items passed. Freshness: canvas sha and PNG `git` chunk read e6e31f5 = HEAD (chunk says `-dirty` only because docs/superpowers/workflow/state.md was modified). Evidence: docs/superpowers/workflow/evidence/it03/
- Tests: 224 collected, 224 passed, 0 skipped (it02: 183/183/0); 2 removed test lines since 83b6945: the MIN_CONF import and test_festival.py:180 (owner decision Q9)
- Verdict (pixels read by the operator: 128x32 and 64x64, led and distance at 5 m): every element is where the plan says, inside the blue border. LED shows round dots with dark gaps. The distance look is soft but every letter, both scale-2 8s and the sha read clearly at both layouts, amber stays amber, and the glow is widest on white and green and barely there on blue. The diagonal clears the text and disc. One thing to note for the owner: the red "88" is drawn as (255, 40, 40) and previews as salmon pink, because with gamma 2.2 modelled a channel at 40 emits visible light on an uncorrected panel. That is the preview telling the truth, not a bug; whether the card applies gamma (config `gamma` 2.2 vs 1.0) is the owner's prototype-week decision, and until then games should pick colours with low channels at 0. Success criterion touched: text is legible at 5 m at both layouts.
- Carried forward: C17-C21 (roadmap); forwarded-to-task items and GATE B additions recorded in the roadmap.
- Status: done
