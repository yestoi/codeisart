import logging
import os
import signal
import statistics
import sys
import time
from pathlib import Path

import pytest

from show.terminal import READ_CHUNK, Terminal

WAIT = 2.0            # seconds any child is given to do its thing
POLL = 0.005          # seconds between pumps while waiting
FLOOD = ["sh", "-c", "yes xxxxxxxx"]
FLOOD_SETTLE = 0.2    # seconds the flood gets to fill the pty before a pump is timed
PUMP_BOUND_MS = 20.0  # the amendment's bound on a default pump
KILL_BOUND_MS = 200.0  # kill() of a flood; one show frame is 50 ms
# A session leader that backgrounds `sleep 30` on the pty, prints its pid and exits without a controlling tty.
ORPHAN_LEADER = "import subprocess; print(subprocess.Popen(['sleep', '30']).pid, flush=True)"


@pytest.fixture
def term():
    t = Terminal()
    yield t
    t.kill()


def wait_finished(t: Terminal, seconds: float = WAIT) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline and not t.finished:
        t.pump()
        time.sleep(POLL)


def wait_for_text(t: Terminal, predicate, seconds: float = WAIT) -> str | None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        t.pump()
        for line in t.screen.display:
            if predicate(line.strip()):
                return line.strip()
        time.sleep(POLL)
    return None


def wait_gone(pid: int, seconds: float = WAIT) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(POLL)
    return False


def test_default_geometry_is_80x23(term):
    assert (term.columns, term.rows) == (80, 23)
    assert (term.screen.columns, term.screen.lines) == (80, 23)


def test_feed_updates_screen_with_lnm(term):
    term.feed(b"hello\nworld")
    assert term.screen.display[0].startswith("hello")
    assert term.screen.display[1].startswith("world")
    assert (term.screen.cursor.x, term.screen.cursor.y) == (5, 1)


def test_listeners_receive_bytes(term):
    got = []
    term.listeners.append(got.append)
    term.feed(b"abc")
    assert got == [b"abc"]


def test_reset_clears_and_keeps_lnm(term):
    term.feed(b"abc")
    term.reset()
    term.feed(b"x\ny")
    assert term.screen.display[0].startswith("x")
    assert term.screen.display[1].startswith("y")


def test_reset_restores_geometry_after_132_columns(term):
    term.feed(b"\x1b[?3h")
    assert term.screen.columns == 132
    term.reset()
    assert (term.screen.columns, term.screen.lines) == (80, 23)
    assert (term.columns, term.rows) == (80, 23)


def test_reset_after_132_columns_keeps_tab_stops_inside_80(term):
    term.feed(b"\x1b[?3h")
    term.reset()
    term.feed(b"\x1b[1;79H\t")          # column 79 (1-based), then a tab
    assert term.screen.cursor.x <= 79


def test_reset_to_24_rows_for_full_screen(term, tmp_path):
    term.reset(24)
    assert (term.rows, term.screen.lines, term.screen.columns) == (24, 24, 80)
    term.run(["sh", "-c", "stty size"], cwd=tmp_path)
    wait_finished(term)
    assert term.screen.display[0].startswith("24 80")


def test_run_captures_child_output_and_exit_code(term, tmp_path):
    term.run(["sh", "-c", "printf 'hi there\\n'; exit 3"], cwd=tmp_path)
    wait_finished(term)
    assert term.finished
    assert term.returncode == 3
    assert term.screen.display[0].startswith("hi there")


def test_child_sees_window_size(term, tmp_path):
    term.run(["sh", "-c", "stty size"], cwd=tmp_path)
    wait_finished(term)
    assert term.screen.display[0].startswith("23 80")


def test_child_env_has_term_columns_lines(term, tmp_path):
    term.run(["sh", "-c", 'echo "$TERM $COLUMNS $LINES"'], cwd=tmp_path)
    wait_finished(term)
    assert term.screen.display[0].startswith("xterm 80 23")


def test_kill_stops_running_child(term, tmp_path):
    term.run(["sh", "-c", "sleep 30"], cwd=tmp_path)
    assert term.running
    term.kill()
    assert not term.running
    assert term.finished
    assert term.returncode is not None and term.returncode < 0


def test_kill_of_a_flood_is_quick(term, tmp_path):
    # macOS: a child killed while its pty output queue is full waits in close() for the queue to drain
    # (about 0.6 s) unless the master is read while it dies.
    term.run(FLOOD, cwd=tmp_path)
    time.sleep(FLOOD_SETTLE)
    start = time.monotonic()
    term.kill()
    elapsed_ms = (time.monotonic() - start) * 1000.0
    print(f"kill() of a flood: {elapsed_ms:.2f} ms")
    assert term.finished
    assert elapsed_ms < KILL_BOUND_MS


def test_run_while_running_is_an_error(term, tmp_path):
    term.run(["sh", "-c", "sleep 30"], cwd=tmp_path)
    with pytest.raises(RuntimeError):
        term.run(["true"], cwd=tmp_path)


def test_default_pump_is_bounded_by_bytes_and_time(term, tmp_path):
    term.run(FLOOD, cwd=tmp_path)
    time.sleep(FLOOD_SETTLE)
    counts, times_ms = [], []
    for _ in range(10):
        start = time.monotonic()
        n = term.pump()
        times_ms.append((time.monotonic() - start) * 1000.0)
        counts.append(n)
    median = statistics.median(times_ms)
    print(f"default pump: bytes {counts}; ms {[round(x, 2) for x in times_ms]}; median {median:.2f} ms")
    assert all(n <= 4096 for n in counts)
    assert sum(counts) > 0
    assert median < PUMP_BOUND_MS


def test_pump_honours_a_small_budget(term, tmp_path):
    term.run(FLOOD, cwd=tmp_path)
    time.sleep(FLOOD_SETTLE)
    start = time.monotonic()
    n = term.pump(max_bytes=10**7, budget_ms=2.0)
    elapsed_ms = (time.monotonic() - start) * 1000.0
    print(f"pump(10**7, 2.0 ms): {n} bytes in {elapsed_ms:.2f} ms")
    assert n > 0
    assert elapsed_ms < PUMP_BOUND_MS


def test_pump_reads_at_most_read_chunk_at_a_time(term, tmp_path, monkeypatch):
    # The size asked of os.read is checked (a macOS pty never returns more than 1024 bytes anyway).
    asked = []
    real_read = os.read

    def spy(fd, n):
        if fd == term.master_fd:
            asked.append(n)
        return real_read(fd, n)

    term.run(FLOOD, cwd=tmp_path)
    time.sleep(FLOOD_SETTLE)
    monkeypatch.setattr(os, "read", spy)
    term.pump(max_bytes=10 * READ_CHUNK, budget_ms=1000.0)
    monkeypatch.undo()
    assert len(asked) > 1
    assert max(asked) <= READ_CHUNK


def test_run_closes_both_fds_when_popen_raises(term, tmp_path):
    before = len(os.listdir("/dev/fd"))
    with pytest.raises(FileNotFoundError):
        term.run(["/nonexistent/prog"], cwd=tmp_path)
    after = len(os.listdir("/dev/fd"))
    assert after == before
    assert not term.running


def test_kill_takes_the_process_group(term, tmp_path):
    # `trap '' HUP`: on macOS sh holds the pty as controlling terminal and its death alone would SIGHUP the
    # sleep; deaf to SIGHUP, only the group kill ends it.
    term.run(["sh", "-c", "trap '' HUP; sleep 30 & echo $!; wait"], cwd=tmp_path)
    line = wait_for_text(term, str.isdigit)
    assert line is not None
    pid = int(line)
    term.kill()
    assert wait_gone(pid)


def test_background_child_counts_as_finished_after_grace(term, tmp_path):
    # The plan's child is `sh -c "sleep 30 & exit 0"`. On macOS /bin/sh (bash 3.2) takes the pty as its
    # controlling terminal, so its exit revokes the pty: EOF comes at once and the orphan never holds it
    # (dash on the Pi does not). A leader that takes no controlling terminal holds it on both.
    term.run([sys.executable, "-c", ORPHAN_LEADER], cwd=tmp_path)
    line = wait_for_text(term, str.isdigit)
    assert line is not None
    pid = int(line)
    deadline = time.monotonic() + WAIT
    while term.running and time.monotonic() < deadline:
        term.pump()
        time.sleep(POLL)
    assert not term.running
    term.pump()
    assert not term.finished                       # the sleep holds the pty open
    assert term.finished_or_orphaned(0.3) is False  # the exit is first seen here
    time.sleep(0.3)
    term.pump()
    assert term.finished_or_orphaned(0.3) is True
    assert term.finished
    assert wait_gone(pid)


def test_finished_or_orphaned_is_true_for_a_clean_exit(term, tmp_path):
    term.run(["sh", "-c", "true"], cwd=tmp_path)
    start = time.monotonic()
    done = False
    while not done and time.monotonic() - start < WAIT:
        term.pump()
        done = term.finished_or_orphaned(grace=10 * WAIT)  # a grace far longer than the wait
        time.sleep(POLL)
    assert done
    assert term.finished


def test_finished_or_orphaned_kills_the_orphans_of_a_shell(term, tmp_path):
    # Linux: the orphan holds the pty and the grace ends it. macOS: the shell's exit revokes the pty (EOF
    # at once) and the orphan, deaf to SIGHUP, lives on unless the group is killed on the finished path.
    term.run(["sh", "-c", "trap '' HUP; sleep 30 & echo $!; exit 0"], cwd=tmp_path)
    line = wait_for_text(term, str.isdigit)
    assert line is not None
    pid = int(line)
    deadline = time.monotonic() + WAIT
    done = False
    while not done and time.monotonic() < deadline:
        term.pump()
        done = term.finished_or_orphaned(0.3)
        time.sleep(POLL)
    assert done
    assert wait_gone(pid)


def test_kill_after_the_shell_exited_unreaped_is_harmless(term, tmp_path):
    # macOS: killpg on a group holding only an unreaped zombie raises PermissionError (EPERM).
    term.run(["sh", "-c", "exit 0"], cwd=tmp_path)
    time.sleep(0.1)
    term.kill()
    assert term.finished
    assert term.returncode == 0


def test_finished_or_orphaned_is_false_before_any_run(term):
    assert term.finished_or_orphaned() is False


def test_kill_without_a_run_is_harmless(term):
    term.kill()
    assert not term.running and not term.finished


# C48: the group is forgotten once it cannot hold a process of this run, and never signalled after.

def spy_killpg(monkeypatch) -> list[tuple[int, int, str | None]]:
    """Record every os.killpg as (pgid, signal, the exception's name or None); the real call is made."""
    calls: list[tuple[int, int, str | None]] = []
    real = os.killpg

    def spy(pgid, sig):
        try:
            real(pgid, sig)
        except OSError as e:
            calls.append((pgid, sig, type(e).__name__))
            raise
        calls.append((pgid, sig, None))

    monkeypatch.setattr(os, "killpg", spy)
    return calls


def run_to_true(t: Terminal, **kwargs) -> bool:
    deadline = time.monotonic() + WAIT
    while time.monotonic() < deadline:
        t.pump()
        if t.finished_or_orphaned(**kwargs):
            return True
        time.sleep(POLL)
    return False


def test_a_finished_group_is_signalled_once(term, tmp_path, monkeypatch):
    calls = spy_killpg(monkeypatch)
    term.run(["true"], cwd=tmp_path)
    pgid = term.proc.pid
    assert run_to_true(term)
    for _ in range(3):
        assert term.finished_or_orphaned() is True
    term.kill()
    print(f"killpg calls: {calls}")
    assert [c[:2] for c in calls if c[0] == pgid] == [(pgid, signal.SIGKILL)]


def test_run_does_not_signal_the_previous_group(term, tmp_path, monkeypatch):
    term.run(["true"], cwd=tmp_path)
    first = term.proc.pid
    wait_finished(term)
    assert term.finished
    calls = spy_killpg(monkeypatch)
    term.run(["true"], cwd=tmp_path)
    print(f"killpg calls: {calls}")
    assert all(c[0] != first for c in calls)


def test_a_group_that_is_gone_is_forgotten(term, tmp_path, monkeypatch):
    calls = spy_killpg(monkeypatch)
    term.run(["true"], cwd=tmp_path)
    pgid = term.proc.pid
    wait_finished(term)
    assert term.finished_or_orphaned() is True  # the leader is reaped and alone: the group is gone
    for _ in range(3):
        term.finished_or_orphaned()
    term.kill()
    print(f"killpg calls: {calls}")
    assert calls == [(pgid, signal.SIGKILL, "ProcessLookupError")]


# Note 2: a pty still delivering data after the exit is drained, up to drain_max.

DRAIN_GRACE = 0.3
DRAIN_MAX_TEST = 1.0
# A session leader (no controlling tty, as ORPHAN_LEADER) that leaves a writer on the pty and exits.
SLOW_WRITER = "for i in 1 2 3 4 5 6 7 8; do echo line $i; sleep 0.1; done; echo END"
ENDLESS_WRITER = "while :; do echo x; sleep 0.1; done"


def leader_leaving(writer: str) -> list[str]:
    code = f"import subprocess; print(subprocess.Popen(['sh', '-c', {writer!r}]).pid, flush=True)"
    return [sys.executable, "-c", code]


def test_output_after_the_exit_is_drained_before_the_kill(term, tmp_path):
    term.run(leader_leaving(SLOW_WRITER), cwd=tmp_path)
    assert run_to_true(term, grace=DRAIN_GRACE)
    lines = [line.strip() for line in term.screen.display]
    print(f"screen at True: {[x for x in lines if x]}")
    assert "END" in lines


def test_a_writing_orphan_is_killed_at_drain_max(term, tmp_path):
    term.run(leader_leaving(ENDLESS_WRITER), cwd=tmp_path)
    line = wait_for_text(term, str.isdigit)
    assert line is not None
    pid = int(line)
    deadline = time.monotonic() + WAIT
    while term.running and time.monotonic() < deadline:
        term.pump()
        time.sleep(POLL)
    assert not term.running
    exit_seen = time.monotonic()  # the terminal first sees the exit in the next call, no sooner
    done = run_to_true(term, drain_max=DRAIN_MAX_TEST)
    elapsed = time.monotonic() - exit_seen
    print(f"writing orphan: True {elapsed:.3f} s after the exit (drain_max {DRAIN_MAX_TEST} s)")
    assert done and term.finished
    assert DRAIN_MAX_TEST <= elapsed <= DRAIN_MAX_TEST + WAIT
    assert wait_gone(pid)


# C49: a pump that raises inside kill() (pyte on a malformed escape) is logged once; the master is still
# closed and the group forgotten.

ESCAPE_THEN_SLEEP = ["sh", "-c", "printf '\\033[?3A'; sleep 30"]  # pyte raises on the private CUU
UNPUMPED = 0.3  # seconds the escape waits in the pty, no pump reading it


def test_kill_closes_the_master_when_the_pump_raises(term, tmp_path, caplog):
    term.run(ESCAPE_THEN_SLEEP, cwd=tmp_path)
    pid = term.proc.pid
    time.sleep(UNPUMPED)
    with caplog.at_level(logging.ERROR, logger="show.terminal"):
        term.kill()
    logged = [r for r in caplog.records if r.name == "show.terminal"]
    print(f"logged: {[r.getMessage() for r in logged]}")
    assert term.master_fd is None
    assert term._pgid is None
    assert term.proc.poll() is not None
    assert wait_gone(pid)
    assert len(logged) == 1
