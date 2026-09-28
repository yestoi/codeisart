# Iteration 6: first playable, headless (M3b), camera stretch (M3c)
Base 6403cc3. Roadmap M3b (must), M3c (stretch). Carried C30, C31. Notes applied: C21, C23, C28, C33, C36.
Thin plan (Loop rule 1): no bodies. "Core plan" = `docs/superpowers/plans/2026-09-26-wall-arcade-core.md`; a
core-plan line range named below is a draft to test, not text to paste.
SAFETY SLICE: no. C30 and C31 change `arcade/runner.py` only (the cap's `phase` compare, the camera result check,
`PlayerLock`, the result's score). Limiter, governor, push order untouched; `flash.py`, `brightness.py` untouched.

## Global Constraints
- Test command, from the checkout's (or worktree's) root: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
  /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs`. At 6403cc3: 478 collected, 478 passed, 0 skipped.
- Touch only your task's files. Never `cd`: absolute paths and `git -C`. No command over 10 minutes. Test-first
  (superpowers:test-driven-development); write the code yourself. No removed or weakened asserts in existing
  tests: this plan changes none; if you find you must, stop and report it.
- Every call that builds `Sensed` or `Audio` uses keywords (C21): `Sensed(t, camera_t=..., bodies=...)`.
- Every frame reaches the display only through the runner: limiter, then governor, then push. No game or lobby
  pushes; none saves images: `.save` appears only under `tools/`.
- Colours saturated, low channels at 0 (`(255, 120, 0)`, `(0, 200, 0)`, `(255, 255, 255)`): gamma is unknown.
- No game or lobby code knows which machine it runs on. Timing tests time CPU (`time.thread_time`). Seeds from
  `zlib.crc32`, never `hash()` of a str, printed in assertion messages.
- `debug_state` keys are never `arcade.game.reserved()` (`game, t, idle, attract, hidden, crashes, glitch,
  flash_held_ticks, player, present`, `fx_*`), the lobby's included.
- Owner decisions: Q11 governor last before push; Q17 three crashes per runner start hide a game; Q18 shake is
  jumps; Q19 a burst within 32 px of one in the last 0.5 s is dropped; Q20 `fx.flash` is a hold.
- A finding or idea outside your task goes in your final message, not in code.

## Lanes
- SERIAL, main checkout, opus, one at a time, committed before anything parallel: S1, then S2.
- PARALLEL, one message, each `isolation: "worktree"` from the local HEAD after S2: P1 (opus), P2, P3 (sonnet).
- INTEGRATION, orchestrator, main checkout, merging P1, P2, P3 in that order: I1. I2 is the operator's, in verify.
- STRETCH, serial, main checkout (model file and camera are not in git), after I1 is green: X1, X2.
- Shared files: none edited. `tests/arcade/helpers.py` (callers use `run_headless`) and `arcade/games/__init__.py`
  (`"pong"` is in `MENU_ORDER`; discovery reads `GAME`) stay as they are.

## S1 (opus, serial): C30 and C31
Files: `arcade/runner.py`, `tests/arcade/test_runner.py`.
- C30a `_session_rule` (runner.py:509-510): `phase = self._state.get("phase", "play")`; cap only when
  `isinstance(phase, str) and phase != "play"`. A non-str phase counts as "play", as a missing key does. Nothing
  in the session rules calls `bool()` on a game-supplied value.
- C30b `_camera_result` (216-228): `motion` is None or a 2-D `np.ndarray` with `motion.dtype.kind in "biuf"`;
  any other dtype raises there, so `sense()` treats the camera as failed (logged once) and never builds the
  `Sensed` at 599-600 from it.
- C30c `end_session` (367): `SessionResult.score` is the game's `score` as a finite float or None (the rule of
  `scores._finite`; import it or add a public helper in runner.py, no edit to scores.py). The end card formats it.
- C31 `PlayerLock.update` (108-134): while the locked id is absent (slot kept, player None) clear `self._rival`,
  so the switch needs `SWITCH_SECONDS` of a larger rival while the player is seen.
- `_push` is unchanged; C30 asks only for its test.
Tests, added to `tests/arcade/test_runner.py` (`make_runner`, `feed`, `stand`, `ticks`, `spy`):
- `test_an_array_phase_never_raises_out_of_tick`: strict=False, `extra={"phase": np.array(["a", "b"])}`,
  `players=1`, three in-zone persons, `max_session_seconds=1.0`: 90 ticks raise nothing; not `capped`. And
  `test_a_numpy_str_phase_still_caps`: `np.str_("serve")` under the same setup ends `capped`.
- `test_an_object_motion_grid_is_a_failed_source`: `latest()` gives an object-dtype 2-D grid; `sense()` gives no
  bodies, the lobby's status has camera_ok False, one log line over 3 calls.
- `test_a_raising_limiter_or_governor_pushes_nothing`: parametrized `limiter`, `governor`; its `apply` raises;
  after 3 ticks `display.count == 0` and one "display push failed" line.
- `test_rival_timer_restarts_when_the_player_returns`: A locked; rival B at 1.5x from t0; A missing t0+0.2 to
  t0+0.6; the lock is A at t0+1.1 and B from t0+1.6 (within a tick).
- `test_session_result_score_is_a_finite_float_or_none`: scores `np.array([3])`, `4`, `nan` give None, 4.0, None.

## S2 (opus, serial): a lobby for `run_headless`
Files: `arcade/headless.py`, `tests/arcade/test_headless.py`.
```
def run_headless(cfg, font, game_cls: type | Sequence[type], sensed_iter: Iterable[Sensed], seed: int = 0,
                 strict: bool = True, trace: bool = False, raw: bool = False, display=None,
                 lobby: LobbyLike | None = None) -> tuple[list[np.ndarray], Runner]
```
- `game_cls`: one game class or a sequence, the runner's `games`. `lobby=None`: unchanged (`NullLobby`, the
  first game launched before the first tick).
- `lobby` given: that instance is the runner's lobby, nothing is launched, the lobby's `request` launches;
  `runner.game` is None until then. `helpers.run` unchanged.
Tests (the requesting lobby is a `StubLobby` subclass in the test file that sets `request` on tick N):
- `test_with_a_lobby_the_run_starts_in_the_lobby`: no request: every trace `game == "lobby"`, `runner.game is None`.
- `test_the_lobbys_request_launches_the_game`: request on tick 5: `"lobby"` for ticks 0-4, the spy from tick 5.
- `test_several_games_are_offered_to_the_lobby` (`lobby.available` has both; requesting the second launches it);
  `test_a_sequence_without_a_lobby_launches_the_first`.

## P1 (opus, worktree): the small lobby and the mirror figure
Files: `arcade/figure.py`, `arcade/attract/__init__.py` (docstring only), `arcade/attract/lobby.py`,
`tests/arcade/test_figure.py`, `tests/arcade/test_lobby.py`.
`arcade/figure.py` owns `to_wall` and `draw_figure`; M8's director and Copy Me import them from there. Draft: core
Task 11, lines 3389-3523 (`Puppet.draw`; tests 3405-3447), changed to a uniform scale, 2 px strokes, a rect, no game.
```
FRAME_ASPECT = 4 / 3; STROKE = 2     # camera frame width over height; px (spec 7.3 step 2)
def to_wall(body: Body, rect: tuple[int, int, int, int], aspect: float = FRAME_ASPECT
            ) -> Callable[[float, float], tuple[int, int]]
    # frame-normalised (x, y) to a wall pixel in rect (x, y, w, h): box height fills h, one scale on both axes
    # (x times aspect), box centre on rect centre
def figure_rect(body: Body, size: tuple[int, int]) -> tuple[int, int, int, int]
    # a square of the wall's height centred on column round(zone_x * (width - 1))
def draw_figure(canvas: Canvas, body: Body, rect, color: Color, stroke: int = STROKE) -> None
    # SKELETON limbs with both keypoints conf >= MIN_CONF, stroke px thick; a head disc when the nose is seen
```
`arcade/attract/lobby.py`:
```
PICTOGRAM_SECONDS = 1.5; BREATH_HZ = 1.0; BREATH_LOW = 0.4; CARD_SECONDS = 3.0
TITLE_COLOR = (120, 60, 0); TEXT_COLOR = (255, 160, 0); PICTOGRAM_COLOR = (0, 200, 0)
HAND_UP: np.ndarray                              # 16x16 bool, icon_from_rows, 2 px strokes
MODES = ("attract", "mirror", "invite", "card")
class Lobby:                                     # runner.LobbyLike; info = None; request: str | None
    def __init__(self, games: Sequence[type], cfg: ArcadeConfig)
    def reset(self, size, rng, fx=None); update(sensed, dt); draw(canvas); done() -> False; debug_state()
    def set_available(self, names); set_status(camera_ok, mic_ok, inputs, calibrated); end_session(result)
    def featured(self) -> str | None
```
- `featured()`: the first `MENU_ORDER` name among the constructor's games that is in the last `set_available`,
  has `cfg.layout` in `info.layouts` and `info.needs <= inputs`. Inputs are all of `arcade.game.INPUTS` until the
  first `set_status` (headless runs never call `sense()`). None: never requests.
- attract (no `sensed.player`): the featured title at 1x, centred, `TITLE_COLOR`, static; nothing when None.
- mirror: `draw_figure` for `sensed.player` in `PLAYER_COLORS[0]` and `sensed.player2` in `PLAYER_COLORS[1]`,
  each in its `figure_rect`, from the tick the runner locks them.
- invite: `Hold(PICTOGRAM_SECONDS, grace=capture_grace(cfg.camera_fps))` on "a player is locked"; then `HAND_UP`
  breathes (light BREATH_LOW..1 at BREATH_HZ) beside the player's figure, on the side with more room.
- start: one `Edge(capture_grace(cfg.camera_fps))` on `sensed.player.raised_wrist is not None`, updated every tick
  (False without a player). Its rising edge in mirror or invite sets `request = featured()`. On a newly locked
  player id the Edge is rebuilt and primed with the current value. Blobs and body centre never start anything.
- card: from `end_session(result)`, `CARD_SECONDS` of: the title and score (when not None), "BEST!" when
  `score >= best` (both not None), then "NEXT: RAISE A HAND" when `result.waiting`, else "HAND UP = AGAIN",
  wrapped to the width, `TEXT_COLOR`. Hands do nothing during it; the Edge is primed at its end.
- `debug_state`: `mode`, `near` (s, 3 d.p.), `pictogram`, `figures` (0-2), `featured`, `card_game`, `card_score`,
  `card_reason`, `card_waiting` (None outside the card), `figure_xy` (player's head on the wall), `pictogram_xy`.
- Its own drawing keeps the flash rule: mode changes are single steps, the breath is 1 Hz, nothing fills the field.
`tests/arcade/test_figure.py`: `test_to_wall_is_uniform` (offsets of 0.1 in y and 0.1/aspect in x give equal
pixel offsets); `test_figure_rect_follows_zone_x_and_fills_the_height`; `test_mirror_draws_2px_figure_in_player_colour`
(every lit pixel the colour, limbs 2 px wide); `test_low_confidence_limbs_skipped` (fewer lit pixels, more than 0).
`tests/arcade/test_lobby.py` (through `run_headless(..., lobby=Lobby(games, cfg))`, `helpers.spy` games named from
`MENU_ORDER`, actors from `arcade.sources.actors`):
- `test_implements_lobbylike` (every member; `info is None`; `done()` False); `test_two_bodies_two_colours`.
- `test_attract_shows_the_featured_title_statically`: nobody; frames identical tick to tick.
- `test_mirror_within_half_second`: arrival at 1.0 s; `figures == 1`, `PLAYER_COLORS[0]` pixels by 1.5 s.
- `test_pictogram_after_1_5s`: False at 1.4 s near, True by 1.6 s; its light swings at 1 Hz.
- `test_raised_hand_requests_the_featured_game` (trace `game` is the spy within a tick of the raised wrist);
  `test_hand_up_on_arrival_does_not_start` (up on arrival for 3 s: no launch; lowered then raised: launch).
- `test_featured_is_first_in_menu_order_that_fits`: hidden, wrong-layout and missing-input games never requested.
- `test_end_card_shows_the_result_for_3_seconds`: spy `finish_after`, `extra={"score": 3}`: `mode == "card"`,
  `card_score == 3.0` for 3.0 s (within a tick), then `mirror`.
- `test_end_card_says_next_when_someone_waits`: three in-zone persons, a 1-player spy: `card_waiting` True and the
  card frame differs from the not-waiting one. `test_hands_during_the_card_do_nothing`.
- `test_lobby_frames_keep_the_flash_rule`: raw frames of walk-up, pictogram, launch, card: `flash_area == 0.0`,
  `concurrent_area < SMALL_AREA`, `square_flashes <= BUDGET`. `test_debug_keys_are_not_reserved`.

## P2 (sonnet, worktree): Pong
Files: `arcade/games/pong.py`, `tests/arcade/test_pong.py`. Spec 8 game 2; no core-plan body.
```
GAME = Pong
class Pong(Game):
    info = GameInfo(name="pong", title="PONG", verb="BLOCK", icon=ICON, needs=frozenset({"pose"}),
                    layouts=frozenset({"128x32"}), players=2, kind="score")
    PHASES = ("serve", "play", "point", "over"); CAPTION_KEYS = ("phase", "left", "right")
    SCENARIOS = MappingProxyType({"solo": solo, "duel": duel})     # () -> Iterator[Sensed], via scene()
WIN_POINTS = 5; MAX_SECONDS = 90.0            # first to 5, else the leader at 90 s (a tie: player 1's side)
SERVE_SECONDS = 1.0; POINT_SECONDS = 1.0; OVER_SECONDS = 2.0
BALL_START = 40.0; BALL_GAIN = 1.08; BALL_MAX = 110.0    # px/s; x speed times BALL_GAIN per paddle hit
MAX_ANGLE = 60; CPU_SPEED = 28.0      # degrees off horizontal by hit offset; px/s, under a late ball: beatable
PADDLE_W = 2; PADDLE_H = height // 4; BALL = 2; JOIN_SECONDS = 1.0
CPU_COLOR = (0, 200, 0); BALL_COLOR = (255, 255, 255); NET_COLOR = (0, 0, 96)
```
- Paddles on columns 0-1 and width-2..width-1. A human paddle's centre is `body.cursor[1] * (height - 1)` (the
  reach box, spec 7.3); no cursor holds it. Humans: `sensed.player` (`PLAYER_COLORS[0]`), `sensed.player2`
  (`PLAYER_COLORS[1]`). Sides by `zone_x` at each serve (smaller left); a solo player keeps the side they stand
  on, the CPU the other. A second body present for `JOIN_SECONDS` joins at the next serve in place of the CPU; a
  human gone over `capture_grace(10)` gives way to the CPU at the next serve.
- Phases: serve (ball at centre, `SERVE_SECONDS`), play, point (`POINT_SECONDS` after a goal), over
  (`OVER_SECONDS`, then `done()`). It leaves `play` after every point, so the runner's cap can apply.
- Juice: `fx.burst` at a paddle hit in its colour; `fx.shake(2, 0.3)` and `fx.pop("+1", ...)` on a point;
  `fx.celebrate(winner colour)` at over. No `fx.flash` of its own, no full-field drawing. Digits 1x at the top
  in each side's colour; a dashed net.
- `score`: solo, the human's points; duel, player 1's. `self.scores.record(score)` at over, solo only.
- `active`: a Python bool, True on a tick where a human paddle moved 1 px or more or hit the ball.
- `debug_state`: `phase, score, left, right, cpu` ("left" | "right" | None), `humans`, `active`, `speed`,
  `ball_xy`, `left_xy`, `right_xy` (paddle centres), wall coordinates.
- 64x64: never offered; runs and stays legible with the same rules.
- Scenarios: `solo`: `Person(0.3, id=1)`, right hand raised at 2.5 s for 0.5 s, then its right wrist sweeping
  0 to 1 and back every 1.2 s from 4.0 s, 100 s long. `duel`: the same plus `Person(0.7, id=2)` arriving at 0.5 s,
  right wrist held at 0.5. The walk-up and raise let them drive the lobby too (I1, I2).
`tests/arcade/test_pong.py` (through `helpers.run`; seeds `zlib.crc32(f"pong:{layout}:{i}".encode())`):
- `test_registered_and_declared`: `get_game("pong") is Pong`; the info, PHASES and CAPTION_KEYS above.
- `test_paddle_follows_hand_height`: wrist 0.1 then 0.9: `left_xy[1]` near the top then the bottom.
- `test_solo_player_gets_the_cpu_on_the_other_side`: at x 0.3 `cpu == "right"`, at 0.7 `"left"`.
- `test_cpu_is_beatable`: a ball at `BALL_MAX` aimed at the corner far from the CPU paddle is missed.
- `test_phase_leaves_play_after_every_point`: serve, play, point in order per point.
- `test_duel_and_solo_scenarios_reach_a_result`: `done()` within the scenario.
- `test_runs_and_stays_legible_on_64x64`: 300 ticks of `duel`, ball and paddles lit, nothing raised.
- `test_own_drawing_keeps_the_flash_rule`: raw frames of `duel`: `flash_area == 0.0`, `square_flashes <= BUDGET`.
- `test_second_player_joins_at_the_next_serve`; `test_ball_speeds_up_on_each_hit_up_to_the_max`;
  `test_first_to_5_goes_over_then_done`; `test_time_limit_ends_at_90s`; `test_active_is_a_bool_and_true_on_input`;
  `test_seeded_runs_repeat`; `test_debug_keys_not_reserved_and_xy_on_the_wall`.

## P3 (sonnet, worktree): `tools/arcade_shot.py`, small version
Files: `tools/arcade_shot.py`, `tests/test_arcade_shot.py`. No `tools/__init__.py`: `tools` is already a namespace
package (`tests/test_wall_pattern.py` does `from tools import wall_pattern`). Draft for the sheets:
`docs/superpowers/workflow/evidence/it05/runner_sheet.py`. Core Task 13 (lines 3778-3977) is M4a's full tool.
```
python -m tools.arcade_shot GAME [GAME ...] --out STEM [--lobby none|small|MOD:ATTR] [--size 128x32]
    [--scenario NAME|MOD:ATTR] [--ticks N] [--every 15] [--cols 4] [--scale 2] [--look plain|led] [--seed 0]
    [--no-strict] [--raw-vs-pushed] [--from N]
def resolve_game(spec: str) -> type                  # "pong" -> arcade.games.get_game; "mod:Attr" -> importlib
def resolve_lobby(spec: str) -> Callable[[list[type], ArcadeConfig], Any] | None
    # "none" -> None; "small" -> arcade.attract.lobby:Lobby; "mod:Attr" -> importlib; called as f(games, cfg)
def resolve_scenario(spec: str | None, games: list[type], ticks: int | None) -> Iterable[Sensed]
    # NAME -> games[0].SCENARIOS[NAME](); "mod:attr" -> callable(); None -> Person(0.5, id=1) standing, 300 ticks
def shoot(games, sensed, cfg, font, lobby=None, seed=0, strict=True) -> tuple[list, list, list, Runner]
    # run_headless(trace=True, raw=True, lobby=...): (pushed, raw, trace, runner)
def contact_sheet(frames, trace, look: str, scale: int, every: int, cols: int, title: str) -> Image.Image
def raw_vs_pushed(raw, pushed, start: int, count: int = 40, scale: int = 2, title: str = "") -> Image.Image
def git_sha() -> str                                 # short sha, "+dirty" when the tree is dirty
def save_png(image: Image.Image, path: Path, sha: str) -> None     # PngInfo text chunk "git"
def main(argv: list[str] | None = None) -> int
```
- Writes `STEM.png` (`render(frame, look, scale, cfg.gamma)`, cells captioned `#30 1.00s <game> <phase>`, a
  title band with sha, size, seed, games, lobby) and `STEM-distance.png` (`render(frame, "distance", max(4,
  scale), cfg.gamma, metres=5.0)`, C23).
- `--raw-vs-pushed` also writes `STEM-raw-vs-pushed.png`: 40 ticks from `--from`, by default centred on the tick
  of the largest raw change, each a raw | pushed pair (as it05). Prints the `#+.` luminance timelines, `held`,
  `flash_area` raw and pushed, `concurrent_area(pushed)`, `square_flashes(pushed)`, `BUDGET`; exits 1 when
  `square_flashes(pushed) > BUDGET` or `concurrent_area(pushed) >= SMALL_AREA`.
- Imports no game module and no `arcade.attract` at module import, only inside the resolvers.
- cfg `ArcadeConfig(width, height, backend="fake", camera="none", audio="none")`; font from `cfg.font_path`.
Tests (stubs `Blink`, `Strobe` and a `StepLobby` requesting on tick 3 defined in the test file, passed as
`tests.test_arcade_shot:Blink` and so on):
- `test_png_has_the_git_sha_text_chunk`; `test_cells_match_render` (a cell equals `render(frame)`);
  `test_distance_sheet_written_at_scale_4_or_more`; `test_scenario_from_the_game_and_ticks_honoured`.
- `test_lobby_and_game_by_module_path`: trace `lobby` for ticks 0-2, then the stub game.
- `test_import_does_not_load_games_or_the_lobby`: in a subprocess, no `arcade.games.pong` or `arcade.attract`.
- `test_raw_vs_pushed_sheet_and_report`: `Strobe`: the PNG exists, stdout has the timelines and numbers, exit 0.
- `test_raw_vs_pushed_exits_1_when_pushed_flashes`: `FlashGovernor.apply` monkeypatched to return its input.

## I1 (orchestrator): the M3b "done when"
File: `tests/arcade/test_first_playable.py`. No shared-file edits. Uses `Pong.SCENARIOS["duel"]` and `["solo"]`
(built from `scene`, `Person.arrive`, `raise_hand`, `wrist`), `run_headless(make_cfg((128, 32)), font5x7, [Pong],
..., lobby=Lobby([Pong], cfg), trace=True, raw=True)`, and `flash_area`, `concurrent_area`, `square_flashes`,
`BUDGET`, `SMALL_AREA` from `arcade.flash`.
- `test_two_players_walk_up_play_pong_and_see_the_card`: `mode` attract then mirror (figure within 0.5 s of
  arrival), `pictogram` after 1.5 s near, `game == "pong"` within a tick of the raise; `humans == 2`, `cpu is
  None`, `left_xy` follows player 1's sweep while the other paddle stays; Pong ends done at 5 points or 90 s; the
  `SessionResult`: `game "pong"`, `reason "done"`, `players 2`, `score` equal to Pong's last; then `mode ==
  "card"` with that score for 3 s.
- `test_solo_walk_up_plays_the_cpu`: `humans == 1`, `cpu == "right"`, result `players 1`, a best recorded.
- `test_first_playable_keeps_the_flash_rule`: whole duel run, pushed: `square_flashes <= BUDGET`,
  `concurrent_area < SMALL_AREA`, `flash_area == 0.0`; raw: `flash_area <= 0.10` (spec 7.6).

## I2 (the operator, in verify, after the review; not the orchestrator): evidence, from the repo root
```
mkdir -p docs/superpowers/workflow/evidence/it06
.venv/bin/python -m tools.arcade_shot pong --lobby small --scenario duel --every 30 --cols 6 \
    --out docs/superpowers/workflow/evidence/it06/it06-128x32-first-playable
.venv/bin/python -m tools.arcade_shot pong --lobby small --scenario duel --raw-vs-pushed \
    --out docs/superpowers/workflow/evidence/it06/it06-128x32-strobe \
    > docs/superpowers/workflow/evidence/it06/strobe-check.txt
```
The second exits 0. Plus collect.txt, pytest.txt, head.txt as in it05.

## STRETCH, M3c (serial, main checkout; what is not done moves to iteration 7)
X1 (opus), the MediaPipe camera, pose only. Files: `arcade/sources/camera.py` (`ThreadedCamera`, `BodyTracker`,
`assign`), `arcade/sources/pose_mediapipe.py`, `tests/arcade/test_camera.py`, `tests/arcade/test_pose_mediapipe.py`.
Draft: core Task 16, lines 4397-4843, amendment 631-648. Changes: `latest() -> (capture_t, bodies, (), None) |
None`, no `FrameFeatures`, blobs or motion until M5; `clock` injected (default `time.monotonic`), `capture_t` its
reading at capture, in seconds; MediaPipe on the unflipped frame, `sources/mirror.py` flips once when
`cfg.mirror`, no `cv2.flip`; model `arcade.main.MODEL_PATH`; no `tools/fetch_models.py` or clip test.
Tests: the amendment's list (lines 640-648) without `test_mediapipe_runs_on_clip`, plus
`test_capture_stamped_on_the_injected_clock_in_seconds` and `test_latest_has_no_blobs_and_no_motion`.
X2 (opus), sources and `python -m arcade run`. Files: `arcade/sources/__init__.py`, `arcade/sources/scripted.py`,
`arcade/main.py`, `tests/arcade/test_main.py`, `tests/arcade/test_sources.py`; `arcade/config.py` and
`arcade.toml` only if a field is missing (none expected). Draft: core Task 18, lines 5085-5391, amendment 660-674.
- `make_sources(cfg, size, clock=time.monotonic, script: str | None = None) -> (camera, audio)`: `mediapipe` ->
  X1; `none` -> `latest()` None; audio the none source until M5; `script` -> `ScriptedCamera(frames, clock)`, one
  frame per `latest()` stamped `clock()`, from `SCRIPTS = {"walkup": ...}` built with `scene`.
- `build_display(cfg)` (C23): `sdl` -> `PreviewDisplay(SDLDisplay(w*scale, h*scale, 1), cfg.look, scale,
  cfg.gamma)`; `fake` passes through.
- `run`, the default command: `--seconds S` (max_ticks S * fps), `--script NAME`. `main` calls `all_games()` once
  (C28) and builds `Runner(cfg, display, font, Lobby(games, cfg), games, scores=Scores(data_dir / "scores.json"),
  sessions=SessionLog(data_dir / "sessions.jsonl"), calibration=load_calibration(data_dir),
  local_clock=datetime.now, lux=None)` (C36). No `Director` (M8); no record, calibrate or stats (M5).
- Tests: `test_build_display_wraps_sdl_in_preview_and_passes_fake_through`, `test_make_sources_none_and_scripted`,
  `test_main_builds_runner_with_the_small_lobby_and_games_once` (for `..._with_director` until M8),
  `test_scripted_camera_stamps_the_runner_clock`, `test_run_seconds_exits_zero_under_dummy_sdl` (subprocess).
- Done when `python -m arcade run --seconds 5 --script walkup` exits 0 under the SDL dummy driver and
  `python -m arcade doctor --require camera,pose` passes.

## Decisions
- A non-str `phase` counts as "play": the same as a missing key, and comparing only a str cannot raise.
- Motion grids limited to bool, int, uint, float dtypes: those `np.asarray(..., bool)` and the resample take safely.
- `SessionResult.score` is a finite float or None: the end card formats it, and an array would crash the lobby.
- C31 clears the rival while the player is missing: the timer counts only time when both are seen.
- `run_headless(lobby=...)` takes an instance and `game_cls` a class or sequence: every caller keeps its argument.
- `to_wall` and `draw_figure` live in a new `arcade/figure.py`: not an engine file; lobby, M8 and Copy Me share it.
- `FRAME_ASPECT = 4/3`: both camera streams are 4:3, so the figure is not stretched sideways.
- The featured game is the first in `MENU_ORDER` that fits: the minimum until M8's rotation and doors.
- The lobby assumes every input until `set_status`: headless runs never call `sense()`.
- The lobby's Edge is primed on a new player and after the card: a hand left up never fires by itself.
- Pong declares only 128x32 (spec 8); on 64x64 it runs legibly and is never offered.
- Pong ends at 90 s at the latest: spec 8's 45 to 90 s rule; it also bounds the tests.
- Pong's scenarios begin with a walk-up and a raise: one script serves the game tests, I1 and the evidence.
- The strobe check exits non-zero on failure: the evidence command is a check as well.
- X1 skips `fetch_models` and the clip test: the model is on disk and `doctor` is the gate.

## Owner questions (defaulted)
- The lobby with nobody near, before M8's modes: the featured game's title, static and dim.
- The duel end card's score: player 1's points; bests recorded for solo Pong only.
- A raised hand during the 3 s end card does nothing (no instant replay); after it a raise starts the game.
- A hand already up when a player walks in must be lowered and raised again to start.
