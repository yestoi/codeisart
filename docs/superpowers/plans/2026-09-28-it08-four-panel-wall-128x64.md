# Iteration 8: the four-panel wall, 128x64 is the only layout (M4b), and C38 to C41
Base 0c1ff29. Roadmap M4b (must). Carried C38, C39, C40, C41. Notes applied: the it07 and it06 notes on the tools,
the suite's time, Pong's score seat and Q23. Owner decisions Q32 and Q33: four 64x32 panels 2 x 2; games are
designed, tuned and judged at 128x64 alone; the engine stays free of any size.
Thin plan (Loop rule 1). "Spec" = `docs/superpowers/specs/2026-09-26-wall-arcade-design.md`; where it names 128x32 or
64x64 as a game's layout, Q33 overrides it. The spec file is not edited.
SAFETY SLICE: no. `arcade/flash.py`, `arcade/brightness.py`, `show/display/colorlight.py` and the runner's order
(limiter, governor, push) are untouched. `tools/wall_pattern.py` changes its default size and its `index` seams
only; its brightness cap and the driver are unchanged. The panels' 2 x 2 wiring is the owner's hardware item.

## Global Constraints
- Test command, from the checkout's (or worktree's) root: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
  /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs`. At 0c1ff29: 675 collected; it07's run: 675
  passed, 0 skipped, 133.6 s.
- Touch only your task's files. Never `cd`: absolute paths and `git -C` (in a worktree: plain git from its root,
  one command per call). No command over 10 minutes. Test-first (superpowers:test-driven-development); write the
  code yourself. No removed or weakened asserts. The only changed asserts allowed are those this plan names under
  "Changed asserts"; any other: stop and report it.
- Every call that builds `Sensed` or `Audio` uses keywords (C21).
- Every frame reaches the display only through the runner: limiter, then governor, then push. No game, lobby,
  bot or metric pushes; none saves images: `.save` appears only under `tools/`.
- Colours saturated, low channels at 0: gamma is unknown. No game or lobby code knows which machine it runs on.
  Timing tests time CPU (`time.thread_time`). Seeds from `zlib.crc32`, printed in assertion messages.
- `debug_state` keys are never `arcade.game.reserved()`, the lobby's included.
- Owner decisions: Q11 governor last before push; Q17 three crashes hide a game; Q18 shake is jumps; Q19 close
  bursts dropped; Q20 `fx.flash` is a hold; Q22 attract shows the featured title, static and dim; Q23 a duel's
  card shows player 1's points, bests for solo only; Q24, Q25 as defaulted; Q26 to Q31 budgets as defaulted.
- Size: no code under `arcade/` names 128 or 64 as the wall's size except `arcade/config.py`'s defaults, a game's
  `GameInfo.layouts` and its bots. Layout-driven rules read `canvas.height`/`size` (for example "at least 48 rows").
- A game's own files: `arcade/games/<name>.py`, `<name>_bots.py`, `<name>_feel.toml`, `tests/arcade/test_<name>.py`.
- Suite time: this iteration adds at most 40 s (the suite at most 175 s). Sizes move, they are not added: Pong's
  tests, the oracle's one module-scoped 20-seed report and feel's stubs go from 128x32 to 128x64. The only added
  runs: the lobby's third size and the engine tick budget at 128x64. Per task: S1 at most +5 s, S2 +10 s,
  P1 +15 s, P2 +10 s, P3 +2 s. Say in your report what yours added (a probe: one good-bot play of Pong costs
  0.48 ms a tick at 128x32 and 0.65 ms at 128x64).
- A finding or idea outside your task goes in your final message, not in code.

## Lanes
- SERIAL, main checkout, opus, one at a time, each committed before the next: S1, then S2. No game task is in
  flight while S1 changes `arcade/game.py`.
- PARALLEL, `isolation: "worktree"` from the local HEAD after S2, launched in ONE message: P1 (sonnet), P2
  (opus), P3 (sonnet), P4 (sonnet). A task imports nothing another parallel task builds.
- INTEGRATION, orchestrator, main checkout: merge P1, P2, P3, P4 in that order, the suite after each; then I1.
  I2 is the operator's, in verify, after the review.
- Shared files: S1 is given `arcade/config.py`, `arcade.toml`, `arcade/main.py`, `tests/arcade/helpers.py`;
  S2 is given `arcade/bots.py`, `arcade/feel_budgets.toml`. No other shared file is edited.
- Changed asserts (each named, none weakened): `test_game.py::test_game_info_defaults_follow_the_spec` LAYOUTS
  `{"128x64"}` (S1); `test_config.py` lines 20 and 99, the default size `(128, 64)` and layout `"128x64"` (S1);
  `test_pong.py::test_registered_and_declared` layouts `{"128x64"}` and `test_feel_file_overrides_have_reasons`
  reading `"128x64"` (P1); `test_wall_pattern.py` line 206, the PNG `(128 * 8, 64 * 8)` (P3); key sets and the
  budget dict that gain `response_px` (S2, extended). Constants that move (`WALL`, `LAYOUT`, `seed("128x64", i)`)
  are not asserts.

## S1 (opus, serial): LAYOUTS, the wall's default size, the engine's tick budget at 8192 pixels
Files: `arcade/game.py`, `arcade/config.py`, `arcade.toml`, `arcade/juice.py`, `arcade/main.py`,
`tests/arcade/helpers.py`, `tests/arcade/test_game.py`, `tests/arcade/test_config.py`,
`tests/arcade/test_main.py`, `tests/arcade/test_headless.py`, `tests/arcade/test_juice.py`.
```
LAYOUTS = frozenset({"128x64"})           # arcade/game.py: the design layout, Q33; GameInfo.layouts' default
class ArcadeConfig: width: int = 128; height: int = 64      # arcade/config.py; arcade.toml the same, commented
class Juice: def __init__(self, rng, size: tuple[int, int] = (128, 64))   # the fallback only; the runner passes size
SPY_LAYOUTS = frozenset({"128x64", "128x32", "64x64", "96x48"})   # tests/arcade/helpers.py: spy_info's default
```
- The change after `game-protocol-v1` is a data value: no member, parameter or field of the protocol changes. The
  commit message carries the reason: "Q33: LAYOUTS is a data value; the protocol's members are unchanged". The
  canary `test_protocol_members_are_the_frozen_set` is not edited and passes (it checks LAYOUTS by name).
- `game.py`'s docstring: layouts name the design layout 128x64; a game still runs at any size it does not declare.
- `arcade.toml`: `width = 128`, `height = 64`, comment "four 64x32 panels, 2 x 2 (Q32)".
- `main.py`: `run` logs `wall WxH, backend B` at INFO once at start. Nothing else changes.
- `helpers.spy_info` declares `SPY_LAYOUTS` so the engine's and the lobby's spies keep being featured at the
  sizes the engine tests use (the lobby features only a game whose layouts hold `cfg.layout`).
- `tests/arcade/conftest.py`'s `size` fixture is not changed: the engine's tests stay at 128x32 and 64x64.
Tests:
- `test_game_info_defaults_follow_the_spec`: LAYOUTS is `{"128x64"}` (the named change).
- `test_config.py`: `test_defaults_when_file_missing` and `test_layout_name` at 128x64 (named);
  `test_default_file_in_repo_lists_every_field_with_its_default` passes unchanged against the new file.
- `test_main.py::test_run_opens_a_128x64_wall_by_default`: `main(["run", "--seconds", "0.2", "--script",
  "walkup"])` with no `--config` from the repo root builds its display with `cfg.size == (128, 64)` (a spy
  `build_display`) and logs `wall 128x64`.
- `test_headless.py::test_tick_budget_with_the_governors_share` gains a `(128, 64)` case (8192 pixels) beside
  its `size` cases: the same budget, no looser.
- `test_juice.py`: a test that relies on Juice's default size moves with it; report which, if any.

## S2 (opus, serial): C38, the response metric and the arcade's launch in `feel`; bots' default layout
Files: `arcade/feel.py`, `arcade/bots.py`, `arcade/feel_budgets.toml`, `tests/arcade/test_feel.py`,
`tests/arcade/test_bots.py`.
```
RESPONSE_PX = 12        # now the magnitude floor, judged by the budget on response_px (spec 11)
LATENCY_TICKS = 2       # unchanged: response_px is read this many ticks after the probe
def measure(game_cls, layout, seeds=FEEL_SEEDS, font=None, *, own=None) -> dict   # unchanged signature
    # ValueError when layout is not in game_cls.info.layouts, naming both
def play(game_cls, bot, seed, layout: str | None = None, ...) -> Play              # arcade/bots.py
def win_rate(game_cls, bot_factory, seeds, layout: str | None = None) -> float
    # None: the game's one declared layout when it declares exactly one, else ArcadeConfig().layout
```
- Launch as the arcade does (C38, part 2): canonical runs through `run_headless(..., lobby=Lobby([game_cls],
  cfg))` (`arcade.attract.lobby`), so the game starts on the raised hand with the body in view; metrics count
  from the launch tick (`current`, as now). The counterfactual reruns use a fresh `Lobby` on the same records.
  `presence_answer_seconds` keeps its direct launch (idle_body raises no hand), measured only, as Q31 says.
- Latency and magnitude apart (C38, part 1; spec 9.3 names both):
  - `response_ticks`: the median over probes of the first tick after the probe on which the held run's pushed
    frame differs from the original's in any pixel; `5 * LATENCY_TICKS` when never.
  - `response_px` (new): the median over probes of the pixels differing `LATENCY_TICKS` ticks after the probe.
  - A probe is a canonical tick where the input moves on the next record, the game is current, and, with a
    `[fidelity]` table, the control's `_xy` axis changes on the next traced tick (a clamped control is no probe).
- `feel_budgets.toml`: `response_px` `min = 12` for `control`, `score` and `toy` (the header comment says so).
  If Pong at 128x32 (the oracle at S2's commit) then misses it, stop and report: I1 takes the line instead.
- `SCORE_SCALES` stays `(1, 2)` here; I1 sets `(2,)` after P1's 2x scores merge (C39).
- Tests (the stubs' `canonical` gains the walk-up and a raised hand the way the guide says, so the lobby
  launches them; `WALL = "128x64"`, which the stubs declare by default after S1):
  - `test_response_ticks_does_not_depend_on_the_probe_count`: a follower stub and a stub whose 2 px paddle moves
    1 px a tick; `PROBES` 4, 8 and 16 (monkeypatched) give the same `response_ticks`, 1.0.
  - `test_a_clamped_control_is_not_probed`: a stub pinned at the wall's edge for half of canonical gets no probe
    there; `response_ticks` stays 1.0.
  - `test_response_px_counts_the_change_after_two_ticks`: the slow stub gives under 12, the follower 12 or more.
  - `test_measure_launches_through_the_lobby`: a spy game records `sensed.player` on its first update: a body,
    at the tick of canonical's raise or the next.
  - `test_measure_refuses_an_undeclared_layout`: ValueError naming the game and the layout.
  - `test_a_1x_score_is_not_visible`: a stub drawing its score at 1x gets `score_visible == 0.0` at the default
    scales; `xfail(strict=True, reason="until I1 sets SCORE_SCALES = (2,)")`.
  - `test_find_text_locates_the_score_at_either_scale` passes `scales=(1, 2)` explicitly (same asserts).
  - Existing: `test_follower_passes_fidelity_and_response`, `test_screensaver_fails_both` keep their asserts;
    `test_measure_repeats_under_seeds` and `test_report_is_json_ok` key sets gain `response_px` (extended).
  - `test_bots.py`: `test_budget_file_parses_and_has_every_kind` gains `response_px` (extended);
    `test_play_defaults_to_the_declared_layout` (a one-layout spy at 96x48 plays at 96x48; a two-layout spy
    plays at `ArcadeConfig().layout`).

## P1 (sonnet, worktree): Pong at 128x64, 2x scores (C39), an idle body scores nothing (C41)
Files: `arcade/games/pong.py`, `arcade/games/pong_bots.py`, `arcade/games/pong_feel.toml`,
`tests/arcade/test_pong.py`, `tests/arcade/test_oracle.py`, `tests/arcade/test_first_playable.py`.
```
Pong.info.layouts = frozenset({"128x64"})       # 128x32 dropped (Decisions); Pong still runs at any size
SCORE_SCALE = 2                                 # spec 7.4: both scores 10x14, top row y 1, centred on w/4 and 3w/4
CPU_SPEED = 0.75                                # wall heights per second (48 px/s at 64 rows, 24 at 32)
class Good: WALL_W, WALL_H = 128, 64            # pong_bots.py: the declared layout
```
- Geometry follows the height as now: paddle `h // 4` (16 px), `PADDLE_W` 2, `BALL` 2, the net every 4 rows.
  Ball speeds stay px/s (the width is still 128). `CPU_SPEED` becomes a share of the height per second so the
  CPU is tuned for a field twice as tall. Tuning (CPU, ball start, gain, max) is this task's, within the bands:
  at 128x64 over `bots.seeds(Pong, "128x64", 20)` every budget passes and `response_px` is 12 or more. Report
  how many good rounds end by points before the cap (the it07 note; not required).
- C41: a point won by a human seat counts only if that human moved the paddle (1 px or more on some tick) in
  the rally that ended in it; otherwise nobody scores, the `point` phase shows no "+1", and the next serve
  follows as usual. `_finish` records a best only when the solo player moved during the game. `score` keeps
  following player 1 by id (Q23, the it06 note).
- `pong_feel.toml`: `[budgets."128x64"]`, each override with a reason; the 128x32 table goes with the layout.
- `test_oracle.py`: `LAYOUT = "128x64"`; its one module-scoped report moves there (no second report). The
  evidence test's names become `pong-128x64-*`.
- `test_first_playable.py`: `WALL = (128, 64)`; its asserts scale with `WALL` and stay.
Tests (in `test_pong.py`, `WALL = (128, 64)`, seeds `seed("128x64", i)`):
- `test_registered_and_declared`: layouts `{"128x64"}` (named).
- `test_scores_drawn_at_2x`: `feel.find_text(frame, font, str(points), scales=(2,))` finds both scores on a drawn
  frame; at `scales=(1,)` it finds neither.
- `test_a_still_paddle_banks_no_point`: a human seat whose paddle never moved; the ball passes the CPU; no
  point, the next serve comes. `test_a_moving_player_still_scores`: the same with the paddle moved: one point.
- `test_idle_body_scores_nothing` over `bots.seeds(Pong, "128x64", 10)`: `score == 0` and the human side 0 on
  each seed, `scores.best("pong", "128x64") is None`; its existing asserts stay (C41; the reviewer's case).
- `test_cpu_speed_follows_the_height`: the CPU paddle's px per tick at 128x64 is twice that at 128x32.
- `test_runs_and_stays_legible_on_64x64` stays as is: an undeclared size.
- `test_feel_file_overrides_have_reasons` reads `"128x64"` (named).
- `test_first_playable.py::test_canonical_round_from_attract_to_the_card` (new): `Pong.SCENARIOS["canonical"]`
  through `run_headless(..., lobby=Lobby([Pong], cfg))` at 128x64: the lobby's modes in order attract, mirror,
  invite, then `game == "pong"`, then card; the card's score is Pong's last `score`; one session in the log.
- Existing bot tests (`test_good_beats_lazy_beats_nobody`, `test_good_round_length_in_band`) run at 128x64 by
  `play`'s new default; their asserts stay.

## P2 (opus, worktree): the small lobby laid out for 64 rows
Files: `arcade/attract/lobby.py`, `arcade/figure.py` (expected unchanged), `tests/arcade/test_lobby.py`,
`tests/arcade/test_figure.py`.
```
BIG_ROWS = 48           # a wall at least this tall draws the lobby's big text at 2x
BIG_SCALE = 2
def _lines(text: str, width: int, canvas: Canvas, scale: int = 1) -> list[str]
def _centred(canvas: Canvas, lines: list[tuple[str, int]], color) -> None   # (text, scale) per line, one block
```
- Attract (Q22 kept: static, dim, centred): the featured title at `BIG_SCALE` when `canvas.height >= BIG_ROWS` and
  it fits the width on one line, else 1x.
- The end card (Q23 kept, content unchanged): the head line (title and score) and "BEST!" at `BIG_SCALE` on a tall
  wall where they fit, the prompt ("HAND UP = AGAIN" or "NEXT: RAISE A HAND") at 1x; the block centred.
- The mirror figure: `figure_rect`'s square of the wall's height (64 px), strokes 2 px (spec 7.3); the hand-up
  pictogram 16 px beside it, level with the shoulders, as now. Mode changes stay single steps.
- `test_lobby.py` and `test_figure.py` override the `size` fixture at module level: `(128, 64)`, `(128, 32)`,
  `(64, 64)`, so every sized test also runs on the wall's size. No assert changes.
Tests, added:
- `test_attract_title_is_2x_on_a_tall_wall_and_1x_on_128x32`: the lit rows of the title span 14 at 128x64, 7 at
  128x32; static over 30 ticks.
- `test_card_fits_64_rows_with_best`: head line and BEST! at 2x, the prompt at 1x, all inside the wall, centred
  within 1 px; `debug_state` card keys unchanged.
- `test_card_falls_back_to_1x_when_2x_does_not_fit`: a long title at 128x64 draws at 1x.
- `test_pictogram_beside_a_full_height_figure_on_128x64`: pictogram inside the wall, not over the figure's box.
- The strobe check at 128x64 (existing tests on the override): `test_mirror_under_real_noise_keeps_the_area_rule`
  (raw `concurrent_area < SMALL_AREA`) and `test_lobby_frames_keep_the_flash_rule`; plus
  `test_lobby_holds_no_tick_at_128x64`: the walk-up to card run's `flash_held_ticks` stays 0.

## P3 (sonnet, worktree): the tools at 128x64, and C40
Files: `tools/arcade_evidence.py`, `tools/arcade_shot.py`, `tools/wall_pattern.py`, `tests/test_arcade_evidence.py`,
`tests/test_arcade_shot.py`, `tests/test_wall_pattern.py`.
```
arcade_shot: --size default "128x64"
wall_pattern: --width default 128, --height default 64; PANEL_W, PANEL_H = 64, 32
def index(width, height, t) -> np.ndarray   # a seam (cyan, then yellow) at every multiple of PANEL_W inside the
                                            # width and of PANEL_H inside the height; the four corners as now
```
- C40: `games.md` prints `-` in the ok column for a metric with no budget (`presence_answer_seconds`), `yes` or `no`
  otherwise; a missing value against a budget stays `no`.
- `wall_pattern`'s docstring names 128x64 as the default and `--width 128 --height 32` for one row of two panels.
Tests, added: `test_ok_column_is_a_dash_without_a_budget` (evidence); `test_default_size_is_128x64` (shot, from
the parser); `test_default_size_is_the_four_panel_wall` (wall_pattern, from the parser);
`test_index_marks_every_panel_seam` (128x64: both seams; 128x32 and 64x64: one each, as the old test asserts).
`test_wall_pattern.py`'s `LAYOUTS` gains `(128, 64)`; line 206's PNG size is `(128 * 8, 64 * 8)` (named).

## P4 (sonnet, worktree): the game guide and the live smoke say 128x64
Files: `.claude/skills/arcade-game-authoring/SKILL.md`, `docs/superpowers/workflow/live-smoke.md`.
- The guide: `LAYOUTS` is `{"128x64"}`, the design layout (Q33); a game declares it and still runs at any size
  (the soak adds 96x48); `[budgets."128x64"]` in examples; `feel.report(GameCls, "128x64", ...)`; scores at 2x
  (spec 7.4; the oracle finds only 2x after I1); an idle body scores nothing and stores no best (C41: points need
  movement); `response_ticks` is latency and `response_px` magnitude, 12 px within 2 ticks (spec 11); feel launches
  through the small lobby, so canonical needs its walk-up and raised hand. Under 400 lines.
- `live-smoke.md`: one row per game at 128x64 (the 128x32 and 64x64 rows go); the panel line names the 2 x 2
  wall. No tests: check every named file, constant and command against S2's commit and this plan.

## I1 (orchestrator): C39's last step, the oracle at 128x64
Files: `arcade/feel.py` (only `SCORE_SCALES = (2,)`), `tests/arcade/test_feel.py` (only S2's `xfail` mark removed).
- After the four merges, one commit: the two edits above, the suite green.
- Report: Pong's feel table at 128x64 (every metric, value and budget, `response_px` included), the tick-budget
  test's mean at 128x64, the suite's count and time against the 175 s limit. A failing budget is fixed in P1's
  files by P1's implementer or sent to the owner, never loosened.

## I2 (the operator, in verify, after the review): evidence at 128x64, from the repo root
```
.venv/bin/python -m tools.arcade_evidence --iteration 8 --games pong --out docs/superpowers/workflow/evidence/it08
.venv/bin/python -m tools.arcade_shot pong --lobby small --scenario duel --raw-vs-pushed --flash-report \
    --out <scratch>/it08-128x64-strobe > <scratch>/strobe-check.txt
.venv/bin/python -m tools.arcade_shot pong --lobby small --scenario canonical --look both --out <scratch>/it08-walkup
.venv/bin/python -m tools.wall_pattern index --png <scratch>/index-128x64.png
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m arcade run --seconds 5 --script walkup \
    > <scratch>/run-default.txt 2>&1
```
The `arcade_shot` and `wall_pattern` files are written to the scratchpad with the tree clean, then copied into
evidence/it08/ (the it07 note: `arcade_shot` stamps `+dirty` for untracked files). `run-default.txt` shows
`wall 128x64` and exit 0. Plus collect.txt, pytest.txt, head.txt as in it07. Done when (roadmap M4b): the oracle
passes at 128x64, the canonical round runs attract to card at 128x64, `arcade run` opens 128x64 by default, and
the sheets, the GIF and the strobe check at 128x64 are in evidence.

## STRETCH (only if fewer than 70 minutes have passed at I1's end; at most 15 minutes)
- X1 (opus, main checkout, after I1): the it07 note on `KeypointHold`: hold a dropped keypoint relative to the
  body's box so a held wrist follows a walker. Files `arcade/figure.py`, `tests/arcade/test_figure.py`.
  `test_a_held_wrist_follows_a_walking_body`: the reviewer's walk (0.3 of the zone in 1 s) keeps the held wrist
  within 3 px of the true one on the 64 px figure.

## Left out (named)
- it07's X2 (`tools/arcade_feel.py`) and X3 (`test_privacy.py`); the idle hint and the fail-versus-win transient.
- The panels' 2 x 2 wiring and `evidence/hardware.md`: the owner's item. `index` at 128x64 is ready for it.
- A second report or second layout anywhere in the oracle.

## Decisions
- `LAYOUTS = {"128x64"}` is a data change after the freeze (Q33), made first in the serial lane with no game in
  flight; the canary is not edited and still passes; the reason goes in S1's commit and the operator's journal.
- Pong's 128x32 declaration is dropped: 2x scores cover 14 of 32 rows and the CPU is retuned, so keeping 128x32
  would need its own 20-seed oracle report (about 55 s) and tuning, which Q33 calls extra work. Pong still runs
  at 128x32, 64x64 and 96x48 undeclared.
- The engine's `size` fixture stays at 128x32 and 64x64; the wall's size reaches the engine through the tick
  budget case, the soak (Pong's declaration) and the lobby's module-level override.
- Spies declare four layouts (`SPY_LAYOUTS`): the lobby features only declared layouts, and engine tests keep
  their sizes.
- `bots.play`'s layout defaults to the game's one declared layout: size-free, and Pong's tests follow Pong's
  declaration without a serial change breaking them.
- C38: latency is the first differing pixel; magnitude is its own metric with spec 11's 12 px; a clamped
  control is no probe. Feel launches through the small lobby, the arcade's own path; S2 is serial so Pong is
  tuned against the final metric.
- C39: Pong draws 2x; `SCORE_SCALES = (2,)` only after Pong's 2x merges (I1), so no merge breaks the oracle.
- C41: points need movement in the rally; a best needs movement in the game.
- The lobby's big text is layout-driven (`BIG_ROWS`), not keyed to 128x64; the card's content stays Q23's.
- Merge order P1, P2, P3, P4: Pong first so the first-playable round at 128x64 judges P2's lobby at its merge.

## Owner questions (defaulted)
- Pong at 128x64: paddle a quarter of the height (16 px), ball 2 px, ball speeds in px/s as at 128x32, the CPU
  at 0.75 wall heights a second before tuning; scores 2x at the top over each half.
- An idle body's points: a human's point counts only after they moved the paddle in that rally; a best only after
  movement in the game.
- A good-bot round need not reach 5 points before the 90 s cap (the owner's live smoke judges the pace).
- The lobby at 64 rows: title, card score line and BEST! at 2x when the wall has 48 rows or more; prompt at 1x;
  the figure the wall's full height with 2 px strokes; the pictogram 16 px.
- The response budget: `response_px` at least 12 pixels two ticks after the input moves, every kind (spec 11).
- `wall_pattern index` marks every panel seam (every 64 columns and 32 rows).
