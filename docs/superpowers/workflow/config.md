# Workflow config — wall arcade
- Phase: 1 (Mac). Phase 2 (Pi 5) is a config change made at GATE B.
- Deploy: none (phase 1, Mac)
- App URL: none (local Python process; verification is headless)
- Test: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs` (run from repo root)
- Evidence: `.venv/bin/python tools/arcade_evidence.py --iteration <N> --games changed`, written to docs/superpowers/workflow/evidence/itNN/. That tool is built in M4. Until then, evidence is `tools/arcade_shot.py` output plus the test command's output saved to the same evidence dir, with a README.md whose first line is the decision.
- Screenshots dir: docs/superpowers/workflow/evidence/
- Freshness check: every PNG in evidence/itNN/ carries the git sha in its header and it must equal HEAD. Before M4, the evidence README records HEAD by hand (`git rev-parse --short HEAD`). A mismatch is a tooling defect, fixed before anything is judged.
- Gates: gate-deploys: false, gate-iteration-plans: false
- Plan review: required. Every iteration plan gets an adversarial opus review before it is committed (operator design step 2a, decision Q6); verdict in evidence/itNN/plan-review.md.
- iterations-per-run: 6
  (first run; raise after it proves out. Keep it below 8, Claude Code's consecutive Stop-hook block cap, so the loop's own gate fires first. The Stop hook reads this line.)

## Verify checklist
Replaces the walkthrough checklist; run inline in the main session (design section 4, step 6). No walker agent in phase 1.
1. Freshness: the evidence sha equals HEAD (see Freshness check above).
2. The test command is green.
3. Skip count has not risen since the last journal entry (`-rs` output, count of SKIPPED), unless the rise is journaled with a reason.
4. Collected count has not dropped (`pytest --collect-only -q | tail -1`), unless journaled with a reason.
5. `.venv/bin/python -m arcade doctor` passes for the sources this slice needs (once doctor exists, from M1).
6. Evidence written to evidence/itNN/ with the matching sha: README with the decision on line 1, sheets, GIFs, feel table once feel metrics exist (M4).
7. The main session has read the changed games' sheets and GIFs itself with the Read tool (read `feel.json` first; a failing game gets its sheet read closely) and written the verdict into the journal before any other tool call.

## Success criteria
- The roadmap end goal: a stranger is playing within ten seconds of walking up, unprompted.
- Every game in the accepted list runs headlessly from scripted inputs and produces sheets, GIFs and feel metrics an agent can judge.
- Every game meets its feel budgets in full on each layout it declares; on undeclared layouts it runs and stays legible.
- 128x32 is the design layout; 64x64 is first-class for single-player games and square visuals.
- The flash governor and brightness limiter hold on every game and attract mode (at most 3 full-field flashes per second).
- The owner's live smoke (live-smoke.md) scores each shipped game "responded: y" and "understood: y" on both layouts it declares.
