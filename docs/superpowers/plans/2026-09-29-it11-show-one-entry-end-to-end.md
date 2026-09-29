# Iteration 11: the show daemon plays one entry end to end (D2)
BASE: HEAD at the spawn, after I0 commits this plan on c28c027 (the ink view). Roadmap D2 (Q33, Q49). Carried: C48.
"Core plan" = `docs/superpowers/plans/2026-09-22-show-daemon.md` (a draft to test, never to paste); its Amendments
(lines 13 to 71) override its tasks. "Spec" = `docs/superpowers/specs/2026-09-22-code-is-art-design.md` rev. 2, over
both. "Note N" = point N of the roadmap note "it10 (D2, pipeline)". SAFETY SLICE: no. flash.py, brightness.py,
colorlight.py, the runner's order untouched; D2 pushes no frame to a display (the show's flash governor is D3's, Q50).

## Global Constraints
- Test command, from the checkout's (or worktree's) root: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
  /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs`. At c28c027: 901 collected, 900 passed, 1 skipped,
  169.4 s (the ink branch's own run 175.9 s).
- Suite time: at most 212 s, from 176 s (the slower run): T-pipe 15 s (terminal 3), T-attract 1, T-io 1, T-hello 4,
  T-shot 7, about 204 s, and 8 s of spread (168 to 178 s since it10). D2 runs real compilers and children in real
  time (spec 2), hello's 3 s of motion included. Report what yours added (`--durations=0` on your modules).
- Test-first (superpowers:test-driven-development); only your files; never `cd` (in a worktree, plain git from its
  root, one command a call); no stash, push or command over 10 min; suite green; other findings in your final message.
- Tests leave nothing behind: files only under `tmp_path` (an entry a test builds is copied there first); every child
  killed in teardown (a yielding fixture, then `kill()` or `stop()`), its group too; `pgrep` in your report. `skipif(
  shutil.which("cc") is None)` on compiles. Named timeouts; a child's test about 2 s at most (hello's run about 3 s).
- No test opens a sound device or needs a Pi: GPIO through a fake `gpiozero` (`monkeypatch.setitem(sys.modules,
  ...)`; it is not installed on the Mac), audio through a fake mixer passed in; WAV files only under `tmp_path`.
- Timing asserts use `time.monotonic` and print their readings. A missed bound is never loosened: commit what passes,
  save the failing test in your scratchpad, report the numbers, go on; the orchestrator takes no rulings meanwhile.
- Shared files (`pyproject.toml`, `tests/conftest.py`, `.gitignore`, `show.toml`, `show/config.py`, `tests/test_
  config.py`) are the orchestrator's (I0). `fast_cfg` keeps `min_build_seconds` 1.5: tests that do not time the build
  use `dataclasses.replace(fast_cfg, min_build_seconds=0.0)`. `from tests.show_helpers import HELLO_C, write_entry`.

## Lanes
- I0 (orchestrator, main checkout, first): the config edit below, the suite, a commit with the plan; that is BASE.
- GROUP 1, one message, `isolation: "worktree"`: T-pipe (opus), T-attract (sonnet), T-io (sonnet), T-hello
  (sonnet). None imports what another builds. Merge T-pipe, T-hello, T-attract, T-io, the suite after each.
- GROUP 2, a worktree from the merged HEAD: T-shot (sonnet), on `EntryPlayer`, `Attract`, hello. Merge, suite; I1.
- C48 is not a serial task: the pipeline is the first caller of `run`, `kill`, `finished_or_orphaned` (T-attract
  uses `reset`, `feed`); T-pipe commits the terminal first. A serial lane costs a suite and a spawn for ~30 lines.

## I0 (orchestrator): `lightbox_pins`, the one config key D2 needs
Amendment Task 13 drives the lightbox (12 V, MOSFET) as well as the ring; `Config` has only `light_pins` (rings).
Edited on the merged files (c28c027: `view` after `glow`). `show.poc.toml` gets no key; it takes the defaults.
- `show/config.py`, after `light_pins`: `lightbox_pins: list[int] = field(default_factory=lambda: [17, 22, 23, 24, 27])`
- `show.toml`, after `light_pins` (comment `# button rings`): `lightbox_pins = [17, 22, 23, 24, 27]  # lightboxes (Q55)`
- `tests/test_config.py::test_defaults_when_file_missing` gains `assert cfg.lightbox_pins == [17, 22, 23, 24, 27]`;
  `test_repo_show_toml_matches_defaults` holds the two files together. No pin is shared, I2C, SPI or UART.

## T-pipe (opus): C48, the drain, and the entry pipeline
Files: `show/terminal.py`, `tests/test_terminal.py`, `show/pipeline.py`, `tests/test_pipeline.py`. Terminal first.

### The terminal (C48 and note 2)
C48: the terminal keeps the current run's group, forgotten when `killpg` raises `ProcessLookupError`, after a SIGKILL
sent once the leader is reaped (every member got it; none can join), and at the end of `kill()`; a forgotten group is
never signalled; `run()` no longer signals the previous group; EPERM (macOS, leader not yet reaped) keeps it. Note 2:
the grace runs from the later of the exit's first sighting and the last byte read; data still arriving keeps the run
open up to `drain_max` after the exit, then `kill()`. The caller pumps at the frame bound (spec 4.6, 4 KB or 8 ms).
```
DRAIN_MAX = 2.0   # seconds after the exit that a pty still delivering data is drained before the kill
_pgid: int | None # the current run's process group; None before a run and once forgotten
def finished_or_orphaned(self, grace: float = 0.5, drain_max: float = DRAIN_MAX) -> bool
    # finished (EOF and exit): the group signalled once, True. Exited and nothing read for grace s since the later
    # of the exit's first sighting and the last read, or drain_max s since that sighting: kill(), True.
```
Acceptance tests (added; every existing test in `tests/test_terminal.py` stays as it is and passes):
- `test_a_finished_group_is_signalled_once`: `os.killpg` counted; `true` run to True, three more calls and a
  `kill()`: one SIGKILL to it. `test_run_does_not_signal_the_previous_group`: a second `run()` names not the first.
  `test_a_group_that_is_gone_is_forgotten`: `ProcessLookupError` once, no later call.
- `test_output_after_the_exit_is_drained_before_the_kill`: a session leader (the `ORPHAN_LEADER` pattern) leaves a
  writer printing a line every 0.1 s for 0.8 s, then `END`; grace 0.3: `END` is on the screen before True.
- `test_a_writing_orphan_is_killed_at_drain_max`: a writer that never stops, `drain_max=1.0`: True between 1.0 s
  and 1.0 + `WAIT` after the exit (printed); the writer is gone.

### The pipeline (core Task 10, lines 1746 to 2075)
Changes against the draft: `signal_of` only for `rc < 0`; `exec ` before a run command with no shell operator
(amendment; a crash reads as a signal under dash, bash or `unshare`); the run through `sandbox.wrap` with `limits`
(spec 4.3 step 4); the build as `sh -c <build>` with `limits` and `LC_ALL=C` (note 4); BUILD lasts at least
`min_build_seconds`, success or failure; the run's timeout per the amendment; crowd mode (spec 4.5) read every tick;
rows from `entry.full_screen` (it10); `pump(cfg.pump_bytes, cfg.pump_ms)`, each build and run ended through
`finished_or_orphaned()` (note 2); an exception while feeding or pumping kills the child, fails the entry with
`terminal error (<ExceptionName>)`, then the fallback or the end (note 1); a `CastError` fallback counts as none
(logged); an exception in the fallback ends the entry; the fallback is cut at the run's timeout; the capture writes
`fallback.cast.part`, `os.replace`d onto `fallback.cast` only after a clean run (an exit or a timeout), else deleted
(note 3). Note 6: nothing is built for `ESC#8` or `ESC[2J` floods beyond the pump's budget; curation rejects them.
```
class Phase(str, Enum):  SOURCE, BUILD, RUN, ERROR_HOLD, FALLBACK, DWELL, DONE    # values "source", "build", ...
BUILD_MEMORY = 512 * 1024 * 1024; RUN_MEMORY = sandbox.DEFAULT_MEMORY
CPU_MARGIN = 5.0             # CPU seconds over a phase's wall-clock timeout, so the timeout ends it first
CROWD_SPEEDUP = 4            # spec 4.5: the source types at 4x in crowd mode
BUILD_ENV = {"LC_ALL": "C"}; CAPTURE_TEMP = "fallback.cast.part"
def signal_of(returncode: int) -> int | None      # -returncode when below 0, else None
def run_command(run: str) -> str   # "exec " + run, unless run holds a shell operator, quote, glob, $, = or newline
class EntryPlayer:
    def __init__(self, entry: Entry, term: Terminal, cfg: Config, clock: Callable[[], float] = time.monotonic)
    phase: Phase
    failure: str | None   # "build failed (exit N)", "build timed out", "crashed (signal N)", "terminal error (X)"
    crowd: bool           # read every tick: typewriter x4, the run capped at crowd_run_seconds, no dwell
    done: bool            # property: phase is DONE
    def start(self, now: float, crowd: bool = False) -> None
        # term.reset(cfg.rows if entry.full_screen else cfg.rows - 1); feeds "<title>\n<plaque>\n\n$ cat <source>\n"
    def tick(self, now: float) -> list[str]     # never raises; events "cue:compile", "cue:run", "cue:error"
    def stop(self) -> None                      # kills the child, drops a capture in progress, DONE
    def run_timeout(self) -> float  # min(entry.run_seconds, crowd_run_seconds if crowd else idle_run_seconds)
```
Flow (spec 4.3): SOURCE types the source (CRLF as LF), then feeds `$ <build>`, starts it, `cue:compile`. BUILD: at
its end and at least `min_build_seconds` in, exit 0 starts the run (`$ <run>`, `cue:run`), else failure; past
`build_seconds`: kill, failure. RUN: at its end a signal is a failure, any exit code normal; past `run_timeout()`:
kill, normal. A failure feeds `\n*** <reason> ***\n`, `cue:error`, holds `error_hold`, then FALLBACK (`term.reset`
to the entry's rows, `$ <run>   (recording)`, the cast) if there is one, else DWELL; DWELL holds `dwell`, then DONE.
Acceptance tests (`write_entry` under `tmp_path`; a `drive` helper ticks every 5 ms to DONE or a named deadline; a
fixture stops every player in teardown):
- `test_happy_path_compiles_and_runs`: title, `Created by Test Author, 2026, Not A.I.`, `$ cat prog.c`, the source,
  `$ cc -o prog prog.c`, `hello, world` on the screen; compile then run cues, no error; phases SOURCE to DONE in order.
- `test_build_runs_with_lc_all_c`: build `echo LC=$LC_ALL && cc -o prog prog.c`: `LC=C` on the screen.
- `test_build_shows_for_at_least_min_build_seconds`: 0.5 s: RUN no sooner than 0.5 s after BUILD (printed); a
  failing build too holds 0.5 s before ERROR_HOLD.
- `test_build_failure_without_fallback_holds_then_finishes`: `int main( {`: `*** build failed` on the screen,
  `cue:error`, DWELL, DONE. `test_build_timeout_is_a_failure`: `sleep 30`, 0.5 s: `build timed out`, sleep gone.
- `test_crash_with_fallback_replays_recording`: a null dereference: `crashed (signal`; after the hold, `(recording)`
  and `recorded output`. `test_nonzero_exit_is_not_a_crash`: `return 1;` and `return 200;`: failure None.
- `test_run_command_prepends_exec_only_for_a_plain_command`: `./prog`, `./prog 30` gain it; `./prog | head`,
  `./prog > out`, `FOO=1 ./prog`, `./prog; echo` do not.
- `test_run_goes_through_the_sandbox_and_the_build_does_not`: `show.pipeline.wrap` spied: once, `exec ./prog`.
- `test_run_timeout_is_a_normal_end`: a forever printer, `run_seconds` 1.0: failure None, child gone, RUN ends
  within a named slack (printed). `test_idle_run_is_capped_by_idle_run_seconds`: 30 s against 0.5 s.
- `test_crowd_mode_speeds_the_source_caps_the_run_and_skips_the_dwell`: 400 cps and a 400-byte source: SOURCE about
  0.25 s; `crowd_run_seconds` 0.5; `dwell` 5 skipped. `test_crowd_set_during_the_run_caps_it`: set 0.3 s into RUN.
- `test_a_pump_exception_ends_the_entry_and_plays_the_fallback`: prints `ESC[?3A`, sleeps 30: `terminal error
  (TypeError)`, child gone, the fallback shown; without a fallback, DWELL and DONE; `tick` never raised.
- `test_an_unreadable_fallback_counts_as_none`: fallback `not json`, a broken build: DONE, no exception, a log line.
- `test_capture_writes_fallback_only_on_a_clean_run`: during RUN only the `.part` exists; a clean run leaves
  `fallback.cast` with `hello, world` and no `.part`; a crash leaves neither, nor does `stop()`.
- `test_stop_kills_the_process_and_finishes`; `test_backgrounding_entry_leaves_no_process`: the program forks a
  SIGHUP-deaf child that prints its pid and sleeps 30, then exits 0: failure None, the child gone (spec 4.7).
- `test_flooding_entry_does_not_stall_the_ticks`: a `puts` loop, 1 s: median tick under 20 ms, max printed;
  `test_the_output_tail_reaches_the_final_screen`: lines 1 to 3000 then exit: `3000` on the DWELL screen.
- `test_full_screen_entry_gets_24_rows`: `stty size` prints `24 80` with `full_screen`, `23 80` without.

## T-attract (sonnet): attract mode (core Task 11, lines 2078 to 2184)
Files: `show/attract.py`, `tests/test_attract.py`. Changes: the banner every 40 source lines (amendment, spec 4.5);
`idle_seconds` for D3's autoplay; `start` resets to 23 rows (a full-screen entry left 24); the header uses the plaque
(with the year); an unreadable source is skipped, logged; no entries leave the banner; a late tick feeds a screen.
```
BANNER = b"CODE IS ART, A.I. IS NOT\nPress the button on any portrait to compile and run it.\n\n"
BANNER_EVERY = 40; MAX_LINES_PER_TICK = 23
class Attract:
    def __init__(self, entries: Iterable[Entry], term: Terminal, lines_per_second: float, rows: int = 23)
        # sources read here, in station order; "---- <title> -- <plaque> ----" between blank lines before each
    def start(self, now: float) -> None           # term.reset(rows), the banner; the idle clock starts
    def tick(self, now: float) -> None            # feeds the lines due; never raises
    def idle_seconds(self, now: float) -> float   # since start()
```
Acceptance tests (`write_entry` under `tmp_path`; a `Terminal()` fed only): `test_attract_scrolls_sources_in_station_
order` (the draft's, the plaque with its year); `test_attract_wraps_around`; `test_banner_returns_every_40_source_
lines` (a 100-line source: banners after lines 40 and 80, counted by a listener); `test_start_resets_a_24_row_
terminal_to_23`; `test_idle_seconds_counts_from_start`; `test_no_entries_shows_the_banner_and_ticks_without_error`;
`test_an_unreadable_source_is_skipped` (removed after loading: a log, the other still scrolls);
`test_a_late_tick_feeds_at_most_a_screen` (a 1000 s gap: at most 23 lines).

## T-io (sonnet): input, lights, audio, cues (core Task 13, lines 2478 to 2747)
Files: `show/input.py`, `show/lights.py`, `show/audio.py`, `tools/make_cues.py`, `audio/{keypress,compile,run,
error}.wav`, `tests/test_io.py`, `tests/test_make_cues.py`. Changes: lights drive lightbox and ring, with `flash`
and `all_off` (amendments Tasks 13, 14; spec 4.5's idle, playing and queued looks); `AudioCues` with volume and quiet
hours (an injected clock); the error cue a soft two-tone; GPIO and audio built in `try/except`, falling back to fakes
with a logged error; cues through `pygame.mixer` (a dependency already: no player child to reap, volume per sound),
not `aplay`/`afplay`. `audio/*.wav` made by `python -m tools.make_cues audio` from the worktree's root, committed.
```
class PressQueue: def put(self, station: int) -> None; def drain(self) -> list[int]      # thread-safe, in order
class ButtonInput: def __init__(self, pins: list[int], presses: PressQueue); def close(self) -> None
    # gpiozero Button(pin, pull_up=True, bounce_time=BOUNCE_S = 0.05); pins[0] is station 1
def make_buttons(pins: list[int], presses: PressQueue) -> ButtonInput | None   # None and a logged error on failure
MODES = ("off", "on", "bright", "pulse")          # per station
LIGHTBOX = {"off": 0.0, "on": 0.4, "bright": 1.0, "pulse": 0.4}   # Q55
SLOW_HZ = 0.5; FAST_HZ = 2.0   # ring: off 0, "on" pulses at SLOW_HZ (idle), "pulse" at FAST_HZ (queued), bright 1
FLASH_S = 0.3; FLASH_PERIOD = 0.1   # a press: the ring blinks full and dark, visible over any mode, then returns
def pulse_level(now: float, hz: float) -> float   # 0.5 + 0.5 sin(2 pi hz now)
def levels(mode: str, now: float, flash_start: float | None) -> tuple[float, float]    # (lightbox, ring)
class FakeLights:   # modes: dict[int, str]; levels: dict[int, tuple[float, float]] as of the last tick
    def set(self, station: int, mode: str) -> None      # ValueError for a mode not in MODES
    def flash(self, station: int, now: float) -> None; def all_off(self) -> None; def tick(self, now: float) -> None
class GpioLights(FakeLights): def __init__(self, ring_pins: list[int], lightbox_pins: list[int]); def close(self)
    # one gpiozero PWMLED per ring and per lightbox; tick writes the levels
def make_lights(ring_pins: list[int], lightbox_pins: list[int]) -> FakeLights   # GpioLights, else FakeLights, logged
CUES = ("keypress", "compile", "run", "error")
def parse_quiet_hours(spec: str) -> tuple[time, time] | None   # "02:00-08:00"; "" is None; ValueError if malformed
def in_quiet_hours(window: tuple[time, time] | None, t: time) -> bool   # may wrap midnight; the end excluded
class FakeAudio: played: list[str]; def play(self, cue: str) -> None
class AudioCues:
    def __init__(self, dir: Path, volume: float = 0.6, quiet_hours: str = "",
                 clock: Callable[[], datetime] = datetime.now, mixer=None)
        # mixer None: pygame.mixer, init in try/except (a failure logs and mutes); loads dir/<cue>.wav; a bad
        # quiet_hours logs and means none; volume clamped to 0..1 and set on each sound
    def play(self, cue: str) -> None   # never raises; silent in quiet hours and for an unknown or missing cue
RATE = 22050; CUES: dict[str, np.ndarray]; def main(argv: list[str] | None = None) -> int   # tools/make_cues.py
```
Acceptance tests (`tests/test_io.py`): `test_press_queue_drains_in_order`; `test_press_queue_is_thread_safe` (4x1000
puts, 4000 drained); `test_buttons_map_pins_to_stations` (pin index 0 puts 1); `test_make_buttons_without_gpiozero_
is_none_and_logs`; `test_levels_follow_the_modes` (the tables; the rings move at their rates); `test_flash_blinks_
the_ring_for_0_3_s_then_returns` (over "bright" too); `test_all_off_darkens_everything`; `test_unknown_mode_is_an_
error`; `test_gpio_lights_write_both_outputs`; `test_make_lights_without_gpiozero_falls_back_and_logs`;
`test_quiet_hours_parse_and_wrap_midnight` (23:00-06:00 holds 23:30, 05:59, not 06:00, 12:00); `test_bad_quiet_
hours_log_and_mean_none`; `test_cues_are_muted_in_quiet_hours`; `test_volume_is_set_on_each_sound` (0.6; 1.7 as
1.0); `test_missing_or_unknown_cue_is_a_noop`; `test_mixer_failure_mutes_and_logs`; `test_play_never_raises`.
`tests/test_make_cues.py`: `test_make_cues_writes_four_wavs` (22050 Hz, 16-bit mono); `test_error_cue_is_a_soft_
two_tone` (two spectral peaks, falling; under 5 % of samples within 1 % of the peak, a square wave has nearly all;
peak at most half scale); `test_committed_cues_match_the_generator` (`audio/*.wav` equal a fresh run's bytes).

## T-hello (sonnet): the sample entry `entries/hello` (amendment Task 19; core lines 1168 to 1190, 3674)
Files: `entries/hello/hello.c`, `entries/hello/entry.toml`, `tests/test_entries.py` (tests added, none changed).
Decision: ONE `-Wall` warning on purpose, an unused variable, its line commented as such. Spec 1 and 4.3 ("Real
warnings are the point") put the compile in the show; `-Werror` makes the same warning a failed build (I2). `hello.c`:
no stdin, no raw modes; ASCII, `ESC[H`, `ESC[2J`, `ESC[?25l/h` only; reads `LINES`, `COLUMNS` (default 23, 80);
about 3 s of large motion (a band of `#` on every row, its column on a wave, at least 20 columns a second, about 20
frames a second by `usleep`); then clears, shows the cursor, prints `hello, world`, exits 0. No `-lm`.
`entry.toml`: title "hello", author "Trey", year 2026, station 6, source "hello.c", build "cc -Wall -o hello
hello.c", run "./hello", build_seconds 30, run_seconds 10.
Fallback: none committed (no portrait); T-shot's `--capture-first` makes one by the pipeline's own capture in a
temp copy, so none goes stale when `hello.c` changes. The five entries' casts are GATE C's.
Acceptance tests (build and run in a temp copy):
- `test_sample_entry_loads`: slug `hello`, station 6, plaque `Created by Trey, 2026, Not A.I.`, fallback None,
  `full_screen` False; the build holds `-Wall` and no `-w` word.
- `test_sample_entry_builds_with_one_warning` (skipif no cc): `LC_ALL=C`, exit 0, one `warning:` line, the variable.
- `test_sample_entry_runs_with_large_motion` (skipif no cc): `LINES=23 COLUMNS=80`, to a pipe: exit 0 within
  `run_seconds`, ends `hello, world`; split at `ESC[H`, 40 frames or more; the band moves 20 columns or more.

## T-shot (sonnet, group 2): the real pipeline in the operator's sheets
Files: `tools/show_shot.py`, `tests/test_show_shot.py` (no other task edits them). The `cc` script stays; the
pipeline's sheet replaces it in verify (note 5). New inputs, exclusive with `--script` and `--command`:
- `--entry DIR`: copies the entry into a `TemporaryDirectory` (no build product in the checkout), plays it through
  `EntryPlayer` on `Terminal(cfg.columns, cfg.rows - 1)` in real time at `cfg.fps`, rendered with its `full_screen`;
  a frame every `--every-ms`, at each phase change and at DONE, labelled `<phase> <t>s`; stops at DONE or
  `--seconds` (default 60 with `--entry`), `stop()` in a `finally`. Strip: `NOW: <title> by <author>, <year>, Not
  A.I. | NEXT: -` (Q52). Prints each phase change with its time, and the failure. `--capture-first` first plays the
  copy with its own build and `capture` on, keeping no frames; then `--build CMD` replaces the copy's build.
- `--attract DIR`: `Attract(load_entries(DIR).values(), ...)` at `cfg.attract_lps`, strip `ATTRACT_STRIP`.
- Both honour `--config` and render through the merged `_renderer(cfg, font)`: `Renderer(font, width, height,
  columns, rows, phosphor, glow=False, view="text")` given `cfg.glow`, `cfg.view`. The terminal is 80x23 in both views.
```
def play_strip(entry: Entry) -> str
def frames_from_entry(entry_dir: Path, cfg: Config, font: Font, seconds: float, every_ms: int,
                      build: str | None = None, capture_first: bool = False
                      ) -> tuple[list[tuple[str, np.ndarray]], list[tuple[str, float]], str | None]
    # the frames, the phases seen with their start times, the failure
def frames_from_attract(entries_dir: Path, cfg: Config, font: Font, seconds: float,
                        every_ms: int) -> list[tuple[str, np.ndarray]]
```
Acceptance tests (outputs under `tmp_path`; a fast `Config` for plays: dwell, error_hold, min_build 0.2 s, 5000 cps):
- `test_entry_mode_plays_the_sample_entry_through_the_pipeline` (skipif no cc): `entries/hello`: phases SOURCE,
  BUILD, RUN, DWELL, DONE in order; failure None; first and last frames differ; afterwards `git status --porcelain
  entries` is empty and no `entries/hello/hello` exists.
- `test_entry_mode_with_a_broken_build_replays_the_captured_fallback` (skipif no cc): a `write_entry` of `HELLO_C`,
  `build="false"`, `capture_first`: phases include ERROR_HOLD and FALLBACK; failure starts `build failed`.
- `test_attract_mode_scrolls`: two `write_entry` entries: frames differ over time; every one has the strip lit;
  with `Config(width=128, height=64, view="ink")` too, the frames 64x128 and lit above the strip's row.
- `test_entry_and_attract_modes_write_stamped_sheets`: `main` with `--attract`, and with `--entry` on a
  `write_entry` directory (skipif no cc): three PNGs each, `git` == `git_sha()`.

## I1 (orchestrator): merges and the report
I0, then the merges in Lanes' order, the suite after each. Report: collected (about 901 + 75); skips (1 on the Mac,
the loopback; none new with `cc`); the time against 212 s and each task's; the timing readings; `pgrep` at the end.

## I2 (the operator, in verify, after the review): evidence, from the repo root, the tree clean
```
.venv/bin/python -m tools.show_shot --entry entries/hello --every-ms 1500 --look both --out <scratch>/it11-hello
.venv/bin/python -m tools.show_shot --entry entries/hello --build "cc -Wall -Werror -o hello hello.c" \
    --capture-first --every-ms 1500 --look both --out <scratch>/it11-hello-fallback
.venv/bin/python -m tools.show_shot --attract entries --seconds 20 --every-ms 2500 --look both \
    --out <scratch>/it11-attract
.venv/bin/python -m tools.show_shot --config show.poc.toml --entry entries/hello --every-ms 1500 --look led \
    --out <scratch>/it11-hello-poc
```
Stdout (phase lines) to `show-shot.txt`; all into `evidence/it11/` with collect.txt, pytest.txt, head.txt. The first
three (text view): the strip in reverse on row 24. it11-hello: title, plaque, `$ cat hello.c` typing; `$ cc -Wall`
with the real `unused variable` warning, straight quotes, BUILD at least 1.5 s; `$ ./hello`, the band moving; the
dwell on `hello, world`. it11-hello-fallback: the warning as an error, `*** build failed (exit 1) ***`, the hold,
`$ ./hello   (recording)`, the replayed band. it11-attract: the banner, hello's header and source scrolling, the
banner again after 40 lines. it11-hello-poc (the pipeline on the 128x64 proof of concept, ink view): a cell a dot,
the source typing as texture, the band a moving stripe, no cursor; the strip in reverse on the bottom 8 px row, cut
to `NOW: hello by Trey, 2` (Q58, D3's). The `--crop 16,128,128,64` sheet is dropped: it showed the text view's 21x8
corner, which the proof of concept no longer uses. No network, camera, sound or Pi.

## Decisions
- Left out, D3: the state machine (presses, `notice`, `strip()`, autoplay on `idle_seconds`, setting `crowd`),
  `main` and its CLI, the loop's render cache, the error frame, the watchdog, `all_off()` after push failures,
  rescan, deploy files, the flash governor (Q50), Q54's strips, Q58 (the operator's: the 128x64 strip cuts "Not
  A.I."), `main`'s `Renderer` with `cfg.view` (D2's pipeline and attract feed a `Terminal` and build none; T-shot's
  are D2's only renderers). D4: the test pattern, the soak. GATE C: the five entries and casts; the Linux checks.
- Crowd mode is a flag read every tick (spec 4.5's queue state over the amendment's "at start"). A pty still
  delivering data after the exit is drained up to 2 s; a silent one is killed after the 0.5 s grace (spec 4.6).
- The build is not wrapped in `unshare` (spec 4.3 step 4 names the run); both carry `limits`. A missing `-Wall` is
  curation's to catch (GATE C); the pipeline runs the build line as written.

## Owner questions (defaulted)
- Q55 How are the lightboxes wired, and do they dim? Default: 12 V through a MOSFET on PWM pins [17, 22, 23, 24,
  27], 0.4 idle or queued, 1.0 while playing; rings on `light_pins`; show.toml changes when the boards are built.
- Q56 Does `entries/hello` play on the festival wall? Default: no; it stays for tests and demos (station 6, no
  portrait); D3's attract and autoplay leave out stations above 5 once a station 1 to 5 is loaded.
- Q57 What does the wall print around an entry (spec 4.3 names phases, not words)? Default: title, plaque, `$ cat
  <source>`, `$ <build>`, `$ <run>` as a shell transcript; `*** <reason> ***`; `$ <run>   (recording)` over a replay.
