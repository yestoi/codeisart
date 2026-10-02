# it20 fix round 1: B1 to B5 (the orchestrator's report)

Base c8324fa (the review's round 1). Test-first throughout: each new test was run on today's code first and failed for
the reason the finding gives, then the fix. B1, B2, B5 (Jump) and B4 (Copy Me's test) were done by the orchestrator in
the main checkout; B3 (the S2 reader) by an opus implementer in a worktree, merged with `--no-ff`. The reviewer's
probes in the scratchpad (`it20-code-review/`) were the failing inputs and were run again after the fixes.

Files touched: `arcade/games/jump.py`, `tests/arcade/test_jump.py`, `tests/arcade/test_copyme.py`,
`arcade/sources/scenario.py`, `tests/arcade/test_scenario.py`, and the notes `B3-fix-notes.md` and this report. No
shared or engine file (`arcade/figure.py`, `KeypointHold`, the runner, juice) and not `copyme.py` or `replay.py`.

## B1: Jump's own drawing lit rows 60 to 63 under real noise
- Change (`jump.py`): `FREE_Y = 60` ("rows 60 to 63 stay free (the runner's marker)", as the other games word it), and
  in `draw` right after the figure, before the striker and the texts: `canvas.fill_rect(0, FREE_Y, self.w, self.h -
  FREE_Y, BLACK)`. The operator's second option (the simpler one); the figure is the only thing Jump draws that can
  reach those rows, and the blackout runs in every phase.
- Test: `test_a_degraded_jumper_keeps_rows_60_to_63_dark[body_id]`, beside `test_own_drawing_keeps_rows_60_to_63_dark`,
  over the 11 body ids the probe showed lit in their FIRST window (3, 8, 10, 12, 15, 24, 30, 34, 36, 37, 40): the
  probe's jumper (one jump of 0.15 at 2.5 + 0.033 x id) under `degrade(**REAL_NOISE)` for 5 s (the noise is keyed by
  tick, body id and joint, so the cut scene's frames are the probe's). Failed first: all 11, e.g. "id 10: rows 60 to
  63 lit on 3 ticks, from [(3.2, 'play'), ...]", "id 24: ... (3.6, 'play')". Now passes; 0.06 s each, about 0.7 s in
  all.
- Probe again (`probe_rows.py`, ids 1 to 40, three jumps over 30 s): "runs with rows 60-63 lit: 0 of 40" (was 22).

## B2: a newcomer in the window was measured against the earlier player's baseline
- Change (`jump.py`): the baseline carries its body id, `_base = (held.id, nose y, hip y, torso)`. In `_measure`, when
  `_base` is None or the held body's id differs from it, the baseline is dropped (`_base = None`), `rise` and `cm` read
  0 and the capture does not count, so for the rest of that window nothing is measured, the bell cannot ring, and the
  peak reached before stands and banks at the window's end as before. The window keeps its length (no return to
  ready); the next ready takes the newcomer's baseline as today. The module docstring says so.
- Tests (through the real runner, `run(Jump, ...)`, seed 12345, the probe's swap: A stands, B (height 0.72, y 0.47,
  id 2) takes A's place at 2.2 s):
  - `test_a_newcomer_in_the_window_is_not_measured_against_the_last_baseline[clean|real_noise]`: heights [0, 0, 0],
    best 0, no bell, no recorded best. Failed first: heights [37, 0, 0] clean and [40, 0, 0] under REAL_NOISE.
  - `test_a_jump_before_the_swap_still_counts[clean|real_noise]`: A jumps 0.08 at 2.0 s (under the bell and under B's
    false rise), B takes the place at 3.5 s; the heights and the recorded best equal those of A staying: [22, 0, 0]
    clean, [23, 0, 0] under noise. Failed first: [37, 0, 0] and [40, 0, 0] (B's false rise beat A's real one).
  - 0.7 to 1.5 s each, about 4.3 s for the four.
- Probe again (`probe_swap.py`): swap clean [0, 0, 0], recorded best None; swap under noise [0, 0, 0], None; B alone
  [0, 0, 0], None.

## B5: `fx.flash`'s return was dropped at jump.py:227
- Change (`jump.py`): `if not self.fx.flash(FLASH, 0.15): self.fx.burst(BAR_X + BAR_W // 2, _row(self.bell_cm) -
  BELL_H // 2, BELL_COLOR)`, Copy Me's pattern: a refused flash becomes a burst on the bell. The "DING!" pop is as
  before.
- Test: `test_the_bell_rings_once_and_checks_the_flash` gains the refused case after its granted case (whose asserts
  are unchanged): a `Refused(Jump)` whose `fx.flash` returns False; it asserts one "DING!", `rang`, exactly one burst,
  and that burst inside the bell's box. Failed first: `assert 0 == 1` (no burst). The test now takes 0.49 s.
- Probe again (`probe_flash_return.py`): `jump.py:234 self.fx.flash(FLASH, 0.15): return used` (every game's flash
  return is used).

## B3: the scenario reader (by the opus implementer; its notes are `B3-fix-notes.md`)
- Change (`scenario.py` only; `replay.py` not touched): the reader catches any Exception from one line
  (RecursionError included), skips it with the warning and `skipped += 1`, and reads on; at open, a header that fails
  to parse for any reason is the documented ValueError ("no header: RecursionError: ..."). Every float field is read
  through `_finite` (NaN, Infinity, -Infinity, 1e999 refused): the box, each keypoint's x, y and conf, vx, vy, scale,
  seen_ago, torso_per_width, a blob's x, y, size, vx, vy, and every float audio field (bpm may still be null); t and
  camera_t were already checked. `BAD_LINE` is gone (no other user). Side effect: `decode_raw` shares the box and
  keypoint readers, so a raw record's detections refuse a non-finite number too.
- Tests (33 new, `test_scenario.py`), each failing first on c8324fa's `scenario.py` (31 failed, 45 passed in the
  scenario and sensed files before the fix):
  - `test_a_deeply_nested_line_is_skipped`: RecursionError out of the reader.
  - `test_replay_reads_past_a_deeply_nested_line` (`open_replay`, `latest()` once a tick): RecursionError on the
    second `latest()`.
  - `test_a_header_that_cannot_be_parsed_is_refused` (ScenarioReader and open_replay): RecursionError, not ValueError.
  - `test_a_non_finite_box_is_skipped`: the record came through with `box=(0, 0, inf, inf)`, skipped 0.
  - `test_a_non_finite_box_never_reaches_a_game` (3 s of the Infinity box then good lines, into Jump, `strict=False`):
    `crashes == {'jump': 1}` ("cannot convert float NaN to integer").
  - `test_a_non_finite_blob_value_is_skipped` (size Infinity): two records read, not one.
  - `test_a_non_finite_audio_value_is_skipped` (level NaN): the record came through with level nan.
  - `test_every_float_field_refuses_a_non_finite_number[<field>]`, 26 field paths x the four tokens: 24 failed
    (five records read, not one); the t and camera_t cases passed already and are kept to pin that check.
  - Its own run: 76 passed (scenario and sensed), 0.24 to 0.31 s.
- Probes again on main after the merge: `probe_scenario.py` (1) "no raise; records [0.0, 0.0333, 0.0667], skipped
  1", (1b) the replay reads every tick past the nested line; (2) the Infinity-box record is skipped (the probe's own
  next line then fails with IndexError, as it assumed the record got through). `probe_scenario_runner.py`: "read
  360 lines, skipped 90; runner: crashes {}, hidden [], game now jump".

## B4: Copy Me's outline test did not test the plan's clause
- Change (`test_copyme.py` only; `copyme.py` untouched): the second half of
  `test_the_outline_differs_from_every_figure_colour` now reads the outline's own pixels. During the draw of the
  first `duo` frame of play, `Canvas.line` and `Canvas.circle` are spied (pytest's `monkeypatch`, scoped to that one
  draw): every stroke whose caller is copyme's `draw_view` itself (the outline; the figure's strokes come from
  `draw_figure` and the matched segments' from `_thick_line`, so neither is counted) is drawn again alone on a blank canvas, keyed by the seat colour `draw_view` was
  called with. It asserts strokes from both seats, that each seat's outline lights pixels, and that no outline pixel
  of either seat is seat b's colour. The first half's asserts, and the second half's two old asserts, stay as they
  were (no assert removed or weakened; the test gained `monkeypatch` and `import sys`).
- Mutation check (scratchpad, not committed: `it20-fix/b4_mutation_check.py`, the reviewer's mutant installed, then
  pytest on this one test in the same process): today's code, 1 passed; the mutant (seat b's outline drawn in seat
  b's colour), 1 failed: "outline pixels in seat b's colour (0, 160, 255), by seat: {(255, 120, 0): 0, (0, 160, 255):
  69}". The review showed the old test passing on the same mutant.

## Jump's feel report
Unchanged, every metric identical at full precision (`arcade.feel.report(Jump, "128x64")`, 20 seeds, the project
font; run on a detached scratch worktree at c8324fa and on the fixed main, then compared; the worktree was removed):
win_good 1.0, win_lazy 0.45, win_none 0.0, fidelity 0.9991432, range 0.6850394, response_ticks 1.0, response_px 197.5,
flash_area_raw 0.0024414, square_flashes 4.0, score_visible 0.9784483, score_legible 1.0, round_seconds 30.0,
phases_reached 1.0, lit_fraction 0.1106457, dim_fraction 0.0, liveliness 0.0180975, presence_answer_seconds 0.0;
failures none. Jump's constants and feel bands did not move (FREE_Y is new, a drawing bound).

## The subset check
`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_all_games.py
tests/arcade/test_jump.py tests/arcade/test_copyme.py tests/arcade/test_scenario.py tests/arcade/test_oracle.py
tests/arcade/test_game.py` on main at 32980ed: 284 passed, 0 skipped, 180.58 s. Pool: 480 plays, 4 workers, 120.3 s,
the join waited 9.3 s. `test_jump.py` alone: 54 passed (39 + 15 new), 21.5 s. The full suite was not run (the
operator runs it in verify).

## Deviations
- Two of my Bash commands began with `cd /Users/trey/dev/codeisart` (the graft lookup of `reserved` and the first
  feel run), against the never-`cd` rule. Both named the directory the shell was already in, so nothing changed;
  every later command used absolute paths.
- The before/after feel comparison used a detached `git worktree` of c8324fa in the scratchpad (removed after), so
  the "unchanged" claim is exact rather than read off G5's rounded numbers.

## Owner questions (each defaulted)
- Q-fix-a (B1): rows 60 to 63 are blacked out, not the figure clipped to its rect, so a held keypoint can still draw
  in rows 56 to 59 below the figure's rect (beside the bar's bottom, row 57). Default: keep (the operator's simpler
  option); the shared cause in `KeypointHold` is iteration 21's.
- Q-fix-b (B2): the check is by body id, so the same person given a new id by the tracker inside a window (lost
  longer than the tracker holds, then found) also stops counting for the rest of that window. Default: keep (the
  tracker never reuses ids, and the window is only 5 s; the next attempt measures again).
