Decision: iteration 5 done. Second M3 slice landed (juice, runner, run_headless, with C10, C21 and C22 in the runner and C25-C27); continue to iteration 6 (director, mirror, four attract modes) with C28 and C30 first.

# Evidence, iteration 5 (juice, runner, run_headless)

- **HEAD at verify:** a1320bc (head.txt). `tick-budget.txt`, `runner-path.txt` and the sheet are all stamped with a1320bc.
- **Plan:** docs/superpowers/plans/2026-09-28-it05-juice-runner-headless.md (4971882)
- **Plan review** (plan-review.md):
  - Round 1 BLOCKED on B1 (numpy `active`) and B2 (timing tests under load).
  - Round 2 APPROVED; R2-N2 to R2-N5 folded in.
- **Implementation review:** APPROVED in round 1 (reviewer-verdict.md). The orchestrator's report is orchestrator-report.md.

| Check | Result | File |
|---|---|---|
| Collected | 448 (it04: 334) | collect.txt |
| Test command | 448 passed, 0 skipped | pytest.txt |
| Removed test lines since ee6780b | exactly the 4 `perf_counter` lines of the planned clock switch | removed-test-lines.txt |
| Heavy imports from juice, runner and headless | `[]` (orchestrator verify step 4) | orchestrator-report.md |
| `arcade doctor` | camera, mic and pose ok, exit 0 | doctor.txt |
| Tick budget (CPU clock) | strobe 0.365/0.395 ms mean, governor 54%, held 200; static 0.35 ms, held 0 | tick-budget.txt |
| Runner path | raw flash_area 1.0 → pushed 0.006 at both layouts; held 58, scaled 90, crash red peak 96 | runner-path.txt |
| Operator's sheet and timeline | Strobe game, raw vs pushed, ticks 0-39 at 128x32 | it05-128x32-strobe-raw-vs-pushed.png, strobe-timeline.txt, runner_sheet.py |

**The operator's read of the sheet.**
- The raw game alternates full white and black every tick.
- What the runner pushed:
  - The white comes out mid grey, because the brightness limiter caps the day picture level.
  - Ticks 0-6 alternate grey and black three times.
  - From tick 7 the governor holds grey until the next second's window. The timeline shows the same pattern repeating every 30 ticks for the 90 ticks run.
- The wall shows at most 3 flashes a second where the game asked for 15.
- The orange burst at tick 30 and the 2 px player marker on the bottom row come through dimmed, and held frames keep the last shown pixels.
- None of the pushed frames shows the game's full white.

The success criterion "the flash governor and brightness limiter hold on every game (at most 3 full-field flashes per second)" is now met through the real runner path, not just in the module.
