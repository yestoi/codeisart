Decision: iteration 4 done. First M3 slice landed (C18-C20, input helpers with C10, core Task 7, flash governor and brightness limiter); continue to iteration 5 (juice, runner, run_headless) with C25-C28.

# Evidence, iteration 4 (carried C18-C20, input helpers, game protocol, frame safety)

- **HEAD at verify:** 9e48c24 (head.txt). This iteration has no PNGs. The flash trace prints the HEAD it ran on, 9e48c24.
- **Plan:** docs/superpowers/plans/2026-09-28-it04-carried-input-protocol-safety.md (e9b23ec)
- **Plan review** (plan-review.md):
  - Round 1 BLOCKED on B1-B6.
  - Round 2 BLOCKED on B7, gated as Q14.
  - Round 3 (confirm-only) APPROVED; notes N25-N28 folded in.
- **Implementation review:** APPROVED in round 1 (reviewer-verdict.md). The orchestrator's report is orchestrator-report.md.

| Check | Result | File |
|---|---|---|
| Collected | 334 (it03: 224) | collect.txt |
| Test command | 334 passed, 0 skipped | pytest.txt |
| Removed test lines since 83b6945 | 2, the same two as it03 (owner Q9); 0 since e6e31f5 | removed-test-lines.txt |
| Heavy imports; `all_games()` | `[]`; `[]` (orchestrator verify steps 4 and 5; reviewer re-ran them) | orchestrator-report.md |
| `arcade doctor` | camera, mic and pose ok, exit 0 | doctor.txt |
| Flash trace (operator, at HEAD) | every attack governed to at most 6 square flashes (BUDGET) on both layouts; grating flash_area 0.188 to 0; static control untouched | flash-trace.txt, flash_trace.py |

**The operator's read of the flash trace.**
- Whole-field white/black at 15 Hz, red/blue at 12 Hz and red/green at 10 Hz each go from 15-30 square transitions a second to 6, which is 3 flashes.
- The turn-taking dithers, which beat the round-2 plan (30 → 30), now give 6.
- The 12-pair reversing grating is held completely by the 12.5% field cap.
- A static frame is never held.

The success criterion "the flash governor holds (at most 3 full-field flashes per second)" is met at module level. The runner wiring lands in it05, and the soak in core Task 20.
