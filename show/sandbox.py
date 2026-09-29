"""Limits and network isolation for entry processes (spec 4.3).

Wall-clock timeouts and killing the process group are the pipeline's job; this is the safety net under them.
"""

from __future__ import annotations

import functools
import logging
import math
import resource
import shutil
import subprocess
import sys
from typing import Callable

log = logging.getLogger(__name__)

MAX_OUTPUT_FILE = 64 * 1024 * 1024
DEFAULT_MEMORY = 256 * 1024 * 1024
PROBE_TIMEOUT = 2.0


def limits(cpu_seconds: float, memory_bytes: int = DEFAULT_MEMORY) -> Callable[[], None]:
    """Return a preexec_fn that caps CPU time, core dumps, output file size and (on Linux) address space."""
    cpu = max(1, math.ceil(cpu_seconds))

    def apply() -> None:
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT_FILE, MAX_OUTPUT_FILE))
        if sys.platform.startswith("linux"):  # macOS refuses RLIMIT_AS
            resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))

    return apply


@functools.cache
def unshare_works() -> bool:
    """True when `unshare -rn` (user namespace, no network) runs here. Probed once; a failure logs a warning."""
    if shutil.which("unshare") is None:
        log.warning("no unshare: entries run without network isolation")
        return False
    try:
        probe = subprocess.run(["unshare", "-rn", "true"], timeout=PROBE_TIMEOUT,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as e:
        log.warning("unshare -rn probe failed (%s): entries run without network isolation", e)
        return False
    if probe.returncode != 0:
        log.warning("unshare -rn exited %d: entries run without network isolation", probe.returncode)
        return False
    return True


def wrap(command: str) -> list[str]:
    """The argv that runs a shell command, inside `unshare -rn` when the probe passed."""
    shell = ["sh", "-c", command]
    return ["unshare", "-rn", *shell] if unshare_works() else shell
