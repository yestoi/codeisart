import dataclasses
import json
import logging
import os
import shutil
import statistics
import time
from dataclasses import dataclass, field
from typing import Callable

import pytest

import show.pipeline
from show.entries import load_entry
from show.pipeline import CAPTURE_TEMP, EntryPlayer, Phase, run_command, signal_of
from show.sandbox import wrap
from show.terminal import Terminal
from tests.show_helpers import HELLO_C, write_entry

needs_cc = pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler")

DRIVE_DEADLINE = 10.0   # seconds a player is given to reach the phase a test waits for
TICK = 0.005            # seconds between ticks, as the spec's 20 fps and faster
GONE_WAIT = 2.0         # seconds a killed child is given to be gone
MIN_BUILD = 0.5         # min_build_seconds of the build-time test
BUILD_TIMEOUT = 0.5     # build_seconds of the build timeout test
RUN_SECONDS = 1.0       # run_seconds of the run timeout and flood tests
CAP = 0.5               # idle_run_seconds / crowd_run_seconds of the cap tests
CROWD_AT = 0.3          # seconds into RUN that crowd mode is set
RUN_END_SLACK = 0.5     # seconds past its timeout a RUN may take to end (a tick, the kill of a flood)
CROWD_CPS = 400
SOURCE_BYTES = 400
SOURCE_SLACK = 0.1      # seconds past bytes / (cps x 4) the crowd's typing may take
DWELL_SKIP_BOUND = 0.1  # seconds from RUN's end to DONE in crowd mode, against a dwell of 5 s
FLOOD_TICK_MS = 20.0    # median tick of a flooding entry

CRASH_C = "int main(void){volatile int*p=0;return *p;}\n"
BROKEN_C = "int main( {\n"
FOREVER_C = '#include <stdio.h>\nint main(void){for(;;){puts("tick");fflush(stdout);}}\n'
SLOW_FOREVER_C = ('#include <stdio.h>\n#include <unistd.h>\n'
                  'int main(void){for(;;){puts("tick");fflush(stdout);usleep(10000);}}\n')
SLOW_HELLO_C = ('#include <stdio.h>\n#include <unistd.h>\n'
                'int main(void){usleep(400000);puts("hello, world");return 0;}\n')
ESCAPE_C = ('#include <stdio.h>\n#include <unistd.h>\n'
            'int main(void){printf("\\033[?3A");fflush(stdout);sleep(30);return 0;}\n')
BACKGROUND_C = ('#include <signal.h>\n#include <stdio.h>\n#include <unistd.h>\n'
                'int main(void){signal(SIGHUP,SIG_IGN);pid_t p=fork();\n'
                'if(p==0){execlp("sleep","sleep","30",(char*)0);_exit(1);}\n'
                'printf("%d\\n",(int)p);fflush(stdout);return 0;}\n')
COUNT_C = '#include <stdio.h>\nint main(void){for(int i=1;i<=3000;i++)printf("%d\\n",i);return 0;}\n'


def exit_c(code: int) -> str:
    return f"int main(void){{return {code};}}\n"


def cast(text: str) -> str:
    return json.dumps({"version": 2, "width": 80, "height": 23}) + "\n" + json.dumps([0.0, "o", text]) + "\n"


def screen_text(term: Terminal) -> str:
    return "\n".join(term.screen.display)


def screen_lines(term: Terminal) -> list[str]:
    return [line.strip() for line in term.screen.display]


def wait_gone(pid: int, seconds: float = GONE_WAIT) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(TICK)
    return False


@dataclass
class Play:
    events: list[str] = field(default_factory=list)
    phases: list[Phase] = field(default_factory=list)                 # each change, in order
    at: dict[Phase, float] = field(default_factory=dict)              # the tick a phase began
    screens: dict[Phase, str] = field(default_factory=dict)           # the screen as it began
    tick_ms: dict[Phase, list[float]] = field(default_factory=dict)   # tick durations by the phase ticked
    pids: dict[Phase, int] = field(default_factory=dict)              # the child's pid as BUILD, RUN began

    def seconds(self, a: Phase, b: Phase) -> float:
        return self.at[b] - self.at[a]


def record(player: EntryPlayer, play: Play, now: float) -> None:
    play.phases.append(player.phase)
    play.at[player.phase] = now
    play.screens[player.phase] = screen_text(player.term)
    if player.phase in (Phase.BUILD, Phase.RUN) and player.term.proc is not None:
        play.pids[player.phase] = player.term.proc.pid


def start(player: EntryPlayer, crowd: bool = False) -> Play:
    play = Play()
    now = time.monotonic()
    player.start(now, crowd=crowd)
    record(player, play, now)
    return play


def drive(player: EntryPlayer, play: Play, until: Phase = Phase.DONE, seconds: float = DRIVE_DEADLINE,
          each: Callable[[EntryPlayer, Play, float], None] | None = None) -> Play:
    """Tick every TICK s until the phase `until` or the deadline."""
    deadline = time.monotonic() + seconds
    while player.phase != until and time.monotonic() < deadline:
        now = time.monotonic()
        ticked = player.phase
        play.events += player.tick(now)
        play.tick_ms.setdefault(ticked, []).append((time.monotonic() - now) * 1000.0)
        if player.phase != play.phases[-1]:
            record(player, play, now)
        if each is not None:
            each(player, play, now)
        time.sleep(TICK)
    assert player.phase == until, f"stuck in {player.phase} after {seconds} s; phases {play.phases}"
    return play


def play_through(player: EntryPlayer, crowd: bool = False, **kwargs) -> Play:
    return drive(player, start(player, crowd), **kwargs)


@pytest.fixture
def cfg(fast_cfg):
    """No build minimum and no dwell: the tests that time them set their own."""
    return dataclasses.replace(fast_cfg, min_build_seconds=0.0, dwell=0.0)


@pytest.fixture
def make_player():
    players: list[EntryPlayer] = []

    def make(entry_dir, config) -> EntryPlayer:
        player = EntryPlayer(load_entry(entry_dir), Terminal(config.columns, config.rows - 1), config)
        players.append(player)
        return player

    yield make
    for player in players:
        player.stop()


P = Phase
HAPPY = [P.SOURCE, P.BUILD, P.RUN, P.DWELL, P.DONE]


@needs_cc
def test_happy_path_compiles_and_runs(tmp_path, cfg, make_player):
    player = make_player(write_entry(tmp_path, "greeting", 1, HELLO_C), cfg)
    play = play_through(player)
    assert play.phases == HAPPY
    assert play.events == ["cue:compile", "cue:run"]
    assert player.failure is None
    lines = screen_lines(player.term)
    print("\n".join(line for line in lines if line))
    assert lines[0] == "greeting"
    assert "Created by Test Author, 2026, Not A.I." in lines
    assert "$ cat prog.c" in lines
    assert "#include <stdio.h>" in lines
    assert 'int main(void){puts("hello, world");return 0;}' in lines
    assert "$ cc -o prog prog.c" in lines
    assert "$ ./prog" in lines
    assert "hello, world" in lines


@needs_cc
def test_build_runs_with_lc_all_c(tmp_path, cfg, make_player, monkeypatch):
    monkeypatch.setenv("LC_ALL", "en_US.UTF-8")
    player = make_player(write_entry(tmp_path, "locale", 1, HELLO_C,
                                     build="echo LC=$LC_ALL && cc -o prog prog.c"), cfg)
    play_through(player)
    assert player.failure is None
    assert "LC=C" in screen_lines(player.term)


@needs_cc
def test_build_shows_for_at_least_min_build_seconds(tmp_path, fast_cfg, make_player):
    slow = dataclasses.replace(fast_cfg, min_build_seconds=MIN_BUILD)
    good = play_through(make_player(write_entry(tmp_path, "good", 1, HELLO_C), slow))
    bad = play_through(make_player(write_entry(tmp_path, "bad", 2, BROKEN_C), slow))
    print(f"BUILD to RUN {good.seconds(P.BUILD, P.RUN):.3f} s; "
          f"BUILD to ERROR_HOLD {bad.seconds(P.BUILD, P.ERROR_HOLD):.3f} s; min {MIN_BUILD} s")
    assert good.seconds(P.BUILD, P.RUN) >= MIN_BUILD
    assert bad.seconds(P.BUILD, P.ERROR_HOLD) >= MIN_BUILD


@needs_cc
def test_build_failure_without_fallback_holds_then_finishes(tmp_path, cfg, make_player):
    player = make_player(write_entry(tmp_path, "broken", 1, BROKEN_C), cfg)
    play = play_through(player)
    assert play.phases == [P.SOURCE, P.BUILD, P.ERROR_HOLD, P.DWELL, P.DONE]
    assert play.events == ["cue:compile", "cue:error"]
    assert player.failure is not None and player.failure.startswith("build failed (exit ")
    print(player.failure)
    assert "*** build failed" in play.screens[P.DWELL]


def test_build_timeout_is_a_failure(tmp_path, cfg, make_player):
    player = make_player(write_entry(tmp_path, "slow", 1, HELLO_C, build="sleep 30 & echo $!; wait",
                                     build_seconds=BUILD_TIMEOUT), cfg)
    play = play_through(player)
    assert player.failure == "build timed out"
    assert "*** build timed out ***" in play.screens[P.ERROR_HOLD]
    sleeper = [line for line in play.screens[P.ERROR_HOLD].split("\n") if line.strip().isdigit()]
    assert len(sleeper) == 1
    assert wait_gone(int(sleeper[0]))
    print(f"BUILD to ERROR_HOLD {play.seconds(P.BUILD, P.ERROR_HOLD):.3f} s; timeout {BUILD_TIMEOUT} s")
    assert play.seconds(P.BUILD, P.ERROR_HOLD) >= BUILD_TIMEOUT


@needs_cc
def test_crash_with_fallback_replays_recording(tmp_path, cfg, make_player):
    player = make_player(write_entry(tmp_path, "crash", 1, CRASH_C, fallback=cast("recorded output\r\n")), cfg)
    play = play_through(player)
    assert play.phases == [P.SOURCE, P.BUILD, P.RUN, P.ERROR_HOLD, P.FALLBACK, P.DWELL, P.DONE]
    assert play.events == ["cue:compile", "cue:run", "cue:error"]
    print(player.failure)
    assert player.failure is not None and player.failure.startswith("crashed (signal ")
    assert "*** crashed (signal " in play.screens[P.ERROR_HOLD]
    lines = screen_lines(player.term)
    assert lines[0] == "$ ./prog   (recording)"
    assert "recorded output" in lines


@needs_cc
def test_nonzero_exit_is_not_a_crash(tmp_path, cfg, make_player):
    assert signal_of(200) is None and signal_of(1) is None and signal_of(0) is None
    assert signal_of(-11) == 11
    for station, code in enumerate((1, 200), start=1):
        player = make_player(write_entry(tmp_path, f"exit{code}", station, exit_c(code)), cfg)
        play = play_through(player)
        assert player.term.returncode == code
        assert player.failure is None
        assert play.phases == HAPPY and "cue:error" not in play.events


def test_run_command_prepends_exec_only_for_a_plain_command():
    assert run_command("./prog") == "exec ./prog"
    assert run_command("./prog 30") == "exec ./prog 30"
    for run in ("./prog | head", "./prog > out", "FOO=1 ./prog", "./prog; echo", "./prog && echo",
                "./prog 'a b'", "./prog *.c", "./prog $HOME", "./prog\necho"):
        assert run_command(run) == run, run


@needs_cc
def test_run_goes_through_the_sandbox_and_the_build_does_not(tmp_path, cfg, make_player, monkeypatch):
    calls: list[str] = []

    def spy(command: str) -> list[str]:
        calls.append(command)
        return wrap(command)

    monkeypatch.setattr(show.pipeline, "wrap", spy)
    player = make_player(write_entry(tmp_path, "boxed", 1, HELLO_C), cfg)
    play_through(player)
    assert player.failure is None
    assert calls == ["exec ./prog"]


@needs_cc
def test_run_timeout_is_a_normal_end(tmp_path, cfg, make_player):
    player = make_player(write_entry(tmp_path, "forever", 1, FOREVER_C, run_seconds=RUN_SECONDS), cfg)
    play = play_through(player)
    ran = play.seconds(P.RUN, P.DWELL)
    print(f"RUN of a forever printer: {ran:.3f} s against run_seconds {RUN_SECONDS} s, slack {RUN_END_SLACK} s")
    assert player.failure is None and play.phases == HAPPY
    assert not player.term.running
    assert wait_gone(play.pids[P.RUN])
    assert RUN_SECONDS <= ran <= RUN_SECONDS + RUN_END_SLACK


@needs_cc
def test_idle_run_is_capped_by_idle_run_seconds(tmp_path, cfg, make_player):
    capped = dataclasses.replace(cfg, idle_run_seconds=CAP)
    player = make_player(write_entry(tmp_path, "long", 1, SLOW_FOREVER_C, run_seconds=30.0), capped)
    assert player.run_timeout() == CAP
    play = play_through(player)
    ran = play.seconds(P.RUN, P.DWELL)
    print(f"RUN of 30 s capped at idle_run_seconds {CAP} s: {ran:.3f} s")
    assert player.failure is None
    assert CAP <= ran <= CAP + RUN_END_SLACK


def padded(source: str, size: int) -> str:
    pad = size - len(source) - len("/**/\n")
    return source + "/*" + "x" * pad + "*/\n"


@needs_cc
def test_crowd_mode_speeds_the_source_caps_the_run_and_skips_the_dwell(tmp_path, cfg, make_player):
    crowd_cfg = dataclasses.replace(cfg, typewriter_cps=CROWD_CPS, crowd_run_seconds=CAP, dwell=5.0)
    source = padded(SLOW_FOREVER_C, SOURCE_BYTES)
    assert len(source) == SOURCE_BYTES
    player = make_player(write_entry(tmp_path, "crowd", 1, source, run_seconds=30.0), crowd_cfg)
    play = play_through(player, crowd=True)
    typed = play.seconds(P.SOURCE, P.BUILD)
    ran = play.seconds(P.RUN, P.DWELL)
    dwelt = play.seconds(P.DWELL, P.DONE)
    expected = SOURCE_BYTES / (CROWD_CPS * show.pipeline.CROWD_SPEEDUP)
    print(f"crowd: SOURCE {typed:.3f} s (expected {expected:.3f}); RUN {ran:.3f} s (cap {CAP}); "
          f"DWELL {dwelt:.3f} s (dwell 5 s)")
    assert show.pipeline.CROWD_SPEEDUP == 4
    assert expected <= typed <= expected + SOURCE_SLACK
    assert CAP <= ran <= CAP + RUN_END_SLACK
    assert dwelt < DWELL_SKIP_BOUND
    assert player.failure is None


@needs_cc
def test_crowd_set_during_the_run_caps_it(tmp_path, cfg, make_player):
    crowd_cfg = dataclasses.replace(cfg, crowd_run_seconds=CAP)
    player = make_player(write_entry(tmp_path, "late", 1, SLOW_FOREVER_C, run_seconds=30.0), crowd_cfg)
    set_at: list[float] = []

    def crowd_arrives(p: EntryPlayer, play: Play, now: float) -> None:
        if p.phase == P.RUN and not p.crowd and now - play.at[P.RUN] >= CROWD_AT:
            p.crowd = True
            set_at.append(now - play.at[P.RUN])

    play = drive(player, start(player), each=crowd_arrives)
    ran = play.seconds(P.RUN, P.DWELL)
    print(f"crowd set {set_at[0]:.3f} s into RUN; RUN {ran:.3f} s (crowd_run_seconds {CAP})")
    assert player.failure is None
    assert CAP <= ran <= CAP + RUN_END_SLACK


@needs_cc
def test_a_pump_exception_ends_the_entry_and_plays_the_fallback(tmp_path, cfg, make_player):
    with_cast = make_player(write_entry(tmp_path, "esc", 1, ESCAPE_C, run_seconds=30.0,
                                        fallback=cast("recorded output\r\n")), cfg)
    play = play_through(with_cast)
    assert with_cast.failure == "terminal error (TypeError)"
    assert "*** terminal error (TypeError) ***" in play.screens[P.ERROR_HOLD]
    assert play.phases == [P.SOURCE, P.BUILD, P.RUN, P.ERROR_HOLD, P.FALLBACK, P.DWELL, P.DONE]
    assert "recorded output" in screen_lines(with_cast.term)
    assert wait_gone(play.pids[P.RUN])

    bare = make_player(write_entry(tmp_path, "esc2", 2, ESCAPE_C, run_seconds=30.0), cfg)
    play = play_through(bare)
    assert bare.failure == "terminal error (TypeError)"
    assert play.phases == [P.SOURCE, P.BUILD, P.RUN, P.ERROR_HOLD, P.DWELL, P.DONE]
    assert wait_gone(play.pids[P.RUN])


def test_an_unreadable_fallback_counts_as_none(tmp_path, cfg, make_player, caplog):
    player = make_player(write_entry(tmp_path, "bad", 1, HELLO_C, build="false", fallback="not json\n"), cfg)
    assert player.entry.fallback is not None
    with caplog.at_level(logging.ERROR, logger="show.pipeline"):
        play = play_through(player)
    assert play.phases == [P.SOURCE, P.BUILD, P.ERROR_HOLD, P.DWELL, P.DONE]
    assert player.failure == "build failed (exit 1)"
    logged = [r.getMessage() for r in caplog.records if r.name == "show.pipeline"]
    print(logged)
    assert any("fallback" in m for m in logged)


@needs_cc
def test_capture_writes_fallback_only_on_a_clean_run(tmp_path, cfg, make_player):
    capture = dataclasses.replace(cfg, capture=True)

    good_dir = write_entry(tmp_path, "good", 1, SLOW_HELLO_C)
    good = make_player(good_dir, capture)
    play = drive(good, start(good), until=P.RUN)
    assert (good_dir / CAPTURE_TEMP).exists() and not (good_dir / "fallback.cast").exists()
    drive(good, play)
    assert good.failure is None
    assert "hello, world" in (good_dir / "fallback.cast").read_text()
    assert not (good_dir / CAPTURE_TEMP).exists()

    bad_dir = write_entry(tmp_path, "bad", 2, CRASH_C)
    bad = make_player(bad_dir, capture)
    play_through(bad)
    assert bad.failure is not None and bad.failure.startswith("crashed")
    assert not (bad_dir / CAPTURE_TEMP).exists() and not (bad_dir / "fallback.cast").exists()

    stopped_dir = write_entry(tmp_path, "stopped", 3, SLOW_FOREVER_C, run_seconds=30.0)
    stopped = make_player(stopped_dir, capture)
    drive(stopped, start(stopped), until=P.RUN)
    assert (stopped_dir / CAPTURE_TEMP).exists()
    stopped.stop()
    assert stopped.done
    assert not (stopped_dir / CAPTURE_TEMP).exists() and not (stopped_dir / "fallback.cast").exists()


@needs_cc
def test_stop_kills_the_process_and_finishes(tmp_path, cfg, make_player):
    player = make_player(write_entry(tmp_path, "forever", 1, FOREVER_C, run_seconds=30.0), cfg)
    play = drive(player, start(player), until=P.RUN)
    player.stop()
    assert player.done and not player.term.running
    assert player.tick(time.monotonic()) == []
    assert wait_gone(play.pids[P.RUN])


@needs_cc
def test_backgrounding_entry_leaves_no_process(tmp_path, cfg, make_player):
    player = make_player(write_entry(tmp_path, "bg", 1, BACKGROUND_C), cfg)
    play = play_through(player)
    assert player.failure is None and play.phases == HAPPY
    orphans = [line for line in play.screens[P.DWELL].split("\n") if line.strip().isdigit()]
    assert len(orphans) == 1
    assert wait_gone(int(orphans[0]))


@needs_cc
def test_flooding_entry_does_not_stall_the_ticks(tmp_path, cfg, make_player):
    player = make_player(write_entry(tmp_path, "flood", 1, FOREVER_C, run_seconds=RUN_SECONDS), cfg)
    play = play_through(player)
    ticks = play.tick_ms[P.RUN]
    median = statistics.median(ticks)
    print(f"flood: {len(ticks)} RUN ticks; median {median:.2f} ms, max {max(ticks):.2f} ms")
    assert player.failure is None
    assert median < FLOOD_TICK_MS


@needs_cc
def test_the_output_tail_reaches_the_final_screen(tmp_path, cfg, make_player):
    player = make_player(write_entry(tmp_path, "count", 1, COUNT_C), cfg)
    play = play_through(player)
    assert player.failure is None
    dwell_lines = [line.strip() for line in play.screens[P.DWELL].split("\n")]
    assert "3000" in dwell_lines


def test_full_screen_entry_gets_24_rows(tmp_path, cfg, make_player):
    for station, (full, size) in enumerate(((True, "24 80"), (None, "23 80")), start=1):
        player = make_player(write_entry(tmp_path, f"stty{station}", station, HELLO_C, build="true",
                                         run="stty size", full_screen=full), cfg)
        play_through(player)
        assert player.failure is None
        assert size in screen_lines(player.term), (full, screen_lines(player.term))
