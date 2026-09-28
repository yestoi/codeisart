# Iteration 7: the oracle for games (M4a), and C37
Base 5ed04f2. Roadmap M4a (must). Carried C37. Notes applied: C23, C24, C36, the three "it06" notes.
Thin plan (Loop rule 1). "Core plan" = `docs/superpowers/plans/2026-09-26-wall-arcade-core.md`: drafts to test.
SAFETY SLICE: no. The `pattern` check is a new file, `arcade/pattern.py`, a check on content that reads
`flash.signals` and changes nothing. `flash.py`, `brightness.py`, `colorlight.py` and the runner are untouched.

## Global Constraints
- Test command, from the checkout's (or worktree's) root: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
  /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs`. At 5ed04f2: 596 collected, 596 passed, 0 skipped.
- Touch only your task's files. Never `cd`: absolute paths and `git -C`. No command over 10 minutes. Test-first
  (superpowers:test-driven-development); write the code yourself. No removed or weakened asserts in existing
  tests: this plan changes none; if you find you must, stop and report it.
- Every call that builds `Sensed` or `Audio` uses keywords (C21): `Sensed(t, camera_t=..., bodies=...)`.
- Every frame reaches the display only through the runner: limiter, then governor, then push. No game, lobby,
  bot or metric pushes; none saves images: `.save` appears only under `tools/`.
- Colours saturated, low channels at 0 (`(255, 120, 0)`, `(0, 200, 0)`, `(255, 255, 255)`): gamma is unknown.
- No game or lobby code knows which machine it runs on. Timing tests time CPU (`time.thread_time`). Seeds from
  `zlib.crc32`, never `hash()` of a str, printed in assertion messages.
- `debug_state` keys are never `arcade.game.reserved()` (`game, t, idle, attract, hidden, crashes, glitch,
  flash_held_ticks, player, present`, `fx_*`), the lobby's included.
- Owner decisions: Q11 governor last before push; Q17 three crashes per runner start hide a game; Q18 shake is
  jumps; Q19 a burst within 32 px of one in the last 0.5 s is dropped; Q20 `fx.flash` is a hold; Q23 a duel's
  card shows player 1's points, bests for solo only.
- Suite time: 36.9 s at 5ed04f2. A task adds at most 20 s of CPU (I1 at most 60 s); say what yours adds.
- A game's own files: `arcade/games/<name>.py`, `<name>_bots.py`, `<name>_feel.toml`, `tests/arcade/test_<name>.py`.
  Discovery imports only `MENU_ORDER` names, so `pong_bots` is never taken for a game.
- A finding or idea outside your task goes in your final message, not in code.

## Lanes
- SERIAL, main checkout, opus, committed before anything parallel: S1. PARALLEL, `isolation: "worktree"` from
  the local HEAD after S1, at most four at once, launched in this order as slots free: P1 (opus), P2 (opus),
  P3 (sonnet), P4 (sonnet), then P5 (sonnet), P6 (opus), P7 (sonnet).
  A task imports nothing another parallel task builds: it uses S1's pieces and stubs in its own test file.
- INTEGRATION, orchestrator, main checkout, merging P3, P1, P2, P4, P5, P6, P7 in that order, the suite after
  each: I1. I2 is the operator's, in verify, after the review.
- Shared files: S1 creates `arcade/bots.py` and `arcade/feel_budgets.toml` (given to S1 here); no other shared
  file is edited (`pyproject.toml` has the `feel` and `perf` markers already).

## S1 (opus, serial): the closed-loop feed, the protocol's last changes, `bots.py`, the default budgets
Files: `arcade/headless.py`, `arcade/game.py`, `arcade/bots.py`, `arcade/feel_budgets.toml`,
`tests/arcade/test_headless.py`, `tests/arcade/test_game.py`, `tests/arcade/test_bots.py`. Draft: core 710-713.
```
def run_headless(cfg, font, game_cls, sensed_iter: Iterable[Sensed] | Callable[[Runner], Iterable[Sensed]], ...)
    # a callable is called once with the built runner, before any launch or tick; its iterable is pulled one
    # record per tick, so a generator reads runner.game.debug_state() between ticks. Nothing else changes.
REQUIRED_SCENARIOS = ("canonical", "idle_body", "nobody")      # arcade/game.py: every game has at least these
class Game(Protocol): ...  def reset(self, size: tuple[int, int], rng: random.Random, fx: Juice) -> None
```
- `game.py`: `fx` typed `Juice` (under `TYPE_CHECKING`); the docstring gains C24's `phase` and `active` rules,
  canonical's empty-wall start and where bots and budgets live. Nothing else in `game.py` changes.
`arcade/bots.py` (the `Bot` protocol, `play` and `win_rate`, and what they need):
```
MAX_PLAY_SECONDS = 180.0
@dataclass(frozen=True)             # a bot's actor spec for one tick, one body (id 1): hips at zone x; the hand's
class Move: x: float = 0.5; hand: str = "right"; wrist_y: float | None = None  # wrist in reach-box v, None: down
class Bot(Protocol):                # reaction_ticks: sees debug_state() that late; noise: SD on x, wrist_y
    reaction_ticks: int; noise: float
    def __call__(self, state: dict, t: float) -> Move | None: ...     # None: nobody in view
class Nobody: ...                   # no input: reaction_ticks 0, noise 0.0, always None
@dataclass(frozen=True)             # frames: the pushed frames when keep_frames, else None
class Play: seed: int; ticks: int; seconds: float; done: bool; won: bool; state: dict; phases: frozenset[str]; frames
def seeds(game_cls, layout: str, n: int) -> list[int]  # zlib.crc32(f"{name}:{layout}:{i}".encode())
def for_game(game_cls) -> tuple[Mapping[str, Callable[[], Bot]], Callable[[dict], bool]]
    # arcade.games.<name>_bots's (BOTS, won); a missing module raises naming the file the game must add
def play(game_cls, bot: Bot, seed: int, layout: str = "128x32", won=None, seconds: float = MAX_PLAY_SECONDS,
         keep_frames: bool = False, font=None) -> Play
def win_rate(game_cls, bot_factory: Callable[[], Bot], seeds: Sequence[int], layout: str = "128x32") -> float
```
- `play`: `run_headless` with `ArcadeConfig(w, h, backend="fake", camera="none", audio="none")`, the font from
  `cfg.font_path` against the repository root, a callable feed. Each tick the bot gets the `debug_state()` of
  `reaction_ticks` ago (`{}` before), noise from `random.Random(seed)` clamped to 0..1; the `Move` becomes a
  `Person(x, id=1)` body, wrist held at `wrist_y`, `place`d with the default `Calibration`, in a `Sensed` shaped
  as `actors._frames` makes it. The feed stops after the tick on which `runner.game.done()`. `won` defaults to
  `for_game(...)[1]` on the last state; `phases` is every `phase` seen.
- `feel_budgets.toml`: per `kind`, each metric a table with `min` and/or `max`; `[<kind>.layouts."<WxH>".<metric>]`
  overrides one layout. Values (owner question, defaulted): control and score: `response_ticks` max 2;
  `fidelity` min 0.8; `range` min 0.6; `lit_fraction` min 0.01 max 0.5; `dim_fraction` max 0.1; `liveliness`
  min 0.001; `flash_area_raw` max 0.1; `square_flashes` max 6; `phases_reached` min 1.0; `round_seconds` min 20
  max 120. Score also: `win_good` min 0.7; `win_lazy` min 0.1 max 0.7; `win_none` max 0.05. Toy: the control
  set without `round_seconds`, `fidelity`, `range`.
Tests:
- `test_headless.py`: `test_a_callable_feed_gets_the_runner_before_the_first_tick`;
  `test_a_callable_feed_reads_state_between_ticks` (yielding while `runner.game.updates < 5` gives 5 ticks).
- `test_game.py`: `test_protocol_members_are_the_frozen_set` (the canary: members and parameter names equal a
  literal set); `test_required_scenarios`; `test_runner_passes_what_the_protocol_says` (`scores` before `reset`;
  `(w, h)` ints, a `random.Random`, a `Juice`; `update(Sensed, TICK)`; a fresh instance per launch).
- `test_bots.py` (a `Target` spy there: won when `cursor_xy` stays within 2 px of a seeded dot for 1 s):
  `test_play_repeats_under_a_seed`; `test_reaction_delay_is_honoured`; `test_noise_is_seeded_and_clamped`;
  `test_play_stops_on_done`; `test_good_beats_lazy_beats_nobody_on_target`;
  `test_for_game_names_the_missing_bots_module`; `test_budget_file_parses_and_has_every_kind`.

## P1 (opus, worktree): feel metrics
Files: `arcade/feel.py`, `tests/arcade/test_feel.py`. Draft: core amendment lines 705-709 (Task 21).
```
RESPONSE_PX = 12; LATENCY_TICKS = 2; PROBES = 8; FEEL_SECONDS = 20.0; FEEL_SEEDS = 20
DIM_LEVEL = 140                    # a lit pixel with every channel under this is dim (spec 11)
DEFAULTS = Path(__file__).with_name("feel_budgets.toml")
@dataclass(frozen=True) class Budget: metric: str; min: float | None; max: float | None; reason: str | None
def budgets(game_cls, layout: str, defaults: Path = DEFAULTS, own: Path | None = None) -> dict[str, Budget]
    # kind defaults, then its layout table, then <name>_feel.toml [budgets."<layout>"]; a game entry without a
    # non-empty `reason` raises ValueError naming the metric
def control(game_cls, own: Path | None = None) -> tuple[str, str, int] | None
    # the game file's [fidelity]: input ("cursor_x" | "cursor_y" | "zone_x"), xy (a *_xy key), axis (0 | 1)
def measure(game_cls, layout: str, seeds: int | Sequence[int] = FEEL_SEEDS, font=None) -> dict[str, float | None]
def judge(metrics: dict, budgets: dict[str, Budget]) -> list[str]   # "win_lazy 0.85 > max 0.7"; None misses
def report(game_cls, layout: str, seeds=FEEL_SEEDS, font=None) -> dict   # {"metrics", "budgets", "failures"}
```
Metrics through `run_headless` at `layout`; canonical is `SCENARIOS["canonical"]`'s first `FEEL_SECONDS`, raw
frames are the game's own drawing, pushed what the wall shows:
- `response_ticks`: at `PROBES` canonical ticks where `control()`'s input (else the cursor) moves next record, a
  second run holds every later record at that tick's input (times advance); ticks until pushed frames differ
  in `RESPONSE_PX` pixels or more; the median; `5 * LATENCY_TICKS` when never.
- `fidelity`: Pearson r of `control()`'s input of `sensed.player` against the `_xy` axis over canonical ticks
  where both exist (None without `[fidelity]`); `range`: that axis's max minus min over the wall's extent - 1.
- `lit_fraction` (pushed, mean share non-black); `dim_fraction` (raw, share of lit pixels that are dim);
  `liveliness` (raw, mean share changing per tick); `flash_area_raw`; `square_flashes` (pushed).
- From `bots.play` over `bots.seeds(game_cls, layout, n)`: `win_good`, `win_lazy`, `win_none` (`Nobody`);
  `round_seconds` (median of the `good` plays that ended done, else None); `phases_reached` (share of `PHASES`
  seen over the `good` plays, reused, not rerun).
Tests (stub games, a stub `<name>_bots` module put in `sys.modules`, tmp TOML files):
`test_follower_passes_fidelity_and_response`; `test_screensaver_fails_both`; `test_override_without_reason_is_
rejected`; `test_layout_table_overrides_the_kind`; `test_judge_names_each_failing_budget`; `test_dim_fraction_
counts_dim_lit_pixels`; `test_good_plays_are_reused`; `test_measure_repeats_under_seeds`; `test_report_is_json_ok`.

## P2 (opus, worktree): the pattern check and the generic tests for every registered game
Files: `arcade/pattern.py`, `tests/arcade/test_pattern.py`, `tests/arcade/test_all_games.py`.
Draft: core Task 20, lines 5598-5680, and its amendment lines 687-700.
```
PATTERN_PAIRS = 5; PATTERN_AREA = 0.25     # C24, BT.1702-3 Guideline 2, owner Q15
def stripes(frame: np.ndarray, gamma: float = 2.2) -> np.ndarray
    # bool mask: pixels in a row or column run of more than PATTERN_PAIRS light-dark band pairs of equal width
    # (within 1 px), each light band at least flash.THRESHOLD above its dark neighbours in flash.signals
def pattern_area(frames, gamma: float = 2.2) -> float
    # the largest share of the wall, over consecutive frames, striped in both and changed between them
    # (reversing, oscillating or moving); static stripes count 0
```
`test_all_games.py`, parametrized over `all_games()`, seeds `zlib.crc32(f"{name}:{layout}:{i}".encode())` for
i in 0..4, sizes the declared layouts plus 96x48, 300 ticks through `run_headless(..., trace=True, raw=True)`
of `random_mix` (the draft, plus `motion_rect` when `"motion" in needs`) under `degrade(**REAL_NOISE)` and of
`hostile_mix` (five bodies, eight blobs, keypoints at 0 and 1, confidence-0 limbs, flickering presence, short
both-hands-up). About 5 s of CPU per game.
- `test_every_game_soaks_without_error`: nothing raised (strict), a non-black pushed frame, every traced
  `phase` in `PHASES`, no reserved debug key.
- `test_every_game_keeps_the_flash_rule_in_the_soak`: pushed `square_flashes <= BUDGET` and `pattern_area <=
  PATTERN_AREA`; raw `flash_area <= 0.10` under the strobe inputs (`claps` at 12 Hz, `tempo(180)`, a motion grid
  alternating every tick) plus a person (spec 7.6).
- `test_every_game_fits_the_tick_budget` (`perf`, C36): 300 ticks, `RecordingDisplay(keep_all=False)`,
  `thread_time` between feed records, first 10 dropped; mean under `ARCADE_TICK_BUDGET_MS` (2.0), p95 twice it.
- `test_every_game_declares_the_required_scenarios`, `test_every_game_has_good_and_lazy_bots`: Pong gets them in
  P3, so here `xfail(strict=True, reason="until P3")`; I1 removes the marks (its only edit to this file).
`test_pattern.py`: `test_six_pair_stripes_reversing_count`; `test_five_pairs_do_not_count`; `test_static_stripes_
count_zero`; `test_moving_stripes_count`; `test_uneven_bands_are_not_stripes`; `test_a_dashed_net_is_under_the_limit`.

## P3 (sonnet, worktree): Pong's scripts, bots and budgets
Files: `arcade/games/pong.py`, `arcade/games/pong_bots.py`, `arcade/games/pong_feel.toml`, `tests/arcade/test_pong.py`.
- `pong.py`: `SCENARIOS` gains `canonical` (nobody for 2 s; `Person(0.3, id=1)` arrives at 2.0 s, raises the
  right hand at 4.5 s for 0.5 s, sweeps as `solo` from 6.0 s; 100 s), `idle_body` (`Person(0.3, id=1)` standing,
  60 s), `nobody` (30 s); `solo` and `duel` unchanged. The it06 note: `score` follows player 1 as seated at the
  first serve (by body id), not seat 0, so it never becomes player 2's points (Q23). Nothing else changes.
- `pong_bots.py`: `BOTS = {"good": Good, "lazy": Lazy}`; `won(state)`: `phase == "over"` and the human side's
  points above the CPU's. `Good`: reaction 3 ticks, noise 0.02, aims the paddle centre at the ball's y while it
  comes towards it, else back to the middle. `Lazy`: reaction 8, noise 0.08, moves only while the ball is in its
  half. Both `Move(x=0.3)`: the CPU is on the right.
- `pong_feel.toml`: `[fidelity] input = "cursor_y", xy = "left_xy", axis = 1`; `[budgets."128x32"]` overrides,
  each with a `reason` (expected: `dim_fraction`, the dashed net is dim on purpose).
- Tuning within the bands is this task's (CPU and ball speeds); a band is never loosened.
Tests, added: `test_required_scenarios_start_with_an_empty_wall`; `test_canonical_drives_the_lobby_to_pong`
(`lobby=Lobby([Pong], cfg)`: `game == "pong"` within a tick of the raise); `test_idle_body_scores_nothing`;
`test_score_stays_with_player_one_when_they_leave`; `test_bots_module_is_found`;
`test_good_beats_lazy_beats_nobody` (5 seeds: `good` wins 4 or more, `nobody` 0, `lazy` fewer than `good`);
`test_good_round_length_in_band` (median 20 to 120 s); `test_feel_file_overrides_have_reasons`.

## P4 (sonnet, worktree): `tools/arcade_evidence.py`
Files: `tools/arcade_evidence.py`, `tests/test_arcade_evidence.py`. Draft: spec 9.6; core amendment 714-718.
```
python -m tools.arcade_evidence --iteration N [--games changed|NAME[,NAME]] [--since REV] [--out DIR]
    [--seeds 20] [--allow-dirty]     # also `python tools/arcade_evidence.py` (the ROOT path insert, as arcade_shot)
EMPTY = 2.0; GIF_SECONDS = 6.0; GIF_BYTES = 300_000; GIF_EVERY = 3; GIF_MS = 100; SHEET_SECONDS = 30.0
def changed_games(since: str | None) -> list[str]   # a game's four files in `git diff --name-only since..HEAD`;
    # all games when game.py, runner.py or headless.py changed; since: the last commit touching evidence/
def clean_sha(out: Path, allow_dirty: bool) -> str  # ONCE at the start; porcelain status ignoring out; dirty:
    # exit 2 naming the paths, or with --allow-dirty sha + "+dirty"; every file written carries this sha
def gif(frames, path: Path, sha: str, scale: int = 2) -> int    # plain, every GIF_EVERY tick at GIF_MS, comment
    # = sha; scale 1 when over GIF_BYTES; raises when still over; returns the size
def package(games: list[type], out: Path, sha: str, seeds, report=None, font=None) -> list[Path]
def main(argv: list[str] | None = None) -> int
```
- Per game and declared layout, canonical through the small lobby for `SHEET_SECONDS` (starting empty, so
  attract shows): `<game>-<layout>-plain.png`, `-led.png`, `-distance.png` (arcade_shot's current functions),
  `-canonical.gif` (from 1 s before the launch), `-trace.jsonl`, `-timeline.txt` (at most ten `t phase` lines).
- `feel.json`: `{game: {layout: report(...)}}`, `report` defaulting to `arcade.feel.report` imported inside `main`.
  `games.md`: the sha, the feel table per game (metric, value, budget, ok), every image inline. Never README.md.
Tests (a stub game and stub `report` in the test file; a tmp git repo where needed):
`test_file_set_per_game_and_layout`; `test_gif_under_6s_and_300kb_with_the_sha`;
`test_sha_taken_once_and_own_outputs_never_dirty_it`; `test_dirty_tree_refused_unless_allowed`;
`test_changed_games_from_git_diff`; `test_engine_change_marks_every_game`; `test_timeline_at_most_ten_lines`;
`test_feel_json_and_games_md_from_report`; `test_runs_as_a_script_and_as_a_module` (subprocess `--help`).

## P5 (sonnet, worktree): `tools/arcade_shot.py`, provenance and the black refusal
Files: `tools/arcade_shot.py`, `tests/test_arcade_shot.py`. Draft: core Task 13 (3778-3977), amendment line 597;
only what follows. Existing signatures stay (P4 calls them); new parameters are keyword-only with defaults.
- The header band: sha, dirty flag, games, size, look, seed, scenario, lobby. Captions `#30 1.00s <game>` plus
  the game's `CAPTION_KEYS` values from the trace (the lobby's `mode` while in the lobby).
- `--allow-black`: without it, all-black pushed frames exit 2, naming the games' `needs`.
- `--look plain|led|both` (default `plain`, names unchanged; `both` writes `STEM-plain.png`, `STEM-led.png`).
  Sheets capped at 1,536 px wide: fewer columns, then a smaller scale.
- `--flash-report` prints `flash_area` raw and pushed and the mean picture level. Every run prints frames, the
  non-black count and the final `runner.state()`.
Tests, added: `test_header_has_provenance`; `test_all_black_refused_unless_allowed`; `test_width_capped_at_1536`;
`test_both_looks_written`; `test_flash_report_prints`; `test_captions_carry_caption_keys`.

## P6 (opus, worktree): C37, the mirror holds a dropped keypoint
Files: `arcade/figure.py`, `arcade/attract/lobby.py`, `tests/arcade/test_figure.py`, `tests/arcade/test_lobby.py`.
```
class KeypointHold:                  # arcade/figure.py: one per figure; Copy Me and M8 reuse it
    def __init__(self, grace: float)
    def update(self, body: Body | None, t: float) -> Body | None
        # a keypoint under MIN_CONF takes its last confident place and conf while seen within grace; a new body
        # id or None clears it; a keypoint gone longer than grace stays low, so its limb is not drawn
```
- The mirror draws `hold.update(sensed.player, sensed.t)` (and `player2`), grace `capture_grace(cfg.camera_fps)`.
  Nothing else in the lobby changes.
Tests: `test_a_single_keypoint_dropout_is_held`; `test_a_limb_gone_longer_than_grace_disappears`;
`test_hold_clears_on_a_new_body_id`; `test_mirror_under_real_noise_keeps_the_area_rule` (128x32, 64x64; the input
of evidence/it06/reviewer-notes.md, `lobby=Lobby([spy], cfg)`: raw `concurrent_area < SMALL_AREA` for each run).

## P7 (sonnet, worktree): the game guide, a project skill
File: `.claude/skills/arcade-game-authoring/SKILL.md` (committed; `.gitignore` ignores only `/.claude/worktrees/`).
Frontmatter `name: arcade-game-authoring`, `description: Use when writing or changing a game under arcade/games/`.
Under 400 lines, from spec 7.1, 8.1, 9.1 to 9.3, 11 and this plan. It says: the protocol, frozen at
`game-protocol-v1`; a game is its four files and a `MENU_ORDER` name; what the runner passes (the freeze list
below), the lobby passes nothing but the launch, a game never pushes, saves or reads the config; `debug_state`:
`phase` from `PHASES`, leaving `play` between rounds or the session cap never applies, `score`, `active` True or a
numpy bool (1, "yes" and numpy ints do not count), `_xy` wall pixels, no reserved keys; scenarios are scripts
(canonical: 2 s empty, walk-up, raised hand) and bots judge difficulty (`good`, `lazy`, `won`); budgets per kind
and layout, overrides with a reason, never loosened; the flash rule: shake, flash and bursts each keep it alone,
banner text, pops and combinations are the game's to pace, its own drawing keeps it, `flash` is a hold (False
while one shows or within 0.5 s after), no reversing stripes over a quarter of the wall; spec 11's feel guidance;
the test template (Pong's module); the "card then done()" recipe; the evidence command. No tests: the
implementer checks every named file, function and command exists at S1's commit or in this plan.

## I1 (orchestrator): the oracle, end to end on Pong
File: `tests/arcade/test_oracle.py` (and P2's two `xfail` marks removed). One module-scoped
`feel.report(Pong, "128x32", seeds=bots.seeds(Pong, "128x32", 20))`, shared by:
- `test_feel_pong_meets_its_budgets` (`feel`): `failures == []`, the message listing each by name and value.
- `test_bots_rank_on_pong`: `win_good > win_lazy > win_none`, `phases_reached == 1.0`.
- `test_evidence_package_for_pong`: `tools.arcade_evidence.package([Pong], tmp_path, "test", seeds[:2])` writes
  the file set and a `feel.json` with Pong's metrics.
A failing budget is reported by name and fixed in P3's files or sent to the owner, never loosened here.
Report the suite's count and time.

## I2 (the operator, in verify, after the review): evidence, from the repo root
```
.venv/bin/python -m tools.arcade_evidence --iteration 7 --games pong --out docs/superpowers/workflow/evidence/it07
.venv/bin/python -m tools.arcade_shot pong --lobby small --scenario duel --raw-vs-pushed \
    --out docs/superpowers/workflow/evidence/it07/it07-128x32-strobe \
    > docs/superpowers/workflow/evidence/it07/strobe-check.txt
```
Files under `--out` do not dirty the stamp. Both `-m tools.arcade_evidence` (tested) and the script path work,
so config.md's command stands. Plus collect.txt, pytest.txt, head.txt as in it06; then the tag.

## Freezing the Game protocol (`game-protocol-v1`)
True of `arcade/game.py` at the tag: `GameInfo`'s ten fields and validation as at 5ed04f2; `Game`'s `info,
scores, SCENARIOS, CAPTION_KEYS, PHASES, reset(size, rng, fx), update(sensed, dt), draw(canvas), done(),
debug_state()`; `REQUIRED_SCENARIOS`, `INPUTS`, `KINDS`, `LAYOUTS`, `RUNNER_KEYS`, `reserved()`,
`icon_from_rows`; S1's canary holds the list. What the runner passes: `scores` before `reset`; `reset((w, h),
random.Random, Juice)` on a fresh instance per launch; `update(Sensed, TICK)` with the runner's `player` and
`player2`; `draw` on a cleared `Canvas`. Known later changes, each with a journaled reason: M5's `Blob.id`,
`vx`, `vy` and per-input availability (C35) in `Sensed`.

## STRETCH (only if fewer than 60 minutes have passed at I1's end; serial, main checkout)
- X1 (opus): spec 9.3's other metrics in `feel.py` (score visibility, legibility after `distance` at 5 m,
  fail-versus-win transient, the idle hint) with default budgets. Least needed: the 5 m sheet shows the score.
- X2 (sonnet): `tools/arcade_feel.py GAME [--layout]` prints the feel table (`games.md` already has it).
- X3 (opus): `tests/arcade/test_privacy.py` (core amendment 700-703), spec 9.1's layout hook in its conftest.

## Decisions
- Bots and budgets in `<name>_bots.py`, `<name>_feel.toml`: parallel games never share a file; `bots.py` stays generic.
- `run_headless` takes a callable feed: the closed loop needs the runner between ticks, nothing more.
- A bot's `Move` becomes a `Person` body: the same geometry and `place` as every script.
- `play` applies reaction delay and noise from the seed: bots stay simple and every play repeats.
- Required scripts `canonical`, `idle_body`, `nobody`; spec 7.1's `fail` and `win` are the bots' job now.
- Canonical starts with 2 s of an empty wall: one script shows attract, drives the lobby and feeds feel.
- The soak checks traced phases are declared; reaching all is judged on `good` plays (no `over` in 300 ticks).
- Response latency by holding the input from a probe tick: a counterfactual without M8's event scripts.
- `dim_fraction` on raw frames: the limiter dims pushed frames on purpose.
- The evidence tool writes `games.md`, not `README.md`: the README and its decision are the operator's.
- Its dirty check ignores `--out`, the sha taken once: its own and the operator's files never mark it. GIFs with
  Pillow (12.3 in the venv; imageio is absent): no new dependency.
- Pong's `score` stays with player 1 by id: the it06 note, within Q23's default.
- 5 seeds in Pong's tests, 20 in I1 and the evidence: spec 9.3's count where it is judged, a short suite.

## Owner questions (defaulted)
- The feel budget numbers (spec 9.3 gives none; 2 ticks, 12 px and rounds of 20 to 120 s are spec 11's).
- The win bands: `good` at least 0.7, `lazy` 0.1 to 0.7, no input at most 0.05.
- Dim is every channel under 140 (spec 11's wall-look line); Pong's dim net is an override with a reason.
- The GIF: 6 s from 1 s before the launch, every third tick at 10 fps, plain look.
- The stripe rule's reading: bands of equal width within 1 px, contrast of `THRESHOLD` in `flash.signals`.
