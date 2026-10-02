import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # before anything imports pygame
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from show.config import Config
from show.font import Font

POOLED = "tests.arcade.pooled"   # imported only by a session that selects a test reading the oracle's pool


def _pool():
    """The session's running pool (tests/arcade/pooled.py's RUNNING), or None when no test started one."""
    pooled = sys.modules.get(POOLED)
    return None if pooled is None else pooled.RUNNING


def pytest_collection_finish(session):
    """Start the oracle's worker pool for the rows the selected tests read, so it plays beside the soaks."""
    if session.config.option.collectonly:
        return
    reading = [item for item in session.items if "pooled_plays" in item.fixturenames]
    if reading:
        from tests.arcade import pooled

        pooled.RUNNING = pooled.start(pooled.rows_for(session.items, reading[0].module.REPORT_PLAYS))


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Join a running pool before the first test that is not beside it (a timed one among them)."""
    pool = _pool()
    if pool is not None and not pool.joined:
        from tests.arcade import pooled

        if not pooled.beside_the_pool(item.nodeid, item.get_closest_marker("perf") is not None):
            pool.join()


def pytest_sessionfinish(session):
    """A pool never joined (-x, Ctrl-C, an error) is stopped: no worker outlives the session."""
    pool = _pool()
    if pool is not None and not pool.joined:
        pool.stop()


def pytest_terminal_summary(terminalreporter):
    pool = _pool()
    if pool is None:
        return
    if pool.waited is None:
        terminalreporter.write_line(f"pooled: stopped before its join, {len(pool.procs)} workers")
        return
    terminalreporter.write_line(f"pooled: {len(pool.stored)} plays, {len(pool.procs)} workers, {pool.elapsed:.1f} s, "
                                f"the join waited {pool.waited:.1f} s")

# Column bytes for a capital A in the glcdfont layout (bit 0 = top row).
A_COLUMNS = bytes([0x7E, 0x11, 0x11, 0x11, 0x7E])


@pytest.fixture
def font() -> Font:
    data = bytearray(256 * 5)
    data[65 * 5 : 66 * 5] = A_COLUMNS
    return Font(bytes(data))


@pytest.fixture
def fast_cfg() -> Config:
    return Config(typewriter_cps=1_000_000, dwell=0.1, error_hold=0.1, attract_lps=1000.0)
