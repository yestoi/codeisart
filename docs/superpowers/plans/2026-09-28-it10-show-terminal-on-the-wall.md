# Iteration 10: the show daemon's terminal on the wall (D1)
BASE: HEAD at the spawn. Roadmap D1 (owner decisions Q33, Q49). No carried fixes are tagged for `show/`. Thin plan.
"Core plan" = `docs/superpowers/plans/2026-09-22-show-daemon.md`; its Amendments (lines 13 to 71) override its task
bodies. "Spec" = `docs/superpowers/specs/2026-09-22-code-is-art-design.md`, revision 2, which wins over the core plan
(the terminal is 80x23 plus the strip on row 24). The core plan's code is a draft to test, never text to paste.
SAFETY SLICE: no: flash.py, brightness.py, colorlight.py and the runner's order are untouched; no display path (Q50).

## Global Constraints
- Test command, from the checkout's (or worktree's) root: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
  /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs`. At 40e8226: 762 collected, 0 skipped, 173 s.
- Suite time after this iteration: at most 192 s. Shares: T3 2 s, T4 6 s, T6 1 s, T7 0.5 s, T8 0.5 s, T9 3 s,
  T-shot 4 s. Report what yours added (`--durations=0` on your module).
- Test-first (superpowers:test-driven-development); write the code yourself. Touch only your task's files. Never
  `cd`: absolute paths; in a worktree, plain git from its root, one command per Bash call. No `git stash`, no push,
  no command over 10 minutes. The arcade's suite stays green.
- Tests leave nothing behind: files only under `tmp_path`; every child is killed in teardown (a fixture that yields,
  then calls `kill()`), its process group included. Tests needing a C compiler: `skipif(shutil.which("cc") is None)`.
  Timeouts in tests are named constants; each test that runs a child finishes in about 2 s or less.
- Pump timing asserts use `time.monotonic`; the renderer's perf test `time.thread_time` and the `perf` marker. Every
  timing assert prints its readings.
- A bound or test this plan names that cannot be met is never loosened: commit what passes, save the failing test
  in your scratchpad, report the readings (numbers) and go on. The orchestrator takes no rulings while agents run.
- Shared files (`pyproject.toml`, `tests/conftest.py`, `.gitignore`, `show.toml`, `show/config.py`) are not edited:
  pyte, numpy and Pillow are dependencies; the `font` and `fast_cfg` fixtures and the `perf` marker exist. A task
  that finds it needs a shared file stops that part and reports it. A test needing more glyphs than conftest's `font`
  (only `A`) builds its own `Font` in its own module.
- `tests/` is a package: `from tests.show_helpers import ...`, never `from helpers`. Findings outside your task go in
  your final message.

## Lanes (no serial lane: no arcade engine file is touched)
- GROUP 1, one message, `isolation: "worktree"` from the local HEAD after the plan's commit: T3 (opus), T4 (opus),
  T6 (sonnet), T9 (opus). No task imports what another builds. Merge T3, T4, T6, T9 in that order, suite after each.
- GROUP 2, one message, worktrees from the merged HEAD: T7 (sonnet), T8 (sonnet), T-shot (sonnet). T-shot builds on
  T3 and T4 as merged; T7 may use T6's `tests/show_helpers.py`. Merge T7, T8, T-shot, suite after each; then I1.

## Geometry (decision; every task reads it)
`Config` is not changed. `cfg.rows` (24) counts the wall's text rows including the strip. A normal entry's terminal
is `Terminal(cfg.columns, cfg.rows - 1)`, 80x23; a `full_screen` entry's has `cfg.rows`, 80x24. The renderer takes
the wall's rows, `Renderer(font, cfg.width, cfg.height, cfg.columns, cfg.rows, cfg.phosphor_rgb, cfg.glow)`, draws
the screen's lines into rows 0..rows-2 (0..rows-1 for `full_screen`) and the strip on row rows-1. Full tier: 480 of
512 px wide (x0 16), 192 of 192 px high (y0 0). Reduced tier: `rows = 16`, `height = 128` (Q51).

## T3 (opus): the renderer
Files: `show/renderer.py`, `tests/test_renderer.py`. Draft: core plan lines 546 to 760. Changes: the strip replaces
`status` (amendment Task 3); `full_screen`, `strip_visible`; a screen of any line count up to `rows` is drawn, extra
lines or columns ignored; non-Latin-1 is `?` in cells, the strip and `draw_text` (the draft maps it to chr(255) in
the strip and `draw_text`); empty cell data (a wide character's right half) is a space; the cursor is never drawn on
the strip; glow by padded slices, not `np.roll`; the dirty cache (spec 4.2, 4.6).
```
NORMAL = 0.7                       # normal text at 70 % of the phosphor, bold at 100 %
class Renderer:
    def __init__(self, font: Font, width: int, height: int, columns: int, rows: int,
                 phosphor: tuple[int, int, int], glow: bool = False)   # ValueError: columns*6 > width, rows*8 > height
    x0: int; y0: int               # (width - columns*6) // 2, (height - rows*8) // 2
    def render(self, screen: pyte.Screen, cursor_on: bool = False, strip: str = "", *,
               full_screen: bool = False, strip_visible: bool = True) -> np.ndarray
        # (height, width, 3) uint8 at full phosphor (backends set brightness). The strip, cut or padded to columns, in
        # reverse video on row rows-1 unless full_screen and not strip_visible. Nothing changed (screen.dirty empty;
        # same cursor x, y, hidden, cursor_on, strip, full_screen, strip_visible): the cached frame, read-only.
        # Otherwise redraw and clear screen.dirty.
def apply_glow(frame: np.ndarray, amount: float = 0.3) -> np.ndarray     # 4-neighbour max, padded, no wrap
def draw_text(frame: np.ndarray, x: int, y: int, text: str, font: Font, color: tuple[int, int, int]) -> None
    # clips at every edge (negative x or y included); non-Latin-1 as '?'
```
Acceptance tests (the `font` fixture; screens are `pyte.Screen(80, 23)` unless named):
- `test_frame_shape_and_only_the_strip_lit_when_blank`: (192, 512, 3) uint8; rows 0..183 all 0; row 191 lit.
- `test_terminal_must_fit`: 80x24 on 400x192 and on 512x184 raise `ValueError`.
- `test_glyph_lands_in_centered_cell`, `test_bold_is_full_phosphor_and_reverse_inverts`: the draft's asserts, with
  "the rest is black" limited to rows 0..183.
- `test_strip_is_reverse_video_on_the_last_row`: rows 184..191 lit where the strip is blank; an `A` inverts the
  glyph's mask; text past 80 columns is cut, never wrapped.
- `test_program_rows_never_reach_the_strip`: a 24-line screen full of `A` in normal mode: rows 184..191 equal the
  strip-only frame's.
- `test_full_screen_draws_the_programs_last_row_when_the_strip_is_hidden`: `Screen(80, 24)`, `full_screen=True`:
  with `strip_visible=False` rows 184..191 show the program's `A`s; with True the strip covers them.
- `test_cursor_inverts_cell_and_clamps_at_column_80`: `"A" * 80` leaves `cursor.x == 80`; column 79 inverted.
  `test_cursor_under_the_strip_is_not_drawn` (full screen, row 23, strip visible); `test_hidden_cursor_not_drawn`.
- `test_non_latin1_char_renders_as_question_mark`: `"█é"`: cell 0 is the `?` mask, cell 1 the `é` mask (a module
  font with `?` and `é` drawn); the same in the strip. `test_wide_character_does_not_raise` (a CJK character).
- `test_unchanged_screen_returns_the_cached_frame` (same object, read-only); `test_dirty_screen_or_new_strip_or_
  cursor_blink_redraws`; `test_draw_text` (draft); `test_draw_text_clips_at_every_edge` (x -3, the right, y past).
- `test_glow_spreads_light` (the draft's); `test_glow_does_not_wrap_around_edges`: a lit pixel at (0, 0) leaves
  column w-1 and row h-1 black.
- `test_render_is_fast` (perf): median `thread_time` of 50 renders of a changed full 80x23 screen under 5 ms on this
  Mac (a scratch reading of the draft: 1.7 ms).

## T4 (opus): the terminal
Files: `show/terminal.py`, `tests/test_terminal.py`. Draft: core plan lines 763 to 981. Changes (amendment Task 4,
spec 4.6): the pump is bounded by bytes and time, reading at most `READ_CHUNK` at a time so the clock is checked
often; `reset(rows=None)` calls `screen.resize` before `set_mode(LNM)`; `run()` closes both pty fds when `Popen`
raises; `kill()` always calls `os.killpg` under `try/except ProcessLookupError`, also after the shell has exited
(its orphans); `finished_or_orphaned`.
```
READ_CHUNK = 1024
class Terminal:
    def __init__(self, columns: int = 80, rows: int = 23)
    columns: int; rows: int                      # the geometry reset() restores and run() gives the child
    screen: pyte.Screen                          # LNM set: a fed "\n" is CR LF
    listeners: list[Callable[[bytes], None]]     # called with every chunk fed (the cast writer listens)
    def feed(self, data: bytes) -> None
    def reset(self, rows: int | None = None) -> None
        # rows given: it becomes self.rows (23, or 24 for full_screen). screen.reset(); screen.resize(rows, columns);
        # set_mode(LNM). Undoes ESC[?3h (pyte goes to 132 columns and screen.reset() keeps them).
    def run(self, cmd: list[str], cwd: Path, env: dict | None = None, preexec=None) -> None
        # RuntimeError while running; start_new_session; TIOCSWINSZ, TERM=xterm, COLUMNS, LINES from the geometry
    def pump(self, max_bytes: int = 4096, budget_ms: float = 8.0) -> int
        # bytes fed; stops at max_bytes, at budget_ms since the call, when nothing is ready, or at EOF or EIO
    running: bool; finished: bool; returncode: int | None   # finished = exited and pty EOF seen
    def finished_or_orphaned(self, grace: float = 0.5) -> bool
        # finished; or exited and no EOF within grace s of the exit first being seen: then kill() and True
    def kill(self) -> None                       # SIGKILL to the process group, wait, a last pump, close the fd
```
Acceptance tests (a `term` fixture yields `Terminal()` and kills it; children are `sh -c`; `WAIT = 2.0` s at most):
- `test_feed_updates_screen_with_lnm`, `test_listeners_receive_bytes`, `test_reset_clears_and_keeps_lnm`,
  `test_run_captures_child_output_and_exit_code`, `test_kill_stops_running_child`,
  `test_run_while_running_is_an_error`: the draft's. `test_default_geometry_is_80x23`.
- `test_child_sees_window_size`: `stty size` prints `23 80`. `test_reset_restores_geometry_after_132_columns`:
  `ESC[?3h` then `reset()`: 80x23. `test_reset_to_24_rows_for_full_screen`: 80x24; a child's `stty size` is `24 80`.
- `test_default_pump_is_bounded_by_bytes_and_time`: a flood (`yes xxxxxxxx`), after 0.2 s: each of 10 successive
  default pumps returns at most 4096 bytes; their median wall time is under 20 ms (the amendment's bound).
- `test_pump_honours_a_small_budget`: `pump(max_bytes=10**7, budget_ms=2.0)` on the flood returns in under 20 ms.
- `test_run_closes_both_fds_when_popen_raises`: `run(["/nonexistent/prog"], ...)` raises `FileNotFoundError`;
  `len(os.listdir("/dev/fd"))` is the same before and after; `running` is False.
- `test_kill_takes_the_process_group`: `sleep 30 & echo $!; wait`: the pid read from the screen; after `kill()`,
  `os.kill(pid, 0)` raises `ProcessLookupError` within `WAIT`.
- `test_background_child_counts_as_finished_after_grace`: `sleep 30 & exit 0`: `finished` stays False (the sleep
  holds the pty); `finished_or_orphaned(0.3)` is False when the exit is first seen, True 0.3 s later; the sleep is dead.
- `test_finished_or_orphaned_is_true_for_a_clean_exit`: `true`: True without waiting for the grace.

## T6 (sonnet): entries
Files: `show/entries.py`, `tests/show_helpers.py`, `tests/test_entries.py`. Draft: core plan lines 1157 to 1385.
Not in D1: `entries/hello` (roadmap D2, `station = 6` by amendment Task 19) and the draft's tests on it. Changes:
the plaque carries the year (spec 3.5 revision 2; the core plan's Global Constraints are older); `full_screen`
(amendment Task 19, spec 4.4); the station is a TOML integer of at least 1 (bool, float, string rejected; 6 and up
allowed); `run_seconds` and `build_seconds` over 0; `rescan` (spec 4.2, 4.6's 30 s rescan).
```
REQUIRED = ("title", "author", "year", "station", "source", "build", "run")
class EntryError(Exception)
@dataclass(frozen=True)
class Entry:
    slug: str; dir: Path; title: str; author: str; year: int; station: int; source: Path; build: str; run: str
    build_seconds: float = 60.0; run_seconds: float = 20.0; fallback: Path | None = None; full_screen: bool = False
    plaque: str          # property: f"Created by {author}, {year}, Not A.I."
    fallback_path: Path  # property: dir / "fallback.cast"
def load_entry(dir: Path) -> Entry                  # EntryError on any fault in the directory or its TOML
def load_entries(root: Path) -> dict[int, Entry]    # by station; bad dirs and duplicate stations skipped, logged
                                                    # "skipping"; EntryError when none, or root is missing
def rescan(root: Path, current: dict[int, Entry]) -> dict[int, Entry]   # load_entries, else current; never raises
```
`tests/show_helpers.py`: `HELLO_C` and `write_entry(root, slug, station, source, *, build="cc -o prog prog.c",
run="./prog", run_seconds=5.0, build_seconds=30.0, fallback=None, full_screen: bool | None = None, year=2026) -> Path`
(the draft's plus two keywords; `full_screen` written only when given). D2's pipeline tests reuse it.
Acceptance tests (all under `tmp_path`):
- `test_entry_loads_with_its_plaque`: `"Created by Test Author, 2026, Not A.I."`, the source path, fallback None.
- `test_fallback_detected_when_present`, `test_missing_toml_is_an_error`, `test_missing_source_is_an_error`,
  `test_load_entries_skips_bad_and_duplicate_stations`, `test_no_entries_raises`: the draft's.
- `test_bad_toml_is_an_error`; `test_missing_key_is_an_error` (each of REQUIRED in turn);
  `test_station_must_be_an_integer_of_at_least_one`: 0, -1, `true`, `1.5`, `"2"` raise; 6 loads.
- `test_full_screen_defaults_false_and_reads_true`; `test_full_screen_must_be_a_bool`; `test_missing_root_raises_
  entry_error`; `test_entries_are_hashable_and_equal_by_value`; `test_rescan_picks_up_a_new_entry`;
  `test_rescan_keeps_current_when_the_directory_is_empty_or_gone`.

## T9 (opus): the sandbox
Files: `show/sandbox.py`, `tests/test_sandbox.py`. Draft: core plan lines 1648 to 1743. Changes (amendment Task 9,
spec 4.3): `wrap` and the cached `unshare -rn` probe; the draft's test runs `python3`: use `sys.executable`.
`RLIMIT_AS` stays Linux only (macOS refuses it).
```
MAX_OUTPUT_FILE = 64 * 1024 * 1024; DEFAULT_MEMORY = 256 * 1024 * 1024; PROBE_TIMEOUT = 2.0
def limits(cpu_seconds: float, memory_bytes: int = DEFAULT_MEMORY) -> Callable[[], None]
    # preexec_fn: RLIMIT_CPU ceil, at least 1 (hard +1); RLIMIT_CORE 0; RLIMIT_FSIZE MAX_OUTPUT_FILE; RLIMIT_AS on Linux
@functools.cache
def unshare_works() -> bool     # which("unshare") and `unshare -rn true` exits 0 in PROBE_TIMEOUT; else False (warns)
def wrap(command: str) -> list[str]   # ["unshare", "-rn", "sh", "-c", command] if unshare_works(), else no unshare
```
Acceptance tests (probe tests call `unshare_works.cache_clear()` before and after):
- `test_cpu_limit_kills_busy_loop` (about 1 s, returncode below 0), `test_limited_process_can_still_run_normally`,
  `test_fractional_cpu_rounds_up_to_one_second`: the draft's, the child being `sys.executable`.
- `test_core_and_file_size_limits_are_set` (the child reads 0 and 64 MiB); `test_address_space_is_limited_on_linux_
  only` (256 MiB on Linux, the parent's value elsewhere).
- `test_probe_is_false_without_unshare` (`shutil.which` patched to None: no subprocess, a warning); `test_probe_is_
  cached` (`subprocess.run` counted: once for two calls); `test_wrap_uses_unshare_only_when_the_probe_passes`.
- `test_sandboxed_run_cannot_reach_the_hosts_loopback`: `skipif(not unshare_works(), reason="needs a working
  unshare -rn (Linux with unprivileged user namespaces); macOS has no unshare")`. The test listens on 127.0.0.1;
  the wrapped client exits non-zero, the unwrapped one connects. The only new skip: on the Mac (+1, journaled once);
  it runs on the Omarchy box and the Pi at GATE C.

## T7 (sonnet): the queue
Files: `show/queue.py`, `tests/test_queue.py`. Draft: core plan lines 1388 to 1484. Changes: `position` (spec 4.2's
per-station position, for D3's "QUEUED #3") and iteration (D3's lights pulse the queued stations).
```
class EntryQueue:
    def push(self, entry: Entry) -> bool      # False when already queued
    def pop(self) -> Entry | None; def peek(self) -> Entry | None; def clear(self) -> None
    def position(self, entry: Entry) -> int | None      # 1 for the next to play; None when not queued
    def __len__(self) -> int; def __contains__(self, entry: object) -> bool; def __iter__(self) -> Iterator[Entry]
```
Acceptance tests (entries from `tests.show_helpers.write_entry` under `tmp_path`): `test_fifo_and_dedupe`,
`test_clear` (the draft's); `test_position_is_one_based_and_moves_up_on_pop`; `test_iteration_is_in_play_order`;
`test_equal_entries_loaded_twice_are_deduped` (two `load_entry` of one directory).

## T8 (sonnet): recording
Files: `show/recording.py`, `tests/test_recording.py`. Draft: core plan lines 1487 to 1645. Changes: an incremental
UTF-8 decoder in the writer (the draft decodes each chunk alone: a character split across two pty reads becomes two
U+FFFD); the player clamps negative gaps to 0, skips blank lines, raises `CastError` on a file it cannot read (D2
treats that as no fallback), and exposes the header's geometry.
```
class CastError(ValueError)
class CastWriter:
    def __init__(self, path: Path, columns: int, rows: int, clock: Callable[[], float] = time.monotonic)
    path: Path
    def write(self, data: bytes) -> None       # [t, "o", text], t from the writer's start, rounded to 4 places
    def close(self) -> None                    # idempotent; also a context manager
class CastPlayer:
    def __init__(self, path: Path, max_gap: float = 2.0)    # CastError on a bad header or event line
    columns: int; rows: int                    # from the header
    def start(self, now: float) -> None; def tick(self, now: float) -> bytes
    done: bool; duration: float
```
Acceptance tests: `test_writer_produces_v2_cast`, `test_player_replays_with_timing_and_gap_compression`,
`test_empty_cast_is_done_immediately` (the draft's, height 23); `test_a_character_split_across_writes_survives`
(`"é".encode()` in two writes reads back `é`); `test_round_trip_through_writer_and_player`; `test_malformed_cast_
raises_cast_error` (not JSON, no header, an event not a list); `test_player_exposes_the_header_geometry`.

## T-shot (sonnet): `tools/show_shot.py`, the operator's sheets
Files: `tools/show_shot.py`, `tests/test_show_shot.py`. Group 2, on T3's `Renderer` and T4's `Terminal` as merged.
Reuses, never copies: `arcade.look.render` (plain, led, distance), `tools.arcade_shot.git_sha`, `save_png` (the sha
in the PNG text chunk `git`), `fit_width` and the sheet constants. PNGs are saved only from `tools/`.
```
SCRIPTS: dict[str, Callable[[], list[Step]]]   # "strip", "edges", "fullscreen", "cc"
@dataclass(frozen=True)
class Step:
    label: str; data: bytes = b""; strip: str = ATTRACT_STRIP; full_screen: bool = False
    strip_visible: bool = True; cursor_on: bool = True
ATTRACT_STRIP = "PRESS A BUTTON ON ANY PORTRAIT"
PLAY_STRIP = "NOW: hello by Trey, 2026, Not A.I. | NEXT: -"       # a sample until D3's strip() (Q52)
SHOW_MAX_WIDTH = 2080                                             # one 512 px frame at the led look's scale 4
def frames_from_steps(steps: list[Step], cfg: Config, font: Font) -> list[tuple[str, np.ndarray]]
def frames_from_command(command: str, cfg: Config, font: Font, seconds: float, every_ms: int,
                        cwd: Path) -> list[tuple[str, np.ndarray]]
    # a real child in Terminal(cfg.columns, cfg.rows - 1), pumped at cfg.fps with (cfg.pump_bytes, cfg.pump_ms),
    # a frame kept every every_ms, the child killed at the end
def sheet(frames, look: str, scale: int, title: str, gamma: float, cols: int) -> Image.Image
def main(argv: list[str] | None = None) -> int
    # --script | --command, --seconds 3, --every-ms 500, --look plain|led|both (plus OUT-distance.png at 10 m, the
    # middle of spec 1's 15 to 40 feet), --gamma 2.2, --crop X,Y,W,H (a window of the wall), --cwd, --allow-black,
    # --out. Title: sha, clean/dirty, script or command, look, gamma, crop. Exit 1 and no PNG when every frame's
    # program rows (all but the strip) are black, unless --allow-black. A command runs in a TemporaryDirectory.
```
Scripts: `strip` (the attract strip, then the play strip over scrolling source); `edges` (80 `A`s leaving the cursor
at column 80, `█` and CJK as `?`, bold and reverse, the cursor hidden); `fullscreen` (a 24-row screen, the strip
hidden, then shown); `cc` (a small C file with one `-Wall` warning in a temp dir: `cat`, `cc -Wall`, run; needs `cc`).
Acceptance tests (outputs under `tmp_path`):
- `test_script_writes_stamped_plain_led_and_distance_sheets`: three PNGs, each with text `git` == `git_sha()`.
- `test_every_frame_has_the_strip_lit`; `test_fullscreen_script_hides_and_shows_the_strip`; `test_black_session_
  is_refused`: `--command true` exits 1 and writes no PNG; with `--allow-black` it writes them.
- `test_command_output_reaches_the_frames`: `printf hello`: a frame's program rows are lit; no child is left.
- `test_crop_gives_the_prototype_window`: `--crop 0,0,128,64`: the plain sheet's cells are 128x64 times the scale.
- `test_cc_script_compiles_and_runs` (skipif no `cc`): the last frame's screen holds the warning and the output.

## I1 (orchestrator): merges and the report
Merge in the order of Lanes, the suite after each; no shared file is edited in this iteration. Report the collected
count (about 762 + 75), the skips (1 on the Mac: the loopback test, its reason), the suite time against 192 s, each
task's seconds, and the printed readings of `test_render_is_fast` and the two pump tests.

## I2 (the operator, in verify, after the review): evidence, from the repo root, the tree clean
```
.venv/bin/python -m tools.show_shot --script strip --look both --out <scratch>/it10-strip
.venv/bin/python -m tools.show_shot --script edges --look both --out <scratch>/it10-edges
.venv/bin/python -m tools.show_shot --script fullscreen --look both --out <scratch>/it10-fullscreen
.venv/bin/python -m tools.show_shot --script cc --look both --out <scratch>/it10-cc
.venv/bin/python -m tools.show_shot --command "seq 1 60" --seconds 2 --every-ms 250 --look both --out <scratch>/it10-seq
.venv/bin/python -m tools.show_shot --script strip --crop 0,0,128,64 --look led --out <scratch>/it10-prototype
```
Copied into `evidence/it10/` with collect.txt, pytest.txt, head.txt. The sheets must show: the strip in reverse on
row 24 of every normal frame, legible at the led look; no program text on row 24; the block cursor, on the last
cell after 80 `A`s; `?` for `█` and CJK; a full-screen entry's row 24 while the strip is hidden; a real `cc -Wall`
warning and the program's output; `seq` scrolling within 23 rows; the crop showing 21 columns by 8 rows.

## Decisions
- Left out: `entries/hello`, pipeline, attract, input, lights, audio (D2); `strip()`, the loop's use of the render
  cache, the cursor's blink rate, the flash governor on the show's frames (D3, Q50); a 128x64 mode (Q53).
- `cfg.rows` counts the strip: terminal `rows - 1`, renderer `rows`; `Config` and `show.toml` do not change.
- A `full_screen` entry gets 24 rows through `Terminal.reset(24)`; the renderer overlays the strip on demand
  (`strip_visible`; D3's state machine flashes it 2 s in 10).
- The renderer cuts the strip at 80 columns (fitting it is D3's `strip()`) and holds the dirty-only cache (spec 4.2).
- The pump reads 1024-byte chunks so `budget_ms` binds on the Pi: pyte feeds 4096 bytes in about 3 ms on this Mac
  (scratch reading), likely over 8 ms on a Pi 4.
- The plaque carries the year (spec 3.5 revision 2 over the core plan's older text). `rescan` never raises.
- The LED sheets use gamma 2.2 (an uncorrected wall) until the owner's hardware notes give the card's gamma.

## Owner questions (defaulted)
- Q51 How do the rows split on the Reduced tier (512x128)? Default: `rows = 16`, 80x15 for programs plus the strip,
  as spec 3.1's table says; nothing in D1 changes; the owner sets `height` and `rows` in show.toml.
- Q52 What does the strip show before D3, and does it carry the year? Default: the renderer draws the text it is
  given; the sheets use spec 4.4's strings with the year added (`NOW: <title> by <author>, <year>, Not A.I. |
  NEXT: ...`), matching the plaque (spec 3.5: "the year is the proof"); D3's `strip()` builds it.
- Q53 Which wall do the LED sheets show, and what can the 128x64 prototype show? Default: the sheets render the full
  512x192 wall (128x64 cannot hold 80 columns of 6 px). The prototype shows a 128x64 window, 21 columns by 8 rows,
  in the sheets by `--crop` and on the panels by D4's test pattern; no scaled-down terminal mode is built.
