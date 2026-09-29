import os
import resource
import shlex
import signal
import socket
import subprocess
import sys
import time

import pytest

from show import sandbox
from show.sandbox import DEFAULT_MEMORY, MAX_OUTPUT_FILE, limits

WAIT = 5.0  # seconds a child may take before the test gives up (a passing child takes about 1 s or less)


@pytest.fixture
def spawn():
    """Start children in their own process group; kill every group in teardown."""
    children: list[subprocess.Popen] = []

    def start(args: list[str], preexec) -> subprocess.Popen:
        p = subprocess.Popen(args, preexec_fn=preexec, start_new_session=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        children.append(p)
        return p

    yield start
    for p in children:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        p.wait()
        for stream in (p.stdout, p.stderr):
            if stream:
                stream.close()


def python_says(spawn, code: str, preexec) -> tuple[int, str]:
    p = spawn([sys.executable, "-c", code], preexec)
    out, _ = p.communicate(timeout=WAIT)
    return p.returncode, out.strip()


def test_cpu_limit_kills_busy_loop(spawn):
    t0 = time.monotonic()
    p = spawn([sys.executable, "-c", "while True: pass"], limits(1))
    try:
        rc = p.wait(timeout=WAIT)
    except subprocess.TimeoutExpired:
        pytest.fail("busy loop was not killed by the CPU limit")
    took = time.monotonic() - t0
    print(f"busy loop ended with rc {rc} after {took:.2f} s")
    assert rc < 0


def test_limited_process_can_still_run_normally(spawn):
    rc, out = python_says(spawn, "print('ok')", limits(5))
    assert (rc, out) == (0, "ok")


def test_fractional_cpu_rounds_up_to_one_second(spawn):
    rc, out = python_says(spawn, "import resource; print(*resource.getrlimit(resource.RLIMIT_CPU))",
                          limits(0.2))
    assert (rc, out) == (0, "1 2")


def test_core_and_file_size_limits_are_set(spawn):
    code = ("import resource; print(*resource.getrlimit(resource.RLIMIT_CORE), "
            "*resource.getrlimit(resource.RLIMIT_FSIZE))")
    rc, out = python_says(spawn, code, limits(5))
    assert rc == 0
    assert [int(v) for v in out.split()] == [0, 0, MAX_OUTPUT_FILE, MAX_OUTPUT_FILE]
    assert MAX_OUTPUT_FILE == 64 * 1024 * 1024


def test_address_space_is_limited_on_linux_only(spawn):
    rc, out = python_says(spawn, "import resource; print(*resource.getrlimit(resource.RLIMIT_AS))", limits(5))
    assert rc == 0
    got = tuple(int(v) for v in out.split())
    if sys.platform.startswith("linux"):
        assert DEFAULT_MEMORY == 256 * 1024 * 1024
        assert got == (DEFAULT_MEMORY, DEFAULT_MEMORY)
    else:
        assert got == resource.getrlimit(resource.RLIMIT_AS)


@pytest.fixture
def fresh_probe():
    sandbox.unshare_works.cache_clear()
    yield
    sandbox.unshare_works.cache_clear()


def fake_probe(monkeypatch, returncode: int | None, calls: list | None = None) -> None:
    """`unshare` is found; the probe run exits with returncode, or times out when it is None."""
    monkeypatch.setattr("shutil.which", lambda name: f"/usr/bin/{name}")

    def run(args, **kwargs):
        if calls is not None:
            calls.append((args, kwargs))
        if returncode is None:
            raise subprocess.TimeoutExpired(args, kwargs.get("timeout"))
        return subprocess.CompletedProcess(args, returncode)

    monkeypatch.setattr("subprocess.run", run)


def test_probe_is_false_without_unshare(fresh_probe, monkeypatch, caplog):
    monkeypatch.setattr("shutil.which", lambda name: None)

    def no_run(*args, **kwargs):
        pytest.fail("the probe ran a subprocess although unshare is missing")

    monkeypatch.setattr("subprocess.run", no_run)
    with caplog.at_level("WARNING", logger="show.sandbox"):
        assert sandbox.unshare_works() is False
    assert any(r.levelname == "WARNING" and "unshare" in r.getMessage() for r in caplog.records)


def test_probe_is_cached(fresh_probe, monkeypatch):
    calls: list = []
    fake_probe(monkeypatch, 0, calls)
    assert sandbox.unshare_works() is True
    assert sandbox.unshare_works() is True
    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args == ["unshare", "-rn", "true"]
    assert kwargs.get("timeout") == sandbox.PROBE_TIMEOUT == 2.0


@pytest.mark.parametrize("returncode", [1, None], ids=["fails", "hangs"])
def test_probe_is_false_when_unshare_fails_or_hangs(fresh_probe, monkeypatch, caplog, returncode):
    fake_probe(monkeypatch, returncode)
    with caplog.at_level("WARNING", logger="show.sandbox"):
        assert sandbox.unshare_works() is False
    assert any(r.levelname == "WARNING" for r in caplog.records)


def test_wrap_uses_unshare_only_when_the_probe_passes(fresh_probe, monkeypatch):
    fake_probe(monkeypatch, 0)
    assert sandbox.wrap("./prog x") == ["unshare", "-rn", "sh", "-c", "./prog x"]
    sandbox.unshare_works.cache_clear()
    fake_probe(monkeypatch, 1)
    assert sandbox.wrap("./prog x") == ["sh", "-c", "./prog x"]


CONNECT = "import socket, sys; socket.create_connection(('127.0.0.1', int(sys.argv[1])), timeout=1).close()"


@pytest.mark.skipif(not sandbox.unshare_works(),
                    reason="needs a working unshare -rn (Linux with unprivileged user namespaces); "
                           "macOS has no unshare")
def test_sandboxed_run_cannot_reach_the_hosts_loopback(spawn):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen(4)
        port = server.getsockname()[1]
        command = f"{shlex.quote(sys.executable)} -c {shlex.quote(CONNECT)} {port}"

        plain = spawn(["sh", "-c", command], limits(5))
        plain.communicate(timeout=WAIT)
        assert plain.returncode == 0

        boxed = spawn(sandbox.wrap(command), limits(5))
        boxed.communicate(timeout=WAIT)
        assert boxed.returncode != 0
