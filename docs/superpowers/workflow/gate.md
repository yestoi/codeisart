# Gate: iteration 2 plan review blocked after two rounds

Question: the it02 plan review is BLOCKED in round 2 on one finding (R2-B1). May the loop apply the reviewer's
verified fix and continue?

- R2-B1: with one shoulder the body centre takes x from `hip_mid`, and `hip_mid` is a single hip when one hip
  drops out. On 9.7% of noisy captures of a still player, `zone_x` moves by up to 0.099 (a door is 0.33 wide).
  The reviewer's fix is already verified: take x from both hips only when both are confident, else the nose,
  else a single hip, else the shoulder. The statistical test runs on the spec 6.4 literals with tolerances at
  or below 0.02. Result: 182 passed, 0.0% outliers, every regression caught.
- B1-B3 from round 1 are closed; 19 of 20 mutations are caught. Nothing else is open.

Evidence: docs/superpowers/workflow/evidence/it02/plan-review.md (Round 1 and Round 2 sections)
Default: apply R2-B1 and notes R2-N1 to N4 exactly as the reviewer specified, have the reviewer confirm the edit
(a third, confirm-only round), then commit and implement.
Deadline: it2 (the loop waits for the owner, who is present)
