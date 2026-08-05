"""Shared helpers for spawning the example host shell under test.

Both ``test_host_shell`` and ``test_conformance_kit_packaging`` need an
interpreter outside the repository ``.venv`` and a bounded read of the
host shell's listening-URL banner; keeping them here avoids one test
module importing another (which would couple unittest discovery order
and run the other module's import-time work).
"""

from __future__ import annotations

import os
import queue
import shutil
import subprocess
import threading

from tests.helpers import ROOT

BANNER_TIMEOUT_SECONDS = 30


def non_venv_interpreter() -> str:
    """Return an interpreter outside the repository .venv, if one exists."""
    venv_dir = os.path.realpath(str(ROOT / ".venv"))
    for candidate in ("/usr/bin/python3", shutil.which("python3")):
        if not candidate:
            continue
        resolved = os.path.realpath(candidate)
        if not os.path.isfile(resolved):
            continue
        if resolved.startswith(venv_dir + os.sep):
            continue
        return resolved
    return ""


def read_banner_line(server: subprocess.Popen) -> str:
    """Read the host shell's listening-URL line with a bounded wait.

    ``readline`` alone blocks until the job timeout if the host hangs
    before printing its URL, and a readiness poll can fire on a partial
    line.  A daemon thread performs the blocking read and hands the
    result through a queue, so the wait stays bounded either way; an
    empty line means the host exited before printing anything and is
    reported as a failure, not a silent success.
    """
    result = queue.Queue()

    def reader() -> None:
        try:
            result.put(server.stdout.readline())
        except Exception as error:
            result.put(error)

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    try:
        value = result.get(timeout=BANNER_TIMEOUT_SECONDS)
    except queue.Empty:
        raise AssertionError(
            "host shell did not print its listening URL within "
            f"{BANNER_TIMEOUT_SECONDS}s"
        ) from None
    if isinstance(value, BaseException):
        raise value
    if not value:
        raise AssertionError("host shell exited before printing its URL")
    return value
